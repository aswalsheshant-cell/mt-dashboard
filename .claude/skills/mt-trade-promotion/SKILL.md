---
name: mt-trade-promotion
description: Analyse trade promotion effectiveness, scheme ROI, and BTL investment decisions for Modern Trade channels. Use when user asks about "trade spend ROI", "scheme effectiveness", "promo analysis", "visibility spend", "activation ROI", "BTL review", "trade investment", "which scheme is working", "promo uplift", "scheme analysis by chain", "should we invest more in trade", "trade spend by brand".
---

# MT Trade Promotion Intelligence

Trade promotion is Honasa's single largest controllable cost in MT channels.
This skill measures, diagnoses, and recommends trade investment decisions.

---

## Core Framework: ROPE Analysis

Every trade promotion analysis must answer 4 questions — in this order:

```
R — Reach:       How many stores / consumers were touched?
O — Offtake:     Did consumer sell-through increase during and after the promo?
P — Profitability: Was GM% preserved? Did EBITDA remain positive?
E — Efficiency:  What was the NSV generated per ₹ spent on trade?
```

---

## Trade Spend Categories

| Category | Description | Typical % of NSV | Decision Owner |
|---|---|---|---|
| **Schemes** | Off-invoice discounts, free goods, bundle packs | 10–15% | Finance + Sales |
| **Activation** | In-store events, demos, sampling | 2–4% | Marketing |
| **Visibility** | Shelf space, secondary display, end caps | 3–5% | Sales Ops / NKAM |
| **Digital Trade** | Online coupons, app promos, click&collect | 1–3% | D2C / E-com |
| **Field Force** | Promoter salaries, incentives | 4–6% | HR / Sales |
| **Total BTL** | Sum of all above | 20–30% | MT Lead |

**Target:** Total Trade Spend % of NSV ≤ 18–22% (varies by chain and brand maturity)

---

## Trade Spend ROI Calculation

```python
# Core ROI formula
trade_spend_roi = offtake_value_lakhs / trade_spend_lakhs

# Minimum viable ROI thresholds
ROI_BENCHMARKS = {
    "excellent":  2.0,   # ₹2 offtake per ₹1 spent — scale up
    "positive":   1.5,   # ₹1.5 offtake per ₹1 spent — maintain
    "breakeven":  1.0,   # ₹1 offtake per ₹1 spent — review
    "negative":  "<1.0", # Less offtake than spend — exit or restructure
}

# Incremental ROI (promo period vs baseline)
def promo_uplift_roi(offtake_promo, offtake_baseline, trade_spend):
    incremental_offtake = offtake_promo - offtake_baseline
    return incremental_offtake / trade_spend

# Payback period
def trade_payback_months(gm_lakhs, trade_spend_lakhs):
    monthly_gm = gm_lakhs
    return trade_spend_lakhs / monthly_gm if monthly_gm > 0 else float('inf')
```

---

## Promotion Types — Analysis Pattern

### 1. Scheme (Off-Invoice Discount)

**When to use:** Drive volume, clear old stock, defend vs competitor promo

**Analysis checklist:**
```
□ Offtake uplift during scheme period: target ≥ +20% vs baseline month
□ Post-scheme offtake: must not fall below baseline (if it does → pantry loading)
□ NSV impact: net NSV after scheme deduction vs pre-scheme baseline
□ GM% impact: scheme reduces NSV, COGS unchanged → GM% compresses
□ Recurrence risk: chains may demand same terms permanently
□ Return trigger: high scheme → high MRN in return months
```

**SQL pattern:**
```sql
SELECT
    chain_name,
    month_label,
    SUM(nsv_lakhs) AS primary_nsv,
    SUM(scheme_deduction_lakhs) AS scheme_cost,
    SUM(scheme_deduction_lakhs) / NULLIF(SUM(gross_billing_lakhs), 0) * 100 AS scheme_pct,
    SUM(offtake_value_lakhs) AS offtake_value,
    SUM(offtake_value_lakhs) / NULLIF(SUM(scheme_deduction_lakhs), 0) AS scheme_roi
FROM primary_fact
JOIN offtake_fact USING (month_label, chain_name)
WHERE month_label IN ('promo month', 'baseline month')
GROUP BY chain_name, month_label
ORDER BY scheme_roi ASC  -- worst ROI first
```

### 2. Visibility / Secondary Display

**When to use:** Drive new product trials, support launches, fight for shelf share

**Calculation:**
```
Visibility ROI = Offtake during display period / Visibility cost
Incremental Offtake = Offtake (display stores) - Offtake (non-display stores, same chain)
Payback threshold: Visibility cost < Incremental GM (i.e., ROI × GM% > 1)
```

**Decision rule:**
- If Incremental Offtake / Visibility Cost > 1.5 → repeat or expand
- If > 1.0 → maintain current level
- If < 1.0 → renegotiate location or exit this chain's secondary display

### 3. Activation (In-store Demo / Sampling)

**When to use:** New SKU launch, trial generation, consumer education

**Analysis pattern:**
```
□ Pre-launch offtake: 0 or baseline (new product)
□ During activation: gross sales in demo stores vs non-demo stores
□ Post-activation retention: % of consumers who repeat purchased in 4 weeks
□ Cost per trial = Activation cost / Units sampled
□ Trial-to-repeat conversion (target: ≥ 25%)
```

---

## Trade Investment Decision Framework

### When to INCREASE Trade Spend:
```
✓ Chain has high offtake potential (DOS < 15 days, consumers pulling)
✓ ROI > 1.5 consistently across 3+ months
✓ Distribution < 60% — investment unlocks new stores
✓ Competitor is investing — need to defend shelf
✓ New product launch (investment period, payback expected in 3–6 months)
✓ Key season (festive, summer) — demand spike, maximize shelf placement
```

### When to REDUCE Trade Spend:
```
✗ Chain DOS > 30 days — trade is stocking, not selling; more investment just adds DOS
✗ ROI < 1.0 for 2+ consecutive months
✗ GM% below 30% AND Trade Spend% above 20% (Channel EBITDA negative)
✗ Post-scheme offtake drops below pre-scheme baseline (pantry loading)
✗ Chain has been listing competition brands with same terms (retaliation risk)
✗ Reliance Brand Counter situation — separate rules apply (NKAM escalation)
```

### When to EXIT Trade Spend on a Chain/SKU:
```
✗ Channel EBITDA negative for 3+ consecutive months
✗ NSV < ₹2L/month and Trade Spend% > 25%
✗ Store coverage < 10% of chain footprint despite spend
✗ SKU velocity < 1 unit/store/month for 6+ months
```

---

## P&L Impact Analysis

When trade spend changes, trace the full P&L waterfall:

```
NSV (post-scheme)
  → Gross Margin = NSV × GM%
  → Less: BTL Trade Spend (schemes + activation + visibility)
  → Less: Field Force Cost
  = Channel EBITDA

Tolerance thresholds (from BUSINESS_RULES.md):
  Trade Spend%:     0% to 50% (>25% = flag for review)
  GM%:             -20% to 85% (outside = calculation error)
  Channel EBITDA:  Negative = blocked from release without Finance approval
```

---

## Monthly Trade Review Output Format

Report trade promotion analysis in this structure:

```
## Trade Promotion Review — [Month] [FY]

### Executive Summary
[1 sentence: total trade spend, ROI, key winner, key loser]

### Scheme Effectiveness by Chain
| Chain       | Scheme Cost (₹L) | Offtake Uplift | ROI  | Action |
|-------------|-----------------|----------------|------|--------|
| BigBasket   | 12.4            | +28%           | 1.8  | Scale  |
| DMart       | 8.1             | +6%            | 0.9  | Review |
| Reliance    | 15.2            | +31%           | 2.1  | Scale  |

### Visibility Investment Review
[ROI by chain + recommendation]

### Activation Results
[Trial rate, repeat rate, cost per trial]

### Recommendations
P1 — [Increase / Reduce / Exit] [Chain/Brand/Category] [Rationale] [₹L impact]
P2 — ...
P3 — ...

### Next Month Investment Plan
[Chain-wise trade budget with expected ROI and assumptions]
```

---

## Common Trade Spend Traps

1. **Scheme addiction** — chain demands permanent scheme after receiving it once. Rule: always time-bound schemes with exit criteria.

2. **DOS inflation** — high schemes push stock into trade that consumers don't pull. Trace: Primary NSV up, Offtake flat or down → DOS building.

3. **MRN spike after heavy scheme months** — returns spike 2–3 months after aggressive schemes. Always check MRN register before approving large schemes.

4. **Visibility spend without POS compliance check** — paying for shelf space that isn't implemented. Rule: activation team confirms before invoice is released.

5. **Promo cannibalisation** — scheme on Brand A kills Brand B in same chain. Check total brand family offtake, not just the promo SKU.

6. **Low DOS + high trade spend** — if DOS < 15 days AND trade spend > 20%, you're under-investing. Opportunity to grow.

---

## Integration with Other Skills

- Use **mt-financial-intelligence** for full P&L waterfall after trade changes
- Use **mt-intelligence-engine** for NKAM decision on which chains to invest in
- Use **mt-sql-analytics** for scheme ROI query, promo uplift calculation
- Use **mt-executive-storytelling** for writing the trade review narrative
- Use **mt-deck-builder** Slide 7 (P&L Waterfall) and Slide 9 (Action Grid) for deck output
