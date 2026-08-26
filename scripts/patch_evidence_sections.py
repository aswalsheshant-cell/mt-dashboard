"""
Populate EVIDENCE / IMPLICATION / ACTION / OWNER sections on slides 4, 5, 6, 7
from the user-supplied screenshot content.
"""
import pathlib

BASE = pathlib.Path("unpacked_enriched/ppt/slides")

PATCHES = {
    # ── Slide 4 — Decision framework / growth levers ──────────────────────
    "slide4.xml": [
        (
            "<a:t>What moved</a:t>",
            "<a:t>5 validated growth levers are live; SAH / WD / PDO / OOS fields not yet field-reconciled for July</a:t>",
        ),
        (
            "<a:t>Why it matters</a:t>",
            "<a:t>Decisions without field reconciliation treat stock-timing noise as demand signal and risk driving wrong actions</a:t>",
        ),
        (
            "<a:t>What changes now</a:t>",
            "<a:t>Reconcile SAH, WD and OOS for August cycle; add PDO by state-chain; publish validated diagnostic by 31-Aug</a:t>",
        ),
        (
            "<a:t>Who closes it</a:t>",
            "<a:t>Analytics | 31-Aug</a:t>",
        ),
    ],

    # ── Slide 5 — Nielsen MT share / pack pilots ───────────────────────────
    "slide5.xml": [
        (
            "<a:t>What moved</a:t>",
            "<a:t>Face Wash MT share rose to 3.7%; Nielsen RMS MAT Jun-26 confirms demand pull — weighted distribution running ahead of value share</a:t>",
        ),
        (
            "<a:t>Why it matters</a:t>",
            "<a:t>Shampoo is the fastest-growing segment in MT — delay in expanding controlled pack pilots codes early-mover advantage to competitors</a:t>",
        ),
        (
            "<a:t>What changes now</a:t>",
            "<a:t>Run controlled pack pilots (top 3 formats) in DMart and Apollo; protect Face Wash hero EAN availability above 95% in top-100 stores</a:t>",
        ),
        (
            "<a:t>Who closes it</a:t>",
            "<a:t>Category + NKAM DMart / Apollo | Pilots by 15-Sep</a:t>",
        ),
    ],

    # ── Slide 6 — Zone portfolio / recoverable value ────────────────────────
    "slide6.xml": [
        (
            "<a:t>What moved</a:t>",
            "<a:t>MT offtake Jul-26: &#x20B9;36.06 Cr (+64.2% YoY vs Jul-25 &#x20B9;21.96 Cr); L3M May&#x2013;Jul &#x20B9;114.86 Cr (+65.8% YoY); Reliance Paisa Vasool event drove pipeline draw-forward &#x2014; same event expected mid-Aug; North + East hold 70.5% of recoverable gap</a:t>",
        ),
        (
            "<a:t>Why it matters</a:t>",
            "<a:t>West and South sustaining at 82&#x2013;84% conversion; concentrating intervention on North and East yields the highest recovery per rupee of commercial effort</a:t>",
        ),
        (
            "<a:t>What changes now</a:t>",
            "<a:t>Validate Reliance Aug-26 offtake in first week (Paisa Vasool effect expected ~40% MoM vs Jul; per LY pattern); run weekly ZSM gap closure on DMart and non-Reliance exceptions from 22-Aug; Reliance EAN-store review after Aug read is confirmed</a:t>",
        ),
        (
            "<a:t>Who closes it</a:t>",
            "<a:t>North ZSM + East ZSM | Weekly from 22-Aug</a:t>",
        ),
    ],

    # ── Slide 7 — West zone deep dive ─────────────────────────────────────
    "slide7.xml": [
        (
            "<a:t>What moved</a:t>",
            "<a:t>West &#x20B9;8.28 Cr conversion; DMart West 94.2% is the best DMart rate nationally; Reliance West 54.5% is the only exception; Wellness Forever 134.8% is a timing signal</a:t>",
        ),
        (
            "<a:t>Why it matters</a:t>",
            "<a:t>DMart West&#x2019;s 94.2% conversion proves EAN availability discipline works; Reliance West has 45% of billed inventory not selling through &#x2014; recoverable with store-level action</a:t>",
        ),
        (
            "<a:t>What changes now</a:t>",
            "<a:t>NKAM to map Reliance West EAN-store failures; restore top-10 declining articles by 30-Aug; hold Wellness Forever loading until timing discrepancy is explained</a:t>",
        ),
        (
            "<a:t>Who closes it</a:t>",
            "<a:t>NKAM Reliance West + NKAM Wellness | 30-Aug</a:t>",
        ),
    ],
}

for filename, subs in PATCHES.items():
    path = BASE / filename
    slide = path.read_text(encoding="utf-8")
    changed = 0
    for old, new in subs:
        if old in slide:
            slide = slide.replace(old, new, 1)
            changed += 1
        else:
            print(f"  WARNING — not found in {filename}: {repr(old[:60])}")
    path.write_text(slide, encoding="utf-8")
    print(f"{filename}: {changed}/{len(subs)} substitutions applied")

print("\nAll evidence sections patched.")
