# Data Lineage

**Created:** 2026-09-13. Traces the two KPIs actually investigated this pass
(Primary NSV, Offtake NSV) plus the chain-allocation and category-mapping
mechanisms end to end, so a future question ("where did this number come
from?") does not require re-deriving the answer from scratch. Extend this file
the next time a KPI's lineage is actually traced -- do not pre-fill entries for
KPIs not yet investigated (see `docs/BUSINESS_LOGIC_REGISTRY.md` for the rule
definitions of TDP/CM2/Market Share/SSG, which are documented but not
re-traced here).

## Primary NSV

```
RAW SOURCE
  PowerBI/RawDataFolders/Primary_Article_Monthly/primary_article_<Mon>_<YY>.csv
  (one file per month, invoice-line grain; FY25 files use column "Chain name",
   FY26+ files use "Chain name for Dashboard" -- see BL-03 canonicalization)
        |
TRANSFORMATION
  scripts/build_dashboard_data.py: load_primary_v2()
  NSV = "Inv. Net value(LOC)" / 1e5  ->  Lakh
        |
BUSINESS RULE
  BL-01 (THE ONE FY RULE) assigns each row's FY from Month+Year
  BL-02 (Distributor->Chain allocation) re-splits "Dist." PO-Type rows using
        real secondary-offtake contribution fractions; "Direct" rows keep
        their own chain name as-is
  BL-03 (canonicalization) normalizes chain/brand/zone/state spelling variants
        |
VALIDATION
  scripts/release_gate.py gates G3 (reconciliation variance <= 0.01%),
  G5 (allocation coverage >= 95%, currently advisory), G6 (unmapped <= 2%)
  config/baselines.json: primary_nsv_fy26 frozen at Rs32,900.36L
        |
OUTPUT
  dashboard/data.js: primary.*, detail_meta.fyx_primary
  PowerBI/PowerQuery/16_Fact_PrimaryArticle.pq (Power BI equivalent, same rules)
```

**Verified 2026-09-13** (`scripts/reconcile_primary_baseline.py`): summing
`Inv. Net value(LOC)` across all 16 monthly files currently on disk reproduces
both Rs32,900.36L (FY26 subtotal) and Rs51,481.65L (16-month grand total)
exactly. A third figure, Rs46,560.34L (`PowerBI/docs/Desktop_Assembly_Checklist.md`
Phase J), is explained as stale-by-one-month (see that file's own note), not a
defect.

**Unresolved: Aug'26 Primary total (SOURCE_CONFLICT, not silently picked).**
Two Aug'26 sources exist and disagree:
- `data/monthly/Aug26_primary_detailed.csv` (article grain): Rs36.58 Cr.
  Corroborated three independent ways: matches `Aug26_chain_summary.csv`
  (sum of `Primary_Crores` column), `Aug26_zone_summary.csv`, and
  `Aug26_metrics.json`'s `primary_nsv_cr` field, all exactly.
- `PowerBI/RawDataFolders/Primary_Aug26_FY27.csv` (Bill-to-customer grain):
  Rs38.72 Cr (`NSV` column already in Lakh, summed and divided by 100).
- Gap: ~Rs2.14 Cr (~5.5%). Not reconciled -- could be a different cutoff date,
  additional adjustment/credit rows in one file, or a scope difference between
  invoice-line and customer-level aggregation. **Recommended next step:** ask
  the data owner which file is the approved Aug'26 Primary source before
  either is used for a published total; the article-grain file is used
  provisionally above because it has three-way internal corroboration the
  other file lacks, not because it is confirmed correct.

## Offtake NSV

```
RAW SOURCE
  FY25/FY26: pre-aggregated source workbooks (gitignored; baked into data.js
             by a full build -- raw files are not in the repo)
  FY27+:     PowerBI/RawDataFolders/Offtake_Monthly/offtake_store_article_<Mon>_<YY>.csv
             (store x article grain, one file per month)
        |
TRANSFORMATION
  FY25/FY26: scripts/build_dashboard_data.py (full build, offtake block)
  FY27+:     scripts/build_dashboard_data.py --offtake-patch
             NSV column is already in Lakh at row grain
        |
BUSINESS RULE
  BL-07 (Reliance Brand Counter isolation): rows where Chain Name ==
        "Reliance Brand Counter" MUST be excluded from any offtake total --
        they carry a documented 49% double-count risk. This is NOT optional
        formatting; verified 2026-09-13 that excluding RBC is exactly what
        makes the Jul'26 computed total (Rs36.21 Cr) match the independently
        supplied Rs36.18 Cr benchmark, and including it (Rs40.67 Cr) does not.
  BL-08 (Offtake FY27 coverage): --offtake-patch is idempotent, merges under
        total_fyNN / monthly_fyNN / months_fyNN keys, never double-counts
        |
VALIDATION
  config/baselines.json: offtake_fy26_total frozen at Rs31,119.87L
  tests/test_dashboard_disclosures.py::TestBrandCounterDisclosure (6 tests)
        |
OUTPUT
  dashboard/data.js: offtake.total_fyNN / monthly_fyNN / months_fyNN /
                      zone_monthly_fyNN
  PowerBI/PowerQuery/11_Fact_OfftakeSales.pq (Power BI equivalent)
```

**The "Aug'25 unavailable" failure, traced.** An agent asked for Aug'25
Offtake and searching only `PowerBI/RawDataFolders/Offtake_Monthly/` (earliest
file: Apr'26) will wrongly conclude the month doesn't exist. Root cause:
that watch folder is scoped to the FY27+ patch mechanism only -- it was never
meant to hold FY25/FY26 history, which already lives in `dashboard/data.js`'s
pre-aggregated `offtake.monthly_fy26` array (Aug'25 = index 4 = Rs2,435.71L,
confirmed 2026-09-13, and the array sums exactly to `total_fy26`). See
`config/data_source_registry.yml`'s `offtake_preagg_fy25_fy26` entry and
`scripts/data_catalog.py get_historical_source("offtake_nsv", "2025-08")`.

## Chain / distributor allocation

```
RAW SOURCE: Primary file's PO Type column (Direct vs Dist.) + Ship-To Name
        |
Direct rows -> chain name taken as-is (canonicalized)
Dist. rows  -> split via REAL secondary-offtake contribution fractions:
               1. article-level ratio (distributor+brand+description), else
               2. distributor+brand ratio, else
               3. "Unmapped Chain" (never silently dropped, never guessed)
        |
IMPLEMENTATION: scripts/aug26_data_readiness_gate.py:allocate_primary()
                (ad-hoc Aug'26 files) / scripts/build_dashboard_data.py
                apply_chain_allocation() (production monthly build) --
                same methodology, same non-negotiable reconciliation
                assertion: allocated total == parent Primary total, exact
        |
EXCEPTION HANDLING: a chain the allocator cannot place lands in
                     TRACKED_EXCEPTION_CHAINS with an evidence-based status
                     (MATCHED / MAPPING_GAP / SECONDARY_SOURCE_MISSING /
                     PRIMARY_SOURCE_MISSING / UNRESOLVED) -- never silently
                     zero, never silently merged into another chain
```

**Verified 2026-09-13.** Re-ran `scripts/aug26_data_readiness_gate.py` against
the current, complete Aug'26 files (the repo's one prior baseline record, from
2026-09-09, used an incomplete offtake upload and is stale -- 42% coverage vs
81.4% on today's complete file). Lulu, Spencer, Ratnadeep, National Mart,
Frankross, Sumo Save and B&N all resolved to `PRIMARY_SOURCE_MISSING` for
Aug'26 -- checked against both secondary evidence and pooled-distributor
("Customer name 2") evidence, genuinely absent, not a groupby artifact.

## Article -> Category / Sub-category (blank-field recovery)

```
Primary file's own sub_category / PPT Category columns (populated on most
monthly files) is the primary source.

WHEN BLANK on a given month (confirmed: primary_article_Jul_26.csv, 0 of
31,355 rows populated in either field):
  FALLBACK -> the SAME EAN's Sub_category on the Offtake file for the same
              period (offtake_store_article_Jul_26.csv carries it at full
              population) -- join on EAN, not on free-text description.

This is a genuine per-month data gap on one file, not a structural absence of
the business dimension. "Category analysis is impossible" is the wrong
conclusion; "the Primary file itself doesn't carry it this month, use the
Offtake join" is the checked one.
```
