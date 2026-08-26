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
        assert bd.canon_chain("VISHAL ENTERPRISES") == "VMM"
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
        # FY25 = ₹23,331.97 L (correct restored value; matches monthly sum)
        assert dash["primary"]["nsv_fy25"] == 23331.97

    def test_primary_fy26_unchanged(self, dash):
        # FY26 remains at 32900 (was 32900.36 before rounding)
        assert dash["primary"]["nsv_fy26"] == 32900

    def test_offtake_fy25_unchanged(self, dash):
        assert dash["offtake"]["total_fy25"] == 21840.0

    def test_offtake_fy26_unchanged(self, dash):
        assert dash["offtake"]["total_fy26"] == 31082.0

    def test_offtake_fy27_updated(self, dash):
        # Updated 2026-08-21: Jun+Jul-26 offtake integrated (Apr+May+Jun+Jul)
        total = dash["offtake"]["total_fy27"]
        assert abs(total - 15054.73) < 1.0, f"FY27 offtake total {total} unexpected"

    def test_bc_excluded(self, dash):
        bc = dash.get("reliance_bc", {})
        assert bc.get("include_in_overall_offtake") is False
        # Updated 2026-08-15: Full BC history (Jan-24 to Jul-26) from dedicated RBC xlsb
        assert abs(bc.get("total", 0) - 9186.08) < 5.0

    def test_fyx_primary_fy27_value(self, dash):
        fp = dash["detail_meta"]["fyx_primary"]["FY27"]
        assert abs(fp["nsv"] - 18581.29) < 2.0

    def test_tot_blended_preserved(self, dash):
        assert dash["tot"]["blended_tot_pct"] == 50.0

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
