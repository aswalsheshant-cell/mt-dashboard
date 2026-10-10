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

**Verified 2026-09-26** (`scripts/reconcile_primary_baseline.py`, run in CI by
`tests/test_primary_baseline_reconciliation.py`): each documented Primary figure is a
total over a stated month window, recomputed from the monthly files
(`Inv. Net value(LOC)` / 1e5) -- FY26 Apr'25–Mar'26 = Rs32,900.36L; Apr'25–Jun'26
= Rs46,560.34L (`PowerBI/docs/Desktop_Assembly_Checklist.md` Phase J snapshot);
Apr'25–Jul'26 = Rs51,481.65L (#119 frozen 16-month baseline). All match exactly.
The all-months total (17 files to Aug'26: Rs55,139.95L) grows every month and is
not a baseline. The source FY column spells FY27 two ways (`FY'26-27`, `FY27`);
both normalise to FY27 and agree with each file's month.

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

**Piece 2 -- Rs96.80L (45.4% of the gap), EXPLAINED (2026-10-10).**
After matching on the returns treatment above, the entire remaining
difference sits inside the **MT channel only** (EB2B and SIS reconcile to zero
variance, both value and row count). Source B has 350 more MT-channel rows
(12,299) than Source A's MT `Sales`-only rows (11,949).

Cause: Source A's `Cancel Invoice` type holds 350 positive rows (+Rs96.80L,
all MT) and 350 negative rows (-Rs96.80L), net zero. Source B carries the 350
positive rows (the original invoice value) and not the 350 reversals. Check:
Source A `Sales` Rs3,774.80L + `Cancel Invoice` positive legs Rs96.80L =
Rs3,871.60L = Source B total, to the paisa. The row gap (350) matches the
count of cancelled invoices (350).

Full bridge (Rs lakh): Source B 3,871.60 - MRN returns 116.50 - cancelled
invoice reversals 96.80 = Source A 3,658.30. Source B is gross of both
returns and cancellations. Source A is net.

Reproduce: group `PowerBI/RawDataFolders/Primary_Article_Monthly/primary_article_Aug_26.csv`
by `MTD-Sale type` and sign of `Inv. Net value(LOC)`.

Earlier work that ruled out FOC rows (Rs0.017L) and literal duplicates in
Source B stands. The `Direct/Distributor` column in Source B is still 100%
"Direct" and cannot be trusted (`BUG_MAPPING` below). Source B's `Channel`
column also reads "MT" on every row; its real channel split is in `Chain Name`
(MT, EB2B, SIS).

**Recommendation: use Source A (`data/monthly/Aug26_primary_detailed.csv`,
Rs36.58 Cr) as the Aug'26 Primary NSV.** It is invoice/article-line grain
(matching how FY26 and Apr-Jul'26 FY27 Primary are already built elsewhere in
this pipeline -- see `detail_meta.fyx_primary`'s own note, "FULL (uncapped)
article-wise primary"), nets returns and cancellations explicitly, has
three-way internal corroboration, and its `PO Type` field is verified
reliable. Source B should not be used for the Aug'26 Primary total -- treat
it as superseded for that purpose, not deleted (still useful for spot-checks
outside MT channel, where it ties exactly). This does not require further
data-owner escalation to proceed with ingestion. Both pieces of the gap are
now explained (2026-10-10), so no technical discrepancy remains open between
the two files. Data-owner confirmation of the source choice is still welcome.

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
