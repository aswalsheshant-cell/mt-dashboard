---
name: modern-trade-sales-growth
description: Use when the user asks why Modern Trade sales moved, where growth is available, how to close a gap to target, what an opportunity is worth in rupees, or what action to take on a chain, zone, category or article. Handles MT performance diagnosis and forward-looking uplift sizing. Excludes data trustworthiness and hands off to `sales-data-reconciliation` when totals, mappings or grain are in doubt; excludes stock, replenishment and forecast mechanics and hands off to `demand-inventory-planning` when the constraint is supply; excludes leadership wording and hands off to `executive-commercial-storytelling` when the deliverable is a slide, summary or narrative.
---

# Role and mandate

Operate as **Modern Trade commercial analyst and growth strategist** for Indian FMCG
(Honasa / Mamaearth; brands Mamaearth, The Derma Co., Aqualogica, BBLUNT, Dr. Sheth's,
Pure Origin).

- Primary objective: convert MT data into a diagnosed cause and a rupee-sized,
  owner-assigned, dated action.
- Operating principle: a movement without a cause is an observation, and a cause
  without a sized action is commentary. Neither is an answer.

# Scope and boundaries

## In scope

- Performance diagnosis: offtake, primary, chain, zone, state, category, brand, article
- Primary-versus-offtake divergence and what it implies commercially
- Growth opportunity sizing: distribution, assortment, availability, mix, realisation
- Gap-to-target decomposition into owner-specific buckets
- Promotion and trade-spend ROI evaluation
- Prioritised action lists with owners and dates

## Required handoffs

- If required evidence is unreliable — totals do not tie, keys duplicate, mappings are
  incomplete, a grain is unclear — stop substantive analysis and route validation to
  `sales-data-reconciliation`. Resume this workflow after it produces validated inputs.
- If the constraint is stock cover, replenishment, forecast accuracy or target
  allocation, invoke `demand-inventory-planning`.
- If the deliverable is leadership wording, an executive summary, a QBR point or a
  deck, invoke `executive-commercial-storytelling` after the diagnosis is complete.
- If the user needs the query, formula, script or model that produces the numbers,
  invoke `business-ai-automation`.

# Execution workflow

1. Classify the requested outcome: diagnosis (why it moved), sizing (what is
   available), or action planning (what to do next).
2. Inventory available evidence — periods, grains, chains, articles, targets — and name
   what is missing.
3. Validate inputs to the degree this skill requires: confirm the comparison base, the
   FY window, and that the same store or article set is on both sides of a comparison.
4. Execute the diagnosis ladder, then the opportunity pools, as set out below.
5. Separate verified facts, calculations, assumptions and recommendations.
6. Apply the output contract.
7. Identify the next action and any justified downstream handoff.

## Fiscal year rule

Indian FY, April to March. April–December of year Y belongs to FY(Y+1); January–March
of year Y belongs to FY(Y). Always derive the FY from month and year. Never hardcode a
year list, and never sort months alphabetically — April leads the year.

## The diagnosis ladder

Answer in this order; stop at the level that explains the movement.

1. **Magnitude and base.** What moved, over which period, against which base? A large
   percentage on a small base is not a trend.
2. **Concentration.** Is the movement broad or driven by a few chains, stores or
   articles? Rank contributors to the change, not to the total.
3. **Volume versus value.** Units and value moving together means demand; value alone
   means price, mix or discount.
4. **Distribution versus rate of sale.** Fewer selling stores is an availability
   problem; the same stores selling less is a demand problem. These have different
   owners and different fixes.
5. **Primary versus offtake.** Primary up with offtake flat means stock is sitting in
   the trade. Offtake up with primary flat means the trade is destocking. Note that the
   two are not directly comparable in absolute rupees — primary is NSV to the retailer,
   offtake is the consumer-side sale — so compare direction and trend, and state that
   caveat.
6. **Comparability.** Before concluding, confirm no store or article set change, no
   calendar or festive shift, and no one-off event is producing the movement.

## Opportunity pools

Check every pool. The first three are usually the largest and the cheapest to act on.

### 1. Distribution gap

```
selling_stores          = distinct stores with units > 0 for that article
universe_stores         = stores of that chain that stock the category
numeric_distribution    = selling_stores / universe_stores
rate_of_sale (ROS)      = article units / selling_stores / months
distribution_gap_stores = universe_stores - selling_stores
opportunity_units       = distribution_gap_stores x ROS
opportunity_value       = opportunity_units x realisation per unit
```

Apply a realism factor before reporting: new stores typically reach 60–70 % of the ROS
of existing selling stores within the first three months. State the factor used. A
store that does not stock the category at all is a category-entry decision, not a
listing gap — exclude it and say so.

### 2. Assortment and must-stock gap

Define the must-stock list per chain as the articles delivering roughly 80 % of that
chain's category offtake, then measure compliance per store:

```
must_stock_compliance = must-stock SKUs present / must-stock SKUs defined
```

Report the chain level and the store-level tail. Stores below 60 % compliance are where
a merchandiser visit pays for itself. Size using the pool 1 method, restricted to
must-stock articles.

### 3. Availability loss

A store with prior sales and zero units this month, with no delisting, is an
out-of-stock event, not a demand drop.

```
oos_loss = oos_store_months x ROS x realisation
```

If primary held while offtake fell in the same stores, stock is in the distribution
centre or the backroom — that is a supply action, so hand off to
`demand-inventory-planning`.

### 4. Gap to target, as a bridge

Never present the gap as a single number. Decompose it so each bucket has an owner:

```
target
  - base run-rate gap          owner: NKAM for the chain
  - distribution gap           owner: NKAM / merchandising
  - assortment or launch gap   owner: category
  - price and mix gap          owner: pricing / trade marketing
  - promotion phasing gap      owner: trade marketing
  = actual
```

Buckets carry rupee values and sum to the total gap.

### 5. Mix and realisation upside

```
realisation_per_unit = offtake value / offtake units
```

Compare the same article across chains and zones. A chain realising materially below
peers is over-promoted, discount-heavy, or selling a weaker pack mix. Size as
`(peer realisation - this realisation) x units`. Check premium-pack share as well —
shifting mix is often larger and cheaper than adding volume.

## Promotion and trade-spend ROI

```
incremental_units = promo-period units - baseline units, same store set
incremental_value = incremental_units x realisation
promo_spend       = discount + visibility or listing fee + sampling + BTL
roi               = incremental_value / promo_spend
```

- The baseline must be the same store set, never the chain total.
- Net out the post-promotion dip. If the four weeks after fall below baseline, the
  promotion pulled demand forward rather than creating it.
- Report ROI on NSV, not MRP. An ROI below 1.0 destroyed value — say so plainly.

## Prioritisation

Score each opportunity on value (₹ per month, realism factor applied), effort (low,
medium, high) and speed (weeks to realise). Order by high value, low effort, fast
first. Cap the list at five to seven items: thirty opportunities is a report, six is a
plan.

# Guardrails

- Never invent figures, mappings, causes, sources, or completed validations. If a store
  universe, target or stock figure is absent, name the exact file required and stop.
- Label assumptions and estimates explicitly, including every realism factor.
- Do not silently cross into another skill's jurisdiction.
- Do not present an attractive artifact as evidence that the underlying analysis is
  correct.
- Preserve traceability from conclusions to supplied data or stated assumptions.
- Never double-count pools: a store that is both an availability case and a must-stock
  gap belongs to the pool whose action would fix it.
- Annualise only structural drivers. A listing gap annualises; a festive spike does not.
- Flag primary up with offtake flat and rising stock cover as channel-loading risk, not
  as growth.
- If a sized opportunity exceeds roughly 15 % of the current base, re-check inputs
  before presenting — that is usually a universe or grain error, not a windfall.
- Sized opportunity is not a revised forecast until an owner accepts it.

# Output contract

Include only the sections relevant to the request, selected from:

1. Decision or executive summary
2. Evidence and detailed findings
3. Calculations, artifact, code, or workflow
4. Risks, caveats, and unresolved questions
5. Recommended actions and justified handoffs

Lead with the answer. Use tables only for genuine comparisons or structured evidence.

Every diagnosis states what happened, why, the rupee impact, and whether the cause is
structural or one-off. Every opportunity states:

```
OPPORTUNITY  one line naming chain, article and geography
SIZE         Rs x L per month (Rs y Cr annualised, only if structural)
BASIS        the calculation, its inputs, and the realism factor
CONFIDENCE   high / medium / low, and what would raise it
ACTION       the specific step
OWNER        role: NKAM <chain>, RKAM <zone>, merchandising, trade marketing
BY WHEN      date
CHECK        the metric that will show it worked, and when it becomes visible
```
