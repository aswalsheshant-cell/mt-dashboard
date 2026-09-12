# Power BI PBIX Build Guide

**Version:** MVP 1.0  
**Date:** 2026-08-06  
**Estimated build time:** 2–3 hours (one-time; subsequent refreshes are automated)

This guide walks a Power BI Desktop user through assembling the `.pbix` from the
checked-in build kit. The kit (PQ queries, DAX measures, seed data, theme) is fully
committed; only the GUI assembly step requires Power BI Desktop.

---

## Prerequisites

- Power BI Desktop (June 2025 or later)
- Access to the `PowerBI/` folder from this repository
- The `pRootFolder` parameter must point to the absolute path of the `PowerBI/` folder
  on the machine running the report (e.g. `C:\Users\YourName\mt-dashboard\PowerBI`)

---

## Step 1 — Create a new Power BI Desktop file

Open Power BI Desktop → **New report** → save as `MT_Dashboard_MVP.pbix` in
`PowerBI/` (the file is gitignored; do not commit it).

---

## Step 2 — Set the root folder parameter

1. Home → **Transform data** → **Manage parameters**
2. Create a parameter named `pRootFolder` (Text, required, no default)
3. Set the current value to the absolute path of the `PowerBI/` folder

---

## Step 3 — Paste Power Query queries

Open Power Query Editor and paste each `.pq` file from `PowerBI/PowerQuery/`
via **Advanced Editor**. Create queries in numerical order (01 → 41) so
dependencies resolve correctly.

Use the **QuickSetup** reference files for a faster paste-in experience:
- `PowerBI/QuickSetup/AllPowerQueryQueries.txt` — all PQ in one document
- `PowerBI/QuickSetup/AllDAXMeasures.txt` — all DAX in one document

**Key queries and their sources:**

| Query | Source | Notes |
|-------|--------|-------|
| 01–09 | Various masters in `SeedData/` | Load seed CSVs |
| 10 | `RawDataFolders/Primary_Weekly/` | Empty for MVP; 0 rows |
| 16 | `RawDataFolders/Primary_Article_Monthly/` | Main primary fact with DIST allocation |
| 41 | ShipTo CSV + Approved Patch | **REBUILT** — no XLSX dependency |
| Others | See individual `.pq` headers | — |

---

## Step 4 — Apply the theme

Design tab → **Browse for themes** → select `PowerBI/theme/MT_Dashboard_Theme.json`

---

## Step 5 — Paste DAX measures

In the report view, create a **Measures table** (Enter Data → blank table named
"Measures") then paste each `.dax` file from `PowerBI/DAX/` using the DAX editor.

Files in `PowerBI/DAX/`:
- `01_DateTable.dax` — date dimension
- `02_CoreSales.dax` — total NSV/Qty measures
- `03_GrowthMeasures.dax` — YoY, MoM
- `04_PnL.dax` — P&L measures
- `05_Offtake.dax` — offtake and TDP
- `06_DataQuality_Measures.dax` — DQ checks (updated: Primary Article QC added)
- `07_PrimaryAllocation_Measures.dax` — allocation NSV by source type (updated)
- `08_Distribution.dax` — distribution measures
- `09_ForecastMeasures.dax` — forecast vs target
- `10_CategoryPackMeasures.dax` — category/pack analysis
- `11_MarketShare.dax` — Nielsen measures (manual upload required)
- `12_PromoSpend.dax` — promo and trade spend
- `13_PerformanceComparison.dax` — ranking and comparison
- `14_InsightsWayForward.dax` — exception detection

---

## Step 6 — Load raw data files

Drop source files into the appropriate `RawDataFolders/` subfolders:

| Subfolder | What goes here |
|-----------|----------------|
| `Primary_Article_Monthly/` | Monthly CSVs from `split_primary_article_xlsb.py` |
| `Primary_ShipTo_Monthly/` | `Primary_ShipTo_FY25-26_to_May26.csv` (already present) |
| `Offtake_Monthly/` | Monthly offtake CSVs from `split_offtake_xlsb.py` |
| `Primary_Weekly/` | Weekly primary files (deferred — not required for MVP) |
| `Nielsen/` | Nielsen RMS upload (deferred — see `Nielsen_Source_Requirement.md`) |

---

## Step 7 — Refresh and validate

1. Click **Refresh all** in Power BI Desktop
2. Check the Data Quality page — target: `Data Health %` > 90%
3. Verify `Dist Allocation Coverage %` > 95%
4. If Jun'26 Provisional rows appear: expected behaviour — see `Jun26_Provisional_Allocation.md`
5. Confirm no "Unmapped Chain" rows exist (or document the cause if they do)

---

## Step 8 — Publish to Power BI Service (optional)

1. Home → **Publish** → select your workspace
2. Set scheduled refresh in the Service (requires an on-premises data gateway if files
   are local, or upload to SharePoint/OneDrive and use connector)
3. See `ServiceReadiness.md` for deployment checklist

---

## Allocation Source Transparency (QC Page)

After the build, add a table visual on the Data Quality page with:
- Rows: `Allocation Status`, `Source Type`
- Values: `Primary NSV (sum)`, row count
- Filter: `PO Type = Dist.`

This surfaces the breakdown of Approved / ShipTo CSV / Provisional / Unmapped
for any month selection.

---

## Known Deferred Items (not MVP blockers)

| Item | Status | Action required |
|------|--------|----------------|
| Weekly primary data | Empty folder | Drop files when available |
| Nielsen market share | Slide values only | Upload Nielsen RMS CSV |
| TDP (ACV-weighted) | Presence-based proxy in use | Business definition sign-off |
| Jun'26 DistCont approval | Provisional fallback active | Finance approval of patch |
