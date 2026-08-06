# Changelog

All notable changes to the MT Dashboard project are recorded here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased] — branch `claude/primary-pipeline-allocation-fy27-l9bdf6`

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
