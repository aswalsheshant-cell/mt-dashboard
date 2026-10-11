"""Build the in-house TDP focus article list (NOT Nielsen TDP: no ACV %, no weighted distribution).

Rule agreed with the MT Channel Analyst Lead (2026-10-11):
  1. For each Chain x Brand, take the articles that together make 95% of that chain-brand's
     FY27 year-to-date offtake NSV (largest first; the article that crosses 95% is included).
  2. Also list every article whose first sale in our data is Jan-26 or later (offtake or primary).
  3. NPI from offtake only (owner, 2026-10-11): an article with no offtake in that chain in the Apr-26 baseline that first shows up there later.

Offtake: PowerBI/RawDataFolders/Offtake_Monthly, FY27 months, Reliance Brand Counter rows left out
(offtake de-duplication rule; primary is never filtered). Chain names use the same aliases as query 11.
Primary (MT channel only) is read only to find each article's first-sale month.
Limit: offtake history in the repo starts Apr-26 and primary starts Apr-25, so "new since Jan-26" means
no sale in primary or offtake from Apr-25 to Dec-25. Offtake-only history before Apr-26 is not in the repo.

Writes (aggregates only, no store rows):
  PowerBI/SeedData/Masters/TDP_Focus_Articles.csv
  PowerBI/SeedData/Masters/TDP_New_Articles_Since_Jan26.csv
  dashboard/tdp_focus.js  (same rows for the HTML dashboard)
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

    # 1) article-level first sale over offtake (Apr-26+) and primary MT (Apr-25+)
    a = pd.concat([o[o.NSV > 0][["EAN", "y", "m"]].assign(src="Offtake"), p[p.NSV > 0][["EAN", "y", "m"]].assign(src="Primary")])
    a = a[a.EAN != ""]
    a["ym"] = a.y * 100 + a.m
    first = a.groupby("EAN").ym.min()
    srcs = a.groupby("EAN").apply(lambda x: "+".join(sorted(x[x.ym == x.ym.min()].src.unique())), include_groups=False)
    new_eans = set(first[first >= NEW_FROM[0] * 100 + NEW_FROM[1]].index)
    fmt = lambda v: "%d-%02d" % (v // 100, v % 100) if pd.notna(v) else ""
    # primary history reaches back to Apr-25, so a primary-confirmed article is truly new since Jan-26
    prim_new = {e for e in new_eans if "Primary" in srcs[e]}

    # 2) NPI from offtake only: the article had no offtake in that chain in the baseline month (Apr-26)
    #    and first shows up there later (May-26 onwards). Needs no primary data.
    ov = o[(o.NSV > 0) & (o.EAN != "")].copy()
    ov["ym"] = ov.y * 100 + ov.m
    chain_first = ov.groupby(["Chain", "EAN"]).ym.min().rename("chain_first").reset_index()
    BASE = 202604
    g = g.merge(chain_first, on=["Chain", "EAN"], how="left")
    base_chains = set(ov[ov.ym == BASE].Chain)  # a chain with no Apr-26 offtake has no baseline: every article would look new
    g["npi_chain"] = (g.chain_first > BASE) & g.Chain.isin(base_chains)
    g["First Sale"] = g.EAN.map(first).map(fmt)
    g["First Month in Chain"] = g.chain_first.map(fmt)
    g["prim_new"] = g.EAN.isin(prim_new)
    sel = g[g.top95 | g.prim_new | g.npi_chain].copy()

    def label(r):
        parts = []
        if r.top95:
            parts.append("TOP95")
        if r.prim_new:
            parts.append("NEW_SINCE_JAN26")
        if r.npi_chain:
            parts.append("NPI_NEW_TO_CHAIN")
        return "+".join(parts)

    sel["Selection"] = sel.apply(label, axis=1)
    sel["Newness Evidence"] = sel.apply(lambda r: "; ".join(x for x in [
        "Primary history from Apr-25 shows first sale %s" % r["First Sale"] if r.prim_new else "",
        "Offtake: absent in this chain in Apr-26, first seen %s" % r["First Month in Chain"] if r.npi_chain else ""] if x), axis=1)
    sel["Article Description"] = sel.EAN.map(desc)
    sel["FY27 YTD NSV (Rs L)"] = sel.NSV.round(4)
    sel["Avg Monthly NSV (Rs L)"] = (sel.NSV / n_months).round(4)
    sel["Chain-Brand FY27 YTD NSV (Rs L)"] = sel.tot.round(4)
    sel["Rank in Chain-Brand"] = sel["rank"]
    sel["Share %"] = sel["Share %"].round(2)
    sel["Cum Share %"] = sel["Cum Share %"].round(2)
    cols = ["Chain", "Brand", "EAN", "Article Description", "Rank in Chain-Brand", "FY27 YTD NSV (Rs L)", "Avg Monthly NSV (Rs L)",
            "Share %", "Cum Share %", "Chain-Brand FY27 YTD NSV (Rs L)", "Selection", "First Sale", "First Month in Chain", "Newness Evidence"]
    OUT.mkdir(parents=True, exist_ok=True)
    sel[cols].to_csv(OUT / "TDP_Focus_Articles.csv", index=False, encoding="utf-8")

    # article-level new list: primary-confirmed, or new to at least one chain in offtake
    npi_eans = set(g[g.npi_chain].EAN)
    keep = sorted(prim_new | npi_eans)
    pn = p[p.EAN.isin(keep)].groupby("EAN").agg(Primary_NSV=("NSV", "sum"), Brand=("Brand", "first"), Description=("Description", "first"))
    on = cur[cur.EAN.isin(keep)].groupby("EAN").agg(Offtake_NSV=("NSV", "sum"), Brand_o=("Brand", "first"))
    nchain = g[g.npi_chain].groupby("EAN").Chain.nunique()
    n = pd.DataFrame({"EAN": keep}).set_index("EAN").join(pn).join(on)
    n["Brand"] = n.Brand.fillna(n.Brand_o)
    n["Article Description"] = n.Description.fillna(pd.Series(desc))
    n["First Sale"] = first.reindex(n.index).map(fmt)
    n["Type"] = [("NEW_SINCE_JAN26" if e in prim_new else "") + ("+" if e in prim_new and e in npi_eans else "") + ("NPI_NEW_TO_CHAIN" if e in npi_eans else "") for e in n.index]
    n["Chains New To"] = nchain.reindex(n.index).fillna(0).astype(int)
    n["Primary NSV to Aug-26 (Rs L)"] = n.Primary_NSV.round(4)
    n["Offtake FY27 YTD NSV (Rs L)"] = n.Offtake_NSV.round(4)
    n = n.reset_index().sort_values(["Type", "First Sale", "Brand"])
    n[["EAN", "Brand", "Article Description", "Type", "First Sale", "Chains New To", "Primary NSV to Aug-26 (Rs L)", "Offtake FY27 YTD NSV (Rs L)"]] \
        .to_csv(OUT / "TDP_New_Articles_Since_Jan26.csv", index=False, encoding="utf-8")
    unconfirmed = len(new_eans - prim_new - npi_eans)

    # dashboard feed (aggregates only)
    import json
    rows = sel[cols].fillna("").to_dict("records")
    summ = (sel.groupby(["Chain"]).agg(articles=("EAN", "nunique"), nsv=("NSV", "sum")).round(2).reset_index().sort_values("nsv", ascending=False).to_dict("records"))
    feed = {"label": "In-house article focus list, not Nielsen TDP (no ACV %, no weighted distribution)", "period": "FY27 Apr-Aug 2026",
            "rule": "Top articles making 95% of each chain-brand FY27 YTD offtake NSV, plus articles new since Jan-26 (primary history) and articles new to a chain after Apr-26 (offtake)",
            "months": int(n_months), "columns": cols, "rows": [[r[c] for c in cols] for r in rows], "by_chain": summ,
            "counts": {"pairs": int(g.groupby(["Chain", "Brand"]).ngroups), "rows": len(rows), "top95": int(sel.top95.sum()),
                       "new_jan26": int(sel.prim_new.sum()), "npi_chain": int(sel.npi_chain.sum()), "new_articles": len(n)}}
    (ROOT / "dashboard" / "tdp_focus.js").write_text("window.TDP_FOCUS=" + json.dumps(feed, ensure_ascii=False, separators=(",", ":")) + ";\n", encoding="utf-8")

    tot = float(cur.NSV.sum())
    print("FY27 months: %d  offtake ex Brand Counter: %.2f L  (Brand Counter left out: %.2f L)" % (n_months, tot, counter_nsv))
    print("chain-brand pairs: %d  focus rows: %d  (TOP95 %d, new/NPI only %d)" % (
        g.groupby(["Chain", "Brand"]).ngroups, len(sel), int(sel.top95.sum()), int((~sel.top95).sum())))
    print("share of FY27 YTD NSV covered by focus rows: %.2f%%" % (sel.NSV.sum() / g.NSV.sum() * 100))
    print("new-article list: %d (primary-confirmed %d, NPI new to a chain %d); offtake-only and present in Apr-26 baseline, left out: %d" % (
        len(n), len(prim_new), len(npi_eans), unconfirmed))


if __name__ == "__main__":
    main()
