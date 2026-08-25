#!/usr/bin/env python3
"""
Distributor Claims Column Inspection & Mapping Preview

Inspects raw claim files to validate column mappings, show sample data,
and preview how specific chains/distributors will be aggregated.

USAGE:
  python scripts/inspect_claims_columns.py [--chain "Trent"] [--file "file_name.csv"]
  python scripts/inspect_claims_columns.py --all-chains
  python scripts/inspect_claims_columns.py --sample-rows 20
"""

import argparse
import sys
from pathlib import Path
import pandas as pd

# Paths
INPUT_DIR = Path("data_sources/raw_large_claims")
OUTPUT_DIR = Path("data_sources/distributor_claims")

# Standard column names we expect
MANDATORY_FIELDS = {
    "distributor_id": ["distributor_id", "dist_id", "dist_code", "dtr_id", "vendor_code"],
    "claim_id": ["claim_id", "claim_no", "claim_ref", "doc_no", "invoice_no"],
    "claim_date": ["claim_date", "doc_date", "date", "month", "period"],
    "claim_amount": ["claim_amount", "amount", "claim_val", "settled_value", "claim_amt", "val_inr", "settled_amt"],
    "chain": ["chain", "account", "customer_name", "retailer", "key_account", "customer"],
    "zone": ["zone", "region", "territory", "geo", "area"],
    "brand": ["brand", "brand_name", "division", "product_line"],
    "category": ["category", "cat", "product_category"],
    "subcategory": ["subcategory", "subcat", "product_subcategory"],
    "article_code": ["article_code", "article_id", "article_no", "sku", "product_code"],
    "expense_type": ["expense_type", "claim_type", "scheme_type", "promo_head", "head", "nature"],
}

REQUIRED_FOR_AGGREGATION = ["chain", "brand", "claim_amount"]


def resolve_column(df_columns: list, aliases: list) -> str:
    """Find matching column name from aliases (case-insensitive)."""
    clean_cols = {col.strip().lower().replace(" ", "_"): col for col in df_columns}
    for alias in aliases:
        if alias.lower() in clean_cols:
            return clean_cols[alias.lower()]
    return None


def inspect_file(file_path: Path, limit_rows: int = None) -> dict:
    """Inspect a single file and return column mapping + sample data."""
    print(f"\n{'='*80}")
    print(f"📄 FILE: {file_path.name}")
    print(f"{'='*80}")

    try:
        if file_path.suffix.lower() == ".csv":
            df = pd.read_csv(file_path, low_memory=False, nrows=limit_rows)
        else:
            df = pd.read_excel(file_path, nrows=limit_rows)
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return None

    print(f"Total Rows in File: {len(df):,}")
    print(f"Raw Columns Found ({len(df.columns)}): {list(df.columns)}\n")

    # Map columns
    mapped = {}
    missing = []
    for standard_name, aliases in MANDATORY_FIELDS.items():
        matched = resolve_column(df.columns.tolist(), aliases)
        if matched:
            mapped[standard_name] = matched
            print(f"  ✓ {standard_name:20s} ← '{matched}'")
        else:
            missing.append(standard_name)
            print(f"  ✗ {standard_name:20s} (NOT FOUND)")

    if missing:
        print(f"\n⚠️  Missing Mandatory Fields: {', '.join(missing)}")

    # Validate required columns for aggregation
    print(f"\n{'─'*80}")
    print("AGGREGATION READINESS CHECK:")
    print(f"{'─'*80}")
    can_aggregate = all(f in mapped for f in REQUIRED_FOR_AGGREGATION)
    if can_aggregate:
        print("✅ All required aggregation columns present")
    else:
        missing_agg = [f for f in REQUIRED_FOR_AGGREGATION if f not in mapped]
        print(f"❌ Missing required aggregation columns: {missing_agg}")

    # Sample data
    print(f"\n{'─'*80}")
    print("SAMPLE DATA (First 5 rows, all columns):")
    print(f"{'─'*80}")
    print(df.head(5).to_string())

    return {
        "file": file_path.name,
        "total_rows": len(df),
        "dataframe": df,
        "mapped_columns": mapped,
        "missing_fields": missing,
        "can_aggregate": can_aggregate,
    }


def inspect_chain_distribution(df: pd.DataFrame, mapped_cols: dict) -> None:
    """Show chain/distributor value distribution in the file."""
    if "chain" not in mapped_cols or "distributor_id" not in mapped_cols:
        print("\n⚠️  Cannot show chain distribution (missing chain or distributor_id mapping)")
        return

    chain_col = mapped_cols["chain"]
    dist_col = mapped_cols["distributor_id"]
    amt_col = mapped_cols.get("claim_amount", None)

    print(f"\n{'='*80}")
    print("CHAIN × DISTRIBUTOR DISTRIBUTION:")
    print(f"{'='*80}")

    if amt_col:
        summary = df.groupby([chain_col, dist_col]).agg({
            amt_col: ["sum", "count"]
        }).round(2)
        summary.columns = ["Total_Claim_Amount", "Claim_Count"]
        summary = summary.reset_index()
        summary = summary.sort_values("Total_Claim_Amount", ascending=False)
        print(summary.head(20).to_string(index=False))
    else:
        summary = df.groupby([chain_col, dist_col]).size().reset_index(name="Claim_Count")
        summary = summary.sort_values("Claim_Count", ascending=False)
        print(summary.head(20).to_string(index=False))


def filter_by_chain(df: pd.DataFrame, mapped_cols: dict, chain_name: str, limit_rows: int = 100) -> None:
    """Show sample records for a specific chain."""
    if "chain" not in mapped_cols:
        print(f"❌ Cannot filter by chain (chain column not mapped)")
        return

    chain_col = mapped_cols["chain"]
    filtered = df[df[chain_col].str.contains(chain_name, case=False, na=False)]

    if filtered.empty:
        print(f"\n❌ No records found for chain containing '{chain_name}'")
        print(f"   Available chains: {df[chain_col].unique()[:10].tolist()}")
        return

    print(f"\n{'='*80}")
    print(f"SAMPLE RECORDS FOR CHAIN: {chain_name}")
    print(f"{'='*80}")
    print(f"Matching Rows: {len(filtered):,} (showing first {min(limit_rows, len(filtered))})\n")
    print(filtered.head(limit_rows).to_string())

    # Summary by mapped dimensions
    if all(col in mapped_cols for col in ["brand", "category", "claim_amount"]):
        print(f"\n{'─'*80}")
        print(f"BREAKDOWN BY BRAND × CATEGORY (for {chain_name}):")
        print(f"{'─'*80}")
        breakdown = filtered.groupby(
            [mapped_cols["brand"], mapped_cols["category"]]
        )[mapped_cols["claim_amount"]].agg(["sum", "count"]).round(2)
        breakdown.columns = ["Total_Amount", "Count"]
        breakdown = breakdown.reset_index()
        breakdown = breakdown.sort_values("Total_Amount", ascending=False)
        print(breakdown.to_string(index=False))


def main():
    parser = argparse.ArgumentParser(
        description="Inspect raw distributor claim files and preview column mappings"
    )
    parser.add_argument(
        "--file",
        type=str,
        help="Specific file name to inspect (default: all .csv and .xlsx files)"
    )
    parser.add_argument(
        "--chain",
        type=str,
        help="Filter and show records for a specific chain (e.g., 'Trent', 'Guardian')"
    )
    parser.add_argument(
        "--all-chains",
        action="store_true",
        help="Show distribution across all chains in file"
    )
    parser.add_argument(
        "--sample-rows",
        type=int,
        default=5,
        help="Number of sample rows to show (default: 5)"
    )
    args = parser.parse_args()

    # Check if input directory exists
    if not INPUT_DIR.exists():
        print(f"❌ Input directory not found: {INPUT_DIR}")
        print("Please create 'data_sources/raw_large_claims/' and place raw claim files there.")
        sys.exit(1)

    # Find files
    if args.file:
        files = [INPUT_DIR / args.file]
        if not files[0].exists():
            print(f"❌ File not found: {files[0]}")
            sys.exit(1)
    else:
        files = list(INPUT_DIR.glob("*.csv")) + list(INPUT_DIR.glob("*.xlsx"))

    if not files:
        print(f"❌ No CSV or Excel files found in {INPUT_DIR}")
        sys.exit(1)

    print("=" * 80)
    print("🔍 DISTRIBUTOR CLAIMS COLUMN INSPECTION & MAPPING PREVIEW")
    print("=" * 80)
    print(f"Input Directory: {INPUT_DIR.resolve()}")
    print(f"Files to Inspect: {len(files)}\n")

    # Inspect each file
    inspection_results = []
    for file_path in sorted(files):
        result = inspect_file(file_path, limit_rows=args.sample_rows * 100)
        if result:
            inspection_results.append(result)

    # Chain distribution summary
    if args.all_chains and inspection_results:
        for result in inspection_results:
            inspect_chain_distribution(result["dataframe"], result["mapped_columns"])

    # Filter by specific chain
    if args.chain and inspection_results:
        for result in inspection_results:
            filter_by_chain(
                result["dataframe"],
                result["mapped_columns"],
                args.chain,
                limit_rows=args.sample_rows
            )

    # Final summary
    print(f"\n{'='*80}")
    print("INSPECTION SUMMARY")
    print(f"{'='*80}")
    for result in inspection_results:
        status = "✅ READY" if result["can_aggregate"] else "⚠️  NEEDS MAPPING"
        print(f"{status} | {result['file']} ({result['total_rows']:,} rows)")

    print(f"\n{'='*80}")
    print("NEXT STEPS:")
    print(f"{'='*80}")
    print("""
1. Review column mappings above for accuracy
2. If columns need custom mapping, edit MANDATORY_FIELDS in this script
3. Run full aggregation: python scripts/compress_and_aggregate_claims.py
4. Commit & push: git add data_sources/distributor_claims/ && git commit && git push
    """)


if __name__ == "__main__":
    main()
