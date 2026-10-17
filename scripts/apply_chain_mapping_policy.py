#!/usr/bin/env python3
"""Turn the owner-approved chain rules (config/chain_mapping_policy.yml) into month-grain rows for
PowerBI/SeedData/Masters/PrimaryAllocationOverride.csv, which the build already reads (FM-19, option A:
an override only applies to a (Ship To, Brand, Month) key the cont% sheet cannot map at all).

Dry run by default: prints what would be added and what is skipped and why. `--write` appends (never rewrites)
rows. Only APPROVED, single-chain rules are used; SPLIT rules, pending rules and ship-tos with no rule are listed
and left alone. Evidence in Remarks follows the form the build requires: `Approved: <who> <YYYY-MM-DD> ...`.

Usage:
    python scripts/apply_chain_mapping_policy.py --month 2026-09 --approved-by "MT Channel Analyst Lead 2026-10-17"
    python scripts/apply_chain_mapping_policy.py --month 2026-09 --approved-by "..." --write

The unmapped keys come from dashboard/data.js (alloc.missing_mapping), so run it after a build that shows them.
"""
import argparse
import csv
import json
import re
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
from build_dashboard_data import canon_brand  # noqa: E402

POLICY = REPO / "config" / "chain_mapping_policy.yml"
OVERRIDE = REPO / "PowerBI" / "SeedData" / "Masters" / "PrimaryAllocationOverride.csv"
DATA_JS = REPO / "dashboard" / "data.js"
FIELDS = ["Month", "Ship To Name", "Chain", "Brand", "Override Cont%", "Remarks", "Evidence_Alignment", "Evidence_Reference"]


def _norm(s):
    return str(s or "").strip().lower()


def _brand_match(scope, brand):
    """scope: 'ALL' | 'ALL except X' | 'X'. Brands compared after canonicalisation."""
    b = _norm(canon_brand(brand))
    s = str(scope or "ALL").strip()
    if s.upper() == "ALL":
        return True, False
    m = re.match(r"(?i)all except (.+)$", s)
    if m:
        return _norm(canon_brand(m.group(1))) != b, False
    return _norm(canon_brand(s)) == b, True            # (matches, is_brand_specific)


def rule_for(rules, ship_to, brand):
    """(rule, ...) for the most specific APPROVED single-chain rule, else None. A brand-specific rule beats ALL scopes."""
    best = None
    for r in rules:
        if r.get("status") != "APPROVED" or str(r.get("chain", "")).upper().startswith("SPLIT"):
            continue
        if _norm(r.get("distributor")) != _norm(ship_to):
            continue
        ok, specific = _brand_match(r.get("brand"), brand)
        if not ok:
            continue
        if best is None or (specific and not best[1]):
            best = (r, specific)
    return best


def build_rows(rules, keys, month, approved_by, existing=frozenset()):
    rows, skipped, seen = [], [], set()
    for ship_to, brand in keys:
        k = (_norm(ship_to), _norm(canon_brand(brand)), month)
        if k in seen:
            continue
        seen.add(k)
        if k in existing or (_norm(ship_to), _norm(brand), month) in existing:
            skipped.append(f"{ship_to} / {brand}: already in the override file")
            continue
        hit = rule_for(rules, ship_to, brand)
        if hit is None:
            skipped.append(f"{ship_to} / {brand}: no approved single-chain rule (needs an owner decision)")
            continue
        r = hit[0]
        rows.append({"Month": month, "Ship To Name": ship_to, "Chain": r["chain"], "Brand": canon_brand(brand),
                     "Override Cont%": 100,
                     "Remarks": f"Approved: {approved_by} (option A - unmapped rows only; {r['rule_id']})",
                     "Evidence_Alignment": "OWNER_RULE", "Evidence_Reference": f"config/chain_mapping_policy.yml {r['rule_id']}"})
    return rows, skipped


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--month", required=True, help="YYYY-MM of the unmapped keys")
    ap.add_argument("--approved-by", required=True, help='for example "MT Channel Analyst Lead 2026-10-17"')
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args(argv)
    if not re.search(r"\d{4}-\d{2}-\d{2}", a.approved_by):
        print("FAIL: --approved-by must carry the approval date (YYYY-MM-DD)")
        return 1
    rules = yaml.safe_load(POLICY.read_text(encoding="utf-8"))["rules"]
    s = DATA_JS.read_text(encoding="utf-8")
    mm = json.loads(s[s.index("{"): s.rindex("}") + 1])["alloc"]["missing_mapping"]
    keys = [(r["ship_to"], r["brand"]) for r in mm]
    existing = set()
    if OVERRIDE.exists():
        with OVERRIDE.open(newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                existing.add((_norm(r["Ship To Name"]), _norm(r["Brand"]), str(r["Month"])[:7]))
                existing.add((_norm(r["Ship To Name"]), _norm(canon_brand(r["Brand"])), str(r["Month"])[:7]))
    rows, skipped = build_rows(rules, keys, a.month, a.approved_by, existing)
    print(f"{len(rows)} override row(s) to add for {a.month}; {len(skipped)} skipped")
    for r in rows:
        print(f"  + {r['Ship To Name']:40s} {r['Brand']:14s} -> {r['Chain']}   ({r['Evidence_Reference'].split()[-1]})")
    for x in skipped:
        print(f"  - {x}")
    if a.write and rows:
        new = not OVERRIDE.exists()
        with OVERRIDE.open("a", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=FIELDS)
            if new:
                w.writeheader()
            w.writerows(rows)
        print(f"appended {len(rows)} row(s) to {OVERRIDE.relative_to(REPO)}")
    elif not a.write:
        print("dry run: nothing written (use --write)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
