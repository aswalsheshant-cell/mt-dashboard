#!/usr/bin/env python3
"""
Distributor Claims Pre-Push Schema Validation

Validates extracted claim files before ingestion into data_master.json.
Checks for mandatory fields, data types, nulls, and duplicate claim records.

USAGE:
  python scripts/validate_claims_precheck.py
"""

import os
import sys
from pathlib import Path
import pandas as pd

# Directory configuration
CLAIMS_DIR = Path("data_sources/distributor_claims")

# Essential schema definitions
MANDATORY_FIELDS = {
    "distributor_id": ["distributor_id", "dist_id", "dist_code", "dtr_id", "vendor_code"],
    "claim_id": ["claim_id", "claim_no", "claim_ref", "doc_no", "invoice_no"],
    "claim_date": ["claim_date", "doc_date", "date", "month", "period"],
    "claim_amount": ["claim_amount", "amount", "claim_val", "settled_value", "claim_amt"],
    "chain": ["chain", "account", "customer_name", "retailer", "key_account"],
    "brand": ["brand", "brand_name", "division"],
    "expense_type": ["expense_type", "claim_type", "scheme_type", "promo_head", "head"]
}

ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls"}


def resolve_column(df_columns: list, aliases: list) -> str:
    """Finds matching column name from aliases (case-insensitive)."""
    clean_cols = {col.strip().lower().replace(" ", "_"): col for col in df_columns}
    for alias in aliases:
        if alias.lower() in clean_cols:
            return clean_cols[alias.lower()]
    return None


def inspect_file(file_path: Path) -> tuple:
    """Validates schema, data types, nulls, and duplicate primary keys in a single file."""
    issues = []

    # 1. Read file
    try:
        if file_path.suffix.lower() == ".csv":
            df = pd.read_csv(file_path, low_memory=False)
        else:
            df = pd.read_excel(file_path)
    except Exception as e:
        return False, [f"Failed to read file: {e}"], None

    total_rows = len(df)
    if total_rows == 0:
        return False, ["File is empty."], df

    # 2. Check Mandatory Columns
    mapped_columns = {}
    missing_fields = []
    for standard_name, aliases in MANDATORY_FIELDS.items():
        matched = resolve_column(df.columns.tolist(), aliases)
        if matched:
            mapped_columns[standard_name] = matched
        else:
            missing_fields.append(standard_name)

    if missing_fields:
        issues.append(f"Missing mandatory fields: {', '.join(missing_fields)}")

    # 3. Check for Nulls in Key Identifiers (if present)
    if "claim_id" in mapped_columns:
        null_claims = df[mapped_columns["claim_id"]].isna().sum()
        if null_claims > 0:
            issues.append(f"{null_claims} rows have null '{mapped_columns['claim_id']}'")

    # 4. Check for Numeric Validity on Amounts
    if "claim_amount" in mapped_columns:
        amt_col = mapped_columns["claim_amount"]
        non_numeric = pd.to_numeric(df[amt_col], errors="coerce").isna().sum()
        if non_numeric > 0:
            issues.append(f"{non_numeric} non-numeric values in '{amt_col}'")

    # 5. Check Exact Duplicate Claim Records
    if "claim_id" in mapped_columns and "distributor_id" in mapped_columns:
        dup_subset = [mapped_columns["distributor_id"], mapped_columns["claim_id"]]
        duplicates = df.duplicated(subset=dup_subset, keep=False).sum()
        if duplicates > 0:
            issues.append(f"{duplicates} duplicate rows based on Distributor + Claim ID")

    is_valid = len(issues) == 0
    return is_valid, issues, mapped_columns


def run_precheck():
    if not CLAIMS_DIR.exists():
        print(f"❌ Error: Directory '{CLAIMS_DIR}' does not exist.")
        print("Create the folder and place your extracted claim files inside.")
        sys.exit(1)

    claim_files = [
        f for f in CLAIMS_DIR.iterdir()
        if f.suffix.lower() in ALLOWED_EXTENSIONS and not f.name.startswith("~$")
    ]

    if not claim_files:
        print(f"❌ Error: No CSV or Excel files found in '{CLAIMS_DIR}'.")
        sys.exit(1)

    print("=" * 65)
    print("📋 DISTRIBUTOR CLAIMS PRE-PUSH SCHEMA VALIDATION")
    print("=" * 65)
    print(f"Target Directory: {CLAIMS_DIR.resolve()}")
    print(f"Total Files Found: {len(claim_files)}\n")

    all_passed = True
    summary_rows = []

    for file_path in sorted(claim_files):
        passed, errors, mapped = inspect_file(file_path)
        status_icon = "✅ PASS" if passed else "❌ FAIL"
        if not passed:
            all_passed = False

        print(f"{status_icon} | {file_path.name}")
        if not passed:
            for err in errors:
                print(f"       ⚠️  {err}")
        else:
            print("       ✓ All required headers mapped and basic data types valid.")

    print("\n" + "=" * 65)
    if all_passed:
        print("🎉 ALL FILES PASSED VALIDATION.")
        print("You can safely commit and push these files to the repository.")
        print("=" * 65)
        sys.exit(0)
    else:
        print("🛑 VALIDATION FAILED.")
        print("Fix the schema/header issues listed above before pushing.")
        print("=" * 65)
        sys.exit(1)


if __name__ == "__main__":
    run_precheck()
