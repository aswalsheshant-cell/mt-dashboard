#!/usr/bin/env python3
"""
DIST allocation governance — formalize core rules for distributor primary explosion.

Handles:
  1. 5-tier eligibility gate for chain allocation decisions
  2. QC reconciliation (Original = Allocated + Blocked, variance must = 0)
  3. Business override application from PrimaryAllocationOverride.csv

The governance model treats Distributor-billed primary (blank "Chain name" in
source) as requiring special handling:
  - Eligible (Tier 1): Exact match in secondary contribution % master
  - Eligible_TAT (Tier 2): Match within ±3 months (time-at-target fallback)
  - Brand_Not_Listed (Tier 3): No match, but brand absent from offtake universe
  - Article_Not_Listed (Tier 4): No match, but article absent from offtake universe
  - Not_Eligible (Tier 5): No match AND both brand & article in offtake universe

QC reconciliation gates the build:
  Original Primary NSV = Allocated NSV + Blocked NSV (variance = 0, no tolerance)

Usage:
  gov = DistAllocationGovernance()
  tier, confidence = gov.check_eligibility(
    primary_row, secondary_match_found, brand_in_offtake, article_in_offtake
  )
  is_balanced, variance = gov.reconcile_qc(
    distributor, brand, month,
    original_nsv, allocated_nsv, blocked_nsv
  )
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Tuple
import pandas as pd
from pathlib import Path


@dataclass
class EligibilityResult:
    """Represents a single eligibility decision."""
    tier: str  # Eligible, Eligible_TAT, Brand_Not_Listed, Article_Not_Listed, Not_Eligible
    confidence_pct: float  # 100 = definitive, < 100 = inferred
    reasoning: str  # Human-readable explanation


@dataclass
class QCReconciliation:
    """QC reconciliation result for a Distributor × Brand × Month grain."""
    is_balanced: bool  # True if variance = 0
    variance: float  # NSV variance (allocated + blocked - original)
    original_nsv: float
    allocated_nsv: float
    blocked_nsv: float


class DistAllocationGovernance:
    """Formalize DIST allocation governance rules and QC gates."""

    def __init__(self):
        """Initialize governance engine. No state required; all decisions are stateless."""
        self.tier_order = [
            "Eligible",
            "Eligible_TAT",
            "Brand_Not_Listed",
            "Article_Not_Listed",
            "Not_Eligible",
        ]

    def check_eligibility(
        self,
        primary_row: dict,
        secondary_match_found: bool,
        secondary_match_within_tат: bool = False,
        brand_in_offtake: bool = True,
        article_in_offtake: bool = True,
    ) -> EligibilityResult:
        """
        Determine eligibility tier for a Distributor primary row.

        Args:
            primary_row: Source row (dict with ship_to, brand, month, nsv, etc.)
            secondary_match_found: Bool — exact match in allocation master
            secondary_match_within_tат: Bool — match within ±3 months if exact not found
            brand_in_offtake: Bool — brand present in offtake universe (if False → exclusion)
            article_in_offtake: Bool — article present in offtake universe (if False → exclusion)

        Returns:
            EligibilityResult with tier, confidence_pct, reasoning
        """
        # Tier 1: Exact secondary match → Eligible
        if secondary_match_found:
            return EligibilityResult(
                tier="Eligible",
                confidence_pct=100.0,
                reasoning="Exact match in secondary-based allocation master; "
                         "chain split is definitive.",
            )

        # Tier 2: TAT fallback (within ±3 months)
        if secondary_match_within_tат:
            return EligibilityResult(
                tier="Eligible_TAT",
                confidence_pct=90.0,
                reasoning="No exact match, but nearest-month allocation within ±3 months; "
                         "used as time-at-target fallback.",
            )

        # Tier 3: Brand not in offtake → Brand_Not_Listed
        if not brand_in_offtake:
            return EligibilityResult(
                tier="Brand_Not_Listed",
                confidence_pct=95.0,
                reasoning="No secondary data and brand not in offtake universe; "
                         "allocation cannot be derived; retain primary tag.",
            )

        # Tier 4: Article not in offtake → Article_Not_Listed
        if not article_in_offtake:
            return EligibilityResult(
                tier="Article_Not_Listed",
                confidence_pct=95.0,
                reasoning="No secondary data and article not in offtake universe; "
                         "allocation cannot be derived; retain primary tag.",
            )

        # Tier 5: No match AND both brand & article in offtake → Not_Eligible
        if brand_in_offtake and article_in_offtake:
            return EligibilityResult(
                tier="Not_Eligible",
                confidence_pct=100.0,
                reasoning="No secondary data match despite brand and article being in "
                         "offtake universe; data gap or special case; requires review.",
            )

        # Fallback (shouldn't reach here given the boolean logic)
        return EligibilityResult(
            tier="Not_Eligible",
            confidence_pct=50.0,
            reasoning="Unable to determine tier from available signals; default to Not_Eligible.",
        )

    def reconcile_qc(
        self,
        distributor: str,
        brand: str,
        month: str,
        original_nsv: float,
        allocated_nsv: float,
        blocked_nsv: float,
        tolerance_lakh: float = 0.0,
    ) -> QCReconciliation:
        """
        QC reconciliation: Original Primary = Allocated + Blocked.

        Args:
            distributor: Ship-To name
            brand: Brand name
            month: Period (YYYY-MM)
            original_nsv: Original primary NSV (Lakh)
            allocated_nsv: Allocated to chains (Lakh)
            blocked_nsv: Blocked/unmapped (Lakh)
            tolerance_lakh: Allowed variance (default 0.0 = strict)

        Returns:
            QCReconciliation with is_balanced, variance, and detail
        """
        variance = allocated_nsv + blocked_nsv - original_nsv
        is_balanced = abs(variance) <= tolerance_lakh

        return QCReconciliation(
            is_balanced=is_balanced,
            variance=variance,
            original_nsv=original_nsv,
            allocated_nsv=allocated_nsv,
            blocked_nsv=blocked_nsv,
        )

    def apply_overrides(
        self,
        primary_row: pd.Series,
        override_csv: Optional[Path] = None,
    ) -> pd.Series:
        """Apply business overrides from PrimaryAllocationOverride.csv.

        CSV format: Month, Ship To Name, Chain, Brand, Override Cont%, Remarks
        Match key: (Ship To Name × Brand × Month) — case/space-insensitive.
        When a match is found, sets Chain and Override_Cont_Pct on the row.
        """
        if override_csv is None:
            override_csv = Path("PowerBI/SeedData/Masters/PrimaryAllocationOverride.csv")

        if not override_csv.exists():
            return primary_row

        try:
            overrides = pd.read_csv(override_csv)
        except Exception as e:
            print(f"Warning: Could not load overrides from {override_csv}: {e}")
            return primary_row

        if overrides.empty:
            return primary_row

        # Normalise column names to handle spaces in headers
        overrides.columns = [c.strip() for c in overrides.columns]

        # Match key: (Ship To Name, Brand, Month) — case-insensitive
        st = str(primary_row.get("_CustName", primary_row.get("Ship To Name", ""))).strip().lower()
        brand = str(primary_row.get("brand", primary_row.get("Brand", ""))).strip().lower()
        month = str(primary_row.get("Month", ""))

        if st and brand and month and "Ship To Name" in overrides.columns and "Brand" in overrides.columns:
            match = overrides[
                (overrides["Ship To Name"].astype(str).str.strip().str.lower() == st)
                & (overrides["Brand"].astype(str).str.strip().str.lower() == brand)
                & (overrides.get("Month", pd.Series(dtype=str)).astype(str) == month)
            ]
            if not match.empty:
                override_row = match.iloc[0]
                if "Chain" in override_row and pd.notna(override_row["Chain"]):
                    primary_row = primary_row.copy()
                    primary_row["Chain"] = override_row["Chain"]
                if "Override Cont%" in override_row and pd.notna(override_row["Override Cont%"]):
                    primary_row["Override_Cont_Pct"] = float(override_row["Override Cont%"])

        return primary_row

    def generate_qc_report(
        self, qc_results: list[QCReconciliation]
    ) -> dict:
        """
        Generate QC summary report from list of reconciliation results.

        Returns:
            Dict with summary stats: total_rows, balanced, unbalanced, variance_sum, etc.
        """
        if not qc_results:
            return {
                "total_rows": 0,
                "balanced": 0,
                "unbalanced": 0,
                "total_variance": 0.0,
                "max_variance": 0.0,
                "note": "No QC results provided",
            }

        balanced_count = sum(1 for r in qc_results if r.is_balanced)
        unbalanced_count = len(qc_results) - balanced_count
        total_variance = sum(r.variance for r in qc_results)
        max_variance = max((abs(r.variance) for r in qc_results), default=0.0)

        return {
            "total_rows": len(qc_results),
            "balanced": balanced_count,
            "unbalanced": unbalanced_count,
            "total_variance_lakh": round(total_variance, 2),
            "max_variance_lakh": round(max_variance, 2),
            "balance_rate_pct": round(balanced_count / len(qc_results) * 100, 1) if qc_results else 0.0,
            "note": "QC gate PASSES if all rows balanced (variance = 0.0)" if unbalanced_count == 0 else f"{unbalanced_count} rows with non-zero variance",
        }


# ── Standalone helpers ──────────────────────────────────────────────────────

def eligibility_tier_rank(tier: str) -> int:
    """Return sort order for eligibility tiers (lower = more eligible)."""
    tier_order = {
        "Eligible": 1,
        "Eligible_TAT": 2,
        "Brand_Not_Listed": 3,
        "Article_Not_Listed": 4,
        "Not_Eligible": 5,
    }
    return tier_order.get(tier, 99)


def load_override_master(
    override_path: Path = None,
) -> pd.DataFrame:
    """
    Load PrimaryAllocationOverride.csv with validation.

    Returns:
        DataFrame with columns: Ship_To_Name, Brand, Month, Chain, Eligibility_Tier, Approval_Date
    """
    if override_path is None:
        override_path = Path("PowerBI/SeedData/Masters/PrimaryAllocationOverride.csv")

    if not override_path.exists():
        return pd.DataFrame()

    df = pd.read_csv(override_path)

    # Validate key columns
    required = ["Ship_To_Name", "Brand", "Month"]
    if not all(col in df.columns for col in required):
        print(f"Warning: Override master missing required columns {required}")
        return df

    return df


if __name__ == "__main__":
    # Simple validation test
    gov = DistAllocationGovernance()

    # Test Tier 1: Exact match
    result = gov.check_eligibility(
        primary_row={"ship_to": "ABC Dist", "brand": "Mamaearth", "month": "2026-04"},
        secondary_match_found=True,
        secondary_match_within_tат=False,
        brand_in_offtake=True,
        article_in_offtake=True,
    )
    print(f"Tier 1: {result.tier} ({result.confidence_pct}%) — {result.reasoning}")
    assert result.tier == "Eligible", f"Expected Eligible, got {result.tier}"

    # Test Tier 2: TAT fallback
    result = gov.check_eligibility(
        primary_row={"ship_to": "ABC Dist", "brand": "Mamaearth", "month": "2026-05"},
        secondary_match_found=False,
        secondary_match_within_tат=True,
        brand_in_offtake=True,
        article_in_offtake=True,
    )
    print(f"Tier 2: {result.tier} ({result.confidence_pct}%) — {result.reasoning}")
    assert result.tier == "Eligible_TAT", f"Expected Eligible_TAT, got {result.tier}"

    # Test Tier 3: Brand not listed
    result = gov.check_eligibility(
        primary_row={"ship_to": "XYZ Dist", "brand": "Unknown", "month": "2026-06"},
        secondary_match_found=False,
        secondary_match_within_tат=False,
        brand_in_offtake=False,
        article_in_offtake=True,
    )
    print(f"Tier 3: {result.tier} ({result.confidence_pct}%) — {result.reasoning}")
    assert result.tier == "Brand_Not_Listed", f"Expected Brand_Not_Listed, got {result.tier}"

    # Test QC reconciliation
    qc = gov.reconcile_qc(
        distributor="ABC Dist",
        brand="Mamaearth",
        month="2026-04",
        original_nsv=1000.0,
        allocated_nsv=900.0,
        blocked_nsv=100.0,
        tolerance_lakh=0.0,
    )
    print(f"QC Reconciliation: balanced={qc.is_balanced}, variance={qc.variance}")
    assert qc.is_balanced, "Expected QC to balance"

    print("\n✓ All governance tests passed")
