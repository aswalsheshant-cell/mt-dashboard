# Power BI Automation Scorecard

**Version:** 3.0 — corrected arithmetic  
**Date:** 2026-08-06  
**Branch:** `claude/primary-pipeline-allocation-fy27-l9bdf6`  
**Commit:** `6ea2c08`  
**Prior claimed score (v2.0):** 68% *(see arithmetic note below)*  
**Corrected current score (v3.0):** **54%** (calculated; no Desktop work has been done)

---

## Arithmetic Correction Notice (v2.0 → v3.0)

Version 2.0 of this scorecard contained an arithmetic error in Domain 1 (Data Ingestion):

| | v2.0 (claimed) | v3.0 (corrected) |
|--|--|--|
| Domain 1 average | 0.595 | **0.483** |
| Domain 1 sum | *(implied 5.355)* | **4.350** ← actual |
| Domain 1 weighted contribution | 11.9% | **9.7%** |
| Total score | 56.2% (table) / "68% est." | **53.9%** |

The sum 0.85+0.85+0.85+0.70+0.70+0+0+0+0.40 = 4.35, divided by 9 components = **0.483**, not 0.595.
All other domain calculations were arithmetically correct. The "68%" in v2.0 was an aspirational
estimate, not a calculated value. The table in v2.0 itself summed to 56.2% (also containing the
Domain 1 error); the true sum of the domain contributions is **53.9%**.

No Desktop assembly has been performed since commit `6ea2c08`. No tier upgrades are possible without
Desktop validation. Score remains at 53.9% for this session.

---

## Scoring Method

Five-tier classification per component:

| Tier | Label | Score factor |
|------|-------|-------------|
| A | Validated in production (Desktop + Service) | 1.00 |
| B | Implemented and validated (code/sim, not Desktop) | 0.85 |
| C | Implemented, not yet validated in Desktop | 0.70 |
| D | Partially implemented | 0.40 |
| E | Not started / blocked | 0.00 |

---

## Domain Breakdown

### 1 — Data Ingestion (weight 20%)

| Component | Tier | Score | Notes |
|-----------|------|-------|-------|
| Primary Article CSVs (15 months, May'25–Jun'26) | B | 0.85 | Present; SHA256 spot-checked |
| ShipTo CSV (May'25–May'26) | B | 0.85 | Present; SHA256 verified |
| Approved Patch CSV (Oct'25, 27 rows) | B | 0.85 | Present; SHA256 verified |
| Offtake CSVs (Apr'26, May'26 only) | C | 0.70 | 2 months; full history needed |
| SeedData Masters (16 files) | C | 0.70 | Present; not validated in Desktop |
| Nielsen CSV | E | 0.00 | Empty folder; manual upload required |
| TDP Monthly CSV | E | 0.00 | Empty folder |
| Primary Weekly CSV | E | 0.00 | Empty; MVP deferred |
| Jun'26 Approved DistCont patch | D | 0.40 | Provisional fallback only; Finance approval pending |

**Domain sum:** 0.85+0.85+0.85+0.70+0.70+0+0+0+0.40 = **4.35**  
**Domain average:** 4.35 / 9 = **0.483 (48.3%)**  
**Domain contribution:** 0.20 × 0.483 = **9.7%**

---

### 2 — Power Query (weight 20%)

| Component | Tier | Score | Notes |
|-----------|------|-------|-------|
| Q41 Dist Cont Weights (XLSX removed, P1→P4 chain) | B | 0.85 | Python-validated; PBIX not assembled |
| Q16 Fact Primary Article (governance columns) | B | 0.85 | Code-reviewed; not run in Desktop |
| Q00 Parameters (pRootFolder, no hardcoded paths) | C | 0.70 | Authored; not tested in Desktop |
| Q10 Fact Primary Sales (deferred, 0 rows) | C | 0.70 | Correctly deferred; documented |
| Q11 Fact Offtake Sales | C | 0.70 | Authored; not validated in Desktop |
| Q12–Q15 Fact P&L / Nielsen / TDP / ShipTo | C | 0.70 | Authored; not validated |
| Q20–Q40 Dimension queries | C | 0.70 | Authored; not validated |
| Q01 fnCombineFolder helper | C | 0.70 | Authored; not validated |

**Domain sum:** 0.85+0.85+0.70+0.70+0.70+0.70+0.70+0.70 = **5.90**  
**Domain average:** 5.90 / 8 = **0.738 (73.8%)**  
**Domain contribution:** 0.20 × 0.738 = **14.8%**

---

### 3 — Data Model and DAX (weight 20%)

| Component | Tier | Score | Notes |
|-----------|------|-------|-------|
| Star schema design (DataModel.md) | C | 0.70 | Fully documented; not yet built in Desktop |
| Relationships specification (34 relationships) | C | 0.70 | Exact list in DataModel.md; not yet created |
| Hierarchies (Geography, Product, Time) | C | 0.70 | Specified in DataModel.md; not yet created |
| Date Table / Fiscal Calendar (DAX) | C | 0.70 | Authored in 00_DateTable.dax |
| Core measures (01_CoreMeasures.dax) | C | 0.70 | Authored; not loaded in Desktop |
| Dist allocation measures (07) — 8 new measures | C | 0.70 | Authored; Python-logic verified |
| DQ measures (06) — 14 measures incl. Neg Frac | C | 0.70 | Authored; not loaded in Desktop |
| Forecast / P&L / Nielsen / TDP / SIS measures | C | 0.70 | Authored; not loaded |
| TOT% / CM2 calculated columns + measures | D | 0.40 | Require Desktop column creation before measures load |

**Domain sum:** 0.70×8 + 0.40 = **6.00**  
**Domain average:** 6.00 / 9 = **0.667 (66.7%)**  
**Domain contribution:** 0.20 × 0.667 = **13.3%**

---

### 4 — Report Pages and UX (weight 15%)

| Component | Tier | Score | Notes |
|-----------|------|-------|-------|
| Page designs (PageLayouts.md — 18 pages) | D | 0.40 | Fully specified; not yet built in Desktop |
| Governance banners (6 banners) | D | 0.40 | Specified with exact text; not yet placed |
| Theme (HonasaMT_Theme.json) | C | 0.70 | File present; not yet applied to PBIX |
| Global slicer bar | E | 0.00 | Not yet built |
| Conditional formatting | E | 0.00 | Not yet built |
| Drill-down hierarchies on visuals | E | 0.00 | Not yet placed |

**Domain sum:** 0.40+0.40+0.70+0+0+0 = **1.50**  
**Domain average:** 1.50 / 6 = **0.250 (25.0%)**  
**Domain contribution:** 0.15 × 0.250 = **3.8%**

---

### 5 — Reconciliation and QC (weight 15%)

| Component | Tier | Score | Notes |
|-----------|------|-------|-------|
| Primary NSV reconciliation (Python) | B | 0.85 | 0.0000% variance confirmed |
| Dist NSV reconciliation (Python) | B | 0.85 | 0.0000% variance confirmed |
| Frac normalisation validation (Python) | B | 0.85 | Max deviation 2.22e-16 |
| Negative Frac QC (Python) | B | 0.85 | 157 rows, −₹0.21 L identified |
| Provisional allocation identification | B | 0.85 | 10,236 rows, ₹1,376.49 L |
| Unmapped row tracking | B | 0.85 | 3 rows, ₹0.15 L |
| Desktop reconciliation checks | E | 0.00 | PBIX not assembled |
| Automation tests A–E | E | 0.00 | Cannot run without Desktop |

**Domain sum:** 0.85×6 + 0 + 0 = **5.10**  
**Domain average:** 5.10 / 8 = **0.638 (63.8%)**  
**Domain contribution:** 0.15 × 0.638 = **9.6%**

---

### 6 — Refresh and Deployment (weight 10%)

| Component | Tier | Score | Notes |
|-----------|------|-------|-------|
| Raw data folder structure (watch pattern) | B | 0.85 | Correctly structured; CSV drop triggers refresh |
| RefreshGuide.md | B | 0.85 | Documented |
| Desktop refresh (Refresh All) | E | 0.00 | PBIX not assembled |
| Gateway configuration | E | 0.00 | Not configured |
| Power BI Service publish | E | 0.00 | Not published |
| Scheduled refresh | E | 0.00 | Not configured |

**Domain sum:** 0.85+0.85+0+0+0+0 = **1.70**  
**Domain average:** 1.70 / 6 = **0.283 (28.3%)**  
**Domain contribution:** 0.10 × 0.283 = **2.8%**

---

## Score Summary (v3.0 — corrected)

| Domain | Weight | Component avg | Weighted contribution |
|--------|--------|---------------|-----------------------|
| Data Ingestion | 20% | 48.3% | **9.7%** |
| Power Query | 20% | 73.8% | **14.8%** |
| Data Model & DAX | 20% | 66.7% | **13.3%** |
| Report Pages & UX | 15% | 25.0% | **3.8%** |
| Reconciliation & QC | 15% | 63.8% | **9.6%** |
| Refresh & Deployment | 10% | 28.3% | **2.8%** |
| **TOTAL** | **100%** | | **53.9%** |

**Breakdown by validation status:**

| Category | % |
|----------|---|
| Validated automation (Tier A — production) | 0.0% |
| Implemented + code-validated (Tier B) | 30.7% |
| Implemented, not Desktop-validated (Tier C) | 20.5% |
| Partially implemented (Tier D) | 2.7% |
| Manual / not started / blocked (Tier E) | 46.1% |
| **Remaining gap to 100%** | **46.1%** |

---

## Gap to 100%

| Gap | Action required | Score impact (est.) |
|-----|----------------|---------------------|
| PBIX assembly + queries refreshing in Desktop | Complete Phase A–C of Desktop_Assembly_Checklist.md | +6% |
| Data model built + DAX loaded | Complete Phase D–G | +8% |
| Report pages built | Complete Phase H–I | +8% |
| Full Desktop reconciliation | Complete Phase J | +5% |
| Automation tests A–E | Complete Phase K | +4% |
| Power BI Service deployment | Complete Phase M | +5% |
| Jun'26 Finance approval | Decision required | +2% |
| Offtake historical data (pre-Apr'26) | Load historical offtake CSVs | +3% |
| Nielsen CSV upload | Finance/Nielsen to supply data | +3% |
| TDP Monthly data | Business to supply data | +2% |
| **Total gap** | | **~46%** |

---

## Score History

| Date | Version | Score | Key change |
|------|---------|-------|-----------|
| Pre-Aug-2026 | — | ~47% | Baseline (XLSX dependency broken, no governance DAX) |
| 2026-08-06 | v2.0 | 68% est. *(arithmetic error)* | Q41 rewritten, Q16 extended, 22 DAX measures |
| 2026-08-06 | v3.0 | **54%** | Corrected Domain 1 arithmetic; same actual work |
| *(pending)* | — | ~60% | PBIX assembled + queries refresh in Desktop |
| *(pending)* | — | ~68% | DAX loaded + data model built in Desktop |
| *(pending)* | — | ~76% | Report pages built + reconciliation in Desktop |
| *(pending)* | — | ~80% | Automation tests A–E passed |
| *(pending)* | — | ~86%+ | Service deployed; Finance approvals received |
| *(pending)* | — | ~92%+ | Nielsen/TDP/Offtake historical data loaded |
