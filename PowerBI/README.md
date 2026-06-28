# Modern Trade (MT) Leadership Dashboard — Power BI Build Kit

A complete, self-service Power BI dashboard for Honasa Modern Trade reporting:
Primary & Offtake sales, Chain / Brand / Category / SKU / Zone performance,
Chain-wise P&L, Forecast, Nielsen Market Share, TDP (Total Distribution Points),
Raw Data Export, and Data Quality — refreshable every month by dropping a file
into a folder and clicking **Refresh**.

> **Why this is a build kit and not a finished `.pbix`:** a `.pbix` is a binary
> produced by the Power BI Desktop engine and can't be generated outside Desktop.
> Everything that *can* be pre-built is here and ready: all Power Query (M),
> every DAX measure, the date table, an importable theme, seed master tables
> built from your real data, monthly raw-data templates, the full model spec,
> and page-by-page layouts. Assembling visuals is a one-time GUI step in Desktop
> (~2-3 hrs following `docs/PageLayouts.md`). After that, monthly refresh is
> drop-file → Refresh, with **no rebuilding**.

---

## What's in here

```
PowerBI/
├─ README.md                  ← you are here (build order + checklist)
├─ docs/
│  ├─ RefreshGuide.md         ← the monthly refresh SOP (also becomes a report page)
│  ├─ DataModel.md            ← star schema, tables, relationships
│  ├─ DataDictionary.md       ← every standard column + which ones must not be renamed
│  └─ PageLayouts.md          ← all 18 pages: visuals, fields, slicers, positions
├─ theme/
│  └─ HonasaMT_Theme.json     ← View ▸ Themes ▸ Browse for themes (import this)
├─ PowerQuery/                ← paste each .pq into a new Blank Query (Advanced Editor)
│  ├─ 00_Parameters.pq        ← pRootFolder (the ONE thing each machine sets)
│  ├─ 01_fnCombineFolder.pq   ← folder-combine function (the refresh engine)
│  ├─ 10..15_Fact_*.pq        ← Primary, Offtake, P&L, Nielsen, TDP, Primary-ShipTo facts
│  ├─ 20_Dim_Masters.pq       ← Chain/Brand/Category/Article/Zone/Store/Nielsen masters
│  ├─ 21_ShipToMaster.pq      ← Ship-to party master
│  └─ 30..36_*.pq             ← Assumption, Targets, Store-SO map, Forecast override,
│                               Primary Allocation Map + Override, Sales Team Mapping
├─ DAX/
│  ├─ 00_DateTable.dax        ← calculated Date table (Indian FY)
│  └─ 01..08_*.dax            ← Core, P&L, Forecast (TY-target driven), Nielsen,
│                               TDP, Data-Quality, Ship-to Allocation, Forecast-QC
├─ SeedData/                  ← reference tables + targets + mapping (edit by hand)
│  ├─ Masters/*.csv           ← ChainMaster, BrandMaster, …, AssumptionTable, ForecastOverride
│  ├─ Targets/FY2627_Targets.csv
│  └─ Mapping/Store_SO_Mapping.csv
├─ RawDataFolders/            ← the watch folders you drop monthly files into
│  ├─ Primary_Weekly/         ← weekly primary files (MoM rolled up from weeks)
│  ├─ Offtake_Monthly/        ← monthly offtake files
│  ├─ Nielsen_Monthly/        ← monthly Nielsen market-share files
│  └─ TDP_Monthly/            ← monthly TDP / ACV files
└─ templates/                 ← blank templates with the exact fixed column headers
```

---

## One-time setup (do this once in Power BI Desktop)

1. **Copy the whole `PowerBI/` folder to a fixed path** on your machine or a
   shared/OneDrive drive, e.g. `C:\MT-Dashboard`. Everyone who refreshes uses
   the same layout; only the root path differs per machine.

2. **Create the parameter.** Power BI ▸ Home ▸ *Transform data* ▸ *Manage
   Parameters* ▸ New → name it `pRootFolder`, Type *Text*, value = your path
   (e.g. `C:\MT-Dashboard`). See `PowerQuery/00_Parameters.pq`.

3. **Add the folder-combine function.** *New Source ▸ Blank Query ▸ Advanced
   Editor*, paste `PowerQuery/01_fnCombineFolder.pq`, rename the query to
   **fnCombineFolder**.

4. **Add each table query.** For every `.pq` file in `PowerQuery/` (10–33):
   New Blank Query ▸ Advanced Editor ▸ paste ▸ rename to the name in the file's
   header comment (e.g. `Fact Offtake Sales`, `Chain Master`, `Targets`).
   `20_Dim_Masters.pq` contains several masters — split each commented block
   into its own query.

5. **Close & Apply.** Tables load from the seed CSVs + whatever files already
   sit in the watch folders.

6. **Create the Date table.** Modeling ▸ *New table* ▸ paste `DAX/00_DateTable.dax`.
   Then Table tools ▸ *Mark as date table* ▸ `[Date]`. Set the sort-by columns
   noted at the bottom of that file.

7. **Build relationships** per `docs/DataModel.md` (a clean star schema).

8. **Add measures.** Create a `_Measures` table (Enter Data, one dummy column,
   delete it later) and paste every measure from `DAX/01..06`. Group them into
   display folders matching the file names.

9. **Import the theme.** View ▸ Themes ▸ *Browse for themes* ▸
   `theme/HonasaMT_Theme.json`.

10. **Build the pages** following `docs/PageLayouts.md` (18 pages). Each page
    lists the visuals, the exact fields/measures, slicers, and placement.

11. **Save as `MT_Leadership_Dashboard.pbix`** in the root folder. Done.

After this, your monthly job is only steps in `docs/RefreshGuide.md`.

---

## Monthly refresh (the whole point)

1. Drop the new month's file into the right watch folder
   (`Offtake_Monthly`, weekly files into `Primary_Weekly`, etc.) — keep the
   template's column names unchanged.
2. Open the `.pbix` ▸ **Home ▸ Refresh**.
3. Check the **Data Quality Check** page (should be all green / zero issues).
4. Publish to Power BI Service if you share online.

Full SOP, including the "don't rename these columns" list and how to export raw
data, is in `docs/RefreshGuide.md` (and is reproduced as a page inside the report).

---

## Data maintenance guidance (as requested)

- **Primary Sales = weekly grain.** Keep one file per week (or a running file
  with a `Week Start Date` column) in `Primary_Weekly/`. The model rolls weeks
  up to month via the Date table, so MoM still works while you retain weekly
  detail.
- **Offtake Sales = monthly grain.** One file per month in `Offtake_Monthly/`.
- **Never overwrite history.** Add a *new* file each period; the folder-combine
  appends. To correct a month, replace just that month's file.
- **Masters change rarely** — edit the CSVs in `SeedData/Masters/` to add a new
  chain, brand, SKU, or to update P&L assumptions / forecast overrides. No
  dashboard rebuild needed.

## Ship-to party primary allocation (secondary-driven)

Primary is driven onto **Chains** using each ship-to party's **secondary /
offtake contribution %**, month-on-month — never a flat split.

- **Source:** `RawDataFolders/Primary_ShipTo_Monthly/` (history file seeded from
  Apr'25→May'26). Each row is Month × Ship-To × Chain × Brand with the primary
  NSV already allocated by `Cont%` (Direct = 100% to one chain; Distributor =
  split across the chains it serves).
- **Dynamic mapping table:** `Primary Allocation Map` (query 34) projects the
  month-wise `Cont%` so it updates itself every refresh. To override a split by
  hand, add a row to `SeedData/Masters/PrimaryAllocationOverride.csv` — DAX
  prefers the override. Nothing is hardcoded in any measure.
- **Article lead/lag:** `Ship-to Primary NSV (Active Articles)` keeps only
  articles with offtake in the **current or previous** month, so primary that
  moves a month before/after the secondary sale isn't dropped.
- **Page 2B — Ship-to Primary Allocation** visualises allocated primary vs
  offtake, the distributor→chain split, Direct/Distributor mix, and MoM movement.
- See `DAX/07_PrimaryAllocation_Measures.dax` and `docs/PageLayouts.md` (Page 2B).
