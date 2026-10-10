# Tabular Editor Automation Scripts

These C# scripts automate the Power BI model build for the MT Dashboard.
Instead of pasting ~480 measures one at a time (2-3 hours), run these
4 scripts in order (~10 minutes total).

## Pre-requisites

1. **Power BI Desktop** (June 2025+) on Windows
2. **Tabular Editor 3** (or free TE2) — download from sqlbi.com/tools/tabular-editor
3. **DAX Studio** (free) — download from daxstudio.org
4. Clone this repo to a fixed path (e.g. `C:\MT-Dashboard`)

## Build steps

### Before running scripts

1. Create a new PBIX: Power BI Desktop → New report → Save as `MT_Dashboard.pbix`
2. Set `pRootFolder` parameter: Home → Transform data → Manage Parameters →
   New → `pRootFolder` = `C:\MT-Dashboard\PowerBI`
3. Paste all 46 PQ queries from `QuickSetup/AllPowerQuery_Consolidated.txt`
   (in order, via Advanced Editor) → Close & Apply
4. Create the Date Table: Modeling → New Table → paste entire `DAX/00_DateTable.dax`
   → Mark as date table on `[Date]` column

### Run scripts (in Tabular Editor)

Open Tabular Editor from Power BI's **External Tools** ribbon, then:

| # | Script | What it does | Time |
|---|--------|-------------|------|
| 1 | `01_Create_Relationships.cs` | Creates all relationships from DataModel.md | ~1 min |
| 2 | `02_Import_Measures.cs` | Reads all .dax files, creates ~480 measures | ~2 min |
| 3 | `03_Create_Hierarchies.cs` | Creates 4 drill hierarchies + sort orders | ~30 sec |
| 4 | `04_Validate_Model.cs` | Checks everything is connected, reports issues | ~30 sec |

**How to run:** In Tabular Editor → C# Script tab (or Advanced Scripting) →
paste the script → Run (F5 or play button). Check the output messages.
After all 4 scripts, press **Ctrl+S** in Tabular Editor to save back to Power BI.

### After scripts

1. **Calculated columns** (manual — Script 02 flags these):
   - `Fact Offtake Sales[Offtake Channel]` — from `10_SIS_Reconciliation.dax`
   - `Fact Primary Article[TOT Method]`, `[TOT Pass-on Value]` — from `12_TOT_Measures.dax`
   - `PL Expense Input[Resolved Chain/Brand/Category/Bad Brand Or Category]` — from `13_CM2_Measures.dax`
   - Add via: right-click table → New Calculated Column → paste DAX
2. **Theme:** View → Themes → Browse → `PowerBI/theme/HonasaMT_Theme.json`
3. **Validate in DAX Studio:** Open DAX Studio → run queries from `05_DAXStudio_Validation.dax`
4. **Build 18 pages** per `PowerBI/docs/PageLayouts.md`
5. **Save as** `MT_Leadership_Dashboard.pbix`

## Important: change the path

In `02_Import_Measures.cs`, line 18, change:
```csharp
var daxFolder = @"C:\MT-Dashboard\PowerBI\DAX";
```
to match your local repo location.

## File list

| File | Purpose |
|------|---------|
| `01_Create_Relationships.cs` | C# — creates all star-schema relationships |
| `02_Import_Measures.cs` | C# — batch-imports ~480 DAX measures from files |
| `03_Create_Hierarchies.cs` | C# — creates 4 drill hierarchies + sort orders |
| `04_Validate_Model.cs` | C# — validates the model is complete |
| `05_DAXStudio_Validation.dax` | DAX queries — run in DAX Studio to verify data |
| `README.md` | This file |
