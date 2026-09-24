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
| Financial impact | **Real, live.** For any `GOV-003`/`GOV-005` chain (CNC/EB2B/Others/Vijetha at FY27; the 8 newly-onboarded chains at FY26), if the *other* side (Primary) has a real positive value, `off[c]` resolves to a **stale, non-FY-specific figure**, `ratio=o/p` computes a **non-null, wrong** health ratio and status ("Selling out faster than billed" / "Billed ahead of sell-out"), which is **not** filtered out (the `p>0&&o>0` guard only excludes zero/null cases, not stale-nonzero ones). This is a materially worse failure mode than F1's pre-fix state, because it doesn't even show "no data" — it shows a confident, wrong verdict. |
| **Classification** | **UNCONTROLLED_FINANCIAL_TRUTH** (the offtake-side accessor specifically; the ratio/status/color derivation around it is a `DERIVED_ANALYTIC` built on that one uncontrolled input) |
| Recommended action | Phase 2B-B candidate: port the same `canonicalChainOfftakeNSV`-style accessor to both the offtake and primary sides here, following the same governed, no-fallback pattern as F1. Needs its own shadow comparison first (this produces a *ratio*, not a raw NSV total, so F1's parity script does not directly cover it) |
| Evidence | Direct code reading, this session, 2026-09-24; corroborates and supersedes `docs/VISUAL_REGISTRY.md` finding #8's "duplicate calculation, not proven inconsistent" — this pass proves the offtake-side fallback specifically, not just structural duplication |

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
| Missing-data behaviour | Not traced to its Python source in this pass (would require reading `build_dashboard_data.py`'s block that produces `D.primary_offtake_gap`, not yet done) |
| **Classification** | **UNKNOWN** (structural duplication confirmed — three independent Primary-vs-Offtake computations exist in this codebase — but this specific block's own missing-data behavior is not yet traced) |
| Recommended action | Trace `D.primary_offtake_gap`'s Python source before any remediation; this is the clearest concrete instance of `docs/VISUAL_REGISTRY.md` finding #8's "drift risk," now with F2's fallback defect proven as one of the three competing paths |
| Evidence | `docs/VISUAL_REGISTRY.md` finding #8 (pre-existing, 2026-09-13, never resolved); `dashboard/index.html:1063-1073,3499-3501,3592-3595` |

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

### F14 — `scripts/build_dashboard_data.py` — the Python-side root cause (highest priority to verify)

| Field | Value |
|---|---|
| Function/symbol | `primary_block()`'s `dim_rows()` (`pv.pivot_table(...).fillna(0)`, line ~777); `offtake_block()`'s `fy_sum` (~878-884) and `offtake_rebuild_block()`'s `dim_rows()` (~2198-2202) |
| Input source | The raw pivot/aggregation step that produces every `by_chain[]` row, upstream of ANY client-side (JS/DAX) logic |
| Missing-data behaviour | `fillna(0)` and `sum()` over an empty per-chain-per-FY generator both write a **real, present `0`** — structurally, "no rows at all for this chain this FY" and "rows exist and genuinely sum to zero" become indistinguishable in the emitted JSON **before** any downstream null-check (JS `!=null`, canonical `exact_fy_or_not_available()`) ever sees the data |
| Financial impact | **Not yet proven to have produced an actual wrong canonical value in the current certified `data.js`** — this session's own empirical checks (Phase 1/2A) confirmed `exact_fy_or_not_available()` correctly returns `NOT_AVAILABLE` for the known cases (GOV-003's 4 chains, GOV-005's 8 chains) because their FY keys are genuinely *absent*, not present-as-zero. Whether some *other*, not-yet-identified chain/FY combination has a fabricated `0` masquerading as a real figure was not verified this pass |
| **Classification** | **UNKNOWN** (structurally real risk, not empirically confirmed or ruled out) |
| Recommended action | **Highest-priority item for a dedicated audit before this codebase can honestly claim `0 UNKNOWN` end to end** — this is the one finding that could, if real, mean the canonical engine's core guarantee ("missing never becomes zero") has a gap at its own source, not in any consumer. Needs: for every chain × FY combination the certified data.js reports a real `0.0` (not an absent key), cross-check against the raw monthly source files whether that chain genuinely had zero transactions that FY vs. simply wasn't in the source at all |
| Evidence | Sub-agent code trace, 2026-09-24, with specific line citations for all three writer functions |

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
0 UNKNOWN                        NOT MET -- 2 open: F6 (D.primary_offtake_gap's
                                  Python source not traced), F14 (whether Python-
                                  side fillna(0)/sum-over-empty has produced any
                                  actual false-real-zero in the certified data.js
                                  -- not empirically confirmed or ruled out)
0 unexplained financial truth
sources                          NOT MET -- F6 (3 independent Primary-vs-Offtake
                                  computations) and F14 (a possible source-level
                                  missing-vs-zero ambiguity upstream of every
                                  consumer) both real, neither fully resolved
100% financial consumers
classified                       SUBSTANTIALLY EXPANDED -- F1-F14 fully classified
                                  (offtake/primary chain lineage, mobile.html,
                                  PowerBI DAX/M, build_dashboard_data.py's chain
                                  writers). Still explicitly open: P&L, TOT%,
                                  Promo, Correlations, Category&Pack, Reliance
                                  (non-canonical paths), Demand Forecast,
                                  Competitive Landscape, two PowerBI DAX files
                                  noted but not traced
Every fallback path explicitly
identified                       F1 (fixed), F2 (live defect), F3 (dormant), F5
                                  (dead code), F7 (live KPI defect), F8 (dormant,
                                  hardcoded fake number), F9 (dead), F10 (dormant
                                  double-allocation), F11-F13 (lower severity) --
                                  all identified with exact expressions
Every missing->zero
transformation identified        F2, F3, F7, F9, F12, F13 identified with exact
                                  expressions; F6 and F14 (the deepest, source-
                                  level case) still open; remaining "not yet
                                  classified" domains still open
Issue #200 lineage proven        YES -- F2, with more precision than the original
                                  Phase 2A lineage trace (both the offtake-side AND
                                  a previously-unnoticed primary-side fallback, plus
                                  the dead 'Overstocked' filter)
No production behavior changed   YES -- zero files outside this docs/ commit touched
```

**Verdict: PHASE 2B-A DISCOVERY INCOMPLETE — do not proceed to Phase 2B-B (remediation)
on the full dashboard yet.** Three items are fully proven and ready for independent
remediation cycles the moment they're approved: **F2** (Issue #200), **F7** (Total
Offtake KPI's `?? 0`, a small display-layer fix), and **F8** (delete the hardcoded
fake growth badge in `mobile.html` now, regardless of dormancy — a landmine is still
a landmine before it fires). **F14 is the highest-priority open item** — if the
Python-side `fillna(0)`/sum-over-empty pattern has produced even one false-real-zero
in the certified `data.js`, it would mean the canonical engine's core "missing never
becomes zero" guarantee has a gap at its own source, undiscovered by any test in
Phase 1 or 2A (which only exercised the "key genuinely absent" case, not "key present
with a source-fabricated zero"). This needs empirical verification before it can be
ruled in or out — the domains in "deliberately not yet classified" still need a
scoped, per-domain sweep before this repo can honestly claim `0 UNCONTROLLED_FINANCIAL_TRUTH`
end to end.

## Recommended remediation order

1. **F14 (Python-side missing-vs-zero root cause)** — verify first, before any UI
   fix, since it could affect the correctness of figures this whole inventory
   otherwise treats as trustworthy. For every chain × FY the certified `data.js`
   shows a real `0.0` (not an absent key), cross-check the raw monthly source: did
   that chain genuinely have zero transactions, or was it simply absent from the
   source entirely?
2. **F2 (`computeChannelHealth()` / Issue #200)** — highest-confidence live UI
   defect. Ready to start its own Gate-1-style shadow comparison now (produces a
   ratio, needs its own comparison logic, not a reuse of F1's).
3. **F7 (Total Offtake KPI `?? 0`)** — small, low-risk, display-layer-only fix
   (`?? null` + `'–'` render), no shadow comparison needed. Safe to bundle with F2's
   remediation cycle or do standalone.
4. **F8 (mobile.html hardcoded fake badge)** — delete now regardless of dormancy;
   zero risk (the code path is unreachable today), zero benefit to leaving it.
5. **F6 (`D.primary_offtake_gap` Python source trace) + F10 (PowerBI double-
   allocation dormancy check)** — both need one more trace each (is the block/measure
   actually live anywhere) before a remediation decision can be made.
6. **F3 (Primary chain cross-FY fallback)** — lower priority, dormant today; worth a
   `CHAIN_PRIMARY_NSV` canonical metric if/when this table is migrated.
7. **The "deliberately not yet classified" domains** — a follow-up Phase 2B-A2 sweep,
   scoped per-domain (P&L, TOT%, Promo, Correlations, Category&Pack, Reliance,
   Demand Forecast, Competitive Landscape) rather than one more all-at-once pass.
8. **F5, F9, F11-F13 (dead code / lower-severity patterns)** — cosmetic or low-risk,
   no urgency, bundle into any future cleanup pass.
