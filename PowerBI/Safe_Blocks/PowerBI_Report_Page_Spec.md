# Power BI Report Page Specification — Safe Offtake Blocks

**Branch:** claude/safe-powerbi-dashboard-rulings  
**Generated:** 2026-07-11  
**Version:** 3 (NSV unit confirmed; all NSV measures now ACTIVE)  
**Status:** Updated for Power BI Desktop implementation

---

## Overview

Five report pages defined:
1. **Data Explorer** — drill-down and QC overview (MRP + NSV charts)
2. **Overview** — executive summary (MRP + NSV basis, June'26 partial)
3. **QC & Reconciliation** — data quality and validation
4. **Interim Offtake View: MRP, NSV & Qty** — Multi-basis view with trends and contribution
5. **BA Availability View** — Reliance Brand Counter coverage (NSV now active)

All pages:
- Use **MRP Sales Value** (verified rupees ÷ 10,000,000 for Cr display) as primary basis
- Include **NSV Sales Value** (converted from Lakhs ÷ 100 for Cr display) alongside MRP
- Flag **June'26 as Partial** everywhere
- **Block profitability, CM2, margin %, BA profitability** measures (NSV unit now confirmed)
- Display watermarks: "NSV converted from Lakhs to ₹Cr", "⚠ June'26 Partial"
- Page 5 shows **BA coverage only** (no BA profitability); now includes NSV basis metrics

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
| NSV Sales Value | [NSV Cr] | ₹X.XX Cr | None (NSV now active) |
| Sales Qty | [Sales Qty] | #,##0 Cr Qty | None |
| Month Coverage | COUNT(Dim_Month) | # months | None |

### Charts (3-column grid)

| Position | Chart Type | Title | Measure | Dimension | Sort | Interactions |
|----------|-----------|-------|---------|-----------|------|--------------|
| Row 1, Col 1 | Column | MRP by Chain | [MRP Sales Value] | Chain | MRP Desc | Click → Filter |
| Row 1, Col 2 | Column | NSV by Zone | [NSV Cr] | Zone | NSV Desc | Click → Filter (NSV now active) |
| Row 1, Col 3 | Column | MRP by Category | [MRP Sales Value] | Category | MRP Desc | Click → Filter |
| Row 2, Col 1 | Line | MRP Trend by Month | [MRP Sales Value] | Month | Month ASC | Hover tooltip |
| Row 2, Col 2 | Line | NSV Trend by Month | [NSV Cr] | Month | Month ASC | Hover tooltip (NSV now active) |
| Row 2, Col 3 | Clustered | Contribution % (MRP vs NSV) | [MRP Contribution %], [NSV Contribution %] | Chain | % Desc | Dual-basis comparison |

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
- Add note: "NSV values converted from source Lakhs to ₹ Crore (NSV Cr = Lakhs ÷ 100). MRP in actual rupees (÷10,000,000 for Cr display). NSV now confirmed and active."

---

## Page 2: Overview

**Purpose:** Executive summary (MRP basis only, watermarked interim)

**Layout:** Watermarks (top) + KPI section + charts grid

### Watermark Section (Top)

Add text box with:
```
Offtake Overview — MRP & NSV Sales Value Basis (v3: NSV Confirmed Lakhs)
NSV converted to ₹ Crore (Lakhs ÷ 100) | MRP in ₹ actual rupees (÷10,000,000 for Cr) | June'26 Partial
```

Color: Teal background (#E8F5F2), dark text

### KPI Cards

| Card | Measure | Format | Baseline |
|------|---------|--------|----------|
| Total MRP (Apr'24–Jun'26) | [MRP Sales Value Cr] | ₹X.XX Cr | ₹1,443.45 Cr |
| Total NSV (Apr'24–Jun'26) | [NSV Cr] | ₹X.XX Cr | ₹X.XX Cr (NSV now active) |
| MRP vs NSV Ratio | [MRP to NSV Ratio] | X.XX | Relationship indicator |
| Total Qty (Apr'24–Jun'26) | [Sales Qty] | #,##0 Cr Qty | 2,055.07 Cr Qty |
| Active Chains | [Distinct Chains] | # | 34 chains |
| Active Zones | [Distinct Zones] | # | 37 zones |
| June'26 Row Count | [June26 Partial Row Count] | #,##0 | 78,111 rows (PARTIAL) |
| Negative Returns | [Negative Return Rows] | #,##0 | 12,705 rows |

### Charts (2-column Grid)

| Position | Chart Type | Title | Measures | Dimensions | Notes |
|----------|-----------|-------|----------|-----------|-------|
| Row 1, Col 1 | Line | MRP vs NSV Trend (Month) | [MRP Sales Value], [NSV Cr] | Dim_Month[Month] | Mark June'26 differently (dashed line); dual-axis for scale |
| Row 1, Col 2 | Line | MRP Trend by FY | [MRP Sales Value] | Dim_Month[FY] | Show 3-year trend |
| Row 2, Col 1 | Doughnut | MRP Share by Zone | [MRP Sales Value] | Zone | Top 5 zones + Other |
| Row 2, Col 2 | Doughnut | NSV Share by Category | [NSV Cr] | Category | Top 10 categories + Other (NSV now active) |
| Row 3, Col 1 | Bar | Top 10 Chains by MRP | [MRP Sales Value] | Chain | Descending; add variance to previous period if available |
| Row 3, Col 2 | Clustered | Qty vs NSV by Zone | [Sales Qty], [NSV Cr] | Zone | Dual-axis if needed (NSV now active) |

### Slicers

Same as Data Explorer (FY, Month, Chain, Zone, Category, Format, Classification)

### Page Notes

- Add conditional formatting to highlight June'26 in all month-based visuals
- Add watermark: "Interim view: MRP & NSV confirmed. Not for final profitability review (cost structure pending)."
- Add note under cards: "MRP = verified actual rupees (÷10,000,000 for Cr). NSV = confirmed source Lakhs (÷100 for Cr). Both displayable in ₹ Crore for side-by-side comparison."

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
| Grand NSV Total | [NSV Cr] | ₹X.XX Cr (NSV now confirmed) |
| Data Quality | Text | ✓ Safe for MRP & NSV basis reporting |

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

**Title:** "Blocked Measures (v3: NSV Confirmed, Cost Sources Now Block)"

**Content (formatted as list):**
```
✓ NSV (unit confirmed as Lakhs; now ACTIVE)
✓ More Retail chain totals (business approved; all rows retained)
✓ Brand Counter BA Availability (approved; Page 5 shows coverage)
✓ State-level reporting (approved zone-only approach)

✗ P&L / Profitability measures (requires cost sources, COGS, allocation rules)
✗ CM2 (requires cost source and accounting method)
✗ Margin % (requires margin assumptions and cost sources)
✗ BA profitability (requires BA Headcount + cost structure)
✗ Primary vs Offtake Gap (requires Primary NSV validation)
✗ Chain-level reporting for variants (canonicalization pending)
```

### Text Box: Pending Business Decisions

**Table format (completed + ongoing):**

| # | Decision | Timeline | Status |
|---|----------|----------|--------|
| 1 | NSV Unit Validation | COMPLETE | ✓ Confirmed Lakhs; all NSV measures now active |
| 2 | More Retail Duplicates | COMPLETE | ✓ Approved: all rows retained, no dedup |
| 3 | Brand Counter Classification | COMPLETE | ✓ Approved: BA Availability flag; Page 5 shows coverage |
| 4 | State-to-City Mapping | COMPLETE | ✓ Approved: zone-only approach, no state rollups |
| 5 | Profitability & Cost Structure | Pending | Blocks P&L, CM2, Margin %, BA profitability |
| 6 | Chain Master Canonicalization | Pending | Awaiting canonical names approval (Vmm/VMM, etc.) |

---

## Page 4: Interim Offtake View: MRP, NSV & Qty

**Purpose:** Multi-basis view with MRP and NSV confirmed; shows trends and contribution; profitability measures still blocked

**Title & Watermark (Top):**
```
Interim Offtake View: MRP, NSV & Qty (v3: NSV Confirmed Lakhs)
Converted NSV from Lakhs to ₹ Crore | MRP in actual rupees | June'26 Partial
```

**Layout:** Watermark + KPI section + charts

### Watermark Text Box

Color: Amber background (#FFF7E6), dark text

Text:
```
Interim view. NSV confirmed at source (Lakhs); converted to ₹ Crore (÷100) for display alongside MRP (÷10,000,000 for Cr).
MRP and NSV can now be compared on equal footing (both in ₹ Crore).
All profitability, margin %, and CM2 measures remain blocked until cost sources are confirmed.
June'26 data is PARTIAL (78,111 rows; some accounts pending).
```

### KPI Cards

| Card | Measure | Format | Notes |
|------|---------|--------|-------|
| Total Offtake (MRP) | [MRP Sales Value Cr] | ₹X.XX Cr | Verified, rupee basis |
| Total Offtake (NSV) | [NSV Cr] | ₹X.XX Cr | Converted from Lakhs; now confirmed |
| Total Qty | [Sales Qty] | #,##0 Cr Qty | Units |
| Avg MRP/Month | [Avg MRP Per Month Cr] | ₹X.XX Cr | Average across months |
| MRP vs NSV Ratio | [MRP to NSV Ratio] | X.XX | Relationship indicator |
| Jun'26 MRP | CALCULATE([MRP Sales Value Cr], Dim_Month[Is_June26_Partial]=TRUE) | ₹X.XX Cr | Partial month warning |

### Charts (2-column Grid)

| Position | Chart Type | Title | Measures | Dimensions | Notes |
|----------|-----------|-------|----------|-----------|-------|
| Row 1, Col 1 | Column | MRP by Chain | [MRP Sales Value] | Chain (top 10 + Other) | MRP Desc; June'26 visibly marked |
| Row 1, Col 2 | Column | NSV by Zone | [NSV Cr] | Zone | NSV Desc (NSV now active) |
| Row 2, Col 1 | Line | MRP Trend (Month) | [MRP Sales Value] | Dim_Month[Month] | Mark June'26 differently; add MoM absolute change annotation |
| Row 2, Col 2 | Line | NSV Trend (Month) | [NSV Cr] | Dim_Month[Month] | NSV MoM comparison (NSV now active) |
| Row 3, Col 1 | Clustered | MRP & NSV Contribution % | [MRP Contribution %], [NSV Contribution %] | Category (top 10 + Other) | Dual-basis comparison |
| Row 3, Col 2 | Clustered | MRP MoM vs NSV MoM Change | [MRP MoM Abs Change Cr], [NSV MoM Abs Change Cr] | Dim_Month[Month] | Dual-metric trend (NSV now active) |

### Page-Level Slicers

- FY
- Month (exclude June'26 or mark as partial)
- Chain (raw names, variants included)
- Zone
- Category

### Page Notes

- Add conditional text box: IF [Has June26 Partial] THEN "⚠ June'26 is selected. Data from this month is PARTIAL."
- Add info box: "MRP and NSV confirmed and active. Profitability, CM2, margin %, and BA profitability measures remain BLOCKED pending cost sources. Use MRP & NSV basis for interim analysis only."
- Do NOT include slicers or measures for:
  - Margin %
  - Profitability / CM2
  - BA metrics
  - State
  - (NSV is now ACTIVE on this page)

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
Interim MRP & NSV View (v3: NSV Confirmed Lakhs) | June'26 Partial
Safe Blocks Build | claude/safe-powerbi-dashboard-rulings
NSV Cr = Lakhs ÷ 100 | MRP Cr = Rupees ÷ 10,000,000 | Cost sources pending
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
Reliance BA Availability Coverage
Brand Counter represents places/accounts where our BA is available.
⚠ Coverage view only. BA profitability is blocked until BA cost structure and NSV unit are confirmed.
```

**Layout:** KPI section + charts + detail view

### Watermark Text Box

Color: Amber background (#FFF7E6), dark text

Text:
```
BA Availability View Only
This page shows Reliance Brand Counter coverage (BA Available = Yes).
It does NOT include BA profitability, BA cost, or BA productivity metrics.
These remain blocked until: (1) BA Headcount is provided, (2) NSV unit is confirmed.
```

### KPI Cards

| Card | Measure | Format | Notes |
|------|---------|--------|-------|
| BA Available Row Count | [BA Available Row Count] | #,##0 | Transactions where Brand Counter = Yes |
| BA Available MRP | [BA Available MRP Sales Value Cr] | ₹X.XX Cr | MRP for BA-available rows |
| BA Available NSV | [BA Available NSV Cr] | ₹X.XX Cr | NSV for BA-available rows (NSV now active) |
| BA Availability Mix % (MRP) | [BA Availability Mix %] | X.X% | BA rows as % of total MRP |
| BA Availability Mix % (NSV) | [BA Availability Mix % NSV] | X.X% | BA rows as % of total NSV (NSV now active) |
| Total MRP (All) | [MRP Sales Value Cr] | ₹X.XX Cr | For comparison |

### Charts (2-column Grid)

| Position | Chart Type | Title | Measures | Dimensions | Notes |
|----------|-----------|-------|----------|-----------|-------|
| Row 1, Col 1 | Column | BA Available MRP by Zone | [BA Available MRP Sales Value] | Zone | MRP Desc; Reliance zones only |
| Row 1, Col 2 | Column | BA Available NSV by Category | [BA Available NSV Cr] | Category | NSV Desc (NSV now active) |
| Row 2, Col 1 | Line | BA Available MRP Trend (Month) | [BA Available MRP Sales Value] | Dim_Month[Month] | Show Reliance BA MRP trend over time |
| Row 2, Col 2 | Line | BA Available NSV Trend (Month) | [BA Available NSV Cr] | Dim_Month[Month] | Show Reliance BA NSV trend (NSV now active) |

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

- Add text box: "Reliance BA Availability shows Brand Counter coverage. Business decision APPROVED: Brand Counter represents BA availability, not a chain for profit-center allocation."
- Add conditional text: IF no Brand Counter rows selected THEN "No Brand Counter rows in current filter."
- Add note: "BA profitability metrics are blocked. Use Overview or Data Explorer pages for full chain analysis."

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

