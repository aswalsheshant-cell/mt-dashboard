# MT Analytics Platform — Engineering Constitution

**Project:** Honasa / Mamaearth Modern Trade Analytics Platform
**Status:** Active — all contributors and AI agents must follow these standards
**Last updated:** 2026-08-09

> Before starting any task, load and follow this document, BUSINESS_RULES.md, and QC_FRAMEWORK.md.
> Do not implement changes that violate these standards.

---

## Governance Layers

The platform is governed by four layers, each with its own Claude skill and engineering rules.

### Layer 1 — Architecture & Development
**Skills:** `mt-enterprise-architecture` · `mt-powerbi-dax`

**Law 1 — Enterprise Solution Architecture**
- Every solution must be scalable, maintainable, modular, reusable, and documented
- No quick fixes. Architecture review before every change.
- Prefer additive changes; never remove existing working functionality
- Minimize changed files per task

**Law 2 — PBIP First Engineering**
- Power BI development is text-first: PBIP / TMDL / JSON only
- Never commit `.pbix` to Git — binary files cannot be reviewed, merged, or rolled back
- Report definitions, semantic models, pages, themes: all in version-controlled text format

**Law 3 — Git Governance**
- Branch per task: `claude/<slug>`, `feature/<slug>`, `fix/<slug>`, `data/<fy>-<month>`
- PR required for all changes — no direct commits to `main`
- Every PR includes: architecture review, impact analysis, regression status, rollback plan
- Commit messages: `<type>: <plain English description>` + Co-Authored-By trailer

**Law 4 — Performance Engineering**
- Profile before optimizing: measure what is slow before fixing it
- Power Query: ensure query folding where possible
- DAX: avoid SUMX over millions of rows; use column aggregation where equivalent
- data.js ceiling: ~9MB; profile block sizes if approaching limit

**Law 5 — Pipeline Automation**
- All data generation flows through `build_dashboard_data.py` — no hand-editing data.js
- Partial refresh modes: `--primary-only`, `--offtake-patch`, `--detail-only`, `--forecast-only`
- Pipelines must be idempotent: re-running the same input produces the same output

---

### Layer 2 — Business Logic & Data Governance
**Skills:** `mt-data-governance` · `mt-error-resolution`

**Law 6 — Business Logic Guardian**
No business logic may change without validating:
- Primary: NSV = Gross Billing − Returns − Schemes − Damages
- Offtake: store-level sell-through, independent FY gating
- Allocation: Distributor → Chain → Brand → Article via controlled mapping tables
- MRN: reduces NSV in credit note month, not original billing month
- GST: NSV is always ex-GST
- Returns: validated against source MRN register
- Mapping tables (Chain, Store, EAN, Brand, Distributor, Employee): single source of truth

**Law 7 — Reconciliation Specialist**
Nothing is accepted until all six levels reconcile:
Raw → After Cleaning → After Mapping → After Aggregation → Cross-Source → Executive Summary

**Law 8 — Data Quality Engineer**
Every pipeline output reports: Completeness · Accuracy · Consistency · Validity · Uniqueness · Timeliness
Health Score ≥ 95 required for release (documented exceptions allowed with approval at ≥85).

**Law 9 — Modern Trade Master Data Governor**
- All master data changes go through the change control process
- No mapping changes in Excel directly — all changes via controlled mapping CSVs in the build script
- Change control record: old value, new value, effective date, impacted FYs, approved by

**Law 10 — Allocation Intelligence Engine**
- Distributor total ≈ Chain total (±0.5% tolerance)
- All unmapped records logged to `alloc.missing_mapping` — never silently dropped
- Allocation rules documented in `docs/ALLOCATION_RULES.md`

---

### Layer 3 — Analytics & AI
**Skills:** `mt-intelligence-engine` · `mt-executive-storytelling` · `mt-financial-intelligence`

**Law 11 — Executive Insight Generator**
Never show numbers without context. Every output answers:
What changed? → Why? → Business impact? → Financial impact? → Owner? → Priority? → Action? → Gain? → Confidence?

**Law 12 — NKAM Decision Engine**
Dashboard serves decisions, not charts. For every chain:
- Identify: Grow / Protect / Recover / Exit
- Surface: Listing opportunity, Visibility opportunity, Price opportunity, Promotion opportunity, Distribution gap
- Rank stores and SKUs by recovery potential

**Law 13 — Regional Manager Engine**
Surface automatically: Weak State · Weak City · Weak Distributor · Weak Supervisor · Coverage Gaps · Growth Hotspots

**Law 14 — Root Cause Analysis Engine**
When variance exceeds threshold, auto-run the 10-point driver sequence:
Price → Distribution → Listing → Inventory → Returns → Promotion → Execution → Seasonality → Supply → Master Data

**Law 15 — Forecast Intelligence**
Every forecast includes: Expected (P50) · Best Case (P90) · Worst Case (P10) · Risk factors · Confidence · Target Achievement %

**Law 16 — AI Report Planner**
Before creating any page: Business Goal → Audience → KPIs → Drill Path → Filters → Navigation → Executive Story → Mobile Layout → Action Trigger

---

### Layer 4 — Production Governance
**Skills:** `mt-production-readiness` · `mt-enterprise-architecture`

**Law 17 — Production Readiness Reviewer**
Nothing is marked complete until all 10 gates pass:
Architecture · Performance · Business · Security · QC · Documentation · Git · PBIP · Automation · Executive Review

**Law 18 — Security Auditor**
Always validate before release:
- No secrets/tokens in committed code
- No PII in data.js (aggregated only)
- Repository visibility appropriate for data sensitivity
- Power BI sensitivity labels applied

**Law 19 — Documentation Generator**
Every completed feature produces: Architecture · Workflow · Business Rule · Technical Rule · Data Dictionary · Measure Dictionary · Release Note · Deployment Guide · User Guide · Support Guide

**Law 20 — Continuous Improvement Engine**
After every release, generate: Technical Debt · Risk Register · Improvement Backlog · Performance Opportunities · Automation Opportunities · AI Opportunities · Business Opportunities

---

## Platform Evolution Phases

| Phase | Status | Focus |
|---|---|---|
| Phase 1: Manual Reporting | Complete | Excel → Python automation |
| Phase 2: Business Intelligence | Complete | Power BI, Dashboard, KPIs |
| Phase 3: Enterprise Data Platform | In Progress | Git, QC, Forecast, AI |
| Phase 4: AI Analytics Platform | In Progress | Executive insights, Recommendations |
| Phase 5: Enterprise Product | Target | Governed, automated, self-documenting platform |

---

## Critical Remaining Items (as of 2026-08-09)

| Priority | Item | Skill Responsible |
|---|---|---|
| P1 | Complete Distributor → Chain → Brand → Article allocation logic for FY27 | mt-data-governance |
| P1 | Primary and Offtake monthly continuity logic aligned | mt-data-governance |
| P1 | Automated reconciliation gates before every release | mt-production-readiness |
| P2 | Business Rule Registry — single source of truth for every KPI and allocation rule | mt-data-governance |
| P2 | PBIP migration — Git-based Power BI as default | mt-enterprise-architecture |
| P2 | Automated production-readiness checks (QC, security, docs, performance) | mt-production-readiness |
| P3 | Monthly release automation (QC report, release notes, deployment checklist) | mt-production-readiness |
| P3 | Power BI model optimization and health checks | mt-data-governance |

---

## Quick Reference — Which Skill for Which Task

| Task | Use Skill |
|---|---|
| Before ANY change | `mt-enterprise-architecture` |
| SQL queries | `mt-sql-analytics` |
| Python/Pandas scripts | `mt-python-pipeline` |
| Data quality / reconciliation | `mt-data-governance` |
| P&L / financial analysis | `mt-financial-intelligence` |
| NKAM insights / opportunities | `mt-intelligence-engine` |
| Leadership narratives / decks | `mt-executive-storytelling` |
| Power BI / DAX | `mt-powerbi-dax` |
| Before marking anything done | `mt-production-readiness` |
| Data pipeline errors | `mt-error-resolution` |
| Excel formulas | `excel-automation` |
| Charts / visualizations | `dataviz` |
