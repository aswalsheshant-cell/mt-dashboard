# Build BA Stores Performance & Provisional Profitability Page — Power BI Desktop Guide

**Branch:** claude/safe-powerbi-dashboard-rulings  
**Status:** v0 — Build guide (provisional, awaiting Finance validation)  
**Time estimate:** 2–3 hours (first-time implementation)  
**Prerequisite:** Power BI Desktop 2024.11+, completed Phases 1–5 from main build kit

---

## Overview

This guide walks through building a new Power BI page:
**"BA Stores Performance & Provisional Profitability"**

The page includes:
- 12 Executive KPIs (BA Sales, Costs, Profitability)
- 4 Trend & Comparison Charts (BA vs Non-BA analysis)
- 1 Interactive Store Profitability Matrix (19 columns, sortable/filterable)
- Conditional formatting for store classification & missing data flags
- External Excel input table for expense assumptions (fully refreshable, no hard-coded values)

**Key principle:** All expenses are managed in an external Excel file (`Expense_Assumptions_Input.xlsx`), not hard-coded in Power BI. This enables Finance to update assumptions without touching Power BI.

---

## Prerequisite: Prepare Expense_Assumptions_Input.xlsx

### Step 0a: Create Excel Seed File

**File location:** `PowerBI/SeedData/Expense_Assumptions_Input.xlsx`

**Sheet name:** "Assumptions"

**Columns (in order):**

```
A: Month (Date, YYYY-MM-01 format)
B: Chain (Text)
C: Store_Code (Text, if available; leave blank for now)
D: Store_Name (Text, optional reference)
E: Brand (Text)
F: BA_Salary (Currency, ₹)
G: BA_Supervisor_Cost (Currency, ₹)
H: Dmart_BA_Merchandiser_Cost (Currency, ₹)
I: Other_Employee_Cost (Currency, ₹)
J: Visibility_Cost (Currency, ₹)
K: Rental_Cost (Currency, ₹)
L: NPI_Listing_Cost (Currency, ₹)
M: TOT_Percentage (Decimal, %, e.g., 2.5 for 2.5%)
N: TOT_Value (Currency, ₹, leave blank if using %)
O: Promotional_Offer_Percentage (Decimal, %)
P: Promotional_Offer_Value (Currency, ₹)
Q: Claims_Reimbursements (Currency, ₹)
R: Other_Direct_Cost (Currency, ₹)
S: COGS_Rate (Decimal, factor or %, e.g., 0.1655)
T: COGS_Value (Currency, ₹)
U: Tax_Basis (Text, "Excl_Tax" / "Incl_Tax" / "Unknown")
V: Allocation_Method (Text, "Direct" / "By_Headcount" / "By_MRP_Share" / etc.)
W: Effective_From (Date)
X: Effective_To (Date, leave blank for ongoing)
Y: Data_Status (Text, "Actuals" / "Estimates" / "Pending" / "Provisional" / "Validated")
Z: Missing_Cost_Flag (Boolean, Y/N)
AA: Provisional_Cost_Flag (Boolean, Y/N)
AB: Mapping_Status (Text, "Mapped" / "Partial" / "Unmapped" / "Under_Review")
AC: Finance_Validation_Status (Text, "Awaiting" / "Confirmed" / "Rejected" / "Clarification_Needed")
AD: Last_Updated_Date (Date)
AE: Updated_By (Text)
AF: Source_File (Text)
AG: Remarks (Text)
```

### Step 0b: Populate Seed Data

**Sample rows from actual expense sheets (Apr-May-Jun 2026):**

| Month | Chain | Store_Code | Brand | BA_Salary | BA_Supervisor_Cost | Visibility_Cost | NPI_Listing_Cost | TOT_Percentage | Promotional_Offer_Percentage | Tax_Basis | Data_Status | Finance_Validation_Status | Remarks |
|-------|-------|-----------|-------|-----------|-------------------|-----------------|------------------|----------------|-------------------------------|-----------|-----------|------------------------|---------|
| 2026-04 | Reliance | (TBD) | Mamaearth | 15000 | 25000 | 5000 | 2500 | (blank) | 3.0 | Excl_Tax | Provisional | Awaiting | From Sheet 2 BA salary; TOT % pending |
| 2026-05 | Walmart | (TBD) | TDC | 12000 | 20000 | 4000 | (blank) | (blank) | 2.5 | Excl_Tax | Provisional | Awaiting | From Sheet 4 Dmart BA; Listing pending |
| 2026-06 | Amazon | (TBD) | AQ | 10000 | (blank) | 6000 | 1500 | (blank) | 3.5 | Excl_Tax | Provisional | Awaiting | From Sheet 5 other employ; TOT pending |

**Save as:** `PowerBI/SeedData/Expense_Assumptions_Input.xlsx`

**Commit to repo:** Yes (seed data for reproducibility)

---

## Phase 1: Load Expense_Assumptions_Input Table (10–15 min)

### Step 1a: Create Power Query Connection to Excel

1. **Open Power BI Desktop**
2. **Home tab → Get Data → Excel → Browse**
3. Navigate to `PowerBI/SeedData/Expense_Assumptions_Input.xlsx`
4. **Select worksheet:** "Assumptions"
5. **Click Load**

**Expected result:** `Expense_Assumptions_Input` table appears in Fields pane

### Step 1b: Verify & Configure Table

1. **Right-click table → Edit Query**
2. **Verify column types:**
   - Month: Date type
   - Chain: Text
   - Store_Code: Text
   - BA_Salary, BA_Supervisor_Cost, etc.: Currency (₹)
   - Percentages: Decimal (not percentage type)
   - Flags: Logical (Y/N converted to TRUE/FALSE)
   - Dates: Date type
3. **Remove** any blank rows at bottom
4. **Click Close & Apply**

**Verify in data model:**
- Table should have 32 columns
- At least 3–5 sample rows (Apr-May-Jun)
- No red error indicators

---

## Phase 2: Load Mapping Tables (Optional, if Store Master Available)

### Step 2a: Store Master Table (Pending Operations)

**If store_code → chain → zone mapping is available:**

1. **Create Power Query connection** to store master CSV/Excel
2. **Columns required:** Store_Code, Store_Name, Chain, Zone, BA_Deployment_Date
3. **Merge with Expense_Assumptions_Input** on Store_Code
4. **Note:** Store master is NOT available yet (marked as High-Priority blocker)

**For now:** Leave Store_Code column in Expense_Assumptions_Input as placeholder; populate once store master arrives.

---

## Phase 3: Create DAX Measures (45–60 min)

### Step 3a: Copy All Measures from BA_Profitability_DAX_Measures.dax

1. **Open** file: `PowerBI/Safe_Blocks/BA_Profitability_DAX_Measures.dax`
2. **Select all measures** (Ctrl+A)
3. **Copy to clipboard**
4. **In Power BI Desktop:**
   - **Right-click on Fact_Offtake_Safe table → New Measure**
5. **Paste measures into Power BI DAX editor**
   - Power BI will create individual measures for each
6. **Organize:** Move all measures to a single measure table or group them by category (optional; Power BI auto-organizes)

**Expected result:** 45+ new measures appear in Fields pane under Fact_Offtake_Safe (or new measure table)

### Step 3b: Validate Measures (Quick Test)

1. **Create a new page** (right-click sheet tab → New Page)
2. **Add KPI visual** to test a measure
3. **Select measure:** [BA_Store_NSV_Cr]
4. **Verify:** KPI shows value (not error)
5. **Add filter:** Drag Dim_Month[Month] to filters → Select single month
6. **Verify:** KPI updates (no hard-coded values)
7. **Delete test page** (not needed for final report)

---

## Phase 4: Create New Report Page (90–120 min)

### Step 4a: Add Page & Set Layout

1. **Right-click on sheet tab → New Page**
2. **Rename page:** "BA Stores Performance & Profitability"
3. **Set page size:** Design → Page size → Widescreen (16:9, 1920×1080)
4. **Add header text:** Insert → Text box
   ```
   BA STORES PERFORMANCE & PROVISIONAL PROFITABILITY
   (Provisional — Pending Finance Validation)
   ```
   - Font: Bold, 24pt, dark gray
   - Position: Top of page

### Step 4b: Create Section 1 — Executive KPIs (12 Cards)

**Cards to create:** BA Store NSV, Non-BA Store NSV, BA Store Growth, Incremental Sales, BA Cost, NPI Listing Cost, TOT Cost, Promo Cost, Visibility/Rental, Other Employee Cost, Provisional CM2, Provisional CM2%

**For each card:**

1. **Insert → Card visual**
2. **Fields:** Drag measure to card (e.g., [BA_Store_NSV_Cr])
3. **Format:**
   - Number format: ₹ Crore (2 decimals) or ₹ Lakh (2 decimals)
   - Background: White (light gray if provisional)
   - Title: Measure name + unit (e.g., "BA Store NSV — ₹ Crore")
   - Tooltip: Add label "Excluding Tax" or "Including Tax" where relevant

**Conditional formatting for provisional KPIs:**
- TOT Cost: If [TOT_Cost_Missing_Flag] = TRUE, show "⚠️ Pending" (yellow background)
- Promo Cost: If [Promotional_Cost_Missing_Flag] = TRUE, show "⚠️ Pending" (yellow background)
- Provisional CM2: Always yellow background (provisional status)
- Provisional CM2%: Always yellow background

**Layout:** Arrange in 2 columns × 3 rows (or 1 row × 6 columns depending on space)

**Add watermark text below KPIs:**
```
⚠️ PROVISIONAL: TOT, promotional, listing costs, and COGS unit are pending Finance validation.
```

### Step 4c: Create Section 2 — BA vs Non-BA Trend Chart

**Chart 1: Line Chart (BA vs Non-BA NSV over time)**

1. **Insert → Line chart**
2. **X-Axis:** Drag Dim_Month[Month_Label] or Dim_Month[Date]
3. **Y-Axis:** Add two measures:
   - [BA_Store_NSV_Cr] (blue line)
   - [Non_BA_Store_NSV_Cr] (gray line)
4. **Legend:** "BA Stores | Non-BA Stores"
5. **Format:**
   - Y-axis title: "NSV ₹ Crore (Excluding Tax)"
   - X-axis title: "Month"
   - Add data labels: Yes (show values on points)
6. **Tooltip:** Customize to show NSV, Qty, stores count, growth %
7. **Position:** Below KPI section, spanning ~60% width

**Add text box annotation:**
```
BA vs Non-BA Sales Trend
Blue line = BA-supported stores | Gray line = Non-BA stores
```

### Step 4d: Create Section 3 — Pre-BA vs Post-BA Comparison (Bar Chart)

**Chart 2: Clustered Bar Chart**

1. **Insert → Clustered Bar chart**
2. **Axis (Y):** Dim_Chain_Raw[Chain_Name]
3. **Values (X):** Add three measures:
   - [Pre_BA_Growth_Pct] (red bar)
   - [Post_BA_Growth_Pct] (green bar)
   - [Break_Even_Gap_Pct] (gray bar)
4. **Format:**
   - X-axis title: "Growth % | Break-even Gap %"
   - Legend: "Pre-BA Growth | Post-BA Growth | Break-even Gap"
   - Color scheme: Red / Green / Gray
5. **Position:** Right side of Section 2, ~40% width

### Step 4e: Create Section 4 — Store Profitability Matrix (19 Columns)

**This is the main interactive table.**

1. **Insert → Matrix/Table visual**
2. **Rows:** Add Dim_Chain_Raw[Chain_Name], then Store_Code (once available), then Store_Name
3. **Columns:** Dim_Month[Month_Label] (optional, for monthly breakdown)
4. **Values (column order):**
   ```
   1. [Store_NSV_Cr] — format ₹ Cr, 2 decimals
   2. [Store_Sales_Qty] — format Units (M), 1 decimal
   3. [Store_Growth_Pct] — format %, 1 decimal
   4. BA_Salary from Expense_Assumptions_Input — format ₹ Lakh
   5. BA_Supervisor_Cost — format ₹ Lakh
   6. NPI_Listing_Cost — format ₹ Lakh
   7. [TOT_Cost_Cr] × 100 (to Lakh) — format ₹ Lakh ⚠️ (conditional yellow if pending)
   8. [Promotional_Cost_Cr] × 100 — format ₹ Lakh ⚠️
   9. [Visibility_Rental_Cost_Cr] × 100 — format ₹ Lakh
   10. [Other_Employee_Cost_Cr] × 100 — format ₹ Lakh
   11. [Total_Support_Cost_Cr] × 100 — format ₹ Lakh, bold
   12. [Provisional_CM2_Cr] — format ₹ Cr, 2 decimals, yellow background ⚠️
   13. [Provisional_CM2_Pct] — format %, 1 decimal, yellow background ⚠️
   14. [Break_Even_Gap_Cr] — format ₹ Cr, 2 decimals
   15. [Store_Status] — format Text, conditional color (Green / Yellow / Orange / Red / Gray)
   16. [Recommendation_Status] — format Text, italic ("Under Review — Provisional")
   ```

5. **Format conditional coloring by Store_Status:**
   - "Strong Performer" → 🟢 Green background
   - "Monitor" → 🟡 Yellow background
   - "Improvement Required" → 🟠 Orange background
   - "Below Break-even" → 🔴 Red background
   - "Cost Data Pending" → ⚪ Gray background
   - "Insufficient History" → ⚪ Gray background

6. **Conditional formatting for Missing Costs:**
   - If [Total_Support_Cost_Missing_Flag] = TRUE → TOT & Promo columns: yellow background + "⚠️"
   - If [Missing_Data_Count] > 0 → Store Status: gray background

7. **Add sorting:** 
   - Sort by [Store_NSV_Cr] (descending) by default
   - Allow users to click column headers to resort

8. **Position:** Below Section 2 & 3, spanning full width

**Add column header explanations (tooltip on each):**
- NSV: "Net Sales Value, Excluding Tax (₹ Crore)"
- Qty: "Sales Quantity (units, millions)"
- Growth %: "Month-over-Month growth %"
- BA Salary / Supervisor / Listing / TOT / Promo / Visibility: "Cost component (₹ Lakh)"
- Total Support Cost: "Sum of all cost components (₹ Lakh)"
- CM2: "Contribution Margin 2 — Provisional, Pending Finance Validation ⚠️"
- CM2%: "CM2 as % of NSV — Provisional ⚠️"
- Break-even Gap: "Difference between actual NSV and break-even level (₹ Cr)"
- Store Status: "Classification based on profitability & growth — Provisional"
- Recommendation: "All recommendations blocked until Finance validates CM2"

### Step 4f: Add Slicers (Across All Visuals)

1. **Insert 6 slicers** (above KPI section or on right side):
   - **FY:** Dim_Month[FY], multi-select, default: current FY
   - **Month:** Dim_Month[Month_Label], multi-select, default: last 3 months
   - **Chain:** Dim_Chain_Raw[Chain_Name], multi-select, default: all chains
   - **Zone:** Dim_Zone[Zone_Name], multi-select, default: all zones
   - **Brand:** Dim_Category[Brand], multi-select, default: all brands
   - **BA Status:** Create custom slicer with values ("BA", "Non-BA", "All"), default: "All"

2. **Connect slicers to visuals:**
   - Select each visual → Format → Edit Interactions
   - Toggle slicer effects: On/Off as needed (e.g., BA Status slicer filters all visuals)

3. **Format slicers:**
   - Orientation: Horizontal (if space allows) or vertical
   - Style: Dropdown or list with search
   - Position: Top-right corner or sidebar

### Step 4g: Add Global Warning Banner

1. **Insert → Text box**
2. **Content:**
   ```
   ⚠️ PROVISIONAL PROFITABILITY: TOT, promotional offer costs, listing costs, 
      margins and selected expenses are pending validation. 
      
      Do NOT recommend closure or BA withdrawal until Finance confirms:
      - COGS factor units (Q1)
      - CM2 formula and tax-basis treatment (Q2)
      - TOT % or fixed value (Q4)
      - Promotional offer % or fixed value (Q5)
      
      Last updated: [insert measure [Last_Updated_Date]]
      Data status: Provisional — Pending Finance Validation
   ```
3. **Format:** Red or orange border, light yellow background, bold text
4. **Position:** Bottom of page

---

## Phase 5: Add Drill-Through Actions (Optional, 15–20 min)

### Step 5a: Create Store Detail Page (Secondary Page)

1. **Right-click sheet tab → New Page**
2. **Rename:** "Store Detail"
3. **Set as hidden:** Right-click tab → Hide (optional, only visible when drilling through)

### Step 5b: Add Drill-Through Fields to Main Table

1. **Select Store Profitability Matrix visual**
2. **Right-click Store row → Add drill-through page**
3. **Destination:** "Store Detail" page
4. **Pass fields:** Store_Code, Chain, Month

### Step 5c: Store Detail Page Layout

**Display fields:**
- Store Name (from Store_Master or Expense_Assumptions_Input)
- Chain, Zone, Store_Code
- BA Status & Deployment Date
- NSV (current month), Growth %
- Cost breakdown (BA salary, visibility, listing, TOT, promo, other)
- Provisional CM2 & CM2%
- Break-even gap & status
- Data quality (missing costs, validation status)
- 3-month trend chart (NSV, CM2 trajectory)

---

## Phase 6: Validation & Testing (30–45 min)

### Step 6a: Functional Testing

**Test Case 1: KPIs update when filter changes**
1. Slicer: Set Month = "Apr-26"
2. Verify: All KPIs recalculate (visually check that values change)
3. Slicer: Set Month = "May-26"
4. Verify: Values update (not cached from previous selection)

**Test Case 2: Missing costs are flagged (yellow) not zeroed**
1. In Expense_Assumptions_Input.xlsx, leave TOT_Percentage blank for Apr-26 Reliance
2. Refresh Power BI (Ctrl+Shift+R)
3. Verify: TOT Cost KPI shows "⚠️ Pending" (not ₹0)
4. Verify: Store Profitability table shows yellow highlight for that row's TOT column

**Test Case 3: Store status colors are correct**
1. Filter to a store with high NSV and low costs → Should show "Strong Performer" (green)
2. Filter to a store with NSV < Break-even → Should show "Below Break-even" (red)
3. Filter to a store with missing TOT/Promo data → Should show "Cost Data Pending" (gray)

**Test Case 4: Chart interactions work**
1. Click bar in Chart 2 (Pre-BA vs Post-BA) → should filter other visuals to that chain
2. Click data point in Trend chart → should drill through to store detail
3. Verify no orphaned selections (all visuals update coherently)

### Step 6b: Data Quality Checks

**Run QC validation:**
1. **Row Count:** Store Profitability matrix should show:
   - BA stores: [BA_Store_Count]
   - Non-BA stores: [Non_BA_Store_Count]
   - Total rows visible: sum of above
2. **NSV total:** Sum of all rows' NSV ≈ [BA_Store_NSV_Cr] + [Non_BA_Store_NSV_Cr]
3. **Cost total:** Sum of all rows' costs ≈ [BA_Total_Cost_Cr] + [Total_Support_Cost_Cr]
4. **CM2 total:** Sum of all rows' CM2 ≈ [Provisional_CM2_Cr]

**Check for anomalies:**
- Any negative NSV values? (Expected: some returns/credit notes, should be flagged separately)
- Any CM2% > 100%? (Suggests missing costs, not accounted for)
- Any CM2% with missing cost flag? (Should be grayed out or show "⚠️ Cannot calculate")

### Step 6c: Finance Validation Readiness

**Before sharing with Finance, verify:**
- [ ] All KPIs have "Provisional" or "⚠️ Pending" labels
- [ ] No hard-coded values in measures (all pull from Expense_Assumptions_Input)
- [ ] No final recommendations shown (Recommendation column = "Under Review — Provisional")
- [ ] Warning banner visible on page
- [ ] Missing cost flags are highlighted (not hidden)
- [ ] Last Updated date populated (from Expense_Assumptions_Input)

---

## Phase 7: Save & Commit (5 min)

### Step 7a: Save Power BI File

1. **File → Save As**
2. **Filename:** `MT_Dashboard_BA_Stores_Profitability_v0.pbix`
3. **Location:** `PowerBI/` root (not tracked in git; .pbix excluded)
4. **Note:** Only `.pq`, `.dax`, `.md`, and `.xlsx` seed files are tracked in git, not `.pbix` files

### Step 7b: Commit Specification Files to Git

```bash
git add PowerBI/Safe_Blocks/Expense_Assumptions_Input_Table.md
git add PowerBI/Safe_Blocks/BA_Stores_Profitability_Page_Spec.md
git add PowerBI/Safe_Blocks/BA_Profitability_DAX_Measures.dax
git add PowerBI/SeedData/Expense_Assumptions_Input.xlsx
git add PowerBI/Safe_Blocks/Build_BA_Page_Guide.md

git commit -m "Add BA Stores Profitability page specification & build guide (v0)

Provisional profitability page structure with:
- Expense_Assumptions_Input table structure (Excel-based, refreshable)
- BA_Stores_Profitability_Page_Spec.md (12 KPIs, 4 charts, 19-column matrix)
- BA_Profitability_DAX_Measures.dax (45+ measures, all provisional)
- Build_BA_Page_Guide.md (step-by-step Power BI Desktop build)
- Seed data: Expense_Assumptions_Input.xlsx (3-5 sample rows)

Status: v0 — Provisional, awaiting Finance validation of Q1-Q2
Blocked: Final CM2 formula, TOT %, Promotional %, COGS unit interpretation
Blocked: Store master (store_code → chain → zone), BA deployment list

Branch: claude/safe-powerbi-dashboard-rulings
PR: #14 (keep open, do not merge until Finance confirms)

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01CQGpGGfbd3arMdBNzJyPj9"
```

### Step 7c: Verify Commit

```bash
git status
# Should show all files committed, working directory clean
```

---

## Troubleshooting

### Issue: Measures show errors (#DIV/0! or #NAME?)

**Solution:**
1. Verify Expense_Assumptions_Input table is loaded (check Data pane)
2. Verify column names in table match measure references (case-sensitive)
3. Verify Fact_Offtake_Safe & Dim_Month tables exist and have expected columns
4. Refresh data: Ctrl+Shift+R
5. Check formula syntax: Measure → Edit → Review error line

### Issue: KPI shows "Pending" but I provided the cost in Excel

**Solution:**
1. Verify [Missing_Cost_Flag] is set to FALSE or blank in Excel row
2. Verify [Finance_Validation_Status] is set to "Confirmed"
3. Verify date range: Effective_From ≤ current filter month ≤ Effective_To
4. Refresh Power BI: Ctrl+Shift+R

### Issue: Store Status not showing correct color

**Solution:**
1. Verify [Store_Status] measure is applied to table visual
2. Verify conditional formatting rules are set (right-click table → Conditional formatting)
3. Check if [Total_Support_Cost_Missing_Flag] is overriding classification (gray takes precedence)
4. Manually test: Filter to a store with high NSV, low costs → should show "Strong Performer" (green)

### Issue: Slicers not filtering visuals

**Solution:**
1. Select each visual → Format → Edit Interactions
2. Toggle slicer effects: Verify "Filter" is selected (not "None" or "Highlight")
3. Verify slicer values are available in data (e.g., if Month slicer has no Apr-26, won't show)

### Issue: Excel file won't refresh in Power BI

**Solution:**
1. Close Excel file (Power BI cannot read locked files)
2. In Power BI: Home → Refresh (or Ctrl+Shift+R)
3. If still fails: Right-click query → Edit → Verify file path is correct
4. Resave Excel file: File → Save (ensure no unsaved changes)

---

## Next Steps After Build

### Immediate (Once Page is Built)

1. **Share page with Finance team** for review & feedback
2. **Request Q1-Q2 answers** (COGS unit, CM2 formula)
3. **Request Q4-Q5 answers** (TOT %, Promotional %)
4. **Request store master** from Operations (once available)

### Once Finance Answers Q1-Q2

1. **Update [COGS_Cost_Cr] measure** based on Q1 interpretation
2. **Update [Provisional_CM2_Cr] measure** with exact Q2 formula
3. **Rename measures:** Remove "Provisional_" prefix
4. **Remove yellow ⚠️ from CM2 KPIs** (status changed to "Validated")
5. **Unhide recommendation columns:** Withdrawal, Closure, ROI, Payback
6. **Update [Recommendation_Status]:** Replace "Under Review" with actual recommendations
7. **Retest:** Full validation pass

### Once Operations Provides Store Master

1. **Load store master table** via Power Query
2. **Merge with Expense_Assumptions_Input** on Store_Code
3. **Add Zone & BA_Deployment_Date** to Store Profitability matrix
4. **Enable drill-through:** Store detail page with store-specific analysis
5. **Retest:** Drill-through actions, store classification accuracy

### Once All Data is Ready (6+ months post-BA)

1. **Unlock recommendation logic:** BA withdrawal, closure, ROI, payback
2. **Implement comparable-store analysis:** Pre-BA vs post-BA statistical testing
3. **Add forecasting:** Trend projections based on 6-month history
4. **Archive provisional model:** Tag as "v0 — Validated" once confirmed

---

## Files Reference

| File | Location | Purpose | Status |
|------|----------|---------|--------|
| Expense_Assumptions_Input_Table.md | `PowerBI/Safe_Blocks/` | Input table structure & design rules | v0 |
| BA_Stores_Profitability_Page_Spec.md | `PowerBI/Safe_Blocks/` | Detailed page design (12 KPIs, 4 charts, 19-column matrix) | v0 |
| BA_Profitability_DAX_Measures.dax | `PowerBI/Safe_Blocks/` | 45+ DAX measures (all provisional) | v0 |
| Build_BA_Page_Guide.md (this file) | `PowerBI/Safe_Blocks/` | Step-by-step Power BI build instructions | v0 |
| Expense_Assumptions_Input.xlsx | `PowerBI/SeedData/` | Seed data (sample 3-5 rows) | Create |
| MT_Dashboard_BA_Stores_Profitability_v0.pbix | `PowerBI/` (not tracked) | Power BI file (build output, .pbix excluded from git) | Create |

---

## Status & Compliance

- **Branch:** claude/safe-powerbi-dashboard-rulings
- **Status:** v0 — Build guide (ready for implementation)
- **PR:** #14 (keep open, do not merge until Finance confirms Q1-Q2)
- **Blocked items:** Final CM2, TOT %, Promotional %, COGS unit, store master, BA deployment list
- **Provisional flag:** All CM2, profitability, and recommendations labeled "Pending Finance Validation"

**Compliance checklist:**
- ✓ No final recommendations shown
- ✓ No hard-coded expense values
- ✓ All costs refreshable from external Excel
- ✓ Missing costs flagged (not zeroed)
- ✓ Warning banner visible on all visuals
- ✓ Drill-through to store detail available
- ✓ Conditional formatting for store classification
- ✓ Data quality flags (provisional cost, missing data)

---

**Ready to build. Follow Phases 1–7. Estimated 2–3 hours. Good luck!**

