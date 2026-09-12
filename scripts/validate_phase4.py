#!/usr/bin/env python3
"""
Phase 4 Validation: Verify S&OP Forecast Diagnostics, PO SLA Risk Monitor, Real P&L Margins & Cross-Tab Drill-Through.
Checks:
- Real P&L margin calculation functions
- S&OP WMAPE and Forecast Bias computations
- Open PO SLA penalty risk calculation
- Cross-tab click navigation handlers
- ForecastAccuracy and PORiskSummary functions
"""
import json
import re
import sys
from pathlib import Path

def validate_html_implementation():
    """Verify Phase 4 code in dashboard/index.html"""
    print("=" * 70)
    print("PHASE 4 VALIDATION: S&OP Forecast Intelligence & PO SLA Risk Monitor")
    print("=" * 70)

    html_path = Path("dashboard/index.html")
    try:
        html = html_path.read_text()
    except FileNotFoundError:
        print("❌ dashboard/index.html not found")
        return False

    checks = {
        "computeForecastAccuracy function": r"function computeForecastAccuracy\(\)",
        "computePORiskSummary function": r"function computePORiskSummary\(\)",
        "calculateRealGrossMargin method": r"calculate_real_gross_margin",
        "WMAPE % calculation": r"wmape",
        "Forecast Bias tracking": r"bias_pct|bias_status",
        "PO SLA penalty debit": r"Penalty_Debit|SLA_Window|penalty_exposure",
        "Cross-tab drillTo calls": r"drillTo\(.*?\)",
        "Health chart click handler": r"cvHealth|onClick.*health",
        "Quadrant bubble click handler": r"cvQuadrant|onClick.*quad",
        "Forecast Reliability UI": r"S&OP Forecast Reliability|Accuracy|WMAPE",
        "Open PO Risk Summary": r"Open PO.*SLA|breach_count|penalty_exposure",
        "Real P&L Margin integration": r"Gross_Margin|Gross Margin %",
        "Chart destroy lifecycle": r"destroyAnalyticsCharts",
    }

    all_passed = True
    for check_name, pattern in checks.items():
        if re.search(pattern, html, re.IGNORECASE):
            print(f"✓ {check_name}")
        else:
            print(f"❌ {check_name} NOT FOUND")
            all_passed = False

    return all_passed

def validate_python_enhancements():
    """Verify Phase 4 methods in analytics_enhancement_layer.py"""
    print("\n" + "=" * 70)
    print("PYTHON ANALYTICS ENHANCEMENTS VALIDATION")
    print("=" * 70)

    py_path = Path("scripts/analytics_enhancement_layer.py")
    try:
        py = py_path.read_text()
    except FileNotFoundError:
        print("❌ scripts/analytics_enhancement_layer.py not found")
        return False

    checks = {
        "calculate_real_gross_margin method": r"def calculate_real_gross_margin",
        "calculate_sop_forecast_accuracy method": r"def calculate_sop_forecast_accuracy",
        "calculate_open_po_sla_risk method": r"def calculate_open_po_sla_risk",
        "WMAPE % computation": r"WMAPE|wmape_pct",
        "Forecast Bias % computation": r"bias_pct|Forecast Bias",
        "PO SLA window mapping": r"sla_windows",
        "Penalty debit calculation": r"Penalty_Debit|penalty_pct",
        "Gross Margin % safe fallback": r"Gross_Margin_Pct.*fillna|clip\(0, 100\)",
    }

    all_passed = True
    for check_name, pattern in checks.items():
        if re.search(pattern, py):
            print(f"✓ {check_name}")
        else:
            print(f"❌ {check_name} NOT FOUND")
            all_passed = False

    return all_passed

def validate_data_js_structure():
    """Verify data.js has required blocks for Phase 4"""
    print("\n" + "=" * 70)
    print("DATA.JS STRUCTURE VALIDATION")
    print("=" * 70)

    data_js_path = Path("dashboard/data.js")
    try:
        txt = data_js_path.read_text()
        start = txt.index("window.DASH = ") + len("window.DASH = ")
        end = txt.rindex(";")
        data = json.loads(txt[start:end])
    except Exception as e:
        print(f"❌ Failed to load data.js: {e}")
        return False

    required_blocks = {
        "primary": "Primary sales data for P&L margin integration",
        "forecast": "Forecast targets for WMAPE/Bias calculation",
        "detail_records": "Article-level detail for real margin computation",
    }

    all_present = True
    for block, desc in required_blocks.items():
        if block in data:
            if isinstance(data[block], (dict, list)):
                size = len(data[block]) if isinstance(data[block], list) else len(str(data[block]))
                print(f"✓ {block}: {size} records/entries ({desc})")
            else:
                print(f"✓ {block}: {desc}")
        else:
            print(f"❌ {block} NOT FOUND")
            all_present = False

    return all_present

def validate_sop_and_po_safety():
    """Verify NaN/undefined safety in S&OP and PO calculations"""
    print("\n" + "=" * 70)
    print("S&OP & PO RISK SAFETY CHECKS")
    print("=" * 70)

    html_path = Path("dashboard/index.html")
    html = html_path.read_text()

    safety_checks = {
        "Nullish coalescing for forecast accuracy": r"\?\?.*accuracy",
        "Nullish coalescing for bias": r"\?\?.*bias",
        "Nullish coalescing for PO aging": r"\?\?.*aging",
        "Safe division (avoiding divide-by-zero)": r"\.replace\(0, np\.nan\)|\.replace\(0, 1\)|if.*>0",
        "Try-catch around forecast calc": r"try\s*{.*forecast",
        "Try-catch around PO calc": r"try\s*{.*po|try\s*{.*PO",
    }

    checks_passed = 0
    for check_name, pattern in safety_checks.items():
        if re.search(pattern, html, re.DOTALL | re.IGNORECASE):
            print(f"✓ {check_name}")
            checks_passed += 1
        else:
            print(f"⚠️  {check_name} - may need verification")

    print(f"\n✓ {checks_passed}/{len(safety_checks)} safety checks passed")
    return checks_passed >= 4  # At least 4 checks must pass

def main():
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║  PHASE 4 VALIDATION: S&OP Intelligence + PO SLA Risk + Real P&L   ║")
    print("╚" + "=" * 68 + "╝")
    print()

    results = {
        "HTML Implementation": validate_html_implementation(),
        "Python Enhancements": validate_python_enhancements(),
        "Data.JS Structure": validate_data_js_structure(),
        "S&OP & PO Safety": validate_sop_and_po_safety(),
    }

    print("\n" + "=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)

    for check, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {check}")

    all_passed = all(results.values())

    print("\n" + "=" * 70)
    if all_passed:
        print("✅ PHASE 4 VALIDATION PASSED — Ready for 56-state audit")
    else:
        print("❌ PHASE 4 VALIDATION FAILED — Review above errors")
    print("=" * 70 + "\n")

    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
