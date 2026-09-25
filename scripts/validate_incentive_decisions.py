#!/usr/bin/env python3
"""CLI: validate a FY27 incentive decision register (Phase 3A, STEP 3).

Validates a supplied register file WITHOUT containing any real restricted
data itself -- the register path is always an explicit argument, never a
default pointing at incentive_working/ (that directory is gitignored and
this script must run cleanly in CI without it).

Usage:
  python3 scripts/validate_incentive_decisions.py --register <path/to/register.json>

Exit codes:
  0 = PASS
  1 = FAIL_VALIDATION (schema-valid but internally inconsistent register)
  2 = FAIL_SCHEMA (register does not conform to schemas/fy27_incentive_decision.schema.json)
  3 = BLOCKED_BASIS_CONFLICT (D1A/D1B both approved but disagree)
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from incentive_control.register_io import RegisterLoadError, load_register
from incentive_control.validator import validate_register


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--register", required=True, type=Path,
                         help="Path to a decision register JSON file (schema: "
                              "schemas/fy27_incentive_decision.schema.json)")
    args = parser.parse_args()

    try:
        records = load_register(args.register)
    except RegisterLoadError as e:
        print(f"FAIL_SCHEMA: {e}")
        return 2

    report = validate_register(records)
    report.print_report()

    if report.status == "PASS":
        return 0
    if report.status == "BLOCKED_BASIS_CONFLICT":
        return 3
    return 1


if __name__ == "__main__":
    sys.exit(main())
