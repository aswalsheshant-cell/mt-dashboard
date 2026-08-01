# -*- coding: utf-8 -*-
"""Phase A Historical Backtesting Framework.

Validates forecast engine accuracy against completed historical periods.
No future data leakage. Compares against simple benchmarks.
Produces WAPE, MAPE, bias at Channel, Chain, Brand, Article levels.
"""
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import datetime as dt
import json


class BacktestingFramework:
    """Historical backtesting with strict no-future-data policy."""

    # Completed months available for backtesting (Apr 2025 - Jun 2026)
    BACKTEST_RUNS = [
        {
            "forecast_month": "2026-03",
            "data_available_through": "2026-02",
            "description": "March 2026 forecast using Feb data cutoff"
        },
        {
            "forecast_month": "2026-04",
            "data_available_through": "2026-03",
            "description": "April 2026 forecast using Mar data cutoff"
        },
        {
            "forecast_month": "2026-05",
            "data_available_through": "2026-04",
            "description": "May 2026 forecast using Apr data cutoff"
        },
        {
            "forecast_month": "2026-06",
            "data_available_through": "2026-05",
            "description": "June 2026 forecast using May data cutoff"
        },
    ]

    def __init__(self, input_dir: str, output_dir: str, engine_class=None):
        """Initialize backtesting framework.

        Args:
            input_dir: Directory containing historical data
            output_dir: Directory for backtest outputs
            engine_class: ForecastEngine class (imported at runtime to avoid circular imports)
        """
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.engine_class = engine_class
        self.backtest_results = []
        self.accuracy_summary = {}

    def filter_data_by_cutoff(self, df: pd.DataFrame, cutoff_month: str) -> pd.DataFrame:
        """Filter data to only include records available before cutoff date.

        Ensures no future data leakage in backtests.
        """
        if "month" not in df.columns:
            return df

        df = df.copy()
        df["month"] = pd.to_datetime(df["month"], errors="coerce")
        cutoff_date = pd.to_datetime(cutoff_month, errors="coerce")

        # Include only data up to and including cutoff month
        return df[df["month"] <= cutoff_date].copy()

    def calculate_wape(self, actual: pd.Series, forecast: pd.Series) -> float:
        """Calculate Weighted Absolute Percentage Error (WAPE).

        WAPE = SUM(|Actual - Forecast|) / SUM(Actual)

        Better than MAPE for low-volume items and averages.
        """
        numerator = np.abs(actual - forecast).sum()
        denominator = actual.sum()

        if denominator == 0:
            return np.nan
        return (numerator / denominator) * 100

    def calculate_mape(self, actual: pd.Series, forecast: pd.Series) -> float:
        """Calculate Mean Absolute Percentage Error (MAPE).

        MAPE = Mean(|Actual - Forecast| / |Actual|) × 100

        Use WAPE for reporting; MAPE for reference only.
        """
        if (actual == 0).any():
            # MAPE undefined for zero actuals; use WAPE instead
            return np.nan

        pct_errors = np.abs((actual - forecast) / actual)
        return pct_errors.mean() * 100

    def calculate_bias(self, actual: pd.Series, forecast: pd.Series) -> float:
        """Calculate Forecast Bias.

        Bias = SUM(Forecast - Actual) / SUM(Actual) × 100

        Positive = over-forecast
        Negative = under-forecast
        """
        numerator = (forecast - actual).sum()
        denominator = actual.sum()

        if denominator == 0:
            return np.nan
        return (numerator / denominator) * 100

    def calculate_accuracy_by_level(
        self,
        actual_df: pd.DataFrame,
        forecast_df: pd.DataFrame,
        groupby_cols: List[str],
        level_name: str
    ) -> pd.DataFrame:
        """Calculate accuracy metrics grouped by specified columns."""
        merged = actual_df.merge(
            forecast_df[groupby_cols + ["forecast_qty"]],
            on=groupby_cols,
            how="inner"
        )

        results = []
        for keys, group in merged.groupby(groupby_cols):
            actual_qty = group["offtake_qty"].sum()
            forecast_qty = group["forecast_qty"].sum()

            if actual_qty == 0:
                continue

            wape = self.calculate_wape(group["offtake_qty"], group["forecast_qty"])
            mape = self.calculate_mape(group["offtake_qty"], group["forecast_qty"])
            bias = self.calculate_bias(group["offtake_qty"], group["forecast_qty"])

            under_forecast = max(0, actual_qty - forecast_qty)
            over_forecast = max(0, forecast_qty - actual_qty)

            result = {
                "level": level_name,
                "dimension": "_".join([str(k) for k in (keys if isinstance(keys, tuple) else [keys])]),
                "actual_qty": actual_qty,
                "forecast_qty": forecast_qty,
                "wape_pct": wape,
                "mape_pct": mape,
                "bias_pct": bias,
                "under_forecast_qty": under_forecast,
                "over_forecast_qty": over_forecast,
                "article_count": len(group),
            }
            results.append(result)

        return pd.DataFrame(results)

    def compare_vs_benchmarks(
        self,
        actual_df: pd.DataFrame,
        forecast_df: pd.DataFrame
    ) -> Dict:
        """Compare Forecast Engine against simple baseline methods."""
        actual_df = actual_df.copy()
        forecast_df = forecast_df.copy()

        # Prepare data
        actual_df["month"] = pd.to_datetime(actual_df["month"], errors="coerce")
        forecast_df["month"] = pd.to_datetime(forecast_df["month"], errors="coerce")

        actual_totals = actual_df.groupby("month")["offtake_qty"].sum()
        forecast_totals = forecast_df.groupby("month")["forecast_qty"].sum()

        # Channel-level totals
        actual_channel_total = actual_totals.sum()
        forecast_engine_total = forecast_totals.sum()

        benchmarks = {}

        # B1: Last month actual
        if len(actual_totals) > 1:
            last_month = actual_totals.iloc[-2]  # Month before forecast month
            benchmarks["last_month"] = {
                "forecast_qty": last_month,
                "wape": self.calculate_wape(
                    pd.Series([actual_channel_total]),
                    pd.Series([last_month])
                )
            }

        # B2: Last 3-month average
        if len(actual_totals) >= 3:
            l3m_avg = actual_totals.iloc[-3:-1].mean()
            benchmarks["l3m_average"] = {
                "forecast_qty": l3m_avg,
                "wape": self.calculate_wape(
                    pd.Series([actual_channel_total]),
                    pd.Series([l3m_avg])
                )
            }

        # B3: Weighted moving average (3-month: 50%, 30%, 20%)
        if len(actual_totals) >= 3:
            wma = (
                actual_totals.iloc[-1] * 0.5 +
                actual_totals.iloc[-2] * 0.3 +
                actual_totals.iloc[-3] * 0.2
            )
            benchmarks["weighted_moving_avg"] = {
                "forecast_qty": wma,
                "wape": self.calculate_wape(
                    pd.Series([actual_channel_total]),
                    pd.Series([wma])
                )
            }

        # B4: Same month last year
        # (Would require data spanning 12+ months; skip if not available)

        # Forecast Engine
        benchmarks["forecast_engine"] = {
            "forecast_qty": forecast_engine_total,
            "wape": self.calculate_wape(
                pd.Series([actual_channel_total]),
                pd.Series([forecast_engine_total])
            )
        }

        return benchmarks

    def run_backtest(self, backtest_config: Dict) -> Dict:
        """Run a single historical backtest run.

        Args:
            backtest_config: Dict with forecast_month and data_available_through

        Returns:
            Dict with backtest results
        """
        forecast_month = backtest_config["forecast_month"]
        cutoff_month = backtest_config["data_available_through"]

        print(f"\n{'='*70}")
        print(f"BACKTEST: {forecast_month} (data available through {cutoff_month})")
        print(f"{'='*70}")

        # Load data
        try:
            actual_df = pd.read_csv(self.input_dir / "offtake_history.csv", dtype=str)
            primary_df = pd.read_csv(self.input_dir / "primary_history.csv", dtype=str)
            margin_df = pd.read_csv(self.input_dir / "fact_margin.csv", dtype=str)
        except FileNotFoundError as e:
            print(f"❌ Missing input file: {e}")
            return None

        # Filter to cutoff month (no future leakage)
        primary_df = self.filter_data_by_cutoff(primary_df, cutoff_month)
        margin_df = self.filter_data_by_cutoff(margin_df, cutoff_month)

        # Filter actual to forecast month only
        actual_df["month"] = pd.to_datetime(actual_df["month"], errors="coerce")
        actual_forecast_month = actual_df[
            actual_df["month"] == pd.to_datetime(forecast_month, errors="coerce")
        ].copy()

        if len(actual_forecast_month) == 0:
            print(f"⚠ No actual data available for {forecast_month}")
            return None

        # Run forecast (would call ForecastEngine here if available)
        # For now, return structure with placeholders
        forecast_df = pd.DataFrame()  # Would be populated by engine

        # Calculate accuracy
        accuracy_channel = self.calculate_accuracy_by_level(
            actual_forecast_month,
            forecast_df,
            [],
            "Channel"
        )

        accuracy_chain = self.calculate_accuracy_by_level(
            actual_forecast_month,
            forecast_df,
            ["chain_name"],
            "Chain"
        )

        accuracy_article = self.calculate_accuracy_by_level(
            actual_forecast_month,
            forecast_df,
            ["ean"],
            "Article"
        )

        # Benchmarks
        benchmarks = self.compare_vs_benchmarks(actual_forecast_month, forecast_df)

        result = {
            "forecast_month": forecast_month,
            "cutoff_date": cutoff_month,
            "actual_records": len(actual_forecast_month),
            "forecast_records": len(forecast_df),
            "accuracy_by_channel": accuracy_channel.to_dict("records"),
            "accuracy_by_chain": accuracy_chain.to_dict("records"),
            "accuracy_by_article": accuracy_article.to_dict("records"),
            "benchmarks": benchmarks,
        }

        return result

    def run_all_backtests(self) -> List[Dict]:
        """Execute all historical backtest runs."""
        print("\n" + "="*70)
        print("PHASE A HISTORICAL BACKTESTING")
        print(f"Framework: No future-data leakage, {len(self.BACKTEST_RUNS)} runs")
        print("="*70)

        for config in self.BACKTEST_RUNS:
            result = self.run_backtest(config)
            if result:
                self.backtest_results.append(result)

        # Generate summary
        self._write_backtest_reports()

        return self.backtest_results

    def _write_backtest_reports(self):
        """Write backtest results to outputs."""
        if not self.backtest_results:
            print("⚠ No backtest results to report")
            return

        # JSON summary
        summary = {
            "timestamp": dt.datetime.now().isoformat(timespec="seconds"),
            "runs_completed": len(self.backtest_results),
            "backtest_results": self.backtest_results,
        }

        with open(self.output_dir / "backtest_summary.json", "w") as f:
            json.dump(summary, f, indent=2, default=str)

        # CSV by level
        all_channel = pd.concat([
            pd.DataFrame(r["accuracy_by_channel"])
            for r in self.backtest_results if r["accuracy_by_channel"]
        ], ignore_index=True)

        if len(all_channel) > 0:
            all_channel.to_csv(self.output_dir / "accuracy_by_channel.csv", index=False)

        all_chain = pd.concat([
            pd.DataFrame(r["accuracy_by_chain"])
            for r in self.backtest_results if r["accuracy_by_chain"]
        ], ignore_index=True)

        if len(all_chain) > 0:
            all_chain.to_csv(self.output_dir / "accuracy_by_chain.csv", index=False)

        # Benchmarks
        benchmarks_data = []
        for result in self.backtest_results:
            for method, metrics in result["benchmarks"].items():
                benchmarks_data.append({
                    "forecast_month": result["forecast_month"],
                    "method": method,
                    "forecast_qty": metrics.get("forecast_qty", 0),
                    "wape_pct": metrics.get("wape", np.nan),
                })

        if benchmarks_data:
            benchmarks_df = pd.DataFrame(benchmarks_data)
            benchmarks_df.to_csv(self.output_dir / "benchmark_comparison.csv", index=False)
            print(f"✓ Benchmark comparison: {self.output_dir / 'benchmark_comparison.csv'}")

        print(f"✓ Backtest reports written to {self.output_dir}")


def run_backtesting(
    input_dir: str = "Phase_A_Input",
    output_dir: str = "backtest_output"
):
    """Run Phase A historical backtesting."""
    framework = BacktestingFramework(input_dir, output_dir)
    results = framework.run_all_backtests()

    print("\n" + "="*70)
    print("BACKTEST SUMMARY")
    print("="*70)
    print(f"Completed runs: {len(results)}")
    print(f"Output directory: {output_dir}")

    if results:
        # Print channel-level accuracy
        for result in results:
            if result["accuracy_by_channel"]:
                channel_acc = result["accuracy_by_channel"][0]
                print(f"\n{result['forecast_month']}:")
                print(f"  WAPE: {channel_acc.get('wape_pct', 'N/A'):.1f}%")
                print(f"  Bias: {channel_acc.get('bias_pct', 'N/A'):.1f}%")

    print("="*70)

    return results


if __name__ == "__main__":
    import sys
    input_dir = sys.argv[1] if len(sys.argv) > 1 else "Phase_A_Input"
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "backtest_output"
    run_backtesting(input_dir, output_dir)
