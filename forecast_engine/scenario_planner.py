# -*- coding: utf-8 -*-
"""Scenario planning: Best/Expected/Worst case forecasts."""
import pandas as pd
from typing import Dict, Tuple, List
import datetime as dt


class ScenarioPlanner:
    """Generate and manage forecast scenarios."""

    SCENARIO_FACTORS = {
        "expected": {
            "qty_factor": 1.0,
            "margin_factor": 1.0,
            "trade_spend_factor": 1.0,
        },
        "best_case": {
            "qty_factor": 1.2,      # +20% volume
            "margin_factor": 1.1,   # +10% margin
            "trade_spend_factor": 0.95,  # -5% spend
            "description": "Strong demand, improved margins, lower promo spend",
        },
        "worst_case": {
            "qty_factor": 0.75,     # -25% volume
            "margin_factor": 0.9,   # -10% margin
            "trade_spend_factor": 1.2,  # +20% spend
            "description": "Weak demand, margin pressure, higher discounting",
        }
    }

    def __init__(self):
        self.scenarios = {}

    def generate_scenarios(
        self,
        base_forecast_df: pd.DataFrame,
        scenario_names: List[str] = ["expected", "best_case", "worst_case"]
    ) -> Dict[str, pd.DataFrame]:
        """Generate multiple scenarios from base forecast."""
        scenarios = {}

        for scenario_name in scenario_names:
            factor_set = self.SCENARIO_FACTORS.get(scenario_name)
            if factor_set is None:
                continue

            scenario_df = base_forecast_df.copy()

            qty_factor = factor_set.get("qty_factor", 1.0)
            scenario_df["forecast_qty"] = scenario_df["forecast_qty"] * qty_factor
            scenario_df["forecast_nsv"] = scenario_df["forecast_nsv"] * qty_factor
            scenario_df["forecast_primary_qty"] = scenario_df["forecast_primary_qty"] * qty_factor
            scenario_df["forecast_offtake_qty"] = scenario_df["forecast_offtake_qty"] * qty_factor

            for warehouse in ["gurgaon", "mumbai", "bangalore", "kolkata"]:
                col = f"warehouse_{warehouse}"
                if col in scenario_df.columns:
                    scenario_df[col] = scenario_df[col] * qty_factor

            margin_factor = factor_set.get("margin_factor", 1.0)
            scenario_df["forecast_trade_spend"] = scenario_df["forecast_trade_spend"] * factor_set.get("trade_spend_factor", 1.0)
            scenario_df["forecast_cm2"] = (scenario_df["forecast_nsv"] * margin_factor) - scenario_df["forecast_trade_spend"]

            scenario_df["scenario"] = scenario_name
            scenario_df["scenario_description"] = factor_set.get("description", "")

            scenarios[scenario_name] = scenario_df

        self.scenarios = scenarios
        return scenarios

    def build_scenario_summary(
        self,
        scenarios: Dict[str, pd.DataFrame]
    ) -> pd.DataFrame:
        """Build executive summary comparing scenarios."""
        summary_rows = []

        for scenario_name, scenario_df in scenarios.items():
            summary_rows.append({
                "scenario": scenario_name,
                "total_forecast_qty": scenario_df["forecast_qty"].sum(),
                "total_forecast_nsv": scenario_df["forecast_nsv"].sum(),
                "total_primary_qty": scenario_df["forecast_primary_qty"].sum(),
                "total_trade_spend": scenario_df["forecast_trade_spend"].sum(),
                "total_cm2": scenario_df["forecast_cm2"].sum(),
                "avg_confidence_pct": scenario_df["confidence_pct"].mean(),
                "articles_at_risk": (scenario_df["risk_level"].isin(["HIGH_RISK", "BLOCKED"])).sum(),
                "exception_count": scenario_df["exception_flag"].sum(),
            })

        return pd.DataFrame(summary_rows)

    def apply_business_adjustment(
        self,
        forecast_df: pd.DataFrame,
        adjustment: Dict
    ) -> pd.DataFrame:
        """Apply a business adjustment (listing, promo, etc.) to forecast."""
        adjusted = forecast_df.copy()

        numeric_cols = ["forecast_qty", "forecast_nsv", "forecast_primary_qty",
                        "forecast_offtake_qty", "forecast_trade_spend", "forecast_cm2"]
        for col in numeric_cols:
            if col in adjusted.columns:
                adjusted[col] = adjusted[col].astype(float)

        chain = adjustment.get("chain")
        brand = adjustment.get("brand")
        article = adjustment.get("article")
        ean = adjustment.get("ean")
        adjustment_type = adjustment.get("adjustment_type")
        adjustment_qty = float(adjustment.get("adjustment_qty", 0))
        adjustment_reason = adjustment.get("adjustment_reason", "")

        mask = (adjusted["chain"] == chain)
        if brand:
            mask &= (adjusted["brand"] == brand)
        if article:
            mask &= (adjusted["article"] == article)
        if ean:
            mask &= (adjusted["ean"] == ean)

        matched = mask.sum()

        if matched == 0:
            return adjusted

        if adjustment_type == "NEW_LISTING":
            adjusted.loc[mask, "forecast_qty"] += adjustment_qty
            adjusted.loc[mask, "npi_uplift"] = adjustment_qty
            adjusted.loc[mask, "forecast_driver_primary"] = "NEW_LISTING"

        elif adjustment_type == "DELISTING":
            adjusted.loc[mask, "forecast_qty"] = max(0, adjusted.loc[mask, "forecast_qty"] - adjustment_qty)
            adjusted.loc[mask, "exception_flag"] = True
            adjusted.loc[mask, "exception_reason"] = "DELISTING"

        elif adjustment_type == "EXTRA_VISIBILITY":
            adjusted.loc[mask, "forecast_qty"] += adjustment_qty
            adjusted.loc[mask, "forecast_driver_secondary"] = "EXTRA_VISIBILITY"

        elif adjustment_type == "PROMOTION":
            uplift_qty = adjusted.loc[mask, "forecast_qty"] * (adjustment_qty / 100.0)
            adjusted.loc[mask, "forecast_qty"] += uplift_qty
            adjusted.loc[mask, "forecast_trade_spend"] *= 1.15

        elif adjustment_type == "BOGO":
            uplift_qty = adjusted.loc[mask, "forecast_qty"] * (adjustment_qty / 100.0)
            adjusted.loc[mask, "forecast_qty"] += uplift_qty
            adjusted.loc[mask, "forecast_trade_spend"] *= 1.25

        elif adjustment_type == "PRICE_CHANGE":
            adjusted.loc[mask, "forecast_qty"] *= (1 + adjustment_qty / 100.0)

        elif adjustment_type == "DISTRIBUTOR_CHANGE":
            adjusted.loc[mask, "exception_flag"] = True
            adjusted.loc[mask, "exception_reason"] = "DISTRIBUTOR_CHANGE"

        elif adjustment_type == "EVENT_SALES":
            adjusted.loc[mask, "forecast_qty"] += adjustment_qty

        elif adjustment_type == "BULK_ORDER":
            adjusted.loc[mask, "forecast_qty"] += adjustment_qty

        adjusted.loc[mask, "adjustment_applied"] = True
        adjusted.loc[mask, "adjustment_reason"] = adjustment_reason

        return adjusted

    def compute_scenario_variance(
        self,
        expected_df: pd.DataFrame,
        best_case_df: pd.DataFrame,
        worst_case_df: pd.DataFrame
    ) -> pd.DataFrame:
        """Compute variance analysis across scenarios."""
        variance = pd.DataFrame({
            "chain": expected_df["chain"],
            "brand": expected_df["brand"],
            "article": expected_df["article"],
            "ean": expected_df["ean"],
            "expected_qty": expected_df["forecast_qty"],
            "best_case_qty": best_case_df["forecast_qty"],
            "worst_case_qty": worst_case_df["forecast_qty"],
        })

        variance["upside_variance_pct"] = (
            (variance["best_case_qty"] - variance["expected_qty"]) /
            variance["expected_qty"].replace(0, 1) * 100
        )
        variance["downside_variance_pct"] = (
            (variance["worst_case_qty"] - variance["expected_qty"]) /
            variance["expected_qty"].replace(0, 1) * 100
        )

        variance["variance_range_qty"] = (
            variance["best_case_qty"] - variance["worst_case_qty"]
        )

        variance["risk_band"] = variance["variance_range_qty"].apply(
            lambda x: "LOW" if x < expected_df["forecast_qty"].std() else "HIGH"
        )

        return variance
