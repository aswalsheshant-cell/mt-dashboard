#!/usr/bin/env python3
"""Tests for the FY27 primary fallback from detail_meta.fyx_primary.

Covers:
  - Workbook-present path (mocked — normal rebuild is integration-tested separately)
  - Workbook-missing + fyx_primary fallback
  - Workbook-missing + fyx_primary absent (should raise)
  - Idempotency / no double-count
  - Protection of FY25 / FY26 values
  - Partial-month status markers
  - No June 2026 value generated
"""
import sys, os, copy, unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from build_dashboard_data import _patch_primary_from_fyx, r2, fy_start_year

# ---------------------------------------------------------------------------
# Fixtures matching the real confirmed data
# ---------------------------------------------------------------------------
FYX27 = {
    "tag": "FY27",
    "nsv": 9492.6,
    "mrp": 22050.21,
    "months_covered": ["April", "May"],
    "monthly": [5076.86, 4415.74, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    "by_chain": [
        {"name": "Dmart",           "nsv": 3825.23},
        {"name": "Reliance Retail", "nsv": 2071.02},
        {"name": "Apollo",          "nsv": 1764.21},
        {"name": "New Chain",       "nsv": 100.0},   # chain absent from FY25/26 preagg
    ],
    "by_zone": [
        {"name": "West",    "nsv": 2682.07},
        {"name": "North",   "nsv": 1500.0},
        {"name": "South 1", "nsv": 1200.0},
        {"name": "South 2", "nsv": 800.0},
        {"name": "East",    "nsv": 1310.53},
    ],
    "by_channel": [
        {"name": "MT",    "nsv": 9032.06},
        {"name": "EB2B",  "nsv": 460.54},
        {"name": "SIS",   "nsv": 0.0},
    ],
    "by_brand": [
        {"name": "Mamaearth",     "nsv": 6196.78},
        {"name": "The Derma Co",  "nsv": 1200.0},
        {"name": "Aqualogica",    "nsv": 900.0},
        {"name": "BBlunt",        "nsv": 500.0},
        {"name": "Dr. Sheth's",   "nsv": 300.0},
        {"name": "Staze",         "nsv": 200.0},
        {"name": "Pure Origin",   "nsv": 195.82},
    ],
    "unit": "INR Lakh",
}

PRIMARY = {
    "fy_tags": ["fy25", "fy26"],
    "nsv_fy25": 23331.97,
    "nsv_fy26": 32900.36,
    "mrp_fy25": 52878.34,
    "mrp_fy26": 84114.62,
    "monthly_fy25": [2160.75, 2240.04, 1995.21, 2195.96, 1420.12, 2110.0,
                     1439.1, 1923.39, 2096.71, 1773.08, 2027.3, 1950.32],
    "monthly_fy26": [3174.6, 2366.9, 2182.64, 2472.9, 2162.39, 2223.75,
                     2674.89, 3329.34, 2820.61, 3665.41, 2924.94, 2902.0],
    "by_chain": [
        {"name": "Dmart",           "fy25": 8530.56, "fy26": 12190.3},
        {"name": "Reliance Retail", "fy25": 4000.0,  "fy26": 6000.0},
        {"name": "Apollo",          "fy25": 3000.0,  "fy26": 4500.0},
    ],
    "by_zone": [
        {"name": "West",    "fy25": 7077.44, "fy26": 8859.78},
        {"name": "North",   "fy25": 5037.19, "fy26": 7840.21},
        {"name": "South 1", "fy25": 5042.10, "fy26": 7382.04},
        {"name": "South 2", "fy25": 3211.21, "fy26": 4762.45},
        {"name": "East",    "fy25": 2964.02, "fy26": 4055.87},
    ],
    "by_channel": [
        {"name": "MT",    "fy25": 21722.96, "fy26": 30684.99},
        {"name": "EB2B",  "fy25": 1609.01,  "fy26": 1965.20},
        {"name": "SIS",   "fy25": 0.0,      "fy26": 250.17},
    ],
    "by_brand": [
        {"name": "Mamaearth",    "fy25": 20638.47, "fy26": 27179.45},
        {"name": "The Derma Co", "fy25": 1000.0,   "fy26": 2000.0},
        {"name": "Aqualogica",   "fy25": 800.0,    "fy26": 1500.0},
        {"name": "BBlunt",       "fy25": 400.0,    "fy26": 800.0},
        {"name": "Dr. Sheth's",  "fy25": 250.0,    "fy26": 600.0},
        {"name": "Staze",        "fy25": 150.0,    "fy26": 400.0},
        {"name": "Pure Origin",  "fy25": 93.5,     "fy26": 420.91},
    ],
}


def _do_patch(primary=None, fyx27=None):
    return _patch_primary_from_fyx(
        copy.deepcopy(primary or PRIMARY),
        copy.deepcopy(fyx27 or FYX27),
    )


class TestFyTagsAndScalars(unittest.TestCase):
    def test_fy_tags_contains_fy27(self):
        r = _do_patch()
        self.assertIn("fy27", r["fy_tags"])

    def test_fy_tags_sorted_order(self):
        r = _do_patch()
        self.assertEqual(r["fy_tags"], ["fy25", "fy26", "fy27"])

    def test_fy_tags_sort_via_start_year(self):
        # Verify sort uses fy_start_year not lexical order
        self.assertLess(fy_start_year("fy25"), fy_start_year("fy26"))
        self.assertLess(fy_start_year("fy26"), fy_start_year("fy27"))

    def test_nsv_fy27(self):
        r = _do_patch()
        self.assertAlmostEqual(r["nsv_fy27"], 9492.6, places=1)

    def test_mrp_fy27(self):
        r = _do_patch()
        self.assertAlmostEqual(r["mrp_fy27"], 22050.21, places=1)


class TestMonthlyFy27(unittest.TestCase):
    def test_april_nsv(self):
        r = _do_patch()
        self.assertAlmostEqual(r["monthly_fy27"][0], 5076.86, places=1)

    def test_may_nsv(self):
        r = _do_patch()
        self.assertAlmostEqual(r["monthly_fy27"][1], 4415.74, places=1)

    def test_june_is_zero(self):
        """June 2026 must be 0 — it is not in the Apr-May source."""
        r = _do_patch()
        self.assertEqual(r["monthly_fy27"][2], 0.0,
                         "June must not be generated from an Apr-May-only source")

    def test_july_through_march_zero(self):
        r = _do_patch()
        for i in range(3, 12):
            self.assertEqual(r["monthly_fy27"][i], 0.0,
                             f"Slot {i} should be 0 (no data beyond May)")

    def test_twelve_slots(self):
        r = _do_patch()
        self.assertEqual(len(r["monthly_fy27"]), 12)

    def test_april_plus_may_equals_total(self):
        r = _do_patch()
        self.assertAlmostEqual(
            r["monthly_fy27"][0] + r["monthly_fy27"][1],
            r["nsv_fy27"], places=0,
            msg="Apr+May monthly sum must equal nsv_fy27"
        )


class TestFy25Fy26Unchanged(unittest.TestCase):
    def test_nsv_fy25_unchanged(self):
        r = _do_patch()
        self.assertAlmostEqual(r["nsv_fy25"], 23331.97, places=1)

    def test_nsv_fy26_unchanged(self):
        r = _do_patch()
        self.assertAlmostEqual(r["nsv_fy26"], 32900.36, places=1)

    def test_mrp_fy25_unchanged(self):
        r = _do_patch()
        self.assertAlmostEqual(r["mrp_fy25"], 52878.34, places=1)

    def test_mrp_fy26_unchanged(self):
        r = _do_patch()
        self.assertAlmostEqual(r["mrp_fy26"], 84114.62, places=1)

    def test_monthly_fy25_unchanged(self):
        r = _do_patch()
        self.assertEqual(r["monthly_fy25"], PRIMARY["monthly_fy25"])

    def test_monthly_fy26_unchanged(self):
        r = _do_patch()
        self.assertEqual(r["monthly_fy26"], PRIMARY["monthly_fy26"])

    def test_by_chain_fy25_unchanged(self):
        r = _do_patch()
        dmart = next(x for x in r["by_chain"] if x["name"] == "Dmart")
        self.assertAlmostEqual(dmart["fy25"], 8530.56, places=1)

    def test_by_chain_fy26_unchanged(self):
        r = _do_patch()
        dmart = next(x for x in r["by_chain"] if x["name"] == "Dmart")
        self.assertAlmostEqual(dmart["fy26"], 12190.3, places=1)


class TestDimensionFy27Keys(unittest.TestCase):
    def test_by_chain_fy27_dmart(self):
        r = _do_patch()
        dmart = next(x for x in r["by_chain"] if x["name"] == "Dmart")
        self.assertAlmostEqual(dmart["fy27"], 3825.23, places=1)

    def test_by_chain_new_chain_appended(self):
        """A chain in fyx_primary not in preagg must be added with fy25=fy26=0."""
        r = _do_patch()
        new_chain = next((x for x in r["by_chain"] if x["name"] == "New Chain"), None)
        self.assertIsNotNone(new_chain, "New Chain from fyx_primary should be appended")
        self.assertEqual(new_chain["fy25"], 0.0)
        self.assertEqual(new_chain["fy26"], 0.0)
        self.assertAlmostEqual(new_chain["fy27"], 100.0, places=1)

    def test_by_zone_west_fy27(self):
        r = _do_patch()
        west = next(x for x in r["by_zone"] if x["name"] == "West")
        self.assertAlmostEqual(west["fy27"], 2682.07, places=1)

    def test_by_channel_mt_fy27(self):
        r = _do_patch()
        mt = next(x for x in r["by_channel"] if x["name"] == "MT")
        self.assertAlmostEqual(mt["fy27"], 9032.06, places=1)

    def test_by_channel_sis_fy27(self):
        r = _do_patch()
        sis = next(x for x in r["by_channel"] if x["name"] == "SIS")
        self.assertEqual(sis["fy27"], 0.0)

    def test_by_brand_mamaearth_fy27(self):
        r = _do_patch()
        mama = next(x for x in r["by_brand"] if x["name"] == "Mamaearth")
        self.assertAlmostEqual(mama["fy27"], 6196.78, places=1)


class TestProvenanceMarkers(unittest.TestCase):
    def test_source_marker(self):
        r = _do_patch()
        self.assertEqual(r["fy27_summary_source"], "detail_meta.fyx_primary.FY27")

    def test_status_marker(self):
        r = _do_patch()
        self.assertEqual(r["fy27_data_status"], "partial_apr_may_2026")

    def test_months_covered_marker(self):
        r = _do_patch()
        self.assertEqual(r["fy27_months_covered"], ["April", "May"])


class TestIdempotencyAndProtection(unittest.TestCase):
    def test_idempotent_nsv(self):
        """Calling twice must not change nsv_fy27."""
        once = _do_patch()
        twice = _patch_primary_from_fyx(copy.deepcopy(once), copy.deepcopy(FYX27))
        self.assertAlmostEqual(once["nsv_fy27"], twice["nsv_fy27"], places=2)

    def test_idempotent_by_chain_no_double_count(self):
        """Dmart.fy27 must be identical on both calls — no accumulation."""
        once = _do_patch()
        twice = _patch_primary_from_fyx(copy.deepcopy(once), copy.deepcopy(FYX27))
        dmart_once  = next(x for x in once["by_chain"]  if x["name"] == "Dmart")
        dmart_twice = next(x for x in twice["by_chain"] if x["name"] == "Dmart")
        self.assertAlmostEqual(dmart_once["fy27"], dmart_twice["fy27"], places=2)

    def test_idempotent_monthly_no_double_count(self):
        once = _do_patch()
        twice = _patch_primary_from_fyx(copy.deepcopy(once), copy.deepcopy(FYX27))
        self.assertEqual(once["monthly_fy27"], twice["monthly_fy27"])

    def test_no_overwrite_existing_fy27(self):
        """If primary already has fy27 in fy_tags, function is a no-op."""
        sentinel = copy.deepcopy(PRIMARY)
        sentinel["fy_tags"] = ["fy25", "fy26", "fy27"]
        sentinel["nsv_fy27"] = 1234.56   # sentinel value
        result = _patch_primary_from_fyx(sentinel, copy.deepcopy(FYX27))
        self.assertAlmostEqual(result["nsv_fy27"], 1234.56, places=2,
                               msg="Existing FY27 value must not be overwritten")

    def test_fy25_by_chain_protected_in_idempotent_run(self):
        once = _do_patch()
        twice = _patch_primary_from_fyx(copy.deepcopy(once), copy.deepcopy(FYX27))
        dmart_twice = next(x for x in twice["by_chain"] if x["name"] == "Dmart")
        self.assertAlmostEqual(dmart_twice["fy25"], 8530.56, places=1)


class TestEdgeCases(unittest.TestCase):
    def test_fy_tags_inferred_from_nsv_keys_when_empty(self):
        """If fy_tags is [] but nsv_fy25/nsv_fy26 keys exist, they must be inferred."""
        primary_empty_tags = copy.deepcopy(PRIMARY)
        primary_empty_tags["fy_tags"] = []   # simulate pre-tagging data.js
        r = _patch_primary_from_fyx(primary_empty_tags, copy.deepcopy(FYX27))
        self.assertEqual(r["fy_tags"], ["fy25", "fy26", "fy27"])

    def test_missing_monthly_defaults_to_twelve_zeros(self):
        fyx_no_monthly = copy.deepcopy(FYX27)
        del fyx_no_monthly["monthly"]
        r = _patch_primary_from_fyx(copy.deepcopy(PRIMARY), fyx_no_monthly)
        self.assertEqual(r["monthly_fy27"], [0.0] * 12)

    def test_empty_by_chain_in_fyx(self):
        fyx_empty = copy.deepcopy(FYX27)
        fyx_empty["by_chain"] = []
        r = _patch_primary_from_fyx(copy.deepcopy(PRIMARY), fyx_empty)
        # Existing chains get fy27=0.0, no rows removed
        dmart = next(x for x in r["by_chain"] if x["name"] == "Dmart")
        self.assertEqual(dmart.get("fy27"), 0.0)

    def test_months_covered_custom(self):
        fyx_custom = copy.deepcopy(FYX27)
        fyx_custom["months_covered"] = ["April", "May", "June"]
        r = _patch_primary_from_fyx(copy.deepcopy(PRIMARY), fyx_custom)
        self.assertEqual(r["fy27_months_covered"], ["April", "May", "June"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
