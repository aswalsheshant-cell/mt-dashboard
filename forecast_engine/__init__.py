# -*- coding: utf-8 -*-
"""Forecast Engine — Production-grade demand planning for Modern Trade.

Modules:
- forecast_schema: Data model and validation
- forecast_drivers: Trend computation and forecast factors
- forecast_engine: Core forecasting logic
- scenario_planner: Scenario generation and business adjustments
- powerbi_export: Power BI dataset export
- cli: Command-line interface

Usage:
    python -m forecast_engine.cli --margin-repo <path> --primary-data <path> --offtake-data <path> --out <dir>
"""

__version__ = "1.0.0"
__author__ = "Modern Trade Analytics"

__all__ = [
    "ForecastEngine",
    "ScenarioPlanner",
    "validate_forecast_frame",
]
