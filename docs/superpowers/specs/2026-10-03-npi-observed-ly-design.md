# Provisional NPI first-observed-sale comparison design

Date: 2026-10-03  
Repository: `aswalsheshant-cell/mt-dashboard`  
Status: design for review; no dashboard implementation or B5 sign-off

## Intent and boundary

Leadership needs a usable FY27 versus FY26 view of new-product activity without presenting incomplete FY26 launch history as confirmed NPI growth. The owner approved a phased repair: first add a separately labeled, equal-window **provisional observed first-sale comparison** to HTML; then repair the Power BI data/model foundation and add NPI parity; then fix proven HTML export and drill gaps. Raw financial rows, approved totals, the existing cohort cards, and the blocked B5 status must be preserved.

This spec covers the first phase and defines the cross-dashboard contract the later phases must use. The later Power BI and HTML gaps require focused specs/plans after this phase. The repository is the available Power BI source: its checked-in report definition has one Finance page; the manual page guide does not establish that more live Desktop pages exist.

## Evidence and problem

`scripts/build_dashboard_data.py` builds NPI at Chain × EAN, falling back to Chain × Article only when EAN is absent. First sale requires NSV > 0 **and** Qty > 0. March first sales carry into the next reporting FY. The April 2025 source boundary leaves 2,326 pairs `boundary_unknown`, excluded from NPI counts but retained in the source. FY26 has 3,102 counted launches, all `observed_only`; FY27 has 1,216, including 1,076 operationally confirmed and 140 `observed_only`. The 12-month status is an operational lookback rule, not proof of first-ever launch.

`npd_block()` currently stores `yoy_npi_nsv_growth_pct = -71.17%` for FY27 by comparing FY26 full-year cohort NSV ₹2,636.56 lakh with FY27 April–August cohort NSV ₹760.15 lakh. `dashboard/index.html` hides the number because FY26 is partial, but the payload remains unsafe for a future consumer or a later change to the confidence gate. Equal April–August cohort performance alone is also not comparable: FY26 April boundary pairs are excluded while FY27 April entrants and 140 March carry-forward pairs are included. A separate first-observed activity selection is needed.

## Chosen comparison contract

For the current April 2025–August 2026 dataset, the common eligible months are **May, June, July, August** in each FY. The dataset's first month (April 2025) is excluded on *both* sides, even though April 2026 has history. March carry-forward entries are excluded on both sides. This makes both the admission months and performance months identical. When data grows, the builder must derive common months from actual source coverage and exclude the earliest dataset-boundary month; it must not assume four months or use a later FY's unmatched months. If source coverage is incomplete or no common eligible month remains, the comparison is unavailable with a reason, never zero or a carried-forward value.

A candidate is one Chain × EAN pair (Chain × Article fallback if EAN is missing) whose **first valid commercial sale in the whole available history** occurs in a common eligible month of the corresponding FY. Cohort membership is computed before dashboard filters and never reassigned by them. Sum all Primary NSV and Qty rows for admitted pairs within the common eligible reporting months of their own FY, including legitimate negative adjustments and returns; do not use NSV > 0 as a later performance-row filter. `active_count` means admitted pairs with at least one positive-NSV performance row in that window. The display must retain each side's `confirmed` and `observed_only` counts. Selection never changes existing NPI cohort totals, FY contribution, or source records.

The builder publishes a distinct `observed_first_sale_comparison` payload under `npd`, with: source coverage, base/current FY, compared month names, grain and admission rule, for each side pair count/active count/NSV/Qty/confidence counts, NSV delta and percentage when the prior NSV is nonzero, `status="provisional"`, and a human-readable caveat. Values must be calculated from the canonical detail records, not from rounded displayed cohort totals. Pair IDs in the existing `by_fy` launch list support filter-aware browser recomputation; the new payload's unfiltered totals are the oracle. The JSON must not reuse `yoy_npi_nsv_growth_pct` or `yoy_comparison_valid` to carry the provisional number.

Unfiltered expected snapshot, rounded for presentation only:

| May–August first-observed activity | FY26 | FY27 | FY27 change |
|---|---:|---:|---:|
| Admitted pairs | 2,042 | 824 | −1,218 (−59.65%) |
| Active pairs | 2,042 | 824 | −1,218 |
| Primary NSV | ₹460.86 lakh | ₹667.36 lakh | +₹206.50 lakh (+44.81%) |
| Confidence counts | 0 confirmed; 2,042 observed-only | 824 confirmed; 0 observed-only | unequal evidence depth |

These are acceptance fixtures for the current source snapshot, not constants in product code. FY26's ₹460.86 lakh differs from the existing full-cohort April–August ₹436.94 lakh because the analytical pair/month selection differs; negative rows remain present. The provisional value describes **first-observed activity**, not confirmed NPI growth or proof of launch novelty. FY26 entrants have only 1–4 months of prior source history while FY27 entrants have 13–16.

## Confirmed YoY gate and presentation

The existing “YoY NPI NSV growth” card stays blank for FY27. Its explanatory text must identify the unequal period and confidence/admission limitations. No numeric confirmed YoY may be exposed in a public metric field unless both FYs have: matching reporting months, matching source/grain/admission rules, complete prior base, and every counted pair meeting the approved confidence rule. A later authoritative launch master could change the confidence decision only through an approved governance change. Preserve current raw cohort figures; remove or null the unsafe `yoy_npi_nsv_growth_pct` when these gates fail, and add a machine-readable invalid reason. Do not replace it with the provisional percentage.

In Commercial Analytics, place a distinct **“Provisional first-observed-sale NSV, May–Aug”** comparison beside or below the existing cohort view. Show both FY amounts, the signed delta and percentage, pair counts, confidence mix, exact compared months, and a short caveat directly with the metric. Tooltip/detail text must say FY26's 1–4 month lookback cannot establish genuinely new launches; FY27 has 13–16 months. Use “observed” and “provisional” in the card, table/chart label, and any download. The current NPI cohort FY selector may choose the later FY; if there is no prior eligible FY, show unavailable. Do not label this result “confirmed NPI YoY” or place it under the confirmed growth column.

Dashboard dimension filters (chain/category/brand/etc.) select visible pairs using their full-history identity, as the current NPI view does. The global FY filter does not alter either comparison side; the NPI selector chooses the current side. A Month filter intersects the common eligible months for **both** sides; the UI must show the resulting months. A filter yielding no eligible month or a zero prior NSV shows unavailable, not infinity or 0% growth. Browser filtered totals must reconcile to the unfiltered builder payload when filters are cleared. Downloads, if provided for this new comparison, must use the same filtered values and carry the status, compared months, confidence mix, and caveat.

Fix the existing NPI explanation that says Chain × Article so it accurately says Chain × EAN with Article fallback. This is a labeling correction, not a grain change.

## Implementation units and failure behavior

1. **Builder calculation:** a focused helper calculates available common months, admission, performance sums, confidence counts, and the provisional payload from `detail_records` and existing launch identities. It also applies the confirmed YoY gates. It must not alter raw records or the existing cohort metric calculation.
2. **HTML view:** a focused renderer consumes the new payload, applies existing filter semantics to the admitted pair IDs, and displays provisional values separately from confirmed YoY. It does not invent missing source data.
3. **Validation:** tests cover current snapshot counts/values, March carry exclusion, April boundary symmetry, Chain × EAN rename deduplication, Article fallback, negative performance rows, filter parity, zero denominator, missing months, missing/short history, and absence of confirmed YoY in both payload and browser. Existing approved raw cohort totals and financial baselines must remain identical.

If the source coverage or join integrity check fails, publish an explicit unavailable status and show the reason. A malformed comparison must never silently fall back to a whole-FY ratio. Do not mask a failing assertion by changing source rows or numeric baselines. The test suite should distinguish deterministic source-snapshot fixtures from live Power BI Desktop validation.

## Follow-on phases and evidence gates

The next focused phase fixes `PowerBI/PowerQuery/11_Fact_OfftakeSales.pq` parsing for both `Apr'26` and bare `Jun`/`Jul`/`Aug` with numeric Year, and repairs the documented relationship from monthly facts to a **unique** date/month key. The following phase adds an NPI model/page to the repository's actual PBIP, using the same Chain × EAN admission, provisional comparison and confirmed gate, then reconciles pair counts, NSV, units, statuses and filter behavior to HTML. The ten-row `PowerBI/SeedData/NPI_Master.csv` is test data, not a substitute for production cohort history. The last phase fixes the proven zonal CSV chain-filter omission, raw-chain drill mismatch, and full NPI cohort export; tab rendering alone does not prove number parity.

Each phase needs source-to-payload tests and the narrowest relevant browser/model checks. Power BI claims about all pages require evidence from the checked-in page(s) and a successful live Desktop refresh/relationship/visual inspection of any additional report supplied later. Keep B5 `BLOCKED_PENDING_DESKTOP_EVIDENCE` until its governed live Desktop cases are collected and independently reviewed. Keep relevant PRs draft; do not merge, publish production, delete evidence, or remove data as part of this design.
