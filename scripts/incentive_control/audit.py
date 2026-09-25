"""Audit event schema (Phase 3A, STEP 7).

Deliberately non-sensitive: every field here is safe to appear in a CI log
or an issue tracker. NEVER log employee names, HCPL IDs, salary, incentive
amounts, or any restricted compensation data through this module -- those
never enter this framework's audit trail at all; they stay in
incentive_working/ and its own access controls.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

EVENT_TYPES = {
    "DECISION_LOADED",
    "DECISION_VALIDATED",
    "DECISION_BLOCKED",
    "DECISION_APPROVED",
    "CONFLICT_DETECTED",
    "CALCULATION_BLOCKED",
    "SHADOW_CALCULATION_ALLOWED",
}

CODE_VERSION = "phase-3a-1.0"
RULE_VERSION = "fy27-incentive-decision-schema-1.0"

_DISALLOWED_FIELD_NAME_FRAGMENTS = (
    "employee", "name", "hcpl", "salary", "compensation", "payout_amount",
    "incentive_amount", "amount_l",
)


class AuditPayloadError(Exception):
    """Raised if an event's source_reference looks like it might carry
    restricted data -- fails closed rather than silently logging it."""


@dataclass(frozen=True)
class AuditEvent:
    event_type: str
    decision_id: Optional[str]
    status: Optional[str]
    source_reference: Optional[str] = None
    rule_version: str = RULE_VERSION
    code_version: str = CODE_VERSION
    event_timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __post_init__(self):
        if self.event_type not in EVENT_TYPES:
            raise ValueError(f"unknown event_type: {self.event_type}")
        if self.source_reference:
            lowered = self.source_reference.lower()
            for fragment in _DISALLOWED_FIELD_NAME_FRAGMENTS:
                if fragment in lowered:
                    raise AuditPayloadError(
                        f"source_reference for {self.event_type}/{self.decision_id} contains "
                        f"'{fragment}' -- looks like it may carry restricted data; use a "
                        f"document/thread reference instead (e.g. 'email-thread-2026-09-30'), "
                        f"never the content itself"
                    )

    def to_dict(self) -> dict:
        return asdict(self)


def emit(event: AuditEvent, log_path: Optional[Path] = None) -> None:
    """Append one audit event as a JSON line. Default log path is under
    the repo's scratch/log area, never incentive_working/ -- this log is
    safe to inspect without restricted-data access controls."""
    if log_path is None:
        log_path = Path(__file__).resolve().parent.parent.parent / "logs" / "incentive_decision_audit.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event.to_dict(), sort_keys=True) + "\n")
