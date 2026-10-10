# Power BI full report: issue ledger

Started 2026-10-10. Branch `claude/gallant-shannon-wou27y`. Update this file as each item moves.
Status labels follow the repo convention. Nothing here is Desktop-verified.

## G0 Workspace safety

| Item | Finding | Status |
|---|---|---|
| This branch | Clean at `bda3dd9`, 0 ahead / 0 behind its remote when this work started. | OK |
| The 20 tracked deletions | They exist only in the local Windows worktree (`codex/powerbi-full-report-20261004`, HEAD `8dbf598`). They cannot be seen from this cloud branch. | OPEN, needs local check |
| Nielsen files on this branch | All still present: `PowerQuery/13_, 47_, 48_, 51_, 57_*.pq`, `DAX/04_, 18_*.dax`, `SeedData/Nielsen/**`, `data/nielsen/**`, `dashboard/nielsen.js`, `Nielsen_MS_Dashboard_Jul26.html`. | OK here |
| History | Only commit touching Nielsen with deletions is `bf64ffd` (#300), which removed old `.pptx` files, not Nielsen sources. | No intentional Nielsen removal found in Git |

To compare on the local machine (read-only, changes nothing):

```
git status --short | findstr /B " D"
git diff --stat origin/claude/gallant-shannon-wou27y -- PowerBI/PowerQuery PowerBI/SeedData PowerBI/DAX data/nielsen dashboard/nielsen.js
```

Do not restore, reset or clean until each deleted path is listed and someone confirms it was intentional.

## G1 Source coverage (default window Apr-25 to Aug-26)

Full detail: `PowerBI/full_report_sources.json` (made by `scripts/powerbi_full_sources.py`).

| Table | Status | What it means | Pages hit |
|---|---|---|---|
| Fact Primary Sales | TEMPLATE_ONLY | `Primary_Weekly` has only the template. No weekly Primary data. | 1, 2, 3, 4, 6, 7, 8 |
| Fact Offtake Sales | INCOMPLETE_PERIODS | Folder has Apr-26 to Aug-26 only. FY26 is missing here (FY26 offtake sits in `dashboard/data.js`). | 1, 2, 3, 6, 7, 8 |
| Fact Primary ShipTo | INCOMPLETE_PERIODS | Covers to May-26. Jun to Aug-26 missing. Three overlapping snapshots, double count risk. | 2B, 3 |
| Fact Secondary Sales | INCOMPLETE_PERIODS | Apr-26 to Aug-26 only. FY25/FY26 not in these folders. | 2, 3 |
| Fact Nielsen, Nielsen Pack, Pack Brand, Brand Cut | TEMPLATE_ONLY / EMPTY | Raw folders hold README or template only. Real Aug-26 files are in `SeedData/Nielsen`, but the queries read `RawDataFolders`. | 9 |
| Fact TDP | TEMPLATE_ONLY | No TDP monthly data. | 10 |
| Fact Store Type, Pack Size, Sales Cuts, Inhouse Distribution | MISSING | Queries read `RawDataFolders\Store_Cuts\*.csv`. The folder has a README only. Copy from `SeedData\Store_Cuts`. | 8, 10 |
| Fact Account Category / Geo / Assortment | INCOMPLETE_PERIODS | Seed files start later than Apr-25. | 9 |
| Fact P&L | DERIVED | Built from Fact Offtake Sales, so it inherits the offtake gap. | 4 |
| Dim Promo Calendar | READY, with warning | Query uses a hard-coded `PowerBI/RawDataFolders/...` path, not `pRootFolder`. It will not resolve on another machine. | 6 |
| Fact Primary Article | READY | Apr-25 to Aug-26, 17 files. | 2B, 7 |

Missing means incomplete. None of it is treated as zero.

## G1 Source-side expected values (not Desktop-verified)

Full detail: `PowerBI/reconciliation_expected.json` (made by `scripts/reconcile_powerbi_full.py`).

| Measure | Source result (Rs L) | Reference | Note |
|---|---|---|---|
| Primary Article FY26, Channel = MT | 30,684.99 | 30,684.99 | Matches the MT basis |
| Primary Article FY26, all channels | 32,900.36 | 32,900.36 | Matches all-channel |
| Primary Article FY27 Apr to Aug, MT | 21,075.63 | none | |
| Offtake FY27 Apr to Aug, gross | 8,784.64 | none | |
| Offtake FY27 Apr to Aug, ex Reliance Brand Counter | 8,276.46 | none | Counter split applies to Offtake only |
| Distributor Secondary (chain files) FY27 | 5,083.20 | none | |
| Offtake FY26 | not reproducible from these folders | 31,119.88 | Source folder starts Apr-26 |

## Findings to fix or decide

1. `16_Fact_PrimaryArticle.pq` does not filter Channel. An unfiltered Power BI total for FY26 will read 32,900.36, not 30,684.99. Decide: filter to MT in the query, or require a Channel slicer. Do not change until you choose. Primary must never lose Reliance rows.
2. Source FY text is inconsistent (`FY'25-26`, `FY'26-27`, `FY27`). The model must derive FY from Month (Apr to Mar rule), not from that text.
3. Channel text has a case variant (`Eb2b` vs `EB2B`). Fold case before grouping.
4. `46_Dim_PromoCalendar.pq` hard-coded path (see above).
5. Queries for Store Cuts and Nielsen read `RawDataFolders`, but the real files sit in `SeedData`. Either copy the files across or point the queries at the seed path.
6. The HTML has 11 subviews (3 + 3 + 5), not 9. `storecuts` (State, Pack & Store Type) and `tdp` (TDP & Distribution) were added after the 9 in CLAUDE.md. The page contract uses 11.

## Still needs Desktop or business input

- Desktop refresh, live DAX, screenshots, B5 run, Service draft: your Windows machine.
- B3, B4, B6 inputs: see `config/project_state.yml`.
