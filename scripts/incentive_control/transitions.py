"""Decision state-transition control (Phase 3B, STEP 4/5).

Governs which `current_status` moves are allowed at all, and separately,
which moves require an amendment record (a new evidence reference, a
reason, and a preserved `revision_history` entry) rather than a silent
in-place overwrite.

These are two different questions on purpose:
    is_allowed_transition() -- is this move structurally permitted?
    requires_amendment()    -- if permitted, must it be recorded as a
                                revision rather than a plain field update?
"""
from __future__ import annotations

from typing import Optional

# Every status a decision can be in, and every status it may move to next.
# REJECTED and NOT_APPLICABLE are terminal -- reopening one is a new
# governance exception, not a plain transition, and is out of scope for
# this framework (it would need its own explicit process, not a silent
# status flip).
ALLOWED_TRANSITIONS = {
    "PENDING_LEADERSHIP": {
        "PENDING_LEADERSHIP", "APPROVED", "REJECTED", "NOT_APPLICABLE", "CLARIFICATION_REQUIRED",
    },
    "PENDING_FINANCE": {
        "PENDING_FINANCE", "APPROVED", "REJECTED", "NOT_APPLICABLE", "CLARIFICATION_REQUIRED",
    },
    "CLARIFICATION_REQUIRED": {
        "CLARIFICATION_REQUIRED", "APPROVED", "REJECTED", "NOT_APPLICABLE",
        "PENDING_LEADERSHIP", "PENDING_FINANCE",
    },
    "BLOCKED_CONFLICT": {
        "BLOCKED_CONFLICT", "APPROVED", "REJECTED", "PENDING_LEADERSHIP", "PENDING_FINANCE",
    },
    # From APPROVED, every move below is PERMITTED but -- per requires_amendment()
    # -- none of them may happen as a silent field overwrite. The ingestion
    # helper (record_incentive_decision.py) enforces that split.
    "APPROVED": {
        "APPROVED", "REJECTED", "NOT_APPLICABLE", "PENDING_LEADERSHIP", "PENDING_FINANCE",
    },
    "REJECTED": {"REJECTED"},
    "NOT_APPLICABLE": {"NOT_APPLICABLE"},
}


class TransitionError(Exception):
    """Raised for a structurally disallowed state move (e.g. REJECTED ->
    APPROVED with no amendment process) -- distinct from AmendmentRequiredError,
    which is for a move that IS allowed but was attempted without the
    required amendment fields."""


class AmendmentRequiredError(Exception):
    """Raised when a caller tries to change an already-APPROVED decision's
    response (or move it off APPROVED) without supplying a new evidence
    reference and a reason -- i.e. without going through the amendment path."""


def is_allowed_transition(current_status: str, new_status: str) -> bool:
    if current_status not in ALLOWED_TRANSITIONS:
        return False
    return new_status in ALLOWED_TRANSITIONS[current_status]


def requires_amendment(
    current_status: str,
    current_response: Optional[str],
    new_status: str,
    new_response: Optional[str],
) -> bool:
    """True iff the decision is currently APPROVED and this update would
    either move it off APPROVED or change its recorded response -- i.e.
    it would alter history, not just fill in a still-open decision."""
    if current_status != "APPROVED":
        return False
    if new_status != "APPROVED":
        return True
    return new_response != current_response


def validate_transition(
    current_status: str,
    new_status: str,
    *,
    has_amendment_fields: bool,
    current_response: Optional[str] = None,
    new_response: Optional[str] = None,
) -> None:
    """Raises TransitionError or AmendmentRequiredError; returns None (no
    exception) if the move is fully valid to apply as given."""
    if not is_allowed_transition(current_status, new_status):
        raise TransitionError(
            f"{current_status} -> {new_status} is not an allowed transition"
        )
    if requires_amendment(current_status, current_response, new_status, new_response):
        if not has_amendment_fields:
            raise AmendmentRequiredError(
                f"changing an APPROVED decision (response {current_response!r} -> "
                f"{new_response!r}, status {current_status!r} -> {new_status!r}) "
                f"requires a new evidence reference and a reason -- the prior "
                f"approval must be preserved in revision_history, not overwritten"
            )
