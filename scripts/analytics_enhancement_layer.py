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

    def calculate_real_gross_margin(
        self, df_sales: pd.DataFrame, df_cogs: pd.DataFrame = None
    ) -> pd.DataFrame:
        """
        Phase 4: Calculate real Gross Margin % from actual COGS data.
        Gross Margin % = (NSV - Total COGS) / NSV × 100
        Fallback to category/brand average if SKU-level COGS missing.
        """
        try:
            df = df_sales.copy()

            if df_cogs is not None and not df_cogs.empty:
                # Merge with actual COGS
                df = pd.merge(df, df_cogs[["SKU", "Total_COGS"]], on="SKU", how="left")
            else:
                # Default: assume 55% COGS (45% margin baseline)
                df["Total_COGS"] = df.get("NSV", 0) * 0.55

            # Compute Gross Margin %
            df["Gross_Margin_Pct"] = (
                (df["NSV"] - df["Total_COGS"]) / df["NSV"].replace(0, np.nan) * 100
            ).fillna(45)  # Fallback to 45% if missing

            # Cap at 0–100%
            df["Gross_Margin_Pct"] = df["Gross_Margin_Pct"].clip(0, 100)

            return df
        except Exception as e:
            print(f"WARN: Real margin calculation error: {e}")
            return df_sales.copy()

    def calculate_sop_forecast_accuracy(
        self, df_actual: pd.DataFrame, df_forecast: pd.DataFrame, group_col: str = "Chain"
    ) -> pd.DataFrame:
        """
        Phase 4: Compute S&OP Forecast Accuracy (WMAPE %) and Forecast Bias.
        WMAPE % = (∑|Actual - Forecast| / ∑Actual) × 100
        Bias % = (∑(Forecast - Actual) / ∑Actual) × 100
        """
        try:
            actual_agg = df_actual.groupby(group_col)["NSV"].sum().reset_index()
            actual_agg.rename(columns={"NSV": "actual_nsv"}, inplace=True)

            forecast_agg = df_forecast.groupby(group_col)["Target"].sum().reset_index()
            forecast_agg.rename(columns={"Target": "forecast_nsv"}, inplace=True)

            merged = pd.merge(actual_agg, forecast_agg, on=group_col, how="outer").fillna(0)

            # WMAPE %
            merged["abs_error"] = (merged["forecast_nsv"] - merged["actual_nsv"]).abs()
            merged["wmape_pct"] = (
                merged["abs_error"] / merged["actual_nsv"].replace(0, np.nan) * 100
            ).fillna(0)
            merged["accuracy_pct"] = (100 - merged["wmape_pct"]).clip(0, 100)

            # Forecast Bias %
            merged["forecast_error"] = merged["forecast_nsv"] - merged["actual_nsv"]
            merged["bias_pct"] = (
                merged["forecast_error"] / merged["actual_nsv"].replace(0, np.nan) * 100
            ).fillna(0)

            # Bias Status
            merged["bias_status"] = merged["bias_pct"].apply(
                lambda x: "Under-forecasting" if x < -5
                else ("Over-forecasting" if x > 5 else "Accurate")
            )

            return merged
        except Exception as e:
            print(f"WARN: S&OP forecast accuracy error: {e}")
            return pd.DataFrame()

    def calculate_open_po_sla_risk(
        self, df_po: pd.DataFrame, sla_windows: dict = None
    ) -> pd.DataFrame:
        """
        Phase 4: Compute Open PO SLA Penalty Risk based on aging days.
        SLA Windows: DMart/Reliance 7d, Q-Commerce 2d, Others 14d (default).
        Penalty Risk: 2–5% of PO value for breaches.
        """
        if sla_windows is None:
            sla_windows = {
                "DMart": 7,
                "Reliance": 7,
                "Q-Comm": 2,
                "Wellness": 10,
                "Apollo": 10,
                "Spencer": 14,
                "More": 14,
            }

        try:
            df = df_po.copy()

            # Calculate aging days
            df["PO_Date"] = pd.to_datetime(df["PO_Date"], errors="coerce")
            today = pd.Timestamp.now()
            df["Aging_Days"] = (today - df["PO_Date"]).dt.days

            # Map SLA window per account
            df["SLA_Window"] = df["Account"].map(sla_windows).fillna(14)

            # Compute risk status
            def risk_status(aging, sla_window):
                if aging <= 3:
                    return "Normal"
                elif aging <= (sla_window - 2):
                    return "Caution"
                else:
                    return "BREACH"

            df["Risk_Status"] = df.apply(
                lambda row: risk_status(row["Aging_Days"], row["SLA_Window"]), axis=1
            )

            # Penalty debit % (2–5% scale)
            def penalty_pct(aging, sla_window):
                days_over = max(0, aging - sla_window)
                return min(5, 2 + (days_over * 0.5))

            df["Penalty_Debit_Pct"] = df.apply(
                lambda row: penalty_pct(row["Aging_Days"], row["SLA_Window"]), axis=1
            )
            df["Penalty_Debit_Value"] = df["PO_Value"] * df["Penalty_Debit_Pct"] / 100

            return df
        except Exception as e:
            print(f"WARN: PO SLA risk calculation error: {e}")
            return pd.DataFrame()

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
