# Phase A Assumptions Register — Template & Instructions

**Date Created**: 2026-08-01  
**Purpose**: Formal decision log for Phase A business assumptions  
**Format**: Excel workbook (Assumptions_Register.xlsx)  
**Status**: Template ready for sign-off

---

## Workbook Structure

### Sheet 1: Assumptions (Primary)

| Column | Type | Example | Notes |
|--------|------|---------|-------|
| **ID** | Text | A1, A2, A3... | Unique identifier |
| **Business Question** | Text | "Should primary or offtake drive baseline demand?" | What is the business rule? |
| **Context** | Text | "Primary includes distributor stock; offtake reflects retail demand" | Background/rationale |
| **Recommended Rule (Phase A)** | Text | "Offtake drives baseline; primary used for pipeline checks" | What we recommend starting with |
| **Alternative Rule (Phase B/C)** | Text | "Weighted combination: 70% offtake + 30% primary" | Possible enhancement |
| **Owner** | Text | Sales Head | Who decides? |
| **Approved By** | Text | (Leave blank until signed) | Approver name |
| **Approval Date** | Date | (Leave blank) | When approved |
| **Approval Status** | Dropdown: Pending / Approved / Rejected | Pending | Gate status |
| **Comments** | Text | (Optional) | Questions, caveats, edge cases |

### Sheet 2: Operational Decisions (Support)

Detail-level decisions that flow from primary assumptions.

| Column | Type | Example | Notes |
|--------|------|---------|-------|
| **Decision ID** | Text | D1.1, D1.2, D2.1... | Hierarchy under assumption |
| **Parent Assumption** | Text | A1 | Links to primary assumption |
| **Decision** | Text | "How to handle zero offtake in a month?" | Specific rule |
| **Rule (Phase A)** | Text | "Treat as 0; do not impute" | Starting approach |
| **Threshold / Trigger** | Text | "Any month with 0 units" | When does rule apply? |
| **Owner** | Text | KAM / Category | Decision maker |
| **Approved By** | Text | (Blank) | Approver |
| **Approval Date** | Date | (Blank) | Signed date |
| **Status** | Dropdown | Pending | Approval status |
| **Comments** | Text | "Review with Supply Planner first" | Implementation notes |

### Sheet 3: Metrics & Gates (Reference)

Pre-calculated gates and thresholds tied to assumptions.

| Column | Type | Example | Notes |
|--------|------|---------|-------|
| **Gate ID** | Text | G1, G2, G3... | Reference only |
| **Linked Assumption** | Text | A1 | Which assumption drives this gate? |
| **Metric** | Text | "Channel WAPE" | What is measured? |
| **Target (Phase A)** | Text | ≤ 10% | Acceptance threshold |
| **Measurement Level** | Text | Channel, Chain, Chain × Brand | Granularity |
| **Backtest Baseline** | Text | (Leave blank) | Filled during validation |
| **Production Result** | Text | (Leave blank) | Filled after first live run |
| **Gate Status** | Dropdown: Pass / Warning / Fail | (Blank) | Approval status |
| **Owner** | Text | Business Sponsor | Who owns the gate? |
| **Comments** | Text | "Threshold is industry standard for FMCG" | Rationale |

---

## Assumptions to Approve (Phase A)

### Assumption A1: Baseline Demand Source

**Business Question**: "Should primary or offtake drive baseline demand?"

**Context**:
- Primary includes stock movement through distribution (may include safety stock, pipeline)
- Offtake reflects actual retail sales (what consumers bought)
- For forecasting, which is the true signal?

**Recommended Rule (Phase A)**:
> Offtake drives the baseline forecast. Primary is used for supply-chain planning and pipeline visibility only.

**Rationale**:
- Offtake is end-demand; it's what the business needs to plan for
- Primary includes distributor behavior, which can be volatile or policy-driven
- De-coupling supply and demand planning improves clarity

**Alternatives**:
- Phase B: Blend 70% offtake + 30% primary for markets with limited offtake
- Phase C: Regional blend based on distributor reliability score

**Decision Required**: ✓ or ✗

---

### Assumption A2: New Product Without History (NPI)

**Business Question**: "How should NPI (new products or brand-new listings) be forecast without 6+ months history?"

**Context**:
- Some launches have <3 months data
- Without history, MoM/YoY trends cannot be calculated
- Risk of over-forecast on launch hype or under-forecast if launch is slower than expected

**Recommended Rule (Phase A)**:
> Use similar-article reference curve + approved launch distribution assumption. Confidence capped at 60% (BLOCKED for planner review).

**Method**:
1. Identify most similar existing article in same brand/category
2. Apply reference curve to new article
3. Layer launch plan distribution (% of similar article baseline)
4. Example: Brand launches new variant; use main brand curve, apply 30% adoption assumption

**Alternatives**:
- Phase B: Use competitive launch benchmarks (external data)
- Phase C: Learn launch curve from observed uptake and refine automatically

**Decision Required**: ✓ or ✗

---

### Assumption A3: Manual Uplift Application

**Business Question**: "How are manual forecast adjustments applied? Additive or multiplicative? Unit-level or wholesale?"

**Context**:
- KAMs know of planned promotions, new listings, distributor changes
- Adjustments can be for promotional lift, listing uplift, price/pack changes
- Incorrect method distorts confidence and warehouse allocation

**Recommended Rule (Phase A)**:
> Manual adjustments are **incremental quantities** on top of statistical baseline. All adjustments require:
> - Adjustment type (promotion, listing, price, distributor, event, bulk order)
> - Adjustment quantity (units or %)
> - Business reason (100 chars)
> - Owner name (who approved it)
> - Start and end month (when does it apply)

**Method**:
```
Final Forecast Qty = Statistical Forecast + Manual Adjustment Qty
Adjustment Qty = override_qty_by_chain_brand_article_month
```

**Alternatives**:
- Multiplicative: Final = Statistical × (1 + adjustment_pct)
- Weighted: Allow mix of baseline override + incremental for risk scenarios

**Decision Required**: ✓ or ✗

---

### Assumption A4: Warehouse Allocation

**Business Question**: "How are forecasted quantities split across 4 warehouses (Gurgaon, Mumbai, Bangalore, Kolkata)?"

**Context**:
- Current: Fixed percentages (Gurgaon 35%, Mumbai 30%, Bangalore 25%, Kolkata 10%)
- Better: Allocation reflects actual chain servicing logic (which chain uses which warehouse)
- Constraint: Warehouse allocation must reconcile exactly to forecast qty

**Recommended Rule (Phase A)**:
> Allocation based on chain-region servicing map, not fixed percentages across all chains.
> - Each chain is assigned primary warehouses by region (state/zone)
> - Allocation percentages can vary by chain
> - Allocation locked at chain-level (no article-level variance in Phase A)
> - Example: DMart Karnataka uses Bangalore 60% + Gurgaon 40%; Reliance uses all 4 equally

**Mapping**:
```
warehouse_gurgaon_qty = forecast_qty × chain_to_gurgaon_pct
warehouse_mumbai_qty   = forecast_qty × chain_to_mumbai_pct
warehouse_bangalore_qty = forecast_qty × chain_to_bangalore_pct
warehouse_kolkata_qty  = forecast_qty × chain_to_kolkata_pct

SUM(all warehouse qtys) = forecast_qty  (reconciliation gate)
```

**Alternatives**:
- Phase B: Allocation varies by article (high-velocity vs. niche)
- Phase C: Allocation adjusts based on real-time warehouse capacity/stock

**Decision Required**: ✓ or ✗

---

### Assumption A5: Partial-Month Treatment

**Business Question**: "How are incomplete months handled in the model?"

**Context**:
- August 2026 is current month (incomplete)
- Including partial data can skew trends and averages
- Option 1: Exclude and forecast from prior complete data
- Option 2: Include with run-rate pro-ration

**Recommended Rule (Phase A)**:
> Exclude current/partial month from model training. Use only completed months (Apr 2025 through Jun 2026). Do not backtest on Jul 2026 until Jul actuals are fully reconciled.

**Rationale**:
- Partial data introduces bias (week 1-3 of August looks like low month)
- Safer to forecast with 15 months complete data than 15.5 months partial

**Alternatives**:
- Approved run-rate logic: If 2+ weeks of current month available, pro-rate to full month (month-to-date ÷ days-elapsed × total-days)

**Decision Required**: ✓ or ✗

---

## Operational Decisions (Detail) — Supporting A1-A5

### D1.1: Zero Offtake or Negative Sales Handling

**Parent**: A1 (Baseline Demand)

**Decision**: "When an article has 0 offtake in a month, or negative offtake (returns), how is it treated?"

**Rule (Phase A)**:
- Zero offtake: Treat as actual 0; do not impute or smooth
- Negative offtake: Investigate (stock-out correction? data error?); exclude if unexplained
- Action: Flag to KAM; investigate separately; do not auto-forecast until resolved

**Owner**: Category Manager

---

### D2.1: BOGO Calculation Basis

**Parent**: A3 (Manual Uplift)

**Decision**: "Promotional BOGOs: is uplift calculated on units (1+1=2) or on NSV?"

**Rule (Phase A)**:
- BOGO uplift = unit uplift (buy 1 get 1 free = 2 units sold for 1.5x NSV)
- Adjustment qty = incremental units over baseline
- NSV adjustment = adjustment_qty × (0.5 × mrp) [50% NSV assumption for free unit]

**Owner**: Promo Manager

---

### D3.1: Maximum Growth Without Approval

**Parent**: A3 (Manual Uplift)

**Decision**: "If forecasted growth >X%, does it need separate approval?"

**Rule (Phase A)**:
- Confidence <60%: Auto-BLOCKED (requires planner review)
- YoY trend >50%: WARNING; flag to KAM
- Manual uplift >25% of baseline: Requires reason + owner signature

**Owner**: Business Sponsor

---

### D4.1: Case Pack and MOQ Rounding

**Parent**: A4 (Warehouse Allocation)

**Decision**: "Rounding strategy for fractional quantities?"

**Rule (Phase A)**:
- Round to nearest whole unit
- Rounding error allocated to largest warehouse (Gurgaon)
- Document rounding loss transparently in output

**Owner**: Supply Chain

---

### D5.1: Stock-Out / Zero Sales Treatment

**Parent**: A1 (Baseline Demand)

**Decision**: "When an article goes out of stock or has 0 demand for multiple months, how is it forecast?"

**Rule (Phase A)**:
- If >3 consecutive months of zero: Confidence set to 50%, flag as "LOW_DEMAND"
- Investigate: Delisted? De-prioritized? Supply issue?
- Forecast: Use 3-month MA before stock-out; apply decay factor (×0.5) if relaunch

**Owner**: Supply Chain / Sales

---

## Release Gate Checklist

Before v1.0.1 deployment, confirm:

- [ ] **A1 approved**: Baseline demand source (offtake vs. primary) signed off
- [ ] **A2 approved**: NPI forecasting method approved by Category
- [ ] **A3 approved**: Manual adjustment method and audit trail approved
- [ ] **A4 approved**: Warehouse allocation logic and reconciliation approved
- [ ] **A5 approved**: Partial-month treatment and run-rate logic approved
- [ ] **D1–D5 approved**: All operational decisions signed off
- [ ] **Blocked count = 0**: Data readiness audit passed
- [ ] **Historical backtesting complete**: WAPE/MAPE/bias calculated
- [ ] **Benchmark comparison done**: Engine better than baseline methods
- [ ] **UAT completed**: Business team tested 30–50 scenarios
- [ ] **Warehouse allocation reconciles**: 0 difference
- [ ] **Known limitations documented**: In ARCHITECTURE.md
- [ ] **Business sponsor sign-off**: On assumptions + acceptance gates

---

## How to Use This Template

1. **Share with stakeholders** (Sales Head, KAM, Supply Chain, Finance, Business Sponsor)
2. **Each owner reviews their assumptions** (A1-A5 + operational decisions)
3. **Approval meeting**: 1–2 hours, discuss any questions or alternatives
4. **Signatures**: Add approval date, approver name, status → "Approved"
5. **Store in version control**: Assumptions_Register_v1.0.xlsx
6. **Reference in every Phase A report**: Link audit/backtest/UAT results to assumptions

---

**Status**: Ready for Phase A stakeholder approval  
**Next Step**: Present to Business Sponsor, collect signatures  
**Timeline**: 1 meeting, 1–2 hours
