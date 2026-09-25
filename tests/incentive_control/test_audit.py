"""Phase 3A, STEP 7 -- audit event schema tests."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts"))

from incentive_control.audit import AuditEvent, AuditPayloadError, emit  # noqa: E402


def test_valid_event_round_trips_through_log(tmp_path):
    log_path = tmp_path / "audit.jsonl"
    event = AuditEvent(event_type="DECISION_BLOCKED", decision_id="NC-01",
                        status="BLOCKED_LEADERSHIP_DECISION",
                        source_reference="email-thread-2026-09-30")
    emit(event, log_path=log_path)
    lines = log_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["decision_id"] == "NC-01"
    assert row["status"] == "BLOCKED_LEADERSHIP_DECISION"
    assert set(row.keys()) == {
        "event_type", "decision_id", "status", "source_reference",
        "rule_version", "code_version", "event_timestamp",
    }


def test_unknown_event_type_rejected():
    with pytest.raises(ValueError):
        AuditEvent(event_type="NOT_A_REAL_EVENT", decision_id="NC-01", status="PASS")


def test_source_reference_that_looks_like_restricted_data_is_rejected():
    with pytest.raises(AuditPayloadError):
        AuditEvent(event_type="DECISION_APPROVED", decision_id="DM-01", status="APPROVED",
                    source_reference="employee_name=Jane Doe, salary=...")


def test_multiple_events_append_not_overwrite(tmp_path):
    log_path = tmp_path / "audit.jsonl"
    emit(AuditEvent(event_type="DECISION_LOADED", decision_id=None, status=None), log_path=log_path)
    emit(AuditEvent(event_type="DECISION_VALIDATED", decision_id=None, status="PASS"), log_path=log_path)
    lines = log_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
