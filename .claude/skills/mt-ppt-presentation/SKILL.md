# Skill: mt-ppt-presentation
# Domain: PowerPoint Presentation Design & Business Communication

Activate this skill whenever: creating or updating a .pptx file, building a business presentation, designing slide layouts, writing presentation scripts, adding data visualizations to slides, or when the user asks for help with Microsoft PowerPoint, slide design, or business storytelling through slides.

---

## PART 1 — SLIDE DESIGN FOUNDATIONS

### The 6-Second Rule
A slide must communicate its main point within 6 seconds of viewing. If it cannot, the slide fails — regardless of how accurate the data is. Every design decision serves this rule.

### Hierarchy of slide elements (apply in order)
1. **Headline** — the one sentence the audience must remember (verb + outcome). Never use a label ("Sales Data"). Use a claim ("Sales fell ₹1.4 Cr — Reliance is the single cause").
2. **Visual** — chart, table, or diagram that proves the headline.
3. **Context strip** — 1–2 lines that tell the audience what to do with this information.
4. **Metadata** — source, date, scope in a small footer.

### Slide Master discipline
- Create one Slide Master per deck, not per slide.
- Define: font pair (heading/body), 3 accent colours, background, footer format.
- For Honasa/MT decks: dark navy `#0D1B2A` or white background; accent `#E63946` (alert), `#2A9D8F` (growth), `#F4A261` (caution).
- Every content slide inherits the master — never override colour manually on individual slides.

### Layout types and when to use each
| Layout | Use when |
|--------|----------|
| Title slide | First slide only; 60% visual, 40% text |
| Section divider | Between major topics; full-bleed image or colour block |
| Single-headline + chart | One metric, one visual, 2–3 annotation lines |
| Comparison (2-column) | Before/after, plan vs. actual, zone A vs. zone B |
| Data table | 5–8 rows max; highlight top row in accent colour |
| Quote / callout | Single insight in 28–36pt bold; use sparingly |
| Appendix / detail | Dense data that supports but doesn't lead |

### Typography rules
- Body text: minimum 18pt (24pt preferred). Never go below 16pt.
- Slide headline: 28–40pt, bold or semi-bold.
- Data labels on charts: 12–14pt, high contrast.
- One font family per deck; use weight (bold/regular/light) for hierarchy.
- Maximum 2 font sizes on any single slide (headline + body); data labels are the only third.

### Colour discipline
- Maximum 3 colours per chart series. More than 3 requires a legend, which competes with the headline.
- Use red/orange only for problems, never decoratively.
- Use green only for positives or targets met.
- Grey = neutral comparison or context data, not emphasis.
- Accessibility: never rely on red/green alone — add shape or pattern for colour-blind readers.

### White space
- Margins: minimum 0.5" (1.27 cm) on all sides.
- Between chart title and chart: 0.15".
- Between callout boxes: 0.2" minimum.
- If a slide feels crowded, the solution is always to split it — never to shrink text.

---

## PART 2 — DATA VISUALIZATION IN SLIDES

### Chart selection guide
| Goal | Best chart | Avoid |
|------|-----------|-------|
| Compare categories (≤7) | Horizontal bar | 3D bar, pie |
| Show trend over time | Line chart | Area chart (if multiple series) |
| Show part-to-whole | Stacked bar (%) or treemap | Pie with >5 slices |
| Show distribution | Box plot or column with error bars | 3D anything |
| Show correlation | Scatter plot | Line connecting unrelated points |
| Show single KPI | Big number card + trend sparkline | Gauge/speedometer |
| Compare 2 metrics side-by-side | Combo (bar + line, 2 y-axes) | Mixed 3D |

### MT-specific chart templates

**Zone scorecard slide:**
```
Metric card layout: PRIMARY | OFFTAKE | CONVERSION | GAP | CALL
Each metric: large number (28pt bold) + small label (12pt) + colour indicator
Colour: green if above benchmark, amber ±5%, red below benchmark
```

**Chain waterfall (MoM change):**
```
Start = prior month total
Positive bars = green, upward
Negative bars = red, downward
Net total = total bar in dark navy
Label every bar: ₹X.XX Cr / +X% or −X%
```

**Trend sparkline table:**
```
Table header row: Chain | Apr | May | Jun | Jul | MoM%
Sparkline column: tiny 4-bar mini-chart per row (in-cell) showing trend direction
Highlight: top performer row in light green fill; worst performer in light red fill
```

### Annotation and callout discipline
- Every significant data point gets ONE callout line — not a paragraph.
- Callout format: **[WHAT happened] — [WHY it matters] — [WHAT to do]** (all on one slide, not three).
- Use leader lines (thin, no arrow) to connect annotation to data point.
- Callouts sit inside the chart boundary or in a dedicated right-side annotation column.

### Table design rules
- Header row: white text on dark navy fill, 14pt bold.
- Data rows: alternate white / light grey (#F5F5F5); 12–14pt regular.
- Highlight row: accent colour fill for best/worst or most important row.
- Numbers: right-align; text: left-align; headers: centre.
- Never use gridlines that are the same weight as the data — header border 1.5pt, internal 0.5pt.
- Maximum 8 columns. If more are needed, split the table across slides.

---

## PART 3 — SLIDE SCRIPTING AND BUSINESS STORYTELLING

### The SCQA structure (Situation → Complication → Question → Answer)
Use for any executive briefing slide sequence:
1. **Situation** (slide 1–2): What is the current state? (neutral, factual)
2. **Complication** (slide 3–4): What changed or is threatening that state?
3. **Question** (implicit): What should we do?
4. **Answer** (slide 5+): Here is the specific action with evidence.

For MT decks, apply at deck level AND at individual slide level using EVIDENCE → IMPLICATION → ACTION → OWNER.

### EIAO frame (slide-level script)
```
EVIDENCE: [1 sentence, measurable fact] "Reliance offtake fell ₹1.42 Cr MoM."
IMPLICATION: [1 sentence, so what] "One account caused the entire MT decline."
ACTION: [1 sentence, specific] "Run hero-EAN OSA audit by Aug 25."
OWNER: [role + date] "NKAM Reliance · 25-Aug"
```

### Writing headline rules
- Start with the insight, not the topic.
- Bad: "July Zone Performance" → Good: "East converts at 50% — the only zone below benchmark"
- Use specific numbers: "₹6.22 Cr recoverable" beats "significant opportunity"
- Use active verbs: "converted", "fell", "grew", "missed" — not "was", "had", "showed"
- Maximum 12 words. If you cannot fit it, split the slide.

### Script writing for presenter notes
- Write notes in first person: "We are seeing Reliance drive this..."
- Include the 3 things NOT on the slide (context, what happened before, what's next).
- Format: [OPENING LINE to say] | [KEY NUMBER to emphasise] | [QUESTION to anticipate]
- Total notes per slide: 80–120 words. Longer notes are rarely read.

### Presentation flow for MT leadership review (monthly deck structure)
```
Slide 1: Title (Month + Theme headline)
Slide 2: Exec summary — 3 bullets, each with ₹ value
Slide 3: The month's one story (single chart, large, one callout)
Slide 4: Decision/action framework (what we're doing about it)
Slides 5–N: Zone deep dives, chain analysis, NPI, brand performance
Slide N+1: Next month's action register with owners and KPIs
Appendix: Data tables, methodology, audit results
```

---

## PART 4 — SMARTART, ANIMATIONS AND MULTIMEDIA

### SmartArt selection guide
| Concept | SmartArt type |
|---------|--------------|
| Sequential process | Chevron process or Basic process |
| Hierarchy (org chart) | Hierarchy or Half circle organisation chart |
| Cycle / recurring | Cycle or Gear |
| Comparison | Comparison list |
| Funnel / conversion | Funnel |
| Venn / overlap | Venn or Segmented cycle |

**Rule**: Convert SmartArt to shapes before final distribution — it renders inconsistently across PowerPoint versions and on screens that lack embedded fonts.

### Animation discipline (business presentations)
- Use animations sparingly — at most 1 animation type per deck.
- Acceptable: **Appear** (on click, for sequential reveals), **Fade** (for emphasising a callout).
- Never use: Spin, Bounce, Zoom with motion path, or any animation that takes more than 0.4 seconds.
- Charts: use **Wipe** (direction: bottom-to-top for bars, left-to-right for lines) with 0.3s duration.
- Build a table row-by-row only when the sequence IS the story (e.g., ranking a list for the first time).

### Morph transition (PowerPoint 365+ / Office 2019+)
- Use Morph to animate a metric card growing larger on click (zoom into one KPI).
- Technique: Slide 1 has all 6 metric cards at normal size → Slide 2 (Morph) has one card enlarged. Name objects `!!object_name` on both slides for Morph to recognise the pair.
- Never use Morph between slides that have completely different layouts — only when ≥60% of shapes are shared.

### PowerPoint Zoom (Summary / Section Zoom)
- Insert → Zoom → Section Zoom: creates a clickable thumbnail that jumps to a section.
- Use in navigation slides for non-linear presentations.
- Avoid in decks that will be exported to PDF — Zoom links break in PDF.

### Video and audio embedding
- Always embed video (Link to file = broken link on other machines). In Insert → Video → choose "Embed".
- Compress media before embedding: File → Info → Compress Media → HD (720p) for decks sent by email.
- Audio: use sparingly; set to "Play across slides" only for background music in kiosk/auto-run mode.
- Supported formats: MP4 (H.264), WMV, AVI. Avoid MOV on Windows.

---

## PART 5 — MICROSOFT COPILOT INTEGRATION IN POWERPOINT

### What Copilot can do in PowerPoint (M365 Copilot)
- `Create a presentation about [topic]` → generates 5–10 slides from a prompt.
- `Add a slide about [topic]` → inserts a new slide in the current deck.
- `Summarise this presentation` → produces bullet-point summary in the chat pane.
- `Make this slide more concise` → rewrites slide text to shorter form.
- `Change the design of this slide` → applies a different Designer layout.

### Copilot limitations to know
- Copilot does not read your data files automatically — you must reference specific numbers.
- Generated slides will have generic charts (not your actual data) — always replace with live data.
- Copilot-designed layouts may not match your Slide Master — always check and apply your master after Copilot runs.
- Prompt specificity matters: "Create a slide showing zone-wise MT offtake for July with Reliance declining" produces better output than "Create a sales slide".

### Effective Copilot prompts for MT decks
```
"Create a slide with headline 'Reliance drove the entire MT decline' showing a waterfall chart comparing June and July chain offtake. Add EVIDENCE/IMPLICATION/ACTION callout boxes."

"Rewrite this slide's text to be under 30 words total, keeping the key number ₹1.42 Cr prominent."

"Create a presenter note for this slide that explains why Reliance conversion fell and what action is planned, in 100 words."
```

---

## PART 6 — ADVANCED POWERPOINT FEATURES

### Slide Master setup (step-by-step for MT decks)
1. View → Slide Master
2. Edit the top (parent) master: set background colour, font pair, footer text format.
3. Create child layouts for: Title, Section Divider, Content (chart+text), Comparison, Data Table.
4. Insert logo and footer line in the parent master (appears on all slides automatically).
5. Close Master view → all new slides inherit the master.
6. **Never** skip the master and format slides individually — it breaks consistency when the theme changes.

### Accessibility features
- All images: Add Alt Text (right-click → Edit Alt Text → write a description, not "image").
- Reading order: View → Selection Pane → verify order top-to-bottom matches logical reading order.
- Colour contrast: minimum 4.5:1 ratio for body text. Use Microsoft Accessibility Checker (Review → Check Accessibility).
- Font minimum 18pt for reading on screen; 24pt for projected slides in large rooms.

### PowerPoint Live (Teams integration)
- Share the .pptx file instead of your screen in Teams → audience can follow along on their own device.
- Audience can see slide notes if presenter enables it.
- Live captions display automatically when enabled.
- Use for large-room review sessions; do not use for a 1:1 where screen share is cleaner.

### Presenter View
- Slide shown to audience on external screen; you see: current slide + next slide + notes + timer.
- Enable: Slide Show → Use Presenter View.
- For MT leadership reviews: pre-write 3-line talking points per slide in notes; display on your laptop while the slide is projected.
- Shortcut during presentation: `W` = white screen (pause audience), `B` = black screen, `G` = grid, `Ctrl+H` = hide cursor.

### Recording and export
- Record narration: Slide Show → Record → Record from beginning. Saves as .pptx with embedded audio.
- Export to video: File → Export → Create a Video → HD (1080p) for sharing.
- Export to PDF: File → Export → PDF. Deselect "Include Document Properties" for clean output.
- **Note**: animations and transitions are lost in PDF; Zoom links break. For static distribution, always export to PDF. For interactive, share the .pptx.

---

## PART 7 — COLLABORATION AND REVIEW

### Co-authoring in SharePoint/OneDrive
- Both authors must have the file in OneDrive/SharePoint (not local desktop).
- Changes are auto-saved; conflicts are resolved by "last write wins".
- Add comments: Insert → Comment. Tag reviewers with @name to notify them.
- Review → Compare → Merge Presentations: use when you receive a revised copy by email and need to see what changed.

### Comment and review etiquette for MT decks
- Comment format: [TOPIC: question or change request] — e.g., "[DATA: Confirm July offtake includes Trent?]"
- Resolve comments before sending to leadership — do not leave open questions in a leadership deck.
- Use Track Changes equivalent: duplicate the slide with a "[DRAFT]" prefix, make changes on the new copy, let the owner approve before deleting the original.

---

## PART 8 — PYTHON-PPTX AUTOMATION (for programmatic deck creation)

### Creating slides from data
```python
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor

prs = Presentation('template.pptx')
slide_layout = prs.slide_layouts[1]  # 0=title, 1=content, etc.
slide = prs.slides.add_slide(slide_layout)

# Set headline
title = slide.shapes.title
title.text = "Reliance drove the entire MT decline"
title.text_frame.paragraphs[0].runs[0].font.bold = True
title.text_frame.paragraphs[0].runs[0].font.size = Pt(32)

# Add a text box
from pptx.util import Inches
txBox = slide.shapes.add_textbox(Inches(1), Inches(2), Inches(8), Inches(1))
tf = txBox.text_frame
tf.text = "EVIDENCE: Reliance fell ₹1.42 Cr MoM — every other chain combined grew ₹0.13 Cr."
```

### Modifying existing shapes by name
```python
def get_shape_by_name(slide, name):
    return next((s for s in slide.shapes if s.name == name), None)

shape = get_shape_by_name(slide, 'Text 55')
if shape and shape.has_text_frame:
    shape.text_frame.paragraphs[0].runs[0].text = "Updated text here"
```

### Adding a chart from data
```python
from pptx.chart.data import ChartData
from pptx.enum.chart import XL_CHART_TYPE

chart_data = ChartData()
chart_data.categories = ['North', 'East', 'South-1', 'South-2', 'West', 'Central']
chart_data.add_series('Jul-26 NSV (₹ Cr)', (6.97, 3.54, 8.18, 4.87, 8.27, 2.12))

chart = slide.shapes.add_chart(
    XL_CHART_TYPE.BAR_CLUSTERED,
    Inches(1), Inches(2), Inches(8), Inches(4),
    chart_data
).chart
chart.has_legend = False
chart.series[0].format.fill.fore_color.rgb = RGBColor(0x2A, 0x9D, 0x8F)
```

### Saving
```python
prs.save('MT_July26_offtake_analysis_V22.pptx')
```

---

## PART 9 — MT DECK QA CHECKLIST (run before every distribution)

### MANDATORY PRE-DELIVERY FILE VALIDATION (Step 0 — never skip)

Before sending ANY generated or modified .pptx file, run this validation. A file that fails is NOT deliverable.

```python
import zipfile
from pptx import Presentation
from lxml import etree

def validate_pptx(path):
    """Returns (True, 'OK') or (False, error_message). Run before every delivery."""
    # Step 1: Valid ZIP with parseable XML
    try:
        with zipfile.ZipFile(path) as z:
            for name in z.namelist():
                data = z.read(name)
                if name.endswith('.xml') or name.endswith('.rels'):
                    try:
                        etree.fromstring(data)
                    except etree.XMLSyntaxError as e:
                        return False, f"Invalid XML in {name}: {e}"
    except Exception as e:
        return False, f"ZIP error: {e}"
    # Step 2: python-pptx loads and all text frames readable
    try:
        prs = Presentation(path)
        for slide in prs.slides:
            for shape in slide.shapes:
                if shape.has_text_frame:
                    _ = shape.text_frame.text
    except Exception as e:
        return False, f"python-pptx load error: {e}"
    return True, "OK"

ok, msg = validate_pptx("path/to/file.pptx")
assert ok, f"VALIDATION FAILED: {msg}"
```

**Root cause of PPTX corruption** — always use safe text replacement:
```python
# SAFE: modify existing run's text element directly
ns = '{http://schemas.openxmlformats.org/drawingml/2006/main}'
runs = shape.text_frame.paragraphs[0]._p.findall(f'{ns}r')
if runs:
    runs[0].find(f'{ns}t').text = new_text
else:
    # SAFE: use python-pptx API, never raw etree.SubElement for runs
    run = shape.text_frame.paragraphs[0].add_run()
    run.text = new_text

# NEVER DO THIS — creates malformed XML PowerPoint cannot read:
# r = etree.SubElement(p, qn('a:r'))   ← corrupts the file
```

### MANDATORY LAYOUT OVERFLOW CHECK (Step 0b — run after every text change)

After modifying text in any shape, check that the shape's height accommodates the new (potentially longer) text. Overflow causes wrapped text to bleed visually into adjacent shapes.

```python
def fix_text17_overflow(prs):
    """
    Expand source-footnote shape (Text 17) on every slide to use the full
    remaining slide height, preventing wrapped text from overflowing.
    Call this after any text changes to footnote shapes.
    """
    NS_A = '{http://schemas.openxmlformats.org/drawingml/2006/main}'
    slide_h = int(prs.slide_height)
    for slide in prs.slides:
        for sh in slide.shapes:
            if sh.name == 'Text 17':
                xfrm = sh._element.find(f'.//{NS_A}xfrm')
                ext  = xfrm.find(f'{NS_A}ext')
                off  = xfrm.find(f'{NS_A}off')
                top  = int(off.get('y'))
                new_h = slide_h - top - 12700   # 12700 EMU ≈ 0.014" margin
                if new_h > int(ext.get('cy')):
                    ext.set('cy', str(new_h))

# Run immediately after prs.save() but before validate_pptx():
# fix_text17_overflow(prs)
# prs.save(DST)
# assert validate_pptx(DST)[0]
```

**Z-order rule:** Source footnote shapes must be inserted into the spTree BEFORE content shapes so they render behind (not on top of) EVIDENCE/ACTION tables. Use `sp_tree.insert(early_index, shape_element)`.

### MANDATORY SHAPE OVERFLOW AUDIT (generalised — run on any modified slide)

```python
def audit_overflows(prs):
    """Print shapes whose bottom edge exceeds slide height."""
    slide_h = prs.slide_height.inches
    for si, slide in enumerate(prs.slides):
        for sh in slide.shapes:
            if not sh.has_text_frame:
                continue
            bot = (sh.top + sh.height) / 914400
            if bot > slide_h + 0.02:
                print(f"OVERFLOW slide {si+1} {sh.name!r}: bottom={bot:.3f}\" > {slide_h:.3f}\"")
# Call audit_overflows(prs) before prs.save() — fix any reported shape before delivering.
```

### Content checklist

1. [ ] **[Step 0 above]** File validates: `validate_pptx()` returns True before sending.
1b.[ ] **[Step 0b above]** No text overflow: `audit_overflows(prs)` reports nothing before saving.
2. [ ] Headline on every slide is a claim, not a topic label.
3. [ ] Every data point has a source in the footer.
4. [ ] All financial values in ₹ Cr (or stated otherwise) consistently.
5. [ ] Zone names normalised: Central, North, South-1, South-2, East, West (not abbreviations).
6. [ ] FY labelling follows THE ONE FY RULE: Apr–Dec Y → FY(Y+1), Jan–Mar Y → FY(Y).
7. [ ] No slide exceeds 80 words of body text.
8. [ ] Chart colour palette: growth = teal (#2A9D8F), decline = red (#E63946), neutral = grey.
9. [ ] Presenter notes written for slides 1, key insight slides, and action slide.
10. [ ] All animations set to ≤0.4s; no decorative animations.
11. [ ] File compressed: File → Info → Compress Media (if video embedded).
12. [ ] Accessibility Checker run and all errors resolved.
13. [ ] Final version saved as `MT_[Month][YY]_[Purpose]_V[N].pptx`.

---

## PART 10 — CHALLENGE → RESOLUTION LOOKUP

| Challenge | Resolution |
|-----------|-----------|
| Slide looks crowded | Split into 2 slides; if not possible, remove the least important callout |
| Chart colours look wrong on projector | Use solid fills only (no gradients); avoid light yellow/cyan — they wash out |
| Audience reads slide instead of listening | Use builds (click-to-reveal) so only the current point is visible |
| Table has too many rows | Show top 5 in main slide; full table in appendix |
| Presenter forgot the data | Never put data only in the notes — put it on the slide; notes are for narrative, not facts |
| File too large to email | Compress images (right-click → Compress Pictures → Email quality); compress media |
| Font missing on recipient's machine | Embed fonts: File → Options → Save → Embed fonts in file |
| Transitions look bad on PDF | Remove all transitions before exporting to PDF |
| Central Zone missing from slide | Check zone normalisation; Central = MP + CG + Vidarbha; add explicitly if not showing |
| NPI data not attributed to zone | Apply Vidarbha remapping: 101 Vidarbha stores → Central (not West) |
