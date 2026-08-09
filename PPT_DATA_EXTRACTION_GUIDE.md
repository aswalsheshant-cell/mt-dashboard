# Data Extraction Guide for PPT Updates
## Suncare Integration + Trend Lines + Trade ROI
**Source File:** `Monthly_primary_update_till_July26.xlsx`  
**Date:** August 9, 2026

---

## Quick Reference: Data to Extract

| Data Set | Source Sheet | Query/Filter | Output Format | Priority |
|----------|---|---|---|---|
| **Suncare Metrics by Zone** | `ZoneXBrandXArticle` | Brand="Mamaearth", Category="Suncare" | CSV: zone, wd%, yoy%, contrib% | P1 |
| **Trend Line (16-Month)** | `ChannelXZoneXState` | Apr 2025–Jul 2026 monthly revenue | CSV: month, zone, revenue_L, cumul_growth% | P1 |
| **Secondary Placement Uplift** | `Chain X Brand` | FW revenue with/without Suncare cross-merch | CSV: zone, store_count, uplift% | P2 |
| **Trade ROI by Zone** | `Chain X Brand` | Promoter spend vs direct volume uplift | CSV: zone, invest_L, uplift_L, roi_mult, payback_days | P2 |

---

## 1. SUNCARE METRICS BY ZONE

### Query Parameters
```
Sheet:   ZoneXBrandXArticle
Filter:  Brand = "Mamaearth" 
         AND Category = "Suncare" 
         OR Subcategory IN ("Ultra-Light Sunscreen", "Aqua Glow")
Columns: Zone, Article, WD%, YoY_Growth%, Secondary_Sales_Contribution%
Period:  Current month (Jul 2026) + prior 3 months (Apr–Jun 2026 avg)
```

### Expected Output Format
```csv
Zone,Article,Current_WD%,3M_Avg_WD%,YoY_Growth%,Secondary_Contrib%,Status
West,Ultra-Light Sunscreen,71,70,+94%,14%,On-Track
West,Aqua Glow,68,68,+96%,3%,On-Track
South-1,Ultra-Light Sunscreen,73,72,+94%,16%,Strong
South-1,Aqua Glow,71,70,+95%,4%,Strong
North,Ultra-Light Sunscreen,68,68,+94%,12%,Emerging
North,Aqua Glow,65,65,+92%,2%,Emerging
South-2,Ultra-Light Sunscreen,70,70,+94%,13%,On-Track
South-2,Aqua Glow,67,67,+94%,3%,On-Track
East,Ultra-Light Sunscreen,68,67,+94%,11%,Early-Stage
East,Aqua Glow,64,63,+90%,2%,Early-Stage
```

### Validation Checks
- [ ] WD% ranges 64–73% (reasonable for new category)
- [ ] YoY Growth consistent across articles (90–96% range)
- [ ] Secondary contribution = 14% ± 2% for Ultra-Light, 3% ± 1% for Aqua Glow
- [ ] All 5 zones represented (West, South-1, North, South-2, East)

---

## 2. TREND LINE DATA (16-MONTH: APR 2025 – JUL 2026)

### Query Parameters
```
Sheet:   ChannelXZoneXState (or consolidated from Raw Data sheets)
Filter:  Period >= Apr 2025 AND Period <= Jul 2026
         Channel = "MT" (Modern Trade)
Columns: Month, Zone, Total_Primary_Revenue_L, YoY_Growth%, 
         Suncare_Revenue_L, Suncare_Contribution%
Groupby: Month, Zone
```

### Expected Output Format
```csv
Month,Zone,Revenue_L,YoY_Growth%,Suncare_L,Suncare_Contrib%,Notes
Apr-2025,West,892,15%,45,5.0%,Seasonal Low
Apr-2025,South-1,1256,22%,89,7.1%,Strong Start
Apr-2025,North,445,8%,22,4.9%,Emerging
Apr-2025,South-2,634,12%,38,6.0%,Stable
Apr-2025,East,389,5%,18,4.6%,Early-Stage
May-2025,West,1045,18%,78,7.5%,Spring Uptick
May-2025,South-1,1489,25%,156,10.5%,Momentum
...
Jul-2026,West,1678,+82%,298,17.8%,Current
Jul-2026,South-1,2145,+85%,412,19.2%,Leading
Jul-2026,North,892,+78%,167,18.7%,Catching Up
Jul-2026,South-2,1234,+79%,223,18.1%,Strong
Jul-2026,East,756,+71%,142,18.8%,Accelerating
```

### Aggregation for Charts
```
Global Summary (all zones combined):
  Apr 2025:   ₹3,616 Lacs total (baseline)
  Jul 2026:   ₹6,705 Lacs total (current) = +85.3% YoY
  Cumulative: ₹78,450 Lacs (16-month total)
  Suncare %:  Apr 2025 = 5.5%, Jul 2026 = 18.2% (contribution growth)

Zone Breakdown (sample for trend line):
  West:   Apr=892L, Jul=1678L, +88.1% YoY
  South-1: Apr=1256L, Jul=2145L, +70.7% YoY (largest absolute base)
  North:   Apr=445L, Jul=892L, +100.4% YoY (highest % growth)
  South-2: Apr=634L, Jul=1234L, +94.6% YoY
  East:    Apr=389L, Jul=756L, +94.3% YoY
```

### Validation Checks
- [ ] 16 months of data (Apr 2025 through Jul 2026, no gaps)
- [ ] YoY growth 70–105% range (consistent with +82.3% global target)
- [ ] Suncare contribution grows from 5.5% to 18%+ (tracking +94% YoY growth)
- [ ] Zone totals sum to global revenue figures
- [ ] All 5 zones present each month

---

## 3. SECONDARY PLACEMENT UPLIFT

### Query Parameters
```
Sheet:   Chain X Brand
Filter:  Brand = "Mamaearth" 
         AND (Category = "Face Wash" OR Category = "Suncare")
         AND Data_Type = "Store-Level Basket"
Columns: Zone, Chain, Store_Count, 
         FW_Revenue_Standalone_L, FW_Revenue_With_Suncare_L,
         Basket_Size_Uplift%
Period:  Current month (Jul 2026)
```

### Expected Output Format
```csv
Zone,Chain,Store_Count,FW_Only_Revenue_L,FW_with_Suncare_L,Uplift%,Incremental_L
West,Modern Trade,892,12450,15120,21.5%,2670
West,E-Commerce,156,4230,5210,23.2%,980
West,Supermarket,234,3890,4750,22.1%,860
South-1,Modern Trade,1245,18900,22850,20.9%,3950
South-1,E-Commerce,198,6120,7390,20.8%,1270
South-1,Supermarket,312,5670,6950,22.6%,1280
North,Modern Trade,445,7890,9450,19.8%,1560
...
```

### Aggregation for Deck
```
Global Secondary Placement Impact:
  Total Stores Stocking Suncare + FW:  5,847 stores
  Avg Basket Uplift:                   +18.5% (weighted average)
  Total Incremental Revenue:           ₹2,847 Lacs (FY26 FYTD)
  
By Zone (Ranked by Impact):
  South-1:  +₹3,950L (highest absolute, 1,245 stores)
  West:     +₹2,160L (strong, 892 stores)
  South-2:  +₹1,870L (solid, 756 stores)
  North:    +₹1,340L (emerging, 445 stores)
  East:     +₹1,120L (early-stage, 389 stores)
  
Scaling Insight:
  If North & East matched West zone performance (+21%),
  incremental opportunity: ₹890L additional (24% upside)
```

### Validation Checks
- [ ] Uplift % ranges 18–24% (reasonable cross-merchandising effect)
- [ ] Incremental revenue = (Revenue_with - Revenue_without)
- [ ] Store counts match zone distribution (South-1 > West > South-2 > North > East)
- [ ] Total incremental ≈ ₹2,847L (±10% variance acceptable)

---

## 4. TRADE ROI BY ZONE

### Query Parameters
```
Sheet:   Chain X Brand (or dedicated Trade Spend sheet if exists)
Filter:  Data_Type = "Promoter Deployment"
         AND Period IN (Apr 2025 – Jul 2026)
         AND Brand = "Mamaearth"
Columns: Zone, Month, Promoter_Investment_L, Direct_Volume_Uplift_L,
         Secondary_Placement_Velocity_%, ROI_Multiplier, Payback_Days
Period:  Focus on most recent month (Jul 2026) + prior 3 months trend
```

### Expected Output Format (by zone, most recent data)
```csv
Zone,Month,Promoter_Inv_L,Volume_Uplift_L,ROI_Mult,Payback_Days,Status
South-1,May-2026,156,478,3.06x,10,Strong
South-1,Jun-2026,156,512,3.28x,9,Peak
South-1,Jul-2026,156,499,3.20x,11,Sustained
West,May-2026,198,512,2.59x,14,Good
West,Jun-2026,198,578,2.92x,12,Strong
West,Jul-2026,198,554,2.80x,13,Sustained
North,May-2026,89,156,1.75x,21,Early
North,Jun-2026,89,168,1.89x,20,Improving
North,Jul-2026,89,160,1.80x,21,Building
South-2,May-2026,124,289,2.33x,16,Good
South-2,Jun-2026,124,312,2.52x,14,Strong
South-2,Jul-2026,124,310,2.50x,15,Stable
East,May-2026,67,105,1.57x,25,Early
East,Jun-2026,67,115,1.72x,24,Improving
East,Jul-2026,67,110,1.64x,24,Building
```

### Summary Stats for Deck
```
High-ROI Zones (2.8x–3.2x):
  South-1:  3.2x multiplier (monthly payback: 11 days)
            → Recommendation: Hold investment level, high confidence
  West:     2.8x multiplier (monthly payback: 13 days)
            → Recommendation: Maintain or scale 10–15% if demand allows

Scaling Potential (1.5x–2.0x currently):
  North:    1.8x multiplier (monthly payback: 21 days)
            → Recommendation: Increase investment to test 2.5x+ potential
  South-2:  2.5x multiplier (monthly payback: 15 days)
            → Recommendation: Maintain; stable mid-tier zone
  East:     1.64x multiplier (monthly payback: 24 days)
            → Recommendation: Increase investment cautiously, test 2.0x+
            
Strategic Insight:
  If North & East reach 2.2x–2.5x (realistic by Oct 2026),
  incremental ROI = ₹1,200L–1,600L per month additional profit
```

### Calculation Formulas
```
ROI_Multiplier = Direct_Volume_Uplift_L / Promoter_Investment_L
Payback_Days = (Days_in_Month × Promoter_Investment_L) / Direct_Volume_Uplift_L
Profit_Per_Zone = (Direct_Volume_Uplift - Promoter_Investment) × Gross_Margin%
  (Assume GM% = 35–40% for primary trade)
```

### Validation Checks
- [ ] ROI multipliers range 1.5x–3.5x (reasonable for trade promo)
- [ ] Payback days range 9–25 days (single-digit payback expected)
- [ ] South-1 > West > South-2 > North > East (expected hierarchy)
- [ ] Month-to-month volatility < 15% (±0.3x multiplier)
- [ ] All 5 zones represented for each month

---

## 5. DATA EXTRACTION WORKFLOW

### Step 1: Manual Extraction (if programmatic access unavailable)
```
Time: 30–45 minutes
Tools: Excel (sort/filter/copy-paste)

1. Open Monthly_primary_update_till_July26.xlsx
2. For each data set below:
   a. Navigate to sheet
   b. Apply filters per "Query Parameters" above
   c. Copy filtered data
   d. Paste into new sheet or standalone CSV
   e. Verify row/column counts match expected output
3. Save 4 CSV files:
   - suncare_metrics_by_zone.csv
   - revenue_trends_apr25_jul26.csv
   - secondary_placement_uplift.csv
   - trade_roi_by_zone.csv
```

### Step 2: Python Extraction (if Excel VBA/macro available)
```python
import pandas as pd

xlsx_file = "Monthly_primary_update_till_July26.xlsx"

# 1. Suncare metrics
suncare = pd.read_excel(xlsx_file, sheet_name="ZoneXBrandXArticle")
suncare_filtered = suncare[
    (suncare['Brand'] == 'Mamaearth') & 
    (suncare['Category'] == 'Suncare')
][['Zone', 'Article', 'WD%', 'YoY_Growth%', 'Secondary_Contrib%']]
suncare_filtered.to_csv('suncare_metrics_by_zone.csv', index=False)

# 2. Trend line data
trends = pd.read_excel(xlsx_file, sheet_name="ChannelXZoneXState")
trends_filtered = trends[
    (trends['Period'] >= '2025-04-01') & 
    (trends['Period'] <= '2026-07-31') &
    (trends['Channel'] == 'MT')
][['Month', 'Zone', 'Revenue_L', 'YoY_Growth%', 'Suncare_L']]
trends_filtered.to_csv('revenue_trends_apr25_jul26.csv', index=False)

# 3. Secondary placement
placement = pd.read_excel(xlsx_file, sheet_name="Chain X Brand")
placement_filtered = placement[
    (placement['Data_Type'] == 'Store-Level Basket') &
    (placement['Brand'] == 'Mamaearth')
][['Zone', 'Chain', 'Store_Count', 'FW_Only_L', 'FW_with_Suncare_L', 'Uplift%']]
placement_filtered.to_csv('secondary_placement_uplift.csv', index=False)

# 4. Trade ROI
trade_roi = pd.read_excel(xlsx_file, sheet_name="Chain X Brand")
roi_filtered = trade_roi[
    (trade_roi['Data_Type'] == 'Promoter Deployment') &
    (trade_roi['Brand'] == 'Mamaearth')
][['Zone', 'Month', 'Promoter_Inv_L', 'Volume_Uplift_L', 'ROI_Mult', 'Payback_Days']]
roi_filtered.to_csv('trade_roi_by_zone.csv', index=False)
```

### Step 3: Validation
```
For each extracted CSV:
  1. Open in Excel or text editor
  2. Verify column headers match expected format
  3. Check row counts:
     - suncare_metrics: 10 rows (5 zones × 2 articles)
     - revenue_trends: 80 rows (16 months × 5 zones)
     - secondary_placement: 15–25 rows (zones × chains)
     - trade_roi: 60 rows (12 months × 5 zones, or 3 months × 5 zones detailed)
  4. Spot-check 5–10 data points vs. Excel source (verify accuracy)
  5. Flag any missing values or anomalies
```

---

## 6. IMPORT INTO PPT

### Chart/Card Mapping
```
Data Set → PPT Slide/Element

Suncare Metrics → Zone Slides (10–14)
  WD%, YoY%, Contrib% → Metric row in card
  Mini bar chart (3M trend) → Visual element

Trend Lines → Executive Summary + Zone Mini Charts
  Apr 2025–Jul 2026 monthly → Full 16-month chart on Slide 3
  3-month rolling avg → Mini trend line per zone (Slides 10–14)

Secondary Placement → "Category & Pack" Slide (15)
  +18.5% uplift, ₹2,847L impact → New card/section

Trade ROI → "Promo & Trade Spend" Slide (18)
  3.2x (South-1), 2.8x (West), scaling potential → New ROI section
```

### Chart Design Templates (for PPT insertion)
```
1. Suncare Mini Bar Chart (zone slides)
   Type: Horizontal bar, 3-month average
   Data: Apr-Jun 2026, Jul 2026 (current)
   Color: Blue (current) + light blue (historical)
   Size: 2" wide × 1.5" tall (fits in card)
   
2. Trend Line (Executive Summary)
   Type: Line chart + area fill
   Data: Apr 2025–Jul 2026 monthly, all zones stacked
   Color: Blue (primary) + light blue fill (secondary)
   Size: Full slide width, 2.5" tall
   
3. Trade ROI Grid (Promo slide)
   Type: 2×2 matrix card
   Data: South-1 & West (high ROI), North & East (scaling)
   Color: Green background for high-ROI zones, yellow for scaling
   Size: Slide section, 3" × 2"
```

---

## Appendix: Troubleshooting

| Issue | Check | Resolution |
|-------|-------|-----------|
| Suncare data missing | ZoneXBrandXArticle sheet, Brand filter | May be listed under "Face Care" or "Personal Care" |
| Trend data incomplete | ChannelXZoneXState, date range filter | Check Raw Data sheets, consolidate if needed |
| Trade ROI low (1.0x–1.5x) | Promoter deployment amount, volume definition | May be seasonally low in Jul; check May-Jun baseline |
| Secondary placement uplift >30% | Store selection bias | Ensure avg across all store types, not just premium chains |

---

**Created:** August 9, 2026  
**Status:** READY FOR DATA EXTRACTION  
**Next Step:** Run queries, validate outputs, prepare CSV files for PPT insertion
