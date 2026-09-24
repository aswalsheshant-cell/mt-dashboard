# Canonical Financial Truth — Design (Phase 1: Design Only)

**Status:** DESIGN ONLY. No production calculation, dashboard code, or `data.js` schema changes are made by this document or this branch. Nothing here is implemented yet.
**Depends on:** `main` @ `ca67f67173dd9c1d71ae715b3abf47a2e072ed63` — the certified baseline from `docs/POST_MERGE_CERTIFICATION_PR193.md` / PR #193 / PR #196.
**Related governance:** [Issue #194](https://github.com/aswalsheshant-cell/mt-dashboard/issues/194) (infrastructure, kept fully separate — Track C below), [Issue #195](https://github.com/aswalsheshant-cell/mt-dashboard/issues/195) (`KI-OFFTAKE-001`, mapped into this design rather than patched standalone — Track B below).

## Why this document exists

PR #193 fixed four business-number defects. Three of the four (channel split, Category/Pack display, Reliance zone display) were each a *display or aggregation-source* bug local to one code path. The fourth (Inventory Total Offtake KPI) and the still-open `KI-OFFTAKE-001` are both symptoms of the same deeper pattern: **the same business number can be computed more than one way in this codebase, and nothing enforces that the two ways agree.** `primary.by_channel` (pre-aggregated) and `detail_records` (article-wise) both claim to describe Primary Channel NSV; `offtake.total_<fy>` and the "Top Chains by Offtake" table's own per-chain fallback both claim to describe Offtake NSV — and PR #193 had to reconcile them by hand, once, for four specific views. That does not scale, and it is exactly the failure mode a semantic-model-style canonical layer exists to prevent: one calculation, many consumers, instead of many calculations hoping to agree.

This document maps the **current** state honestly (including the gaps — no invented capability), designs a **target** state, defines metric contracts for the first 7 canonical metrics, and maps `KI-OFFTAKE-001`'s actual root cause into that target design. Implementation, impact analysis, and migration are explicitly out of scope for this phase.

---

## Current state (as verified in `scripts/build_dashboard_data.py` / `dashboard/index.html` at the certified baseline)

```
RAW SOURCES
  Primary_FY202426_10.csv (pre-agg, committed seed)         Primary_Article_Monthly/*.csv (article-wise)
  offtake chain-month / zone-state-month masters             UniverseMT.csv (store roster)
  reliance BC extract
        │                                                           │
        ▼                                                           ▼
  load_primary_v2() + apply_chain_allocation()          detail_records_real() (File 2)
        │                                                           │
        ▼                                                           ▼
  primary_block()  ──► primary.by_channel, by_chain,      detail_records (160,834 rows,
                        by_zone, by_brand (pre-agg,        article-wise, real Channel/
                        FY25/FY26 window)                 Chain/Category/Zone/NSV)
        │                                                           │
        │        apply_primary_channel_correction()                │
        │        (PR #193 — patches FY25/26 by_channel               │
        │        values from detail_meta.channel_totals               │
        │        when totals agree within 0.5%)                     │
        └───────────────────────┬───────────────────────────────────┘
                                 │
                    (still TWO separate objects in data.js;
                     the correction narrows disagreement on
                     one field, it does not unify the paths)

  offtake_block() [full build] ──► offtake.total (nested {fy: value}
                                    as originally coded), total_<fy>
                                    (flat), by_chain[], by_zone[],
                                    by_state[]
        │
        ▼
  patch_offtake_new_months() [--offtake-patch, the routine monthly
  refresh path per CLAUDE.md] ──► rewrites total_<fy> (flat) and each
                                   by_chain/by_zone/by_state row's
                                   <fy> field, per-FY, idempotently.
                                   Never reads or writes offtake["total"]
                                   (the nested object) at all.

  ⚠ OBSERVED AND NOW ROOT-CAUSED (updated after tracing the actual code
  paths, not just the symptom): THREE different functions in
  scripts/build_dashboard_data.py can write offtake["total"] and
  offtake["by_chain"][].value, with different semantics each time:
    1. offtake_block() (the original full-build path) — out["total"] =
       {fy26: value, fy27: value, ...} (nested, per-FY dict).
    2. offtake_rebuild_block() (--offtake-rebuild; confirmed via its
       provenance string, "Rebuilt from N monthly store x article
       extracts...", to be the function that actually produced the
       certified baseline's offtake block) — out["total"] =
       sum(off_m[m]["total"] for m in months): a FLAT number, summed
       across EVERY month the rebuild's source covers, with NO FY
       subscript. Its dim_rows() helper sets each by_chain row's
       "value" field the same way: sum across all months in that
       rebuild's source, not one FY.
    3. patch_offtake_new_months() (--offtake-patch, the routine monthly
       refresh path this repo's own docs recommend for adding new
       months) updates total_<fy> and each row's <fy>-keyed field, but
       NEVER reads or writes "total" or "value" at all.
  A dashboard/index.html comment (line 377-382, pre-dating this design)
  records that offtake.total_fy26 and sum(offtake.by_chain[].value)
  "tie to it exactly" — true at the time it was written, because the
  rebuild's source then covered FY26 only, so the all-months sum and
  the FY26 sum were the same number by coincidence, not by any enforced
  invariant. Once FY27 months were added afterward via --offtake-patch
  (which never touches .value), that coincidence broke silently: .value
  is now stale, frozen at its old FY26-only meaning, while the
  <fy>-keyed fields have moved on. This is the exact field
  buildInventoryHealth's chainData fallback chain reaches last (see
  KI-OFFTAKE-001 below) — not "a different FY's number" as an earlier
  draft of this document said, but "the sum across however many months
  existed the last time a full rebuild ran, silently decaying into
  looking like a single stale FY's number as new FYs are patched in
  around it without it being refreshed."

DASHBOARD (dashboard/index.html) consumes both objects independently:
  Executive Cockpit donut           ──reads── primary.by_channel
  Channel & Chain / Primary drill   ──reads── detail_records (filtered)
  Data Explorer charts              ──reads── detail_records
  Category & Pack Mix               ──reads── detail_records, grouped client-side
  Reliance Brand Counter sub-view   ──reads── detail_records (Chain=='Reliance Retail')
                                                — this is PRIMARY data, NOT offtake,
                                                despite living under a tab called
                                                "Reliance Brand Counter"
  Inventory Health "Total Offtake"  ──reads── offtake.total_<fyR> (after PR #193 fix)
  Inventory Health "Top Chains"     ──reads── offtake.by_chain[], falls back to
                                                stale .value when the selected FY's
                                                own key is absent (KI-OFFTAKE-001)
  reliance_brand_counters block     ──UNUSED── real offtake-side Reliance BC data
                                                exists (D.reliance_brand_counters:
                                                total, by_zone, by_brand, fy_tags)
                                                but no current UI view reads it —
                                                the "Reliance Brand Counter" tab
                                                actually shows Primary data instead
```

**Honest gaps in the current data model** (naming what does *not* exist, per this repo's "no dummy data" rule — a metric contract below is marked `NOT CURRENTLY AVAILABLE` rather than invented):
- No category-level breakdown exists anywhere in the `offtake` block (`D.offtake.by_category` does not exist). Category analysis in the dashboard is Primary-only (`detail_records`).
- No store-level or article-level NSV breakdown exists in the `offtake` block. `D.universe.by_chain[].stores` is a **store count**, not NSV. Store-level offtake NSV is not computed anywhere in this pipeline today.
- `D.reliance_brand_counters` (the real offtake-side Reliance Brand Counter block) exists in `data.js` but has no dashboard consumer — the tab named "Reliance Brand Counter" reads Primary `detail_records` instead, which is correct per this repo's dedup rule (isolation applies to Offtake, never Primary) but means the offtake-side BC block is currently write-only.

---

## Target state

```
                         SOURCE DATA
              (Primary article-wise, Primary pre-agg,
               Offtake chain-month master, Reliance BC,
               Universe/store roster — unchanged inputs)
                              │
                              ▼
                    VALIDATED FACTS
       (one fact table per grain: primary_fact [article ×
        month × chain × channel], offtake_fact [chain/zone/
        state × month], reliance_bc_fact — each with an
        explicit, single FY-derivation function and an
        explicit, single missing-data policy. No fact table
        is assembled two different ways by two functions.)
                              │
                              ▼
                   CANONICAL METRICS
        (PRIMARY_NSV, OFFTAKE_NSV, CHANNEL_PRIMARY_NSV,
         CHAIN_OFFTAKE_NSV, CATEGORY_OFFTAKE_NSV*,
         STORE_OFFTAKE_NSV*, RELIANCE_OFFTAKE_NSV —
         each with ONE metric contract, below. *Two of
         these have no source fact today; the contract
         says so rather than inventing one.)
                              │
              ┌───────────────┼───────────────┬───────────────┐
              ▼               ▼                ▼               ▼
        Executive        Explorer /       Inventory &      Power BI /
        Cockpit          Drill-down       Channel Perf.    PBIP (future,
                                                             PR after this one)
              └───────────────┴───────────────┴───────────────┘
                                    │
                              ONE TRUTH
              (every consumer reads the same canonical metric
               function/value; a fix to a metric's logic fixes
               every consumer at once — no second reconciliation
               PR like #193 required for the next display bug)
```

This is the standard star-schema-adjacent shape (facts at a consistent grain, dimensions for filtering/grouping, a semantic layer of named, reusable measures on top) — not a new invention, just formalizing what this codebase's own comments already describe informally (`THE ONE FY RULE`, `apply_primary_channel_correction`'s "one source of truth" framing) into an actual enforced contract layer.

---

## Metric contracts (first 7)

Each contract below is filled from the **current, real** source where one exists. Where no current source exists, every field after `Authoritative source` reads `NOT CURRENTLY AVAILABLE` rather than a fabricated value — consistent with this repo's "No dummy data" rule.

### PRIMARY_NSV

| Field | Value |
|---|---|
| Metric ID | `PRIMARY_NSV` |
| Availability Status | **AVAILABLE** (two sources today, need reconciling per row below — not a gap, a consolidation task) |
| Business definition | Factory/depot billing to MT chains and distributors (SAP/ERP billing), before any offtake or secondary step |
| Business owner | MT Leadership / Finance (per CLAUDE.md's business-confirmation-required rule) |
| Authoritative source | Two sources exist today and must be reconciled, not picked arbitrarily: (a) `PowerBI/SeedData/Primary/Primary_FY202426_10.csv` (pre-agg, FY25/FY26 window, `load_primary_v2()`), (b) `PowerBI/RawDataFolders/Primary_Article_Monthly/*.csv` (article-wise, all FYs, `detail_records_real()`). Per `docs/PR_193_PRODUCTION_CERTIFICATION.md` Control 1, (b) is already the confirmed source of truth for the Channel dimension; the canonical design should make it the sole source for NSV too, with (a) either retired or reduced to a pure cross-check |
| Source columns | `Inv. Net value(LOC)` (article-wise) / `NSV` (pre-agg) |
| Grain | Article × Month × Ship-To × Channel (article-wise); Ship-To × Month × Chain-allocation (pre-agg) — different grains today, a canonical fact table must pick one (article-wise is finer and should be canonical) |
| Date grain | Month |
| FY logic | THE ONE FY RULE (`_fylabel()` / `fy_tag_from_label()`) — already single-implementation, reuse as-is |
| Channel rules | MT / EB2B / SIS, per the `Channel` column on the article-wise source (case-normalized via `_CHAN_MAP`) |
| Chain mapping rules | `canon_chain()` + DIST allocation (`allocate_dist_primary()` / `apply_chain_allocation()`) for Distributor-billed rows |
| Brand rules | `canon_brand()` |
| Store rules | N/A at this grain (Ship-To, not store) |
| Aggregation rule | SUM(NSV) at the target grain |
| Unit | INR Lakh (canonical internal unit throughout this codebase) |
| ₹/Lac/Cr conversion rule | Display-only, via `crc()` (dashboard) — never applied before storage. (PR #193's bug #2 was exactly a violation of this rule: a display-side pre-division before `crc()`'s own conversion.) |
| Null policy | A null/missing NSV cell is 0, never dropped (would silently understate a real transaction) |
| Missing-data policy | FY25 (Apr'24–Mar'25) has no real Primary extract anywhere in this repo (confirmed, documented in `docs/DATA_AVAILABILITY_MATRIX.md`) — must render as "–", never 0 |
| Negative-value policy | Real (returns/credit notes). Never floored to 0; already handled correctly in `_sis_reconciliation()`'s documented note about negative NSV |
| Fallback policy | **None across FY tags.** A canonical FY-selection function must never substitute one FY's value when another FY is requested (this is precisely `KI-OFFTAKE-001`'s failure mode, applied here pre-emptively) |
| Reconciliation target | Certified FY26 baseline: ₹32,900.36 L (both sources must tie to this) |
| Tolerance | ±0.01 L (this repo's `r2()` rounding convention) |
| Certification test | `tests/test_pr193_reconciliation.py::test_channel_by_channel_reconciles_to_article_wise_channel_totals` (partial — channel dimension only today; a full canonical test is future work) |
| Current consumers | Executive Cockpit (via `primary.by_channel`), Data Explorer / Channel & Chain Performance / Category & Pack Mix (via `detail_records`) — **two different consumers reading two different objects for nominally the same number** |
| Future semantic-model measure | `[Primary NSV]` (PBIP, future PR) |
| Known exceptions | FY25 has no Primary data at all (documented gap, not a defect) |

### OFFTAKE_NSV

| Field | Value |
|---|---|
| Metric ID | `OFFTAKE_NSV` |
| Availability Status | **AVAILABLE**, but see ADR-002 — the total is currently producible in 3 different shapes depending on which builder last ran; needs consolidation, not new data |
| Business definition | Chain POS sell-out (store shelf → consumer) |
| Business owner | MT Leadership |
| Authoritative source | Chain-month / zone-state-month offtake master, loaded via `load_offtake()` / `load_offtake_article_files()` |
| Source columns | Per-chain, per-month NSV cells in the offtake master |
| Grain | Chain × Month (full build); merged incrementally by `patch_offtake_new_months()` for new FYs |
| Date grain | Month |
| FY logic | THE ONE FY RULE, same as Primary |
| Channel rules | N/A — Offtake is inherently MT-chain POS; EB2B/SIS are Primary-only channel concepts |
| Chain mapping rules | `canon_chain()` |
| Brand rules | `canon_brand()` (`offtake.by_brand`) |
| Store rules | Not tracked at store grain — see `STORE_OFFTAKE_NSV` below |
| Aggregation rule | SUM(NSV) at chain × month |
| Unit | INR Lakh |
| ₹/Lac/Cr conversion rule | Display-only via `crc()`, same rule as Primary |
| Null policy | Missing cell = 0 |
| Missing-data policy | A chain/FY combination genuinely absent from the source must render as "–", not a stale different-FY value — **this is exactly where `KI-OFFTAKE-001` currently violates the intended policy** |
| Negative-value policy | Real returns; not floored |
| Fallback policy | **None across FY tags** (see `KI-OFFTAKE-001` mapping below — this field is the fix target) |
| Reconciliation target | `offtake.total_<fy>` must equal `sum(offtake.monthly_<fy>)` exactly (proven for FY27 in `docs/PR_193_PRODUCTION_CERTIFICATION.md` Control 4: 0.00 L variance) |
| Tolerance | ±0.01 L |
| Certification test | `tests/test_pr193_reconciliation.py::test_inventory_total_offtake_reconciles_to_monthly_sum` |
| Current consumers | Inventory & Supply Health "Total Offtake" KPI (fixed in PR #193), Performance & Comparison's MoM table |
| Future semantic-model measure | `[Offtake NSV]` (PBIP, future PR) |
| Known exceptions | `offtake.total`'s nested-vs-flat shape inconsistency (see Current State section above) — not yet filed as its own issue; folded into this design's remit since it's the same class of defect as `KI-OFFTAKE-001` |

### CHANNEL_PRIMARY_NSV

| Field | Value |
|---|---|
| Metric ID | `CHANNEL_PRIMARY_NSV` |
| Availability Status | **AVAILABLE** (fixed and certified in PR #193; article-wise source is the confirmed authority) |
| Business definition | `PRIMARY_NSV` split by Channel (MT / EB2B / SIS) |
| Business owner | MT Leadership |
| Authoritative source | `detail_meta.channel_totals` (article-wise, exact, uncapped) — per PR #193, this is now the corrective source for `primary.by_channel`'s FY25/FY26 values too |
| Source columns | Same as `PRIMARY_NSV`, grouped by `Channel` |
| Grain | Channel × FY |
| Date grain | FY (no monthly channel split currently surfaced) |
| FY logic | THE ONE FY RULE |
| Channel rules | MT / EB2B / SIS via `_CHAN_MAP` |
| Chain mapping rules | N/A at this grain |
| Brand rules | N/A at this grain |
| Store rules | N/A |
| Aggregation rule | SUM(NSV) per channel per FY |
| Unit | INR Lakh |
| ₹/Lac/Cr conversion rule | Display-only via `crc()` |
| Null policy | Missing channel tag treated as its own bucket, never silently dropped |
| Missing-data policy | A channel with 0 real transactions in an FY shows 0, not blank (distinct from a whole FY being unavailable, which shows "–") |
| Negative-value policy | Real; not floored |
| Fallback policy | Cross-source correction only when the two sources' FY total agrees within 0.5% (the guard already implemented in `apply_primary_channel_correction()`) — this guard itself should become the canonical pattern for any future "correct a lossy pre-agg field from a better source" case |
| Reconciliation target | ₹32,900.36 L (FY26 certified baseline) |
| Tolerance | ±0.01 L absolute; ±0.5% for the cross-source agreement guard specifically |
| Certification test | `tests/test_primary_channel_correction.py` (5 tests) + `tests/test_pr193_reconciliation.py` (channel tests) |
| Current consumers | Executive Cockpit channel-split donut |
| Future semantic-model measure | `[Channel Primary NSV]` |
| Known exceptions | None currently open (PR #193 resolved the prior defect) |

### CHAIN_OFFTAKE_NSV

| Field | Value |
|---|---|
| Metric ID | `CHAIN_OFFTAKE_NSV` |
| Availability Status | **AVAILABLE**, but see `KI-OFFTAKE-001` (ADR-001) — the fallback defect must close before this metric is certified, not just before it's "available" |
| Business definition | `OFFTAKE_NSV` split by Chain |
| Business owner | MT Leadership |
| Authoritative source | `offtake.by_chain[]` |
| Source columns | Per-chain `<fy>` fields, maintained by both `offtake_block()` (full build) and `patch_offtake_new_months()` (incremental) |
| Grain | Chain × FY |
| Date grain | FY (monthly not surfaced per-chain) |
| FY logic | THE ONE FY RULE |
| Channel rules | N/A |
| Chain mapping rules | `canon_chain()` |
| Brand rules | N/A |
| Store rules | N/A |
| Aggregation rule | SUM(NSV) per chain per FY |
| Unit | INR Lakh |
| ₹/Lac/Cr conversion rule | Display-only via `crc()` — the dashboard's `Offtake (Cr)` Chart.js dataset manually divides by 100 for its axis, which is correct (charts don't use `crc()`) and must stay that way, not be "fixed" to match the table pattern |
| Null policy | A chain with no row for the requested FY must not silently substitute another FY's value |
| Missing-data policy | Show `–` for a chain/FY combination genuinely absent, never a different period's figure |
| Negative-value policy | Real; not floored |
| Fallback policy | **THIS IS `KI-OFFTAKE-001`.** Current code (`buildInventoryHealth`'s `chainData` map in `dashboard/index.html`) falls back `ch_data.total?.[fyR] ?? ch_data['total_'+fyR] ?? ch_data[fyR] ?? ch_data.value ?? 0` — the last fallback, `ch_data.value`, is a different FY's number silently presented as the requested FY's. Canonical fallback policy: **none** — render `–` instead |
| Reconciliation target | `sum(offtake.by_chain[].{fy}) ` should reconcile to `offtake.total_{fy}` for every chain that actually has data in that FY (excluding the stale-fallback chains once the fix lands) |
| Tolerance | ±0.01 L once the fallback is removed; currently ~15.17 L / 0.08% of FY27 total (the `KI-OFFTAKE-001` variance) |
| Certification test | None exists yet for this specific table — future work, see below |
| Current consumers | Inventory & Supply Health "Top Chains by Offtake" table and its Chart.js bar chart |
| Future semantic-model measure | `[Chain Offtake NSV]` |
| Known exceptions | `KI-OFFTAKE-001` (Issue #195) — mapped in detail below |

### CATEGORY_OFFTAKE_NSV

| Field | Value |
|---|---|
| Metric ID | `CATEGORY_OFFTAKE_NSV` |
| Availability Status | **NOT_AVAILABLE**. Reason: required source grain (offtake at category/article level) does not currently exist. Do not derive from: Primary category data, chain-level percentage allocation, or AI/estimation of any kind (ADR-004) |
| Business definition | `OFFTAKE_NSV` split by product Category |
| Business owner | MT Leadership |
| Authoritative source | **NOT CURRENTLY AVAILABLE.** No category dimension exists anywhere in `D.offtake` (verified: `'by_category' in D.offtake` is `false` on the certified baseline). The dashboard's "Category & Pack Mix" view is Primary-only (`detail_records`), not offtake |
| Source columns | N/A |
| Grain | N/A |
| Date grain | N/A |
| FY logic | N/A |
| Channel rules | N/A |
| Chain mapping rules | N/A |
| Brand rules | N/A |
| Store rules | N/A |
| Aggregation rule | N/A |
| Unit | N/A |
| ₹/Lac/Cr conversion rule | N/A |
| Null policy | N/A |
| Missing-data policy | Any future dashboard card claiming "Category Offtake" must say "not available in this build" (per this repo's established pattern, e.g. the Market Share and weekly-gap cards) rather than substitute Primary category data unlabeled |
| Negative-value policy | N/A |
| Fallback policy | N/A |
| Reconciliation target | N/A |
| Tolerance | N/A |
| Certification test | N/A |
| Current consumers | None |
| Future semantic-model measure | Deferred — requires a new source (offtake extract with a Category column at the store×article grain, or a mapping join from `detail_records`' article-level Category via EAN) before this contract can be completed |
| Known exceptions | This entire metric is a gap, not a defect — named here so a future request for "offtake by category" isn't quietly built from the wrong (Primary) source |

### STORE_OFFTAKE_NSV

| Field | Value |
|---|---|
| Metric ID | `STORE_OFFTAKE_NSV` |
| Availability Status | **NOT_AVAILABLE**. Reason: required source grain (offtake at store level) does not currently exist. Do not derive from: `universe.by_chain[].stores` (a store count, not NSV), the Store Audit Scorecard's self-flagged demo data, or chain-total ÷ store-count estimation (ADR-005) |
| Business definition | `OFFTAKE_NSV` split by individual store |
| Business owner | MT Leadership |
| Authoritative source | **NOT CURRENTLY AVAILABLE** at NSV grain. `D.universe.by_chain[].stores` is a store **count** per chain, not NSV. The Store Audit Scorecard (`D.compliance`) is a separate, explicitly-flagged-as-unverified/demo-matching PES/audit dataset (per `dashboard/index.html`'s own `_synthNote`), not a real store-level sales figure |
| Source columns | N/A |
| Grain | N/A |
| Date grain | N/A |
| FY logic | N/A |
| Channel rules | N/A |
| Chain mapping rules | N/A |
| Brand rules | N/A |
| Store rules | N/A |
| Aggregation rule | N/A |
| Unit | N/A |
| ₹/Lac/Cr conversion rule | N/A |
| Null policy | N/A |
| Missing-data policy | Same as `CATEGORY_OFFTAKE_NSV` — must say "not available," never substitute the store-count field or the flagged-demo compliance data as if it were real store-level NSV |
| Negative-value policy | N/A |
| Fallback policy | N/A |
| Reconciliation target | N/A |
| Tolerance | N/A |
| Certification test | N/A |
| Current consumers | None |
| Future semantic-model measure | Deferred — requires a store×article×month offtake extract (finer than the current chain-month master) before this contract can be completed |
| Known exceptions | Gap, not a defect |

### RELIANCE_OFFTAKE_NSV

| Field | Value |
|---|---|
| Metric ID | `RELIANCE_OFFTAKE_NSV` |
| Availability Status | **AVAILABLE** as data (`D.reliance_brand_counters` is real), but **BLOCKED on ADR-003** for which UI/business meaning it should serve — do not wire it into any view until that decision lands |
| Business definition | Reliance-specific Offtake, split into Total Reliance Offtake (macro) and the ~350 staffed Brand Counter doors (a strict subset, per CLAUDE.md's Reliance Brand Counter Deduplication Safeguard) |
| Business owner | MT Leadership |
| Authoritative source | `D.reliance_brand_counters` (`load_reliance_bc_data()`) — this block is real and exists in `data.js` today (`total`, `by_zone`, `by_brand`, `fy_tags`) but has **no current dashboard consumer**. Separately, `D.offtake.by_chain` has a "Reliance Retail" row for total chain offtake |
| Source columns | Reliance BC extract, per `load_reliance_bc_data()` |
| Grain | Zone/Brand × Month, BC-specific |
| Date grain | Month |
| FY logic | THE ONE FY RULE |
| Channel rules | N/A — offtake-side, not a Primary channel |
| Chain mapping rules | Fixed to Reliance Retail |
| Brand rules | `canon_brand()` |
| Store rules | Doors, not individual stores (~350 staffed Brand Counter doors, an operational subset per CLAUDE.md) |
| Aggregation rule | SUM(NSV); BC total is a partition of, never additive on top of, total Reliance offtake (per the dedup safeguard — `validate_offtake_partition()` already checks this) |
| Unit | INR Lakh |
| ₹/Lac/Cr conversion rule | Display-only via `crc()` |
| Null policy | Missing cell = 0 |
| Missing-data policy | `bc_data.june_status` pattern (an explicit coverage-gap note) already exists for BC data — reuse that pattern, don't fabricate a missing month |
| Negative-value policy | Real; not floored |
| Fallback policy | None across FY tags |
| Reconciliation target | `validate_offtake_partition()`'s existing check: BC total must not exceed total Reliance offtake (already implemented, already run) |
| Tolerance | Exact partition (BC ⊆ total), per the existing validator |
| Certification test | `validate_offtake_partition()` (exists; not yet wired into `tests/`) |
| Current consumers | **None in the current UI.** The "Reliance Brand Counter" tab (`renderChannelSubview`'s `reliance` branch) reads `detail_records` filtered to `Chain==='Reliance Retail'` — that is **Primary** data, shown under a tab named for an Offtake-side concept. This naming/data mismatch is worth flagging to the business owner, not silently "fixed" by swapping data sources without confirming which one the tab is actually meant to show |
| Future semantic-model measure | `[Reliance Offtake NSV]` / `[Reliance BC NSV]` |
| Known exceptions | The tab-vs-data mismatch above. **Not touched in this design phase** — needs an explicit business decision (is "Reliance Brand Counter" meant to show Primary or Offtake?) before any code changes, consistent with CLAUDE.md's `INTERNAL_BUSINESS_CONFIRMATION_REQUIRED` pattern |

---

## `KI-OFFTAKE-001` root-cause mapping (Issue #195)

Per the instruction not to patch the four long-tail chains directly, here is the causal chain:

```
KI-OFFTAKE-001 (observed symptom)
  "Top Chains by Offtake" table shows a stale FY26 figure for
  ~4 chains (e.g. Vijetha) under the FY27 view, instead of "–"
       │
       ▼
Which calculation path generates it?
  buildInventoryHealth()'s chainData map, dashboard/index.html:
  nsv = (ch_data.total && ch_data.total[fyR]) || ch_data['total_'+fyR]
        || ch_data[fyR] || ch_data.value || 0
  The last fallback, ch_data.value, is populated by offtake_block()
  as a legacy single-value field (historically "the" NSV before this
  dashboard supported multiple FYs) and is never FY-aware.
       │
       ▼
Why can stale-FY fallback occur?
  Precisely because of the offtake_rebuild_block() finding above:
  ch_data.value is not an FY-scoped field at all — it's "sum across
  whatever months the last --offtake-rebuild's source happened to
  cover," which only LOOKED single-FY-correct by coincidence at the
  moment it was set, and has no mechanism to stay correct as
  --offtake-patch adds later FYs around it. CHAIN_OFFTAKE_NSV's
  fallback policy was never made explicit anywhere in the codebase —
  the JS fallback chain was written defensively ("give me SOME number")
  rather than correctly ("give me THIS FY's number or say so"), and
  the Python side has no invariant enforcing that .value stays
  FY-consistent with the <fy>-keyed fields sitting right next to it in
  the same row.
       │
       ▼
What should canonical FY-selection logic be?
  A single, canonical accessor — e.g. get_metric_for_fy(entity, fy) —
  used by every consumer of CHAIN_OFFTAKE_NSV (and every other FY-keyed
  canonical metric), with ONE rule: return the value for the exact FY
  requested, or None/"–" if absent. No cross-FY fallback, ever, for a
  metric whose contract says "Fallback policy: none." This is not a new
  idea for this codebase — it's the same discipline THE ONE FY RULE
  already applies to FY *derivation*; it just hasn't been applied to FY
  *lookup* yet.
       │
       ▼
Which other KPIs use similar fallback?
  - offtake.total's nested/flat shape drift (Current State section) —
    same root cause, one layer up (object shape, not row value)
  - primary.by_channel pre-PR-193 (now fixed, but the SAME class of
    bug: a stale/wrong value presented as if it were the requested
    one, because nothing enforced a single source of truth)
  - Worth auditing during implementation: any other `||` fallback
    chain in dashboard/index.html that mixes an FY-keyed lookup with a
    non-FY-keyed one (`.value`, `.total` without a `[fy]` subscript,
    etc.) is a candidate for the same defect. Not enumerated here —
    that audit belongs to the implementation phase, not this design
    document.
       │
       ▼
What regression test prevents recurrence?
  Two layers, both already precedented in this PR's own tests:
  1. A DATA reconciliation: for the canonical fact table, assert that
     every entity present in the FY the fact table claims to cover has
     a real (non-fallback) value — i.e. no entity's displayed value
     for FY-N was sourced from FY-(N-1) data. Mirrors
     tests/test_pr193_reconciliation.py's pattern of asserting an
     arithmetic identity against the real data.js.
  2. A SOURCE regression guard: a static check that no `||`/`??`
     fallback chain in the canonical accessor's call sites crosses an
     FY boundary. Mirrors
     tests/test_pr193_reconciliation.py::test_no_double_lakh_division_before_crc_in_category_or_reliance_tables's
     pattern of grepping for the exact buggy pattern.
```

**Disposition, per Track B below:** `KI-OFFTAKE-001` is absorbed into the canonical `CHAIN_OFFTAKE_NSV` implementation (its "Fallback policy: none" row above), not fixed as an isolated four-chain patch. Issue #195 stays open until the canonical implementation phase closes it with both regression-test layers in place.

---

## Search for other cross-FY fallback logic (repository-wide; nothing modified)

Grepped `dashboard/index.html` and `scripts/build_dashboard_data.py` for the same shape of defect (a lookup that silently substitutes a different FY's — or an all-FY-combined — value when the requested FY's own field is absent).

| Location | Pattern | Verdict |
|---|---|---|
| `dashboard/index.html:1618` (`buildInventoryHealth`'s `chainData`) | `ch_data.total?.[fyR] ?? ch_data['total_'+fyR] ?? ch_data[fyR] ?? ch_data.value ?? 0` | **`KI-OFFTAKE-001`** — the defect this design addresses |
| `dashboard/index.html:1555` (`buildInventoryHealth`'s KPI `total`, fixed by PR #193) | `o?.total?.[fyR] ?? o?.[`total_${fyR}`] ?? 0` | Not a cross-FY fallback — terminates at `0`, never at another FY's or an all-FY value. Fixed correctly in PR #193; no residual issue |
| `dashboard/index.html:3654` (`buildComparison`, Performance & Comparison tab) | `rows=arr.filter(x=>(x.fy26\|\|0)>0\|\|(x.fy25\|\|0)>0).map(x=>({name:x.name,a:x.fy25,b:x.fy26,...}))` | **Not a defect.** This is an explicit, labelled FY25-vs-FY26 side-by-side comparison view (`yrPair=[fyDispLabel('FY25'),fyDispLabel('FY26')]`) — exactly the "explicitly labelled as a comparison" exception this design's `PRIMARY_NSV` contract already carves out. Both FYs are shown as separate columns, never merged into one silently-substituted figure |
| `scripts/build_dashboard_data.py` (full file) | Searched for `.get(fy...) or .get(...)`-style cross-FY substitution patterns | No occurrences found outside the two already-documented ones above (`offtake_rebuild_block()`'s `.value` field, `offtake["total"]`'s three-shapes issue) |

No other occurrence found. Both real findings (`KI-OFFTAKE-001` itself, and the `offtake["total"]` three-different-shapes issue one layer up) are already mapped above; neither is touched by this document.

---

## Architecture Decision Register

| ID | Decision | Options considered | Status |
|---|---|---|---|
| **ADR-001** | Financial KPIs must never silently fall back to another FY (or an all-FY-combined figure) when the requested FY's own value is absent. The canonical accessor returns the exact-FY value or an explicit `MISSING`/`NOT_AVAILABLE` status — never a substitute number presented as if it were the requested FY's. A genuine side-by-side FY comparison (e.g. Performance & Comparison's FY25-vs-FY26 view) is not "fallback" under this rule as long as both FYs are shown as distinct, labelled columns, never merged into one figure | Silent fallback (current `KI-OFFTAKE-001` behavior) vs. explicit `–`/`NOT_AVAILABLE` | **APPROVED** — directly resolves `KI-OFFTAKE-001`'s root cause; no viable alternative that keeps financial-reporting integrity |
| **ADR-002** | `OFFTAKE_NSV`'s FY-specific canonical total must be derived from the same fact layer used by `CHAIN_OFFTAKE_NSV`, `by_zone`, and `by_state` — one function producing all of them from the same per-month, per-entity rows, not three independent builder functions (`offtake_block()`, `offtake_rebuild_block()`, `patch_offtake_new_months()`) that can each leave `total`/`value` in a different shape or staleness state, as documented in the Current State section above | Keep 3 separate builder functions with manual consistency discipline vs. one canonical fact table all three derive from | **APPROVED** — the "manual discipline" alternative is exactly what already failed (the `.value` staleness) |
| **ADR-003** | Business definition of the "Reliance Brand Counter" tab: does it mean (A) Primary — what Honasa billed into Reliance BC stores, (B) Offtake — what consumers bought from Reliance BC stores, or (C) Primary + Offtake + Gap together? Today's tab reads Primary `detail_records` while a real, unused Offtake-side `D.reliance_brand_counters` block sits idle | A: Primary only (current de facto behavior) · B: Offtake only (matches the real unused block and the tab's literal name, "Brand Counter" being an offtake/BA-staffing concept) · C: Both + Primary-Offtake Gap + sell-through trend (enables the fullest MT-relevant view: primary push, offtake pull, and the gap/inventory signal between them) | **PENDING BUSINESS OWNER** — not inferred here. See recommendation below |
| **ADR-004** | `CATEGORY_OFFTAKE_NSV` remains `NOT_AVAILABLE` unless an authoritative offtake source carrying the required category/article grain is supplied. Never derived from Primary category data, chain-level percentage allocation, or estimation of any kind | Mark unavailable vs. approximate from Primary category mix × offtake chain totals | **APPROVED** (mark unavailable) — an allocated/estimated figure presented as real offtake-by-category would be exactly the kind of fabricated-precision defect this whole audit exists to prevent |
| **ADR-005** | `STORE_OFFTAKE_NSV` remains `NOT_AVAILABLE` unless an authoritative store-level offtake source exists. Never derived from `universe.by_chain[].stores` (a store **count**, not NSV) or from the Store Audit Scorecard's already-self-flagged demo/unverified PES data | Mark unavailable vs. approximate from chain offtake ÷ store count | **APPROVED** (mark unavailable) — a divided-evenly estimate would misrepresent real store-level variance as if it were measured |
| **ADR-006** | Canonical financial storage unit is absolute ₹ (equivalently, this codebase's existing INR-Lakh convention, which is already absolute-₹-based, not display-scaled) — Lac/Crore conversion happens only in presentation logic (`crc()` or its future canonical-layer equivalent), never baked into a stored or intermediate value | Keep today's "store in Lakh, format via `crc()`" convention vs. restate everything in absolute ₹ | **APPROVED, with an implementation note**: this codebase already stores everything in INR Lakh (an absolute unit, just scaled by 10⁵ from ₹1) and only converts at display time via `crc()` — PR #193's bug #2 was a violation of exactly this rule (a display-side pre-division before `crc()`'s own conversion), not evidence the storage convention itself is wrong. The canonical layer should keep INR Lakh as the stored/computed unit (consistent with every existing fact/metric in this repo) and enforce, by test, that no intermediate computation divides by 100 before the single presentation-layer conversion |
| **ADR-007** | Missing financial data must remain `NULL`/`NOT_AVAILABLE`, never silently converted to zero | Silent zero (risk: indistinguishable from "real zero-value transaction period") vs. explicit missing-marker | **APPROVED** — already this repo's own stated practice in several places (e.g. FY25 Primary showing "–", not 0); this ADR makes it a canonical-layer-wide rule rather than a per-view convention some views (like the pre-fix Inventory KPI and `KI-OFFTAKE-001`) violated |
| **ADR-008** | The canonical metric layer is the sole owner of financial calculations. Dashboard visual code (and, later, Power BI/PBIP) must consume canonical metric values, not independently recompute or re-aggregate them | Keep today's pattern (each view aggregates from `detail_records`/`primary.by_channel`/`offtake.by_chain` independently) vs. one canonical layer, many read-only consumers | **APPROVED** — this is the core fix for the pattern that produced 3 of PR #193's 4 defects (two different aggregation paths for what should have been one number) |

**Note on ADR-003** (recorded for the business owner's decision, not as a recommendation this document is making unilaterally): Option C (Primary + Offtake + Gap) is the only option of the three that would make use of the real, currently-idle `D.reliance_brand_counters` Offtake block *and* keep today's Primary-based view, rather than discarding one of the two real data sources this repo already has. Option A matches current behavior with no data change required. Option B would require building a new view from currently-unused data and retiring the current one. Whichever is chosen, `validate_offtake_partition()` (already implemented, already enforces BC ⊆ total Reliance offtake) becomes directly relevant only under B or C.

---

## Three tracks (kept separate, per instruction)

```
TRACK A — Financial truth architecture           [this document; HIGH PRIORITY]
  Design (this doc) → metric contracts (above) → impact analysis
  → canonical fact implementation → reconciliation tests →
  dashboard migration → PBIP alignment

TRACK B — KI-OFFTAKE-001 (Issue #195)             [absorbed into Track A]
  Root-cause mapped above. Fix lands as part of CHAIN_OFFTAKE_NSV's
  canonical implementation, not a standalone patch. Issue stays open
  as the tracking record until then.

TRACK C — github-advanced-security (Issue #194)   [infrastructure, fully separate]
  Not financial logic. Not touched by this design or by Track A/B.
  Revisit independently of the architecture work.
```

---

## Explicitly NOT done in this phase

- No change to `scripts/build_dashboard_data.py`, `dashboard/index.html`, or `dashboard/data.js`.
- No fix to Issue #194 or Issue #195.
- No new dashboard features, no UI redesign.
- No PBIP / Power BI semantic model changes.
- No AI insight layer work.
- No destructive migration of any kind — nothing here proposes deleting `primary.by_channel`, `offtake.by_chain`, or any other existing field; the target state shows canonical metrics sitting *in front of* today's facts, with the question of retiring the older pre-agg paths left to the impact-analysis phase, not decided here.

Verified directly (not asserted): `git diff --stat main` against this entire branch shows only two files added (`docs/CANONICAL_FINANCIAL_TRUTH_DESIGN.md`, `docs/CANONICAL_METRIC_DEPENDENCY_MAP.md`) — zero lines changed in any `.py`, `.html`, `.js`, or `.json` file.

---

## Design Acceptance Gate

```
DESIGN ACCEPTANCE GATE — Canonical Financial Truth Layer
[x] Current-state data lineage documented (Current State section, code-verified)
[x] Seven metric contracts documented
[x] Every metric has authoritative source (or explicit NOT_CURRENTLY_AVAILABLE)
[x] Every metric has explicit grain (or explicit N/A for unavailable metrics)
[x] FY logic defined (THE ONE FY RULE, reused — not redefined)
[x] Unit logic defined (ADR-006)
[x] Null/missing logic defined (ADR-007)
[x] Negative handling defined (real, never floored — per metric contract)
[x] Cross-FY fallback policy defined (ADR-001)
[ ] Reliance BC business meaning resolved (ADR-003 — PENDING BUSINESS OWNER)
[x] Unavailable metrics honestly marked unavailable (ADR-004, ADR-005)
[x] Dashboard consumers mapped (docs/CANONICAL_METRIC_DEPENDENCY_MAP.md)
[x] KI-OFFTAKE-001 incorporated (root-cause mapped, absorbed into CHAIN_OFFTAKE_NSV, not patched)
[x] No code/data/dashboard changes (verified via git diff --stat)

VERDICT: BLOCKED — BUSINESS DECISION REQUIRED (ADR-003 only)
```

Every item is resolved except one: what "Reliance Brand Counter" is supposed to mean. That is a real business-definition question this audit surfaced, not a technical gap — the three options (and the tradeoffs of each) are recorded above for MT Leadership to decide. Nothing else blocks this design from being merged as the architecture contract once that one decision is made; the other 13 gate items are already `APPROVED`/complete and do not need to be re-litigated when ADR-003 resolves.

## Next step (not started by this document)

Once ADR-003 is resolved: mark this Design Acceptance Gate fully passed, merge this PR as the architecture contract, and open a new implementation PR scoped to **only** the canonical metric engine and reconciliation layer (no UI changes) — Phase 1 of the phased rollout below. Phases 2 onward (reconciliation tests, then Executive Cockpit, Performance/Comparison, Inventory/Alerts, Reliance views, and finally PBIP) are each their own gated PR, comparing old output vs. canonical output and blocking on unexplained variance, not implemented together.

```
Phase 1  Canonical contracts + pure calculation layer
Phase 2  Automated reconciliation tests (old output vs. canonical output)
Phase 3  Executive Cockpit migration
Phase 4  Performance / Comparison migration
Phase 5  Inventory / Alerts migration (closes KI-OFFTAKE-001 / Issue #195)
Phase 6  Reliance views (per whatever ADR-003 resolves to)
Phase 7  Power BI / PBIP semantic model alignment
```

The AI insight layer remains downstream of all of this — it explains certified canonical numbers, it never independently calculates them.
