#!/usr/bin/env python3
"""
Ingest newly generated FY27 forecast workbooks into dashboard/data.js.

Reads:
  - Combined_MT_Forecast_Q2_FY27.xlsx (portfolio view: Face Wash + Shampoo)
  - Extracts monthly forecast totals (Sep/Oct/Nov)
  - Updates the forecast block in existing data.js with new values

Usage:
    python ingest_forecast_to_dashboard.py \
        --forecast-xlsx exports/Combined_MT_Forecast_Q2_FY27.xlsx \
        --data-js dashboard/data.js
"""
import argparse
import json
from pathlib import Path
import pandas as pd
import re

def r2(v):
    """Round to 2 decimal places, matching build_dashboard_data.py convention."""
    return round(float(v or 0), 2) if v else 0

def fy_tag_from_ym(year, month):
    """Calendar (year, month) -> 'FY27' style tag. Apr-2026 -> FY27; Mar-2026 -> FY26."""
    return f"FY{(year + 1 if month >= 4 else year) % 100:02d}"

def fy_start_year(tag):
    """'FY27' -> 2026 (the FY's April calendar year)."""
    return 2000 + int(str(tag).strip()[2:]) - 1

def extract_forecast_from_xlsx(xlsx_path):
    """
    Load Combined_MT_Forecast_Q2_FY27.xlsx and extract monthly forecast totals.

    Expected sheet: Portfolio_Summary with columns:
      Month | FY27_FaceWash_Cr | FY27_Shampoo_Cr | FY27_Total_Cr

    Returns:
      {
        'months': ['Sep-26', 'Oct-26', 'Nov-26'],
        'values': [307.60, 344.86, 354.17],  # in Crores
        'fy_tag': 'FY27'
      }
    """
    try:
        df = pd.read_excel(xlsx_path, sheet_name='Portfolio_Summary')
        print(f"✓ Loaded {xlsx_path}")
        print(f"  Columns: {df.columns.tolist()}")
        print(f"  Shape: {df.shape}")
    except Exception as e:
        print(f"✗ Error reading {xlsx_path}: {e}")
        return None

    # Identify month and total columns
    # Try variations of column names
    month_col = None
    total_col = None

    for col in df.columns:
        col_lower = str(col).lower()
        if 'month' in col_lower or 'week' in col_lower:
            month_col = col
        if 'total' in col_lower and 'cr' in col_lower:
            total_col = col

    if not month_col or not total_col:
        # Fallback: assume first column is Month, last numeric is Total
        month_col = df.columns[0]
        # Find last numeric column
        for col in reversed(df.columns):
            if pd.api.types.is_numeric_dtype(df[col]):
                total_col = col
                break

    if month_col is None or total_col is None:
        print(f"✗ Could not identify Month/Total columns in {xlsx_path}")
        print(f"  Available columns: {df.columns.tolist()}")
        return None

    # Extract rows with month labels
    records = []
    month_map = {'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
                 'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12}
    month_abbrev = {v: k for k, v in month_map.items()}

    for idx, row in df.iterrows():
        month_label = str(row[month_col]).strip()
        total_val = row[total_col]

        # Skip non-numeric rows (headers, summaries)
        try:
            total_val = float(total_val)
        except (ValueError, TypeError):
            continue

        # Match "Sep-26", "Oct-26", etc. or "September", "October", etc.
        # Try short form first (Sep-26)
        matched_label = None
        if re.match(r'^[A-Z][a-z]{2}-\d{2}$', month_label):
            matched_label = month_label
        else:
            # Try full month name (September, October, etc.)
            for full_name, abbrev in [('September', 'Sep'), ('October', 'Oct'),
                                       ('November', 'Nov'), ('December', 'Dec'),
                                       ('January', 'Jan'), ('February', 'Feb'),
                                       ('March', 'Mar'), ('April', 'Apr'),
                                       ('May', 'May'), ('June', 'Jun'),
                                       ('July', 'Jul'), ('August', 'Aug')]:
                if month_label.lower() == full_name.lower():
                    # Assume current year (2026) for Sep-Nov
                    matched_label = f"{abbrev}-26"
                    break

        if matched_label:
            # Convert Crores to Lakh (multiply by 100) for dashboard consistency
            val_lakh = r2(total_val * 100)
            records.append({
                'label': matched_label,
                'value_cr': total_val,
                'value_lakh': val_lakh
            })

    if not records:
        print(f"✗ No valid forecast records extracted from {xlsx_path}")
        return None

    print(f"✓ Extracted {len(records)} months:")
    for r in records:
        print(f"    {r['label']}: ₹{r['value_cr']:.2f} Cr (₹{r['value_lakh']:.0f} Lakh)")

    # Derive FY tag from first month (e.g., Sep-26 -> FY27)
    first_month = records[0]['label']
    parts = first_month.split('-')
    year = 2000 + int(parts[1])
    month_map = {'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
                 'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12}
    month = month_map.get(parts[0], 9)
    fy_tag = fy_tag_from_ym(year, month)

    return {
        'months': [r['label'] for r in records],
        'values': [r['value_lakh'] for r in records],
        'fy_tag': fy_tag,
        'total_cr': r2(sum(r['value_cr'] for r in records))
    }

def update_forecast_block_in_datajs(datajs_path, forecast_data):
    """
    Load existing data.js, update forecast block, and write back.

    Preserves all other blocks (primary, offtake, insights, etc.).
    """
    # Read data.js
    try:
        txt = datajs_path.read_text(encoding='utf-8')
    except Exception as e:
        print(f"✗ Could not read {datajs_path}: {e}")
        return False

    # Extract JSON object from "window.DASH = {...};"
    match = re.search(r'window\.DASH\s*=\s*({.*})\s*;', txt, re.DOTALL)
    if not match:
        print(f"✗ Could not parse data.js format (expected window.DASH = {{...}};)")
        return False

    try:
        obj = json.loads(match.group(1))
    except json.JSONDecodeError as e:
        print(f"✗ JSON parse error in data.js: {e}")
        return False

    # Update forecast block
    # Build forecast structure matching the existing schema
    # We'll use the existing historical data (if present) and add new forecast

    existing_forecast = obj.get('forecast', {})
    existing_hist_labels = existing_forecast.get('hist_labels', [])
    existing_hist = existing_forecast.get('hist', [])

    # Determine base FY tag (latest complete FY from offtake)
    offtake = obj.get('offtake', {})
    fy_tags_str = offtake.get('fy_tags', [])
    base_tag = fy_tags_str[-1].upper() if fy_tags_str else 'FY26'

    # Compute base actual from offtake (sum of last complete FY)
    base_actual = 0
    if offtake.get('monthly'):
        # Assume last 12 months in offtake.monthly correspond to last complete FY
        # This is approximate; better would be to filter by tag
        base_actual = r2(sum(offtake.get('monthly', [])[-12:]) or 0)

    if base_actual == 0:
        # Fallback to historical or estimate
        base_actual = existing_forecast.get('fy26_actual', 0)

    # Build new forecast block
    new_forecast = {
        'hist_labels': existing_hist_labels,
        'hist': existing_hist,
        'fc_labels': forecast_data['months'],
        'fc': forecast_data['values'],
        'base_fy_tag': base_tag,
        'target_fy_tag': forecast_data['fy_tag'],
        'fy26_actual': base_actual,
        'fy27_forecast': r2(sum(forecast_data['values'])),
        'growth_assumption_pct': r2(
            (sum(forecast_data['values']) / base_actual - 1) * 100
        ) if base_actual > 0 else None,
        'method': f"{forecast_data['fy_tag']} Q2 (Sep-Nov) consensus forecast from "
                  f"build_mapping_forecast.py + generate_facewash_forecast.py + generate_shampoo_forecast.py. "
                  f"Sep ₹{forecast_data['total_cr']:.2f} Cr baseline + PSR uplift projections."
    }

    # Preserve any diagnostics that existed
    if 'diagnostics' in existing_forecast:
        new_forecast['diagnostics'] = existing_forecast['diagnostics']

    obj['forecast'] = new_forecast

    # Write back to data.js
    new_txt = "window.DASH = " + json.dumps(obj, indent=1, ensure_ascii=False) + ";\n"

    try:
        datajs_path.write_text(new_txt, encoding='utf-8')
        print(f"✓ Updated {datajs_path}")
        return True
    except Exception as e:
        print(f"✗ Could not write {datajs_path}: {e}")
        return False

def main():
    ap = argparse.ArgumentParser(
        description="Ingest FY27 forecast files into dashboard data.js"
    )
    ap.add_argument("--forecast-xlsx", default="exports/Combined_MT_Forecast_Q2_FY27.xlsx",
                    help="Path to Combined_MT_Forecast_Q2_FY27.xlsx")
    ap.add_argument("--data-js", default="dashboard/data.js",
                    help="Path to output data.js")
    args = ap.parse_args()

    xlsx_path = Path(args.forecast_xlsx)
    datajs_path = Path(args.data_js)

    print("=" * 80)
    print("INGESTING FY27 FORECAST INTO DASHBOARD")
    print("=" * 80)

    if not xlsx_path.exists():
        print(f"✗ Forecast file not found: {xlsx_path}")
        return 1

    if not datajs_path.exists():
        print(f"✗ Data.js file not found: {datajs_path}")
        return 1

    # Extract forecast data
    forecast_data = extract_forecast_from_xlsx(xlsx_path)
    if not forecast_data:
        return 1

    print(f"\n[FORECAST SUMMARY]")
    print(f"  FY Tag: {forecast_data['fy_tag']}")
    print(f"  Months: {', '.join(forecast_data['months'])}")
    print(f"  Total Q2: ₹{forecast_data['total_cr']:.2f} Cr")

    # Update data.js
    print(f"\n[UPDATING DATA.JS]")
    if not update_forecast_block_in_datajs(datajs_path, forecast_data):
        return 1

    print(f"\n{'=' * 80}")
    print(f"✓ FORECAST INGESTION COMPLETE")
    print(f"{'=' * 80}")
    print(f"\nNext: Open dashboard/index.html in browser and verify Forecast tab")
    print(f"      shows FY27 Q2 data (Sep-Nov) with updated values.")

    return 0

if __name__ == "__main__":
    exit(main())
