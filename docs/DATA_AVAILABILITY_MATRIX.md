# Data Availability Matrix

**Created:** 2026-09-13. **Scope of this pass:** Primary NSV, Offtake NSV, chain
allocation and article/category mapping only -- the datasets actually exercised
while investigating why an agent repeatedly declared data "unavailable." Other
KPIs (TDP, CM2, Market Share, SSG, forecast) already have rule definitions in
`docs/BUSINESS_LOGIC_REGISTRY.md` and readiness gates in
`config/analytics_config.json`'s `readiness` block -- they are not re-audited
here; add a row when they are actually investigated, not before.

Do not mark anything MISSING without checking `config/data_source_registry.yml`
and, where relevant, running `scripts/data_catalog.py` first.

Statuses: **AVAILABLE** (validated, ready to use) · **PARTIAL** (real data,
incomplete coverage -- use with the stated caveat) · **DERIVED** (computed via
an existing rule from another available source) · **PROVISIONAL** (Finance/
business sign-off pending) · **MISSING** (checked, genuinely absent) ·
**CONFLICT** (two sources disagree, not yet resolved).

## Primary NSV

| Period | Status | Source | Notes |
|---|---|---|---|
| FY25 (Apr'24-Mar'25) | **SOURCE_NOT_AVAILABLE — corrected 2026-09-13** | n/a | **This row previously said AVAILABLE. That was wrong** -- verified directly against the live `dashboard/data.js`: `primary.fy_tags == ['fy26']` only; there is no `fy25` key anywhere in the `primary` block. No true FY25 Primary billing extract exists anywhere in this repo (`.claude/skills/mt-distributor-secondary/SKILL.md` traced every file that looks like FY25 primary and found each one is either FY26/27-only or a synthesized Pareto-fallback, not a real extract). The only FY25 series in the dashboard is Distributor Secondary (see below) -- do not read `primary.*` and conclude FY25 Primary is present. |
| FY26 (Apr'25-Mar'26) | AVAILABLE_AND_LOADED | `PowerBI/RawDataFolders/Primary_Article_Monthly/*.csv` (12 months) + `dashboard/data.js primary.monthly_fy26` | Rs32,900.36L, matches CLAUDE.md exactly (reconciled 2026-09-13) |
| Apr-Jul'26 (FY27 article-level) | AVAILABLE_AND_LOADED | `dashboard/data.js detail_meta.fyx_primary.FY27.monthly_canon` | Rs18,581.29L across 4 months; sums with FY26 to Rs51,481.65L grand total, matches PR #119 exactly |
| Aug'26 | **AVAILABLE_BUT_NOT_LOADED, plus an unresolved CONFLICT** | Two Aug'26 sources disagree by ~Rs2.1 Cr: `data/monthly/Aug26_primary_detailed.csv` (article grain, Rs36.58 Cr, corroborated 3 ways) vs `PowerBI/RawDataFolders/Primary_Aug26_FY27.csv` (customer grain, Rs38.72 Cr) | Verified 2026-09-13: `detail_meta.fyx_primary.FY27.months_canon` still stops at `Jul-26` -- Aug'26 has NOT been merged into `data.js` yet. Two blockers, in order: (1) which of the two conflicting totals is correct (needs a data-owner decision, see `docs/DATA_LINEAGE.md`), (2) the raw-SAP Aug'26 file's schema (53 columns) does not match the production loader's expected trimmed schema (~24 columns) -- needs harmonization before ingest, not attempted blind |
| Aug'26, chain-level split | PARTIAL | `scripts/aug26_data_readiness_gate.py` output, 2026-09-13 run | 81.4% of NSV allocated to a matched chain; Lulu/Spencer/Ratnadeep/National Mart/Frankross/Sumo Save/B&N = `PRIMARY_SOURCE_MISSING` (checked, not a mapping bug) |
| Sep'26+ | Not yet arrived | -- | Will land in `Primary_Article_Monthly/primary_article_Sep_26.csv` per the existing naming convention; `fy_tag_from_ym()` will tag it FY27 automatically, no code change needed |

## Offtake NSV

| Period | Status | Source | Notes |
|---|---|---|---|
| FY25 (Apr'24-Mar'25) | **SOURCE_NOT_AVAILABLE — added 2026-09-13, was missing a row entirely** | n/a | Verified directly against `dashboard/data.js`: there is no `offtake.total_fy25` / `monthly_fy25` (non-secondary) key. Chain-level POS offtake was not collected/extracted for this year. Do not confuse this with `offtake.secondary_total_fy25` (below), which is a different measure (distributor-to-retailer), not store-to-consumer offtake. |
| FY25 Distributor Secondary (Apr'24-Mar'25) | AVAILABLE_AND_LOADED | `dashboard/data.js offtake.secondary_monthly_fy25` / `secondary_total_fy25` | Rs23,332.36L across 12 months, correctly namespaced with a `secondary_` prefix inside the `offtake` block -- this is the ONLY real series covering Apr'24-Mar'25 for any of the three MT measures |
| FY25-labelled month inside FY26 block (Aug'25) | AVAILABLE | `dashboard/data.js offtake.monthly_fy26[months_fy26.indexOf('Aug-25')]` | Aug'25 = Rs2,435.71L (Rs24.36 Cr). This is a **calendar** Aug'25, which under THE ONE FY RULE falls in **FY26** (Apr'25-Mar'26), not FY25 -- it is correctly filed there, and is not evidence that FY25 (Apr'24-Mar'25) offtake exists. Not in the raw `Offtake_Monthly/` watch folder because that folder is FY27+-only by design, not because the month doesn't exist. |
| FY26 (Apr'25-Mar'26) | AVAILABLE_AND_LOADED | `dashboard/data.js offtake.total_fy26` | Rs31,119.87L, frozen in `config/baselines.json` |
| Apr-Aug'26 (FY27) | AVAILABLE_AND_LOADED | `dashboard/data.js offtake.monthly_fy27` / `PowerBI/RawDataFolders/Offtake_Monthly/offtake_store_article_{Apr,May,Jun,Jul,Aug}_26.csv` | Rs19,044.99L across 5 months; Jul'26 ex-Reliance-Brand-Counter = Rs36.21 Cr, matches independently supplied Rs36.18 Cr benchmark |
| Reliance Brand Counter, Apr-Jun'26 | ZERO_ACTIVITY OR NOT SEPARATELY REPORTED (unresolved which) | n/a | RBC value is Rs0.00 in these three files -- either genuinely zero that quarter or the counter wasn't separately reported yet; not investigated further this pass. Remember: from Jul'26 the source forks `Chain Name` into "Reliance"/"Reliance Brand Counter"; for Apr-Jun'26 both share "Reliance" and only `Store Type` distinguishes them (BL-07) -- filtering by Chain Name alone for those 3 months silently double-counts, filtering by Store Type does not |
| Sep'26+ | Not yet arrived | -- | Will land in `offtake_store_article_Sep_26.csv`; `fy_tag_from_ym()` will tag it FY27 automatically |

## 29-Month Coverage Matrix (Apr'24-Aug'26) -- Primary / Distributor Secondary / Offtake

Requested window per the 2026-09-13 governance prompt. Status vocabulary follows that
prompt's own terms where a real determination was made this pass; every other domain it
asked about (Promotions, Claims, Trade Spend, COGS, Logistics, Targets, Inventory) is
**NOT_YET_AUDITED** here -- BL-15/BL-16 and `config/data_source_registry.yml` already
carry partial findings for some of them (see those documents), but this pass verified
only the three headline MT measures against the live `data.js`, not a full workbook-tab
sweep of every domain the prompt lists. Do not read a blank cell as zero.

| FY (project tag) | Calendar months | Primary | Distributor Secondary | Offtake (POS) |
|---|---|---|---|---|
| FY25 | Apr'24-Mar'25 (12 mo) | `SOURCE_NOT_AVAILABLE` -- no real extract exists anywhere in the repo | `AVAILABLE_AND_LOADED` -- Rs23,332.36L, 12 months | `SOURCE_NOT_AVAILABLE` -- no chain-level POS extract exists for this year |
| FY26 | Apr'25-Mar'26 (12 mo) | `AVAILABLE_AND_LOADED` -- Rs32,900.36L | Not published as a separate FY26 total (secondary continues to feed chain-allocation ratios internally, per `mt-distributor-secondary` skill, but is not shown as a headline FY26 series once real Primary+Offtake exist) | `AVAILABLE_AND_LOADED` -- Rs31,119.87L |
| FY27 (so far) | Apr'26-Aug'26 (5 of 12 mo) | `AVAILABLE_AND_LOADED` Apr-Jul'26 (Rs18,581.29L); Aug'26 = `AVAILABLE_BUT_NOT_LOADED` (raw source exists, unresolved CONFLICT + schema harmonization pending) | Continues to exist at EAN/article grain from FY27 (`SecondarySales_Monthly_TOT_Analysis/01_FULL_HIERARCHY_*.csv`), used for allocation, not published as a headline total | `AVAILABLE_AND_LOADED` -- all 5 months, Rs19,044.99L |
| FY27 (not yet arrived) | Sep'26-Mar'27 (7 mo) | `NOT_YET_ARRIVED` | `NOT_YET_ARRIVED` | `NOT_YET_ARRIVED` |

**Total genuinely available headline coverage today: 17 of the 29 requested months** (12
FY26 + 5 FY27-so-far) have both Primary and Offtake. The 12 FY25 months have neither --
only Distributor Secondary -- and that is a source-data limitation confirmed by direct
file search, not a dashboard bug, pipeline defect, or FY-mapping error. Closing it
requires the business to supply a real FY25 SAP/ERP Primary billing extract and a real
FY25 chain-level Offtake/POS extract; neither can be derived from what already exists in
this repo (see "Requesting real FY25 primary" in the `mt-distributor-secondary` skill for
the exact ask to send).

## Known data.js hygiene issue (does not affect the dashboard UI)

`dashboard/data.js` carries two duplicate top-level blocks, `meta` and `metadata`, with
identical content. `meta` is the one the UI actually reads (header title/period/footer in
`index.html`); `metadata` is read nowhere in `index.html` (checked 2026-09-13,
`grep -n "DASH.metadata" dashboard/index.html` returns nothing). Both blocks contain a
`coverage.fy25_months` / `fy26_months` / `fy27_months` sub-object that is **wrong** by
this project's own FY convention -- it lists `fy25_months: [Apr-25..Jul-25]`, which under
THE ONE FY RULE is FY26, not FY25. No script in `scripts/*.py` generates this block
(`grep -rn "fy25_months" scripts/*.py` finds nothing) -- it is leftover content from a
superseded build step, carried forward unedited across every partial-refresh patch since.
It causes no visible dashboard defect today because nothing reads `.coverage`, but it is
exactly the kind of stale, misleading field a future reader (human or AI) could
mistakenly trust if they open `data.js` directly instead of querying through
`scripts/data_catalog.py` or this matrix. Flagged, not fixed: fixing it means either (a)
finding a full-rebuild opportunity to regenerate `data.js` cleanly (no source files
staged for a full rebuild this session), or (b) a targeted one-off patch script -- not
attempted here since `data.js` must never be hand-edited and there is no material impact
to justify a bespoke patch script on its own.

## Chain / distributor allocation

| Question | Status | Source |
|---|---|---|
| Does a governed distributor->chain allocation exist? | AVAILABLE | `scripts/aug26_data_readiness_gate.py:allocate_primary()` (ad-hoc/Aug'26 files) and `scripts/build_dashboard_data.py:apply_chain_allocation()` (production monthly build) -- **use these, never a raw groupby on the billing-customer column** |
| Aug'26 allocation coverage | PARTIAL | 81.4% of Primary NSV value matched to a chain with real secondary evidence (2026-09-13 run); 42 raw chain strings still `NEEDS_REVIEW` (no governed `canon_chain()` alias yet) |

## Article -> Category / Sub-category mapping

| Question | Status | Source |
|---|---|---|
| Jul'26 Primary `sub_category` populated? | MISSING on that file | 0 of 31,355 rows (confirmed) |
| Is category analysis therefore impossible for Jul'26? | **No -- DERIVED** | Same EAN's `Sub_category` is fully populated on `offtake_store_article_Jul_26.csv` for the same period -- join on EAN instead of trusting the blank Primary field |
