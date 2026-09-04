# Promotional Analytics — Power BI Desktop Integration Guide

**Version:** 1.0  
**Date:** August 30, 2026  
**Measures:** 15 (Trade Spend ROI, Execution Status, Incremental Lift)  
**Source Files:**
- `PowerBI/DAX/15_Promo_Measures.dax` (complete measure definitions)
- `PowerBI/QuickSetup/AllDAX_Consolidated.txt` (STEP 16, ready to paste)
- `PowerBI/RawDataFolders/Promo_Calendar/promo_mechanics_Sep_2026.csv` (2,613 SKU records)

---

## Step 1: Load Promo Calendar Dimension in Power BI Desktop

### 1a. Open Power BI Desktop

1. Open your existing `.pbix` file (should have Dim_Calendar, Dim_Chain, Dim_Brand, Dim_Distributor, Fact_Secondary_TOT_Hierarchy)
2. Go to **Transform Data** (Home tab)

### 1b. Import Promo Calendar CSV

1. **New Source** → **Text/CSV**
2. Navigate to: `PowerBI/RawDataFolders/Promo_Calendar/promo_mechanics_Sep_2026.csv`
3. Click **Load** (or **Transform Data** to adjust column types first)
4. Rename the query to: `Dim_PromoCalendar`

### 1c. Verify Data Load

In Power Query Editor, verify columns:
```
Source_Month            (Text: "2026-09")
Chain Name              (Text: Standardized chain names)
Brand                   (Text: Mamaearth, The Derma Co, etc.)
Category                (Text: Product category)
Sub_Category            (Text: Product sub-category)
Range                   (Text: Product range/line)
EAN Code                (Text: Article EAN code)
Article Code            (Text: Article/SKU code)
Description             (Text: Full product description)
MRP                     (Decimal: Maximum Retail Price)
Offer to consumer       (Text or Decimal: Offer value/discount)
ME_Contribution_Pct     (Decimal: Mamaearth contribution %)
Chain_Contribution_Pct  (Decimal: Chain contribution %)
Total_Contribution_Pct  (Decimal: Total trade spend %)
Locations               (Decimal: Store location count)
From                    (Date: Promo start date)
To                      (Date: Promo end date)
Promo_Type              (Text: "Consumer Promotion")
Promo_Key               (Text: Concatenated join key)
```

Click **Close & Apply**.

---

## Step 2: Wire Relationships in Model View

### 2a. Open Model View

Click **Model** (left sidebar)

### 2b. Create 3 Single-Direction Relationships

**Relationship 1: Promo Calendar ↔ Secondary TOT Hierarchy (EAN Link)**
```
From: Dim_PromoCalendar[EAN Code]
To:   Fact_Secondary_TOT_Hierarchy[EAN]
Direction: 1 → * (One-to-Many)
Cardinality: One-to-Many
Cross Filter: Single
Assume Referential Integrity: OFF (not all fact table EANs have promos)
```

**Relationship 2: Promo Calendar ↔ Brand Dimension**
```
From: Dim_PromoCalendar[Brand]
To:   Dim_Brand[Brand_Name]
Direction: 1 → * (One-to-Many)
Cardinality: One-to-Many
Cross Filter: Single
```

**Relationship 3: Promo Calendar ↔ Calendar Dimension**
```
From: Dim_PromoCalendar[From ]
To:   Dim_Calendar[Date]
Direction: 1 → * (One-to-Many)
Cardinality: One-to-Many
Cross Filter: Single
Note: This is the promo START date link for period-based filtering
```

### 2c. Verify All Relationships

Return to **Report View**. All four original relationships (Calendar, Distributor, Chain, Brand to Fact_Secondary_TOT_Hierarchy) should remain **active** (solid line).

---

## Step 3: Create Measures Table

### 3a. Add a New Table (or Use Existing _Measures)

1. Go to **Report View**
2. In the Data pane (right), locate or create a **_Measures** table
3. Click the table name, then **New Measure** (Home tab)

### 3b. Paste All 15 Measures

1. Open `PowerBI/QuickSetup/AllDAX_Consolidated.txt`
2. Navigate to **STEP 16: PROMOTIONAL ANALYTICS**
3. Copy each measure (starting with `[Actual NSV Lakh]` through `[Promo ROI Performance Band]`)
4. Paste into the formula bar in Power BI Desktop
5. Press Enter to commit each measure

**Measures to Create (in order):**
1. `[Actual NSV Lakh]` — Base sales volume
2. `[Actual Promoted NSV Lakh]` — NSV of promoted SKUs only
3. `[Baseline Non-Promoted NSV Lakh]` — Non-promoted baseline
4. `[Active Promo Offer Count]` — Number of active promos
5. `[Promoted NSV Share %]` — % of total NSV that is promoted
6. `[Promoted SKU Breadth %]` — % of SKUs under promotion
7. `[Planned Promo Discount %]` — Weighted average consumer discount
8. `[Planned Company Trade Spend %]` — Weighted avg Mamaearth contribution
9. `[Planned Trade Spend Value Lakh]` — Planned spend (₹ Lakh)
10. `[Actual Claim Expense Lakh]` — Actual trade spend from claims
11. `[Promo Spend Variance Lakh]` — Plan minus actual (₹ Lakh)
12. `[Promo Spend Variance %]` — Variance as %
13. `[Promo Execution Status]` — Status text (On-Plan / Over-Spent / Under-Utilized)
14. `[Incremental Promo NSV Lakh]` — Sales lift vs 3-month baseline
15. `[Promo Volume Lift %]` — Lift as % of baseline
16. `[Promo Trade Spend ROI]` — Incremental NSV ÷ Spend (ratio)
17. `[Promo Net Margin ROI]` — (Margin - Cost) ÷ Cost
18. `[Promo ROI Performance Band]` — Visual status band (High / Moderate / Break-even / Destroying)

---

## Step 4: Apply Formatting Strings

1. Select each measure in the Data pane
2. Go to **Measure Tools** → **Formatting** (or right-click → **Format**)
3. Apply the format string:

| Measure | Format String |
|---------|----------------|
| `[Actual NSV Lakh]`, `[Actual Promoted NSV Lakh]`, `[Baseline Non-Promoted NSV Lakh]`, `[Planned Trade Spend Value Lakh]`, `[Actual Claim Expense Lakh]`, `[Promo Spend Variance Lakh]`, `[Historical Baseline Velocity Lakh]`, `[Incremental Promo NSV Lakh]` | `₹#,##0.00 "L"` |
| `[Promoted NSV Share %]`, `[Promoted SKU Breadth %]`, `[Planned Promo Discount %]`, `[Planned Company Trade Spend %]`, `[Promo Spend Variance %]`, `[Promo Volume Lift %]`, `[Promo Net Margin ROI]` | `0.0%` |
| `[Active Promo Offer Count]` | `#,##0` |
| `[Promo Trade Spend ROI]` | `0.00 "x"` |
| `[Promo Execution Status]`, `[Promo ROI Performance Band]` | **(Default/Text)** |

---

## Step 5: Build Analytics Visuals

### Visual 1: Promo Trade Spend Variance Matrix

**Type:** Matrix (Pivot Table)

**Rows:**
- `Dim_Brand[Brand_Name]`
- `Dim_Chain[Chain_Name]`
- `Dim_PromoCalendar[EAN Code]`

**Columns:**
- (None — single month selected via slicer)

**Values:**
1. `[Actual Promoted NSV Lakh]` (column 1)
2. `[Planned Company Trade Spend %]` (column 2)
3. `[Planned Trade Spend Value Lakh]` (column 3)
4. `[Actual Claim Expense Lakh]` (column 4)
5. `[Promo Spend Variance Lakh]` (column 5)
6. `[Promo Execution Status]` (column 6)

**Conditional Formatting on `[Promo Spend Variance Lakh]`:**
- Apply background color scale based on `[Promo Spend Variance %]`:
  - **< -15%** → Background: `#FCE8E6` (Light Red), Font: `#C5221F` (Dark Red)
  - **-15% to +15%** → Background: `#E6F4EA` (Light Green), Font: `#137333` (Dark Green)
  - **> +15%** → Background: `#FEF7E0` (Light Amber), Font: `#B06000` (Dark Amber)

**Sorting:**
- Sort rows by `[Actual Promoted NSV Lakh]` descending

---

### Visual 2: Promo ROI Performance Dashboard

**Type:** Card (Multi-row card)

**Cards (one per measure):**
1. `[Actual Promoted NSV Lakh]` — "Promoted NSV"
2. `[Actual Claim Expense Lakh]` — "Claim Spend"
3. `[Incremental Promo NSV Lakh]` — "Incremental Lift"
4. `[Promo Trade Spend ROI]` — "Trade ROI"
5. `[Promo Net Margin ROI]` — "Margin ROI"

**Background Color by `[Promo ROI Performance Band]`:**
- Apply conditional formatting using measure value to select background:
  - 🟢 "High ROI (≥3.0x)" → Green background
  - 🟡 "Moderate ROI (1.5-3.0x)" → Yellow background
  - 🟠 "Break-even (1.0-1.5x)" → Orange background
  - 🔴 "Value Destroying (<1.0x)" → Red background

---

### Visual 3: Promo Volume Lift by Chain (Column Chart)

**Type:** Column Chart

**X-Axis:** `Dim_Chain[Chain_Name]` (sorted by descending `[Incremental Promo NSV Lakh]`)

**Y-Axis (Primary):** `[Incremental Promo NSV Lakh]` (₹ Lakh)

**Y-Axis (Secondary, optional):** `[Promo Volume Lift %]` (%)

**Tooltips:**
- Include `[Promo Trade Spend ROI]`, `[Actual Claim Expense Lakh]`

---

### Visual 4: Execution Status Gauge/KPI

**Type:** Gauge or Card

**Target Measure:** `[Promo Execution Status]`

**Display Logic:**
- Green ✓ — "On-Plan (Within ±15%)"
- Amber ⚠ — "Under-Utilized Plan" or "Over-Spent vs Plan"
- Red ✗ — "No Actual Offtake"

---

## Step 6: Add Slicers

Create the following slicers on a dedicated page:

1. **Month Slicer:** `Dim_Calendar[Month_Label]` (default to Sep-2026)
2. **Brand Slicer:** `Dim_Brand[Brand_Name]`
3. **Chain Slicer:** `Dim_Chain[Chain_Name]`
4. **Promo Type Slicer:** `Dim_PromoCalendar[Promo_Type]`

Cross-filter all visuals to these slicers.

---

## Step 7: Refresh & Validate

1. **Home** → **Refresh**
2. Monitor the Data Load Progress window
3. Expected: Dim_PromoCalendar loads 2,613 rows in <3 seconds
4. Verify:
   - ✅ No errors in Fact_Secondary_TOT_Hierarchy join
   - ✅ No #ERROR values in measure columns
   - ✅ `[Promo Execution Status]` shows one of 4 statuses (not blank)
   - ✅ `[Promo Trade Spend ROI]` shows numeric values or "Self-Liquidating" text
   - ✅ Matrix displays all brand-chain-EAN combinations with measures

---

## Troubleshooting

### Issue: "No Actual Offtake" appears for all rows

**Solution:**
- Verify Dim_PromoCalendar[EAN Code] column contains values (not blank)
- Check that Fact_Secondary_TOT_Hierarchy[EAN] has matching values
- Ensure relationship is **active** (solid line) in Model View

### Issue: `[Promo Spend Variance %]` shows #DIV/0!

**Solution:**
- This occurs when `[Planned Trade Spend Value Lakh]` is 0
- Verify Dim_PromoCalendar[ME_Contribution_Pct] has values > 0
- Check that `[Actual Promoted NSV Lakh]` > 0 for selected filters

### Issue: Measures show 0 or blank across the board

**Solution:**
- Verify Dim_PromoCalendar is marked as **Dim** (not Fact) in Model View
- Confirm relationships are **single-direction** (1 → *)
- Ensure cross-filter is set to **Single** (not Both)
- Run **Refresh** to reload data

---

## Measurement Interpretation Guide

| Measure | Interpretation | Target |
|---------|----------------|--------|
| `[Promoted NSV Share %]` | % of total NSV covered by active promos | 20–40% (optimal portfolio mix) |
| `[Promo Volume Lift %]` | Incremental sales % due to promo vs baseline | 15–50% (brand-dependent) |
| `[Promo Trade Spend ROI]` | Incremental NSV per ₹1 of trade spend | >1.5x (efficient), >3.0x (exceptional) |
| `[Promo Net Margin ROI]` | True profit net of claim cost (using 40% margin) | >0.2x (profitable), >1.0x (highly profitable) |
| `[Promo Spend Variance %]` | Planned vs actual spend gap | ±15% tolerance (on-plan) |
| `[Promo Execution Status]` | Promo plan execution quality | "On-Plan" is green light |

---

## Next Steps

1. **Integration:** Copy all 15 measures into your _Measures table (Step 3b)
2. **Validation:** Refresh and confirm zero errors (Step 7)
3. **Visuals:** Build trade spend variance matrix + ROI dashboard
4. **Slicing:** Apply monthly/brand/chain filters for drill-down analysis
5. **September Data:** Once Sep billing data arrives, refresh fact table to see Sep promo performance

---

## Support & Reference

**Files:**
- Measures: `PowerBI/DAX/15_Promo_Measures.dax`
- Consolidated: `PowerBI/QuickSetup/AllDAX_Consolidated.txt` (STEP 16)
- Data: `PowerBI/RawDataFolders/Promo_Calendar/promo_mechanics_Sep_2026.csv`

**Related Docs:**
- Power BI Integration Guide (Apr–Jul): `PowerBI/docs/TOT_Analysis_Power_BI_Integration_Guide.md`
- Promo Calendar Reference: `PowerBI/RawDataFolders/Promo_Calendar/promo_mechanics_Sep_2026.csv`

---

**Status:** ✅ **READY FOR POWER BI INTEGRATION**  
**Last Updated:** 2026-08-30
