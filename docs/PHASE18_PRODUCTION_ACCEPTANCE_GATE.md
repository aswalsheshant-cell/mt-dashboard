# Phase 18 — Production Acceptance Gate

**Created:** 2026-09-23, direct follow-on to Phase 17
(`docs/MAIN_BRANCH_PROTECTION_AUDIT.md`, closed same day). **Updated same day —
STATUS: COMPLETE.** `Production Acceptance Gate` was added to the ruleset's
required-checks list and behaviorally verified via a real fail→blocked / fix→clean
test on PR #189 (full evidence in `docs/MAIN_BRANCH_PROTECTION_AUDIT.md`'s "Phase
18" section). That test also found and fixed a real defect: 4 of the ruleset's
then-10 required checks were path-filtered and never triggered for PR #189,
producing a permanent false block (`mergeable_state: "blocked"` even with
`Production Acceptance Gate` green). All 4 were duplicative of jobs already inside
`Production Acceptance Gate` and were removed from the required-checks list — down
to 6 essential required checks total.

## Why this exists

Phase 17 closed with `main` protected by a live, tested ruleset — but two of
the accepted realities from that work were:

1. The 9 required checks today are spread across 3 separate workflows
   (`validate-promo-data.yml`, `validate.yml`, `codeql.yml`,
   `dashboard-health-check.yml`), some path-filtered, one a 2-way matrix
   (`Analyze (python)` / `Analyze (javascript-typescript)`). Each has its own
   name and trigger shape, so extending or auditing "what's actually
   required" means reading four YAML files.
2. `pytest tests/` (165 tests, 1 intentionally skipped) and
   `pytest answer_governance/` (60 tests) — the two suites this session's own
   17-point certification leaned on most heavily — have **no CI trigger at
   all**. They only ever ran manually in this session's own shell.

Per GitHub's own documented behavior, a required check whose workflow never
triggers for a given PR (path filter, wrong branch, etc.) does not block that
PR's merge — it just never appears. A single, always-triggering workflow with
one stable final job name is easier to reason about and to keep the ruleset's
required-checks list in sync with than adding more individually-named,
possibly-path-filtered checks one at a time.

## What was built

`.github/workflows/production-acceptance-gate.yml` — triggers on every
`pull_request` to `main`, **no path filter**. Runs 8 jobs in parallel, each
wrapping one existing, already-proven script or suite (nothing new was
written to validate correctness — this wires up what already existed):

| Job | What it runs | Blocking? |
|---|---|---|
| Gate: Python Full Test Suite | `pytest tests/` | Yes |
| Gate: Answer Governance Suite | `pytest answer_governance/` | Yes |
| Gate: Historical Baseline Integrity | `scripts/validate_historical_baseline.py` | Yes |
| Gate: Schema/Data Validation | `scripts/validate_promo_schema.py --datajs dashboard/data.js` | Yes |
| Gate: Dashboard Integrity | HTML brace/critical-function/`window.DASH` checks (mirrors `validate-promo-data.yml`) | Yes |
| Gate: Release Validation | `scripts/ci_validate_datajs.py` | Yes |
| Gate: Reconciliation (informational) | `scripts/mt_channel_reconciliation.py dashboard/data.js` | **No — see below** |
| Gate: Browser Regression | Playwright `tests/e2e_v1.1.0_consolidation.spec.js` (mirrors `ui-smoke.yml`) | Yes |

A final `gate` job (`if: always()`, `needs:` all 8) aggregates the 7 blocking
results into one job named **`Production Acceptance Gate`** — that single
name is the only thing a future ruleset change would need to add.

All action references use the same 40-character commit SHAs already pinned
elsewhere in this repo's workflows (CLAUDE.md's CI governance rule) — reused,
not re-picked. YAML parses; the repo's own SHA-pin lint (from `validate.yml`)
passes against this file.

## The one deliberate exception: reconciliation is informational, not blocking

`scripts/mt_channel_reconciliation.py dashboard/data.js` was tested directly
against the branch's current, already-committed `dashboard/data.js` before
being wired in. **It exits 2 (BLOCKED) today** — a real, already-known,
unresolved business finding: eB2B/SIS non-MT primary (~Rs 11.64 Cr) sitting
inside MT zone sales, and Nykaa (FSN, a B2C marketplace account that also
carries eB2B billing) presented as an MT zone account. This is not something
any given PR introduces — it is the current state of `main` itself, and the
script's own docstring says a business owner still needs to decide how to
treat the Nykaa (FSN) case.

Wiring this in as a blocking check today would make the gate fail
permanently, on every PR, regardless of what the PR actually changes — the
opposite of what a production gate is for. It runs on every PR
(`continue-on-error: true`) so the finding stays visible, but its result is
excluded from the final gate's pass/fail condition. Once the eB2B/SIS
zone-contamination question is resolved and this script reports clean
against `main`, flip `continue-on-error` off and add its result to the gate
job's failure condition.

## Scope change worth naming: Browser Regression now runs on every PR

`ui-smoke.yml`'s Playwright suite is currently path-filtered to
`dashboard/index.html`, `dashboard/data.js`, the spec file, and
`playwright.config.js` — it only runs when those files change. This gate
reuses the same suite but with no path filter, so it now runs on **every**
PR to `main`, including documentation-only PRs like the one that closed
Phase 17. That's a deliberate part of "one gate covers every PR" — it adds
roughly 1–2 minutes of CI time (Chromium download + suite run) to every PR,
which was accepted as the cost of closing the path-filter gap Phase 17 found.

## What this does NOT do

- It does not touch the internal logic of `validate-promo-data.yml`,
  `validate.yml`, `codeql.yml`, or `dashboard-health-check.yml`. It does,
  however, **remove 4 of those workflows' checks from the required-checks
  list** (`Schema Validation`, `Historical Baseline Integrity`,
  `Dashboard Integrity Check`, `CI Results Summary`) — found duplicative and
  a real false-block risk during the enforcement proof; see
  `docs/MAIN_BRANCH_PROTECTION_AUDIT.md`'s "Phase 18" section. The workflows
  themselves still run as before, just aren't required any more.
- It does not change any business logic, financial value, or dashboard code.
- The reconciliation job's business question (eB2B/SIS zone contamination,
  Nykaa FSN treatment) is still unresolved — see below, not a Phase 18
  blocker.

## Completion criteria

- [x] Workflow runs and all 7 blocking jobs pass on a real PR (PR #188, then
      re-confirmed on PR #189).
- [x] `Production Acceptance Gate` added to the ruleset's required-checks
      list, behaviorally verified via a real fail→blocked / fix→clean test
      (PR #189) — not assumed from the UI. Found and fixed a real defect
      (4 duplicative, path-filtered required checks) along the way.
- [ ] Reconciliation job's business question (eB2B/SIS zone contamination,
      Nykaa FSN treatment) resolved, `continue-on-error` removed, and its
      result folded into the gate's failure condition. **Not a Phase 18
      blocker** — this is a separate, standing business decision (also
      tracked in PR #182's carried-forward open items), independent of
      whether the CI/governance architecture itself works.

**STATUS: COMPLETE.** The CI-governance scope of Phase 18 (an always-running,
behaviorally-verified required gate covering `pytest tests/` and
`answer_governance/` for the first time) is done. The reconciliation business
question remains open as its own separate item, not as unfinished Phase 18
work.
