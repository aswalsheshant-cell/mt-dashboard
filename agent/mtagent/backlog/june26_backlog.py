"""The real June'26 audit backlog (tasks #18-22 plus the openpyxl tests,
evidence package, and closure recommendation from the Master Prompt),
instantiated against Backlog Orchestration Skill. Status below reflects
actual repo/environment state at the time this was run -- not aspiration.
"""
from __future__ import annotations

from . import environment as env
from .orchestration import Backlog, BacklogTask


def build_june26_backlog(repo_root: str) -> Backlog:
    tasks = [
        BacklogTask(
            task_id="ENV-1", business_purpose="Confirm the machine can run release-gate checks for real",
            dependency=[], assigned_subagent="environment-readiness",
            input_required=["agent/requirements.txt"], expected_output="ENVIRONMENT_READY or ENVIRONMENT_BLOCKED report",
            validation_required="python -c \"import openpyxl\" succeeds",
            evidence_required="agent/mtagent/backlog/environment.py::check_environment() output",
            closure_criteria="openpyxl importable in the environment that will run the release-gate tests",
        ),
        BacklogTask(
            task_id="TEST-OPENPYXL", business_purpose="Prove the 4 skipped release-gate tests actually pass, not just compile",
            dependency=["ENV-1"], assigned_subagent="test-orchestration",
            input_required=["agent/tests/test_release_gate.py"], expected_output="4/4 openpyxl-dependent tests PASS",
            validation_required="python -m unittest tests.test_release_gate -v",
            evidence_required="test runner output naming each test by name with PASS",
            closure_criteria="0 skipped tests in TestConfidentialHiddenSheetBlocksSharing / TestNoVersionCannotBeApproved",
        ),
        BacklogTask(
            task_id="TRACE-1", business_purpose="Connect every June'26 business rule to implementation, test, and evidence",
            dependency=[], assigned_subagent="traceability-matrix",
            input_required=["PowerBI/SeedData/Masters/*.csv", "PowerBI/SeedData/Mapping/*.csv", "agent/tests/*.py"],
            expected_output="agent/pbi_build/backlog_evidence/03_Rule_Test_Traceability.csv",
            validation_required="every row has a non-empty Evidence location before PASS",
            evidence_required="the matrix file itself, cross-checked against real repo files",
            closure_criteria="no rule shows PASS with an empty evidence column",
        ),
        BacklogTask(
            task_id="JUN26-V3", business_purpose="Produce a reconciled, provisional June'26 dataset for leadership use",
            dependency=[], assigned_subagent="audit-rerun",
            input_required=["June'26 primary source extract", "June'26 secondary/distributor source extract"],
            expected_output="agent/pbi_build/FY27_Jun26/ (Fact table + reconciliation report)",
            validation_required="row/NSV/Qty reconciliation = 0 variance; canonical chain count in expected range",
            evidence_required="Source_To_Model_Reconciliation_Report.csv for the June'26 build",
            closure_criteria="reconciliation PASS and period correctly labeled Partial",
        ),
        BacklogTask(
            task_id="REPRO-1", business_purpose="Prove the June'26 build is reproducible from the same inputs",
            dependency=["JUN26-V3"], assigned_subagent="reproducibility",
            input_required=["two independent runs of JUN26-V3 against identical source files"],
            expected_output="REPRODUCIBLE or NON_REPRODUCIBLE verdict with a diffed comparison report",
            validation_required="normalized business content (row counts, NSV/Qty totals, chain count) identical across both runs",
            evidence_required="agent/pbi_build/backlog_evidence/06_Reproducibility_Report.md",
            closure_criteria="verdict = REPRODUCIBLE, or every difference is explained as expected-technical",
        ),
        BacklogTask(
            task_id="EVID-1", business_purpose="Produce a leadership-reviewable evidence pack without requiring codebase access",
            dependency=["ENV-1", "TEST-OPENPYXL", "TRACE-1", "JUN26-V3", "REPRO-1"],
            assigned_subagent="evidence-packaging",
            input_required=["outputs of all prior tasks"],
            expected_output="agent/pbi_build/backlog_evidence/ (10-file package)",
            validation_required="every file listed in the Master Prompt's required package is present",
            evidence_required="the package directory listing itself",
            closure_criteria="all 10 files present, none marked NOT_AVAILABLE",
        ),
        BacklogTask(
            task_id="CLOSE-1", business_purpose="Give the user an explicit, evidence-backed closure recommendation",
            dependency=["EVID-1"], assigned_subagent="leadership-communication",
            input_required=["EVID-1 package"], expected_output="closure recommendation with release status and decisions required",
            validation_required="no unsupported claims -- every statement traces to a cited check",
            evidence_required="the recommendation text plus its citations",
            closure_criteria="explicit human approval recorded for release status and any commit/push",
        ),
    ]
    backlog = Backlog(tasks)

    # Real evaluation against actual environment/repo state -- not
    # aspiration. ENV-1: technically complete (the check ran for real),
    # but the outcome is BLOCKED, so it cannot be VALIDATED as "ready".
    report = env.check_environment(repo_root=repo_root)
    env1 = backlog.get("ENV-1")
    if report.status == env.READY:
        env1.status = "TECHNICALLY_COMPLETE"
    else:
        env1.status = "BLOCKED"
        env1.blocking_reason = "; ".join(report.missing)

    from pathlib import Path
    root = Path(repo_root)
    june_sources = list((root / "PowerBI" / "RawDataFolders").rglob("*jun*26*")) if (root / "PowerBI" / "RawDataFolders").exists() else []
    june26 = backlog.get("JUN26-V3")
    if not june_sources:
        june26.status = "BLOCKED"
        june26.blocking_reason = ("no June'26 (2026) primary/secondary source files found under "
                                   "PowerBI/RawDataFolders/ in this environment -- the two files audited "
                                   "in an earlier session are not present here")

    backlog.refresh_ready_states()
    # refresh_ready_states() would otherwise overwrite the two explicit
    # BLOCKED calls above with a generic dependency-based BLOCKED for
    # dependents; re-apply the specific reasons for the root-cause tasks
    # since they have no unmet dependency, only a real-world blocker.
    if report.status != env.READY:
        env1.status = "BLOCKED"
        env1.blocking_reason = "; ".join(report.missing)
    if not june_sources:
        june26.status = "BLOCKED"
        june26.blocking_reason = ("no June'26 (2026) primary/secondary source files found under "
                                   "PowerBI/RawDataFolders/ in this environment -- the two files audited "
                                   "in an earlier session are not present here")
    return backlog
