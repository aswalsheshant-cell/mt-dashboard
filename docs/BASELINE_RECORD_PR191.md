# Baseline Record — PR #191 (WoA exception-visibility fix)

**Created:** 2026-09-23. Documentation-only record of a merge that already happened
and was already validated in conversation — this file exists so that evidence isn't
left only in chat history. No business logic, workbook output, or WoA classification
is touched by this PR. If anything here needs updating, it means a later fact
changed, not that this record was wrong when written.

## 1. Baseline commit

`main` SHA: **`3ef146abc9285e949eb808a877d4aed5691cb4c0`** — the merge commit for
PR #191, currently at the tip of `main` at the time this record was written.

## 2. PR #191 lineage

- **Title:** `fix(incentive): close 08_Exceptions visibility gap + placeholder regex bug`
- **Base:** `main` @ `61d939348bde2bd0c5dfa223e53dc29ab2036b30` (PR #190's merge)
- **Head:** `fix/woa-exception-visibility` @ `5da07e5538de6fc25bb22bbd62a7cec45e19841e`
- **Two commits:**
  1. `e40a29b` — the two root-cause fixes (`08_Exceptions` filter, `PLACEHOLDERS`
     regex) + `Scope_Gate`/`BASUP-01` tagging + initial `QC-WOA-EXC-01` (count-only).
  2. `5da07e5` — strengthened `QC-WOA-EXC-01` to exact key-set equality on
     `(WoA_Role_Column, WoA_Raw_Name, Zone)` plus explicit duplicate detection, after
     review flagged that a bare count match can hide a swap. Factored into a pure
     function (`qc_woa_exc_01`) with 5 dedicated negative-path tests.
- **Required checks on the merge SHA (`5da07e5`), all `success`:** `validate`,
  `Analyze (python)`, `Analyze (javascript-typescript)`,
  `Validate Dashboard Data & Schema`, `Validate HTML Structure & Fixes`,
  `Production Acceptance Gate`. `mergeable_state: clean` before merge.
- Merged via the GitHub merge API with `expectedHeadSha` pinned to `5da07e5` — not a
  stale-SHA merge.

## 3. Full test result

Run twice, independently: once on the PR branch before merge, once from a **fresh
`main` checkout** after merge (`git fetch && git checkout main && git pull`,
confirmed fast-forward, `git status --short` empty before running).

```
174 passed, 1 skipped, 0 failed   (229.02s)
```

Identical both times. 32 of the 174 are incentive-specific (`test_incentive_workbook.py`
+ `test_incentive_identity.py`), re-run separately against a freshly-regenerated
workbook as a second, independent check.

## 4. The governed skip

`tests/test_published_assets_privacy.py::TestPublishedAssetsPrivacy::test_sales_actuals_is_aggregate_only`

```
SKIPPED [1] tests/test_published_assets_privacy.py:62: sales_actuals not built yet
```

**Classification: governed, expected, not a PR #191 concern.** This test's own skip
condition (`sales_actuals.json` not present in this environment) is unrelated to
anything PR #191 touched — it predates this PR, isn't in its diff, and the file it
checks for is a downstream dashboard-publish artifact this sandbox hasn't built.
Confirmed by running the file in isolation: 2 of its 3 tests pass, only this one
skips, for the stated reason.

## 5. QC-WOA-EXC-01

**Rule:** every row in `incentive_working/woa_employee_mapping_register.csv` must
appear in the governed workbook's `08_Exceptions` sheet exactly once, keyed on
`(WoA_Role_Column, WoA_Raw_Name, Zone)` — the same natural key
`build_incentive_identity.py` already aggregates WoA rows on. Checks, in order:
row-count equality, key-set equality (no missing, no extra), and duplicate detection
on both the register and the exception sheet independently. **Severity: BLOCKING** —
`build_incentive_workbook.py` raises `SystemExit` and produces no workbook if any
condition fails.

**Result on this baseline: PASS.** Verified twice — once during PR #191 development,
once again from the fresh-`main` checkout in this record (§6). `qc_woa_exc_01()` is a
pure function with 5 dedicated tests proving the negative path actually fires (a
dropped row, a same-total-count swap, an extra untraceable key, a duplicate on either
side) — see `tests/test_incentive_workbook.py::QcWoaExc01`.

## 6. Register / workbook regeneration (fresh `main`, not the PR branch)

```bash
python3 scripts/build_incentive_identity.py \
  --woa <WOA_APril26_to_July26_working_sheet.csv> --employees <employee master, CSV>
python3 scripts/build_incentive_workbook.py \
  --employees <Employee_wise_grade_for_payment.xlsx> --slabs <INCENTIVE_SLAB.xlsx> \
  --targets <All_India_RKAM_Target_Planning__Compiled_File.xlsx>
```

Output, identical to the pre-merge run:

```
register classification:
  INSUFFICIENT_EVIDENCE      35
  OWNER_RULE_APPROVAL        28
  SOURCE_DATA_FIX_REQUIRED   2
  OWNER_ROW_EXCEPTION        2
  (67 rows total)

workbook: employees 51 | grade VALID 42 | slab rows 85 | target rows 3124 | WoA 67 | exceptions 87
target coverage 77.0% -> Target_Scope_Status UNKNOWN_SCOPE
calculation status: BLOCKED — no payout produced
```

**Generated outputs are stable** — the fresh-`main` regeneration matches the
pre-merge PR-branch regeneration exactly, on both row counts and the classification
breakdown. These outputs are RESTRICTED and gitignored (`incentive_working/`), so
they are not part of this PR's diff; this record documents the run, not the file.

## 7. Git working-tree cleanliness

`git status --short` on fresh `main` at `3ef146a`, before and after the
regeneration in §6: **empty both times** (the regenerated `incentive_working/*`
files are gitignored and don't appear in `git status`). No unexpected mutation to
any tracked file.

## 8. Known unresolved business classifications (unchanged by this PR)

| Classification | Rows | What it means | Next action, and by whom |
|---|---:|---|---|
| `INSUFFICIENT_EVIDENCE` | 35 | No credible employee-master candidate (29 of these are `Scope_Gate = BASUP-01` — see below; the remaining 6 are genuine no-candidate rows, minus the 5 with a manually-found high-confidence candidate not yet built into the algorithm) | MT Ops / HR — supply Employee ID or confirm absence |
| `OWNER_RULE_APPROVAL` | 28 | One clean, exact name+zone candidate, needs a one-line MT Ops confirmation | MT Ops |
| `SOURCE_DATA_FIX_REQUIRED` | 2 | Placeholder values (`VACANT`, `Vacant_S1`), not people | Corrected WoA extract needed |
| `OWNER_ROW_EXCEPTION` | 2 | Two real candidates each, genuinely ambiguous | MT Ops picks one (`Ganesh Khengre`); the other (`Suraj`) is gated by BASUP-01 |

**63 of 67 rows are not code defects.** The engineering work that could close them —
visibility, classification, a governed audit trail — is done as of this baseline.
What remains is business input: `BASUP-01` (are BA Supervisors incentive-eligible? —
29 rows, 538 stores) plus MT Ops confirmation on the 28+2 identity rows.

## 9. Confirmation: unresolved cases require owner/business approval, not inference

No row's `Approval_Status` is anything but `PENDING`. No `Owner_Decision` is set by
any script in this repo. `build_incentive_identity.py`'s own docstring states this
as a guardrail ("Fuzzy similarity is never used to auto-approve an identity: paying
the wrong person is worse than leaving a row open") and PR #191 did not change that
guarantee — it only made every open row *visible*, not resolved.

## 10. Next controlled action

`incentive_working/target_scope_decision_pack.md` (RESTRICTED, gitignored, already
updated with `BASUP-01` in DACI format) is ready to send to MT Leadership / MT Ops.
No further engineering work is needed to unblock that step — it is a business
handoff, not a code task.

## Branch protection / ruleset assessment (verified where stated, not assumed)

This session has no tool that can read GitHub branch-protection/ruleset settings
directly (confirmed repeatedly across this whole engagement — see
`docs/MAIN_BRANCH_PROTECTION_AUDIT.md`). What follows is evidence-based, not a fresh
UI screenshot: it combines (a) the documented Phase 17/18 configuration and (b) fresh
behavioral corroboration from PR #191's own merge in this session.

| Control | Status | Evidence |
|---|---|---|
| PR required before merge | **Configured** (Phase 17), **freshly corroborated** | PR #191 went through the standard PR + merge-API path; no direct push was available or attempted |
| Required CI checks enforced | **Configured** (Phase 17/18), **freshly corroborated** | PR #191's merge required all 6 checks (`validate`, `Analyze (python)`, `Analyze (javascript-typescript)`, `Validate Dashboard Data & Schema`, `Validate HTML Structure & Fixes`, `Production Acceptance Gate`) to report `success` on the exact head SHA before `mergeable_state` became `clean` |
| Branch must be current before merge | **Configured** (Phase 17 ruleset setting: "Require branches to be up to date") | Not independently re-tested in this session against a deliberately stale branch |
| Force push blocked | **Configured** (Phase 17 ruleset setting) | Not independently re-tested this session |
| Branch deletion blocked | **Configured** (Phase 17 ruleset setting) | Not independently re-tested this session |
| Bypass permissions | **None configured** (Phase 17: "No bypass" selected deliberately) | Not independently re-tested this session |

**Recommendation, not acted on:** if a fresh, direct confirmation of the live
ruleset screen is wanted before treating this baseline as fully protected, that's a
repo-owner UI check (`Settings → Rules → Rulesets → Protect main - MT Dashboard
Production`) — this session cannot perform it. No repository protection setting was
modified by this PR or this record.
