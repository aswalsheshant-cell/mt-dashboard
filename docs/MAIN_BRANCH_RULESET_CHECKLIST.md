# Main Branch Ruleset — Configuration Checklist

**Created:** 2026-09-23, direct follow-up to `docs/MAIN_BRANCH_PROTECTION_AUDIT.md`'s
P0 finding (`main` currently has zero GitHub-enforced protection, confirmed by the
repo owner directly in Settings). **This is a checklist for a human with repository
admin access to apply manually in the GitHub UI. No tool available to this session
can create or modify a ruleset, and this phase's own governing rule prohibits doing
so automatically even if one existed — this document does not change anything by
itself.**

Use GitHub's current **Rulesets** feature (`Settings → Rules → Rulesets`), not the
older classic "Branch protection rules" screen — rulesets are the actively developed
mechanism and support restricting a required check to a specific source (relevant
below). If this repository's plan doesn't expose Rulesets, the classic screen
(`Settings → Branches → Add branch protection rule`) covers everything except the
"restrict to source" option — noted where that matters.

---

## Step 1 — Navigate

`https://github.com/aswalsheshant-cell/mt-dashboard/settings/rules` →
**New ruleset → New branch ruleset**

## Step 2 — Name and enforcement

| Field | Value |
|---|---|
| Ruleset name | `main-protection` (or your preferred convention) |
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
  - [x] **Require branches to be up to date before merging** — check this. This is
    the GitHub-enforced version of the manual discipline this session applied by
    hand throughout Phase F2 (re-fetching `main` before every merge).
  - **Add required checks** — search and select each of the following (GitHub's
    picker lists checks by the names it has actually seen reported on this repo;
    select the current/latest instance of each):

    | Check to search for | Confirmed exact name (from this session's own CI runs) |
    |---|---|
    | Schema Validation | `Schema Validation` (job inside `validate-promo-data.yml`) |
    | Historical Baseline Integrity | `Historical Baseline Integrity` (job inside `validate-promo-data.yml` — the exact check this session's PR #181 fixed) |
    | Dashboard Integrity Check | `Dashboard Integrity Check` (job inside `validate-promo-data.yml`) |
    | CI Results Summary | `CI Results Summary` (rollup job inside `validate-promo-data.yml`) |
    | Dashboard Validation & QC | Workflow name confirmed; **exact job name not verified by this session** — select whatever check entry GitHub shows for the `validate.yml` workflow |
    | Dashboard UI Smoke Tests | Workflow name confirmed; exact job name not verified this pass — select the entry for `ui-smoke.yml` |
    | Power BI Windows CI Validation | Workflow name confirmed; exact job name not verified this pass — select the entry for `pbi-windows-ci.yml` |
    | CodeQL Security Analysis | Workflow name confirmed; exact job name not verified this pass — select the entry for `codeql.yml` |
    | Dashboard Health Check | Workflow name confirmed; exact job name not verified this pass — select the entry for `dashboard-health-check.yml` |

    **Do not add `answer_governance` or `pytest tests/` here yet** — per
    `docs/MAIN_BRANCH_PROTECTION_AUDIT.md`'s own finding, neither currently has a CI
    workflow trigger at all. Adding them as *required* checks before they exist as
    real CI jobs would permanently block every merge (a required check that never
    reports never becomes green). Build the CI trigger first (see companion action
    item below), confirm it reports at least once, *then* add it here.
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

## Step 7 — Verify it actually works (don't just trust the checkboxes)

Do these two low-risk tests before considering this done:

1. **Try (and expect to fail) a trivial direct push to `main`** from a local clone:
   ```
   git checkout main && git pull
   echo "# ruleset test" >> /tmp/discard_me.md && cp /tmp/discard_me.md ruleset-test.md
   git add ruleset-test.md && git commit -m "ruleset test - expect rejection"
   git push origin main
   ```
   Expect GitHub to **reject** this push with a message naming the ruleset. If it
   succeeds, the ruleset isn't actually active — stop and re-check Step 2 and Step 3.
   **Clean up either way**: `git reset --hard HEAD~1` locally; if the push somehow
   succeeded, also revert it on `main`.
2. **Open a real PR with one check still running** and confirm the **Merge** button
   is disabled/greyed out until all required checks report success. This is the
   direct behavioral proof that Step 5's required-checks configuration is real, not
   cosmetic.

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

## After this is done

Re-open `docs/MAIN_BRANCH_PROTECTION_AUDIT.md` and replace its "CONFIRMED GAP, P0"
verdict with the actual configured state — ideally verified the same way this
checklist's Step 7 verifies it (a real rejected push, a real blocked merge), not
just "the checkboxes are ticked."
