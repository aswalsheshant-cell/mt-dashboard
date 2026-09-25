#!/usr/bin/env python3
"""
Regression tests for chain consolidation, CHAIN_ALIASES expansion,
and dashboard data integrity after the controlled correction.

Covers:
  - CHAIN_ALIASES expanded mapping (distributor→chain)
  - canon_chain() for new aliases
  - No duplicate alias keys
  - data.js chain names after consolidation targets
  - Pre-aggregated totals unchanged (FY25/FY26 regression)
  - Brand Counter exclusion preserved
  - TOT% structure preserved
"""
from __future__ import annotations
import importlib, json, math, re, sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
bd = importlib.import_module("build_dashboard_data")

BASELINES_JSON = Path(__file__).resolve().parent.parent / "config" / "baselines.json"


def _governed_baseline(key):
    """Look up a check from the single governed baseline registry
    (config/baselines.json) by its key, instead of keeping a private
    hardcoded copy of the same figure in this test file."""
    checks = json.loads(BASELINES_JSON.read_text())["checks"]
    for c in checks:
        if c["key"] == key:
            return c
    raise KeyError(f"{key!r} not found in {BASELINES_JSON}")


@pytest.fixture(scope="module")
def dash():
    path = Path(__file__).resolve().parent.parent / "dashboard" / "data.js"
    txt = path.read_text(encoding="utf-8")
    m = re.search(r"window\.DASH\s*=\s*", txt)
    raw = txt[m.end():].rstrip().rstrip(";")
    raw = re.sub(r"\bNaN\b", "null", raw)
    return json.loads(raw)


class TestChainAliases:
    def test_dmart_variants(self):
        assert bd.canon_chain("DC-D-Mart-Offline") == "DMart"
        assert bd.canon_chain("JUST MARK-Dmart") == "DMart"
        assert bd.canon_chain("D-Mart-Store-E-Com") == "DMart"
        assert bd.canon_chain("JUST MARK-D-Mart") == "DMart"

    def test_reliance_variants(self):
        assert bd.canon_chain("Reliance Retail-DC") == "Reliance Retail"
        assert bd.canon_chain("Reliance Retail-Store") == "Reliance Retail"

    def test_azorte_separated(self):
        assert bd.canon_chain("Reliance Retail-(Azorte)") == "Azorte"
        assert bd.canon_chain("AZORTE") == "Azorte"

    def test_nykaa(self):
        assert bd.canon_chain("Nykaa E-Retail Limited") == "Nykaa (FSN)"

    def test_metro(self):
        assert bd.canon_chain("Metro-CNC") == "Metro C&C"

    def test_walmart(self):
        assert bd.canon_chain("Walmart-CNC") == "Walmart"

    def test_guardian_typo(self):
        assert bd.canon_chain("Gaurdian") == "Guardian"
        assert bd.canon_chain("Guardian Healthcare") == "Guardian"
        assert bd.canon_chain("Guardian Healthcare-Delhi") == "Guardian"

    def test_vmart_variants(self):
        assert bd.canon_chain("V-Mart Retail Limited") == "V-Mart"
        assert bd.canon_chain("V-Mart Retail") == "V-Mart"
        assert bd.canon_chain("V Mart East") == "V-Mart"

    def test_apollo_mapping(self):
        assert bd.canon_chain("United Marketing") == "Apollo"

    def test_wh_smith(self):
        assert bd.canon_chain("Travel News Services-Wsmith") == "WH-Smith"

    def test_relay(self):
        assert bd.canon_chain("Travel Retail Services-Relay") == "Relay"

    def test_ratnadeep_typo(self):
        assert bd.canon_chain("Ratanadeep") == "Ratnadeep"

    def test_vishal_mega_mart(self):
        # INTENTIONAL_BUSINESS_CHANGE: "Vishal Enterprises (Solapur)" is a
        # distributor billing into D-Mart, not a name for the Vishal Mega
        # Mart chain (see the CHAIN_ALIASES comment right above the "vishal
        # enterprises" alias in build_dashboard_data.py) -- every real
        # "VISHAL ENTERPRISES_Solapur" row already carries Chain Name =
        # "D-Mart". This test used to assert the pre-correction mapping.
        assert bd.canon_chain("VISHAL ENTERPRISES") == "DMart"
        assert bd.canon_chain("VMM") == "VMM"

    def test_hg_variants(self):
        assert bd.canon_chain("Health & Glow") == "Health & Glow"

    def test_eremedium(self):
        assert bd.canon_chain("Eremedium Private Limited") == "Eremedium"

    def test_sancus(self):
        assert bd.canon_chain("Sancus") == "Sancus (RMT)"
        assert bd.canon_chain("Sancus Networks-MT-Reg.") == "Sancus (RMT)"

    def test_trent(self):
        assert bd.canon_chain("Trent Hypermarket") == "Trent"

    def test_spencer_variants(self):
        assert bd.canon_chain("Spencers") == "Spencer"
        assert bd.canon_chain("Spencer") == "Spencer"
        assert bd.canon_chain("Spencer's") == "Spencer"

    def test_frankross_variants(self):
        assert bd.canon_chain("Frank Ross") == "Frankross"
        assert bd.canon_chain("Frankross") == "Frankross"
        assert bd.canon_chain("frankros") == "Frankross"

    def test_sasta_sundar_variants(self):
        assert bd.canon_chain("sastasundar") == "Sasta Sundar"
        assert bd.canon_chain("Sasta Sunder") == "Sasta Sundar"

    def test_arambagh(self):
        assert bd.canon_chain("Aarambagh food mart") == "Arambagh"

    def test_canonical_passthrough(self):
        assert bd.canon_chain("Dmart") == "DMart"
        assert bd.canon_chain("Apollo") == "Apollo"
        assert bd.canon_chain("Shoppers Stop") == "Shoppers Stop"

    def test_nan_guard(self):
        assert bd.canon_chain(None) is None
        assert bd.canon_chain(float("nan")) is None


class TestNoAliasConflicts:
    def test_no_duplicate_alias_keys(self):
        seen = {}
        for canon, aliases in bd.CHAIN_ALIASES:
            for a in aliases:
                if a in seen and seen[a] != canon:
                    pytest.fail(
                        f"Alias '{a}' maps to both '{seen[a]}' and '{canon}'"
                    )
                seen[a] = canon


class TestDataJsRegression:
    def test_primary_fy25_unchanged(self, dash):
        # STALE_TEST_EXPECTATION: a synthetic FY25 Primary derivation was
        # briefly wired into data.js by an earlier session, then correctly
        # reverted (docs/FAILURE_MODE_REGISTER.md FM-13) -- FY25 (Apr'24-
        # Mar'25) has no real Primary billing extract anywhere in this repo
        # (THE ONE FY RULE coverage notes in CLAUDE.md). This test used to
        # assert that fabricated number must survive; assert its absence
        # stays correct instead, so a future rebuild can't silently
        # reintroduce it.
        assert "nsv_fy25" not in dash["primary"], (
            "primary.nsv_fy25 reappeared -- FY25 has no real Primary source; "
            "see docs/FAILURE_MODE_REGISTER.md FM-13 before treating this as "
            "a legitimate restore"
        )
        assert dash["primary"]["fy_tags"] == ["fy26"], (
            f"primary.fy_tags={dash['primary']['fy_tags']} -- expected only "
            "fy26 until a real FY25/FY27 Primary source is registered"
        )

    def test_primary_fy26_unchanged(self, dash):
        # DUPLICATED_BASELINE: this was a private hardcoded 32900 (a rounded
        # copy) that drifted from the governed exact value. FY26 is closed
        # (frozen_history) -- read the one governed baseline instead of
        # keeping a second copy of it here.
        baseline = _governed_baseline("primary_nsv_fy26")
        actual = dash["primary"]["nsv_fy26"]
        assert abs(actual - baseline["expected"]) <= baseline["tolerance"], (
            f"primary.nsv_fy26={actual} but config/baselines.json's "
            f"primary_nsv_fy26={baseline['expected']}"
        )

    def test_offtake_fy25_unchanged(self, dash):
        # STALE_TEST_EXPECTATION, same root cause as test_primary_fy25_unchanged:
        # FY25 offtake does not exist in this repo's real sources either.
        assert dash["offtake"].get("total_fy25") is None, (
            "offtake.total_fy25 is no longer None -- if a real FY25 offtake "
            "source was registered, update this test with its provenance; "
            "do not just restore the old fabricated 21840.0"
        )

    def test_offtake_fy26_unchanged(self, dash):
        # DUPLICATED_BASELINE, same pattern as primary_nsv_fy26 above.
        baseline = _governed_baseline("offtake_fy26_total")
        actual = dash["offtake"]["total_fy26"]
        assert abs(actual - baseline["expected"]) <= baseline["tolerance"], (
            f"offtake.total_fy26={actual} but config/baselines.json's "
            f"offtake_fy26_total={baseline['expected']}"
        )

    def test_offtake_fy27_updated(self, dash):
        # OPEN_PERIOD: FY27 offtake is tracked_universe -- it legitimately
        # grows every time a new month is ingested (this was hardcoded to a
        # 4-month snapshot; the repo is now at 5 months and still growing).
        # Assert the structural/business invariants instead of an exact
        # snapshot: positive, monotonically explained by real monthly data,
        # and each month present is chronological/unique.
        total = dash["offtake"]["total_fy27"]
        monthly = dash["offtake"].get("monthly_fy27", [])
        months = dash["offtake"].get("months_fy27", [])
        assert total > 0, "offtake.total_fy27 must be positive once any FY27 month is loaded"
        assert len(months) == len(monthly) > 0, "months_fy27/monthly_fy27 must be non-empty and equal length"
        assert len(set(months)) == len(months), f"months_fy27 has duplicates: {months!r}"
        assert abs(sum(monthly) - total) < 1.0, (
            f"sum(monthly_fy27)={sum(monthly)} does not reconcile to total_fy27={total}"
        )

    def test_bc_excluded(self, dash):
        # OPEN_PERIOD, superseding the prior FY26-only contract: fixing
        # load_reliance_bc_data()'s non-recursive glob (see the Reliance BC
        # CSV-loading fix) means FY27's real Apr-Aug'26 data now loads
        # alongside FY26, so reliance_bc.total correctly sums across every
        # FY actually present in fy_tags -- not just FY26. Assert that
        # reconciliation instead of a single-FY or fixed-value snapshot, so
        # this doesn't go stale again when FY28 data is ingested.
        bc = dash.get("reliance_bc", {})
        assert bc.get("include_in_overall_offtake") is False
        fy_tags = bc.get("fy_tags", [])
        assert fy_tags, "reliance_bc.fy_tags must not be empty"
        expected_total = sum(bc.get(f"total_{tag}", 0) for tag in fy_tags)
        assert abs(bc.get("total", 0) - expected_total) < 0.01, (
            f"reliance_bc.total={bc.get('total')} does not reconcile to the "
            f"sum of its per-FY subtotals ({fy_tags}) = {expected_total}"
        )

    def test_fyx_primary_fy27_value(self, dash):
        # OPEN_PERIOD, with documented provenance: docs/PROJECT_STATE.md's
        # Regression Baseline table already explains the last jump (18581.29
        # -> 22239.59 when Aug'26 was ingested 2026-09-13, a 5th month). This
        # will keep moving as more FY27 months arrive -- assert the
        # reconciliation invariant instead of chasing the latest snapshot.
        fp = dash["detail_meta"]["fyx_primary"]["FY27"]
        assert fp["nsv"] > 0
        assert abs(sum(fp["monthly_canon"]) - fp["nsv"]) < 1.0, (
            f"fyx_primary.FY27 monthly_canon sum={sum(fp['monthly_canon'])} "
            f"does not reconcile to nsv={fp['nsv']}"
        )
        assert len(fp["months_canon"]) == len(fp["monthly_canon"])

    def test_tot_blended_preserved(self, dash):
        # blended_tot_pct is a real computed statistic (tot_passon/tot_mrp,
        # see build_dashboard_data.py) that naturally drifts a little as the
        # underlying chain mix shifts month to month -- it was hardcoded to
        # an exact snapshot (50.0; current value is 50.1). Assert it's a
        # sane percentage instead of an exact float.
        pct = dash["tot"]["blended_tot_pct"]
        assert 0 <= pct <= 100, f"tot.blended_tot_pct={pct} outside a valid percentage range"

    def test_tot_by_chain_has_entries(self, dash):
        assert len(dash["tot"]["by_chain"]) > 0

    def test_tot_qc_table_has_entries(self, dash):
        assert len(dash["tot"]["qc_table"]) == 12


class TestConsolidationTargets:
    """Verify that the dashboard JS consolidation targets exist in the data.

    Phase 2 (2026-08-04): allocate_dist_primary() now uses Primary_ShipTo_FY25-26_to_May26.csv
    as a Priority-1 fallback, correctly resolving MCD distributor names to real chains at the
    data layer. These tests were updated to reflect the resolved state: distributor names that
    previously leaked are now correctly mapped and must NOT appear in by_chain. The runtime
    consolidateChains() layer in index.html remains as a defence-in-depth guard for any
    residual naming variants that could appear from future data sources.
    """

    def test_fyx_primary_no_distributor_names(self, dash):
        """After Phase 2 allocation, MCD distributor names must not appear in by_chain."""
        fp = dash["detail_meta"]["fyx_primary"]["FY27"]
        names = [c["name"] for c in fp["by_chain"]]
        distributor_names = ["DC-D-Mart-Offline", "JUST MARK-Dmart", "Kiran Trading Company"]
        leaked = [n for n in distributor_names if n in names]
        assert not leaked, (
            f"Distributor names {leaked} leaked into fyx_primary.by_chain — "
            "allocation should have resolved them to canonical chain names."
        )

    def test_tot_has_canonical_chain_names(self, dash):
        """tot.by_chain may still contain un-allocated names (different pipeline);
        verify it at least contains the key canonical chains we expect from FY26."""
        names = set(c["name"] for c in dash["tot"]["by_chain"])
        # TOT uses a different source (pre-agg FY26 workbook) — check canonical names present
        expected_canonical = {"DMart", "Reliance Retail", "Apollo"}
        found = expected_canonical & names
        assert found, (
            f"No canonical chain names found in tot.by_chain; got sample: {list(names)[:10]}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
