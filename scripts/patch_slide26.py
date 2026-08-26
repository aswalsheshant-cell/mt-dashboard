"""
Patch chart35.xml (Primary series) and slide26.xml (text boxes) for slide 26
of MT_Jul26_Enriched_Command_Centre.pptx with derived-primary values.

QC-verified values (Jul'26):
  Primary (₹ Cr): DMart=15.16, Reliance=17.23, Apollo=9.65, FSN/Nykaa=0.21,
                  Lulu=0.75, Wellness=0.48, H&G=0.43, Metro=1.84
  Offtake (₹ Cr): DMart=13.97, Reliance=8.06, Apollo=7.18, FSN/Nykaa=2.07,
                  Lulu=1.70, Wellness=0.72, H&G=0.51, Metro=0.49 (unchanged)
  Conversion: DMart=92.2%, Reliance=46.8%, Apollo=74.4%, Metro=26.4%
              Lulu=226%, H&G=118%, Wellness=150%
  Gross positive gap: +14.18 Cr (DMart+Reliance+Apollo+Metro)
  Gross negative gap: -1.27 Cr (Lulu+H&G+Wellness; FSN/Nykaa excluded as EB2B)
"""

import re
import pathlib

BASE = pathlib.Path("unpacked_enriched/ppt")

# ── 1. chart35.xml — update Primary series only ───────────────────────────────
chart_path = BASE / "charts/chart35.xml"
chart = chart_path.read_text(encoding="utf-8")

PRIMARY_SUBS = [
    ("<c:v>18.2536</c:v>", "<c:v>15.16</c:v>"),    # DMart
    ("<c:v>15.6615</c:v>", "<c:v>17.23</c:v>"),    # Reliance
    ("<c:v>7.2003</c:v>",  "<c:v>9.65</c:v>"),     # Apollo
    ("<c:v>2.079</c:v>",   "<c:v>0.21</c:v>"),     # FSN/Nykaa (MT only)
    ("<c:v>0.0</c:v>",     "<c:v>0.75</c:v>"),     # Lulu
    ("<c:v>0.4855</c:v>",  "<c:v>0.48</c:v>"),     # Wellness
    ("<c:v>0.2203</c:v>",  "<c:v>0.43</c:v>"),     # H&G
    ("<c:v>1.8449</c:v>",  "<c:v>1.84</c:v>"),     # Metro
]

for old, new in PRIMARY_SUBS:
    assert old in chart, f"NOT FOUND in chart35.xml: {old}"
    chart = chart.replace(old, new, 1)

chart_path.write_text(chart, encoding="utf-8")
print("chart35.xml updated.")

# ── 2. slide26.xml — text-box substitutions ───────────────────────────────────
slide_path = BASE / "slides/slide26.xml"
slide = slide_path.read_text(encoding="utf-8")

SLIDE_SUBS = [
    # Slide title
    (
        "Chain conversion: Apollo &amp; FSN at ≥99% — Reliance (51%) and Metro (26%) are the gap",
        "Chain conversion: Reliance at 47% drives ₹9.2 Cr pipeline risk — DMart improved to 92%, Apollo 74%"
    ),
    # Reliance callout header
    ("₹7.60 Cr", "₹9.17 Cr"),
    # Reliance callout narrative
    (
        "51.4% — 48.6% unsold; ₹7.60 Cr pipeline risk",
        "46.8% — 53.2% unsold; ₹9.17 Cr pipeline risk"
    ),
    # DMart callout value
    ("₹4.28 Cr", "₹1.19 Cr"),
    # DMart callout narrative
    (
        "76.5% — needs ≥85% to reach benchmark",
        "92.2% — improved; South-2 residual ₹1.19 Cr remains"
    ),
    # Apollo callout value
    ("99.7%", "74.4%"),
    # Apollo callout narrative
    (
        "near parity, but zone figures need reconciling",
        "₹2.47 Cr pipeline gap; recover zone-level secondary"
    ),
    # Gross gap table — Reliance row
    ("<a:t>15.66</a:t>", "<a:t>17.23</a:t>"),
    ("<a:t>+7.61</a:t>", "<a:t>+9.17</a:t>"),
    ("<a:t>51.4%</a:t>", "<a:t>46.8%</a:t>"),
    # Gross gap table — DMart row
    ("<a:t>18.25</a:t>", "<a:t>15.16</a:t>"),
    ("<a:t>+4.29</a:t>", "<a:t>+1.19</a:t>"),
    ("<a:t>76.5%</a:t>", "<a:t>92.2%</a:t>"),
    ("<a:t>Recover, concentrated in South-2</a:t>", "<a:t>Near parity; South-2 residual</a:t>"),
    # Metro row
    ("<a:t>+1.36</a:t>", "<a:t>+1.35</a:t>"),
    ("<a:t>26.5%</a:t>", "<a:t>26.4%</a:t>"),
    # Lulu row
    ("<a:t>0.00</a:t>", "<a:t>0.75</a:t>"),
    ("<a:t>−1.70</a:t>", "<a:t>−0.95</a:t>"),
    ("<a:t>n/a</a:t>", "<a:t>226%</a:t>"),            # Lulu conversion (1st n/a)
    ("<a:t>Primary not mapped — cannot test</a:t>", "<a:t>Demand &gt; supply; scale primary</a:t>"),
    # H&G row
    ("<a:t>0.22</a:t>", "<a:t>0.43</a:t>"),
    ("<a:t>−0.29</a:t>", "<a:t>−0.08</a:t>"),
    # H&G: second n/a → 118%  (we replace one at a time; the first was Lulu's done above)
    ("<a:t>n/a</a:t>", "<a:t>118%</a:t>"),            # H&G conversion (2nd remaining n/a)
    ("<a:t>Primary route incomplete</a:t>", "<a:t>Demand &gt; supply</a:t>"),  # H&G read (1st)
    # Wellness row
    ("<a:t>0.49</a:t>", "<a:t>0.48</a:t>"),
    # Wellness: third n/a → 150%
    ("<a:t>n/a</a:t>", "<a:t>150%</a:t>"),            # Wellness conversion (3rd remaining n/a)
    ("<a:t>Primary route incomplete</a:t>", "<a:t>Demand &gt; supply</a:t>"),  # Wellness read (2nd)
    # Gross positive gap
    ("<a:t>₹13.27 Cr</a:t>", "<a:t>₹14.18 Cr</a:t>"),
    (
        "<a:t>Billed but not yet sold through, in three chains. This is the recoverable pool — 90.7% of it in DMart and Reliance alone.</a:t>",
        "<a:t>Billed but not yet sold through, across four chains. Recoverable pool — 64.7% in Reliance, 17.4% in Apollo, 12.3% in DMart, 9.5% in Metro.</a:t>"
    ),
    # Gross negative gap
    ("<a:t>₹2.23 Cr</a:t>", "<a:t>₹1.27 Cr</a:t>"),
    (
        "<a:t>Sold with no primary joined, in three chains. Not performance — a mapping defect that was previously netted against the pool above.</a:t>",
        "<a:t>Offtake exceeds primary in Lulu, H&amp;G, and Wellness — demand established; primary supply needs scaling, not a mapping defect.</a:t>"
    ),
    # Account plan
    (
        "<a:t>Reliance: attack North and East first — ₹3.92 Cr recoverable at DMart parity. Convert billed inventory through hero-SKU visibility and replenishment, not new loading.</a:t>",
        "<a:t>Reliance: ₹9.17 Cr pipeline at risk — attack North and East; convert billed inventory through hero-SKU visibility and replenishment. No new loading until secondary improves.</a:t>"
    ),
    (
        "<a:t>DMart: attack South-2 first, then North. Review top-SKU store availability and DC-to-store fill; West and Central prove the account can run above 94%.</a:t>",
        "<a:t>DMart: improved to 92.2%; residual ₹1.19 Cr concentrated in South-2. Review DC-to-store fill and top-SKU store availability in that region.</a:t>"
    ),
    (
        "<a:t>Apollo: protect the cadence and reconcile zone-level opening stock so the 99.7% national figure becomes quotable.</a:t>",
        "<a:t>Apollo: 74.4% conversion with ₹2.47 Cr gap — push NKAM to drive secondary sell-through. Reconcile zone-level stock; national primary is healthy.</a:t>"
    ),
    (
        "<a:t>Lulu, Health &amp; Glow, Wellness Forever: map primary before any commercial conclusion. Three chains and ₹2.23 Cr are currently unreadable.</a:t>",
        "<a:t>Lulu, H&amp;G, Wellness: demand exceeds primary supply — offtake running ahead. Scale primary to match pull-through and avoid OOS. ₹1.27 Cr upside if supply keeps pace.</a:t>"
    ),
]

for old, new in SLIDE_SUBS:
    if old not in slide:
        print(f"WARNING — not found: {repr(old[:80])}")
    else:
        slide = slide.replace(old, new, 1)

slide_path.write_text(slide, encoding="utf-8")
print("slide26.xml updated.")
print("Done.")
