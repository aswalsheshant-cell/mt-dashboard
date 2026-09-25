# Main Branch Protection Audit

**Created:** 2026-09-23, Phase 17.1 of "Production Acceptance & Certified Baseline
Lock." **Updated:** 2026-09-23, same day — ruleset created, tested, and configured;
CODEOWNERS reclassified from GAP to deferred/N/A (deliberate, single-collaborator
decision, not an oversight). Phase 17 closed on this state.
**Updated again, same day — Phase 18 complete.** `Production Acceptance Gate`
(`.github/workflows/production-acceptance-gate.yml`) was added to the required-checks
list and *behaviorally verified* via a real fail→blocked / fix→clean test (PR #189),
not just configured. That same test surfaced and fixed a third real defect — see
"Phase 18: positive-case verification and a real defect found" below. **This is now
the final state for both Phase 17 and Phase 18.**
**Scope:** determine whether `main`'s critical controls are actually *enforced* by
GitHub, not merely documented or assumed.

**Certified baseline this audit is protecting:**
`e0d4ceb8e3fd067e6395e5833f7358d1f2369c68` (main, 2026-09-23; 17/17 certification
gates PASS — unaffected by anything in this document).

## Where this landed

`main` started this pass with **zero GitHub-enforced protection**, confirmed
directly by the repo owner in Settings. A ruleset
(`Protect main - MT Dashboard Production`, Active) now exists, created by the repo
owner and verified — not just configured — via three real test PRs
(#183/#184, #185, #186/#187; full narrative in
`docs/MAIN_BRANCH_RULESET_CHECKLIST.md`). That testing found two genuine gaps, both
now accepted as documented limitations rather than chased further (repo owner
decision, 2026-09-23):

1. **Path-filtered required checks don't protect PRs outside their paths** — fixed
   by adding 5 always-triggering checks alongside the original 4, so every PR now
   has at least one enforced check.
2. **A merge attempted within ~1 second of PR creation can race ahead of check
   registration** — accepted as a limitation specific to near-instant, API-driven
   merges; a human using the GitHub UI does not reproduce this (opening and reading
   a PR before clicking Merge takes far longer than the ~1-second window measured).

**Phase 17's residual honesty note (now resolved by Phase 18, see below)**: both live
merge-attempt tests in Phase 17 that could have proven the *positive* case — "a
genuinely-registered, still-pending required check actually blocks a merge" —
instead surfaced one of the two gaps above before that could be observed. That gap
closed in Phase 18.

## Phase 18: positive-case verification and a real defect found

**Goal:** get the one remaining honest gap from Phase 17 — the positive case never
cleanly observed — actually proven, not assumed.

**What was added:** `.github/workflows/production-acceptance-gate.yml` (PR #188,
merged) — one always-running workflow (no path filter) wrapping `pytest tests/`
(165 tests, previously had no CI trigger at all), `pytest answer_governance/` (60
tests, same), `scripts/validate_historical_baseline.py`,
`scripts/validate_promo_schema.py`, the dashboard HTML/critical-function/
`window.DASH` checks, `scripts/ci_validate_datajs.py`, a Playwright browser-
regression suite, and an informational (non-blocking) reconciliation check — all
aggregated into one final job, `Production Acceptance Gate`. Full design:
`docs/PHASE18_PRODUCTION_ACCEPTANCE_GATE.md`.

**Stage A (PR #189, commit `70e2c25`)** — `tests/test_gate_enforcement_probe.py`
deliberately failed. `Production Acceptance Gate` reported `failure`. A real
`merge_pull_request` API call was attempted (not just eyeballed) and was refused:

```
405 Repository rule violations found
5 of 10 required status checks have not succeeded: 4 expected and 1 failing.
```

**This exposed a third, genuine defect**, distinct from Phase 17's two accepted
limitations: 4 of the then-10 required checks (`Schema Validation`,
`Historical Baseline Integrity`, `Dashboard Integrity Check`, `CI Results Summary` —
all from `validate-promo-data.yml`, path-filtered to `data/**`/`raw_promos/**`/a few
named scripts) never triggered for PR #189, since it only touched a test file. They
sat as GitHub's `expected` state — the exact failure mode GitHub's own docs warn
about for path-filtered required checks. This meant the ruleset could permanently
block a legitimate PR that never touches those paths, independent of whether
anything actually failed.

**Diagnosed and fixed, not just accepted.** All 4 were classified before removal:

| Check | Covered by `Production Acceptance Gate`? |
|---|---|
| `Schema Validation` | Yes — `Gate: Schema/Data Validation` runs the identical `scripts/validate_promo_schema.py --datajs dashboard/data.js` |
| `Historical Baseline Integrity` | Yes — `Gate: Historical Baseline Integrity` runs the identical `scripts/validate_historical_baseline.py` |
| `Dashboard Integrity Check` | Yes — `Gate: Dashboard Integrity` runs the identical brace/function/`window.DASH` checks (copied verbatim) |
| `CI Results Summary` | Yes, superseded — it was itself just an aggregator of the other 3; `Production Acceptance Gate` is a bigger aggregator doing the same job |

All 4 were safe to remove — pure duplication once `Production Acceptance Gate`
existed, nothing left uncovered. The repo owner removed them from the ruleset's
required-checks list directly in Settings (2026-09-23); `validate-promo-data.yml`
itself keeps running as-is for its own PR comments on data-path changes, just no
longer in the *required* list.

**Stage B (same PR #189, fix commit `842af2d`)** — the probe file was removed.
`Production Acceptance Gate` reported `success` on the new SHA. Before the ruleset
fix, `mergeable_state` was still `"blocked"` (a second diagnostic merge attempt
returned `405 ... 4 of 10 required status checks are expected` — direct confirmation
the defect, not the probe, was now the only thing blocking it). **After** the repo
owner removed the 4 duplicative checks, re-querying the *same* commit (`842af2d`, no
new push) showed `mergeable_state: "clean"` immediately — the passing state was
already there; only the required-checks list needed correcting.

PR #189 was closed without merging once both stages were recorded.

**Verdict: `Production Acceptance Gate`'s positive-blocking case is now
BEHAVIORALLY VERIFIED** — fail → real API refusal; fix → real API-confirmed clean
state, both on record with exact SHAs, error messages, and a live ruleset
correction along the way. This is the row-3 gap from Phase 17, now closed.

## Full control table (final state)

| # | Control | Evidence | Status |
|---|---|---|---|
| 1 | Pull request required before merge | Ruleset setting is ON, confirmed by the repo owner in the UI. Not independently tested via a literal direct `git push origin main` (all testing went through the PR+merge-API path). Strongly corroborated by Phase 18's Stage A/B: every merge attempt and every `mergeable_state` read went through the PR+required-checks combination exactly as this setting implies | **CONFIGURED** — not directly behavior-tested via a bare direct push |
| 2 | Required status checks exist and are wired to `pull_request` events | Confirmed directly, repeatedly, across all 3 Phase 17 test PRs plus Phase 18's PR #188/#189: the required-checks list now has **6** checks (`validate`, `Analyze (python)`, `Analyze (javascript-typescript)`, `Validate Dashboard Data & Schema`, `Validate HTML Structure & Fixes`, `Production Acceptance Gate`) after Phase 18 removed 4 duplicative, path-filtered ones — see "Phase 18" section above | **PASS** |
| 3 | Those checks marked *required*, and actually block a pending merge | **BEHAVIORALLY VERIFIED, Phase 18**: PR #189 Stage A — failing gate → real `405` merge refusal (`5 of 10 ... 4 expected and 1 failing`). Stage B — fixed gate → `mergeable_state` still `blocked` until the 4 duplicative checks were removed, then `clean` on the same SHA with no new push. Both directions proven with exact SHAs and API responses, not inferred | **PASS** — behaviorally verified |
| 4 | Direct push to `main` blocked | Implied by #1 being ON; not independently tested | **CONFIGURED** — not directly behavior-tested |
| 5 | Force push blocked | Ruleset setting is ON | **CONFIGURED** — not directly behavior-tested |
| 6 | Branch deletion blocked | Ruleset setting is ON | **CONFIGURED** — not directly behavior-tested |
| 7 | PR conversations must be resolved before merge | Ruleset setting is ON; no PR was tested with a deliberately unresolved conversation | **CONFIGURED** — not directly behavior-tested |
| 8 | Branch must be up to date with `main` before merge | Ruleset setting is ON; not behaviorally tested against a deliberately stale branch | **CONFIGURED** — not directly behavior-tested |
| 9 | Code owner / required-reviewer approval | No `CODEOWNERS` file exists; required approvals are set to `0`. Both are **deliberate, not gaps** (repo owner decision, 2026-09-23): with exactly one collaborator (`aswalsheshant-cell`, confirmed live via `list_repository_collaborators`), a CODEOWNERS file would only name that same person, making "code owner approval" a self-approval with no real control — and a risk of a dead end if GitHub ever required an owner review only the PR author could give | **DEFERRED / N/A** — not a blocker; revisit only if a second collaborator with write access joins |
| 10 | Security/code scanning as a merge condition | `Analyze (python)` and `Analyze (javascript-typescript)` (from `codeql.yml`) are required checks — both passed on every test PR, including Phase 18's PR #188/#189. The *separate* `github-advanced-security` check (not one of the required checks) showed a real `failure` on PR #187 and #188 and, correctly, did not block either merge since it isn't required; root-caused in Phase 18 as a GitHub-side Copilot Autofix backend error (`CAPIError: 400 The requested model is not supported`), not a licensing/plan gap — deferred as platform noise, not a repo defect | **CONFIGURED** — the CodeQL checks now share row 3's PASS via the same Stage A/B mechanism (they were 2 of the 6 checks proven to gate `mergeable_state`) |

## Classification summary (final)

| Status | Count | Rows |
|---|---|---|
| PASS | 3 | #2, #3, #10 |
| CONFIGURED (not directly behavior-tested for its own specific mechanism) | 6 | #1, #4, #5, #6, #7, #8 |
| DEFERRED / N/A (deliberate, single-collaborator reality) | 1 | #9 |
| GAP | 0 | — |
| NOT_VERIFIABLE_FROM_THIS_SESSION | 0 | — |

This is a meaningfully stronger state than both the original "9 GAP, 1 PASS" finding
and Phase 17's "1 PASS, 8 CONFIGURED" close. Rows 4–8 (direct push, force push,
deletion, conversation resolution, up-to-date-branch) still haven't each been
individually behavior-tested — Phase 18's proof was specifically about required
status checks (row 3) and, by direct consequence, the checks actually enforced under
that mechanism (row 10). That distinction is preserved here rather than rounded up
to "fully verified."

## What this changes from the original audit

The code certification (`e0d4ceb`, 17/17 gates, 224 tests) is unaffected — it
stood before this work and stands now. What changed: `main` went from provably
unprotected to a configured, partially-behavior-tested ruleset, with two real gaps
found by testing (not guessed at) and knowingly accepted rather than silently
assumed away.

## Remaining open items

1. **`.github/CODEOWNERS`** — deferred/N/A by deliberate repo owner decision
   (2026-09-23), not an oversight: see row 9. Revisit only if a second collaborator
   with write access joins the repo.
2. **CI trigger for `pytest tests/` and `answer_governance/`** — **DONE, Phase 18.**
   Both now run on every PR via `Production Acceptance Gate`, proven live and now
   part of the required-checks list.
3. **The untested-per-mechanism rows (1, 4–8)** — accepted as-is per the repo
   owner's 2026-09-23 decision not to chase further testing of each individual
   ruleset setting (direct push, force push, deletion, conversation resolution,
   up-to-date branch) beyond what Phase 18 already proved for required status
   checks. If a real incident ever traces back to one of these not blocking
   something it should have, that's the trigger to revisit it, not a scheduled
   re-test.
4. **`github-advanced-security`'s red status** — root-caused (Phase 18) as a
   GitHub-side Copilot Autofix backend error, not a repo-side config or licensing
   issue. Deferred as platform noise; already correctly excluded from required
   checks.

## Verdict for this sub-phase

**RESOLVED — Phase 17 and Phase 18 both CLOSED.** `main` has a real, configured
ruleset, now with the positive-blocking case behaviorally verified (not just
configured) via a real fail→blocked / fix→clean test on PR #189. That same test
found and fixed a third real defect — 4 duplicative, path-filtered checks that could
have permanently blocked legitimate PRs — bringing the required-checks list down to
6 essential ones: `validate`, `Analyze (python)`, `Analyze (javascript-typescript)`,
`Validate Dashboard Data & Schema`, `Validate HTML Structure & Fixes`, and
`Production Acceptance Gate` (which itself wires in `pytest tests/`,
`pytest answer_governance/`, and 6 other production checks). CODEOWNERS remains
deferred/N/A by deliberate decision (row 9), not a gap. `github-advanced-security`
is deferred platform noise, root-caused, not a repo defect. No open item here is
blocking; the repo's branch-protection governance work is complete for this pass.
