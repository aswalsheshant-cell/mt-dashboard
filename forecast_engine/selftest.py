# -*- coding: utf-8 -*-
"""Self-test suite for forecast engine."""
import unittest
import pandas as pd
import numpy as np
import datetime as dt
from io import StringIO

from forecast_engine.forecast_schema import (
    validate_forecast_frame, compute_fy_from_date, get_forecast_months,
    FORECAST_HIERARCHY
)
from forecast_engine.forecast_drivers import (
    compute_mom_trend, compute_yoy_trend, compute_weighted_moving_average,
    compute_seasonality_factor, apply_festival_uplift, apply_npi_uplift,
    compute_confidence_interval, score_forecast_driver
)
from forecast_engine.forecast_engine import ForecastEngine, UNIT_NSV_CEILING
from forecast_engine.scenario_planner import ScenarioPlanner
from forecast_engine.data_normalizer import DataNormalizer


class TestForecastSchema(unittest.TestCase):
    """Test data model and validation."""

    def test_fy_computation(self):
        """Test Indian fiscal year calculation."""
        self.assertEqual(compute_fy_from_date(dt.date(2026, 4, 1)), "FY27")
        self.assertEqual(compute_fy_from_date(dt.date(2026, 3, 31)), "FY26")
        self.assertEqual(compute_fy_from_date(dt.date(2025, 12, 15)), "FY26")

    def test_forecast_months(self):
        """Test forecast month generation with explicit start_date and no offset."""
        months = get_forecast_months(num_months=3, start_date=dt.date(2026, 1, 15), start_month_offset=0)
        self.assertEqual(len(months), 3)
        self.assertEqual(months[0], (2026, 1))
        self.assertEqual(months[1], (2026, 2))
        self.assertEqual(months[2], (2026, 3))

    def test_forecast_months_wraparound(self):
        """Test forecast month generation across year boundary with no offset."""
        months = get_forecast_months(num_months=3, start_date=dt.date(2026, 11, 15), start_month_offset=0)
        self.assertEqual(len(months), 3)
        self.assertEqual(months[0], (2026, 11))
        self.assertEqual(months[1], (2026, 12))
        self.assertEqual(months[2], (2027, 1))

    def test_forecast_frame_validation(self):
        """Test forecast frame validation."""
        df = pd.DataFrame({
            "chain_name": ["A", "B"],
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
            "chain_name": ["A"],
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
            "chain_name": ["A", "A", "B"],
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
            "chain_name": "A",
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
            "chain_name": "A",
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


class TestDataNormalizer(unittest.TestCase):
    """Test data schema normalization."""

    def test_normalize_uppercase_columns(self):
        """Test normalization of uppercase column names."""
        df = pd.DataFrame({
            "EAN": ["123", "456"],
            "Brand": ["X", "Y"],
        })
        normalized = DataNormalizer.normalize(df, source_type="margin")
        self.assertIn("ean", normalized.columns)
        self.assertIn("brand", normalized.columns)

    def test_normalize_mixed_case_columns(self):
        """Test normalization of mixed-case column names."""
        df = pd.DataFrame({
            "Chain Name": ["A", "B"],
            "Article": ["SKU1", "SKU2"],
            "Offtake_Qty": ["100", "200"],
        })
        normalized = DataNormalizer.normalize(df, source_type="offtake")
        self.assertIn("chain_name", normalized.columns)
        self.assertIn("article", normalized.columns)
        self.assertIn("offtake_qty", normalized.columns)

    def test_normalize_numeric_columns(self):
        """Test conversion of numeric columns."""
        df = pd.DataFrame({
            "ean": ["123"],
            "mrp": ["500"],
            "quantity": ["1000"],
        })
        normalized = DataNormalizer.normalize(df, source_type="margin")
        self.assertEqual(normalized["mrp"].dtype, "float64")
        self.assertEqual(normalized["quantity"].dtype, "float64")

    def test_validate_normalized(self):
        """Test validation of normalized data."""
        df = pd.DataFrame({
            "ean": ["123"],
            "chain_name": ["A"],
        })
        is_valid, missing = DataNormalizer.validate_normalized(df, {"ean", "chain_name"})
        self.assertTrue(is_valid)
        self.assertEqual(len(missing), 0)


class TestForecastHorizon(unittest.TestCase):
    """Verify forecast months never include the current month."""

    def test_offset_advances_start(self):
        """offset=1 yields months starting one month after start_date."""
        months = get_forecast_months(num_months=3, start_date=dt.date(2026, 8, 2), start_month_offset=1)
        self.assertEqual(months[0], (2026, 9))
        self.assertEqual(months[1], (2026, 10))
        self.assertEqual(months[2], (2026, 11))

    def test_current_month_absent(self):
        """With offset=1 the current calendar month must not appear."""
        today = dt.date.today()
        months = get_forecast_months(num_months=3, start_month_offset=1)
        self.assertNotIn((today.year, today.month), months)

    def test_offset_year_boundary(self):
        """offset=1 wraps correctly across December → January."""
        months = get_forecast_months(num_months=2, start_date=dt.date(2026, 12, 1), start_month_offset=1)
        self.assertEqual(months[0], (2027, 1))
        self.assertEqual(months[1], (2027, 2))

    def test_zero_offset_backward_compat(self):
        """offset=0 (legacy default) starts from start_date unchanged."""
        months = get_forecast_months(num_months=1, start_date=dt.date(2026, 8, 2), start_month_offset=0)
        self.assertEqual(months[0], (2026, 8))


class TestNSVFormula(unittest.TestCase):
    """Verify the authoritative NSV = MRP / ((1+GST/100) × (1+TOT/100)) formula."""

    def _make_engine(self):
        return ForecastEngine(margin_repo_path=".", verbose=False)

    def _make_margin(self, mrp, gst_pct, tot_pct, cm2_pct, quality_status="DERIVED",
                     mrp_denomination="CONSUMER_UNIT_MRP", unit_nsv_validated=None,
                     unit_nsv_source="", cm2_value_type="", cm2_value_per_unit=None,
                     cm2_pct_rate=None):
        return pd.DataFrame([{
            "chain_name": "TEST_CHAIN", "ean": "TEST_EAN", "mrp": mrp,
            "gst_pct": gst_pct, "tot_pct": tot_pct, "cm2_pct": cm2_pct,
            "quality_status": quality_status, "margin_pct": tot_pct,
            "mrp_denomination": mrp_denomination,
            "unit_nsv_validated": unit_nsv_validated,
            "unit_nsv_source": unit_nsv_source,
            "cm2_value_type": cm2_value_type,
            "cm2_value_per_unit": cm2_value_per_unit,
            "cm2_pct_rate": cm2_pct_rate,
            "cm2_approval_status": "",
        }])

    def test_nsv_formula_per_unit(self):
        """ARAMBAGH-like CONSUMER_UNIT_MRP row: NSV = 449 / (1.18 × 1.3644) ≈ 278.88."""
        engine = self._make_engine()
        margin = self._make_margin(mrp=449.0, gst_pct=18.0, tot_pct=36.44, cm2_pct=53.88,
                                   mrp_denomination="CONSUMER_UNIT_MRP")
        forecast = {"forecast_qty": 10, "ean": "TEST_EAN", "chain_name": "TEST_CHAIN"}
        result = engine.compute_nsv_and_trade_spend(forecast, margin, tentative_mode=True)
        expected_unit_nsv = 449.0 / (1.18 * 1.3644)
        self.assertAlmostEqual(result["forecast_nsv"] / 10, expected_unit_nsv, places=1)
        # Status must reflect a validated/formula NSV was successfully computed
        self.assertTrue(
            result["unit_price_status"].startswith("VALIDATED_NSV:"),
            f"Expected VALIDATED_NSV:... status, got: {result['unit_price_status']}"
        )

    def test_implausible_aggregate_chain(self):
        """Dmart-like AGGREGATE_DENOMINATION row: NSV and CM2 zeroed; qty retained."""
        engine = self._make_engine()
        margin = self._make_margin(mrp=7184.0, gst_pct=18.0, tot_pct=49.15, cm2_pct=862.08,
                                   mrp_denomination="AGGREGATE_DENOMINATION")
        forecast = {"forecast_qty": 5, "ean": "TEST_EAN", "chain_name": "TEST_CHAIN"}
        result = engine.compute_nsv_and_trade_spend(forecast, margin, tentative_mode=True)
        self.assertEqual(result["forecast_nsv"], 0.0)
        self.assertEqual(result["forecast_cm2"], 0.0)
        self.assertEqual(result["unit_price_status"], "NO_UNIT_NSV_AGGREGATE_DENOMINATION")
        # Quantity must be retained for operational planning
        self.assertGreater(result.get("forecast_primary_qty", 0), 0)

    def test_nsv_positive_for_per_unit_chain(self):
        """Valid CONSUMER_UNIT_MRP row must produce forecast_nsv > 0."""
        engine = self._make_engine()
        margin = self._make_margin(mrp=349.0, gst_pct=18.0, tot_pct=36.44, cm2_pct=41.88,
                                   mrp_denomination="CONSUMER_UNIT_MRP")
        forecast = {"forecast_qty": 100, "ean": "TEST_EAN", "chain_name": "TEST_CHAIN"}
        result = engine.compute_nsv_and_trade_spend(forecast, margin, tentative_mode=True)
        self.assertGreater(result["forecast_nsv"], 0.0)

    def test_pack_case_level_mrp_zeroes_nsv(self):
        """PACK_CASE_LEVEL_MRP row: NSV=0, CM2=0, forecast_qty retained."""
        engine = self._make_engine()
        margin = self._make_margin(mrp=1200.0, gst_pct=18.0, tot_pct=28.0, cm2_pct=144.0,
                                   mrp_denomination="PACK_CASE_LEVEL_MRP")
        forecast = {"forecast_qty": 50, "ean": "TEST_EAN", "chain_name": "TEST_CHAIN"}
        result = engine.compute_nsv_and_trade_spend(forecast, margin, tentative_mode=True)
        self.assertEqual(result["forecast_nsv"], 0.0)
        self.assertEqual(result["forecast_cm2"], 0.0)
        self.assertEqual(result["unit_price_status"], "NO_UNIT_NSV_PACK_CASE_LEVEL_MRP")
        self.assertEqual(result["operational_inclusion_flag"], True)

    def test_consumer_unit_mrp_with_validated_nsv_uses_primary(self):
        """CONSUMER_UNIT_MRP row with unit_nsv_validated uses primary history NSV, not formula."""
        engine = self._make_engine()
        validated_nsv = 163.0  # from primary invoices
        margin = self._make_margin(mrp=449.0, gst_pct=18.0, tot_pct=36.44, cm2_pct=53.88,
                                   mrp_denomination="CONSUMER_UNIT_MRP",
                                   unit_nsv_validated=validated_nsv,
                                   unit_nsv_source="PRIMARY_INVOICE_MEDIAN")
        forecast = {"forecast_qty": 10, "ean": "TEST_EAN", "chain_name": "TEST_CHAIN"}
        result = engine.compute_nsv_and_trade_spend(forecast, margin, tentative_mode=True)
        self.assertAlmostEqual(result["forecast_nsv"], 10 * validated_nsv, places=1)
        self.assertIn("PRIMARY_INVOICE_MEDIAN", result["unit_price_status"])

    def test_estimated_row_cm2_rate_based(self):
        """ESTIMATED row: cm2_pct = 15.0 means 15% of NSV, not ₹ per unit."""
        engine = self._make_engine()
        margin = self._make_margin(mrp=250.0, gst_pct=18.0, tot_pct=30.0, cm2_pct=15.0,
                                   quality_status="ESTIMATED")
        forecast = {"forecast_qty": 100, "ean": "TEST_EAN", "chain_name": "TEST_CHAIN"}
        result = engine.compute_nsv_and_trade_spend(forecast, margin, tentative_mode=True)
        unit_nsv = 250.0 / (1.18 * 1.30)
        expected_cm2 = 100 * unit_nsv * 0.15
        self.assertAlmostEqual(result["forecast_cm2"], expected_cm2, places=1)


class TestCM2Nonzero(unittest.TestCase):
    """Confirm CM2 is non-zero and correctly computed for operational DERIVED rows."""

    def _make_engine(self):
        return ForecastEngine(margin_repo_path=".", verbose=False)

    def test_derived_cm2_nonzero(self):
        """DERIVED row: CM2 = forecast_qty × cm2_pct (₹ per unit), never 0."""
        engine = self._make_engine()
        margin = pd.DataFrame([{
            "chain_name": "Apollo", "ean": "EAN1", "mrp": 408.0,
            "gst_pct": 18.0, "tot_pct": 36.44, "cm2_pct": 48.96,
            "quality_status": "DERIVED", "margin_pct": 36.44,
        }])
        forecast = {"forecast_qty": 200, "ean": "EAN1", "chain_name": "Apollo"}
        result = engine.compute_nsv_and_trade_spend(forecast, margin, tentative_mode=True)
        self.assertGreater(result["forecast_cm2"], 0.0)
        self.assertAlmostEqual(result["forecast_cm2"], 200 * 48.96, places=1)

    def test_cm2_label_provisional_in_tentative_mode(self):
        """All rows in tentative mode must carry PROVISIONAL label."""
        engine = self._make_engine()
        margin = pd.DataFrame([{
            "chain_name": "Apollo", "ean": "EAN1", "mrp": 408.0,
            "gst_pct": 18.0, "tot_pct": 36.44, "cm2_pct": 48.96,
            "quality_status": "DERIVED", "margin_pct": 36.44,
        }])
        forecast = {"forecast_qty": 50, "ean": "EAN1", "chain_name": "Apollo"}
        result = engine.compute_nsv_and_trade_spend(forecast, margin, tentative_mode=True)
        self.assertEqual(result["cm2_label"], "PROVISIONAL_CM2_NOT_FINANCE_APPROVED")


class TestVMMControl(unittest.TestCase):
    """VMM rows must be excluded from operational totals."""

    def _make_engine(self):
        return ForecastEngine(margin_repo_path=".", verbose=False)

    def _make_any_margin(self):
        return pd.DataFrame([{
            "chain_name": "Apollo", "ean": "EAN1", "mrp": 408.0,
            "gst_pct": 18.0, "tot_pct": 36.44, "cm2_pct": 48.96,
            "quality_status": "DERIVED", "margin_pct": 36.44,
        }])

    def test_vmm_operational_flag_false(self):
        """VMM rows must have operational_inclusion_flag=False."""
        engine = self._make_engine()
        forecast = {"forecast_qty": 500, "ean": "VMM_EAN", "chain_name": "VMM"}
        result = engine.compute_nsv_and_trade_spend(
            forecast, self._make_any_margin(), tentative_mode=True
        )
        self.assertFalse(result["operational_inclusion_flag"])

    def test_vmm_forecast_qty_zeroed(self):
        """VMM rows must have forecast_qty=0 to prevent entering operational totals."""
        engine = self._make_engine()
        forecast = {"forecast_qty": 500, "ean": "VMM_EAN", "chain_name": "VMM"}
        result = engine.compute_nsv_and_trade_spend(
            forecast, self._make_any_margin(), tentative_mode=True
        )
        self.assertEqual(result["forecast_qty"], 0.0)

    def test_vmm_gross_qty_preserved(self):
        """VMM gross_forecast_qty must equal the original pre-exclusion quantity."""
        engine = self._make_engine()
        original_qty = 500.0
        forecast = {"forecast_qty": original_qty, "ean": "VMM_EAN", "chain_name": "VMM"}
        result = engine.compute_nsv_and_trade_spend(
            forecast, self._make_any_margin(), tentative_mode=True
        )
        self.assertEqual(result["gross_forecast_qty"], original_qty)

    def test_vmm_nsv_and_cm2_zero(self):
        """VMM excluded rows must have forecast_nsv=0 and forecast_cm2=0."""
        engine = self._make_engine()
        forecast = {"forecast_qty": 500, "ean": "VMM_EAN", "chain_name": "VMM"}
        result = engine.compute_nsv_and_trade_spend(
            forecast, self._make_any_margin(), tentative_mode=True
        )
        self.assertEqual(result["forecast_nsv"], 0.0)
        self.assertEqual(result["forecast_cm2"], 0.0)


def run_tests(verbose=True):
    """Run all tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestForecastSchema))
    suite.addTests(loader.loadTestsFromTestCase(TestForecastDrivers))
    suite.addTests(loader.loadTestsFromTestCase(TestScenarioPlanner))
    suite.addTests(loader.loadTestsFromTestCase(TestDataNormalizer))
    suite.addTests(loader.loadTestsFromTestCase(TestForecastHorizon))
    suite.addTests(loader.loadTestsFromTestCase(TestNSVFormula))
    suite.addTests(loader.loadTestsFromTestCase(TestCM2Nonzero))
    suite.addTests(loader.loadTestsFromTestCase(TestVMMControl))

    runner = unittest.TextTestRunner(verbosity=2 if verbose else 1)
    result = runner.run(suite)

    return result.wasSuccessful(), len(result.failures) + len(result.errors)


if __name__ == "__main__":
    success, error_count = run_tests()
    exit(0 if success else 1)
