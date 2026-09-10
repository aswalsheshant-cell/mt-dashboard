# Compression algorithm

## Load at the finest grain available

Compress from the finest grain the source data actually has (e.g. Month × Distributor ×
Brand × Chain), not from an already-aggregated summary. An aggregate can already hide a
month where the same distributor+brand resolved to a different chain — compressing from
there would silently launder that conflict into a clean-looking rule.

## Progressive broadening

Try candidate groupings from broadest to narrowest, accepting the broadest one that
survives the consistency test below:

1. Distributor → Chain (all brands, all months)
2. Distributor × Brand → Chain (all months)
3. Distributor × Month-range → Chain (all brands)
4. Distributor × Brand × Month-range → Chain (narrowest — always available as a fallback)

Do not skip a level to reach a "nicer" broader rule — test each level's consistency
before accepting it, and stop broadening the moment a level fails.

## Consistency test (must pass before accepting a grouping)

A candidate grouping is acceptable only if:

- Every row folded into it proposes the **same** chain (or, for a multi-chain split,
  the same percentage split from the same source) — a single dissenting row fails the
  whole candidate at that level, not just that row.
- The evidence source is the same across every folded row (mixing a workbook-sourced
  row with a Secondary-derived row into one rule hides where the evidence actually came
  from).
- The affected value and month range are both known exactly — never "approximately."
- Every original row stays listed underneath the rule (traceability) — a rule is a
  presentation layer over the rows, not a replacement for them.

If a candidate fails, split it at the exact point of disagreement (the dissenting
month, brand, or chain) and recurse: try to broaden the two resulting sub-groups
independently. Never resolve the failure by dropping the dissenting row silently or by
picking whichever side has more rupees.

## Materiality tiering

Apply after clustering, not before — materiality decides how a cluster or exception is
presented, not whether it's allowed to exist.

| Tier | Suggested threshold (state the actual thresholds used, don't leave them implicit) | Presentation |
|---|---|---|
| HIGH | e.g. ≥ ₹200L or ≥ 5% of the unresolved bucket | Own line in the decision pack, full evidence shown |
| MEDIUM | e.g. ≥ ₹20L | Own line, evidence summarized |
| LOW | below the MEDIUM floor | Grouped into a single "low-value exceptions" line unless policy requires individual review |

State the exact thresholds used in every compression report — a materiality tier with
an unstated cutoff is not reproducible.

## What compression must never do

- Never change a proposed chain to make a cluster consistent — the rows either already
  agree or they don't.
- Never invent a percentage split that isn't already present in the source evidence.
- Never treat "these are probably the same business decision" as sufficient — the
  consistency test is mechanical (same chain, same source, same value), not a judgment
  call made during compression.
- Never let compression itself become the approval — every compressed rule still needs
  an explicit Owner_Decision; compression only changes how many lines the owner has to
  decide on, not whether a decision is needed.
