# Canonical Metric Dependency Map

**Status:** Reference document for the canonical financial truth architecture (`docs/CANONICAL_FINANCIAL_TRUTH_DESIGN.md`). Design-only — no code changed to produce this map.
**Method:** Direct `grep` of `dashboard/index.html` and `scripts/build_dashboard_data.py` for every named field, resolved to the enclosing `function` at each match line. This is a static, source-grounded trace, not an inferred one — every consumer listed below was found in the actual file, not assumed.

Purpose: before any canonical accessor replaces a direct field read, know every place that read would need to change — so a fix on one screen (the pattern that produced 3 of PR #193's 4 defects) cannot silently break another.

---

## `primary.by_channel`

Written by: `primary_block()` (initial pre-agg), then corrected by `apply_primary_channel_correction()` (`scripts/build_dashboard_data.py`) — PR #193's fix.

| Consumer | File | Kind |
|---|---|---|
| `buildExecutiveCockpit()` | `dashboard/index.html` | Executive Cockpit channel-split donut |
| `buildChannelDynamics()` | `dashboard/index.html` | Channel & Chain Performance (Primary Sales sub-view) |
| `buildPrimary()` (×2 call sites) | `dashboard/index.html` | Legacy pre-consolidation builder — per CLAUDE.md's maintenance note, reachable only via `LEGACY_TAB_ROUTES`, not a live top-level nav surface. Still technically a consumer; any canonical migration must not break its route even though no user reaches it directly |
| `tests/test_primary_channel_correction.py` | test | 5 tests on the correction function itself |
| `tests/test_pr193_reconciliation.py` | test | Channel reconciliation tests (Controls 1) |
| `tests/validate_data_integrity.py` | test | Asserts MT/EB2B/SIS all present |

## `primary.by_chain`

Written by: `primary_block()`.

| Consumer | File | Kind |
|---|---|---|
| `buildExecutiveCockpit()` | `dashboard/index.html` | Executive Cockpit |
| `buildChannelDynamics()` | `dashboard/index.html` | Channel & Chain Performance |
| `buildPrimary()` (×2) | `dashboard/index.html` | Legacy, routed-only |
| `buildComparison()` (×2 call sites) | `dashboard/index.html` | Performance & Comparison (chain ranked comparison, FY25-vs-FY26 view — the legitimate comparison pattern noted in the design doc's fallback search) |
| `computeChannelHealth()` | `dashboard/index.html` | Feeds a health/status computation — not yet further traced past this function name; note for implementation-phase deeper trace |

## `primary.total` / `primary["total"]`

**No direct consumer found.** `primary_block()` does not appear to emit a single flat `total` field the way `offtake_block()`/`offtake_rebuild_block()` do — Primary's headline totals are read via `primary.by_channel`'s own sum, `primary.by_chain`'s own sum, or `detail_records`' own sum, computed client-side wherever needed (e.g. Data Explorer's "NSV (Filtered)" KPI). Named in the requested trace list; documented here as **not a field that exists** on `primary`, so a canonical `PRIMARY_NSV` accessor is not replacing an existing single source — it is *introducing* one where today's dashboard recomputes the sum independently in each view.

## `offtake.total`

Written by three different functions with three different semantics — see `docs/CANONICAL_FINANCIAL_TRUTH_DESIGN.md`'s Current State section and ADR-002 for the full root-cause trace: `offtake_block()` (nested per-FY dict), `offtake_rebuild_block()` (flat, all-months-summed — confirmed to be what actually produced the certified baseline), `patch_offtake_new_months()` (never touches it at all).

| Consumer | File | Kind |
|---|---|---|
| `buildInventoryHealth()`'s KPI `total` (line ~1555) | `dashboard/index.html` | Total Offtake KPI. **Already made FY-safe by PR #193** — falls through to `0`, never to another FY's or the flat all-months value, so it is unaffected by `offtake["total"]`'s shape ambiguity |
| `tests/test_pr193_reconciliation.py` | test | Reconciles `total_<fy>` (the flat, FY-specific key — not the ambiguous `total`) against `monthly_<fy>`'s own sum |

## `offtake.by_fy`

**This key does not exist.** Named in the requested trace list; verified via grep that no `offtake.by_fy` field is ever written or read anywhere in this repository. The nearest real equivalents are the flat `total_<fy>` / `monthly_<fy>` / `months_<fy>` keys directly on the `offtake` object, and the per-row `<fy>` keys on `offtake.by_chain[]` / `by_zone[]` / `by_state[]`. Documented here rather than silently substituting one of those and presenting it as if the user's named field existed.

## `offtake.by_chain` (including the `.value` field specifically)

Written by: `offtake_block()` (full build) and `offtake_rebuild_block()`'s `dim_rows()` helper (confirmed to be the actual current-baseline source of the `.value` field — see root-cause trace in the design doc); updated per-`<fy>`-key only by `patch_offtake_new_months()`.

| Consumer | File | Kind |
|---|---|---|
| `buildInventoryHealth()` (`chainData` map, line ~1618) | `dashboard/index.html` | "Top Chains by Offtake" table + its Chart.js bar chart — **`KI-OFFTAKE-001`'s exact call site** |
| `buildInventoryHealth()` (`Object.keys(o.by_chain\|\|{})`, line ~1705) | `dashboard/index.html` | Passed onward as a chain-name list to `renderInventorySubview()` |
| `fy25SecondarySection()` | `dashboard/index.html` | Reads `.secondary_fy25` specifically (a distinct field from `.value`/`<fy>`, not implicated in `KI-OFFTAKE-001`) |
| `computeChannelHealth()` | `dashboard/index.html` | Not yet further traced past this function name |
| `tests/*` | — | No direct test found exercising `offtake.by_chain[].value`'s correctness today — a gap the implementation phase's reconciliation-test layer should close |

## `detail_records`

Written by: `detail_records_real()` (article-wise Primary, File 2) / `detail_records_representative()` (fallback synthesizer, only used when File 2 is absent).

| Consumer | File | Kind |
|---|---|---|
| `buildExplorer()` | `dashboard/index.html` | Data Explorer (all charts/tables) |
| `buildComparison()` | `dashboard/index.html` | Performance & Comparison (article-level drill mode) |
| `buildInventory()` | `dashboard/index.html` | Supply Chain & Inventory tab (separately self-flagged as demo/unverified data for its own `D.inventory_fillrate` block — `detail_records` usage here needs its own confirmation of what it feeds) |
| `buildPrimary()` | `dashboard/index.html` | Legacy, routed-only |
| `renderChannelSubview()` | `dashboard/index.html` | Channel & Chain Performance's Category & Pack Mix and Reliance Brand Counter sub-views — **the actual call site of PR #193's bugs #2 (display) and the Reliance-tab-shows-Primary-not-Offtake question in ADR-003** |
| `consolidateChains()` | `dashboard/index.html` | Shared chain-name consolidation helper |
| `expLine()` | `dashboard/index.html` | Chart line-series helper |
| `computeNpiPerformance()`, `npiSetCohortFy()` | `dashboard/index.html` | Commercial Analytics — NPD/new-article performance |
| `computeSkuVolatility()`, `skuVolatilitySection()` | `dashboard/index.html` | Commercial Analytics — SKU NSV volatility |
| `renderPogGapCharts()` | `dashboard/index.html` | Commercial Analytics — price/gap-related charts |
| `tests/test_pr193_reconciliation.py` | test | Category and Reliance reconciliation tests (Controls 2, 3) |

`detail_records` is by far the most widely-consumed single object in the dashboard — any canonical `PRIMARY_NSV`/`CHANNEL_PRIMARY_NSV` migration touches every function in this list, which is why the phased rollout plan (design doc) puts Executive Cockpit and Explorer in early, separate phases rather than one combined migration PR.

## `D.reliance_brand_counters`

Written by: `load_reliance_bc_data()`.

| Consumer | File | Kind |
|---|---|---|
| **None.** | — | Verified via grep: zero occurrences of `reliance_brand_counters` anywhere in `dashboard/index.html`. This block is written by the Python pipeline and never read by any current dashboard view — directly relevant to **ADR-003**: whichever option is chosen, options B and C both require wiring this real, currently-idle data into a UI for the first time; option A requires no change here |

---

## Summary: what a canonical migration would need to touch, by metric

| Metric | JS functions to migrate | Count |
|---|---|---|
| `PRIMARY_NSV` / `CHANNEL_PRIMARY_NSV` | `buildExecutiveCockpit`, `buildChannelDynamics`, `buildPrimary` (×2, legacy), `buildComparison` (×2), `computeChannelHealth`, `buildExplorer`, `renderChannelSubview`, `consolidateChains`, `expLine`, `computeNpiPerformance`, `npiSetCohortFy`, `computeSkuVolatility`, `skuVolatilitySection`, `renderPogGapCharts` | ~15 call sites across 2 source objects (`primary.by_channel`/`by_chain` and `detail_records`) |
| `OFFTAKE_NSV` / `CHAIN_OFFTAKE_NSV` | `buildInventoryHealth` (×3 distinct reads), `fy25SecondarySection`, `computeChannelHealth` | ~5 call sites, 1 confirmed defect (`KI-OFFTAKE-001`) |
| `RELIANCE_OFFTAKE_NSV` | None today (block is unread) | 0 — pure greenfield wiring once ADR-003 resolves |
| `CATEGORY_OFFTAKE_NSV` / `STORE_OFFTAKE_NSV` | None (no source exists) | N/A |

This table is the concrete basis for the phased implementation plan in `docs/CANONICAL_FINANCIAL_TRUTH_DESIGN.md`: Primary-side metrics have the widest blast radius (Phase 3-4 in that plan splits Executive Cockpit from Performance/Comparison rather than migrating all ~15 call sites in one PR), Offtake-side metrics are narrower and directly gate closing `KI-OFFTAKE-001` (Phase 5), and Reliance is genuinely greenfield pending a business decision (Phase 6).
