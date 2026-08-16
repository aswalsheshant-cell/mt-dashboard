# Market share, Nielsen and distribution points

Competitive position measurement. Share answers a question growth numbers cannot: did
the business grow because the category grew, or because it took share from someone.

## The two questions share answers

```
category_growth  = category value this period / category value base period - 1
brand_growth     = brand value this period / brand value base period - 1
share            = brand value / category value
share_change_bps = (share_now - share_base) x 10000
```

- Brand growing **slower** than the category means losing share while growing. This is
  the case most often missed, because the internal number looks positive.
- Brand growing while the category shrinks means gaining share in a declining pool —
  worth defending but not worth scaling investment into.

Report share movement in **basis points**, not percentage points of a percentage. "Share
up 40 bps to 6.2 %" is unambiguous; "share up 0.4 %" is not.

## Reading Nielsen data

Measures in the Nielsen extracts used here: URB (urban) market share by value and by
volume, brand share, and pack or format splits such as Bottles. Value share and volume
share moving in opposite directions is a pricing or mix story, not a demand story —
volume share up with value share down means the brand is buying share with discount.

Nielsen panel coverage is not the same universe as internal offtake. Never reconcile a
Nielsen number to an internal number and never present the difference as an error. Use
Nielsen for relative position and trend, internal data for absolute performance.

Nielsen periods lag. State the period on every share figure and never compare a Nielsen
period to an internal period of different length or timing.

## Competitor movement

For any share change, decompose where it came from:

```
share_gained_from = competitor whose share fell by a matching amount in the same period
```

A share gain with no matching competitor loss usually means the category definition
changed, a new entrant diluted the base, or the panel composition moved. Check before
claiming a win.

## TDP — total distribution points

TDP measures how widely the portfolio is present, weighting each store by the number of
SKUs it carries.

```
TDP            = sum over stores of (SKUs carried in that store)
avg_SKUs_per_store = TDP / selling stores
```

Rising TDP with flat offtake means distribution is being added where it does not sell —
a targeting problem, not a listing problem. Falling TDP with flat offtake means the
portfolio is concentrating into productive stores, which is often good.

Pair TDP with numeric distribution: numeric distribution says how many stores stock
anything, TDP says how much of the range they stock. A chain can be at 95 % numeric
distribution and still carry only two SKUs per store.

## Where this sits

Share and TDP are diagnostic inputs to `modern-trade-sales-growth`, not a separate
workflow. Use them at step 2 of the diagnosis ladder — concentration — and again when
sizing the assortment gap, where the must-stock list should reflect what competitors
carry, not only what already sells.

Data quality on any Nielsen or TDP file goes to `sales-data-reconciliation` first: these
extracts change column layout between releases more often than internal sources do.

Power BI measures already exist — `PowerBI/DAX/04_Nielsen_Measures.dax` and
`PowerBI/DAX/05_TDP_Measures.dax`. Search them before writing a new one.
