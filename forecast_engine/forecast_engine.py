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

# unit_nsv above this threshold indicates the margin row stores aggregate (case/shipment) values,
# not per-consumer-unit values — flag as IMPLAUSIBLE_UNIT_NSV and zero out P&L fields.
UNIT_NSV_CEILING = 2000.0


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
                festival_name=article_key["festival_name"],
                uplift_pct=article_key.get("festival_uplift_pct"),
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

    def _resolve_margin(
        self,
        ean: str,
        chain: str,
        margin_data: pd.DataFrame,
        category: Optional[str] = None,
        brand: Optional[str] = None,
        tentative_mode: bool = False,
    ) -> Tuple[Optional[object], str, str, str]:
        """Resolve margin data using 5-level fallback hierarchy.

        Returns (row_or_series, value_source, fallback_method, confidence_level).
        row_or_series is None when no margin data is available at any level.
        """
        if margin_data.empty:
            return None, "NO_DATA", "NO_MARGIN_AVAILABLE", "LOW"

        chain_col = "chain_name" if "chain_name" in margin_data.columns else "chain"

        # VMM exclusion in tentative mode
        if tentative_mode and chain == "VMM":
            return None, "EXCLUDED_VMM", "VMM_EXCLUDED", "EXCLUDED"

        # Level 1: Finance-approved exact EAN × chain match
        if "approval_status" in margin_data.columns:
            lvl1 = margin_data[
                (margin_data["ean"] == ean) &
                (margin_data[chain_col] == chain) &
                (margin_data["approval_status"] == "FINANCE_APPROVED")
            ]
            if not lvl1.empty:
                return lvl1.iloc[0], "FINANCE_APPROVED", "EXACT_MATCH", "HIGH"

        # Level 2: Any non-ESTIMATED exact EAN × chain match
        qs_col = "quality_status" if "quality_status" in margin_data.columns else None
        lvl2_mask = (margin_data["ean"] == ean) & (margin_data[chain_col] == chain)
        if qs_col:
            lvl2_mask = lvl2_mask & (margin_data[qs_col] != "ESTIMATED")
        lvl2 = margin_data[lvl2_mask]
        if not lvl2.empty:
            qs = lvl2.iloc[0].get(qs_col, "DERIVED") if qs_col else "DERIVED"
            return lvl2.iloc[0], str(qs), "EAN_CHAIN_EXACT", "HIGH"

        # Level 3: ESTIMATED exact EAN × chain (tentative only — warn, still use)
        if tentative_mode:
            lvl3 = margin_data[
                (margin_data["ean"] == ean) & (margin_data[chain_col] == chain)
            ]
            if not lvl3.empty:
                return lvl3.iloc[0], "ESTIMATED", "EAN_CHAIN_ESTIMATED", "LOW"

        # Level 4: Category × chain average (non-ESTIMATED, non-VMM)
        if tentative_mode and category and "category" in margin_data.columns:
            base_mask = (margin_data[chain_col] != "VMM")
            if qs_col:
                base_mask = base_mask & (margin_data[qs_col] != "ESTIMATED")
            lvl4 = margin_data[
                base_mask &
                (margin_data["category"] == category) &
                (margin_data[chain_col] == chain)
            ]
            if not lvl4.empty:
                avg = lvl4[
                    [c for c in ["mrp", "margin_pct", "cm2_pct", "tot_pct"]
                     if c in lvl4.columns]
                ].apply(pd.to_numeric, errors="coerce").mean()
                return avg, "DERIVED", "CATEGORY_CHAIN_AVG", "MEDIUM"

        # Level 5: Brand × national average (non-ESTIMATED, non-VMM)
        if tentative_mode and brand and "brand" in margin_data.columns:
            base_mask = (margin_data[chain_col] != "VMM")
            if qs_col:
                base_mask = base_mask & (margin_data[qs_col] != "ESTIMATED")
            lvl5 = margin_data[base_mask & (margin_data["brand"] == brand)]
            if not lvl5.empty:
                avg = lvl5[
                    [c for c in ["mrp", "margin_pct", "cm2_pct", "tot_pct"]
                     if c in lvl5.columns]
                ].apply(pd.to_numeric, errors="coerce").mean()
                return avg, "DERIVED", "BRAND_NATIONAL_AVG", "MEDIUM"

        return None, "NO_DATA", "NO_MARGIN_AVAILABLE", "LOW"

    def compute_nsv_and_trade_spend(
        self,
        forecast: Dict,
        margin_data: pd.DataFrame,
        mrp: Optional[float] = None,
        tentative_mode: bool = False,
    ) -> Dict:
        """Compute NSV, Primary, Offtake, Trade Spend, CM2."""
        ean = forecast.get("ean")
        chain = forecast.get("chain_name")
        category = forecast.get("category")
        brand = forecast.get("brand")

        row, value_source, fallback_method, confidence_level = self._resolve_margin(
            ean, chain, margin_data,
            category=category, brand=brand,
            tentative_mode=tentative_mode,
        )

        # Traceability fields
        forecast["value_source"] = value_source
        forecast["fallback_method"] = fallback_method
        forecast["confidence_level"] = confidence_level

        # Preserve original (gross) quantity before any exclusion zeroing
        gross_qty = float(forecast.get("forecast_qty", 0))

        if row is None:
            # VMM or no-data exclusion: zero operational qty, keep gross for reconciliation
            forecast["gross_forecast_qty"] = gross_qty
            forecast["operational_inclusion_flag"] = False
            forecast["exclusion_reason"] = (
                "VMM_EXCLUDED_TENTATIVE" if value_source == "EXCLUDED_VMM"
                else f"NO_MARGIN_DATA:{fallback_method}"
            )
            forecast["forecast_qty"] = 0.0
            forecast["forecast_nsv"] = 0.0
            forecast["forecast_primary_qty"] = 0.0
            forecast["forecast_offtake_qty"] = 0.0
            forecast["forecast_trade_spend"] = 0.0
            forecast["forecast_cm2"] = 0.0
            forecast["unit_price_status"] = "NO_MARGIN_DATA"
            forecast["cm2_label"] = "PROVISIONAL_CM2_NOT_FINANCE_APPROVED"
            forecast["is_tentative"] = tentative_mode
            return forecast

        # Non-excluded operational row
        forecast["gross_forecast_qty"] = gross_qty
        forecast["operational_inclusion_flag"] = True
        forecast["exclusion_reason"] = ""

        # ── pull repaired fields from fact_margin ──────────────────────────
        mrp_val         = float(mrp or row.get("mrp", 0))
        gst_pct         = float(row.get("gst_pct", 0) or 0)
        tot_pct         = float(row.get("tot_pct", 0) or row.get("margin_pct", 0) or 0)
        quality_status  = str(row.get("quality_status", "DERIVED") or "DERIVED")
        mrp_denomination = str(row.get("mrp_denomination", "") or "")

        # Prefer validated NSV from primary invoice history (brand actual NSV).
        # Falls back to formula with stored tot_pct for ESTIMATED/UNKNOWN rows.
        unit_nsv_validated = row.get("unit_nsv_validated")
        unit_nsv_source    = str(row.get("unit_nsv_source", "") or "UNAVAILABLE")

        try:
            unit_nsv_validated = float(unit_nsv_validated) if unit_nsv_validated not in (None, "", "nan") else None
        except (TypeError, ValueError):
            unit_nsv_validated = None

        # ── denomination routing ───────────────────────────────────────────
        # PACK_CASE_LEVEL_MRP and AGGREGATE_DENOMINATION: cannot produce consumer-
        # unit NSV without validated pack-size conversion factor. Quantity forecast
        # is retained for operational planning; NSV/CM2 are set to UNAVAILABLE.
        if mrp_denomination in ("PACK_CASE_LEVEL_MRP", "AGGREGATE_DENOMINATION"):
            forecast["unit_price_status"] = f"NO_UNIT_NSV_{mrp_denomination}"
            forecast["forecast_nsv"]       = 0.0
            forecast["forecast_trade_spend"] = 0.0
            forecast["forecast_cm2"]       = 0.0
            forecast["cm2_label"]          = "PROVISIONAL_CM2_NOT_FINANCE_APPROVED"
            primary_qty = gross_qty / max(tot_pct / 100.0, 0.01)
            forecast["forecast_primary_qty"]  = round(primary_qty, 2)
            forecast["forecast_offtake_qty"]  = round(gross_qty, 2)
            forecast["is_tentative"]          = tentative_mode
            return forecast

        # ── compute unit NSV ───────────────────────────────────────────────
        if unit_nsv_validated is not None and unit_nsv_validated > 0:
            # PRIMARY_INVOICE_HISTORY — most reliable: actual brand NSV from invoices
            unit_nsv = unit_nsv_validated
            price_source = unit_nsv_source
        else:
            # Authoritative formula fallback: NSV = MRP / ((1+GST/100) × (1+TOT/100))
            gst_factor = 1.0 + gst_pct / 100.0
            tot_factor = 1.0 + tot_pct / 100.0
            if mrp_val > 0 and gst_factor > 1.0 and tot_factor > 1.0:
                unit_nsv = mrp_val / (gst_factor * tot_factor)
            else:
                unit_nsv = 0.0
            price_source = "FORMULA_FALLBACK_STORED_TOT"

        if unit_nsv <= 0:
            forecast["unit_price_status"] = "ZERO_OR_NEGATIVE_UNIT_NSV"
            forecast["forecast_nsv"]       = 0.0
            forecast["forecast_trade_spend"] = 0.0
            forecast["forecast_cm2"]       = 0.0
            forecast["cm2_label"]          = "PROVISIONAL_CM2_NOT_FINANCE_APPROVED"
            primary_qty = gross_qty / max(tot_pct / 100.0, 0.01)
            forecast["forecast_primary_qty"]  = round(primary_qty, 2)
            forecast["forecast_offtake_qty"]  = round(gross_qty, 2)
            forecast["is_tentative"]          = tentative_mode
            return forecast

        # Guard: unit_nsv must not exceed MRP
        if unit_nsv > mrp_val > 0:
            forecast["unit_price_status"] = "NSV_EXCEEDS_MRP_ERROR"
            forecast["forecast_nsv"]       = 0.0
            forecast["forecast_trade_spend"] = 0.0
            forecast["forecast_cm2"]       = 0.0
            forecast["cm2_label"]          = "PROVISIONAL_CM2_NOT_FINANCE_APPROVED"
            primary_qty = gross_qty / max(tot_pct / 100.0, 0.01)
            forecast["forecast_primary_qty"]  = round(primary_qty, 2)
            forecast["forecast_offtake_qty"]  = round(gross_qty, 2)
            forecast["is_tentative"]          = tentative_mode
            return forecast

        forecast["unit_price_status"] = f"VALIDATED_NSV:{price_source}"

        # Trade spend = NSV × TOT% / 100
        # Equivalent to (MRP_ex_gst − NSV) when NSV is formula-derived; yields a
        # brand-level trade cost that is always ≤ NSV regardless of NSV source.
        trade_spend_per_unit = unit_nsv * tot_pct / 100.0

        primary_qty = gross_qty / max(tot_pct / 100.0, 0.01)
        forecast["forecast_primary_qty"]  = round(primary_qty, 2)
        forecast["forecast_offtake_qty"]  = round(gross_qty, 2)
        forecast["forecast_nsv"]          = round(gross_qty * unit_nsv, 2)
        forecast["forecast_trade_spend"]  = round(gross_qty * trade_spend_per_unit, 2)

        # ── CM2 computation — separate paths by cm2_value_type ─────────────
        # DERIVED rows:   cm2_value_type = PER_UNIT_RUPEES
        #                 cm2_value_per_unit = mrp × 0.12 (₹/unit absolute, provisional)
        # ESTIMATED rows: cm2_value_type = PERCENT_OF_NSV
        #                 cm2_pct_rate = 15.0 (provisional % of NSV)
        cm2_value_type    = str(row.get("cm2_value_type", "") or "")
        cm2_value_per_unit = row.get("cm2_value_per_unit")
        cm2_pct_rate       = row.get("cm2_pct_rate")

        try:
            cm2_value_per_unit = float(cm2_value_per_unit) if cm2_value_per_unit not in (None, "", "nan") else None
        except (TypeError, ValueError):
            cm2_value_per_unit = None

        try:
            cm2_pct_rate = float(cm2_pct_rate) if cm2_pct_rate not in (None, "", "nan") else None
        except (TypeError, ValueError):
            cm2_pct_rate = None

        if cm2_value_type == "PER_UNIT_RUPEES" and cm2_value_per_unit is not None:
            forecast["forecast_cm2"] = round(gross_qty * cm2_value_per_unit, 2)
        elif cm2_value_type == "PERCENT_OF_NSV" and cm2_pct_rate is not None:
            forecast["forecast_cm2"] = round(forecast["forecast_nsv"] * cm2_pct_rate / 100.0, 2)
        else:
            # Legacy fallback: DERIVED uses cm2_pct field directly (₹/unit);
            # ESTIMATED uses cm2_pct as % of NSV (for fact_margin rows not yet repaired)
            legacy_cm2_pct = float(row.get("cm2_pct", 0) or 0)
            if quality_status == "ESTIMATED":
                forecast["forecast_cm2"] = round(forecast["forecast_nsv"] * legacy_cm2_pct / 100.0, 2)
            else:
                forecast["forecast_cm2"] = round(gross_qty * legacy_cm2_pct, 2)

        cm2_approval = str(row.get("cm2_approval_status", "") or "")
        if cm2_approval == "FINANCE_APPROVED" and value_source == "FINANCE_APPROVED":
            forecast["cm2_label"] = "FINANCE_APPROVED_CM2"
        else:
            forecast["cm2_label"] = "PROVISIONAL_CM2_NOT_FINANCE_APPROVED"

        forecast["is_tentative"] = tentative_mode
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
        verbose: bool = True,
        events_calendar_path: Optional[str] = None,
        launch_plan_path: Optional[str] = None,
        tentative_mode: bool = False,
    ) -> pd.DataFrame:
        """Execute end-to-end forecast for all articles."""
        self.verbose = verbose
        mode_label = "TENTATIVE" if tentative_mode else "FINAL"
        self.log(f"Starting {mode_label} forecast for {len(article_catalog)} articles, {num_forecast_months} months")

        events_df = pd.DataFrame()
        if events_calendar_path and os.path.exists(events_calendar_path):
            events_df = pd.read_csv(events_calendar_path, dtype=str)
            self.log(f"Loaded {len(events_df)} events from {events_calendar_path}")

        launch_df = pd.DataFrame()
        if launch_plan_path and os.path.exists(launch_plan_path):
            launch_df = pd.read_csv(launch_plan_path, dtype=str)
            if not launch_df.empty:
                self.log(f"Loaded {len(launch_df)} NPI launch plans from {launch_plan_path}")

        forecasts = []
        # start_month_offset=1: forecast begins next calendar month, never the current month.
        forecast_months = get_forecast_months(num_months=num_forecast_months, start_month_offset=1)

        # Horizon guard: the current month must never appear in the forecast output.
        today = dt.date.today()
        current_month_tuple = (today.year, today.month)
        if current_month_tuple in forecast_months:
            raise ValueError(
                f"Forecast horizon guard failed: current month {current_month_tuple} "
                f"must not appear in forecast. Got months: {forecast_months}. "
                "Check start_month_offset in get_forecast_months()."
            )

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

                # Apply event uplift from calendar for this forecast month
                # Uses 5-level fallback hierarchy in tentative mode
                article.pop("festival_name", None)
                article.pop("festival_uplift_pct", None)
                article.pop("uplift_value_source", None)
                if not events_df.empty and "forecast_month" in events_df.columns:
                    month_events = events_df[
                        events_df["forecast_month"] == forecast_month_str
                    ]
                    if not month_events.empty:
                        chain_match = (
                            month_events["chain_filter"].isin(["ALL", chain]) if "chain_filter" in month_events.columns
                            else pd.Series(True, index=month_events.index)
                        )
                        brand_match = (
                            month_events["brand_filter"].isin(["ALL", article.get("brand", "")]) if "brand_filter" in month_events.columns
                            else pd.Series(True, index=month_events.index)
                        )
                        applicable = month_events[chain_match & brand_match]
                        if not applicable.empty:
                            best = applicable.loc[
                                pd.to_numeric(applicable["uplift_pct"], errors="coerce").fillna(0).idxmax()
                            ]
                            event_status = str(best.get("status", "PLACEHOLDER_TBC"))
                            event_uplift = float(best.get("uplift_pct", 0) or 0)

                            if event_status == "APPROVED" and event_uplift > 0:
                                # Level 1 (HIGH): APPROVED uplift
                                article["festival_name"] = best["event_name"]
                                article["festival_uplift_pct"] = event_uplift
                                article["uplift_value_source"] = "APPROVED_EVENT"
                            elif tentative_mode:
                                # Level 2 (HIGH): Proposed uplift from Proposed_base_pct column
                                proposed = float(best.get("Proposed_base_pct", 0) or 0)
                                if proposed > 0:
                                    article["festival_name"] = best["event_name"]
                                    article["festival_uplift_pct"] = proposed
                                    article["uplift_value_source"] = "PROPOSED_UPLIFT"
                                else:
                                    # Level 5 (LOW): 0% uplift — conservative baseline
                                    article["festival_name"] = best["event_name"]
                                    article["festival_uplift_pct"] = 0.0
                                    article["uplift_value_source"] = "ZERO_UPLIFT_TENTATIVE"
                            else:
                                # Non-tentative: use whatever is in uplift_pct (even placeholder)
                                article["festival_name"] = best["event_name"]
                                article["festival_uplift_pct"] = event_uplift
                                article["uplift_value_source"] = "PLACEHOLDER"

                # Apply NPI uplift from launch plan
                article.pop("days_since_launch", None)
                if not launch_df.empty and "ean" in launch_df.columns:
                    npi_rows = launch_df[
                        (launch_df["ean"] == ean) &
                        (launch_df["chain_name"].isin(["ALL", chain]))
                    ]
                    if not npi_rows.empty:
                        launch_month_str = npi_rows.iloc[0]["launch_month"]
                        try:
                            launch_date = dt.datetime.strptime(launch_month_str, "%Y-%m").date()
                            days_since = (dt.date(year, month, 1) - launch_date).days
                            if days_since >= 0:
                                article["days_since_launch"] = days_since
                        except (ValueError, TypeError):
                            pass

                forecast = self.compute_base_forecast(article, historical_demand, margin_data)
                forecast["forecast_month"] = forecast_month_str
                forecast["forecast_fy"] = forecast_fy_str
                forecast["is_tentative"] = tentative_mode
                forecast["uplift_value_source"] = article.pop("uplift_value_source", "")
                forecast = self.compute_nsv_and_trade_spend(
                    forecast, margin_data, tentative_mode=tentative_mode
                )
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
