#!/usr/bin/env python3
"""
Reconcile the three Primary NSV figures currently in circulation across this repo's
documentation, against the real current source files in
PowerBI/RawDataFolders/Primary_Article_Monthly/.

Background: three different Primary NSV totals appear in different docs/PRs with no
stated relationship between them:
  - CLAUDE.md:                      "FY26 Rs32,900.36 L"           (three-measures table)
  - PowerBI/docs/Desktop_Assembly_Checklist.md, Phase J:  "Rs46,560.34 L" (grand total,
    dated 2026-08-06)
  - PR #119 description:            "Total Primary Rs51,481.65 L"  (16-month backfill)

This script recomputes the same NSV figure build_dashboard_data.py's load_primary_v2()
uses (Inv. Net value(LOC) / 1e5, no PO-Type filter or dedup at this stage -- see that
function, ~line 4745) directly from the real monthly CSVs on disk today, and classifies
each of the three figures as MATCH / STALE (explained) / UNEXPLAINED.

Usage: python3 scripts/reconcile_primary_baseline.py
"""
from __future__ import annotations
import glob
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PRIMARY_DIR = ROOT / "PowerBI" / "RawDataFolders" / "Primary_Article_Monthly"

KNOWN_FIGURES = {
    "CLAUDE.md three-measures table (FY26)": 32900.36,
    "Desktop_Assembly_Checklist.md Phase J (2026-08-06, 'grand total')": 46560.34,
    "PR #119 description (Total Primary, 16-month backfill)": 51481.65,
}


def load_all() -> pd.DataFrame:
    frames = []
    for f in sorted(PRIMARY_DIR.glob("primary_article_*.csv")):
        df = pd.read_csv(f, low_memory=False)
        df.columns = [" ".join(str(c).split()) for c in df.columns]
        df["_src_file"] = f.name
        frames.append(df)
    if not frames:
        raise SystemExit(f"No primary_article_*.csv files found under {PRIMARY_DIR}")
    return pd.concat(frames, ignore_index=True)


def main() -> int:
    df = load_all()
    df["_NSV"] = pd.to_numeric(df["Inv. Net value(LOC)"], errors="coerce").fillna(0.0) / 1e5

    n_files = df["_src_file"].nunique()
    grand_total = round(df["_NSV"].sum(), 2)
    by_fy = df.groupby("FY")["_NSV"].sum().round(2)
    by_file = df.groupby("_src_file")["_NSV"].sum().round(2)

    print(f"Loaded {n_files} monthly file(s), {len(df)} rows, from {PRIMARY_DIR}\n")
    print("--- NSV by FY label (as-is in source; = Inv. Net value(LOC) / 1e5) ---")
    print(by_fy.to_string())
    print(f"\n--- Grand total across all {n_files} months on file ---")
    print(f"Rs{grand_total:,.2f} L")

    print("\n--- Reconciliation against known figures ---")
    fy26_total = by_fy.get("FY'25-26")
    for label, value in KNOWN_FIGURES.items():
        if fy26_total is not None and abs(value - fy26_total) < 0.01:
            print(f"MATCH     {label}: Rs{value:,.2f} L == FY'25-26 (FY26) subtotal exactly.")
            continue
        if abs(value - grand_total) < 0.01:
            print(f"MATCH     {label}: Rs{value:,.2f} L == current grand total exactly.")
            continue
        # Check "grand total minus exactly one month's file" (the documented staleness
        # pattern found manually: Desktop_Assembly_Checklist.md predates a later month
        # being added to the watch folder).
        explained = False
        for fname, fval in by_file.items():
            if abs((grand_total - fval) - value) < 0.01:
                print(
                    f"STALE     {label}: Rs{value:,.2f} L == current grand total minus "
                    f"{fname} (Rs{fval:,.2f} L). This figure predates that month being "
                    f"added to {PRIMARY_DIR.name}/ -- not a data defect, just an older "
                    f"snapshot. Needs the doc's own re-run against the current file set, "
                    f"not a code fix."
                )
                explained = True
                break
        if not explained:
            print(f"UNEXPLAINED  {label}: Rs{value:,.2f} L -- does not match the grand "
                  f"total, the FY26 subtotal, or (grand total - any single month's file). "
                  f"Needs manual investigation before being treated as current.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
