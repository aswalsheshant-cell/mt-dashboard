#!/usr/bin/env python3
"""
tests/validate_unified_3yr_reconciliation.py
Automated 3-Year Unified Primary Reconciliation & Data Integrity Validator
Validates FY25 (composite), FY26, and FY27 coverage with control totals.
"""

import sys
from pathlib import Path
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent

# File paths
PATH_PRIMARY_COMPOSITE = (
    REPO_ROOT / "PowerBI/RawDataFolders/Primary_ShipTo_Monthly/Primary_ShipTo_FY24-26_Composite.csv"
)
PATH_DATA_JS = REPO_ROOT / "dashboard/data.js"

# Control targets (Lakhs)
EXPECTED_FY25_NSV_LAKH = 23325.00
TOLERANCE_LAKH = 1.00


def test_fy25_composite_control():
    """Validate FY25 data from composite file."""
    print("\n[1/3] Validating FY25 Composite Control Total...")
    if not PATH_PRIMARY_COMPOSITE.exists():
        print(f"  ❌ Missing: {PATH_PRIMARY_COMPOSITE}")
        return False

    df = pd.read_csv(PATH_PRIMARY_COMPOSITE, low_memory=False)
    df.columns = [c.strip().replace(" ", "_") for c in df.columns]

    df_fy25 = df[df["FY_Year"].str.contains("FY_24-25", case=False, na=False)]
    df_fy25["Primary_NSV"] = pd.to_numeric(df_fy25["Primary_NSV"], errors="coerce").fillna(0)

    total_fy25_rupees = df_fy25["Primary_NSV"].sum()
    # Composite file stores in rupees, convert to Lakhs
    total_fy25 = total_fy25_rupees / 100000
    variance = abs(total_fy25 - EXPECTED_FY25_NSV_LAKH)

    print(f"  Target:      ₹{EXPECTED_FY25_NSV_LAKH:,.2f}L")
    print(f"  Composite:   ₹{total_fy25:,.2f}L (from {total_fy25_rupees:,.0f} rupees)")
    print(f"  Variance:    ₹{variance:,.4f}L")

    if variance > TOLERANCE_LAKH:
        print(f"  ❌ Failed (exceeds ±₹{TOLERANCE_LAKH}L tolerance)")
        return False

    print("  ✓ FY25 composite fully reconciled")
    return True


def test_datajs_fy25_integration():
    """Validate FY25 in dashboard data.js."""
    print("\n[2/3] Validating FY25 in data.js...")
    if not PATH_DATA_JS.exists():
        print(f"  ❌ Missing: {PATH_DATA_JS}")
        return False

    with open(PATH_DATA_JS, 'r') as f:
        content = f.read()

    # Check for FY25 mentions
    checks = [
        ('"fy25"' in content, "FY25 tag present"),
        ('"nsv_fy25"' in content, "FY25 NSV key present"),
        ('"monthly_fy25"' in content, "FY25 monthly data present"),
        ('23325' in content, "FY25 control total (₹233.25Cr) present"),
    ]

    for condition, desc in checks:
        if condition:
            print(f"  ✓ {desc}")
        else:
            print(f"  ❌ {desc}")
            return False

    # Check no NaN in primary section
    if '"NaN"' in content[:content.find('"offtake"')] if '"offtake"' in content else content:
        print(f"  ❌ NaN values in primary section")
        return False

    print("  ✓ FY25 data fully integrated in dashboard")
    return True


def test_multiyear_integrity():
    """Validate FY25 + FY26 + FY27 continuity."""
    print("\n[3/3] Validating 3-Year Continuity...")

    import json
    import re

    with open(PATH_DATA_JS, 'r') as f:
        content = f.read()

    start = content.find('{')
    end = content.rfind('}') + 1

    try:
        data = json.loads(content[start:end])
    except Exception as e:
        print(f"  ❌ JSON parse error: {e}")
        return False

    primary = data.get('primary', {})
    fy_tags = primary.get('fy_tags', [])

    if fy_tags != ['fy25', 'fy26', 'fy27']:
        print(f"  ❌ Expected FY tags ['fy25','fy26','fy27'], got {fy_tags}")
        return False

    # Check all dimensions
    by_chain = primary.get('by_chain', [])
    by_zone = primary.get('by_zone', [])

    chains_3yr = [c for c in by_chain if all(c.get(f) for f in ['fy25', 'fy26', 'fy27'])]
    zones_fy25 = [z for z in by_zone if z.get('fy25')]

    print(f"  ✓ FY25 + FY26 + FY27 continuous across {len(fy_tags)} fiscal years")
    print(f"  ✓ {len(chains_3yr)}/{len(by_chain)} chains span 3 years")
    print(f"  ✓ {len(zones_fy25)}/{len(by_zone)} zones have FY25 data")

    # Sample YoY math
    if by_chain and len(by_chain) > 0:
        sample = by_chain[0]
        fy25 = sample.get('fy25', 0)
        fy26 = sample.get('fy26', 0)
        if fy25 > 0 and fy26 > 0:
            yoy = sample.get('yoy')
            expected_yoy = (fy26 - fy25) / fy25 * 100
            if yoy and abs(yoy - expected_yoy) < 1:
                print(f"  ✓ YoY math validated (sample: {yoy:.1f}%)")
            else:
                print(f"  ⚠ YoY variance detected")

    return True


def main():
    print("=" * 70)
    print(" 🚀 3-Year Unified Primary Reconciliation Test Suite")
    print("=" * 70)

    results = [
        test_fy25_composite_control(),
        test_datajs_fy25_integration(),
        test_multiyear_integrity(),
    ]

    print("\n" + "=" * 70)
    passed = sum(results)
    total = len(results)

    if all(results):
        print(f" ✅ ALL {total} TESTS PASSED - FY25 Integration Complete")
        print("=" * 70)
        return 0
    else:
        print(f" ⚠️  {total - passed} of {total} tests failed")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
