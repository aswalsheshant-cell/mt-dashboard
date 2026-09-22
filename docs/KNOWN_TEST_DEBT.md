# Known Test Debt Register

Created 2026-09-22, Section C of the Financial & Period Integrity Baseline pass.
Formalizes the 6 pre-existing failures in `answer_governance/test_governance.py`
that were previously being accepted informally as "the same six failures" on every
run. Each row is root-caused individually — they are **not** one problem, they are
three unrelated problems that happen to share one symptom (a red `pytest` line).

**Scope note, checked first:** `answer_governance/` (the module these tests cover)
has **zero production consumers** today — confirmed by grep across
`scripts/*.py`, `dashboard/index.html`, and every `.github/workflows/*.yml`. It is
not called by `build_dashboard_data.py`, not read by the dashboard, and not wired
into any CI gate. Every defect below therefore has **zero current business blast
radius** — the impact column states what it would be if/when this module is wired
into something users see, not what it is today.

**Independence from PRs #171-177:** none of the 6 failures touch any file changed
by PRs #171 through #177 (the six branches queued for Section D integration
certification), and none of those PRs touch `answer_governance/`. Confirmed by
`git diff --stat` of each PR against `main` containing no `answer_governance/`
path. These failures are pre-existing debt, not something the current PR batch
introduced or could fix as a side effect.

## Disposition legend

- **FIX** — real defect in production code (`answer_governance/evidence.py`);
  needs a dedicated root-cause fix in its own branch/PR, not a quick patch here.
- **FIX-TEST** — the test's own assertion is wrong (asserts something that
  structurally cannot be true per this project's own documented data model);
  the fix is to correct the test, not the code it exercises.
- **XFAIL** — code and test are both "correct" in isolation, but the test pins a
  literal snapshot of live, legitimately-growing data; mark `xfail(strict=True)`
  and refresh the literal in a follow-up rather than letting it silently rot.

| Test ID | Test | Root Cause | First Known Failing Commit | Business Impact | Owner | Disposition | Evidence | Target Closure |
|---|---|---|---|---|---|---|---|---|
| TD-01 | `TestEvidenceBuilding::test_primary_q1_fy27_confirmed_or_high` | **Real code bug.** `_primary_evidence()` (`answer_governance/evidence.py:65-172`) validates period *completeness* against the requested `period` (via `check_period()`), but the returned numeric **value** is always `fyx.get("nsv")` — the whole-FY-so-far total — never sliced down to the requested period's months. Asking for "Q1 FY27" and "FY27" (no period) return the identical value. Verified independently: `fyx_primary.FY27.monthly_canon` = `[5076.86, 4415.74, 4167.38, 4921.31, 3658.3]` for Apr-Aug; Apr+May+Jun = 13,659.98 exactly matches the test's expected literal, while the code actually returns the Apr-Aug sum, 22,239.59 | Assertions authored in `b61d84e` (2026-08-26). The underlying code bug has existed since that commit, but was symptomatically invisible at the time — FY27 had ~1 month of real data loaded then, so "whole FY27 so far" ≈ "Q1" by coincidence (see TD-04/05, whose FY27 literal from the same commit, 11,438.72, matches TD-03's Q1 expectation exactly for the same reason). The discrepancy became visible only as later monthly rebuilds added April-August; the specific commit where it first diverged was not bisected (out of scope for this pass) | MEDIUM if ever wired into a leadership-facing answer surface: any "Q1 FY27 Primary" query would silently return the full FY-to-date figure instead, exactly the "numerator spans more months than the period label claims" pattern this project's FY audits specifically watch for. ZERO today — module has no consumer | Unassigned | **FIX** | Reproduced directly: `build_evidence("primary","Q1","FY27",dash).source_periods` returns 5 months (`April`...`Aug`) while `.coverage.available_months` (from `check_period`) correctly returns only 3 (`April`,`May`,`June`) — the function's own two code paths already disagree with each other, independent of the test's literal | Dedicated branch: slice `fyx["monthly_canon"]` (or per-chain/per-zone monthly arrays) to the `period`-derived month list before summing, for every non-`"FY"` period value; add a test asserting `source_periods` and `coverage.available_months` are always the same list |
| TD-02 | `TestEvidenceBuilding::test_offtake_q1_fy27` | **Real code bug, same class as TD-01.** `_offtake_evidence()` (`answer_governance/evidence.py:174-`) reads `val = o.get(f"total_{fy_tag.lower()}")` — the whole-FY total — regardless of `period`, then separately computes coverage via `check_period()`. Same two-code-paths-disagree symptom as TD-01 | Same commit, `b61d84e` (2026-08-26); same masking mechanism (FY27 had ~1 month of data at authoring time, so the bug was invisible) | Same as TD-01 — MEDIUM if wired in, ZERO today | Unassigned | **FIX** | `build_evidence("offtake","Q1","FY27",dash).source_periods` returns 5 months while `.coverage.available_months` returns 3, mirroring TD-01 exactly | Same branch as TD-01 (both evidence builders share the identical defect pattern and should be fixed together with one shared helper, not two separate patches) |
| TD-03 | `TestEvidenceBuilding::test_primary_fy25_preagg` | **Test-authoring error, not a code bug.** The test expects `build_evidence("primary","FY","FY25",dash).value == 23331.97` — but per this project's own **THE ONE FY RULE** / three-measures documentation (`CLAUDE.md`, `docs/DATA_AVAILABILITY_MATRIX.md`), **Primary billing for FY25 does not exist in any source file this repo has** — only Distributor Secondary does (FY25 Distributor Secondary = ₹23,332.36 L per `CLAUDE.md`'s reference table, ~0.39L rounding-different from the test's 23,331.97 literal — the same number, mislabeled). `_primary_evidence()`'s `BLOCKED` / "Primary FY25 value not found" response is the **honest, correct** governance answer given real data availability; the test's expectation is what's wrong | `b61d84e` (2026-08-26) — likely never passed; no evidence in git history that `primary.nsv_fy25` was ever a real key in any committed `data.js` | ZERO — the code's actual behavior (refuse the claim, cite the reason) is exactly what this project's "never fabricate a number to fill a genuine gap" rule requires. Fixing the *test* to match reality closes this with no code change | Unassigned | **FIX-TEST** | `dashboard/data.js`'s live `primary` block has no `nsv_fy25` key (confirmed by direct inspection: `sorted(dash['primary'].keys())` = `by_brand, by_chain, by_channel, by_zone, coverage_note, coverage_withheld, fy_tags, month_labels, monthly_fy26, mrp_fy26, n_brands, n_chains, nsv_fy26, yoy` — no FY25 key at all); `docs/DATA_AVAILABILITY_MATRIX.md`'s 29-month coverage matrix documents FY25 Primary as unavailable by design | Rewrite the assertion to expect `ConfidenceStatus.BLOCKED` with a reason naming the missing source, matching how the project treats every other genuinely-unavailable period (see `CLAUDE.md`: "name the exact missing source file instead" of fabricating) |
| TD-04 | `TestPipelineIsolation::test_primary_totals_unchanged` | **Same test-authoring error as TD-03, at the raw-key level.** Asserts `dash["primary"]["nsv_fy25"] == 23331.97` directly against the live `data.js` fixture — `nsv_fy25` has never been a valid key of the `primary` block (see TD-03); this is a `KeyError`, not a value mismatch | `b61d84e` (2026-08-26) | ZERO | Unassigned | **FIX-TEST** | Same evidence as TD-03 | Drop the `nsv_fy25` assertion (or replace with `"nsv_fy25" not in dash["primary"]` as an explicit, honest invariant); keep the `nsv_fy26` assertion, which is correct and currently passes as part of the same test |
| TD-05 | `TestPipelineIsolation::test_offtake_totals_unchanged` | **Same class as TD-03/04.** Asserts `dash["offtake"]["total_fy25"] == 21840.0` — Offtake FY25 does not exist in this repo's source data either (per the same three-measures table: Offtake FY26 is the earliest Offtake figure available); `total_fy25` is not a key of the live `offtake` block (confirmed: `sorted(dash['offtake'].keys())` has no `total_fy25`, only `secondary_total_fy25` — the Distributor Secondary measure, again conflated with Offtake) | `b61d84e` (2026-08-26) | ZERO | Unassigned | **FIX-TEST** | Same class of evidence as TD-03/04 — direct key inspection of the live block | Drop the `total_fy25` assertion (or assert its absence explicitly); the `total_fy26`/`total_fy27` assertions in the same test function are a separate, additional problem (see TD-06 note below — `total_fy27` is stale in the same way TD-01/02's literals are, since it was authored the same day from the same ~1-month-old FY27 snapshot) |
| TD-06 | `TestPipelineIsolation::test_bc_unchanged` | **Genuine test debt (stale literal), not a bug.** Asserts `dash["reliance_bc"]["total"] == 943.68`. Live value is now 7,144.66 — real, legitimate growth: `reliance_bc.fy_tags` now covers `['fy26','fy27']` (more real Reliance Brand Counter months loaded since 2026-08-26) vs. whatever narrower window existed at authoring time. Not a code defect — a snapshot literal that was never designed to track a live, monthly-growing fixture | `b61d84e` (2026-08-26) | ZERO — `include_in_overall_offtake == False` (the other half of this same assertion) still passes, confirming the actual double-count-prevention logic this test cares about is intact; only the raw total literal is stale | Unassigned | **XFAIL** | `bc.get('total')` = 7144.66 vs. expected 943.68; `bc.get('include_in_overall_offtake')` still `False` as asserted | Replace the hardcoded total with either (a) a tolerance-free structural check (`total > 0` and `include_in_overall_offtake is False`) that can't go stale as real data grows, or (b) a computed expectation derived from `reliance_bc.monthly`/`fy_tags` at test time rather than a frozen literal |

## Enforcement — new vs. known failures

All 6 tests above are now marked `@pytest.mark.xfail(reason="TD-NN, see docs/KNOWN_TEST_DEBT.md", strict=True)`
in `answer_governance/test_governance.py`. Under `strict=True`:

- **Known failure continues failing** → reports as `xfail` (yellow, non-blocking, but
  visible in the run summary — never silently green, never silently red).
- **Any of these 6 unexpectedly starts passing** (e.g., someone fixes the underlying
  code without updating this register) → reports as `XPASS`, which `strict=True`
  turns into a **hard failure** — surfaces for review rather than quietly
  disappearing. Whoever fixes a TD-NN item must close it here (move the row to a
  "RESOLVED" state, matching `docs/FAILURE_MODE_REGISTER.md`'s convention) in the
  same change, not just delete the marker.
- **Any test not listed here starts failing** → an ordinary, blocking failure —
  no marker suppresses it. This register only ever grows by deliberate addition,
  never by a new failure quietly joining the "known" set unnoticed.
- **A genuinely new test debt item** must get its own `TD-NN` row (root cause,
  evidence, disposition, target closure) before a marker referencing it is added —
  never add `xfail` first and document later.
