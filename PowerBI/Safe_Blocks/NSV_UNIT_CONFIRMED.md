# NSV Unit Confirmed (v3 Update)

**Branch:** claude/safe-powerbi-dashboard-rulings  
**Date:** 2026-07-11  
**Version:** 3  
**Previous Version:** v2 (NSV blocked)

---

## Executive Summary

NSV (Net Sales Value) unit has been confirmed as **Lakhs** by business. This unblocks all NSV-based measures, allowing MRP and NSV to be shown side-by-side in Crore format for comparison.

**Key Changes:**
- NSV measures are now ACTIVE (not blocked)
- NSV Cr = Source NSV Lacs ÷ 100
- MRP Cr = MRP actual rupees ÷ 10,000,000
- Both can now be displayed in ₹ Cr for clean comparison

---

## Conversion Logic

### NSV Conversion

| From | To | Formula | Example |
|------|----|---------| --------|
| Source NSV Lacs | NSV Actual Value (₹) | Lacs × 100,000 | 10 Lacs → ₹10,00,000 |
| Source NSV Lacs | NSV Cr (₹ Crore) | Lacs ÷ 100 | 10 Lacs → ₹0.10 Cr |

### MRP Conversion

| From | To | Formula | Example |
|------|----|---------| --------|
| MRP Sales Value (₹) | MRP Cr (₹ Crore) | Rupees ÷ 10,000,000 | ₹1,00,00,000 → ₹1.00 Cr |

### Qty Display

| From | To | Formula | Example |
|------|----|---------| --------|
| Sales Qty (units) | Sales Qty Cr | Units ÷ 10,000,000 | 10,000,000 units → 1 Cr Qty |

---

## Power Query Changes

### New Columns Added

```
Source_NSV_Lacs         = Original NSV column (renamed; confirmed unit = Lakhs)
NSV_Actual_Value        = Source_NSV_Lacs × 100,000 (convert to rupees)
NSV_Cr                  = Source_NSV_Lacs ÷ 100 (convert to Crores)
MRP_Sales_Value_Cr      = MRP_Sales_Value ÷ 10,000,000 (convert to Crores)
Sales_Qty_Cr            = Sales_Qty ÷ 10,000,000 (convert to Crores for display)
Is_Negative_NSV         = Source_NSV_Lacs < 0 (flag for QC)
```

### Column Reorder

```
Site_Code, Site_Name, Chain_Name, Zone, Category, PPT_Category, Format, Classification,
Month, FY, Month_Sort, Month_Num, Calendar_Year, Is_Month_Partial, Is_June26_Partial,
Sales_Qty, Sales_Qty_Cr, MRP_Sales_Value, MRP_Sales_Value_Cr,
Source_NSV_Lacs, NSV_Actual_Value, NSV_Cr,
Safe_Value_Basis, Is_Safe_For_Reporting, Is_Negative_Return, Is_Negative_NSV, BA_Available
```

---

## DAX Measures (New/Updated)

### Base Measures

| Measure | Formula | Unit |
|---------|---------|------|
| [MRP Sales Value] | SUM(MRP_Sales_Value) | ₹ (rupees) |
| [MRP Sales Value Cr] | [MRP Sales Value] ÷ 10,000,000 | ₹ Cr |
| [Source NSV Lacs] | SUM(Source_NSV_Lacs) | Lakhs |
| [NSV Actual Value] | SUM(NSV_Actual_Value) | ₹ (rupees) |
| [NSV Cr] | [Source NSV Lacs] ÷ 100 | ₹ Cr |
| [Sales Qty] | SUM(Sales_Qty) | Units |
| [Sales Qty Cr] | [Sales Qty] ÷ 10,000,000 | Cr Units |

### Contribution Measures

| Measure | Formula | Notes |
|---------|---------|-------|
| [MRP Contribution %] | [MRP Sales Value Cr] ÷ total (MRP Cr) × 100 | MRP-basis contribution |
| [NSV Contribution %] | [NSV Cr] ÷ total (NSV Cr) × 100 | NSV-basis contribution |
| [Qty Contribution %] | [Sales Qty] ÷ total (Qty) × 100 | Qty-basis contribution |
| [MRP Share of Total] | [MRP Sales Value Cr] ÷ grand total × 100 | Ignores filters |
| [NSV Share of Total] | [NSV Cr] ÷ grand total × 100 | Ignores filters |

### Trend Measures

| Measure | Notes |
|---------|-------|
| [Previous Month MRP Cr] | MRP for previous month |
| [MRP MoM Abs Change Cr] | Current vs previous MRP (Crore) |
| [MRP MoM % Change] | % growth month-over-month |
| [Previous Month NSV Cr] | NSV for previous month (Crore) |
| [NSV MoM Abs Change Cr] | Current vs previous NSV (Crore) |
| [NSV MoM % Change] | % growth month-over-month |
| [Previous Month Qty] | Qty for previous month |
| [Qty MoM Abs Change] | Current vs previous Qty |
| [Qty MoM % Change] | % growth month-over-month |

### BA Availability Measures (Updated with NSV)

| Measure | Notes |
|---------|-------|
| [BA Available MRP Sales Value Cr] | MRP for Brand Counter rows |
| [BA Available NSV Cr] | NSV for Brand Counter rows |
| [BA Available Sales Qty] | Qty for Brand Counter rows |
| [BA Availability Mix % MRP] | BA rows as % of total MRP |
| [BA Availability Mix % NSV] | BA rows as % of total NSV |
| [BA Availability Mix % Qty] | BA rows as % of total Qty |

### QC & Validation Measures

| Measure | Notes |
|---------|-------|
| [Negative MRP Return Rows] | Count of MRP < 0 (valid returns) |
| [Negative NSV Return Rows] | Count of NSV < 0 (valid returns) |
| [June26 Partial Row Count] | Row count for June'26 only |
| [Distinct Chains] | Count of unique chains |
| [Distinct Zones] | Count of unique zones |
| [Distinct Categories] | Count of unique categories |
| [MRP to NSV Ratio] | [MRP Sales Value Cr] ÷ [NSV Cr] |

---

## Report Pages Updated

### Page 1: Data Explorer (Updated)

**New KPI Cards:**
- NSV Cr (₹ Crore)

**New Charts:**
- NSV by Chain / Zone / Category
- NSV Trend by Month
- MRP vs NSV comparison (optional)

### Page 2: Overview (Updated)

**New KPI Cards:**
- Total NSV Cr
- MRP vs NSV Ratio

**New Charts:**
- NSV Trend by Month/FY
- NSV vs MRP Trend (optional)

### Page 3: QC & Reconciliation (Updated)

**New Columns:**
- Monthly Source NSV Lacs
- Monthly NSV Cr
- Negative NSV Count (for QC)

### Page 4: Interim Offtake View (Renamed & Updated)

**Previous Name:** Interim Offtake P&L  
**New Name:** Interim Offtake View: MRP, NSV & Qty

**Updated Content:**
- MRP Sales Value Cr (kept)
- NSV Cr (new, active)
- Sales Qty (kept)
- MRP Contribution %
- NSV Contribution %
- Qty Contribution %
- MRP vs NSV MoM Change (new)
- June'26 warning (kept)

**Updated Watermark:**
"Interim view. NSV converted from source Lakhs to ₹ Crore. June'26 Partial. Not for final profitability review (cost structure pending)."

### Page 5: BA Availability View (Updated)

**New KPI Cards:**
- BA Available NSV Cr

**New Charts:**
- BA Available NSV by Zone/Category
- BA Availability Mix % (NSV basis)

---

## QC & Validation Changes

### Blocked Measures List (Updated)

**Removed from Blocked (Now Active):**
- ~~NSV (unit unvalidated)~~ → ✓ [Source NSV Lacs], [NSV Cr] (ACTIVE)
- ~~NSV Cr / Lacs / Label~~ → ✓ ALL NSV measures (ACTIVE)
- ~~MoM/YoY % (NSV basis)~~ → ✓ [NSV MoM Abs Change Cr], [NSV MoM % Change] (ACTIVE)
- ~~Contribution % (NSV-driven)~~ → ✓ [NSV Contribution %] (ACTIVE)
- ~~Rank by Sales (NSV-driven)~~ → Available via NSV-based charts (ACTIVE)

**Still Blocked:**
- CM2, Margin %, Profitability (requires cost sources)
- BA Profitability (requires BA Headcount + cost)
- Primary vs Offtake Gap (requires Primary NSV validation)
- State-level rollups (business decision: zone-only)
- Chain variant consolidation (pending canonicalization)

### Pending Decisions (Updated)

| Item | v2 Status | v3 Status | Impact |
|------|-----------|-----------|--------|
| NSV Unit | Pending | ✓ COMPLETE | Unblocks all NSV measures |
| Profitability & Cost | Pending | Pending | Blocks P&L, CM2, margin % |
| More Retail | ✓ COMPLETE | ✓ COMPLETE | All rows retained |
| Brand Counter | ✓ COMPLETE | ✓ COMPLETE | BA Availability flag |
| State Mapping | ✓ COMPLETE | ✓ COMPLETE | Zone-only approach |
| Chain Canonicalization | Pending | Pending | Blocks variant consolidation |

---

## Watermark Updates

### Old (v2)

"⚠ NSV unit pending | Interim MRP basis only"

### New (v3)

"NSV converted from source Lakhs to ₹ Crores (÷100). MRP in actual rupees (÷10,000,000 for Cr display)."

---

## Validation Checklist (v3)

✓ NSV source unit confirmed as Lakhs  
✓ NSV Cr = Source NSV Lacs ÷ 100  
✓ NSV Actual Value = Source NSV Lacs × 100,000  
✓ MRP Sales Value remains actual rupees  
✓ MRP Sales Value Cr = MRP Sales Value ÷ 10,000,000  
✓ No "NSV unit pending" wording remains  
✓ NSV measures are ACTIVE in all pages  
✓ NSV trends show MoM changes  
✓ No profitability/CM2/margin % exists  
✓ More Retail retained as valid  
✓ Brand Counter = BA Availability only  
✓ State reporting remains excluded  
✓ June'26 marked Partial  
✓ All 5 pages include NSV metrics  

---

## Build Time Impact (v3)

- **v1:** 2–3 hours (4 pages, NSV blocked)
- **v2:** 2.5–3.5 hours (5 pages, NSV blocked)
- **v3:** 2.5–3.5 hours (5 pages, NSV ACTIVE; no new pages)

**Time Change:** No additional time needed (NSV integration into existing page structure).

---

## Next Steps

1. **Build Power BI file** using updated `Build_In_PowerBI_Desktop_Guide.md`
2. **Add NSV charts** to Pages 1–2, 4–5 as per `PowerBI_Report_Page_Spec.md`
3. **Validate NSV values** using `QC_Validation_Checklist.md`
4. **Test MRP vs NSV comparison** charts
5. **Deploy** and share with business

---

## Blockers Remaining (Post-NSV Confirmation)

1. **Profitability & Cost Sources** (blocks P&L, CM2, margin %)
2. **BA Headcount + Cost Structure** (blocks BA profitability)
3. **Chain Canonicalization** (blocks variant consolidation; optional)
4. **Primary NSV Validation** (blocks gap analysis; optional)

---

**Status:** NSV unit confirmed. All NSV measures now ACTIVE. Ready for Power BI Desktop build with NSV analytics included.

