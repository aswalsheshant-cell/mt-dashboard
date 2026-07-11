# BA Stores Performance & Provisional Profitability — Page Specification

**Branch:** claude/safe-powerbi-dashboard-rulings  
**Status:** v0 — Page design (provisional, awaiting Finance validation of CM2 formula & cost data)  
**Generated:** 2026-07-11  
**Page Type:** Multi-tab analysis + Store Profitability matrix

---

## Overview

This new page provides:

1. **Executive KPI cards** (12 metrics) — BA vs Non-BA sales, cost breakdown, provisional CM2
2. **BA vs Non-BA Trend Analysis** — Line charts showing sales/profitability pre-BA vs post-BA
3. **Store Profitability Matrix** — Interactive table (19 columns) with drill-down by chain/zone/store/brand
4. **Store Classification** — Conditional formatting labels (Strong Performer, Monitor, Improvement Required, etc.)
5. **Editable Input Integration** — All expenses linked to external Excel table, refreshable without Power BI edits

**Key Principle:** All displays are labeled "Provisional — Pending Finance Validation." No final recommendations until Finance confirms Q1-Q2.

---

## Layout & Visuals

### Page Structure

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      BA STORES PERFORMANCE & PROVISIONAL PROFITABILITY      │
│                          (Provisional — Pending Finance Validation)         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  SECTION 1: EXECUTIVE KPIs (Top Row)                                         │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┬──────────┐        │
│  │ BA Store │Non-BA    │ BA Store │Incremental│ BA Cost │ NPI      │        │
│  │ NSV      │ Store NSV│ Growth  │ Sales    │ Cr      │Listing   │        │
│  │ ₹Cr      │ ₹Cr      │ %       │ ₹Cr      │         │Cost ₹Lakh│        │
│  └──────────┴──────────┴──────────┴──────────┴──────────┴──────────┘        │
│                                                                               │
│  SECTION 2: COST BREAKDOWN KPIs (2nd Row)                                    │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┬──────────┐        │
│  │ TOT Cost │Promo     │Visibility│Other Emp │ Prov.    │ Prov.    │        │
│  │ ₹Lakh    │Cost      │/Rental   │Cost      │ CM2      │ CM2%     │        │
│  │ ⚠️ Pending│₹Lakh ⚠️ |₹Lakh     │₹Lakh     │₹Cr ⚠️   │ % ⚠️     │        │
│  └──────────┴──────────┴──────────┴──────────┴──────────┴──────────┘        │
│                                                                               │
│  SECTION 3: BA EFFICIENCY & BREAK-EVEN                                       │
│  ┌──────────┬──────────┬──────────┐                                          │
│  │ Cost per │ Sales per│Break-even│                                          │
│  │ BA Store │ BA       │ Sales    │                                          │
│  │ ₹Lakh    │ ₹Cr      │₹Cr ⚠️   │                                          │
│  └──────────┴──────────┴──────────┘                                          │
│                                                                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  SECTION 4: BA vs NON-BA ANALYSIS (Mid Section)                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ Chart 1: BA vs Non-BA NSV Trend (Line, X: Month, Y: ₹Cr)            │   │
│  │ Slicers: FY | Month | Chain | Zone | Brand | Category               │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                               │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ Chart 2: Pre-BA vs Post-BA Performance Comparison (Bar, by chain)   │   │
│  │ Metrics: NSV Growth %, Break-even Status                             │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                               │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ Chart 3: Comparable-Store Growth (Scatter: Prior Month NSV vs Current)   │   │
│  │ Bubble size: Provisional CM2; Color: Store Status                   │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                               │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ Chart 4: Performance by Dimension (Breakdown by chain/zone/brand)   │   │
│  │ (Drill-down matrix)                                                  │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  SECTION 5: STORE PROFITABILITY TABLE (Interactive, Sortable, Drillable)   │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ (19-column matrix table — see detailed spec below)                  │   │
│  │ Rows: Chain | Store Code | Store Name | BA Status | Deployment Date   │   │
│  │ Columns: NSV | Qty | Growth | Costs (salary, supervisor, listing,   │   │
│  │          TOT, promo, visibility, other) | Total Cost | Prov. CM2 |   │   │
│  │          CM2% | Break-even Gap | Store Status | Recommendation      │   │
│  │                                                                       │   │
│  │ Sorting: By NSV (desc), By Prov. CM2 (desc), By Status              │   │
│  │ Filtering: BA Status (BA / Non-BA / All), Chain, Zone, Month, Brand │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                               │
│  ⚠️ GLOBAL WARNING (footer)                                                  │
│  "Provisional profitability: TOT, promotions, listing costs, margins and   │
│  selected expenses are pending validation. Do not recommend closure or      │
│  BA withdrawal until Finance confirms the CM2 formula and tax basis."       │
│                                                                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Detailed Visual Specifications

### SECTION 1: EXECUTIVE KPIs (12 Metrics)

**Layout:** 6 cards in top row (2 columns × 3 rows, or 1 row × 6 cards)

#### KPI 1: BA Store NSV (₹ Crore)

```
┌────────────────────┐
│  BA Store NSV      │
│    ₹ Crore         │
│                    │
│     1,234.56       │  ← Large font, bold
│                    │
│ Excl. Tax | Apr-Jun│
└────────────────────┘
```

- **Measure:** [BA_Store_NSV_Cr] (filter Fact_Offtake_Safe where BA_Available = "Yes")
- **Label:** "BA Store NSV — Excluding Tax"
- **Format:** ₹ Crore, 2 decimals
- **Drill-through:** Click → detail by Store Name

#### KPI 2: Non-BA Store NSV (₹ Crore)

```
┌────────────────────┐
│ Non-BA Store NSV   │
│   ₹ Crore          │
│                    │
│      567.89        │
│                    │
│ Excl. Tax | Apr-Jun│
└────────────────────┘
```

- **Measure:** [Non_BA_Store_NSV_Cr] (filter BA_Available = "No")
- **Label:** "Non-BA Store NSV — Excluding Tax"
- **Format:** ₹ Crore, 2 decimals

#### KPI 3: BA Store Growth (%)

```
┌────────────────────┐
│ BA Store Growth    │
│        %           │
│                    │
│      +12.5%        │  ← Green if positive
│                    │
│ MoM / YoY (toggle) │
└────────────────────┘
```

- **Measure:** [BA_Store_Growth_Pct] = (Current Month NSV - Prior Month NSV) / Prior Month NSV × 100
- **Label:** "BA Store Growth % (Month-over-Month)"
- **Format:** Percentage, 1 decimal
- **Conditional formatting:** Green if >0, Red if <0

#### KPI 4: Incremental Sales (₹ Crore)

```
┌────────────────────┐
│ Incremental Sales  │
│   ₹ Crore          │
│                    │
│      234.56        │
│                    │
│ BA Attribution     │
└────────────────────┘
```

- **Measure:** [Incremental_Sales_Cr] = (BA_Store_NSV_Cr × BA_Growth_Pct) + (BA_Store_NSV_Cr × Attribution_Multiplier)
- **Note:** Attribution logic TBD by Finance (how much growth is BA-driven vs. organic/market)
- **Label:** "Incremental Sales — BA Attribution (Provisional)"
- **Format:** ₹ Crore, 2 decimals

#### KPI 5: BA Cost (₹ Crore)

```
┌────────────────────┐
│  BA Cost           │
│   ₹ Crore          │
│                    │
│      0.45          │
│                    │
│ Salary + Supv      │
└────────────────────┘
```

- **Measure:** [BA_Total_Cost_Cr] = ([BA_Salary_Lakhs] + [BA_Supervisor_Lakhs] + [BA_Merchandiser_Lakhs]) ÷ 100
- **Label:** "BA Cost — Salary, Supervisor, Merchandiser (₹ Crore)"
- **Format:** ₹ Crore, 4 decimals
- **Sub-label:** Sum of Sheets 2, 3, 4 from Expense_Assumptions_Input

#### KPI 6: NPI Listing Cost (₹ Lakh)

```
┌────────────────────┐
│ NPI Listing Cost   │
│   ₹ Lakh           │
│                    │
│      45.25         │
│                    │
│ Total | Pending    │
└────────────────────┘
```

- **Measure:** [NPI_Listing_Cost_Lakhs] = SUM([NPI_Listing_Cost]) from Expense_Assumptions_Input, converted to Lakhs
- **Label:** "NPI Listing Cost — ₹ Lakh (Pending: Some stores not yet charged)"
- **Format:** ₹ Lakh, 2 decimals
- **Flag:** If [Missing_Cost_Flag] = Y, show ⚠️ icon and tooltip "Listing cost data pending for X stores"

---

### SECTION 2: COST BREAKDOWN KPIs (6 Metrics)

#### KPI 7: TOT Cost (₹ Lakh) ⚠️

```
┌────────────────────┐
│  TOT Cost          │
│   ₹ Lakh           │
│                    │
│    ⚠️ Pending      │  ← Yellow highlight
│                    │
│ Awaiting Q4 Answer │
└────────────────────┘
```

- **Measure:** [TOT_Cost_Lakhs] (from Expense_Assumptions_Input, using TOT_Percentage or TOT_Value)
- **Label:** "Trade-off-Trade Cost — ₹ Lakh ⚠️ (Pending % from business)"
- **Format:** ₹ Lakh, 2 decimals OR "Pending" text
- **Conditional formatting:** 
  - If `Missing_Cost_Flag = Y` → Yellow background + "⚠️ Pending"
  - If `Finance_Validation_Status = "Awaiting"` → Italic + gray text
- **Tooltip:** "TOT % not yet provided by business. Set Missing_Cost_Flag = Y in Expense_Assumptions_Input until confirmed."

#### KPI 8: Promotional Cost (₹ Lakh) ⚠️

```
┌────────────────────┐
│ Promotional Cost   │
│   ₹ Lakh           │
│                    │
│    ⚠️ Pending      │
│                    │
│ Awaiting Q5 Answer │
└────────────────────┘
```

- **Measure:** [Promotional_Cost_Lakhs] (from Expense_Assumptions_Input)
- **Label:** "Promotional Offer Cost — ₹ Lakh ⚠️ (Pending % from business)"
- **Format:** ₹ Lakh, 2 decimals OR "Pending"
- **Conditional formatting:** Same as TOT (yellow + italic if pending)

#### KPI 9: Visibility/Rental Cost (₹ Lakh)

```
┌────────────────────┐
│ Visibility/Rental  │
│ Cost               │
│   ₹ Lakh           │
│                    │
│      12.50         │
│                    │
│ From Sheet 6       │
└────────────────────┘
```

- **Measure:** [Visibility_Rental_Cost_Lakhs] = ([Visibility_Cost] + [Rental_Cost]) from Expense_Assumptions_Input, converted to Lakhs
- **Label:** "Visibility & Rental Cost — ₹ Lakh"
- **Format:** ₹ Lakh, 2 decimals
- **Source:** Sheet 6 visibility or Rental

#### KPI 10: Other Employee Cost (₹ Lakh)

```
┌────────────────────┐
│ Other Employee     │
│ Cost               │
│   ₹ Lakh           │
│                    │
│       8.75         │
│                    │
│ Operations, etc.   │
└────────────────────┘
```

- **Measure:** [Other_Employee_Cost_Lakhs] (from Sheet 5, converted to Lakhs)
- **Label:** "Other Employee Cost — ₹ Lakh (Operations, Support Staff)"
- **Format:** ₹ Lakh, 2 decimals

#### KPI 11: Provisional CM2 (₹ Crore) ⚠️

```
┌────────────────────┐
│ Provisional CM2    │
│   ₹ Crore          │
│                    │
│    ⚠️ 234.50       │  ← Yellow warning
│                    │
│ Pending Finance    │
│ Validation         │
└────────────────────┘
```

- **Measure:** [Provisional_CM2_Cr]
  ```
  = ([BA_Store_NSV_Cr] - [BA_Cost_Cr] - [NPI_Listing_Cost_Cr] 
     - [TOT_Cost_Cr] - [Promotional_Cost_Cr] - [Visibility_Rental_Cost_Cr] 
     - [Other_Employee_Cost_Cr] - [COGS_Cost_Cr])
  ```
- **Label:** "Provisional CM2 — ₹ Crore ⚠️ (Pending Finance Validation)"
- **Format:** ₹ Crore, 2 decimals
- **Conditional formatting:** Yellow background (indicating provisional status)
- **Tooltip:** "CM2 formula pending Finance confirmation of Q1 & Q2. Do not use for final decisions."

#### KPI 12: Provisional CM2% ⚠️

```
┌────────────────────┐
│ Provisional CM2%   │
│       %            │
│                    │
│    ⚠️ 18.9%        │
│                    │
│ Pending Finance    │
│ Validation         │
└────────────────────┘
```

- **Measure:** [Provisional_CM2_Pct] = [Provisional_CM2_Cr] / [BA_Store_NSV_Cr] × 100
- **Label:** "Provisional CM2% ⚠️ (Pending Finance Validation)"
- **Format:** Percentage, 1 decimal
- **Conditional formatting:** Yellow background

---

### SECTION 3: BA EFFICIENCY & BREAK-EVEN (3 Metrics)

#### KPI 13: Cost per BA Store (₹ Lakh)

```
┌────────────────────┐
│ Cost per BA Store  │
│   ₹ Lakh           │
│                    │
│      3.20          │
│                    │
│ Avg. by Store      │
└────────────────────┘
```

- **Measure:** [Cost_Per_BA_Store_Lakh] = [BA_Total_Cost_Lakhs] / DISTINCTCOUNT(Store_Code) where BA_Status = "BA"
- **Label:** "Average Cost per BA-Supported Store — ₹ Lakh"
- **Format:** ₹ Lakh, 2 decimals

#### KPI 14: Sales per BA (₹ Crore)

```
┌────────────────────┐
│ Sales per BA       │
│   ₹ Crore          │
│                    │
│      0.78          │
│                    │
│ NSV / BA Headcount │
└────────────────────┘
```

- **Measure:** [Sales_Per_BA_Cr] = [BA_Store_NSV_Cr] / [BA_Headcount]
- **Label:** "Average Sales per BA — ₹ Crore (NSV / BA Headcount)"
- **Format:** ₹ Crore, 3 decimals
- **Note:** BA Headcount from Expense_Assumptions_Input (count of distinct employees with BA role)

#### KPI 15: Break-even Sales (₹ Crore) ⚠️

```
┌────────────────────┐
│ Break-even Sales   │
│   ₹ Crore          │
│                    │
│    ⚠️ 0.65         │
│                    │
│ At Current Costs   │
└────────────────────┘
```

- **Measure:** [Break_Even_Sales_Cr] = ([BA_Cost_Cr] + [NPI_Listing_Cost_Cr] + [TOT_Cost_Cr] + [Promotional_Cost_Cr] + [Visibility_Rental_Cost_Cr] + [Other_Employee_Cost_Cr]) × (100 / [Provisional_CM2_Pct])
- **Label:** "Break-even Sales — ₹ Crore ⚠️ (Pending CM2 Formula Confirmation)"
- **Format:** ₹ Crore, 3 decimals
- **Conditional formatting:** Yellow (provisional)
- **Interpretation:** Sales level at which CM2 = 0. If actual NSV < Break-even, store is below break-even.

---

### SECTION 4: BA vs NON-BA ANALYSIS (Charts)

#### Chart 1: BA vs Non-BA NSV Trend (Line Chart)

```
X-Axis: Month (Apr'26, May'26, Jun'26, ...)
Y-Axis: NSV ₹ Crore (Excluding Tax)
Lines:
  - BA Store NSV (blue)
  - Non-BA Store NSV (gray)
Legend: "BA Stores | Non-BA Stores"
Slicers: FY | Month | Chain | Zone | Brand | Category
```

**Measures:**
- [BA_Store_NSV_Cr] (blue line)
- [Non_BA_Store_NSV_Cr] (gray line)

**Interactivity:**
- Hover over data point → tooltip shows NSV, Qty, stores count
- Click on legend item → toggle series visibility

---

#### Chart 2: Pre-BA vs Post-BA Performance Comparison (Clustered Bar)

```
X-Axis: Chain (Reliance, Walmart, Amazon, ...)
Y-Axis: NSV Growth % & Break-even Status
Bars:
  - Pre-BA Growth % (red)
  - Post-BA Growth % (green)
  - Break-even Gap % (gray)
```

**Measures:**
- [Pre_BA_Growth_Pct] (red bar)
- [Post_BA_Growth_Pct] (green bar)
- [Break_Even_Gap_Pct] = (Actual NSV - Break-even NSV) / Break-even NSV × 100 (gray bar)

**Interactivity:**
- Drill-down by Zone, then Store
- Show store names in tooltip

---

#### Chart 3: Comparable-Store Growth (Scatter Plot)

```
X-Axis: Prior Month NSV (₹ Crore)
Y-Axis: Current Month NSV (₹ Crore)
Bubble Size: Provisional CM2 (₹ Crore)
Bubble Color: Store Status (Strong Performer = Green, Monitor = Yellow, Improvement = Orange, Below Break-even = Red)
```

**Measures:**
- X: [Prior_Month_NSV_Cr]
- Y: [Current_Month_NSV_Cr]
- Size: [Provisional_CM2_Cr]
- Color: [Store_Status] (conditional formatting)

**Interactivity:**
- Hover → tooltip shows Store Name, Chain, NSV change %, CM2
- Click store bubble → drill-through to store detail page

---

#### Chart 4: Performance by Dimension (Drill-down Matrix)

```
Rows: 
  - Level 1: Chain (Reliance, Walmart, Amazon, ...)
  - Level 2: Zone (expand chain)
  - Level 3: Store (expand zone)
Columns:
  - NSV (₹ Cr)
  - Growth %
  - BA Status (BA / Non-BA)
  - Prov. CM2 (₹ Cr)
  - CM2% 
  - Store Status

Sorting: By NSV (desc) or by CM2 (desc)
Filtering: BA Status, Chain, Zone, Month
```

**Interactivity:**
- Expand/collapse chain → show zones → show stores
- Click store row → drill-through to store detail table (Section 5)

---

### SECTION 5: STORE PROFITABILITY TABLE (19 Columns)

**Visual Type:** Matrix or Table with conditional formatting + drill-through

**Primary Key:** (Month, Chain, Store_Code, Brand)  
**Rows:** Distinct combinations of Store_Code, Store_Name, Chain, BA_Status, BA_Deployment_Date

**Columns (in order):**

| # | Column | Data Type | Format | Measure / Source | Editable? | Notes |
|---|--------|-----------|--------|------------------|-----------|-------|
| 1 | Chain | Text | — | Dim_Chain_Raw | No | From Fact_Offtake_Safe |
| 2 | Store_Code | Text | — | (from store master, pending) | No | Unique identifier |
| 3 | Store_Name | Text | — | (from store master, pending) | No | Lookup from Store_Code |
| 4 | BA_Status | Text | — | "BA" / "Non-BA" | No | Derived from BA_Deployment_Date |
| 5 | BA_Deployment_Date | Date | YYYY-MM-DD | (from store master, pending) | Yes | Operations input |
| 6 | NSV | Currency | ₹ Cr | [Store_NSV_Cr] | No | From Fact_Offtake_Safe |
| 7 | Quantity | Number | Units (millions) | [Store_Sales_Qty] ÷ 1M | No | From Fact_Offtake_Safe |
| 8 | Growth % | Decimal | % | [Store_Growth_Pct] = (Current - Prior) / Prior × 100 | No | Calculated |
| 9 | BA Salary | Currency | ₹ Lakh | [Store_BA_Salary] from Expense_Assumptions_Input | Yes | Excel-editable |
| 10 | Supervisor Cost | Currency | ₹ Lakh | [Store_BA_Supervisor_Cost] | Yes | Excel-editable |
| 11 | Listing Cost | Currency | ₹ Lakh | [Store_NPI_Listing_Cost] | Yes | Excel-editable |
| 12 | TOT Cost | Currency | ₹ Lakh | [Store_TOT_Cost] ⚠️ | Yes | Excel-editable; Pending % |
| 13 | Promotional Cost | Currency | ₹ Lakh | [Store_Promotional_Cost] ⚠️ | Yes | Excel-editable; Pending % |
| 14 | Visibility/Rental | Currency | ₹ Lakh | [Store_Visibility_Rental_Cost] | Yes | Excel-editable |
| 15 | Other Direct Cost | Currency | ₹ Lakh | [Store_Other_Employee_Cost] | Yes | Excel-editable |
| 16 | Total Support Cost | Currency | ₹ Lakh | Sum(cols 9-15) | No | Calculated |
| 17 | Provisional CM2 | Currency | ₹ Cr | [Store_Provisional_CM2_Cr] = NSV - Total Support Cost | No | Calculated ⚠️ |
| 18 | CM2% | Decimal | % | [Store_CM2_Pct] = CM2 / NSV × 100 | No | Calculated ⚠️ |
| 19 | Break-even Gap | Currency | ₹ Cr | [Store_Break_Even_Gap_Cr] = Store_NSV - [Break_Even_Sales] | No | Calculated ⚠️ |
| 20 | Store Status | Text | — | [Store_Status] (conditional formula) | No | Provisionally classified |
| 21 | Recommendation | Text | — | "Under Review" (all for now) | No | Blocked until Finance confirms |

---

## Store Classification Logic

**Classification is PROVISIONAL only.** No final recommendations until Finance confirms CM2 formula.

### Conditional Rules

```
IF [Break_Even_Gap_Cr] < -0.1 Cr
  THEN "Below Break-even" (Red background)
  
ELSE IF [Break_Even_Gap_Cr] BETWEEN -0.1 AND 0 Cr
  THEN "Improvement Required" (Orange background)
  
ELSE IF [Provisional_CM2_Pct] < 5%
  THEN "Monitor" (Yellow background)
  
ELSE IF [Provisional_CM2_Pct] >= 15% AND [Store_Growth_Pct] > 10%
  THEN "Strong Performer" (Green background)
  
ELSE IF [Store_Status] IN ("Below Break-even", "Improvement Required")
  AND [Missing_Cost_Flag] = Y
  THEN "Cost Data Pending" (Gray background) — OVERRIDE above
  
ELSE IF [Data_Status] = "Pending" OR [Finance_Validation_Status] = "Awaiting"
  THEN "Cost Data Pending" (Gray background) — OVERRIDE above
  
ELSE IF [Provisional_Cost_Flag] = Y
  THEN Status + " (Provisional)" suffix — show status but note provisional
  
ELSE
  "Monitor" (Yellow) — default if no condition matches
```

### Status Labels (Non-Editable, Provisional)

| Label | Condition | Color | Meaning | Action |
|-------|-----------|-------|---------|--------|
| **Strong Performer** | CM2% ≥ 15% & Growth > 10% & No missing costs | 🟢 Green | High profitability + growth | Monitor for sustainability |
| **Monitor** | CM2% BETWEEN 5–15% | 🟡 Yellow | Acceptable but watch closely | Monthly review |
| **Improvement Required** | Break-even Gap BETWEEN -0.1 & 0 Cr | 🟠 Orange | Close to break-even | Support with promotion/visibility |
| **Below Break-even** | Break-even Gap < -0.1 Cr | 🔴 Red | Operating at loss | Investigation needed (cost/sales driven?) |
| **Cost Data Pending** | Missing_Cost_Flag = Y | ⚪ Gray | Cannot classify until costs provided | Request missing data from Finance/Operations |
| **Insufficient History** | Store active < 3 months OR < 3 data points | ⚪ Gray | Too early to assess | Wait for stable data pattern |

---

## Recommendation Status (Blocked)

**All stores show:** `"Under Review — Provisional"` (not editable, displayed in italics)

**Recommendation field cannot be populated until:**
1. ✓ Store master is complete (store_code → chain → zone → location)
2. ✓ BA deployment list is confirmed (which stores have BA, when deployed)
3. ✓ Finance answers Q1-Q2 (COGS unit, CM2 formula, tax-basis)
4. ✓ Finance provides TOT %, Promotional % (Q4-Q5)
5. ✓ 6+ months of post-BA data available (comparable-store analysis)

**Blocked recommendations:**
- ❌ "Withdraw BA" (cannot recommend without 6+ months post-BA data)
- ❌ "Close Store" (cannot recommend without full cost/sales history)
- ❌ "Expand BA to X stores" (cannot recommend without Finance validation)
- ❌ ROI calculation, payback period (blocked until Finance confirms CM2)

---

## Global Warning (Footer, All Sections)

**Visible on every screen (top + bottom):**

```
⚠️ PROVISIONAL PROFITABILITY: TOT, promotional offer costs, listing costs, 
   margins and selected expenses are pending validation. 

   Do NOT recommend closure or BA withdrawal until Finance confirms:
   - COGS factor units (Q1)
   - CM2 formula and tax-basis treatment (Q2)
   - TOT % or fixed value (Q4)
   - Promotional offer % or fixed value (Q5)

   Last updated: [Last_Updated_Date from Expense_Assumptions_Input]
   Data status: Provisional — Pending Finance Validation
```

---

## Slicers & Filtering

**Applied to all visuals (Sections 1-5):**

| Slicer | Data Source | Multi-Select | Default |
|--------|-------------|--------------|---------|
| **FY** | Dim_Month[FY] | ✓ Yes | Current FY (FY26) |
| **Month** | Dim_Month[Month_Label] | ✓ Yes | Current month |
| **Chain** | Dim_Chain_Raw[Chain_Name] | ✓ Yes | All chains |
| **Zone** | Dim_Zone[Zone_Name] | ✓ Yes | All zones |
| **Brand** | Fact_Offtake_Safe[Brand] | ✓ Yes | All brands |
| **Category** | Dim_Category[Category] | ✓ Yes | All categories |
| **BA Status** | ("BA", "Non-BA", "All") | ✗ No | "All" (default: show both) |
| **Store Status** | [Store_Status] | ✓ Yes | All statuses |

---

## Drill-Through Actions

**Clicking on a store row → Navigate to:**

**Store Detail Page (new page or tooltip):**
```
Store Name: Reliance Thane Store 1
Store Code: REL-001
Chain: Reliance
Zone: WEST-1
BA Status: BA (deployed 2026-04-15)

Sales History:
  Apr'26 NSV: ₹1.5 Cr
  May'26 NSV: ₹1.6 Cr
  Jun'26 NSV: ₹1.7 Cr
  Growth: +13.3%

Cost Breakdown:
  BA Salary: ₹0.15 Lakh
  Visibility: ₹0.05 Lakh
  Listing: ₹0.025 Lakh
  TOT: ⚠️ Pending
  Promo: ⚠️ Pending
  Total: ₹0.225 Lakh

Profitability:
  NSV: ₹1.6 Cr
  Total Cost: ₹0.225 Lakh (= ₹0.00225 Cr)
  Prov. CM2: ₹1.5975 Cr
  CM2%: 99.8% ⚠️ (implausible — awaiting TOT/Promo data)
  Break-even: ₹0.23 Lakh equivalent NSV
  Gap: ₹1.6 Cr (far above break-even)
  Status: "Strong Performer" (provisional)

Data Quality:
  Missing Costs: TOT %, Promotional %
  Last Updated: 2026-07-11
  Status: "Cost Data Pending"
```

---

## Power BI Build Checklist

- [ ] Load Expense_Assumptions_Input via Power Query (external Excel)
- [ ] Create 12 Executive KPI measures (all with ⚠️ labels where provisional)
- [ ] Create Chart 1: BA vs Non-BA Trend (line)
- [ ] Create Chart 2: Pre-BA vs Post-BA Comparison (bar)
- [ ] Create Chart 3: Comparable-Store Growth (scatter)
- [ ] Create Chart 4: Performance by Dimension (drill-down matrix)
- [ ] Create Store Profitability Table (19 columns)
- [ ] Add conditional formatting for Store Status colors
- [ ] Add conditional formatting for Missing Cost highlights (yellow)
- [ ] Add conditional formatting for Provisional Cost (italic + gray)
- [ ] Add slicers: FY, Month, Chain, Zone, Brand, Category, BA Status
- [ ] Add global warning banner (top + bottom)
- [ ] Add drill-through to store detail page
- [ ] Test refresh: Update Expense_Assumptions_Input.xlsx in Excel → Refresh Power BI → Verify KPIs update
- [ ] Validate: No final CM2 recommendations shown (all labeled "Pending Finance Validation")

---

## Files to Create / Reference

| File | Type | Status | Purpose |
|------|------|--------|---------|
| `Expense_Assumptions_Input.xlsx` | Excel | Create (seed) | Editable input table |
| `PowerQuery_Expense_Assumptions.pq` | Power Query | Create | Load Excel into Power BI |
| `BA_Profitability_DAX_Measures.dax` | DAX | Create | 20+ new measures for page |
| (This file) | Doc | Create | Page specification & design |
| `Build_BA_Page_Guide.md` | Doc | Create | Step-by-step Power BI build instructions |

---

## Status & Next Steps

**Status:** v0 — Design complete, awaiting build in Power BI Desktop

**Blocked until:**
1. ✓ Finance answers Q1-Q2 (COGS unit, CM2 formula)
2. Store master provided (store_code → chain → zone)
3. BA deployment list provided (which stores have BA, when)

**Next step:** Build page in Power BI Desktop following Build_BA_Page_Guide.md

---

**Branch:** claude/safe-powerbi-dashboard-rulings  
**PR:** #14 (do not merge until Finance confirms)

