# Power BI MT Offtake Dashboard — Build Package v1

**Build Package for Local Power BI Desktop Implementation**

---

## QUICK START

1. **Download this package**
2. **Open `LOCAL_POWERBI_DESKTOP_BUILD_GUIDE.md`** — Follow step-by-step
3. **Open Power BI Desktop** → Create blank report
4. **Copy-paste Power Query** from `PowerQuery_Complete_DataModel.pq`
5. **Copy-paste DAX measures** from `DAX_Complete_Measure_Library.dax`
6. **Build 10 pages** using `PAGE_BY_PAGE_BUILD_STEPS.md`
7. **Validate** using `POWERBI_QC_VALIDATION_TEMPLATE.csv`
8. **Save** as `MT_Offtake_Dashboard_Interim_MRP_NSV_Qty.pbix`

**Estimated time:** 5–7 hours (Pages 1–8, 9 held for Finance Q1-Q2)

---

## PACKAGE CONTENTS

### Core Build Files
- **PowerQuery_Complete_DataModel.pq** — All Power Query scripts (copy-paste into Power BI)
- **DAX_Complete_Measure_Library.dax** — All 84 DAX measures (copy-paste into Power BI)
- **PowerBI_10Page_DetailedSpec.md** — Original 10-page specification (reference)
- **Build_Dashboard_Complete_Checklist.md** — Original build checklist (reference)
- **DataModel_Schema_Diagram.md** — Star schema documentation (reference)

### Build Guides
- **LOCAL_POWERBI_DESKTOP_BUILD_GUIDE.md** ← **START HERE**
- **PAGE_BY_PAGE_BUILD_STEPS.md** — Detailed visual specs for each page

### Business Rules & Context
- **BUSINESS_RULES_FINAL.md** — All business rules (NSV, MRP, tax basis, etc.)
- **KNOWN_BLOCKERS_AND_PENDING_DECISIONS.md** — What's blocked and why

### Quality Control
- **POWERBI_QC_VALIDATION_TEMPLATE.csv** — QC checklist for validating every visual

### Reference Docs (Support)
- **README_BUILD_PACKAGE.md** — This file

---

## WHAT IS THIS PACKAGE?

**This package contains everything needed to build the MT Offtake Dashboard in your local Power BI Desktop.**

It includes:
- ✅ Production-ready Power Query scripts
- ✅ Production-ready DAX measures (84 total)
- ✅ Complete page-by-page visual specifications
- ✅ Step-by-step build guide
- ✅ Business rules documentation
- ✅ QC validation framework

**It does NOT include:**
- ❌ Binary `.pbix` file (must be created locally in Power BI Desktop)
- ❌ Pre-built data files (you provide source CSVs)
- ❌ Sample data (you load from your data sources)

---

## KEY DECISIONS IMPLEMENTED

### ✅ NSV is Excluding Tax
- **Every NSV display** labeled "(Excl Tax)"
- **NSV in Crores** = Source NSV Lakhs ÷ 100

### ✅ MRP is Including Tax
- **Every MRP display** labeled "(Incl Tax)"
- **MRP in Crores** = MRP Sales Value ÷ 10,000,000

### ✅ NSV vs MRP Comparisons Include Tax-Basis Warning
- When both shown together: "Different tax bases; QC/realization only"
- Cannot be directly compared without context

### ✅ No State-Level Reporting
- Zone-only approach (P6 canonical zones)
- No State slicer or State rollups

### ✅ No BA Profitability Yet
- Page 7: BA-availability segmentation only (not cost/break-even)
- Page 9: Readiness QC only (awaiting Finance Q2 formula)

### ✅ More Retail Rows Retained
- 13,661 duplicate rows included (not deduped)
- Treated as valid source data

### ✅ June'26 Marked Partial
- 78,111 rows from 16 chains only
- Watermarked on all relevant pages

### ✅ CM2 / Profitability Provisional
- All measures marked ⚠️ PROVISIONAL
- Awaiting Finance Q1-Q2 answers
- Page 9 is placeholder only

---

## BEFORE YOU START

### Required Files (Provide These)
You must supply your own source data:
- `Fact_Offtake_Safe.csv` (4.21M rows)
- `Dim_Month.csv` (27 rows)
- `Dim_Chain_Raw.csv` (34 rows)
- `Dim_Zone.csv` (37 rows)
- `Dim_Category.csv` (50–150 rows)
- `Expense_Assumptions_Input.xlsx` (seed data, 3–5 rows minimum)

### Power BI Setup
- Power BI Desktop 2024.11+
- 500 MB free disk space
- 8 GB RAM (16 GB recommended)
- Stable network connection (for Excel external source)

---

## BUILD FLOW

### Phase 1: Environment Setup (30 min)
→ See **LOCAL_POWERBI_DESKTOP_BUILD_GUIDE.md**, SECTION 1

### Phase 2: Load Data Model (90 min)
→ See **LOCAL_POWERBI_DESKTOP_BUILD_GUIDE.md**, SECTION 2

### Phase 3: Create DAX Measures (45 min)
→ See **LOCAL_POWERBI_DESKTOP_BUILD_GUIDE.md**, SECTION 3

### Phase 4: Build Pages 1–8 (240 min = 4 hours)
→ See **PAGE_BY_PAGE_BUILD_STEPS.md** (detailed specs for each page)

**Build order (fastest to longest):**
1. Page 1: Executive Overview (30 min)
2. Page 5: Zone Performance (35 min)
3. Page 3: Brand Performance (40 min)
4. Page 4: Category Performance (40 min)
5. Page 2: Chain Performance (45 min)
6. Page 8: Data Explorer (60 min)
7. Page 6: Store Performance (60 min)
8. Page 7: BA Availability View (90 min) ⚠️ Most complex

### Phase 5: Build Page 10 (50 min)
→ Page 10: QC & Reconciliation (data quality dashboard)

### Phase 6: Build Page 9 Placeholder (10 min)
→ Page 9: Profitability / CM2 Readiness QC (placeholder only, awaiting Finance Q1-Q2)

### Phase 7: Test & Validate (60 min)
→ See **LOCAL_POWERBI_DESKTOP_BUILD_GUIDE.md**, SECTION 6  
→ Use **POWERBI_QC_VALIDATION_TEMPLATE.csv** for detailed checks

### Phase 8: Save & Finalize (15 min)
→ See **LOCAL_POWERBI_DESKTOP_BUILD_GUIDE.md**, SECTION 7

---

## KEY RULES TO REMEMBER

### Rule 1: Tax Basis (CRITICAL)
- NSV (Excl Tax) and MRP (Incl Tax) cannot be directly compared
- Every comparison must include warning
- **Violating this rule invalidates the build** ❌

### Rule 2: No State Reporting
- Zone-only analysis (P6 canonical zones)
- No State slicer, no State rollups
- **Verify: All pages use Zone, not State**

### Rule 3: Provisional Labels on CM2/Profitability
- Page 7: CM2 measures marked ⚠️ PROVISIONAL (yellow background)
- Page 9: QC placeholder only (no active profitability visuals)
- **No store closure decisions until Finance Q2 confirmed**

### Rule 4: More Retail Retained
- 13,661 rows are valid source data
- NO deduplication in Power Query
- All totals include these rows

### Rule 5: June'26 Partial Watermark
- 78,111 rows from 16 chains only
- Must show warning on all relevant pages
- Users must know data is incomplete

---

## WHAT HAPPENS WHEN FINANCE CONFIRMS Q1-Q2?

### Finance Q1 (COGS Units)
→ Update [COGS Cost Cr Provisional] formula  
→ Re-run Page 7 profitability

### Finance Q2 (CM2 Formula)
→ Update [CM2 Cr Provisional], [CM2 Pct Provisional] formulas  
→ **Unlock Page 9** with profitability visuals  
→ Finalize store classifications  
→ Remove "Provisional" labels (become final)

**See KNOWN_BLOCKERS_AND_PENDING_DECISIONS.md for full flow**

---

## TROUBLESHOOTING

### "4.21M rows taking too long to load"
→ Wait 3–5 minutes on first load (normal for large fact table)  
→ Or reduce to 12 months temporarily (change Power Query filter)

### "Measure shows #DIV/0! error"
→ Check table name matches exactly (case-sensitive)  
→ Verify relationship exists in Model view  
→ See BUSINESS_RULES_FINAL.md for measure definitions

### "Slicer doesn't filter charts"
→ Model tab → Manage Relationships  
→ Verify 5 relationships exist and are Active  
→ Check relationship direction

### "Refresh is very slow"
→ Ensure Expense_Assumptions_Input.xlsx is local (not on network)  
→ Close Excel file before refreshing Power BI  
→ Check network connection stability

→ **Full troubleshooting:** See LOCAL_POWERBI_DESKTOP_BUILD_GUIDE.md, SECTION 9

---

## QC VALIDATION

**After building all pages, use POWERBI_QC_VALIDATION_TEMPLATE.csv to validate:**

- [ ] All KPI values within expected ranges
- [ ] All slicers filter correctly
- [ ] Tax-basis labels present everywhere
- [ ] June'26 warnings visible
- [ ] No State dimensions
- [ ] CM2 measures marked PROVISIONAL
- [ ] Page 9 is QC placeholder only
- [ ] All 84 measures in Fields pane
- [ ] 5 relationships in Model view
- [ ] Dashboard loads < 30 seconds
- [ ] Slicer click updates visuals < 2 seconds

→ **Track results in CSV template**

---

## FINAL VALIDATION BEFORE HANDOFF

**Confirm these before declaring build complete:**

- [ ] NSV labeled "(Excl Tax)" on every page ✅
- [ ] MRP labeled "(Incl Tax)" on every page ✅
- [ ] NSV/MRP comparison includes tax warning ✅
- [ ] NO State slicer or rollups ✅
- [ ] NO BA profitability visuals (Page 7 ⚠️, Page 9 placeholder) ✅
- [ ] NO More Retail deduplication ✅
- [ ] June'26 marked "Partial" (78,111 rows) ✅
- [ ] Brand Counter = BA availability only ✅
- [ ] Page 9 is readiness QC only ✅
- [ ] All 84 measures present ✅
- [ ] All visuals render without errors ✅
- [ ] All slicers work ✅
- [ ] Refresh succeeds ✅

→ Once all ✅, you're ready for team review

---

## NEXT STEPS AFTER BUILD

### For You (Local Build)
1. Open Power BI Desktop
2. Follow LOCAL_POWERBI_DESKTOP_BUILD_GUIDE.md
3. Build pages 1–10 using PAGE_BY_PAGE_BUILD_STEPS.md
4. Validate using POWERBI_QC_VALIDATION_TEMPLATE.csv
5. Save .pbix file locally
6. Take screenshots of key pages
7. Return .pbix + screenshots for review

### For Finance (Answering Q1-Q2)
- **Q1:** COGS factor units (%, ratio, per-unit?)
- **Q2:** CM2 formula + tax-basis treatment
- Once answered → Update Power BI, unlock Page 9

### For Operations (Providing Data)
- **Store Master:** Store_Code → Chain → Zone mapping
- **BA Deployment Dates:** When BA deployed/left each store
- Once provided → Page 6-7 becomes fully actionable

---

## CONTACT & QUESTIONS

**For build guidance:** See LOCAL_POWERBI_DESKTOP_BUILD_GUIDE.md  
**For business rules:** See BUSINESS_RULES_FINAL.md  
**For blockers:** See KNOWN_BLOCKERS_AND_PENDING_DECISIONS.md  
**For QC:** Use POWERBI_QC_VALIDATION_TEMPLATE.csv

---

**Package Version:** v1  
**Commit:** e19c467  
**Branch:** claude/safe-powerbi-dashboard-rulings  
**Status:** Production-ready for local Power BI Desktop build

**Good luck! 🚀**

