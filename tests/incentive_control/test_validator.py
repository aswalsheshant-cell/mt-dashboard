"""Phase 3A, STEP 8 -- decision-register validator tests. Synthetic data
only; no real Leadership/Finance responses, no employee data."""
import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts"))

from incentive_control.gate import evaluate_gate  # noqa: E402
from incentive_control.register_io import load_register  # noqa: E402
from incentive_control.validator import validate_register  # noqa: E402

from .fixtures import (  # noqa: E402
    all_pending_register,
    approved_decision,
    fully_approved_register,
)

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "incentive_decisions"


def _records_from_dict(data: dict):
    """Round-trip a register dict through a temp file so both schema
    validation (register_io) and semantic validation (validator) run,
    exactly as the CLI does."""
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        path = Path(f.name)
    try:
        return load_register(path)
    finally:
        path.unlink()


def test_case1_all_decisions_pending_blocked():
    records = _records_from_dict(all_pending_register())
    assert validate_register(records).status == "PASS"
    result = evaluate_gate(records)
    assert result.state == "BLOCKED_LEADERSHIP_DECISION"


def test_case2_leadership_complete_finance_missing():
    data = all_pending_register()
    for i, d in enumerate(data["decisions"]):
        if d["decision_owner"] == "MT Leadership":
            data["decisions"][i] = approved_decision(d["decision_id"], d["allowed_responses"][0])
    records = _records_from_dict(data)
    assert validate_register(records).status == "PASS"
    result = evaluate_gate(records)
    assert result.state == "BLOCKED_FINANCE_INPUT"
    assert not result.ready


def test_case3_finance_complete_leadership_missing():
    data = all_pending_register()
    for i, d in enumerate(data["decisions"]):
        if d["decision_owner"] == "Finance":
            data["decisions"][i] = approved_decision(d["decision_id"], d["allowed_responses"][0])
    records = _records_from_dict(data)
    assert validate_register(records).status == "PASS"
    result = evaluate_gate(records)
    assert result.state == "BLOCKED_LEADERSHIP_DECISION"


def test_case4_d1_basis_conflict():
    data = fully_approved_register("OFFTAKE")
    for i, d in enumerate(data["decisions"]):
        if d["decision_id"] == "D1B":
            data["decisions"][i] = approved_decision("D1B", "PRIMARY")
    records = _records_from_dict(data)
    result = evaluate_gate(records)
    assert result.state == "BLOCKED_BASIS_CONFLICT"
    assert not result.ready
    assert any(b["decision_id"] == "D1A/D1B" for b in result.blocking)


def test_case5_approved_without_evidence_fails():
    data = fully_approved_register("OFFTAKE")
    for i, d in enumerate(data["decisions"]):
        if d["decision_id"] == "NC-01":
            d["evidence_reference"] = None
    records = _records_from_dict(data)
    report = validate_register(records)
    assert report.status == "FAIL_VALIDATION"
    assert any("APPROVED without evidence_reference" in p for p in report.problems)


def test_case6_approved_without_approver_fails():
    data = fully_approved_register("OFFTAKE")
    for i, d in enumerate(data["decisions"]):
        if d["decision_id"] == "NC-01":
            d["approved_by"] = None
    records = _records_from_dict(data)
    report = validate_register(records)
    assert report.status == "FAIL_VALIDATION"
    assert any("APPROVED without approved_by" in p for p in report.problems)


def test_case7_response_outside_enum_fails_schema():
    # The schema itself only constrains decision_id/current_status enums;
    # selected_response is a free string at the JSON-Schema layer (allowed
    # tokens differ per decision), so an out-of-enum response is caught by
    # the semantic validator, not by schema validation.
    data = fully_approved_register("OFFTAKE")
    for i, d in enumerate(data["decisions"]):
        if d["decision_id"] == "TG-01":
            d["selected_response"] = "NOT_A_REAL_TOKEN"
    records = _records_from_dict(data)
    report = validate_register(records)
    assert report.status == "FAIL_VALIDATION"
    assert any("not in allowed_responses" in p for p in report.problems)


def test_case8_duplicate_decision_id_detected_by_validator():
    # The JSON Schema itself doesn't enforce decision_id uniqueness (JSON
    # Schema's uniqueItems would require whole-object equality, not a
    # single-key constraint) -- the register loads schema-clean, and the
    # semantic validator's own duplicate check is what catches this.
    data = fully_approved_register("OFFTAKE")
    data["decisions"].append(copy.deepcopy(data["decisions"][0]))
    records = _records_from_dict(data)
    report = validate_register(records)
    assert report.status == "FAIL_VALIDATION"
    assert any("duplicate Decision_ID" in p for p in report.problems)


def test_case8b_duplicate_decision_id_detected_by_validator_directly():
    # Bypass schema (which also has an implicit uniqueness expectation via
    # our validator) to prove the validator's own duplicate check fires
    # even if a caller constructs records directly rather than via JSON.
    from incentive_control.models import DecisionRecord
    r1 = DecisionRecord(decision_id="NC-01", decision_owner="MT Leadership",
                         affected_period="P", allowed_responses=("H1_ONLY",),
                         current_status="PENDING_LEADERSHIP")
    r2 = DecisionRecord(decision_id="NC-01", decision_owner="MT Leadership",
                         affected_period="P", allowed_responses=("H1_ONLY",),
                         current_status="PENDING_LEADERSHIP")
    report = validate_register([r1, r2])
    assert report.status == "FAIL_VALIDATION"
    assert any("duplicate Decision_ID" in p for p in report.problems)


def test_case9_ambiguous_free_text_stays_clarification_required():
    data = all_pending_register()
    for i, d in enumerate(data["decisions"]):
        if d["decision_id"] == "NC-01":
            data["decisions"][i]["current_status"] = "CLARIFICATION_REQUIRED"
            data["decisions"][i]["notes"] = "reply text did not map to an allowed token"
    records = _records_from_dict(data)
    report = validate_register(records)
    assert report.status == "PASS"  # a correctly-flagged ambiguity is valid, not an error
    result = evaluate_gate(records)
    assert result.state == "BLOCKED_LEADERSHIP_DECISION"
    assert any(b["decision_id"] == "NC-01" for b in result.blocking)


def test_case10_all_valid_ready_for_shadow_calculation():
    records = _records_from_dict(fully_approved_register("OFFTAKE"))
    report = validate_register(records)
    assert report.status == "PASS"
    result = evaluate_gate(records)
    assert result.state == "READY_FOR_SHADOW_CALCULATION"
    assert result.ready
    assert result.blocking == []


def test_missing_required_decision_detected():
    data = all_pending_register()
    data["decisions"] = [d for d in data["decisions"] if d["decision_id"] != "RES-01"]
    records = _records_from_dict(data)
    report = validate_register(records)
    assert report.status == "FAIL_VALIDATION"
    assert any("missing required decision: RES-01" in p for p in report.problems)


def test_duplicate_approval_record_detected():
    data = fully_approved_register("OFFTAKE")
    shared_evidence = "shared-evidence-smell"
    for d in data["decisions"][:2]:
        d["evidence_reference"] = shared_evidence
    records = _records_from_dict(data)
    report = validate_register(records)
    assert report.status == "FAIL_VALIDATION"
    assert any("duplicate approval record" in p for p in report.problems)


def test_static_fixtures_on_disk_are_valid_or_expected():
    all_pending = load_register(FIXTURES / "synthetic_all_pending.json")
    assert validate_register(all_pending).status == "PASS"
    assert evaluate_gate(all_pending).state == "BLOCKED_LEADERSHIP_DECISION"

    fully_approved = load_register(FIXTURES / "synthetic_fully_approved_offtake.json")
    assert validate_register(fully_approved).status == "PASS"
    assert evaluate_gate(fully_approved).state == "READY_FOR_SHADOW_CALCULATION"
