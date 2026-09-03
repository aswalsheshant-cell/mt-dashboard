#!/usr/bin/env python3
"""
Test the TOT% and MRP Corrected Rate derivation logic.

This validates the formulas against known sample data from the analysis.
"""

def calculate_tot_and_mrp(mrp_rate, inv_qty, inv_net_value):
    """Calculate TOT% and MRP Corrected Rate."""
    mrp_extended = mrp_rate * inv_qty
    if mrp_extended == 0:
        tot_pct = 0
    else:
        tot_pct = ((mrp_extended - inv_net_value) / mrp_extended) * 100

    mrp_corrected = mrp_rate * (1 - tot_pct / 100)
    return tot_pct, mrp_corrected

# Test cases from the analysis
test_cases = [
    # (MRP Rate, Inv Qty, Inv. Net value, Expected TOT%, Expected MRP Corrected)
    (549, 168, 33219.15, 63.98, 197.75),
    (449, 160, 27396.61, 61.86, 171.25),
    (449, 120, 20547.46, 61.86, 171.25),
]

print("Testing TOT% and MRP Corrected Rate Derivation")
print("=" * 80)

all_passed = True
for mrp_rate, inv_qty, inv_net_value, expected_tot, expected_mrp_corrected in test_cases:
    tot_pct, mrp_corrected = calculate_tot_and_mrp(mrp_rate, inv_qty, inv_net_value)

    # Check with tolerance for floating point (rounding differences are expected)
    tot_match = abs(tot_pct - expected_tot) < 0.05
    mrp_match = abs(mrp_corrected - expected_mrp_corrected) < 0.05

    status = "✓ PASS" if (tot_match and mrp_match) else "✗ FAIL"

    print(f"\n{status}")
    print(f"  MRP Rate:     {mrp_rate}")
    print(f"  Inv Qty:      {inv_qty}")
    print(f"  Inv Net Val:  {inv_net_value}")
    print(f"  Calculated TOT%:        {tot_pct:.2f}% (expected {expected_tot}%)")
    print(f"  Calculated MRP Corr:    {mrp_corrected:.2f} (expected {expected_mrp_corrected})")

    if not (tot_match and mrp_match):
        all_passed = False

print("\n" + "=" * 80)
if all_passed:
    print("✓ All tests passed")
else:
    print("✗ Some tests failed")
