# -*- coding: utf-8 -*-
"""Forecast data model and validation.

Hierarchy:
- Channel (Modern Trade, General Trade, etc.)
- Chain (big-box retail chains)
- Zone (geographic sales zone)
- State (geography)
- Brand (Mamaearth, Honasa, etc.)
- Category (Personal Care, Skincare, etc.)
- Article (EAN-keyed SKU)

Core tables:
- fact_demand_forecast: Chain × Brand × Article level forecasts
- fact_demand_scenario: Best/Expected/Worst case forecasts
- fact_warehouse_allocation: Warehouse-level dispatch recommendations
- fact_business_adjustment: Manual overrides and adjustments
- dim_article: Article/EAN master
- dim_chain: Chain master
- dim_date: Date dimension with FY/Q/M
- dim_zone: Zone hierarchy
"""
import pandas as pd
from typing import Dict, List, Tuple, Optional
import datetime as dt


FORECAST_HIERARCHY = {
    "channel": ["Modern Trade", "General Trade"],
    "severity": ["EXTREME_HIGH", "HIGH", "MEDIUM", "LOW"],
    "risk_level": ["NORMAL", "WARNING", "HIGH_RISK", "BLOCKED"],
    "adjustment_type": [
        "NEW_LISTING", "DELISTING", "EXTRA_VISIBILITY", "PROMOTION",
        "BOGO", "PRICE_CHANGE", "DISTRIBUTOR_CHANGE", "EVENT_SALES", "BULK_ORDER"
    ]
}

FORECAST_COLUMNS = {
    "fact_demand_forecast": [
        # Identity
        "forecast_id", "chain_name", "zone", "state", "brand", "category", "article", "ean",
        "forecast_month", "forecast_fy",
        # Inputs
        "historical_offtake_qty", "historical_primary_qty",
        # Trends
        "mom_trend_pct", "yoy_trend_pct", "weighted_ma_qty",
        # Drivers
        "seasonality_factor", "festival_uplift", "npi_uplift", "distribution_expansion",
        "store_additions", "margin_change_impact", "listing_change_impact",
        # Forecast outputs
        "forecast_qty", "forecast_nsv", "forecast_primary_qty", "forecast_offtake_qty",
        "forecast_trade_spend", "forecast_cm2",
        # Dispatch
        "suggested_dispatch_qty", "warehouse_gurgaon", "warehouse_mumbai",
        "warehouse_bangalore", "warehouse_kolkata",
        # Confidence
        "confidence_pct", "forecast_driver_primary", "forecast_driver_secondary",
        # Risk and exception
        "risk_level", "exception_flag", "exception_reason",
        # Audit
        "forecast_timestamp", "version", "created_by"
    ],
    "fact_business_adjustment": [
        "adjustment_id", "chain_name", "brand", "article", "ean",
        "adjustment_type", "adjustment_qty", "adjustment_reason",
        "planner_name", "adjustment_date", "effective_from",
        "status"  # PENDING, APPROVED, APPLIED, REJECTED
    ]
}

RISK_TIER_RULES = {
    "NORMAL": {"pct_diff_max": 1.0},
    "WARNING": {"pct_diff_max": 3.0},
    "HIGH_RISK": {"pct_diff_max": 5.0},
    "BLOCKED": {"pct_diff_max": float('inf')}
}

EXCEPTION_TYPES = {
    "UNDER_FORECAST": "Actual > Forecast by >3%",
    "OVER_FORECAST": "Forecast > Actual by >3%",
    "INVENTORY_RISK": "Low inventory vs high demand forecast",
    "HIGH_MARGIN_OPPORTUNITY": "High margin SKU with low distribution",
    "LOW_DISTRIBUTION": "<50% chain coverage",
    "HIGH_GROWTH_SKU": ">20% YoY growth",
    "NPI_WATCHLIST": "New article <3 months old",
}

WAREHOUSE_ALLOCATION_HIERARCHY = [
    "Gurgaon",   # North
    "Mumbai",    # West
    "Bangalore", # South
    "Kolkata",   # East
]


def validate_forecast_frame(df: pd.DataFrame) -> Tuple[bool, List[str]]:
    """Validate forecast frame structure and content."""
    errors = []

    required_cols = [
        "chain_name", "brand", "article", "ean", "forecast_month",
        "forecast_qty", "confidence_pct", "risk_level"
    ]
    for col in required_cols:
        if col not in df.columns:
            errors.append(f"Missing required column: {col}")

    if not errors:
        if (df["confidence_pct"] < 0).any() or (df["confidence_pct"] > 100).any():
            errors.append("confidence_pct must be 0-100")
        if not df["risk_level"].isin(FORECAST_HIERARCHY["risk_level"]).all():
            errors.append(f"risk_level must be one of {FORECAST_HIERARCHY['risk_level']}")
        if (df["forecast_qty"] < 0).any():
            errors.append("forecast_qty cannot be negative")

    return len(errors) == 0, errors


def compute_fy_from_date(date_val: dt.date) -> str:
    """Convert date to FY tag (Indian fiscal year Apr-Mar)."""
    if isinstance(date_val, str):
        date_val = dt.datetime.strptime(date_val, "%Y-%m-%d").date()
    month = date_val.month
    year = date_val.year
    if month >= 4:
        return f"FY{year + 1 - 2000}"
    else:
        return f"FY{year - 2000}"


def get_forecast_months(num_months: int = 3, start_date: Optional[dt.date] = None) -> List[Tuple[int, int]]:
    """Return list of (year, month) tuples for next N months."""
    if start_date is None:
        start_date = dt.date.today()

    months = []
    current_date = start_date.replace(day=1)
    for _ in range(num_months):
        months.append((current_date.year, current_date.month))
        if current_date.month == 12:
            current_date = current_date.replace(year=current_date.year + 1, month=1)
        else:
            current_date = current_date.replace(month=current_date.month + 1)

    return months
