# -*- coding: utf-8 -*-
"""Core forecasting engine.

Consumes:
- Margin Repository published data
- Historical Primary & Offtake
- Store Master
- Target plans
- Inventory (optional)
- Event/NPI/Seasonal calendars

Produces:
- Chain × Brand × Article forecasts
- Scenario variants (Best/Expected/Worst)
- Warehouse allocation recommendations
- Exception flags and risk scoring
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import datetime as dt
import uuid
import os

from forecast_engine.forecast_schema import (
    validate_forecast_frame, compute_fy_from_date, get_forecast_months,
    RISK_TIER_RULES, EXCEPTION_TYPES, WAREHOUSE_ALLOCATION_HIERARCHY
)
from forecast_engine.forecast_drivers import (
    compute_mom_trend, compute_yoy_trend, compute_weighted_moving_average,
    compute_seasonality_factor, apply_festival_uplift, apply_npi_uplift,
    compute_margin_change_impact, compute_distribution_expansion_impact,
    compute_confidence_interval, score_forecast_driver
)
from forecast_engine.data_normalizer import DataNormalizer


class ForecastEngine:
    """Production-grade demand forecasting engine."""

    def __init__(self, margin_repo_path: str, verbose: bool = True):
        """Initialize engine with margin repository path."""
        self.margin_repo_path = margin_repo_path
        self.verbose = verbose
        self.forecasts = []
        self.exceptions = []
        self.scenarios = {}

    def log(self, msg: str):
        if self.verbose:
            print(f"[FORECAST] {msg}")

    def load_margin_repository(self) -> pd.DataFrame:
        """Load published margin data from repository."""
        import os
        import csv

        margin_file = os.path.join(
            self.margin_repo_path, "Release_v1.0.0_RC1", "04_Business_Outputs", "fact_margin.csv"
        )

        if not os.path.exists(margin_file):
            raise FileNotFoundError(f"Margin file not found: {margin_file}")

        self.log(f"Loading margin data from {margin_file}")
        df = pd.read_csv(margin_file, dtype=str)

        # Normalize column names and data types
        df = DataNormalizer.normalize(df, source_type="margin")

        return df

    def load_historical_demand(
        self,
        primary_path: str,
        offtake_path: str,
        months_back: int = 12
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Load historical primary and offtake data."""
        self.log(f"Loading {months_back} months of historical demand")

        primary = pd.read_csv(primary_path, dtype=str) if os.path.exists(primary_path) else pd.DataFrame()
        offtake = pd.read_csv(offtake_path, dtype=str) if os.path.exists(offtake_path) else pd.DataFrame()

        # Normalize column names and data types
        if not primary.empty:
            primary = DataNormalizer.normalize(primary, source_type="primary")
        if not offtake.empty:
            offtake = DataNormalizer.normalize(offtake, source_type="offtake")

        return primary, offtake

    def compute_base_forecast(
        self,
        article_key: Dict,
        historical_demand: pd.DataFrame,
        margin_data: pd.DataFrame,
        target_qty: Optional[float] = None
    ) -> Dict:
        """Compute base forecast for one Chain × Brand × Article."""
        forecast = {
            "forecast_id": str(uuid.uuid4()),
            "chain_name": article_key.get("chain_name"),
            "zone": article_key.get("zone"),
            "state": article_key.get("state"),
            "brand": article_key.get("brand"),
            "category": article_key.get("category"),
            "article": article_key.get("article"),
            "ean": article_key.get("ean"),
        }

        if historical_demand.empty:
            forecast["forecast_qty"] = target_qty or 0.0
            forecast["confidence_pct"] = 50.0
            forecast["risk_level"] = "HIGH_RISK"
            forecast["forecast_driver_primary"] = "Insufficient_History"
            forecast["forecast_driver_secondary"] = "None"
            return forecast

        forecast["historical_offtake_qty"] = float(historical_demand["quantity"].sum())
        primary_col = historical_demand.get("primary_qty") if "primary_qty" in historical_demand.columns else None
        forecast["historical_primary_qty"] = float(primary_col.sum()) if primary_col is not None else 0.0

        mom_trend = compute_mom_trend(historical_demand, str(article_key), months_back=3)
        yoy_trend = compute_yoy_trend(historical_demand, str(article_key))
        weighted_ma = compute_weighted_moving_average(historical_demand)
        seasonality = compute_seasonality_factor(
            historical_demand,
            target_month=dt.date.today().month,
            base_avg=historical_demand["quantity"].mean()
        )

        forecast["mom_trend_pct"] = round(mom_trend, 2)
        forecast["yoy_trend_pct"] = round(yoy_trend, 2)
        forecast["weighted_ma_qty"] = round(weighted_ma, 2)
        forecast["seasonality_factor"] = round(seasonality, 3)

        base_forecast_qty = weighted_ma * seasonality

        base_forecast_qty *= (1 + yoy_trend / 100.0) if yoy_trend > 0 else 1.0

        festival_uplift = 0.0
        if "festival_name" in article_key:
            base_forecast_qty, festival_uplift = apply_festival_uplift(
                base_forecast_qty,
                festival_name=article_key["festival_name"]
            )

        npi_uplift = 0.0
        if "days_since_launch" in article_key:
            base_forecast_qty, npi_uplift = apply_npi_uplift(
                base_forecast_qty,
                days_since_launch=article_key["days_since_launch"]
            )

        forecast["festival_uplift"] = round(festival_uplift, 2)
        forecast["npi_uplift"] = round(npi_uplift, 2)
        forecast["forecast_qty"] = round(max(0, base_forecast_qty), 2)

        confidence_pct, ci_lower, ci_upper = compute_confidence_interval(
            forecast["forecast_qty"],
            historical_std=float(historical_demand["quantity"].std()) if len(historical_demand) > 1 else 0.0
        )
        forecast["confidence_pct"] = round(confidence_pct, 2)

        pct_diff = abs(forecast["forecast_qty"] - weighted_ma) / max(weighted_ma, 1) * 100
        if pct_diff <= 1.0:
            forecast["risk_level"] = "NORMAL"
        elif pct_diff <= 3.0:
            forecast["risk_level"] = "WARNING"
        elif pct_diff <= 5.0:
            forecast["risk_level"] = "HIGH_RISK"
        else:
            forecast["risk_level"] = "BLOCKED"

        primary, secondary = score_forecast_driver(
            mom_trend, yoy_trend, seasonality, npi_uplift, festival_uplift
        )
        forecast["forecast_driver_primary"] = primary
        forecast["forecast_driver_secondary"] = secondary

        forecast["forecast_timestamp"] = dt.datetime.now().isoformat(timespec="seconds")
        forecast["version"] = "1.0"
        forecast["created_by"] = "ForecastEngine"

        return forecast

    def compute_nsv_and_trade_spend(
        self,
        forecast: Dict,
        margin_data: pd.DataFrame,
        mrp: Optional[float] = None
    ) -> Dict:
        """Compute NSV, Primary, Offtake, Trade Spend, CM2."""
        ean = forecast.get("ean")
        chain = forecast.get("chain_name")

        margin_col = "chain_name" if "chain_name" in margin_data.columns else "chain"
        margin_row = margin_data[
            (margin_data["ean"] == ean) & (margin_data[margin_col] == chain)
        ]

        if margin_row.empty:
            forecast["forecast_nsv"] = 0.0
            forecast["forecast_primary_qty"] = 0.0
            forecast["forecast_offtake_qty"] = forecast["forecast_qty"]
            forecast["forecast_trade_spend"] = 0.0
            forecast["forecast_cm2"] = 0.0
            return forecast

        row = margin_row.iloc[0]
        mrp_val = float(mrp or row.get("mrp", 0))
        # Accept both the legacy synthetic column names and the real fact_margin column names
        margin_pct = float(row.get("final_effective_margin_pct") or row.get("margin_pct") or 0)
        distribution_pct = float(row.get("distribution_pct") or row.get("tot_pct") or 0)

        forecast["forecast_nsv"] = round(forecast["forecast_qty"] * mrp_val, 2)

        primary_qty = forecast["forecast_qty"] / max(distribution_pct / 100.0, 0.01)
        forecast["forecast_primary_qty"] = round(primary_qty, 2)
        forecast["forecast_offtake_qty"] = round(forecast["forecast_qty"], 2)

        trade_spend = primary_qty * (mrp_val * margin_pct / 100.0)
        forecast["forecast_trade_spend"] = round(trade_spend, 2)

        cm2 = (primary_qty * mrp_val * margin_pct / 100.0) - trade_spend
        forecast["forecast_cm2"] = round(cm2, 2)

        return forecast

    def allocate_warehouse(self, forecast: Dict, warehouse_map: Optional[Dict] = None) -> Dict:
        """Allocate forecast quantity to warehouses based on zone/state."""
        DEFAULT_ALLOCATION = {
            "Gurgaon": 0.35,
            "Mumbai": 0.30,
            "Bangalore": 0.25,
            "Kolkata": 0.10,
        }

        if warehouse_map is None:
            warehouse_map = DEFAULT_ALLOCATION

        total_dispatch = forecast.get("forecast_primary_qty", 0)

        for warehouse, alloc_pct in warehouse_map.items():
            col = warehouse.lower().replace(" ", "_")
            forecast[f"warehouse_{col}"] = round(total_dispatch * alloc_pct, 2)

        forecast["suggested_dispatch_qty"] = round(total_dispatch, 2)

        return forecast

    def flag_exceptions(self, forecast: Dict, threshold_accuracy: float = 0.85) -> Dict:
        """Flag forecast exceptions and anomalies."""
        exceptions = []

        if forecast.get("confidence_pct", 0) < 60:
            exceptions.append(("LOW_CONFIDENCE", f"Confidence {forecast['confidence_pct']}% < 60%"))

        if forecast.get("risk_level") == "HIGH_RISK" or forecast.get("risk_level") == "BLOCKED":
            exceptions.append(("RISK_FLAGGED", f"Risk level {forecast['risk_level']}"))

        yoy_trend = forecast.get("yoy_trend_pct", 0)
        if yoy_trend > 50:
            exceptions.append(("HIGH_GROWTH_SKU", f"YoY trend {yoy_trend}% > 50%"))

        if "npi_uplift" in forecast and forecast["npi_uplift"] > 0:
            exceptions.append(("NPI_WATCHLIST", "New product launch detected"))

        distribution = forecast.get("distribution_pct", 100)
        if distribution < 50:
            exceptions.append(("LOW_DISTRIBUTION", f"Distribution {distribution}% < 50%"))

        if exceptions:
            forecast["exception_flag"] = True
            forecast["exception_reason"] = "; ".join([e[0] for e in exceptions])
        else:
            forecast["exception_flag"] = False
            forecast["exception_reason"] = ""

        return forecast

    def run_forecast(
        self,
        margin_data: pd.DataFrame,
        primary_data: pd.DataFrame,
        offtake_data: pd.DataFrame,
        article_catalog: List[Dict],
        num_forecast_months: int = 3,
        verbose: bool = True
    ) -> pd.DataFrame:
        """Execute end-to-end forecast for all articles."""
        self.verbose = verbose
        self.log(f"Starting forecast for {len(article_catalog)} articles, {num_forecast_months} months")

        forecasts = []
        forecast_months = get_forecast_months(num_months=num_forecast_months)

        for month_idx, (year, month) in enumerate(forecast_months):
            self.log(f"Processing forecast month {month_idx + 1}/{num_forecast_months}: {year}-{month:02d}")

            for article in article_catalog:
                ean = article.get("ean")
                chain = article.get("chain_name")

                if offtake_data.empty or "ean" not in offtake_data.columns:
                    historical_demand = pd.DataFrame()
                else:
                    offtake_chain_col = "chain_name" if "chain_name" in offtake_data.columns else "chain"
                    historical_demand = offtake_data[
                        (offtake_data["ean"] == ean) & (offtake_data[offtake_chain_col] == chain)
                    ].copy()
                    # Engine internals expect "quantity" and "date"; alias from offtake columns
                    if "quantity" not in historical_demand.columns and "offtake_qty" in historical_demand.columns:
                        historical_demand["quantity"] = pd.to_numeric(
                            historical_demand["offtake_qty"], errors="coerce"
                        )
                    if "date" not in historical_demand.columns and "month" in historical_demand.columns:
                        historical_demand["date"] = pd.to_datetime(
                            historical_demand["month"], errors="coerce"
                        )

                forecast_month_str = f"{year}-{month:02d}"
                forecast_fy_str = compute_fy_from_date(dt.date(year, month, 1))
                article["forecast_month"] = forecast_month_str
                article["forecast_fy"] = forecast_fy_str

                forecast = self.compute_base_forecast(article, historical_demand, margin_data)
                forecast["forecast_month"] = forecast_month_str
                forecast["forecast_fy"] = forecast_fy_str
                forecast = self.compute_nsv_and_trade_spend(forecast, margin_data)
                forecast = self.allocate_warehouse(forecast)
                forecast = self.flag_exceptions(forecast)

                forecasts.append(forecast)

        forecasts_df = pd.DataFrame(forecasts)

        ok, errors = validate_forecast_frame(forecasts_df)
        if not ok:
            self.log(f"WARNING: Forecast validation errors: {errors}")

        self.forecasts = forecasts_df
        self.log(f"Forecast complete: {len(forecasts_df)} records generated")

        return forecasts_df
