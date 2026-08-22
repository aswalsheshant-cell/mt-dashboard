#!/usr/bin/env python3
"""
Transform raw July 2026 transaction data into dashboard schema.

Reads raw primary invoice data from MTEB2BMTDPrimaryJuly26._2.xlsx
and maps columns to the build_dashboard_data.py expected schema:
  - Month: "Jul" (extracted from invoice date)
  - FY: "FY27" (derived from month)
  - Brand: Division Desc. (Mamaearth/Honasa normalized)
  - Zone: extracted from ship-to state (mapped via zone master)
  - Channel: chain name (from Bill to Customer or hardcoded for direct)
  - Inv. Net value(LOC): invoice net value in Lakh
  - Total MRP sales: MRP × Qty
  - Inv Qty: invoice quantity
  - category: Category (normalized)
  - sub_category: extracted if available
  - range: Product range (from description parsing or master)
  - net_content: net content (from product master if available)
  - Description: Description
  - EAN No.: EAN No.
  - Chain name for Dashboard: chain name or direct indicator

Output: cleaned_july_primary.xlsx with columns matching build_dashboard_data.py schema
"""
from pathlib import Path
import pandas as pd
import re
from datetime import datetime

# Zone mapping: state -> zone (simplified; refine with business data)
STATE_TO_ZONE = {
    # North
    "Punjab": "North", "Haryana": "North", "Himachal Pradesh": "North",
    "Jammu & Kashmir": "North", "Uttarakhand": "North", "Uttar Pradesh": "North",
    "Delhi": "North",
    # South
    "Telangana": "South", "Andhra Pradesh": "South", "Karnataka": "South",
    "Tamil Nadu": "South", "Kerala": "South",
    # West
    "Gujarat": "West", "Maharashtra": "West", "Rajasthan": "West",
    "Goa": "West",
    # Central (new 6-zone structure)
    "Madhya Pradesh": "Central", "Chhattisgarh": "Central",  # Vidarbha (Maharashtra) stays West above
    # East
    "West Bengal": "East", "Assam": "East", "Odisha": "East", "Bihar": "East", "Jharkhand": "East",
}

# Brand canonicalization
BRAND_MAP = {
    "Mamaearth": "Mamaearth",
    "Honasa": "Honasa",
    "Mamaearth Hydrogel": "Mamaearth",
}

def extract_state_from_shiptoname(ship_to_name):
    """Heuristic: extract state abbreviation from ship-to name if present."""
    if not ship_to_name:
        return None
    # Common patterns: "City, State" or "Chain - State"
    parts = str(ship_to_name).split(",")
    if len(parts) > 1:
        return parts[-1].strip()
    return None

def map_zone(state_or_name):
    """Map state/region to zone."""
    if not state_or_name:
        return "Unknown"
    state_norm = str(state_or_name).strip()
    return STATE_TO_ZONE.get(state_norm, "Unknown")

def canonicalize_brand(div_desc):
    """Normalize brand from Division Desc."""
    if not div_desc:
        return "Unknown"
    brand = str(div_desc).strip()
    return BRAND_MAP.get(brand, brand)

def canonicalize_category(cat):
    """Normalize category."""
    if not cat:
        return "Other"
    cat_str = str(cat).strip()
    # Map known categories
    if cat_str.lower() in ["hair", "haircare"]:
        return "Hair"
    if cat_str.lower() in ["face", "skincare", "facial"]:
        return "Face"
    if cat_str.lower() in ["body", "bodycare"]:
        return "Body"
    return cat_str

def transform_july_data(input_file, output_file):
    """
    Transform raw July invoice data to dashboard schema.

    Parameters:
        input_file: path to MTEB2BMTDPrimaryJuly26._2.xlsx
        output_file: path to write cleaned_july_primary.xlsx
    """
    print(f"Reading {input_file}...")

    # Read the MTD-Primary-July'26 sheet (transaction-level data)
    try:
        df = pd.read_excel(input_file, sheet_name="MTD-Primary-July'26.", header=0)
    except Exception as e:
        print(f"Error reading sheet: {e}")
        return None

    print(f"Loaded {len(df)} rows from transaction sheet")

    # Required columns from raw file
    required_cols = {
        "Inv. Date": "date",
        "Ship-To Name": "ship_to",
        "Bill to customer": "bill_to",
        "Division Desc.": "division",
        "Category": "category",
        "EAN No.": "ean",
        "Description": "description",
        "MRP": "mrp",
        "Inv Qty": "qty",
        "Inv. Net value(LOC)": "nsv",  # Already in Lakh
    }

    # Check for column presence (case-insensitive matching)
    col_map = {}
    df_cols_lower = {c.lower(): c for c in df.columns}

    for required, alias in required_cols.items():
        key_lower = required.lower()
        if key_lower in df_cols_lower:
            col_map[alias] = df_cols_lower[key_lower]
        else:
            print(f"⚠️  Missing expected column: {required}")

    # Create working dataframe with mapped columns
    work_df = pd.DataFrame()
    for alias, actual_col in col_map.items():
        if actual_col in df.columns:
            work_df[alias] = df[actual_col]

    if work_df.empty:
        print("❌ No recognized columns found in input file")
        return None

    print(f"Extracted {len(work_df)} rows with {len(work_df.columns)} mapped columns")

    # Derive dashboard schema columns
    work_df["Month"] = "Jul"  # All July data
    work_df["FY"] = "FY27"    # July -> FY27

    # Brand: from Division Desc.
    work_df["brand"] = work_df.get("division", "Unknown").apply(canonicalize_brand)

    # Zone: from Ship-To Name heuristic or default
    work_df["Zone"] = work_df.get("ship_to", "").apply(lambda x: map_zone(extract_state_from_shiptoname(x)))

    # Channel / Chain: from Bill-to-Customer (simplified)
    # Real implementation would use a chain master
    work_df["Channel"] = work_df.get("bill_to", "Direct").apply(
        lambda x: str(x).strip()[:40] if x else "Direct"
    )

    # Rename to dashboard schema
    schema_map = {
        "nsv": "Inv. Net value(LOC)",
        "qty": "Inv Qty",
        "mrp": "MRP",
        "category": "category",
        "ean": "EAN No.",
        "description": "Description",
    }

    for src, tgt in schema_map.items():
        if src in work_df.columns:
            work_df[tgt] = work_df[src]

    # Add derived columns (not in raw data, but needed for completeness)
    work_df["Total MRP sales"] = (work_df.get("MRP", 0) * work_df.get("Inv Qty", 0)).fillna(0)
    work_df["sub_category"] = ""  # Placeholder
    work_df["range"] = ""          # Placeholder (would need product master)
    work_df["net_content"] = ""    # Placeholder (would need product master)
    work_df["Chain name for Dashboard (or Chain name)"] = work_df.get("Channel", "")

    # Final schema columns for output
    output_schema = [
        "Month", "FY", "brand", "Zone", "Channel",
        "Inv. Net value(LOC)", "Total MRP sales", "Inv Qty",
        "category", "sub_category", "range", "net_content",
        "Description", "EAN No.", "Chain name for Dashboard (or Chain name)"
    ]

    output_df = pd.DataFrame()
    for col in output_schema:
        if col in work_df.columns:
            output_df[col] = work_df[col]
        else:
            output_df[col] = ""

    # Clean nulls
    for col in output_df.columns:
        output_df[col] = output_df[col].fillna("")

    print(f"\nWriting {len(output_df)} transformed rows to {output_file}...")
    output_df.to_excel(output_file, sheet_name="Dump", index=False)

    print("✓ Transformation complete")
    print(f"  Rows: {len(output_df)}")
    print(f"  Columns: {len(output_df.columns)}")
    print(f"  Brands: {output_df['brand'].unique().tolist()}")
    print(f"  Zones: {output_df['Zone'].unique().tolist()}")
    print(f"  FY coverage: {output_df['FY'].unique().tolist()}")

    return output_df

if __name__ == "__main__":
    import sys
    import argparse

    ap = argparse.ArgumentParser(description="Transform raw July 2026 primary data to dashboard schema")
    ap.add_argument("--input", default="scripts/../dashboard/../PowerBI/RawDataFolders/MTEB2BMTDPrimaryJuly26._2.xlsx",
                    help="Input raw primary file (MTEB2BMTDPrimaryJuly26._2.xlsx)")
    ap.add_argument("--output", default="scripts/../dashboard/../scripts/../dashboard/cleaned_july_primary.xlsx",
                    help="Output transformed file")

    args = ap.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        # Try alternate location
        alt_paths = [
            Path("MTEB2BMTDPrimaryJuly26._2.xlsx"),
            Path("/tmp/claude-0/-home-user-mt-dashboard/6971cc9a-1fdd-5f77-a6c3-8e4fd8247ff9/scratchpad/july_data") / "6cd317fe-MTEB2BMTDPrimaryJuly26._2.xlsx",
        ]
        for alt in alt_paths:
            if alt.exists():
                input_path = alt
                break

    if not input_path.exists():
        print(f"❌ Input file not found: {input_path}")
        sys.exit(1)

    transform_july_data(input_path, output_path)
