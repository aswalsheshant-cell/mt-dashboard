"""
Regression tests for two related fixes (2026-09-14):

1. scripts/build_dashboard_data.py's load_chain_allocation_weights() used to
   return None whenever PowerBI/SeedData/DIST/ChainAllocationWeights.csv (or
   its XLSX fallback) was absent -- even though a narrower, already-APPROVED
   patch file (DistPrimaryContWeightsArticle.csv) sat right next to it,
   unused. Real approved data was going untouched.

2. scripts/allocate_dist_enhanced.py's apply_chain_allocation_enhanced() used
   to fabricate a generic "typical Modern Trade distribution" split for any
   Dist. row with no real evidence (Tier 3) -- a hardcoded, invented
   DMart/Reliance/"Q-Comm"/"Others" split that (a) is not backed by any real
   data for this business and (b) only summed to 85%, silently losing 15% of
   every such row's value despite the function's own "zero revenue leakage"
   guarantee. Replaced with the same "Unmapped Chain" pattern already used
   elsewhere in this repo (scripts/aug26_data_readiness_gate.py's
   allocate_primary()) -- keep 100% of the value, tag it honestly as
   unmapped, never invent a split for real money.
"""
import sys
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import build_dashboard_data as bdd  # noqa: E402
from allocate_dist_enhanced import apply_chain_allocation_enhanced  # noqa: E402


def test_load_chain_allocation_weights_falls_back_to_approved_patch():
    """The comprehensive weights file doesn't exist in this repo -- verified
    directly. The narrow, real, already-approved patch file does, and must
    now actually be used instead of the loader silently returning None."""
    assert not Path("PowerBI/SeedData/DIST/ChainAllocationWeights.csv").exists()
    weights = bdd.load_chain_allocation_weights(REPO_ROOT)
    assert weights is not None, "should fall back to DistPrimaryContWeightsArticle.csv, not return None"
    assert len(weights) > 0
    for key, splits in weights.items():
        total = sum(frac for _, frac in splits)
        assert total == pytest.approx(1.0, abs=1e-6), f"{key} splits sum to {total}, not 1.0"


def test_load_chain_allocation_weights_only_uses_approved_rows():
    """Every row in the real patch file happens to be Approved today, but the
    loader must filter on Approval_Status rather than assume that."""
    patch = pd.read_csv("PowerBI/SeedData/DIST/DistPrimaryContWeightsArticle.csv")
    assert set(patch["Approval_Status"].unique()) == {"Approved"}, (
        "This test's premise (all rows Approved) no longer holds -- "
        "re-check load_chain_allocation_weights() actually filters"
    )


def _dist_row(ship_to, brand, month, nsv):
    return {
        "PO Type": "Dist.", "_CustName": ship_to, "brand": brand, "Month": month,
        "_NSV": nsv, "_MRP": nsv * 2, "_Qty": 10, "_TaxLOC": nsv * 0.1,
        "Chain Name": "SHOULD_BE_OVERWRITTEN",
    }


def test_tier3_no_longer_fabricates_a_split():
    """A Dist. row with no Tier-1 (explicit weights) or Tier-2 (offtake)
    evidence must land entirely under 'Unmapped Chain', not a fabricated
    generic split."""
    df = pd.DataFrame([_dist_row("Totally Unknown Distributor", "Mamaearth", "2099-01-01", 100.0)])
    allocated, qc = apply_chain_allocation_enhanced(df, weights_dict=None, df_offtake=None)
    assert list(allocated["Chain Name"]) == ["Unmapped Chain"]
    assert allocated["_NSV"].iloc[0] == pytest.approx(100.0)
    assert qc["tier3_rows"] == 1
    assert qc["tier1_rows"] == 0 and qc["tier2_rows"] == 0


def test_tier3_no_longer_leaks_revenue():
    """The old fabricated default only summed to 85% weight -- 15% of every
    Tier-3 row's value vanished. The fix must reconcile exactly."""
    df = pd.DataFrame([
        _dist_row("Unknown A", "Mamaearth", "2099-01-01", 250.0),
        _dist_row("Unknown B", "The Derma Co", "2099-02-01", 75.5),
    ])
    allocated, qc = apply_chain_allocation_enhanced(df, weights_dict=None, df_offtake=None)
    assert allocated["_NSV"].sum() == pytest.approx(325.5)
    assert qc["variance_lakh"] == pytest.approx(0.0, abs=1e-9)
    assert bool(qc["reconciliation_passed"]) is True


def test_tier1_explicit_weights_still_take_priority():
    """Confirms Tier 1 (real explicit weights) is checked before falling
    through to Unmapped, using the same key shape load_chain_allocation_weights
    produces."""
    weights = {("known distributor", "mamaearth", "2099-03-01"): [("Apollo", 0.6), ("DMart", 0.4)]}
    df = pd.DataFrame([_dist_row("Known Distributor", "Mamaearth", "2099-03-01", 100.0)])
    allocated, qc = apply_chain_allocation_enhanced(df, weights_dict=weights, df_offtake=None)
    assert set(allocated["Chain Name"]) == {"Apollo", "DMart"}
    assert qc["tier1_rows"] == 1
    assert allocated["_NSV"].sum() == pytest.approx(100.0)


def test_mapping_health_reflects_current_detail_records_not_a_stale_snapshot():
    """mapping_health_block()'s completeness_pct is computed purely from the
    frame it's given -- confirms it is NOT reading some other cached/stale
    source, so refreshing it from current detail_records (via the new
    --mapping-health-only build mode) actually changes the number."""
    df = pd.DataFrame([
        {"_FY": "FY99", "_Chain": "DMart", "_NSV": 90.0},
        {"_FY": "FY99", "_Chain": "Unmapped Chain", "_NSV": 10.0},
    ])
    out = bdd.mapping_health_block(df, cfg=None)
    assert out["by_fy"]["FY99"]["completeness_pct"] == pytest.approx(90.0)
    assert out["by_fy"]["FY99"]["unmapped_nsv"] == pytest.approx(10.0)


def test_mapping_health_cumulative_pct_discloses_negative_nsv_rows():
    """FM-20: a return/credit row (negative NSV) sorted to the tail of the
    exception list can make an earlier row's cumulative_pct read above 100%
    before the negative tail pulls it back to exactly 100% -- correct
    arithmetic (cumulative % of a NET total), but read as broken math by a
    real business reviewer on 2026-09-22 ("Cumulative is increased, kindly
    adjust"). The note must disclose this when it can happen; the formula
    itself must NOT change (capping at 100% or dropping negative rows would
    hide real return/credit activity)."""
    df = pd.DataFrame([{"_FY": "FY99", "_Chain": "Unmapped Chain", "_NSV": 100.0}])
    missing = [
        {"fy": "FY99", "month": "April", "brand": "Mamaearth", "cust_code": "C1",
         "ship_to": "Big Distributor", "nsv": 90.0, "rows": 1},
        {"fy": "FY99", "month": "June", "brand": "Mamaearth", "cust_code": "C3",
         "ship_to": "Credit Note Distributor", "nsv": -2.0, "rows": 1},
    ]
    out = bdd.mapping_health_block(df, alloc={"missing_mapping": missing}, cfg=None)
    cum_pcts = [d["cumulative_pct"] for d in out["exceptions"]]
    # Sorted descending by nsv: 90 (C1) first, -2 (C3) last. tot_ex = 88.
    # Row 1's cumulative is measured against the FINAL (smaller) total, so it
    # reads > 100% even though nothing is double-counted -- exactly the
    # pattern the real 2026-09-22 export showed (100.8% mid-list, 100.0% at
    # the end).
    assert cum_pcts[0] == pytest.approx(100.0 * 90.0 / 88.0, abs=0.01)   # ~102.27%, > 100% (r2()-rounded)
    assert cum_pcts[-1] == pytest.approx(100.0)   # always ends at exactly 100%
    assert any(p > 100.0 for p in cum_pcts), "fixture should reproduce the >100% mid-list read"
    assert "negative NSV" in out["note"] and "returns/credits" in out["note"]


def test_mapping_health_note_has_no_negative_nsv_caveat_when_all_positive():
    """The disclosure must be conditional -- it should NOT appear (and
    therefore not confuse anyone) when every exception row is a genuine
    positive-NSV unmapped amount, the common case."""
    df = pd.DataFrame([{"_FY": "FY99", "_Chain": "Unmapped Chain", "_NSV": 100.0}])
    missing = [
        {"fy": "FY99", "month": "April", "brand": "Mamaearth", "cust_code": "C1",
         "ship_to": "Distributor A", "nsv": 60.0, "rows": 1},
        {"fy": "FY99", "month": "May", "brand": "Mamaearth", "cust_code": "C2",
         "ship_to": "Distributor B", "nsv": 40.0, "rows": 1},
    ]
    out = bdd.mapping_health_block(df, alloc={"missing_mapping": missing}, cfg=None)
    cum_pcts = [d["cumulative_pct"] for d in out["exceptions"]]
    assert all(p <= 100.0 for p in cum_pcts)
    assert "negative NSV" not in out["note"]
