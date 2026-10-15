#!/usr/bin/env python3
"""Sales Journey proxy KPIs -> dashboard/sj_kpis.js (window.SJ_KPIS).

Built from the "FMCG Sales Journey" ladder (docs/prompts/FMCG_SALES_JOURNEY_TRACKER.md). Three blocks, each labelled
as a PROXY because the real source is not in the repo. Nothing here is estimated: a figure the source cannot give is null.

1. distribution  (Days 5 and 6: numeric and weighted distribution, in-house proxy)
     active stores   = distinct stores with offtake NSV > 0 for the chain in the period  (the denominator: OUR active stores,
                       not every relevant outlet in the market, so this is NOT Nielsen ND / WD)
     ND  %           = stores selling the item / active stores x 100
     WD  %           = chain offtake value in the stores selling the item / chain offtake value in all active stores x 100
                       (stores are weighted by our own offtake, not by category sales)
     missing stores  = active stores - stores selling
     indicative NSV  = missing stores x MEDIAN NSV per selling store (observed rate, not a forecast; a ceiling, because the missing
                       stores may be smaller or may not suit the item)
   Offtake only (store x article files, Apr-Aug'26). Reliance Brand Counter left out. Chains whose source has no store
   identity for at least MIN_CODED of NSV show no ND / WD (same rule as scripts/build_tdp_inhouse.py).
2. order_line_value  (Day 11: average order value, proxy)
     PO value per sales-order line = PO value / SO lines, MT channel, from PO_Fill_Rate_Monthly_Apr25_to_Aug26.csv.
     It is NOT value per order: the order count is not in that file, and the primary article files for Jun-Aug'26 no
     longer carry PO Number or Inv No.
3. breakeven_inputs  (Day 16: promotion break-even, calculator inputs)
     chain average offer depth (promo block), margin % of NSV (profitability block, standard-cost basis), MRP / NSV
     (tot block). The dashboard calculator turns them into the break-even volume uplift; the share of the discount that
     Honasa funds is NOT in any file, so it is an input the user sets (default 100% = upper bound).

    python scripts/build_sj_kpis.py
"""
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).parent))
import visit_cities as vc  # noqa: E402

OUT = ROOT / "dashboard" / "sj_kpis.js"
FOCUS = ROOT / "PowerBI" / "SeedData" / "Masters" / "TDP_Focus_Articles.csv"
PO_FILE = ROOT / "PowerBI" / "SeedData" / "Forecast" / "PO_Fill_Rate_Monthly_Apr25_to_Aug26.csv"
DATA_JS = ROOT / "dashboard" / "data.js"
MONTH_LABEL = {"Apr": "Apr'26", "May": "May'26", "Jun": "Jun'26", "Jul": "Jul'26", "Aug": "Aug'26"}
MIN_CODED = 0.9
YTD = "FY27 YTD"


def _ean(v):
    t = str(v).strip().lstrip("'")
    if t.lower() in ("", "nan", "none"):
        return None
    return t[:-2] if t.endswith(".0") else t


def nd_wd(df, key, period_stores=None):
    """ND / WD per (Chain, key) for one period. df needs Chain, sid, NSV and the key column. Pure function (tested)."""
    store_val = df.groupby(["Chain", "sid"], as_index=False)["NSV"].sum().rename(columns={"NSV": "store_val"})
    active = store_val.groupby("Chain").agg(active_stores=("sid", "nunique"), chain_val=("store_val", "sum"))
    pairs = df[["Chain", "sid", key]].drop_duplicates().merge(store_val, on=["Chain", "sid"])
    pairs = pairs.merge(df.groupby(["Chain", "sid", key], as_index=False)["NSV"].sum().rename(columns={"NSV": "item_val"}),
                        on=["Chain", "sid", key])
    g = pairs.groupby(["Chain", key]).agg(stores_selling=("sid", "nunique"), weight=("store_val", "sum"), item_nsv=("item_val", "sum"),
                                         median_store_nsv=("item_val", "median")).reset_index()
    g = g.merge(active, left_on="Chain", right_index=True)
    g["nd_pct"] = g["stores_selling"] / g["active_stores"] * 100
    g["wd_pct"] = g["weight"] / g["chain_val"] * 100
    g["missing_stores"] = g["active_stores"] - g["stores_selling"]
    g["nsv_per_store"] = g["median_store_nsv"]
    g["indicative_lakh"] = g["missing_stores"] * g["nsv_per_store"]
    return g


def build_distribution():
    d = vc.load_offtake(vc.MONTHS)
    d = d[~d["bc"]].copy()
    d["Month"] = d["file"].map(MONTH_LABEL)
    d["EANs"] = d["EAN"].map(_ean)
    d = d[(d["NSV"] > 0) & d["EANs"].notna()]
    coded = d.assign(c=d["code"].notna()).groupby("Chain").apply(
        lambda g: g.loc[g["c"], "NSV"].sum() / g["NSV"].sum() if g["NSV"].sum() else 0, include_groups=False)
    ok_chain = {c for c, v in coded.items() if v >= MIN_CODED}
    skipped = sorted(set(coded.index) - ok_chain)
    months = [MONTH_LABEL[m] for m in vc.MONTHS]
    last = months[-1]
    periods = {last: d[d["Month"] == last], YTD: d}

    focus = pd.read_csv(FOCUS, dtype=str)
    focus = focus[focus["Selection"].str.contains("TOP95", na=False)]
    focus_keys = set(zip(focus["Chain"], focus["EAN"].map(_ean)))

    out = {"by_chain": [], "by_brand": [], "by_article": []}
    for per, df in periods.items():
        df = df[df["Chain"].isin(ok_chain)]
        act = df.groupby("Chain")["sid"].nunique()
        for ch, n in act.items():
            out["by_chain"].append({"chain": ch, "period": per, "active_stores": int(n),
                                    "nsv": round(float(df.loc[df["Chain"] == ch, "NSV"].sum()), 2)})
        for r in nd_wd(df, "Brand").itertuples(index=False):
            out["by_brand"].append({"chain": r.Chain, "brand": r.Brand, "period": per, "active_stores": int(r.active_stores),
                                    "stores_selling": int(r.stores_selling), "nd_pct": round(r.nd_pct, 1), "wd_pct": round(r.wd_pct, 1)})
        g = nd_wd(df, "EANs")
        g = g[[(c, e) in focus_keys for c, e in zip(g["Chain"], g["EANs"])]]
        name = dict(zip(zip(focus["Chain"], focus["EAN"].map(_ean)), focus["Article Description"]))
        brand = dict(zip(zip(focus["Chain"], focus["EAN"].map(_ean)), focus["Brand"]))
        for r in g.itertuples(index=False):
            k = (r.Chain, r.EANs)
            out["by_article"].append({"chain": r.Chain, "brand": brand.get(k), "ean": r.EANs, "article": name.get(k), "period": per,
                                      "active_stores": int(r.active_stores), "stores_selling": int(r.stores_selling),
                                      "nd_pct": round(r.nd_pct, 1), "wd_pct": round(r.wd_pct, 1), "missing_stores": int(r.missing_stores),
                                      "nsv_per_store": round(r.nsv_per_store, 4), "indicative_lakh": round(r.indicative_lakh, 2)})
    out["by_article"].sort(key=lambda r: -r["indicative_lakh"])
    return {"label": "In-house proxy from our offtake, not Nielsen ND / WD", "periods": [last, YTD], "months": months,
            "denominator": "Our active stores = stores of the chain with offtake NSV > 0 in the period. ND = stores selling / active stores. "
                           "WD = share of the chain's offtake value sitting in the stores selling the item (stores weighted by our own offtake, not category sales).",
            "indicative_note": "Indicative NSV = stores not selling x median NSV per selling store in the period. A ceiling, not a forecast: the missing stores may be smaller or may not suit the item.",
            "chains_without_store_identity": skipped, **out}


def build_order_line_value():
    d = pd.read_csv(PO_FILE)
    d = d[d["Channel"] == "MT"].copy()
    def roll(g):
        lines = float(g["SO_Lines"].sum())
        return {"so_lines": int(lines), "po_value_l": round(float(g["PO_Value_L"].sum()), 2),
                "billed_value_l": round(float(g["Billed_Value_L"].sum()), 2),
                "po_value_per_line_rs": round(float(g["PO_Value_L"].sum()) * 100000 / lines, 0) if lines else None}
    mon = {m: i for i, m in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])}
    key = lambda m: (int(m.split("-")[1]), mon[m.split("-")[0]])      # "Oct-25" -> (25, 9)
    months = sorted(set(d["Month"]), key=key)
    by_month = [{"month": m, "fy": d.loc[d["Month"] == m, "FY"].iloc[0], **roll(d[d["Month"] == m])} for m in months]
    last_fy = d.loc[d["Month"] == months[-1], "FY"].iloc[0]
    cur = d[d["FY"] == last_fy]
    last_m = months[-1]
    by_chain = [{"chain": c, "period": last_m, **roll(g)} for c, g in d[d["Month"] == last_m].groupby("Chain")]
    by_chain_ytd = [{"chain": c, "period": f"{last_fy} YTD", **roll(g)} for c, g in cur.groupby("Chain")]
    for lst in (by_chain, by_chain_ytd):
        lst.sort(key=lambda r: -r["po_value_l"])
    return {"label": "Order-line value (proxy for average order value)",
            "note": "PO value per sales-order line, MT channel. Not value per order: the order count is not in the PO summary, and the primary "
                    "article files for Jun-Aug'26 no longer carry PO Number or Inv No. (they did up to May'26).",
            "source": "PowerBI/SeedData/Forecast/PO_Fill_Rate_Monthly_Apr25_to_Aug26.csv", "fy": last_fy,
            "by_month": by_month, "by_chain_last_month": by_chain, "by_chain_ytd": by_chain_ytd}


def build_breakeven_inputs():
    s = DATA_JS.read_text(encoding="utf-8")
    D = json.loads(s[s.index("{"): s.rindex("}") + 1])
    promo = D.get("promo") or {}
    depth = {}
    for mon, blk in (promo.get("monthly") or {}).items():
        for r in blk.get("by_chain", []):
            if r.get("avg_offer_pct") is not None:
                depth.setdefault(r["name"], []).append((mon, r["avg_offer_pct"], r.get("skus")))
    prof = {r["name"]: r for r in (D.get("profitability") or {}).get("by_chain", [])}
    tot = {r["name"]: r for r in (D.get("tot") or {}).get("by_chain", [])}
    rows = []
    for ch, lst in depth.items():
        p, t = prof.get(ch), tot.get(ch)
        if not p or not t or not t.get("nsv"):
            continue
        w = sum(x[2] or 0 for x in lst)
        avg = (sum(x[1] * (x[2] or 0) for x in lst) / w) if w else sum(x[1] for x in lst) / len(lst)
        rows.append({"chain": ch, "avg_offer_pct": round(avg, 1), "promo_months": [x[0] for x in lst],
                     "margin_pct_of_nsv": p.get("margin_pct_of_nsv"), "mrp_to_nsv": round(t["mrp"] / t["nsv"], 3),
                     "nsv_lakh": p.get("nsv_lakh")})
    rows.sort(key=lambda r: -(r["nsv_lakh"] or 0))
    return {"label": "Promotion break-even calculator inputs",
            "formula": "Required volume uplift % = d / (m - d) x 100, where d = offer depth x Honasa funding share x MRP/NSV (discount as % of NSV) and m = margin % of NSV.",
            "notes": ["Offer depth is the average offer to the consumer (% of MRP) in the promo files, weighted by SKUs.",
                      "Margin % of NSV is the standard-cost basis (cost = % of MRP), not SAP COGS.",
                      "No file holds the share of the discount that Honasa funds or the promotion spend. It is an input; 100% is an upper bound.",
                      "Break-even ignores the post-promotion dip and any baseline shift."],
            "rows": rows}


def build():
    payload = {"status": "PROXY", "generated_from": ["offtake_store_article_<Mon>_26.csv", "PO_Fill_Rate_Monthly_Apr25_to_Aug26.csv",
                                                       "dashboard/data.js (promo, profitability, tot)"],
               "distribution": build_distribution(), "order_line_value": build_order_line_value(),
               "breakeven_inputs": build_breakeven_inputs()}
    OUT.write_text("window.SJ_KPIS=" + json.dumps(payload, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + ";\n", encoding="utf-8")
    d = payload["distribution"]
    print(f"wrote {OUT} ({OUT.stat().st_size/1024:.0f} KB): by_chain {len(d['by_chain'])}, by_brand {len(d['by_brand'])}, by_article {len(d['by_article'])}; "
          f"skipped chains {d['chains_without_store_identity']}; PO months {len(payload['order_line_value']['by_month'])}; break-even chains {len(payload['breakeven_inputs']['rows'])}")


if __name__ == "__main__":
    build()
