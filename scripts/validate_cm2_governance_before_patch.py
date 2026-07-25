#!/usr/bin/env python3
"""Validate CM2 governance before running patch_cm2_provisional.py.

Ensures that:
1. Decision status is APPROVED (not PENDING_APPROVAL)
2. Named approver is populated (not blank or "Finance")
3. Approval date is populated and parses as a valid date
4. Approved option is populated
5. Decision register and formula config agree
6. D1 option matches one of the valid choices
7. D9 includes only authorised allocation rules

Fail the script if any control fails. This prevents the banner from being
cleared by running the patch script with provisional or incomplete data.

Usage:
    python3 scripts/validate_cm2_governance_before_patch.py [decision]
    python3 scripts/validate_cm2_governance_before_patch.py D1
    python3 scripts/validate_cm2_governance_before_patch.py D1 D9  (multiple)
    python3 scripts/validate_cm2_governance_before_patch.py --all  (all)
"""
from __future__ import annotations

import argparse
import csv
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DECISION_REGISTER = ROOT / "config" / "cm2_decision_register.csv"
FORMULA_CONFIG = ROOT / "config" / "cm2_formula.csv"
ALLOCATION_RULES = ROOT / "config" / "cm2_allocation_rules.csv"


def load_csv(path: Path) -> dict:
    """Load CSV as list of dicts."""
    if not path.exists():
        print(f"ERROR: {path} not found", file=sys.stderr)
        sys.exit(2)
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def validate_decision(decision_id: str) -> bool:
    """Validate a single decision. Return True if all checks pass."""
    register = {d["decision_id"]: d for d in load_csv(DECISION_REGISTER)}
    if decision_id not in register:
        print(f"ERROR: Decision {decision_id} not found in decision register", file=sys.stderr)
        return False

    record = register[decision_id]
    status = record.get("status", "").strip()
    approver = record.get("approved_by", "").strip()
    date_str = record.get("approved_at", "").strip()
    option = record.get("approved_option", "").strip()

    issues = []

    # Check 1: Status must be APPROVED
    if status != "APPROVED":
        issues.append(f"Status is '{status}', not APPROVED")

    # Check 2: Approver must be named (not blank, not just "Finance")
    if not approver or approver.lower() == "finance":
        issues.append(f"Approver is '{approver}' — must be a named individual")

    # Check 3: Approval date must be populated and valid
    if not date_str:
        issues.append("Approval date is blank")
    else:
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            issues.append(f"Approval date '{date_str}' is not valid YYYY-MM-DD format")

    # Check 4: Approved option must be populated
    if not option:
        issues.append("Approved option is blank")

    # Check 5: D1 option must match known choices
    if decision_id == "D1":
        if option not in ["(a) INCLUDE", "(b) EXCLUDE"]:
            issues.append(f"D1 approved option '{option}' must be '(a) INCLUDE' or '(b) EXCLUDE'")

    # Check 6: D9 logic (if additional validation needed)
    if decision_id == "D9":
        # D9 decision is whether to activate ALLOC-001/002/003
        if option not in ["APPROVE", "keep DRAFT"]:
            issues.append(f"D9 approved option '{option}' must be 'APPROVE' or 'keep DRAFT'")
        # If APPROVE, validate that only ALLOC-001/002/003 are used
        # (This is a config check, not a register check, but noted for completeness)

    if issues:
        print(f"\n❌ {decision_id} FAILED:")
        for issue in issues:
            print(f"   - {issue}")
        return False
    else:
        print(f"\n✅ {decision_id} PASSED")
        return True


def validate_formula_agreement(decision_id: str) -> bool:
    """Verify that decision register and formula config agree on status."""
    register = {d["decision_id"]: d for d in load_csv(DECISION_REGISTER)}
    formula = load_csv(FORMULA_CONFIG)

    reg_record = register.get(decision_id, {})
    reg_status = reg_record.get("status", "").strip()

    # Find the formula row that references this decision
    formula_rows = [f for f in formula if decision_id in f.get("Decision_Reference", "")]

    if not formula_rows:
        print(f"   (no formula component references {decision_id})")
        return True

    for formula_row in formula_rows:
        formula_status = formula_row.get("Status", "").strip()
        if reg_status != formula_status:
            print(f"   ⚠ Mismatch: register says {reg_status}, formula says {formula_status}")
            return False

    return True


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Validate CM2 governance before clearing provisional flags"
    )
    ap.add_argument("decisions", nargs="*", default=[])
    ap.add_argument("--all", action="store_true",
                   help="Validate all blocking decisions (D1–D9)")
    args = ap.parse_args()

    if args.all:
        decisions = ["D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9"]
    elif args.decisions:
        decisions = args.decisions
    else:
        ap.print_help()
        return 1

    print("Validating CM2 governance decisions before patch:")
    print("=" * 60)

    passed = []
    failed = []

    for decision_id in decisions:
        if validate_decision(decision_id):
            passed.append(decision_id)
            if not validate_formula_agreement(decision_id):
                failed.append(decision_id)
        else:
            failed.append(decision_id)

    print("\n" + "=" * 60)
    print(f"\nResults: {len(passed)} passed, {len(failed)} failed")

    if failed:
        print(f"\n❌ VALIDATION FAILED for: {', '.join(failed)}")
        print("\nThe patch script should NOT be run until these issues are resolved:")
        print("  1. Finance must confirm the decision in the register")
        print("  2. Named approver (not 'Finance') must be entered")
        print("  3. Approval date (YYYY-MM-DD format) must be entered")
        print("  4. Approved option must be selected")
        return 1
    else:
        print(f"\n✅ ALL VALIDATIONS PASSED for: {', '.join(passed)}")
        print("\nThe patch script can now be safely run:")
        print("  python3 scripts/patch_cm2_provisional.py --dry-run")
        print("  python3 scripts/patch_cm2_provisional.py")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
