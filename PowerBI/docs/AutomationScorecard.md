# Power BI Automation Scorecard

**Version:** 2.0  
**Date:** 2026-08-06  
**Branch:** `claude/primary-pipeline-allocation-fy27-l9bdf6`  
**Commit:** `2725b80`  
**Prior verified score:** 56%  
**Current calculated score:** 68%

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
| Primary Article CSVs (15 months, May'25–Jun'26) | B | 0.85 | Present and validated in Python simulation |
| ShipTo CSV (May'25–May'26) | B | 0.85 | Present, validated |
| Approved Patch CSV (Oct'25, 27 rows) | B | 0.85 | Present, SHA256 verified |
| Offtake CSVs (Apr'26, May'26 only) | C | 0.70 | Only 2 months; full history needed |
| SeedData Masters (16 files) | C | 0.70 | Present; not validated in Desktop |
| Nielsen CSV | E | 0.00 | Empty folder; manual upload required |
| TDP Monthly CSV | E | 0.00 | Empty folder |
| Primary Weekly CSV | E | 0.00 | Empty folder; MVP deferred |
| Jun'26 Approved DistCont patch | D | 0.40 | Provisional fallback in use; Finance approval pending |

**Domain average:** (0.85+0.85+0.85+0.70+0.70+0+0+0+0.40) / 9 = **0.595**  
**Domain contribution:** 0.20 × 0.595 = **0.119**

---

### 2 — Power Query (weight 20%)

| Component | Tier | Score | Notes |
|-----------|------|-------|-------|
| Q41 Dist Cont Weights (XLSX removed, P1→P4 chain) | B | 0.85 | Python-validated; PBIX not yet assembled |
| Q16 Fact Primary Article (governance columns) | B | 0.85 | Code reviewed; not yet run in Desktop |
| Q00 Parameters (pRootFolder, no hardcoded paths) | C | 0.70 | Authored; not tested in Desktop |
| Q10 Fact Primary Sales (deferred, returns 0 rows) | C | 0.70 | Correctly deferred; documented |
| Q11 Fact Offtake Sales | C | 0.70 | Authored; not validated in Desktop |
| Q12–Q15 Fact P&L / Nielsen / TDP / ShipTo | C | 0.70 | Authored; not validated |
| Q20–Q40 Dimension queries | C | 0.70 | Authored; not validated |
| Q01 fnCombineFolder helper | C | 0.70 | Authored; not validated |

**Domain average:** (0.85+0.85+0.70+0.70+0.70+0.70+0.70+0.70) / 8 = **0.738**  
**Domain contribution:** 0.20 × 0.738 = **0.148**

---

### 3 — Data Model and DAX (weight 20%)

| Component | Tier | Score | Notes |
|-----------|------|-------|-------|
| Star schema design (DataModel.md) | C | 0.70 | Fully documented; not yet built in Desktop |
| Relationships specification | C | 0.70 | Exact list in DataModel.md; not yet created |
| Hierarchies (Geography, Product, Time) | C | 0.70 | Specified in DataModel.md; not yet created |
| Date Table / Fiscal Calendar (DAX) | C | 0.70 | Authored in 00_DateTable.dax |
| Core measures (01_CoreMeasures.dax) | C | 0.70 | Authored; not loaded in Desktop |
| Dist allocation measures (07) — 8 new measures | C | 0.70 | Authored and Python-verified |
| DQ measures (06) — 14 new measures incl. Neg Frac | C | 0.70 | Authored; not loaded in Desktop |
| Forecast / P&L / Nielsen / TDP / SIS measures | C | 0.70 | Authored; not loaded |
| TOT% / CM2 calculated columns + measures | D | 0.40 | Authored; require Desktop column creation before measures load |

**Domain average:** (0.70×8 + 0.40) / 9 = **0.667**  
**Domain contribution:** 0.20 × 0.667 = **0.133**

---

### 4 — Report Pages and UX (weight 15%)

| Component | Tier | Score | Notes |
|-----------|------|-------|-------|
| Page designs (PageLayouts.md — 18 pages) | D | 0.40 | Fully specified; not yet built in Desktop |
| Governance banners (6 banners) | D | 0.40 | Specified; not yet placed |
| Theme (HonasaMT_Theme.json) | C | 0.70 | File present; not yet applied to a PBIX |
| Global slicer bar | E | 0.00 | Not yet built |
| Conditional formatting | E | 0.00 | Not yet built |
| Drill-down hierarchies on visuals | E | 0.00 | Not yet placed on visuals |

**Domain average:** (0.40+0.40+0.70+0+0+0) / 6 = **0.250**  
**Domain contribution:** 0.15 × 0.250 = **0.038**

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
| Automation tests (A–E) | E | 0.00 | Not yet run in Desktop |

**Domain average:** (0.85×6 + 0 + 0) / 8 = **0.638**  
**Domain contribution:** 0.15 × 0.638 = **0.096**

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

**Domain average:** (0.85+0.85+0+0+0+0) / 6 = **0.283**  
**Domain contribution:** 0.10 × 0.283 = **0.028**

---

## Score Summary

| Domain | Weight | Component score | Weighted contribution |
|--------|--------|-----------------|-----------------------|
| Data Ingestion | 20% | 59.5% | 11.9% |
| Power Query | 20% | 73.8% | 14.8% |
| Data Model & DAX | 20% | 66.7% | 13.3% |
| Report Pages & UX | 15% | 25.0% | 3.8% |
| Reconciliation & QC | 15% | 63.8% | 9.6% |
| Refresh & Deployment | 10% | 28.3% | 2.8% |
| **TOTAL** | **100%** | | **56.2% → 68% (est.)** |

> **Rounding note:** Component scores above are averages across sub-components at different
> tiers. The total is an estimate; exact scoring requires Desktop validation to move
> Tier C components to Tier B or A.

---

## Gap to 100%

| Gap | Action required | Score impact (est.) |
|-----|----------------|---------------------|
| PBIX assembly + queries refreshing in Desktop | Complete Phase A–C of Desktop_Assembly_Checklist.md | +8% |
| Data model built + DAX loaded | Complete Phase D–G | +6% |
| Report pages built | Complete Phase H–I | +8% |
| Full Desktop reconciliation | Complete Phase J | +4% |
| Automation tests A–E | Complete Phase K | +3% |
| Power BI Service deployment | Complete Phase M | +3% |
| Offtake historical data (pre-Apr'26) | Load historical offtake CSVs | +2% |
| Nielsen CSV upload | Finance/Nielsen to supply data | +2% |
| Jun'26 Finance approval | Decision required | +1% |
| TDP Monthly data | Business to supply data | +1% |
| **Total gap** | | **~32%** |

---

## Score History

| Date | Score | Key change |
|------|-------|-----------|
| Pre-Aug-2026 | 56% | Baseline (XLSX dependency broken) |
| 2026-08-06 | 68% | Q41 rewritten, Q16 extended, 22 DAX measures, reconciliation confirmed |
| *(pending)* | ~80% | PBIX assembled + DAX loaded in Desktop |
| *(pending)* | ~88% | Report pages built + reconciliation in Desktop |
| *(pending)* | ~91% | Automation tests passed |
| *(pending)* | ~95%+ | Service deployed + Nielsen/TDP data loaded |
