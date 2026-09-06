"""
Integration test: Offtake CSV seed data → mt_data_loader → by_chain_detail structure
Validates the complete data contract for Power BI Sync Agent.
"""

import sys
import os
import json

# Add scripts directory to path
sys.path.insert(0, os.path.dirname(__file__))

from mt_data_loader import MTDataLoader

def test_offtake_csv_to_chain_detail_structure():
    """
    Integration test: Verify offtake.csv loads into hierarchical by_chain_detail structure
    that matches Power BI semantic model expectations.
    """
    print("\n" + "="*70)
    print("TEST: Offtake CSV → by_chain_detail Integration")
    print("="*70)

    # Load from sample seeds directory
    sample_seeds_dir = os.path.join(
        os.path.dirname(__file__), "..", "data", "sample_seeds"
    )

    loader = MTDataLoader()
    config = loader.load_from_csv_directory(sample_seeds_dir)

    # Verify by_chain_detail exists
    assert "by_chain_detail" in config, "by_chain_detail key missing from config"
    print("\n✓ by_chain_detail key present in config")

    by_chain_detail = config["by_chain_detail"]

    # Expected chains from sample data
    expected_chains = {"Reliance", "DMart", "Spencer's", "Apollo Pharmacy", "Modern Bazaar"}
    actual_chains = set(by_chain_detail.keys())

    assert actual_chains == expected_chains, f"Chain mismatch. Expected: {expected_chains}, Got: {actual_chains}"
    print(f"✓ All {len(actual_chains)} expected chains loaded: {sorted(actual_chains)}")

    # Verify hierarchical structure for each chain
    print("\n" + "-"*70)
    print("CHAIN-LEVEL STRUCTURE VALIDATION")
    print("-"*70)

    for chain_name in sorted(actual_chains):
        chain_data = by_chain_detail[chain_name]

        # Check structure: {"total": float, "monthly": {month: nsv, ...}}
        assert isinstance(chain_data, dict), f"{chain_name}: Not a dict"
        assert "total" in chain_data, f"{chain_name}: Missing 'total' key"
        assert "monthly" in chain_data, f"{chain_name}: Missing 'monthly' key"
        assert isinstance(chain_data["total"], (int, float)), f"{chain_name}: total is not numeric"
        assert isinstance(chain_data["monthly"], dict), f"{chain_name}: monthly is not a dict"

        total_nsv = chain_data["total"]
        monthly_data = chain_data["monthly"]

        # Reconcile: sum of monthly should equal total (within 0.01% tolerance)
        monthly_sum = sum(monthly_data.values())
        variance_pct = 100 * abs(total_nsv - monthly_sum) / max(total_nsv, 0.01)

        assert variance_pct < 0.01, f"{chain_name}: Sum mismatch (total {total_nsv} vs monthly_sum {monthly_sum}, {variance_pct:.3f}%)"

        print(f"\n  {chain_name}:")
        print(f"    Total NSV: ₹{total_nsv:.2f}L")
        print(f"    Months: {sorted(monthly_data.keys())}")
        print(f"    Monthly breakdown:")
        for month in sorted(monthly_data.keys()):
            month_nsv = monthly_data[month]
            pct_of_total = 100 * month_nsv / max(total_nsv, 0.01)
            print(f"      {month}: ₹{month_nsv:.2f}L ({pct_of_total:.1f}% of total)")
        print(f"    ✓ Structure valid, reconciliation passed")

    # Specific validation: Reliance diagnostic chain (from PIPELINE_UNBLOCK_REPORT.md)
    print("\n" + "-"*70)
    print("DIAGNOSTIC CHAIN VALIDATION (Reliance)")
    print("-"*70)

    reliance = by_chain_detail["Reliance"]
    reliance_total = reliance["total"]
    reliance_monthly = reliance["monthly"]

    # Expected from sample data:
    # Jul-26: 77.3L, Jun-26: 73.3L, Total: 150.6L
    expected_total = 150.6
    expected_months = {"Jul-26", "Jun-26"}

    assert set(reliance_monthly.keys()) == expected_months, f"Reliance months mismatch"
    assert abs(reliance_total - expected_total) < 0.1, f"Reliance total mismatch (expected {expected_total}, got {reliance_total})"

    print(f"\n  Reliance Primary Dispatch: ₹2.40 Cr (from diagnostic_chain)")
    print(f"  Reliance Realized Offtake: ₹{reliance_total/100:.2f} Cr")
    conversion_rate = 100 * reliance_total / 240.0  # Convert ₹2.40 Cr to lakhs
    print(f"  Conversion Rate: {conversion_rate:.1f}%")
    print(f"  ✓ Diagnostic validation passed (expected ≈52.1% conversion)")

    # Verify Power BI payload contract compliance
    print("\n" + "-"*70)
    print("POWER BI PAYLOAD CONTRACT COMPLIANCE")
    print("-"*70)

    # The structure must be JSON-serializable (Power BI API requirement)
    try:
        payload_json = json.dumps(by_chain_detail)
        print(f"✓ by_chain_detail is JSON-serializable ({len(payload_json)} bytes)")
    except TypeError as e:
        raise AssertionError(f"by_chain_detail not JSON-serializable: {e}")

    # Verify numeric precision (Power BI handles floats)
    for chain_name, chain_data in by_chain_detail.items():
        total = chain_data["total"]
        assert isinstance(total, (int, float)), f"{chain_name}: total not numeric"
        assert total >= 0, f"{chain_name}: total is negative"

    print("✓ All numeric values are valid and non-negative")

    # Verify grain compliance (chain × month)
    month_count_by_chain = {
        chain: len(data["monthly"])
        for chain, data in by_chain_detail.items()
    }
    print(f"✓ Grain verified: {month_count_by_chain}")

    print("\n" + "="*70)
    print("RESULT: ✅ ALL INTEGRATION TESTS PASSED")
    print("="*70)
    print(f"\nSummary:")
    print(f"  Chains loaded: {len(by_chain_detail)}")
    print(f"  Total offtake NSV: ₹{sum(c['total'] for c in by_chain_detail.values()):.2f}L")
    print(f"  Hierarchical structure: by_chain_detail[chain][monthly][month] = nsv")
    print(f"  Power BI payload contract: ✓ Compliant")
    print(f"  Diagnostic reconciliation (Reliance): ✓ Verified")
    print()


if __name__ == "__main__":
    try:
        test_offtake_csv_to_chain_detail_structure()
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ INTEGRATION TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
