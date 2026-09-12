# KPI Validation Framework — Finance Reconciliation

**Issued:** 2026-08-08  
**Authority:** Analytics Engineering + Finance  
**Scope:** Production certification validation of all KPIs to Finance control totals  
**Status:** Phase 3 Business Validation (awaiting Finance control totals)  

---

## Executive Summary

The MT Dashboard computes KPIs from source data and allocation logic. Before production certification, every KPI must be reconciled to Finance-owned control totals to confirm accuracy within agreed-upon tolerance.

**What this document defines:**
1. All dashboard KPIs by tab and business metric
2. Expected Finance source for each control total
3. Reconciliation procedure and variance tolerance
4. Sign-off criteria for production readiness

**What's needed from Finance:**
- Primary NSV control total (by FY, by chain, by distributor type)
- Offtake Qty control total (by FY, by chain, by month)
- P&L Expense control total (by month)
- CM2% and TOT% reconciliation sources
- Approval of tolerance levels

---

## KPI Inventory & Validation Matrix

### Block 1: Primary NSV (Dashboard Tab: "Primary")

| KPI | Definition | Source | Finance Control | Dashboard Calculation | Tolerance | Status |
|-----|-----------|--------|-----------------|---------------------|-----------|--------|
| **Primary NSV Total (FY26)** | Total net sales value, direct from source | Finance Close workbook | [AWAITING] | `detail_meta.primary_total_nsv.FY26` | ±₹79 L (0.5%) | PENDING |
| **Primary NSV by Chain (FY26)** | Breakdown by 5 major chains | Finance Close workbook | [AWAITING] | Allocated via chain dimension | ±₹50 L per chain (0.5%) | PENDING |
| **Primary NSV by Distributor Type (FY26)** | Direct vs. Indirect split | Finance Close workbook | [AWAITING] | From source data | ±₹50 L (0.5%) | PENDING |
| **Primary NSV by Brand (FY26)** | Top 20 brands | Finance Close workbook | [AWAITING] | Drilled from article level | ±₹40 L per brand (0.5%) | PENDING |
| **Jun'26 Distributor NSV (Provisional)** | 21 distributors, 10,236 rows, ₹1,376.49 L | Primary_ShipTo_FY25-26 (May fallback) | Finance Decision 1 approval | Allocated using May'26 splits (Option A assumed) | Pending decision | PENDING Finance Decision 1 |

**Reconciliation Identity:**
```
Original Primary NSV (from source)
= Allocated NSV (after distributor split)
+ Blocked NSV (failed allocation eligibility)

Variance must = 0.0000% (this is reconciliation, not approximation)
```

**Validation Steps:**
1. Export Finance close Primary NSV total (by chain, by month)
2. Query dashboard: `window.DASH.primary.FY26.chain_breakdown`
3. Compare line-by-line; document any divergence > ±₹50 L per chain
4. If divergence found: Investigate allocation logic, source data, business rules
5. Finance approves variance or requests rerun with corrected data

**Sign-off criteria:** Finance approves all chain/brand totals within tolerance OR explains variance

---

### Block 2: Offtake Volume & Value (Dashboard Tab: "Offtake")

| KPI | Definition | Source | Finance Control | Dashboard Calculation | Tolerance | Status |
|-----|-----------|--------|-----------------|---------------------|-----------|--------|
| **Offtake Qty Total (FY26)** | Total units sold through channels | Supply Chain close | [AWAITING] | `detail_meta.offtake_total_qty.FY26` | ±2% | PENDING |
| **Offtake Qty by Chain (FY26)** | By major chain (Apollo, Reliance, DMart, etc.) | Supply Chain close | [AWAITING] | `offtake.FY26.chain_breakdown` | ±2% per chain | PENDING |
| **Offtake Qty by Month (FY26)** | Monthly trend | Supply Chain close | [AWAITING] | `offtake.FY26.monthly_trend` | ±2% per month | PENDING |
| **Reliance Brand Counter Offtake (Isolated)** | BC volumes (separate dataset; not mixed in totals) | Reliance BC reconciliation | [AWAITING] | `reliance_bc` (not in `offtake` totals) | N/A (isolated) | PENDING |
| **FY27 Offtake (Monthly Ingestion)** | Incremental monthly updates | Supply Chain | Ongoing monthly supply | Merged via `--offtake-patch` | ±2% per month | CONDITIONAL on FY27 data supply |

**Reconciliation Identity:**
```
Offtake Qty (from Supply Chain close)
= Allocated to Chains via dimension drill
+ Unallocated/Rounding (should be < 0.1%)

Variance must be < 2% (accounting for rounding/timing differences)
```

**Validation Steps:**
1. Obtain Supply Chain offtake close by chain (for FY26)
2. Query dashboard by chain: `window.DASH.offtake.FY26.chain_breakdown`
3. Compare totals; calculate variance %
4. If > 2%: Investigate drill logic, store assignment, timing (month-end vs. month-start)
5. Supply Chain + Finance jointly approve variance reason

**Sign-off criteria:** Supply Chain confirms offtake totals match close; variance reason documented

---

### Block 3: P&L Expenses & CM2% (Dashboard Tab: "P&L")

| KPI | Definition | Source | Finance Control | Dashboard Calculation | Tolerance | Status |
|-----|-----------|--------|-----------------|---------------------|-----------|--------|
| **P&L Expenses Total (FY26)** | NSV - CM2 (Cost of Goods Sold analogue) | Finance expense input CSV | [AWAITING] | Summed from CustCode_Chain_Map matches | ±₹30 L (0.5%) | PENDING |
| **CM2% by Chain (FY26)** | Contribution Margin 2 % (NSV - Expenses) / NSV | Finance close | [AWAITING] | `(offtake_nsv - expenses) / offtake_nsv` | ±1% per chain | PENDING |
| **Expense Matching Coverage** | % of Offtake NSV with matched expense records | Finance input | ≥80% | `matched_expense_rows / total_offtake_rows` | ≥80% minimum | PENDING |

**Reconciliation Identity:**
```
Total Offtake NSV (from earlier)
= Matched Expense NSV (via CustCode_Chain_Map)
+ Unmapped Expense NSV (no customer code match)

Matched % should be ≥ 80% (per Release Gate G9)
```

**Validation Steps:**
1. Obtain Finance Expense Input file (PL_Expense_Input.csv by customer code, amount)
2. Verify CustCode_Chain_Map: all customer codes present?
3. Query dashboard: `window.DASH.pnl.FY26.expense_coverage_pct`
4. Compare to Finance control total
5. If coverage < 80%: Identify unmapped customer codes; request additional mapping or Finance reconciliation

**Sign-off criteria:** Expense matching ≥80% coverage achieved; CM2% agrees within ±1%

---

### Block 4: Distribution & TDP (Dashboard Tab: "Distribution")

| KPI | Definition | Source | Finance Control | Dashboard Calculation | Tolerance | Status |
|-----|-----------|--------|-----------------|---------------------|-----------|--------|
| **Total Distribution Points (TDP) (FY27)** | Total # of stores | Supply Chain TDP supply | [AWAITING SUPPLY] | `detail_meta.tdp_total` | ±2% | BLOCKED (data dependency) |
| **TDP by Chain (FY27)** | Store count by major chain | Supply Chain TDP supply | [AWAITING SUPPLY] | `tdp.chain_breakdown` | ±2% per chain | BLOCKED (data dependency) |
| **TDP Growth (FY27 vs FY26)** | Net new stores | Supply Chain trend | [AWAITING SUPPLY] | `tdp.FY27 - tdp.FY26` | ±5% | BLOCKED (data dependency) |

**Status:** Cannot validate until Supply Chain provides FY27 TDP monthly CSVs.

**Validation Steps (when data arrives):**
1. Receive monthly TDP file from Supply Chain
2. Load into `PowerBI/RawDataFolders/TDP/`
3. Refresh Q14 (Fact TDP) in Power BI
4. Query dashboard: `window.DASH.distribution.tdp_by_chain`
5. Compare to Supply Chain source; confirm ±2%

**Sign-off criteria:** Supply Chain confirms TDP totals and chain breakdown match source

---

### Block 5: Market Share (Dashboard Tab: "Market Share")

| KPI | Definition | Source | Finance Control | Dashboard Calculation | Tolerance | Status |
|-----|-----------|--------|-----------------|---------------------|-----------|--------|
| **Market Share % by Brand (FY26)** | Estimated share from Nielsen data | Nielsen | [AWAITING SUPPLY] | `share.FY26.brand_market_share_pct` | ±2% (Nielsen sampling error) | BLOCKED (data dependency) |
| **Market Share Trend (FY26 vs FY27)** | YoY change | Nielsen + dashboard | [AWAITING SUPPLY] | Trend analysis on loaded Nielsen data | ±3% | BLOCKED (data dependency) |

**Status:** Cannot validate until Nielsen provides FY26 data (FY27 future).

**Validation Steps (when data arrives):**
1. Receive Nielsen monthly CSV from Finance
2. Load into `PowerBI/RawDataFolders/Nielsen/`
3. Refresh Q13 (Fact Nielsen) in Power BI
4. Query dashboard: `window.DASH.share.FY26.brand_breakdown`
5. Compare sampling methodology; document Nielsen methodology notes

**Sign-off criteria:** Finance confirms Nielsen data is authentic and current

---

### Block 6: Forecast (Dashboard Tab: "Forecast")

| KPI | Definition | Source | Finance Control | Dashboard Calculation | Tolerance | Status |
|-----|-----------|--------|-----------------|---------------------|-----------|--------|
| **FY27 Target Primary NSV** | Revenue forecast | Finance FY27 target | [AWAITING] | `forecast.FY27.target_nsv` | ±₹100 L (0.5%) | PENDING |
| **FY27 Target by Chain** | Chain-level targets | Finance breakdown | [AWAITING] | `forecast.FY27.chain_targets` | ±₹50 L per chain | PENDING |

**Validation Steps:**
1. Obtain Finance FY27 target by chain (from budget)
2. Query dashboard: `window.DASH.forecast.FY27.target_nsv`
3. Compare total and by-chain; document any divergence
4. If divergence: Investigate if Finance targets should be re-baselined

**Sign-off criteria:** Finance confirms FY27 targets match approved budget

---

## Reconciliation Tolerance Levels (To Be Approved by Finance)

| Metric Type | Current Engineering Setting | Finance Policy Approval | Rationale |
|-------------|---------------------------|----------------------|-----------|
| **Primary NSV** | ±₹79 L (0.5%) | [AWAITING] | Source = Allocated + Blocked; should be exact (0%) unless rounding |
| **Offtake Qty** | ±2% | [AWAITING] | Supply Chain close may have timing differences (accrual vs. cash) |
| **CM2 Expenses** | ±₹30 L per month (0.5%) | [AWAITING] | Customer code mismatches; mapping incomplete |
| **Expense Matching Coverage** | ≥80% minimum | [AWAITING] | Acceptable unmapped percentage; remainder reconciled via exceptions |
| **TDP (Distribution Points)** | ±2% | [AWAITING SUPPLY] | Dependent on Supply Chain data quality |
| **Market Share (Nielsen)** | ±2% (Nielsen sampling error) | [AWAITING SUPPLY] | Nielsen data quality inherent variability |

---

## Phase 3 Validation Plan

### Timeline

| Phase | Task | Owner | Timeline | Deliverable |
|-------|------|-------|----------|------------|
| **3A** | Finance provides control totals | Finance | By 2026-08-10 | Primary NSV, Offtake Qty, CM2 expenses, FY27 targets (Excel/CSV) |
| **3B** | Analytics reconciles KPIs | Analytics Eng | By 2026-08-12 | KPI Validation Report (this file, updated with results) |
| **3C** | Finance reviews & approves | Finance | By 2026-08-13 | Sign-off on tolerance levels and variance explanations |
| **3D** | Supply Chain provides TDP & Nielsen | Supply Chain / Finance | Rolling (weekly) | FY27 TDP monthly CSVs; Nielsen data |
| **3E** | Update dashboard & PBIP | Analytics Eng | By 2026-08-15 | Refresh data.js; validate PBIP (if available) |
| **3F** | Production certification sign-off | Leadership | By 2026-08-16 | Final approval for production deployment |

### Validation Report Template (To Be Completed in Phase 3B)

```markdown
## KPI Validation Report — FY26 Baseline Snapshot

**Date:** [Date of validation]  
**Validator:** [Analytics Engineer name]  
**Finance Approver:** [Finance name]  

### Primary NSV Reconciliation

| KPI | Finance Close | Dashboard | Variance | % Variance | Status |
|-----|---|---|---|---|---|
| Primary NSV Total | ₹[X] L | ₹[Y] L | ₹[V] L | [P]% | [APPROVED / EXCEPTION] |
| Chain: Apollo | ₹[X] L | ₹[Y] L | ₹[V] L | [P]% | [APPROVED / EXCEPTION] |
| Chain: Reliance | ₹[X] L | ₹[Y] L | ₹[V] L | [P]% | [APPROVED / EXCEPTION] |
| [Continue for all chains] | | | | | |

**Variance Explanations:** [Document any > ±0.5% variance]

### Offtake Qty Reconciliation

[Similar table structure]

### Expense & CM2% Reconciliation

[Similar table structure]

### Summary

- **All KPIs within tolerance:** YES / NO
- **Exceptions requiring Finance approval:** [List and brief explanation]
- **Finance sign-off:** [Name, Date, Approval stamp]
```

---

## What Finance Must Provide (Checklist for Phase 3A)

- [ ] Primary NSV control total (FY25, FY26; by chain; by month)
- [ ] Offtake Qty control total (FY25, FY26; by chain; by month)
- [ ] P&L Expense input (by customer code, by month; in CSV format)
- [ ] Approved tolerance levels for each KPI (to override engineering defaults if needed)
- [ ] FY27 revenue target (by chain, if available)
- [ ] Nielsen data (historical and current, by brand, by month)
- [ ] TDP monthly CSVs from Supply Chain partner (or contact info for TDP reconciliation)
- [ ] Approval form for KPI Validation Report (sign-off on results)

---

## Blocker: Finance Decisions Pending

**Critical:** Phase 3 Business Validation cannot proceed fully until Finance Decisions 1 & 2 are approved (due 2026-08-09 EOD). Once approved:

1. Jun'26 Distributor allocation will be finalized (Decision 1 → Option A/B/C)
2. Negative fraction treatment will be finalized (Decision 2 → RETAIN/ZERO-FLOOR)
3. Release Gate config will be updated
4. Data.js will be rebuilt with final configuration
5. Finance can then provide definitive control totals for validation

**Implication:** KPI Validation Report will use final (not provisional) data; reconciliation will be authoritative.

---

## Post-Validation: Ongoing Reconciliation

Once Phase 3 Business Validation is complete:

- **Monthly:** Analytics team refreshes `data.js` and compares to Finance close within 5 business days
- **Quarterly:** Formal reconciliation review with Finance and Supply Chain (documented in an ops runbook)
- **Annually:** Full re-baseline of tolerance levels (updated in this document)

**Responsibility Matrix:**
| Task | Owner | Frequency |
|------|-------|-----------|
| Obtain Finance close | Finance | Monthly (5 days after month-end) |
| Build data.js from latest sources | Analytics Eng | Monthly |
| Reconcile KPIs to close | Analytics Eng | Monthly |
| Review exceptions | Finance + Analytics | Quarterly |
| Update tolerance policy | Finance + Leadership | Annually |

---

## Acceptance Criteria for Production Readiness

KPI Validation is COMPLETE when:

- [ ] All primary NSV KPIs reconcile within tolerance (or variance explained)
- [ ] All offtake qty KPIs reconcile within tolerance (or variance explained)
- [ ] Expense matching coverage ≥ 80%
- [ ] CM2% by chain reconciles within ±1%
- [ ] Finance provides written approval on all reconciliations
- [ ] Release Gate G3 (reconciliation variance) passes ≤ 0.01%
- [ ] FY27 monthly data ingestion validated (if applicable)
- [ ] Monthly reconciliation process documented and staffed

Once all criteria met: **Gap-10 CLOSED**. Ready for Phase 4 (Power BI Validation).

---

**Next Step:** Finance provides control totals and supplies missing TDP/Nielsen data. Analytics team completes reconciliation by 2026-08-13.
