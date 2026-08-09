# Exception thresholds, ownership map and diagnosis confirms

Exception-based reporting means surfacing only what breaches a threshold. Without
stated numbers that becomes a judgement call every cycle, and the same table gets dumped
in full. These are the standing thresholds.

## Thresholds — flag only what breaches

| Condition | Threshold | Why it matters |
|---|---|---|
| Article or chain decline | Worse than **-10 %** MoM or YoY | Below this is normally noise or phasing |
| Store or chain achievement | Below **90 %** of plan | The level at which a gap needs an owner |
| Ageing stock | **DOI above the agreed cover** for that chain | Returns, expiry and a future primary cut |
| Out-of-stock risk | **DOI near zero**, or a store with prior sales at zero units | Lost offtake that looks like lost demand |
| Chain concentration | Top-3 chains crossing the agreed risk share | Over-dependence on a few accounts |
| Zero billing | Any chain that **dropped to zero** versus last month | Almost always a data or listing break, not demand |
| Unmapped records | Any unmapped chain, store, article or EAN | Blocks release — route to `sales-data-reconciliation` |

Where a chain-specific agreed DOI cover exists, it wins over any generic band. State
which cover was applied.

Do not dump the full table. Report the breaches, their size in rupees, and nothing else.
If nothing breaches, say so in one line — that is a valid and useful answer.

## Ownership map — every action gets one owner

| Cause | Owner |
|---|---|
| Listing or assortment gap | **NKAM / RKAM** — close the listing in the chain |
| Out-of-stock, low stock, DOI near zero | **NKAM + Supply** |
| Pricing or ASP movement | **Category + KAM** |
| Scheme, visibility, POSM pullback | **Trade Marketing / BD** |
| Ageing stock, over-cover, liquidation | **Supply + Category** |
| Master data or mapping error | **Analyst (self)** |
| Forecast or target phasing error | **Analyst (self) + Category** |

"Monitor closely" is not an action and has no owner. If no specific step can be named,
say what evidence is missing to name one.

## Offtake decline — cause table with quick confirms

Work down the list. The first check that fits is usually the cause. Each row pairs the
cause with the check that confirms or rules it out in a single cut.

| Check | Likely cause | Quick confirm |
|---|---|---|
| Article missing or not billing in some stores | Distribution / listing gap | Count active stores this month versus last; look for stores that dropped to zero |
| Fewer SKUs selling than planned | Assortment gap | Live SKU count versus planned assortment for that chain |
| ASP moved up sharply | Pricing / MRP change | ASP (NSV ÷ Units) MoM; a jump with a unit drop is price resistance |
| Units flat but value down | Mix or pack-size shift | Share of large versus small packs |
| Stock low or zero in stores | OOS / DOI problem | Closing stock and DOI; low DOI with falling offtake is a supply issue |
| Scheme or visibility ended | Promo or POSM pullback | Did a scheme or display run in the base month but not now |
| Base month unusually high | Base effect | LY and last-month values; a one-off spike inflates the comparison |

If two causes overlap — out-of-stock plus a scheme ending, for example — name both and
rank them by size of impact rather than picking one.

## Primary versus offtake — pipeline health

Always read the pair together; neither number means much alone.

| Pattern | Reading | Action leans to |
|---|---|---|
| Primary up, offtake flat or down | Stock loading into the chain without selling out | Supply and Category: slow-moving SKU review, hold primary |
| Offtake up, primary flat or down | Selling faster than replenishing; OOS coming | NKAM: push the next primary order |
| Both up | Healthy volume-led growth | Confirm it is not a one-time loading spike |
| Both down | A real demand or distribution problem | Go to the offtake decline table above |

Primary is NSV into the chain and offtake is the consumer-side sale, so the two are not
comparable in absolute rupees. Compare direction and trend, and say so.

## Quality bar before answering

- Was the base month checked before crediting or blaming a base effect?
- Were primary and offtake read together, not in isolation?
- Is the action specific and owned, not "monitor closely"?
- Are only exceptions shown, not the full table?
- Are the numbers tied to a validated source — has `sales-data-reconciliation` run?
