# Production Gap Matrix

**Frozen:** 2026-08-07  
**Branch:** `claude/primary-pipeline-allocation-fy27-l9bdf6`  
**Commit:** `ab6852b` (Production Readiness Sprint complete)  
**Assessment date:** 2026-08-07  
**Authority:** Chief Enterprise Engineer conducting Phase 1 assessment

---

## Executive Summary

**Total gaps identified:** 21  
**Critical blockers:** 3  
**Major issues:** 8  
**Minor issues:** 10  

| Severity | Count | Blocking Production | Examples |
|----------|-------|-------------------|----------|
| CRITICAL | 3 | YES | Finance decisions pending, PBIP not assembled, no local reproducibility |
| MAJOR | 8 | NO (but risky) | No requirements.txt, no deployment runbook, Nielsen/TDP absent |
| MINOR | 10 | NO | Documentation gaps, no rollback procedure, no on-call guide |

**Estimated effort to close all gaps:** 5–7 days  
**Estimated effort to close critical blockers only:** 2–3 days (Finance decisions + PBIP assembly)

---

## Gap Inventory

### CRITICAL BLOCKERS (Block Production Certification)

#### GAP-01: Finance Decision 1 (Jun'26 Allocation) Unresolved

| Attribute | Value |
|-----------|-------|
| **Gap ID** | GAP-01 |
| **Category** | Finance Governance |
| **Severity** | CRITICAL |
| **Business Impact** | Jun'26 distributor allocation status is PROVISIONAL (₹1,376.49 L, 10,236 rows). Cannot designate as approved without Finance sign-off. Risk: production dashboard shows unapproved allocations. |
| **Technical Impact** | Release Gate G10 cannot fully pass; Q16 `Approval Status` field cannot be set to "Finance-Approved" |
| **Evidence** | `PowerBI/docs/Finance_Approval_Decision_Log.md` — Status: PENDING (2026-08-06) |
| **Root Cause** | Finance approval workflow not yet triggered; Decision 1 options (A/B/C) require Finance evaluation |
| **Owner** | Finance |
| **Recommended Resolution** | Issue Finance Approval Pack; get Decision 1 signed off within 1 business day |
| **Estimated Effort** | 0.5 days (Finance review) + 0.5 days (Analytics implementation) |
| **Dependencies** | Decision 1 decision, `release_gate.py` config update, Q16 refresh |
| **Acceptance Criteria** | Finance approval recorded in Decision Log; config updated; `data.js` refreshed; G10 passes without notes |
| **Status** | OPEN |

---

#### GAP-02: Finance Decision 2 (Negative Cont% Treatment) Unresolved

| Attribute | Value |
|-----------|-------|
| **Gap ID** | GAP-02 |
| **Category** | Finance Governance |
| **Severity** | CRITICAL |
| **Business Impact** | 8 source rows with negative Cont% (157 article-level rows, −₹0.2093 L). Current treatment is RETAIN (visible in QC); Finance must decide whether to RETAIN or ZERO-FLOOR. Risk: production dashboard behavior on negatives is not Finance-approved. |
| **Technical Impact** | Release Gate G10 will pass with default config `"PROVISIONAL"` (recently corrected). Negative Frac Flag visible in DAX measures. |
| **Evidence** | `PowerBI/docs/Finance_Approval_Decision_Log.md` — Status: PENDING (2026-08-06); `release_gate.py:192` shows PROVISIONAL (corrected from APPROVED in latest commit) |
| **Root Cause** | Finance approval workflow not yet triggered; Decision 2 options (RETAIN vs ZERO-FLOOR) require evaluation |
| **Owner** | Finance |
| **Recommended Resolution** | Issue Finance Approval Pack; get Decision 2 signed off within 1 business day |
| **Estimated Effort** | 0.5 days (Finance review) + 0.25 days (if zero-floor chosen; zero if retain) |
| **Dependencies** | Decision 2 decision, `release_gate.py` config update (if needed), DAX refresh (if needed) |
| **Acceptance Criteria** | Finance approval recorded in Decision Log; `release_gate.py` config reflects decision; G10 passes without notes |
| **Status** | OPEN |

---

#### GAP-03: Power BI PBIP Not Assembled — Desktop Validation Incomplete

| Attribute | Value |
|-----------|-------|
| **Gap ID** | GAP-03 |
| **Category** | Power BI Readiness |
| **Severity** | CRITICAL |
| **Business Impact** | 25 PQ queries and 14 DAX files are authored but never assembled or validated in Power BI Desktop. Automation Score 53.9% — 46.1% of the platform is unvalidated. Risk: PBIP refresh may fail; measures may not calculate correctly; report pages cannot be built until model is validated. |
| **Technical Impact** | No .pbip file exists; PBIP cannot be published to Power BI Service; no refresh possible; no report pages can be built; Desktop validation may reveal model issues. |
| **Evidence** | `docs/PBIP_PRODUCTION_READINESS.md` — NOT PERFORMED; `PowerBI/docs/AutomationScorecard.md` — 53.9% score; `PowerBI/docs/Desktop_Assembly_Checklist.md` exists but not executed |
| **Root Cause** | Linux container environment — Power BI Desktop is Windows-only. No Windows machine scheduled for assembly. |
| **Owner** | Analytics Engineering + IT (Windows environment provisioning) |
| **Recommended Resolution** | Provision a Windows machine; follow `PowerBI/docs/Desktop_Assembly_Checklist.md` step-by-step; execute full Refresh; validate model; publish to Power BI Service. |
| **Estimated Effort** | 2–3 days (includes environment setup + assembly + validation) |
| **Dependencies** | Windows environment, Power BI Desktop (June 2025+), all PQ/DAX files present (locked) |
| **Acceptance Criteria** | PBIX file created; Refresh All succeeds; all 25 queries load; all 14 DAX measures calculate; Desktop screenshots confirm no errors; Dataset publishes to Service; Service refresh successful |
| **Status** | BLOCKED (environment) |

---

### MAJOR ISSUES (High Risk, No Go Until Resolved)

#### GAP-04: No Local Source Build Reproducibility

| Attribute | Value |
|-----------|-------|
| **Gap ID** | GAP-04 |
| **Category** | Build Reproducibility |
| **Severity** | MAJOR |
| **Business Impact** | Source workbooks (Primary, Offtake, Universe, Promo) are gitignored. A new team member cannot perform a full `build_dashboard_data.py --src ... --out dashboard/data.js` build from scratch. Production data.js is a "black box" with unknown source state. Risk: if source files are lost, cannot rebuild dashboard from audit trail. |
| **Technical Impact** | Full rebuild path is untested; `--src` parameter requires all four workbooks; no CI step validates build reproducibility |
| **Evidence** | `.gitignore` excludes `*.xlsx`, `*.xlsb`, `*.csv.gz`; `build_dashboard_data.py` reads from `--src <dir>` parameter with no fallback |
| **Root Cause** | Large binary files cannot be reasonably committed to Git; source workbooks kept in external storage (Google Drive, per CLAUDE.md) |
| **Owner** | Analytics Engineering + IT (artifact storage) |
| **Recommended Resolution** | Document the external source storage location; create a `SOURCES.md` file listing all required source files with SHA256 checksums; implement monthly archival of source files alongside each `data.js` build |
| **Estimated Effort** | 1 day (documentation + archive setup) |
| **Dependencies** | Source file location known and accessible; versioning strategy for sources |
| **Acceptance Criteria** | `SOURCES.md` exists; all required source files SHA256-documented; monthly archive process documented in Operations Model |
| **Status** | OPEN |

---

#### GAP-05: No Python Dependency File (requirements.txt)

| Attribute | Value |
|-----------|-------|
| **Gap ID** | GAP-05 |
| **Category** | Environment Reproducibility |
| **Severity** | MAJOR |
| **Business Impact** | Python dependencies are installed in CI via hardcoded `pip install pandas openpyxl pyxlsb pytest playwright`. No team member can reproduce the exact environment locally. Risk: local testing diverges from CI; subtle version mismatches. |
| **Technical Impact** | No local `python -m build_dashboard_data.py --src ... --out dashboard/data.js` possible without manual `pip install` commands; no version pinning; no control over transitive dependencies |
| **Evidence** | No `requirements.txt`, `setup.py`, or `pyproject.toml` in repo root; dependencies only in `.github/workflows/qc.yml` line 23 |
| **Root Cause** | Historically added to CI only; not formalized for local development |
| **Owner** | Analytics Engineering |
| **Recommended Resolution** | Create `requirements.txt` with pinned versions (pandas==X.X.X, openpyxl==X.X.X, etc.); add to `.gitignore` if generated, or commit if pinned; document local setup in `README.md` |
| **Estimated Effort** | 0.25 days |
| **Dependencies** | None |
| **Acceptance Criteria** | `requirements.txt` exists and is tracked; CI step uses `pip install -r requirements.txt`; local setup instructions in README work end-to-end |
| **Status** | OPEN |

---

#### GAP-06: No Deployment Runbook — PBIP to Power BI Service Undocumented

| Attribute | Value |
|-----------|-------|
| **Gap ID** | GAP-06 |
| **Category** | Operations Readiness |
| **Severity** | MAJOR |
| **Business Impact** | `PowerBI/docs/Desktop_Assembly_Checklist.md` covers PBIX creation, but there is no documented process for: refreshing PBIP in Service, scheduling refreshes, handling refresh failures, monitoring dataset health, managing incremental refresh, publishing reports. Risk: after PBIP is created, team does not know how to maintain it in production. |
| **Technical Impact** | No automation for PBIP refresh; no monitoring; no alerting; manual Power BI Service administration |
| **Evidence** | `PowerBI/docs/Desktop_Assembly_Checklist.md` is a local build guide; no `PowerBI_Service_Deployment_Guide.md` exists |
| **Root Cause** | PBIP project is not yet in Service; deployment process is premature to document |
| **Owner** | Analytics Engineering + IT (Power BI Service administration) |
| **Recommended Resolution** | Create `PowerBI/docs/PowerBI_Service_Deployment_Guide.md` covering: (a) dataset publishing, (b) refresh schedule setup, (c) incremental refresh configuration, (d) monitoring/alerting, (e) failure recovery, (f) report lifecycle. Template existing; ready after PBIP assembly. |
| **Estimated Effort** | 0.5 days (after PBIP exists) |
| **Dependencies** | PBIP Desktop assembly complete (GAP-03) |
| **Acceptance Criteria** | Guide exists with step-by-step procedures; refresh schedules documented; SLA for recovery defined; monitoring dashboard created |
| **Status** | BLOCKED (requires GAP-03) |

---

#### GAP-07: Nielsen Data Absent — Market Share Tab FY27 Unavailable

| Attribute | Value |
|-----------|-------|
| **Gap ID** | GAP-07 |
| **Category** | Data Supply |
| **Severity** | MAJOR |
| **Business Impact** | Nielsen CSV (market share data) is not supplied. Market Share tab (dashboard.html) will show no data for FY27. FY25/FY26 pre-aggregated data only. Risk: business cannot compare product performance to market share for FY27+. |
| **Technical Impact** | `PowerBI/RawDataFolders/Nielsen/` folder is empty; Q13 `Fact Nielsen` query has no data; `D.share` block in `data.js` is populated only from pre-aggregated workbook (FY25/FY26 only) |
| **Evidence** | `PowerBI/docs/Nielsen_Source_Requirement.md` — documents the requirement; `PowerBI/RawDataFolders/Nielsen/` — folder empty |
| **Root Cause** | Nielsen data not yet supplied by Finance/Nielsen; outside Analytics Engineering control |
| **Owner** | Finance + Nielsen partnership |
| **Recommended Resolution** | Contact Finance; confirm Nielsen data supply timeline; if urgent, consider manual upload; update `SOURCES.md` with Nielsen data SLA |
| **Estimated Effort** | 0 days (Analytics Engineering) — depends on external party |
| **Dependencies** | Nielsen data supply; `SOURCES.md` update |
| **Acceptance Criteria** | Nielsen monthly CSV files present in `PowerBI/RawDataFolders/Nielsen/`; Q13 loads without error; Market Share tab shows FY27 data; test suite passes |
| **Status** | BLOCKED (data dependency) |

---

#### GAP-08: TDP Data Absent — Distribution TDP KPIs Unavailable

| Attribute | Value |
|-----------|-------|
| **Gap ID** | GAP-08 |
| **Category** | Data Supply |
| **Severity** | MAJOR |
| **Business Impact** | TDP (Total Distribution Points) monthly CSV not supplied. Distribution tab cannot calculate TDP KPIs for FY27. FY25/FY26 data only. Risk: business cannot track store expansion for FY27+. |
| **Technical Impact** | `PowerBI/RawDataFolders/TDP/` empty; Q14 `Fact TDP` has no data; TDP measures in DAX fail silently (0 or blank) |
| **Evidence** | `PowerBI/docs/TDP_Definition_Decision.md` — documents the metric; folder empty |
| **Root Cause** | TDP data supply not yet started; outside Analytics Engineering control |
| **Owner** | Supply Chain / Business |
| **Recommended Resolution** | Confirm TDP data definition; establish supply SLA; update `SOURCES.md`; add placeholder in Documentation Handoff noting TDP unavailability for FY27 |
| **Estimated Effort** | 0 days (Analytics Engineering) |
| **Dependencies** | Business TDP supply; `SOURCES.md` update |
| **Acceptance Criteria** | TDP monthly CSV files present; Q14 loads; Distribution tab shows FY27 TDP data; test suite passes |
| **Status** | BLOCKED (data dependency) |

---

#### GAP-09: No Release Rollback Procedure Documented

| Attribute | Value |
|-----------|-------|
| **Gap ID** | GAP-09 |
| **Category** | Operational Resilience |
| **Severity** | MAJOR |
| **Business Impact** | If a `data.js` build fails validation after publication to GitHub Pages or Vercel, there is no documented rollback procedure. Risk: corrupt data serves to users until discovered; slow recovery. |
| **Technical Impact** | Git history allows revert, but steps are not documented; no automated rollback; no dashboard notification of rollback |
| **Evidence** | No `ROLLBACK.md` in `docs/`; no CI step for rollback; no monitoring dashboard |
| **Root Cause** | Operations processes not yet formalized |
| **Owner** | Release Manager + Analytics Engineering |
| **Recommended Resolution** | Create `docs/ROLLBACK.md` covering: (a) how to identify corrupt `data.js`, (b) git revert command, (c) re-publish to GitHub Pages, (d) notification to stakeholders. Integrate into Monthly Operations Runbook (Phase 6). |
| **Estimated Effort** | 0.5 days |
| **Dependencies** | Phase 6 Production Operating Model complete |
| **Acceptance Criteria** | `ROLLBACK.md` exists; procedure tested in staging; team trained; SLA for rollback defined (target < 30 min) |
| **Status** | OPEN |

---

#### GAP-10: No Business Validation Baseline — KPIs Not Reconciled to Finance

| Attribute | Value |
|-----------|-------|
| **Gap ID** | GAP-10 |
| **Category** | Business Reconciliation |
| **Severity** | MAJOR |
| **Business Impact** | No Finance-approved control totals provided for KPIs (Primary NSV, Offtake, CM2, TOT%, etc.). Dashboard values are pipeline-computed; business cannot confirm accuracy. Risk: business makes decisions on unvalidated KPIs. |
| **Technical Impact** | Release Gate does not have Finance control totals as reference; no cross-check possible; variance tolerance is an engineering guess (0.01%) not Finance-approved |
| **Evidence** | No KPI Validation Report exists; `docs/BUSINESS_LOGIC_REGISTRY.md` marks all threshold sources as POLICY APPROVAL REQUIRED |
| **Root Cause** | Business Validation phase (Phase 3 of Production Certification Sprint) not yet executed |
| **Owner** | Finance + Analytics Engineering |
| **Recommended Resolution** | Conduct Phase 3: Business Validation. For every KPI, obtain Finance control total from Finance-owned source; compare to dashboard value; document variance and reason. Create KPI Validation Report. |
| **Estimated Effort** | 1.5 days |
| **Dependencies** | Finance availability; access to Finance-owned control totals |
| **Acceptance Criteria** | KPI Validation Report exists; every KPI reconciled; variance < 0.5% explained; Finance sign-off on KPIs |
| **Status** | OPEN |

---

#### GAP-11: No On-Call Guide — Production Support Procedure Undefined

| Attribute | Value |
|-----------|-------|
| **Gap ID** | GAP-11 |
| **Category** | Operational Support |
| **Severity** | MAJOR |
| **Business Impact** | If the dashboard goes down (data.js corrupt, GitHub Pages/Vercel fails, Release Gate error), there is no documented escalation procedure. Risk: business does not know how to get help; SLA for recovery undefined. |
| **Technical Impact** | No monitoring; no alerting; no on-call rotation; no runbook for common failures |
| **Evidence** | No `ON_CALL_GUIDE.md`; no monitoring dashboard; no alerting rules in CI |
| **Root Cause** | Operations processes not formalized; no on-call infrastructure |
| **Owner** | Release Manager + IT |
| **Recommended Resolution** | Create `docs/ON_CALL_GUIDE.md` covering: (a) who to contact, (b) common failure modes, (c) diagnosis steps, (d) mitigation/recovery, (e) SLA targets. Integrate into Phase 6. Add CI monitoring for gate failures. |
| **Estimated Effort** | 1 day |
| **Dependencies** | Phase 6 complete |
| **Acceptance Criteria** | Guide exists; on-call contacts defined; SLA 4-hour recovery target; team trained; test drill passed |
| **Status** | OPEN |

---

### MINOR ISSUES (Low Risk, Improve UX/Maintainability)

#### GAP-12: No Automated Local Build Script

| Attribute | Value |
|-----------|-------|
| **Gap ID** | GAP-12 |
| **Category** | Developer Experience |
| **Severity** | MINOR |
| **Business Impact** | Low — affects developer productivity, not production. |
| **Technical Impact** | New team members must manually run `python scripts/build_dashboard_data.py --src <dir> --out dashboard/data.js`. No shell script to simplify this. |
| **Evidence** | No `build.sh` or `Makefile` in repo |
| **Root Cause** | Not prioritized during development |
| **Owner** | Analytics Engineering |
| **Recommended Resolution** | Create `build.sh` script with defaults; document in README |
| **Estimated Effort** | 0.1 days |
| **Acceptance Criteria** | `build.sh` exists; works on bash + zsh; documented |
| **Status** | OPEN |

---

#### GAP-13: No README.md — Project Documentation Sparse

| Attribute | Value |
|-----------|-------|
| **Gap ID** | GAP-13 |
| **Category** | Documentation |
| **Severity** | MINOR |
| **Business Impact** | Low — affects onboarding. |
| **Technical Impact** | New team members have no quick-start guide; must navigate wiki docs manually. |
| **Evidence** | No `README.md` in repo root; docs scattered across `PowerBI/docs/` and `docs/` |
| **Root Cause** | Not prioritized; docs are comprehensive but not discoverable |
| **Owner** | Analytics Engineering |
| **Recommended Resolution** | Create root `README.md` with: (a) project overview, (b) quick-start, (c) folder structure, (d) key concepts (FY rule, allocation, PBIP-first), (e) links to all docs |
| **Estimated Effort** | 0.25 days |
| **Acceptance Criteria** | README.md exists; covers key sections; team confirms it answers onboarding questions |
| **Status** | OPEN |

---

#### GAP-14: No Data Dictionary for data.js Object Schema

| Attribute | Value |
|-----------|-------|
| **Gap ID** | GAP-14 |
| **Category** | Documentation |
| **Severity** | MINOR |
| **Business Impact** | Low — affects developer understanding of dashboard JSON structure. |
| **Technical Impact** | Dashboard UI developers must reverse-engineer `data.js` schema. No formal schema definition. |
| **Evidence** | `PowerBI/docs/DataDictionary.md` documents Power BI columns, not `data.js` keys |
| **Root Cause** | Schema evolved with development; not formally documented |
| **Owner** | Analytics Engineering |
| **Recommended Resolution** | Create `docs/DATA_JS_SCHEMA.md` documenting every top-level key in `window.DASH` (meta, primary, offtake, pnl, forecast, share, universe, detail_meta, detail_records, alloc, reliance_bc) with data types and examples |
| **Estimated Effort** | 0.5 days |
| **Acceptance Criteria** | Schema doc exists; every key documented; examples provided; team confirms it matches actual data.js |
| **Status** | OPEN |

---

#### GAP-15: No Git Workflow Policy — Branch Protection Rules Undefined

| Attribute | Value |
|-----------|-------|
| **Gap ID** | GAP-15 |
| **Category** | Source Control Governance |
| **Severity** | MINOR |
| **Business Impact** | Low — affects code safety practices. |
| **Technical Impact** | Main branch has no protection; direct pushes allowed; merge conflicts possible. |
| **Evidence** | No `.github/CODEOWNERS`, no branch protection rules in GitHub; no status check enforcement |
| **Root Cause** | Not configured; project is small enough that it hasn't been necessary |
| **Owner** | Release Manager + IT |
| **Recommended Resolution** | Configure GitHub branch protection on `main`: (a) require PR reviews, (b) require CI to pass, (c) require CODEOWNERS approval, (d) dismiss stale reviews, (e) block direct pushes |
| **Estimated Effort** | 0.25 days |
| **Acceptance Criteria** | Branch protection enabled; team trained; test PR process validated |
| **Status** | OPEN |

---

#### GAP-16: No Monitoring Dashboard — Release Gate Status Not Visible to Stakeholders

| Attribute | Value |
|-----------|-------|
| **Gap ID** | GAP-16 |
| **Category** | Observability |
| **Severity** | MINOR |
| **Business Impact** | Low — affects visibility, not functionality. |
| **Technical Impact** | Release Gate report is uploaded to CI artifact; not visible in a dashboard. Stakeholders cannot see gate status without accessing CI logs. |
| **Evidence** | `release_gate_report.json` uploaded to CI artifact but not surfaced; no public dashboard |
| **Root Cause** | No monitoring infrastructure set up |
| **Owner** | Release Manager + IT |
| **Recommended Resolution** | Create a simple HTML status page (or GitHub Pages tab) that displays latest `release_gate_report.json` state; link from dashboard footer |
| **Estimated Effort** | 0.5 days |
| **Acceptance Criteria** | Status page exists; updates on every CI run; stakeholders can view gate status without CI access |
| **Status** | OPEN |

---

#### GAP-17: No Test Data Fixtures — QA Testing Manual

| Attribute | Value |
|-----------|-------|
| **Gap ID** | GAP-17 |
| **Category** | Test Automation |
| **Severity** | MINOR |
| **Business Impact** | Low — affects QA efficiency. |
| **Technical Impact** | Test suite uses real data from `data.js` snapshot. No isolated test fixtures for unit testing individual functions. |
| **Evidence** | Tests import from real `data.js`; no `tests/fixtures/` folder |
| **Root Cause** | Not prioritized; full end-to-end tests sufficient for current scope |
| **Owner** | Analytics Engineering |
| **Recommended Resolution** | Create test fixture CSVs for primary/offtake with known data; use for unit tests of `build_dashboard_data.py` functions. Low priority. |
| **Estimated Effort** | 0.75 days |
| **Acceptance Criteria** | Fixtures exist; unit tests use them; test coverage improves; CI time unaffected |
| **Status** | OPEN |

---

#### GAP-18: No Performance Baseline — Dashboard Load Time Not Measured

| Attribute | Value |
|-----------|-------|
| **Gap ID** | GAP-18 |
| **Category** | Performance Monitoring |
| **Severity** | MINOR |
| **Business Impact** | Low — affects user experience perception. |
| **Technical Impact** | No performance SLA; no regression detection for future `data.js` size increases; no optimization targets |
| **Evidence** | No performance test in test suite; no dashboard load time measurement; `data.js` is 14 MB (likely slow on slow networks) |
| **Root Cause** | Not prioritized; static site performance acceptable for internal users |
| **Owner** | Analytics Engineering |
| **Recommended Resolution** | Run Lighthouse audit on dashboard; document baseline load time; add Playwright performance test to CI; set SLA (e.g., First Contentful Paint < 3s on 4G) |
| **Estimated Effort** | 0.5 days |
| **Acceptance Criteria** | Performance baseline documented; CI step measures load time; regression alerting configured |
| **Status** | OPEN |

---

#### GAP-19: No Disaster Recovery Plan — Data Loss Scenario Undefined

| Attribute | Value |
|-----------|-------|
| **Gap ID** | GAP-19 |
| **Category** | Business Continuity |
| **Severity** | MINOR |
| **Business Impact** | Low — affects risk posture. Disaster scenario unlikely. |
| **Technical Impact** | If Git repo is lost or corrupted, or source files deleted, no recovery procedure documented. |
| **Evidence** | No `DISASTER_RECOVERY.md`; no backup strategy documented |
| **Root Cause** | Not prioritized; cloud-hosted repo (GitHub) provides inherent redundancy |
| **Owner** | IT + Release Manager |
| **Recommended Resolution** | Document disaster recovery: (a) repo backup (GitHub Enterprise or mirror), (b) source file archive strategy, (c) recovery RTO/RPO targets, (d) test recovery monthly |
| **Estimated Effort** | 0.5 days |
| **Acceptance Criteria** | DR plan exists; backup automation in place; test performed successfully |
| **Status** | OPEN |

---

#### GAP-20: No Change Log Automation — Releases Not Tagged

| Attribute | Value |
|-----------|-------|
| **Gap ID** | GAP-20 |
| **Category** | Release Management |
| **Severity** | MINOR |
| **Business Impact** | Low — affects release auditability. |
| **Technical Impact** | `CHANGELOG.md` is manually updated; no Git tags for releases; version not visible in dashboard |
| **Evidence** | `CHANGELOG.md` is markdown file; no Git release tags; no semantic versioning in repo |
| **Root Cause** | Release process is informal; project is young |
| **Owner** | Release Manager |
| **Recommended Resolution** | Adopt semantic versioning; create Git tags for each release (e.g., `v1.0.0`); automate CHANGELOG update from commits (using tools like `auto-changelog` or conventional commits) |
| **Estimated Effort** | 0.5 days |
| **Acceptance Criteria** | Versioning scheme defined; first release tagged; CHANGELOG automated; dashboard displays version |
| **Status** | OPEN |

---

#### GAP-21: No Acceptance Test Gate — Business Validation Not Automated

| Attribute | Value |
|-----------|-------|
| **Gap ID** | GAP-21 |
| **Category** | QC Automation |
| **Severity** | MINOR |
| **Business Impact** | Low — Phase 3 (Business Validation) will address this. |
| **Technical Impact** | KPI reconciliation to Finance is manual. No automated check that dashboard values match Finance control totals. |
| **Evidence** | No `test_business_validation.py`; no Finance control total data in test fixtures |
| **Root Cause** | Finance control totals not yet provided (GAP-10) |
| **Owner** | Analytics Engineering + Finance |
| **Recommended Resolution** | After Phase 3 (Business Validation) produces Finance control totals, implement automated test in CI: `pytest scripts/test_kpi_validation.py` that compares `data.js` KPIs to Finance controls |
| **Estimated Effort** | 0.5 days (after GAP-10 resolved) |
| **Acceptance Criteria** | Test file exists; runs in CI; all KPIs validated; variance < 0.5%; Finance data source documented |
| **Status** | BLOCKED (requires GAP-10) |

---

## Gap Closure Priority (Recommended Sequence)

| Priority | Gap IDs | Effort | Timeline |
|----------|---------|--------|----------|
| **IMMEDIATE (Sprint A)** | GAP-01, GAP-02 | 1 day | Finance decisions (0.5 day each) |
| **IMMEDIATE (Sprint A)** | GAP-03 | 2–3 days | PBIP Desktop assembly |
| **WITHIN 1 WEEK (Sprint B)** | GAP-10 | 1.5 days | Business Validation (Phase 3) |
| **WITHIN 1 WEEK** | GAP-04, GAP-05, GAP-06, GAP-09 | 2 days | Build reproducibility + operations docs |
| **FOLLOW-UP (Sprint C)** | GAP-07, GAP-08 | 0 days | Data supply (external parties) |
| **FOLLOW-UP** | GAP-12–21 | 3–4 days | Documentation + governance + UX |

---

## Production Gap Matrix Summary

| Status | Count | Action | Timeline |
|--------|-------|--------|----------|
| CRITICAL BLOCKERS | 3 | Resolve now (Finance + PBIP) | 2–3 days |
| MAJOR ISSUES | 8 | Resolve before freeze | 3–4 days |
| MINOR ISSUES | 10 | Resolve this month | 3–4 days |
| **TOTAL GAPS** | **21** | **TOTAL EFFORT** | **~1 week** |

**Production Certification can be achieved** when:
1. Finance decisions (GAP-01, GAP-02) are signed off
2. PBIP is assembled and refreshes successfully (GAP-03)
3. Business Validation baseline exists (GAP-10)

All other gaps are hygiene items that improve maintainability but do not block production deployment.

---

**Phase 1 assessment complete.** Ready for Phase 2 (Finance Decision Closure).
