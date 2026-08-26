#!/usr/bin/env python3
"""
Non-destructive sidecar analytics enrichment for FMCG / Modern Trade dashboards.
Computes PVM decomposition, channel health ratios, SKU quadrants without mutating base data.
"""
import json
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Any


class FMCGAnalyticsEnhancer:
    """
    Enrichment engine: Price-Volume-Mix, inventory health, SKU portfolio classification.
    All outputs → enriched_metrics.json (sidecar), never modifies source data.js.
    """

    def __init__(self, target_service_level: float = 0.95):
        self.z_score = 1.65 if target_service_level == 0.95 else 2.33
        self.enriched_output = {}

    def calculate_pvm_decomposition(
        self, df_current: pd.DataFrame, df_prior: pd.DataFrame, group_col: str = "Chain"
    ) -> pd.DataFrame:
        """
        Price-Volume-Mix variance between current and prior period.
        Returns DataFrame with volume_effect, price_effect, mix_effect columns.
        """
        try:
            curr = (
                df_current.groupby(group_col)
                .agg(volume_act=("Units", "sum"), revenue_act=("NSV", "sum"))
                .reset_index()
            )
            prior = (
                df_prior.groupby(group_col)
                .agg(volume_prior=("Units", "sum"), revenue_prior=("NSV", "sum"))
                .reset_index()
            )
            merged = pd.merge(curr, prior, on=group_col, how="outer").fillna(0)

            # Compute average prices
            merged["price_act"] = merged["revenue_act"] / merged["volume_act"].replace(
                0, np.nan
            )
            merged["price_prior"] = merged["revenue_prior"] / merged["volume_prior"].replace(
                0, np.nan
            )
            merged["price_act"] = merged["price_act"].fillna(0)
            merged["price_prior"] = merged["price_prior"].fillna(0)

            # PVM Effects
            merged["volume_effect"] = (
                merged["volume_act"] - merged["volume_prior"]
            ) * merged["price_prior"]
            merged["price_effect"] = (
                merged["price_act"] - merged["price_prior"]
            ) * merged["volume_prior"]
            merged["mix_effect"] = (
                merged["revenue_act"]
                - merged["revenue_prior"]
                - merged["volume_effect"]
                - merged["price_effect"]
            )
            merged["total_delta_nsv"] = merged["revenue_act"] - merged["revenue_prior"]
            merged["pct_change_nsv"] = (
                merged["total_delta_nsv"] / merged["revenue_prior"].replace(0, np.nan) * 100
            ).fillna(0)

            return merged
        except Exception as e:
            print(f"WARN: PVM decomposition error: {e}")
            return pd.DataFrame()

    def calculate_channel_health_ratio(
        self, df_offtake: pd.DataFrame, df_primary: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Offtake-to-Primary Health Ratio by Account.
        Ratio > 1.15: Understocked (OSA risk).
        Ratio < 0.85: Overstocked (return/freeze risk).
        0.85–1.15: Healthy balance.
        """
        try:
            offtake_agg = (
                df_offtake.groupby("Chain")["Offtake"].sum().reset_index()
                .rename(columns={"Chain": "Account", "Offtake": "offtake_total"})
            )
            primary_agg = (
                df_primary.groupby("Chain")["NSV"].sum().reset_index()
                .rename(columns={"Chain": "Account", "NSV": "primary_total"})
            )
            merged = pd.merge(offtake_agg, primary_agg, on="Account", how="outer").fillna(0)
            merged["health_ratio"] = merged["offtake_total"] / merged["primary_total"].replace(
                0, np.nan
            )
            merged["health_ratio"] = merged["health_ratio"].fillna(0)
            merged["health_status"] = merged["health_ratio"].apply(
                lambda x: "Understocked"
                if x > 1.15
                else ("Overstocked" if x < 0.85 else "Balanced")
            )
            return merged
        except Exception as e:
            print(f"WARN: Channel health calculation error: {e}")
            return pd.DataFrame()

    def classify_sku_quadrants(
        self, df_sales: pd.DataFrame, ros_col: str = "Rate_of_Sale", margin_col: str = "Gross_Margin_Pct"
    ) -> pd.DataFrame:
        """
        Classify SKUs into 4 strategic quadrants based on Rate-of-Sale (ROS) vs. Gross Margin %.
        Q1: Core Driver (High ROS, High Margin) → protect 100% OSA
        Q2: Traffic Builder (High ROS, Low Margin) → optimize promo spend
        Q3: Margin Booster (Low ROS, High Margin) → secondary displays
        Q4: Delist Review (Low ROS, Low Margin) → rationalization candidate
        """
        try:
            df = df_sales.copy()
            ros_median = df[ros_col].median()
            margin_median = df[margin_col].median()

            conditions = [
                (df[ros_col] >= ros_median) & (df[margin_col] >= margin_median),
                (df[ros_col] >= ros_median) & (df[margin_col] < margin_median),
                (df[ros_col] < ros_median) & (df[margin_col] >= margin_median),
                (df[ros_col] < ros_median) & (df[margin_col] < margin_median),
            ]
            quadrants = [
                "Q1_Core_Driver",
                "Q2_Traffic_Builder",
                "Q3_Margin_Booster",
                "Q4_Delist_Review",
            ]
            df["sku_strategic_quadrant"] = np.select(
                conditions, quadrants, default="Unclassified"
            )
            return df
        except Exception as e:
            print(f"WARN: SKU quadrant classification error: {e}")
            return pd.DataFrame()

    def generate_executive_insights(
        self, df_pvm: pd.DataFrame, df_health: pd.DataFrame
    ) -> List[str]:
        """
        Rule-based executive summary insights.
        """
        insights = []
        try:
            # PVM Insights
            if not df_pvm.empty:
                price_negative = df_pvm[df_pvm["price_effect"] < 0]
                if len(price_negative) > 0:
                    insights.append(
                        f"📊 Price compression across {len(price_negative)} accounts; "
                        f"offset by volume growth in {len(df_pvm[df_pvm['volume_effect'] > 0])} accounts."
                    )

            # Channel Health Insights
            if not df_health.empty:
                overstocked = df_health[df_health["health_status"] == "Overstocked"]
                understocked = df_health[df_health["health_status"] == "Understocked"]
                if len(overstocked) > 0:
                    accounts = ", ".join(overstocked["Account"].head(2).tolist())
                    insights.append(
                        f"⚠️ Inventory risk: {len(overstocked)} accounts overstocked "
                        f"(DOI >45 days risk). Examples: {accounts}."
                    )
                if len(understocked) > 0:
                    accounts = ", ".join(understocked["Account"].head(2).tolist())
                    insights.append(
                        f"📈 OSA risk: {len(understocked)} accounts understocked. "
                        f"Replenishment needed for: {accounts}."
                    )
        except Exception as e:
            print(f"WARN: Insight generation error: {e}")

        return insights or ["No anomalies detected."]

    def to_json(self) -> Dict[str, Any]:
        """
        Export enriched metrics as JSON-serializable dict.
        All NaN, None, and inf values replaced with null.
        """
        output = self.enriched_output.copy()

        def sanitize_value(v):
            if v is None or (isinstance(v, float) and (np.isnan(v) or np.isinf(v))):
                return None
            if isinstance(v, (np.integer, np.floating)):
                return float(v)
            if isinstance(v, pd.Timestamp):
                return v.isoformat()
            return v

        def sanitize_dict(d):
            if isinstance(d, dict):
                return {k: sanitize_dict(v) for k, v in d.items()}
            if isinstance(d, (list, tuple)):
                return [sanitize_dict(item) for item in d]
            return sanitize_value(d)

        return sanitize_dict(output)

    def export_to_file(self, output_path: str = "dashboard/enriched_metrics.json"):
        """
        Write enriched metrics to sidecar JSON file.
        """
        try:
            with open(output_path, "w") as f:
                json.dump(self.to_json(), f, indent=2)
            print(f"✓ Enriched metrics exported to {output_path}")
        except Exception as e:
            print(f"ERROR: Failed to export enriched metrics: {e}")
            raise
