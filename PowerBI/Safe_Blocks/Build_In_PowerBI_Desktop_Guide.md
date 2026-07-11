# Build Guide: Creating Safe Offtake Blocks in Power BI Desktop

**Branch:** claude/safe-powerbi-blocks  
**Target:** Power BI Desktop 2024.11 or later  
**Generated:** 2026-07-11  
**Status:** Step-by-step implementation guide

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
   - Extract Month from Month_Raw label (e.g., "Apr-24" → 4)
   - Calculate FY (Apr–Mar rule: Apr–Dec → FY+1; Jan–Mar → FY)
   - Create Month_Sort, Month, FY columns
   - Flag June'26 as Partial
   - Create Safe_Value_Basis = MRP_Sales_Value

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
- [Sales Qty]
- [Row Count]
- [MRP Sales Value Cr]
- [MRP Contribution %]
- [Distinct Chains]
- [Has June26 Partial]
- [June26 Partial Warning]

### Step 3.3: Verify Measures

- Confirm all measures return numbers (no errors)
- Confirm no NSV-based measures are created
- Confirm no State-level measures exist
- Confirm no BA profitability measures exist

---

## Phase 4: Build Report Pages (45–60 minutes)

### Step 4.1: Create 4 Report Pages

1. **New Page** → Rename to "Data Explorer"
2. **New Page** → Rename to "Overview"
3. **New Page** → Rename to "QC & Reconciliation"
4. **New Page** → Rename to "Interim Offtake P&L"

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
- State (blocked, mapping pending)
- NSV (blocked, unit pending)

### Step 4.3: Page 1 — Data Explorer

Follow spec in `PowerBI_Report_Page_Spec.md`:

1. **Add KPI Cards (top row):**
   - Row Count → [Row Count]
   - MRP Sales Value → [MRP Sales Value Cr]
   - Sales Qty → [Sales Qty]
   - Month Coverage → DISTINCTCOUNT(Dim_Month)

2. **Add Charts (3-column grid):**
   - MRP by Chain (column, top 10)
   - MRP by Zone (column, top 10)
   - MRP by Category (column, top 10)
   - MRP Trend (line by month)
   - Qty Trend (line by month)
   - Contribution % (pie or donut)

3. **Add Detail Table:**
   - Columns: Site_Code, Site_Name, Chain_Name, Zone, Category, Month, FY, Sales_Qty, MRP_Sales_Value
   - Row limit: 1,000 (show record count)

4. **Add Slicers** (left side or top)

5. **Add Text Box (warning):**
   "⚠ June'26 is PARTIAL: 78,111 rows from 16 chains only. Some accounts pending."

### Step 4.4: Page 2 — Overview

Follow spec:

1. **Add Watermark Text Box (top):**
   "Interim Offtake Overview — MRP Sales Value Basis
   ⚠ NSV unit pending | June'26 Partial"

2. **Add KPI Cards:**
   - Total MRP (Apr'24–Jun'26) → [MRP Sales Value Cr]
   - Total Qty → [Sales Qty]
   - Active Chains → [Distinct Chains]
   - Active Zones → [Distinct Zones]
   - June'26 Row Count → [June26 Partial Row Count]
   - Negative Returns → [Negative Return Rows]

3. **Add Charts (2-column grid):**
   - MRP Trend by Month (line; mark June'26 with dashed line)
   - MRP Trend by FY (line)
   - MRP Share by Zone (doughnut)
   - MRP Share by Category (doughnut)
   - Top 10 Chains (bar)
   - Qty vs MRP by Zone (clustered)

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

2. **Add Table 1 (QC_Monthly_Reconciliation):**
   - Columns: Month, FY, Is_Month_Partial (badge), Row_Count, MRP_Sales_Value, Sales_Qty, Negative_Value_Row_Count
   - Conditional formatting: June'26 row orange, negative values orange

3. **Add Table 2 (QC_Chain_Variant_Check):**
   - Columns: Chain_Name, Row_Count, MRP_Total
   - Note below: "34 chains found; variants pending canonicalization. More Retail: 13,661 duplicates (₹1.36 Cr / 10.3% MRP)."

4. **Add Table 3 (QC_Duplicate_Report):**
   - Show if More Retail has duplicates
   - Columns: Count, MRP_Total, Sample_Month

5. **Add Text Box: Blocked Measures**
   - List of 11 blocked measures (copy from QC_Blocked_Measures table)

6. **Add Table: Pending Decisions**
   - Display QC_Pending_Decisions (6 rows)
   - Columns: Decision, Action, Impact, Timeline

### Step 4.6: Page 4 — Interim Offtake P&L (MRP Basis)

Follow spec:

1. **Add Watermark (top, red background):**
   "⚠ INTERIM ONLY: NSV unit pending. June'26 Partial."

2. **Add KPI Cards:**
   - Total Offtake (MRP) → [MRP Sales Value Cr]
   - Total Qty → [Sales Qty]
   - Avg MRP/Month → [Avg MRP Per Month Cr]
   - Jun'26 MRP → CALCULATE([MRP Sales Value Cr], Is_June26_Partial=TRUE)

3. **Add Charts:**
   - MRP by Chain (top 10)
   - MRP by Zone
   - MRP Trend by Month (mark June'26)
   - Category Mix (pie)
   - Top 15 Category × Chain (table)
   - MRP MoM Change (card or gauge)

4. **Add Slicers**

5. **Add Info Box:**
   "NSV-based profitability blocked. Using MRP Sales Value basis only."

6. **DO NOT include:**
   - NSV measure
   - Margin %
   - Profitability
   - CM2
   - State-level rollups
   - BA metrics

---

## Phase 5: Final Validation (15–20 minutes)

### Step 5.1: Verify Safe-Only Implementation

Run through this checklist:

- [ ] No NSV measure appears in any visual
- [ ] No State dimension visible or filtered
- [ ] No BA profitability visuals
- [ ] June'26 flagged as Partial on all pages (visual markers + text)
- [ ] All 4 pages load without errors
- [ ] Slicers work correctly (cross-filter behavior)
- [ ] Watermarks visible and readable
- [ ] More Retail duplicates reported but NOT deduped
- [ ] Chain variants shown RAW (not canonicalized)
- [ ] All charts use MRP Sales Value as value basis
- [ ] QC & Reconciliation page shows all reference tables

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

## Next Steps (After Business Decisions)

Once business approves the 6 pending decisions, proceed with:

1. **NSV Unit Confirmed** → Implement [NSV Cr] measure; unblock NSV pages
2. **More Retail Dedup Decided** → Apply dedup in Power Query if approved
3. **Chain Master Approved** → Add Dim_Chain_Canonical; replace Chain_Name with canonical
4. **State-to-City Mapping Approved** → Add Dim_State_Canonical; enable state-level slicers
5. **Brand Counter Classified** → Add Dim_BA_Store; enable BA reporting
6. **Reliance Schema Finalized** → Ensure all measures work with Reliance data

---

**Status:** Safe Blocks build is complete and ready for deployment.

**Estimated Total Build Time:** 2–3 hours (first-time build)

