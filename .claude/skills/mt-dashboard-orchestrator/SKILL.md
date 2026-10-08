---
name: mt-dashboard-orchestrator
description: Use when an MT Dashboard request spans two or more domains, the symptom's owning layer is unclear, or the user asks for a full-project audit, completion plan, next move, root-cause plan or permanent resolution. Routes the work to the smallest existing project skill set and orders the handoffs. Excludes doing specialist validation or implementation itself; hands off to `dashboard-qa-sentinel`, `sales-data-reconciliation`, `mapping-approval-governor`, `change-verification`, `pr-deep-review`, `business-ai-automation`, `data-freshness-coverage`, `source-lineage-reproducibility` or `session-handoff-recovery` based on evidence.
---

# Role and mandate

Operate as the **routing controller for cross-domain MT Dashboard work**.

The dashboard has multiple truth layers: source files, transformations, governed mappings,
`dashboard/data.js`, browser rendering, Power BI assets, GitHub PR/CI state, and human
business approvals. A visible symptom is not evidence of which layer is broken.

Your job is to identify the owning layer before any fix is proposed and then invoke the
smallest specialist workflow that can prove or resolve it.

# Scope and boundaries

## In scope

- Full-project audits and completion planning
- Requests containing several symptoms at once, for example DOI wrong + Market Share blank + FY coverage mismatch
- Ambiguous defects where it is not yet known whether the problem is UI, data, mapping, finance governance, CI, Power BI or source availability
- Sequencing several specialist skills so evidence from one becomes the input to the next
- Separating executable engineering work from human-decision blockers
- Producing one consolidated status after specialist checks are complete

## Required handoffs

Route by the **earliest wrong layer**, not by the screen where the symptom appears:

- Browser/UI/runtime symptom after a dashboard change -> `dashboard-qa-sentinel`
- Wrong number, reconciliation, missing-vs-zero, grain, duplicate or financial truth question -> `sales-data-reconciliation`
- Provisional/approved distributor mapping or owner register -> `mapping-approval-governor`
- Latest month, FY coverage, missing month, stale domain, Market Share/TDP availability -> `data-freshness-coverage`
- Source provenance, hashes, rebuildability, generated-artifact lineage -> `source-lineage-reproducibility`
- PR readiness or historical PR relevance -> `pr-deep-review`
- Claim that something is fixed/green/ready, or root-cause proof -> `change-verification`
- Script, Python, JavaScript, Power Query, DAX or automation implementation -> `business-ai-automation`
- Session/model switch, context compaction, resumed work with uncertain current state -> `session-handoff-recovery`
- Incoming review comment/CI event where the action itself needs triage -> `steward`

# Execution workflow

1. **Re-establish repository truth.** Read CLAUDE.md first. Record current branch, HEAD,
   working-tree state and current `main`. Never plan from an old chat summary alone.
2. **Inventory symptoms without assuming causes.** For each symptom capture: visible
   behaviour, affected tab/KPI, FY/month, whether it is numeric or rendering-only, and
   the last known good state if available.
3. **Classify each symptom into one owner layer:**
   - source availability/freshness
   - source classification/grain
   - transformation/pipeline
   - mapping/allocation/business rule
   - generated data contract (`data.js`)
   - UI/runtime
   - Power BI Desktop evidence
   - PR/CI/infrastructure
   - human approval/governance
4. **Check governed project references before creating work.** At minimum consult the
   relevant sections of CLAUDE.md, `docs/FAILURE_MODE_REGISTER.md`,
   `docs/DATA_AVAILABILITY_MATRIX.md`, `config/data_source_registry.yml`, and the open
   PR/issue state when the task touches them.
5. **Route to the fewest specialist skills needed.** Do not run five generic audits when
   one specialist can prove the root cause.
6. **Order dependencies.** Typical order is availability -> reconciliation -> root-cause
   verification -> implementation -> QA -> PR review. Human approval gates stay explicit
   and cannot be replaced by technical checks.
7. **Return one consolidated control table** with: symptom, owning layer, evidence,
   specialist used, status, blocker owner, next executable action.

# Guardrails

- Never fix a screen before establishing whether its source domain actually contains the
  requested period. A blank Market Share panel may be a Nielsen input gap, not a JS bug.
- Never describe a technical PASS as Finance/business approval.
- Never manufacture data to make coverage continuous. Missing data remains missing and is
  labelled with the exact source dependency.
- Never hand-edit `dashboard/data.js`; it is generated.
- Never change governed mappings, baselines, thresholds, frozen evidence or financial
  treatment merely because a test would then pass.
- Never merge or push to `main` as part of orchestration. Follow the repository's explicit
  approval rules.
- Do not duplicate another skill's specialist procedure inside this skill. Routing is the
  value of this skill; evidence remains owned by the specialist.
- A plan is not complete while any root cause is still `UNKNOWN`. Unknowns must be converted
  to a bounded investigation or an explicit `BLOCKED_INPUT`, `BLOCKED_ENVIRONMENT` or
  `BLOCKED_HUMAN_DECISION` state.

# Output contract

Use only the sections needed for the request:

1. **Current project truth** — branch/HEAD and the scope checked
2. **Issue routing matrix** — symptom -> owning layer -> specialist -> evidence/status
3. **Execution sequence** — numbered next actions in dependency order
4. **Human decisions** — decisions that cannot be automated, with owner and exact ask
5. **Completion definition** — the evidence required before the project can move to the next stage

Lead with the current blockers and next executable action, not with generic advice.
