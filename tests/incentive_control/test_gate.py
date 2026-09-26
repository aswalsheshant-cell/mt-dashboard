"""Phase 3A, STEP 5/6 -- D1 conflict control, fail-closed raise behaviour,
and the business-rule interface. Synthetic data only."""
import json
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts"))

from incentive_control.business_rules import (  # noqa: E402
    canonical_measurement_basis,
    extract_approved_rules,
)
from incentive_control.gate import assert_ready_for_shadow_calculation, evaluate_gate  # noqa: E402
from incentive_control.models import (  # noqa: E402
    BlockedBasisConflict,
    BlockedLeadershipDecision,
    DecisionGateBlocked,
)
from incentive_control.register_io import load_register  # noqa: E402

from .fixtures import all_pending_register, approved_decision, fully_approved_register  # noqa: E402


def _records_from_dict(data: dict):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        path = Path(f.name)
    try:
        return load_register(path)
    finally:
        path.unlink()


def test_assert_raises_blocked_leadership_when_nothing_approved():
    records = _records_from_dict(all_pending_register())
    with pytest.raises(BlockedLeadershipDecision) as exc_info:
        assert_ready_for_shadow_calculation(records)
    assert exc_info.value.gate_state == "BLOCKED_LEADERSHIP_DECISION"


def test_assert_raises_basis_conflict_not_a_silent_default():
    data = fully_approved_register("OFFTAKE")
    for i, d in enumerate(data["decisions"]):
        if d["decision_id"] == "D1B":
            data["decisions"][i] = approved_decision("D1B", "PRIMARY")
    records = _records_from_dict(data)
    with pytest.raises(BlockedBasisConflict):
        assert_ready_for_shadow_calculation(records)


def test_assert_returns_normally_when_fully_ready():
    records = _records_from_dict(fully_approved_register("OFFTAKE"))
    assert_ready_for_shadow_calculation(records)  # must not raise


def test_never_silently_defaults_to_offtake_or_zero():
    """The literal control this phase exists to prove: no code path here
    ever substitutes a default basis or a zero target when a decision is
    missing -- it raises instead. This test would fail if some future
    edit reintroduced `if decision_missing: use_offtake()`."""
    records = _records_from_dict(all_pending_register())
    try:
        basis = canonical_measurement_basis(records)
    except DecisionGateBlocked:
        pass  # correct: raised, not a returned default value
    else:
        pytest.fail(f"canonical_measurement_basis() returned {basis!r} instead of raising")


def test_extract_approved_rules_raises_on_partial_approval():
    data = fully_approved_register("OFFTAKE")
    for i, d in enumerate(data["decisions"]):
        if d["decision_id"] == "RES-01":
            data["decisions"][i]["current_status"] = "PENDING_FINANCE"
            data["decisions"][i]["selected_response"] = None
            data["decisions"][i]["approved_by"] = None
            data["decisions"][i]["approval_date"] = None
            data["decisions"][i]["evidence_reference"] = None
    records = _records_from_dict(data)
    with pytest.raises(DecisionGateBlocked):
        extract_approved_rules(records)


def test_extract_approved_rules_returns_decision_results_when_ready():
    records = _records_from_dict(fully_approved_register("PRIMARY"))
    rules = extract_approved_rules(records)
    ids = {r.decision_id for r in rules}
    assert ids == {"NC-01", "TG-01", "TG-02", "TG-03", "TG-04", "TG-05",
                    "GRAIN-01", "DM-01", "BASUP-01", "D1A", "D1B", "RES-01"}
    d1a_result = next(r for r in rules if r.decision_id == "D1A")
    assert d1a_result.approved_response == "PRIMARY"
    assert canonical_measurement_basis(records) == "PRIMARY"


def test_content_hash_mismatch_reblocks_an_approved_decision():
    """A hand-edit to a decision's CONTENT (affected_value_l/period/entity/
    store_count/allowed_responses) after it was APPROVED must re-block the
    gate, even though current_status still says APPROVED and every
    evidence field is still populated. record_incentive_decision.py has no
    flag to change these content fields at all, so a mismatch here means
    the register was edited outside the sanctioned CLI -- the whole point
    of stamping content_hash at resolution time."""
    data = fully_approved_register("OFFTAKE")
    for i, d in enumerate(data["decisions"]):
        if d["decision_id"] == "NC-01":
            data["decisions"][i]["affected_value_l"] = 999999.99  # tampered post-approval
    records = _records_from_dict(data)
    result = evaluate_gate(records)
    assert result.state != "READY_FOR_SHADOW_CALCULATION"
    assert any(b["decision_id"] == "NC-01" for b in result.blocking)


def test_missing_content_hash_on_approved_decision_blocks_the_gate():
    """A decision resolved before this control existed (no content_hash at
    all) must not be trusted by default -- fail closed, not open."""
    data = fully_approved_register("OFFTAKE")
    for i, d in enumerate(data["decisions"]):
        if d["decision_id"] == "NC-01":
            data["decisions"][i]["content_hash"] = None
    records = _records_from_dict(data)
    result = evaluate_gate(records)
    assert result.state != "READY_FOR_SHADOW_CALCULATION"
    assert any(b["decision_id"] == "NC-01" for b in result.blocking)


def test_rejected_and_not_applicable_do_not_block_the_gate_when_evidenced():
    """A decision resolved as REJECTED or NOT_APPLICABLE closes it without
    authorizing a value -- confirm the gate treats an EVIDENCED one as
    resolved, not as still-pending, so a genuinely N/A account doesn't
    block everything forever. Evidence is still required, though -- see
    test_not_applicable_without_evidence_still_blocks_the_gate below."""
    data = fully_approved_register("OFFTAKE")
    for i, d in enumerate(data["decisions"]):
        if d["decision_id"] == "TG-05":
            data["decisions"][i]["current_status"] = "NOT_APPLICABLE"
            data["decisions"][i]["selected_response"] = None
            data["decisions"][i]["approved_by"] = "SYNTHETIC_FIXTURE_APPROVER"
            data["decisions"][i]["approval_date"] = "2099-01-01"
            data["decisions"][i]["evidence_reference"] = "synthetic-test-fixture-evidence-001-tg05-na"
            data["decisions"][i]["business_rule_result"] = None
    records = _records_from_dict(data)
    result = evaluate_gate(records)
    assert result.state == "READY_FOR_SHADOW_CALCULATION"


def test_not_applicable_without_evidence_still_blocks_the_gate():
    """Regression test for a confirmed critical defect: before this fix,
    REJECTED/NOT_APPLICABLE bypassed is_fully_approved() entirely, so all
    12 required decisions could be closed with zero evidence anywhere and
    the gate would still return READY_FOR_SHADOW_CALCULATION. Flipping a
    decision's status alone -- with no approver, date, or evidence -- must
    never resolve it."""
    data = fully_approved_register("OFFTAKE")
    for i, d in enumerate(data["decisions"]):
        if d["decision_id"] == "TG-05":
            data["decisions"][i]["current_status"] = "NOT_APPLICABLE"
            data["decisions"][i]["selected_response"] = None
            data["decisions"][i]["approved_by"] = None
            data["decisions"][i]["approval_date"] = None
            data["decisions"][i]["evidence_reference"] = None
            data["decisions"][i]["business_rule_result"] = None
    records = _records_from_dict(data)
    result = evaluate_gate(records)
    assert result.state != "READY_FOR_SHADOW_CALCULATION"
    assert any(b["decision_id"] == "TG-05" for b in result.blocking)
