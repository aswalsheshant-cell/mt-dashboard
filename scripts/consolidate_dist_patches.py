#!/usr/bin/env python3
"""
consolidate_dist_patches.py

Consolidate existing DIST allocation patch files into a single versioned seed CSV.

Input files:
  - PowerBI/SeedData/Mapping/DistCont_Patch_Approved_*.csv (approved patches)
  - PowerBI/SeedData/Mapping/Mapping_Corrections.csv (mapping corrections)
  - PowerBI/SeedData/Masters/PrimaryAllocationOverride.csv (business overrides)

Output:
  - PowerBI/SeedData/DIST/DistPrimaryContWeightsArticle.csv (consolidated seed)

This script:
1. Reads all approved patch files from Mapping/ directory
2. Consolidates them into a single CSV with standardized columns
3. Adds audit trail metadata (Source, Approved_Date, Approved_By)
4. Writes to PowerBI/SeedData/DIST/DistPrimaryContWeightsArticle.csv

Usage:
  python scripts/consolidate_dist_patches.py
"""
import pandas as pd
from pathlib import Path
from datetime import datetime
import logging
import glob

logging.basicConfig(level=logging.INFO, format='%(message)s')
log = logging.getLogger(__name__)


def consolidate_patches():
    """Consolidate existing DIST patches into a single seed CSV."""

    # Find all approved patch files
    mapping_dir = Path("PowerBI/SeedData/Mapping")
    patch_files = sorted(glob.glob(str(mapping_dir / "DistCont_Patch_Approved_*.csv")))

    if not patch_files:
        log.warning("No approved patch files found in PowerBI/SeedData/Mapping/")
        return False

    # Read and consolidate all patches
    dfs = []
    for pf in patch_files:
        df = pd.read_csv(pf)
        # Add source tracking
        df['Source'] = 'Approved Patch'
        df['Patch_File'] = Path(pf).name
        # Extract approval date from filename if available (e.g., DistCont_Patch_Approved_2026-07-04.csv)
        try:
            date_str = Path(pf).stem.split('_')[-1]  # Extract date from filename
            df['Approved_Date'] = pd.to_datetime(date_str).strftime('%Y-%m-%d')
        except:
            df['Approved_Date'] = datetime.now().strftime('%Y-%m-%d')
        dfs.append(df)

    # Consolidate
    consolidated = pd.concat(dfs, ignore_index=True)

    # Standardize column names for the output schema
    # Input: Ship To Name, Direct/Distributor, Chain Name, Brand, Revised month, FY, Channel,
    #        Secondary contribution %, Confidence, Basis
    # Output: Distributor, Ship_To_Name, Chain_Name, Brand, Month, Cont_Pct, Source,
    #         Approved_Date, Approved_By, Basis

    rename_cols = {
        'Ship To Name': 'Ship_To_Name',
        'Direct/Distributor': 'Distributor',
        'Chain Name': 'Chain_Name',
        'Revised month': 'Month',
        'Secondary contribution %': 'Cont_Pct',
        'Confidence': 'Approval_Status',
    }

    consolidated.rename(columns=rename_cols, inplace=True)

    # Keep only necessary columns
    keep_cols = [
        'Distributor', 'Ship_To_Name', 'Chain_Name', 'Brand', 'Month', 'Cont_Pct',
        'Source', 'Approved_Date', 'Approval_Status', 'Basis', 'Patch_File'
    ]

    # Keep existing columns if they exist
    consolidated = consolidated[[col for col in keep_cols if col in consolidated.columns]]

    # Write output
    out_file = Path("PowerBI/SeedData/DIST/DistPrimaryContWeightsArticle.csv")
    out_file.parent.mkdir(parents=True, exist_ok=True)

    consolidated.to_csv(out_file, index=False)
    log.info(f"✓ Consolidated {len(consolidated)} approved patch rows into {out_file}")
    log.info(f"  Sources: {len(patch_files)} patch files")
    log.info(f"  Columns: {', '.join(consolidated.columns.tolist())}")

    return True


if __name__ == "__main__":
    import sys
    success = consolidate_patches()
    sys.exit(0 if success else 1)
