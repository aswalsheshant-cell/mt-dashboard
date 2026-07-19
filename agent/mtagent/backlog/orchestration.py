"""Backlog Orchestration Skill.

Converts open items into an ordered execution plan with dependencies,
evidence requirements, and completion criteria. A task is never marked
complete because code was written -- only because its output, tests, and
evidence all exist. Technical completion and business acceptance are
tracked as separate states.
"""
from __future__ import annotations

from dataclasses import dataclass, field

NOT_STARTED = "NOT_STARTED"
READY = "READY"
IN_PROGRESS = "IN_PROGRESS"
BLOCKED = "BLOCKED"
TECHNICALLY_COMPLETE = "TECHNICALLY_COMPLETE"
VALIDATED = "VALIDATED"
CLOSED = "CLOSED"

_STATUSES = (NOT_STARTED, READY, IN_PROGRESS, BLOCKED, TECHNICALLY_COMPLETE, VALIDATED, CLOSED)


@dataclass
class BacklogTask:
    task_id: str
    business_purpose: str
    dependency: list                  # list[task_id]
    assigned_subagent: str
    input_required: list
    expected_output: str
    validation_required: str
    evidence_required: str
    status: str = NOT_STARTED
    blocking_reason: str = ""
    closure_criteria: str = ""

    def __post_init__(self):
        if self.status not in _STATUSES:
            raise ValueError(f"unknown status '{self.status}' -- must be one of {_STATUSES}")


class Backlog:
    def __init__(self, tasks: list):
        self._tasks = {t.task_id: t for t in tasks}

    def get(self, task_id: str) -> BacklogTask:
        return self._tasks[task_id]

    def all(self) -> list:
        return list(self._tasks.values())

    def dependencies_met(self, task_id: str) -> tuple:
        """A task may not start if any dependency is not yet CLOSED (or
        at least VALIDATED -- business-accepted, not just code-complete).
        Returns (met, unmet_dependency_ids).
        """
        task = self._tasks[task_id]
        unmet = [
            dep for dep in task.dependency
            if self._tasks[dep].status not in (VALIDATED, CLOSED)
        ]
        return (len(unmet) == 0, unmet)

    def refresh_ready_states(self) -> None:
        """A NOT_STARTED task becomes READY only once its dependencies are
        met -- this is the "do not start a task whose dependencies are
        incomplete" rule, enforced structurally rather than by convention.
        """
        for task in self._tasks.values():
            if task.status == NOT_STARTED:
                met, unmet = self.dependencies_met(task.task_id)
                if met:
                    task.status = READY
                else:
                    task.status = BLOCKED
                    task.blocking_reason = f"waiting on: {', '.join(unmet)}"

    def mark_technically_complete(self, task_id: str, evidence_present: bool) -> None:
        """Code being written is NOT completion. This can only be called
        with evidence_present=True backed by a real check upstream (a
        test result, a file that exists, a report that was generated) --
        the caller is responsible for that check being real, but this
        method refuses to silently accept a False.
        """
        task = self._tasks[task_id]
        if not evidence_present:
            task.status = BLOCKED
            task.blocking_reason = "cannot mark technically complete -- no evidence produced yet"
            return
        task.status = TECHNICALLY_COMPLETE

    def mark_validated(self, task_id: str, business_accepted: bool, reason: str = "") -> None:
        """Business acceptance is a SEPARATE decision from technical
        completion -- a task must be TECHNICALLY_COMPLETE first, and this
        call still requires the caller to state whether a human/process
        actually accepted the result, not just that it ran."""
        task = self._tasks[task_id]
        if task.status != TECHNICALLY_COMPLETE:
            raise ValueError(f"{task_id}: cannot validate a task that isn't TECHNICALLY_COMPLETE "
                              f"(currently {task.status})")
        if not business_accepted:
            task.status = BLOCKED
            task.blocking_reason = reason or "technically complete but not yet business-accepted"
            return
        task.status = VALIDATED

    def close(self, task_id: str) -> None:
        task = self._tasks[task_id]
        if task.status != VALIDATED:
            raise ValueError(f"{task_id}: cannot close a task that isn't VALIDATED (currently {task.status})")
        task.status = CLOSED

    def format_table(self) -> str:
        headers = ("Task ID", "Business purpose", "Dependency", "Status", "Blocking reason")
        rows = [headers]
        for t in self._tasks.values():
            rows.append((t.task_id, t.business_purpose, ", ".join(t.dependency) or "(none)",
                         t.status, t.blocking_reason or "(none)"))
        widths = [max(len(str(r[i])) for r in rows) for i in range(len(headers))]
        lines = []
        for i, row in enumerate(rows):
            lines.append(" | ".join(str(c).ljust(widths[j]) for j, c in enumerate(row)))
            if i == 0:
                lines.append("-+-".join("-" * w for w in widths))
        return "\n".join(lines)
