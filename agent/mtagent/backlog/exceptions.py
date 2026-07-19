"""Exception Ownership Skill.

Every exception must have an owner, an action, and a verification method
-- an issue with no owner cannot be closed, structurally, not just by
convention.
"""
from __future__ import annotations

from dataclasses import dataclass

OPEN = "open"
CLOSED = "closed"


@dataclass
class Exception_:  # trailing underscore: `Exception` shadows the builtin
    title: str
    severity: str              # High | Medium | Low
    impact: str
    root_cause: str
    recommended_action: str
    owner: str
    due_date: str
    blocking_status: str       # e.g. "Blocking JUN26-V3" or "Not blocking"
    verification_method: str
    status: str = OPEN

    def can_close(self) -> tuple:
        if not self.owner:
            return False, "cannot close -- no owner assigned"
        if not self.recommended_action:
            return False, "cannot close -- no recommended action recorded"
        return True, "ok"

    def close(self) -> None:
        ok, reason = self.can_close()
        if not ok:
            raise ValueError(reason)
        self.status = CLOSED


def format_exception(exc: Exception_) -> str:
    return "\n".join([
        f"Exception:\n{exc.title}", "",
        f"Severity:\n{exc.severity}", "",
        f"Impact:\n{exc.impact}", "",
        f"Root cause:\n{exc.root_cause}", "",
        f"Recommended action:\n{exc.recommended_action}", "",
        f"Owner:\n{exc.owner}", "",
        f"Due date:\n{exc.due_date}", "",
        f"Blocking status:\n{exc.blocking_status}", "",
        f"Verification method:\n{exc.verification_method}",
    ])


def known_backlog_exceptions() -> list:
    """The two real, current blockers found while running this backlog
    -- not hypothetical examples."""
    return [
        Exception_(
            title="June'26 (2026) primary and secondary source files are not present in this environment",
            severity="High",
            impact="JUN26-V3, REPRO-1, EVID-1, and CLOSE-1 cannot proceed; the audit backlog cannot reach "
                   "a genuine business outcome without them",
            root_cause="the two xlsx files audited in an earlier session were never saved into this repo "
                       "or this session's working environment",
            recommended_action="re-upload or point to the June'26 primary and secondary distributor extracts",
            owner="Sheshant Aswal (repo owner)",
            due_date="before JUN26-V3 can start",
            blocking_status="Blocking JUN26-V3, REPRO-1, EVID-1, CLOSE-1",
            verification_method="files present under PowerBI/RawDataFolders/ matching June'26, "
                                 "confirmed via Environment Readiness / source_inventory stage",
        ),
        Exception_(
            title="openpyxl is not installed and this sandbox has no network access to install it",
            severity="Medium",
            impact="2 release-gate tests (hidden-sheet redaction) remain unexecuted here; "
                   "APPROVED_FOR_SHARING cannot be certified for workbook outputs from this environment",
            root_cause="agent/requirements.txt lists openpyxl as optional infrastructure, but no package "
                       "index is reachable from this sandboxed session",
            recommended_action="run `python -m pip install -r agent/requirements.txt` on a machine with "
                               "network access (e.g. the analyst's own Windows machine per CONTROLLER_GUIDE.md), "
                               "then rerun `python -m unittest tests.test_release_gate -v` and confirm 0 skipped",
            owner="Sheshant Aswal (repo owner) / whoever runs the release-gate checks locally",
            due_date="before certifying any workbook output as APPROVED_FOR_SHARING",
            blocking_status="Blocking TEST-OPENPYXL, EVID-1",
            verification_method="python -c \"import openpyxl; print(openpyxl.__version__)\" succeeds, "
                                 "then test_release_gate.py shows 0 skipped",
        ),
    ]
