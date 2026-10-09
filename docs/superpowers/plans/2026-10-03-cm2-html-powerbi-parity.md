# CM2 HTML and Power BI Parity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give HTML and the checked-in Power BI project the same source-backed provision and recorded-DN CM2 views, tax treatment, coverage, and matched comparison without promoting provisional values to Finance actuals.

**Architecture:** A Python reporting module computes one unrounded MT month × chain × brand contract from Primary article rows and a locally supplied workbook; only aggregates enter `dashboard/data.js` and a local Power BI import CSV. HTML and the PBIP read that contract, while source workbook rows stay off GitHub. An unavailable workbook or unresolved modeled COGS base yields an explicit unavailable CM2 cell, with source NSV, tax, claims, and coverage still visible.

**Tech Stack:** Python 3, pandas/openpyxl/pytest; existing vanilla JavaScript and Playwright browser tests; Power BI PBIP/TMDL/Power Query M/DAX; PowerShell only for the separate B5 runner.

**Spec:** `docs/superpowers/specs/2026-10-03-cm2-dual-level-dashboard-design.md`

## Global Constraints

- Preserve signed sales, credits, returns, financial source files, evidence, and approved totals; never drop nonpositive groups to force reconciliation.
- Provision and recorded-DN claims are alternative cuts of overlapping events, never additive. PR #267 distributor claims stay draft/HOLD and outside these cuts.
- `Inv. Tax Amount(LOC)` is recorded tax; `Inv. Net value(LOC)` and `Total MRP sales` are distinct source fields. No fixed 18% GST in either CM2 cut.
- COGS 16%, logistics 3%, and fallback TOT/MD 30% are modeled assumptions. Do not publish modeled CM2 while the source gross/COGS base remains unresolved; retain `NOT_AVAILABLE` with claim/coverage facts.
- Keep chain-month no-sales claims in reconciliation: provision ₹137.9529L and recorded DN ₹2.20L in the supplied workbook.
- July/August recorded DN remain `PARTIAL_REGISTER`. Source actual claims do not make the resulting CM2 a Finance actual.
- Raw workbook and row-level claims remain local/ignored. The public HTML payload and Power BI export contain governed aggregates and no customer/distributor identifiers.
- B5 stays `BLOCKED_PENDING_DESKTOP_EVIDENCE`; no generated or static test output clears it. No PR merge or production publish in this plan.

## Review Focus

1. A signed negative/return-only chain must remain in reconciliation; Task 3 tests the exact signed sum.
2. A tiny invoice value may yield a rounded tax/net ratio outside 5% or 18%; Task 1 tests amount materiality before calling it invalid.
3. A workbook claim with no matching Primary sales must be unallocated rather than divided by zero; Task 2 tests North RMTs and WH-Smith fixtures.
4. Provision and DN covers differ; Task 3 tests that the percentage gap uses only matched keys and one denominator.
5. A missing workbook, incomplete DN month, or unsupported category filter must never render 100% or a whole-population margin; Tasks 3–5 test each surface.

---

### Task 1: Source Tax and Gross-Basis QC

**Files:** Create `scripts/cm2_reporting.py`; test in `tests/test_cm2_reporting_tax.py`; add no raw source file.

**Interfaces:** `build_tax_basis(primary: pandas.DataFrame) -> pandas.DataFrame` consumes the existing article-frame columns `_FY`, `_M`, `_Chain`, `_Brand`, `_category`, `_EAN No.`, `_NSV`, `_TaxLOC`, `_MRP`, `_Chan` after distributor allocation; it preserves signed INR-lakh amounts and adds `gst_qc_status`. `tax_summary(rows: pandas.DataFrame) -> dict` returns signed `nsv`, `tax`, `mrp`, `effective_gst_pct`, status counts and reviewed amount for a selected population. `effective_gst_pct = 100 * Σtax/Σnsv` only where invoice NSV is validated tax-exclusive; no simple average.

- [ ] **Step 1:** Write failing synthetic tests for one 5% row, one 18% row, mixed April/May rows, a negative credit, a missing-tax row, a zero-tax row, and ₹0.10 NSV/₹0.02 tax rounded row. Assert source sums, month-specific weighted rates, `MIXED_RATE` aggregate status, and `REVIEW_RATE_OR_BASE` for the small row.
- [ ] **Step 2:** Run `python -m pytest tests/test_cm2_reporting_tax.py -q`; expect missing-interface failures.
- [ ] **Step 3:** Implement the two interfaces. Use a documented percent tolerance plus absolute-tax/NSV materiality, keep missing distinct from zero, and require an explicit invoice-NSV-tax-exclusive assertion before presenting an effective rate. Do not infer MRP from NSV and GST.
- [ ] **Step 4:** Run the focused test; expect PASS. Separately reconcile the FY27 Apr–Aug Primary CSVs read-only: 123,773 numeric tax/net rows and month-level tax/net ratios approximately 15.17%, 14.86%, 14.39%, 13.85%, 14.20% across all channels. Record any changed source snapshot instead of updating expectations blindly.
- [ ] **Step 5:** Commit the tested code on the implementation branch with a signed GitHub-verified commit.

### Task 2: Workbook Cut Adapter and Coverage

**Files:** Extend `scripts/cm2_reporting.py`; test in `tests/test_cm2_reporting_claims.py`; add an ignored local input pattern in `.gitignore` only if a new staging path is used.

**Interfaces:** `load_workbook_cuts(path: pathlib.Path) -> tuple[pandas.DataFrame, pandas.DataFrame, pandas.DataFrame]` returns provision claims, provision BA, and recorded DN with `month`, canonical `chain`, `head`, signed `amount_lakh`, `source_row`, and `source_status`. Resolve `Data_Primary`/`Data_ActualClaims` formula-column aliases from `Chain_Alias` source names, not cached formula values. `claim_coverage(primary, claims) -> dict` returns covered NSV, uncovered NSV, no-sales claim amount/keys, and source total without dropping signed values.

- [ ] **Step 1:** Write failing tests with a minimal temporary workbook: two different source aliases to one locked chain, claim and BA on one month, a credit, an unmapped alias, and a no-sales claim. Assert row counts, signed control totals, explicit unmapped/no-sales buckets, and that BA remains separate.
- [ ] **Step 2:** Run `python -m pytest tests/test_cm2_reporting_claims.py -q`; expect missing-interface failures.
- [ ] **Step 3:** Implement workbook reads/validation, require the expected sheet/column contract, reject duplicate source-event IDs and unsupported status text, and never rely on Excel formula caches. Do not copy the workbook into the repository.
- [ ] **Step 4:** Run the focused test; expect PASS. Run a read-only local reconciliation against the supplied workbook: provision Claim 133/₹1,174.3635L, BA 40/₹769.6355L, DN 64/₹1,274.7132L, plus the two no-sales buckets. A mismatch stops integration and is reported with source row references.
- [ ] **Step 5:** Commit the tested adapter with a signed GitHub-verified commit.

### Task 3: One Governed CM2 Contract and Local Power BI Export

**Files:** Extend `scripts/cm2_reporting.py`; modify `scripts/build_dashboard_data.py` around `cm2_block()` and its `detail_records_real()` caller; test in `tests/test_cm2_views_contract.py` and `tests/test_cm2_scope_disclosure.py`.

**Interfaces:** `build_cm2_views(primary, provision_claims, provision_ba, direct_dn, *, cogs_basis_status: str) -> dict` emits `cm2.views` keyed `provision` and `recorded_dn` with FY/month/chain/brand aggregated rows, raw NSV/tax/MRP, claim amount, covered NSV, status, assumption metadata, unallocated entries, and matched-key bridge. `write_cm2_powerbi_export(views: dict, path: pathlib.Path) -> None` writes exactly those non-identifying aggregate rows to a local CSV. Add optional CLI `--cm2-workbook PATH` and `--cm2-powerbi-export PATH`; without the workbook, expose `NOT_AVAILABLE` and never fabricate a provision cut.

- [ ] **Step 1:** Write failing tests for provision/DN mutual exclusion, 23 matched-key fixture logic using one denominator, partial July/August, absent workbook, unresolved COGS base, signed negative-only groups, and `Σ raw MT NSV` versus rounded exported/detail sum with an explicit bridge. Assert no row-level customer, distributor, or invoice IDs in payload/export.
- [ ] **Step 2:** Run `python -m pytest tests/test_cm2_views_contract.py tests/test_cm2_scope_disclosure.py -q`; expect new-contract failures.
- [ ] **Step 3:** Implement the contract from the unrounded, already allocated Primary frame. Preserve old `cm2` keys for existing consumers during migration, but do not publish mixed-FY/FY26 numeric CM2 when expense coverage is absent. Remove the nonpositive-group omission in the CM2 rollup and add a status alongside every percentage. Do not change the Primary source rows.
- [ ] **Step 4:** Run focused tests; expect PASS. Against the supplied workbook, verify 23 matched chain-month keys, ₹11,280.96L rounded-detail NSV, ₹721.5595L provision claims, ₹1,259.7150L DN, ₹538.1555L claim difference, and the raw-versus-rounded MT NSV bridge of ₹1.38L; explain any raw-basis difference rather than forcing equality to rounded workbook rows.
- [ ] **Step 5:** Commit the contract and non-identifying export with a signed GitHub-verified commit; keep generated real-source CSV out of Git.

### Task 4: HTML P&L Cards, Drills and Exports

**Files:** Modify `dashboard/index.html` `buildPnl()` and adjacent export helpers; test in `tests/test_cm2_views_browser.js` using the repository's existing local HTTP/Playwright harness.

**Interfaces:** Read only `D.cm2.views` from Task 3 for the new sections. Apply `F.FY`, `F.Month`, and `F.Chain` to the same row set for cards, chart, table, tooltips and CSV/XLSX exports. A Brand filter is supported only with `NSV-share allocated estimate` labeling; Category and other unsupported filters withhold modeled CM2. The existing loaded-DN card, if kept, is explicitly separate from workbook-modeled CM2.

- [ ] **Step 1:** Write a failing browser test that injects a small `D.cm2.views` fixture and selects FY27/Apollo/April, then August partial, then Category. Assert matching card/table/export population, partial/status copy, matched claim bridge, no fabricated 100%, and no stale FY fallback.
- [ ] **Step 2:** Run the local server and `node tests/test_cm2_views_browser.js`; expect fixture assertions to fail on the old UI.
- [ ] **Step 3:** Render two separate workbook-aligned views, covered-NSV and GST-QC strip, matched-claim bridge, and unallocated/partial exceptions from the shared contract. Keep provision BA separate and avoid a whole-population margin when a cut is uncovered or the COGS base is unresolved.
- [ ] **Step 4:** Rerun the focused browser test plus `node tests/test_cm2_display_truthful.js` and `node tests/test_pnl_cm2_tot_fy_filter.js`; expect PASS with no page errors.
- [ ] **Step 5:** Commit the HTML/test change with a signed GitHub-verified commit.

### Task 5: Checked-In PBIP Model and Page Parity

**Files:** Create `ModernTrade_Report.Dataset/definition/tables/Fact_CM2.tmdl`; modify `ModernTrade_Report.Dataset/definition/model.tmdl`, `ModernTrade_Report.Dataset/definition/tables/_Measures.tmdl`, and `ModernTrade_Report.Report/definition/report.json` or the Desktop-generated equivalent page files; update `PowerBI/docs/DataModel.md` and `PowerBI/docs/PageLayouts.md`; test in `tests/test_powerbi_cm2_views_structure.py` and governed live Desktop evidence.

**Interfaces:** `Fact_CM2` imports Task 3's local aggregate CSV through a repo-root path parameter, with a unique month key dimension and one-to-many relationship. DAX measures consume the same fields/statuses as HTML: provision claim, recorded DN, covered NSV, source tax, GST QC, modeled CM2 (BLANK if COGS base unresolved), and matched-key comparison. No DAX measure sums provision and DN together or averages GST rates.

- [ ] **Step 1:** Write failing structural tests for table/measure names, unique month-side relationship, signed amount handling, no hard-coded 18% GST, no provision-plus-DN measure, status/coverage presence, and a real CM2 page reference in the checked-in PBIP.
- [ ] **Step 2:** Run `python -m pytest tests/test_powerbi_cm2_views_structure.py -q`; expect missing-model failures.
- [ ] **Step 3:** Use a Power BI Desktop-compatible PBIP layout, preferably saved by Desktop after importing the local aggregate, to add the table, measures and page. Replace the sample model's hardcoded `\\data-server` dependency for this CM2 page with a local repo-root parameter; do not relabel its existing Finance sample measures as governed CM2. If Desktop cannot open the current simplified PBIP, repair/round-trip its structure before claiming page parity.
- [ ] **Step 4:** Rerun structural tests; expect PASS. In a real Desktop session, refresh the model and verify unique relationship/cardinality, Apr and Aug filters, a mixed-rate month, a negative credit, provision/DN separation, coverage and blank modeled margin for unresolved COGS. Record screenshots/values; if no Desktop engine is available, report runtime verification pending.
- [ ] **Step 5:** Commit model, page, docs and tests with a signed GitHub-verified commit only after the file structure opens in Desktop; otherwise keep the work in draft with the exact blocker.

## Release Check

Run the repository's narrow CM2/PBIP tests and browser checks after each dependent task, then compare HTML and Desktop for the same FY × month × chain and claim-source selections. The independent PR #291 runner repair is planned in `docs/superpowers/plans/2026-10-03-b5-runner-preflight.md`. A code review may accept the branch while Finance's COGS-base definition, Desktop runtime evidence, PR #267 approvals, and B5 exit remain open. Keep the implementation in draft until those gates are met.
