# Modern Trade Analytics Platform — MT Dashboard

[![CI Status](https://github.com/aswalsheshant-cell/mt-dashboard/actions/workflows/qc.yml/badge.svg)](https://github.com/aswalsheshant-cell/mt-dashboard/actions)
[![Production Status](https://img.shields.io/badge/status-CONDITIONALLY%20READY-orange)](docs/PRODUCTION_READINESS_REPORT.md)
[![PPT Test Coverage](coverage.svg)](test_generate_ppt.py)

A self-contained offline analytics dashboard for Honasa / Mamaearth Modern Trade channel data, covering Primary (distributor) sales, Offtake (retail), P&L, Forecasts, and Executive Insights.

**Live Dashboard:** https://mt-dashboard.github.io

---

## Quick Start

### View the Dashboard

1. **Online:** Open [https://mt-dashboard.github.io](https://mt-dashboard.github.io) in your browser
2. **Offline:** Clone this repo, double-click `dashboard/index.html`
3. **No login required.** Data is embedded in `dashboard/data.js` (~14 MB)

### Build Data.js Locally

To rebuild the dashboard from source workbooks:

```bash
# Install dependencies
pip install -r requirements.txt

# Full rebuild from source workbooks
python scripts/build_dashboard_data.py \
  --src ~/MT-Sources \
  --out dashboard/data.js

# Or: Refresh only new Offtake data (faster)
python scripts/build_dashboard_data.py \
  --offtake-patch \
  --src ~/MT-Sources \
  --out dashboard/data.js

# Run quality gates
pytest scripts/test_pipeline.py -v
python scripts/qc_dashboard.py --data dashboard/data.js
```

See [`docs/SOURCES.md`](docs/SOURCES.md) for source file locations and archival strategy.

### Generate Executive 1-Pager PPT

Automatically generate professional executive presentations from MT Primary vs. Offtake data:

```bash
# Generate PPT locally
python generate_1pager_ppt.py
# Output: MT_Primary_vs_Offtake_1Pager.pptx (+ .pdf and .png auto-generated)

# Or push Excel template to trigger GitHub Actions auto-generation
git push origin main
```

**Features:**
- 16:9 widescreen executive layout
- RAG status coloring (Green/Amber/Red based on alignment gap)
- Zone performance table with 6 regions
- Automatic alerts and action items
- Multi-format output: PPTX, PDF, and 300 DPI PNG
- Idempotent (same input = same output)
- GitHub Actions auto-regeneration on Excel push

#### 📊 Latest Modern Trade Snapshot

![Modern Trade Snapshot](MT_Primary_vs_Offtake_1Pager.png?raw=true)

**Download formats:**
- 📥 [Download PPTX (Editable)](MT_Primary_vs_Offtake_1Pager.pptx?raw=true) — PowerPoint presentation
- 📄 [Download PDF (Print-Ready)](MT_Primary_vs_Offtake_1Pager.pdf?raw=true) — Executive summary
- 🖼️ [PNG (Mobile-Friendly)](MT_Primary_vs_Offtake_1Pager.png?raw=true) — Direct sharing

**Full documentation:** See [`AUTOMATED_PPT_GUIDE.md`](AUTOMATED_PPT_GUIDE.md)

---

## Repository Structure

```
dashboard/
  index.html         Single-file web app (12 tabs, filters, drill-down, exports)
  data.js            Generated ~14 MB JSON (DO NOT EDIT BY HAND)
  *.min.js           Vendored libraries (Chart.js, jsPDF, xlsx)

scripts/
  build_dashboard_data.py    🔑 Core: generates data.js from source workbooks
  release_gate.py            Production gates (10 mandatory/advisory checks)
  qc_dashboard.py            Data quality gate (validates data.js)
  split_*.py                 Helpers: split large Excel files by month
  test_*.py                  5 test suites; 167 tests total

PowerBI/
  PowerQuery/                25 Power Query scripts (text, git-tracked)
  DAX/                       14 DAX measures (text, git-tracked)
  SeedData/                  Mapping CSVs: GST rates, chain codes, expense input
  RawDataFolders/            Monthly source data (Offtake, Nielsen, TDP)
  QuickSetup/                Consolidated PQ+DAX paste-in for desktop

docs/
  PRODUCTION_READINESS_REPORT.md     🔑 Certification status & scorecard
  FINANCE_DECISION_PACK.md           Business decisions awaiting approval
  PRODUCTION_GAP_MATRIX.md           21 gaps: priority, owner, timeline
  SOURCES.md                         Source file locations & archival
  ROLLBACK.md                        Emergency data recovery procedure
  ON_CALL_GUIDE.md                   Production support playbook
  KPI_VALIDATION_FRAMEWORK.md        Finance reconciliation process
  [10+ other domain-specific docs]

.github/workflows/
  qc.yml                     CI pipeline (pytest + Release Gate + QC)
```

---

## The 12 Dashboard Tabs

| # | Tab | Purpose | FY Coverage | Data Source |
|---|-----|---------|-------------|-------------|
| 1 | **Data Explorer** | Ad-hoc drill into article-level detail | FY25–FY27 | Primary + Offtake |
| 2 | **Overview** | Executive summary; KPI cards & trends | FY25–FY27 | Pre-agg + article-level |
| 3 | **Primary** | Distributor sales by chain, brand, zone | FY25–FY27 | Primary workbook |
| 4 | **Offtake** | Retail channel volumes & trends | FY25–FY27 | Offtake workbook + monthly |
| 5 | **P&L** | Profitability, CM2%, expense tracking | FY25–FY26 | P&L workbook + Finance input |
| 6 | **Category & Pack** | Brand performance; pack mix | FY25–FY27 | Universe + Primary |
| 7 | **Forecast** | FY27 targets and budget alignment | FY27 | Finance targets |
| 8 | **Promo & Trade Spend** | Promotional allocations by brand | FY25–FY27 | Promo workbook |
| 9 | **Market Share** | Nielsen-based competitive position | FY25–FY26 | Nielsen data (awaiting FY27) |
| 10 | **Distribution** | Store count and expansion (TDP) | FY26 only | TDP data (awaiting FY27) |
| 11 | **Performance & Comparison** | KPI benchmarks; month-over-month | FY25–FY27 | All blocks |
| 12 | **Insights & Way Forward** | AI-generated insights + recommendations | FY25–FY27 | Insights block |

---

## Architecture & Key Concepts

### The One FY Rule

Indian financial years (Apr–Mar):
- **Apr–Dec** of calendar year Y → **FY(Y+1)**  
  *Example: Apr-26 → FY27*
- **Jan–Mar** of calendar year Y → **FY(Y)**  
  *Example: Mar-26 → FY26*

FY boundaries are computed from data dates; no hardcoded FY25/FY26-only logic.

See: [`scripts/build_dashboard_data.py` lines 42–93](scripts/build_dashboard_data.py#L42-L93) (`fy_tag_from_ym()`, etc.)

### Distributor-to-Chain Allocation

Distributor ("Dist.") rows that ship to multiple chains are re-split using contribution percentages from:
- **Primary_ShipTo_FY25-26_to_May26.csv** (May'25–May'26)
- **Jun'26** uses May'26 splits as fallback (PROVISIONAL; awaiting Finance Decision 1)

**Reconciliation Identity (must = 0%):**
```
Original Primary NSV 
= Allocated NSV (across chains) 
+ Blocked NSV (failed eligibility)
```

See: [`PowerBI/docs/DistributorPrimaryAllocation_Logic.md`](PowerBI/docs/DistributorPrimaryAllocation_Logic.md)

### Release Gate (10 Checks)

Before `data.js` is published, a production gate validates:

**Mandatory (block if failed):**
- G1: Schema validation  
- G2: Month/FY validation  
- G3: Primary reconciliation variance ≤ 0.01%  
- G6: Unmapped NSV % ≤ 2%  
- G10: Finance-approved rules status (Jun'26 allocation + negative fractions)

**Advisory (report but don't block):**
- G4-G5: Allocation fractions and coverage  
- G7: Reliance BC isolation  
- G8: TOT% fallback coverage ≤ 30%  
- G9: CM2% expense matching ≥ 80%

See: [`scripts/release_gate.py`](scripts/release_gate.py), [`scripts/demo_release_gate_blocking.py`](scripts/demo_release_gate_blocking.py)

### Reliance Brand Counter (BC)

Reliance BC volumes are stored separately (`D.reliance_bc` in `data.js`) to prevent 49% double-count risk. **BC is NOT included** in standard Offtake totals; drill engine cannot access BC.

See: [`PowerBI/docs/Reliance_BC_Isolation.md`](PowerBI/docs/Reliance_BC_Isolation.md)

### PBIP-First, Git-First

- All Power Query (25 files) and DAX (14 files) are stored as `.pq` and `.dax` text files in version control.
- `.pbix` files are **not committed** (gitignored); built manually in Power BI Desktop (Windows-only).
- Seed data (GST rates, mappings, expense input) is committed as `.csv` files.

Automation Score: **53.9%** (46.1% gap to full desktop validation).

See: [`PowerBI/docs/Desktop_Assembly_Checklist.md`](PowerBI/docs/Desktop_Assembly_Checklist.md), [`docs/PBIP_PRODUCTION_READINESS.md`](docs/PBIP_PRODUCTION_READINESS.md)

---

## Development Workflow

### Prerequisites

```bash
# Clone repo
git clone https://github.com/aswalsheshant-cell/mt-dashboard.git
cd mt-dashboard

# Install Python dependencies
pip install -r requirements.txt

# (Optional) Playwright for browser tests
python -m playwright install chromium
```

### Before Committing

```bash
# 1. Syntax check
python -m py_compile scripts/build_dashboard_data.py

# 2. Run all tests (5 test suites, 167 total tests)
pytest scripts/test_*.py -v

# 3. Run Release Gate demo (proof of fail-closed behavior)
python scripts/demo_release_gate_blocking.py

# 4. Run QC gate on data.js
python scripts/qc_dashboard.py --data dashboard/data.js
```

### Branching & PRs

1. Branch from `main`: `git checkout -b feature/your-feature`
2. Make changes; commit with descriptive messages
3. Open PR **as draft** (do not auto-merge)
4. CI runs automatically (pytest + gates)
5. Await manual review & approval before merge
6. **Never** force-push to main

See: [`.github/CODEOWNERS`](.github/CODEOWNERS) (when configured)

---

## Production Status

**Current:** CONDITIONALLY READY (6.15/10)

**Blockers (must resolve before production deployment):**
1. **Finance Decision 1 (Jun'26 Allocation)** — Due 2026-08-09 EOD  
   See: [`docs/FINANCE_DECISION_PACK.md`](docs/FINANCE_DECISION_PACK.md)

2. **Finance Decision 2 (Negative Fractions)** — Due 2026-08-09 EOD  
   See: [`docs/FINANCE_DECISION_PACK.md`](docs/FINANCE_DECISION_PACK.md)

3. **PBIP Desktop Assembly** — Windows-only, 2–3 days  
   See: [`PowerBI/docs/Desktop_Assembly_Checklist.md`](PowerBI/docs/Desktop_Assembly_Checklist.md)

**Outstanding Gaps:**
- 21 production gaps identified (3 CRITICAL, 8 MAJOR, 10 MINOR)
- See: [`docs/PRODUCTION_GAP_MATRIX.md`](docs/PRODUCTION_GAP_MATRIX.md) for full inventory

**Path to Production Ready:**
- Phase 1A: Gap governance ✅ (in progress)
- Phase 2: Finance decision closure (2026-08-09 EOD)
- Phase 3: Business validation (KPI reconciliation to Finance)
- Phase 4: Power BI validation (PBIP assembly & refresh)
- Phase 5: Production release & monitoring

See: [`docs/PRODUCTION_READINESS_REPORT.md`](docs/PRODUCTION_READINESS_REPORT.md)

---

## Key Documentation

| Document | Purpose | Audience |
|----------|---------|----------|
| [`docs/PRODUCTION_READINESS_REPORT.md`](docs/PRODUCTION_READINESS_REPORT.md) | Certification status & scorecard | Leadership, Finance |
| [`docs/FINANCE_DECISION_PACK.md`](docs/FINANCE_DECISION_PACK.md) | Business decisions requiring approval | Finance |
| [`docs/PRODUCTION_GAP_MATRIX.md`](docs/PRODUCTION_GAP_MATRIX.md) | 21 gaps: priority, owner, timeline | Engineering, Product |
| [`docs/SOURCES.md`](docs/SOURCES.md) | Source file locations & archival | Analytics Engineering |
| [`docs/ROLLBACK.md`](docs/ROLLBACK.md) | Emergency data recovery | On-call, Release Manager |
| [`docs/ON_CALL_GUIDE.md`](docs/ON_CALL_GUIDE.md) | Production support playbook | On-call, Release Manager |
| [`docs/KPI_VALIDATION_FRAMEWORK.md`](docs/KPI_VALIDATION_FRAMEWORK.md) | Finance reconciliation process | Finance, Analytics Engineering |
| [`PowerBI/docs/DataDictionary.md`](PowerBI/docs/DataDictionary.md) | All column definitions | Data analysts, Power BI users |
| [`PowerBI/docs/DataModel.md`](PowerBI/docs/DataModel.md) | Star schema, relationships, cardinality | Power BI developers |
| [`PowerBI/docs/RefreshGuide.md`](PowerBI/docs/RefreshGuide.md) | Monthly PBIP refresh process | Operations |

---

## Common Tasks

### "I want to rebuild data.js with a new month of Offtake data"

```bash
# Place new Offtake_Monthly_Store_FY27_<month>.xlsb in ~/MT-Sources/
python scripts/build_dashboard_data.py \
  --offtake-patch \
  --src ~/MT-Sources \
  --out dashboard/data.js

# Verify
python scripts/qc_dashboard.py --data dashboard/data.js
```

See: [`docs/SOURCES.md`](docs/SOURCES.md)

### "The dashboard crashed; data shows NaN"

Go to [`docs/ROLLBACK.md`](docs/ROLLBACK.md) immediately. Target recovery: < 30 minutes.

### "A Finance decision affects the allocation logic"

The decision framework and implementation steps are in:
- [`docs/FINANCE_DECISION_PACK.md`](docs/FINANCE_DECISION_PACK.md) (decision options)
- [`scripts/release_gate.py`](scripts/release_gate.py) (gate config)
- [`PowerBI/docs/Finance_Approval_Decision_Log.md`](PowerBI/docs/Finance_Approval_Decision_Log.md) (approval tracking)

### "I need to validate KPIs match Finance control totals"

See: [`docs/KPI_VALIDATION_FRAMEWORK.md`](docs/KPI_VALIDATION_FRAMEWORK.md)

### "I want to review the Release Gate logic"

Start with [`scripts/release_gate.py`](scripts/release_gate.py) (gate definitions) and [`scripts/demo_release_gate_blocking.py`](scripts/demo_release_gate_blocking.py) (demonstration of fail-closed behavior).

---

## Testing & Validation

```bash
# Full test suite (all 5 test modules, 167 tests)
pytest scripts/test_*.py -v

# Individual test modules
pytest scripts/test_pipeline.py                 # Pipeline logic
pytest scripts/test_chain_consolidation.py     # Chain allocation
pytest scripts/test_june_fallback.py           # Jun'26 fallback
pytest scripts/test_dashboard_disclosures.py   # Governance banners
pytest scripts/test_release_gate.py            # Gate enforcement

# Browser-based QC (checks for NaN, undefined, console errors)
python scripts/qc_dashboard.py --data dashboard/data.js

# Release Gate demonstration (5 scenarios)
python scripts/demo_release_gate_blocking.py
```

---

## Troubleshooting

### "Python: ModuleNotFoundError: No module named 'pandas'"

```bash
pip install -r requirements.txt
```

### "pytest: command not found"

```bash
pip install -r requirements.txt
python -m pytest scripts/test_*.py -v  # use python -m instead
```

### "Release Gate shows ⊘ BLOCKED for Jun'26 Allocation"

This is expected until Finance approves Decision 1 (due 2026-08-09 EOD).  
See: [`docs/FINANCE_DECISION_PACK.md`](docs/FINANCE_DECISION_PACK.md)

### "data.js is missing FY27 Offtake data"

FY27 offtake data is ingested monthly via `--offtake-patch`. If not present:
1. Check if source file is in `~/MT-Sources/Offtake/`
2. Verify Supply Chain has provided the monthly file
3. See: [`docs/SOURCES.md`](docs/SOURCES.md) for file location

### "Market Share tab shows no FY27 data"

Nielsen data not yet supplied. See: [`docs/SOURCES.md`](docs/SOURCES.md) for status.

---

## Support & Escalation

**Production Issue (dashboard down, data corrupt)?**  
→ See [`docs/ON_CALL_GUIDE.md`](docs/ON_CALL_GUIDE.md)

**Business Question (KPI divergence, reconciliation)?**  
→ Contact Finance + Analytics Engineering

**Feature Request / Enhancement?**  
→ Open GitHub issue (label: `feature` or `enhancement`)

**Bug Report?**  
→ Open GitHub issue (label: `bug`); include error log + screenshot

---

## License & Attribution

Internal Honasa / Mamaearth analytics platform. All source code, documentation, and data models are proprietary.

**Questions?** Reach out to the Analytics Engineering team.

---

**Last Updated:** 2026-08-08  
**Status Badge:** [![CI Status](https://github.com/aswalsheshant-cell/mt-dashboard/actions/workflows/qc.yml/badge.svg)](https://github.com/aswalsheshant-cell/mt-dashboard/actions)  
**Production Dashboard:** https://mt-dashboard.github.io
