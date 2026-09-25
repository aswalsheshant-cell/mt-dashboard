"""Regression test for F15 (docs/PHASE_2B_FINANCIAL_CONSUMER_INVENTORY.md
follow-up sweep, 2026-09-25): generate_correlations_block() used to hardcode
avg_lift=0 (a placeholder presented as a real observation) and compute
'elasticity' as avg_discount/100 -- not the real lift/discount formula this
file's own CorrelationAnalyzer.calculate_elasticity() defines, unused here
for lack of a monthly offtake-by-chain source to compute a real lift
against. A fully-built "Promo Elasticity Executive Brief" feature in
dashboard/index.html (currently unreachable -- no wired button, no canvas
elements in the DOM) would have exposed this fabricated data the moment
someone finished wiring it up.

Fix: elasticity/avg_lift/roc_index/highest_roi_tier/optimal_depth_range/
avg_discount_tier_N are never fabricated -- they stay None with an explicit
NOT_AVAILABLE_UNTIL_VALIDATED_LIFT_SOURCE status and methodology_validated:
False, until a real offtake-by-chain source and a reviewed methodology
exist. avg_discount/count (genuinely observed, real values) are preserved.
"""
import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
poc = importlib.import_module("promo_offtake_correlation")


def _master_with_promo(chains):
    """Minimal data_master shape generate_correlations_block() reads:
    promo.monthly[month].by_chain[] entries with avg_offer_pct/skus/brands."""
    return {
        "promo": {
            "monthly": {
                "Apr-26": {"by_chain": [
                    {"name": name, "avg_offer_pct": depth, "skus": 5, "brands": 2}
                    for name, depth in chains
                ]},
                "May-26": {"by_chain": [
                    {"name": name, "avg_offer_pct": depth, "skus": 6, "brands": 2}
                    for name, depth in chains
                ]},
            }
        }
    }


def test_no_hardcoded_avg_lift_zero():
    master = _master_with_promo([("Reliance Retail", 55.0)])
    result = poc.generate_correlations_block(master)
    tiers = result["correlations"]["by_chain"][0]["elasticity_tiers"]
    for tier_metrics in tiers.values():
        assert tier_metrics["avg_lift"] is None
        assert tier_metrics["elasticity"] is None
        assert tier_metrics["status"] == "NOT_AVAILABLE_UNTIL_VALIDATED_LIFT_SOURCE"


def test_avg_discount_and_count_are_still_real_observed_values():
    """avg_discount/count are genuinely observed from the promo calendar --
    only the lift/elasticity derivation (which needs offtake data this
    function never receives) must be blocked, not the real inputs."""
    master = _master_with_promo([("Wellness Forever", 60.0)])
    result = poc.generate_correlations_block(master)
    tiers = result["correlations"]["by_chain"][0]["elasticity_tiers"]
    tier_2 = tiers.get("tier_2")
    assert tier_2 is not None
    assert tier_2["avg_discount"] == 60.0
    assert tier_2["count"] == 2  # Apr + May


def test_roc_index_is_none_not_a_sum_over_none_crash():
    """roc_index used to sum per-tier 'elasticity' values -- now that those
    are None, it must not crash (sum() over None raises TypeError) or
    silently resolve to a fabricated 0."""
    master = _master_with_promo([("D-Mart", 40.0), ("Reliance Retail", 75.0)])
    result = poc.generate_correlations_block(master)
    for chain_entry in result["correlations"]["by_chain"]:
        assert chain_entry["roc_index"] is None


def test_summary_never_fabricates_highest_roi_tier_or_depth_range():
    master = _master_with_promo([("D-Mart", 45.0)])
    summary = poc.generate_correlations_block(master)["correlations"]["summary"]
    assert summary["highest_roi_tier"] is None
    assert summary["optimal_depth_range"] is None
    assert summary["avg_discount_tier_1"] is None
    assert summary["avg_discount_tier_2"] is None
    assert summary["avg_discount_tier_3"] is None
    assert summary["methodology_validated"] is False
    assert summary["status"] == "NOT_AVAILABLE_UNTIL_VALIDATED_LIFT_SOURCE"


def test_top_level_correlations_block_carries_methodology_validated_false():
    """Single, top-level allowlist flag a JS consumer can check without
    needing to know this function's internal shape -- must be explicitly
    False, never absent (absent could be misread as 'not set yet' rather
    than 'confirmed not validated')."""
    master = _master_with_promo([("D-Mart", 45.0)])
    correlations = poc.generate_correlations_block(master)["correlations"]
    assert correlations["methodology_validated"] is False
    assert correlations["status"] == "NOT_AVAILABLE_UNTIL_VALIDATED_LIFT_SOURCE"


def test_anomaly_flags_still_work_unaffected():
    """Excessive-discount anomaly detection uses only real, observed
    discount depth -- not elasticity/lift -- so it must be untouched by
    this fix."""
    master = _master_with_promo([("Reliance Retail", 85.0)])
    anomalies = poc.generate_correlations_block(master)["correlations"]["anomaly_flags"]
    assert any(a["flag"] == "excessive_discount" for a in anomalies)


def test_real_calculate_elasticity_method_is_untouched():
    """The correct, real implementation (CorrelationAnalyzer.calculate_
    elasticity(), which needs real offtake_data) must still work exactly as
    before -- this fix only changes generate_correlations_block()'s own,
    separate, cruder inline logic, not the analyzer class itself."""
    # compute_baseline_offtake() sorts month keys as plain strings, so use
    # ISO-ordered keys (alphabetical order == chronological order) to avoid
    # an unrelated, pre-existing sort quirk this test isn't about.
    analyzer = poc.CorrelationAnalyzer()
    offtake_data = {"by_chain_detail": {"D-Mart": {"monthly": {
        "2026-01": 100, "2026-02": 100, "2026-03": 100, "2026-04": 150,
    }}}}
    promo_data = {"by_chain": [{"name": "D-Mart", "monthly_depth": {"2026-04": 40.0}}]}
    result = analyzer.calculate_elasticity(promo_data, offtake_data)
    assert result["D-Mart"]["tier_1"]["avg_lift"] == 50.0
    assert result["D-Mart"]["tier_1"]["elasticity"] == 1.25
