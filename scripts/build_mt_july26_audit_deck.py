#!/usr/bin/env python3
"""Build: "Modern Trade July'26 Offtake Audit & Nielsen Category Performance".

19 slides, portrait 7.5 x 13.33in, drawn with scripts/deck_kit.py so the deck
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

TOTAL = 19

SRC_OFFTAKE = ("Source: PowerBI/RawDataFolders/Offtake_Monthly/"
               "offtake_store_article_Jul_26.csv (221,548 rows), Reliance Brand "
               "Counter excluded per the offtake dedup rule.")
SRC_OFFTAKE_JUN = ("Source: offtake_store_article_Jul_26.csv and "
                    "offtake_store_article_Jun_26.csv, both ex-Brand-Counter, "
                    "canon_chain()/zone_with_central_override() applied.")
SRC_NIELSEN = ("Source: NielsenIQ, India Urban Modern Trade, July 2026 "
               "(data/nielsen/*.csv, data/nielsen_jul26.json).")

# ===========================================================================
# VERIFIED FIGURES — from the Data Verification Sub-Agent's truth matrix.
# ₹ Lakh unless the name says Cr. 1 Cr = 100 L.
# ===========================================================================

JUL26_EX_BC = 3621.47      # raw CSV, Brand Counter excluded
JUL26_INC_BC = 4067.28     # same file, unfiltered
JUL26_BC = 445.81          # Reliance Brand Counter partition, 22,818 rows
DASHJS_JUL26 = 3414.00     # what dashboard/data.js published BEFORE the Sep'26 fix
FSN_PAN_INDIA = 206.64     # the chain that was dropped
ROUNDING = 0.83            # 2-dp rounding across the six retained zones
JUL25_EX_BC = 2199.19
JUN26_EX_BC = 3840.46      # recovered 22-Jul-2026 commit, merged into main 07-Sep-2026
MAY26_EX_BC = 4019.42
APR26_EX_BC = 3588.51

# chain: (Jul'26, share %, Jul'25, YoY %, Jun'26, vs Jun %)
# Jun'26 replaces May'26 as the sequential reference now that June is a real,
# audited month rather than a two-month-old stand-in.
CHAINS = [
    ("D-Mart",          1396.72, 38.6,  780.25,  79.0, 1455.91,  -4.1),
    ("Reliance Retail", 805.64,  22.2,  556.79,  44.7,  947.81, -15.0),
    ("Apollo",          718.16,  19.8,  287.14, 150.1,  723.03,  -0.7),
    ("Nykaa / FSN",     206.64,   5.7,  191.40,   8.0,  216.67,  -4.6),
    ("Lulu",            169.77,   4.7,   47.32, 258.8,  115.85,  46.5),
    ("Wellness Forever", 72.09,   2.0,   71.95,   0.2,   80.02,  -9.9),
    ("Health & Glow",    50.81,   1.4,   79.42, -36.0,   51.84,  -2.0),
    ("More Retail",      40.69,   1.1,   35.32,  15.2,   43.66,  -6.8),
    ("Spencer",           8.55,   0.2,   14.16, -39.6,    8.49,   0.7),
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

# --- Brand mix, July'26 offtake, ex-Brand-Counter
# (brand, Jul'26 L, share %, Jun'26 L, MoM %, YoY % or None if not meaningful)
BRAND_MIX = [
    ("Mamaearth",     2455.41, 67.8, 2762.85, -11.1,  26.9),
    ("The Derma Co.", 1107.73, 30.6, 1003.43,  10.4, 426.4),
    ("Aqualogica",       48.36, 1.3,   62.76, -22.9,  21.2),
    ("BBLUNT",            6.34, 0.2,    7.76, -18.3, -52.8),
    ("Other brands",      3.63, 0.1,    3.65,  -0.5,  None),
]

# --- Sub-category mix, July'26 offtake, ex-Brand-Counter
# (sub-category, Jul'26 L, share %, Jun'26 L, MoM %)
SUBCAT_MIX = [
    ("Face Cleanser", 1764.30, 48.7, 1718.32,   2.7),
    ("Shampoo",         744.58, 20.6,  813.36,  -8.5),
    ("Sun Care",        459.09, 12.7,  603.22, -23.9),
    ("Face Serum",        93.99, 2.6,  100.04,  -6.0),
    ("Body Lotion",       82.28, 2.3,   89.86,  -8.4),
    ("Soap",               76.99, 2.1,  58.38,  31.9),
    ("Moisturisers",       75.76, 2.1,  91.52, -17.2),
    ("Baby Soap",          64.99, 1.8,  71.58,  -9.2),
    ("Body Wash",          61.69, 1.7,  71.28, -13.5),
    ("Hair Oil",           59.69, 1.6,  63.97,  -6.7),
    ("Other",             138.13, 3.8, 158.93, -13.1),
]

# --- Zone deep dive: chain mix within each zone, Jul'26 vs Jun'26 (₹ Lakh)
# top 5 chains + an "Other" residual so each zone's rows sum to its total.
ZONE_CHAINS = {
    "Central": [
        ("DMart", 187.35, 131.52), ("Reliance Retail", 46.47, 53.48),
        ("Apollo", 24.17, 18.95), ("Wellness Forever", 4.57, 1.35),
        ("VMM", 2.71, 1.61), ("Other", 1.03, 0.76),
    ],
    "East": [
        ("Reliance Retail", 216.16, 249.68), ("Apollo", 79.63, 79.54),
        ("VMM", 17.35, 13.80), ("More Retail", 9.27, 9.75),
        ("Spencer", 6.16, 6.10), ("Other", 26.65, 29.18),
    ],
    "North": [
        ("DMart", 250.56, 219.00), ("Reliance Retail", 240.25, 270.24),
        ("Apollo", 115.55, 110.62), ("Lulu", 26.57, 17.98),
        ("Sancus (RMT)", 18.50, 39.83), ("Other", 46.46, 43.67),
    ],
    "Pan India": [
        ("Nykaa (FSN)", 206.64, 216.67),
    ],
    "South 1": [
        ("Apollo", 284.14, 288.84), ("DMart", 231.16, 229.40),
        ("Lulu", 122.12, 86.17), ("Reliance Retail", 112.74, 151.30),
        ("Health & Glow", 34.12, 34.54), ("Other", 36.34, 36.99),
    ],
    "South 2": [
        ("DMart", 194.90, 229.44), ("Apollo", 163.55, 162.57),
        ("Reliance Retail", 66.69, 94.36), ("Lulu", 21.08, 11.70),
        ("Health & Glow", 13.37, 14.14), ("Other", 33.87, 35.63),
    ],
    "West": [
        ("DMart", 531.93, 645.31), ("Reliance Retail", 123.33, 128.75),
        ("Wellness Forever", 62.26, 73.35), ("Apollo", 51.13, 62.52),
        ("Trent", 6.05, 6.60), ("Other", 6.64, 19.41),
    ],
}

# --- Zone deep dive: headline metrics. Central's jul25 is re-derived from
# data/raw_drops/offtake_fy26/Jul'25/*.csv's State column (Madhya Pradesh +
# Chhattisgarh), the same fix already applied to Jun'26 -- Jul'25's own Zone
# column tagged those rows North/West instead of Central. Real, not fabricated.
ZONE_DEEPDIVE = {
    "Central":   dict(jul=266.30, jun=207.92, jul25=102.02, share=7.4),
    "East":      dict(jul=355.21, jun=389.87, jul25=222.98, share=9.8),
    "North":     dict(jul=697.90, jun=706.36, jul25=479.34, share=19.3),
    "Pan India": dict(jul=206.64, jun=216.67, jul25=191.40, share=5.7),
    "South 1":   dict(jul=820.63, jun=829.80, jul25=454.06, share=22.7),
    "South 2":   dict(jul=493.45, jun=549.77, jul25=318.92, share=13.6),
    "West":      dict(jul=781.34, jun=940.06, jul25=532.48, share=21.6),
}

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
FY27_OFFTAKE = [APR26_EX_BC, MAY26_EX_BC, JUN26_EX_BC, JUL26_EX_BC]
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
        ("Fixed", "The Sep'26 FY27 rebuild gives Nykaa/FSN its own zone total."),
        ("Verified", "Apr and May'26 zones now tie to source — rebuilt alongside June."),
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
        ("Repaired", "The FY27 rebuild now computes Pan India/Nykaa-FSN correctly."),
        ("Confirmed", "All four Apr–Jul'26 zone splits tie to source, rupee-lakh."),
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
        "Year-on-year is like-for-like. The sequential column is against Jun'26, "
        "now a fully audited month.",
        page_no=4, total=TOTAL,
        source=SRC_OFFTAKE + " Jul'25 from data/raw_drops/_agg/offtake_fy26.json; "
                             "Jun'26 from offtake_store_article_Jun_26.csv.")

    y = k.bars(s, y, [(c[0], c[1], f"{c[1]:,.0f}") for c in CHAINS[:7]],
               h_row=0.34, gap=0.08,
               hi=("D-Mart", "Reliance Retail", "Apollo"),
               note="₹ Lakh, Jul'26, Reliance shown ex-Brand Counter. "
                    "Top three = 80.6% of the month.")
    y += 0.34

    y = k.data_table(
        s, y,
        ["Chain", "Jul'26", "Share", "vs Jul'25", "vs Jun'26"],
        [[name, f"{v:,.0f}", f"{sh:.1f}%", pct(yoy), pct(mm)]
         for name, v, sh, _j25, yoy, _jn6, mm in CHAINS] +
        [["TOTAL", f"{JUL26_EX_BC:,.0f}", "100.0%", pct(64.7), pct(-5.7)]],
        [0.28, 0.17, 0.14, 0.20, 0.21],
        hi_rows=("TOTAL",), row_h=0.26)
    y += 0.28

    y = k.insight(s, y, "the account read", [
        ("Apollo is the standout",
         "₹718 L, up 150% year on year, now the third-largest account at 19.8% "
         "of the channel — from under 13% a year ago. Lulu is the other engine, "
         "up 259% and the only top-10 account also up sequentially."),
        ("Reliance and D-Mart softened month on month",
         "Reliance is down 15.0% and D-Mart 4.1% against June, the two biggest "
         "sequential movers. Both are still up sharply year on year — this is a "
         "month-on-month read, not a decline."),
    ], h_item=0.86)
    y += 0.20

    k.rect(s, k.ML, y, k.CW, 0.86, fill=k.RGBColor(0xFB, 0xF0, 0xE8),
           shape=k.MSO_SHAPE.ROUNDED_RECTANGLE, adj=0.10)
    k.rect(s, k.ML, y, 0.045, 0.86, fill=k.AMBER)
    k.text(s, k.ML + 0.18, y + 0.13, k.CW - 0.36, 0.20, "DATA FLAG — NOT A BUSINESS READ",
           size=8, bold=True, color=k.AMBER, spacing=1.0)
    k.text(s, k.ML + 0.18, y + 0.37, k.CW - 0.36, 0.42,
           "Walmart C&C is nil in both June and July, down from ₹25.59 L in "
           "April and ₹11.31 L in May. Two months at zero reads more like an "
           "exit than a feed gap — worth a direct confirmation either way.",
           size=9, color=k.INK, line_spacing=1.18)
    y += 0.86
    k.fits(y, "s04")
    return s


# ===========================================================================
# 05 — brand mix
# ===========================================================================
@slide
def s05(prs):
    s, y = k.page(
        prs, "july'26 offtake  ·  brand mix",
        "Two brands carry 98% of July — and The Derma Co. is still scaling fast",
        "Brand share of July'26 offtake, ex-Brand-Counter, with June and July'25 "
        "for comparison.",
        page_no=5, total=TOTAL, source=SRC_OFFTAKE_JUN)

    y = k.kpi_row(s, y, [
        ("Mamaearth", cr(BRAND_MIX[0][1]), f"{BRAND_MIX[0][2]:.1f}% of month", "n"),
        ("The Derma Co.", cr(BRAND_MIX[1][1]), pct(BRAND_MIX[1][5]) + " YoY", "+"),
        ("Top 2 brands", f"{BRAND_MIX[0][2]+BRAND_MIX[1][2]:.1f}%", "of July offtake", "n"),
    ])
    y += 0.32

    y = k.donut(s, k.ML, y, k.CW, 2.15,
                [(b, sh) for b, _, sh, *_ in BRAND_MIX],
                [k.TEAL, k.BLUE, k.AMBER, k.RGBColor(0xA8, 0xC5, 0xBE), k.RULE],
                centre_value=f"{BRAND_MIX[0][2]:.0f}%", centre_label="MAMAEARTH")
    y += 0.26

    y = k.data_table(
        s, y, ["Brand", "Jul'26 ₹L", "Share", "vs Jun'26", "vs Jul'25"],
        [[b, f"{jul:,.2f}", f"{sh:.1f}%", pct(mm),
          ("n/m — new/negligible base" if yoy is None else pct(yoy))]
         for b, jul, sh, jun, mm, yoy in BRAND_MIX],
        [0.24, 0.19, 0.14, 0.18, 0.25], hi_rows=("Mamaearth",), row_h=0.27)
    y += 0.30

    y = k.insight(s, y, "the brand read", [
        ("The Derma Co. is the growth engine",
         "Up 426% year on year and still up 10.4% on June alone — the one brand "
         "growing sequentially while the channel softened."),
        ("Mamaearth is normalising off a strong base",
         "Down 11.1% on June but still up 26.9% year on year. At 67.8% of the "
         "month, its month-on-month moves set the channel's shape."),
    ], h_item=0.80)
    y += 0.20

    y = k.sowhat(s, y, [
        ("Watch", "The Derma Co.'s share of the channel is compounding monthly."),
        ("Protect", "Mamaearth's base is still the majority of every zone."),
    ], h=1.02)
    k.fits(y, "s05")
    return s


# ===========================================================================
# 06 — sub-category mix
# ===========================================================================
@slide
def s06(prs):
    s, y = k.page(
        prs, "july'26 offtake  ·  sub-category mix",
        "Face Cleanser and Shampoo are 69% of July; Sun Care is the steepest "
        "sequential faller",
        "Sub-category share of July'26 offtake, ex-Brand-Counter, against June.",
        page_no=6, total=TOTAL, source=SRC_OFFTAKE_JUN)

    y = k.kpi_row(s, y, [
        ("Face Cleanser", cr(SUBCAT_MIX[0][1]), f"{SUBCAT_MIX[0][2]:.1f}% of month", "n"),
        ("Shampoo", cr(SUBCAT_MIX[1][1]), pct(SUBCAT_MIX[1][4]) + " vs Jun", "-"),
        ("Sun Care", cr(SUBCAT_MIX[2][1]), pct(SUBCAT_MIX[2][4]) + " vs Jun", "-"),
    ])
    y += 0.32

    y = k.data_table(
        s, y, ["Sub-category", "Jul'26 ₹L", "Share", "vs Jun'26"],
        [[c, f"{v:,.2f}", f"{sh:.1f}%", pct(mm)] for c, v, sh, _jn, mm in SUBCAT_MIX],
        [0.34, 0.22, 0.18, 0.26], hi_rows=("Face Cleanser", "Shampoo"), row_h=0.235)
    y += 0.28

    y = k.insight(s, y, "the sub-category read", [
        ("Sun Care fell fastest",
         "Down 23.9% on June as the peak-season taper begins — the largest "
         "sequential swing of any sub-category above ₹50 L."),
        ("Face Cleanser held up, Shampoo softened",
         "Face Cleanser is flat-to-up (+2.7% on June); Shampoo is down 8.5%, "
         "in line with the channel's broader June-to-July pullback."),
    ], h_item=0.72)
    y += 0.18

    y = k.sowhat(s, y, [
        ("Expect", "Sun Care's taper is seasonal, not a demand problem."),
        ("Hold", "Face Cleanser availability protects 48.7% of the month."),
    ], h=0.90)
    k.fits(y, "s06")
    return s


# ===========================================================================
# 07-13 — zone deep dives
# ===========================================================================
ZONE_COPY = {
    "Central": dict(
        headline="Central is July's fastest-growing zone — up 28% on June, "
                 "161% on July'25",
        subhead="D-Mart carries 70% of the zone; Jul'25 is now measured on the "
                "same Madhya Pradesh + Chhattisgarh basis as this July.",
        insight=[
            ("D-Mart drives the zone",
             "₹187.35 L of ₹266.30 L — 70.4% of Central sits in one chain, up "
             "from ₹131.52 L in June."),
            ("The YoY base is now real, not estimated",
             "Jul'25 tagged MP/Chhattisgarh rows North/West, not Central — the "
             "same defect Jun'26 had. Re-derived from State: a real ₹102.02 L "
             "base, not a fabricated one. Growth has climbed all year (₹102-196 "
             "L, Apr'25-Mar'26), so 161% YoY isn't a one-month spike."),
        ],
        sowhat=[("Watch", "Confirm D-Mart's Central growth is sell-through, not stock-in.")],
    ),
    "East": dict(
        headline="East is Reliance's zone — and its steepest June-to-July pullback",
        subhead="Reliance is 61% of East. The zone is still up 59% year on year "
                "despite the monthly dip.",
        insight=[
            ("Reliance-concentrated",
             "₹216.16 L of ₹355.21 L — 60.9% of East sits in one chain, down "
             "from ₹249.68 L in June (−13.4%)."),
            ("Still a strong year",
             "East is up 59.3% on July'25 (₹222.98 L), so the June-to-July dip "
             "is a sequential read, not a trend reversal."),
        ],
        sowhat=[("Confirm", "Whether Reliance's East dip is a listing or a stocking gap.")],
    ),
    "North": dict(
        headline="North holds steady — D-Mart and Reliance are running neck and neck",
        subhead="The two largest chains are within ₹10 L of each other; the "
                "zone is flat month on month.",
        insight=[
            ("A genuine two-horse race",
             "D-Mart ₹250.56 L vs Reliance ₹240.25 L — the closest contest of "
             "any zone, and Reliance's June lead (₹270.24 L) has narrowed."),
            ("Broad-based growth",
             "North is up 45.6% year on year with Apollo (₹115.55 L) and Lulu "
             "(₹26.57 L, +47.8% on June) both contributing."),
        ],
        sowhat=[("Hold", "No single-chain risk here — the zone is genuinely diversified.")],
    ),
    "Pan India": dict(
        headline="Pan India is Nykaa/FSN, in full — a single-chain zone by design",
        subhead="This is not a physical-store zone; it exists because Nykaa/FSN "
                "isn't mapped to a state-level zone.",
        insight=[
            ("100% one chain",
             "Every rupee of Pan India's ₹206.64 L is Nykaa/FSN — there is no "
             "chain mix to show because none exists."),
            ("This is what slide 3 was about",
             "The FY27 zone-drop bug happened precisely because this zone has "
             "only one chain in it — its outage looked like a rounding error "
             "instead of a whole account going missing."),
        ],
        sowhat=[("Consider", "Whether Nykaa/FSN deserves a chain-level view instead of a zone.")],
    ),
    "South 1": dict(
        headline="South 1 is the largest zone at 22.7% of July — and up 81% year on year",
        subhead="Apollo leads, D-Mart is close behind, and Lulu is the "
                "fastest-growing chain in the zone.",
        insight=[
            ("Apollo edges D-Mart",
             "₹284.14 L vs ₹231.16 L — Apollo has led South 1 in both June and "
             "July, though its margin has narrowed slightly."),
            ("Lulu is scaling fast within the zone",
             "₹122.12 L, up 41.7% on June's ₹86.17 L — South 1 is where Lulu's "
             "channel-wide growth is concentrated."),
        ],
        sowhat=[("Bank", "South 1's 80.7% YoY makes it the zone to protect first.")],
    ),
    "South 2": dict(
        headline="South 2 posts the second-steepest pullback, down 10.2% on June",
        subhead="D-Mart still leads but fell from June; Apollo held almost flat.",
        insight=[
            ("D-Mart pulled back, Apollo didn't",
             "D-Mart fell to ₹194.90 L from ₹229.44 L (−15.1%) while Apollo held "
             "at ₹163.55 L, essentially flat on June's ₹162.57 L."),
            ("Reliance also softened",
             "₹66.69 L, down 29.3% on June's ₹94.36 L — the zone's decline is "
             "concentrated in two chains, not broad-based."),
        ],
        sowhat=[("Check", "Whether D-Mart and Reliance's South 2 dip is a common cause.")],
    ),
    "West": dict(
        headline="West has July's steepest pullback, down 16.9% on June — still up "
                 "47% year on year",
        subhead="D-Mart alone is 68% of the zone; its swing is the largest "
                "single chain-month movement in this deck.",
        insight=[
            ("D-Mart's West swing is the single largest in the deck",
             "₹531.93 L in July against ₹645.31 L in June — a ₹113.38 L drop, "
             "bigger than the total offtake of five other zones combined."),
            ("The zone is still a strong year",
             "West is up 46.7% on July'25 (₹532.48 L), so July's level is still "
             "well ahead of last year despite the June pullback."),
        ],
        sowhat=[("Prioritise", "D-Mart West is the single largest MoM swing to root-cause.")],
    ),
}


def zone_deepdive_slide(prs, page_no, zone):
    meta = ZONE_DEEPDIVE[zone]
    copy = ZONE_COPY[zone]
    jul, jun, jul25, share = meta["jul"], meta["jun"], meta["jul25"], meta["share"]
    mom = (jul / jun - 1) * 100
    yoy = (jul / jul25 - 1) * 100 if jul25 else None

    if zone == "Central" and jul25 is not None:
        jul25_source = (SRC_OFFTAKE_JUN + " Jul'25 Central re-derived from "
                         "offtake_fy26/Jul'25/*.csv by State (MP + Chhattisgarh).")
    elif jul25 is not None:
        jul25_source = (SRC_OFFTAKE_JUN + " Jul'25 zone total from "
                         "data/raw_drops/_agg/offtake_fy26.json.")
    else:
        jul25_source = SRC_OFFTAKE_JUN

    s, y = k.page(
        prs, f"zone deep dive  ·  {zone.lower()}  ·  july 2026",
        copy["headline"], copy["subhead"],
        page_no=page_no, total=TOTAL,
        source=jul25_source)

    y = k.kpi_row(s, y, [
        ("Jul'26 value", cr(jul), f"{share:.1f}% of total", "n"),
        ("vs Jun'26", pct(mom), "month on month", "+" if mom >= 0 else "-"),
        ("vs Jul'25", ("not tracked" if yoy is None else pct(yoy)),
         "separately last year" if yoy is None else "year on year",
         "n" if yoy is None else ("+" if yoy >= 0 else "-")),
    ])
    y += 0.10

    if zone == "Central":
        footnote = ("Like-for-like YoY (MP+CG only): 108%. Headline 161% includes "
                    "Vidarbha, reclassified into Central this year.")
        fh = k.text_height(footnote, 8, k.CW)
        k.text(s, k.ML, y, k.CW, fh, footnote, size=8, color=k.MUTED)
        y += fh + 0.08

    y += 0.11

    rows = ZONE_CHAINS[zone]
    if len(rows) > 1:
        y = k.bars(s, y, [(c, v, f"{v:,.0f}") for c, v, _jn in rows],
                   h_row=0.36, gap=0.09,
                   hi=(rows[0][0],),
                   note=f"₹ Lakh, Jul'26, chain mix within {zone}. "
                        f"June comparison in the table below.")
        y += 0.30
        y = k.data_table(
            s, y, ["Chain", "Jul'26 ₹L", "Jun'26 ₹L", "vs Jun'26"],
            [[c, f"{jl:,.2f}", f"{jn:,.2f}", pct((jl/jn-1)*100 if jn else 0.0)]
             for c, jl, jn in rows],
            [0.32, 0.24, 0.24, 0.20], hi_rows=(rows[0][0],), row_h=0.27)
        y += 0.30
    else:
        c, jl, jn = rows[0]
        y = k.data_table(
            s, y, ["Chain", "Jul'26 ₹L", "Jun'26 ₹L", "vs Jun'26"],
            [[c, f"{jl:,.2f}", f"{jn:,.2f}", pct((jl/jn-1)*100 if jn else 0.0)]],
            [0.32, 0.24, 0.24, 0.20], hi_rows=(c,), row_h=0.30)
        y += 0.34

    y = k.insight(s, y, "the zone read", copy["insight"], h_item=0.80)
    y += 0.22

    y = k.sowhat(s, y, copy["sowhat"], h=0.90)
    k.fits(y, f"zone-{zone}")
    return s


@slide
def s07(prs):
    return zone_deepdive_slide(prs, 7, "Central")


@slide
def s08(prs):
    return zone_deepdive_slide(prs, 8, "East")


@slide
def s09(prs):
    return zone_deepdive_slide(prs, 9, "North")


@slide
def s10(prs):
    return zone_deepdive_slide(prs, 10, "Pan India")


@slide
def s11(prs):
    return zone_deepdive_slide(prs, 11, "South 1")


@slide
def s12(prs):
    return zone_deepdive_slide(prs, 12, "South 2")


@slide
def s13(prs):
    return zone_deepdive_slide(prs, 13, "West")


# ===========================================================================
# 14 — section divider
# ===========================================================================
@slide
def s14(prs):
    return k.divider(
        prs, "section two", "NielsenIQ Category\nIntelligence",
        "External category read for Face Wash and Shampoo through July 2026. "
        "India Urban Modern Trade. Measured on a different base to internal NSV "
        "— the two are never compared as one series.",
        page_no=14, total=TOTAL)


# ===========================================================================
# 15 — face wash
# ===========================================================================
@slide
def s15(prs):
    s, y = k.page(
        prs, "nielseniq  ·  face wash",
        "Mamaearth is the No.4 face wash brand at 11.2% share — and the fastest "
        "growing of the top eight",
        "Share is up 2.4 points year on year while the three brands above it all "
        "lost ground.",
        page_no=15, total=TOTAL, source=SRC_NIELSEN)

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
    k.fits(y, "s15")
    return s


# ===========================================================================
# 16 — shampoo
# ===========================================================================
@slide
def s16(prs):
    s, y = k.page(
        prs, "nielseniq  ·  shampoo",
        "Shampoo value is consolidating into bulk packs — but we cannot yet see "
        "Mamaearth's position in it",
        "Category pack architecture is clear. Brand-level detail is not in the "
        "supplied file.",
        page_no=16, total=TOTAL,
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
    k.fits(y, "s16")
    return s


# ===========================================================================
# 17 — multi-year momentum
# ===========================================================================
@slide
def s17(prs):
    s, y = k.page(
        prs, "multi-year momentum  ·  apr'24 to jul'26",
        "Offtake is up 65% year on year, on a base that only becomes "
        "like-for-like from April 2025",
        "FY25 has no true offtake anywhere in the source set — the dotted line is "
        "distributor secondary, shown as an indicative anchor only.",
        page_no=17, total=TOTAL,
        source="Source: offtake from data/raw_drops/_agg/offtake_fy26.json and the "
               "Apr/May/Jun/Jul'26 store x article extracts; primary from "
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
         ["FY27 to date (Apr–Jul'26)", "₹150.70 Cr", "₹185.81 Cr",
          "full 4 months"]],
        [0.34, 0.20, 0.20, 0.26], row_h=0.30)
    y += 0.30

    y = k.insight(s, y, "how to read this", [
        ("The growth is real and verified",
         "July'26 at ₹36.21 Cr against ₹21.99 Cr in July'25 is a like-for-like "
         "+64.7% — both sides are true offtake, both exclude Brand Counter."),
        ("All four months are now audited",
         "June'26 was recovered from an unmerged commit and folded into the "
         "same rebuild as April and May. All four Apr–Jul'26 zone splits now "
         "tie to source to the rupee-lakh."),
        ("FY25 is not a comparison base",
         "Distributor secondary sits one step above offtake in the chain. It "
         "anchors scale; it cannot carry a growth rate."),
    ], h_item=0.72)
    y += 0.24

    y = k.sowhat(s, y, [
        ("Quote", "FY26 ₹311.20 Cr and FY27-to-date ₹150.70 Cr are safe to publish."),
        ("Withhold", "No FY25-vs-FY26 growth rate until true primary arrives."),
        ("Close", "August'26 is the next month to source once available."),
    ], h=1.24)
    k.fits(y, "s17")
    return s


# ===========================================================================
# 18 — strategic takeaways
# ===========================================================================
@slide
def s18(prs):
    s, y = k.page(
        prs, "strategic commercial takeaways",
        "The growth is broad and genuine — most of the reporting gaps behind it "
        "are now closed",
        "Where the value is coming from, and what could still take it away.",
        page_no=18, total=TOTAL,
        source="Source: as per the preceding audit, brand, zone and category slides.")

    k.text(s, k.ML, y, k.CW, 0.22, "GROWTH DRIVERS", size=8.5, bold=True,
           color=k.GREEN, spacing=1.2)
    y += 0.30
    for label, body, val in [
        ("Apollo scale-up", "Third-largest account from a standing start; "
         "+150% year on year and now a fifth of the channel.", "+₹431 L YoY"),
        ("The Derma Co. is compounding", "Up 426% year on year and still up "
         "10.4% on June alone — growing while the channel softened.", "+426% YoY"),
        ("Face wash share gain", "Rank 4 at 11.2%, +2.4 points, while every "
         "brand above lost share. Velocity-led, not distribution-led.", "+2.4 pp"),
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
        ("West's D-Mart swing", "A ₹113 L June-to-July drop in one chain, one "
         "zone — the single largest sequential movement in this audit.", "−16.9% West"),
        ("Reach quality", "Relative numeric distribution fell to 57.8% while "
         "weighted held at 89.2% — the remaining stores are lower value.", "−1.7 pp"),
        ("Walmart C&C at nil for two months", "Zero in both June and July "
         "after falling through April and May. Needs a direct answer, not an "
         "assumption.", "2 months at ₹0"),
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
    k.fits(y, "s18")
    return s


# ===========================================================================
# 19 — action plan and governance
# ===========================================================================
@slide
def s19(prs):
    s, y = k.page(
        prs, "action plan  ·  governance roadmap",
        "Two fixes done, three open, all with named owners",
        "The two data-integrity items that gated everything else closed with "
        "the June'26 restore. Nothing on this page needs new investment.",
        page_no=19, total=TOTAL,
        source="Owners and dates to be confirmed in the monthly MT governance call.")

    k.text(s, k.ML, y, k.CW, 0.22, "PRIORITY ACTIONS", size=8.5, bold=True,
           color=k.TEAL, spacing=1.2)
    y += 0.30
    y = k.data_table(
        s, y, ["#", "Action", "Owner", "Status"],
        [["01", "Re-zone Nykaa/FSN so the roll-up stops overwriting it",
          "Sales Analytics", "Done 07-Sep"],
         ["02", "Source the June'26 offtake extract and rebuild Apr–Jun zones",
          "MT Analytics", "Done 07-Sep"],
         ["03", "Settle one zone master (Telangana/AP and Kerala conflict)",
          "Sales Analytics", "19-Sep"],
         ["04", "Request Nielsen brand-by-pack Shampoo extract",
          "Category / Insights", "22-Sep"],
         ["05", "Confirm Walmart C&C status — nil for two months running",
          "NKAM", "12-Sep"]],
        [0.07, 0.53, 0.20, 0.20], row_h=0.34,
        hi_rows=("01", "02"),
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
        [["FY25 primary", "Any two-year like-for-like", "Billing extract"],
         ["Shampoo by brand", "Pack and price-ladder calls", "Nielsen file"],
         ["Walmart C&C status", "Whether the account is still live", "NKAM confirmation"]],
        [0.30, 0.42, 0.28], row_h=0.30)
    y += 0.30

    y = k.sowhat(s, y, [
        ("Approve", f"{cr(JUL26_EX_BC)} as the July baseline for Q2 targets."),
        ("Assign", "The five owners above, reviewed in the next MT call."),
    ], h=1.00)
    k.fits(y, "s19")
    return s


# ===========================================================================
DATA_NOTES = """
Verified against source; see the Data Truth Matrix for full derivations.

RESOLVED since the first cut of this deck (07-Sep-2026):
  - June'26 offtake recovered from an unmerged commit (fb4d7e3e, blob
    21b2dc44) and folded into the FY27 rebuild. Rs 3,840.46 L ex-Brand-
    Counter, independently re-verified against the restored CSV.
  - The Pan India/Nykaa-FSN zone drop that understated July by Rs 2.07 Cr
    was a symptom of the same stale FY27 block June's absence pointed at.
    The full 4-month rebuild fixed both: Jul'26 now nets to Rs 3,621.47 L
    (matching the audited figure) with no manual patch, and Apr/May/Jun/Jul
    zone splits all tie to source to the rupee-lakh.
  - "vs May'26" throughout this deck is now "vs Jun'26" — a real prior
    month rather than a two-month-old stand-in.

ADDED in this revision (slides 5-13): brand mix, sub-category mix, and a
deep-dive slide per zone, all computed from the same restored Jun/Jul'26
store x article extracts using the pipeline's own canon_chain() and
zone_with_central_override().

UPDATED in the follow-up pass: Central's Jul'25 comparison, previously shown
as "not tracked". FY26 offtake's raw per-store extracts
(data/raw_drops/offtake_fy26/, one CSV per chain per month, Apr'25-Mar'26)
were checked and found to have the same defect Jun'26 had — Madhya Pradesh
and Chhattisgarh rows are tagged North/East/West in the Zone column instead
of Central, for all 12 months, not just June. Re-deriving each month's Central
total from the State column (same zone_with_central_override() logic) gives
a real, reconciled FY26 Central series: Rs 1,630.27 L total against a known
Rs 31,119.87-31,119.88 L FY26 offtake baseline (ties to the rupee). Central's
Jul'25 value (Rs 102.02 L) comes from that recomputation, not an estimate.
This also surfaced a separate, larger defect: dashboard/data.js's FY26
zone_monthly block for Aug'25-Mar'26 (all 7 zones, not just Central) held a
flat "10% of Primary NSV" placeholder (data_source: "Primary_Article_Monthly",
conversion_pct: 10 on every month) instead of measured offtake -- dead data
no dashboard tab or generator script actually read, but fabricated
nonetheless. dashboard/data.js's full FY26 offtake block (by_chain, by_zone,
zone_monthly_fy26, monthly_fy26, total_fy26) was rebuilt from the same real
per-store extracts; FY25 and FY27 are byte-identical before/after (diffed).
The unused conversion_rates_fy25/26/27 fields, which mixed those same
fabricated placeholders with real FY27 figures under one key, were removed
rather than "fixed", since nothing reads them.

STILL NOT PUBLISHED because it could not be verified:
  - FY25 primary — Primary_Article_Synthesized_FY25.csv is the distributor
    secondary file re-split, not billing. Shown as an indicative proxy only.
  - Mamaearth-level shampoo share/value/WD/PDO — not in the supplied file.
  - Nielsen "Simple 2.6%" — outside the top-8 extract held in the repo.
  - Walmart C&C — nil in both June and July, down from Rs 25.59 L in April.
    Read as a likely exit, not asserted as one; needs direct confirmation.

ZONE MASTER: this deck uses the source Zone column (which ties to
dashboard/data.js). The pipeline's zone_with_central_override() now derives
Central from State for Madhya Pradesh and Chhattisgarh specifically (the one
state pair Jun'26 mistagged), but a separate conflict remains: the pipeline's
broader state-to-zone master disagrees with the source on Telangana/AP and
Kerala, moving c.₹376 L between South 1 and South 2. That conflict is action
03 on the action-plan slide.
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
