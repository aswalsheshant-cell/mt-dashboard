"""Business-rule interface (Phase 3A, STEP 6).

The bridge between an APPROVED decision register and a future incentive
calculation engine. This module extracts approved rules; it does NOT
calculate anything. The calculation layer (not built in this phase) is
expected to consume DecisionResult objects from here -- never raw email
text, a free-text response, a historical guess, or a hardcoded default.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from .gate import assert_ready_for_shadow_calculation
from .models import DecisionRecord


@dataclass(frozen=True)
class DecisionResult:
    decision_id: str
    approved_response: str
    effective_period: str
    evidence_reference: str
    approval_date: str


def extract_approved_rules(records: List[DecisionRecord]) -> List[DecisionResult]:
    """Return every fully-approved decision as a DecisionResult.

    Raises the same DecisionGateBlocked subclass as
    gate.assert_ready_for_shadow_calculation() if any required decision is
    not yet fully approved -- this function deliberately does NOT return a
    partial list silently. A calculation layer that only needs a subset of
    decisions still calls this after the gate is fully READY, not before;
    building a partial-consumption path is exactly the kind of embedded
    assumption this phase is not allowed to make.
    """
    assert_ready_for_shadow_calculation(records)  # raises if not fully ready

    results = []
    for r in records:
        if r.is_fully_approved():
            results.append(DecisionResult(
                decision_id=r.decision_id,
                approved_response=r.selected_response,
                effective_period=r.affected_period,
                evidence_reference=r.evidence_reference,
                approval_date=r.approval_date,
            ))
    return results


def canonical_measurement_basis(records: List[DecisionRecord]) -> str:
    """The single governed accessor for 'Primary or Offtake' -- reads D1A
    (and implicitly confirms D1B agrees, via the gate check already run
    inside extract_approved_rules). Any future code that needs the
    measurement basis calls this, rather than re-reading D1A/D1B fields
    directly and risking a divergent, ungoverned check of its own."""
    rules = extract_approved_rules(records)
    d1a = next((r for r in rules if r.decision_id == "D1A"), None)
    if d1a is None:
        # extract_approved_rules() would already have raised if D1A were
        # not fully approved -- reaching here with d1a is None means the
        # gate considered D1A not required, which should never happen
        # given REQUIRED_DECISIONS. Fail loudly rather than guess.
        raise RuntimeError("D1A missing from approved rules despite a READY gate -- investigate REQUIRED_DECISIONS config")
    return d1a.approved_response
