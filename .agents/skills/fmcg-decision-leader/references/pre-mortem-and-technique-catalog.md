# Pre-mortem and technique catalog

## The pre-mortem step (required before GO / GO WITH CONDITIONS)

Before a decision label ships, answer three questions out loud in the response:

1. **What observation would prove this decision wrong?** Not "what could go wrong in
   general" — a specific number, report, or event that would falsify the conclusion.
2. **Who sees that observation first?** If nobody is positioned to notice the falsifier,
   the decision has no early-warning system and should carry a condition that creates
   one (a check, an owner, a re-run date).
3. **What would this skill have said one level too early?** Apply this repo's own two
   corrections as the standard: the D-Mart-Offline chain question looked like a material
   business ambiguity needing an owner alias decision — the pre-mortem question ("what
   would prove this isn't a real second chain?") led straight to checking whether the
   Direct rows' own `Chain name` column already resolved it, which it did. The ₹9,455.51L
   transcription error looked like a fine number to report — the pre-mortem question
   ("what would prove this figure is wrong?") is exactly "regenerate it from source and
   diff" — a five-minute check that was skipped the first time.

A decision with no stated falsifier is not ready to ship. This is not a formality — both
worked examples above were *caught this way*, not by a smarter analysis.

## Look deeper than the headline metric

Before treating a single moved number as the whole story (e.g. "Primary is up 18%, that's
a strong month"), check what corroborating evidence exists and what would contradict it:

- Secondary / sell-out (does the chain's DMS agree, or is this channel loading?)
- Numeric/weighted distribution and OOS
- Inventory cover and returns
- Discount/scheme depth funding the number
- Retail execution (visibility, POSM, planogram compliance)
- Distributor health (is one distributor's pooled billing masking a problem underneath?)
- Brand/SKU mix and concentration (is the gain broad or one SKU in one chain?)

₹50L billed is not ₹50L consumed. A number that only checks out against itself is a
symptom report, not a decision input — route the underlying validation to
`sales-data-reconciliation` and the commercial diagnosis to `modern-trade-sales-growth`
before labelling anything GO.

## Technique catalog (apply selectively, cite which one you used)

These are general-purpose problem-solving tools, not FMCG-specific analysis — the actual
number-crunching still belongs to `modern-trade-sales-growth` (commercial diagnosis) or
`sales-data-reconciliation` (data integrity). This skill uses them to structure a
decision, not to replace the specialist analysis:

| Technique | Use it when |
|---|---|
| Root cause (5 whys) | A symptom is reported and the temptation is to fix the symptom — e.g. "reclassify these 86 rows" instead of asking why `PO Type` holds an `MTD-Sale type` value |
| First principles | An assumption is inherited from a prior report rather than re-derived — e.g. re-checking whether `Dist chain ten` really is `Customer name 2` rather than assuming a prior note |
| SWOT | Weighing whether to act now vs. wait, with named internal/external factors |
| Pareto (80/20) | A long tail of small unallocated lines exists alongside a few large ones — the ₹9,455.20L provisional bucket is 74% concentrated in 5 distributors; review those five first |
| Decision matrix | Comparing 2+ genuinely different options with named weighted criteria, not just picking the familiar one |
| Reverse thinking | Starting from "what would BUSINESS_ACCEPTANCE look like" and working backward to what has to be true at each earlier gate |
| Scenario planning | An owner decision (Approve/Reject/Amend) could go either way and both paths need to be ready |
| Cost-benefit | A fix is technically possible but the question is whether it's worth doing before a gate needs it |
| Systems thinking | A local fix (one distributor's mapping) could ripple into another month's or another chain's totals — always re-run the full reconciliation, never assume isolation |
| Data-driven, not gut-feel | Default posture for this whole skill — a HOLD grounded in a named pending gate beats a GO grounded in confidence |
| Rapid experimentation | Only for genuinely reversible, low-stakes changes — never for a mapping or classification that would need to be walked back publicly if wrong |

Do not run the full catalog on every question. State which one or two techniques
actually did the work; listing all twelve as decoration is the anti-pattern this catalog
exists to avoid.
