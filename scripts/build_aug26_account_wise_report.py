#!/usr/bin/env python3
"""
Aug'26 account-wise Excel report, built from data/monthly/Aug26_primary_detailed.csv.

Two things requested directly from this file:
  1. An account/chain-wise NSV breakdown (this is the raw Aug'26 detailed invoice
     export, NOT the governed allocation output -- see the caution below).
  2. Article-wise GST input (Inv. Tax Amount(LOC)), referenced directly off this
     file's own column of that name.

IMPORTANT -- why "Chain name" is not simply trustworthy for Dist. rows:
For PO Type == "Direct" rows, "Chain name" IS the real retail chain (Reliance
Retail, Nykaa, Apollo, D-Mart, ...) -- safe to group by directly.
For PO Type == "Dist." rows, "Chain name" is verifiably the DISTRIBUTOR's own
name (e.g. "Sancus Networks Private Limited-RMT", "G.V Enterprises"), not a
retail chain -- grouping by it would fabricate fake "chains" named after
distributors. This matches the exact "Customer name 2" caution already
written into scripts/aug26_data_readiness_gate.py: this file's
"Customer Name.1" column is that same field (e.g. "Dmart/Apollo/H&G/Lulu/Max
Hyper/Pothys" for one distributor's pooled billing). That script treats it as
DIAGNOSTIC ONLY -- never an allocation weight -- until the data owner confirms
what the field means (does it list every chain the pool covers, in what
proportion?). This report follows the same rule: Dist. rows are reported at
their own DISTRIBUTOR identity (never invented as a chain), with the pooled
"Customer Name.1" hint shown in its own sheet for visibility, not blended into
the account-wise totals.

Usage:
    python scripts/build_aug26_account_wise_report.py \
        --src data/monthly/Aug26_primary_detailed.csv \
        --out <path>.xlsx
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REQUIRED_COLS = {
    "PO Type", "Chain name", "Customer Name", "Customer Name.1",
    "Inv. Net value(LOC)", "Inv. Tax Amount(LOC)", "Inv Qty", "Total MRP sales",
    "Article Code", "Description", "brand", "category", "Zone", "State", "Month",
}


def load(src):
    df = pd.read_csv(src, low_memory=False)
    missing = REQUIRED_COLS - set(df.columns)
    if missing:
        raise SystemExit(f"Missing expected columns in {src}: {sorted(missing)}")
    for col in ("Inv. Net value(LOC)", "Inv. Tax Amount(LOC)", "Inv Qty", "Total MRP sales"):
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    return df


def account_wise_summary(df):
    """Direct rows -> real Chain name. Dist. rows -> the distributor's OWN
    identity (Customer Name), never the pooled Customer Name.1 hint. This is
    reporting-only visibility, not the governed allocation
    (scripts/aug26_data_readiness_gate.py's allocate_primary() remains the
    source of truth for chain-split NSV)."""
    d = df.copy()
    d["Account"] = d["Chain name"].where(d["PO Type"] == "Direct", d["Customer Name"])
    d["Account_Type"] = d["PO Type"].map({"Direct": "Direct (real chain)", "Dist.": "Distributor (NOT a chain)"})
    g = d.groupby(["Account", "Account_Type"], as_index=False).agg(
        NSV_LOC=("Inv. Net value(LOC)", "sum"),
        Tax_LOC=("Inv. Tax Amount(LOC)", "sum"),
        MRP_Sales=("Total MRP sales", "sum"),
        Qty=("Inv Qty", "sum"),
        Invoice_Lines=("Inv. Net value(LOC)", "count"),
    ).sort_values("NSV_LOC", ascending=False)
    g["NSV_Lakh"] = (g["NSV_LOC"] / 1e5).round(2)
    return g


def gst_input_article_wise(df):
    """GST input (Inv. Tax Amount(LOC)) by article -- exactly the column and
    grain named in the request: article-wise GST input from the primary sheet."""
    g = df.groupby(["Article Code", "Description", "brand", "category"], as_index=False).agg(
        NSV_LOC=("Inv. Net value(LOC)", "sum"),
        GST_Input_Tax_LOC=("Inv. Tax Amount(LOC)", "sum"),
        Qty=("Inv Qty", "sum"),
        Invoice_Lines=("Inv. Net value(LOC)", "count"),
    ).sort_values("GST_Input_Tax_LOC", ascending=False)
    g["Effective_Tax_Rate_pct"] = (g["GST_Input_Tax_LOC"] / g["NSV_LOC"].replace(0, np.nan) * 100).round(2)
    return g


def dist_pooled_hints(df):
    """Diagnostic-only view of Dist. rows' pooled 'Customer Name.1' hint.
    NEVER used as an allocation weight -- see module docstring."""
    dist = df[df["PO Type"] == "Dist."].copy()
    g = dist.groupby(["Customer Name", "Customer Name.1"], as_index=False).agg(
        NSV_LOC=("Inv. Net value(LOC)", "sum"),
        Qty=("Inv Qty", "sum"),
    ).sort_values("NSV_LOC", ascending=False)
    g["NSV_Lakh"] = (g["NSV_LOC"] / 1e5).round(2)
    g.insert(0, "NOTE", "DIAGNOSTIC ONLY -- not used to derive chain-level NSV. "
                         "Confirm with data owner what this field means before using it as an allocation weight.")
    return g


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", default="data/monthly/Aug26_primary_detailed.csv")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    df = load(args.src)
    acct = account_wise_summary(df)
    gst = gst_input_article_wise(df)
    pooled = dist_pooled_hints(df)

    total_nsv_lakh = df["Inv. Net value(LOC)"].sum() / 1e5
    direct_nsv_lakh = df[df["PO Type"] == "Direct"]["Inv. Net value(LOC)"].sum() / 1e5
    dist_nsv_lakh = df[df["PO Type"] == "Dist."]["Inv. Net value(LOC)"].sum() / 1e5

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(out, engine="xlsxwriter") as xw:
        acct.to_excel(xw, sheet_name="Account-wise Summary", index=False)
        gst.to_excel(xw, sheet_name="GST Input - Article wise", index=False)
        pooled.to_excel(xw, sheet_name="Dist-Pooled hints (diagnostic)", index=False)
        wb, ws = xw.book, xw.sheets["Account-wise Summary"]
        bold = wb.add_format({"bold": True})
        ws.write(len(acct) + 2, 0, "Total NSV (Lakh)", bold)
        ws.write(len(acct) + 2, 1, round(total_nsv_lakh, 2))
        ws.write(len(acct) + 3, 0, "Direct NSV (Lakh) -- real chain identity", bold)
        ws.write(len(acct) + 3, 1, round(direct_nsv_lakh, 2))
        ws.write(len(acct) + 4, 0, "Dist. NSV (Lakh) -- distributor identity, NOT chain", bold)
        ws.write(len(acct) + 4, 1, round(dist_nsv_lakh, 2))

    print(f"Wrote {out} -- {len(acct)} accounts, {len(gst)} articles, "
          f"{len(pooled)} distributor/pooled-hint rows")
    print(f"Total NSV {total_nsv_lakh:,.2f}L = Direct {direct_nsv_lakh:,.2f}L "
          f"({direct_nsv_lakh/total_nsv_lakh*100:.1f}%) + Dist. {dist_nsv_lakh:,.2f}L "
          f"({dist_nsv_lakh/total_nsv_lakh*100:.1f}%)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
