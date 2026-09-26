# Review checklist

Work through it for every PR. Record each "no" as a finding.

## 1. State

- [ ] `main` SHA, PR head SHA and merge base recorded (`git merge-base origin/main <head>`)
- [ ] No merge base → the branch is from unrelated history; judge the defect, not the branch
- [ ] Mergeable, and up to date with `main` (the ruleset requires strict up-to-date)
- [ ] All six required checks green on the **head** SHA, not an older commit
- [ ] Any non-required workflow the PR touches is also read (a required-check list can
      miss the very workflow the PR changes — #225's Power BI Windows CI)

## 2. Historical PR triage

- [ ] Defect reproduced on current `main` → `STILL_LIVE`
- [ ] Not reproducible, and the fix is on `main` → `SUPERSEDED` (name the commit)
- [ ] Still live and the branch is stale, conflicted or has no merge base →
      `REBUILD_REQUIRED` on a fresh branch from `main`, reusing the old diff's reasoning
- [ ] Old PR's extra scope (new features, rewrites) is dropped unless still needed

## 3. The diff

- [ ] Every changed file read in full context, not only the hunks
- [ ] Scope matches the stated purpose; unrelated edits are named
- [ ] No protected path changed without a reason: `dashboard/data.js`, `config/`,
      `PowerBI/SeedData/`, baselines, the MT universe and store-to-SO mapping CSVs
- [ ] Missing data renders as `–`, not `0`, `NaN` or `undefined` (CLAUDE.md invariant 3)
- [ ] FY logic derived from month and year (THE ONE FY RULE), no hard-coded FY list
- [ ] No secret, token or personal identifier added
- [ ] Error paths: a caught error is surfaced, not swallowed (`.catch(()=>{})`,
      `except: pass`) unless a comment says why
- [ ] Existing function extended rather than duplicated (CLAUDE.md rules 2–3)

## 4. Verification harness

See SKILL.md, "Verification-harness integrity", and `github-actions-checklist.md`.

## 5. Governance records

- [ ] New failure pattern → a row in `docs/FAILURE_MODE_REGISTER.md` (or a note on the
      matching FM-NN row), never a parallel register
- [ ] New data source → `config/data_source_registry.yml`
- [ ] New number on a card → `docs/METRIC_REGISTRY.md`

## Worked examples

**#225 — Power BI Windows CI green over two exit-1 validators (rebuild of #131).**
The job conclusion was success; its log said `CI RUN FAILED`. Causes found by reading
the log, not the badge: `continue-on-error: true` on both validation steps; a pwsh step
running two scripts with no `$LASTEXITCODE` check; an M checker that rejected a valid
parameter query; three integrity checks asserting fields and names the current
architecture no longer uses. Review points that mattered: the replacement checks were
proven not weaker with mutation cases (zone double count, missing FY27 total, NaN); the
retired `eval_harness.py` was named "optional diagnostic" and shown as a warning rather
than hidden; the pwsh-dependent tests were shown to run in CI by matching the log's
pass/skip counts (391/23) against a local run with pwsh present.

**#226 — failed alert-feed load rendered "All metrics within thresholds" (rebuild of
#156).** Product fix was sound. Second-order finding: the new Playwright test hard-coded
`/opt/pw-browsers/chromium` although `tests/browser_launch.js` exists for exactly that —
a verification-standard defect introduced by the fix. Fixed before merge; the test was
re-proven (12/17 fail on `main`, 17/17 on the fix; a missing browser exits 1 with a
named error, never a skip).
