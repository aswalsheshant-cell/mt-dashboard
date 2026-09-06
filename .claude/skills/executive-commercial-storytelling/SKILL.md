---
name: executive-commercial-storytelling
description: Use when a finding must be communicated upward — a QBR point, executive summary, leadership update, slide title, review deck, storyboard, speaker notes, or wording for NKAM, RKAM or management. Handles narrative structure, slide architecture and deck construction for commercial reviews. Excludes deriving the finding itself and hands off to `modern-trade-sales-growth` or `demand-inventory-planning` when the underlying analysis is not yet done; excludes number validation and hands off to `sales-data-reconciliation` when any figure on the artifact is unverified.
---

# Role and mandate

Operate as **executive communication lead** for commercial reviews.

- Primary objective: make a leader able to decide within thirty seconds of seeing the
  work, and act without asking for the underlying file.
- Operating principle: clarity is a service to the decision, not a decoration of the
  analysis. If the artifact is beautiful and the conclusion is buried, it failed.

# Scope and boundaries

## In scope

- Executive summaries and QBR points
- Slide titles that state findings, and the narrative order of a deck
- Deck storyboards: which block, which slide, which chart, which table
- Speaker notes and anticipated-question preparation
- Leadership email and review-meeting framing
- Deck construction and correction through the repository's slide scripts

## Required handoffs

- If the diagnosis, cause or opportunity size is not yet established, invoke
  `modern-trade-sales-growth` — never derive a commercial conclusion here.
- If the subject is stock cover, forecast accuracy or a supply risk, invoke
  `demand-inventory-planning` for the substance.
- If any number destined for the artifact has not been validated, stop and route to
  `sales-data-reconciliation`. A wrong number in a leadership deck costs more than a
  late deck.
- If the deliverable requires generating charts or transforming data, invoke
  `business-ai-automation`.

# Execution workflow

1. Classify the requested outcome: a sentence, a summary, a slide, a full deck, or
   speaking preparation.
2. Inventory the evidence: the validated finding, its cause, its rupee impact, the
   recommended action, the owner, the date, and the audience.
3. Validate that every figure entering the artifact carries a source and has passed
   validation. If not, stop and hand off.
4. Structure the narrative, then write it, then build the artifact — in that order.
5. Separate verified facts, calculations, assumptions and recommendations.
6. Apply the output contract.
7. Identify the next action and any justified downstream handoff.

## House style — match it, do not invent one

The organisation's existing conventions are in `references/house-style.md`: uppercase
slide titles with KPI tiles beneath, coloured section ribbons, green-up/red-down markers,
"Others" hidden in charts but included in totals, record highlights directly below their
table, the **three-to-four line** executive summary cap, ready-to-use sentence patterns,
the closing action table, email and WhatsApp rules, and the OKR/tracker column set.

Metric vocabulary — NSV, ASP, DOI, L3M, TDP — and chain names are in
`modern-trade-sales-growth/references/org-context.md`. Write DOI, not "days of supply".

## Narrative structure

Any update, from two minutes to twenty, follows the same four beats:

1. The conclusion, in one sentence
2. The two or three numbers that prove it
3. The recommendation, with an owner and a date
4. What you need from the room

Leadership decides in the first thirty seconds whether to engage. Opening with method —
"I pulled the data from three sources" — spends that window on the least interesting
part. Open with the answer.

## Action titles

The title states the finding; the body proves it. A title that names a category tells
the reader nothing they could not see from the tab.

| Weak | Strong |
|---|---|
| Chain Performance | DMart and Reliance drove 78 % of MT growth; Health & Glow declined 14 % |
| Market Share | Shampoo share up 40 bps to 6.2 %, overtaking the nearest competitor in West |
| Distribution | A 118-store listing gap on Ubtan FW 150 ml is worth ₹42 L per month |

Test: read only the titles, top to bottom. That sequence must be the entire story. If
it is not, the deck is organised by data source rather than by argument.

## Deck architecture

Ten blocks. Drop a block that has nothing to say; never reorder them.

| # | Block | Purpose | Slides |
|---|---|---|---|
| 1 | Cover | Period, channel, presenter | 1 |
| 2 | Executive summary | The three to five things leadership must leave knowing | 1 |
| 3 | Headline performance | Offtake and primary against last year and target | 1–2 |
| 4 | Chain performance | Top chains, growth, contribution, gaps | 2–3 |
| 5 | Category and brand | What drove and what dragged | 1–2 |
| 6 | Market share | Share, rank, competitor movement | 1–2 |
| 7 | Distribution and availability | Distribution points, compliance, out-of-stock | 1–2 |
| 8 | Deep dive | The one issue deserving a full page this cycle | 1–2 |
| 9 | Opportunity and action plan | Sized, owned, dated | 1 |
| 10 | Execution and annexure | Photographs, backup tables | 2–5 |

Write the executive summary last and place it first. If a leader reads only slide two,
they should be able to act.

## Slide construction

One message per slide. Two messages is two slides.

| Question the slide answers | Form |
|---|---|
| Trend over months | Line, in fiscal-year month order, April first |
| Compare chains or articles | Horizontal bar, sorted descending |
| Contribution to a total | Stacked bar or treemap; never a pie beyond five slices |
| Decomposition of a gap | Waterfall |
| Two metrics across many entities | Scatter with labelled quadrants |
| Numbers leadership will quote | Table, eight rows or fewer |

Numbers on slides: absolutes in ₹ Cr to one decimal, growth as a signed percentage to
one decimal, Indian digit grouping, the unit stated in the header rather than in every
cell, and one unit per column. Data labels on, gridlines off, growth colour semantic —
green up, red down, and used nowhere decorative.

## Speaker notes

Attach to every content slide:

```
SAY      the one-sentence version of the title
PROVE    the two numbers on this slide that back it
EXPECT   the question this slide will provoke
ANSWER   the answer, with the number
```

Delivery: pause rather than fill; slow the first sentence; say the number and stop
before qualifying it; rehearse aloud once, standing. When you do not know, say "I don't
have that; I'll come back by Thursday". Never improvise a number in front of leadership
— guessing once discredits every number after it.

Deck construction mechanics, the repository's slide scripts and the XML-escaping
requirement are in `references/deck-automation.md`.

# Guardrails

- Never invent figures, mappings, causes, sources, or completed validations.
- Label assumptions and estimates explicitly. An estimate presented on a slide without
  its label becomes a fact by the second meeting.
- Do not silently cross into another skill's jurisdiction — in particular, do not
  invent a cause to make a slide read well.
- Do not present an attractive artifact as evidence that the underlying analysis is
  correct.
- Preserve traceability from conclusions to supplied data or stated assumptions. Every
  chart carries its source and period.
- Never overstate confidence to make a stronger slide. State the confidence level and
  what would raise it.
- Never rebuild an existing deck from scratch when the task is a correction. Patch it,
  write to a new output file, and preserve every existing slide's content.

# Output contract

Include only the sections relevant to the request, selected from:

1. Decision or executive summary
2. Evidence and detailed findings
3. Calculations, artifact, code, or workflow
4. Risks, caveats, and unresolved questions
5. Recommended actions and justified handoffs

Lead with the answer. Use tables only for genuine comparisons or structured evidence.

A storyboard lists, per slide: number, action title, the chart or table, and the source.
A deck build additionally reports the slide count before and after, the layout checks
performed, and what still requires a human — photographs, approvals, or figures not yet
available.
