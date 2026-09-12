#!/usr/bin/env python3
"""
CI VALIDATION: Zonal Primary Reconciliation Gate

Validates that distributor primary allocation has zero revenue leakage
and all zones sum correctly to the national total.

Exit code: 0 = pass, 1 = fail
"""
import json
import sys
from pathlib import Path


def load_data_js(data_js_path):
    """Load and parse data.js"""
    try:
        txt = Path(data_js_path).read_text()
        start = txt.index("window.DASH = ") + len("window.DASH = ")
        end = txt.rindex(";")
        return json.loads(txt[start:end])
    except Exception as e:
        print(f"❌ Failed to load {data_js_path}: {e}")
        return None


def validate_zonal_reconciliation(data):
    """Check: sum(zones) ≈ total_primary"""
    if "primary" not in data:
        print("❌ 'primary' block not found in data.js")
        return False

    primary = data["primary"]
    errors = []

    # Check each FY tag
    fy_tags = primary.get("fy_tags", [])
    for tag in fy_tags:
        tag_upper = tag.upper()

        # Get total NSV for this FY
        total_key = f"nsv_{tag}"
        total_nsv = primary.get(total_key, 0) or 0

        if total_nsv == 0:
            continue  # Skip empty FYs

        # Sum zones for this FY
        by_zone = primary.get("by_zone", [])
        zone_key = tag
        zone_sum = sum(z.get(zone_key, 0) or 0 for z in by_zone)

        variance = abs(total_nsv - zone_sum)
        variance_pct = (variance / total_nsv * 100) if total_nsv > 0 else 0

        status = "✅" if variance < 0.01 else "❌"
        print(f"{status} {tag_upper}: Total={total_nsv:.2f}L, Zones={zone_sum:.2f}L, Var={variance:.4f}L ({variance_pct:.3f}%)")

        if variance >= 0.01:
            errors.append(f"{tag_upper}: Zone variance {variance:.2f}L exceeds tolerance")

    return len(errors) == 0, errors


def validate_no_unmapped_chains(data):
    """Check: No "Unmapped Chain" or "Distributor" entries in Modern Trade"""
    if "primary" not in data:
        return True, []

    primary = data["primary"]
    errors = []

    by_chain = primary.get("by_chain", [])
    for chain_entry in by_chain:
        chain_name = chain_entry.get("name", "").lower()

        if "unmapped" in chain_name or (chain_name == "distributor"):
            errors.append(f"Found unmapped chain: {chain_entry.get('name')}")

    if errors:
        print(f"❌ Unmapped chains detected:")
        for err in errors:
            print(f"  - {err}")
        return False, errors

    print(f"✅ No unmapped chains found in primary.by_chain")
    return True, []


def validate_all_zones_covered(data):
    """Check: All 5 expected zones (West, South-1, North, South-2, East) present"""
    if "primary" not in data:
        return True, []

    primary = data["primary"]
    expected_zones = {"West", "South-1", "North", "South-2", "East"}

    by_zone = primary.get("by_zone", [])
    found_zones = {z.get("name", "").strip() for z in by_zone}

    missing = expected_zones - found_zones
    errors = []

    if missing:
        errors.append(f"Missing zones: {missing}")
        print(f"❌ Missing zones: {missing}")
    else:
        print(f"✅ All 5 zones present: {found_zones}")

    return len(errors) == 0, errors


def validate_chain_allocation_qc(data):
    """Check: QC report indicates successful allocation"""
    qc = data.get("chain_allocation_qc")

    if not qc:
        print("⚠️  No chain_allocation_qc report in data.js (may be okay if no distributor rows)")
        return True, []

    errors = []

    # Check reconciliation
    if not qc.get("reconciliation_passed"):
        variance = qc.get("variance_lakh", 0)
        errors.append(f"Allocation reconciliation failed: {variance:.4f}L variance")
        print(f"❌ Allocation failed: {variance:.4f}L variance")
    else:
        print(f"✅ Allocation reconciliation passed")

    # Check coverage
    coverage = qc.get("tier1_rows", 0) + qc.get("tier2_rows", 0) + qc.get("tier3_rows", 0)
    if coverage == 0:
        print(f"⚠️  No distributor rows allocated (may be direct-only data)")
    else:
        print(f"✅ {coverage} distributor rows allocated (T1={qc.get('tier1_rows', 0)}, T2={qc.get('tier2_rows', 0)}, T3={qc.get('tier3_rows', 0)})")

    return len(errors) == 0, errors


def main():
    """Run all validation checks"""
    data_js_path = Path("dashboard/data.js")

    print("\n" + "=" * 70)
    print("CI VALIDATION: Zonal Primary Reconciliation")
    print("=" * 70 + "\n")

    if not data_js_path.exists():
        print(f"❌ {data_js_path} not found")
        return 1

    data = load_data_js(data_js_path)
    if not data:
        return 1

    results = []

    # Check 1: Zonal Reconciliation
    print("CHECK 1: Zonal Primary Reconciliation")
    print("-" * 70)
    passed, errors = validate_zonal_reconciliation(data)
    results.append(("Zonal Reconciliation", passed))
    if errors:
        for err in errors:
            print(f"  ⚠️  {err}")
    print()

    # Check 2: No Unmapped Chains
    print("CHECK 2: No Unmapped Chains in Modern Trade")
    print("-" * 70)
    passed, errors = validate_no_unmapped_chains(data)
    results.append(("No Unmapped Chains", passed))
    print()

    # Check 3: All Zones Covered
    print("CHECK 3: All 5 Zones Present")
    print("-" * 70)
    passed, errors = validate_all_zones_covered(data)
    results.append(("All Zones Covered", passed))
    print()

    # Check 4: Allocation QC
    print("CHECK 4: Allocation QC Report")
    print("-" * 70)
    passed, errors = validate_chain_allocation_qc(data)
    results.append(("Allocation QC", passed))
    print()

    # Summary
    print("=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)
    all_passed = all(r[1] for r in results)

    for check_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {check_name}")

    print()
    if all_passed:
        print("✅ ALL CHECKS PASSED — Zonal allocation is correct")
        return 0
    else:
        print("❌ SOME CHECKS FAILED — Review zonal allocation")
        return 1


if __name__ == "__main__":
    sys.exit(main())
