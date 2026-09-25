"""Synthetic decision-register builders for Phase 3A tests. No real
Leadership/Finance responses, no employee data -- every approver name,
evidence reference, and period string here is an obvious placeholder.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts"))

from incentive_control.models import REQUIRED_DECISIONS  # noqa: E402

SYNTHETIC_APPROVER = "SYNTHETIC_FIXTURE_APPROVER"
SYNTHETIC_EVIDENCE = "synthetic-test-fixture-evidence-001"
SYNTHETIC_DATE = "2099-01-01"
SYNTHETIC_PERIOD = "SYNTHETIC_TEST_PERIOD"


def pending_decision(decision_id: str) -> dict:
    cfg = REQUIRED_DECISIONS[decision_id]
    status = "PENDING_LEADERSHIP" if cfg["owner"] == "MT Leadership" else "PENDING_FINANCE"
    return {
        "decision_id": decision_id,
        "decision_owner": cfg["owner"],
        "consulted_owner": None,
        "affected_period": SYNTHETIC_PERIOD,
        "affected_entity": None,
        "affected_value_l": None,
        "affected_store_count": None,
        "allowed_responses": list(cfg["allowed_responses"]),
        "current_status": status,
        "selected_response": None,
        "approved_by": None,
        "approval_date": None,
        "evidence_reference": None,
        "business_rule_result": None,
        "implementation_status": "NOT_STARTED",
        "notes": "synthetic test fixture -- not a real decision",
    }


def approved_decision(decision_id: str, response: str, **overrides) -> dict:
    d = pending_decision(decision_id)
    assert response in d["allowed_responses"], f"{response} not allowed for {decision_id}"
    d.update({
        "current_status": "APPROVED",
        "selected_response": response,
        "approved_by": SYNTHETIC_APPROVER,
        "approval_date": SYNTHETIC_DATE,
        # unique per decision by default -- a real register never reuses one
        # evidence reference across unrelated decisions; tests that want to
        # exercise the duplicate-approval-record check pass evidence_reference
        # explicitly via overrides instead.
        "evidence_reference": f"{SYNTHETIC_EVIDENCE}-{decision_id.lower()}",
        "business_rule_result": f"synthetic rule result for {response}",
    })
    d.update(overrides)
    return d


def all_pending_register() -> dict:
    return {"schema_version": "1.0", "decisions": [pending_decision(d) for d in REQUIRED_DECISIONS]}


def fully_approved_register(basis: str = "OFFTAKE") -> dict:
    """Every decision APPROVED, D1A == D1B == basis. This is a synthetic
    fixture ONLY -- it must never be mistaken for a real approval state."""
    decisions = []
    for decision_id, cfg in REQUIRED_DECISIONS.items():
        response = cfg["allowed_responses"][0]
        if decision_id in ("D1A", "D1B"):
            response = basis
        decisions.append(approved_decision(decision_id, response))
    return {"schema_version": "1.0", "decisions": decisions}
