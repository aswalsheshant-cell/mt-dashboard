"""Phase 3B, STEPS 6-8 -- end-to-end response-ingestion + closure tests.

Drives scripts/record_incentive_decision.py exactly as a real operator
would (subprocess, real CLI flags) against a throwaway copy of the
synthetic all-pending fixture. No real decisions, no employee data.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "record_incentive_decision.py"
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "incentive_decisions" / "synthetic_all_pending.json"

sys.path.insert(0, str(REPO_ROOT / "scripts"))
from incentive_control.business_rules import extract_approved_rules  # noqa: E402
from incentive_control.gate import assert_ready_for_shadow_calculation, evaluate_gate  # noqa: E402
from incentive_control.models import DecisionGateBlocked  # noqa: E402
from incentive_control.register_io import load_register  # noqa: E402


def _fresh_register(tmp_path) -> Path:
    dest = tmp_path / "register.json"
    dest.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
    return dest


def _record(register_path, decision_id, **kwargs):
    args = [sys.executable, str(SCRIPT), "--register", str(register_path), "--decision-id", decision_id]
    for flag, value in kwargs.items():
        if value is not None:
            args += [f"--{flag.replace('_', '-')}", str(value)]
    result = subprocess.run(args, capture_output=True, text=True, cwd=REPO_ROOT)
    return result.returncode, result.stdout + result.stderr


def _approve(register_path, decision_id, response, evidence, approver="Synthetic Approver", approval_date="2026-10-01", **extra):
    return _record(
        register_path, decision_id, status="APPROVED", selected_response=response,
        approved_by=approver, approval_date=approval_date, evidence_reference=evidence, **extra,
    )


ALL_LEADERSHIP_RESPONSES = {
    "NC-01": "H1_ONLY", "TG-01": "TARGET_REQUIRED", "TG-02": "TARGET_REQUIRED",
    "TG-03": "TARGET_REQUIRED", "TG-04": "TARGET_REQUIRED", "TG-05": "TARGET_REQUIRED",
    "GRAIN-01": "STATE_BRAND_MEASUREMENT_APPROVED",
    "DM-01": "IN_SCOPE_EMPLOYEE_ATTRIBUTION",
    "BASUP-01": "INCENTIVE_ELIGIBLE",
    "D1A": "OFFTAKE",
}
ALL_FINANCE_RESPONSES = {"D1B": "OFFTAKE", "RES-01": "OTHER_EXPLAINED"}


def _approve_all(register_path, skip=()):
    for decision_id, response in {**ALL_LEADERSHIP_RESPONSES, **ALL_FINANCE_RESPONSES}.items():
        if decision_id in skip:
            continue
        code, out = _approve(register_path, decision_id, response, f"synthetic-e2e-{decision_id.lower()}")
        assert code == 0, f"expected {decision_id} approval to succeed, got {code}: {out}"


# ---------------------------------------------------------------------------
# STEP 6 -- full synthetic closure
# ---------------------------------------------------------------------------

def test_step6_full_synthetic_closure_reaches_ready(tmp_path):
    reg = _fresh_register(tmp_path)
    _approve_all(reg)

    records = load_register(reg)
    result = evaluate_gate(records)
    assert result.state == "READY_FOR_SHADOW_CALCULATION"
    assert_ready_for_shadow_calculation(records)  # must not raise

    rules = extract_approved_rules(records)
    assert {r.decision_id for r in rules} == set(ALL_LEADERSHIP_RESPONSES) | set(ALL_FINANCE_RESPONSES)
    d1a = next(r for r in rules if r.decision_id == "D1A")
    assert d1a.approved_response == "OFFTAKE"


# ---------------------------------------------------------------------------
# STEP 7 -- blocked scenarios A-J
# ---------------------------------------------------------------------------

def test_step7a_one_leadership_response_missing(tmp_path):
    reg = _fresh_register(tmp_path)
    _approve_all(reg, skip={"TG-05"})
    result = evaluate_gate(load_register(reg))
    assert result.state == "BLOCKED_LEADERSHIP_DECISION"
    assert any(b["decision_id"] == "TG-05" for b in result.blocking)


def test_step7b_d1b_missing(tmp_path):
    reg = _fresh_register(tmp_path)
    _approve_all(reg, skip={"D1B"})
    result = evaluate_gate(load_register(reg))
    assert result.state == "BLOCKED_FINANCE_INPUT"


def test_step7c_d1_basis_conflict(tmp_path):
    reg = _fresh_register(tmp_path)
    _approve_all(reg, skip={"D1B"})
    code, out = _approve(reg, "D1B", "PRIMARY", "synthetic-e2e-d1b-conflict")
    assert code == 0, out
    result = evaluate_gate(load_register(reg))
    assert result.state == "BLOCKED_BASIS_CONFLICT"


def test_step7d_res01_unresolved(tmp_path):
    reg = _fresh_register(tmp_path)
    _approve_all(reg, skip={"RES-01"})
    result = evaluate_gate(load_register(reg))
    assert result.state == "BLOCKED_FINANCE_INPUT"
    assert any(b["decision_id"] == "RES-01" for b in result.blocking)


def test_step7e_approved_without_evidence_fails(tmp_path):
    reg = _fresh_register(tmp_path)
    code, out = _record(
        reg, "NC-01", status="APPROVED", selected_response="H1_ONLY",
        approved_by="X", approval_date="2026-10-01",  # evidence-reference omitted
    )
    assert code == 4
    assert "requires all of" in out


def test_step7f_invalid_enum_fails(tmp_path):
    reg = _fresh_register(tmp_path)
    code, out = _approve(reg, "TG-01", "NOT_A_REAL_TOKEN", "e1")
    assert code == 4
    assert "not in" in out


def test_step7g_duplicate_evidence_across_decisions_blocked(tmp_path):
    reg = _fresh_register(tmp_path)
    code1, _ = _approve(reg, "NC-01", "H1_ONLY", "shared-evidence-smell")
    assert code1 == 0
    code2, out2 = _approve(reg, "TG-01", "TARGET_REQUIRED", "shared-evidence-smell")
    assert code2 == 1
    assert "duplicate approval record" in out2
    # the second (invalid) write must NOT have been persisted
    data = json.loads(reg.read_text())
    tg01 = next(d for d in data["decisions"] if d["decision_id"] == "TG-01")
    assert tg01["current_status"] == "PENDING_LEADERSHIP"


def test_step7h_approved_decision_modified_without_amendment_fails(tmp_path):
    reg = _fresh_register(tmp_path)
    _approve(reg, "NC-01", "H1_ONLY", "v1-evidence")
    code, out = _approve(reg, "NC-01", "H2_PENDING", "v2-evidence")  # no --reason
    assert code == 3
    assert "AMENDMENT_REQUIRED" in out
    data = json.loads(reg.read_text())
    nc01 = next(d for d in data["decisions"] if d["decision_id"] == "NC-01")
    assert nc01["selected_response"] == "H1_ONLY"  # unchanged -- not silently overwritten


def test_step7h2_approved_decision_amended_with_reason_succeeds_and_preserves_history(tmp_path):
    reg = _fresh_register(tmp_path)
    _approve(reg, "NC-01", "H1_ONLY", "v1-evidence")
    code, out = _approve(reg, "NC-01", "H2_PENDING", "v2-evidence", reason="corrected after follow-up")
    assert code == 0, out
    data = json.loads(reg.read_text())
    nc01 = next(d for d in data["decisions"] if d["decision_id"] == "NC-01")
    assert nc01["selected_response"] == "H2_PENDING"
    assert len(nc01["revision_history"]) == 1
    assert nc01["revision_history"][0]["previous_response"] == "H1_ONLY"
    assert nc01["revision_history"][0]["new_response"] == "H2_PENDING"


def test_step7i_malformed_approval_date_fails(tmp_path):
    reg = _fresh_register(tmp_path)
    code, out = _approve(reg, "NC-01", "H1_ONLY", "e1", approval_date="not-a-date")
    assert code == 4
    assert "not a valid ISO date" in out


def test_step7j_ambiguous_response_recorded_as_clarification_required(tmp_path):
    reg = _fresh_register(tmp_path)
    code, out = _record(reg, "TG-03", status="CLARIFICATION_REQUIRED",
                          notes="reply did not map to an allowed token")
    assert code == 0, out
    data = json.loads(reg.read_text())
    tg03 = next(d for d in data["decisions"] if d["decision_id"] == "TG-03")
    assert tg03["current_status"] == "CLARIFICATION_REQUIRED"
    assert tg03["selected_response"] is None
    result = evaluate_gate(load_register(reg))
    assert any(b["decision_id"] == "TG-03" for b in result.blocking)


# ---------------------------------------------------------------------------
# STEP 8 -- partial approvals stay governed, never a partial payout
# ---------------------------------------------------------------------------

def test_step8_partial_approvals_remain_visible_but_gate_stays_blocked(tmp_path):
    reg = _fresh_register(tmp_path)
    _approve_all(reg, skip={"TG-04", "BASUP-01"})  # 10 approved, 2 pending

    records = load_register(reg)
    approved_ids = {r.decision_id for r in records if r.is_fully_approved()}
    assert len(approved_ids) == 10
    assert "TG-04" not in approved_ids and "BASUP-01" not in approved_ids

    result = evaluate_gate(records)
    assert not result.ready
    assert result.state in ("BLOCKED_LEADERSHIP_DECISION", "BLOCKED_BUSINESS_DEFINITION")

    with pytest.raises(DecisionGateBlocked):
        extract_approved_rules(records)  # no partial rule set is ever handed to a calculation layer
