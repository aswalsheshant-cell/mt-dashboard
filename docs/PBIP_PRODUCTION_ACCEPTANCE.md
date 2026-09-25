# PBIP Production Acceptance Audit

**Created:** 2026-09-23, Phase 17.4 of "Production Acceptance & Certified Baseline
Lock." **Scope:** audit whether the certified Git state
(`e0d4ceb8e3fd067e6395e5833f7358d1f2369c68`) can be traced through
`Git → PBIP → DEV → TEST → PROD`. **No publish or deploy action was taken by this
audit** — read-only, per this phase's own rule.

## What exists in this repository (verified directly)

| Item | Found | Evidence |
|---|---|---|
| PBIP project file | Yes — `ModernTrade_Report.pbip` at repo root, referencing `ModernTrade_Report.Report/` | `cat ModernTrade_Report.pbip` |
| Report definition folder | Yes — `ModernTrade_Report.Report/` present alongside the `.pbip` | `find . -maxdepth 2 -iname "*.Report"` |
| Semantic model source (Power Query M, DAX) | Yes — `PowerBI/PowerQuery/`, `PowerBI/DAX/` | Directory listing |
| Deployment documentation | Yes, extensive — `PowerBI/docs/DEPLOYMENT_RUNBOOK.md`, `ServiceReadiness.md`, `RefreshGuide.md`, `PBIX_Build_Guide.md`, `POWERBI_TEAM_HANDOFF.md` | Directory listing |
| Rollback procedure | Yes, already documented | `DEPLOYMENT_RUNBOOK.md` §"Rollback Procedure" (republish previous `.pbix` from Desktop, or recover a committed `.pbit` template via `git checkout`) |
| Sign-off checklist | Yes, already documented | `DEPLOYMENT_RUNBOOK.md` §"Sign-Off Checklist" |
| Committed `.pbix` binary | **No** — and this is by design, not a gap: `CLAUDE.md` states plainly *"No `.pbix` is committed — it can only be produced inside Power BI Desktop."* | `CLAUDE.md` architecture map |

## What this audit could NOT verify (environment limitation, stated honestly)

This session runs in a Linux container with no Power BI Desktop, no Windows gateway
host, and no reachable Power BI Service tenant. Per `docs/METRIC_REGISTRY.md`'s own
already-documented finding: *"No `.pbix` exists in this repo and no Power BI Desktop
instance is reachable from this environment."* Every row below that depends on a live
workspace is therefore **BLOCKED: NO_LIVE_WORKSPACE_ACCESS**, not guessed at.

| Control | Status | Reason |
|---|---|---|
| Source control ownership | PASS | `ModernTrade_Report.pbip`/`.Report` are tracked in this same Git repo as the dashboard — one source of truth, not a parallel one (satisfies "PBIP/Git remains the source, don't let Desktop become another independent source of truth") |
| Semantic model lineage | PARTIAL | DAX/PQ *text* exists and is readable (`PowerBI/DAX/*.dax`, `PowerBI/PowerQuery/*.pq`); whether the assembled `.Report`/model in `ModernTrade_Report.Report/` currently matches that DAX/PQ text 1:1 was **not diffed in this pass** — a real, boundable follow-up, not claimed done |
| Report lineage | NOT_VERIFIABLE_FROM_THIS_SESSION | Would require opening the `.Report` folder's own definition files against the current DAX registry; not attempted this pass (time-boxed, out of Phase 17's core scope) |
| Environment-specific configuration (DEV/TEST/PROD parameters) | GAP | `DEPLOYMENT_RUNBOOK.md` line 32 itself says *"workspace name: TBD — verify with IT"* — no DEV/TEST/PROD workspace names are recorded anywhere in this repo today. There is no evidence a workspace of any kind has ever been created. |
| Deployment rules / pipeline | GAP | No Power BI deployment pipeline (the Service feature) is referenced anywhere in this repo's docs; promotion between workspaces is currently a **manual republish-from-Desktop** procedure (`DEPLOYMENT_RUNBOOK.md`), not an automated DEV→TEST→PROD pipeline |
| Refresh behavior | DOCUMENTED, NOT LIVE | `RefreshGuide.md`/`ServiceReadiness.md` fully specify the intended refresh mechanics (gateway, schedule, retries) but `ServiceReadiness.md`'s own status line reads *"SERVICE READY FOR CONFIGURATION (pending PBIX Desktop assembly and local validation)"* — i.e., **not yet configured, by the doc's own admission** |
| Credentials ownership | NOT_APPLICABLE_YET | No live gateway/credentials exist to own; `ServiceReadiness.md` correctly leaves the gateway owner/credentials fields as `*(confirm: ...)*` placeholders rather than a fabricated value — this audit does not fill them in either, consistent with "do not expose secrets" and "do not invent company policy" |
| Workspace permissions | NOT_APPLICABLE_YET | No workspace exists to have permissions |
| Production approval path | DOCUMENTED, NOT EXECUTED | `DEPLOYMENT_RUNBOOK.md`'s Sign-Off Checklist is a real, usable approval gate — but its own checklist items are unchecked in the source file (this is the template, not a completed record) |
| Post-deployment reconciliation | DESIGNED, NOT RUN | The checklist's "Baseline metrics verified (NSV FY25, Offtake FY26, etc.)" step is the right control — but the two example figures printed elsewhere in that same runbook (`Total NSV FY25 = ₹2,105 Cr`, `Offtake FY26 = ₹2,347 Cr`, around line 291) **do not match this repo's own current certified baselines** (`config/baselines.json`: Primary FY26 = ₹329.00 Cr, Offtake FY26 = ₹311.20 Cr) — flagged as a **new documentation-drift finding**, not fixed here (out of this phase's scope; the runbook needs its illustrative numbers refreshed before anyone uses it as a literal reconciliation target) |
| Rollback procedure | DOCUMENTED | See table above — real and usable, not fabricated for this audit |

## Findings summary

| Status | Count |
|---|---|
| PASS | 1 (source control ownership) |
| PARTIAL | 1 (semantic model lineage — text exists, not diffed against the assembled report) |
| DOCUMENTED, NOT LIVE/EXECUTED | 4 (refresh behavior, production approval path, post-deployment reconciliation, rollback) |
| GAP | 2 (no named DEV/TEST/PROD workspaces exist anywhere; no automated promotion pipeline) |
| NOT_APPLICABLE_YET | 2 (credentials, workspace permissions — nothing exists yet to have either) |
| NOT_VERIFIABLE_FROM_THIS_SESSION | 1 (report lineage diff) |

## New finding requiring attention

`DEPLOYMENT_RUNBOOK.md`'s own illustrative baseline figures (₹2,105 Cr / ₹2,347 Cr)
are stale relative to this repo's actual current certified baselines (₹329.00 Cr /
₹311.20 Cr — over 6x smaller). If a future operator followed that runbook literally
and compared a live Power BI refresh against those printed numbers, they would
(correctly) conclude something is catastrophically wrong, when in fact the runbook's
example values are simply out of date. **Recommend refreshing those two lines before
this runbook is ever used for a real deployment** — flagged, not fixed, per this
phase's "audit only" scope.

## Verdict for this sub-phase

**NOT YET PRODUCTION-ACCEPTED — by design, not by failure.** This repository has done
real, substantive PBIP-readiness work (a tracked `.pbip`, DAX/PQ text, a genuinely
useful deployment runbook with rollback and sign-off procedures already written) —
but zero of it has been executed against a live Power BI workspace, because no
workspace exists yet (`ServiceReadiness.md` says so itself). The correct next action
is a **human decision to stand up a real DEV workspace** and begin the promotion path
CLAUDE.md's architecture already anticipates (`PowerBI/` build kit → PBIP → DEV →
TEST → PROD), not an automated action this session can take unilaterally — publishing
or deploying without explicit authorization is expressly out of scope for this audit.
