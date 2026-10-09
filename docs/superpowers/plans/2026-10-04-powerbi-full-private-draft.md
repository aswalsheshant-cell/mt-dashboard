# Full Power BI Private Draft Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build source-backed Power BI coverage for all 11 HTML dashboard tabs and their named subviews, validate it in Desktop, and publish a private draft to My workspace.

**Architecture:** Extend the existing PBIP model with sales, offtake, market, store, and planning facts from the repository's Power Query definitions. Generate report navigation and PBIR pages from one explicit page manifest, preserving the governed CM2 page. Validate numerical parity and source coverage before Desktop and Service checks.

**Tech Stack:** PBIP/PBIR JSON, TMDL/DAX, Power Query M, Python 3, pytest, Power BI Desktop and Power BI Service.

**Spec:** `docs/superpowers/specs/2026-10-04-powerbi-full-private-draft-design.md`

## Global Constraints

- Target Power BI Service **My workspace**, **private draft**; do not share, create an app, promote, merge, or change production.
- All 11 main tabs and 9 named subviews need source-backed visuals for full-dashboard completion; a missing source is visibly **incomplete**.
- Preserve source rows, B5 evidence, the provisional NPI comparison, and the two workbook-aligned CM2 views; keep B5 `BLOCKED_PENDING_DESKTOP_EVIDENCE` until its own exit evidence exists.
- The first Service dataset may be a manually refreshed import snapshot. Do not claim automatic refresh until a gateway/cloud source and a successful scheduled run are verified.
- Reconcile figures only over identical periods, filters, units, and source coverage. Never turn missing data into zero.

## Review Focus

1. A source folder with no current-period file must make its dependent page incomplete, not show a zero KPI (Task 1 and Task 6).
2. Duplicate article or store keys must not multiply financial totals through relationships (Task 2).
3. A page slicer unsupported by a source must not imply a filtered result (Task 3 and Task 6).
4. FY and partial-month comparisons must not silently compare unequal periods (Task 3 and Task 6).
5. A published report with a failed Service refresh must retain a manual-refresh warning and never be reported as automated (Task 8).

## File map

- `PowerBI/full_report_sources.json`: source query, grain, key, coverage, and refresh-mode manifest.
- `scripts/powerbi_full_sources.py`: inspect sources and produce a deterministic coverage report; no source mutation.
- `ModernTrade_Report.Dataset/definition/tables/*.tmdl` and `relationships.tmdl`: shared model, facts, dimensions, and measures.
- `PowerBI/full_report_pages.json`: 11-tab and 9-subview page manifest, visual bindings, and supported slicers.
- `scripts/build_powerbi_full_pages.py`: idempotent PBIR page/visual generation from the page manifest.
- `ModernTrade_Report.Report/definition/pages/**`: checked-in generated PBIR output.
- `scripts/reconcile_powerbi_full.py`: compare governed source aggregates with page measure outputs for identical context.
- `PowerBI/docs/FullReportParity.md`: page-by-page source, formula, units, parity, and incomplete-state record.
- `tests/test_powerbi_full_sources.py`, `tests/test_powerbi_full_model.py`, `tests/test_powerbi_full_pages.py`, `tests/test_powerbi_full_reconciliation.py`: focused static and data tests.
- `docs/evidence/powerbi_full_desktop_*.md` and `docs/evidence/powerbi_full_service_*.md`: live evidence, created only after the relevant run.

### Task 1: Source coverage contract

**Files:** Create `PowerBI/full_report_sources.json`, `scripts/powerbi_full_sources.py`, `tests/test_powerbi_full_sources.py`.

**Interfaces:** `inspect_sources(repo_root: Path, manifest_path: Path) -> dict` returns per-source `files`, `periods`, `row_count`, `key_issues`, and `available` without editing input files. Later tasks consume these fields.

- [ ] Write tests for empty current-period folders, duplicate source keys, and the actual repository folder names; assert unavailable is distinct from zero rows.
- [ ] Run `python -m pytest tests/test_powerbi_full_sources.py -q` and confirm the new tests fail for the missing implementation.
- [ ] Implement the source manifest using existing `PowerBI/PowerQuery/10_...` through `46_...` files and `PowerBI/RawDataFolders/`; record fact grain and supported dimensions.
- [ ] Implement `inspect_sources`, produce a read-only JSON coverage report, and rerun the focused tests to PASS.
- [ ] Commit the source contract and test.

### Task 2: Shared semantic model

**Files:** Modify `ModernTrade_Report.Dataset/definition/tables/*.tmdl`, `ModernTrade_Report.Dataset/definition/relationships.tmdl`, `ModernTrade_Report.Dataset/definition/expressions.tmdl`; create `tests/test_powerbi_full_model.py`.

**Interfaces:** Model tables are named `Fact_PrimarySales`, `Fact_OfftakeSales`, `Fact_Nielsen`, `Fact_TDP`, `Fact_PrimaryArticle`, `Fact_SecondarySales`, `Dim_Article`, `Dim_Store`, `Dim_Geography`, and the existing date/chain/category/CM2 tables. Measures live in `_Measures.tmdl`; CM2 contract v2 names remain unchanged.

- [ ] Write failing structure tests for each required table, unique-side relationship, fiscal date path, and no many-to-many path that can duplicate totals.
- [ ] Run `python -m pytest tests/test_powerbi_full_model.py -q` and confirm failure.
- [ ] Translate the repository's governed Power Query definitions into TMDL partitions, add explicit dimensions/relationships at real source grain, and add source-count/coverage measures.
- [ ] Run the focused tests and existing `tests/test_powerbi_cm2_views_structure.py`; fix only model defects exposed by them.
- [ ] Commit the model and tests.

### Task 3: Measures and comparison truth

**Files:** Modify `ModernTrade_Report.Dataset/definition/tables/_Measures.tmdl`; create `tests/test_powerbi_full_reconciliation.py` and `scripts/reconcile_powerbi_full.py`.

**Interfaces:** `reconcile_context(repo_root: Path, period: str, filters: dict[str, list[str]]) -> list[dict]` emits metric, source amount, expected report amount, unit, coverage, and variance. No missing measure may be encoded as zero.

- [ ] Write failing tests for identical-period NSV, source-coverage blanks, duplicate-key guard, provisional observed NPI labeling, and FY partial-period suppression.
- [ ] Run `python -m pytest tests/test_powerbi_full_reconciliation.py -q` and confirm failure.
- [ ] Add measures from the existing governed DAX files for primary, offtake, market, forecast, store, and alert contexts; retain the CM2 view and claim measures.
- [ ] Implement reconciliation output and run focused tests plus existing NPI/CM2 truth tests.
- [ ] Commit measures, reconciler, and tests.

### Task 4: Page contract and navigation

**Files:** Create `PowerBI/full_report_pages.json`, `scripts/build_powerbi_full_pages.py`, `tests/test_powerbi_full_pages.py`; modify `ModernTrade_Report.Report/definition/pages/pages.json`.

**Interfaces:** `build_pages(repo_root: Path, manifest_path: Path) -> list[str]` returns generated page IDs, writes deterministic PBIR definitions, and leaves `CM2Governed`/`FinanceSample` unchanged. Each manifest page has `id`, `displayName`, `parentTab`, `sourceIds`, `visualBindings`, `supportedSlicers`, and `statusMeasure`. Use separate pages for the 9 named subviews, with main-tab navigation and shared slicer bindings.

- [ ] Write failing tests that the manifest has the exact 11 main tabs and 9 named subviews, unique page IDs, supported field references, and no false filter claims.
- [ ] Run `python -m pytest tests/test_powerbi_full_pages.py -q` and confirm failure.
- [ ] Implement manifest and PBIR generator using the checked-in CM2 page as the format reference; add navigation and per-page source/coverage status visuals.
- [ ] Regenerate twice and assert identical output; run focused tests and JSON parse checks.
- [ ] Commit manifest, generator, generated pages, and tests.

### Task 5: Page groups with real visuals

**Files:** Extend `PowerBI/full_report_pages.json`, generated `ModernTrade_Report.Report/definition/pages/**`, and `PowerBI/docs/FullReportParity.md`.

**Interfaces:** Each page entry binds a source-backed measure/table and lists supported slicers. `FullReportParity.md` records its HTML tab, source, fiscal context, units, and completeness.

- [ ] Fill Explorer, Executive Cockpit, Channel Dynamics, Comparison, and Analytics bindings; write assertions for their required visual types and measures, then run focused page tests.
- [ ] Fill Inventory Health, Demand Planning, Stores, and Inventory bindings; add explicit unavailable-source states where actual source coverage is absent, then rerun focused tests.
- [ ] Fill P&L and Alerts bindings; keep claims, COGS assumptions, observed NPI, and alert thresholds labeled, then rerun focused tests.
- [ ] Run the full Power BI static test subset and commit each coherent page group after its tests pass.

### Task 6: Numerical and filter parity

**Files:** Extend `scripts/reconcile_powerbi_full.py`, `tests/test_powerbi_full_reconciliation.py`, and `PowerBI/docs/FullReportParity.md`.

**Interfaces:** Reconciliation report compares the HTML/source baseline with model measures at the same FY, month, chain, brand, units, and partial-period coverage.

- [ ] Add failing fixtures for missing month, unsupported slicer, duplicate key, negative chain adjustment, and partial FY.
- [ ] Run the focused tests and confirm failure.
- [ ] Implement context-normalized comparisons and populate the page parity matrix from real source aggregations.
- [ ] Run focused tests and the existing dashboard reconciliation gates; record unresolved variance as incomplete rather than changing source rows or expected values.
- [ ] Commit the parity evidence code and documentation.

### Task 7: Live Desktop validation

**Files:** Create `docs/evidence/powerbi_full_desktop_<date>.md` after the live run only; modify PBIP definitions only for reproduced Desktop defects.

**Interfaces:** Evidence records Desktop version, git SHA, model refresh result, each page/subview rendering, representative slicer outcomes, reconciliation values, export check, and screenshots. B5 evidence is a separate governed artifact.

- [ ] Open the complete `ModernTrade_Report.pbip` in Power BI Desktop and refresh from the repository sources; capture exact errors if any.
- [ ] Exercise all 11 pages and 9 subviews, a cross-page slicer, a partial period, and an export; record actual results and screenshots.
- [ ] Run the B5 Desktop runner and FY parser only under its governed instructions; keep B5 blocked if any required result or screenshot is missing.
- [ ] Repair reproduced issues, rerun affected checks, and commit truthful Desktop evidence; do not write PASS for untested pages.

### Task 8: Private Service publication

**Files:** Create `docs/evidence/powerbi_full_service_<date>.md` after publication.

**Interfaces:** Evidence records My workspace report/dataset URL, owner, page list, initial refresh mode, Service rendering, and access scope.

- [ ] Export/publish the Desktop-validated report to **My workspace** as a private draft and verify the signed-in account and destination before completing the publish dialog.
- [ ] Open the Service report, confirm all page navigation and representative visuals, and inspect dataset credentials/refresh status.
- [ ] Record any license, tenant, gateway, or credential block by its exact message; if blocked, do not claim a remote deployment.
- [ ] If published, save the private link and evidence, leave sharing and production untouched, and commit the evidence file.
