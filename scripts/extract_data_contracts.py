#!/usr/bin/env python3
"""
Extract Data Contracts from data.js → Normalized CSV Tables for Power BI

Parses the pre-aggregated dashboard data.js and exports normalized CSV tables
suitable for Power Query ingestion in Power BI Desktop.

Outputs to PowerBI/ExportData/:
  - offtake.csv (store-level sell-out by zone/chain/month)
  - primary.csv (distributor-level sell-in by chain/brand/month)
  - pnl_expenses.csv (P&L expense by chain/head/month)
  - detail_articles.csv (top 40K articles with metadata)
  - forecast_targets.csv (FY targets by chain/brand)
  - universe.csv (store universe & coverage by chain/zone)
  - tot_mapping.csv (TOT% by chain for MRP reverse-calc)

Usage:
    python scripts/extract_data_contracts.py --src dashboard/data.js --out PowerBI/ExportData/

Exit codes:
    0 = Success (all CSVs written)
    1 = File not found or parse error
    2 = Output directory error
"""
from __future__ import annotations
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd


def log(level: str, msg: str):
    """Print timestamped log message."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sym = {"INFO": "ℹ", "OK": "✓", "WARN": "⚠", "ERROR": "✗", "DEBUG": "→"}[level]
    print(f"[{ts}] {sym} {msg}")


def load_data_js(path: Path) -> dict:
    """Load dashboard/data.js and return parsed JSON object."""
    log("INFO", f"Loading {path}")
    try:
        with open(path) as f:
            content = f.read()
            # Remove 'window.DASH = ' prefix and trailing semicolon
            start = content.index('{')
            end = content.rindex('}') + 1
            json_str = content[start:end]
            data = json.loads(json_str)
        log("OK", f"Parsed {path} ({len(content) / 1024 / 1024:.1f} MB)")
        return data
    except FileNotFoundError:
        log("ERROR", f"File not found: {path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        log("ERROR", f"JSON parse error: {e}")
        sys.exit(1)


def extract_offtake_csv(data: dict, out_dir: Path) -> None:
    """
    Extract offtake data (zone/chain/month grain) from data['offtake'].
    Enhanced to include pipeline health metrics (conversion, flow gap, units).
    Outputs to offtake.csv
    """
    offtake_dict = data.get('offtake', {})
    if not offtake_dict:
        log("WARN", "Offtake block missing or empty")
        return

    rows = []

    # Extract FY26/FY27 monthly data by zone with enhanced metrics
    for fy in ['fy26', 'fy27']:
        monthly_key = f'zone_monthly_{fy}'
        if monthly_key in offtake_dict:
            zone_monthly = offtake_dict[monthly_key]
            for zone, months_dict in zone_monthly.items():
                for month, month_data in months_dict.items():
                    # Handle both old format (direct NSV) and new format (full month_data dict)
                    if isinstance(month_data, dict):
                        rows.append({
                            'Zone': zone,
                            'Month': month,
                            'FY': fy.upper(),
                            'Offtake_NSV_Lakh': month_data.get('offtake_cr', 0),
                            'Primary_NSV_Lakh': month_data.get('primary_cr', 0),
                            'Pipeline_Gap_Lakh': month_data.get('flow_gap_cr', 0),
                            'Conversion_Pct': month_data.get('conversion_pct', 0),
                            'Units_Sold': month_data.get('units_sold', 0),
                            'Chain_Count': month_data.get('chain_count', 0),
                            'State_Count': month_data.get('state_count', 0),
                        })
                    else:
                        # Fallback for legacy data format
                        rows.append({
                            'Zone': zone,
                            'Month': month,
                            'FY': fy.upper(),
                            'Offtake_NSV_Lakh': month_data if month_data else 0,
                            'Primary_NSV_Lakh': 0,
                            'Pipeline_Gap_Lakh': 0,
                            'Conversion_Pct': 0,
                            'Units_Sold': 0,
                            'Chain_Count': 0,
                            'State_Count': 0,
                        })

    # Extract by-chain data (list of {name, value} dicts)
    by_chain = offtake_dict.get('by_chain', [])
    if isinstance(by_chain, list):
        for item in by_chain:
            chain_name = item.get('name', '')
            value = item.get('value', 0)
            rows.append({
                'Zone': '',
                'Month': 'All',
                'FY': 'FY26/27',
                'Chain': chain_name,
                'NSV_Lakh': value,
            })

    if rows:
        df = pd.DataFrame(rows)
        out_path = out_dir / 'offtake.csv'
        df.to_csv(out_path, index=False)
        log("OK", f"Wrote {len(df)} offtake records to {out_path.name}")
    else:
        log("WARN", "No offtake data extracted")


def extract_primary_csv(data: dict, out_dir: Path) -> None:
    """
    Extract primary data (sell-in by FY) from data['primary'].
    Outputs to primary.csv
    """
    primary_dict = data.get('primary', {})
    if not primary_dict:
        log("WARN", "Primary block missing or empty")
        return

    rows = []

    # Summary totals by FY (simple aggregate)
    for fy in ['fy25', 'fy26', 'fy27']:
        nsv_key = f'nsv_{fy}'
        mrp_key = f'mrp_{fy}'
        if nsv_key in primary_dict:
            rows.append({
                'FY': fy.upper(),
                'NSV_Lakh': primary_dict.get(nsv_key, 0),
                'MRP_Sales_Lakh': primary_dict.get(mrp_key, 0),
                'Chain_Count': primary_dict.get('n_chains', 0),
                'Brand_Count': primary_dict.get('n_brands', 0),
            })

    if rows:
        df = pd.DataFrame(rows)
        out_path = out_dir / 'primary.csv'
        df.to_csv(out_path, index=False)
        log("OK", f"Wrote {len(df)} primary FY records to {out_path.name}")
    else:
        log("WARN", "No primary data extracted")


def extract_pnl_csv(data: dict, out_dir: Path) -> None:
    """
    Extract P&L expenses (chain/expense_head/month) from data['pnl_expenses'].
    Outputs to pnl_expenses.csv
    """
    pnl_dict = data.get('pnl_expenses', {})
    if not pnl_dict:
        log("WARN", "P&L block missing or empty")
        return

    rows = []

    # Extract chain-level P&L by expense head
    by_chain = pnl_dict.get('by_chain', {})
    for chain, expenses in by_chain.items():
        for expense_head, amount_lakhs in expenses.items():
            rows.append({
                'Chain': chain,
                'Expense_Head': expense_head,
                'Amount_Lakh': amount_lakhs if amount_lakhs else 0,
            })

    if rows:
        df = pd.DataFrame(rows)
        out_path = out_dir / 'pnl_expenses.csv'
        df.to_csv(out_path, index=False)
        log("OK", f"Wrote {len(df)} P&L records to {out_path.name}")
    else:
        log("WARN", "No P&L data extracted")


def extract_detail_articles_csv(data: dict, out_dir: Path) -> None:
    """
    Extract top 40K detail articles from data['detail_records'].
    Outputs to detail_articles.csv
    """
    detail_records = data.get('detail_records', [])
    if not detail_records:
        log("WARN", "Detail records missing or empty")
        return

    rows = []
    for rec in detail_records:
        rows.append({
            'EAN': rec.get('EAN', ''),
            'Article': rec.get('Article', ''),
            'Brand': rec.get('Brand', ''),
            'Category': rec.get('Category', ''),
            'SubCategory': rec.get('SubCategory', ''),
            'PackSize': rec.get('PackSize', ''),
            'Channel': rec.get('Channel', ''),
            'FY': rec.get('FY', ''),
            'Month': rec.get('Month', ''),
            'NSV_Lakh': rec.get('NSV', 0),
            'Qty': rec.get('Qty', 0),
        })

    if rows:
        df = pd.DataFrame(rows)
        out_path = out_dir / 'detail_articles.csv'
        df.to_csv(out_path, index=False)
        log("OK", f"Wrote {len(df)} detail articles to {out_path.name}")


def extract_forecast_csv(data: dict, out_dir: Path) -> None:
    """
    Extract forecast targets from data['forecast'].
    Outputs to forecast_targets.csv
    """
    forecast_dict = data.get('forecast', {})
    if not forecast_dict:
        log("WARN", "Forecast block missing or empty")
        return

    rows = []

    # Simple FY totals
    rows.append({
        'FY': 'FY26',
        'Actual_NSV_Lakh': forecast_dict.get('fy26_actual', 0),
    })
    rows.append({
        'FY': 'FY27',
        'Forecast_NSV_Lakh': forecast_dict.get('fy27_forecast', 0),
        'Growth_Assumption_Pct': forecast_dict.get('growth_assumption_pct', 0),
    })

    if rows:
        df = pd.DataFrame(rows)
        out_path = out_dir / 'forecast_targets.csv'
        df.to_csv(out_path, index=False)
        log("OK", f"Wrote {len(df)} forecast records to {out_path.name}")
    else:
        log("WARN", "No forecast data extracted")


def extract_universe_csv(data: dict, out_dir: Path) -> None:
    """
    Extract store universe from data['universe'].
    Enhanced to include zone and store-type breakdown for distribution analysis.
    Outputs to universe.csv
    """
    universe_dict = data.get('universe', {})
    if not universe_dict:
        log("WARN", "Universe block missing or empty")
        return

    rows = []

    # Total universe summary
    rows.append({
        'Grain': 'Total',
        'Chain': 'ALL',
        'Zone': '',
        'Store_Type': '',
        'Store_Count': universe_dict.get('total_stores', 0),
        'Active_Stores': universe_dict.get('active_stores', 0),
    })

    # By chain (can be list or dict)
    by_chain = universe_dict.get('by_chain', [])
    if isinstance(by_chain, list):
        for item in by_chain:
            if isinstance(item, dict):
                chain_name = item.get('name', '')
                store_count = item.get('value', 0)
            else:
                chain_name = ''
                store_count = 0
            if chain_name:
                rows.append({
                    'Grain': 'By_Chain',
                    'Chain': chain_name,
                    'Zone': '',
                    'Store_Type': '',
                    'Store_Count': store_count,
                    'Active_Stores': store_count,
                })
    elif isinstance(by_chain, dict):
        for chain, count in by_chain.items():
            rows.append({
                'Grain': 'By_Chain',
                'Chain': chain,
                'Zone': '',
                'Store_Type': '',
                'Store_Count': count,
                'Active_Stores': count,
            })

    # By zone (NEW - for distribution % calculation)
    by_zone = universe_dict.get('by_zone', {})
    if isinstance(by_zone, dict):
        for zone, count in by_zone.items():
            rows.append({
                'Grain': 'By_Zone',
                'Chain': '',
                'Zone': zone,
                'Store_Type': '',
                'Store_Count': count,
                'Active_Stores': count,
            })
    elif isinstance(by_zone, list):
        for item in by_zone:
            if isinstance(item, dict):
                zone_name = item.get('name', '')
                store_count = item.get('value', 0)
                if zone_name:
                    rows.append({
                        'Grain': 'By_Zone',
                        'Chain': '',
                        'Zone': zone_name,
                        'Store_Type': '',
                        'Store_Count': store_count,
                        'Active_Stores': store_count,
                    })

    # By store type (NEW - for productivity analysis)
    by_storetype = universe_dict.get('by_storetype', {})
    if isinstance(by_storetype, dict):
        for storetype, count in by_storetype.items():
            rows.append({
                'Grain': 'By_StoreType',
                'Chain': '',
                'Zone': '',
                'Store_Type': storetype,
                'Store_Count': count,
                'Active_Stores': count,
            })
    elif isinstance(by_storetype, list):
        for item in by_storetype:
            if isinstance(item, dict):
                storetype_name = item.get('name', '')
                store_count = item.get('value', 0)
                if storetype_name:
                    rows.append({
                        'Grain': 'By_StoreType',
                        'Chain': '',
                        'Zone': '',
                        'Store_Type': storetype_name,
                        'Store_Count': store_count,
                        'Active_Stores': store_count,
                    })

    if rows:
        df = pd.DataFrame(rows)
        out_path = out_dir / 'universe.csv'
        df.to_csv(out_path, index=False)
        log("OK", f"Wrote {len(df)} universe records to {out_path.name}")


def extract_tot_csv(data: dict, out_dir: Path) -> None:
    """
    Extract TOT% (Trade Offer Terms) by chain from data['tot'].
    Outputs to tot_mapping.csv
    """
    tot_dict = data.get('tot', {})
    if not tot_dict:
        log("WARN", "TOT block missing or empty")
        return

    rows = []

    # Blended TOT%
    blended = tot_dict.get('blended_tot_pct', 0)
    rows.append({
        'Chain': 'BLENDED',
        'TOT_Pct': blended,
    })

    # By chain (can be list or dict)
    by_chain = tot_dict.get('by_chain', [])
    if isinstance(by_chain, list):
        for item in by_chain:
            if isinstance(item, dict):
                rows.append({
                    'Chain': item.get('name', ''),
                    'TOT_Pct': item.get('value', 0),
                })
    elif isinstance(by_chain, dict):
        for chain, pct in by_chain.items():
            rows.append({
                'Chain': chain,
                'TOT_Pct': pct if pct else 0,
            })

    if rows:
        df = pd.DataFrame(rows)
        out_path = out_dir / 'tot_mapping.csv'
        df.to_csv(out_path, index=False)
        log("OK", f"Wrote {len(df)} TOT% records to {out_path.name}")


def main():
    ap = argparse.ArgumentParser(
        description="Extract normalized CSV tables from dashboard data.js for Power BI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract CSVs to PowerBI/ExportData/
  python scripts/extract_data_contracts.py --src dashboard/data.js --out PowerBI/ExportData/

  # Custom output directory
  python scripts/extract_data_contracts.py --src dashboard/data.js --out /tmp/pbi-export/
        """
    )
    ap.add_argument("--src", type=Path, default=Path("dashboard/data.js"),
                    help="Input data.js path (default: dashboard/data.js)")
    ap.add_argument("--out", type=Path, default=Path("PowerBI/ExportData"),
                    help="Output directory for CSVs (default: PowerBI/ExportData)")

    args = ap.parse_args()

    log("INFO", "═" * 70)
    log("INFO", "Data Contract Extraction for Power BI")
    log("INFO", "═" * 70)
    log("INFO", f"Source: {args.src}")
    log("INFO", f"Output: {args.out}")

    # Create output directory
    args.out.mkdir(parents=True, exist_ok=True)
    log("OK", f"Output directory ready: {args.out}")

    # Load data.js
    data = load_data_js(args.src)

    # Extract all tables
    log("INFO", "Extracting data contracts...")
    extract_offtake_csv(data, args.out)
    extract_primary_csv(data, args.out)
    extract_pnl_csv(data, args.out)
    extract_detail_articles_csv(data, args.out)
    extract_forecast_csv(data, args.out)
    extract_universe_csv(data, args.out)
    extract_tot_csv(data, args.out)

    log("INFO", "═" * 70)
    log("OK", "Data extraction complete!")
    log("INFO", f"All CSVs ready in {args.out}/")
    log("INFO", "═" * 70)
    sys.exit(0)


if __name__ == "__main__":
    main()
