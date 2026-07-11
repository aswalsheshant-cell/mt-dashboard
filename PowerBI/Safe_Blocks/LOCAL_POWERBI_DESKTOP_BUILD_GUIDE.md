# Power BI Desktop Local Build Guide
**For: MT Offtake Dashboard (10-page interim build)**  
**Source Commit:** e19c467  
**Branch:** claude/safe-powerbi-dashboard-rulings  
**Date:** 2026-07-11  
**Estimated Time:** 5–7 hours (Pages 1–8, 9 held)

---

## SECTION 1: ENVIRONMENT SETUP (30 MIN)

### Step 1.1: System Requirements
- **Power BI Desktop:** 2024.11+ (latest recommended)
- **Available disk space:** 500 MB minimum
- **RAM:** 8 GB minimum (16 GB recommended for 4.21M row fact table)
- **Network:** Stable (for external Excel connection to Expense_Assumptions_Input.xlsx)

### Step 1.2: Files Required
Before starting, ensure you have:
```
✓ PowerQuery_Complete_DataModel.pq
✓ DAX_Complete_Measure_Library.dax
✓ Fact_Offtake_Safe.csv (4.21M rows, 14 columns)
✓ Dim_Month.csv (27 rows)
✓ Dim_Chain_Raw.csv (34 rows)
✓ Dim_Zone.csv (37 rows)
✓ Dim_Category.csv (50-150 rows)
✓ Expense_Assumptions_Input.xlsx (seed data, 3-5 rows minimum)
✓ DATA_MODEL_DICTIONARY.md (reference)
✓ BUSINESS_RULES_FINAL.md (reference)
```

**Path Configuration:**
- **Source CSV files:** Ensure they're accessible at: `C:\Data\` (Windows) or `/Data/` (Mac/Linux)
  - **Alternative:** Edit Power Query paths to match your local folder
- **Expense Excel:** Place at: `C:\PowerBI\SeedData\Expense_Assumptions_Input.xlsx`
  - **Alternative:** Edit Power Query path to match your location

### Step 1.3: Create Power BI File
1. **Open Power BI Desktop**
2. **File → New**
3. **File → Save As**
   - **Filename:** `MT_Offtake_Dashboard_Interim_MRP_NSV_Qty.pbix`
   - **Location:** `C:\PowerBI\` (or your preferred location)
4. **Click Save**

---

## SECTION 2: LOAD DATA MODEL (90 MIN)

### Step 2.1: Import Power Query Queries

**Method A: Copy-Paste (Recommended)**
1. **Open** `PowerQuery_Complete_DataModel.pq` in text editor
2. **In Power BI Desktop:**
   - **Home → Get Data → Other Sources → Blank Query**
3. **In Power Query Editor:**
   - **View → Advanced Editor**
   - **Clear all existing code**
   - **Paste entire contents of PowerQuery_Complete_DataModel.pq**
4. Power BI auto-creates all 12 tables
5. **Close & Apply**

**Method B: Manual Load (if copy-paste has issues)**
1. Follow Step 2.1 for each table separately
2. Load Fact_Offtake_Safe first
3. Then load dimensions (Dim_Month, Dim_Chain_Raw, Dim_Zone, Dim_Category)
4. Then load master/reference tables

### Step 2.2: Configure Source Paths

**CRITICAL:** Power Query references paths like `C:\Data\Fact_Offtake_Safe.csv`

**To update paths:**
1. **Power Query Editor → Edit Queries**
2. For each CSV query:
   - Click **query name** (e.g., Fact_Offtake_Safe)
   - **Applied Steps → Source** (right-click → Edit)
   - **Update file path** to match your local location
   - **OK**
3. For Excel (Expense_Assumptions_Input):
   - Update path in Power Query to match your local Excel location

**Example path updates:**
- Windows: `C:\Data\Fact_Offtake_Safe.csv` → `C:\Users\YourName\Documents\Data\Fact_Offtake_Safe.csv`
- Mac: `/Users/YourName/Data/Fact_Offtake_Safe.csv`
- Network: `\\server\share\Data\Fact_Offtake_Safe.csv`

### Step 2.3: Verify Tables Loaded

**Expected in Power Query:**
```
✓ Fact_Offtake_Safe (4.21M rows, 18 columns including calculated)
✓ Dim_Month (27 rows, 8 columns)
✓ Dim_Chain_Raw (34 rows, 4 columns)
✓ Dim_Zone (37 rows, 4 columns)
✓ Dim_Category (50-150 rows, 4 columns)
✓ Date_Table (730+ rows, 7 columns)
✓ Store_Master (placeholder, 4 rows example)
✓ BA_Master (placeholder, 4 rows example)
✓ Expense_Assumptions_Input (3-5 rows, 32 columns)
✓ Cost_Master (10 rows, 6 columns)
✓ QC_Reference_Months (3 rows)
✓ Blocked_Measures_Reference (10 rows)
```

**Close & Apply Power Query Editor**
- Power BI loads all tables into the data model
- **Wait 2–5 minutes** for 4.21M row fact table to process

### Step 2.4: Create Relationships (Star Schema)

1. **Model tab** (or **Home → Model view**)
2. **Manage Relationships** (or right-click blank area → New Relationship)
3. **Create 5 relationships:**

| From | To | Link By |
|------|----|----|
| Fact_Offtake_Safe | Dim_Month | [Month] ←→ [Month_Label] |
| Fact_Offtake_Safe | Dim_Chain_Raw | [Chain_Name] ←→ [Chain_Name] |
| Fact_Offtake_Safe | Dim_Zone | [Zone] ←→ [Zone_Name] |
| Fact_Offtake_Safe | Dim_Category | [Category] ←→ [Category] |
| Date_Table | Dim_Month | [Date] ←→ [Date] (optional) |

**Settings for each relationship:**
- **Cardinality:** Many-to-one (Fact → Dimension)
- **Direction:** One (Dimension is single-valued)
- **Active:** Yes (for all 5)
- **Cross-filter:** Both (recommended)

**Verify:**
- **Model view** shows star schema (Fact in center, 4 dimensions around)
- **No red error icons** on any table

### Step 2.5: Quick Data Quality Check

1. **Home → Report View**
2. **Insert → Card visual**
3. **Drag measure:** Create a test measure `[Total NSV Cr]` (we'll add DAX next)
4. **Verify:** Card shows a number (not #DIV/0! error)
5. **Delete test visual** (we'll use real measures from DAX)

---

## SECTION 3: CREATE DAX MEASURES (45 MIN)

### Step 3.1: Import All 84 Measures

1. **Open** `DAX_Complete_Measure_Library.dax` in text editor
2. **In Power BI Desktop:**
   - **Model tab → right-click Fact_Offtake_Safe → New Measure**
3. **Copy entire contents of DAX_Complete_Measure_Library.dax**
4. **Paste into Power BI DAX editor**
5. **Wait 30–60 seconds** for Power BI to parse and create all 84 measures
6. **Verify:** All measures appear in Fields pane under Fact_Offtake_Safe

**Expected measures (sample):**
```
Sales section:
  ✓ [Total NSV Cr]
  ✓ [Total MRP Sales Value Cr]
  ✓ [Total Sales Qty M]

Growth section:
  ✓ [NSV MoM Growth Pct]
  ✓ [MRP MoM Growth Pct]

BA Specific section:
  ✓ [BA Available NSV Cr]
  ✓ [Non_BA Available NSV Cr]
  ✓ [BA Coverage Pct]

Profitability (Provisional):
  ✓ [CM2 Cr Provisional]
  ✓ [CM2 Pct Provisional]
  ✓ [Break Even Gap Cr Provisional]

... and 74 more measures
```

### Step 3.2: Quick Measure Test

1. **Insert → Card visual**
2. **Drag [Total NSV Cr]** from Fields pane
3. **Verify:** Shows value ≈ 1,200–1,500 Cr (Apr'24–Jun'26 aggregate)
4. **Delete card**

---

## SECTION 4: BUILD PAGES 1–8 (240 MIN = 4 HOURS)

### Build Process
For each page:
1. **Right-click page tab → New Page**
2. **Rename page** (double-click tab)
3. **Design → Page Size → Widescreen (16:9)** (recommended)
4. **Follow PAGE_BY_PAGE_BUILD_STEPS.md** for that page
5. **Insert slicers, KPI cards, charts, tables** as specified
6. **Format:** Colors, labels, warnings
7. **Refresh & verify** all visuals update correctly

### Page Build Order
**Recommended sequence (shortest to longest):**
1. **Page 1: Executive Overview** (30 min)
2. **Page 5: Zone Performance** (35 min)
3. **Page 3: Brand Performance** (40 min)
4. **Page 4: Category Performance** (40 min)
5. **Page 2: Chain Performance** (45 min)
6. **Page 8: Data Explorer** (60 min)
7. **Page 6: Store/Account Performance** (60 min)
8. **Page 7: BA Availability View** (90 min) ⚠️ Most complex
9. **Page 10: QC & Reconciliation** (50 min)

### Critical Rules for Each Page

**Every page MUST have:**
- ✅ **6 global slicers** (FY, Month, Chain, Zone, Brand, Category) — consistently formatted
- ✅ **Tax-basis labels** (NSV "(Excl Tax)" / MRP "(Incl Tax)") on any NSV/MRP column
- ✅ **Warning banners** if NSV and MRP appear together ("...different tax bases, QC/realization only")
- ✅ **June'26 partial watermark** (if applicable to that page)
- ✅ **No State slicer or State dimension**
- ✅ **Provisional labels** on any CM2/profitability measure (Page 7 only)

**Detailed page specifications:** See `PAGE_BY_PAGE_BUILD_STEPS.md`

---

## SECTION 5: BUILD PAGE 9 (PROFITABILITY QC READINESS ONLY)

### Critical: Page 9 is NOT a profitability page yet

**Create placeholder page showing:**
1. **Title:** "Profitability / CM2 Readiness QC"
2. **Status banner (red background, yellow text):**
   ```
   ⚠️ PROFITABILITY ANALYSIS — AWAITING FINANCE Q1-Q2 CONFIRMATION
   
   Q1: COGS Factor Units (%, ratio, per-unit?)
   Q2: Exact CM2 Formula & Tax-Basis Treatment
   
   Current Status: CM2 measures created but NOT VISUALIZED (see MEASURE_DICTIONARY.md)
   Expected Timeline: Finance confirmation within 1 week
   
   Do NOT use this page for business decisions until Q1-Q2 confirmed.
   ```

3. **Available fields table (informational only):**
   - Shows which measures exist: [CM2 Cr Provisional], [CM2 Pct Provisional], etc.
   - Shows which are BLOCKED: [COGS Cost Cr], [Profitability Status]
   - No charts or KPI cards

4. **Pending decisions table (from DATA_MODEL_DICTIONARY.md):**
   - Lists Q1, Q2, Q4, Q5 decisions
   - No visual interpretation of these yet

---

## SECTION 6: TEST & VALIDATE (60 MIN)

### 6.1: Data Quality Checks

**Open each page and verify:**
- ✓ All KPI cards show numbers (not #DIV/0! or #VALUE! errors)
- ✓ All charts render without errors
- ✓ Slicer selections filter visuals (test by selecting 1 chain, verify NSV updates)
- ✓ June'26 partial warning visible on relevant pages
- ✓ Tax-basis labels present (NSV "Excl Tax", MRP "Incl Tax")

**Expected value ranges:**
- **Total NSV (Apr'24–Jun'26):** ₹1,200–1,500 Cr
- **Total MRP (Apr'24–Jun'26):** ₹1,400–1,600 Cr
- **Total Qty (Apr'24–Jun'26):** 150–200 M units
- **Growth:** -20% to +30%

### 6.2: Functionality Checks

```
□ FY slicer: Click "FY26" → all visuals update to FY26 only
□ Month slicer: Click "Jun-26" → KPIs update, warning appears ("Partial")
□ Chain slicer: Click "Reliance" → metrics change to Reliance-only
□ Zone slicer: Click "NORTH-1" → data updates
□ Brand slicer: Works correctly
□ Category slicer: Works correctly
□ Drill-through (if configured): Click → navigates to detail page
□ Conditional formatting: Green/yellow/red colors appear on appropriate values
□ Tooltips: Hover over chart points → show details
```

### 6.3: Performance Checks

```
□ Dashboard loads in < 30 seconds
□ Slicer click → visual updates within 2 seconds
□ Refresh takes < 60 seconds (Home → Refresh)
□ No "out of memory" warnings
□ No red error icons in Fields pane or data model
```

### 6.4: QC Validation Checklist

**Use POWERBI_QC_VALIDATION_TEMPLATE.csv:**
1. For each page, check each measure value
2. Verify against source totals (from DATA_MODEL_DICTIONARY.md)
3. Compare with previous month (growth % should be reasonable)
4. Document any variances
5. Mark Pass/Fail

---

## SECTION 7: SAVE & FINALIZE (15 MIN)

### Step 7.1: Save File

1. **File → Save**
   - Filename: `MT_Offtake_Dashboard_Interim_MRP_NSV_Qty.pbix`
   - Location: `C:\PowerBI\` (or your preferred location)
2. **Wait for save to complete** (may take 30–60 seconds for 4.21M row model)

### Step 7.2: Backup

1. **Create backup copy:**
   - `MT_Offtake_Dashboard_Interim_MRP_NSV_Qty_BACKUP.pbix`
2. **Document your local path:** Save this for Phase 3 (Finance Q1-Q2 updates)

### Step 7.3: Export Model Diagram (Optional)

1. **Model tab → right-click blank area**
2. **Screenshot** (Ctrl+PrintScreen) or **Export as image**
3. Save as: `DataModel_Diagram_Built.png`

---

## SECTION 8: VALIDATION BEFORE HANDOFF

### Checklist: All Business Rules Preserved

Before returning to team:

```
✓ NSV labeled "(Excl Tax)" on all pages
✓ MRP labeled "(Incl Tax)" on all pages
✓ NSV/MRP comparisons show warning: "Different tax bases; QC/realization only"
✓ NO State slicer or State rollup anywhere
✓ NO BA profitability measures visualized
✓ NO More Retail deduplication (all rows retained)
✓ June'26 marked "Partial" with 78,111 row count
✓ Brand Counter shows BA availability only ([BA Available NSV Cr], [Non_BA Available NSV Cr])
✓ Page 9 remains QC/readiness only (NO CM2 visuals)
✓ All 84 measures present in Fields pane
✓ 5 relationships created (star schema)
✓ All pages load without errors
✓ Slicers work across all pages
```

### Final Validation Before Saving

Run through POWERBI_QC_VALIDATION_TEMPLATE.csv:
1. **Page 1:** KPI values correct?
2. **Page 2:** Chain ranking correct?
3. **Page 7:** BA metrics correct? (Provisional labels visible?)
4. **Page 10:** QC flags visible?
5. **All pages:** No State dimension, no BA profitability?

---

## SECTION 9: KNOWN ISSUES & TROUBLESHOOTING

### "Query took too long to load"
- **Cause:** 4.21M row fact table is large
- **Solution:** Wait 3–5 minutes on first load, or reduce to 12 months temporarily

### "Measure shows #DIV/0! or #VALUE!"
- **Cause:** Table name mismatch or missing data
- **Solution:** Check MEASURE_DICTIONARY.md, verify table names match exactly (case-sensitive)

### "Slicer doesn't filter charts"
- **Cause:** Relationship not created or inactive
- **Solution:** Model tab → Manage Relationships → Verify 5 relationships exist and are Active

### "Refresh is slow (>2 min)"
- **Cause:** External Excel file or network delay
- **Solution:** Ensure Expense_Assumptions_Input.xlsx is local (not network), not open in Excel

### "Import/Save fails"
- **Cause:** Disk space, permissions, or file corruption
- **Solution:** Free up 500 MB, restart Power BI, save with different filename

---

## SECTION 10: FINAL HANDOFF

### You now have:
1. ✅ Data model with 4.21M sales rows + dimensions + expense tracking
2. ✅ 84 DAX measures (Sales, Growth, Costs, QC flags)
3. ✅ 8 core pages (Pages 1–8) built and validated
4. ✅ 1 QC/readiness page (Page 9, holding for Finance)
5. ✅ 1 QC page (Page 10) with validation metrics

### Next step:
**When Finance provides Q1-Q2 answers:**
1. Update Expense_Assumptions_Input.xlsx with confirmed values
2. Update [CM2 Cr Provisional] formula in DAX
3. Build out Page 9 with profitability visuals
4. Re-run QC validation
5. Re-save .pbix

---

## Questions?
Refer to:
- **BUSINESS_RULES_FINAL.md** — Business context & rules
- **MEASURE_DICTIONARY.md** — What each measure means
- **DATA_MODEL_DICTIONARY.md** — What each field means
- **PAGE_BY_PAGE_BUILD_STEPS.md** — Visual specs for each page
- **KNOWN_BLOCKERS_AND_PENDING_DECISIONS.md** — What's blocked and why

**Estimated completion:** 5–7 hours (Pages 1–8, working with breaks)

