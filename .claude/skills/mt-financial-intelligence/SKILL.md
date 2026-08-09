---
name: mt-financial-intelligence
description: |
  Financial analysis, P&L outlier detection, gross margin diagnostics, and trade spend
  intelligence for Modern Trade (MT) at Honasa/Mamaearth. Use this skill when the user asks
  about P&L analysis, margin trends, financial anomalies, trade spend ROI, gross margin
  waterfall, revenue vs cost reconciliation, or says: "P&L looks off", "margins dropped",
  "why is gross margin low", "spot anomalies in P&L", "trade spend analysis",
  "financial review", "cost of sales", "EBITDA for MT", "channel profitability",
  "which chain is most profitable", "show me the waterfall", "financial outlier",
  "revenue recognition issue", "deductions analysis".
  Do NOT use for primary/offtake data reconciliation (use mt-error-resolution) or
  raw Excel formulas (use excel-automation).
---

# MT Financial Intelligence

Diagnose financial anomalies, build P&L narratives, and assess trade spend efficiency
across chains for Modern Trade — connecting numbers to business decisions.

## Financial Statement Map for MT

```
Revenue Line:
  Gross Sales (Billing NSV)
  – Primary Deductions (schemes, damage, returns)
  = Net Sales Value (NSV)  ← primary reported metric

Cost Line:
  NSV
  – Cost of Goods Sold (COGS / Material Cost)
  = Gross Margin (GM)
  – Trade Spend (BTL: in-store activations, promotions, discounts)
  – Sales Force Cost (field staff, RSM, ASM)
  = Contribution Margin / Channel EBITDA

Key Ratios:
  GM%          = Gross Margin / NSV × 100
  Trade Spend% = Trade Spend / NSV × 100
  ROI per Lakh = (Offtake uplift ÷ Trade Spend) — incremental attribution
```

## Outlier Detection Framework

Flag a metric when it meets ONE OR MORE of these conditions:

| Condition | Threshold | Action |
|---|---|---|
| MoM swing (GM%) | ±3 percentage points | Diagnose immediately |
| YoY swing (NSV) | ±15% with no business event | Confirm with business |
| Trade spend% spike | >25% NSV in any month | Check scheme structure |
| Chain EBITDA negative | Any month | Escalate to leadership |
| Primary–offtake gap | >10% of primary | Inventory/channel stuffing risk |
| Return rate | >8% of billing | MRN or deduction issue |
| COGS% jump | ±5pp vs prior period | Check pack-size mix change |

## Diagnostic Workflow

### Step 1: Frame the question
Before any analysis, establish:
- **Period:** which FY, which months?
- **Grain:** chain-level, brand-level, or total MT?
- **Baseline:** vs prior period, vs budget, or vs peer chains?

### Step 2: Build the P&L waterfall
Always start top-down:
```
NSV (current period)  →  NSV (prior period)  →  Delta  →  Delta%
GM%  (current)        →  GM% (prior)          →  Delta pp
Trade Spend% (current) →  Trade Spend% (prior) →  Delta pp
```
Never jump directly to EBITDA without explaining the waterfall steps.

### Step 3: Isolate the driver
Use decomposition:
```
NSV change = Volume effect + Price/Mix effect
Volume effect = (qty_current - qty_prior) × avg_price_prior
Price/Mix effect = NSV_current - (qty_current × avg_price_prior)
```

### Step 4: Cross-check against operations
| Symptom | Likely cause | Check |
|---|---|---|
| NSV up, GM% down | Pack-size mix shift to lower-margin SKUs | EAN-level GM by brand |
| Trade spend% spike | Unplanned promo or scheme escalation | Scheme master vs actuals |
| NSV flat, offtake up | Inventory drawdown at trade — no new billing | Days of supply calculation |
| GM% drop in one chain | Chain-specific deduction or damage claim | Chain P&L vs others |
| Negative NSV | Return / MRN exceeds billing in period | MRN log, credit note register |

### Step 5: Write the insight (executive-ready)

Lead with the variance, not the data:
- "Reliance GM% fell 4.1pp MoM in June-26, driven by a 22% spike in BTL trade spend
  for the summer push — this is expected and recoverable as schemes close."
- "D-Mart NSV declined ₹8.2L YoY in Q1 FY27 due to 3 weeks of discontinued shelf
  placement; recovery expected with Q2 planogram reset."

## Channel Profitability Matrix

Use this to rank chains by financial health:

```
Score each chain on:
  1. NSV contribution (% of total MT NSV)
  2. GM% (vs MT average)
  3. Trade spend efficiency (offtake per lakh of trade spend)
  4. Growth trajectory (3M rolling NSV trend)

Priority quadrants:
  HIGH NSV + HIGH GM%  → Core Pillar (protect, invest)
  HIGH NSV + LOW GM%   → Value Trap (optimize deductions, review schemes)
  LOW NSV  + HIGH GM%  → Growth Opportunity (scale shelf space, activations)
  LOW NSV  + LOW GM%   → Review (strategic question: exit or reform)
```

## Trade Spend ROI Analysis

```python
# Basic incremental ROI calculation
def trade_spend_roi(offtake_base_lakhs, offtake_promo_lakhs, trade_spend_lakhs):
    """
    offtake_base  = sell-through in comparable non-promo period
    offtake_promo = sell-through during promo period
    Returns incremental offtake per lakh of spend.
    """
    incremental = offtake_promo_lakhs - offtake_base_lakhs
    if trade_spend_lakhs == 0:
        return None
    return round(incremental / trade_spend_lakhs, 2)

# ROI > 1.5 = positive incremental (promo lifted more than it cost)
# ROI < 0.5 = scheme is not incrementally effective
```

## SAP FI Context (Mamaearth reporting alignment)

Key P&L concepts relevant to MT data from SAP FI:
- **G/L (General Ledger):** All revenue and cost entries — NSV flows here
- **AP/AR:** Vendor deductions and trade receivables track scheme settlements
- **ACDOCA (Universal Journal):** Single source of truth in S/4HANA — replaces BKPF+BSEG
- **Cost Elements:** COGS and trade spend mapped as secondary cost elements in CO module
- **Profit Center:** Each MT chain may have its own profit center for P&L attribution

When reconciling MT dashboard P&L to SAP:
1. Align period definition (SAP uses calendar period; MT uses Apr–Mar FY)
2. Confirm revenue recognition point (billing date vs delivery date)
3. Check deduction netting — SAP may net returns against revenue; MT may show gross

## Output Format for Financial Reviews

```
## [Chain / Period] P&L Summary

| Metric | Current | Prior Period | Delta | Delta% | Status |
|---|---|---|---|---|---|
| NSV (₹L) | 142.3 | 128.7 | +13.6 | +10.6% | ✓ |
| GM% | 38.2% | 41.5% | -3.3pp | — | ⚠️ |
| Trade Spend% | 12.8% | 9.6% | +3.2pp | — | ⚠️ |
| Channel EBITDA% | 25.4% | 31.9% | -6.5pp | — | 🔴 |

### Key Driver: [one sentence]
### Business Context: [one sentence]
### Recommended Action: [one sentence]
```

## Governance Rules

- Never state a finding without quantifying it (use ₹L or pp, not "significant")
- Always distinguish: anomaly (unexpected) vs. business-driven change (explained)
- Flag, do not conclude — finance leadership retains final interpretation authority
- When data conflicts with prior-period numbers, surface the discrepancy explicitly
