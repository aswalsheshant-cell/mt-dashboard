# Critical Operational & Financial Metrics
## Modern Trade Dashboard — Supply Chain, Trade Spend & Inventory Analytics

**Version:** 1.0  
**Last Updated:** 2026-08-27  
**Status:** Production-Ready

---

## Overview

This document defines critical operational metrics that complete the dashboard suite:
1. **Supply Chain Fulfillment** (Fill Rate, Lost Sales)
2. **Trade Spend & Promotional Effectiveness** (ROI, Net ASP)
3. **Inventory Health** (Days of Cover, Stock-out Risk)
4. **Category Penetration** (Listing %, Distribution Reach)

---

## 1. Supply Chain & Fulfillment Metrics

### Fill Rate (Case Fill Rate / CFR %)

**Business Question:** Did demand forecasting miss occur because stores had insufficient stock?

```dax
Fill Rate % =
DIVIDE(
    SUMX(Fact_Sales, Fact_Sales[Delivered_Qty]),
    SUMX(Fact_Sales, Fact_Sales[Ordered_Qty]),
    0
)
```

**Interpretation:**
- **100%** = All orders fulfilled (no stock-outs)
- **85-95%** = Minor stock constraints (acceptable)
- **<85%** = Significant fulfillment issues (investigate)
- **>100%** = Over-delivery or return adjustments

**Format:** Percentage (0.0%)  
**Color Coding:**
- 🟢 Green: ≥95%
- 🟡 Yellow: 85-95%
- 🔴 Red: <85%

### Lost Sales Opportunity (Unfulfilled Demand in ₹)

```dax
Lost Sales Opportunity ₹ =
SUMX(
    Fact_Sales,
    (Fact_Sales[Ordered_Qty] - Fact_Sales[Delivered_Qty]) * 
    (Fact_Sales[Actual_Revenue] / DIVIDE(Fact_Sales[Actual_Qty], 1, 1))
)
```

**Interpretation:**
- Monetary value of demand not served due to stock-outs
- Identifies revenue leakage by state, chain, SKU
- High values → trigger inventory planning review

**Format:** Currency (₹ 0.0 Cr)  
**Usage:** Sort chains/states by this metric to identify fulfillment bottlenecks

### Stock-out Flag (by Chain × SKU)

```dax
Has_Stockout_Flag =
IF(
    SUMX(Fact_Sales, Fact_Sales[Delivered_Qty]) < 
    SUMX(Fact_Sales, Fact_Sales[Ordered_Qty]),
    "⚠️ STOCKOUT DETECTED",
    "✓ Full Fulfillment"
)
```

**Usage:** Display in chain performance matrix; flag Tier 1 accounts for immediate action

---

## 2. Trade Spend & Promotional Effectiveness

### Trade Spend % of Gross Sales

**Business Question:** How much of revenue is consumed by promotional schemes and trade discounts?

```dax
Trade Spend % =
DIVIDE(
    SUMX(Fact_Sales, Fact_Sales[Scheme_Adjustment]) + 
    SUMX(Fact_Sales, Fact_Sales[Promo_Cost]),
    [Total Actual Revenue],
    0
)
```

**Interpretation:**
- **3-5%** of revenue (healthy; efficient promotion)
- **5-8%** (moderate; competitive pressure)
- **>8%** (pressure; margin erosion)

**Format:** Percentage (0.0%)  
**Benchmark:** DMart 4%, Reliance 5.5%, Tier 2 chains 6.5%

### Promo Lift % (Incremental Sales During Promotion)

```dax
Promo Lift % =
VAR BaselineSales = CALCULATE(
    [Total Actual Revenue],
    Fact_Sales[Promo_Cost] = 0  -- Non-promo periods only
)
VAR PromoSales = CALCULATE(
    [Total Actual Revenue],
    Fact_Sales[Promo_Cost] > 0  -- Promo periods only
)
RETURN
    DIVIDE(
        PromoSales - BaselineSales,
        BaselineSales,
        0
    )
```

**Interpretation:**
- **Positive Lift:** Promotion drove incremental sales (ROI > 1)
- **Negative Lift:** Promotion cannibalized baseline; pure discount
- **>20% Lift:** Highly effective promotion (repeat)
- **<5% Lift:** Question ROI; consider alternative tactics

**Format:** Percentage (0.0%)

### Net Realized Price per Unit (ASP Erosion)

```dax
Net Realized Price per Unit =
DIVIDE(
    [Total Actual Revenue] - 
    (SUMX(Fact_Sales, Fact_Sales[Scheme_Adjustment]) + 
     SUMX(Fact_Sales, Fact_Sales[Promo_Cost])),
    SUMX(Fact_Sales, Fact_Sales[Actual_Qty]),
    0
)
```

**Interpretation:**
- Shows **effective price** after all discounts
- Compare to baseline list price (from Dim_Product)
- **Gap = Price erosion due to trade spend**

**Format:** Currency (₹ 0.00)  
**Usage:** Track price realization by chain; identify excessive discounting

### Trade Spend ROI %

```dax
Trade Spend ROI % =
DIVIDE(
    [Promo Lift %] * [Total Actual Revenue],
    SUMX(Fact_Sales, Fact_Sales[Scheme_Adjustment]) + 
    SUMX(Fact_Sales, Fact_Sales[Promo_Cost]),
    0
)
```

**Interpretation:**
- **ROI > 1.0** = Promo generated ≥₹1 incremental sales per ₹1 spent (profitable)
- **0.5-1.0** = Marginal ROI (review spend allocation)
- **<0.5** = Poor ROI (likely cannibalizing baseline)

**Format:** 0.00x (e.g., 1.35x means ₹1.35 return per ₹1 invested)

---

## 3. Inventory Health & Stock Cover

### Days of Sales Inventory (DSI / Days of Cover)

**Business Question:** How many days of demand do we have in stock at RDCs and chain warehouses?

```dax
Days of Cover =
DIVIDE(
    SUMX(Fact_Inventory, Fact_Inventory[Closing_Stock_Units]),
    DIVIDE(
        [Total Actual Qty 30D],  -- 30-day moving average
        30,
        0
    ),
    0
)
```

**Interpretation:**
- **7-14 days:** Optimal (JIT inventory; low working capital)
- **14-30 days:** Normal (buffer for demand variance)
- **30-45 days:** High (working capital block; consider markdown)
- **>45 days:** Excessive (risk of obsolescence, markdown losses)

**Format:** Integer (# of days)  
**Color Coding:**
- 🟢 Green: 7-30 days
- 🟡 Yellow: 30-45 days
- 🔴 Red: <7 days OR >45 days

### Stock-out Risk Flag (by Regional Hub)

```dax
Stockout_Risk_Status =
IF(
    [Days of Cover] < 7,
    "🔴 CRITICAL: <7 days (Immediate Action Required)",
    IF(
        [Days of Cover] < 14,
        "🟡 WARNING: <14 days (Monitor Closely)",
        IF(
            [Days of Cover] > 45,
            "🟠 OVERSTOCK: >45 days (Plan Markdown)",
            "🟢 HEALTHY: 14-45 days (Normal Operation)"
        )
    )
)
```

**Usage:** Display on supply chain dashboard; trigger alerts if <7 or >45 days

### Regional Hub Inventory (Pivot View)

| Hub | SKU | Closing Stock | Days of Cover | Status | Action |
|-----|-----|---|---|---|---|
| DC_MH_01 | SKU-101 | 1,250 units | 18 days | 🟢 | Monitor |
| DC_MH_01 | SKU-201 | 450 units | 5 days | 🔴 | URGENT: Replenish |
| WH_GJ_01 | SKU-102 | 3,200 units | 52 days | 🟠 | Plan markdown |

---

## 4. Category Penetration & Store Listing

### SKU Distribution % (Store Listing Breadth)

**Business Question:** How many chains/stores are listing our core SKUs?

```dax
SKU Distribution % =
VAR TotalChainCount = DISTINCTCOUNT(Dim_Chain[Chain_ID])
VAR ListedChainCount = DISTINCTCOUNT(
    FILTER(
        Fact_Sales,
        Fact_Sales[Actual_Qty] > 0  -- Only counted if sold in period
    ),
    Dim_Chain[Chain_ID]
)
RETURN
    DIVIDE(ListedChainCount, TotalChainCount, 0)
```

**Interpretation:**
- **>90%:** Core SKU (must-stock; high compliance)
- **70-90%:** Key SKU (good penetration; target for growth)
- **50-70%:** Secondary SKU (selective listing)
- **<50%:** Emerging/legacy SKU (limited availability)

**Format:** Percentage (0.0%)  
**Usage:** Create matrix: Rows = Brand, Columns = Chain, Values = SKU Distribution %

### Weighted Distribution (WD %)

**Business Question:** What % of Modern Trade sales volume is reachable by our SKUs?

```dax
Weighted Distribution % =
DIVIDE(
    SUMX(
        FILTER(
            Fact_Sales,
            Fact_Sales[Actual_Qty] > 0
        ),
        Fact_Sales[Actual_Revenue]
    ),
    SUMX(Fact_Sales, Fact_Sales[Actual_Revenue]),
    0
)
```

**Interpretation:**
- **>80%:** Excellent penetration across high-volume chains
- **60-80%:** Good reach; some gaps in smaller accounts
- **40-60%:** Selective penetration; growth opportunity
- **<40%:** Limited reach; new SKU or chain resistance

**Format:** Percentage (0.0%)  
**Usage:** Track by brand/category/pack size

### Category Penetration (Brand Market Share by Chain)

```dax
Brand Penetration % in Chain =
DIVIDE(
    SUMX(
        FILTER(
            Fact_Sales,
            Fact_Sales[Brand] = SELECTEDVALUE(Dim_Product[Brand])
        ),
        Fact_Sales[Actual_Revenue]
    ),
    SUMX(Fact_Sales, Fact_Sales[Actual_Revenue]),
    0
)
```

**Interpretation:**
- Shows your brand's share within each chain
- Compare to competitive benchmarks
- Identify chains where brand is under-represented

**Format:** Percentage (0.0%)  
**Usage:** Create heatmap: Rows = Brand, Columns = Chain, Values = Penetration %

### New SKU Ramp-up (Velocity Index)

```dax
Ramp_Up_Velocity =
VAR WeeksSinceIntro = DATEDIFF(
    MINX(Fact_Sales, Fact_Sales[DateKey]),
    MAXX(Fact_Sales, Fact_Sales[DateKey]),
    DAY
) / 7
VAR CurrentSalesWeekly = [Total Actual Revenue] / WeeksSinceIntro
VAR TargetVelocity = 50000  -- ₹ per week (benchmark)
RETURN
    DIVIDE(CurrentSalesWeekly, TargetVelocity, 0)
```

**Interpretation:**
- **>1.0x:** SKU ramping above target (accelerate supply)
- **0.7-1.0x:** On track (monitor)
- **<0.7x:** Below ramp target (investigate resistance, plan support)

**Format:** 0.00x (e.g., 1.25x)

---

## 5. Executive Dashboard Matrix

### Operational Scorecard (All Key Metrics at a Glance)

| Metric | Current | Target | Status | Trend |
|--------|---------|--------|--------|-------|
| **Revenue** | ₹341 Cr | ₹360 Cr | 🟡 -5.3% | ↗ +2.1% MoM |
| **Forecast Realization %** | 101% | 95-105% | 🟢 ON | ↗ Improving |
| **CM2 Amount (Baseline)** | ₹52.3 Cr | ₹58.0 Cr | 🟡 -9.8% | ↘ Declining |
| **Fill Rate %** | 94.2% | ≥95% | 🟡 -0.8% | ↘ Slight decline |
| **Lost Sales (₹)** | ₹8.4 Cr | <₹5 Cr | 🔴 HIGH | ↘ Worsening |
| **Trade Spend %** | 6.2% | 4-5% | 🟠 ELEVATED | → Stable |
| **Promo Lift %** | +18% | >15% | 🟢 GOOD | ↗ Strong |
| **Days of Cover** | 22 days | 14-30 days | 🟢 OPTIMAL | → Stable |
| **SKU Distribution %** | 83% | >80% | 🟢 GOOD | ↗ Improving |
| **Weighted Distribution** | 76% | >75% | 🟢 GOOD | → Stable |

---

## 6. Report Page: Supply Chain & Operations (Proposed New Page)

### Layout: Supply Chain Hub

**Row 1: KPI Scorecard (6 cards)**
- Fill Rate % (with status color)
- Lost Sales (₹)
- Trade Spend %
- Days of Cover (average)
- SKU Distribution %
- Weighted Distribution

**Row 2: Dual Visuals**
- **Left:** Fill Rate trend by Chain (line chart)
- **Right:** Days of Cover by Hub (gauge/radial chart)

**Row 3: Trade Spend Analysis**
- **Left:** Promo Lift % by Chain (bar chart, sorted)
- **Right:** Net Realized Price by Chain (column chart)

**Row 4: Inventory Health Matrix**
- Rows: Regional Hub (DC_MH_01, WH_GJ_01, etc.)
- Columns: SKU
- Values: Days of Cover (conditional color), Status flag

**Row 5: Category Penetration Heatmap**
- Rows: Brand
- Columns: Chain
- Values: Distribution % (color saturation)

---

## 7. DAX Measure Summary Table

| Measure | Table | Category | Format | Threshold |
|---------|-------|----------|--------|-----------|
| Fill Rate % | Operational | Supply Chain | 0.0% | Green ≥95% |
| Lost Sales ₹ | Operational | Supply Chain | ₹ Cr | Red >5 Cr |
| Trade Spend % | Operational | Promo/Trade | 0.0% | Yellow >6% |
| Promo Lift % | Operational | Promo/Trade | 0.0% | Green >15% |
| Net Realized Price | Operational | Pricing | ₹ 0.00 | Compare to list |
| Trade Spend ROI | Operational | Promo/Trade | 0.00x | Green >1.0x |
| Days of Cover | Operational | Inventory | # days | Green 14-30 |
| Stock-out Status | Operational | Inventory | Text | Red <7 days |
| SKU Distribution % | Operational | Penetration | 0.0% | Green >80% |
| Weighted Distribution | Operational | Penetration | 0.0% | Green >75% |
| Brand Penetration % | Operational | Penetration | 0.0% | Compare benchmark |
| Ramp-up Velocity | Operational | New SKU | 0.00x | Green >0.8x |

---

## 8. Implementation Checklist

- [ ] **Data Model:** Verify Fact_Sales includes all required columns
  - [ ] Delivered_Qty, Ordered_Qty (for Fill Rate)
  - [ ] Scheme_Adjustment, Promo_Cost (for Trade Spend)
  - [ ] Ensure consistent grain: [DateKey, ChainKey, SKU_Code, ZoneKey]

- [ ] **Fact_Inventory table (New)**
  - [ ] Create table with: [DateKey, Hub_ID, SKU_Code, Closing_Stock_Units, Opening_Stock]
  - [ ] Link to Dim_Geography[Hub_ID] (if available)

- [ ] **Add 12 new measures** to `_Measures` table
  - [ ] Fill Rate %, Lost Sales ₹, Stock-out Flag
  - [ ] Trade Spend %, Promo Lift %, Net Realized Price, ROI %
  - [ ] Days of Cover, Stock-out Risk Status
  - [ ] Distribution %, Weighted Distribution %, Brand Penetration %
  - [ ] Ramp-up Velocity

- [ ] **Test each measure** with sample data
  - [ ] Verify no #DIV/0! or NaN errors
  - [ ] Verify thresholds trigger correct status colors
  - [ ] Verify context filters (Chain, Hub, SKU) work correctly

- [ ] **Create Supply Chain operations page** (Page 6 recommended)
  - [ ] Add KPI scorecard (6 cards)
  - [ ] Add trend charts (Fill Rate, Days of Cover)
  - [ ] Add trade spend analysis visuals
  - [ ] Add inventory matrix
  - [ ] Add penetration heatmap

---

## 9. Data Quality Notes

**Critical:** Ensure Fact_Sales data includes:
- `Delivered_Qty` (actual shipped to store)
- `Ordered_Qty` (store demand; can exceed delivered if stock-out)
- `Scheme_Adjustment` (trade discount amount)
- `Promo_Cost` (promotional spend)

**Inventory:** Fact_Inventory should be updated weekly:
- Week-end snapshot of stock-at-hand by Hub × SKU
- Load fresh after each physical stock verification

**Benchmark:** Compare metrics monthly to:
- Industry averages (Modern Trade retail standards)
- Competitive performance (DMart, Reliance, etc.)
- Internal targets (brand-specific SLAs)

---

**Related Documents:**
- `03_DAX_MEASURE_LIBRARY.md` — Base financial measures
- `06_PARAMETERIZED_CM2_MODEL.md` — CM2 margin model
- `04_REPORT_LAYOUT_SPECS.md` — Report design specs
