#!/usr/bin/env python3
"""CLI: FY27 incentive decision closure gate (Phase 3A, STEP 4).

Answers whether the register is READY_FOR_SHADOW_CALCULATION or which
BLOCKED_* state applies. Never calculates a payout or a shadow figure
itself -- see scripts/incentive_control/gate.py for the full contract.

Usage:
  python3 scripts/incentive_decision_gate.py --register <path/to/register.json>

Exit codes:
  0 = READY_FOR_SHADOW_CALCULATION
  1 = FAIL_SCHEMA (register does not conform to the schema)
  3 = any BLOCKED_* state (see printed report for which)
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from incentive_control.gate import evaluate_gate
from incentive_control.register_io import RegisterLoadError, load_register


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
        return 1

    result = evaluate_gate(records)
    result.print_report()

    return 0 if result.ready else 3


if __name__ == "__main__":
    sys.exit(main())
