# Power BI: dynamic dashboard design and Windows build checklist

A `.pbix` can only be produced in Power BI Desktop (Windows). Everything below is ready to follow; nothing here has been run inside Desktop yet. Evidence for closing
blocker B5 goes in `docs/evidence/B5_RUN_SHEET.md`. The picture in `docs/images/powerbi_dynamic_preview_*.png` is a design preview drawn from the repo's real numbers, not a Power BI screenshot.

## 1. What "dynamic" means here
One chart answers several questions, and every drill step shows 2 to 3 insights from different heads.

| Head | Question it answers | Measures |
|---|---|---|
| SALES | How big, and moving which way? | `Total MT NSV`, `MoM Growth %`, `YoY Growth %`, `Drill NSV Cr` |
| MIX | How much of the whole, and who carries the growth? | `Drill Share Of Selection %`, `Drill Share Of Growth %`, `Chain Share of NSV %` |
| PRICE | Do we earn more or less per unit? | `MT ASP`, `MT Realisation %`, `Zone Price Index`, Nielsen `Cut Price Index` |
| REACH | How many stores, and how productive? | `Drill Stores Selling`, `Universe Availability %`, Nielsen `Cut WD %` |
| SHARE | Are we winning in the market and inside the chain? | `Market Share %`, `Cut Value Share %`, `Account Share %` |

## 2. Controls that make one chart do the work of many
1. **Measure picker** (field parameter): the chart's value switches between NSV, Units, ASP, Realisation, YoY %, MoM %, Share of selection, Stores selling.
2. **Dimension picker** (field parameter): the chart's axis switches between Zone, Chain, Brand, Category, Pack size (and Month for a trend).
3. **Hierarchies** for drill down and up (right-click a bar, Drill down; or the arrows at the chart corner):
   Geography `Zone > State > City > Store`, Product `Category > Sub-category > Brand > Range > Pack size > Article`, Chain `Chain > Store`, Time `FY > Quarter > Month`.
   (`DataModel.md` lists them; add City from `Store City Master[City Final]` to the Geography one.)
4. **Tooltip page** (one per level family): hover a bar and see three heads (Sales, Mix, Price or Reach) in one card, using the `Drill Head ...` text measures plus a small chart.
5. **Drill-through pages** (right-click a store, chain or brand, Drill through): Store detail, Chain detail, Brand detail. Each has the same three blocks: Sales trend, Mix / share, Price and reach.
6. **Decomposition tree** on the Executive page: pick `Total MT NSV`, then Chain, Zone, Brand in any order to see why the number moved.
7. **Bookmarks and buttons**: Offtake / Primary / Nielsen view, Facewash / Shampoo, "show Brand Counter" toggle (Reliance Brand Counter stays out of the offtake total by default).
8. **Synced slicers** on every page: FY, Month, Chain, Zone, Category (Format > Sync slicers).

## 3. Pages (tab order)
| # | Page | Main visual (drill / pickers) | What a drill step reveals |
|---|---|---|---|
| 1 | Executive Cockpit | KPI cards, trend bar + line (Time hierarchy), decomposition tree | Month > Zone > Chain: Sales, Mix, Price in the tooltip |
| 2 | Chain Performance | Bar by chain with both pickers; matrix Chain > Store | Store: reach, ASP, Brand Counter vs non-counter |
| 3 | Zone and State | Map or bar on Geography hierarchy | Zone > State > City > Store: sales, share of zone, stores selling |
| 4 | Brand and Category | Treemap on Product hierarchy | Category > Sub-category > Brand > Range > Pack: sales, mix, ASP, packs not sold |
| 5 | Nielsen Cuts | Share trend, brand cut table, pack presence (page 9 spec) | Brand: price index, WD, ND, SAH, headroom |
| 6 | Chain Share and Plan | Share inside Lulu, More, Wellness, Reliance; white space table | Category by zone and state: account vs ours |
| 7 | Stores and Beats | Visit cities, Store City Master, store count | City > store: NSV, last-year NSV, YoY |
| 8 | Data Quality | Totals tie, duplicates, month coverage | each check with its count |
| 9 | State, Pack Size and Store Type (preview file 7) | State bars split LFL / NFL; chain table; pack bar + MoM | State > City > Store: LFL growth, new stores, lost stores |
| T1-T3 | Tooltip pages | 3 text heads + mini chart | hover only |
| D1-D3 | Drill-through: Store, Chain, Brand | Sales trend, Mix, Price and reach | right-click, Drill through |

Details of every visual are in `PowerBI/docs/PageLayouts.md` (pages 1 to 12); this file adds the drill layer on top.

## 4. Build checklist (one Windows session, about 2 to 3 hours)
Tick each line; the right-hand column says what to see before moving on.

**A. Prepare**
- [ ] Power BI Desktop (current monthly release). Copy the `PowerBI/` folder to `C:\MT-Dashboard`. | folder has `PowerQuery`, `DAX`, `SeedData`, `RawDataFolders`
- [ ] Copy the Nielsen seed files from `SeedData\Nielsen\<folder>` into `RawDataFolders\<same folder name>` (four folders, including `Nielsen_Brand_Cut_Monthly`). | each drop folder has one `*_aug26.csv`
- [ ] Optional, for store-level year on year: put the cleaned FY26 monthly files (`offtake_store_article_<Mon>_25.csv` and `_26.csv` for Jan to Mar) in `RawDataFolders\Offtake_Monthly`. | folder shows 12 + 5 monthly files

**B. Load**
- [ ] Parameter `pRootFolder` = `C:\MT-Dashboard` (STEP 01). | no error
- [ ] Paste queries STEP 02 to STEP 41 in order from `QuickSetup\AllPowerQuery_Consolidated.txt`, renaming each as shown. | no query shows a red error; if one does, stop and note which
- [ ] Close and Apply. | row counts: Fact Offtake Sales above 200k rows per month file; Store City Master about 12,100; Fact Account Category about 1,900; Fact Nielsen Brand Cut about 1,650

**C. Model**
- [ ] Date table from STEP 01 of `AllDAX_Consolidated.txt`, mark as date table on `[Date]`. | Month sorts Apr to Mar
- [ ] Relationships per `PowerBI/docs/DataModel.md` (one active path per pair). | Model view shows no ambiguity warning
- [ ] Create the 4 hierarchies (section 2, item 3) and set the sort-by columns. | arrows appear on a test bar chart

**D. Measures**
- [ ] `_Measures` table, then STEP 02 to STEP 19 of `AllDAX_Consolidated.txt` (skip the 6 flagged calculated columns, add them on their own tables). | no measure shows an error; the new `Drill ...` ones return a value on a card
- [ ] Add the calculated column `Match Key` to `Fact Offtake Sales` using the formula at the top of query 56. | `[Visit Master Match %]` close to 100%

**E. Field parameters**
- [ ] Modeling > New parameter > Fields. Name `Measure Picker`; add: `Total MT NSV`, `MT Offtake Qty`, `MT ASP`, `MT Realisation %`, `YoY Growth %`, `MoM Growth %`, `Drill Share Of Selection %`, `Drill Stores Selling`. Tick "Add slicer". | slicer lists the 8 names
- [ ] New parameter > Fields. Name `Dimension Picker`; add: `Chain Master[Chain]`, `Zone State Master[Zone]`, `Brand Master[Brand]`, `Category Master[Category]`, `Article Master[Pack Size]`. Tick "Add slicer". | slicer lists the 5 names
- [ ] Put `Measure Picker` on the chart value and `Dimension Picker` on the axis. | picking a name changes the chart

**F. Pages**
- [ ] Theme: View > Themes > Browse > `theme\HonasaMT_Theme.json`.
- [ ] Build pages 1 to 9 from section 3 and `PageLayouts.md`. Use the hierarchy (not the bare field) on the axis. | drill arrows at the chart corner
- [ ] Sync slicers FY, Month, Chain, Zone, Category across pages.
- [ ] Edit interactions: the decomposition tree and KPI cards should not filter the trend chart.

**G. Tooltips and drill-through**
- [ ] Add pages T1 to T3 (Page size: Tooltip). Each: three card visuals with `Drill Head Sales`, `Drill Head Mix`, `Drill Head Price` (T3 uses `Drill Head Reach`) and one small trend. Page information > Allow use as tooltip. | hover shows the 3 lines
- [ ] On each main chart: Format > General > Tooltips > Type: Report page, choose T1/T2/T3.
- [ ] Add D1 Store, D2 Chain, D3 Brand. Put the drill-through field in the Drill-through well (`Store City Master[Store Key]`, `Chain Master[Chain]`, `Brand Master[Brand]`). Three blocks each: Sales trend, Mix, Price and reach. | right-click a bar shows Drill through

**H. Bookmarks**
- [ ] Bookmarks and buttons for Offtake / Primary / Nielsen and Facewash / Shampoo. | the button switches the visible visual

**I. Verify and save**
- [ ] Run `docs/evidence/B5_RUN_SHEET.md` (FY parser, CM2 cases, rolling averages) and fill `docs/evidence/B5_EVIDENCE_TEMPLATE.md` as `B5_powerbi_runtime_<date>.md`.
- [ ] Tie-outs: FY27 offtake Apr to Aug = 18,971.69 L (Rs 189.72 Cr); FY26 offtake = 31,119.87 L; Reliance Brand Counter excluded from the MT total.
- [ ] Save as `MT_Leadership_Dashboard.pbix`.

## 5. Not done yet (needs Desktop)
Everything in sections 2 to 4 inside Power BI. The queries, measures, seeds and this checklist are in the repo and tested for structure only.

## Design previews (look only, not Power BI screenshots)

Drawn by `scripts/render_powerbi_preview.py` from the repo's real numbers.
Files: `docs/images/powerbi_preview_1_cockpit`, `2_brand_drillthrough`, `3_chain`,
`4_zone_state`, `5_nielsen`, `6_chain_share` (.html and .png).
Rebuild: `python scripts/render_powerbi_preview.py`.

Page 7 `7_state_pack_lfl`: State cut, pack size, LFL / NFL stores. Data from
`python scripts/build_store_cuts.py` -> `data/store_cuts_aug26.json`.
LFL = sold this year and in the same months last year; NFL = no sales last year; Lost = sold last year, nothing this year.
Reliance Retail non-counter is kept out of LFL (last year is state-level only). Pack size is FY27 only (last year has no pack in the store-month file).

### Page 7 in Power BI Desktop (tick-box)
- [ ] Copy `PowerBI/SeedData/Store_Cuts/*.csv` into `RawDataFolders/Store_Cuts`.
- [ ] Paste PQ 58 (`Fact Store Type`) and PQ 59 (`Fact Pack Size`); relate `Fact Pack Size[MonthStart]` to `Date Table[MonthStart]`.
- [ ] Paste DAX 20 into `_Measures`.
- [ ] Visuals: stacked column State x (LFL NSV Cr, NFL NSV Cr, No LY Store Data NSV Cr) + line LFL Growth %; table Chain x LFL Stores, NFL Stores, LFL NSV Cr, LFL Growth %, Lost Stores; column Pack x Pack Share % + line Pack MoM % (sort by `Pack Sort`); insight cards `Store Type Insight` and `Pack Insight`.
- [ ] Store type table does not follow the Date slicer (fixed period Apr-Aug FY27 vs same months last year). Put the period in the page title.
- [ ] Check: sum of Store Type NSV This Year Cr = 189.72 Cr (FY27 Apr-Aug); LFL NSV Cr = 127.0; Reliance Retail shows no LFL.
Monthly refresh: run `python scripts/build_store_cuts.py`, copy both CSVs to `RawDataFolders/Store_Cuts`, Refresh.

NFL is split in two (column `NFL Kind`): **New** = no sales anywhere last year; **Restarted** = sold last year in another month (Sep-Mar). Apr-Aug FY27: 1,463 new stores (Rs 4.9 Cr), 1,265 restarted (Rs 10.7 Cr). Measures: `New Stores`, `Restarted Stores`, `New Stores NSV Cr`, `Restarted Stores NSV Cr`.

Store-level growth rule: shown only for stores with 3 or more months of sales last year (`LY Months Sold`, `Growth Basis` = Enough history / Thin history). Apr-Aug FY27: 8,284 LFL stores qualify, 365 are left out. Use `Store Growth % (3+ months)` and `LFL Growth % (3+ months)` on store lists and rankings (`Pan India` online accounts are not shown as stores in the web movers list). Web dashboard: "Biggest store movers" card.

### Zone, brand, sub-category sales and the in-house distribution view
- Queries 60 (`Fact Sales Cuts`) and 61 (`Fact Inhouse Distribution`), measures at the end of DAX 20 (`Cut NSV Cr`, `Cut Share %`, `Cut LFL NSV Cr`, `Cut MoM %`, `Inhouse ...`). Seeds: `sales_cuts_fy27.csv`, `inhouse_distribution_fy27.csv` in `SeedData/Store_Cuts` (copy to `RawDataFolders/Store_Cuts`).
- Page 9 gets three more visuals: zone table (NSV, share, LFL, YoY, MoM), brand table and sub-category table. Brand and sub-category have no last-year figure (the FY26 store file has none), so no YoY there. Zone YoY uses the main offtake fact.
- TDP page: `Fact Inhouse Distribution` is "From our offtake, not TDP". Filter `Level` to one value on every visual. Swap to `Fact TDP` (query 14) when the real file arrives.

## Design previews: all 15 pages (look only, not Power BI screenshots)
Drawn from the repo's real numbers. Rebuild: `python scripts/render_powerbi_preview_rest.py` (it also runs `render_powerbi_preview.py`), then take screenshots of the HTML files.

| Plan page | Preview file (docs/images) |
|---|---|
| 1 Executive Cockpit | `powerbi_preview_1_cockpit` |
| 2 Chain Performance | `powerbi_preview_3_chain` |
| 3 Zone and State | `powerbi_preview_4_zone_state` |
| 4 Brand and Category | `powerbi_preview_8_brand_category` |
| 5 Nielsen Cuts | `powerbi_preview_5_nielsen` |
| 6 Chain Share and Plan | `powerbi_preview_6_chain_share` |
| 7 Stores and Beats | `powerbi_preview_9_stores_beats` |
| 8 Data Quality | `powerbi_preview_10_data_quality` |
| 9 State, Pack Size and Store Type | `powerbi_preview_7_state_pack_lfl` |
| T1, T2, T3 Tooltips (one image) | `powerbi_preview_11_tooltips` |
| D1 Drill-through Store | `powerbi_preview_12_drill_store` |
| D2 Drill-through Chain | `powerbi_preview_13_drill_chain` |
| D3 Drill-through Brand | `powerbi_preview_2_brand_drillthrough` |
