# Known Blockers & Pending Decisions

**Dashboard:** MT Offtake Dashboard  
**Status:** Phase 2 build (Pages 1–10, with blockers documented)  
**Commit:** e19c467  
**Date:** 2026-07-11

---

## BLOCKED ITEMS (Cannot Build Without External Input)

### 1. CM2 Formula & Tax-Basis Treatment — Finance Q2 ❌ CRITICAL
**Status:** 🔴 BLOCKED  
**Owner:** Finance Q1-Q2  
**Current Impact:**
- Page 7 (BA Stores Performance): CM2 measures visualized with ⚠️ PROVISIONAL labels
- Page 9 (Profitability): Readiness QC only (no active visuals)
- Store recommendations: All show "Under Review — Provisional"

**What's needed:**
- Exact formula: NSV-based or MRP-based?
- Which cost sheets included? (All? Only direct costs?)
- Tax-basis handling: How to reconcile NSV (excl tax) with MRP (incl tax) in calculation?

**Impact when answered:**
- Update [CM2 Cr Provisional] formula
- Update [CM2 Pct Provisional] calculation
- Build out Page 9 profitability visuals
- Finalize store classifications (Strong Performer, Monitor, Improvement, etc.)

**Timeline:** Expected Q2 (within 1 week)

---

### 2. COGS Factor Units Interpretation — Finance Q1 ❌ CRITICAL
**Status:** 🔴 BLOCKED  
**Owner:** Finance Q1-Q2  
**Current Impact:**
- [COGS Cost Cr Provisional] created but may use wrong interpretation
- Affects CM2 calculation (Finance Q2 depends on this)

**What's needed:**
- Current Expense_Assumptions_Input.xlsx contains: 0.1655, 0.185, 0.155, etc.
- Question: Are these % margins, ratio multipliers, per-unit costs, or other?
- Example:
  - If % margin: COGS = NSV × 0.1655
  - If ratio: COGS = NSV × 0.1655 (same as above)
  - If per-unit: COGS = Qty × 0.1655 (very different!)

**Impact when answered:**
- Update [COGS Cost Cr Provisional] formula (will affect CM2 calculation)
- Re-run Page 7 profitability table with correct COGS
- Update Store Status classifications

**Timeline:** Expected Q1 (within 1 week)

---

### 3. Store Master (Store_Code → Chain → Zone Mapping) — Operations 🟡 PARTIAL
**Status:** 🟡 WAITING  
**Owner:** Operations  
**Current Impact:**
- Page 6 (Store Performance): Using placeholder data (4 example stores)
- Page 7 (BA Stores): Store drill-down limited

**What's needed:**
- Real Store_Code column
- Store_Name column
- Chain assignment
- Zone assignment (P6 canonical)
- BA_Deployment_Date (optional but valuable)

**Current state in Power Query:**
```
Store_Code | Store_Name | Chain | Zone | Region | BA_Deployment_Date | BA_Status
REL-001    | Reliance... | Rel   | W-1  | WEST   | 2026-04-15        | BA
```

**Impact when available:**
- Page 6 auto-populates with real store names
- Page 7 store profitability table shows actual stores
- Drill-down analysis becomes actionable

**Timeline:** Awaiting Operations (no hard deadline)

---

### 4. BA Deployment Dates & Pre/Post-BA Classification — Operations/Reliance 🟡 PARTIAL
**Status:** 🟡 WAITING  
**Owner:** Operations / Reliance HR  
**Current Impact:**
- Page 7, Chart 2 (Pre-BA vs Post-BA Growth): Limited to BA flag only
- Cannot calculate true Pre-BA period vs Post-BA impact
- [Pre_BA Growth Pct] and [Post_BA Growth Pct] measures currently use BA_Available flag as proxy

**What's needed:**
- For each store with BA_Available = Yes:
  - BA_Deployment_Date: When BA started
  - Separation_Date: When BA left (if applicable)
- Allows calculation of:
  - Pre-BA period: Months before BA_Deployment_Date
  - Post-BA period: Months after BA_Deployment_Date
  - Comparable-store growth comparison

**Impact when available:**
- More accurate Pre-BA vs Post-BA analysis
- Can show actual BA impact on store growth
- Support for Page 7 Chart 2 deeper analysis

**Timeline:** Awaiting Operations/Reliance (no hard deadline)

---

### 5. TOT (Trade-off-Trade) Cost % or Value — Finance Q4 🟡 PARTIAL
**Status:** 🟡 WAITING  
**Owner:** Finance Q4  
**Current Impact:**
- [TOT Cost Cr Provisional] measure created but returns BLANK (no input)
- Page 7 & 8: TOT costs show as missing (yellow highlight "Pending")
- Store profitability incomplete

**What's needed:**
- TOT % (if percentage of NSV/MRP)
- OR TOT Value (if absolute cost per store/month)
- For all relevant stores/months

**Where to add:**
- Expense_Assumptions_Input.xlsx → TOT_Percentage or TOT_Value column
- By Store_Code × Month

**Impact when available:**
- [TOT Cost Cr Provisional] auto-calculates
- Page 7 store costs complete
- CM2 calculation more accurate

**Timeline:** Expected Finance Q4 (no hard deadline)

---

### 6. Promotional Offer Cost % or Value — Finance Q5 🟡 PARTIAL
**Status:** 🟡 WAITING  
**Owner:** Finance Q5  
**Current Impact:**
- [Promotional Cost Cr Provisional] measure created but returns BLANK (no input)
- Page 7 & 8: Promo costs show as missing (yellow highlight "Pending")
- Store profitability incomplete

**What's needed:**
- Promo % (if percentage of NSV/MRP)
- OR Promo Value (if absolute cost per store/month)
- For all relevant stores/months

**Where to add:**
- Expense_Assumptions_Input.xlsx → Promotional_Offer_Percentage or Promotional_Offer_Value column
- By Store_Code × Month

**Impact when available:**
- [Promotional Cost Cr Provisional] auto-calculates
- Page 7 store costs complete
- CM2 calculation more accurate

**Timeline:** Expected Finance Q5 (no hard deadline)

---

### 7. BA Headcount & CTC Data — HR 🟡 PARTIAL
**Status:** 🟡 WAITING  
**Owner:** HR  
**Current Impact:**
- BA_Master table uses placeholder data (4 example employees)
- [BA Salary Cost Cr] uses placeholder rates
- Headcount-based cost allocation not fully populated

**What's needed:**
- BA_ID, BA_Name, Chain, Zone assignment
- Monthly_CTC (salary)
- Deployment_Date & Separation_Date
- For all BA staff (current + historical)

**Impact when available:**
- Accurate BA salary cost allocation
- Headcount trending
- Cost-per-BA metrics

**Timeline:** Awaiting HR (no hard deadline, but improves accuracy)

---

## COMPLETED DECISIONS (No Further Action Needed)

### ✅ NSV Unit Confirmed (Lakhs)
**Decision:** NSV source is Lakhs (₹100K per lakh)  
**Confirmed by:** Phase 1 v3 ruling  
**Implementation:** NSV_Cr = Source_NSV_Lacs ÷ 100  
**Status:** ✅ COMPLETE — no further input needed

---

### ✅ More Retail Duplicate Retention
**Decision:** 13,661 More Retail rows retained as valid (not deduped)  
**Confirmed by:** Phase 1 data quality analysis  
**Implementation:** No deduplication in Power Query  
**Status:** ✅ COMPLETE — no further action

---

### ✅ State Reporting Exclusion
**Decision:** No state-level rollups; zone-only reporting (P6 canonical zones)  
**Reason:** Source state data unreliable (city-state mapping incomplete)  
**Implementation:** Zone dimension only, no State slicer  
**Status:** ✅ COMPLETE — all pages follow this rule

---

### ✅ Brand Counter = BA Availability
**Decision:** Brand Counter measures only segment by BA_Available flag  
**NOT:** BA profitability or cost impact  
**Implementation:** [BA Available NSV Cr], [Non_BA Available NSV Cr] measures  
**Status:** ✅ COMPLETE — measures created and validated

---

### ✅ June'26 Partial Data Handling
**Decision:** 78,111 Jun-26 rows (16 chains only) included with watermark  
**NOT:** Excluded or adjusted  
**Implementation:** Is_June26_Partial = TRUE flag + warning on all pages  
**Status:** ✅ COMPLETE — warning visible

---

### ✅ BA Profitability NOT Implemented
**Decision:** No "BA profitability" visuals (Page 7 shows BA-availability only, not break-even)  
**Reason:** Awaiting Finance Q2 CM2 formula  
**Implementation:** Page 7 CM2 measures marked PROVISIONAL ⚠️, Page 9 is QC only  
**Status:** ✅ COMPLETE — correctly scoped

---

## PENDING DECISIONS (Finance/Operations to Answer)

| Item | Question | Owner | Expected Answer | Timeline |
|------|----------|-------|-----------------|----------|
| **COGS Units** | Are 0.1655 values %, ratio, per-unit, or other? | Finance Q1 | "These are % margins of NSV" or similar | 1 week |
| **CM2 Formula** | NSV-based or MRP-based? Which costs included? Tax handling? | Finance Q2 | "CM2 = NSV - COGS - BA_Salary - Listing" or similar | 1 week |
| **TOT %** | What % of NSV/MRP is TOT? | Finance Q4 | "TOT is 5% of NSV" or "TOT is 2% of MRP" | 2-3 weeks |
| **Promo %** | What % of NSV/MRP is Promotional? | Finance Q5 | "Promo is 3% of NSV" or "Promo is 1.5% of MRP" | 2-3 weeks |
| **Store Master** | Store_Code → Chain → Zone mapping with BA dates? | Operations | Excel/CSV with store list + dates | No deadline |
| **BA Deployment** | When was BA deployed at each store? When separated? | Operations/Reliance | Store × BA_Start_Date × BA_End_Date | No deadline |
| **BA Headcount** | Employee list with CTC and deployment dates? | HR | CSV of all BA staff (current + historical) | No deadline |

---

## BLOCKERS → READY DECISION FLOW

### When Finance Confirms Q1 (COGS Units)
1. **Action:** Update Expense_Assumptions_Input.xlsx with confirmed COGS interpretation
2. **Power BI:** Update [COGS Cost Cr Provisional] formula
3. **Impact:** CM2 calculation becomes more accurate (but still provisional until Q2)
4. **Status change:** Q1 ✅ ANSWERED

---

### When Finance Confirms Q2 (CM2 Formula)
1. **Action:** Update Expense_Assumptions_Input.xlsx with Finance-approved formula
2. **Power BI:**
   - Update [CM2 Cr Provisional] formula
   - Update [CM2 Pct Provisional] formula
   - Update [Break Even Gap Cr Provisional] formula
   - Rename measures: Remove "Provisional" suffix
3. **Page 9:** Unlock and build profitability visuals
4. **Page 7:** Finalize store classifications (remove "Under Review" status)
5. **Status change:** Q2 ✅ ANSWERED → Build Page 9 profitability analysis

---

### When Finance Confirms Q4 (TOT %)
1. **Action:** Update Expense_Assumptions_Input.xlsx with TOT % or value
2. **Power BI:** [TOT Cost Cr Provisional] auto-calculates
3. **Page 7 & 8:** TOT costs populate (no more yellow "Pending" highlight)
4. **Status change:** Q4 ✅ ANSWERED

---

### When Finance Confirms Q5 (Promo %)
1. **Action:** Update Expense_Assumptions_Input.xlsx with Promo % or value
2. **Power BI:** [Promotional Cost Cr Provisional] auto-calculates
3. **Page 7 & 8:** Promo costs populate (no more yellow "Pending" highlight)
4. **Status change:** Q5 ✅ ANSWERED

---

### When Operations Provides Store Master
1. **Action:** Update Power Query source path (or import new CSV)
2. **Power BI:** Page 6 (Store Performance) auto-updates with real store names
3. **Page 7:** Store drill-down becomes fully actionable
4. **Status change:** Store Master ✅ PROVIDED

---

### When Operations/Reliance Provides BA Deployment Dates
1. **Action:** Update BA_Master table with deployment/separation dates
2. **Power BI:** [Pre_BA Growth Pct], [Post_BA Growth Pct] calculations improve
3. **Page 7:** Chart 2 (Pre-BA vs Post-BA) shows deeper analysis
4. **Status change:** BA Deployment ✅ PROVIDED

---

## SUMMARY: WHAT CAN BE BUILT NOW vs. WHAT MUST WAIT

### Build Now (Phases 1–8, Page 10) ✅
- Page 1–8: All core sales, cost, BA-availability, QC visuals
- Measures: NSV, MRP, Qty, Growth, BA segmentation, Cost totals, QC flags
- Data model: Complete and validated
- Slicers: All functional

### Must Wait for Finance Q1-Q2 🔴
- Page 9: Profitability dashboard (QC placeholder only for now)
- Page 7 CM2 cards & store status finalization
- Profitability recommendations (closure, BA withdrawal, etc.)

### Nice to Have (Improves Page 6-7 Actionability) 🟡
- Store Master (real store names)
- BA deployment dates (Pre-BA vs Post-BA analysis)
- HR BA headcount (accurate salary allocation)

---

**Current Status:** Phase 2 ready (Pages 1–10 buildable; Page 9 holds for Q1-Q2)  
**Next Gate:** Finance Q1-Q2 answers → Unlock profitability analysis

