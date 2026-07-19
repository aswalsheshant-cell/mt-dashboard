"""Evidence Packaging Skill + Leadership Communication Skill.

Produces the 10-file evidence package a reviewer can read without
touching the codebase. A file this skill cannot honestly populate (no
June'26 source data, no openpyxl in this environment) is written with an
explicit NOT_AVAILABLE marker and the exact reason -- never a fabricated
placeholder that looks like real content.
"""
from __future__ import annotations

from pathlib import Path

PACKAGE_FILES = [
    "01_Executive_Summary.md", "02_Backlog_Closure_Matrix.csv",
    "03_Rule_Test_Traceability.csv", "04_June26_V3_Reconciliation.csv",
    "05_June26_Exception_Report.csv", "06_Reproducibility_Report.md",
    "07_Test_Results.txt", "08_Release_Gate_Report.md",
    "09_Source_and_Output_Hashes.csv", "10_Remaining_Risks.md",
]

NOT_AVAILABLE = "NOT_AVAILABLE"


def not_available_content(filename: str, reason: str) -> str:
    return (f"{NOT_AVAILABLE}\n\nThis file could not be produced with real data.\n\n"
            f"Reason: {reason}\n\nThis is a disclosed gap, not a placeholder for real content -- "
            f"do not treat this file as evidence of anything until it is regenerated with real inputs.")


def build_package(repo_root: str, backlog, traceability_rows, test_results_text: str,
                   exceptions: list, out_dir: str = "agent/pbi_build/backlog_evidence") -> dict:
    """Writes what's real, marks what isn't. Returns {filename: status}
    where status is 'written' or 'NOT_AVAILABLE: <reason>'.
    """
    from .traceability import format_csv, summarize
    root = Path(repo_root)
    out = root / out_dir
    out.mkdir(parents=True, exist_ok=True)
    status: dict = {}

    # 03: real, from actual repo evidence
    (out / "03_Rule_Test_Traceability.csv").write_text(format_csv(traceability_rows), encoding="utf-8")
    status["03_Rule_Test_Traceability.csv"] = "written"

    # 02: real, from the actual backlog orchestration state
    import csv as _csv
    import io as _io
    buf = _io.StringIO()
    w = _csv.writer(buf)
    w.writerow(["Task ID", "Business purpose", "Status", "Blocking reason"])
    for t in backlog.all():
        w.writerow([t.task_id, t.business_purpose, t.status, t.blocking_reason])
    (out / "02_Backlog_Closure_Matrix.csv").write_text(buf.getvalue(), encoding="utf-8")
    status["02_Backlog_Closure_Matrix.csv"] = "written"

    # 07: real, from the actual test run
    (out / "07_Test_Results.txt").write_text(test_results_text, encoding="utf-8")
    status["07_Test_Results.txt"] = "written"

    # 04/05: cannot be produced -- no June'26 source data in this environment
    reason_june = ("no June'26 (2026) primary/secondary source files are present in this repo/session -- "
                    "the audit that would produce this file has not run (see JUN26-V3 in the backlog)")
    for f in ("04_June26_V3_Reconciliation.csv", "05_June26_Exception_Report.csv"):
        (out / f).write_text(not_available_content(f, reason_june), encoding="utf-8")
        status[f] = f"NOT_AVAILABLE: {reason_june}"

    # 06: cannot be produced -- depends on 04
    reason_repro = "depends on JUN26-V3 (04), which has not run -- see reason above"
    (out / "06_Reproducibility_Report.md").write_text(not_available_content("06_Reproducibility_Report.md", reason_repro), encoding="utf-8")
    status["06_Reproducibility_Report.md"] = f"NOT_AVAILABLE: {reason_repro}"

    # 09: partial -- real repo-file hashes can be produced now; June output hashes cannot
    from ..worklog import hash_files
    known_files = [
        root / "PowerBI" / "SeedData" / "Masters" / "ChainMaster.csv",
        root / "PowerBI" / "SeedData" / "Mapping" / "ChainAccount_Mapping_Inferred.csv",
    ]
    known_files = [f for f in known_files if f.exists()]
    hashes = hash_files(known_files) if known_files else {}
    import json as _json
    hash_note = ("June'26 output hashes: NOT_AVAILABLE (no June'26 build exists). "
                 "The hashes below are for the CURRENT mapping master files only, as evidence of "
                 "what R7-R10 in the traceability matrix were checked against.")
    (out / "09_Source_and_Output_Hashes.csv").write_text(
        hash_note + "\n\n" + _json.dumps(hashes, indent=2), encoding="utf-8")
    status["09_Source_and_Output_Hashes.csv"] = "written (partial -- see note in file)"

    # 08: real -- release gate mechanism status can be reported honestly right now
    release_note = (
        "Release Gate Report\n\n"
        "This environment cannot certify APPROVED_FOR_SHARING for any June'26 output because:\n"
        "1. No June'26 source data exists here (totals_reconciled, period_status_confirmed cannot be set True)\n"
        "2. openpyxl is not installed (confidentiality_level_confirmed cannot be verified for workbook outputs)\n\n"
        "The release-gate MECHANISM itself is implemented and tested: see "
        "agent/mtagent/validators/release_gate.py and agent/tests/test_release_gate.py.\n"
    )
    (out / "08_Release_Gate_Report.md").write_text(release_note, encoding="utf-8")
    status["08_Release_Gate_Report.md"] = "written (mechanism status, not a June'26 verdict)"

    # 10: real -- the actual known risks/exceptions
    from .exceptions import format_exception
    risk_text = "\n\n---\n\n".join(format_exception(e) for e in exceptions)
    (out / "10_Remaining_Risks.md").write_text(risk_text, encoding="utf-8")
    status["10_Remaining_Risks.md"] = "written"

    # 01: written last, summarizing the other 9
    trace_summary = summarize(traceability_rows)
    exec_summary = format_executive_summary(backlog, trace_summary, exceptions)
    (out / "01_Executive_Summary.md").write_text(exec_summary, encoding="utf-8")
    status["01_Executive_Summary.md"] = "written"

    return status


def format_executive_summary(backlog, trace_summary: dict, exceptions: list) -> str:
    closed = sum(1 for t in backlog.all() if t.status == "CLOSED")
    blocked = [t for t in backlog.all() if t.status == "BLOCKED"]
    return "\n".join([
        "# June'26 Audit Backlog -- Executive Summary", "",
        "## What was achieved", "",
        f"- Traceability check completed for {trace_summary['total']} business rules using real repo "
        f"evidence: {trace_summary['pass']} PASS, {trace_summary['partial']} PARTIAL (mechanism ready, "
        f"not yet applied to June data), {trace_summary['fail']} FAIL (a real gap found), "
        f"{trace_summary['not_evaluated']} NOT_EVALUATED (environment-blocked).",
        f"- {closed}/{len(backlog.all())} backlog tasks CLOSED; {len(blocked)} BLOCKED.",
        "",
        "## What was proven", "",
        "- Store-level chain explosion prevention, alias scoping, commit/push approval-gating, and the "
        "release-gate checklist mechanism are all real and test-covered (see traceability matrix).",
        "",
        "## What risk remains", "",
        *[f"- {e.title} ({e.severity})" for e in exceptions],
        "",
        "## What decision is required", "",
        "- Provide the June'26 primary and secondary source files, or confirm they don't yet exist for this period.",
        "- Install openpyxl on a machine with network access and confirm 0 skipped tests in test_release_gate.py.",
        "",
        "## What happens next", "",
        "- Once both are resolved, JUN26-V3 can run for real, followed by reproducibility, full release-gate "
        "evaluation, and a genuine evidence package -- not before.",
    ])
