#!/usr/bin/env python3
"""RKAM target planning workbook (Sheet2, Q3) -> chain-level Primary target seed.

Reads   : All_India_RKAM_Target_Planning workbook, sheet "Sheet2"
          (QTR, RKAM, NKAM, Chain, Q3 TGT OLD, Q3 TGT New).
Writes  : PowerBI/SeedData/Masters/Q3_FY27_Chain_Target_Primary.csv

Privacy: RKAM / NKAM names are employee identifiers and never leave the
workbook. The seed holds chain totals only. Employee-level targets wait for
the employee-ID mapping (docs/PROJECT_STATE.md, Required Business Inputs #2).

Basis: Primary (owner decision, 2026-10-17). Unit: INR Lakh.

Usage:
  python scripts/ingest_rkam_q3_targets.py --xlsx <workbook> [--write]
"""
from __future__ import annotations
import argparse, csv, sys
from collections import OrderedDict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
OUT = REPO / "PowerBI" / "SeedData" / "Masters" / "Q3_FY27_Chain_Target_Primary.csv"
HEADER = ["FY", "Quarter", "Chain", "Basis", "Q3_Old_Target_L", "Q3_New_Target_L",
          "Unit", "Source", "Approved_By", "Approved_Date"]
APPROVED_BY = "MT Channel Analyst Lead"
APPROVED_DATE = "2026-10-17"
SOURCE = "All_India_RKAM_Target_Planning_-_Pan_India_1.xlsx / Sheet2 (chain totals only)"


def chain_totals(rows, canon):
    """rows: iterable of (qtr, rkam, nkam, chain, old, new). Total rows and
    blank chains are skipped; chains are canonicalised and summed."""
    agg = OrderedDict()
    for qtr, _rkam, _nkam, chain, old, new in rows:
        if qtr != "Q3" or not chain:
            continue
        c = canon(chain) or str(chain).strip()
        a = agg.setdefault(c, [0.0, 0.0])
        a[0] += float(old or 0)
        a[1] += float(new or 0)
    return agg


def seed_rows(agg):
    return [["FY27", "Q3", c, "Primary", round(o, 4), round(n, 4), "INR Lakh",
             SOURCE, APPROVED_BY, APPROVED_DATE]
            for c, (o, n) in sorted(agg.items(), key=lambda kv: -kv[1][1])]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--xlsx", required=True)
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    import openpyxl
    from build_dashboard_data import canon_chain
    ws = openpyxl.load_workbook(a.xlsx, data_only=True)["Sheet2"]
    src = [(r[0], r[1], r[2], r[3], r[4], r[5]) for r in ws.iter_rows(min_row=2, values_only=True)
           if r[0] == "Q3" and r[2] and r[3]]
    rows = seed_rows(chain_totals(src, canon_chain))
    print(f"{len(rows)} chains, old {sum(r[4] for r in rows):.2f} L, new {sum(r[5] for r in rows):.2f} L")
    if a.write:
        with open(OUT, "w", newline="") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(HEADER); w.writerows(rows)
        print("wrote", OUT.relative_to(REPO))


if __name__ == "__main__":
    main()
