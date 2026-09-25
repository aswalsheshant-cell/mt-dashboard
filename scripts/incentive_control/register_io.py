"""Load a FY27 incentive decision register (JSON, matching
schemas/fy27_incentive_decision.schema.json) into DecisionRecord objects.

This module never reads incentive_working/ by default -- callers pass an
explicit path. CI passes synthetic fixture paths under tests/fixtures/;
a human running this locally against the real, gitignored register passes
that path explicitly on the command line.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import List

import jsonschema

from .models import DecisionRecord

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCHEMA_PATH = REPO_ROOT / "schemas" / "fy27_incentive_decision.schema.json"


class RegisterLoadError(Exception):
    """Raised when a register file fails schema validation -- distinct from
    a decision-level gate block, this means the file itself is malformed
    and no decision content can be trusted from it."""


def load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def load_register(path: Path) -> List[DecisionRecord]:
    """Read, schema-validate, and parse a register JSON file.

    Raises RegisterLoadError (with the jsonschema validation message) if
    the file does not conform to schemas/fy27_incentive_decision.schema.json.
    Never returns a partial/best-effort parse of a malformed file.
    """
    path = Path(path)
    if not path.is_file():
        raise RegisterLoadError(f"Register file not found: {path}")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise RegisterLoadError(f"{path}: invalid JSON -- {e}") from e

    schema = load_schema()
    try:
        jsonschema.validate(instance=data, schema=schema)
    except jsonschema.ValidationError as e:
        raise RegisterLoadError(f"{path}: FAIL_SCHEMA -- {e.message} (at {'/'.join(str(p) for p in e.absolute_path)})") from e

    records = []
    for d in data["decisions"]:
        records.append(DecisionRecord(
            decision_id=d["decision_id"],
            decision_owner=d["decision_owner"],
            affected_period=d["affected_period"],
            allowed_responses=tuple(d["allowed_responses"]),
            current_status=d["current_status"],
            selected_response=d.get("selected_response"),
            approved_by=d.get("approved_by"),
            approval_date=d.get("approval_date"),
            evidence_reference=d.get("evidence_reference"),
            business_rule_result=d.get("business_rule_result"),
            implementation_status=d.get("implementation_status", "NOT_STARTED"),
            consulted_owner=d.get("consulted_owner"),
            affected_entity=d.get("affected_entity"),
            affected_value_l=d.get("affected_value_l"),
            affected_store_count=d.get("affected_store_count"),
            notes=d.get("notes"),
        ))
    return records


def load_register_raw(path: Path) -> dict:
    """Schema-validated raw dict (unlike load_register(), keeps every field
    -- including revision_history -- so a caller can modify one decision
    and write the whole structure back without losing anything)."""
    path = Path(path)
    if not path.is_file():
        raise RegisterLoadError(f"Register file not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise RegisterLoadError(f"{path}: invalid JSON -- {e}") from e
    schema = load_schema()
    try:
        jsonschema.validate(instance=data, schema=schema)
    except jsonschema.ValidationError as e:
        raise RegisterLoadError(f"{path}: FAIL_SCHEMA -- {e.message} (at {'/'.join(str(p) for p in e.absolute_path)})") from e
    return data


def save_register_raw(path: Path, data: dict) -> None:
    """Schema-validates before writing -- refuses to persist a register
    that would fail load_register_raw() on the next read. Fail-closed: an
    invalid update never reaches disk."""
    schema = load_schema()
    try:
        jsonschema.validate(instance=data, schema=schema)
    except jsonschema.ValidationError as e:
        raise RegisterLoadError(
            f"refusing to write {path}: resulting register would FAIL_SCHEMA -- "
            f"{e.message} (at {'/'.join(str(p) for p in e.absolute_path)})"
        ) from e
    Path(path).write_text(json.dumps(data, indent=2, sort_keys=False) + "\n", encoding="utf-8")
