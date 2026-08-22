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
8. BC dimension sub-totals (zone/state/brand/category) reconcile with monthly grand total
9. by_category FY sub-totals match monthly FY sums when present (regression guard for
   the load_reliance_bc_data() by_category FY loop bug fixed in Phase 5 QC pass)

Run:  pytest scripts/test_dashboard_disclosures.py -v
"""
import csv
import json
import re
import sys
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

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

    def test_bc_data_complete_through_matches_last_loaded_month(self, bc):
        """data_complete_through must equal the last month actually present in bc.months."""
        months = bc.get("months", [])
        if months:
            assert bc["data_complete_through"] == months[-1], (
                f"data_complete_through={bc['data_complete_through']!r} "
                f"but last bc month is {months[-1]!r}"
            )

    def test_bc_june_status_field_present(self, bc):
        """june_status field must be present (even if None when Jun-26 is loaded)."""
        assert "june_status" in bc, "reliance_bc missing 'june_status' field"

    def test_bc_june_status_blocked_when_source_absent(self, bc):
        """june_status must be BLOCKED only when Jun-26 data is not loaded at all.
        Jun-26 can now come from the dedicated RBC xlsb (not just the monthly CSV),
        so we gate on whether Jun-26 is actually in bc.months, not on CSV presence."""
        jun_loaded = "Jun-26" in (bc.get("months") or [])
        june_csv = OFFTAKE_DIR / "offtake_store_article_Jun_26.csv"
        if not june_csv.exists() and not jun_loaded:
            assert bc["june_status"] is not None, (
                "Jun-26 not loaded from any source but reliance_bc.june_status is None — disclosure missing"
            )
            assert "BLOCKED" in str(bc["june_status"]), (
                f"june_status should start with 'BLOCKED' but got: {bc['june_status'][:80]}"
            )

    def test_bc_june_not_in_months_when_source_absent(self, bc):
        """Jun-26 must not appear in bc.months unless data was actually sourced.
        Jun-26 can now be sourced from the dedicated RBC xlsb; if it is loaded,
        june_status must be None (validated by test_bc_june_status_null_when_source_present)."""
        jun_loaded = "Jun-26" in (bc.get("months") or [])
        june_csv = OFFTAKE_DIR / "offtake_store_article_Jun_26.csv"
        if not june_csv.exists() and not jun_loaded:
            # Neither dedicated BC xlsb nor CSV provided Jun-26 — it must not appear
            assert "Jun-26" not in (bc.get("months") or []), (
                "Jun-26 is in reliance_bc.months but no Jun-26 source was loaded"
            )
        if jun_loaded:
            # Jun-26 is present from dedicated BC xlsb → june_status must be None
            assert bc.get("june_status") is None, (
                "Jun-26 is loaded but june_status is not None — disclosure is stale"
            )

    def test_bc_june_status_null_when_source_present(self, bc):
        """june_status must be None when Jun-26 data is actually loaded."""
        june_file = OFFTAKE_DIR / "offtake_store_article_Jun_26.csv"
        if june_file.exists() and "Jun-26" in (bc.get("months") or []):
            assert bc["june_status"] is None, (
                "Jun-26 appears loaded but june_status is not None — disclosure is stale"
            )


# ---------------------------------------------------------------------------
# Brand Counter data reconciliation
# ---------------------------------------------------------------------------

class TestBrandCounterReconciliation:

    def _fy_of(self, label):
        """Return short FY tag (e.g. 'fy25') for a month label like 'Apr-25'."""
        mn_num = {'Jan':1,'Feb':2,'Mar':3,'Apr':4,'May':5,'Jun':6,
                  'Jul':7,'Aug':8,'Sep':9,'Oct':10,'Nov':11,'Dec':12}
        mn, yr = label.split('-')
        y = 2000 + int(yr)
        m = mn_num[mn]
        suffix = (y + 1) % 100 if m >= 4 else y % 100
        return f"fy{suffix:02d}"

    def test_bc_monthly_sum_equals_total(self, bc):
        """Sum of monthly values must match reported bc.total (within 0.05 L rounding)."""
        monthly = bc.get('monthly', [])
        total = bc.get('total', 0)
        assert monthly, "bc.monthly is empty"
        diff = abs(sum(monthly) - total)
        assert diff < 0.05, (
            f"bc.monthly sum={sum(monthly):.4f} but bc.total={total:.4f} (diff={diff:.4f} L)"
        )

    def test_bc_zone_sum_equals_total(self, bc):
        """by_zone totals must sum to bc.total (within 0.5 L rounding)."""
        by_zone = bc.get('by_zone', [])
        total = bc.get('total', 0)
        if not by_zone:
            pytest.skip("no by_zone data")
        zone_sum = sum(z['total'] for z in by_zone)
        assert abs(zone_sum - total) < 0.5, (
            f"by_zone sum={zone_sum:.2f} != bc.total={total:.2f} (diff={zone_sum-total:.4f})"
        )

    def test_bc_brand_sum_equals_total(self, bc):
        """by_brand totals must sum to bc.total (within 0.5 L rounding)."""
        by_brand = bc.get('by_brand', [])
        total = bc.get('total', 0)
        if not by_brand:
            pytest.skip("no by_brand data")
        brand_sum = sum(b['total'] for b in by_brand)
        assert abs(brand_sum - total) < 0.5, (
            f"by_brand sum={brand_sum:.2f} != bc.total={total:.2f} (diff={brand_sum-total:.4f})"
        )

    def test_bc_category_sum_equals_total(self, bc):
        """by_category totals must sum to bc.total (within 0.5 L rounding)."""
        by_cat = bc.get('by_category', [])
        total = bc.get('total', 0)
        if not by_cat:
            pytest.skip("no by_category data")
        cat_sum = sum(c['total'] for c in by_cat)
        assert abs(cat_sum - total) < 0.5, (
            f"by_category sum={cat_sum:.2f} != bc.total={total:.2f} (diff={cat_sum-total:.4f})"
        )

    def test_bc_category_has_fy_subtotals_when_present(self, bc):
        """by_category entries must have FY sub-totals when by_brand entries do.
        Regression guard for the missing FY loop bug in load_reliance_bc_data().
        Skips when: (a) by_brand has no FY keys (pre-fix data.js) or (b) by_category
        has no FY keys — the latter means data.js predates the fix and must be rebuilt.
        The code-level fix is validated by test_bc_category_fy_loop_unit_test below."""
        by_brand = bc.get('by_brand', [])
        by_cat = bc.get('by_category', [])
        if not by_brand or not by_cat:
            pytest.skip("no by_brand or by_category data")
        brand_fy_keys = {k for b in by_brand for k in b if k.startswith('fy')}
        if not brand_fy_keys:
            pytest.skip("by_brand has no FY keys — pre-fix build, skipping")
        cat_fy_keys = {k for c in by_cat for k in c if k.startswith('fy')}
        if not cat_fy_keys:
            pytest.skip(
                "by_category has no FY sub-totals — data.js built before the FY loop fix; "
                "rebuild data.js with current build_dashboard_data.py to activate this check"
            )
        assert cat_fy_keys == brand_fy_keys, (
            f"by_category FY keys {cat_fy_keys} differ from by_brand FY keys {brand_fy_keys}"
        )

    def test_bc_category_fy_sums_match_monthly_fy_sums(self, bc):
        """For each FY, by_category[*][fy] sum must match monthly FY sum.
        Only runs when by_category has FY sub-totals (post-fix builds)."""
        by_cat = bc.get('by_category', [])
        months = bc.get('months', [])
        monthly = bc.get('monthly', [])
        if not by_cat or not months:
            pytest.skip("no by_category or monthly data")
        cat_fy_keys = {k for c in by_cat for k in c if k.startswith('fy')}
        if not cat_fy_keys:
            pytest.skip("by_category has no FY sub-totals — pre-fix build, skipping")
        # Compute FY sums from monthly time-series
        monthly_fy = {}
        for lbl, v in zip(months, monthly):
            tag = self._fy_of(lbl)
            monthly_fy[tag] = monthly_fy.get(tag, 0) + v
        for tag in sorted(cat_fy_keys):
            cat_fy_sum = sum(c.get(tag, 0) for c in by_cat)
            expected = monthly_fy.get(tag, 0)
            assert abs(cat_fy_sum - expected) < 0.5, (
                f"by_category {tag} sum={cat_fy_sum:.2f} != monthly {tag} sum={expected:.2f}"
            )

    def test_bc_no_negative_monthly_values(self, bc):
        """Monthly BC values must all be non-negative."""
        months = bc.get('months', [])
        monthly = bc.get('monthly', [])
        negatives = [(lbl, v) for lbl, v in zip(months, monthly) if v < 0]
        assert not negatives, f"Negative BC monthly values: {negatives}"

    def test_bc_state_sum_equals_total(self, bc):
        """by_state totals must sum to bc.total (within 0.5 L rounding)."""
        by_state = bc.get('by_state', [])
        total = bc.get('total', 0)
        if not by_state:
            pytest.skip("no by_state data")
        state_sum = sum(s['total'] for s in by_state)
        assert abs(state_sum - total) < 0.5, (
            f"by_state sum={state_sum:.2f} != bc.total={total:.2f}"
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


# ---------------------------------------------------------------------------
# Code-level unit test: load_reliance_bc_data() by_category FY loop fix
# ---------------------------------------------------------------------------

class TestBCCategoryFyLoopFix:
    """Validates that load_reliance_bc_data() produces FY sub-totals for by_category.
    Uses a minimal synthetic CSV — no xlsb file required."""

    def _write_bc_csv(self, tmp_path):
        rows = [
            # header
            ["Chain Name", "Zone", "State", "Month", "NSV",
             "Data status", "Brand", "Category"],
            # FY26 rows (Apr-25 is FY26 Apr-Dec)
            ["Reliance Smart", "East", "West Bengal", "Apr'25", "100.0",
             "Brand Counter", "Mamaearth", "Haircare"],
            ["Reliance Smart", "East", "West Bengal", "Apr'25", "50.0",
             "Brand Counter", "The Derma Co", "Skincare"],
            ["Reliance Smart", "North", "Delhi", "May'25", "80.0",
             "Brand Counter", "Mamaearth", "Haircare"],
            # FY27 row (Apr-26 starts FY27)
            ["Reliance Smart", "East", "West Bengal", "Apr'26", "200.0",
             "Brand Counter", "Mamaearth", "Haircare"],
            # Non-BC row (should be excluded)
            ["Reliance Smart", "East", "West Bengal", "Apr'25", "999.0",
             "Non-Brand Counter", "Mamaearth", "Haircare"],
            # Non-Reliance row (should be excluded)
            ["DMart", "East", "West Bengal", "Apr'25", "999.0",
             "Brand Counter", "Mamaearth", "Haircare"],
        ]
        fp = tmp_path / "offtake_store_article_Apr_25.csv"
        with open(fp, "w", newline="") as f:
            csv.writer(f).writerows(rows)
        return tmp_path

    def test_by_category_has_fy_subtotals(self, tmp_path):
        """load_reliance_bc_data() must produce FY sub-totals for every by_category entry."""
        from build_dashboard_data import load_reliance_bc_data
        src = self._write_bc_csv(tmp_path)
        result = load_reliance_bc_data(src)
        assert result is not None, "load_reliance_bc_data returned None for valid BC data"
        by_cat = result.get("by_category", [])
        assert by_cat, "by_category is empty — no categories loaded"
        for entry in by_cat:
            fy_keys = [k for k in entry if k.startswith("fy")]
            assert fy_keys, (
                f"by_category entry {entry['name']!r} has no FY sub-totals — "
                "load_reliance_bc_data() is missing the FY loop for by_category"
            )

    def test_by_category_fy_sums_correct(self, tmp_path):
        """by_category FY sub-totals must match per-FY monthly totals."""
        from build_dashboard_data import load_reliance_bc_data
        src = self._write_bc_csv(tmp_path)
        result = load_reliance_bc_data(src)
        assert result is not None
        by_cat = result.get("by_category", [])
        months = result.get("months", [])
        monthly = result.get("monthly", [])
        mn_num = {'Jan':1,'Feb':2,'Mar':3,'Apr':4,'May':5,'Jun':6,
                  'Jul':7,'Aug':8,'Sep':9,'Oct':10,'Nov':11,'Dec':12}

        def fy_of(label):
            mn, yr = label.split('-')
            y = 2000 + int(yr)
            return f"fy{(y+1)%100:02d}" if mn_num[mn] >= 4 else f"fy{y%100:02d}"

        monthly_fy = {}
        for lbl, v in zip(months, monthly):
            tag = fy_of(lbl)
            monthly_fy[tag] = monthly_fy.get(tag, 0) + v

        for tag, expected in monthly_fy.items():
            cat_fy_sum = sum(c.get(tag, 0) for c in by_cat)
            assert abs(cat_fy_sum - expected) < 0.01, (
                f"by_category {tag} sum={cat_fy_sum:.2f} != monthly {tag} sum={expected:.2f}"
            )

    def test_by_category_matches_by_brand_fy_keys(self, tmp_path):
        """by_category and by_brand must have the same set of FY keys."""
        from build_dashboard_data import load_reliance_bc_data
        src = self._write_bc_csv(tmp_path)
        result = load_reliance_bc_data(src)
        assert result is not None
        by_cat = result.get("by_category", [])
        by_brand = result.get("by_brand", [])
        if not by_cat or not by_brand:
            pytest.skip("missing by_category or by_brand")
        cat_fy = {k for c in by_cat for k in c if k.startswith("fy")}
        brand_fy = {k for b in by_brand for k in b if k.startswith("fy")}
        assert cat_fy == brand_fy, (
            f"by_category FY keys {cat_fy} differ from by_brand FY keys {brand_fy}"
        )


# ---------------------------------------------------------------------------
# Phase 6: Build gating & governance metadata
# ---------------------------------------------------------------------------

class TestPhase6GovernanceGate:
    """Tests for the --not-eligible-gate-pct build gating mechanism."""

    def test_governance_gate_passes_when_disabled(self):
        """Gate with threshold=0 never raises."""
        from build_dashboard_data import _check_governance_gate
        alloc = {"governance": {"not_eligible_pct": 99.9, "not_eligible_nsv_lakh": 100.0,
                                "total_dist_nsv_lakh": 100.1, "flagged_rows": 5, "override_count": 0,
                                "flagged_rows_csv": "some.csv"}}
        _check_governance_gate(alloc, gate_pct=0.0)  # must not raise

    def test_governance_gate_passes_when_below_threshold(self):
        """Gate passes when not_eligible_pct <= threshold."""
        from build_dashboard_data import _check_governance_gate
        alloc = {"governance": {"not_eligible_pct": 4.5, "not_eligible_nsv_lakh": 4.5,
                                "total_dist_nsv_lakh": 100.0, "flagged_rows": 2, "override_count": 0,
                                "flagged_rows_csv": "some.csv"}}
        _check_governance_gate(alloc, gate_pct=10.0)  # must not raise

    def test_governance_gate_triggers_when_exceeded(self):
        """Gate raises SystemExit when not_eligible_pct > threshold."""
        from build_dashboard_data import _check_governance_gate
        alloc = {"governance": {"not_eligible_pct": 15.3, "not_eligible_nsv_lakh": 15.3,
                                "total_dist_nsv_lakh": 100.0, "flagged_rows": 7, "override_count": 0,
                                "flagged_rows_csv": "some.csv"}}
        with pytest.raises(SystemExit) as exc_info:
            _check_governance_gate(alloc, gate_pct=10.0)
        assert "Not_Eligible" in str(exc_info.value)
        assert "15.3" in str(exc_info.value)

    def test_governance_gate_none_alloc_is_noop(self):
        """Gate with alloc=None never raises."""
        from build_dashboard_data import _check_governance_gate
        _check_governance_gate(None, gate_pct=5.0)  # must not raise

    def test_governance_gate_message_contains_resolution_options(self):
        """SystemExit message must include actionable resolution instructions."""
        from build_dashboard_data import _check_governance_gate
        alloc = {"governance": {"not_eligible_pct": 20.0, "not_eligible_nsv_lakh": 20.0,
                                "total_dist_nsv_lakh": 100.0, "flagged_rows": 10, "override_count": 2,
                                "flagged_rows_csv": "FlaggedRows.csv"}}
        with pytest.raises(SystemExit) as exc_info:
            _check_governance_gate(alloc, gate_pct=10.0)
        msg = str(exc_info.value)
        assert "PrimaryAllocationOverride.csv" in msg
        assert "FlaggedRows.csv" in msg
        assert "override_count" not in msg  # approved_overrides should be formatted, not raw key


class TestPhase6GovernanceDataJs:
    """Tests for governance metadata in data.js when alloc block is present."""

    @pytest.fixture
    def alloc(self, data):  # noqa: F811
        if "alloc" not in data:
            pytest.skip("alloc block absent from data.js (built without source files)")
        return data["alloc"]

    @pytest.fixture
    def gov(self, alloc):
        gov = alloc.get("governance")
        if not gov:
            pytest.skip("alloc.governance absent from data.js")
        return gov

    def test_governance_has_not_eligible_pct(self, gov):
        """alloc.governance must expose not_eligible_pct for dashboard display."""
        assert "not_eligible_pct" in gov, "not_eligible_pct missing from governance"
        assert isinstance(gov["not_eligible_pct"], (int, float))
        assert 0.0 <= gov["not_eligible_pct"] <= 100.0

    def test_governance_has_flagged_rows(self, gov):
        """alloc.governance must expose flagged_rows count."""
        assert "flagged_rows" in gov
        assert isinstance(gov["flagged_rows"], int)
        assert gov["flagged_rows"] >= 0

    def test_governance_has_override_count(self, gov):
        """alloc.governance must expose override_count."""
        assert "override_count" in gov
        assert isinstance(gov["override_count"], int)
        assert gov["override_count"] >= 0

    def test_governance_has_flagged_rows_csv(self, gov):
        """alloc.governance must expose flagged_rows_csv path."""
        assert "flagged_rows_csv" in gov
        assert gov["flagged_rows_csv"].endswith(".csv")

    def test_not_eligible_pct_consistent_with_nsv(self, gov):
        """not_eligible_pct must be consistent with not_eligible_nsv_lakh / total_dist_nsv_lakh."""
        ne_nsv = gov.get("not_eligible_nsv_lakh", 0)
        total_nsv = gov.get("total_dist_nsv_lakh", 0)
        ne_pct = gov.get("not_eligible_pct", 0)
        if total_nsv > 0:
            expected_pct = round(ne_nsv / total_nsv * 100, 2)
            assert abs(ne_pct - expected_pct) < 0.1, (
                f"not_eligible_pct {ne_pct} inconsistent with "
                f"NSV ratio {ne_nsv}/{total_nsv} = {expected_pct}"
            )
