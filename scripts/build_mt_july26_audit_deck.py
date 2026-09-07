#!/usr/bin/env python3
"""Build: "Modern Trade July'26 Offtake Audit & Nielsen Category Performance".

Ten slides, portrait 7.5 x 13.33in, drawn with scripts/deck_kit.py so the deck
sits in the same visual family as the existing MT leadership pack.

Every figure carries a source. Nothing here is estimated: where a number could
not be verified against a file on disk the slide says so in plain words instead
of showing a value. See DATA_NOTES at the foot of this file for the gaps.

    python scripts/build_mt_july26_audit_deck.py -o MT_July26_Offtake_Audit.pptx
    python scripts/check_deck_geometry.py MT_July26_Offtake_Audit.pptx
    python scripts/preview_deck.py MT_July26_Offtake_Audit.pptx /tmp/preview
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import deck_kit as k  # noqa: E402

TOTAL = 10

SRC_OFFTAKE = ("Source: PowerBI/RawDataFolders/Offtake_Monthly/"
               "offtake_store_article_Jul_26.csv (221,548 rows), Reliance Brand "
               "Counter excluded per the offtake dedup rule.")
SRC_NIELSEN = ("Source: NielsenIQ, India Urban Modern Trade, July 2026 "
               "(data/nielsen/*.csv, data/nielsen_jul26.json).")

# ===========================================================================
# VERIFIED FIGURES — from the Data Verification Sub-Agent's truth matrix.
# ₹ Lakh unless the name says Cr. 1 Cr = 100 L.
# ===========================================================================

JUL26_EX_BC = 3621.47      # raw CSV, Brand Counter excluded
JUL26_INC_BC = 4067.28     # same file, unfiltered
JUL26_BC = 445.81          # Reliance Brand Counter partition, 22,818 rows
DASHJS_JUL26 = 3414.00     # what dashboard/data.js currently publishes
FSN_PAN_INDIA = 206.64     # the dropped chain
ROUNDING = 0.83            # 2-dp rounding across the six retained zones
JUL25_EX_BC = 2199.19
MAY26_EX_BC = 4019.42
APR26_EX_BC = 3588.51

# chain: (Jul'26, share %, Jul'25, YoY %, May'26, vs May %)
CHAINS = [
    ("D-Mart",          1396.72, 38.6,  780.25,  79.0, 1517.52,  -8.0),
    ("Reliance Retail", 805.64,  22.2,  556.79,  44.7,  990.20, -18.6),
    ("Apollo",          718.16,  19.8,  287.14, 150.1,  751.19,  -4.4),
    ("Nykaa / FSN",     206.64,   5.7,  191.40,   8.0,  207.87,  -0.6),
    ("Lulu",            169.77,   4.7,   47.32, 258.8,  116.40,  45.9),
    ("Wellness Forever", 72.09,   2.0,   71.95,   0.2,  101.64, -29.1),
    ("Health & Glow",    50.81,   1.4,   79.42, -36.0,   87.44, -41.9),
    ("More Retail",      40.69,   1.1,   35.32,  15.2,   55.11, -26.2),
    ("Spencer",           8.55,   0.2,   14.16, -39.6,   11.99, -28.7),
]

# zone as the source labels it — this is the view that ties to dashboard/data.js
ZONES = [
    ("South 1",    820.63, 22.7),
    ("West",       781.34, 21.6),
    ("North",      697.90, 19.3),
    ("South 2",    493.45, 13.6),
    ("East",       355.21,  9.8),
    ("Central",    266.30,  7.4),
    ("Pan India",  206.64,  5.7),
]

# 28 months, Apr'24 -> Jul'26
MONTHS = (["Apr'24", "May'24", "Jun'24", "Jul'24", "Aug'24", "Sep'24", "Oct'24",
           "Nov'24", "Dec'24", "Jan'25", "Feb'25", "Mar'25"] +
          ["Apr'25", "May'25", "Jun'25", "Jul'25", "Aug'25", "Sep'25", "Oct'25",
           "Nov'25", "Dec'25", "Jan'26", "Feb'26", "Mar'26"] +
          ["Apr'26", "May'26", "Jun'26", "Jul'26"])

# FY25 has no true offtake anywhere on disk; distributor secondary is the proxy
FY25_SECONDARY = [2160.81, 2240.04, 1995.21, 2195.99, 1420.11, 2110.12,
                  1439.12, 1923.32, 2096.81, 1773.06, 2027.30, 1950.47]
FY26_OFFTAKE = [2271.99, 2449.48, 2270.36, 2199.19, 2435.71, 2095.21,
                2651.74, 2819.99, 2891.30, 3039.29, 2761.18, 3234.43]
FY27_OFFTAKE = [APR26_EX_BC, MAY26_EX_BC, None, JUL26_EX_BC]   # Jun'26 = no file
FY26_PRIMARY = [3174.60, 2366.90, 2182.64, 2472.90, 2162.39, 2223.75,
                2674.89, 3329.34, 2820.61, 3665.41, 2924.94, 2902.00]
FY27_PRIMARY = [5076.86, 4415.74, 4167.38, 4921.31]

OFFTAKE_SERIES = [None] * 12 + FY26_OFFTAKE + FY27_OFFTAKE
PRIMARY_SERIES = [None] * 12 + FY26_PRIMARY + FY27_PRIMARY
SECONDARY_SERIES = FY25_SECONDARY + [None] * 16

# --- Nielsen, face wash, July 2026
FW_BRANDS = [
    ("Himalaya",      22.8, 23.2, -0.4, 18.7,  13.9, 99.5, 9177),
    ("Garnier",       13.3, 14.5, -1.2, 10.9,   6.6, 88.5, 6396),
    ("Pond's",        13.0, 14.2, -1.1, 10.7,   6.9, 97.5, 5869),
    ("Mamaearth",     11.2,  8.8,  2.4,  9.2,  47.7, 89.2, 7025),
    ("Clean & Clear",  7.7,  7.7,  0.0,  6.3,  15.7, 97.0, 3823),
    ("Joy",            6.7,  6.6,  0.1,  5.5,  17.7, 75.1, 5924),
    ("Lakme",          4.0,  3.5,  0.5,  3.3,  35.0, 77.8, 3403),
    ("Nivea",          3.4,  5.1, -1.7,  2.8, -21.1, 85.3, 2233),
]
FW_PACKS = [("150 ml", 32.1, 20.1, 59.7, 39.1), ("100 ml", 24.0, 26.6, -9.8, 29.2),
            ("50 ml", 14.9, 13.4, 11.2, 18.1), ("200 ml", 4.8, 6.5, -26.2, 5.8),
            ("125 ml", 2.0, 0.4, 400.0, 2.4), ("240 ml", 1.8, 1.6, 12.5, 2.2)]

SH_PACKS = [("650 ml", 40.5, 35.7, 13.4, 26.0), ("340 ml", 23.6, 30.4, -22.4, 15.1),
            ("180 ml", 22.3, 21.9, 1.8, 14.3), ("1000 ml", 20.7, 13.1, 58.0, 13.3),
            ("400 ml", 7.2, 5.3, 35.8, 4.6), ("200 ml", 6.1, 5.6, 8.9, 3.9),
            ("580 ml", 5.6, 5.5, 1.8, 3.6)]

SLIDES = []


def slide(fn):
    SLIDES.append(fn)
    return fn


def cr(lakh):
    return f"₹{lakh / 100:,.2f} Cr"


def pct(v, dp=1):
    return f"▲ {v:.{dp}f}%" if v >= 0 else f"▼ {abs(v):.{dp}f}%"


# ===========================================================================
# 01 — title
# ===========================================================================
@slide
def s01(prs):
    s = k._blank(prs, k.DEEP)
    k.text(s, k.ML, 2.30, k.CW, 0.26, "HONASA CONSUMER  ·  MODERN TRADE",
           size=9.5, bold=True, color=k.TEAL, spacing=1.6)
    k.rect(s, k.ML, 2.74, 1.05, 0.055, fill=k.TEAL)

    k.text(s, k.ML, 3.05, k.CW, 2.60,
           "Modern Trade July'26\nOfftake Audit &\nNielsen Category\nPerformance",
           size=33, bold=True, color=k.WHITE, line_spacing=1.02)

    k.text(s, k.ML, 5.95, k.CW, 0.70,
           "An audited July'26 baseline, the correction behind it, and what the "
           "external category read says about where the growth is coming from.",
           size=12, color=k.RGBColor(0xC8, 0xDC, 0xD7), line_spacing=1.28)

    # audited baseline block
    k.rect(s, k.ML, 7.05, k.CW, 1.98, fill=k.RGBColor(0x11, 0x6F, 0x68),
           shape=k.MSO_SHAPE.ROUNDED_RECTANGLE, adj=0.05)
    k.text(s, k.ML + 0.32, 7.28, k.CW - 0.64, 0.22, "AUDITED JULY'26 BASELINE",
           size=8.5, bold=True, color=k.RGBColor(0xA8, 0xD5, 0xCA), spacing=1.2)
    k.text(s, k.ML + 0.32, 7.56, 3.10, 0.62, cr(JUL26_EX_BC), size=32, bold=True,
           color=k.WHITE)
    k.text(s, k.ML + 0.32, 8.22, k.CW - 0.64, 0.62,
           f"MT offtake NSV, Reliance Brand Counter excluded. Replaces the "
           f"{cr(DASHJS_JUL26)} previously carried on the dashboard — a "
           f"{cr(JUL26_EX_BC - DASHJS_JUL26)} understatement.",
           size=9.5, color=k.RGBColor(0xC8, 0xDC, 0xD7), line_spacing=1.22)

    for i, (lab, val) in enumerate([("vs Jul'25", pct(64.7)),
                                    ("Chains live", "26"),
                                    ("Transacting stores", "10,484")]):
        x = k.ML + i * (k.CW / 3)
        k.text(s, x, 9.45, k.CW / 3 - 0.10, 0.20, lab.upper(), size=8,
               bold=True, color=k.TEAL, spacing=1.0)
        k.text(s, x, 9.70, k.CW / 3 - 0.10, 0.34, val, size=15, bold=True,
               color=k.WHITE)

    k.text(s, k.ML, 12.44, k.CW, 0.24,
           "Leadership review  ·  prepared September 2026", size=9,
           color=k.RGBColor(0xC8, 0xDC, 0xD7))
    k.text(s, k.ML, SRC := 13.00 - 0.0, k.CW, 0.24,
           "All offtake figures recomputed from source store x article extracts.",
           size=7.5, color=k.RGBColor(0x5F, 0x71, 0x6E))
    return s


# ===========================================================================
# 02 — executive summary / why the audit happened
# ===========================================================================
@slide
def s02(prs):
    s, y = k.page(
        prs, "executive summary  ·  audit context",
        "The published July number was ₹2.07 Cr light — one chain was being "
        "read as a subtotal",
        "What the audit found, why it mattered, and what is now safe to quote.",
        page_no=2, total=TOTAL,
        source=SRC_OFFTAKE + " Comparison value read from dashboard/data.js.")

    y = k.kpi_row(s, y, [
        ("Audited Jul'26", cr(JUL26_EX_BC), "source of truth", "n"),
        ("Previously shown", cr(DASHJS_JUL26), "understated", "-"),
        ("Correction", f"+{cr(JUL26_EX_BC - DASHJS_JUL26)}", "▲ 6.1%", "+"),
    ])
    y += 0.34

    y = k.insight(s, y, "what the audit found", [
        ("The defect",
         "The FY27 zone build treats \"Pan India\" as a roll-up row. Nykaa/FSN is "
         "the only chain filed under that zone, so its entire month was written "
         "over by the subtotal and never counted."),
        ("The size",
         f"₹{FSN_PAN_INDIA:,.2f} L of Nykaa/FSN plus ₹{ROUNDING:.2f} L of rounding "
         f"across the six retained zones — {cr(JUL26_EX_BC - DASHJS_JUL26)} in "
         f"total, all of it explained."),
        ("The rest is clean",
         "All six other zones tie to the raw extract to the rupee-lakh. This is a "
         "single labelling fault, not a broken pipeline."),
    ], h_item=0.86)
    y += 0.22

    y = k.insight(s, y, "why it mattered", [
        ("Understated growth",
         "July was being reported 6.1% below actual, which flows into every "
         "chain, zone and target view built off the same block."),
        ("A blind account",
         "Nykaa/FSN is a ₹2 Cr-a-month account. It was invisible in the zone "
         "view while still sitting in the chain view — the two never agreed."),
    ], h_item=0.72)
    y += 0.22

    y = k.sowhat(s, y, [
        ("Adopt", f"{cr(JUL26_EX_BC)} is the July baseline for targets and QBR."),
        ("Fix", "Give Nykaa/FSN a real zone so the roll-up stops overwriting it."),
        ("Re-check", "Apr and May'26 zones do not tie either — rebuild them."),
    ], h=1.34)
    k.fits(y, "s02")
    return s


# ===========================================================================
# 03 — the reconciliation bridge
# ===========================================================================
@slide
def s03(prs):
    s, y = k.page(
        prs, "reconciled offtake impact",
        "July'26 offtake is ₹36.21 Cr — Nykaa/FSN accounts for the whole gap",
        "Pre-correction to post-correction, every rupee attributed.",
        page_no=3, total=TOTAL,
        source=SRC_OFFTAKE + " Pre-correction = sum of the six zones carried in "
                             "dashboard/data.js for Jul-26.")

    y = k.bridge(s, y, DASHJS_JUL26,
                 [("Nykaa / FSN\n(Pan India)", FSN_PAN_INDIA),
                  ("Zone rounding", ROUNDING)],
                 JUL26_EX_BC, h=3.15,
                 start_label="Published\n₹34.14 Cr", end_label="Audited\n₹36.21 Cr",
                 unit="₹ Lakh", floor=3300)
    y += 0.30

    y = k.data_table(
        s, y, ["Zone", "Audited Jul'26", "Contribution", "Ties to dashboard"],
        [[z, f"{v:,.2f}", f"{c:.1f}%",
          "Yes" if z != "Pan India" else "No — dropped"] for z, v, c in ZONES] +
        [["TOTAL", f"{JUL26_EX_BC:,.2f}", "100.0%", "—"]],
        [0.28, 0.24, 0.22, 0.26], hi_rows=("Pan India", "TOTAL"), row_h=0.27)
    y += 0.30

    y = k.insight(s, y, "read the bridge", [
        ("Six zones already correct",
         "Central through West reproduce the source extract exactly. Central is "
         f"present and healthy at ₹{266.30:,.2f} L, 7.4% of the month."),
        ("One zone missing entirely",
         "Pan India carries a single node — Nykaa/FSN — and never reached the "
         "published total."),
        ("Brand Counter stays out",
         f"₹{JUL26_BC:,.2f} L across 321 staffed Reliance doors is held in the "
         f"separate counter partition. Adding it to offtake would double-count."),
    ], h_item=0.72)
    y += 0.26

    y = k.sowhat(s, y, [
        ("Restate", "July'26 goes to leadership at ₹36.21 Cr, not ₹34.14 Cr."),
        ("Repair", "Nykaa/FSN needs its own zone before the next refresh."),
        ("Re-run", "Apr and May'26 zones are unreconciled — rebuild both."),
    ], h=1.24)
    k.fits(y, "s03")
    return s


# ===========================================================================
# 04 — key account dynamics
# ===========================================================================
@slide
def s04(prs):
    s, y = k.page(
        prs, "key account offtake dynamics",
        "Three chains carry 81% of July; Apollo and Lulu are the growth engines",
        "Year-on-year is like-for-like. The sequential column is against May'26 — "
        "there is no June'26 extract on file.",
        page_no=4, total=TOTAL,
        source=SRC_OFFTAKE + " Jul'25 from data/raw_drops/_agg/offtake_fy26.json; "
                             "May'26 from offtake_store_article_May_26.csv.")

    y = k.bars(s, y, [(c[0], c[1], f"{c[1]:,.0f}") for c in CHAINS[:7]],
               h_row=0.34, gap=0.08,
               hi=("D-Mart", "Reliance Retail", "Apollo"),
               note="₹ Lakh, Jul'26, Reliance shown ex-Brand Counter. "
                    "Top three = 80.6% of the month.")
    y += 0.34

    y = k.data_table(
        s, y,
        ["Chain", "Jul'26", "Share", "vs Jul'25", "vs May'26"],
        [[name, f"{v:,.0f}", f"{sh:.1f}%", pct(yoy), pct(mm)]
         for name, v, sh, _j25, yoy, _m26, mm in CHAINS] +
        [["TOTAL", f"{JUL26_EX_BC:,.0f}", "100.0%", pct(64.7), pct(-9.9)]],
        [0.28, 0.17, 0.14, 0.20, 0.21],
        hi_rows=("TOTAL",), row_h=0.26)
    y += 0.28

    y = k.insight(s, y, "the account read", [
        ("Apollo is the standout",
         "₹718 L, up 150% year on year, now the third-largest account at 19.8% "
         "of the channel — from under 13% a year ago. Lulu is the other engine, "
         "up 259% and the only top-10 account also up sequentially."),
        ("Health & Glow and Spencer are contracting",
         "Down 36% and 40% year on year. Small in value, but both have fallen "
         "in every month since April."),
    ], h_item=0.86)
    y += 0.20

    k.rect(s, k.ML, y, k.CW, 0.86, fill=k.RGBColor(0xFB, 0xF0, 0xE8),
           shape=k.MSO_SHAPE.ROUNDED_RECTANGLE, adj=0.10)
    k.rect(s, k.ML, y, 0.045, 0.86, fill=k.AMBER)
    k.text(s, k.ML + 0.18, y + 0.13, k.CW - 0.36, 0.20, "DATA FLAG — NOT A BUSINESS READ",
           size=8, bold=True, color=k.AMBER, spacing=1.0)
    k.text(s, k.ML + 0.18, y + 0.37, k.CW - 0.36, 0.42,
           "Walmart C&C is absent from the July extract altogether (₹15.11 L in "
           "Jul'25). It was also missing in May but present in April, so treat this "
           "as a feed gap until the source owner confirms it.",
           size=9, color=k.INK, line_spacing=1.18)
    y += 0.86
    k.fits(y, "s04")
    return s


# ===========================================================================
# 05 — section divider
# ===========================================================================
@slide
def s05(prs):
    return k.divider(
        prs, "section two", "NielsenIQ Category\nIntelligence",
        "External category read for Face Wash and Shampoo through July 2026. "
        "India Urban Modern Trade. Measured on a different base to internal NSV "
        "— the two are never compared as one series.",
        page_no=5, total=TOTAL)


# ===========================================================================
# 06 — face wash
# ===========================================================================
@slide
def s06(prs):
    s, y = k.page(
        prs, "nielseniq  ·  face wash",
        "Mamaearth is the No.4 face wash brand at 11.2% share — and the fastest "
        "growing of the top eight",
        "Share is up 2.4 points year on year while the three brands above it all "
        "lost ground.",
        page_no=6, total=TOTAL, source=SRC_NIELSEN)

    y = k.kpi_row(s, y, [
        ("July value", "₹9.2 Cr", "▲ 47.7% YoY", "+"),
        ("Value share", "11.2%", "▲ +2.4 pp", "+"),
        ("Weighted distn", "89.2%", "▲ from 82.8%", "+"),
        ("Rel. numeric", "57.8%", "▼ from 59.5%", "-"),
    ])
    y += 0.32

    y = k.donut(s, k.ML, y, k.CW, 2.02,
                [(b, sh) for b, sh, *_ in FW_BRANDS] +
                [("All others", round(100 - sum(b[1] for b in FW_BRANDS), 1))],
                [k.MUTED, k.BLUE, k.RGBColor(0x8A, 0x93, 0x9C), k.TEAL,
                 k.RGBColor(0xA8, 0xC5, 0xBE), k.AMBER,
                 k.RGBColor(0xC0, 0xB8, 0xAC), k.RGBColor(0xD6, 0x54, 0x4D),
                 k.RULE],
                centre_value="11.2%", centre_label="MAMAEARTH")
    y += 0.26

    y = k.data_table(
        s, y, ["Brand", "Share", "Δ pp YoY", "Value ₹Cr", "YoY", "PDO"],
        [[b, f"{sh:.1f}%",
          ("flat" if abs(d) < 0.05 else f"{'▲ +' if d > 0 else '▼ '}{abs(d):.1f}"),
          f"{val:.1f}", pct(yoy), f"{pdo:,.0f}"]
         for b, sh, _, d, val, yoy, _, pdo in FW_BRANDS],
        [0.24, 0.14, 0.16, 0.15, 0.16, 0.15], hi_rows=("Mamaearth",), row_h=0.25)
    y += 0.30

    y = k.insight(s, y, "what is driving it", [
        ("Growth is velocity-led, not just reach",
         "Value +48.4% against stores +25.6%. Per-dealer offtake rose 17.6%, so "
         "the shelf is working harder, not merely wider."),
        ("The 150 ml pack is where the category moved",
         "₹32.1 Cr in July, up 59.7%, now 39.1% of category value while 100 ml "
         "fell 9.8%."),
        ("Reach quality is the watch-out",
         "Weighted distribution is at 89.2% but relative numeric slipped to "
         "57.8%. The stores left to add are lower-value ones."),
    ], h_item=0.68)
    y += 0.20

    y = k.sowhat(s, y, [
        ("Protect", "150 ml availability is the single biggest lever on share."),
        ("Qualify", "Set store-addition and PDO targets separately."),
    ], h=1.02)
    k.fits(y, "s06")
    return s


# ===========================================================================
# 07 — shampoo
# ===========================================================================
@slide
def s07(prs):
    s, y = k.page(
        prs, "nielseniq  ·  shampoo",
        "Shampoo value is consolidating into bulk packs — but we cannot yet see "
        "Mamaearth's position in it",
        "Category pack architecture is clear. Brand-level detail is not in the "
        "supplied file.",
        page_no=7, total=TOTAL,
        source=SRC_NIELSEN + " Pack cut from Shampoo_Jul26_PackSize_Analysis.csv.")

    y = k.kpi_row(s, y, [
        ("Bulk >250 ml", "72.1%", "of July value", "n"),
        ("650 ml", "₹40.5 Cr", "▲ 13.4% YoY", "+"),
        ("1000 ml", "₹20.7 Cr", "▲ 58.0% YoY", "+"),
        ("340 ml", "₹23.6 Cr", "▼ 22.4% YoY", "-"),
    ])
    y += 0.34

    y = k.col_compare(
        s, y, [(p, [ly, cy]) for p, cy, ly, _, _ in SH_PACKS],
        ["Jul'25", "Jul'26"], [k.RULE, k.TEAL], h=2.28, unit="₹ Cr",
        value_fmt="{:,.1f}")
    y += 0.22

    y = k.data_table(
        s, y, ["Pack", "Jul'26 ₹Cr", "Jul'25 ₹Cr", "YoY", "Share of value"],
        [[p, f"{cy:.1f}", f"{ly:.1f}", pct(yy), f"{sh:.1f}%"]
         for p, cy, ly, yy, sh in SH_PACKS],
        [0.22, 0.20, 0.20, 0.18, 0.20],
        hi_rows=("650 ml", "1000 ml"), row_h=0.25)
    y += 0.30

    y = k.insight(s, y, "the category structure", [
        ("Bulk is taking the category",
         "650 ml leads at ₹40.5 Cr and 1000 ml grew 58%. Together with 580 ml "
         "they are 42.9% of July value."),
        ("The mid pack is losing",
         "340 ml fell 22.4% year on year — the only large pack in decline, and "
         "the clearest place value is migrating from."),
        ("Trial packs are immaterial here",
         "Packs up to 50 ml are about 0.1% of value in this Modern Trade bottle "
         "cut. Entry-pack strategy has to be judged elsewhere."),
    ], h_item=0.68)
    y += 0.20

    k.rect(s, k.ML, y, k.CW, 1.02, fill=k.RGBColor(0xFB, 0xF0, 0xE8),
           shape=k.MSO_SHAPE.ROUNDED_RECTANGLE, adj=0.09)
    k.rect(s, k.ML, y, 0.045, 1.02, fill=k.AMBER)
    k.text(s, k.ML + 0.18, y + 0.13, k.CW - 0.36, 0.20,
           "OPEN GAP — BLOCKS A SHAMPOO DECISION", size=8, bold=True,
           color=k.AMBER, spacing=1.0)
    k.text(s, k.ML + 0.18, y + 0.37, k.CW - 0.36, 0.58,
           "The supplied Shampoo file carries pack sizes with no brand identifier, "
           "so there is no Mamaearth share, value, WD or PDO for the category. "
           "Request the brand-by-pack extract before any pack-mix or price-ladder "
           "decision is taken on shampoo.",
           size=9, color=k.INK, line_spacing=1.18)
    y += 1.02
    k.fits(y, "s07")
    return s


# ===========================================================================
# 08 — multi-year momentum
# ===========================================================================
@slide
def s08(prs):
    s, y = k.page(
        prs, "multi-year momentum  ·  apr'24 to jul'26",
        "Offtake is up 65% year on year, on a base that only becomes "
        "like-for-like from April 2025",
        "FY25 has no true offtake anywhere in the source set — the dotted line is "
        "distributor secondary, shown as an indicative anchor only.",
        page_no=8, total=TOTAL,
        source="Source: offtake from data/raw_drops/_agg/offtake_fy26.json and the "
               "Apr/May/Jul'26 store x article extracts; primary from "
               "primary_article_*.csv; FY25 from "
               "Distributor_secondary_FY25_Apr24_Mar25.csv.")

    y = k.trend(s, y, MONTHS, [
        {"name": "Primary NSV", "values": PRIMARY_SERIES, "color": k.BLUE,
         "end_label": "4,921"},
        {"name": "Offtake (ex-BC)", "values": OFFTAKE_SERIES, "color": k.TEAL,
         "width": 2.4, "end_label": "3,621", "end_label_below": True},
        {"name": "FY25 distributor secondary (proxy)", "values": SECONDARY_SERIES,
         "color": k.MUTED, "width": 1.5, "dash": "DASH"},
    ], h=3.30, unit="₹ Lakh, monthly", label_every=3)
    y += 0.26

    y = k.data_table(
        s, y, ["Period", "Offtake", "Primary", "Basis"],
        [["FY25 (Apr'24–Mar'25)", "not available", "not available",
          "distributor secondary only"],
         ["FY26 (Apr'25–Mar'26)", "₹311.20 Cr", "₹329.00 Cr", "full 12 months"],
         ["FY27 to date (Apr–Jul'26)", "₹112.29 Cr*", "₹185.81 Cr",
          "*3 of 4 months"]],
        [0.34, 0.20, 0.20, 0.26], row_h=0.30)
    y += 0.30

    y = k.insight(s, y, "how to read this", [
        ("The growth is real and verified",
         "July'26 at ₹36.21 Cr against ₹21.99 Cr in July'25 is a like-for-like "
         "+64.7% — both sides are true offtake, both exclude Brand Counter."),
        ("Two months of FY27 are still open",
         "June'26 offtake has no source file at all, and April/May'26 zone "
         "figures on the dashboard do not tie to the raw extracts."),
        ("FY25 is not a comparison base",
         "Distributor secondary sits one step above offtake in the chain. It "
         "anchors scale; it cannot carry a growth rate."),
    ], h_item=0.72)
    y += 0.24

    y = k.sowhat(s, y, [
        ("Quote", "FY26 ₹311.20 Cr and Jul'26 ₹36.21 Cr are safe to publish."),
        ("Withhold", "No FY25-vs-FY26 growth rate until true primary arrives."),
        ("Close", "June'26 is the one file that completes Q1 FY27."),
    ], h=1.24)
    k.fits(y, "s08")
    return s


# ===========================================================================
# 09 — strategic takeaways
# ===========================================================================
@slide
def s09(prs):
    s, y = k.page(
        prs, "strategic commercial takeaways",
        "The growth is broad and genuine; the reporting around it is what needs "
        "fixing",
        "Where the value is coming from, and what could take it away.",
        page_no=9, total=TOTAL,
        source="Source: as per slides 3, 4, 6, 7 and 8.")

    k.text(s, k.ML, y, k.CW, 0.22, "GROWTH DRIVERS", size=8.5, bold=True,
           color=k.GREEN, spacing=1.2)
    y += 0.30
    for label, body, val in [
        ("Apollo scale-up", "Third-largest account from a standing start; "
         "+150% year on year and now a fifth of the channel.", "+₹431 L YoY"),
        ("Face wash share gain", "Rank 4 at 11.2%, +2.4 points, while every "
         "brand above lost share. Velocity-led, not distribution-led.", "+2.4 pp"),
        ("150 ml pack shift", "The category's value pool moved to 150 ml, up "
         "59.7%. Mamaearth is positioned in the growing pack.", "39.1% of category"),
        ("Bulk shampoo demand", "650 ml and 1000 ml both growing strongly — "
         "72.1% of category value is now above 250 ml.", "1000 ml +58%"),
    ]:
        k.rect(s, k.ML, y, 0.045, 0.66, fill=k.GREEN)
        b = k.text(s, k.ML + 0.16, y, k.CW - 1.55, 0.66,
                   [(label, {"bold": True, "color": k.INK, "size": 9.5}),
                    ("  —  ", {"color": k.RULE, "size": 9.5}),
                    (body, {"color": k.MUTED, "size": 9.5})], line_spacing=1.18)
        b.text_frame.word_wrap = True
        k.text(s, k.ML + k.CW - 1.34, y + 0.02, 1.34, 0.24, val, size=9.5,
               bold=True, color=k.GREEN, align=k.PP_ALIGN.RIGHT)
        y += 0.70
    y += 0.16

    k.text(s, k.ML, y, k.CW, 0.22, "RISK AREAS", size=8.5, bold=True,
           color=k.RED, spacing=1.2)
    y += 0.30
    for label, body, val in [
        ("Account concentration", "D-Mart, Reliance and Apollo are 80.6% of the "
         "channel. A single listing or planogram change moves the month.", "80.6%"),
        ("Sequential softening", "July is 9.9% below May across almost every "
         "account. Without a June file we cannot see the shape of the decline.",
         "−9.9% vs May"),
        ("Reach quality", "Relative numeric distribution fell to 57.8% while "
         "weighted held at 89.2% — the remaining stores are lower value.", "−1.7 pp"),
        ("Reporting integrity", "One chain was dropped from the zone view, "
         "April and May zones do not tie, and June is missing entirely.",
         "3 open defects"),
    ]:
        k.rect(s, k.ML, y, 0.045, 0.66, fill=k.RED)
        b = k.text(s, k.ML + 0.16, y, k.CW - 1.55, 0.66,
                   [(label, {"bold": True, "color": k.INK, "size": 9.5}),
                    ("  —  ", {"color": k.RULE, "size": 9.5}),
                    (body, {"color": k.MUTED, "size": 9.5})], line_spacing=1.18)
        b.text_frame.word_wrap = True
        k.text(s, k.ML + k.CW - 1.34, y + 0.02, 1.34, 0.24, val, size=9.5,
               bold=True, color=k.RED, align=k.PP_ALIGN.RIGHT)
        y += 0.70
    y += 0.18

    y = k.sowhat(s, y, [
        ("Bank", "Face wash momentum and Apollo are the two proven engines."),
        ("Hedge", "Concentration means chain-level risk is channel-level risk."),
        ("Close", "No pack or zone decision until the data gaps are shut."),
    ], h=1.20)
    k.fits(y, "s09")
    return s


# ===========================================================================
# 10 — action plan and governance
# ===========================================================================
@slide
def s10(prs):
    s, y = k.page(
        prs, "action plan  ·  governance roadmap",
        "Five fixes, named owners, closed by end September",
        "Three are data-integrity items that gate the others. Nothing on this "
        "page needs new investment.",
        page_no=10, total=TOTAL,
        source="Owners and dates to be confirmed in the monthly MT governance call.")

    k.text(s, k.ML, y, k.CW, 0.22, "PRIORITY ACTIONS", size=8.5, bold=True,
           color=k.TEAL, spacing=1.2)
    y += 0.30
    y = k.data_table(
        s, y, ["#", "Action", "Owner", "By"],
        [["01", "Re-zone Nykaa/FSN so the roll-up stops overwriting it",
          "Sales Analytics", "12-Sep"],
         ["02", "Source the June'26 offtake extract and rebuild Apr–Jun zones",
          "MT Analytics", "15-Sep"],
         ["03", "Settle one zone master (Telangana/AP and Kerala conflict)",
          "Sales Analytics", "19-Sep"],
         ["04", "Request Nielsen brand-by-pack Shampoo extract",
          "Category / Insights", "22-Sep"],
         ["05", "Confirm Walmart C&C July feed — gap or genuine nil",
          "NKAM", "12-Sep"]],
        [0.07, 0.53, 0.22, 0.18], row_h=0.34,
        aligns=[k.PP_ALIGN.CENTER, k.PP_ALIGN.LEFT, k.PP_ALIGN.LEFT,
                k.PP_ALIGN.RIGHT])
    y += 0.34

    k.text(s, k.ML, y, k.CW, 0.22, "GOVERNANCE — WHAT CHANGES PERMANENTLY",
           size=8.5, bold=True, color=k.TEAL, spacing=1.2)
    y += 0.30
    y = k.insight(s, y, "", [
        ("Monthly tie-out before publication",
         "Zone and chain totals must reconcile to the raw store x article extract "
         "before any number leaves the dashboard. A zone that does not tie is "
         "held back, not published."),
        ("One source label on every chart",
         "External Nielsen share and internal NSV stay on separate slides with "
         "their basis named. They are never plotted on one axis."),
        ("Missing is not zero",
         "A chain or month with no feed is shown as \"no data\", never as nil. "
         "Walmart C&C is the live example."),
    ], h_item=0.86)
    y += 0.24

    k.text(s, k.ML, y, k.CW, 0.22, "OPEN ITEMS CARRIED FORWARD", size=8.5,
           bold=True, color=k.AMBER, spacing=1.2)
    y += 0.30
    y = k.data_table(
        s, y, ["Open item", "What it blocks", "Needed"],
        [["June'26 offtake", "True MoM and Q1 FY27 close", "Source extract"],
         ["FY25 primary", "Any two-year like-for-like", "Billing extract"],
         ["Shampoo by brand", "Pack and price-ladder calls", "Nielsen file"]],
        [0.30, 0.42, 0.28], row_h=0.30)
    y += 0.30

    y = k.sowhat(s, y, [
        ("Approve", f"{cr(JUL26_EX_BC)} as the July baseline for Q2 targets."),
        ("Assign", "The five owners above, reviewed in the next MT call."),
    ], h=1.00)
    k.fits(y, "s10")
    return s


# ===========================================================================
DATA_NOTES = """
Verified against source; see the Data Truth Matrix for full derivations.

NOT PUBLISHED because it could not be verified:
  - Jul'26 vs Jun'26 MoM — no offtake_store_article_Jun_26.csv exists.
    Sequential comparisons on this deck are against May'26 and labelled.
  - FY25 primary — Primary_Article_Synthesized_FY25.csv is the distributor
    secondary file re-split, not billing. Shown as an indicative proxy only.
  - Mamaearth-level shampoo share/value/WD/PDO — not in the supplied file.
  - Nielsen "Simple 2.6%" — outside the top-8 extract held in the repo.
  - Walmart C&C -100% — flagged as a feed gap, not stated as a decline.

ZONE MASTER: this deck uses the source Zone column (which ties to
dashboard/data.js). The pipeline's canon_zone_from_state() disagrees on
Telangana/AP and Kerala, moving c.₹376 L between South 1 and South 2.
That conflict is action 03 on slide 10.
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out",
                    default="MT_July26_Offtake_Audit_Nielsen.pptx")
    args = ap.parse_args()
    prs = k.new_deck()
    for fn in SLIDES:
        fn(prs)
    prs.save(args.out)
    print(f"built {args.out} — {len(SLIDES)} slides")


if __name__ == "__main__":
    main()
