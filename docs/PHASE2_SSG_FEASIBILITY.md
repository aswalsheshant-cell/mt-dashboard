# Phase 2 Feasibility — Same-Store Growth (SSG)

Read-only inventory pass, no code or `data.js` changes made. Run 2026-09-20,
gated on PR #167's Phase 1 certification (`docs/PR167_PHASE1_CERTIFICATION.md`,
`PHASE1_CERTIFIED`).

## 1. What was actually inspected

Every real (non-template) monthly offtake source file present in this repo:

```
PowerBI/RawDataFolders/Offtake_Monthly/offtake_store_article_Apr_26.csv
PowerBI/RawDataFolders/Offtake_Monthly/offtake_store_article_May_26.csv
PowerBI/RawDataFolders/Offtake_Monthly/offtake_store_article_Jun_26.csv
PowerBI/RawDataFolders/Offtake_Monthly/offtake_store_article_Jul_26.csv
PowerBI/RawDataFolders/Offtake_Monthly/offtake_store_article_Aug_26.csv
```

That is **all 5 months that exist** — Apr through Aug 2026, all FY27. No FY26
or FY25 file at this store×article grain exists anywhere in this repository
(confirmed by directory listing; `config/data_source_registry.yml` registers
no such source either).

## 2. Store identity — the field, and whether it's usable

There is no column literally named `Store Code` in the real files (only the
unused `_TEMPLATE_Offtake_Monthly.csv` uses that name). The real files use
**`Site Code`** / **`Site Name`**, already recognized as part of this
source's registered primary key: `config/data_source_registry.yml` line 71,
`primary_keys: ["Month", "Site Code", "Article", "Chain Name"]`.

**Initial concern, then resolved with more evidence:** a first pass comparing
raw sample values made `Site Code` look inconsistent (April's first rows are
alphanumeric like `HINOP:003`; August's first rows are bare integers like
`1.0`). That turned out to be a red herring — different **chains** use
different internal numbering conventions, not the same chain changing
formats month to month. Re-checked properly, scoped to `(Chain Name, Site
Code)` as a compound key:

| Check | Result |
|---|---|
| Distinct `(Chain, Site Code)` pairs, April | 9,963 |
| Distinct `(Chain, Site Code)` pairs, August | 9,751 |
| Pairs present in **both** April and August | 8,755 (**87.9%** of April's) |
| Of those overlapping pairs, `Site Name` matches (case-insensitive) | 8,491 / 8,755 (**97.0%**) |
| Mismatches on the remaining 3% | Abbreviation differences for the same physical store (e.g. `GARHAT` vs `GARIAHAT`, `N.ALIP` vs `NEW ALIPORE`) — not different stores |
| `Site Code` reused by >1 chain **within the same month** | 99 of 9,646 August codes — expected and harmless once `Chain` is part of the join key (each chain numbers its own sites independently) |

**Conclusion: store identity is usable.** `(Chain Name, Site Code)` is a
reasonably stable compound key across the 5 months that exist, with real,
explainable churn (~12%) rather than format chaos. This is workable
raw material for a cohort key — a real project, not a data-quality dead end.

## 3. The actual blocker

**There is no FY26 (or FY25) store×article extract in this repository at
all.** Same-Store Growth as requested is a **year-over-year** measure
(`docs/PageLayouts.md`'s own framing: "the same period this year against the
same period last year"). With only FY27 (Apr–Aug'26) store-level data
present, there is nothing to compare it against — not a quality problem, a
completeness problem. This is consistent with, and the same root cause as,
this repo's already-documented "FY25/FY26 have no real store-level Primary
or Offtake extract" gap (`docs/DATA_AVAILABILITY_MATRIX.md`'s 29-Month
Coverage Matrix, `CLAUDE.md`'s "THE ONE FY RULE" coverage-split notes).

**Exact missing input:** a monthly (or full-FY) store×article offtake
extract for FY26 (Apr'25–Mar'26), in the same shape as
`offtake_store_article_*.csv` (i.e. carrying `Site Code`/`Site Name`, not
just the pre-aggregated chain-level workbook this repo already has for
FY26). Without it, no FY26-vs-FY27 comparable-store cohort can be built,
regardless of code quality.

## 4. Answering the 10 inventory questions directly

| # | Question | Answer |
|---|---|---|
| 1 | Is Store ID stable across months? | Reasonably — 87.9% month-over-month persistence on `(Chain, Site Code)`, within the 5 FY27 months that exist |
| 2 | Are duplicate Store IDs present? | Only across different chains (expected, resolved by compound key); not within a chain |
| 3 | Can stores move between chains? | Not observed in the 5-month window; would need to be checked once cross-FY data exists |
| 4 | Can store-name changes create false new stores? | Not if `Site Code` (not `Site Name`) is the join key — confirmed 97% name-match rate on code-matched pairs, so the code is the reliable identifier, name is just a display label |
| 5 | What months have store-level coverage? | Apr, May, Jun, Jul, Aug 2026 only — all FY27. Zero FY26 or earlier months |
| 6 | What % of NSV has usable store identity? | Not separately computed in this pass (all rows in these 5 files carry `Site Code`); would need a null-rate check once a real Phase 2 build starts |
| 7 | Stores in current-only / prior-only / both periods | Computed for Apr vs Aug (4 months apart, both FY27): 1,208 April-only, 996 August-only, 8,755 in both. A true prior-FY comparison can't be computed at all (§3) |
| 8 | Are zero-sales stores distinguishable from missing records? | Not tested in this pass — every row in these extracts appears to carry a positive-or-real Qty/NSV; whether a store that sold zero units still gets a row (vs. being entirely absent) needs a targeted check before Phase 2 build |
| 9 | Are closures/openings identifiable? | Only inferable indirectly (a store present in one month and absent in another) — no explicit open/close date field exists in these files |
| 10 | Can a comparable cohort be built without assumptions? | Within FY27 month-to-month: yes, on reasonable evidence. Across FY26-vs-FY27: no — there is nothing to build it from |

## 5. Classification

**`READY_WITH_GAPS`**

Not `BLOCKED`: the store-identity mechanism itself is sound, already
governed as part of this source's primary key, and empirically stable
enough (87.9%/97.0%) to build a cohort key on. Not `READY`: the specific,
named gap in §3 (a real FY26 store×article extract) must be supplied before
any FY26-vs-FY27 Same-Store Growth number can be computed — no shortcut,
proxy, or estimate should be used to fill it, per this repo's "no dummy
data" rule.

**Exact missing input, and its owner:** a real FY26 (Apr'25–Mar'26)
store×article offtake extract, in the same shape as the FY27 files above,
supplied by whoever supplies the monthly `offtake_store_article_*.csv`
drops today (per `config/data_source_registry.yml`'s existing ownership for
this source). Until it exists, Phase 2 can still make **useful, honest**
progress on: (a) an intra-FY27 store-cohort MoM view (Apr→Aug, already
demonstrated feasible above), clearly labeled as not a YoY measure, and (b)
designing the governance rules below so implementation is fast once the
FY26 file arrives.

## 6. Proposed SSG governance (designed, NOT implemented)

- **Canonical cohort key:** `(Chain Name, Site Code)`. Never `Site Name`
  alone (abbreviation drift, §2) and never `Site Code` alone (cross-chain
  reuse, §2).
- **Comparable-store definition:** a cohort key present in both the current
  and prior period's real extract, with a nonzero row (not just present in
  the master/universe file).
- **Minimum history requirement:** a store must have at least one full month
  of real transactional data in the comparison window's shared months on
  both sides — matching this repo's existing `same_period_block()`
  shared-months discipline (never comparing a part-period to a full one).
- **Opening-store rule:** a cohort key with a prior-period row absent and a
  current-period row present = `NEW_STORE`; included in the total account
  figure, excluded from the Same-Store subtotal — same pattern as this PR's
  `NEW_ACCOUNT` flag, applied one grain lower.
- **Closed-store rule:** the reverse = `CLOSED_STORE`; same treatment,
  mirrored.
- **Missing-month rule:** a store with some but not all shared months
  present should not be silently dropped or zero-filled — flag
  `PARTIAL_COVERAGE` and exclude from Same-Store unless/until the business
  confirms a specific fallback (matches this repo's `LY_BASE_MISSING`-style
  disclosure pattern elsewhere).
- **Zero-sales rule:** a store with a real row and zero NSV/Qty is
  `COMPARABLE` with a real zero, not missing — must be distinguished from a
  store with no row at all (open question #8 above, needs a targeted check
  before this rule can be implemented with confidence).
- **Chain-transfer rule:** if the same physical site is later reassigned to
  a different chain (not observed in the 5-month window, but not ruled out
  either), it should NOT be silently treated as one continuous store history
  across the chain boundary — flag and hold for manual review, since
  `Chain Name` is part of the cohort key by design.
- **Duplicate-store rule:** if a `(Chain, Site Code)` pair appears more than
  once in a single month's extract (not observed in the checked files, but
  not proven absent everywhere), aggregate rather than pick one row
  arbitrarily, and log the count so a future data-quality regression is
  visible.
- **Returns/negative-sales rule:** reuse this PR's own precedent
  (`TestNegativeValues` in `scripts/test_account_yoy_edge_cases.py`) — a
  net-negative period is a real, computable number, not suppressed, and
  does not by itself imply `CLOSED_STORE`.

## 7. Explicitly not done in this pass

No DAX, no new chart, no `data.js` change, no PR opened for Phase 2, no
merge of PR #167. This document is an input to a human decision on whether
to pursue getting the FY26 store×article file, not a go-ahead to build
against a workaround.
