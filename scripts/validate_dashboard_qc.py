#!/usr/bin/env python3
"""
Deep QC Validation Suite for MT Dashboard data.js
Validates: schema, nulls, Primary vs Offtake reconciliation, CM2 calcs, RBC completeness.
"""

import json
import sys
from pathlib import Path
from collections import defaultdict

def load_data_js(data_js_path):
    """Safely load dashboard/data.js as JSON."""
    if not Path(data_js_path).exists():
        raise FileNotFoundError(f"Required file not found: {data_js_path}")

    try:
        with open(data_js_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # data.js contains "const DASH = { ... };" so extract the JSON
            start = content.find('{')
            end = content.rfind('}') + 1
            data_json = content[start:end]
            return json.loads(data_json)
    except (json.JSONDecodeError, IOError) as e:
        raise ValueError(f"Failed to parse data.js: {e}")

def validate_schema(data, block_name, required_keys):
    """Check required keys in a data block."""
    missing = set(required_keys) - set(data.get(block_name, {}).keys())
    if missing:
        return False, f"❌ {block_name}: missing keys {missing}"
    return True, f"✓ {block_name}: schema OK"

def census_nulls(items, block_name, dim_cols):
    """Report nulls across dimension columns."""
    if not isinstance(items, list):
        return {}, f"⚠ {block_name}: not a list (type={type(items).__name__})"

    null_counts = defaultdict(int)
    for item in items:
        for col in dim_cols:
            val = item.get(col)
            if val is None or val == '' or val == 'null':
                null_counts[col] += 1

    total_nulls = sum(null_counts.values())
    if total_nulls == 0:
        return null_counts, f"✓ {block_name}: no nulls in {dim_cols}"

    msg = f"⚠ {block_name}: {total_nulls} nulls found:\n"
    for col, count in sorted(null_counts.items(), key=lambda x: -x[1]):
        pct = 100 * count / len(items) if items else 0
        msg += f"    {col}: {count} ({pct:.1f}%)\n"
    return null_counts, msg

def validate_primary_vs_offtake(primary_items, offtake_items):
    """Reconcile Primary NSV vs Offtake by FY+Chain+Month."""
    if not primary_items or not offtake_items:
        return {"status": "SKIP", "reason": "Missing primary or offtake items"}

    # Aggregate Primary by (fy_tag, chain_name, month_label)
    p_agg = defaultdict(float)
    for item in primary_items:
        key = (item.get('fy_tag'), item.get('chain_name'), item.get('month_label'))
        nsv = float(item.get('nsv_lakhs', 0))
        p_agg[key] += nsv

    # Aggregate Offtake by (fy_tag, chain_name, month_label)
    o_agg = defaultdict(float)
    for item in offtake_items:
        key = (item.get('fy_tag'), item.get('chain_name'), item.get('month_label'))
        offtake = float(item.get('value_sold_lakhs', 0))
        o_agg[key] += offtake

    # Compare
    matches = 0
    mismatches = []
    tolerance = 0.01  # ±1%

    all_keys = set(p_agg.keys()) | set(o_agg.keys())
    for key in all_keys:
        p_val = p_agg.get(key, 0)
        o_val = o_agg.get(key, 0)

        if p_val == 0:
            variance_pct = 100 if o_val != 0 else 0
        else:
            variance_pct = abs((p_val - o_val) / p_val * 100)

        if variance_pct <= tolerance:
            matches += 1
        else:
            mismatches.append({
                'fy_tag': key[0],
                'chain_name': key[1],
                'month_label': key[2],
                'primary_nsv': p_val,
                'offtake_value': o_val,
                'variance_pct': variance_pct
            })

    return {
        "status": "OK" if len(mismatches) == 0 else "WARNING",
        "matches": matches,
        "mismatches": len(mismatches),
        "tolerance_pct": tolerance,
        "top_mismatches": sorted(mismatches, key=lambda x: -x['variance_pct'])[:5]
    }

def validate_rbc_mapping(rbc_items):
    """Check RBC zone/brand/state mapping completeness."""
    if not rbc_items:
        return {
            "status": "EMPTY",
            "total_records": 0,
            "zones_unique": 0,
            "brands_unique": 0,
            "states_unique": 0,
            "unmapped_rows": 0
        }

    zones = set()
    brands = set()
    states = set()
    unmapped = 0

    for item in rbc_items:
        zone = item.get('zone_name')
        brand = item.get('brand_name')
        state = item.get('state_name')

        if zone and zone != 'null':
            zones.add(zone)
        else:
            unmapped += 1

        if brand and brand != 'null':
            brands.add(brand)

        if state and state != 'null':
            states.add(state)

    status = "OK" if unmapped == 0 else "WARNING"

    return {
        "status": status,
        "total_records": len(rbc_items),
        "zones_unique": len(zones),
        "brands_unique": len(brands),
        "states_unique": len(states),
        "unmapped_rows": unmapped,
        "unmapped_pct": 100 * unmapped / len(rbc_items) if rbc_items else 0,
        "zones_list": sorted(zones) if zones else [],
        "brands_list": sorted(brands) if brands else []
    }

def validate_cm2_logic(pnl_items):
    """Audit CM2% calculations (NSV, Expense, CM2 Value, CM2%)."""
    if not pnl_items:
        return {"status": "EMPTY", "total_records": 0}

    calc_errors = []

    for item in pnl_items:
        nsv = float(item.get('nsv_lakhs', 0))
        expense = float(item.get('expense_lakhs', 0))
        cm2_value = float(item.get('cm2_value_lakhs', 0))
        cm2_pct = float(item.get('cm2_pct', 0))

        # Expected: CM2 Value = NSV - Expense
        expected_cm2_value = nsv - expense
        if abs(expected_cm2_value - cm2_value) > 0.01:  # tolerance ±0.01L
            calc_errors.append({
                'chain_name': item.get('chain_name'),
                'month_label': item.get('month_label'),
                'nsv': nsv,
                'expense': expense,
                'cm2_value_actual': cm2_value,
                'cm2_value_expected': expected_cm2_value,
                'error': cm2_value - expected_cm2_value
            })

        # Expected: CM2% = (CM2 Value / NSV) * 100
        if nsv > 0:
            expected_cm2_pct = (cm2_value / nsv) * 100
            if abs(expected_cm2_pct - cm2_pct) > 0.1:  # tolerance ±0.1%
                calc_errors.append({
                    'chain_name': item.get('chain_name'),
                    'month_label': item.get('month_label'),
                    'cm2_pct_actual': cm2_pct,
                    'cm2_pct_expected': expected_cm2_pct,
                    'error': cm2_pct - expected_cm2_pct
                })

    status = "OK" if len(calc_errors) == 0 else "WARNING"

    return {
        "status": status,
        "total_records": len(pnl_items),
        "calc_errors": len(calc_errors),
        "error_details": calc_errors[:5]  # first 5 errors
    }

def count_dimension_coverage(items, dim_col):
    """Count unique values in a dimension column."""
    if not items:
        return 0

    unique_vals = set()
    for item in items:
        val = item.get(dim_col)
        if val and val != 'null' and val != '':
            unique_vals.add(val)

    return len(unique_vals), sorted(unique_vals) if len(unique_vals) <= 20 else []

def main():
    data_js_path = Path(__file__).parent.parent / "dashboard" / "data.js"

    print("=" * 80)
    print("MT DASHBOARD DEEP QC VALIDATION REPORT")
    print("=" * 80)
    print()

    # Load data
    try:
        data = load_data_js(str(data_js_path))
        print(f"✓ Loaded data.js ({len(str(data))/1e6:.1f} MB)")
    except Exception as e:
        print(f"❌ Failed to load data.js: {e}")
        return 1

    # ===== SCHEMA VALIDATION =====
    print("\n[1] SCHEMA VALIDATION")
    print("-" * 80)

    primary = data.get('primary', [])
    offtake = data.get('offtake', [])
    rbc = data.get('rbc', [])
    pnl = data.get('pnl', [])

    print(f"  Primary:  {len(primary)} records")
    print(f"  Offtake:  {len(offtake)} records")
    print(f"  RBC:      {len(rbc)} records")
    print(f"  P&L:      {len(pnl)} records")
    print()

    # ===== NULL CENSUS =====
    print("[2] NULL CENSUS BY DIMENSION")
    print("-" * 80)

    dim_cols = ['fy_tag', 'chain_name', 'zone_name', 'brand_name', 'state_name']

    _, msg = census_nulls(primary, "Primary", dim_cols)
    print(msg)

    _, msg = census_nulls(offtake, "Offtake", dim_cols)
    print(msg)

    _, msg = census_nulls(rbc, "RBC", dim_cols)
    print(msg)

    # ===== DIMENSION COVERAGE =====
    print("[3] DIMENSION COVERAGE")
    print("-" * 80)

    for dim_col in ['zone_name', 'brand_name', 'state_name']:
        n_zones, zones = count_dimension_coverage(primary, dim_col)
        print(f"  Primary {dim_col}: {n_zones} unique values")
        if zones and len(zones) <= 10:
            print(f"    → {', '.join(zones)}")
    print()

    # ===== RECONCILIATION =====
    print("[4] PRIMARY vs OFFTAKE RECONCILIATION")
    print("-" * 80)

    recon = validate_primary_vs_offtake(primary, offtake)
    if recon['status'] == 'SKIP':
        print(f"  ⚠ Skipped: {recon['reason']}")
    else:
        print(f"  {recon['status']}: {recon['matches']} matches, {recon['mismatches']} mismatches (tolerance: ±{recon['tolerance_pct']}%)")
        if recon['top_mismatches']:
            print("  Top mismatches:")
            for mm in recon['top_mismatches']:
                print(f"    • {mm['fy_tag']} | {mm['chain_name']} | {mm['month_label']}: "
                      f"Primary ₹{mm['primary_nsv']:.2f}L vs Offtake ₹{mm['offtake_value']:.2f}L "
                      f"({mm['variance_pct']:.1f}% variance)")
    print()

    # ===== RBC MAPPING =====
    print("[5] RBC DATA COMPLETENESS & MAPPING")
    print("-" * 80)

    rbc_status = validate_rbc_mapping(rbc)
    print(f"  Status: {rbc_status['status']}")
    print(f"  Total RBC records: {rbc_status['total_records']}")
    print(f"  Unique zones: {rbc_status['zones_unique']}")
    print(f"  Unique brands: {rbc_status['brands_unique']}")
    print(f"  Unique states: {rbc_status['states_unique']}")
    print(f"  Unmapped rows (no zone): {rbc_status['unmapped_rows']} ({rbc_status['unmapped_pct']:.1f}%)")

    if rbc_status['zones_list']:
        print(f"  Zones: {', '.join(rbc_status['zones_list'][:5])}")
    if rbc_status['brands_list']:
        print(f"  Brands: {', '.join(rbc_status['brands_list'][:5])}")
    print()

    # ===== CM2 CALCULATION AUDIT =====
    print("[6] CM2 CALCULATION AUDIT (NSV, Expense, CM2%, CM2 Value)")
    print("-" * 80)

    cm2_status = validate_cm2_logic(pnl)
    print(f"  Status: {cm2_status['status']}")
    print(f"  Total P&L records: {cm2_status['total_records']}")
    print(f"  Calculation errors found: {cm2_status['calc_errors']}")

    if cm2_status['error_details']:
        print("  Error details:")
        for err in cm2_status['error_details']:
            if 'cm2_value_actual' in err:
                print(f"    • {err.get('chain_name', '?')} | {err.get('month_label', '?')}: "
                      f"CM2 Value error ₹{err['error']:.4f}L")
            elif 'cm2_pct_actual' in err:
                print(f"    • {err.get('chain_name', '?')} | {err.get('month_label', '?')}: "
                      f"CM2% error {err['error']:.2f}%")
    print()

    # ===== SUMMARY & RECOMMENDATIONS =====
    print("[7] SUMMARY & REMEDIATION PLAN")
    print("-" * 80)

    issues = []
    if rbc_status['unmapped_rows'] > 0:
        issues.append(f"RBC: {rbc_status['unmapped_rows']} rows missing zone mapping")
    if rbc_status['zones_unique'] == 0:
        issues.append("RBC: No zone data — verify source file contains zone_name column")
    if recon['mismatches'] > 0 and recon['status'] != 'SKIP':
        issues.append(f"Reconciliation: {recon['mismatches']} Primary-Offtake mismatches exceed tolerance")
    if cm2_status['calc_errors'] > 0:
        issues.append(f"P&L: {cm2_status['calc_errors']} CM2 calculation errors")

    if not issues:
        print("✓ All validations PASSED")
        return 0
    else:
        print(f"⚠ Found {len(issues)} issues requiring attention:")
        for i, issue in enumerate(issues, 1):
            print(f"  {i}. {issue}")
        print()
        print("RECOMMENDED FIXES:")
        print("  • RBC unmapped zones: Check source RBC file for zone_name column; backfill with zone defaults if safe")
        print("  • Primary-Offtake variance: Review monthly reconciliation in source files; validate month labels")
        print("  • CM2 errors: Verify Expense column calculation logic; check for rounding/precision issues")
        print("  • Missing states: Confirm state-level data exists in source; add state mapping if available")
        return 1

if __name__ == "__main__":
    sys.exit(main())
