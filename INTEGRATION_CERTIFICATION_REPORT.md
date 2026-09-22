# Integration Certification Report — Financial & Period Integrity Baseline v1

**Date:** 2026-09-22
**Integration branch:** `integration/baseline-v1-certification` (temporary, disposable — do not merge this branch itself; use it only to reference the evidence below)
**Base:** `origin/main` @ `08693d42d993cfa95336d86d74f167d895bf4da6` (PR #157 merged)
**Scope:** all 9 open PRs from this session's FY-integrity audit, combined into one working tree and tested together — not six/nine isolated green checkmarks.

**This report does not merge anything.** It is evidence plus a recommended dependency order for human approval, per this pass's governing instruction.

---

## 1. What was combined

| # | PR | Branch | FM/TD | Files changed |
|---|----|--------|-------|----------------|
| 1 | [#171](https://github.com/aswalsheshant-cell/mt-dashboard/pull/171) | `fix/fy27-same-period-comparison` | FM-18 | 3 files, +152/-4 |
| 2 | [#172](https://github.com/aswalsheshant-cell/mt-dashboard/pull/172) | `chore/chain-mapping-policy-fm19-fm20` | FM-19, FM-20 | 4 files, +449/-0 |
| 3 | [#173](https://github.com/aswalsheshant-cell/mt-dashboard/pull/173) | `fix/mapping-health-fy-filter` | FM-21 | 3 files, +89/-2 |
| 4 | [#174](https://github.com/aswalsheshant-cell/mt-dashboard/pull/174) | `fix/primary-offtake-gap-fy-filter` | FM-22 | 3 files, +79/-2 |
| 5 | [#175](https://github.com/aswalsheshant-cell/mt-dashboard/pull/175) | `fix/partial-refresh-staleness-fm17-followup` | FM-17 (follow-up) | 3 files, +114/-1 |
| 6 | [#176](https://github.com/aswalsheshant-cell/mt-dashboard/pull/176) | `fix/targets-block-fy-shape-mismatch` | FM-23 | 3 files, +128/-1 |
| 7 | [#177](https://github.com/aswalsheshant-cell/mt-dashboard/pull/177) | `fix/sidecar-pipeline-mock-data-guard` | FM-24 | 3 files, +216/-27 |
| 8 | [#178](https://github.com/aswalsheshant-cell/mt-dashboard/pull/178) | `fix/pnl-cm2-tot-fy-filter` | FM-25 | 5 files, +158/-14 |
| 9 | [#179](https://github.com/aswalsheshant-cell/mt-dashboard/pull/179) | `docs/known-test-debt-register` | TD-01..TD-06 | 2 files, +68/-0 |

All 9 were on the original list or created by this same pass's own Section B/C work (#178, #179 — the P&L audit and the test-debt register the user's own instructions asked for). None have been merged; all remain open, draft PRs on `main`.

**Merge order used:** #172 → #173 → #174 → #171 → #175 → #176 → #177 → #178 → #179 (the user's proposed order for the original six, then #177/#178/#179 appended — all three are independent of the first six and of each other).

---

## 2. Business KPI affected per PR

| PR | Business KPI / surface affected | Nature of change |
|---|---|---|
| #171 | Performance & Comparison — article-level YoY (SubCategory/Range/PackSize/Article) | Fixes a direction-reversed YoY (Face Cleanser: -18.1% shown vs. true +113.1%) |
| #172 | Chain mapping governance (14 business-owner-approved decisions recorded) | Adds `config/chain_mapping_policy.yml`; does **not** change `_Chain` yet (FM-19 still OPEN, dead-code wiring not done) — zero `data.js` impact, confirmed below |
| #173 | Commercial Analytics — Chain Mapping Health KPI cards | FY filter now actually scopes completeness/mapped/unmapped % |
| #174 | Channel & Chain Performance — Primary-Offtake Gap card/chart | FY filter now actually scopes the shown FY window |
| #175 | Targets/insights/mapping_health/mom/scorecard/pvm/profitability/npd/readiness (whole derived layer) | Closes staleness gap for `--primary-only`/`--offtake-rebuild`/`--offtake-patch` refresh modes (code path only — no `data.js` diff today since no such partial refresh has run since) |
| #176 | Executive Cockpit / Demand & S&OP — FY Target, Achievement % | Fixes a dormant ~92% target-understatement bug that would trigger the next time the real target `.xlsb` is supplied (CSV fallback currently in use, `data.js` unaffected today) |
| #177 | Store Audit Scorecard / Supply Chain & Inventory (sidecar JSONs) | Closes a mock-data landmine in the daily sidecar refresh cron; no `dashboard/data.js` involvement (separate JSON files) |
| #178 | P&L tab — TOT%/CM2 KPI cards | FY filter now actually scopes NSV/TOT%/CM2 KPI cards (previously always FY26+FY27 combined); **the only PR in this batch that changed `dashboard/data.js`** |
| #179 | None (test governance only) | No dashboard-facing change; formalizes 6 pre-existing `answer_governance` test failures |

---

## 3. Tests added, per PR

| PR | New regression tests |
|---|---|
| #171 | `tests/test_fy_same_period_guard.js` (15 tests) |
| #172 | `tests/test_chain_allocation_no_fabrication.py` (structural) |
| #173 | `tests/test_mapping_health_fy_filter.js` (5 tests) |
| #174 | `tests/test_pog_gap_fy_filter.js` (5 tests) |
| #175 | `tests/test_partial_refresh_wiring.py` (6 tests, structural) |
| #176 | `tests/test_targets_block_shape_normalization.py` (5 tests) |
| #177 | `tests/test_sidecar_pipeline_fails_closed.py` (4 tests) |
| #178 | `tests/test_pnl_cm2_tot_fy_filter.js` (4 tests) |
| #179 | none new — adds `xfail` markers to the 6 existing `answer_governance` failures |

---

## 4. Combined-state validation (all 17 points, run against the integration branch, not six isolated branches)

| # | Check | Result |
|---|---|---|
| 1 | Full Python suite (`pytest tests/ answer_governance/`) | **202 passed, 1 skipped, 6 xfailed, 0 failed**, exit 0 |
| 2 | Known-failure classification | 6 `xfail` = exactly TD-01..TD-06, **0 unexpected `XPASS`**, 0 unlisted failures |
| 3 | Browser/dashboard sweep (`tests/dashboard_sweep.js`, 11 tabs × 4 FY states) | **44/44 pass, 0 JS errors** |
| 4 | `data.js` schema/JSON validation (`scripts/ci_validate_datajs.py`) | Valid JSON; 100.0% detail coverage; **7/7 baseline invariants hold**; only the known, pre-existing FM-05 WARN (`meta`/`metadata` divergence — unrelated, documented) |
| 5 | NaN/Infinity scan (raw token scan of `data.js`) | **0 occurrences of either** |
| 6 | Primary reconciliation (`primary.nsv_fy26` vs Σ `by_chain[].fy26`) | 32,900.36 vs 32,900.36 — **0.0000% variance** |
| 7 | Offtake reconciliation (`offtake.total_fy26` vs Σ `by_chain[].fy26`) | 31,119.87 vs 31,119.90 — **0.0001% variance** |
| 8 | Primary↔Offtake comparison block | `primary_offtake_gap` present, `fy26`/`fy27` keys populated |
| 9 | FY26-vs-FY27 comparable-period checks | `test_fy_same_period_guard.js` 15/15, `test_pnl_cm2_tot_fy_filter.js` 4/4 |
| 10 | Mapping-health checks | `test_mapping_health_fy_filter.js` 5/5; `mapping_health.by_fy` = `['FY26','FY27']` |
| 11 | Target reconciliation | `targets.source` = CSV fallback path (confirmed); FM-23 fix present in code, correctly dormant (no `.xlsb` supplied to this build) |
| 12 | Scorecard/PVM/MoM reconciliation | All three blocks present and non-empty (`scorecard`, `pvm`, `mom`); exercised live by the 44-state sweep with 0 errors |
| 13 | NPI cohort regression | `tests/test_npi_filter_aware.js` **22/22**; `npd` block present with expected keys |
| 14 | Inventory period-contract tests | Section A of this pass already certified this area clean (no code changed since; not re-litigated) |
| 15 | P&L FY-propagation tests | `tests/test_pnl_cm2_tot_fy_filter.js` **4/4** |
| 16 | Release-gate execution | `ci_validate_datajs.py` PASS; the FM-25 rebuild's own `AUTOMATED RELEASE GATE REPORT` scored **10/10** at build time |
| 17 | Git diff / tracked-file mutation inspection | See §5 below |

`tests/test_contribution_grouping.js` (10/10) also re-run clean as an adjacent-regression check (FM-18's own stated validation).

---

## 5. Git diff / mutation inspection — did anything unintended change?

- **Only PR #178 touched `dashboard/data.js`** in this entire batch. Confirmed by diffing each of the other 8 branches against its own merge-base: `git diff --stat <merge-base> <branch> -- dashboard/data.js` returns empty for all 8. This matches each PR's own stated status (FM-19/20 dead-code-not-wired, FM-17-followup/FM-23 code-path-only-dormant, FM-24 touches separate sidecar JSONs, not `data.js`).
- **The combined integration branch's `data.js` differs from `origin/main`'s in exactly one top-level key: `tot`** — and within `tot`, only the new `mrp` field added to each `monthly` row (FM-25). Every other top-level block — `primary`, `offtake`, `cm2`, `targets`, `mapping_health`, `scorecard`, `pvm`, `mom`, `npd`, `readiness`, `detail_meta`, `alloc`, everything — is **byte-identical** to `origin/main`.
- **FY25/FY26 baselines explicitly diffed and unchanged**: `primary.nsv_fy26` = 32900.36 both before and after; `offtake.total_fy26` = 31119.87 both before and after; `cm2.total_nsv` = 55140.26 both before and after.
- **`FAILURE_MODE_REGISTER.md` merge conflicts** (expected — 6 of the 9 branches append a new row to the same table) were resolved manually, additively, on every merge: every branch's own FM-NN row was kept, nothing was dropped or overwritten. Verified by `grep -c "^| FM-"` before/after each merge step matching the expected running count, and a final scan confirming zero leftover `<<<<<<<`/`=======`/`>>>>>>>` markers anywhere in the tree.
- One pre-existing, **out-of-scope** documentation defect was noticed but deliberately not touched: `FAILURE_MODE_REGISTER.md`'s FM-17 row is nested inside the wrong table (the 3-column "Error-to-pattern routing" table instead of the main 9-column FM table) — an artifact from before this session, unrelated to any of the 9 PRs here, and fixing it would be scope creep against this pass's "stop expanding scope" instruction. Flagged here for a future small doc-only PR.

---

## 6. Residual risk

| Risk | Severity | Status |
|---|---|---|
| FM-19 (chain-mapping overrides recorded but not applied to `_Chain`) | MEDIUM | Explicitly OPEN in the register; #172 only records the decisions, doesn't wire them — no regression, just not-yet-delivered value |
| FM-16A (real `Dist_primary_cont_based_on_secondary_MOM.xlsx` still not supplied) | LOW | Unrelated to this batch; pre-existing, external dependency |
| TD-01/TD-02 (`answer_governance` period-value slicing bug) | MEDIUM if the module is ever wired into production; **ZERO today** (no consumer) | Documented, `xfail`-gated, not fixed in this pass (correctly out of scope — separate module) |
| `FAILURE_MODE_REGISTER.md`'s FM-17 mis-nested row (doc formatting only) | LOW | Pre-existing, noted above, not fixed here |
| Large `dashboard/data.js` (66MB+) triggers a GitHub file-size warning on push | LOW/cosmetic | Known, unrelated to correctness; not an LFS migration in scope here |

No new risk was introduced by combining these 9 PRs beyond what each already carried independently — every reconciliation, sweep, and full-suite run above was run **against the combined tree**, not assumed from each PR's isolated CI.

---

## 7. Recommended merge order (for human approval — nothing has been merged)

1. **#172** (chain-mapping policy — additive config, zero behavior change)
2. **#173** (FM-21 mapping health FY filter)
3. **#174** (FM-22 primary-offtake gap FY filter)
4. **#171** (FM-18 same-period YoY guard)
5. **#175** (FM-17 follow-up — partial-refresh wiring)
6. **#176** (FM-23 targets shape fix — dormant, safe)
7. **#177** (FM-24 sidecar pipeline guard — independent surface)
8. **#178** (FM-25 P&L FY filter — the only one carrying a `data.js` change; merge after the others so its `data.js` rebuild is the final one and doesn't need to be redone)
9. **#179** (test-debt register — no dashboard code, safe last or first)

This order matches the sequence actually exercised in this certification (§1), so it's not just a theoretical recommendation — it's the exact order already proven to merge cleanly and pass the full combined-state gate above.

---

## 8. Release decision

**Recommendation: all 9 PRs are individually mergeable and jointly consistent.** The combined state:
- Introduces zero regressions across 202 Python tests + 44 dashboard-sweep states + 60 JS regression-test assertions across 6 dedicated FY/NPI/contribution-grouping suites.
- Leaves FY25/FY26 baselines byte-identical to `main`.
- Changes `data.js` in exactly one, fully-audited, minimal way (FM-25's `tot.monthly[].mrp` field).
- Correctly classifies pre-existing test debt (6 items) as non-blocking and visible rather than silently ignored or newly-blocking.

**This is a recommendation for human review, not an authorization to merge.** Per this pass's governing instruction: do not merge anything without explicit approval.
