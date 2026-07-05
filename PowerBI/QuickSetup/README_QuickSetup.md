# Power BI Quick Setup (15-30 min, one-time)

This folder exists to cut down file-hunting during the one-time build in
`PowerBI/README.md`. It does **not** replace that file — it's a faster way to
work through the same steps using two consolidated reference files instead of
opening 24+ separate `.pq`/`.dax` files one at a time.

> **No `.pbix`/`.pbit`/`.pbip` exists in this repo.** A `.pbix` can only be
> produced by the Power BI Desktop application (Windows GUI, not scriptable) —
> it can't be generated here. Everything that *can* be pre-built — every
> query, every measure, the data model, seed data, and now these consolidated
> references — is ready to paste in.

## What's in this folder

- **`AllPowerQuery_Consolidated.txt`** — all 25 Power Query steps, in the
  order to add them, each with the exact query name to rename it to.
- **`AllDAX_Consolidated.txt`** — all measures across the 13 DAX files (plus
  the Date Table), in order, with the 6 calculated-column exceptions flagged
  in a warning banner at the top so you see them before you start pasting.

Open one of these two files side-by-side with Power BI Desktop and work
top to bottom — that's the whole time-saving versus the full build kit.

## The steps (same order as `PowerBI/README.md`, condensed)

1. Copy the whole `PowerBI/` folder to a fixed path (e.g. `C:\MT-Dashboard`).
2. **Parameter:** Home ▸ Manage Parameters ▸ New ▸ `pRootFolder` ▸ your path.
   (STEP 01 in `AllPowerQuery_Consolidated.txt`.)
3. **Queries:** for STEP 02 through STEP 25 in that file — New Blank Query ▸
   Advanced Editor ▸ paste ▸ OK ▸ rename to the name shown ▸ next step.
   A few steps (20, 24) contain more than one query — each `---------- X
   ----------` block is its own complete query.
4. Close & Apply.
5. **Date table:** Modeling ▸ New table ▸ paste STEP 01 of
   `AllDAX_Consolidated.txt` whole ▸ mark as date table on `[Date]`.
6. **Relationships:** build per `PowerBI/docs/DataModel.md`.
7. **Measures:** create a `_Measures` table (Enter Data, one blank column,
   delete the column after). For STEP 02 through STEP 14 in
   `AllDAX_Consolidated.txt` — New Measure ▸ paste ONE `Name = Expression`
   block (including any `VAR`/`RETURN` lines under it) ▸ Enter ▸ next measure.
   **Skip the 6 commented-out blocks flagged at the top of that file** — add
   those as calculated columns on their own table instead (also flagged).
8. **Theme:** View ▸ Themes ▸ Browse for themes ▸ `theme/HonasaMT_Theme.json`.
9. **Pages:** build the 18 pages per `PowerBI/docs/PageLayouts.md`.
10. **Save as** `MT_Leadership_Dashboard.pbix`. Done — monthly refresh from
    here on is `PowerBI/docs/RefreshGuide.md` (drop file ▸ Refresh).

## Latest data already linked

`PowerBI/RawDataFolders/Offtake_Monthly/` already has the real
`offtake_store_article_Apr_26.csv` and `..._May_26.csv` (FY27) alongside the
FY24-26 history, and `PowerBI/RawDataFolders/Primary_Article_Monthly/`
already has its own Apr/May'26 files — so the first refresh after setup
picks up FY27 automatically, no extra step needed.
