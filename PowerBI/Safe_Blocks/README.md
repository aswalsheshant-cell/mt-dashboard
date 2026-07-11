# Power BI Safe Blocks — Complete Build Kit (v2)

**Branch:** claude/safe-powerbi-dashboard-rulings  
**Status:** Updated with business rulings (ready for implementation in Power BI Desktop)  
**Generated:** 2026-07-11  
**Version:** 2 (Business Rulings Applied)

---

## Overview

This folder contains a complete, production-ready Power BI build kit for **safe-to-proceed offtake analytics** (MRP basis, June'26 partial, NSV blocked).

**What's included:**
- Power Query scripts (data loading, QC tables)
- DAX measures (safe-only, no NSV/state/BA profitability)
- Data model specification
- Report page specifications
- Step-by-step build guide
- QC validation checklist
- Blocked measures reference

**What's NOT included yet:**
- PBIP/PBIX file (you build this in Power BI Desktop using the guide)
- CSV seed data (use your existing monthly offtake CSVs)

**Time to build:** 2.5–3.5 hours (first-time implementation in Power BI Desktop with 5 pages)

---

## Files in This Folder

| File | Purpose | Pages | Status |
|------|---------|-------|--------|
| **PowerQuery_Safe_Offtake.pq** | Power Query scripts (data loading, QC tables, BA_Available flag) | 1 | Updated v2, ready to copy-paste |
| **DAX_Safe_Measures.dax** | Safe DAX measures (25+: MRP, Qty, contribution, BA Availability coverage) | 1 | Updated v2, ready to copy-paste |
| **PowerBI_Model_Spec.md** | Data model: tables, columns, relationships, diagram | 8 | Current |
| **PowerBI_Report_Page_Spec.md** | 5 report pages (added Page 5: BA Availability View) | 16 | Updated v2 |
| **Build_In_PowerBI_Desktop_Guide.md** | Step-by-step build instructions (phase 1–6, 5 pages) | 7 | Updated v2 |
| **QC_Validation_Checklist.md** | Pre-build & post-build validation tests (5 pages) | 5 | Updated v2 |
| **Blocked_Measures.md** | 9 blocked measures (v2: More Retail & Brand Counter approved) | 7 | Updated v2 |
| **README.md** | This file | 1 | Overview & quick-start v2 |

**Total:** 46 pages of specification + ready-to-use code (updated with v2 business rulings)

---

## Quick Start (5 minutes)

### To understand what will be built:

1. Read **PowerBI_Report_Page_Spec.md** (skim page titles)
2. Skim **DAX_Safe_Measures.dax** (look at measure names)
3. Review **Blocked_Measures.md** (understand what's intentionally NOT built)

### To build in Power BI Desktop:

1. Follow **Build_In_PowerBI_Desktop_Guide.md** step-by-step (2–3 hours)
2. Validate against **QC_Validation_Checklist.md** (before deploying)
3. Reference **PowerBI_Model_Spec.md** & **PowerBI_Report_Page_Spec.md** as needed

### To understand the model:

1. Read **PowerBI_Model_Spec.md** (tables, columns, relationships)
2. Refer to **PowerQuery_Safe_Offtake.pq** (transformation logic)

---

## What This Build Delivers

### Safe-to-Publish Blocks ✓

✓ **5 Report Pages** (Data Explorer, Overview, QC & Reconciliation, Interim Offtake P&L, BA Availability View)  
✓ **MRP Sales Value basis** (verified, rupee unit; NSV blocked)  
✓ **June'26 flagged as Partial** (78,111 rows, 16 chains; watermarks on Pages 1–4)  
✓ **Zone-level analysis** (P6 canonicalized; state-level rollups blocked)  
✓ **25+ safe DAX measures** (MRP, Qty, contribution %, trends, BA Availability coverage, QC)  
✓ **BA Availability coverage** (Brand Counter = BA coverage; Page 5 reports only, no profitability)  
✓ **5 QC reference tables** (monthly reconciliation, More Retail audit, variants, blocked list, pending decisions)  
✓ **Interactive filtering** (FY, Month, Chain [raw], Zone, Category, Format, Classification)  

### Business Rulings Applied (v2) ✓

✓ **More Retail Records** — Business reviewed; retained as valid source records; no dedup applied
✓ **Reliance Brand Counter** — Approved as BA Availability flag; Page 5 created for coverage view
✓ **State-wise Reporting** — Source data unreliable; zone-level used; no state rollups created

### Remaining Blockers (Awaiting Business Decisions)

✗ **NSV measures** (unit unvalidated; awaiting finance anchor)  
✗ **Profitability measures** (depend on NSV + margin assumptions)  
✗ **BA profitability** (awaiting BA Headcount + cost structure confirmation)  
✗ **Chain canonicalization** (variants Vmm/VMM, Fsn/FSN, etc. awaiting business approval)  

---

## Data Model Summary

```
Fact_Offtake_Safe (4.21M rows)
  ├─ Dim_Month (27 rows)
  ├─ Dim_Chain_Raw (34 rows, raw names preserved)
  ├─ Dim_Zone (37 rows)
  ├─ Dim_Category (50–150 rows)
  └─ QC Reference Tables (5 tables, no relationships)
```

**Measures:** 22+ safe-only (MRP basis)  
**Blocked:** 11+ (NSV, profitability, state, BA, dedup)

---

## Implementation Phases

| Phase | Time | Tasks | Deliverable |
|-------|------|-------|-------------|
| 1 | 30–45 min | Create queries, load data, transform | Fact_Offtake_Safe + 4 dimensions + 5 QC tables |
| 2 | 10–15 min | Define relationships | Star schema (fact ↔ 4 dims) |
| 3 | 20–30 min | Create DAX measures | 22+ safe measures |
| 4 | 45–60 min | Build 4 report pages | All visuals, slicers, formatting |
| 5 | 15–20 min | Validate (QC checklist) | Confirm safe-only, no NSV, June'26 flagged |
| 6 | 5 min | Save & export | PBIP or PBIX file |

**Total: 2–3 hours**

---

## Key Features

### ✓ June'26 Partial Flagging

- **Dim_Month[Is_Partial]** = TRUE for June'26
- **Fact_Offtake_Safe[Is_June26_Partial]** = TRUE for all June'26 rows
- **Watermarks** on every page: "⚠ June'26 Partial"
- **Visual markers** in charts (dashed line, different color, annotation)
- **Row count** (~78,111 rows, 16 chains only)

### ✓ NSV Unit Blocked (Watermarked)

- **No [NSV] measure** created (will error if attempted)
- **No NSV in any chart** (all value-based visuals use MRP)
- **Watermark:** "⚠ NSV unit pending | Interim MRP basis only"
- **QC page:** Full explanation + pending decisions table
- **Blocked Measures list:** 11 items documented

### ✓ Safe Filtering (No State, NSV, or BA)

**Slicers included:**
- FY (dropdown, multi-select)
- Month (dropdown, multi-select)
- Chain (dropdown, raw names, variants included)
- Zone (dropdown, canonicalized)
- Category (dropdown, multi-select)
- Format (dropdown, multi-select)
- Classification (dropdown, multi-select)

**Slicers NOT included (blocked):**
- State (mapping pending)
- NSV (unit pending)
- BA metrics (headcount + classification pending)

### ✓ QC & Validation Built-In

**On QC & Reconciliation page:**
- Monthly reconciliation table (27 rows, one per month)
- Chain variant summary (34 chains, raw names preserved)
- More Retail duplicate report (13,661 dup rows, ₹1.36 Cr)
- Blocked measures list (11 items)
- Pending decisions table (6 blocking items + timeline)

---

## Blocked Business Decisions (6 Items)

Until these are resolved, the following remain blocked:

| # | Decision | Impact | Timeline |
|---|----------|--------|----------|
| 1 | **NSV Unit Validation** | Unblocks all NSV/P&L/profitability measures | 1–2 wk |
| 2 | **More Retail Duplicates** | 13,661 dup rows = ₹1.36 Cr MRP (10.3% of total) | 1–3 wk |
| 3 | **Brand Counter Classification** | 549,617 rows; is it BA channel or chain? | 1 wk |
| 4 | **State-to-City Mapping** | 247 raw state values (include cities) → canonicalization | 1–2 wk |
| 5 | **Chain Master Canonicalization** | Variants (Vmm/VMM, Fsn/FSN, etc.) awaiting merge | 1 wk |
| 6 | **Reliance Schema** | 29 cols (vs 40-42 std); accept partial or request full | 1–3 wk |

See **Blocked_Measures.md** for full details on each.

---

## Data Quality

✓ **4.21M rows** (Apr'24–Jun'26, 582 files, 27 months)  
✓ **MRP Sales Value:** ₹1,443.45 Cr (verified basis)  
✓ **Sales Qty:** 2,055,065,438 units  
✓ **Chains:** 34 distinct (raw names preserved; variants not merged)  
✓ **Zones:** 37 canonicalized (P6)  
✓ **Negative-value rows:** 12,705 (valid returns/credit notes; preserved, flagged)  
✓ **June'26 partial:** 78,111 rows from 16 chains  
✓ **More Retail duplicates:** 13,661 exact-dup rows (reported, not removed)  

---

## Next Steps

### To Build Now:

1. **Read** Build_In_PowerBI_Desktop_Guide.md
2. **Open** Power BI Desktop
3. **Follow** Phases 1–6 step-by-step (2–3 hours)
4. **Validate** using QC_Validation_Checklist.md
5. **Save** as PBIP or PBIX

### After Business Decisions:

Once decisions 1–6 are made:
1. Add [NSV] measures (if NSV unit confirmed)
2. Implement P&L / Profitability measures
3. Add State dimension + state-level rollups
4. Add BA Store Master + BA profitability
5. Apply More Retail dedup (if approved)
6. Merge chain variants in Dim_Chain_Canonical

---

## Support & Questions

**For questions about the specification:**
- See relevant .md file (PowerBI_Model_Spec.md, PowerBI_Report_Page_Spec.md, etc.)

**For implementation help:**
- See Build_In_PowerBI_Desktop_Guide.md (step-by-step)

**For troubleshooting:**
- See Build_In_PowerBI_Desktop_Guide.md → Troubleshooting section
- Run QC_Validation_Checklist.md to identify issues

**For blocked measures logic:**
- See Blocked_Measures.md (full reference)

---

## Version & Branch Info

- **Branch:** claude/safe-powerbi-blocks
- **Generated:** 2026-07-11
- **Status:** Draft (ready for implementation)
- **PR #14:** NOT merged (separate from original PR)
- **Main branch:** NOT affected
- **Files in repo:** All in PowerBI/Safe_Blocks/

---

## Checklist Before Building

- [ ] Power BI Desktop 2024.11+ installed
- [ ] Monthly offtake CSV files available (Apr'24–Jun'26, 582 files)
- [ ] Read Build_In_PowerBI_Desktop_Guide.md
- [ ] Understand data model (PowerBI_Model_Spec.md)
- [ ] Understand report pages (PowerBI_Report_Page_Spec.md)
- [ ] Have QC_Validation_Checklist.md open (for final validation)

---

**Ready to build. Follow the guide. Estimated 2–3 hours. Good luck!**

