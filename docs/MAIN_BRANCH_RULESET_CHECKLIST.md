# Main Branch Ruleset — Configuration Checklist

**Created:** 2026-09-23, direct follow-up to `docs/MAIN_BRANCH_PROTECTION_AUDIT.md`'s
P0 finding (`main` currently had zero GitHub-enforced protection, confirmed by the
repo owner directly in Settings). **Steps 0–6 below were applied manually in the
GitHub UI by the repo owner and are now DONE** — the ruleset
`Protect main - MT Dashboard Production` exists and is Active. No tool available to
this session can create or modify a ruleset itself; every actual UI action recorded
below was performed by the repo owner, with this session verifying the result via the
API. **Status as of 2026-09-23: DONE — ruleset live with all 9 required checks (the
original 4 + the 5 verified in Test 2). Two real gaps were found by testing (not
assumed) and are recorded as accepted limitations below — see "Verification
results" and "Known limitations (accepted, not further mitigated)".**

## Verification results (what actually happened, not the plan)

**Test 1 — proved the ruleset was real, and found a real gap.** A throwaway PR
(#183) was merged deliberately while its checks were still pending, to prove
enforcement rather than trust the checkbox. **It merged — which it shouldn't have.**
Root cause: all 4 originally-required checks live inside `validate-promo-data.yml`,
which is path-filtered to `data/**`, `raw_promos/**`, and a few named scripts. The
test PR's only file didn't match any of those paths, so that workflow never
triggered at all — and GitHub does not block a merge on a required check whose
source workflow never fires for a given PR (documented behavior, not a bug). This
means the original 4 checks only protect PRs that touch those specific paths — most
of `dashboard/` and most of `scripts/` were unprotected. **Fixed immediately**: the
accidental merge was reverted via a clean PR (#184), not a direct push — `main` is
back to the exact certified tree.

**Test 2 — audited 5 candidate checks from workflows with no path filter on
`pull_request`**, before adding any of them, per the correct caution: don't add a
required check on the assumption it runs everywhere; prove it first with a
docs-only PR, and don't merge it. PR #185 (`docs/ruleset-required-check-test.md`,
closed without merging) confirmed all 5 ran to completion and passed:

| Check | Source workflow | Result |
|---|---|---|
| `validate` | `validate.yml` (no path filter) | ✅ completed, `success` |
| `Analyze (python)` | `codeql.yml` (no path filter) | ✅ completed, `success` |
| `Analyze (javascript-typescript)` | `codeql.yml` (no path filter) | ✅ completed, `success` |
| `Validate Dashboard Data & Schema` | `dashboard-health-check.yml` (`pull_request` trigger has no path filter — only its `push` trigger does) | ✅ completed, `success` |
| `Validate HTML Structure & Fixes` | `dashboard-health-check.yml` (same as above) | ✅ completed, `success` |

All 5 are **SAFE_TO_REQUIRE: YES** — confirmed live, not inferred from reading the
YAML alone. **Action still needed**: add these 5 to the ruleset's required-checks
list, alongside the original 4 (see the updated table below). This closes the exact
gap Test 1 found: every PR now has at least one required check that actually runs,
regardless of which files it touches.

One unrelated finding surfaced during Test 2, not part of the 5 candidates and not
yet acted on: `github-advanced-security` (a separate, GitHub-native default
code-scanning check, distinct from this repo's own `codeql.yml`) completed with
`failure` on a trivial docs-only change. Worth investigating on its own; not added to
required checks and not blocking this ruleset work.

**Test 3 — the 5 new checks were added to the ruleset, then re-verified with the
same merge-while-pending method used in Test 1.** A third throwaway PR (#186) was
merged immediately after creation. **It merged again** — but for a different reason
than Test 1. This time all 5 checks genuinely started running; the merge API call
just completed *before* GitHub had registered them against that commit SHA.
Timestamps: merge completed `04:30:26`; the required checks' own `started_at` was
`04:30:27`–`04:30:28`, one second later. **Fixed immediately** via a clean revert PR
(#187), merged only after its own checks had genuinely completed (not rushed this
time) — `main` confirmed back to the exact certified tree.

## Known limitations (accepted, not further mitigated) — decision made 2026-09-23

Two real, test-proven gaps exist in this ruleset. Both are being accepted as-is
rather than chased further, because both require conditions a normal human using the
GitHub UI does not produce:

1. **Path-filtered required checks don't protect PRs outside their paths** (Test 1).
   The original 4 checks (`Schema Validation`, `Historical Baseline Integrity`,
   `Dashboard Integrity Check`, `CI Results Summary`) only enforce on PRs touching
   `data/**`, `raw_promos/**`, or the few named scripts in
   `validate-promo-data.yml`'s path filter. **Mitigated, not eliminated**: the 5
   checks added after Test 2 (`validate`, `Analyze (python)`,
   `Analyze (javascript-typescript)`, `Validate Dashboard Data & Schema`,
   `Validate HTML Structure & Fixes`) have no path filter and cover every PR — so
   every PR now has at least one enforced check, even though the original 4 remain
   path-scoped by design (they're specifically about data/pipeline integrity, which
   doesn't need to run on, say, a docs-only change).
2. **A merge attempted within ~1 second of PR creation can race ahead of check
   registration** (Test 3). This is a GitHub platform timing behavior, not a
   configuration mistake — confirmed by observing that the required checks
   genuinely started running, just a moment after the merge API call returned.
   **Accepted as a known limitation of near-instant, API-driven merges specifically.**
   A human clicking "Merge" in the GitHub UI does not reproduce this: opening a PR,
   reading it, and clicking merge takes several seconds at an absolute minimum —
   far past the ~1-second race window measured here. The two accidental merges this
   limitation caused in this repo's own history (PR #183, PR #186) were both
   produced by this session's own automated, immediate merge-attempt testing
   methodology, not by normal human use of the repository.

**Decision, per the repo owner (2026-09-23): accept both as documented, don't
build further mitigation (e.g., a required "wait" step, a merge queue, or
retry-with-backoff logic) unless a real incident traces back to either one.** If
that changes, `docs/POST_MERGE_CERTIFICATION_DESIGN.md`'s already-designed
post-merge certification gate would be the natural place to add a defense-in-depth
check (re-validating the actual `main` SHA after merge, independent of whether the
pre-merge ruleset caught everything).

Use GitHub's current **Rulesets** feature (`Settings → Rules → Rulesets`), not the
older classic "Branch protection rules" screen — rulesets are the actively developed
mechanism and support restricting a required check to a specific source (relevant
below). If this repository's plan doesn't expose Rulesets, the classic screen
(`Settings → Branches → Add branch protection rule`) covers everything except the
"restrict to source" option — noted where that matters.

---

## Step 0 — Check for an existing rule first (do this before creating anything)

Rulesets and classic branch protection **layer together** — GitHub applies the most
restrictive combination of whatever exists, not just your newest rule. Before
creating a new ruleset, check both screens for anything already targeting `main`:

- `https://github.com/aswalsheshant-cell/mt-dashboard/settings/rules`
- `https://github.com/aswalsheshant-cell/mt-dashboard/settings/branches`

This session's own audit (`docs/MAIN_BRANCH_PROTECTION_AUDIT.md`) already found —
confirmed by you directly in Settings — that **no rule or ruleset exists for `main`
today**, so this should come up empty. If it doesn't (something shows up that wasn't
there when the audit was done), stop and compare it against what follows rather than
creating a second, possibly-conflicting rule blindly.

## Step 1 — Navigate

`https://github.com/aswalsheshant-cell/mt-dashboard/settings/rules` →
**New ruleset → New branch ruleset**

## Step 2 — Name and enforcement

| Field | Value |
|---|---|
| Ruleset name | `Protect main - MT Dashboard Production` |
| Enforcement status | **Active** — not "Evaluate" (Evaluate only logs what *would* have been blocked; it enforces nothing) |

## Step 3 — Target branches

- Targeting criteria: **Include by pattern** → `main`
- Do not use "Include default branch" as a shortcut unless you're certain `main` is
  and will remain the default — an explicit pattern is safer and self-documenting.

## Step 4 — Bypass list

**Decide this deliberately, don't leave it default.** Options:

- **No bypass (recommended for a production dashboard repo)** — even repository
  admins must go through a PR and pass checks. This is the strictest, safest option
  and matches what this session's own certification work actually did throughout
  (every one of the 10 PRs in this pass went through checks, by choice — this makes
  that choice mandatory instead of optional).
- **Repository admin bypass** — if you want an emergency-fix escape hatch. If chosen,
  restrict it to a named role, not "everyone with write access," and treat every use
  of it as an incident worth a note in `docs/FAILURE_MODE_REGISTER.md`.

This audit does not pick one for you — it's a real governance decision, not an
engineering one.

## Step 5 — Branch rules (check each box, configure as shown)

- [ ] **Restrict deletions** — prevents `main` from being deleted by anyone in the
  bypass-excluded set.
- [ ] **Require linear history** *(optional — this repo has used merge commits
  throughout, e.g. `e0d4ceb Merge pull request #180...`; only enable this if you
  intend to switch the whole team to squash/rebase merges going forward — enabling it
  today would make every past merge-commit-based PR workflow this session used no
  longer possible)*.
- [ ] **Require a pull request before merging** — check this, then configure:
  - [ ] **Required approvals**: your call — even `0` is a meaningful improvement over
    today's zero-gate state, since it still forces a PR + required checks. `1+`
    requires a human reviewer — checked live via `list_repository_collaborators`:
    this repo currently has exactly **one** collaborator (`aswalsheshant-cell`,
    admin), no second maintainer. Set to `0` unless you add a second reviewer first,
    or the rule will permanently block every merge (nobody else could ever approve).
  - [ ] **Dismiss stale pull request approvals when new commits are pushed** —
    recommended if you set approvals ≥1.
  - [ ] **Require review from Code Owners** — leave **unchecked** until
    `.github/CODEOWNERS` exists (see the companion action item below); checking it
    now with no CODEOWNERS file configured would either do nothing or block every PR
    depending on GitHub's current behavior — don't rely on that ambiguity.
  - [x] **Require conversation resolution before merging** — check this.
  - [ ] **Require signed commits** *(optional, stricter — not currently practiced by
    this session's commits, which are unsigned; enabling this would retroactively
    require a workflow change, not just a setting change)*.
- [ ] **Require status checks to pass** — check this, then:
  - [x] **Require branches to be up to date before merging** — check this (steady-
    state recommendation). This is the GitHub-enforced version of the manual
    discipline this session applied by hand throughout the earlier certification
    merge sequence (re-fetching `main` before every merge). **Note:** at the time
    you're applying this, all 10 certified PRs from that sequence are already
    merged — there is no open PR queue behind this repo right now, so turning this
    on has no "PR #2 goes stale when PR #1 merges, repeat" cost today. It only
    matters for future PRs, same as any repo.
  - **Add required checks** — the confirmed, final list (originally-configured 4,
    plus the 5 verified safe by Test 2 above — **add these 5 now if not already
    added**):

    | Exact check name | Source | Path-filtered? | Verified |
    |---|---|---|---|
    | `Schema Validation` | `validate-promo-data.yml` | Yes — `data/**`, `raw_promos/**`, a few scripts | Original 4, live since ruleset creation |
    | `Historical Baseline Integrity` | `validate-promo-data.yml` | Yes, same as above | Original 4 |
    | `Dashboard Integrity Check` | `validate-promo-data.yml` | Yes, same as above | Original 4 |
    | `CI Results Summary` | `validate-promo-data.yml` | Yes, same as above | Original 4 |
    | `validate` | `validate.yml` | **No** | Confirmed by Test 2, PR #185, `success` |
    | `Analyze (python)` | `codeql.yml` | **No** | Confirmed by Test 2, `success` |
    | `Analyze (javascript-typescript)` | `codeql.yml` | **No** | Confirmed by Test 2, `success` |
    | `Validate Dashboard Data & Schema` | `dashboard-health-check.yml` | **No** (on `pull_request`) | Confirmed by Test 2, `success` |
    | `Validate HTML Structure & Fixes` | `dashboard-health-check.yml` | **No** (on `pull_request`) | Confirmed by Test 2, `success` |

    The first 4 stay valuable for PRs that touch data/pipeline paths; the last 5 are
    what actually close the "PR touching neither" gap Test 1 found — **every PR now
    has at least one required check from the second group that will always run.**

    **Still do not add `answer_governance` or `pytest tests/`** — per
    `docs/MAIN_BRANCH_PROTECTION_AUDIT.md`'s own finding, neither currently has a CI
    workflow trigger at all. Build the CI trigger first (see companion action item
    below), confirm it reports at least once on a real PR (the same Test-2 method
    used above, not assumed), *then* add it here.
  - If using **Rulesets** (not classic protection): for each required check, use the
    **"Restrict to source"** option and pin it to **GitHub Actions** — this is the
    protection this audit's earlier research flagged as available ("GitHub supports
    restricting a required check to the expected GitHub App, preventing a same-named
    status from another source satisfying the gate"). Skip this sub-step if using
    classic branch protection, which doesn't offer it.
- [x] **Block force pushes** — check this.

## Step 6 — Save

Click **Create** (or **Save changes**). The ruleset is **Active** immediately — no
separate publish step.

## Step 7 — Verify it actually works (done — this is what was actually run, and why the "optional stronger proof" turned out to be the necessary one)

Don't test this against your real `main` with a direct push — the ruleset's PR
requirement makes that impossible anyway once it's active. What was actually done,
in order:

1. **A throwaway branch + PR** (`ruleset-test` → PR #183, `RULESET_TEST.md`) —
   opened, not merged, checks still pending.
2. **The "optional, stronger proof" was not optional — it's what actually caught the
   real gap.** Attempting to merge PR #183 *while its checks were still pending*
   **succeeded**, when it should have been refused. That's what surfaced the
   path-filter gap documented in "Verification results" above. A test that only
   checks whether the merge button *looks* greyed out in the UI would not have
   caught this — the API-level merge attempt was the test that actually mattered.
3. **The accidental merge was reverted via a clean revert PR** (#184), not a force-
   push or direct edit to `main` — `main` confirmed back to the exact certified
   tree afterward (`GET` on the test file returned "does not exist").
4. **A second, more careful test** (PR #185, `docs/ruleset-required-check-test.md`,
   opened as **draft** specifically to remove any risk of an accidental merge) was
   used to audit the 5 candidate checks before adding them — waited for full
   completion (not just "started running"), confirmed all 5 reached `success`, then
   closed without merging. See "Verification results" above for the exact outcome.

**Lesson for any future ruleset check-list change**: the real test is attempting a
merge while a required check is genuinely pending or absent, not just opening a PR
and eyeballing the UI. A required check that never triggers looks identical, from
the merge-box UI, to one that's about to pass — the only way to tell them apart is
to actually try the merge.

## Companion action items (referenced above, not part of this checklist itself)

1. Add `.github/CODEOWNERS` — a separate, already-identified gap
   (`docs/MAIN_BRANCH_PROTECTION_AUDIT.md` row 9). Minimal example:
   ```
   # Default owner for the whole repo
   *  @aswalsheshant-cell
   ```
   Once this exists, you can revisit Step 5's "Require review from Code Owners" box.
2. Add a `pull_request`-triggered CI workflow for `pytest tests/` and
   `pytest answer_governance/` (design left open in
   `docs/POST_MERGE_CERTIFICATION_DESIGN.md`) — then add it to Step 5's required
   checks once it has reported at least once.

## Current status (2026-09-23) — DONE

- Ruleset created, Active: ✅ done.
- All 9 required checks live: ✅ done — original 4 (`Schema Validation`,
  `Historical Baseline Integrity`, `Dashboard Integrity Check`, `CI Results Summary`)
  plus the 5 always-triggering ones (`validate`, `Analyze (python)`,
  `Analyze (javascript-typescript)`, `Validate Dashboard Data & Schema`,
  `Validate HTML Structure & Fixes`).
- Two real gaps found by testing (not assumed): path-filter gap (Test 1) and a
  merge/check-registration race (Test 3) — both documented in "Known limitations
  (accepted, not further mitigated)" above, and accepted as-is per the repo owner's
  explicit decision (2026-09-23): don't build further mitigation unless a real
  incident traces back to either one.
- All three accidental merges this testing produced (#183, #186 — plus their
  reverts #184, #187) were cleaned up; `main` confirmed back to the exact certified
  tree each time, verified via direct file-existence checks, not assumed.
- `docs/MAIN_BRANCH_PROTECTION_AUDIT.md` still needs a follow-up pass to move from
  "CONFIRMED GAP, P0" to the actual final state now that the ruleset is genuinely
  live and verified — this is the next, smaller remaining step.
- Stale test branches (`ruleset-test`, `revert-ruleset-test`, `required-check-audit`,
  `ruleset-test-2`, `revert-ruleset-test-2`) remain on `origin` — branch deletion via
  `git push --delete` hit a 403 from this environment's outbound proxy; delete them
  via the GitHub UI's "Delete branch" button whenever convenient (cosmetic only, not
  a risk).
