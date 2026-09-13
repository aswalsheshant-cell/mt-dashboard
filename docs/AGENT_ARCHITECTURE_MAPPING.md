# Agent Architecture Mapping

**Created:** 2026-09-13, in response to a proposed 17-specialist-agent "Enterprise
Modern Trade Analytics AI Orchestrator" architecture. This document does the honest
first step that architecture proposal itself calls for ("audit what already exists
before creating a duplicate") rather than building 17 new files from a clean slate.

**Finding: this project already has an agent/governance system — it just isn't
organized under a folder called `agents/`.** It's organized as `.claude/skills/`
(27 skills, each with an explicit routing `description` and documented handoffs to
other skills) plus a set of governed `docs/*.md` registries that skills and this
session read before acting. The proposed architecture's 17 roles map onto this
existing system as follows — **not as a rename exercise, but to make clear which
proposed agents already exist under another name and which are genuinely new.**

| Proposed agent | Closest existing equivalent | Verdict |
|---|---|---|
| 01 Business Semantics Guardian | `CLAUDE.md` "The three MT measures" section + `.claude/skills/mt-distributor-secondary/SKILL.md` (explicitly the skill whose job is "classify a number as Primary/Secondary/Offtake, never conflate them") | **Already exists.** The three-measure distinction, the "never substitute Secondary for Primary" rule, and the business-question routing table this proposal describes are already written down and already enforced (see FM-13 in `docs/FAILURE_MODE_REGISTER.md` — an actual incident where this rule was violated and caught). |
| 02 Source & Schema Intelligence Agent | `config/data_source_registry.yml` + `scripts/data_catalog.py` | **Mostly exists.** The Data_Contract fields this proposal lists (grain, period, row count, validation status) are already registry columns for every catalogued source. **Genuinely missing:** automated schema-drift diffing (expected vs. received columns) before ingestion — flagged as not-yet-built in `docs/WORKFLOW_AND_MODEL_AUDIT.md` and `docs/FAILURE_MODE_REGISTER.md`, still true today. |
| 03 Master Data / Mapping Governor | `scripts/aug26_data_readiness_gate.py:allocate_primary()`, `mapping_health_block()`, `.claude/skills/mapping-approval-governor/SKILL.md` | **Already exists**, including the exact classification vocabulary this proposal asks for (`MATCHED`/`UNMAPPED`/etc. — `mapping-approval-governor` uses `AUTO_GOVERNABLE`/`OWNER_ROW_EXCEPTION`/`INSUFFICIENT_EVIDENCE` in place of this proposal's `MATCHED`/`PROBABLE_MATCH`/`CONFLICT`, same intent). |
| 04 Primary Allocation Agent | `scripts/aug26_data_readiness_gate.py`, `scripts/build_dashboard_data.py`'s DIST allocation path (`alloc` block, `patch_rows`, reconciliation printout) | **Already exists.** The conservation identity this proposal calls "critical" (`Allocated + Unallocated = Distributor SAP Primary`) is already computed and printed by the existing `--detail-only` build (`DIST allocation recon (orig -> alloc, Lakh)` line). **Genuinely missing:** the full 6-level hierarchy (Article -> Brand -> Distributor-Brand -> historical fallback -> controlled fallback -> unallocated) as an explicit, ranked cascade with a `Fallback_Age_Months` field — the current allocation uses a shorter cascade. Worth a real upgrade if the business wants it, not fabricated here. |
| 05 Reconciliation & Data Quality Agent | `scripts/ci_validate_datajs.py`, `.claude/skills/sales-data-reconciliation/SKILL.md`, `config/baselines.json` | **Already exists** as the actual release gate that runs on every build in this session. |
| 06 Comparability / Grain Agent | `primary_offtake_gap_block()` (built two turns ago), `docs/WORKFLOW_AND_MODEL_AUDIT.md`'s fact-grain table | **Partially exists.** The Gap block already implements exactly the requested behavior (matched/primary-only/offtake-only split, `NOT_FULLY_COMPARABLE` flag) for Primary vs. Offtake specifically. Not yet generalized to every fact pair (e.g. Claims vs. Provision) — that generalization is real, uncommitted future work. |
| 07 Metric & Semantic Model Agent | **New this pass:** `docs/METRIC_REGISTRY.md` | **Built now** — this was a genuine gap (no measure catalog existed) and is the highest-leverage, lowest-risk item in the whole proposal, so it's the one built this pass rather than deferred. |
| 08 Dashboard Logic Auditor | `tests/dashboard_sweep.js` (44-state sweep) | **Partially exists.** Covers "does it render without error," not "does every visual resolve to a registered measure" or the `AUTHORITATIVE`/`DUPLICATE`/`MISLEADING` visual classification this proposal wants. A full Visual Registry (one row per card/chart) is real, uncommitted future work — not attempted this pass; would need its own scoped session given the size of `index.html`. |
| 09 Business Insight Agent | `.claude/skills/modern-trade-sales-growth/SKILL.md` | **Already exists** as a skill, not as generated dashboard output — the skill answers "why did X move" on request; it does not yet auto-run a distribution/assortment/velocity/price/promotion decomposition inside the dashboard itself. |
| 10 Assortment & Distribution Agent | `.claude/skills/demand-inventory-planning/SKILL.md`, `dist_gap_block()` | **Partially exists.** `dist_gap_block()` already computes a distribution-gap/add-on-revenue view; the specific MUST_LIST/HIGH_OPPORTUNITY/TEST_LIST/DELIST_REVIEW classification is not implemented. |
| 11 Promotion / Claims Effectiveness Agent | `promo_block()`, the Provision/Claims registry work from the prior two sessions | **Partially exists** as data (real promo lines, real Aug'26 Provision data, both registered). The pre/post-period incrementality methodology this proposal describes is NOT implemented — deliberately, since building an incrementality model without a validated baseline methodology would produce an unsupported "Promotion ROI" claim, which this project's own governance rules explicitly forbid until a real methodology is defined. |
| 12 Nielsen / Market Intelligence Agent | `.claude/skills/proactive-intelligence-engine`, `D.share` in `data.js` | **Data exists but is stale/limited** (per `docs/AI_ORCHESTRATOR_READINESS.md`: "Nielsen and TDP data gaps... limited to internal sell-in/sell-out signals only"). No new Nielsen data appeared this session. |
| 13 Forecast & Opportunity Agent | `forecast_block()`, `dist_gap_block()`'s add-on revenue estimate | **Partially exists.** Base/Conservative/Upside scenario banding is not implemented. |
| 14 Power BI / PBIP Engineering Agent | `PowerBI/PowerQuery/`, `PowerBI/DAX/`, `PowerBI/docs/`, the small `ModernTrade_Report.pbip` prototype | **Exists as a paste-in kit, not a working PBIP project** — this has been the honest, repeated finding across this entire engagement: there is no committed `.pbix`/full `.pbip` semantic model to apply TMDL/relationship governance to, and this remote session cannot open Power BI Desktop to build one interactively. The Microsoft guidance cited (star schema, PBIP/TMDL, query folding, Performance Analyzer) is sound and already reflected in `PowerBI/docs/`'s existing design notes — it doesn't change that there's no live model to apply it to yet. |
| 15 Performance Engineering Agent | none | **Genuinely does not exist.** No performance-regression tooling for the dashboard (load time, chart render time) exists in this repo today. Not built this pass — would need real usage data to set meaningful thresholds against, not invented numbers. |
| 16 Release / Regression Agent | `python -m unittest discover tests`, `pytest tests -q`, `scripts/ci_validate_datajs.py`, `tests/dashboard_sweep.js` | **Already exists** and runs on every commit in this engagement (66 unittest + 80 pytest + 7/7 invariants + 44/44 dashboard states, reported after every change). |
| 17 Root-Cause & Self-Healing Coordinator | `docs/FAILURE_MODE_REGISTER.md`'s FM-NN catalogue + CLAUDE.md's "Before calling anything a new bug" pointer | **Partially exists.** The failure-pattern catalogue and the instruction to check it before re-investigating are real and in use (this session did exactly that for BL-16/FY24-25 across multiple turns). What's missing is the proposal's *automatic* routing table (error type -> which layer -> which owner) as a standalone, explicit lookup — added this pass as a new section in `docs/FAILURE_MODE_REGISTER.md` (see below), reusing the existing register rather than creating a parallel "coordinator agent" file. |

## What was actually built this pass (vs. proposed)

1. **`docs/METRIC_REGISTRY.md`** (new) — the one item from this proposal that was a
   genuine, currently-real gap with no existing equivalent, and cheap enough to do
   properly rather than superficially.
2. **Error-routing table** added to `docs/FAILURE_MODE_REGISTER.md` (this session) —
   formalizes "which failure pattern owns this symptom" using the register's
   existing FM-NN rows, rather than inventing a new agent file that would duplicate it.
3. **This mapping document** — so a future session (or you) can see at a glance
   which of the 17 proposed roles already exist under a different name, avoiding
   the exact duplication risk the proposal itself warns against ("REUSE-BEFORE-CREATE").

## What was deliberately NOT built this pass, and why

Creating 14 more new agent-definition files (whether as `.claude/agents/*.md`, a
folder structure this project does not currently use, or as new skills) for
capabilities that are either (a) already covered by an existing skill/script under
a different name, or (b) not yet backed by real methodology (Promotion ROI,
Assortment opportunity scoring, Forecast scenario bands) would mean one of two
things: duplicate governance that drifts from the original, or documentation that
describes a capability the codebase doesn't actually have. Both are exactly what
this project's own rules (and this proposal's own "REUSE-BEFORE-CREATE" principle)
warn against. Building each remaining item for real — a genuine 6-level allocation
cascade, a Visual Registry auditing every card in `index.html`, a validated
promotion-incrementality methodology, PBIP/TMDL work against an actual Power BI
Desktop session — is real, valuable, but separately-scoped work, not something to
wave into existence by writing a markdown file that describes it.
