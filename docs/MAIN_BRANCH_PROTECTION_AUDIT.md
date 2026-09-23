# Main Branch Protection Audit

**Created:** 2026-09-23, Phase 17.1 of "Production Acceptance & Certified Baseline
Lock." **Updated:** 2026-09-23, same day — human confirmation received. **Scope:**
determine whether `main`'s critical controls are actually *enforced* by GitHub, not
merely documented or assumed. This document does not modify any GitHub setting —
audit only, per this phase's own non-negotiable rule ("Do NOT modify GitHub
governance automatically unless explicitly authorized").

**Certified baseline this audit is protecting:**
`e0d4ceb8e3fd067e6395e5833f7358d1f2369c68` (main, 2026-09-23; 17/17 certification
gates PASS).

## CONFIRMED FINDING (human-verified, 2026-09-23)

**`main` has no branch protection rule and no repository ruleset. It is completely
unprotected.** Checked directly by the repository's human owner at
`github.com/aswalsheshant-cell/mt-dashboard/settings/branches` and
`.../settings/rules` — no rule/protection entry exists for `main` at all.

This resolves every row this audit previously marked
`NOT_VERIFIABLE_FROM_THIS_SESSION` (this session had no tool to read GitHub's
branch-protection/ruleset API — confirmed by exhaustive `ToolSearch`, and a direct
unauthenticated API fallback via `WebFetch` returned `403 Forbidden` from this
environment's outbound proxy). With a human confirming no rule exists, there is
nothing left to enforce any of the following — every row that was previously
"unverifiable" is now definitively **GAP**, not because this session guessed, but
because the human-reported absence of any rule makes every dependent control absent
by construction.

## Full control table (updated with the confirmed finding)

| # | Control | Evidence | Status |
|---|---|---|---|
| 1 | Pull request required before merge | No rule exists → **a direct push to `main` would succeed today**, by anyone with write access. Every PR in this certification pass (#171–#178, #180, #181) went through a PR only because this session chose to, not because GitHub required it | **GAP** |
| 2 | Required status checks exist and are wired to `pull_request` events | Confirmed directly and unaffected by this finding: `.github/workflows/validate.yml`, `validate-promo-data.yml`, `ui-smoke.yml`, `pbi-windows-ci.yml`, `codeql.yml`, `dashboard-health-check.yml` all run on `pull_request` and are capable of failing (PR #180's `Promo Data Schema Validation` genuinely went `failure` → `success` across two head SHAs) | **PASS** — the checks exist and work; they are just not *required* by anything (see #3) |
| 3 | Those checks marked *required* in branch protection | No rule exists to mark anything required. **A red check today would not block a merge** — GitHub would allow it | **GAP** |
| 4 | Direct push to `main` blocked | No rule exists → not blocked | **GAP** |
| 5 | Force push blocked | No rule exists → not blocked | **GAP** |
| 6 | Branch deletion blocked | No rule exists → not blocked. `main` itself could be deleted by anyone with admin/write-delete permission | **GAP** |
| 7 | PR conversations must be resolved before merge | No rule exists → not enforced. Every merged PR in this pass happened to have conversations resolved, but that was this session's discipline, not a gate | **GAP** |
| 8 | Branch must be up to date with `main` before merge | No rule exists → not enforced. This session manually re-merged `main` into every PR before merging (the entire Phase F2 conflict-resolution sequence), but GitHub itself would have allowed a stale merge | **GAP** |
| 9 | Code owner / required-reviewer approval | No `CODEOWNERS` file exists (confirmed directly, independent of the ruleset question) — and even if one were added, there is no rule to require its use | **GAP** (two-part: no file, no rule) |
| 10 | Security/code scanning as a merge condition | `CodeQL Security Analysis` runs and reports real results, but with no rule marking it required, a failing scan would not block merge | **GAP** |

## What this changes from the original audit

Nothing about the **code certification** (`e0d4ceb`, 17/17 gates, 224 tests) —
that stands independent of this finding. What changes is the honesty of the claim
"main is protected": it was previously reported as *unconfirmed*; it is now
**confirmed false**. Every merge in this entire certification pass — all 10 PRs —
succeeded because this session chose to run checks and wait for green, not because
GitHub would have refused otherwise. That discipline held throughout this session,
but it is not durable: any future session, human, or automation with write access to
this repository can push directly to `main`, force-push over history, delete `main`
outright, or merge a PR with every check red, and nothing GitHub-side would stop it.

## Classification summary (updated)

| Status | Count | Rows |
|---|---|---|
| PASS | 1 | #2 (checks exist and run) |
| GAP | 9 | #1, #3, #4, #5, #6, #7, #8, #9, #10 |
| NOT_VERIFIABLE_FROM_THIS_SESSION | 0 | — (resolved by human confirmation) |
| BLOCKED | 0 | — |
| NOT_APPLICABLE | 0 | — |

## Recommended next action

This is now a **P0, not a "nice to have"** — the repository has zero GitHub-enforced
protection on its production branch. Recommended, in order (none executed by this
session — implementation requires explicit authorization, same as before):

1. **Create a branch protection rule or ruleset for `main`**, at minimum:
   - Require a pull request before merging.
   - Require status checks to pass before merging, and explicitly select as
     required: `Dashboard Validation & QC`, the `Historical Baseline Integrity` job,
     `Dashboard Health Check`, `Dashboard UI Smoke Tests`, `Power BI Windows CI
     Validation`, `CodeQL Security Analysis`.
   - Require the branch to be up to date with `main` before merging.
   - Block force pushes.
   - Block branch deletion.
   - Require conversation resolution before merging.
2. Add a `.github/CODEOWNERS` file (still a separate, independently real gap — see
   row #9) so a future "require code owner review" setting has something to attach to.
3. Add a CI trigger for `pytest tests/` and `pytest answer_governance/` on
   `pull_request` (from the original audit's finding — still open, still not
   implemented) so those two suites — 224 and 60 tests respectively, everything this
   certification pass relied on most heavily — are enforced automatically rather
   than only by a human running them by hand.
4. Once the rule/ruleset exists, re-run this audit against the live configuration to
   confirm each row moved from GAP to PASS.

## Verdict for this sub-phase

**CONFIRMED GAP, P0 PRIORITY.** The certified baseline
(`e0d4ceb8e3fd067e6395e5833f7358d1f2369c68`) itself is unaffected — its 17/17
certification stands. But the claim "main is protected" is now **known to be false**,
not merely unverified. Until a rule or ruleset is created, this repository's actual
safety net is entirely operator discipline — real, and held throughout this
certification pass, but not something GitHub itself backs up. This is the single
highest-priority action to come out of the entire Phase 17 audit.
