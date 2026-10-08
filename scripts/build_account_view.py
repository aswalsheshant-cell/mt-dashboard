#!/usr/bin/env python3
"""Account share view for the dashboards: data/account_share/Account_View.json

Built from the CSVs of build_account_share.py plus the Nielsen payload (for the Facewash plan) and the review deck's Dmart / Reliance
fair share. Everything is computed here, so the page only draws it.

Blocks
  chains      per chain: latest month, share of the account's category sales, MoM of account sales and of ours, share trend (with the
              scope break marked for More Retail), face wash share
  top5        top 5 categories by account sales, per chain (latest month) with our sales and share; also by zone and by state
  flags       white space / low assortment / below chain average / proven elsewhere, per chain and category (L3M, latest scope)
  together    one table: chains side by side for Face Wash and Shampoo (Lulu, More, Wellness monthly; Dmart, Reliance quarterly from the deck)
  plan        Facewash share plan with the numbers behind each lever

Rules (also written in the JSON, so the page can show them):
  white space      account category is at least 2% of the chain's category sales and our share is under 0.5%
  low assortment   our articles in the category <= 3 (Lulu, More, Reliance) and our share is under the chain average
  below average    our share is under half of our chain-wide share (category at least 2% of the chain)
  strong           our share is at least 1.5 times our chain-wide share
  relevant         a flag or "proven elsewhere" line is shown only for a category that is at least 0.5% of our own sales across these chains
                   (Jun-Aug 26) and is not "Other". A category we only sell a trace of in one chain is listed under "not highlighted", never flagged.
Sizes are indicative: gap = account category sales per month x (our share in the rest of our range, i.e. without Face Wash and Shampoo, minus our
category share), never counted twice across categories that overlap. Reliance values are gross sales as supplied (about 0.45 of that is our NSV).
"""
import json
from pathlib import Path

import pandas as pd

from build_account_share import RELEVANT_MIN_PCT

ROOT = Path(__file__).resolve().parent.parent
AS = ROOT / "data" / "account_share"
NIELSEN = ROOT / "data" / "nielsen_aug26.json"
RULES = {"white_space_min_pct_of_chain": 2.0, "white_space_share_under": 0.5, "low_assortment_articles": 3, "strong_x": 1.5, "below_x": 0.5,
         "relevant_min_pct_of_our_sales": RELEVANT_MIN_PCT}
CHAINS = ("Lulu", "More Retail", "Wellness Forever", "Reliance Retail", "Reliance Brand Counter")
MON = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def mk(label):
    m, y = label.split()
    return int(y) * 12 + MON.index(m)


def r(v, d=2):
    return None if v is None or (isinstance(v, float) and pd.isna(v)) else round(float(v), d)


def share(h, a):
    return h / a * 100 if a and a > 0 else None


def consistent_months(df, chain):
    """Months on one scope, latest first: More Retail uses Jun-Aug 26 only (the earlier months cover fewer categories)."""
    d = df[df["Chain"] == chain]
    months = sorted(d["Month"].unique(), key=mk)
    if chain == "More Retail":
        months = [m for m in months if mk(m) >= mk("Jun 26")]
    return months


def build():
    monthly = pd.read_csv(AS / "Account_Category_Monthly.csv")
    geo = pd.read_csv(AS / "Account_Category_Geo.csv")
    art = pd.read_csv(AS / "Account_Assortment.csv")
    cat = monthly[monthly["Level"] == "Category"]
    rel_m = cat[cat["Month"].isin(["Jun 26", "Jul 26", "Aug 26"])]
    mix = rel_m.groupby("Common Category")["Honasa Sales Rs L"].sum()
    mix_pct = (mix / mix.sum() * 100).to_dict()
    relevant = {k for k, v in mix_pct.items() if v >= RULES["relevant_min_pct_of_our_sales"] and k != "Other"}
    assert relevant == set(cat.loc[cat["Relevant For Us"] == "Yes", "Common Category"]), "Relevant For Us column and the view disagree: rebuild Account_Category_Monthly.csv"
    sells_in = rel_m[rel_m["Honasa Sales Rs L"] > 0].groupby("Common Category")["Chain"].agg(lambda x: sorted(set(x))).to_dict()
    out = {"rules": RULES, "relevant": sorted(relevant),
           "not_highlighted": [{"common": k, "our_pct": r(v, 2), "chains": sells_in.get(k, [])} for k, v in sorted(mix_pct.items(), key=lambda kv: -kv[1]) if k not in relevant], "months": {}, "chains": {}, "top5": [], "flags": [], "proven_elsewhere": [], "together": [], "store_map_check": []}
    for chain in CHAINS:
        c = cat[cat["Chain"] == chain]
        months = consistent_months(c, chain)
        all_months = sorted(c["Month"].unique(), key=mk)
        last, prev = months[-1], months[-2]
        tot = c.groupby("Month")[["Account Sales Rs L", "Honasa Sales Rs L"]].sum()
        fw = c[c["Common Category"] == "Face Wash & Cleanser"].groupby("Month")[["Account Sales Rs L", "Honasa Sales Rs L"]].sum()
        series = [{"month": m, "account": r(tot.loc[m, "Account Sales Rs L"]), "honasa": r(tot.loc[m, "Honasa Sales Rs L"]),
                   "share": r(share(tot.loc[m, "Honasa Sales Rs L"], tot.loc[m, "Account Sales Rs L"])),
                   "fw_account": r(fw["Account Sales Rs L"].get(m)), "fw_honasa": r(fw["Honasa Sales Rs L"].get(m)),
                   "fw_share": r(share(fw["Honasa Sales Rs L"].get(m, 0), fw["Account Sales Rs L"].get(m, 0))),
                   "scope_ok": m in months} for m in all_months]
        l3 = months[-3:]
        out["chains"][chain] = {
            "latest": last, "previous": prev, "l3m": l3, "series": series,
            "scope": c[c["Month"] == last]["Scope"].iloc[0],
            "account_latest": r(tot.loc[last, "Account Sales Rs L"]), "honasa_latest": r(tot.loc[last, "Honasa Sales Rs L"]),
            "share_latest": r(share(tot.loc[last, "Honasa Sales Rs L"], tot.loc[last, "Account Sales Rs L"])),
            "account_mom_pct": r((tot.loc[last, "Account Sales Rs L"] / tot.loc[prev, "Account Sales Rs L"] - 1) * 100, 1),
            "honasa_mom_pct": r((tot.loc[last, "Honasa Sales Rs L"] / tot.loc[prev, "Honasa Sales Rs L"] - 1) * 100, 1),
            "share_change_pp": r(share(tot.loc[last, "Honasa Sales Rs L"], tot.loc[last, "Account Sales Rs L"]) - share(tot.loc[prev, "Honasa Sales Rs L"], tot.loc[prev, "Account Sales Rs L"])),
            "fw_share_latest": r(share(fw["Honasa Sales Rs L"].get(last, 0), fw["Account Sales Rs L"].get(last, 0))),
            "fw_account_latest": r(fw["Account Sales Rs L"].get(last)), "fw_honasa_latest": r(fw["Honasa Sales Rs L"].get(last)),
            "fw_account_l3m_avg": r(fw["Account Sales Rs L"].reindex(l3).mean()), "fw_honasa_l3m_avg": r(fw["Honasa Sales Rs L"].reindex(l3).mean()),
            "n_months_available": len(all_months)}
        # top 5 categories by account sales, latest month, with our sales, share and MoM
        lastc = c[c["Month"] == last].set_index("Category")
        prevc = c[c["Month"] == prev].set_index("Category")
        for name, row in lastc.sort_values("Account Sales Rs L", ascending=False).head(5).iterrows():
            p = prevc.loc[name] if name in prevc.index else None
            out["top5"].append({"chain": chain, "level": "Chain", "name": "All", "month": last, "category": name, "common": row["Common Category"], "relevant": row["Common Category"] in relevant,
                                "account": r(row["Account Sales Rs L"]), "honasa": r(row["Honasa Sales Rs L"]), "share": r(row["Share %"]),
                                "account_mom": r((row["Account Sales Rs L"] / p["Account Sales Rs L"] - 1) * 100, 1) if p is not None and p["Account Sales Rs L"] > 0 else None,
                                "honasa_mom": r((row["Honasa Sales Rs L"] / p["Honasa Sales Rs L"] - 1) * 100, 1) if p is not None and p["Honasa Sales Rs L"] > 0 else None})
        # flags on L3M
        l3d = c[c["Month"].isin(l3)].groupby(["Category", "Common Category"]).agg(a=("Account Sales Rs L", "sum"), h=("Honasa Sales Rs L", "sum")).reset_index()
        chain_a, chain_h = l3d["a"].sum(), l3d["h"].sum()
        chain_share = share(chain_h, chain_a)
        rest = l3d[~l3d["Common Category"].isin(["Face Wash & Cleanser", "Shampoo"])]
        rest_share = share(rest["h"].sum(), rest["a"].sum()) or chain_share      # the rest of our range: the realistic target for a thin category
        art_c = art[(art["Chain"] == chain) & (art["Month"] == last)].set_index("Category")["Articles"] if chain != "Wellness Forever" else pd.Series(dtype=float)
        for _, x in l3d.iterrows():
            pct = x["a"] / chain_a * 100
            s = share(x["h"], x["a"]) or 0.0
            n_art = int(art_c.get(x["Category"], 0)) if len(art_c) else None
            flag = None
            if x["Common Category"] not in relevant:
                continue                                  # not a category for us: never highlighted
            if pct >= RULES["white_space_min_pct_of_chain"] and s < RULES["white_space_share_under"]:
                flag = "White space"
            elif n_art is not None and 0 < n_art <= RULES["low_assortment_articles"] and pct >= RULES["white_space_min_pct_of_chain"] and s < chain_share:
                flag = "Low assortment"
            elif pct >= RULES["white_space_min_pct_of_chain"] and s < chain_share * RULES["below_x"]:
                flag = "Below chain average"
            elif pct >= RULES["white_space_min_pct_of_chain"] and s >= chain_share * RULES["strong_x"]:
                flag = "Strong"
            if flag:
                target = chain_share if x["Common Category"] in ("Face Wash & Cleanser", "Shampoo") else rest_share
                gap = max(target - s, 0) / 100 * x["a"] / len(l3) if flag != "Strong" else 0.0
                out["flags"].append({"chain": chain, "category": x["Category"], "common": x["Common Category"], "flag": flag,
                                     "pct_of_chain": r(pct, 1), "account_avg_month": r(x["a"] / len(l3)), "honasa_avg_month": r(x["h"] / len(l3)),
                                     "share": r(s), "chain_share": r(chain_share), "articles": n_art, "gap_l_month": r(gap), "l3m": l3})
    # geo top 5 (latest month of each chain)
    for chain, g in geo.groupby("Chain"):
        last = out["chains"][chain]["latest"]
        gl = g[g["Month"] == last]
        for level in ("Zone", "State"):
            for name, d in gl.groupby(level):
                tot_a = d["Account Sales Rs L"].sum()
                agg = d.groupby("Category").agg(a=("Account Sales Rs L", "sum"), h=("Honasa Sales Rs L", "sum")).reset_index().sort_values("a", ascending=False).head(5)
                for _, x in agg.iterrows():
                    out["top5"].append({"chain": chain, "level": level, "name": name, "month": last, "category": x["Category"],
                                        "common": g[g["Category"] == x["Category"]]["Common Category"].iloc[0], "relevant": g[g["Category"] == x["Category"]]["Common Category"].iloc[0] in relevant,
                                        "account": r(x["a"]), "honasa": r(x["h"]),
                                        "share": r(share(x["h"], x["a"])), "account_mom": None, "honasa_mom": None,
                                        "pct_of_geo": r(x["a"] / tot_a * 100, 1)})
    # proven elsewhere: common category share >= 3% in one chain, below 1% in another
    comm = cat[cat["Month"].isin(["Jun 26", "Jul 26", "Aug 26"])].groupby(["Chain", "Common Category"]).agg(a=("Account Sales Rs L", "sum"), h=("Honasa Sales Rs L", "sum")).reset_index()
    comm["share"] = comm["h"] / comm["a"] * 100
    chain_tot = comm.groupby("Chain")["a"].sum()
    for cc, d in comm.groupby("Common Category"):
        if cc not in relevant or len(d) < 2:
            continue
        best = d.sort_values("share", ascending=False).iloc[0]
        if best["share"] < 3:
            continue
        for _, x in d.iterrows():
            if x["Chain"] != best["Chain"] and x["share"] < 1 and x["a"] / chain_tot[x["Chain"]] * 100 >= 1.5:
                out["proven_elsewhere"].append({"chain": x["Chain"], "common": cc, "share": r(x["share"]), "account_l3m": r(x["a"]), "best_chain": best["Chain"],
                                                "best_share": r(best["share"]), "gap_l_month": r((best["share"] / 100 * 0.5 - x["share"] / 100) * x["a"] / 3) if best["share"] * 0.5 > x["share"] else 0.0})
    # chains side by side, face wash and shampoo
    deck = json.loads((ROOT / "data" / "nielsen" / "Deck_MT_Review_Big3_v3_1.json").read_text(encoding="utf-8"))
    fs = deck["fair_share"]
    for chain in CHAINS:
        ch = out["chains"][chain]
        sh = comm[(comm["Chain"] == chain) & (comm["Common Category"] == "Shampoo")]
        out["together"].append({"chain": chain, "basis": "Monthly, account report" if not chain.startswith("Reliance") else "Monthly, Reliance file (gross sales)", "period": ch["latest"], "fw_share": ch["fw_share_latest"],
                                "fw_account": ch["fw_account_latest"], "fw_honasa": ch["fw_honasa_latest"],
                                "sh_share": r(share(cat[(cat.Chain == chain) & (cat["Common Category"] == "Shampoo") & (cat.Month == ch["latest"])]["Honasa Sales Rs L"].sum(),
                                                    cat[(cat.Chain == chain) & (cat["Common Category"] == "Shampoo") & (cat.Month == ch["latest"])]["Account Sales Rs L"].sum())),
                                "total_share": ch["share_latest"], "scope": ch["scope"]})
    out["together"].append({"chain": "Dmart", "basis": "Quarterly, review deck", "period": fs["quarters_dmart"][-1], "fw_share": fs["dmart_fw"][-1], "sh_share": fs["dmart_sh"][-1],
                            "scope": "Honasa value as % of the retailer's own category (NSV)"})
    out["together"].append({"chain": "Reliance Retail (deck)", "basis": "Quarterly, review deck", "period": fs["quarters_reliance"][-1], "fw_share": fs["reliance_fw"][-1], "sh_share": fs["reliance_sh"][-1],
                            "scope": "Honasa value as % of the retailer's own category (MRP)"})
    sm = pd.read_csv(AS / "Account_Store_Map.csv")
    out["store_map_check"] = json.loads(sm.fillna("").to_json(orient="records"))
    out["availability"] = [
        {"file": "Compiled_Monthly_Files (Lulu)", "chain": "Lulu", "months": "Jan-Aug 26", "grain": "store x category x brand, store x article",
         "store_city": "Yes: 20 stores with store code, name, state, zone and format; city is read from the store name (7 stores have none in the name)",
         "zone_state": "Yes", "articles": "Yes", "scope": "Stores and categories where Honasa sells"},
        {"file": "More_MS_Till_Aug26_Updated", "chain": "More Retail", "months": "Mar 25, Aug 25-Aug 26 (class level); Jun-Aug 26 (DC city)", "grain": "class and sub-class by month; DC city x item for Jun-Aug",
         "store_city": "No store: DC city only (10 DC cities, 8 states); the ~400 stores are not listed", "zone_state": "Yes (Jun-Aug)", "articles": "Yes, Honasa items (Jun-Aug)",
         "scope": "Sub-categories where Honasa sells to May 26; full account category report from Jun 26 (not comparable across the break)"},
        {"file": "Wellness_MS_Jun-Aug26_Updated", "chain": "Wellness Forever", "months": "Mar-Aug 26", "grain": "category x month (Honasa and overall)",
         "store_city": "No: category level only, no store, zone, state or city", "zone_state": "No", "articles": "No", "scope": "All 63 categories in the account file"},
        {"file": "RIL_BA_Store_MS_Aug26 (Article MS Source)", "chain": "Reliance Retail", "months": "Nov 25-Aug 26", "grain": "article x state x month, Reliance (RRL) and Honasa (HCL)",
         "store_city": "No store code or city in this sheet: zone and state only (the 10-month detail)", "zone_state": "Yes", "articles": "Yes, Honasa articles",
         "scope": "Reliance stores outside the brand counters; RRL Others (categories outside the file's own pivots) left out; gross sales Rs lakh as supplied"},
        {"file": "RIL_BA_Store_MS_Aug26 (BA Store)", "chain": "Reliance Brand Counter", "months": "Jan-Aug 26", "grain": "store x article x month for the staffed brand-counter (BA) stores",
         "store_city": "Yes: about 323 stores with store code, name, zone, state and city (184 cities, 4 stores without a city); kept out of this page, counts only",
         "zone_state": "Yes", "articles": "Yes", "scope": "Staffed counters only, kept apart from Reliance Retail and never added to it"},
        {"file": "UniverseMT.csv", "chain": "All MT", "months": "Current", "grain": "store (426 stores)", "store_city": "No city: store code, chain, zone, state, tier and store type only",
         "zone_state": "Yes", "articles": "No", "scope": "Same file already in the repo (identical, 426 rows)"}]
    out["facewash_plan"] = facewash_plan(out)
    return out


def reliance_nsv_factor(view):
    """Our Reliance NSV (store x article offtake, brand counters left out) / our gross sales in the Reliance file, Jun-Aug 26. None if the offtake files are not there."""
    raw = ROOT / "PowerBI" / "RawDataFolders" / "Offtake_Monthly"
    nsv, gross = 0.0, 0.0
    ch = view["chains"]["Reliance Retail"]
    for mon in ("Jun", "Jul", "Aug"):
        f = raw / f"offtake_store_article_{mon}_26.csv"
        if not f.exists():
            return None
        d = pd.read_csv(f, usecols=["Chain Name", "Store Type", "NSV"], low_memory=False)
        d = d[d["Chain Name"].astype(str).str.strip().str.lower().eq("reliance") & ~d["Store Type"].astype(str).str.strip().eq("Brand Counter")]
        nsv += d["NSV"].sum()
    gross = sum(x["honasa"] for x in ch["series"] if x["month"] in ("Jun 26", "Jul 26", "Aug 26"))
    return nsv / gross if gross else None


def facewash_plan(view):
    """Levers for lifting Facewash share, each with its evidence and an indicative size (Rs Cr per month)."""
    pay = json.loads(NIELSEN.read_text(encoding="utf-8")) if NIELSEN.exists() else {}
    levers = []
    me = next((b for b in pay.get("fw_all", []) if b["n"] == "Mamaearth"), None)
    him = next((b for b in pay.get("fw_all", []) if b["n"] == "Himalaya"), None)
    cat_cr = (pay.get("fw_cat") or {}).get("value")
    # 1 distribution: close part of the WD gap to the leader at today's share per WD point
    if me and him and cat_cr:
        target = min(95.0, him["wd"])
        spd = me["ms"] / me["wd"]
        d_share = spd * (target - me["wd"])
        levers.append({"lever": "Distribution", "evidence": f"WD {me['wd']:.1f}% vs Himalaya {him['wd']:.1f}%; share per WD point {spd:.3f} pp",
                       "action": f"Take WD from {me['wd']:.1f}% to {target:.0f}% by listing Facewash in the {me['stores']:,.0f} -> {him['stores']:,.0f} store gap, largest chains first",
                       "size_cr_month": r(d_share / 100 * cat_cr), "method": f"(target WD - WD) x share per WD point x category value Rs {cat_cr:.1f} Cr",
                       "owner": "NKAM + distributor team", "timeline": "Oct-Dec 26", "kpi": f"WD {target:.0f}% (Nielsen)"})
    # 2 packs not sold
    pg = pay.get("fw_pack_gap") or {}
    miss = [x for x in pg.get("rows", []) if x["status"] == "Not present" and x["cat_share"] >= 1]
    if miss:
        levers.append({"lever": "Pack gaps", "evidence": "; ".join(f"{x['size']} ml = {x['cat_share']:.1f}% of category value, we sell none" for x in miss),
                       "action": "Launch or list the missing sizes in modern trade; check the format fit first", "size_cr_month": r(sum(x["opp_cr"] for x in miss)),
                       "method": "category pack value x (our overall share - our share in the pack)", "owner": "Category + NPD", "timeline": "Launch by Dec 26", "kpi": "Pack listed in top 3 chains"})
    # 3 200 ml where we win but a big chain does not stock it
    p200 = next((x for x in pg.get("rows", []) if x["size"] == "200"), None)
    cp = pd.read_csv(ROOT / "data" / "nielsen" / "Chain_Pack_Presence_Aug26.csv") if (ROOT / "data" / "nielsen" / "Chain_Pack_Presence_Aug26.csv").exists() else None
    if p200 and cp is not None:
        f = cp[cp["Category"] == "Face wash"].assign(Chain=lambda d: d["Chain"].str.upper())
        sold = f[f["Pack"].astype(str) == "200"]
        rel = f[f["Chain"].isin(sold["Chain"])]
        ratio = sold["NSV_lakh"].sum() / rel["NSV_lakh"].sum() if rel["NSV_lakh"].sum() else None
        dm = f[f["Chain"] == "DMART"]
        if ratio is not None and len(dm) and "DMART" not in set(sold["Chain"]):
            gain = dm["NSV_lakh"].sum() / 5 * ratio * 0.5 / 100       # per month, Rs Cr, with a 50% haircut
            levers.append({"lever": "200 ml in Dmart", "evidence": f"200 ml is {p200['cat_share']:.1f}% of category value and we hold {p200['me_share_in_pack']:.0f}% of it; sold in {', '.join(c.title() for c in sold['Chain'])}, not in Dmart",
                           "action": "List Facewash 200 ml in Dmart in the 250/600 ml-led architecture (the range logic of the deck)", "size_cr_month": r(gain),
                           "method": f"Dmart Facewash NSV per month x 200 ml share of Facewash NSV in chains that sell it ({ratio * 100:.0f}%) x 50% haircut",
                           "owner": "NKAM Dmart", "timeline": "Listing cycle Nov-Dec 26", "kpi": "200 ml in Dmart stores"})
    # 4 chain share: lift face wash share inside accounts toward the best account (the staffed brand counters are not a benchmark)
    accts = {n: c for n, c in view["chains"].items() if n != "Reliance Brand Counter"}
    best = max((c["fw_share_latest"] for c in accts.values() if c["fw_share_latest"] is not None), default=None)
    for name, c in accts.items():
        if c["fw_share_latest"] is None or c["fw_account_l3m_avg"] is None or best is None or c["fw_share_latest"] >= best - 0.01:
            continue                                    # the best account is the benchmark, not a lever
        add = 3.0
        factor, basis = 1.0, ""
        if name == "Reliance Retail":                   # the Reliance file is gross sales; our NSV is about 0.4 of it, so size in NSV
            factor = reliance_nsv_factor(view)
            if factor is None:
                continue
            basis = f" x {factor:.2f} (our NSV / gross sales in the Reliance file, Jun-Aug 26)"
        levers.append({"lever": f"Account share: {name}", "evidence": f"Face wash & cleanser share {c['fw_share_latest']:.1f}% of {name}'s category (Rs {c['fw_account_l3m_avg']:.0f} L a month); best account {best:.1f}%",
                       "action": f"Shelf share and range depth in {name}: facings, hero SKUs in every store, end-cap in the lowest-share states", "size_cr_month": r(add / 100 * c["fw_account_l3m_avg"] * factor / 100),
                       "method": f"+{add:.0f} pp of the account's Face Wash category (L3M average){basis}", "owner": f"NKAM {name}", "timeline": "Oct-Nov 26", "kpi": f"Share in {name} +{add:.0f} pp"})
    return {"levers": levers, "total_cr_month": r(sum(x["size_cr_month"] or 0 for x in levers)),
            "note": "Levers overlap (a listing also lifts WD and account share), so the total is an upper bound, not a forecast.",
            "nielsen": {"share": me and me["ms"], "share_yoy_pp": me and me["pp"], "wd": me and me["wd"], "category_cr": cat_cr}}


def main():
    import argparse
    global NIELSEN
    ap = argparse.ArgumentParser(description="Build data/account_share/Account_View.json")
    ap.add_argument("--payload", type=Path, default=NIELSEN, help="Nielsen payload used for the Facewash plan (default: the Aug-26 payload)")
    NIELSEN = ap.parse_args().payload
    view = build()
    path = AS / "Account_View.json"
    path.write_text(json.dumps(view, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print("wrote", path, f"({path.stat().st_size // 1024} KB)")
    for ch, c in view["chains"].items():
        print(ch, c["latest"], "share", c["share_latest"], "fw", c["fw_share_latest"], "acct MoM", c["account_mom_pct"], "ours MoM", c["honasa_mom_pct"])
    from collections import Counter
    print(Counter((f["chain"], f["flag"]) for f in view["flags"]))
    for lv in view["facewash_plan"]["levers"]:
        print(lv["lever"], lv["size_cr_month"])


if __name__ == "__main__":
    main()
