# Power BI Safe Blocks — Complete Build Kit (v3.1)

**Branch:** claude/safe-powerbi-dashboard-rulings  
**Status:** NSV unit confirmed (Lakhs) + tax-basis ruling applied (ready for Power BI Desktop)  
**Generated:** 2026-07-11  
**Version:** 3.1 (Tax-Basis Clarification: NSV excl. tax, MRP incl. tax)

---

## Critical Update: Tax-Basis Ruling (v3.1)

**NSV and MRP operate on DIFFERENT tax bases:**
- **NSV** = Net Sales Value **EXCLUDING tax** (unit: Lakhs)
- **MRP Sales Value** = Gross consumer value **INCLUDING tax** (actual rupees)

**Impact:**
- ✓ All NSV cards/charts labeled "excluding tax"
- ✓ All MRP cards/charts labeled "including tax"
- ✓ MRP vs NSV comparisons marked "QC/realization only" (tax basis differs)
- ✓ Profitability/CM2 remains blocked (requires cost structure + tax-basis CM2 formula)

**See:** `TAX_BASIS_RULING.md` for complete documentation.

---

## Overview

This folder contains a complete, production-ready Power BI build kit for **safe-to-proceed offtake analytics** with **tax-aware NSV (excl. tax) and MRP (incl. tax) reporting**.

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
| **PowerQuery_Safe_Offtake.pq** | Power Query scripts (NSV excl. tax: Lakhs→Cr; MRP incl. tax, Qty, BA flag) | 1 | Updated v3, tax-aware |
| **DAX_Safe_Measures.dax** | Safe DAX measures (30+: NSV excl. tax, MRP incl. tax, Qty, trends, BA) | 1 | Updated v3, tax-labeled |
| **PowerBI_Model_Spec.md** | Data model: tables, columns, relationships, diagram | 8 | Current (NSV/MRP tax basis added) |
| **PowerBI_Report_Page_Spec.md** | 5 report pages (NSV excl. tax, MRP incl. tax charts; tax-basis notes) | 16 | Updated v3.1 |
| **Build_In_PowerBI_Desktop_Guide.md** | Step-by-step build instructions (phase 1–6, 5 pages, tax-basis aware) | 7 | Updated v3.1 |
| **QC_Validation_Checklist.md** | Pre-build & post-build validation (NSV excl. tax, MRP incl. tax checks) | 5 | Updated v3.1 |
| **Blocked_Measures.md** | 9 blocked measures (cost sources now block P&L/CM2; NSV unblocked) | 7 | Updated v3 |
| **NSV_UNIT_CONFIRMED.md** | v2→v3 update: NSV unit confirmed as Lakhs | 6 | Reference (v3 milestone) |
| **TAX_BASIS_RULING.md** | **v3.1 NEW:** Tax-basis clarification (NSV excl. tax, MRP incl. tax) | 10 | New (v3.1 critical) |
| **README.md** | This file | 1 | Overview & quick-start v3.1 |

**Total:** 60+ pages of specification + tax-aware code (v3.1: NSV unit confirmed as Lakhs, tax-basis applied)

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

✓ **5 Report Pages** (Data Explorer, Overview, QC & Reconciliation, Interim Offtake View, BA Availability View)  
✓ **NSV Sales Value basis** (Lakhs ÷ 100 for Crore display; **EXCLUDING tax**)  
✓ **MRP Sales Value basis** (actual rupees ÷ 10,000,000 for Crore display; **INCLUDING tax**)  
✓ **Tax-aware labels** (all NSV cards "excl. tax"; all MRP cards "incl. tax"; comparisons marked QC/realization only)  
✓ **June'26 flagged as Partial** (78,111 rows, 16 chains; watermarks on Pages 1–4)  
✓ **Zone-level analysis** (P6 canonicalized; state-level rollups blocked by business decision)  
✓ **30+ safe DAX measures** (NSV excl. tax, MRP incl. tax, Qty, contribution %, trends, BA, QC)  
✓ **NSV & MRP Trends** (shown separately for net/gross view; comparison marked QC/realization only)  
✓ **BA Availability coverage** (Brand Counter = BA coverage; Page 5 reports only, no profitability)  
✓ **5 QC reference tables** (monthly reconciliation with tax-basis checks, More Retail audit, variants, blocked list, pending decisions)  
✓ **Interactive filtering** (FY, Month, Chain [raw], Zone, Category, Format, Classification)  

### Business Rulings Applied ✓

**v3 — NSV Unit Confirmed:**
✓ **NSV Unit Confirmed** — Source is in Lakhs; NSV Cr = Lakhs ÷ 100; all NSV measures now ACTIVE

**v3.1 — Tax-Basis Ruling (NEW):**
✓ **Tax-Basis Clarification** — NSV excludes tax; MRP includes tax; all pages labeled accordingly
✓ **Comparison Rules** — MRP vs NSV shown for QC/realization only (tax basis differs)

**Earlier Rulings:**
✓ **More Retail Records** — Business reviewed; retained as valid source records; no dedup applied
✓ **Reliance Brand Counter** — Approved as BA Availability flag; Page 5 created for coverage view
✓ **State-wise Reporting** — Source data unreliable; zone-level used; no state rollups created

### Remaining Blockers (Awaiting Business Decisions)

✗ **Profitability & CM2 measures** (require cost sources, COGS, allocation rules)  
✗ **Margin % measures** (require margin assumptions and cost sources)  
✗ **BA Profitability** (requires BA Headcount + cost structure; NSV now confirmed)  
✗ **Primary vs Offtake Gap** (requires Primary NSV validation)  
✗ **Chain Variant Consolidation** (awaiting canonical names approval)  

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

**Measures:** 30+ safe (NSV excl. tax, MRP incl. tax, Qty, contribution %, trends, BA, QC)  
**Blocked:** 6 (cost sources block P&L/CM2; NSV now ACTIVE)

---

## Implementation Phases

| Phase | Time | Tasks | Deliverable |
|-------|------|-------|-------------|
| 1 | 30–45 min | Create queries, load data, transform | Fact_Offtake_Safe + 4 dimensions + 5 QC tables |
| 2 | 10–15 min | Define relationships | Star schema (fact ↔ 4 dims) |
| 3 | 20–30 min | Create DAX measures | 30+ safe measures (NSV excl. tax, MRP incl. tax) |
| 4 | 45–60 min | Build 5 report pages | All visuals, slicers, formatting, tax-basis labels |
| 5 | 15–20 min | Validate (QC checklist) | Confirm NSV excl. tax, MRP incl. tax, June'26 flagged |
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

### ✓ NSV Unit Active (Tax-Basis Aware)

- **NSV Measures ACTIVE** (Source NSV Lacs, NSV Cr, NSV Actual Value, etc.)
- **All NSV labeled "excluding tax"** (clearly distinguished from MRP)
- **Tax-basis awareness:** NSV and MRP conversions documented; ratio shown for QC/realization only
- **Watermark:** "NSV excludes tax. MRP Sales Value includes tax. Use separately for net/gross view."
- **Blocked Measures list:** 6 items (cost sources, not NSV unit; NSV now ACTIVE)

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
- State (mapping pending; zone-level used instead)
- BA metrics (headcount + profitability pending; BA coverage on Page 5 only)

### ✓ QC & Validation Built-In

**On QC & Reconciliation page:**
- Monthly reconciliation table with tax-basis checks (27 rows, NSV excl. tax vs MRP incl. tax)
- Chain variant summary (34 chains, raw names preserved)
- More Retail duplicate report (13,661 dup rows, ₹1.36 Cr; retained per business approval)
- Realization ratio (MRP to NSV, QC/realization only)
- Negative value tracking (NSV and MRP separately)
- Blocked measures list (6 items)
- Pending decisions table (timeline to cost structure confirmation)

---

## Business Inputs Needed for Profitability (v3.1 Status Update)

**v3 Complete:** NSV unit confirmed (Lakhs); tax-basis clarified (NSV excl. tax, MRP incl. tax)

**Profitability Implementation Status (Partially Unblocked):**

| # | Input | Blocks | Status | Timeline |
|---|-------|--------|--------|----------|
| 1 | **CM2 Formula (exact)** | P&L / CM2 / Margin % measures | **Pending** (CRITICAL) | 1–2 wk |
| 2 | **Cost Data (COGS, allocation)** | Profitability calculations | **✓ RECEIVED** (All_Expenses_together.xlsx): COGS, BA Salary, BA Supervisor, Dmart BA-Merchandiser, Other Employ, Visibility/Rental | Ready to integrate |
| 3 | **Tax Handling Rules** | CM2 tax-basis treatment | **Pending** (CRITICAL) | 1 wk |
| 4 | **BA Headcount & Cost** | BA profitability (BA coverage active on Page 5) | **Partial** (salary data received; headcount mapping pending) | 1 wk |
| 5 | **Chain Master Canonicalization** | Chain variant consolidation | Pending from Business | 1 wk |

**Approved & Complete:**
✓ NSV Unit = Lakhs (unblocks all NSV measures; v3 complete)  
✓ Tax-Basis = NSV excl. tax, MRP incl. tax (v3.1 complete)  
✓ More Retail Records = Retained as valid; no dedup  
✓ Brand Counter = BA Availability flag; Page 5 coverage active  
✓ State Reporting = Zone-level used; no state rollups

See **TAX_BASIS_RULING.md** and **Blocked_Measures.md** for full details.

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

### After Cost Structure Confirmation:

Once Finance provides CM2 formula + cost data:
1. Implement [CM2] / Contribution Margin 2 measures
2. Implement [Margin %] / [Gross Margin %] measures
3. Implement P&L block (Gross Profit, EBITDA, Net Profit)
4. Implement BA Profitability (once BA Headcount confirmed)
5. (Optional) Merge chain variants in Dim_Chain_Canonical
6. (Optional) Add State dimension + state-level rollups (if business approves City-State mapping)

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

**For tax-basis treatment:**
- See TAX_BASIS_RULING.md (comprehensive tax-basis documentation)

---

## Version & Branch Info

- **Branch:** claude/safe-powerbi-dashboard-rulings
- **Generated:** 2026-07-11
- **Version:** 3.1 (Tax-Basis Clarification: NSV excl. tax, MRP incl. tax)
- **Status:** Ready for implementation (tax-basis aware)
- **Previous version:** v3 (NSV unit confirmed as Lakhs)
- **Files in repo:** All in PowerBI/Safe_Blocks/ (9 files, 60+ pages specification + tax-aware code)

---

## Pre-Build Checklist

- [ ] Power BI Desktop 2024.11+ installed
- [ ] Monthly offtake CSV files available (Apr'24–Jun'26, 582 files)
- [ ] Read TAX_BASIS_RULING.md (understand NSV excl. tax vs MRP incl. tax)
- [ ] Read Build_In_PowerBI_Desktop_Guide.md (step-by-step instructions)
- [ ] Understand data model (PowerBI_Model_Spec.md)
- [ ] Understand report pages (PowerBI_Report_Page_Spec.md)
- [ ] Have QC_Validation_Checklist.md open (for final validation)
- [ ] Confirm understanding: NSV = without tax (Lakhs), MRP = with tax (rupees)

---

**Ready to build. Follow the guide. Estimated 2–3 hours. Tax-basis aware. Good luck!**

