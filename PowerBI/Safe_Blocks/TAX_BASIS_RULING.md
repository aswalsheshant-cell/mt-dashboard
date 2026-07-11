# Tax-Basis Ruling — NSV (Excl. Tax) vs MRP (Incl. Tax)

**Branch:** claude/safe-powerbi-dashboard-rulings  
**Date:** 2026-07-11  
**Version:** v3.1 (Tax-Basis Clarification)  
**Previous Version:** v3 (NSV Lakhs confirmed)

---

## Executive Summary

**NSV and MRP operate on different tax bases:**
- **NSV** = Net Sales Value **excluding tax** (source unit: Lakhs)
- **MRP Sales Value** = Gross consumer value **including tax** (rupees basis)

This affects:
1. How comparisons are presented (QC/realization only, with tax-basis warning)
2. How profitability/CM2 is calculated (requires cost structure + tax handling)
3. How pages are labeled and watermarked
4. How QC validation is structured

**Impact:** NSV and MRP are NOT directly comparable as performance metrics without tax-basis context. Profitability measures remain blocked pending cost sources and CM2 formula confirmation.

---

## Tax-Basis Definitions

### NSV (Net Sales Value) — WITHOUT TAX

| Attribute | Value |
|-----------|-------|
| **Tax Treatment** | Excludes all taxes (GST, VAT, etc.) |
| **Source Unit** | Lakhs (confirmed) |
| **Conversion to Crore** | NSV Cr = Source NSV Lacs ÷ 100 |
| **Conversion to Rupees** | NSV Actual = Source NSV Lacs × 100,000 |
| **Labeling** | "NSV ₹ Cr, excluding tax" or "Net Sales Value (excl. tax)" |
| **Use Case** | Net sales reporting, offtake analysis, scheme/margin view |
| **Valid for Profitability?** | Only if cost/COGS/CM2 formula excludes tax components |

### MRP Sales Value — WITH TAX

| Attribute | Value |
|-----------|-------|
| **Tax Treatment** | Includes all taxes (GST, VAT, etc.) |
| **Source Unit** | Actual rupees (verified basis) |
| **Conversion to Crore** | MRP Cr = MRP Sales Value ÷ 10,000,000 |
| **Labeling** | "MRP Sales Value ₹ Cr, including tax" or "MRP (incl. tax)" |
| **Use Case** | Gross consumer value, MRP basis reporting, market view |
| **Valid for Profitability?** | Only if cost/COGS/CM2 formula includes tax components |

### Tax-Basis Difference

**MRP vs NSV includes:**
1. **Tax component** (GST/VAT/excise)
2. **Trade scheme / discount** (if applied on MRP)
3. **Margin structure** (distributor, retailer margins)
4. **Other deductions** (visibility, logistics, scheme allowance, etc.)

**Formula:**
```
MRP Sales Value (incl. tax) 
= NSV excluding tax 
  + Tax (GST/VAT/Excise)
  + Trade Scheme/Discount deductions
  + Margin structure components
  + Other deductions
```

---

## Updated Conversion Logic

### NSV Conversions (Unchanged from v3)

| From | To | Formula | Example |
|------|----|---------| --------|
| Source NSV Lacs | NSV Actual Value (₹, excl. tax) | Lacs × 100,000 | 10 Lacs → ₹10,00,000 |
| Source NSV Lacs | NSV Cr (₹ Crore, excl. tax) | Lacs ÷ 100 | 10 Lacs → ₹0.10 Cr (excl. tax) |

### MRP Conversions (Updated Labeling)

| From | To | Formula | Example | Tax Treatment |
|------|----|---------| --------|---|
| MRP Sales Value (₹) | MRP Cr (₹ Crore, incl. tax) | Rupees ÷ 10,000,000 | ₹1,00,00,000 → ₹1.00 Cr | Including tax |

### Qty Display (Unchanged)

| From | To | Formula | Example |
|------|----|---------| --------|
| Sales Qty (units) | Sales Qty Cr | Units ÷ 10,000,000 | 10,000,000 units → 1 Cr Qty |

---

## Power Query Changes

### Column Naming & Labeling

**NSV Columns (tax-exclusive):**
```
Source_NSV_Lacs          = Original NSV column (unit: Lakhs, excl. tax)
NSV_Actual_Value         = Source_NSV_Lacs × 100,000 (rupees, excl. tax)
NSV_Cr                   = Source_NSV_Lacs ÷ 100 (Crores, excl. tax)
Is_Negative_NSV          = Source_NSV_Lacs < 0 (flag for QC)
```

**MRP Columns (tax-inclusive):**
```
MRP_Sales_Value          = Original column (actual rupees, INCL. TAX)
MRP_Sales_Value_Cr       = MRP_Sales_Value ÷ 10,000,000 (Crores, INCL. TAX)
Is_Negative_MRP          = MRP_Sales_Value < 0 (flag for returns/credits)
```

**Tax-Basis Flag (New):**
```
NSV_Tax_Basis            = "Excl. Tax" (constant for all rows)
MRP_Tax_Basis            = "Incl. Tax" (constant for all rows)
```

---

## DAX Measures (Updated with Tax-Basis Labels)

### Base Measures (Tax-Basis Aware)

| Measure | Formula | Unit | Tax Basis |
|---------|---------|------|-----------|
| [Source NSV Lacs] | SUM(Source_NSV_Lacs) | Lakhs | Excl. Tax |
| [NSV Actual Value] | SUM(NSV_Actual_Value) | ₹ (rupees) | Excl. Tax |
| [NSV Cr] | [Source NSV Lacs] ÷ 100 | ₹ Cr | Excl. Tax |
| [MRP Sales Value] | SUM(MRP_Sales_Value) | ₹ (rupees) | **Incl. Tax** |
| [MRP Sales Value Cr] | [MRP Sales Value] ÷ 10,000,000 | ₹ Cr | **Incl. Tax** |
| [Sales Qty] | SUM(Sales_Qty) | Units | N/A (quantity) |
| [Sales Qty Cr] | [Sales Qty] ÷ 10,000,000 | Cr Units | N/A |

### Tax-Aware Ratio Measures

| Measure | Formula | Notes | Labeling |
|---------|---------|-------|----------|
| [MRP to NSV Ratio] | [MRP Sales Value Cr] ÷ [NSV Cr] | Realization indicator only | "MRP to NSV Realization (incl./excl. tax)" |
| [MRP to NSV Tax Impact] | [MRP Sales Value Cr] - [NSV Cr] | Difference includes tax, schemes, margins | "Difference incl. tax & margins" |

**Note:** These ratios are for QC/realization only. Do NOT present as performance variance without tax-basis warning.

### Contribution Measures (Tax-Basis Maintained)

| Measure | Formula | Tax Basis |
|---------|---------|-----------|
| [NSV Contribution %] | [NSV Cr] ÷ total (NSV Cr) × 100 | Based on NSV excl. tax |
| [MRP Contribution %] | [MRP Sales Value Cr] ÷ total (MRP Cr) × 100 | Based on MRP incl. tax |
| [Qty Contribution %] | [Sales Qty] ÷ total (Qty) × 100 | Quantity basis |

**Note:** Contributions are separate metrics (one NSV-based, one MRP-based) — do NOT mix or directly compare.

---

## Report Page Updates

### All Pages: Labeling Rules

**For NSV cards/charts:**
```
"NSV ₹ Cr, excluding tax"
OR
"Net Sales Value (excl. tax)"
```

**For MRP cards/charts:**
```
"MRP Sales Value ₹ Cr, including tax"
OR
"Gross Consumer Value (incl. tax)"
```

**For comparisons:**
```
"MRP vs NSV shown for QC/realization only.
MRP is tax-inclusive; NSV is tax-exclusive.
Difference includes tax, trade scheme, margin structure, and other deductions."
```

### Page-Specific Updates

#### Page 1: Data Explorer

**KPI Cards:**
- NSV ₹ Cr, excluding tax (new labeling)
- MRP Sales Value ₹ Cr, including tax (new labeling)

**Charts:**
- NSV by Zone, excl. tax (renamed, clarified)
- NSV Trend by Month, excl. tax (renamed)
- MRP vs NSV shown for QC/realization (note added)

#### Page 2: Overview

**KPI Cards:**
- Total NSV ₹ Cr, excluding tax
- Total MRP Sales Value ₹ Cr, including tax
- **MRP to NSV Realization Ratio** (QC indicator only; not performance variance)

**Charts:**
- MRP vs NSV Trend — **NEW NOTE:** "Realization indicator (tax basis differs)"

#### Page 4: Interim Offtake View

**Watermark (updated):**
```
"NSV excludes tax. MRP Sales Value includes tax.
Difference includes tax, trade schemes, margins, and other deductions.
Use separately for net/gross view respectively. Do not compare as performance variance."
```

**KPI Cards:**
- Total Offtake (NSV) ₹ Cr, excluding tax
- Total Offtake (MRP) ₹ Cr, including tax
- **MRP to NSV Realization Ratio** (for QC only)

#### Page 5: BA Availability View

**KPI Cards:**
- BA Available NSV ₹ Cr, excluding tax
- BA Available MRP ₹ Cr, including tax

---

## QC & Reconciliation Page — Tax-Basis Checks

### New Validation Columns

| Column | Formula | Purpose |
|--------|---------|---------|
| Monthly NSV excl. Tax | SUM(NSV_Cr) by Month | Track NSV excluding tax |
| Monthly MRP incl. Tax | SUM(MRP_Cr) by Month | Track MRP including tax |
| Realization Ratio | MRP Cr ÷ NSV Cr | QC indicator (not performance) |
| Negative NSV Count | COUNT(Is_Negative_NSV=TRUE) | Returns/credits validation |
| Negative MRP Count | COUNT(Is_Negative_MRP=TRUE) | Returns/credits validation |

### New QC Checks

**Add to QC & Reconciliation page:**

1. **Tax-Basis Consistency Check:**
   - [ ] NSV is consistently labeled "excluding tax" on all pages
   - [ ] MRP is consistently labeled "including tax" on all pages
   - [ ] Comparison notes mention tax-basis difference

2. **Realization Ratio Validation:**
   - [ ] MRP to NSV ratio calculated (for QC only)
   - [ ] Ratio flagged as "QC/realization indicator, not performance variance"
   - [ ] Ratio aligns with known tax/margin structure

3. **Negative Value Validation:**
   - [ ] Negative NSV count tracked (returns/credits)
   - [ ] Negative MRP count tracked (returns/credits)
   - [ ] Both counted separately

4. **Tax Impact Note:**
   - Text box: "MRP vs NSV difference includes tax (GST/VAT), trade scheme, margin structure, and other deductions."

---

## Profitability & CM2 Readiness (Tax-Basis Impact)

### Current Blocker Status

**P&L / CM2 / Profitability remain BLOCKED** because:

1. **NSV is tax-exclusive** — requires cost/COGS data that is also tax-exclusive
2. **MRP is tax-inclusive** — requires cost/COGS data that is also tax-inclusive
3. **No single CM2 formula can use mixed tax bases**

### Required Before CM2 Implementation

Finance must provide:

1. **CM2 Formula (exact):**
   - Numerator: NSV excl. tax? Or MRP incl. tax? (Clarify)
   - Tax handling: How is GST/VAT included/excluded?
   - Components: COGS, discount, scheme, margin, visibility, BA cost, etc.

2. **Cost Data (tax-basis specified):**
   - COGS per unit / category (excl. tax? incl. tax?)
   - GST amount (if not already in NSV/MRP)
   - Trade scheme deduction amount
   - Visibility/activation spend
   - BA cost per unit / category
   - Fixed overhead allocation

3. **Tax Handling Rules:**
   - Is GST included in NSV or MRP or both or neither?
   - How are trade schemes handled (as deduction from MRP? or separate)?
   - How is margin structure handled (distributor %, retailer %, etc.)?

### Profitability Calculation Approach

**Once cost data is provided:**

```
IF NSV-based CM2:
  CM2 (excl. tax) = NSV Cr - COGS (excl. tax) - Direct costs (excl. tax)
  
ELSE IF MRP-based CM2:
  CM2 (incl. tax) = MRP Cr - COGS (incl. tax) - Direct costs (incl. tax) - Tax component
  
ELSE IF Hybrid CM2:
  CM2 = NSV Cr - Tax impact - COGS - All deductions
  (Requires exact formula + tax handling rules)
```

**For now:** Keep P&L / CM2 / Profitability blocked. Collect cost structure from finance.

---

## Watermarks & Documentation

### Updated Watermark (All Pages)

```
"NSV excludes tax. MRP Sales Value includes tax.
Profitability/CM2 requires cost confirmation.
Use NSV for net sales view. Use MRP for consumer value view.
Comparison shown for QC/realization only (tax basis differs)."
```

### Page 4 (Interim Offtake View) — Specific Note

```
"This interim view shows:
- NSV ₹ Cr, EXCLUDING all taxes
- MRP Sales Value ₹ Cr, INCLUDING all taxes
- Profitability / CM2 measures remain blocked (cost structure pending)

Use these separately:
  - NSV for net margin / scheme view
  - MRP for gross consumer value view
  - MRP to NSV for realization/tax-basis QC only
  
Do NOT present MRP vs NSV as direct performance variance without tax-basis context."
```

---

## Validation Checklist (Tax-Basis Audit)

### Before Implementation

- [ ] NSV labeled "excluding tax" on ALL pages (5 pages)
- [ ] MRP labeled "including tax" on ALL pages (5 pages)
- [ ] Comparison notes mention tax-basis difference
- [ ] MRP to NSV ratio shown only with "QC/realization only" note
- [ ] No direct MRP vs NSV variance presented without tax-basis warning
- [ ] NSV Cr = Source NSV Lacs ÷ 100 (verified)
- [ ] MRP Cr = MRP Sales Value ÷ 10,000,000 (verified)
- [ ] Profitability / CM2 remains blocked
- [ ] QC page includes tax-basis validation checks
- [ ] Watermarks reflect tax-basis ruling on all 5 pages

### After Implementation

- [ ] User sees clear "excl. tax" / "incl. tax" labels
- [ ] No confusion between NSV and MRP as comparable metrics
- [ ] Comparison sections are marked "QC/realization only"
- [ ] Business users understand tax-basis difference
- [ ] QC monitors negative NSV and MRP separately
- [ ] Finance has been asked for CM2 formula + cost structure

---

## Remaining Inputs Needed for Full Profitability Implementation

| Input | Status | Blocker? | Notes |
|-------|--------|----------|-------|
| NSV unit (Lakhs) | ✓ CONFIRMED (v3) | No | Done |
| NSV tax basis (excl.) | ✓ CONFIRMED (v3.1) | No | Done |
| MRP tax basis (incl.) | ✓ CONFIRMED (v3.1) | No | Done |
| **CM2 formula (exact)** | Pending | **YES** | Finance to provide |
| **COGS / cost data** | Pending | **YES** | Finance + Ops |
| **Tax handling rules** | Pending | **YES** | Finance to clarify |
| **BA cost structure** | Pending | **YES** | HR/Finance |
| **Trade scheme deduction** | Pending | **YES** | Commercial/Finance |
| **Visibility/activation spend** | Pending | No* | May be in cost data |
| **Fixed overhead allocation** | Pending | No* | May be in cost data |

**\*Not critical for immediate implementation; can be added to CM2 later once base formula confirmed.**

---

## Summary: What Changes, What Stays

### CHANGES (v3 → v3.1)

✓ NSV labeled "excluding tax" everywhere  
✓ MRP labeled "including tax" everywhere  
✓ MRP vs NSV comparisons marked "QC/realization only"  
✓ Tax-basis warning added to watermarks  
✓ QC page includes tax-basis validation checks  

### STAYS THE SAME

✓ NSV Cr = Source NSV Lacs ÷ 100 (unchanged)  
✓ MRP Cr = MRP Sales Value ÷ 10,000,000 (unchanged)  
✓ NSV measures remain ACTIVE (unblocked)  
✓ Profitability / CM2 remains BLOCKED (pending cost sources)  
✓ June'26 marked Partial (unchanged)  
✓ More Retail retained (unchanged)  
✓ State-level reporting excluded (unchanged)  
✓ BA Availability coverage on Page 5 (unchanged)  

---

**Status:** Tax-basis ruling documented. Ready for Power BI Desktop implementation with tax-aware labeling.

