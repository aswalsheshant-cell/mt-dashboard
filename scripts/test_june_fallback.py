"""
June-26 allocation transparency tests.

Verifies that the june_fallback_* fields in data.js are correctly populated
with the exact values established in the Change Impact Note (2026-08-04)
and that no business values were altered by adding these governance fields.

Run:  pytest scripts/test_june_fallback.py -v
"""
import json
import re
import pytest
from pathlib import Path

DATA_JS = Path(__file__).resolve().parent.parent / "dashboard" / "data.js"

EXPECTED_JUNE_FB_NSV    = 1376.64   # ₹ Lakh — derived-fallback portion of June-26 Dist NSV
EXPECTED_JUNE_FB_KEYS   = 48        # unique (ShipTo × Brand) keys that used fallback
EXPECTED_MAY_KEYS       = 45        # keys whose effective source period was 2026-05
EXPECTED_MAR_KEYS       = 2         # keys whose effective source period was 2026-03
EXPECTED_APR_KEYS       = 1         # keys whose effective source period was 2026-04
EXPECTED_FY27_NSV       = 13659.98  # ₹ Lakh — must not change
EXPECTED_FY27_BY_CHAIN_TOTAL = 13659.98  # sum of by_chain NSVs ≈ FY27 total
NSV_TOL                 = 0.5       # ₹ Lakh tolerance for floating-point rounding


@pytest.fixture(scope="module")
def data():
    assert DATA_JS.exists(), f"data.js not found at {DATA_JS}"
    content = DATA_JS.read_text(encoding="utf-8")
    m = re.search(r"window\.DASH\s*=\s*(\{.*\})\s*;?\s*$", content, re.DOTALL)
    assert m, "window.DASH not found in data.js"
    return json.loads(m.group(1))


@pytest.fixture(scope="module")
def alloc(data):
    a = data.get("alloc", {})
    assert a, "alloc block missing from data.js"
    return a


@pytest.fixture(scope="module")
def fy27(data):
    fyx = data.get("detail_meta", {}).get("fyx_primary", {})
    assert "FY27" in fyx, "FY27 not found in fyx_primary"
    return fyx["FY27"]


# ── June fallback disclosure fields ──────────────────────────────────────────

class TestJuneFallbackFields:

    def test_june_fallback_nsv_present(self, alloc):
        assert "june_fallback_nsv_lakh" in alloc, "june_fallback_nsv_lakh missing from alloc"

    def test_june_fallback_nsv_value(self, alloc):
        v = alloc["june_fallback_nsv_lakh"]
        assert abs(v - EXPECTED_JUNE_FB_NSV) < NSV_TOL, (
            f"june_fallback_nsv_lakh={v} expected ≈{EXPECTED_JUNE_FB_NSV} (tol {NSV_TOL} L)"
        )

    def test_june_fallback_pct_of_fy27_present(self, alloc):
        assert "june_fallback_pct_of_fy27" in alloc, "june_fallback_pct_of_fy27 missing from alloc"

    def test_june_fallback_pct_of_fy27_reasonable(self, alloc):
        pct = alloc["june_fallback_pct_of_fy27"]
        assert pct is not None, "june_fallback_pct_of_fy27 is None"
        # ₹1376.64 L / ₹13659.98 L ≈ 10.1%
        assert 8 < pct < 15, f"june_fallback_pct_of_fy27={pct} outside expected range 8–15%"

    def test_june_fallback_source_present(self, alloc):
        assert "june_fallback_source" in alloc, "june_fallback_source missing from alloc"

    def test_june_actual_shipto_not_available(self, alloc):
        src = alloc["june_fallback_source"]
        assert src.get("june_actual_shipto_available") is False, (
            "june_actual_shipto_available should be False — no June ShipTo primary exists"
        )

    def test_data_available_through_may(self, alloc):
        src = alloc["june_fallback_source"]
        assert src.get("data_available_through") == "2026-05", (
            "data_available_through should be 2026-05"
        )

    def test_june_fallback_keys_count(self, alloc):
        src = alloc["june_fallback_source"]
        keys = src.get("june_fallback_keys", 0)
        assert keys == EXPECTED_JUNE_FB_KEYS, (
            f"june_fallback_keys={keys}, expected {EXPECTED_JUNE_FB_KEYS}"
        )

    def test_june_exact_keys_zero(self, alloc):
        src = alloc["june_fallback_source"]
        exact = src.get("june_exact_keys", -1)
        assert exact == 0, f"june_exact_keys={exact}, expected 0 (no June ShipTo data)"

    def test_june_unmapped_keys_zero(self, alloc):
        src = alloc["june_fallback_source"]
        unmapped = src.get("june_unmapped_keys", -1)
        assert unmapped == 0, f"june_unmapped_keys={unmapped}, expected 0"

    def test_breakdown_by_source_period_present(self, alloc):
        src = alloc["june_fallback_source"]
        bd = src.get("breakdown_by_source_period", [])
        assert len(bd) > 0, "breakdown_by_source_period is empty"

    def test_may_2026_keys_in_breakdown(self, alloc):
        src = alloc["june_fallback_source"]
        bd = {row["source_period"]: row for row in src.get("breakdown_by_source_period", [])}
        assert "2026-05" in bd, "2026-05 not found in breakdown_by_source_period"
        assert bd["2026-05"]["keys"] == EXPECTED_MAY_KEYS, (
            f"May-26 keys={bd['2026-05']['keys']}, expected {EXPECTED_MAY_KEYS}"
        )

    def test_mar_2026_keys_in_breakdown(self, alloc):
        src = alloc["june_fallback_source"]
        bd = {row["source_period"]: row for row in src.get("breakdown_by_source_period", [])}
        assert "2026-03" in bd, "2026-03 not found in breakdown_by_source_period"
        assert bd["2026-03"]["keys"] == EXPECTED_MAR_KEYS, (
            f"Mar-26 keys={bd['2026-03']['keys']}, expected {EXPECTED_MAR_KEYS}"
        )

    def test_apr_2026_keys_in_breakdown(self, alloc):
        src = alloc["june_fallback_source"]
        bd = {row["source_period"]: row for row in src.get("breakdown_by_source_period", [])}
        assert "2026-04" in bd, "2026-04 not found in breakdown_by_source_period"
        assert bd["2026-04"]["keys"] == EXPECTED_APR_KEYS, (
            f"Apr-26 keys={bd['2026-04']['keys']}, expected {EXPECTED_APR_KEYS}"
        )

    def test_breakdown_keys_sum_to_total(self, alloc):
        src = alloc["june_fallback_source"]
        bd = src.get("breakdown_by_source_period", [])
        total_keys = sum(row["keys"] for row in bd)
        assert total_keys == EXPECTED_JUNE_FB_KEYS, (
            f"breakdown keys sum={total_keys}, expected {EXPECTED_JUNE_FB_KEYS}"
        )

    def test_governance_note_present(self, alloc):
        src = alloc["june_fallback_source"]
        note = src.get("governance_note", "")
        assert "June-26" in note and len(note) > 50, "governance_note missing or too short"


# ── Business value immutability ───────────────────────────────────────────────

class TestNoValueChange:

    def test_fy27_total_nsv_unchanged(self, fy27):
        nsv = fy27.get("nsv", 0)
        assert abs(nsv - EXPECTED_FY27_NSV) < NSV_TOL, (
            f"FY27 total NSV={nsv} expected {EXPECTED_FY27_NSV} (regression!)"
        )

    def test_fy27_april_nsv_unchanged(self, fy27):
        # April is monthly[0]; expected 5076.86 L from before-state
        april = fy27.get("monthly", [None])[0]
        assert april is not None and abs(april - 5076.86) < NSV_TOL, (
            f"April NSV={april} changed unexpectedly"
        )

    def test_fy27_may_nsv_unchanged(self, fy27):
        may = fy27.get("monthly", [None, None])[1]
        assert may is not None and abs(may - 4415.74) < NSV_TOL, (
            f"May NSV={may} changed unexpectedly"
        )

    def test_fy27_june_nsv_unchanged(self, fy27):
        june = fy27.get("monthly", [None, None, None])[2]
        assert june is not None and abs(june - 4167.38) < NSV_TOL, (
            f"June NSV={june} changed unexpectedly"
        )

    def test_fy27_by_chain_total_unchanged(self, fy27):
        by_chain = fy27.get("by_chain", [])
        chain_total = sum(c.get("nsv", 0) for c in by_chain)
        assert abs(chain_total - EXPECTED_FY27_BY_CHAIN_TOTAL) < NSV_TOL, (
            f"FY27 by_chain total={chain_total} changed (regression!)"
        )

    def test_dmart_nsv_unchanged(self, fy27):
        by_chain = {c["name"]: c["nsv"] for c in fy27.get("by_chain", [])}
        assert "Dmart" in by_chain, "Dmart missing from by_chain"
        assert abs(by_chain["Dmart"] - 5488.97) < NSV_TOL, (
            f"Dmart NSV={by_chain['Dmart']} changed"
        )

    def test_reliance_nsv_unchanged(self, fy27):
        by_chain = {c["name"]: c["nsv"] for c in fy27.get("by_chain", [])}
        assert "Reliance Retail" in by_chain
        assert abs(by_chain["Reliance Retail"] - 3050.94) < NSV_TOL

    def test_apollo_nsv_unchanged(self, fy27):
        by_chain = {c["name"]: c["nsv"] for c in fy27.get("by_chain", [])}
        assert "Apollo" in by_chain
        assert abs(by_chain["Apollo"] - 2588.79) < NSV_TOL

    def test_chain_alloc_note_present_in_fy27(self, fy27):
        note = fy27.get("chain_alloc_note", "")
        assert note and "June-26" in note, (
            "chain_alloc_note missing or does not mention June-26"
        )

    def test_alloc_source_label_unchanged(self, alloc):
        assert alloc.get("source_label") == "shipto_primary_csv"

    def test_no_mcd_distributors_in_by_chain(self, fy27):
        mcd_names = {
            "az enterprises", "d.l. sales", "kiran trading company_ship to",
            "mark enterprise", "real time logistics_mt_br", "sai saachi associates",
        }
        chain_names_lower = {c["name"].lower() for c in fy27.get("by_chain", [])}
        leaked = [n for n in mcd_names if any(n in cn for cn in chain_names_lower)]
        assert not leaked, f"MCD distributor names still in by_chain: {leaked}"
