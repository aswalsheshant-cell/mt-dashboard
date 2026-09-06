# Distributor-Chain-Brand-Article TOT% Analysis (April–July 2026)

**Last Updated:** 2026-08-30  
**Data Period:** Apr 2026 – Jul 2026 (4 months)  
**Total Records:** 28,537 transactions  
**Total NSV:** ₹42.81 Cr (₹4,281.34 Lakh)

## Overview

This folder contains comprehensive **Trade-Off-Take (TOT%) Analysis** showing how distributor sales are allocated across chains, brands, and articles over a 4-month period. TOT% represents the percentage of one entity's sales attributed to the next level in the hierarchy.

## Files

### 1. `00_SUMMARY_Statistics.csv`
Dataset summary statistics including:
- Total records (28,537)
- Date range (Apr-Jul 2026)
- Entity counts (34 distributors, 76 chains, 23 brands, 798 EANs)
- Aggregate NSV (₹42.81 Cr)

### 2. `01_FULL_HIERARCHY_Apr_Jul_2026.csv` ⭐ PRIMARY FOR POWER BI
Complete transaction-level grain with all hierarchy levels and calculated TOT% at each step:

**Columns:**
- `Source_Month`: YYYY-MM format (2026-04 to 2026-07)
- `Distributor`: Distributor entity name
- `Dist_Monthly_Total`: Total NSV for distributor in that month
- `Chain`: Chain/customer entity
- `Chain_Monthly_Total`: Total NSV for chain in that month
- `Chain_TOT_Pct`: % of distributor sales going to this chain (0–100)
- `Brand`: Brand name
- `Brand_Monthly_Total`: Total NSV for brand in that month
- `Brand_TOT_Pct`: % of chain sales for this brand (0–100)
- `EAN`: Article EAN code (if available)
- `Article`: Article name
- `NSV_Value`: Sales value in INR
- `NSV_Lakh`: Sales value in Lakh (NSV_Value ÷ 100,000)
- `Quantity`: Unit quantity sold

**Use Case:** Import into Power BI watch folder for auto-refresh; wire relationships to Dim_Distributor, Dim_Chain, Dim_Brand.

### 3. `02_DISTRIBUTOR_CHAIN_TOT_Apr_Jul_2026.csv`
Aggregated **Distributor → Chain** level with monthly TOT%:

**Columns:**
- `Month`: Source month (2026-04, 2026-05, 2026-06, 2026-07)
- `Distributor`: Distributor name
- `Chain`: Chain name
- `Chain_NSV_Lakh`: Total NSV for this distributor-chain pair (in Lakh)
- `Dist_Total_Lakh`: Total monthly NSV for distributor (in Lakh)
- `Chain_TOT_Percent`: Percentage of distributor's sales going to this chain (0–100%)

**Records:** 235 Distributor-Chain combinations across 4 months  
**Key Insight:** Shows distributor concentration (single-chain vs multi-chain allocation patterns)

### 4. `03_CHAIN_BRAND_TOT_Apr_Jul_2026.csv`
Aggregated **Chain → Brand** level with monthly TOT%:

**Columns:**
- `Month`: Source month
- `Chain`: Chain name
- `Brand`: Brand name
- `Brand_NSV_Lakh`: Total NSV for this chain-brand pair (in Lakh)
- `Chain_Total_Lakh`: Total monthly NSV for chain (in Lakh)
- `Brand_TOT_Percent`: Percentage of chain's sales from this brand (0–100%)

**Records:** 379 Chain-Brand combinations across 4 months  
**Key Insight:** Shows brand concentration risk per chain; identifies top-performing brands per channel

### 5. `04_DISTRIBUTOR_CHAIN_MoM_TOT_Pivot.csv`
**Month-over-Month (MoM) Pivot Table** for Distributor-Chain TOT% trends:

**Structure:**
- Rows: Distributor-Chain pairs (140 unique)
- Columns: Months (2026-04, 2026-05, 2026-06, 2026-07)
- Values: Chain_TOT_Percent for each month

**Use Case:** Track distributor channel allocation stability across 4 months; identify seasonal patterns

**Example Interpretation:**
```
Distributor            Chain         2026-04  2026-05  2026-06  2026-07
Just Mark              Dmart         —        —        100.00   100.00
Kiran Trading          Dmart         —        —        —        100.00
Sri Vijaya Durga       Dmart         48.32    43.74    60.44    46.94
Sri Vijaya Durga       Reliance      29.97    30.72    28.86    35.59
AZ Enterprises         Apollo        35.47    51.38    40.79    28.89
```

→ Just Mark: 100% stable to DMart (concentration risk)
→ SVDA: Balanced (43–60% DMart, 28–36% Reliance) = lower risk
→ AZ Enterprises: Apollo allocation declining (35% → 29%) = channel shift

## Key Metrics & Patterns

### Distributor Concentration
- **Single-chain (100% allocation):** Just Mark, Kiran Trading, Mark Enterprises, United Marketing
  - Risk: High (one channel failure = total loss)
  - Stability: High (no allocation variability)

- **Multi-chain (diversified):** SVDA (7 chains), DL Sales (9 chains), AZ Enterprises (7 chains)
  - Risk: Lower (distributed across channels)
  - Stability: Moderate (±10-15% MoM variance)

### NSV Trends (Apr–Jul 2026)
| Distributor | Total 4M (₹Lakh) | Avg Monthly | Trend |
|---|---|---|---|
| Kiran Trading | 1,205.26 | 301.31 | Declining (552→251) |
| SVDA | 457.27 | 114.32 | Stable |
| GV Enterprises | 455.08 | 113.77 | Volatile |
| Just Mark | 443.08 | 110.77 | Growth (0→255) |
| AZ Enterprises | 256.50 | 64.13 | Stable |

### Brand Concentration by Chain
- **DMart:** 23 brands tracked; no single brand >50% share
- **Reliance Retail:** 18 brands; top brand ~38%
- **Apollo:** 21 brands; top brand ~42%
- **Lulu:** Significant SKU diversity

## How to Use

### 📊 For Power BI Integration
1. **Import Primary File:**
   ```
   01_FULL_HIERARCHY_Apr_Jul_2026.csv → PowerBI/RawDataFolders/SecondarySales_Monthly/
   (Rename as: secondary_sales_tot_analysis_Apr_Jul_2026.csv)
   ```

2. **Wire Relationships in Power BI Model:**
   - `Dim_Distributor[Distributor]` ← `Fact_SecondarySales[Distributor]`
   - `Dim_Chain[Chain]` ← `Fact_SecondarySales[Chain]`
   - `Dim_Brand[Brand]` ← `Fact_SecondarySales[Brand]`

3. **Create Slicers & Measures:**
   - Slicer: Source_Month (filter by Apr, May, Jun, Jul)
   - Measure: SUM([NSV_Lakh]) by Distributor, Chain, Brand
   - Measure: TOT% cards showing Chain_TOT_Pct, Brand_TOT_Pct

4. **Power Query Formula (fnCombineFolder):**
   ```pq
   let
       Source = Folder.Files("path\to\SecondarySales_Monthly"),
       Filter = Table.SelectRows(Source, each Text.EndsWith([Name], ".csv")),
       Combine = Table.Combine(Filter[Content]),
       Parsed = Csv.Document(Combine, [Delimiter=",", Encoding=65001])
   in
       Parsed
   ```

### 📈 For Business Analysis
1. **Distributor Performance Scorecard:**
   - Use `02_DISTRIBUTOR_CHAIN_TOT_Apr_Jul_2026.csv`
   - Track NSV growth and chain reach month-by-month

2. **Channel Health Dashboard:**
   - Use `03_CHAIN_BRAND_TOT_Apr_Jul_2026.csv`
   - Identify underperforming brands per chain
   - Monitor brand concentration risk

3. **MoM Trend Analysis:**
   - Use `04_DISTRIBUTOR_CHAIN_MoM_TOT_Pivot.csv`
   - Spot allocation shifts (distributors changing channel strategy)
   - Forecast next month based on observed patterns

### 💡 For Forecasting
- Apply 4-month average TOT% to next month's top-line forecast
- Allocate distributor targets by chain using historical TOT%
- Example: If Distributor X averages 60% to Chain A over 4 months, allocate 60% of next month's target to Chain A

## Data Quality Notes

✅ **Strengths:**
- 28,537 records covering 4 complete months
- Consistent distributor-chain-brand grain
- 798 unique EAN-level SKUs tracked
- No missing critical fields for top entities

⚠️ **Limitations:**
- Some distributors marked "Unmapped" in Chain field (Apr-May-Jun data from secondary repository; Jul billing detail has full chain mapping)
- EAN codes missing for some items (~5% of records)
- North distributor registers not yet integrated (pending Q1 FY27 completion)

## Reconciliation Notes

**Apr-Jun 2026:** Data from Secondary Sales Master Repository (self-reported by distributors)  
**Jul 2026:** Data from Distributor-Chain-Brand-Article Billing Detail (invoice-level, higher confidence)

Reconciliation gap expected between secondary sales and billing records; TOT% ratios remain consistent where data overlaps (Mar-Jun chain allocations).

## Next Steps

- [ ] Import to Power BI watch folder for automated refresh
- [ ] Create distributor KPI dashboard (NSV, chains served, concentration score)
- [ ] Reconcile Apr-Jun secondary sales with Jul billing grain
- [ ] Forecast Aug 2026+ using 4-month TOT% patterns
- [ ] Archive analysis with metadata for audit trail

---

**Contact:** MT Data Team | **Questions?** Refer to CLAUDE.md for data pipeline documentation
