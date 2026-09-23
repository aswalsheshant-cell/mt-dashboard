# AI Orchestrator Governance — Role Readiness Design

**Created:** 2026-09-23, Phase 17.6 of "Production Acceptance & Certified Baseline
Lock." **This is a governance design, not an implementation.** No agent code is
written by this document. It defines the permission boundary each future role must
respect, so that when implementation is authorized, it starts from a governed
contract rather than an improvised one.

## The one rule every role below must obey

**No AI agent — Business Logic, QC, Insight, or Release Manager — may create,
compute, or assert a new financial truth.** Every number any agent ever surfaces
must trace to a value already produced by `scripts/build_dashboard_data.py` and
present in `dashboard/data.js`, or to a value already registered in
`docs/METRIC_REGISTRY.md`/`config/baselines.json`. An agent that cannot find a
governed source for a number must say so (`BLOCKED` or
`INTERNAL_BUSINESS_CONFIRMATION_REQUIRED`, per this repo's own existing knowledge-base
convention in `docs/knowledge/INDEX.md`) — never estimate, interpolate, or invent one.
This is not a new rule invented for this document; it is this repository's existing
"No dummy data" rule (CLAUDE.md) and the knowledge base's own escalation convention,
applied to agent design specifically.

---

## Role 1 — Business Logic Agent

| Field | Definition |
|---|---|
| Purpose | Answer "what does this number mean" using already-governed definitions |
| READ permissions | `dashboard/data.js` (published aggregates only); `docs/METRIC_REGISTRY.md`; `docs/BUSINESS_LOGIC_REGISTRY.md`; `docs/DATA_AVAILABILITY_MATRIX.md`; `CLAUDE.md` |
| WRITE permissions | **None to any financial artifact.** May draft documentation text for human review only |
| FORBIDDEN actions | Computing a KPI independently instead of reading the registered one; answering a business-definition question for a measure not in `METRIC_REGISTRY.md` without flagging it as unregistered; asserting FY25 Primary/Offtake exist (a repeatedly-made historical error this repo's own docs, e.g. FM-07, exist specifically to prevent) |
| Authoritative sources | `docs/METRIC_REGISTRY.md` is the single source of truth for "what is the formula for X" |
| Required validation gates before answering | Must check `docs/METRIC_REGISTRY.md` first; if the measure isn't there, must say so rather than reconstruct a formula from code inspection alone |
| Human approval points | None required for read-only explanation; any request to add a NEW registered measure requires a human to add the `METRIC_REGISTRY.md` row (this agent may draft the row, never merge it) |
| Audit evidence | Every answer should cite the `Measure_ID` and its registry row |

## Role 2 — QC Agent

| Field | Definition |
|---|---|
| Purpose | Continuous integrity checking — the automatable half of what this session did manually across Phases 0–17 |
| READ permissions | `dashboard/data.js`; `config/baselines.json`; `docs/FAILURE_MODE_REGISTER.md`; all `scripts/ci_validate_*.py` and `scripts/validate_*.py` outputs |
| WRITE permissions | May write a **new row to `docs/FAILURE_MODE_REGISTER.md`** when it finds a genuinely new pattern (following this repo's own established additive-conflict-resolution convention, never overwriting an existing FM-NN row) — but only as a proposed diff for human review, never a direct commit to `main` |
| FORBIDDEN actions | "Fixing" a check by weakening it (exactly the trap this session avoided in Phase 16/17: the correct fix for the dead `metadata` dependency was a new canonical source, never lowering the bar); silently marking a BLOCKED item as PASS; running `--i-understand-this-is-mock-data` or any similar override flag on its own initiative |
| Required validation gates | Mapping completeness, duplicate detection, missing-as-zero scan, FY boundary checks, negative-value review, schema drift, Primary/Offtake reconciliation, store/article master checks — exactly the checks this session ran manually in Phases 13–15 |
| Human approval points | Any proposed change to `config/baselines.json` (changing a frozen/approved figure) always requires human sign-off — the file's own `_README` says so |
| Audit evidence | Every finding logged with the same evidence discipline this session used: file, line, exact number, exact discrepancy |

## Role 3 — Insight Agent

| Field | Definition |
|---|---|
| Purpose | "What changed, where, why, what's driving it" — narrative and diagnostic, not calculation |
| Gate | **May only run after QC Agent reports PASS for the relevant data.** An Insight Agent that explains a trend built on a BLOCKED or FAILED QC state is explaining noise as signal — this ordering is load-bearing, not optional |
| READ permissions | Same as Business Logic Agent, plus MoM/YoY comparison blocks (`same_period_block()` outputs) |
| WRITE permissions | None to any data artifact; may produce narrative text (QBR points, leadership summaries) for human review |
| FORBIDDEN actions | Explaining a BQ-07-style discrepancy (see `docs/GOLDEN_BUSINESS_QUESTIONS.md`) as if it were a real business trend rather than flagging the data-quality question first; presenting a directional/non-comparable figure (e.g. `PRIMARY_OFFTAKE_GAP`'s FY27 `NOT_FULLY_COMPARABLE` disclosure) as a precise number without carrying its own disclosure forward |
| Human approval points | Any insight destined for a leadership-facing document goes through the existing `executive-commercial-storytelling` skill's own number-validation handoff to `sales-data-reconciliation` — this agent does not bypass that chain |
| Audit evidence | Every insight traces to specific `data.js` fields and the QC Agent's PASS confirmation for them |

## Role 4 — Release Manager Agent

| Field | Definition |
|---|---|
| Purpose | The decision layer — "should this change progress" — never a computation layer |
| Output | Exactly one of `PASS`, `BLOCKED`, `REQUIRES_APPROVAL` — never a hedge like "looks fine" (per this phase's own explicit instruction) |
| READ permissions | QC Agent's full output; `docs/FAILURE_MODE_REGISTER.md`; CI check results (mirroring what this session did manually across every PR in this certification pass) |
| WRITE permissions | May merge a PR **only** when every required check is green AND no financial/security/governance control is failed — the exact discipline this session applied by hand throughout Phases F1–F2 and 8–14 (stop-and-report on the dead-`metadata` CI failure rather than merging around it is the canonical example of correct behavior for this role) |
| FORBIDDEN actions | **Silently overriding a failed financial, security, or governance control** (explicit, non-negotiable, stated verbatim from this phase's own instructions); force-merging; bypassing a required check; merging with an unresolved PR conversation; creating a git tag or GitHub Release (this repo's standing CLAUDE.md rule) |
| Human approval points | `REQUIRES_APPROVAL` is the correct output whenever a change touches: `config/baselines.json`, `dashboard/data.js`'s financial blocks, any file under `PowerBI/SeedData/Masters/`, or anything this session's own Phase 17.1 audit found NOT_VERIFIABLE_FROM_THIS_SESSION (i.e., until branch protection enforcement is confirmed by a human, this role should treat every merge as needing a human backstop, not fully autonomous) |
| Audit evidence | A merge log entry mirroring this session's own Phase 6/12 reports: PR number, head SHA, merge SHA, checks passed, financial impact stated as NONE or itemized |

---

## Orchestration flow (design only)

```
                MT ANALYTICS ORCHESTRATOR
                         |
        +----------------+----------------+
        |                |                |
        v                v                v
 Business Logic       QC Agent        Insight Agent
 Agent               (must PASS      (gated on QC
 (read-only           before Insight  PASS, per
 definitions)          runs)          above)
        |                |                |
        +--------+-------+----------------+
                 v
           Release Manager
           (PASS / BLOCKED /
            REQUIRES_APPROVAL)
                 |
                 v
           Human Approval
        (required whenever
         Release Manager
         returns anything
         but a clean PASS)
```

## Readiness assessment

| Readiness question | Answer |
|---|---|
| Is the underlying data trustworthy enough to build agents on top of? | **Yes, as of this certification** — `e0d4ceb` passed 17/17 gates, zero unexplained drift |
| Does a governed measure catalog exist for the Business Logic Agent to read? | Yes — `docs/METRIC_REGISTRY.md` |
| Does a QC baseline exist for the QC Agent to check against? | Yes — `config/baselines.json`, `scripts/ci_validate_datajs.py`, `scripts/validate_historical_baseline.py` |
| Does a privacy boundary exist for every role to respect? | Yes — KA-10, tested |
| Is `main` protected against a rogue or buggy agent merging something bad? | **Confirmed NO** (2026-09-23, repo owner checked directly — see `docs/MAIN_BRANCH_PROTECTION_AUDIT.md`). No branch protection rule or ruleset exists for `main` at all. This is now a **hard blocker, not an open question**: implementing the Release Manager Agent's merge authority today would mean the agent's own discipline is the *only* thing standing between it and a direct push, force-push, or deletion of `main` — there is no GitHub-enforced safety net behind it at all. |

## Verdict for this sub-phase

**DESIGN READY, IMPLEMENTATION BLOCKED.** The four-role contract above is sound and
buildable. The blocking precondition is no longer open — it is **confirmed**: `main`
has zero GitHub-enforced protection (`docs/MAIN_BRANCH_PROTECTION_AUDIT.md`,
2026-09-23). The Release Manager Agent role specifically must not be granted merge
authority until that gap is closed; the other three roles (read-only or
draft-output-only) are unaffected by this blocker and could proceed to
implementation design independent of it.
