# Data Model — Facts & Dimensions

**Purpose.** Name this repo's real data model in standard star-schema vocabulary
(fact table, dimension, grain), so it can be discussed in those terms — in an
interview, in a Power BI design conversation, or when deciding where a new
metric belongs. This is a **naming exercise over live, verified structure**,
not new data or new dashboard logic. Verified directly against the current
`dashboard/data.js` on 2026-09-16 (see "How this was verified" at the end).

**Relationship to `docs/DATA_JS_SCHEMA.md`.** That file documents the full
JSON shape of every block for developers wiring up the dashboard. This file
is narrower and complementary: it only names the fact/dimension roles. **Known
issue found while writing this doc:** `DATA_JS_SCHEMA.md`'s own description of
`detail_records` (Block 9) — field names like `article_id`, `brand`, `pack`,
`primary_fy25` — does not match the live file. The real fields are listed
below, verified directly against `data.js`. `DATA_JS_SCHEMA.md` also lists 14
top-level blocks; the live file has 30, including several load-bearing ones
(`targets`, `pvm`, `scorecard`, `mapping_health`, `cm2`) that aren't mentioned
there at all. That file needs a refresh — flagged as a separate follow-up, not
fixed here, since it's a bigger job than this doc.

---

## The core fact table: `detail_records`

```
detail_records: [
  { Month, FY, Channel, Zone, State, Chain, Brand, Category,
    SubCategory, Range, PackSize, Article, EAN, NSV, MRP, Qty },
  ...
]
```

| Property | Value |
|---|---|
| **Grain** | one row = one Article × one Chain × one Month |
| **Row count** | 160,834 |
| **FY coverage** | FY26, FY27 (verified — FY25 is not in this table; see "why two fact tables" below) |
| **Measures** (the numbers you sum) | `NSV`, `MRP`, `Qty` |
| **Dimension keys carried on the row** (degenerate dimensions — see below) | `Chain`, `Brand`, `Category`, `SubCategory`, `Range`, `PackSize`, `Article`, `EAN`, `Zone`, `State`, `Channel`, `Month`, `FY` |

This is a **transaction-grain fact table**: every aggregate you see on the
dashboard (chain totals, brand totals, category cuts) is `SUM(NSV)` or
`SUM(Qty)` over this table, grouped by whichever dimension column you filter
or group on. This is exactly the pattern behind the top-90%-buildup and
account/brand/subcategory cuts built earlier this session — a `groupby()` in
pandas is doing the same job SQL's `GROUP BY` does over this same table.

## The dimensions

None of these are separate tables in `data.js` today — they're **degenerate
dimensions**: the attribute values live directly on the fact row instead of
in their own lookup table with a surrogate key. That's a legitimate, common
pattern for low-cardinality attributes (a real star schema in Power BI would
likely split these into their own `Dim_Chain`, `Dim_Article` tables so a
slicer only touches a small dimension table instead of scanning 160K fact
rows — see `docs/knowledge/KA-06-star-schema-bridge-tables.md` for when that
split is worth doing).

| Conceptual dimension | Columns that carry it today | Notes |
|---|---|---|
| **Date** | `Month`, `FY` | THE ONE FY RULE derives FY from Month; see `CLAUDE.md` |
| **Chain (Account)** | `Chain` | e.g. DMart, Apollo, Reliance Retail — verified real values |
| **Product hierarchy** | `Brand → Category → SubCategory → Range → PackSize → Article → EAN` | A genuine hierarchy, not a flat list — Category & Pack Mix's drill-down (Category → SubCategory) walks exactly this chain |
| **Geography** | `Zone`, `State` | |
| **Channel** | `Channel` | e.g. "MT" |

## Why there are actually *two* fact tables, not one

`primary` (FY25/FY26, pre-aggregated by chain/zone/brand/month — no article
grain) and `detail_records` (FY26/FY27, article grain) are **two fact tables
at two different grains covering the same subject** — this is the "Coverage
split" already documented in `CLAUDE.md`'s THE ONE FY RULE section, just not
previously named in star-schema terms. KA-06's own rule applies directly:
*"Every fact table has ONE consistent grain, stated explicitly"* and *"Do not
relate unrelated fact tables to each other."* Concretely: never `UNION` or
naively sum `primary.FY26.total` with `detail_records` FY26 rows as if they
were one table — they're reconciled against each other (see `docs/DATA_LINEAGE.md`),
not merged. `offtake` and `pnl` are further aggregate fact tables of their
own, at their own grains (`offtake` is chain × month; `pnl` is chain × expense
head).

## One line for an interview

*"The core fact table is article-level transactions — Chain × Article ×
Month, with NSV/MRP/Qty as measures. The product hierarchy (Brand down to
EAN) and geography (Zone/State) are degenerate dimensions embedded on the
fact row rather than split into separate dimension tables. There's a second,
coarser-grain fact table for FY25/FY26 history that isn't unioned with the
detail table — it's reconciled against it — because mixing two grains in one
fact table is exactly the anti-pattern the star-schema pattern warns against."*

---

## How this was verified

```js
// Run in Node against dashboard/data.js — same check used to write this doc
const fs = require('fs');
const txt = fs.readFileSync('dashboard/data.js', 'utf8');
const d = JSON.parse(txt.slice(txt.indexOf('{'), txt.lastIndexOf('}') + 1));
Object.keys(d.detail_records[0]);           // -> field list above
[...new Set(d.detail_records.map(r => r.FY))]; // -> ['FY27', 'FY26']
Object.keys(d).sort();                       // -> all 30 top-level blocks
```

No field name or FY coverage claim above was assumed — each was run against
the live file on 2026-09-16.
