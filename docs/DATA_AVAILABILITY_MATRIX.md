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
| FY25 (Apr'24-Mar'25) | AVAILABLE | `dashboard/data.js` `primary.*` (pre-agg) | |
| FY26 (Apr'25-Mar'26) | AVAILABLE | `PowerBI/RawDataFolders/Primary_Article_Monthly/*.csv` (12 months) + `dashboard/data.js` | Rs32,900.36L, matches CLAUDE.md exactly (reconciled 2026-09-13) |
| Apr-Jul'26 (FY27 article-level) | AVAILABLE | `Primary_Article_Monthly/primary_article_{Apr,May,Jun,Jul}_26.csv` | Sums with FY26 to Rs51,481.65L grand total, matches PR #119 exactly |
| Aug'26 | **CONFLICT** | Two Aug'26 sources disagree by ~Rs2.1 Cr: `data/monthly/Aug26_primary_detailed.csv` (article grain, Rs36.58 Cr, corroborated 3 ways) vs `PowerBI/RawDataFolders/Primary_Aug26_FY27.csv` (customer grain, Rs38.72 Cr) | See `docs/DATA_LINEAGE.md` "Unresolved: Aug'26 Primary total" |
| Aug'26, chain-level split | PARTIAL | `scripts/aug26_data_readiness_gate.py` output, 2026-09-13 run | 81.4% of NSV allocated to a matched chain; Lulu/Spencer/Ratnadeep/National Mart/Frankross/Sumo Save/B&N = `PRIMARY_SOURCE_MISSING` (checked, not a mapping bug) |
| Sep'26+ | Not yet arrived | -- | Will land in `Primary_Article_Monthly/primary_article_Sep_26.csv` per the existing naming convention |

## Offtake NSV

| Period | Status | Source | Notes |
|---|---|---|---|
| FY25 (incl. Aug'25) | **AVAILABLE** | `dashboard/data.js` `offtake.monthly_fy26[months_fy26.indexOf('Aug-25')]` | **This is the fix**: Aug'25 = Rs2,435.71L (Rs24.36 Cr). Not in the raw `Offtake_Monthly/` watch folder because that folder is FY27+-only by design, not because the month doesn't exist. |
| FY26 (Apr'25-Mar'26) | AVAILABLE | `dashboard/data.js` `offtake.total_fy26` | Rs31,119.87L, frozen in `config/baselines.json` |
| Apr-Aug'26 (FY27) | AVAILABLE | `PowerBI/RawDataFolders/Offtake_Monthly/offtake_store_article_{Apr,May,Jun,Jul,Aug}_26.csv` | Jul'26 ex-Reliance-Brand-Counter = Rs36.21 Cr, matches independently supplied Rs36.18 Cr benchmark |
| Reliance Brand Counter, Apr-Jun'26 | MISSING (confirmed) | n/a | RBC value is Rs0.00 in these three files -- either genuinely zero that quarter or the counter wasn't separately reported yet; not investigated further this pass |
| Sep'26+ | Not yet arrived | -- | Will land in `offtake_store_article_Sep_26.csv` |

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
