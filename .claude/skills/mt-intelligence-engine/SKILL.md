---
name: mt-intelligence-engine
description: |
  AI-powered insight generation, NKAM decision recommendations, regional performance
  diagnosis, root cause analysis, and executive insight generation for the Honasa MT
  Analytics Platform. Use this skill when the user asks for: insights from data,
  what the numbers mean for the business, which chains to grow, where to find opportunity,
  why a number changed, root cause of a miss, regional weak spots, store recommendations,
  distribution gap analysis, or says: "what does this tell us", "find opportunities",
  "why did this drop", "which chain is struggling", "root cause", "give me insights",
  "AI report planner", "what should NKAM focus on", "regional analysis", "weak BDE",
  "coverage gap", "growth hotspot", "SKU opportunity", "price opportunity",
  "promotion opportunity", "what actions should we take".
  Always connects numbers to decisions — never just shows data.
---

# MT Intelligence Engine

AI-driven decision support for NKAM, Regional Managers, and leadership — converting
MT analytics data into prioritized actions and opportunity identification.

## Executive Insight Standard

Every insight MUST answer all nine questions — never show a number without context:

```
EXECUTIVE INSIGHT TEMPLATE
━━━━━━━━━━━━━━━━━━━━━━━━━━
What changed?        [metric + quantified delta, e.g. "D-Mart NSV fell ₹8.2L, -14% MoM"]
Why?                 [primary driver — ONE cause explaining >60% of variance]
Business impact?     [revenue, margin, or share consequence in ₹L or pp]
Financial impact?    [GM or EBITDA effect]
Owner?               [NKAM / RSM / Supply / Finance / Category]
Priority?            [Critical / High / Medium / Low]
Recommended action?  [one specific, time-bound action]
Expected gain?       [quantified if possible — "₹5–8L recovery in 4 weeks"]
Confidence?          [High / Medium / Low — based on data quality and sample size]
```

## Root Cause Analysis Engine

Trigger automatically when any metric variance exceeds threshold.

### Variance Thresholds
| Metric | Threshold | Auto-trigger |
|---|---|---|
| Chain NSV MoM | ±15% | Yes |
| GM % MoM | ±3pp | Yes |
| Offtake vs Primary gap | >10% | Yes |
| Distribution MoM | ±5pp | Yes |
| Trade Spend % | >25% NSV | Yes |
| Market Share | ±1pp | Yes |

### Root Cause Decision Tree

```
Variance detected → Run through this sequence:

1. PRICE driver?
   → Check: avg price per unit this month vs prior
   → If price dropped: promo / scheme / mix shift to lower SKU

2. DISTRIBUTION driver?
   → Check: numeric distribution this month vs prior
   → If stores lost: delisting, OOS, shelf space cut

3. LISTING driver?
   → Check: active SKU count this month vs prior
   → If SKUs reduced: channel rationalization, compliance

4. INVENTORY driver?
   → Check: days of supply at chain level
   → If DOS high: overbuild from prior push (drawdown phase)
   → If DOS low: OOS / supply failure

5. RETURNS driver?
   → Check: MRN / return rate vs prior period
   → If returns spiked: damage, expiry, scheme closure returns

6. PROMOTION driver?
   → Check: trade spend % this month
   → If spend high: planned activation (expected); unplanned: investigate

7. EXECUTION driver?
   → Check: same-store growth for top 20 stores
   → If existing stores flat but new stores added: footprint, not execution

8. SEASONALITY driver?
   → Check: same month prior year
   → If pattern repeats: seasonal — adjust forecast, not actions

9. SUPPLY driver?
   → Check: order fill rate from warehouse
   → If fill rate <95%: supply chain issue — escalate

10. MASTER DATA driver?
    → Check: any new mapping added / chain split / store realigned
    → Reclassification can shift numbers without business change
```

## NKAM Decision Engine

For each key account, auto-generate decision recommendations — not charts:

```python
def nkam_recommendations(chain_data: dict) -> list[dict]:
    """
    chain_data = {
        "chain": "D-Mart",
        "nsv_trend": "declining",  # growing / flat / declining
        "gm_pct": 36.2,
        "offtake_vs_primary_gap": 18.5,  # % — primary > offtake = inventory build
        "numeric_dist": 74,
        "target_dist": 82,
        "dos": 28,                  # days of supply (norm = 18)
        "top_skus_share": 72,       # top 5 SKUs = 72% of NSV
        "slow_sku_count": 8,        # SKUs below threshold velocity
        "listing_opportunity": 4,   # SKUs listed at competitor but not here
        "trade_spend_pct": 14.2,
    }
    """
    recs = []

    if chain_data["nsv_trend"] == "declining":
        recs.append({"priority": "Critical", "action": "Investigate NSV decline",
                     "type": "Revenue", "owner": "NKAM"})

    if chain_data["offtake_vs_primary_gap"] > 15:
        recs.append({"priority": "High", "action": "Pause primary billing — DOS elevated",
                     "type": "Inventory", "owner": "NKAM + Supply"})

    if chain_data["numeric_dist"] < chain_data["target_dist"]:
        gap = chain_data["target_dist"] - chain_data["numeric_dist"]
        recs.append({"priority": "High",
                     "action": f"Close {gap}pp distribution gap — target {chain_data['target_dist']}%",
                     "type": "Distribution", "owner": "NKAM"})

    if chain_data["slow_sku_count"] > 5:
        recs.append({"priority": "Medium",
                     "action": f"Review {chain_data['slow_sku_count']} slow SKUs for rationalization",
                     "type": "Portfolio", "owner": "Category + NKAM"})

    if chain_data["listing_opportunity"] > 0:
        recs.append({"priority": "Medium",
                     "action": f"List {chain_data['listing_opportunity']} incremental SKUs available at competitor",
                     "type": "Listing", "owner": "NKAM"})

    return sorted(recs, key=lambda x: {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}[x["priority"]])
```

### NKAM Opportunity Matrix (output format)

```
CHAIN: D-MART — JUNE FY27 OPPORTUNITY SCAN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[CRITICAL] Revenue: NSV declining 3 consecutive months — root cause: distribution loss
[HIGH]     Inventory: DOS at 28 days vs 18-day norm — pause next 2 billing cycles
[HIGH]     Distribution: 74% vs 82% target — identify 12 non-compliant stores
[MEDIUM]   Portfolio: 8 slow SKUs below 2 units/store/month threshold
[MEDIUM]   Listing: 4 SKUs available at Big Basket not yet listed at D-Mart
[LOW]      Price: Avg pack price ₹2 below recommended — check scheme netting

Top 5 stores by opportunity (offtake uplift potential):
  Store 1 | Site 4821 | Current ₹0.8L | Benchmark ₹1.4L | Gap ₹0.6L
  Store 2 | Site 3190 | Current ₹0.6L | Benchmark ₹1.1L | Gap ₹0.5L
```

## Regional Manager Engine

Auto-identify weak and strong geographies:

```
REGIONAL PERFORMANCE SCAN
━━━━━━━━━━━━━━━━━━━━━━━━━
Weak States (NSV declining or >20% below target):
  Maharashtra: -12% vs target — primary driver: D-Mart listing loss in Mumbai
  Karnataka:   -8% vs target  — primary driver: distributor coverage gap in Tier-2

Weak Cities (bottom quartile offtake/store):
  Pune:      ₹0.9L/store vs ₹1.4L benchmark (-36%)
  Hyderabad: ₹1.1L/store vs ₹1.4L benchmark (-21%)

Weak Distributor:
  [Distributor X] — fill rate 87% (target 95%), 3 consecutive months
  Action: escalate to supply chain; review MSL compliance

Weak Supervisor / BDE:
  [Supervisor Y] — 6 stores below 50% target achievement
  Action: field review + coaching plan

Growth Hotspots (above benchmark + positive trend):
  Chennai: +18% YoY, distribution expanding — invest in activations
  Ahmedabad: New stores outperforming — prioritize listing

Priority Stores (highest recovery opportunity):
  Top 10 stores × (benchmark − actual offtake) sorted descending
```

## AI Report Planner

Before creating any new dashboard page or report, answer:

```
REPORT PLANNING BRIEF
━━━━━━━━━━━━━━━━━━━━
Business Goal:      [what decision does this enable?]
Audience:           [NKAM / RSM / VP Sales / MD / Finance]
Primary KPIs:       [max 5 — ranked by importance]
Secondary KPIs:     [supporting metrics]
Drill Path:         [MT Total → Chain → State → City → Store → SKU]
Filter Dimensions:  [FY / Chain / Brand / Category / Region / Month]
Navigation:         [where does this page sit in the dashboard flow?]
Executive Story:    [the one-sentence takeaway this page answers]
Mobile Layout:      [yes/no — does leadership view on phone?]
Action Trigger:     [what should the reader DO after seeing this page?]
```

## Forecast Intelligence Framework

Every forecast must include all dimensions:

```
FORECAST OUTPUT STRUCTURE
━━━━━━━━━━━━━━━━━━━━━━━━
Period: [FY27 Q2 — Jul, Aug, Sep]
Base assumption: [current run rate × seasonal factor]

Expected (P50):    ₹XXX L  — base case, no significant events
Best case (P90):   ₹XXX L  — positive assumptions: distribution win + promotion uplift
Worst case (P10):  ₹XXX L  — downside: OOS risk + competitor promo

Key Risk factors:
  Seasonality:    [Monsoon / Festival effect — % adjustment]
  Festival:       [Navratri / Diwali / year-end — timing and impact]
  Distribution:   [Planned new store additions / delistings]
  NPI:            [New products launching — contribution timeline]
  Inventory:      [Current DOS at chain — affects near-term billing]
  Supply Risk:    [Fill rate trend — any SKU at risk?]
  Target:         [FY27 target implied run rate — gap to cover]

Confidence:       [High / Medium / Low]
Target Achievement probability: XX%

Forecast Accuracy Monitor (vs prior forecast):
  Last month forecast: ₹XXX L
  Actual:              ₹XXX L
  Variance:            ₹XX L (±X%)
  Miss driver:         [one sentence]
```
