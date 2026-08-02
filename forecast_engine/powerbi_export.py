# -*- coding: utf-8 -*-
"""Export forecast data for Power BI."""
import pandas as pd
import os
from typing import Dict, Tuple
import datetime as dt


def export_forecast_tables(
    forecast_df: pd.DataFrame,
    scenario_dfs: Dict[str, pd.DataFrame],
    exception_df: pd.DataFrame,
    output_dir: str,
    fmt: str = "csv"
) -> Dict[str, str]:
    """Export clean forecast tables for Power BI."""
    os.makedirs(output_dir, exist_ok=True)
    paths = {}

    keep_cols_forecast = [
        "forecast_id", "chain_name", "zone", "state", "brand", "category", "article", "ean",
        "forecast_month", "forecast_fy",
        "historical_offtake_qty", "historical_primary_qty",
        "mom_trend_pct", "yoy_trend_pct", "weighted_ma_qty",
        "seasonality_factor", "festival_uplift", "npi_uplift",
        "forecast_qty", "forecast_nsv", "forecast_primary_qty", "forecast_offtake_qty",
        "forecast_trade_spend", "forecast_cm2",
        "warehouse_gurgaon", "warehouse_mumbai", "warehouse_bangalore", "warehouse_kolkata",
        "confidence_pct", "risk_level",
        "forecast_driver_primary", "forecast_driver_secondary",
        "exception_flag", "exception_reason", "version",
        # Tentative mode traceability fields — present when --mode tentative
        "is_tentative", "value_source", "fallback_method", "confidence_level", "uplift_value_source",
    ]

    forecast_clean = forecast_df[[c for c in keep_cols_forecast if c in forecast_df.columns]]

    forecast_path = os.path.join(output_dir, f"fact_demand_forecast.{fmt}")
    if fmt == "csv":
        forecast_clean.to_csv(forecast_path, index=False)
    elif fmt == "xlsx":
        forecast_clean.to_excel(forecast_path, sheet_name="Forecast", index=False)
    paths["fact_demand_forecast"] = forecast_path

    for scenario_name, scenario_df in scenario_dfs.items():
        keep_cols_scenario = [
            "chain_name", "zone", "state", "brand", "category", "article", "ean",
            "forecast_month", "forecast_qty", "forecast_nsv",
            "forecast_primary_qty", "forecast_trade_spend", "forecast_cm2",
            "confidence_pct", "scenario", "scenario_description"
        ]

        scenario_clean = scenario_df[[c for c in keep_cols_scenario if c in scenario_df.columns]]
        scenario_path = os.path.join(output_dir, f"fact_demand_{scenario_name}.{fmt}")

        if fmt == "csv":
            scenario_clean.to_csv(scenario_path, index=False)
        elif fmt == "xlsx":
            scenario_clean.to_excel(scenario_path, sheet_name=scenario_name.title(), index=False)

        paths[f"fact_demand_{scenario_name}"] = scenario_path

    if not exception_df.empty:
        exception_cols = [
            "chain_name", "brand", "article", "ean",
            "exception_type", "exception_reason", "risk_level", "recommendation"
        ]

        exception_clean = exception_df[[c for c in exception_cols if c in exception_df.columns]]
        exception_path = os.path.join(output_dir, f"fact_exceptions.{fmt}")

        if fmt == "csv":
            exception_clean.to_csv(exception_path, index=False)
        elif fmt == "xlsx":
            exception_clean.to_excel(exception_path, sheet_name="Exceptions", index=False)

        paths["fact_exceptions"] = exception_path

    dim_article = forecast_df[["ean", "brand", "category", "article"]].drop_duplicates()
    dim_article_path = os.path.join(output_dir, f"dim_article.{fmt}")
    if fmt == "csv":
        dim_article.to_csv(dim_article_path, index=False)
    elif fmt == "xlsx":
        dim_article.to_excel(dim_article_path, sheet_name="Article", index=False)
    paths["dim_article"] = dim_article_path

    dim_chain = forecast_df[["chain_name", "zone", "state"]].drop_duplicates()
    dim_chain_path = os.path.join(output_dir, f"dim_chain.{fmt}")
    if fmt == "csv":
        dim_chain.to_csv(dim_chain_path, index=False)
    elif fmt == "xlsx":
        dim_chain.to_excel(dim_chain_path, sheet_name="Chain", index=False)
    paths["dim_chain"] = dim_chain_path

    dim_date = forecast_df[["forecast_month", "forecast_fy"]].drop_duplicates().sort_values("forecast_month")
    dim_date_path = os.path.join(output_dir, f"dim_date.{fmt}")
    if fmt == "csv":
        dim_date.to_csv(dim_date_path, index=False)
    elif fmt == "xlsx":
        dim_date.to_excel(dim_date_path, sheet_name="Date", index=False)
    paths["dim_date"] = dim_date_path

    return paths


def build_pbi_measures() -> str:
    """Generate DAX measures for Power BI."""
    measures_dax = """
// Forecast Measures
Forecast Total Qty = SUM(fact_demand_forecast[forecast_qty])
Forecast Total NSV = SUM(fact_demand_forecast[forecast_nsv])
Forecast Total Primary = SUM(fact_demand_forecast[forecast_primary_qty])
Forecast Total Offtake = SUM(fact_demand_forecast[forecast_offtake_qty])
Forecast Avg Confidence = AVERAGE(fact_demand_forecast[confidence_pct])

// Dispatch Allocation
Dispatch Gurgaon = SUM(fact_demand_forecast[warehouse_gurgaon])
Dispatch Mumbai = SUM(fact_demand_forecast[warehouse_mumbai])
Dispatch Bangalore = SUM(fact_demand_forecast[warehouse_bangalore])
Dispatch Kolkata = SUM(fact_demand_forecast[warehouse_kolkata])

// Risk Metrics
High Risk Count = COUNTIF(fact_demand_forecast[risk_level], "HIGH_RISK") + COUNTIF(fact_demand_forecast[risk_level], "BLOCKED")
Exception Count = COUNTIF(fact_demand_forecast[exception_flag], TRUE)
Low Confidence Count = COUNTIF(fact_demand_forecast[confidence_pct], "<60")

// Trend Drivers
Avg YoY Trend = AVERAGE(fact_demand_forecast[yoy_trend_pct])
Avg MoM Trend = AVERAGE(fact_demand_forecast[mom_trend_pct])
Avg Seasonality = AVERAGE(fact_demand_forecast[seasonality_factor])

// Trade Spend
Forecast Trade Spend = SUM(fact_demand_forecast[forecast_trade_spend])
Forecast CM2 = SUM(fact_demand_forecast[forecast_cm2])
Trade Spend per Unit = DIVIDE(CALCULATE(SUM(fact_demand_forecast[forecast_trade_spend])), SUM(fact_demand_forecast[forecast_qty]), 0)
"""
    return measures_dax.strip()


def export_measures_file(output_dir: str) -> str:
    """Write DAX measures to file for copy-paste into Power BI."""
    measures_path = os.path.join(output_dir, "MEASURES.dax")
    with open(measures_path, "w") as f:
        f.write(build_pbi_measures())
    return measures_path


def build_executive_summary(
    forecast_df: pd.DataFrame,
    scenarios: Dict[str, pd.DataFrame],
    exception_df: pd.DataFrame
) -> Dict:
    """Build executive summary metrics."""
    summary = {
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "forecast_rows": len(forecast_df),
        "forecast_months": forecast_df["forecast_month"].nunique(),
        "articles": forecast_df["ean"].nunique(),
        "chains": forecast_df["chain_name"].nunique(),
        "brands": forecast_df["brand"].nunique(),

        "total_forecast_qty": float(forecast_df["forecast_qty"].sum()),
        "total_forecast_nsv": float(forecast_df["forecast_nsv"].sum()),
        "total_forecast_primary": float(forecast_df["forecast_primary_qty"].sum()),
        "total_forecast_offtake": float(forecast_df["forecast_offtake_qty"].sum()),
        "total_forecast_trade_spend": float(forecast_df["forecast_trade_spend"].sum()),
        "total_forecast_cm2": float(forecast_df["forecast_cm2"].sum()),

        "avg_confidence_pct": float(forecast_df["confidence_pct"].mean()),
        "articles_at_risk": int((forecast_df["risk_level"].isin(["HIGH_RISK", "BLOCKED"])).sum()),
        "exception_count": int(forecast_df["exception_flag"].sum()),

        "top_growth_drivers": forecast_df.nlargest(5, "yoy_trend_pct")[["article", "yoy_trend_pct"]].to_dict("records"),
    }

    for scenario_name, scenario_df in scenarios.items():
        summary[f"scenario_{scenario_name}_qty"] = float(scenario_df["forecast_qty"].sum())
        summary[f"scenario_{scenario_name}_nsv"] = float(scenario_df["forecast_nsv"].sum())
        summary[f"scenario_{scenario_name}_cm2"] = float(scenario_df["forecast_cm2"].sum())

    return summary
