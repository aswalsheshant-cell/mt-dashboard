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

**Aug'26 Primary total -- RECONCILED 2026-09-13 (was SOURCE_CONFLICT).**
Two Aug'26 sources exist and disagreed by ~Rs2.14 Cr (Rs213.30L). Row-level
reconciliation (not a guess) explains the entire gap in two pieces:

- `data/monthly/Aug26_primary_detailed.csv` (**Source A**, article/invoice-line
  grain, 19,070 rows): Rs36.58 Cr. Has `Inv No.`, `Article Code`, `EAN No.`,
  and an explicit `MTD-Sale type` field (`Sales` / `MRN` / `Cancel Invoice`)
  that nets returns and cancellations. Corroborated three independent ways
  already (chain/zone summaries + `Aug26_metrics.json`).
- `PowerBI/RawDataFolders/Primary_Aug26_FY27.csv` (**Source B**,
  Bill-to-customer grain, 16,488 rows, no invoice/article key): Rs38.72 Cr.

**Piece 1 -- Rs116.50L (54.6% of the gap), fully explained.** Source A's
`Sales`-type rows alone (ignoring its own MRN/Cancel netting) total
Rs3,774.80L; Source B totals Rs3,871.60L. By channel, Source A's `Sales`-only
figures for **EB2B** (Rs202.64L) and **SIS** (Rs72.75L) match Source B
**exactly**, to the rupee, row-count included (4,044 and 145 rows in both).
Source A's `MRN` (return/credit-note) rows are worth -Rs116.50L and its
`Cancel Invoice` rows net to ~Rs0. **Source B is a gross-of-returns figure --
it does not net out the Rs116.50L of Aug'26 returns that Source A correctly
subtracts.** This piece is closed: Source A's returns-netted treatment is
correct; Source B under-nets by exactly this amount.

**Piece 2 -- Rs96.80L (45.4% of the gap), isolated but not fully explained.**
After matching on the returns treatment above, the entire remaining
difference sits inside the **MT channel only** (confirmed: EB2B and SIS
reconcile to zero variance, both value and row count). Source B has 350 more
MT-channel rows (12,299) than Source A's MT `Sales`-only rows (11,949).
Investigated and ruled out:
- Not FOC invoices (Source A's FOC rows total Rs0.017L -- immaterial).
- Not literal duplicate rows in Source B -- de-duplicating Source B's MT rows
  on every shared dimension (customer/brand/zone/state/NSV/MRP/month)
  over-removes (drops to 10,528 rows, Rs3,345.26L, undershooting Source A),
  meaning many of the "duplicate-looking" rows are genuinely distinct
  transactions that happen to share those dimensions and values --
  coincidental, not a data defect, at customer grain with no invoice key.
- **A real, separate data-quality bug found in Source B along the way**: its
  `Direct/Distributor` column is **100% "Direct"** for every one of its
  16,488 rows. Source A's equivalent field (`PO Type`) shows the MT channel
  genuinely contains both `Direct` (Rs2,260.10L) and `Dist.` (Rs1,239.31L)
  billing -- Source B's totals are in the right neighbourhood for MT overall
  (consistent with including both), so the column isn't dropping distributor
  rows, but the column itself cannot be trusted for a Direct-vs-Distributor
  split. Registered as `BUG_MAPPING` in the exception register below.
- Remaining Rs96.80L residual: not resolved to a specific row-level cause
  with the columns available in these two aggregated extracts (neither file
  carries a shared unique transaction key). Immaterial to the recommendation
  below (2.7% of the Rs36.58 Cr total) -- flagged as `LOW` materiality, not
  blocking.

**Recommendation: use Source A (`data/monthly/Aug26_primary_detailed.csv`,
Rs36.58 Cr) as the Aug'26 Primary NSV.** It is invoice/article-line grain
(matching how FY26 and Apr-Jul'26 FY27 Primary are already built elsewhere in
this pipeline -- see `detail_meta.fyx_primary`'s own note, "FULL (uncapped)
article-wise primary"), nets returns and cancellations explicitly, has
three-way internal corroboration, and its `PO Type` field is verified
reliable. Source B should not be used for the Aug'26 Primary total -- treat
it as superseded for that purpose, not deleted (still useful for spot-checks
outside MT channel, where it ties exactly). This does not require further
data-owner escalation to proceed with ingestion; the residual Rs96.80L "how
exactly are these 350 MT rows different" question stays open as a
**non-blocking technical source discrepancy** (not formally called
"immaterial" without a Finance-set threshold to measure that against, per
the 2026-09-13 governance request).

**INGESTED 2026-09-13.** Schema-harmonized and production-ingested:
`scripts/ingest_aug26_primary.py` maps the raw-SAP 53-column source to the
production loader's exact 24-column `Primary_Article_Monthly` schema (full
Source-Column -> Canonical-Column -> Transformation table in that script's
docstring; every source column classified USED / renamed / or
IGNORED_WITH_REASON -- none dropped silently), writes
`PowerBI/RawDataFolders/Primary_Article_Monthly/primary_article_Aug_26.csv`,
verified row-count and value-exact against the source (19,070 rows, Rs36.58
Cr, both match to the rupee). `scripts/build_dashboard_data.py --detail-only
--detail-max-rows 0 --out dashboard/data.js` then picked it up automatically
via the existing monthly-CSV-glob fallback in `detail_records_real()` -- no
other code change needed.

Reconciliation, source through dashboard:
| Stage | Rows | NSV |
|---|---|---|
| Raw source (`Aug26_primary_detailed.csv`) | 19,070 | Rs36.58 Cr |
| Transformed (`primary_article_Aug_26.csv`) | 19,070 | Rs36.58 Cr (exact) |
| Canonical (`detail_meta.fyx_primary.FY27`, Apr-Aug) | -- | Rs22,239.59L = Rs18,581.29L (Apr-Jul, unchanged) + Rs3,658.30L (Aug, exact) |
| Dashboard (44-state sweep) | -- | 0 failures, 0 JS errors, 0 NaN/undefined |

`--detail-max-rows 0` (uncapped) was used deliberately after the default
40,000-row cap was tried first and found to silently reduce total
`detail_records` coverage from 100% (108,893/108,893 groups, matching the
prior file's own uncapped state) to 95.6% -- that would have been a real,
undocumented regression to drill-down granularity across **every** FY, not
just Aug'26, so it was reverted and re-run uncapped before this was
committed. FY25/FY26 verified unchanged (Rs32,900.37L / Rs31,119.87L, exact
to the pre-ingestion commit) -- diffed before and after per `CLAUDE.md`'s
own validation rule, not assumed.

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
