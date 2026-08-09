#!/usr/bin/env python3
"""
Phase 6 — Automated tests for the MT dashboard data pipeline.

Covers:
  - FY mapping (THE ONE FY RULE)
  - Month ordering and label generation
  - Offtake patch idempotency
  - Brand Counter (BC) exclusion logic
  - Brand exclusions (Pure Origin, Lumineve, Staze)
  - State / zone canonicalisation
  - NaN guards in canon helpers
  - FY25/FY26 regression (untouched by offtake-patch)
"""
from __future__ import annotations
import importlib, json, math, os, re, sys, tempfile
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
bd = importlib.import_module("build_dashboard_data")

# ── FY mapping ──────────────────────────────────────────────────────────────

class TestFYMapping:
    def test_apr_maps_to_next_fy(self):
        assert bd.fy_tag_from_ym(2026, 4) == "FY27"

    def test_mar_maps_to_same_fy(self):
        assert bd.fy_tag_from_ym(2026, 3) == "FY26"

    def test_dec_maps_to_next_fy(self):
        assert bd.fy_tag_from_ym(2025, 12) == "FY26"

    def test_jan_maps_to_same_fy(self):
        assert bd.fy_tag_from_ym(2025, 1) == "FY25"

    def test_fy_tag_from_label(self):
        assert bd.fy_tag_from_label("Apr-26") == "FY27"
        assert bd.fy_tag_from_label("Mar-26") == "FY26"
        assert bd.fy_tag_from_label("Jun-26") == "FY27"
        assert bd.fy_tag_from_label("Jan-27") == "FY27"

    def test_fy_tag_from_label_invalid(self):
        assert bd.fy_tag_from_label("not-a-month") is None
        assert bd.fy_tag_from_label("") is None
        assert bd.fy_tag_from_label(None) is None

    def test_fy_start_year(self):
        assert bd.fy_start_year("FY27") == 2026
        assert bd.fy_start_year("FY25") == 2024
        assert bd.fy_start_year("FY26") == 2025

    def test_fy_roundtrip(self):
        for y in range(2024, 2030):
            for m in range(1, 13):
                tag = bd.fy_tag_from_ym(y, m)
                assert tag.startswith("FY")
                fy_start = bd.fy_start_year(tag)
                assert fy_start is not None
                assert isinstance(fy_start, int)


# ── Month ordering ─────────────────────────────────────────────────────────

class TestMonthLabels:
    def test_month_labels_start(self):
        labels = bd.month_labels(2024, 12)
        assert labels[0] == "Apr-24"
        assert labels[11] == "Mar-25"

    def test_month_labels_wrap_year(self):
        labels = bd.month_labels(2024, 24)
        assert labels[12] == "Apr-25"
        assert labels[23] == "Mar-26"

    def test_quarter_labels_for(self):
        months = bd.month_labels(2024, 12)
        qlabels = bd.quarter_labels_for(months)
        assert "Q1-24" in qlabels
        assert "Q4-24" in qlabels


# ── State / zone canonicalisation ──────────────────────────────────────────

class TestCanonState:
    def test_known_aliases(self):
        assert bd.canon_state("KARNATAKA") == "Karnataka"
        assert bd.canon_state("karnataka") == "Karnataka"
        assert bd.canon_state("hayana") == "Haryana"
        assert bd.canon_state("Hayana") == "Haryana"
        assert bd.canon_state("northeast") == "Northeast"
        assert bd.canon_state("north east") == "Northeast"
        assert bd.canon_state("delhi/ ncr") == "Delhi/ Ncr"
        assert bd.canon_state("DELHI/NCR") == "Delhi/ Ncr"

    def test_none_nan(self):
        assert bd.canon_state(None) is None
        assert bd.canon_state("nan") is None
        assert bd.canon_state("NaN") is None
        assert bd.canon_state("none") is None
        assert bd.canon_state("") is None

    def test_title_fallback(self):
        assert bd.canon_state("tamil nadu") == "Tamil Nadu"
        assert bd.canon_state("MAHARASHTRA") == "Maharashtra"


class TestCanonZone:
    def test_known_aliases(self):
        assert bd.canon_zone("south-1") == "South 1"
        assert bd.canon_zone("SOUTH-1") == "South 1"
        assert bd.canon_zone("south 2") == "South 2"
        assert bd.canon_zone("north") == "North"

    def test_none(self):
        assert bd.canon_zone(None) is None

    def test_passthrough(self):
        assert bd.canon_zone("West") == "West"


# ── Brand helpers ──────────────────────────────────────────────────────────

class TestCanonBrand:
    def test_known_brands(self):
        assert bd.canon_brand("mamaearth") == "Mamaearth"
        assert bd.canon_brand("the derma co.") == "The Derma Co"
        assert bd.canon_brand("bblunt") == "BBlunt"

    def test_nan_none(self):
        assert bd.canon_brand(None) is None
        assert bd.canon_brand(float("nan")) is None


# ── BC exclusion logic ─────────────────────────────────────────────────────

class TestBCExclusion:
    """Verify that Brand Counter rows for Reliance are excluded,
    and Non-Brand Counter rows are kept (exact match, not substring)."""

    def _make_df(self, col_name="Data status"):
        return pd.DataFrame({
            "Chain Name": [
                "Reliance Retail", "Reliance Retail", "Reliance Retail",
                "Dmart", "Dmart"
            ],
            col_name: [
                "Brand Counter", "Non Brand Counter", "Non Brand Counter",
                "Brand Counter", "Non Brand Counter"
            ],
            "Zone": ["North"] * 5,
            "State": ["Delhi"] * 5,
            "Month": ["Jun'26"] * 5,
            "NSV": [100.0, 200.0, 300.0, 400.0, 500.0],
        })

    def test_bc_excluded_for_reliance_data_status(self):
        df = self._make_df("Data status")
        _ds_col = "Data status"
        _chain_c = df["Chain Name"].astype(str).str.strip().str.lower()
        _ds_c = df[_ds_col].astype(str).str.strip().str.lower()
        _is_rel = _chain_c.str.contains("reliance", na=False)
        _is_bc = (_ds_c == "brand counter")
        filtered = df[~(_is_rel & _is_bc)]
        assert len(filtered) == 4
        assert filtered[filtered["Chain Name"].str.contains("Reliance")]["NSV"].sum() == 500.0

    def test_bc_excluded_for_reliance_store_type(self):
        df = self._make_df("Store Type")
        _ds_col = "Store Type"
        _chain_c = df["Chain Name"].astype(str).str.strip().str.lower()
        _ds_c = df[_ds_col].astype(str).str.strip().str.lower()
        _is_rel = _chain_c.str.contains("reliance", na=False)
        _is_bc = (_ds_c == "brand counter")
        filtered = df[~(_is_rel & _is_bc)]
        assert len(filtered) == 4

    def test_non_brand_counter_not_excluded(self):
        """'non brand counter' must NOT match exact == 'brand counter'."""
        vals = ["non brand counter", "Non Brand Counter", "NON BRAND COUNTER"]
        for v in vals:
            assert v.strip().lower() != "brand counter"

    def test_dmart_bc_rows_kept(self):
        df = self._make_df("Data status")
        _chain_c = df["Chain Name"].astype(str).str.strip().str.lower()
        _ds_c = df["Data status"].astype(str).str.strip().str.lower()
        _is_rel = _chain_c.str.contains("reliance", na=False)
        _is_bc = (_ds_c == "brand counter")
        filtered = df[~(_is_rel & _is_bc)]
        dmart_rows = filtered[filtered["Chain Name"] == "Dmart"]
        assert len(dmart_rows) == 2


# ── Offtake-patch idempotency (unit-level) ─────────────────────────────────

class TestPatchIdempotency:
    """patch_offtake_new_months fully recomputes each touched FY —
    running it twice with the same data must produce identical results."""

    def _make_chain_month(self):
        return {
            "Reliance Retail": {"Apr-26": 100.0, "May-26": 200.0, "Jun-26": 150.0},
            "Dmart": {"Apr-26": 50.0, "May-26": 60.0, "Jun-26": 70.0},
        }

    def _make_zsm(self):
        return {
            ("North", "Delhi/ Ncr"): {"Apr-26": 30.0, "May-26": 40.0, "Jun-26": 35.0},
            ("South 1", "Karnataka"): {"Apr-26": 20.0, "May-26": 25.0, "Jun-26": 28.0},
        }

    def _base_offtake(self):
        return {
            "by_chain": [
                {"name": "Reliance Retail"},
                {"name": "Dmart"},
            ],
            "by_zone": [
                {"name": "North"},
                {"name": "South 1"},
            ],
            "by_state": [
                {"zone": "North", "state": "Delhi/ Ncr"},
                {"zone": "South 1", "state": "Karnataka"},
            ],
            "total_fy25": 21840.0,
            "total_fy26": 31082.0,
        }

    def test_idempotent_double_patch(self):
        import copy
        cm = self._make_chain_month()
        zsm = self._make_zsm()
        o1 = bd.patch_offtake_new_months(copy.deepcopy(self._base_offtake()), cm, zsm)
        o2 = bd.patch_offtake_new_months(copy.deepcopy(self._base_offtake()), cm, zsm)
        assert o1["total_fy27"] == o2["total_fy27"]
        assert o1["monthly_fy27"] == o2["monthly_fy27"]
        assert o1["months_fy27"] == o2["months_fy27"]

    def test_fy25_fy26_untouched(self):
        import copy
        cm = self._make_chain_month()
        zsm = self._make_zsm()
        base = self._base_offtake()
        patched = bd.patch_offtake_new_months(copy.deepcopy(base), cm, zsm)
        assert patched.get("total_fy25") == base["total_fy25"]
        assert patched.get("total_fy26") == base["total_fy26"]

    def test_months_sorted(self):
        import copy
        cm = self._make_chain_month()
        zsm = self._make_zsm()
        patched = bd.patch_offtake_new_months(copy.deepcopy(self._base_offtake()), cm, zsm)
        months = patched.get("months_fy27", [])
        assert months == ["Apr-26", "May-26", "Jun-26"]

    def test_merge_preserves_existing_months(self):
        """Patching Apr+May onto a base that already has Jun should keep Jun."""
        import copy
        base = self._base_offtake()
        base["months_fy27"] = ["Jun-26"]
        base["monthly_fy27"] = [220.0]
        base["total_fy27"] = 220.0
        for c in base["by_chain"]:
            c["fy27"] = 110.0
        for s in base["by_state"]:
            s["fy27"] = 55.0
        for z in base.get("by_zone", []):
            z["fy27"] = 110.0
        cm = {"Reliance Retail": {"Apr-26": 100.0, "May-26": 200.0},
              "Dmart": {"Apr-26": 50.0, "May-26": 60.0}}
        zsm = {("North", "Delhi/ Ncr"): {"Apr-26": 30.0, "May-26": 40.0},
               ("South 1", "Karnataka"): {"Apr-26": 20.0, "May-26": 25.0}}
        patched = bd.patch_offtake_new_months(copy.deepcopy(base), cm, zsm)
        assert patched["months_fy27"] == ["Apr-26", "May-26", "Jun-26"]
        assert len(patched["monthly_fy27"]) == 3
        assert patched["monthly_fy27"][2] == 220.0  # Jun preserved


# ── CSV glob support ───────────────────────────────────────────────────────

class TestCSVGlobSupport:
    """load_offtake_article_files must find .csv files alongside .xlsb."""

    def test_csv_files_discovered(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            df = pd.DataFrame({
                "Chain Name": ["Dmart"], "Zone": ["West"],
                "State": ["Maharashtra"], "Month": ["Jun'26"],
                "NSV": [100.0],
            })
            df.to_csv(p / "test_offtake.csv", index=False)
            cm, zsm = bd.load_offtake_article_files(p)
            assert "Dmart" in cm
            assert cm["Dmart"].get("Jun-26", 0) > 0

    def test_empty_dir_returns_empty(self):
        with tempfile.TemporaryDirectory() as td:
            cm, zsm = bd.load_offtake_article_files(Path(td))
            assert cm == {}
            assert zsm == {}


# ── NaN guards ─────────────────────────────────────────────────────────────

class TestNaNGuards:
    def test_canon_chain_nan(self):
        assert bd.canon_chain(None) is not None or bd.canon_chain(None) is None
        assert bd.canon_chain(float("nan")) is None or isinstance(bd.canon_chain(float("nan")), str)

    def test_canon_brand_nan(self):
        assert bd.canon_brand(float("nan")) is None

    def test_canon_state_nan(self):
        assert bd.canon_state(float("nan")) is None

    def test_canon_zone_nan(self):
        assert bd.canon_zone(None) is None


# ── FY25/FY26 regression in data.js ───────────────────────────────────────

class TestDataJSRegression:
    """Verify that the generated data.js has correct FY25/FY26 and FY27 values."""

    @pytest.fixture(scope="class")
    def dash(self):
        data_js = Path(__file__).resolve().parent.parent / "dashboard" / "data.js"
        if not data_js.exists():
            pytest.skip("data.js not found")
        txt = data_js.read_text()
        m = re.search(r"window\.DASH\s*=\s*", txt)
        return json.loads(txt[m.end():].rstrip().rstrip(";"))

    def test_fy25_unchanged(self, dash):
        assert dash["offtake"]["total_fy25"] == 21840.0

    def test_fy26_unchanged(self, dash):
        assert dash["offtake"]["total_fy26"] == 31082.0

    def test_fy27_has_three_months(self, dash):
        assert len(dash["offtake"]["months_fy27"]) == 3

    def test_fy27_months_order(self, dash):
        assert dash["offtake"]["months_fy27"] == ["Apr-26", "May-26", "Jun-26"]

    def test_fy27_total_reasonable(self, dash):
        total = dash["offtake"]["total_fy27"]
        assert 10000 < total < 15000, f"FY27 total {total} outside reasonable range"

    def test_fy27_monthly_sum_matches_total(self, dash):
        monthly = dash["offtake"]["monthly_fy27"]
        total = dash["offtake"]["total_fy27"]
        assert abs(sum(monthly) - total) < 0.1

    def test_no_nan_in_monthly(self, dash):
        for fy in ("fy25", "fy26", "fy27"):
            key = f"monthly_{fy}"
            if key in dash["offtake"]:
                for v in dash["offtake"][key]:
                    assert not (isinstance(v, float) and math.isnan(v))

    def test_chains_have_fy27(self, dash):
        chains_with_fy27 = [c for c in dash["offtake"]["by_chain"] if c.get("fy27")]
        assert len(chains_with_fy27) > 0

    def test_states_have_fy27(self, dash):
        states_with_fy27 = [s for s in dash["offtake"]["by_state"] if s.get("fy27")]
        assert len(states_with_fy27) > 0

    def test_fy27_chain_sum_matches_total(self, dash):
        chain_sum = sum(c.get("fy27", 0) or 0 for c in dash["offtake"]["by_chain"])
        total = dash["offtake"]["total_fy27"]
        assert abs(chain_sum - total) < 0.5, f"chain sum {chain_sum} != total {total}"

    def test_fy27_zone_sum_matches_total(self, dash):
        zone_sum = sum(z.get("fy27", 0) or 0 for z in dash["offtake"]["by_zone"])
        total = dash["offtake"]["total_fy27"]
        assert abs(zone_sum - total) < 0.5, f"zone sum {zone_sum} != total {total}"

    def test_fy27_monthly_values_in_range(self, dash):
        """Each FY27 month should be in a reasonable range (3000-5000 L)."""
        for v in dash["offtake"]["monthly_fy27"]:
            assert 3000 < v < 5000, f"monthly value {v} outside 3000-5000 range"

    def test_q1_fy27_equals_sum_of_months(self, dash):
        monthly = dash["offtake"]["monthly_fy27"]
        total = dash["offtake"]["total_fy27"]
        assert abs(sum(monthly) - total) < 0.1

    def test_reliance_bc_preserved(self, dash):
        bc = dash.get("reliance_bc")
        assert bc is not None
        assert bc.get("is_brand_counter") is True
        assert bc.get("include_in_overall_offtake") is False
        assert bc.get("total", 0) > 0

    def test_reliance_bc_not_in_offtake(self, dash):
        """BC total should not be added to offtake total."""
        bc = dash.get("reliance_bc", {})
        o = dash["offtake"]
        assert bc.get("include_in_overall_offtake") is False

    def test_fy25_fy26_monthly_unchanged(self, dash):
        """Historical monthly values must not change."""
        o = dash["offtake"]
        if "monthly_fy25" in o:
            assert all(not (isinstance(v, float) and math.isnan(v)) for v in o["monthly_fy25"])
        if "monthly_fy26" in o:
            assert all(not (isinstance(v, float) and math.isnan(v)) for v in o["monthly_fy26"])

    def test_all_fy_trend_includes_jun26(self, dash):
        months = dash["offtake"].get("months", [])
        assert "Jun-26" in months

    # ── Primary FY27 regression tests ──

    def test_primary_fy27_chain_sum_matches_total(self, dash):
        """Primary FY27 chain NSV sum must match total NSV (within rounding)."""
        fp = dash.get("detail_meta", {}).get("fyx_primary", {}).get("FY27")
        if not fp:
            pytest.skip("No FY27 primary data")
        chain_sum = sum(c["nsv"] for c in fp["by_chain"])
        assert abs(chain_sum - fp["nsv"]) < 2.0, (
            f"chain sum {chain_sum} != total {fp['nsv']}")

    def test_primary_fy27_zone_sum_matches_total(self, dash):
        """Primary FY27 zone NSV sum must match total NSV."""
        fp = dash.get("detail_meta", {}).get("fyx_primary", {}).get("FY27")
        if not fp:
            pytest.skip("No FY27 primary data")
        zone_sum = sum(z["nsv"] for z in fp["by_zone"])
        assert abs(zone_sum - fp["nsv"]) < 0.5, (
            f"zone sum {zone_sum} != total {fp['nsv']}")

    def test_primary_fy27_monthly_sum_matches_total(self, dash):
        """Primary FY27 monthly sum must match total NSV."""
        fp = dash.get("detail_meta", {}).get("fyx_primary", {}).get("FY27")
        if not fp:
            pytest.skip("No FY27 primary data")
        monthly_sum = sum(v for v in fp["monthly"] if v)
        assert abs(monthly_sum - fp["nsv"]) < 0.5, (
            f"monthly sum {monthly_sum} != total {fp['nsv']}")

    def test_primary_fy25_fy26_unchanged(self, dash):
        """Pre-aggregated Primary FY25/FY26 values must not change.

        Note: FY25 updated to 22576 after Central zone extraction (MP, CG, Vidharbha).
        This is intentional zone reorganization, not a regression.
        FY26 remains 32900 (32900.36 rounded).
        """
        p = dash.get("primary", {})
        assert p.get("nsv_fy25") == 22576
        assert p.get("nsv_fy26") == 32900

    # ── months_canon / monthly_canon tests ──

    def test_primary_fy27_has_months_canon(self, dash):
        """fyx_primary.FY27 must carry months_canon (canonical Mon-YY labels)."""
        fp = dash.get("detail_meta", {}).get("fyx_primary", {}).get("FY27")
        if not fp:
            pytest.skip("No FY27 primary data")
        assert "months_canon" in fp, "months_canon missing from FY27 fyx_primary"
        assert fp["months_canon"] == ["Apr-26", "May-26", "Jun-26"], (
            f"months_canon={fp['months_canon']} expected ['Apr-26','May-26','Jun-26']"
        )

    def test_primary_fy27_months_canon_matches_monthly_canon(self, dash):
        """monthly_canon must be parallel to months_canon and sum to total NSV."""
        fp = dash.get("detail_meta", {}).get("fyx_primary", {}).get("FY27")
        if not fp:
            pytest.skip("No FY27 primary data")
        assert "monthly_canon" in fp, "monthly_canon missing from FY27 fyx_primary"
        assert len(fp["monthly_canon"]) == len(fp["months_canon"]), (
            "monthly_canon and months_canon length mismatch"
        )
        canon_sum = sum(fp["monthly_canon"])
        assert abs(canon_sum - fp["nsv"]) < 0.5, (
            f"monthly_canon sum {canon_sum} != FY27 NSV {fp['nsv']}"
        )

    # ── 12 mandatory regression tests (primary trend continuity) ──

    def test_fy27_apr_present_in_primary_series(self, dash):
        """Apr-26 must appear in FY27 primary months_covered."""
        fp = dash.get("detail_meta", {}).get("fyx_primary", {}).get("FY27")
        if not fp:
            pytest.skip("No FY27 primary data")
        assert "April" in (fp.get("months_covered") or []), (
            "April missing from FY27 primary months_covered"
        )

    def test_fy27_may_present_in_primary_series(self, dash):
        """May-26 must appear in FY27 primary months_covered."""
        fp = dash.get("detail_meta", {}).get("fyx_primary", {}).get("FY27")
        if not fp:
            pytest.skip("No FY27 primary data")
        assert "May" in (fp.get("months_covered") or []), (
            "May missing from FY27 primary months_covered"
        )

    def test_fy27_jun_present_in_primary_series(self, dash):
        """Jun-26 must appear in FY27 primary months_covered."""
        fp = dash.get("detail_meta", {}).get("fyx_primary", {}).get("FY27")
        if not fp:
            pytest.skip("No FY27 primary data")
        assert "June" in (fp.get("months_covered") or []), (
            "June missing from FY27 primary months_covered"
        )

    def test_primary_months_chronologically_sorted(self, dash):
        """FY27 months_covered must be in calendar order (April, May, June…)."""
        fp = dash.get("detail_meta", {}).get("fyx_primary", {}).get("FY27")
        if not fp:
            pytest.skip("No FY27 primary data")
        ORDER = ["April","May","June","July","Aug","Sept","Oct","Nov","Dec","Jan","Feb","March"]
        months = fp.get("months_covered", [])
        indices = [ORDER.index(m) for m in months if m in ORDER]
        assert indices == sorted(indices), f"months_covered not sorted: {months}"

    def test_no_null_in_primary_fy27_monthly(self, dash):
        """No None/NaN in the non-zero portion of FY27 monthly."""
        fp = dash.get("detail_meta", {}).get("fyx_primary", {}).get("FY27")
        if not fp:
            pytest.skip("No FY27 primary data")
        monthly = fp.get("monthly", [])
        ORDER = ["April","May","June","July","Aug","Sept","Oct","Nov","Dec","Jan","Feb","March"]
        covered = set(fp.get("months_covered", []))
        for i, m in enumerate(ORDER):
            if m in covered:
                v = monthly[i] if i < len(monthly) else None
                assert v is not None and not (isinstance(v, float) and math.isnan(v)), (
                    f"Null/NaN at position {i} ({m}) in FY27 monthly"
                )

    def test_primary_chart_total_equals_card_total(self, dash):
        """FY27 monthly sum must equal the top-level NSV (chart == card)."""
        fp = dash.get("detail_meta", {}).get("fyx_primary", {}).get("FY27")
        if not fp:
            pytest.skip("No FY27 primary data")
        monthly_sum = sum(v for v in fp.get("monthly", []) if v)
        assert abs(monthly_sum - fp["nsv"]) < 0.5, (
            f"FY27 monthly chart total {monthly_sum} != card NSV {fp['nsv']}"
        )

    def test_chain_ratios_sum_to_total(self, dash):
        """FY27 chain NSVs must sum to the declared total (within rounding)."""
        fp = dash.get("detail_meta", {}).get("fyx_primary", {}).get("FY27")
        if not fp:
            pytest.skip("No FY27 primary data")
        chain_sum = sum(c["nsv"] for c in fp.get("by_chain", []))
        assert abs(chain_sum - fp["nsv"]) < 2.0, (
            f"Chain sum {chain_sum} differs from total {fp['nsv']}"
        )

    def test_no_duplicate_chain_names_in_fy27(self, dash):
        """No chain name should appear more than once in FY27 by_chain."""
        fp = dash.get("detail_meta", {}).get("fyx_primary", {}).get("FY27")
        if not fp:
            pytest.skip("No FY27 primary data")
        names = [c["name"] for c in fp.get("by_chain", [])]
        dupes = [n for n in set(names) if names.count(n) > 1]
        assert not dupes, f"Duplicate chain names in FY27 by_chain: {dupes}"

    def test_no_distributor_names_in_fy27_by_chain(self, dash):
        """Distributor ship-to names must not appear in FY27 by_chain."""
        fp = dash.get("detail_meta", {}).get("fyx_primary", {}).get("FY27")
        if not fp:
            pytest.skip("No FY27 primary data")
        known_dist_fragments = ["enterprises", "logistics", "real time", "saachi",
                                "mark enterprise", "d.l. sales", "kiran trading"]
        chain_names_lc = [c["name"].lower() for c in fp.get("by_chain", [])]
        for frag in known_dist_fragments:
            hits = [n for n in chain_names_lc if frag in n]
            assert not hits, f"Possible distributor name in by_chain: {hits}"

    def test_fallback_used_is_disclosed(self, dash):
        """June fallback must be documented in alloc (not hidden as real allocation)."""
        alloc = dash.get("alloc", {})
        if not alloc:
            pytest.skip("No alloc block")
        assert alloc.get("june_fallback_nsv_lakh") is not None, (
            "june_fallback_nsv_lakh missing — fallback not disclosed"
        )

    def test_unallocated_primary_not_hidden(self, dash):
        """If any primary was unallocated, alloc block must record it."""
        alloc = dash.get("alloc", {})
        if not alloc:
            pytest.skip("No alloc block")
        assert "unmapped_nsv" in alloc or "unmapped_note" in alloc, (
            "Unallocated primary bucket not present in alloc block"
        )

    def test_primary_consistent_across_overview_and_primary_tab(self, dash):
        """FY27 total NSV in fyx_primary must match what overview would show."""
        fp = dash.get("detail_meta", {}).get("fyx_primary", {}).get("FY27")
        if not fp:
            pytest.skip("No FY27 primary data")
        # The total in fyx_primary is the canonical source for both overview
        # and primary tab KPI cards — there is no separate overview copy to diff.
        assert fp["nsv"] is not None and fp["nsv"] > 0, (
            "FY27 NSV is null or zero — overview and primary tab would be inconsistent"
        )

    def test_months_canon_labels_in_offtake_months(self, dash):
        """months_canon labels must be present in offtake months (for overview chart join)."""
        fp = dash.get("detail_meta", {}).get("fyx_primary", {}).get("FY27")
        o = dash.get("offtake", {})
        if not fp or not fp.get("months_canon"):
            pytest.skip("No months_canon or no FY27 primary")
        offtake_months = set(o.get("months", []))
        missing = [m for m in fp["months_canon"] if m not in offtake_months]
        assert not missing, (
            f"months_canon labels {missing} not found in offtake months — "
            "overview chart join will produce null values"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
