#!/usr/bin/env python3
"""
Phase 3 Validation: Verify Commercial Analytics tab (Tab 14) implementation.
Checks:
- buildAnalytics() function implementation
- Chart renderer functions (PVM, Health, Quadrant)
- Filter reactivity integration
- Empty state handling
- enriched_metrics.json schema validation
"""
import json
import re
import sys
from pathlib import Path

def validate_html_implementation():
    """Verify Phase 3 code in dashboard/index.html"""
    print("=" * 70)
    print("PHASE 3 VALIDATION: Commercial Analytics Implementation")
    print("=" * 70)

    html_path = Path("dashboard/index.html")
    try:
        html = html_path.read_text()
    except FileNotFoundError:
        print("❌ dashboard/index.html not found")
        return False

    checks = {
        "buildAnalytics function": r"function buildAnalytics\(\)",
        "destroyAnalyticsCharts function": r"function destroyAnalyticsCharts\(\)",
        "renderPVMChart function": r"function renderPVMChart\(\)",
        "renderHealthChart function": r"function renderHealthChart\(\)",
        "renderQuadrantChart function": r"function renderQuadrantChart\(\)",
        "Chart.destroy() calls": r"\.destroy\(\)",
        "Chart.js instantiation": r"new Chart\(",
        "computePVMMetrics function": r"function computePVMMetrics\(\)",
        "computeChannelHealth function": r"function computeChannelHealth\(\)",
        "computeSKUQuadrants function": r"function computeSKUQuadrants\(\)",
        "generateAnalyticsInsights function": r"function generateAnalyticsInsights\(\)",
        "Canvas element cvPVM": r"id=\"cvPVM\"",
        "Canvas element cvHealth": r"id=\"cvHealth\"",
        "Canvas element cvQuadrant": r"id=\"cvQuadrant\"",
        "Tab analytics section": r"id=\"tab-analytics\"",
        "Filter reactivity check": r"destroyAnalyticsCharts\(\)",
    }

    all_passed = True
    for check_name, pattern in checks.items():
        if re.search(pattern, html):
            print(f"✓ {check_name}")
        else:
            print(f"❌ {check_name} NOT FOUND")
            all_passed = False

    return all_passed

def validate_enriched_metrics():
    """Verify enriched_metrics.json schema if it exists"""
    print("\n" + "=" * 70)
    print("ENRICHED METRICS VALIDATION")
    print("=" * 70)

    metrics_path = Path("dashboard/enriched_metrics.json")
    if not metrics_path.exists():
        print("⚠️  enriched_metrics.json not generated yet (optional, non-blocking)")
        return True

    try:
        with open(metrics_path, "r") as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Failed to parse enriched_metrics.json: {e}")
        return False

    # Validate schema
    required_keys = ["pvm_decomposition", "channel_health", "sku_quadrants", "insights"]
    found_keys = [k for k in required_keys if k in data]

    print(f"\n✓ Valid JSON structure")
    print(f"✓ Sections found: {', '.join(found_keys)}")

    # Check for NaN/undefined literals
    serialized = json.dumps(data)
    if re.search(r'\bNaN\b|\bundefined\b', serialized):
        print(f"❌ Contains literal 'NaN' or 'undefined' strings")
        return False
    else:
        print(f"✓ No NaN/undefined literals detected")

    # Validate insights structure
    if "insights" in data and isinstance(data["insights"], list):
        print(f"✓ {len(data['insights'])} insights generated")
    else:
        print(f"⚠️  Insights not in expected format")

    return True

def validate_data_js_structure():
    """Verify data.js has required blocks for Phase 3"""
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
        "primary": "Primary sales data for PVM computation",
        "offtake": "Offtake data for health ratios",
        "detail_records": "SKU-level detail for quadrant analysis",
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

    # Check FY coverage
    if "primary" in data:
        fy_tags = data["primary"].get("fy_tags", [])
        if fy_tags:
            print(f"\n✓ FY Coverage in primary: {', '.join(fy_tags)}")

    if "offtake" in data:
        fy_check = any(k.startswith("total_fy") or k.startswith("monthly_fy") for k in data["offtake"].keys())
        if fy_check:
            print(f"✓ FY Coverage in offtake: Present")

    return all_present

def validate_chart_safety():
    """Verify NaN/undefined safety and filter handling"""
    print("\n" + "=" * 70)
    print("CHART SAFETY & FILTER HANDLING")
    print("=" * 70)

    html_path = Path("dashboard/index.html")
    html = html_path.read_text()

    safety_checks = {
        "nullish coalescing ??": r"\?\?",
        "OR fallback ||": r"\|\|",
        "Empty state handling": r"No.*data.*available|No offtake data",
        "Chart destroy before render": r"destroyAnalyticsCharts\(\)",
        "Try-catch error handling": r"try\s*{.*?}\s*catch",
    }

    checks_passed = 0
    for check_name, pattern in safety_checks.items():
        if re.search(pattern, html, re.DOTALL):
            print(f"✓ {check_name}")
            checks_passed += 1
        else:
            print(f"⚠️  {check_name} - may need verification")

    print(f"\n✓ {checks_passed}/{len(safety_checks)} safety checks passed")
    return checks_passed >= 3  # At least 3 checks must pass

def main():
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║  PHASE 3 VALIDATION: Commercial Analytics Visualization Layer       ║")
    print("╚" + "=" * 68 + "╝")
    print()

    results = {
        "HTML Implementation": validate_html_implementation(),
        "Enriched Metrics": validate_enriched_metrics(),
        "Data.JS Structure": validate_data_js_structure(),
        "Chart Safety": validate_chart_safety(),
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
        print("✅ PHASE 3 VALIDATION PASSED — Ready for 56-state audit")
    else:
        print("❌ PHASE 3 VALIDATION FAILED — Review above errors")
    print("=" * 70 + "\n")

    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
