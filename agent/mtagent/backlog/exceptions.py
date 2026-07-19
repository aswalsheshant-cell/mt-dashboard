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
    -- not hypothetical examples. Both original exceptions below are now
    CLOSED (kept for audit trail, not deleted): June'26 source files
    arrived 2026-07-19 and were processed for real (see
    agent/pbi_build/FY27_Jun26/); the openpyxl dependency was removed
    the same day by rewriting the release-gate scans to pure stdlib
    (agent/mtagent/validators/_xlsx_stdlib.py) after pypi.org returned
    HTTP 403 (an organization policy denial) on a real install attempt."""
    e1 = Exception_(
        title="June'26 (2026) primary and secondary source files are not present in this environment",
        severity="High",
        impact="JUN26-V3, REPRO-1, EVID-1, and CLOSE-1 cannot proceed; the audit backlog cannot reach "
               "a genuine business outcome without them",
        root_cause="the two xlsx files audited in an earlier session were never saved into this repo "
                   "or this session's working environment",
        recommended_action="RESOLVED 2026-07-19: real June'26 primary (MTD_Primary_Jun_26.csv, 23,193 rows) "
                           "and secondary (secondary_distributor_chain_Jun_26.csv, 712 rows) supplied and "
                           "processed -- allocated, reconciled to exact zero diff, see "
                           "agent/pbi_build/FY27_Jun26/Reconciliation_Report_Jun26.md",
        owner="Sheshant Aswal (repo owner)",
        due_date="before JUN26-V3 can start",
        blocking_status="was blocking JUN26-V3, REPRO-1, EVID-1, CLOSE-1 -- no longer blocking",
        verification_method="files present under PowerBI/RawDataFolders/ matching June'26, "
                             "confirmed via Environment Readiness / source_inventory stage",
    )
    e1.close()
    e2 = Exception_(
        title="openpyxl is not installed and this sandbox has no network access to install it",
        severity="Medium",
        impact="2 release-gate tests (hidden-sheet redaction) remain unexecuted here; "
               "APPROVED_FOR_SHARING cannot be certified for workbook outputs from this environment",
        root_cause="agent/requirements.txt lists openpyxl as optional infrastructure, but pypi.org returned "
                   "HTTP 403 (an organization policy denial, confirmed via a real install attempt, not assumed) "
                   "when installation was attempted from this sandboxed session",
        recommended_action="RESOLVED 2026-07-19: redaction_scan()/formula_error_scan() rewritten to read "
                           ".xlsx via stdlib zipfile + ElementTree instead of requiring openpyxl -- "
                           "agent/mtagent/validators/_xlsx_stdlib.py. All redaction-scan tests now run and "
                           "pass in this environment with 0 skipped.",
        owner="Sheshant Aswal (repo owner) / whoever runs the release-gate checks locally",
        due_date="before certifying any workbook output as APPROVED_FOR_SHARING",
        blocking_status="was blocking TEST-OPENPYXL, EVID-1 -- no longer blocking",
        verification_method="python -m unittest tests.test_release_gate -v shows 0 skipped",
    )
    e2.close()
    return [e1, e2]
