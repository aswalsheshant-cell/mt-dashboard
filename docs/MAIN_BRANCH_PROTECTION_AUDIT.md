# Main Branch Protection Audit

**Created:** 2026-09-23, Phase 17.1 of "Production Acceptance & Certified Baseline
Lock." **Scope:** determine whether `main`'s critical controls are actually
*enforced* by GitHub, not merely documented or assumed. This document does not
modify any GitHub setting — audit only, per this phase's own non-negotiable rule
("Do NOT modify GitHub governance automatically unless explicitly authorized").

**Certified baseline this audit is protecting:**
`e0d4ceb8e3fd067e6395e5833f7358d1f2369c68` (main, 2026-09-23; 17/17 certification
gates PASS — see `docs/BASELINE_VERSION.md` if present, or the certification report
in this session's own record).

## A hard limitation, stated up front

**This session has no tool that reads GitHub's branch-protection or repository-ruleset
API** (`GET /repos/{owner}/{repo}/branches/{branch}/protection` or
`GET /repos/{owner}/{repo}/rules/branches/{branch}`). The GitHub MCP server available
in this session exposes PR, issue, commit, workflow-run, and file-content tools, but
no branch-protection or ruleset read/write endpoint (confirmed by exhaustive
`ToolSearch` across this session's tool catalog before writing this audit — not
assumed absent).

Per this phase's own rule — **"No UNKNOWN result is permitted without a documented
reason"** — every row below that depends on that missing capability is classified
**NOT_VERIFIABLE_FROM_THIS_SESSION**, with the reason stated, rather than guessed at
or assumed either PASS or GAP. **This is itself the first finding**: closing it
requires either (a) a human checking `github.com/aswalsheshant-cell/mt-dashboard/settings/branches`
and `.../settings/rules` directly and reporting back, or (b) granting this session
(or a future one) a GitHub App/token scope and MCP tool that can read repository
rulesets.

## What this audit COULD verify from this session's own tools

| # | Control | Evidence available | Status |
|---|---|---|---|
| 1 | Pull request required before merge | Indirect: every one of the 10 PRs merged in this certification pass (#171–#178, #180, #181) went through `create_pull_request` → CI → `merge_pull_request`; no direct push to `main` was made or attempted by this session at any point in this audit's traceable history | **CONSISTENT WITH PR-required, not proof of an enforced rule** — a session choosing to use PRs is not evidence GitHub would *reject* a direct push |
| 2 | Required status checks exist and are wired to `pull_request` events | Confirmed directly: `.github/workflows/validate.yml`, `validate-promo-data.yml`, `ui-smoke.yml`, `pbi-windows-ci.yml`, `codeql.yml`, `dashboard-health-check.yml` all declare `on: pull_request` and all ran and reported a conclusion (`success`/`failure`) on every PR this session touched (PR #180's `Promo Data Schema Validation` genuinely went from `failure` to `success` across two head SHAs, proving the check is live, not decorative) | **PASS** (checks exist, run, and are capable of failing — verified, not assumed) |
| 3 | Whether those checks are *marked required* in branch protection (i.e., whether GitHub would block a merge if one were red) | Not observable from this session — `merge_pull_request` was only ever called after visually confirming all checks were `success`; whether GitHub itself would have refused the merge with a red check is untested this pass, and the tool used (`mcp__github__merge_pull_request`) does not report whether it succeeded *because* checks passed or because nothing required them | **NOT_VERIFIABLE_FROM_THIS_SESSION** — no red-check merge was ever attempted (deliberately, per this session's own governing rule against bypassing checks), so the enforcement boundary itself was never tested |
| 4 | Direct push to `main` blocked | Not tested — this session never attempted a direct push to `main` (by design, per its own operating rules), so absence of an attempt is not evidence of a working block | **NOT_VERIFIABLE_FROM_THIS_SESSION** |
| 5 | Force push blocked | Not tested; no force push was attempted | **NOT_VERIFIABLE_FROM_THIS_SESSION** |
| 6 | Branch deletion blocked | Not tested | **NOT_VERIFIABLE_FROM_THIS_SESSION** |
| 7 | PR conversations must be resolved before merge | Every merged PR in this pass had 0–3 comments, none left unresolved by the time of merge, but this was a matter of this session's own diligence, not a tested GitHub-enforced gate (no PR was attempted to merge with a deliberately unresolved conversation) | **NOT_VERIFIABLE_FROM_THIS_SESSION** |
| 8 | "Branch must be up to date with `main` before merge" (or equivalent merge-queue protection) | Every PR in this pass was manually re-merged with the latest `main` before each merge attempt (the entire Phase F2 conflict-resolution sequence exists because of this discipline) — but this was operator discipline, not a tested GitHub-enforced requirement; no attempt was made to merge a stale PR to see if GitHub itself would refuse | **NOT_VERIFIABLE_FROM_THIS_SESSION** — though the operational discipline that substitutes for it is well evidenced (every PR's conflict-resolution branch in this session traces to a fresh `git fetch origin main` immediately before use) |
| 9 | Code owner / required-reviewer approval | No `CODEOWNERS` file exists in the repository (confirmed: `ls .github/CODEOWNERS` and `find . -iname CODEOWNERS` both return nothing on `main` at `e0d4ceb`) | **GAP** — this is directly verifiable and is a real gap, not a tooling limitation: with no `CODEOWNERS` file, a required-code-owner-review rule (even if configured in branch protection) has nothing to attach to |
| 10 | Security/code scanning as a merge condition | `CodeQL Security Analysis` (`codeql.yml`) runs on every PR and reported `success` on every PR in this pass; whether a `failure` conclusion would itself block merge (i.e., whether it's a *required* check) is the same unverifiable boundary as row 3 | **PARTIAL** — the scan itself is real and running; its status as a blocking gate is NOT_VERIFIABLE_FROM_THIS_SESSION |

## Required-checks vs. validated-workflow comparison

The prompt's suggested required-check list, checked against what actually exists and
ran green in this certification pass:

| Suggested required check | Exists as a real workflow? | Ran and passed on the final certified head? |
|---|---|---|
| Dashboard Validation & QC | Yes — `validate.yml` | Yes (PR #180, #181) |
| Historical Baseline Integrity | Yes — job inside `validate-promo-data.yml` | Yes (PR #180, #181 — this is the exact check this session's Phase-16-adjacent work fixed) |
| Promo Data Schema Validation | Yes — `validate-promo-data.yml` (the workflow; "Historical Baseline Integrity" is one job inside it, not a separate workflow) | Yes |
| Dashboard Health Check | Yes — `dashboard-health-check.yml` | Yes |
| Dashboard UI Smoke Tests | Yes — `ui-smoke.yml` | Yes |
| Power BI Windows CI | Yes — `pbi-windows-ci.yml` | Yes |
| CodeQL | Yes — `codeql.yml` | Yes |
| `answer_governance` | **Not a separate CI job** — it runs as part of the local `pytest` suite this session ran manually (60/60 passed on final main); **no GitHub Actions workflow in this repo currently invokes `pytest answer_governance/` on a PR event** | **GAP** — this is a real, actionable, low-risk finding: `answer_governance/`'s 60 tests protect governed evidence-building logic and currently have no CI trigger at all, only manual/local execution |
| `validate_historical_baseline` (the new PR #181 module) | Yes — invoked directly by `validate-promo-data.yml`'s "Verify FY25/FY26 baseline coverage" step (`python3 scripts/validate_historical_baseline.py`) | Yes |
| Publication-contract validation | Partially — `validate-promo-data.yml`'s `validate-dashboard` job checks the `window.DASH` wrapper and a handful of function names; there is no dedicated "publication contract" schema check beyond that | **PARTIAL** — real but thin |

**New finding from this comparison, not previously flagged:** `pytest tests/` (224
tests) and `pytest answer_governance/` (60 tests) — the two suites this entire
certification pass relied on most heavily — have **no CI workflow trigger at all**.
Every green result reported for them in this certification was produced by a human
(this session) running `pytest` manually inside the sandboxed environment, not by an
automated, required GitHub Actions gate. A future PR could regress either suite and
no required check would catch it before merge.

## Classification summary

| Status | Count | Rows |
|---|---|---|
| PASS | 1 | #2 |
| PARTIAL | 2 | #3 (partial, checks exist)*, #10 |
| GAP | 2 | #9 (no CODEOWNERS), pytest/answer_governance CI trigger (new finding above) |
| NOT_VERIFIABLE_FROM_THIS_SESSION | 7 | #1, #3 (enforcement), #4, #5, #6, #7, #8 |
| BLOCKED | 0 | — |
| NOT_APPLICABLE | 0 | — |

\* Row #3 appears in both PASS (workflow existence, confirmed) and
NOT_VERIFIABLE_FROM_THIS_SESSION (whether marked "required," unconfirmed) — split
deliberately rather than forced into one bucket, per the no-UNKNOWN rule.

## Recommended next action (not executed — audit only)

1. **A human with repository admin access** opens
   `https://github.com/aswalsheshant-cell/mt-dashboard/settings/rules` (or
   `/settings/branches` if this repo still uses classic branch protection rather than
   the newer rulesets) and reports back which of rows #1, #3 (enforcement), #4–#8
   are actually configured. Until that happens, this repository's real protection
   level is **unknown to any Claude Code session**, not merely to this one.
2. Add a `.github/CODEOWNERS` file naming at least the repository's primary
   maintainer for `dashboard/`, `scripts/`, `.github/workflows/`, and `config/` — a
   real, actionable, zero-ambiguity gap this audit found directly (row #9).
3. Add a CI workflow trigger for `pytest tests/` and `pytest answer_governance/` on
   `pull_request` — closing the gap found in the required-checks comparison above.
   This is scoped as a **design recommendation for Phase 17.2**, not implemented here.
4. Once a human confirms the live ruleset state, re-run this audit and replace every
   NOT_VERIFIABLE_FROM_THIS_SESSION row with a real PASS/GAP.

## Verdict for this sub-phase

**GAPS FOUND, NOT BLOCKING CERTIFICATION** — the certified baseline
(`e0d4ceb8e3fd067e6395e5833f7358d1f2369c68`) is unaffected by this audit; nothing here
changes its CERTIFIED status. But **"main is protected" cannot be asserted as true
today** — it can only be asserted as "operationally protected by this session's own
discipline so far," which is a materially weaker and non-durable claim. Two concrete,
low-risk, high-value actions are identified (CODEOWNERS, CI trigger for the two
un-gated pytest suites) and left for explicit human authorization before
implementation.
