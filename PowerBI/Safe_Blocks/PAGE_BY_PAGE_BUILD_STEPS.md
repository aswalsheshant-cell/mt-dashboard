# Page-by-Page Power BI Build Steps

**For:** MT Offtake Dashboard 10-page build  
**Reference:** PowerBI_10Page_DetailedSpec.md  
**Measures:** From DAX_Complete_Measure_Library.dax  

Each page includes exact visual specifications, measure requirements, and QC checks.

---

## PAGE 1: EXECUTIVE OVERVIEW (30 MIN)

**Purpose:** Leadership summary — top-level KPIs and trends  
**Status:** ✅ No blockers

### Layout Grid
```
┌──────────────────────────────────────────────────┐
│ SECTION 1: 6 KPI Cards (2 rows × 3 cols)        │
│ ┌─────────────┬──────────────┬──────────────┐    │
│ │   Total NSV │  Total MRP   │   Total Qty  │    │
│ │ ₹ Cr (ExTx) │ ₹ Cr (InTx)  │   Millions   │    │
│ └─────────────┴──────────────┴──────────────┘    │
│ ┌─────────────┬──────────────┬──────────────┐    │
│ │  NSV Growth │  MRP Growth  │  Qty Growth  │    │
│ │    MoM %    │    MoM %     │    MoM %     │    │
│ └─────────────┴──────────────┴──────────────┘    │
│                                                   │
│ SECTION 2: 2 Charts (1 row × 2 cols)             │
│ ┌──────────────────┬──────────────────┐          │
│ │ NSV Trend (Line) │ Top 6 Chains (Bar)          │
│ └──────────────────┴──────────────────┘          │
│                                                   │
│ SECTION 3: 6 Slicers (FY, Month, Chain, Zone,   │
│            Brand, Category)                      │
│                                                   │
│ SECTION 4: Warning Banner (2 lines)              │
│ ⚠️ June'26 Partial...                            │
│ ⚠️ NSV vs MRP...                                 │
└──────────────────────────────────────────────────┘
```

### Build Steps

**Step 1: Add 6 KPI Cards**

| Card | Measure | Label | Format | Color Logic |
|------|---------|-------|--------|-------------|
| 1 | [Total NSV Cr] | "Total NSV ₹Cr (Excl Tax)" | 2 decimals | Black |
| 2 | [Total MRP Sales Value Cr] | "Total MRP ₹Cr (Incl Tax)" | 2 decimals | Black |
| 3 | [Total Sales Qty M] | "Total Sales Qty Millions" | 1 decimal | Black |
| 4 | [NSV MoM Growth Pct] | "NSV Growth %" | 1 decimal | Green if >0, Red if <0 |
| 5 | [MRP MoM Growth Pct] | "MRP Growth %" | 1 decimal | Green if >0, Red if <0 |
| 6 | [Qty MoM Growth Pct] | "Qty Growth %" | 1 decimal | Green if >0, Red if <0 |

**Build:**
1. Insert → Card (repeat 6 times)
2. Drag measure to Visual Field
3. Format → Data label → Change label text to match above
4. Format → Conditional formatting (for growth cards): Green >0, Red <0

**Step 2: Add Line Chart (NSV Trend)**

- **Visual:** Line chart
- **X-axis:** Dim_Month[Month_Label]
- **Y-axis:** [Total NSV Cr]
- **Format:**
  - Title: "NSV Trend (Excl Tax)"
  - Line color: Blue
  - Data labels: Enabled (on points)
  - Legend: Hidden

**Step 3: Add Bar Chart (Top 6 Chains)**

- **Visual:** Clustered bar chart
- **X-axis:** Dim_Chain_Raw[Chain_Name]
- **Y-axis:** [Total NSV Cr]
- **Filters:** Top N = 6
- **Format:**
  - Title: "Top 6 Chains by NSV (Excl Tax)"
  - Bar color: Orange
  - Sort by: [Total NSV Cr] descending
  - Data labels: Enabled

**Step 4: Add 6 Slicers**

| Slicer | Field | Type | Style |
|--------|-------|------|-------|
| 1 | Dim_Month[FY] | Dropdown | Multi-select |
| 2 | Dim_Month[Month_Label] | Dropdown | Multi-select |
| 3 | Dim_Chain_Raw[Chain_Name] | Dropdown | Multi-select |
| 4 | Dim_Zone[Zone_Name] | Dropdown | Multi-select |
| 5 | Dim_Category[Brand] | Dropdown | Multi-select |
| 6 | Dim_Category[Category] | Dropdown | Multi-select |

**Position:** Top of page, horizontal row

**Step 5: Add Warning Banner**

- Insert → Text Box
- **Text:**
  ```
  ⚠️ June'26 Partial: 78,111 rows (16 chains only)
  ⚠️ NSV (Excl Tax) vs MRP (Incl Tax): Shown for QC/realization reference only.
     Do NOT use for direct variance analysis — different tax bases.
  ```
- **Format:**
  - Background: Yellow (#FFC000)
  - Text color: Black, 11pt bold
  - Border: Red, 2pt
  - Position: Bottom of page

### QC Checks

```
✓ Total NSV: ≈ 1,200–1,500 Cr (Apr'24–Jun'26)
✓ Total MRP: ≈ 1,400–1,600 Cr
✓ Total Qty: ≈ 150–200 M
✓ NSV Growth: -20% to +30% range
✓ Chart points all visible
✓ Slicer click updates all visuals
✓ Tax-basis warning visible
✓ June'26 warning visible
```

---

## PAGE 2: CHAIN PERFORMANCE (45 MIN)

**Purpose:** Chain ranking and zone drill-down  
**Status:** ✅ No blockers

### Key Elements

**3 KPI Cards:**
- [Total NSV Cr] — "Total NSV ₹Cr (Excl Tax)"
- [NSV MoM Growth Pct] — "NSV Growth %"
- [Distinct Zones] — "# of Zones" (COUNTDISTINCT(Dim_Zone[Zone_Name]))

**Drill-down Matrix:**
- Rows: Dim_Chain_Raw[Chain_Name], then Dim_Zone[Zone_Name]
- Values: [Total NSV Cr] (Excl Tax), [NSV MoM Growth Pct], [Total MRP Sales Value Cr] (Incl Tax), [Total Sales Qty M]
- Allow expand/collapse

**2 Charts:**
1. Clustered Bar: Chain vs NSV (Excl Tax), top 5
2. Line: Month vs NSV (Excl Tax), top 3 chains

**Warning Banner:**
```
⚠️ NSV (Excl Tax) vs MRP (Incl Tax): Shown for QC/realization reference only.
   Do NOT use for direct variance analysis — different tax bases.
```

### Build Steps
1. Insert 3 KPI cards (measures as above)
2. Insert Matrix visual → Configure drill-down as above
3. Insert 2 charts (bar + line)
4. Add 6 slicers (same as Page 1)
5. Add warning banner

### QC Checks
```
✓ Top chain (Reliance or Walmart) visible
✓ Zone drill-down expands correctly
✓ Growth % shows month-over-month change
✓ MRP column shows with "(Incl Tax)" label
✓ NSV column shows with "(Excl Tax)" label
✓ Warning banner about tax basis present
```

---

## PAGE 3: BRAND PERFORMANCE (40 MIN)

**Purpose:** Product brand analysis  
**Status:** ✅ No blockers

### Key Elements

**3 KPI Cards:**
- [Total NSV Cr] — "Total NSV ₹Cr (Excl Tax)"
- [NSV MoM Growth Pct] — "NSV Growth %"
- [Distinct Categories] — "# of Categories"

**Matrix: Brand × Category**
- Rows: Dim_Category[Brand], Dim_Category[Category]
- Values: [Total NSV Cr] (Excl Tax), [NSV MoM Growth Pct], [Total Sales Qty M], [Total MRP Sales Value Cr] (Incl Tax)

**2 Charts:**
1. Bar: Brand ranking by NSV (Excl Tax), top 10
2. Stacked Bar: Category mix by brand (NSV %)

**Warning Banner:**
```
⚠️ NSV (Excl Tax) vs MRP (Incl Tax): Shown for QC/realization reference only.
   Do NOT use for direct variance analysis — different tax bases.
```

### QC Checks
```
✓ Top brands visible
✓ Category breakdown by brand works
✓ Matrix expands/collapses
✓ MRP shown with "(Incl Tax)" label
✓ NSV shown with "(Excl Tax)" label
✓ Warning banner present
```

---

## PAGE 4: CATEGORY PERFORMANCE (40 MIN)

**Purpose:** Product category analysis  
**Status:** ✅ No blockers

### Key Elements

**3 KPI Cards:**
- [Total NSV Cr] — "Total NSV ₹Cr (Excl Tax)"
- [NSV MoM Growth Pct] — "NSV Growth %"
- [Category Count] — "# of Categories"

**3 Charts:**
1. Bar: Category ranking by NSV (Excl Tax), sorted desc
2. Line: Category trend (month-over-month NSV)
3. Scatter: NSV (Excl Tax) vs Qty, bubble size = MRP (Incl Tax), labeled "QC/Realization Only"

**Warning Banner:**
```
⚠️ NSV (Excl Tax) vs MRP (Incl Tax): Shown for QC/realization reference only.
   Do NOT use for direct variance analysis — different tax bases.
```

### QC Checks
```
✓ Top categories visible (Facewash, Shampoo, etc.)
✓ Trend line shows month progression
✓ Scatter plot bubble sizes vary
✓ Scatter labeled "QC/Realization Only"
✓ Warning banner present
```

---

## PAGE 5: ZONE PERFORMANCE (35 MIN)

**Purpose:** Geographic zone analysis  
**Status:** ✅ No blockers

### Key Elements

**3 KPI Cards:**
- [Total NSV Cr] — "Total NSV ₹Cr (Excl Tax)"
- [NSV MoM Growth Pct] — "NSV Growth %"
- [Distinct Chains] — "# of Chains"

**Matrix: Zone × Chain**
- Rows: Dim_Zone[Zone_Name]
- Columns: Dim_Chain_Raw[Chain_Name]
- Values: [Total NSV Cr]

**2 Charts:**
1. Heatmap or Conditional Bar: Zone comparison by NSV, colored by growth %
2. Bar: Zone growth comparison, sorted

### QC Checks
```
✓ All zones visible (NORTH-1, SOUTH-1, EAST-1, WEST-1, etc.)
✓ Chain breakdown by zone shows
✓ Growth % colored (green >0, red <0)
✓ No State dimension visible (only zones)
```

---

## PAGE 6: STORE / ACCOUNT PERFORMANCE (60 MIN)

**Purpose:** Store-level analysis (top/bottom/growth)  
**Status:** ⚠️ Partial blocker (Store_Master placeholder)

### Key Elements

**3 Tabs (Navigation):**

**Tab 1: Top Stores**
- Table: Top 20 stores by NSV (Excl Tax)
- Columns: Store_Code, Store_Name, Chain, Zone, NSV Cr (Excl Tax), Growth %, Qty, MRP Cr (Incl Tax)
- Sort: By NSV descending

**Tab 2: Bottom Stores**
- Table: Bottom 20 stores by NSV (Excl Tax)

**Tab 3: Growth Leaders**
- Table: Highest growth % stores

**2 Charts:**
1. Bar: Top 10 stores by NSV
2. Scatter: X=Prior NSV, Y=Current NSV, bubble size=Growth %

**Warning Banner:**
```
⚠️ NSV (Excl Tax) vs MRP (Incl Tax): Shown for QC/realization reference only.
   Do NOT use for direct variance analysis — different tax bases.
Note: Store Master currently uses placeholder data. Once Operations provides
real Store_Code → Chain → Zone mapping, this will auto-update.
```

### QC Checks
```
✓ Store codes visible (or "Pending" if Store_Master not ready)
✓ Top stores sorted correctly
✓ Growth % reasonable
✓ MRP shown with "(Incl Tax)" label
✓ NSV shown with "(Excl Tax)" label
✓ Warning about placeholder data visible
```

---

## PAGE 7: BA AVAILABILITY VIEW (90 MIN) ⚠️

**Purpose:** BA vs Non-BA analysis (sales, not profitability)  
**Status:** ⚠️ Partial blocker (BA deployment dates pending)

### Layout Grid
```
┌────────────────────────────────────────────────┐
│ SECTION 1: 12 KPI Cards (4 rows × 3 cols)     │
│ Row 1: BA NSV | Non-BA NSV | BA Coverage %    │
│ Row 2: BA Growth % | BA Row Count | BA MRP    │
│ Row 3: BA Cost | Listing Cost | Visibility    │
│ Row 4: CM2 ⚠️ | CM2% ⚠️ | Break-even Gap ⚠️ │
│                                                │
│ SECTION 2: 3 Charts                           │
│ Chart 1: BA vs Non-BA Trend (line)            │
│ Chart 2: Pre-BA vs Post-BA Growth (bar)       │
│ Chart 3: Comparable-Store Scatter (bubble)    │
│                                                │
│ SECTION 3: 19-column Store Profitability      │
│ Table: Chain, Store, NSV, Qty, Growth, Costs, │
│        CM2 ⚠️, Status, Recommendation         │
│                                                │
│ SECTION 4: Warning Banner (RED BACKGROUND)    │
│ ⚠️ PROVISIONAL PROFITABILITY...               │
└────────────────────────────────────────────────┘
```

### KPI Cards (12 total)

**Row 1: BA Metrics**
| Card | Measure | Label | Color |
|------|---------|-------|-------|
| 1 | [BA Available NSV Cr] | "BA Stores NSV ₹Cr (Excl Tax)" | Blue |
| 2 | [Non_BA Available NSV Cr] | "Non-BA Stores NSV ₹Cr (Excl Tax)" | Gray |
| 3 | [BA Coverage Pct] | "BA Coverage %" | Blue |

**Row 2: BA Growth & Count**
| Card | Measure | Label | Color |
|------|---------|-------|-------|
| 4 | [BA Available Growth Pct] | "BA Growth % MoM" | Green/Red |
| 5 | [BA Row Count] | "BA Transaction Count" | Blue |
| 6 | [BA Available MRP] | "BA Stores MRP ₹Cr (Incl Tax)" | Blue |

**Row 3: BA Costs**
| Card | Measure | Label | Color |
|------|---------|-------|-------|
| 7 | [Total BA Cost Cr] | "Total BA Cost ₹Cr" | Orange |
| 8 | [NPI Listing Cost Cr] | "Listing Cost ₹Cr" | Orange |
| 9 | [Visibility Rental Cost Cr] | "Visibility/Rental Cost ₹Cr" | Orange |

**Row 4: Profitability (All Provisional ⚠️)**
| Card | Measure | Label | Color |
|------|---------|-------|-------|
| 10 | [CM2 Cr Provisional] | "CM2 ₹Cr ⚠️ PROVISIONAL" | Yellow |
| 11 | [CM2 Pct Provisional] | "CM2 % ⚠️ PROVISIONAL" | Yellow |
| 12 | [Break Even Gap Cr Provisional] | "Break-even Gap ₹Cr ⚠️" | Yellow |

**Format cards 10-12:**
- Background: Light yellow (#FFFFCC)
- Border: Red
- Text: Bold, include ⚠️

### Charts (3 total)

**Chart 1: BA vs Non-BA Trend (Line)**
- X: Dim_Month[Month_Label]
- Y1: [BA Available NSV Cr] (blue line, "BA Stores")
- Y2: [Non_BA Available NSV Cr] (gray line, "Non-BA Stores")
- Title: "BA vs Non-BA Sales Trend (Excl Tax)"
- Legend: Enabled

**Chart 2: Pre-BA vs Post-BA Growth (Clustered Bar)**
- X: Dim_Chain_Raw[Chain_Name]
- Y1: [Pre_BA Growth Pct] (red bar, "Pre-BA")
- Y2: [Post_BA Growth Pct] (green bar, "Post-BA")
- Title: "Pre-BA vs Post-BA Growth Comparison"
- Sort: By growth descending
- Legend: Enabled

**Chart 3: Comparable-Store Scatter (Bubble)**
- X: [Store Prior Month NSV Cr] — "Prior Month NSV (Excl Tax)"
- Y: [Store NSV Cr] — "Current Month NSV (Excl Tax)"
- Bubble size: [Store CM2 Cr Provisional]
- Bubble color: [Store Status] (Green/Yellow/Orange/Red/Gray)
- Title: "Comparable-Store Growth Analysis ⚠️ (Provisional)"
- Legend: Enabled (status colors)

### Table: Store Profitability (19 columns)

**Columns (in order):**
1. Store_Code (from Store_Master)
2. Store_Name
3. Chain
4. Zone
5. [Store NSV Cr] — "(Excl Tax)"
6. [Store Sales Qty]
7. [Store Growth Pct]
8. [BA Salary Cost Cr]
9. [BA Supervisor Cost Cr]
10. [NPI Listing Cost Cr]
11. [TOT Cost Cr Provisional] — "⚠️"
12. [Promotional Cost Cr Provisional] — "⚠️"
13. [Visibility Rental Cost Cr]
14. [Other Employee Cost Cr]
15. [Total Support Cost Cr]
16. [Store CM2 Cr Provisional] — "⚠️"
17. [CM2 Pct Provisional] — "⚠️"
18. [Break Even Gap Cr Provisional]
19. [Store Status]

**Conditional Formatting on Store Status column:**
```
If [Store Status] = "Strong Performer" → Green (#00B050)
If [Store Status] = "Monitor" → Yellow (#FFC000)
If [Store Status] = "Improvement Required" → Orange (#FF7F00)
If [Store Status] = "Below Break-even" → Red (#FF0000)
If [Store Status] = "Cost Data Pending" → Gray (#D9D9D9)
```

**Sort:** By NSV descending (default)

### Warning Banner (Large, RED background)

**Text:**
```
⚠️ PROVISIONAL PROFITABILITY: TOT, promotional, listing, COGS unit, margins, 
   and CM2 are pending Finance validation. Do NOT recommend closure or 
   BA withdrawal until Q1-Q2 confirmed.

Current Status: 
   Q1 Decision: COGS Factor Units (awaiting Finance)
   Q2 Decision: Exact CM2 Formula & Tax-Basis Treatment (awaiting Finance)
   
Timeline: Expected Finance confirmation within 1 week
```

**Format:**
- Background: Red (#FF0000) or Dark Red
- Text: White, 11pt bold
- Border: Black, 2pt
- Position: Above table

### Slicer: BA Status (Custom Single-Select)

**Options:**
- "All"
- "BA Stores Only"
- "Non-BA Stores Only"

**Position:** Top-left slicer area

### QC Checks

```
✓ BA NSV < Total NSV ✓
✓ Non-BA NSV + BA NSV ≈ Total NSV ✓
✓ BA Coverage % ≤ 100% ✓
✓ CM2 cards show ⚠️ yellow background ✓
✓ Table shows 19 columns correctly ✓
✓ Conditional formatting colors visible ✓
✓ Warning banner prominent (red background) ✓
✓ Store Status shows "Cost Data Pending" for rows without CM2 input ✓
```

---

## PAGE 8: DATA EXPLORER (60 MIN)

**Purpose:** Detailed cost tracking and expense analysis  
**Status:** ⚠️ Partial blocker (TOT %, Promo % pending Finance Q4-Q5)

### Key Elements

**6 KPI Cards (Cost Summary):**
- [Total BA Cost Cr] — "BA Salary ₹Cr"
- [NPI Listing Cost Cr] — "Listing Cost ₹Cr"
- [TOT Cost Cr Provisional] — "TOT Cost ₹Cr ⚠️ PROVISIONAL"
- [Promotional Cost Cr Provisional] — "Promo Cost ₹Cr ⚠️ PROVISIONAL"
- [Visibility Rental Cost Cr] — "Visibility/Rental ₹Cr"
- [COGS Cost Cr Provisional] — "COGS Cost ₹Cr ⚠️ PROVISIONAL"

**Format cards with ⚠️:**
- Background: Light yellow
- Text: Bold with ⚠️

**3 Charts:**
1. Pie: Cost breakdown (% of total)
2. Line: Cost trend (by month)
3. Clustered Bar: Cost by chain

**Cost Allocation Table:**
- Rows: Chain, Store
- Columns: BA Salary, Supervisor, Listing, TOT ⚠️, Promo ⚠️, Visibility, Other, Total Cost
- Conditional highlighting: Yellow if missing/provisional, Red if >10% of NSV

**Warning Banner:**
```
⚠️ TOT % and Promotional % values pending Finance confirmation (Q4-Q5)
   Missing costs shown as "Pending" not ₹0
   All cost allocations subject to change when Finance provides final values.
```

### QC Checks
```
✓ Total costs reasonable (10–20% of NSV typically)
✓ Pie chart shows all cost types
✓ Trend line shows cost progression
✓ Chain breakdown visible
✓ Missing values highlighted (not zeroed)
✓ Warning about pending Finance values visible
```

---

## PAGE 9: PROFITABILITY / CM2 READINESS QC (10 MIN)

**Purpose:** QC & readiness only, NOT profitability reporting  
**Status:** ❌ BLOCKED awaiting Finance Q1-Q2

### Key Element: Placeholder Only

**This page does NOT contain active profitability visuals.**

**Create single large text box:**

**Text:**
```
⚠️⚠️⚠️ PROFITABILITY ANALYSIS — BLOCKED FOR FINANCE VALIDATION ⚠️⚠️⚠️

This page is a READINESS QC PAGE ONLY. No profitability visuals active.

AWAITING FINANCE CONFIRMATION:

Q1: COGS Factor Units
    Current values in Expense_Assumptions_Input.xlsx: 0.1655, 0.185, etc.
    Question: Are these %, ratios, per-unit costs, or other?
    Impact: Changes [COGS Cost Cr Provisional] calculation

Q2: Exact CM2 Formula & Tax-Basis Treatment
    Current formula (provisional): CM2 = NSV - COGS - Support Costs
    Question: Is this NSV-based or MRP-based? Which cost sheets included? Tax handling?
    Impact: Changes [CM2 Cr Provisional], [CM2 Pct Provisional], Break-even calculations

AVAILABLE MEASURES (NOT VISUALIZED):
  - [CM2 Cr Provisional] — Pending formula confirmation
  - [CM2 Pct Provisional] — Pending formula confirmation
  - [Break Even Gap Cr Provisional] — Pending formula confirmation
  - [ROI Pct Provisional] — Pending formula confirmation
  - [Payback Period Months Provisional] — Pending formula confirmation

CURRENT STATUS:
  All profitability measures created in DAX (see MEASURE_DICTIONARY.md)
  All formulas marked PROVISIONAL
  All visualizations HIDDEN (intentional)
  Do NOT use Page 7 CM2 metrics for business decisions yet

TIMELINE: Expected Finance Q1-Q2 answers within 1 week

NEXT STEP: Once Finance confirms Q1-Q2:
  1. Update Expense_Assumptions_Input.xlsx with confirmed values
  2. Update DAX measure formulas
  3. Unhide profitability visuals on this page
  4. Rebuild Page 7 tables with final CM2 values
  5. Re-run QC validation

Contact Finance Q1-Q2 Owners before proceeding.
```

**Format:**
- Background: Light gray (#F0F0F0)
- Text: 10pt, left-aligned, monospace (Courier) for readability
- Border: Red, 3pt
- Padding: 20px

**NO KPI cards, NO charts, NO formulas visualized on this page.**

### QC Checks
```
✓ Page exists but has no active profitability visuals
✓ Placeholder text explains why (Finance Q1-Q2 pending)
✓ Red border/warning visible
✓ No CM2, Margin, or Profitability measures shown in any visual
```

---

## PAGE 10: QC & RECONCILIATION (50 MIN)

**Purpose:** Data quality flags and monthly reconciliation  
**Status:** ✅ No blockers

### Key Elements

**5 KPI Cards (Quality Metrics):**
- [Total Row Count] — "Total Transactions"
- [June26 Partial Row Count] — "Jun-26 Partial Rows"
- [Negative NSV Return Count] — "Negative NSV Returns"
- [Missing Cost Count] — "Missing Cost Fields"
- [Finance Validation Required] — "Awaiting Finance"

**Table 1: Validation Status**
- Filter: Rows where Missing_Cost_Flag = TRUE OR Finance_Validation_Status ≠ "Confirmed"
- Columns: Chain, Store_Code, Cost_Type, Missing_Cost_Flag, Finance_Validation_Status, Data_Status
- Conditional: Yellow highlight if Missing_Cost_Flag = TRUE
- Purpose: Show all incomplete/pending data

**Table 2: Monthly Reconciliation**
- Rows: Dim_Month[Month_Label] (Apr-24 to Jun-26)
- Columns:
  - [Total Row Count]
  - [Distinct Chains]
  - [Distinct Zones]
  - [Total NSV Cr] "(Excl Tax)"
  - [Total MRP Sales Value Cr] "(Incl Tax)"
  - [Total Sales Qty M]
  - June26 Partial Flag
- Purpose: Monthly quality summary

**QC Alerts Section:**
- Text box listing all known issues:
  ```
  KNOWN QC ISSUES:
  - June'26 Partial: 78,111 rows (16 chains only) ✓ DOCUMENTED
  - Negative Returns: 12,705 rows (flagged, valid credit notes) ✓ OK
  - More Retail Duplicates: 13,661 rows (retained, not deduped) ✓ OK
  - NSV Unit: Confirmed Lakhs (₹ 100K) ✓ OK
  - MRP Unit: Confirmed rupees ✓ OK
  - Pending COGS Unit Confirmation (awaiting Finance Q1) ⏳ PENDING
  - Pending CM2 Formula Confirmation (awaiting Finance Q2) ⏳ PENDING
  - Pending TOT % (awaiting Finance Q4) ⏳ PENDING
  - Pending Promotional % (awaiting Finance Q5) ⏳ PENDING
  - Store Master pending from Operations ⏳ PENDING
  - BA Deployment dates pending from Operations/Reliance ⏳ PENDING
  ```

**Refresh Status:**
- Text: "Last Refresh: [Last Updated Date] | Status: [Data Quality Status]"
- Updates when data refreshes

### QC Checks

```
✓ Total Row Count ≈ 4.21M
✓ June'26 Partial ≈ 78,111
✓ Negative NSV Returns ≈ 12,705
✓ Monthly totals reconcile (sum of monthly NSV ≈ Total NSV Cr)
✓ Validation status table shows any missing costs
✓ QC alerts text box complete and readable
✓ Refresh timestamp updates when data reloads
```

---

## GLOBAL REQUIREMENTS (ALL PAGES)

### Slicer Configuration (Standard across all pages)

**6 Slicers (consistent formatting):**
1. **FY** — Dim_Month[FY] — Multi-select — Default: Current FY
2. **Month** — Dim_Month[Month_Label] — Multi-select — Default: All
3. **Chain** — Dim_Chain_Raw[Chain_Name] — Multi-select — Default: All
4. **Zone** — Dim_Zone[Zone_Name] — Multi-select — Default: All
5. **Brand** — Dim_Category[Brand] — Multi-select — Default: All
6. **Category** — Dim_Category[Category] — Multi-select — Default: All

**Position:** Top of every page, horizontal row (consistent)

**Format (all slicers):**
- Style: Dropdown or List (choose one, apply to all)
- Height: 30px
- Background: Light gray (#F5F5F5)
- Text: 10pt, dark gray
- Spacing: 10px apart

### Tax-Basis Labeling (ALL PAGES)

**Every NSV column/measure must show:** "(Excl Tax)"  
**Every MRP column/measure must show:** "(Incl Tax)"  
**Every NSV/MRP comparison must include warning:** "Different tax bases; QC/realization only"

### June'26 Watermark (Pages 1, 2, 3, 4, 5, 6, 7, 8, 10)

**Warning:** "⚠️ June'26 Partial: 78,111 rows (16 chains only)"

**Position:** Bottom of page or in a tooltip

### No State Dimension (ALL PAGES)

**Confirm:**
- ❌ NO State slicer anywhere
- ❌ NO State column in any table
- ❌ NO State drill-down
- ✅ Zone-only reporting (P6 canonical zones)

### Provisional Labels (Page 7 & 8 only)

**Any measure with "Provisional" in name must show:**
- ⚠️ Yellow highlight or warning icon
- Explicit "⚠️ PROVISIONAL" in card label or chart title

---

## Build Validation Checklist

**Before declaring page complete:**

```
□ All visuals render without #ERROR
□ All measures show reasonable numbers
□ Slicers filter all visuals correctly
□ Tax-basis labels present (NSV "Excl Tax", MRP "Incl Tax")
□ June'26 warning visible (if applicable)
□ No State dimension anywhere
□ Provisional labels visible (Page 7-8)
□ Colors/formatting consistent
□ Page title clear
□ Tooltips work
```

**Return to LOCAL_POWERBI_DESKTOP_BUILD_GUIDE.md for full QC framework.**

