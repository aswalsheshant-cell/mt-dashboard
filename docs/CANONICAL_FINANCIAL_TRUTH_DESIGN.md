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

  ⚠ OBSERVED (found while grounding this design, not yet filed as a
  separate defect — see KI-OFFTAKE-001 mapping below): in the certified
  baseline's dashboard/data.js, offtake.total is a FLAT NUMBER
  (31119.88), not the nested {fy26:…, fy27:…} dict offtake_block()'s
  own code produces. The dashboard's own JS already defends against
  this (`o?.total?.[fyR] ?? o?.[`total_${fyR}`] ?? 0` falls through to
  the flat key when the nested lookup misses) — which is exactly why
  PR #193's KPI fix worked. But the underlying inconsistency — one
  full-build code path producing a nested shape, one routine-refresh
  code path never maintaining it, and the dashboard silently coping —
  is the same class of problem as the Top Chains stale-fallback
  (KI-OFFTAKE-001), just one layer up.

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
  CHAIN_OFFTAKE_NSV's fallback policy was never made explicit anywhere
  in the codebase — the JS fallback chain was written defensively
  ("give me SOME number") rather than correctly ("give me THIS FY's
  number or say so"). The same permissive instinct produced the
  offtake.total nested-vs-flat drift documented in the Current State
  section above: both are "if the exact field is missing, reach for
  whatever's nearby" instead of "if the exact field is missing, that's
  a real gap, report it as one."
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

## Next step (not started by this document)

Dependency / impact analysis: for each of the 7 metrics above, enumerate every current dashboard call site (JS) and every current `build_dashboard_data.py` function that reads or writes the underlying fields, so the implementation phase knows exactly what a canonical accessor must not break. That analysis, the canonical fact implementation, and the dashboard migration are separate future PRs, each gated on review of the one before it — starting with review of this design document.
