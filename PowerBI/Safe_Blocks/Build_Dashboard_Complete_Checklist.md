# Build Dashboard Complete Checklist — Power BI Desktop Step-by-Step

**Branch:** claude/safe-powerbi-dashboard-rulings  
**Status:** v1 — Production build guide  
**Generated:** 2026-07-11  
**Estimated time:** 5–7 hours (Pages 1–8, holding Page 9)  
**Prerequisite:** Power BI Desktop 2024.11+

---

## PHASE 0: PRE-BUILD (30 min)

### Step 0.1: Prepare source files

**Files needed (check availability):**

```
□ Fact_Offtake_Safe.csv or similar (4.21M rows, 14 columns)
□ Dim_Month.csv (27 rows)
□ Dim_Chain_Raw.csv (34 rows)
□ Dim_Zone.csv (37 rows)
□ Dim_Category.csv (50-150 rows)
□ Expense_Assumptions_Input.xlsx (seed data, 3-5 rows)
  └─ Location: C:\PowerBI\SeedData\Expense_Assumptions_Input.xlsx
□ PowerQuery_Complete_DataModel.pq (copy-paste ready)
□ DAX_Complete_Measure_Library.dax (copy-paste ready)
□ PowerBI_10Page_DetailedSpec.md (reference guide)
```

### Step 0.2: Create Power BI file

1. Open **Power BI Desktop**
2. **File → New**
3. **File → Save As**
   - Filename: `MT_Dashboard_10Pages_v1.pbix`
   - Location: `C:\PowerBI\`
4. Click **Save**

### Step 0.3: Verify environment

- Power BI version: 2024.11+ ✓
- Available disk space: 500 MB ✓
- Network connection: Stable ✓

---

## PHASE 1: BUILD DATA MODEL (90 min)

### Step 1.1: Load Fact_Offtake_Safe

1. **Home → Get Data → Text/CSV**
2. Navigate to source file: `Fact_Offtake_Safe.csv`
3. **Load**
4. **Transform Data**
   - Verify columns (14 expected):
     - FY, Month, Month_Num, Month_Label, Chain_Name, Zone, Category, Format
     - Source_NSV_Lacs, MRP_Sales_Value, Sales_Qty
     - BA_Available, Is_Negative_Return, Is_Negative_NSV, Is_June26_Partial
   - Column types: ✓ Check date/number/text formatting
5. **Close & Apply**

**Expected result:** 4.21M rows imported

### Step 1.2: Add calculated columns to Fact_Offtake_Safe

1. Right-click **Fact_Offtake_Safe** → **New Column**
2. Add 3 calculated columns:

```
NSV_Cr = Fact_Offtake_Safe[Source_NSV_Lacs] / 100

NSV_Actual_Value = Fact_Offtake_Safe[Source_NSV_Lacs] * 100000

MRP_Sales_Value_Cr = Fact_Offtake_Safe[MRP_Sales_Value] / 10000000
```

3. **Verify:** All 3 columns appear in Fields pane

### Step 1.3: Load dimensions (Dim_Month, Dim_Chain_Raw, Dim_Zone, Dim_Category)

Repeat for each dimension:

1. **Home → Get Data → Text/CSV**
2. Load file
3. **Transform Data** → Verify columns & types
4. **Close & Apply**

**Expected result:**
```
✓ Dim_Month: 27 rows, 8 columns
✓ Dim_Chain_Raw: 34 rows, 4 columns
✓ Dim_Zone: 37 rows, 4 columns
✓ Dim_Category: 50-150 rows, 4 columns
```

### Step 1.4: Create Date_Table

1. **Home → New Table**
2. Paste formula:

```
Date_Table = CALENDAR(DATE(2024,4,1), DATE(2026,6,30))
```

3. Add calculated columns:

```
Year = YEAR([Date])
Month = MONTH([Date])
Day = DAY([Date])
Quarter = "Q" & ROUNDUP(MONTH([Date])/3, 0)
Month_Name = FORMAT([Date], "MMMM")
Year_Month = FORMAT([Date], "yyyy-MM")
FY = IF(MONTH([Date]) >= 4, "FY" & YEAR([Date])+1, "FY" & YEAR([Date]))
```

### Step 1.5: Load Expense_Assumptions_Input (Excel external connection)

1. **Home → Get Data → Excel**
2. Navigate to: `C:\PowerBI\SeedData\Expense_Assumptions_Input.xlsx`
3. Select **Assumptions** sheet
4. **Load**
5. **Transform Data:**
   - Verify 32 columns (Month, Chain, Store_Code, ..., Remarks)
   - Column types: Date, Text, Number, Logical as appropriate
   - Filter out blank rows
   - Add column: `Is_Provisional = Expense_Assumptions_Input[Finance_Validation_Status] <> "Confirmed"`
6. **Close & Apply**

**Expected result:** External connection to Excel (will refresh when Excel changes)

### Step 1.6: Build relationships (Star Schema)

1. **Model tab → Manage Relationships** (or **Home → Manage Relationships**)
2. Create relationships:

| From | To | Relationship |
|------|----|----|
| Fact_Offtake_Safe | Dim_Month | [Month] ←→ [Month_Label] |
| Fact_Offtake_Safe | Dim_Chain_Raw | [Chain_Name] ←→ [Chain_Name] |
| Fact_Offtake_Safe | Dim_Zone | [Zone] ←→ [Zone_Name] |
| Fact_Offtake_Safe | Dim_Category | [Category] ←→ [Category] |
| Date_Table | Dim_Month | [Date] ←→ [Date] (optional, enhances time slicing) |

3. **Verify relationships:** Should form star schema (Fact in center, dimensions pointing inward)
4. **No red errors** in model view

### Step 1.7: Verify data quality

**Quick validation:**

```
□ Fact_Offtake_Safe: 4.21M rows loaded
□ Dim_Month: 27 rows (Apr'24 to Jun'26)
□ NSV_Cr values showing (e.g., 15.00 Cr for 1500 Lacs)
□ MRP_Sales_Value_Cr values showing (e.g., 15.00 Cr for 150M rupees)
□ BA_Available column has "Yes" and "No" values
□ June'26 partial flag visible (Is_June26_Partial = TRUE for ~78K rows)
□ Expense_Assumptions_Input loaded with 3-5 sample rows
□ All relationships created (Model view shows star schema, no red error icons)
```

---

## PHASE 2: CREATE DAX MEASURES (45 min)

### Step 2.1: Copy all measures from DAX_Complete_Measure_Library.dax

1. **Open** file: `DAX_Complete_Measure_Library.dax`
2. **Select all** (Ctrl+A)
3. **Copy** (Ctrl+C)
4. **In Power BI:**
   - **Model tab** (or **Model view**)
   - Right-click **Fact_Offtake_Safe** → **New Measure**
5. **Paste** entire DAX code into measure editor
6. Power BI auto-creates 84 measures (may take 30–60 seconds)

### Step 2.2: Organize measures (optional, for cleanliness)

1. **Model tab → Create measure group** (or manually in Fields pane)
2. Group by category:
   - Sales (measures 1–7)
   - Growth (measures 8–16)
   - Contribution (measures 17–22)
   - BA Specific (measures 23–28)
   - Expenses (measures 29–43)
   - Profitability [PROVISIONAL] (measures 44–50)
   - ROI [PROVISIONAL] (measures 51–54)
   - Data Quality (measures 55–60)
   - Returns Tracking (measures 61–64)
   - Dimension Counts (measures 65–68)
   - Ratios (measures 69–70)
   - Comparisons (measures 71–74)
   - Display & Warnings (measures 75–77)
   - Store Level (measures 78–80)
   - Helpers (measures 81–84)

### Step 2.3: Quick test (5 min)

1. **Create test page:** Right-click page tab → **New Page**
2. **Insert Card visual**
3. **Drag measure:** [Total NSV Cr]
4. **Verify:** Shows value (e.g., 1,234.56)
5. **Add filter:** Drag Dim_Month[Month_Label], select single month
6. **Verify:** Card value updates
7. **Delete test page** (right-click tab → Delete)

---

## PHASE 3: BUILD PAGES 1–8 (240 min = 4 hours)

### Template for each page:

1. **Right-click page tab → New Page**
2. **Rename** page (double-click tab)
3. **Set page size:** Design → Page size → Widescreen (16:9)
4. **Add slicers** (top)
5. **Add KPI cards** (if applicable)
6. **Add charts**
7. **Add tables/matrices** (if applicable)
8. **Format & conditional formatting**
9. **Test refresh**

---

### PAGE 1: EXECUTIVE DASHBOARD (30 min)

**Layout:**

```
Row 1: 6 KPI cards
Row 2: 2 charts (trend line, top 6 bars)
Slicers: FY | Month | Chain | Zone | Brand | Category
Footer: Warning banner
```

**Build steps:**

1. Create 6 KPI cards:
   - [Total NSV Cr] - label "NSV ₹Cr (Excl Tax)"
   - [Total MRP Sales Value Cr] - label "MRP ₹Cr (Incl Tax)"
   - [Total Sales Qty M] - label "Qty Millions"
   - [NSV MoM Growth Pct] - label "NSV Growth %", conditional color (green if >0, red if <0)
   - [MRP MoM Growth Pct] - label "MRP Growth %", conditional color
   - [Qty MoM Growth Pct] - label "Qty Growth %", conditional color

2. Create 2 charts:
   - **Chart 1: Line chart**
     - X: Dim_Month[Month_Label]
     - Y: [Total NSV Cr]
     - Title: "NSV Trend"
   - **Chart 2: Clustered bar chart**
     - X: Dim_Chain_Raw[Chain_Name]
     - Y: [Total NSV Cr]
     - Title: "Top 6 Chains by NSV"
     - Limit to top 6: Sort by [Total NSV Cr] desc, show top 6 only

3. Add slicers (6 total):
   - Drag Dim_Month[FY] → Slicer visual (multi-select)
   - Drag Dim_Month[Month_Label] → Slicer visual (multi-select)
   - Drag Dim_Chain_Raw[Chain_Name] → Slicer (multi-select)
   - Drag Dim_Zone[Zone_Name] → Slicer (multi-select)
   - Drag Dim_Category[Brand] → Slicer (multi-select)
   - Drag Dim_Category[Category] → Slicer (multi-select)

4. Add warning text box:
   ```
   ⚠️ June'26 Partial: 78,111 rows (16 chains only)
   ⚠️ Provisional Profitability: See Page 9 for details
   ```
   - Format: 12pt, red border, yellow background

5. **Test:** Select month → KPIs update ✓

---

### PAGE 2: CHAIN PERFORMANCE (45 min)

**Build steps:**

1. Add 3 KPI cards:
   - [Total NSV Cr] - "Total NSV"
   - [NSV MoM Growth Pct] - "Growth %"
   - [Distinct Zones] - "# of Zones"

2. Create drill-down matrix:
   - Rows: Dim_Chain_Raw[Chain_Name], then Dim_Zone[Zone_Name] (for drill-down)
   - Values: [Total NSV Cr], [NSV MoM Growth Pct], [Total MRP Sales Value Cr], [Total Sales Qty M]
   - Allow expand/collapse

3. Create 2 charts:
   - **Chart 1: Clustered bar**
     - X: Dim_Chain_Raw[Chain_Name]
     - Y: [Total NSV Cr]
     - Sort by [Total NSV Cr] desc
   - **Chart 2: Line chart (Top 3 chains)**
     - X: Dim_Month[Month_Label]
     - Y: [NSV MoM Growth Pct]
     - Filter to top 3 chains by NSV

4. Add slicers (same 6 as Page 1)

5. **Drill-through:** Right-click matrix → Select Drill On
   - Configure to pass Chain_Name to other pages (optional, for cross-page drill)

---

### PAGES 3–6: SIMILAR PATTERN (40–60 min each)

Follow same template:
1. Add KPI cards (3–6 per page)
2. Add charts (1–3 per page)
3. Add optional matrix/table (drill-down if applicable)
4. Add 6 slicers
5. Format & test

**Specific measures for each:**

**Page 3 (Brand):**
- [Total NSV Cr], [Distinct Categories], [NSV MoM Growth Pct]
- Charts: Brand ranking bar, Category mix stacked bar

**Page 4 (Category):**
- [Total NSV Cr], [Category Count], [NSV MoM Growth Pct]
- Charts: Category ranking, Category trend line, NSV vs Qty scatter

**Page 5 (Zone):**
- [Total NSV Cr], [Distinct Chains], [NSV MoM Growth Pct]
- Charts: Zone ranking, Zone growth comparison, optional heatmap

**Page 6 (Store):**
- Requires Store_Master table (pending Operations)
- Build with placeholder data for now
- 3 tabs: Top stores, Bottom stores, Growth leaders
- Measures: NSV, Growth %, Qty

---

### PAGE 7: BA STORES PERFORMANCE (90 min) ⚠️

**Layout:**

```
Row 1-4: 12 KPI cards (3 cols × 4 rows)
  Row 1: [BA Available NSV Cr] | [Non_BA Available NSV Cr] | [BA Coverage Pct]
  Row 2: [BA Available Growth Pct] | [BA Row Count] | [BA Available MRP]
  Row 3: [Total BA Cost Cr] | [NPI Listing Cost Cr] | [Visibility Rental Cost Cr]
  Row 4: [CM2 Cr Provisional] ⚠️ | [CM2 Pct Provisional] ⚠️ | [Break Even Gap Cr Provisional] ⚠️

Row 5-7: 3 charts
  Chart 1: BA vs Non-BA Trend (line)
  Chart 2: Pre-BA vs Post-BA Growth (bar)
  Chart 3: Comparable-Store Scatter (bubble)

Row 8: 19-column store profitability matrix/table
  Columns: Chain, Store, NSV, Qty, Growth %, (7 costs), Total Cost, CM2, CM2%, Break-even Gap, Status
  Conditional formatting: Green/Yellow/Orange/Red/Gray by [Store Status]

Footer: Warning banner ⚠️ PROVISIONAL PROFITABILITY
```

**Build steps:**

1. Add 12 KPI cards (use measures as shown above)
   - Cards 4, 6, 12 need yellow ⚠️ formatting (conditional)

2. Create trend line chart:
   - X: Dim_Month[Month_Label]
   - Y-Series 1: [BA Available NSV Cr] (blue)
   - Y-Series 2: [Non_BA Available NSV Cr] (gray)
   - Legend: "BA Stores | Non-BA Stores"

3. Create comparison bar chart:
   - X: Dim_Chain_Raw[Chain_Name]
   - Y-Series 1: [Pre_BA Growth Pct] (red)
   - Y-Series 2: [Post_BA Growth Pct] (green)
   - Optional Y-Series 3: [Break Even Gap Pct] (gray)

4. Create scatter plot:
   - X: [Store Prior Month NSV Cr]
   - Y: [Store NSV Cr]
   - Bubble size: [Store CM2 Cr Provisional]
   - Bubble color: [Store Status] (conditional color legend)

5. Create matrix/table (19 columns):
   - Rows: Store_Code (once Store Master available, use Store Code + Store Name)
   - Values: [Store NSV Cr], [Store Sales Qty], [Store Growth Pct]
   - Add expense columns: [BA Salary Cost Cr], [BA Supervisor Cost Cr], ..., [TOT Cost], [Promotional Cost], [Visibility], [Other Employee Cost]
   - Add profitability: [Store BA Cost Cr], [Total Support Cost Cr], [Store CM2 Cr Provisional], [CM2 Pct Provisional], [Break Even Gap Cr Provisional]
   - Add status: [Store Status], [Recommendation_Status]

6. Conditional formatting for table:
   ```
   If [Store Status] = "Strong Performer" → Green (#00B050)
   If [Store Status] = "Monitor" → Yellow (#FFC000)
   If [Store Status] = "Improvement Required" → Orange
   If [Store Status] = "Below Break-even" → Red (#FF0000)
   If [Store Status] = "Cost Data Pending" → Gray (#D9D9D9)
   If [Has Missing Costs] = TRUE → Yellow highlight on cost columns
   ```

7. Add slicers:
   - Add custom slicer for BA Status: "BA" / "Non-BA" / "All"
   - Add standard 6 slicers

8. Add warning banner:
   ```
   ⚠️ PROVISIONAL PROFITABILITY: TOT, promotional, listing, COGS unit, 
      margins, and CM2 are pending Finance validation.
      Do NOT recommend closure or BA withdrawal until Q1-Q2 confirmed.
   ```

9. **Test refresh:** Update Expense_Assumptions_Input.xlsx → Refresh Power BI → KPIs update ✓

---

### PAGE 8: EXPENSE DASHBOARD (60 min) ⚠️

**Layout:**

```
Row 1: 6 cost KPI cards
Row 2-3: 3 charts (pie, trend, by chain)
Row 4: Cost allocation table
Slicers: Standard 6
Warning: TOT % & Promo % pending Finance Q4-Q5
```

**Build steps:**

1. Add 6 KPI cards:
   - [Total BA Cost Cr]
   - [NPI Listing Cost Cr]
   - [TOT Cost Cr Provisional] ⚠️ (yellow formatting if BLANK)
   - [Promotional Cost Cr Provisional] ⚠️ (yellow if BLANK)
   - [Visibility Rental Cost Cr]
   - [COGS Cost Cr Provisional] ⚠️ (yellow if BLANK)

2. Create pie chart:
   - Values: Cost components as % of total
   - Measures: [Total BA Cost], [NPI Listing Cost], [TOT Cost], [Promotional Cost], [Visibility], [COGS], [Other Employee Cost]
   - Title: "Cost Breakdown"

3. Create trend line:
   - X: Dim_Month[Month_Label]
   - Y: [Total Support Cost Cr]
   - Title: "Cost Trend"

4. Create bar chart by chain:
   - X: Dim_Chain_Raw[Chain_Name]
   - Y: [Total Support Cost Cr]
   - Title: "Cost by Chain"

5. Create allocation table:
   - Rows: Store (if Store Master available)
   - Columns: Cost components (BA Salary, Supervisor, Listing, TOT, Promo, Visibility, Other)
   - Values: Cost amounts (Cr or Lakh)
   - Conditional formatting: Red if cost > NSV × 10% (high cost warning)

6. Add slicers

7. Add warning:
   ```
   ⚠️ TOT % and Promotional % values pending Finance confirmation (Q4-Q5)
   Missing costs shown as "Pending" not ₹0
   ```

---

### PAGE 10: DATA QUALITY DASHBOARD (50 min)

**Layout:**

```
Row 1: 5 quality metric KPI cards
Row 2: Validation status table
Row 3: Monthly reconciliation table
Row 4: QC alerts text box
Row 5: Refresh status display
Slicers: Standard 6
```

**Build steps:**

1. Add 5 KPI cards:
   - [Total Row Count] - "Total Transactions"
   - [June26 Partial Row Count] - "Jun-26 Partial Rows"
   - [Negative NSV Return Count] - "Negative NSV (Returns)"
   - [Missing Cost Count] - "Missing Costs"
   - [Finance Validation Required] - "Validation Pending"

2. Create validation status table:
   - Rows: Filter Expense_Assumptions_Input where [Missing_Cost_Flag] = TRUE or [Finance_Validation_Status] ≠ "Confirmed"
   - Columns: Chain, Store_Code, Cost_Type, Missing_Cost_Flag, Finance_Validation_Status, Data_Status
   - Conditional formatting: Yellow if Missing_Cost_Flag = TRUE

3. Create reconciliation table:
   - Rows: Dim_Month[Month_Label]
   - Columns: [Total Row Count], [Distinct Chains], [Distinct Zones], [Total NSV Cr], [Total MRP Sales Value Cr], [Total Sales Qty M], [June26 Partial Row Count]
   - Shows monthly summary

4. Add QC alerts text box:
   ```
   KNOWN QC ISSUES:
   - June'26 Partial: 78,111 rows (16 chains only)
   - Negative Returns: 12,705 rows (flagged, valid credit notes)
   - More Retail Duplicates: 13,661 rows (retained, reported)
   - Pending COGS Unit Confirmation (Q1)
   - Pending CM2 Formula Confirmation (Q2)
   - Pending TOT % from Business (Q4)
   - Pending Promotional % from Business (Q5)
   - Store Master pending from Operations
   - BA Deployment dates pending from Operations/Reliance
   ```

5. Add refresh status section:
   - Text: [Data Refresh Status]
   - Display: "Last refresh: [Last Updated Date] | Status: [Data Quality Status]"

6. Add slicers

---

### PAGE 9: PROFITABILITY DASHBOARD ❌ (DO NOT BUILD YET)

**Status: BLOCKED**

```
⚠️ DO NOT BUILD THIS PAGE YET ⚠️

This page will be built ONLY after Finance confirms:

Q1: COGS Factor Units (are 0.1655 values %, ratio, per-unit, or other?)
Q2: Exact CM2 Formula & Tax-Basis Treatment

Current placeholder shows:
- 6 KPI cards (all show "Provisional" ⚠️)
- 3 charts (held for later)
- Store profitability table (held for later)
- All recommendation columns hidden ("Under Review — Provisional")

Expected Timeline: Build Page 9 once Q1-Q2 confirmed (1 week)
```

**For now:**
- Create page tab (optional): Right-click → New Page, rename to "Profitability (BLOCKED)"
- Add text box with message above
- Do NOT add visuals or measures

---

## PHASE 4: TEST & VALIDATION (60 min)

### Step 4.1: Data quality checks

```
□ Page 1: KPI values match expected ranges
  ├─ Total NSV: ₹1,200–1,500 Cr (Apr'24–Jun'26 average)
  ├─ Total MRP: ₹1,400–1,600 Cr
  ├─ Qty: 150–200 M units
  └─ Growth: -20% to +30%

□ Page 1-6: All slicers respond to clicks
  └─ Select month → KPIs update ✓

□ Page 7: BA metrics match expectations
  ├─ BA NSV < Total NSV ✓
  ├─ Non-BA NSV < Total NSV ✓
  ├─ BA Coverage % ≤ 100% ✓
  └─ CM2 shows "⚠️" labels ✓

□ Page 8: Expense measures update from Excel
  └─ Update Expense_Assumptions_Input.xlsx → Refresh Power BI → Verify cost KPI updates ✓

□ Page 10: Quality metrics show expected flags
  └─ June'26 row count ≈ 78,111 ✓
  └─ Returns count ≈ 12,705 ✓
```

### Step 4.2: Functionality checks

```
□ All slicers work correctly (multi-select, filters visuals)
□ Drill-through paths configured (if applicable)
□ Conditional formatting shows correct colors
□ Charts render without errors
□ Refresh takes < 30 seconds
□ No red error icons in data model
```

### Step 4.3: Performance checks

```
□ Dashboard loads in < 30 seconds
□ Refresh takes < 60 seconds
□ No "out of memory" warnings
□ Slicers responsive (click → chart updates within 2 sec)
```

---

## PHASE 5: SAVE & DOCUMENT (15 min)

### Step 5.1: Save file

1. **File → Save**
   - Filename: `MT_Dashboard_10Pages_v1.pbix`
   - Location: `C:\PowerBI\`

### Step 5.2: Export data model diagram (optional)

1. **Model tab → Model view**
2. **Screenshot** (Ctrl+PrintScreen)
3. Save image: `DataModel_Diagram.png`

### Step 5.3: Document build details

Create build log:

```
DASHBOARD BUILD LOG
Date: 2026-07-11
Builder: [Your name]
Time invested: [# hours]

Pages completed:
✓ Page 1: Executive Dashboard (30 min)
✓ Page 2: Chain Performance (45 min)
✓ Page 3: Brand Performance (40 min)
✓ Page 4: Category (40 min)
✓ Page 5: Zone Performance (35 min)
✓ Page 6: Store Performance (60 min)
✓ Page 7: BA Stores Performance (90 min)
✓ Page 8: Expense Dashboard (60 min)
○ Page 9: Profitability Dashboard (BLOCKED - awaiting Finance Q1-Q2)
✓ Page 10: Data Quality Dashboard (50 min)

Total time: 5–6 hours
Data validation: PASSED ✓
Performance validation: PASSED ✓

Known issues: None (all blockers documented)

Pending from Finance: Q1, Q2, Q4, Q5 answers
Pending from Operations: Store Master, BA Deployment dates
```

---

## PHASE 6: WHEN FINANCE ANSWERS Q1-Q2 (2–3 hours)

### Step 6.1: Update Expense_Assumptions_Input.xlsx

1. Open Excel file
2. Add Finance answers to relevant rows:
   - COGS_Rate: Update based on Q1 answer (what do 0.1655 values mean?)
   - CM2 formula: Document in Remarks column
   - Tax treatment: Confirm Excl_Tax / Incl_Tax for each cost

### Step 6.2: Update DAX measures

1. In Power BI:
   - Locate [COGS Cost Cr Provisional] measure
   - Replace formula based on Q1 answer
   - Locate [CM2 Cr Provisional] measure
   - Replace formula based on Q2 answer

### Step 6.3: Rename measures (optional cleanup)

1. Remove "Provisional" from measure names (now validated)
2. Update warning labels in display measures

### Step 6.4: Build Page 9 (Profitability Dashboard)

1. Add 6 KPI cards
2. Add 3 profitability charts
3. Add store profitability table
4. Unhide recommendation columns
5. Test & validate

### Step 6.5: Retest all pages

```
□ Page 1-8: Numbers haven't changed (same input = same output)
□ Page 9: New profitability numbers now available
□ Refresh validates all measures
□ No warnings or errors
```

---

## CHECKLIST SUMMARY

### Phase 0 (Pre-Build): 30 min
- [ ] Verify source files available
- [ ] Create Power BI file
- [ ] Check environment (disk space, version)

### Phase 1 (Data Model): 90 min
- [ ] Load Fact_Offtake_Safe + calculate columns
- [ ] Load 4 dimensions
- [ ] Create Date_Table
- [ ] Load Expense_Assumptions_Input (external Excel)
- [ ] Build 5 relationships (star schema)
- [ ] Verify data quality

### Phase 2 (Measures): 45 min
- [ ] Copy all 84 DAX measures
- [ ] Organize by category (optional)
- [ ] Quick test (card visual)

### Phase 3 (Pages 1–8): 240 min (4 hours)
- [ ] Page 1: Executive Dashboard (30 min)
- [ ] Page 2: Chain Performance (45 min)
- [ ] Page 3: Brand Performance (40 min)
- [ ] Page 4: Category (40 min)
- [ ] Page 5: Zone Performance (35 min)
- [ ] Page 6: Store Performance (60 min)
- [ ] Page 7: BA Stores Performance (90 min) ⚠️
- [ ] Page 8: Expense Dashboard (60 min) ⚠️
- [ ] Page 10: Data Quality Dashboard (50 min)

### Phase 4 (Test & Validation): 60 min
- [ ] Data quality checks
- [ ] Functionality checks
- [ ] Performance checks

### Phase 5 (Save & Document): 15 min
- [ ] Save .pbix file
- [ ] Export model diagram
- [ ] Document build log

### Phase 6 (Finance Q1-Q2): 2–3 hours (later)
- [ ] Update measures based on Finance answers
- [ ] Build Page 9 (Profitability)
- [ ] Retest all pages

---

## TOTAL TIME ESTIMATE

| Phase | Time |
|-------|------|
| Phase 0 (Pre-build) | 30 min |
| Phase 1 (Data Model) | 90 min |
| Phase 2 (Measures) | 45 min |
| Phase 3 (Pages 1–8) | 240 min (4 hours) |
| Phase 4 (Test & Validation) | 60 min |
| Phase 5 (Save & Document) | 15 min |
| **TOTAL (Pages 1–8, 9 held)** | **480 min = 8 hours** |
| Phase 6 (Finance Q1-Q2, Page 9) | 120–180 min (2–3 hours) |
| **GRAND TOTAL (10 pages)** | **600–660 min = 10–11 hours** |

**Realistic expectation:** 5–7 hours for Pages 1–8 (working with breaks), then +2–3 hours for Page 9 once Finance confirms.

---

## TROUBLESHOOTING

### "Query took too long to load"
- Reduce data: Filter Fact_Offtake_Safe to last 12 months first (optional)
- Increase Power BI memory: Settings → Options → Privacy

### "Measure shows error (#DIV/0! or #NAME?)"
- Verify table names match exactly (case-sensitive)
- Verify Expense_Assumptions_Input is loaded
- Check formula syntax in DAX editor

### "Slicer not filtering charts"
- Select chart → Format → Edit Interactions
- Toggle slicer effect to "Filter" (not "Highlight" or "None")

### "Refresh is slow (>2 min)"
- Check external Excel file (close in Excel, then refresh Power BI)
- Reduce data in Fact_Offtake_Safe (optional temporary measure)
- Check network connection

### "Export fails (PBIX file corrupt)"
- Save with different filename
- Close and reopen Power BI
- Restart computer if issue persists

---

**Status:** v1 — Complete build guide  
**Branch:** claude/safe-powerbi-dashboard-rulings  
**Ready to build in Power BI Desktop**

