#!/usr/bin/env python3
"""CLI: record ONE human response into a FY27 incentive decision register
(Phase 3B, STEP 3).

This is the ONLY sanctioned way a response enters the register -- no
decision may be hand-edited into the JSON, and no agent or script may set
current_status to APPROVED except through this helper's explicit,
fully-supplied fields. It contains no actual decisions itself; every value
comes from the command line, supplied by a person transcribing a real
response (or, in tests, a synthetic fixture value).

It never silently overwrites an existing APPROVED decision: changing one
requires --reason and a NEW --evidence-reference, and the prior approval
is preserved in that decision's revision_history, never discarded.

Usage (new approval):
  python3 scripts/record_incentive_decision.py \
    --register <path/to/register.json> \
    --decision-id NC-01 \
    --status APPROVED \
    --selected-response H1_ONLY \
    --approved-by "Jane Leadership" \
    --approval-date 2026-10-01 \
    --evidence-reference "email-thread-2026-09-30-nc01"

Usage (amending an already-APPROVED decision):
  ... same flags, plus --reason "corrected after follow-up call" --amend

Usage (recording an ambiguous reply):
  python3 scripts/record_incentive_decision.py \
    --register <path> --decision-id TG-03 --status CLARIFICATION_REQUIRED \
    --notes "reply did not map to an allowed token, asked for clarification"

Exit codes:
  0 = recorded (or no-op: identical re-submission of an existing APPROVED row)
  1 = FAIL_SCHEMA / FAIL_VALIDATION (register invalid before or after the change)
  2 = TransitionError (structurally disallowed status move)
  3 = AmendmentRequiredError (would silently overwrite an APPROVED decision)
  4 = decision_id not found in the register, or response not in its allowed_responses
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from incentive_control.gate import evaluate_gate  # noqa: E402
from incentive_control.register_io import (  # noqa: E402
    RegisterLoadError,
    load_register,
    load_register_raw,
    save_register_raw,
)
from incentive_control.transitions import (  # noqa: E402
    AmendmentRequiredError,
    TransitionError,
    requires_amendment,
    validate_transition,
)
from incentive_control.validator import validate_register  # noqa: E402


def _is_iso_date(value: str) -> bool:
    try:
        date.fromisoformat(value)
        return True
    except (ValueError, TypeError):
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--register", required=True, type=Path)
    parser.add_argument("--decision-id", required=True)
    parser.add_argument("--status", default="APPROVED",
                         choices=["APPROVED", "REJECTED", "NOT_APPLICABLE",
                                  "CLARIFICATION_REQUIRED", "PENDING_LEADERSHIP", "PENDING_FINANCE"])
    parser.add_argument("--selected-response", default=None)
    parser.add_argument("--approved-by", default=None)
    parser.add_argument("--approval-date", default=None)
    parser.add_argument("--evidence-reference", default=None)
    parser.add_argument("--reason", default=None,
                         help="Required when amending an already-APPROVED decision")
    parser.add_argument("--notes", default=None)
    args = parser.parse_args()

    try:
        raw = load_register_raw(args.register)
    except RegisterLoadError as e:
        print(f"FAIL_SCHEMA: {e}")
        return 1

    entry = next((d for d in raw["decisions"] if d["decision_id"] == args.decision_id), None)
    if entry is None:
        print(f"NOT_FOUND: {args.decision_id} is not present in this register -- "
              f"no decision may be recorded that wasn't already tracked")
        return 4

    if args.status == "APPROVED":
        missing = [name for name, val in [
            ("--selected-response", args.selected_response),
            ("--approved-by", args.approved_by),
            ("--approval-date", args.approval_date),
            ("--evidence-reference", args.evidence_reference),
        ] if not val or not str(val).strip()]
        if missing:
            print(f"FAIL: --status APPROVED requires all of: {', '.join(missing)} (none may be blank)")
            return 4
        if args.selected_response not in entry["allowed_responses"]:
            print(f"FAIL: '{args.selected_response}' is not in {args.decision_id}'s "
                  f"allowed_responses {entry['allowed_responses']}")
            return 4
        if not _is_iso_date(args.approval_date):
            print(f"FAIL: --approval-date '{args.approval_date}' is not a valid ISO date")
            return 4

    current_status = entry["current_status"]
    current_response = entry.get("selected_response")
    new_response = args.selected_response if args.status == "APPROVED" else None

    # Idempotent re-submission: identical status/response/approver/date/evidence
    # as what's already recorded -- a no-op, never treated as a duplicate
    # approval or a change requiring amendment.
    if (args.status == current_status == "APPROVED"
            and new_response == current_response
            and args.approved_by == entry.get("approved_by")
            and args.approval_date == entry.get("approval_date")
            and args.evidence_reference == entry.get("evidence_reference")):
        print(f"NO_CHANGE: {args.decision_id} already APPROVED with identical response/approver/"
              f"date/evidence -- nothing to record (idempotent re-submission)")
        return 0

    amendment_needed = requires_amendment(current_status, current_response, args.status, new_response)

    # An amendment is properly evidenced only when BOTH a reason is given
    # AND a genuinely new evidence reference is supplied -- reusing the
    # prior approval's own evidence_reference would make the "new" entry
    # indistinguishable from the one it's meant to supersede.
    has_amendment_fields = (
        bool(args.reason and args.reason.strip())
        and bool(args.evidence_reference and args.evidence_reference.strip())
        and args.evidence_reference != entry.get("evidence_reference")
    )

    try:
        validate_transition(
            current_status, args.status,
            has_amendment_fields=has_amendment_fields,
            current_response=current_response, new_response=new_response,
        )
    except TransitionError as e:
        print(f"BLOCKED_TRANSITION: {e}")
        return 2
    except AmendmentRequiredError as e:
        print(f"AMENDMENT_REQUIRED: {e}")
        return 3

    if amendment_needed:
        history = entry.setdefault("revision_history", [])
        next_version = len(history) + 2  # version 1 = the original approval, never itself an entry
        history.append({
            "decision_version": next_version,
            "previous_response": current_response if current_response is not None else "(none)",
            "new_response": new_response if new_response is not None else "(none)",
            "changed_by": args.approved_by or "(unspecified)",
            "changed_date": args.approval_date or date.today().isoformat(),
            "change_evidence": args.evidence_reference or "(unspecified)",
            "reason": args.reason,
        })

    entry["current_status"] = args.status
    if args.status == "APPROVED":
        entry["selected_response"] = args.selected_response
        entry["approved_by"] = args.approved_by
        entry["approval_date"] = args.approval_date
        entry["evidence_reference"] = args.evidence_reference
        entry["business_rule_result"] = f"selected_response={args.selected_response}"
    else:
        entry["selected_response"] = None
        entry["business_rule_result"] = None
        # approved_by/approval_date/evidence_reference deliberately left as-is
        # (or None) -- CLARIFICATION_REQUIRED etc. don't require them, and if
        # a decision is being moved OFF a prior APPROVED via --status REJECTED
        # or similar, the amendment history above already preserved the facts.
        if args.status not in ("APPROVED",):
            entry["approved_by"] = None
            entry["approval_date"] = None
            entry["evidence_reference"] = None
    if args.notes:
        entry["notes"] = args.notes

    # Re-validate the WHOLE register before writing anything -- a single
    # decision update must not silently push the file into an inconsistent
    # state (e.g. two decisions ending up with the exact same evidence).
    # Round-trip the in-memory, post-edit `raw` dict through a temp file so
    # validate_register() sees the change we just made, without writing to
    # the real register path until validation confirms it's safe to.
    import json
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(raw, f)
        tmp_path = Path(f.name)
    try:
        updated_records = load_register(tmp_path)
    except RegisterLoadError as e:
        tmp_path.unlink(missing_ok=True)
        print(f"FAIL_SCHEMA (post-update): {e}")
        return 1
    tmp_path.unlink(missing_ok=True)

    report = validate_register(updated_records)
    if not report.passed and report.status != "BLOCKED_BASIS_CONFLICT":
        print(f"FAIL_VALIDATION (post-update, not written): {report.status}")
        for p in report.problems:
            print(f"  - {p}")
        return 1

    save_register_raw(args.register, raw)

    gate_result = evaluate_gate(updated_records)
    print(f"RECORDED: {args.decision_id} -> {args.status}"
          + (f" (amendment v{entry.get('revision_history', [{}])[-1].get('decision_version')})" if amendment_needed else ""))
    print(f"Register validation: {report.status}")
    print(f"Closure gate: {gate_result.state}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
