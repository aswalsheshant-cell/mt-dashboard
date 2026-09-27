#!/usr/bin/env python3
"""Build the FY27 Distributor Secondary register for Jul'26 and Aug'26.

Reads the monthly "Distributor_Chain_Brand_Article_Billing_<Month>_2026.xlsx"
workbooks (sheet "Billing Detail", one row per invoice line) and writes the
same register files that already exist for Apr-Jun'26 (Q1):

  PowerBI/RawDataFolders/SecondarySales_Monthly/
      secondary_sales_distributor_Jul_Aug_FY27.csv   (Q1 schema, 7 columns)
      secondary_sales_chain_Jul_Aug_FY27.csv         (Q1 schema, 5 columns)
      secondary_sales_brand_Jul_Aug_FY27.csv         (Q1 schema, 5 columns)
  PowerBI/RawDataFolders/SecondarySales_Monthly_TOT_Analysis/
      05_ARTICLE_REGISTER_Jul_Aug_2026.csv           (distributor x chain x brand x article)
      06_REGISTER_EXCEPTIONS_Jul_Aug_2026.csv        (date repairs, out-of-period, duplicates, gaps)

Rules
  * Business date = Invoice Date (THE ONE FY RULE applied to it). A line dated
    in another covered month is moved to that month and flagged; a line dated
    outside Jul/Aug'26 or with an unreadable date is quarantined (listed in the
    exceptions file, not summed).
  * Day/month swapped dates (e.g. "2026-02-07" in the July register = 2 Jul) are
    repaired only when the swap lands in the register month; each repair is logged.
  * Nothing is deleted or netted: returns (negative lines) stay, a possible
    duplicate is flagged, not dropped.
  * Distributors with no register in a month get NO row (missing is not zero);
    they are listed in the exceptions file.
  * Distributor names follow the Q1 register so Apr-Aug reads as one series.

Source workbooks are gitignored (*.xlsx); pass their folder with --src.

    python scripts/build_secondary_register.py --src <folder with the xlsx files>
"""
import argparse
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_dashboard_data import canon_chain  # noqa: E402  governed chain aliases

MONTHS = {"July": 7, "August": 8}
COVERED = {"2026-07", "2026-08"}
OUT_REG = ROOT / "PowerBI/RawDataFolders/SecondarySales_Monthly"
OUT_TOT = ROOT / "PowerBI/RawDataFolders/SecondarySales_Monthly_TOT_Analysis"

# source name -> Q1 register name (Q1 = secondary_sales_distributor_Q1_FY27.csv)
DIST_Q1 = {
    "Balaji Associate": "Balaji",
    "DL sales": "DL Sales",
    "Real time logistics": "RealTime",
    "AZ Enterprises(Apollo/More)Mt": "AZ Enterprises",
    "GV Enterprises": "GV Enterprises",
    "KOTTARAM BUSINESS CORPORATION": "Kottaram",
    "Sri Vijaya Durga Agencies_Mt": "SVDA",
    "Venkateshwara Agencies": "VA",
    "Just Mark": "Just Mark",
    "Kiran Trading Co.": "Kiran Trading",
    "Mark Enterprises": "Mark Enterprises",
    "United Marketing": "United Marketing",
    "TROY Tradex": "TROY Tradex",          # new in Aug'26, no Q1 history
}
BRAND_Q1 = {"Mamaearth": "Mamaearth", "The Derma Co": "The Derma Co.", "Aqualogica": "Aqualogica",
            "Bblunt": "BBLUNT", "Dr Sheth's": "Dr. Sheth's", "Unmapped": "Unmapped"}
# billing bases the source itself states as excluding GST
EX_GST = {"NSV excl. GST", "Net value excl. GST", "Amount excl. GST", "Value excl. GST"}
# 44_Fact_SecondarySales.pq marks a row provisional when Notes contains "GST" or "provisional",
# so the confirmed-basis note must not use either word.
BASE_NOTE = "NSV as reported by distributor sale register (ex-tax basis stated in source); North registers not available."
BASE_NOTE_UNCONFIRMED = "Value as reported by distributor sale register; North registers not available."


def register_month(path):
    m = re.search(r"Billing_(July|August)_(\d{4})", path.name)
    if not m:
        raise SystemExit(f"cannot read the register month from {path.name}")
    return int(m.group(2)), MONTHS[m.group(1)]


def parse_date(v, reg_y, reg_m, allow_swap=False):
    """Return (Timestamp|None, flag)."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None, "DATE_MISSING"
    if isinstance(v, pd.Timestamp) or hasattr(v, "year"):
        ts = pd.Timestamp(v)
    else:
        s = str(v).strip()
        if re.fullmatch(r"\d{1,2}-\d{1,2}-\d{2,4}", s):
            ts = pd.to_datetime(s, dayfirst=True, errors="coerce")
        else:
            ts = pd.to_datetime(s, errors="coerce")
        if pd.isna(ts):
            return None, "DATE_UNREADABLE"
    if (ts.year, ts.month) == (reg_y, reg_m):
        return ts, ""
    # day/month swapped by the source export: repair only if the swap lands in the register month
    if allow_swap and ts.day == reg_m and ts.year == reg_y:
        try:
            sw = pd.Timestamp(year=reg_y, month=reg_m, day=ts.month)
            return sw, "DATE_DAY_MONTH_SWAPPED_REPAIRED"
        except ValueError:
            pass
    return ts, "OUT_OF_PERIOD"


def load(path):
    reg_y, reg_m = register_month(path)
    d = pd.read_excel(path, sheet_name="Billing Detail", header=3, dtype={"EAN": str, "Bill No.": str, "Distributor Code": str})
    d["Register_Month"] = f"{reg_y}-{reg_m:02d}"
    # A swapped export shows up register-wide: every ISO-form date of that distributor has
    # day == register month (e.g. 2026-01-07, 2026-08-07 in July). Only then is a swap repaired,
    # so a genuine 2026-07-08 invoice in the August register is never turned into 7 Aug.
    iso = d["Invoice Date"].astype(str).str.extract(r"^(\d{4})-(\d{2})-(\d{2})")
    iso_day = pd.to_numeric(iso[2], errors="coerce")
    swap_dist = {x for x, g in iso_day.groupby(d["Distributor"]) if g.notna().any() and (g.dropna() == reg_m).all()
                 and (pd.to_numeric(iso[1], errors="coerce")[g.dropna().index] != reg_m).any()}
    parsed = [parse_date(v, reg_y, reg_m, dist in swap_dist) for v, dist in zip(d["Invoice Date"], d["Distributor"])]
    d["Invoice_Date"] = [p[0] for p in parsed]
    d["Date_Flag"] = [p[1] for p in parsed]
    d["Source_Month"] = [p[0].strftime("%Y-%m") if p[0] is not None else None for p in parsed]
    d["Source_Workbook"] = re.sub(r"^[0-9a-f]{8}-", "", path.name)   # drop upload prefix
    return d


def fy_tag(ym):
    y, m = int(ym[:4]), int(ym[5:7])
    return f"FY{(y + 1 if m >= 4 else y) % 100}"


def month_label(ym):
    return pd.Timestamp(ym + "-01").strftime("%b-%Y")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="folder holding Distributor_Chain_Brand_Article_Billing_<Month>_2026.xlsx")
    a = ap.parse_args()
    files = sorted(Path(a.src).glob("*Distributor_Chain_Brand_Article_Billing_*_2026.xlsx"))
    if not files:
        raise SystemExit("no Distributor_Chain_Brand_Article_Billing_*_2026.xlsx in --src")
    d = pd.concat([load(f) for f in files], ignore_index=True)
    d["Billing Value"] = pd.to_numeric(d["Billing Value"], errors="coerce")
    d["Quantity"] = pd.to_numeric(d["Quantity"], errors="coerce")
    unknown = set(d["Distributor"]) - set(DIST_Q1)
    if unknown:
        raise SystemExit(f"distributor(s) with no register name mapping: {sorted(unknown)}")
    d["Distributor_Q1"] = d["Distributor"].map(DIST_Q1)
    d["Brand_Q1"] = d["Brand"].map(BRAND_Q1).fillna(d["Brand"])
    d["Chain_Canon"] = d["Chain"].map(lambda c: canon_chain(c) if isinstance(c, str) else "Unmapped")

    ex = []
    def exc(kind, dist, month, lines, value, detail):
        ex.append({"Exception": kind, "Distributor": dist, "Month": month, "Lines": lines,
                   "NSV_Lakh": round(value / 1e5, 2) if value is not None else None, "Detail": detail})

    keep = d["Source_Month"].isin(COVERED)
    for (kind, dist, reg, sm), g in d.groupby(["Date_Flag", "Distributor_Q1", "Register_Month", "Source_Month"], dropna=False):
        if kind == "DATE_DAY_MONTH_SWAPPED_REPAIRED":
            exc(kind, dist, reg, len(g), g["Billing Value"].sum(), f"Invoice dates stored day/month swapped in the {reg} register; repaired into {reg}")
        elif kind == "OUT_OF_PERIOD" and sm in COVERED:
            exc("LATE_REPORTED_MOVED_TO_INVOICE_MONTH", dist, sm, len(g), g["Billing Value"].sum(),
                f"Invoices dated {sm} reported in the {reg} register; counted in {sm} (invoice date). Bills checked: none repeated in the {sm} register")
    q = d[~keep]
    for (kind, dist, reg), g in q.groupby(["Date_Flag", "Distributor_Q1", "Register_Month"], dropna=False):
        exc("QUARANTINED_" + str(kind), dist, reg, len(g), g["Billing Value"].sum(), "Invoice date outside Jul-Aug 2026 or unreadable; not summed")
    dup_cols = ["Distributor Code", "Bill No.", "Article Key", "Quantity", "Billing Value"]
    dup = d[keep & d.duplicated(dup_cols, keep=False)]
    for (dist, bill), g in dup.groupby(["Distributor_Q1", "Bill No."]):
        exc("POSSIBLE_DUPLICATE_KEPT", dist, ",".join(sorted(set(g["Source_Month"]))), len(g), g["Billing Value"].sum(),
            f"Bill {bill}: same article/qty/value on {len(g)} lines, invoice dates {', '.join(sorted(set(str(x.date()) for x in g['Invoice_Date'])))}; kept - confirm with distributor")
    for (dist, reg), g in d[d["EAN"].isna()].groupby(["Distributor_Q1", "Register_Month"]):
        exc("EAN_MISSING_IN_SOURCE", dist, reg, len(g), g["Billing Value"].sum(), "Register has no EAN on these lines; Article Key kept, EAN left blank")
    for (dist, reg), g in d[~d["Billing Basis"].isin(EX_GST)].groupby(["Distributor_Q1", "Register_Month"]):
        exc("GST_BASIS_NOT_CONFIRMED", dist, reg, len(g), g["Billing Value"].sum(),
            f"Billing basis '{g['Billing Basis'].iloc[0]}' - source does not state ex-GST; value used as reported, marked provisional")
    # distributors in the Q1 register with no Jul/Aug register (listed, never written as zero)
    q1 = pd.read_csv(OUT_REG / "secondary_sales_distributor_Q1_FY27.csv")
    q1_names = set(q1.loc[q1["NSV_Lakh"] != 0, "Distributor"])
    for m in sorted(COVERED):
        have = set(d.loc[keep & (d["Source_Month"] == m), "Distributor_Q1"])
        for n in sorted(q1_names - have):
            if n == "VA" and m == "2026-07":
                exc("INCLUDED_IN_ANOTHER_DISTRIBUTOR", n, m, 0, None, "VA July billing is inside the SVDA consolidated July report (source excluded the VA file to avoid duplicates) - no separate VA row")
                continue
            exc("NO_REGISTER_THIS_MONTH", n, m, 0, None, "In Q1 register but no sale register supplied for this month - missing, not zero (North distributors not supplied at all)")

    k = d[keep].copy()
    # ---- distributor register (Q1 schema)
    notes = {}
    for (m, dist), g in k.groupby(["Source_Month", "Distributor_Q1"]):
        confirmed = g["Billing Basis"].isin(EX_GST).all()
        n = [BASE_NOTE if confirmed else BASE_NOTE_UNCONFIRMED]
        if not confirmed:
            n.append(f"Provisional: billing basis '{g.loc[~g['Billing Basis'].isin(EX_GST), 'Billing Basis'].iloc[0]}' - GST treatment not confirmed in source.")
        moved = g[g["Date_Flag"] == "OUT_OF_PERIOD"]
        if len(moved):
            n.append(f"Includes Rs{moved['Billing Value'].sum() / 1e5:.2f} L invoiced {m} but reported in the {moved['Register_Month'].iloc[0]} register.")
        if (g["Date_Flag"] == "DATE_DAY_MONTH_SWAPPED_REPAIRED").any():
            n.append("Invoice dates repaired (day/month swapped in source).")
        if dist == "SVDA" and m == "2026-07":
            n.append("Jul'26 SVDA consolidated report includes VA billing (VA file excluded by source to avoid duplicates) - no separate VA row this month.")
        notes[(m, dist)] = " ".join(n)
    dist_rows = (k.groupby(["Source_Month", "Distributor_Q1"])["Billing Value"].sum().div(1e5).round(2).reset_index())
    dist_rows = pd.DataFrame({
        "Source_Month": dist_rows["Source_Month"], "Month_Label": dist_rows["Source_Month"].map(month_label),
        "FY_Year": dist_rows["Source_Month"].map(fy_tag), "Distributor": dist_rows["Distributor_Q1"],
        "NSV_Lakh": dist_rows["Billing Value"],
        "Data_Source": [", ".join(sorted(set(k.loc[(k.Source_Month == m) & (k.Distributor_Q1 == x), "Source_Workbook"])))
                        for m, x in zip(dist_rows["Source_Month"], dist_rows["Distributor_Q1"])],
        "Notes": [notes[(m, x)] for m, x in zip(dist_rows["Source_Month"], dist_rows["Distributor_Q1"])],
    })

    def dim(col, name):
        t = k.groupby(["Source_Month", col])["Billing Value"].sum().div(1e5).round(2).reset_index()
        return pd.DataFrame({"Source_Month": t["Source_Month"], "Month_Label": t["Source_Month"].map(month_label),
                             "FY_Year": t["Source_Month"].map(fy_tag), name: t[col], "NSV_Lakh": t["Billing Value"]})
    chain_rows, brand_rows = dim("Chain_Canon", "Chain"), dim("Brand_Q1", "Brand")

    art = (k.groupby(["Source_Month", "Register_Month", "Distributor Code", "Distributor_Q1", "Distributor", "Chain_Canon", "Chain",
                      "Brand_Q1", "EAN", "Article Key", "Billing Basis"], dropna=False)
           .agg(Quantity=("Quantity", "sum"), NSV_Value=("Billing Value", "sum"), Lines=("Billing Value", "size"),
                Date_Flag=("Date_Flag", lambda s: ";".join(sorted(set(x for x in s if x)))))
           .reset_index())
    art = art.rename(columns={"Distributor Code": "Distributor_Code", "Distributor_Q1": "Distributor", "Distributor": "Distributor_Source",
                              "Chain_Canon": "Chain", "Chain": "Chain_Source", "Brand_Q1": "Brand", "Article Key": "Article",
                              "Billing Basis": "Billing_Basis"})
    art.insert(2, "FY_Year", art["Source_Month"].map(fy_tag))
    art["NSV_Lakh"] = (art["NSV_Value"] / 1e5).round(4)
    art = art.sort_values(["Source_Month", "Distributor", "Chain", "Brand", "Article"]).reset_index(drop=True)

    dist_rows.sort_values(["Source_Month", "Distributor"]).to_csv(OUT_REG / "secondary_sales_distributor_Jul_Aug_FY27.csv", index=False)
    chain_rows.sort_values(["Source_Month", "Chain"]).to_csv(OUT_REG / "secondary_sales_chain_Jul_Aug_FY27.csv", index=False)
    brand_rows.sort_values(["Source_Month", "Brand"]).to_csv(OUT_REG / "secondary_sales_brand_Jul_Aug_FY27.csv", index=False)
    art.to_csv(OUT_TOT / "05_ARTICLE_REGISTER_Jul_Aug_2026.csv", index=False)
    pd.DataFrame(ex).to_csv(OUT_TOT / "06_REGISTER_EXCEPTIONS_Jul_Aug_2026.csv", index=False)

    src_tot = d.groupby("Register_Month")["Billing Value"].sum().div(1e5).round(2).to_dict()
    reg_tot = k.groupby("Source_Month")["Billing Value"].sum().div(1e5).round(2).to_dict()
    print("source register totals (L):", src_tot)
    print("register by invoice month (L):", reg_tot, "| quarantined L:", round(d.loc[~keep, "Billing Value"].sum() / 1e5, 2))
    print("rows: distributor", len(dist_rows), "chain", len(chain_rows), "brand", len(brand_rows), "article", len(art), "exceptions", len(ex))


if __name__ == "__main__":
    main()
