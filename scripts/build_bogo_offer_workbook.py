#!/usr/bin/env python3
"""Chain x article offer-wise offtake workbook: BOGO eligible vs non-BOGO, by month and chain.

Reads files that are already in the repo and builds one Excel workbook. Nothing is invented:
a margin, offer or distributor figure that is not in a source file is left blank and flagged.

Sources (all under PowerBI/RawDataFolders):
  Offtake_Monthly/offtake_store_article_<Mon>_26.csv   store x article offtake, with a Margin column
  SecondarySales_Monthly_TOT_Analysis/05_ARTICLE_REGISTER_*.csv   distributor register with Quantity
  Promo_Calendar/*.csv                                  promotional communication (one file per month)

Rules:
  * BOGO eligible = article margin >= threshold (default 0.55, inclusive). Eligibility is NOT an active offer.
  * Reliance Brand Counter rows (Store Type = 'Brand Counter') are left out of offtake, as everywhere else in
    this project (CLAUDE.md). The workbook reconciles to the source with and without them.
  * Saliency = a segment's units (or value) divided by ALL units (or value) of the same chain in the same month.

Usage:
  python scripts/build_bogo_offer_workbook.py [--out work/Offtake_BOGO_Offer_DeepDive.xlsx] [--threshold 0.55]
The .xlsx is git-ignored on purpose: it holds chain x article offtake and margins.
"""
import argparse
import glob
import os
import hashlib
import json
import re
import sys
from pathlib import Path

import pandas as pd
import xlsxwriter
from xlsxwriter.utility import xl_col_to_name, xl_rowcol_to_cell

if os.environ.get("BOGO_NOCACHE"):
    # test mode: drop the pre-computed formula results so a spreadsheet engine must calculate every formula itself
    _wf = xlsxwriter.worksheet.Worksheet.write_formula
    xlsxwriter.worksheet.Worksheet.write_formula = lambda self, *a, **k: _wf(self, *(a[:4] if isinstance(a[0], int) else a[:3]))

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import build_dashboard_data as B  # noqa: E402  (canon_chain / canon_brand: the governed names)

RAW = ROOT / "PowerBI" / "RawDataFolders"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
ELIG = ["BOGO eligible", "Non-BOGO", "Margin missing"]
OFF_COLS = ["Chain Name", "Store Type", "EAN", "Article", "Description as per Fountain", "Chain Article Description",
            "Brand", "Category", "Sub_category", "Range", "Net Weight", "MRP", "Sales Qty", "MRP Sales Value", "NSV", "Margin"]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def ean(x):
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return ""
    s = str(x).strip().lstrip("'").replace(".0", "")
    try:
        return str(int(float(s))) if re.fullmatch(r"[\d.]+(e\+?\d+)?", s, re.I) else s
    except ValueError:
        return s


def mlabel(code):  # "Apr_26" / "2026-04" -> "Apr-26"
    if re.fullmatch(r"\d{4}-\d{2}", code):
        return "%s-%s" % (MONTHS[int(code[5:]) - 1], code[2:4])
    m, y = code.split("_")
    return "%s-%s" % (m, y)


def morder(lbl):
    m, y = lbl.split("-")
    return (int(y), MONTHS.index(m))


# --------------------------------------------------------------------------- load
def load_offtake():
    files = sorted(glob.glob(str(RAW / "Offtake_Monthly" / "offtake_store_article_*_*.csv")))
    parts, src = [], []
    for f in files:
        mon = mlabel(Path(f).stem.replace("offtake_store_article_", ""))
        d = pd.read_csv(f, usecols=OFF_COLS, low_memory=False)
        d["Month"] = mon
        parts.append(d)
        bc = d["Store Type"].astype(str).str.strip() == "Brand Counter"
        src.append({"file": Path(f).name, "month": mon, "rows": len(d), "sha256": sha(f),
                    "units_all": float(d["Sales Qty"].sum()), "nsv_all": float(d["NSV"].sum()),
                    "units_bc": float(d.loc[bc, "Sales Qty"].sum()), "nsv_bc": float(d.loc[bc, "NSV"].sum()),
                    "rows_bc": int(bc.sum()), "nsv_main": float(d.loc[~bc, "NSV"].sum()),
                    "units_main": float(d.loc[~bc, "Sales Qty"].sum())})
    a = pd.concat(parts, ignore_index=True)
    a = a[a["Store Type"].astype(str).str.strip() != "Brand Counter"].copy()
    a["Chain"] = a["Chain Name"].map(B.canon_chain)
    a["BrandC"] = a["Brand"].map(B.canon_brand)
    a["EANs"] = a["EAN"].map(ean)
    # Excel text matching ignores case, so two spellings that differ only in case would be added together by SUMIFS.
    # Use ONE spelling (the one with most offtake value) for each such group and list the merges on Review_List.
    merges = []
    for col in ("Sub_category", "Range"):
        a[col] = a[col].fillna("").astype(str).str.strip()
        key = a[col].str.lower()
        top = (a.assign(_k=key).groupby(["_k", col])["NSV"].sum().reset_index().sort_values("NSV", ascending=False).drop_duplicates("_k").set_index("_k")[col])
        a["_k"] = key
        used = a["_k"].map(top)
        for orig, new_ in a.loc[a[col] != used, [col]].assign(n=used[a[col] != used]).drop_duplicates().itertuples(index=False):
            merges.append((col, orig, new_))
        a[col] = used
        a = a.drop(columns="_k")
    a.attrs["merges"] = merges
    a["Desc"] = a["Description as per Fountain"].fillna(a["Chain Article Description"]).fillna("")
    def _code(x):
        if pd.isna(x):
            return ""
        t = str(x).strip()
        return str(int(float(t))) if re.fullmatch(r"\d+(\.0+)?", t) else t
    a["ArtCode"] = a["Article"].map(_code)
    return a, src, sorted({s["month"] for s in src}, key=morder)


def build_detail(a):
    keys = ["Month", "Chain", "EANs", "ArtCode", "Desc", "BrandC", "Sub_category", "Range", "Net Weight", "Margin"]
    a = a.copy()
    for k in ("Sub_category", "Range"):
        a[k] = a[k].fillna("")
    a["Net Weight"] = a["Net Weight"].fillna(-1)
    a["Margin"] = a["Margin"].round(6)
    g = a.groupby(keys, dropna=False).agg(Units=("Sales Qty", "sum"), NSV=("NSV", "sum"), MRPV=("MRP Sales Value", "sum"),
                                         Stores=("Sales Qty", "size")).reset_index()
    g["_m"] = g["Month"].map(morder)
    g = g.sort_values(["_m", "Chain", "BrandC", "Sub_category", "Range", "Net Weight", "EANs", "Margin"]).drop(columns="_m").reset_index(drop=True)
    g["Net Weight"] = g["Net Weight"].where(g["Net Weight"] >= 0, other=pd.NA)
    return g


def load_register():
    files = sorted(glob.glob(str(RAW / "SecondarySales_Monthly_TOT_Analysis" / "05_ARTICLE_REGISTER_*.csv")))
    parts, src = [], []
    for f in files:
        d = pd.read_csv(f, dtype=str)
        parts.append(d)
        src.append({"file": Path(f).name, "rows": len(d), "sha256": sha(f)})
    r = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
    if r.empty:
        return r, src
    r["Month"] = r["Source_Month"].map(mlabel)
    r["ChainC"] = r["Chain"].map(lambda x: B.canon_chain(x) if isinstance(x, str) else x)
    r["EANs"] = r["EAN"].map(ean)
    r["Qty"] = pd.to_numeric(r["Quantity"], errors="coerce")
    r["NSVr"] = pd.to_numeric(r["NSV_Value"], errors="coerce")
    r["Include"] = r["Billing_Basis"].fillna("").str.contains("excl. GST", case=False).map({True: "Y", False: "N"})
    return r, src


def _offer_text(v):
    s = str(v).strip()
    if s == "" or s.lower() == "nan":
        return "", ""
    if s.upper() == "BOGO":
        return "BOGO", "BOGO"
    try:
        f = float(s)
        return "%g%% off" % round(f * 100, 4), "Discount %"
    except ValueError:
        return s, "Not specified" if s.lower() == "not specified" else "Other"


def load_promo():
    files = sorted(glob.glob(str(RAW / "Promo_Calendar" / "*.csv")))
    parts, src = [], []
    for f in files:
        d = pd.read_csv(f, dtype=str)
        d["file"] = Path(f).name
        parts.append(d)
        src.append({"file": Path(f).name, "rows": len(d), "sha256": sha(f),
                    "months": sorted(d["Source_Month"].dropna().unique().tolist())})
    p = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
    if p.empty:
        return p, src
    p["Month"] = p["Source_Month"].map(mlabel)
    p["ChainC"] = p["Chain Name"].map(lambda x: B.canon_chain(str(x).strip()))
    p["EANs"] = p["EAN Code"].map(ean)
    t = p["Offer to consumer"].map(_offer_text)
    p["Offer"] = t.map(lambda x: x[0])
    p["OfferType"] = t.map(lambda x: x[1])
    p["From"] = p["From "].fillna("") if "From " in p else ""
    p["To"] = p["To"].fillna("") if "To" in p else ""
    return p, src


# --------------------------------------------------------------------------- workbook
def build(out, thr):
    a, off_src, months = load_offtake()
    d = build_detail(a)
    reg, reg_src = load_register()
    promo, promo_src = load_promo()
    n = len(d)
    last = n + 1  # last Excel row of the detail sheet

    wb = xlsxwriter.Workbook(out, {"nan_inf_to_errors": True})
    F = lambda **k: wb.add_format(dict({"font_name": "Calibri", "font_size": 10}, **k))
    hdr = F(bold=True, bg_color="#1F3A5F", font_color="#FFFFFF", text_wrap=True, valign="top", border=1)
    hdr_f = F(bold=True, bg_color="#3A6B35", font_color="#FFFFFF", text_wrap=True, valign="top", border=1)  # formula columns
    txt, num0, num2, num4 = F(), F(num_format="#,##0"), F(num_format="#,##0.00"), F(num_format="#,##0.0000")
    pct, pct2 = F(num_format="0.0%"), F(num_format="0.00%")
    inp = F(bg_color="#FFF2CC", border=1, num_format="0.0%", bold=True)
    bold, wrap, title = F(bold=True), F(text_wrap=True, valign="top"), F(bold=True, font_size=14)
    warn = F(bg_color="#FCE4D6", text_wrap=True, valign="top")
    good, bad = F(bg_color="#E2EFDA", bold=True), F(bg_color="#F8CBAD", bold=True)

    # ---- sheet order
    ws_read = wb.add_worksheet("README")
    ws_par = wb.add_worksheet("Parameters")
    ws_raw = wb.add_worksheet("Raw_Data")
    ws_cm = wb.add_worksheet("Chain_Month")
    sums = {k: wb.add_worksheet(k) for k in ("Sum_Chain", "Sum_Brand", "Sum_Subcategory", "Sum_Range", "Sum_Pack")}
    ws_off = wb.add_worksheet("Offer_Compare")
    ws_tr = wb.add_worksheet("MoM_Trends")
    ws_chk = wb.add_worksheet("Checks")
    ws_rev = wb.add_worksheet("Review_List")
    ws_sd = wb.add_worksheet("Source_Distributor")
    ws_sp = wb.add_worksheet("Source_Promo")
    ws_src = wb.add_worksheet("Sources")

    # ---- Parameters
    ws_par.write(0, 0, "Parameters (change the yellow cell; every sheet recalculates)", title)
    ws_par.write(2, 0, "BOGO margin threshold (inclusive)", bold)
    ws_par.write(2, 2, thr, inp)
    ws_par.write(3, 0, "Rule", bold)
    ws_par.write(3, 2, "Article margin >= threshold = BOGO eligible. Eligible is NOT the same as an offer that was communicated or run.", wrap)
    ws_par.write(5, 0, "Unit of offtake value", bold)
    ws_par.write(5, 2, "INR Lakh (NSV, the offtake file's NSV column). MRP value is in INR.", txt)
    ws_par.write(6, 0, "Saliency", bold)
    ws_par.write(6, 2, "Segment units (or value) / total units (or value) of the SAME chain in the SAME month. Units and value are separate.", wrap)
    ws_par.set_column(0, 0, 34); ws_par.set_column(2, 2, 110)
    wb.define_name("p_threshold", "=Parameters!$C$3")

    # ---- Source_Distributor
    sd_cols = ["Month", "Chain (canonical)", "EAN", "Distributor", "Chain (as in register)", "Brand", "Article", "Billing basis",
               "Counted as ex-GST (Y/N)", "Quantity", "NSV value (INR)", "Date flag", "Source row"]
    for c, h in enumerate(sd_cols):
        ws_sd.write(0, c, h, hdr)
    if not reg.empty:
        for i, r in reg.reset_index(drop=True).iterrows():
            row = i + 1
            ws_sd.write_string(row, 0, r["Month"]); ws_sd.write_string(row, 1, "" if pd.isna(r["ChainC"]) else str(r["ChainC"]))
            ws_sd.write_string(row, 2, r["EANs"]); ws_sd.write_string(row, 3, str(r["Distributor"]))
            ws_sd.write_string(row, 4, "" if pd.isna(r["Chain"]) else str(r["Chain"]))
            ws_sd.write_string(row, 5, "" if pd.isna(r["Brand"]) else str(r["Brand"]))
            ws_sd.write_string(row, 6, "" if pd.isna(r["Article"]) else str(r["Article"]))
            ws_sd.write_string(row, 7, "" if pd.isna(r["Billing_Basis"]) else str(r["Billing_Basis"]))
            ws_sd.write_string(row, 8, r["Include"])
            ws_sd.write_number(row, 9, 0 if pd.isna(r["Qty"]) else float(r["Qty"]))
            ws_sd.write_number(row, 10, 0 if pd.isna(r["NSVr"]) else float(r["NSVr"]))
            ws_sd.write_string(row, 11, "" if pd.isna(r["Date_Flag"]) else str(r["Date_Flag"]))
            ws_sd.write_number(row, 12, i + 2)
    sd_last = max(2, len(reg) + 1)
    ws_sd.freeze_panes(1, 0); ws_sd.set_column(0, 12, 16); ws_sd.autofilter(0, 0, sd_last - 1, 12)
    for nm, col in (("sd_month", "A"), ("sd_chain", "B"), ("sd_ean", "C"), ("sd_inc", "I"), ("sd_qty", "J"), ("sd_nsv", "K")):
        wb.define_name(nm, "=Source_Distributor!$%s$2:$%s$%d" % (col, col, sd_last))

    # ---- Source_Promo
    sp_cols = ["Key (Month|Chain|EAN)", "Month", "Chain (canonical)", "EAN", "Chain (as in file)", "Brand", "Article code", "Description",
               "Offer as supplied", "Offer", "Offer type", "From", "To", "Promo type", "Source file"]
    for c, h in enumerate(sp_cols):
        ws_sp.write(0, c, h, hdr)
    if not promo.empty:
        for i, r in promo.reset_index(drop=True).iterrows():
            row = i + 1
            key = "%s|%s|%s" % (r["Month"], r["ChainC"], r["EANs"])
            vals = [key, r["Month"], str(r["ChainC"]), r["EANs"], str(r["Chain Name"]), str(r["Brand"]), str(r["Article Code"]),
                    str(r["Description"]), str(r["Offer to consumer"]), r["Offer"], r["OfferType"], str(r["From"]), str(r["To"]),
                    str(r.get("Promo_Type", "")), r["file"]]
            for c, v in enumerate(vals):
                ws_sp.write_string(row, c, "" if v == "nan" else v)
    sp_last = max(2, len(promo) + 1)
    ws_sp.freeze_panes(1, 0); ws_sp.set_column(0, 0, 40); ws_sp.set_column(1, 14, 16); ws_sp.autofilter(0, 0, sp_last - 1, 14)
    for nm, col in (("sp_key", "A"), ("sp_offer", "J"), ("sp_type", "K"), ("sp_from", "L"), ("sp_to", "M"), ("sp_month", "B")):
        wb.define_name(nm, "=Source_Promo!$%s$2:$%s$%d" % (col, col, sp_last))

    # ---- Raw_Data (detail)
    cols = [
        ("Row ID", 8, False), ("Month", 9, False), ("Chain", 18, False), ("EAN", 15, False), ("Article code", 11, False),
        ("Article description", 38, False), ("Brand", 14, False), ("Subcategory", 18, False), ("Range", 18, False), ("Pack (net weight)", 9, False),
        ("Offer type (from communication)", 16, True), ("Offtake units", 11, False), ("Offtake value NSV (INR Lakh)", 14, False),
        ("MRP sales value (INR)", 14, False), ("Avg MRP per unit (INR)", 11, True), ("Article margin %", 10, False),
        ("Margin used: source", 44, False), ("BOGO eligibility", 15, True),
        ("Distributor qty (register, ex-GST basis)", 13, True), ("Distributor NSV (INR, ex-GST basis)", 14, True),
        ("Distributor-to-chain billed margin %", 14, True), ("Billed margin: formula / source", 40, True),
        ("Promotional offer communicated", 20, True), ("Communication date / month", 24, True), ("BOGO communicated?", 18, True),
        ("Review flag", 44, True), ("Store rows aggregated", 9, False), ("Lookup key", 30, True),
    ]
    for c, (h, w, isf) in enumerate(cols):
        ws_raw.write(0, c, h, hdr_f if isf else hdr)
        ws_raw.set_column(c, c, w)
    ws_raw.set_row(0, 45); ws_raw.freeze_panes(1, 3); ws_raw.autofilter(0, 0, n, len(cols) - 1)
    C = {h: xl_col_to_name(i) for i, (h, _, _) in enumerate(cols)}
    names = {"rd_month": "Month", "rd_chain": "Chain", "rd_brand": "Brand", "rd_subcat": "Subcategory", "rd_range": "Range",
             "rd_pack": "Pack (net weight)", "rd_units": "Offtake units", "rd_value": "Offtake value NSV (INR Lakh)",
             "rd_margin": "Article margin %", "rd_elig": "BOGO eligibility", "rd_offer": "Promotional offer communicated",
             "rd_offertype": "Offer type (from communication)", "rd_dq": "Distributor qty (register, ex-GST basis)",
             "rd_bm": "Distributor-to-chain billed margin %", "rd_ean": "EAN", "rd_flag": "Review flag", "rd_bogocomm": "BOGO communicated?"}
    for nm, h in names.items():
        wb.define_name(nm, "=Raw_Data!$%s$2:$%s$%d" % (C[h], C[h], last))

    # cached values (computed here the same way the formulas compute them)
    reg_inc = reg[reg["Include"] == "Y"] if not reg.empty else reg
    dist = (reg_inc.groupby(["Month", "ChainC", "EANs"])[["Qty", "NSVr"]].sum().to_dict("index") if not reg.empty else {})
    promo_first = {}
    if not promo.empty:
        for _, r in promo.iterrows():
            promo_first.setdefault("%s|%s|%s" % (r["Month"], r["ChainC"], r["EANs"]), r)

    rows = []
    for i, r in d.iterrows():
        x = i + 2
        mg = r["Margin"]
        mg_ok = pd.notna(mg) and mg > 0
        elig = "Margin missing" if not mg_ok else ("BOGO eligible" if mg >= thr else "Non-BOGO")
        avg_mrp = (r["MRPV"] / r["Units"]) if r["Units"] > 0 else ""
        dd = dist.get((r["Month"], r["Chain"], r["EANs"]), {"Qty": 0.0, "NSVr": 0.0})
        dq, dn = float(dd["Qty"]), float(dd["NSVr"])
        bm = (1 - (dn / dq) / avg_mrp) if (dq > 0 and avg_mrp not in ("", 0)) else ""
        key = "%s|%s|%s" % (r["Month"], r["Chain"], r["EANs"])
        pr = promo_first.get(key)
        offer = pr["Offer"] if pr is not None else ""
        otype = pr["OfferType"] if pr is not None else ""
        comm = ("%s to %s" % (pr["From"], pr["To"]) if (pr["From"] or pr["To"]) else pr["Month"]) if pr is not None else ""
        bogoc = "" if pr is None else ("Communicated BOGO" if otype == "BOGO" else "Other offer communicated")
        flag = ("Margin missing; " if elig == "Margin missing" else "") + ("No offer communication on file; " if offer == "" else "") + \
               ("No distributor quantity match; " if dq <= 0 else "") + \
               ("Billed margin outside 0-90%: check units or basis; " if (bm != "" and (bm < 0 or bm > 0.9)) else "")
        flag = flag.strip()
        rows.append((x, elig, avg_mrp, dq, dn, bm, offer, comm, bogoc, flag, otype, key))
        # write
        ws_raw.write_number(x - 1, 0, i + 1)
        ws_raw.write_string(x - 1, 1, r["Month"]); ws_raw.write_string(x - 1, 2, r["Chain"])
        ws_raw.write_string(x - 1, 3, r["EANs"]); ws_raw.write_string(x - 1, 4, r["ArtCode"])
        ws_raw.write_string(x - 1, 5, r["Desc"] or "(no description in source)"); ws_raw.write_string(x - 1, 6, r["BrandC"])
        ws_raw.write_string(x - 1, 7, r["Sub_category"] or "(blank in source)"); ws_raw.write_string(x - 1, 8, r["Range"] or "(blank in source)")
        if pd.isna(r["Net Weight"]):
            ws_raw.write_string(x - 1, 9, "(blank in source)")
        else:
            ws_raw.write_number(x - 1, 9, float(r["Net Weight"]))
        k = lambda h: "%s%d" % (C[h], x)
        ws_raw.write_formula(x - 1, 10, '=IF(%s="","",INDEX(sp_type,MATCH(%s,sp_key,0)))' % (k("Promotional offer communicated"), k("Lookup key")), txt, otype)
        ws_raw.write_number(x - 1, 11, float(r["Units"]), num0)
        ws_raw.write_number(x - 1, 12, float(r["NSV"]), num4)
        ws_raw.write_number(x - 1, 13, float(r["MRPV"]), num2)
        ws_raw.write_formula(x - 1, 14, '=IF(%s>0,%s/%s,"")' % (k("Offtake units"), k("MRP sales value (INR)"), k("Offtake units")), num2, avg_mrp)
        if mg_ok:
            ws_raw.write_number(x - 1, 15, float(mg), pct)
        else:
            ws_raw.write_blank(x - 1, 15, None, pct)
        src_f = "Offtake file offtake_store_article_%s.csv, column 'Margin' (as supplied; one row per distinct margin)" % r["Month"].replace("-", "_")
        ws_raw.write_string(x - 1, 16, src_f if mg_ok else "Margin blank or 0 in the offtake file; no other margin source supplied")
        ws_raw.write_formula(x - 1, 17, '=IF(OR(%s="",%s<=0),"Margin missing",IF(%s>=p_threshold,"BOGO eligible","Non-BOGO"))' % (
            k("Article margin %"), k("Article margin %"), k("Article margin %")), txt, elig)
        ws_raw.write_formula(x - 1, 18, '=SUMIFS(sd_qty,sd_month,%s,sd_chain,%s,sd_ean,%s,sd_inc,"Y")' % (k("Month"), k("Chain"), k("EAN")), num0, dq)
        ws_raw.write_formula(x - 1, 19, '=SUMIFS(sd_nsv,sd_month,%s,sd_chain,%s,sd_ean,%s,sd_inc,"Y")' % (k("Month"), k("Chain"), k("EAN")), num2, dn)
        ws_raw.write_formula(x - 1, 20, '=IF(OR(%s<=0,%s=""),"",1-(%s/%s)/%s)' % (
            k("Distributor qty (register, ex-GST basis)"), k("Avg MRP per unit (INR)"), k("Distributor NSV (INR, ex-GST basis)"),
            k("Distributor qty (register, ex-GST basis)"), k("Avg MRP per unit (INR)")), pct, bm)
        ws_raw.write_formula(x - 1, 21, '=IF(%s="","No distributor quantity for this month/chain/article: left blank","= 1 - (Distributor NSV / Distributor qty) / Avg MRP; NSV and qty from Source_Distributor, MRP from offtake")' % k("Distributor-to-chain billed margin %"),
                             txt, "No distributor quantity for this month/chain/article: left blank" if bm == "" else "= 1 - (Distributor NSV / Distributor qty) / Avg MRP; NSV and qty from Source_Distributor, MRP from offtake")
        ws_raw.write_formula(x - 1, 22, '=IFERROR(INDEX(sp_offer,MATCH(%s,sp_key,0)),"")' % k("Lookup key"), txt, offer)
        ws_raw.write_formula(x - 1, 23, '=IFERROR(IF(INDEX(sp_from,MATCH(%s,sp_key,0))&INDEX(sp_to,MATCH(%s,sp_key,0))="",INDEX(sp_month,MATCH(%s,sp_key,0)),INDEX(sp_from,MATCH(%s,sp_key,0))&" to "&INDEX(sp_to,MATCH(%s,sp_key,0))),"")' % ((k("Lookup key"),) * 5), txt, comm)
        ws_raw.write_formula(x - 1, 24, '=IF(%s="","",IF(%s="BOGO","Communicated BOGO","Other offer communicated"))' % (k("Promotional offer communicated"), k("Offer type (from communication)")), txt, bogoc)
        ws_raw.write_formula(x - 1, 25, '=TRIM(IF(%s="Margin missing","Margin missing; ","")&IF(%s="","No offer communication on file; ","")&IF(%s<=0,"No distributor quantity match; ","")&IF(%s="","",IF(OR(%s<0,%s>0.9),"Billed margin outside 0-90%%: check units or basis; ","")))' % (
            k("BOGO eligibility"), k("Promotional offer communicated"), k("Distributor qty (register, ex-GST basis)"),
            k("Distributor-to-chain billed margin %"), k("Distributor-to-chain billed margin %"), k("Distributor-to-chain billed margin %")), txt, flag)
        ws_raw.write_number(x - 1, 26, int(r["Stores"]), num0)
        ws_raw.write_formula(x - 1, 27, '=%s&"|"&%s&"|"&%s' % (k("Month"), k("Chain"), k("EAN")), txt, key)
    d["Elig"] = [r[1] for r in rows]
    d["Flag"] = [r[9] for r in rows]
    d["DistQty"] = [r[3] for r in rows]
    d["Offer"] = [r[6] for r in rows]
    d["BM"] = [r[5] for r in rows]

    # ---- Chain_Month (denominators)
    cm = d.groupby(["Month", "Chain"]).agg(U=("Units", "sum"), V=("NSV", "sum")).reset_index()
    cm["_m"] = cm["Month"].map(morder)
    cm = cm.sort_values(["_m", "Chain"]).drop(columns="_m").reset_index(drop=True)
    ws_cm.write(0, 0, "Chain x month totals: the denominator of every saliency %", title)
    ch = ["Month", "Chain", "Total units", "Total value (INR Lakh)", "BOGO eligible units", "BOGO eligible value", "Non-BOGO units",
          "Non-BOGO value", "Margin missing units", "Margin missing value", "Check: classes - total"]
    for c, h in enumerate(ch):
        ws_cm.write(2, c, h, hdr_f if c >= 2 else hdr)
    ws_cm.set_row(2, 32)
    cm0 = 3
    for i, r in cm.iterrows():
        x = cm0 + i
        ws_cm.write_string(x, 0, r["Month"]); ws_cm.write_string(x, 1, r["Chain"])
        sub = d[(d["Month"] == r["Month"]) & (d["Chain"] == r["Chain"])]
        ws_cm.write_formula(x, 2, "=SUMIFS(rd_units,rd_month,$A%d,rd_chain,$B%d)" % (x + 1, x + 1), num0, float(r["U"]))
        ws_cm.write_formula(x, 3, "=SUMIFS(rd_value,rd_month,$A%d,rd_chain,$B%d)" % (x + 1, x + 1), num4, float(r["V"]))
        for j, e in enumerate(ELIG):
            su = float(sub.loc[sub["Elig"] == e, "Units"].sum()); sv = float(sub.loc[sub["Elig"] == e, "NSV"].sum())
            ws_cm.write_formula(x, 4 + 2 * j, '=SUMIFS(rd_units,rd_month,$A%d,rd_chain,$B%d,rd_elig,"%s")' % (x + 1, x + 1, e), num0, su)
            ws_cm.write_formula(x, 5 + 2 * j, '=SUMIFS(rd_value,rd_month,$A%d,rd_chain,$B%d,rd_elig,"%s")' % (x + 1, x + 1, e), num4, sv)
        ws_cm.write_formula(x, 10, "=ROUND(E%d+G%d+I%d-C%d,6)+ROUND(F%d+H%d+J%d-D%d,6)" % ((x + 1,) * 8), num4, 0)
    cm_last = cm0 + len(cm)
    ws_cm.freeze_panes(3, 2); ws_cm.set_column(0, 1, 18); ws_cm.set_column(2, 10, 15)
    for nm, col in (("cm_month", "A"), ("cm_chain", "B"), ("cm_units", "C"), ("cm_value", "D")):
        wb.define_name(nm, "=Chain_Month!$%s$%d:$%s$%d" % (col, cm0 + 1, col, cm_last))
    tot = cm_last + 1
    ws_cm.write(tot, 1, "All chains, all months", bold)
    ws_cm.write_formula(tot, 2, "=SUM(C%d:C%d)" % (cm0 + 1, cm_last), num0, float(cm["U"].sum()))
    ws_cm.write_formula(tot, 3, "=SUM(D%d:D%d)" % (cm0 + 1, cm_last), num4, float(cm["V"].sum()))
    cmu = {(r["Month"], r["Chain"]): r["U"] for _, r in cm.iterrows()}
    cmv = {(r["Month"], r["Chain"]): r["V"] for _, r in cm.iterrows()}

    # ---- Sum_ sheets
    dims = {"Sum_Chain": (None, None), "Sum_Brand": ("Brand", "BrandC"), "Sum_Subcategory": ("Subcategory", "Sub_category"),
            "Sum_Range": ("Range", "Range"), "Sum_Pack": ("Pack (net weight)", "Net Weight")}
    dname = {"Sum_Brand": "rd_brand", "Sum_Subcategory": "rd_subcat", "Sum_Range": "rd_range", "Sum_Pack": "rd_pack"}
    sum_totals = {}
    for sh, ws in sums.items():
        label, col = dims[sh]
        ws.write(0, 0, "BOGO eligible vs non-BOGO by month and chain%s" % ("" if col is None else " and " + label.lower()), title)
        ws.write(1, 0, "Saliency = segment units (value) / total units (value) of the same chain in the same month. Units and value are separate. "
                       "Margin-missing articles are shown on their own so they are never counted as BOGO or non-BOGO.", wrap)
        heads = ["Month", "Chain"] + ([label] if col else []) + [
            "BOGO eligible units", "BOGO eligible value (INR Lakh)", "Non-BOGO units", "Non-BOGO value (INR Lakh)",
            "Margin missing units", "Margin missing value (INR Lakh)", "Segment total units", "Segment total value (INR Lakh)",
            "Chain-month total units", "Chain-month total value (INR Lakh)",
            "BOGO eligible unit saliency %", "BOGO eligible value saliency %", "Non-BOGO unit saliency %", "Non-BOGO value saliency %",
            "Margin missing unit saliency %", "Margin missing value saliency %", "Segment unit saliency %", "Segment value saliency %"]
        for c, h in enumerate(heads):
            ws.write(3, c, h, hdr_f if c >= (3 if col else 2) else hdr)
        ws.set_row(3, 48)
        keys = ["Month", "Chain"] + ([col] if col else [])
        gg = d.copy()
        if col == "Net Weight":
            gg["Net Weight"] = gg["Net Weight"].astype(object).where(gg["Net Weight"].notna(), "(blank in source)")
        elif col in ("Sub_category", "Range"):
            gg[col] = gg[col].replace("", "(blank in source)")
        seg = gg.groupby(keys).size().reset_index()[keys]
        seg["_m"] = seg["Month"].map(morder)
        seg = seg.sort_values(["_m", "Chain"] + ([col] if col else []), key=lambda s: s.astype(str) if s.name == col else s).drop(columns="_m").reset_index(drop=True)
        r0 = 4
        off = 3 if col else 2
        coln = lambda k_: xl_col_to_name(k_)
        piv = gg.groupby(keys + ["Elig"]).agg(U=("Units", "sum"), V=("NSV", "sum"))
        acc = [0.0] * 8
        for i, r in seg.iterrows():
            x = r0 + i
            xr = x + 1
            ws.write_string(x, 0, r["Month"]); ws.write_string(x, 1, r["Chain"])
            segv = None
            if col:
                segv = r[col]
                if isinstance(segv, float) and segv == int(segv):
                    ws.write_number(x, 2, float(segv))
                else:
                    ws.write(x, 2, segv)
            crit = "rd_month,$A%d,rd_chain,$B%d" % (xr, xr) + (",%s,$C%d" % (dname[sh], xr) if col else "")
            vals = {}
            for j, e in enumerate(ELIG):
                try:
                    pu = float(piv.loc[tuple([r[k_] for k_ in keys] + [e]), "U"]); pv = float(piv.loc[tuple([r[k_] for k_ in keys] + [e]), "V"])
                except KeyError:
                    pu = pv = 0.0
                vals[e] = (pu, pv)
                ws.write_formula(x, off + 2 * j, '=SUMIFS(rd_units,%s,rd_elig,"%s")' % (crit, e), num0, pu)
                ws.write_formula(x, off + 2 * j + 1, '=SUMIFS(rd_value,%s,rd_elig,"%s")' % (crit, e), num4, pv)
            su = sum(v[0] for v in vals.values()); sv = sum(v[1] for v in vals.values())
            for k_ in range(3):
                acc[2 * k_] += vals[ELIG[k_]][0]; acc[2 * k_ + 1] += vals[ELIG[k_]][1]
            acc[6] += su; acc[7] += sv
            cu, cv = cmu[(r["Month"], r["Chain"])], cmv[(r["Month"], r["Chain"])]
            c1, c2, c3, c4, c5, c6 = [coln(off + k_) for k_ in range(6)]
            ct, cvv = coln(off + 6), coln(off + 7)
            ws.write_formula(x, off + 6, "=%s%d+%s%d+%s%d" % (c1, xr, c3, xr, c5, xr), num0, su)
            ws.write_formula(x, off + 7, "=%s%d+%s%d+%s%d" % (c2, xr, c4, xr, c6, xr), num4, sv)
            ws.write_formula(x, off + 8, "=SUMIFS(cm_units,cm_month,$A%d,cm_chain,$B%d)" % (xr, xr), num0, float(cu))
            ws.write_formula(x, off + 9, "=SUMIFS(cm_value,cm_month,$A%d,cm_chain,$B%d)" % (xr, xr), num4, float(cv))
            cu_c, cv_c = coln(off + 8), coln(off + 9)
            sal = [(c1, vals[ELIG[0]][0], cu_c, cu), (c2, vals[ELIG[0]][1], cv_c, cv), (c3, vals[ELIG[1]][0], cu_c, cu), (c4, vals[ELIG[1]][1], cv_c, cv),
                   (c5, vals[ELIG[2]][0], cu_c, cu), (c6, vals[ELIG[2]][1], cv_c, cv), (ct, su, cu_c, cu), (cvv, sv, cv_c, cv)]
            for k_, (nc, nv, dc, dv) in enumerate(sal):
                ws.write_formula(x, off + 10 + k_, '=IF(%s%d=0,"",%s%d/%s%d)' % (dc, xr, nc, xr, dc, xr), pct2, (nv / dv) if dv else "")
        endr = r0 + len(seg)
        ws.write(endr + 1, 1, "Total of rows above", bold)
        for k_ in range(0, 8):
            cc = off + k_
            ws.write_formula(endr + 1, cc, "=SUM(%s%d:%s%d)" % (coln(cc), r0 + 1, coln(cc), endr), num4 if k_ % 2 else num0, acc[k_])
        ws.freeze_panes(4, off); ws.set_column(0, 1, 16)
        if col:
            ws.set_column(2, 2, 22)
        ws.set_column(off, off + 17, 14)
        ws.autofilter(3, 0, endr - 1, off + 17)
        sum_totals[sh] = (r0 + 1, endr, off)

    # ---- Offer_Compare
    ws_off.write(0, 0, "Offer-wise comparison: eligibility group x communicated offer type, by month", title)
    ws_off.write(1, 0, "Eligibility (margin rule) and communication (the offer we shared) are kept apart. A BOGO-eligible article is NOT shown as an active BOGO offer unless a BOGO was communicated.", wrap)
    oh = ["Month", "Eligibility group", "Communicated offer type", "Chain-article rows", "Offtake units", "Offtake value (INR Lakh)",
          "Unit saliency % (of month total)", "Value saliency % (of month total)", "Value-weighted article margin %"]
    for c, h in enumerate(oh):
        ws_off.write(3, c, h, hdr_f if c >= 3 else hdr)
    ws_off.set_row(3, 40)
    types = ["BOGO", "Discount %", "Other", "Not specified", "No communication on file"]
    r = 4
    mtot_u = d.groupby("Month")["Units"].sum().to_dict(); mtot_v = d.groupby("Month")["NSV"].sum().to_dict()
    d["OfferT"] = [x[10] if x[10] else "No communication on file" for x in rows]
    for m in months:
        for e in ELIG:
            for t in types:
                sub = d[(d["Month"] == m) & (d["Elig"] == e) & (d["OfferT"] == t)]
                xr = r + 1
                ws_off.write_string(r, 0, m); ws_off.write_string(r, 1, e); ws_off.write_string(r, 2, t)
                tcrit = '' if t == "No communication on file" else ',rd_offertype,$C%d' % xr
                if t == "No communication on file":
                    cnt = '=COUNTIFS(rd_month,$A%d,rd_elig,$B%d,rd_offer,"")' % (xr, xr)
                    su = '=SUMIFS(rd_units,rd_month,$A%d,rd_elig,$B%d,rd_offer,"")' % (xr, xr)
                    sv = '=SUMIFS(rd_value,rd_month,$A%d,rd_elig,$B%d,rd_offer,"")' % (xr, xr)
                else:
                    cnt = '=COUNTIFS(rd_month,$A%d,rd_elig,$B%d,rd_offertype,$C%d)' % (xr, xr, xr)
                    su = '=SUMIFS(rd_units,rd_month,$A%d,rd_elig,$B%d,rd_offertype,$C%d)' % (xr, xr, xr)
                    sv = '=SUMIFS(rd_value,rd_month,$A%d,rd_elig,$B%d,rd_offertype,$C%d)' % (xr, xr, xr)
                ws_off.write_formula(r, 3, cnt, num0, len(sub))
                ws_off.write_formula(r, 4, su, num0, float(sub["Units"].sum()))
                ws_off.write_formula(r, 5, sv, num4, float(sub["NSV"].sum()))
                ws_off.write_formula(r, 6, '=IF(SUMIFS(rd_units,rd_month,$A%d)=0,"",E%d/SUMIFS(rd_units,rd_month,$A%d))' % (xr, xr, xr), pct2,
                                     (sub["Units"].sum() / mtot_u[m]) if mtot_u[m] else "")
                ws_off.write_formula(r, 7, '=IF(SUMIFS(rd_value,rd_month,$A%d)=0,"",F%d/SUMIFS(rd_value,rd_month,$A%d))' % (xr, xr, xr), pct2,
                                     (sub["NSV"].sum() / mtot_v[m]) if mtot_v[m] else "")
                # weighted margin: sum(margin*value)/sum(value) over rows with a margin
                crit = 'rd_month,$A%d,rd_elig,$B%d' % (xr, xr) + (',rd_offer,""' if t == "No communication on file" else ',rd_offertype,$C%d' % xr)
                wm_val = ""
                ss = sub[sub["Margin"] > 0]
                if len(ss) and ss["NSV"].sum() > 0:
                    wm_val = float((ss["Margin"] * ss["NSV"]).sum() / ss["NSV"].sum())
                ws_off.write_formula(r, 8, '=IF(OR($B%d="Margin missing",F%d=0),"",IFERROR(SUMPRODUCT((rd_month=$A%d)*(rd_elig=$B%d)*%s*(rd_margin<>"")*rd_margin*rd_value)/F%d,""))' % (
                    xr, xr, xr, xr, ('(rd_offer="")' if t == "No communication on file" else '(rd_offertype=$C%d)' % xr), xr), pct,
                    wm_val if e != "Margin missing" else "")
                r += 1
    ws_off.freeze_panes(4, 3); ws_off.set_column(0, 2, 22); ws_off.set_column(3, 8, 16); ws_off.autofilter(3, 0, r - 1, 8)

    # ---- MoM_Trends
    ws_tr.write(0, 0, "Month-on-month trends: BOGO eligible vs non-BOGO", title)
    ws_tr.write(1, 0, "All chains together, then each chain. Saliency = share of that month's offtake (all chains) or of that chain's offtake.", wrap)
    th = ["Group"] + sum([[m + " units", m + " value", m + " unit sal.", m + " value sal."] for m in months], [])
    ws_tr.write(3, 0, "Scope", hdr); ws_tr.write(3, 1, "Class", hdr)
    for j, m in enumerate(months):
        for q, lab in enumerate(["units", "value (INR Lakh)", "unit saliency %", "value saliency %"]):
            ws_tr.write(3, 2 + 4 * j + q, "%s %s" % (m, lab), hdr_f)
    for j in range(len(months) - 1):
        ws_tr.write(3, 2 + 4 * len(months) + j, "MoM value change %% %s vs %s" % (months[j + 1], months[j]), hdr_f)
    ws_tr.set_row(3, 40)
    scopes = ["All chains"] + sorted(d["Chain"].unique())
    r = 4
    trend_rows = {}
    for sc in scopes:
        for e in ELIG:
            xr = r + 1
            ws_tr.write_string(r, 0, sc); ws_tr.write_string(r, 1, e)
            prevv = None
            for j, m in enumerate(months):
                sub = d[(d["Month"] == m) & (d["Elig"] == e) & ((d["Chain"] == sc) if sc != "All chains" else True)]
                tot_u = d[(d["Month"] == m) & ((d["Chain"] == sc) if sc != "All chains" else True)]["Units"].sum()
                tot_v = d[(d["Month"] == m) & ((d["Chain"] == sc) if sc != "All chains" else True)]["NSV"].sum()
                cu = xl_col_to_name(2 + 4 * j); cv = xl_col_to_name(3 + 4 * j)
                mh = '"%s"' % m
                if sc == "All chains":
                    fu = '=SUMIFS(rd_units,rd_month,%s,rd_elig,$B%d)' % (mh, xr); fv = '=SUMIFS(rd_value,rd_month,%s,rd_elig,$B%d)' % (mh, xr)
                    du = 'SUMIFS(rd_units,rd_month,%s)' % mh; dv = 'SUMIFS(rd_value,rd_month,%s)' % mh
                else:
                    fu = '=SUMIFS(rd_units,rd_month,%s,rd_chain,$A%d,rd_elig,$B%d)' % (mh, xr, xr); fv = '=SUMIFS(rd_value,rd_month,%s,rd_chain,$A%d,rd_elig,$B%d)' % (mh, xr, xr)
                    du = 'SUMIFS(rd_units,rd_month,%s,rd_chain,$A%d)' % (mh, xr); dv = 'SUMIFS(rd_value,rd_month,%s,rd_chain,$A%d)' % (mh, xr)
                ws_tr.write_formula(r, 2 + 4 * j, fu, num0, float(sub["Units"].sum()))
                ws_tr.write_formula(r, 3 + 4 * j, fv, num2, float(sub["NSV"].sum()))
                ws_tr.write_formula(r, 4 + 4 * j, '=IF(%s=0,"",%s%d/%s)' % (du, cu, xr, du), pct, (sub["Units"].sum() / tot_u) if tot_u else "")
                ws_tr.write_formula(r, 5 + 4 * j, '=IF(%s=0,"",%s%d/%s)' % (dv, cv, xr, dv), pct, (sub["NSV"].sum() / tot_v) if tot_v else "")
                if j > 0:
                    pc = xl_col_to_name(3 + 4 * (j - 1))
                    pv = float(d[(d["Month"] == months[j - 1]) & (d["Elig"] == e) & ((d["Chain"] == sc) if sc != "All chains" else True)]["NSV"].sum())
                    cur = float(sub["NSV"].sum())
                    ws_tr.write_formula(r, 2 + 4 * len(months) + j - 1, '=IF(%s%d=0,"",%s%d/%s%d-1)' % (pc, xr, cv, xr, pc, xr), pct, (cur / pv - 1) if pv else "")
            trend_rows[(sc, e)] = r
            r += 1
    ws_tr.freeze_panes(4, 2); ws_tr.set_column(0, 1, 20); ws_tr.set_column(2, 2 + 4 * len(months) + len(months), 12)
    # charts (all chains): contiguous helper block so every spreadsheet app can read it
    hb = r + 2
    ws_tr.write(hb, 0, "Chart data (all chains; linked to the table above)", bold)
    for c, h in enumerate(["Month"] + ["%s value sal." % e for e in ELIG] + ["%s unit sal." % e for e in ELIG]):
        ws_tr.write(hb + 1, c, h, hdr_f)
    for j, m in enumerate(months):
        ws_tr.write_string(hb + 2 + j, 0, m)
        for q, e in enumerate(ELIG):
            rr = trend_rows[("All chains", e)] + 1
            sub_u = d[(d["Month"] == m) & (d["Elig"] == e)]
            ws_tr.write_formula(hb + 2 + j, 1 + q, "=%s%d" % (xl_col_to_name(5 + 4 * j), rr), pct,
                                (sub_u["NSV"].sum() / mtot_v[m]) if mtot_v[m] else "")
            ws_tr.write_formula(hb + 2 + j, 4 + q, "=%s%d" % (xl_col_to_name(4 + 4 * j), rr), pct,
                                (sub_u["Units"].sum() / mtot_u[m]) if mtot_u[m] else "")
    for q, (ttl, c0) in enumerate([("Value saliency %: BOGO eligible vs non-BOGO (all chains)", 1), ("Unit saliency %: BOGO eligible vs non-BOGO (all chains)", 4)]):
        ch_ = wb.add_chart({"type": "column", "subtype": "stacked"})
        for k_, (e, colr) in enumerate(zip(ELIG, ["#2E7D32", "#1F3A5F", "#BDBDBD"])):
            ch_.add_series({"name": e, "categories": ["MoM_Trends", hb + 2, 0, hb + 1 + len(months), 0],
                            "values": ["MoM_Trends", hb + 2, c0 + k_, hb + 1 + len(months), c0 + k_], "fill": {"color": colr}})
        ch_.set_title({"name": ttl}); ch_.set_y_axis({"num_format": "0%"}); ch_.set_size({"width": 560, "height": 300})
        ws_tr.insert_chart(hb + 3 + len(months), 0 if q == 0 else 8, ch_)

    # ---- Checks
    ws_chk.write(0, 0, "Reconciliation and data checks", title)
    ws_chk.write(1, 0, "Green = reconciles / nothing to review. Red = needs your review. Counts and totals are formulas on Raw_Data and the source sheets; "
                       "source totals are read straight from the CSV files by the build script (file names and hashes on Sources).", wrap)
    for c, h in enumerate(["Check", "Month / item", "Workbook value", "Source / expected", "Difference", "Status", "Note"]):
        ws_chk.write(3, c, h, hdr)
    r = 4

    def chk(name, item, wf, wv, sv, note="", pcts=False, tol=0.005, formula_src=None):
        nonlocal r
        xr = r + 1
        ws_chk.write_string(r, 0, name); ws_chk.write_string(r, 1, item)
        f_ = pct if pcts else num4
        ws_chk.write_formula(r, 2, wf, f_, wv)
        if formula_src:
            ws_chk.write_formula(r, 3, formula_src, f_, sv)
        else:
            ws_chk.write_number(r, 3, sv, f_)
        diff = (wv - sv) if isinstance(wv, (int, float)) and isinstance(sv, (int, float)) else ""
        ws_chk.write_formula(r, 4, '=IFERROR(C%d-D%d,"")' % (xr, xr), f_, diff)
        ok = (abs(diff) <= tol) if diff != "" else True
        ws_chk.write_formula(r, 5, '=IF(ABS(E%d)<=%s,"OK","REVIEW")' % (xr, tol), good if ok else bad, "OK" if ok else "REVIEW")
        ws_chk.write_string(r, 6, note)
        r += 1

    ws_chk.write(r, 0, "A. Offtake totals reconcile to the source CSV files", bold); r += 1
    for s in off_src:
        m = s["month"]
        chk("Offtake value, excl. Brand Counter (INR Lakh)", m, '=SUMIFS(rd_value,rd_month,"%s")' % m, float(d.loc[d["Month"] == m, "NSV"].sum()), s["nsv_main"],
            "Source = NSV column summed over rows whose Store Type is not 'Brand Counter' (%s)" % s["file"], tol=0.0001)
        chk("Offtake units, excl. Brand Counter", m, '=SUMIFS(rd_units,rd_month,"%s")' % m, float(d.loc[d["Month"] == m, "Units"].sum()), s["units_main"], "", tol=0.5)
    chk("Offtake value, all months (INR Lakh)", "All", "=SUM(rd_value)", float(d["NSV"].sum()), sum(s["nsv_main"] for s in off_src), "Also ties to the dashboard offtake FY27 total (18,971.69 L for Apr-Aug)", tol=0.0001)
    chk("Chain_Month total equals Raw_Data total", "All", "=Chain_Month!D%d" % (tot + 1), float(cm["V"].sum()), float(d["NSV"].sum()), "", tol=0.0001, formula_src="=SUM(rd_value)")
    ws_chk.write(r, 0, "B. Brand Counter rows left out (project rule: offtake only)", bold); r += 1
    for s in off_src:
        ws_chk.write_string(r, 0, "Brand Counter value left out (INR Lakh)"); ws_chk.write_string(r, 1, s["month"])
        ws_chk.write_number(r, 2, s["nsv_bc"], num4); ws_chk.write_number(r, 3, s["nsv_all"] - s["nsv_main"], num4)
        ws_chk.write_formula(r, 4, "=C%d-D%d" % (r + 1, r + 1), num4, s["nsv_bc"] - (s["nsv_all"] - s["nsv_main"]))
        ws_chk.write_string(r, 5, "INFO"); ws_chk.write_string(r, 6, "%d rows with Store Type 'Brand Counter' in %s; all-rows total %.2f L" % (s["rows_bc"], s["file"], s["nsv_all"]))
        r += 1
    ws_chk.write(r, 0, "C. Missing margins", bold); r += 1
    miss = d[d["Elig"] == "Margin missing"]
    ws_chk.write_string(r, 0, "Rows with no usable article margin"); ws_chk.write_string(r, 1, "All")
    ws_chk.write_formula(r, 2, '=COUNTIF(rd_elig,"Margin missing")', num0, len(miss)); ws_chk.write_number(r, 3, 0, num0)
    ws_chk.write_formula(r, 4, "=C%d-D%d" % (r + 1, r + 1), num0, len(miss))
    ws_chk.write_formula(r, 5, '=IF(C%d=0,"OK","REVIEW")' % (r + 1), good if len(miss) == 0 else bad, "OK" if len(miss) == 0 else "REVIEW")
    ws_chk.write_string(r, 6, "Margin blank or 0 in the offtake file. Shown as 'Margin missing', never as BOGO or non-BOGO."); r += 1
    ws_chk.write_string(r, 0, "Offtake value with no usable margin (INR Lakh)"); ws_chk.write_string(r, 1, "All")
    ws_chk.write_formula(r, 2, '=SUMIFS(rd_value,rd_elig,"Margin missing")', num4, float(miss["NSV"].sum())); r += 1
    ws_chk.write(r, 0, "D. Offer communications", bold); r += 1
    nocomm = int((d["Offer"] == "").sum())
    ws_chk.write_string(r, 0, "Chain-article rows with no offer communication on file"); ws_chk.write_string(r, 1, "All")
    ws_chk.write_formula(r, 2, '=COUNTIF(rd_offer,"")', num0, nocomm); ws_chk.write_formula(r, 3, "=ROWS(rd_offer)", num0, n)
    ws_chk.write_formula(r, 4, "=C%d-D%d" % (r + 1, r + 1), num0, nocomm - n)
    ws_chk.write_formula(r, 5, '=IF(C%d=0,"OK","REVIEW")' % (r + 1), bad if nocomm else good, "REVIEW" if nocomm else "OK")
    pm = sorted({s for p in promo_src for s in p["months"]})
    ws_chk.write_string(r, 6, "Promo files on hand cover only: %s. Offtake months in this workbook: %s. Missing communications are left blank and flagged, not guessed." % (", ".join(pm) or "none", ", ".join(months)))
    r += 1
    for m in months:
        sub = d[d["Month"] == m]
        ws_chk.write_string(r, 0, "Rows with no communication, by month"); ws_chk.write_string(r, 1, m)
        ws_chk.write_formula(r, 2, '=COUNTIFS(rd_month,"%s",rd_offer,"")' % m, num0, int((sub["Offer"] == "").sum()))
        ws_chk.write_formula(r, 3, '=COUNTIF(rd_month,"%s")' % m, num0, len(sub)); r += 1
    ws_chk.write(r, 0, "E. Distributor secondary match", bold); r += 1
    nodq = d[d["DistQty"] <= 0]
    ws_chk.write_string(r, 0, "Chain-article rows with no distributor quantity"); ws_chk.write_string(r, 1, "All")
    ws_chk.write_formula(r, 2, '=COUNTIF(rd_dq,0)', num0, len(nodq)); ws_chk.write_formula(r, 3, "=ROWS(rd_dq)", num0, n)
    ws_chk.write_string(r, 6, "Quantity exists only in the distributor register (Jul-Aug); the Apr-Jun distributor file has value but no quantity, so no billed margin can be calculated for those months."); r += 1
    for m in months:
        sub = d[d["Month"] == m]
        ws_chk.write_string(r, 0, "Rows matched to distributor quantity, by month"); ws_chk.write_string(r, 1, m)
        ws_chk.write_formula(r, 2, '=COUNTIFS(rd_month,"%s",rd_dq,">0")' % m, num0, int((sub["DistQty"] > 0).sum()))
        ws_chk.write_formula(r, 3, '=COUNTIF(rd_month,"%s")' % m, num0, len(sub)); r += 1
    outl = int(sum(1 for v in d["BM"] if v != "" and (v < 0 or v > 0.9)))
    ws_chk.write_string(r, 0, "Billed margin outside 0-90% (rows)"); ws_chk.write_string(r, 1, "All")
    ws_chk.write_formula(r, 2, '=SUMPRODUCT((rd_bm<>"")*((rd_bm<0)+(rd_bm>0.9)>0))', num0, outl)
    ws_chk.write_formula(r, 5, '=IF(C%d=0,"OK","REVIEW")' % (r + 1), bad if outl else good, "REVIEW" if outl else "OK")
    ws_chk.write_string(r, 6, "Calculated from distributor NSV and quantity against offtake MRP; outliers usually mean a unit-of-sale or billing-basis difference. Listed so you can judge, not removed."); r += 1
    ws_chk.write_string(r, 0, "Register rows not counted (billing basis not clearly ex-GST)"); ws_chk.write_string(r, 1, "All")
    ws_chk.write_formula(r, 2, '=COUNTIF(sd_inc,"N")', num0, int((reg["Include"] == "N").sum()) if not reg.empty else 0)
    ws_chk.write_string(r, 6, "Billing basis 'Invoice value' / 'Item amount' may include GST; left out of the margin calculation until you confirm."); r += 1
    ws_chk.write_string(r, 0, "Register rows with no EAN"); ws_chk.write_string(r, 1, "All")
    ws_chk.write_formula(r, 2, '=COUNTIF(sd_ean,"")', num0, int((reg["EANs"] == "").sum()) if not reg.empty else 0)
    ws_chk.write_string(r, 6, "Cannot be matched to an article."); r += 1
    ws_chk.write(r, 0, "F. Duplicate mappings", bold); r += 1
    dup = d.groupby(["Month", "Chain", "EANs"]).size()
    ws_chk.write_string(r, 0, "Month-chain-EAN keys that appear on more than one row"); ws_chk.write_string(r, 1, "All")
    ws_chk.write_number(r, 2, int((dup > 1).sum()), num0)
    ws_chk.write_string(r, 6, "Same chain and article with more than one margin (or description) in the same month; each margin is kept on its own row. Listed on Review_List. Script-computed from the source files."); r += 1
    pd_dup = int((promo.groupby(["Month", "ChainC", "EANs"]).size() > 1).sum()) if not promo.empty else 0
    ws_chk.write_string(r, 0, "Promo keys with more than one offer line"); ws_chk.write_string(r, 1, "All")
    ws_chk.write_formula(r, 2, '=SUMPRODUCT(--(COUNTIF(sp_key,sp_key)>1))', num0, int(sum(v for v in promo.groupby(["Month", "ChainC", "EANs"]).size() if v > 1)) if not promo.empty else 0)
    ws_chk.write_string(r, 6, "Only the first matching offer is shown on Raw_Data; the others are on Source_Promo."); r += 1
    ws_chk.write(r, 0, "G. Summaries reconcile to Raw_Data", bold); r += 1
    for sh, (first_x, last_x, off) in sum_totals.items():
        tcol_v = xl_col_to_name(off + 7); tcol_u = xl_col_to_name(off + 6)
        for lab, tc, rng, fmt_, val in (("value", tcol_v, "rd_value", num4, float(d["NSV"].sum())), ("units", tcol_u, "rd_units", num0, float(d["Units"].sum()))):
            ws_chk.write_string(r, 0, "%s: segment %s total vs Raw_Data" % (sh, lab)); ws_chk.write_string(r, 1, "All")
            ws_chk.write_formula(r, 2, "=SUM(%s!%s%d:%s%d)" % (sh, tc, first_x, tc, last_x), fmt_, val)
            ws_chk.write_formula(r, 3, "=SUM(%s)" % rng, fmt_, val)
            ws_chk.write_formula(r, 4, "=C%d-D%d" % (r + 1, r + 1), fmt_, 0)
            ws_chk.write_formula(r, 5, '=IF(ABS(E%d)<=0.5,"OK","REVIEW")' % (r + 1), good, "OK"); r += 1
    ws_chk.set_column(0, 0, 52); ws_chk.set_column(1, 1, 14); ws_chk.set_column(2, 5, 17); ws_chk.set_column(6, 6, 110)
    ws_chk.freeze_panes(4, 0)

    # ---- fill the 'total of rows' cells on Sum_ sheets now that rows are known
    # (written above with value 0; rewrite with proper values)
    # ---- Review_List
    ws_rev.write(0, 0, "Items for your review (script-computed from the source files)", title)
    r = 2
    ws_rev.write(r, 0, "1. Same month, chain and article with more than one margin or description", bold); r += 1
    for c, h in enumerate(["Month", "Chain", "EAN", "Margins found", "Descriptions found", "Rows", "Offtake value (INR Lakh)"]):
        ws_rev.write(r, c, h, hdr)
    r += 1
    multi = d.groupby(["Month", "Chain", "EANs"]).agg(M=("Margin", lambda s: ", ".join("%.3f" % v for v in sorted(set(s.dropna())))),
                                                      Ds=("Desc", lambda s: len(set(s))), Rn=("Margin", "size"), V=("NSV", "sum")).reset_index()
    multi = multi[multi["Rn"] > 1].sort_values("V", ascending=False)
    for _, x in multi.iterrows():
        ws_rev.write_string(r, 0, x["Month"]); ws_rev.write_string(r, 1, x["Chain"]); ws_rev.write_string(r, 2, x["EANs"])
        ws_rev.write_string(r, 3, x["M"]); ws_rev.write_number(r, 4, int(x["Ds"])); ws_rev.write_number(r, 5, int(x["Rn"])); ws_rev.write_number(r, 6, float(x["V"]), num4)
        r += 1
    r += 1
    ws_rev.write(r, 0, "2. Distributor register chains with no offtake chain (unmatched, Jul-Aug)", bold); r += 1
    for c, h in enumerate(["Register chain (canonical)", "Rows", "NSV (INR)", "Months"]):
        ws_rev.write(r, c, h, hdr)
    r += 1
    offchains = set(d["Chain"])
    if not reg.empty:
        un = reg[~reg["ChainC"].isin(offchains)].groupby(reg["ChainC"].fillna("(blank)")).agg(R=("NSVr", "size"), V=("NSVr", "sum"), Ms=("Month", lambda s: ", ".join(sorted(set(s))))).reset_index()
        for _, x in un.sort_values("V", ascending=False).iterrows():
            ws_rev.write_string(r, 0, str(x["ChainC"])); ws_rev.write_number(r, 1, int(x["R"])); ws_rev.write_number(r, 2, float(x["V"]), num0); ws_rev.write_string(r, 3, x["Ms"]); r += 1
    r += 1
    ws_rev.write(r, 0, "3. Offtake chains with no distributor-register line (no billed margin possible)", bold); r += 1
    for c, h in enumerate(["Offtake chain", "Offtake value (INR Lakh)", "Months"]):
        ws_rev.write(r, c, h, hdr)
    r += 1
    regchains = set(reg["ChainC"].dropna()) if not reg.empty else set()
    for chn, x in d[~d["Chain"].isin(regchains)].groupby("Chain").agg(V=("NSV", "sum"), Ms=("Month", lambda s: ", ".join(sorted(set(s), key=morder)))).sort_values("V", ascending=False).iterrows():
        ws_rev.write_string(r, 0, chn); ws_rev.write_number(r, 1, float(x["V"]), num4); ws_rev.write_string(r, 2, x["Ms"]); r += 1
    r += 1
    ws_rev.write(r, 0, "4. Chain names merged to one governed name (source spelling -> name used)", bold); r += 1
    for c, h in enumerate(["Source spelling", "Used in workbook"]):
        ws_rev.write(r, c, h, hdr)
    r += 1
    pairs = a[["Chain Name", "Chain"]].drop_duplicates()
    for _, x in pairs[pairs["Chain Name"] != pairs["Chain"]].sort_values("Chain").iterrows():
        ws_rev.write_string(r, 0, repr(x["Chain Name"])); ws_rev.write_string(r, 1, str(x["Chain"])); r += 1
    r += 1
    ws_rev.write(r, 0, "5. Segment spellings that differ only by letter case (merged to the most used spelling)", bold); r += 1
    for c, h in enumerate(["Field", "Source spelling", "Used in workbook"]):
        ws_rev.write(r, c, h, hdr)
    r += 1
    for col, orig, new_ in a.attrs.get("merges", []):
        ws_rev.write_string(r, 0, "Subcategory" if col == "Sub_category" else col); ws_rev.write_string(r, 1, str(orig)); ws_rev.write_string(r, 2, str(new_)); r += 1
    ws_rev.set_column(0, 0, 40); ws_rev.set_column(1, 6, 22)

    # ---- Sources
    ws_src.write(0, 0, "Source files (read-only; not changed)", title)
    r = 2
    for c, h in enumerate(["File", "Month", "Rows", "SHA-256", "Offtake value all rows (INR Lakh)", "Brand Counter value (INR Lakh)", "Value used (INR Lakh)"]):
        ws_src.write(r, c, h, hdr)
    r += 1
    for s in off_src:
        for c, v in enumerate([s["file"], s["month"], s["rows"], s["sha256"], s["nsv_all"], s["nsv_bc"], s["nsv_main"]]):
            ws_src.write(r, c, v)
        r += 1
    r += 1
    for lab, lst in (("Distributor register", reg_src), ("Promotional communication", promo_src)):
        ws_src.write(r, 0, lab, bold); r += 1
        for s in lst:
            ws_src.write(r, 0, s["file"]); ws_src.write(r, 2, s["rows"]); ws_src.write(r, 3, s["sha256"])
            if s.get("months"):
                ws_src.write(r, 1, ", ".join(s["months"]))
            r += 1
        if not lst:
            ws_src.write(r, 0, "none found"); r += 1
    r += 1
    ws_src.write(r, 0, "The store-level offtake (%s rows incl. Brand Counter) is not copied in: it is over Excel's 1,048,576-row limit. "
                       "Raw_Data holds it summed to month x chain x article x margin, built by scripts/build_bogo_offer_workbook.py; Checks section A ties it back to these files." % "{:,}".format(sum(s["rows"] for s in off_src)), wrap)
    ws_src.set_column(0, 0, 40); ws_src.set_column(1, 2, 12); ws_src.set_column(3, 3, 70); ws_src.set_column(4, 6, 20)

    # ---- README
    ws_read.set_column(0, 0, 140)
    L = [("Chain x article offer-wise offtake deep dive: BOGO eligible vs non-BOGO", title),
         ("Months: %s.  Chains: %d.  Detail rows: %s (month x chain x article x margin).  Offtake value is NSV in INR Lakh; Brand Counter rows are left out." %
          (", ".join(months), d["Chain"].nunique(), "{:,}".format(n)), wrap),
         ("", txt),
         ("HOW TO READ IT", bold),
         ("Raw_Data: one row per month, chain, article and margin. Blue headers = values from the source files; green headers = formulas. Eligibility, billed margin and offer lookups are formulas you can trace.", wrap),
         ("Parameters: the BOGO threshold (yellow cell). Change it and every sheet recalculates.", wrap),
         ("Sum_Chain / Sum_Brand / Sum_Subcategory / Sum_Range / Sum_Pack: BOGO eligible vs non-BOGO units, value and saliency % by month and chain (and by the segment named in the sheet).", wrap),
         ("Offer_Compare: eligibility group x communicated offer type. MoM_Trends: month-on-month, all chains and each chain, with charts. Checks and Review_List: what does not reconcile or needs your call.", wrap),
         ("", txt),
         ("DEFINITIONS", bold),
         ("BOGO eligible = article margin >= the threshold (55% by default, inclusive). It says the margin allows a BOGO. It does NOT say a BOGO was shared or run.", wrap),
         ("BOGO communicated = a BOGO shows in the promotional communication file for the same month, chain and article. Today this is blank for every row (see below).", wrap),
         ("Saliency % = segment units (value) / total units (value) of the same chain in the same month. Unit and value saliency are separate columns.", wrap),
         ("Article margin % = the Margin column of the offtake file for that chain and article, as supplied. Where a chain and article carried more than one margin in a month, each margin has its own row.", wrap),
         ("Distributor-to-chain billed margin % = 1 - (distributor NSV / distributor quantity) / average MRP per unit. NSV and quantity are summed from Source_Distributor (rows with an ex-GST billing basis) at month, chain and EAN. MRP is the offtake MRP value / units. Blank where there is no distributor quantity.", wrap),
         ("", txt),
         ("WHAT IS MISSING (left blank, flagged, not guessed)", bold),
         ("1. Promotional offer communicated: only %s promo file(s) exist (%s). None covers %s, so the offer, date and BOGO-communicated columns are blank for all rows. Every row carries a review flag." %
          (len(promo_src), ", ".join(pm) or "none", ", ".join(months)), warn),
         ("2. Distributor billed margin: the distributor register with quantity covers Jul-Aug only. Apr-Jun distributor data is value only (no quantity), so billed margin is blank for those months.", warn),
         ("3. A separate article margin file was not supplied. The offtake file's Margin column is used and its source is shown on every row.", warn),
         ("", txt),
         ("NEED FROM YOU BEFORE THIS IS FINAL", bold),
         ("a. Confirm the article margin source: is the offtake file's 'Margin' column the article margin you mean? If you have a separate article margin file, send it.", wrap),
         ("b. Send the promotional communication for Apr-Aug (chain, article or EAN, offer, date) in the same layout as promo_mechanics_Sep_2026.csv.", wrap),
         ("c. Confirm the margin basis for the billed margin: on MRP including GST (used here) or on MRP excluding GST. Also confirm how 'Invoice value' / 'Item amount' register lines should be treated (left out for now).", wrap),
         ("d. Send distributor quantity for Apr-Jun, or confirm billed margin can stay blank for those months.", wrap),
         ("e. Confirm the 55% rule is 'greater than or equal to' and applies per chain and article (it does here), and that Brand Counter stays out.", wrap),
         ("f. Confirm pack = the offtake file's Net Weight column, and Offer type = the type of the communicated offer (BOGO, discount %, other).", wrap),
         ("", txt),
         ("Built by scripts/build_bogo_offer_workbook.py from files in PowerBI/RawDataFolders. The .xlsx is git-ignored (chain x article offtake and margins).", wrap)]
    for i, (t, f) in enumerate(L):
        ws_read.write(i, 0, t, f)
    wb.close()
    return {"rows": n, "months": months, "chains": int(d["Chain"].nunique()), "elig_rows": d["Elig"].value_counts().to_dict(),
            "dist_matched": int((d["DistQty"] > 0).sum()), "offers_matched": int((d["Offer"] != "").sum()), "sum_totals": sum_totals}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(ROOT / "work" / "Offtake_BOGO_Offer_DeepDive.xlsx"))
    ap.add_argument("--threshold", type=float, default=0.55)
    a = ap.parse_args()
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    info = build(a.out, a.threshold)
    print(json.dumps(info, indent=1, default=str))
    print("wrote", a.out)
