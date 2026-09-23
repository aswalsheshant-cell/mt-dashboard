# Final Operational Acceptance Matrix

**Created:** 2026-09-23, Phase 17.7 — the rollup of Phases 17.1–17.6.
**Updated:** 2026-09-23, same day — row 5 re-updated: the repo owner created and
live-tested a ruleset on `main` (see `docs/MAIN_BRANCH_PROTECTION_AUDIT.md`); the
original "unprotected" finding no longer holds.
**Certified baseline:** `e0d4ceb8e3fd067e6395e5833f7358d1f2369c68`.

| Row | Control | Evidence | Owner | Status | Blocking? | Next action |
|---|---|---|---|---|---|---|
| 1 | Repository integrity (17-pt gate) | This session's Phase 13 certification: 17/17 PASS, 224 pytest passed / 1 skipped / 0 failed | MT Analytics | **PASS** | No | None — maintain via post-merge gate once built |
| 2 | CI validation coverage | All 6 PR-triggered workflows green on final head; `pytest tests/`+`answer_governance/` have no CI trigger (found in Phase 17.1) | MT Analytics | **GAP** | No (not blocking the current certification) | Add a `pull_request` trigger for both pytest suites |
| 3 | Financial reconciliation | Phase 14: `data.js` diff vs. prior certified state = 66 lines, both fully explained (metadata removal, one harmless key-order swap) | MT Analytics | **PASS** | No | None |
| 4 | Historical baselines (FY25/FY26) | `scripts/validate_historical_baseline.py` — canonical, live, tested (12/12), merged as PR #181 | MT Analytics | **PASS** | No | None |
| 5 | Main branch protection (GitHub-enforced) | `docs/MAIN_BRANCH_PROTECTION_AUDIT.md` — ruleset `Protect main - MT Dashboard Production` (Active) now exists and was live-tested via 3 real merge-attempt PRs (#183/#184, #185, #186/#187), not just configured in the UI. 9 required checks in place. Testing found 2 genuine gaps (path-filtered checks don't cover PRs outside their paths; a merge within ~1s of PR creation can race ahead of check registration), both accepted as documented limitations rather than further engineered around (repo owner decision, 2026-09-23) — not reproduced by normal human GitHub-UI use. CODEOWNERS is deferred/N/A by deliberate decision, not a gap: with one collaborator it would only name that same person, so "code owner approval" would be self-approval with no real control | **Human with repo admin access** | **RESOLVED, WITH 2 ACCEPTED LIMITATIONS** | No — main is no longer unprotected; the 2 accepted limitations are narrow and specific, not "no protection" | None required unless a real incident traces back to one of the 2 accepted limitations; CODEOWNERS revisit only if a second collaborator joins |
| 6 | Post-merge certification | `docs/POST_MERGE_CERTIFICATION_DESIGN.md` — designed, not implemented; one open design question (drift-comparison baseline storage) | MT Analytics / repo owner | **DESIGNED, NOT BUILT** | No | Human picks option 1/2/3 for the drift-comparison baseline, then implementation PR |
| 7 | PBIP source control | `ModernTrade_Report.pbip` + `.Report/` tracked in this same Git repo, one source of truth | MT Analytics | **PASS** | No | None |
| 8 | Power BI live deployment (DEV→TEST→PROD) | `docs/PBIP_PRODUCTION_ACCEPTANCE.md` — no workspace exists yet, `ServiceReadiness.md` says so itself | MT Analytics / IT | **NOT_APPLICABLE_YET** | No (deployment was never in scope for this session) | Human decision to stand up a DEV workspace |
| 9 | Business acceptance (Golden Business Questions) | `docs/GOLDEN_BUSINESS_QUESTIONS.md` — 9/15 PASS at the published-data layer, 1 genuine new discrepancy found (BQ-07 by_zone field divergence), 4 not-yet-evaluated, 1 source-unavailable (Nielsen) | MT Analytics | **PARTIAL** | **Yes, for BQ-07 specifically** — a real data-quality question, not yet root-caused | Investigate `offtake.by_zone.fy26` vs `.value` divergence before treating zone-level Offtake as certified |
| 10 | Security / data classification | `docs/DATA_SECURITY_CLASSIFICATION.md` — extends already-enforced KA-10 (privacy test passing); retention policy and named Security Owner genuinely undefined | Security Owner (unnamed) | **PARTIAL** | No (the one enforced rule — no employee data published — holds) | Human names a Security Owner and a retention policy |
| 11 | AI orchestrator governance | `docs/AI_ORCHESTRATOR_GOVERNANCE.md` — 4 roles designed, gated on row 5 (branch protection) before granting any agent merge authority | MT Analytics / repo owner | **DESIGN READY, NOT IMPLEMENTED** | No | Implement only after row 5 is resolved |
| 12 | Production monitoring | No monitoring/alerting configuration for the live GitHub Pages dashboard was found anywhere in this repo (not investigated as a dedicated sub-phase; noted here as a genuine, unscored gap since Phase 17 didn't explicitly assign it a sub-phase) | Unassigned | **NOT_YET_EVALUATED** | No | Scope as a follow-up if leadership wants uptime/error monitoring on the published dashboard |
| 13 | Rollback / recovery procedure | Git-level rollback is implicit (revert a merge commit); Power BI-level rollback is documented in `DEPLOYMENT_RUNBOOK.md` (republish previous `.pbix`, or `git checkout` a committed `.pbit`) though never exercised against a live workspace | MT Analytics | **DOCUMENTED, NOT EXERCISED** | No | None required until a live Power BI deployment exists to actually roll back |

## Verdict rollup

| Status | Count |
|---|---|
| PASS | 4 (rows 1, 3, 4, 7) |
| RESOLVED, WITH ACCEPTED LIMITATIONS | 1 (row 5 — ruleset live and tested; 2 narrow gaps accepted, not P0 any more) |
| PARTIAL | 2 (rows 9, 10) |
| GAP | 1 (row 2) |
| DESIGNED/DOCUMENTED, NOT IMPLEMENTED | 4 (rows 6, 8, 11, 13) |
| NOT_YET_EVALUATED | 1 (row 12) |

No row is UNKNOWN without a stated reason.
