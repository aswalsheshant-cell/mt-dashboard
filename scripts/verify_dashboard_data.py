#!/usr/bin/env python3
"""
scripts/verify_dashboard_data.py

Sanity check for data.js:
1. Detects raw JavaScript artifacts: NaN, undefined, Infinity.
2. Validates JSON parsing after stripping JS assignments (e.g., window.DATA = ...).
3. Verifies offtake_units sum equals the expected target (4,512).
4. Verifies all chain names exist within UniverseMT.csv (no None, blank, or unmapped chains).
"""

import json
import math
import os
import re
import sys
from pathlib import Path
import pandas as pd

# Paths
DATA_JS_PATH = Path("dashboard/data.js")
UNIVERSE_CSV_PATH = Path("PowerBI/SeedData/Distribution/UniverseMT.csv")
EXPECTED_OFFTAKE_UNITS = 4512


def scan_raw_tokens(raw_text: str) -> list:
    """Check for raw unquoted NaN, undefined, or Infinity tokens."""
    errors = []
    # Match NaN, undefined, Infinity that are not part of strings or identifiers
    token_pattern = re.compile(r"(?<![\w\"'])\b(NaN|undefined|Infinity|-Infinity)\b(?![\w\"'])")
    matches = list(token_pattern.finditer(raw_text))
    if matches:
        sample = [m.group(0) for m in matches[:5]]
        errors.append(
            f"Found {len(matches)} illegal raw JS literal(s) (e.g. {sample}) in data payload."
        )
    return errors


def extract_json_payload(raw_text: str):
    """Extract JSON object/array from JS file assignment (window.X = {...}; or const X = ...)."""
    clean_text = raw_text.strip()

    # Strip trailing semicolon
    if clean_text.endswith(";"):
        clean_text = clean_text[:-1].strip()

    # Find the opening bracket of the main data structure
    first_brace = clean_text.find("{")
    first_bracket = clean_text.find("[")

    start_idx = -1
    if first_brace != -1 and first_bracket != -1:
        start_idx = min(first_brace, first_bracket)
    elif first_brace != -1:
        start_idx = first_brace
    elif first_bracket != -1:
        start_idx = first_bracket

    if start_idx == -1:
        raise ValueError("Could not locate starting '{' or '[' in data.js")

    json_substring = clean_text[start_idx:]
    return json.loads(json_substring)


def load_universe_chains(csv_path: Path) -> set:
    """Load valid chain names from UniverseMT.csv."""
    if not csv_path.exists():
        raise FileNotFoundError(f"Universe file not found: {csv_path}")

    df_universe = pd.read_csv(csv_path)
    # Identify chain column (case-insensitive search)
    chain_col = next((c for c in df_universe.columns if "chain" in c.lower()), None)
    if not chain_col:
        chain_col = df_universe.columns[0]

    return set(df_universe[chain_col].dropna().astype(str).str.strip().unique())


def inspect_data_payload(data, valid_chains: set) -> tuple:
    """Recursively traverses the data structure to validate chains and sum offtake_units."""
    errors = []
    total_offtake_units = 0.0
    unmapped_chains_found = set()

    def walk(node):
        nonlocal total_offtake_units
        if isinstance(node, dict):
            # 1. Offtake units check
            for k, v in node.items():
                if k in ("offtake_units", "sales_qty", "units"):
                    if isinstance(v, (int, float)):
                        if not math.isnan(v):
                            total_offtake_units += v
                    elif v is not None:
                        try:
                            val = float(v)
                            total_offtake_units += val
                        except (ValueError, TypeError):
                            pass

                # 2. Chain validation
                if k in ("chain", "chain_name", "Chain", "Chain_Name"):
                    if v is None or (isinstance(v, str) and not v.strip()):
                        unmapped_chains_found.add("<NULL_OR_EMPTY>")
                    else:
                        norm_v = str(v).strip()
                        if norm_v not in valid_chains:
                            unmapped_chains_found.add(norm_v)

            # Continue walking children
            for child in node.values():
                walk(child)

        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(data)

    if unmapped_chains_found:
        errors.append(
            f"Found unmapped / invalid chains ({len(unmapped_chains_found)}): "
            f"{list(unmapped_chains_found)[:10]}"
        )

    return errors, total_offtake_units


def main():
    print("=" * 60)
    print("🔍 Starting data.js pre-smoke validation...")
    print("=" * 60)

    # 1. Check file existence
    if not DATA_JS_PATH.exists():
        print(f"❌ Error: {DATA_JS_PATH} not found.")
        sys.exit(1)

    raw_text = DATA_JS_PATH.read_text(encoding="utf-8")

    # 2. Raw token checks
    raw_errors = scan_raw_tokens(raw_text)
    if raw_errors:
        for err in raw_errors:
            print(f"❌ Token Check: {err}")
    else:
        print("✅ Raw literal scan: No NaN, undefined, or Infinity literals detected.")

    # 3. Parse JSON
    try:
        data_obj = extract_json_payload(raw_text)
        print("✅ Payload structure: Successfully parsed into valid JSON structure.")
    except Exception as e:
        print(f"❌ JSON Parse Failure: {e}")
        sys.exit(1)

    # 4. Load UniverseMT
    try:
        universe_chains = load_universe_chains(UNIVERSE_CSV_PATH)
        print(f"✅ Loaded {len(universe_chains)} valid chains from {UNIVERSE_CSV_PATH}.")
    except Exception as e:
        print(f"❌ Universe File Error: {e}")
        sys.exit(1)

    # 5. Deep semantic checks
    semantic_errors, total_units = inspect_data_payload(data_obj, universe_chains)

    # Offtake units verification
    print(f"📊 Offtake Units Computed: {int(total_units)} (Expected: {EXPECTED_OFFTAKE_UNITS})")
    if int(total_units) == EXPECTED_OFFTAKE_UNITS:
        print(f"✅ Offtake units verified: Exact match ({EXPECTED_OFFTAKE_UNITS}).")
    else:
        semantic_errors.append(
            f"Offtake units mismatch: Found {total_units}, expected {EXPECTED_OFFTAKE_UNITS}."
        )

    # Semantic errors report
    if semantic_errors:
        for err in semantic_errors:
            print(f"❌ Validation Error: {err}")

    print("=" * 60)
    if raw_errors or semantic_errors:
        print("❌ PRE-SMOKE VALIDATION FAILED. Fix highlighted data issues above.")
        sys.exit(1)
    else:
        print("✅ ALL GATES PASSED. data.js is clean for browser smoke testing.")
        sys.exit(0)


if __name__ == "__main__":
    main()
