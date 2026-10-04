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

---

## Decision governance layer (added 2026-10-04)

**Status: baseline v2.** Built around one principle taken from the supplied governance
papers (read as PDFs; the LinkedIn posts themselves could not be opened): *the agent is
an untrusted part. Governance sits outside it and must hold even if the agent is wrong.*
The two other supplied papers (identity-system theory) gave no rule to apply to an MT
analytics agent, so nothing was built from them. The PDFs are marked proprietary and are
not copied into this repo.

The four roles above say *who* may do what. This layer makes the rules *enforced
outside the agent*, so an agent cannot decide its own permissions.

| Piece | File | What it does |
|---|---|---|
| Policy | `config/agent_decision_policy.yml` | Action classes → AUTO / AUTO_LOG / HUMAN_APPROVAL / FORBIDDEN; protected paths; `main_branch_protection_confirmed` flag |
| Evaluator | `scripts/agent_governance.py evaluate` | Returns ALLOWED / NEEDS_APPROVAL / BLOCKED with reasons. Unknown action = needs a human |
| Decision log | `governance/decision_log.jsonl` | Hash-chained, append-only. `record()` refuses anything not ALLOWED |
| Check | `scripts/agent_governance.py check` | Fails if a record is edited, deleted, or breaks the policy |
| Tests | `tests/test_agent_governance.py` | 21 tests |

Every record uses the five labels from `fmcg-decision-leader` (GO / GO WITH CONDITIONS /
HOLD / ESCALATE / REJECT) plus: actor, action_class, evidence, rule, owner,
validation_check, and approver where a human is required.

**Untrusted-agent controls (v2):** (1) only registered actors, each limited to its own
action classes; (2) an agent can never approve its own action; (3) approvers must be on
the `approvers` list, which is **empty until the MT Leadership / Finance owner supplies
names** (`INTERNAL_BUSINESS_CONFIRMATION_REQUIRED`), so human-approval actions stay
NEEDS_APPROVAL; (4) evidence must be a checkable `file`+sha256 or `commit` entry, and the
check re-verifies it against the repo, so a typed sentence or a changed file fails.

**Hard stops in the policy:** merge is BLOCKED until a human confirms branch protection
on `main`; releases/tags and overriding a failed control are FORBIDDEN; touching
`config/baselines.json`, `dashboard/data.js`, seed/master data or the policy file itself
always needs a named approver.

**Not done yet:** the check is not wired into CI (needs a workflow change with pinned
SHAs per CLAUDE.md) and nothing forces an agent to call `record()` — that needs a hook
or the agent's own instructions to be updated once the policy is agreed.

### Source register (for the reconciliation discussion)

Sources supplied for this governance layer. LinkedIn is blocked from the cloud session,
so posts marked UNREAD have not been compared with the policy yet. Tracking parameters
were removed from the links. Nothing from these sources is copied into the repo.

| # | Source | Status | Topic (from the link title only) |
|---|---|---|---|
| 1 | linkedin.com/posts/judiaevans_oslayerproblem-suif-trustworthyai-activity-7509669743130439680-8QBP | UNREAD | OS layer, SUIF, trustworthy AI |
| 2 | linkedin.com/posts/judiaevans_oslayerproblem-governancearchitecture-governedstate-activity-7511759942903603201-udNo | UNREAD | governance architecture, governed state |
| 3 | linkedin.com/posts/judiaevans_oslayerproblem-aigovernance-trustworthyai-activity-7508665592577523712-EgKv | UNREAD | AI governance |
| 4 | linkedin.com/posts/judiaevans_oslayerproblem-ai-governance-activity-7507967118382874625-2fWo | UNREAD | AI governance |
| 5 | linkedin.com/posts/judiaevans_aiinfrastructure-oslayerproblem-substrategovernance-activity-7507214883286016000-4AXE | UNREAD | AI infrastructure, substrate governance |
| 6 | linkedin.com/posts/judiaevans_ai-artificialintelligence-aigovernance-activity-7506248692706754560-Jq5N | UNREAD | AI governance |
| 7 | linkedin.com/posts/judiaevans_identitysecurity-decentralizedidentity-verifiablecredentials-activity-7504526399802675200-H1Vc | UNREAD | identity security, verifiable credentials |
| 8 | linkedin.com/posts/judiaevans_when-foundational-rules-are-missing-system-activity-7465366594563686400-ntmC | UNREAD | what happens when foundational rules are missing |
| 9 | PDF: Model-Centric Safety Cannot Fix OS-Layer Failures (Part 5) | READ, applied | governance outside the model; agent is untrusted |
| 10 | PDF: Axiom Sea | READ, nothing to apply | identity-system theory |
| 11 | PDF: The Lattice Layer | READ, nothing to apply | identity-system theory |

**Open for the later discussion:** approver names; branch-protection confirmation;
whether to add signed approvals (post 7); and what the policy should do when a rule is
missing (post 8). Today the answer is fail closed: an unknown action class or an unlisted
approver is never allowed.
