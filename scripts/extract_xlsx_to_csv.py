#!/usr/bin/env python3
"""
extract_xlsx_to_csv.py
Extract XLSX seed data files into CSV format for versioning in git.

This script converts the following XLSX files into CSV seeds when available in --src:
  - Primary_FY202426_10.xlsx -> PowerBI/SeedData/Primary/Primary_FY202426_10.csv
  - Dist_primary_cont_based_on_secondary_MOM.xlsx (Sheet2) -> PowerBI/SeedData/DIST/ChainAllocationWeights.csv
  - Dist_primary_cont_based_on_secondary_MOM.xlsx ("Dist Primary Conv to Chain Art") -> PowerBI/SeedData/DIST/DistPrimaryContWeightsArticle.csv
  - Universe MT.xlsx -> PowerBI/SeedData/Distribution/UniverseMT.csv
  - Promo Master -MT.xlsx -> PowerBI/SeedData/Promo/PromoMaster.csv

Usage:
  python scripts/extract_xlsx_to_csv.py --src <path> [--out <path>]

The --src directory should contain the XLSX source files. CSV seeds are written to
PowerBI/SeedData/* (or override with --out <path>).
"""
import argparse
import sys
from pathlib import Path
import pandas as pd
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
log = logging.getLogger(__name__)


def extract_primary(src_dir, out_dir):
    """Extract Primary_FY202426_10.xlsx Sheet 'Dump' to CSV."""
    xlsx_file = src_dir / "Primary_FY202426_10.xlsx"
    if not xlsx_file.exists():
        log.warning(f"Primary file not found: {xlsx_file}")
        return False

    try:
        df = pd.read_excel(xlsx_file, sheet_name="Dump", header=1)
        df.columns = [str(c).strip() for c in df.columns]

        csv_file = out_dir / "Primary" / "Primary_FY202426_10.csv"
        csv_file.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(csv_file, index=False)
        log.info(f"✓ Extracted {df.shape[0]} rows: {xlsx_file.name} -> {csv_file.name}")
        return True
    except Exception as e:
        log.error(f"✗ Failed to extract Primary: {e}")
        return False


def extract_chain_allocation_weights(src_dir, out_dir):
    """Extract Dist_primary_cont_based_on_secondary_MOM.xlsx Sheet2 to CSV."""
    xlsx_file = src_dir / "Dist_primary_cont_based_on_secondary_MOM.xlsx"
    if not xlsx_file.exists():
        log.warning(f"Chain allocation weights file not found: {xlsx_file}")
        return False

    try:
        df = pd.read_excel(xlsx_file, sheet_name="Sheet2", header=1)
        df.columns = [str(c).strip() for c in df.columns]

        csv_file = out_dir / "DIST" / "ChainAllocationWeights.csv"
        csv_file.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(csv_file, index=False)
        log.info(f"✓ Extracted {df.shape[0]} rows: Sheet2 -> {csv_file.name}")
        return True
    except Exception as e:
        log.error(f"✗ Failed to extract chain allocation weights: {e}")
        return False


def extract_dist_cont_weights(src_dir, out_dir):
    """Extract Dist_primary_cont_based_on_secondary_MOM.xlsx sheet 'Dist Primary Conv to Chain Art' to CSV."""
    xlsx_file = src_dir / "Dist_primary_cont_based_on_secondary_MOM.xlsx"
    if not xlsx_file.exists():
        log.warning(f"DIST allocation file not found: {xlsx_file}")
        return False

    try:
        df = pd.read_excel(xlsx_file, sheet_name="Dist Primary Conv to Chain Art", header=1)
        df.columns = [str(c).strip() for c in df.columns]

        csv_file = out_dir / "DIST" / "DistPrimaryContWeightsArticle_Source.csv"
        csv_file.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(csv_file, index=False)
        log.info(f"✓ Extracted {df.shape[0]} rows: 'Dist Primary Conv to Chain Art' -> {csv_file.name}")
        return True
    except Exception as e:
        log.error(f"✗ Failed to extract DIST cont weights: {e}")
        return False


def extract_universe(src_dir, out_dir):
    """Extract Universe MT.xlsx 'PAN INDIA' sheet to CSV."""
    xlsx_file = src_dir / "Universe MT.xlsx"
    if not xlsx_file.exists():
        log.warning(f"Universe file not found: {xlsx_file}")
        return False

    try:
        df = pd.read_excel(xlsx_file, sheet_name="PAN INDIA", header=0)
        df.columns = [str(c).strip() for c in df.columns]

        csv_file = out_dir / "Distribution" / "UniverseMT.csv"
        csv_file.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(csv_file, index=False)
        log.info(f"✓ Extracted {df.shape[0]} rows: Universe MT.xlsx -> {csv_file.name}")
        return True
    except Exception as e:
        log.error(f"✗ Failed to extract universe: {e}")
        return False


def extract_promo(src_dir, out_dir):
    """Extract Promo Master -MT.xlsx to CSV."""
    xlsx_file = src_dir / "Promo Master -MT.xlsx"
    if not xlsx_file.exists():
        log.warning(f"Promo master file not found: {xlsx_file}")
        return False

    try:
        df = pd.read_excel(xlsx_file, sheet_name="Sheet1", header=0)
        df.columns = [str(c).strip() for c in df.columns]

        csv_file = out_dir / "Promo" / "PromoMaster.csv"
        csv_file.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(csv_file, index=False)
        log.info(f"✓ Extracted {df.shape[0]} rows: Promo Master -MT.xlsx -> {csv_file.name}")
        return True
    except Exception as e:
        log.error(f"✗ Failed to extract promo master: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Extract XLSX seed files to CSV format"
    )
    parser.add_argument(
        "--src", type=Path, required=True,
        help="Source directory containing XLSX files"
    )
    parser.add_argument(
        "--out", type=Path, default=None,
        help="Output directory for CSV seeds (default: PowerBI/SeedData relative to CWD)"
    )

    args = parser.parse_args()

    if not args.src.exists():
        log.error(f"Source directory not found: {args.src}")
        sys.exit(1)

    out_dir = args.out or Path.cwd() / "PowerBI" / "SeedData"
    out_dir.mkdir(parents=True, exist_ok=True)

    log.info(f"Extracting XLSX files from: {args.src}")
    log.info(f"Writing CSV seeds to: {out_dir}\n")

    results = {
        "Primary": extract_primary(args.src, out_dir),
        "ChainAllocationWeights": extract_chain_allocation_weights(args.src, out_dir),
        "DistContWeights": extract_dist_cont_weights(args.src, out_dir),
        "Universe": extract_universe(args.src, out_dir),
        "Promo": extract_promo(args.src, out_dir),
    }

    log.info(f"\n{'='*60}")
    passed = sum(1 for v in results.values() if v)
    log.info(f"Extraction complete: {passed}/{len(results)} files extracted")

    if passed == len(results):
        log.info("✓ All XLSX files converted to CSV. Commit seeds to git.")
        return 0
    else:
        log.warning("⚠ Some XLSX files were missing or failed. Build will use fallback logic.")
        return 0  # Non-fatal


if __name__ == "__main__":
    sys.exit(main())
