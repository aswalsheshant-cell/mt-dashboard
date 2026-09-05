"""Unit tests for MT Data Loader — JSON, CSV, and fallback merging."""

import os
import csv
import json
import tempfile
from mt_data_loader import MTDataLoader


def test_json_loader():
    """Test loading metrics from JSON file."""
    mock_payload = {
        "diagnostic_chain": {"chain_name": "DMart", "primary": 3.10, "offtake": 2.45}
    }
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tmp:
        json.dump(mock_payload, tmp)
        tmp_path = tmp.name

    try:
        loader = MTDataLoader(fallback_config={"fallback_key": "val"})
        res = loader.load_from_json(tmp_path)

        assert res["diagnostic_chain"]["chain_name"] == "DMart"
        assert res["fallback_key"] == "val"
        print("✅ test_json_loader passed")
    finally:
        os.remove(tmp_path)


def test_csv_loader_zones():
    """Test loading zones from CSV directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create mock zones.csv
        zones_csv = os.path.join(tmpdir, "zones.csv")
        with open(zones_csv, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["zone_name", "offtake_nsv", "conversion_pct", "yoy_growth"])
            writer.writerow(["North", "4.2", "68.5", "22.0"])
            writer.writerow(["East", "3.5", "45.0", "18.0"])

        loader = MTDataLoader()
        res = loader.load_from_csv_directory(tmpdir)

        assert len(res["zones_detail"]) == 2
        assert res["zones_detail"][0]["name"] == "North"
        assert res["zones_detail"][0]["conversion"] == 68.5
        print("✅ test_csv_loader_zones passed")


def test_csv_loader_chains():
    """Test loading chains from CSV directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create mock chains.csv
        chains_csv = os.path.join(tmpdir, "chains.csv")
        with open(chains_csv, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["chain_name", "primary_cr", "offtake_cr", "conversion_pct", "growth_yoy"])
            writer.writerow(["Reliance", "2.40", "1.25", "52.1", "179.0"])

        loader = MTDataLoader()
        res = loader.load_from_csv_directory(tmpdir)

        assert res["diagnostic_chain"]["chain_name"] == "Reliance"
        assert res["diagnostic_chain"]["primary"] == 2.40
        assert res["diagnostic_chain"]["offtake"] == 1.25
        print("✅ test_csv_loader_chains passed")


def test_csv_loader_categories():
    """Test loading categories from CSV directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create mock categories.csv
        categories_csv = os.path.join(tmpdir, "categories.csv")
        with open(categories_csv, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["category_name", "share_pct", "growth_yoy", "hero_sku"])
            writer.writerow(["Mamaearth Core", "54.0", "22.4", "Onion Shampoo 250ml"])

        loader = MTDataLoader()
        res = loader.load_from_csv_directory(tmpdir)

        assert len(res["categories"]) == 1
        assert res["categories"][0]["name"] == "Mamaearth Core"
        assert res["categories"][0]["share"] == 54.0
        print("✅ test_csv_loader_categories passed")


def test_fallback_merge():
    """Test that dynamically loaded values override fallback defaults."""
    fallback = {
        "zones_detail": [{"name": "Old Zone", "nsv": 1.0}],
        "other_field": "preserved"
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        zones_csv = os.path.join(tmpdir, "zones.csv")
        with open(zones_csv, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["zone_name", "offtake_nsv", "conversion_pct", "yoy_growth"])
            writer.writerow(["New Zone", "5.0", "70.0", "25.0"])

        loader = MTDataLoader(fallback_config=fallback)
        res = loader.load_from_csv_directory(tmpdir)

        assert res["zones_detail"][0]["name"] == "New Zone"  # Overridden
        assert res["other_field"] == "preserved"  # Preserved from fallback
        print("✅ test_fallback_merge passed")


if __name__ == "__main__":
    test_json_loader()
    test_csv_loader_zones()
    test_csv_loader_chains()
    test_csv_loader_categories()
    test_fallback_merge()
    print("\n✅ All Data Loader tests passed.")
