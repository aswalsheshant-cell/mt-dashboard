# Visual Registry — Full Audit

**Created:** 2026-09-13, full sweep of `dashboard/index.html` (4364 lines) across all 11
live tabs plus every sub-view, ahead of V1 release certification. This is the audit
`docs/AGENT_ARCHITECTURE_MAPPING.md` (item 08) flagged as a real, not-yet-built gap —
built now as its own dedicated pass, per explicit request, not folded into a smaller task.

**Method:** four parallel read-only sweeps of the file (one per tab-group), each
extracting every `card()`/`kpi()` KPI tile, every chart (`mkBar`/`mkBarH`/`mkLine`/
`mkDonut`, and the few bypassing those helpers), its data source traced to the actual
`D.xxx` field, filter/FY awareness, and click/drill behaviour — all with line-number
citations so every claim below is checkable against the file directly. Classification
(AUTHORITATIVE/DIAGNOSTIC/DUPLICATE/LEGACY/MISLEADING) was applied after the raw
inventory, by inspecting each flagged item's actual code, not by assumption.

**Scope note:** this file lists every visual found. It does not re-derive or re-verify
every underlying number (that's `docs/METRIC_REGISTRY.md`'s job for the ~10 headline
measures) — it verifies *what each visual reads, whether that source is real, and
whether the visual's behaviour matches what it claims to do*.

---

## Critical findings (ranked by severity — read this section first)

**Findings #1-#3 below were fixed the same session** (commit `cc53f0d`, after
user sign-off), verified live via Playwright. Kept in full below as the audit
record; each now says **FIXED** instead of being silently removed, since a
registry that erases its own findings once addressed defeats the point of
having one.

### 1. FIXED (was MISLEADING) — a chart showed entirely fabricated numbers
`dashboard/index.html:1558-1572`, Inventory & Supply Health tab, "Demand-Supply Gap"
sub-view. The line chart directly beneath the (real-data) "Distribution of Inventory
Watchlist" table is built from **literal hardcoded arrays**, no `D.xxx` reference at
all:
```js
labels: ['Wk1','Wk2','Wk3','Wk4','Wk5']
'Primary Inflow': [45,48,50,52,51]
'Offtake':        [40,42,45,48,50]
```
This is the exact thing CLAUDE.md's Core Invariants forbid ("No dummy data... never
fabricate numbers") — and it sat on a live, reachable tab, immediately below a table
built from real data, with nothing in the UI distinguishing the two.

**Fix applied:** the fabricated chart is removed and replaced with an honest "source
not available" card explaining that Primary/Offtake are monthly-grain in this build,
not weekly, naming the exact file that would need a weekly extract added
(`scripts/build_dashboard_data.py`) — the same disclosure pattern already used for
Demand Planning's "Competitive Market Share" card.

### 2. FIXED (was MISLEADING) — Store Coverage table was reading a field that doesn't exist
`dashboard/index.html:1576` (pre-fix). The code read `D.offtake.by_zone.stores` — a
field that does not exist in that block at all (`D.offtake.by_zone` carries NSV, not
store counts) — and additionally called `Object.keys()` on it as if it were a map,
when `D.offtake.by_zone` is actually an array. Real effect in production: every row
showed the **array index** ("0", "1", "2"...) as the zone name, 0 stores, and 0.0%
"coverage" — not a NaN risk, an always-zero, always-mislabelled table.

**Fix applied:** switched to the real source, `D.universe.by_zone` (`{name,stores}`),
which sums to the 426-store baseline invariant — verified live: North 117, East 91,
South 1 77, West 73, South 2 39, Central 29 = 426. The fabricated "Coverage %" column
(`stores/10*100`, no real denominator) is dropped rather than replaced with another
invented ratio, since no active-vs-total split by zone exists yet to compute a real
coverage % from.

### 3. FIXED (was MISLEADING) — two KPI tiles bound to fields that don't exist
`dashboard/index.html:1478, 1493` (pre-fix). "Pipeline Cover (DOI)" read
`metrics.avg_fill_rate` and "Fill Rate (OTIF)" read `metrics.otif_pct` — neither field
name appears anywhere else in the codebase. Traced to source: `build_dashboard_data.py`
emits `metrics.doi = {}` and `metrics.otif = {}` as explicit, permanently-empty
placeholders (comments: "Days of Inventory by zone", "On-Time In-Full by zone") — no
DOI/OTIF computation is implemented anywhere in the pipeline yet, so these two KPIs
always showed a bare `–`, indistinguishable from a KPI that's legitimately zero after
filtering.

**Fix applied:** changed the blank-state label to **"Not computed"** so it reads as
"this pipeline gap exists" rather than "filtered to zero" — no fabricated number was
invented, since no real DOI/OTIF source exists to compute one from.

### 4. Real bug — a safety fix is silently shadowed
`dashboard/index.html:433` and `:3292` both declare `function destroyAnalyticsCharts()`
at top level. The second (no `try/catch` per chart) silently overrides the first
(has `try/catch`) everywhere `destroyCharts()` calls it — so the defensive version was
never actually active. One-line fix (delete the later, unsafe duplicate) once approved.

### 5. Hardcoded business constants feeding real-looking outputs, undisclosed
- `dashboard/index.html:3191-3206` (`computeSKUQuadrants`, Commercial Analytics
  "SKU Portfolio Quadrants" chart): silently substitutes 100 stores / 45% gross
  margin when the real fields are missing — the chart gives no indication which
  points used a real vs. a guessed value.
  **Update 2026-09-26:** fixed as FM-35 (branch `claude/sku-quadrants-truthful`) —
  no defaults; the card says "Not available" and names the missing fields.
- `dashboard/index.html:3393-3403` (`computePORiskSummary`, "Open PO SLA Risk
  Summary"): hardcodes a ≥7-day breach threshold and a flat ₹50L penalty per
  breach with no visible source/config for either number.

### 6. Alerts empty-state is a false "all healthy" on load failure
`dashboard/index.html:275-276`, `alert_controller.js:59-62`. `window.alertsFeed`
fetch has a silent `.catch(()=>{})`; a failed fetch renders identically to a
genuinely empty, healthy alert feed ("No active alerts. All metrics within
thresholds."). Currently harmless only because the live feed also happens to be
empty — the failure mode is real regardless.

**Status: FIXED on branch `claude/alerts-feed-load-state` (rebuild of old PR
#156), not yet merged.** `window.alertsFeedStatus` (loading/loaded/error); a
failed or non-200 load shows "Alert feed unavailable … not a confirmation that
metrics are healthy" and `–` in the 3 KPI cards; the tab repaints when the fetch
settles. Regression test: `tests/test_alerts_feed_load_state.js`.

### 7. Dead drill-links / dead toggle (functional, not data-integrity)
- Executive Cockpit's two "target vs achievement" tables (`by_zone`/`by_chain`,
  `dashboard/index.html:900-911`) render `drillLink` spans but `buildExecutiveCockpit`
  never calls `wireDrillLinks(s)` — clicks do nothing.
- The Reliance Brand Counter macro/BA toggle (`dashboard/index.html:3954-3988`) only
  changes button styling and a disclaimer note; `relianceBCViewMode` is never read
  by the actual "Reliance by Zone" table, which always computes from the unfiltered
  full record set regardless of which toggle is selected.
- `computeChannelHealth()` (`dashboard/index.html:3152-3189`) never produces a status
  string of `'Overstocked'`, but `generateAnalyticsInsights()` (line 3225) filters for
  exactly that string — the "Inventory Imbalance" insight card can never fire.

### 8. DUPLICATE — the same Primary-vs-Offtake relationship computed twice, independently
- `computeChannelHealth()` (Commercial Analytics, `cvHealth` chart) — from
  `D.primary.by_chain` + `D.offtake.by_chain` / same-period detail.
- `primaryOfftakeGapSection()` (Performance & Comparison, `pogMonthChart` + table) —
  from the separately pre-built `D.primary_offtake_gap` block.

Two different tabs answer "is Primary keeping pace with Offtake?" from two
independently-computed sources rather than one shared calculation. Not proven
inconsistent (not numerically compared here), but a real drift risk per this
project's own Metric Registry principle ("reuse a registered measure, don't
recompute independently").

### 9. LEGACY — dead pre-consolidation code, larger than previously known
Already known: `buildPrimary()`, `buildCategory()` (neither in the `BUILD` map, no
live caller). **Newly confirmed dead this pass:**
- `buildRelianceBC()` (`dashboard/index.html:1916`) — also targets a DOM id
  (`tab-reliance-bc`) that doesn't exist in the template.
- Six unused render helpers, never called from any live path (**removed
  2026-09-26 by Issue #113** -- see "Confirmed dead code" below):
  `renderMultiSelect` (2494), `renderAnomalyBadge` (2747), `renderElasticityCurves`
  (4069), `renderROIHeatmap` (4100), `renderWaterfall` (4125), `renderScatterTrend`
  (4154).

None of this is a defect on its own (dead code doesn't run, so it can't render
wrong data) — but it's real maintenance debt matching exactly the pattern CLAUDE.md
already documents for `buildOfftake`/`buildDistribution`/etc.

---

## Full visual inventory by tab

Classification key: **AUTHORITATIVE** (correct, live, canonical) · **DIAGNOSTIC**
(QC/detail table, working as intended) · **DUPLICATE** (see #8 above) ·
**LEGACY** (dead code, listed for completeness) · **MISLEADING** (see #1-3, #5-6
above).

### Executive Cockpit (`buildExecutiveCockpit`, L913-1032)

| Visual | Type | Source | Filter/FY aware | Click | Class |
|---|---|---|---|---|---|
| Primary NSV KPI | KPI | `D.primary.by_chain` | yes/yes | static | AUTHORITATIVE |
| Offtake KPI | KPI | `D.offtake['total_'+offYr]` | no/yes | static | AUTHORITATIVE |
| Active MT Stores | KPI | `D.universe` | no/no | static | AUTHORITATIVE |
| Chains Tracked | KPI | `chains.length` | yes/yes | static | AUTHORITATIVE |
| FY27 Target KPI | KPI | `D.forecast` | no/fixed FY27 | static | AUTHORITATIVE |
| `cockpitTrend` | line | `D.primary`+`D.offtake` monthly | **no/no** (always full FY25-27 span, ignores FY filter) | static | AUTHORITATIVE (behaviour gap noted) |
| `cockpitChannel` | donut | `D.primary.by_channel` | yes/yes | `drillTo('Channel')` | AUTHORITATIVE |
| `cockpitDrill` | drill bar | `recFilter()` | yes/yes | drill hierarchy | AUTHORITATIVE |
| Target/Actual/Achievement/Run-rate KPIs (6) | KPI | `D.targets` | no/no | static | AUTHORITATIVE |
| Target by zone/chain tables (2) | table | `D.targets.measures[basis]` | no/no | **dead** (`wireDrillLinks` never called) | AUTHORITATIVE, functional bug (#7) |
| Insight cards | cards | `D.insights` | no/no | static | AUTHORITATIVE |
| Recommended Actions | static text | hardcoded prose, no `D.xxx` | n/a | static | narrative, not a data visual — not misleading, just not data-backed (expected) |

### Channel & Chain Performance (`buildChannelDynamics`/`renderChannelSubview`, L1207-1469)

| Visual | Sub-view | Type | Source | Filter/FY | Click | Class |
|---|---|---|---|---|---|---|
| Top Chains table | primary | table | `D.primary.by_chain` | yes/yes | drill | AUTHORITATIVE |
| Channel Split table | primary | table | `D.primary.by_channel` | yes/yes | static | AUTHORITATIVE |
| `chanPrimTrend` | primary | line | `D.primary.monthly_fy26/27` | no/partial | static | AUTHORITATIVE |
| `chanChanSplit` | primary | donut | `D.primary.by_channel` | yes/yes | **static** (sibling `cockpitChannel`, same data, is clickable) | AUTHORITATIVE, inconsistency noted (#8-adjacent) |
| Category & Pack Mix drill table | category | table | `recFilter()` | yes/yes | custom drill + **95%-Others grouping at SubCategory level** (this session's fix) | AUTHORITATIVE |
| Reliance macro/BA toggle | reliance | control | n/a | n/a | cosmetic only (#7) | functional bug, not data |
| Reliance by Zone table | reliance | table | `recFilter('Brand')` | yes/yes | drill | AUTHORITATIVE |

### Data Explorer (`buildExplorer`, L3840-3907)

17 visuals (4 KPIs, 10 configurable gallery charts, 1 Category→SubCategory drill, 1
detail table) — all AUTHORITATIVE, all `recFilter()`-driven, all FY-aware, **except**
the "SIS — Primary (FY26)" KPI which is intentionally hardcoded to FY26 (title says
so) and won't move if a different FY is selected — labelled correctly, not misleading,
just worth knowing.

### Inventory & Supply Health (`buildInventoryHealth`, L1472-1611)

| Visual | Sub-view | Type | Source | Class |
|---|---|---|---|---|
| Total Offtake / Active Stores / Pipeline Cover / Fill Rate KPIs (4) | all | KPI | `D.offtake` | Pipeline Cover + Fill Rate: **FIXED, now "Not computed" (#3)**; other two AUTHORITATIVE |
| Top Chains by Offtake table + bar chart | velocity | table+bar | `D.offtake.by_chain` | AUTHORITATIVE (not drill-linked, not filter-aware) |
| Inventory Watchlist table | gap | table | `D.offtake.metrics.doi_watchlist` | AUTHORITATIVE |
| Gap line chart | gap | line → honest note | was hardcoded literals | **FIXED (#1)** — now an honest "source not available" card |
| Store Distribution by Zone table + donut | coverage | table+donut | `D.universe.by_zone` (was wrongly `D.offtake.by_zone`) | **FIXED (#2)** — real zone names/store counts, sums to 426 |

None of this tab's visuals respond to the Chain/Brand/Channel/Zone filter bar; only
the FY selector partially applies (see full inventory notes below).

### Demand & S&OP Planning (`buildDemandPlanning`, L1058-1205)

| Visual | Sub-view | Type | Source | Class |
|---|---|---|---|---|
| TY Target / FY26 Actual / Gap / Required Growth KPIs (4) | all | KPI | `D.forecast` | AUTHORITATIVE (fixed to FY27/FY26 by field name, not the FY selector) |
| Zone Forecast Allocation table + bar | forecast | table+bar | `D.offtake.by_zone` + `D.forecast.fy27_forecast` | AUTHORITATIVE |
| Promo Intensity by Chain table + scatter | promo | table+scatter | `D.promo.by_chain` | AUTHORITATIVE |
| Competitive Market Share | market-share | static card | none — explicit "not available" note | AUTHORITATIVE (honestly discloses the gap, not misleading) |

The `fy` parameter passed into this tab's render function is dead — never read after
being declared (see full notes). No visual here responds to the sidebar filter chips.

### P&L (`buildPnl`, L1988-2164)

19 visuals. All AUTHORITATIVE by source, with two disclosed/undisclosed filter gaps:
- Gross-to-net bridge section (KPIs, `plBridge`, `plDisc`, chain table): Chain-filter
  and FY-gated (`fy26ok`) correctly.
- TOT% and CM2 sections (11 visuals): **no FY filtering at all**, and — unlike the
  `dimUnsupportedNote` shown for Zone/Brand/Channel/Category — nothing tells the user
  FY doesn't apply here either. Not a data error (the numbers are real and correctly
  labeled FY26-27), just an undisclosed filter-scope gap.
- "Promo Lines" KPI reads the dashboard-wide `D.promo.n_promos`, not `D.pnl`-scoped —
  sits inside an otherwise Chain-filtered KPI row without shrinking when Chain is
  filtered.

### Performance & Comparison (`buildComparison`, L3024-3130 + 5 fixed sections)

24 visuals across 6 `cmpDim` values plus 5 always-shown sections (Primary-Offtake
Gap, Unified Trend, FY25 Secondary, MoM, Scorecard). All AUTHORITATIVE by source.
Filter-scope gaps (not data errors, all correctly labeled):
- Chain/Brand ranking (FY25/26 branch) ignores every chip filter with no
  `dimUnsupportedNote`, while the SubCategory/Range/PackSize/Article branch on the
  same tab correctly respects them — an inconsistency within one tab.
- The 5 fixed sections are static regardless of which `cmpDim` is selected, despite
  the page caption implying dimension-scoped content.
- FY25 Secondary section: chain rows are drill-linked, sibling brand rows are not.

### Commercial Analytics (`buildAnalytics`, L3296-3367 + helpers)

15 visuals. AUTHORITATIVE overall, with the specific defects at #4, #5, #7 (dead
`Overstocked` filter), #8 (duplicate Primary/Offtake calc) called out above. `cvPVM`/
`cvHealth`/`cvQuadrant` bypass the shared chart helper (`mkBar` family), so they have
no download-menu and no click/drill — a consistency gap, not a data error.

### Operational Alerts (`buildAlerts` → `alert_controller.js`)

3 KPIs + 1 card-feed list, sourced from a **separate global** (`window.alertsFeed`,
not `D`/`window.DASH`) fetched from `alerts_feed.json`. AUTHORITATIVE when the feed
loads; on a failed load it now says the feed is unavailable and shows `–` (#6, fixed). Not filter/FY-aware (by design —
alerts are current-state, not historical).

### Store Audit Scorecard (`buildStores`) & Supply Chain and Inventory (`buildInventory`)

6 visuals total (KPI rows + tables), sourced from `D.compliance`/`D.inventory_fillrate`
(a separate async fetch from `compliance_metrics.json`, same pattern as Alerts).
**PROVENANCE_UNVERIFIED, not AUTHORITATIVE** (corrected on `fix/compliance-data-provenance`
after this claim was found wrong): `compliance.accounts`/`compliance.doors`/
`inventory_fillrate.accounts` are a byte-for-byte match to
`scripts/sync_compliance_data.py`'s mock generator, and `compliance.chain_summary`
(unused by any tab, but its `total_stores` sum feeds `metadata.total_doors_audited`,
which the Store Audit Scorecard's macro PES card and the `scorecard_execution`
readiness gate both read) carries an internal template fingerprint — an identical
`[85,84,86,85,<current>]` trend across all 5 unrelated chains/zones — that no real,
independent audit history would produce. No script in this repo generates this data
and `config/data_source_registry.yml` has no entry for it (`forecast_stock_inventory`
there is `validation_status: MISSING` for the same OTIF/fill-rate domain). Both tabs
now show an amber provenance banner driven by `metadata.is_synthetic` in the file
itself. Neither tab responds to any filter or FY selector — by-design for a
point-in-time snapshot, but undocumented as such. One card ("Days of Cover")
is a documentation stub only — references `InventoryEngine.calculateDaysOfCover()`,
which exists (`inventory_engine.js:16-40`) but is never actually invoked anywhere.

---

## Confirmed dead code (LEGACY, not reachable from any live tab)

| Function | Line | Why dead |
|---|---|---|
| `buildPrimary` | 1615 | Not in `BUILD` map; targets nonexistent `#tab-primary` |
| `buildCategory` | 2328 | Not in `BUILD` map; targets nonexistent `#tab-category` |
| `buildRelianceBC` | 1916 | Not in `BUILD` map; targets nonexistent `#tab-reliance-bc` |

**Update 2026-09-26 (Issue #113):** the six render helpers that were listed here
(`renderMultiSelect`, `renderAnomalyBadge`, `renderElasticityCurves`,
`renderROIHeatmap`, `renderWaterfall`, `renderScatterTrend`) were removed together
with the rest of their Sprint 6 groups: the Executive Brief modal (DOM, CSS, 6
functions), the promo filter/export/anomaly helpers, the `D.dist_gap` helpers (not
the live Demand-Supply Gap subview), the forecast detail helpers and
`onGlobalFilterChange()`. Guard: `tests/test_promo_elasticity_guard.js`.
Still dead, left for a separate decision: `buildPrimary`, `buildCategory`,
`buildRelianceBC` (above; `buildRelianceBC` is exercised directly by
`tests/test_reliance_bc_period_leakage.js`), `monthUnsupportedNote`, `expBarH`,
`expDonut`, `expLine` (`index.html`) and `exportMonthlyInsightPDF`
(`monthly-insights.js`). Line numbers in this table are from the original audit.

All 11 `TABS`/`BUILD` entries verified to match 1:1 — every live tab does have a
real, reachable builder function; the dead functions above are pure surplus, not a
sign any tab is secretly broken.

---

## What this audit does NOT cover

- It does not re-verify the arithmetic behind any number (that's the Metric Registry's
  job for headline measures; this audit traced *source*, not *correctness of formula*).
- The DUPLICATE finding (#8) identifies two independent computations of a similar
  concept; it does not prove they disagree — that would need pulling both and diffing,
  a follow-up if the business wants that reconciled.
- Power BI / PBIP visuals are out of scope (separate, still-not-built PBIP project —
  see `docs/ALLOCATION_CAPABILITY_MATRIX.md`'s STOP condition section).
