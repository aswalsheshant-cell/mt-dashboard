"""
Patch slide26.xml EVIDENCE / IMPLICATION / ACTION / OWNER section
with Jul'26 chain-conversion findings (QC-verified numbers only).
"""
import pathlib, re

slide_path = pathlib.Path("unpacked_enriched/ppt/slides/slide26.xml")
slide = slide_path.read_text(encoding="utf-8")

SUBS = [
    # EVIDENCE — "What moved"
    (
        "<a:t>What moved</a:t>",
        "<a:t>Reliance primary &#x20B9;17.23 Cr &#x2014; 46.8% converted; &#x20B9;9.17 Cr unsold. DMart improved to 92.2%; South-2 residual &#x20B9;1.19 Cr. Apollo 74.4%; &#x20B9;2.47 Cr gap. Lulu, H&amp;G, Wellness: offtake exceeds primary supply.</a:t>",
    ),
    # IMPLICATION — "Why it matters"
    (
        "<a:t>Why it matters</a:t>",
        "<a:t>&#x20B9;14.18 Cr billed-but-unsold pipeline risk (Reliance &#x20B9;9.17, Apollo &#x20B9;2.47, DMart &#x20B9;1.19, Metro &#x20B9;1.35). &#x20B9;1.27 Cr supply-constrained upside at Lulu, H&amp;G, and Wellness &#x2014; demand established, primary not keeping pace.</a:t>",
    ),
    # ACTION — "What changes now"
    (
        "<a:t>What changes now</a:t>",
        "<a:t>Reliance: no new loading; NKAM drives secondary sell-through in North &amp; East. Apollo: NKAM to push SKU-level sell-through; reconcile zone stock. Lulu/H&amp;G/Wellness: scale primary to match pull-through; avoid OOS. DMart: monitor South-2 DC fill.</a:t>",
    ),
    # OWNER — "Who closes it"
    (
        "<a:t>Who closes it</a:t>",
        "<a:t>Reliance: NKAM (Reliance team). Apollo: NKAM (Apollo team). Lulu / H&amp;G / Wellness: NKAM + Supply Planning. DMart: NKAM. Review at next weekly MT call.</a:t>",
    ),
]

for old, new in SUBS:
    if old not in slide:
        print(f"WARNING — not found: {repr(old[:60])}")
    else:
        slide = slide.replace(old, new, 1)
        print(f"OK: replaced {repr(old[:50])}")

slide_path.write_text(slide, encoding="utf-8")
print("slide26.xml EVIDENCE section updated.")
