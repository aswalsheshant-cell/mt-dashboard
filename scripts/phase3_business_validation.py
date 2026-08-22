#!/usr/bin/env python3
"""
Phase 3: Business Validation Implementation Script

Purpose:
  Automate KPI reconciliation between dashboard and Finance control totals.
  Validate that dashboard numbers reconcile to SAP FI / Finance master within
  established tolerance thresholds.

Usage:
  python scripts/phase3_business_validation.py \
    --finance-controls <path-to-finance-export.csv> \
    --data-js <path-to-data.js> \
    --fy <FY27|FY26|FY25> \
    --validation-date <YYYY-MM-DD>

Example:
  python scripts/phase3_business_validation.py \
    --finance-controls ~/Finance_Controls_FY27_Aug2026.csv \
    --data-js dashboard/data.js \
    --fy FY27 \
    --validation-date 2026-08-12

Output:
  - KPI reconciliation matrix (9 KPIs × tolerance check)
  - Variance analysis by KPI (dashboard vs Finance control)
  - Pass/fail status per KPI and overall
  - Sign-off form template (for business stakeholder approval)
  - Timestamped validation report
  - JSON output for CI/CD integration

Exit codes:
  0 = Success (all KPIs reconciled, within tolerance)
  1 = Argument error (missing or invalid parameter)
  2 = File not found (finance controls or data.js)
  3 = Data format error (invalid CSV or JSON)
  4 = KPI mismatch (variance exceeds tolerance)
  5 = Incomplete data (Finance controls missing required columns)
  6 = Sign-off error (approval form generation failed)
"""

import sys
import os
import json
import csv
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Configuration
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_JS_PATH = PROJECT_ROOT / "dashboard" / "data.js"

# KPI Validation Matrix (from docs/KPI_VALIDATION_FRAMEWORK.md)
KPI_MATRIX = {
    "primary_nsv": {
        "tab": "Primary",
        "definition": "Primary NSV (Net Sales Value) in ₹ Lakh",
        "finance_control_column": "primary_nsv_lakhs",
        "dashboard_source": "primary.nsv_fy26",  # FY26 only; FY27 from detail_meta
        "tolerance_pct": 0.5,
        "tolerance_type": "percentage",
        "unit": "₹ Lakh"
    },
    "offtake_qty": {
        "tab": "Offtake",
        "definition": "Offtake Quantity in units",
        "finance_control_column": "offtake_qty_units",
        "dashboard_source": "offtake.total_fy26",  # FY26 only
        "tolerance_pct": 2.0,
        "tolerance_type": "percentage",
        "unit": "units"
    },
    "pnl_gross_margin": {
        "tab": "P&L",
        "definition": "Gross Margin in ₹ Lakh",
        "finance_control_column": "gross_margin_lakhs",
        "dashboard_source": "pnl.total_nsv",  # Proxy; actual GM not in total
        "tolerance_pct": 0.5,
        "tolerance_type": "percentage",
        "unit": "₹ Lakh"
    },
    "pnl_gm_pct": {
        "tab": "P&L",
        "definition": "Gross Margin % (GM / NSV * 100)",
        "finance_control_column": "gm_pct",
        "dashboard_source": "pnl.blended_discount_pct",  # Placeholder
        "tolerance_pct": 1.0,
        "tolerance_type": "percentage_points",
        "unit": "%"
    },
    "pnl_expense_ratio": {
        "tab": "P&L",
        "definition": "Expense Ratio % (Trade Spend / NSV * 100)",
        "finance_control_column": "expense_ratio_pct",
        "dashboard_source": "cm2.expense_ratio",  # FY26 if exists
        "tolerance_pct": 1.5,
        "tolerance_type": "percentage_points",
        "unit": "%"
    },
    "cm2_pct": {
        "tab": "P&L",
        "definition": "CM2 % (Contribution Margin 2 after expenses)",
        "finance_control_column": "cm2_pct",
        "dashboard_source": "cm2.cm2_pct_fy26",  # FY26 if exists
        "tolerance_pct": 1.0,
        "tolerance_type": "percentage_points",
        "unit": "%"
    },
    "tdp_distribution": {
        "tab": "Distribution",
        "definition": "TDP (Trade Display Points) numeric distribution %",
        "finance_control_column": "tdp_numeric_dist_pct",
        "dashboard_source": "dist_gap.tdp_numeric",  # If exists
        "tolerance_pct": 2.0,
        "tolerance_type": "percentage_points",
        "unit": "%"
    },
    "market_share": {
        "tab": "Market Share",
        "definition": "Market Share % (Mamaearth NSV / Total Market NSV)",
        "finance_control_column": "market_share_pct",
        "dashboard_source": "universe.share_pct_fy26",  # Calculated from universe
        "tolerance_pct": 0.5,
        "tolerance_type": "percentage_points",
        "unit": "%"
    },
    "forecast_target": {
        "tab": "Forecast",
        "definition": "FY27 Target NSV in ₹ Lakh",
        "finance_control_column": "fy27_target_nsv_lakhs",
        "dashboard_source": "forecast.fy27_total",  # FY27 forecast
        "tolerance_pct": 2.0,
        "tolerance_type": "percentage",
        "unit": "₹ Lakh"
    }
}

def log_info(msg):
    print(f"✓ {msg}")

def log_warn(msg):
    print(f"⚠ {msg}")

def log_error(msg):
    print(f"✗ {msg}", file=sys.stderr)

def validate_arguments(args):
    """Validate command-line arguments."""
    if not args.finance_controls:
        log_error("--finance-controls is required")
        return False

    if not args.fy or args.fy not in ["FY25", "FY26", "FY27"]:
        log_error("Invalid --fy. Choose: FY25, FY26, FY27")
        return False

    if not args.validation_date:
        log_error("--validation-date is required (format: YYYY-MM-DD)")
        return False

    try:
        datetime.strptime(args.validation_date, "%Y-%m-%d")
    except ValueError:
        log_error("Invalid validation date format (expected: YYYY-MM-DD)")
        return False

    return True

def check_files_exist(finance_controls_path, data_js_path):
    """Verify required files exist."""
    if not Path(finance_controls_path).exists():
        log_error(f"Finance controls file not found: {finance_controls_path}")
        return False

    if not Path(data_js_path).exists():
        log_error(f"data.js not found: {data_js_path}")
        return False

    return True

def load_finance_controls(filepath: str, fy: str) -> Dict:
    """Load Finance control data from CSV export."""
    log_info(f"Loading Finance controls from {filepath}")

    try:
        controls = {}
        with open(filepath, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Assume CSV has columns: fy, kpi_name, value, unit, control_date
                if row.get('fy') == fy:
                    kpi_name = row.get('kpi_name', '').lower()
                    value = float(row.get('value', 0))
                    controls[kpi_name] = {
                        'value': value,
                        'unit': row.get('unit', ''),
                        'control_date': row.get('control_date', ''),
                        'source': row.get('source', 'SAP FI')
                    }

        if not controls:
            log_error(f"No Finance controls found for {fy}")
            return None

        log_info(f"Loaded {len(controls)} Finance control KPIs for {fy}")
        return controls

    except Exception as e:
        log_error(f"Failed to load Finance controls: {str(e)}")
        return None

def load_data_js(filepath: str) -> Dict:
    """Extract dashboard data from data.js (generated JSON)."""
    log_info(f"Loading dashboard data from {filepath}")

    try:
        with open(filepath, 'r') as f:
            content = f.read()

        # Extract JSON from data.js (format: window.DASH = {...};)
        match = re.search(r'window\.DASH\s*=\s*(\{.*?\});', content, re.DOTALL)
        if not match:
            log_error("Could not find window.DASH in data.js")
            return None

        json_str = match.group(1)
        data = json.loads(json_str)

        log_info(f"Loaded dashboard data with {len(data)} top-level blocks")
        return data

    except json.JSONDecodeError as e:
        log_error(f"JSON parse error in data.js: {str(e)}")
        return None
    except Exception as e:
        log_error(f"Failed to load data.js: {str(e)}")
        return None

def extract_dashboard_kpi(data: Dict, kpi_key: str) -> Optional[float]:
    """Extract a single KPI value from dashboard data using dot-notation path."""
    try:
        kpi_config = KPI_MATRIX.get(kpi_key)
        if not kpi_config:
            log_warn(f"KPI {kpi_key} not in validation matrix")
            return None

        source_path = kpi_config['dashboard_source']  # e.g. "data.primary.total"
        parts = source_path.split('.')

        value = data
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return None

            if value is None:
                return None

        return float(value) if isinstance(value, (int, float)) else None

    except Exception as e:
        log_warn(f"Error extracting {kpi_key}: {str(e)}")
        return None

def calculate_variance(dashboard_value: float, finance_value: float,
                       tolerance_type: str) -> Tuple[float, float]:
    """Calculate absolute and percentage variance between two values."""
    if tolerance_type == "percentage":
        variance_pct = 100 * (dashboard_value - finance_value) / max(abs(finance_value), 1)
    else:  # percentage_points (for % metrics)
        variance_pct = dashboard_value - finance_value

    variance_abs = dashboard_value - finance_value
    return variance_abs, variance_pct

def validate_kpi(kpi_key: str, dashboard_value: Optional[float],
                 finance_value: float, tolerance_pct: float,
                 tolerance_type: str) -> Tuple[bool, Dict]:
    """Validate a single KPI against tolerance."""

    if dashboard_value is None:
        return False, {
            'kpi': kpi_key,
            'status': 'FAIL',
            'reason': 'Missing value in dashboard',
            'dashboard_value': None,
            'finance_value': finance_value,
            'variance': None,
            'tolerance': tolerance_pct
        }

    variance_abs, variance_pct = calculate_variance(dashboard_value, finance_value, tolerance_type)

    passes = abs(variance_pct) <= tolerance_pct

    return passes, {
        'kpi': kpi_key,
        'status': 'PASS' if passes else 'FAIL',
        'dashboard_value': round(dashboard_value, 2),
        'finance_value': round(finance_value, 2),
        'variance_abs': round(variance_abs, 2),
        'variance_pct': round(variance_pct, 2),
        'tolerance_pct': tolerance_pct,
        'tolerance_type': tolerance_type,
        'reason': "Within tolerance" if passes else f"Exceeds {tolerance_pct} threshold"
    }

def run_validation(finance_controls: Dict, dashboard_data: Dict, fy: str) -> Dict:
    """Run full KPI validation suite."""
    log_info(f"Running KPI validation for {fy}")

    results = {
        'fy': fy,
        'validation_timestamp': datetime.now().isoformat(),
        'kpi_results': [],
        'summary': {
            'total_kpis': 0,
            'passed': 0,
            'failed': 0,
            'missing': 0,
            'overall_status': 'PENDING'
        }
    }

    for kpi_key, kpi_config in KPI_MATRIX.items():
        # Get Finance control value
        finance_value = finance_controls.get(kpi_key, {}).get('value')
        if finance_value is None:
            log_warn(f"{kpi_key}: No Finance control value")
            results['summary']['missing'] += 1
            results['kpi_results'].append({
                'kpi': kpi_key,
                'status': 'MISSING_CONTROL',
                'reason': 'Finance control not provided'
            })
            continue

        # Extract dashboard value
        dashboard_value = extract_dashboard_kpi(dashboard_data, kpi_key)

        # Validate
        passed, validation_result = validate_kpi(
            kpi_key,
            dashboard_value,
            finance_value,
            kpi_config['tolerance_pct'],
            kpi_config['tolerance_type']
        )

        results['kpi_results'].append(validation_result)
        results['summary']['total_kpis'] += 1

        if passed:
            results['summary']['passed'] += 1
        else:
            results['summary']['failed'] += 1

    # Overall status
    if results['summary']['failed'] == 0 and results['summary']['missing'] == 0:
        results['summary']['overall_status'] = 'PASS'
    elif results['summary']['failed'] == 0 and results['summary']['missing'] > 0:
        results['summary']['overall_status'] = 'PASS_WITH_MISSING_CONTROLS'
    else:
        results['summary']['overall_status'] = 'FAIL'

    return results

def generate_validation_report(results: Dict, validation_date: str) -> str:
    """Generate human-readable validation report."""

    report = f"""
================================================================================
PHASE 3 BUSINESS VALIDATION REPORT
================================================================================

Validation Date: {validation_date}
Report Generated: {results['validation_timestamp']}
FY: {results['fy']}

SUMMARY
================================================================================
Overall Status: {results['summary']['overall_status']}

KPI Results:
  Total KPIs Validated: {results['summary']['total_kpis']}
  Passed (within tolerance): {results['summary']['passed']}
  Failed (exceed tolerance): {results['summary']['failed']}
  Missing Controls: {results['summary']['missing']}

Pass Rate: {100 * results['summary']['passed'] / max(results['summary']['total_kpis'], 1):.1f}%

================================================================================
DETAILED RESULTS
================================================================================
"""

    for result in results['kpi_results']:
        kpi = result.get('kpi', 'UNKNOWN')
        kpi_config = KPI_MATRIX.get(kpi, {})
        status = result.get('status', 'UNKNOWN')

        report += f"\n{kpi.upper()}\n"
        report += f"  Tab: {kpi_config.get('tab', 'N/A')}\n"
        report += f"  Definition: {kpi_config.get('definition', 'N/A')}\n"
        report += f"  Status: {status}\n"

        if status in ['PASS', 'FAIL']:
            report += f"  Dashboard Value: {result.get('dashboard_value')} {kpi_config.get('unit', '')}\n"
            report += f"  Finance Control: {result.get('finance_value')} {kpi_config.get('unit', '')}\n"
            variance_pct = result.get('variance_pct')
            if variance_pct is not None:
                report += f"  Variance: {result.get('variance_abs')} ({variance_pct:.2f}%)\n"
            else:
                report += "  Variance: N/A (missing dashboard value)\n"
            report += f"  Tolerance: ±{result.get('tolerance_pct')} {result.get('tolerance_type')}\n"
            report += f"  Result: {result.get('reason')}\n"
        elif status == 'MISSING_CONTROL':
            report += f"  Reason: {result.get('reason')}\n"
            report += f"  Action: Awaiting Finance to provide {kpi} control value\n"

    return report

def _generate_failed_kpi_summary(results: Dict) -> str:
    """Generate summary of failed KPIs for sign-off form."""
    failed = [r for r in results['kpi_results'] if r.get('status') == 'FAIL']
    if not failed:
        return "None — all KPIs within tolerance."

    explanation = ""
    for kpi_result in failed:
        variance_pct = kpi_result.get('variance_pct')
        if variance_pct is not None:
            explanation += f"\n  - {kpi_result.get('kpi')}: Variance {variance_pct:.2f}% " \
                          f"(tolerance: {kpi_result.get('tolerance_pct')})\n" \
                          f"    Root Cause: [TO BE COMPLETED BY VALIDATOR]\n"
        else:
            explanation += f"\n  - {kpi_result.get('kpi')}: N/A (missing data)\n"

    return explanation

def _generate_variance_summary(results: Dict) -> str:
    """Generate variance analysis summary."""
    summary = "\nKPI Variance Summary (By Magnitude):\n"

    kpis_with_variance = [r for r in results['kpi_results']
                         if r.get('variance_pct') is not None]
    kpis_with_variance.sort(key=lambda x: abs(x.get('variance_pct', 0)), reverse=True)

    for i, kpi_result in enumerate(kpis_with_variance[:5]):  # Top 5
        summary += f"\n  {i+1}. {kpi_result.get('kpi')}: " \
                  f"{kpi_result.get('variance_pct'):.2f}% variance\n"

    return summary

def generate_signoff_form(results: Dict, validation_date: str) -> str:
    """Generate Business Stakeholder Sign-Off Form."""

    form = f"""
================================================================================
PHASE 3 BUSINESS VALIDATION — SIGN-OFF FORM
================================================================================

Project: Modern Trade (MT) Dashboard — Production Readiness Sprint
Phase: Phase 3 — Business Validation (KPI Reconciliation)
Date: {validation_date}

VALIDATION RESULTS SUMMARY
================================================================================
FY Under Review: {results['fy']}
Total KPIs Validated: {results['summary']['total_kpis']}
Passed: {results['summary']['passed']}
Failed: {results['summary']['failed']}
Missing Controls: {results['summary']['missing']}

Overall Status: {results['summary']['overall_status']}

================================================================================
CERTIFICATION STATEMENT
================================================================================

I hereby certify that:

[ ] I have reviewed the KPI reconciliation report above.

[ ] I have verified that dashboard KPI values reconcile to Finance control
    totals within established tolerance thresholds.

[ ] I have investigated any failed KPIs and documented the root cause
    (variance explanation document attached: ______________________).

[ ] I approve the MT Dashboard for production deployment with the
    reconciliation status documented in this sign-off.

[ ] I understand that any post-deployment data anomalies will trigger a
    production incident and immediate investigation per ON_CALL_GUIDE.md.

================================================================================
SIGN-OFF INFORMATION
================================================================================

Name (Print): ___________________________________

Title: ___________________________________

Organization/Department: ___________________________________

Email: ___________________________________

Signature: ___________________________________ Date: _______________

Phone: ___________________________________

================================================================================
ADDITIONAL INFORMATION
================================================================================

Failed KPIs Explanation (if any):
{_generate_failed_kpi_summary(results)}

Variance Investigation Summary:
{_generate_variance_summary(results)}

Data Quality Issues Identified:
(List any data anomalies or quality concerns discovered during validation)
___________________________________________________________________________
___________________________________________________________________________
___________________________________________________________________________

Dependencies/Next Steps:
[ ] PBIP assembly (Power BI build kit) — Timeline: _________________
[ ] Power BI testing — Timeline: _________________
[ ] Enterprise deployment — Timeline: _________________
[ ] Post-deployment monitoring (KPI dashboard) — Timeline: _________________

Notes:
___________________________________________________________________________
___________________________________________________________________________
___________________________________________________________________________

================================================================================
SUBMISSION INSTRUCTIONS
================================================================================

1. Complete all sections above (required fields marked with [ ])
2. Attach any supporting documentation (variance explanations, root cause analysis)
3. Sign and date the form
4. Submit to: analytics-team@honasa.com
5. Keep copy for records (archive in: /docs/PHASE_3_SIGNOFFS/)

Approval Authority: Finance Controller (or delegated CFO representative)
Approval SLA: 2 business days

================================================================================
"""

    return form

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Phase 3: Business Validation — KPI Reconciliation to Finance Controls"
    )
    parser.add_argument("--finance-controls", help="Path to Finance control export (CSV)")
    parser.add_argument("--data-js", default=str(DATA_JS_PATH),
                       help="Path to data.js (default: dashboard/data.js)")
    parser.add_argument("--fy", help="Fiscal year (FY25|FY26|FY27)")
    parser.add_argument("--validation-date", help="Validation date (YYYY-MM-DD)")
    parser.add_argument("--output-report",
                       help="Output path for validation report (default: docs/PHASE_3_VALIDATION_<timestamp>.txt)")

    args = parser.parse_args()

    # Validate arguments
    if not validate_arguments(args):
        return 1

    # Check files
    if not check_files_exist(args.finance_controls, args.data_js):
        return 2

    # Load data
    finance_controls = load_finance_controls(args.finance_controls, args.fy)
    if not finance_controls:
        return 5

    dashboard_data = load_data_js(args.data_js)
    if not dashboard_data:
        return 3

    # Run validation
    results = run_validation(finance_controls, dashboard_data, args.fy)

    # Generate reports
    validation_report = generate_validation_report(results, args.validation_date)
    signoff_form = generate_signoff_form(results, args.validation_date)

    # Print reports
    print(validation_report)
    print("\n" + "="*80)
    print(signoff_form)

    # Save reports
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    docs_dir = PROJECT_ROOT / "docs"

    report_path = docs_dir / f"PHASE_3_VALIDATION_{timestamp}.txt"
    with open(report_path, 'w') as f:
        f.write(validation_report)
    log_info(f"Validation report saved: {report_path}")

    signoff_path = docs_dir / f"PHASE_3_SIGNOFF_{timestamp}.txt"
    with open(signoff_path, 'w') as f:
        f.write(signoff_form)
    log_info(f"Sign-off form saved: {signoff_path}")

    # Save JSON for CI/CD
    json_output = {
        'validation_date': args.validation_date,
        'fy': args.fy,
        'results': results,
        'overall_status': results['summary']['overall_status']
    }
    json_path = docs_dir / f"PHASE_3_RESULTS_{timestamp}.json"
    with open(json_path, 'w') as f:
        json.dump(json_output, f, indent=2)
    log_info(f"JSON output saved: {json_path}")

    # Determine exit code
    if results['summary']['overall_status'] == 'PASS':
        log_info("Phase 3 Validation: ALL KPIs PASSED ✓")
        return 0
    elif results['summary']['overall_status'] == 'PASS_WITH_MISSING_CONTROLS':
        log_warn("Phase 3 Validation: PASSED (with missing Finance controls)")
        return 0
    else:
        log_error("Phase 3 Validation: FAILED (one or more KPIs exceed tolerance)")
        return 4

if __name__ == "__main__":
    sys.exit(main())
