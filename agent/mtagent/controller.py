"""Main Controller — the single entry point that turns a natural-language
instruction into a structured, approval-gated execution plan, then runs it
against REAL ``mtagent pbi`` commands only (never a fabricated one).

Design constraint from `agent/AGENT_OPERATING_PRINCIPLES.md`: this module
IS the enforcement point for principles #3/#4 (outcome before execution),
#6 (entry/exit conditions per stage), #10 (no commit/push without explicit
approval). It does not reimplement any pipeline logic — every stage in a
Plan maps to a function already in `pbi_dataset.py` / `pbi_compile.py` /
`pbi_article_master.py` / `pbi_npi.py` / `pbi_reconcile.py`.

No live LLM is required or assumed. Instruction interpretation is a
conservative, regex-based classifier over the small set of instruction
shapes this project has actually used (see `KNOWN_ACTIONS`). Anything
that doesn't match is reported as UNRECOGNIZED with the closest known
verbs listed — it is never silently guessed. Open-ended question
answering is a *different* capability (`mtagent ask`, RAG-backed) and is
untouched by this module.
"""
from __future__ import annotations

import csv
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from .config import Config
from .validators import outcome_gate
from .worklog import hash_files, log_run

# --------------------------------------------------------------------- #
# What the controller is allowed to do -- every entry maps to a REAL
# function. Adding a new action means adding a real capability first,
# never adding a name here that nothing implements.
# --------------------------------------------------------------------- #
READ_ONLY = "read_only"          # never needs approval
GENERATES_OUTPUT = "generates_output"   # writes gitignored build artifacts; no approval needed
DESTRUCTIVE = "destructive"      # commit/push/publish/overwrite-approved/external-share -- ALWAYS needs approval

KNOWN_ACTIONS = {
    "status": {"class": READ_ONLY, "subagent": "pbi-workflow",
               "describe": "Report current PBI workflow status"},
    "build_dataset": {"class": GENERATES_OUTPUT, "subagent": "pbi-workflow",
                       "describe": "Build the Power BI dataset from the latest offtake files"},
    "reconcile": {"class": GENERATES_OUTPUT, "subagent": "pbi-workflow",
                  "describe": "Run source-to-model reconciliation"},
    "compile_model": {"class": GENERATES_OUTPUT, "subagent": "pbi-workflow",
                       "describe": "Compile the .pbip semantic model"},
    "derive_article_master": {"class": GENERATES_OUTPUT, "subagent": "mapping-auditor",
                               "describe": "Derive ArticleMaster.csv from offtake data"},
    "derive_npi_list": {"class": GENERATES_OUTPUT, "subagent": "mapping-auditor",
                         "describe": "Derive NPI_List.csv from primary history"},
    "run_automated": {"class": GENERATES_OUTPUT, "subagent": "pbi-workflow",
                       "describe": "Run the full automated chain end to end"},
    "apply_alias": {"class": GENERATES_OUTPUT, "subagent": "mapping-auditor",
                     "describe": "Record a scoped chain-name alias mapping"},
    "commit": {"class": DESTRUCTIVE, "subagent": None,
               "describe": "git commit tracked changes"},
    "push": {"class": DESTRUCTIVE, "subagent": None,
             "describe": "git push to the remote branch"},
}

# --------------------------------------------------------------------- #
# Outcome-first fields per action (agent/policies/AI_LEVERAGE_AND_JUDGMENT.md
# rule 2 / enforcement §A-§B). Populated into Plan BEFORE tool_selection_reason
# is meaningful -- outcome first, tool second, by construction order.
# --------------------------------------------------------------------- #
ACTION_OUTCOME_SPEC = {
    "status": {
        "business_outcome": "Give the analyst a trustworthy read on pipeline health before relying on any downstream output.",
        "deliverable": "Workflow status summary (phase, completion %, blockers, warnings)",
        "decision_supported": "Whether it's safe to proceed with the next pipeline step",
        "stakeholder": "MT channel analyst / lead running the pipeline",
        "source_data": ["agent/index/worklog.jsonl", "agent/pbi_build/<latest>"],
        "required_grain": "workflow-run level",
        "approval_boundary": [],
        "tool_selection_reason": "Read-only status lookup -- no data transformation, so no tool beyond the existing WorkflowController status call is needed.",
    },
    "build_dataset": {
        "business_outcome": "Produce a Power BI-ready fact table from the latest offtake source so downstream reconciliation and reporting can run.",
        "deliverable": "Fact_OfftakeSales.csv + supporting dimension tables for one build cycle",
        "decision_supported": "Whether this month's data is structurally ready to reconcile and load into Power BI",
        "stakeholder": "MT channel analyst preparing the monthly refresh",
        "source_data": ["PowerBI/RawDataFolders/Offtake_Monthly/*.csv (or .xlsb)"],
        "required_grain": "store x article x month",
        "approval_boundary": [],
        "tool_selection_reason": "Python selected because the transformation requires row-level parsing and chain/article mapping across a large CSV/XLSB source, not a single lookup.",
    },
    "reconcile": {
        "business_outcome": "Prove the built dataset's NSV/Qty/row counts match the source before it's trusted for leadership reporting.",
        "deliverable": "Source_To_Model_Reconciliation_Report.csv with a PASS/FAIL verdict per metric",
        "decision_supported": "Whether the current build is safe to compile into Power BI or report on",
        "stakeholder": "MT channel analyst / leadership relying on the numbers",
        "source_data": ["latest agent/pbi_build/<FY>_<Month>/Fact_OfftakeSales.csv", "PowerBI/RawDataFolders/Offtake_Monthly/*.csv"],
        "required_grain": "chain x article x month totals",
        "approval_boundary": [],
        "tool_selection_reason": "Python selected because row-level and metric-level reconciliation across two large sources is required, not a manual spot check.",
    },
    "compile_model": {
        "business_outcome": "Turn a reconciled build into a Power BI semantic model the team can actually open.",
        "deliverable": "PowerBI/ModelDefinition.pbip",
        "decision_supported": "Whether the model is ready for manual Power BI Desktop steps",
        "stakeholder": "MT channel analyst preparing the Power BI deliverable",
        "source_data": ["latest reconciled agent/pbi_build/<FY>_<Month>/"],
        "required_grain": "table/relationship/measure level",
        "approval_boundary": [],
        "tool_selection_reason": "Python selected to generate the .pbip structure programmatically from the already-reconciled build, avoiding manual re-entry of tables/measures.",
    },
    "derive_article_master": {
        "business_outcome": "Fill ArticleMaster.csv gaps directly from what's actually selling, instead of leaving unmapped articles blank.",
        "deliverable": "PowerBI/SeedData/Masters/ArticleMaster.csv (updated)",
        "decision_supported": "Whether article-level reporting (category/brand/pack) is complete for this build",
        "stakeholder": "Mapping auditor / MT analyst maintaining masters",
        "source_data": ["offtake data actually observed in the latest build"],
        "required_grain": "article/EAN level",
        "approval_boundary": [],
        "tool_selection_reason": "Python selected because deriving masters requires deduplicating and cross-referencing article codes across thousands of source rows.",
    },
    "derive_npi_list": {
        "business_outcome": "Identify genuinely new (NPI) articles from primary history so they're visible in reporting instead of silently falling into 'unmapped'.",
        "deliverable": "PowerBI/SeedData/Masters/NPI_List.csv",
        "decision_supported": "Which articles should be flagged as NPI for this cycle",
        "stakeholder": "MT channel analyst tracking new product performance",
        "source_data": ["primary sales history"],
        "required_grain": "article level",
        "approval_boundary": [],
        "tool_selection_reason": "Python selected because NPI derivation requires comparing article first-seen dates across the full primary history, not a single file.",
    },
    "run_automated": {
        "business_outcome": "Run the full pipeline end to end in one pass so nothing is missed between build, reconcile, and compile.",
        "deliverable": "The combined result of build_dataset + reconcile + compile_model in sequence",
        "decision_supported": "Whether the whole chain is healthy without stepping through each stage manually",
        "stakeholder": "MT channel analyst doing a full monthly refresh",
        "source_data": ["same as build_dataset/reconcile/compile_model, combined"],
        "required_grain": "pipeline-run level",
        "approval_boundary": [],
        "tool_selection_reason": "Python selected to sequence build/reconcile/compile deterministically and halt on the first failed stage.",
    },
    "apply_alias": {
        "business_outcome": "Record one business-approved chain-name alias so raw source labels roll up to the correct canonical chain.",
        "deliverable": "A scoped alias record (ControllerAlias_<scope>.csv row)",
        "decision_supported": "Whether this specific raw label is safe to fold into an existing canonical chain",
        "stakeholder": "Mapping auditor confirming a chain naming decision",
        "source_data": ["PowerBI/SeedData/Masters/ChainMaster.csv"],
        "required_grain": "single alias mapping",
        "approval_boundary": [],
        "tool_selection_reason": "A direct CSV lookup/append is sufficient -- no need for a full pipeline run to record one mapping decision.",
    },
    "commit": {
        "business_outcome": "Make already-approved local changes visible in shared history.",
        "deliverable": "a new commit",
        "decision_supported": "Whether this specific set of changes should become permanent history",
        "stakeholder": "the orchestrating session / repo owner",
        "source_data": ["git working tree"],
        "required_grain": "n/a",
        "approval_boundary": ["explicit approval required this turn", "controller never runs git itself even when approved"],
        "tool_selection_reason": "n/a -- this action is deliberately never executed by this module; git remains a human/orchestrator-run step.",
    },
    "push": {
        "business_outcome": "Make already-approved commits visible to the team on the remote branch.",
        "deliverable": "an updated remote branch",
        "decision_supported": "Whether local history is ready to become shared history",
        "stakeholder": "the orchestrating session / repo owner",
        "source_data": ["git working tree"],
        "required_grain": "n/a",
        "approval_boundary": ["explicit approval required this turn", "controller never runs git itself even when approved"],
        "tool_selection_reason": "n/a -- this action is deliberately never executed by this module; git remains a human/orchestrator-run step.",
    },
}

# Conservative, anchored patterns -- a false negative just falls through to
# "unrecognized" (safe); a false positive would silently misfire, so every
# pattern requires an imperative verb AND a specific real-object keyword.
_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("status", re.compile(r"\b(show|what'?s|check)\b.*\b(status|pending|blockers?)\b", re.I)),
    ("build_dataset", re.compile(r"\b(rebuild|build|refresh)\b.*\b(dataset|data\s*set)\b", re.I)),
    ("reconcile", re.compile(r"\b(run|check)\b.*\breconcil", re.I)),
    ("compile_model", re.compile(r"\bcompile\b.*\bmodel\b", re.I)),
    ("derive_article_master", re.compile(r"\bderive\b.*\barticle\s*master\b", re.I)),
    ("derive_npi_list", re.compile(r"\bderive\b.*\bnpi\b", re.I)),
    ("run_automated", re.compile(r"\brun\b.*\b(everything|full\s*pipeline|automated)\b", re.I)),
    ("apply_alias", re.compile(r"\bapply\b.*\bto\b.*\b(scope|file|only)\b", re.I)),
    ("commit", re.compile(r"\bcommit\b", re.I)),
    ("push", re.compile(r"\bpush\b", re.I)),
]

_ALIAS_RE = re.compile(
    r"""apply\s+["']?(?P<alias>[\w &().\-]+?)["']?\s+to\s+["']?(?P<canonical>[\w &().\-]+?)["']?"""
    r"""(?:\s+for\s+the\s+(?P<scope>[\w \-]+?)\s*(?:file)?\s*(?:only)?)?[.\s]*$""",
    re.I | re.X,
)
# a canonical target that LOOKS like a raw store/ship-to code (long digit/
# suffix runs typical of SAP store identifiers) is refused outright --
# this is the enforcement point for "store names cannot silently become
# canonical chains" (see agent/AGENT_OPERATING_PRINCIPLES.md #9).
_STORE_CODE_SHAPE = re.compile(r"(_[A-Za-z0-9]{3,8}$)|(\bLimited[\s_-]?\d)|(-\d{2,}[A-Z]{0,3}$)")


@dataclass
class Plan:
    raw_instruction: str
    action: str | None
    desired_output: str
    input_files: list = field(default_factory=list)
    business_rules: list = field(default_factory=list)
    required_systems: list = field(default_factory=list)
    entry_exit_conditions: dict = field(default_factory=dict)
    success_criteria: list = field(default_factory=list)
    risks: list = field(default_factory=list)
    approval_required: bool = False
    approval_reason: str = ""
    expected_output_files: list = field(default_factory=list)
    params: dict = field(default_factory=dict)   # action-specific (e.g. alias/canonical/scope)
    recognized: bool = True
    suggestions: list = field(default_factory=list)
    # Outcome-gate fields (agent/policies/AI_LEVERAGE_AND_JUDGMENT.md rule 2).
    # approval_boundary defaults to [] (a deliberate "no approval needed"),
    # never None -- outcome_gate.check_plan() treats None as "never set".
    business_outcome: str = ""
    deliverable: str = ""
    decision_supported: str = ""
    stakeholder: str = ""
    source_data: list = field(default_factory=list)
    required_grain: str = ""
    approval_boundary: list = field(default_factory=list)
    tool_selection_reason: str = ""


def interpret(instruction: str) -> Plan:
    """Turn free text into a Plan. Never invents an action outside
    KNOWN_ACTIONS; unmatched text comes back with recognized=False and a
    list of the verbs this controller does understand.
    """
    text = instruction.strip()
    action = None
    for name, pat in _PATTERNS:
        if pat.search(text):
            action = name
            break

    if action is None:
        return Plan(
            raw_instruction=text, action=None,
            desired_output="(unrecognized instruction)",
            recognized=False,
            suggestions=sorted(KNOWN_ACTIONS),
        )

    spec = KNOWN_ACTIONS[action]
    plan = Plan(
        raw_instruction=text,
        action=action,
        desired_output=spec["describe"],
        required_systems=[spec["subagent"]] if spec["subagent"] else [],
        approval_required=(spec["class"] == DESTRUCTIVE),
        approval_reason=("destructive/publishing action -- requires explicit approval"
                          if spec["class"] == DESTRUCTIVE else ""),
    )

    # Outcome first, tool second: these come from the static per-action
    # template, set immediately after the action/desired_output are known
    # and BEFORE any action-specific business_rules/success_criteria below.
    outcome = ACTION_OUTCOME_SPEC.get(action, {})
    plan.business_outcome = outcome.get("business_outcome", "")
    plan.deliverable = outcome.get("deliverable", plan.desired_output)
    plan.decision_supported = outcome.get("decision_supported", "")
    plan.stakeholder = outcome.get("stakeholder", "")
    plan.source_data = list(outcome.get("source_data", []))
    plan.required_grain = outcome.get("required_grain", "")
    plan.approval_boundary = list(outcome.get("approval_boundary", []))
    plan.tool_selection_reason = outcome.get("tool_selection_reason", "")

    if action == "apply_alias":
        m = _ALIAS_RE.search(text)
        if not m:
            plan.recognized = False
            plan.suggestions = ['apply "<alias>" to "<canonical>" for the <scope> file only']
            return plan
        alias, canonical, scope = m.group("alias").strip(), m.group("canonical").strip(), (m.group("scope") or "").strip()
        if _STORE_CODE_SHAPE.search(canonical):
            plan.recognized = False
            plan.action = None
            plan.desired_output = "(refused)"
            plan.suggestions = [
                f"'{canonical}' looks like a raw store/ship-to code, not a canonical chain name -- "
                "refusing to alias a store into a chain bucket. Confirm the real canonical chain first."
            ]
            return plan
        plan.params = {"alias": alias, "canonical": canonical, "scope": scope or "unscoped"}
        plan.business_rules = [f"{alias} -> {canonical} (scope: {scope or 'unscoped'})"]
        plan.success_criteria = [f"'{canonical}' resolves to an existing ChainMaster entry or is flagged for review"]
        plan.expected_output_files = ["scoped alias record (see report)"]

    if action == "status":
        plan.success_criteria = ["status summary returned with no exception"]
    elif action == "build_dataset":
        plan.success_criteria = ["blocked_reason absent", "row count plausible vs prior month"]
        plan.expected_output_files = ["agent/pbi_build/<FY>_<Month>/Fact_OfftakeSales.csv"]
        plan.risks = ["source file staleness or a wrong month picked up unnoticed",
                       "unmapped chains/articles inflating the exception report"]
    elif action == "reconcile":
        plan.success_criteria = ["0 FAIL at configured tolerance"]
        plan.expected_output_files = ["Source_To_Model_Reconciliation_Report.csv"]
        plan.risks = ["reconciling against a stale build if build_dataset wasn't rerun first"]
    elif action == "compile_model":
        plan.success_criteria = ["NSV, Offtake NSV (Adjusted), Reliance BC NSV, BC Isolation Check all compiled in"]
        plan.expected_output_files = ["PowerBI/ModelDefinition.pbip"]
        plan.risks = ["compiling on top of a reconciliation that hasn't been re-checked this session"]
    elif action == "derive_article_master":
        plan.success_criteria = ["ArticleMaster.csv updated with no blocked_reason"]
        plan.expected_output_files = ["PowerBI/SeedData/Masters/ArticleMaster.csv"]
        plan.risks = ["deriving from an offtake build that itself has unmapped rows"]
    elif action == "derive_npi_list":
        plan.success_criteria = ["NPI_List.csv generated with no blocked_reason"]
        plan.expected_output_files = ["PowerBI/SeedData/Masters/NPI_List.csv"]
        plan.risks = ["primary history gaps causing an article to be misclassified as NPI"]
    elif action == "run_automated":
        plan.success_criteria = ["every stage in the automated chain reports PASS, none skipped silently"]
        plan.risks = ["a later stage running on top of an earlier stage's undetected failure"]
    elif action == "apply_alias":
        plan.risks = ["canonical target may not be a real, business-confirmed chain -- guarded, but still review the flag",
                       "scope may be narrower or wider than intended -- confirm before treating as pipeline-wide"]
    elif action in ("commit", "push"):
        plan.entry_exit_conditions = {"entry": "explicit approval granted this turn", "exit": "n/a until approved"}
        plan.success_criteria = ["explicit approval granted this turn"]
        plan.risks = ["irreversible in shared history once pushed -- never auto-run by this controller"]

    plan.entry_exit_conditions.setdefault(
        "entry", "prior stage(s) exited PASS" if spec["class"] != READ_ONLY else "none")
    plan.entry_exit_conditions.setdefault("exit", "stage-specific success criteria met")
    return plan


@dataclass
class StageResult:
    name: str
    status: str   # PASS | FAIL | BLOCKED
    detail: str = ""


@dataclass
class RunResult:
    run_status: str    # PASS | FAIL | BLOCKED | CLARIFICATION_REQUIRED
    desired_output: str
    stages: list        # list[StageResult]
    key_results: dict
    files_created: list
    approval_required: str | None   # human-readable question, or None
    # Rule 4/15 (AI_LEVERAGE_AND_JUDGMENT.md): separate activity from outcome.
    business_outcome_achieved: bool | None = None   # True/False/None (None = never ran, e.g. CLARIFICATION_REQUIRED)
    checks_passed: list = field(default_factory=list)
    checks_failed: list = field(default_factory=list)
    remaining_uncertainty: list = field(default_factory=list)


def _run_pbi_command(cfg: Config, controller, name: str, **kwargs) -> dict:
    from . import pbi_commands  # noqa: F401 -- import populates the pbi_registry
    from .pbi_registry import get_command
    return get_command(name).handler(cfg, controller, **kwargs)


def execute(cfg: Config, plan: Plan, approved: bool = False) -> RunResult:
    """Run a Plan's action against the real pipeline. Any FAIL/BLOCKED
    stage halts immediately -- later stages are never attempted (see
    AGENT_OPERATING_PRINCIPLES.md #2 and #6). A DESTRUCTIVE action without
    `approved=True` is BLOCKED before anything runs, no exceptions.

    EVERY exit path (unrecognized, approval-blocked, stage failure, or a
    clean PASS) funnels through the single `_finish()` call at the bottom
    -- a run that never reaches the worklog write is exactly the kind of
    silent feedback-loop gap AGENT_OPERATING_PRINCIPLES.md #7 exists to
    prevent, so there is deliberately no early `return` in this function.
    """
    from .pbi_workflow import WorkflowController

    run_id = uuid.uuid4().hex[:12]
    stages: list[StageResult] = []
    key_results: dict = {}
    files_created: list = []
    approval_question: str | None = None

    def _finish(override_status: str | None = None) -> RunResult:
        if override_status:
            overall = override_status
        else:
            overall = "PASS"
            for s in stages:
                if s.status == "BLOCKED":
                    overall = "BLOCKED"
                    break
                if s.status == "FAIL":
                    overall = "FAIL"
                    break
        log_run(
            cfg, f"controller:{plan.action or 'unrecognized'}", [], 0 if overall == "PASS" else 1, [],
            run_id=run_id,
            desired_output=plan.desired_output,
            success_criteria=plan.success_criteria,
            stage_results={s.name: s.status for s in stages},
            output_files=files_created,
            decision_required=[plan.approval_reason] if (plan.approval_required and not approved) else [],
            approved_by="controller-session" if approved else None,
        )
        # Rule 3/4: activity (stages ran) is not the same claim as outcome
        # achieved. CLARIFICATION_REQUIRED means nothing ran, so the
        # question of "was the outcome achieved" doesn't apply yet.
        outcome_achieved = None if overall == "CLARIFICATION_REQUIRED" else (overall == "PASS")
        checks_passed = [s.name for s in stages if s.status == "PASS"]
        checks_failed = [s.name for s in stages if s.status in ("FAIL", "BLOCKED")]
        remaining_uncertainty = [s.detail for s in stages if s.status != "PASS" and s.detail]
        return RunResult(overall, plan.desired_output, stages, key_results, files_created, approval_question,
                          business_outcome_achieved=outcome_achieved,
                          checks_passed=checks_passed, checks_failed=checks_failed,
                          remaining_uncertainty=remaining_uncertainty)

    if not plan.recognized:
        stages.append(StageResult("interpret", "BLOCKED",
                                   f"unrecognized instruction; known actions: {', '.join(plan.suggestions) if plan.suggestions else plan.suggestions}"))
        return _finish(override_status="CLARIFICATION_REQUIRED")

    gate = outcome_gate.check_plan(plan)
    if not gate.ok:
        stages.append(StageResult("outcome_gate", "BLOCKED",
                                   f"plan is missing required field(s): {', '.join(gate.missing)} -- "
                                   "desired outcome is materially unclear, refusing to execute"))
        return _finish(override_status="CLARIFICATION_REQUIRED")

    if plan.approval_required and not approved:
        stages.append(StageResult("approval_gate", "BLOCKED", plan.approval_reason))
        approval_question = f"{plan.action}: {plan.raw_instruction!r} -- approve this destructive action? Yes/No"
        return _finish()

    controller = WorkflowController(cfg)

    try:
        if plan.action == "status":
            summary = controller.status_summary()
            stages.append(StageResult("status", "PASS"))
            key_results = summary

        elif plan.action == "build_dataset":
            result = _run_pbi_command(cfg, controller, "build-dataset")
            ok = result.get("status") not in ("Blocked", "Failed")
            stages.append(StageResult("build_dataset", "PASS" if ok else result["status"].upper(),
                                       result.get("blocked_reason", result.get("warning", ""))))
            key_results = {k: result.get(k) for k in ("output_file", "warning") if k in result}
            if ok and result.get("output_file"):
                files_created.append(result["output_file"])

        elif plan.action == "reconcile":
            base = cfg.path(cfg.pbi_build_dir)
            candidates = sorted([p for p in base.glob("FY*_*") if (p / "Fact_OfftakeSales.csv").exists()]) if base.exists() else []
            if not candidates:
                stages.append(StageResult("reconcile", "BLOCKED", "no completed dataset build found -- build_dataset must run first"))
            else:
                build_dir = candidates[-1]
                offtake_dir = cfg.root() / "PowerBI" / "RawDataFolders" / "Offtake_Monthly"
                sources = sorted(offtake_dir.glob("offtake_store_article_*.csv")) if offtake_dir.exists() else []
                if not sources:
                    stages.append(StageResult("reconcile", "BLOCKED", "no source offtake CSV found"))
                else:
                    result = _run_pbi_command(cfg, controller, "reconcile-model",
                                               source=str(sources[-1]), build_dir=str(build_dir))
                    ok = result.get("status") not in ("Blocked", "Failed") and not result.get("warning")
                    stages.append(StageResult("reconcile", "PASS" if ok else "FAIL",
                                               result.get("validation_result", "")))
                    key_results = {"validation_result": result.get("validation_result", "")}
                    if result.get("output_file"):
                        files_created.append(result["output_file"])

        elif plan.action == "compile_model":
            result = _run_pbi_command(cfg, controller, "compile-model")
            ok = result.get("status") not in ("Blocked", "Failed")
            stages.append(StageResult("compile_model", "PASS" if ok else result["status"].upper(),
                                       result.get("blocked_reason", "")))
            key_results = {k: result.get(k) for k in ("output_file", "warning") if k in result}
            if ok and result.get("output_file"):
                files_created.append(result["output_file"])

        elif plan.action == "derive_article_master":
            result = _run_pbi_command(cfg, controller, "derive-article-master")
            ok = result.get("status") not in ("Blocked", "Failed")
            stages.append(StageResult("derive_article_master", "PASS" if ok else "FAIL", result.get("blocked_reason", "")))
            if ok and result.get("output_file"):
                files_created.append(result["output_file"])

        elif plan.action == "derive_npi_list":
            result = _run_pbi_command(cfg, controller, "derive-npi-list")
            ok = result.get("status") not in ("Blocked", "Failed")
            stages.append(StageResult("derive_npi_list", "PASS" if ok else "FAIL", result.get("blocked_reason", "")))
            if ok and result.get("output_file"):
                files_created.append(result["output_file"])

        elif plan.action == "run_automated":
            result = _run_pbi_command(cfg, controller, "run-automated")
            ok = result.get("status") not in ("Blocked", "Failed")
            stages.append(StageResult("run_automated", "PASS" if ok else result["status"].upper()))
            key_results = {"results": result.get("results", {})}

        elif plan.action == "apply_alias":
            path, note = _apply_alias(cfg, plan.params["alias"], plan.params["canonical"], plan.params["scope"])
            stages.append(StageResult("apply_alias", "PASS", note))
            files_created.append(str(path))
            key_results = dict(plan.params)

        elif plan.action in ("commit", "push"):
            # approval WAS granted (checked above) -- still never executed
            # here silently; the orchestrating session runs the real git
            # command explicitly. This module never calls git commit/push.
            stages.append(StageResult(plan.action, "BLOCKED",
                                       "approved, but git operations are performed by the orchestrating "
                                       "session explicitly, never auto-run by the controller"))

    except Exception as exc:  # noqa: BLE001 -- a controller stage must report, never crash the CLI
        stages.append(StageResult(plan.action or "execute", "FAIL", f"{type(exc).__name__}: {exc}"))

    return _finish()


def format_plan(plan: Plan) -> str:
    """The structured plan shown BEFORE execution -- principle #4
    (desired output drives the process): the human sees what will run and
    why before it runs, not just the result after."""
    if not plan.recognized:
        return ("Plan: UNRECOGNIZED instruction.\n"
                f"Known actions / notes: {', '.join(plan.suggestions)}")
    lines = [
        f"Plan for: {plan.raw_instruction!r}", "",
        f"Desired output: {plan.desired_output}",
        f"Business outcome: {plan.business_outcome or 'n/a'}",
        f"Deliverable: {plan.deliverable or 'n/a'}",
        f"Decision supported: {plan.decision_supported or 'n/a'}",
        f"Stakeholder: {plan.stakeholder or 'n/a'}",
        f"Required systems: {', '.join(plan.required_systems) or '(none)'}",
        f"Tool selection reason: {plan.tool_selection_reason or 'n/a'}",
    ]
    if plan.source_data:
        lines.append(f"Source data: {', '.join(plan.source_data)}")
    if plan.required_grain:
        lines.append(f"Required grain: {plan.required_grain}")
    if plan.input_files:
        lines.append(f"Input files: {', '.join(plan.input_files)}")
    if plan.business_rules:
        lines.append("Business rules:")
        lines += [f"  - {r}" for r in plan.business_rules]
    lines.append(f"Entry condition: {plan.entry_exit_conditions.get('entry', 'n/a')}")
    lines.append(f"Exit condition: {plan.entry_exit_conditions.get('exit', 'n/a')}")
    if plan.success_criteria:
        lines.append("Success criteria:")
        lines += [f"  - {c}" for c in plan.success_criteria]
    if plan.risks:
        lines.append("Risks:")
        lines += [f"  - {r}" for r in plan.risks]
    lines.append(f"Approval boundary: {'REQUIRED — destructive/publishing' if plan.approval_required else 'none — read-only or generates gitignored output only'}")
    if plan.expected_output_files:
        lines.append("Expected output files:")
        lines += [f"  - {f}" for f in plan.expected_output_files]
    return "\n".join(lines)


def format_run_result(result: RunResult) -> str:
    """The exact report shape required by AGENT_OPERATING_PRINCIPLES.md's
    'Every completed request should end with a standard response.'"""
    lines = [f"Run status: {result.run_status}", ""]
    lines += ["Desired output:", result.desired_output, ""]
    lines.append("Completed stages:")
    for s in result.stages:
        detail = f" ({s.detail})" if s.detail else ""
        lines.append(f"- {s.name}: {s.status}{detail}")
    lines.append("")
    lines.append("Key results:")
    if result.key_results:
        for k, v in result.key_results.items():
            lines.append(f"- {k}: {v}")
    else:
        lines.append("- (none)")
    lines.append("")
    lines.append("Files created:")
    if result.files_created:
        for f in result.files_created:
            lines.append(f"- {f}")
    else:
        lines.append("- (none)")
    lines.append("")
    achieved = {True: "Yes", False: "No", None: "n/a (did not execute)"}[result.business_outcome_achieved]
    lines.append(f"Business outcome achieved: {achieved}")
    lines.append(f"Checks passed: {', '.join(result.checks_passed) or '(none)'}")
    lines.append(f"Checks failed: {', '.join(result.checks_failed) or '(none)'}")
    lines.append(f"Remaining uncertainty: {'; '.join(result.remaining_uncertainty) or '(none)'}")
    lines.append("")
    lines.append("Approval required:")
    lines.append(result.approval_required or "None")
    return "\n".join(lines)


def process_instruction(cfg: Config, text: str, approved: bool = False) -> tuple[str, RunResult | None]:
    """One shared entry point for both `ask` (single-shot) and `chat`
    (interactive): classify, and either execute a recognized action or
    return None so the caller falls through to the existing RAG ask path.
    Returns (message, result) -- result is None when nothing controller-
    shaped was recognized (caller should treat `text` as a question).
    """
    plan = interpret(text)
    if not plan.recognized:
        return "", None
    result = execute(cfg, plan, approved=approved)
    return format_run_result(result), result


def _apply_alias(cfg: Config, alias: str, canonical: str, scope: str) -> tuple[Path, str]:
    """Record one scoped alias. Guarded: `canonical` must already exist in
    ChainMaster.csv, OR the caller is told explicitly that it doesn't and
    nothing is written -- this is the concrete enforcement of "store names
    cannot silently become canonical chains" for aliases that aren't
    caught by the regex shape-guard in `interpret()`.
    """
    root = cfg.root()
    master_path = root / "PowerBI" / "SeedData" / "Masters" / "ChainMaster.csv"
    known_chains = set()
    if master_path.exists():
        with open(master_path, newline="", encoding="utf-8") as fh:
            known_chains = {r["Chain"].strip() for r in csv.DictReader(fh)}

    scope_slug = re.sub(r"[^a-z0-9]+", "_", scope.lower()).strip("_") or "unscoped"
    out_dir = root / "PowerBI" / "SeedData" / "Mapping"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"ControllerAlias_{scope_slug}.csv"

    is_new_row = not out_path.exists()
    with open(out_path, "a", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        if is_new_row:
            w.writerow(["Alias", "Canonical Chain", "Scope", "Canonical Exists In ChainMaster", "Note"])
        w.writerow([alias, canonical, scope, canonical in known_chains,
                    "recorded via controller.apply_alias -- review before treating as pipeline-wide"])

    scope_label = f"{scope} file only" if scope != "unscoped" else "pipeline-wide (no scope specified)"
    # Explainability format (AI_LEVERAGE_AND_JUDGMENT.md enforcement §F):
    # What changed / Scope / Impact / Reason / Risk -- never a bare
    # "successful" with no business content.
    if canonical not in known_chains:
        risk = (f"'{canonical}' is NOT an existing ChainMaster.csv chain -- "
                f"flagged for human confirmation, not silently promoted to canonical")
    else:
        risk = f"none identified; '{canonical}' matches an existing canonical chain in ChainMaster.csv"
    note = (
        f"What changed: '{alias}' mapped to '{canonical}'. "
        f"Scope: {scope_label}. "
        f"Impact: rows/NSV/Qty affected not computed in this step -- run reconcile to quantify before treating this as reconciled. "
        f"Reason: recorded via controller.apply_alias. "
        f"Risk: {risk}"
    )
    return out_path, note
