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
        assert bd.canon_chain("DC-D-Mart-Offline") == "Dmart"
        assert bd.canon_chain("JUST MARK-Dmart") == "Dmart"
        assert bd.canon_chain("D-Mart-Store-E-Com") == "Dmart"
        assert bd.canon_chain("JUST MARK-D-Mart") == "Dmart"

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
        assert bd.canon_chain("VISHAL ENTERPRISES") == "Vishal Mega Mart"

    def test_hg_variants(self):
        assert bd.canon_chain("Health & Glow") == "H&G"

    def test_eremedium(self):
        assert bd.canon_chain("Eremedium Private Limited") == "Eremedium"

    def test_sancus(self):
        assert bd.canon_chain("Sancus") == "RMT-Sancus"
        assert bd.canon_chain("Sancus Networks-MT-Reg.") == "RMT-Sancus"

    def test_trent(self):
        assert bd.canon_chain("Trent Hypermarket") == "Trent"

    def test_arambagh(self):
        assert bd.canon_chain("Aarambagh food mart") == "Arambagh"

    def test_canonical_passthrough(self):
        assert bd.canon_chain("Dmart") == "Dmart"
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
        assert dash["primary"]["nsv_fy25"] == 23331.97

    def test_primary_fy26_unchanged(self, dash):
        assert dash["primary"]["nsv_fy26"] == 32900.36

    def test_offtake_fy25_unchanged(self, dash):
        assert dash["offtake"]["total_fy25"] == 21840.0

    def test_offtake_fy26_unchanged(self, dash):
        assert dash["offtake"]["total_fy26"] == 31082.0

    def test_offtake_fy27_unchanged(self, dash):
        assert dash["offtake"]["total_fy27"] == 11438.72

    def test_bc_excluded(self, dash):
        bc = dash.get("reliance_bc", {})
        assert bc.get("include_in_overall_offtake") is False
        assert bc.get("total") == 943.68

    def test_fyx_primary_fy27_value(self, dash):
        fp = dash["detail_meta"]["fyx_primary"]["FY27"]
        assert abs(fp["nsv"] - 13659.98) < 2.0

    def test_tot_blended_preserved(self, dash):
        assert dash["tot"]["blended_tot_pct"] == 50.0

    def test_tot_by_chain_has_entries(self, dash):
        assert len(dash["tot"]["by_chain"]) > 0

    def test_tot_qc_table_has_entries(self, dash):
        assert len(dash["tot"]["qc_table"]) == 12


class TestConsolidationTargets:
    """Verify that the dashboard JS consolidation targets exist in the data."""

    def test_fyx_primary_has_distributor_names(self, dash):
        fp = dash["detail_meta"]["fyx_primary"]["FY27"]
        names = [c["name"] for c in fp["by_chain"]]
        assert any(n in names for n in [
            "DC-D-Mart-Offline", "JUST MARK-Dmart", "Kiran Trading Company"
        ]), "Expected distributor names in raw fyx_primary.by_chain"

    def test_tot_has_distributor_names(self, dash):
        names = [c["name"] for c in dash["tot"]["by_chain"]]
        assert any(n in names for n in [
            "JUST MARK-Dmart", "Kiran Trading Company", "Nykaa E-Retail Limited"
        ]), "Expected distributor names in raw tot.by_chain"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
