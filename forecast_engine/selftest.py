# -*- coding: utf-8 -*-
"""Self-test suite for forecast engine."""
import unittest
import pandas as pd
import numpy as np
import datetime as dt
from io import StringIO

from forecast_schema import (
    validate_forecast_frame, compute_fy_from_date, get_forecast_months,
    FORECAST_HIERARCHY
)
from forecast_drivers import (
    compute_mom_trend, compute_yoy_trend, compute_weighted_moving_average,
    compute_seasonality_factor, apply_festival_uplift, apply_npi_uplift,
    compute_confidence_interval, score_forecast_driver
)
from scenario_planner import ScenarioPlanner


class TestForecastSchema(unittest.TestCase):
    """Test data model and validation."""

    def test_fy_computation(self):
        """Test Indian fiscal year calculation."""
        self.assertEqual(compute_fy_from_date(dt.date(2026, 4, 1)), "FY27")
        self.assertEqual(compute_fy_from_date(dt.date(2026, 3, 31)), "FY26")
        self.assertEqual(compute_fy_from_date(dt.date(2025, 12, 15)), "FY26")

    def test_forecast_months(self):
        """Test forecast month generation."""
        months = get_forecast_months(num_months=3, start_date=dt.date(2026, 1, 15))
        self.assertEqual(len(months), 3)
        self.assertEqual(months[0], (2026, 1))
        self.assertEqual(months[1], (2026, 2))
        self.assertEqual(months[2], (2026, 3))

    def test_forecast_months_wraparound(self):
        """Test forecast month generation across year boundary."""
        months = get_forecast_months(num_months=3, start_date=dt.date(2026, 11, 15))
        self.assertEqual(len(months), 3)
        self.assertEqual(months[0], (2026, 11))
        self.assertEqual(months[1], (2026, 12))
        self.assertEqual(months[2], (2027, 1))

    def test_forecast_frame_validation(self):
        """Test forecast frame validation."""
        df = pd.DataFrame({
            "chain": ["A", "B"],
            "brand": ["X", "Y"],
            "article": ["SKU1", "SKU2"],
            "ean": ["123", "456"],
            "forecast_month": ["2026-01", "2026-01"],
            "forecast_qty": [100, 200],
            "confidence_pct": [85, 90],
            "risk_level": ["NORMAL", "WARNING"]
        })
        ok, errors = validate_forecast_frame(df)
        self.assertTrue(ok)
        self.assertEqual(len(errors), 0)

    def test_forecast_frame_invalid_confidence(self):
        """Test validation catches invalid confidence pct."""
        df = pd.DataFrame({
            "chain": ["A"],
            "brand": ["X"],
            "article": ["SKU1"],
            "ean": ["123"],
            "forecast_month": ["2026-01"],
            "forecast_qty": [100],
            "confidence_pct": [150],
            "risk_level": ["NORMAL"]
        })
        ok, errors = validate_forecast_frame(df)
        self.assertFalse(ok)
        self.assertGreater(len(errors), 0)


class TestForecastDrivers(unittest.TestCase):
    """Test forecast driver computation."""

    def setUp(self):
        """Create sample historical data."""
        self.historical = pd.DataFrame({
            "date": pd.date_range("2025-01-01", periods=12, freq="MS"),
            "quantity": [100, 105, 110, 115, 120, 125, 130, 135, 140, 145, 150, 155],
            "primary_qty": [200, 210, 220, 230, 240, 250, 260, 270, 280, 290, 300, 310]
        })

    def test_mom_trend_positive(self):
        """Test positive MoM trend computation."""
        trend = compute_mom_trend(self.historical, "SKU1", months_back=3)
        self.assertGreater(trend, 0)

    def test_yoy_trend_positive(self):
        """Test YoY trend computation."""
        trend = compute_yoy_trend(self.historical, "SKU1")
        self.assertGreater(trend, 0)

    def test_weighted_moving_average(self):
        """Test weighted moving average."""
        wma = compute_weighted_moving_average(self.historical)
        self.assertGreater(wma, 0)
        self.assertLess(wma, self.historical["quantity"].max() * 2)

    def test_seasonality_factor(self):
        """Test seasonality factor computation."""
        seasonal = compute_seasonality_factor(self.historical, target_month=6)
        self.assertGreater(seasonal, 0)

    def test_festival_uplift(self):
        """Test festival uplift application."""
        base_qty = 100
        uplifted, pct = apply_festival_uplift(base_qty, festival_name="Diwali")
        self.assertGreater(uplifted, base_qty)
        self.assertGreater(pct, 0)

    def test_npi_uplift(self):
        """Test NPI uplift for new products."""
        base_qty = 100
        uplifted, penetration = apply_npi_uplift(base_qty, days_since_launch=30)
        self.assertGreater(uplifted, base_qty)
        self.assertGreater(penetration, 0)
        self.assertLess(penetration, 100)

    def test_confidence_interval(self):
        """Test confidence interval computation."""
        conf_pct, lower, upper = compute_confidence_interval(100, historical_std=10)
        self.assertGreater(conf_pct, 0)
        self.assertLess(conf_pct, 100)
        self.assertLess(lower, upper)


class TestScenarioPlanner(unittest.TestCase):
    """Test scenario planning."""

    def setUp(self):
        """Create sample forecast."""
        self.forecast = pd.DataFrame({
            "chain": ["A", "A", "B"],
            "brand": ["X", "X", "Y"],
            "article": ["SKU1", "SKU2", "SKU3"],
            "ean": ["111", "222", "333"],
            "forecast_month": ["2026-01", "2026-01", "2026-01"],
            "forecast_qty": [100, 200, 150],
            "forecast_nsv": [1000, 2000, 1500],
            "forecast_primary_qty": [300, 400, 350],
            "forecast_offtake_qty": [100, 200, 150],
            "forecast_trade_spend": [100, 200, 150],
            "forecast_cm2": [50, 100, 75],
            "confidence_pct": [85, 90, 80],
            "risk_level": ["NORMAL", "WARNING", "NORMAL"],
            "exception_flag": [False, False, True]
        })

    def test_scenario_generation(self):
        """Test scenario generation."""
        planner = ScenarioPlanner()
        scenarios = planner.generate_scenarios(self.forecast)

        self.assertIn("expected", scenarios)
        self.assertIn("best_case", scenarios)
        self.assertIn("worst_case", scenarios)

        best = scenarios["best_case"]["forecast_qty"].sum()
        expected = scenarios["expected"]["forecast_qty"].sum()
        worst = scenarios["worst_case"]["forecast_qty"].sum()

        self.assertGreater(best, expected)
        self.assertGreater(expected, worst)

    def test_scenario_summary(self):
        """Test scenario summary generation."""
        planner = ScenarioPlanner()
        scenarios = planner.generate_scenarios(self.forecast)
        summary = planner.build_scenario_summary(scenarios)

        self.assertEqual(len(summary), 3)
        self.assertIn("expected", summary["scenario"].values)

    def test_business_adjustment_listing(self):
        """Test NEW_LISTING adjustment."""
        planner = ScenarioPlanner()
        adjustment = {
            "chain": "A",
            "brand": "X",
            "article": "SKU1",
            "ean": "111",
            "adjustment_type": "NEW_LISTING",
            "adjustment_qty": 50,
            "adjustment_reason": "Test listing"
        }
        adjusted = planner.apply_business_adjustment(self.forecast, adjustment)
        original_qty = self.forecast[self.forecast["ean"] == "111"]["forecast_qty"].iloc[0]
        adjusted_qty = adjusted[adjusted["ean"] == "111"]["forecast_qty"].iloc[0]
        self.assertEqual(adjusted_qty, original_qty + 50)

    def test_business_adjustment_promotion(self):
        """Test PROMOTION adjustment."""
        planner = ScenarioPlanner()
        adjustment = {
            "chain": "A",
            "brand": "X",
            "article": "SKU2",
            "ean": "222",
            "adjustment_type": "PROMOTION",
            "adjustment_qty": 10,
            "adjustment_reason": "Festive promotion"
        }
        adjusted = planner.apply_business_adjustment(self.forecast, adjustment)
        adjusted_qty = adjusted[adjusted["ean"] == "222"]["forecast_qty"].iloc[0]
        self.assertGreater(adjusted_qty, 200)


def run_tests(verbose=True):
    """Run all tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestForecastSchema))
    suite.addTests(loader.loadTestsFromTestCase(TestForecastDrivers))
    suite.addTests(loader.loadTestsFromTestCase(TestScenarioPlanner))

    runner = unittest.TextTestRunner(verbosity=2 if verbose else 1)
    result = runner.run(suite)

    return result.wasSuccessful(), len(result.failures) + len(result.errors)


if __name__ == "__main__":
    success, error_count = run_tests()
    exit(0 if success else 1)
