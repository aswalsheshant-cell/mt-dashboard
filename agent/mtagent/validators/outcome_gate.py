"""Pre-execution outcome gate (AI_LEVERAGE_AND_JUDGMENT.md, enforcement §A).

A plan may not execute unless it names a business outcome, a concrete
deliverable, success criteria, its source data, and an approval boundary
(which may legitimately be an empty list -- "no approval needed" -- but
must have been set deliberately, not left undefined). Missing any of these
means the request was materially unclear and must come back as
`CLARIFICATION_REQUIRED`, never a silent best-effort execution.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# Fields that must be non-empty (business_outcome, deliverable are strings;
# success_criteria, source_data are lists).
_REQUIRED_NONEMPTY = ("business_outcome", "deliverable", "success_criteria", "source_data")
# approval_boundary must be *set* (a list, possibly empty) -- "not None",
# not "non-empty" -- an empty approval boundary is a valid, deliberate
# statement that no approval is required.
_REQUIRED_NOT_NONE = ("approval_boundary",)

ALL_REQUIRED_FIELDS = _REQUIRED_NONEMPTY + _REQUIRED_NOT_NONE


@dataclass
class GateResult:
    ok: bool
    missing: list = field(default_factory=list)


def check_plan_fields(plan_dict: dict) -> GateResult:
    """Check a raw dict shaped like the outcome-gate object from the spec:
    {business_outcome, deliverable, success_criteria, source_data,
    approval_boundary, ...}. Extra keys are ignored.
    """
    missing = []
    for key in _REQUIRED_NONEMPTY:
        if not plan_dict.get(key):
            missing.append(key)
    for key in _REQUIRED_NOT_NONE:
        if plan_dict.get(key) is None:
            missing.append(key)
    return GateResult(ok=not missing, missing=missing)


def check_plan(plan) -> GateResult:
    """Same check against a `controller.Plan` object."""
    return check_plan_fields({
        "business_outcome": getattr(plan, "business_outcome", ""),
        "deliverable": getattr(plan, "deliverable", ""),
        "success_criteria": getattr(plan, "success_criteria", []),
        "source_data": getattr(plan, "source_data", []),
        "approval_boundary": getattr(plan, "approval_boundary", None),
    })
