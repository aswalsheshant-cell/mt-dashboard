# -*- coding: utf-8 -*-
"""Forecast drivers: trends, seasonality, growth factors."""
import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional
import datetime as dt


def compute_mom_trend(historical_df: pd.DataFrame, article_key: str, months_back: int = 3) -> float:
    """Compute month-over-month growth trend (average % change)."""
    if len(historical_df) < 2:
        return 0.0

    recent = historical_df.nlargest(months_back, "date")
    if len(recent) < 2:
        return 0.0

    recent = recent.sort_values("date")
    qty_values = recent["quantity"].values.astype(float)

    mom_changes = []
    for i in range(1, len(qty_values)):
        prev = qty_values[i - 1]
        curr = qty_values[i]
        if prev != 0:
            pct_change = ((curr - prev) / abs(prev)) * 100
            mom_changes.append(pct_change)

    return np.mean(mom_changes) if mom_changes else 0.0


def compute_yoy_trend(historical_df: pd.DataFrame, article_key: str) -> float:
    """Compute year-over-year growth trend (% change)."""
    if len(historical_df) < 12:
        return 0.0

    current_year = historical_df.nlargest(3, "date")["quantity"].mean()
    prior_year = historical_df.nsmallest(3, "date")["quantity"].mean()

    if prior_year == 0:
        return 0.0

    return ((current_year - prior_year) / abs(prior_year)) * 100


def compute_weighted_moving_average(
    historical_df: pd.DataFrame,
    weights: Optional[Dict[int, float]] = None
) -> float:
    """Compute weighted moving average of recent demand."""
    if len(historical_df) == 0:
        return 0.0

    if weights is None:
        weights = {
            1: 0.5,   # most recent = 50%
            2: 0.3,   # 2nd most recent = 30%
            3: 0.2,   # 3rd most recent = 20%
        }

    recent = historical_df.nlargest(3, "date").sort_values("date", ascending=False)
    total_weight = 0.0
    weighted_sum = 0.0

    for idx, (_, row) in enumerate(recent.iterrows(), start=1):
        w = weights.get(idx, 0.0)
        weighted_sum += row["quantity"] * w
        total_weight += w

    return weighted_sum / total_weight if total_weight > 0 else 0.0


def compute_seasonality_factor(
    historical_df: pd.DataFrame,
    target_month: int,
    base_avg: Optional[float] = None
) -> float:
    """Compute seasonality factor for a given month (ratio to average)."""
    if len(historical_df) == 0:
        return 1.0

    if base_avg is None:
        base_avg = historical_df["quantity"].mean()

    if base_avg == 0:
        return 1.0

    # Extract all instances of target_month
    historical_df = historical_df.copy()
    historical_df["month"] = pd.to_datetime(historical_df["date"]).dt.month

    same_month = historical_df[historical_df["month"] == target_month]
    if len(same_month) == 0:
        return 1.0

    month_avg = same_month["quantity"].mean()
    return month_avg / base_avg


def apply_festival_uplift(
    base_qty: float,
    festival_date: Optional[dt.date] = None,
    festival_name: Optional[str] = None,
    uplift_pct: Optional[float] = None
) -> Tuple[float, float]:
    """Apply festival uplift (name → % from calendar)."""
    FESTIVAL_CALENDAR = {
        "Diwali": 35.0,
        "Holi": 25.0,
        "New_Year": 20.0,
        "Navratri": 20.0,
        "Rakhi": 15.0,
        "Christmas": 15.0,
    }

    if uplift_pct is None:
        uplift_pct = FESTIVAL_CALENDAR.get(festival_name, 0.0)

    uplift = base_qty * (uplift_pct / 100.0)
    return base_qty + uplift, uplift_pct


def apply_npi_uplift(
    base_qty: float,
    days_since_launch: int,
    category_type: str = "personal_care"
) -> Tuple[float, float]:
    """Apply new product introduction uplift based on lifecycle stage."""
    NPI_CURVES = {
        "personal_care": {
            0: 0.0,      # Day 0 (launch)
            30: 60.0,    # Month 1
            60: 85.0,    # Month 2
            90: 100.0,   # Month 3 (mature)
        },
        "premium": {
            0: 0.0,
            30: 40.0,
            60: 70.0,
            90: 90.0,
        }
    }

    curve = NPI_CURVES.get(category_type, NPI_CURVES["personal_care"])

    if days_since_launch >= 90:
        penetration = 100.0
    elif days_since_launch <= 0:
        penetration = 0.0
    else:
        surrounding_days = sorted([d for d in curve.keys() if d <= days_since_launch])
        if not surrounding_days:
            penetration = curve[30]
        else:
            penetration = curve[surrounding_days[-1]]

    uplift = base_qty * (penetration / 100.0)
    return base_qty + uplift, penetration


def compute_margin_change_impact(
    new_margin_pct: float,
    old_margin_pct: float,
    historical_qty: float,
    elasticity: float = -0.5
) -> Tuple[float, float]:
    """Compute demand impact from margin change (price elasticity)."""
    if old_margin_pct == 0:
        return historical_qty, 0.0

    margin_change_pct = ((new_margin_pct - old_margin_pct) / abs(old_margin_pct)) * 100
    qty_change_pct = margin_change_pct * elasticity

    new_qty = historical_qty * (1 + qty_change_pct / 100.0)
    return max(0, new_qty), qty_change_pct


def compute_distribution_expansion_impact(
    current_distribution: int,
    target_distribution: int,
    current_qty: float
) -> Tuple[float, float]:
    """Compute incremental demand from distribution expansion."""
    if current_distribution == 0:
        return current_qty, 0.0

    dist_increase_pct = ((target_distribution - current_distribution) / current_distribution) * 100
    qty_increase = current_qty * (dist_increase_pct / 100.0)

    return current_qty + qty_increase, dist_increase_pct


def compute_confidence_interval(
    forecast_qty: float,
    historical_std: float,
    confidence_level: float = 0.95
) -> Tuple[float, float, float]:
    """Compute forecast confidence interval and overall confidence %."""
    if historical_std == 0:
        confidence_pct = 95.0
        ci_width = forecast_qty * 0.1
    else:
        cv = historical_std / max(forecast_qty, 1)
        if cv < 0.1:
            confidence_pct = 95.0
        elif cv < 0.2:
            confidence_pct = 85.0
        elif cv < 0.3:
            confidence_pct = 75.0
        else:
            confidence_pct = 60.0

        ci_width = 1.96 * historical_std if confidence_level == 0.95 else 1.645 * historical_std

    lower_bound = max(0, forecast_qty - ci_width)
    upper_bound = forecast_qty + ci_width

    return confidence_pct, lower_bound, upper_bound


def score_forecast_driver(
    mom_trend: float,
    yoy_trend: float,
    seasonality: float,
    npi_uplift: float,
    festival_uplift: float
) -> Tuple[str, str]:
    """Rank drivers by impact and identify primary + secondary."""
    drivers = {
        "YoY Trend": abs(yoy_trend),
        "Seasonality": abs(seasonality - 1.0) * 100,
        "MoM Trend": abs(mom_trend),
        "NPI Uplift": npi_uplift,
        "Festival Uplift": festival_uplift,
    }

    sorted_drivers = sorted(drivers.items(), key=lambda x: x[1], reverse=True)

    primary = sorted_drivers[0][0] if sorted_drivers else "Baseline"
    secondary = sorted_drivers[1][0] if len(sorted_drivers) > 1 else "None"

    return primary, secondary
