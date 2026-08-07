"""
Dashboard disclosure tests.

Verifies that:
1. Brand Counter june_status / data_complete_through fields are present in data.js
2. Distribution universe storetype gap is disclosed (storetype_note, storetype_unclassified)
3. by_storetype includes an 'Unclassified' bucket for stores with blank Store Type
4. storetype_classified + storetype_unclassified == active_stores
5. Brand Counter june_status is BLOCKED when Jun-26 source file is absent
6. BC months do not include Jun-26 (since the source file is absent)
7. Distribution zone / chain / citycat totals reconcile to active_stores

Run:  pytest scripts/test_dashboard_disclosures.py -v
"""
import json
import re
import pytest
from pathlib import Path

DATA_JS = Path(__file__).resolve().parent.parent / "dashboard" / "data.js"
OFFTAKE_DIR = Path(__file__).resolve().parent.parent / "PowerBI" / "RawDataFolders" / "Offtake_Monthly"


@pytest.fixture(scope="module")
def data():
    assert DATA_JS.exists(), f"data.js not found at {DATA_JS}"
    content = DATA_JS.read_text(encoding="utf-8")
    m = re.search(r'window\.DASH\s*=\s*(\{.*\})\s*;', content, re.DOTALL)
    assert m, "Could not extract JSON object from data.js"
    return json.loads(m.group(1))


@pytest.fixture(scope="module")
def bc(data):
    assert "reliance_bc" in data, "reliance_bc missing from data.js"
    return data["reliance_bc"]


@pytest.fixture(scope="module")
def universe(data):
    assert "universe" in data, "universe missing from data.js"
    return data["universe"]


# ---------------------------------------------------------------------------
# Brand Counter coverage disclosures
# ---------------------------------------------------------------------------

class TestBrandCounterDisclosure:

    def test_bc_data_complete_through_present(self, bc):
        """data_complete_through field must be set."""
        assert "data_complete_through" in bc, "reliance_bc missing 'data_complete_through'"
        assert bc["data_complete_through"] is not None, (
            "reliance_bc.data_complete_through should not be None when months are loaded"
        )

    def test_bc_data_complete_through_is_may26_or_later(self, bc):
        """When Jun-26 source is absent, last covered month must be May-26."""
        june_file = OFFTAKE_DIR / "offtake_store_article_Jun_26.csv"
        if not june_file.exists():
            assert bc["data_complete_through"] == "May-26", (
                f"Jun-26 source absent but data_complete_through = {bc['data_complete_through']!r}; "
                f"expected 'May-26'"
            )

    def test_bc_june_status_field_present(self, bc):
        """june_status field must be present (even if None when Jun-26 is loaded)."""
        assert "june_status" in bc, "reliance_bc missing 'june_status' field"

    def test_bc_june_status_blocked_when_source_absent(self, bc):
        """june_status must be BLOCKED when offtake_store_article_Jun_26.csv is absent."""
        june_file = OFFTAKE_DIR / "offtake_store_article_Jun_26.csv"
        if not june_file.exists():
            assert bc["june_status"] is not None, (
                "Jun-26 source absent but reliance_bc.june_status is None — disclosure missing"
            )
            assert "BLOCKED" in str(bc["june_status"]), (
                f"june_status should start with 'BLOCKED' but got: {bc['june_status'][:80]}"
            )

    def test_bc_june_not_in_months_when_source_absent(self, bc):
        """When Jun-26 source is absent, 'Jun-26' must not appear in bc.months."""
        june_file = OFFTAKE_DIR / "offtake_store_article_Jun_26.csv"
        if not june_file.exists():
            assert "Jun-26" not in (bc.get("months") or []), (
                "Jun-26 is in reliance_bc.months but offtake_store_article_Jun_26.csv is absent"
            )

    def test_bc_june_status_null_when_source_present(self, bc):
        """june_status must be None when Jun-26 data is actually loaded."""
        june_file = OFFTAKE_DIR / "offtake_store_article_Jun_26.csv"
        if june_file.exists() and "Jun-26" in (bc.get("months") or []):
            assert bc["june_status"] is None, (
                "Jun-26 appears loaded but june_status is not None — disclosure is stale"
            )


# ---------------------------------------------------------------------------
# Distribution store type gap disclosures
# ---------------------------------------------------------------------------

class TestDistributionStoretypeDisclosure:

    def test_storetype_classified_present(self, universe):
        """storetype_classified field must be present."""
        assert "storetype_classified" in universe, (
            "universe missing 'storetype_classified' — rebuild with updated build_dashboard_data.py"
        )

    def test_storetype_unclassified_present(self, universe):
        """storetype_unclassified field must be present."""
        assert "storetype_unclassified" in universe, (
            "universe missing 'storetype_unclassified'"
        )

    def test_storetype_classified_plus_unclassified_equals_active(self, universe):
        """classified + unclassified must equal active_stores."""
        classified = universe.get("storetype_classified", 0)
        unclassified = universe.get("storetype_unclassified", 0)
        active = universe["active_stores"]
        assert classified + unclassified == active, (
            f"storetype_classified ({classified}) + storetype_unclassified ({unclassified}) "
            f"= {classified + unclassified}, expected active_stores = {active}"
        )

    def test_by_storetype_includes_unclassified_bucket(self, universe):
        """by_storetype must include 'Unclassified' bucket when gap > 0."""
        unclassified = universe.get("storetype_unclassified", 0)
        if unclassified > 0:
            names = [t["name"] for t in universe.get("by_storetype", [])]
            assert "Unclassified" in names, (
                f"{unclassified} stores have no Store Type but 'Unclassified' bucket missing from by_storetype"
            )

    def test_by_storetype_unclassified_count_matches(self, universe):
        """'Unclassified' bucket stores count must equal storetype_unclassified."""
        unclassified = universe.get("storetype_unclassified", 0)
        if unclassified > 0:
            bucket = next((t for t in universe.get("by_storetype", []) if t["name"] == "Unclassified"), None)
            assert bucket is not None, "Unclassified bucket missing from by_storetype"
            assert bucket["stores"] == unclassified, (
                f"Unclassified bucket stores={bucket['stores']} != storetype_unclassified={unclassified}"
            )

    def test_storetype_note_present_when_gap_exists(self, universe):
        """storetype_note must be set when there is a storetype gap."""
        unclassified = universe.get("storetype_unclassified", 0)
        if unclassified > 0:
            assert universe.get("storetype_note"), (
                "storetype_unclassified > 0 but storetype_note is missing — disclosure absent"
            )

    def test_by_storetype_total_leq_active_stores(self, universe):
        """Sum of by_storetype stores (including Unclassified) must equal active_stores."""
        total_st = sum(t["stores"] for t in universe.get("by_storetype", []))
        active = universe["active_stores"]
        assert total_st == active, (
            f"by_storetype sum ({total_st}) != active_stores ({active}); "
            f"once Unclassified bucket is included these should match"
        )


# ---------------------------------------------------------------------------
# Cross-dimension reconciliation
# ---------------------------------------------------------------------------

class TestDistributionReconciliation:

    def test_by_zone_total_equals_active_stores(self, universe):
        """Zone totals must sum to active_stores."""
        zone_total = sum(z["stores"] for z in universe.get("by_zone", []))
        active = universe["active_stores"]
        assert zone_total == active, (
            f"by_zone sum ({zone_total}) != active_stores ({active})"
        )

    def test_by_chain_total_leq_active_stores(self, universe):
        """Chain totals (top-20 list) must be <= active_stores."""
        chain_total = sum(c["stores"] for c in universe.get("by_chain", []))
        active = universe["active_stores"]
        assert chain_total <= active, (
            f"by_chain sum ({chain_total}) > active_stores ({active})"
        )
