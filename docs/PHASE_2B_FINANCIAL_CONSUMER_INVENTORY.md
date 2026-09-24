# Phase 2B-A — Canonical Financial Truth Consumer Inventory

**Read-only discovery. No production edits, no legacy deletion, no new financial
calculations, no consumer switching, no dashboard redesign, no remediation.** This
document is the inventory and recommended remediation order only — Phase 2B-B
(actually acting on any finding) requires separate, explicit approval.

**Scope covered exhaustively:** every consumer of `D.offtake.by_chain` (the
`CHAIN_OFFTAKE_NSV`/`OFFTAKE_NSV` lineage Phase 1/2A built canonical coverage for),
plus every consumer surfaced by that trace that turned out to touch a second or
third independent financial-truth source (Primary chain NSV, the pre-built
Primary-vs-Offtake gap block). **Scope covered at lighter depth, explicitly flagged,
not silently assumed clean:** P&L NSV (`D.pnl.by_chain`), TOT% (`D.tot.by_chain`),
Promo (`D.promo.by_chain`), Forecast (`D.forecast`), Category & Pack, Reliance Brand
Counter, Correlations/elasticity (`corr.by_chain`) — these are real, separate
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

## Deliberately not yet classified (real domains, not silently assumed clean)

These are genuine financial-truth-bearing surfaces this pass did not trace to F1-F6's
depth. Listed so the exit criteria below is honest about what it actually covers,
rather than claiming whole-dashboard coverage from a keyword sweep:

- **P&L NSV** (`D.pnl.by_chain`, `dashboard/index.html:2114-2127`) and **TOT%**
  (`D.tot.by_chain`) — separate, pre-existing, already-certified pipeline (PR #193),
  not part of Offtake/Primary chain lineage. Uses simple `\|\|0` patterns at a glance;
  not deep-traced for cross-FY fallback in this pass.
- **Promo** (`D.promo.by_chain`) — Promo Intensity by Chain table; not an NSV/offtake
  figure, lower financial-truth relevance.
- **Forecast** (`D.forecast`, `D.offtake.by_zone` + `D.forecast.fy27_forecast`) — Zone
  Forecast Allocation table; zone grain, not chain grain; canonical engine has no
  zone-level metric yet either.
- **Correlations/elasticity** (`corr.by_chain`) — Commercial Analytics promo-elasticity
  section; derived analytics over Promo/Primary data, not raw Offtake NSV.
- **Category & Pack Mix, Reliance Brand Counter (non-`RBC_OFFTAKE_NSV`/`RBC_PRIMARY_NSV`
  paths), Demand Forecast, Competitive Landscape** — not searched this pass.
- **`dashboard/mobile.html`, `PowerBI/DAX/`, `PowerBI/PowerQuery/`,
  `scripts/build_dashboard_data.py` (functions beyond `offtake_block()`/
  `offtake_rebuild_block()`)** — delegated to a parallel sweep this same session;
  see that sweep's findings folded in below if completed before this document's
  final commit, otherwise flagged here as still open.

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
0 UNKNOWN                        NOT MET -- 1 open (F6: D.primary_offtake_gap's
                                  Python-side missing-data behavior not yet traced)
0 unexplained financial truth
sources                          NOT MET -- F6's structural duplication is explained
                                  (three independent Primary-vs-Offtake computations
                                  exist) but not yet fully resolved to a single source
100% financial consumers
classified                       PARTIAL -- F1-F6 fully classified; several real
                                  domains (P&L, TOT%, Promo, Forecast, mobile.html,
                                  PowerBI) explicitly flagged as not yet covered,
                                  not silently assumed clean
Every fallback path explicitly
identified                       F1 (fixed), F2 (live defect), F3 (dormant), F5
                                  (dead code) -- all identified with exact expressions
Every missing->zero
transformation identified        F2's primary-side `p=pri[c]||0`, F3's `c[primYr]||0`
                                  -- identified; F6 and the "not yet classified" list
                                  still open
Issue #200 lineage proven        YES -- F2 above, with more precision than the
                                  original Phase 2A lineage trace (both the offtake-
                                  side AND a previously-unnoticed primary-side
                                  fallback, plus the dead 'Overstocked' filter)
No production behavior changed   YES -- zero files outside this docs/ commit touched
```

**Verdict: PHASE 2B-A DISCOVERY INCOMPLETE — do not proceed to Phase 2B-B (remediation)
on the full dashboard yet.** F2 (Issue #200 / `computeChannelHealth()`) is fully
proven and ready for its own Phase 2B-B remediation cycle (shadow comparison → gates
→ cutover, mirroring Phase 2A's exact playbook) independent of the rest. F6 needs one
more trace (its Python source) before it can be closed out. The "deliberately not yet
classified" domains need their own dedicated sweep before this repo can honestly claim
`0 UNCONTROLLED_FINANCIAL_TRUTH` end to end.

## Recommended remediation order

1. **F2 (`computeChannelHealth()` / Issue #200)** — highest confidence, highest
   financial-truth risk (a live, provable wrong-number defect, not just dormant risk).
   Ready to start its own Gate-1-style shadow comparison now.
2. **F6 (`D.primary_offtake_gap` Python source trace)** — needed to close out the
   "duplicate calculation" question before deciding whether F2's fix should also
   consolidate toward one shared Primary-vs-Offtake source.
3. **F3 (Primary chain cross-FY fallback)** — lower priority, dormant today; worth a
   `CHAIN_PRIMARY_NSV` canonical metric if/when this table is migrated.
4. **The "deliberately not yet classified" domains** — a follow-up Phase 2B-A2 sweep,
   scoped per-domain (P&L, Promo, Forecast, mobile.html, PowerBI) rather than one
   more all-at-once pass.
5. **F5 (dead code)** — cosmetic, no urgency, bundle into any future cleanup pass.
