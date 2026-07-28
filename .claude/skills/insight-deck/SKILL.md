---
name: insight-deck
description: Compress a sprawling review deck into a few dense insight pages, and build them as a .pptx. Use whenever the user wants a PPT/deck/slides for leadership, a QBR, a monthly or MBR/JC review, an executive summary, a one-pager or "one-slide" summary — and especially when they say the deck is too long, has too many pages, repeats the same insight, or ask to shorten, condense, merge, summarise or "put it on one page". Trigger it before writing any slide content or laying out any slide, including when the input is an existing .pptx to be cut down.
---

# Insight Deck — say more in fewer pages

A 24-page deck where 6 pages differ only by zone name is not 24 insights. It is
~5 insights, each printed four times. This skill finds the repetition, collapses
it, and builds a dense but readable deck.

**The rule: one page = one insight = one decision.** If a page does not change
what someone does, it belongs in the appendix or nowhere.

Target for a monthly/QBR leadership review: **4-6 main pages + an appendix.**

---

## Workflow

### Step 0 — Get the real source

Never invent numbers. Work from an existing `.pptx`, the dashboard data, or an
analysis the user supplies. If a figure needed for a page is missing, name the
exact file or field required and leave the tile out — do not estimate.

For the *why* behind a number, run the **mt-business-logic** skill first. For
leadership wording, run **qbr-insight-writer**. This skill handles the page
architecture and the build.

### Step 1 — Audit (only if an existing deck exists)

```bash
python scripts/audit_deck.py "deck.pptx"            # add --json plan.json
```

Prints every page with its word/picture/chart/table counts, then a compression
plan: which pages are structural clones, which are photo pages, which are thin.
It never edits the source deck. Use the plan as the starting point, then apply
judgement — the script sees structure, you see meaning.

### Step 2 — Collapse, using these five patterns

| # | You have | Collapse to |
|---|---|---|
| **1** | N pages identical except for one filter value (zone, chain, brand, month) | **One page.** `metrics` chip grid — one chip per value — plus a `bars` ranking and 2-3 *exception* bullets. Never a per-value roll-call. |
| **2** | A stack of deep-dive pages on one topic (e.g. 4 market-share pages) | **One page.** Two compact `table` tiles side by side + two `callout` tiles carrying the verdict. |
| **3** | Photo/execution pages, one market per page | **One contact sheet.** An `image` tile, 4 x 2 with captions. The rest go to appendix. |
| **4** | Definition / methodology / "basis differs" pages | **A footnote line** in the `subhead` or footer of the page that uses them. |
| **5** | A page titled with a topic and no conclusion ("Zone Performance Summary") | **Delete it**, or fold its one real fact into a neighbouring page as a tile. |

Two guardrails while collapsing:

- **Exceptions only.** On a collapsed page, name the leader, the laggard and
  anything that broke trend. Six zones each getting a sentence is the disease,
  not the cure.
- **Nothing real is lost.** Every number that drove a decision must survive
  somewhere — main page or appendix. Compression removes *repetition*, never
  evidence. Say in your summary what moved to the appendix.

### Step 3 — Write the page architecture before building

List the pages as headlines only, and check each one against "does this change a
decision?". A monthly MT review usually lands on:

1. **The verdict** — what happened to the channel, why, what is at risk, what to do.
2. **Where the growth came from** — zones and chains on one page (replaces the clones).
3. **External validation** — market share vs the market (replaces the deep-dive stack).
4. **Portfolio** — category / pack / SKU mix, gainers and decliners.
5. **Execution + actions** — contact sheet plus owner-and-date actions.
6. **Appendix** — everything else, clearly labelled as appendix.

### Step 4 — Build

Write a spec JSON (see `reference/spec_schema.md`, full worked example in
`examples/mt_offtake_may26.json`) and render:

```bash
python scripts/build_deck.py spec.json -o "MT Review May26.pptx"
```

Requires `python-pptx` (`pip install python-pptx`). 16:9, offline, no template
needed. If the user needs their own corporate template, use the **pptx** skill's
template workflow instead and carry these layout rules across by hand.

### Step 5 — Check before sending

```bash
python scripts/preview.py "MT Review May26.pptx" -o preview.html --png
```

Then look at the PNGs and confirm:

- [ ] No text overflows its tile, no tile overlaps another.
- [ ] Every headline states a **conclusion with a number**, not a topic.
- [ ] Every page has a "So what" footer with an owner and a date where relevant.
- [ ] No two pages make the same point.
- [ ] Every number traces back to the source. Nothing invented.
- [ ] Page count reported as before → after.

### Step 6 — Report

End with: pages before → after, what was collapsed into what, what moved to the
appendix, and anything you deliberately dropped.

---

## Page anatomy

Each page is built from four bands, all optional except the header:

```
┌──────────────────────────────────────────────────────────┐
│ EYEBROW                                        [ STAMP ] │  header — the
│ HEADLINE: THE CONCLUSION, WITH THE NUMBER                │  conclusion
│ subhead: the qualifier                                   │
├──────────────────────────────────────────────────────────┤
│ [KPI] [KPI] [KPI] [KPI] [KPI]                            │  ≤5 numbers
├──────────────────────────────────────────────────────────┤
│ ┌── tile ──┐ ┌── tile ──┐ ┌───── tile ─────┐             │  rows of tiles,
│ │  bars    │ │  table   │ │    bullets     │             │  2-3 per row
│ └──────────┘ └──────────┘ └────────────────┘             │
├──────────────────────────────────────────────────────────┤
│ SO WHAT │ takeaway · takeaway · takeaway                 │  the decision
└──────────────────────────────────────────────────────────┘
```

Tile kinds: `bars`, `table`, `metrics` (chip grid), `bullets`, `callout`,
`image`, `text`. Tones `good` / `risk` / `warn` / `info` / `neutral` colour the
title bar, markers and rails — use them to make the exception visible at a
glance.

## Density budget (per page)

Dense is the point; cluttered is not. Stay inside these and the page stays
readable at the back of a meeting room:

| Element | Max |
|---|---|
| KPIs in the strip | 5 |
| Tiles on a page | 6 |
| Bullets in a tile | 4, ≤ 16 words each |
| Bar rows / chips | 7 |
| Table rows | 6 (+ header), 5 columns |
| Words on the page | ~350, table cells and labels included |

If content will not fit, the answer is fewer facts, not smaller type — the
builder auto-shrinks text, and anything under ~8 pt means the page is overloaded.

## Writing rules

- **Headline = the conclusion.** "MAY'26 OFFTAKE HITS A RECORD ₹40.19 CR, +63%
  YoY — GROWTH IS BROAD-BASED" beats "Offtake Performance Summary".
- **Lead with the number**, then the reason. One idea per bullet.
- **Drop the scaffolding words.** "Zone Insight:", "Growth View:", "Key
  Performance Highlights" carry no information — the tile title already says it.
- **Every action names an owner and a date.** No owner, no action.
- **`**bold**`** the number inside a bullet so it is findable while someone talks.
- Deltas: write `▲ +12%` / `▼ -35 bps` — the builder colours them automatically
  (green up, red down), so never colour a decline green just to look positive.

## Files

| Path | What it does |
|---|---|
| `scripts/audit_deck.py` | Audits a `.pptx`, prints the compression plan |
| `scripts/build_deck.py` | Spec JSON → dense `.pptx` |
| `scripts/preview.py` | Any `.pptx` → HTML/PNG preview (no PowerPoint needed) |
| `reference/spec_schema.md` | Every spec field, with snippets |
| `examples/mt_offtake_may26.json` | Real 24-page review compressed to 3 pages |

The default palette matches `dashboard/index.html`, so decks and dashboard look
like one system. Pass `"theme": "slate"` or a `"palette"` override for others.
