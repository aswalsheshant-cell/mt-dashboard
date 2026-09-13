# 95%-Cumulative-Contribution Presentation Hierarchy

**Created:** 2026-09-13. A governed presentation rule for long-tail
Subcategory-within-Category (and, where a live consumer exists, Brand)
charts/tables: **PRESENTATION only, never a data-deletion rule.** No source
array, filter, export or canonical NSV is changed — only what one visual
groups into one bucket for display.

**Why 95% cumulative, not a fixed Top-N:** how many contributors matter can
change by FY, month, chain, zone or brand filter. A fixed Top-5/Top-10 either
hides a real contributor or clutters the view with near-invisible slivers,
depending on how many items happen to exist in that filter context.
Cumulative contribution adapts automatically because it's recomputed from
whatever filtered array reaches the visual — never a pre-computed, hardcoded
ranking.

## The rule

**Subcategory:** calculated **within each Category independently** (never
one global subcategory ranking) — subcategories covering the first 95% of
their OWN parent Category's NSV display individually; the remainder for that
Category groups into **"Others."**

**Brand:** the same rule (brands covering the first 95% of NSV display
individually, remainder -> **"Emerging Brands"**) — implemented as a shared,
tested utility (`cumulative95Group()`), but **not currently wired into any
live visual** — see "Where it is NOT applied" below for why.

**Category** itself is NOT grouped by this rule — a separate, not-yet-made
business decision.

**Boundary rule:** cumulative contribution, not a per-item `>= 5%` filter —
an item is included if the RUNNING cumulative total *before* adding it is
still under 95% (so the item that crosses the threshold is the last one
included). Matches the worked example: Mamaearth 70% / Derma Co 85% /
Aqualogica 91% / Dr Sheth's 95% -> all four included, rest -> tail.

**Deterministic tie-break:** value descending, then name ascending — applied
everywhere this class of bug was found (an unstable sort tied to
object/array/set iteration order, which is process-dependent and not stable
across rebuilds): `cumulative95Group()`, `subcatPareto95()`, `grp()`, and the
Category & Pack Mix drill table's own sort, all in `dashboard/index.html`;
`cm2_block()`'s `rollup()` in `scripts/build_dashboard_data.py`.

**Negative values (returns/MRN/credit adjustments):** never deleted, zeroed,
or `abs()`'d. A negative or zero item can never count as a "major" positive
contributor, so it always falls into the tail bucket — but the bucket's total
is the real **signed** sum (e.g. `+2.0 +1.0 -0.5 = 2.5`, never `3.5`). Full
unaggregated detail remains in `detail_records`/the article-level export;
grouping never removes a row from underlying data, only from one visual's
display array.

**Conservation:** `SUM(major items) + tail_value == SUM(all items)` exactly,
by construction. Verified by `tests/test_contribution_grouping.js` on
synthetic edge cases, the real `D.primary.by_brand` data, AND a real render
of the live drill table (see below).

## Where it IS applied (live, verified by rendering the actual page)

| Visual | Function | Grouping | Ranking metric | Ranking context |
|---|---|---|---|---|
| Sub-Category level of the Category & Pack Mix drill table (Channel & Chain Performance tab) | `dashboard/index.html`, `renderChannelSubview()`'s `sv==='category'` branch | Subcategory-within-Category 95% -> **"Others (N sub-categories, <95% cutoff)"** row | Article-level Primary NSV (`recFilter()`, scoped to the Category already selected via the drill path) | Whatever Chain/Zone/Brand/FY/Month filter plus drill path (`catPath`) is currently active — recomputed on every render |

Verified live (not just unit-tested): drilling into "Face" (real FY26-27
data, 18 categories -> Face has 27 sub-categories) now shows exactly 5 named
sub-categories (Face Cleanser 59.9%, Sun Care 20.6%, Unknown 8.9%, Face Serum
4.5%, Moisturisers 3.4% — cumulative 97.3%, crossing 95% at Moisturisers) plus
one `Others (22 sub-categories, <95% cutoff)` row at 2.7%, summing to exactly
100%. Previously this table showed all 27 rows unbounded.

## Where it is NOT applied, and why (important correction made during this change)

The two visuals that looked like the natural target at first — a "By Brand"
bar chart (`prBrand` canvas) and a "NSV by Sub-category" donut (`catSubP`
canvas, originally grouped **per-Brand**, not per-Category, which was itself
inconsistent with this rule) — turned out to be defined inside
`buildPrimary()` and `buildCategory()`, **two functions with no live caller
anywhere in `index.html`** (confirmed: `grep -n "buildPrimary("` and
`grep -n "buildCategory("` each return only the function's own definition
line). These are pre-`v1.1.0`-consolidation leftovers, the same category
CLAUDE.md already documents for `buildOfftake`/`buildDistribution`/etc. — code
still present but reachable only via `LEGACY_TAB_ROUTES`, which today routes
`'primary'` and `'category'` to `channel-dynamics` (`buildChannelDynamics` /
`renderChannelSubview`), not to these two functions.

Grouping logic was initially added to both dead functions before this was
caught by trying to render the actual chart in a browser and finding neither
canvas exists in the live DOM. That work was reverted rather than left as a
second, parallel "fix" nobody will ever see (CLAUDE.md: "don't treat this as
a second, parallel UI to maintain"). `subcatPareto95()` itself is left
corrected (Category-scoped, deterministic, signed-negative-safe) since it is
objectively more correct than its previous Brand-scoped form even though
nothing currently calls it — if this dead code path is ever revived, it will
already be right.

**No live Brand-specific chart exists in this dashboard today** that shows a
raw, cluttered list of every brand (`D.primary.by_brand` in the live
"Performance & Comparison" tab is a sortable **table**, where a long tail of
small rows is a materially smaller readability problem than a bar/donut chart
with invisible slivers). `cumulative95Group()` is built, tested, and
documented so it can be applied to a real Brand chart the moment one exists,
without re-deriving the logic.

`cm2.by_brand`/`cm2.by_category` (`scripts/build_dashboard_data.py`,
`cm2_block()`) are computed and shipped in `data.js` but are **also not
rendered by any chart or table today** (only `cm2.by_chain` is, on the P&L
tab) — pre-existing, not introduced by this change. Only the deterministic
tie-break sort (the actual reported `Hair Colour`/`Fragrances` symptom) was
applied there.

## Click-through / drill behaviour

- **Others row** (Category & Pack Mix Sub-Category table): not drillable
  further (a mixed remainder isn't one business entity), but its full
  constituent sub-category list is available on hover (`title` attribute) —
  full diagnostic visibility without adding a second detail layer.

## Known limitation not fixed here

A full Visual Registry (every card/chart in `index.html` classified
AUTHORITATIVE/DIAGNOSTIC/DUPLICATE/LEGACY/MISLEADING) still does not exist in
this repo (see `docs/AGENT_ARCHITECTURE_MAPPING.md`, item 08) — this document
records the grouping rule for the one live visual it actually touches, not a
substitute for that larger, separately-scoped audit. The dead-code discovery
above (`buildPrimary`/`buildCategory` unreachable) is itself exactly the kind
of finding that audit would be expected to catch systematically.
