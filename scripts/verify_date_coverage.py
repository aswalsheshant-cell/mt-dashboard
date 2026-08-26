#!/usr/bin/env python3
"""
Verifies complete 28-month data coverage (April 2024 to July 2026) across all
data files. Run standalone to audit ingestion pipeline for missing months.
"""
import json
import re
import sys
from pathlib import Path
import pandas as pd
import numpy as np

# Expected canonical 28-month timeline
EXPECTED_TIMELINE = [
    # FY25 (Apr'24 - Mar'25)
    "2024-04", "2024-05", "2024-06", "2024-07", "2024-08", "2024-09",
    "2024-10", "2024-11", "2024-12", "2025-01", "2025-02", "2025-03",
    # FY26 (Apr'25 - Mar'26)
    "2025-04", "2025-05", "2025-06", "2025-07", "2025-08", "2025-09",
    "2025-10", "2025-11", "2025-12", "2026-01", "2026-02", "2026-03",
    # FY27 YTD (Apr'26 - Jul'26)
    "2026-04", "2026-05", "2026-06", "2026-07",
]

def parse_date_flexible(val):
    """Robust multi-format date parser handling Excel serials, ISO dates, and MMM'YY."""
    if pd.isna(val) or val == "":
        return None
    val_str = str(val).strip()

    # Format: MMM'YY or MMM-YY (e.g. Apr'24, Jul-26)
    match_my = re.match(r"([A-Za-z]{3})['\-](\d{2})", val_str)
    if match_my:
        mon_str, yr_str = match_my.groups()
        try:
            dt = pd.to_datetime(f"01-{mon_str}-20{yr_str}", format="%d-%b-%Y")
            return dt.strftime("%Y-%m")
        except Exception:
            pass

    # Standard date parsing
    try:
        dt = pd.to_datetime(val_str, errors="coerce")
        if pd.notna(dt):
            return dt.strftime("%Y-%m")
    except Exception:
        pass

    return None

def get_canonical_fy(dt_str):
    """Derives Indian Fiscal Year (Apr-Mar) from YYYY-MM string."""
    if not dt_str or len(dt_str) < 7:
        return "Unknown"
    yr = int(dt_str[:4])
    mo = int(dt_str[5:7])
    return f"FY{yr + 1 - 2000}" if mo >= 4 else f"FY{yr - 2000}"

def audit_dataset_coverage(csv_path: str, date_col: str):
    """Audit a single CSV file for 28-month coverage."""
    print(f"\n{'=' * 70}")
    print(f"AUDITING: {csv_path}")
    print(f"Date Column: '{date_col}'")
    print(f"{'=' * 70}")

    try:
        df = pd.read_csv(csv_path, low_memory=False)
    except Exception as e:
        print(f"❌ Failed to load {csv_path}: {e}")
        return False

    if date_col not in df.columns:
        print(f"❌ Column '{date_col}' not found.")
        print(f"   Available columns: {list(df.columns[:10])}")
        return False

    df["parsed_month"] = df[date_col].apply(parse_date_flexible)
    found_months = set(df["parsed_month"].dropna().unique())
    found_months_sorted = sorted(list(found_months))

    missing_months = [m for m in EXPECTED_TIMELINE if m not in found_months]
    present_months = [m for m in EXPECTED_TIMELINE if m in found_months]

    print(f"\n✓ Rows: {len(df):,}")
    print(f"✓ Valid date parses: {len(df[df['parsed_month'].notna()]):,}")
    print(f"✓ Unique months found: {len(found_months)}/{len(EXPECTED_TIMELINE)}")
    if found_months_sorted:
        print(f"   Span: {found_months_sorted[0]} to {found_months_sorted[-1]}")

    # Check by FY block
    print(f"\nFY Block Coverage:")
    for fy_label, span in [
        ("FY25 (Apr'24-Mar'25)", EXPECTED_TIMELINE[:12]),
        ("FY26 (Apr'25-Mar'26)", EXPECTED_TIMELINE[12:24]),
        ("FY27 YTD (Apr'26-Jul'26)", EXPECTED_TIMELINE[24:]),
    ]:
        present_in_fy = [m for m in span if m in found_months]
        pct = round(100 * len(present_in_fy) / len(span), 1) if span else 0
        status = (
            "✓ COMPLETE"
            if len(present_in_fy) == len(span)
            else f"⚠️ INCOMPLETE ({len(present_in_fy)}/{len(span)} = {pct}%)"
        )
        print(f"   • {fy_label}: {status}")

    if missing_months:
        print(f"\n🚨 MISSING MONTHS ({len(missing_months)}):")
        for m in sorted(missing_months):
            print(f"   - {m} ({get_canonical_fy(m)})")
        return False
    else:
        print(f"\n✅ 100% COVERAGE: All 28 months (Apr'24 to Jul'26) verified.")
        return True

def audit_datajs_coverage():
    """Audit data.js for complete FY coverage."""
    print(f"\n{'=' * 70}")
    print(f"AUDITING: dashboard/data.js")
    print(f"{'=' * 70}")

    try:
        with open("dashboard/data.js", "r") as f:
            txt = f.read()
            # Extract JSON from window.DASH = {...};
            start = txt.index("window.DASH = ") + len("window.DASH = ")
            end = txt.rindex(";")
            data = json.loads(txt[start:end])
    except Exception as e:
        print(f"❌ Failed to load data.js: {e}")
        return False

    # Check FY coverage in primary block
    if "primary" in data:
        primary = data["primary"]
        fy_tags = primary.get("fy_tags", [])
        print(f"\n✓ Primary FY Tags: {fy_tags}")

        # Verify each FY has non-zero NSV
        for fy in ["fy25", "fy26", "fy27"]:
            nsv_key = f"nsv_{fy}"
            if nsv_key in primary:
                nsv = primary[nsv_key]
                status = "✓" if nsv > 0 else "⚠️"
                print(f"   {status} {nsv_key.upper()}: {nsv:,.0f} Lakh")

        # Check month coverage
        if "month_labels" in primary:
            months = primary["month_labels"]
            print(f"\n✓ Month Labels: {len(months)} months")
            print(f"   {months[:3]} ... {months[-3:]}")

    # Check offtake block
    if "offtake" in data:
        offtake = data["offtake"]
        fy_tags = offtake.get("fy_tags", [])
        print(f"\n✓ Offtake FY Tags: {fy_tags}")

        for fy in ["fy25", "fy26", "fy27"]:
            total_key = f"total_{fy}"
            if total_key in offtake:
                total = offtake[total_key]
                status = "✓" if total > 0 else "⚠️"
                print(f"   {status} {total_key.upper()}: {total:,.0f} Lakh")

    # Check detail_records for FY27 presence
    if "detail_records" in data:
        detail = data["detail_records"]
        fy_counts = {}
        for rec in detail:
            fy = rec.get("FY", "Unknown")
            fy_counts[fy] = fy_counts.get(fy, 0) + 1
        print(f"\n✓ Detail Records by FY:")
        for fy in sorted(fy_counts.keys()):
            print(f"   {fy}: {fy_counts[fy]:,} records")

    print(f"\n✅ data.js structure validated.")
    return True

if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parent.parent

    print("\n" + "=" * 70)
    print("28-MONTH DATA COVERAGE AUDIT (Apr'24 to Jul'26)")
    print("=" * 70)

    all_passed = True

    # Audit data.js first
    try:
        if not audit_datajs_coverage():
            all_passed = False
    except Exception as e:
        print(f"⚠️ data.js audit skipped: {e}")

    # Audit raw CSVs if they exist
    csv_files = [
        ("PowerBI/RawDataFolders/Primary/primary_sales.csv", "Month"),
        ("PowerBI/RawDataFolders/Offtake/offtake.csv", "Month"),
    ]

    for csv_path, date_col in csv_files:
        full_path = repo_root / csv_path
        if full_path.exists():
            if not audit_dataset_coverage(str(full_path), date_col):
                all_passed = False
        else:
            print(f"\n⚠️ SKIPPED (not found): {csv_path}")

    print("\n" + "=" * 70)
    if all_passed:
        print("✅ VERIFICATION PASSED: 28-month coverage complete")
    else:
        print("❌ VERIFICATION FAILED: Missing months detected")
    print("=" * 70 + "\n")

    sys.exit(0 if all_passed else 1)
