# Power BI Report Layout Specifications
## Modern Trade Dashboard — Demand & Sales Forecasting

**Version:** 1.0  
**Last Updated:** 2026-08-27  
**Status:** Production-Ready

---

## Overview

This document specifies the **page layout, visual types, field bindings, filter hierarchy, and drill-down navigation** for the MT Dashboard Power BI report.

**Report structure:**
- **Global Slicers** (top, cross-report): Date, Chain, Product Category, State, Zone.
- **5 report pages** (operational → strategic):
  1. **Executive Summary** — KPI strip, trend overview, budget variance.
  2. **Forecast Accuracy** — Realization grid, accuracy scatter, bias by state.
  3. **Regional Performance** — State vs. Chain matrix, geography heatmap.
  4. **Demand vs. Actuals** — Waterfall variance, SKU deviation, forecast model quality.
  5. **P&L & Logistics** — Margin breakdown, state logistics cost, CM2 governance flag.

---

## Global Slicers & Filter Hierarchy

All slicers are positioned at the top of Page 1 (Executive Summary) and appear across all pages via **Report Slicers** (right-side filter pane, optional; or persist slicers on each page for clarity).

| Slicer | Table | Field | Type | Default | Multi-Select | Search |
|---|---|---|---|---|---|---|
| **Date** | Dim_Date | DateKey | Dropdown | Current Month | No | No |
| **Chain** | Dim_Chain | Chain_Name | Dropdown | All | Yes | Yes |
| **Product Category** | Dim_Product | Category | Buttons (dropdown) | All | Yes | Yes |
| **State** | Dim_Geography | State | Dropdown | All | Yes | Yes |
| **Zone** | Dim_Geography | Zone | Buttons | All | Yes | No |

### Slicer Interaction Notes

- **Date slicer:** Cascades to all measures (filters Fact_Sales, Fact_Forecast by DateKey).
- **Chain slicer:** Multi-select allows "compare across chains"; All includes every chain.
- **State slicer:** NEW; enables operational drill-down; when selected, Regional Performance page shows **state-level detail**.
- **Zone slicer:** Convenience filter; selecting one zone auto-populates state list (optional secondary cascade).
- **Product slicer:** Filters by category first; drill to subcategory in Regional Performance page.

---

## Page 1: Executive Summary

**Purpose:** C-suite overview; KPI status, period-over-period trend, budget alignment.

### Layout (Recommended: 16:9 Widescreen)

```
┌─────────────────────────────────────────────────────────────────────┐
│  [Date ▼] [Chain ▼] [Category ▼] [State ▼] [Zone ▼]  (Global Slicers) │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌─────────┐  ┌──────────┐  ┌─────────┐  ┌──────────┐  ┌─────────┐ │
│  │ Total   │  │Realization│ │ Budget  │  │Forecast  │  │CM2      │ │
│  │Revenue  │  │    %      │  │Realization│ Accuracy │  │Status   │ │
│  │ ₹341 Cr │  │   101%    │  │  98%     │  │   88%    │  │⚠️ DRAFT│ │
│  │🟢       │  │🟢        │  │🟢       │  │🟡      │  │        │ │
│  └─────────┘  └──────────┘  └─────────┘  └──────────┘  └─────────┘ │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ Trend: Actual vs. Forecast (Line+Column Combo)              │  │
│  │                                                               │  │
│  │     ₹                                                         │  │
│  │  Actual ─── Forecast ─── Target                              │  │
│  │  ▲▲▲      ▼▼▼      ───                                       │  │
│  │                                                               │  │
│  │  Apr    May   Jun   Jul   Aug   Sep  ...                     │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                       │
│  ┌────────────────────┐  ┌────────────────────────────────────────┐ │
│  │ Variance Waterfall │  │ State Contribution (Top 5)             │ │
│  │                    │  │ Maharashtra     25% ███████████        │ │
│  │ Forecast ─┐        │  │ Delhi NCR       18% ██████             │ │
│  │   ↓ ₹+12 │─ Actual │  │ Gujarat         15% █████              │ │
│  │ Target  ─┤        │  │ Tamil Nadu      12% ████                │ │
│  │ Variance │        │  │ Other           30% ██████████          │ │
│  │   ₹-8   │┘        │  │                                        │ │
│  └────────────────────┘  └────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

### Visuals & Field Bindings

| Visual | Type | Field Bindings | Notes |
|---|---|---|---|
| **Revenue Card** | KPI Card | Value: [Total Actual Revenue]; Format: ₹ (0 decimals) | Show trend: YoY or MoM (optional) |
| **Realization % Card** | KPI Card | Value: [Forecast Realization %]; Format: 0.0%; Status: [Forecast Status] | Green if 95-105% |
| **Budget Realization % Card** | KPI Card | Value: [Budget Realization %]; Format: 0.0%; Status: [Budget Status] | Green if ≥95% |
| **Forecast Accuracy Card** | KPI Card | Value: [Forecast Accuracy %]; Format: 0.0% | Yellow if <85% |
| **CM2 Status Card** | Card/Text | Value: [CM2 Governance Flag] | ⚠️ if Provisional; ✓ if Approved |
| **Trend Line+Column** | Combo Chart (Line+Column) | X-axis: Dim_Date[Month]; Series: [Total Actual Revenue] (Line), [Total Forecast Revenue] (Column), [Total Target Revenue] (Line, dashed) | Color: Actual=Blue, Forecast=Orange, Target=Gray |
| **Variance Waterfall** | Waterfall Chart | X-axis: Variance Type (Forecast → +Variance → Actual → -Variance → Target); Y-axis: [Forecast Variance ₹] | Shows ↑ upside or ↓ downside visually |
| **State Contribution** | Stacked Horizontal Bar | Y-axis: Top 5 States (sorted by [Total Actual Revenue]); X-axis: [State Contribution %] | Color: state-wise palette; hover = absolute ₹ |

### Interactions

- **Date slicer → all visuals:** Changes all trend lines, waterfall, KPI values.
- **Chain slicer → all visuals:** Filters to selected chain(s); multi-chain shows combined KPIs.
- **State slicer → visuals:** Filters State Contribution chart; if single state selected, all above metrics recalc for that state.
- **Drill-down (optional):** Click State Contribution bar → navigates to **Page 3 (Regional Performance)** filtered to that state.

---

## Page 2: Forecast Accuracy & Bias

**Purpose:** Data science / forecast model quality; identify systematic over/underestimation.

### Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│  [Date ▼] [Chain ▼] [Category ▼] [State ▼] [Zone ▼]  (Global Slicers) │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────┐  ┌──────────────┐  ┌─────────────┐                    │
│  │Accuracy  │  │Bias %        │  │MAPE %       │                    │
│  │  88.2%   │  │  +5.3%       │  │   12.1%     │                    │
│  │🟡       │  │ 🟢 (slight    │  │🟡          │                    │
│  │(Tune)    │  │  overestimate)   │(Improve)    │                    │
│  └──────────┘  └──────────────┘  └─────────────┘                    │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ Realization % by State (Matrix / Heatmap)                    │  │
│  │                                                               │  │
│  │ State           Realization %   Status                       │  │
│  │ Maharashtra        105%         🟢 ON TARGET                │  │
│  │ Delhi NCR          98%          🟢 ON TARGET                │  │
│  │ Gujarat            88%          🟡 BELOW TARGET             │  │
│  │ Tamil Nadu        112%          🟡 ABOVE TARGET             │  │
│  │ West Bengal        75%          🔴 SEVERE MISS              │  │
│  │ Karnataka          94%          🟢 ON TARGET                │  │
│  │ Punjab             82%          🟡 BELOW TARGET             │  │
│  │ Uttar Pradesh      91%          🟢 ON TARGET                │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                       │
│  ┌──────────────────────────┐  ┌──────────────────────────────────┐ │
│  │ Accuracy Scatter Plot    │  │ Bias by State (Column)           │ │
│  │ (Actual vs. Forecast)    │  │ % Over/Underestimation           │ │
│  │ Each dot = State/Chain   │  │                                  │ │
│  │ Position: [Forecast] vs  │  │  Maharashtra    +2%   ┃          │ │
│  │           [Actual]       │  │  Delhi          -3%   ┃          │ │
│  │ Color: [Confidence Lvl]  │  │  Gujarat        +8%   ┃┃         │ │
│  │ Size: [Volume]           │  │  Tamil Nadu    -12%   ┃          │ │
│  │ 45° line = perfect       │  │  West Bengal   -18%   ┃          │ │
│  │                          │  │  Karnataka      +1%   ┃          │ │
│  │ Above line = Underesti.  │  │  ...                              │ │
│  │ Below line = Overesti.   │  │                                  │ │
│  └──────────────────────────┘  └──────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

### Visuals & Field Bindings

| Visual | Type | Field Bindings | Notes |
|---|---|---|---|
| **Accuracy Card** | KPI Card | [Forecast Accuracy %] | Target: ≥90% (green); 80-90% (yellow); <80% (red) |
| **Bias Card** | KPI Card | [Forecast Bias %] | Positive = underestimated; Negative = overestimated |
| **MAPE Card** | KPI Card | [Forecast MAPE %] | Mean Absolute % Error; target <15% |
| **Realization Matrix** | Table / Matrix | Rows: Dim_Geography[State]; Columns: Static (1 column); Values: [Forecast Realization %], [Forecast Status] | Conditional formatting: Color cells Green/Yellow/Red by status |
| **Accuracy Scatter** | Scatter Plot | X-axis: [Total Forecast Revenue]; Y-axis: [Total Actual Revenue]; Legend: Dim_Geography[State]; Size: [Total Forecast Qty]; Color: [Confidence Weighted Forecast] | 45° reference line added manually (optional); hover = State name + exact ₹ values |
| **Bias Column Chart** | Column Chart | X-axis: Top 10 States (by [Forecast Bias %]); Y-axis: [Forecast Bias %]; Color: Red if negative, Green if positive | Y-axis axis line at 0%; hover = Bias % value |

### Interactions

- **State slicer:** Filters all visuals to selected state(s).
- **Date slicer:** Changes accuracy/bias calculation for that month.
- **Drill-down (optional):** Click State in Scatter → filter all other visuals on that state; click Region in Bias Column → drill to State detail.

---

## Page 3: Regional Performance & State Analytics

**Purpose:** Operational accountability by state; compare chain performance within state.

### Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│  [Date ▼] [Chain ▼] [Category ▼] [State ▼] [Zone ▼]  (Global Slicers) │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                  │
│  │ State Share │  │ Logistics   │  │ Forecast    │                  │
│  │    of Zone  │  │ Drag %      │  │ Bias %      │                  │
│  │   (26%)     │  │   (5.2%)    │  │  (+3.1%)    │                  │
│  │ 🟢          │  │ 🟡          │  │ 🟢          │                  │
│  └─────────────┘  └─────────────┘  └─────────────┘                  │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ State vs. Chain Performance (Cross-Tab Matrix)               │  │
│  │                                                               │  │
│  │  State / Chain  │  Reliance   DMart    Aditya    Others       │  │
│  │  ───────────────┼──────────────────────────────────────      │  │
│  │  Maharashtra    │   98% 🟢    105% 🟢   92% 🟢   89% 🟡      │  │
│  │  Delhi NCR      │  102% 🟢    96% 🟢   101% 🟢   87% 🟡      │  │
│  │  Gujarat        │   85% 🟡    92% 🟢   88% 🟡   81% 🔴       │  │
│  │  Tamil Nadu     │  108% 🟢   115% 🟡   105% 🟢  102% 🟢      │  │
│  │  West Bengal    │   71% 🔴    79% 🟡   76% 🟡   68% 🔴       │  │
│  │  Karnataka      │   99% 🟢   102% 🟢   96% 🟢   94% 🟢       │  │
│  │                                                               │  │
│  │  Values: [Forecast Realization %]; Colors: Status           │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ Geographic Heatmap (Filled Map)                              │  │
│  │ Color Saturation: Realization % or Logistics Drag %          │  │
│  │                                                               │  │
│  │     [Map of India by State; hover = State name + metric]     │  │
│  │     Green shades = Realization 90-110%                       │  │
│  │     Yellow shades = Realization 80-90% or 110-120%           │  │
│  │     Red shades = Realization <80% or >120%                   │  │
│  │                                                               │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ Logistics Cost by State (Bar Chart)                          │  │
│  │ Sorted by Logistics Drag %                                   │  │
│  │                                                               │  │
│  │ Maharashtra   (3.2%)  ║                                      │  │
│  │ Delhi NCR     (3.8%)  ║                                      │  │
│  │ Gujarat       (4.5%)  ║                                      │  │
│  │ Karnataka     (5.1%)  ║                                      │  │
│  │ Tamil Nadu    (6.3%)  ║                                      │  │
│  │ West Bengal   (7.9%)  ║                                      │  │
│  │ Punjab        (6.2%)  ║                                      │  │
│  │ Uttar Pradesh (8.1%)  ║                                      │  │
│  │                                                               │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### Visuals & Field Bindings

| Visual | Type | Field Bindings | Notes |
|---|---|---|---|
| **State Contribution Card** | KPI Card | [State Contribution %] | Shows % of total/zone revenue from selected state |
| **Logistics Drag Card** | KPI Card | [State Logistics Drag %] | Target: <5%; Yellow if 5-7%, Red if >7% |
| **Forecast Bias Card** | KPI Card | [State Forecast Bias %] | Shows direction of model bias (+ = underestimate) |
| **State vs. Chain Matrix** | Table / Matrix | Rows: Dim_Geography[State]; Columns: Dim_Chain[Chain_Name]; Values: [Forecast Realization %], [Forecast Status] (color); Slicers: Date, Product Category | Conditional cell coloring: Green/Yellow/Red by Forecast Status; hover = absolute ₹ values |
| **Filled Map** | Filled Map (Power BI Native) | Location: Dim_Geography[State] (or Dim_Geography[State_Code]); Color: [Forecast Realization %] or [State Logistics Drag %] (toggle option); Saturation: intensity of metric | Tooltip: State name, Realization %, Logistics Drag %, Revenue ₹ |
| **Logistics Cost Bar** | Column Chart | Y-axis: Dim_Geography[State] (sorted by [Logistics Drag %]); X-axis: [State Logistics Drag %]; Color: single color (blue) or gradient (green→red by logistics intensity) | Target reference line at 5%; hover = Drag % and absolute ₹ cost |

### Interactions

- **State slicer:** Single state selected → all visuals drill to that state; multi-select → aggregate across states.
- **Chain slicer:** Filters State vs. Chain Matrix to selected chain(s).
- **Drill-down (optional):** Click State in Matrix → filter Page 2 (Accuracy) to that state; Click State in Heatmap → same drill.

---

## Page 4: Demand vs. Actuals & Waterfall Variance

**Purpose:** Deep-dive variance analysis; where did we miss forecast?

### Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│  [Date ▼] [Chain ▼] [Category ▼] [State ▼] [Zone ▼]  (Global Slicers) │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐               │
│  │Variance ₹   │  │Variance %    │  │Top Missing   │               │
│  │ -₹12.3 Cr   │  │  -5.8%       │  │ Chain       │               │
│  │ 🟡 DOWNSIDE │  │ 🟡 BELOW     │  │ DMart -3.2% │               │
│  └─────────────┘  └──────────────┘  └──────────────┘               │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ Waterfall: Forecast → Demand → Actuals → Target              │  │
│  │                                                               │  │
│  │      ₹ Cr                                                     │  │
│  │  80 │                                                         │  │
│  │  60 │  ╱╲ Forecast       Demand Driver Analysis               │  │
│  │  40 │ ╱  ╲ ↓ Volume Variance                                  │  │
│  │  20 │╱    ╲    - Chain X: -2.1 Cr (qty miss)                 │  │
│  │   0 │      ╲   ↓ Mix Variance                                 │  │
│  │ -20 │       ╲  - Category A: +0.5 Cr (premium shift)         │  │
│  │     │        ╲ ↓ Price Variance                              │  │
│  │     │ Actual  ╲ - Region B: -1.8 Cr (discounting)            │  │
│  │     │                                                         │  │
│  │     └──────────────────────────────────────────────────────  │  │
│  │     Forecast → Actual → Target                                │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ SKU Deviation from Forecast (Top 20 by Absolute Miss)        │  │
│  │                                                               │  │
│  │  SKU_MAMAEA001 (Mamaearth FW 150ml)  Forecast: 2.1L, Actual: │  │
│  │                                       1.8L  🟡  -14% MISS      │  │
│  │  SKU_ARATA001 (Arata Oil 200ml)       Forecast: 1.2L, Actual: │  │
│  │                                       1.4L  🟢  +17% BEAT      │  │
│  │  SKU_HONASA001 (Brand X Lotion)       Forecast: 3.0L, Actual: │  │
│  │                                       2.5L  🟡  -17% MISS      │  │
│  │  ... (17 more)                                                │  │
│  │                                                               │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ Forecast Model Quality (Confidence Weighted Realization %)   │  │
│  │                                                               │  │
│  │ Forecast    Actual      Confidence  Adj. Realization         │  │
│  │ ₹500 Cr     ₹505 Cr     0.85        94.1%  (penalized        │  │
│  │                                       for low confidence)      │  │
│  │ Shows: High-confidence forecasts are more accurate than      │  │
│  │        low-confidence (model is well-calibrated).            │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### Visuals & Field Bindings

| Visual | Type | Field Bindings | Notes |
|---|---|---|---|
| **Variance ₹ Card** | KPI Card | [Forecast Variance ₹] | Positive (green) = upside; Negative (red) = downside; format: ₹ 0.0 Cr |
| **Variance % Card** | KPI Card | [Forecast Variance %] | Percentage; color by status |
| **Top Missing Chain Card** | Card / Text | Value: Top chain by [Forecast Variance ₹] (TOPN(1)); Format: Chain_Name + Variance % | Dynamically updates; shows biggest miss |
| **Waterfall Chart** | Waterfall Chart (Power BI Native) | X-axis: Categories (Forecast, +Volume Variance, +Mix Variance, +Price Variance, Actual, Variance to Target); Y-axis: [Forecast Variance ₹] decomposed | Volume/Mix/Price variances computed via DAX or Python; each column shows contribution to total variance |
| **SKU Deviation Table** | Table / Matrix | Columns: Dim_Product[SKU_Code], Dim_Product[Product_Name], [Total Forecast Qty], [Total Actual Qty], [Forecast Variance %], [Forecast Status]; Sort: [Forecast Variance ₹] (descending by absolute value) | Highlight top 20 misses (worst first); conditional cell color by Status |
| **Confidence Calibration Table** | Table | Columns: Dim_Forecast[Confidence_Level] (binned: 0-0.5, 0.5-0.75, 0.75-1.0), [Forecast Realization %] (aggregated), Record Count; Sort: Confidence Level | Shows: Does higher confidence → better accuracy? If yes, model is well-calibrated |

### Interactions

- **Date slicer:** Changes all variance calculations for that month.
- **Chain slicer:** Multi-chain variance combined; single chain → drill to that chain's SKU deviations.
- **Product Category slicer:** Filters SKU deviation table to that category; waterfall recalculates on category mix.
- **Drill-down (optional):** Click SKU in table → drill to Daily Detail page (if available) to see store-level offtake.

---

## Page 5: P&L & Logistics Analysis

**Purpose:** Finance accountability; margin analysis, CM2 governance flag, state-level cost allocation.

### Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│  [Date ▼] [Chain ▼] [Category ▼] [State ▼] [Zone ▼]  (Global Slicers) │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ⚠️  CM2 PROVISIONAL — Formula Status: DRAFT                        │
│      Example P&L expense rows loaded. Banner clears when Finance    │
│      updates config/cm2_formula.csv to APPROVED and real expenses   │
│      are loaded. See documentation for details.                    │
│                                                                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌────────────────┐  ┌──────────────┐  ┌──────────────┐             │
│  │Gross Margin %  │  │Contribution  │  │Total CM2     │             │
│  │    42.3%       │  │ Margin %     │  │ Amount       │             │
│  │🟢              │  │    18.5%     │  │ ₹63.2 Cr     │             │
│  │                │  │🟡 (Provisional)│ │ (⚠️ Draft)  │             │
│  └────────────────┘  └──────────────┘  └──────────────┘             │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ Margin Bridge: Revenue → COGS → Gross → P&L → CM2            │  │
│  │                                                               │  │
│  │      ₹ Cr                                                     │  │
│  │  100 │ ╱╲ Revenue                                             │  │
│  │   80 │╱  ╲ -COGS                                              │  │
│  │   60 │    ╲ Gross Margin (₹144.5 Cr, 42.3%)                  │  │
│  │   40 │     ╲ -P&L Expenses (₹81.3 Cr)                        │  │
│  │   20 │      ╲ CM2 (₹63.2 Cr, 18.5%)                           │  │
│  │    0 │       ╲                                                │  │
│  │      │        ╲                                               │  │
│  │      └──────────────────────────────────────────────────────  │  │
│  │      Revenue → COGS → Gross → P&L → CM2                      │  │
│  │                                                               │  │
│  │      Note: P&L expense data EXAMPLE ONLY (Provisional Flag)  │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ Logistics Cost & Drag % by State                             │  │
│  │                                                               │  │
│  │ State           Logistics $  Drag %   Rank                   │  │
│  │ West Bengal     ₹28.4 Cr     7.8%     1 (Highest)            │  │
│  │ Uttar Pradesh   ₹24.1 Cr     7.1%     2                      │  │
│  │ Tamil Nadu      ₹19.2 Cr     6.2%     3                      │  │
│  │ Punjab          ₹16.3 Cr     5.9%     4                      │  │
│  │ Gujarat         ₹15.8 Cr     4.5%     5                      │  │
│  │ Karnataka       ₹14.2 Cr     4.1%     6                      │  │
│  │ Delhi NCR       ₹12.6 Cr     3.8%     7                      │  │
│  │ Maharashtra     ₹11.4 Cr     3.2%     8 (Lowest)             │  │
│  │                                                               │  │
│  │ Opportunity: Optimize remote-state distribution; consider    │  │
│  │             regional consolidation hubs.                     │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ P&L Expense Breakdown (Stacked Bar by Expense Category)      │  │
│  │ (Only shown if CM2 is APPROVED)                              │  │
│  │                                                               │  │
│  │ Salaries & Incentives    ║ 40% of total P&L                 │  │
│  │ Logistics & Transportation║ 35% of total P&L                 │  │
│  │ Marketing & Promotions   ║ 15% of total P&L                 │  │
│  │ Other (Rent, Utils, etc) ║ 10% of total P&L                 │  │
│  │                                                               │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### Visuals & Field Bindings

| Visual | Type | Field Bindings | Notes |
|---|---|---|---|
| **CM2 Flag Text Box** | Text Box / DAX String | Value: [CM2 Provisional Flag]; Color: Amber if Provisional; Green if Approved | Sticky at top; warns users when data is example-only |
| **Gross Margin % Card** | KPI Card | [Gross Margin %] | Format: 0.0%; Target: >40%; Color if below target |
| **Contribution Margin % Card** | KPI Card | [Contribution Margin %] | Format: 0.0%; Target: >18%; Warning if CM2_Provisional = TRUE |
| **Total CM2 Card** | KPI Card | [Total CM2 Amount]; Format: ₹ 0.0 Cr; Warning: "⚠️ Example Data Only" if CM2_Provisional = TRUE | Disclaimer under card explaining provisional status |
| **Margin Bridge Waterfall** | Waterfall Chart | X-axis: Waterfall steps (Revenue, -COGS, Gross Margin, -P&L Expenses, CM2); Y-axis: [Total Actual Revenue], [Total Base COGS], [Total CM2 Amount] as waterfall segments | Each column = step in P&L; hover = absolute ₹ and % of revenue |
| **Logistics by State** | Table / Matrix | Rows: Dim_Geography[State] (sorted by [State Logistics Drag %] descending); Columns: [Total Logistics Cost] (format: ₹), [State Logistics Drag %] (format: 0.0%), Ranking; Tooltip: State name, cost ₹, drag % | Highlight top 3 states by cost (red background); bottom 3 (green) |
| **P&L Expense Breakdown** | Stacked Column Chart | X-axis: Expense Category (Salaries, Logistics, Marketing, Other); Y-axis: Expense ₹ (stacked); Color: unique per category | Only visible if CM2 is APPROVED; hide entire visual if Provisional; filter on Fact_Sales where CM2_Provisional = FALSE |

### Interactions

- **State slicer:** Drill to state-level P&L and logistics cost; multi-state shows aggregate.
- **Date slicer:** Changes all margin/cost calculations for that month.
- **Chain slicer:** Shows P&L by chain (if available in source data).
- **CM2 Flag interaction:** If CM2_Provisional = TRUE, hide P&L Expense Breakdown and show warning banner; if FALSE, show full P&L detail.

---

## Report-Level Settings & Navigation

### Cross-Page Navigation (Buttons / Drill-through)

Add navigation buttons at the top-left of each page:

- **Page 1 (Executive Summary)** ← Current Page
- **Page 2 (Forecast Accuracy)** → Click → Navigate
- **Page 3 (Regional Performance)** → Click → Navigate
- **Page 4 (Demand vs. Actuals)** → Click → Navigate
- **Page 5 (P&L & Logistics)** → Click → Navigate

### Breadcrumb / Context Display

Top-left corner (all pages):

```
📍 Reporting Context:
   Date: [DateKey selected]
   Chain(s): [Chain names or "All"]
   State(s): [State names or "All"]
   Category: [Category or "All"]
```

Updates dynamically as slicers change.

### Export & Print Settings

- **Each page:** Add a "Download PDF" or "Export to Excel" button (optional; Power BI Desktop Export button available by default).
- **Excel exports:** Remove slicers from export; include measure definitions as a separate sheet (Data Dictionary).
- **PDF exports:** Hide slicers and context breadcrumb; print all charts at high resolution.

---

## Performance Optimization

1. **Aggregated tables:** Pre-aggregate fact tables by [DateKey, ChainKey, ProductKey, State_Code] for snappy matrix/waterfall rendering.
2. **Incremental refresh:** On Fact_Sales and Fact_Forecast, enable Power BI incremental refresh to load only the latest month (see `02_POWER_QUERY_TRANSFORMS.md` Section 5).
3. **Visual-level filtering:** Use Report-Level Tooltips sparingly (they slow rendering); prefer drill-through for deep dives.
4. **Measure optimization:** Pre-calculate monthly aggregates in a separate `Fact_Sales_Agg` table if Fact_Sales >50M rows; update daily/weekly rather than computing on-demand.

---

## Testing & Deployment Checklist

| Checklist Item | Pass/Fail | Notes |
|---|---|---|
| All 5 pages load without DAX errors | | Check DAX calculation engine logs |
| Slicers cascade correctly (Date → Chain → State) | | Multi-select works for Chain, Category, State |
| Visuals update when slicers change | | No frozen/stale values |
| KPI cards show correct status colors (Green/Yellow/Red) | | Verify threshold boundaries |
| CM2 Flag toggles between ⚠️ and ✓ based on CM2_Provisional | | Hide P&L Expense chart when Provisional = TRUE |
| Drill-downs (State → Accuracy page) work | | Navigation buttons tested |
| Tooltips display (hover on visuals) | | All charts show value on hover |
| Text formatting: Currency (₹ 0.0 Cr), % (0.0%), Volume (0 units) | | Check all visuals; remove trailing decimals if not needed |
| Print preview: No content overflow, slicers hidden | | PDF export readable |
| Performance: All visuals load <2 sec after slicer change | | Monitor DAX query time in Performance Analyzer |
| Dark mode (if enabled): Text readable, colors consistent | | Test in Power BI "Appearance" theme toggle |

---

## Next Steps

1. **Build all 5 pages** in Power BI Desktop using visuals & field bindings above.
2. **Load sample data** (seed CSVs from Section 5 of `02_POWER_QUERY_TRANSFORMS.md`).
3. **Test slicers and drill-downs** (verify cascading filters work).
4. **Validate measures** against hand-calculated values (e.g., Realization % for a single chain should match manual calc).
5. **Apply formatting** (colors, fonts, alignment) per design specs.
6. **Publish to Power BI Service** (Premium capacity recommended for >100M row fact tables).
7. **Set refresh schedule** (Daily for Fact_Sales, Weekly for Fact_Forecast).
8. **Enable drill-through** (Page 2 → Page 3, etc.) and test cross-page navigation.

---

**Deliverables:**
- ✅ `01_SEMANTIC_MODEL_SCHEMA.md` — Star schema design
- ✅ `02_POWER_QUERY_TRANSFORMS.md` — Power Query M code (copy-paste ready)
- ✅ `03_DAX_MEASURE_LIBRARY.md` — All DAX measures (base + advanced)
- ✅ `04_REPORT_LAYOUT_SPECS.md` — Report pages, visuals, bindings (this document)

**Final step:** Create sample seed data CSV files and test the complete build package.
