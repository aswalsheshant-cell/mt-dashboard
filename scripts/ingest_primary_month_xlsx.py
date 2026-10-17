#!/usr/bin/env python3
"""Map a monthly MT Primary billing workbook (the "MTD-Primary-<Mon>'<YY>" sheet, raw SAP
columns plus the team's lookup columns) to the 24-column Primary_Article_Monthly schema,
so the normal `--detail-only` build picks the month up. First used for Sep'26.

Usage:
    python scripts/ingest_primary_month_xlsx.py --src "<workbook>.xlsx" --month Sep_26

Source column -> target column (all rows kept, signed values kept, nothing filtered or deduplicated,
exactly as the Aug'26 ingest does; the pipeline nets returns by summing signed values):
  Chanel -> Channel                      Customer master 2 -> Chain name for Dashboard
  Inv. Date -> Inv. Date (ISO date)      Cust-SAP Code, Ship-To Name, EAN No., Description, Inv Qty,
  MRP Rate -> MRP                        Inv. Net value(LOC), Inv. Tax Amount(LOC), MTD-Sale type,
  MRP Value -> Total MRP sales           PO Type -> same name
  TOT% Round -> Avg Tot                  lower-case `zone` / `state` -> Zone / State (the sheet's upper-case
  Category -> category                   Zone/State columns hold a different, territory-level split and do not
                                         match the Aug'26 file; the lower-case pair matches it 100%)
  brand, net_content, PPT Category, sub_category, range: looked up by EAN from the months already loaded
  (the workbook does not carry them). `brand` uses the existing spelling ("The Derma Co.", "BBLUNT").
  An EAN not seen before keeps net_content / PPT Category / sub_category / range BLANK and is listed in the
  report: nothing is guessed.

Checks printed (and the run fails on a hard error): required columns, a single month, invoice dates inside
the month, row count and NSV vs the source, and NSV vs the workbook's own Summary pivot when it is present.
The raw workbook is only read. The output CSV is a restricted source: keep it out of Git.
"""
from __future__ import annotations

import argparse
import glob
import os
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parent.parent
PRIMARY_DIR = REPO / "PowerBI" / "RawDataFolders" / "Primary_Article_Monthly"
REFERENCE = PRIMARY_DIR / "primary_article_Aug_26.csv"
MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

COLUMN_MAP = {
    "Chanel": "Channel", "Inv. Date": "Inv. Date", "Cust-SAP Code": "Cust-SAP Code", "Ship-To Name": "Ship To Name",
    "EAN No.": "EAN No.", "Description": "Description", "MRP Rate": "MRP", "Inv Qty": "Inv Qty",
    "Inv. Net value(LOC)": "Inv. Net value(LOC)", "Inv. Tax Amount(LOC)": "Inv. Tax Amount(LOC)",
    "MRP Value": "Total MRP sales", "TOT% Round": "Avg Tot", "MTD-Sale type": "MTD-Sale type", "PO Type": "PO Type",
    "Customer master 2": "Chain name for Dashboard", "zone": "Zone", "state": "State", "Category": "category",
}
LOOKUP_COLS = ["brand", "net_content", "PPT Category", "sub_category", "range"]


def fy_tag(year, month):
    """THE ONE FY RULE: Apr-Dec of Y is FY(Y+1); Jan-Mar of Y is FY(Y)."""
    return f"FY{(year + 1 if month >= 4 else year) % 100:02d}"


def parse_month(arg):
    mon, yy = arg.split("_")
    m = MON.index(mon[:3].title()) + 1
    return 2000 + int(yy), m


def _file_month(path):
    mon, yy = Path(path).stem.replace("primary_article_", "").split("_")
    return 2000 + int(yy), MON.index(mon[:3].title()) + 1


def ean_master(before):
    """Attributes by EAN from files for months STRICTLY EARLIER than `before` (year, month), so a re-run of the same
    month, or a back-fill, never reads its own output or a later month and the new-EAN list stays stable."""
    frames = []
    for f in sorted(glob.glob(str(PRIMARY_DIR / "primary_article_*.csv"))):
        try:
            if _file_month(f) >= before:
                continue
        except (ValueError, IndexError):
            continue
        frames.append(pd.read_csv(f, usecols=["EAN No."] + LOOKUP_COLS, low_memory=False))
    m = pd.concat(frames).dropna(subset=["EAN No."])
    m["EAN No."] = pd.to_numeric(m["EAN No."], errors="coerce")
    return m.dropna(subset=["EAN No."]).drop_duplicates("EAN No.", keep="last").set_index("EAN No.")


def pivot_control(xl, nsv):
    """Independent control: the workbook's own Summary pivot. Returns (found_pivot_sheet, grand_total_matches)."""
    sheet = next((s for s in xl.sheet_names if s.startswith("Summary")), None)
    if sheet is None:
        return False, False
    tot = xl.parse(sheet, header=None).apply(pd.to_numeric, errors="coerce").stack()
    return True, bool(((tot - nsv).abs() < 1).any())


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--src", required=True, type=Path)
    ap.add_argument("--month", required=True, help="for example Sep_26")
    ap.add_argument("--out-dir", type=Path, default=PRIMARY_DIR)
    ap.add_argument("--control-total", type=float, help="source NSV in rupees from another control, required when the workbook has no Summary pivot")
    a = ap.parse_args(argv)

    y, m = parse_month(a.month)
    label, fy = f"{MON[m - 1]}'{y % 100:02d}", fy_tag(y, m)
    expected = list(pd.read_csv(REFERENCE, nrows=0).columns)

    xl = pd.ExcelFile(a.src, engine="openpyxl")
    sheet = next((s for s in xl.sheet_names if s.upper().startswith("MTD-PRIMARY")), None)
    if sheet is None:
        print(f"FAIL: no sheet starting 'MTD-Primary' in {a.src.name}: {xl.sheet_names}")
        return 1
    src = xl.parse(sheet)
    need = list(COLUMN_MAP) + ["Division Desc."]
    missing = [c for c in need if c not in src.columns]
    if missing:
        print(f"FAIL: source is missing columns {missing}")
        return 1

    blank = src[src["Inv. Date"].isna()]
    if len(blank):
        value_cols = [c for c in ("Inv. Net value(LOC)", "Inv. Tax Amount(LOC)", "Inv Qty") if c in src.columns]
        has_value = blank[value_cols].apply(pd.to_numeric, errors="coerce").fillna(0).abs().sum(axis=1) > 0
        has_item = blank["EAN No."].notna() | blank["Ship-To Name"].notna()
        if (has_value | has_item).any():
            print(f"FAIL: {int((has_value | has_item).sum())} rows have no invoice date but carry value, quantity, EAN or ship-to; "
                  "fix the source, they would otherwise be dropped silently")
            return 1
        print(f"Note: {len(blank)} fully empty row(s) with no invoice date ignored (no value, quantity, EAN or ship-to).")
        src = src[src["Inv. Date"].notna()].copy()
    src["Inv. Date"] = pd.to_datetime(src["Inv. Date"])
    bad_dates = src[(src["Inv. Date"].dt.year != y) | (src["Inv. Date"].dt.month != m)]
    if len(bad_dates):
        print(f"FAIL: {len(bad_dates)} rows have invoice dates outside {label}")
        return 1

    out = src[list(COLUMN_MAP)].rename(columns=COLUMN_MAP)
    out["Inv. Date"] = out["Inv. Date"].dt.strftime("%Y-%m-%d")
    out["FY"], out["Month"] = fy, label
    ean = pd.to_numeric(src["EAN No."], errors="coerce")
    master = ean_master((y, m))
    look = master.reindex(ean.values)[LOOKUP_COLS].reset_index(drop=True)
    for c in LOOKUP_COLS:
        out[c] = look[c].values
    # brand for an EAN not seen before: use the workbook's Division Desc., written the way existing months spell it
    spell = (src.assign(e=ean).join(master["brand"].rename("b"), on="e").dropna(subset=["b"])
             .groupby("Division Desc.")["b"].agg(lambda s: s.mode().iat[0]).to_dict())
    nb = out["brand"].isna()
    out.loc[nb, "brand"] = src.loc[nb.values, "Division Desc."].map(lambda d: spell.get(d, d)).values
    new_ean = src[~ean.isin(master.index).values]
    out = out[expected]

    # checks
    nsv_src = src["Inv. Net value(LOC)"].sum()
    nsv_out = out["Inv. Net value(LOC)"].sum()
    if len(out) != len(src) or abs(nsv_src - nsv_out) > 0.01:
        print(f"FAIL: rows/value did not survive: {len(src)} -> {len(out)}, {nsv_src} -> {nsv_out}")
        return 1
    blanks = {c: int(out[c].isna().sum()) for c in ("Chain name for Dashboard", "Zone", "State", "category", "Channel") if out[c].isna().any()}
    if blanks:
        print(f"FAIL: blanks in required columns: {blanks}")
        return 1

    found, ties = pivot_control(xl, nsv_src)
    if found and not ties:
        print(f"FAIL: the workbook's Summary pivot does not contain a grand total equal to the source NSV {nsv_src:,.2f}; nothing written")
        return 1
    if not found:
        if a.control_total is None:
            print("FAIL: no Summary pivot in the workbook; pass --control-total <rupees> from another control; nothing written")
            return 1
        if abs(a.control_total - nsv_src) > 1:
            print(f"FAIL: --control-total {a.control_total:,.2f} != source NSV {nsv_src:,.2f}; nothing written")
            return 1

    a.out_dir.mkdir(parents=True, exist_ok=True)
    target = a.out_dir / f"primary_article_{a.month}.csv"
    tmp = target.with_suffix(".csv.tmp")
    out.to_csv(tmp, index=False)
    os.replace(tmp, target)                     # the destination is replaced only after every check passed

    print(f"Wrote {target}")
    print(f"{label} ({fy}): {len(out):,} rows; NSV {nsv_out / 1e5:,.2f} L (all channels, signed, nothing filtered)")
    print((out.groupby("Channel")["Inv. Net value(LOC)"].sum() / 1e5).round(2).to_string())
    print("Ties to the workbook's own Summary pivot grand total." if found else "Ties to the supplied --control-total.")
    if len(new_ean):
        e = new_ean.assign(EAN=new_ean["EAN No."]).drop_duplicates("EAN")[["EAN", "Description"]]
        print(f"NEW EANs not in earlier months ({len(e)}); net_content / PPT Category / sub_category / range left blank:")
        print(e.to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
