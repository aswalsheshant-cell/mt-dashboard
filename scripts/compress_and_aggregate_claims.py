#!/usr/bin/env python3
"""
Local Pre-Aggregation & Compression Pipeline

Reads large raw claim files from local machine, aggregates to CM2 hierarchy,
and outputs lightweight Git-ready CSV files.

This reduces 200MB+ files to <5MB per month while preserving all dimensions
required for CM2, Trade Spend ROI, and MoM analysis.

USAGE:
  python scripts/compress_and_aggregate_claims.py
"""

import sys
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np

# Paths
INPUT_DIR = Path("data_sources/raw_large_claims")
OUTPUT_DIR = Path("data_sources/distributor_claims")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Column aliases for robust mapping
COLUMN_ALIASES = {
    "fiscal_year": ["fiscal_year", "fy", "year"],
    "month": ["month", "month_name", "month_label", "period"],
    "chain": ["chain", "account", "customer_name", "retailer", "key_account", "customer"],
    "zone": ["zone", "region", "territory", "geo", "area"],
    "brand": ["brand", "brand_name", "division", "product_line"],
    "category": ["category", "cat", "product_category"],
    "subcategory": ["subcategory", "subcat", "product_subcategory"],
    "article_code": ["article_code", "article_id", "article_no", "sku", "product_code"],
    "claim_amount": ["claim_amount", "amount", "claim_val", "settled_value", "claim_amt", "val_inr", "settled_amt"],
    "expense_type": ["expense_type", "claim_type", "scheme_type", "promo_head", "head", "nature"],
    "distributor_id": ["distributor_id", "dist_id", "dist_code", "dtr_id", "vendor_code"],
    "claim_id": ["claim_id", "claim_no", "claim_ref", "doc_no", "invoice_no"],
}

# Aggregation grain (CM2 hierarchy)
GROUP_COLS = [
    "fiscal_year", "month", "chain", "zone",
    "brand", "category", "subcategory", "article_code", "expense_type"
]


def resolve_column(df_columns: list, aliases: list) -> str:
    """Find matching column name from aliases (case-insensitive)."""
    clean_cols = {col.strip().lower().replace(" ", "_"): col for col in df_columns}
    for alias in aliases:
        if alias.lower() in clean_cols:
            return clean_cols[alias.lower()]
    return None


def normalize_and_map_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize column names and map to standard names."""
    # Lowercase and replace spaces
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    # Apply alias mapping
    for standard_name, aliases in COLUMN_ALIASES.items():
        matched_col = resolve_column(df.columns.tolist(), aliases)
        if matched_col and matched_col != standard_name:
            df = df.rename(columns={matched_col: standard_name})

    return df


def validate_and_quarantine(df: pd.DataFrame) -> tuple:
    """
    Separate valid records from quarantine-worthy records.
    Returns (valid_df, quarantine_df)
    """
    # Identify invalid records
    invalid_mask = (
        df["claim_amount"].isna() |
        (pd.to_numeric(df["claim_amount"], errors="coerce") <= 0) |
        df["chain"].isna() |
        df["brand"].isna()
    )

    quarantine = df[invalid_mask].copy()
    quarantine["quarantine_reason"] = ""

    # Categorize quarantine reasons
    quarantine.loc[quarantine["claim_amount"].isna(), "quarantine_reason"] = "Null_Claim_Amount"
    quarantine.loc[
        pd.to_numeric(quarantine["claim_amount"], errors="coerce") <= 0,
        "quarantine_reason"
    ] = "Non_Positive_Claim_Amount"
    quarantine.loc[quarantine["chain"].isna(), "quarantine_reason"] = "Null_Chain"
    quarantine.loc[quarantine["brand"].isna(), "quarantine_reason"] = "Null_Brand"

    valid = df[~invalid_mask].copy()

    # Coerce numeric fields
    valid["claim_amount"] = pd.to_numeric(valid["claim_amount"], errors="coerce")

    return valid, quarantine


def aggregate_to_hierarchy(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate to CM2 hierarchy grain: Chain × Brand × Category × Subcategory × Article × Month."""
    # Select available grouping columns
    available_cols = [col for col in GROUP_COLS if col in df.columns]

    agg_df = df.groupby(available_cols, as_index=False, dropna=False).agg({
        "claim_amount": ["sum", "count", "mean", "min", "max"],
        "claim_id": "nunique" if "claim_id" in df.columns else "size"
    }).round(2)

    # Flatten multi-level columns
    agg_df.columns = [
        f"{col[0]}_{col[1]}" if col[1] else col[0]
        for col in agg_df.columns
    ]

    # Rename for clarity
    agg_df = agg_df.rename(columns={
        "claim_amount_sum": "total_claim_amount",
        "claim_amount_count": "transaction_count",
        "claim_amount_mean": "avg_claim_amount",
        "claim_amount_min": "min_claim_amount",
        "claim_amount_max": "max_claim_amount",
        "claim_id_nunique": "unique_claim_ids"
    })

    return agg_df.sort_values(by="total_claim_amount", ascending=False)


def process_large_claims():
    """Main pipeline: read, validate, aggregate, output."""
    if not INPUT_DIR.exists():
        print(f"❌ Input directory not found: {INPUT_DIR}")
        print("Please create 'data_sources/raw_large_claims/' and place raw files there.")
        sys.exit(1)

    raw_files = list(INPUT_DIR.glob("*.csv")) + list(INPUT_DIR.glob("*.xlsx"))

    if not raw_files:
        print(f"❌ No CSV/Excel files found in {INPUT_DIR}")
        sys.exit(1)

    print("=" * 80)
    print("🚀 DISTRIBUTOR CLAIMS PRE-AGGREGATION & COMPRESSION")
    print("=" * 80)
    print(f"Input Directory: {INPUT_DIR.resolve()}")
    print(f"Output Directory: {OUTPUT_DIR.resolve()}")
    print(f"Files to Process: {len(raw_files)}\n")

    aggregated_chunks = []
    quarantine_records = []
    total_valid = 0
    total_quarantine = 0

    for file_path in sorted(raw_files):
        print(f"\n📂 Processing: {file_path.name}")

        # Read with chunking for memory efficiency
        chunk_size = 100_000
        file_aggregates = []

        try:
            if file_path.suffix.lower() == ".csv":
                chunks = pd.read_csv(file_path, chunksize=chunk_size, low_memory=False)
            else:
                # For Excel, read all at once (chunking not supported)
                df = pd.read_excel(file_path)
                chunks = [df[i:i+chunk_size] for i in range(0, len(df), chunk_size)]

            for idx, chunk in enumerate(chunks):
                # Normalize and map columns
                chunk = normalize_and_map_columns(chunk)

                # Validate and separate
                valid, quarantine = validate_and_quarantine(chunk)

                if not valid.empty:
                    agg = aggregate_to_hierarchy(valid)
                    file_aggregates.append(agg)
                    total_valid += len(valid)

                if not quarantine.empty:
                    quarantine_records.append(quarantine)
                    total_quarantine += len(quarantine)

                if (idx + 1) % 5 == 0:
                    print(f"  ✓ Processed {(idx + 1) * chunk_size:,} rows...")

        except Exception as e:
            print(f"  ❌ Error processing file: {e}")
            continue

        # Aggregate file-level chunks
        if file_aggregates:
            file_total = pd.concat(file_aggregates, ignore_index=True)
            file_final = file_total.groupby(
                [c for c in GROUP_COLS if c in file_total.columns],
                as_index=False, dropna=False
            ).agg({
                "total_claim_amount": "sum",
                "transaction_count": "sum",
                "unique_claim_ids": "sum"
            }).round(2)
            aggregated_chunks.append(file_final)
            print(f"  ✅ Aggregated to {len(file_final):,} grain-level rows")

    # Combine all files
    if aggregated_chunks:
        print(f"\n{'='*80}")
        print("📊 FINALIZING MASTER AGGREGATED TABLE...")
        print(f"{'='*80}")

        final_df = pd.concat(aggregated_chunks, ignore_index=True)
        master_agg = final_df.groupby(
            [c for c in GROUP_COLS if c in final_df.columns],
            as_index=False, dropna=False
        ).agg({
            "total_claim_amount": "sum",
            "transaction_count": "sum",
            "unique_claim_ids": "sum"
        }).round(2)

        # Output master file
        master_file = OUTPUT_DIR / "distributor_claims_aggregated_master.csv"
        master_agg.to_csv(master_file, index=False)
        master_size_mb = master_file.stat().st_size / (1024 * 1024)
        print(f"✅ Master Aggregated File: {master_file.name} ({master_size_mb:.2f} MB)")
        print(f"   Total Grain Nodes: {len(master_agg):,}")
        print(f"   Total Claim Value: ₹{master_agg['total_claim_amount'].sum():.2f} Cr")

    # Export quarantine
    if quarantine_records:
        print(f"\n{'='*80}")
        print("⚠️  QUARANTINE LEDGER (Review Before Ingestion)...")
        print(f"{'='*80}")

        quarantine_df = pd.concat(quarantine_records, ignore_index=True)
        quarantine_file = OUTPUT_DIR / "distributor_claims_quarantine_audit.csv"
        quarantine_df.to_csv(quarantine_file, index=False)
        quarantine_size_mb = quarantine_file.stat().st_size / (1024 * 1024)
        print(f"⚠️  Quarantine Ledger: {quarantine_file.name} ({quarantine_size_mb:.2f} MB)")
        print(f"   Total Quarantined Rows: {len(quarantine_df):,}")

        # Summary by reason
        reason_summary = quarantine_df["quarantine_reason"].value_counts()
        print(f"\n   Breakdown:")
        for reason, count in reason_summary.items():
            print(f"     - {reason}: {count:,} rows")

    # Final report
    print(f"\n{'='*80}")
    print("✅ COMPRESSION COMPLETE")
    print(f"{'='*80}")
    print(f"""
Raw Ingestion Summary:
  Total Valid Records: {total_valid:,}
  Total Quarantine Records: {total_quarantine:,}

Output Files:
  1. distributor_claims_aggregated_master.csv ← Use this for data_master.json integration
  2. distributor_claims_quarantine_audit.csv ← Review & reconcile manually

Next Steps:
  1. Review quarantine audit for legitimate disputes vs. data entry errors
  2. Validate aggregated master against finance ledgers
  3. Commit & push: git add data_sources/distributor_claims/ && git commit && git push
  4. I will ingest into data_master.json and regenerate dashboard/data.js
    """)


if __name__ == "__main__":
    process_large_claims()
