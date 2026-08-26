# PBIP Production Readiness Report

**Frozen:** 2026-08-07  
**Branch:** `claude/primary-pipeline-allocation-fy27-l9bdf6`  
**Commit:** `91b66c3`  
**Automation Score:** 53.9% (v3.0 — corrected; `PowerBI/docs/AutomationScorecard.md`)  
**Power BI Desktop assembly status:** NOT PERFORMED (Linux container — Power BI Desktop is Windows-only)  

---

## Audit Legend

| Classification | Meaning |
|----------------|---------|
| **READY** | Asset exists, is complete, has been validated (code or simulation) |
| **WARNING** | Asset exists but has a known gap, unvalidated assumption, or pending decision |
| **BLOCKER** | Asset is missing, fundamentally incomplete, or blocks Desktop assembly |

---

## Section 1 — PBIP Asset Structure

### Power Query (25 files)

| Query | File | Classification | Notes |
|-------|------|----------------|-------|
| Q00 — Parameters | `PowerQuery/Q00_Parameters.pq` | WARNING | `pRootFolder` parameter avoids hardcoded paths. Not validated in Desktop. |
| Q01 — fnCombineFolder | `PowerQuery/Q01_fnCombineFolder.pq` | WARNING | Helper function; authored but not tested in Desktop. |
| Q10 — Fact Primary Sales | `PowerQuery/Q10_FactPrimarySales.pq` | WARNING | Deferred (0 rows — all primary via article CSVs now). Correctly documented. |
| Q11 — Fact Offtake Sales | `PowerQuery/Q11_FactOfftakeSales.pq` | WARNING | Authored; not validated in Desktop. |
| Q12 — Fact P&L | `PowerQuery/Q12_FactPnL.pq` | WARNING | Authored; not validated. |
| Q13 — Fact Nielsen | `PowerQuery/Q13_FactNielsen.pq` | WARNING | Authored; data folder empty (no Nielsen CSV). |
| Q14 — Fact TDP | `PowerQuery/Q14_FactTDP.pq` | WARNING | Authored; data folder empty (no TDP CSV). |
| Q15 — Fact Primary ShipTo | `PowerQuery/Q15_FactPrimaryShipTo.pq` | WARNING | Authored; not validated. |
| Q16 — Fact Primary Article | `PowerQuery/Q16_FactPrimaryArticle.pq` | READY | Governance columns implemented (Allocation Status, Provisional Flag, Approval Status, Negative Frac Flag). Python-validated. |
| Q20–Q40 — Dimensions | `PowerQuery/Q20_*.pq` … `Q40_*.pq` | WARNING | All 14 dimension queries authored; none validated in Desktop. |
| Q41 — Dist Cont Weights | `PowerQuery/Q41_DistContWeights.pq` | WARNING | XLSX source removed; P1→P4 chain implemented. Python-validated. Not run in Desktop. |

**Section 1 summary:** 1 READY, 24 WARNING, 0 BLOCKER  
**Blocking issue:** None in the PQ files themselves. All queries are structurally present. Desktop assembly required to validate data flow end-to-end.

---

### DAX Measures (14 files)

| File | Classification | Notes |
|------|----------------|-------|
| `DAX/00_DateTable.dax` | WARNING | Fiscal calendar with THE ONE FY RULE. Authored; not loaded in Desktop. |
| `DAX/01_CoreMeasures.dax` | WARNING | NSV, MRP, Qty, Growth measures. Authored; not loaded. |
| `DAX/02_PrimaryAllocation.dax` | WARNING | 8 allocation measures (Dist NSV, Allocated NSV, etc.). Authored; Python-logic verified. |
| `DAX/03_ForecastMeasures.dax` | WARNING | TY target measures. Authored; not loaded. |
| `DAX/04_OfftakeMeasures.dax` | WARNING | Offtake NSV, Qty, Store coverage. Authored; not loaded. |
| `DAX/05_ShareMeasures.dax` | WARNING | Nielsen share measures. Authored; not loaded. |
| `DAX/06_DQMeasures.dax` | WARNING | 14 DQ measures incl. `Primary Negative Frac Flag`, `Primary Negative Frac Rows`. Authored; not loaded. |
| `DAX/07_DistributionMeasures.dax` | WARNING | TDP, weighted distribution. Authored; not loaded. |
| `DAX/08_PromoMeasures.dax` | WARNING | Promo spend, ROI. Authored; not loaded. |
| `DAX/09_CMRatioMeasures.dax` | WARNING | CM1%, CM2%. Authored; not loaded. |
| `DAX/10_ComparisonMeasures.dax` | WARNING | YoY, QoQ comparison. Authored; not loaded. |
| `DAX/11_InsightsMeasures.dax` | WARNING | Narrative KPIs. Authored; not loaded. |
| `DAX/12_TOT_Measures.dax` | WARNING | 3-tier TOT% logic. GST cutover date has hardcoded fallback (`DATE(2025,9,22)`) inside COALESCE — low risk. Authored; calculated columns require Desktop to create. |
| `DAX/13_CM2_Measures.dax` | WARNING | CM2 = NSV − P&L Expenses. Calculated columns (`Resolved Chain`, `Resolved Brand`) require Desktop. Authored; not loaded. |

**Section 2 summary:** 0 READY, 14 WARNING, 0 BLOCKER  
**Blocking issue:** `DAX/12_TOT_Measures.dax` and `DAX/13_CM2_Measures.dax` define calculated columns on Fact tables — these require Desktop/Tabular Editor to create before the dependent measures can load. This is a known Desktop assembly prerequisite, not an authoring error.

---

### Seed Data (16 CSVs)

| File | Classification | Notes |
|------|----------------|-------|
| `SeedData/Mapping/DistCont_*.csv` | READY | Primary ShipTo weights — SHA256 verified |
| `SeedData/Mapping/CustCode_Chain_Map.csv` | READY | Customer code→chain lookup |
| `SeedData/Masters/GST_Rate_QC_Table.csv` | READY | TOT% fallback rates |
| `SeedData/Masters/GST_Config.csv` | READY | GST cutover date config |
| `SeedData/Masters/PL_Expense_Input.csv` | READY | CM2 expense inputs |
| 11 other master CSVs | WARNING | Present; not validated in Desktop join |

**Section 3 summary:** 5 READY, 11 WARNING, 0 BLOCKER

---

### Raw Data Folders

| Folder | Status | Classification | Notes |
|--------|--------|----------------|-------|
| `RawDataFolders/Offtake_Monthly/` | 2 CSVs (Apr-26, May-26) | WARNING | Partial coverage — historical offtake CSVs pre-Apr-26 not present |
| `RawDataFolders/Nielsen/` | EMPTY | **BLOCKER** | Nielsen CSV required for Market Share tab |
| `RawDataFolders/TDP/` | EMPTY | **BLOCKER** | TDP monthly CSV required for Distribution tab |
| `RawDataFolders/Primary_Article/` | 15 CSVs (May-25–Jun-26) | READY | All 15 months present; SHA256 spot-checked |

**Section 4 summary:** 1 READY, 1 WARNING, 2 BLOCKER

---

## Section 2 — Finance Decision Dependencies

| Decision | Status | Impact on PBIP |
|----------|--------|----------------|
| Jun'26 distributor allocation (Decision 1) | **PENDING** | Q41 source path, `Approval Status` column value in Q16 |
| Negative Cont% treatment (Decision 2) | **PENDING** | `Primary Negative Frac Flag` behavior in Q16 + DAX/06 |

Both decisions must be resolved before the PBIP assets can be certified as production-ready. The current `Q16` implementation correctly isolates both conditions under governance columns — no rework is needed after Finance decides; only a config parameter change and a Refresh.

---

## Section 3 — PBIP Project File

**Status:** NOT PRESENT  
**Classification:** WARNING (not BLOCKER for the text assets; BLOCKER for Desktop assembly)  

The PBIP project file (`.pbip` / `.pbixproj` / report model definition) has not been created. Power BI Desktop generates this file when a report is saved in PBIP format. No `.pbix` is committed (gitignored per CLAUDE.md).

**Impact:** All 25 PQ queries and 14 DAX files exist as standalone text but have not been assembled into a working Power BI model. Desktop assembly (following `PowerBI/docs/Desktop_Assembly_Checklist.md`) is the required next step. This is a manual process — Power BI Desktop is Windows-only and unavailable in this Linux container.

---

## Section 4 — Documentation Assets

| Document | Classification | Notes |
|----------|----------------|-------|
| `DataModel.md` | READY | Full star schema with 9 dims, 7 facts, 34 relationships |
| `DataDictionary.md` | READY | All canonical column definitions |
| `DistributorPrimaryAllocation_Logic.md` | READY | Complete allocation methodology |
| `Finance_Approval_Decision_Log.md` | WARNING | Two decisions PENDING |
| `Jun26_Provisional_Allocation.md` | READY | Jun'26 gap documented with fallback coverage |
| `Desktop_Assembly_Checklist.md` | WARNING | References stale commit `2725b80` — should be `91b66c3` |
| `AutomationScorecard.md` | READY | v3.0 corrected arithmetic |
| `PBIX_Build_Guide.md` | READY | Step-by-step assembly guide |
| `RefreshGuide.md` | READY | Monthly refresh procedures |
| `Nielsen_Source_Requirement.md` | READY | Documents the supply gap |
| `TDP_Definition_Decision.md` | WARNING | TDP metric definition pending confirmation |
| `ServiceReadiness.md` | WARNING | Service deployment not started |
| `PageLayouts.md` | READY | 18 pages specified |
| `ExportAndVisualSettings.md` | READY | Visual standards documented |
| `SIS_Reconciliation.md` | READY | SIS reconciliation methodology |

**Section 5 summary:** 11 READY, 4 WARNING, 0 BLOCKER

---

## Section 5 — Automation Scorecard Summary (v3.0)

| Domain | Score | Classification |
|--------|-------|----------------|
| Data Ingestion | 48.3% | WARNING |
| Power Query | 73.8% | WARNING |
| Data Model & DAX | 66.7% | WARNING |
| Report Pages & UX | 25.0% | WARNING |
| Reconciliation & QC | 63.8% | READY (Python) / WARNING (Desktop) |
| Refresh & Deployment | 28.3% | WARNING |
| **TOTAL** | **53.9%** | **WARNING** |

---

## Section 6 — PBIP Production Readiness Verdict

**Overall PBIP status: WARNING — NOT PRODUCTION READY**

| Category | Count | Classification |
|----------|-------|----------------|
| READY items | 18 | — |
| WARNING items | 54 | Require Desktop validation |
| BLOCKER items | 2 | Nielsen CSV, TDP CSV |

**Primary blockers (in priority order):**

1. **No Desktop assembly performed** — 25 PQ queries and 14 DAX files are unvalidated in Power BI Desktop. This is the single most impactful gap.
2. **Nielsen CSV absent** — Market Share tab will have no FY27+ data.
3. **TDP CSV absent** — TDP KPIs unavailable.
4. **Finance decisions pending** — Two governance decisions must be resolved before production certification.

**Next required action:** Schedule Power BI Desktop assembly session (Windows environment required). Follow `PowerBI/docs/Desktop_Assembly_Checklist.md` (updating stale commit reference first). Estimated effort: 2–3 days for a skilled Power BI developer with the guidance documents.
