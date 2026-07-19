"""Recovery and Resume Skill.

Lets an interrupted workflow continue safely by reading back what the
worklog already recorded for a given run -- never repeats a completed
destructive action, never overwrites an already-approved output. Built
directly on the real `run_id` field controller.py now stamps onto every
worklog entry (agent/mtagent/worklog.py schema v2), not a separate,
parallel state file that could drift from the real audit trail.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..worklog import read_log


@dataclass
class ResumeState:
    run_id: str
    found: bool
    last_completed_stage: str | None
    stage_results: dict
    inputs_used: list
    output_hashes: dict
    rules_version: str | None
    files_created: list
    blocking_issue: str | None
    next_safe_action: str


def find_run(cfg, run_id: str, tail: int = 5000) -> ResumeState:
    """Search the worklog for the most recent entry matching `run_id`.
    Reads a large tail rather than a separate index -- the worklog IS the
    source of truth, there is no second state file to fall out of sync.
    """
    entries = [e for e in read_log(cfg, tail=tail) if e.get("run_id") == run_id]
    if not entries:
        return ResumeState(run_id=run_id, found=False, last_completed_stage=None,
                            stage_results={}, inputs_used=[], output_hashes={},
                            rules_version=None, files_created=[], blocking_issue=None,
                            next_safe_action=f"no worklog entry found for run_id '{run_id}' -- nothing to resume")
    latest = entries[-1]
    stage_results = latest.get("stage_results") or {}
    last_completed = None
    for name, status in stage_results.items():
        if status == "PASS":
            last_completed = name

    decision_required = latest.get("decision_required") or []
    if decision_required:
        next_action = f"resolve pending decision(s) before resuming: {'; '.join(decision_required)}"
    elif latest.get("status", 1) != 0:
        failing = [n for n, s in stage_results.items() if s != "PASS"]
        next_action = (f"the run did not complete cleanly (stage(s) not PASS: {', '.join(failing) or 'unknown'}) "
                       f"-- re-diagnose before re-running the same instruction, do not blindly retry")
    else:
        next_action = "run completed cleanly -- nothing to resume"

    return ResumeState(
        run_id=run_id, found=True, last_completed_stage=last_completed,
        stage_results=stage_results, inputs_used=latest.get("input_files") or [],
        output_hashes=latest.get("output_hashes") or {},
        rules_version=None,   # not yet tracked in worklog v2 -- honest gap, not fabricated
        files_created=latest.get("output_files") or [],
        blocking_issue=("; ".join(decision_required) if decision_required else None),
        next_safe_action=next_action,
    )


def format_resume_state(state: ResumeState) -> str:
    if not state.found:
        return f"Resume: no record of run_id '{state.run_id}'.\nNext safe action: {state.next_safe_action}"
    lines = [
        f"Resume state for run_id '{state.run_id}':", "",
        f"Last completed stage: {state.last_completed_stage or '(none)'}",
        f"Stage results: {state.stage_results}",
        f"Inputs used: {state.inputs_used or '(none recorded)'}",
        f"Output hashes: {state.output_hashes or '(none recorded)'}",
        f"Rules version: {state.rules_version or '(not tracked yet)'}",
        f"Files created: {state.files_created or '(none)'}",
        f"Blocking issue: {state.blocking_issue or '(none)'}",
        "",
        f"Next safe action: {state.next_safe_action}",
    ]
    return "\n".join(lines)
