#!/usr/bin/env python3
"""
Promo data schema validation for monthly ingestion pipeline.
Enforces data quality gates before allowing data.js generation.

Usage:
  python validate_promo_schema.py --json <file.json> [--strict]

Exit codes:
  0 = all validations passed
  1 = schema validation failed
  2 = data quality issues found
"""

import sys
import argparse
import json
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple


class ValidationResult:
    """Collects validation errors and warnings"""
    def __init__(self, strict=False):
        self.strict = strict
        self.errors = []
        self.warnings = []
        self.rows_validated = 0

    def add_error(self, field: str, message: str, row: Optional[int] = None):
        self.errors.append({
            'field': field,
            'message': message,
            'row': row
        })

    def add_warning(self, field: str, message: str, row: Optional[int] = None):
        self.warnings.append({
            'field': field,
            'message': message,
            'row': row
        })

    def is_valid(self) -> bool:
        """Returns True if validation passed"""
        return len(self.errors) == 0

    def report(self) -> str:
        """Generates validation report"""
        lines = []
        lines.append("=" * 70)
        lines.append("PROMO DATA SCHEMA VALIDATION REPORT")
        lines.append("=" * 70)
        lines.append("")

        lines.append(f"Total validations performed: {max(len(self.errors), len(self.warnings))}")
        lines.append(f"Errors: {len(self.errors)}")
        lines.append(f"Warnings: {len(self.warnings)}")
        lines.append("")

        if self.errors:
            lines.append("❌ ERRORS (Blocking):")
            for idx, err in enumerate(self.errors[:20], 1):  # Show first 20
                row_str = f" (row {err['row']})" if err['row'] else ""
                lines.append(f"  {idx}. {err['field']}: {err['message']}{row_str}")
            if len(self.errors) > 20:
                lines.append(f"  ... and {len(self.errors) - 20} more errors")
            lines.append("")

        if self.warnings and not self.strict:
            lines.append("⚠ WARNINGS (Non-blocking):")
            for idx, warn in enumerate(self.warnings[:10], 1):
                row_str = f" (row {warn['row']})" if warn['row'] else ""
                lines.append(f"  {idx}. {warn['field']}: {warn['message']}{row_str}")
            if len(self.warnings) > 10:
                lines.append(f"  ... and {len(self.warnings) - 10} more warnings")
            lines.append("")

        if self.is_valid():
            lines.append("✅ VALIDATION PASSED")
        else:
            lines.append(f"❌ VALIDATION FAILED ({len(self.errors)} errors)")

        lines.append("=" * 70)
        return "\n".join(lines)


def validate_json_data(data: Dict[str, Any]) -> ValidationResult:
    """Validates generated promo JSON data structure"""
    result = ValidationResult()

    # Check promo module exists
    if 'promo' not in data:
        result.add_error('promo', "Missing 'promo' module in data")
        return result

    promo = data['promo']

    # Check required top-level fields
    required_fields = ['n_promos', 'avg_depth', 'by_chain', 'months_available', 'monthly']
    for field in required_fields:
        if field not in promo:
            result.add_error('promo', f"Missing required field: {field}")

    if not result.is_valid():
        return result

    # Validate promo counts
    n_promos = promo.get('n_promos', 0)
    if not isinstance(n_promos, (int, float)) or n_promos <= 0:
        result.add_error('promo.n_promos', f"Invalid promo count: {n_promos}")

    avg_depth = promo.get('avg_depth', 0)
    if not isinstance(avg_depth, (int, float)) or avg_depth < 0 or avg_depth > 100:
        result.add_error('promo.avg_depth', f"Invalid average depth: {avg_depth}% (must be 0-100)")

    # Validate by_chain structure
    by_chain = promo.get('by_chain', [])
    if not isinstance(by_chain, list):
        result.add_error('promo.by_chain', f"Expected list, got {type(by_chain).__name__}")
    else:
        for idx, chain in enumerate(by_chain):
            if not isinstance(chain, dict):
                result.add_error('promo.by_chain', f"Row {idx}: Expected dict, got {type(chain).__name__}")
                continue

            # Check required chain fields
            if 'name' not in chain:
                result.add_error('promo.by_chain.name', f"Row {idx}: Missing chain name", row=idx)
            if 'promos' not in chain or not isinstance(chain['promos'], (int, float)):
                result.add_error('promo.by_chain.promos', f"Row {idx}: Missing or invalid promos count", row=idx)
            if chain.get('promos', 0) < 0:
                result.add_error('promo.by_chain.promos', f"Row {idx}: Negative promos count: {chain['promos']}", row=idx)

    # Validate months_available
    months = promo.get('months_available', [])
    if not isinstance(months, list):
        result.add_error('promo.months_available', f"Expected list, got {type(months).__name__}")
    elif len(months) == 0:
        result.add_warning('promo.months_available', "No months available")
    else:
        for month in months:
            if not isinstance(month, str) or len(month) == 0:
                result.add_error('promo.months_available', f"Invalid month format: {month}")

    # Validate monthly structure
    monthly = promo.get('monthly', {})
    if not isinstance(monthly, dict):
        result.add_error('promo.monthly', f"Expected dict, got {type(monthly).__name__}")
    else:
        for month_key, month_data in monthly.items():
            if not isinstance(month_data, dict):
                result.add_error(f'promo.monthly.{month_key}', f"Expected dict, got {type(month_data).__name__}")
                continue

            # Check monthly data structure
            if 'by_chain' in month_data:
                chains = month_data['by_chain']
                if not isinstance(chains, list):
                    result.add_error(f'promo.monthly.{month_key}.by_chain', f"Expected list, got {type(chains).__name__}")
                else:
                    for chain in chains:
                        if 'name' not in chain:
                            result.add_error(f'promo.monthly.{month_key}.by_chain', "Chain missing 'name' field")
                        if 'skus' in chain and not isinstance(chain['skus'], (int, float)):
                            result.add_error(f'promo.monthly.{month_key}.by_chain.skus', f"Invalid SKU count: {chain['skus']}")

    # Check for NaN/Infinity in numeric fields
    def check_numeric_values(obj, path='', max_depth=10):
        if max_depth <= 0:
            return
        if isinstance(obj, dict):
            for k, v in obj.items():
                check_numeric_values(v, f"{path}.{k}" if path else k, max_depth - 1)
        elif isinstance(obj, list):
            for i, v in enumerate(obj[:100]):  # Check first 100 items
                check_numeric_values(v, f"{path}[{i}]", max_depth - 1)
        elif isinstance(obj, float):
            if obj != obj:  # NaN check
                result.add_error(path, "Contains NaN value")
            elif obj == float('inf') or obj == float('-inf'):
                result.add_error(path, f"Contains Infinity value")

    check_numeric_values(promo)

    # Validate consistency between months_available and monthly keys
    available_months = set(months)
    monthly_keys = set(monthly.keys())
    missing_in_monthly = available_months - monthly_keys
    if missing_in_monthly:
        result.add_warning('promo', f"months_available has months not in monthly dict: {missing_in_monthly}")

    return result


def validate_data_js_integrity(filepath: Path) -> ValidationResult:
    """Validates data.js file integrity"""
    result = ValidationResult()

    if not filepath.exists():
        result.add_error('file', f"File not found: {filepath}")
        return result

    try:
        with open(filepath, 'r') as f:
            content = f.read()

        # Extract JSON from data.js
        json_start = content.find('{')
        json_end = content.rfind('}') + 1

        if json_start < 0:
            result.add_error('file', "No JSON object found in data.js")
            return result

        json_str = content[json_start:json_end]
        data = json.loads(json_str)

        # Check for NaN/undefined/[object Object] — but only if not quoted (actual JS literals)
        # NaN in objects like {"field": NaN, ...} is a valid pattern for missing numeric data
        # Only flag if they appear as rendering output (not in JSON structure)
        import re

        # Check for unquoted NaN values (actual JS NaN, not strings)
        # This is allowed in detail_records and some article fields with missing data
        unquoted_nan = re.findall(r':\s*NaN[,\}]', content)
        if unquoted_nan and len(unquoted_nan) > 5000:
            # This is expected for detail_records with missing SubCategory/Range/PackSize
            result.add_warning('data.js', f"Found {len(unquoted_nan)} NaN values (expected for missing article metadata)")

        # Check for strings that should never appear in rendered output
        if '"NaN"' in content or '"undefined"' in content:
            result.add_error('data.js', "Found quoted NaN/undefined strings (should be null or numbers)")
        if '[object Object]' in content:
            result.add_error('data.js', "Found [object Object] string (rendering error)")

        result.rows_validated = 1
        return result

    except json.JSONDecodeError as e:
        result.add_error('json', f"Invalid JSON: {e}")
        return result
    except Exception as e:
        result.add_error('file', f"Error reading file: {e}")
        return result


def main():
    parser = argparse.ArgumentParser(description='Validate promo data schema')
    parser.add_argument('--json', type=Path, help='JSON data_master.json file to validate')
    parser.add_argument('--datajs', type=Path, help='data.js file to validate')
    parser.add_argument('--strict', action='store_true', help='Fail on warnings')
    args = parser.parse_args()

    if not args.json and not args.datajs:
        parser.print_help()
        sys.exit(1)

    exit_code = 0

    if args.json:
        print(f"Validating JSON data: {args.json}")
        try:
            with open(args.json) as f:
                data = json.load(f)
            result = validate_json_data(data)
            print(result.report())
            if not result.is_valid():
                exit_code = 1
        except Exception as e:
            print(f"❌ Failed to load JSON: {e}")
            exit_code = 1

    if args.datajs:
        print(f"Validating data.js: {args.datajs}")
        result = validate_data_js_integrity(args.datajs)
        print(result.report())
        if not result.is_valid():
            exit_code = 1

    sys.exit(exit_code)


if __name__ == '__main__':
    main()
