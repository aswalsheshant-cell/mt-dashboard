"""
Pre-Flight CSV Schema & Type Validator for Modern Trade (MT) Seeds.
Validates headers, data types, nulls, and logical bounds before running the deck generator.
"""

import os
import csv
import sys
import argparse
from typing import Dict, Any, List, Tuple

# Schema definition: required columns, cast types, and optional constraints
SCHEMAS: Dict[str, Dict[str, Any]] = {
    "zones.csv": {
        "required_columns": ["zone_name", "primary_nsv", "offtake_nsv", "conversion_pct", "yoy_growth"],
        "types": {
            "zone_name": str,
            "primary_nsv": float,
            "offtake_nsv": float,
            "conversion_pct": float,
            "yoy_growth": float,
        },
        "bounds": {
            "primary_nsv": (0.0, None),
            "offtake_nsv": (0.0, None),
            "conversion_pct": (0.0, 100.0),
            "yoy_growth": (-100.0, 500.0),
        },
    },
    "chains.csv": {
        "required_columns": ["chain_name", "primary_cr", "offtake_cr", "conversion_pct", "growth_yoy"],
        "types": {
            "chain_name": str,
            "primary_cr": float,
            "offtake_cr": float,
            "conversion_pct": float,
            "growth_yoy": float,
        },
        "bounds": {
            "primary_cr": (0.0, None),
            "offtake_cr": (0.0, None),
            "conversion_pct": (0.0, 100.0),
            "growth_yoy": (-100.0, 1000.0),
        },
    },
    "categories.csv": {
        "required_columns": ["category_name", "share_pct", "growth_yoy", "hero_sku"],
        "types": {
            "category_name": str,
            "share_pct": float,
            "growth_yoy": float,
            "hero_sku": str,
        },
        "bounds": {
            "share_pct": (0.0, 100.0),
            "growth_yoy": (-100.0, 500.0),
        },
    },
    "offtake.csv": {
        "required_columns": ["chain_name", "month", "article", "nsv_lakhs", "qty", "store_count"],
        "types": {
            "chain_name": str,
            "month": str,
            "article": str,
            "nsv_lakhs": float,
            "qty": float,
            "store_count": int,
        },
        "bounds": {
            "nsv_lakhs": (0.0, None),
            "qty": (0.0, None),
            "store_count": (0, None),
        },
    },
}


class SeedValidationError:
    def __init__(self, filename: str, row_num: int, column: str, message: str):
        self.filename = filename
        self.row_num = row_num
        self.column = column
        self.message = message

    def __str__(self) -> str:
        loc = f"Row {self.row_num}" if self.row_num > 0 else "Header"
        col = f" [{self.column}]" if self.column else ""
        return f"[{self.filename}] {loc}{col}: {self.message}"


def validate_file(filepath: str, schema: Dict[str, Any]) -> List[SeedValidationError]:
    filename = os.path.basename(filepath)
    errors: List[SeedValidationError] = []

    if not os.path.exists(filepath):
        return [SeedValidationError(filename, 0, "", "File not found.")]

    with open(filepath, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []

        # 1. Check Missing Columns
        missing_cols = [c for c in schema["required_columns"] if c not in headers]
        if missing_cols:
            errors.append(
                SeedValidationError(
                    filename, 0, "", f"Missing required columns: {', '.join(missing_cols)}"
                )
            )
            return errors  # Stop early if required headers are absent

        row_count = 0
        total_share = 0.0

        # 2. Check Rows & Types
        for row_idx, row in enumerate(reader, start=2):
            row_count += 1
            for col, expected_type in schema["types"].items():
                raw_val = row.get(col, "")
                if raw_val is None or str(raw_val).strip() == "":
                    errors.append(SeedValidationError(filename, row_idx, col, "Empty or null value."))
                    continue

                cleaned_val = str(raw_val).strip().replace("%", "").replace(",", "")

                if expected_type == float:
                    try:
                        numeric_val = float(cleaned_val)
                    except ValueError:
                        errors.append(
                            SeedValidationError(filename, row_idx, col, f"Cannot parse '{raw_val}' as float.")
                        )
                        continue

                    # Range checks
                    bounds = schema.get("bounds", {}).get(col)
                    if bounds:
                        min_v, max_v = bounds
                        if min_v is not None and numeric_val < min_v:
                            errors.append(
                                SeedValidationError(
                                    filename, row_idx, col, f"Value {numeric_val} < allowed minimum {min_v}."
                                )
                            )
                        if max_v is not None and numeric_val > max_v:
                            errors.append(
                                SeedValidationError(
                                    filename, row_idx, col, f"Value {numeric_val} > allowed maximum {max_v}."
                                )
                            )

                    if filename == "categories.csv" and col == "share_pct":
                        total_share += numeric_val

                elif expected_type == str:
                    if len(cleaned_val) == 0:
                        errors.append(SeedValidationError(filename, row_idx, col, "String value cannot be empty."))

        if row_count == 0:
            errors.append(SeedValidationError(filename, 0, "", "CSV contains no data rows."))

        # 3. Macro Business Validation
        if filename == "categories.csv" and row_count > 0:
            if not (98.0 <= total_share <= 102.0):
                errors.append(
                    SeedValidationError(
                        filename,
                        0,
                        "share_pct",
                        f"Cumulative category share sums to {total_share:.1f}%, expected ~100.0%.",
                    )
                )

    return errors


def run_preflight_check(csv_dir: str) -> bool:
    print(f"Executing seed pre-flight validation on: {csv_dir}")
    all_errors: List[SeedValidationError] = []

    for filename, schema in SCHEMAS.items():
        filepath = os.path.join(csv_dir, filename)
        errs = validate_file(filepath, schema)
        all_errors.extend(errs)

    if not all_errors:
        print("  All CSV seed files passed schema and logical validation. ✅")
        return True

    print(f"\n  Validation failed with {len(all_errors)} error(s):")
    for err in all_errors:
        print(f"   - {err}")
    return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pre-flight validation for Modern Trade CSV seed files")
    parser.add_argument(
        "--data-dir",
        default="/home/user/mt-dashboard/data/sample_seeds",
        help="Path to folder containing CSV files",
    )
    args = parser.parse_args()

    success = run_preflight_check(args.data_dir)
    sys.exit(0 if success else 1)
