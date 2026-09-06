# Changelog

All notable changes to the MT Dashboard project are recorded here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased] — branch `claude/primary-pipeline-allocation-fy27-l9bdf6`

### Phase Q — Automation Scorecard v3.0 (corrected arithmetic) (2026-08-06)

Updated `PowerBI/docs/AutomationScorecard.md` to v3.0:

- Identified arithmetic error in v2.0 Domain 1 (Data Ingestion): sum 4.35 ÷ 9 = 0.483, not 0.595 as previously stated
- Corrected Domain 1 contribution from 11.9% to 9.7%
- Corrected total score from "68% est." to **54%** (verified calculated)
- Added breakdown: Tier B 30.7% / Tier C 20.5% / Tier D 2.7% / Tier E 46.1%
- Gap to 100% correctly calculated as 46% (was stated as ~32% in v2.0)
- Score history updated with corrected milestones
- No tier upgrades are possible without Power BI Desktop assembly

| Domain | Weight | Component avg | Weighted contribution |
|--------|--------|---------------|-----------------------|
| Data Ingestion | 20% | 48.3% | 9.7% |
| Power Query | 20% | 73.8% | 14.8% |
| Data Model & DAX | 20% | 66.7% | 13.3% |
| Report Pages & UX | 15% | 25.0% | 3.8% |
| Reconciliation & QC | 15% | 63.8% | 9.6% |
| Refresh & Deployment | 10% | 28.3% | 2.8% |
| **TOTAL** | | | **53.9%** |

### Phase A Asset Re-verification (2026-08-06, commit 6ea2c08)

All key assets re-verified at current HEAD:

| Asset | SHA256 (first 16 chars) | Status |
|-------|------------------------|--------|
| `41_DistContWeights.pq` | `2992f65489a14f46` | MATCH ✓ |
| `16_Fact_PrimaryArticle.pq` | `21cd6db6a62b0204` | MATCH ✓ |
| `06_DataQuality_Measures.dax` | `6326d0bedc358c34` | MATCH ✓ |
| `07_PrimaryAllocation_Measures.dax` | `c37fa48db9353bbe` | MATCH ✓ |
| `DistCont_Patch_Approved_2026-07-04.csv` | `ab91405435dbd670` | MATCH ✓ |
| `Primary_ShipTo_FY25-26_to_May26.csv` | `b9dd91fd4c224b9d` | MATCH ✓ |

Additional confirmations:
- XLSX dependency in Q41: `0` functional references (comment-only mention, line 17)
- `DistCont_Patch_Proposed.csv` not referenced in any PQ file ✓
- `Jun26Fallback` step present in Q41 ✓ · `AddFrac` normalisation step present ✓
- `Provisional – Jun'26 gap; awaiting Finance approval` still active in Q41 ✓
- `FillSrcType` / `FillApproval` / `FillProv` / `DistAllocStatus` / `DirectWithGov` all present in Q16 ✓
- `Primary Negative Frac Rows` / `Primary Negative Frac NSV` / `Primary Negative Frac Flag` in DAX 06 ✓
- `Dist NSV – Approved Patch` / `Has Provisional Allocation` / `Dist Allocation Coverage %` in DAX 07 ✓
- 25 PQ files, 14 DAX files, 15 Primary Article CSVs, 2 Offtake CSVs, 16 SeedData Masters confirmed ✓

Desktop assembly environment blocked: Linux container. Power BI Desktop is Windows-only.

### Documentation — Phase 16–18 Governance Package (2026-08-06)

New documents completing the handoff package for Power BI Desktop assembly:

| File | Purpose |
|------|---------|
| `PowerBI/docs/Finance_Approval_Decision_Log.md` | Formal Finance decision log for Jun'26 allocation and negative-frac treatment; fields for Finance to complete |
| `PowerBI/docs/ServiceReadiness.md` | Power BI Service configuration requirements; Gateway, licence, workspace, and schedule specifications |
| `PowerBI/docs/Desktop_Assembly_Checklist.md` | Operational step-by-step checklist for the PBIX builder; phases A–M with exact checkbox items and governance banner text |
| `PowerBI/docs/AutomationScorecard.md` | Weighted automation scorecard v2.0: prior 56% → current 68%; gap analysis to 100%; score history |

### Phase 0 / Phase 1 Asset Verification (2026-08-06)

All assets confirmed at commit `2725b80`:

| Asset | SHA256 (first 16 chars) |
|-------|------------------------|
| `41_DistContWeights.pq` | `2992f65489a14f46` |
| `16_Fact_PrimaryArticle.pq` | `21cd6db6a62b0204` |
| `06_DataQuality_Measures.dax` | `6326d0bedc358c34` |
| `07_PrimaryAllocation_Measures.dax` | `c37fa48db9353bbe` |
| `DistCont_Patch_Approved_2026-07-04.csv` | `ab91405435dbd670` |
| `Primary_ShipTo_FY25-26_to_May26.csv` | `b9dd91fd4c224b9d` |

Data source counts confirmed: 15 Primary Article CSVs (May'25–Jun'26), 2 Offtake CSVs (Apr'26–May'26), 16 SeedData masters, 25 PQ files, 14 DAX files.

### Phase 18 Final Verdicts (2026-08-06)

| Verdict | Status |
|---------|--------|
| PBIX | **NOT READY** — Desktop assembly required |
| Finance approval | **PENDING** — Decision Log issued; awaiting Finance response |
| Negative reversals | **RETAINED FOR RECONCILIATION** — pending Finance zero-floor decision |
| Power BI Service | **SERVICE READY FOR CONFIGURATION** — blocked by PBIX assembly |
| Overall | **POWER BI AUTOMATION PARTIALLY READY** — repository-side complete; Desktop assembly required |

---

### Power BI — Query 41 (Dist Cont Weights) — COMPLETE REWRITE

**Breaking change: removed XLSX dependency**
- Deleted reference to `Dist_primary_cont_based_on_secondary_MOM.xlsx` (gitignored,
  never committed; caused `DataSource.Error` on every new machine)
- Replaced with two committed CSV sources implementing a P1 → P4 priority chain:

| Priority | Source | Format | Coverage |
|----------|--------|--------|----------|
| P1 | `SeedData/Mapping/DistCont_Patch_Approved_2026-07-04.csv` | 0–100 ÷ 100 | Oct'25 backfill (27 rows) |
| P2 | `RawDataFolders/Primary_ShipTo_Monthly/Primary_ShipTo_FY25-26_to_May26.csv` | 0–1 | May'25–May'26 Dist. rows |
| P3 | Nearest-month fallback (May'26 → Jun'26) | Auto-generated | Jun'26 gap (Provisional) |
| P4 | "Unmapped Chain" sentinel | Auto | No ShipTo match |

- P1 overrides P2 for same (ShipTo × Brand × Month) keys via `JoinKind.LeftAnti`
- Fraction normalisation: `Frac = RawCont / GroupSum` per key; sums to 1 (max deviation: 2.22e−16)
- Jun'26 fallback: 160 Q41 rows → 10,236 article rows → ₹1,376.49 L (8.7% of Dist NSV); tagged Provisional
- 9 governance columns output: Source File, Source Type, Approval Status, Allocation Method,
  Provisional Flag, Fallback Flag, Fallback Source Month, Load Timestamp, Raw Pct Sum

### Power BI — Query 16 (Fact Primary Article) — EXTENDED

- Expanded `ExpandedW` to include `Source Type`, `Approval Status`, `Provisional Flag` from Q41
- Added fill steps for unmatched Dist rows: `FillSrcType`, `FillApproval`, `FillProv`
- Added `DistAllocStatus` step: `Allocation Status` ∈ {Allocated, Provisional, Unmapped}
- Added `DirectWithGov`: Direct rows now carry `Source Type = null`, `Provisional Flag = false`,
  `Allocation Status = "Direct"` — consistent schema across both paths
- Removed `Approval Status` from DistSwap (internal governance; not needed in fact table)

### Power BI — DAX: `06_DataQuality_Measures.dax` — EXTENDED

Added Primary Article DQ section (11 new measures):
- `Primary Missing Month/Chain/Brand`, `Primary Blank NSV`, `Primary Negative NSV`
- `Primary Unmapped Dist`, `Primary Provisional Alloc`, `Primary Provisional NSV`
- `Primary Dist Coverage %`, `Primary Total DQ Issues`, `Primary Article Total Rows`
- `Primary Data Health %`
- `Primary Negative Frac Rows`, `Primary Negative Frac NSV`, `Primary Negative Frac Flag`
  (QC flag for 8 ShipTo CSV reversal rows → 157 article rows → −₹0.2093 L)

### Power BI — DAX: `07_PrimaryAllocation_Measures.dax` — EXTENDED

Added 8 new measures after `Allocation Health Check`:
- `Dist NSV – Approved Patch`, `Dist NSV – ShipTo CSV`, `Dist NSV – Provisional Fallback`,
  `Dist NSV – Unmapped` (NSV by source tier)
- `Dist Allocation Coverage %` (target: ≥ 95%)
- `Has Provisional Allocation` (disclosure card text)
- `Unmapped Dist Rows` (target: 0)
- `Dist Row Count`

### Power BI — Query 10 (Fact Primary Sales) — COMMENT ONLY

Added MVP DEFERRED marker: weekly primary folder is empty; not an MVP blocker.

### Power BI — QuickSetup

- `AllDAX_Consolidated.txt`: appended all new DAX measures from files 06 and 07

### Documentation — New Files

| File | Purpose |
|------|---------|
| `PowerBI/docs/Jun26_Provisional_Allocation.md` | Jun'26 gap analysis, distributor list, Finance actions |
| `PowerBI/docs/PBIX_Build_Guide.md` | Step-by-step Power BI Desktop assembly guide (MVP 1.0) |
| `PowerBI/docs/Nielsen_Source_Requirement.md` | Nielsen RMS data requirements; current workaround |
| `PowerBI/docs/TDP_Definition_Decision.md` | Option A/B/C for TDP definition; business sign-off needed |

### Reconciliation (Verified, 2026-08-06)

- Q41 rows: 2,083 (27 Approved Patch + 1,896 ShipTo CSV + 160 Jun'26 fallback)
- Allocation groups: 892; frac sum max deviation: 2.22×10⁻¹⁶ ✓
- Dist NSV In = Dist NSV Out = ₹15,756.23 L (0.0000% variance) ✓
- Total Primary NSV In = Out = ₹46,560.34 L ✓
- Unmapped: ₹0.15 L across 3 rows (0.001%) — never hidden
- Negative Frac QC: 157 rows, −₹0.2093 L, 4 distributors (reversal entries — Finance review pending)

### Known Deferred (not MVP blockers)

| Item | Status |
|------|--------|
| Weekly primary data | Empty folder; Q10 deferred |
| Nielsen market share | Manual slide values only; CSV upload required |
| TDP (ACV-weighted) | Presence proxy in use; business sign-off needed |
| Jun'26 DistCont approval | Provisional fallback active; Finance approval pack issued |
| PBIX file assembly | Requires Power BI Desktop (Windows GUI) |

---

## Initial state (before this branch)

- Q41 referenced a gitignored XLSX; failed on any new machine
- Q16 had no governance columns (Source Type, Provisional Flag, Allocation Status)
- No DAX measures for Dist allocation source breakdown or Primary Article DQ
- No documentation for Jun'26 gap, build process, Nielsen requirements, or TDP definition

## [v1.4.0] - 2026-09-05 (Infrastructure & YoY Update)
### Added
- **Phase 4.2 YoY Infrastructure:** Automated monthly data archiving (`archive/`) and YoY growth calculations.
- **YoY UI Badges:** Added dynamic growth indicators (green/red) to KPI cards on the dashboard.
- **RBC Data Block:** Ingested 12,011 Reliance Brand Counter records mapping 6 zones and 5 brands.
- **Dashboard QC Suite:** Added comprehensive automated data validation workflow.

### Changed
- **CI/CD Standardization:** Upgraded all GitHub Actions workflows to Python 3.11 with pip caching.
- **Concurrency Safety:** Added concurrency controls to state-modifying workflows to prevent deployment race conditions.

### Security
- **CodeQL Remediation:** Fixed 7 DOM XSS vulnerabilities by replacing `document.write` with safe DOM APIs.
- **Path Traversal:** Hardened subprocess inputs in data loading scripts using `os.path.realpath()`.
