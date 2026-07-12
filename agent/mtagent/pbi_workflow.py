"""Power BI Workflow Controller — the stateful backbone of Module 2.

Manages the 16-step Power BI dashboard preparation sequence end to end,
persistently, so a build can be paused (e.g. to go do something inside
Power BI Desktop) and resumed later without losing the last completed
step. Nothing here drives Power BI Desktop itself — see the module
docstring in ``pbi_dataset.py`` / ``pbi_dax_gap.py`` for what is actually
automated vs. what this controller only *tracks* as a manual step.

State is a single JSON file (gitignored, like ``agent/index/``):
    agent/index/pbi_workflow_state.json

Every state transition is appended to an in-file ``events`` audit log
(distinct from the generic ``worklog.py`` CLI-run log — this one is
scoped to the Power BI build and captures step-level detail: which step,
old status -> new status, evidence, warnings/blockers).
"""
from __future__ import annotations

import datetime
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Optional

from .config import Config

STATE_FILE = "pbi_workflow_state.json"


# --------------------------------------------------------------------- #
# Statuses — exact strings from the spec (used verbatim in state files
# and CLI output, so do not rename without a migration).
# --------------------------------------------------------------------- #
NOT_STARTED = "Not Started"
READY = "Ready"
RUNNING = "Running"
COMPLETED = "Completed"
COMPLETED_WITH_WARNING = "Completed with Warning"
MANUAL_ACTION_REQUIRED = "Manual Action Required"
APPROVAL_REQUIRED = "Approval Required"
BLOCKED = "Blocked"
FAILED = "Failed"
SKIPPED_WITH_APPROVAL = "Skipped with Approval"

TERMINAL_OK = {COMPLETED, COMPLETED_WITH_WARNING, SKIPPED_WITH_APPROVAL}
STATUSES = (NOT_STARTED, READY, RUNNING, COMPLETED, COMPLETED_WITH_WARNING,
            MANUAL_ACTION_REQUIRED, APPROVAL_REQUIRED, BLOCKED, FAILED,
            SKIPPED_WITH_APPROVAL)

AUTOMATED = "automated"
MANUAL = "manual"
APPROVAL = "approval"

EVIDENCE_KINDS = ("screenshot", "metadata_export", "query_output", "file_output", "user_confirmation")


# --------------------------------------------------------------------- #
# The 16-step sequence (spec order, fixed — do not reorder without
# bumping a schema version, since saved state references steps by id).
# --------------------------------------------------------------------- #
@dataclass(frozen=True)
class StepDef:
    id: str
    seq: int
    name: str
    classification: str   # AUTOMATED | MANUAL | APPROVAL


STEP_SEQUENCE: list[StepDef] = [
    StepDef("validate_sources", 1, "Validate source files.", AUTOMATED),
    StepDef("build_datasets", 2, "Build Power BI-ready datasets.", AUTOMATED),
    StepDef("generate_dim_fact", 3, "Generate dimension and fact tables.", AUTOMATED),
    StepDef("validate_keys", 4, "Validate business keys and relationships.", AUTOMATED),
    StepDef("generate_power_query", 5, "Generate Power Query scripts.", AUTOMATED),
    StepDef("generate_dax", 6, "Generate the DAX measure library.", AUTOMATED),
    StepDef("generate_page_blueprint", 7, "Generate the page-wise visual blueprint.", AUTOMATED),
    StepDef("generate_theme", 8, "Generate the Power BI theme JSON.", AUTOMATED),
    StepDef("generate_docs", 9, "Generate model documentation.", AUTOMATED),
    StepDef("prepare_build_package", 10, "Prepare the Power BI build package.", AUTOMATED),
    StepDef("manual_desktop_actions", 11, "Guide the user through manual Power BI Desktop actions.", MANUAL),
    StepDef("review_evidence", 12, "Review screenshots and exported metadata.", MANUAL),
    StepDef("reconcile_source_to_model", 13, "Run source-to-model reconciliation.", AUTOMATED),
    StepDef("page_level_qc", 14, "Run page-level QC.", MANUAL),
    StepDef("final_release_qc", 15, "Run final dashboard release QC.", APPROVAL),
    StepDef("mark_release_complete", 16, "Mark the approved release package as complete.", APPROVAL),
]
STEP_BY_ID = {s.id: s for s in STEP_SEQUENCE}


@dataclass
class StepRecord:
    id: str
    seq: int
    name: str
    classification: str
    status: str = NOT_STARTED
    required_input: str = ""
    output_file: str = ""
    validation_result: str = ""
    warning: str = ""
    blocker: str = ""
    approval_status: str = ""
    completed_at: str = ""


@dataclass
class WorkflowState:
    schema_version: int = 1
    build_id: str = ""
    started_at: str = ""
    steps: dict = field(default_factory=dict)      # id -> StepRecord (as dict)
    events: list = field(default_factory=list)      # audit trail


def _now() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def _fresh_state() -> WorkflowState:
    steps = {
        s.id: asdict(StepRecord(id=s.id, seq=s.seq, name=s.name, classification=s.classification))
        for s in STEP_SEQUENCE
    }
    steps[STEP_SEQUENCE[0].id]["status"] = READY
    return WorkflowState(build_id=_now().replace(":", ""), started_at=_now(), steps=steps)


class WorkflowController:
    """Loads/saves ``pbi_workflow_state.json`` and enforces the sequence's
    status transitions. All mutation goes through this class so the audit
    trail (``state.events``) is always complete.
    """

    def __init__(self, cfg: Config):
        self.cfg = cfg
        self._path = cfg.path(cfg.index_path).parent / STATE_FILE
        self.state = self._load()

    # -- persistence --------------------------------------------------
    def _load(self) -> WorkflowState:
        if self._path.exists():
            try:
                data = json.loads(self._path.read_text(encoding="utf-8"))
                return WorkflowState(**data)
            except (OSError, json.JSONDecodeError, TypeError):
                pass  # corrupt/legacy state -> start fresh rather than crash
        return _fresh_state()

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(asdict(self.state), indent=2, ensure_ascii=False), encoding="utf-8")

    # -- internal helpers ----------------------------------------------
    def _record(self, step_id: str) -> dict:
        if step_id not in self.state.steps:
            raise KeyError(f"unknown workflow step: {step_id!r}")
        return self.state.steps[step_id]

    def _log_event(self, step_id: str, from_status: str, to_status: str, note: str = "") -> None:
        self.state.events.append({
            "ts": _now(), "step": step_id, "from": from_status, "to": to_status, "note": note,
        })

    def _set_status(self, step_id: str, status: str, **fields) -> None:
        rec = self._record(step_id)
        old = rec["status"]
        rec["status"] = status
        for k, v in fields.items():
            if k in rec:
                rec[k] = v
        self._log_event(step_id, old, status, fields.get("blocker") or fields.get("warning") or "")
        self.save()

    def _advance_ready(self, completed_step_id: str) -> None:
        """Mark the next step Ready once the given step reaches a terminal-OK state."""
        completed = STEP_BY_ID[completed_step_id]
        for s in STEP_SEQUENCE:
            if s.seq == completed.seq + 1 and self.state.steps[s.id]["status"] == NOT_STARTED:
                self._set_status(s.id, READY)
                break

    # -- public transitions ---------------------------------------------
    def start_step(self, step_id: str, required_input: str = "") -> None:
        self._set_status(step_id, RUNNING, required_input=required_input)

    def complete_step(self, step_id: str, output_file: str = "", validation_result: str = "",
                       warning: str = "") -> None:
        status = COMPLETED_WITH_WARNING if warning else COMPLETED
        self._set_status(step_id, status, output_file=output_file,
                          validation_result=validation_result, warning=warning,
                          completed_at=_now())
        self._advance_ready(step_id)

    def fail_step(self, step_id: str, error: str) -> None:
        self._set_status(step_id, FAILED, blocker=error)

    def block_step(self, step_id: str, reason: str, required_input: str = "") -> None:
        self._set_status(step_id, BLOCKED, blocker=reason, required_input=required_input)

    def require_manual_action(self, step_id: str, instructions: str) -> None:
        self._set_status(step_id, MANUAL_ACTION_REQUIRED, required_input=instructions)

    def require_approval(self, step_id: str, summary: str) -> None:
        self._set_status(step_id, APPROVAL_REQUIRED, validation_result=summary, approval_status="Pending")

    def skip_with_approval(self, step_id: str, reason: str) -> None:
        self._set_status(step_id, SKIPPED_WITH_APPROVAL, blocker=reason,
                          approval_status="Approved", completed_at=_now())
        self._advance_ready(step_id)

    def mark_step_complete(self, step_id: str, evidence_kind: str, evidence: str) -> dict:
        """'Mark this step complete' command. Refuses to complete a step
        whose evidence itself indicates an unresolved error — the caller
        must fix the underlying problem and provide clean evidence.
        """
        if evidence_kind not in EVIDENCE_KINDS:
            raise ValueError(f"unknown evidence_kind {evidence_kind!r}, expected one of {EVIDENCE_KINDS}")
        if not evidence or not str(evidence).strip():
            raise ValueError("evidence must be a non-empty string (screenshot path, export path, or confirmation text)")
        lowered = str(evidence).lower()
        if any(bad in lowered for bad in ("error", "failed", "broken", "blank visual", "#error", "n/a")):
            self.block_step(step_id, f"evidence indicates an unresolved problem: {evidence!r}")
            return {"ok": False, "status": BLOCKED, "reason": "evidence shows an unresolved error"}
        rec = self._record(step_id)
        self.complete_step(step_id, output_file=rec.get("output_file", ""),
                            validation_result=f"confirmed via {evidence_kind}: {evidence}")
        return {"ok": True, "status": self.state.steps[step_id]["status"]}

    # -- read-only queries -----------------------------------------------
    def status_summary(self) -> dict:
        steps = sorted(self.state.steps.values(), key=lambda r: r["seq"])
        completed = [s for s in steps if s["status"] in TERMINAL_OK]
        current = next((s for s in steps if s["status"] in (RUNNING, READY, MANUAL_ACTION_REQUIRED,
                                                             APPROVAL_REQUIRED, BLOCKED, FAILED)), None)
        next_step = next((s for s in steps if s["status"] == NOT_STARTED), None)
        manual_pending = [s["name"] for s in steps
                           if s["classification"] == MANUAL and s["status"] not in TERMINAL_OK]
        automated_pending = [s["name"] for s in steps
                              if s["classification"] == AUTOMATED and s["status"] not in TERMINAL_OK]
        blockers = list(dict.fromkeys(s["blocker"] for s in steps if s["status"] in (BLOCKED, FAILED) and s["blocker"]))
        warnings = list(dict.fromkeys(s["warning"] for s in steps if s["warning"]))
        return {
            "build_id": self.state.build_id,
            "completion_pct": round(100 * len(completed) / len(steps), 1),
            "completed_phases": [s["name"] for s in completed],
            "current_phase": current["name"] if current else None,
            "current_status": current["status"] if current else None,
            "next_step": next_step["name"] if next_step else None,
            "manual_steps_pending": manual_pending,
            "automated_steps_pending": automated_pending,
            "blockers": blockers,
            "warnings": warnings,
            "latest_outputs": list(dict.fromkeys(s["output_file"] for s in steps if s["output_file"])),
        }

    def next_manual_step(self) -> Optional[dict]:
        for s in sorted(self.state.steps.values(), key=lambda r: r["seq"]):
            if s["status"] == MANUAL_ACTION_REQUIRED:
                return s
        return None

    def resume_plan(self) -> dict:
        """'Resume from the last completed step' — identifies the next
        valid step without repeating completed work.
        """
        steps = sorted(self.state.steps.values(), key=lambda r: r["seq"])
        last_completed = None
        for s in steps:
            if s["status"] in TERMINAL_OK:
                last_completed = s
        next_step = next((s for s in steps if s["status"] not in TERMINAL_OK), None)
        return {
            "last_completed_step": last_completed["name"] if last_completed else None,
            "next_step": next_step["name"] if next_step else None,
            "next_step_id": next_step["id"] if next_step else None,
            "next_step_status": next_step["status"] if next_step else None,
        }


def run_automated_step(controller: WorkflowController, step_id: str,
                        fn: Callable[[], dict], required_input: str = "") -> dict:
    """Wrap an automated step's handler with consistent state transitions +
    error handling, so every automated command in pbi_dataset.py /
    pbi_dax_gap.py / pbi_reconcile.py behaves identically on success,
    partial success (warning), and failure.

    `fn` must return a dict with keys: output_file, validation_result,
    warning (optional), blocked_reason (optional).
    """
    controller.start_step(step_id, required_input=required_input)
    try:
        result = fn()
    except Exception as exc:  # noqa: BLE001 -- a failing build step must never crash the CLI
        controller.fail_step(step_id, f"{type(exc).__name__}: {exc}")
        return {"status": FAILED, "error": str(exc)}

    if result.get("blocked_reason"):
        controller.block_step(step_id, result["blocked_reason"], required_input=required_input)
        return {"status": BLOCKED, **result}

    controller.complete_step(step_id, output_file=result.get("output_file", ""),
                              validation_result=result.get("validation_result", ""),
                              warning=result.get("warning", ""))
    return {"status": controller.state.steps[step_id]["status"], **result}
