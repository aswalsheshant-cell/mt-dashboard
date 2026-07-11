# Power BI Dashboard — 10-Page Detailed Specification

**Branch:** claude/safe-powerbi-dashboard-rulings  
**Status:** v1 — Production-ready page specifications  
**Generated:** 2026-07-11  
**Total Pages:** 10  
**Total Visuals:** 60+  
**Measures Used:** 84 (from DAX_Complete_Measure_Library.dax)

---

## Page Navigation & Order

```
1. Executive Dashboard (KPIs, Summary charts)
   ↓
2. Chain Performance (Chain ranking, drill-down)
   ↓
3. Brand Performance (Brand ranking, trends)
   ↓
4. Category (Category analysis)
   ↓
5. Zone Performance (Zone comparison)
   ↓
6. Store Performance (Top/Bottom stores, growth)
   ↓
7. BA Stores Performance (BA vs Non-BA, profitability ⚠️)
   ↓
8. Expense Dashboard (Cost breakdown, trends)
   ↓
9. Profitability Dashboard ⚠️ (CM2, ROI, Break-even — HOLDS until Finance Q1-Q2)
   ↓
10. Data Quality Dashboard (Missing data, flags, reconciliation)
```

---

## PAGE 1: EXECUTIVE DASHBOARD

**Purpose:** Leadership summary — KPIs + key trends  
**Time estimate:** 30 min to build  
**Status:** ✅ No blockers (uses NSV, MRP, Qty only)

### Layout

```
┌─────────────────────────────────────────────────────────────────┐
│                  EXECUTIVE DASHBOARD                             │
│              Sales Performance Summary                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  SECTION 1: TOP-LEVEL KPIs (6 cards, 2 rows × 3)                │
│  ┌──────────────┬──────────────┬──────────────┐                 │
│  │   Total NSV  │  Total MRP   │   Total Qty  │                 │
│  │  ₹ Crore     │  ₹ Crore     │   Millions   │                 │
│  │  (Excl Tax)  │  (Incl Tax)  │    Units     │                 │
│  │   [TOTAL]    │   [TOTAL]    │   [TOTAL]    │                 │
│  └──────────────┴──────────────┴──────────────┘                 │
│  ┌──────────────┬──────────────┬──────────────┐                 │
│  │  NSV Growth  │  MRP Growth  │  Qty Growth  │                 │
│  │     MoM %    │     MoM %    │     MoM %    │                 │
│  │  [+12.5%]    │  [+11.2%]    │  [+14.8%]    │                 │
│  └──────────────┴──────────────┴──────────────┘                 │
│                                                                   │
│  SECTION 2: CHARTS (2 charts, 1 row)                             │
│  ┌────────────────────────────┬────────────────────────────────┐ │
│  │ Chart 1: NSV Trend (Line)  │ Chart 2: Top Chains (Bar)      │ │
│  │ X: Month                   │ X: Chain                       │ │
│  │ Y: NSV Cr (by Month)       │ Y: NSV Cr (Top 6)              │ │
│  │ Measure: [Total NSV Cr]    │ Measure: [Total NSV Cr]        │ │
│  └────────────────────────────┴────────────────────────────────┘ │
│                                                                   │
│  SECTION 3: SLICERS (Top, connects all pages)                    │
│  FY | Month | Chain | Zone | Brand | Category                   │
│                                                                   │
│  SECTION 4: WARNINGS (if applicable)                             │
│  ⚠️ June'26 Partial: 78,111 rows (16 chains only)               │
│  ⚠️ NSV (Excl Tax) vs MRP (Incl Tax): Different tax bases.      │
│     Shown for summary reference; do NOT use for variance.       │
│  ⚠️ Provisional Profitability: See Page 9 for details            │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### Visuals Specification

| Visual | Type | Measures | Format | Sorting |
|--------|------|----------|--------|---------|
| **KPI 1: Total NSV** | Card | [Total NSV Cr] | ₹ Cr, 2 decimals, label "NSV ₹Cr (Excl Tax)" | N/A |
| **KPI 2: Total MRP** | Card | [Total MRP Sales Value Cr] | ₹ Cr, 2 decimals, label "MRP ₹Cr (Incl Tax)" | N/A |
| **KPI 3: Total Qty** | Card | [Total Sales Qty M] | M units, 1 decimal | N/A |
| **KPI 4: NSV Growth** | Card | [NSV MoM Growth Pct] | %, 1 decimal, conditional color (green if +, red if -) | N/A |
| **KPI 5: MRP Growth** | Card | [MRP MoM Growth Pct] | %, 1 decimal, conditional color | N/A |
| **KPI 6: Qty Growth** | Card | [Qty MoM Growth Pct] | %, 1 decimal, conditional color | N/A |
| **Chart 1: NSV Trend** | Line | X: Dim_Month[Month_Label], Y: [Total NSV Cr] | Legend: "NSV Trend" | Month order (ascending) |
| **Chart 2: Top 6 Chains** | Clustered Bar | X: Dim_Chain_Raw[Chain_Name], Y: [Total NSV Cr] | Sorted by [Total NSV Cr] desc | Top 6 by NSV |
| **Slicers (6)** | Dropdown | FY, Month, Chain, Zone, Brand, Category | Multi-select, show all values | N/A |
| **Warning Banner** | Text Box | Static + [June26 Partial Row Count] if applicable | Red border, yellow bg, 12pt font | N/A |

### Page Interactions

- Slicers connect to all visuals (FY, Month, Chain, Zone filter all charts)
- Drill-through: Click on chain bar → go to Page 2 (Chain Performance detail)

---

## PAGE 2: CHAIN PERFORMANCE

**Purpose:** Performance by chain (ranking, drill-down to zones)  
**Time estimate:** 45 min  
**Status:** ✅ No blockers

### Layout

```
Slicer: Chain (multi-select) | FY | Month | Zone | Brand

KPI Row: Total NSV (Excl Tax) | Growth % | Top Zone | Bottom Zone

TABLE: Chain Drill-down
  Chain | Total NSV (Excl Tax) | Growth % | MRP (Incl Tax) | Qty | Zone (sub-rows)
    RELIANCE | ₹500 Cr | +12% | ... | (expand → zones below)
      └─ NORTH-1 | ₹100 Cr | +8% | ...
      └─ SOUTH-1 | ₹150 Cr | +15% | ...
    WALMART | ₹300 Cr | +10% | ...
      └─ WEST-1 | ...

CHARTS (2):
  - Chain Comparison (Clustered Bar: Chain vs NSV (Excl Tax) vs MRP (Incl Tax) — QC/Realization Only)
  - Growth Trend by Chain (Line: Month vs Growth % for top 3 chains)

WARNING BANNER:
  ⚠️ NSV (Excl Tax) vs MRP (Incl Tax): Shown for QC/realization reference only.
     Do NOT use for direct variance analysis — different tax bases.
```

### Measures by Visual

- Total NSV Cr (Excl Tax), MRP Cr (Incl Tax), Qty, Growth %, Contribution %
- Drill-down: Zone detail (sub-table)
- **NOTE:** NSV excludes tax; MRP includes tax. Not directly comparable for variance.

---

## PAGE 3: BRAND PERFORMANCE

**Purpose:** Product brand analysis (ranking, category breakdown)  
**Time estimate:** 40 min  
**Status:** ✅ No blockers

### Layout

```
Slicer: Brand | FY | Month | Chain | Zone | Category

KPI Row: Total NSV (Excl Tax) | Growth % | Qty | NSV per Unit

MATRIX/TABLE: Brand × Category
  Brand | Category | NSV (Excl Tax) | Growth | Qty | MRP (Incl Tax)

CHARTS (2):
  - Brand Ranking (Bar: sorted by NSV desc)
  - Category Mix by Brand (Stacked Bar)

WARNING BANNER:
  ⚠️ NSV (Excl Tax) vs MRP (Incl Tax): Shown for QC/realization reference only.
     Do NOT use for direct variance analysis — different tax bases.
```

---

## PAGE 4: CATEGORY

**Purpose:** Product category analysis  
**Time estimate:** 40 min  
**Status:** ✅ No blockers

### Layout

```
Slicer: Category | FY | Month | Brand | Chain | Zone

KPI Row: Top Category (NSV Excl Tax) | Category Count | Total NSV (Excl Tax) | Growth

CHARTS (3):
  - Category Ranking (Bar)
  - Category Trend (Line)
  - NSV (Excl Tax) vs Qty by Category (Scatter, bubble size = MRP (Incl Tax) — QC/Realization Only)

WARNING BANNER:
  ⚠️ NSV (Excl Tax) vs MRP (Incl Tax): Shown for QC/realization reference only.
     Do NOT use for direct variance analysis — different tax bases.
```

---

## PAGE 5: ZONE PERFORMANCE

**Purpose:** Geographic zone analysis (North/South/East/West)  
**Time estimate:** 35 min  
**Status:** ✅ No blockers

### Layout

```
Slicer: Zone | FY | Month | Chain | Brand | Category

KPI Row: Top Zone | Total Zones | NSV by Zone | Growth

MATRIX: Zone × Chain
  Zone | Chain1 | Chain2 | Chain3 | ... (NSV values)

CHARTS (2):
  - Zone Map/Heatmap (conditional color by NSV/Growth)
  - Zone Growth Comparison (Bar)
```

---

## PAGE 6: STORE PERFORMANCE

**Purpose:** Store-level analysis (top performers, bottom performers, ranking)  
**Time estimate:** 60 min  
**Status:** ⚠️ Partial blocker (Store Master pending from Operations)

### Layout

```
Slicer: BA Status (BA / Non-BA / All) | FY | Month | Chain | Zone | Brand

TAB 1: Top Stores
  TABLE: Top 20 stores by NSV (Excl Tax)
    Store | Chain | Zone | NSV Cr (Excl Tax) | Growth % | Qty | MRP (Incl Tax)

TAB 2: Bottom Stores
  TABLE: Bottom 20 stores by NSV (Excl Tax)

TAB 3: Growth Leaders
  TABLE: Highest growth % stores (sorted)

CHARTS (2):
  - Top 10 Stores (Bar)
  - Growth by Store (Scatter: X=Prior NSV (Excl Tax), Y=Current NSV (Excl Tax), bubble size=Growth%)

WARNING BANNER:
  ⚠️ NSV (Excl Tax) vs MRP (Incl Tax): Shown for QC/realization reference only.
     Do NOT use for direct variance analysis — different tax bases.

NOTE: Requires Store_Master table (pending Operations)
```

---

## PAGE 7: BA STORES PERFORMANCE ⚠️

**Purpose:** BA vs Non-BA analysis, provisional profitability  
**Time estimate:** 90 min  
**Status:** ⚠️ Partial blocker (Store Master + BA deployment dates pending)

### Layout

```
SECTION 1: EXECUTIVE KPIs (12 cards, 4 rows × 3)
  Row 1: [BA Available NSV Cr] | [Non_BA Available NSV Cr] | [BA Coverage Pct]
  Row 2: [BA Available Growth Pct] | [BA Row Count] | [BA Available MRP]
  Row 3: [Total BA Cost Cr] | [NPI Listing Cost Cr] | [Visibility Rental Cost Cr]
  Row 4: [CM2 Cr Provisional] ⚠️ | [CM2 Pct Provisional] ⚠️ | [Break Even Gap Cr Provisional] ⚠️

SECTION 2: BA vs NON-BA CHARTS (3 charts, 2 rows)
  Chart 1: BA vs Non-BA NSV Trend (Line)
  Chart 2: Pre-BA vs Post-BA Growth (Bar)
  Chart 3: Comparable-Store Growth (Scatter: Prior NSV vs Current, bubble=CM2)

SECTION 3: STORE PROFITABILITY TABLE (19 columns)
  Chain | Store | NSV | Qty | Growth % | BA Salary | Supervisor | Listing | TOT ⚠️ | Promo ⚠️
  Visibility | Other | Total Cost | Prov CM2 ⚠️ | CM2% ⚠️ | Break-even Gap | Status | Recommendation

CONDITIONAL FORMATTING:
  - Strong Performer (CM2% ≥15%, Growth >10%) → Green
  - Monitor (CM2% 5-15%) → Yellow
  - Improvement Required (Break-even gap -0.1 to 0) → Orange
  - Below Break-even (gap <-0.1) → Red
  - Cost Data Pending (Missing_Cost_Flag=Y) → Gray
  - Provisional cost (Provisional_Cost_Flag=Y) → Italic

WARNING BANNER:
  ⚠️ PROVISIONAL PROFITABILITY: TOT, promotional, listing, COGS unit, margins pending Finance validation.
  Do NOT recommend closure/BA withdrawal until Q1-Q2 confirmed.
```

### Measures by Visual

**KPIs:**
- [BA Available NSV Cr], [Non_BA Available NSV Cr], [BA Coverage Pct]
- [BA Available Growth Pct], [Total BA Cost Cr], [NPI Listing Cost Cr]
- [Visibility Rental Cost Cr], [TOT Cost Cr Provisional], [Promotional Cost Cr Provisional]
- [CM2 Cr Provisional], [CM2 Pct Provisional], [Break Even Gap Cr Provisional]

**Charts:**
- Trend: [BA Available NSV Cr] vs [Non_BA Available NSV Cr] by month
- Comparison: [Pre_BA Growth Pct] vs [Post_BA Growth Pct] by chain
- Scatter: [Store Prior Month NSV Cr] (X), [Store NSV Cr] (Y), bubble size [Store CM2 Cr Provisional]

**Table:**
- 19 columns with [Store_Status], [Recommendation_Status] (all "Under Review — Provisional")
- Sort options: By NSV, By CM2, By Status
- Drill-through: Click store → Store Detail page (new page showing month-by-month trends)

---

## PAGE 8: EXPENSE DASHBOARD

**Purpose:** Cost tracking and analysis  
**Time estimate:** 60 min  
**Status:** ⚠️ Partial blocker (TOT % and Promo % pending Finance Q4-Q5)

### Layout

```
SECTION 1: COST SUMMARY KPIs (6 cards)
  [Total BA Cost Cr] | [NPI Listing Cost Cr] | [TOT Cost Cr Provisional] ⚠️
  [Promotional Cost Cr Provisional] ⚠️ | [Visibility Rental Cost Cr] | [COGS Cost Cr Provisional] ⚠️

SECTION 2: COST BY TYPE (3 charts)
  Chart 1: Cost Breakdown Pie (% of total cost by type)
  Chart 2: Cost Trend (Line: cost amount by month)
  Chart 3: Cost by Chain (Clustered Bar: each chain's cost components)

SECTION 3: COST ALLOCATION TABLE
  Chain | Store | BA Salary | Supervisor | Listing | TOT ⚠️ | Promo ⚠️ | Visibility | Other | Total

CONDITIONAL FORMATTING:
  - Missing cost (TOT %, Promo %) → Yellow highlight ⚠️
  - Provisional cost → Italic
  - High cost (>10% of NSV) → Red background

METRICS:
  [Total Support Cost Cr] | [Cost as % of NSV] | [Cost per Store] | [Cost Trend %]
```

### Measures by Visual

- [Total BA Cost Cr], [NPI Listing Cost Cr], [TOT Cost Cr Provisional], [Promotional Cost Cr Provisional]
- [Visibility Rental Cost Cr], [COGS Cost Cr Provisional], [Other Employee Cost Cr]
- [Total Support Cost Cr] (sum of above)
- Ratios: Cost components as % of Total Support Cost

---

## PAGE 9: PROFITABILITY DASHBOARD ⚠️⚠️⚠️

**Purpose:** Profitability analysis (CM2, ROI, Break-even)  
**Status:** ❌ **BLOCKED UNTIL FINANCE CONFIRMS Q1-Q2**

### Current Status

This page is **HELD** with message:

```
⚠️ AWAITING FINANCE CONFIRMATION ⚠️

This page cannot be populated until Finance confirms:

Q1: COGS Factor Units
    (are 0.1655 values %, ratio, per-unit costs, or other?)
    
Q2: Exact CM2 Formula & Tax-Basis Treatment
    (NSV-based or MRP-based? Which cost sheets included? Tax handling?)

Current Status: All profitability measures show PROVISIONAL labels
                All recommendations show "Under Review"
                Do NOT use for final business decisions

Timeline: Expected Finance confirmation within 1 week

When Q1-Q2 are confirmed:
  ✓ [CM2 Cr Provisional] → [CM2 Cr] (formula updated)
  ✓ [ROI Pct Provisional] → [ROI Pct] (recalculated)
  ✓ [Payback Period Months Provisional] → [Payback Period Months] (valid)
  ✓ Recommendation_Status → "Close", "Withdraw BA", "Expand", etc.
  ✓ Page fully unlocked for business decisions
```

### Placeholder Layout (to be populated)

```
KPI ROW (will populate when Q1-Q2 confirmed):
  [CM1 Pct Provisional] | [CM2 Cr Provisional] | [CM2 Pct Provisional]
  [ROI Pct Provisional] | [Payback Period Months Provisional] | [Break Even Sales]

CHARTS (will populate when Q1-Q2 confirmed):
  - Profitability by Chain (Bar)
  - CM2 Trend (Line)
  - ROI Distribution (Histogram)

TABLE (will populate when Q1-Q2 confirmed):
  Store | NSV | Cost | CM1 | CM2 | ROI % | Payback Months | Status
```

---

## PAGE 10: DATA QUALITY DASHBOARD

**Purpose:** QC, validation, missing data, reconciliation  
**Time estimate:** 50 min  
**Status:** ✅ No blockers

### Layout

```
SECTION 1: DATA QUALITY METRICS (5 cards)
  [Total Row Count] | [June26 Partial Row Count] | [Negative Return Count]
  [Missing Cost Count] | [Finance Validation Required]

SECTION 2: VALIDATION FLAGS
  TABLE: Missing Costs & Validation Status
    Chain | Store | Cost_Type | Missing? | Validation_Status | Data_Status
    (shows all rows where Missing_Cost_Flag=Y or Finance_Validation_Status≠"Confirmed")

SECTION 3: MONTHLY RECONCILIATION
  TABLE: Month × Metrics
    Month | Row Count | Chain Count | Zone Count | NSV Total (Excl Tax) | MRP Total (Incl Tax) | Qty Total | Status
    (Apr-24, May-24, ..., Jun-26)
  
  WARNING: NSV (Excl Tax) vs MRP (Incl Tax) shown for QC/realization reference only.
           Do NOT use for direct variance analysis — different tax bases.

SECTION 4: QC ALERTS
  TEXT: Lists all known issues:
    - June'26 Partial: 78,111 rows (16 chains only)
    - Negative Returns: 12,705 rows (valid, flagged)
    - More Retail Duplicates: 13,661 rows (retained)
    - Missing Costs: TOT %, Promo % (Finance Q4-Q5)
    - Pending Mappings: Store Master, BA Deployment dates (Operations)

SECTION 5: REFRESH STATUS
  [Data Refresh Status] | [Last Updated Date] | [Data Quality Status]
```

### Measures by Visual

- [Total Row Count], [June26 Partial Row Count], [Negative NSV Return Count], [Negative MRP Return Count]
- [Missing Cost Count], [Finance Validation Required]
- [Distinct Chains], [Distinct Zones], [Distinct Categories]
- Reconciliation table: aggregates by month

---

## GLOBAL SLICER CONFIGURATION

**Applied to all pages (1–10):**

| Slicer | Table | Column | Multi-Select | Default Value |
|--------|-------|--------|--------------|----------------|
| FY | Dim_Month | FY | ✓ Yes | Current FY (FY26) |
| Month | Dim_Month | Month_Label | ✓ Yes | Last 3 months |
| Chain | Dim_Chain_Raw | Chain_Name | ✓ Yes | All chains |
| Zone | Dim_Zone | Zone_Name | ✓ Yes | All zones |
| Brand | Dim_Category | Brand | ✓ Yes | All brands |
| Category | Dim_Category | Category | ✓ Yes | All categories |
| BA Status | (Custom) | BA / Non-BA / All | ✗ No | All (Pages 1-6), BA (Page 7) |

**Slicer Interactions:**
- All slicers filter all visuals on their page
- Slicers persist across page navigation (last selected values remembered)
- Reset button: Right-click slicer → "Reset Slicer"

---

## CONDITIONAL FORMATTING RULES

### By Page & Visual

**Page 1 (Executive): KPI Cards**
- If [Is June26 Partial] = TRUE → Show ⚠️ "Jun-26 Partial" badge on card
- If [NSV MoM Growth Pct] > 0 → Green highlight; else Red

**Page 7 (BA Stores): Store Status Column**
```
IF [Store Status] = "Strong Performer" → 🟢 Green background (#00B050)
IF [Store Status] = "Monitor" → 🟡 Yellow background (#FFC000)
IF [Store Status] = "Improvement Required" → 🟠 Orange background (#FFC000 darker)
IF [Store Status] = "Below Break-even" → 🔴 Red background (#FF0000)
IF [Store Status] = "Cost Data Pending" → ⚪ Gray background (#D9D9D9)
IF [Has Missing Costs] = TRUE → Yellow highlight (any cost column)
IF [Provisional_Cost_Flag] = TRUE → Italic font + gray text
```

**Page 8 (Expense): Cost Columns**
- If cost > NSV × 10% → Red background (high cost warning)
- If [TOT Cost Cr Provisional] = BLANK → Yellow "⚠️ Pending"
- If [Promotional Cost Cr Provisional] = BLANK → Yellow "⚠️ Pending"

**Page 9 (Profitability): NOT BUILT YET**
- Awaiting Finance Q1-Q2 confirmation

**Page 10 (Data Quality): Validation Table**
- If [Missing_Cost_Flag] = TRUE → Yellow row
- If [Finance_Validation_Status] = "Awaiting" → Gray row + italic

---

## DRILL-THROUGH CONFIGURATION

### Drill Paths

| Source Page | Source Visual | Target Page | Pass Fields |
|-------------|---------------|-------------|-------------|
| Page 1 | Top Chains chart | Page 2 | Chain_Name |
| Page 2 | Chain Table | Page 5 | Zone (via chain→zone) |
| Page 5 | Zone chart | Page 6 | Zone_Name |
| Page 6 | Top Stores table | *New: Store Detail* | Store_Code, Store_Name |
| Page 7 | Store Profitability table | *New: Store Detail* | Store_Code, Month |
| Page 3 | Brand chart | Page 4 | Brand, Category |

### Store Detail Page (Drill-Through Target)

**Hidden page, appears on drill-through:**

```
← Back to previous page

STORE DETAIL: [Store_Name] ([Store_Code])
Chain: [Chain] | Zone: [Zone] | BA Status: [BA_Status] | Deployed: [BA_Deployment_Date]

3-MONTH TREND CHART:
  X: Month | Y: NSV Cr
  Measures: [Store NSV Cr], [Store Prior Month NSV Cr], [Store CM2 Cr Provisional]

CURRENT MONTH METRICS:
  NSV | Growth % | BA Cost | Profitability | Status

MONTHLY DETAIL TABLE:
  Month | NSV | Qty | MRP | Costs | CM2 | Status
```

---

## BUILD TIMELINE & CHECKLIST

### Phase 1: Build Pages 1–6 (No blockers)

**Estimated time:** 3–4 hours

```
□ Page 1: Executive Dashboard (30 min)
□ Page 2: Chain Performance (45 min)
□ Page 3: Brand Performance (40 min)
□ Page 4: Category (40 min)
□ Page 5: Zone Performance (35 min)
□ Page 6: Store Performance (60 min)
□ Test refresh & data validation (30 min)
```

### Phase 2: Build Pages 7–10 (Partial blockers)

**Estimated time:** 2–3 hours (but Page 9 will be held)

```
□ Page 7: BA Stores Performance (90 min)
  ⚠️ Note: Store Master & BA deployment dates pending
□ Page 8: Expense Dashboard (60 min)
  ⚠️ Note: TOT % & Promo % pending Finance Q4-Q5
□ Page 9: Profitability Dashboard (HOLD)
  ❌ BLOCKED: Awaiting Finance Q1-Q2
□ Page 10: Data Quality Dashboard (50 min)
□ Configure all drill-throughs (30 min)
□ Add Store Detail drill-through page (45 min)
```

### Phase 3: Finance Confirmation → Unlock Page 9

**Once Finance answers Q1-Q2:**

```
□ Update [COGS Cost Cr Provisional] formula (Q1 answer)
□ Update [CM2 Cr Provisional] formula (Q2 answer)
□ Remove "Provisional" warnings from Page 7 & 8 (if applicable)
□ Build & populate Page 9 (Profitability Dashboard)
□ Unhide recommendation columns (BA Withdrawal, Closure, ROI)
□ Retest all pages (refresh + validation)
□ Publish dashboard
```

---

## Status Summary

| Page | Name | Status | Blockers | ETA |
|------|------|--------|----------|-----|
| 1 | Executive Dashboard | ✅ Ready | None | This week |
| 2 | Chain Performance | ✅ Ready | None | This week |
| 3 | Brand Performance | ✅ Ready | None | This week |
| 4 | Category | ✅ Ready | None | This week |
| 5 | Zone Performance | ✅ Ready | None | This week |
| 6 | Store Performance | ⚠️ Ready (partial) | Store Master | This week |
| 7 | BA Stores Performance | ⚠️ Ready (partial) | BA Deployment dates | This week |
| 8 | Expense Dashboard | ⚠️ Ready (partial) | TOT %, Promo % (Q4-Q5) | This week |
| 9 | Profitability Dashboard | ❌ BLOCKED | Finance Q1-Q2 | Next week |
| 10 | Data Quality Dashboard | ✅ Ready | None | This week |

---

**Total effort:** 5–7 hours (Pages 1–8: 5–6 hours, Page 9: 2–3 hours once Finance confirms)

**Next:** Use this spec + Build_Dashboard_Complete_Checklist.md to build in Power BI Desktop

---

**Branch:** claude/safe-powerbi-dashboard-rulings  
**Related files:** PowerQuery_Complete_DataModel.pq, DAX_Complete_Measure_Library.dax, DataModel_Schema_Diagram.md

