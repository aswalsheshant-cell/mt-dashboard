---
name: mt-growth-opportunity
description: "Quantifies and prioritises forward-looking sales-uplift opportunities in Modern Trade (MT) — distribution gaps (ND/WD/TDP), assortment and must-stock gaps, sell-through and days-of-supply, out-of-stock loss, gap-to-target bridges, promo/spend ROI, and mix or realisation upside. Use this skill whenever the user asks how to grow, increase, uplift or recover sales, asks 'where is the opportunity', 'how do we close the gap', 'what is the size of the prize', 'how much can we gain', wants an action plan with rupee value, asks about must-stock lists, store-count expansion, listing gaps, OOS, ROI on a promo, or planning the next month/quarter. Do NOT use for explaining why a past number moved (use mt-business-logic) or for wording the finding for leadership (use qbr-insight-writer)."
---

# MT Growth & Opportunity Sizing

Turns MT data into a **ranked, rupee-sized, owner-assigned list of things to do next**.
Where `mt-business-logic` explains what already happened, this skill quantifies what is
still available and what it is worth.

## Boundaries — do not overlap

| Question | Skill |
|---|---|
| Why did offtake decline in July | `mt-business-logic` |
| How do I phrase this for leadership | `qbr-insight-writer` |
| The number itself looks wrong | `mt-error-resolution` |
| Give me the formula / query / script | `excel-automation`, `mt-sql-analytics`, `mt-python-toolkit` |
| Where is the growth and what is it worth | **this skill** |

Handoff: `mt-business-logic` (diagnosis) → **this skill** (sizing and prioritisation) →
`qbr-insight-writer` (leadership wording) → `mt-deck-builder` (slide).

## The rule this skill exists to enforce

**No opportunity is stated without three things: a rupee value, a named owner, and a
date.** "We should improve availability in DMart" is not an output. "₹42 L/month
available from closing the 118-store gap on Ubtan FW 150 ml in DMart West — owner
NKAM DMart, listing PO by 25 Aug" is.

## Six opportunity pools — always check all six

Work through them in this order. The first three are usually the largest and the
cheapest to act on.

### 1. Distribution gap (the biggest and most controllable pool)

An article sells in some stores of a chain and not others. The gap is worth
(non-selling stores) × (average rate of sale in selling stores).

```
selling_stores          = distinct stores with units > 0 for that article
universe_stores         = stores of that chain that stock the category
nd_pct                  = selling_stores / universe_stores
rate_of_sale (ROS)      = article offtake units / selling_stores / months
distribution_gap_stores = universe_stores - selling_stores
opportunity_units/month = distribution_gap_stores × ROS
opportunity_value/month = opportunity_units × realisation per unit
```

Apply a **realism factor** before reporting: assume new stores reach 60–70 % of the
ROS of existing selling stores in the first three months. State the factor used.

Rank by opportunity value, then filter to what is actionable: a store that does not
stock the category at all is not a listing gap, it is a category-entry decision.

### 2. Assortment / must-stock gap

For each chain, define a must-stock list (the articles that deliver ~80 % of that
chain's category offtake — use the ABC cut). Then:

```
must_stock_compliance_pct = must-stock SKUs present / must-stock SKUs defined  (per store)
```

Report at chain level and at store level. The store-level tail — stores below 60 %
compliance — is where a merchandiser visit pays for itself. Size it the same way as
pool 1, restricted to must-stock SKUs.

### 3. Out-of-stock / availability loss

A store that sold an article in prior months and sold zero this month, with no
delisting, is an OOS event, not a demand drop.

```
oos_store_months  = stores with prior sales and zero units this month
oos_loss_value    = oos_store_months × ROS × realisation
```

Cross-check against primary: if primary held and offtake fell in the same stores,
stock sat in the DC or backroom — a supply-chain action, not a demand action.

### 4. Sell-through and days of supply

```
sell_through_pct = offtake units / (opening stock + receipts) units
days_of_supply   = closing stock units / (offtake units per day)
```

Reading:

| Days of supply | Meaning | Action |
|---|---|---|
| < 15 | Under-stocked, risk of OOS | Push replenishment PO |
| 15–45 | Healthy | Hold |
| 45–75 | Building | Slow primary, push offtake |
| > 75 | Over-stocked | Stop primary; returns/expiry risk; liquidation plan |

High days of supply plus strong primary growth is the classic **channel-loading**
signal — flag it as a risk, not a win, because it reverses next quarter.

### 5. Gap to target — always as a bridge, never as one number

Decompose the gap into buckets that each have a different owner:

```
target
  − volume/base run-rate gap        (owner: NKAM, chain)
  − distribution gap                (owner: NKAM / merchandising)
  − assortment / new-launch gap     (owner: category)
  − price-mix / realisation gap     (owner: pricing / trade marketing)
  − promo phasing gap               (owner: trade marketing)
  = actual
```

Every bucket carries a rupee value and sums to the total gap. A gap presented as a
single number cannot be actioned; a bridge can.

### 6. Mix and realisation upside

```
realisation_per_unit = offtake value / offtake units
```

Compare across chains and zones for the same article. A chain realising materially
below peers is either over-promoted, discount-heavy, or selling a lower pack mix —
size the upside as `(peer realisation − this realisation) × units`. Also check the
premium-pack share: shifting mix is often larger and cheaper than adding volume.

## Promo and spend ROI

Never approve or repeat a promo without this:

```
incremental_units  = promo-period units − baseline units (same store set, pre-promo run-rate)
incremental_value  = incremental_units × realisation
promo_spend        = discount value + visibility/listing fee + sampling + BTL
roi                = incremental_value / promo_spend
payback            = promo_spend / (incremental_value per month)
```

Rules:
- Baseline must be the **same store set**, not the chain total.
- Check the **post-promo dip**: if the four weeks after the promo fall below baseline,
  the promo pulled forward demand instead of creating it. Net the dip out of the
  incremental before reporting ROI.
- ROI below 1.0 means the promo destroyed value. Say so plainly.
- Report ROI on NSV, not MRP.

## Prioritisation — how to rank the list

Score each opportunity on three axes, then sort:

| Axis | Scale | What it means |
|---|---|---|
| Value | ₹/month | Sized with the realism factor applied |
| Effort | Low / Med / High | Listing PO = low; new chain entry = high |
| Speed | Weeks to realise | Availability fixes land in 2–4 weeks; listings in 6–12 |

Order the output: **high value + low effort + fast** first. Cap the list at 5–7 items.
A list of 30 opportunities is a report; a list of 6 is a plan.

## Standard output format

```
OPPORTUNITY: <one line, names the chain/article/geography>
SIZE:        ₹<x> L per month  (₹<y> Cr annualised)
BASIS:       <the calculation, with the inputs and the realism factor>
CONFIDENCE:  High / Medium / Low  — and what would raise it
ACTION:      <the specific thing to do>
OWNER:       <role — NKAM <chain> / RKAM <zone> / merchandising / trade marketing>
BY WHEN:     <date>
CHECK:       <the metric that will show it worked, and when it will be visible>
```

## Honesty rules

1. **Never fabricate a base number.** If the store universe, stock or target is not in
   the data, say exactly which file is needed and stop. An opportunity sized on a
   guessed universe is worse than no opportunity.
2. **State the realism factor every time.** An unadjusted distribution gap
   over-promises by roughly a third.
3. **Do not double-count pools.** A store that is both an OOS case and a must-stock gap
   belongs in one pool only — assign it to the pool whose action would fix it.
4. **Annualise only when the driver is structural.** A listing gap annualises; a
   festive-month spike does not.
5. **Separate "available" from "committed".** Sized opportunity is not a revised
   forecast until an owner has accepted it.
6. If the sized opportunity exceeds ~15 % of the current base, re-check the inputs
   before presenting — that is usually a universe or grain error, not a windfall.

## Quick diagnostic ladder

When asked "where is the growth?", answer in this order:

1. Which chains are below their fair share of category offtake? (share-of-category gap)
2. Within those chains, which articles are under-distributed? (pool 1)
3. Within those articles, which stores are non-selling or OOS? (pools 2 and 3)
4. Is stock the constraint or is demand? (pool 4 — days of supply)
5. What does the gap-to-target bridge say is missing? (pool 5)
6. Is there realisation or mix upside on top? (pool 6)

That ladder goes from ₹ crores of ambition to a specific store list in five steps,
which is what makes it actionable.
