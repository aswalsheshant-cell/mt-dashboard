#!/usr/bin/env python3
"""
FY24-25 Data Restoration - Automated Processing Script

This script orchestrates the complete FY24-25 data workflow:
1. Validates downloaded XLSB files
2. Runs split scripts to generate monthly CSVs
3. Verifies output
4. Prepares git commands for commit

Run this AFTER you've downloaded the XLSB files locally.

Usage:
    python scripts/process_fy24_25_data.py \
        --primary "/path/to/MT, Eb2B & SIS primary April_23 to May_26.xlsb" \
        --offtake "/path/to/FY-24-26 Chain offtake Store Wise File till May.xlsb"

Or with environment variables:
    export PRIMARY_XLSB="/path/to/primary.xlsb"
    export OFFTAKE_XLSB="/path/to/offtake.xlsb"
    python scripts/process_fy24_25_data.py
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

# Constants
PRIMARY_OUTPUT_DIR = "PowerBI/RawDataFolders/Primary_Article_Monthly"
OFFTAKE_OUTPUT_DIR = "PowerBI/RawDataFolders/Offtake_Monthly"

class Logger:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.successes = []

    def error(self, msg):
        self.errors.append(msg)
        print(f"✗ {msg}")

    def warning(self, msg):
        self.warnings.append(msg)
        print(f"⚠ {msg}")

    def success(self, msg):
        self.successes.append(msg)
        print(f"✓ {msg}")

    def info(self, msg):
        print(f"  {msg}")

    def summary(self):
        print("\n" + "="*70)
        print("SUMMARY")
        print("="*70)
        print(f"✓ Successes: {len(self.successes)}")
        print(f"⚠ Warnings: {len(self.warnings)}")
        print(f"✗ Errors: {len(self.errors)}")
        if self.errors:
            print("\nERRORS:")
            for e in self.errors:
                print(f"  - {e}")
        return len(self.errors) == 0

def validate_file(path, name):
    """Validate that a file exists and is readable."""
    logger = Logger()
    p = Path(path)

    if not p.exists():
        logger.error(f"{name} file not found: {path}")
        return False

    if not p.is_file():
        logger.error(f"{name} is not a file: {path}")
        return False

    size_mb = p.stat().st_size / (1024 * 1024)
    if size_mb < 10:
        logger.error(f"{name} too small ({size_mb:.1f} MB) - may be corrupted")
        return False

    logger.success(f"{name} found ({size_mb:.1f} MB)")
    return True

def run_split_primary(xlsb_path, output_dir):
    """Run primary article split script."""
    print("\n" + "="*70)
    print("STEP 1: Splitting Primary Article XLSB")
    print("="*70)

    logger = Logger()

    # Check if split script exists
    split_script = Path("scripts/split_primary_article_xlsb.py")
    if not split_script.exists():
        logger.error(f"Split script not found: {split_script}")
        return False

    logger.success(f"Split script found: {split_script}")

    # Create output directory
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    logger.success(f"Output directory ready: {output_dir}")

    # Run split
    try:
        print(f"\nRunning: python {split_script} \"{xlsb_path}\" \"{output_dir}\"")
        result = subprocess.run(
            [sys.executable, str(split_script), str(xlsb_path), str(output_dir)],
            capture_output=True,
            text=True,
            timeout=600
        )

        if result.returncode == 0:
            logger.success("Primary split completed successfully")
            print(result.stdout)
            return True
        else:
            logger.error(f"Primary split failed with exit code {result.returncode}")
            print("STDERR:", result.stderr)
            print("STDOUT:", result.stdout)
            return False

    except subprocess.TimeoutExpired:
        logger.error("Primary split timed out (> 10 minutes)")
        return False
    except Exception as e:
        logger.error(f"Primary split failed: {e}")
        return False

def run_split_offtake(xlsb_path, output_dir):
    """Run offtake split script."""
    print("\n" + "="*70)
    print("STEP 2: Splitting Offtake XLSB")
    print("="*70)

    logger = Logger()

    # Check if split script exists
    split_script = Path("scripts/split_offtake_store_article_xlsb.py")
    if not split_script.exists():
        logger.error(f"Split script not found: {split_script}")
        return False

    logger.success(f"Split script found: {split_script}")

    # Create output directory
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    logger.success(f"Output directory ready: {output_dir}")

    # Run split
    try:
        print(f"\nRunning: python {split_script} \"{xlsb_path}\" \"{output_dir}\"")
        result = subprocess.run(
            [sys.executable, str(split_script), str(xlsb_path), str(output_dir)],
            capture_output=True,
            text=True,
            timeout=600
        )

        if result.returncode == 0:
            logger.success("Offtake split completed successfully")
            print(result.stdout)
            return True
        else:
            logger.error(f"Offtake split failed with exit code {result.returncode}")
            print("STDERR:", result.stderr)
            print("STDOUT:", result.stdout)
            return False

    except subprocess.TimeoutExpired:
        logger.error("Offtake split timed out (> 10 minutes)")
        return False
    except Exception as e:
        logger.error(f"Offtake split failed: {e}")
        return False

def verify_output():
    """Verify that all expected CSV files were created."""
    print("\n" + "="*70)
    print("STEP 3: Verifying Output CSVs")
    print("="*70)

    logger = Logger()

    # Check primary CSVs
    primary_dir = Path(PRIMARY_OUTPUT_DIR)
    if primary_dir.exists():
        primary_csvs = list(primary_dir.glob("primary_article_*.csv"))
        logger.success(f"Primary CSVs: {len(primary_csvs)} files")

        # List months
        months = [f.stem.replace("primary_article_", "") for f in primary_csvs]
        months.sort()
        logger.info(f"Months: {', '.join(months[:5])} ... {', '.join(months[-5:])}")

        # Check for FY24-25 files
        fy24_25_files = [f for f in primary_csvs if any(m in f.name for m in ['Apr_24', 'Mar_25'])]
        if fy24_25_files:
            logger.success(f"FY24-25 primary files present ({len(fy24_25_files)} check)")
        else:
            logger.warning("No FY24-25 primary files detected - check file naming")
    else:
        logger.error(f"Primary output directory not found: {PRIMARY_OUTPUT_DIR}")

    # Check offtake CSVs
    offtake_dir = Path(OFFTAKE_OUTPUT_DIR)
    if offtake_dir.exists():
        offtake_csvs = list(offtake_dir.glob("offtake_store_article_*.csv"))
        logger.success(f"Offtake CSVs: {len(offtake_csvs)} files")

        # List months
        if offtake_csvs:
            months = [f.stem.replace("offtake_store_article_", "") for f in offtake_csvs]
            months.sort()
            logger.info(f"Months: {', '.join(months[:5])} ... {', '.join(months[-5:])}")
    else:
        logger.warning(f"Offtake output directory not found: {OFFTAKE_OUTPUT_DIR}")

    return logger.summary()

def main():
    parser = argparse.ArgumentParser(description="FY24-25 Data Processing Automation")
    parser.add_argument("--primary", help="Path to primary XLSB file",
                       default=os.environ.get("PRIMARY_XLSB"))
    parser.add_argument("--offtake", help="Path to offtake XLSB file",
                       default=os.environ.get("OFFTAKE_XLSB"))
    parser.add_argument("--skip-primary", action="store_true", help="Skip primary split")
    parser.add_argument("--skip-offtake", action="store_true", help="Skip offtake split")

    args = parser.parse_args()

    print("="*70)
    print("FY24-25 DATA RESTORATION - AUTOMATED PROCESSING")
    print("="*70)

    # Validate inputs
    if not args.primary or not args.offtake:
        print("\nERROR: Both --primary and --offtake paths required")
        print("Usage:")
        print("  python scripts/process_fy24_25_data.py \\")
        print("    --primary '/path/to/primary.xlsb' \\")
        print("    --offtake '/path/to/offtake.xlsb'")
        sys.exit(1)

    print(f"\nConfiguration:")
    print(f"  Primary XLSB: {args.primary}")
    print(f"  Offtake XLSB: {args.offtake}")
    print(f"  Output: {PRIMARY_OUTPUT_DIR}, {OFFTAKE_OUTPUT_DIR}")

    all_success = True

    # Step 1: Split primary
    if not args.skip_primary:
        if not run_split_primary(args.primary, PRIMARY_OUTPUT_DIR):
            all_success = False

    # Step 2: Split offtake
    if not args.skip_offtake:
        if not run_split_offtake(args.offtake, OFFTAKE_OUTPUT_DIR):
            all_success = False

    # Step 3: Verify
    if not verify_output():
        all_success = False

    # Final status
    print("\n" + "="*70)
    if all_success:
        print("✓✓✓ PROCESSING COMPLETE ✓✓✓")
        print("="*70)
        print("\nNEXT STEPS:")
        print("1. Review the CSVs generated:")
        print(f"   ls {PRIMARY_OUTPUT_DIR}/")
        print(f"   ls {OFFTAKE_OUTPUT_DIR}/")
        print("\n2. Commit to git:")
        print("   git add PowerBI/RawDataFolders/")
        print("   git commit -m 'Add FY24-25 monthly data splits'")
        print("   git push origin claude/ai-agent-powerbi-dashboard-issues-wpjuh6")
        print("\n3. Rebuild dashboard:")
        print("   python scripts/build_dashboard_data.py --src PowerBI/RawDataFolders --out dashboard/data.js")
        print("\n4. Verify FY25 appears on dashboard (index.html)")
    else:
        print("✗✗✗ PROCESSING FAILED ✗✗✗")
        print("="*70)
        print("\nPlease review errors above and retry.")
        sys.exit(1)

if __name__ == "__main__":
    main()
