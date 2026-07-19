"""Audit Rerun Skill.

Executes an audit from source to validated output as 16 named stages, in
order, halting at the first stage that reports BLOCKED or FAIL -- later
stages are never attempted on top of an unresolved earlier one. Each
stage function receives the running `AuditContext` and returns a
`StageOutcome`; the runner does the halting, stages don't have to.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

STAGE_NAMES = [
    "environment_readiness", "source_inventory", "source_hash_capture",
    "schema_validation", "canonical_mapping_load", "transformation",
    "row_reconciliation", "nsv_reconciliation", "qty_reconciliation",
    "canonical_chain_validation", "store_explosion_test", "partial_month_validation",
    "exception_generation", "leadership_insight_generation", "release_gate_evaluation",
    "evidence_packaging",
]

PASS = "PASS"
BLOCKED = "BLOCKED"
FAIL = "FAIL"


@dataclass
class StageOutcome:
    stage: str
    status: str
    rows_in: int = 0
    rows_out: int = 0
    control_total: dict = field(default_factory=dict)
    exception_count: int = 0
    evidence_file: str = ""
    blocking_issue: str = ""


@dataclass
class AuditContext:
    repo_root: Path
    period_label: str
    source_files: list = field(default_factory=list)
    data: dict = field(default_factory=dict)   # stages stash intermediate results here


@dataclass
class AuditRunResult:
    stages: list                # list[StageOutcome], only up to and including the halting stage
    halted_at: str | None       # stage name, or None if all 16 completed


def _stage_environment_readiness(ctx: AuditContext) -> StageOutcome:
    from . import environment as env
    report = env.check_environment(repo_root=str(ctx.repo_root))
    ctx.data["environment_report"] = report
    if report.status != env.READY:
        return StageOutcome("environment_readiness", BLOCKED,
                             blocking_issue="; ".join(report.missing))
    return StageOutcome("environment_readiness", PASS)


def _stage_source_inventory(ctx: AuditContext) -> StageOutcome:
    raw_dir = ctx.repo_root / "PowerBI" / "RawDataFolders"
    found = []
    if raw_dir.exists():
        period_slug = ctx.period_label.lower().replace("'", "").replace(" ", "")
        for p in raw_dir.rglob("*"):
            if p.is_file() and period_slug in p.name.lower().replace("_", "").replace("-", ""):
                found.append(p)
    ctx.source_files = found
    if not found:
        return StageOutcome("source_inventory", BLOCKED,
                             blocking_issue=f"no source files matching period '{ctx.period_label}' found "
                                            f"under {raw_dir} -- cannot proceed without the actual primary and "
                                            f"secondary/distributor extracts for this period")
    return StageOutcome("source_inventory", PASS, rows_in=0, rows_out=len(found),
                         evidence_file=", ".join(str(f) for f in found))


# Stages 3-16 are intentionally NOT implemented with real transformation
# logic here -- there is no real pipeline function for a from-scratch
# "June'26 v3" build (the real pipeline builds from committed monthly
# CSVs via pbi_dataset.py, which already has its own tested path). This
# stage machine's job is to prove the ORDERING and HALT discipline for
# real; stages downstream of a real blocker are represented as
# not-yet-implemented rather than faked into a false PASS.
def _stage_not_implemented(name: str):
    def _stage(ctx: AuditContext) -> StageOutcome:
        return StageOutcome(name, BLOCKED,
                             blocking_issue=f"stage '{name}' has no real implementation wired in this "
                                            f"environment yet -- would only be reachable once source_inventory "
                                            f"passes, which requires real source files")
    return _stage


STAGES = {"environment_readiness": _stage_environment_readiness, "source_inventory": _stage_source_inventory}
for _name in STAGE_NAMES:
    if _name not in STAGES:
        STAGES[_name] = _stage_not_implemented(_name)


def run_audit(repo_root: str, period_label: str) -> AuditRunResult:
    ctx = AuditContext(repo_root=Path(repo_root), period_label=period_label)
    results = []
    for stage_name in STAGE_NAMES:
        outcome = STAGES[stage_name](ctx)
        results.append(outcome)
        if outcome.status != PASS:
            return AuditRunResult(stages=results, halted_at=stage_name)
    return AuditRunResult(stages=results, halted_at=None)


def format_result(result: AuditRunResult) -> str:
    lines = ["Audit rerun stages:", ""]
    for s in result.stages:
        lines.append(f"{s.stage}: {s.status}" + (f"  ({s.blocking_issue})" if s.blocking_issue else ""))
    lines.append("")
    lines.append(f"Halted at: {result.halted_at or '(completed all 16 stages)'}")
    return "\n".join(lines)
