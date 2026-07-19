# AI Leverage and Judgment Rules

**Status: enforceable, not aspirational.** These rules exist as actual code
in `agent/mtagent/controller.py` and `agent/mtagent/validators/`, not only
as prompt text. See "Enforcement logic" below for the exact gate each rule
maps to, and `agent/tests/test_outcome_gate.py` /
`test_business_validation.py` / `test_materiality.py` /
`test_final_summary.py` for the behavioral proof.

This document sits alongside `agent/AGENT_OPERATING_PRINCIPLES.md` (the 10
systems-thinking principles) — that document covers *how a system should be
built*; this one covers *when an agent is allowed to call its own work
done*. Both are referenced, not duplicated, from `.claude/agents/pbi-workflow.md`
and `.claude/agents/mapping-auditor.md`.

## 1. Exact instruction changes

Every subagent and the controller operate under these rules:

1. Every task must begin with a clearly stated business outcome.
2. The agent must identify: desired deliverable, business decision
   supported, intended user/stakeholder, success criteria, source data,
   required reporting grain, approval boundary.
3. The agent must not treat completed activity as achieved progress.
4. The agent must distinguish between: work completed, business outcome
   achieved, unresolved risk, human decision required.
5. A technically successful script cannot be marked `PASS` unless business
   validation also passes.
6. Business validation must include, where relevant: row-count
   reconciliation, NSV reconciliation, Qty reconciliation, distinct-value
   checks, mapping validation, period completeness checks, reasonableness
   checks, business-rule checks.
7. A polished dashboard, report, presentation, or file must be rejected if
   the underlying logic is not validated.
8. The agent must explain all material assumptions, mappings, exceptions,
   and decision logic in clear business language.
9. Approved business rules and domain knowledge take priority over generic
   AI assumptions.
10. The agent must select tools only after the business objective is
    defined.
11. The agent must not create outputs merely because they are technically
    possible.
12. When multiple outputs or approaches are possible, the agent must select
    based on: accuracy, materiality, business relevance, decision
    usefulness, traceability.
13. If the desired outcome is materially unclear, the agent must return
    `CLARIFICATION_REQUIRED` and must not begin execution.
14. If a critical validation fails, the agent must return `BLOCKED` and
    stop downstream execution.
15. Every final response must clearly state: business result achieved,
    checks passed, checks failed, remaining uncertainty, human approval
    required, files created or changed.

**Strong operating rule:** do not build more simply because AI makes
building easier. Build only what creates a verified business result.

## 2. Enforcement logic

### A. Pre-execution outcome gate
`agent/mtagent/validators/outcome_gate.py` — `check_plan()`/`check_plan_fields()`.
A plan is rejected before execution if it is missing `business_outcome`,
`deliverable`, `success_criteria`, `source_data`, or `approval_boundary`.
Wired into `controller.execute()`: an unrecognized or field-incomplete plan
returns `run_status = CLARIFICATION_REQUIRED` and never reaches a pipeline
call.

### B. Tool-selection gate
`controller.Plan.tool_selection_reason` is populated per action in
`interpret()`, always *after* `business_outcome`/`deliverable` are set in
the same function — outcome first, tool second, by construction order, not
convention.

### C. Validation gate
`agent/mtagent/validators/business_validation.py` — `CheckResult`/`evaluate()`.
A run is `PASS` only when technical execution and business validation both
pass; a clean exit code with a failed reconciliation is `BLOCKED`, never
`PASS`.

### D. Output-quality gate
Before a build/reconcile/compile result is reported as usable, its answer
to: totals reconciled? mappings approved? period complete? material
exceptions visible? decision-useful? is carried in `RunResult.checks_failed`
/ `remaining_uncertainty` — if any critical check is missing or failing,
`business_outcome_achieved` is `False`, never silently `True`.

### E. Materiality filter
`agent/mtagent/validators/materiality.py` — `rank_movements()`. Default
thresholds: flag movements at or above **±10%** or **₹10L absolute impact**
(configurable per call), capped to the top N by absolute impact. Not every
movement is reported — only material ones.

### F. Explainability gate
`controller._apply_alias()`'s stage detail (and any future business-facing
action) follows: **What changed / Scope / Impact / Reason / Risk** — never
a bare "successful" with no business content.

## 3. Behavioral tests (spec reference)

See the test files for the actual assertions; this table is a pointer, not
a substitute for reading them.

| # | Scenario | Expected | Test |
|---|---|---|---|
| 1 | Vague instruction ("build the dashboard") | `CLARIFICATION_REQUIRED`, no execution | `test_final_summary.py::TestVagueRequestNeverExecutes` |
| 2 | Activity completed but NSV fails to reconcile | business validation `FAIL` | `test_business_validation.py::TestActivityCannotEqualSuccess` |
| 3 | Exit code 0 but distinct chain count 45→130 | `FAIL`, chain-explosion named | `test_business_validation.py::TestDistinctValueExplosion` |
| 4 | Polished output, partial June shown as closed | `FAIL`, period-completeness named | `test_business_validation.py::TestPeriodCompleteness` |
| 5 | Tool selected only after outcome defined | `business_outcome` set before `tool_selection_reason` is meaningful; no PowerPoint before analysis output | `test_final_summary.py::TestToolFollowsOutcome` |
| 6 | Mapping instruction | explainability format present | `test_final_summary.py::TestMappingExplainability` |
| 7 | "Generate leadership insights" | only material movements returned, capped, sorted | `test_materiality.py` |
| 8 | Final response structure | work completed / outcome achieved / validation status / uncertainty / decision required all present | `test_final_summary.py::TestFinalResponseSeparatesWorkFromOutcome` |

## 4. Honest scope note

`materiality.py` is implemented and independently tested against synthetic
MT-shaped movement data (Test 7), but is **not yet wired into a live
controller action** — there is no real "generate leadership insights"
pipeline function in `pbi_dataset.py`/`pbi_compile.py` for it to sit on top
of. Per rule 11 above ("the agent must not create outputs merely because
they are technically possible"), a fake `generate_insights` action was
deliberately **not** added to `KNOWN_ACTIONS` just to give this module a
caller — that would be exactly the kind of unverified capability this
document exists to prevent. When a real insights pipeline exists, wiring
`rank_movements()` into it is a small follow-up, not a redesign.
