"""Chain x Article primary billing, Apr-Aug'26 (FY27 so far), by the repo's allocation rule. Writes one Excel file.

The rule is not re-implemented here. It is the one the dashboard already uses, called as-is (build_dashboard_data.detail_records_real):
  * Direct rows keep their own chain ("Chain name for Dashboard").
  * Distributor rows are split to chains by Cont%, taken from the chain-level primary at Ship-To x Brand x Month x Chain
    (Primary_ShipTo_FY25-26_to_May26.csv). A month with no exact entry uses the same Ship-To x Brand's split from the nearest
    month within 3 months (QC-tagged "Mapped (nearest ...)"). Qty, MRP value, NSV and tax scale by Cont%; article MRP does not.
  * Offtake-eligibility gate on distributor rows: Eligible (offtake in M), Eligible_TAT (offtake in M+1), else Not_Eligible and
    reported separately, never forced into a chain.
  * Brand Counter is not touched: this is PRIMARY, and counters are never taken out of primary (CLAUDE.md).
The only change: NSV / MRP are kept to 6 decimals instead of 2 so that the file adds up to the dashboard's own totals
(rounding every one of ~47,000 small groups to 2 decimals loses about Rs 2 L).

  python scripts/build_primary_chain_article.py [--out exports/Primary_Chain_Article_Apr_Aug26.xlsx]
"""
import argparse
import re
import sys
import tempfile
from datetime import date
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import build_dashboard_data as bd  # noqa: E402
import visit_cities as vc  # noqa: E402

MONTHS = {"April": 4, "May": 5, "June": 6, "July": 7, "Aug": 8, "Sept": 9, "Oct": 10, "Nov": 11, "Dec": 12}
NAVY = "10254A"


def ean(v):
    s = re.sub(r"\.0$", "", str(v).strip())
    return s if s.isdigit() else ""


def hdr(ws, row, n, h=30):
    for c in range(1, n + 1):
        x = ws.cell(row=row, column=c)
        x.font, x.fill = Font(bold=True, color="FFFFFF"), PatternFill("solid", fgColor=NAVY)
        x.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
    ws.row_dimensions[row].height = h


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "exports" / "Primary_Chain_Article_Apr_Aug26.xlsx"))
    a = ap.parse_args()
    orig_r2 = bd.r2
    bd.r2 = lambda x, n=2: round(x, 6) if n == 2 else orig_r2(x, n)      # keep precision in the detail rows only
    with tempfile.TemporaryDirectory() as tmp:
        res = bd.detail_records_real(ROOT / "PowerBI" / "RawDataFolders", max_rows=10 ** 9, output_dir=Path(tmp))
    recs, ctot = res[0], res[1]      # res[1] = exact channel totals {FY: {channel: NSV}} (res[2] is the SIS reconciliation)
    bd.r2 = orig_r2
    d = pd.DataFrame(recs)
    d = d[d["FY"] == "FY27"].copy()
    d["Month"] = d["Month"].map(lambda m: date(2026, MONTHS[m], 1))
    d["EAN"] = d["EAN"].map(ean)
    d["PackSize"] = d["PackSize"].map(lambda x: re.sub(r"\.0$", "", str(x)) + " g/ml" if str(x) not in ("None", "nan", "") else "Not stated")
    d = d.groupby(["Month", "Channel", "Chain", "Brand", "Category", "SubCategory", "PackSize", "EAN", "Article"], dropna=False, as_index=False).agg(
        NSV=("NSV", "sum"), MRPS=("MRP", "sum"), Qty=("Qty", "sum"))
    months = sorted(d["Month"].unique())

    # ---- tie-outs to the dashboard's own numbers
    ct = ctot["FY27"]
    by_ch = d.groupby("Channel")["NSV"].sum()
    tie = [(c, float(by_ch.get(c, 0.0)), float(ct.get(c, 0.0))) for c in ("MT", "EB2B", "SIS")]
    assert all(abs(x - y) < 0.05 for _, x, y in tie), tie
    tot = float(d["NSV"].sum())

    # ---- offtake (MT, Brand Counter out) for the same chain x article x months, same EAN key
    o = vc.load_offtake([m.strftime("%b") for m in months])
    o = o[~o["bc"]].copy()
    o["EAN"] = o["EAN"].map(ean)
    nz = lambda s: re.sub(r"[^a-z0-9]", "", str(s).lower())
    pnames = {nz(c): c for c in d["Chain"].unique()}            # same chain, same spelling as the primary side (e.g. Nykaa FSN -> Nykaa (FSN))
    o["Chain"] = o["Chain"].map(lambda c: pnames.get(nz(bd.canon_chain(c)), bd.canon_chain(c)))
    off = o.groupby(["Chain", "EAN"], as_index=False)["NSV"].sum().rename(columns={"NSV": "Offtake"})
    mt = d[d["Channel"] == "MT"]
    pri = mt.groupby(["Chain", "EAN"], as_index=False).agg(Primary=("NSV", "sum"), Brand=("Brand", "first"), Article=("Article", "first"), SubCategory=("SubCategory", "first"))
    pv = pri.merge(off, on=["Chain", "EAN"], how="outer")
    pv[["Primary", "Offtake"]] = pv[["Primary", "Offtake"]].fillna(0.0)
    pv["Gap"] = pv["Primary"] - pv["Offtake"]
    pv = pv.sort_values("Gap", key=lambda s: -s.abs())

    wb = Workbook()
    rd = wb.active
    rd.title = "README"
    txt = [
        ("Primary billing by Chain x Article, Apr-Aug'26 (FY27 so far)", "t"),
        ("PRIMARY = SAP billing. NSV in Rs lakh. Offtake (chain POS) appears only on sheet Primary_vs_Offtake: different measure, never one growth rate.", ""),
        ("", ""),
        ("THE RULE (the one the dashboard already uses; called as-is, not re-written)", "h"),
        ("1. Direct billing rows keep their own chain.", ""),
        ("2. Distributor billing rows are split to chains by Cont%: the chain-level primary at Ship-To x Brand x Month x Chain. A month with no exact entry uses the same Ship-To x Brand's split from the nearest month within 3 months. Qty, MRP value, NSV and tax scale by Cont%.", ""),
        ("3. Offtake-eligibility gate: Eligible (offtake in the month), Eligible_TAT (offtake next month), else Not_Eligible, reported apart and never forced into a chain (0.07% of distributor NSV, Rs 12.13 L).", ""),
        ("4. Brand Counter is NOT removed: this is primary. Only offtake leaves counters out.", ""),
        ("5. Unmapped distributor rows: 0 (every distributor row found a chain split).", ""),
        ("", ""),
        ("TIE-OUT", "h"),
    ]
    for c, x, y in tie:
        txt.append((f"{c}: this file {x:,.2f} L vs dashboard {y:,.2f} L (difference {x - y:+.3f})", ""))
    txt += [(f"All channels: {tot:,.2f} L vs dashboard FY27 primary {sum(ct.values()):,.2f} L.", ""), ("", ""),
            ("CHECK BEFORE YOU USE IT", "h"),
            ("- MT is the chain view. EB2B and SIS rows (own accounts such as Azorte, Nykaa eB2B, Shoppers Stop) are kept in the data with a Channel column; the By_Chain and Chain_Article sheets show MT only.", ""),
            ("- Jun'26 distributor split borrows the nearest month's Cont% (provisional, Finance-approved 2026-08-09). 6.19% of FY27 primary uses a nearest-month split.", ""),
            ("- Article names differ by chain; the same EAN can carry several names. Article here = the first name for that EAN; EAN is the key.", ""),
            ("- Sep'26 primary is not in the repo (needs primary_article_Sep_26.csv), so this file stops at Aug'26.", "")]
    for i, (t, k) in enumerate(txt, 1):
        c = rd.cell(row=i, column=1, value=t)
        c.alignment = Alignment(wrap_text=True, vertical="top")
        if k == "t":
            c.font = Font(bold=True, size=15, color=NAVY)
        elif k == "h":
            c.font, c.fill = Font(bold=True, color="FFFFFF"), PatternFill("solid", fgColor=NAVY)
    rd.column_dimensions["A"].width = 150

    # ---- By_Chain (MT)
    wc = wb.create_sheet("By_Chain")
    labs = [m.strftime("%b-%y") for m in months]
    hs = ["Chain"] + labs + ["Apr–Aug total", "Share %"]
    for j, h in enumerate(hs, 1):
        wc.cell(row=1, column=j, value=h)
    hdr(wc, 1, len(hs), 22)
    pc = mt.pivot_table(index="Chain", columns="Month", values="NSV", aggfunc="sum").reindex(columns=months).fillna(0.0)
    pc["T"] = pc.sum(axis=1)
    pc = pc.sort_values("T", ascending=False)
    n = len(pc)
    for i, (ch, row) in enumerate(pc.iterrows(), 2):
        wc.cell(row=i, column=1, value=ch)
        for j, m in enumerate(months, 2):
            wc.cell(row=i, column=j, value=round(float(row[m]), 4)).number_format = "#,##0.0;[Red]-#,##0.0"
        wc.cell(row=i, column=len(months) + 2, value=f"=SUM(B{i}:{chr(65 + len(months))}{i})").number_format = "#,##0.0;[Red]-#,##0.0"
        wc.cell(row=i, column=len(months) + 3, value=f"={chr(66 + len(months))}{i}/{chr(66 + len(months))}${n + 2}").number_format = "0.0%"
    wc.cell(row=n + 2, column=1, value="Total MT").font = Font(bold=True)
    for j in range(2, len(months) + 3):
        x = wc.cell(row=n + 2, column=j, value=f"=SUM({chr(64 + j)}2:{chr(64 + j)}{n + 1})")
        x.number_format, x.font = "#,##0.0", Font(bold=True)
    wc.column_dimensions["A"].width = 26
    wc.freeze_panes = "B2"

    # ---- Chain_Article (MT, wide)
    wa = wb.create_sheet("Chain_Article")
    key = ["Chain", "Brand", "Category", "SubCategory", "PackSize", "EAN", "Article"]
    w = mt.pivot_table(index=key, columns="Month", values="NSV", aggfunc="sum").reindex(columns=months).fillna(0.0).reset_index()
    q = mt.groupby(key)["Qty"].sum().reset_index()
    w = w.merge(q, on=key)
    w["T"] = w[months].sum(axis=1)
    w = w.sort_values(["Chain", "T"], ascending=[True, False])
    hs = ["Chain", "Brand", "Category", "Sub-category", "Pack", "EAN", "Article"] + labs + ["Apr–Aug NSV (₹ L)", "Apr–Aug Qty"]
    for j, h in enumerate(hs, 1):
        wa.cell(row=1, column=j, value=h)
    hdr(wa, 1, len(hs), 30)
    for i, r in enumerate(w.itertuples(index=False), 2):
        vals = list(r[:7]) + [round(float(getattr(r, "_%d" % (k + 7), 0) if False else r[7 + k]), 4) for k in range(len(months))] + [round(float(r[7 + len(months) + 1]), 4), int(r[7 + len(months)])]
        for j, v in enumerate(vals, 1):
            wa.cell(row=i, column=j, value=v)
    for c in range(8, 8 + len(months) + 1):
        for i in range(2, len(w) + 2):
            wa.cell(row=i, column=c).number_format = "#,##0.00;[Red]-#,##0.00"
    for c, ww in zip("ABCDEFG", (22, 14, 12, 18, 10, 16, 44)):
        wa.column_dimensions[c].width = ww
    wa.freeze_panes = "H2"
    wa.auto_filter.ref = f"A1:{chr(64 + len(hs)) if len(hs) < 27 else 'AA'}{len(w) + 1}"

    # ---- long data (all channels)
    wl = wb.create_sheet("Data_long")
    hs = ["Month", "Channel", "Chain", "Brand", "Category", "Sub-category", "Pack", "EAN", "Article", "NSV (₹ L)", "MRP value (₹ L)", "Qty"]
    for j, h in enumerate(hs, 1):
        wl.cell(row=1, column=j, value=h)
    hdr(wl, 1, len(hs), 22)
    for r in d.sort_values(["Month", "Chain", "NSV"], ascending=[True, True, False]).itertuples(index=False):
        wl.append([r.Month, r.Channel, r.Chain, r.Brand, r.Category, r.SubCategory, r.PackSize, r.EAN, r.Article, round(float(r.NSV), 6), round(float(r.MRPS), 6), int(r.Qty)])
    for row in wl.iter_rows(min_row=2, max_row=len(d) + 1, min_col=1, max_col=1):
        row[0].number_format = "mmm-yy"
    wl.freeze_panes = "A2"
    wl.auto_filter.ref = f"A1:L{len(d) + 1}"
    for c, ww in zip("ABCDEFGHIJKL", (9, 9, 22, 14, 12, 18, 10, 16, 44, 12, 12, 12)):
        wl.column_dimensions[c].width = ww

    # ---- Primary vs Offtake, chain x article (MT)
    wp = wb.create_sheet("Primary_vs_Offtake")
    wp["A1"] = "Chain x Article, Apr–Aug'26, MT: Primary (SAP billing) vs Offtake (chain POS, Brand Counter out), joined on chain + EAN. The gap is not 'inventory': it also holds timing, returns and coverage. Rows sorted by size of gap."
    wp["A1"].alignment = Alignment(wrap_text=True)
    wp.merge_cells("A1:I1")
    wp.row_dimensions[1].height = 34
    hs = ["Chain", "EAN", "Article", "Brand", "Sub-category", "Primary (₹ L)", "Offtake (₹ L)", "Gap P − O (₹ L)", "Primary ÷ Offtake"]
    for j, h in enumerate(hs, 1):
        wp.cell(row=3, column=j, value=h)
    hdr(wp, 3, len(hs), 28)
    for i, r in enumerate(pv.itertuples(index=False), 4):
        vals = [r.Chain, r.EAN, r.Article if isinstance(r.Article, str) else "(offtake only: no primary billing)", r.Brand if isinstance(r.Brand, str) else "",
                r.SubCategory if isinstance(r.SubCategory, str) else "", round(r.Primary, 4), round(r.Offtake, 4), None, None]
        for j, v in enumerate(vals, 1):
            wp.cell(row=i, column=j, value=v)
        wp.cell(row=i, column=8, value=f"=F{i}-G{i}")
        wp.cell(row=i, column=9, value=f'=IF(G{i}>0,F{i}/G{i},"–")')
        for c in (6, 7, 8):
            wp.cell(row=i, column=c).number_format = "#,##0.00;[Red]-#,##0.00"
        wp.cell(row=i, column=9).number_format = "0.00"
    last = len(pv) + 3
    wp.cell(row=last + 1, column=1, value="Total").font = Font(bold=True)
    for c in "FGH":
        wp[f"{c}{last + 1}"] = f"=SUM({c}4:{c}{last})"
        wp[f"{c}{last + 1}"].number_format = "#,##0.0"
        wp[f"{c}{last + 1}"].font = Font(bold=True)
    for c, ww in zip("ABCDEFGHI", (22, 16, 46, 14, 18, 14, 14, 16, 14)):
        wp.column_dimensions[c].width = ww
    wp.freeze_panes = "A4"
    wp.auto_filter.ref = f"A3:I{last}"
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out)
    print(f"wrote {out}: {len(d)} chain x article x month rows ({d['Chain'].nunique()} chains, {d['EAN'].nunique()} EANs), total {tot:,.2f} L; MT {float(by_ch.get('MT', 0)):,.2f} L")
    print("offtake join: primary-only rows", int(((pv['Offtake'] == 0) & (pv['Primary'] != 0)).sum()), "| offtake-only rows", int(((pv['Primary'] == 0) & (pv['Offtake'] != 0)).sum()), "| total offtake", round(pv['Offtake'].sum(), 2))


if __name__ == "__main__":
    main()
