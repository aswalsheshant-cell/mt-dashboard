"""State, pack size and like-for-like (LFL) / new store (NFL) cuts for Apr-Aug FY27 offtake.

Definitions (plain words):
  LFL store  = sold in Apr-Aug this year AND had sales in Apr-Aug last year (same store, same months)
  NFL store  = sold this year, no sales last year in those months (new or restarted)
  Lost store = sold last year in those months, nothing this year (shown as a count and last-year NSV)
  Reliance Retail non-counter has last-year sales at state level only, so it is kept apart as "No LY store data".
Brand Counter stores are left out (offtake rule). NSV in Rs lakh. Nothing is estimated.
Output: data/store_cuts_aug26.json (+ data/qc/store_cuts_*.csv)
"""
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import visit_cities as vc  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
LY_FILE = ROOT / "data" / "offtake_fy26" / "Store_Month_NSV_FY26.csv"
LINKS = ROOT / "data" / "offtake_fy26" / "Store_Key_Links_FY26.csv"
OUT = ROOT / "data" / "store_cuts_aug26.json"
JS_OUT = ROOT / "dashboard" / "store_cuts.js"
MIN_LY_MONTHS = 3   # store-level growth is shown only for stores with at least this many months of sales last year
LY_MONTHS = ["Apr'25", "May'25", "Jun'25", "Jul'25", "Aug'25"]


def zone_dashboard_totals():
    """Apr-Aug NSV (Rs lakh) by zone from the dashboard's own zone totals: this year and the same five months last year, so the growth compares like with like.
    Zone names follow the dashboard ('South 1'); returned with a hyphen ('South-1') to match the store files. {} when data.js or the keys are missing."""
    try:
        txt = (ROOT / "dashboard" / "data.js").read_text(encoding="utf-8")
        o = json.loads(txt[txt.index("{"):txt.rindex("}") + 1])["offtake"]
        ly = {z.replace("South ", "South-"): round(sum(v[:5]), 2) for z, v in o["zone_monthly_fy26"].items()}
        ty = {z.replace("South ", "South-"): round(sum(v[:5]), 2) for z, v in o["zone_monthly_fy27"].items()}
        return {z: (ty.get(z), ly[z]) for z in ly}
    except (OSError, KeyError, ValueError):
        return {}


def build():
    d = vc.load_offtake(vc.MONTHS)
    d = d[~d["bc"]].copy()
    d["Net Weight"] = pd.to_numeric(d["Net Weight"], errors="coerce")
    st = d.groupby("sid").agg(Chain=("Chain", "first"), State=("State", lambda s: s.mode().iat[0] if s.notna().any() else None),
                              Zone=("Zone", lambda s: s.mode().iat[0] if s.notna().any() else None), TY=("NSV", "sum"))
    ly_all = pd.read_csv(LY_FILE)
    ly = ly_all[ly_all["Month"].isin(LY_MONTHS)].copy()
    links = dict(pd.read_csv(LINKS)[["LY Store Key", "Store Key"]].values) if LINKS.exists() else {}
    ly["Key"] = ly["Store Key"].map(lambda k: links.get(k, k))
    ly_all["Key"] = ly_all["Store Key"].map(lambda k: links.get(k, k))
    sold_other_ly_months = set(ly_all[~ly_all["Month"].isin(LY_MONTHS) & (ly_all["NSV"] > 0)]["Key"])
    lys = ly.groupby("Key")["NSV"].sum()
    ly_months = ly[ly["NSV"] > 0].groupby("Key")["Month"].nunique()
    lych = ly.groupby("Key")["Chain Name"].first()
    st["LY"] = st.index.map(lys).astype(float)
    st["LY Months"] = st.index.map(ly_months).fillna(0).astype(int)
    reliance_no_ly = st["Chain"].eq("Reliance Retail")          # last year only at state level
    st["Type"] = "LFL"
    st.loc[st["LY"].isna() | (st["LY"] <= 0), "Type"] = "NFL"
    st.loc[reliance_no_ly, "Type"] = "No LY store data"
    # NFL splits in two: Restarted = sold in another month of last year (Sep-Mar), so not a new store; New = no sales anywhere last year
    st["NFL Kind"] = ""
    nfl = st["Type"].eq("NFL")
    st.loc[nfl, "NFL Kind"] = ["Restarted" if k in sold_other_ly_months else "New" for k in st.index[nfl]]
    lost = lys[~lys.index.isin(st.index) & (lys > 0)]
    lost_df = pd.DataFrame({"Chain": lych.reindex(lost.index), "LY": lost})

    def roll(by):
        g = st.rename(columns={"NFL Kind": "Kind"}).assign(Reliable=st["LY Months"] >= MIN_LY_MONTHS).groupby(by + ["Type", "Kind", "Reliable"]).agg(Stores=("TY", "size"), TY=("TY", "sum"), LY=("LY", "sum")).reset_index()
        rows = []
        for key, grp in g.groupby(by):
            key = key if isinstance(key, tuple) else (key,)
            r = dict(zip(by, key))
            for t, tag in (("LFL", "lfl"), ("NFL", "nfl"), ("No LY store data", "noly")):
                x = grp[grp["Type"] == t]
                r[f"{tag}_stores"] = int(x["Stores"].sum())
                r[f"{tag}_ty"] = round(float(x["TY"].sum()), 2)
            for kind, tag in (("New", "new"), ("Restarted", "restart")):
                x = grp[(grp["Type"] == "NFL") & (grp["Kind"] == kind)]
                r[f"{tag}_stores"] = int(x["Stores"].sum())
                r[f"{tag}_ty"] = round(float(x["TY"].sum()), 2)
            r["lfl_ly"] = round(float(grp[grp["Type"] == "LFL"]["LY"].sum()), 2)
            ok = grp[(grp["Type"] == "LFL") & (grp["Reliable"])]
            r["lfl3_ty"] = round(float(ok["TY"].sum()), 2)
            r["lfl3_ly"] = round(float(ok["LY"].sum()), 2)
            r["lfl3_growth_pct"] = round((r["lfl3_ty"] / r["lfl3_ly"] - 1) * 100, 1) if r["lfl3_ly"] > 0 else None
            r["ty_total"] = round(float(grp["TY"].sum()), 2)
            r["lfl_growth_pct"] = round((r["lfl_ty"] / r["lfl_ly"] - 1) * 100, 1) if r["lfl_ly"] > 0 else None
            r["lost_stores"] = int(len(lost_df[lost_df["Chain"] == r["Chain"]])) if by == ["Chain"] else None
            rows.append(r)
        return sorted(rows, key=lambda r: -r["ty_total"])

    pk = d.groupby("Net Weight").agg(NSV=("NSV", "sum"), Stores=("sid", "nunique")).reset_index()
    jul = d[d["file"] == "Jul"].groupby("Net Weight")["NSV"].sum()
    aug = d[d["file"] == "Aug"].groupby("Net Weight")["NSV"].sum()
    tot = float(pk["NSV"].sum())
    packs = [{"pack": (f"{int(r['Net Weight'])} g/ml" if pd.notna(r["Net Weight"]) else "Not stated"), "nsv": round(float(r["NSV"]), 2),
              "share_pct": round(float(r["NSV"]) / tot * 100, 1), "stores": int(r["Stores"]),
              "mom_pct": round((aug.get(r["Net Weight"], 0) / jul.get(r["Net Weight"], 0) - 1) * 100, 1) if jul.get(r["Net Weight"], 0) > 0 else None}
             for _, r in pk.sort_values("NSV", ascending=False).iterrows()]
    cat = d.groupby(["Category", "Net Weight"])["NSV"].sum().reset_index()
    mv = st[(st["Type"] == "LFL") & (st["LY Months"] >= MIN_LY_MONTHS) & (st["LY"] > 0)].copy()
    mv["g"] = (mv["TY"] / mv["LY"] - 1) * 100
    mv["gain"] = mv["TY"] - mv["LY"]
    row = lambda i, r: {"store": i, "chain": r["Chain"], "state": r["State"], "ly": round(float(r["LY"]), 2), "ty": round(float(r["TY"]), 2), "growth_pct": round(float(r["g"]), 0), "ly_months": int(r["LY Months"])}
    movers = {"min_ly_months": MIN_LY_MONTHS, "eligible_stores": int(len(mv)), "thin_history_stores": int(((st["Type"] == "LFL") & (st["LY Months"] < MIN_LY_MONTHS)).sum()),
              "top_gainers": [row(i, r) for i, r in mv[mv["State"] != "Pan India"].sort_values("gain", ascending=False).head(10).iterrows()],
              "top_decliners": [row(i, r) for i, r in mv[mv["State"] != "Pan India"].sort_values("gain").head(10).iterrows()]}   # Pan India = an online account, not a store
    # Sales by zone, brand and sub-category (this year, Apr-Aug), each split by store type. Last year has no brand or sub-category in the store file,
    # so brand / sub-category growth is not possible; zone growth comes from the dashboard's zone totals (same five months).
    tp = st["Type"].where(st["Type"] != "NFL", "NFL " + st["NFL Kind"])
    d = d.assign(SType=d["sid"].map(tp))
    zone_tot = zone_dashboard_totals()

    def dim_sales(col, label):
        rows = []
        for name, g in d.groupby(col, dropna=False):
            r = {label: ("Not stated" if pd.isna(name) else str(name)), "ty": round(float(g["NSV"].sum()), 2), "stores": int(g["sid"].nunique())}
            for t, tag in (("LFL", "lfl"), ("NFL New", "new"), ("NFL Restarted", "restart"), ("No LY store data", "noly")):
                r[f"{tag}_ty"] = round(float(g[g["SType"] == t]["NSV"].sum()), 2)
            jul, aug = float(g[g["file"] == "Jul"]["NSV"].sum()), float(g[g["file"] == "Aug"]["NSV"].sum())
            r["jul"], r["aug"] = round(jul, 2), round(aug, 2)
            r["mom_pct"] = round((aug / jul - 1) * 100, 1) if jul > 0 else None
            r["share_pct"] = round(r["ty"] / float(d["NSV"].sum()) * 100, 1)
            rows.append(r)
        return sorted(rows, key=lambda r: -r["ty"])

    zone_sales = dim_sales("Zone", "zone")
    for r in zone_sales:
        t_z, ly_z = zone_tot.get(r["zone"], (None, None))
        r["dash_ty"], r["dash_ly"] = t_z, ly_z      # the dashboard's zone totals for the same five months (its zone rules differ slightly from the store files)
        r["yoy_pct"] = round((t_z / ly_z - 1) * 100, 1) if t_z and ly_z else None
    sub = dim_sales("Sub_category", "subcategory")
    cat_of = d.groupby("Sub_category")["Category"].agg(lambda s_: s_.mode().iat[0] if s_.notna().any() else None)
    for r in sub:
        r["category"] = cat_of.get(r["subcategory"])
    out = {
        "zone_sales": zone_sales, "brand_sales": dim_sales("Brand", "brand"), "subcat_sales": sub,
        "movers": movers,
        "period": "Apr-Aug FY27 vs Apr-Aug FY26", "unit": "Rs lakh", "total_ty": round(float(d["NSV"].sum()), 2),
        "stores": {t: int((st["Type"] == t).sum()) for t in ("LFL", "NFL", "No LY store data")} | {"New": int((st["NFL Kind"] == "New").sum()), "Restarted": int((st["NFL Kind"] == "Restarted").sum())},
        "lost": {"stores": int(len(lost_df)), "ly_nsv": round(float(lost_df["LY"].sum()), 2)},
        "by_chain": roll(["Chain"]), "by_state": roll(["State"]), "by_zone": roll(["Zone"]), "by_pack": packs,
        "pack_by_category": [{"category": r["Category"], "pack": int(r["Net Weight"]), "nsv": round(float(r["NSV"]), 2)}
                             for _, r in cat.dropna().sort_values("NSV", ascending=False).head(30).iterrows()],
    }
    st.attrs["lost"] = lost_df
    st.attrs["rows"] = d
    st.attrs["pack_month"] = (d.groupby(["file", "Category", "Net Weight"], dropna=False).agg(NSV=("NSV", "sum"), Stores=("sid", "nunique")).reset_index())
    return out, st


SEED = ROOT / "PowerBI" / "SeedData" / "Store_Cuts"
RAW_FOLDER = ROOT / "PowerBI" / "RawDataFolders" / "Store_Cuts"
MONTH_LABEL = {"Apr": "Apr'26", "May": "May'26", "Jun": "Jun'26", "Jul": "Jul'26", "Aug": "Aug'26"}


def write_powerbi_seed(st):
    """Two small seed tables for Power BI (NSV in rupees: the offtake lakh x 100,000). One row per store (LFL / NFL / No LY store data / Lost; NFL Kind = New or Restarted) and one row per month x category x pack."""
    SEED.mkdir(parents=True, exist_ok=True)
    a = st.reset_index().rename(columns={"sid": "Store Key", "Type": "Store Type"})
    a["NFL Kind"] = a["NFL Kind"].replace("", "Not NFL")
    a["LY Months Sold"] = a["LY Months"]
    a["Growth Basis"] = a["LY Months"].map(lambda m: "Enough history" if m >= MIN_LY_MONTHS else "Thin history")
    a["NSV This Year Rs"] = (a["TY"] * 100000).round(0)
    a["NSV Last Year Same Months Rs"] = (a["LY"].fillna(0) * 100000).round(0)
    a = a[["Store Key", "Chain", "State", "Zone", "Store Type", "NFL Kind", "NSV This Year Rs", "NSV Last Year Same Months Rs"]]
    lost = st.attrs["lost"].reset_index().rename(columns={"Key": "Store Key", "index": "Store Key"})
    lost["State"] = "Not available"
    lost["Zone"] = "Not available"
    lost["Store Type"] = "Lost"
    lost["NFL Kind"] = "Not NFL"
    lost["LY Months Sold"] = 0
    lost["Growth Basis"] = "Thin history"
    lost["NSV This Year Rs"] = 0
    lost["NSV Last Year Same Months Rs"] = (lost["LY"] * 100000).round(0)
    lost = lost[["Store Key", "Chain", "State", "Zone", "Store Type", "NFL Kind", "LY Months Sold", "Growth Basis", "NSV This Year Rs", "NSV Last Year Same Months Rs"]]
    pd.concat([a, lost], ignore_index=True).assign(**{"Period": "Apr-Aug FY27 vs Apr-Aug FY26"}).to_csv(SEED / "store_type_aug26.csv", index=False)
    r = st.attrs["rows"].assign(SType=lambda x: x["sid"].map(st["Type"].where(st["Type"] != "NFL", "NFL " + st["NFL Kind"])))
    r["Month"] = r["file"].map(MONTH_LABEL)
    c = (r.groupby(["Month", "Zone", "Brand", "Category", "Sub_category", "SType"], dropna=False).agg(**{"NSV Rs": ("NSV", "sum"), "Stores Selling": ("sid", "nunique")}).reset_index()
         .rename(columns={"Sub_category": "Sub Category", "SType": "Store Type"}))
    c["NSV Rs"] = (c["NSV Rs"] * 100000).round(0)
    for col in ("Zone", "Brand", "Category", "Sub Category"):
        c[col] = c[col].fillna("Not stated")
    c.insert(1, "FY Year", "FY27")
    c.to_csv(SEED / "sales_cuts_fy27.csv", index=False)
    b = st.attrs["pack_month"].copy()
    b["Month"] = b["file"].map(MONTH_LABEL)
    b["FY Year"] = "FY27"
    b["Pack"] = b["Net Weight"].map(lambda v: f"{int(v)}" if pd.notna(v) else "Not stated")
    b["NSV Rs"] = (b["NSV"] * 100000).round(0)
    b[["Month", "FY Year", "Category", "Pack", "NSV Rs", "Stores"]].rename(columns={"Stores": "Stores Selling"}).to_csv(SEED / "pack_size_monthly_fy27.csv", index=False)


def main():
    out, st = build()
    OUT.write_text(json.dumps(out, indent=1))
    qc = ROOT / "data" / "qc"
    qc.mkdir(exist_ok=True)
    st.reset_index().rename(columns={"sid": "Store Key"}).to_csv(qc / "store_cuts_store_type.csv", index=False)
    JS_OUT.write_text("window.STORE_CUTS=" + json.dumps(out, separators=(",", ":")) + ";\n", encoding="utf-8")
    write_powerbi_seed(st)
    print("total", out["total_ty"], out["stores"], out["lost"])


if __name__ == "__main__":
    main()
