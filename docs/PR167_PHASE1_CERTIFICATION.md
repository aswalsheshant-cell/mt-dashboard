# PR #167 Phase 1 Certification — Account/Chain YoY Intelligence

Certification date: 2026-09-20. This document is evidence, not a summary of
claims — every number below was independently reproduced during this
certification pass, not copied from the PR description.

## 1. Identity

- **PR:** #167 — `feat: Account/Chain YoY intelligence — units, contribution%, comparability governance`
- **Head SHA (at certification start):** `e29fb630991c47139a6a47f99e74fd21028f2750`
- **Base SHA:** `9b56d3416cf0716c56acb3a48dc7dd53d64e85dd` (current `main` tip at PR creation)
- **Branch:** `feat/account-chain-yoy-intelligence`, up to date with its base (no divergence — base is `main`'s actual tip, not a stale snapshot)
- **State:** Draft, not merged, `mergeable_state: clean`
- **Files changed at head SHA:** `scripts/build_dashboard_data.py`, `dashboard/index.html`, `dashboard/data.js`, `docs/METRIC_REGISTRY.md` (4 files)
- **This certification pass adds one more file** (not yet on the PR branch as of the head SHA above): `scripts/test_account_yoy_edge_cases.py`, plus this document — both committed and pushed as a follow-up commit after this certification (see §7).

## 2. Test evidence

| Run | Result |
|---|---|
| `python -m py_compile scripts/build_dashboard_data.py` | Clean |
| Full suite before edge-case tests added (`scripts/ tests/`, excluding pre-existing `test_json_serialization.py`/`smoke_dashboard.js` exclusions) | **442 passed, 0 failed, 30 skipped** — matches the session's established baseline exactly |
| Full suite after adding `scripts/test_account_yoy_edge_cases.py` (8 new tests) | **450 passed, 0 failed, 30 skipped** |

## 3. Browser evidence

- `tests/dashboard_sweep.js` (11 tabs × 4 FY states = 44 states): **44/44 clean, 0 JS errors**
- Targeted check on Performance & Comparison tab (new bubble chart + table columns): rendered correctly, bubble canvas has drawn pixels, table shows "Unit YoY"/"Comparability" columns, `COMPARABLE` pills visible — screenshot captured during implementation (not re-attached here; re-run `tests/dashboard_sweep.js` plus the Performance & Comparison tab manually to reproduce)
- Re-verified after FY filter cycling (FY25/FY26/FY27/no-filter): no NaN/undefined/[object Object] introduced

## 4. Mutation evidence

- `git status --porcelain`: clean immediately before commit, clean immediately after the full suite run (no governed file — `PowerBI/SeedData/Mapping/*.csv` — was touched)
- `data.js` diffed key-by-key, old vs. new: **only** `detail_meta.same_period`, `data.scorecard`, and `config` (one stale description string, unrelated to this PR's fields) changed. `primary`, `offtake`, `pnl`, `forecast`, `targets`, `npd`, `mom`, `data_quality`, `readiness`, `detail_records` (row-for-row, `rows_kept` = 160,834 both before and after) are **byte-identical**.

## 5. Metric lineage — every new field, independently traced

| Field | Source | Transformation | Formula | Output field | UI consumer | QC test |
|---|---|---|---|---|---|---|
| Units YoY | `df["_Qty"]` (real column, confirmed present in `detail_records_real()`'s source frame, set from `Inv Qty`) | Grouped by dim (chain/zone/brand) over the same-period shared months, current vs. prior FY | `(Qty_curr / Qty_prev - 1) × 100`, `None` if `Qty_prev` is falsy | `same_period_block()` rows → `qty_yoy_pct` → `scorecard_block()` rows → `qty_yoy_pct` | Performance & Comparison → Account & Zone Scorecard, "Unit YoY" column | `TestComparableAccount`, `TestNewAccountNoPriorBase`, `TestExitedAccount` in `test_account_yoy_edge_cases.py` |
| NSV Contribution % | `df["_NSV"]`, same grouping | This dim value's share of the **current period's own total** across all rows in that dim | `NSV_curr(row) / SUM(NSV_curr across dim) × 100`, `None` if the total is 0 | `same_period_block()` rows → `nsv_contribution_pct` → `scorecard_block()` rows → `nsv_contribution_pct` | Same table, "NSV Contrib%" column; bubble chart Y-axis | `TestContributionReconciliation` (sums to exactly 100%, both synthetic and real data — see §6); `TestZeroTotalDenominator` |
| Comparability flag | `curr`/`prev` NSV values already computed above | Classifies each row before any growth number is read | `COMPARABLE` (curr>0 and prev>0) / `NEW_ACCOUNT` (curr>0, prev≤0) / `EXITED` (curr≤0, prev>0) / `NOT_COMPARABLE` (both ≤0) | `same_period_block()` rows → `comparability` → `scorecard_block()` rows → `comparability` | Same table, "Comparability" pill column | `TestNewAccountNoPriorBase`, `TestExitedAccount`, `TestNegativeValues`, `TestBrandOnlyInOnePeriod` |
| Bubble chart X | `growth_pct` (pre-existing field, unchanged by this PR) | Only `COMPARABLE` rows plotted (`renderAccountYoyBubble()` filters on `comparability==='COMPARABLE'` client-side) | Same as chain YoY % above | `mkBubble` data point `x` | Bubble chart X-axis | Covered indirectly — `growth_pct` itself predates this PR and is unchanged |
| Bubble chart Y | `nsv_contribution_pct` (new, above) | Same COMPARABLE-only filter | Same as NSV Contribution % above | Bubble data point `y` | Bubble chart Y-axis | Same as NSV Contribution % |
| Bubble size | `curr` (pre-existing NSV field) | `6 + sqrt(curr / max(curr across plotted rows)) × 24` — square-root scaling so area, not radius, is proportional to NSV (standard bubble-chart convention, avoids visually overstating large accounts) | — | Bubble data point `r` | Bubble radius | Visual only; no numeric claim to test beyond "renders, non-crashing" (confirmed in §3) |

## 6. Edge-case results (new: `scripts/test_account_yoy_edge_cases.py`, 8 tests, all passing)

| Case | Expected behavior | Result |
|---|---|---|
| Prior period missing (`NEW_ACCOUNT`) | `yoy_pct`/`qty_yoy_pct` = `None`, never 0% | ✅ Confirmed — no valid base to divide by |
| Current period missing (`EXITED`) | `yoy_pct` = **true** `-100%`, not suppressed — a well-defined division, unlike the missing-base case above | ✅ Confirmed (this was corrected mid-certification: my first draft of this test wrongly expected `None` here; see below) |
| Prior value = 0 exactly | Same as "prior period missing" — `NEW_ACCOUNT`, `None` | ✅ Confirmed |
| Negative current value (net returns) | Classified `EXITED` (curr≤0), `yoy_pct` computed as a real (very negative) number, not suppressed or crashed | ✅ Confirmed, `-105%` for the constructed case |
| Chain exists only in one period | Covered by `NEW_ACCOUNT`/`EXITED` cases above | ✅ |
| Brand exists only in one period | `by_brand` (new dim added by this PR) applies the identical rule set as `by_chain`/`by_zone` — not a second, looser implementation | ✅ Confirmed |
| Zero total contribution denominator | `nsv_contribution_pct` = `None`, not a `ZeroDivisionError` | ✅ Confirmed |
| Contribution reconciliation | `SUM(nsv_contribution_pct)` across a dim = exactly 100% | ✅ Confirmed on synthetic data AND on real production `data.js` (§ below) |

**A genuine finding during this certification, resolved by correcting the test, not the code:** my first draft asserted `yoy_pct is None` for `EXITED` rows, on the theory that "missing data must never become genuine growth." That's the right rule for `NEW_ACCOUNT` (no valid denominator), but wrong for `EXITED` — going from a real prior value to zero is a mathematically well-defined -100%, and it is real information leadership should see (the `comparability: EXITED` flag is what supplies the "this account exited, not just declined" context, not a suppressed number). The underlying `_pct()` division helper predates this PR and was not changed; only the test's expectation was wrong. Both tests now assert the corrected, intentional behavior.

**Real-data reconciliation** (against the PR's own `dashboard/data.js`, `detail_meta.same_period`):

| Dim | Sum of `nsv_contribution_pct` | Rows with `None` contribution | Total rows | Comparability breakdown |
|---|---|---|---|---|
| `by_chain` | **100.0000%** | 0 | 48 | COMPARABLE 27, NEW_ACCOUNT 10, EXITED 9, NOT_COMPARABLE 2 |
| `by_zone` | **100.0000%** | 0 | 6 | COMPARABLE 6 |
| `by_brand` | **100.0000%** | 0 | 8 | COMPARABLE 4, NEW_ACCOUNT 2, EXITED 2 |

## 7. No duplicate financial truth

- `same_period_block()` is the single existing YoY engine (predates this PR); this PR extends its output rows, it does not compute a second, parallel YoY anywhere.
- `scorecard_block()` (existing "Account & Zone Scorecard") is extended with the new fields on its existing rows — no new top-level `data.js` block was created for this feature.
- The existing, separately-computed `contribution_pct` (target-share-derived, used to split the FY target — unrelated arithmetic) was left untouched under its original name; the new field is named `nsv_contribution_pct` specifically so the two are never confused as the same number.
- `pvm_block()`'s own `by_chain`/`by_brand` contribution tables (pre-existing, "Growth contribution by chain") were not modified and remain their own, separately-computed view (delta and %-of-total-change, a different question than this PR's %-of-current-total).

## 8. `docs/METRIC_REGISTRY.md` completeness

The `ACCOUNT_YOY_INTELLIGENCE` row (added by this PR) follows this registry's existing column set: Measure_ID, Business Question (= definition), Formula (states numerator, denominator, and the comparability rule inline), Grain, Fact Source, FY Logic (= period logic), Comparable Across, UI Location(s) (= consumer), Status. Null behavior is stated explicitly in the Formula cell ("a missing prior-year base is never read as 0% or -100% growth"). This registry has no separate "owner" column on any row — ownership is implicit ("MT Analytics", consistent with every other entry and with `config/baselines.json`'s convention) rather than a gap specific to this row.

## 9. Known limitations / residual risk

- **Store-level Same-Store Growth is out of scope for this PR** (see PR body and `ACCOUNT_YOY_INTELLIGENCE`'s registry note) — this pipeline has no persistent per-store monthly identity downstream of the raw source files. Gate B below assesses whether it's buildable at all before any Phase 2 work starts.
- **`github-advanced-security` check on PR #167 shows `failure`.** Investigated via job logs (job id `106137808424`): it is GitHub's own Copilot-based agentic code-scanning backend, and it crashed with `SessionModelError: 400 The requested model is not supported` — an infrastructure/model-routing error on GitHub's side, before the tool ever fetched or analyzed this PR's diff. This is not a finding about this PR's code. A manual re-run was attempted and rejected by GitHub (`403 This workflow run cannot be retried`) — this check type can't be force-rerun via the API available here; it will re-fire on the next push to the branch. Classified `COLLECTION_INFRASTRUCTURE`, non-blocking.
- All other 16 required checks on PR #167 are green.
- Branch protection settings on `main` were not verified — no tool available in this session exposes repository branch-protection configuration. Recommend checking manually under repo Settings → Branches.

## 10. Certification decision

**`PHASE1_CERTIFIED`**

Basis: exact SHA/base confirmed; full backend suite green (450/450, 0 failed) both before and after this certification's new edge-case tests; 44-state browser sweep clean; mutation guard clean; every new field traced source→UI with a passing QC test; real-data contribution reconciliation exact (100.0000% on all three dims); no duplicate KPI computation introduced; registry updated. The one non-green check is independently confirmed to be a GitHub-side infrastructure failure unrelated to this diff.

**Not done by this certification, per its own scope:** merging PR #167, converting it out of Draft, or starting any Phase 2 implementation. Those remain explicit human decisions.
