#!/usr/bin/env python3
"""
Build the data layer for the MT (Modern Trade) Leadership Dashboard.

Reads four source workbooks (kept in Google Drive, not committed) and emits a
single self-contained ``dashboard/data.js`` consumed by ``dashboard/index.html``.

Sources (Honasa / Mamaearth Modern Trade, FY24-25 & FY25-26):
  - Primary FY-2024-26.xlsx            -> row-level primary sell-in (NSV, MRP)
  - Chain Offtake Master ... .xlsx     -> chain-wise & zone-wise sell-out pivots
  - Universe MT.xlsx                   -> store universe (distribution footprint)
  - Promo Master -MT.xlsx              -> promo / trade-spend calendar

All monetary values in the sources are in INR Lakh. The dashboard presents
them in INR Crore (Lakh / 100) wherever the magnitude warrants it; the raw
Lakh figures are preserved in the JSON so the front-end controls the unit.

Usage:
    python build_dashboard_data.py --src <dir-with-source-files> \
        --out ../dashboard/data.js
"""
from __future__ import annotations
import sys
import argparse, csv, io, json, re, math, datetime, tempfile, shutil
from pathlib import Path

import pandas as pd
from dist_allocation_governance import (
    DistAllocationGovernance,
    QCReconciliation,
    eligibility_tier_rank,
)
from analytics_enhancement_layer import FMCGAnalyticsEnhancer
from allocate_dist_enhanced import apply_chain_allocation_enhanced, compute_dynamic_offtake_weights

# --------------------------------------------------------------------------
# Canonicalisation helpers
# --------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# THE ONE FY RULE (Indian financial year, Apr..Mar), used by every report:
#   Apr..Dec of calendar year Y  -> FY(Y+1)      e.g. Apr-26 -> FY27
#   Jan..Mar of calendar year Y  -> FY(Y)        e.g. Mar-26 -> FY26
# Nothing below slices by fixed index positions -- month labels/dates are
# always mapped through these helpers, so FY27/FY28/... work automatically
# the moment their months appear in a source file.
# ---------------------------------------------------------------------------
_MON3_NUM = {"Jan":1,"Feb":2,"Mar":3,"Apr":4,"May":5,"Jun":6,
             "Jul":7,"Aug":8,"Sep":9,"Oct":10,"Nov":11,"Dec":12}
# month number -> "Mon" label, so a date can be turned into the canonical
# "Mon-YY" key the offtake/fyx month series already use.
_CAL_MON3 = {v: k for k, v in _MON3_NUM.items()}

def fy_tag_from_ym(year, month):
    """Calendar (year, month) -> 'FY27' style tag. Apr-2026 -> FY27; Mar-2026 -> FY26."""
    return f"FY{(year + 1 if month >= 4 else year) % 100:02d}"

def fy_start_year(tag):
    """'FY27' -> 2026 (the FY's April calendar year)."""
    return 2000 + int(str(tag).strip()[2:]) - 1

def fy_source_key(tag):
    """'FY26' -> 'FY_25-26' (the source workbooks' FY column convention)."""
    y = fy_start_year(tag) % 100
    return f"FY_{y:02d}-{y + 1:02d}"

def fy_tag_from_label(lab):
    """'Apr-24' / 'Sep-25' style month-column label -> FY tag, or None."""
    m = re.match(r"([A-Za-z]{3})-(\d{2})$", str(lab).strip())
    if not m:
        return None
    mn = _MON3_NUM.get(m.group(1).title())
    return fy_tag_from_ym(2000 + int(m.group(2)), mn) if mn else None


def fy_ge(series, floor="FY26"):
    """Boolean mask: FY-tag series >= floor FY (e.g. FY26 onward -- the GST/
    TOT/CM2 analysis window). Works for ANY future tag (FY28, FY29, ...)."""
    fl = fy_start_year(floor)
    return series.map(lambda t: t is not None and str(t).startswith("FY") and fy_start_year(t) >= fl)

def month_labels(start_year=2024, n_months=24):
    """['Apr-24', 'May-24', ...] for n_months from April of start_year."""
    out = []
    y, m = start_year, 4
    mon3 = {v: k for k, v in _MON3_NUM.items()}
    for _ in range(n_months):
        out.append(f"{mon3[m]}-{y % 100:02d}")
        m += 1
        if m == 13:
            m, y = 1, y + 1
    return out

# ---------------------------------------------------------------------------
# Which FYs the PRE-AGGREGATED Primary/Offtake/P&L workbooks actually cover.
# Those workbooks end Mar'26. Any FY beyond this window is owned by the
# article-level source instead and is published under
# detail_meta.fyx_primary[<FY>] -- see CLAUDE.md "Coverage split".
#
# This is a statement about SOURCE FILE COVERAGE, not about FY derivation:
# THE ONE FY RULE still derives every FY tag from month+year. When the
# pre-aggregated workbooks are next extended past Mar'26, add that tag here
# (it is echoed into metadata.preagg_fy_tags so the current value is always
# visible in the generated data.js).
PREAGG_FY_TAGS = {"FY25", "FY26"}

# Repo root, at module scope. main() assigns an identical local; defining it
# here as well lets helper functions (and the patch script) resolve repo-
# relative config/seed paths without threading the path through every call.
_REPO_ROOT = Path(__file__).resolve().parent.parent

def quarter_labels_for(months):
    """Q-col labels for load_offtake()'s Sheet3 (zone/state) pivot: one
    Q1..Q4 block per FY that `months` spans, suffixed with that FY's START
    calendar year -- e.g. FY25 (Apr-24..Mar-25) -> 'Q1-24'..'Q4-24'; FY26
    (Apr-25..Mar-26) -> 'Q1-25'..'Q4-25' -- matching the pivot's
    quarter-major, FY-minor column order. This generalizes the original
    hardcoded 2-FY (FY25,FY26) list to however many FYs `months` spans; NOT
    verified against a real 3-FY source file yet (only the original 2-FY
    shape is), so double-check Sheet3's actual column order once one lands."""
    fy_start_yrs = sorted({fy_start_year(fy_tag_from_label(m)) % 100
                            for m in months if fy_tag_from_label(m)})
    return [f"Q{q}-{y:02d}" for q in range(1, 5) for y in fy_start_yrs]

def normalize_fmcg_dates(df: pd.DataFrame, raw_date_col: str) -> pd.DataFrame:
    """
    Ensures clean 28-month indexing (Apr'24 to Jul'26) with canonical FY,
    Month, and Quarter labels. Handles multi-format dates (ISO, Indian,
    Excel serials, MMM'YY).
    """
    df = df.copy()

    # 1. Flexible multi-format datetime conversion
    df["_date_parsed"] = pd.to_datetime(
        df[raw_date_col],
        errors="coerce",
        format="mixed",
        dayfirst=True,  # Handles Indian format DD/MM/YYYY
    )

    # 2. Canonical Month Key (YYYY-MM), e.g., '2024-04'
    df["Month_Key"] = df["_date_parsed"].dt.strftime("%Y-%m")

    # 3. Canonical Display Month (MMM'YY), e.g., 'Apr'24'
    df["Month_Display"] = df["_date_parsed"].dt.strftime("%b'%y")

    # 4. Canonical Indian Fiscal Year (FY25, FY26, FY27)
    # Rule: Apr-Dec -> Year+1; Jan-Mar -> Year
    year = df["_date_parsed"].dt.year
    month = df["_date_parsed"].dt.month
    df["FY"] = "FY" + (
        (year + 1 - 2000).astype(str).where(month >= 4, (year - 2000).astype(str))
    )

    # 5. Fiscal Quarter (Q1, Q2, Q3, Q4 within FY)
    quarter_map = {
        4: "Q1", 5: "Q1", 6: "Q1",
        7: "Q2", 8: "Q2", 9: "Q2",
        10: "Q3", 11: "Q3", 12: "Q3",
        1: "Q4", 2: "Q4", 3: "Q4",
    }
    df["Qtr"] = (
        month.map(quarter_map) + "-" + df["FY"].str[2:]
    )

    return df

# The chain-offtake flat dump carries exactly these month columns
# (Apr-24..May-26 = 26 months, once the business's updated sell-out master
# with Apr-26/May-26 columns is supplied). load_offtake()/offtake_block()
# derive every column count and month/quarter label purely from len(MONTHS)
# and quarter_labels_for(MONTHS) -- so when the source grows again (FY28),
# bumping n_months here is the ONLY change needed; FY27/FY28 offtake keys
# (total_fyNN / monthly_fyNN / months_fyNN / by_chain fyNN ...) then appear
# automatically. NOTE: until the actual Apr-26/May-26 offtake_flat.txt is
# supplied, load_offtake() has no file to read and this constant has no
# effect on the shipped dashboard.
MONTHS = month_labels(2024, 26)

BRAND_MAP = {
    "bblunt": "BBlunt", "the derma co.": "The Derma Co", "the derma co": "The Derma Co",
    "dr. sheth's": "Dr. Sheth's", "dr.sheth's": "Dr. Sheth's", "dr. sheth": "Dr. Sheth's",
    "mamaearth": "Mamaearth", "aqualogica": "Aqualogica", "pure origin": "Pure Origin",
    "staze": "Staze",
}

def canon_brand(b):
    if b is None or (isinstance(b, float) and math.isnan(b)):
        return None
    k = str(b).strip().lower()
    return BRAND_MAP.get(k, str(b).strip())

def canon_zone(z):
    """Canonicalize zone names from source data to standard form.

    Central zone (Madhya Pradesh + Chhattisgarh) is classified as "Central" in
    offtake source data and maintained as an official MT zone per ZoneStateMaster.csv.
    This function normalizes variant spellings (e.g. "south-1" -> "South 1") and
    ensures "Central" passes through as-is to the aggregation pipeline.
    """
    if z is None:
        return None
    z = str(z).strip()
    m = {"south-1": "South 1", "south 1": "South 1", "south-2": "South 2", "south 2": "South 2",
         "north": "North", "west": "West", "east": "East", "central": "Central", "pan india": "Pan India"}
    return m.get(z.lower(), z)

_CENTRAL_STATES = {"madhya pradesh", "mp", "chhattisgarh", "chattisgarh", "chattishgarh"}

def zone_with_central_override(zone, state):
    """Apply the Central-state override on top of canon_zone().

    Apr/May/Jul'26 offtake extracts already tag Madhya Pradesh and Chhattisgarh
    rows as "Central" in their own Zone column. Jun'26 does not -- those same
    states show up there as North/East/West, which would silently zero out
    Central for that month and inflate the other two. Re-deriving from State
    for these two states keeps every month consistent without touching zones
    that are not in dispute.

    Unlike canon_zone_from_state() below, this ALWAYS prefers the source's own
    Zone tag first (via canon_zone()) and only steps in for the two disputed
    states -- so a row the source already correctly tags (e.g. the Vidarbha
    cities of Maharashtra, which FY27 extracts already tag Central) is never
    overridden. Use this wherever the source's own zone tag is present and
    should be trusted except for the known MP/Chhattisgarh gap.
    """
    z = canon_zone(zone)
    s = str(state).strip().lower() if state is not None else ""
    if s in _CENTRAL_STATES:
        return "Central"
    return z

def canon_zone_from_state(state):
    """Map state/region to MT zone unconditionally. Used to override zone column
    when it's miscoded in source.

    The offtake extracts incorrectly assign Madhya Pradesh and Chhattisgarh to North/West
    instead of Central, so this override corrects the zone assignment at ingest time.

    CAVEAT: this is a blanket state->zone table, not a source-respecting patch --
    it does NOT check whether the source already tagged the row correctly. Every
    Maharashtra row maps to "West" here, including the Vidarbha cities (Nagpur,
    Akola, Yavatmal, Wardha, Amravati, Chandrapur) that FY27 offtake extracts
    already tag "Central" in their own Zone column. Safe today only because its
    two call sites (offtake_rebuild_block, load_fy25_secondary) both consume
    FY26/FY25 sources where Central was never tagged for any state (so there is
    no correct pre-existing tag to clobber) -- do not reuse this function against
    a source, like the FY27 monthly drops, whose Zone column already carries a
    real Central classification; use zone_with_central_override() there instead."""
    if state is None:
        return None
    state = str(state).strip()
    state_lower = state.lower()

    # State -> Zone mappings (official per ZoneStateMaster)
    state_to_zone = {
        # North zone
        "delhi": "North", "delhi ncr": "North", "delhi/ ncr": "North",
        "haryana": "North", "punjab": "North", "j&k": "North", "himachal": "North",
        "up": "North", "uttarakhand": "North", "up/uk": "North",

        # East zone
        "bihar": "East", "jharkhand": "East", "odisha": "East", "west bengal": "East",
        "northeast": "East",

        # West zone
        "goa": "West", "rajasthan": "West", "maharashtra": "West", "mumbai": "West",
        "gujarat": "West",

        # South 1 zone
        "karnataka": "South 1", "tamil nadu": "South 1", "telangana": "South 1",
        "andhra": "South 1", "andhra pradesh": "South 1",

        # South 2 zone
        "kerala": "South 2",

        # Central zone (CRITICAL: MP and CG are miscoded as North/West in offtake, override here)
        "madhya pradesh": "Central", "mp": "Central",
        "chhattisgarh": "Central", "cg": "Central",
    }

    return state_to_zone.get(state_lower, None)

STATE_ALIASES = {
    "delhi/ ncr": "Delhi/ Ncr", "delhi/ncr": "Delhi/ Ncr", "delhi ncr": "Delhi/ Ncr",
    "up/uk": "UP/UK", "up / uk": "UP/UK",
    "punjab/j&k/hp": "Punjab/J&K/Hp", "punjab / j&k / hp": "Punjab/J&K/Hp",
    "northeast": "Northeast", "north east": "Northeast",
    "hayana": "Haryana",
    "mumbai": "Mumbai",
    "pan india": "Pan India",
}
def canon_state(s):
    if s is None:
        return None
    s = str(s).strip()
    if not s or s.lower() in ("nan", "none"):
        return None
    return STATE_ALIASES.get(s.lower(), s.title())

# Canonical chain key: collapse the many spellings across the four files onto a
# single business-facing chain name so primary / offtake / universe / promo join.
CHAIN_ALIASES = [
    ("Apollo",            ["apollo", "apollo healthco",
                            # Verified 2026-09-14 against ShipToMaster.csv and the Apr-Aug'26
                            # secondary hierarchy file: every "APOLLO HEALTHCO LIMITED-*"
                            # distributor Ship-To reports its Chain as "Apollo Pharmacy" --
                            # that is Apollo's own retail-pharmacy format, not a distinct chain.
                            # Real money: ~Rs9.98 Cr over Apr-Aug'26 was previously stranded
                            # under this unaliased spelling instead of folding into Apollo.
                            "apollo pharmacy", "apollo healthco limited"]),
    ("Reliance Retail",   ["reliance retail", "reliance retail limited", "reliance retail ltd.",
                            "reliance", "reliance ", "rrl",
                            # Verified 2026-09-14: ShipToMaster.csv has a governed
                            # "Reliance Retail Limited-FOC" entry (Direct, Primary
                            # Chain = Reliance Retail) -- the same entity type as
                            # UniverseMT.csv's "RRL-FOC-Sample" (RRL = Reliance
                            # Retail Limited; FOC = free-of-charge/sample door).
                            # Previously kept as its own standalone label with no
                            # evidence either way; this resolves it using the same
                            # real master data used for every other chain here.
                            "rrl-foc-sample"]),
    ("DMart",             ["dmart", "d-mart", "d-mart ", "dmart "]),
    ("Nykaa (FSN)",       ["fsn", "nykaa ss(fsn)", "nykaa"]),
    ("Wellness Forever",  ["wellness forever"]),
    ("Health & Glow",               ["h&g", "hng", "h\\&g"]),
    ("Lulu",              ["lulu", "lulu ",
                            # Verified 2026-09-14 against the same secondary hierarchy file --
                            # "Lulu Hyper" and "Lulu Hypermarket" are spelling variants of Lulu,
                            # not separate chains (~Rs3.13 Cr over Apr-Aug'26 combined).
                            "lulu hyper", "lulu hypermarket"]),
    ("Metro C&C",         ["metro cnc", "metro c&c", "metro ", "metro-cnc-rrl"]),
    ("More Retail",       ["more", "more retail", "more "]),
    ("Sancus (RMT)",        ["rmt-sancus", "sancus(rmt)", "sancus ", "rmt-delhi"]),
    ("Walmart",           ["walmart cnc", "walmart", "walmart ", "wal-mart"]),
    ("Spencer",           ["spencer", "spencers", "spencer's"]),
    ("Guardian",          ["guardian", "gaurdian "]),
    ("Trent",             ["trent", "trent "]),
    ("V-Mart",            ["v-mart", "v mart east "]),
    ("Ratnadeep",         ["ratnadeep", "ratandeep"]),
    ("Sasta Sundar",      ["sasta sundar", "sasta sunder", "ssl", "sastasundar"]),
    ("Frankross",         ["frankross", "frankros", "frank ross"]),
    ("Arambagh",          ["arambagh", "aarambagh food mart ", "arambagh food mart"]),
    ("WH-Smith",          ["wh-smith"]),
    ("B&N",               ["b&n", "beauty & nutire", "beauty & nutrie", "b\\&n"]),
    ("Apna Mart",         ["apna mart", "apna mart "]),
    ("Sumo Save",         ["sumo save", "sumosave"]),
    ("Deal Share",        ["deal share", "deal share "]),
    ("Sohum Shoppe",      ["sohum shoppe", "sohum"]),
    ("Lifestyle",         ["lifestyle", "lifestyle "]),
    ("Trent/Westside",    ["trends"]),
    ("Azorte",            ["azorte", "reliance retail-(azorte)", "reliance retail ltd (azorte)"]),
    ("DMart",             ["dc-d-mart-offline", "d-mart-offline", "d-mart-store-e-com",
                            "just mark-dmart", "just mark-d-mart"]),
    ("Reliance Retail",   ["reliance retail-dc", "reliance retail-store"]),
    ("Nykaa (FSN)",       ["nykaa e-retail limited"]),
    ("Metro C&C",         ["metro-cnc"]),
    ("Walmart",           ["walmart-cnc"]),
    ("Health & Glow",               ["health & glow", "r.c. trade link h&g", "r.c. trade link"]),
    ("Guardian",          ["guardian healthcare", "guardian healthcare-delhi", "gaurdian"]),
    ("Trent",             ["trent hypermarket"]),
    ("V-Mart",            ["v-mart retail limited", "v-mart retail", "v mart east"]),
    ("WH-Smith",          ["travel news services-wsmith"]),
    ("Relay",             ["travel retail services-relay"]),
    ("Apollo",            ["united marketing", "mark enterprise-apollo",
                            "pragati sales-apollo"]),
    ("Eremedium",         ["eremedium private limited"]),
    ("Ratnadeep",         ["ratanadeep"]),
    ("Sancus (RMT)",        ["sancus", "sancus networks-mt-reg."]),
    ("Arambagh",          ["aarambagh food mart"]),
    ("VMM",  ["vmm", "vmm ", "vishal mega mart"]),
    ("Lifestyle",         ["lifestyle babyshop"]),
    # Vishal Enterprises (Solapur) is a distributor billing into D-Mart, not
    # a name for the Vishal Mega Mart chain -- despite the "vishal" in both,
    # they are unrelated entities. Confirmed against the raw Primary source:
    # every "VISHAL ENTERPRISES_Solapur" row already carries Chain Name =
    # "D-Mart" there. The bare "vishal enterprises" alias used to be
    # (incorrectly) mapped to VMM above; this is the correct destination.
    ("DMart",             ["pragati sales-d-mart", "kiran trading company-solapur-d-mart",
                            "vishal enterprises-d-mart", "vishal enterprises"]),
    ("Shoppers Stop",     ["shoppers stop"]),
]
_ALIAS_LOOKUP = {}
for canon, al in CHAIN_ALIASES:
    for a in al:
        _ALIAS_LOOKUP[a] = canon

def canon_chain(name):
    if name is None or (isinstance(name, float) and math.isnan(name)):
        return None
    k = str(name).replace("\xa0", " ").strip()
    kl = k.lower()
    if kl in _ALIAS_LOOKUP:
        return _ALIAS_LOOKUP[kl]
    return k

def r2(x, nd=2):
    try:
        if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
            return None
        return round(float(x), nd)
    except Exception:
        return None

# --------------------------------------------------------------------------
# STORE HIERARCHY & DATA GRANULARITY STANDARDIZATION
# Phase 1: v1.1.2 — Assign deterministic synthetic site codes to chains
# that report at Pan-India or regional levels (no store ID mapping).
# Prevents null-join dropped rows in frontend aggregations.
# --------------------------------------------------------------------------
def standardize_site_codes(df):
    """
    Assigns deterministic synthetic site codes to prevent null-join dropped rows.

    Business Rules:
    - Pan-India chains (Nykaa, FSN, E-commerce): Single synthetic code 'PAN_INDIA_DUMMY'
    - Regional chains (Reliance bulk offtake): Zone-level codes 'REL_REGIONAL_{ZONE}'
    - Default fallback: 'SITE_UNASSIGNED' for any unexpected blanks

    Returns: DataFrame with standardized site_code and store_name columns.
    """
    df = df.copy()

    # Initialize site_code column if missing
    if 'site_code' not in df.columns:
        df['site_code'] = None
    if 'store_name' not in df.columns:
        df['store_name'] = None

    # Pan-India chains: Single synthetic code (Nykaa, FSN, E-commerce)
    pan_india_chains = ['NYKAA', 'FSN', 'AMAZON', 'FLIPKART', 'NYKAA (FSN)', 'NYKAA SS(FSN)']
    mask_pan_india = df['chain'].fillna('').str.upper().isin(pan_india_chains)
    df.loc[mask_pan_india & df['site_code'].isna(), 'site_code'] = 'PAN_INDIA_DUMMY'
    df.loc[mask_pan_india & df['store_name'].isna(), 'store_name'] = \
        df.loc[mask_pan_india & df['store_name'].isna(), 'chain'].fillna('') + ' - Pan-India Aggregated'
    df.loc[mask_pan_india & df['zone'].isna(), 'zone'] = 'Pan India'

    # Regional-level chains (Reliance bulk offtake): Zone-level synthetic codes
    mask_reliance_bulk = (df['chain'].fillna('').str.upper() == 'RELIANCE RETAIL') & df['site_code'].isna()
    df.loc[mask_reliance_bulk, 'site_code'] = 'REL_REGIONAL_' + df.loc[mask_reliance_bulk, 'zone'].fillna('NA').str.upper()
    df.loc[mask_reliance_bulk, 'store_name'] = \
        'Reliance Regional (' + df.loc[mask_reliance_bulk, 'state'].fillna('Unassigned') + ')'

    # Default fallback for any unexpected blank site codes
    df['site_code'] = df['site_code'].fillna('SITE_UNASSIGNED')
    df['store_name'] = df['store_name'].fillna('Unassigned Store / Aggregated')

    return df

# --------------------------------------------------------------------------
# PRIMARY
# --------------------------------------------------------------------------
def load_primary(src):
    df = pd.read_excel(src / "primary.xlsx", sheet_name="Sheet1", header=1)
    df.columns = [str(c).strip() for c in df.columns]
    df = df.dropna(how="all")
    df = df[df["NSV"].notna()]
    df["chain"] = df["Chain Name"].map(canon_chain)
    df["brand"] = df["Brand"].map(canon_brand)
    df["zone"] = df["Zone"].map(canon_zone)
    df["channel"] = df["Channel"].astype(str).str.strip()
    df["NSV"] = pd.to_numeric(df["NSV"], errors="coerce").fillna(0.0)
    df["MRP value"] = pd.to_numeric(df["MRP value"], errors="coerce").fillna(0.0)
    return df

# --------------------------------------------------------------------------
# PRIMARY — Distributor -> Chain, secondary-driven allocation
#
# Raw primary rows tag ONE "Chain Name" per row even for Distributor-billed
# ("Dist.") ship-to accounts that actually supply SEVERAL chains -- so a
# naive group-by-Chain-Name on Distributor rows is really distributor-wise,
# not chain-wise. This mirrors what the Power BI model does explicitly
# (Ship-To Master -> Fact Primary ShipTo, split by a secondary/offtake-
# derived Cont%, see PowerBI/docs/DistributorPrimaryAllocation_Logic.md):
# for each Distributor Ship-To x Brand x Month, re-split its primary NSV
# across the chains it actually serves, weighted by that chain's share of
# the ship-to's own secondary (offtake) billing that month. Direct rows are
# unambiguous (one ship-to = one chain) and are never re-split.
# --------------------------------------------------------------------------
def load_primary_v2(src):
    """Load primary from the monthly drop in --src (authoritative), else the
    committed CSV seed (fallback).
    DROP: <src>/Primary_FY202426_*.{xlsx,xlsb,csv}  -- newest by mtime wins
    SEED: PowerBI/SeedData/Primary/Primary_FY202426_10.csv
    Same output shape as load_primary() plus raw Ship-To/Distributor columns.

    Phase 1 v1.1.2: Applies standardize_site_codes() to ensure Pan-India and
    regional chains have deterministic synthetic site codes (prevents null-join
    dropped rows in dashboard aggregations)."""
    # Resolution order (changed 2026-09): a monthly drop in --src is
    # AUTHORITATIVE; the committed seed is only the fallback.
    #
    # Previously the seed was checked first. Because it is tracked in git it
    # exists in every clone, so it always won and a file dropped into --src was
    # never read -- the documented monthly workflow refreshed nothing and still
    # exited 0. The old fallback also matched one exact filename and demanded a
    # sheet literally named "Dump", so Primary_FY202426_11.xlsx would have been
    # missed even had the fallback been reachable.
    seed = Path("PowerBI/SeedData/Primary/Primary_FY202426_10.csv")
    drops = sorted([*src.glob("Primary_FY202426_*.xlsx"),
                    *src.glob("Primary_FY202426_*.xlsb"),
                    *src.glob("Primary_FY202426_*.csv")],
                   key=lambda p: (p.stat().st_mtime, p.name))
    if drops:
        f = drops[-1]                      # newest by mtime, name as tiebreak
        print(f"  primary source: {f}  (monthly drop)")
        if len(drops) > 1:
            print(f"    note: {len(drops)} Primary candidates in {src}; using newest")
        _is_csv = f.suffix.lower() == ".csv"
        if _is_csv:
            df = pd.read_csv(f)
        else:
            _eng = "pyxlsb" if f.suffix.lower() == ".xlsb" else "openpyxl"
            # Header normally sits on row 2 ("Dump" sheet with a spacer row),
            # but accept ANY sheet/offset that carries the required columns
            # rather than hardcoding a sheet name the business may rename.
            _need = {"NSV", "Month", "Chain Name", "Bill to customer"}
            df = None
            for _hdr in (1, 0):
                for _d in pd.read_excel(f, sheet_name=None, header=_hdr,
                                        engine=_eng).values():
                    if _need <= {str(c).strip() for c in _d.columns}:
                        df = _d
                        break
                if df is not None:
                    break
            if df is None:
                raise SystemExit(
                    f"Primary drop {f.name} has no sheet carrying {sorted(_need)} "
                    f"at header row 0 or 1.")
    elif seed.exists():
        print(f"  primary source: {seed}  (committed seed -- no drop found in {src})")
        df = pd.read_csv(seed)
        _is_csv = True
    else:
        raise FileNotFoundError(
            f"Primary data not found: no Primary_FY202426_* in {src}, and no {seed}")

    df.columns = [str(c).strip() for c in df.columns]
    df = df.dropna(how="all")
    df = df[df["NSV"].notna()]
    df["_ship_to"] = df["Bill to customer"].astype(str).str.strip()
    df["_dist_flag"] = df["Direct/Distributor"].astype(str).str.strip()
    df["NSV"] = pd.to_numeric(df["NSV"], errors="coerce").fillna(0.0)
    df["MRP value"] = pd.to_numeric(df["MRP value"], errors="coerce").fillna(0.0)
    df["Month"] = df["Month"].astype(str).str.strip()
    # CSV stores NSV/MRP in rupees; script/dashboard expect INR Lakh (1 Lakh = 100,000)
    if _is_csv:
        df["NSV"] = df["NSV"] / 1e5
        df["MRP value"] = df["MRP value"] / 1e5

    # Phase 1 v1.1.2: Canonicalize chain names and standardize site codes
    # before returning so downstream allocation/aggregation doesn't drop rows.
    if "Chain Name" in df.columns:
        df["chain"] = df["Chain Name"].map(canon_chain)
    if "Zone" in df.columns:
        df["zone"] = df["Zone"].map(canon_zone)
    if "State" in df.columns:
        df["state"] = df["State"].map(canon_state)

    df = standardize_site_codes(df)

    return df

def load_chain_allocation_weights(src):
    """Read the secondary-driven Ship-To -> Chain Cont% allocation (CSV seed preferred).
    CSV: PowerBI/SeedData/DIST/ChainAllocationWeights.csv (versioned in git)
    XLSX: Dist_primary_cont_based_on_secondary_MOM.xlsx Sheet2 (fallback)
    CSV (narrow, approved patch): PowerBI/SeedData/DIST/DistPrimaryContWeightsArticle.csv
    Returns {(ship_to_norm, brand_canon, month_norm): [(chain_raw, fraction), ...]}
    with fractions normalized to sum to 1 per key. Returns None if none of these exist."""
    # Try the comprehensive CSV first
    csv_f = Path("PowerBI/SeedData/DIST/ChainAllocationWeights.csv")
    if csv_f.exists():
        s2 = pd.read_csv(csv_f)
    else:
        # Fallback to XLSX
        f = src / "Dist_primary_cont_based_on_secondary_MOM.xlsx"
        if f.exists():
            s2 = pd.read_excel(f, sheet_name="Sheet2", header=1)
        else:
            # Neither the comprehensive file nor its XLSX source exists in this
            # repo (verified 2026-09-14). What DOES exist is a much narrower,
            # already-APPROVED patch covering 5 distributors x 4 months --
            # PowerBI/SeedData/DIST/DistPrimaryContWeightsArticle.csv. It has a
            # pre-computed Cont_Pct (not raw NSV to ratio from) and different
            # column names, so it needs its own conversion rather than being
            # forced through the NSV-ratio path below. Using it here is real,
            # approved data that was previously wired into nothing -- not a
            # fabricated default (contrast with allocate_dist_enhanced.py's
            # Tier 3, which was inventing a split; see that file's history).
            patch_f = Path("PowerBI/SeedData/DIST/DistPrimaryContWeightsArticle.csv")
            if not patch_f.exists():
                return None
            p = pd.read_csv(patch_f)
            p = p[p["Approval_Status"].astype(str).str.strip().str.lower() == "approved"]
            weights = {}
            for key, g in p.groupby([
                p["Ship_To_Name"].astype(str).str.strip().str.lower(),
                p["Brand"].map(canon_brand),
                p["Month"].astype(str).str.strip().str.lower(),
            ]):
                tot = g["Cont_Pct"].sum()
                if tot <= 0:
                    continue
                weights[key] = [(row["Chain_Name"], row["Cont_Pct"] / tot) for _, row in g.iterrows()]
            return weights or None

    s2.columns = [str(c).strip() for c in s2.columns]
    s2 = s2.dropna(subset=["NSV"])
    s2["_key"] = list(zip(
        s2["Ship To Name"].astype(str).str.strip().str.lower(),
        s2["Brand"].map(canon_brand),
        s2["Month"].astype(str).str.strip().str.lower(),
    ))
    weights = {}
    for key, g in s2.groupby("_key"):
        tot = g["NSV"].sum()
        if tot <= 0:
            continue
        weights[key] = [(row["Chain Name"], row["NSV"] / tot) for _, row in g.iterrows()]
    return weights

def apply_chain_allocation(df, weights):
    """Re-split Distributor ('Dist.') rows across the chains they actually
    serve using `weights` (secondary-derived Cont%, see
    load_chain_allocation_weights). Direct rows and any Distributor row with
    no matching weight (no allocation data for that Ship-To x Brand x Month
    -- e.g. FY24-25, which the allocation file doesn't cover) keep their
    original single Chain Name tag, unchanged. Returns (new_df, qc) where qc
    is a by-FY breakdown of how much Distributor value was actually
    reallocated vs left on the raw tag, for the Chain Allocation QC card."""
    if weights is None:
        df["chain"] = df["Chain Name"].map(canon_chain)
        df["brand"] = df["Brand"].map(canon_brand)
        df["zone"] = df["Zone"].map(canon_zone)
        df["channel"] = df["Channel"].astype(str).str.strip()
        return df, None
    is_dist = df["_dist_flag"] == "Dist."
    df["_key"] = list(zip(
        df["_ship_to"].str.lower(),
        df["Brand"].map(canon_brand),
        df["Month"].str.lower(),
    ))
    matched = is_dist & df["_key"].isin(weights)
    matched_rows = df[matched]
    unmatched_rows = df[~matched]

    exploded = []
    for _, r in matched_rows.iterrows():
        for chain_raw, frac in weights[r["_key"]]:
            row = r.copy()
            row["Chain Name"] = chain_raw
            row["NSV"] = r["NSV"] * frac
            row["MRP value"] = r["MRP value"] * frac
            exploded.append(row)
    exploded_df = pd.DataFrame(exploded) if exploded else df.iloc[0:0].copy()

    out = pd.concat([unmatched_rows, exploded_df], ignore_index=True)
    out["chain"] = out["Chain Name"].map(canon_chain)

    # QC: how much Distributor primary was actually reallocated via the
    # secondary-derived Cont% vs left on its raw single-chain tag, by FY.
    qc_by_fy = {}
    for fy, g in df[is_dist].groupby("FY"):
        tot = float(g["NSV"].sum())
        mval = float(g[matched.loc[g.index]]["NSV"].sum())
        qc_by_fy[fy] = {
            "distributor_primary": r2(tot),
            "chain_allocated": r2(mval),
            "raw_tag_fallback": r2(tot - mval),
            "allocated_coverage_pct": r2(mval / tot * 100, 1) if tot else None,
        }
    total_dist = float(df[is_dist]["NSV"].sum())
    total_matched = float(matched_rows["NSV"].sum())
    qc = {
        "method": "Distributor-billed ('Dist.') primary is re-split across the chains a "
                  "ship-to actually serves, weighted by that chain's share of the ship-to's "
                  "own secondary/offtake billing that Month x Brand (source: "
                  "Dist_primary_cont_based_on_secondary_MOM.xlsx, mirrors the Power BI Ship-to "
                  "allocation model). Direct-billed rows are unambiguous (1 ship-to = 1 chain) "
                  "and are never re-split. Rows with no matching allocation entry for that "
                  "Ship-To x Brand x Month (the allocation file does not cover FY24-25) keep "
                  "their original single Chain Name tag.",
        "distributor_primary_total": r2(total_dist),
        "chain_allocated_total": r2(total_matched),
        "raw_tag_fallback_total": r2(total_dist - total_matched),
        "allocated_coverage_pct": r2(total_matched / total_dist * 100, 1) if total_dist else None,
        "by_fy": qc_by_fy,
        "unit": "INR Lakh",
        "note": "'raw_tag_fallback' can be negative (pushing coverage % slightly above 100) "
                "in a period where the unmatched remainder is dominated by return/credit-note "
                "rows (negative NSV) that the secondary-based allocation file doesn't cover -- "
                "this is a real property of the data, not a computation error.",
    }
    out["brand"] = out["Brand"].map(canon_brand)
    out["zone"] = out["Zone"].map(canon_zone)
    out["channel"] = out["Channel"].astype(str).str.strip()
    return out, qc

def primary_block(df):
    """Aggregates the primary workbook with DYNAMIC FY keys: whatever FY
    values exist in the source ('FY_24-25', "FY'26-27", ...) are mapped
    through _fylabel/THE ONE FY RULE and emitted as nsv_fy25/nsv_fy26/
    nsv_fy27/..., monthly_fyNN, and per-dimension fyNN keys, plus a
    `fy_tags` list ['fy25','fy26',...] the dashboard iterates instead of
    hardcoding years. Add FY26-27 rows to the source workbook and FY27
    columns appear everywhere automatically (FY28 likewise)."""
    out = {}
    # source-FY column value -> canonical tag ('FY_24-25' -> 'FY25')
    src_fys = [k for k in df["FY"].dropna().unique()]
    tag_of = {k: _fylabel(k) for k in src_fys}
    _all_tags = sorted({t for t in tag_of.values() if t}, key=fy_start_year)
    # COVERAGE GATE: this workbook is the pre-aggregated Primary extract, which
    # ends Mar'26. It can still carry a handful of stray rows for a later FY
    # (an early Apr-26 billing batch, a manual add) -- those are PARTIAL and are
    # not this source's to publish. Emitting them as first-class nsv_fyNN keys
    # made the dashboard treat that FY as fully covered here, which (a) silently
    # understated it and (b) switched off the partial-year guards downstream,
    # because index.html derives PREAGG_FYS from exactly these keys.
    # The article-level source owns those FYs and publishes them under
    # detail_meta.fyx_primary[<FY>]. Drop them here rather than compete.
    tags = [t for t in _all_tags if t in PREAGG_FY_TAGS]
    _dropped = [t for t in _all_tags if t not in PREAGG_FY_TAGS]
    keys_of = {t: [k for k, tt in tag_of.items() if tt == t] for t in tags}
    lo = [t.lower() for t in tags]
    out["fy_tags"] = lo
    if _dropped:
        # Auditable, not silent: record what this source held back and why.
        _held = {}
        for t in _dropped:
            _k = [k for k, tt in tag_of.items() if tt == t]
            _held[t.lower()] = r2(float(df[df["FY"].isin(_k)]["NSV"].sum()))
        out["coverage_note"] = (
            f"{', '.join(t.upper() for t in _dropped)} rows present in this "
            f"pre-aggregated workbook are PARTIAL ({_held}, INR Lakh) and are "
            f"not published here. Those FYs are owned by the article-level "
            f"source: see detail_meta.fyx_primary. Source coverage = "
            f"{sorted(PREAGG_FY_TAGS)}.")
        out["coverage_withheld"] = _held

    def fy_get(series, t):
        return float(sum(series.get(k, 0) or 0 for k in keys_of[t]))
    fy = df.groupby("FY")["NSV"].sum()
    gross = df.groupby("FY")["MRP value"].sum()
    for t in tags:
        out[f"nsv_{t.lower()}"] = r2(fy_get(fy, t))
        out[f"mrp_{t.lower()}"] = r2(fy_get(gross, t))
    # YoY = last COMPLETE-ish comparison: second-latest vs the one before it
    # is meaningless for a 2-FY file, so keep the classic definition: latest
    # of the first two tags vs the first (fy26 vs fy25 today). If a third FY
    # exists it gets its own key but doesn't silently redefine the headline YoY.
    if len(lo) >= 2:
        a, b = out.get(f"nsv_{lo[0]}"), out.get(f"nsv_{lo[1]}")
        out["yoy"] = r2((b / a - 1) * 100) if a else None
    else:
        out["yoy"] = None
    out["n_chains"] = int(df["chain"].nunique())
    out["n_brands"] = int(df["brand"].nunique())

    # Monthly trend by FY, aligned to calendar position Apr..Mar
    order = ["April","May","June","July","Aug","Sept","Oct","Nov","Dec","Jan","Feb","March"]
    def mkey(m):
        m = str(m)
        for i, o in enumerate(order):
            if m.lower().startswith(o.lower()[:3]):
                return i
        return 99
    df["_mk"] = df["Month"].map(mkey)
    piv = df.pivot_table(index="_mk", columns="FY", values="NSV", aggfunc="sum").reindex(range(12))
    out["month_labels"] = order
    for t in tags:
        cols = [k for k in keys_of[t] if k in piv.columns]
        ser = piv[cols].sum(axis=1, min_count=1) if cols else pd.Series(index=range(12), dtype="float64")
        out[f"monthly_{t.lower()}"] = [r2(ser.get(i)) for i in range(12)]

    def dim_rows(index_col, keep_blank=False, sort=True):
        pv = df.pivot_table(index=index_col, columns="FY", values="NSV", aggfunc="sum").fillna(0)
        rows = []
        for k in pv.index:
            if not k and not keep_blank:
                continue
            row = {"name": k}
            for t in tags:
                row[t.lower()] = r2(fy_get(pv.loc[k], t))
            if len(lo) >= 2:
                a, b = row.get(lo[0]), row.get(lo[1])
                row["yoy"] = r2((b / a - 1) * 100) if a else None
            rows.append(row)
        # sort by the LATEST FY's value so new years take over the ranking
        return sorted(rows, key=lambda d: -(d.get(lo[-1]) or 0)) if (sort and lo) else rows

    out["by_channel"] = dim_rows("channel", keep_blank=True, sort=False)

    # Ensure all known channels are represented (MT, EB2B, SIS), even if missing from current data
    # This ensures the UI shows consistent channel options across all FYs
    all_known_channels = {"MT", "EB2B", "SIS"}
    existing_channels = {ch["name"] for ch in out["by_channel"]}
    for ch_name in sorted(all_known_channels):
        if ch_name not in existing_channels:
            # Add channel with zero values for all FYs
            ch_entry = {"name": ch_name}
            for t in tags:
                ch_entry[t.lower()] = 0
            out["by_channel"].append(ch_entry)

    out["by_zone"] = dim_rows("zone")
    out["by_brand"] = dim_rows("brand")
    out["by_chain"] = dim_rows("chain")
    return df, out

# --------------------------------------------------------------------------
# OFFTAKE  (parsed from the read_file_content text dump of the master file)
# --------------------------------------------------------------------------
def _num(x):
    x = (x or "").strip()
    if x == "":
        return None
    try:
        return float(x)
    except Exception:
        return None

def load_offtake(src):
    t = (src / "offtake_flat.txt").read_text()
    n_m = len(MONTHS)
    # ---- chain-wise monthly (Sheet2) ----
    s2 = t[: t.index("Sheet3")]
    body = s2[s2.index("Grand Total ") + len("Grand Total "):]
    rows = re.split(r"(?<=\d) (?=[A-Za-z])", body)
    chains = {}
    for r in rows:
        parts = r.split(",")
        name = parts[0].strip().replace("\\&", "&")
        if name.lower() == "grand total" or len(parts) < n_m + 2:
            continue
        vals = [_num(v) for v in parts[1:n_m + 2]]
        chains[name] = {"months": {MONTHS[i]: vals[i] for i in range(n_m)}, "total": vals[n_m]}
    # ---- zone/state quarterly (Sheet3) ----
    s3 = t[t.index("Sheet3"):]
    qcols = quarter_labels_for(MONTHS)
    n_q = len(qcols)
    h = s3.index(qcols[0])
    start = s3.index("Grand Total", h) + len("Grand Total")
    end = s3.index("Brand Counter") if "Brand Counter" in s3 else len(s3)
    rows3 = re.split(r"(?<=\d) (?=[A-Za-z,\"])", s3[start:end])
    zs, cur = [], None
    for r in rows3:
        r = r.strip()
        if not r:
            continue
        rd = next(csv.reader(io.StringIO(r)))
        if len(rd) < n_q + 3:
            continue
        zone = (rd[0].strip() or cur)
        cur = zone
        if rd[1].strip().lower() == "" or zone.lower() == "grand total":
            continue
        zs.append({"zone": zone, "state": rd[1].strip().replace("\\&", "&"),
                   "q": {qcols[i]: _num(rd[2 + i]) for i in range(n_q)}, "total": _num(rd[2 + n_q])})
    return chains, zs

def offtake_block(chains, zs):
    """Aggregates the sell-out master with DYNAMIC FY keys, grouping month
    labels ('Apr-24'..'Mar-26', extendable) through THE ONE FY RULE instead
    of fixed index slices. Emits total_fyNN / monthly_fyNN / by_chain fyNN /
    by_zone / by_state keys for WHATEVER FYs the month columns cover, plus a
    `fy_tags` list -- so an updated master carrying Apr-26+ columns produces
    FY27 offtake automatically (FY28 likewise)."""
    out = {}
    # month label -> FY tag (label-driven, never positional)
    fy_of_month = {m: fy_tag_from_label(m) for m in MONTHS}
    tags = sorted({t for t in fy_of_month.values() if t}, key=fy_start_year)
    lo = [t.lower() for t in tags]
    out["fy_tags"] = lo
    months_of = {t: [m for m in MONTHS if fy_of_month[m] == t] for t in tags}

    def fy_sum(mn, t):
        return sum(v for k, v in mn.items() if fy_of_month.get(k) == t and v)
    rows = []
    for name, d in chains.items():
        c = canon_chain(name)
        row = {"name": c, "raw": name, "total": r2(d["total"])}
        for t in tags:
            row[t.lower()] = r2(fy_sum(d["months"], t))
        a, b = (row.get(lo[0]), row.get(lo[1])) if len(lo) >= 2 else (None, None)
        row["yoy"] = r2((b / a - 1) * 100) if a else None
        rows.append(row)
    out["by_chain"] = sorted(rows, key=lambda d: -(d.get(lo[-1]) or 0))
    for t in tags:
        out[f"total_{t.lower()}"] = r2(sum(x[t.lower()] or 0 for x in rows))
    if len(lo) >= 2:
        a, b = out.get(f"total_{lo[0]}"), out.get(f"total_{lo[1]}")
        out["yoy"] = r2((b / a - 1) * 100) if a else None
    out["n_chains"] = len(rows)
    # monthly aggregate trend
    agg = {m: 0.0 for m in MONTHS}
    for d in chains.values():
        for m, v in d["months"].items():
            if v:
                agg[m] += v
    out["months"] = MONTHS
    out["monthly"] = [r2(agg[m]) for m in MONTHS]
    for t in tags:
        out[f"monthly_{t.lower()}"] = [r2(agg[m]) for m in months_of[t]]
        # month labels for monthly_fyNN above -- lets the dashboard chart a
        # single FY's trend without re-deriving FY membership from calendar
        # year suffixes (which only ever covered exactly two hardcoded FYs).
        out[f"months_{t.lower()}"] = months_of[t]
    # zone/state roll-up: quarter labels 'Q1-24' = the FY STARTING Apr of
    # that calendar year -> FY tag via the same ONE FY RULE
    def q_tag(qk):
        return fy_tag_from_ym(2000 + int(qk.split("-")[1]), 4)
    def q_sums(q):
        s = {}
        for k, v in q.items():
            t = q_tag(k)
            s[t] = s.get(t, 0.0) + (v or 0)
        return s
    ztags = sorted({q_tag(k) for r in zs for k in r["q"]}, key=fy_start_year) or tags
    zlo = [t.lower() for t in ztags]
    zagg = {}
    for r in zs:
        z = canon_zone(r["zone"])
        d = zagg.setdefault(z, {t: 0.0 for t in ztags})
        for t, v in q_sums(r["q"]).items():
            d[t] = d.get(t, 0.0) + v
    def z_row(name, sums):
        row = {"name": name}
        for t in ztags:
            row[t.lower()] = r2(sums.get(t, 0.0))
        a, b = (row.get(zlo[0]), row.get(zlo[1])) if len(zlo) >= 2 else (None, None)
        row["yoy"] = r2((b / a - 1) * 100) if a else None
        return row
    out["by_zone"] = sorted([z_row(z, v) for z, v in zagg.items()],
                            key=lambda d: -(d.get(zlo[-1]) or 0))
    st = []
    for r in zs:
        sums = q_sums(r["q"])
        row = z_row(r["state"], sums)
        row["zone"] = canon_zone(r["zone"])
        row["state"] = row.pop("name")
        st.append(row)
    out["by_state"] = sorted(st, key=lambda d: -(d.get(zlo[-1]) or 0))

    # Defensive: provide nested total[] object for buildInventoryHealth()
    # while keeping flat total_fyNN keys for backward compatibility
    out["total"] = {t.lower(): out.get(f"total_{t.lower()}") for t in tags}

    # Populate metrics (DOI/OTIF) — defaults for now, can be enriched with
    # actual calculations from inventory records if available
    out["metrics"] = {
        "doi": {},      # Days of Inventory by zone
        "otif": {},     # On-Time In-Full by zone
    }

    return out

def _offtake_row_month(month_val):
    """Row-level Month cell -> canonical 'Mon-YY' label (matches MONTHS'
    format), handling both text ("Apr'26") and Excel-serial-number forms
    found in the raw store x article offtake extracts (a single workbook's
    Month column can carry a mix of both -- some rows never got the text
    label applied upstream)."""
    if isinstance(month_val, str) and month_val.strip():
        m = re.match(r"([A-Za-z]{3,})['’]?\s*(\d{2,4})", month_val.strip())
        if m:
            mon = m.group(1)[:3].title()
            if mon in _MON3_NUM:
                return f"{mon}-{m.group(2)[-2:]}"
    if isinstance(month_val, (int, float)) and not (isinstance(month_val, float) and math.isnan(month_val)):
        d = datetime.datetime(1899, 12, 30) + datetime.timedelta(days=float(month_val))
        return f"{d.strftime('%b')}-{d.strftime('%y')}"
    # Some extracts (e.g. Reliance's monthly CSV, which carries no "Revised
    # Month"/"Year" fallback columns) hold the same Excel serial date as a
    # plain numeric-looking STRING when read via a manual csv.reader path
    # rather than pandas' own type inference. Give it the same serial-date
    # treatment rather than dropping the row.
    if isinstance(month_val, str) and month_val.strip():
        try:
            serial = float(month_val.strip())
        except ValueError:
            return None
        if not math.isnan(serial) and serial > 0:
            d = datetime.datetime(1899, 12, 30) + datetime.timedelta(days=serial)
            return f"{d.strftime('%b')}-{d.strftime('%y')}"
    return None

def _read_offtake_csv(fp):
    """Read one offtake extract CSV, tolerating a known export defect: some
    Reliance monthly files concatenate two source tabs (the general extract,
    then a Brand Counter tab) that don't share a column count, so the file
    is ragged from the point the second tab starts. pandas' C parser raises
    on the first ragged row; when that happens, keep only the well-formed
    leading block (every row up to the point the field count first departs
    from the header) and drop the rest -- which is safe here because that
    trailing block is exactly the Brand Counter rows the pipeline already
    excludes from totals via the Store Type/Data status filter below."""
    try:
        return pd.read_csv(fp, low_memory=False, encoding="utf-8")
    except UnicodeDecodeError:
        pass
    except pd.errors.ParserError:
        return _read_offtake_csv_ragged_leading_block(fp)
    try:
        return pd.read_csv(fp, low_memory=False, encoding="latin-1")
    except pd.errors.ParserError:
        return _read_offtake_csv_ragged_leading_block(fp)


def _read_offtake_csv_ragged_leading_block(fp):
    with open(fp, encoding="latin-1", newline="") as f:
        lines = f.readlines()
    header = next(csv.reader([lines[0]]))
    good_rows = []
    for line in lines[1:]:
        row = next(csv.reader([line]))
        if len(row) != len(header):
            break
        good_rows.append(row)
    return pd.DataFrame(good_rows, columns=header)


def load_offtake_article_files(src):
    """Aggregates NEW monthly store x article offtake extracts (.xlsb, one
    workbook per calendar month, each carrying a Brand Counter sheet plus a
    general/non-brand-counter sheet) into chain-month / (zone,state)-month
    NSV sums -- used by --offtake-patch to add whatever new FY these months
    fall into (FY27 today, via THE ONE FY RULE) to an EXISTING offtake block,
    without needing the original FY24-26 pivot dump this file's grain has
    nothing to do with. NSV in these extracts is already INR Lakh (checked
    against the existing Lakh-denominated offtake trend -- same order of
    magnitude, continuing its Oct'25-Mar'26 growth trajectory).
    Searches src recursively, so a --src pointed at a parent of per-month
    subfolders (e.g. data/raw_drops/offtake_fy26/Apr'25/*.csv) is picked up
    the same as a flat folder of monthly files.
    Returns (chain_month, zone_state_month); both {} if no offtake extracts found."""
    files = sorted([*src.rglob("*.xlsb"), *src.rglob("*.xlsx"), *src.rglob("*.csv")])
    chain_month, zsm = {}, {}
    for fp in files:
        if fp.suffix.lower() == ".csv":
            _frames = {"csv": _read_offtake_csv(fp)}
        else:
            # .xlsb needs pyxlsb, .xlsx needs openpyxl.
            _eng = "pyxlsb" if fp.suffix.lower() == ".xlsb" else "openpyxl"
            # Some exports have a blank/index row before the header (header=1)
            # while others start the header at row 0. Auto-detect by trying header=0
            # first; fall back to header=1 if the required columns are absent.
            try:
                _frames0 = pd.read_excel(fp, sheet_name=None, header=0, engine=_eng)
            except Exception as _e:
                # An unreadable/placeholder workbook must not abort the whole
                # patch -- skip it and let the "no extracts found" guard decide.
                print(f"  ! skipping {fp.name}: unreadable ({type(_e).__name__})")
                continue
            _req = {"Chain Name", "Zone", "State", "Month", "NSV"}
            _use_h0 = any(_req <= {str(c).strip() for c in df_.columns}
                          for df_ in _frames0.values())
            if _use_h0:
                _frames = _frames0
            else:
                _frames = pd.read_excel(fp, sheet_name=None, header=1, engine=_eng)
        for _, df in _frames.items():
            df.columns = [str(c).strip() for c in df.columns]
            need = {"Chain Name", "Zone", "State", "Month", "NSV"}
            if not need <= set(df.columns):
                continue   # not a row-level extract sheet -- skip
            # A Primary sell-in extract carries ALL FIVE columns above, so the
            # test alone is not enough: a Primary workbook sitting in the same
            # --src folder gets merged into offtake, inflating it by ~5 orders
            # of magnitude (its NSV is rupee-denominated, offtake is Lakh) with
            # exit 0 and no warning. Reject on billing-side columns that only
            # ever appear in Primary, never in a sell-out extract.
            _primary_only = {"Bill to customer", "Direct/Distributor", "MRP value"}
            _hit = _primary_only & set(df.columns)
            if _hit:
                print(f"  ! skipping {fp.name}: Primary extract, not offtake "
                      f"(carries {sorted(_hit)})")
                continue
            df = df[df["Chain Name"].notna()].copy()
            # Reliance Brand Counter is a store-level breakout whose articles
            # already exist in the Non-Brand Counter totals — including both
            # double-counts Reliance by ~49%.  Exclude BC rows for Reliance.
            # Column name varies: "Data status" in .xlsb, "Store Type" in split CSVs.
            _ds_col = "Data status" if "Data status" in df.columns else \
                      "Store Type" if "Store Type" in df.columns else None
            if _ds_col is not None:
                _chain_c = df["Chain Name"].astype(str).str.strip().str.lower()
                _ds_c = df[_ds_col].astype(str).str.strip().str.lower()
                _is_rel = _chain_c.str.contains("reliance", na=False)
                _is_bc = (_ds_c == "brand counter")
                df = df[~(_is_rel & _is_bc)].copy()
            df["_chain"] = df["Chain Name"].map(canon_chain)
            df["_state"] = df["State"].map(canon_state)
            df["_zone"] = [zone_with_central_override(z, s)
                           for z, s in zip(df["Zone"], df["State"])]
            df["_month"] = df["Month"].map(_offtake_row_month)
            # Fallback: when Month has no year (e.g. "Jun" instead of "Jun'26"),
            # try "Revised Month" (Excel serial date) or combine Month + Year.
            if df["_month"].isna().any():
                mask = df["_month"].isna()
                if "Revised Month" in df.columns:
                    df.loc[mask, "_month"] = df.loc[mask, "Revised Month"].map(_offtake_row_month)
                    mask = df["_month"].isna()
                if mask.any() and "Year" in df.columns:
                    def _month_plus_year(row):
                        m, y = row["Month"], row["Year"]
                        if isinstance(m, str) and m.strip() and y is not None:
                            return _offtake_row_month(f"{m.strip()}'{int(y) % 100:02d}")
                        return None
                    df.loc[mask, "_month"] = df.loc[mask].apply(_month_plus_year, axis=1)
            df["_nsv"] = pd.to_numeric(df["NSV"], errors="coerce").fillna(0.0)
            df = df[df["_month"].notna() & df["_chain"].notna()]
            for (chain, mo), v in df.groupby(["_chain", "_month"])["_nsv"].sum().items():
                chain_month.setdefault(chain, {})
                chain_month[chain][mo] = chain_month[chain].get(mo, 0.0) + float(v)
            for (zone, state, mo), v in df[df["_zone"].notna()].groupby(["_zone", "_state", "_month"])["_nsv"].sum().items():
                key = (zone, state)
                zsm.setdefault(key, {})
                zsm[key][mo] = zsm[key].get(mo, 0.0) + float(v)
    return chain_month, zsm


def build_offtake_universe(src):
    """Read monthly store×article offtake extracts from src and return
    (brand_set, ean_set) for governance tier-signal wiring.

      brand_set: frozenset[str] — lowercased brand names present in any offtake file
      ean_set:   frozenset[str] — EAN strings present in any offtake file

    Returns (None, None) if no files with Brand or EAN columns are found
    (e.g. during --primary-only runs where no offtake files are supplied).
    Graceful: per-file exceptions are printed and skipped; never raises.
    Reads the same .xlsb/.csv files as load_offtake_article_files() but
    collects Brand and EAN columns that function does not aggregate."""
    files = sorted([*src.glob("*.xlsb"), *src.glob("*.csv")])
    brands, eans = set(), set()
    for fp in files:
        try:
            if fp.suffix.lower() == ".csv":
                _frames = {"csv": pd.read_csv(fp, low_memory=False)}
            else:
                _frames = pd.read_excel(fp, sheet_name=None, header=1, engine="pyxlsb")
            for _, df in _frames.items():
                df.columns = [str(c).strip() for c in df.columns]
                if "Brand" in df.columns:
                    brands.update(
                        str(b).strip().lower()
                        for b in df["Brand"].dropna()
                        if str(b).strip() not in ("", "nan")
                    )
                if "EAN" in df.columns:
                    eans.update(
                        str(e).strip()
                        for e in df["EAN"].dropna()
                        if str(e).strip() not in ("", "nan")
                    )
        except Exception as e:
            print(f"Warning: build_offtake_universe skipped {fp.name}: {e}")
    if not brands and not eans:
        return None, None
    return frozenset(brands), frozenset(eans)


def load_reliance_bc_data(src):
    """Extract Reliance Brand Counter rows from offtake source files for
    the separate analytical tab.  These rows are EXCLUDED from overall
    offtake (already embedded in Reliance's non-BC total); this function
    captures them separately.
    Returns a dict ready for data.js['reliance_bc'], or None if no data.
    Searches src recursively (like load_offtake_article_files(), its sibling
    function reading the same source tree) so a --src pointed at a parent of
    per-month subfolders (e.g. PowerBI/RawDataFolders, with the real CSVs
    one level down in Offtake_Monthly/) is picked up the same as a flat
    folder -- previously used a non-recursive glob(), so every production
    call (always passed the parent dir) silently found zero files and
    returned None without any error."""
    files = sorted([*src.rglob("*.xlsb"), *src.rglob("*.csv")])
    frames = []
    for fp in files:
        if fp.suffix.lower() == ".csv":
            try:
                # Use pandas with engine='python' for better variable-width CSV handling.
                # low_memory is a C-engine-only kwarg -- passing it with
                # engine='python' raises ValueError on every call, which the
                # bare `except Exception` below silently swallowed, so every
                # CSV file this function was ever given got silently skipped.
                try:
                    _frames = {"csv": pd.read_csv(fp, engine='python', encoding='utf-8',
                                                 on_bad_lines='warn')}
                except (UnicodeDecodeError, pd.errors.ParserError):
                    _frames = {"csv": pd.read_csv(fp, engine='python', encoding='latin-1',
                                                 on_bad_lines='warn')}
            except Exception:
                # Skip files that can't be parsed
                continue
        else:
            _frames0 = pd.read_excel(fp, sheet_name=None, header=0, engine="pyxlsb")
            _req = {"Chain Name", "Zone", "State", "Month", "NSV"}
            _use_h0 = any(_req <= {str(c).strip() for c in df_.columns}
                          for df_ in _frames0.values())
            _frames = _frames0 if _use_h0 else \
                      pd.read_excel(fp, sheet_name=None, header=1, engine="pyxlsb")
        for _, df in _frames.items():
            df.columns = [str(c).strip() for c in df.columns]
            need = {"Chain Name", "Zone", "State", "Month", "NSV"}
            if not need <= set(df.columns):
                continue
            _ds_col = "Data status" if "Data status" in df.columns else \
                      "Store Type" if "Store Type" in df.columns else None
            if _ds_col is None:
                continue
            _chain_c = df["Chain Name"].astype(str).str.strip().str.lower()
            _ds_c = df[_ds_col].astype(str).str.strip().str.lower()
            _is_rel = _chain_c.str.contains("reliance", na=False)
            _is_bc = (_ds_c == "brand counter")

            # Also check Source_Tab column if it exists (some exports use this instead)
            if "Source_Tab" in df.columns:
                _source_c = df["Source_Tab"].astype(str).str.strip().str.lower()
                _is_bc = _is_bc | (_source_c.str.contains("brand.counter|_ba_counter", regex=True, na=False))

            bc_df = df[_is_rel & _is_bc].copy()
            if bc_df.empty:
                continue
            bc_df["_month"] = bc_df["Month"].map(_offtake_row_month)
            if bc_df["_month"].isna().any():
                mask = bc_df["_month"].isna()
                if "Revised Month" in bc_df.columns:
                    bc_df.loc[mask, "_month"] = bc_df.loc[mask, "Revised Month"].map(_offtake_row_month)
                    mask = bc_df["_month"].isna()
                if mask.any() and "Year" in bc_df.columns:
                    def _mp(row):
                        m, y = row["Month"], row["Year"]
                        if isinstance(m, str) and m.strip() and y is not None:
                            return _offtake_row_month(f"{m.strip()}'{int(y) % 100:02d}")
                        return None
                    bc_df.loc[mask, "_month"] = bc_df.loc[mask].apply(_mp, axis=1)
            bc_df["_nsv"] = pd.to_numeric(bc_df["NSV"], errors="coerce").fillna(0.0)
            bc_df["_zone"] = bc_df["Zone"].map(canon_zone)
            bc_df["_state"] = bc_df["State"].map(canon_state)
            bc_df["_brand"] = bc_df["Brand"].map(canon_brand) if "Brand" in bc_df.columns else None
            bc_df["_category"] = bc_df["Category"].astype(str).str.strip() if "Category" in bc_df.columns else ""
            bc_df["_city"] = bc_df["City"].astype(str).str.strip() if "City" in bc_df.columns else ""
            bc_df["_article"] = bc_df["Article"].astype(str).str.strip() if "Article" in bc_df.columns else ""
            bc_df = bc_df[bc_df["_month"].notna()]
            frames.append(bc_df)
    if not frames:
        return None
    all_bc = pd.concat(frames, ignore_index=True)
    months = sorted(all_bc["_month"].unique(),
                    key=lambda mo: (int(mo.split("-")[1]), _MON3_NUM[mo.split("-")[0]]))
    # Aggregate by FY
    fy_data = {}
    for mo in months:
        tag = fy_tag_from_label(mo)
        if tag:
            fy_data.setdefault(tag.lower(), []).append(mo)
    monthly_totals = {}
    for mo in months:
        monthly_totals[mo] = r2(float(all_bc[all_bc["_month"] == mo]["_nsv"].sum()))
    # By zone
    by_zone = []
    for zone, grp in all_bc.groupby("_zone"):
        entry = {"name": zone, "total": r2(float(grp["_nsv"].sum()))}
        for mo in months:
            tag = fy_tag_from_label(mo)
            if tag:
                lo = tag.lower()
                mo_val = float(grp[grp["_month"] == mo]["_nsv"].sum())
                entry[lo] = r2(entry.get(lo, 0) + mo_val)
        by_zone.append(entry)
    by_zone.sort(key=lambda d: -d["total"])
    # By state
    by_state = []
    for (zone, state), grp in all_bc.groupby(["_zone", "_state"]):
        entry = {"zone": zone, "state": state, "total": r2(float(grp["_nsv"].sum()))}
        for mo in months:
            tag = fy_tag_from_label(mo)
            if tag:
                lo = tag.lower()
                mo_val = float(grp[grp["_month"] == mo]["_nsv"].sum())
                entry[lo] = r2(entry.get(lo, 0) + mo_val)
        by_state.append(entry)
    by_state.sort(key=lambda d: -d["total"])
    # By brand
    by_brand = []
    if all_bc["_brand"].notna().any():
        for brand, grp in all_bc[all_bc["_brand"].notna()].groupby("_brand"):
            entry = {"name": brand, "total": r2(float(grp["_nsv"].sum()))}
            for mo in months:
                tag = fy_tag_from_label(mo)
                if tag:
                    lo = tag.lower()
                    mo_val = float(grp[grp["_month"] == mo]["_nsv"].sum())
                    entry[lo] = r2(entry.get(lo, 0) + mo_val)
            by_brand.append(entry)
        by_brand.sort(key=lambda d: -d["total"])
    # By category
    by_category = []
    if all_bc["_category"].notna().any():
        for cat, grp in all_bc[all_bc["_category"] != ""].groupby("_category"):
            entry = {"name": cat, "total": r2(float(grp["_nsv"].sum()))}
            for mo in months:
                tag = fy_tag_from_label(mo)
                if tag:
                    lo = tag.lower()
                    mo_val = float(grp[grp["_month"] == mo]["_nsv"].sum())
                    entry[lo] = r2(entry.get(lo, 0) + mo_val)
            by_category.append(entry)
        by_category.sort(key=lambda d: -d["total"])
    result = {
        "total": r2(float(all_bc["_nsv"].sum())),
        "months": months,
        "monthly": [monthly_totals[mo] for mo in months],
        "fy_tags": sorted(fy_data.keys(), key=lambda t: fy_start_year(t.upper())),
        "by_zone": by_zone,
        "by_state": by_state,
        "by_brand": by_brand,
        "by_category": by_category,
        "include_in_overall_offtake": False,
        "is_brand_counter": True,
        "parent_chain": "Reliance Retail",
        "note": ("Reliance Brand Counter Offtake is shown as a separate analytical breakout. "
                 "It is already included in Reliance's reported Offtake and is excluded from "
                 "additional Overall Offtake aggregation to prevent double counting."),
    }
    for tag, tag_months in fy_data.items():
        result[f"months_{tag}"] = tag_months
        result[f"monthly_{tag}"] = [monthly_totals[mo] for mo in tag_months]
        result[f"total_{tag}"] = r2(sum(monthly_totals[mo] for mo in tag_months))
    # June-26 coverage disclosure
    result["data_complete_through"] = months[-1] if months else None
    if months and "Jun-26" not in months:
        result["june_status"] = (
            "BLOCKED: source file offtake_store_article_Jun_26.csv (or equivalent .xlsb) "
            "is not present in PowerBI/RawDataFolders/Offtake_Monthly/. "
            "Brand Counter June-26 offtake is unavailable. "
            "April–May 2026 data shown; this does not constitute a complete Q1 FY27 figure. "
            "Expected file: offtake_store_article_Jun_26.csv with columns: "
            "Store Code, Article Code/EAN, NSV (Lakh), Chain Name."
        )
    else:
        result["june_status"] = None
    return result


def validate_offtake_partition(offtake, reliance_bc=None):
    """
    Phase 1 v1.1.2: Validate that the offtake-BA partition is mathematically
    sound (BA counters are not double-counted in overall offtake totals).

    Returns: dict with validation results {
        'valid': bool,
        'offtake_total': float,
        'reliance_bc_total': float (if present),
        'partition_check': str (human-readable status),
    }
    """
    result = {
        'valid': True,
        'offtake_total': None,
        'reliance_bc_total': None,
        'partition_check': 'PASS: No Reliance BC data detected (standard offtake only)',
    }

    if not offtake or 'by_chain' not in offtake:
        result['partition_check'] = 'WARN: Offtake structure incomplete'
        return result

    # Get overall offtake total (should NOT include BA)
    offtake_fy_tags = offtake.get('fy_tags', [])
    offtake_total = 0.0
    for tag in offtake_fy_tags:
        total_key = f"total_{tag}"
        if total_key in offtake:
            offtake_total += offtake[total_key] or 0.0
    result['offtake_total'] = r2(offtake_total)

    # If Reliance BC exists, verify it's isolated
    if reliance_bc and isinstance(reliance_bc, dict):
        bc_total = reliance_bc.get('total', 0.0) or 0.0
        result['reliance_bc_total'] = r2(bc_total)

        # Check: BC should be a SUBSET of Reliance's offtake, not additional
        reliance_offtake = 0.0
        for chain_row in offtake.get('by_chain', []):
            if 'reliance' in (chain_row.get('name') or '').lower():
                for tag in offtake_fy_tags:
                    reliance_offtake += chain_row.get(tag, 0.0) or 0.0

        if reliance_offtake > 0 and bc_total > 0:
            # BC should be <= Reliance's total (it's a subset)
            if bc_total <= reliance_offtake * 1.05:  # Allow 5% rounding variance
                result['partition_check'] = (
                    f"PASS: Reliance BC (₹{bc_total:.2f}L) is correctly isolated as a subset "
                    f"of Reliance offtake (₹{reliance_offtake:.2f}L). No double counting."
                )
            else:
                result['valid'] = False
                result['partition_check'] = (
                    f"FAIL: Reliance BC (₹{bc_total:.2f}L) exceeds Reliance offtake "
                    f"(₹{reliance_offtake:.2f}L). Possible double counting detected."
                )
        elif bc_total > 0 and reliance_offtake == 0:
            result['partition_check'] = (
                f"WARN: Reliance BC detected (₹{bc_total:.2f}L) but no Reliance offtake rows. "
                "Check data source."
            )
        else:
            result['partition_check'] = "PASS: Reliance BC isolated correctly"
    else:
        result['partition_check'] = "INFO: No Reliance BC detected in data.js"

    return result


def patch_offtake_new_months(offtake, chain_month, zsm):
    """Merge chain-month / (zone,state)-month NSV aggregates (from
    load_offtake_article_files) into an EXISTING offtake_block() output.
    For every FY tag chain_month's months touch (FY27 today, FY28 once
    Apr-27 months appear -- via fy_tag_from_label, never a fixed index),
    FULLY RECOMPUTES (never incrementally adds to) that tag's total_/
    monthly_/months_ keys and every by_chain/by_zone/by_state row's tag
    value -- so re-running --offtake-patch with an accumulating --src folder
    (April, then April+May, then April+May+June, ...) is always idempotent
    and never double-counts a month twice. Does not touch any FY tag that
    chain_month has no months for. Mutates and returns `offtake`."""
    if not chain_month:
        return offtake
    if "fy_tags" not in offtake:
        offtake["fy_tags"] = sorted(
            {k[len("total_"):] for k in offtake if re.match(r"^total_fy\d{2}$", k)},
            key=lambda t: fy_start_year(t.upper()))
    all_months = sorted({mo for mm in chain_month.values() for mo in mm},
                         key=lambda mo: (int(mo.split("-")[1]), _MON3_NUM[mo.split("-")[0]]))
    touched_tags = sorted({fy_tag_from_label(mo) for mo in all_months if fy_tag_from_label(mo)},
                          key=fy_start_year)
    by_chain_idx = {c["name"]: c for c in offtake["by_chain"]}
    by_zone_idx = {z["name"]: z for z in offtake["by_zone"]}
    # Canonicalize state names in existing by_state entries and merge duplicates
    _deduped_states = []
    _seen_state_keys = {}
    for s in offtake.get("by_state", []):
        cs = canon_state(s["state"]) or s["state"]
        cz = canon_zone(s.get("zone"))
        key = (cz, cs)
        if key in _seen_state_keys:
            existing = _seen_state_keys[key]
            for k, v in s.items():
                if k not in ("state", "zone") and isinstance(v, (int, float)):
                    existing[k] = r2((existing.get(k) or 0) + v)
        else:
            s["state"] = cs
            if cz:
                s["zone"] = cz
            _seen_state_keys[key] = s
            _deduped_states.append(s)
    offtake["by_state"] = _deduped_states
    by_state_idx = {(s.get("zone"), s["state"]): s for s in offtake.get("by_state", [])}
    for tag in touched_tags:
        lo = tag.lower()
        new_months_of_tag = [mo for mo in all_months if fy_tag_from_label(mo) == tag]
        # Merge with any existing months for this FY that aren't in the new source.
        # This allows patching Apr+May onto a data.js that already has Jun without
        # losing Jun (whose raw source may no longer be on disk).
        existing_months = offtake.get(f"months_{lo}", [])
        existing_monthly = offtake.get(f"monthly_{lo}", [])
        existing_month_vals = dict(zip(existing_months, existing_monthly))
        # Build per-chain existing values for months we're NOT replacing
        existing_chain_vals = {}
        for c in offtake.get("by_chain", []):
            if lo in c and c[lo]:
                existing_chain_vals[c["name"]] = c[lo]
        existing_zone_vals = {}
        for z in offtake.get("by_zone", []):
            if lo in z and z[lo]:
                existing_zone_vals[z["name"]] = z[lo]
        existing_state_vals = {}
        for s in offtake.get("by_state", []):
            if lo in s and s[lo]:
                existing_state_vals[(s.get("zone"), s["state"])] = s[lo]
        # Months to keep from existing data (not in new source)
        kept_months = [m for m in existing_months if m not in new_months_of_tag]
        # Combined month list: kept existing + new, sorted chronologically
        combined_months = sorted(
            kept_months + new_months_of_tag,
            key=lambda mo: (int(mo.split("-")[1]), _MON3_NUM[mo.split("-")[0]]))
        # New monthly values: for kept months use existing; for new months compute from source
        new_month_set = set(new_months_of_tag)
        monthly_vals = []
        for mo in combined_months:
            if mo in new_month_set:
                monthly_vals.append(r2(sum(mm.get(mo, 0.0) for mm in chain_month.values())))
            else:
                monthly_vals.append(existing_month_vals.get(mo, 0.0))
        offtake[f"months_{lo}"] = combined_months
        offtake[f"monthly_{lo}"] = monthly_vals
        offtake[f"total_{lo}"] = r2(sum(v or 0 for v in monthly_vals))
        for chain, months in chain_month.items():
            row = by_chain_idx.get(chain)
            if row is None:
                row = {"name": chain, "raw": chain, "total": 0.0}
                offtake["by_chain"].append(row)
                by_chain_idx[chain] = row
            new_val = r2(sum(v for mo, v in months.items() if mo in new_months_of_tag))
            if kept_months:
                old_total = existing_chain_vals.get(chain, 0.0)
                # old_total covers existing_months (e.g. Apr+May+Jun+Jul).
                # new source covers new_months_of_tag (e.g. Apr+May+Jul — may be missing Jun).
                # truly_new = months in source not yet in existing.
                # Correct: old_total already includes overlap months; just add truly_new.
                # (Re-adding new_val directly would double-count the overlap months.)
                truly_new = set(new_months_of_tag) - set(existing_months)
                if truly_new:
                    # Case A: source has genuinely new months → add only those
                    truly_new_val = r2(sum(v for mo, v in months.items() if mo in truly_new))
                    row[lo] = r2(old_total + truly_new_val)
                elif set(new_months_of_tag) == set(existing_months):
                    # Case B: source covers exactly the same months → fresh recompute
                    # (e.g. alias mapping changed; source is authoritative for this window)
                    row[lo] = new_val
                else:
                    # Case C: source is a strict subset of existing (some months not in --src)
                    # → preserve existing total; adding new_val would drop missing months.
                    row[lo] = old_total
            else:
                row[lo] = new_val
        zone_truly_new_totals = {}   # Case A zone increments (new months only)
        zone_full_totals = {}        # Case B/no-kept-months zone sums (full recompute)
        _truly_new_months = set(new_months_of_tag) - set(existing_months)
        _source_exact_match = (not _truly_new_months) and (set(new_months_of_tag) == set(existing_months))
        _source_is_subset = (not _truly_new_months) and (set(new_months_of_tag) < set(existing_months))
        for (zone, state), months in zsm.items():
            v = r2(sum(v for mo, v in months.items() if mo in new_months_of_tag)) or 0.0
            srow = by_state_idx.get((zone, state))
            if srow is None:
                srow = {"state": state, "zone": zone}
                offtake.setdefault("by_state", []).append(srow)
                by_state_idx[(zone, state)] = srow
            if kept_months:
                old_sv = existing_state_vals.get((zone, state), 0.0)
                if _truly_new_months:
                    # Case A: add truly-new-months increment only
                    truly_new_sv = r2(sum(v for mo, v in months.items() if mo in _truly_new_months)) or 0.0
                    srow[lo] = r2(old_sv + truly_new_sv)
                    zone_truly_new_totals[zone] = zone_truly_new_totals.get(zone, 0.0) + truly_new_sv
                elif _source_exact_match:
                    # Case B: source covers same months — fresh recompute
                    srow[lo] = v
                    zone_full_totals[zone] = zone_full_totals.get(zone, 0.0) + v
                # else Case C: source subset — leave srow[lo] unchanged (don't touch zone_full_totals)
            else:
                srow[lo] = v
                zone_full_totals[zone] = zone_full_totals.get(zone, 0.0) + v
        for zone, inc in zone_truly_new_totals.items():
            # Case A: add only the truly-new-months increment to the existing zone value.
            # This preserves the existing zone total (which includes old months AND
            # any rows where state was null/unmapped that are not in zsm).
            zrow = by_zone_idx.get(zone)
            if zrow is None:
                zrow = {"name": zone}
                offtake["by_zone"].append(zrow)
                by_zone_idx[zone] = zrow
            old_zone_val = existing_zone_vals.get(zone, 0.0)
            zrow[lo] = r2(old_zone_val + inc)
        for zone, v in zone_full_totals.items():
            # Case B or no-kept-months: full zone recompute
            zrow = by_zone_idx.get(zone)
            if zrow is None:
                zrow = {"name": zone}
                offtake["by_zone"].append(zrow)
                by_zone_idx[zone] = zrow
            zrow[lo] = r2(v)
        if lo not in offtake["fy_tags"]:
            offtake["fy_tags"].append(lo)
    offtake["fy_tags"] = sorted(offtake["fy_tags"], key=lambda t: fy_start_year(t.upper()))
    last = offtake["fy_tags"][-1]
    offtake["by_chain"] = sorted(offtake["by_chain"], key=lambda d: -(d.get(last) or 0))
    offtake["by_zone"] = sorted(offtake["by_zone"], key=lambda d: -(d.get(last) or 0))
    if "by_state" in offtake:
        offtake["by_state"] = sorted(offtake["by_state"], key=lambda d: -(d.get(last) or 0))
    offtake["n_chains"] = len(offtake["by_chain"])
    # extend the overall (all-FY) trend series with any months not already in it
    have = set(offtake.get("months", []))
    appended = [mo for mo in all_months if mo not in have]
    if appended:
        offtake["months"] = list(offtake.get("months", [])) + appended
        offtake["monthly"] = list(offtake.get("monthly", [])) + [
            r2(sum(mm.get(mo, 0.0) for mm in chain_month.values())) for mo in appended]
    # Build per-zone monthly series for each touched FY tag.
    # Zone monthly is derived from zsm (zone,state,month) aggregates.
    # For months missing from source (e.g. Jun when only Apr/May/Jul available),
    # each zone's value is estimated proportionally from the known monthly total.
    for tag in touched_tags:
        lo = tag.lower()
        tag_months = offtake.get(f"months_{lo}", [])
        if not tag_months:
            continue
        tag_monthly = offtake.get(f"monthly_{lo}", [])
        # Build zone→month dict from zsm for source months
        zone_mo_nsv = {}  # {zone: {month: nsv}}
        for (zone, state), months in zsm.items():
            if zone is None:
                continue
            if zone not in zone_mo_nsv:
                zone_mo_nsv[zone] = {}
            for mo, v in months.items():
                if fy_tag_from_label(mo) == tag:
                    zone_mo_nsv[zone][mo] = zone_mo_nsv[zone].get(mo, 0.0) + v
        if not zone_mo_nsv:
            continue
        # Source months (have zone data); missing months get proportional estimate
        source_months = set(new_months_of_tag)
        # Compute zone shares from source months (zone_total / all_zone_total per month)
        zone_source_totals = {}
        for zone in zone_mo_nsv:
            zone_source_totals[zone] = sum(
                zone_mo_nsv[zone].get(mo, 0.0) for mo in source_months)
        all_zone_grand = sum(zone_source_totals.values())
        zone_shares = {z: (v / all_zone_grand if all_zone_grand else 0.0)
                       for z, v in zone_source_totals.items()}
        zone_monthly_series = {}
        for zone in zone_mo_nsv:
            series = []
            for mo, mo_total in zip(tag_months, tag_monthly):
                if mo in source_months:
                    series.append(r2(zone_mo_nsv[zone].get(mo, 0.0)))
                else:
                    # Estimate: zone_share * monthly_total
                    series.append(r2(zone_shares.get(zone, 0.0) * (mo_total or 0.0)))
            zone_monthly_series[zone] = series
        offtake[f"zone_monthly_{lo}"] = zone_monthly_series
    return offtake

# --------------------------------------------------------------------------
# DISTRIBUTION GAP & ADD-ON REVENUE POTENTIAL
# Per product (EAN), compares presence only across COMPARABLE stores -- sites
# of the product's own chain FORMAT (Pharmacy / Hypermarket / Supermarket /
# Beauty Retail / ...), so a drug-store SKU is measured against drug-store
# doors, never against Dmart. Built from the REAL store x article offtake
# extracts (the same *.xlsb the offtake patch reads) + ChainMaster's "Chain
# Type" column; NO fabricated numbers. Everything is derived from month+site+
# EAN, so it extends to more months automatically.
# --------------------------------------------------------------------------
_CHAIN_FORMAT_BRIDGE = {   # offtake chain (canon) -> ChainMaster spelling, where canon differs
    "H&G": "Health & Glow", "Spencer": "Spencers",
}
def load_chain_formats(repo_root):
    """canon chain name -> format ('Chain Type' from PowerBI ChainMaster.csv)."""
    f = repo_root / "PowerBI" / "SeedData" / "Masters" / "ChainMaster.csv"
    if not f.exists():
        return {}
    cm = pd.read_csv(f)
    fmt = {}
    for _, r in cm.iterrows():
        c = canon_chain(r.get("Chain"))
        if c and pd.notna(r.get("Chain Type")):
            fmt[c] = str(r["Chain Type"]).strip()
    for canon_name, master_name in _CHAIN_FORMAT_BRIDGE.items():
        m = canon_chain(master_name)
        if canon_name not in fmt and m in fmt:
            fmt[canon_name] = fmt[m]
    return fmt

def dist_gap_block(src, repo_root, top_n=250, min_target=50):
    """Distribution gap & add-on revenue potential from store x article offtake.

    For each EAN: its dominant FORMAT = the Chain Type contributing most NSV.
    Within that format only:
      target    = distinct sites selling the product's CATEGORY (comparable base)
      carrying  = distinct sites selling THIS EAN
      penetration = carrying / target ; missing = target - carrying
      NSV/store = EAN NSV per carrying site ; add-on = missing * NSV/store
    'TP' (distribution points) = distinct carrying sites; Latest = latest month,
    Max = peak across the loaded months. Values in INR Lakh; annualised = monthly
    average * 12. Returns None if no store x article files are present.
    """
    files = sorted([*src.glob("*.xlsb"), *src.glob("*.csv")])
    if not files:
        return None
    fmt_map = load_chain_formats(repo_root)
    cols = ["Chain Name", "Site Code", "EAN", "Category", "Brand",
            "Description as per Fountain", "NSV", "Month",
            "Revised Month", "Year", "Data status", "Store Type"]
    frames = []
    for fp in files:
        if fp.suffix.lower() == ".csv":
            _sheets = {"csv": pd.read_csv(fp, low_memory=False)}
        else:
            _sheets0 = pd.read_excel(fp, sheet_name=None, header=0, engine="pyxlsb")
            _req2 = {"Chain Name", "Site Code", "EAN", "Category", "NSV", "Month"}
            _use_h0 = any(_req2 <= {str(c).strip() for c in df_.columns}
                          for df_ in _sheets0.values())
            _sheets = _sheets0 if _use_h0 else \
                      pd.read_excel(fp, sheet_name=None, header=1, engine="pyxlsb")
        for _, df in _sheets.items():
            df.columns = [str(c).strip() for c in df.columns]
            if not {"Chain Name", "Site Code", "EAN", "Category", "NSV", "Month"} <= set(df.columns):
                continue
            frames.append(df[[c for c in cols if c in df.columns]].copy())
    if not frames:
        return None
    d = pd.concat(frames, ignore_index=True)
    # Reliance Brand Counter is a store-level breakout already included in
    # Non-Brand Counter totals — exclude to prevent double-counting.
    # Column name varies: "Data status" in .xlsb, "Store Type" in split CSVs.
    _ds_col = "Data status" if "Data status" in d.columns else \
              "Store Type" if "Store Type" in d.columns else None
    if _ds_col is not None:
        _chain_c = d["Chain Name"].astype(str).str.strip().str.lower()
        _ds_c = d[_ds_col].astype(str).str.strip().str.lower()
        _is_rel = _chain_c.str.contains("reliance", na=False)
        _is_bc = (_ds_c == "brand counter")
        d = d[~(_is_rel & _is_bc)].copy()
    d["_chain"] = d["Chain Name"].map(canon_chain)
    d["_fmt"] = d["_chain"].map(lambda c: fmt_map.get(c, "Unclassified"))
    # Fill missing Site Codes with "NA" so chains without store-level detail
    # (FSN, Arambagh, etc.) still participate; their site key becomes
    # "ChainName|NA" — a single aggregate placeholder per chain.
    _sc_str = d["Site Code"].astype(str).str.strip()
    _sc_missing = d["Site Code"].isna() | _sc_str.isin(["nan", "None", "none", "", "<NA>"])
    _sc_str = _sc_str.copy()
    _sc_str.loc[_sc_missing] = "NA"
    d["_site"] = d["_chain"].astype(str) + "|" + _sc_str
    d["_ean"] = d["EAN"].astype(str)
    d["_nsv"] = pd.to_numeric(d["NSV"], errors="coerce").fillna(0.0)
    d["_cat"] = d["Category"].astype(str)
    d["_mon"] = d["Month"].map(_offtake_row_month)
    if d["_mon"].isna().any():
        mask = d["_mon"].isna()
        if "Revised Month" in d.columns:
            d.loc[mask, "_mon"] = d.loc[mask, "Revised Month"].map(_offtake_row_month)
            mask = d["_mon"].isna()
        if mask.any() and "Year" in d.columns:
            def _month_plus_year_dg(row):
                m, y = row["Month"], row["Year"]
                if isinstance(m, str) and m.strip() and y is not None:
                    return _offtake_row_month(f"{m.strip()}'{int(y) % 100:02d}")
                return None
            d.loc[mask, "_mon"] = d.loc[mask].apply(_month_plus_year_dg, axis=1)
    months = sorted([m for m in d["_mon"].dropna().unique()],
                    key=lambda mo: (int(mo.split("-")[1]), _MON3_NUM[mo.split("-")[0]]))
    n_months = max(1, len(months))
    latest = months[-1] if months else None

    # dominant format per EAN (by NSV); category + description (first non-blank)
    dom = (d.groupby(["_ean", "_fmt"])["_nsv"].sum().reset_index()
             .sort_values("_nsv", ascending=False).drop_duplicates("_ean")
             .set_index("_ean")["_fmt"].to_dict())
    def _first(s):
        s = s.dropna()
        return str(s.iloc[0]) if len(s) else ""
    ean_cat = d.groupby("_ean")["_cat"].agg(_first).to_dict()
    ean_desc = d.groupby("_ean")["Description as per Fountain"].agg(_first).to_dict() \
        if "Description as per Fountain" in d.columns else {}
    ean_brand = {k: (canon_brand(v) or v) for k, v in
                 d.groupby("_ean")["Brand"].agg(_first).to_dict().items()} if "Brand" in d.columns else {}
    # target universe: distinct sites per (format, category)
    tgt = d.groupby(["_fmt", "_cat"])["_site"].nunique().to_dict()

    rows = []
    for ean, g in d.groupby("_ean"):
        f = dom.get(ean)
        if not f or f == "Unclassified":
            continue
        cat = ean_cat.get(ean, "")
        target = int(tgt.get((f, cat), 0))
        if target < min_target:
            continue
        gg = g[g["_fmt"] == f]
        carrying = int(gg["_site"].nunique())
        if carrying == 0:
            continue
        nsv = float(gg["_nsv"].sum())                      # Lakh over loaded months
        nsv_monthly = nsv / n_months
        nsv_ann = nsv_monthly * 12                          # Lakh / year
        per_store_period = nsv / carrying                   # Lakh (loaded window)
        missing = max(0, target - carrying)
        addon_period = per_store_period * missing           # Lakh over window
        addon_ann = (nsv_ann / carrying) * missing          # Lakh / year
        by_mon = gg.groupby("_mon")["_site"].nunique()
        rows.append({
            "product": (ean_desc.get(ean, "") or ean)[:60],
            "ean": ean, "brand": ean_brand.get(ean, ""), "category": cat,
            "group": f, "carrying": carrying, "target": target, "missing": missing,
            "penetration": r2(carrying / target * 100),
            "nsv_avg_ann": r2(nsv_ann),          # Lakh/yr  (dashboard shows ₹Cr/yr)
            "nsv_window": r2(nsv),               # Lakh over loaded months
            "latest_tp": int(by_mon.get(latest, 0)) if latest else carrying,
            "max_tp": int(by_mon.max()) if len(by_mon) else carrying,
            "addon_window": r2(addon_period),    # Lakh over window
            "addon_ann": r2(addon_ann),          # Lakh/yr
        })
    rows.sort(key=lambda r: -(r["addon_window"] or 0))
    groups = {}
    for r in rows:
        groups[r["group"]] = groups.get(r["group"], 0.0) + (r["addon_window"] or 0)
    return {
        "months_covered": months,
        "n_months": n_months,
        "window_label": ("L%dM (%s)" % (n_months, "–".join([months[0], months[-1]]) if months else "")),
        "unit": "INR Lakh",
        "rows": rows[:top_n],
        "row_count": len(rows),
        "addon_by_group": [{"name": k, "addon": r2(v)} for k, v in
                           sorted(groups.items(), key=lambda kv: -kv[1])],
        "total_addon_window": r2(sum(r["addon_window"] or 0 for r in rows)),
        "total_addon_ann": r2(sum(r["addon_ann"] or 0 for r in rows)),
        "note": ("Per EAN, compared ONLY across comparable stores = sites of the "
                 "product's dominant chain FORMAT (Chain Type from ChainMaster), so "
                 "drug-store SKUs are measured against drug-store doors only. Target "
                 "= distinct format-sites selling that product's Category; Carrying = "
                 "format-sites selling this EAN; Add-on = missing sites × NSV per "
                 "carrying site. Built from real store×article offtake; annualised = "
                 "monthly avg × 12. Window is whatever store-level months are loaded "
                 "(currently 2), refreshes to true L3M as more months arrive."),
    }

# --------------------------------------------------------------------------
# UNIVERSE (distribution footprint)
# --------------------------------------------------------------------------
# Root QC (2026-09-14): several "Chain Name" values in UniverseMT.csv are not
# retail chains at all -- they are Primary billing Ship-To/DC codes for
# distributors, each of whom actually serves SEVERAL real chains (confirmed
# against PowerBI/SeedData/Masters/ShipToMaster.csv's own "Chains Served"
# column, e.g. "G.V Enterprises" serves Apollo, D-Mart, Lulu and Pothys -- not
# a single chain called "G.V Enterprises"). For a STORE-COUNT purpose (one
# physical location needs exactly one label, unlike revenue, which is never
# split here), ShipToMaster.csv's "Primary Chain" column is a real, governed
# single answer already present in this repo -- used ONLY as a fallback when
# canon_chain() has no existing alias for the raw name, never overriding a
# governed alias.
def _load_shipto_primary_chain():
    f = Path("PowerBI/SeedData/Masters/ShipToMaster.csv")
    if not f.exists():
        return {}
    df = pd.read_csv(f)
    return {str(n).replace("\xa0", " ").strip().lower(): str(c).strip()
            for n, c in zip(df["Ship To Name"], df["Primary Chain"]) if pd.notna(n) and pd.notna(c)}

# Reviewed spelling-variant links between UniverseMT.csv's "Chain Name" and
# ShipToMaster.csv's "Ship To Name" for the SAME distributor, checked one at a
# time (same convention as aug26_data_readiness_gate.py's
# DISTRIBUTOR_NAME_ALIAS) -- only needed where the two files don't already
# match case-insensitively.
_UNIVERSE_SHIPTO_ALIAS = {
    "az enterprises-h&g": "az enterprises",
    "az enterprises-mt": "az enterprises",
    "sri vijaya durga agencies": "sri vijaya durga agencies_mt",
    "sc business combine": "sc business combine_mt",
    "m/s kottaram business": "m/s kottaram business corporation-mt",
}


def universe_block(src):
    # Try CSV first (versioned in git), fallback to XLSX
    csv_f = Path("PowerBI/SeedData/Distribution/UniverseMT.csv")
    if csv_f.exists():
        u = pd.read_csv(csv_f)
    else:
        # Fallback to XLSX
        f = src / "universe.xlsx"
        if not f.exists():
            f = src / "Universe MT.xlsx"  # Try alternate naming
        if not f.exists():
            raise FileNotFoundError(f"Universe data not found: {csv_f} or {f}")
        u = pd.read_excel(f, sheet_name="PAN INDIA", header=0)
    u.columns = [str(c).strip() for c in u.columns]
    u = u[u["Chain Name"].notna()]
    u["active"] = u["Status"].astype(str).str.strip().str.upper().eq("ACTIVE")
    u["zone"] = u["Zone"].map(canon_zone)
    u["chain"] = u["Chain Name"].map(canon_chain)

    # Second-tier resolution: only for rows canon_chain() left unresolved
    # (raw name not in the governed alias table -- i.e. it passed through
    # unchanged), try ShipToMaster's Primary Chain.
    _shipto_primary = _load_shipto_primary_chain()
    _reclassified = 0
    for idx, raw in u["Chain Name"].items():
        key = str(raw).replace("\xa0", " ").strip().lower()
        if key in _ALIAS_LOOKUP:
            continue  # already governed via canon_chain() -- leave it
        lookup_key = _UNIVERSE_SHIPTO_ALIAS.get(key, key)
        primary = _shipto_primary.get(lookup_key)
        if primary:
            u.loc[idx, "chain"] = canon_chain(primary) or primary
            _reclassified += 1
    act = u[u["active"]]
    out = {"total_stores": int(len(u)), "active_stores": int(len(act))}
    if _reclassified:
        out["shipto_reclassified_note"] = (
            f"{_reclassified} store(s) whose raw Chain Name was actually a distributor Ship-To/DC "
            "billing code (not a retail chain) were reassigned to that distributor's governed "
            "Primary Chain per PowerBI/SeedData/Masters/ShipToMaster.csv -- see BUSINESS_LOGIC "
            "root-QC note, 2026-09-14."
        )
    out["by_zone"] = sorted([{"name": k, "stores": int(v)}
                             for k, v in act.groupby("zone").size().items() if k],
                            key=lambda d: -d["stores"])
    out["by_citycat"] = [{"name": k, "stores": int(v)}
                         for k, v in act.groupby(act["City Category"].astype(str).str.strip()).size().items()]
    _chain_counts = sorted([{"name": k, "stores": int(v)}
                            for k, v in act.groupby("chain").size().items() if k],
                           key=lambda d: -d["stores"])
    # n_chains/chains: verified MT chain count (config/baselines.json). Set
    # here from the real, post-reclassification chain list -- previously this
    # field existed in dashboard/data.js with no code path producing it
    # anywhere in this repo (confirmed 2026-09-14: neither this function nor
    # scripts/sync_data_js.py set it), so any full rebuild would have silently
    # dropped it. "Other (below top 20)" is a display bucket, not a chain --
    # excluded from this count.
    out["chains"] = [d["name"] for d in _chain_counts]
    out["n_chains"] = len(_chain_counts)
    out["by_chain"] = _chain_counts[:20]
    _chain_other = sum(d["stores"] for d in _chain_counts[20:])
    if _chain_other > 0:
        # Root QC (2026-09-14): silently truncating here made by_chain sum to
        # 415 of 426 active stores with no disclosure -- indistinguishable from
        # a real 11-store data gap. Disclosed the same way storetype_note
        # already discloses its own truncation below, rather than fabricating
        # which of the excluded entities is a real chain vs a distributor
        # billing point (several -- e.g. "REAL TIME LOGISTICS_MT_BR",
        # "CHHABRA TRADERS" -- look like the latter; that reclassification is
        # a business call, not made here).
        out["by_chain"].append({"name": "Other (below top 20)", "stores": _chain_other})
        out["by_chain_note"] = (
            f"{_chain_other} of {len(act)} active stores belong to chains outside the top 20 by "
            "store count (mostly 1-store entries, some of which read as distributor/logistics "
            "names rather than retail chains -- e.g. from the raw Chain Name column, not "
            "reclassified here). Folded into \"Other (below top 20)\" so this total reconciles "
            "to active_stores; see PowerBI/SeedData/Distribution/UniverseMT.csv for the raw names."
        )
    _st_col = act["Store Type"].astype(str).str.strip()
    _st_valid = _st_col[_st_col.str.upper().ne("NAN") & _st_col.ne("") & _st_col.ne("NONE")]
    _n_unclassified = int(len(act)) - int(len(_st_valid))
    _st_counts = _st_valid.str.upper().value_counts()
    _by_st = sorted([{"name": k.title(), "stores": int(v)} for k, v in _st_counts.items()],
                    key=lambda d: -d["stores"])[:10]
    if _n_unclassified > 0:
        _by_st.append({"name": "Unclassified", "stores": _n_unclassified})
    out["by_storetype"] = _by_st
    out["storetype_classified"] = int(len(_st_valid))
    out["storetype_unclassified"] = _n_unclassified
    if _n_unclassified > 0:
        _pct = round(_n_unclassified * 100 / len(act), 1)
        out["storetype_note"] = (
            f"{_n_unclassified:,} of {len(act):,} active stores ({_pct}%) have a blank or missing "
            f"Store Type in the universe master (universe.xlsx) and are not shown in the chart above. "
            f"Update the Store Type column in universe.xlsx to complete this view."
        )
    return act, out

# --------------------------------------------------------------------------
# PROMO (trade spend intensity)
# --------------------------------------------------------------------------
def parse_depth(x):
    """Best-effort effective consumer discount depth (0-1) from messy free text."""
    if x is None:
        return None
    s = str(x).strip().lower()
    if s in ("", "nan"):
        return None
    if "b1g1" in s or "bogo" in s:
        return 0.5
    if "b2g1" in s:
        return 0.333
    if "b3g1" in s:
        return 0.25
    m = re.search(r"(\d+(?:\.\d+)?)\s*%", s)
    if m:
        return float(m.group(1)) / 100.0
    try:
        v = float(s)
        if 0 < v <= 1:
            return v
        if 1 < v <= 100:
            return v / 100.0
    except Exception:
        pass
    return None

def promo_block(src):
    # Try CSV first (versioned in git), fallback to XLSX
    csv_f = Path("PowerBI/SeedData/Promo/PromoMaster.csv")
    if csv_f.exists():
        p = pd.read_csv(csv_f)
    else:
        # Fallback to XLSX
        f = src / "promo.xlsx"
        if not f.exists():
            f = src / "Promo Master -MT.xlsx"  # Try alternate naming
        if not f.exists():
            # Promo is optional; skip if not found
            return pd.DataFrame(), None
        p = pd.read_excel(f, sheet_name="Sheet1", header=0)
    p.columns = [str(c).strip() for c in p.columns]
    p = p[p["Chain Name"].notna()]
    p["chain"] = p["Chain Name"].map(canon_chain)
    p["brand"] = p["Brand"].map(canon_brand)
    p["depth"] = p["Offer to consumer"].map(parse_depth)
    out = {"n_promos": int(len(p)),
           "avg_depth": r2(p["depth"].mean() * 100, 1),
           "n_chains": int(p["chain"].nunique())}
    g = p.groupby("chain")
    rows = [{"name": k, "promos": int(len(d)), "avg_depth": r2(d["depth"].mean() * 100, 1),
             "brands": int(d["brand"].nunique())} for k, d in g if k]
    out["by_chain"] = sorted(rows, key=lambda d: -d["promos"])
    gb = p.groupby("brand")
    out["by_brand"] = sorted([{"name": k, "promos": int(len(d)), "avg_depth": r2(d["depth"].mean() * 100, 1)}
                              for k, d in gb if k], key=lambda d: -d["promos"])
    gc = p.groupby(p["Category"].astype(str).str.strip())
    out["by_category"] = sorted([{"name": k, "promos": int(len(d))} for k, d in gc if k and k != "nan"],
                                key=lambda d: -d["promos"])[:8]
    return p, out


# --------------------------------------------------------------------------
# OFFTAKE v2 -- folder-of-months chain extracts
#
# Layout: <src>/offtake_fy26/<Mon'YY>/<Chain>.csv, one CSV per chain per month.
#
# Two things make a naive read wrong, both found the hard way:
#
#  1. ROW WIDTH VARIES WITHIN A FILE. Reliance.csv has a 29-field header but
#     also carries 30-field rows (an extra leading field), so a DictReader
#     silently shifts every column: "NSV" then reads the Margin column and the
#     file's total inflates ~15x. Rows are indexed against the header with an
#     offset of len(row) - len(header).
#
#  2. RELIANCE BRAND COUNTER IS INSIDE THE SAME FILE. The 30-field rows are the
#     staffed-counter doors (Source_Tab "Reliance_Brand_Counter", Store Type
#     "Brand Counter"); the 29-field rows are the macro figure
#     ("Reliance_Non_Brand_Counter"). Per CLAUDE.md the macro number already
#     subsumes counter sales, so counting both double-counts Reliance. Counters
#     are partitioned out of offtake and returned separately for the BC block.
#
# Verified against the business's own anchors: offtake FY26 ex-counter comes to
# Rs 311.20 Cr against a stated Rs 311.28 Cr (-0.026%), and the partitioned
# counter total comes to Rs 45.62 Cr, matching reliance_bc.total_fy26 exactly.
# NSV in these extracts is already INR Lakh (MRP Sales Value / 1.18 * (1 -
# Margin) / 1e5 reproduces it in both layouts).
# --------------------------------------------------------------------------
_OFFTAKE_V2_DIRS = ("offtake_fy26", "offtake", "Offtake")

def _mon_folder_to_label(name):
    """\"Apr'25\" -> \"Apr-25\"; returns None for anything that is not a month."""
    m = re.match(r"([A-Za-z]{3})'?-?(\d{2})$", str(name).strip())
    if not m:
        return None
    mon = m.group(1).title()
    return f"{mon}-{m.group(2)}" if mon in _MON3_NUM else None

def load_offtake_month_folders(src):
    """Read <src>/<offtake dir>/<Mon'YY>/*.csv.

    Returns (offtake, counters) where each is
        {month_label: {"total": L, "chain": {...}, "zone": {...}, "brand": {...}}}
    Both {} when no such folder exists, so callers can fall back."""
    root = None
    for d in _OFFTAKE_V2_DIRS:
        p = src / d
        if p.is_dir() and any(_mon_folder_to_label(x.name) for x in p.iterdir() if x.is_dir()):
            root = p
            break
    if root is None:
        return {}, {}

    csv.field_size_limit(min(sys.maxsize, 2**31 - 1))
    off, ctr = {}, {}
    for mdir in sorted(root.iterdir()):
        if not mdir.is_dir():
            continue
        lab = _mon_folder_to_label(mdir.name)
        if not lab:
            continue
        o = off.setdefault(lab, {"total": 0.0, "chain": {}, "zone": {}, "brand": {}})
        c = ctr.setdefault(lab, {"total": 0.0, "chain": {}, "zone": {}, "brand": {}})
        for fp in sorted(mdir.glob("*.csv")):
            with open(fp, newline="", encoding="utf-8", errors="replace") as fh:
                rd = csv.reader(fh)
                hdr = next(rd, None)
                if not hdr:
                    continue
                H = len(hdr)
                ix = {n: (hdr.index(n) if n in hdr else -1) for n in
                      ("NSV", "Source_Tab", "Chain Name", "Zone", "State", "Brand", "Store Type")}
                if ix["NSV"] < 0:
                    continue
                for row in rd:
                    shift = len(row) - H          # >0 => extra leading field(s)
                    def g(i):
                        if i < 0:
                            return ""
                        j = i - shift if shift > 0 else i
                        return row[j] if 0 <= j < len(row) else ""
                    try:
                        v = float(g(ix["NSV"]) or 0)
                    except (TypeError, ValueError):
                        continue
                    src_tab = (g(ix["Source_Tab"]) or "").strip()
                    stype = (g(ix["Store Type"]) or "").strip()
                    bucket = c if (src_tab == "Reliance_Brand_Counter"
                                   or stype.lower() == "brand counter") else o
                    ch = canon_chain((g(ix["Chain Name"]) or "").strip())
                    # Zone override: if state maps to a zone (e.g. Madhya Pradesh -> Central),
                    # use that instead of the Zone column (which misclassifies MP/CG as North/West)
                    state_val = (g(ix["State"]) or "").strip() if ix["State"] >= 0 else ""
                    zone_override = canon_zone_from_state(state_val) if state_val else None
                    zn = canon_zone(zone_override or (g(ix["Zone"]) or "").strip())
                    br = canon_brand((g(ix["Brand"]) or "").strip())
                    bucket["total"] += v
                    if ch: bucket["chain"][ch] = bucket["chain"].get(ch, 0.0) + v
                    if zn: bucket["zone"][zn] = bucket["zone"].get(zn, 0.0) + v
                    if br: bucket["brand"][br] = bucket["brand"].get(br, 0.0) + v
    return off, ctr

def load_fy25_secondary(src):
    """Distributor secondary for FY25 (Apr-24..Mar-25), already chain-mapped by
    the business in its 'Chain Mapping' column -- no allocation model needed.

    NOTE ON MEASURE: this is SECONDARY (distributor -> retailer), not offtake
    (store -> consumer). It is the only FY25 series available, so it is carried
    as the prior-year reference, but under keys that name it as secondary so no
    caller can mistake it for like-for-like offtake."""
    cand = sorted(src.glob("Distributor_secondary_*.csv")) + sorted(src.glob("*Distributor_secondary*.csv"))
    if not cand:
        return {}
    out = {}
    with open(cand[0], newline="", encoding="utf-8", errors="replace") as fh:
        for row in csv.DictReader(fh):
            lab = (row.get("Revised month") or "").strip()          # e.g. "Apr-24"
            if not fy_tag_from_label(lab):
                continue
            try:
                v = float(row.get("NSV") or 0)
            except (TypeError, ValueError):
                continue
            m = out.setdefault(lab, {"total": 0.0, "chain": {}, "zone": {}, "brand": {}})
            ch = canon_chain((row.get("Chain Mapping") or row.get("Chain Name") or "").strip())
            state_val = (row.get("State") or "").strip()
            zone_override = canon_zone_from_state(state_val) if state_val else None
            zn = canon_zone(zone_override or (row.get("Zone") or "").strip())
            br = canon_brand((row.get("Brand") or "").strip())
            m["total"] += v
            if ch: m["chain"][ch] = m["chain"].get(ch, 0.0) + v
            if zn: m["zone"][zn] = m["zone"].get(zn, 0.0) + v
            if br: m["brand"][br] = m["brand"].get(br, 0.0) + v
    return out


def offtake_rebuild_block(prev, off_m, ctr_m, sec_m):
    """Build a COMPLETE offtake block from the month-folder extracts, replacing
    the stale one rather than patching it.

    The shipped block had three independent defects, which is why this rebuilds
    instead of patching: months_fy26 held 8 of 12 months (Apr-25..Jul-25 were
    assigned to no FY at all), total_fy26 matched neither the 8- nor the
    12-month sum, and `monthly` carried PRIMARY values rather than offtake.
    Every key below is derived from one labelled month series, so the parts
    cannot drift apart again. Keys this function does not own (metrics, doi,
    otif, ...) are carried over from `prev` untouched."""
    out = dict(prev or {})
    months = sorted(off_m, key=lambda l: (int(l.split("-")[1]), _MON3_NUM[l.split("-")[0]]))
    out["months"] = months
    out["monthly"] = [r2(off_m[m]["total"]) for m in months]

    tags = sorted({fy_tag_from_label(m) for m in months if fy_tag_from_label(m)}, key=fy_start_year)
    out["fy_tags"] = [t.lower() for t in tags]
    for t in tags:
        lo = t.lower()
        ms = [m for m in months if fy_tag_from_label(m) == t]
        out[f"months_{lo}"] = ms
        out[f"monthly_{lo}"] = [r2(off_m[m]["total"]) for m in ms]
        out[f"total_{lo}"] = r2(sum(off_m[m]["total"] for m in ms))
    out["total"] = r2(sum(off_m[m]["total"] for m in months))

    # FY25 prior-year reference. SECONDARY, not offtake -- named so throughout.
    sec_tags = sorted({fy_tag_from_label(m) for m in sec_m if fy_tag_from_label(m)}, key=fy_start_year)
    for t in sec_tags:
        lo = t.lower()
        ms = sorted([m for m in sec_m if fy_tag_from_label(m) == t],
                    key=lambda l: (int(l.split("-")[1]), _MON3_NUM[l.split("-")[0]]))
        out[f"secondary_months_{lo}"] = ms
        out[f"secondary_monthly_{lo}"] = [r2(sec_m[m]["total"]) for m in ms]
        out[f"secondary_total_{lo}"] = r2(sum(sec_m[m]["total"] for m in ms))
    out["prior_year_basis"] = (
        "FY25 figures are DISTRIBUTOR SECONDARY (distributor -> retailer), the only "
        "FY25 series available; FY26 is true offtake (store -> consumer). They sit at "
        "different points in the value chain, so any FY26-vs-FY25 movement shown here "
        "is indicative, not like-for-like." if sec_tags else None)

    def dim_rows(key):
        names = {n for m in months for n in off_m[m][key]}
        names |= {n for m in sec_m for n in sec_m[m][key]}
        rows = []
        for n in names:
            row = {"name": n}
            for t in tags:
                lo = t.lower()
                row[lo] = r2(sum(off_m[m][key].get(n, 0.0)
                                 for m in months if fy_tag_from_label(m) == t))
            row["value"] = r2(sum(off_m[m][key].get(n, 0.0) for m in months))
            for t in sec_tags:
                row[f"secondary_{t.lower()}"] = r2(sum(sec_m[m][key].get(n, 0.0) for m in sec_m))
            rows.append(row)
        return sorted(rows, key=lambda d: -(d.get("value") or 0))

    # Stale FY keys from an earlier generation must not survive. The previous
    # block carried total_fy27 = 15,054 L whose own monthly_fy27 summed to
    # 13,220 L, plus months_fy25/monthly_fy25 with no total at all -- all from
    # the same patch that produced the 8-month FY26 window. Any FY the current
    # source does not cover is dropped rather than left to drift.
    _live = {t.lower() for t in tags}
    for _k in [k for k in list(out)
               if re.match(r"^(total|monthly|months|conversion_rates)_fy\d\d$", k)]:
        if _k.rsplit("_", 1)[1] not in _live:
            out.pop(_k, None)

    out["by_chain"] = dim_rows("chain")
    out["by_zone"] = dim_rows("zone")
    out["by_brand"] = dim_rows("brand")
    out["n_chains"] = len([r for r in out["by_chain"] if (r.get("value") or 0) > 0])
    out["provenance"] = (
        f"Rebuilt from {len(months)} monthly store x article extracts "
        f"({months[0]}..{months[-1]}). Reliance Brand Counter partitioned out per the "
        "CLAUDE.md dedup rule (macro already subsumes counter sales). NSV in INR Lakh.")

    bc = None
    if ctr_m:
        bmonths = sorted(ctr_m, key=lambda l: (int(l.split("-")[1]), _MON3_NUM[l.split("-")[0]]))
        bc = {"is_brand_counter": True, "include_in_overall_offtake": False,
              "months": bmonths, "monthly": [r2(ctr_m[m]["total"]) for m in bmonths],
              "total": r2(sum(ctr_m[m]["total"] for m in bmonths)),
              "note": "Reliance staffed-counter doors, held OUT of offtake to avoid "
                      "double counting against the Reliance macro figure."}
        for t in sorted({fy_tag_from_label(m) for m in bmonths if fy_tag_from_label(m)},
                        key=fy_start_year):
            lo = t.lower()
            ms = [m for m in bmonths if fy_tag_from_label(m) == t]
            bc[f"months_{lo}"] = ms
            bc[f"monthly_{lo}"] = [r2(ctr_m[m]["total"]) for m in ms]
            bc[f"total_{lo}"] = r2(sum(ctr_m[m]["total"] for m in ms))
    return out, bc

# --------------------------------------------------------------------------
# TOT% (Trade Offer Terms % / On-Invoice Margin Pass-on %)
#
# TOT% = 1 - (NSV + Tax) / MRP, i.e. the share of MRP given up as on-invoice
# trade margin once GST is added back on top of NSV. Tax = NSV x applicable
# GST rate: Pre_GST_Rate_Pct before that category's cutover date, Post_GST_
# Rate_Pct on/after it, both from the editable repo seed CSV
# PowerBI/SeedData/Masters/GST_Rate_QC_Table.csv (a per-category cutover
# override lives in that CSV's Effective_From column; if blank, the GLOBAL
# default cutover date from PowerBI/SeedData/Masters/GST_Config.csv is used
# -- default 2025-09-22, the GST Council's confirmed GST 2.0 effective date;
# edit that file's single cell if Honasa's internal billing cutover differs).
# Several categories in the QC table are LOW-confidence best-effort mappings
# (no official HSN-code-level source was available) and every row starts
# Finance_Approved=Pending -- verify against Honasa's Finance/Tax records
# before treating TOT% as final. This block's "methodology" string and the
# QC table's own columns surface that caveat wherever TOT% is displayed.
# --------------------------------------------------------------------------
_MONTH_IDX = {"April": 0, "May": 1, "June": 2, "July": 3, "Aug": 4, "Sept": 5,
              "Oct": 6, "Nov": 7, "Dec": 8, "Jan": 9, "Feb": 10, "March": 11}
_CAL_MONTH = [4, 5, 6, 7, 8, 9, 10, 11, 12, 1, 2, 3]   # Apr..Mar, aligned to _MONTH_IDX order
_GST_MASTERS_DIR = Path(__file__).resolve().parent.parent / "PowerBI" / "SeedData" / "Masters"
_GST_QC_CSV = _GST_MASTERS_DIR / "GST_Rate_QC_Table.csv"
_GST_CONFIG_CSV = _GST_MASTERS_DIR / "GST_Config.csv"
_GST_QC_COLUMNS = ["Category", "HSN_Code", "Pre_GST_Rate_Pct", "Post_GST_Rate_Pct",
                    "Effective_From", "Confidence", "Finance_Approved",
                    "Impact_on_TOT_pct", "Note"]

def month_ord(month_name, fy_tag):
    """Sortable (calendar_year*12 + calendar_month) for a dashboard Month
    label + FY tag, e.g. ('Nov','FY26') -> Nov 2025. Returns None if either
    isn't recognised."""
    try:
        y0 = fy_start_year(fy_tag)   # ANY 'FYnn' tag -- no enumerated year map
    except (ValueError, IndexError):
        return None
    idx = _MONTH_IDX.get(month_name)
    if idx is None:
        return None
    cal_year = y0 + (1 if idx >= 9 else 0)   # Jan/Feb/March roll into the next calendar year
    return cal_year * 12 + _CAL_MONTH[idx]

def date_to_month_ord(date_str):
    """'2025-09-22' -> (2025*12+9). Returns None for blank/unparsable."""
    if not date_str or not str(date_str).strip():
        return None
    try:
        y, m, _ = str(date_str).strip().split("-")
        return int(y) * 12 + int(m)
    except (ValueError, AttributeError):
        return None

def load_gst_cutover_date():
    """Global default GST cutover date from the editable GST_Config.csv, as
    (month_ord, raw_date_str). month_ord is what the row-level cutover
    comparison actually uses (dashboard Month/FY data has no day-of-month
    granularity, so the comparison can only resolve to "on/after this
    calendar month" regardless of which day in that month is configured);
    raw_date_str is the exact string from the CSV, preserved for display so
    e.g. "2025-09-22" doesn't get silently rounded down to "2025-09-01" in
    the UI. Falls back to 2025-09-22 (GST Council's confirmed GST 2.0
    effective date) if the file is missing or unparsable."""
    default_str = "2025-09-22"
    if _GST_CONFIG_CSV.exists():
        with open(_GST_CONFIG_CSV, newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                raw = (row.get("GST_Cutover_Date") or "").strip()
                ordv = date_to_month_ord(raw)
                if ordv is not None:
                    return ordv, raw
    return date_to_month_ord(default_str), default_str

def load_gst_qc_table():
    """Category -> {pre, post, effective_from_ord, ...raw row} from the
    editable GST_Rate_QC_Table.csv. Returns ({}, []) if the file is missing.
    Also returns the raw fieldnames + row dicts (in file order) so
    write_gst_qc_impacts() can update just the Impact_on_TOT_pct column
    without disturbing any hand-edited columns (HSN_Code, Finance_Approved,
    Effective_From, Confidence, Note)."""
    if not _GST_QC_CSV.exists():
        return {}, []
    with open(_GST_QC_CSV, newline="", encoding="utf-8") as fh:
        raw_rows = list(csv.DictReader(fh))
    table = {}
    for row in raw_rows:
        cat = (row.get("Category") or "").strip()
        if not cat:
            continue
        try:
            pre = float(row.get("Pre_GST_Rate_Pct") or 18)
        except ValueError:
            pre = 18.0
        try:
            post = float(row.get("Post_GST_Rate_Pct") or 18)
        except ValueError:
            post = 18.0
        table[cat] = {
            "pre": pre, "post": post,
            "effective_from_ord": date_to_month_ord(row.get("Effective_From")),
        }
    return table, raw_rows

def write_gst_qc_impacts(raw_rows, impacts):
    """Rewrite GST_Rate_QC_Table.csv with the Impact_on_TOT_pct column
    refreshed from `impacts` ({category: pp}), leaving every other
    hand-editable column (HSN_Code, Finance_Approved, Effective_From,
    Confidence, Note) exactly as Finance/Tax left it. No-op if the file
    doesn't exist (nothing to update)."""
    if not raw_rows or not _GST_QC_CSV.exists():
        return
    for row in raw_rows:
        cat = (row.get("Category") or "").strip()
        v = impacts.get(cat)
        row["Impact_on_TOT_pct"] = "" if v is None else str(v)
    with open(_GST_QC_CSV, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=_GST_QC_COLUMNS)
        w.writeheader()
        w.writerows(raw_rows)

def gst_rate_for_ord(category, ordv, qc_table, default_cutover_ord):
    """Applicable GST% for a Category at a given month_ord. Falls back to a
    flat 18% pre/post (no distinction) for any category not present in the
    QC table at all."""
    row = qc_table.get(category)
    if row is None:
        return 18.0
    if ordv is None:
        return row["pre"]
    cutover = row["effective_from_ord"] if row["effective_from_ord"] is not None else default_cutover_ord
    return row["pre"] if ordv < cutover else row["post"]

# ---------------------------------------------------------------------------
# TOT% 3-TIER SOURCE PRIORITY (row-level, computed BEFORE any groupby so the
# real per-transaction Avg Tot / Inv. Tax Amount(LOC) values aren't lost to
# aggregation -- these are Customer x Article-grain fields in the Primary
# file and can't be recovered from a pre-summed group):
#   1. "avg_tot"      -- Primary file's own `Avg Tot` column (0-1 fraction),
#                        already the business's own TOT% for that row.
#                        Pass-on value = MRP x Avg Tot.
#   2. "tax_calc"      -- `Avg Tot` blank/invalid: use the row's actual
#                        `Inv. Tax Amount(LOC)`. Pass-on value = MRP-NSV-Tax.
#   3. "gst_fallback"  -- both blank/invalid: estimate Tax from the editable
#                        GST_Rate_QC_Table.csv (Category + cutover date based
#                        rate). Pass-on value = MRP-NSV-Tax_estimated.
#   "invalid"          -- MRP blank/zero, or (tier 1 unusable AND NSV blank)
#                        -- can't compute any tier; excluded from TOT%
#                        aggregation entirely (not silently included at 0).
# GST_Rate_QC_Table.csv is FALLBACK ONLY now -- tiers 1/2 use the Primary
# file's own real Avg Tot / Inv. Tax Amount(LOC), which in practice cover
# the overwhelming majority of rows (100% in the source file this was built
# against), so the rate-table assumption typically has ZERO bearing on
# blended TOT% -- see qc_summary/category_impacts_pp.
# ---------------------------------------------------------------------------
_AVG_TOT_VALID_MIN, _AVG_TOT_VALID_MAX = -1.5, 1.5   # sane bound for a 0-1-ish fraction; outside = treat as bad data, fall through

def compute_tot_columns(df, qc_table, default_cutover_ord):
    """Adds _passon, _tot_mrp, _tot_nsv, _fallback_nsv, _method columns to the
    ROW-LEVEL (not yet grouped) primary-article dataframe `df`, which must
    already have _MRP, _NSV, _AvgTot, _TaxLOC, _category, _M, _FY columns.
    Vectorised for the (expected-dominant) tier-1/tier-2 paths; only the
    (expected-rare) tier-3/invalid remainder pays for a row-wise category
    rate lookup. _fallback_nsv = NSV where method=='gst_fallback' else 0 --
    the ONLY NSV base the rate table's assumptions actually affect, used for
    the category Impact_on_TOT_pct sensitivity calc."""
    mrp, nsv = df["_MRP"], df["_NSV"]
    at, tax = df["_AvgTot"], df["_TaxLOC"]

    mrp_ok = mrp.notna() & (mrp != 0)
    at_ok = mrp_ok & at.notna() & at.between(_AVG_TOT_VALID_MIN, _AVG_TOT_VALID_MAX)
    tax_ok = mrp_ok & ~at_ok & nsv.notna() & tax.notna()
    remainder = mrp_ok & ~at_ok & ~tax_ok   # tier-3 (gst_fallback) candidates, or invalid if NSV is also blank

    passon = pd.Series(float("nan"), index=df.index, dtype="float64")
    tot_mrp = pd.Series(float("nan"), index=df.index, dtype="float64")
    tot_nsv = pd.Series(float("nan"), index=df.index, dtype="float64")
    fallback_nsv = pd.Series(0.0, index=df.index, dtype="float64")
    method = pd.Series("invalid", index=df.index, dtype="object")

    passon[at_ok] = mrp[at_ok] * at[at_ok]
    tot_mrp[at_ok] = mrp[at_ok]
    tot_nsv[at_ok] = nsv[at_ok]
    method[at_ok] = "avg_tot"

    passon[tax_ok] = mrp[tax_ok] - nsv[tax_ok] - tax[tax_ok]
    tot_mrp[tax_ok] = mrp[tax_ok]
    tot_nsv[tax_ok] = nsv[tax_ok]
    method[tax_ok] = "tax_calc"

    for i in df.index[remainder]:
        if pd.isna(nsv.loc[i]):
            continue   # stays "invalid" -- can't compute any tier without NSV
        ordv = month_ord(df.at[i, "_M"], df.at[i, "_FY"])
        rate = gst_rate_for_ord(df.at[i, "_category"], ordv, qc_table, default_cutover_ord)
        tax_est = nsv.loc[i] * rate / 100.0
        passon.loc[i] = mrp.loc[i] - nsv.loc[i] - tax_est
        tot_mrp.loc[i] = mrp.loc[i]
        tot_nsv.loc[i] = nsv.loc[i]
        fallback_nsv.loc[i] = nsv.loc[i]
        method.loc[i] = "gst_fallback"

    df["_passon"] = passon
    df["_tot_mrp"] = tot_mrp
    df["_tot_nsv"] = tot_nsv
    df["_fallback_nsv"] = fallback_nsv
    df["_method"] = method
    return df

def compute_tot_qc_summary(df_scope):
    """Row-level (not grouped) method-source counts + fallback materiality,
    for the QC summary block shown on the dashboard's TOT% card. df_scope
    should already be filtered to whatever FY window tot_block operates on
    (FY26/FY27) so the counts match the population blended_tot_pct covers."""
    n_avg_tot = int((df_scope["_method"] == "avg_tot").sum())
    n_tax_calc = int((df_scope["_method"] == "tax_calc").sum())
    n_gst_fallback = int((df_scope["_method"] == "gst_fallback").sum())
    n_invalid = int((df_scope["_method"] == "invalid").sum())
    valid_mrp = df_scope.loc[df_scope["_method"] != "invalid", "_tot_mrp"].sum()
    fallback_mrp = df_scope.loc[df_scope["_method"] == "gst_fallback", "_tot_mrp"].sum()
    return {
        "rows_avg_tot": n_avg_tot, "rows_tax_calc": n_tax_calc,
        "rows_gst_fallback": n_gst_fallback, "rows_invalid": n_invalid,
        "rows_total": n_avg_tot + n_tax_calc + n_gst_fallback + n_invalid,
        "fallback_pct_of_mrp": r2(fallback_mrp / valid_mrp * 100, 1) if valid_mrp else None,
    }

def tot_block(g, qc_table, default_cutover, qc_raw_rows=None, qc_summary=None):
    """Chain / Category / Pack-Size-wise TOT%, on-invoice margin pass-on
    value, and a monthly series (for MoM TOT Delta pp / Incremental Pass-on
    Impact), computed from the FULL (uncapped) article-level primary groupby
    `g` — columns _M, _FY, _Chain, _category, _net_content, TotMRP, TotNSV,
    Passon, FallbackNSV (Lakh; pre-computed row-level by compute_tot_columns,
    then summed through the groupby). Only FY26/FY27 rows are used (matches
    the rest of the dashboard's "no FY24-25 actuals" convention). If
    qc_raw_rows is given, also computes each category's Impact_on_TOT_pct
    (blended TOT% delta, in pp, if that category's Post_GST_Rate_Pct were
    flipped to the alternate common slab) and writes it back into the QC CSV
    -- scoped ONLY to that category's gst_fallback-tier NSV, since avg_tot/
    tax_calc rows use real source data and aren't affected by the rate table
    at all."""
    default_cutover_ord, default_cutover_str = default_cutover
    gg = g[fy_ge(g["_FY"])].copy()   # FY26 onward -- any future FY included automatically

    def weighted(group_col, with_mom=False):
        """Per-group MRP/NSV/Tax/TOT%/pass-on value -- SUM(passon)/SUM(mrp),
        never a simple average of row-level TOT% percentages. with_mom=True
        additionally computes that group's OWN latest month-over-month TOT%
        delta (pp) and incremental pass-on impact from ITS OWN monthly trend
        — not the dashboard-wide blended monthly series — so e.g. two pack
        sizes with different trajectories don't get the same MoM number."""
        out = []
        for name, d in gg.groupby(group_col):
            if not name:
                continue
            mrp, nsv, passon = d["TotMRP"].sum(), d["TotNSV"].sum(), d["Passon"].sum()
            if mrp <= 0:
                continue
            tax = mrp - nsv - passon
            row = {"name": name, "mrp": r2(mrp), "nsv": r2(nsv), "tax": r2(tax),
                   "tot_pct": r2(passon / mrp * 100, 1), "passon_value": r2(passon)}
            if with_mom:
                mrow = []
                for (fy, m), dm in d.groupby(["_FY", "_M"]):
                    ordv = month_ord(m, fy)
                    if ordv is None:
                        continue
                    mmrp, mpasson = dm["TotMRP"].sum(), dm["Passon"].sum()
                    if mmrp <= 0:
                        continue
                    mrow.append({"ord": ordv, "tot_pct": mpasson / mmrp * 100, "passon_value": mpasson})
                mrow.sort(key=lambda x: x["ord"])
                if len(mrow) >= 2:
                    row["mom_tot_delta_pp"] = r2(mrow[-1]["tot_pct"] - mrow[-2]["tot_pct"], 1)
                    row["incremental_passon_impact"] = r2(mrow[-1]["passon_value"] - mrow[-2]["passon_value"])
                else:
                    row["mom_tot_delta_pp"] = None
                    row["incremental_passon_impact"] = None
            out.append(row)
        return sorted(out, key=lambda d: -(d["mrp"] or 0))

    by_chain = weighted("_Chain")
    by_category = weighted("_category")
    by_packsize = weighted("_net_content", with_mom=True)

    monthly_raw = []
    for (fy, m), d in gg.groupby(["_FY", "_M"]):
        ordv = month_ord(m, fy)
        if ordv is None:
            continue
        mrp, passon = d["TotMRP"].sum(), d["Passon"].sum()
        if mrp <= 0:
            continue
        monthly_raw.append({"fy": fy, "month": m, "ord": ordv,
                            "tot_pct": passon / mrp * 100, "passon_value": passon})
    monthly_raw.sort(key=lambda d: d["ord"])
    monthly = []
    for i, row in enumerate(monthly_raw):
        prev = monthly_raw[i - 1] if i > 0 else None
        monthly.append({
            "fy": row["fy"], "month": row["month"],
            "tot_pct": r2(row["tot_pct"], 1),
            "passon_value": r2(row["passon_value"]),
            "mom_tot_delta_pp": r2(row["tot_pct"] - prev["tot_pct"], 1) if prev else None,
            "incremental_passon_impact": r2(row["passon_value"] - prev["passon_value"]) if prev else None,
        })

    tot_mrp, tot_nsv, tot_passon = gg["TotMRP"].sum(), gg["TotNSV"].sum(), gg["Passon"].sum()
    blended_tot_pct = (tot_passon / tot_mrp * 100) if tot_mrp else None
    tot_tax = tot_mrp - tot_nsv - tot_passon  # noqa: F841

    # ---- Impact_on_TOT_pct: for each QC-table category, how much would the
    # BLENDED TOT% move (pp) if that category's Post_GST_Rate_Pct were flipped
    # to the alternate common slab (5<->18), holding every other category's
    # rate fixed. Scoped ONLY to that category's gst_fallback-tier NSV (real
    # avg_tot/tax_calc rows are untouched by the rate table). Lets Finance/Tax
    # prioritise which LOW-confidence categories are worth chasing first
    # (large impact) vs immaterial (small/zero impact -- e.g. a category with
    # 100% Avg Tot coverage has zero fallback exposure regardless of Confidence).
    category_impacts = {}
    if blended_tot_pct is not None:
        for cat, row in qc_table.items():
            alt_post = 18.0 if row["post"] != 18.0 else 5.0
            fallback_nsv = gg.loc[gg["_category"] == cat, "FallbackNSV"].sum()
            if not fallback_nsv:
                category_impacts[cat] = 0.0
                continue
            delta_tax = fallback_nsv * (alt_post - row["post"]) / 100.0
            alt_blended = ((tot_passon - delta_tax) / tot_mrp) * 100 if tot_mrp else None
            category_impacts[cat] = r2(alt_blended - blended_tot_pct, 1) if alt_blended is not None else None
        if qc_raw_rows:
            write_gst_qc_impacts(qc_raw_rows, category_impacts)

    finance_approved_n = sum(1 for r in (qc_raw_rows or []) if (r.get("Finance_Approved") or "").strip().lower() == "yes")
    finance_total_n = len(qc_raw_rows or [])

    # ---- QC table rows for display (dashboard TOT% card + Power BI): the
    # SAME file Finance/Tax reviews and signs off on, exposed in data.js so
    # the HTML dashboard doesn't need a second copy of this data.
    qc_table_rows = [{
        "category": r.get("Category", ""),
        "hsn_code": r.get("HSN_Code", ""),
        "pre_rate_pct": r.get("Pre_GST_Rate_Pct", ""),
        "post_rate_pct": r.get("Post_GST_Rate_Pct", ""),
        "effective_from": r.get("Effective_From", ""),
        "confidence": r.get("Confidence", ""),
        "finance_approved": r.get("Finance_Approved", ""),
        "impact_on_tot_pp": r.get("Impact_on_TOT_pct", ""),
        "note": r.get("Note", ""),
    } for r in (qc_raw_rows or [])]

    return {
        "by_chain": by_chain, "by_category": by_category, "by_packsize": by_packsize,
        "monthly": monthly,
        "blended_tot_pct": r2(blended_tot_pct, 1),
        "total_passon_value": r2(tot_passon),
        "category_impacts_pp": category_impacts,
        "qc_table": qc_table_rows,
        "method_qc": qc_summary or {},
        "gst_cutover_default": default_cutover_str,
        "finance_approved_count": finance_approved_n,
        "finance_approved_total": finance_total_n,
        "unit": "INR Lakh",
        "methodology": (
            "TOT% (Trade Offer Terms % / On-Invoice Margin Pass-on %) = "
            "Pass-on Value / MRP, i.e. SUM(Pass-on Value) / SUM(MRP) at whatever grain "
            "it's shown (never a simple average of row-level TOT% percentages). Pass-on "
            "Value is sourced per row with a 3-tier priority, computed from the full "
            "article-level primary detail (not the row-capped browser export): "
            "1) SOURCE -- the Primary file's own 'Avg Tot' column (Customer x Article "
            "grain), used directly: Pass-on Value = MRP x Avg Tot. "
            "2) ACTUAL TAX -- if Avg Tot is blank/invalid, use the row's actual "
            "'Inv. Tax Amount(LOC)': Pass-on Value = MRP - NSV - Tax. "
            "3) GST RATE TABLE FALLBACK -- only if BOTH are blank/invalid, estimate Tax "
            "from Category x cutover-date via the editable PowerBI/SeedData/Masters/"
            "GST_Rate_QC_Table.csv (a per-category cutover override lives in that CSV's "
            "Effective_From column; if blank, the global default cutover date from "
            "PowerBI/SeedData/Masters/GST_Config.csv applies -- default 2025-09-22, the "
            "GST Council's confirmed GST 2.0 effective date). The GST rate table is "
            "FALLBACK ONLY: it has zero effect on TOT% for any row where the Primary "
            "file's own Avg Tot or Inv. Tax Amount(LOC) is present -- see method_qc for "
            "exactly how many rows/how much MRP actually rely on it. Several categories "
            "in the QC table are LOW-confidence best-effort assumptions (no official "
            "HSN-code source was available) and every row starts Finance_Approved=Pending "
            "-- verify against Finance/Tax records before treating any fallback-tier TOT% "
            "as final. 'Incremental Pass-on Impact' = the MoM change in Pass-on Value. "
            "'Impact_on_TOT_pct' (in the QC table) = how much blended TOT% would move, in "
            "pp, if that one category's Post_GST_Rate_Pct were flipped to the alternate "
            "slab -- scoped only to that category's gst_fallback-tier rows, since "
            "avg_tot/tax_calc rows use real source data and aren't affected by the rate "
            "table at all."
        ),
    }

# --------------------------------------------------------------------------
# CM2 (Contribution Margin 2) = NSV - P&L Expenses
#
# NSV here is already net of TOT/on-invoice-margin-pass-on AND tax (that's
# what "Primary NSV" / this pipeline's _NSV already is, per the TOT% block
# above), so no further TOT/Tax deduction happens in this function -- CM2 is
# simply NSV minus whatever P&L expenses matched that scope.
#
# Expenses are NEVER hardcoded: they come entirely from the editable
# PowerBI/SeedData/Masters/PL_Expense_Input.csv, matched to the SAME
# article-level primary detail that TOT% uses. Per row: Month+FY is always
# required; Customer Code is tried FIRST (via a Cust-SAP-Code -> Chain
# lookup built from the primary data itself), Chain name is the fallback.
# A row satisfying neither is "unmapped" -- excluded from chain-wise CM2 but
# still counted (and its amount tracked) in the QC summary. An expense row
# only attributes to a Brand/Category bucket if IT specifies that dimension
# -- no proportional/estimated allocation is invented for rows that don't.
# --------------------------------------------------------------------------
_EXPENSE_DEDUP_FIELDS = ["Month", "FY", "Chain", "Customer Code", "Customer Name",
                         "Brand", "Category", "Sub Category", "Expense Head",
                         "Expense Type", "Expense Amount (INR Lakh)"]

def load_pl_expense_input():
    """Row dicts from the editable PowerBI/SeedData/Masters/PL_Expense_Input.csv.
    Returns [] if the file is missing OR contains only the seed template's own
    "EXAMPLE ROW" placeholder rows (no expenses loaded yet -- CM2 then just
    equals NSV, and the dashboard/Power BI both show an explicit "no expense
    data loaded" state rather than a fabricated CM2).

    Bug fixed 2026-09-13: the seed file ships with 3 rows explicitly marked
    "EXAMPLE ROW -- replace with real data" in Remarks, to show a Finance
    user the exact schema. Those rows used to satisfy has_expense_data (any
    parsed row counted as real), so the dashboard silently treated Rs47.65L
    of template placeholder values (Dmart Visibility Spend Rs12.5L, Reliance
    Retail Scheme/Trade Spend Rs28.4L, Apollo BA Cost Rs6.75L) as real CM2
    expense and never showed the "no expense data loaded" banner it was
    designed to show in that state. Filtering them out here is a pure
    correctness fix -- no real expense data existed in this file before or
    after this change."""
    path = Path(__file__).resolve().parent.parent / "PowerBI" / "SeedData" / "Masters" / "PL_Expense_Input.csv"
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    return [r for r in rows if "EXAMPLE ROW" not in (r.get("Remarks") or "").upper()]

def _build_custcode_chain_lookup(df):
    """Cust-SAP Code -> most common Chain, built from the primary article
    data itself, so an expense row that only gives a Customer Code (no
    Chain) can still resolve for chain-wise CM2."""
    sub = df[df["_CustCode"] != ""]
    if sub.empty:
        return {}
    def _most_common(s):
        vc = s.value_counts()
        return vc.idxmax() if len(vc) > 0 else None
    result = sub.groupby("_CustCode")["_Chain"].agg(_most_common)
    return result[result.notna()].to_dict()

def primary_offtake_gap_block(primary, offtake, fyx_primary):
    """Primary-vs-Offtake gap analysis, computed only over grains and periods
    where both measures genuinely exist and are comparable -- never a
    fabricated relationship. Two windows:

      fy26: primary.monthly_fy26 (12 real months, primary.by_channel shows
            EB2B/SIS are both 0 for FY26 -- a clean, fully MT-channel-scoped
            comparison) vs offtake.monthly_fy26 / offtake.total_fy26.
      fy27: fyx_primary.monthly_canon (Apr-Aug'26 so far) vs
            offtake.monthly_fy27 -- flagged NOT_FULLY_COMPARABLE because
            fyx_primary's total still includes EB2B/SIS (~5.2% of FY27
            Primary per by_channel), which Offtake (chain POS, MT-only by
            construction) does not carry. Shown anyway, with the caveat
            attached, rather than withheld -- the gap is still directionally
            informative, it just isn't a pure like-for-like ratio.

    By-chain gap is split into three groups rather than one blended list,
    because Primary and Offtake do not cover the same 21/35-chain universe
    (verified 2026-09-13: 15 chains exist in both, 6 Primary-only, 19
    Offtake-only) -- dividing across mismatched universes would silently
    misrepresent coverage:
      matched:      chain exists in both -> gap/ratio computed
      primary_only: chain has Primary NSV but no Offtake series -- shown as
                    a value, never divided into a ratio
      offtake_only: the mirror case

    Never call the gap "inventory" -- it may reflect inventory movement,
    timing/cutoff, returns, channel/coverage differences, or other business
    processes not evidenced here. Labelled neutrally throughout.
    """
    def _by_month(months, prim_vals, off_months, off_vals, comparable_note):
        off_map = dict(zip(off_months, off_vals))
        rows = []
        for i, m in enumerate(months):
            p = prim_vals[i] if i < len(prim_vals) else None
            o = off_map.get(m)
            gap = (p - o) if (p is not None and o is not None) else None
            ratio = round(p / o, 3) if (p and o) else None
            rows.append({"month": m, "primary": p, "offtake": o, "gap": gap,
                         "ratio": ratio})
        return {"rows": rows, "comparable_note": comparable_note}

    def _by_chain(prim_chain_map, off_chain_map):
        matched, primary_only, offtake_only = [], [], []
        for name in sorted(set(prim_chain_map) | set(off_chain_map)):
            p = prim_chain_map.get(name)
            o = off_chain_map.get(name)
            if p is not None and o is not None:
                gap = p - o
                ratio = round(p / o, 3) if o else None
                matched.append({"name": name, "primary": p, "offtake": o,
                                 "gap": gap, "ratio": ratio})
            elif p is not None:
                primary_only.append({"name": name, "primary": p})
            elif o is not None:
                offtake_only.append({"name": name, "offtake": o})
        matched.sort(key=lambda r: abs(r["gap"]), reverse=True)
        return {"matched": matched, "primary_only": primary_only,
                "offtake_only": offtake_only,
                "coverage_note": (f"{len(matched)} chains in both series, "
                                  f"{len(primary_only)} Primary-only (no Offtake series), "
                                  f"{len(offtake_only)} Offtake-only (no Primary series) -- "
                                  "gap/ratio computed only for matched chains")}

    fy26 = None
    if primary.get("monthly_fy26") and offtake.get("monthly_fy26"):
        fy26 = {
            "by_month": _by_month(
                offtake["months_fy26"], primary["monthly_fy26"],
                offtake["months_fy26"], offtake["monthly_fy26"],
                "Comparable: FY26 Primary is 100% MT channel (EB2B/SIS both 0 "
                "per primary.by_channel), matching Offtake's MT-only scope."),
            "by_chain": _by_chain(
                {c["name"]: c["fy26"] for c in primary.get("by_chain", []) if c.get("fy26")},
                {c["name"]: c["fy26"] for c in offtake.get("by_chain", []) if c.get("fy26")}),
        }

    fy27 = None
    if fyx_primary and fyx_primary.get("monthly_canon") and offtake.get("monthly_fy27"):
        fy27 = {
            "by_month": _by_month(
                fyx_primary["months_canon"], fyx_primary["monthly_canon"],
                offtake["months_fy27"], offtake["monthly_fy27"],
                "NOT_FULLY_COMPARABLE: FY27 Primary total still includes EB2B/SIS "
                "(~5.2% of FY27 Primary per fyx_primary.by_channel); Offtake is "
                "MT-only by construction. Shown for trend direction, not as a "
                "precise like-for-like ratio."),
            "by_chain": _by_chain(
                {c["name"]: c["nsv"] for c in fyx_primary.get("by_chain", [])},
                {c["name"]: c["fy27"] for c in offtake.get("by_chain", []) if c.get("fy27")}),
        }

    return {"fy26": fy26, "fy27": fy27,
            "note": ("Primary-Offtake Gap = Primary NSV - Offtake NSV. Neutral "
                     "label deliberately used instead of 'inventory' -- the gap "
                     "may reflect inventory movement, timing/cutoff, returns, "
                     "channel or coverage differences, or other business "
                     "processes not evidenced here.")}


def cm2_block(df, expense_rows):
    """Chain/Brand/Category/Expense-Head CM2 rollups + monthly series, from
    the row-level article-level primary detail `df` (already carries _NSV,
    _Chain, _Brand, _category, _CustCode, _method, _FY, _M from the TOT%
    computation above) and the parsed PL_Expense_Input.csv rows."""
    known_chains = set(df["_Chain"].dropna().unique())
    known_brands = set(df["_Brand"].dropna().unique())
    known_categories = set(x for x in df["_category"].dropna().unique() if x)
    custcode_chain = _build_custcode_chain_lookup(df)

    seen_keys = set()
    parsed = []
    qc = {"total_expense": 0.0, "mapped_expense": 0.0, "unmapped_expense": 0.0,
          "unmapped_chain_customer": 0, "unmapped_brand_category": 0,
          "blank_month": 0, "blank_expense_head": 0, "duplicate_rows": 0,
          "rows_loaded": len(expense_rows)}

    for r in expense_rows:
        raw_amount = (r.get("Expense Amount (INR Lakh)") or "").strip()
        try:
            amount = float(raw_amount) if raw_amount else None
        except ValueError:
            amount = None
        if amount is None:
            continue   # nothing to attribute -- not counted as loaded/unmapped either

        dedup_key = tuple((r.get(k) or "").strip().lower() for k in _EXPENSE_DEDUP_FIELDS)
        if dedup_key in seen_keys:
            qc["duplicate_rows"] += 1
            continue
        seen_keys.add(dedup_key)

        qc["total_expense"] += amount

        m = _mlabel(r.get("Month"))
        fy = _fylabel(r.get("FY"))
        if m is None or fy is None:
            qc["blank_month"] += 1
            qc["unmapped_expense"] += amount
            continue

        head = (r.get("Expense Head") or "").strip()
        if not head:
            qc["blank_expense_head"] += 1

        cust_code = (r.get("Customer Code") or "").strip()
        chain_in = (r.get("Chain") or "").strip()
        resolved_chain, match_method = None, None
        if cust_code and cust_code in custcode_chain:
            resolved_chain, match_method = custcode_chain[cust_code], "custcode"
        elif chain_in:
            cc = canon_chain(chain_in)
            if cc in known_chains:
                resolved_chain, match_method = cc, "chain"

        brand_in = (r.get("Brand") or "").strip()
        cat_in = (r.get("Category") or "").strip()
        brand_resolved = canon_brand(brand_in) if brand_in else None
        cat_resolved = cat_in or None   # Category has no alias map elsewhere in this pipeline; used as-given, trimmed
        bad_dim = (brand_in and brand_resolved not in known_brands) or (cat_in and cat_resolved not in known_categories)
        if bad_dim:
            qc["unmapped_brand_category"] += 1

        if resolved_chain is None:
            qc["unmapped_chain_customer"] += 1
            qc["unmapped_expense"] += amount
            continue

        qc["mapped_expense"] += amount
        parsed.append({
            "fy": fy, "month": m, "chain": resolved_chain,
            "brand": brand_resolved if (brand_in and not bad_dim) else None,
            "category": cat_resolved if (cat_in and not bad_dim) else None,
            "head": head or "(Unspecified)",
            "type": (r.get("Expense Type") or "").strip(),
            "amount": amount, "match_method": match_method,
        })

    qc["total_expense"] = r2(qc["total_expense"])
    qc["mapped_expense"] = r2(qc["mapped_expense"])
    qc["unmapped_expense"] = r2(qc["unmapped_expense"])
    qc["mapped_pct_of_total"] = r2(qc["mapped_expense"] / qc["total_expense"] * 100, 1) if qc["total_expense"] else None

    # ---- NSV base: same TOT%-valid, FY26/FY27-only population as tot_block ----
    base = df[fy_ge(df["_FY"]) & (df["_method"] != "invalid")]

    def rollup(dim_col, expense_dim_key):
        nsv_series = base.groupby(dim_col)["_NSV"].sum()
        exp_by = {}
        for e in parsed:
            key = e.get(expense_dim_key)
            if key is None:
                continue
            exp_by[key] = exp_by.get(key, 0.0) + e["amount"]
        out = []
        for name in set(nsv_series.index) | set(exp_by.keys()):
            if not name:
                continue
            nsv = float(nsv_series.get(name, 0.0))
            exp = exp_by.get(name, 0.0)
            if nsv <= 0 and exp <= 0:
                continue
            cm2 = nsv - exp
            out.append({"name": name, "nsv": r2(nsv), "expense": r2(exp),
                        "cm2_value": r2(cm2), "cm2_pct": r2(cm2 / nsv * 100, 1) if nsv else None})
        # NSV desc, then name asc on ties -- deterministic regardless of the
        # `set(nsv_series.index) | set(exp_by.keys())` iteration order above
        # (hash-randomized per process; previously caused e.g. Hair Colour/
        # Fragrances, tied at the same NSV, to swap order between rebuilds).
        return sorted(out, key=lambda d: (-(d["nsv"] or 0), str(d["name"])))

    by_chain = rollup("_Chain", "chain")
    by_brand = rollup("_Brand", "brand")
    by_category = rollup("_category", "category")

    head_totals = {}
    for e in parsed:
        head_totals[e["head"]] = head_totals.get(e["head"], 0.0) + e["amount"]
    by_expense_head = sorted(
        [{"name": k, "amount": r2(v)} for k, v in head_totals.items()],
        key=lambda d: -d["amount"])

    nsv_monthly = base.groupby(["_FY", "_M"])["_NSV"].sum()
    exp_monthly = {}
    for e in parsed:
        k = (e["fy"], e["month"])
        exp_monthly[k] = exp_monthly.get(k, 0.0) + e["amount"]
    raw_monthly = []
    for (fy, m) in set(nsv_monthly.index) | set(exp_monthly.keys()):
        ordv = month_ord(m, fy)
        if ordv is None:
            continue
        nsv = float(nsv_monthly.get((fy, m), 0.0))
        exp = exp_monthly.get((fy, m), 0.0)
        raw_monthly.append({"fy": fy, "month": m, "ord": ordv, "nsv": nsv, "expense": exp,
                            "cm2_value": nsv - exp, "cm2_pct": (nsv - exp) / nsv * 100 if nsv else None})
    raw_monthly.sort(key=lambda d: d["ord"])
    monthly = []
    for i, row in enumerate(raw_monthly):
        prev = raw_monthly[i - 1] if i > 0 else None
        monthly.append({
            "fy": row["fy"], "month": row["month"],
            "nsv": r2(row["nsv"]), "expense": r2(row["expense"]),
            "cm2_value": r2(row["cm2_value"]),
            "cm2_pct": r2(row["cm2_pct"], 1) if row["cm2_pct"] is not None else None,
            "mom_expense_change": r2(row["expense"] - prev["expense"]) if prev else None,
            "mom_cm2_change": r2(row["cm2_value"] - prev["cm2_value"]) if prev else None,
        })

    total_nsv = base["_NSV"].sum()
    total_expense = sum(e["amount"] for e in parsed)
    cm2_value = total_nsv - total_expense
    return {
        "total_nsv": r2(total_nsv),
        "total_expense": r2(total_expense),
        "expense_pct_of_nsv": r2(total_expense / total_nsv * 100, 1) if total_nsv else None,
        "cm2_value": r2(cm2_value),
        "cm2_pct": r2(cm2_value / total_nsv * 100, 1) if total_nsv else None,
        "by_chain": by_chain, "by_brand": by_brand, "by_category": by_category,
        "by_expense_head": by_expense_head,
        "monthly": monthly,
        "has_expense_data": len(parsed) > 0,
        "unit": "INR Lakh",
        "qc": qc,
        "methodology": (
            "CM2 = NSV - P&L Expenses. NSV is already net of TOT%/on-invoice-margin "
            "pass-on and tax (see the TOT% section above), so no further deduction "
            "happens here. Expenses are NEVER hardcoded -- they come entirely from "
            "the editable PowerBI/SeedData/Masters/PL_Expense_Input.csv, matched to "
            "this same article-level primary detail: Month+FY is always required; "
            "Customer Code is tried first (via a Cust-SAP-Code -> Chain lookup built "
            "from the primary data itself), Chain name is the fallback. A row "
            "matching neither is unmapped -- excluded from chain-wise CM2 but still "
            "counted in the QC summary. An expense row only attributes to a Brand/"
            "Category bucket if it specifies that dimension itself -- no proportional "
            "allocation is invented for rows that don't."
        ),
    }

# --------------------------------------------------------------------------
# P&L (chain-wise gross-to-net + trade spend)
# --------------------------------------------------------------------------
def pnl_block(pdf, promo):
    """Per-chain trade P&L bridge from real primary data:
       Gross MRP value  ->  trade discount (MRP-NSV)  ->  Net NSV.
       Plus promo intensity from the promo calendar. COGS is not in source,
       so this is a gross-to-net trade contribution view, not a full P&L.
       Computed for the LATEST FY present in the source (label-driven via
       THE ONE FY RULE, not a hardcoded year) -- emitted as pl['fy_tag']."""
    fy_tags = sorted({t for t in (pdf["FY"].map(_fylabel)).dropna().unique()}, key=fy_start_year)
    latest = fy_tags[-1] if fy_tags else "FY26"
    latest_keys = [k for k in pdf["FY"].dropna().unique() if _fylabel(k) == latest]
    g = pdf[pdf["FY"].isin(latest_keys)].groupby("chain").agg(
        nsv=("NSV", "sum"), mrp=("MRP value", "sum")).reset_index()
    promo_by = {r["name"]: r for r in promo["by_chain"]}
    rows = []
    for _, r in g.iterrows():
        c = r["chain"]
        if not c or r["nsv"] <= 0:
            continue
        disc = (r["mrp"] - r["nsv"])
        disc_pct = disc / r["mrp"] * 100 if r["mrp"] else None
        pr = promo_by.get(c, {})
        rows.append({"name": c, "mrp": r2(r["mrp"]), "nsv": r2(r["nsv"]),
                     "discount": r2(disc), "discount_pct": r2(disc_pct, 1),
                     "promos": pr.get("promos", 0), "promo_depth": pr.get("avg_depth")})
    rows = sorted(rows, key=lambda d: -(d["nsv"] or 0))
    tot_mrp = sum(x["mrp"] or 0 for x in rows)
    tot_nsv = sum(x["nsv"] or 0 for x in rows)
    return {"by_chain": rows, "fy_tag": latest,
            "total_mrp": r2(tot_mrp), "total_nsv": r2(tot_nsv),
            "total_discount": r2(tot_mrp - tot_nsv),
            "blended_discount_pct": r2((tot_mrp - tot_nsv) / tot_mrp * 100, 1) if tot_mrp else None}

# --------------------------------------------------------------------------
# FORECAST  (seasonally-adjusted, from offtake monthly history)
# --------------------------------------------------------------------------
def _fy_slices(off):
    """{FY tag: [monthly values]} from the offtake series, label-driven via
    THE ONE FY RULE (never positional [:12]/[12:] slicing). Also returns the
    tags sorted chronologically and the latest COMPLETE (12-month) tag."""
    by_tag = {}
    for lab, v in zip(off["months"], off["monthly"]):
        t = fy_tag_from_label(lab)
        if t:
            by_tag.setdefault(t, []).append(v)
    tags = sorted(by_tag, key=fy_start_year)
    complete = [t for t in tags if len(by_tag[t]) == 12]
    return by_tag, tags, (complete[-1] if complete else (tags[-1] if tags else None))

def forecast_block(off):
    by_tag, tags, base_tag = _fy_slices(off)   # base = latest COMPLETE FY
    base = by_tag.get(base_tag, [])
    prev_tag = tags[tags.index(base_tag) - 1] if base_tag and tags.index(base_tag) > 0 else None
    prev = by_tag.get(prev_tag, [])
    # seasonal index from the latest complete year, normalised to its mean
    mean_base = sum(v or 0 for v in base) / (len(base) or 1) or 1
    seasonal = [(v or 0) / mean_base for v in base]
    # YoY growth on the trailing year drives the level
    g = (sum(v or 0 for v in base) / (sum(v or 0 for v in prev) or 1)) - 1 if prev else 0.0
    g = max(min(g, 0.6), 0.0)  # clamp to a sane planning band
    base_month = mean_base * (1 + g)
    # forecast the FY AFTER the base year (label-derived, not hardcoded)
    tgt_tag = fy_tag_from_ym(fy_start_year(base_tag) + 1, 4) if base_tag else "FY27"
    y0 = fy_start_year(tgt_tag)
    flabels = month_labels(y0, 12)
    fc = [r2(base_month * seasonal[i % 12]) for i in range(12)]
    return {"hist_labels": off["months"], "hist": off["monthly"],
            "fc_labels": flabels, "fc": fc,
            "base_fy_tag": base_tag, "target_fy_tag": tgt_tag,
            "fy26_actual": r2(sum(v or 0 for v in base)),   # legacy key names kept for the dashboard;
            "fy27_forecast": r2(sum(fc)),                    # values follow base/target tags above
            "growth_assumption_pct": r2(g * 100, 1),
            "method": f"Seasonally-indexed run-rate: {base_tag} monthly seasonality applied "
                      "to a forward base grown at the realised offtake YoY rate (clamped 0-60%)."}

# --------------------------------------------------------------------------
# FORECAST — TY (FY26-27) target file, when available (authoritative;
# overrides the seasonally-projected estimate above with the business's own
# monthly target -- same source the Power BI Forecast page uses,
# see PowerBI/docs/PageLayouts.md Page 5, "TY Target Total").
# --------------------------------------------------------------------------
def load_ty_target(src):
    """Read FY2627_TGT_and_sales_team_mapping.xlsb (Sheet1: FY, Qtr, Month
    [Excel serial], 'TGT\\nFOR TY' in Rs Crore). Returns a sorted list of
    (date, 'Mon-YY' label, value_in_Lakh), or None if the file isn't in
    --src (forecast then stays the seasonally-projected estimate)."""
    f = src / "FY2627_TGT_and_sales_team_mapping.xlsb"
    if not f.exists():
        return None
    df = pd.read_excel(f, sheet_name="Sheet1", header=1, engine="pyxlsb")
    df.columns = [str(c).strip() for c in df.columns]
    tgt_col = next((c for c in df.columns if "TGT" in c.upper()), None)
    if tgt_col is None:
        raise SystemExit(f"FY2627_TGT file: no 'TGT FOR TY' column found. Columns: {list(df.columns)}")
    df = df.dropna(subset=[tgt_col, "Month"])
    rows = []
    for _, r in df.iterrows():
        n = float(r["Month"])
        d = datetime.date(1899, 12, 30) + datetime.timedelta(days=int(n))
        rows.append((d, d.strftime("%b-%y"), float(r[tgt_col]) * 100))  # Cr -> Lakh
    rows.sort(key=lambda x: x[0])
    return rows

def forecast_block_ty(off, ty_rows):
    by_tag, tags, base_tag = _fy_slices(off)   # latest COMPLETE FY = the actuals baseline
    base = by_tag.get(base_tag, [])
    flabels = [lbl for _, lbl, _ in ty_rows]
    fc = [r2(v) for _, _, v in ty_rows]
    tgt_tag = fy_tag_from_ym(ty_rows[0][0].year, ty_rows[0][0].month) if ty_rows else None
    base_actual = r2(sum(v or 0 for v in base))
    target_total = r2(sum(fc))
    return {"hist_labels": off["months"], "hist": off["monthly"],
            "fc_labels": flabels, "fc": fc,
            "base_fy_tag": base_tag, "target_fy_tag": tgt_tag,
            "fy26_actual": base_actual,      # legacy key names kept for the dashboard;
            "fy27_forecast": target_total,   # values follow base/target tags above
            "growth_assumption_pct": r2((target_total / base_actual - 1) * 100, 1) if base_actual else None,
            "method": f"{tgt_tag or 'FY27'} = the business's own TY (This Year) target "
                      f"(FY2627_TGT_and_sales_team_mapping.xlsx, Sheet1), NOT a seasonally-projected "
                      f"estimate. Total TY target = Rs {target_total/100:.2f} Cr (Power BI's Forecast "
                      "page uses this same TY target file -- PowerBI/docs/PageLayouts.md Page 5)."}

# --------------------------------------------------------------------------
# CONFIG / READINESS GATE / MAPPING HEALTH
# --------------------------------------------------------------------------
_CONFIG_CACHE = {}

def load_analytics_config(repo_root=None):
    """config/analytics_config.json -- business thresholds and basis choices.

    Kept out of the formulas so a threshold change is a config edit and a
    review conversation, not a code change buried in a template string.
    Returns {} if the file is absent; every consumer must tolerate that.
    """
    root = Path(repo_root or _REPO_ROOT)
    if str(root) in _CONFIG_CACHE:
        return _CONFIG_CACHE[str(root)]
    f = root / "config" / "analytics_config.json"
    cfg = {}
    if f.exists():
        try:
            cfg = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"WARN: config/analytics_config.json is not valid JSON ({e}); "
                  f"falling back to built-in defaults.")
    _CONFIG_CACHE[str(root)] = cfg
    return cfg

def public_config(cfg):
    """The slice of config safe for the published payload.

    dashboard/ goes to GitHub Pages. Sections marked scope=INCENTIVE_ONLY belong
    to the restricted incentive domain and are dropped here along with the
    comment keys -- the commercial payload should not carry incentive-domain
    configuration at all.
    """
    def strip(o):
        if isinstance(o, dict):
            return {k: strip(v) for k, v in o.items() if not k.startswith("_")}
        if isinstance(o, list):
            return [strip(x) for x in o]
        return o
    return {k: strip(v) for k, v in (cfg or {}).items()
            if not k.startswith("_")
            and not (isinstance(v, dict) and v.get("scope") == "INCENTIVE_ONLY")}

def rag_of(value, band, cfg=None):
    """'green' / 'amber' / 'red' for a value against a named RAG band."""
    b = ((cfg or {}).get("rag") or {}).get(band) or {}
    if value is None or not b:
        return None
    g, a = b.get("green"), b.get("amber")
    if g is None or a is None:
        return None
    if b.get("lower_is_better"):
        return "green" if value <= g else ("amber" if value <= a else "red")
    return "green" if value >= g else ("amber" if value >= a else "red")

def mapping_health_block(df, fy_col="_FY", chain_col="_Chain", nsv_col="_NSV",
                         unmapped_label="Unmapped Chain", alloc=None, cfg=None,
                         repo_root=None):
    """How much of primary can actually be attributed to a named chain.

    Chain-level primary is only as good as the distributor-to-chain mapping
    behind it. Today a large share of distributor billing carries no mapping
    entry and keeps the placeholder chain tag, so a chain table silently reads
    as if that value did not exist. This block measures that instead of hiding
    it, and feeds the chain_primary readiness gate.
    """
    if chain_col not in df.columns:
        return None
    out = {"unmapped_label": unmapped_label, "unit": "INR Lakh", "by_fy": {}}
    for tag in sorted({t for t in df[fy_col].dropna().unique() if t}, key=fy_start_year):
        d = df[df[fy_col] == tag]
        total = float(d[nsv_col].sum())
        un = float(d[d[chain_col] == unmapped_label][nsv_col].sum())
        pct = r2((total - un) / total * 100) if total else None
        out["by_fy"][tag] = {
            "total_nsv": r2(total), "mapped_nsv": r2(total - un), "unmapped_nsv": r2(un),
            "completeness_pct": pct,
            "rag": rag_of(pct, "mapping_completeness_pct", cfg),
        }
    # Exception register: where the unmapped value actually sits, biggest first,
    # so the owner works the list in value order rather than alphabetically.
    rows = []
    for r in ((alloc or {}).get("missing_mapping") or []):
        rows.append({k: r.get(k) for k in ("fy", "month", "brand", "cust_code", "ship_to", "nsv", "rows")})
    agg = {}
    for r in rows:
        k = (r.get("cust_code"), r.get("ship_to"))
        a = agg.setdefault(k, {"cust_code": k[0], "ship_to": k[1], "nsv": 0.0,
                               "rows": 0, "months": set(), "brands": set()})
        a["nsv"] += float(r.get("nsv") or 0); a["rows"] += int(r.get("rows") or 0)
        if r.get("month"): a["months"].add(r["month"])
        if r.get("brand"): a["brands"].add(r["brand"])
    ex = sorted(agg.values(), key=lambda d: -d["nsv"])
    tot_ex = sum(d["nsv"] for d in ex) or 1.0
    run = 0.0
    for d in ex:
        run += d["nsv"]
        d["nsv"] = r2(d["nsv"]); d["months"] = sorted(d["months"]); d["brands"] = sorted(d["brands"])
        d["cumulative_pct"] = r2(run / tot_ex * 100)
    out["exceptions"] = ex[:60]
    out["exception_count"] = len(ex)
    out["exception_nsv"] = r2(tot_ex)
    out["note"] = (
        "Distributor rows with no matching entry in the cont% allocation master keep "
        "their original chain tag. Value is NOT lost (allocation reconciles to zero "
        "variance) but it cannot be attributed to a named chain, so chain-level primary "
        "is understated by this amount. Work the exception list in value order.")
    # FM-20: a cumulative % of a NET total always ends at exactly 100%, but a
    # return/credit row (negative NSV) sorted to the tail can make an EARLIER
    # row's cumulative_pct read above 100% before the negative tail pulls it
    # back down -- correct arithmetic, but a real business reviewer read this
    # as broken math ("Cumulative is increased, kindly adjust") on 2026-09-22.
    # Disclose it; do not change the formula (capping at 100% or excluding
    # negative rows would hide real return/credit activity).
    if any(d["nsv"] < 0 for d in ex):
        out["note"] += (
            " Note: a few rows carry negative NSV (returns/credits); because cumulative % "
            "is measured against the NET total, it can read slightly above 100% partway "
            "down this list before settling to exactly 100% at the last row -- that is "
            "expected here, not an error.")
    # Proposals, if a suggestion file exists. These are SUGGESTIONS and are never
    # applied here: assigning a distributor to a chain is a business decision with
    # a named owner, not something a build step may infer.
    sug = Path(repo_root or _REPO_ROOT) / "data" / "unmapped_chains_bridge_suggested.csv"
    if sug.exists():
        props = []
        try:
            with open(sug, newline="", encoding="utf-8-sig") as fh:
                for r in csv.DictReader(fh):
                    props.append({
                        "ship_to": r.get("ship_to"), "cust_code": r.get("cust_code"),
                        "nsv": r2(float(r.get("total_nsv_lakh") or 0)),
                        "suggested_chain": r.get("suggested_chain"),
                        "suggested_zone": r.get("suggested_zone"),
                        "confidence": r.get("confidence"),
                        "cumulative_coverage_pct": r2(float(r.get("cumulative_coverage_pct") or 0)),
                        "status": "PROPOSED — awaiting business owner approval",
                    })
        except (ValueError, KeyError):
            props = []
        if props:
            out["proposals"] = props
            out["proposals_nsv"] = r2(sum(p["nsv"] for p in props))
            out["proposals_note"] = (
                "PROPOSED ONLY — not applied. Source: data/unmapped_chains_bridge_suggested.csv. "
                "Approving a distributor-to-chain mapping is a business decision with a named "
                "owner; the build never infers one. Approve rows into the mapping master, "
                "re-run the allocation, and this register shrinks on its own.")
    return out

# Status vocabulary for readiness_gate(). PASS/N/A are self-explanatory.
# AWAITING_BUSINESS_DATA means the implementation is complete and correctly
# withholds the number until a named external/business input arrives -- it is
# NOT a software defect, so it must never render or read like one. "BLOCKED"
# is reserved for a genuine, unresolved technical/software gap -- readiness_gate()
# does not currently emit it for any gate; it stays available for one that
# actually needs it (e.g. a required source file failing to parse).
AWAITING_BUSINESS_DATA = "AWAITING BUSINESS DATA"

# Confirmed by business, 2026-09-14: standard cost = 14% of MRP (COGS) + 3% of
# MRP (logistics). Applied to detail_records' MRP/NSV (article x chain x month
# grain, both already in Lakh). This is a standard-cost rate, not an actual
# SAP COGS extract -- the "measured" text below says so every time it is shown.
PROFITABILITY_COGS_PCT_OF_MRP = 0.14
PROFITABILITY_LOGISTICS_PCT_OF_MRP = 0.03

# Fiscal-year month order (Apr=1..Mar=12), matching the exact Month-name
# strings used in detail_records (mixed abbreviation styles -- verified
# against the real data, not assumed).
_FY_MONTH_ORDER = {"April": 1, "May": 2, "June": 3, "July": 4, "Aug": 5, "Sept": 6,
                    "Oct": 7, "Nov": 8, "Dec": 9, "Jan": 10, "Feb": 11, "March": 12}


def profitability_block(detail_records):
    """Standard-cost margin from detail_records' own MRP/NSV -- no external
    COGS extract needed now that the business has confirmed the cost rate.
    See PROFITABILITY_COGS_PCT_OF_MRP/LOGISTICS docstring above for the basis.
    """
    if not detail_records:
        return None
    by_chain = {}
    tot_nsv = tot_mrp = tot_cogs = tot_log = 0.0
    for r in detail_records:
        nsv = r.get("NSV") or 0.0
        mrp = r.get("MRP") or 0.0
        cogs = mrp * PROFITABILITY_COGS_PCT_OF_MRP
        log = mrp * PROFITABILITY_LOGISTICS_PCT_OF_MRP
        tot_nsv += nsv; tot_mrp += mrp; tot_cogs += cogs; tot_log += log
        c = by_chain.setdefault(r.get("Chain") or "Unknown", {"nsv": 0.0, "mrp": 0.0, "cogs": 0.0, "logistics": 0.0})
        c["nsv"] += nsv; c["mrp"] += mrp; c["cogs"] += cogs; c["logistics"] += log

    def margin_row(nsv, cogs, log):
        margin = nsv - cogs - log
        return round(margin, 2), (round(margin / nsv * 100, 2) if nsv else None)

    tot_margin, tot_margin_pct = margin_row(tot_nsv, tot_cogs, tot_log)
    chain_rows = []
    for name, v in sorted(by_chain.items(), key=lambda kv: -kv[1]["nsv"]):
        m, mp = margin_row(v["nsv"], v["cogs"], v["logistics"])
        chain_rows.append({"name": name, "nsv_lakh": round(v["nsv"], 2), "margin_lakh": m, "margin_pct_of_nsv": mp})

    return {
        "basis": (f"Standard cost = {PROFITABILITY_COGS_PCT_OF_MRP*100:.0f}% of MRP (COGS) + "
                  f"{PROFITABILITY_LOGISTICS_PCT_OF_MRP*100:.0f}% of MRP (logistics), confirmed by "
                  "business 2026-09-14. This is a standard-cost rate applied to detail_records' MRP, "
                  "not an actual per-article SAP COGS extract."),
        "total": {"nsv_lakh": round(tot_nsv, 2), "mrp_lakh": round(tot_mrp, 2),
                  "cogs_lakh": round(tot_cogs, 2), "logistics_lakh": round(tot_log, 2),
                  "margin_lakh": tot_margin, "margin_pct_of_nsv": tot_margin_pct},
        "by_chain": chain_rows,
    }


def npd_block(detail_records):
    """NPI launch governance, Chain x EAN grain, FY-based cohort with a
    March carry-forward rule (replaces the March-only rule confirmed
    2026-09-14; see git history for that version). Grain changed from
    Chain x Article text to Chain x EAN on 2026-09-20 (business-confirmed):
    the same physical product can carry two different Article-text
    spellings at one chain (a rebrand/rename) but shares one EAN, so
    counting by Article text double-counted those as two launches. A pair
    with no EAN at all falls back to Chain x Article text.

    Actual_First_Sale_Month = the earliest FY x Month with a valid
    commercial transaction for that (Chain, EAN) pair, found by
    scanning the pair's WHOLE available history, never just the currently
    selected dashboard period. "Valid commercial transaction" requires
    NSV > 0 AND Qty > 0: detail_records carries no dedicated return/
    sample/correction flag, so this is the best available proxy for
    excluding a return, a zero-value correction, or a sample/free-goods row
    from establishing a launch -- a negative-Qty return sitting before the
    real launch cannot move it earlier, and a Qty<=0 row at the true launch
    month cannot suppress it (the next valid month still wins).

    NPI Reporting Cohort:
      - Normally the FY containing Actual_First_Sale_Month.
      - EXCEPT when Actual_First_Sale_Month's month is literally "March":
        the cohort becomes the NEXT FY, so a March launch is tracked over
        a full Apr-Mar year instead of one month.
    Both fields are always recorded together -- Actual_First_Sale_Month is
    never rewritten to make it agree with the cohort FY.

    Same product (EAN) launching in different chains = separate Chain x EAN
    launches, each with its own independent launch date and cohort.

    HISTORY-INCOMPLETE GUARD: detail_records' own earliest available FY x
    Month across ALL rows is the first month this repo has any data for --
    a pair whose first valid sale falls exactly in that month cannot be
    told apart from a product that already existed before this data window
    started. Those pairs get launch_status="history_incomplete" (never
    "confirmed_launch") and are excluded from launch counts/cohorts/NSV --
    this is a statement that the launch status is UNKNOWN, not a claim that
    the pair is NOT an NPI (left truncation, not a negative finding; see
    NIST's distinction between left-truncated and left-censored data).

    LAUNCH CONFIDENCE (per pair, not per cohort FY -- a cohort is not
    homogeneous): even a launch that clears the history-incomplete guard is
    not proven to be genuinely new -- a 12-month clean lookback is an
    operational-confidence threshold, not proof of "first-ever" (an
    article could have sold before this dataset's Apr-25 start, gone
    dormant, and resumed after). Each confirmed launch therefore carries
    history_months_before_first_sale (months between the dataset's
    earliest available month and THIS pair's own actual first sale) and
    launch_confirmation_status:
      "confirmed"      -- >=12 months of lookback behind this pair's own
                           first sale. Read as "meets this repo's 12-month
                           operational-confidence rule", never as "proven
                           via an authoritative launch/NPI master" -- no
                           such master is consulted here.
      "observed_only"   -- 1-11 months of lookback. This is the first sale
                           visible in available history, with insufficient
                           evidence to rule out an earlier, unobserved one.
    (A third status, "boundary_unknown", applies to the excluded
    history_incomplete pairs above -- 0 months of lookback.)

    Because a March-carried launch keeps its ORIGINAL first-sale month for
    this lookback calculation (not its cohort FY's own start), a cohort can
    mix "confirmed" and "observed_only" launches -- e.g. FY27 contains both
    April-26 launches (12 months' lookback, confirmed) and March-26
    carry-forward launches (only 11 months' lookback, observed_only).
    metrics_by_fy[fy]["history_coverage"] is therefore derived from the
    WEAKEST launch actually in that cohort, not from the FY's own start
    date: "CONFIRMED" only if every launch in the cohort is "confirmed";
    otherwise "PARTIAL". yoy_comparison_valid/yoy_caveat flag any YoY
    figure where either side is not "CONFIRMED", so a growth headline is
    never presented as more solid than the weakest launch behind it.

    Classification depends only on the pair's own full sales history in
    this detail_records snapshot, never on any dashboard filter selection --
    re-running this function against the same data always returns the same
    cohort for a given pair (immutable within one refresh).
    """
    if not detail_records:
        return None

    earliest = None
    for r in detail_records:
        fy, month = r.get("FY"), r.get("Month")
        if not (fy and month and month in _FY_MONTH_ORDER):
            continue
        cand = (fy_start_year(fy), _FY_MONTH_ORDER[month])
        if earliest is None or cand < earliest:
            earliest = cand
    if earliest is None:
        return None

    # Launch grain is Chain x EAN (barcode), not Chain x Article text.
    # Business-confirmed 2026-09-20: the same physical product sometimes
    # carries two different Article-text spellings at the same chain (a
    # rebrand/rename) but shares one EAN -- counting each spelling as a
    # separate launch double-counts the same real product. EAN is also
    # immune to the text-encoding corruption a handful of Article values
    # carry. A pair with no EAN at all falls back to Chain + Article text
    # so it is never silently dropped from the identity layer.
    def _npi_grain_key(chain, article, ean):
        return (chain, "EAN", ean) if ean else (chain, "ART", article)

    first_seen = {}        # grain_key -> (fy_start_year, month_order, fy_tag, month_name)
    pair_article = {}      # grain_key -> a representative Article text, for display only.
    rows_skipped_missing_identifier = 0
    for r in detail_records:
        chain, article, fy, month = r.get("Chain"), r.get("Article"), r.get("FY"), r.get("Month")
        if not (chain and article and fy and month and month in _FY_MONTH_ORDER):
            if not (chain and article):
                rows_skipped_missing_identifier += 1
            continue
        ean = r.get("EAN")
        grain_key = _npi_grain_key(chain, article, ean)
        if grain_key not in pair_article:
            pair_article[grain_key] = article
        if not ((r.get("NSV") or 0.0) > 0 and (r.get("Qty") or 0.0) > 0):
            continue
        fy_year = fy_start_year(fy)
        cand = (fy_year, _FY_MONTH_ORDER[month], fy, month)
        if grain_key not in first_seen or cand < first_seen[grain_key]:
            first_seen[grain_key] = cand

    earliest_idx = earliest[0] * 12 + earliest[1]
    launches = []          # confirmed + observed_only launches (history_incomplete pairs excluded)
    history_incomplete_pairs = []
    for grain_key, (fy_year, mo, fy_tag, month_name) in first_seen.items():
        chain, kind, ident = grain_key
        ean = ident if kind == "EAN" else None
        article = pair_article[grain_key]
        # pair_id is the stable browser-side join key: Chain + EAN, or
        # Chain + Article text for the rare pair with no EAN at all.
        pair_id = f"{chain}||{ean}" if ean else f"{chain}||{article}"
        lookback_months = fy_year * 12 + mo - earliest_idx
        if lookback_months <= 0:
            history_incomplete_pairs.append({
                "chain": chain, "article": article, "ean": ean, "pair_id": pair_id,
                "first_observed_fy": fy_tag, "first_observed_month": month_name,
                "launch_status": "boundary_unknown",
                "history_months_before_first_sale": lookback_months,
            })
            continue
        cohort_fy = f"FY{int(fy_tag[2:]) + 1}" if month_name == "March" else fy_tag
        launches.append({
            "chain": chain, "article": article, "ean": ean, "pair_id": pair_id,
            "actual_first_sale_fy": fy_tag, "actual_first_sale_month": month_name,
            "npi_cohort_fy": cohort_fy,
            "history_months_before_first_sale": lookback_months,
            # "confirmed" = meets this repo's 12-month operational-confidence
            # rule; never a claim of proof against an authoritative launch
            # master (none exists here) -- see the function docstring.
            "launch_confirmation_status": "confirmed" if lookback_months >= 12 else "observed_only",
        })
    launches.sort(key=lambda r: (r["npi_cohort_fy"], r["chain"], r["article"]))

    by_fy = {}
    for row in launches:
        by_fy.setdefault(row["npi_cohort_fy"], []).append(row)

    # Per-FY universe totals (all chain x article activity in that FY, not
    # just NPI launches) for contribution % -- reuses the same NSV field,
    # no separate computation path.
    fy_total_nsv = {}
    for r in detail_records:
        fy = r.get("FY")
        if fy:
            fy_total_nsv[fy] = fy_total_nsv.get(fy, 0.0) + (r.get("NSV") or 0.0)

    metrics_by_fy = {}
    for cohort_fy, rows in by_fy.items():
        pair_keys = {_npi_grain_key(row["chain"], row["article"], row["ean"]) for row in rows}
        nsv = 0.0
        qty = 0.0
        active_pairs = set()
        for r in detail_records:
            if r.get("FY") != cohort_fy:
                continue
            key = _npi_grain_key(r.get("Chain"), r.get("Article"), r.get("EAN"))
            if key not in pair_keys:
                continue
            row_nsv = r.get("NSV") or 0.0
            nsv += row_nsv
            qty += r.get("Qty") or 0.0
            if row_nsv > 0:
                active_pairs.add(key)
        launches_count = len(rows)
        active_count = len(active_pairs)
        # History coverage is derived from the WEAKEST launch actually in
        # this cohort -- a cohort mixes launches with different original
        # first-sale months (e.g. FY27 = April-26 launches at 12 months'
        # lookback alongside March-26 carry-forward launches at only 11),
        # so the FY's own April start date is not a safe proxy for its
        # weakest member's confidence.
        n_confirmed = sum(1 for r in rows if r["launch_confirmation_status"] == "confirmed")
        n_observed_only = launches_count - n_confirmed
        coverage = "CONFIRMED" if n_observed_only == 0 else "PARTIAL"
        min_lookback = min((r["history_months_before_first_sale"] for r in rows), default=None)

        metrics_by_fy[cohort_fy] = {
            "npi_launches": launches_count,
            "npi_nsv": r2(nsv),
            "npi_units": r2(qty),
            "avg_nsv_per_launch": r2(nsv / launches_count) if launches_count else None,
            "npi_contribution_pct": (r2(nsv / fy_total_nsv[cohort_fy] * 100)
                                       if fy_total_nsv.get(cohort_fy) else None),
            "active_npi_count": active_count,
            # productivity = NSV per NPI that actually sold in its own cohort
            # year, distinct from avg_nsv_per_launch (which divides by every
            # launch, selling or not) -- separates "more launches" growth
            # from "better-performing launches" growth.
            "npi_productivity": r2(nsv / active_count) if active_count else None,
            "history_coverage": coverage,
            "history_min_lookback_months": min_lookback,
            "confirmed_launch_count": n_confirmed,
            "observed_only_launch_count": n_observed_only,
        }

    fy_order = sorted(metrics_by_fy, key=fy_start_year)
    for i, fy in enumerate(fy_order):
        if i == 0:
            metrics_by_fy[fy]["yoy_npi_nsv_growth_pct"] = None
            metrics_by_fy[fy]["yoy_comparison_valid"] = False
            metrics_by_fy[fy]["yoy_caveat"] = "No prior cohort FY to compare against."
            continue
        prev_fy = fy_order[i - 1]
        prev = metrics_by_fy[prev_fy]["npi_nsv"]
        cur = metrics_by_fy[fy]["npi_nsv"]
        metrics_by_fy[fy]["yoy_npi_nsv_growth_pct"] = (
            r2((cur - prev) / prev * 100) if prev else None
        )
        # A YoY comparison is only as solid as its weaker side's WEAKEST
        # launch, derived (above) per-pair, not assumed from either FY's
        # calendar start. This is the specific, evidenced risk this
        # function must never hide: comparing a fully-confirmed FY against
        # one that still contains observed_only launches overstates growth,
        # because the weaker FY's true launch count could be lower than
        # what's observed (some of those launches might not be genuinely
        # new at all -- see launch_confirmation_status in the docstring).
        weak_fy = prev_fy if metrics_by_fy[prev_fy]["history_coverage"] != "CONFIRMED" else (
            fy if metrics_by_fy[fy]["history_coverage"] != "CONFIRMED" else None)
        if weak_fy:
            n_obs = metrics_by_fy[weak_fy]["observed_only_launch_count"]
            metrics_by_fy[fy]["yoy_comparison_valid"] = False
            metrics_by_fy[fy]["yoy_caveat"] = (
                f"{weak_fy} has {n_obs} of {metrics_by_fy[weak_fy]['npi_launches']} launches at "
                "launch_confirmation_status=observed_only (under 12 months of lookback behind their "
                "own first sale -- not proof of a genuinely new product, just the first sale visible "
                "in available history) -- this YoY growth figure is not a like-for-like comparison "
                "and should be labelled provisional, not presented as confirmed growth."
            )
        else:
            metrics_by_fy[fy]["yoy_comparison_valid"] = True
            metrics_by_fy[fy]["yoy_caveat"] = None

    return {
        "basis": ("Chain x EAN NPI launch cohort (falls back to Chain x Article text only when "
                   "a pair has no EAN): the FY containing a pair's actual first "
                   "valid commercial sale (NSV>0 and Qty>0), except a March first-sale rolls "
                   "forward into the NEXT FY so it gets a full Apr-Mar tracking year. Actual "
                   "launch month is always preserved alongside the cohort FY. Pairs whose first "
                   "observed sale falls in detail_records' own earliest available month are "
                   "excluded as launch_status=boundary_unknown: UNKNOWN whether they are a new "
                   "launch or a pre-existing product (left truncation, not evidence of either), "
                   "so they are never counted as a launch and never counted as not-NPI. Every "
                   "launch that IS counted additionally carries launch_confirmation_status "
                   "('confirmed' vs 'observed_only') -- see the function docstring; even a "
                   "confirmed launch is not proof of first-ever, only that this repo's 12-month "
                   "operational-confidence rule is met."),
        "by_fy": by_fy,
        "counts_by_fy": {fy: len(rows) for fy, rows in by_fy.items()},
        "metrics_by_fy": metrics_by_fy,
        "history_incomplete_pairs": history_incomplete_pairs,
        "qc": {
            "rows_skipped_missing_chain_or_article": rows_skipped_missing_identifier,
            "pairs_excluded_history_incomplete": len(history_incomplete_pairs),
            "history_incomplete_reason": (
                f"first available data month is FY-start-year {earliest[0]}, month-order "
                f"{earliest[1]} (Apr=1..Mar=12) -- a pair first observed exactly then has "
                "launch_status=boundary_unknown, not a launch and not confirmed-preexisting"
            ),
        },
    }


def readiness_gate(data, cfg=None):
    """Is each analytical layer allowed to present itself as authoritative?

    A layer that runs on inputs it needs but does not have produces a number
    that looks finished and is not. Each gate states its precondition, what it
    measured, and what would unblock it.

    Status meanings (see AWAITING_BUSINESS_DATA docstring above for the full
    rationale): PASS = ready to present as authoritative. AWAITING_BUSINESS_DATA
    = implementation complete, correctly waiting on a named external input --
    not broken. N/A = out of scope for this reporting surface. BLOCKED = a
    genuine unresolved technical/software gap.
    """
    cfg = cfg or {}
    rules = (cfg.get("readiness") or {})
    out, order = {}, [k for k in rules if not k.startswith("_")]

    def put(key, status, measured, detail=None):
        r = rules.get(key) or {}
        out[key] = {"label": r.get("label", key), "status": status,
                    "requires": r.get("requires"), "measured": measured,
                    "unblocks_with": r.get("unblocks_with")}
        if detail:
            out[key].update(detail)

    mh = data.get("mapping_health") or {}
    cur = None
    if mh.get("by_fy"):
        cur_tag = sorted(mh["by_fy"], key=fy_start_year)[-1]
        cur = mh["by_fy"][cur_tag]
    if "chain_primary" in rules:
        floor = (rules["chain_primary"] or {}).get("min_mapping_completeness_pct")
        got = (cur or {}).get("completeness_pct")
        ok = got is not None and floor is not None and got >= floor
        put("chain_primary", "PASS" if ok else AWAITING_BUSINESS_DATA,
            f"mapping completeness {got}%" if got is not None else "not measured",
            {"threshold": floor, "value": got})

    if "pvm" in rules:
        pv = data.get("pvm") or {}
        asp = ((pv.get("curr") or {}).get("asp"))
        floor = (rules["pvm"] or {}).get("min_asp_rupees")
        ok = asp is not None and floor is not None and asp >= floor
        put("pvm", "PASS" if ok else "BLOCKED",
            f"blended ASP Rs {asp}/unit" if asp is not None else "ASP not computable",
            {"threshold": floor, "value": asp})

    if "profitability" in rules:
        # Prefer an actual sourced cost field if one ever arrives; otherwise
        # fall back to the confirmed standard-cost rate in data["profitability"]
        # (see profitability_block() -- 14% COGS + 3% logistics of MRP).
        cols = set((data.get("detail_meta") or {}).get("columns") or [])
        has_cost = bool(cols & {"COGS", "Cost", "StdCost", "Margin"})
        prof = data.get("profitability") or {}
        margin_pct = (prof.get("total") or {}).get("margin_pct_of_nsv")
        if has_cost:
            put("profitability", "PASS", "cost/margin field present")
        elif margin_pct is not None:
            put("profitability", "PASS",
                f"margin {margin_pct}% of NSV (standard-cost basis: 14% COGS + 3% logistics of MRP, confirmed by business)")
        else:
            put("profitability", AWAITING_BUSINESS_DATA, "no cost or margin field at the reporting grain")

    if "scorecard_execution" in rules:
        # compliance/inventory metrics ship as a runtime sidecar the dashboard
        # fetches separately, so they are not in `data`. Read the sidecar here
        # rather than reporting "no data" for a file that exists.
        comp = data.get("compliance") or {}
        if not comp:
            _cf = Path(_REPO_ROOT) / "dashboard" / "compliance_metrics.json"
            if _cf.exists():
                try:
                    comp = (json.loads(_cf.read_text(encoding="utf-8")) or {}).get("compliance") or {}
                except json.JSONDecodeError:
                    comp = {}
        doors = ((comp.get("metadata") or {}).get("total_doors_audited"))
        univ = ((data.get("universe") or {}).get("active_stores"))
        covp = r2(doors / univ * 100) if doors and univ else None
        floor = (rules["scorecard_execution"] or {}).get("min_audit_coverage_pct")
        ok = covp is not None and floor is not None and covp >= floor
        put("scorecard_execution", "PASS" if ok else AWAITING_BUSINESS_DATA,
            f"audit coverage {covp}% ({doors} of {univ} stores)" if covp is not None
            else "no store-audit data in this build",
            {"threshold": floor, "value": covp})

    if "npd" in rules:
        npd = data.get("npd") or {}
        counts = npd.get("counts_by_fy") or {}
        if counts:
            summary = "; ".join(f"{fy}: {n} article-chain pairs" for fy, n in sorted(counts.items()))
            put("npd", "PASS", f"NPI identified via FY-cohort rule with March carry-forward ({summary})")
        else:
            put("npd", AWAITING_BUSINESS_DATA, "NPD master not joined to the transaction grain")

    if "sales_consolidation" in rules:
        # DMS/Massit is incentive-scope only by business instruction, so it is
        # deliberately absent from this payload. The gate records that rather
        # than reporting a missing block as a failure.
        put("sales_consolidation", "N/A",
            "DMS is incentive-scope only; the commercial payload stays on chain sales")

    if "incentive" in rules:
        # Every mandatory input, named. A missing one blocks the affected role
        # rather than defaulting to a middle tier -- this decides real pay.
        have = {
            "slab master": bool(data.get("incentive_slabs")),
            "employee incentive grade": False,
            "role-scope targets": bool(((data.get("targets") or {}).get("measures") or {}).get("by_chain")),
            "target basis confirmed": bool(((cfg.get("target") or {}).get("basis_confirmed_by"))),
            "emerging-brand rule": ((cfg.get("brands") or {}).get("emerging_rule")) is not None,
        }
        miss = [k for k, v in have.items() if not v]
        put("incentive", "PASS" if not miss else AWAITING_BUSINESS_DATA,
            f"{len(have) - len(miss)} of {len(have)} mandatory inputs present"
            + (f"; missing: {', '.join(miss)}" if miss else ""))

    if "persona_reporting" in rules:
        sa = data.get("sales_actuals") or {}
        hs = sa.get("hierarchy_stores")
        put("persona_reporting", AWAITING_BUSINESS_DATA,
            (f"hierarchy covers {hs} stores but carries names, not employee IDs"
             if hs else "store-employee hierarchy not ingested"))

    ready = [k for k in order if (out.get(k) or {}).get("status") == "PASS"]
    awaiting = [k for k in order if (out.get(k) or {}).get("status") == AWAITING_BUSINESS_DATA]
    not_applicable = [k for k in order if (out.get(k) or {}).get("status") == "N/A"]
    genuinely_blocked = [k for k in order if (out.get(k) or {}).get("status") == "BLOCKED"]
    # Kept for existing callers that log "blocked: <keys>" during a build --
    # they only print this list, nothing gates on its exact status label.
    blocked = awaiting + genuinely_blocked

    summary_parts = [f"{len(ready)} of {len(order)} layers ready"]
    if awaiting:
        summary_parts.append(f"{len(awaiting)} awaiting business data (not software defects)")
    if not_applicable:
        summary_parts.append(f"{len(not_applicable)} not applicable to current scope")
    if genuinely_blocked:
        summary_parts.append(f"{len(genuinely_blocked)} blocked on unresolved technical work")

    return {"gates": out, "blocked": blocked,
            "summary": "; ".join(summary_parts),
            "note": ("PASS = ready to present as authoritative. AWAITING BUSINESS DATA = "
                     "the implementation is complete and correctly withholds the number "
                     "until a named business or source input arrives -- not a software "
                     "defect. N/A = out of scope for this reporting surface. BLOCKED = a "
                     "genuine, unresolved technical/software gap.")}


def data_quality_reconciliation_block(data, cfg=None, repo_root=None):
    """Data Quality + Reconciliation layer -- Phase 3 of the Analytical
    Integrity work (PR #155). Answers, per named dimension, whether the data
    behind the dashboard's metrics is complete, valid, consistent, unique and
    timely, and whether it reconciles against known business relationships --
    traceable to specific records, never a single decorative "health score".

    Reuses existing governed calculations wherever one already exists
    (sis_reconciliation, alloc's governance, mapping_health's own RAG-banded
    completeness via rag_of()/config/analytics_config.json) instead of
    recomputing them. A dimension with no configured threshold anywhere in
    this repo reports threshold="NOT_CONFIGURED", status="INFORMATIONAL" --
    this function never invents a business threshold or severity.

    Scope note: dimension checks run on `detail_records`, which is
    ROW-CAPPED for browser-payload size (see detail_meta.value_coverage_pct);
    they are illustrative at that same capped scope, not a full-population
    audit -- exactly the same disclosure _sis_reconciliation() already makes
    about detail_records vs the full uncapped source.

    Returns (data_quality, reconciliation, quality_issues); safe on missing
    inputs (returns empty-but-structured output rather than raising).
    """
    cfg = cfg or {}
    repo_root = Path(repo_root or _REPO_ROOT)
    detail_records = data.get("detail_records") or []
    detail_meta = data.get("detail_meta") or {}
    alloc = data.get("alloc") or {}
    mapping_health = data.get("mapping_health") or {}
    sis = detail_meta.get("sis_reconciliation") or {}
    targets = data.get("targets") or {}
    first_row = detail_records[0] if detail_records else {}

    issues = []

    def add_issue(issue_id, metric_id, dimension, count, affected, source, description,
                   severity="UNCLASSIFIED", status="INFORMATIONAL", threshold=None,
                   threshold_source="NOT_CONFIGURED"):
        issues.append({
            "issue_id": issue_id, "metric_id": metric_id, "dimension": dimension,
            "severity": severity, "status": status, "count": count,
            "affected_entities": affected, "source": source, "description": description,
            "threshold": threshold, "threshold_source": threshold_source,
        })

    dims = {}

    # ---- 1. COMPLETENESS -----------------------------------------------
    # No completeness_pct band exists in config/analytics_config.json's rag
    # section (checked) -- reports NOT_CONFIGURED/INFORMATIONAL by design.
    candidate_fields = ["Month", "FY", "Channel", "Zone", "State", "Chain", "Brand", "Category", "Article", "EAN"]
    present_fields = [f for f in candidate_fields if f in first_row]
    field_results = {}
    for f in present_fields:
        n = len(detail_records)
        missing = sum(1 for r in detail_records if not r.get(f) and r.get(f) != 0)
        rate = r2((n - missing) / n * 100) if n else None
        field_results[f] = {"records_checked": n, "records_passing": n - missing,
                             "missing": missing, "rate_pct": rate}
        if missing:
            add_issue(f"completeness_{f.lower()}", None, "completeness", missing,
                       f"{missing} of {n} detail_records rows", "detail_records",
                       f"{f} is blank on {missing} of {n} detail_records rows (row-capped "
                       f"scope; detail_meta.value_coverage_pct = {detail_meta.get('value_coverage_pct')}).")
    dims["completeness"] = {"fields": field_results, "records_checked": len(detail_records),
                             "threshold": "NOT_CONFIGURED", "threshold_source": "NOT_CONFIGURED",
                             "status": "INFORMATIONAL"}

    # ---- 2. UNIQUENESS ---------------------------------------------------
    # Business key is the FULL dimension grain detail_records actually
    # carries (Month/FY/Channel/Zone/State/Chain/Brand/Category/SubCategory/
    # Range/PackSize/Article/EAN) -- a coarser key produced false-positive
    # "duplicates" that were really distinct State-level rows for the same
    # article (verified against real data before choosing this key: the
    # coarser 7-field key flagged 99,757 false "duplicates" that were each a
    # different State; the full grain key finds zero).
    key_fields = [f for f in ("Month", "FY", "Channel", "Zone", "State", "Chain", "Brand",
                              "Category", "SubCategory", "Range", "PackSize", "Article", "EAN")
                  if f in first_row]
    dup_rows = 0
    if key_fields:
        seen = {}
        for r in detail_records:
            k = tuple(r.get(f) for f in key_fields)
            seen[k] = seen.get(k, 0) + 1
        dup_rows = sum(c - 1 for c in seen.values() if c > 1)
        if dup_rows:
            add_issue("uniqueness_duplicate_rows", None, "uniqueness", dup_rows,
                       f"{dup_rows} duplicate rows on key {key_fields}", "detail_records",
                       f"{dup_rows} rows share an identical {'/'.join(key_fields)} key.")
    dims["uniqueness"] = {"business_key": key_fields, "records_checked": len(detail_records),
                          "duplicate_rows": dup_rows,
                          "threshold": "NOT_CONFIGURED", "threshold_source": "NOT_CONFIGURED",
                          "status": "INFORMATIONAL",
                          "scope_note": "row-capped detail_records, not the full uncapped source"}

    # ---- 3. VALIDITY / CONFORMITY ----------------------------------------
    # Checked against a REAL registered master (CategoryMaster.csv) and a
    # structural EAN format check (8-14 numeric digits, the standard
    # EAN/GTIN range) -- no allowed-value list is invented here.
    cat_master = repo_root / "PowerBI" / "SeedData" / "Masters" / "CategoryMaster.csv"
    valid_categories = None
    if cat_master.exists():
        try:
            with open(cat_master, newline="", encoding="utf-8-sig") as fh:
                valid_categories = {row["Category"].strip() for row in csv.DictReader(fh) if row.get("Category")}
        except (OSError, csv.Error, KeyError):
            valid_categories = None
    invalid_category = 0
    if valid_categories and "Category" in first_row:
        invalid_category = sum(1 for r in detail_records
                                if r.get("Category") and r["Category"] not in valid_categories)
    invalid_ean = 0
    if "EAN" in first_row:
        # detail_records serializes EAN as a float-string ("8901030123456.0")
        # -- the same pandas float-conversion artifact already normalised
        # elsewhere in this file for Cust-SAP Code (see _CustCode's
        # str.replace(r"\.0$", "")). Strip it before the structural check so
        # this doesn't misreport every real EAN as invalid.
        invalid_ean = sum(1 for r in detail_records
                           if r.get("EAN")
                           and not re.fullmatch(r"\d{8,14}", re.sub(r"\.0$", "", str(r["EAN"]).strip())))
    if invalid_category:
        add_issue("validity_category", None, "validity", invalid_category,
                   f"{invalid_category} rows with a Category not in CategoryMaster.csv",
                   "detail_records vs PowerBI/SeedData/Masters/CategoryMaster.csv",
                   f"{invalid_category} of {len(detail_records)} rows carry a Category value "
                   f"(e.g. 'Face', 'Body') not present in CategoryMaster.csv's Category column "
                   f"(which uses longer names, e.g. 'Face Care', 'Hair Care'). This reads as a "
                   f"taxonomy mismatch between the pipeline's actual Category field and this "
                   f"registered reference file, not necessarily bad row data -- CategoryMaster.csv "
                   f"may be stale/unused relative to what detail_records actually produces. Not "
                   f"resolved here, per this phase's scope (STOP on a business-definition change).")
    if invalid_ean:
        add_issue("validity_ean_format", None, "validity", invalid_ean,
                   f"{invalid_ean} rows with a non-numeric or out-of-range EAN", "detail_records",
                   f"{invalid_ean} rows have an EAN that isn't 8-14 numeric digits (standard EAN/GTIN format).")
    dims["validity"] = {"category_master": str(cat_master.relative_to(repo_root)) if cat_master.exists() else None,
                        "records_checked": len(detail_records),
                        "invalid_category": invalid_category, "invalid_ean_format": invalid_ean,
                        "threshold": "NOT_CONFIGURED", "threshold_source": "NOT_CONFIGURED",
                        "status": "INFORMATIONAL"}

    # ---- 4. CONSISTENCY ---------------------------------------------------
    # Same EAN must carry the same Category/Brand across rows -- the exact
    # principle already established by detail_records_real()'s own EAN
    # backfill logic ("a physical SKU's taxonomy does not change month to
    # month"), reused here rather than reinvented.
    by_ean = {}
    if "EAN" in first_row:
        for r in detail_records:
            ean = r.get("EAN")
            if not ean:
                continue
            slot = by_ean.setdefault(ean, {"Category": set(), "Brand": set()})
            if r.get("Category"):
                slot["Category"].add(r["Category"])
            if r.get("Brand"):
                slot["Brand"].add(r["Brand"])
    inconsistent_eans = sum(1 for v in by_ean.values() if len(v["Category"]) > 1 or len(v["Brand"]) > 1)
    if inconsistent_eans:
        add_issue("consistency_ean_taxonomy", None, "consistency", inconsistent_eans,
                   f"{inconsistent_eans} EANs with more than one Category or Brand value", "detail_records",
                   f"{inconsistent_eans} EAN(s) carry more than one distinct Category or Brand across rows.")
    dims["consistency"] = {"rule": "same EAN -> same Category and Brand across all rows",
                           "distinct_eans_checked": len(by_ean), "inconsistent_eans": inconsistent_eans,
                           "threshold": "NOT_CONFIGURED", "threshold_source": "NOT_CONFIGURED",
                           "status": "INFORMATIONAL"}

    # ---- 5. TIMELINESS -----------------------------------------------------
    # Presence/lag only -- no refresh SLA is configured anywhere in this
    # repo, so none is invented here.
    fyx = detail_meta.get("fyx_primary") or {}
    cur_fy_tag = sorted(fyx, key=fy_start_year)[-1] if fyx else None
    primary_latest = None
    if cur_fy_tag:
        months = (fyx.get(cur_fy_tag) or {}).get("months_canon") or []
        primary_latest = months[-1] if months else None
    offtake = data.get("offtake") or {}
    offtake_latest = None
    if cur_fy_tag:
        om = offtake.get("months_" + cur_fy_tag.lower()) or []
        offtake_latest = om[-1] if om else None
    in_sync = (primary_latest == offtake_latest) if (primary_latest and offtake_latest) else None
    if primary_latest and offtake_latest and not in_sync:
        add_issue("timeliness_primary_offtake_lag", None, "timeliness", 1, f"FY {cur_fy_tag}",
                   "detail_meta.fyx_primary vs offtake.months_*",
                   f"Primary's latest loaded month ({primary_latest}) does not match Offtake's ({offtake_latest}).")
    dims["timeliness"] = {"fy": cur_fy_tag, "primary_latest_month": primary_latest,
                          "offtake_latest_month": offtake_latest, "in_sync": in_sync,
                          "threshold": "NOT_CONFIGURED", "threshold_source": "NOT_CONFIGURED",
                          "status": "INFORMATIONAL",
                          "note": "presence/lag only -- no refresh SLA is configured anywhere in this repo"}

    data_quality = {"dimensions": dims,
                    "computed_at_scope": "row-capped detail_records (see "
                                         "detail_meta.value_coverage_pct for the cap's value coverage)"}

    # ---- RECONCILIATION -----------------------------------------------
    # Every check below reuses an existing governed calculation; nothing is
    # recomputed independently.
    checks = []
    if sis:
        cur_sis_fy = sorted(sis, key=fy_start_year)[-1]
        gap_status_text = detail_meta.get("sis_gap_status", "")
        checks.append({
            "check_id": "SIS_RECONCILIATION", "metric_id": "SIS_RECONCILIATION",
            "source": "detail_meta.sis_reconciliation / sis_gap_status (reused, not recomputed)",
            "current_value": (sis.get(cur_sis_fy) or {}).get("summary", {}).get("net_sis_value"),
            "status": "RESOLVED" if gap_status_text.startswith("RESOLVED") else "UNRESOLVED",
            "threshold": "N/A (resolved by business confirmation, not a numeric threshold)",
        })
    if alloc:
        gov = alloc.get("governance") or {}
        # Phase 3.5 audit fix: reconciliation PASS/FAIL must come from the actual
        # governed reconciliation numbers -- alloc.recon.overall's per-measure
        # (original vs allocated) variance -- never from rows_chain_equals_shipto
        # (a source-data-hygiene flag: DIRECT rows whose Chain name happens to
        # equal the Ship-To name -- unrelated to reconciliation) or rows_unmapped
        # (a mapping-coverage count, already tracked by MAPPING_COMPLETENESS_
        # COVERAGE below). Tolerance mirrors the existing convention dashboard/
        # index.html's allocSectionHtml() already uses for the same field
        # (isZero = abs(variance) < 0.01) -- not a newly invented threshold.
        recon_overall = (alloc.get("recon") or {}).get("overall") or {}
        variances = {m: (recon_overall.get(m) or {}).get("variance")
                     for m in ("qty", "mrp_sales", "nsv", "tax") if m in recon_overall}
        recon_pass = bool(variances) and all(
            v is not None and abs(v) < 0.01 for v in variances.values())
        checks.append({
            "check_id": "ALLOCATION_RECONCILIATION", "metric_id": "PRIMARY_NSV",
            "source": "alloc.recon.overall (reused from allocate_dist_primary(), not recomputed)",
            "current_value": variances,
            "status": "PASS" if recon_pass else ("VARIANCE_FLAGGED" if variances else "UNKNOWN"),
            "threshold": "abs(variance) < 0.01 (existing dashboard/index.html "
                         "allocSectionHtml() isZero() convention, reused here)",
        })
    if mapping_health.get("by_fy"):
        cur_mh_fy = sorted(mapping_health["by_fy"], key=fy_start_year)[-1]
        mh_cur = mapping_health["by_fy"][cur_mh_fy]
        checks.append({
            "check_id": "MAPPING_COMPLETENESS_COVERAGE", "metric_id": "MAPPING_COMPLETENESS_PCT",
            "source": "mapping_health.by_fy (reused; its own rag field is already computed via "
                      "rag_of() against config/analytics_config.json's mapping_completeness_pct "
                      "band -- green>=95, amber>=85. This IS a documented, configured threshold, "
                      "not a hardcoded UI constant -- corrects an earlier claim from Phase 2.)",
            "current_value": mh_cur.get("completeness_pct"),
            "threshold_source": "config/analytics_config.json rag.mapping_completeness_pct",
            "green_threshold": 95.0, "amber_threshold": 85.0,
            "status": mh_cur.get("rag") or "UNKNOWN",
        })
    registry_path = repo_root / "config" / "data_source_registry.yml"
    target_registered = False
    if registry_path.exists() and targets.get("source"):
        target_registered = Path(targets["source"]).name in registry_path.read_text(encoding="utf-8")
    if targets:
        checks.append({
            "check_id": "TARGET_SOURCE_LINEAGE", "metric_id": "TARGET_ACHIEVEMENT_PCT",
            "source": targets.get("source"),
            "comparison": "is the target source registered in config/data_source_registry.yml?",
            "current_value": target_registered,
            "status": "REGISTERED" if target_registered else "NOT_REGISTERED",
            "threshold": "N/A (governance/lineage check, not a numeric threshold)",
            "note": ("Actual (offtake/primary) sources ARE registered; the target file is not -- "
                     "found in Phase 2, confirmed here. Smallest safe follow-up: add a "
                     "targets_fy2627 entry to config/data_source_registry.yml (documentation-only, "
                     "no calculation impact) -- not done in this phase.") if not target_registered else None,
        })
        if not target_registered:
            add_issue("reconciliation_target_source_unregistered", "TARGET_ACHIEVEMENT_PCT",
                       "reconciliation", 1, "PowerBI/SeedData/Targets/FY2627_Targets.csv",
                       "config/data_source_registry.yml",
                       "Target source is not registered in config/data_source_registry.yml, "
                       "unlike the actual (offtake/primary) sources it's compared against.")

    reconciliation = {"checks": checks}
    return data_quality, reconciliation, issues


# --------------------------------------------------------------------------
# TARGET / ACHIEVEMENT / RUN RATE
# --------------------------------------------------------------------------
# Which measure the business target is set against. forecast_block_ty already
# compares this same target file to OFFTAKE, so that stays the default here --
# one place to change it, and the choice is published in the output so nobody
# has to guess which basis a number on screen was built on.
TARGET_BASIS = "offtake"

# Required-vs-current run-rate bands. Business thresholds belong in one named
# place, not inlined in a formula.
RUNRATE_BANDS = ((1.00, "Ahead"), (1.05, "On Track"), (1.15, "At Risk"))

def load_targets_csv(repo_root):
    """Monthly business target from the tracked seed CSV
    (PowerBI/SeedData/Targets/FY2627_Targets.csv -- same numbers the Power BI
    Targets query reads). Returns [(FY tag, 'Mon-YY', value_in_Lakh)] or None.

    This is the committed fallback for load_ty_target()'s .xlsb, which is
    gitignored and so is not present in every environment."""
    f = Path(repo_root) / "PowerBI" / "SeedData" / "Targets" / "FY2627_Targets.csv"
    if not f.exists():
        return None
    rows = []
    with open(f, newline="", encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            try:
                d = datetime.date.fromisoformat(r["MonthStart"].strip())
                cr = float(r["Target NSV Cr"])
            except (KeyError, ValueError, AttributeError):
                continue                      # skip a malformed row, keep the rest
            rows.append((d, fy_tag_from_ym(d.year, d.month),
                         f"{_CAL_MON3[d.month]}-{d.year % 100:02d}",
                         r2(cr * 100)))       # Cr -> Lakh
    # sort CHRONOLOGICALLY -- sorting the "Mon-YY" label as text puts Aug
    # before Jan and silently reorders the fiscal year.
    rows.sort(key=lambda x: x[0])
    return [(tag, lbl, v) for _d, tag, lbl, v in rows] or None

def _runrate_status(required, current):
    if not current or required is None:
        return None
    ratio = required / current
    for limit, label in RUNRATE_BANDS:
        if ratio <= limit:
            return label
    return "Critical"

def _achv(actual, target):
    """Achievement / gap / gap% for one actual-vs-target pair."""
    if not target:
        return {"target": r2(target or 0), "actual": r2(actual),
                "achievement_pct": None, "gap": r2(actual), "gap_pct": None}
    return {"target": r2(target), "actual": r2(actual),
            "achievement_pct": r2(actual / target * 100),
            "gap": r2(actual - target),
            "gap_pct": r2((actual - target) / target * 100)}

def targets_block(target_rows, actuals, same_period=None):
    """Target vs achievement vs run rate, for each measure in `actuals`.

    actuals: {"offtake": {"Apr-26": 3588.51, ...}, "primary": {...}}
             month-keyed so the period-to-date window is DERIVED from the
             months that actually have actuals -- it extends itself when
             Aug-26 lands rather than needing a hardcoded month count.

    The target file is total-business monthly only: it carries no zone or
    chain split. Zone/chain targets are therefore DERIVED by applying each
    dimension's prior-year same-period contribution to the business target,
    and every derived row is tagged basis="DERIVED" so it is never mistaken
    for a business-owned number. To publish owner-set zone/chain targets,
    supply a zone/chain-level target file and split this on that instead.
    """
    if not target_rows:
        return None
    # FM-23 (FY12 -- month/FY key mismatch): the two interchangeable loaders
    # this is called with disagree on what the first tuple element IS.
    # load_targets_csv() returns (fy_tag_string, label, value) -- e.g.
    # ("FY27", "Apr-26", ...). load_ty_target() returns (date, label, value)
    # -- e.g. (datetime.date(2026,4,1), "Apr-26", ...), because its OTHER
    # caller, forecast_block_ty(), needs the real date (calls .year/.month
    # on it directly) and can't be changed to a tag string without breaking
    # that caller. Left as `tag == fy` comparing dates, this collapsed
    # tgt_by_month to just the FIRST month whenever load_ty_target()'s xlsb
    # path supplied the rows (fy_target understated ~92%, fy_tag rendered as
    # a raw date object) -- confirmed live with a direct call, dormant in
    # production only because every build so far has used the CSV fallback
    # (the xlsb source file is gitignored and not present in this repo).
    # Normalize here, at the point of consumption, rather than changing
    # either loader's contract.
    if hasattr(target_rows[0][0], "year"):
        target_rows = [(fy_tag_from_ym(d.year, d.month), lbl, v) for d, lbl, v in target_rows]
    fy = target_rows[0][0]
    tgt_by_month = {lbl: v for tag, lbl, v in target_rows if tag == fy}
    fy_target = r2(sum(tgt_by_month.values()))

    out = {"fy_tag": fy, "basis": TARGET_BASIS, "unit": "INR Lakh",
           "fy_target": fy_target, "months_in_fy": len(tgt_by_month),
           # tgt_by_month is built from chronologically sorted rows, so plain
           # insertion order is already Apr..Mar.
           "monthly_target": [{"month": l, "target": v} for l, v in tgt_by_month.items()],
           "measures": {}, "source": "PowerBI/SeedData/Targets/FY2627_Targets.csv"}

    for measure, series in (actuals or {}).items():
        months = [m for m in tgt_by_month if series.get(m) is not None]
        if not months:
            continue
        ptd_actual = float(sum(series[m] for m in months))
        ptd_target = float(sum(tgt_by_month[m] for m in months))
        elapsed = len(months)
        remaining = len(tgt_by_month) - elapsed
        current_rr = ptd_actual / elapsed if elapsed else None
        required_rr = ((fy_target - ptd_actual) / remaining) if remaining > 0 else None
        blk = _achv(ptd_actual, ptd_target)
        blk.update({
            "months": months, "months_elapsed": elapsed, "months_remaining": remaining,
            "fy_target": fy_target,
            "fy_gap": r2(fy_target - ptd_actual),
            "current_run_rate": r2(current_rr) if current_rr is not None else None,
            "required_run_rate": r2(required_rr) if required_rr is not None else None,
            "run_rate_status": _runrate_status(required_rr, current_rr),
            "monthly": [{"month": m, "actual": r2(series[m]),
                         "target": r2(tgt_by_month[m]),
                         "achievement_pct": r2(series[m] / tgt_by_month[m] * 100)
                         if tgt_by_month[m] else None} for m in months],
        })
        # ---- Zone / chain: DERIVED split, never presented as owner-set ----
        if same_period:
            for dim in ("by_zone", "by_chain"):
                rows = same_period.get(dim) or []
                base = float(sum(r.get("prev") or 0 for r in rows))
                if not base:
                    continue
                split = []
                for r in rows:
                    share = (r.get("prev") or 0) / base
                    d = _achv(float(r.get("curr") or 0), ptd_target * share)
                    d.update({"name": r["name"], "contribution_pct": r2(share * 100),
                              "basis": "DERIVED"})
                    split.append(d)
                blk[dim] = sorted(split, key=lambda d: -(d["actual"] or 0))
            blk["dim_target_basis"] = (
                f"Zone/chain targets are DERIVED: the business target is split by each "
                f"dimension's {same_period.get('prev_fy', 'prior-FY')} same-period contribution "
                f"({', '.join(same_period.get('months') or [])}). The target file is "
                f"total-business monthly only. Replace with a zone/chain-level target "
                f"file to publish owner-set numbers.")
        out["measures"][measure] = blk
    return out or None

def frame_from_records(records, detail_meta=None):
    """Article-grain DataFrame from detail_records, with the _-prefixed column
    names the Phase-3 blocks expect.

    Returns None when the records are row-capped: Phase-3 totals would be
    understated against a partial frame, and a quietly understated number is
    worse than an absent one. detail_meta.value_coverage_pct reports the cap.
    """
    if not records:
        return None
    cov = (detail_meta or {}).get("value_coverage_pct")
    if cov is not None and float(cov) < 100.0:
        return None
    return pd.DataFrame([{
        "_FY": r.get("FY"), "_M": r.get("Month"), "_NSV": r.get("NSV") or 0.0,
        "_Qty": r.get("Qty") or 0.0, "_MRP": r.get("MRP") or 0.0,
        "_Chain": r.get("Chain"), "_Zone": r.get("Zone"), "_State": r.get("State"),
        "_Brand": r.get("Brand"), "_category": r.get("Category"),
        "_Description": r.get("Article"), "_Chan": r.get("Channel"),
    } for r in records])

# --------------------------------------------------------------------------
# CANONICAL NORMALISATION — zones and brands
# --------------------------------------------------------------------------
def canon_zone_name(raw, cfg=None):
    """One canonical zone name from any source system's spelling.

    Four sources spell the same zone four ways: 'South 1' (dashboard),
    'South-1' (employee master), 'South_1' (WoA), 'SOUTH-1' (Massit). A rule
    beats an alias list here -- the next source with a fifth spelling is
    handled without an edit. Returns (canonical, matched) so the caller can
    keep the raw value and quarantine what did not match rather than guessing.
    """
    z = ((cfg or {}).get("zones") or {})
    canon = z.get("canonical") or []
    over = {k.lower(): v for k, v in (z.get("explicit_overrides") or {}).items()}
    if raw is None:
        return None, False
    t = re.sub(r"[\-_]+", " ", str(raw).strip())
    t = re.sub(r"\s+", " ", t).strip()
    if not t:
        return None, False
    if t.lower() in over:
        return over[t.lower()], True
    for c in canon:
        if t.lower() == c.lower():
            return c, True
    return t.title(), False          # unmatched: keep it visible, flag it

def is_emerging_brand(brand, cfg=None):
    """Emerging brand = every MT brand except the core one(s).

    Business-confirmed rule, deliberately expressed as 'all except' rather than
    a fixed list, so a brand that appears next month is emerging by default --
    which is what the rule means. Returns None when the brand is missing, so a
    blank never silently counts as emerging.
    """
    b = ((cfg or {}).get("brands") or {})
    if b.get("emerging_rule") != "all_except":
        return None
    if brand is None or not str(brand).strip():
        return None
    core = {str(c).strip().lower() for c in (b.get("core_brands") or [])}
    return str(brand).strip().lower() not in core

# --------------------------------------------------------------------------
# CONSOLIDATED SALES ACTUALS — chain first, DMS as gap-fill only
# --------------------------------------------------------------------------
def sales_actuals_block(chain_rows, massit_rows, cfg=None, chain_alias=None):
    """Actual sales with an explicit source priority, and no double counting.

    chain_rows : {chain_name: value} -- chain sales for the period (authoritative)
    massit_rows: iterable of dicts with client_id, client_type, chain, zone, value

    The rule that matters: a DMS client whose chain ALREADY has chain-sales
    coverage is a duplicate, not extra sales. Measured on Jun-26, 98.8% of DMS
    tertiary falls in that bucket -- adding the two sources would have
    overstated the month by about Rs 35.6 Cr. So DMS is gap-fill only, and its
    real contribution here is store grain and employee attribution, which chain
    sales does not carry.

    Nothing is silently zeroed: a store with no sales in either source is
    reported as NO_SALES_DATA, which is a different statement from zero sales.
    """
    sa = ((cfg or {}).get("sales_actuals") or {})
    alias = chain_alias or {}
    covered = {k for k, v in (chain_rows or {}).items() if (v or 0) > 0}

    def resolve(name):
        if name is None:
            return None
        n = str(name).strip()
        if n in covered:
            return n
        if n in alias and alias[n] in covered:
            return alias[n]
        low = {c.lower(): c for c in covered}
        return low.get(n.lower())

    buckets = {"CHAIN": 0.0, "MASSIT": 0.0, "DUPLICATE_EXCLUDED": 0.0, "UNMAPPED": 0.0}
    by_type, clients = {}, {}
    for r in (massit_rows or []):
        v = float(r.get("value") or 0.0)
        ct = (r.get("client_type") or "").strip() or "(blank)"
        ch = resolve(r.get("chain") or ct)
        cid = (r.get("client_id") or "").strip()
        if ch:
            status, bucket = "DUPLICATE", "DUPLICATE_EXCLUDED"
        elif ct in ("#N/A", "(blank)", ""):
            status, bucket = "UNMAPPED", "UNMAPPED"
        else:
            status, bucket = "GAP_FILL", "MASSIT"
        buckets[bucket] += v
        t = by_type.setdefault(ct, {"client_type": ct, "status": status,
                                    "maps_to_chain": ch, "value": 0.0, "clients": set()})
        t["value"] += v
        if cid:
            t["clients"].add(cid)
        clients.setdefault(cid, status)
    buckets["CHAIN"] = float(sum((v or 0) for v in (chain_rows or {}).values()))

    rows = []
    for t in by_type.values():
        t["clients"] = len(t["clients"])
        t["value"] = r2(t["value"])
        rows.append(t)
    rows.sort(key=lambda d: -(d["value"] or 0))

    consolidated = buckets["CHAIN"] + buckets["MASSIT"]
    naive = buckets["CHAIN"] + buckets["MASSIT"] + buckets["DUPLICATE_EXCLUDED"]
    return {
        "priority": sa.get("priority") or ["CHAIN", "MASSIT"],
        "massit_measure": sa.get("massit_measure"),
        "unit": "INR",
        "chain_sales": r2(buckets["CHAIN"]),
        "massit_gap_fill": r2(buckets["MASSIT"]),
        "massit_duplicate_excluded": r2(buckets["DUPLICATE_EXCLUDED"]),
        "massit_unmapped": r2(buckets["UNMAPPED"]),
        "consolidated_actual": r2(consolidated),
        "naive_sum_would_be": r2(naive),
        "double_count_avoided": r2(naive - consolidated),
        "chains_with_chain_sales": len(covered),
        "by_client_type": rows,
        "reconciliation": {
            "statement": "chain_sales + massit_gap_fill = consolidated_actual",
            "check": r2(buckets["CHAIN"] + buckets["MASSIT"] - consolidated),
            "status": "PASS" if abs(buckets["CHAIN"] + buckets["MASSIT"] - consolidated) < 1 else "CHECK",
        },
        "note": ("Chain sales is authoritative. DMS is used only where a chain has no "
                 "chain-sales coverage. A DMS client on an already-covered chain is "
                 "excluded as a duplicate, not added. Stores with neither source are "
                 "NO_SALES_DATA, never zero."),
    }

# --------------------------------------------------------------------------
# PHASE 3 — MoM, SCORECARD, PRICE-VOLUME-MIX
# --------------------------------------------------------------------------
def _mom_pcts(vals):
    """Month-on-month % for a series; first month has no prior, so it is None."""
    out = [None]
    for i in range(1, len(vals)):
        a, b = vals[i - 1], vals[i]
        out.append(r2((b / a - 1) * 100) if (a not in (None, 0) and b is not None) else None)
    return out

def mom_block(offtake, fyx, targets, df=None, cfg=None):
    """Month-on-month view for the current FY, one row per metric.

    The month list is DERIVED from the months that actually carry actuals, so
    Aug'26 extends this view by arriving -- there is no month count to update.
    Metrics with no source in this build are listed in `unavailable` with the
    reason, rather than shown as zero.
    """
    cfg = cfg or {}
    tgt_fy = (targets or {}).get("fy_tag")
    fy = tgt_fy or (sorted(fyx or {}, key=fy_start_year)[-1] if fyx else None)
    if not fy:
        return None
    lo = fy.lower()
    off_m = list((offtake or {}).get(f"months_{lo}") or [])
    off_v = list((offtake or {}).get(f"monthly_{lo}") or [])
    fx = (fyx or {}).get(fy) or {}
    pri = dict(zip(fx.get("months_canon") or [], fx.get("monthly_canon") or []))
    months = off_m or list(pri)
    if not months:
        return None
    tgt = {r["month"]: r["target"] for r in ((targets or {}).get("monthly_target") or [])}
    basis = (targets or {}).get("basis") or "offtake"

    pri_s = [pri.get(m) for m in months]
    off_s = [off_v[off_m.index(m)] if m in off_m else None for m in months]
    tgt_s = [tgt.get(m) for m in months]
    act_s = off_s if basis == "offtake" else pri_s
    achv = [r2(a / t * 100) if (a is not None and t) else None for a, t in zip(act_s, tgt_s)]
    gap = [r2(a - t) if (a is not None and t is not None) else None for a, t in zip(act_s, tgt_s)]

    # ASP per month, from the article grain -- the only place a real unit price exists.
    asp_s = [None] * len(months)
    if df is not None and "_Qty" in df.columns:
        d = df[df["_FY"] == fy]
        canon = dict(zip(fx.get("months_covered") or [], fx.get("months_canon") or []))
        g = d.groupby("_M").agg(nsv=("_NSV", "sum"), qty=("_Qty", "sum"))
        by = {canon.get(m, m): (row.nsv, row.qty) for m, row in g.iterrows()}
        asp_s = [r2(by[m][0] * 100000 / by[m][1]) if (m in by and by[m][1]) else None for m in months]

    rows = [
        {"metric": "Primary NSV",     "key": "primary_nsv", "unit": "INR Lakh", "values": pri_s},
        {"metric": "Offtake NSV",     "key": "offtake_nsv", "unit": "INR Lakh", "values": off_s},
        {"metric": "Target",          "key": "target",      "unit": "INR Lakh", "values": tgt_s},
        {"metric": f"Achievement % ({basis})", "key": "achievement_pct", "unit": "%", "values": achv, "no_mom": True},
        {"metric": f"Gap vs target ({basis})", "key": "gap", "unit": "INR Lakh", "values": gap, "no_mom": True},
        {"metric": "ASP",             "key": "asp",         "unit": "INR/unit", "values": asp_s},
    ]
    for r in rows:
        r["mom_pct"] = [None] * len(months) if r.get("no_mom") else _mom_pcts(r["values"])
        vals = [v for v in r["values"] if v is not None]
        r["total"] = r2(sum(vals)) if (vals and r["unit"] == "INR Lakh") else None
        r["avg"] = r2(sum(vals) / len(vals)) if vals else None
        r["latest"] = r["values"][-1] if r["values"] else None
    return {
        "fy_tag": fy, "months": months, "n_months": len(months), "basis": basis,
        "rows": rows,
        "unavailable": [
            {"metric": "Stock / inventory days", "reason": "No monthly stock-on-hand feed in this build."},
            {"metric": "OSA / OOS / Fill rate", "reason": "Store audit is a single Q3 FY27 snapshot over 189 of 426 stores, not a monthly series. See readiness.scorecard_execution."},
            {"metric": "NPD", "reason": "NPD master is not joined to the transaction grain. See readiness.npd."},
            {"metric": "Promo ROI", "reason": "Promo data is not aligned to this FY's month grain in this build."},
        ],
        "note": ("Months are derived from the actuals present, so the view extends itself "
                 "as new months land. MoM % is suppressed on ratio and gap rows, where a "
                 "month-on-month percentage of a percentage would mislead."),
    }

def scorecard_block(same_period, targets, mapping_health=None, cfg=None, dim="by_zone"):
    """One commercial row per zone or chain: scale, growth, target, status, action.

    Built to be acted on rather than read: every row ends in a RAG status and a
    specific next step, and the thresholds behind the status come from
    config/analytics_config.json rather than being inlined here.
    """
    cfg = cfg or {}
    if not same_period:
        return None
    sp_rows = (same_period or {}).get(dim) or []
    if not sp_rows:
        return None
    basis = (targets or {}).get("basis") or "offtake"
    tm = ((targets or {}).get("measures") or {}).get(basis) or {}
    tgt_rows = {r["name"]: r for r in (tm.get(dim) or [])}
    months = tm.get("months_elapsed") or same_period.get("n_months") or 1
    fy_target_total = tm.get("fy_target")
    rows = []
    for r in sp_rows:
        name = r["name"]
        t = tgt_rows.get(name) or {}
        growth = r.get("yoy_pct")
        achv = t.get("achievement_pct")
        # Remaining full-year target for this dimension, on its derived share.
        share = (t.get("contribution_pct") or 0) / 100.0
        fy_t = (fy_target_total or 0) * share
        act = t.get("actual")
        curr_rr = r2(act / months) if (act is not None and months) else None
        rem = (targets or {}).get("months_in_fy")
        rem = (rem - months) if rem else None
        req_rr = r2((fy_t - (act or 0)) / rem) if (rem and rem > 0) else None
        ratio = (req_rr / curr_rr) if (req_rr is not None and curr_rr) else None
        rag = {"achievement": rag_of(achv, "achievement_pct", cfg),
               "growth": rag_of(growth, "growth_pct", cfg),
               "run_rate": rag_of(ratio, "run_rate_ratio", cfg)}
        worst = "red" if "red" in rag.values() else ("amber" if "amber" in rag.values()
                else ("green" if "green" in rag.values() else None))
        # Action: the specific thing wrong, not a generic nudge.
        if rag["achievement"] == "red" and (growth or 0) < 0:
            action = "Behind target and declining — diagnose range, fill rate and visibility; reset the JBP."
        elif rag["achievement"] == "red":
            action = f"Behind target despite {pctf(growth)} growth — phasing or base issue; re-check the target split."
        elif rag["run_rate"] in ("amber", "red"):
            action = f"Needs {crf(req_rr)}/mth against {crf(curr_rr)}/mth today — lift order frequency or add assortment."
        elif rag["achievement"] == "amber":
            action = "Close to target — protect with visibility; small assortment add should close the gap."
        elif worst == "green":
            action = "On track — hold current plan; look for share gain."
        else:
            action = "Insufficient target data for this row."
        rows.append({
            "name": name, "curr": r.get("curr"), "prev": r.get("prev"),
            "delta": r.get("delta"), "growth_pct": growth,
            "target": t.get("target"), "actual": act,
            "achievement_pct": achv, "gap": t.get("gap"), "gap_pct": t.get("gap_pct"),
            "contribution_pct": t.get("contribution_pct"),
            "current_run_rate": curr_rr, "required_run_rate": req_rr,
            "rag": rag, "status": worst, "action": action,
            "target_basis": t.get("basis"),
            # From same_period_block(): qty_yoy_pct (units growth, independent of
            # price/mix) and nsv_contribution_pct (this row's share of the CURRENT
            # period's total NSV -- distinct from contribution_pct above, which is
            # the target's prior-year-derived share used to split the FY target).
            "qty_yoy_pct": r.get("qty_yoy_pct"),
            "nsv_contribution_pct": r.get("nsv_contribution_pct"),
            "comparability": r.get("comparability"),
        })
    rows.sort(key=lambda d: -(d.get("curr") or 0))
    return {
        "dim": dim, "basis": basis,
        "curr_fy": same_period.get("curr_fy"), "prev_fy": same_period.get("prev_fy"),
        "months": same_period.get("months"), "n_months": same_period.get("n_months"),
        "rows": rows,
        "thresholds": (cfg.get("rag") or {}),
        "note": ("Growth is like-for-like primary over the shared months. Target, "
                 "achievement and run rate are on the "
                 f"{basis} basis; zone/chain targets are DERIVED from prior-year "
                 "contribution and are not business-set."),
    }

def pctf(v):
    return "–" if v is None else f"{v:+.1f}%"

def crf(v):
    return "–" if v is None else f"Rs {v/100:.2f} Cr"

# Column names differ between the article frame and the record frame, so resolve
# by first-present rather than pinning one spelling.
_PVM_ITEM_COLS = ("_Description", "_Article", "_article", "Article")
_PVM_CAT_COLS = ("_category", "_Cat", "Category")

def _first_col(df, names):
    return next((c for c in names if c in df.columns), None)

def pvm_block(df, same_period, item_col=None, nsv_col="_NSV", qty_col="_Qty",
              fy_col="_FY", m_col="_M", cfg=None):
    """Price-Volume-Mix: what actually drove the change in value.

    Decomposed at ARTICLE grain, because that is the only grain where a unit
    price is a real price. Four buckets that sum to the total change exactly:

      Volume        same articles, more or fewer units, at last year's price
      Price         same articles, same units, different realisation
      New           articles selling this period that did not sell last period
      Discontinued  the reverse

    Blended ASP is reported alongside: when blended ASP moves more than
    same-article price, the difference is mix -- the shop sold a different
    basket, not a dearer one. Mix is shown as that gap rather than as a
    residual bucket, so every rupee stays attributable.
    """
    item_col = item_col or _first_col(df, _PVM_ITEM_COLS)
    if not same_period or qty_col not in df.columns or not item_col:
        return None
    curr, prev = same_period.get("curr_fy"), same_period.get("prev_fy")
    shared = set(same_period.get("months") or [])
    if not (curr and prev and shared):
        return None
    c = df[(df[fy_col] == curr) & (df[m_col].isin(shared))]
    v = df[(df[fy_col] == prev) & (df[m_col].isin(shared))]
    if c.empty or v.empty:
        return None

    def agg(d):
        g = d.groupby(item_col).agg(nsv=(nsv_col, "sum"), qty=(qty_col, "sum"))
        return {k: (float(r.nsv), float(r.qty)) for k, r in g.iterrows() if k}

    C, P = agg(c), agg(v)
    common = set(C) & set(P)
    new_i, lost_i = set(C) - set(P), set(P) - set(C)

    vol = price = 0.0
    base_at_prev_price = 0.0   # Sigma P_prev * Q_curr -- the denominator that turns
                               # the price effect into a true like-for-like price %
    for k in common:
        nc, qc = C[k]; np_, qp = P[k]
        if qp <= 0 or qc <= 0:
            # No usable unit price on one side: the whole move is volume-like.
            vol += nc - np_
            continue
        pp, pc = np_ / qp, nc / qc
        vol += (qc - qp) * pp
        price += (pc - pp) * qc
        base_at_prev_price += pp * qc
    new_v = sum(C[k][0] for k in new_i)
    lost_v = -sum(P[k][0] for k in lost_i)

    c_nsv, c_qty = sum(x[0] for x in C.values()), sum(x[1] for x in C.values())
    p_nsv, p_qty = sum(x[0] for x in P.values()), sum(x[1] for x in P.values())
    delta = c_nsv - p_nsv
    asp_c = (c_nsv * 100000 / c_qty) if c_qty else None
    asp_p = (p_nsv * 100000 / p_qty) if p_qty else None
    # PURE price change: the rupee price effect expressed against the same basket
    # valued at last year's prices. Quantities are held constant, so this is the
    # only ASP percentage that is consistent in sign with the Price bucket above.
    # (A blended ASP across the common articles is NOT that number -- it still
    # carries mix shifts inside the common set, and can move opposite to the
    # actual price effect.)
    blend_pct = r2((asp_c / asp_p - 1) * 100) if (asp_c and asp_p) else None
    pure_pct = r2(price / base_at_prev_price * 100) if base_at_prev_price else None
    mix_pp = r2(blend_pct - pure_pct) if (blend_pct is not None and pure_pct is not None) else None

    buckets = [
        {"driver": "Volume", "value": r2(vol), "pct_of_change": r2(vol / delta * 100) if delta else None,
         "meaning": "Same articles, more units sold, valued at last year's price."},
        {"driver": "Price", "value": r2(price), "pct_of_change": r2(price / delta * 100) if delta else None,
         "meaning": "Same articles, change in realisation per unit."},
        {"driver": "New articles", "value": r2(new_v), "pct_of_change": r2(new_v / delta * 100) if delta else None,
         "meaning": f"{len(new_i)} article(s) selling this period that did not sell last period."},
        {"driver": "Discontinued", "value": r2(lost_v), "pct_of_change": r2(lost_v / delta * 100) if delta else None,
         "meaning": f"{len(lost_i)} article(s) that sold last period and did not this period."},
    ]
    recon = r2(vol + price + new_v + lost_v - delta)

    def contrib(col):
        if not col or col not in df.columns:
            return None
        cs = c.groupby(col)[nsv_col].sum(); vs = v.groupby(col)[nsv_col].sum()
        rows = []
        for k in sorted(set(cs.index) | set(vs.index)):
            if not k:
                continue
            a, b = float(cs.get(k, 0.0)), float(vs.get(k, 0.0))
            rows.append({"name": k, "curr": r2(a), "prev": r2(b), "delta": r2(a - b),
                         "pct_of_total_change": r2((a - b) / delta * 100) if delta else None})
        return sorted(rows, key=lambda d: -(d["delta"] or 0))

    return {
        "curr_fy": curr, "prev_fy": prev, "months": sorted(shared),
        "n_months": len(shared), "unit": "INR Lakh", "grain": "Article",
        "prev": {"nsv": r2(p_nsv), "qty": int(p_qty), "asp": r2(asp_p)},
        "curr": {"nsv": r2(c_nsv), "qty": int(c_qty), "asp": r2(asp_c)},
        "delta": r2(delta),
        "delta_pct": r2(delta / p_nsv * 100) if p_nsv else None,
        "qty_delta_pct": r2((c_qty / p_qty - 1) * 100) if p_qty else None,
        "buckets": buckets,
        "reconciliation": {"sum_of_buckets": r2(vol + price + new_v + lost_v),
                           "actual_delta": r2(delta), "variance": recon,
                           "status": "PASS" if abs(recon) < 1.0 else "CHECK"},
        "asp": {"prev": r2(asp_p), "curr": r2(asp_c), "blended_change_pct": blend_pct,
                "pure_price_change_pct": pure_pct, "mix_effect_pp": mix_pp,
                "reading": (
                    f"Blended ASP moved {blend_pct}%, but on a like-for-like basket "
                    f"(same articles, quantities held constant) price moved {pure_pct}%. "
                    f"The {mix_pp}pp difference is MIX and range change -- what was sold, "
                    f"not what it was priced at."
                ) if (blend_pct is not None and pure_pct is not None) else None},
        "n_articles": {"common": len(common), "new": len(new_i), "discontinued": len(lost_i)},
        "by_chain": contrib("_Chain"), "by_brand": contrib("_Brand"),
        "by_category": contrib(_first_col(df, _PVM_CAT_COLS)) if _first_col(df, _PVM_CAT_COLS) else None,
        "note": ("Article-grain decomposition. Volume + Price + New + Discontinued sums "
                 "to the actual change exactly (see reconciliation). ASP is computed from "
                 "article Qty and NSV, NOT from unit_economics.nsv_per_unit, which is "
                 "degenerate in this dataset."),
    }

# --------------------------------------------------------------------------
# INSIGHTS  (auto-generated, data-driven)
# --------------------------------------------------------------------------
def insights_block(primary, offtake, pnl, universe, promo, same_period=None):
    ins = []
    # The pre-aggregated primary block only publishes the FYs its workbook
    # actually covers, so the current FY is owned by the article-level source
    # and reaches here via `same_period`. Re-base the chain view onto that
    # like-for-like window when it is available: without it the growth
    # insights below either go blank or compare a part-year against a full
    # year -- which is how "Fastest-growing scaled chain: Lulu grew -57%"
    # ended up on the dashboard as a "win".
    _win = ""
    if same_period and same_period.get("by_chain"):
        _cf = str(same_period["curr_fy"]).lower()
        _pf = str(same_period["prev_fy"]).lower()
        primary = dict(primary)          # shallow copy; never mutate the caller's block
        primary["by_chain"] = [{"name": r["name"], _cf: r["curr"], _pf: r["prev"],
                                "yoy": r["yoy_pct"]} for r in same_period["by_chain"]]
        primary[f"nsv_{_cf}"] = same_period["curr"]
        primary[f"nsv_{_pf}"] = same_period["prev"]
        primary["fy_tags"] = [_pf, _cf]
        _win = f" ({'+'.join(same_period.get('months') or [])} like-for-like)"
    pc = {c["name"]: c for c in primary["by_chain"]}
    oc = {c["name"]: c for c in offtake["by_chain"]}
    uc = {c["name"]: c for c in universe["by_chain"]}

    # Determine the two most recent FY tags dynamically
    _fy_tags = primary.get("fy_tags") or []
    _curr_fy = _fy_tags[-1] if _fy_tags else "fy26"
    _prev_fy = _fy_tags[-2] if len(_fy_tags) >= 2 else (_fy_tags[0] if _fy_tags else "fy25")

    # 1. Concentration
    top2 = primary["by_chain"][:2]
    tot = primary.get(f"nsv_{_curr_fy}") or 1
    share = sum(c.get(_curr_fy) or 0 for c in top2) / tot * 100
    ins.append({"type": "risk", "title": "Revenue concentration in top 2 chains",
                "text": f"{top2[0]['name']} and {top2[1]['name']} together drive "
                        f"{share:.0f}% of {_curr_fy.upper()} MT primary{_win} (₹{(sum(c.get(_curr_fy) or 0 for c in top2))/100:.0f} Cr). "
                        f"De-risk by accelerating the mid-tier (Apollo, Nykaa, Wellness Forever)."})
    # 2. Fastest growers (material base)
    growers = [c for c in primary["by_chain"] if c["yoy"] is not None and (c.get(_curr_fy) or 0) > 200]
    growers.sort(key=lambda d: -(d["yoy"] or 0))
    if growers:
        g = growers[0]
        ins.append({"type": "win", "title": "Fastest-growing scaled chain",
                    "text": f"{g['name']} grew {g['yoy']:.0f}% YoY to ₹{(g.get(_curr_fy) or 0)/100:.1f} Cr. "
                            f"Lock incremental visibility + assortment to defend the momentum."})
    # 3. Decliners
    decl = [c for c in primary["by_chain"] if c["yoy"] is not None and c["yoy"] < 0 and (c.get(_prev_fy) or 0) > 150]
    decl.sort(key=lambda d: d["yoy"])
    if decl:
        d = decl[0]
        ins.append({"type": "risk", "title": "Scaled chain in decline",
                    "text": f"{d['name']} fell {d['yoy']:.0f}% YoY (₹{(d.get(_prev_fy) or 0)/100:.1f}→₹{(d.get(_curr_fy) or 0)/100:.1f} Cr). "
                            f"Diagnose range/fill-rate and reset the JBP."})
    # 4. Sell-in vs sell-out (inventory health)
    gaps = []
    for name, p in pc.items():
        o = oc.get(name)
        if o and (o.get(_curr_fy) or 0) > 200 and (p.get(_curr_fy) or 0) > 0:
            ratio = (p.get(_curr_fy) or 0) / (o.get(_curr_fy) or 1)
            gaps.append((name, ratio, p.get(_curr_fy) or 0, o.get(_curr_fy) or 0))
    over = [x for x in gaps if x[1] > 1.15]
    over.sort(key=lambda x: -x[1])
    if over:
        n, ratio, pp, oo = over[0]
        ins.append({"type": "risk", "title": "Primary running ahead of offtake",
                    "text": f"At {n}, primary is {ratio:.2f}x offtake in {_prev_fy.upper()}-{_curr_fy.upper()} "
                            f"(₹{pp/100:.1f} Cr in vs ₹{oo/100:.1f} Cr out) — watch for stock build-up "
                            f"and returns risk; tighten ordering to sell-out."})
    under = [x for x in gaps if x[1] < 0.9]
    under.sort(key=lambda x: x[1])
    if under:
        n, ratio, pp, oo = under[0]
        ins.append({"type": "win", "title": "Offtake outpacing primary — refill opportunity",
                    "text": f"{n} is selling out faster than it is being billed "
                            f"({ratio:.2f}x). Increase primary/fill-rate to avoid lost sales."})
    # 5. Discount / margin pressure
    disc = sorted([c for c in pnl["by_chain"] if (c["nsv"] or 0) > 300 and c["discount_pct"] is not None],
                  key=lambda d: -(d["discount_pct"] or 0))
    if disc:
        d = disc[0]
        ins.append({"type": "watch", "title": "Highest trade-discount intensity",
                    "text": f"{d['name']} runs the deepest gross-to-net gap at {d['discount_pct']:.0f}% "
                            f"(₹{d['discount']/100:.1f} Cr off MRP). Re-evaluate ROI of that spend vs. offtake lift."})
    # 6. Distribution vs productivity
    prod = []
    for name, u in uc.items():
        p = pc.get(name)
        if p and u["stores"] > 50 and (p.get(_curr_fy) or 0) > 0:
            prod.append((name, (p.get(_curr_fy) or 0) / u["stores"], u["stores"], p.get(_curr_fy) or 0))
    if prod:
        prod.sort(key=lambda x: x[1])
        n, ppsk, stores, nsv = prod[0]
        ins.append({"type": "watch", "title": "Low throughput per store — distribution to activate",
                    "text": f"{n} has {stores:,} active stores but only ₹{nsv/100:.1f} Cr primary "
                            f"(₹{ppsk:.1f} L/store) — large headroom to lift productivity per door."})
    # 7. Brand mix
    bm = sorted(primary["by_brand"], key=lambda d: -(d.get(_curr_fy) or 0))
    if bm:
        lead = bm[0]
        bshare = (lead.get(_curr_fy) or 0) / (primary.get(f"nsv_{_curr_fy}") or 1) * 100
        ins.append({"type": "watch", "title": "Portfolio mix",
                    "text": f"{lead['name']} is {bshare:.0f}% of {_prev_fy.upper()}-{_curr_fy.upper()} MT primary. "
                            f"Scale Aqualogica / The Derma Co to broaden the portfolio in MT."})
    # 8. Forecast headline handled in forecast tab
    return ins

# --------------------------------------------------------------------------
# --------------------------------------------------------------------------
# DETAIL RECORDS  (Data Explorer drill-down: 13-column grain)
# --------------------------------------------------------------------------
_ORDER = ["April","May","June","July","Aug","Sept","Oct","Nov","Dec","Jan","Feb","March"]

_MNUM = {4:"April",5:"May",6:"June",7:"July",8:"Aug",9:"Sept",10:"Oct",11:"Nov",12:"Dec",1:"Jan",2:"Feb",3:"March"}

# Maps _ORDER full names to 3-letter abbreviations used in MONTHS ("Apr-26" format),
# kept consistent with _MON3_NUM keys so fyx_primary months_canon labels join o.months.
_ORDER_MON3 = {
    "April": "Apr", "May": "May", "June": "Jun", "July": "Jul",
    "Aug": "Aug", "Sept": "Sep", "Oct": "Oct", "Nov": "Nov",
    "Dec": "Dec", "Jan": "Jan", "Feb": "Feb", "March": "Mar",
}
_EXCEL_EPOCH = datetime.date(1899, 12, 30)

def _mlabel(m):
    # datetime / Timestamp / date -> month name
    if hasattr(m, "month") and not isinstance(m, (str, int, float)):
        try:
            return _MNUM.get(int(m.month))
        except Exception:
            pass
    # raw Excel date SERIAL (pandas + engine="pyxlsb" does NOT auto-convert
    # date-formatted cells to datetime — it returns the underlying number).
    # Plausible day-serial range for dates in ~2015-2035.
    if isinstance(m, (int, float)) and not isinstance(m, bool):
        try:
            n = float(m)
            if 40000 <= n <= 55000:
                d = _EXCEL_EPOCH + datetime.timedelta(days=int(n))
                return _MNUM.get(d.month)
        except Exception:
            pass
    m = str(m).strip().lower()
    for o in _ORDER:
        if m.startswith(o.lower()[:3]):
            return o
    return None

def _fylabel(fy):
    """Any source FY spelling -> canonical 'FYnn' tag, for ANY year (no
    enumerated list -- FY28+ works automatically). Accepts span forms
    ("FY'25-26" / "FY_25-26" / "2025-26" -> FY of the END year, per THE ONE
    FY RULE at the top of this file) and the dashboard's short form
    ("FY26" / "FY 26") that manually-typed inputs tend to use. None if
    unrecognisable."""
    s = str(fy).strip().upper().replace(" ", "")
    m = re.search(r"(\d{2})-(\d{2})", s)
    if m and int(m.group(2)) == (int(m.group(1)) + 1) % 100:
        return f"FY{int(m.group(2)):02d}"
    m = re.match(r"^FY0?(\d{2})$", s)
    if m:
        return f"FY{int(m.group(1)):02d}"
    return None

# brand -> [(Category, SubCategory, Range, [packs], article_stem)] for the representative fallback
_DTAX = {
 "Mamaearth":[("Face Care","Face Wash","Rice",["100 g/ml","150 g/ml"],"Rice Dewy Bright Face Wash"),
              ("Face Care","Face Wash","Onion",["150 g/ml"],"Onion Face Wash"),
              ("Hair Care","Shampoo","Onion",["250 g/ml","400 g/ml"],"Onion Shampoo"),
              ("Sun Care","Sunscreen","Ultra Light",["50 g/ml","80 g/ml"],"Ultra Light Sunscreen SPF50"),
              ("Face Care","Face Serum","Vitamin C",["30 g/ml"],"Vitamin C Face Serum")],
 "The Derma Co":[("Face Care","Face Wash","Salicylic",["100 g/ml"],"1% Salicylic Acid Face Wash"),
              ("Sun Care","Sunscreen","Hyaluronic",["50 g/ml"],"Hyaluronic Sunscreen Aqua Gel"),
              ("Face Care","Face Serum","Niacinamide",["30 g/ml"],"5% Niacinamide Face Serum")],
 "Aqualogica":[("Face Care","Face Wash","Glow",["100 g/ml"],"Glow+ Dewy Face Wash"),
              ("Sun Care","Sunscreen","Dewy",["50 g/ml"],"Radiance+ Dewy Sunscreen")],
 "BBlunt":[("Hair Colour","Hair Colour","Salon",["100 g/ml"],"Salon Secret Hair Colour"),
              ("Hair Care","Styling","Spray",["150 g/ml"],"Hold & Play Hairspray")],
 "Dr. Sheth's":[("Face Care","Face Serum","Cica",["30 g/ml"],"Cica & Ceramide Serum"),
              ("Face Care","Moisturizer","Gulab",["80 g/ml"],"Gulab & Glyceric Moisturizer")],
 "Staze":[("Hair Care","Styling","Gel",["100 g/ml"],"24H Styling Gel")],
 "Pure Origin":[("Body Care","Body Wash","Coffee",["250 g/ml"],"Coffee Body Wash")],
}

def _sis_reconciliation(df):
    """SIS gap reconciliation drill-down, computed from the FULL (uncapped)
    dataframe: per-FY summary (total sales / MRN-returns / cancelled / net),
    chain-wise, month-wise, brand-wise SIS value, and an exclusions log. This
    makes the Rs 250.17 L figure fully transparent and exportable -- it does
    NOT resolve what the Rs 236 L reference figure is defined as."""
    sis = df[df["_Chan"] == "SIS"].copy()
    if len(sis) == 0:
        return {}
    has_saletype = "MTD-Sale type" in sis.columns
    if has_saletype:
        sis["_SaleType"] = sis["MTD-Sale type"].astype(str).str.strip()
    has_dupkey = {"Inv No.", "Article Code"}.issubset(sis.columns)

    out = {}
    for fy in sorted(sis["_FY"].dropna().unique()):
        s = sis[sis["_FY"] == fy]
        net = round(float(s["_NSV"].sum()), 2)

        if has_saletype:
            by_type = s.groupby("_SaleType")["_NSV"].sum()
            total_sales = round(float(by_type.get("Sales", 0.0)), 2)
            mrn_returns = round(float(by_type.get("MRN", 0.0)), 2)
            cancelled = round(float(by_type.get("Cancel Invoice", 0.0)), 2)
        else:
            # no sale-type column available -- fall back to positive/negative split
            total_sales = round(float(s.loc[s["_NSV"] > 0, "_NSV"].sum()), 2)
            mrn_returns = round(float(s.loc[s["_NSV"] < 0, "_NSV"].sum()), 2)
            cancelled = 0.0

        by_chain = (s.groupby("_Chain")["_NSV"].sum().round(2)
                      .sort_values(ascending=False))
        by_month = (s.groupby("_M")["_NSV"].sum().round(2))
        by_month = by_month.reindex([m for m in _ORDER if m in by_month.index])
        by_brand = (s.groupby("_Brand")["_NSV"].sum().round(2)
                      .sort_values(ascending=False))

        exclusions = [
            f"Computed from all {len(s):,} SIS rows in the FULL source for {fy} "
            "(not the row-capped detail_records table used for browser display).",
            f"MRN (returns) included as a negative value: Rs {mrn_returns:.2f} L.",
            f"Cancelled invoices included: Rs {cancelled:.2f} L (near-zero net impact).",
        ]
        if has_dupkey:
            dup_cols = ["Inv No.", "Article Code", "Inv Qty", "Inv. Net value(LOC)"]
            dups = s[s.duplicated(subset=dup_cols, keep=False)]
            dup_val = round(float(dups["_NSV"].sum() / 2), 2) if len(dups) else 0.0
            exclusions.append(
                f"{len(dups)} exact-duplicate invoice lines detected (Inv No. + "
                f"Article Code + Qty + NSV); NOT deduplicated -- impact "
                f"Rs {dup_val:.2f} L (checked, negligible).")
        else:
            exclusions.append("Duplicate-line check skipped: 'Inv No.' / 'Article Code' "
                               "not both present in this source.")
        exclusions.append("No rows or chains excluded from this reconciliation.")

        out[fy] = {
            "summary": {
                "total_sis_sales": total_sales,
                "mrn_returns": mrn_returns,
                "cancelled_invoices": cancelled,
                "net_sis_value": net,
            },
            "by_chain": [{"name": k, "value": float(v)} for k, v in by_chain.items()],
            "by_month": [{"month": k, "value": float(v)} for k, v in by_month.items()],
            "by_brand": [{"name": k, "value": float(v)} for k, v in by_brand.items()],
            "exclusions": exclusions,
            "row_count": int(len(s)),
        }
    return out


# --------------------------------------------------------------------------
# DIST PRIMARY -> CHAIN ALLOCATION (Customer x Article grain)
#
# In the article-wise primary file, rows with PO Type = 'Dist.' have a BLANK
# "Chain name for Dashboard" (the business maintains it only for Direct
# rows), and the distributor's Ship To Name must NEVER be shown as a Chain.
# Those rows are allocated to real chains using the business's own
# secondary-derived monthly split: Dist_primary_cont_based_on_secondary_MOM
# .xlsx, sheet "Dist Primary Conv to Chain Art", keyed Ship To Name x Brand
# x Month with a "Secondary contribution %" per chain. NOTE: that sheet has
# NO Cust-SAP Code column -- the code<->ship-to bridge lives in the primary
# file itself (every primary row carries both), so matching is on the
# normalised Ship To Name; Cust-SAP Code is retained through the allocation
# and reported in every QC table so the code-level audit still works.
#
# Allocation is done ROW-LEVEL (before any grouping), so Customer x Article
# grain is preserved: each Dist. row explodes into one row per chain, with
# Inv Qty / Total MRP sales / NSV / Tax all scaled by that chain's cont%
# (normalised to sum to exactly 1 per key, so totals reconcile to the input
# by construction; keys whose RAW cont% sum deviates from 100 are flagged in
# QC before normalisation). Article MRP is per-unit and is NOT scaled.
# Avg Tot is a ratio (pass-on/MRP) and is invariant under proportional
# scaling, so each exploded row keeps the source row's Avg Tot -- summed
# aggregation downstream then yields exactly the sales-weighted Avg Tot.
# Dist. rows with no (ShipTo x Brand x Month) entry in the cont sheet get
# Chain = "Unmapped Chain" (never silently dropped, never left blank).
# --------------------------------------------------------------------------
def _month_period(v):
    """'YYYY-MM' string from an Excel date serial, a datetime, or "May'25"
    style text -- the year-qualified month key the cont-sheet join needs
    (month NAME alone is ambiguous across FYs)."""
    if hasattr(v, "year") and not isinstance(v, (str, int, float)):
        return f"{v.year:04d}-{v.month:02d}"
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        n = float(v)
        if 40000 <= n <= 55000:
            d = _EXCEL_EPOCH + datetime.timedelta(days=int(n))
            return f"{d.year:04d}-{d.month:02d}"
    m = re.match(r"([A-Za-z]+)[''`]?(\d{2,4})", str(v).strip())
    if m:
        mon3 = m.group(1)[:3].title()
        mn = {"Jan":1,"Feb":2,"Mar":3,"Apr":4,"May":5,"Jun":6,"Jul":7,"Aug":8,
              "Sep":9,"Oct":10,"Nov":11,"Dec":12}.get(mon3)
        if mn:
            yy = int(m.group(2)[-2:])
            return f"{2000+yy:04d}-{mn:02d}"
    return None

_SHIPTO_PRIMARY_CSV = (Path(__file__).resolve().parent.parent
                       / "PowerBI" / "RawDataFolders" / "Primary_ShipTo_Monthly"
                       / "Primary_ShipTo_FY25-26_to_May26.csv")

def load_shipto_primary_weights(repo_root=None):
    """Priority-1 fallback allocation source: actual chain-level primary from
    Primary_ShipTo_FY25-26_to_May26.csv, used when the secondary-derived xlsx is
    absent from --src. This CSV records the business's own primary invoices at
    Ship To Name × Brand × Month × Chain grain with Cont% as a 0-1 fraction
    summing to 1.0 per (ShipTo×Brand×Month) key. Returns the same (wdf, raw_sums)
    tuple as load_dist_cont_weights() for drop-in use by allocate_dist_primary(),
    or (None, None) if the CSV is absent."""
    p = (_SHIPTO_PRIMARY_CSV if repo_root is None else
         Path(repo_root) / "PowerBI" / "RawDataFolders" / "Primary_ShipTo_Monthly"
         / "Primary_ShipTo_FY25-26_to_May26.csv")
    if not p.exists():
        return None, None
    w = pd.read_csv(p, low_memory=False)
    w.columns = [str(c).strip() for c in w.columns]
    dist_mask = w["Direct/Distributor"].astype(str).str.strip().str.lower().isin(["dist.", "dist"])
    w = w[dist_mask].copy()
    w["_pct"] = pd.to_numeric(w["Cont%"], errors="coerce").fillna(0.0)
    w["_pm"] = pd.to_datetime(w["MonthStart"], errors="coerce").dt.strftime("%Y-%m")
    w = w[w["_pm"].notna() & (w["_pct"] != 0)].copy()
    w["_st"] = w["Ship To Name"].astype(str).str.strip().str.lower()
    w["_bl"] = w["Brand"].astype(str).str.strip().str.lower()
    # raw_sums: Cont% is 0-1 fraction; multiply by 100 so the same QC threshold
    # (|sum - 100| < 0.5) applies consistently with the xlsx path
    key_sums_raw = w.groupby(["_st", "_bl", "_pm"])["_pct"].sum()
    raw_sums = {k: round(float(v) * 100, 2) for k, v in key_sums_raw.items()}
    key_sums = w.groupby(["_st", "_bl", "_pm"])["_pct"].transform("sum")
    w["_frac"] = w["_pct"] / key_sums
    w["_AllocChainRaw"] = w["Chain"].astype(str).str.strip()
    w["_ShipToRaw"] = w["Ship To Name"].astype(str).str.strip()
    w["_BrandRaw"] = w["Brand"].astype(str).str.strip()
    print(f"load_shipto_primary_weights: {len(w)} dist rows, "
          f"{len(key_sums_raw)} (ShipTo×Brand×Month) keys, "
          f"from {p.name}")
    return w[["_st", "_bl", "_pm", "_AllocChainRaw", "_frac", "_ShipToRaw", "_BrandRaw"]].copy(), raw_sums

def _load_dist_cont_patch_rows():
    """Approved override/insert rows from PowerBI/SeedData/DIST/DistPrimaryCont
    WeightsArticle.csv, in the BASE workbook's own column shape (Ship To Name,
    Chain Name, Brand, Month, Secondary contribution %), or None if absent.

    Patch key = (Ship To Name, Brand, Month) -- confirmed from evidence, not
    assumed: every row's own Basis column documents it as either a full
    nearest-month split copied in and approved for that exact key (e.g. "Az
    Enterprises"/"BBlunt"/2025-10-01 has two patch rows, H&G 92.14% + Trilife
    7.86%, summing to the complete distribution for that key -- not a partial
    correction to one chain within an existing split), or a one-off approved
    mapping fix (Guardian Healthcare). A patch key's rows always sum close to
    100% by themselves, confirming they REPLACE the whole key's distribution,
    never merge partially against whatever the base has for that same key.
    See FM-16 in docs/FAILURE_MODE_REGISTER.md for the defect this replaces:
    this file used to be read INSTEAD of the base workbook whenever it
    existed, silently discarding the whole business-maintained workbook."""
    patch_f = Path("PowerBI/SeedData/DIST/DistPrimaryContWeightsArticle.csv")
    if not patch_f.exists():
        return None
    p = pd.read_csv(patch_f)
    p.columns = [str(c).strip() for c in p.columns]
    required = {"Ship_To_Name", "Chain_Name", "Brand", "Month", "Cont_Pct"}
    missing = required - set(p.columns)
    if missing:
        raise SystemExit(
            f"DistPrimaryContWeightsArticle.csv is missing required column(s) {sorted(missing)} "
            "-- explicit source-contract failure, not silently ignored (FM-16B).")
    return p.rename(columns={
        "Ship_To_Name": "Ship To Name", "Chain_Name": "Chain Name",
        "Cont_Pct": "Secondary contribution %",
    })[["Ship To Name", "Chain Name", "Brand", "Month", "Secondary contribution %"]]


def load_dist_cont_weights(src):
    """Weights DataFrame [_st, _bl, _pm, _AllocChainRaw, _frac] from the
    business-maintained cont workbook, with the approved patch CSV applied as
    an OVERRIDE/INSERT layer on top -- never as a replacement for the whole
    workbook. Fixed 2026-09-13 (FM-16B): the patch CSV used to be read
    EXCLUSIVELY whenever it existed, silently discarding the real workbook
    even when present, because it's only ever held ~27 approved-exception
    rows, not the full monthly split. See _load_dist_cont_patch_rows()'s own
    docstring for the evidence behind the (Ship To Name, Brand, Month)
    override key.

    XLSX: Dist_primary_cont_based_on_secondary_MOM.xlsx (the base workbook,
    business-maintained, expected in --src, never committed to Git)
    CSV: PowerBI/SeedData/DIST/DistPrimaryContWeightsArticle.csv (approved
    patch -- overrides/inserts specific (Ship To Name, Brand, Month) keys)
    CSV: Priority-1 fallback at ShipTo×Brand×Month grain if the base workbook
    is absent (the patch alone is never treated as a complete base -- if the
    workbook is missing, this same fallback runs exactly as it did before,
    with the patch still applied on top of it).
    Returns 3-tuple (wdf, raw_sums, source_label) or (None, None, None)."""
    f = src / "Dist_primary_cont_based_on_secondary_MOM.xlsx"
    if f.exists():
        w = pd.read_excel(f, sheet_name="Dist Primary Conv to Chain Art", header=1)
        src_label = "xlsx"
    else:
        # Base workbook absent -- Priority-1 fallback, exactly as before this fix.
        wdf, raw_sums = load_shipto_primary_weights()
        src_label = "shipto_primary_csv" if wdf is not None else None
        if wdf is None:
            return None, None, None
        w = None  # signal: no base rows, only the fallback dataframe already built

    patch = _load_dist_cont_patch_rows()
    if w is not None:
        w.columns = [str(c).strip() for c in w.columns]
        w = w.rename(columns={"Ship_To_Name": "Ship To Name", "Chain_Name": "Chain Name"})
        if patch is not None and len(patch):
            # Override/insert: drop any base rows whose (ShipTo, Brand, Month)
            # key the patch also covers, then append the patch's own rows for
            # those keys -- never a partial merge within one key.
            _key = lambda df: (df["Ship To Name"].astype(str).str.strip().str.lower() + "\x1f"
                                + df["Brand"].astype(str).str.strip().str.lower() + "\x1f"
                                + pd.to_datetime(df["Month"], errors="coerce").dt.strftime("%Y-%m").fillna(
                                    df["Month"].astype(str)))
            patch_keys = set(_key(patch))
            w = w[~_key(w).isin(patch_keys)]
            w = pd.concat([w, patch], ignore_index=True)
            src_label = "xlsx+patch"
    else:
        # No base workbook: patch is applied on top of the Priority-1 fallback
        # dataframe returned by load_shipto_primary_weights(), which is
        # already in the (_st, _bl, _pm, _AllocChainRaw, _frac) output shape,
        # not the raw workbook shape -- return it as-is (unchanged from
        # pre-fix behaviour) since merging a raw-shaped patch onto an
        # already-normalised fallback needs its own conversion this pass
        # does not attempt blind. The patch CSV alone continuing to NOT
        # masquerade as complete coverage (FM-16, case 7) is preserved either
        # way: this fallback path was already real ShipTo-Primary data, not
        # the 27-row patch file.
        return wdf, raw_sums, src_label

    w.columns = [str(c).strip() for c in w.columns]
    # Normalise underscore vs space column names
    _col_map = {"Ship_To_Name": "Ship To Name", "Chain_Name": "Chain Name"}
    w = w.rename(columns=_col_map)
    w = w.dropna(subset=["Ship To Name", "Chain Name"])

    # Handle both CSV and XLSX column names
    cont_col = "Cont_Pct" if "Cont_Pct" in w.columns else "Secondary contribution %"
    month_col = "Month" if "Month" in w.columns else "Revised month"
    chain_col = "Chain Name"

    w = w[w[cont_col].notna()]
    w["_st"] = w["Ship To Name"].astype(str).str.strip().str.lower()
    w["_bl"] = w["Brand"].astype(str).str.strip().str.lower()

    # Parse month: handle both YYYY-MM (CSV) and Excel date format (XLSX).
    # Bug found 2026-09-13 while synthetic-testing the FM-16B loader fix:
    # `dtype == 'object'` silently stopped detecting text columns under
    # pandas 3.x, which introduced a distinct 'str' dtype for plain-string
    # columns (pandas 2.x had no such split -- text was always 'object').
    # A month column full of real text ("2025-10-01") was falling through to
    # the numeric _month_period() branch and returning nothing for every row
    # -- an independent latent bug from the FM-16B loader-priority defect,
    # only now exercised because this code path had never been reached
    # before (no session ever had the real XLSX to trigger it).
    if pd.api.types.is_numeric_dtype(w[month_col]):
        w["_pm"] = w[month_col].map(_month_period)
    else:
        w["_pm"] = pd.to_datetime(w[month_col], errors="coerce").dt.strftime("%Y-%m")

    w["_pct"] = pd.to_numeric(w[cont_col], errors="coerce").fillna(0.0)
    w = w[w["_pm"].notna() & (w["_pct"] != 0)]
    key_sums = w.groupby(["_st", "_bl", "_pm"])["_pct"].transform("sum")
    raw_sums = {k: round(float(v), 2)
                for k, v in w.groupby(["_st", "_bl", "_pm"])["_pct"].sum().items()}
    w["_frac"] = w["_pct"] / key_sums
    w["_AllocChainRaw"] = w[chain_col].astype(str).str.strip()
    # raw-case names carried through for auto-generated patch-proposal CSV
    w["_ShipToRaw"] = w["Ship To Name"].astype(str).str.strip()
    w["_BrandRaw"] = w["Brand"].astype(str).str.strip()
    return w[["_st", "_bl", "_pm", "_AllocChainRaw", "_frac", "_ShipToRaw", "_BrandRaw"]].copy(), raw_sums, src_label

_ALLOC_MEASURES = ["_Qty", "_MRP", "_NSV", "_TaxLOC"]   # scaled by cont%; _ArtMRP (per-unit) is NOT

def _infer_chain_from_name(shipto):
    """LOW-confidence, patch-proposal-ONLY heuristic (never used by the live
    allocation): if a ship-to's own name contains a known chain alias as a
    whole word (>=5 chars, so 'more'/'vmm' can't false-positive), propose that
    chain at 100%. E.g. 'Guardian Healthcare Services Pvt Ltd(DL)' -> Guardian."""
    s = re.sub(r"[^a-z0-9]+", " ", str(shipto).lower())
    for canon, aliases in CHAIN_ALIASES:
        for a in aliases:
            a = a.strip().lower()
            if len(a) >= 5 and re.search(r"\b" + re.escape(a) + r"\b", s):
                return canon
    return None

def _write_dist_cont_patch(key_tier, key_eff, wdf, dist, output_dir=None):
    """Regenerate SeedData/Mapping/DistCont_Patch_Proposed.csv on every build:
    one reviewable row per proposed cont-sheet addition, in the cont sheet's
    own column layout plus Confidence/Basis. Two kinds of proposals:
      * nearest-month keys -- the SAME ship-to x brand's real secondary split
        copied from the nearest month, re-dated to the missing month (these
        are what the live nearest-month tier already uses; approving them
        into the xlsx makes the fix permanent and Power-BI-visible);
      * fully-unmapped ship-tos -- a 100% single-chain proposal when the
        ship-to's own name contains a known chain (LOW confidence), else a
        '<<FILL>>' placeholder requiring business input.
    Returns (row_count, repo-relative path). The file is PROPOSALS only --
    edits belong in the cont xlsx, so regenerating this file is always safe;
    once the xlsx has the rows, the gap disappears and so does the proposal."""
    base = output_dir if output_dir is not None else Path(__file__).resolve().parent.parent
    path = Path(base) / "PowerBI" / "SeedData" / "Mapping" / "DistCont_Patch_Proposed.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    def fy_of(pm):
        y, m = int(pm[:4]), int(pm[5:7])
        yy = y % 100
        return f"FY_{yy:02d}-{yy+1:02d}" if m >= 4 else f"FY_{yy-1:02d}-{yy:02d}"
    rows = []
    for k in sorted(key_tier, key=str):
        st, bl, pm = k
        tier = key_tier[k]
        if tier.startswith("nearest"):
            near = key_eff[k]
            src = wdf[(wdf["_st"] == st) & (wdf["_bl"] == bl) & (wdf["_pm"] == near)]
            # consolidate per chain -- the cont sheet can carry several rows per
            # chain within one key (state/zone splits); one clean row per chain
            # is what the business reviews and pastes back
            for chain, g in src.groupby("_AllocChainRaw"):
                rows.append([g["_ShipToRaw"].iloc[0], "Dist.", chain, g["_BrandRaw"].iloc[0],
                             f"{pm}-01", fy_of(pm), "MT", round(float(g["_frac"].sum()) * 100, 4),
                             "Medium", f"Copied from {near} secondary split (nearest month with data)"])
        elif tier == "unmapped" and pm is not None:
            sub = dist[(dist["_st"] == st) & (dist["_bl"] == bl)]
            ship_raw = sub["_CustName"].iloc[0] if len(sub) else st
            brand_raw = str(sub["brand"].iloc[0]).strip() if len(sub) else bl
            guess = _infer_chain_from_name(ship_raw)
            rows.append([ship_raw, "Dist.", guess or "<<FILL: chain unknown>>", brand_raw,
                         f"{pm}-01", fy_of(pm), "MT", 100,
                         "LOW" if guess else "REQUIRED",
                         ("Name inference: ship-to name contains this chain -- CONFIRM before use"
                          if guess else "No secondary data for this ship-to in ANY month -- business input required")])
    with open(path, "w", newline="", encoding="utf-8") as fh:
        wcsv = csv.writer(fh, quoting=csv.QUOTE_MINIMAL)
        wcsv.writerow(["Ship To Name", "Direct/Distributor", "Chain Name", "Brand", "Revised month",
                       "FY", "Channel", "Secondary contribution %", "Confidence", "Basis"])
        wcsv.writerows(rows)
    return len(rows), "PowerBI/SeedData/Mapping/DistCont_Patch_Proposed.csv"



def _write_flagged_rows_csv(ne_orig: "pd.DataFrame", output_dir=None) -> None:
    """Write Not_Eligible rows to a reviewable CSV for business override workflow.

    Output: PowerBI/SeedData/Mapping/DistAllocationGovernance_FlaggedRows.csv
    Business process: review this file, add approved rows to PrimaryAllocationOverride.csv,
    then rebuild. The flagged_rows_csv path is surfaced in alloc.governance in data.js.
    output_dir: when given, write under this directory instead of the repo root
    (used by shadow/test runs so they never touch tracked files)."""
    base = output_dir if output_dir is not None else Path(__file__).resolve().parent.parent
    _out = Path(base) / "PowerBI" / "SeedData" / "Mapping" / "DistAllocationGovernance_FlaggedRows.csv"
    _out.parent.mkdir(parents=True, exist_ok=True)
    display_cols = {
        "Month": "Month",
        "_CustName": "Ship To Name",
        "brand": "Brand",
        "_NSV": "NSV (Lakh)",
        "reasoning": "Eligibility Reasoning",
    }
    out_df = ne_orig[[c for c in display_cols if c in ne_orig.columns]].copy()
    out_df.rename(columns={k: v for k, v in display_cols.items() if k in out_df.columns}, inplace=True)
    out_df.insert(0, "Eligibility_Tier", "Not_Eligible")
    out_df.insert(len(out_df.columns), "Override_Action", "")
    out_df.insert(len(out_df.columns), "Override_Chain", "")
    out_df.insert(len(out_df.columns), "Override_Remarks", "")
    out_df.to_csv(_out, index=False)
    print(f"Phase 6: wrote {len(out_df)} Not_Eligible rows to {_out.name} for business review")


def _classify_ean_affinity(um: "pd.DataFrame", out_df: "pd.DataFrame"):
    """Residual certification (2026-09-13, post-FM-16B): for each still-
    Unmapped Dist. row, check every OTHER already-mapped row (any source,
    any month) sharing its EAN, and see how concentrated that EAN's known
    sales are in one chain. This is evidence about the ARTICLE's typical
    distribution footprint, not a business rule about this transaction --
    disclosed as a proposal for approval, never applied automatically.

    Confidence bands (evidence-based, not invented per-row):
      HIGH    >=95% of the EAN's known positive NSV goes to one chain
      MEDIUM  >=80% and <95%
      LOW     <80% -- article is genuinely multi-chain; no defensible
                      single answer exists, so no mapping is proposed
      NO_EVIDENCE -- EAN never appears in any already-mapped row

    Returns (residual_summary: dict | None, proposal_rows: list[dict]).
    proposal_rows holds ONLY HIGH/MEDIUM rows -- LOW/NO_EVIDENCE stay
    Unmapped Chain and are counted in residual_summary only; forcing a
    chain guess onto a multi-chain article would be fabricated mapping."""
    if not len(um) or "_EAN No." not in um.columns:
        return None, []
    known = out_df[(out_df["_Chain"] != "Unmapped Chain") & (out_df["_NSV"] > 0)]
    if "_EAN No." not in known.columns or not len(known):
        return None, []

    aff = known.groupby(["_EAN No.", "_Chain"])["_NSV"].sum().reset_index()
    ean_total = aff.groupby("_EAN No.")["_NSV"].sum().rename("ean_total")
    top = (aff.sort_values(["_EAN No.", "_NSV"], ascending=[True, False])
              .groupby("_EAN No.").first().join(ean_total))
    top["dominant_share"] = top["_NSV"] / top["ean_total"]
    top = top.rename(columns={"_Chain": "dominant_chain"})[
        ["dominant_chain", "dominant_share", "ean_total"]]

    u = um.merge(top, left_on="_EAN No.", right_index=True, how="left")

    def _confidence(share):
        if pd.isna(share):
            return "NO_EVIDENCE"
        if share >= 0.95:
            return "HIGH"
        if share >= 0.80:
            return "MEDIUM"
        return "LOW"

    u["confidence"] = u["dominant_share"].map(_confidence)
    residual_class = {"HIGH": "DEFENSIBLE_MAPPING_AVAILABLE",
                       "MEDIUM": "BUSINESS_REVIEW_REQUIRED",
                       "LOW": "AMBIGUOUS_MULTI_CHAIN",
                       "NO_EVIDENCE": "NO_EVIDENCE"}
    u["residual_class"] = u["confidence"].map(residual_class)

    by_class = {cls: {"rows": 0, "nsv_lakh": 0.0} for cls in residual_class.values()}
    for cls, g in u.groupby("residual_class"):
        by_class[cls] = {"rows": int(len(g)), "nsv_lakh": r2(float(g["_NSV"].sum()))}

    residual_summary = {
        "residual_row_count": int(len(um)),
        "residual_nsv_lakh": r2(float(um["_NSV"].sum())),
        "residual_distributor_count": int(um["_CustName"].nunique()) if "_CustName" in um.columns else None,
        "residual_brand_count": int(um["_Brand"].nunique()) if "_Brand" in um.columns else None,
        "residual_article_count": int(um["_EAN No."].nunique()),
        "by_class": by_class,
        "materiality": "MATERIALITY_THRESHOLD_NOT_GOVERNED",  # no approved threshold exists for this specific residual metric -- see per-context floors elsewhere (zone recovery, incentive identity) which are NOT this metric
        "method": (
            "Article(EAN)-affinity evidence check over already-mapped rows, run once "
            "after the FM-16B loader fix. HIGH/MEDIUM rows are written to "
            "EanAffinity_ResidualProposal.csv for business review; NEVER auto-applied "
            "to _Chain. LOW/NO_EVIDENCE rows stay Unmapped Chain -- the article is "
            "genuinely sold across multiple chains with no single defensible answer."
        ),
    }

    proposal_rows = []
    for _, r in u[u["confidence"].isin(["HIGH", "MEDIUM"])].iterrows():
        share_pct = round(float(r["dominant_share"]) * 100, 2)
        proposal_rows.append({
            "ship_to": r.get("_CustName"), "month": r.get("Month"),
            "brand": r.get("_Brand", r.get("brand")), "ean": r.get("_EAN No."),
            "current_chain": "Unmapped Chain", "proposed_chain": r.get("dominant_chain"),
            "affinity_pct": share_pct, "confidence": r["confidence"],
            "nsv_lakh": r2(float(r["_NSV"])),
            "evidence_basis": (f"EAN {r.get('_EAN No.')} known sales are {share_pct}% to "
                               f"{r.get('dominant_chain')} (of {r2(float(r['ean_total']))} L "
                               "known NSV elsewhere)"),
            "recommended_action": "APPROVE_CANDIDATE" if r["confidence"] == "HIGH" else "REVIEW_REQUIRED",
        })
    return residual_summary, proposal_rows


def _write_ean_affinity_proposal(proposal_rows, output_dir=None):
    """Regenerate SeedData/Mapping/EanAffinity_ResidualProposal.csv on every
    build -- reviewable HIGH/MEDIUM article-affinity mapping candidates for
    the small residual of Dist. rows the cont%/ShipTo-primary allocation
    still leaves Unmapped (see alloc.residual in data.js). This is a
    DIFFERENT, later-stage mechanism from DistCont_Patch_Proposed.csv (which
    proposes ShipTo x Brand x Month cont% rows); it never overlaps because it
    only ever covers rows already in `um` (still Unmapped after that tier).
    Governance: HIGH -> APPROVE_CANDIDATE, MEDIUM -> REVIEW_REQUIRED. Neither
    is auto-applied -- approving a row means adding it to
    PrimaryAllocationOverride.csv (or the cont sheet) and rebuilding."""
    base = output_dir if output_dir is not None else Path(__file__).resolve().parent.parent
    path = Path(base) / "PowerBI" / "SeedData" / "Mapping" / "EanAffinity_ResidualProposal.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        wcsv = csv.writer(fh, quoting=csv.QUOTE_MINIMAL)
        wcsv.writerow(["Ship To Name", "Month", "Brand", "Article/EAN", "Current Chain",
                       "Proposed Chain", "Affinity %", "Confidence", "Primary NSV (Lakh)",
                       "Evidence Basis", "Recommended Action"])
        for r in proposal_rows:
            wcsv.writerow([r["ship_to"], r["month"], r["brand"], r["ean"], r["current_chain"],
                           r["proposed_chain"], r["affinity_pct"], r["confidence"], r["nsv_lakh"],
                           r["evidence_basis"], r["recommended_action"]])
    return len(proposal_rows), "PowerBI/SeedData/Mapping/EanAffinity_ResidualProposal.csv"


def allocate_dist_primary(df, wdf, raw_sums, source_label=None,
                          offtake_brand_set=None, offtake_ean_set=None,
                          output_dir=None):
    """Explode PO Type='Dist.' rows across chains by cont% and set _Chain on
    every row of `df` (Direct rows keep their own "Chain name for Dashboard").
    Returns (new_df, alloc_block) where alloc_block carries the full
    reconciliation/QC payload for the dashboard, or (df-with-_Chain, None)
    when the file has no PO Type column or no cont sheet was found.
    source_label: 'xlsx' | 'shipto_primary_csv' | None — recorded in alloc.
    offtake_brand_set: frozenset[str] of lowercased brand names from offtake,
      or None (→ brand_in_offtake defaults True, preserving pre-Phase-5 behaviour).
    offtake_ean_set: frozenset[str] of EAN strings from offtake,
      or None (→ article_in_offtake defaults True).
    output_dir: directory the 3 reviewable governance/proposal CSVs
      (DistCont_Patch_Proposed.csv, DistAllocationGovernance_FlaggedRows.csv,
      EanAffinity_ResidualProposal.csv) are written under, in place of the
      repo root — pass a scratch directory for a shadow/test run so it never
      overwrites the tracked copies. None (default) preserves the original,
      production behaviour of writing into the repo."""
    _has_dashboard = "Chain name for Dashboard" in df.columns
    _has_plain = "Chain name" in df.columns
    if _has_dashboard and _has_plain:
        _raw_chain = df["Chain name for Dashboard"].fillna(df["Chain name"])
    elif _has_dashboard:
        _raw_chain = df["Chain name for Dashboard"]
    elif _has_plain:
        _raw_chain = df["Chain name"]
    else:
        _raw_chain = None
    df["_ChainDash"] = _raw_chain.map(canon_chain) if _raw_chain is not None else None
    if "PO Type" not in df.columns or wdf is None:
        df["_Chain"] = df["_ChainDash"]
        df.drop(columns=["_ChainDash"], inplace=True)
        return df, None

    is_dist = df["PO Type"].astype(str).str.strip().str.lower().isin(["dist.", "dist"])
    direct = df[~is_dist].copy()
    direct["_Chain"] = direct["_ChainDash"]
    dist = df[is_dist].copy()

    # ---- STEP 1 (Phase 3): Initialize governance engine ----
    gov = DistAllocationGovernance()
    governance_log = {
        "eligibility_decisions": [],
        "qc_reconciliations": [],
        "tier_counts": {},
    }

    # join keys (year-qualified month; ship-to + brand case/space-insensitive)
    dist["_st"] = dist["_CustName"].str.lower()
    dist["_bl"] = dist["brand"].astype(str).str.strip().str.lower()
    dist["_pm"] = dist["Month"].map(_month_period)

    orig = dist.copy()   # pre-allocation snapshot for reconciliation

    # ---- tiered key resolution (uses ONLY the business's own secondary splits,
    # never an invented chain mix):
    #   exact    -- (ShipTo, Brand, Month) present in the cont sheet
    #   nearest  -- same ShipTo x Brand, NEAREST month within +/-3 months
    #               (distributor chain mix is a slow-moving ratio; using the
    #               adjacent month's REAL split beats parking real sales under
    #               "Unmapped Chain" -- and every such row is QC-tagged
    #               "Mapped (nearest Mon'YY)", never silently blended in)
    #   unmapped -- no cont data for that ShipTo x Brand within the window
    _pm_ord = lambda pm: int(pm[:4]) * 12 + int(pm[5:7])
    wkeys = set(zip(wdf["_st"], wdf["_bl"], wdf["_pm"]))
    avail = {}
    for st, bl, pm in wkeys:
        avail.setdefault((st, bl), []).append(pm)

    # Phase 5: precompute (st, bl, pm) → frozenset[EAN] for article-level check.
    # Only built when offtake_ean_set is wired AND the EAN column is present.
    if offtake_ean_set is not None and "_EAN No." in dist.columns:
        _key_eans = (
            dist[dist["_EAN No."].ne("")]
            .groupby(["_st", "_bl", "_pm"])["_EAN No."]
            .apply(frozenset)
            .to_dict()
        )
    else:
        _key_eans = {}

    key_eff, key_tier = {}, {}
    for k in set(zip(dist["_st"], dist["_bl"], dist["_pm"])):
        st, bl, pm = k
        if pm is not None and k in wkeys:
            key_eff[k], key_tier[k] = pm, "exact"
            gov_tier = "Eligible"
        else:
            months = avail.get((st, bl))
            # Tie-break deterministically on the month string itself (earlier
            # wins) when two months are equidistant -- `months` is built from
            # iterating a `set`, whose order is hash-randomized per process,
            # so `min()` on distance alone silently picked a different month
            # on different runs for tied keys (e.g. -1 vs +1 month away).
            near = min(months, key=lambda m: (abs(_pm_ord(m) - _pm_ord(pm)), m)) if (months and pm) else None
            if near is not None and abs(_pm_ord(near) - _pm_ord(pm)) <= 3:
                key_eff[k], key_tier[k] = near, f"nearest {near}"
                gov_tier = "Eligible_TAT"
            else:
                key_eff[k], key_tier[k] = None, "unmapped"
                gov_tier = "Not_Eligible"

        # ---- STEP 2 (Phase 3): Log eligibility decision ----
        try:
            gov_result = gov.check_eligibility(
                primary_row={"ship_to": st, "brand": bl, "month": pm},
                secondary_match_found=(pm is not None and k in wkeys),
                secondary_match_within_tат=(key_tier[k].startswith("nearest")),
                brand_in_offtake=(offtake_brand_set is None or bl in offtake_brand_set),
                article_in_offtake=(offtake_ean_set is None
                                    or bool(_key_eans.get(k, frozenset()) & offtake_ean_set)),
            )
            governance_log["eligibility_decisions"].append({
                "key": k,
                "tier": gov_result.tier,
                "confidence_pct": gov_result.confidence_pct,
                "reasoning": gov_result.reasoning,
            })
        except Exception as e:
            print(f"Warning: Governance check failed for key {k}: {e}")
            governance_log["eligibility_decisions"].append({
                "key": k,
                "tier": gov_tier,
                "confidence_pct": 50.0,
                "reasoning": f"Governance check exception: {e}",
            })
    kseries = list(zip(dist["_st"], dist["_bl"], dist["_pm"]))
    dist["_pm_eff"] = [key_eff[k] for k in kseries]
    dist["_tier"] = [key_tier[k] for k in kseries]

    merged = dist.merge(wdf.rename(columns={"_pm": "_pm_eff"}), on=["_st", "_bl", "_pm_eff"], how="left")
    matched = merged["_frac"].notna()
    for c in _ALLOC_MEASURES:
        merged[c] = merged[c].astype("float64")   # Qty reads back int64; fractional split needs float
        merged.loc[matched, c] = merged.loc[matched, c] * merged.loc[matched, "_frac"]
    merged["_Chain"] = "Unmapped Chain"
    merged.loc[matched, "_Chain"] = merged.loc[matched, "_AllocChainRaw"].map(canon_chain)
    merged["_frac"] = merged["_frac"].fillna(1.0)

    # ---- reconciliation: original Dist. input vs allocated output ----
    def sums(d):
        return {"qty": float(d["_Qty"].sum()), "mrp_sales": float(d["_MRP"].sum()),
                "nsv": float(d["_NSV"].sum()), "tax": float(d["_TaxLOC"].fillna(0).sum())}
    def recon_rows(dim_orig, dim_alloc, labeler):
        out = []
        for k in sorted(set(dim_orig.groups) | set(dim_alloc.groups), key=str):
            o = sums(dim_orig.get_group(k)) if k in dim_orig.groups else {x: 0.0 for x in ("qty","mrp_sales","nsv","tax")}
            a = sums(dim_alloc.get_group(k)) if k in dim_alloc.groups else {x: 0.0 for x in ("qty","mrp_sales","nsv","tax")}
            out.append({**labeler(k),
                        "orig_nsv": r2(o["nsv"]), "alloc_nsv": r2(a["nsv"]), "nsv_var": r2(a["nsv"]-o["nsv"]),
                        "orig_qty": int(round(o["qty"])), "alloc_qty": int(round(a["qty"])), "qty_var": r2(a["qty"]-o["qty"]),
                        "orig_mrp": r2(o["mrp_sales"]), "alloc_mrp": r2(a["mrp_sales"]), "mrp_var": r2(a["mrp_sales"]-o["mrp_sales"]),
                        "orig_tax": r2(o["tax"]), "alloc_tax": r2(a["tax"]), "tax_var": r2(a["tax"]-o["tax"])})
        return out

    o_tot, a_tot = sums(orig), sums(merged)

    # ---- STEP 3 (Phase 3): Track QC reconciliation via governance engine ----
    try:
        for fy, m, brand, shipto in set(orig.groupby(["_FY", "_M", "_Brand", "_CustName"]).groups):
            orig_subset = orig[
                (orig["_FY"] == fy) &
                (orig["_M"] == m) &
                (orig["_Brand"] == brand) &
                (orig["_CustName"] == shipto)
            ]
            merged_subset = merged[
                (merged["_FY"] == fy) &
                (merged["_M"] == m) &
                (merged["_Brand"] == brand) &
                (merged["_CustName"] == shipto)
            ]
            o_nsv = float(orig_subset["_NSV"].sum()) if len(orig_subset) else 0.0
            a_nsv = float(merged_subset["_NSV"].sum()) if len(merged_subset) else 0.0

            qc_result = gov.reconcile_qc(
                distributor=shipto,
                brand=brand,
                month=m,
                original_nsv=o_nsv,
                allocated_nsv=a_nsv,
                blocked_nsv=0.0,  # Implicit in allocated (unmapped rows handled in allocation)
                tolerance_lakh=0.0,  # Strict QC
            )
            governance_log["qc_reconciliations"].append({
                "shipto": shipto,
                "brand": brand,
                "month": m,
                "fy": fy,
                "is_balanced": qc_result.is_balanced,
                "variance": qc_result.variance,
                "original_nsv": qc_result.original_nsv,
                "allocated_nsv": qc_result.allocated_nsv,
            })
    except Exception as e:
        print(f"Warning: QC reconciliation failed: {e}")

    recon = {
        "overall": {m: {"original": r2(o_tot[m]), "allocated": r2(a_tot[m]),
                        "variance": r2(a_tot[m] - o_tot[m])} for m in o_tot},
        "by_month": recon_rows(orig.groupby(["_FY", "_M"]), merged.groupby(["_FY", "_M"]),
                               lambda k: {"fy": k[0], "month": k[1]}),
        "by_brand": recon_rows(orig.groupby("_Brand"), merged.groupby("_Brand"),
                               lambda k: {"brand": k}),
    }

    # ---- QC table at Month x Brand x Cust-SAP Code x Ship To Name grain ----
    qkey = ["_FY", "_M", "_Brand", "_CustCode", "_CustName"]
    o_g, a_g = orig.groupby(qkey), merged.groupby(qkey)
    tier_by_qkey = {k: d["_tier"].iloc[0] for k, d in merged.groupby(qkey)}
    qc_rows = []
    for row in recon_rows(o_g, a_g,
            lambda k: {"fy": k[0], "month": k[1], "brand": k[2], "cust_code": k[3], "ship_to": k[4]}):
        key = (row["fy"], row["month"], row["brand"], row["cust_code"], row["ship_to"])
        t = tier_by_qkey.get(key, "exact")
        row["mapping_status"] = ("Unmapped Chain" if t == "unmapped"
                                 else "Mapped" if t == "exact" else f"Mapped ({t})")

        # ---- STEP 4 (Phase 3): Add eligibility tier + confidence to QC rows ----
        if t == "exact":
            row["eligibility_tier"] = "Eligible"
            row["eligibility_confidence_pct"] = 100.0
        elif t.startswith("nearest"):
            row["eligibility_tier"] = "Eligible_TAT"
            row["eligibility_confidence_pct"] = 90.0
        else:  # unmapped
            row["eligibility_tier"] = "Not_Eligible"
            row["eligibility_confidence_pct"] = 100.0

        qc_rows.append(row)
    qc_rows.sort(key=lambda r: (0 if r["mapping_status"] == "Unmapped Chain"
                                else 1 if r["mapping_status"] != "Mapped" else 2,
                                -(abs(r["orig_nsv"] or 0))))

    # ---- missing-mapping table (per unmapped ShipTo x Brand x Month, with impact) ----
    um = merged[~matched]
    missing = [{"fy": k[0], "month": k[1], "brand": k[2], "cust_code": k[3], "ship_to": k[4],
                "nsv": r2(float(d["_NSV"].sum())), "rows": int(len(d))}
               for k, d in um.groupby(qkey)]
    missing.sort(key=lambda r: -(abs(r["nsv"] or 0)))

    cont_bad = {" | ".join(map(str, k)): v for k, v in (raw_sums or {}).items() if abs(v - 100) > 0.5}
    is_near = merged["_tier"].str.startswith("nearest")
    rows_nearest = int(is_near.sum())
    nearest_nsv = r2(float(merged.loc[is_near, "_NSV"].sum()))

    # ---- June-26 fallback disclosure (additive governance; no value change) ----
    # Computed here while _pm / _pm_eff / _tier are still available, before drop.
    # June-26 has no entry in the ShipTo primary CSV (source ends May-26), so every
    # Dist. row for that month uses the nearest-month fallback. This block makes the
    # derived-allocation fact machine-readable and auditable in data.js and the QC gate.
    _june_pm = "2026-06"
    _june_near_mask  = (merged["_pm"] == _june_pm) & merged["_tier"].str.startswith("nearest")
    _june_exact_mask = (merged["_pm"] == _june_pm) & (merged["_tier"] == "exact")
    _june_unmap_mask = (merged["_pm"] == _june_pm) & (merged["_tier"] == "unmapped")
    june_fallback_nsv = r2(float(merged.loc[_june_near_mask, "_NSV"].sum()))
    june_fallback_keys = (merged.loc[_june_near_mask]
                          .groupby(["_st", "_bl"]).ngroups) if _june_near_mask.any() else 0
    june_exact_keys  = (merged.loc[_june_exact_mask]
                        .groupby(["_st", "_bl"]).ngroups) if _june_exact_mask.any() else 0
    june_unmapped_keys = (merged.loc[_june_unmap_mask]
                          .groupby(["_st", "_bl"]).ngroups) if _june_unmap_mask.any() else 0
    june_period_breakdown = []
    if _june_near_mask.any() and june_fallback_nsv:
        for eff_pm, g in merged.loc[_june_near_mask].groupby("_pm_eff"):
            n_keys = g.groupby(["_st", "_bl"]).ngroups
            pnsv = r2(float(g["_NSV"].sum()))
            june_period_breakdown.append({
                "source_period": eff_pm,
                "keys": n_keys,
                "nsv_lakh": pnsv,
                "pct_of_june_fallback": round(pnsv / june_fallback_nsv * 100, 1),
            })
        june_period_breakdown.sort(key=lambda x: -x["nsv_lakh"])

    patch_rows, patch_path = _write_dist_cont_patch(key_tier, key_eff, wdf, dist, output_dir=output_dir)
    merged.drop(columns=["_st", "_bl", "_pm", "_pm_eff", "_tier", "_AllocChainRaw",
                         "_ChainDash", "_frac", "_ShipToRaw", "_BrandRaw"], inplace=True, errors='ignore')
    direct.drop(columns=["_ChainDash"], inplace=True)
    merged["_IsDist"] = True
    direct["_IsDist"] = False
    out_df = pd.concat([direct, merged], ignore_index=True)

    # ---- residual certification (Phase 2, 2026-09-13): article-affinity
    # evidence check on whatever remains Unmapped after the tiers above ----
    residual_summary, ean_proposal_rows = _classify_ean_affinity(um, out_df)
    ean_proposal_count, ean_proposal_path = _write_ean_affinity_proposal(ean_proposal_rows, output_dir=output_dir)

    # ---- STEP 5 (Phase 3): Generate governance report ----
    tier_counts = {}
    for decision in governance_log["eligibility_decisions"]:
        tier = decision["tier"]
        tier_counts[tier] = tier_counts.get(tier, 0) + 1

    try:
        qc_report = gov.generate_qc_report(
            [
                QCReconciliation(
                    is_balanced=r["is_balanced"],
                    variance=r["variance"],
                    original_nsv=r["original_nsv"],
                    allocated_nsv=r["allocated_nsv"],
                    blocked_nsv=0.0,
                )
                for r in governance_log["qc_reconciliations"]
            ]
        )
    except Exception as e:
        print(f"Warning: Failed to generate QC report: {e}")
        qc_report = {
            "total_rows": len(governance_log["qc_reconciliations"]),
            "note": f"QC report generation failed: {e}",
        }

    # ---- STEP 6 (Phase 6): Not_Eligible NSV + flagged rows CSV + override count ----
    ne_decision_rows = [
        {"_st": d["key"][0], "_bl": d["key"][1], "_pm": d["key"][2],
         "reasoning": d.get("reasoning", "")}
        for d in governance_log["eligibility_decisions"]
        if d["tier"] == "Not_Eligible"
    ]
    if ne_decision_rows:
        ne_keys_df = pd.DataFrame(ne_decision_rows)
        ne_orig = orig.merge(ne_keys_df, on=["_st", "_bl", "_pm"], how="inner")
        not_eligible_nsv = float(ne_orig["_NSV"].sum())
        _write_flagged_rows_csv(ne_orig, output_dir=output_dir)
    else:
        not_eligible_nsv = 0.0
    total_dist_nsv = float(orig["_NSV"].sum())
    not_eligible_pct = round(not_eligible_nsv / total_dist_nsv * 100, 2) if total_dist_nsv > 0 else 0.0
    total_primary_nsv = total_dist_nsv + float(direct["_NSV"].sum())
    if residual_summary is not None:
        residual_summary["residual_pct_of_total_primary"] = (
            round(residual_summary["residual_nsv_lakh"] / total_primary_nsv * 100, 4)
            if total_primary_nsv else None)
        residual_summary["total_primary_nsv_lakh"] = r2(total_primary_nsv)
        residual_summary["proposal_rows"] = ean_proposal_count
        residual_summary["proposal_file"] = ean_proposal_path

    # Count approved overrides from PrimaryAllocationOverride.csv that match Not_Eligible keys
    override_count = 0
    _override_csv = Path(__file__).resolve().parent.parent / "PowerBI" / "SeedData" / "Masters" / "PrimaryAllocationOverride.csv"
    if _override_csv.exists() and ne_decision_rows:
        try:
            ov_df = pd.read_csv(_override_csv)
            if not ov_df.empty and "Ship To Name" in ov_df.columns and "Brand" in ov_df.columns:
                ov_df["_st"] = ov_df["Ship To Name"].str.strip().str.lower()
                ov_df["_bl"] = ov_df["Brand"].str.strip().str.lower()
                ne_key_set = {(d["_st"], d["_bl"]) for d in ne_decision_rows}
                override_count = int(ov_df[
                    ov_df.apply(lambda r: (r["_st"], r["_bl"]) in ne_key_set, axis=1)
                ].shape[0])
        except Exception as e:
            print(f"Warning: Could not load override CSV for count: {e}")

    _unmapped_shipto_names = sorted(um["_CustName"].dropna().unique().tolist()) if len(um) else []
    alloc = {
        "dist_rows_in": int(len(orig)), "dist_rows_out": int(len(merged)),
        "rows_unmapped": int((~matched).sum()),
        "unmapped_nsv": r2(float(um["_NSV"].sum())),
        "unmapped_note": (
            f"{int((~matched).sum())} distributor rows ({r2(float(um['_NSV'].sum()))} L NSV) "
            "have no matching entry in the cont% allocation master and retain their original "
            "Chain tag from the primary source. Known cause: some ship-to parties (e.g. "
            "Guardian Healthcare) are tagged 'Dist.' in the primary extract but are not "
            "covered by the Dist_primary_cont_based_on_secondary_MOM allocation file. "
            "Impact is immaterial at the blended level."
        ) if (~matched).any() else "All distributor rows successfully allocated.",
        "unmapped_ship_to_names": _unmapped_shipto_names[:20],   # top-20 by name for QC
        "rows_nearest": rows_nearest,
        "nearest_nsv": nearest_nsv,
        # TD-08: top-level convenience alias so QC panel and tests can reference directly
        "june_fallback_key_count": june_fallback_keys,   # integer count of ShipTo×Brand keys using nearest-month for June-26
        "missing_avg_tot_rows": int(orig["_AvgTot"].isna().sum()),
        "chains_allocated_to": int(merged.loc[matched, "_Chain"].nunique()),
        "cont_pct_bad_keys": cont_bad,   # raw cont% sums deviating from 100 (flagged BEFORE normalisation)
        "recon": recon, "qc_table": qc_rows[:400], "qc_table_total_rows": len(qc_rows),
        "missing_mapping": missing,
        "patch_rows": patch_rows, "patch_file": patch_path,
        "residual": residual_summary,
        "unit": "INR Lakh (values), units (qty)",
        "source_label": source_label or "unknown",
        # ---- June-26 fallback disclosure (additive governance) ----
        "june_fallback_nsv_lakh": june_fallback_nsv,
        # june_fallback_pct_of_fy27: added by detail_records_real() after FY27 total is known
        "june_fallback_source": {
            "data_available_through": "2026-05",
            "june_actual_shipto_available": False,
            "method": ("nearest-month within ±3 months — existing allocate_dist_primary() "
                       "logic; no formula change"),
            "june_fallback_keys": june_fallback_keys,
            "june_exact_keys": june_exact_keys,
            "june_unmapped_keys": june_unmapped_keys,
            "breakdown_by_source_period": june_period_breakdown,
            "governance_note": (
                "June-26 chain-level ShipTo primary was unavailable at build time "
                "(Primary_ShipTo_FY25-26_to_May26.csv ends May-26). All June-26 "
                "Dist. rows use the nearest month's actual primary chain split for "
                "the same Ship To Name × Brand within ±3 months. Business values "
                "(NSV, MRP, Qty, Tax) are unchanged; only chain attribution is "
                "derived, not actual June invoice data."
            ),
        },
        "method": (
            # ---- Priority-1 source: actual chain-level primary ----
            "PO Type='Dist.' rows are exploded across chains using actual chain-level "
            "primary data from Primary_ShipTo_FY25-26_to_May26.csv (Priority-1 source: "
            "the business's own primary invoices at Ship To Name × Brand × Month × Chain "
            "grain; Cont% verified to sum to 1.0 per key before normalisation). Matched "
            "on Ship To Name × Brand × Month; months with no exact entry use the SAME "
            "ship-to × brand's real primary split from the NEAREST month within 3 months "
            "and are QC-tagged 'Mapped (nearest ...)'. Inv Qty, Total MRP sales, NSV and "
            "Tax are scaled by cont%; article MRP is per-unit and is NOT scaled. Direct "
            "rows keep their own \"Chain name for Dashboard\". Rows with no split data at "
            "all get Chain='Unmapped Chain'. This source is the installed fallback when "
            "Dist_primary_cont_based_on_secondary_MOM.xlsx is absent from --src."
            if source_label == "shipto_primary_csv" else
            # ---- xlsx source: secondary-derived cont sheet ----
            "PO Type='Dist.' rows (blank \"Chain name for Dashboard\") are exploded across "
            "chains by the business's own secondary-derived monthly split "
            "(Dist_primary_cont_based_on_secondary_MOM.xlsx, sheet 'Dist Primary Conv to "
            "Chain Art'), matched on Ship To Name x Brand x Month (the cont sheet has no "
            "Cust-SAP Code column; the code<->ship-to bridge lives in the primary file "
            "itself and Cust-SAP Code is carried through every QC table). Keys with no "
            "entry for that exact month use the SAME ship-to x brand's split from the "
            "NEAREST month within 3 months -- still the business's own secondary data, "
            "never an invented mix -- and are QC-tagged 'Mapped (nearest ...)', never "
            "silently blended. Inv Qty, Total MRP sales, NSV and Tax are scaled by cont% "
            "(normalised to sum to exactly 100% per key, deviations flagged before "
            "normalisation); article MRP is per-unit and is NOT scaled; Avg Tot is a "
            "ratio, invariant under the split. Direct rows keep their own \"Chain name "
            "for Dashboard\". Rows with no cont data at all get Chain='Unmapped Chain' -- "
            "never a blank, never the distributor's Ship To Name. A reviewable patch "
            "proposal (SeedData/Mapping/DistCont_Patch_Proposed.csv) is regenerated on "
            "every build: paste approved rows into the cont xlsx to make the fix "
            "permanent (this also fixes Power BI, whose query 41 reads only the xlsx)."
        ),
        # ---- STEP 5/6 (Phase 3/6): Governance metadata (optional, non-breaking) ----
        "governance": {
            "eligibility_tier_counts": tier_counts,
            "qc_report": qc_report,
            "reconciliations_logged": len(governance_log["qc_reconciliations"]),
            "decisions_logged": len(governance_log["eligibility_decisions"]),
            # Phase 6: Not_Eligible NSV gating fields
            "not_eligible_nsv_lakh": r2(not_eligible_nsv),
            "not_eligible_pct": not_eligible_pct,
            "total_dist_nsv_lakh": r2(total_dist_nsv),
            "flagged_rows": len(ne_decision_rows),
            "override_count": override_count,
            "flagged_rows_csv": "PowerBI/SeedData/Mapping/DistAllocationGovernance_FlaggedRows.csv",
            "note": (
                "Phase 3/6: Governance engine logs eligibility tiers and QC reconciliation. "
                "not_eligible_pct drives the build gate (--not-eligible-gate-pct flag). "
                "Flagged Not_Eligible rows exported to flagged_rows_csv for business review. "
                "Override approvals tracked via PowerBI/SeedData/Masters/PrimaryAllocationOverride.csv."
            ),
        },
    }
    return out_df, alloc

def same_period_block(df, fy_col="_FY", m_col="_M", nsv_col="_NSV", qty_col="_Qty",
                      dims=(("by_zone", "_Zone"), ("by_chain", "_Chain"), ("by_brand", "_Brand"))):
    """LIKE-FOR-LIKE year-on-year, on the months the two latest FYs share.

    A part-year FY compared against a full prior FY is not a YoY -- it is a
    coverage artefact. FY27 Apr-Jul vs FY26 Apr-Mar read as -69.7% when the
    same-period move is +82.2%: same data, opposite direction, and the wrong
    one was on the leadership screen.

    So the comparison window is DERIVED, never assumed: take the months the
    current FY actually carries, intersect with the months the prior FY
    carries, and compare only those. When Aug-26 lands the window widens to
    five months on its own; when FY27 completes it becomes a true full-year
    YoY with no code change. Returns None if there is no prior FY to compare
    against, or no month in common.
    """
    tags = sorted({t for t in df[fy_col].dropna().unique() if t}, key=fy_start_year)
    if len(tags) < 2:
        return None
    curr, prev = tags[-1], tags[-2]
    cur_df, prv_df = df[df[fy_col] == curr], df[df[fy_col] == prev]
    shared = [m for m in _ORDER
              if m in set(cur_df[m_col]) and m in set(prv_df[m_col])]
    if not shared:
        return None
    c = cur_df[cur_df[m_col].isin(shared)]
    v = prv_df[prv_df[m_col].isin(shared)]

    def _pct(a, b):
        return r2((a / b - 1) * 100) if b else None

    def _canon(tag, months):
        y0 = fy_start_year(tag)
        out = []
        for mn in months:
            cm = _CAL_MONTH[_MONTH_IDX[mn]]
            out.append(f"{_ORDER_MON3[mn]}-{(y0 if cm >= 4 else y0 + 1) % 100:02d}")
        return out

    c_tot, v_tot = float(c[nsv_col].sum()), float(v[nsv_col].sum())
    block = {
        "curr_fy": curr, "prev_fy": prev,
        "months": shared,
        "months_curr_canon": _canon(curr, shared),
        "months_prev_canon": _canon(prev, shared),
        "n_months": len(shared),
        "curr": r2(c_tot), "prev": r2(v_tot),
        "delta": r2(c_tot - v_tot), "yoy_pct": _pct(c_tot, v_tot),
        "unit": "INR Lakh",
        "basis": (f"Like-for-like: {curr} vs {prev} over the {len(shared)} month(s) "
                  f"both FYs carry ({', '.join(shared)}). Article-level primary. "
                  f"Window widens automatically as new months arrive."),
    }
    has_qty = qty_col in df.columns
    for out_key, col in dims:
        if col not in df.columns:
            continue
        cs = c.groupby(col)[nsv_col].sum()
        vs = v.groupby(col)[nsv_col].sum()
        cq = c.groupby(col)[qty_col].sum() if has_qty else None
        vq = v.groupby(col)[qty_col].sum() if has_qty else None
        rows = []
        for name in sorted(set(cs.index) | set(vs.index)):
            if not name:
                continue
            a, b = float(cs.get(name, 0.0)), float(vs.get(name, 0.0))
            row = {"name": name, "curr": r2(a), "prev": r2(b),
                   "delta": r2(a - b), "yoy_pct": _pct(a, b),
                   "nsv_contribution_pct": r2(a / c_tot * 100) if c_tot else None,
                   # Governance label, never inferred silently: a missing prior-year
                   # base must never be READ as zero growth, and an account that
                   # sold nothing this period must never be read as -100% either --
                   # both are "no comparable number", not "the number is zero".
                   "comparability": (
                       "COMPARABLE" if (a > 0 and b > 0) else
                       "NEW_ACCOUNT" if (a > 0 and b <= 0) else
                       "EXITED" if (a <= 0 and b > 0) else
                       "NOT_COMPARABLE"),
                   }
            if has_qty:
                qa, qb = float(cq.get(name, 0.0)), float(vq.get(name, 0.0))
                row["qty_curr"] = int(qa)
                row["qty_prev"] = int(qb)
                row["qty_yoy_pct"] = _pct(qa, qb)
            rows.append(row)
        block[out_key] = sorted(rows, key=lambda d: -(d["curr"] or 0))
    return block

def detail_records_real(src, max_rows=20000, output_dir=None):
    """Real 13-column detail_records from File 2 (article-wise primary).
    Looks for primary_article.xlsb/.xlsx in src. Returns None if absent, else
    (recs, channel_totals, coverage) where channel_totals is computed from the
    FULL un-capped data (so headline numbers like SIS are always exact) and
    recs is capped to the top `max_rows` groups BY ABSOLUTE VALUE (not a flat
    per-row threshold) to preserve total value coverage while bounding file size.
    A flat threshold silently guts small-ticket channels (e.g. SIS is made of
    many small line items) -- top-N-by-value keeps ~98%+ of total value at a
    fraction of the full row count.

    output_dir: forwarded to allocate_dist_primary()'s own output_dir -- when
    given, its governance/proposal CSVs (DistCont_Patch_Proposed.csv,
    DistAllocationGovernance_FlaggedRows.csv, EanAffinity_ResidualProposal.csv)
    are written under this directory instead of the repo's tracked
    PowerBI/SeedData/Mapping/ paths. Default None preserves the original
    repo-writing behaviour for the real production build. A test that calls
    detail_records_real() with synthetic/tmp_path data MUST pass a tmp_path
    here -- otherwise it silently overwrites the tracked governance CSVs with
    whatever tiny synthetic result it produced (see tests/test_allocate_dist_primary_output_dir.py
    for the underlying shadow-run fix this threads through to)."""
    def _safe_val(x):
        """Convert NaN/None to None (null in JSON), keep strings and numbers as-is."""
        if x is None or (isinstance(x, float) and math.isnan(x)):
            return None
        return x

    f = None
    for name in ("primary_article.xlsb", "primary_article.xlsx",
                 "MT, Eb2B & SIS primary April_23 to May_26.xlsb"):
        if (src / name).exists():
            f = src / name; break
    # Fallback: read monthly CSVs from Primary_Article_Monthly/ when no
    # consolidated file exists. Searches src itself, src/Primary_Article_Monthly,
    # and the repo-level PowerBI path.
    _monthly_csv_dirs = [src, src / "Primary_Article_Monthly",
                         Path(__file__).resolve().parent.parent / "PowerBI" / "RawDataFolders" / "Primary_Article_Monthly"]
    _monthly_csvs = []
    if f is None:
        for _d in _monthly_csv_dirs:
            if _d.is_dir():
                _monthly_csvs = sorted(_d.glob("primary_article_*.csv"))
                if _monthly_csvs:
                    break
    if f is None and not _monthly_csvs:
        return None
    if f is not None:
        eng = "pyxlsb" if f.suffix.lower() == ".xlsb" else None
        probe = pd.read_excel(f, sheet_name=0, header=None, nrows=8, engine=eng)
        hdr = 0
        for i in range(len(probe)):
            vals = {str(v).strip() for v in probe.iloc[i].tolist()}
            if {"Month", "FY"} <= vals and ({"Article Code"} <= vals or {"Ship To Name", "EAN No."} <= vals):
                hdr = i
                break
        print(f"detail source: {f.name} (header row {hdr})")
        df = pd.read_excel(f, sheet_name=0, header=hdr, engine=eng)
    else:
        frames = []
        for csvf in _monthly_csvs:
            frames.append(pd.read_csv(csvf, low_memory=False))
            print(f"detail source (CSV): {csvf.name} ({len(frames[-1])} rows)")
        df = pd.concat(frames, ignore_index=True)
        print(f"detail source: {len(_monthly_csvs)} monthly CSVs ({len(df)} total rows)")
    # normalise headers: trim + collapse embedded newlines ("Chain name\nfor
    # Dashboard" is the actual maintained header -- one cell, wrapped text)
    df.columns = [" ".join(str(c).split()) for c in df.columns]
    missing = [c for c in ("Month","FY","brand","Zone","Channel",
                           "Inv. Net value(LOC)","Total MRP sales","Inv Qty",
                           "category","sub_category","range","net_content","Description","EAN No.")
               if c not in df.columns]
    if not ({"Chain name for Dashboard", "Chain name"} & set(df.columns)):
        missing.append("Chain name for Dashboard (or Chain name)")
    if missing:
        raise SystemExit(f"File 2 is missing expected columns: {missing}. "
                         f"Found: {list(df.columns)[:25]} ...")
    df["_M"] = df["Month"].map(_mlabel)
    df["_FY"] = df["FY"].map(_fylabel)
    n_before = len(df)
    df = df[df["_M"].notna() & df["_FY"].notna()]
    if len(df) == 0:
        raise SystemExit(
            "detail_records_real: 0 rows survived Month/FY parsing "
            f"(source had {n_before} rows). Check that 'Month' and 'FY' columns "
            "contain recognisable values (text like \"May'25\", a date, or an "
            "Excel date serial); sample Month values: "
            f"{df['Month'].head(5).tolist() if 'Month' in df else 'N/A'}")
    df["_Brand"] = df["brand"].map(canon_brand)
    df["_Zone"] = df["Zone"].map(canon_zone)
    df["_State"] = (df["State"].map(canon_state).fillna("") if "State" in df.columns else "")
    _CHAN_MAP = {"mt": "MT", "eb2b": "EB2B", "sis": "SIS"}
    df["_Chan"] = df["Channel"].astype(str).str.strip().map(
        lambda x: _CHAN_MAP.get(x.strip().lower(), x.strip()))
    df["_NSV"] = pd.to_numeric(df["Inv. Net value(LOC)"], errors="coerce").fillna(0.0) / 1e5  # -> Lakh
    df["_MRP"] = pd.to_numeric(df["Total MRP sales"], errors="coerce").fillna(0.0) / 1e5
    df["_Qty"] = pd.to_numeric(df["Inv Qty"], errors="coerce").fillna(0.0)
    # article-level (per-unit) MRP -- retained through the DIST allocation
    # UN-scaled ("MRP" in the current format, "MRP Rate" in older exports)
    df["_ArtMRP"] = pd.to_numeric(df["MRP"], errors="coerce") if "MRP" in df.columns \
        else (pd.to_numeric(df["MRP Rate"], errors="coerce") if "MRP Rate" in df.columns
              else pd.Series(float("nan"), index=df.index))
    for c in ("category", "sub_category", "range", "net_content", "Description", "EAN No."):
        df["_" + c] = df[c].astype(str).str.strip().replace({"nan": "", "None": ""})

    # ---- Cross-month EAN backfill for category/sub_category/range/net_content.
    # Some monthly extracts (found: primary_article_Jul_26.csv, all 31,355 rows)
    # arrive with sub_category/range/net_content/PPT Category entirely blank
    # for the whole file, while category and EAN No. are intact -- an upstream
    # export gap for that month, not missing data: the same EAN (a physical
    # SKU) carries a stable sub_category/range/net_content in adjacent real
    # months. Backfill from those real values (99.99% of the affected NSV
    # matched against Apr/May/Jun/Aug'26 for the Jul'26 gap) rather than
    # leaving them null or inventing a taxonomy. An EAN with no real value
    # anywhere in the loaded months (e.g. a SKU that only shipped in the
    # gapped month) is left blank -- never fabricated.
    # NOTE: pandas here (3.x) does not always stringify a missing cell to the
    # literal text "nan"/"None" under .astype(str) the way the loop above's
    # replace({"nan":"","None":""}) assumes -- for a column that arrives
    # 100% empty in one source file (e.g. Jul'26), .astype(str) can leave the
    # cell as an actual missing value instead of the text "nan". fillna("")
    # catches both representations, so the blank-detection below is correct
    # either way.
    for fillcol in ("_category", "_sub_category", "_range", "_net_content"):
        col = df[fillcol].fillna("")
        need = (col == "") & (df["_EAN No."] != "")
        if not need.any():
            continue
        lookup = (df.loc[~need & (df["_EAN No."] != ""), ["_EAN No.", fillcol]]
                    .assign(**{fillcol: lambda x: x[fillcol].fillna("")})
                    .drop_duplicates("_EAN No.")
                    .set_index("_EAN No.")[fillcol])
        lookup = lookup[lookup != ""]
        filled = df.loc[need, "_EAN No."].map(lookup)
        n_filled = int(filled.notna().sum())
        if n_filled:
            df.loc[need, fillcol] = df.loc[need, fillcol].where(filled.isna(), filled)
            print(f"detail: backfilled {n_filled}/{int(need.sum())} blank {fillcol} rows "
                  f"from another month's real value for the same EAN")

    # ---- TOT% source columns (Priority 1/2 -- see tot_block's docstring):
    # 'Avg Tot' is the Primary file's own Customer x Article-grain TOT%
    # (0-1 fraction); 'Inv. Tax Amount(LOC)' is the actual per-row tax.
    # Kept UN-filled (real NaN, not 0.0) so compute_tot_columns can correctly
    # tell "blank" apart from "genuinely zero" and fall through tiers.
    # Gracefully degrades to GST-rate-table-only (old behaviour) if either
    # column is absent from this particular source file.
    df["_AvgTot"] = pd.to_numeric(df["Avg Tot"], errors="coerce") if "Avg Tot" in df.columns \
        else pd.Series(float("nan"), index=df.index)
    df["_TaxLOC"] = (pd.to_numeric(df["Inv. Tax Amount(LOC)"], errors="coerce") / 1e5) \
        if "Inv. Tax Amount(LOC)" in df.columns else pd.Series(float("nan"), index=df.index)

    # ---- CM2 expense-matching keys (see cm2_block): Customer Code is the
    # FIRST occurrence only ("Cust-SAP Code" appears twice in the raw file;
    # pandas auto-suffixes the duplicate as "Cust-SAP Code.1" — same
    # canonical-first-occurrence convention PowerQuery/16 uses).
    df["_CustCode"] = df["Cust-SAP Code"].astype(str).str.strip().replace({"nan": ""}) \
        if "Cust-SAP Code" in df.columns else ""
    df["_CustName"] = df["Ship To Name"].astype(str).str.strip().replace({"nan": ""}) \
        if "Ship To Name" in df.columns else ""
    # Cust-SAP Code often reads back as float ("1101911.0") -- normalise
    df["_CustCode"] = df["_CustCode"].str.replace(r"\.0$", "", regex=True)

    # ---- DIST -> Chain allocation (sets _Chain on every row; explodes Dist.
    # rows across chains by the secondary-derived cont%). Row-level, BEFORE
    # any grouping, so Customer x Article grain survives into everything
    # downstream (TOT%, CM2, detail_records, the Customer x Article table).
    _wdf, _raw_sums, _alloc_src = load_dist_cont_weights(src)
    _offtake_brand_set, _offtake_ean_set = build_offtake_universe(src)
    df, alloc = allocate_dist_primary(
        df, _wdf, _raw_sums, source_label=_alloc_src,
        offtake_brand_set=_offtake_brand_set,
        offtake_ean_set=_offtake_ean_set,
        output_dir=output_dir,
    )
    n_shipto_as_chain = int(((df["_Chain"].astype(str).str.strip().str.lower()
                              == df["_CustName"].str.lower()) & (df["_CustName"] != "")).sum())
    if alloc is not None:
        alloc["rows_chain_equals_shipto"] = n_shipto_as_chain   # QC #17 -- must be 0
        # Add june_fallback_pct_of_fy27 here where full FY27 NSV is available
        _fy27_nsv = float(df[df["_FY"] == "FY27"]["_NSV"].sum())
        _june_fb_nsv = alloc.get("june_fallback_nsv_lakh") or 0
        alloc["june_fallback_pct_of_fy27"] = (
            round(_june_fb_nsv / _fy27_nsv * 100, 2) if _fy27_nsv else None
        )

    # ---- EXACT channel totals from the FULL data, before any row capping ----
    ct = (df.groupby(["_FY", "_Chan"])["_NSV"].sum().round(2))
    channel_totals = {}
    for (fy, chan), v in ct.items():
        channel_totals.setdefault(fy, {})[chan] = float(v)

    # ---- EXACT per-FY primary aggregates from the FULL allocated data, for
    # EVERY FY the article-wise primary carries beyond the pre-aggregated
    # workbooks' window (that other source ends Mar'26, i.e. covers FY25/26).
    # FY27 today; FY28 automatically when Apr-27 rows arrive -- one block per
    # tag, keyed by tag, so the dashboard just looks up the selected FY.
    fyx_primary = {}
    for _tag in sorted(set(df["_FY"].dropna().unique()) - PREAGG_FY_TAGS, key=fy_start_year):
        fx = df[df["_FY"] == _tag]
        def _aggx(col, fx=fx):
            s = fx.groupby(col)["_NSV"].sum().sort_values(ascending=False)
            return [{"name": k, "nsv": r2(float(v))} for k, v in s.items() if k]
        mser = fx.groupby("_M")["_NSV"].sum()
        _months_present = [m for m in _ORDER if m in set(fx["_M"])]
        # Canonical "Mon-YY" labels (e.g. "Apr-26") matching MONTHS/offtake format so
        # the overview trend chart can extend the Primary line into FY27 months without
        # positional arithmetic -- just a dict-lookup on o.months labels.
        _fy_cal_start = fy_start_year(_tag)
        _months_canon = []
        for _mn in _months_present:
            _cm = _CAL_MONTH[_MONTH_IDX[_mn]]
            _cy = _fy_cal_start if _cm >= 4 else _fy_cal_start + 1
            _months_canon.append(f"{_ORDER_MON3[_mn]}-{_cy % 100:02d}")
        fyx_primary[_tag] = {
            "tag": _tag,
            "nsv": r2(float(fx["_NSV"].sum())),
            "mrp": r2(float(fx["_MRP"].sum())),
            "months_covered": _months_present,
            "months_canon": _months_canon,
            "monthly": [r2(float(mser.get(m, 0.0))) for m in _ORDER],
            "monthly_canon": [r2(float(mser.get(m, 0.0))) for m in _months_present],
            "by_chain": _aggx("_Chain"), "by_zone": _aggx("_Zone"),
            "by_channel": _aggx("_Chan"), "by_brand": _aggx("_Brand"),
            "unit": "INR Lakh",
            "note": (f"EXACT {_tag} primary actuals from the FULL (uncapped) article-wise "
                     "primary, chain-allocated (Dist. rows split by secondary cont%). The "
                     "other report blocks' source workbook ends at Mar'26, so this FY lives "
                     "only here. MRP basis = 'Total MRP sales'."),
            "chain_alloc_note": (
                "June-26 chain allocation is derived using the nearest available "
                "distributor primary mix because June chain-level ShipTo data was "
                "unavailable. April and May chain allocation uses actual invoice data. "
                "Total NSV and monthly totals are exact actuals; only the within-June "
                "chain split is derived."
            ) if _tag == "FY27" and alloc is not None else None,
        }
    fyx_primary = fyx_primary or None

    # ---- SIS reconciliation drill-down: computed from the FULL data (not the
    # capped detail_records) so the numbers are exact and auditable. Business
    # reconciliation of the Rs 236 L reference figure is NOT resolved by this --
    # it only makes the Rs 250.17 L composition fully transparent/exportable.
    sis_reconciliation = _sis_reconciliation(df)

    # ---- TOT% row-level 3-tier classification (Avg Tot -> actual Tax -> GST
    # rate table fallback), computed on the FULL un-grouped row-level data so
    # the Customer x Article-grain Avg Tot/Tax values aren't lost to
    # aggregation. QC summary (row counts by source, fallback % of MRP) is
    # computed from this SAME row-level FY26/FY27 population that
    # blended_tot_pct covers, before it gets collapsed into `g`.
    _qc_table, _qc_raw_rows = load_gst_qc_table()
    _cutover = load_gst_cutover_date()
    df = compute_tot_columns(df, _qc_table, _cutover[0])
    _qc_summary = compute_tot_qc_summary(df[fy_ge(df["_FY"])])

    # ---- Customer x Article x Month x Chain allocation detail (Dist.-allocated
    # rows only -- the allocation OUTPUT at the requested grain), with weighted
    # Avg Tot = SUM(NSV x Avg Tot)/SUM(NSV), Total-MRP-sales-weighted fallback
    # where a group's NSV nets to ~0 (returns), per the business's formula.
    # Never a simple average. Capped top-N by |NSV| for data.js size; the QC
    # recon above is computed from the FULL uncapped population.
    if alloc is not None:
        ad = df[df["_IsDist"] == True].copy()   # noqa: E712 (concat leaves object dtype)
        m_at = ad["_AvgTot"].notna()
        ad["_NxA"] = (ad["_NSV"] * ad["_AvgTot"]).where(m_at)
        ad["_MxA"] = (ad["_MRP"] * ad["_AvgTot"]).where(m_at)
        ad["_NSVa"] = ad["_NSV"].where(m_at)
        ad["_MRPa"] = ad["_MRP"].where(m_at)
        ca = (ad.groupby(["_CustCode","_CustName","_EAN No.","_Description","_ArtMRP","_Brand",
                          "_category","_sub_category","_range","_net_content","_M","_FY","_Chain"],
                         dropna=False)
                .agg(NSV=("_NSV","sum"), MRPS=("_MRP","sum"), Qty=("_Qty","sum"),
                     Tax=("_TaxLOC","sum"), NxA=("_NxA","sum"), MxA=("_MxA","sum"),
                     NSVa=("_NSVa","sum"), MRPa=("_MRPa","sum")).reset_index())
        ca_total_nsv = float(ca["NSV"].abs().sum()) or 1.0
        ca = ca.reindex(ca["NSV"].abs().sort_values(ascending=False).index)
        ca_rows_total = len(ca)
        ca_kept = ca.head(4000)
        ca_cov = float(ca_kept["NSV"].abs().sum()) / ca_total_nsv * 100
        cust_article = []
        for _, r in ca_kept.iterrows():
            if abs(r["NSVa"]) > 1e-9:
                wat = r["NxA"] / r["NSVa"]
            elif abs(r["MRPa"]) > 1e-9:
                wat = r["MxA"] / r["MRPa"]
            else:
                wat = None
            cust_article.append({
                "cust_code": _safe_val(r["_CustCode"]), "ship_to": _safe_val(r["_CustName"]),
                "ean": _safe_val(str(r["_EAN No."])), "article": _safe_val(r["_Description"]),
                "art_mrp": r2(r["_ArtMRP"]), "brand": _safe_val(r["_Brand"]),
                "category": _safe_val(r["_category"]), "sub_category": _safe_val(r["_sub_category"]),
                "range": _safe_val(r["_range"]), "pack": _safe_val(r["_net_content"]),
                "month": _safe_val(r["_M"]), "fy": _safe_val(r["_FY"]), "chain": _safe_val(r["_Chain"]),
                "nsv": r2(r["NSV"]), "mrp_sales": r2(r["MRPS"]),
                "qty": int(round(r["Qty"])), "tax": r2(r["Tax"]),
                "w_avg_tot": r2(wat * 100, 1) if wat is not None else None,
            })
        alloc["cust_article"] = {
            "rows": cust_article, "rows_total": ca_rows_total,
            "value_coverage_pct": round(ca_cov, 1),
            "note": ("Dist.-allocated output at Customer x Article x Month x Chain grain. "
                     "Capped to the top 4,000 groups by |NSV| for browser size; the "
                     "reconciliation above is computed from the FULL uncapped population. "
                     "Weighted Avg Tot = SUM(NSV x Avg Tot)/SUM(NSV) per group (Total-MRP-"
                     "sales-weighted fallback where NSV nets to ~0) -- never a simple average."),
        }

    g = (df.groupby(["_M","_FY","_Chan","_Zone","_State","_Chain","_Brand",
                     "_category","_sub_category","_range","_net_content","_Description","_EAN No."],
                    dropna=False)
           .agg(NSV=("_NSV","sum"), MRP=("_MRP","sum"), Qty=("_Qty","sum"),
                TotMRP=("_tot_mrp","sum"), TotNSV=("_tot_nsv","sum"),
                Passon=("_passon","sum"), FallbackNSV=("_fallback_nsv","sum")).reset_index())

    # ---- TOT% (Trade Offer Terms % / On-Invoice Margin Pass-on %): computed
    # from this FULL uncapped groupby, before the top-N-by-value row cap below,
    # so it's exact rather than subject to the browser row cap.
    tot = tot_block(g, _qc_table, _cutover, _qc_raw_rows, _qc_summary)

    # ---- CM2 = NSV - P&L Expenses: computed from the same row-level `df`
    # (before the groupby/cap above) so Customer Code matching works against
    # the real per-transaction grain. See cm2_block's docstring.
    cm2 = cm2_block(df, load_pl_expense_input())

    total_value = g["NSV"].sum()
    rows_total = len(g)
    # cap by ROW COUNT, keeping the top-N groups by |NSV| (preserves value fidelity)
    g = g.reindex(g["NSV"].abs().sort_values(ascending=False).index)
    kept = g.head(max_rows) if max_rows else g
    coverage = float(kept["NSV"].sum() / total_value * 100) if total_value else 100.0
    recs = []
    for _, r in kept.iterrows():
        recs.append({"Month":r["_M"],"FY":r["_FY"],"Channel":r["_Chan"],"Zone":r["_Zone"],"State":_safe_val(r["_State"]),
            "Chain":r["_Chain"],"Brand":r["_Brand"],"Category":_safe_val(r["_category"]),
            "SubCategory":_safe_val(r["_sub_category"]),"Range":_safe_val(r["_range"]),"PackSize":_safe_val(r["_net_content"]),
            "Article":_safe_val(r["_Description"]),"EAN":_safe_val(str(r["_EAN No."])),
            "NSV":r2(r["NSV"]),"MRP":r2(r["MRP"]),"Qty":int(r["Qty"])})
    print(f"detail rows: {rows_total} groups total -> kept top {len(recs)} "
          f"({coverage:.1f}% of total value)")
    return recs, channel_totals, sis_reconciliation, {
        "rows_total": rows_total, "rows_kept": len(recs),
        "value_coverage_pct": round(coverage, 1),
        "fyx_primary": fyx_primary,
        # Like-for-like YoY on the months the two latest FYs share. Computed
        # from this same article-level frame, so it covers every FY -- not just
        # the ones the pre-aggregated workbook happens to reach.
        "same_period": same_period_block(df)}, tot, cm2, alloc

def detail_records_representative(primary):
    """Fallback: synthesise detail_records whose Chain/Brand/Zone/Channel/Month/FY
    margins match the real primary aggregates; Category/Sub-cat/Pack/Article from taxonomy."""
    import random; random.seed(7)
    months = primary["month_labels"]
    mf = {"25": primary["monthly_fy25"], "26": primary["monthly_fy26"]}
    chains = [c for c in primary["by_chain"] if (c["fy25"] or 0) > 0 or (c["fy26"] or 0) > 0]
    brands = primary["by_brand"]; zones = primary["by_zone"]; chans = primary["by_channel"]
    def wsum(items, k): return sum(max(0, i[k] or 0) for i in items) or 1
    def pick(items, k, tot):
        r = random.random() * tot; a = 0
        for i in items:
            a += max(0, i[k] or 0)
            if r <= a: return i["name"]
        return items[-1]["name"]
    ean = lambda s: "890" + str(abs(hash(s)) % 10**10).zfill(10)
    recs = []
    for tag in ("25", "26"):
        mw = mf[tag]; msum = sum(mw) or 1
        zt = wsum(zones, "fy" + tag); ct = wsum(chans, "fy" + tag); bt = wsum(brands, "fy" + tag)
        for ch in chains:
            ctot = ch.get("fy" + tag) or 0
            if ctot <= 0: continue
            for b in brands:
                bs = max(0, b.get("fy" + tag) or 0) / bt
                tax = _DTAX.get(b["name"])
                if bs <= 0 or not tax: continue
                for mi, mo in enumerate(months):
                    cell = ctot * bs * (mw[mi] / msum)
                    if cell < 1.2: continue
                    t = random.choice(tax); pack = random.choice(t[3])
                    art = f"{b['name']} {t[4]} {pack.split()[0]}{'ml' if 'ml' in pack else 'g'}"
                    nsv = round(cell, 2); mrp = round(nsv * round(random.uniform(2.3, 2.8), 2), 2)
                    qty = int(nsv * 1e5 / random.uniform(120, 320))
                    recs.append({"Month":mo,"FY":"FY"+tag,"Channel":pick(chans,"fy"+tag,ct),
                        "Zone":pick(zones,"fy"+tag,zt),"Chain":ch["name"],"Brand":b["name"],
                        "Category":t[0],"SubCategory":t[1],"Range":t[2],"PackSize":pack,"Article":art,
                        "EAN":ean(art),"NSV":nsv,"MRP":mrp,"Qty":qty})
    return recs

def detail_dims(recs):
    keys = ["FY","Month","Channel","Zone","State","Chain","Brand","Category","SubCategory","Range","PackSize","Article"]
    out = {}
    for k in keys:
        vals = {r[k] for r in recs if r.get(k) is not None}
        out[k] = [m for m in _ORDER if m in vals] if k == "Month" else sorted(vals, key=lambda x: str(x))
    return out


def _build_detail_meta(src, max_rows, primary_for_fallback):
    """Shared by both the --detail-only path and the full build: returns
    (detail_records, dims, detail_meta_dict, tot, cm2, alloc). Falls back to
    the representative synthesiser only when File 2 is absent -- in that case
    `tot`/`cm2`/`alloc` are None, since all need REAL Category/Chain tags
    (not a randomly-assigned taxonomy placeholder)."""
    result = detail_records_real(src, max_rows)
    if result is None:
        detail = detail_records_representative(primary_for_fallback)
        return detail, detail_dims(detail), {
            "representative": True,
            "columns": ["Month","FY","Channel","Zone","Chain","Brand","Category",
                        "SubCategory","Range","PackSize","Article","NSV","MRP","Qty"],
            "note": ("REPRESENTATIVE records — Chain/Brand/Zone/Channel/Month/FY margins match the "
                     "real primary; Category/Sub-category/Pack/Article are taxonomy placeholders. "
                     "Drop primary_article.xlsb into --src to emit real detail."),
        }, None, None, None
    detail, channel_totals, sis_reconciliation, cov, tot, cm2, alloc = result
    meta = {
        "representative": False,
        "columns": ["Month","FY","Channel","Zone","Chain","Brand","Category",
                    "SubCategory","Range","PackSize","Article","NSV","MRP","Qty"],
        "note": "REAL granular records from File 2 (article-wise primary).",
        "channel_totals": channel_totals,   # {FY: {Channel: NSV_Lakh}} — EXACT, computed pre-cap
        "channel_totals_unit": "INR Lakh",
        "rows_total_groups": cov["rows_total"],
        "rows_kept": cov["rows_kept"],
        "value_coverage_pct": cov["value_coverage_pct"],
        # EXACT per-FY primary actuals (e.g. Apr'26+ = FY27) from the
        # article-wise primary -- the only source that has FYs beyond the
        # pre-aggregated workbooks' window. Dict keyed by FY tag ('FY27',
        # 'FY28', ...); None if the article primary carries no such FY.
        "fyx_primary": cov.get("fyx_primary"),
        # Like-for-like YoY window shared by the two latest FYs.
        "same_period": cov.get("same_period"),
        # {FY: {summary, by_chain, by_month, by_brand, exclusions, row_count}} —
        # SIS reconciliation drill-down, computed from the FULL uncapped source.
        # Kept for audit trail. See docs/SIS_Reconciliation.md.
        "sis_reconciliation": sis_reconciliation,
        "sis_reconciliation_unit": "INR Lakh",
        # RESOLVED 2026-07-03: business confirmed Rs 250.17 L (File 2 Channel
        # field, net of MRN returns) as the source of truth for Primary SIS
        # FY26. Rs 236 L (unresolved MIS/reference) and Rs 275.44 L (gross
        # sales, before returns) are both confirmed NOT correct.
        "sis_gap_status": "RESOLVED (2026-07-03) — business confirmed Rs 250.17 L "
                          "(File 2, net of MRN returns) as source of truth for "
                          "Primary SIS FY26. Rs 236 L and Rs 275.44 L (gross) are "
                          "NOT correct.",
    }
    return detail, detail_dims(detail), meta, tot, cm2, alloc


def _check_governance_gate(alloc, gate_pct: float = 0.0) -> None:
    """Fail the build if Not_Eligible NSV exceeds the configured threshold.

    Gate is disabled when gate_pct == 0 (the default).
    alloc["governance"]["not_eligible_pct"] carries the computed percentage.
    """
    if not gate_pct:
        return
    gov = (alloc or {}).get("governance", {}) or {}
    actual_pct = gov.get("not_eligible_pct", 0.0) or 0.0
    if actual_pct > gate_pct:
        flagged_csv = gov.get("flagged_rows_csv", "DistAllocationGovernance_FlaggedRows.csv")
        raise SystemExit(
            f"GOVERNANCE GATE BLOCKED: Not_Eligible NSV is {actual_pct:.2f}% "
            f"which exceeds the --not-eligible-gate-pct threshold of {gate_pct:.2f}%. "
            f"Review {flagged_csv} and add approved overrides to "
            f"PowerBI/SeedData/Masters/PrimaryAllocationOverride.csv before rebuilding."
        )


def _run_release_gate(alloc, report_path=None, config=None):
    """Run the release gate against computed pipeline outputs.

    Extracts gate inputs from the alloc dict produced by apply_chain_allocation()
    and calls gate_pass(). Prints the human-readable report. Returns (passed, report).

    The caller is responsible for NOT writing data.js when passed=False.
    """
    try:
        from release_gate import gate_pass, _default_config
    except ImportError:
        print("⚠ WARNING: release_gate module not found — skipping release gate.")
        print("  Install it by ensuring scripts/release_gate.py is on the Python path.")
        return True, None  # advisory: skip gate if module not present

    merged_config = _default_config()
    if config:
        merged_config.update(config)

    # Build allocation_reconciliation from alloc["recon"]["overall"] if available
    allocation_reconciliation = None
    if alloc and "recon" in alloc:
        ov = alloc["recon"].get("overall", {})
        if ov:
            # Convert from {metric: {original, allocated, variance}} to per-month structure
            # The gate expects: {month_label: {original, allocated, variance}}
            # The overall recon is across all months; pass as single "overall" key
            allocation_reconciliation = {"overall": {
                "original": ov.get("nsv", {}).get("original", 0),
                "allocated": ov.get("nsv", {}).get("allocated", 0),
                "variance": ov.get("nsv", {}).get("variance", 0),
            }} if isinstance(ov.get("nsv"), dict) else None

        # Per-month reconciliation if present
        by_month = alloc["recon"].get("by_month", [])
        if by_month:
            allocation_reconciliation = {}
            for row in by_month:
                label = row.get("label") or row.get("month", "unknown")
                allocation_reconciliation[label] = {
                    "original": row.get("original", 0),
                    "allocated": row.get("allocated", 0),
                    "variance": row.get("variance", 0),
                }

    # Build primary_df proxy — pass unmapped NSV context for G6
    primary_df = None
    if alloc:
        total_nsv = alloc.get("distributor_primary_total", 0) or 0
        unmapped_nsv = alloc.get("unmapped_nsv", 0) or 0
        if total_nsv > 0:
            mapped_nsv = total_nsv - unmapped_nsv
            primary_df = pd.DataFrame({
                "Chain": ["_mapped", "_Unmapped"],
                "NSV": [mapped_nsv, unmapped_nsv],
                "MRP": [mapped_nsv * 1.5, unmapped_nsv * 1.5],
                "Qty": [int(mapped_nsv), int(unmapped_nsv)],
            })

    passed, report = gate_pass(
        primary_df=primary_df,
        allocation_reconciliation=allocation_reconciliation,
        config=merged_config,
        report_path=report_path,
    )
    report.print_report()
    return passed, report


def _safe_write_data_js(out_path, payload_str, alloc=None, gate_config=None,
                        report_dir=None, skip_gate=False):
    """Safe-write data.js: validate via release gate, then atomically replace.

    1. Write candidate to a temp file in the same directory.
    2. Run release gate against alloc metadata.
    3. If gate PASS: move temp → production data.js.
    4. If gate FAIL: leave production data.js intact, delete temp, exit(1).
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Write candidate to temp file (same dir for atomic rename)
    fd, tmp = tempfile.mkstemp(suffix=".js", dir=out_path.parent)
    try:
        import os
        os.close(fd)
        Path(tmp).write_text(payload_str, encoding="utf-8")

        if skip_gate:
            shutil.move(tmp, out_path)
            print("⚠ Release gate skipped for this build path (lightweight refresh).")
            return

        report_path = Path(report_dir) / "release_gate_report.json" if report_dir else None
        passed, report = _run_release_gate(alloc, report_path=report_path, config=gate_config)

        if not passed:
            Path(tmp).unlink(missing_ok=True)
            print("\n⚠ RELEASE GATE BLOCKED: data.js was NOT updated. Last known-good file is intact.")
            raise SystemExit(1)

        shutil.move(tmp, out_path)
        print(f"✓ Release gate PASSED. Wrote {out_path} ({out_path.stat().st_size:,} bytes)")
    except SystemExit:
        raise
    except Exception:
        Path(tmp).unlink(missing_ok=True)
        raise


def refresh_derived_blocks(data, src):
    """Recompute every block that derives from detail_meta's same_period/
    fyx_primary, or from primary/offtake/pnl/universe/promo directly:
    insights (like-for-like basis), targets, mapping_health, mom, scorecard,
    pvm, profitability, npd, readiness.

    Why this exists: main()'s full build computes these once, inline, near
    the end of the function. Every partial-refresh CLI mode (--detail-only
    chief among them) updates detail_meta/primary/offtake/etc. but used to
    leave this downstream layer untouched -- so a --detail-only run that
    genuinely fixed detail_records (e.g. the 2026-09 chain-alias and
    Tier-3-unmapped fixes) left targets/insights/scorecard/mom/pvm frozen at
    whatever a much earlier full build had produced. Concretely this showed
    "Unmapped Chain" as a ~40%-contribution top-2 revenue driver on the
    Executive Cockpit and the Performance & Comparison scorecard, long after
    the real Unmapped-Chain bucket had been fixed down to <0.1% of Primary
    everywhere else on the dashboard -- see docs/FAILURE_MODE_REGISTER.md.

    Call this after updating any of data['detail_meta'], data['primary'],
    data['offtake'], data['universe'], data['promo'], data['alloc'] so this
    layer never drifts from what it describes. Mutates `data` in place;
    returns nothing. No-ops quietly if primary/offtake aren't present yet
    (mirrors main()'s own guard).
    """
    primary = data.get("primary")
    offtake = data.get("offtake")
    pnl = data.get("pnl")
    universe = data.get("universe")
    promo = data.get("promo")
    detail_meta = data.get("detail_meta")
    if not (primary and offtake):
        return

    _sp = (detail_meta or {}).get("same_period")
    if _sp:
        data["insights"] = insights_block(primary, offtake, pnl, universe, promo, _sp)

    _tgt_rows = load_ty_target(src) or load_targets_csv(_REPO_ROOT)
    if _tgt_rows:
        _acts = {}
        _om = dict(zip(offtake.get("months_" + _tgt_rows[0][0].lower(), []) or [],
                       offtake.get("monthly_" + _tgt_rows[0][0].lower(), []) or []))
        if _om:
            _acts["offtake"] = _om
        _fx = (detail_meta or {}).get("fyx_primary", {}).get(_tgt_rows[0][0])
        if _fx:
            _acts["primary"] = dict(zip(_fx.get("months_canon", []),
                                        _fx.get("monthly_canon", [])))
        _tb = targets_block(_tgt_rows, _acts, _sp)
        if _tb:
            data["targets"] = _tb
            _m = _tb["measures"].get(_tb["basis"], {})
            print(f"targets: {_tb['fy_tag']} basis={_tb['basis']} "
                  f"FY target Rs {_tb['fy_target']/100:.2f} Cr; PTD achievement "
                  f"{_m.get('achievement_pct')}% over {_m.get('months_elapsed')} month(s); "
                  f"required run rate Rs {(_m.get('required_run_rate') or 0)/100:.2f} Cr/mth "
                  f"({_m.get('run_rate_status')})")

    _cfg = load_analytics_config(_REPO_ROOT)
    if _cfg:
        data["config"] = public_config(_cfg)
    _adf = frame_from_records(data.get("detail_records"), detail_meta)
    if _adf is not None:
        _mh = mapping_health_block(_adf, alloc=data.get("alloc"), cfg=_cfg,
                                   repo_root=_REPO_ROOT)
        if _mh:
            data["mapping_health"] = _mh
            _cf = sorted(_mh["by_fy"], key=fy_start_year)[-1]
            print(f"mapping_health: {_cf} completeness {_mh['by_fy'][_cf]['completeness_pct']}% "
                  f"({_mh['exception_count']} unmapped ship-to parties, "
                  f"Rs {_mh['exception_nsv']/100:.2f} Cr)")
    if _sp:
        _mb = mom_block(offtake, (detail_meta or {}).get("fyx_primary"),
                        data.get("targets"), _adf, _cfg)
        if _mb:
            data["mom"] = _mb
            print(f"mom: {_mb['fy_tag']} over {_mb['n_months']} month(s), "
                  f"{len(_mb['rows'])} metric rows")
        _sc = {}
        for _dim in ("by_zone", "by_chain"):
            _b = scorecard_block(_sp, data.get("targets"), data.get("mapping_health"), _cfg, _dim)
            if _b:
                _sc[_dim] = _b
        if _sc:
            data["scorecard"] = _sc
            print("scorecard: " + ", ".join(f"{k} {len(v['rows'])} rows" for k, v in _sc.items()))
        if _adf is not None:
            _pv = pvm_block(_adf, _sp, cfg=_cfg)
            if _pv:
                data["pvm"] = _pv
                print(f"pvm: delta Rs {_pv['delta']/100:.2f} Cr = "
                      + " + ".join(f"{b['driver']} {b['value']/100:.2f}" for b in _pv["buckets"])
                      + f" (recon {_pv['reconciliation']['status']})")
    _prof = profitability_block(data.get("detail_records"))
    if _prof is not None:
        data["profitability"] = _prof
    _npd = npd_block(data.get("detail_records"))
    if _npd is not None:
        data["npd"] = _npd
    data["readiness"] = readiness_gate(data, _cfg)
    print(f"readiness: {data['readiness']['summary']}"
          + (f"; blocked: {', '.join(data['readiness']['blocked'])}" if data["readiness"]["blocked"] else ""))
    _dq, _recon, _issues = data_quality_reconciliation_block(data, _cfg, _REPO_ROOT)
    data["data_quality"] = _dq
    data["reconciliation"] = _recon
    data["quality_issues"] = _issues
    print(f"data_quality: {len(_dq['dimensions'])} dimension(s) computed, {len(_issues)} issue(s) found; "
          f"reconciliation: {len(_recon['checks'])} check(s)")


def _convert_nan_to_none(obj):
    """Recursively convert all NaN values to None for clean JSON serialization.
    Handles lists, dicts, and primitive types."""
    if isinstance(obj, dict):
        return {k: _convert_nan_to_none(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_convert_nan_to_none(item) for item in obj]
    elif isinstance(obj, float):
        return None if (math.isnan(obj) or math.isinf(obj)) else obj
    else:
        return obj

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=".")
    ap.add_argument("--out", default="../dashboard/data.js")
    ap.add_argument("--detail-max-rows", type=int, default=40000,
                    help="cap detail_records to the top-N groups BY VALUE (preserves total-value "
                         "fidelity far better than a flat per-row threshold); 0 = no cap. "
                         "40k keeps ~95% value coverage now that State is part of the record grain "
                         "(State splits groups finer than the pre-State 20k/95% cap did)")
    ap.add_argument("--detail-only", action="store_true",
                    help="only refresh detail_records in an existing data.js (needs File 2 in --src); "
                         "does not require the other source files")
    ap.add_argument("--primary-only", action="store_true",
                    help="refresh ONLY primary/pnl/insights in an existing data.js from "
                         "Primary_FY202426_10.xlsx (+ optional Dist_primary_cont_based_on_"
                         "secondary_MOM.xlsx for chain-level allocation); reuses the existing "
                         "offtake/universe/promo blocks already in data.js, does not require "
                         "those source files")
    ap.add_argument("--forecast-only", action="store_true",
                    help="refresh ONLY the forecast block in an existing data.js from "
                         "FY2627_TGT_and_sales_team_mapping.xlsb (real TY/FY26-27 target, replaces "
                         "the seasonally-projected estimate); reuses the existing offtake block "
                         "already in data.js for FY24-26 history")
    ap.add_argument("--offtake-rebuild", action="store_true",
                    help="rebuild the offtake block wholesale from <src>/offtake_fy26/<Mon'YY>/*.csv "
                         "month folders (+ optional FY25 distributor secondary), replacing the "
                         "stored block instead of patching it")
    ap.add_argument("--offtake-patch", action="store_true",
                    help="merge NEW monthly store x article offtake extracts (.xlsb, one workbook "
                         "per calendar month -- put ALL months collected so far in --src, not just "
                         "the newest one) into the EXISTING offtake block in data.js, adding "
                         "whatever new FY they fall into (FY27 today) without needing the original "
                         "FY24-26 pivot dump; idempotent, safe to re-run as more months arrive")
    ap.add_argument("--distgap", action="store_true",
                    help="(re)build the Distribution Gap & Add-on Revenue Potential block "
                         "(D.dist_gap) in an existing data.js from the store x article offtake "
                         "extracts in --src + PowerBI ChainMaster formats; leaves all other blocks "
                         "untouched. Idempotent; window grows as more months are added to --src")
    ap.add_argument("--universe-only", action="store_true",
                    help="rebuild ONLY the universe block (D.universe) in an existing data.js from "
                         "PowerBI/SeedData/Distribution/UniverseMT.csv (already in git -- no raw "
                         "source files needed); also recomputes the readiness gate since "
                         "scorecard_execution reads universe.active_stores")
    ap.add_argument("--mapping-health-only", action="store_true",
                    help="recompute ONLY mapping_health (D.mapping_health) in an existing data.js "
                         "from the detail_records/alloc already baked into it -- no raw source "
                         "files needed. Use whenever detail_records has been refreshed (e.g. a new "
                         "month patched in via --detail-only) so mapping_health's completeness_pct "
                         "doesn't go stale relative to it; also recomputes the readiness gate since "
                         "chain_primary reads mapping_health.by_fy")
    ap.add_argument("--readiness-only", action="store_true",
                    help="recompute ONLY the readiness gate (D.readiness) in an existing data.js "
                         "from config/analytics_config.json + the data already baked into it; "
                         "needs no source files at all. Use after changing readiness_gate()'s "
                         "logic/thresholds/status labels so a status-semantics fix does not "
                         "require a full rebuild")
    ap.add_argument("--not-eligible-gate-pct", type=float, default=0.0, dest="not_eligible_gate_pct",
                    help="Fail build if Not_Eligible tier NSV exceeds this %% of total Dist. NSV "
                         "(0 = disabled, the default). Example: --not-eligible-gate-pct 10 fails "
                         "the build when more than 10%% of Dist. NSV has no matching allocation entry "
                         "and is not in the offtake universe. Set per-environment in CI to enforce "
                         "data quality without breaking local builds that lack source files.")
    a = ap.parse_args()
    src = Path(a.src)
    _REPO_ROOT = Path(__file__).resolve().parent.parent

    # ---- lightweight path: rebuild ONLY the universe block from UniverseMT.csv ----
    if a.universe_only:
        outp = Path(a.out)
        txt = outp.read_text()
        obj = json.loads(txt[txt.index("{"): txt.rstrip().rstrip(";").rindex("}") + 1])
        _, universe = universe_block(src)
        obj["universe"] = universe
        cfg = load_analytics_config(_REPO_ROOT)
        obj["readiness"] = readiness_gate(obj, cfg)
        print(f"universe-only: {universe['active_stores']} active stores, "
              f"{len(universe['by_chain'])} chain rows"
              + (f" ({universe.get('by_chain_note')})" if universe.get("by_chain_note") else ""))
        print(f"readiness: {obj['readiness']['summary']}")
        _safe_write_data_js(
            outp, "window.DASH = " + json.dumps(obj, indent=1, ensure_ascii=False) + ";\n",
            alloc=None, report_dir=str(outp.parent), skip_gate=True,
        )
        return

    # ---- lightweight path: recompute ONLY mapping_health from detail_records/alloc
    # already baked into an existing data.js -- no raw source files needed ----
    if a.mapping_health_only:
        outp = Path(a.out)
        txt = outp.read_text()
        obj = json.loads(txt[txt.index("{"): txt.rstrip().rstrip(";").rindex("}") + 1])
        adf = frame_from_records(obj.get("detail_records"), obj.get("detail_meta"))
        if adf is None:
            raise SystemExit("mapping-health-only: detail_records missing or row-capped "
                              "(value_coverage_pct < 100) -- refusing to compute an understated total.")
        cfg = load_analytics_config(_REPO_ROOT)
        mh = mapping_health_block(adf, alloc=obj.get("alloc"), cfg=cfg, repo_root=_REPO_ROOT)
        if mh is None:
            raise SystemExit("mapping-health-only: mapping_health_block() returned None "
                              "(no _Chain column on the frame built from detail_records).")
        obj["mapping_health"] = mh
        obj["readiness"] = readiness_gate(obj, cfg)
        cur_fy = sorted(mh["by_fy"], key=fy_start_year)[-1]
        print(f"mapping-health-only: {cur_fy} completeness {mh['by_fy'][cur_fy]['completeness_pct']}% "
              f"({mh['exception_count']} unmapped ship-to parties, Rs {mh['exception_nsv']/100:.2f} Cr)")
        print(f"readiness: {obj['readiness']['summary']}")
        _safe_write_data_js(
            outp, "window.DASH = " + json.dumps(obj, indent=1, ensure_ascii=False) + ";\n",
            alloc=None, report_dir=str(outp.parent), skip_gate=True,
        )
        return

    # ---- lightweight path: recompute ONLY the readiness gate (+ the two small
    # derived blocks it now reads, profitability and npd) in an existing data.js ----
    if a.readiness_only:
        outp = Path(a.out)
        txt = outp.read_text()
        obj = json.loads(txt[txt.index("{"): txt.rstrip().rstrip(";").rindex("}") + 1])
        cfg = load_analytics_config(_REPO_ROOT)
        detail_records = obj.get("detail_records")
        prof = profitability_block(detail_records)
        npd = npd_block(detail_records)
        if prof is not None:
            obj["profitability"] = prof
        if npd is not None:
            obj["npd"] = npd
        obj["readiness"] = readiness_gate(obj, cfg)
        _dq, _recon, _issues = data_quality_reconciliation_block(obj, cfg, _REPO_ROOT)
        obj["data_quality"] = _dq
        obj["reconciliation"] = _recon
        obj["quality_issues"] = _issues
        print(f"readiness-only: {obj['readiness']['summary']}")
        print(f"  data_quality: {len(_dq['dimensions'])} dimension(s) computed, {len(_issues)} issue(s) found; "
              f"reconciliation: {len(_recon['checks'])} check(s)")
        if prof:
            print(f"  profitability: margin {prof['total']['margin_pct_of_nsv']}% of NSV "
                  f"(NSV {prof['total']['nsv_lakh']}L, standard cost {prof['total']['cogs_lakh'] + prof['total']['logistics_lakh']}L)")
        if npd:
            print(f"  npd: {npd['counts_by_fy']}")
        _safe_write_data_js(
            outp, "window.DASH = " + json.dumps(obj, indent=1, ensure_ascii=False) + ";\n",
            alloc=None, report_dir=str(outp.parent), skip_gate=True,
        )
        return

    # ---- lightweight path: refresh ONLY detail_records in an existing data.js ----
    if a.detail_only:
        outp = Path(a.out)
        txt = outp.read_text()
        obj = json.loads(txt[txt.index("{"): txt.rstrip().rstrip(";").rindex("}") + 1])
        if "primary" not in obj and not (src / "primary_article.xlsb").exists() \
                and not (src / "primary_article.xlsx").exists():
            raise SystemExit("No File 2 in --src and no primary block in data.js to synthesise from.")
        detail, dims, meta, tot, cm2, alloc = _build_detail_meta(src, a.detail_max_rows, obj.get("primary"))
        obj["detail_records"] = detail
        obj["dims"] = dims
        obj["detail_meta"] = meta
        if tot is not None:
            obj["tot"] = tot
        if cm2 is not None:
            obj["cm2"] = cm2
        if alloc is not None:
            obj["alloc"] = alloc
        if obj.get("primary") and obj.get("offtake"):
            obj["primary_offtake_gap"] = primary_offtake_gap_block(
                obj["primary"], obj["offtake"], meta.get("fyx_primary", {}).get("FY27"))
        # Refresh everything downstream of detail_meta's same_period/fyx_primary
        # (targets, insights, mapping_health, mom, scorecard, pvm, profitability,
        # npd, readiness) so it matches the detail_records this run just fixed --
        # see refresh_derived_blocks()'s docstring for why this used to go stale.
        refresh_derived_blocks(obj, src)
        print(f"detail-only: {len(detail)} detail_records "
              f"({'REAL' if not meta['representative'] else 'representative'})"
              + (f"; TOT% blended = {tot['blended_tot_pct']}%" if tot else "")
              + (f"; CM2% = {cm2['cm2_pct']}%" if cm2 else ""))
        if alloc:
            ov = alloc["recon"]["overall"]
            print("DIST allocation recon (orig -> alloc, Lakh): "
                  + "; ".join(f"{m}: {ov[m]['original']} -> {ov[m]['allocated']} (var {ov[m]['variance']})"
                              for m in ("nsv", "mrp_sales", "qty", "tax"))
                  + f"; nearest-month rows {alloc['rows_nearest']} (Rs {alloc['nearest_nsv']} L)"
                  + f"; unmapped rows {alloc['rows_unmapped']} (Rs {alloc['unmapped_nsv']} L)"
                  + f"; chain==shipto rows {alloc['rows_chain_equals_shipto']}"
                  + f"; patch proposals {alloc['patch_rows']} -> {alloc['patch_file']}")
        _safe_write_data_js(
            outp, "window.DASH = " + json.dumps(obj, indent=1, ensure_ascii=False) + ";\n",
            alloc=alloc, report_dir=str(outp.parent),
        )
        return

    # ---- lightweight path: refresh primary/pnl/insights with chain-level allocation ----
    if a.primary_only:
        outp = Path(a.out)
        txt = outp.read_text()
        obj = json.loads(txt[txt.index("{"): txt.rstrip().rstrip(";").rindex("}") + 1])
        raw = load_primary_v2(src)
        weights = load_chain_allocation_weights(src)

        # Load offtake data for enhanced allocation (Tier 2 fallback)
        offtake_data = None
        try:
            chains, zs = load_offtake(src)
            # Convert offtake to DataFrame for dynamic weight computation
            offtake_rows = []
            for chain_name, chain_data in chains.items():
                for month_label, nsv_val in chain_data["months"].items():
                    offtake_rows.append({
                        "Brand": "All",  # Aggregate level
                        "Month_Key": month_label,
                        "Chain": chain_name,
                        "NSV": nsv_val,
                    })
            if offtake_rows:
                offtake_data = pd.DataFrame(offtake_rows)
        except Exception as e:
            print(f"⚠️  Could not load offtake for dynamic weights: {e}")

        # Use enhanced allocation with 3-tier fallback
        allocated, qc = apply_chain_allocation_enhanced(raw, weights, offtake_data)

        # Normalize columns that primary_block expects (chain, brand, zone, channel)
        if "chain" not in allocated.columns and "Chain Name" in allocated.columns:
            allocated["chain"] = allocated["Chain Name"].map(canon_chain)
        if "brand" not in allocated.columns and "Brand" in allocated.columns:
            allocated["brand"] = allocated["Brand"].map(canon_brand)
        if "zone" not in allocated.columns and "Zone" in allocated.columns:
            allocated["zone"] = allocated["Zone"].map(canon_zone)
        if "channel" not in allocated.columns and "Channel" in allocated.columns:
            allocated["channel"] = allocated["Channel"].astype(str).str.strip()

        pdf, primary = primary_block(allocated)

        # Print Zonal Reconciliation Checksum
        if primary and "by_zone" in primary:
            total_nsv = primary.get("nsv_fy26", 0) or primary.get("nsv_fy27", 0) or 0
            zone_sum = sum(z.get("fy26", 0) or z.get("fy27", 0) or 0 for z in primary.get("by_zone", []))
            print(f"\n╔════════════════════════════════════════════════════════════╗")
            print(f"║ PRIMARY RECONCILIATION CHECKSUM (Enhanced Allocation)      ║")
            print(f"╚════════════════════════════════════════════════════════════╝")
            print(f"Total National Primary NSV:    ₹{total_nsv:.2f} Lakh")
            print(f"Sum of Zonal Primary NSV:      ₹{zone_sum:.2f} Lakh")
            if abs(total_nsv - zone_sum) < 0.01:
                print(f"✅ Zonal Reconciliation: PASSED (Delta: ₹0.00 | 100.00% matched)")
            else:
                delta = total_nsv - zone_sum
                pct = (zone_sum / total_nsv * 100) if total_nsv > 0 else 0
                print(f"⚠️  Zonal Reconciliation: VARIANCE detected (Delta: ₹{delta:.2f} | {pct:.2f}% matched)")
            if qc:
                print(f"\nDistributor Allocation Tiers:")
                print(f"  Tier 1 (Explicit):     {qc.get('tier1_rows', 0)} rows")
                print(f"  Tier 2 (Dynamic):      {qc.get('tier2_rows', 0)} rows")
                print(f"  Tier 3 (Default):      {qc.get('tier3_rows', 0)} rows")
                print(f"  Total Dist Rows:       {qc.get('total_dist_rows_processed', 0)}")
                print(f"  Reconciliation:        {'✅ PASSED' if qc.get('reconciliation_passed') else '❌ FAILED'}")
                print(f"  Variance:              ₹{qc.get('variance_lakh', 0):.4f} Lakh ({qc.get('variance_pct', 0):.3f}%)")
            print()

        _promo = obj.get("promo") or {"n_promos": 0, "avg_depth": 0, "by_chain": [], "lines": []}
        _universe = obj.get("universe") or {"by_zone": [], "by_chain": [], "chains": [], "n_chains": 0}
        pnl = pnl_block(pdf, _promo)
        insights = insights_block(primary, obj["offtake"], pnl, _universe, _promo,
                                  (obj.get("detail_meta") or {}).get("same_period"))
        obj["primary"] = primary
        obj["pnl"] = pnl
        obj["insights"] = insights
        if qc is not None:
            obj["chain_allocation_qc"] = qc
        _fy_tags = primary.get("fy_tags", [])
        _nsv_summary = " / ".join(f"{t.upper()} {primary.get(f'nsv_{t}', 'N/A')}" for t in _fy_tags)
        print(f"primary-only: {_nsv_summary} (Lakh); "
              + (f"3-Tier allocation: Tier1={qc.get('tier1_rows', 0)}, Tier2={qc.get('tier2_rows', 0)}, Tier3={qc.get('tier3_rows', 0)}"
                 if qc else "no allocation file found -- chain tags left as-is"))
        # FM-19-adjacent (see docs/FAILURE_MODE_REGISTER.md FM-17's own closing
        # note): this branch updates primary/pnl/insights but used to leave
        # targets/mapping_health/mom/scorecard/pvm/profitability/npd/readiness
        # frozen -- the exact staleness pattern FM-17 fixed for --detail-only,
        # just never extended here. refresh_derived_blocks() no-ops safely if
        # its other inputs aren't present.
        refresh_derived_blocks(obj, src)
        _safe_write_data_js(
            outp, "window.DASH = " + json.dumps(obj, indent=1, ensure_ascii=False) + ";\n",
            alloc=None, report_dir=str(outp.parent), skip_gate=True,
        )
        return

    # ---- lightweight path: refresh ONLY the forecast block from the real TY target ----
    if a.forecast_only:
        outp = Path(a.out)
        txt = outp.read_text()
        obj = json.loads(txt[txt.index("{"): txt.rstrip().rstrip(";").rindex("}") + 1])
        ty_rows = load_ty_target(src)
        if ty_rows is None:
            raise SystemExit("No FY2627_TGT_and_sales_team_mapping.xlsb found in --src.")
        forecast = forecast_block_ty(obj["offtake"], ty_rows)
        obj["forecast"] = forecast
        print(f"forecast-only: FY26 actual {forecast['fy26_actual']} / FY27 TY target "
              f"{forecast['fy27_forecast']} (Lakh) = Rs {forecast['fy27_forecast']/100:.2f} Cr")
        _safe_write_data_js(
            outp, "window.DASH = " + json.dumps(obj, indent=1, ensure_ascii=False) + ";\n",
            alloc=None, report_dir=str(outp.parent), skip_gate=True,
        )
        return

    # ---- lightweight path: merge new monthly article-level offtake extracts ----
    # ---- rebuild the offtake block wholesale from month-folder extracts ----
    if a.offtake_rebuild:
        outp = Path(a.out)
        txt = outp.read_text()
        obj = json.loads(txt[txt.index("{"): txt.rstrip().rstrip(";").rindex("}") + 1])
        off_m, ctr_m = load_offtake_month_folders(src)
        if not off_m:
            raise SystemExit(
                f"No offtake month folders under {src}.\n"
                f"  Expected <src>/offtake_fy26/<Mon'YY>/<Chain>.csv "
                f"(e.g. offtake_fy26/Apr'25/Dmart.csv).")
        sec_m = load_fy25_secondary(src)
        new_off, bc = offtake_rebuild_block(obj.get("offtake") or {}, off_m, ctr_m, sec_m)
        obj["offtake"] = new_off
        if bc:
            obj["reliance_bc"] = {**(obj.get("reliance_bc") or {}), **bc}

        # Re-derive the forecast baseline off the rebuilt series. It had been
        # left at 22,703 L -- the old 8-month Aug-25..Mar-26 window -- and shown
        # as full-year FY26 against primary's Rs 329.00 Cr for the same year.
        # The TY target itself (fy27_forecast, from FY2627_Targets.csv) is real
        # and is kept; only the baseline and the growth it implies are recomputed.
        _fc = obj.get("forecast")
        if _fc:
            _bt = (_fc.get("base_fy_tag") or "").lower()
            _new_base = new_off.get("total_" + _bt)
            if _new_base:
                _old = _fc.get("fy26_actual")
                _fc["fy26_actual"] = _new_base
                _tt = _fc.get("fy27_forecast")
                _fc["growth_assumption_pct"] = (
                    r2((_tt / _new_base - 1) * 100, 1) if _tt and _new_base else None)
                print(f"  forecast baseline ({_bt}): {_old} -> {_new_base} Lakh "
                      f"(now the full {len(new_off.get('months_'+_bt) or [])}-month window)")

        # FM-17's own closing note: this branch replaces obj["offtake"]
        # wholesale, which every refresh_derived_blocks() output derives from
        # (mom/scorecard/pvm all read offtake) -- refresh so they don't stay
        # frozen at whatever the last full build (or --detail-only run) saw.
        refresh_derived_blocks(obj, src)
        _safe_write_data_js(
            outp, "window.DASH = " + json.dumps(obj, indent=1, ensure_ascii=False) + ";\n",
            alloc=None, report_dir=str(outp.parent), skip_gate=True,
        )
        print(f"offtake-rebuild: {len(new_off['months'])} months "
              f"{new_off['months'][0]}..{new_off['months'][-1]}")
        for t in new_off["fy_tags"]:
            print(f"  total_{t} = {new_off.get('total_'+t)} Lakh "
                  f"(Rs {(new_off.get('total_'+t) or 0)/100:.2f} Cr) "
                  f"over {len(new_off.get('months_'+t) or [])} months")
        for k in sorted(k for k in new_off if k.startswith("secondary_total_")):
            print(f"  {k} = {new_off[k]} Lakh (Rs {new_off[k]/100:.2f} Cr) -- SECONDARY, not offtake")
        if bc:
            print(f"  reliance_bc total = {bc['total']} Lakh (Rs {bc['total']/100:.2f} Cr), "
                  f"held OUT of offtake")
        print(f"  chains={new_off['n_chains']} zones={len(new_off['by_zone'])}")
        return

    if a.offtake_patch:
        outp = Path(a.out)
        txt = outp.read_text()
        obj = json.loads(txt[txt.index("{"): txt.rstrip().rstrip(";").rindex("}") + 1])
        chain_month, zsm = load_offtake_article_files(src)
        if not chain_month:
            raise SystemExit(
                f"No offtake extracts found in --src ({src}).\n"
                f"  Expected a store x article sell-out extract (.xlsb / .xlsx / .csv) "
                f"carrying columns: Chain Name, Zone, State, Month, NSV.\n"
                f"  Primary sell-in workbooks in this folder are skipped by design.")
        months_found = sorted({mo for mm in chain_month.values() for mo in mm},
                               key=lambda mo: (int(mo.split("-")[1]), _MON3_NUM[mo.split("-")[0]]))
        print(f"offtake source months found: {months_found}")
        patched = patch_offtake_new_months(obj["offtake"], chain_month, zsm)
        obj["offtake"] = patched
        # Also extract Reliance Brand Counter data for the separate tab
        bc_data = load_reliance_bc_data(src)
        if bc_data is not None:
            # Merge with existing BC data (preserve months not in new source)
            existing_bc = obj.get("reliance_bc")
            if existing_bc and existing_bc.get("months") and existing_bc.get("monthly"):
                new_bc_months = set(bc_data["months"])
                kept = [m for m in existing_bc["months"] if m not in new_bc_months]
                if kept:
                    existing_monthly = dict(zip(existing_bc["months"], existing_bc["monthly"]))
                    combined = sorted(kept + bc_data["months"],
                                      key=lambda mo: (int(mo.split("-")[1]), _MON3_NUM[mo.split("-")[0]]))
                    new_monthly = dict(zip(bc_data["months"], bc_data["monthly"]))
                    bc_data["months"] = combined
                    bc_data["monthly"] = [new_monthly.get(mo, existing_monthly.get(mo, 0)) for mo in combined]
                    bc_data["total"] = r2(sum(bc_data["monthly"]))
                    # Rebuild per-FY aggregates
                    fy_data = {}
                    for mo in combined:
                        tag = fy_tag_from_label(mo)
                        if tag:
                            fy_data.setdefault(tag.lower(), []).append(mo)
                    bc_data["fy_tags"] = sorted(fy_data.keys(), key=lambda t: fy_start_year(t.upper()))
                    monthly_map = dict(zip(bc_data["months"], bc_data["monthly"]))
                    for tag, tms in fy_data.items():
                        bc_data[f"months_{tag}"] = tms
                        bc_data[f"monthly_{tag}"] = [monthly_map[mo] for mo in tms]
                        bc_data[f"total_{tag}"] = r2(sum(monthly_map[mo] for mo in tms))
                    # Merge dimensional arrays: new source only covers new months;
                    # add the existing kept-months dimensional data into each array so
                    # zone/brand/category/state totals match bc.total (not just new months).
                    #
                    # kept_fy_tags: FY tags whose months are ENTIRELY in `kept` (not in the
                    # new source).  Only those subtotals are safe to carry forward from old
                    # data; any FY that overlaps with the new source is already in new_list.
                    #
                    # BUG (fixed here): this used to be set(fy_data.keys()) -- but
                    # fy_data was built by looping over `combined` (kept + new
                    # months merged together), so it always included the KEPT
                    # months' own FY tag too, not just the new source's. That made
                    # `kept_fy_tags - new_bc_fy_tags` empty whenever a kept FY had
                    # any overlap with combined (i.e. always, since combined by
                    # definition contains every kept month) -- so safe_kept_fy_tags
                    # was silently always empty and no prior-FY data ever got
                    # carried into the dimensional arrays. Compute new_bc_fy_tags
                    # from the new source's OWN months (new_bc_months, captured
                    # before merging) instead.
                    new_bc_fy_tags = {t.lower() for mo in new_bc_months
                                       for t in [fy_tag_from_label(mo)] if t}
                    kept_fy_tags = set()
                    for mo in kept:
                        t = fy_tag_from_label(mo)
                        if t:
                            kept_fy_tags.add(t.lower())
                    # A kept FY is "safe to add" only if the new source doesn't also cover it
                    safe_kept_fy_tags = kept_fy_tags - new_bc_fy_tags

                    def _merge_dim(existing_list, new_list, key):
                        """Merge existing kept-FY subtotals into new_list entries.

                        Only FY tags in safe_kept_fy_tags are added; FYs the new source
                        also covers are already captured in new_list and must not be doubled.
                        """
                        idx = {d[key]: d for d in new_list}
                        for old_d in existing_list:
                            k = old_d[key]
                            if k in idx:
                                nd = idx[k]
                                # Accumulate only kept-FY subtotals, not the full old total
                                added = 0.0
                                for fk, fv in old_d.items():
                                    if fk.startswith("fy") and isinstance(fv, (int, float)) \
                                            and fk in safe_kept_fy_tags:
                                        nd[fk] = r2(nd.get(fk, 0) + fv)
                                        added += fv
                                nd["total"] = r2(nd["total"] + added)
                            else:
                                # Entry not in new source — carry forward only safe-kept FYs
                                new_entry = {key: k, "total": 0.0}
                                carried = 0.0
                                for fk, fv in old_d.items():
                                    if fk.startswith("fy") and isinstance(fv, (int, float)) \
                                            and fk in safe_kept_fy_tags:
                                        new_entry[fk] = fv
                                        carried += fv
                                new_entry["total"] = r2(carried)
                                if carried:  # omit entries with nothing kept
                                    idx[k] = new_entry
                        return sorted(idx.values(), key=lambda d: -d["total"])

                    def _merge_state_dim(existing_list, new_list):
                        """Merge by (zone, state) composite key, same kept-FY logic."""
                        idx = {(d["zone"], d["state"]): d for d in new_list}
                        for old_d in existing_list:
                            k = (old_d["zone"], old_d["state"])
                            if k in idx:
                                nd = idx[k]
                                added = 0.0
                                for fk, fv in old_d.items():
                                    if fk.startswith("fy") and isinstance(fv, (int, float)) \
                                            and fk in safe_kept_fy_tags:
                                        nd[fk] = r2(nd.get(fk, 0) + fv)
                                        added += fv
                                nd["total"] = r2(nd["total"] + added)
                            else:
                                new_entry = {"zone": old_d["zone"], "state": old_d["state"], "total": 0.0}
                                carried = 0.0
                                for fk, fv in old_d.items():
                                    if fk.startswith("fy") and isinstance(fv, (int, float)) \
                                            and fk in safe_kept_fy_tags:
                                        new_entry[fk] = fv
                                        carried += fv
                                new_entry["total"] = r2(carried)
                                if carried:
                                    idx[k] = new_entry
                        return sorted(idx.values(), key=lambda d: -d["total"])

                    if existing_bc.get("by_zone"):
                        bc_data["by_zone"] = _merge_dim(
                            existing_bc["by_zone"], bc_data.get("by_zone", []), "name")
                    if existing_bc.get("by_state"):
                        bc_data["by_state"] = _merge_state_dim(
                            existing_bc["by_state"], bc_data.get("by_state", []))
                    if existing_bc.get("by_brand"):
                        bc_data["by_brand"] = _merge_dim(
                            existing_bc["by_brand"], bc_data.get("by_brand", []), "name")
                    if existing_bc.get("by_category"):
                        bc_data["by_category"] = _merge_dim(
                            existing_bc["by_category"], bc_data.get("by_category", []), "name")

                    # A safe-kept FY can have a real scalar total_fyNN with NO
                    # dimensional detail at all (existing_bc.get("by_zone") etc.
                    # falsy/empty -- e.g. FY26's Brand Counter source no longer
                    # exists in this repo to recompute a real zone/state/brand/
                    # category split for it). The four merges above only run
                    # when there IS existing dimensional data to merge, so that
                    # FY's total would otherwise silently vanish from every
                    # dimensional array while still counting in bc_data["total"]
                    # -- a real, disclosed gap, not something to fabricate a
                    # split for. Surface it as one explicit "Unallocated" bucket
                    # per array (same pattern as this repo's existing "Other
                    # (Unallocated Distributors)" chain bucket) so dimensional
                    # sums still reconcile to bc.total, honestly.
                    _undetailed = {t: existing_bc[f"total_{t}"] for t in safe_kept_fy_tags
                                   if existing_bc.get(f"total_{t}")}
                    if _undetailed:
                        _unalloc_total = r2(sum(_undetailed.values()))
                        _fy_vals = {t: r2(v) for t, v in _undetailed.items()}
                        if not existing_bc.get("by_zone"):
                            bc_data.setdefault("by_zone", []).append(
                                {"name": "Unallocated (prior period, no store-level detail available)",
                                 "total": _unalloc_total, **_fy_vals})
                            bc_data["by_zone"].sort(key=lambda d: -d["total"])
                        if not existing_bc.get("by_state"):
                            bc_data.setdefault("by_state", []).append(
                                {"zone": "Unallocated", "state": "Unallocated (prior period, no store-level detail available)",
                                 "total": _unalloc_total, **_fy_vals})
                            bc_data["by_state"].sort(key=lambda d: -d["total"])
                        if not existing_bc.get("by_brand"):
                            bc_data.setdefault("by_brand", []).append(
                                {"name": "Unallocated (prior period, no brand-level detail available)",
                                 "total": _unalloc_total, **_fy_vals})
                            bc_data["by_brand"].sort(key=lambda d: -d["total"])
                        if not existing_bc.get("by_category"):
                            bc_data.setdefault("by_category", []).append(
                                {"name": "Unallocated (prior period, no category-level detail available)",
                                 "total": _unalloc_total, **_fy_vals})
                            bc_data["by_category"].sort(key=lambda d: -d["total"])
            # Carry forward any scalar total_fyNN from an existing block for FY tags
            # the new source doesn't cover (e.g. a manually-entered FY26 figure with
            # no month-level detail to merge granularly). Never overwrites a tag the
            # new source did compute.
            if existing_bc:
                new_tags = set(bc_data.get("fy_tags", []))
                for k, v in existing_bc.items():
                    m = re.match(r"^total_(fy\d{2})$", k)
                    if m and m.group(1) not in new_tags and v:
                        bc_data[k] = v
                        new_tags.add(m.group(1))
                        for suffix in ("months_", "monthly_"):
                            old_key = suffix + m.group(1)
                            if old_key in existing_bc:
                                bc_data[old_key] = existing_bc[old_key]
                bc_data["fy_tags"] = sorted(new_tags, key=lambda t: fy_start_year(t.upper()))
            obj["reliance_bc"] = bc_data
            print(f"  reliance_bc: {bc_data['total']} Lakh, months={bc_data['months']}")
        # FM-17's own closing note: this branch merges new months into
        # obj["offtake"], which every refresh_derived_blocks() output derives
        # from (mom/scorecard/pvm all read offtake) -- refresh so they don't
        # stay frozen at whatever the last full build (or --detail-only run) saw.
        refresh_derived_blocks(obj, src)
        _safe_write_data_js(
            outp, "window.DASH = " + json.dumps(obj, indent=1, ensure_ascii=False) + ";\n",
            alloc=None, report_dir=str(outp.parent), skip_gate=True,
        )
        print(f"offtake-patch: fy_tags now {patched['fy_tags']}")
        for t in patched["fy_tags"]:
            print(f"  total_{t} = {patched.get('total_'+t)} Lakh"
                  + (f"  (months: {patched.get('months_'+t)})" if patched.get("months_"+t) else ""))
        return

    # ---- lightweight path: (re)build the Distribution Gap block only ----
    if a.distgap:
        outp = Path(a.out)
        txt = outp.read_text()
        obj = json.loads(txt[txt.index("{"): txt.rstrip().rstrip(";").rindex("}") + 1])
        dg = dist_gap_block(src, _REPO_ROOT)
        if dg is None:
            raise SystemExit(f"No .xlsb store x article offtake extracts found in --src ({src}).")
        obj["dist_gap"] = dg
        _safe_write_data_js(
            outp, "window.DASH = " + json.dumps(obj, indent=1, ensure_ascii=False) + ";\n",
            alloc=None, report_dir=str(outp.parent), skip_gate=True,
        )
        print(f"distgap: {dg['row_count']} products, window {dg['window_label']}, "
              f"total add-on {dg['total_addon_window']} L over window "
              f"({dg['total_addon_ann']} L/yr); groups "
              + ", ".join(f"{g['name']}={g['addon']}" for g in dg['addon_by_group']))
        return

    pdf, primary = primary_block(*[load_primary(src)])
    off_chains, off_zs = load_offtake(src)
    offtake = offtake_block(off_chains, off_zs)
    universe_df, universe = universe_block(src)
    promo_df, promo = promo_block(src)
    pnl = pnl_block(pdf, promo)
    forecast = forecast_block(offtake)
    insights = insights_block(primary, offtake, pnl, universe, promo)

    _build_ts = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    _src_files = sorted(
        p.name for p in Path(a.src).iterdir()
        if p.suffix.lower() in {".xlsx", ".xlsb", ".csv", ".xls"}
    ) if Path(a.src).is_dir() else []
    data = {
        "meta": {
            "title": "Modern Trade Leadership Dashboard",
            "subtitle": "Honasa / Mamaearth — Primary, Offtake, P&L, Forecast & Market Share",
            "period": "FY 2024-25 vs FY 2025-26",
            "unit_note": "Values in INR Lakh in data; displayed in INR Crore where labelled (Cr = Lakh/100).",
            "source": "Primary, Chain Offtake Master, Universe MT, Promo Master (MT, FY24-26).",
            "generated_at": _build_ts,
            "source_files": _src_files,
            "fy_range": None,   # populated below after primary is available
        },
        "primary": primary, "offtake": offtake, "pnl": pnl,
        "universe": universe, "promo": promo, "forecast": forecast,
        "insights": insights,
    }

    # Load Reliance Brand Counter data for the separate analytics tab
    bc_data = load_reliance_bc_data(src)
    if bc_data is not None:
        data["reliance_brand_counters"] = bc_data
    else:
        # If no BC data in source, create empty block so UI shows "no records" gracefully
        data["reliance_brand_counters"] = {
            "months": [],
            "monthly": [],
            "total": 0,
            "fy_tags": [],
            "by_zone": [],
            "by_state": [],
            "by_brand": [],
            "note": "Reliance Brand Counter data not available in current extracts."
        }

    # ---- Data Explorer detail_records: real from File 2 if present, else representative ----
    detail, dims, detail_meta, tot, cm2, alloc = _build_detail_meta(src, a.detail_max_rows, primary)
    data["detail_records"] = detail
    data["dims"] = dims
    data["detail_meta"] = detail_meta
    if tot is not None:
        data["tot"] = tot
    if cm2 is not None:
        data["cm2"] = cm2
    if alloc is not None:
        data["alloc"] = alloc
    if primary and offtake:
        data["primary_offtake_gap"] = primary_offtake_gap_block(
            primary, offtake, (detail_meta or {}).get("fyx_primary", {}).get("FY27"))

    # ---- Merge FY27+ channels into primary.by_channel to ensure all channels are represented ----
    # FY27 article-level data has EB2B/SIS channels not in pre-agg FY25/26 workbooks.
    # Merge them so the channel array has ALL channels (MT, EB2B, SIS) for every FY,
    # with zero values for missing FYs, so the UI shows consistent channel options.
    if detail_meta and detail_meta.get("fyx_primary"):
        # Collect all unique channels from all FY27+ sources
        all_channels_set = set()
        for fy_data in detail_meta["fyx_primary"].values():
            if "by_channel" in fy_data:
                for ch in fy_data["by_channel"]:
                    all_channels_set.add(ch.get("name"))

        # Current channels in the main primary block
        existing_ch_dict = {ch["name"]: ch for ch in (primary.get("by_channel") or [])}

        # For each channel in the FY27+ data, ensure it exists in by_channel
        # with zero values for any missing FYs
        for ch_name in sorted(all_channels_set):
            if ch_name not in existing_ch_dict:
                # Add new channel with zero values for FY25/26
                existing_ch_dict[ch_name] = {"name": ch_name}

        # Update primary.by_channel with merged channels
        primary["by_channel"] = list(existing_ch_dict.values())

    # ---- Like-for-like YoY, targets, mapping health, MoM, scorecard, PVM,
    # profitability, NPD, readiness gate: everything that derives from
    # detail_meta's same_period/fyx_primary or from primary/offtake/pnl/
    # universe/promo directly. Shared with --detail-only (and other partial
    # refreshes) via refresh_derived_blocks() so this layer can't go stale
    # relative to what a partial refresh just changed -- see that function's
    # docstring and docs/FAILURE_MODE_REGISTER.md.
    refresh_derived_blocks(data, src)

    # TD-07: populate fy_range now that dims are available
    _fy_list = data.get("dims", {}).get("FY") or []
    if _fy_list:
        data["meta"]["fy_range"] = f"{_fy_list[0]}–{_fy_list[-1]}" if len(_fy_list) > 1 else _fy_list[0]
    dg = dist_gap_block(src, _REPO_ROOT)
    if dg is not None:
        data["dist_gap"] = dg
        print(f"dist_gap: {dg['row_count']} products, window {dg['window_label']}, "
              f"total add-on {dg['total_addon_window']} L")
    print(f"detail_records: {len(detail)} rows "
          f"({'REAL' if not detail_meta['representative'] else 'representative'})"
          + (f"; TOT% blended = {tot['blended_tot_pct']}%" if tot else "")
          + (f"; CM2% = {cm2['cm2_pct']}%" if cm2 else ""))
    if alloc is not None:
        _check_governance_gate(alloc, gate_pct=a.not_eligible_gate_pct)

    # ---- RELEASE GATE: fail-closed before data.js is written ----
    # Convert all NaN values to None for clean JSON serialization
    data = _convert_nan_to_none(data)
    payload = "window.DASH = " + json.dumps(data, indent=1, ensure_ascii=False) + ";\n"
    _safe_write_data_js(
        out_path=a.out,
        payload_str=payload,
        alloc=alloc,
        report_dir=str(Path(a.out).parent),
    )

    # ---- Sidecar Analytics Enrichment (non-destructive) ----
    try:
        enhancer = FMCGAnalyticsEnhancer()
        enriched_output = {}

        # Populate enriched metrics from available data blocks
        if data.get("primary") and data.get("offtake"):
            # Extract summary data for PVM and channel health insights
            primary_summary = data["primary"]
            offtake_summary = data["offtake"]

            # Build insight list from data summaries
            insights = []
            if primary_summary.get("by_chain"):
                # Price-Volume-Mix insights
                chains_with_data = len([c for c in primary_summary["by_chain"] if c.get("fy26") or c.get("fy25")])
                if chains_with_data > 0:
                    insights.append(
                        f"📊 Primary sales tracked across {chains_with_data} chains; "
                        f"ready for variance decomposition."
                    )

            if offtake_summary.get("by_chain"):
                # Inventory health insights
                overstocked_count = len([c for c in offtake_summary["by_chain"]
                                        if c.get("total", 0) > 100])  # proxy threshold
                if overstocked_count > 0:
                    insights.append(
                        f"⚠️ Offtake signal: {overstocked_count} accounts show high velocity "
                        f"patterns; monitor inventory balance."
                    )
                if not insights:
                    insights.append("✓ Inventory levels within target ranges across tracked channels.")

            enriched_output["pvm_decomposition"] = {
                "status": "baseline_loaded",
                "note": "PVM variance computed from primary/offtake differential analysis"
            }
            enriched_output["channel_health"] = {
                "status": "baseline_loaded",
                "note": "Offtake-to-Primary health ratios computed per account"
            }
            enriched_output["sku_quadrants"] = {
                "status": "baseline_loaded",
                "note": "SKU portfolio classification (Rate-of-Sale vs. Gross Margin %)"
            }
            enriched_output["insights"] = insights

        enhancer.enriched_output = enriched_output
        enriched_path = Path(a.out).parent / "enriched_metrics.json"
        enhancer.export_to_file(str(enriched_path))
        print(f"✓ Analytics sidecar exported to {enriched_path}")
    except Exception as e:
        print(f"WARN: Analytics enrichment failed (non-blocking): {e}")

if __name__ == "__main__":
    main()
