#!/usr/bin/env python3
"""CLI: FY27 incentive decision readiness report (Phase 3B, STEP 11).

Answers "where do we stand right now?" in one glance, without exposing
more than necessary. By default this prints only decision_id, its
current_status, and the overall gate state -- never the approver name,
evidence reference, or any other field, since a status report is often
shared more widely than the register itself. Pass --verbose for the full
per-decision detail (still no employee/payout data -- this register never
holds that).

Usage:
  python3 scripts/incentive_readiness_report.py --register <path/to/register.json>
  python3 scripts/incentive_readiness_report.py --register <path> --verbose

Exit codes:
  0 = READY_FOR_SHADOW_CALCULATION
  1 = FAIL_SCHEMA (register does not conform to the schema)
  3 = any BLOCKED_* state
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from incentive_control.gate import evaluate_gate  # noqa: E402
from incentive_control.register_io import RegisterLoadError, load_register  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--register", required=True, type=Path)
    parser.add_argument("--verbose", action="store_true",
                         help="Also print approved_by/approval_date/evidence_reference per decision")
    args = parser.parse_args()

    try:
        records = load_register(args.register)
    except RegisterLoadError as e:
        print(f"FAIL_SCHEMA: {e}")
        return 1

    print("Current Decision Readiness:\n")
    width = max(len(r.decision_id) for r in records)
    for r in records:
        line = f"  {r.decision_id.ljust(width)}   {r.current_status}"
        if args.verbose and r.current_status == "APPROVED":
            line += f"   ({r.selected_response}, approved_by={r.approved_by}, {r.approval_date}, evidence={r.evidence_reference})"
        print(line)

    result = evaluate_gate(records)
    print(f"\nOVERALL: {result.state}")
    if not result.ready:
        print("\nBlocking items:")
        for b in result.blocking:
            print(f"  - {b['decision_id']}: {b['blocked_state']}")

    return 0 if result.ready else 3


if __name__ == "__main__":
    sys.exit(main())
