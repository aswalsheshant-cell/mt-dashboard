# Business Rulings Applied (v2)

**Branch:** claude/safe-powerbi-dashboard-rulings  
**Date:** 2026-07-11  
**Version:** 2  
**Previous Version:** v1 (claude/safe-powerbi-blocks)

---

## Summary of Changes

Three business rulings have been applied, unblocking previous decisions and enabling new dashboard features.

| Item | v1 Status | v2 Status | Change |
|------|-----------|-----------|--------|
| More Retail Duplicates | BLOCKED (pending dedup decision) | ✓ APPROVED (No dedup) | Removed from blockers; all rows retained |
| Reliance Brand Counter | BLOCKED (pending classification) | ✓ APPROVED (BA Availability) | Added BA_Available flag; Page 5 created |
| State Mapping | BLOCKED (pending City-State mapping) | ✓ APPROVED (No state rollups) | Removed state blockers; zone-only approach |

---

## Detailed Changes

### 1. More Retail Records Approved

**Ruling:**  
More Retail rows are NOT duplicates for dashboard purposes. All rows are valid source records.

**Changes Made:**

**Power Query (PowerQuery_Safe_Offtake.pq):**
- Removed QC_Duplicate_Report dedup logic
- Renamed to QC_More_Retail_Audit (simpler monthly aggregation)
- Updated note: "Business has reviewed repeated records and retained them as valid source data. No deduplication is applied."

**DAX (DAX_Safe_Measures.dax):**
- Removed note about "13,661 dup rows (₹1.36 Cr / 10.3% MRP)"
- Updated blocked measure comment: Changed from dedup blocker to "Business reviewed and retained as valid"

**Reports:**
- QC & Reconciliation page now shows More Retail Audit table (monthly rollups, not duplicates)
- Removed "More Retail duplicates reported but NOT deduped" from conditional note
- Changed to: "More Retail rows kept; no dedup applied"

**Blocked List (Blocked_Measures.md):**
- Removed Item #11 (More Retail Chain Totals & Dedup Decision)
- Updated summary table: 11 items → 9 items

**Documentation:**
- README.md: "More Retail is not called inflated in final visuals"
- QC_Validation_Checklist.md: Updated Test 2 to check More Retail Audit instead of duplicates

---

### 2. Reliance Brand Counter = BA Availability

**Ruling:**  
Brand Counter under Reliance represents places/accounts where our BA is available. Create BA Availability flag for coverage visibility; DO NOT treat as chain or profitability.

**Changes Made:**

**Power Query (PowerQuery_Safe_Offtake.pq):**
- Added column: `BA_Available = IF [Chain_Name] = "Brand Counter" THEN "Yes" ELSE "No"`
- Included in final column reorder
- Note: "Brand Counter = BA coverage for Reliance"

**DAX (DAX_Safe_Measures.dax):**
- Added 5 new safe measures (coverage only, NOT profitability):
  - `[BA Available Row Count]`
  - `[BA Available MRP Sales Value]`
  - `[BA Available MRP Sales Value Cr]`
  - `[BA Availability Mix %]`
  - `[BA Availability Note]` (display-only message)
- Updated blocked measure comment: "BA Profitability remains blocked pending BA cost/headcount"
- Clarified: "BA Availability measures show coverage, not profitability"

**Reports:**
- **NEW Page 5: BA Availability View**
  - Title: "Reliance BA Availability Coverage"
  - Watermark: "Coverage view only. BA profitability blocked."
  - KPI cards: BA Available Row Count, BA Available MRP, BA Availability Mix %, Total MRP (comparison)
  - Charts: BA Available MRP by Zone/Category, BA Available MRP Trend, Total BA Available Rows
  - Detail table: BA-available records only (Brand Counter rows)
  - Info box: "Brand Counter = BA Availability. Coverage only, not profitability."

**Data Model:**
- Added BA_Available column to Fact_Offtake_Safe
- No new dimension tables required (BA_Available is a Yes/No flag)

**Blocked List (Blocked_Measures.md):**
- Updated Item #9: "BA Profitability" now specifies:
  - APPROVED: BA Availability flag exists (coverage view on Page 5)
  - BLOCKED: BA Profitability measures (pending BA Headcount + cost structure)

**Build Guide (Build_In_PowerBI_Desktop_Guide.md):**
- Added Step 4.7: Page 5 — BA Availability View (new page instructions)
- Updated Phase 4 time estimate: 45–60 min → 60–75 min
- Added validation: "Page 5 watermark clearly states 'Coverage only, not profitability'"

**Documentation:**
- README.md: "✓ BA Availability coverage (Brand Counter = BA coverage; Page 5 reports only, no profitability)"
- QC_Validation_Checklist.md: Added validation for Page 5 and BA Available measures
- PowerBI_Report_Page_Spec.md: Added complete Page 5 specification

---

### 3. State Mapping Approved (Zone-Only Approach)

**Ruling:**  
State mapping is mostly pending because source data is not reliably received state-wise. NO state-level rollups. NO state slicer. Use zone-only reporting.

**Changes Made:**

**Power Query (PowerQuery_Safe_Offtake.pq):**
- Kept State columns as raw QC fields (not reporting dimensions)
- Updated QC_Blocked_Measures note: "247 raw state values include cities; mapping pending" → "Source data lacks reliable state mapping"
- Updated QC_Pending_Decisions: "State-to-City Mapping" → Status = APPROVED: "No state-level rollups. Zone-level used instead."

**DAX (DAX_Safe_Measures.dax):**
- Updated blocked measure comment for State-level: "Source data lacks reliable state mapping; zone-level reporting available instead"
- No state measures created or needed (already using zone-level)

**Reports:**
- All pages use ZONE slicers only (not State)
- No state-level breakdown charts on any page
- QC & Reconciliation page includes note: "State-wise reporting pending due to incomplete/unreliable source state mapping. Zone-level reporting used instead."

**Blocked List (Blocked_Measures.md):**
- Updated Item #10: "State-level rollups" now specifies:
  - APPROVED: No state rollups needed
  - Status: Zone-level reporting available and used
  - Timeline: COMPLETE

**Documentation:**
- README.md: "Zone-level analysis (P6 canonicalized; state-level rollups blocked)"
- QC_Validation_Checklist.md: Updated to confirm NO state slicer exists
- PowerBI_Report_Page_Spec.md: Confirmed state filter NOT included in slicers

---

## Files Updated

| File | Changes | Type |
|------|---------|------|
| PowerQuery_Safe_Offtake.pq | Added BA_Available flag; renamed More Retail audit query; updated blocked list | Code |
| DAX_Safe_Measures.dax | Added 5 BA Availability measures; updated blocked comments | Code |
| PowerBI_Report_Page_Spec.md | Added Page 5 (BA Availability View); updated overview | Spec |
| Build_In_PowerBI_Desktop_Guide.md | Added Step 4.7; updated phase times; updated validation | Guide |
| QC_Validation_Checklist.md | Updated for 5 pages; added Page 5 validation; new Test 6 | Checklist |
| Blocked_Measures.md | Removed 2 items (#11, #12); updated summary table; added v2 implementation order | Reference |
| README.md | Updated branch; added v2 status; 4→5 pages; added approved rulings | Overview |
| BUSINESS_RULINGS_APPLIED.md | NEW: This document | Documentation |

---

## Summary of All Blockers (v2)

### Approved & Complete ✓

1. ✓ **More Retail Records** — Business reviewed; kept as valid; no dedup
2. ✓ **Reliance Brand Counter** — BA Availability flag created; Page 5 shows coverage only
3. ✓ **State-wise Reporting** — No state rollups; zone-only approach approved

### Remaining Blockers (Awaiting Business Decisions)

1. **NSV Unit Validation** — Finance must provide ₹Cr anchor (Timeline: Pending)
2. **P&L / Profitability** — Requires NSV unit + margin assumptions (Timeline: Pending post-NSV)
3. **BA Profitability** — Requires BA Headcount + cost structure + NSV unit (Timeline: Pending)
4. **Chain Master Canonicalization** — Awaiting approval of canonical names (Timeline: Pending)
5. **Reliance Schema Completeness** — Accept partial (29 cols) or request full (Timeline: Pending)

---

## Implementation Path (v2)

**Immediate (v2):**
1. Build 5 report pages (was 4)
2. Include BA Availability coverage view (Page 5)
3. More Retail: All rows kept, no dedup
4. State: Zone-level only
5. NSV: Still blocked

**Next (Pending NSV Unit):**
- Add [NSV Cr] measure
- Unblock NSV-based pages and measures
- Implement P&L/Profitability measures

**Later (Pending Other Decisions):**
- Chain canonicalization: Merge Vmm/VMM, Fsn/FSN variants
- BA Headcount: Add BA profitability measures
- Reliance Schema: Confirm or request full export

---

## Build Time Impact

- **v1:** 2–3 hours (4 pages)
- **v2:** 2.5–3.5 hours (5 pages, includes Page 5 BA Availability)

**Additional Time:**
- +30 min for Page 5 build (4 charts + KPI cards + detail table)
- -15 min on QC page (simpler More Retail Audit, no dedup logic)
- **Net:** +15 min

---

## Branch & Merge Plan

**Current Branch:** `claude/safe-powerbi-dashboard-rulings`  
**Original Branch:** `claude/safe-powerbi-blocks` (PR #14, separate)

**Merge Order:**
1. Do NOT merge PR #14 yet (contains v1 without business rulings)
2. After v2 testing: Create new PR from `claude/safe-powerbi-dashboard-rulings`
3. New PR contains all v2 updates with business rulings applied

---

**Status:** v2 complete. Ready for Power BI Desktop implementation using new specification files.

