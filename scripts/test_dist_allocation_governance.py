#!/usr/bin/env python3
"""
Unit tests for DIST allocation governance module.

Covers:
  - 5-tier eligibility gate (all tiers + edge cases)
  - QC reconciliation (balanced, unbalanced, edge cases)
  - Override application
  - QC report generation
"""
from __future__ import annotations
import sys, pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dist_allocation_governance import (
    DistAllocationGovernance,
    EligibilityResult,
    QCReconciliation,
    eligibility_tier_rank,
)


class TestEligibilityGate:
    """Test 5-tier eligibility gate."""

    def test_tier_1_eligible_exact_match(self):
        """Tier 1: Exact secondary match → Eligible."""
        gov = DistAllocationGovernance()
        result = gov.check_eligibility(
            primary_row={"ship_to": "ABC Dist", "brand": "Mamaearth", "month": "2026-04"},
            secondary_match_found=True,
            secondary_match_within_tат=False,
            brand_in_offtake=True,
            article_in_offtake=True,
        )
        assert result.tier == "Eligible"
        assert result.confidence_pct == 100.0
        assert "exact match" in result.reasoning.lower()

    def test_tier_2_eligible_tat_fallback(self):
        """Tier 2: Match within ±3 months → Eligible_TAT."""
        gov = DistAllocationGovernance()
        result = gov.check_eligibility(
            primary_row={"ship_to": "XYZ Dist", "brand": "Tagalogs", "month": "2026-05"},
            secondary_match_found=False,
            secondary_match_within_tат=True,
            brand_in_offtake=True,
            article_in_offtake=True,
        )
        assert result.tier == "Eligible_TAT"
        assert 80.0 <= result.confidence_pct <= 100.0
        assert "nearest-month" in result.reasoning.lower() or "tat" in result.reasoning.lower()

    def test_tier_3_brand_not_listed(self):
        """Tier 3: No match, brand not in offtake → Brand_Not_Listed."""
        gov = DistAllocationGovernance()
        result = gov.check_eligibility(
            primary_row={"ship_to": "Unknown Dist", "brand": "UnknownBrand", "month": "2026-06"},
            secondary_match_found=False,
            secondary_match_within_tат=False,
            brand_in_offtake=False,
            article_in_offtake=True,
        )
        assert result.tier == "Brand_Not_Listed"
        assert result.confidence_pct >= 90.0
        assert "brand" in result.reasoning.lower()

    def test_tier_4_article_not_listed(self):
        """Tier 4: No match, article not in offtake → Article_Not_Listed."""
        gov = DistAllocationGovernance()
        result = gov.check_eligibility(
            primary_row={"ship_to": "ABC Dist", "brand": "Mamaearth", "article": "UNKNOWN_SKU"},
            secondary_match_found=False,
            secondary_match_within_tат=False,
            brand_in_offtake=True,
            article_in_offtake=False,
        )
        assert result.tier == "Article_Not_Listed"
        assert result.confidence_pct >= 90.0
        assert "article" in result.reasoning.lower()

    def test_tier_5_not_eligible(self):
        """Tier 5: No match, both brand & article in offtake → Not_Eligible."""
        gov = DistAllocationGovernance()
        result = gov.check_eligibility(
            primary_row={"ship_to": "Mystery Dist", "brand": "Mamaearth", "month": "2026-07"},
            secondary_match_found=False,
            secondary_match_within_tат=False,
            brand_in_offtake=True,
            article_in_offtake=True,
        )
        assert result.tier == "Not_Eligible"
        assert result.confidence_pct == 100.0
        assert "no secondary data match" in result.reasoning.lower()

    def test_tier_precedence_exact_beats_tat(self):
        """Exact match takes precedence over TAT."""
        gov = DistAllocationGovernance()
        result = gov.check_eligibility(
            primary_row={"ship_to": "ABC Dist", "brand": "Mamaearth"},
            secondary_match_found=True,
            secondary_match_within_tат=True,  # Both true, exact should win
            brand_in_offtake=True,
            article_in_offtake=True,
        )
        assert result.tier == "Eligible", "Exact match should take precedence"

    def test_tier_precedence_brand_exclusion_beats_article(self):
        """Brand exclusion (Tier 3) takes precedence over article exclusion (Tier 4)."""
        gov = DistAllocationGovernance()
        result = gov.check_eligibility(
            primary_row={"ship_to": "ABC Dist", "brand": "UnknownBrand"},
            secondary_match_found=False,
            secondary_match_within_tат=False,
            brand_in_offtake=False,
            article_in_offtake=False,  # Both false, brand should win
        )
        assert result.tier == "Brand_Not_Listed", "Brand exclusion should take precedence"


class TestQCReconciliation:
    """Test QC reconciliation logic."""

    def test_qc_balanced_exact_zero_variance(self):
        """QC PASS: Original = Allocated + Blocked (variance = 0)."""
        gov = DistAllocationGovernance()
        qc = gov.reconcile_qc(
            distributor="ABC Dist",
            brand="Mamaearth",
            month="2026-04",
            original_nsv=1000.0,
            allocated_nsv=900.0,
            blocked_nsv=100.0,
            tolerance_lakh=0.0,
        )
        assert qc.is_balanced is True
        assert qc.variance == 0.0

    def test_qc_unbalanced_positive_variance(self):
        """QC FAIL: Allocated + Blocked > Original (positive variance)."""
        gov = DistAllocationGovernance()
        qc = gov.reconcile_qc(
            distributor="XYZ Dist",
            brand="Tagalogs",
            month="2026-05",
            original_nsv=1000.0,
            allocated_nsv=600.0,
            blocked_nsv=500.0,  # Sum = 1100 > 1000
            tolerance_lakh=0.0,
        )
        assert qc.is_balanced is False
        assert qc.variance == 100.0

    def test_qc_unbalanced_negative_variance(self):
        """QC FAIL: Allocated + Blocked < Original (negative variance)."""
        gov = DistAllocationGovernance()
        qc = gov.reconcile_qc(
            distributor="Mystery Dist",
            brand="Other",
            month="2026-06",
            original_nsv=1000.0,
            allocated_nsv=600.0,
            blocked_nsv=300.0,  # Sum = 900 < 1000
            tolerance_lakh=0.0,
        )
        assert qc.is_balanced is False
        assert qc.variance == -100.0

    def test_qc_tolerance_within_band(self):
        """QC PASS: Variance within tolerance band (±0.5L)."""
        gov = DistAllocationGovernance()
        qc = gov.reconcile_qc(
            distributor="ABC Dist",
            brand="Mamaearth",
            month="2026-07",
            original_nsv=1000.0,
            allocated_nsv=900.0,
            blocked_nsv=100.3,
            tolerance_lakh=0.5,
        )
        assert qc.is_balanced is True
        assert abs(qc.variance) <= 0.5

    def test_qc_tolerance_outside_band(self):
        """QC FAIL: Variance exceeds tolerance band."""
        gov = DistAllocationGovernance()
        qc = gov.reconcile_qc(
            distributor="XYZ Dist",
            brand="Tagalogs",
            month="2026-08",
            original_nsv=1000.0,
            allocated_nsv=900.0,
            blocked_nsv=99.0,  # Variance = -1.0 > tolerance of 0.5
            tolerance_lakh=0.5,
        )
        assert qc.is_balanced is False
        assert abs(qc.variance) > 0.5

    def test_qc_zero_values(self):
        """QC handles zero values gracefully."""
        gov = DistAllocationGovernance()
        qc = gov.reconcile_qc(
            distributor="Zero Dist",
            brand="Zero Brand",
            month="2026-09",
            original_nsv=0.0,
            allocated_nsv=0.0,
            blocked_nsv=0.0,
        )
        assert qc.is_balanced is True
        assert qc.variance == 0.0

    def test_qc_negative_nsv_returns(self):
        """QC handles negative NSV (returns/credit notes)."""
        gov = DistAllocationGovernance()
        qc = gov.reconcile_qc(
            distributor="ABC Dist",
            brand="Mamaearth",
            month="2026-10",
            original_nsv=-100.0,  # Return
            allocated_nsv=-90.0,
            blocked_nsv=-10.0,
        )
        assert qc.is_balanced is True
        assert qc.variance == 0.0


class TestQCReportGeneration:
    """Test QC report generation."""

    def test_report_all_balanced(self):
        """Report when all rows balanced."""
        gov = DistAllocationGovernance()
        results = [
            QCReconciliation(True, 0.0, 1000.0, 900.0, 100.0),
            QCReconciliation(True, 0.0, 500.0, 400.0, 100.0),
            QCReconciliation(True, 0.0, 2000.0, 1800.0, 200.0),
        ]
        report = gov.generate_qc_report(results)
        assert report["total_rows"] == 3
        assert report["balanced"] == 3
        assert report["unbalanced"] == 0
        assert report["total_variance_lakh"] == 0.0
        assert report["balance_rate_pct"] == 100.0

    def test_report_mixed_results(self):
        """Report with mix of balanced and unbalanced rows."""
        gov = DistAllocationGovernance()
        results = [
            QCReconciliation(True, 0.0, 1000.0, 900.0, 100.0),
            QCReconciliation(False, 50.0, 500.0, 400.0, 150.0),  # +50 variance
            QCReconciliation(False, -25.0, 2000.0, 1800.0, 175.0),  # -25 variance
        ]
        report = gov.generate_qc_report(results)
        assert report["total_rows"] == 3
        assert report["balanced"] == 1
        assert report["unbalanced"] == 2
        assert report["total_variance_lakh"] == 25.0
        assert report["max_variance_lakh"] == 50.0
        assert 33.3 <= report["balance_rate_pct"] <= 33.4  # 1/3

    def test_report_empty_results(self):
        """Report with no results."""
        gov = DistAllocationGovernance()
        report = gov.generate_qc_report([])
        assert report["total_rows"] == 0
        assert report["balanced"] == 0
        assert report["unbalanced"] == 0
        assert "note" in report  # Empty report has note instead of variance


class TestEligibilityTierRank:
    """Test tier ranking utility."""

    def test_rank_eligible_is_highest(self):
        """Eligible (Tier 1) ranks highest."""
        assert eligibility_tier_rank("Eligible") < eligibility_tier_rank("Eligible_TAT")
        assert eligibility_tier_rank("Eligible") < eligibility_tier_rank("Not_Eligible")

    def test_rank_not_eligible_is_lowest(self):
        """Not_Eligible (Tier 5) ranks lowest."""
        assert eligibility_tier_rank("Not_Eligible") > eligibility_tier_rank("Eligible")
        assert eligibility_tier_rank("Not_Eligible") > eligibility_tier_rank("Brand_Not_Listed")

    def test_rank_unknown_tier(self):
        """Unknown tier gets high rank (default 99)."""
        assert eligibility_tier_rank("UnknownTier") == 99
        assert eligibility_tier_rank("UnknownTier") > eligibility_tier_rank("Not_Eligible")


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_eligibility_all_false_signals(self):
        """Worst case: no matches, both exclusions false."""
        gov = DistAllocationGovernance()
        result = gov.check_eligibility(
            primary_row={},
            secondary_match_found=False,
            secondary_match_within_tат=False,
            brand_in_offtake=False,  # Brand NOT in offtake
            article_in_offtake=False,  # Article NOT in offtake
        )
        # Brand exclusion should win (Tier 3 > Tier 4)
        assert result.tier == "Brand_Not_Listed"

    def test_qc_large_variance(self):
        """QC handles large variances without overflow."""
        gov = DistAllocationGovernance()
        qc = gov.reconcile_qc(
            distributor="Big Dist",
            brand="Big Brand",
            month="2026-11",
            original_nsv=1_000_000.0,
            allocated_nsv=500_000.0,
            blocked_nsv=600_000.0,  # Variance = 100,000
        )
        assert qc.is_balanced is False
        assert qc.variance == 100_000.0

    def test_qc_very_small_variance(self):
        """QC distinguishes zero from near-zero variance."""
        gov = DistAllocationGovernance()
        qc_zero = gov.reconcile_qc(
            distributor="Precise Dist",
            brand="Precise Brand",
            month="2026-12",
            original_nsv=1000.0,
            allocated_nsv=900.0,
            blocked_nsv=100.0,
            tolerance_lakh=0.0,
        )
        qc_near = gov.reconcile_qc(
            distributor="Precise Dist",
            brand="Precise Brand",
            month="2026-12",
            original_nsv=1000.0,
            allocated_nsv=900.0,
            blocked_nsv=100.001,
            tolerance_lakh=0.0,
        )
        assert qc_zero.is_balanced is True
        assert qc_near.is_balanced is False


if __name__ == "__main__":
    # Run with: pytest scripts/test_dist_allocation_governance.py -v
    pytest.main([__file__, "-v"])
