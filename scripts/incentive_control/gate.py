"""Decision closure gate (Phase 3A, STEP 4 + STEP 5).

Answers exactly one question: is it safe to start a SHADOW calculation
(never a real payout -- that is a later, separate gate) from the decisions
currently in the register? It never computes anything financial itself.

Two entry points:

  evaluate_gate(records) -> GateResult
      Non-raising. Returns the full picture (state + every blocking
      decision + why) -- what a report/CLI prints.

  assert_ready_for_shadow_calculation(records)
      Raises the first applicable DecisionGateBlocked subclass. This is
      the shape the phase's own governing instruction asked for literally:
      `if required_decision_missing: raise BLOCKED_LEADERSHIP_DECISION`
      instead of ever picking a default. Any future calculation-engine
      entrypoint calls this first and lets the exception propagate --
      it must not catch it and substitute a value.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .models import (
    REQUIRED_DECISIONS,
    DecisionRecord,
    exception_for_state,
)

# RES-01's requirement is materiality-based, not a flat True/False (see
# REQUIRED_DECISIONS["RES-01"]["required_for_gate"] == "MATERIAL"). No
# Finance-approved materiality threshold exists yet -- until one does,
# this stays None, which res01_is_material() below treats as "always
# material" (fail-closed: RES-01 blocks the gate like every other
# required decision, never silently waived because no one set a number).
RES01_MATERIALITY_THRESHOLD_L: Optional[float] = None


def res01_is_material(records: List[DecisionRecord]) -> bool:
    res01 = next((r for r in records if r.decision_id == "RES-01"), None)
    if res01 is None or res01.affected_value_l is None:
        return True  # fail closed: unknown exposure is treated as material
    if RES01_MATERIALITY_THRESHOLD_L is None:
        return True  # fail closed: no approved threshold yet
    return abs(res01.affected_value_l) >= RES01_MATERIALITY_THRESHOLD_L


@dataclass
class GateResult:
    state: str
    blocking: List[Dict[str, str]] = field(default_factory=list)  # [{decision_id, blocked_state, reason}]

    @property
    def ready(self) -> bool:
        return self.state == "READY_FOR_SHADOW_CALCULATION"

    def print_report(self) -> None:
        print(f"Decision closure gate: {self.state}")
        for b in self.blocking:
            print(f"  - {b['decision_id']}: {b['blocked_state']} -- {b['reason']}")


def _decision_by_id(records: List[DecisionRecord], decision_id: str) -> Optional[DecisionRecord]:
    return next((r for r in records if r.decision_id == decision_id), None)


def _is_required_now(decision_id: str, records: List[DecisionRecord]) -> bool:
    cfg = REQUIRED_DECISIONS[decision_id]
    req = cfg["required_for_gate"]
    if req == "MATERIAL":
        return res01_is_material(records)
    return bool(req)


def evaluate_gate(records: List[DecisionRecord]) -> GateResult:
    blocking: List[Dict[str, str]] = []

    # D1 conflict is checked first and independently -- a conflict is a
    # distinct state from either side being merely unanswered.
    d1a = _decision_by_id(records, "D1A")
    d1b = _decision_by_id(records, "D1B")
    d1_conflict = False
    if d1a and d1b and d1a.is_fully_approved() and d1b.is_fully_approved():
        if d1a.selected_response != d1b.selected_response:
            d1_conflict = True
            blocking.append({
                "decision_id": "D1A/D1B",
                "blocked_state": "BLOCKED_BASIS_CONFLICT",
                "reason": (
                    f"Leadership selected {d1a.selected_response!r}, Finance selected "
                    f"{d1b.selected_response!r} -- no basis is selected automatically"
                ),
            })

    for decision_id, cfg in REQUIRED_DECISIONS.items():
        if decision_id in ("D1A", "D1B") and d1_conflict:
            continue  # already reported as the conflict above, not a second generic block

        if not _is_required_now(decision_id, records):
            continue

        record = _decision_by_id(records, decision_id)
        if record is None:
            blocking.append({
                "decision_id": decision_id,
                "blocked_state": cfg["blocked_state"],
                "reason": "decision absent from register entirely",
            })
            continue

        if record.current_status in ("REJECTED", "NOT_APPLICABLE"):
            continue  # resolved, even though not APPROVED -- does not block

        if not record.is_fully_approved():
            blocking.append({
                "decision_id": decision_id,
                "blocked_state": cfg["blocked_state"],
                "reason": f"current_status={record.current_status}, not a fully-approved record",
            })

    if not blocking:
        return GateResult(state="READY_FOR_SHADOW_CALCULATION", blocking=[])

    # Overall state: BLOCKED_BASIS_CONFLICT takes precedence (it is the
    # sharpest signal -- both sides answered, and disagree), then whichever
    # blocked_state appears most among remaining items, in a fixed priority
    # order so the same input always yields the same overall state.
    if d1_conflict:
        overall = "BLOCKED_BASIS_CONFLICT"
    else:
        priority = [
            "BLOCKED_LEADERSHIP_DECISION",
            "BLOCKED_FINANCE_INPUT",
            "BLOCKED_BUSINESS_DEFINITION",
            "BLOCKED_MAPPING",
        ]
        present_states = {b["blocked_state"] for b in blocking}
        overall = next((s for s in priority if s in present_states), blocking[0]["blocked_state"])

    return GateResult(state=overall, blocking=blocking)


def assert_ready_for_shadow_calculation(records: List[DecisionRecord]) -> None:
    """Raise the first blocking DecisionGateBlocked subclass found, in a
    fixed, deterministic order. Returns normally (no return value) only
    when every required decision is fully approved and D1A == D1B.

    This is the function a future calculation entrypoint calls FIRST. It
    must never be wrapped in a try/except that substitutes a default on
    failure -- the whole point of raising here is that the caller cannot
    quietly proceed.
    """
    result = evaluate_gate(records)
    if result.ready:
        return
    first = result.blocking[0]
    exc_cls = exception_for_state(first["blocked_state"])
    raise exc_cls(first["decision_id"], first["reason"])
