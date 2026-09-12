#!/usr/bin/env python3
"""D13 production fix: correct fyx_primary.FY27.mrp in dashboard/data.js.

Root causes (D13, PENDING_APPROVAL → approved for implementation):
  1. Brand exclusion not applied to MRP aggregate: excluded-brand rows in
     primary_article_Apr_26.csv and primary_article_May_26.csv contributed 14.33 L
     to the raw MRP sum, which should be zero (Pure Origin, Lumineve, Staze are
     excluded from all reporting).
  2. Jun-26 absent from MRP: patch_jun26.py (prior run) updated FY27 NSV and
     dimension aggregates for Jun-26 but did not update the MRP field, because the
     source workbook did not include an MRP column. Jun-26 GMV/MRP is recovered
     from the governed seed PowerBI/SeedData/Masters/FY27_Monthly_GMV_MRP.csv.

Fix:
  Before: fyx_primary.FY27.mrp = 22,050.21 L  (Apr raw + May raw, no filter, no Jun)
  After:  fyx_primary.FY27.mrp = 31,336.79 L  (Apr filtered + May filtered + Jun seed)

Sources:
  Apr-26  MRP filtered: 11,760.60 L  ← primary_article_Apr_26.csv, excluded brands removed
  May-26  MRP filtered: 10,275.28 L  ← primary_article_May_26.csv, excluded brands removed
  Jun-26  MRP seed:      9,300.91 L  ← FY27_Monthly_GMV_MRP.csv (Status=AUTHORITATIVE)
  Total:                31,336.79 L

The corresponding build_dashboard_data.py fix (line 2300) ensures future
full builds also apply the exclusion. This script makes the current data.js
consistent with that fix, using only committed, traceable sources.

Usage:
  python scripts/fix_d13_mrp.py [--dry-run]
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_JS = ROOT / "dashboard" / "data.js"
ARTICLE_DIR = ROOT / "PowerBI" / "RawDataFolders" / "Primary_Article_Monthly"
SEED_FILE = ROOT / "PowerBI" / "SeedData" / "Masters" / "FY27_Monthly_GMV_MRP.csv"

EXCLUDED_BRANDS = {"Pure Origin", "Lumineve", "Staze"}
BRAND_MAP = {
    "mamaearth": "Mamaearth", "aqualogica": "Aqualogica",
    "the derma co": "The Derma Co", "pure origin": "Pure Origin",
    "lumineve": "Lumineve", "staze": "Staze",
    "bblunt": "Bblunt", "dr. sheth": "Dr. Sheth",
    "dr sheth": "Dr. Sheth", "dr.sheth": "Dr. Sheth",
}

D = Decimal


def canon_brand(b: str | None) -> str | None:
    if b is None or (isinstance(b, float)):
        return None
    k = str(b).strip().lower()
    canonical = BRAND_MAP.get(k, str(b).strip())
    return None if canonical in EXCLUDED_BRANDS else canonical


def load_article_mrp(fname: str) -> Decimal:
    p = ARTICLE_DIR / fname
    if not p.exists():
        raise FileNotFoundError(f"Article CSV not found: {p}")
    total = D("0")
    with open(p, encoding="latin-1", errors="replace") as fh:
        rdr = csv.DictReader(fh)
        for row in rdr:
            brand = canon_brand(row.get("brand"))
            if brand is None:
                continue
            mrp_raw = row.get("Total MRP sales") or "0"
            try:
                total += D(str(float(mrp_raw))) / D("100000")
            except Exception:
                pass
    return total.quantize(D("0.01"))


def load_seed_mrp(month: str) -> Decimal:
    if not SEED_FILE.exists():
        raise FileNotFoundError(f"Seed not found: {SEED_FILE}")
    with open(SEED_FILE, encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row.get("Month", "").strip() == month:
                if (row.get("Status") or "").upper() != "AUTHORITATIVE":
                    raise ValueError(
                        f"Seed row for {month} is not AUTHORITATIVE "
                        f"(status={row.get('Status')})"
                    )
                return D(row["GMV_MRP_Sales_L"]).quantize(D("0.01"))
    raise KeyError(f"No seed row for month {month!r} in {SEED_FILE}")


def sha256_of(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true",
                    help="show what would change without writing")
    a = ap.parse_args()

    print("D13 MRP correction — source-driven fix")
    print("=" * 60)

    # Step 1: compute from sources
    print("\nStep 1: Read sources")
    apr_mrp = load_article_mrp("primary_article_Apr_26.csv")
    print(f"  Apr-26 MRP (brand-filtered): {apr_mrp} L  "
          f"[{ARTICLE_DIR / 'primary_article_Apr_26.csv'}]")
    may_mrp = load_article_mrp("primary_article_May_26.csv")
    print(f"  May-26 MRP (brand-filtered): {may_mrp} L  "
          f"[{ARTICLE_DIR / 'primary_article_May_26.csv'}]")
    jun_mrp = load_seed_mrp("Jun-26")
    print(f"  Jun-26 MRP (seed AUTHORITATIVE): {jun_mrp} L  [{SEED_FILE}]")

    correct_total = (apr_mrp + may_mrp + jun_mrp).quantize(D("0.01"))
    print(f"\n  Corrected FY27 MRP total: {correct_total} L")

    # Step 2: read data.js and locate the mrp field
    print("\nStep 2: Read data.js")
    if not DATA_JS.exists():
        print(f"ERROR: {DATA_JS} not found", file=sys.stderr)
        return 1
    data_js_hash_before = sha256_of(DATA_JS)
    raw = DATA_JS.read_text(encoding="utf-8")

    # Parse the window.DASH payload
    m = re.search(r"window\.DASH\s*=\s*(\{.*)", raw, re.DOTALL)
    if not m:
        print("ERROR: could not find window.DASH in data.js", file=sys.stderr)
        return 1
    payload_start = m.start(1)
    payload_js = raw[payload_start:]
    # Remove trailing semicolon if present
    payload_js = payload_js.rstrip().rstrip(";").rstrip()
    try:
        dash = json.loads(payload_js)
    except json.JSONDecodeError as e:
        print(f"ERROR parsing data.js JSON: {e}", file=sys.stderr)
        return 1

    fy27 = dash.get("detail_meta", {}).get("fyx_primary", {}).get("FY27", {})
    current_mrp = fy27.get("mrp")
    print(f"  Current data.js FY27.mrp: {current_mrp} L")
    print(f"  FY27.nsv (unchanged):     {fy27.get('nsv')} L")
    print(f"  months_covered:           {fy27.get('months_covered')}")

    if current_mrp is None:
        print("ERROR: detail_meta.fyx_primary.FY27.mrp not found in data.js",
              file=sys.stderr)
        return 1

    diff = correct_total - D(str(current_mrp))
    print(f"\n  Difference: {diff:+.2f} L (expected ~+9286.58 L)")

    if abs(diff) < D("0.01"):
        print("\nNO CHANGE NEEDED — data.js MRP already matches the correct total.")
        return 0

    # Step 3: apply fix
    dash["detail_meta"]["fyx_primary"]["FY27"]["mrp"] = float(correct_total)
    new_payload = json.dumps(dash, ensure_ascii=False, separators=(",", ":"))

    before_prefix = raw[:payload_start]
    new_raw = before_prefix + new_payload + ";\n"

    # Verify the fix round-trips correctly
    verify = json.loads(new_payload)
    assert verify["detail_meta"]["fyx_primary"]["FY27"]["mrp"] == float(correct_total), \
        "Round-trip check failed"
    assert verify["detail_meta"]["fyx_primary"]["FY27"]["nsv"] == fy27.get("nsv"), \
        "NSV changed unexpectedly — aborting"

    print(f"\n  Before: {current_mrp} L")
    print(f"  After:  {correct_total} L")
    print(f"  Delta:  {diff:+.2f} L")

    if a.dry_run:
        print("\nDRY RUN — no files written.")
        return 0

    # Step 4: backup and write
    bak = DATA_JS.with_suffix(".js.d13.bak")
    bak.write_bytes(DATA_JS.read_bytes())
    print(f"\nStep 3: Backup written → {bak}")

    DATA_JS.write_text(new_raw, encoding="utf-8")
    data_js_hash_after = sha256_of(DATA_JS)
    print(f"Step 4: data.js updated")
    print(f"  SHA256 before: {data_js_hash_before}")
    print(f"  SHA256 after:  {data_js_hash_after}")

    print("\nD13 fix applied successfully.")
    print("Run: python3 -m scripts.dataeng.cli health  to confirm improvement.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
