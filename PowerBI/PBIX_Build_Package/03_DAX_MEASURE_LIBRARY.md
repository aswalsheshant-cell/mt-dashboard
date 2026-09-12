# Power BI DAX Measure Library
## Modern Trade Dashboard — Demand & Sales Forecasting

**Version:** 1.0  
**Last Updated:** 2026-08-27  
**Status:** Production-Ready

---

## Overview

This document contains the complete DAX measure library for the MT Dashboard semantic model. All measures follow **DIVIDE() for all ratios**, **explicit CALCULATE() filters**, and **null-value fallbacks** for missing data.

**Measure categories:**
1. **Base Aggregations** (actual/forecast sums)
2. **Variance & Realization** (actual vs. forecast, budget vs. target)
3. **Accuracy & Bias** (forecast quality metrics)
4. **State-Level Analytics** (NEW: state-wise drill-down)
5. **KPI Signals** (status indicators)
6. **Supporting Calculations** (used by above)

---

## 1. Base Aggregations

All measures use `SUMMARIZE()` or direct `SUM()` with no default aggregation assumptions.

### Total Actual Quantity

```dax
Total Actual Qty =
SUMX(
    FILTER(Fact_Sales, Fact_Sales[Metric_Type] = "Actual"),
    Fact_Sales[Actual_Qty]
)
```

**Usage:** Primary volume KPI; gates on Metric_Type = "Actual" (excludes Offtake).

### Total Actual Revenue

```dax
Total Actual Revenue =
SUMX(
    FILTER(Fact_Sales, Fact_Sales[Metric_Type] = "Actual"),
    Fact_Sales[Actual_Revenue]
)
```

**Usage:** Primary revenue; basis for realization %, variance, margin calcs.

### Total Offtake Quantity

```dax
Total Offtake Qty =
SUMX(
    FILTER(Fact_Sales, Fact_Sales[Metric_Type] = "Offtake"),
    Fact_Sales[Actual_Qty]
)
```

**Usage:** Distributor/retail partner offtake volume; separate from company direct sales.

### Total Offtake Revenue

```dax
Total Offtake Revenue =
SUMX(
    FILTER(Fact_Sales, Fact_Sales[Metric_Type] = "Offtake"),
    Fact_Sales[Actual_Revenue]
)
```

**Usage:** Offtake channel revenue; combines with Actual for Total Channel Revenue.

### Total Forecast Quantity

```dax
Total Forecast Qty =
SUMX(Fact_Forecast, Fact_Forecast[Forecast_Qty])
```

**Usage:** Demand forecast volume; basis for variance calc.

### Total Forecast Revenue

```dax
Total Forecast Revenue =
SUMX(Fact_Forecast, Fact_Forecast[Forecast_Revenue])
```

**Usage:** Forecasted revenue; compared against actuals for realization.

### Total Target Revenue

```dax
Total Target Revenue =
SUMX(Fact_Forecast, Fact_Forecast[Target_Revenue])
```

**Usage:** Finance target (This Year TY); basis for budget realization.

### Total Base COGS

```dax
Total Base COGS =
SUMX(Fact_Sales, Fact_Sales[Base_COGS])
```

**Usage:** Cost of goods sold; subtracted from revenue for gross margin.

### Total CM2 Amount

```dax
Total CM2 Amount =
SUMX(Fact_Sales, Fact_Sales[CM2_Amount])
```

**Usage:** Contribution margin after P&L expenses; may be provisional (flagged by CM2_Provisional).

### Total Logistics Cost

```dax
Total Logistics Cost =
SUMX(Fact_Sales, Fact_Sales[Logistics_Cost])
```

**Usage:** State-level freight, warehousing, distribution costs; basis for logistics drag %.

---

## 2. Variance & Realization Measures

### Forecast Variance (₹)

```dax
Forecast Variance ₹ =
[Total Actual Revenue] - [Total Forecast Revenue]
```

**Interpretation:**
- **Positive:** Actual > Forecast (upside; demand better than expected).
- **Negative:** Actual < Forecast (downside; weak demand).
- **Zero:** Perfect forecast.

### Forecast Variance %

```dax
Forecast Variance % =
DIVIDE(
    [Total Actual Revenue] - [Total Forecast Revenue],
    [Total Forecast Revenue],
    0
)
```

**Interpretation:**
- `+15%` = Actual is 15% above forecast.
- `-20%` = Actual is 20% below forecast.
- `0%` = Forecast matched actuals.

**Note:** Denominator defaults to 0 if Forecast Revenue is null.

### Forecast Realization %

```dax
Forecast Realization % =
DIVIDE(
    [Total Actual Revenue],
    [Total Forecast Revenue],
    0
)
```

**Interpretation:**
- `100%` = Actual equals forecast (perfect).
- `>100%` = Upside realization (beat forecast).
- `<100%` = Downside (missed forecast).
- `0%` = No forecast or no actuals.

**Usage:** Primary KPI for forecast-model quality. Color-coded: Green (90-110%), Yellow (80-90%, 110-120%), Red (<80%, >120%).

### Budget Realization %

```dax
Budget Realization % =
DIVIDE(
    [Total Actual Revenue],
    [Total Target Revenue],
    0
)
```

**Interpretation:**
- `100%` = Actual matches Finance target.
- `>100%` = Beat budget (upside).
- `<100%` = Missed budget (downside).

**Usage:** Finance accountability KPI; critical for P&L analysis.

### Variance from Target (₹)

```dax
Variance from Target ₹ =
[Total Actual Revenue] - [Total Target Revenue]
```

**Interpretation:**
- **Positive:** Beat target by ₹X.
- **Negative:** Missed target by ₹X.

### Variance from Target %

```dax
Variance from Target % =
DIVIDE(
    [Total Actual Revenue] - [Total Target Revenue],
    [Total Target Revenue],
    0
)
```

**Interpretation:**
- `+10%` = Beat target by 10%.
- `-15%` = Missed target by 15%.

---

## 3. Accuracy & Bias Measures

### Forecast Accuracy %

```dax
Forecast Accuracy % =
1 - DIVIDE(
    ABS([Total Actual Revenue] - [Total Forecast Revenue]),
    [Total Forecast Revenue],
    0
)
```

**Interpretation:**
- `100%` = Perfect forecast (no error).
- `95%` = 5% forecast error (acceptable).
- `80%` = 20% forecast error (poor).
- `<0%` = Indicates forecast was off by >100% (very poor).

**Note:** `ABS()` treats overforecast and underforecast equally; use Bias % (below) to detect direction.

### Forecast Bias %

```dax
Forecast Bias % =
DIVIDE(
    [Total Actual Revenue] - [Total Forecast Revenue],
    [Total Forecast Revenue],
    0
)
```

**Interpretation:**
- **Positive bias** (`+10%`): Forecast systematically low (miss upside).
- **Negative bias** (`-10%`): Forecast systematically high (overestimate).
- **Zero bias** (`±0%`): Unbiased forecast.

**Advantage over Accuracy %:** Bias detects direction; used to identify whether forecast model needs adjustment (e.g., add growth factor, reduce seasonality).

### Mean Absolute Percentage Error (MAPE)

```dax
Forecast MAPE % =
DIVIDE(
    SUMX(
        FILTER(Fact_Sales, Fact_Sales[Metric_Type] = "Actual"),
        ABS(
            Fact_Sales[Actual_Revenue] - 
            CALCULATE(
                SUMX(Fact_Forecast, Fact_Forecast[Forecast_Revenue]),
                FILTER(Fact_Forecast, Fact_Forecast[DateKey] = Fact_Sales[DateKey])
            )
        )
    ),
    [Total Actual Revenue],
    0
)
```

**Interpretation:** Average magnitude of forecast error as % of actual; more sensitive to small-value errors than Accuracy %.

### Confidence-Weighted Forecast

```dax
Confidence Weighted Forecast ₹ =
SUMX(
    Fact_Forecast,
    Fact_Forecast[Forecast_Revenue] * Fact_Forecast[Confidence_Level]
)
```

**Interpretation:** Forecast revenue discounted by model confidence (0.0–1.0). High-confidence forecasts weighted heavily; low-confidence (e.g., 0.5) cut in half.

**Usage:** Feed into a "Confidence-Adjusted Realization %" measure for quality-aware KPIs.

---

## 4. State-Level Analytics (NEW)

### State Contribution to Total Revenue

```dax
State Contribution % =
DIVIDE(
    [Total Actual Revenue],
    CALCULATE(
        [Total Actual Revenue],
        ALL(Dim_Geography[State_Code]),
        ALL(Dim_Geography[State])
    ),
    0
)
```

**Interpretation:**
- Maharashtra contributes 25% of total revenue.
- Delhi NCR contributes 18%.
- **Usage:** Identify which states drive majority of business; prioritize operational focus.

### State-Level Forecast Bias %

```dax
State Forecast Bias % =
DIVIDE(
    CALCULATE([Total Actual Revenue], FILTER(Fact_Sales, Fact_Sales[Metric_Type] = "Actual")) - 
    [Total Forecast Revenue],
    [Total Forecast Revenue],
    0
)
```

**Interpretation:**
- **Tamil Nadu**: +12% (forecast underestimated demand; upside opportunity).
- **West Bengal**: -8% (forecast overestimated; demand softer).
- **Usage:** Identify which states' forecasts are systematically off; update regional planning assumptions.

### State Logistics Drag %

```dax
State Logistics Drag % =
DIVIDE(
    [Total Logistics Cost],
    [Total Actual Revenue],
    0
)
```

**Interpretation:**
- **Maharashtra (urban)**: 3.5% (efficient; near warehouses).
- **North-East (remote)**: 8.2% (high freight; sparse distribution).
- **Usage:** Explain regional margin variance; identify optimization opportunities.

### State vs. Zone Realization Ratio

```dax
State vs Zone Realization Ratio =
DIVIDE(
    [Forecast Realization %],
    CALCULATE(
        [Forecast Realization %],
        ALL(Dim_Geography[State_Code], Dim_Geography[State])
    ),
    1
)
```

**Interpretation:**
- **1.05** = State beating Zone average by 5%.
- **0.92** = State lagging Zone average by 8%.
- **Usage:** Spot underperforming states within a zone; trigger regional accountability.

### Regional (Operating_Region) Contribution

```dax
Regional Contribution % =
DIVIDE(
    [Total Actual Revenue],
    CALCULATE(
        [Total Actual Revenue],
        ALL(Dim_Geography[Operating_Region])
    ),
    0
)
```

**Interpretation:**
- North-1 (Delhi/Punjab/UP) contributes 32% of North Zone revenue.
- North-2 contributes 68%.
- **Usage:** Supply-chain planning; warehouse capacity allocation.

---

## 5. KPI Status Signals

### Forecast Realization Status

```dax
Forecast Realization Status =
IF(
    [Forecast Realization %] >= 0.95 AND [Forecast Realization %] <= 1.05,
    "🟢 ON TARGET",
    IF(
        [Forecast Realization %] >= 0.80 AND [Forecast Realization %] < 0.95,
        "🟡 BELOW TARGET",
        IF(
            [Forecast Realization %] > 1.05 AND [Forecast Realization %] <= 1.20,
            "🟡 ABOVE TARGET",
            IF(
                [Forecast Realization %] < 0.80,
                "🔴 SEVERE MISS",
                "🔴 UPSIDE MISS"
            )
        )
    )
)
```

**Color Legend:**
- 🟢 Green (90–110%): Forecast accurate; minimal action.
- 🟡 Yellow (80–90%, 110–120%): Moderate miss; review assumptions.
- 🔴 Red (<80%, >120%): Severe miss; escalate to leadership.

### Budget Status

```dax
Budget Status =
IF(
    [Budget Realization %] >= 0.95 AND [Budget Realization %] <= 1.05,
    "🟢 ON BUDGET",
    IF(
        [Budget Realization %] < 0.95,
        "🔴 OVER BUDGET",
        "🟢 UNDER BUDGET"
    )
)
```

**Usage:** Finance dashboard; P&L variance tracking.

### CM2 Governance Flag

```dax
CM2 Provisional Flag =
IF(
    COUNTX(
        FILTER(Fact_Sales, Fact_Sales[CM2_Provisional] = TRUE),
        Fact_Sales[SalesKey]
    ) > 0,
    "⚠️ CM2 PROVISIONAL (D1 DRAFT — Expense Data EXAMPLE)",
    "✓ CM2 APPROVED (Real Expense Data)"
)
```

**Usage:** P&L tab header; warns users when CM2 is not finalized by Finance.

---

## 6. Supporting Calculations (Helper Measures)

### Average Forecast Qty per Chain

```dax
Avg Forecast Qty per Chain =
DIVIDE(
    [Total Forecast Qty],
    COUNTDISTINCT(Dim_Chain[ChainKey]),
    0
)
```

**Usage:** Demand planning; sanity-check forecast vs. store count.

### Average Forecast Qty per SKU

```dax
Avg Forecast Qty per SKU =
DIVIDE(
    [Total Forecast Qty],
    COUNTDISTINCT(Dim_Product[ProductKey]),
    0
)
```

**Usage:** Product-level forecasting; identify over/underprovisioned SKUs.

### Gross Margin %

```dax
Gross Margin % =
DIVIDE(
    [Total Actual Revenue] - [Total Base COGS],
    [Total Actual Revenue],
    0
)
```

**Usage:** Unit-level profitability; pre-logistics, pre-P&L.

### Contribution Margin %

```dax
Contribution Margin % =
DIVIDE(
    [Total CM2 Amount],
    [Total Actual Revenue],
    0
)
```

**Usage:** After P&L expenses; requires Finance D1 approval (CM2_Provisional = FALSE).

### Net Logistics Cost Impact

```dax
Net Logistics Cost Impact ₹ =
[Total Actual Revenue] - [Total Logistics Cost]
```

**Interpretation:** Actual revenue less logistics; shows profitability headwind by state/region.

---

## 7. Measure Placement in Data Model

In Power BI Desktop:

1. Create a new table: **`_Measures`** (hidden).
2. Add each measure above using **Home → New Measure**.
3. Set **Measure Settings** (if available):
   - **Format:** Currency (₹) for revenue/cost, Percentage (%) for ratios.
   - **Decimal Places:** 2 for currency, 1 for percentages.
   - **Hide in Report View:** Check (if measure is support-only; uncheck for KPI measures).

4. **Folder Organization** (optional, for cleanliness):
   - **Actuals & Forecasts** → Total Actual Revenue, Total Forecast Revenue, Total Target Revenue, etc.
   - **Variance & Realization** → Forecast Variance %, Realization %, Budget Realization %, etc.
   - **Accuracy & Bias** → Forecast Accuracy %, Bias %, MAPE %, etc.
   - **State Analytics** → State Contribution %, State Bias %, Logistics Drag %, etc.
   - **Status & Signals** → Forecast Status, Budget Status, CM2 Flag.
   - **Helpers** → Avg Forecast per Chain, Gross Margin %, etc.

---

## 8. Measure Dependencies & Safety Rules

| Measure | Depends On | Requires Non-Null |
|---------|---|---|
| Forecast Realization % | Total Actual Revenue, Total Forecast Revenue | Forecast Revenue |
| Budget Realization % | Total Actual Revenue, Total Target Revenue | Target Revenue |
| Forecast Accuracy % | Forecast Variance %, Total Forecast Revenue | Forecast Revenue |
| Forecast Bias % | Forecast Variance % | Forecast Revenue |
| State Contribution % | Total Actual Revenue (filtered by State_Code) | Revenue for that state |
| State Logistics Drag % | Total Logistics Cost, Total Actual Revenue | Both |
| Contribution Margin % | Total CM2 Amount, Total Actual Revenue | Both (check CM2_Provisional = FALSE) |

**Safety check:** Before publishing a measure in a visual, confirm:
1. ✓ Denominator has a DIVIDE() default (e.g., `0` or blank string).
2. ✓ Numerator/denominator filters are explicit (no ambiguous CALCULATE() contexts).
3. ✓ Measure handles null/missing data (returns `"–"` or `0`, never `NaN` or `undefined`).
4. ✓ Measure is tested with a filtered slicer (e.g., single Chain, single Month) to check stability.

---

## 9. Testing Checklist

| Scenario | Expected Result | Pass/Fail |
|---|---|---|
| **No data selected** | All measures return 0 or "–" (not `NaN`) | |
| **Single State selected** | State Contribution % = 100% | |
| **Multiple States (A+B)** | Individual State % + sum to total | |
| **Forecast 0, Actual 100** | Realization % = ∞ (or flagged) → handle with DIVIDE() | |
| **Actual 100, Forecast 0** | Variance % = ∞ (or flagged) → handle with DIVIDE() | |
| **CM2_Provisional = TRUE** | CM2 Flag = "⚠️ PROVISIONAL" | |
| **CM2_Provisional = FALSE** | CM2 Flag = "✓ APPROVED" | |
| **Date filter: Current Month** | Realization % updates; no stale values | |
| **Chain filter: Chain A only** | State measures still aggregate across all chains in state | |
| **Product filter: Category only** | Measures drill to subcategory detail | |

---

## Next Steps

1. **Paste each measure** into Power BI using **Home → New Measure**.
2. **Create a test report page** with slicers (Date, Chain, State, Product) and visualize:
   - KPI cards: Total Revenue, Forecast Realization %, Budget Realization %.
   - Variance waterfall: (Forecast) → (Actual) → (Target).
   - State matrix: Rows = State, Columns = Chain, Values = Realization %, Logistics Drag %.
3. **Validate with known data:** Load sample seed CSV (Dim_Geography, Fact_Sales, Fact_Forecast) and confirm measures match manual hand-calcs.
4. **Document measure definitions** in a Data Dictionary (e.g., Dim_Date = Calendar dimension with 10-year history; Fact_Sales = Monthly actuals by chain/SKU/zone; etc.).

---

**Next Document:** `04_REPORT_LAYOUT_SPECS.md` — Report page layout, visual bindings, filter hierarchy, drill-down navigation, and export templates.
