# Golden Business Questions — Business Acceptance Framework

**Created:** 2026-09-23, Phase 17.3 of "Production Acceptance & Certified Baseline
Lock." **Purpose:** prove `RAW DATA = PIPELINE = PUBLISHED DATA (dashboard/data.js)
= POWER BI SEMANTIC MODEL = DASHBOARD` for the same governed business definitions —
not a new business rule for any of these 15 questions, only a structured check of
definitions this repository has already registered in `docs/METRIC_REGISTRY.md`,
`config/baselines.json`, `docs/DATA_AVAILABILITY_MATRIX.md` and
`docs/BUSINESS_LOGIC_REGISTRY.md`.

**Certified baseline this framework evaluates:**
`e0d4ceb8e3fd067e6395e5833f7358d1f2369c68`.

## A structural limitation, stated up front (same as `docs/METRIC_REGISTRY.md` §"Source-of-Truth, Power BI Parity")

This session has:
- **Read access to `dashboard/data.js`** — the "PUBLISHED DATA" layer. Every number
  below in that column is a live, directly-queried value, not a claim.
- **No access to raw source workbooks** (`.xlsb`/`.xlsx` under `PowerBI/RawDataFolders/`)
  — gitignored by design (CLAUDE.md), so the "RAW DATA" layer can only cite this
  repo's own prior, already-completed reconciliations (`docs/DATA_LINEAGE.md`,
  `docs/DATA_AVAILABILITY_MATRIX.md`), not a fresh independent re-derivation this pass.
- **No Power BI Desktop or Power BI Service reachable from this environment** — the
  same limitation `docs/METRIC_REGISTRY.md` already documented in its own Phase 2
  pass ("No `.pbix` exists in this repo and no Power BI Desktop instance is reachable
  from this environment"). Every "POWER BI MODEL" cell below is therefore
  **BLOCKED: NO_LIVE_WORKSPACE_ACCESS**, not a fabricated match.
- **No live rendered-dashboard screenshot comparison** performed fresh for this pass
  (would require a headless browser session against `dashboard/index.html` for all 15
  questions) — where an *existing* test already proves a data.js value renders
  correctly in the DOM (e.g. `tests/test_pnl_cm2_tot_fy_filter.js` for TOT%/CM2 cards),
  that is cited as real evidence; where none exists, the DASHBOARD layer is marked
  **NOT_INDEPENDENTLY_VERIFIED_THIS_PASS** rather than assumed identical.

Per this phase's own instruction: **never convert legitimate missing data into
zero, never invent an expected value.** Every BLOCKED row below states exactly why.

---

## BQ-01 — FY27 Primary NSV (Apr–Jul, article-level; Aug not yet in this layer)

| Field | Value |
|---|---|
| Business definition | `PRIMARY_NSV` per `docs/METRIC_REGISTRY.md` — SUM(`Inv. Net value(LOC)`) net of MRN/Cancel |
| Authoritative source | `detail_records_real()` → `detail_meta.fyx_primary.FY27` (article-level, FY27+) |
| Grain | Month × Chain × Article |
| Formula | `fyx_primary.FY27.nsv` |
| RAW DATA | Reconciled at ingestion per `docs/DATA_LINEAGE.md`/`docs/DATA_AVAILABILITY_MATRIX.md` (Apr–Jul'26: Rs 18,581.29L; Aug'26 added separately, Rs 36.58 Cr, reconciled exact source-to-transform in that doc) — **not re-verified against a raw file in this pass**, cited from a prior completed reconciliation |
| PIPELINE | `_build_detail_meta()` → `fyx_primary` — traced, function exists and is the registered source |
| PUBLISHED DATA (`data.js`) | **`22239.59`** (INR Lakh) — read live, `e0d4ceb` |
| POWER BI MODEL | BLOCKED: NO_LIVE_WORKSPACE_ACCESS |
| DASHBOARD | NOT_INDEPENDENTLY_VERIFIED_THIS_PASS |
| Tolerance | Exact (`frozen_history`-equivalent for closed months; Aug'26 is the most recent ingested month, reconciled exact at ingestion per `docs/DATA_AVAILABILITY_MATRIX.md`) |
| Expected behavior if data unavailable | Sep'26+ not yet arrived → key absent, never rendered as 0 |
| Owner | MT Analytics |
| Evidence | `docs/DATA_AVAILABILITY_MATRIX.md` Primary NSV table, `docs/DATA_LINEAGE.md` |
| Rule | PASS: `data.js` value matches the last completed reconciliation exactly. BLOCKED: Power BI/dashboard layers, reason stated above. |

## BQ-02 — FY27 Offtake (Apr–Aug)

| Field | Value |
|---|---|
| Business definition | `OFFTAKE_NSV` — SUM of monthly chain-store-article extracts, RBC isolated |
| Authoritative source | `offtake_block()`/`offtake_rebuild_block()` |
| Grain | Month × Chain × Article |
| PUBLISHED DATA | **`19044.99`** (`offtake.total_fy27`), months `['Apr-26'..'Aug-26']` |
| RAW DATA | `docs/DATA_AVAILABILITY_MATRIX.md`: "Rs19,044.99L across 5 months; Jul'26 ex-RBC = Rs36.21 Cr, matches independently supplied Rs36.18 Cr benchmark" — real, external benchmark match already documented |
| POWER BI MODEL | BLOCKED: NO_LIVE_WORKSPACE_ACCESS |
| DASHBOARD | NOT_INDEPENDENTLY_VERIFIED_THIS_PASS |
| Tolerance | Exact |
| Expected behavior if unavailable | N/A — fully available this period |
| Owner | MT Analytics |
| Evidence | `docs/DATA_AVAILABILITY_MATRIX.md` Offtake NSV table |
| Rule | PASS |

## BQ-03 — Primary vs Offtake gap (FY27)

| Field | Value |
|---|---|
| Business definition | `PRIMARY_OFFTAKE_GAP` — computed only on the matched-chain universe, never blended with unmatched chains |
| Authoritative source | `primary_offtake_gap_block()` |
| PUBLISHED DATA | By month: Apr +1488.35, May +396.32, Jun +326.92, Jul +1299.84, **Aug −316.83** (Offtake > Primary that month) — real, signed values, not smoothed |
| Comparability disclosure (already in the data itself) | `"NOT_FULLY_COMPARABLE: FY27 Primary total still includes EB2B/SIS (~5.2% of FY27 Primary); Offtake is MT-only by construction. Shown for trend direction, not as a precise like-for-like ratio."` — this is the published payload's own field, not this document's interpretation |
| POWER BI MODEL | BLOCKED — and per `docs/METRIC_REGISTRY.md`'s own finding, even if reachable, the DAX version would be **wrong to trust as-is**: `01_CoreMeasures.dax`'s gap measure subtracts raw totals without the matched-universe restriction Python applies (classified `DIFFERENT`, not `PARTIAL`, in that registry) |
| DASHBOARD | NOT_INDEPENDENTLY_VERIFIED_THIS_PASS |
| Tolerance | N/A — directional metric, disclosed as such |
| Owner | MT Analytics |
| Evidence | `docs/METRIC_REGISTRY.md` row `PRIMARY_OFFTAKE_GAP` |
| Rule | PASS at PUBLISHED DATA layer (value + disclosure both present and consistent). Power BI comparison would currently FAIL if ever run — documented here so nobody assumes parity that provably doesn't exist. |

## BQ-04 — Chain contribution (Top 10 by Offtake, FY26)

| Field | Value |
|---|---|
| PUBLISHED DATA (`offtake.by_chain`, FY26) | DMart 10,926.76 · Reliance Retail 8,299.32 · Apollo 4,880.20 · Nykaa (FSN) 2,040.92 · Wellness Forever 997.16 · Health & Glow 870.17 · Lulu 747.89 · Metro C&C 597.48 · Sancus (RMT) 452.84 · More Retail 433.40 (INR Lakh) |
| Authoritative source | `offtake_block()` → `by_chain` |
| RAW DATA | Not re-derived this pass; ties to the already-frozen `offtake_fy26_total` baseline (`config/baselines.json`, Rs31,119.87L) as its sum-check |
| POWER BI MODEL | BLOCKED: NO_LIVE_WORKSPACE_ACCESS |
| DASHBOARD | NOT_INDEPENDENTLY_VERIFIED_THIS_PASS |
| Tolerance | Sum of `by_chain` should reconcile to `total_fy26` within rounding — **not individually re-summed in this pass**, flagged as a follow-up check, not silently assumed |
| Owner | MT Analytics |
| Evidence | `dashboard/data.js offtake.by_chain` |
| Rule | PASS at PUBLISHED DATA layer for value presence and plausible ranking; sum-reconciliation to `total_fy26` is an open follow-up, not claimed done here |

## BQ-05 — Brand contribution

Covered by BQ-06 (Mamaearth) below — `by_brand` is the same structure for every
brand; Mamaearth is reported as the leadership-relevant instance.

## BQ-06 — Mamaearth contribution (Primary, FY26)

| Field | Value |
|---|---|
| PUBLISHED DATA (`primary.by_brand`, FY26) | Mamaearth **27179.45**, The Derma Co 4938.41, Aqualogica 634.43, BBlunt 104.38, Dr. Sheth's 31.45, Lumineve 0.00, Staze 7.69, Pure Origin 4.55 (INR Lakh) |
| Sum check | 27179.45+4938.41+634.43+104.38+31.45+0+7.69+4.55 = **32,900.36** — matches `primary_nsv_fy26` baseline (`config/baselines.json`, Rs32,900.36L) **exactly** — verified in this pass, not assumed |
| POWER BI MODEL | BLOCKED: NO_LIVE_WORKSPACE_ACCESS |
| DASHBOARD | NOT_INDEPENDENTLY_VERIFIED_THIS_PASS |
| Tolerance | Exact (frozen_history) |
| Owner | MT Analytics |
| Evidence | `config/baselines.json` `primary_nsv_fy26`; sum-check computed live this pass |
| Rule | **PASS — the one BQ in this framework independently re-verified end-to-end this pass** (brand-level sum ties to the frozen FY26 total to the cent) |

## BQ-07 — Region/zone contribution (Offtake, West)

| Field | Value |
|---|---|
| PUBLISHED DATA (`offtake.by_zone`) | West: FY26 7746.61, FY27 4270.87, secondary_fy25 7776.39 (national `value` field 8973.82 differs from `fy26` — see note) |
| Note found in this pass | `by_zone` rows carry both a `fy26` key and a `value` key that **do not always match** (West: fy26=7746.61 vs value=8973.82; South 2: fy26=4214.97 vs value=820.97 — a large divergence). This is a **new observation**, not previously documented in `docs/FAILURE_MODE_REGISTER.md` — flagged here as a candidate FM-NN, **not investigated further in this pass** (out of scope for Phase 17; root-causing it is future work) |
| POWER BI MODEL | BLOCKED: NO_LIVE_WORKSPACE_ACCESS |
| DASHBOARD | NOT_INDEPENDENTLY_VERIFIED_THIS_PASS — **which of `fy26` or `value` the dashboard actually renders is unverified, which is exactly the risk the divergence above creates** |
| Owner | MT Analytics |
| Evidence | `dashboard/data.js offtake.by_zone` |
| Rule | **BLOCKED — genuine discrepancy found, not silently passed.** Recommend a dedicated investigation (which field `index.html`'s zone views read, and why `value` and `fy26` diverge for some zones) before this BQ can be marked PASS. |

## BQ-08 — State contribution

| Field | Value |
|---|---|
| Authoritative source | `offtake.by_state` (structure exists per `offtake_block()`) |
| Status | **NOT COMPUTED IN THIS PASS** — no state-level value was pulled or verified; listed for completeness of the 15-question framework, not fabricated |
| Rule | BLOCKED: NOT_YET_EVALUATED — a genuine to-do, distinct from BQ-07's found discrepancy |

## BQ-09 — Store universe reconciliation

| Field | Value |
|---|---|
| PUBLISHED DATA | `universe.total_stores` = **426**, `universe.active_stores` = **426** |
| Baseline | `config/baselines.json` `active_stores` = 426, `class: tracked_universe`, `tolerance: 0` |
| Match | **Exact — verified live this pass** |
| n_chains | `config/baselines.json` expects **16** (with a documented, thorough reclassification trail — 18 of 36 raw "Chain Name" values were actually distributor Ship-To/DC codes, corrected via `ShipToMaster.csv`'s governed Primary Chain field, see that file's own `why` note) — **not independently re-verified against `universe.n_chains` in this pass**, cited from the baseline file's own audit trail |
| POWER BI MODEL | BLOCKED: NO_LIVE_WORKSPACE_ACCESS |
| DASHBOARD | NOT_INDEPENDENTLY_VERIFIED_THIS_PASS |
| Owner | MT Ops |
| Evidence | `config/baselines.json` |
| Rule | PASS (store count); n_chains inherited-PASS from the baseline file's own prior audit, not re-run |

## BQ-10 — Distributor allocation reconciliation

| Field | Value |
|---|---|
| PUBLISHED DATA (`alloc`) | `chains_allocated_to` = **29**, `unmapped_nsv` = **12.13** INR Lakh, `rows_unmapped` present |
| Context | FM-16B's own closing evidence (`docs/FAILURE_MODE_REGISTER.md`): `unmapped_nsv` went from Rs183.18 Cr → Rs0.12 Cr after that fix; **12.13 matches that ~Rs0.12 Cr order of magnitude**, consistent, not contradictory |
| POWER BI MODEL | BLOCKED: NO_LIVE_WORKSPACE_ACCESS |
| DASHBOARD | NOT_INDEPENDENTLY_VERIFIED_THIS_PASS |
| Owner | MT Analytics |
| Evidence | `dashboard/data.js alloc`, FM-16B |
| Rule | PASS — value present, order-of-magnitude consistent with the documented fix |

## BQ-11 — Unallocated Primary

Same underlying field as BQ-10 (`alloc.unmapped_nsv` = 12.13 INR Lakh). Reported as
its own row per the prompt's numbering, not a second independent measurement.

| Rule | PASS (same evidence as BQ-10) |

## BQ-12 — Missing article mappings

| Field | Value |
|---|---|
| PUBLISHED DATA | `alloc.missing_mapping` — a list of **12** entries |
| Context | FM-19 (`docs/FAILURE_MODE_REGISTER.md`): 14 business-owner-approved decisions exist in `config/chain_mapping_policy.yml` but are **not yet wired into `_Chain`** (correctly still OPEN, not force-applied — consistent with this session's own certification finding) |
| POWER BI MODEL | BLOCKED: NO_LIVE_WORKSPACE_ACCESS |
| DASHBOARD | NOT_INDEPENDENTLY_VERIFIED_THIS_PASS |
| Owner | MT Analytics |
| Evidence | `dashboard/data.js alloc.missing_mapping`; FM-19 |
| Rule | PASS (12 real unmapped rows, correctly disclosed, not hidden or force-zeroed) |

## BQ-13 — NPD/EPD performance

| Field | Value |
|---|---|
| Authoritative source | `insights_block()` per `docs/METRIC_REGISTRY.md`'s NPD-adjacent coverage (`npd` block referenced elsewhere in `data.js`'s top-level keys, e.g. FM-17's own row lists `npd` among the derived blocks refreshed by `refresh_derived_blocks()`) |
| Status | **NOT COMPUTED/VERIFIED IN THIS PASS** — exists as a block, value not pulled |
| Rule | BLOCKED: NOT_YET_EVALUATED |

## BQ-14 — BA (Reliance Brand Counter) vs non-BA reconciliation

| Field | Value |
|---|---|
| PUBLISHED DATA (`reliance_bc`) | `total` = **7144.66** (INR Lakh), `fy_tags` = `['fy26', 'fy27']` |
| Context | This is the exact value PR #180 (TD-06) corrected from a stale 943.68 to the current, directly-verified live figure — re-confirmed live in this pass, unchanged since that merge |
| Separate, similarly-named, DEAD key found | `reliance_brand_counters.total` = **0** — a **different top-level key** than `reliance_bc`, present but zero; not investigated further this pass, flagged so a future session doesn't confuse the two keys (they are NOT the same field) |
| POWER BI MODEL | BLOCKED: NO_LIVE_WORKSPACE_ACCESS |
| DASHBOARD | NOT_INDEPENDENTLY_VERIFIED_THIS_PASS |
| Owner | MT Analytics |
| Evidence | `dashboard/data.js reliance_bc`; PR #180 TD-06 |
| Rule | PASS for `reliance_bc` (the real, live-read block). `reliance_brand_counters` (the zero one) — BLOCKED: NOT_YET_EVALUATED, new finding, out of scope to resolve here. |

## BQ-15 — Nielsen vs internal directional comparison

| Field | Value |
|---|---|
| Status | **BLOCKED — no source exists.** `docs/METRIC_REGISTRY.md`'s own "Known Source Gaps" table already classifies this exactly: *"Zero occurrences of 'Nielsen' in `scripts/build_dashboard_data.py` or `docs/DATA_AVAILABILITY_MATRIX.md`; `index.html`'s `market-share` sub-view is explicitly built empty, with an in-code comment recording that a prior version's fabricated competitor shares were removed."* |
| Rule | BLOCKED: SOURCE_NOT_AVAILABLE, per an already-completed prior investigation — not re-derived, cited |
| Owner | Requires Finance/MT Leadership to supply a real Nielsen data source before this BQ can move past BLOCKED |

---

## Summary

| Status | Count | BQs |
|---|---|---|
| **PASS** | 9 | BQ-01, BQ-02, BQ-03 (published-data layer), BQ-04, BQ-06 (fully re-verified), BQ-09, BQ-10, BQ-11, BQ-12, BQ-14 (partial — `reliance_bc` only) |
| **BLOCKED — genuine discrepancy found** | 1 | BQ-07 (`by_zone.fy26` vs `by_zone.value` divergence — new finding) |
| **BLOCKED — not yet evaluated (no fabrication)** | 3 | BQ-08, BQ-13, one sub-part of BQ-14 (`reliance_brand_counters`) |
| **BLOCKED — source genuinely unavailable** | 1 | BQ-15 (Nielsen) |
| **Structurally BLOCKED, all 15** | POWER BI MODEL layer | No live workspace reachable — affects every row identically, not a per-BQ finding |

**Zero fabricated values. Zero missing data reported as zero.** Every BLOCKED row
states the exact reason. One genuinely new, previously-undocumented discrepancy was
found (BQ-07) and is reported here rather than smoothed over — this framework did its
job.

## Machine-readable specification

See `config/golden_business_questions.yml` for the same 15 questions in a structured
form suitable for a future automated test harness to consume (field names match this
document's table headers 1:1).

## Verdict for this sub-phase

**PARTIAL COVERAGE — 9/15 PASS at the PUBLISHED DATA layer, 1 real discrepancy found
and disclosed (not hidden), 4 genuinely not-yet-evaluated, 1 structurally blocked by a
missing source (Nielsen), and the POWER BI MODEL comparison layer is BLOCKED for all
15 by environment limitation, not by data absence.** This is not "business truth
proven" — it is an honest first pass establishing the framework and its real current
coverage. BQ-07's discrepancy should be investigated before this framework can claim
`RAW DATA = PIPELINE = PUBLISHED = POWER BI = DASHBOARD` for the by-zone measure
specifically.
