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

**Reuse the leadership team's own wording.** When the source deck already states
the insight — "114 Cr offtakes: 27% Sequential & 64% YoY Growth", "TDC @ 30 Cr,
doubling sequentially in D-mart" — carry that sentence across as the headline
rather than writing your own. It is how leadership already understands the
quarter, and it makes the compressed deck recognisable rather than foreign.
Rewrite only to merge two of their lines into one headline, or to fix a claim the
source data does not support (and say so when you do).

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

Add `"page": "portrait"` (or `"a4p"`) at the top of the spec for a single tall
one-pager instead of a landscape deck — see *Landscape pages or one portrait
page?* below.

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
- [ ] No two pages make the same point. Re-run `audit_deck.py` on your own
      output — a clean deck should report no clones to collapse.
- [ ] Headlines are the source's own sentences wherever the source had one.
- [ ] Every number traces back to the source. Nothing invented.
- [ ] Page count reported as before → after.

### Step 6 — Report

End with: pages before → after, what was collapsed into what, what moved to the
appendix, and anything you deliberately dropped.

---

## Landscape pages or one portrait page?

`"page"` is a **deck-level** setting — PowerPoint stores one page size per file,
so a portrait one-pager lives in its own `.pptx`, separate from the landscape
review deck.

| | `"page": "landscape"` (13.33 × 7.5, default) | `"page": "portrait"` (7.5 × 13.33) or `"a4p"` |
|---|---|---|
| Use for | The review itself — projected, walked through page by page | One page that carries the *whole* story: pre-read, WhatsApp/mail attachment, printout, notice board |
| Holds | 4-6 pages × ~6 tiles | ~8 blocks + 6 KPIs on a single page |
| Reading | Someone presents it | Someone reads it alone, top to bottom |

Use `a4p` (8.27 × 11.69) instead of `portrait` when it will be printed — same
layout, A4 proportions.

### Reading it on a phone

`portrait` is 9:16 — exactly a phone screen, so each page fills it with no
pinching. But a phone cannot read 7 pt. Set a floor and let the page count grow:

```json
{"page": "portrait", "min_pt": 9.5, "slides": [ ... ]}
```

`min_pt` stops every auto-fit from shrinking past it. Content that no longer fits
has to be cut or moved to another page — which is the point. In practice:

- **One theme per page, 5-7 pages.** Cramming the quarter onto one tall page and
  cramming it onto one slide are the same mistake; on a phone the reader swipes,
  so pages are cheap and small type is not.
- **One tile per row** for tables and bars. Two side-by-side tiles are fine on a
  desktop portrait page and too narrow on a phone.
- **`kpi_cols: 2`** — two big KPI cards per row read cleanly at arm's length.
- Sanity check by viewing the PNG at phone width; if you would zoom, cut.

### Portrait recipe

The tall page works exactly like the reference infographics: labelled section
bands, each holding two blocks side by side. A structure that reliably fits:

1. Header — conclusion + stamp
2. KPI strip — 6 numbers, auto-wrapped 3 × 2
3. `band` **Where the growth came from** — one chip grid (zones or chains)
4. Two tiles side by side — `bars` + `table`
5. `band` **External validation** — two `table` tiles
6. `band` **Portfolio / packs** — `bars` + `bullets`
7. Two `callout` tiles — the risk and the opportunity
8. `band` **Actions** — one `bullets` tile, owner and date on each
9. Footer — "So what", auto-wrapped 2 × 2

Portrait specifics:

- Pin each row's height with `"h"` (inches). The engine scales pinned rows down
  together if they overrun the page and warns on stderr — treat that warning as
  "cut content", not as a clean pass.
- Budget ~7.8 in of row height on a `portrait` page after header, KPI strip and
  footer. Rough starting split: `1.3 / 1.6 / 1.5 / 1.6 / 1.0 / 0.9`.
- Two tiles per row is the limit at this width. Three is unreadable.
- Type gets to ~7 pt in the densest tiles. That is fine on a printed or zoomed
  page and wrong for a projector — which is exactly why this is a *read* format,
  not a *present* format.

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
| Words on the page | ~350 landscape, ~500 portrait (table cells and labels included) |

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
| `examples/mt_offtake_may26.json` | Real 24-page review compressed to 3 landscape pages |
| `examples/mt_may26_onepager_portrait.json` | The same review as **one portrait page** |
| `examples/mt_q1fy27_mobile_portrait.json` | Q1 FY27 review, **6 phone-readable portrait pages** (`min_pt`) |

The default palette matches `dashboard/index.html`, so decks and dashboard look
like one system. Pass `"theme": "slate"` or a `"palette"` override for others.
