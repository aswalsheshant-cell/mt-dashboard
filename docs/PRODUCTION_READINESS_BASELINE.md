# Production Readiness Baseline

**Frozen:** 2026-08-07  
**Branch:** `claude/primary-pipeline-allocation-fy27-l9bdf6`  
**Commit:** `91b66c3` — Phase A+B: Roll drill engine to all tabs; fix pre-existing test debt  
**Working tree status:** Clean (no uncommitted changes)  
**Sprint authority:** Chief Enterprise Data Architect / Principal Data Engineer / Analytics Engineering Lead / Finance Reconciliation Specialist / Software Quality Governor / Release Manager  

---

## A. Repository Inventory

### Tracked source files (relevant to data pipeline)

| Directory | Files | Notes |
|-----------|-------|-------|
| `scripts/` | `build_dashboard_data.py`, `release_gate.py`, `demo_release_gate_blocking.py`, `qc_dashboard.py`, `split_*.py` | Core build + QC pipeline |
| `scripts/test_*.py` | 5 test files, 167 tests | Full suite — see Section D |
| `dashboard/` | `index.html`, `data.js`, 3× `*.min.js` vendored libs | Self-contained offline app |
| `PowerBI/PowerQuery/` | 25 `.pq` files | All PQ steps as text (PBIP-first) |
| `PowerBI/DAX/` | 14 `.dax` files | All measures as text |
| `PowerBI/SeedData/` | 16 master CSVs | Reference/mapping data |
| `PowerBI/RawDataFolders/Offtake_Monthly/` | 2 offtake CSVs | Partial — see Section E |
| `PowerBI/docs/` | 16 markdown docs | Architecture + governance |
| `.github/workflows/qc.yml` | 1 CI workflow | py_compile + pytest + gate |
| `CHANGELOG.md` | 1 file | Phase history |

### Gitignored (not tracked)

- `*.xlsx`, `*.xlsb`, `*.pbix` — source workbooks and Power BI project file
- All raw source files (primary, offtake, universe, promo workbooks)

---

## B. Sprint Scope (Release Candidate Provenance)

The RC (`91b66c3`) incorporates these cumulative phases since branch creation:

| Phase | Commit | Description |
|-------|--------|-------------|
| Phase 3A/3B/3C | `2381250` | Drill engine pilot — Overview + Primary |
| Phase A+B | `91b66c3` | Drill engine on all remaining tabs; fix test debt |

**Prior foundation commits:**
- `c977d59` — Release Gate wired into build pipeline (Stage 1 integration)
- Earlier commits — FY27 primary allocation, chain allocation, PBIP docs

---

## C. Technical Debt Catalogue

| ID | Severity | Description | File | Status |
|----|----------|-------------|------|--------|
| TD-01 | P1 | `negative_frac_treatment_status = "APPROVED"` in default config but Finance decision is PENDING | `scripts/release_gate.py:186` | Open — Finance decision required |
| TD-02 | P1 | `jun26_allocation_status = "PROVISIONAL"` — Finance decision open since 2026-08-06 | `scripts/release_gate.py:193` | Open — Finance decision required |
| TD-03 | P2 | `Desktop_Assembly_Checklist.md` references stale commit `2725b80` (should be `91b66c3`) | `PowerBI/docs/Desktop_Assembly_Checklist.md` | Documentation debt |
| TD-04 | P2 | No Power BI Desktop assembly performed — PBIP assets not validated end-to-end | `PowerBI/` | Architecture constraint (Linux container) |
| TD-05 | P2 | `PowerBI/RawDataFolders/Nielsen/` empty — Nielsen source not supplied | `PowerBI/docs/Nielsen_Source_Requirement.md` | Data dependency gap |
| TD-06 | P2 | `PowerBI/RawDataFolders/TDP/` empty — TDP source not supplied | `PowerBI/docs/TDP_Definition_Decision.md` | Data dependency gap |
| TD-07 | P3 | Article-level chain allocation (Step 3 per `DistributorPrimaryAllocation_Logic.md`) — blocked pending File 2 | `scripts/build_dashboard_data.py` | Known limitation, documented |
| TD-08 | P3 | `PowerBI/DAX/12_TOT_Measures.dax` GST Cutover Date hardcoded fallback `DATE(2025,9,22)` | `PowerBI/DAX/12_TOT_Measures.dax` | Low risk — COALESCE covers it |
| TD-09 | P3 | `AutomationScorecard.md` v2.0 arithmetic errors (corrected in v3.0) | `PowerBI/docs/AutomationScorecard.md` | Fixed |

---

## D. Test Suite Baseline

**Suite command:**
```bash
python -m pytest scripts/test_pipeline.py scripts/test_chain_consolidation.py \
  scripts/test_june_fallback.py scripts/test_dashboard_disclosures.py \
  scripts/test_release_gate.py -v
```

**Result at RC commit `91b66c3`:**

| Metric | Count |
|--------|-------|
| Tests collected | 167 |
| PASSED | 167 |
| FAILED | 0 |
| ERRORS | 0 |
| Warnings | 1 (PytestRemovedIn10Warning — harmless) |

**Runtime:** ~2.26 s

**Improvement vs Phase 3 Baseline (`docs/PHASE3_REGRESSION_BASELINE.md`):**

| Metric | Phase 3 Baseline | RC Baseline | Delta |
|--------|-----------------|-------------|-------|
| PASSED | 151 | 167 | +16 |
| FAILED | 1 | 0 | −1 ✓ |
| ERRORS | 15 | 0 | −15 ✓ |

All 16 previously broken tests now pass. No regressions introduced.

---

## E. Known Data Dependency Gaps

These are not engineering defects — they are documented data supply gaps:

| Gap | Impact | Documented |
|-----|--------|------------|
| Primary FY25/26 source workbooks absent | Full rebuild not possible from this container | Expected — gitignored |
| Chain Offtake Master absent | Offtake block reads from pre-built `data.js` only | Expected — gitignored |
| Universe MT.xlsx absent | Distribution block reads from pre-built `data.js` only | Expected — gitignored |
| Promo Master absent | Promo block reads from pre-built `data.js` only | Expected — gitignored |
| `offtake_store_article_Jun_26.csv` absent | Jun-26 BC status = BLOCKED; months exclude Jun-26 | Tested — test_dashboard_disclosures.py confirms |
| Nielsen source absent | Market Share tab shows no data for FY27 | `Nielsen_Source_Requirement.md` |
| TDP source absent | TDP KPIs absent | `TDP_Definition_Decision.md` |

---

## F. Finance Decision Status (as at 2026-08-07)

| Decision | Description | Status | Blocking |
|----------|-------------|--------|----------|
| Decision 1 | Jun'26 distributor-to-chain allocation (Option A/B/C) | **PENDING** | Production approval |
| Decision 2 | Negative Cont% treatment (Retain vs Zero-floor) | **PENDING** | Production approval |

**Critical discrepancy (TD-01):** `release_gate.py` default config sets `negative_frac_treatment_status = "APPROVED"` but the Finance Approval Decision Log shows Decision 2 is PENDING. The gate will pass on this field with the default config even though Finance has not approved. This must be corrected or Finance must formally ratify the "RETAIN" default before production deployment.

---

## G. CI Pipeline Status

**Workflow:** `.github/workflows/qc.yml`  
**Triggers:** push + pull_request on branch  
**Steps:**
1. `py_compile` check on `build_dashboard_data.py`
2. `pytest` (5 test files)
3. `demo_release_gate_blocking.py`
4. `qc_dashboard.py`
5. Upload `release_gate_report.json` as artifact

**Current status:** All steps pass on RC `91b66c3`.

---

## H. Browser Validation Status

**Method:** Playwright + Chromium (`/opt/pw-browsers/chromium`), HTTP server on `dashboard/`  
**States tested:** 12 tabs × 4 FY filter states (FY25, FY26, FY27, All-FY) = 48 combinations  
**Result:** All 48 states pass — no NaN, no `undefined`, no broken cards, no JS errors  
**Drill engine:** Confirmed functional on all 10 applicable tabs  

---

## I. Production Readiness Verdict (Baseline)

| Gate | Status | Blocker |
|------|--------|---------|
| Test suite | PASS (167/167) | — |
| Browser matrix | PASS (48/48) | — |
| Finance Decision 1 (Jun'26) | PENDING | Yes — cannot designate as Production Approved without Finance sign-off |
| Finance Decision 2 (Neg Frac) | PENDING | Yes — gate config `APPROVED` contradicts Finance log |
| PBIP Desktop Assembly | NOT PERFORMED | Architecture — Power BI Desktop is Windows-only |
| Nielsen/TDP data | ABSENT | Data supply — not an engineering issue |

**Preliminary verdict:** `CONDITIONALLY READY` — pending Finance decisions and config correction.

Full verdict in `docs/PRODUCTION_READINESS_REPORT.md` (Phase 10 deliverable).
