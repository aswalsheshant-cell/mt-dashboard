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
import argparse, csv, io, json, re, math
from pathlib import Path

import pandas as pd

# --------------------------------------------------------------------------
# Canonicalisation helpers
# --------------------------------------------------------------------------
MONTHS = ["Apr-24","May-24","Jun-24","Jul-24","Aug-24","Sep-24","Oct-24","Nov-24",
          "Dec-24","Jan-25","Feb-25","Mar-25","Apr-25","May-25","Jun-25","Jul-25",
          "Aug-25","Sep-25","Oct-25","Nov-25","Dec-25","Jan-26","Feb-26","Mar-26"]
FY25 = MONTHS[:12]   # Apr-24 .. Mar-25  == FY_24-25
FY26 = MONTHS[12:]   # Apr-25 .. Mar-26  == FY_25-26

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
CHAIN_ALIASES = [
    ("Apollo",            ["apollo", "apollo healthco"]),
    ("Reliance Retail",   ["reliance retail", "reliance retail limited", "reliance retail ltd.",
                            "reliance", "reliance ", "rrl", "metro-cnc-rrl"]),
    ("Dmart",             ["dmart", "d-mart", "d-mart ", "dmart "]),
    ("Nykaa (FSN)",       ["fsn", "nykaa ss(fsn)", "nykaa"]),
    ("Wellness Forever",  ["wellness forever"]),
    ("H&G",               ["h&g", "hng", "h\\&g"]),
    ("Lulu",              ["lulu", "lulu "]),
    ("Metro C&C",         ["metro cnc", "metro c&c", "metro ", "metro-cnc-rrl"]),
    ("More Retail",       ["more", "more retail", "more "]),
    ("RMT-Sancus",        ["rmt-sancus", "sancus(rmt)", "sancus ", "rmt-delhi"]),
    ("Walmart",           ["walmart cnc", "walmart", "walmart ", "wal-mart"]),
    ("VMM",               ["vmm", "vmm "]),
    ("Spencer",           ["spencer"]),
    ("Guardian",          ["guardian", "gaurdian "]),
    ("Trent",             ["trent", "trent "]),
    ("V-Mart",            ["v-mart", "v mart east "]),
    ("Ratnadeep",         ["ratnadeep", "ratandeep"]),
    ("Sasta Sundar",      ["sasta sundar", "sasta sunder", "ssl"]),
    ("Frankross",         ["frankross", "frankros"]),
    ("Arambagh",          ["arambagh", "aarambagh food mart ", "arambagh food mart"]),
    ("WH-Smith",          ["wh-smith"]),
    ("B&N",               ["b&n", "beauty & nutire", "b\\&n"]),
    ("Apna Mart",         ["apna mart", "apna mart "]),
    ("Sumo Save",         ["sumo save", "sumosave"]),
    ("Deal Share",        ["deal share", "deal share "]),
    ("Sohum Shoppe",      ["sohum shoppe", "sohum"]),
    ("Lifestyle",         ["lifestyle", "lifestyle "]),
    ("Trent/Westside",    ["trends"]),
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

def primary_block(df):
    out = {}
    fy = df.groupby("FY")["NSV"].sum()
    out["nsv_fy25"] = r2(fy.get("FY_24-25", 0))
    out["nsv_fy26"] = r2(fy.get("FY_25-26", 0))
    out["yoy"] = r2((out["nsv_fy26"] / out["nsv_fy25"] - 1) * 100) if out["nsv_fy25"] else None
    gross = df.groupby("FY")["MRP value"].sum()
    out["mrp_fy25"], out["mrp_fy26"] = r2(gross.get("FY_24-25", 0)), r2(gross.get("FY_25-26", 0))
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
    out["monthly_fy25"] = [r2(piv.get("FY_24-25", pd.Series()).get(i)) for i in range(12)]
    out["monthly_fy26"] = [r2(piv.get("FY_25-26", pd.Series()).get(i)) for i in range(12)]

    # by channel
    ch = df.pivot_table(index="channel", columns="FY", values="NSV", aggfunc="sum").fillna(0)
    out["by_channel"] = [{"name": k, "fy25": r2(ch.loc[k].get("FY_24-25", 0)),
                          "fy26": r2(ch.loc[k].get("FY_25-26", 0))}
                         for k in ch.index]
    # by zone (MT focus but keep all)
    zn = df.pivot_table(index="zone", columns="FY", values="NSV", aggfunc="sum").fillna(0)
    out["by_zone"] = sorted([{"name": k, "fy25": r2(zn.loc[k].get("FY_24-25", 0)),
                              "fy26": r2(zn.loc[k].get("FY_25-26", 0))} for k in zn.index if k],
                            key=lambda d: -(d["fy26"] or 0))
    # by brand
    br = df.pivot_table(index="brand", columns="FY", values="NSV", aggfunc="sum").fillna(0)
    out["by_brand"] = sorted([{"name": k, "fy25": r2(br.loc[k].get("FY_24-25", 0)),
                               "fy26": r2(br.loc[k].get("FY_25-26", 0))} for k in br.index if k],
                             key=lambda d: -(d["fy26"] or 0))
    # by chain
    cn = df.pivot_table(index="chain", columns="FY", values="NSV", aggfunc="sum").fillna(0)
    chains = []
    for k in cn.index:
        if not k:
            continue
        a, b = cn.loc[k].get("FY_24-25", 0), cn.loc[k].get("FY_25-26", 0)
        chains.append({"name": k, "fy25": r2(a), "fy26": r2(b),
                       "yoy": r2((b / a - 1) * 100) if a else None})
    out["by_chain"] = sorted(chains, key=lambda d: -(d["fy26"] or 0))
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
    # ---- chain-wise monthly (Sheet2) ----
    s2 = t[: t.index("Sheet3")]
    body = s2[s2.index("Grand Total ") + len("Grand Total "):]
    rows = re.split(r"(?<=\d) (?=[A-Za-z])", body)
    chains = {}
    for r in rows:
        parts = r.split(",")
        name = parts[0].strip().replace("\\&", "&")
        if name.lower() == "grand total" or len(parts) < 26:
            continue
        vals = [_num(v) for v in parts[1:26]]
        chains[name] = {"months": {MONTHS[i]: vals[i] for i in range(24)}, "total": vals[24]}
    # ---- zone/state quarterly (Sheet3) ----
    s3 = t[t.index("Sheet3"):]
    h = s3.index("Q1-24")
    start = s3.index("Grand Total", h) + len("Grand Total")
    end = s3.index("Brand Counter") if "Brand Counter" in s3 else len(s3)
    rows3 = re.split(r"(?<=\d) (?=[A-Za-z,\"])", s3[start:end])
    qcols = ["Q1-24","Q1-25","Q2-24","Q2-25","Q3-24","Q3-25","Q4-24","Q4-25"]
    zs, cur = [], None
    for r in rows3:
        r = r.strip()
        if not r:
            continue
        rd = next(csv.reader(io.StringIO(r)))
        if len(rd) < 11:
            continue
        zone = (rd[0].strip() or cur)
        cur = zone
        if rd[1].strip().lower() == "" or zone.lower() == "grand total":
            continue
        zs.append({"zone": zone, "state": rd[1].strip().replace("\\&", "&"),
                   "q": {qcols[i]: _num(rd[2 + i]) for i in range(8)}, "total": _num(rd[10])})
    return chains, zs

def offtake_block(chains, zs):
    out = {}
    def fy_sum(mn, fy):
        return sum(v for k, v in mn.items() if k in fy and v)
    rows = []
    for name, d in chains.items():
        c = canon_chain(name)
        a, b = fy_sum(d["months"], FY25), fy_sum(d["months"], FY26)
        rows.append({"name": c, "raw": name, "fy25": r2(a), "fy26": r2(b),
                     "yoy": r2((b / a - 1) * 100) if a else None, "total": r2(d["total"])})
    out["by_chain"] = sorted(rows, key=lambda d: -(d["fy26"] or 0))
    out["total_fy25"] = r2(sum(x["fy25"] or 0 for x in rows))
    out["total_fy26"] = r2(sum(x["fy26"] or 0 for x in rows))
    out["yoy"] = r2((out["total_fy26"] / out["total_fy25"] - 1) * 100) if out["total_fy25"] else None
    out["n_chains"] = len(rows)
    # monthly aggregate trend
    agg = {m: 0.0 for m in MONTHS}
    for d in chains.values():
        for m, v in d["months"].items():
            if v:
                agg[m] += v
    out["months"] = MONTHS
    out["monthly"] = [r2(agg[m]) for m in MONTHS]
    out["monthly_fy25"] = [r2(agg[m]) for m in FY25]
    out["monthly_fy26"] = [r2(agg[m]) for m in FY26]
    # zone roll-up YoY (sum quarters per year)
    zagg = {}
    for r in zs:
        z = canon_zone(r["zone"])
        y24 = sum(r["q"][k] or 0 for k in r["q"] if k.endswith("-24"))
        y25 = sum(r["q"][k] or 0 for k in r["q"] if k.endswith("-25"))
        d = zagg.setdefault(z, {"y24": 0.0, "y25": 0.0})
        d["y24"] += y24
        d["y25"] += y25
    out["by_zone"] = sorted([{"name": z, "fy25": r2(v["y24"]), "fy26": r2(v["y25"]),
                              "yoy": r2((v["y25"] / v["y24"] - 1) * 100) if v["y24"] else None}
                             for z, v in zagg.items()], key=lambda d: -(d["fy26"] or 0))
    # state YoY detail
    st = []
    for r in zs:
        y24 = sum(r["q"][k] or 0 for k in r["q"] if k.endswith("-24"))
        y25 = sum(r["q"][k] or 0 for k in r["q"] if k.endswith("-25"))
        st.append({"zone": canon_zone(r["zone"]), "state": r["state"], "fy25": r2(y24), "fy26": r2(y25),
                   "yoy": r2((y25 / y24 - 1) * 100) if y24 else None})
    out["by_state"] = sorted(st, key=lambda d: -(d["fy26"] or 0))
    return out

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
# P&L (chain-wise gross-to-net + trade spend)
# --------------------------------------------------------------------------
def pnl_block(pdf, promo):
    """Per-chain trade P&L bridge from real primary data:
       Gross MRP value  ->  trade discount (MRP-NSV)  ->  Net NSV.
       Plus promo intensity from the promo calendar. COGS is not in source,
       so this is a gross-to-net trade contribution view, not a full P&L."""
    g = pdf[pdf["FY"] == "FY_25-26"].groupby("chain").agg(
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
    return {"by_chain": rows,
            "total_mrp": r2(tot_mrp), "total_nsv": r2(tot_nsv),
            "total_discount": r2(tot_mrp - tot_nsv),
            "blended_discount_pct": r2((tot_mrp - tot_nsv) / tot_mrp * 100, 1) if tot_mrp else None}

# --------------------------------------------------------------------------
# FORECAST  (seasonally-adjusted, from offtake monthly history)
# --------------------------------------------------------------------------
def forecast_block(off):
    series = off["monthly"]  # 24 months Apr-24..Mar-26
    fy25, fy26 = series[:12], series[12:]
    # seasonal index from FY26 (latest full year) normalised to its mean
    mean26 = sum(v or 0 for v in fy26) / 12 or 1
    seasonal = [(v or 0) / mean26 for v in fy26]
    # YoY growth on the trailing year drives the level
    g = (sum(v or 0 for v in fy26) / (sum(v or 0 for v in fy25) or 1)) - 1
    g = max(min(g, 0.6), 0.0)  # clamp to a sane planning band
    base_month = mean26 * (1 + g)
    flabels = ["Apr-26","May-26","Jun-26","Jul-26","Aug-26","Sep-26",
               "Oct-26","Nov-26","Dec-26","Jan-27","Feb-27","Mar-27"]
    fc = [r2(base_month * seasonal[i]) for i in range(12)]
    return {"hist_labels": off["months"], "hist": series,
            "fc_labels": flabels, "fc": fc,
            "fy26_actual": r2(sum(v or 0 for v in fy26)),
            "fy27_forecast": r2(sum(fc)),
            "growth_assumption_pct": r2(g * 100, 1),
            "method": "Seasonally-indexed run-rate: FY25-26 monthly seasonality applied "
                      "to a forward base grown at the realised offtake YoY rate (clamped 0-60%)."}

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
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=".")
    ap.add_argument("--out", default="../dashboard/data.js")
    a = ap.parse_args()
    src = Path(a.src)

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
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("window.DASH = " + json.dumps(data, indent=1, ensure_ascii=False) + ";\n")
    print("wrote", out, "bytes:", out.stat().st_size)

if __name__ == "__main__":
    main()
