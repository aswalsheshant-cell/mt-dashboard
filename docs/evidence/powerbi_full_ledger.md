# Power BI full report: issue ledger

Started 2026-10-10. Branch `claude/gallant-shannon-wou27y`. Update this file as each item moves.
Everything below is source-side or static. Nothing is Desktop-verified.

Regenerate in this order: `powerbi_full_sources.py`, `reconcile_powerbi_full.py`, `build_model_bim.py`, `build_full_report_pages.py`, `generate_pbir_pages.py`.

## G0 Workspace safety

| Item | Finding | Status |
|---|---|---|
| This branch | Clean at `bda3dd9`, 0 ahead / 0 behind its remote when this work started. | OK |
| The 20 tracked deletions | They exist only in the local Windows worktree (`codex/powerbi-full-report-20261004`, HEAD `8dbf598`). They cannot be seen from this cloud branch. | OPEN, needs local check |
| Nielsen files on this branch | All still present: `PowerQuery/13_, 47_, 48_, 51_, 57_*.pq`, `DAX/04_, 18_*.dax`, `SeedData/Nielsen/**`, `data/nielsen/**`, `dashboard/nielsen.js`, `Nielsen_MS_Dashboard_Jul26.html`. | OK here |
| History | The only commit touching Nielsen with deletions is `bf64ffd` (#300). It removed old `.pptx` files, not Nielsen sources. | No intentional Nielsen removal found in Git |

To compare on the local machine (read-only):

```
git status --short | findstr /B " D"
git diff --stat origin/claude/gallant-shannon-wou27y -- PowerBI/PowerQuery PowerBI/SeedData PowerBI/DAX data/nielsen dashboard/nielsen.js
```

Do not restore, reset or clean until each deleted path is listed and someone confirms it was intentional.

## Defects found in the model build (fixed in this branch)

| # | Defect | Effect | Fix |
|---|---|---|---|
| M1 | `build_model_bim.py` read every `VAR x =` line as a new measure. | About 174 bogus "VAR ..." measures. Real measures such as `MoM Growth %`, `Latest Month NSV`, `L3M Average Sales` were dropped. The earlier count of 446 was wrong. | Measures start at column 0. VAR and RETURN are body lines. Names may hold %, -, and brackets like `Offtake NSV (CBA, M)`. Now 481 measures. |
| M2 | Same generator kept the same column twice in 5 tables. | Tabular Editor would refuse the deploy. | One column per name. A calculated column replaces a same-named source column. |
| M3 | `15_Fact_PrimaryShipTo.pq` loaded all 3 files in `Primary_ShipTo_Monthly`. | The two narrow files are exact subsets of the composite (27 months compared, 0 difference). Those months were counted twice. | The query skips the two subset files by name. New monthly files still load. Not tested in Desktop. |

Checks after the fix: 52 tables, 47 relationships, 481 measures, 22 calculated columns, no duplicate column names, every relationship column exists, every measure reference resolves except local SUMMARIZE aliases (`n`, `tot`, `RowCount`).

## Defects found, not fixed (need your decision)

| # | Finding | Proposed fix | Who decides |
|---|---|---|---|
| D1 | `16_Fact_PrimaryArticle.pq` does not filter Channel. An unfiltered FY26 total reads 32,900.36 L, not the MT basis 30,684.99 L. | Filter to Channel = MT in the query, or require a Channel slicer on Primary pages. Primary must never lose Reliance rows. | MT Leadership / you |
| D2 | `DAX/15_Promo_Measures.dax` names tables that do not exist: `Dim_PromoCalendar` (use `Dim Promo Calendar`), `Fact_ClaimMaster` (use `Fact Claim Master`), `Dim_Calendar` (use `Date Table`), `Fact_Secondary_TOT_Hierarchy` (no table in the model). | The first three are plain renames. The fourth needs a new query on `secondary_sales_tot_hierarchy_Apr_Aug_2026.csv` or a different base table. | You |
| D3 | `46_Dim_PromoCalendar.pq` uses a literal `PowerBI/RawDataFolders/...` path, not `pRootFolder`. | Use `pRootFolder & "\RawDataFolders\Promo_Calendar\..."`. | You |
| D4 | Store Cuts and Nielsen queries read `RawDataFolders`, but the real files sit in `SeedData`. | Copy the files across (`SeedData\Store_Cuts` to `RawDataFolders\Store_Cuts`) or point the queries at the seed path. | You |
| D5 | Source FY text is inconsistent (`FY'25-26`, `FY'26-27`, `FY27`) and Channel has a case variant (`Eb2b`). | FY must come from Month using `fnFYLabel`. Fold case on Channel. | Check in Desktop |
| D6 | The HTML has 11 subviews (3 + 3 + 5). CLAUDE.md lists 9. `storecuts` and `tdp` came later. | Update CLAUDE.md wording when you next edit it. The page contract uses 11. | You |

## G1 Source coverage (window Apr-25 to Aug-26)

Detail: `PowerBI/full_report_sources.json`.

| Table | Status | What it means | Pages that read it |
|---|---|---|---|
| Fact Primary Article | READY | Apr-25 to Aug-26, 17 files. Feeds `Total Primary NSV`. | 1, 2, 3, 4, 11 |
| Fact Primary Sales | TEMPLATE_ONLY | `Primary_Weekly` holds only the template. No page measure reads it. | none |
| Fact Offtake Sales | INCOMPLETE_PERIODS | Folder has Apr-26 to Aug-26 only. FY26 offtake sits in `dashboard/data.js`. | 1 to 12, 2B, 20 |
| Fact Primary ShipTo | INCOMPLETE_PERIODS | Composite has Apr-24 to Jul-26 with no Jun-26. | 2B |
| Fact Secondary Sales | INCOMPLETE_PERIODS | Apr-26 to Aug-26 only. No page measure reads it directly. | none |
| Fact Nielsen, Nielsen Pack, Pack Brand, Brand Cut | TEMPLATE_ONLY / EMPTY | Raw folders hold README or template only. Real Aug-26 files sit in `SeedData/Nielsen`. | 1, 9, 10, 11 |
| Fact TDP | TEMPLATE_ONLY | No TDP monthly data. | 1, 7, 9, 10, 11 |
| Fact Store Type, Pack Size, Sales Cuts, Inhouse Distribution | MISSING | Queries read `RawDataFolders\Store_Cuts\*.csv`. Folder has a README only. | 21 |
| Fact Account Category / Geo / Assortment | INCOMPLETE_PERIODS | Seed files start after Apr-25. | 9 |
| Fact P&L | DERIVED | Built from Fact Offtake Sales, so it inherits the offtake gap. | 4 |
| Dim Promo Calendar | READY, with warning | See D3. | 19 |

Missing means incomplete. None of it is treated as zero.

## G1 Source-side expected values (Rs lakh, not Desktop-verified)

Detail: `PowerBI/reconciliation_expected.json`.

| Measure | Source result | Reference | Note |
|---|---|---|---|
| Primary Article FY26, Channel = MT | 30,684.99 | 30,684.99 | Matches the MT basis |
| Primary Article FY26, all channels | 32,900.36 | 32,900.36 | Matches all-channel |
| Primary ShipTo composite FY26 | 32,900.36 | 32,900.36 | All channels, rupees in source |
| Primary Article FY27 Apr to Aug, MT | 21,075.63 | none | |
| Offtake FY27 Apr to Aug, gross | 8,784.64 | none | |
| Offtake FY27 Apr to Aug, ex Reliance Brand Counter | 8,276.46 | none | Counter split is Offtake only |
| Distributor Secondary (chain files) FY27 | 5,083.20 | none | |
| Offtake FY26 | not reproducible from these folders | 31,119.88 | Folder starts Apr-26 |

## G2 Page contract

Detail: `PowerBI/full_report_pages.json` and `PowerBI/docs/FullReportParity.md`.
11 tabs and 11 subviews all map to a page. 20 pages: 14 from PageLayouts.md and 6 proposed. Page status today: 9 PARTIAL, 6 NO_SOURCE, 4 NO_MODEL_SOURCE, 1 MODEL_ERROR. No page is READY yet, so the report cannot be called complete.

Generated page files are in `PowerBI/PBIR_Generated/`. They are scaffolding, written outside Desktop and not opened in it.

## Needs Desktop or business input

- Desktop refresh, live DAX, screenshots, B5 run, Service draft: your Windows machine.
- B3, B4, B6 inputs: see `config/project_state.yml`.
