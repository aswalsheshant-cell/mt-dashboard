---
name: mt-campaign-analytics
description: |
  Design, measure, and optimise promotional campaigns and experiments for Modern Trade channels.
  Use when user asks about "promo experiment", "A/B test this scheme", "which promo works better",
  "measure campaign uplift", "ICE score this", "attribution for this activation", "promo hypothesis",
  "test vs control", "campaign ROI", "which activation drove offtake", "promo measurement",
  "campaign design", "scheme experiment", "activation measurement", "promo test design",
  "what is driving offtake", "attribution model", "AARRR for MT".
  Do NOT use for scheme ROI benchmarking (→ mt-trade-promotion) or full P&L waterfall (→ mt-financial-intelligence).
---

# MT Campaign Analytics

Design rigorous promo experiments, measure attribution, and prioritise campaign investments
using structured frameworks adapted from marketing science for the MT channel context.

---

## AARRR Framework — MT Channel Mapping

| AARRR Stage | Marketing Definition | MT Equivalent | Primary Metric |
|---|---|---|---|
| **Acquisition** | Attract new users | New store listings secured | Numeric Distribution % |
| **Activation** | First value moment | First offtake from newly listed stores | First-month sell-through rate |
| **Retention** | Keep them coming back | Sustained weighted distribution + repeat offtake | Weighted Distribution %; MoM offtake stability |
| **Referral** | Word of mouth | Chain expanding to new zones / new stores | Coverage expansion % |
| **Revenue** | Monetise | NSV net of trade spend | NSV (₹L); Channel EBITDA |

**Decision rule:** Fix each stage left to right. Do not invest in Retention spend while Acquisition (distribution) is below 60%. Do not invest in Activation before the product is listed.

---

## Promo Experiment Design

### Hypothesis Template (mandatory before any experiment)

```
HYPOTHESIS STATEMENT
──────────────────────────────────────────────────────────────────
Because [observed problem / market insight],
we believe [specific intervention — e.g. "a ₹5 off-invoice scheme on SKU X at BigBasket"]
will cause [measurable outcome — e.g. "+25% offtake uplift and +8pp distribution"]
for [target audience — e.g. "urban tier-1 BigBasket shoppers"]
during [time window — e.g. "Aug-26, 4 weeks"].

We'll know it worked when:
  Primary metric: [e.g. offtake_value_lakhs ↑ ≥ 25% vs Jun-26 baseline]
  Guardrail metrics (must not worsen): [e.g. GM% ≥ 35%, MRN rate ≤ 5%]
  We'll know it FAILED when: [e.g. offtake uplift < 10% OR MRN spike > 3× baseline]
──────────────────────────────────────────────────────────────────
```

### ICE Scoring — Prioritise Which Experiment to Run First

```python
# ICE = Impact × Confidence × Ease   (each scored 1–10)
def ice_score(impact, confidence, ease):
    return impact * confidence * ease

# MT-specific scoring guidance:
# Impact:     1 = NSV <₹5L, 5 = ₹20L, 10 = ₹50L+ potential uplift
# Confidence: 1 = no prior data, 5 = one prior test, 10 = 3+ repeatable results
# Ease:       1 = requires custom contract renegotiation, 5 = existing scheme template, 10 = self-serve

ICE_PRIORITY = {
    ">500": "P1 — run this month",
    "300-500": "P2 — queue for next month",
    "100-300": "P3 — plan but deprioritise",
    "<100": "Kill — not worth the coordination cost",
}
```

### Control Group Design

| Method | When to Use | MT Example |
|---|---|---|
| **Geographic split** | Chain has zones | BigBasket North = test; BigBasket South = control |
| **Store cohort split** | Chain has SKU-level store data | Even-numbered store IDs = test; odd = control |
| **Time-based** | No geography split available | Compare 4-week promo vs 4-week pre-promo baseline |
| **Matched pair** | Similar stores in same chain | Match on pre-period offtake velocity, distribution overlap |

**Minimum sample size:** ≥ 20 stores per arm for statistical significance. Below 20 stores → report directional only, not conclusive.

---

## Attribution Models

Choose an attribution model based on the type of investment being evaluated:

| Model | Formula | Best for MT Use |
|---|---|---|
| **First-touch** | 100% credit to first touchpoint | New product launch — what drove first listing? |
| **Last-touch** | 100% credit to final touchpoint | Conversion at POS — what triggered the purchase? |
| **Linear** | Equal credit across all touchpoints | Multi-month scheme + activation combo evaluation |
| **Time-decay** | Exponential decay; recent events weight more (7-day half-life) | Season-end or festive surge attribution |
| **Position-based (U-shaped)** | 40% first + 40% last + 20% distributed to middle | Full funnel: listing → visibility → scheme → offtake |

**MT source of truth principle** (analogous to marketing's "backend > reporting tools"):
Primary invoiced billing (NSV) is the source of truth for revenue attribution — not platform-reported offtake. When platform offtake diverges from primary, always reconcile to primary before attributing uplift.

---

## Promo Uplift Measurement

### Before–After Analysis (most common)

```python
def measure_promo_uplift(offtake_promo_period, offtake_baseline_period,
                          trade_spend_lakhs, gm_pct):
    """
    offtake_promo_period: ₹L offtake during promotion
    offtake_baseline_period: ₹L offtake in equivalent pre-promo period
    trade_spend_lakhs: total scheme + activation cost
    gm_pct: gross margin % (e.g. 0.38 for 38%)
    """
    incremental_offtake = offtake_promo_period - offtake_baseline_period
    promo_roi = incremental_offtake / trade_spend_lakhs if trade_spend_lakhs > 0 else float('inf')
    incremental_gm = incremental_offtake * gm_pct
    net_campaign_profit = incremental_gm - trade_spend_lakhs

    return {
        "incremental_offtake_lakhs": round(incremental_offtake, 2),
        "promo_roi": round(promo_roi, 2),
        "incremental_gm_lakhs": round(incremental_gm, 2),
        "net_campaign_profit_lakhs": round(net_campaign_profit, 2),
        "verdict": "SCALE" if promo_roi > 1.5 else
                   "MAINTAIN" if promo_roi > 1.0 else "EXIT",
    }
```

### Test vs Control Uplift (when control group available)

```python
def test_vs_control_uplift(test_offtake, control_offtake, trade_spend):
    baseline_scaled = control_offtake  # control group = counterfactual
    true_incremental = test_offtake - baseline_scaled
    incremental_roi = true_incremental / trade_spend if trade_spend > 0 else float('inf')
    return true_incremental, incremental_roi
```

---

## Post-Promo Diagnostic Checks

After every promotion period, run these checks in order:

```
□ 1. OFFTAKE RETENTION: post-promo month offtake ≥ pre-promo baseline?
      If not → pantry loading; do not repeat scheme
□ 2. DOS CHECK: days-of-supply at end of promo ≤ 21 days?
      If DOS > 30 → trade stocked up, consumers didn't pull
□ 3. MRN SPIKE CHECK: returns in next 2 months ≤ 5% of promo-period primary NSV?
      If > 5% → channel returning unsold stock from pantry load
□ 4. DISTRIBUTION HOLD: % stores stocked stayed flat or grew vs pre-promo?
      Drop in distribution after promo → scheme was subsidising poor-fit stores
□ 5. BRAND FAMILY CHECK: did scheme on Brand A suppress Brand B offtake in same chain?
      Total brand family offtake must be compared, not just the promo SKU
```

---

## Marketing Psychology Mental Models for MT Decisions

### Theory of Constraints

Fix the binding constraint before adding investment. Order of priority:
1. **Distribution** — if stores aren't listed, no scheme or activation will drive offtake
2. **Visibility** — if product is listed but buried, fix shelf placement first
3. **Pricing** — if RSP is uncompetitive, activation can't close the gap
4. **Scheme** — only layer in after the above are addressed

### Pareto 80/20 for MT

```
Top 20% of SKUs → drive 80% of NSV
Top 20% of stores → drive 80% of offtake
Action: cut tail SKUs and low-velocity stores before adding activation spend
```

### Second-Order Thinking (Hormozi Value Equation adapted for MT)

```
Trade Investment Value = (Offtake Dream Outcome × Confidence in Plan) / (Execution Time × Channel Resistance)

Second-order check: "What does this promo train the channel to expect?"
  Off-invoice discount → chain expects permanent terms next cycle
  Visibility payment → chain expects annual renewal at same or higher cost
  Activation → chain expects brand-funded demo for every new SKU

Mitigation: always time-bound with explicit exit criteria written into the scheme letter
```

---

## Repeatable Campaign Measurement Loop

For each campaign cycle, run this structured loop:

```
1. PRE-CAMPAIGN (Week -1)
   □ Confirm hypothesis and guardrail metrics in writing
   □ Record baseline: offtake_L3M_avg, DOS, distribution_%
   □ ICE score to confirm this is the priority experiment
   □ Define test/control split and confirm store list

2. DURING CAMPAIGN (Weekly check-in)
   □ Offtake velocity vs. target trajectory (not just final number)
   □ POS compliance confirmed by activation team (visibility only)
   □ DOS not building beyond trigger (> 21 days = pause scheme)

3. POST-CAMPAIGN (Week +1, +4, +8)
   □ Week +1: immediate uplift measurement
   □ Week +4: retention check (offtake ≥ pre-promo baseline?)
   □ Week +8: MRN spike scan, DOS normalisation confirmed
   □ Write campaign result to NKAM decision log (→ mt-channel-decision-log)
   □ Update ICE confidence score based on result
```

---

## Campaign Report Output Format

```
## Campaign Measurement Report — [SKU] × [Chain] × [Month]

### Experiment Summary
Hypothesis: [verbatim hypothesis statement]
Test design: [Before-after / Test-control]; [N] stores

### Results
| Metric | Baseline | Promo Period | Post-Promo | vs Hypothesis |
|---|---|---|---|---|
| Offtake (₹L) | X | Y | Z | ✓/✗ |
| Incremental offtake (₹L) | — | Y-X | — | |
| Trade spend (₹L) | — | TS | — | |
| Promo ROI | — | (Y-X)/TS | — | |
| DOS (days) | D | D' | D'' | |
| MRN spike | — | — | R% | |

### Verdict
[SCALE / MAINTAIN / EXIT] — [1-sentence rationale]

### Next Experiment
[Updated ICE score] — [Next hypothesis building on this result]
```

---

## Integration with Other Skills

- Use **mt-trade-promotion** for scheme ROI benchmarking and ROPE analysis
- Use **mt-financial-intelligence** for full P&L waterfall after campaign
- Use **mt-channel-decision-log** to record campaign decisions and outcomes
- Use **mt-sql-analytics** for offtake uplift SQL queries
- Use **mt-deck-builder** Slide 8 (Root Cause Deep Dive) to present campaign results
