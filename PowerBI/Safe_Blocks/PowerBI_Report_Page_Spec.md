# Power BI Report Page Specification — Safe Offtake Blocks

**Branch:** claude/safe-powerbi-blocks  
**Generated:** 2026-07-11  
**Status:** Draft (specification for Power BI Desktop implementation)

---

## Overview

Four report pages defined:
1. **Data Explorer** — drill-down and QC overview
2. **Overview** — executive summary (MRP basis, June'26 partial)
3. **QC & Reconciliation** — data quality and validation
4. **Interim Offtake P&L** — MRP Sales Value basis only (NSV pending)

All pages:
- Use **MRP Sales Value** as the only value basis
- Flag **June'26 as Partial** everywhere
- **Block NSV, state-level, BA profitability** measures
- Display watermarks: "⚠ NSV unit pending", "⚠ June'26 Partial"

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

| Card | Measure | Format | Conditional |
|------|---------|--------|-------------|
| Row Count | [Row Count] | #,##0 | None |
| MRP Sales Value | [MRP Sales Value Cr] | ₹X.XX Cr | None |
| Sales Qty | [Sales Qty] | #,##0 Cr Qty | None |
| Month Coverage | COUNT(Dim_Month) | # months | None |

### Charts (3-column grid)

| Position | Chart Type | Title | Measure | Dimension | Sort | Interactions |
|----------|-----------|-------|---------|-----------|------|--------------|
| Row 1, Col 1 | Column | MRP by Chain | [MRP Sales Value] | Chain | MRP Desc | Click → Filter |
| Row 1, Col 2 | Column | MRP by Zone | [MRP Sales Value] | Zone | MRP Desc | Click → Filter |
| Row 1, Col 3 | Column | MRP by Category | [MRP Sales Value] | Category | MRP Desc | Click → Filter |
| Row 2, Col 1 | Line | MRP Trend by Month | [MRP Sales Value] | Month | Month ASC | Hover tooltip |
| Row 2, Col 2 | Line | Qty Trend by Month | [Sales Qty] | Month | Month ASC | Hover tooltip |
| Row 2, Col 3 | Clustered | Contribution % (MRP) | [MRP Contribution %] | Chain | % Desc | None |

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
- Add conditional warning box: IF [Has June26 Partial] THEN show "⚠ June'26 is PARTIAL: 78,111 rows from 16 chains only"
- Add note: "NSV-based views blocked until unit validation complete."

---

## Page 2: Overview

**Purpose:** Executive summary (MRP basis only, watermarked interim)

**Layout:** Watermarks (top) + KPI section + charts grid

### Watermark Section (Top)

Add text box with:
```
Interim Offtake Overview — MRP Sales Value Basis
⚠ NSV unit pending | June'26 Partial
```

Color: Amber background (#FFF7E6), dark text

### KPI Cards

| Card | Measure | Format | Baseline |
|------|---------|--------|----------|
| Total MRP (Apr'24–Jun'26) | [MRP Sales Value Cr] | ₹X.XX Cr | ₹1,443.45 Cr |
| Total Qty (Apr'24–Jun'26) | [Sales Qty] | #,##0 Cr Qty | 2,055.07 Cr Qty |
| Active Chains | [Distinct Chains] | # | 34 chains |
| Active Zones | [Distinct Zones] | # | 37 zones |
| June'26 Row Count | [June26 Partial Row Count] | #,##0 | 78,111 rows (PARTIAL) |
| Negative Returns | [Negative Return Rows] | #,##0 | 12,705 rows |

### Charts (2-column Grid)

| Position | Chart Type | Title | Measures | Dimensions | Notes |
|----------|-----------|-------|----------|-----------|-------|
| Row 1, Col 1 | Line | MRP Trend by Month | [MRP Sales Value] | Dim_Month[Month] | Mark June'26 differently (dashed line or different color) |
| Row 1, Col 2 | Line | MRP Trend by FY | [MRP Sales Value] | Dim_Month[FY] | Show 3-year trend |
| Row 2, Col 1 | Doughnut | MRP Share by Zone | [MRP Sales Value] | Zone | Top 5 zones + Other |
| Row 2, Col 2 | Doughnut | MRP Share by Category | [MRP Sales Value] | Category | Top 10 categories + Other |
| Row 3, Col 1 | Bar | Top 10 Chains by MRP | [MRP Sales Value] | Chain | Descending; add variance to previous period if available |
| Row 3, Col 2 | Clustered | Qty vs MRP by Zone | [Sales Qty], [MRP Sales Value] | Zone | Dual-axis if needed |

### Slicers

Same as Data Explorer (FY, Month, Chain, Zone, Category, Format, Classification)

### Page Notes

- Add conditional formatting to highlight June'26 in all month-based visuals
- Add watermark: "Interim only: NSV unit pending. Not for final profitability review."
- Add note under MRP cards: "Based on verified MRP Sales Value. NSV-based measures blocked until business validation."

---

## Page 3: QC & Reconciliation

**Purpose:** Data quality, validation, and flagged issues

**Layout:** Tables and summary cards (no chart drilling needed)

### Summary Cards (Top)

| Card | Measure | Value |
|------|---------|-------|
| Total Files Scanned | Constant | 582 |
| Total Rows | [Row Count] | 4,211,571 |
| Data Period | Constant | Apr'24 – Jun'26 (27 months) |
| Grand MRP Total | [MRP Sales Value Cr] | ₹1,443.45 Cr |
| Data Quality | Text | ✓ Safe for MRP-basis reporting |

### Table 1: Monthly Reconciliation

**Source:** QC_Monthly_Reconciliation

**Columns:**
- Month
- FY
- Is_Month_Partial (badge: red "PARTIAL" if TRUE)
- Row_Count
- MRP_Sales_Value (₹ Cr)
- Sales_Qty (Cr Qty)
- Negative_Value_Row_Count (badge: orange)

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

### Text Box: Blocked Measures

**Title:** "Blocked Measures (Awaiting Business Approval)"

**Content (formatted as list):**
```
✗ NSV (unit unvalidated)
✗ P&L / Profitability measures
✗ CM2, Margin %, Contribution % (NSV-based)
✗ State-level rollups (City-State mapping pending)
✗ More Retail chain totals (dedup pending)
✗ Chain-level reporting for variants (canonicalization pending)
✗ BA profitability (Headcount + classification pending)
```

### Text Box: Pending Business Decisions (6 items)

**Table format (or 6 text boxes):**

| # | Decision | Timeline |
|---|----------|----------|
| 1 | NSV Unit Validation | 1–2 weeks (HIGHEST PRIORITY) |
| 2 | More Retail Duplicates | 1–3 weeks |
| 3 | Brand Counter Classification | 1 week |
| 4 | State-to-City Mapping | 1–2 weeks |
| 5 | Chain Master Canonicalization | 1 week |
| 6 | Reliance Schema | 1–3 weeks |

---

## Page 4: Interim Offtake P&L (MRP Basis)

**Purpose:** P&L view on MRP Sales Value basis only; NSV marked as pending

**Title & Watermark (Top):**
```
Interim Offtake P&L: MRP Sales Value Basis
⚠ Interim only: NSV unit pending. Not for final profitability review.
⚠ June'26 Partial.
```

**Layout:** Watermark + KPI section + charts

### Watermark Text Box

Color: Red/amber background (#FCE8E6), dark red text

Text:
```
⚠ INTERIM ONLY
This P&L uses MRP Sales Value (verified, rupee basis) as the value foundation.
Net Sales Value (NSV) is unit-unvalidated and blocked.
All profitability, margin %, and CM2 measures are blocked until NSV unit is confirmed.
June'26 data is PARTIAL (78,111 rows; some accounts pending).
```

### KPI Cards

| Card | Measure | Format | Notes |
|------|---------|--------|-------|
| Total Offtake (MRP) | [MRP Sales Value Cr] | ₹X.XX Cr | Verified, rupee basis |
| Total Qty | [Sales Qty] | #,##0 Cr Qty | Units |
| Avg MRP/Month | [Avg MRP Per Month Cr] | ₹X.XX Cr | Average across months |
| Jun'26 MRP | CALCULATE([MRP Sales Value Cr], Dim_Month[Is_June26_Partial]=TRUE) | ₹X.XX Cr | Partial month warning |

### Charts (2-column Grid)

| Position | Chart Type | Title | Measures | Dimensions | Notes |
|----------|-----------|-------|----------|-----------|-------|
| Row 1, Col 1 | Column | MRP by Chain | [MRP Sales Value] | Chain (top 10 + Other) | MRP Desc; June'26 visibly marked |
| Row 1, Col 2 | Column | MRP by Zone | [MRP Sales Value] | Zone | MRP Desc |
| Row 2, Col 1 | Line | MRP Trend (Month) | [MRP Sales Value] | Dim_Month[Month] | Mark June'26 differently; add MoM absolute change annotation |
| Row 2, Col 2 | Pie | Category Mix (%) | [MRP Contribution %] | Category (top 10 + Other) | % basis |
| Row 3, Col 1 | Table | Top 15 Category × Chain | [MRP Sales Value], [MRP Contribution %] | Category, Chain | MRP Desc |
| Row 3, Col 2 | Card | MRP MoM Abs Change | [MRP MoM Abs Change Cr] | Current month vs prev | Variance indicator: green ↑ / red ↓ |

### Page-Level Slicers

- FY
- Month (exclude June'26 or mark as partial)
- Chain (raw names, variants included)
- Zone
- Category

### Page Notes

- Add conditional text box: IF [Has June26 Partial] THEN "⚠ June'26 is selected. Data from this month is PARTIAL."
- Add info box: "NSV-based measures (profitability, CM2, margin %, Contribution on NSV basis) are BLOCKED and not shown. Use MRP Sales Value basis for interim reporting only."
- Do NOT include slicers or measures for:
  - NSV
  - Margin %
  - Profitability
  - State
  - BA metrics

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
Interim MRP-Basis View | NSV Unit Pending | June'26 Partial
Safe Blocks Build | claude/safe-powerbi-blocks
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

## Validation Checklist

Before publishing, confirm:

- [ ] No NSV measure appears in any active visual
- [ ] No State dimension slicers exist
- [ ] No BA profitability visuals exist
- [ ] June'26 flagged as Partial on every page
- [ ] Watermarks visible on all 4 pages
- [ ] MRP Sales Value is sole value basis
- [ ] More Retail duplicates reported but NOT deduped
- [ ] Chain variants preserved (not canonicalized)
- [ ] Slicers: FY, Month, Chain (raw), Zone, Category, Format, Classification only
- [ ] Blocked measures list visible on QC page
- [ ] Pending decisions table visible on QC page
- [ ] June'26 marked distinctly in all month-based visuals (dashed line, different color)
- [ ] Info boxes explain NSV pending and interim basis on every value-showing page

---

**Status:** Ready for implementation in Power BI Desktop.

