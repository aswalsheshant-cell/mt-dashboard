"""Build the in-house TDP focus article list (NOT Nielsen TDP: no ACV %, no weighted distribution).

Rule agreed with the MT Channel Analyst Lead (2026-10-11):
  1. For each Chain x Brand, take the articles that together make 95% of that chain-brand's
     FY27 year-to-date offtake NSV (largest first; the article that crosses 95% is included).
  2. Also list every article whose first sale in our data is Jan-26 or later (offtake or primary).

Offtake: PowerBI/RawDataFolders/Offtake_Monthly, FY27 months, Reliance Brand Counter rows left out
(offtake de-duplication rule; primary is never filtered). Chain names use the same aliases as query 11.
Primary (MT channel only) is read only to find each article's first-sale month.
Limit: offtake history in the repo starts Apr-26 and primary starts Apr-25, so "new since Jan-26" means
no sale in primary or offtake from Apr-25 to Dec-25. Offtake-only history before Apr-26 is not in the repo.

Writes (aggregates only, no store rows):
  PowerBI/SeedData/Masters/TDP_Focus_Articles.csv
  PowerBI/SeedData/Masters/TDP_New_Articles_Since_Jan26.csv
Usage: python scripts/build_tdp_focus_articles.py
"""
import glob
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "PowerBI" / "RawDataFolders"
OUT = ROOT / "PowerBI" / "SeedData" / "Masters"
MON = {m: i for i, m in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}
CUT = 0.95
NEW_FROM = (2026, 1)

ALIASES = {  # keep in step with ChainAliases in PowerBI/PowerQuery/11_Fact_OfftakeSales.pq
    "dmart": "D-Mart", "h&g": "Health & Glow", "metro cnc": "Metro CNC", "sancus(rmt)": "RMT-Sancus",
    "vmm": "Vishal Mega Mart", "spencer": "Spencers", "frankros": "Frank Ross", "arambagh": "Arambagh",
    "ratnadeep": "Ratnadeep", "ratandeep": "Ratnadeep", "ratanadeep": "Ratnadeep", "sasta sundar": "SastaSundar",
    "ssl": "SastaSundar", "beauty & nutrie": "B&N", "wh-smith": "WH-Smith", "shoppers stop": "Shoppers Stop",
    "azorte": "Azorte", "trends": "Reliance Trends", "fsn": "Nykaa (FSN)", "mrl": "More Retail",
    "frankross": "Frank Ross", "sasta sunder": "SastaSundar", "baby shop": "Lifestyle Babyshop"}


def ean(v):
    s = str(v).strip()
    if s in ("", "nan", "None"):
        return ""
    return re.sub(r"\.0+$", "", s) if re.fullmatch(r"\d+(\.0+)?", s) else (str(int(float(s))) if re.fullmatch(r"[\d.]+e\+\d+", s.lower()) else s)


def ym(name):
    m = re.search(r"_([A-Za-z]{3})_(\d{2})\.csv$", name)
    return (2000 + int(m.group(2)), MON[m.group(1)])


def fy27(y, m):
    return (y, m) >= (2026, 4) and (y, m) <= (2027, 3)


def offtake():
    frames = []
    for f in sorted(glob.glob(str(RAW / "Offtake_Monthly" / "offtake_store_article_*.csv"))):
        y, m = ym(f)
        d = pd.read_csv(f, usecols=["Chain Name", "Store Type", "EAN", "Chain Article Description", "Brand", "NSV"], low_memory=False)
        d["y"], d["m"] = y, m
        frames.append(d)
    d = pd.concat(frames, ignore_index=True)
    k = d["Chain Name"].astype(str).str.strip()
    d["Chain"] = k.str.lower().map(ALIASES).fillna(k)
    d["EAN"] = d["EAN"].map(ean)
    d["NSV"] = pd.to_numeric(d["NSV"], errors="coerce").fillna(0)
    d["Brand"] = d["Brand"].astype(str).str.strip()
    counter = d["Store Type"].astype(str).str.strip().str.lower().eq("brand counter") & d["Chain"].str.lower().str.contains("reliance") \
        & d["Chain"].ne("Reliance Trends")
    return d[~counter].copy(), float(d[counter].NSV.sum())


def primary():
    frames = []
    for f in sorted(glob.glob(str(RAW / "Primary_Article_Monthly" / "primary_article_*.csv"))):
        y, m = ym(f)
        d = pd.read_csv(f, usecols=["Channel", "EAN No.", "Description", "brand", "Inv. Net value(LOC)"], low_memory=False)
        d = d[d["Channel"].astype(str).str.strip().str.upper() == "MT"]
        d = pd.DataFrame({"EAN": d["EAN No."].map(ean), "Description": d["Description"], "Brand": d["brand"],
                          "NSV": pd.to_numeric(d["Inv. Net value(LOC)"], errors="coerce").fillna(0) / 1e5, "y": y, "m": m})
        frames.append(d)
    return pd.concat(frames, ignore_index=True)


def main():
    o, counter_nsv = offtake()
    p = primary()
    cur = o[[fy27(y, m) for y, m in zip(o.y, o.m)]]
    n_months = cur[["y", "m"]].drop_duplicates().shape[0]
    desc = (cur.sort_values("NSV", ascending=False).drop_duplicates("EAN").set_index("EAN")["Chain Article Description"])

    g = cur[cur.EAN != ""].groupby(["Chain", "Brand", "EAN"], as_index=False).NSV.sum()
    g = g[g.NSV > 0].sort_values(["Chain", "Brand", "NSV"], ascending=[True, True, False])
    g["tot"] = g.groupby(["Chain", "Brand"]).NSV.transform("sum")
    g["cum"] = g.groupby(["Chain", "Brand"]).NSV.cumsum()
    g["rank"] = g.groupby(["Chain", "Brand"]).cumcount() + 1
    g["prev_share"] = (g.cum - g.NSV) / g.tot
    g["Share %"] = g.NSV / g.tot * 100
    g["Cum Share %"] = g.cum / g.tot * 100
    g["top95"] = g.prev_share < CUT

    # first sale per article, over offtake (Apr-26+) and primary MT (Apr-25+)
    a = pd.concat([o[o.NSV > 0][["EAN", "y", "m"]].assign(src="Offtake"), p[p.NSV > 0][["EAN", "y", "m"]].assign(src="Primary")])
    a = a[a.EAN != ""]
    a["ym"] = a.y * 100 + a.m
    first = a.groupby("EAN").ym.min()
    srcs = a.groupby("EAN").apply(lambda x: "+".join(sorted(x[x.ym == x.ym.min()].src.unique())), include_groups=False)
    new_eans = set(first[first >= NEW_FROM[0] * 100 + NEW_FROM[1]].index)
    g["First Sale"] = g.EAN.map(first).map(lambda v: "%d-%02d" % (v // 100, v % 100) if pd.notna(v) else "")
    g["new"] = g.EAN.isin(new_eans)
    sel = g[g.top95 | g.new].copy()
    sel["Selection"] = sel.apply(lambda r: "TOP95+NEW" if r.top95 and r.new else ("TOP95" if r.top95 else "NEW_SINCE_JAN26"), axis=1)
    sel["Article Description"] = sel.EAN.map(desc)
    sel[f"FY27 YTD NSV (Rs L)"] = sel.NSV.round(4)
    sel["Avg Monthly NSV (Rs L)"] = (sel.NSV / n_months).round(4)
    sel["Chain-Brand FY27 YTD NSV (Rs L)"] = sel.tot.round(4)
    sel["Rank in Chain-Brand"] = sel["rank"]
    sel["Share %"] = sel["Share %"].round(2)
    sel["Cum Share %"] = sel["Cum Share %"].round(2)
    cols = ["Chain", "Brand", "EAN", "Article Description", "Rank in Chain-Brand", "FY27 YTD NSV (Rs L)", "Avg Monthly NSV (Rs L)",
            "Share %", "Cum Share %", "Chain-Brand FY27 YTD NSV (Rs L)", "Selection", "First Sale"]
    OUT.mkdir(parents=True, exist_ok=True)

    # article-level new list (offtake and primary)
    pn = p[p.EAN.isin(new_eans)].groupby("EAN").agg(Primary_NSV=("NSV", "sum"), Brand=("Brand", "first"), Description=("Description", "first"))
    on = cur[cur.EAN.isin(new_eans)].groupby("EAN").agg(Offtake_NSV=("NSV", "sum"), Brand_o=("Brand", "first"))
    n = pd.DataFrame({"EAN": sorted(new_eans)}).set_index("EAN").join(pn).join(on)
    n["Brand"] = n.Brand.fillna(n.Brand_o)
    n["Article Description"] = n.Description.fillna(pd.Series(desc))
    n["First Sale"] = first.reindex(n.index).map(lambda v: "%d-%02d" % (v // 100, v % 100))
    n["First Sale Source"] = srcs.reindex(n.index)
    n["Primary NSV to Aug-26 (Rs L)"] = n.Primary_NSV.round(4)
    n["Offtake FY27 YTD NSV (Rs L)"] = n.Offtake_NSV.round(4)
    n["Evidence"] = n["First Sale Source"].map(lambda v: "Checked against primary from Apr-25" if "Primary" in str(v)
                                               else "Offtake only: no offtake before Apr-26 in repo, confirm with owner")
    n = n.reset_index().sort_values(["First Sale", "Brand"])
    ev = n.set_index("EAN")["Evidence"]
    sel["Newness Evidence"] = sel.EAN.map(ev).fillna("")
    sel[cols + ["Newness Evidence"]].to_csv(OUT / "TDP_Focus_Articles.csv", index=False, encoding="utf-8")
    n[["EAN", "Brand", "Article Description", "First Sale", "First Sale Source", "Evidence", "Primary NSV to Aug-26 (Rs L)", "Offtake FY27 YTD NSV (Rs L)"]] \
        .to_csv(OUT / "TDP_New_Articles_Since_Jan26.csv", index=False, encoding="utf-8")

    tot = float(cur.NSV.sum())
    print("FY27 months: %d  offtake ex Brand Counter: %.2f L  (Brand Counter left out: %.2f L)" % (n_months, tot, counter_nsv))
    print("chain-brand pairs: %d  focus rows: %d  (TOP95 %d, NEW only %d)" % (
        g.groupby(["Chain", "Brand"]).ngroups, len(sel), int(sel.top95.sum()), int((~sel.top95).sum())))
    print("share of FY27 YTD NSV covered by focus rows: %.2f%%" % (sel.NSV.sum() / g.NSV.sum() * 100))
    print("new articles since Jan-26: %d (offtake-only, unconfirmed: %d)" % (len(n), int((n.Evidence.str.startswith("Offtake only")).sum())))


if __name__ == "__main__":
    main()
