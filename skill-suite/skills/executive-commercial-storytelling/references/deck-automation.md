# Deck automation

The repository already builds and corrects the MT leadership deck. Reuse these scripts;
do not write a parallel builder.

## Scripts

| Script | What it does |
|---|---|
| `scripts/rebuild_mt_offtake_ppt.py` | Rebuilds the leadership deck in portrait: keeps every existing slide and its content, fixes overlaps, off-slide elements, margins and fonts, applies the Honasa palette, appends execution photo-grid slides. Requires python-pptx and pillow. |
| `scripts/build_fw_nielsen_slide.py` | Builds a standalone Nielsen brand-share slide and inserts it at a display position. Raw OOXML, standard library only. |
| `scripts/build_shampoo_nielsen_slide.py` | Shampoo Nielsen share slide. |
| `scripts/build_shampoo_deepdive_slide.py` | Shampoo deep dive keyed by brand, sales and share, in the pack-size layout. |
| `scripts/insert_pack_size_slide.py` | Inserts the Pack Size Deep Dive slide scaled to A4 portrait, copies its chart and embedding, teals the title bar, unifies the font, renumbers footers. |
| `scripts/patch_corrections_v2.py` | Targeted fixes on an unzipped tree: header bar colour, table and heading overlap, chart label headroom, panel spacing, image replacement. |
| `scripts/enhance_v3.py` | V3 pass over the corrected deck: font unification to Calibri, margin alignment of full-width blocks. |
| `scripts/build_stdlib.py` | Standard-library-only whole-deck builder: operates on the unzipped `lead/` and `d_*/` trees, appends execution image slides, adds warm background and page-number footers, rezips. No pip packages. |

Two build styles exist. Match whichever the target script already uses: **python-pptx**
for layout, fonts, images and whole-deck passes; **raw OOXML** through
`xml.etree.ElementTree` for precise single-slide construction with no dependencies.

## XML escaping — mandatory

Every dynamic string written into slide XML must be escaped. Chain and article names
routinely contain `&` — `Health & Glow`, `R&D` — and comparison text contains `<` and
`>`. An unescaped `&` produces a `.pptx` that PowerPoint refuses to open, with no
useful error message.

```python
from xml.sax.saxutils import escape, quoteattr

# text nodes
f"<a:t>{escape(chain_name)}</a:t>"

# attribute values
f'<p:cNvPr id="2" name={quoteattr(shape_name)}/>'
```

`build_fw_nielsen_slide.py`, `build_shampoo_deepdive_slide.py` and `build_stdlib.py`
already import `escape`. Follow them. Never interpolate a raw value into XML, not even
one that looks safe — the value that breaks the build is always a real chain name
arriving six months later.

The same rule applies to any XML or XML-like structure generated from metadata,
including skill descriptions rendered into prompt markup. See `agent-skill-governance`.

## Portrait layout constants

Used across the slide scripts: slide 7562850 x 10688638 EMU; title block left 212691,
width 6926523. Palette: teal `2D9B7F`, dark `1F2933`, warm `FAF7F2`, white `FFFFFF`,
green `1E8E3E`, red `C0392B`, light teal `E3F2EC`. Font Aptos, falling back to Calibri;
the standard-library scripts write Calibri directly.

## Checks before shipping a deck

1. Nothing off-slide, nothing overlapping.
2. Consistent margins across slides.
3. One font family; title and body sizes consistent within each block.
4. Growth colour semantic — green up, red down — and never decorative.
5. Every chart carries a source and period footnote.
6. Slide count before and after matches the intended change.
7. The output file opens.
8. Every dynamic string passed through `escape()`.

## Working on the existing deck

The committed deck is `Final MT Offtake May26 Leadership slide_CORRECTED_V2.pptx`.

Never rebuild it from scratch — patch it. `rebuild_mt_offtake_ppt.py` exists precisely
to preserve content while correcting layout. Always write to a new `--out` file and
never overwrite the input in place. Read the deck before modifying it: inserting at
"position 7" is meaningless without knowing what currently sits at 6 and 8.

For `.pptx` file mechanics beyond these scripts — opening, extracting text, splitting,
templates — use the host environment's `pptx` skill. For chart form and colour, use its
`dataviz` skill.
