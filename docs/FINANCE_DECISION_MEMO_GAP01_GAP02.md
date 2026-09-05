# MEMORANDUM

**TO:** Modern Trade Commercial Finance Lead  
**FROM:** Analytics & BI Team  
**DATE:** September 5, 2026  
**SUBJECT:** Decision Alignment: GAP-01 (Jun'26 Allocation) and GAP-02 (Negative Cont% Treatment)

---

## GAP-01: Jun'26 FY26 Attribution Methodology

### Context

Due to partial-month reporting and staggered reporting cycles across retail accounts, the trailing forecast for June 2026 requires an agreed allocation rule to attribute top-line Net Sales Value (NSV) and offtake across chains and categories.

**Current State:** Enterprise pool = ₹400 Cr unallocated NSV for Jun'26. No clear methodology for distributing to chain/category slices.

### Options Presented

| Option | Methodology | Pros | Cons |
|--------|-----------|------|------|
| **A: Historical Run-Rate (L3M Weighting)** | Apportion Jun'26 aggregate numbers using the trailing 3 months' (Mar–May '26) actual category/chain mix | • Accounts for recent seasonality and channel momentum<br>• Reflects real operational trends<br>• No reporting lag | • Can carry forward temporary supply-chain disruptions (risk if Apr disrupted) |
| **B: Fixed Budget / AOP Weights** | Distribute strictly according to the Annual Operating Plan (AOP) FY26 category-channel ratios | • 100% aligned with target baselines<br>• Zero data drift from operational anomalies | • Masks actual channel divergence<br>• Doesn't reflect real demand<br>• Gap between plan and reality widens |
| **C: Chain-Level EPOS Extrapolation** | Apply store-level Electronic Point of Sale (EPOS) offtake trends to scale NSV dynamically | • Highest commercial fidelity<br>• Reflects true inventory pull | • Requires high data hygiene<br>• Complex reconciliation scripts<br>• Implementation timeline: 2–3 weeks |

### Recommendation: **Option A (Historical Run-Rate / L3M)**

**Rationale:**
- Reflects real operational trends without introducing the reporting lag of store-level EPOS adjustments
- Maintains the required ±0.5% reconciliation tolerance against enterprise financials
- Can be implemented in DAX within 1 week
- Carries forward recent momentum (e.g., if May saw a promotional spike, Jun'26 is allocated proportionally—good signal of real demand)

**Risk Mitigation:**
- If Apr'26 experienced a supply disruption (e.g., -15% for specific chain), the L3M weight will be lower than Oct'25–Feb'26 baseline. This is **intentional** and reflects true market conditions. Finance can flag if the variance is unexplained.

**Implementation:**
- DAX measures: `NSV_L3M_Actuals`, `Allocation_Weight_L3M`, `NSV_Jun26_Allocated` (see DAX_GAP01_GAP02_Measures.md)
- PBIP integration: Embed in `_Measures` table, use in all chain/category reporting
- Validation: Reconcile Jun'26 allocated total against enterprise pool ±0.5%

---

## GAP-02: Negative Contribution % (Cont%) Treatment

### Context

Certain low-velocity SKUs and heavily promoted Modern Trade accounts show a negative contribution margin (variable trade spend, freight, and allowances exceed gross margin). 

**Example:** DMart Skincare in May 2026:
- NSV: ₹65 Cr
- COGS: ₹45.5 Cr (GM = ₹19.5 Cr, 30%)
- Variable Trade Spend: ₹23.4 Cr (35% of NSV)
- Freight/Logistics: ₹6.5 Cr (10% of NSV)
- **Contribution Margin: -₹8 Cr (-12.3%)**

**Question:** How should negative Cont% be calculated, displayed, and audited?

### Options Presented

| Option | Methodology | Reporting / DAX | Operational Impact |
|--------|-----------|-----------------|-------------------|
| **A: Floor at 0% (Clamping)** | Any negative Cont% is displayed as 0.0%. Actual negative INR values roll up only at total chain level | `MAX(0, [Cont_Margin_Pct])` | Hides loss-making lines from category managers; distorts portfolio ranking |
| **B: Report Unclamped with Visual Warning** | Display exact negative percentages (e.g., -4.2%) highlighted with conditional red badging and threshold flags | `DIVIDE([Cont_Margin_INR], [NSV_INR])` with status badges (`Loss-Making`, `Compressed`, `Target`, `High`) | Complete mathematical auditability; immediately surfaces margin erosion; no hidden losses |
| **C: Split into Commercial Adjustment Bucket** | Clamp SKU operational Cont% at gross-to-net break-even and isolate trade overspend into an unallocated corporate adjustment row | Complex multi-tier DAX + reconciliation layer | Creates dual reconciliations between category reports and statutory P&L |

### Recommendation: **Option B (Report Unclamped with Visual Warning)**

**Rationale:**
- **P&L Integrity:** Preserves mathematical reconcilability across all hierarchy rollups (SKU → Category → Chain → Total). No hidden losses.
- **Risk Visibility:** Category managers immediately see which SKUs/accounts are loss-making. Promotes corrective action (repricing, volume cuts, promo efficiency).
- **Finance Auditability:** Negative Cont% rolls up correctly to operating profit calculations. SAP/GL reconciliation is straightforward.
- **Simplicity:** No dual reconciliations or adjustment buckets. One consistent formula: Cont_Margin_INR ÷ NSV.

**What "Visual Warning" Means:**
- Status badges (text): "Loss-Making (< 0%)", "At-Risk (0-10%)", "Target (10-20%)", "High Margin (> 20%)"
- Hex color codes (conditional formatting): Red (#D32F2F) for negative, Amber (#F57C00) for 0–10%, Green for 10%+
- Tooltip displays: "⚠️ -12.3% [LOSS] | Contribution INR: -₹8 Cr"

**Why NOT Option A (Clamping):**
- Hides ₹8 Cr loss from category manager's view → no incentive to fix the problem
- Rolling up: DMart Skincare shows 0% at SKU level, but the true contribution is negative. Aggregate chain-level math diverges from detail level.
- Violates P&L transparency: SAP shows -₹8 Cr loss, but dashboard shows 0%. Audit gap.

**Why NOT Option C (Adjustment Bucket):**
- Requires maintaining two reconciliation layers: category Cont% vs. corporate adjustment bucket
- Adds complexity with minimal benefit (bucket is a black box; doesn't help category manager optimize)
- Implementation timeline: 3–4 weeks for validation + testing

**Implementation:**
- DAX measures: `Contribution_Margin_INR`, `Cont_Margin_Pct`, `Cont_Margin_Status`, `Cont_Margin_Color`, `Cont_Margin_Badge`
- PBIP integration: Add to all matrix/card visuals; bind conditional formatting to `Cont_Margin_Color`
- Validation: Reconcile sum of Cont_Margin_INR by SKU against SAP GL account

---

## Action Required

Please indicate approval of the recommended approaches:
- ✓ **GAP-01:** Option A (Historical Run-Rate / L3M Weighting) for Jun'26 allocation
- ✓ **GAP-02:** Option B (Report Unclamped Cont% with Visual Warning) for negative margin display

**By:** September 6, 2026 COB

Once approved, the Analytics Engineering team will:
1. Implement DAX measures (ready in `/PowerBI/docs/DAX_GAP01_GAP02_Measures.md`)
2. Integrate into PBIP semantic model (4 hours)
3. Validate with test suite (`tests/test_business_validation_dax.py`) against baseline thresholds
4. Deploy to Power BI Service (30 min)

---

**Sign-Off Line:**

Finance Lead Name: _____________________  
Date: _____________________  
Approved Option A (L3M): ☐ Yes ☐ No ☐ Alternative  
Approved Option B (Unclamped): ☐ Yes ☐ No ☐ Alternative  

---

**Document Version:** 1.0  
**Prepared By:** Analytics & BI Team  
**Status:** Awaiting Finance Approval
