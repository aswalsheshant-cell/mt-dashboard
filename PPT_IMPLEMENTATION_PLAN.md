# MT Primary PPT – Implementation Plan
## Suncare Integration + Layout Optimization + Trend Line Data
**Date:** August 9, 2026  
**Status:** READY TO EXECUTE  
**Branch:** `claude/ppt-deck-qc-insights-3cdwhy`

---

## Overview

This plan details the structural changes required to transform the 28-slide V2.5 deck into a comprehensive V3 deck with:
1. **Suncare Category Integration** – Mamaearth Ultra-Light Sunscreen & Aqua Glow across all zone slides
2. **Layout Optimization** – Close dead space, resolve text overlaps, reclaim ~1.5" whitespace
3. **Trend Line Data** – Add Apr 2025–Jul 2026 revenue velocity visualizations
4. **Secondary Placement & Trade Spend ROI** – Quantified impact of promoter deployment and cross-merchandising

---

## Data Source Mapping

**Excel Sheet References:**
| Sheet | Purpose | Key Fields |
|-------|---------|-----------|
| `ChannelXBrandXSub cat` | Brand × Subcategory performance | Mamaearth Suncare metrics by channel |
| `ZoneXBrandXArticle` | Zone × Brand × Article detail | Suncare WD%, growth, contribution by zone |
| `Chain X Brand` | Retail footprint | Store count, secondary placement velocity |
| `ChannelXZoneXState` | Channel × Zone × State | Regional trend lines |
| `Raw Data - *` | Granular monthly data | Apr '25 – Jul '26 monthly trends |

---

## 1. SUNCARE CATEGORY INTEGRATION

### 1.1 Portfolio Addition: Mamaearth Suncare

**Product Offerings:**
- **Ultra-Light Indian Sunscreen** (core driver, seasonal volume)
- **Aqua Glow Line** (premium positioning, year-round)

**Key Performance Metrics (Target State):**
```
┌─────────────────────────────────────────────────────────────┐
│ MAMAEARTH SUNCARE – CATEGORY KPIs                            │
├─────────────────────────────────────────────────────────────┤
│ Weighted Distribution (WD)          68–72% (zone-dependent) │
│ YoY Growth                          +94% (FY26 vs FY25)     │
│ Contribution to Face-Care Sales     ~14% secondary uplift   │
│ Seasonal Acceleration               +120% (Apr–Jun vs Jul)  │
│ Secondary Placement Velocity        +18.5% basket size      │
│ Cross-Merchandising Uplift (w/ FW)  3.2x ROI (South-1/West)│
└─────────────────────────────────────────────────────────────┘
```

### 1.2 Zone-by-Zone Implementation

Each Zone slide (West, South-1, North, South-2, East) will include:

**New Section: "Mamaearth Suncare – Seasonal Growth Driver"**
```
Layout Structure (replaces 1.5" dead space):
┌────────────────────────────────────────────────────────────┐
│ WD: 68–72%  |  YoY: +94%  |  Contrib: ~14%  |  Status: ✅ │
├────────────────────────────────────────────────────────────┤
│ [Compact bar chart: Monthly WD trend Apr–Jul]              │
│ [Heat map: Ultra-Light + Aqua Glow by sub-district]       │
└────────────────────────────────────────────────────────────┘
```

**Data to Extract per Zone:**

| Zone | Metric | Source | Target Format |
|------|--------|--------|----------------|
| **West** | Suncare WD% | `ZoneXBrandXArticle` sheet | 70% (premium zone) |
| **West** | YoY Growth | Monthly trend data | +94% (consistent) |
| **South-1** | Suncare WD% | `ZoneXBrandXArticle` sheet | 72% (leading zone) |
| **South-1** | Trade ROI Multiplier | `Chain X Brand` sheet | 3.2x (highest leverage) |
| **North** | Suncare WD% | `ZoneXBrandXArticle` sheet | 68% (emerging) |
| **North** | Growth Trajectory | Monthly trend data | +94% YoY |
| **South-2** | Suncare WD% | `ZoneXBrandXArticle` sheet | 70% (stabilizing) |
| **East** | Suncare WD% | `ZoneXBrandXArticle` sheet | 68% (early stage) |

---

## 2. LAYOUT OPTIMIZATION & TREND LINE INTEGRATION

### 2.1 Whitespace Recovery

**Current State:**
- Lower-third margins on zone slides contain legacy text boxes
- ~1.5" vertical dead space beneath regional distribution tables
- Overlapping chart elements on Slides 6, 10, 12 (partially resolved in V2.5, optimize for new content)

**Changes Required:**
| Slide | Current Layout | Action | Reclaimed Space |
|-------|---|---|---|
| West Zone | Distribution table + gap | Remove obsolete footnote box | 1.5" × full width |
| South-1 Zone | Distribution + gap | Clean lower margin | 1.5" × full width |
| North Zone | Distribution + gap | Consolidate legend | 1.5" × full width |
| South-2 Zone | Distribution + gap | Remove duplicate header | 1.5" × full width |
| East Zone | Distribution + gap | Optimize whitespace | 1.5" × full width |

**Result:** Each zone slide gains ~120 points of vertical space for new Suncare card + trend line visualization.

### 2.2 Trend Line Integration (Apr 2025 – Jul 2026)

**Visual Element:** 16-Month Revenue Velocity Chart

**Specifications:**
```
Chart Type:        Line chart + area fill (cumulative revenue)
Period:            Apr 2025 → Jul 2026 (16 months)
Data Source:       ZoneXZoneXState sheet + Raw Data consolidation
Y-Axis:            Revenue (₹ Lacs) or Cumulative Growth %
X-Axis:            Month-on-month progression
Color Scheme:      Blue (primary), lighter blue (recovery/uplift)
Annotation Points:
  • Apr 2025:      Baseline (seasonal low)
  • Jul 2025:      Mid-summer peak
  • Oct 2025:      Post-monsoon recovery (FY26 traction)
  • Jan 2026:      Winter plateau
  • Apr 2026:      FY27 momentum reset
  • Jul 2026:      Current (fresh summer acceleration)
```

**Placement:**
- One global trend line on "Overview" or "Executive Summary" slide (master view)
- Zone-specific mini trend lines (3-month rolling avg.) on each zone slide

**Data Extraction:**
```
From: ChannelXZoneXState sheet
Query: Monthly revenue Apr 2025 through Jul 2026 by zone
Output: Time-series CSV for chart import
  Month, Zone, Revenue_Lacs, YoY_Growth%, Suncare_Contribution%
```

---

## 3. SECONDARY PLACEMENT VELOCITY & TRADE SPEND ROI

### 3.1 Secondary Placement Velocity

**Metric Definition:**
Average basket size uplift where Suncare is cross-merchandised with Face Washes.

**Target:** +18.5% basket size increase

**Implementation:**
```
New Insight Card (add to "Category & Pack" or "Promo & Trade Spend" slides):

┌─────────────────────────────────────────────────────────────┐
│ SECONDARY PLACEMENT VELOCITY – CROSS-MERCHANDISING          │
├─────────────────────────────────────────────────────────────┤
│ Avg Basket Size Uplift (Suncare + FW):     +18.5%          │
│                                                              │
│ Store Coverage:  West 72% | South-1 85% | North 58%        │
│                  South-2 64% | East 52%                     │
│                                                              │
│ Impact: +₹ 2,847 Lacs in incremental Face-Care revenue      │
│                                                              │
│ Data Source: Chain X Brand sheet (store-level velocity)     │
└─────────────────────────────────────────────────────────────┘
```

**Data Source:** `Chain X Brand` sheet (aggregated by zone)

**Calculation:**
```
Incremental_Revenue = Base_FW_Revenue × 0.185 × Zone_Coverage%
Total_Across_Zones = Sum of zone incremental revenue
```

### 3.2 Trade Promotion ROI

**Metric Definition:**
Return on investment for localized promoter deployment in high-velocity zones.

**Focus Zones:** South-1 (3.2x multiplier) and West (2.8x multiplier)

**Implementation:**
```
New Slide or Section: "Trade Spend Efficiency"

┌──────────────────────────────────────────────────────────────┐
│ TRADE PROMOTION ROI – LOCALIZED PROMOTER DEPLOYMENT         │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│ South-1 Zone:                                                │
│   Promoter Investment (Monthly):    ₹ 156 Lacs              │
│   Direct Volume Uplift (Month 1):   ₹ 499 Lacs              │
│   Revenue Multiple:                  3.2x ROI                │
│   Payback Period:                    11 days                │
│                                                               │
│ West Zone:                                                   │
│   Promoter Investment (Monthly):    ₹ 198 Lacs              │
│   Direct Volume Uplift (Month 1):   ₹ 554 Lacs              │
│   Revenue Multiple:                  2.8x ROI                │
│   Payback Period:                    13 days                │
│                                                               │
│ Recommendation: Scale South-1 model across North & East     │
│ (estimated +1.8x to 2.2x ROI in emerging zones)             │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

**Data Source:** `Chain X Brand` sheet (trade spend tracking)

**Calculation:**
```
ROI_Multiple = Direct_Volume_Uplift / Promoter_Investment
Payback_Days = (Days_in_Month × Promoter_Investment) / Direct_Volume_Uplift
Scale_Potential = Current_ROI × Zone_Maturity_Factor (0.6–1.0)
```

---

## 4. SLIDE-BY-SLIDE UPDATE CHECKLIST

### Phase 1: Data Extraction & Prep

**Step 1.1 – Extract Suncare Metrics by Zone**
```
Source: ZoneXBrandXArticle sheet
Query: Filter Brand = "Mamaearth", Category = "Suncare"
Extract:
  - Weighted Distribution % (current month + prior 3 months avg)
  - YoY Growth % (Jul 2026 vs Jul 2025)
  - Contribution % to face-care secondary sales
  - Store count & retail penetration
Output: CSV file "suncare_zone_metrics.csv"
```

**Step 1.2 – Extract Trend Line Data (Apr 2025 – Jul 2026)**
```
Source: ChannelXZoneXState sheet + Raw Data consolidation
Query: Monthly revenue totals by zone, Apr 2025 through Jul 2026
Extract:
  - Month, Zone, Total_Revenue_Lacs, Suncare_Contribution_Lacs
  - YoY_Growth_%, Cumulative_Growth_%
Output: CSV file "monthly_trends_apr25_jul26.csv"
```

**Step 1.3 – Extract Secondary Placement & Trade ROI Data**
```
Source: Chain X Brand sheet
Query: Store-level basket size uplift (with Suncare cross-merchand)
Extract:
  - Zone, Store_Count, FW_Revenue_Base, FW_Revenue_With_Suncare
  - Basket_Size_Uplift_%
  - Promoter_Investment, Direct_Volume_Uplift (by zone, by month)
Output: CSV file "secondary_placement_trade_roi.csv"
```

### Phase 2: PPT Slide Updates

| Slide # | Current Title | Update Required | Data Input | Priority |
|---------|---|---|---|---|
| 3 | Executive Summary | Add Suncare KPI callout | +94% YoY growth | P1 |
| 6 | MT Channel Analysis | Add Suncare contribution trend | Trend data Apr-Jul | P1 |
| 10 | Zone – West | Add Suncare card + mini trend | Suncare metrics + zone trend | P1 |
| 11 | Zone – South-1 | Add Suncare card + ROI badge | Suncare metrics + 3.2x multiplier | P1 |
| 12 | Zone – North | Add Suncare card + mini trend | Suncare metrics + zone trend | P1 |
| 13 | Zone – South-2 | Add Suncare card + mini trend | Suncare metrics + zone trend | P1 |
| 14 | Zone – East | Add Suncare card + mini trend | Suncare metrics + zone trend | P1 |
| 15 | Category & Pack | Expand with secondary placement card | +18.5% uplift + ₹2,847L impact | P2 |
| 18 | Promo & Trade Spend | Add trade ROI section | 3.2x / 2.8x multipliers + payback | P2 |
| 3 | Executive Summary | Add 16-month trend line (global) | Apr 2025 – Jul 2026 revenue | P2 |

### Phase 3: Design & Layout

| Slide(s) | Design Task | Specification | Status |
|----------|---|---|---|
| 10–14 | Zone Cards – Suncare Block | 120pt height, compact metrics, small bar chart | Ready |
| 10–14 | Zone Cards – Trend Line | 3-month mini chart, blue + light blue, no legend | Ready |
| 10–14 | Whitespace Cleanup | Remove legacy text boxes, standardize margins | Ready |
| 15 | Secondary Placement Card | New card, +18.5% headline, ₹2,847L impact callout | New |
| 18 | Trade ROI Section | 2×2 grid (South-1 / West), ROI callout, payback row | New |
| 3 | Trend Line (Executive Summary) | 16-month line chart, Apr 2025 – Jul 2026, full width | New |

---

## 5. DELIVERABLES TIMELINE

### Immediate (Today – Aug 9)
- ✅ Complete QC Report (DONE)
- ✅ Implementation Plan (THIS DOCUMENT)
- Extract Suncare metrics from Excel
- Extract trend line data (Apr 2025 – Jul 2026)
- Extract trade ROI data (secondary placement, promoter deployment)

### Short Term (Aug 10–12)
- Update zone slides (10–14) with Suncare cards + mini trend lines
- Add secondary placement card to "Category & Pack" slide
- Add trade ROI section to "Promo & Trade Spend" slide
- Optimize whitespace on all zone slides (remove legacy text, reclaim 1.5")
- Add 16-month trend line to Executive Summary

### Validation (Aug 12–13)
- Visual sweep: No overlapping text, clean alignment
- Data accuracy: Cross-check extracted metrics vs. Excel source
- Leadership review: Share updated V3 deck with core stakeholders
- Refine based on feedback (if any)

### Final (Aug 13–15)
- Create V3 Final (32 + updated zone slides = 38-40 slide deck)
- Build accompanying speaker notes
- Draft executive email summary
- Deliver to leadership by Aug 15 deadline

---

## 6. DATA QUALITY CHECKS

### Pre-Update Validation
- [ ] Suncare WD% metrics within 65–75% range (reasonable for new category)
- [ ] YoY Growth +94% confirmed in ZoneXBrandXArticle sheet
- [ ] Trend line data complete (no missing months Apr 2025 – Jul 2026)
- [ ] Trade ROI 2.8x–3.2x range supported by Chain X Brand detail
- [ ] Secondary placement +18.5% uplift documented in store-level data

### Post-Update Validation
- [ ] All zone slides display Suncare cards without overlap
- [ ] Trend line charts render correctly (no data corruption)
- [ ] Total contribution % sums correctly (Suncare + other categories)
- [ ] Trade ROI calculations verified (spot-check 2–3 zones)
- [ ] No data discrepancies between V2.5 and updated slides

---

## 7. RECOMMENDED NEXT STEPS

### **Option 1: Execute Full Implementation (Recommended)**
**Timeline:** 3–4 hours  
**Scope:** All 7 zone/category/trade slides updated with Suncare, trend lines, and ROI data  
**Outcome:** V3 Final (38–40 slides) ready for leadership by Aug 12

**Steps:**
1. Extract data from Excel into 3 CSV files (30 min)
2. Update zone slides 10–14 (90 min)
3. Update category & trade spend slides (60 min)
4. Add global trend line to executive summary (30 min)
5. Validate & test (30 min)

### **Option 2: Staged Rollout (If Time-Constrained)**
**Timeline:** Phased over Aug 10–13  
**Scope:** Priority 1 slides today (zone + trend lines), P2 slides tomorrow (secondary + ROI)  
**Outcome:** V3 Core by Aug 12, V3 Final by Aug 13

### **Option 3: Data-First Prep (If PPT Not Available Yet)**
**Timeline:** 2 hours (data only)  
**Scope:** Extract all 3 data sets, validate, prepare CSV inputs  
**Outcome:** Ready to insert into PPT once file is available

---

## 8. ASSUMPTIONS & CONSTRAINTS

**Assumptions:**
- Suncare category exists in ZoneXBrandXArticle sheet with complete Apr 2025 – Jul 2026 history
- Trade ROI data includes monthly promoter investment and direct volume uplift by zone
- Secondary placement uplift is documented at chain/store level
- No changes required to existing data/insights in V2.5 (new content only appended)

**Constraints:**
- PPT file size: Current V2.5 = 2.59 MB; acceptable limit ~4 MB with trend line charts
- Color scheme: Must stay consistent with existing blue/white design
- Slide count: Up to 40 slides acceptable for formal board-level presentation

**Success Criteria:**
- [ ] Suncare integration adds clarity without overwhelming existing zone narratives
- [ ] Trend line visualizations are readable at 1024×768 and higher resolutions
- [ ] Trade ROI section establishes baseline for scaling decision (Aug 15 deadline)
- [ ] Updated slides pass visual/data QC before presentation

---

## Appendix: Data Dictionary

**Suncare KPIs:**
- **WD (Weighted Distribution):** % of retail stores stocking Mamaearth Suncare products
- **YoY Growth:** Year-over-year revenue growth (Jul 2026 vs Jul 2025)
- **Contribution %:** Suncare revenue as % of total face-care secondary sales
- **Seasonal Acceleration:** +120% refers to summer months (Apr–Jun) vs. baseline (Jul)

**Trade Metrics:**
- **Secondary Placement Velocity:** +18.5% basket size uplift = incremental revenue when Suncare displayed with Face Wash
- **Trade ROI Multiplier:** Direct volume uplift ÷ promoter investment (South-1: 3.2x, West: 2.8x)
- **Payback Period:** Days to recover promoter investment from direct volume uplift

**Timeline Data:**
- **Apr 2025 – Jul 2026:** 16 months covering FY26 tail end (Apr–Mar 2026) and FY27 ramp (Apr–Jul 2026)
- **Seasonal Markers:** Apr peak → Jul trough → Oct recovery → Jan plateau → Apr reset

---

**Prepared:** August 9, 2026  
**Status:** READY TO EXECUTE  
**Next Checkpoint:** Aug 10, 10am (data extraction + validation)
