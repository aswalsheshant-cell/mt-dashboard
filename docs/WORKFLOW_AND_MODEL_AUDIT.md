# Workflow & Semantic Model Audit

**Created:** 2026-09-13, in response to a direct request to audit the actual (not
assumed) end-to-end workflow before further dashboard changes. Everything in this
document reflects code and file evidence read during this pass, not a redesign
proposal -- per `CLAUDE.md`, this is an enhancement/completion codebase, and nothing
here recommends rebuilding working architecture.

---

## 1. The workflow AS IT ACTUALLY RUNS TODAY (traced, not assumed)

```
Raw source file (.xlsb/.csv/.xlsx, mostly gitignored)
        |
        v
config/data_source_registry.yml  <-- REGISTRATION (added 2026-09-13; before that,
        |                              a source could reach the dashboard with no
        |                              central record of what it was or its coverage)
        v
scripts/build_dashboard_data.py  <-- the ONLY generator of dashboard/data.js
   - load_primary() / load_primary_v2()   (pre-agg Primary, FY25/FY26 window)
   - load_offtake() / offtake-patch path  (Offtake, FY25/FY26 + FY27 patch)
   - load_fy25_secondary()                (the one real FY25 series)
   - detail_records_real()                (File 2 / monthly CSV glob -> article grain,
   |                                        FY27+ Primary lives ONLY here)
   - cm2_block(), tot_block(), alloc      (derived from the same article-level df)
        v
dashboard/data.js  (~9-46 MB baked JSON, window.DASH)  <-- DO NOT hand-edit
        v
dashboard/index.html  (single-file app, reads D.* blocks directly, no separate
                        semantic-model layer -- see Section 2)
```

**A second, parallel path exists and is NOT the production one:**

```
data_master.json (last touched 2026-08-26)
        v
scripts/ingest_primary_csv.py  --> writes master["metadata"]
        v
scripts/sync_data_js.py        --> regenerates a DIFFERENT data.js from data_master.json,
                                    writing the SAME object into both "meta" and
                                    "metadata" keys of its output
```

This is the origin of the stale `metadata` block investigated in the prior pass
(see `docs/DATA_AVAILABILITY_MATRIX.md` "Known data.js hygiene issue"). It is
already safely deprecated -- `.github/workflows/validate-data.yml` is
`workflow_dispatch`-only (not auto-triggered), and its own header comment records
that a prior session found this exact duplication. **Not retired further this
pass** (deleting scripts/a workflow is bigger and less reversible than this
pass's scope); `scripts/ci_validate_datajs.py` now WARNs if `metadata` and `meta`
ever diverge, so it cannot silently be trusted again.

**Duplicated-pattern check (per the governance request's own instruction: "if one
example of a bug is found, search for the same pattern"):** searched for other
`data_master.json`-shaped legacy inputs or a third competing generator --
`grep -rln "generate_data_js\|def main" scripts/*.py` shows `build_dashboard_data.py`
and `sync_data_js.py` are the only two files that write `dashboard/data.js`'s shape;
no third path found.

## 2. Semantic model reality check

This project does **not** have a Power BI semantic model in production. The two
deliverables (`CLAUDE.md`'s own description) are:
1. `dashboard/` -- a static JS app reading a single baked JSON blob directly. There
   is no relationship layer, no DAX, no star schema at runtime -- `index.html`'s
   JS functions (e.g. `consolidateChains()`, `drillLink()`) do the equivalent of
   joins/filters imperatively, in-memory, per render.
2. `PowerBI/` -- a **paste-in build kit** (`.pq`/`.dax` text files + seed CSVs). No
   `.pbix`/`.pbip` is committed as the real model; it can only be assembled inside
   Power BI Desktop, which this remote session cannot open, run, or inspect
   interactively. There is a small, separate `ModernTrade_Report.pbip` prototype
   (the GAP-01/GAP-02 CM2 demo covered in BL-16) -- its TMDL/model files ARE
   text-inspectable and were read during the BL-16 investigation, but it is a
   demo built on synthetic `sources/Fact_Financials.csv`, not the production model.

**What this means for Sections 5-10 of the governance request** (fact/dimension
classification, relationship cardinality/filter-direction review, many-to-many
justification): there is no live Power BI relationship graph in this repo to
audit programmatically beyond what `PowerBI/PowerQuery/*.pq` and `PowerBI/DAX/*.dax`
state as text, and no `.pbip`/TMDL project backs the production dashboard for a
structural relationship review. Classified `REQUIRES_POWER_BI_DESKTOP_VALIDATION`
for the actual PowerBI relationship graph, per the request's own rule to reserve
that label for what text/model artifacts genuinely cannot answer -- not applied to
the dashboard's own JS-level joins, which ARE inspectable and are covered below.

## 3. Fact grain -- the datasets that actually matter today

| Fact dataset | Business event | Grain (as it exists in the data) | Business date used | Where it lives |
|---|---|---|---|---|
| **Primary** (pre-agg) | SAP/ERP billing, FY25/FY26 window | Chain x Month (pre-aggregated -- the source workbook is NOT article-level for this window) | Invoice/posting date, pre-aggregated to month | `dashboard/data.js primary.*` |
| **Primary** (article-level, FY27+) | SAP/ERP billing, invoice line | Invoice-line: Customer x Article x Month x Chain (one row per `Inv No.` x `Article Code`) | `Inv. Date` | `detail_meta.fyx_primary`, `detail_records`; source `PowerBI/RawDataFolders/Primary_Article_Monthly/*.csv` |
| **Distributor Secondary** | Distributor DMS, sell-out to retailer | FY25: Ship-to x Chain x **Brand** x State x Month (no article/EAN). FY27+: Ship-to x Chain x **EAN**/article x Month | Distributor-reported transaction/settlement date | `offtake.secondary_*` (FY25); `SecondarySales_Monthly_TOT_Analysis/` (FY27+) |
| **Offtake** | Chain POS, sell-out to consumer | Chain-Store x Article x Month | POS reporting period (month) | `dashboard/data.js offtake.*`; source `Offtake_Monthly/offtake_store_article_*.csv` |
| **Provision/Claims** (`mt_provision_national_aug26`) | Chain/distributor claim provisioning | Party (distributor/chain) x Brand x Claim Type x Month | Provision/claim period (month) | not yet ingested to any dashboard block -- registered only, `config/data_source_registry.yml` |
| **Promotions** | Chain promo scheme | Promo line (chain x brand x scheme x month), already in production | Scheme applicable period | `dashboard/data.js promo.*` |
| **Targets/Budget** | RKAM/FY27 target planning | FY x Month x State x Chain x Brand x BDO/BDE x RKAM | Target period (month) | `dashboard/data.js targets.*`; `incentive_working/` (restricted, gitignored) for the incentive-specific target file |

**Grain mismatch already known and respected, not newly found:** Distributor
Secondary is brand-level in FY25 and article-level from FY27 -- this is exactly
why `Primary_Article_Synthesized_FY25.csv` (a **different, rejected** artifact)
had to invent a Pareto-fallback article split, and why FY25 article/category-level
CM2 is explicitly flagged as modelled, not real, in the `mt-distributor-secondary`
skill. This audit does not change that; it is restated here so the grain
constraint is visible in one place rather than only inside a skill file.

**A grain violation already prevented, not found new:** the two Aug'26 Primary
candidate files were at *different* grains (Source A = invoice-line, Source B =
customer-aggregate). The 2026-09-13 reconciliation (see `docs/DATA_LINEAGE.md`)
treated this correctly -- it did not blend the two, it picked the invoice-line
source as authoritative and explained the aggregate source's gap against it.

## 4. Business Relationship Matrix (the datasets that currently coexist in `data.js`)

| Dataset | Date/FY | Chain | Brand | Category | SKU/EAN | Channel |
|---|---|---|---|---|---|---|
| Primary (pre-agg) | DIRECT_KEY (Month column, FY derived) | MAPPED (raw chain string, no governed alias table for the pre-agg block) | DIRECT_KEY | NOT_APPLICABLE (pre-aggregated, no category grain) | NOT_APPLICABLE | DIRECT_KEY |
| Primary (article-level) | DIRECT_KEY | MAPPED (`scripts/aug26_data_readiness_gate.py:allocate_primary()` for governed Dist.->Chain splits; raw `Chain name` for Direct rows) | DIRECT_KEY | DIRECT_KEY (`category`/`sub_category` columns, sometimes blank -- see next row) | DIRECT_KEY (`EAN No.`/`Article Code`) | DIRECT_KEY |
| Primary, category blank rows (e.g. Jul'26 file) | -- | -- | -- | **BRIDGE_REQUIRED** -- 0 of 31,355 rows populated on that file; recovered by joining the SAME EAN to `Offtake_Monthly`'s `Sub_category` for the same period (99.6% match, already implemented) | via EAN | -- |
| Distributor Secondary FY25 | DIRECT_KEY | MAPPED (own chain-alias table, `mt-distributor-secondary` skill documents known defects: Central mis-tagged, "Chattishgarh" misspelling) | DIRECT_KEY | NOT_APPLICABLE (brand grain only, no category) | NOT_APPLICABLE | MAPPED (MT vs EB2B split) |
| Offtake | DIRECT_KEY | MAPPED, with the documented Reliance Brand Counter exception: `Store Type` must be used for Apr-Jun'26, `Chain Name` only forks correctly from Jul'26 (BL-07) | DIRECT_KEY | DIRECT_KEY | DIRECT_KEY | NOT_APPLICABLE (Offtake is MT-only by construction) |
| Promotions | DIRECT_KEY | DIRECT_KEY | DIRECT_KEY | DIRECT_KEY | UNRESOLVED (not checked this pass whether promo lines carry EAN-level detail or category-level only) | NOT_APPLICABLE |
| `mt_provision_national_aug26` | DIRECT_KEY (single month, Aug'26 only) | MAPPED (`Chain Name` column, not cross-checked against the governed chain-alias table this pass) | DIRECT_KEY | NOT_APPLICABLE (no category column in this file) | NOT_APPLICABLE | DIRECT_KEY |
| Targets | DIRECT_KEY | DIRECT_KEY | DIRECT_KEY | NOT_APPLICABLE | NOT_APPLICABLE | NOT_APPLICABLE |

`Chain` in Offtake and `Chain name`/`Customer Name` in Primary are **not** the same
column and are **not** guaranteed to use identical spelling -- this is exactly why
`scripts/aug26_data_readiness_gate.py:allocate_primary()` exists as a governed
mapping layer rather than joining the two on raw text. That governed layer is the
correct answer to Section 7/9's "connect through meaning, not convenience"
requirement for Primary<->Chain; it already existed before this pass and is reused,
not rebuilt.

## 5. Known workflow weaknesses (found across this and the two prior sessions)

1. **Two generators of `data.js`.** Documented in Section 1. Deprecated but not
   removed. Risk: low today (manual-dispatch only), but the scripts/workflow/
   `data_master.json` remain in the repo as a standing invitation to run the wrong
   path. `docs/PROJECT_STATE.md` already recommends full retirement; not executed
   this pass (destructive, needs explicit authorization).
2. **A synthetic-data bug reached a production block.** `PL_Expense_Input.csv`'s
   own "EXAMPLE ROW" placeholders were being silently treated as real Finance
   expense in `cm2_block()`. Fixed this pass (`load_pl_expense_input()` now filters
   them); regression test added (`tests/test_pl_expense_input_filter.py`). This is
   the concrete instance of Section 28's "search for the same synthetic-row pattern
   everywhere" -- checked `PowerBI/SeedData/Masters/*.csv` for other files
   containing an "EXAMPLE" marker; `PL_Expense_Input.csv` is the only one.
3. **A source file's own tagging field was unreliable.** `Primary_Aug26_FY27.csv`'s
   `Direct/Distributor` column read "Direct" for all 16,488 rows regardless of the
   underlying billing type -- not correctable upstream (the file itself is being
   superseded for the Aug'26 total, see Section 3), registered as a caveat on that
   file in `docs/DATA_LINEAGE.md` rather than silently trusted or silently dropped.
4. **`--detail-max-rows` defaults to a value that is NOT what production actually
   runs with.** The default (40,000) drops row-group coverage from 100% to 95.6%
   on the current dataset size. The committed `data.js` has always been built
   uncapped (`--detail-max-rows 0`) even though that isn't the CLI default --
   this is an easy mistake for a future run to make silently. **Recommendation:**
   change the CLI default to `0` (uncapped) so a plain `--detail-only` run matches
   what's actually been shipped, or add a coverage-drop WARN comparing against the
   existing file's own coverage before overwriting it. Not changed this pass
   (behavioral default change on a shared script deserves its own review, not a
   drive-by edit inside an unrelated ingestion task) -- flagged here as the
   concrete next hardening step. `scripts/ci_validate_datajs.py` now at least
   WARNs post-hoc if coverage drops below 99%.
5. **No automated schema-drift check for new monthly Primary files.** This pass's
   Aug'26 ingestion was schema-mapped by hand (in `scripts/ingest_aug26_primary.py`)
   because the raw-SAP export (53 columns) never matches the trimmed monthly-CSV
   schema (24 columns) that `Primary_Article_Monthly/` expects. A recurring monthly
   process would benefit from an explicit expected-vs-received column diff (Section
   31 of the governance request) -- not built this pass; noted as a genuine gap,
   not fabricated as already solved.

## 6. What this audit deliberately did NOT attempt

- A structural review of `PowerBI/PowerQuery/*.pq` and `PowerBI/DAX/*.dax`'s
  relationship/measure correctness beyond what BL-16's investigation already
  touched -- that paste-in kit has its own extensive `PowerBI/docs/` set
  (`DistributorPrimaryAllocation_Logic.md`, `DataDictionary.md`, `PageLayouts.md`)
  which already documents intended relationships; re-deriving that from scratch
  here would duplicate existing documentation rather than add to it.
- A full measure catalog across every KPI in `index.html` (dozens of inline
  calculations). Sections 12-20 of the governance request describe a rich
  analytical-insight layer (Primary-Offtake gap, promo/provision correlation,
  decomposition analysis, etc.) that depends on this audit's fact-grain findings
  above; building that layer is downstream work, appropriately sequenced after
  this document, not inside it.
