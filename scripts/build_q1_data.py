#!/usr/bin/env python3
"""
Build the Q1 FY26-27 data layer for the MT dashboard.

Consumes the leadership-shared planning files:
  - MT_Forecast_with_Regional_allocation (July'26): article x region x category
    unit forecast, with FC vs Consensus.
  - MT Promotion Apr'26 / May'26 / June'26: the Q1 FY26-27 consumer-promo
    calendar (article x chain x offer depth).

Emits ``dashboard/data_q1.js`` (window.DASHQ) with:
  - category   : top-95% contribution Pareto + pack-wise mix (forecast basis)
  - forecast   : regional allocation, category split, FC vs Consensus, top SKUs,
                 and a chain-wise allocation (forecast split to chains on their
                 trailing offtake share from the main dataset).
  - promo      : Q1 (Apr-Jun) offers by month / chain / category / pack / brand
                 / depth band, plus a chain x category coverage matrix.
  - distribution: GAP vs non-GAP article distribution by chain & category, where
                 GAP = the actively-forecasted (planned) portfolio. This is a
                 transparent proxy; swap in an official GAP master to refine.

Usage:
  python build_q1_data.py --src <scratchpad-dir> --main dashboard/data.js \
      --out dashboard/data_q1.js
"""
from __future__ import annotations
import argparse, json, math, re
from pathlib import Path
import pandas as pd

BRAND_MAP = {"me": "Mamaearth", "mamaearth": "Mamaearth", "tdc": "The Derma Co",
             "the derma co.": "The Derma Co", "the derma co": "The Derma Co",
             "aq": "Aqualogica", "aqualogica": "Aqualogica", "bblunt": "BBlunt",
             "dr. sheth's": "Dr. Sheth's", "staze": "Staze"}
CAT_MAP = {"fragrances": "Fragrance", "fragrance": "Fragrance", "hair care": "Hair",
           "hair colour": "Hair Colour", "color care": "Color Care", "combo": "Combo",
           "styling products": "Styling"}
KNOWN_BRANDS = {"mamaearth", "the derma co.", "the derma co", "aqualogica", "bblunt", "dr. sheth's"}

CHAIN_ALIASES = [
    ("Apollo", ["apollo", "apollo healthco"]),
    ("Reliance Retail", ["reliance retail", "reliance retail limited", "reliance retail ltd.",
                          "reliance", "rrl"]),
    ("Dmart", ["dmart", "d-mart", "d mart"]),
    ("Nykaa (FSN)", ["fsn", "nykaa ss(fsn)", "nykaa"]),
    ("Wellness Forever", ["wellness forever"]),
    ("H&G", ["h&g", "hng", "h and g"]),
    ("Lulu", ["lulu"]),
    ("Metro C&C", ["metro cnc", "metro c&c", "metro", "metro c & c"]),
    ("More Retail", ["more", "more retail"]),
    ("RMT-Sancus", ["rmt-sancus", "sancus(rmt)", "sancus", "rmt-delhi", "rmt delhi"]),
    ("Walmart", ["walmart cnc", "walmart", "wal-mart", "walmart c&c"]),
    ("VMM", ["vmm"]),
    ("Spencer", ["spencer", "spencers"]),
    ("Guardian", ["guardian", "gaurdian"]),
    ("Trent", ["trent"]),
    ("V-Mart", ["v-mart", "v mart east", "vmart"]),
    ("Ratnadeep", ["ratnadeep", "ratandeep"]),
    ("Sasta Sundar", ["sasta sundar", "sasta sunder", "ssl"]),
    ("Frankross", ["frankross", "frankros"]),
    ("Arambagh", ["arambagh", "aarambagh", "aarambagh food mart"]),
    ("WH-Smith", ["wh-smith"]),
    ("B&N", ["b&n", "beauty & nutire", "beauty and nutrie"]),
    ("Apna Mart", ["apna mart"]),
    ("Sumo Save", ["sumo save", "sumosave"]),
    ("Deal Share", ["deal share"]),
    ("Sohum Shoppe", ["sohum shoppe", "sohum"]),
    ("Lifestyle", ["lifestyle"]),
]
_AL = {a: c for c, al in CHAIN_ALIASES for a in al}

def canon_chain(x):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return None
    k = str(x).replace("\xa0", " ").strip()
    return _AL.get(k.lower(), k)

def canon_brand(x):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return None
    return BRAND_MAP.get(str(x).strip().lower(), str(x).strip())

def canon_cat(x):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return None
    s = str(x).strip()
    if s.lower() in KNOWN_BRANDS:        # June file sometimes puts brand in cat col
        return None
    return CAT_MAP.get(s.lower(), s)

def parse_pack(name):
    m = re.search(r"(\d+(?:\.\d+)?)\s*(ml|gm|g|kg|l)\b", str(name), re.I)
    if not m:
        return None
    v, u = float(m.group(1)), m.group(2).lower()
    if u == "gm":
        u = "g"
    return f"{int(v) if v==int(v) else v}{u}"

def pack_band(pack):
    if not isinstance(pack, str) or not pack:
        return None
    m = re.match(r"([\d.]+)(ml|g|kg|l)", pack)
    if not m:
        return None
    v = float(m.group(1))
    if m.group(2) in ("kg", "l"):
        v *= 1000
    if v <= 50:
        return "≤50"
    if v <= 100:
        return "51-100"
    if v <= 200:
        return "101-200"
    if v <= 300:
        return "201-300"
    if v <= 400:
        return "301-400"
    return "400+"

def depth(x):
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
        return float(m.group(1)) / 100
    try:
        v = float(s)
        if 0 < v <= 1:
            return v
        if 1 < v <= 100:
            return v / 100
    except Exception:
        pass
    return None

def r2(x, n=2):
    try:
        if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
            return None
        return round(float(x), n)
    except Exception:
        return None

# --------------------------------------------------------------------------
def load_forecast(src):
    fc = pd.read_excel(src / "forecast_q1.xlsx", header=2)
    fc.columns = [str(c).strip() for c in fc.columns]
    fc = fc[fc["Brand"].notna()].copy()
    fccol = [c for c in fc.columns if "FC" in c and "Consensus" not in c][0]
    concol = [c for c in fc.columns if "Consensus" in c][0]
    fc["fc"] = pd.to_numeric(fc[fccol], errors="coerce").fillna(0)
    fc["cons"] = pd.to_numeric(fc[concol], errors="coerce").fillna(0)
    for r in ["NORTH", "SOUTH", "West", "EAST"]:
        fc[r] = pd.to_numeric(fc[r], errors="coerce").fillna(0)
    fc["brand"] = fc["Brand"].map(canon_brand)
    fc["cat"] = fc["Category"].map(canon_cat)
    fc["pack"] = fc["Product Name"].map(parse_pack)
    fc["band"] = fc["pack"].map(pack_band)
    return fc

def forecast_block(fc, chain_shares):
    total = fc["fc"].sum()
    by_region = [{"name": n, "fc": r2(fc[c].sum())} for n, c in
                 [("North", "NORTH"), ("South", "SOUTH"), ("West", "West"), ("East", "EAST")]]
    cat = fc.groupby("cat")["fc"].sum().sort_values(ascending=False)
    by_category = [{"name": k, "fc": r2(v)} for k, v in cat.items() if k]
    brand = fc.groupby("brand")["fc"].sum().sort_values(ascending=False)
    by_brand = [{"name": k, "fc": r2(v)} for k, v in brand.items() if k]
    top = fc.sort_values("fc", ascending=False).head(15)
    top_skus = [{"name": str(r["Product Name"])[:48], "brand": r["brand"], "cat": r["cat"],
                 "fc": r2(r["fc"]), "cons": r2(r["cons"])} for _, r in top.iterrows()]
    # chain-wise allocation: split FC total on trailing offtake chain share
    by_chain = [{"name": c, "fc": r2(total * s)} for c, s in chain_shares[:12]]
    return {"total": r2(total), "total_cons": r2(fc["cons"].sum()),
            "by_region": by_region, "by_category": by_category, "by_brand": by_brand,
            "top_skus": top_skus, "by_chain": by_chain,
            "unit_note": "Forecast in units (July'26 plan, regional allocation file)."}

def category_pack_block(fc):
    cat = fc.groupby("cat")["fc"].sum().sort_values(ascending=False)
    cat = cat[cat.index.notna()]
    tot = cat.sum()
    items, cum = [], 0.0
    p95 = None
    for k, v in cat.items():
        cum += v
        cump = cum / tot * 100
        items.append({"name": k, "fc": r2(v), "share": r2(v / tot * 100, 1), "cum": r2(cump, 1)})
        if p95 is None and cump >= 95:
            p95 = len(items)
    pk = fc.groupby("pack")["fc"].sum().sort_values(ascending=False)
    pk = pk[pk.index.notna()].head(15)
    packs = [{"name": k, "fc": r2(v), "share": r2(v / tot * 100, 1)} for k, v in pk.items()]
    band = fc.groupby("band")["fc"].sum()
    border = ["≤50", "51-100", "101-200", "201-300", "301-400", "400+"]
    bands = [{"name": b, "fc": r2(band.get(b, 0))} for b in border if band.get(b, 0) > 0]
    return {"basis": "July'26 forecast (units)", "categories": items, "pareto95_count": p95,
            "n_categories": len(items), "packs": packs, "bands": bands,
            "top_pack": packs[0]["name"] if packs else None}

# --------------------------------------------------------------------------
def load_promos(src):
    rows = []
    j = pd.read_excel(src / "promo_jun.xlsx", sheet_name="June'26", header=0)
    j.columns = [str(c).strip() for c in j.columns]
    for _, r in j.iterrows():
        if pd.isna(r.get("Chain")):
            continue
        rows.append(dict(month="Apr-Jun", mlabel="Jun", chain=canon_chain(r.get("Chain")),
                         brand=canon_brand(r.get("Brand")), cat=canon_cat(r.get("Category")),
                         offer=depth(r.get("Consumer Promo")), desc=r.get("Article"), ean=r.get("EAN")))
    m = pd.read_excel(src / "promo_may.xlsx", sheet_name="May'26", header=0)
    m.columns = [str(c).strip() for c in m.columns]
    for _, r in m.iterrows():
        if pd.isna(r.get("Chain Name")):
            continue
        rows.append(dict(month="Apr-Jun", mlabel="May", chain=canon_chain(r.get("Chain Name")),
                         brand=canon_brand(r.get("Brand")), cat=canon_cat(r.get("Category")),
                         offer=depth(r.get("Offer to consumer")), desc=r.get("Description"),
                         ean=r.get("EAN Code")))
    a1 = pd.read_excel(src / "promo_apr.xlsx", sheet_name="MT CHain", header=0)
    a1.columns = [str(c).strip() for c in a1.columns]
    for _, r in a1.iterrows():
        if pd.isna(r.get("Chain Name")):
            continue
        rows.append(dict(month="Apr-Jun", mlabel="Apr", chain=canon_chain(r.get("Chain Name")),
                         brand=canon_brand(r.get("Brand")), cat=None,
                         offer=depth(r.get("Consumer Offer")), desc=r.get("Article Desc"), ean=None))
    a2 = pd.read_excel(src / "promo_apr.xlsx", sheet_name="Reliance & C&C", header=1)
    a2.columns = [str(c).strip() for c in a2.columns]
    for _, r in a2.iterrows():
        if pd.isna(r.get("Chain name")):
            continue
        rows.append(dict(month="Apr-Jun", mlabel="Apr", chain=canon_chain(r.get("Chain name")),
                         brand=canon_brand(r.get("Brand")), cat=None,
                         offer=depth(r.get("Offer Support")), desc=r.get("Article Name"), ean=None))
    df = pd.DataFrame(rows)
    df["pack"] = df["desc"].map(parse_pack)
    df["band"] = df["pack"].map(pack_band)
    return df

def promo_block(df):
    out = {"total": int(len(df)),
           "avg_depth": r2(df["offer"].mean() * 100, 1),
           "n_chains": int(df["chain"].nunique())}
    out["by_month"] = [{"name": k, "n": int(v)} for k, v in
                       df["mlabel"].value_counts().reindex(["Apr", "May", "Jun"]).dropna().items()]
    g = df.groupby("chain")
    out["by_chain"] = sorted([{"name": k, "n": int(len(d)), "depth": r2(d["offer"].mean() * 100, 1)}
                              for k, d in g if k], key=lambda x: -x["n"])[:15]
    cat = df[df["cat"].notna()].groupby("cat")
    out["by_category"] = sorted([{"name": k, "n": int(len(d)), "depth": r2(d["offer"].mean() * 100, 1)}
                                 for k, d in cat], key=lambda x: -x["n"])[:10]
    real = {"Mamaearth", "The Derma Co", "Aqualogica", "BBlunt", "Dr. Sheth's", "Staze"}
    bc = {}
    for b in df["brand"].dropna():
        key = b if b in real else "Other"
        bc[key] = bc.get(key, 0) + 1
    out["by_brand"] = sorted([{"name": k, "n": v} for k, v in bc.items()],
                             key=lambda x: (x["name"] == "Other", -x["n"]))
    pk = df[df["pack"].notna()].groupby("pack").size().sort_values(ascending=False).head(12)
    out["by_pack"] = [{"name": k, "n": int(v)} for k, v in pk.items()]
    # depth bands
    bands = {"≤10%": 0, "11-20%": 0, "21-35%": 0, "36-50%": 0, ">50%": 0}
    for v in df["offer"].dropna():
        p = v * 100
        if p <= 10:
            bands["≤10%"] += 1
        elif p <= 20:
            bands["11-20%"] += 1
        elif p <= 35:
            bands["21-35%"] += 1
        elif p <= 50:
            bands["36-50%"] += 1
        else:
            bands[">50%"] += 1
    out["depth_bands"] = [{"name": k, "n": v} for k, v in bands.items()]
    return df, out

# --------------------------------------------------------------------------
def distribution_block(fc, promo):
    """GAP = articles in the active forecast plan (by EAN). Classify the Q1 promo
    article lines (that carry an EAN) as GAP vs non-GAP and roll up by chain."""
    gap_eans = set(str(int(e)) for e in fc["EAN Code"].dropna()
                   if str(e).replace(".", "").isdigit())
    p = promo[promo["ean"].notna()].copy()
    def norm(e):
        try:
            return str(int(float(e)))
        except Exception:
            return None
    p["ean_n"] = p["ean"].map(norm)
    p = p[p["ean_n"].notna()]
    p["is_gap"] = p["ean_n"].isin(gap_eans)
    by_chain = []
    for ch, d in p.groupby("chain"):
        if not ch:
            continue
        gap = int(d["is_gap"].sum())
        non = int((~d["is_gap"]).sum())
        by_chain.append({"name": ch, "gap": gap, "nongap": non,
                         "gap_pct": r2(gap / (gap + non) * 100, 0) if (gap + non) else None})
    by_chain = sorted(by_chain, key=lambda x: -(x["gap"] + x["nongap"]))[:15]
    cat = []
    for c, d in p[p["cat"].notna()].groupby("cat"):
        cat.append({"name": c, "gap": int(d["is_gap"].sum()), "nongap": int((~d["is_gap"]).sum())})
    cat = sorted(cat, key=lambda x: -(x["gap"] + x["nongap"]))
    return {"gap_articles": int(len(gap_eans)),
            "matched_lines": int(len(p)),
            "gap_lines": int(p["is_gap"].sum()),
            "nongap_lines": int((~p["is_gap"]).sum()),
            "by_chain": by_chain, "by_category": cat,
            "note": "GAP = articles in the active July'26 forecast plan, matched to Q1 promo "
                    "lines by EAN (May & Jun carry EAN). Swap in an official GAP/must-stock "
                    "master to refine."}

# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=".")
    ap.add_argument("--main", default="dashboard/data.js")
    ap.add_argument("--out", default="dashboard/data_q1.js")
    a = ap.parse_args()
    src = Path(a.src)

    # trailing chain shares from the main dataset (offtake FY26)
    txt = Path(a.main).read_text()
    main_data = json.loads(txt[txt.index("{"):txt.rindex("}") + 1])
    oc = main_data["offtake"]["by_chain"]
    tot = sum(c["fy26"] or 0 for c in oc) or 1
    shares = sorted([(c["name"], (c["fy26"] or 0) / tot) for c in oc], key=lambda x: -x[1])

    fc = load_forecast(src)
    forecast = forecast_block(fc, shares)
    category = category_pack_block(fc)
    promo_df, promo = promo_block(*[load_promos(src)])
    distribution = distribution_block(fc, promo_df)

    data = {
        "meta": {"period": "Q1 FY 2026-27 (Apr-Jun) · Forecast: July'26 plan",
                 "note": "Forecast values are in units; promo counts are offer lines."},
        "forecast": forecast, "category": category, "promo": promo, "distribution": distribution,
    }
    out = Path(a.out)
    out.write_text("window.DASHQ = " + json.dumps(data, indent=1, ensure_ascii=False) + ";\n")
    print("wrote", out, "bytes:", out.stat().st_size)
    print("forecast total units:", forecast["total"], "| pareto95 cats:", category["pareto95_count"],
          "| promo lines:", promo["total"], "| gap lines:", distribution["gap_lines"],
          "/ matched", distribution["matched_lines"])

if __name__ == "__main__":
    main()
