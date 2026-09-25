# Phase 2B-A — Canonical Financial Truth Consumer Inventory

**Read-only discovery. No production edits, no legacy deletion, no new financial
calculations, no consumer switching, no dashboard redesign, no remediation.** This
document is the inventory and recommended remediation order only — Phase 2B-B
(actually acting on any finding) requires separate, explicit approval.

**Scope covered exhaustively:** every consumer of `D.offtake.by_chain` (the
`CHAIN_OFFTAKE_NSV`/`OFFTAKE_NSV` lineage Phase 1/2A built canonical coverage for);
every consumer surfaced by that trace touching a second, third, fourth or fifth
independent financial-truth source (Primary chain NSV, the pre-built
Primary-vs-Offtake gap block, `sales_actuals_block()`); `dashboard/mobile.html` in
full; the `PowerBI/DAX/` and `PowerBI/PowerQuery/` directories for chain-level
NSV/offtake measures and queries; and `scripts/build_dashboard_data.py`'s chain-level
writer functions, including the Python-side missing-vs-zero mechanics upstream of
every JS/DAX consumer (F14 — the deepest finding, not yet empirically resolved).
**Scope covered at lighter depth, explicitly flagged, not silently assumed clean:**
P&L NSV (`D.pnl.by_chain`), TOT% (`D.tot.by_chain`), Promo (`D.promo.by_chain`),
Category & Pack, Reliance Brand Counter (non-canonical paths), Demand Forecast,
Competitive Landscape, Correlations/elasticity (`corr.by_chain`) — these are real, separate
financial-truth domains this pass did not attempt to fully re-trace to the same
depth as the Offtake/Primary chain lineage; see "Deliberately not yet classified"
below rather than a false `0 UNKNOWN` claim across the whole dashboard.

---

## Findings

### F1 — `dashboard/index.html:1618` (`renderInventorySubview`, "Top Chains by Offtake" table)

| Field | Value |
|---|---|
| Function/symbol | `renderInventorySubview()`'s `chainData` map, `canonicalChainOfftakeNSV()` |
| Input source | `D.offtake.by_chain[]`, exact `<fy>`-keyed field only |
| Output consumer | Inventory & Supply Health → Offtake Velocity → "Top Chains by Offtake" table + bar chart |
| Canonical lineage | Ports `scripts/canonical/offtake.py::chain_offtake_nsv()` / `policies.py::exact_fy_or_not_available()` to JS |
| Missing-data behaviour | Returns `null`, chain excluded from ranking — never a fabricated 0 or stale `.value` |
| Financial impact | None — this is the fixed state (Phase 2A, PR #199) |
| **Classification** | **CANONICAL_CONSUMER** |
| Recommended action | None. Already migrated and certified (`docs/PHASE2A_POST_MERGE_CERTIFICATION.md`). |
| Evidence | `docs/PHASE2A_CHAIN_OFFTAKE_LINEAGE.md`; live-verified FY27=31/FY26=27 chains |

### F2 — `dashboard/index.html:3757-3794` (`computeChannelHealth()`) — Issue #200

| Field | Value |
|---|---|
| Function/symbol | `computeChannelHealth()` |
| Input source | `D.offtake.by_chain[]` (offtake side) **and** `D.primary.by_chain[]` or `D.detail_meta.same_period.by_chain[]` (primary side) — **two independent financial-truth sources in one function** |
| Output consumer | Commercial Analytics tab, `cvHealth` chart; also called a second time inside `generateAnalyticsInsights()` (line ~3815, ~3865) feeding the "Inventory Imbalance" insight-card logic |
| Canonical lineage | **None.** Reads raw `by_chain` arrays directly, no canonical engine involvement |
| Missing-data behaviour | Offtake side (line 3771-3774): `off[r.name]=(offKey&&r[offKey]!=null)?r[offKey]:r.value;` — falls back to `.value` (all-months-combined, no FY subscript) exactly like the pre-fix KI-OFFTAKE-001 expression, when the real FY-keyed field is absent. Primary side (line 3775-3780): `pri[r.name]=fy?r[fy]:r.value;` when no FY filter is active, **also** falls back to `.value`; when a specific FY *is* selected, `r[fy]` with no fallback at all (missing → `undefined`, later defaulted via `p=pri[c]\|\|0`). |
| Financial impact | **CORRECTED in Phase 2B-A2 (`docs/SOURCE_MISSINGNESS_LINEAGE.md`) — does NOT currently produce a visible wrong number.** Tracing `D.primary.by_chain`'s actual shape shows it has zero FY27 coverage on any of its 45 rows and no `.value` field at all — so the Primary side's `p` resolves to `0` for every chain at FY27, and the `p>0&&o>0` ratio guard filters everything out regardless of what the offtake side does. At FY26, `GOV-005`'s 8 chains lack both `fy26` *and* `.value` on the offtake side, so `o=0` there too — also safely filtered. Result: `computeChannelHealth()` currently renders an **empty** list at the FYs where a wrong ratio might otherwise appear, not a populated wrong one. **The underlying code defect is still real** — one data-shape change (e.g. Primary gaining FY27 coverage) away from firing — so this is closer to F8/F10's "landmine" character than a live-today wrong number. |
| **Classification** | **UNCONTROLLED_FINANCIAL_TRUTH** (the offtake-side accessor specifically; unsafe by construction even though today's data shape happens not to trigger it; the ratio/status/color derivation around it is a `DERIVED_ANALYTIC` built on that one uncontrolled input) |
| Recommended action | **Revised per F6's resolution**: do not build a third independent fix. Point `computeChannelHealth()`'s Primary side at `fyx_primary`-derived data (the same real FY27 source `primary_offtake_gap_block()` already uses correctly) and its Offtake side at the same governed, no-fallback accessor `dashboard/index.html:1618` already uses. Ideally, replace this function's per-chain computation with a read of `D.primary_offtake_gap`'s already-correct, already-governed by-chain data instead of recomputing a parallel version. Needs its own shadow comparison first (produces a *ratio*, not a raw NSV total) |
| Evidence | Direct code reading, this session, 2026-09-24; `docs/SOURCE_MISSINGNESS_LINEAGE.md`'s F14 resolution (the correction above); corroborates and supersedes `docs/VISUAL_REGISTRY.md` finding #8 |

**Secondary, lower-severity finding in the same function:** `generateAnalyticsInsights()` (line ~3830) filters `health.filter(h=>h.status==='Overstocked')`, but `computeChannelHealth()`'s actual status values are `'No data'` / `'Selling out faster than billed'` / `'Billed ahead of sell-out'` / `'Balanced'` — never the literal string `'Overstocked'`. This filter can never match; the "Inventory Imbalance" insight card can never fire. Dead logic, not a wrong-number defect (classification: **DISPLAY_ONLY**, bug but not a financial-truth risk) — matches `docs/VISUAL_REGISTRY.md` finding #7, confirmed still present at current line numbers.

### F3 — `dashboard/index.html:1330-1373` ("Top Chains by Primary NSV" table)

| Field | Value |
|---|---|
| Function/symbol | `renderChannelSubview()`'s `sv==='primary'` branch, `validChains`/`sorted` |
| Input source | `D.primary.by_chain[]` |
| Output consumer | Channel & Chain Performance → Primary Sales subview — "Top Chains by Primary NSV" table, "Cumulative Rank & Running Total" table |
| Canonical lineage | Partial — the canonical engine has `PRIMARY_NSV`/`CHANNEL_PRIMARY_NSV`/`RBC_PRIMARY_NSV` but **no `CHAIN_PRIMARY_NSV` metric**; this consumer has no canonical counterpart to migrate to yet |
| Missing-data behaviour | Per-chain: `(c[primYr]\|\|0)` (missing → 0, same class as ADR-007 forbids, but at least doesn't fabricate a *non-zero* stale figure). **Whole-FY fallback** (line 1336-1345): if **every** chain lacks the selected FY entirely, the code explicitly reassigns `validChains=chains.filter(c=>c[fallbackFy]!=null).map(c=>({...c,[primYr]:c[fallbackFy]}))` — i.e. **silently relabels the prior FY's data as if it were the current FY**, a real cross-FY fallback (the exact pattern ADR-001 forbids for the canonical engine), pre-existing and intentional (comment: "fallback to prior FY if empty"), not introduced by Phase 2A |
| Financial impact | Only triggers when an entire FY has zero primary chain rows (a coarse, rare condition — not per-chain like F1/F2's KI-OFFTAKE-001 pattern). No evidence yet that this has actually fired in the certified `data.js` (FY26/FY27 both have real primary chain data) |
| **Classification** | **UNCONTROLLED_FINANCIAL_TRUTH** (a real, independent cross-FY fallback exists, even though not currently triggered) |
| Recommended action | Lower priority than F2 (not currently live, coarser trigger condition). Worth a canonical `CHAIN_PRIMARY_NSV` metric in a future phase if this table is ever migrated; until then, document the fallback condition clearly so a future data gap doesn't silently relabel FYs |
| Evidence | Direct code reading, this session, 2026-09-24 |

### F4 — `dashboard/index.html:3536` (`fy25SecondarySection()`)

| Field | Value |
|---|---|
| Input source | `D.offtake.by_chain[]`, filtered to `c.secondary_fy25` only |
| Output consumer | Performance & Comparison tab, FY25 Secondary chain/brand view |
| Missing-data behaviour | Reads only the `secondary_fy25` field directly; chains lacking it are filtered out, never defaulted to 0 or substituted |
| **Classification** | **DISPLAY_ONLY** (already safe — no fallback-to-`.value`/`.total`/`0` pattern) |
| Recommended action | None |
| Evidence | Confirmed in `docs/PHASE2A_CHAIN_OFFTAKE_LINEAGE.md`'s original lineage trace (consumer #3), re-confirmed this pass |

### F5 — `dashboard/index.html:1717,1726` (dead `by_chain` computations)

| Field | Value |
|---|---|
| Input source | `Object.keys(o.by_chain\|\|{})` / `Object.keys(D.offtake?.by_chain\|\|{})` |
| Output consumer | **None** — the `chains` parameter these compute is passed into `renderInventorySubview()`/discarded in `switchInventorySubview()` but never referenced in either function body |
| Missing-data behaviour | N/A — the underlying `Object.keys()`-on-an-array bug (same class VISUAL_REGISTRY.md already flagged for the now-fixed F1 site) exists here too, but has zero downstream effect since the result is unused |
| **Classification** | **DISPLAY_ONLY** (dead code, zero financial impact — confirmed by tracing every reference to the `chains` parameter in both function bodies) |
| Recommended action | Cosmetic cleanup only, no urgency; safe to remove in a future pass, not a Phase 2B-B item |
| Evidence | Direct code reading, this session, 2026-09-24 — grepped both function bodies for `chains` usage, found none beyond the computation itself |

### F6 — `D.primary_offtake_gap` vs. `computeChannelHealth()` — duplicate financial-relationship computation

| Field | Value |
|---|---|
| Function/symbol | `primaryOfftakeGapSection()` / `renderPogGapCharts()` (`dashboard/index.html:3499,3592`) read a **separately pre-built, Python-side** `D.primary_offtake_gap` block |
| Output consumer | Performance & Comparison tab, `pogMonthChart` + table |
| Canonical lineage | None — a third, independent computation of "is Primary keeping pace with Offtake" (alongside F2's client-side ratio and F1's canonical `CHAIN_OFFTAKE_NSV`) |
| Missing-data behaviour | **Resolved in Phase 2B-A2** — `primary_offtake_gap_block()` (`build_dashboard_data.py:2702-2799`) sources FY27 Primary from `fyx_primary`/`detail_meta.fyx_primary` (the **correct** real article-level source, unlike F2's use of `D.primary.by_chain` which has zero FY27 coverage), and never falls back to `.value`/`.total` on either side. Its `matched`/`primary_only`/`offtake_only` three-way split means a chain missing on either side is never blended into a fabricated ratio. One minor gap: `{c["name"]: c["fy26"] for c in ... if c.get("fy26")}` treats a real `0` the same as missing (both falsy), so a genuinely-zero chain is silently excluded from all three buckets — undercounts coverage, never fabricates a wrong number |
| **Classification** | **RESOLVED — `DERIVED_ANALYTIC`, legitimately different from `computeChannelHealth()`**, not `UNCONTROLLED_FINANCIAL_TRUTH` duplication. Same general business question, different grain handling, different (correct) FY27 source, and — critically — `primary_offtake_gap_block()` is the more correct of the two: it doesn't share F2's defect |
| Recommended action | Consolidate rather than fix independently: point `computeChannelHealth()` (F2) at this block's already-governed by-chain data instead of maintaining a second, less-correct computation. Full detail and remediation proposal in `docs/SOURCE_MISSINGNESS_LINEAGE.md` |
| Evidence | `docs/VISUAL_REGISTRY.md` finding #8 (pre-existing, 2026-09-13, never resolved); `docs/SOURCE_MISSINGNESS_LINEAGE.md`'s full F6 trace, this session, 2026-09-24; `build_dashboard_data.py:2702-2799`, `dashboard/index.html:1063-1073,3499-3501,3592-3595` |

---

### F7 — `dashboard/index.html:1555` (`buildInventoryHealth`, "Total Offtake" headline KPI)

| Field | Value |
|---|---|
| Function/symbol | `buildInventoryHealth()`, `total` |
| Input source | `o?.total?.[fyR] ?? o?.[`total_${fyR}`] ?? 0` — both lookups are genuinely FY-specific (nested vs. flat schema variants of the same real field), **not** the KI-OFFTAKE-001 all-months substitution |
| Output consumer | Inventory & Supply Health tab's headline "Total Offtake" KPI tile (line ~1571) |
| Missing-data behaviour | The trailing `?? 0` turns an honest gap into a fabricated headline figure: if neither FY-specific field exists, the KPI reads **"₹0.00 Cr"** instead of "–" |
| Financial impact | **Real and live, on a headline KPI** — more visible than F2's chart-level defect. Currently masked because `total_<fy>` is populated for both certified FYs today, but the display logic itself does not distinguish "genuinely zero" from "not available" |
| **Classification** | **UNCONTROLLED_FINANCIAL_TRUTH** (the lookup itself is safe; the `?? 0` display coercion is the defect) |
| Recommended action | Small, low-risk fix: change `?? 0` to `?? null` and render `'–'` when null, mirroring F1's pattern exactly. No shadow comparison needed — this is a display-layer fix, not a calculation change |
| Evidence | Sub-agent code trace, 2026-09-24 |

### F8 — `dashboard/mobile.html:769` — hardcoded fake growth badge

| Field | Value |
|---|---|
| Function/symbol | RBC-Total KPI growth badge |
| Input source | **None** — `badge.textContent = '▲ +10.7%'` is a **literal hardcoded string**, gated only by `D.yoy_metrics.status==='active'` |
| Output consumer | Mobile dashboard, RBC-Total KPI tile |
| Missing-data behaviour | N/A — this isn't a missing-data fallback, it's a fabricated number with no data backing it at all |
| Financial impact | **Currently dormant** — `D.yoy_metrics` does not exist anywhere in `build_dashboard_data.py` or `data.js`, so the gate never opens. **If that field is ever populated for an unrelated reason, this renders a fixed fake +10.7% forever**, independent of real data — a worse class than any fallback found in this inventory (a permanently wrong number baked into source, not a stale or defaulted one) |
| **Classification** | **UNCONTROLLED_FINANCIAL_TRUTH** (dormant but severe if triggered) |
| Recommended action | Remove the hardcoded literal now, regardless of dormancy — a fabricated number waiting on an unrelated future field to activate it is exactly the kind of landmine this inventory exists to find before it fires, not after |
| Evidence | Sub-agent code trace, 2026-09-24 |

### F9 — `dashboard/mobile.html` — entire "Top Chains" feature is dead (schema mismatch)

| Field | Value |
|---|---|
| Function/symbol | Mobile "Top Chains" tables (Overview ~795-818, Primary ~841-868, Offtake ~907-936) |
| Input source | `D.by_chain` — but `mobile.html` has no `<script src="data.js">` anywhere; `window.DASH`'s real top-level keys are `primary`, `offtake`, `universe`, etc. — there is no top-level `D.by_chain`, `D.offtake_total`, `D.primary_total`, or `D.rbc` |
| Missing-data behaviour | `if(D.by_chain)` is always false; the tables silently render nothing — not shown as a gap, just empty. `data.nsv\|\|0`/`data.offtake\|\|0` inside those loops (lines 810, 859, 926) are latent (unreachable) missing-to-zero coercions — milder than F1's pre-fix pattern (no wrong nonzero) but would need fixing too if the schema mismatch is ever corrected |
| Financial impact | None today (dead code) — but "Total Offtake"/"Total Primary" mobile KPIs (`D.primary_total ? ... : '–'`, lines 778, 783, 896) are correctly en-dash-guarded, a genuinely good pattern, currently moot since those fields don't exist either |
| **Classification** | **DISPLAY_ONLY** (dead, zero current financial impact) with one **UNKNOWN** sub-item — whether `mobile.html` is meant to be wired to `data.js` at all, or is an intentionally separate/unfinished surface, wasn't determined this pass |
| Recommended action | Not a Phase 2B-B priority (dead code can't display wrong data). Worth a one-line question to the business/product owner: is mobile.html still an active surface? If yes, the schema mismatch needs fixing before any of its financial displays can be trusted; if no, it's cleanup-list material |
| Evidence | Sub-agent code trace, 2026-09-24 |

### F10 — `PowerBI/DAX/07_PrimaryAllocation_Measures.dax:48-70` — dormant double-allocation risk

| Field | Value |
|---|---|
| Function/symbol | `Raw ShipTo Primary = COALESCE(BLANK(), [Ship-to Primary NSV])`, consumed by `Allocated Primary (via Cont%)` |
| Missing-data behaviour | Documented as a placeholder until an un-split feed exists. If `Allocated Primary (via Cont%)` is ever surfaced while the raw feed stays unpopulated, it multiplies an **already chain-split** NSV by the Cont% allocation a second time — a silent **double-application of an allocation percentage**, producing a wrong nonzero, not a gap |
| Financial impact | Dormant (not currently surfaced per the sub-agent's trace) but the exact same "landmine waiting on an unrelated trigger" shape as F8 |
| **Classification** | **UNCONTROLLED_FINANCIAL_TRUTH** (dormant) |
| Recommended action | Confirm whether `Allocated Primary (via Cont%)` is used in any live Power BI report page; if so, treat as high priority; if not, document the landmine clearly in the DAX file itself so a future editor doesn't surface it without noticing |
| Evidence | Sub-agent code trace, 2026-09-24 |

### F11-F13 — lower-severity findings (Power BI grain-matched zeros, zone allocation, per-row NSV defaults)

| # | Location | Pattern | Classification | Note |
|---|---|---|---|---|
| F11 | `PowerBI/PowerQuery/43_SecondarySalesEfficiency.pq:57-58` | `Table.ReplaceValue(...,null,0,...)` after a `JoinKind.FullOuter` on Chain×Brand×Month | DERIVED_ANALYTIC | A genuine grain-matched zero (row absent from an exact-key join side), not a scope-mismatched substitution — but can't distinguish "genuinely zero" from "month hasn't loaded yet." Lower severity; worth monitoring, not urgent |
| F12 | `dashboard/index.html:1136,1138-1139` | `Number(z.fy26)\|\|0`, `Number(z.fy27)\|\|0` (Zone Forecast Allocation) | DERIVED_ANALYTIC | Zone-grain (not chain), feeds a forecast-cascade share calc — a zone silently gets 0% share instead of a flagged gap. Secondary-order, not a headline NSV figure |
| F13 | `dashboard/index.html:1458,3810,4243` (`r.NSV\|\|0`), `PowerBI/DAX/09_ArticleAllocation_Eligibility.dax` (`COALESCE(...,0)`) | Per-row/per-article NSV null-to-zero before aggregation | DISPLAY_ONLY / standard practice | Standard "null cell contributes 0 to a sum" pattern at the finest grain, not a chain/FY-total substitution — outside the KI-OFFTAKE-001 risk class entirely |

### F14 — `scripts/build_dashboard_data.py` — the Python-side root cause — **RESOLVED (Phase 2B-A2)**

| Field | Value |
|---|---|
| Function/symbol | `primary_block()`'s `dim_rows()` (`pv.pivot_table(...).fillna(0)`, line 776-789, **the only Primary chain-level writer — no incremental alternative exists**); `offtake_block()`'s `fy_sum` (862-888, dormant default-rebuild path); `offtake_rebuild_block()`'s `dim_rows()` (2192-2206, dormant `--offtake-rebuild` path); `patch_offtake_new_months()` (1417-1527, **the actual live pipeline**) |
| Input source | The raw pivot/aggregation step that produces every `by_chain[]` row, upstream of ANY client-side (JS/DAX) logic |
| Missing-data behaviour | **MIXED, now proven per writer, not assumed** — full trace, controlled pandas fixtures (Cases A-F), and empirical checks against the real certified `data.js` in `docs/SOURCE_MISSINGNESS_LINEAGE.md`. Summary: `patch_offtake_new_months()` (live) is **clean** — only iterates chains present in the new source, never fabricates a key. `primary_block()`'s `dim_rows()` (live, no alternative) **does fabricate** — `fillna(0)` guarantees every chain gets every FY tag key, confirmed empirically (2 chains, `Dabur New U`/`Medanta`, show `fy26: 0`, indistinguishable from real-zero without raw-source access). `offtake_block()`/`offtake_rebuild_block()` (both dormant today) carry the same fabrication risk if ever invoked |
| Financial impact | **Offtake side: none** — `CHAIN_OFFTAKE_NSV`'s `GOV-003`/`GOV-005` classifications (Phase 1/2A) are confirmed correct and unaffected; the live pipeline never fabricates. **Primary side: confirmed live**, at least 2 chains affected in the current `data.js`, magnitude beyond that unverified without raw source access (out of this pass's scope). **Bonus finding**: resolving F14 also corrected F2's severity — see F2's updated entry above |
| **Classification** | **RESOLVED — MIXED, not UNKNOWN.** Live offtake pipeline clean; live primary pipeline confirmed fabricating; two dormant offtake writers carry latent risk |
| Recommended action | Fix `primary_block()`'s `dim_rows()` to track which (chain, FY) pairs genuinely appeared in the source before filling, matching `exact_fy_or_not_available()`'s semantics on the Python side. This is a `data.js`-shape change needing its own shadow comparison (Phase 2A's exact playbook), not a quick patch. Document (or fix) `offtake_block()`/`offtake_rebuild_block()` before either is ever invoked again. Full proposal in `docs/SOURCE_MISSINGNESS_LINEAGE.md` |
| Evidence | `docs/SOURCE_MISSINGNESS_LINEAGE.md` — full lineage trace, controlled pandas fixtures (this session, 2026-09-24), and empirical cross-checks against the real certified `data.js` |

Also confirmed by this trace: `offtake_block()` (line 882, the older/default full-rebuild path) and `offtake_rebuild_block()`'s `dim_rows()` (line 2202) both still unconditionally emit the all-months-combined `total`/`value` field on every row — the exact field F1's canonical fix had to explicitly exclude and F2 (`computeChannelHealth()`) still reads. And `sales_actuals_block()` (line 4248) is a **fourth, genuinely separate** chain-level sales computation (with its own DMS/Massit gap-fill and an explicit `NO_SALES_DATA` bucket, not a silent zero) — live code, but reached only via `scripts/ingest_massit_sales.py`, outside `build_dashboard_data.py`'s own `main()` / the `--offtake-patch`/rebuild CLI flow. Not yet reconciled against F1/F2's sources; noted as a fifth potential "competing truth" candidate alongside F6.

## Deliberately not yet classified (real domains, not silently assumed clean)

These are genuine financial-truth-bearing surfaces this pass did not trace to F1-F14's
depth. Listed so the exit criteria below is honest about what it actually covers,
rather than claiming whole-dashboard coverage from a keyword sweep:

- **P&L NSV** (`D.pnl.by_chain`, `dashboard/index.html:2114-2127`) and **TOT%**
  (`D.tot.by_chain`) — separate, pre-existing, already-certified pipeline (PR #193),
  not part of Offtake/Primary chain lineage. Uses simple `\|\|0` patterns at a glance;
  not deep-traced for cross-FY fallback in this pass.
- **Promo** (`D.promo.by_chain`) — Promo Intensity by Chain table; not an NSV/offtake
  figure, lower financial-truth relevance.
- **Correlations/elasticity** (`corr.by_chain`) — Commercial Analytics promo-elasticity
  section; derived analytics over Promo/Primary data, not raw Offtake NSV.
- **Category & Pack Mix, Reliance Brand Counter (non-`RBC_OFFTAKE_NSV`/`RBC_PRIMARY_NSV`
  paths), Demand Forecast, Competitive Landscape** — not searched this pass.
- **`02_PnL_Measures.dax`, `04_Nielsen_Measures.dax`** — COALESCE-to-default patterns
  found but out of scope (margin-assumption %/market-share, not chain offtake/primary
  NSV); noted, not traced further.
- **`sales_actuals_block()`'s reconciliation against F1/F2/F6's sources** (see F14) —
  a fifth potential competing-truth candidate, not yet compared.

## Canonical/test infrastructure (all `scripts/canonical/` and `tests/canonical/`)

Every file under `scripts/canonical/` and `tests/canonical/` is, by construction,
either **CANONICAL_CONSUMER** (the metric functions themselves — `primary.py`,
`offtake.py`, `phase2_chain_offtake.py`), **TEST_FIXTURE** (everything under
`tests/canonical/`), or a deliberate, documented **LEGACY_ROLLBACK** replica
(`scripts/canonical/existing.py`, which intentionally reproduces the pre-fix legacy
JS expressions in Python *for reconciliation comparison only* — never executed in
production, verified via `grep -r "canonical\." dashboard/ scripts/build_dashboard_data.py`
returning zero matches outside this migration's own JS port). None of these require
individual line-by-line inventory entries — their purpose and lineage is already
fully documented in `docs/CANONICAL_ENGINE_PHASE1_REPORT.md`.

---

## Summary against Phase 2B-A exit criteria

```
0 UNKNOWN                        MET (as of Phase 2B-A2) -- F6 and F14 both resolved
                                  with real evidence in docs/SOURCE_MISSINGNESS_LINEAGE.md.
                                  F14: MIXED, not UNKNOWN (live offtake pipeline clean,
                                  live primary pipeline confirmed fabricating, 2 dormant
                                  offtake writers carry latent risk). F6: RESOLVED --
                                  legitimately different implementations, one more
                                  correct than the other, not silent duplication.
                                  sales_actuals_block()'s own policy remains an open,
                                  lower-priority new item (not one of the two required
                                  exits)
0 unexplained financial truth
sources                          MET for the required scope -- F6's "3 independent
                                  computations" is now explained (not merely described):
                                  one is provably more correct than the others, and the
                                  fix path is consolidation, not parallel patching
100% financial consumers
classified                       SUBSTANTIALLY EXPANDED -- F1-F14 fully classified,
                                  F2/F6/F14 corrected/resolved with deeper evidence.
                                  Still explicitly open: P&L, TOT%, Promo, Correlations,
                                  Category&Pack, Reliance (non-canonical paths), Demand
                                  Forecast, Competitive Landscape, two PowerBI DAX files,
                                  sales_actuals_block()'s missing-data policy
Every fallback path explicitly
identified                       F1 (fixed), F2 (landmine, not live-today), F3
                                  (dormant), F5 (dead code), F7 (live KPI defect), F8
                                  (dormant, hardcoded fake number), F9 (dead), F10
                                  (dormant double-allocation), F11-F13 (lower severity)
                                  -- all identified with exact expressions
Every missing->zero
transformation identified        F2, F3, F7, F9, F12, F13, and now F14 (the source-level
                                  case, resolved per writer function) all identified with
                                  exact expressions and, for F14, controlled fixtures
Issue #200 lineage proven        YES -- F2, corrected twice: once for more precision
                                  than the original Phase 2A trace, once more in Phase
                                  2B-A2 to correct an overstated "live today" claim once
                                  the full primary-side data shape was traced
No production behavior changed   YES -- zero files outside this docs/ commit touched
```

**Verdict: PHASE 2B-A2 DISCOVERY EXIT GATE MET.** `UNKNOWN = 0` for the two required
items (F6, F14). Phase 2B-B (controlled remediation) may now proceed, in the order
below, subject to separate explicit approval per item — this document still does not
implement anything.

## Recommended remediation order (Phase 2B-B, pending approval)

1. **`primary_block()`'s `dim_rows()` fix** (the F14 root cause) — should land before
   F2's UI fix, since F2's correct behavior depends on Primary chain data no longer
   fabricating zeros the moment FY27 coverage is added there. This is a `data.js`-shape
   change needing its own shadow comparison (Phase 2A's exact playbook), not a quick
   patch. See `docs/SOURCE_MISSINGNESS_LINEAGE.md`'s remediation proposal for detail.
2. **F2 (`computeChannelHealth()` / Issue #200)** — after (1), consolidate onto
   `D.primary_offtake_gap`'s already-correct by-chain data (per F6's resolution) rather
   than patching the existing broken accessors in place. Needs its own shadow
   comparison (produces a ratio, not a raw NSV total).
3. **F7 (Total Offtake KPI `?? 0`)** — small, low-risk, display-layer-only fix
   (`?? null` + `'–'` render), no shadow comparison needed, independent of (1)/(2).
4. **F8 (mobile.html hardcoded fake badge)** — delete now regardless of dormancy;
   zero risk, zero benefit to leaving it.
5. **F10 (PowerBI double-allocation dormancy check)** — confirm whether `Allocated
   Primary (via Cont%)` is used in any live report page before deciding priority.
6. **F3 (Primary chain cross-FY fallback)** — lower priority, dormant today (the
   `fp27`/`FPX()` FY27 real-data path already protects the live "Top Chains by Primary
   NSV" table); worth a `CHAIN_PRIMARY_NSV` canonical metric if this table is ever
   migrated onto the canonical engine.
7. **The "deliberately not yet classified" domains, plus `sales_actuals_block()`'s
   missing-data policy** — a follow-up, scoped sweep per domain rather than one more
   all-at-once pass. **Done — see Phase 2B-C below.**
8. **F5, F9, F11-F13 (dead code / lower-severity patterns)** — cosmetic or low-risk,
   no urgency, bundle into any future cleanup pass. **Done** (PR #208: F5 dead-param
   cleanup, F9 mobile.html wired to real data; F11-F13 needed no code change per
   their own recommendation above).

---

## Phase 2B-C — Follow-up sweep (item 7) and its remediation

Read-only discovery pass, 2026-09-25, tracing the 8-9 domains item 7 above named as
undone. Findings continue the F-numbering (F15 onward). Two were real, live-today
defects; the rest were dormant landmines or already clean. All four items this pass
recommended fixing are now **RESOLVED**.

| # | Domain | Classification | Resolution |
|---|---|---|---|
| F15 | `generate_correlations_block()` (`scripts/promo_offtake_correlation.py`) hardcoded `avg_lift=0` and a wrong `elasticity=avg_discount/100` formula, feeding a fully-built but unreachable "Promo Elasticity Executive Brief" (no canvas elements in the DOM, no button opens the brief modal) | UNCONTROLLED_FINANCIAL_TRUTH, dormant (unreachable today, severe if a future edit reconnects it) | **RESOLVED**, PR #211. Source now emits `None`/`NOT_AVAILABLE_UNTIL_VALIDATED_LIFT_SOURCE`/`methodology_validated:False` instead of a fabricated number; `avg_discount`/`count` (genuinely observed) preserved. JS-side `elasticityMethodologyValidated()` guard added at every render/export entry point as defense-in-depth against a future reconnection. |
| F16 | Promo Intensity (`D.promo.by_chain`) / Promo-vs-Sell-Through correlation card | Clean | No action needed. |
| F17 | P&L bridge (`buildPnl()`) hardcoded the literal `'FY26'` instead of reading `pnl_block()`'s real `fy_tag`; `D.pnl`'s defensive default shape (`{chains,totals,blended}`) didn't match the real `{by_chain,fy_tag,...}` shape | Originally reported **dormant** ("source hasn't extended past FY26 yet") — **corrected to LIVE, confirmed 2026-09-25 against the real committed `data.js`**: `pl.fy_tag` is genuinely `"FY27"` today. On unfixed `main`, the default (no-filter) view rendered the real FY27 P&L bridge (₹99.58 Cr NSV) captioned "FY26"; selecting FY26 showed the same FY27 data under the same wrong label; selecting FY27 explicitly hid that real data behind a false "actuals not available" message. UNCONTROLLED_FINANCIAL_TRUTH (live) / DISPLAY_ONLY (crash risk, still dormant) | **RESOLVED**, PR #211 — the fix itself was already correct before this correction; only the severity classification was wrong. Verified live-fixed: default and FY27-filtered views now correctly show "FY27" with the real ₹99.58 Cr figure; FY26 filter now correctly shows "not available" (the bridge's real source has no FY26 data at all). |
| F18 | Category & Pack Mix | Clean (same pattern as the original F13) | No action needed. |
| F19 | Reliance Brand Counter zone/state/brand/category tables (`buildRelianceBC()`) fell back to `.total` (all-time) when a row had no entry for the selected/default FY — the real "Unallocated" buckets (FY26-only, ₹4,562.49L) rendered as if FY27 | Originally reported LIVE; **corrected to DORMANT** — `buildRelianceBC()` has zero call sites in `index.html` and its DOM container doesn't exist in the template (would crash if invoked). The real, live RBC subview (`renderChannelSubview()`'s `sv==='reliance'`) and `mobile.html`'s `rbcTotal()` were already independently clean. See PR #210's description for the full correction. | **RESOLVED**, PR #210. Fixed anyway per the "never leave a landmine even if dormant" principle (same as F8/F10). |
| F20 | Demand Forecast / Competitive Landscape / Market Share | Clean (dead fallbacks / already-honest "not available" states) | No action needed. |
| F21 | `PowerBI/DAX/02_PnL_Measures.dax` silently defaulted a month with no `AssumptionTable.csv` row to a hardcoded 50% Gross Margin / 0% Trade Spend — the seed file only covers Apr'26/May'26 against real Primary/Offtake coverage through Aug'26 | UNCONTROLLED_FINANCIAL_TRUTH, live in the inputs (not confirmed seen in a rendered report — no `.pbix` exists) | **RESOLVED (code/governance)**, PR #211. DAX now fails closed to `BLANK()`; new `scripts/check_assumption_coverage.py` + `.github/workflows/assumption-coverage-gate.yml` block the build (`BLOCKED_FINANCE_INPUT`) until Finance supplies the missing months. **The underlying data gap itself (Jun/Jul/Aug'26 assumptions) is a standing Business blocker, not closed by this PR** — see `docs/PROJECT_STATE.md`'s Required Business Inputs. |
| F22 | `sales_actuals_block()`'s reconciliation against F1/F2/F6's sources (the "fifth competing-truth candidate" the original doc flagged) | Closed by inspection | It is used only by `scripts/ingest_massit_sales.py` and a non-financial readiness check — zero references in `dashboard/index.html` or `dashboard/data.js`. Nothing on the dashboard for it to compete with; no code change needed. |

**Phase 2B-C exit:** all 7 originally-open items are closed (6 needed no action or were
already resolved elsewhere; F15/F17/F19/F21 got real fixes with regression tests).
Phase 2B is **closed at the code/governance level** once PR #210 and PR #211 merge.
The one thing that remains open is exactly what it always was — a Finance business
input (the missing monthly Assumption Table rows) — now made impossible to miss by
a release gate instead of resting on someone noticing a suspicious 50.0% margin.
