# Power BI full report: issue ledger

Started 2026-10-10. Branch `claude/gallant-shannon-wou27y`. Update this file as each item moves.
Everything below is source-side or static. Nothing is Desktop-verified.

Static refresh check: `python scripts/check_pq_refresh_risks.py` (missing columns, bad values, unknown queries; it does not model joins, so a clean result is not proof of a clean refresh).

Desktop steps and the expected values to compare: `docs/evidence/POWERBI_DESKTOP_RUNBOOK.md` and `PowerBI/TabularEditor/05_DAXStudio_Validation.dax` (rebuilt by `scripts/build_desktop_validation.py`).

Regenerate in this order: `powerbi_full_sources.py`, `reconcile_powerbi_full.py`, `build_model_bim.py`, `build_full_report_pages.py`, `generate_pbir_pages.py`, `build_desktop_validation.py`.

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
| M4 | Six calculated columns (`TOT Method`, `TOT Pass-on Value` on Fact Primary Article; `Resolved Chain/Brand/Category`, `Bad Brand Or Category` on PL Expense Input) exist only as commented blocks in the DAX files. 12 measures use them. | Those measures would error in the deployed model. | The generator now reads the commented blocks and adds the columns, using the repo's own text. Not tested in Desktop. |
| M5 | Empty watch folders (Primary_Weekly, Nielsen x4, TDP) made `fnCombineFolder` return only 2 columns, so the next step failed with "column wasn't found" and stopped the whole refresh. | Refresh error in 6 queries. | `fnCombineFolder` takes an optional expected-column list and returns an empty table with those columns. The 6 queries pass their column lists. Not tested in Desktop. |
| M6 | `46_Dim_PromoCalendar.pq` typed `Locations` as number, but the file holds text like "PAN India" (2,613 rows). | Conversion error rows at load. | Typed as text. No DAX uses the column. |
| M7 | `16_Fact_PrimaryArticle.pq` selected `Chain name for Dashboard` and `MRP`, but 14 of the 17 files (Apr-25 to May-26) name them `Chain name` and `MRP Rate`. `MissingField.UseNull` hid it. | Chain and article MRP blank for 14 months, so Direct rows had no chain. Found by the independent review. | The query merges the old and new names (Qty x MRP matches Total MRP sales in both). The static checker now flags a column present in only some files. Not tested in Desktop. |
| M8 | The `model.bim` generator treated indented filter lines such as `'Chain Master'[Channel] = "MT"` inside measures as calculated columns. They replaced real columns (Chain Master Channel became a broken expression). Also the model had no `pRootFolder` or helper functions, and `FY Year` was typed as a number although its values are text like "25-26". Found by the independent review of the validation queries. | Deploy or refresh would fail, and every `FY Year` filter would mismatch. | Calculated columns are read only from column 0, so only the 6 real ones remain. `model.bim` now carries `pRootFolder`, `fnCombineFolder` and `fnFYLabel` as shared expressions. `FY Year` is text. |
| M9 | Offtake chain names such as `Dmart`, `H&G`, `Metro Cnc`, `Sancus(RMT)`, `Spencer` do not match Chain Master. 9,109.6 L of the 21,553.85 L FY27 offtake had no Chain Master row, so `[Total MT NSV]` was far too low. | Understated MT offtake and every chain view built on it. | `11_Fact_OfftakeSales.pq` maps 18 unambiguous spellings to Chain Master names. After that `[Total MT NSV]` is expected to be 17,936.36 L. Not tested in Desktop. |
| M10 | Two measures used columns that do not exist: `Actual FY26 Offtake` and `Actual FY26 RBC` filtered `'Date Table'[Fiscal Year] = 2026` (the column is `FY Year`, text), and `Dist Allocation Coverage %` filtered `'Fact Primary Article'[Is Dist]`, which query 16 deleted. | Both would error in Desktop. A test now fails if any measure names a missing column. | DAX uses `[FY Year] = "25-26"`. Query 16 keeps `Is Dist` and the model lists it. |
| M12 | Found 2026-10-11: `build_model_bim.py` gave all seven tables from `20_Dim_Masters.pq` (Brand, Category, Article, Zone/State, Store, Nielsen Competitor) the Chain Master query, and Channel Map Chain the Channel Map Store query, because the later queries in those files are commented-out blocks. Each of those tables would have loaded the wrong CSV. | Wrong data and broken relationships on deploy. | The generator splits those files by section header and uncomments each block. Tests check that no two tables share a query and each master loads its own CSV. The refresh checker now reads each of those queries too. |
| M13 | CI (Production Acceptance Gate) failed on the commit that copied Nielsen files into `RawDataFolders`: the restricted-source firewall treats everything tracked there as restricted. My local run missed it because the files were not staged yet. | A red gate. | Copies removed, queries repointed (see D4). Tests are now run after staging. |
| M14 | The refresh checker assumed each step builds on the one above it and could not see nested calls, so it missed a deliberate wrong column in a mutation test. | A clean checker result meant less than it seemed. | It now follows the step each call reads from, and the lookup read in query 15 is written as separate steps. A mutation test catches the wrong column. |
| M3 | `15_Fact_PrimaryShipTo.pq` loaded all 3 files in `Primary_ShipTo_Monthly`. | Every row of the two narrow files is in the composite on Month, Ship To Name, Brand, NSV and MRP, and monthly NSV is identical (independent check). Their Chain labels differ from the composite's normalised names, so they are not byte-identical. Those months were counted twice. | The query skips the two subset files by name. New monthly files still load. Not tested in Desktop. |

Checks after the fix: 52 tables, 47 relationships, 481 measures, 28 calculated columns, every `'Table'[Column]` used by a measure exists, no duplicate column names, every relationship column exists, every measure reference resolves except local SUMMARIZE aliases (`n`, `tot`, `RowCount`).

## Defects found, not fixed (need your decision)

| # | Finding | Proposed fix | Who decides |
|---|---|---|---|
| D1 | RESOLVED 2026-10-10 (owner decision): `16_Fact_PrimaryArticle.pq` now filters Channel through the parameter `pPrimaryChannel` (default `MT`; `ALL` loads every channel). Channel spelling is folded first (`EB2B` and `Eb2b`). Only EB2B and SIS rows are left out. Reliance and every other MT chain stay. FY26 reads 30,684.99 L on MT and 32,900.36 L on ALL. | Done, not tested in Desktop. | Done |
| D11 | RESOLVED 2026-10-11: `Fact Primary ShipTo` now has a Channel column from `SeedData/Masters/ShipToChannelMap.csv` (built by `scripts/build_shipto_channel_map.py` from Primary Article, where each ship-to name sits in one channel) and follows `pPrimaryChannel`. On MT, ShipTo FY26 is 30,684.99 L, equal to Primary Article. Ship-tos not in the map are labelled UNMAPPED and kept: 1,240.90 L in FY25 (names that never appear in Primary Article), none in FY26 or FY27. Rerun the script when a new ship-to appears. | Done, not tested in Desktop. | Done |
| D2 | RESOLVED 2026-10-10: Promo measures now use real tables. New query `62_Fact_Secondary_TOT_Hierarchy.pq` loads the article-grain sell-out file (41,671 rows, Rs 7,582.20 L Apr to Aug 2026). Relationships: Date Table to it by month, and Dim Promo Calendar EAN Code to its EAN (many-to-many; 247 of 265 promo EANs find sell-out). Promo `EAN Code` loses its ".0" float suffix so it matches. `Dim_Calendar[Month_Label]` became `'Date Table'[Month]`. | Done, not tested in Desktop. The many-to-many relationship is the first thing to check if Promo numbers look wrong. | Done |
| M11 | Found by review: `promo_mechanics_Sep_2026.csv` has 7 rows with commas inside quotes but the query read with `QuoteStyle.None`, so those rows shifted columns. "Offer to consumer" holds text (`BOGO`, 1,060 rows) so `VALUE()` errored, and `model.bim` typed it, `Description` and `Locations` as numbers. | Broken promo rows and a measure error. | Query reads with `QuoteStyle.Csv`. `IFERROR(VALUE())` in the discount measure, counted over numeric offers only. Those three columns are text. |
| D12 | The promo file is Sep-26 and the sell-out file is Apr to Aug 2026, so "Actual Promoted NSV" is the sell-out of EANs promoted in September, not sales during the promotion. | Treat promo ROI figures as indicative until a promo period that overlaps sell-out is loaded. | You |
| D3 | `46_Dim_PromoCalendar.pq` now uses `pRootFolder` (fixed). | Done, not tested in Desktop. | Done |
| D4 | RESOLVED 2026-10-11: Store Cuts queries read `SeedData\Store_Cuts`, and the four Nielsen queries (13, 47, 51, 57) now read `SeedData\Nielsen\<folder>`, where `scripts/build_nielsen_powerbi_seed.py` writes its files. An earlier attempt copied the Nielsen files into `RawDataFolders`; the restricted-source firewall (`tests/test_restricted_source_firewall.py`) rejects any tracked file there, so the copies were removed. Nielsen is Aug-23 to Aug-26; pack, pack-brand and brand-cut are Aug-26 only. | Done. | Done |
| D5 | Source FY text is inconsistent (`FY'25-26`, `FY'26-27`, `FY27`) and Channel has a case variant (`Eb2b`). | FY must come from Month using `fnFYLabel`. Fold case on Channel. | Check in Desktop |
| D7 | `Primary_Aug26_FY27.csv` (root of `RawDataFolders`) is Rs213.30L higher than the Aug-26 article file: MRN returns 116.50 + 350 cancelled invoices 96.80, all MT. EB2B and SIS tie once returns are excluded. | Leave it out of `Primary_Article_Monthly`. Reconciled in `docs/DATA_LINEAGE.md`. | Owner to confirm |
| D8 | RESOLVED 2026-10-11: `Cont%` in the composite file was on two scales for distributor rows. Every ship-to/brand/month group sums to exactly 1 (846 groups) or exactly 100 (582 groups), nothing else, so `15_Fact_PrimaryShipTo.pq` divides a group by 100 when its sum is above 1.5. Direct rows are set to 1. A test guards the assumption for new months. | Done, not tested in Desktop. | Done |
| D9 | `promo_mechanics_Sep_2026.csv` holds -9.22e18 placeholder values in `Chain_Contribution_Pct` and `Total_Contribution_Pct`. They parse but would wreck any SUM. | Blank them at source or in the query. | You |
| D10 | RESOLVED 2026-10-10 (owner decision): FSN is eB2B. `Nykaa (FSN)` is added to `ChainMaster.csv` and `ChannelMap_Chain.csv` with Channel EB2B, and the offtake query maps `FSN`/`Fsn` to it. FSN (1,035.14 L Apr to Aug 2026) is out of `[Total MT NSV]`. Only Centro (0.18 L) is still unmatched. | Done, not tested in Desktop. | Done |
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
| Fact Store Type, Pack Size, Sales Cuts, Inhouse Distribution | READY / INCOMPLETE_PERIODS | Files found in `SeedData\Store_Cuts` after the path fix. Store Type is a single Aug-26 snapshot. The other three cover Apr-26 to Aug-26 only, so Apr-25 to Mar-26 is missing. | 21 |
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
| Offtake FY27 Apr to Aug, gross | 21,553.85 | none | An earlier version of this table said 8,784.64. It missed the Jul and Aug files and some Apr rows, whose month labels are `Jul`, `Aug` or an Excel serial. Fixed. |
| Offtake FY27 Apr to Aug, ex Reliance Brand Counter | 18,971.68 | `dashboard/data.js` offtake.total_fy27 = 18,971.69 | Matches to rounding. Counter split is Offtake only |
| Distributor Secondary (chain files) FY27 | 5,083.20 | none | |
| Offtake FY26 | not reproducible from these folders | 31,119.88 | Folder starts Apr-26 |

## G2 Page contract

Detail: `PowerBI/full_report_pages.json` and `PowerBI/docs/FullReportParity.md`.
11 tabs and 11 subviews all map to a page. 20 pages: 14 from PageLayouts.md and 6 proposed. Page status today: 11 PARTIAL, 5 NO_SOURCE, 3 NO_MODEL_SOURCE, 1 DOCUMENTATION (Refresh Guide, a text page), 0 MODEL_ERROR. Every NO_SOURCE page (1, 7, 9, 10, 11) is blocked only by `Fact TDP`: it needs a monthly file in `RawDataFolders/TDP_Monthly/` (template `_TEMPLATE_TDP_Monthly.csv`). The three NO_MODEL_SOURCE pages are the HTML-only views (Operational Alerts, Store Audit Scorecard, Supply Chain & Inventory), which have no source in the model. No page is READY yet, so the report cannot be called complete.

Generated page files are in `PowerBI/PBIR_Generated/`. They are scaffolding, written outside Desktop and not opened in it.

## Needs Desktop or business input

- Desktop refresh, live DAX, screenshots, B5 run, Service draft: your Windows machine.
- B3, B4, B6 inputs: see `config/project_state.yml`.


## How to resolve what is still open (2026-10-11)

External points below come from vendor documentation and industry references; the project rules about which numbers count still come from MT Leadership, Finance and Trade Marketing.

| # | Open item | What resolves it | Who | What the web research says |
|---|---|---|---|---|
| R1 | TDP: pages 1, 7, 9, 10, 11 | A monthly TDP extract in `RawDataFolders/TDP_Monthly/` using `_TEMPLATE_TDP_Monthly.csv` (ACV %, AIC, numeric and weighted distribution per SKU). Until it arrives the pages keep their banner. The in-house view (stores selling, SKUs per store) can be shown, labelled "not TDP". Do not estimate ACV. | Nielsen / RMS desk, Trade Marketing | TDP is the sum of %ACV across a brand's items. %ACV weights each store by its category sales, so it cannot be built from our own offtake. Numeric distribution is stores carrying the item over all stores. |
| R2 | D12: promo period (Sep-26) vs sell-out (Apr to Aug) | Promo calendars for the sell-out months, one file per month, and the promo query reading the folder instead of one named file. Then measure sell-out inside each promo window against a baseline (prior months, same period last year, or non-promoted stores). | Trade Marketing | Standard lift is promo-period sales minus an estimated baseline. Baseline choices: before/after, same period last year, control stores. Watch seasonality, stock-outs and cannibalisation. In DAX a promo-to-sales bridge with TREATAS is the usual pattern; filter the bridge's product and date together. |
| R3 | Store Audit Scorecard and Supply Chain & Inventory (page 23, 24) | Real extracts. `config/data_source_registry.yml` (`store_audit_compliance`) records the current dashboard data as synthetic with unverified origin. Do not load it into Power BI. Needed: a store-audit extract (PES: price, FSDU, availability per door) from Retail Execution / Trade Marketing, and a stock-on-hand and OTIF/fill-rate feed from Supply Chain. Register each in the data source registry before wiring. | Retail Execution, Supply Chain | Not a web question. |
| R4 | Operational Alerts (page 22) | Decide the alert rules and the source tables first; the alerts feed is built from the same dashboard blocks. | MT Analytics | Not a web question. |
| R5 | History before Apr-26 (Offtake FY26, Secondary, Store Cuts, Nielsen pack views) | The monthly CSVs split from the offtake workbook named in `11_Fact_OfftakeSales.pq` ("FY-24-26 Chain offtake Store Wise File till May.xlsb") with `scripts/split_offtake_store_article_xlsb.py`. That workbook is not in the repo. Keep the CSVs out of Git (firewall rule). | You | Not a web question. |
| R6 | Desktop deploy (runbook steps 3 to 5) | Use Power BI Desktop from June 2025 or later. Tabular Editor documents that from that update there are no unsupported write operations from external tools (tables, columns, M expressions); older Desktop versions block some of them. Reports using a live connection have no model to edit. | You | Tabular Editor docs, Microsoft TMDL view announcement. |
| R7 | Private Service draft refresh | Our queries read a local folder through `pRootFolder`. After publishing, scheduled refresh needs an on-premises data gateway on an always-on machine (Folder data source), or the data must move to OneDrive / SharePoint and the queries rewritten to the SharePoint connector. Without either, the draft is a manual refresh from Desktop. A Pro licence allows 8 scheduled refreshes a day. Record the refresh mode in the evidence. | You, IT | Microsoft Learn data-sources and OneDrive refresh pages; community gateway guidance. |
| R8 | The 20 tracked deletions on your local branch | Run the two read-only commands near the top of this file before any restore. | You | Not a web question. |
| R9 | B3, B4, B6 | Full Jul/Aug DN register, FY27 CM2 scope and claim rules (B3); Jun to Aug-26 AssumptionTable rows (B4); incentive decisions (B6). See `config/project_state.yml`. | Finance, MT Leadership, HR | Not a web question. |


## Deep-dive QC: PR and branch history (2026-10-11)

What happened: data files were committed on branches that were never merged, so `main` does not hold them. One cause: `.gitignore` allowed every `PowerBI/**/*.csv`, so raw drops could be tracked by accident.

Tools now in the repo: `scripts/audit_data_source_map.py` (maps every file Power BI, the HTML dashboard and the registry read; `--preflight` checks a machine that holds the real data), `config/data_header_pins.json` (column layouts), a `.gitignore` rule for new raw drops, and `scripts/restore_branch_files.py` (copies a chosen file from a branch to a local folder; never overwrites).

Source map result: 113 references, 0 missing, 0 unpinned layouts, 31 unreferenced files. See `docs/evidence/DATA_SOURCE_MAP.md`.

Why raw copies are not committed: the repo is public, raw store/customer/article files are CONFIDENTIAL in `config/restricted_source_policy.yml`, and the firewall test fails on new tracked files there. Owner decision I-2 is pending.

Files that exist only on unmerged branches (12 branches, 44 files):

| Branch (PR) | Files | Class | Action |
|---|---|---|---|
| cm2-distributor-claim-rebuild (#267 open, HOLD) | PL_Distributor_Claim_Input_Q1_FY27.csv (32 rows) | SAFE_SEED | Take from #267 after owner OK (B3). Allocated and alias files: NEEDS_OWNER. |
| po-billing-fill-rate (#279 open, deferred) | PO fill rate monthly (6,151 rows), unfilled reasons (884), PO vs target (5), QC json | NEEDS_OWNER | Real aggregate, 82.91% fill by quantity, OTIF not measurable, 22% of PO value has no chain. |
| june-26-sales-data-xzbhub (#16 closed) | EAN_Product_Master.csv (3,494 EANs); FY27_Monthly_GMV_MRP.csv | SAFE_SEED / NEEDS_OWNER | Chain mapping file is superseded. |
| offline-agent-pbi-workflow-08cz7j (no PR) | ChainAliases (16 rows), NPI_List, ArticleMaster (936 rows), market share, distributor-routed, account mapping | NEEDS_OWNER | ArticleMaster needs a classification answer (HEAD has 13 rows). |
| same branch | 15 SIS offtake files (54,100 rows), Primary MTD Jun-26, Secondary Jun-26, Cont% Jun-26 | RESTRICTED_RAW | Local only. `MRP In Lac` is unit-corrupt in Apr-26 and May-26. |
| fy27-dashboard-june26-validation-v2lual, pr16-container-recovery-gmba0k (#17 closed) | primary_article.csv, StoreChainMaster | RESTRICTED_RAW | Never import. |
| tock-filter-dashboard-djaiw4 (#11), dashboard-q1-forecast-promo (#3), safe-powerbi-dashboard-rulings, feature/sprint9-alerts-jbp-anomalies | various | SUPERSEDED / low value | No action. |

Other findings:
- Alias conflicts to settle: FSN, TRENDS, Azorte. Alias rows missing from `main`: MRL, FRANKROSS, Sasta Sunder, Baby Shop (none occur in current offtake files).
- `Primary_Article_Synthesized_FY25.csv` is estimated data. It is on the never-read list and is pinned by a test.

Decisions needed from the owner: #267 claim input (B3); #279 PO fill rate; the alias conflicts; ArticleMaster and EAN_Product_Master classification; whether SIS offtake is needed in Power BI; and I-2 (purge or contain tracked raw files).


## Pending items processed (2026-10-11)

| Item | Result |
|---|---|
| Aliases | Added 4 to query 11: MRL to More Retail, Frankross to Frank Ross, Sasta Sunder to SastaSundar, Baby Shop to Lifestyle Babyshop. New test checks every alias target exists in `ChainMaster.csv`. None of these four occur in the Apr to Aug-26 files today. |
| TRENDS | NOT changed. Query 11 maps it to "Trent" (Tata, Hypermarket). The branch record says the business owner confirmed it as "Reliance Trends" (2026-07-22). Rows today: 4,122 in Jun-26 and 921 in Aug-26, NSV under 15 L raw. Changing it needs a Chain Master member, and the step that groups any chain containing "reliance" would fold it into Reliance Retail. Owner to say which treatment is right. |
| FSN | Kept as "Nykaa (FSN)" (eB2B decision). Branch name "Nykaa SS(fsn)" is the same chain under another label. |
| Azorte | Already mapped. The long form "Reliance Retail-(Azorte)" is not added: the "reliance" grouping step would send it to Reliance Retail. Not in current files. |
| Claim input (#267) | 32-row file restored locally and read. Q1 aggregate only, chain labels differ from Chain Master (for example DMart vs D-Mart), and it may overlap the 64 rows in `PL_Expense_Input.csv` (FM-14). Not loaded into the model. B3 stays with Finance. |
| SIS offtake | Not imported. Restricted, and `MRP In Lac` is unit-corrupt in Apr and May-26. |
| TDP | Still missing: `PowerBI/RawDataFolders/TDP_Monthly/` holds only the template. |
| B5 | Unchanged: `BLOCKED_PENDING_DESKTOP_EVIDENCE`. Run `scripts/B5-DesktopRunner.ps1` per `docs/evidence/B5_RUNNER.md`. |

## TRENDS and TDP focus list (2026-10-11)

- **TRENDS** now maps to "Reliance Trends" (new `ChainMaster.csv` row: Account Reliance, Fashion Retail, MT). The "reliance" grouping step in query 11 skips it, so it is not folded into Reliance Retail or Reliance Brand Counter. The HTML dashboard still groups TRENDS under "Trent/Westside" (`scripts/build_dashboard_data.py`, line 354). It needs a data.js rebuild to change, so it is left for a separate decision.
- **TDP focus list** (`scripts/build_tdp_focus_articles.py`, registry entry `tdp_focus_articles`): per chain and brand, the articles that make 95% of FY27 YTD offtake NSV, plus articles first sold from Jan-26. Result: 101 chain-brand pairs, 2,075 rows (1,923 top-95%, 152 new only), covering 95.71% of NSV. Offtake ex Brand Counter ties to 18,971.68 L. 219 articles are new since Jan-26; 144 of them are first seen in offtake, which starts Apr-26, so they are marked "Offtake only: confirm with owner".
- This list is not Nielsen TDP. It has no ACV % or weighted distribution, so it is not loaded into Fact TDP and pages 1, 7, 9, 10 and 11 keep their banner until a real TDP file arrives.

## NPI by offtake, TDP focus list on both dashboards, B5 options (2026-10-11)

- **NPI from offtake only.** In `scripts/build_tdp_focus_articles.py`, an article counts as new to a chain when that chain had offtake in Apr-26 (the baseline month) but none for that article, and the article first shows there from May-26. Chains with no Apr-26 offtake are skipped, otherwise every article would look new. Result: 2,338 focus rows (1,923 top-95%, 415 new/NPI only), 95.82% of FY27 YTD NSV; 454 articles in the new list (75 confirmed new against primary from Apr-25, 418 new to at least one chain). 80 offtake-only articles were already in every baseline they appear in, so they are left out. Offtake before Apr-26 is not in the repo, so "baseline" means Apr-26 only.
- **HTML dashboard.** Inventory & Supply Health > TDP & Distribution has an "Article focus list" section (chain, brand and list filters, CSV download), fed by `dashboard/tdp_focus.js`. Browser check: `tests/tdp_focus_browser.js`.
- **Power BI.** New query 63 (`Fact TDP Focus Articles`), DAX 21 (8 measures), page 10 shows four focus cards, a chain bar and an article table. Page 10 stays NO_SOURCE for the real TDP measures. Not opened in Desktop.
- **B5.** Options are in `docs/evidence/B5_ALTERNATIVES.md`. B5 stays `BLOCKED_PENDING_DESKTOP_EVIDENCE`.

## B5 on Power BI Service (2026-10-11)

Owner accepted the ExecuteQueries route for B5. Added `scripts/b5_execute_queries.py` and a Service mode in `scripts/b5_evidence.py` (source `powerbi_service_execute_queries`: requires workspace and dataset ids, a Completed last refresh, and the published SHA equal to the repo SHA). 10 tests with a fake HTTP layer. Not run against a real workspace. B5 stays `BLOCKED_PENDING_DESKTOP_EVIDENCE` until a run produces the evidence file and the screenshots are attached. The model must first be published and refreshed in a workspace: see `docs/evidence/B5_ALTERNATIVES.md`.

## B5 on a Pro-only tenant (2026-10-11)

Research and decision recorded in `docs/evidence/B5_ALTERNATIVES.md`; one-page steps in `docs/evidence/B5_DESKTOP_QUICKSTART.md`. Desktop runner first; SharePoint + one publish as the fallback (not built). B5 stays `BLOCKED_PENDING_DESKTOP_EVIDENCE`.

## Deep-dive QC fixes (2026-10-11)

Fixed: (1) the TDP focus list now uses the same Reliance grouping as query 11 ("Reliance Retail"), so every chain except Centro is in `ChainMaster.csv` (test added); (2) the HTML focus list also shows when a real TDP file is loaded; (3) QuickSetup no longer leaves out Promo (query 46, DAX 15; its steps now list the two relationships); (4) `PROJECT_STATE.md` counts refreshed.

Open (TRENDS itself fixed later the same day, see below): the HTML dashboard uses its own chain names (DMart, Metro C&C, VMM) while Power BI uses D-Mart, Metro CNC, Vishal Mega Mart. Changing it needs a `data.js` rebuild from the offtake workbook, which is not in the repo. D-Mart names should be aligned in that same rebuild.

Reviewer findings fixed (2026-10-11): Service evidence now needs `--expect-sha` and `--refreshed`, a refresh that ended within 48 h, SHAs of 7+ characters, and recorded queries for every result; a run with failed queries writes no evidence file (so a same-day re-run is not blocked). The focus script now fixes BBLUNT to BBlunt (as queries 11 and 16 do), reads scientific-notation EANs with a warning, and warns about rows with no EAN. Left as is: a missing-EAN fallback to article code (none in current data), pandas 2.2+ requirement (pinned at 3.0.5).


## TRENDS now "Reliance Trends" in the HTML dashboard too (2026-10-11)

`scripts/build_dashboard_data.py` maps "trends" to "Reliance Trends" and has a `CHAIN_RENAMES` step so `--offtake-patch` moves rows already stored under "Trent/Westside" instead of keeping both. `data.js` was rebuilt from the tracked monthly offtake CSVs (the workbook is not needed for FY27). A control run with no code change reproduced the committed `data.js` byte for byte; after the change the only differences are the renamed chain (`offtake.by_chain`, `offtake.pos_stores.fy27.by_chain`, `primary_offtake_gap.fy27.by_chain.offtake_only`). FY26 31,119.87 L and FY27 18,971.69 L are unchanged. "Reliance Trends" is excluded from the Reliance offtake sum used for the Brand Counter check.

New finding, not fixed: recomputing `primary_offtake_gap` from the stored blocks gives different FY26 and FY27 numbers (for example FY26 Apr primary 3,174.60 vs 2,920.73 L). The stored block was built before the MT-basis restatement. It needs a primary refresh by the owner, not a patch. The chain names there (DMart, Metro C&C, VMM) also still differ from Power BI.

Governance note: the GOV-005 approved-exception list (`scripts/canonical/governance.py`) named this chain "Trent/Westside". It now says "Reliance Trends" (same chain, same root cause; approval fields unchanged) and the matching test list was updated. The owner should be aware that a governed list was touched for the rename.
