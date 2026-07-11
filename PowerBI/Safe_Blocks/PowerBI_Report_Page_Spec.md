# Power BI Report Page Specification — Safe Offtake Blocks

**Branch:** claude/safe-powerbi-dashboard-rulings  
**Generated:** 2026-07-11  
**Version:** 3.1 (Tax-Basis Clarification: NSV EXCLUDING tax, MRP INCLUDING tax)  
**Status:** Tax-basis aware; ready for Power BI Desktop implementation

---

## Overview

Five report pages defined:
1. **Data Explorer** — drill-down and QC overview (MRP + NSV charts)
2. **Overview** — executive summary (MRP + NSV basis, June'26 partial)
3. **QC & Reconciliation** — data quality and validation
4. **Interim Offtake View: MRP, NSV & Qty** — Multi-basis view with trends and contribution
5. **BA Availability View** — Reliance Brand Counter coverage (NSV now active)

All pages:
- Use **MRP Sales Value, INCLUDING TAX** (verified rupees ÷ 10,000,000 for Cr display) as primary basis
- Include **NSV Sales Value, EXCLUDING TAX** (confirmed Lakhs ÷ 100 for Cr display) alongside MRP
- **Tax-basis aware labeling:** All NSV labeled "excl. tax"; all MRP labeled "incl. tax"
- **Comparisons marked QC/realization only** (tax bases differ; do not present as performance variance)
- Flag **June'26 as Partial** everywhere
- **Block profitability, CM2, margin %, BA profitability** (NSV unit confirmed; cost sources pending)
- Watermarks: "NSV excludes tax. MRP includes tax. Use separately for net/gross view."
- Page 5 shows **BA coverage only** (no BA profitability); includes NSV basis metrics (excl. tax)

---

## Page 1: Data Explorer

**Purpose:** Interactive drill-down and detailed data view

**Layout:** KPI cards (top) + charts grid (middle) + detail table (bottom)

### Page-Level Filters (Slicers)

| Slicer | Source | Type | Required | Notes |
|--------|--------|------|----------|-------|
| FY | Dim_Month | Dropdown | Yes | Multi-select allowed |
| Month | Dim_Month | Dropdown | Yes | Multi-select allowed |
| Chain | Dim_Chain_Raw | Dropdown | Yes | Multi-select; shows raw chain names (variants included) |
| Zone | Dim_Zone | Dropdown | Yes | Multi-select |
| Category | Dim_Category | Dropdown | No | Multi-select |
| PPT_Category | Dim_Category | Dropdown | No | Multi-select |
| Format | Fact_Offtake_Safe | Dropdown | No | Multi-select |
| Classification | Fact_Offtake_Safe | Dropdown | No | Multi-select |

**NOT included (blocked):**
- State filter (mapping pending)
- NSV-based slicer
- BA profitability filter

### KPI Cards (Top Row)

| Card | Measure | Format | Label | Tax Basis |
|------|---------|--------|-------|-----------|
| Row Count | [Row Count] | #,##0 | Transactions | N/A |
| MRP Sales Value | [MRP Sales Value Cr] | ₹X.XX Cr | MRP Sales Value, including tax | **Incl. Tax** |
| NSV Sales Value | [NSV Cr] | ₹X.XX Cr | NSV, excluding tax | **Excl. Tax** |
| Sales Qty | [Sales Qty] | #,##0 Cr Qty | Sales Qty | Qty only |
| Month Coverage | COUNT(Dim_Month) | # months | Months Covered | N/A |

### Charts (3-column grid)

| Position | Chart Type | Title | Measure | Dimension | Sort | Notes |
|----------|-----------|-------|---------|-----------|------|-------|
| Row 1, Col 1 | Column | MRP by Chain, including tax | [MRP Sales Value] | Chain | MRP Desc | Label: "incl. tax" |
| Row 1, Col 2 | Column | NSV by Zone, excluding tax | [NSV Cr] | Zone | NSV Desc | Label: "excl. tax" |
| Row 1, Col 3 | Column | MRP by Category, including tax | [MRP Sales Value] | Category | MRP Desc | Label: "incl. tax" |
| Row 2, Col 1 | Line | MRP Trend, including tax | [MRP Sales Value] | Month | Month ASC | Label: "incl. tax"; June'26 dashed |
| Row 2, Col 2 | Line | NSV Trend, excluding tax | [NSV Cr] | Month | Month ASC | Label: "excl. tax"; June'26 dashed |
| Row 2, Col 3 | Clustered | Contribution %: MRP & NSV | [MRP Contribution %], [NSV Contribution %] | Chain | % Desc | Dual-basis; note: "QC/realization only" |

### Detail Table

**Title:** "Detail Records (filtered)"

**Columns:**
- Site_Code
- Site_Name
- Chain_Name (raw, not canonicalized)
- Zone
- Category
- Month
- FY
- Sales_Qty
- MRP_Sales_Value (₹)

**Sorting:** Month ASC, Chain ASC, Category ASC

**Row Count:** Capped at 1,000 rows on-screen; note below table shows "Showing X of Y"

**Export:** Include "Export to Excel" button

### Page-Level Notes

- Add text box at top: "Interactive Data Explorer — Filter by any dimension and drill down. All cards and charts update live. Values in ₹ Crore unless noted."
- Add watermark: "NSV excludes tax. MRP includes tax. Use separately for net/gross view. For comparison: MRP to NSV ratio shown for QC/realization only (tax basis differs)."
- Add conditional warning box: IF [Has June26 Partial] THEN show "⚠ June'26 is PARTIAL: 78,111 rows from 16 chains only"
- Add note: "NSV = source Lakhs converted to ₹ Crore (Lakhs ÷ 100), **excluding tax**. MRP = actual rupees (÷10,000,000 for Cr), **including tax**. Both bases available for analysis; use separately."

---

## Page 2: Overview

**Purpose:** Executive summary (MRP basis only, watermarked interim)

**Layout:** Watermarks (top) + KPI section + charts grid

### Watermark Section (Top)

Add text box with:
```
Offtake Overview — Tax-Basis Aware (v3.1)
NSV ₹ Crore, EXCLUDING tax (source: Lakhs ÷ 100)
MRP ₹ Crore, INCLUDING tax (actual rupees ÷ 10,000,000)
June'26 Partial. Comparison shown for QC/realization only (tax basis differs).
```

Color: Teal background (#E8F5F2), dark text

### KPI Cards

| Card | Measure | Format | Label | Notes |
|------|---------|--------|-------|-------|
| Total MRP, incl. tax | [MRP Sales Value Cr] | ₹X.XX Cr | MRP including tax | ₹1,443.45 Cr baseline |
| Total NSV, excl. tax | [NSV Cr] | ₹X.XX Cr | NSV excluding tax | Confirmed unit (Lakhs) |
| MRP to NSV Ratio | [MRP to NSV Ratio] | X.XX | Realization only | Tax basis differs; QC use only |
| Total Qty | [Sales Qty] | #,##0 Cr Qty | Volume | 2,055.07 Cr Qty baseline |
| Active Chains | [Distinct Chains] | # | Count | 34 chains |
| Active Zones | [Distinct Zones] | # | Count | 37 zones (P6 canonicalized) |
| June'26 Partial Row Count | [June26 Partial Row Count] | #,##0 | Partial Flag | 78,111 rows (PARTIAL) |
| Negative Returns (MRP) | [Negative Return Rows] | #,##0 | Returns Count | 12,705 rows flagged |

### Charts (2-column Grid)

| Position | Chart Type | Title | Measures | Dimensions | Notes |
|----------|-----------|-------|----------|-----------|-------|
| Row 1, Col 1 | Line | MRP & NSV Trend (tax bases differ) | [MRP Sales Value] (incl. tax), [NSV Cr] (excl. tax) | Dim_Month[Month] | Dual-axis; June'26 dashed; add note "Comparison for QC/realization only" |
| Row 1, Col 2 | Line | MRP Trend by FY, incl. tax | [MRP Sales Value] | Dim_Month[FY] | Show 3-year trend; label "incl. tax" |
| Row 2, Col 1 | Doughnut | MRP Share by Zone, incl. tax | [MRP Sales Value] | Zone | Top 5 zones + Other; label "incl. tax" |
| Row 2, Col 2 | Doughnut | NSV Share by Category, excl. tax | [NSV Cr] | Category | Top 10 categories + Other; label "excl. tax" |
| Row 3, Col 1 | Bar | Top 10 Chains by MRP, incl. tax | [MRP Sales Value] | Chain | Descending; label "incl. tax" |
| Row 3, Col 2 | Clustered | Qty & NSV by Zone (excl. tax) | [Sales Qty], [NSV Cr] | Zone | Dual-axis; NSV labeled "excl. tax" |

### Slicers

Same as Data Explorer (FY, Month, Chain, Zone, Category, Format, Classification)

### Page Notes

- Add conditional formatting to highlight June'26 in all month-based visuals (dashed line, different color)
- Add watermark: "NSV excludes tax. MRP includes tax. Profitability/CM2 requires cost structure confirmation. Use NSV for net sales view. Use MRP for consumer value view. Comparison shown for QC/realization only."
- Add note under KPI cards: "MRP ₹ Cr, **including tax** (verified rupees basis). NSV ₹ Cr, **excluding tax** (confirmed Lakhs basis). Both bases available; do not directly compare as performance variance without tax-basis context."

---

## Page 3: QC & Reconciliation

**Purpose:** Data quality, validation, and flagged issues

**Layout:** Tables and summary cards (no chart drilling needed)

### Summary Cards (Top)

| Card | Measure | Value | Tax Basis |
|------|---------|-------|-----------|
| Total Files Scanned | Constant | 582 | N/A |
| Total Rows | [Row Count] | 4,211,571 | N/A |
| Data Period | Constant | Apr'24 – Jun'26 (27 months) | N/A |
| Grand MRP Total, incl. tax | [MRP Sales Value Cr] | ₹1,443.45 Cr | **Including Tax** |
| Grand NSV Total, excl. tax | [NSV Cr] | ₹X.XX Cr | **Excluding Tax** |
| Data Quality | Text | ✓ Safe for MRP & NSV basis reporting (tax bases differ) | N/A |

### Table 1: Monthly Reconciliation

**Source:** QC_Monthly_Reconciliation

**Columns:**
- Month
- FY
- Is_Month_Partial (badge: red "PARTIAL" if TRUE)
- Row_Count
- MRP_Sales_Value Cr, incl. tax (₹ Cr)
- NSV_Sales_Value Cr, excl. tax (₹ Cr)
- Sales_Qty (Cr Qty)
- Negative_MRP_Count (badge: orange)
- Negative_NSV_Count (badge: orange)
- MRP to NSV Ratio (QC/realization only)

**Sort:** Month ASC

**Conditional Formatting:**
- June'26 row: Highlight background orange
- All negative-return counts: Show in orange

### Table 2: Chain Variant Summary

**Source:** QC_Chain_Variant_Check

**Columns:**
- Chain_Name (sorted by Row_Count DESC)
- Row_Count
- MRP_Total (₹ Cr)

**Notes Below Table:**
"34 distinct chain names found (some are variants, pending canonicalization).
Examples of variants: Vmm/VMM, Fsn/FSN, Walmart Cnc/CNC, Ratanadeep/Ratanadeep.
More Retail: 40,848 rows; 13,661 exact-dup rows (33.4%) = ₹1.36 Cr MRP (10.3% inflated).
Duplicates NOT removed; pending business decision."

### Table 3: More Retail Duplicate Report

**Source:** QC_Duplicate_Report (if > 0 rows)

**Columns:**
- Count (duplicates)
- MRP_Total (₹)
- Sample_Month

**Note:** "Exact-duplicate rows in More Retail. Do NOT interpret as errors; awaiting business decision on remediation (de-dupe, fix at source, or footnote)."

### Text Box: Approved & Blocked Status (v3.1: Tax-Basis Aware)

**Title:** "Business Approvals & Blockers"

**Content (formatted as list):**
```
APPROVED ✓
✓ NSV unit = Lakhs (v3); NSV tax basis = excluding tax (v3.1); all NSV measures ACTIVE
✓ MRP tax basis = including tax (v3.1)
✓ NSV & MRP tax-basis awareness applied to all labels (v3.1)
✓ More Retail chain totals (all rows retained, no dedup)
✓ Brand Counter BA Availability (Page 5 shows coverage only)
✓ State-level reporting (zone-only approach; no state rollups)

BLOCKED (Pending Inputs)
✗ P&L / Profitability measures (requires CM2 formula + cost sources)
✗ CM2 / Contribution Margin 2 (requires cost structure + exact CM2 formula accounting for tax basis)
✗ Margin % (requires margin assumptions and cost sources)
✗ BA profitability (requires BA Headcount + cost structure; BA coverage active on Page 5)
✗ Primary vs Offtake Gap (requires Primary NSV validation)
✗ Chain-level reporting for variants (canonicalization pending; variants reported separately)
```

### Text Box: Pending Business Decisions

**Table format (completed + ongoing):**

| # | Decision | Timeline | Status |
|---|----------|----------|--------|
| 1 | NSV Unit Validation | ✓ COMPLETE (v3) | Confirmed Lakhs; all NSV measures now ACTIVE |
| 2 | NSV/MRP Tax-Basis Clarification | ✓ COMPLETE (v3.1) | NSV excl. tax, MRP incl. tax; all labels applied |
| 3 | More Retail Duplicates | ✓ COMPLETE | Approved: all rows retained, no dedup (13,661 dup rows flagged) |
| 4 | Brand Counter Classification | ✓ COMPLETE | Approved: BA Availability flag; Page 5 shows coverage |
| 5 | State-to-City Mapping | ✓ COMPLETE | Approved: zone-only approach; no state rollups (P6 zones used) |
| 6 | Profitability & Cost Structure | Pending | Blocks P&L, CM2, Margin %, BA profitability; awaiting CM2 formula + cost data |
| 7 | BA Headcount & Cost | Pending | Blocks BA profitability; BA coverage active on Page 5 |
| 8 | Chain Master Canonicalization | Pending | Blocks chain-level consolidation; variants reported separately |

---

## Page 4: Interim Offtake View: MRP, NSV & Qty

**Purpose:** Multi-basis view with MRP and NSV confirmed; shows trends and contribution; profitability measures still blocked

**Title & Watermark (Top):**
```
Interim Offtake View: Tax-Basis Aware (v3.1)
NSV ₹ Crore, EXCLUDING tax (Lakhs ÷ 100) | MRP ₹ Crore, INCLUDING tax (rupees ÷ 10,000,000) | June'26 Partial
```

**Layout:** Watermark + KPI section + charts

### Watermark Text Box

Color: Amber background (#FFF7E6), dark text

Text:
```
Interim view. NSV confirmed at source (Lakhs), **EXCLUDING tax**; converted to ₹ Crore (÷100) for display.
MRP in actual rupees, **INCLUDING tax**; converted to ₹ Crore (÷10,000,000) for display.
⚠ NSV and MRP operate on different tax bases. Do NOT present MRP vs NSV as direct performance variance.
Use NSV separately for net sales analysis. Use MRP separately for consumer value analysis.
Comparison shown for QC/realization only. All profitability, margin %, and CM2 measures remain blocked.
June'26 data is PARTIAL (78,111 rows; some accounts pending).
```

### KPI Cards

| Card | Measure | Format | Label | Tax Basis |
|------|---------|--------|-------|-----------|
| Total Offtake, incl. tax | [MRP Sales Value Cr] | ₹X.XX Cr | MRP including tax | **Including Tax** |
| Total Offtake, excl. tax | [NSV Cr] | ₹X.XX Cr | NSV excluding tax | **Excluding Tax** |
| Total Qty | [Sales Qty] | #,##0 Cr Qty | Volume | Qty only |
| Avg MRP/Month, incl. tax | [Avg MRP Per Month Cr] | ₹X.XX Cr | Monthly average | **Including Tax** |
| MRP to NSV Ratio | [MRP to NSV Ratio] | X.XX | Realization (QC only) | Tax bases differ |
| Jun'26 MRP, incl. tax | CALCULATE([MRP Sales Value Cr], Dim_Month[Is_June26_Partial]=TRUE) | ₹X.XX Cr | PARTIAL month | **Including Tax** |

### Charts (2-column Grid)

| Position | Chart Type | Title | Measures | Dimensions | Notes |
|----------|-----------|-------|----------|-----------|-------|
| Row 1, Col 1 | Column | MRP by Chain, incl. tax | [MRP Sales Value] | Chain (top 10 + Other) | MRP Desc; June'26 dashed; label "incl. tax" |
| Row 1, Col 2 | Column | NSV by Zone, excl. tax | [NSV Cr] | Zone | NSV Desc; label "excl. tax" |
| Row 2, Col 1 | Line | MRP Trend, incl. tax | [MRP Sales Value] | Dim_Month[Month] | Mark June'26 dashed; label "incl. tax" |
| Row 2, Col 2 | Line | NSV Trend, excl. tax | [NSV Cr] | Dim_Month[Month] | Mark June'26 dashed; label "excl. tax" |
| Row 3, Col 1 | Clustered | Contribution %: MRP & NSV (tax bases differ) | [MRP Contribution %], [NSV Contribution %] | Category (top 10 + Other) | Dual-basis; note "QC/realization only" |
| Row 3, Col 2 | Clustered | MoM Change: MRP & NSV (tax bases differ) | [MRP MoM Abs Change Cr], [NSV MoM Abs Change Cr] | Dim_Month[Month] | Dual-metric; note "Compare separately by tax basis" |

### Page-Level Slicers

- FY
- Month (exclude June'26 or mark as partial)
- Chain (raw names, variants included)
- Zone
- Category

### Page Notes

- Add conditional text box: IF [Has June26 Partial] THEN "⚠ June'26 is selected. Data from this month is PARTIAL (78,111 rows)."
- Add info box: "MRP (incl. tax) and NSV (excl. tax) confirmed and active. Do not compare them directly as performance metrics without tax-basis context. Use MRP separately for consumer value view. Use NSV separately for net sales view. Comparison ratios shown for QC/realization only. Profitability, CM2, margin %, and BA profitability measures remain BLOCKED pending cost structure."
- Do NOT include slicers or measures for:
  - Margin %
  - Profitability / CM2
  - BA metrics
  - State
  - (NSV and MRP tax-basis labels required on all visuals)

---

## Cross-Page Interaction Rules

1. **Bookmark / Filter Propagation:** All slicers on every page affect every other page instantly
2. **Drill-Through (if available):** Clicking a chain in Data Explorer can drill to Overview with that chain filtered
3. **Tooltips:** All charts show value + % contribution + month (if applicable)
4. **Conditional Visibility:** June'26 warning boxes appear only when June'26 is in the current filter

---

## Text Watermarks (All Pages)

Every page must display (top-right or top-center):

**Small text (10pt):**
```
Safe Offtake Analytics v3.1 — Tax-Basis Aware | June'26 Partial | claude/safe-powerbi-dashboard-rulings
NSV ₹ Cr, EXCLUDING tax (Lakhs ÷ 100) | MRP ₹ Cr, INCLUDING tax (Rupees ÷ 10,000,000)
Comparison for QC/realization only. Do not present MRP vs NSV as performance variance without tax context.
```

---

## Formatting Standards

- **Color Scheme:**
  - Teal primary (#2D9B7F)
  - Amber warning (#C77D17)
  - Red blocked (#C0392B)
  - Green up (#1E8E3E)

- **Font:** Aptos or Segoe UI, 11–12pt

- **Number Formats:**
  - Currency: ₹X.XX Cr or ₹X.XX L (auto-select based on magnitude)
  - Percentage: X.X% (1 decimal)
  - Count: #,##0 (thousands separator)

- **Chart Defaults:**
  - Sort high→low (MRP/Qty)
  - Show data labels on bars
  - Use consistent colors (teal for MRP, blue for Qty, amber for June'26)

---

## Page 5: BA Availability View

**Purpose:** Show Reliance Brand Counter coverage (BA availability only, not profitability)

**Title & Watermark (Top):**
```
Reliance BA Availability Coverage (Tax-Basis Aware v3.1)
Brand Counter represents places/accounts where our BA is available.
⚠ Coverage view only. Shows NSV (excl. tax) & MRP (incl. tax). BA profitability blocked until cost structure confirmed.
```

**Layout:** KPI section + charts + detail view

### Watermark Text Box

Color: Amber background (#FFF7E6), dark text

Text:
```
BA Availability View Only (Coverage, Not Profitability)
This page shows Reliance Brand Counter coverage (BA Available = Yes) with NSV/MRP basis.
NSV shown excluding tax. MRP shown including tax. Use separately for net/gross view.
It does NOT include BA profitability, BA cost, or BA productivity metrics.
These remain blocked until: (1) BA Headcount is provided, (2) Cost structure is confirmed.
```

### KPI Cards

| Card | Measure | Format | Label | Tax Basis |
|------|---------|--------|-------|-----------|
| BA Available Row Count | [BA Available Row Count] | #,##0 | Transactions | N/A |
| BA Available MRP, incl. tax | [BA Available MRP Sales Value Cr] | ₹X.XX Cr | MRP for BA rows | **Including Tax** |
| BA Available NSV, excl. tax | [BA Available NSV Cr] | ₹X.XX Cr | NSV for BA rows | **Excluding Tax** |
| BA Availability Mix % (MRP) | [BA Availability Mix %] | X.X% | BA as % of total MRP | **Including Tax** |
| BA Availability Mix % (NSV) | [BA Availability Mix % NSV] | X.X% | BA as % of total NSV | **Excluding Tax** |
| Total MRP (All), incl. tax | [MRP Sales Value Cr] | ₹X.XX Cr | Reference | **Including Tax** |

### Charts (2-column Grid)

| Position | Chart Type | Title | Measures | Dimensions | Notes |
|----------|-----------|-------|----------|-----------|-------|
| Row 1, Col 1 | Column | BA Available MRP by Zone, incl. tax | [BA Available MRP Sales Value] | Zone | MRP Desc; label "incl. tax"; Reliance zones |
| Row 1, Col 2 | Column | BA Available NSV by Category, excl. tax | [BA Available NSV Cr] | Category | NSV Desc; label "excl. tax" |
| Row 2, Col 1 | Line | BA Available MRP Trend, incl. tax | [BA Available MRP Sales Value] | Dim_Month[Month] | Show BA MRP trend; label "incl. tax"; June'26 dashed |
| Row 2, Col 2 | Line | BA Available NSV Trend, excl. tax | [BA Available NSV Cr] | Dim_Month[Month] | Show BA NSV trend; label "excl. tax"; June'26 dashed |

### Slicers

- FY (required)
- Month (required)
- Zone (recommended; can filter to Reliance zones)
- Category (optional)

**NOT included:**
- State slicer
- NSV-based slicer
- BA profitability slicers

### Detail Table

**Title:** "BA Available Records (Reliance Brand Counter)"

**Columns:**
- Site_Code
- Site_Name
- Chain_Name (= "Brand Counter" in this view)
- Zone
- Category
- Month
- FY
- Sales_Qty
- MRP_Sales_Value (₹)
- BA_Available (should be "Yes" for all rows)

**Sorting:** Month ASC, Zone ASC, Category ASC

**Row Count:** Capped at 1,000 rows on-screen

### Page-Level Notes

- Add text box: "Reliance BA Availability shows Brand Counter coverage (BA Available = Yes). Business decision APPROVED: Brand Counter represents BA availability, not a chain for profit-center allocation."
- Add tax-basis note: "NSV shown excluding tax (Lakhs basis). MRP shown including tax (rupees basis). Use separately for analysis; do not compare directly."
- Add conditional text: IF no Brand Counter rows selected THEN "No Brand Counter rows in current filter."
- Add note: "BA profitability metrics are blocked (requires BA Headcount + cost structure). Use Overview or Data Explorer pages for full chain analysis."

### Validation

- [ ] [BA Available Row Count] > 0 when data includes Brand Counter
- [ ] [BA Availability Mix %] is between 0–100%
- [ ] No NSV measures appear on this page
- [ ] No State-level breakdowns
- [ ] No profitability or CM2 measures
- [ ] Watermark clearly states "Coverage only"
- [ ] All charts use [BA Available MRP Sales Value] only

---

## Validation Checklist

Before publishing, confirm:

- [ ] NSV measures appear on all 5 pages (now ACTIVE, no longer blocked)
- [ ] NSV Cr calculations are correct (Lakhs ÷ 100)
- [ ] MRP Cr calculations are correct (rupees ÷ 10,000,000)
- [ ] NSV and MRP both displayed in ₹ Crore for comparison
- [ ] No State dimension slicers exist
- [ ] No BA profitability visuals exist (Page 5 shows coverage only)
- [ ] No Profitability/CM2/Margin % visuals exist
- [ ] June'26 flagged as Partial on Pages 1–4
- [ ] Watermarks visible on all 5 pages (updated to reflect NSV confirmed)
- [ ] MRP and NSV are dual value basis (all pages)
- [ ] More Retail rows are kept; no dedup applied
- [ ] Chain variants preserved (not canonicalized)
- [ ] Slicers: FY, Month, Chain (raw), Zone, Category, Format, Classification only
- [ ] Blocked measures list visible on QC page (updated: NSV marked COMPLETE, cost sources marked PENDING)
- [ ] Pending decisions table visible on QC page (NSV, More Retail, Brand Counter, State marked COMPLETE)
- [ ] June'26 marked distinctly on Pages 1–4 (dashed line, different color)
- [ ] Info boxes explain NSV confirmed and cost structure pending on Pages 1–4
- [ ] Page 4 renamed: "Interim Offtake View: MRP, NSV & Qty"
- [ ] Page 5 (BA Availability) includes NSV-based measures; clearly marked as "coverage only, not profitability"
- [ ] More Retail note: "Business-approved retained records"
- [ ] State note: "Source data unreliable; zone-level reporting used instead"
- [ ] Watermark: "NSV converted from Lakhs to ₹ Crore" (replaces "NSV unit pending")

---

**Status:** Ready for implementation in Power BI Desktop.

