# Business Logic Registry

**Frozen:** 2026-08-07  
**Branch:** `claude/primary-pipeline-allocation-fy27-l9bdf6`  
**Commit:** `91b66c3`  
**Authority:** This document is the source-of-truth inventory of all business-critical calculations in the MT Dashboard pipeline. Any change to these rules requires explicit Finance or business owner approval before implementation.

---

## BL-01 — THE ONE FY RULE

**Category:** Temporal classification  
**Implemented in:** `scripts/build_dashboard_data.py` (lines 42–93); `dashboard/index.html` (`FY_ALL`/`PREAGG_FYS`/`fyBeyondPreagg()`/`FPX(tag)`)  
**Rule:**
- Apr–Dec of calendar year Y → FY(Y+1). Example: Apr-2026 → FY27
- Jan–Mar of calendar year Y → FY(Y). Example: Mar-2026 → FY26

**Python helpers:** `fy_tag_from_ym(year, month)`, `fy_tag_from_label(label)`, `fy_start_year(tag)`, `fy_source_key(tag)`, `month_labels(start_year, n_months)`, `quarter_labels_for(months)`  
**Coverage window:** `MONTHS = month_labels(2024, 26)` → Apr-24 to May-26 (26 months)  
**Extension rule:** Adding FY28+ requires only bumping `n_months` — no hardcoded FY references.  
**Owner:** Analytics Engineering  
**Finance approval required:** No — pure temporal classification  

---

## BL-02 — Distributor-to-Chain Allocation (Primary NSV)

**Category:** Revenue allocation  
**Implemented in:** `scripts/build_dashboard_data.py`: `load_chain_allocation_weights()`, `apply_chain_allocation()`  
**Documented in:** `PowerBI/docs/DistributorPrimaryAllocation_Logic.md`  

**Rule:**
1. **Direct rows** (`PO Type ≠ 'Dist.'`): Chain Name is taken as-is — no re-allocation.
2. **Distributor rows** (`PO Type = 'Dist.'`): NSV is re-split across chains using secondary-offtake-derived contribution fractions from `Primary_ShipTo_FY25-26_to_May26.csv`.
3. **Eligibility gate:** A primary row is allocated to a chain only if that Chain×Brand×Article combination has secondary offtake evidence in month M or M+1. Rows with no offtake evidence are tagged `Blocked`.
4. **Jun'26 gap:** Shipment CSV covers May'25–May'26. Jun'26 distributor rows use May'26 contribution splits (nearest-month fallback). Status: PROVISIONAL — Finance approval pending (Decision 1).

**Reconciliation identity:**
```
Original Primary NSV = Allocated NSV + Blocked NSV
Variance = 0  (exact — never force-fit to 100%)
```

**Source file flag:** `PO Type` column distinguishes Direct vs Distributor (NOT `MTD-Sale type`).  
**Owner:** Analytics Engineering + Finance (for jun26 approval)  
**Finance approval required:** Yes — Decision 1 (Jun'26) PENDING  

---

## BL-03 — Canonicalization (Chain / Brand / Zone / State)

**Category:** Master data normalization  
**Implemented in:** `scripts/build_dashboard_data.py` (lines 107–217)  

**Chain canonicalization:** `CHAIN_ALIASES` (50+ entries) + `canon_chain()` — collapses source spelling variants across all four source files to one business-facing chain name.  
**Brand canonicalization:** `BRAND_MAP` (8 brands) + `canon_brand()`.  
**Zone canonicalization:** `canon_zone()` — 5 zones (North, South 1, South 2, West, East).  
**State canonicalization:** `STATE_ALIASES` (13 aliases) + `canon_state()`.  

**Critical rule:** Canonicalization happens at load time, before any aggregation. New chain spellings appearing in future source files will route to the unresolved form (pass-through) — they must be added to `CHAIN_ALIASES` before next production build.  
**Owner:** Analytics Engineering  
**Finance approval required:** No — but new chain additions require Analytics sign-off  

---

## BL-04 — Negative Contribution Fraction Treatment

**Category:** Data quality / reconciliation  
**Implemented in:** `scripts/build_dashboard_data.py` (allocation logic — retain by default)  
**Documented in:** `PowerBI/docs/Finance_Approval_Decision_Log.md` (Decision 2)  
**Gate:** `release_gate.py:644` — `negative_frac_treatment_status` in G10  

**Rule (current default):**
- **RETAIN** negative fraction rows in the model.
- 8 source rows with negative `Cont%` (credit/reversal entries from Az Enterprises, D.L. Sales - MT, VENKATESHWARA AGENCIES-TG).
- 157 affected article-level rows. Total negative NSV impact: −₹0.2093 L (0.0013% of total Dist NSV).
- These rows are visible in `Primary Negative Frac Rows` and `Primary Negative Frac Flag` DAX measures on the QC page.

**Zero-floor alternative:** Replace negative fracs with zero. Requires documented Finance authorisation — this diverges source ↔ model by ₹0.21 L.  

**CRITICAL DISCREPANCY:** `release_gate.py` default config sets `negative_frac_treatment_status = "APPROVED"` but Finance Decision 2 is PENDING as at 2026-08-07. The gate G10 will pass with the default config. This must be corrected before production deployment.  
**Owner:** Finance (decision) + Analytics Engineering (implementation)  
**Finance approval required:** YES — Decision 2 PENDING  

---

## BL-05 — TOT% Calculation (3-Tier Priority)

**Category:** Financial KPI derivation  
**Implemented in:** `scripts/build_dashboard_data.py` (`tot_block()`) and `PowerBI/DAX/12_TOT_Measures.dax`  
**Documented in:** `PowerBI/docs/DataDictionary.md`  

**Rule (priority order):**
1. **Tier 1 — Direct TOT:** Average TOT% from primary source file (`Avg TOT %` column).
2. **Tier 2 — Reverse calculation:** Derived from `MRP - NSV - Tax` when direct TOT is unavailable.
3. **Tier 3 — GST fallback:** Rate from `GST_Rate_QC_Table.csv`. GST Cutover Date = `COALESCE(MINX(GST Config table), DATE(2025,9,22))` (hardcoded fallback date is safe — COALESCE handles it).

**Gate:** G8 in `release_gate.py` — Tier 3 (GST fallback) usage must remain ≤ 30% of rows.  
**Threshold:** `tot_fallback_max_pct = 30.0` — source of threshold not documented as Finance-approved.  
**Owner:** Finance (threshold approval) + Analytics Engineering  
**Finance approval required:** POLICY APPROVAL REQUIRED — 30% threshold source undocumented  

---

## BL-06 — CM2% Calculation

**Category:** Financial KPI derivation  
**Implemented in:** `scripts/build_dashboard_data.py` (`cm2_block()`) and `PowerBI/DAX/13_CM2_Measures.dax`  

**Rule:**
```
CM2 = NSV − P&L Expenses
```
Expenses sourced from `PL_Expense_Input.csv`. Customer Code → Chain matching via `CustCode_Chain_Map`, with Chain fallback.  

**Gate:** G9 in `release_gate.py` — expense matching must cover ≥ 80% of NSV.  
**Threshold:** `cm2_expense_match_min_pct = 80.0` — source of threshold not documented as Finance-approved.  
**Owner:** Finance (threshold approval) + Analytics Engineering  
**Finance approval required:** POLICY APPROVAL REQUIRED — 80% threshold source undocumented  

---

## BL-07 — Reliance Brand Counter Isolation

**Category:** Data integrity / double-count prevention  
**Implemented in:** `scripts/build_dashboard_data.py` (`load_reliance_bc_data()`)  
**Data structure:** `D.reliance_bc` — separate from `detail_records`. Never included in offtake totals.  

**Rule:**
- Reliance BC rows carry a 49% double-count risk (same units counted once in primary and again via BC program).
- All BC rows are loaded into `D.reliance_bc` exclusively and excluded from `D.offtake` totals.
- Dashboard BC card sources only from `D.reliance_bc`.
- The drill engine (`drillCardHtml` / `renderDrillChart`) is NOT applied to BC data — the data structures are incompatible.

**Gate:** G7 in `release_gate.py` — advisory check that BC total NSV is non-negative (basic sanity).  
**Owner:** Analytics Engineering  
**Finance approval required:** No — isolation rule is an engineering contract, not a Finance decision  

---

## BL-08 — Offtake FY27 Coverage

**Category:** Data sourcing boundary  
**Implemented in:** `scripts/build_dashboard_data.py` (`--offtake-patch` mode)  

**Rule:**
- Pre-aggregated offtake workbooks cover FY25/FY26 only (ends Mar'26).
- FY27 offtake arrives via article-level CSV files in `PowerBI/RawDataFolders/Offtake_Monthly/`.
- Each FY27 CSV is idempotently merged into the offtake block under keys `total_fyNN` / `monthly_fyNN` / `months_fyNN` / per-dim `fyNN`.
- `--offtake-patch` can be run multiple times — it recomputes each touched FY, never double-counts.
- Jun-26 BC file (`offtake_store_article_Jun_26.csv`) is absent → BC status = BLOCKED; Jun-26 excluded from `bc.months`.

**Test coverage:** `test_dashboard_disclosures.py::TestBrandCounterDisclosure` (6 tests, all passing).  
**Owner:** Analytics Engineering  
**Finance approval required:** No  

---

## BL-09 — Distribution Universe Store Classification

**Category:** Distribution KPI  
**Implemented in:** `scripts/build_dashboard_data.py` (universe block)  
**Data structure:** `D.universe` in `data.js`  

**Rule:**
- `active_stores` = total active stores in the MT universe.
- `storetype_classified` = stores with a non-blank Store Type.
- `storetype_unclassified` = stores with blank Store Type.
- Identity: `storetype_classified + storetype_unclassified = active_stores` (exact).
- When `storetype_unclassified > 0`, an `"Unclassified"` bucket is included in `by_storetype`.
- `storetype_note` is set when gap > 0 (disclosure requirement).

**Test coverage:** `test_dashboard_disclosures.py::TestDistributionStoretypeDisclosure` (7 tests, all passing).  
**Owner:** Analytics Engineering  
**Finance approval required:** No  

---

## BL-10 — FY Coverage Gating (Pre-aggregated vs Article-level)

**Category:** Data sourcing boundary  
**Implemented in:** `dashboard/index.html` (`fyBeyondPreagg()`, `FPX(tag)`, `PREAGG_FYS`)  

**Rule:**
- Pre-aggregated blocks (Primary/Offtake/P&L) cover FY25/FY26 (in `D.primary`, `D.offtake`, `D.pnl`).
- FY27+ primary lives in `D.detail_meta.fyx_primary.FY27` and `detail_records`.
- FY27+ offtake lives in `D.offtake` under per-FY keys after `--offtake-patch`.
- Each tab gates on **its own** FY coverage — the Offtake tab checks `o['total_'+fy]`, not the Primary-only `fyUnsupported()`. Cross-contamination between blocks is forbidden.

**Owner:** Analytics Engineering  
**Finance approval required:** No  

---

## BL-11 — Primary Reconciliation (Release Gate)

**Category:** Data integrity assurance  
**Implemented in:** `scripts/release_gate.py` (`_gate_3_primary_reconciliation()`)  

**Rule:**
- For each month in `allocation_reconciliation`, the variance between original and allocated NSV must be ≤ `reconciliation_variance_tolerance_pct` (default: 0.01%).
- This is the zero-variance identity from BL-02 expressed as a tolerance for floating-point rounding.
- Gate is MANDATORY. If variance > tolerance, `data.js` is NOT generated.

**Finance approval required:** POLICY APPROVAL REQUIRED — 0.01% tolerance source undocumented (assumed engineering default, not formally Finance-approved)  

---

## BL-12 — Allocation Coverage Floor (Release Gate)

**Category:** Data quality assurance  
**Implemented in:** `scripts/release_gate.py` (`_gate_5_allocation_coverage()`)  

**Rule:**
- Allocation coverage (NSV % successfully allocated to chains) must be ≥ `allocation_coverage_min_pct` (default: 95.0%).
- Note: Gate G5 is currently set to `mandatory=False` (advisory) — this is a known implementation gap. The docstring says "Advisory in this phase."

**Policy gap:** Gate G5 is advisory rather than mandatory despite covering a material NSV floor. This should be reviewed and potentially elevated to mandatory.  
**Finance approval required:** POLICY APPROVAL REQUIRED — 95% floor source undocumented; advisory vs mandatory classification unresolved  

---

## BL-13 — Unmapped NSV Tolerance (Release Gate)

**Category:** Data quality assurance  
**Implemented in:** `scripts/release_gate.py` (`_gate_6_unmapped_value()`)  

**Rule:**
- Unmapped NSV (rows with no valid chain mapping) must be ≤ `unmapped_nsv_tolerance_pct` (default: 2.0%) of total NSV.
- Gate is MANDATORY.

**Finance approval required:** POLICY APPROVAL REQUIRED — 2% tolerance source undocumented  

---

## Registry Summary

| ID | Rule | Finance Approval | Status |
|----|------|-----------------|--------|
| BL-01 | FY temporal classification | Not required | LOCKED |
| BL-02 | Distributor→Chain allocation | Required (Decision 1) | PENDING |
| BL-03 | Canonicalization (chain/brand/zone/state) | Not required | LOCKED |
| BL-04 | Negative Cont% treatment | Required (Decision 2) | PENDING + CONFIG GAP |
| BL-05 | TOT% 3-tier priority | Threshold approval required | POLICY APPROVAL REQUIRED |
| BL-06 | CM2% expense matching | Threshold approval required | POLICY APPROVAL REQUIRED |
| BL-07 | Reliance BC isolation | Not required | LOCKED |
| BL-08 | Offtake FY27 coverage | Not required | LOCKED |
| BL-09 | Distribution universe classification | Not required | LOCKED |
| BL-10 | FY coverage gating | Not required | LOCKED |
| BL-11 | Primary reconciliation variance tolerance | Threshold approval required | POLICY APPROVAL REQUIRED |
| BL-12 | Allocation coverage floor | Threshold approval required | POLICY APPROVAL REQUIRED (+ advisory gap) |
| BL-13 | Unmapped NSV tolerance | Threshold approval required | POLICY APPROVAL REQUIRED |

**LOCKED** = rule is established, no Finance action needed.  
**PENDING** = Finance decision explicitly open (Decision Log issued 2026-08-06).  
**POLICY APPROVAL REQUIRED** = threshold or classification was set by Analytics Engineering without documented Finance sign-off.  
**CONFIG GAP** = default config in `release_gate.py` contradicts the Finance Decision Log.  
