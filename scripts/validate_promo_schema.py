#!/usr/bin/env python3
"""
Promo Data Schema Validator — Standalone validation for monthly ingestion.
No external dependencies required (pydantic optional for advanced validation).
"""

import json
import sys
import re
from datetime import datetime


class ValidationResult:
    """Collects validation errors and warnings."""

    def __init__(self):
        self.errors = []
        self.warnings = []

    def add_error(self, msg):
        self.errors.append(msg)

    def add_warning(self, msg):
        self.warnings.append(msg)

    def is_valid(self):
        return len(self.errors) == 0

    def report(self, strict=False):
        """Print formatted report. Returns exit code."""
        if self.errors:
            print(f"❌ VALIDATION FAILED: {len(self.errors)} error(s)")
            for err in self.errors:
                print(f"   - {err}")

        if self.warnings:
            print(f"⚠️  {len(self.warnings)} warning(s)")
            for warn in self.warnings:
                print(f"   - {warn}")

        if not self.errors and not self.warnings:
            print("✅ VALIDATION PASSED")
            return 0

        if self.errors:
            return 1

        if self.warnings and strict:
            return 2

        return 0


def validate_month_format(month_str):
    """Validate month format: 'MMM-YY' (e.g., 'Apr-26', 'Sep-26')."""
    pattern = r'^[A-Z][a-z]{2}-\d{2}$'
    return bool(re.match(pattern, month_str))


def validate_chain_name(chain_name, canonical_chains=None):
    """Validate chain name against canonical list (if provided)."""
    if not isinstance(chain_name, str) or len(chain_name) == 0:
        return False

    if canonical_chains is not None:
        return chain_name in canonical_chains

    return True


def validate_discount_depth(depth):
    """Validate discount depth: 0-100% as float or int."""
    try:
        d = float(depth)
        return 0 <= d <= 100
    except (ValueError, TypeError):
        return False


def validate_json_data(filepath):
    """Validate data_master.json structure (if exists)."""
    result = ValidationResult()

    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        result.add_warning(f"File not found: {filepath}")
        return result
    except json.JSONDecodeError as e:
        result.add_error(f"Invalid JSON: {e}")
        return result

    # Validate promo block
    if 'promo' not in data:
        result.add_error("Missing 'promo' key in data")
        return result

    promo = data['promo']

    # Validate required fields
    required_fields = ['n_promos', 'avg_depth', 'by_chain', 'months_available', 'monthly']
    for field in required_fields:
        if field not in promo:
            result.add_error(f"Promo: missing required field '{field}'")

    # Validate numeric ranges
    if 'avg_depth' in promo:
        if not validate_discount_depth(promo['avg_depth']):
            result.add_error(f"Promo avg_depth out of range: {promo['avg_depth']}")

    if 'n_promos' in promo:
        if not isinstance(promo['n_promos'], int) or promo['n_promos'] < 0:
            result.add_error(f"Promo n_promos must be non-negative int: {promo['n_promos']}")

    # Validate by_chain structure
    if 'by_chain' in promo:
        chains = promo['by_chain']
        if not isinstance(chains, list):
            result.add_error("Promo by_chain must be a list")
        else:
            for chain in chains:
                if 'name' not in chain:
                    result.add_error("Chain missing 'name' field")
                if 'promos' not in chain or not isinstance(chain['promos'], int):
                    result.add_error(f"Chain {chain.get('name', '?')}: invalid promos count")

    # Validate monthly blocks
    if 'months_available' in promo and 'monthly' in promo:
        months = promo['months_available']
        monthly = promo['monthly']

        for month in months:
            if not validate_month_format(month):
                result.add_warning(f"Invalid month format: {month}")
            if month not in monthly:
                result.add_error(f"Month {month} in months_available but not in monthly")

    return result


def validate_data_js_integrity(filepath):
    """Validate data.js file: valid JSON wrapped in 'window.DASH = {...}'."""
    result = ValidationResult()

    try:
        with open(filepath, 'r') as f:
            content = f.read()
    except FileNotFoundError:
        result.add_warning(f"File not found: {filepath}")
        return result

    # Extract JSON from window.DASH = {...}
    match = re.search(r'window\.DASH\s*=\s*(\{.*\})\s*;', content, re.DOTALL)
    if not match:
        result.add_error("Could not find 'window.DASH = {...}' in data.js")
        return result

    json_str = match.group(1)

    # Validate JSON parsing
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        result.add_error(f"data.js contains invalid JSON: {e}")
        return result

    # Check for rendered NaN/undefined (quoted strings)
    if '"NaN"' in content or '"undefined"' in content or '"[object Object]"' in content:
        result.add_error("data.js contains quoted NaN/undefined/[object Object] (rendering error)")

    # Unquoted NaN in article metadata is expected; warn but don't error
    if re.search(r':\s*NaN(?!\s*[a-z])', content):
        result.add_warning("Unquoted NaN detected (expected for article metadata)")

    return result


def validate_Sep26_mock_data():
    """Validate structure of mock Sep '26 data for testing."""
    result = ValidationResult()

    # Mock Sep '26 promo data structure
    mock_sep26 = {
        'promo': {
            'n_promos': 1389,
            'avg_depth': 43.1,
            'total_skus': 1389,
            'chains_in_promo': 34,
            'by_chain': [
                {
                    'name': 'Modern Retail',
                    'kam': 'Sheshant K',
                    'promos': 145,
                    'skus': 156,
                    'brands': 12,
                    'avg_offer_pct': 41.2,
                    'received': True
                },
                {
                    'name': 'Kiryana Premium',
                    'kam': 'Raj M',
                    'promos': 89,
                    'skus': 92,
                    'brands': 8,
                    'avg_offer_pct': 55.3,
                    'received': True
                }
            ],
            'months_available': ['Apr-26', 'May-26', 'Jun-26', 'Jul-26', 'Aug-26', 'Sep-26'],
            'monthly': {
                'Sep-26': {
                    'month': 'Sep-26',
                    'total_skus': 1389,
                    'chains_in_promo': 34,
                    'by_chain': []
                }
            }
        }
    }

    # Validate mock structure
    try:
        validate_json_data_inline(mock_sep26)
        result.add_warning("Mock Sep '26 data validated (structure OK)")
    except Exception as e:
        result.add_error(f"Mock Sep '26 data structure invalid: {e}")

    return result


def validate_json_data_inline(data):
    """Inline validation of parsed JSON data (for testing)."""
    if 'promo' not in data:
        raise ValueError("Missing 'promo' key")

    promo = data['promo']

    # Check required fields
    for field in ['n_promos', 'avg_depth', 'by_chain', 'months_available', 'monthly']:
        if field not in promo:
            raise ValueError(f"Missing required field: {field}")

    # Validate ranges
    if not (0 <= promo['avg_depth'] <= 100):
        raise ValueError(f"avg_depth out of range: {promo['avg_depth']}")


def main():
    """CLI interface for validation."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Validate promo data schema for monthly ingestion'
    )
    parser.add_argument(
        '--json',
        type=str,
        help='Path to data_master.json to validate'
    )
    parser.add_argument(
        '--datajs',
        type=str,
        help='Path to data.js to validate'
    )
    parser.add_argument(
        '--strict',
        action='store_true',
        help='Treat warnings as errors (exit code 2)'
    )
    parser.add_argument(
        '--mock-sep26',
        action='store_true',
        help='Validate mock Sep \'26 data structure'
    )

    args = parser.parse_args()

    all_results = []

    if args.json:
        print(f"Validating {args.json}...")
        result = validate_json_data(args.json)
        all_results.append(result)
        print(result.report(args.strict))
        print()

    if args.datajs:
        print(f"Validating {args.datajs}...")
        result = validate_data_js_integrity(args.datajs)
        all_results.append(result)
        print(result.report(args.strict))
        print()

    if args.mock_sep26:
        print("Validating mock Sep '26 data structure...")
        result = validate_Sep26_mock_data()
        all_results.append(result)
        print(result.report(args.strict))
        print()

    if not all_results:
        print("No validation target specified. Use --json, --datajs, or --mock-sep26")
        return 1

    # Return most severe exit code
    exit_codes = [r.report(args.strict) for r in all_results]
    return max(exit_codes)


if __name__ == '__main__':
    sys.exit(main())
