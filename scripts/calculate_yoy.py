#!/usr/bin/env python3
"""
Calculate Year-over-Year (YoY) metrics by comparing current data.js against
archived snapshot from 12 months prior.
Injects yoy_metrics block into window.DASH for Phase 4.2 (YoY Performance Comparison).
"""

import os
import json
import re
from datetime import datetime


def extract_json_from_datajs(file_path):
    """Extract JSON payload from data.js using brace counting."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except IOError as e:
        print(f"❌ Error reading {file_path}: {e}")
        return None

    # Find opening brace after window.DASH=
    start_idx = content.find('window.DASH=')
    if start_idx == -1:
        print("❌ Error: Could not locate 'window.DASH=' in data.js")
        return None

    brace_start = content.find('{', start_idx)
    if brace_start == -1:
        print("❌ Error: Could not locate opening brace")
        return None

    # Count braces to find matching closing brace
    brace_count = 0
    for i in range(brace_start, len(content)):
        if content[i] == '{':
            brace_count += 1
        elif content[i] == '}':
            brace_count -= 1
            if brace_count == 0:
                raw_json = content[brace_start:i+1]
                try:
                    return json.loads(raw_json)
                except json.JSONDecodeError as e:
                    print(f"❌ Error parsing JSON: {e}")
                    return None

    print("❌ Error: Could not find matching closing brace")
    return None


def calculate_yoy():
    """Calculate YoY growth metrics and inject into data.js."""

    # 1. Determine comparison periods
    current_date = datetime.now()
    current_month = current_date.strftime("%Y-%m")
    last_year_month = f"{current_date.year - 1}-{current_date.strftime('%m')}"

    archive_path = os.path.join("archive", last_year_month, "data.json")
    data_js_path = os.path.join("dashboard", "data.js")

    if not os.path.exists(data_js_path):
        print(f"⚠️  {data_js_path} not found. Skipping YoY calculation.")
        return

    # 2. Read current payload
    print(f"Comparing current data ({current_month}) vs. historical ({last_year_month})...")
    current_data = extract_json_from_datajs(data_js_path)
    if not current_data:
        return

    # 3. Initialize default YoY state
    yoy_metrics = {
        "status": "insufficient_history",
        "comparison_period": last_year_month,
        "top_line": {},
        "by_brand": {}
    }

    # 4. Perform comparison if historical data exists
    if os.path.exists(archive_path):
        print(f"✓ Historical data found for {last_year_month}. Calculating YoY...")
        try:
            with open(archive_path, "r", encoding="utf-8") as f:
                historical_data = json.load(f)
        except IOError as e:
            print(f"⚠️  Could not read historical data: {e}")
            return

        # Calculate RBC total FY27 growth (most recent FY)
        curr_rbc_total = current_data.get("reliance_bc", {}).get("total_fy27")
        hist_rbc_total = historical_data.get("reliance_bc", {}).get("total_fy27")

        if hist_rbc_total and hist_rbc_total > 0 and curr_rbc_total:
            rbc_growth = ((curr_rbc_total - hist_rbc_total) / hist_rbc_total) * 100
            yoy_metrics["status"] = "active"
            yoy_metrics["top_line"]["rbc_total_growth_pct"] = round(rbc_growth, 1)
            print(f"  • RBC FY27 Total: ₹{hist_rbc_total:.2f}L → ₹{curr_rbc_total:.2f}L ({rbc_growth:+.1f}%)")

        # Calculate brand-level growth (Mamaearth as example)
        curr_brands = current_data.get("reliance_bc", {}).get("by_brand", [])
        hist_brands = historical_data.get("reliance_bc", {}).get("by_brand", [])

        if curr_brands and hist_brands:
            # Build lookup for historical brands
            hist_brand_map = {b.get("name"): b.get("total", 0) for b in hist_brands}

            for brand in curr_brands[:2]:  # Top 2 brands
                brand_name = brand.get("name")
                curr_total = brand.get("total", 0)
                hist_total = hist_brand_map.get(brand_name, 0)

                if hist_total > 0:
                    brand_growth = ((curr_total - hist_total) / hist_total) * 100
                    yoy_metrics["by_brand"][brand_name] = {
                        "growth_pct": round(brand_growth, 1),
                        "current": round(curr_total, 2),
                        "historical": round(hist_total, 2)
                    }
                    print(f"  • {brand_name}: ₹{hist_total:.2f}L → ₹{curr_total:.2f}L ({brand_growth:+.1f}%)")

    else:
        print(f"⚠️  No historical data found at {archive_path}")
        print(f"   Note: YoY comparisons will be available after {last_year_month} data is archived.")

    # 5. Inject back into current data
    print(f"\n✅ YoY metrics calculated (Status: {yoy_metrics['status']})")
    current_data["yoy_metrics"] = yoy_metrics

    # Read the file again to preserve the exact structure
    with open(data_js_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Find and replace the JSON object while preserving the wrapper
    start_idx = content.find('window.DASH=')
    brace_start = content.find('{', start_idx)

    # Count braces to find matching closing brace
    brace_count = 0
    for i in range(brace_start, len(content)):
        if content[i] == '{':
            brace_count += 1
        elif content[i] == '}':
            brace_count -= 1
            if brace_count == 0:
                brace_end = i + 1
                break

    # Reconstruct with updated JSON
    updated_json = json.dumps(current_data, separators=(',', ':'))
    new_content = content[:brace_start] + updated_json + content[brace_end:]

    try:
        with open(data_js_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"✓ YoY metrics injected into {data_js_path}")
    except IOError as e:
        print(f"❌ Error writing to {data_js_path}: {e}")


if __name__ == "__main__":
    calculate_yoy()
