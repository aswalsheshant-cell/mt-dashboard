"""Decision model, configuration, and the fail-closed exception hierarchy
for the FY27 incentive decision-closure gate (Phase 3A).

Design principle (per the phase's own governing instruction): the code
must never contain a line like `if decision_missing: use_offtake()` or
`if h2_target_missing: target = 0`. Every path where a required decision
is not APPROVED raises one of the exceptions below instead of choosing a
default. This mirrors scripts/canonical/policies.py's NotAvailable
sentinel (missing must never silently become a real value) and
scripts/canonical/governance.py's is_fully_approved() four-field guard
(an approval is only real when approver/reference/date are all present) --
both already-governed patterns in this repo, extended here rather than
reinvented.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


# ---------------------------------------------------------------------------
# Status / gate-state vocabularies (mirrors schemas/fy27_incentive_decision.schema.json)
# ---------------------------------------------------------------------------

VALID_STATUSES = {
    "PENDING_LEADERSHIP",
    "PENDING_FINANCE",
    "APPROVED",
    "REJECTED",
    "NOT_APPLICABLE",
    "BLOCKED_CONFLICT",
    "CLARIFICATION_REQUIRED",
}

# Statuses that resolve a decision (it no longer blocks the gate, even
# though REJECTED/NOT_APPLICABLE are not APPROVED in the payout sense).
RESOLVED_STATUSES = {"APPROVED", "REJECTED", "NOT_APPLICABLE"}

# Statuses that must never carry a business_rule_result (an unresolved
# decision has produced nothing for the calculation layer to consume yet).
UNRESOLVED_STATUSES = {
    "PENDING_LEADERSHIP",
    "PENDING_FINANCE",
    "BLOCKED_CONFLICT",
    "CLARIFICATION_REQUIRED",
}

GATE_STATES = {
    "READY_FOR_SHADOW_CALCULATION",
    "BLOCKED_LEADERSHIP_DECISION",
    "BLOCKED_FINANCE_INPUT",
    "BLOCKED_BASIS_CONFLICT",
    "BLOCKED_MAPPING",
    "BLOCKED_BUSINESS_DEFINITION",
}


# ---------------------------------------------------------------------------
# Decision-family configuration -- the single place required decisions and
# their allowed responses are declared, so validator/gate logic reads this
# table instead of re-hardcoding IDs and tokens per function.
# ---------------------------------------------------------------------------

_TG_RESPONSES = ("TARGET_REQUIRED", "NOT_APPLICABLE", "EXCLUDED_FROM_INCENTIVE",
                 "PENDING_TARGET", "MAPPING_ERROR")

REQUIRED_DECISIONS = {
    "NC-01": {
        "owner": "MT Leadership",
        "allowed_responses": ("H1_ONLY", "H2_PENDING", "FULL_YEAR_TARGET_REQUIRED",
                               "OTHER_REQUIRES_EXPLANATION"),
        "required_for_gate": True,
        "blocked_state": "BLOCKED_LEADERSHIP_DECISION",
    },
    "TG-01": {"owner": "MT Leadership", "allowed_responses": _TG_RESPONSES,
               "required_for_gate": True, "blocked_state": "BLOCKED_LEADERSHIP_DECISION"},
    "TG-02": {"owner": "MT Leadership", "allowed_responses": _TG_RESPONSES,
               "required_for_gate": True, "blocked_state": "BLOCKED_LEADERSHIP_DECISION"},
    "TG-03": {"owner": "MT Leadership", "allowed_responses": _TG_RESPONSES,
               "required_for_gate": True, "blocked_state": "BLOCKED_LEADERSHIP_DECISION"},
    "TG-04": {"owner": "MT Leadership", "allowed_responses": _TG_RESPONSES,
               "required_for_gate": True, "blocked_state": "BLOCKED_LEADERSHIP_DECISION"},
    "TG-05": {"owner": "MT Leadership", "allowed_responses": _TG_RESPONSES,
               "required_for_gate": True, "blocked_state": "BLOCKED_LEADERSHIP_DECISION"},
    "GRAIN-01": {
        "owner": "MT Leadership",
        "allowed_responses": ("STATE_BRAND_MEASUREMENT_APPROVED", "CHAIN_REPLAN_REQUIRED"),
        "required_for_gate": True,
        "blocked_state": "BLOCKED_BUSINESS_DEFINITION",
    },
    "DM-01": {
        "owner": "MT Leadership",
        "allowed_responses": ("IN_SCOPE_EMPLOYEE_ATTRIBUTION", "OUT_OF_SCOPE",
                               "MAPPING_CORRECTION_REQUIRED", "PENDING_BUSINESS_CONFIRMATION"),
        "required_for_gate": True,
        "blocked_state": "BLOCKED_LEADERSHIP_DECISION",
    },
    "BASUP-01": {
        "owner": "MT Leadership",
        "allowed_responses": ("INCENTIVE_ELIGIBLE", "NOT_INCENTIVE_ELIGIBLE",
                               "PENDING_MASTER_UPDATE"),
        "required_for_gate": True,
        "blocked_state": "BLOCKED_BUSINESS_DEFINITION",
    },
    "D1A": {
        "owner": "MT Leadership",
        "allowed_responses": ("PRIMARY", "OFFTAKE"),
        "required_for_gate": True,
        "blocked_state": "BLOCKED_LEADERSHIP_DECISION",
    },
    "D1B": {
        "owner": "Finance",
        "allowed_responses": ("PRIMARY", "OFFTAKE", "OTHER"),
        "required_for_gate": True,
        "blocked_state": "BLOCKED_FINANCE_INPUT",
    },
    "RES-01": {
        "owner": "Finance",
        "allowed_responses": ("SOURCE_BASIS_DIFFERENCE", "PERIOD_DIFFERENCE",
                               "ENTITY_SCOPE_DIFFERENCE", "GRAIN_DIFFERENCE",
                               "MISSING_TARGET", "MAPPING_DIFFERENCE", "ROUNDING",
                               "OTHER_EXPLAINED", "UNEXPLAINED"),
        # RES-01's materiality-based requirement is evaluated by the gate,
        # not hardcoded True/False here -- see gate.py's res01_is_material().
        "required_for_gate": "MATERIAL",
        "blocked_state": "BLOCKED_FINANCE_INPUT",
    },
}


# ---------------------------------------------------------------------------
# Decision record (the in-memory shape of one row from the register)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DecisionRecord:
    decision_id: str
    decision_owner: str
    affected_period: str
    allowed_responses: tuple
    current_status: str
    selected_response: Optional[str] = None
    approved_by: Optional[str] = None
    approval_date: Optional[str] = None
    evidence_reference: Optional[str] = None
    business_rule_result: Optional[str] = None
    implementation_status: str = "NOT_STARTED"
    consulted_owner: Optional[str] = None
    affected_entity: Optional[str] = None
    affected_value_l: Optional[float] = None
    affected_store_count: Optional[int] = None
    notes: Optional[str] = None

    def is_fully_approved(self) -> bool:
        """Mirrors scripts/canonical/governance.py's ApprovedException.is_fully_approved():
        APPROVED is only real when status/response/approver/date/evidence are
        ALL populated -- an APPROVED row missing any one of these is treated
        as if it were still pending, never as a partial approval."""
        return (
            self.current_status == "APPROVED"
            and bool(self.selected_response and self.selected_response.strip())
            and self.selected_response in self.allowed_responses
            and bool(self.approved_by and self.approved_by.strip())
            and bool(self.approval_date and self.approval_date.strip())
            and bool(self.evidence_reference and self.evidence_reference.strip())
        )

    def is_resolved(self) -> bool:
        """A decision that no longer blocks the gate -- APPROVED, REJECTED, or
        NOT_APPLICABLE. Resolved does not mean APPROVED: a REJECTED or
        NOT_APPLICABLE decision closes the item without authorizing a
        calculation basis."""
        return self.current_status in RESOLVED_STATUSES


# ---------------------------------------------------------------------------
# Fail-closed exception hierarchy -- `raise`d, never silently substituted
# ---------------------------------------------------------------------------

class DecisionGateBlocked(Exception):
    """Base class. Never caught and converted into a default value --
    callers catch it only to report the blocked state, not to proceed."""
    gate_state = None

    def __init__(self, decision_id: str, reason: str):
        self.decision_id = decision_id
        self.reason = reason
        super().__init__(f"{self.gate_state}: {decision_id} -- {reason}")


class BlockedLeadershipDecision(DecisionGateBlocked):
    gate_state = "BLOCKED_LEADERSHIP_DECISION"


class BlockedFinanceInput(DecisionGateBlocked):
    gate_state = "BLOCKED_FINANCE_INPUT"


class BlockedBasisConflict(DecisionGateBlocked):
    gate_state = "BLOCKED_BASIS_CONFLICT"


class BlockedMapping(DecisionGateBlocked):
    gate_state = "BLOCKED_MAPPING"


class BlockedBusinessDefinition(DecisionGateBlocked):
    gate_state = "BLOCKED_BUSINESS_DEFINITION"


_BLOCKED_STATE_TO_EXCEPTION = {
    "BLOCKED_LEADERSHIP_DECISION": BlockedLeadershipDecision,
    "BLOCKED_FINANCE_INPUT": BlockedFinanceInput,
    "BLOCKED_BASIS_CONFLICT": BlockedBasisConflict,
    "BLOCKED_MAPPING": BlockedMapping,
    "BLOCKED_BUSINESS_DEFINITION": BlockedBusinessDefinition,
}


def exception_for_state(gate_state: str):
    """Look up the exception class for a blocked-state string -- so gate.py
    raises the same vocabulary the schema and register use, not a parallel
    set of ad hoc error types."""
    return _BLOCKED_STATE_TO_EXCEPTION[gate_state]
