# -*- coding: utf-8 -*-
"""CLI for forecast engine."""
import os
import json
import argparse
import datetime as dt
import pandas as pd

from forecast_engine.forecast_engine import ForecastEngine
from forecast_engine.scenario_planner import ScenarioPlanner
from forecast_engine.powerbi_export import (
    export_forecast_tables, export_measures_file, build_executive_summary
)
from forecast_engine.india_workbook_format import (
    apply_india_format_to_workbook, print_acceptance_report
)


def run_forecast_pipeline(
    margin_repo_path: str,
    primary_data_path: str,
    offtake_data_path: str,
    output_dir: str,
    forecast_months: int = 3,
    verbose: bool = True,
    events_calendar_path: str = None,
    launch_plan_path: str = None,
    tentative_mode: bool = False,
) -> dict:
    """End-to-end forecast pipeline.

    Set tentative_mode=True to run with relaxed approval gates and fallback
    hierarchies for targets, events, and margins.  All tentative outputs carry
    is_tentative=True and traceability fields (value_source, fallback_method,
    confidence_level).  Use the final run (tentative_mode=False) for reporting.
    """
    import pandas as pd

    os.makedirs(output_dir, exist_ok=True)
    log = _stepper(verbose)
    mode_label = "TENTATIVE" if tentative_mode else "FINAL"
    summary = {
        "started_at": dt.datetime.now().isoformat(timespec="seconds"),
        "forecast_mode": mode_label,
        "margin_repo_path": margin_repo_path,
        "output_dir": output_dir,
    }

    log(1, "Initialize forecast engine")
    engine = ForecastEngine(margin_repo_path, verbose=verbose)

    log(2, "Load margin repository data")
    margin_data = engine.load_margin_repository()
    summary["margin_rows"] = len(margin_data)

    log(3, "Load historical demand (Primary & Offtake)")
    primary_df, offtake_df = engine.load_historical_demand(
        primary_data_path, offtake_data_path, months_back=12
    )
    summary["primary_rows"] = len(primary_df)
    summary["offtake_rows"] = len(offtake_df)

    log(4, "Build article catalog from margin data")
    article_catalog = []
    for _, row in margin_data.iterrows():
        article = {
            "ean": row.get("ean"),
            "article": row.get("article"),
            "brand": row.get("brand"),
            "category": row.get("category"),
            "chain_name": row.get("chain_name", row.get("chain", "")),
            "zone": row.get("zone", ""),
            "state": row.get("state", ""),
        }
        article_catalog.append(article)

    summary["articles_in_catalog"] = len(article_catalog)

    log(5, f"Run base forecast ({forecast_months} months) — mode: {mode_label}")
    forecast_df = engine.run_forecast(
        margin_data, primary_df, offtake_df, article_catalog,
        num_forecast_months=forecast_months, verbose=verbose,
        events_calendar_path=events_calendar_path,
        launch_plan_path=launch_plan_path,
        tentative_mode=tentative_mode,
    )
    summary["forecast_rows"] = len(forecast_df)

    log(6, "Generate scenarios (Best/Expected/Worst)")
    scenario_planner = ScenarioPlanner()
    scenarios = scenario_planner.generate_scenarios(forecast_df)
    scenario_summary = scenario_planner.build_scenario_summary(scenarios)
    summary["scenario_summary"] = scenario_summary.to_dict("records")

    log(7, "Identify exceptions and anomalies")
    exception_rows = forecast_df[forecast_df["exception_flag"] == True].copy()
    summary["exception_count"] = len(exception_rows)

    log(8, "Export to Power BI")
    # Write CSVs directly into output_dir (caller already set it to .../PowerBI/)
    pbi_paths = export_forecast_tables(forecast_df, scenarios, exception_rows, output_dir, fmt="csv")
    summary["powerbi_tables"] = {k: os.path.basename(v) for k, v in pbi_paths.items()}

    measures_path = export_measures_file(output_dir)
    summary["powerbi_measures"] = os.path.basename(measures_path)

    log(9, "Build executive summary")
    exec_summary = build_executive_summary(forecast_df, scenarios, exception_rows)
    summary["executive_summary"] = exec_summary

    log(10, "Generate planning workbook (Excel) — India-standard formatting")
    workbook_path = os.path.join(output_dir, "Forecast_Planning_Workbook.xlsx")
    _build_planning_workbook(forecast_df, scenarios, workbook_path)

    # Apply India-standard formatting, Executive Control Panel, and reconciliation
    # validation in one idempotent pass (safe to re-run on an existing workbook).
    india_report = apply_india_format_to_workbook(
        workbook_path,
        forecast_df,
        scenarios,
        exception_rows,
        recon_csv_path=pbi_paths.get("fact_reconciliation_summary"),
        source_version=os.path.basename(margin_repo_path),
    )
    summary["planning_workbook"]   = os.path.basename(workbook_path)
    summary["india_format_report"] = india_report

    log(11, "Generate forecast report")
    report_path = os.path.join(output_dir, "Forecast_Report.md")
    _build_forecast_report(forecast_df, scenarios, exec_summary, report_path)
    summary["forecast_report"] = os.path.basename(report_path)

    summary["finished_at"] = dt.datetime.now().isoformat(timespec="seconds")

    summary_path = os.path.join(output_dir, "Forecast_Summary.json")
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2, default=str)

    if verbose:
        print("\n" + "=" * 68)
        print(" FORECAST PIPELINE COMPLETE [%s] — %s" % (mode_label, summary["finished_at"]))
        print("=" * 68)
        print("  Mode:        %s" % mode_label)
        print("  Output dir:  %s" % output_dir)
        print("  Summary:     %s" % summary_path)
        print("  Workbook:    %s" % workbook_path)
        print("  Report:      %s" % report_path)
        print_acceptance_report(india_report)
        if tentative_mode:
            print()
            print("  ⚠  TENTATIVE OUTPUTS — labeled is_tentative=True.")
            print("     Not for final reporting. Resolve all approvals, then re-run in FINAL mode.")

    return summary


def _stepper(verbose):
    def log(n, msg):
        if verbose:
            print("[%2d/11] %s" % (n, msg))
    return log


def _build_planning_workbook(forecast_df, scenarios, output_path):
    """Build Excel planning workbook with multiple sheets."""
    with pd.ExcelWriter(output_path, engine="xlsxwriter") as writer:
        forecast_df.to_excel(writer, sheet_name="Forecast", index=False)

        for scenario_name, scenario_df in scenarios.items():
            scenario_df.to_excel(writer, sheet_name=scenario_name.title(), index=False)

        exception_rows = forecast_df[forecast_df["exception_flag"] == True]
        exception_rows.to_excel(writer, sheet_name="Exceptions", index=False)


def _build_forecast_report(forecast_df, scenarios, exec_summary, output_path):
    """Build markdown forecast report."""
    date = dt.date.today().strftime("%d %b %Y")
    report = f"""# Demand Forecast Report — {date}

## Executive Summary

- **Forecast Rows**: {exec_summary.get('forecast_rows', 0)}
- **Articles**: {exec_summary.get('articles', 0)}
- **Chains**: {exec_summary.get('chains', 0)}
- **Forecast Months**: {exec_summary.get('forecast_months', 0)}

### Key Metrics

- **Total Forecast Qty**: {exec_summary.get('total_forecast_qty', 0):,.0f} units
- **Total Forecast NSV**: ₹{exec_summary.get('total_forecast_nsv', 0):,.0f}
- **Total Trade Spend**: ₹{exec_summary.get('total_forecast_trade_spend', 0):,.0f}
- **Total CM2**: ₹{exec_summary.get('total_forecast_cm2', 0):,.0f}
- **Avg Confidence**: {exec_summary.get('avg_confidence_pct', 0):.1f}%

### Risk Summary

- **Articles at Risk (HIGH_RISK/BLOCKED)**: {exec_summary.get('articles_at_risk', 0)}
- **Exception Count**: {exec_summary.get('exception_count', 0)}

## Scenario Comparison

"""

    seen_scenarios = set()
    for key in exec_summary:
        if key.startswith("scenario_") and key.endswith("_qty"):
            scenario_name = key[len("scenario_"):-len("_qty")]
            if scenario_name in seen_scenarios:
                continue
            seen_scenarios.add(scenario_name)
            clean_name = scenario_name.replace("_", " ").title()
            qty = exec_summary.get(f"scenario_{scenario_name}_qty", 0)
            nsv = exec_summary.get(f"scenario_{scenario_name}_nsv", 0)
            cm2 = exec_summary.get(f"scenario_{scenario_name}_cm2", 0)
            report += f"\n### {clean_name}\n"
            report += f"- **Qty**: {qty:,.0f} units\n"
            report += f"- **NSV**: ₹{nsv:,.0f}\n"
            report += f"- **CM2**: ₹{cm2:,.0f}\n"

    report += f"""

## Data Quality

- **Avg Confidence %**: {exec_summary.get('avg_confidence_pct', 0):.1f}%
- **High Risk Count**: {exec_summary.get('articles_at_risk', 0)}
- **Exception Count**: {exec_summary.get('exception_count', 0)}

## Top Growth Drivers

"""
    for driver in exec_summary.get('top_growth_drivers', [])[:5]:
        report += f"- {driver.get('article', 'Unknown')}: {driver.get('yoy_trend_pct', 0):.1f}% YoY\n"

    report += f"""

_Forecast generated {date}. See Forecast_Summary.json for full details._
"""

    with open(output_path, "w") as f:
        f.write(report)


def main():
    parser = argparse.ArgumentParser(description="Forecast Engine CLI")
    parser.add_argument("--margin-repo", required=True, help="Path to margin repository root")
    parser.add_argument("--primary-data", required=True, help="Path to primary sales data")
    parser.add_argument("--offtake-data", required=True, help="Path to offtake sales data")
    parser.add_argument("--out", required=True, help="Output directory")
    parser.add_argument("--months", type=int, default=3, help="Number of forecast months")
    parser.add_argument("--verbose", action="store_true", default=True)
    parser.add_argument("--events-calendar", default=None,
                        help="Path to events_calendar.csv (APPROVED uplifts applied; "
                             "in tentative mode, Proposed_base_pct used as fallback)")
    parser.add_argument("--launch-plan", default=None,
                        help="Path to launch_plan.csv (APPROVED NPI rows only affect forecast)")
    parser.add_argument(
        "--mode",
        choices=["final", "tentative"],
        default="final",
        help=("tentative = planning mode (relaxed gates, fallback hierarchies, "
              "is_tentative=True on outputs); final = strict production mode (default)"),
    )

    args = parser.parse_args()

    summary = run_forecast_pipeline(
        margin_repo_path=args.margin_repo,
        primary_data_path=args.primary_data,
        offtake_data_path=args.offtake_data,
        output_dir=args.out,
        forecast_months=args.months,
        verbose=args.verbose,
        events_calendar_path=args.events_calendar,
        launch_plan_path=args.launch_plan,
        tentative_mode=(args.mode == "tentative"),
    )

    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
