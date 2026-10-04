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
- [ ] Build pages 1 to 8 from section 3 and `PageLayouts.md`. Use the hierarchy (not the bare field) on the axis. | drill arrows at the chart corner
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
