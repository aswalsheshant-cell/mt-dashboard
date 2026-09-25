"""Decision-register validator (Phase 3A, STEP 3).

Validates a parsed register (List[DecisionRecord]) for internal
consistency. This is deliberately separate from register_io.load_register()'s
JSON-Schema check: schema validation catches structurally malformed files
(FAIL_SCHEMA); this module catches semantically inconsistent ones (a
schema-valid row that is still, e.g., APPROVED with no approver).

Output is deterministic: one overall status string plus an ordered list of
problem strings. The overall status is one of:
    PASS
    BLOCKED_LEADERSHIP_DECISION
    BLOCKED_FINANCE_INPUT
    BLOCKED_BASIS_CONFLICT
    FAIL_VALIDATION   (a validator-level defect: duplicate IDs, unsupported
                        ID, malformed data -- distinct from a business
                        decision being blocked)

Never raises for a normal blocked/pending register -- that is the expected,
correct state while decisions are outstanding. It raises only via the
underlying register_io on a schema-invalid file.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import List

from .models import (
    REQUIRED_DECISIONS,
    UNRESOLVED_STATUSES,
    VALID_STATUSES,
    DecisionRecord,
)


@dataclass
class ValidationReport:
    status: str
    problems: List[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.status == "PASS"

    def print_report(self) -> None:
        print(f"Decision register validation: {self.status}")
        for p in self.problems:
            print(f"  - {p}")


def _is_iso_date(value: str) -> bool:
    try:
        date.fromisoformat(value)
        return True
    except (ValueError, TypeError):
        return False


def validate_register(records: List[DecisionRecord]) -> ValidationReport:
    problems: List[str] = []

    # 1. duplicate Decision_ID
    seen_ids = {}
    for r in records:
        seen_ids.setdefault(r.decision_id, 0)
        seen_ids[r.decision_id] += 1
    for decision_id, count in seen_ids.items():
        if count > 1:
            problems.append(f"duplicate Decision_ID: {decision_id} appears {count} times")

    # 12. unsupported decision ID
    for r in records:
        if r.decision_id not in REQUIRED_DECISIONS:
            problems.append(f"unsupported Decision_ID: {r.decision_id} not in REQUIRED_DECISIONS")

    for r in records:
        if r.decision_id not in REQUIRED_DECISIONS:
            continue  # already flagged above; downstream checks all read the record directly

        # 14. blank required fields
        if not r.decision_owner or not r.decision_owner.strip():
            problems.append(f"{r.decision_id}: blank decision_owner")
        if not r.affected_period or not r.affected_period.strip():
            problems.append(f"{r.decision_id}: blank affected_period")
        if not r.allowed_responses:
            problems.append(f"{r.decision_id}: allowed_responses is empty")

        # 2. invalid status
        if r.current_status not in VALID_STATUSES:
            problems.append(f"{r.decision_id}: invalid current_status '{r.current_status}'")
            continue  # further status-dependent checks are meaningless

        # 3 / 7. response not in allowed_responses (when a response is set)
        if r.selected_response is not None and r.selected_response not in r.allowed_responses:
            problems.append(
                f"{r.decision_id}: selected_response '{r.selected_response}' not in "
                f"allowed_responses {r.allowed_responses}"
            )

        # 13. ambiguous free-text response never silently resolves a decision
        if r.current_status == "CLARIFICATION_REQUIRED" and r.selected_response is not None \
                and r.selected_response in r.allowed_responses:
            problems.append(
                f"{r.decision_id}: CLARIFICATION_REQUIRED but selected_response is a valid "
                f"token ({r.selected_response}) -- status should have moved to APPROVED/REJECTED "
                f"once the response was unambiguous, not stayed CLARIFICATION_REQUIRED"
            )

        # 4/5/6. APPROVED without approver / date / evidence
        if r.current_status == "APPROVED":
            if not r.approved_by or not r.approved_by.strip():
                problems.append(f"{r.decision_id}: APPROVED without approved_by")
            if not r.approval_date or not r.approval_date.strip():
                problems.append(f"{r.decision_id}: APPROVED without approval_date")
            elif not _is_iso_date(r.approval_date):
                problems.append(f"{r.decision_id}: approval_date '{r.approval_date}' is not a valid ISO date")
            if not r.evidence_reference or not r.evidence_reference.strip():
                problems.append(f"{r.decision_id}: APPROVED without evidence_reference")
            if not r.selected_response or not r.selected_response.strip():
                problems.append(f"{r.decision_id}: APPROVED without selected_response")

        # 10. malformed dates (even outside APPROVED, a populated date must be valid)
        if r.approval_date and not _is_iso_date(r.approval_date):
            problems.append(f"{r.decision_id}: malformed approval_date '{r.approval_date}'")

        # business_rule_result must be null while unresolved
        if r.current_status in UNRESOLVED_STATUSES and r.business_rule_result:
            problems.append(
                f"{r.decision_id}: status is {r.current_status} but business_rule_result is "
                f"populated ('{r.business_rule_result}') -- an unresolved decision must not "
                f"carry a business-rule outcome"
            )

    # 8. missing required decision (every REQUIRED_DECISIONS key must appear at least once)
    present_ids = {r.decision_id for r in records}
    for decision_id in REQUIRED_DECISIONS:
        if decision_id not in present_ids:
            problems.append(f"missing required decision: {decision_id} not present in register")

    # 9. conflicting D1A/D1B
    d1a = next((r for r in records if r.decision_id == "D1A"), None)
    d1b = next((r for r in records if r.decision_id == "D1B"), None)
    if d1a and d1b and d1a.is_fully_approved() and d1b.is_fully_approved():
        if d1a.selected_response != d1b.selected_response:
            problems.append(
                f"D1A/D1B conflict: Leadership selected {d1a.selected_response!r}, "
                f"Finance selected {d1b.selected_response!r} -- BLOCKED_BASIS_CONFLICT, "
                f"not auto-resolved"
            )

    # 11. duplicate approval records (same approver+date+evidence reused verbatim
    # across different decisions is a copy-paste smell, not a real independent approval)
    approval_fingerprints = {}
    for r in records:
        if r.current_status == "APPROVED" and r.approved_by and r.approval_date and r.evidence_reference:
            fp = (r.approved_by.strip().lower(), r.approval_date, r.evidence_reference.strip().lower())
            approval_fingerprints.setdefault(fp, []).append(r.decision_id)
    for fp, ids in approval_fingerprints.items():
        if len(ids) > 1:
            problems.append(
                f"duplicate approval record: decisions {ids} share identical "
                f"approver/date/evidence_reference {fp} -- verify each was independently approved"
            )

    if problems:
        # Classify the overall status from the most specific problem found,
        # so the exit code/print is actionable, not just "something's wrong".
        if any("D1A/D1B conflict" in p for p in problems):
            status = "BLOCKED_BASIS_CONFLICT"
        elif any("duplicate Decision_ID" in p or "unsupported Decision_ID" in p or "invalid current_status" in p
                  or "malformed" in p or "blank" in p or "not in allowed_responses" in p for p in problems):
            status = "FAIL_VALIDATION"
        else:
            status = "FAIL_VALIDATION"
    else:
        status = "PASS"

    return ValidationReport(status=status, problems=problems)
