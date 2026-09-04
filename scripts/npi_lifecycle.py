#!/usr/bin/env python3
"""
NPI Lifecycle Calculator — Derive launch age and maturity status for NPI articles.

For each NPI article, computes:
  - launch_age_months: Months since launch_date
  - maturity_status: LAUNCH | BUILD | SCALE | STABILISE | MATURE
  - launch_month_index: Month number since launch (M1, M2, M3, ...)
  - ramp_curve_profile: Applicable ramp profile (configurable by category/price/etc.)

Maturity thresholds (configurable):
  Month 0–1   = LAUNCH
  Month 2–3   = BUILD
  Month 4–6   = SCALE
  Month 7–12  = STABILISE
  Month 12+   = MATURE

These are defaults; thresholds can be overridden per NPI type or category.
"""
from __future__ import annotations
from datetime import datetime, timedelta
from typing import Optional
import math

# ---- Configurable Thresholds ----
# These define the maturity lifecycle. Can be overridden by config file or CLI args.
DEFAULT_MATURITY_THRESHOLDS = {
    "LAUNCH":    (0, 1),      # 0–1 months
    "BUILD":     (2, 3),      # 2–3 months
    "SCALE":     (4, 6),      # 4–6 months
    "STABILISE": (7, 12),     # 7–12 months
    "MATURE":    (13, 1000),  # 13+ months
}

# Default ramp profiles by category/price (these are 12-month index profiles)
# Values represent expected sales as % of mature baseline per month
DEFAULT_RAMP_PROFILES = {
    # Assume similar profile for all categories unless overridden
    "default": [
        0.15,  # M1: 15% of mature baseline
        0.30,  # M2: 30%
        0.45,  # M3: 45%
        0.60,  # M4: 60%
        0.72,  # M5: 72%
        0.82,  # M6: 82%
        0.88,  # M7: 88%
        0.93,  # M8: 93%
        0.96,  # M9: 96%
        0.98,  # M10: 98%
        0.99,  # M11: 99%
        1.00,  # M12: 100%
    ]
}


class NPILifecycleCalculator:
    """Calculate launch age and maturity status for NPI articles."""

    def __init__(self,
                 reference_date: datetime | str | None = None,
                 maturity_thresholds: dict | None = None,
                 ramp_profiles: dict | None = None):
        """
        Args:
            reference_date: Date to calculate age as of (default: today).
            maturity_thresholds: Override default thresholds.
            ramp_profiles: Override default ramp profiles.
        """
        if reference_date is None:
            self.reference_date = datetime.now().date()
        elif isinstance(reference_date, str):
            self.reference_date = datetime.fromisoformat(reference_date).date()
        else:
            self.reference_date = reference_date.date() if hasattr(reference_date, 'date') else reference_date

        self.maturity_thresholds = maturity_thresholds or DEFAULT_MATURITY_THRESHOLDS
        self.ramp_profiles = ramp_profiles or DEFAULT_RAMP_PROFILES

    def calculate_launch_age(self, launch_date: str | datetime) -> dict:
        """
        Calculate launch age metrics for a single NPI article.

        Args:
            launch_date: Launch date as ISO string ('2025-06-15') or datetime.

        Returns:
            {
                "launch_date": "2025-06-15",
                "reference_date": "2026-09-02",
                "launch_age_days": 443,
                "launch_age_months": 14.6,
                "launch_age_months_int": 14,
                "launch_month_index": 14,
                "maturity_status": "MATURE",
                "maturity_threshold": (13, 1000),
                "months_in_stage": 1.6,
            }
        """
        # Parse launch_date
        if isinstance(launch_date, str):
            dt = datetime.fromisoformat(launch_date).date()
        else:
            dt = launch_date.date() if hasattr(launch_date, 'date') else launch_date

        # Calculate age
        age_delta = self.reference_date - dt
        age_days = age_delta.days
        age_months = age_days / 30.44  # Average days per month

        # Determine maturity status
        maturity_status = "UNKNOWN"
        maturity_threshold = None
        months_in_stage = None

        for status, (min_m, max_m) in self.maturity_thresholds.items():
            if min_m <= age_months < max_m + 1:  # +1 to include boundary
                maturity_status = status
                maturity_threshold = (min_m, max_m)
                months_in_stage = age_months - min_m
                break

        return {
            "launch_date": dt.isoformat(),
            "reference_date": self.reference_date.isoformat(),
            "launch_age_days": age_days,
            "launch_age_months": round(age_months, 1),
            "launch_age_months_int": int(age_months),
            "launch_month_index": int(age_months) + 1,  # M1, M2, M3, ... (1-indexed)
            "maturity_status": maturity_status,
            "maturity_threshold": maturity_threshold,
            "months_in_stage": round(months_in_stage, 1) if months_in_stage is not None else None,
        }

    def get_expected_ramp_pct(self, months_since_launch: int, profile_key: str = "default") -> float:
        """
        Get expected sales as % of mature baseline for a given month since launch.

        Args:
            months_since_launch: Month index (1–12 maps to M1–M12).
            profile_key: Ramp profile to use (e.g., "default", "premium_high_price").

        Returns:
            Float 0.0–1.0 representing expected % of mature baseline.
        """
        profile = self.ramp_profiles.get(profile_key) or self.ramp_profiles.get("default")
        if not profile or months_since_launch < 1 or months_since_launch > 12:
            return None
        return profile[months_since_launch - 1]

    def enrich_npi_article(self, article: dict) -> dict:
        """
        Enrich an NPI article dict with lifecycle metrics.

        Args:
            article: NPI article dict with 'launch_date' field.

        Returns:
            Enhanced article dict with lifecycle fields added.
        """
        article = article.copy()
        launch_date = article.get("launch_date")
        if not launch_date:
            return article

        lifecycle = self.calculate_launch_age(launch_date)
        article.update(lifecycle)

        # Add expected ramp pct (Month 1–12)
        m_idx = lifecycle.get("launch_month_index")
        if m_idx and 1 <= m_idx <= 12:
            profile_key = article.get("_ramp_profile_key", "default")
            article["expected_ramp_pct"] = self.get_expected_ramp_pct(m_idx, profile_key)

        return article


def enrich_npi_master_with_lifecycle(npi_master: dict,
                                      reference_date: str | None = None) -> dict:
    """
    Enrich all NPI articles in an NPI Master dict with lifecycle metrics.

    Args:
        npi_master: Dict from NPIMasterLoader.to_dict(), containing 'npi_articles' key.
        reference_date: Reference date for age calculation (default: today).

    Returns:
        Enhanced npi_master dict with lifecycle fields on each article.
    """
    npi_master = dict(npi_master)  # Shallow copy
    calc = NPILifecycleCalculator(reference_date=reference_date)

    articles = npi_master.get("npi_articles", [])
    enriched_articles = [calc.enrich_npi_article(a) for a in articles]

    npi_master["npi_articles"] = enriched_articles
    npi_master["lifecycle_reference_date"] = calc.reference_date.isoformat()
    npi_master["lifecycle_thresholds"] = {
        k: v for k, v in DEFAULT_MATURITY_THRESHOLDS.items()
    }

    return npi_master


if __name__ == "__main__":
    import json, sys

    # Example: calculate lifecycle for a single NPI
    if len(sys.argv) > 1:
        launch_date_str = sys.argv[1]
        calc = NPILifecycleCalculator()
        result = calc.calculate_launch_age(launch_date_str)
        print(json.dumps(result, indent=2))
    else:
        # Demo
        calc = NPILifecycleCalculator()
        test_dates = [
            "2025-06-15",  # ~3 months ago (SCALE)
            "2025-09-01",  # ~1 month ago (BUILD)
            "2024-06-15",  # ~15 months ago (MATURE)
            "2025-08-01",  # ~1 month ago (BUILD/LAUNCH boundary)
        ]
        for d in test_dates:
            result = calc.calculate_launch_age(d)
            print(f"{d} → {result['maturity_status']} (M{result['launch_month_index']})")
