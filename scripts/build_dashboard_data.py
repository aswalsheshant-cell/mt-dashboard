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
import argparse, csv, io, json, re, math, datetime
from pathlib import Path

import pandas as pd

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
    if z is None:
        return None
    z = str(z).strip()
    m = {"south-1": "South 1", "south 1": "South 1", "south-2": "South 2", "south 2": "South 2",
         "north": "North", "west": "West", "east": "East"}
    return m.get(z.lower(), z)

# Canonical chain key: collapse the many spellings across the four files onto a
# single business-facing chain name so primary / offtake / universe / promo join.
# Aliases resolve to the RETAIL BANNER only. Ship-to/DC/store-format suffixes
# ("-DC", "-Store", "DC-", legal-entity forms like "... Retail Limited") are
# location/entity qualifiers, NOT distinct chains, and must collapse onto the
# banner -- otherwise one chain shows up as several rows in the Chain filter and
# every chain-level total silently splits. Channel (MT / EB2B / SIS) stays a
# SEPARATE dimension on each record and is never baked into the chain name:
# in this dataset every banner trades in exactly one channel, so Chain x Channel
# already disambiguates without duplicating the banner.
CHAIN_ALIASES = [
    ("Apollo",            ["apollo", "apollo healthco"]),
    ("Reliance Retail",   ["reliance retail", "reliance retail limited", "reliance retail ltd.",
                            "reliance", "reliance ", "rrl", "metro-cnc-rrl",
                            # DC / store / FOC-sample splits of the same banner
                            "reliance retail-dc", "reliance retail-store", "rrl-foc-sample"]),
    ("Dmart",             ["dmart", "d-mart", "d-mart ", "dmart ",
                            # DC + e-com store formats of the same banner
                            "dc-d-mart-offline", "d-mart-offline", "d-mart-store-e-com"]),
    ("Nykaa (FSN)",       ["fsn", "nykaa ss(fsn)", "nykaa", "nykaa e-retail limited",
                            "nykaa e-retail"]),
    ("Wellness Forever",  ["wellness forever"]),
    ("H&G",               ["h&g", "hng", "h\\&g", "health & glow", "health and glow"]),
    ("Lulu",              ["lulu", "lulu "]),
    ("Metro C&C",         ["metro cnc", "metro c&c", "metro ", "metro-cnc-rrl", "metro-cnc"]),
    ("More Retail",       ["more", "more retail", "more "]),
    ("RMT-Sancus",        ["rmt-sancus", "sancus(rmt)", "sancus ", "rmt-delhi"]),
    ("Walmart",           ["walmart cnc", "walmart", "walmart ", "wal-mart", "walmart-cnc"]),
    ("VMM",               ["vmm", "vmm "]),
    ("Spencer",           ["spencer"]),
    ("Guardian",          ["guardian", "gaurdian ", "guardian healthcare",
                            "guardian healthcare-delhi"]),
    ("Trent",             ["trent", "trent ", "trent hypermarket"]),
    ("V-Mart",            ["v-mart", "v mart east ", "v-mart retail", "v-mart retail limited"]),
    ("Ratnadeep",         ["ratnadeep", "ratandeep"]),
    ("Sasta Sundar",      ["sasta sundar", "sasta sunder", "ssl"]),
    ("Frankross",         ["frankross", "frankros"]),
    ("Arambagh",          ["arambagh", "aarambagh food mart ", "arambagh food mart"]),
    ("WH-Smith",          ["wh-smith", "travel news services-wsmith", "travel news services"]),
    ("Relay",             ["relay", "travel retail services-relay", "travel retail services"]),
    ("B&N",               ["b&n", "beauty & nutire", "beauty & nutrie", "b\\&n"]),
    ("Apna Mart",         ["apna mart", "apna mart "]),
    ("Sumo Save",         ["sumo save", "sumosave"]),
    ("Deal Share",        ["deal share", "deal share "]),
    ("Sohum Shoppe",      ["sohum shoppe", "sohum"]),
    ("Lifestyle",         ["lifestyle", "lifestyle "]),
    ("Trent/Westside",    ["trends"]),
    ("Sasta Sundar",      ["sastasundar"]),
    ("Frankross",         ["frank ross"]),
    # Azorte is Reliance's own SIS beauty format -- a distinct trading banner,
    # deliberately NOT folded into Reliance Retail (it reports as its own account).
    ("Azorte",            ["azorte", "reliance retail-(azorte)", "reliance retail (azorte)"]),
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
    """Load primary from Primary_FY202426_10.xlsx (business-confirmed
    2026-07-03 as source-of-truth; see PowerBI/docs/SIS_Reconciliation.md).
    Same output shape as load_primary() plus the raw Ship-To / Direct-
    Distributor columns needed for chain-level allocation."""
    f = src / "Primary_FY202426_10.xlsx"
    df = pd.read_excel(f, sheet_name="Dump", header=1)
    df.columns = [str(c).strip() for c in df.columns]
    df = df.dropna(how="all")
    df = df[df["NSV"].notna()]
    df["_ship_to"] = df["Bill to customer"].astype(str).str.strip()
    df["_dist_flag"] = df["Direct/Distributor"].astype(str).str.strip()
    df["NSV"] = pd.to_numeric(df["NSV"], errors="coerce").fillna(0.0)
    df["MRP value"] = pd.to_numeric(df["MRP value"], errors="coerce").fillna(0.0)
    df["Month"] = df["Month"].astype(str).str.strip()
    return df

def load_chain_allocation_weights(src):
    """Read the secondary-driven Ship-To -> Chain Cont% allocation
    (Dist_primary_cont_based_on_secondary_MOM.xlsx, Sheet2 = the already
    chain-split Distributor rows). Returns {(ship_to_norm, brand_canon,
    month_norm): [(chain_raw, fraction), ...]} with fractions derived from
    the sheet's own NSV split (normalised to sum to 1 per key) rather than
    trusting the printed Cont% column's rounding. Returns None if the file
    isn't present in --src (allocation step is then skipped, unchanged
    behaviour)."""
    f = src / "Dist_primary_cont_based_on_secondary_MOM.xlsx"
    if not f.exists():
        return None
    s2 = pd.read_excel(f, sheet_name="Sheet2", header=1)
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
    tags = sorted({t for t in tag_of.values() if t}, key=fy_start_year)
    keys_of = {t: [k for k, tt in tag_of.items() if tt == t] for t in tags}
    lo = [t.lower() for t in tags]
    out["fy_tags"] = lo

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
    return None

# --------------------------------------------------------------------------
# RELIANCE BA (Beauty Advisor) COUNTER ISOLATION
#
# The monthly store x article offtake extracts carry a "Store Type" column with
# exactly two values:
#   "Brand Counter"     -- BA-manned counters, reported at real store site codes
#   "Non Brand Counter" -- the macro//roll-up stream
# In this dataset EVERY "Brand Counter" row is Reliance, and the Reliance
# "Non Brand Counter" stream carries a BLANK site code (i.e. it is an aggregate
# roll-up row, not a store). The two streams share ZERO site codes.
#
# Business rule applied here: the macro roll-up is treated as ALREADY containing
# the BA counter sales, so adding both inflates Reliance. The main Offtake total
# therefore uses the MACRO stream only, and the BA stream is routed to the
# dedicated "Reliance BA Counters" view. See `assumption` in the emitted block --
# this is the one judgement call in the isolation and it is stated in the data.
# --------------------------------------------------------------------------
_BA_STORE_TYPE = "brand counter"
_MACRO_STORE_TYPE = "non brand counter"

def _read_offtake_monthly_frames(src):
    """Yield (label, DataFrame) for every monthly store x article offtake
    extract found under --src, normalising the two schema generations:
      old: 'Chain Name' / 'Site Code' / 'Store Type' / 'Month'   (Apr-26, May-26)
      new: 'Chain' / 'Store' / <no Store Type> / 'MonthKey'      (Jun-26+)
    Only frames that expose Store Type can be BA-isolated; the caller reports
    the rest as un-isolable rather than guessing a split."""
    seen = set()
    for d in (src / "Offtake_Monthly", src):
        if not d.exists():
            continue
        for fp in sorted(d.glob("offtake_store_article_*.csv")):
            if fp.name in seen:
                continue
            seen.add(fp.name)
            try:
                df = pd.read_csv(fp, low_memory=False)
            except Exception:
                continue
            df.columns = [" ".join(str(c).split()) for c in df.columns]
            yield fp.name, df

def load_reliance_ba(src):
    """Split the Reliance offtake stream into BA-counter vs macro, per month.
    Returns a `reliance_ba` block, or None when no extract carries Store Type."""
    ba_m, macro_m, sites_m, rows_m = {}, {}, {}, {}
    isolable, not_isolable = [], []
    for fname, df in _read_offtake_monthly_frames(src):
        chain_col = next((c for c in ("Chain Name", "Chain") if c in df.columns), None)
        if chain_col is None or "NSV" not in df.columns:
            continue
        month_col = next((c for c in ("Month", "MonthKey", "Revised Month")
                          if c in df.columns), None)
        if month_col is None:
            continue
        # month label: prefer whichever column parses to a real 'Mon-YY'
        lab = None
        for mc in (month_col, "MonthKey", "MonthStart", "Month"):
            if mc not in df.columns:
                continue
            s = df[mc].dropna()
            if s.empty:
                continue
            cand = _offtake_row_month(s.iloc[0])
            if cand is None:
                m = re.match(r"(\d{4})-(\d{2})", str(s.iloc[0]).strip())
                if m:
                    cand = (f"{datetime.date(int(m.group(1)), int(m.group(2)), 1):%b}"
                            f"-{m.group(1)[-2:]}")
            if cand:
                lab = cand
                break
        if lab is None:
            continue
        rel = df[df[chain_col].astype(str).str.contains("reliance", case=False, na=False)
                 | df[chain_col].astype(str).str.strip().str.lower().eq("rrl")].copy()
        if rel.empty:
            continue
        rel["_nsv"] = pd.to_numeric(rel["NSV"], errors="coerce").fillna(0.0)
        if "Store Type" not in rel.columns:
            not_isolable.append({"month": lab, "file": fname,
                                 "reliance_nsv": r2(float(rel["_nsv"].sum())),
                                 "reason": "extract has no 'Store Type' column -- "
                                           "BA vs macro cannot be separated"})
            continue
        st = rel["Store Type"].astype(str).str.strip().str.lower()
        ba, macro = rel[st == _BA_STORE_TYPE], rel[st == _MACRO_STORE_TYPE]
        site_col = next((c for c in ("Site Code", "Store") if c in rel.columns), None)
        ba_m[lab] = r2(float(ba["_nsv"].sum()))
        macro_m[lab] = r2(float(macro["_nsv"].sum()))
        rows_m[lab] = {"ba": int(len(ba)), "macro": int(len(macro))}
        sites_m[lab] = int(ba[site_col].dropna().nunique()) if site_col else None
        isolable.append(lab)
    if not ba_m:
        return None
    order = sorted(ba_m, key=lambda mo: (int(mo.split("-")[1]), _MON3_NUM[mo.split("-")[0]]))
    by_fy = {}
    for mo in order:
        tag = fy_tag_from_label(mo)
        if not tag:
            continue
        f = by_fy.setdefault(tag.lower(), {"ba": 0.0, "macro": 0.0, "months": []})
        f["ba"] += ba_m[mo] or 0.0
        f["macro"] += macro_m[mo] or 0.0
        f["months"].append(mo)
    for f in by_fy.values():
        f["ba"], f["macro"] = r2(f["ba"]), r2(f["macro"])
        f["combined"] = r2((f["ba"] or 0) + (f["macro"] or 0))
    return {
        "chain": "Reliance Retail",
        "months": order,
        "ba_monthly": [ba_m[mo] for mo in order],
        "macro_monthly": [macro_m[mo] for mo in order],
        "ba_stores": {mo: sites_m[mo] for mo in order},
        "rows": {mo: rows_m[mo] for mo in order},
        "by_fy": by_fy,
        "months_not_isolable": not_isolable,
        "unit": "INR Lakh",
        "status": "PARTIAL" if not_isolable else "FINAL",
        "assumption": ("Macro (Non Brand Counter) is treated as ALREADY INCLUSIVE of "
                       "BA counter sales, so the main Offtake total uses macro only "
                       "and BA is reported separately. Evidence: the Reliance macro "
                       "stream carries a BLANK site code (an aggregate roll-up, not a "
                       "store) while BA is at ~320 real store site codes, and the two "
                       "share zero site codes. If the business confirms the streams are "
                       "additive instead, set additive=true and rebuild."),
        "method": ("Split on the extract's 'Store Type' column: 'Brand Counter' = BA, "
                   "'Non Brand Counter' = macro. Months whose extract lacks that column "
                   "are listed in months_not_isolable and are LEFT IN the macro total "
                   "un-split -- never guessed at."),
    }

def apply_reliance_ba_isolation(offtake, ba):
    """Remove the BA-counter stream from the main Offtake aggregates so no total
    double-counts it, and stash the pre-isolation figures for audit. Idempotent:
    always recomputes from `combined_before` rather than subtracting again."""
    if not ba:
        return offtake
    row = next((c for c in offtake.get("by_chain", [])
                if c.get("name") == ba["chain"]), None)
    audit = {}
    for lo, f in ba["by_fy"].items():
        before = None
        if row is not None:
            before = row.get("_ba_combined_before", {}).get(lo, row.get(lo))
        if before is None:
            continue
        # macro-only is the isolated value; recompute from `before` every run
        after = r2(max((before or 0) - (f["ba"] or 0), 0.0))
        if row is not None:
            row.setdefault("_ba_combined_before", {})[lo] = r2(before)
            row[lo] = after
        tot_k = f"total_{lo}"
        if tot_k in offtake:
            t_before = offtake.get(f"_ba_total_before_{lo}", offtake[tot_k])
            offtake[f"_ba_total_before_{lo}"] = r2(t_before)
            offtake[tot_k] = r2((t_before or 0) - (f["ba"] or 0))
        mk = f"monthly_{lo}"
        mos = offtake.get(f"months_{lo}") or []
        if mk in offtake and isinstance(offtake[mk], list) and len(offtake[mk]) == len(mos):
            base = offtake.get(f"_ba_monthly_before_{lo}") or list(offtake[mk])
            offtake[f"_ba_monthly_before_{lo}"] = [r2(v) if isinstance(v, (int, float)) else v
                                                   for v in base]
            ba_by_mo = dict(zip(ba["months"], ba["ba_monthly"]))
            offtake[mk] = [
                r2((base[i] or 0) - (ba_by_mo.get(mo) or 0))
                if isinstance(base[i], (int, float)) else base[i]
                for i, mo in enumerate(mos)]
        audit[lo] = {"combined_before": r2(before), "ba_removed": f["ba"],
                     "macro_after": after}
    ba["isolation_audit"] = audit
    ba["applied"] = True
    return offtake

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
    Returns (chain_month, zone_state_month); both {} if no .xlsb found."""
    files = sorted(src.glob("*.xlsb"))
    chain_month, zsm = {}, {}
    for fp in files:
        sheets = pd.read_excel(fp, sheet_name=None, header=1, engine="pyxlsb")
        for _, df in sheets.items():
            df.columns = [str(c).strip() for c in df.columns]
            need = {"Chain Name", "Zone", "State", "Month", "NSV"}
            if not need <= set(df.columns):
                continue   # not a row-level extract sheet -- skip
            df = df[df["Chain Name"].notna()].copy()
            df["_chain"] = df["Chain Name"].map(canon_chain)
            df["_zone"] = df["Zone"].map(canon_zone)
            df["_state"] = df["State"].astype(str).str.strip()
            df["_month"] = df["Month"].map(_offtake_row_month)
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
    by_state_idx = {(s.get("zone"), s["state"]): s for s in offtake.get("by_state", [])}
    for tag in touched_tags:
        lo = tag.lower()
        months_of_tag = [mo for mo in all_months if fy_tag_from_label(mo) == tag]
        monthly_vals = [r2(sum(mm.get(mo, 0.0) for mm in chain_month.values())) for mo in months_of_tag]
        offtake[f"months_{lo}"] = months_of_tag
        offtake[f"monthly_{lo}"] = monthly_vals
        offtake[f"total_{lo}"] = r2(sum(v or 0 for v in monthly_vals))
        for chain, months in chain_month.items():
            row = by_chain_idx.get(chain)
            if row is None:
                row = {"name": chain, "raw": chain, "total": 0.0}
                offtake["by_chain"].append(row)
                by_chain_idx[chain] = row
            row[lo] = r2(sum(v for mo, v in months.items() if mo in months_of_tag))
        zone_totals = {}
        for (zone, state), months in zsm.items():
            v = r2(sum(v for mo, v in months.items() if mo in months_of_tag)) or 0.0
            zone_totals[zone] = zone_totals.get(zone, 0.0) + v
            srow = by_state_idx.get((zone, state))
            if srow is None:
                srow = {"state": state, "zone": zone}
                offtake.setdefault("by_state", []).append(srow)
                by_state_idx[(zone, state)] = srow
            srow[lo] = v
        for zone, v in zone_totals.items():
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
    "H&G": "Health & Glow", "Spencer": "Spencers", "VMM": "Vishal Mega Mart",
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
    files = sorted(src.glob("*.xlsb"))
    if not files:
        return None
    fmt_map = load_chain_formats(repo_root)
    cols = ["Chain Name", "Site Code", "EAN", "Category", "Brand",
            "Description as per Fountain", "NSV", "Month"]
    frames = []
    for fp in files:
        for _, df in pd.read_excel(fp, sheet_name=None, header=1, engine="pyxlsb").items():
            df.columns = [str(c).strip() for c in df.columns]
            if not {"Chain Name", "Site Code", "EAN", "Category", "NSV", "Month"} <= set(df.columns):
                continue
            frames.append(df[[c for c in cols if c in df.columns]].copy())
    if not frames:
        return None
    d = pd.concat(frames, ignore_index=True)
    d["_chain"] = d["Chain Name"].map(canon_chain)
    d["_fmt"] = d["_chain"].map(lambda c: fmt_map.get(c, "Unclassified"))
    d["_site"] = d["_chain"].astype(str) + "|" + d["Site Code"].astype(str)
    d["_ean"] = d["EAN"].astype(str)
    d["_nsv"] = pd.to_numeric(d["NSV"], errors="coerce").fillna(0.0)
    d["_cat"] = d["Category"].astype(str)
    d["_mon"] = d["Month"].map(_offtake_row_month)
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
def universe_block(src):
    u = pd.read_excel(src / "universe.xlsx", sheet_name="PAN INDIA", header=0)
    u.columns = [str(c).strip() for c in u.columns]
    u = u[u["Chain Name"].notna()]
    u["active"] = u["Status"].astype(str).str.strip().str.upper().eq("ACTIVE")
    u["zone"] = u["Zone"].map(canon_zone)
    u["chain"] = u["Chain Name"].map(canon_chain)
    act = u[u["active"]]
    out = {"total_stores": int(len(u)), "active_stores": int(len(act))}
    out["by_zone"] = sorted([{"name": k, "stores": int(v)}
                             for k, v in act.groupby("zone").size().items() if k],
                            key=lambda d: -d["stores"])
    out["by_citycat"] = [{"name": k, "stores": int(v)}
                         for k, v in act.groupby(act["City Category"].astype(str).str.strip()).size().items()]
    out["by_chain"] = sorted([{"name": k, "stores": int(v)}
                              for k, v in act.groupby("chain").size().items() if k],
                             key=lambda d: -d["stores"])[:20]
    st = act.groupby(act["Store Type"].astype(str).str.strip().str.upper()).size()
    out["by_storetype"] = sorted([{"name": k.title(), "stores": int(v)} for k, v in st.items()],
                                 key=lambda d: -d["stores"])[:10]
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
    p = pd.read_excel(src / "promo.xlsx", sheet_name="Sheet1", header=0)
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
    tot_tax = tot_mrp - tot_nsv - tot_passon

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
    Returns [] if the file is missing (no expenses loaded yet -- CM2 then
    just equals NSV, and the dashboard/Power BI both show an explicit
    "no expense data loaded" state rather than a fabricated CM2)."""
    path = Path(__file__).resolve().parent.parent / "PowerBI" / "SeedData" / "Masters" / "PL_Expense_Input.csv"
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))

def _build_custcode_chain_lookup(df):
    """Cust-SAP Code -> most common Chain, built from the primary article
    data itself, so an expense row that only gives a Customer Code (no
    Chain) can still resolve for chain-wise CM2."""
    sub = df[df["_CustCode"] != ""]
    if sub.empty:
        return {}
    return sub.groupby("_CustCode")["_Chain"].agg(lambda s: s.value_counts().idxmax()).to_dict()

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
        return sorted(out, key=lambda d: -(d["nsv"] or 0))

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
# INSIGHTS  (auto-generated, data-driven)
# --------------------------------------------------------------------------
def insights_block(primary, offtake, pnl, universe, promo):
    ins = []
    pc = {c["name"]: c for c in primary["by_chain"]}
    oc = {c["name"]: c for c in offtake["by_chain"]}
    uc = {c["name"]: c for c in universe["by_chain"]}

    # 1. Concentration
    top2 = primary["by_chain"][:2]
    tot = primary["nsv_fy26"] or 1
    share = sum(c["fy26"] or 0 for c in top2) / tot * 100
    ins.append({"type": "risk", "title": "Revenue concentration in top 2 chains",
                "text": f"{top2[0]['name']} and {top2[1]['name']} together drive "
                        f"{share:.0f}% of FY25-26 MT primary (₹{(sum(c['fy26'] for c in top2))/100:.0f} Cr). "
                        f"De-risk by accelerating the mid-tier (Apollo, Nykaa, Wellness Forever)."})
    # 2. Fastest growers (material base)
    growers = [c for c in primary["by_chain"] if c["yoy"] is not None and (c["fy26"] or 0) > 200]
    growers.sort(key=lambda d: -(d["yoy"] or 0))
    if growers:
        g = growers[0]
        ins.append({"type": "win", "title": "Fastest-growing scaled chain",
                    "text": f"{g['name']} grew {g['yoy']:.0f}% YoY to ₹{g['fy26']/100:.1f} Cr. "
                            f"Lock incremental visibility + assortment to defend the momentum."})
    # 3. Decliners
    decl = [c for c in primary["by_chain"] if c["yoy"] is not None and c["yoy"] < 0 and (c["fy25"] or 0) > 150]
    decl.sort(key=lambda d: d["yoy"])
    if decl:
        d = decl[0]
        ins.append({"type": "risk", "title": "Scaled chain in decline",
                    "text": f"{d['name']} fell {d['yoy']:.0f}% YoY (₹{d['fy25']/100:.1f}→₹{d['fy26']/100:.1f} Cr). "
                            f"Diagnose range/fill-rate and reset the JBP."})
    # 4. Sell-in vs sell-out (inventory health)
    gaps = []
    for name, p in pc.items():
        o = oc.get(name)
        if o and (o["fy26"] or 0) > 200 and (p["fy26"] or 0) > 0:
            ratio = (p["fy26"] or 0) / (o["fy26"] or 1)
            gaps.append((name, ratio, p["fy26"], o["fy26"]))
    over = [x for x in gaps if x[1] > 1.15]
    over.sort(key=lambda x: -x[1])
    if over:
        n, ratio, pp, oo = over[0]
        ins.append({"type": "risk", "title": "Primary running ahead of offtake",
                    "text": f"At {n}, primary is {ratio:.2f}x offtake in FY25-26 "
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
        if p and u["stores"] > 50 and (p["fy26"] or 0) > 0:
            prod.append((name, (p["fy26"] or 0) / u["stores"], u["stores"], p["fy26"]))
    if prod:
        prod.sort(key=lambda x: x[1])
        n, ppsk, stores, nsv = prod[0]
        ins.append({"type": "watch", "title": "Low throughput per store — distribution to activate",
                    "text": f"{n} has {stores:,} active stores but only ₹{nsv/100:.1f} Cr primary "
                            f"(₹{ppsk:.1f} L/store) — large headroom to lift productivity per door."})
    # 7. Brand mix
    bm = sorted(primary["by_brand"], key=lambda d: -(d["fy26"] or 0))
    if bm:
        lead = bm[0]
        bshare = (lead["fy26"] or 0) / (primary["nsv_fy26"] or 1) * 100
        ins.append({"type": "watch", "title": "Portfolio mix",
                    "text": f"{lead['name']} is {bshare:.0f}% of FY25-26 MT primary. "
                            f"Scale Aqualogica / The Derma Co to broaden the portfolio in MT."})
    # 8. Forecast headline handled in forecast tab
    return ins

# --------------------------------------------------------------------------
# --------------------------------------------------------------------------
# DETAIL RECORDS  (Data Explorer drill-down: 13-column grain)
# --------------------------------------------------------------------------
_ORDER = ["April","May","June","July","Aug","Sept","Oct","Nov","Dec","Jan","Feb","March"]

_MNUM = {4:"April",5:"May",6:"June",7:"July",8:"Aug",9:"Sept",10:"Oct",11:"Nov",12:"Dec",1:"Jan",2:"Feb",3:"March"}
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

def load_dist_cont_weights(src):
    """Weights DataFrame [_st, _bl, _pm, _AllocChainRaw, _frac] from the cont
    sheet, fractions normalised to sum to 1 per (ShipTo, Brand, Month) key,
    plus {key: raw_pct_sum} for the cont%-sum-=100 QC check. Returns
    (None, None) if the file isn't in --src (allocation is then skipped and
    Dist. rows keep whatever chain tag the source gave them -- old behaviour)."""
    f = src / "Dist_primary_cont_based_on_secondary_MOM.xlsx"
    if not f.exists():
        return None, None
    w = pd.read_excel(f, sheet_name="Dist Primary Conv to Chain Art", header=1)
    w.columns = [str(c).strip() for c in w.columns]
    w = w.dropna(subset=["Ship To Name", "Chain Name", "Secondary contribution %"])
    w["_st"] = w["Ship To Name"].astype(str).str.strip().str.lower()
    w["_bl"] = w["Brand"].astype(str).str.strip().str.lower()
    w["_pm"] = w["Revised month"].map(_month_period)
    w["_pct"] = pd.to_numeric(w["Secondary contribution %"], errors="coerce").fillna(0.0)
    w = w[w["_pm"].notna() & (w["_pct"] != 0)]
    key_sums = w.groupby(["_st", "_bl", "_pm"])["_pct"].transform("sum")
    raw_sums = {k: round(float(v), 2)
                for k, v in w.groupby(["_st", "_bl", "_pm"])["_pct"].sum().items()}
    w["_frac"] = w["_pct"] / key_sums
    w["_AllocChainRaw"] = w["Chain Name"].astype(str).str.strip()
    # raw-case names carried through for the auto-generated patch-proposal CSV
    w["_ShipToRaw"] = w["Ship To Name"].astype(str).str.strip()
    w["_BrandRaw"] = w["Brand"].astype(str).str.strip()
    return w[["_st", "_bl", "_pm", "_AllocChainRaw", "_frac", "_ShipToRaw", "_BrandRaw"]].copy(), raw_sums

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

def _write_dist_cont_patch(key_tier, key_eff, wdf, dist):
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
    path = Path(__file__).resolve().parent.parent / "PowerBI" / "SeedData" / "Mapping" / "DistCont_Patch_Proposed.csv"
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

def allocate_dist_primary(df, wdf, raw_sums):
    """Explode PO Type='Dist.' rows across chains by cont% and set _Chain on
    every row of `df` (Direct rows keep their own "Chain name for Dashboard").
    Returns (new_df, alloc_block) where alloc_block carries the full
    reconciliation/QC payload for the dashboard, or (df-with-_Chain, None)
    when the file has no PO Type column or no cont sheet was found."""
    chain_col = "Chain name for Dashboard" if "Chain name for Dashboard" in df.columns \
        else ("Chain name" if "Chain name" in df.columns else None)
    df["_ChainDash"] = df[chain_col].map(canon_chain) if chain_col else None
    if "PO Type" not in df.columns or wdf is None:
        df["_Chain"] = df["_ChainDash"]
        df.drop(columns=["_ChainDash"], inplace=True)
        return df, None

    is_dist = df["PO Type"].astype(str).str.strip().str.lower().isin(["dist.", "dist"])
    direct = df[~is_dist].copy()
    direct["_Chain"] = direct["_ChainDash"]
    dist = df[is_dist].copy()

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
    key_eff, key_tier = {}, {}
    for k in set(zip(dist["_st"], dist["_bl"], dist["_pm"])):
        st, bl, pm = k
        if pm is not None and k in wkeys:
            key_eff[k], key_tier[k] = pm, "exact"
        else:
            months = avail.get((st, bl))
            near = min(months, key=lambda m: abs(_pm_ord(m) - _pm_ord(pm))) if (months and pm) else None
            if near is not None and abs(_pm_ord(near) - _pm_ord(pm)) <= 3:
                key_eff[k], key_tier[k] = near, f"nearest {near}"
            else:
                key_eff[k], key_tier[k] = None, "unmapped"
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
    patch_rows, patch_path = _write_dist_cont_patch(key_tier, key_eff, wdf, dist)
    merged.drop(columns=["_st", "_bl", "_pm", "_pm_eff", "_tier", "_AllocChainRaw",
                         "_ChainDash", "_frac", "_ShipToRaw", "_BrandRaw"], inplace=True)
    direct.drop(columns=["_ChainDash"], inplace=True)
    merged["_IsDist"] = True
    direct["_IsDist"] = False
    out_df = pd.concat([direct, merged], ignore_index=True)

    alloc = {
        "dist_rows_in": int(len(orig)), "dist_rows_out": int(len(merged)),
        "rows_unmapped": int((~matched).sum()),
        "unmapped_nsv": r2(float(um["_NSV"].sum())),
        "rows_nearest": rows_nearest,
        "nearest_nsv": nearest_nsv,
        "missing_avg_tot_rows": int(orig["_AvgTot"].isna().sum()),
        "chains_allocated_to": int(merged.loc[matched, "_Chain"].nunique()),
        "cont_pct_bad_keys": cont_bad,   # raw cont% sums deviating from 100 (flagged BEFORE normalisation)
        "recon": recon, "qc_table": qc_rows[:400], "qc_table_total_rows": len(qc_rows),
        "missing_mapping": missing,
        "patch_rows": patch_rows, "patch_file": patch_path,
        "unit": "INR Lakh (values), units (qty)",
        "method": ("PO Type='Dist.' rows (blank \"Chain name for Dashboard\") are exploded across "
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
                   "permanent (this also fixes Power BI, whose query 41 reads only the xlsx)."),
    }
    return out_df, alloc

def detail_records_real(src, max_rows=20000):
    """Real 13-column detail_records from File 2 (article-wise primary).
    Looks for primary_article.xlsb/.xlsx in src. Returns None if absent, else
    (recs, channel_totals, coverage) where channel_totals is computed from the
    FULL un-capped data (so headline numbers like SIS are always exact) and
    recs is capped to the top `max_rows` groups BY ABSOLUTE VALUE (not a flat
    per-row threshold) to preserve total value coverage while bounding file size.
    A flat threshold silently guts small-ticket channels (e.g. SIS is made of
    many small line items) -- top-N-by-value keeps ~98%+ of total value at a
    fraction of the full row count.
    """
    f = None
    for name in ("primary_article.xlsb", "primary_article.xlsx",
                 "MT, Eb2B & SIS primary April_23 to May_26.xlsb",
                 "primary_article.csv"):
        if (src / name).exists():
            f = src / name; break
    if f is None:
        # also try concatenating monthly CSVs from Primary_Article_Monthly/
        monthly_dir = src / "Primary_Article_Monthly"
        monthly_csvs = sorted(monthly_dir.glob("primary_article_*.csv")) if monthly_dir.exists() else []
        if monthly_csvs:
            frames = [pd.read_csv(p, low_memory=False) for p in monthly_csvs]
            df_raw = pd.concat(frames, ignore_index=True)
            print(f"detail source: {len(monthly_csvs)} monthly CSVs from {monthly_dir.name} "
                  f"({len(df_raw)} rows)")
            df_raw.columns = [" ".join(str(c).split()) for c in df_raw.columns]
        else:
            return None
        df = df_raw
    elif f.suffix.lower() == ".csv":
        print(f"detail source: {f.name} (CSV)")
        df = pd.read_csv(f, low_memory=False)
        df.columns = [" ".join(str(c).split()) for c in df.columns]
    else:
        eng = "pyxlsb" if f.suffix.lower() == ".xlsb" else None
        # auto-detect the header row (source workbooks carry a blank first row or
        # -- in the current business format -- a reference/annotation row ABOVE the
        # real header, so require the actual data-column signature, not just any
        # row mentioning Month/FY). Old exports carry "Article Code"; the current
        # format doesn't, so accept "Ship To Name"+"EAN No." as the alternative.
        probe = pd.read_excel(f, sheet_name=0, header=None, nrows=8, engine=eng)
        hdr = 0
        for i in range(len(probe)):
            vals = {str(v).strip() for v in probe.iloc[i].tolist()}
            if {"Month", "FY"} <= vals and ({"Article Code"} <= vals or {"Ship To Name", "EAN No."} <= vals):
                hdr = i
                break
        print(f"detail source: {f.name} (header row {hdr})")
        df = pd.read_excel(f, sheet_name=0, header=hdr, engine=eng)
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
    df["_State"] = (df["State"].astype(str).str.strip() if "State" in df.columns else "")
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
    _wdf, _raw_sums = load_dist_cont_weights(src)
    df, alloc = allocate_dist_primary(df, _wdf, _raw_sums)
    n_shipto_as_chain = int(((df["_Chain"].astype(str).str.strip().str.lower()
                              == df["_CustName"].str.lower()) & (df["_CustName"] != "")).sum())
    if alloc is not None:
        alloc["rows_chain_equals_shipto"] = n_shipto_as_chain   # QC #17 -- must be 0

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
    _PREAGG_FY_TAGS = {"FY25", "FY26"}   # the FY window the Primary/Offtake workbooks cover
    fyx_primary = {}
    for _tag in sorted(set(df["_FY"].dropna().unique()) - _PREAGG_FY_TAGS, key=fy_start_year):
        fx = df[df["_FY"] == _tag]
        def _aggx(col, fx=fx):
            s = fx.groupby(col)["_NSV"].sum().sort_values(ascending=False)
            return [{"name": k, "nsv": r2(float(v))} for k, v in s.items() if k]
        mser = fx.groupby("_M")["_NSV"].sum()
        fyx_primary[_tag] = {
            "tag": _tag,
            "nsv": r2(float(fx["_NSV"].sum())),
            "mrp": r2(float(fx["_MRP"].sum())),
            "months_covered": [m for m in _ORDER if m in set(fx["_M"])],
            "monthly": [r2(float(mser.get(m, 0.0))) for m in _ORDER],
            "by_chain": _aggx("_Chain"), "by_zone": _aggx("_Zone"),
            "by_channel": _aggx("_Chan"), "by_brand": _aggx("_Brand"),
            "unit": "INR Lakh",
            "note": (f"EXACT {_tag} primary actuals from the FULL (uncapped) article-wise "
                     "primary, chain-allocated (Dist. rows split by secondary cont%). The "
                     "other report blocks' source workbook ends at Mar'26, so this FY lives "
                     "only here. MRP basis = 'Total MRP sales'."),
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
                "cust_code": r["_CustCode"], "ship_to": r["_CustName"],
                "ean": str(r["_EAN No."]), "article": r["_Description"],
                "art_mrp": r2(r["_ArtMRP"]), "brand": r["_Brand"],
                "category": r["_category"], "sub_category": r["_sub_category"],
                "range": r["_range"], "pack": r["_net_content"],
                "month": r["_M"], "fy": r["_FY"], "chain": r["_Chain"],
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
        recs.append({"Month":r["_M"],"FY":r["_FY"],"Channel":r["_Chan"],"Zone":r["_Zone"],"State":r["_State"],
            "Chain":r["_Chain"],"Brand":r["_Brand"],"Category":r["_category"],
            "SubCategory":r["_sub_category"],"Range":r["_range"],"PackSize":r["_net_content"],
            "Article":r["_Description"],"EAN":str(r["_EAN No."]),
            "NSV":r2(r["NSV"]),"MRP":r2(r["MRP"]),"Qty":int(r["Qty"])})
    print(f"detail rows: {rows_total} groups total -> kept top {len(recs)} "
          f"({coverage:.1f}% of total value)")
    return recs, channel_totals, sis_reconciliation, {
        "rows_total": rows_total, "rows_kept": len(recs),
        "value_coverage_pct": round(coverage, 1),
        "fyx_primary": fyx_primary}, tot, cm2, alloc

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
    ap.add_argument("--reliance-ba", action="store_true",
                    help="(re)build D.reliance_ba in an existing data.js from the monthly "
                         "store x article offtake extracts' 'Store Type' column, and remove "
                         "the BA-counter stream from the main Offtake aggregates so nothing "
                         "double-counts it. Leaves all other blocks untouched. Idempotent.")
    a = ap.parse_args()
    src = Path(a.src)
    _REPO_ROOT = Path(__file__).resolve().parent.parent

    # ---- lightweight path: Reliance BA counter isolation ----
    if a.reliance_ba:
        outp = Path(a.out)
        txt = outp.read_text()
        obj = json.loads(txt[txt.index("{"): txt.rstrip().rstrip(";").rindex("}") + 1])
        ba = load_reliance_ba(src)
        if ba is None:
            raise SystemExit(
                "No offtake extract in --src carries a 'Store Type' column, so BA "
                "counters cannot be separated from macro offtake. Needed: monthly "
                "offtake_store_article_<Mon>_<YY>.csv exports that retain the "
                "'Store Type' column ('Brand Counter' / 'Non Brand Counter').")
        off = obj.get("offtake")
        if off is None:
            raise SystemExit("data.js has no offtake block to isolate against.")
        # repair any month slot that was hand-patched to a {label: value} dict --
        # monthly_* must stay a flat numeric list positionally aligned to months_*
        for k in [k for k in off if re.match(r"^monthly_fy\d{2}$", k)]:
            if isinstance(off[k], list):
                off[k] = [(list(v.values())[0] if isinstance(v, dict) and len(v) == 1 else v)
                          for v in off[k]]
        apply_reliance_ba_isolation(off, ba)
        obj["reliance_ba"] = ba
        outp.write_text("window.DASH = " + json.dumps(obj, indent=1, ensure_ascii=False) + ";\n")
        print(f"reliance-ba: isolated {len(ba['months'])} month(s) {ba['months']}")
        for lo, aud in sorted(ba.get("isolation_audit", {}).items()):
            print(f"  {lo}: combined {aud['combined_before']} -> macro {aud['macro_after']} "
                  f"(BA {aud['ba_removed']} routed to Reliance BA tab)")
        for m in ba["months_not_isolable"]:
            print(f"  NOT ISOLABLE {m['month']} ({m['file']}): {m['reason']} "
                  f"-- {m['reliance_nsv']} L left in macro")
        print(f"  status: {ba['status']}")
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
        outp.write_text("window.DASH = " + json.dumps(obj, indent=1, ensure_ascii=False) + ";\n")
        print(f"detail-only: wrote {len(detail)} detail_records "
              f"({'REAL' if not meta['representative'] else 'representative'}) to {outp}"
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
        return

    # ---- lightweight path: refresh primary/pnl/insights with chain-level allocation ----
    if a.primary_only:
        outp = Path(a.out)
        txt = outp.read_text()
        obj = json.loads(txt[txt.index("{"): txt.rstrip().rstrip(";").rindex("}") + 1])
        raw = load_primary_v2(src)
        weights = load_chain_allocation_weights(src)
        allocated, qc = apply_chain_allocation(raw, weights)
        pdf, primary = primary_block(allocated)
        pnl = pnl_block(pdf, obj["promo"])
        insights = insights_block(primary, obj["offtake"], pnl, obj["universe"], obj["promo"])
        obj["primary"] = primary
        obj["pnl"] = pnl
        obj["insights"] = insights
        if qc is not None:
            obj["chain_allocation_qc"] = qc
        outp.write_text("window.DASH = " + json.dumps(obj, indent=1, ensure_ascii=False) + ";\n")
        print(f"primary-only: FY25 {primary['nsv_fy25']} / FY26 {primary['nsv_fy26']} (Lakh); "
              + (f"chain allocation coverage {qc['allocated_coverage_pct']}% of Distributor primary"
                 if qc else "no allocation file found -- chain tags left as-is"))
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
        outp.write_text("window.DASH = " + json.dumps(obj, indent=1, ensure_ascii=False) + ";\n")
        print(f"forecast-only: FY26 actual {forecast['fy26_actual']} / FY27 TY target "
              f"{forecast['fy27_forecast']} (Lakh) = Rs {forecast['fy27_forecast']/100:.2f} Cr")
        return

    # ---- lightweight path: merge new monthly article-level offtake extracts ----
    if a.offtake_patch:
        outp = Path(a.out)
        txt = outp.read_text()
        obj = json.loads(txt[txt.index("{"): txt.rstrip().rstrip(";").rindex("}") + 1])
        chain_month, zsm = load_offtake_article_files(src)
        if not chain_month:
            raise SystemExit(f"No .xlsb offtake extracts found in --src ({src}).")
        months_found = sorted({mo for mm in chain_month.values() for mo in mm},
                               key=lambda mo: (int(mo.split("-")[1]), _MON3_NUM[mo.split("-")[0]]))
        print(f"offtake source months found: {months_found}")
        patched = patch_offtake_new_months(obj["offtake"], chain_month, zsm)
        obj["offtake"] = patched
        outp.write_text("window.DASH = " + json.dumps(obj, indent=1, ensure_ascii=False) + ";\n")
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
        outp.write_text("window.DASH = " + json.dumps(obj, indent=1, ensure_ascii=False) + ";\n")
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

    data = {
        "meta": {
            "title": "Modern Trade Leadership Dashboard",
            "subtitle": "Honasa / Mamaearth — Primary, Offtake, P&L, Forecast & Market Share",
            "period": "FY 2024-25 vs FY 2025-26",
            "unit_note": "Values in INR Lakh in data; displayed in INR Crore where labelled (Cr = Lakh/100).",
            "source": "Primary, Chain Offtake Master, Universe MT, Promo Master (MT, FY24-26).",
        },
        "primary": primary, "offtake": offtake, "pnl": pnl,
        "universe": universe, "promo": promo, "forecast": forecast,
        "insights": insights,
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
    dg = dist_gap_block(src, _REPO_ROOT)
    if dg is not None:
        data["dist_gap"] = dg
        print(f"dist_gap: {dg['row_count']} products, window {dg['window_label']}, "
              f"total add-on {dg['total_addon_window']} L")
    print(f"detail_records: {len(detail)} rows "
          f"({'REAL' if not detail_meta['representative'] else 'representative'})"
          + (f"; TOT% blended = {tot['blended_tot_pct']}%" if tot else "")
          + (f"; CM2% = {cm2['cm2_pct']}%" if cm2 else ""))

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("window.DASH = " + json.dumps(data, indent=1, ensure_ascii=False) + ";\n")
    print("wrote", out, "bytes:", out.stat().st_size)

if __name__ == "__main__":
    main()
