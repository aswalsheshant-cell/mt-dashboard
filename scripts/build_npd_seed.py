#!/usr/bin/env python3
"""Write the NPD (new product launch) cohort seed for Power BI from dashboard/data.js.

Reads   : dashboard/data.js  npd.by_fy  (built by npd_block(): Chain x EAN launch cohort)
Writes  : PowerBI/SeedData/Masters/NPD_Article_Chain.csv
Grain   : one row per chain x EAN launch (aggregate; no store, employee or restricted fields).

Counts and cohort timing only. The HTML block reports launch NSV on its own basis; that value is
NOT copied here, so Power BI never shows an NPD NSV it cannot reproduce.

Usage:  python scripts/build_npd_seed.py [--check]
"""
from __future__ import annotations
import argparse, csv, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_JS = ROOT / "dashboard" / "data.js"
OUT = ROOT / "PowerBI" / "SeedData" / "Masters" / "NPD_Article_Chain.csv"
HEADER = ["Chain", "EAN", "Article", "NPI Cohort FY", "First Sale FY", "First Sale Month",
          "History Months Before First Sale", "Launch Confirmation"]


def clean_ean(v):
    s = "" if v is None else str(v).strip()
    return s[:-2] if s.endswith(".0") else s


def seed_rows(npd):
    rows = []
    for fy in sorted(npd.get("by_fy") or {}):
        for r in npd["by_fy"][fy]:
            rows.append([r.get("chain") or "", clean_ean(r.get("ean")), r.get("article") or "",
                         r.get("npi_cohort_fy") or fy, r.get("actual_first_sale_fy") or "",
                         r.get("actual_first_sale_month") or "",
                         r.get("history_months_before_first_sale"),
                         r.get("launch_confirmation_status") or ""])
    rows.sort(key=lambda x: (x[3], x[0], x[1]))
    return rows


def load_npd():
    s = DATA_JS.read_text(encoding="utf-8")
    return json.loads(s[s.index("{"): s.rindex("}") + 1])["npd"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="exit 1 if the seed differs from data.js")
    a = ap.parse_args()
    rows = seed_rows(load_npd())
    text = []
    import io
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n"); w.writerow(HEADER); w.writerows(rows)
    if a.check:
        ok = OUT.exists() and OUT.read_text(encoding="utf-8") == buf.getvalue()
        print("NPD seed up to date" if ok else "NPD seed is out of date: run scripts/build_npd_seed.py")
        sys.exit(0 if ok else 1)
    OUT.write_text(buf.getvalue(), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}: {len(rows)} launches")


if __name__ == "__main__":
    main()
