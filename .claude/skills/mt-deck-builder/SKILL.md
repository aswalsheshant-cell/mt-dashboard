---
name: mt-deck-builder
description: "Structures and builds Modern Trade (MT) leadership presentations — deck storyboard and slide order, action titles, which chart belongs on which slide, portrait leadership layout, the python-pptx and raw-OOXML slide scripts in scripts/, and delivery/speaking notes. Use this skill whenever the user asks to build, fix, restructure or review a deck, PPT, PPTX, slide, storyboard, review presentation, monthly or QBR deck, asks 'what should go on this slide', 'in what order should I present', wants speaker notes, or asks about slide overlap, fonts or the brand palette in a deck. Pair with the pptx skill for file mechanics and qbr-insight-writer for the wording of each insight."
---

# MT Deck Builder

Decides **what goes on each slide and in what order** for MT leadership decks, and
drives the slide-generation scripts already in this repo. It does not invent the
insights — those come from `mt-business-logic` and `mt-growth-opportunity` — and it
does not write the sentences — that is `qbr-insight-writer`.

## Boundaries — the deck pipeline

```
mt-business-logic      →  why the number moved
mt-growth-opportunity  →  what is available and what it is worth
qbr-insight-writer     →  the sentence that goes on the slide
mt-deck-builder        →  which slide, what order, which chart, built how   ← this skill
pptx (global skill)    →  .pptx file mechanics: open, edit, extract, save
dataviz (global skill) →  chart form and colour choices
```

If the user only wants a sentence reworded, do not open this skill.

## Repo assets — reuse, never rewrite

| Script | What it does |
|---|---|
| `scripts/rebuild_mt_offtake_ppt.py` | Rebuilds the leadership deck portrait-mode: keeps every existing slide and its content, fixes overlaps, off-slide elements, margins and fonts, applies the Honasa palette, appends execution photo-grid slides. Uses python-pptx + pillow. |
| `scripts/build_fw_nielsen_slide.py` | Builds a standalone Nielsen brand-share slide and inserts it at a display position. Raw OOXML, stdlib only. |
| `scripts/build_shampoo_nielsen_slide.py`, `scripts/build_shampoo_deepdive_slide.py` | Category deep-dive slides. |
| `scripts/insert_pack_size_slide.py` | Inserts the Pack Size Deep Dive slide, scaled to A4 portrait, chart + embedding copied, footers renumbered. |
| `scripts/patch_corrections_v2.py` | Targeted fixes on an unzipped tree: teal header bar, table/heading overlap, chart label headroom, panel spacing, image replacement. |
| `scripts/enhance_v3.py` | V3 pass over the CORRECTED_V2 deck: font unification to Calibri, margin alignment of full-width blocks. |
| `scripts/build_stdlib.py` | Stdlib-only whole-deck builder: works on the unzipped `lead/` and `d_*/` trees, appends execution image slides, adds warm background and page-number footers, rezips. No pip packages. |

Two build styles exist in this repo. Match whichever the target script already uses:

- **python-pptx** (`rebuild_mt_offtake_ppt.py`) — for layout, fonts, images, whole-deck passes.
- **Raw OOXML via `xml.etree.ElementTree`** (`build_*_slide.py`) — for precise
  single-slide construction with no dependencies.

### The rule for raw-OOXML slides

**Every dynamic string written into slide XML must be escaped.** Chain names, article
names and comments routinely contain `&` (`Health & Glow`, `R&D`), and `<`/`>` appear in
comparison text. An unescaped `&` produces a corrupt `.pptx` that PowerPoint refuses to
open — with no useful error.

```python
from xml.sax.saxutils import escape, quoteattr

# text nodes
f"<a:t>{escape(chain_name)}</a:t>"

# attribute values
f"<p:cNvPr id=\"2\" name={quoteattr(shape_name)}/>"
```

`build_fw_nielsen_slide.py`, `build_shampoo_deepdive_slide.py` and `build_stdlib.py`
all already import `escape` — follow them. Never interpolate a raw value into XML, not
even one that "looks safe".

## Deck architecture — the standard MT leadership order

Ten blocks. Drop a block if it has nothing to say; never reorder them.

| # | Block | Purpose | Slides |
|---|---|---|---|
| 1 | Cover | Period, channel, presenter | 1 |
| 2 | Executive summary | The 3–5 things leadership must leave knowing | 1 |
| 3 | Headline performance | Offtake and primary vs LY and vs target | 1–2 |
| 4 | Chain performance | Top chains, growth, contribution, gaps | 2–3 |
| 5 | Category & brand | Which categories drove or dragged | 1–2 |
| 6 | Market share | Nielsen — share, rank, competitor movement | 1–2 |
| 7 | Distribution & availability | TDP, ND/WD, must-stock compliance, OOS | 1–2 |
| 8 | Deep dive | The one issue this month deserving a full page | 1–2 |
| 9 | Opportunity & action plan | Sized, owned, dated (from `mt-growth-opportunity`) | 1 |
| 10 | Execution / annexure | Photos, backup tables | 2–5 |

The executive summary is written **last** and read **first**. If a leader reads only
slide 2, they should be able to act.

## Slide construction rules

**One message per slide.** If a slide has two messages it is two slides.

**Action titles, not category labels.** The title states the finding; the body proves it.

| Weak | Strong |
|---|---|
| Chain Performance | DMart and Reliance drove 78 % of MT growth; Health & Glow declined 14 % |
| Market Share | Shampoo share up 40 bps to 6.2 %, overtaking competitor in West |
| Distribution | 118-store listing gap on Ubtan FW 150 ml is worth ₹42 L/month |

Test: read only the titles top to bottom. That sequence must be the whole story.

**Chart choice** (load `dataviz` before writing chart code):

| Question | Form |
|---|---|
| Trend over months | Line, FY-month order (Apr first) |
| Compare chains/articles | Horizontal bar, sorted descending |
| Contribution to a total | Stacked bar or a treemap — never a pie beyond 5 slices |
| Gap decomposition | Waterfall |
| Two metrics, many entities | Scatter with quadrant labels |
| Exact numbers leadership will quote | Table, ≤ 8 rows |

**Numbers on slides:** ₹ Cr with one decimal for absolutes, signed percentages with one
decimal for growth, unit stated in the header not in every cell, and the same unit down
a whole column. Data labels on, gridlines off.

**Never put a number on a slide that has not passed QC.** Run `mt-error-resolution`
first if there is any doubt — a wrong number in a leadership deck costs more than a
late deck.

## Portrait leadership layout (this deck's format)

`rebuild_mt_offtake_ppt.py` targets portrait. Working constants used across the slide
scripts: slide `7562850 × 10688638` EMU, title block left `212691`, width `6926523`;
palette teal `2D9B7F`, dark `1F2933`, warm `FAF7F2`, green `1E8E3E`, red `C0392B`;
font Aptos falling back to Calibri.

Layout checks before shipping:
1. Nothing off-slide, nothing overlapping.
2. Consistent margins across slides.
3. One font family; title/body sizes consistent block to block.
4. Growth colour is semantic — green up, red down — and used nowhere decorative.
5. Every chart has a source and period footnote.

## Speaker notes

Attach notes to every content slide, in this shape:

```
SAY:     the one sentence version of the title
PROVE:   the two numbers on this slide that back it
EXPECT:  the question leadership will ask here
ANSWER:  the answer, with the number
```

Delivery: open with the conclusion, not the method. Never read the slide aloud. Keep a
backup slide for the predictable question rather than crowding the main slide.

## Working on an existing deck

The repo's committed deck is
`Final MT Offtake May26 Leadership slide_CORRECTED_V2.pptx`.

1. **Never rebuild a deck from scratch.** Patch it. `rebuild_mt_offtake_ppt.py` exists
   precisely because content must be preserved while layout is fixed.
2. Always write to a new `--out` file; never overwrite the input in place.
3. After any script run, verify: slide count, that no slide lost its content, that the
   file opens, and that new dynamic text was XML-escaped.
4. Read the target deck before modifying it — inserting at "position 7" is meaningless
   without knowing what is currently at 6 and 8.

## Output contract

Every deck answer ends with:

1. The storyboard — slide number, action title, chart/table, source.
2. The command to run, if a script builds it.
3. **Verified:** slide count before/after, layout checks passed, escape rule applied.
4. What still needs a human: photos, approvals, numbers not yet available.
