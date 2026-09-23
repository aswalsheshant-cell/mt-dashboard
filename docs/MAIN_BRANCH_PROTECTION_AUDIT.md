# Main Branch Protection Audit

**Created:** 2026-09-23, Phase 17.1 of "Production Acceptance & Certified Baseline
Lock." **Updated:** 2026-09-23, same day — ruleset created, tested, and configured;
CODEOWNERS reclassified from GAP to deferred/N/A (deliberate, single-collaborator
decision, not an oversight). **This is the final state for Phase 17 — CLOSED.**
Follow-on CI-coverage work continues as Phase 18 (`Production Acceptance Gate`).
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

**One important residual honesty note**: both live merge-attempt tests that could
have proven the *positive* case — "a genuinely-registered, still-pending required
check actually blocks a merge" — instead surfaced one of the two gaps above before
that could be observed. Neither test produced a clean confirmation of the ruleset
successfully blocking a merge. The configuration is real and the two failure modes
are fully explained and specific (not "the ruleset does nothing"), but the positive
case remains **CONFIGURED, not directly behavior-verified** — noted honestly rather
than claimed as proven.

## Full control table (final state)

| # | Control | Evidence | Status |
|---|---|---|---|
| 1 | Pull request required before merge | Ruleset setting is ON, confirmed by the repo owner in the UI. Not independently tested via a literal direct `git push origin main` (all testing went through the PR+merge-API path) | **CONFIGURED** — not directly behavior-tested |
| 2 | Required status checks exist and are wired to `pull_request` events | Confirmed directly, repeatedly, across all 3 test PRs: 9 checks now exist and report real pass/fail results | **PASS** |
| 3 | Those checks marked *required*, and actually block a pending merge | Configured (9 checks in the ruleset). **Not cleanly proven behaviorally** — see "residual honesty note" above; both live tests that could have shown this instead exposed the path-filter gap (Test 1) and the registration-race gap (Test 3) first | **CONFIGURED** — positive case untested |
| 4 | Direct push to `main` blocked | Implied by #1 being ON; not independently tested | **CONFIGURED** — not directly behavior-tested |
| 5 | Force push blocked | Ruleset setting is ON | **CONFIGURED** — not directly behavior-tested |
| 6 | Branch deletion blocked | Ruleset setting is ON | **CONFIGURED** — not directly behavior-tested |
| 7 | PR conversations must be resolved before merge | Ruleset setting is ON; no PR was tested with a deliberately unresolved conversation | **CONFIGURED** — not directly behavior-tested |
| 8 | Branch must be up to date with `main` before merge | Ruleset setting is ON; not behaviorally tested against a deliberately stale branch | **CONFIGURED** — not directly behavior-tested |
| 9 | Code owner / required-reviewer approval | No `CODEOWNERS` file exists; required approvals are set to `0`. Both are **deliberate, not gaps** (repo owner decision, 2026-09-23): with exactly one collaborator (`aswalsheshant-cell`, confirmed live via `list_repository_collaborators`), a CODEOWNERS file would only name that same person, making "code owner approval" a self-approval with no real control — and a risk of a dead end if GitHub ever required an owner review only the PR author could give | **DEFERRED / N/A** — not a blocker; revisit only if a second collaborator with write access joins |
| 10 | Security/code scanning as a merge condition | `Analyze (python)` and `Analyze (javascript-typescript)` (from `codeql.yml`) are now required checks — both passed on every test PR. The *separate* `github-advanced-security` check (not one of the 9 required) showed a real `failure` on PR #187 and, correctly, did not block that merge since it isn't required | **CONFIGURED**, consistent behavior observed for the non-required check; the required CodeQL checks' positive-blocking case shares the same untested status as row 3 |

## Classification summary (final)

| Status | Count | Rows |
|---|---|---|
| PASS | 1 | #2 |
| CONFIGURED (not directly behavior-tested for the positive/blocking case) | 8 | #1, #3, #4, #5, #6, #7, #8, #10 |
| DEFERRED / N/A (deliberate, single-collaborator reality) | 1 | #9 |
| GAP | 0 | — |
| NOT_VERIFIABLE_FROM_THIS_SESSION | 0 | — |

This is a meaningfully stronger state than the original "9 GAP, 1 PASS" finding, but
it is not "9 PASS" either — the distinction matters and is preserved here rather
than rounded up.

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
2. **CI trigger for `pytest tests/` and `answer_governance/`** — still not built as
   a required check today; scoped as Phase 18 (`Production Acceptance Gate`), which
   wires both suites, plus the other production checks, into one always-running
   workflow.
3. **The untested positive case (rows 1, 3–8, 10)** — accepted as-is per the repo
   owner's 2026-09-23 decision not to chase further testing. If a real incident ever
   traces back to the ruleset not blocking something it should have, that's the
   trigger to revisit this, not a scheduled re-test.

## Verdict for this sub-phase

**RESOLVED, WITH TWO ACCEPTED LIMITATIONS.** `main` now has a real, configured
ruleset with 9 required checks, tested three times against actual merge attempts.
Two genuine gaps were found and are documented rather than hidden; both are accepted
as out of scope for further mitigation per an explicit decision, not silently
ignored. CODEOWNERS is deferred/N/A by deliberate decision (row 9), not a remaining
gap. Phase 17 is closed; follow-on CI-coverage work (wiring `pytest tests/` and
`answer_governance/` into a required check) continues as Phase 18.
