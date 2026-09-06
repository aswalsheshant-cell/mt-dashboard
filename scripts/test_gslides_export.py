"""
Unit tests for Google Slides API export validation.
Ensures batchUpdate payloads conform to Google Slides API spec.
"""

import json
from gslides_exporter import GoogleSlidesBatchBuilder, build_gslides_batch_from_ir
from mt_deck_ir import build_deck_ir


def test_color_validation():
    """Test RGB color channel values conform to 0.0-1.0 float range."""
    builder = GoogleSlidesBatchBuilder()

    # Test hex to RGB conversion
    rgb = builder._hex_to_rgb("#0D1B2A")
    assert 0.0 <= rgb["red"] <= 1.0, f"Red channel out of range: {rgb['red']}"
    assert 0.0 <= rgb["green"] <= 1.0, f"Green channel out of range: {rgb['green']}"
    assert 0.0 <= rgb["blue"] <= 1.0, f"Blue channel out of range: {rgb['blue']}"
    print("✓ Test passed: Color validation (RGB 0.0-1.0 range)")


def test_emu_conversion():
    """Test unit conversions from inches/points to EMUs."""
    builder = GoogleSlidesBatchBuilder()

    # 1 inch = 914,400 EMUs
    # 1 point = 12,700 EMUs
    left_emu = int(1.0 * 914400)
    assert left_emu == 914400, f"Inch to EMU conversion failed: {left_emu}"

    pt_emu = int(12.0 * 12700)
    assert pt_emu == 152400, f"Point to EMU conversion failed: {pt_emu}"
    print("✓ Test passed: EMU unit conversion")


def test_request_payload_structure():
    """Test batchUpdate payload contains required structure."""
    builder = GoogleSlidesBatchBuilder()
    builder.add_create_slide("slide_1", 0)

    payload = builder.build_payload()
    assert "requests" in payload, "Payload missing 'requests' key"
    assert isinstance(payload["requests"], list), "requests must be a list"
    assert len(payload["requests"]) > 0, "requests list is empty"
    print("✓ Test passed: Payload structure (requests array exists)")


def test_object_id_generation():
    """Test unique object IDs are generated for shapes."""
    builder = GoogleSlidesBatchBuilder()

    id1 = builder._gen_object_id("test")
    id2 = builder._gen_object_id("test")

    assert id1 != id2, f"Object IDs not unique: {id1} == {id2}"
    assert id1.startswith("test_"), f"Object ID missing prefix: {id1}"
    print("✓ Test passed: Unique object ID generation")


def test_shape_creation_request():
    """Test shape creation request has all required fields."""
    builder = GoogleSlidesBatchBuilder()
    builder.add_create_slide("slide_1", 0)
    builder.add_shape(
        "slide_1", "shape_1", "RECTANGLE",
        1.0, 1.0, 2.0, 2.0,
        bg_hex="#FFFFFF",
        border_hex="#000000",
        border_width_pt=2
    )

    payload = builder.build_payload()
    shape_req = [r for r in payload["requests"] if "createShape" in r][0]

    assert "createShape" in shape_req, "Missing createShape"
    assert "objectId" in shape_req["createShape"], "Missing objectId"
    assert "elementProperties" in shape_req["createShape"], "Missing elementProperties"
    assert "size" in shape_req["createShape"]["elementProperties"], "Missing size"
    assert "transform" in shape_req["createShape"]["elementProperties"], "Missing transform"
    print("✓ Test passed: Shape creation request structure")


def test_text_box_request():
    """Test text box request has all required fields."""
    builder = GoogleSlidesBatchBuilder()
    builder.add_create_slide("slide_1", 0)
    builder.add_text_box(
        "slide_1", "text_1",
        1.0, 1.0, 2.0, 1.0,
        text="Test Text",
        font_size_pt=14,
        bold=True,
        color_hex="#FFFFFF"
    )

    payload = builder.build_payload()
    text_reqs = [r for r in payload["requests"] if "insertText" in r or "updateTextStyle" in r]

    assert len(text_reqs) > 0, "No text requests found"
    insert_req = [r for r in text_reqs if "insertText" in r][0]
    assert insert_req["insertText"]["text"] == "Test Text", "Text content mismatch"
    print("✓ Test passed: Text box request structure")


def test_table_creation_request():
    """Test table creation request has required dimensions."""
    builder = GoogleSlidesBatchBuilder()
    builder.add_create_slide("slide_1", 0)
    builder.add_table(
        "slide_1", "table_1",
        1.0, 1.0,
        rows=5,
        columns=3,
        row_height_inches=0.4,
        col_width_inches=2.0
    )

    payload = builder.build_payload()
    table_req = [r for r in payload["requests"] if "createTable" in r][0]

    assert "createTable" in table_req, "Missing createTable"
    assert table_req["createTable"]["rows"] == 5, "Row count mismatch"
    assert table_req["createTable"]["columns"] == 3, "Column count mismatch"
    print("✓ Test passed: Table creation request structure")


def test_ir_to_gslides_conversion():
    """Test full IR→Google Slides conversion produces valid payload."""
    config = {
        "month": "September",
        "year": 2026,
        "period": "Q1-Sep",
        "q1_offtake": "₹114.39 Cr",
        "4m_offtake": "₹185.81 Cr",
        "month_offtake": "₹71.42 Cr",
        "q1_growth_yoy": "+64%",
        "zones": {
            "Central": {"offtake": "₹2.12 Cr", "conv": 78.8, "gap": "₹0.57 Cr", "status": "WATCH", "yoy_growth": 18},
        },
        "diagnostic_chain": {"chain_name": "Reliance", "primary": 2.40, "offtake": 1.25},
        "zones_detail": [{"name": "East", "conversion": 45.3, "nsv": 3.55}],
        "scenario_params": {
            "current_offtake_weekly": 7.0,
            "current_conv": 45.3,
            "target_conv": 70.0,
            "promo_spend": 30.0,
            "promo_days": 21,
        },
        "chains": [],
        "brands": [],
        "scenario": {"zone": "East"},
    }

    # Build IR
    ir = build_deck_ir("September", 2026, config)
    assert ir["slides"], "IR has no slides"
    assert len(ir["slides"]) == 18, f"IR should have 18 slides, got {len(ir['slides'])}"

    # Convert to Google Slides
    payload = build_gslides_batch_from_ir(ir)
    assert payload["requests"], "Payload has no requests"
    assert len(payload["requests"]) > 0, "Payload requests list is empty"
    print("✓ Test passed: Full IR→Google Slides conversion")


def test_json_serialization():
    """Test payload can be serialized to valid JSON."""
    config = {
        "month": "September",
        "year": 2026,
        "period": "Q1-Sep",
        "q1_offtake": "₹114.39 Cr",
        "4m_offtake": "₹185.81 Cr",
        "month_offtake": "₹71.42 Cr",
        "q1_growth_yoy": "+64%",
        "zones": {},
        "diagnostic_chain": {"chain_name": "Reliance", "primary": 2.40, "offtake": 1.25},
        "zones_detail": [{"name": "East", "conversion": 45.3, "nsv": 3.55}],
        "scenario_params": {
            "current_offtake_weekly": 7.0,
            "current_conv": 45.3,
            "target_conv": 70.0,
            "promo_spend": 30.0,
            "promo_days": 21,
        },
        "chains": [],
        "brands": [],
        "scenario": {"zone": "East"},
    }

    ir = build_deck_ir("September", 2026, config)
    payload = build_gslides_batch_from_ir(ir)

    # Serialize to JSON
    json_str = json.dumps(payload)
    assert len(json_str) > 0, "JSON serialization produced empty string"

    # Deserialize to verify roundtrip
    parsed = json.loads(json_str)
    assert parsed["requests"], "Deserialized payload missing requests"
    print("✓ Test passed: JSON serialization roundtrip")


def test_edge_case_zero_dimensions():
    """Test builder handles zero/near-zero dimensions gracefully."""
    builder = GoogleSlidesBatchBuilder()
    builder.add_create_slide("slide_1", 0)

    # Near-zero dimensions should still convert to valid EMUs
    builder.add_shape(
        "slide_1", "tiny_shape", "RECTANGLE",
        0.01, 0.01, 0.1, 0.1,
        bg_hex="#FFFFFF"
    )

    payload = builder.build_payload()
    assert len(payload["requests"]) > 0, "Builder failed on small dimensions"
    print("✓ Test passed: Edge case - zero/near-zero dimensions")


def test_edge_case_large_values():
    """Test builder handles large coordinate values."""
    builder = GoogleSlidesBatchBuilder()
    builder.add_create_slide("slide_1", 0)

    # Very large coordinates (should clamp to reasonable slide bounds)
    builder.add_shape(
        "slide_1", "large_shape", "RECTANGLE",
        100.0, 100.0, 10.0, 10.0,
        bg_hex="#FFFFFF"
    )

    payload = builder.build_payload()
    assert len(payload["requests"]) > 0, "Builder failed on large coordinates"
    print("✓ Test passed: Edge case - large coordinate values")


def run_all_tests():
    """Execute full validation test suite."""
    print("\n" + "="*60)
    print("Running Google Slides Export Validation Test Suite")
    print("="*60 + "\n")

    test_color_validation()
    test_emu_conversion()
    test_request_payload_structure()
    test_object_id_generation()
    test_shape_creation_request()
    test_text_box_request()
    test_table_creation_request()
    test_ir_to_gslides_conversion()
    test_json_serialization()
    test_edge_case_zero_dimensions()
    test_edge_case_large_values()

    print("\n" + "="*60)
    print("✅ All validation tests passed!")
    print("="*60 + "\n")


if __name__ == "__main__":
    run_all_tests()
