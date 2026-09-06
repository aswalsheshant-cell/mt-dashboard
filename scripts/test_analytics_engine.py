"""
Unit tests for MT Analytics Engine.
Validates calculation logic against boundary conditions and edge cases.
"""

from mt_analytics_engine import (
    calculate_waterfall_bridge,
    calculate_scenario_roi,
    calculate_matrix_coordinates
)


def test_waterfall_zero_leakage():
    """Test waterfall when primary equals realized offtake (zero leakage)."""
    result = calculate_waterfall_bridge(2.0, 2.0)
    assert result["trapped_capital"] == 0.0, "Zero leakage should have no trapped capital"
    assert result["conversion_rate"] == 100.0, "100% conversion for zero leakage"
    assert result["shelf_loss"] == 0.0
    assert result["price_loss"] == 0.0
    assert result["stuck_inventory"] == 0.0
    print("✓ Test passed: Waterfall zero leakage boundary")


def test_waterfall_standard_leakage():
    """Test waterfall with typical leakage pattern."""
    result = calculate_waterfall_bridge(2.40, 1.25)
    total_loss = result["shelf_loss"] + result["price_loss"] + result["stuck_inventory"]
    expected_loss = 2.40 - 1.25
    # Allow small rounding tolerance
    assert abs(total_loss - expected_loss) < 0.01, f"Leakage balance failed: {total_loss} != {expected_loss}"
    assert result["conversion_rate"] == round((1.25 / 2.40) * 100, 1)
    print("✓ Test passed: Waterfall standard leakage balance")


def test_waterfall_negative_inputs():
    """Test waterfall handles negative/zero inputs gracefully."""
    result = calculate_waterfall_bridge(-5.0, 2.0)
    assert result["primary"] == 0.0, "Negative primary should be clamped to 0"
    result2 = calculate_waterfall_bridge(2.0, -1.0)
    assert result2["realized_offtake"] == 0.0, "Negative offtake should be clamped to 0"
    print("✓ Test passed: Waterfall negative input clamping")


def test_scenario_roi_zero_promo_spend():
    """Test ROI guard against division by zero on zero promo spend."""
    result = calculate_scenario_roi(
        current_offtake_weekly=7.0,
        current_conv=45.0,
        target_conv=70.0,
        promo_spend=0.0,
        promo_days=21
    )
    assert result["roi_multiple"] == 0.0, "Zero promo spend should yield 0 ROI multiple"
    assert result["net_roi_multiple"] == 0.0
    print("✓ Test passed: Scenario ROI zero promo spend guard")


def test_scenario_roi_conversion_ceiling():
    """Test ROI when current conversion already meets or exceeds target."""
    result = calculate_scenario_roi(
        current_offtake_weekly=7.0,
        current_conv=85.0,
        target_conv=70.0,  # Target is lower than current
        promo_spend=30.0,
        promo_days=21
    )
    # Target should be adjusted to max(current_conv, target_conv)
    assert result["target_conv"] >= result["current_conv"], "Target should not be lower than current"
    assert result["conv_lift_pp"] == 0.0, "No lift when target = current"
    print("✓ Test passed: Scenario ROI conversion ceiling handling")


def test_scenario_roi_standard_case():
    """Test ROI with realistic promotional scenario."""
    result = calculate_scenario_roi(
        current_offtake_weekly=7.0,
        current_conv=45.0,
        target_conv=70.0,
        promo_spend=30.0,  # ₹30 Lakhs
        promo_days=21
    )
    # 21 days = 3 weeks
    assert result["promo_weekly"] > result["current_weekly"], "Promo should increase weekly offtake"
    assert result["net_uplift"] > 0, "Net uplift should be positive"
    assert result["roi_multiple"] > 0, "ROI multiple should be positive"
    assert result["uplift_pct"] > 0, "Uplift % should be positive"
    print("✓ Test passed: Scenario ROI standard case")


def test_matrix_coordinates_clamping():
    """Test matrix coordinates are clamped to bounding box."""
    zones = [
        {"name": "Extreme_High", "conversion": 5.0, "nsv": 100.0},  # Very high gap, very high NSV
        {"name": "Extreme_Low", "conversion": 95.0, "nsv": 0.1},   # Very low gap, very low NSV
    ]
    result = calculate_matrix_coordinates(zones, 0, 0, 100, 100)

    for zone in result:
        assert 0.0 <= zone["x_coord"] <= 100.0, f"X coordinate out of bounds: {zone['x_coord']}"
        assert 0.0 <= zone["y_coord"] <= 100.0, f"Y coordinate out of bounds: {zone['y_coord']}"
    print("✓ Test passed: Matrix coordinates clamping to bounding box")


def test_matrix_quadrant_classification():
    """Test matrix quadrant classification logic."""
    zones = [
        {"name": "East", "conversion": 45.0, "nsv": 3.80},   # High gap, large scale
        {"name": "West", "conversion": 82.0, "nsv": 1.40},   # Low gap, small scale
        {"name": "South-1", "conversion": 78.0, "nsv": 2.40}, # Low gap, medium scale
    ]
    result = calculate_matrix_coordinates(zones, 0, 0, 100, 100)

    # East should be URGENT (high gap, large scale)
    east = [z for z in result if z["name"] == "East"][0]
    assert east["quadrant"] == "URGENT", f"East should be URGENT, got {east['quadrant']}"

    # West should be HEALTHY (low gap, small scale)
    west = [z for z in result if z["name"] == "West"][0]
    assert west["quadrant"] == "HEALTHY", f"West should be HEALTHY, got {west['quadrant']}"

    print("✓ Test passed: Matrix quadrant classification")


def test_matrix_empty_zones():
    """Test matrix handles empty zone list gracefully."""
    result = calculate_matrix_coordinates([], 0, 0, 100, 100)
    assert result == [], "Empty zones should return empty result"
    print("✓ Test passed: Matrix empty zones handling")


def run_all_tests():
    """Execute full test suite."""
    print("\n" + "="*60)
    print("Running MT Analytics Engine Test Suite")
    print("="*60 + "\n")

    test_waterfall_zero_leakage()
    test_waterfall_standard_leakage()
    test_waterfall_negative_inputs()
    test_scenario_roi_zero_promo_spend()
    test_scenario_roi_conversion_ceiling()
    test_scenario_roi_standard_case()
    test_matrix_coordinates_clamping()
    test_matrix_quadrant_classification()
    test_matrix_empty_zones()

    print("\n" + "="*60)
    print("✅ All tests passed successfully!")
    print("="*60 + "\n")


if __name__ == "__main__":
    run_all_tests()
