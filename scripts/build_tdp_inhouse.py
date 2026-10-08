"""In-house distribution view from OUR offtake (Apr-Aug FY27): stores selling, SKUs selling and SKU listings by chain, state, pack and month.
Writes dashboard/tdp_inhouse.js (window.TDP_INHOUSE). This is NOT Nielsen TDP: it has no ACV % and no weighted distribution, because those need
each store's category sales, which we do not have. It is the same idea counted from our own sell-out file, until the real TDP file arrives.

  stores selling   = distinct stores with offtake in the month
  SKUs selling     = distinct EANs with offtake in the month
  SKU listings     = distinct store x EAN pairs in the month  (our in-house "distribution points": each listing is one SKU on one store's shelf)
  SKUs per store   = SKU listings / stores selling   (average items carried, like AIC)
  Store reach %    = stores selling / stores in the store master   (a numeric-distribution style ratio; shown only where the source carries store codes.
                     The master also holds stores first seen in the offtake files, so reach reads high: use it for direction, not as a census)
Brand Counter stores are left out (offtake rule). Nothing is estimated.

    python scripts/build_tdp_inhouse.py
"""
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import build_store_universe as bsu  # noqa: E402
import visit_cities as vc  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "dashboard" / "tdp_inhouse.js"
MONTH_LABEL = {"Apr": "Apr'26", "May": "May'26", "Jun": "Jun'26", "Jul": "Jul'26", "Aug": "Aug'26"}
MIN_CODED = 0.9   # a chain's store reach is shown only when at least this share of its NSV sits on rows with a store code


def master_by_state(path=bsu.MASTER):
    m = pd.read_csv(path)
    m = m[~m["Store Key"].astype(str).str.contains("NO-CITY|\\|Pan India", regex=True, na=False)]
    return m.groupby("State").size().to_dict()


def build():
    d = vc.load_offtake(vc.MONTHS)
    d = d[~d["bc"]].copy()
    d["Month"] = d["file"].map(MONTH_LABEL)
    d["Pack"] = pd.to_numeric(d["Net Weight"], errors="coerce").map(lambda v: f"{int(v)} g/ml" if pd.notna(v) else "Not stated")
    d["Item"] = d["EAN"].astype(str)
    d = d[d["NSV"] != 0]
    coded = d.assign(c=d["code"].notna()).groupby("Chain").apply(lambda g: g.loc[g["c"], "NSV"].sum() / g["NSV"].sum() if g["NSV"].sum() else 0, include_groups=False)
    mc = bsu.master_counts()["by_chain"]
    ms = master_by_state()
    months = [MONTH_LABEL[m] for m in vc.MONTHS]

    def agg(g):
        stores = g["sid"].nunique()
        lst = g[["sid", "Item"]].drop_duplicates().shape[0]
        return {"stores": int(stores), "skus": int(g["Item"].nunique()), "listings": int(lst), "skus_per_store": round(lst / stores, 2) if stores else None, "nsv": round(float(g["NSV"].sum()), 2)}

    def roll(by, denom=None, need_codes=False):
        rows = []
        for (name, mon), g in d.groupby([by, "Month"]):
            r = {by.lower(): str(name), "month": mon, **agg(g)}
            if denom is not None:
                den = denom.get(name)
                ok = (not need_codes) or coded.get(name, 0) >= MIN_CODED
                r["master_stores"] = int(den) if den else None
                r["reach_pct"] = round(r["stores"] / den * 100, 1) if den and ok else None
                r["has_store_codes"] = bool(ok)
                if need_codes and not ok:       # store keys here are city / state placeholders, so a per-store average would mislead
                    r["skus_per_store"] = None
            rows.append(r)
        return rows

    tot = [{"month": mon, **agg(g)} for mon, g in d.groupby("Month")]
    tot.sort(key=lambda r: months.index(r["month"]))
    out = {"status": "IN_HOUSE", "label": "From our offtake, not TDP (no ACV %, no weighted distribution)", "period": "Apr-Aug FY27", "months": months,
           "master_total": int(bsu.master_counts()["total"]), "total": tot,
           "by_chain": roll("Chain", mc, need_codes=True), "by_state": roll("State", ms), "by_pack": roll("Pack")}
    return out


SEED = ROOT / "PowerBI" / "SeedData" / "Store_Cuts"


def write_powerbi_seed(out):
    """One long table for Power BI (NSV in rupees): Level = Chain / State / Pack / Total. 'Stores In Master' is blank where it does not apply."""
    rows = []
    for r in out["total"]:
        rows.append({"Month": r["month"], "Level": "Total", "Name": "All MT", **{k: r.get(k) for k in ("stores", "skus", "listings", "nsv")}, "master": out["master_total"]})
    for lvl, key, name in (("Chain", "by_chain", "chain"), ("State", "by_state", "state"), ("Pack", "by_pack", "pack")):
        for r in out[key]:
            rows.append({"Month": r["month"], "Level": lvl, "Name": r[name], **{k: r.get(k) for k in ("stores", "skus", "listings", "nsv")}, "master": r.get("master_stores")})
    d = pd.DataFrame(rows).rename(columns={"stores": "Stores Selling", "skus": "SKUs Selling", "listings": "SKU Listings", "master": "Stores In Master"})
    d["NSV Rs"] = (d.pop("nsv") * 100000).round(0)
    d.insert(1, "FY Year", "FY27")
    d["Basis"] = "From our offtake, not TDP"
    SEED.mkdir(parents=True, exist_ok=True)
    d.to_csv(SEED / "inhouse_distribution_fy27.csv", index=False)


def main():
    out = build()
    write_powerbi_seed(out)
    OUT.write_text("window.TDP_INHOUSE=" + json.dumps(out, separators=(",", ":")) + ";\n", encoding="utf-8")
    t = out["total"][-1]
    print("tdp in-house:", t)


if __name__ == "__main__":
    main()
