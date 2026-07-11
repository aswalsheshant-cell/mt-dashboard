# Build Guide: Creating Safe Offtake Blocks in Power BI Desktop

**Branch:** claude/safe-powerbi-dashboard-rulings  
**Target:** Power BI Desktop 2024.11 or later  
**Generated:** 2026-07-11  
**Version:** 3 (NSV unit confirmed; all NSV conversions included)  
**Status:** Step-by-step implementation guide (updated for NSV Lakhs → Crore conversion)

---

## Prerequisites

- Power BI Desktop installed (2024.11+)
- Access to monthly offtake CSV files (Apr'24–Jun'26, 582 files)
- Copy of all safe-blocks specification files:
  - `PowerQuery_Safe_Offtake.pq`
  - `DAX_Safe_Measures.dax`
  - `PowerBI_Model_Spec.md`
  - `PowerBI_Report_Page_Spec.md`

---

## Phase 1: Create Data Model (30–45 minutes)

### Step 1.1: Set Up Power Query Data Source

1. **Open Power BI Desktop** → New Project
2. **Get Data** → Folder
3. **Browse** to folder containing monthly offtake CSV files (e.g., `C:\Data\MT_Offtake_Monthly\`)
4. **Load** → Select all CSV files
5. **Transform Data** (in Power Query Editor)

### Step 1.2: Load & Transform Data

1. **Create Base Query:** Copy the content of `PowerQuery_Safe_Offtake.pq` → **New Query** → **Advanced Editor** → Paste
2. **Name this query:** `Offtake_Safe`
3. **Apply transformations** (as specified in PQ file):
   - Rename columns (Site_Code, Site_Name, Chain_Name, Zone, etc.)
   - Clean text fields (trim, proper case for Zone)
   - Convert numeric types (Sales_Qty, MRP_Sales_Value)
   - **[v3] NSV Unit Confirmed:** Rename "NSV" column to "Source_NSV_Lacs" (confirmed unit = Lakhs)
   - **[v3] NSV Conversions (NEW):**
     - Create NSV_Actual_Value = Source_NSV_Lacs × 100,000 (convert to rupees)
     - Create NSV_Cr = Source_NSV_Lacs ÷ 100 (convert to Crores for display)
     - Create Is_Negative_NSV flag for QC (Source_NSV_Lacs < 0)
   - **[v3] MRP Conversion (NEW):**
     - Create MRP_Sales_Value_Cr = MRP_Sales_Value ÷ 10,000,000 (convert to Crores for display)
   - **[v3] Qty Conversion (NEW):**
     - Create Sales_Qty_Cr = Sales_Qty ÷ 10,000,000 (convert to Crores for display)
   - Extract Month from Month_Raw label (e.g., "Apr-24" → 4)
   - Calculate FY (Apr–Mar rule: Apr–Dec → FY+1; Jan–Mar → FY)
   - Create Month_Sort, Month, FY columns
   - Flag June'26 as Partial
   - **[v3] BA Availability Flag:** Create BA_Available = "Yes" if Chain_Name = "Brand Counter", else "No"
   - Create Safe_Value_Basis = MRP_Sales_Value
   - Create Is_Safe_For_Reporting = TRUE (all rows safe for MRP & NSV reporting; NSV unit now confirmed)

4. **Close & Load** → Load to Power BI

### Step 1.3: Create Dimension Tables

#### Dimension 1: Dim_Month

1. **New Query** → Reference "Offtake_Safe"
2. **Remove Duplicate Columns:** Keep only Month, FY, Month_Num, Month_Sort, Calendar_Year, Is_Month_Partial, Is_June26_Partial
3. **Remove Duplicates** → Group by Month (one row per month)
4. **Add Column:** Fiscal_Quarter (Q1–Q4 + FY year)
5. **Add Column:** Date (first day of month, e.g., 2024-04-01 for "Apr-24")
6. **Sort:** FY ASC, Month_Sort ASC
7. **Name:** `Dim_Month`
8. **Close & Load** → Load as Table

#### Dimension 2: Dim_Chain_Raw

1. **New Query** → Reference "Offtake_Safe"
2. **Keep:** Chain_Name only
3. **Remove Duplicates**
4. **Add Metadata Columns:**
   - Row_Count = COUNTIF(Offtake_Safe[Chain_Name] = this Chain_Name)
   - MRP_Total = SUMIF(Offtake_Safe[Chain_Name] = this Chain_Name, MRP_Sales_Value)
5. **Sort:** MRP_Total DESC
6. **Name:** `Dim_Chain_Raw`
7. **Close & Load**

#### Dimension 3: Dim_Zone

1. **New Query** → Reference "Offtake_Safe"
2. **Keep:** Zone only
3. **Remove Duplicates**
4. **Add Metadata Columns:** Row_Count, MRP_Total (as above)
5. **Sort:** MRP_Total DESC
6. **Name:** `Dim_Zone`
7. **Close & Load**

#### Dimension 4: Dim_Category

1. **New Query** → Reference "Offtake_Safe"
2. **Keep:** Category, PPT_Category (if separate)
3. **Remove Duplicates**
4. **Add Metadata Columns:** Row_Count, MRP_Total
5. **Sort:** MRP_Total DESC
6. **Name:** `Dim_Category`
7. **Close & Load**

### Step 1.4: Create QC Reference Tables

#### QC Table 1: QC_Monthly_Reconciliation

1. **New Query** → Reference "Offtake_Safe"
2. **Group By:** Month, FY, Is_Month_Partial
3. **Aggregate:**
   - Row_Count = COUNT(all rows)
   - MRP_Sales_Value = SUM
   - Sales_Qty = SUM
   - Negative_Value_Row_Count = COUNT(Is_Negative_Return = TRUE)
4. **Sort:** FY ASC, Month_Sort ASC
5. **Name:** `QC_Monthly_Reconciliation`
6. **Close & Load**

#### QC Table 2: QC_Duplicate_Report

1. **New Query** → Reference "Offtake_Safe" → Filter: Chain_Name = "More Retail"
2. **Add Column:** Row_Hash = Text.Combine({Site_Code, Chain_Name, Category, Month, MRP_Sales_Value})
3. **Group By:** Row_Hash
4. **Aggregate:**
   - Count = ROWS
   - MRP_Total = SUM(MRP_Sales_Value)
   - Sample_Month = FIRST(Month)
5. **Filter:** Count > 1 (show only duplicates)
6. **Sort:** Count DESC
7. **Name:** `QC_Duplicate_Report`
8. **Close & Load**

#### QC Table 3: QC_Chain_Variant_Check

Copy the PQ query from `PowerQuery_Safe_Offtake.pq` (pre-built reference query)

#### QC Table 4: QC_Blocked_Measures

Copy the PQ query from `PowerQuery_Safe_Offtake.pq` (pre-built reference query)

#### QC Table 5: QC_Pending_Decisions

Copy the PQ query from `PowerQuery_Safe_Offtake.pq` (pre-built reference query)

---

## Phase 2: Define Relationships (10–15 minutes)

### Step 2.1: Set Up Fact-to-Dimension Relationships

In Power BI Desktop **Model View:**

1. **Fact_Offtake_Safe → Dim_Month**
   - From: Month_Sort, FY (composite key)
   - To: Month_Sort, FY
   - Cardinality: Many-to-One
   - Direction: Both

2. **Fact_Offtake_Safe → Dim_Chain_Raw**
   - From: Chain_Name
   - To: Chain_Name
   - Cardinality: Many-to-One
   - Direction: Both

3. **Fact_Offtake_Safe → Dim_Zone**
   - From: Zone
   - To: Zone
   - Cardinality: Many-to-One
   - Direction: Both

4. **Fact_Offtake_Safe → Dim_Category**
   - From: Category
   - To: Category
   - Cardinality: Many-to-One
   - Direction: Both

### Step 2.2: Verify Relationships

- Confirm no circular dependencies
- Confirm no bridges needed (model should be star schema)
- Mark QC tables as "Hide from Report View" (optional) to reduce clutter

---

## Phase 3: Create DAX Measures (20–30 minutes)

### Step 3.1: Create Measure Table

1. **Right-click** Fact_Offtake_Safe → **New Table**
2. **Enter:** `Measures = SELECTCOLUMNS(GENERATESERIES(1,1),"Seq",[Value])`
   (This creates a placeholder table for measures)
3. **Rename to:** `Measures`

### Step 3.2: Add Safe Measures

For each measure in `DAX_Safe_Measures.dax`:

1. **Right-click Measures table** → **New Measure**
2. **Enter measure name** (e.g., "MRP Sales Value")
3. **Enter DAX formula** (copy from `DAX_Safe_Measures.dax`)
4. **Set format:** Currency (₹) or Number as appropriate
5. **Repeat** for all 22+ measures

**Key measures to add first:**
- [MRP Sales Value]
- [MRP Sales Value Cr]
- **[v3 NEW]** [Source NSV Lacs] (NSV now confirmed and active)
- **[v3 NEW]** [NSV Cr] (NSV converted from Lakhs ÷ 100)
- [Sales Qty]
- [Sales Qty Cr]
- [Row Count]
- [MRP Contribution %]
- **[v3 NEW]** [NSV Contribution %] (NSV now active)
- [Distinct Chains]
- [Has June26 Partial]
- [June26 Partial Warning]
- **[v3 NEW]** [MRP to NSV Ratio] (for comparison)
- **[v3 NEW]** [BA Available MRP Sales Value Cr]
- **[v3 NEW]** [BA Available NSV Cr] (NSV now active on BA coverage)
- **[v3 NEW]** [BA Availability Mix % NSV] (NSV now active on BA coverage)

### Step 3.3: Verify Measures

- Confirm all measures return numbers (no errors)
- **[v3]** Confirm NSV-based measures ARE created (NSV unit confirmed)
- Confirm [NSV Cr] calculates correctly (Source NSV Lacs ÷ 100)
- Confirm [MRP Sales Value Cr] calculates correctly (MRP ÷ 10,000,000)
- Confirm no Profitability/CM2/Margin % measures are created
- Confirm no State-level measures exist
- Confirm no BA profitability measures exist (BA coverage only)

---

## Phase 4: Build Report Pages (60–75 minutes)

### Step 4.1: Create 5 Report Pages

1. **New Page** → Rename to "Data Explorer"
2. **New Page** → Rename to "Overview"
3. **New Page** → Rename to "QC & Reconciliation"
4. **New Page** → Rename to "Interim Offtake P&L"
5. **New Page** → Rename to "BA Availability View"

### Step 4.2: Add Slicers (on every page)

**Standard slicer set:**
- FY (Dim_Month[FY])
- Month (Dim_Month[Month])
- Chain (Dim_Chain_Raw[Chain_Name])
- Zone (Dim_Zone[Zone])
- Category (Dim_Category[Category])
- Format (Fact_Offtake_Safe[Format])
- Classification (Fact_Offtake_Safe[Classification])

**NOT included:**
- State (blocked by business decision: zone-only approach)
- NSV (not a slicer; NSV Cr measure is now active on Pages 1–5)

### Step 4.3: Page 1 — Data Explorer

Follow spec in `PowerBI_Report_Page_Spec.md`:

1. **Add KPI Cards (top row):**
   - Row Count → [Row Count]
   - MRP Sales Value → [MRP Sales Value Cr]
   - **[v3 NEW]** NSV Sales Value → [NSV Cr] (NSV now confirmed and active)
   - Sales Qty → [Sales Qty]
   - Month Coverage → DISTINCTCOUNT(Dim_Month)

2. **Add Charts (3-column grid):**
   - MRP by Chain (column, top 10)
   - **[v3 NEW]** NSV by Zone (column, top 10) — NSV now active
   - MRP by Category (column, top 10)
   - MRP Trend (line by month)
   - **[v3 NEW]** NSV Trend (line by month) — NSV now active
   - Contribution % (MRP vs NSV) — dual-basis comparison (NSV now active)

3. **Add Detail Table:**
   - Columns: Site_Code, Site_Name, Chain_Name, Zone, Category, Month, FY, Sales_Qty, MRP_Sales_Value
   - Row limit: 1,000 (show record count)

4. **Add Slicers** (left side or top)

5. **Add Text Box (warning):**
   "⚠ June'26 is PARTIAL: 78,111 rows from 16 chains only. Some accounts pending."

### Step 4.4: Page 2 — Overview

Follow spec:

1. **Add Watermark Text Box (top):**
   "Offtake Overview — MRP & NSV Sales Value Basis (v3: NSV Confirmed Lakhs)
   NSV converted to ₹ Crore (Lakhs ÷ 100) | MRP in ₹ actual rupees (÷10,000,000 for Cr) | June'26 Partial"
   (Color: Teal background, replaces amber from v1/v2)

2. **Add KPI Cards:**
   - Total MRP (Apr'24–Jun'26) → [MRP Sales Value Cr]
   - **[v3 NEW]** Total NSV (Apr'24–Jun'26) → [NSV Cr] (NSV now confirmed and active)
   - **[v3 NEW]** MRP vs NSV Ratio → [MRP to NSV Ratio] (relationship indicator)
   - Total Qty → [Sales Qty]
   - Active Chains → [Distinct Chains]
   - Active Zones → [Distinct Zones]
   - June'26 Row Count → [June26 Partial Row Count]
   - Negative Returns → [Negative Return Rows]

3. **Add Charts (2-column grid):**
   - **[v3 UPDATED]** MRP vs NSV Trend (Month) (line, dual-axis) — NSV now active
   - MRP Trend by FY (line)
   - MRP Share by Zone (doughnut)
   - **[v3 UPDATED]** NSV Share by Category (doughnut) — NSV now active
   - Top 10 Chains (bar)
   - **[v3 UPDATED]** Qty vs NSV by Zone (clustered, dual-axis) — NSV now active

4. **Add Slicers**

5. **Add Info Box:**
   "NSV-based measures blocked until unit validation. Using MRP Sales Value (verified) as interim basis."

### Step 4.5: Page 3 — QC & Reconciliation

Follow spec:

1. **Add Summary Cards:**
   - Files Scanned: 582
   - Total Rows: [Row Count]
   - Data Period: Apr'24–Jun'26
   - Grand MRP: [MRP Sales Value Cr]
   - **[v3 NEW]** Grand NSV: [NSV Cr] (NSV now confirmed and active)

2. **Add Table 1 (QC_Monthly_Reconciliation):**
   - Columns: Month, FY, Is_Month_Partial (badge), Row_Count, MRP_Sales_Value, Sales_Qty, Negative_Value_Row_Count
   - **[v3 NEW]** Add column: NSV_Cr (or NSV_Monthly if in QC table)
   - Conditional formatting: June'26 row orange, negative values orange

3. **Add Table 2 (QC_Chain_Variant_Check):**
   - Columns: Chain_Name, Row_Count, MRP_Total
   - Note below: "34 chains found; variants pending canonicalization. More Retail: All rows retained (business approved)."

4. **Add Table 3 (QC_More_Retail_Audit):**
   - Columns: Month, FY, Row_Count, MRP_Total
   - Note: "Business reviewed More Retail records. No dedup applied. All rows retained as valid."

5. **Add Text Box: Blocked Measures (v3: NSV Confirmed)**
   - **[v3 UPDATED]** List now shows NSV as ✓ ACTIVE (was blocked in v1/v2)
   - Cost sources (P&L, CM2, Margin %, BA profitability) now appear as blockers
   - Copy from updated QC_Blocked_Measures table

6. **Add Table: Pending Decisions (v3: NSV Complete, Cost Structure Pending)**
   - **[v3 UPDATED]** NSV Unit Validation: COMPLETE (confirmed Lakhs)
   - **[v3 UPDATED]** More Retail Duplicates: COMPLETE (all rows retained)
   - **[v3 UPDATED]** Brand Counter Classification: COMPLETE (BA Availability flag)
   - **[v3 UPDATED]** State-to-City Mapping: COMPLETE (zone-only approach)
   - **[v3 NEW]** Profitability & Cost Structure: PENDING (now primary blocker)
   - Chain Master Canonicalization: PENDING
   - Display QC_Pending_Decisions table (updated format with v3 status)
   - Columns: Decision, Timeline, Status

### Step 4.6: Page 4 — Interim Offtake View: MRP, NSV & Qty

**[v3 RENAMED]** from "Interim Offtake P&L" to reflect multi-basis view (MRP & NSV confirmed)

Follow spec:

1. **Add Watermark (top, amber background):**
   "Interim view. NSV confirmed at source (Lakhs); converted to ₹ Crore (÷100) for display alongside MRP (÷10,000,000 for Cr).
   MRP and NSV can now be compared on equal footing (both in ₹ Crore).
   All profitability, margin %, and CM2 measures remain blocked until cost sources are confirmed. June'26 is PARTIAL."
   (Color: Amber background, replaces red from v1/v2)

2. **Add KPI Cards:**
   - Total Offtake (MRP) → [MRP Sales Value Cr]
   - **[v3 NEW]** Total Offtake (NSV) → [NSV Cr] (NSV now confirmed and active)
   - Total Qty → [Sales Qty]
   - Avg MRP/Month → [Avg MRP Per Month Cr]
   - **[v3 NEW]** MRP vs NSV Ratio → [MRP to NSV Ratio]
   - Jun'26 MRP → CALCULATE([MRP Sales Value Cr], Is_June26_Partial=TRUE)

3. **Add Charts (2-column grid):**
   - MRP by Chain (top 10)
   - **[v3 NEW]** NSV by Zone — NSV now active
   - **[v3 UPDATED]** MRP Trend (Month; mark June'26; add MoM annotation)
   - **[v3 NEW]** NSV Trend (Month; MoM comparison) — NSV now active
   - **[v3 UPDATED]** MRP & NSV Contribution % (Category, dual-basis) — NSV now active
   - **[v3 NEW]** MRP MoM vs NSV MoM Change (Month; dual-metric trend) — NSV now active

4. **Add Slicers:**
   - FY, Month, Chain, Zone, Category (standard set)

5. **Add Info Box:**
   "MRP and NSV confirmed and active. Profitability, CM2, margin %, and BA profitability measures remain BLOCKED pending cost sources."

6. **DO NOT include:**
   - Margin %
   - Profitability
   - CM2
   - State-level rollups
   - BA profitability metrics
   - (NSV measures ARE now included on this page)

### Step 4.7: Page 5 — BA Availability View

**Purpose:** Show Reliance Brand Counter coverage (coverage only, not profitability)

Follow spec in `PowerBI_Report_Page_Spec.md`:

1. **Add Watermark (top, amber):**
   "Reliance BA Availability Coverage (v3: NSV Now Active)
   Coverage view only. Shows BA (Brand Counter) availability. BA profitability is blocked until cost structure is confirmed."

2. **Add KPI Cards:**
   - BA Available Row Count → [BA Available Row Count]
   - BA Available MRP → [BA Available MRP Sales Value Cr]
   - **[v3 NEW]** BA Available NSV → [BA Available NSV Cr] (NSV now confirmed and active)
   - **[v3 NEW]** BA Availability Mix % (MRP) → [BA Availability Mix %]
   - **[v3 NEW]** BA Availability Mix % (NSV) → [BA Availability Mix % NSV] (NSV now active)
   - Total MRP (All) → [MRP Sales Value Cr] (for comparison)

3. **Add Charts (2-column grid):**
   - BA Available MRP by Zone (column)
   - **[v3 NEW]** BA Available NSV by Category (column) — NSV now active
   - BA Available MRP Trend by Month (line)
   - **[v3 NEW]** BA Available NSV Trend by Month (line) — NSV now active

4. **Add Slicers:**
   - FY (required)
   - Month (required)
   - Zone (recommended)
   - Category (optional)

5. **Add Detail Table:**
   - Columns: Site_Code, Site_Name, Chain_Name, Zone, Category, Month, FY, Sales_Qty, MRP_Sales_Value
   - Row limit: 1,000 (show record count)
   - Filter: BA_Available = "Yes"

6. **Add Info Box:**
   "Brand Counter represents BA availability. Business decision APPROVED: This is a coverage view only. BA profitability metrics are blocked pending cost structure and headcount."

7. **DO NOT include:**
   - BA Profitability
   - BA Cost to Serve
   - BA Productivity
   - State-level breakdowns
   - Margin % / CM2 / P&L metrics
   - (NSV measures ARE now included on this page)

---

## Phase 5: Final Validation (15–20 minutes)

### Step 5.1: Verify Safe-Only Implementation (v3: NSV Now Active)

Run through this checklist:

- [ ] **[v3]** NSV measures (NSV Cr, NSV Contribution %, NSV MoM, etc.) appear on Pages 1–5
- [ ] **[v3]** NSV Cr calculations correct (Source NSV Lacs ÷ 100)
- [ ] **[v3]** MRP Cr calculations correct (MRP ÷ 10,000,000)
- [ ] **[v3]** NSV and MRP both displayed in ₹ Crore for comparison
- [ ] **[v3]** Watermarks updated: "NSV converted from Lakhs to ₹Cr" (NOT "NSV unit pending")
- [ ] No Profitability / CM2 / Margin % visuals anywhere
- [ ] No State dimension visible or filtered
- [ ] No BA profitability visuals (Page 5 shows coverage only)
- [ ] June'26 flagged as Partial on Pages 1–4 (visual markers + text)
- [ ] All 5 pages load without errors
- [ ] Slicers work correctly (cross-filter behavior)
- [ ] Watermarks visible and readable on all 5 pages
- [ ] More Retail rows kept; no dedup applied
- [ ] More Retail note says "Business-approved retained records"
- [ ] Chain variants shown RAW (not canonicalized)
- [ ] All charts use MRP & NSV as dual value basis (v3)
- [ ] QC & Reconciliation page shows blocked list updated (NSV ✓ ACTIVE; cost sources PENDING)
- [ ] QC & Reconciliation page shows pending decisions updated (NSV complete; cost structure pending)
- [ ] Page 4 renamed: "Interim Offtake View: MRP, NSV & Qty"
- [ ] Page 5 watermark reflects "Coverage only, not profitability" + NSV now active
- [ ] No BA cost/headcount/productivity metrics on Page 5

### Step 5.2: Test Filtering

1. **Filter to June'26 only** → Confirm watermark appears + row count = 78,111 (approximately)
2. **Filter to one chain** → Confirm breakdown by zone/category works
3. **Filter to one zone** → Confirm breakdown by chain/category works
4. **Switch between pages** → Confirm all slicers propagate correctly

### Step 5.3: Check Performance

- Refresh entire data model → Should complete in < 30 seconds
- Verify no query folding issues (all queries marked as loaded)
- Check data volume: 4.21M rows should load without significant lag

---

## Phase 6: Save & Export (5 minutes)

### Step 6.1: Save PBIP (Power BI Project)

1. **File** → **Save As**
2. **Save as type:** Power BI Project file (.pbip)
3. **Filename:** `MT_Dashboard_Safe_Blocks_vYYYYMMDD.pbip`
4. **Location:** `PowerBI/Safe_Blocks/`

### Step 6.2: Export PBIX (if needed)

If PBIX is required for sharing with non-PBIP environments:

1. **File** → **Export**
2. **Select:** Power BI Report (.pbix)
3. **Filename:** `MT_Dashboard_Safe_Blocks_vYYYYMMDD.pbix`
4. **Location:** `PowerBI/Safe_Blocks/`

---

## Troubleshooting

### Issue: "Query folding not supported" warning

**Solution:** This is normal for Power Query transformations. Confirm data loads without errors. Performance may be slower than native SQL, but acceptable for this 4.21M-row dataset.

### Issue: June'26 not visible in Month slicer

**Solution:** Confirm Dim_Month includes June'26. Check Power Query: `Is_Month_Partial` should be TRUE for June'26. Refresh data source.

### Issue: Circular relationship error

**Solution:** Confirm relationships are one-way (Many-to-One) and no extra relationships exist. QC tables should have NO relationships to fact/dimension tables.

### Issue: Blank values in charts

**Solution:** Confirm all slicers have "Show items with no data" enabled if needed. Confirm fact table has no NULL values in key columns (Site_Code, Chain_Name, Zone, Month).

---

## Business Rulings Applied (v2)

The following business rulings have been applied:
- ✓ **More Retail Duplicates:** Business reviewed and retained as valid. No dedup applied.
- ✓ **Reliance Brand Counter:** Classified as BA Availability (coverage view). Page 5 created.
- ✓ **State Mapping:** Source data unreliable; no state-level rollups. Zone-level used.

## Next Steps (After Remaining Business Decisions)

Pending decisions still awaiting approval:

1. **NSV Unit Validation** → Finance must provide ₹Cr anchor for 1 month
   - Timeline: Pending
   - Impact: Unblocks [NSV Cr], [Profitability], all %-growth on NSV

2. **Chain Master Canonicalization** → Business approves canonical names
   - Timeline: Pending
   - Impact: Allows Vmm/VMM, Fsn/FSN merging in Dim_Chain_Canonical

3. **Reliance Schema Completeness** → Accept partial (29 cols) or request full
   - Timeline: Pending
   - Impact: Affects Reliance field mapping

Once approved, proceed with:
1. NSV Unit Confirmed → Implement [NSV Cr] measure; unblock NSV-based pages
2. Chain Master Approved → Add Dim_Chain_Canonical; replace Chain_Name with canonical
3. Reliance Schema Finalized → Ensure all measures work with Reliance data

---

**Status:** Safe Blocks build updated with business rulings v2. Ready for deployment.

**Estimated Total Build Time:** 2.5–3.5 hours (first-time build with 5 pages)

