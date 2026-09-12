#!/usr/bin/env python3
"""
Ingest Primary_ShipTo_Monthly.csv into data_master.json

Parses chain-level primary sales data and extracts:
1. by_chain_offtake: All chains by FY (MT + EB2B)
2. reliance_bc: Reliance Brand Counter data (separate, excluded from totals)

USAGE:
  python scripts/ingest_primary_csv.py --csv <path> --master <path> --output <path>

  Default:
    python scripts/ingest_primary_csv.py
    (reads: PowerBI/RawDataFolders/Primary_ShipTo_Monthly/Primary_ShipTo_FY25-26_to_May26.csv)
    (updates: data_master.json)
"""
from __future__ import annotations
import csv
import json
import argparse
from pathlib import Path
from collections import defaultdict
from datetime import datetime


def month_to_fy(month_label: str) -> str | None:
    """
    Convert month label (e.g., 'Apr-24') to FY tag (e.g., 'fy25')
    using THE ONE FY RULE:
      - Apr-Dec of year Y → FY(Y+1)
      - Jan-Mar of year Y → FY(Y)
    """
    try:
        parts = month_label.split('-')
        if len(parts) != 2:
            return None

        month_abbr = parts[0].strip()
        year = int(parts[1])

        # Indian FY: Apr-Dec of year Y = FY(Y+1), Jan-Mar of year Y = FY(Y)
        if month_abbr in ['Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']:
            return f"fy{year + 1}"
        elif month_abbr in ['Jan', 'Feb', 'Mar']:
            return f"fy{year}"
        else:
            return None
    except (ValueError, IndexError):
        return None


def ingest_primary_csv(csv_path: str, master_path: str) -> dict:
    """
    Parse Primary_ShipTo_Monthly.csv (detail-level data) and update data_master.json

    CSV structure: Month, FY Year, Chain, Zone, State, Brand, Primary NSV, ...
    - Aggregates by Chain × Month
    - Separates Reliance Brand Counter (Store Type = "Brand Counter")

    Returns:
      dict with updated master data
    """
    csv_path = Path(csv_path)
    master_path = Path(master_path)

    print(f"\n[1] Reading CSV: {csv_path}")
    if not csv_path.exists():
        print(f"  ✗ File not found: {csv_path}")
        return {}

    # Load existing data_master.json
    print(f"\n[2] Loading existing master: {master_path}")
    master = {}
    if master_path.exists():
        with open(master_path, 'r', encoding='utf-8') as f:
            master = json.load(f)
        print(f"  ✓ Loaded existing master")
    else:
        print(f"  ○ Creating new master")

    # Initialize required blocks
    master.setdefault("metadata", {})
    master.setdefault("zone_metrics_monthly", {})  # Preserve existing zone data
    master.setdefault("by_chain_offtake", {})
    master.setdefault("reliance_bc", {})

    # Parse detail-level CSV
    print(f"\n[3] Parsing detail-level CSV")
    by_chain = defaultdict(lambda: defaultdict(float))
    by_rbc = defaultdict(lambda: defaultdict(float))
    months_set = set()
    row_count = 0

    with open(csv_path, 'r', encoding='utf-8', errors='replace') as f:
        reader = csv.DictReader(f)

        for row in reader:
            row_count += 1

            # Extract fields from detail row
            chain_name = row.get('Chain', '').strip()
            fy_year_str = row.get('FY Year', '').strip()  # e.g., "FY_25-26"
            month_label = row.get('Month', '').strip()  # e.g., "May'25"
            primary_nsv_str = row.get('Primary NSV', '').strip()
            direct_distributor = row.get('Direct/Distributor', '').strip()

            # Skip empty rows
            if not chain_name or not primary_nsv_str:
                continue

            # Convert month label to FY tag
            # Month format: "May'25" → "fy26" (May-25 → fy26)
            month_for_fy = month_label.replace("'", "-")  # "May'25" → "May-25"
            fy = month_to_fy(month_for_fy)

            if not fy:
                continue

            # Standardize chain name to "Nykaa SS" if it contains FSN/Nykaa
            if 'fsn' in chain_name.lower() or 'nykaa' in chain_name.lower():
                chain_name = "Nykaa SS"

            months_set.add(month_label)

            try:
                nsv = float(primary_nsv_str)

                # Determine if this is RBC: Reliance is RBC if Store Type or other indicator
                # For now, check chain name and direct/distributor pattern
                is_reliance = 'reliance' in chain_name.lower()
                is_brand_counter = 'brand counter' in direct_distributor.lower()

                # Accumulate NSV by chain and FY
                # Note: Source data is in rupees, need to convert to Lakh (divide by 100000)
                nsv_lakh = nsv / 100000

                if is_reliance and is_brand_counter:
                    by_rbc[chain_name][fy] += nsv_lakh
                else:
                    by_chain[chain_name][fy] += nsv_lakh

            except (ValueError, TypeError):
                continue

    print(f"  ✓ Parsed {row_count} detail rows")
    print(f"  ✓ {len(by_chain)} regular chains + {len(by_rbc)} RBC entries")
    print(f"  ✓ {len(months_set)} unique months")

    # Convert to Crore (source data is in Lakh)
    LAKH_TO_CRORE = 1 / 100

    # Build by_chain_offtake block (MT + EB2B, excluding RBC)
    print(f"\n[4] Building by_chain_offtake block")
    by_chain_offtake_output = {}
    total_by_fy = defaultdict(float)

    for fy in ['fy25', 'fy26', 'fy27']:
        by_chain_offtake_output[fy] = {}
        for chain_name in sorted(by_chain.keys()):
            fy_value = by_chain[chain_name].get(fy, 0)
            if fy_value > 0:
                value_cr = round(fy_value * LAKH_TO_CRORE, 2)
                by_chain_offtake_output[fy][chain_name] = value_cr
                total_by_fy[fy] += value_cr

    master["by_chain_offtake"] = by_chain_offtake_output

    print(f"  ✓ FY25: ₹{total_by_fy['fy25']:.2f} Cr ({len(by_chain_offtake_output.get('fy25', {}))} chains)")
    print(f"  ✓ FY26: ₹{total_by_fy['fy26']:.2f} Cr ({len(by_chain_offtake_output.get('fy26', {}))} chains)")
    print(f"  ✓ FY27: ₹{total_by_fy['fy27']:.2f} Cr ({len(by_chain_offtake_output.get('fy27', {}))} chains)")

    # Build reliance_bc block (Reliance Brand Counter, separate)
    print(f"\n[5] Building reliance_bc block")
    reliance_bc_output = {
        "is_brand_counter": True,
        "include_in_overall_offtake": False,  # Critical: exclude from offtake totals
        "months": sorted(months_set),
    }

    total_rbc_by_fy = defaultdict(float)

    for fy in ['fy25', 'fy26', 'fy27']:
        rbc_by_chain = {}
        fy_total = 0

        for chain_name in sorted(by_rbc.keys()):
            fy_value = by_rbc[chain_name].get(fy, 0)
            if fy_value > 0:
                value_cr = round(fy_value * LAKH_TO_CRORE, 2)
                rbc_by_chain[chain_name] = value_cr
                fy_total += value_cr

        if fy_total > 0:
            reliance_bc_output[f"total_{fy}"] = round(fy_total, 2)
            reliance_bc_output[f"by_chain_{fy}"] = rbc_by_chain
            total_rbc_by_fy[fy] = fy_total

    master["reliance_bc"] = reliance_bc_output

    if total_rbc_by_fy['fy25'] > 0:
        print(f"  ✓ FY25 RBC: ₹{total_rbc_by_fy['fy25']:.2f} Cr")
    if total_rbc_by_fy['fy26'] > 0:
        print(f"  ✓ FY26 RBC: ₹{total_rbc_by_fy['fy26']:.2f} Cr")
    if total_rbc_by_fy['fy27'] > 0:
        print(f"  ✓ FY27 RBC: ₹{total_rbc_by_fy['fy27']:.2f} Cr")

    # Update metadata
    print(f"\n[6] Updating metadata")
    master["metadata"]["status"] = "INGEST_PRIMARY_CSV"
    master["metadata"]["ingestion_date"] = datetime.now().isoformat()
    master["metadata"]["source_csv"] = str(csv_path)
    master["metadata"]["title"] = master["metadata"].get("title", "Modern Trade Leadership Dashboard")

    # Save updated data_master.json
    print(f"\n[7] Writing updated master: {master_path}")
    with open(master_path, 'w', encoding='utf-8') as f:
        json.dump(master, f, indent=2, ensure_ascii=False)
    print(f"  ✓ Written successfully")

    # Summary
    print(f"\n" + "=" * 80)
    print("INGESTION COMPLETE")
    print("=" * 80)

    print(f"""
Summary:
  ✓ by_chain_offtake:  {len(by_chain)} chains ingested
  ✓ reliance_bc:       {len(by_rbc)} RBC entries (separate, excluded from totals)
  ✓ Metadata:          Updated with ingestion timestamp

FY26 Totals (Post-Ingestion):
  • MT + EB2B:         ₹{total_by_fy['fy26']:.2f} Cr (from by_chain_offtake)
  • RBC:               ₹{total_rbc_by_fy['fy26']:.2f} Cr (separate block)
  • Combined:          ₹{total_by_fy['fy26'] + total_rbc_by_fy['fy26']:.2f} Cr

Next Step:
  1. Update scripts/sync_data_js.py to use chain data
  2. Regenerate dashboard/data.js
  3. Test dashboard rendering
  4. Commit and push
""")

    return master


def main():
    parser = argparse.ArgumentParser(
        description="Ingest Primary_ShipTo_Monthly.csv into data_master.json"
    )
    parser.add_argument(
        "--csv",
        default="PowerBI/RawDataFolders/Primary_ShipTo_Monthly/Primary_ShipTo_FY25-26_to_May26.csv",
        help="Path to Primary CSV"
    )
    parser.add_argument(
        "--master",
        default="data_master.json",
        help="Path to data_master.json"
    )
    args = parser.parse_args()

    print("=" * 80)
    print("PRIMARY CSV INGESTION")
    print("=" * 80)

    ingest_primary_csv(args.csv, args.master)
    return 0


if __name__ == "__main__":
    exit(main())
