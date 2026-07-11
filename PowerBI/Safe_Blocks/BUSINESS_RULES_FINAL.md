# Business Rules — Final (Phase 2)

**Dashboard:** MT Offtake Dashboard  
**Status:** Production-ready (Phase 2 build)  
**Commit:** e19c467  
**Date:** 2026-07-11

---

## 1. NSV (NET SALES VALUE) RULES

### 1.1 NSV Source Unit
- **Source unit:** Lakhs (₹ 100,000 per lakh)
- **Source field:** `Fact_Offtake_Safe[Source_NSV_Lacs]`
- **Example:** 1500 Lakhs = ₹ 1.5 Cr

### 1.2 NSV Tax Basis
- **NSV is EXCLUDING tax** (before GST, VAT, other taxes)
- **ALWAYS label NSV as:** "NSV ₹ Cr, excluding tax" or "NSV (Excl Tax)"
- **Example:** If source NSV = 1500 Lakh, MRP = 1750 Lakh, then NSV excl tax is lower

### 1.3 NSV Unit Conversions (in Power BI)
- **NSV in Crores:** Source_NSV_Lacs ÷ 100  
  Example: 1500 Lacs ÷ 100 = 15 Cr
- **NSV in Rupees:** Source_NSV_Lacs × 100,000  
  Example: 1500 Lacs × 100,000 = ₹ 15,00,00,000

### 1.4 NSV Reporting
- **All visuals showing NSV:** Use [Total NSV Cr] or similar measures
- **Label:** Always include "(Excl Tax)"
- **Use:** Sales analysis, growth %, volume trends, chain/zone/category breakdown
- **DO NOT:** Use NSV alone for profitability without cost context

### 1.5 NSV Data Quality
- **4.21M rows** covering Apr'24 to Jun'26
- **27 months** of data (Apr-24, May-24, ..., Jun-26)
- **By dimension:** By chain, zone, category, format, brand, SKU

---

## 2. MRP (MAXIMUM RETAIL PRICE) RULES

### 2.1 MRP Source Unit
- **Source unit:** Actual rupees (₹)
- **Source field:** `Fact_Offtake_Safe[MRP_Sales_Value]`
- **Example:** 150,050,000 rupees = ₹ 1.5005 Cr

### 2.2 MRP Tax Basis
- **MRP is INCLUDING tax** (includes GST, VAT, other applicable taxes)
- **ALWAYS label MRP as:** "MRP ₹ Cr, including tax" or "MRP (Incl Tax)"
- **Example:** If NSV = 1500 Lakh (excl tax), MRP will be higher (incl tax)

### 2.3 MRP Unit Conversions (in Power BI)
- **MRP in Crores:** MRP_Sales_Value ÷ 10,000,000  
  Example: 150,050,000 ÷ 10,000,000 = 15.005 Cr
- **MRP as-is:** MRP_Sales_Value (in rupees, no conversion needed)

### 2.4 MRP Reporting
- **All visuals showing MRP:** Use [Total MRP Sales Value Cr] or similar
- **Label:** Always include "(Incl Tax)"
- **Use:** QC/realization comparison only (see 2.5 below)
- **DO NOT:** Use MRP alone for profitability without cost context

### 2.5 MRP vs NSV Comparison Rule (CRITICAL)
- **NSV (Excl Tax) and MRP (Incl Tax) are NOT directly comparable**
- **Tax basis difference:** NSV excludes tax; MRP includes tax
- **When both shown together:**
  - ✅ **ALLOWED:** For QC/realization reference (checking data consistency)
  - ✅ **ALLOWED:** For realization analysis (actual sales realized vs. target)
  - ❌ **FORBIDDEN:** For variance analysis (assuming variance = performance issue)
  - ❌ **FORBIDDEN:** For profitability calculation (directly subtracting one from the other)
- **Every page showing NSV + MRP together MUST include warning:**
  ```
  ⚠️ NSV (Excl Tax) vs MRP (Incl Tax): Shown for QC/realization reference only.
     Do NOT use for direct variance analysis — different tax bases.
  ```

---

## 3. QUANTITY (QTY) RULES

### 3.1 Qty Source Unit
- **Source unit:** Units (individual products sold)
- **Source field:** `Fact_Offtake_Safe[Sales_Qty]`
- **Displayed unit:** Millions (M) = Qty ÷ 1,000,000

### 3.2 Qty Reporting
- **All Qty visuals:** Use [Total Sales Qty M] (shows in millions)
- **Label:** "Qty Millions" or "Qty (M units)"
- **Use:** Volume trends, per-unit pricing (NSV/Qty), growth analysis

---

## 4. MORE RETAIL DUPLICATE HANDLING

### 4.1 More Retail Status
- **13,661 duplicate rows** identified (More Retail brand appears multiple times)
- **Current status:** ✅ **RETAINED AS VALID** (not deduped)
- **Business reason:** More Retail appears to have legitimate multiple store/SKU records
- **Data impact:** These rows are included in all NSV, MRP, Qty totals

### 4.2 Handling in Power BI
- **NO deduplication** in Power Query (data loads as-is)
- **NO filters** to exclude More Retail
- **All measures** naturally include More Retail rows
- **QC flag:** On Page 10, documented as "More Retail Duplicates: 13,661 rows (retained)"

### 4.3 What This Means
- Total NSV includes More Retail rows (not reduced)
- More Retail chain ranking includes duplicates
- If analysis shows More Retail as top chain, it includes these 13,661 rows
- **No adjustment needed** — treat as valid source data

---

## 5. BRAND COUNTER = BA AVAILABILITY ONLY

### 5.1 BA Availability Definition
- **BA Available:** Stores/articles where Brand Ambassador was deployed
- **Non-BA Available:** Stores/articles without BA support
- **Flag field:** `Fact_Offtake_Safe[BA_Available]` (values: "Yes", "No")

### 5.2 Measures
- **[BA Available NSV Cr]:** NSV for rows where BA_Available = "Yes"
- **[Non_BA Available NSV Cr]:** NSV for rows where BA_Available = "No"
- **[BA Coverage Pct]:** (BA NSV / Total NSV) × 100

### 5.3 What This Does NOT Mean
- ❌ **NOT "BA profitability"** (no cost allocation or break-even)
- ❌ **NOT "BA impact"** (no pre/post comparison yet, pending BA deployment dates)
- ❌ **NOT "BA ROI"** (no payback or return calculation, pending Finance Q2)

### 5.4 What This DOES Mean
- ✅ **Sales coverage:** What % of stores/articles have BA support
- ✅ **BA reach:** Total sales in BA-supported stores vs. non-BA stores
- ✅ **Segmentation:** Ability to slice data by BA presence

### 5.5 How to Use
- **Page 7:** Compare BA vs Non-BA sales trends
- **Trend analysis:** Growth in BA-supported stores
- **Preparation for Finance Q2:** Data needed to calculate true BA impact once Q2 formula confirmed

---

## 6. STATE REPORTING STATUS

### 6.1 State Dimension Blocked
- **Status:** ❌ **EXCLUDED from all pages**
- **Reason:** Source data lacks reliable state mapping (city-to-state not validated)
- **Impact:** No state slicer, no state rollups, no state-level charts

### 6.2 Geographic Reporting
- **Active dimension:** Zone (P6 canonical zones)
- **Zones in use:** NORTH-1, NORTH-2, SOUTH-1, SOUTH-2, EAST-1, WEST-1, WEST-2, etc. (37 total)
- **All pages:** Zone-only analysis

### 6.3 Why No State Reporting
- Source data has City/State columns but mapping is incomplete/unreliable
- Publishing state-level rollups without validation could create misleading analysis
- **Once Operations provides validated City-State Master:** State dimension can be added

### 6.4 Verification Checklist
- ❌ NO State slicer on any page
- ❌ NO State column in any table
- ❌ NO State drill-down path
- ✅ Zone dimension only
- ✅ Zone slicers on all pages

---

## 7. JUNE'26 PARTIAL DATA HANDLING

### 7.1 June'26 Status
- **Partial data:** 78,111 rows (16 chains only out of 34)
- **Impact:** June'26 NSV, MRP, Qty are incomplete
- **Flag:** `Fact_Offtake_Safe[Is_June26_Partial]` = TRUE for all Jun-26 rows

### 7.2 Handling in Power BI
- **NO exclusion** (data included in all totals)
- **Watermark:** All pages show "⚠️ June'26 Partial: 78,111 rows (16 chains only)"
- **What users see:** KPIs include Jun-26, but they're warned it's partial
- **QC flag:** Page 10 shows [June26 Partial Row Count] ≈ 78,111

### 7.3 What This Means
- If user filters to Jun-26 only, they see ~16 chains (not 34)
- Jun-26 growth % may look artificially high (smaller subset)
- **Mitigation:** Warning visible to users

### 7.4 When Full June'26 Available
- Once Operations provides missing 18 chains' Jun-26 data:
  - Refresh Power Query
  - June'26 rows update in Fact table
  - All measures auto-recalculate
  - Remove partial watermark

---

## 8. PROFITABILITY & CM2 RULES (CRITICAL)

### 8.1 Current Status: PROVISIONAL ⚠️
- **All profitability measures:** Marked "[Measure Name] Provisional"
- **Visualization status:** Page 9 is readiness QC only (no active profitability visuals)
- **Page 7 CM2 measures:** Visualized BUT labeled ⚠️ PROVISIONAL

### 8.2 What's Pending (Finance Q1-Q2)

**Q1: COGS Factor Units**
- Current Expense_Assumptions_Input.xlsx contains values: 0.1655, 0.185, etc.
- **Question:** Are these percentages, ratios, per-unit costs, or other?
- **Impact on [COGS Cost Cr Provisional]:** Formula changes based on answer

**Q2: Exact CM2 Formula & Tax-Basis Treatment**
- Current formula (provisional): CM2 = NSV - COGS - Support Costs
- **Questions:**
  - NSV-based or MRP-based?
  - Which cost sheets included (BA salary, supervisor, listing, etc.)?
  - How are tax basis differences handled?
- **Impact on:**
  - [CM2 Cr Provisional]
  - [CM2 Pct Provisional]
  - [Break Even Gap Cr Provisional]
  - Page 7 store status classifications

### 8.3 Handling in Power BI (Until Q1-Q2 Confirmed)

**Page 7 (BA Stores Performance):**
- CM2 measures visualized as cards (yellow background ⚠️)
- Warning banner: "⚠️ PROVISIONAL PROFITABILITY...Do NOT recommend closure or BA withdrawal until Q1-Q2 confirmed."
- Store status shows: "Cost Data Pending" (gray) if missing input

**Page 9 (Profitability / CM2 Readiness):**
- No active CM2 visuals (placeholder text only)
- Lists available measures
- Shows Q1-Q2 blocking questions

### 8.4 Rules for Using Provisional CM2
- ✅ **ALLOWED:** For internal readiness QC (checking data completeness)
- ✅ **ALLOWED:** For Finance review (showing current formula state)
- ❌ **FORBIDDEN:** For store closure decisions
- ❌ **FORBIDDEN:** For BA withdrawal recommendations
- ❌ **FORBIDDEN:** For reporting to leadership without Finance sign-off

### 8.5 What Happens When Finance Confirms Q1-Q2

1. Finance provides:
   - COGS factor units interpretation (Q1)
   - Final CM2 formula + tax-basis treatment (Q2)

2. Update Power BI:
   - Expense_Assumptions_Input.xlsx: Add confirmed values
   - DAX measures: Update formulas
   - Page 9: Unhide profitability visuals
   - Remove "Provisional" from measure names

3. Re-validate:
   - Store status classifications
   - CM2 % ranges
   - Break-even calculations

4. Business review:
   - Use finalized CM2 for decisions
   - Publish reports with confidence

---

## 9. ADDITIONAL PENDING DECISIONS (Finance Q4-Q5)

### 9.1 TOT (Trade-off-Trade) Cost — Awaiting Finance Q4
- **Current status:** Pending % or value input
- **Measure:** [TOT Cost Cr Provisional]
- **Handled as:** BLANK if missing (not zeroed)
- **When available:** Add to Expense_Assumptions_Input.xlsx, measure auto-updates

### 9.2 Promotional Offer Cost — Awaiting Finance Q5
- **Current status:** Pending % or value input
- **Measure:** [Promotional Cost Cr Provisional]
- **Handled as:** BLANK if missing (not zeroed)
- **When available:** Add to Expense_Assumptions_Input.xlsx, measure auto-updates

### 9.3 Impact on Profitability
- Missing TOT/Promo → [Has Missing Costs] = TRUE
- [Has Missing Costs] = TRUE → CM2 measures return BLANK (no false calculations)
- Page 7 Store Status shows: "Cost Data Pending" (gray) for affected stores

---

## 10. MISSING OPERATIONAL DATA (Pending)

### 10.1 Store Master — Awaiting Operations
- **Expected:** Store_Code → Store_Name → Chain → Zone mapping
- **Impact:** Page 6 (Store Performance) currently uses placeholder data
- **When available:** Update Power Query, Page 6 auto-populates with real store names

### 10.2 BA Deployment Dates — Awaiting Operations/Reliance
- **Expected:** Which stores got BA on which date, when BA left
- **Impact:** Pre-BA vs Post-BA analysis (Page 7 Chart 2) currently limited
- **When available:** Creates Pre_BA and Post_BA growth period calculations

### 10.3 BA Headcount/CTC — Awaiting HR
- **Expected:** BA_Master table with employee details, monthly CTC
- **Impact:** [BA Salary Cost Cr], headcount-based allocation currently placeholder
- **When available:** Enables accurate BA cost allocation

---

## 11. SUMMARY: SAFE VS BLOCKED MEASURES

### 11.1 Safe to Use (Data Confirmed)
```
✅ [Total NSV Cr] — Source confirmed (Lakhs)
✅ [NSV MoM Growth Pct] — Calculation confirmed
✅ [Total MRP Sales Value Cr] — Source confirmed (rupees)
✅ [Total Sales Qty M] — Source confirmed
✅ [BA Available NSV Cr] — Segmentation confirmed
✅ [Non_BA Available NSV Cr] — Segmentation confirmed
✅ [Distinct Chains], [Distinct Zones], [Distinct Categories] — QC confirmed
✅ [June26 Partial Row Count] — QC confirmed
✅ [More Retail Duplicates] — Documented as valid
✅ All Sales, Growth, BA Availability measures
```

### 11.2 Provisional (Awaiting Finance Confirmation)
```
⚠️ [CM2 Cr Provisional] — Awaiting Q2 formula
⚠️ [CM2 Pct Provisional] — Awaiting Q2 formula
⚠️ [Break Even Gap Cr Provisional] — Awaiting Q2 formula
⚠️ [TOT Cost Cr Provisional] — Awaiting Q4 %
⚠️ [Promotional Cost Cr Provisional] — Awaiting Q5 %
⚠️ [COGS Cost Cr Provisional] — Awaiting Q1 units interpretation
⚠️ All profitability measures marked PROVISIONAL
```

### 11.3 Blocked (Missing Data)
```
❌ [Store Status] — Awaiting Store Master + BA deployment dates
❌ State-level measures — Awaiting validated City-State mapping
❌ Pre-BA vs Post-BA detailed — Awaiting BA deployment dates
```

---

## 12. CHECKLIST: CONFIRM THESE BEFORE DEPLOYING

- [ ] NSV labeled "(Excl Tax)" everywhere
- [ ] MRP labeled "(Incl Tax)" everywhere
- [ ] NSV/MRP comparison includes tax-basis warning
- [ ] No State slicer or State rollup
- [ ] No BA profitability visuals (except Page 7 ⚠️ with warnings)
- [ ] No More Retail deduplication
- [ ] June'26 marked "Partial" with 78,111 row count
- [ ] Page 9 remains readiness QC only (no active CM2 visuals)
- [ ] All provisional measures have ⚠️ labels
- [ ] Store Master placeholder documented
- [ ] BA deployment dates placeholder documented
- [ ] TOT/Promo pending Finance Q4-Q5 documented

---

**Status:** Final business rules (production-ready)  
**Commit:** e19c467  
**Next:** Await Finance Q1-Q2, Operations Store Master, HR BA data

