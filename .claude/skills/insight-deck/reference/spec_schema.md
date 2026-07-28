# Spec schema — `build_deck.py`

A spec is one JSON object. Every field below is optional unless marked
**required**. Sizes are in inches; the page defaults to 13.333 × 7.5 (16:9) and
is set for the whole file by `page`.

```json
{
  "page": "landscape",
  "theme": "honasa",
  "palette": {"accent": "2D9B7F"},
  "slides": [ { ...page... } ]
}
```

| Field | Meaning |
|---|---|
| `page` | Page size for the **whole file** — PowerPoint allows only one. `landscape` 13.33 × 7.5 (default), `portrait` 7.5 × 13.33, `a4` 11.69 × 8.27, `a4p` 8.27 × 11.69, `letterp` 8.5 × 11 |
| `min_pt` | Smallest point size auto-fit may use, for the whole file. Default 7.0; use **9.5** for pages that will be read on a phone |
| `theme` | `honasa` (default, matches the dashboard) or `slate` |
| `palette` | Overrides individual theme keys: `accent`, `accent_d`, `bg`, `card`, `ink`, `muted`, `line`, `good`, `risk`, `warn`, `info`, `font`, `font_head` |
| `slides` | **required** — list of pages, rendered in order |

## Page

```json
{
  "eyebrow": "MT Offtake Review  |  May'26",
  "headline": "MAY'26 OFFTAKE HITS A RECORD ₹40.19 CR, +63% YoY",
  "subhead": "Highest-ever monthly NSV; top-3 chains now 81.1% of offtake",
  "stamp": "HIGHEST EVER",
  "kpis": [ ... ],
  "kpi_cols": 3,
  "rows": [ ... ],
  "footer_title": "So what",
  "footer": [ ... ],
  "footer_cols": 2,
  "page_numbers": true
}
```

`headline` carries the conclusion; the band auto-grows to fit it — up to 2 lines
at 21→14 pt landscape, up to 4 lines at 17→13 pt portrait. `stamp` is the badge on the
right — use it for a one-word status (`HIGHEST EVER`, `WATCH`, `ON TRACK`).

## KPI strip — `kpis` (≤ 5 landscape, ≤ 6 portrait)

```json
{"label": "May'26 NSV", "value": "₹40.19 Cr", "delta": "▲ 12% MoM", "tone": "good"}
```

`delta` colours itself from a leading `▲`/`▼`/`+`/`-`; override with
`"dir": "up" | "down" | "flat"`. `tone` colours the card's left rail. Cards wrap
onto extra rows automatically — 5 per row landscape, 3 portrait; set `kpi_cols`
on the page to force a different split.

## Rows — `rows`

```json
{"weight": 1.25, "tiles": [ ... ]}                  // shares leftover height
{"h": 1.15,      "tiles": [ ... ]}                  // pinned height in inches
{"band": "Where the growth came from", "h": 1.3, "tiles": [ ... ]}
```

Rows stack top to bottom between the KPI strip and the footer. Rows with `h` take
exactly that height; the rest split what is left in proportion to `weight`
(default 1). Within a row, tiles split the width by `span` (default 1). Use `h`
for a single chip strip so it does not stretch, and on portrait pages where
every row should be pinned.

`band` draws a full-width section label above the row — the grouping device that
makes a dense portrait page readable. It costs 0.30 in out of the row's height.

If pinned heights add up to more than the page, they are all scaled down
together and a note is printed on stderr. That note means the page is
overloaded: cut a block rather than shipping squeezed type.

## Tiles

Common to all: `kind`, `title`, `span`, `tone`
(`good` | `risk` | `warn` | `info` | `neutral`).

### `bars` — ranked comparison (≤ 7 rows)

```json
{"kind": "bars", "title": "Chain mix — May'26 NSV (₹ Lacs)",
 "items": [{"label": "D-mart", "value": 1518, "display": "1,518",
            "note": "37.9%", "tone": "good"}]}
```

`value` scales the bar, `display` is the printed number, `note` is the trailing
badge (coloured like a delta). Widen the label column with `"label_w": 1.1`.

### `metrics` — chip grid, the small-multiple killer

```json
{"kind": "metrics", "cols": 6,
 "items": [{"label": "West", "value": "1,016", "delta": "▲ 56% YoY",
            "tone": "good", "note": "25.3% share"}]}
```

One chip per zone/chain/month replaces one page per zone/chain/month. `delta`
wins over `note` when both are given.

### `table` — compact figures (≤ 6 rows + header, ≤ 5 columns)

```json
{"kind": "table", "head": ["Zone", "NSV", "Share", "YoY"],
 "weights": [1.6, 1, 1, 1],
 "items": [["West", "1,016", "25.3%", "▲ 56%"]]}
```

Cells starting `▲`/`▼`/`+`/`-` colour themselves. First column is bold and
left-aligned; the rest right-align. `weights` sets relative column widths.

### `bullets` — the reasoning (≤ 4)

```json
{"kind": "bullets", "title": "Why it moved",
 "items": [{"lead": "Concentration",
            "text": "Top-3 chains delivered **81.1%** of offtake.",
            "tone": "warn"},
           "a plain string also works"]}
```

`lead` prints as a coloured lead-in. `**...**` bolds inline.

### `callout` — one number, one verdict

```json
{"kind": "callout", "title": "Watch-out", "tone": "risk",
 "value": "81.1%", "text": "of offtake sits with three chains."}
```

`value` is optional — omit it for a pure verdict block.

### `image` — contact sheet

```json
{"kind": "image", "title": "Execution proof", "cols": 4,
 "items": [{"path": "photos/apollo_hyd.jpg", "caption": "Apollo · Hyderabad"},
           "photos/dmart_pune.jpg"]}
```

Paths are relative to where you run the script. Images keep their aspect ratio
and are centred in their cell. A missing file draws a grey placeholder and warns — it never crashes the
build.

### `text` — free paragraph (use sparingly)

```json
{"kind": "text", "title": "Method", "items": ["Line one", "Line two"], "size": 9}
```

## Footer — `footer` (≤ 4)

```json
[{"lead": "Risk", "text": "Chain concentration needs a fourth growth chain."},
 "a plain string also works"]
```

Renders as the dark "So what" strip. Rename the chip with `footer_title`, resize
the band with `footer_h`, and set the column count with `footer_cols` (default 3
landscape, 2 portrait — extra items wrap onto more rows and the bar grows).

## Auto-fit behaviour

Text shrinks to fit its box (floor ≈ 7 pt, or `min_pt` when higher); headlines
shrink to 14 pt landscape / 13 pt portrait. Hitting
the floor means the page is overloaded — cut content rather than overriding with
`size` / `text_size`. Those overrides exist for fine-tuning, not for rescuing an
overfull page.
