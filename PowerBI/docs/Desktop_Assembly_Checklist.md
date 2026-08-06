# Power BI Desktop — Step-by-Step Assembly Checklist

**Version:** 1.0 · **Date:** 2026-08-06  
**Prerequisite:** `PBIX_Build_Guide.md` (high-level guide)  
**This document:** Detailed operational checklist for the person doing the build  
**Estimated time:** 2–3 hours (first build); 20 minutes (subsequent monthly refreshes)

---

## Pre-Build Setup

- [ ] Confirm Windows machine (Power BI Desktop is Windows-only)
- [ ] Confirm Power BI Desktop version June 2025 or later (Help → About)
- [ ] Confirm repository branch: `claude/primary-pipeline-allocation-fy27-l9bdf6`
- [ ] Confirm latest commit: `2725b80`
- [ ] Confirm working tree is clean: `git status` → "nothing to commit"
- [ ] Note the absolute path of the `PowerBI/` folder, e.g.:
  `C:\Users\YourName\mt-dashboard\PowerBI`  (this is `pRootFolder`)

---

## Phase A — Create the PBIX

- [ ] Open Power BI Desktop → **New report**
- [ ] File → **Save as** → name: `MT_Automated_Performance_Dashboard_FY27.pbix`
- [ ] Save to: `PowerBI/` folder (the file is in `.gitignore` — will not be committed)
- [ ] If an existing PBIX is present:
  - [ ] Copy to `MT_Automated_Performance_Dashboard_FY27_backup_<date>.pbix`
  - [ ] Record file size and SHA256 of the backup
  - [ ] Open the original; do not overwrite until validation passes

---

## Phase B — Create the Root Parameter

- [ ] Home → **Transform data** → **Manage parameters**
- [ ] New parameter:
  - Name: `pRootFolder`
  - Type: `Text`
  - Required: yes
  - Current value: `<absolute path of PowerBI/ folder>`  ← no trailing backslash
- [ ] Click OK
- [ ] Close & Apply

---

## Phase C — Load Power Query (25 queries)

Open Power Query Editor (Home → Transform data).

Paste queries in **numerical order** (00 first, 41 last) via **Advanced Editor**.
Source: `PowerBI/QuickSetup/AllPowerQuery_Consolidated.txt`

**Critical order notes:**
- Q00 (Parameters) must be first — all others depend on `pRootFolder`
- Q01 (`fnCombineFolder`) must precede Q10, Q11, Q13, Q14, Q15, Q16
- Q40 (`CustCode_Chain_Map`) depends on Q16 — paste Q16 before Q40
- Q41 (`Dist Cont Weights`) must precede Q16 when Q16 references it
  *(Q41 is a helper consumed at query time; paste it before Q16)*

**For each query:**
- [ ] New query (Blank Query) → Advanced Editor → Paste → Done
- [ ] Rename to match the `.pq` filename (without extension)
- [ ] Verify no red error icons in the Preview pane

**Specific checks during paste:**

### Q41 — Dist Cont Weights
- [ ] Source 1 reads: `pRootFolder & "\SeedData\Mapping\DistCont_Patch_Approved_2026-07-04.csv"`
- [ ] Source 2 reads: `pRootFolder & "\RawDataFolders\Primary_ShipTo_Monthly\Primary_ShipTo_FY25-26_to_May26.csv"`
- [ ] No reference to any `.xlsx` file
- [ ] `Jun26Fallback` step exists
- [ ] `AddFrac` normalisation step exists
- [ ] Column `Provisional Flag` is present in output
- [ ] Column `Frac` is present in output
- [ ] Row count: approximately 2,083 rows expected

### Q16 — Fact Primary Article
- [ ] `ExpandedW` expands `Source Type`, `Approval Status`, `Provisional Flag`
- [ ] `FillSrcType`, `FillApproval`, `FillProv` steps exist after `FillFrac`
- [ ] `DistAllocStatus` step produces `Allocation Status` column
- [ ] `DirectWithGov` step produces Source Type / Provisional Flag / Allocation Status on Direct rows
- [ ] Column `Chain` is present (not `Chain Dash`)
- [ ] No `Chain Dash` column in the final output step
- [ ] Row count: approximately 206,000+ rows expected (expanded from 50,648 Dist rows + Direct rows)

### Q10 — Fact Primary Sales
- [ ] Comment: `// MVP DEFERRED — Weekly folder is empty`
- [ ] Returns 0 rows (expected — weekly folder is empty)
- [ ] No red error

### Q00 — Parameters
- [ ] `pRootFolder` parameter visible
- [ ] No hardcoded user-specific path

- [ ] **Close & Apply** — wait for all queries to complete loading
- [ ] Confirm: no yellow warning triangles on any query
- [ ] Confirm: no red error icons on any query

---

## Phase D — Create Calculated Columns (before DAX measures)

Two query-files produce **calculated columns** that must be added to their tables
*before* pasting the associated DAX measure files. Do these in the Report/Data view,
not Power Query:

### On `Fact Primary Article` (needed by `DAX/12_TOT_Measures.dax`):
- [ ] Table tools → **New column**: `TOT Method = ...`  (paste from `12_TOT_Measures.dax` setup note)
- [ ] **New column**: `TOT Pass-on Value = ...`  (paste from `12_TOT_Measures.dax` setup note)

### On `PL Expense Input` (needed by `DAX/13_CM2_Measures.dax`):
- Requires `CustCode_Chain_Map` to be loaded first
- [ ] **New column**: `Resolved Chain = ...`
- [ ] **New column**: `Resolved Brand = ...`
- [ ] **New column**: `Resolved Category = ...`
- [ ] **New column**: `Bad Brand Or Category = ...`

*(Full column expressions are at the top of each DAX file in a setup note.)*

---

## Phase E — Build the Data Model (star schema)

Model view (left rail → diagram icon):

**Mark Date Table:**
- [ ] Right-click `Date Table` → **Mark as date table** → `Date`

**Create all relationships** (from `DataModel.md`):

| From (1 side) | To (* side) |
|---------------|-------------|
| `Date Table[Date]` | `Fact Primary Sales[Week Start Date]` |
| `Date Table[MonthStart]` | `Fact Offtake Sales[MonthStart]` |
| `Date Table[MonthStart]` | `Fact P&L[MonthStart]` |
| `Date Table[MonthStart]` | `Fact Nielsen[MonthStart]` |
| `Date Table[MonthStart]` | `Fact TDP[MonthStart]` |
| `Date Table[MonthStart]` | `Targets[MonthStart]` |
| `Date Table[MonthStart]` | `Fact Primary ShipTo[MonthStartCalc]` |
| `Date Table[MonthStart]` | `Fact Primary Article[MonthStart]` |
| `Date Table[MonthStart]` | `PL Expense Input[MonthStart]` |
| `Chain Master[Chain]` | `Fact Offtake Sales[Chain]` |
| `Chain Master[Chain]` | `Fact Primary Sales[Chain]` |
| `Chain Master[Chain]` | `Fact P&L[Chain]` |
| `Chain Master[Chain]` | `Fact TDP[Chain]` |
| `Chain Master[Chain]` | `Fact Primary ShipTo[Chain]` |
| `Chain Master[Chain]` | `Fact Primary Article[Chain]` |
| `Brand Master[Brand]` | `Fact Offtake Sales[Brand]` |
| `Brand Master[Brand]` | `Fact Primary Sales[Brand]` |
| `Brand Master[Brand]` | `Fact P&L[Brand]` |
| `Brand Master[Brand]` | `Fact TDP[Brand]` |
| `Brand Master[Brand]` | `Fact Nielsen[Brand]` |
| `Brand Master[Brand]` | `Fact Primary ShipTo[Brand]` |
| `Brand Master[Brand]` | `Fact Primary Article[Brand]` |
| `Category Master[Category]` | `Fact Offtake Sales[Category]` |
| `Category Master[Category]` | `Fact Primary Sales[Category]` |
| `Category Master[Category]` | `Fact P&L[Category]` |
| `Category Master[Category]` | `Fact TDP[Category]` |
| `Category Master[Nielsen Category]` | `Fact Nielsen[Nielsen Category]` |
| `Category Master[Category]` | `Fact Primary Article[Category]` |
| `Article Master[Article Code]` | `Fact Offtake Sales[Article Code]` |
| `Article Master[Article Code]` | `Fact Primary Sales[Article Code]` |
| `Article Master[Article Code]` | `Fact TDP[Article Code]` |
| `Store Master[Store Code]` | `Fact Offtake Sales[Store Code]` |
| `Store Master[Store Code]` | `Fact Primary Sales[Store Code]` |
| `Store Master[Store Code]` | `Store SO Mapping[Store Code]` |
| `Zone State Master[Zone]` | `Fact Offtake Sales[Zone]` |
| `Ship-To Master[Ship To Name]` | `Fact Primary ShipTo[Ship To Name]` |

- [ ] Confirm: **no bidirectional** relationships (unless deliberately chosen and documented)
- [ ] Confirm: **no circular** relationships (Power BI will warn)
- [ ] Confirm: `GST Rate QC Table`, `GST Config`, `CustCode Chain Map` have **no relationships** (disconnected)
- [ ] Confirm: `Primary Allocation Map`, `Primary Allocation Override`, `Assumption Table`,
      `Forecast Override` have **no relationships** (disconnected — read by DAX only)

**Create hierarchies** (right-click field → Create Hierarchy):
- [ ] Geography: `Zone State Master` — Zone → State → Chain → Store
- [ ] Product: `Article Master` — Category → Sub-category → Brand → Article
- [ ] Product (pack): `Article Master` — Category → Brand → Pack Size → Article
- [ ] Time: `Date Table` — FY → Fiscal Quarter → Month

**Sort columns:**
- [ ] `Date Table[Month Year]` sort by `[Month Year Sort]`
- [ ] `Zone State Master[Zone]` sort by `[Zone Sort Order]`
- [ ] `Brand Master[Brand]` sort by `[Brand Sort Order]`

---

## Phase F — Apply the Theme

- [ ] View → **Browse for themes** → select `PowerBI/theme/HonasaMT_Theme.json`
  *(or `MT_Dashboard_Theme.json` — whichever is the current file in the theme folder)*
- [ ] Confirm theme applied (background, font, colours)

---

## Phase G — Load DAX Measures

Create a measures table:
- [ ] Home → Enter data → blank table → name `_Measures` → Load

Paste each DAX file's contents into the `_Measures` table via the DAX formula bar
or via Modeling → New measure. Use `PowerBI/QuickSetup/AllDAX_Consolidated.txt`
as the single reference.

**File order (paste all measures from each file, in order):**
- [ ] `00_DateTable.dax` — creates the `Date Table` calculated table first
- [ ] `01_CoreMeasures.dax`
- [ ] `02_PnL_Measures.dax`
- [ ] `03_Forecast_Measures.dax`
- [ ] `04_Nielsen_Measures.dax`
- [ ] `05_TDP_Measures.dax`
- [ ] `06_DataQuality_Measures.dax` ← includes Primary Article DQ + Negative Frac measures
- [ ] `07_PrimaryAllocation_Measures.dax` ← includes Dist NSV breakdown, Coverage %, Provisional flag
- [ ] `08_ForecastQC_Measures.dax`
- [ ] `09_ArticleAllocation_Eligibility.dax`
- [ ] `10_SIS_Reconciliation.dax`
- [ ] `11_ExportDisplay_Measures.dax`
- [ ] `12_TOT_Measures.dax` *(requires calculated columns from Phase D)*
- [ ] `13_CM2_Measures.dax` *(requires calculated columns from Phase D)*

**After loading:**
- [ ] Confirm: no DAX syntax errors (red underlines)
- [ ] Confirm: `Dist Allocation Coverage %` resolves (references `Fact Primary Article`)
- [ ] Confirm: `Has Provisional Allocation` returns the warning string
- [ ] Confirm: `Primary Negative Frac Flag` resolves
- [ ] Test: `[Primary Data Health %]` on a card visual — should be a number, not BLANK

---

## Phase H — Build Report Pages

Follow `PageLayouts.md` for the exact visuals, fields, and measures per page.

### Allocation-specific visuals (required for governance):

**On the Data Quality page (Page 12):**
- [ ] Card: `Has Provisional Allocation` — red if ⚠ warning
- [ ] Card: `Primary Provisional NSV` — shows ₹1,376 L approx.
- [ ] Card: `Primary Negative Frac Flag` — shows warning string if present
- [ ] Card: `Primary Negative Frac NSV` — shows −₹0.21 L approx.
- [ ] Card: `Unmapped Dist Rows` — target = 0
- [ ] Table: Allocation Status × count × NSV (filter: PO Type = Dist.)

**On the Distributor Allocation page (Page 2B or separate):**
- [ ] Columns: `Source Type`, `Allocation Status`, `Provisional Flag`, `Fallback Source Month`
- [ ] Governance banner (see Phase I)

**Executive Summary page:**
- [ ] Card: `Dist Allocation Coverage %` (target ≥ 95%)
- [ ] Card: `Has Provisional Allocation` (if active: amber banner)

---

## Phase I — Governance Banners

Add text boxes on the relevant pages with these exact messages:

### Jun'26 Provisional Allocation banner
*Apply to: Distributor Allocation page, Executive Summary if Provisional rows > 0*

> "Jun'26 distributor-to-chain allocation uses May'26 contribution splits where exact Jun'26
> approved contribution data is unavailable. The affected allocation (₹1,376 L / 21 distributors)
> remains provisional pending Finance approval."

Conditional format: amber background when `[Primary Provisional Alloc] > 0`.

### Negative Reversal banner
*Apply to: Data Quality page*

> "Primary data contains reversal or negative-contribution entries (−₹0.21 L across 157 rows).
> These entries are retained for reconciliation unless Finance approves a zero-floor treatment."

### Nielsen banner
*Apply to: Nielsen/Market Share page*

> "Nielsen automation is not active. Current Nielsen values are presentation extracts
> and are not a refreshable raw-data source."

### TDP banner
*Apply to: TDP/Distribution page*

> "TDP definition pending business sign-off. The current sales-presence proxy is not
> approved TDP and should not be used for external benchmarking."

### Weekly banner
*Apply to: Primary Sales page (Q10 data)*

> "Weekly reporting is deferred. Monthly primary data (Fact Primary Article) is used for
> the current monthly MVP dashboard."

---

## Phase J — Full Reconciliation Checks (in Desktop)

After Refresh all:

- [ ] Grand total Primary NSV matches source: ₹46,560.34 L (±0.01 L rounding tolerance)
- [ ] Dist NSV total: ₹15,756.23 L
- [ ] Allocated (approved): ₹14,379.59 L
- [ ] Provisional (Jun'26): ₹1,376.49 L
- [ ] Unmapped: ₹0.15 L
- [ ] Sum of above = Dist NSV total ✓
- [ ] Direct + Dist = Total Primary NSV ✓
- [ ] `[Dist Allocation Coverage %]` ≥ 99.99%
- [ ] `[Allocation Health Check]` = 0 (all frac groups sum to 1)
- [ ] `[Primary Negative Frac Rows]` = 157
- [ ] `[Primary Negative Frac NSV]` ≈ −₹0.21 L
- [ ] `[Unmapped Dist Rows]` = 3

---

## Phase K — Automation Tests

### Test A: New Primary Row
- [ ] Add one test row to any Primary Article CSV
- [ ] Refresh — row appears in the model
- [ ] Remove test row → Refresh → row disappears

### Test B: New Month File
- [ ] Copy `primary_article_Jun_26.csv` → rename to `primary_article_Jul_26.csv`
- [ ] Refresh — Jul'26 appears as a new month
- [ ] Fiscal sort: Jul'26 appears after Jun'26
- [ ] Remove the copy → Refresh → Jul'26 disappears

### Test C: Unmapped Distributor
- [ ] Add a row to the ShipTo CSV with a new Ship To Name not in Q41
- [ ] Refresh — `[Unmapped Dist Rows]` increases by the row count
- [ ] The row appears as "Unmapped Chain" — not silently dropped
- [ ] Remove the row → Refresh → unmapped count returns to baseline

### Test D: Provisional Mapping
- [ ] Confirm Jun'26 rows appear with `Provisional Flag = TRUE` in a table visual
- [ ] Filter to Jun'26 → `[Has Provisional Allocation]` shows warning string

### Test E: Schema Failure
- [ ] Create a copy of one Primary Article CSV with a mandatory column deleted
- [ ] Replace the original temporarily → Refresh → Power BI shows a specific error naming the column
- [ ] Restore the original → Refresh → model is clean

---

## Phase L — Save and Backup

- [ ] File → **Save**
- [ ] Copy PBIX to: `MT_Automated_Performance_Dashboard_FY27_validated_<date>.pbix`
- [ ] Record SHA256 checksum of validated PBIX
- [ ] Record file size of validated PBIX

---

## Phase M — Power BI Service (if access available)

- [ ] Home → **Publish** → select workspace
- [ ] Dataset → Settings → configure Gateway data source credentials
- [ ] Dataset → Settings → Scheduled refresh → configure schedule
- [ ] Run **Refresh now** → confirm success in Refresh history
- [ ] Workspace → **Create app** (optional)
- [ ] Record completion date

If Service access is unavailable: mark `SERVICE BLOCKED BY ACCESS` and document
requirements in `ServiceReadiness.md`.

---

## Completion Sign-Off

| Check | Confirmed by | Date |
|-------|-------------|------|
| PBIX created and refreshed | | |
| All 25 PQ queries load without error | | |
| Star schema relationships confirmed | | |
| All DAX measures load without error | | |
| Reconciliation variance = 0 | | |
| Governance banners visible | | |
| Automation tests A–E passed | | |
| PBIX backup created with checksum | | |
| Power BI Service published | | |
| Finance Approval Decision Log updated | | |
