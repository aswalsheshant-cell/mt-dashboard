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
LY_MONTHS = ["Apr'25", "May'25", "Jun'25", "Jul'25", "Aug'25"]


def build():
    d = vc.load_offtake(vc.MONTHS)
    d = d[~d["bc"]].copy()
    d["Net Weight"] = pd.to_numeric(d["Net Weight"], errors="coerce")
    st = d.groupby("sid").agg(Chain=("Chain", "first"), State=("State", lambda s: s.mode().iat[0] if s.notna().any() else None),
                              Zone=("Zone", lambda s: s.mode().iat[0] if s.notna().any() else None), TY=("NSV", "sum"))
    ly = pd.read_csv(LY_FILE)
    ly = ly[ly["Month"].isin(LY_MONTHS)]
    links = dict(pd.read_csv(LINKS)[["LY Store Key", "Store Key"]].values) if LINKS.exists() else {}
    ly["Key"] = ly["Store Key"].map(lambda k: links.get(k, k))
    lys = ly.groupby("Key")["NSV"].sum()
    lych = ly.groupby("Key")["Chain Name"].first()
    st["LY"] = st.index.map(lys).astype(float)
    reliance_no_ly = st["Chain"].eq("Reliance Retail")          # last year only at state level
    st["Type"] = "LFL"
    st.loc[st["LY"].isna() | (st["LY"] <= 0), "Type"] = "NFL"
    st.loc[reliance_no_ly, "Type"] = "No LY store data"
    lost = lys[~lys.index.isin(st.index) & (lys > 0)]
    lost_df = pd.DataFrame({"Chain": lych.reindex(lost.index), "LY": lost})

    def roll(by):
        g = st.groupby(by + ["Type"]).agg(Stores=("TY", "size"), TY=("TY", "sum"), LY=("LY", "sum")).reset_index()
        rows = []
        for key, grp in g.groupby(by):
            key = key if isinstance(key, tuple) else (key,)
            r = dict(zip(by, key))
            for t, tag in (("LFL", "lfl"), ("NFL", "nfl"), ("No LY store data", "noly")):
                x = grp[grp["Type"] == t]
                r[f"{tag}_stores"] = int(x["Stores"].sum())
                r[f"{tag}_ty"] = round(float(x["TY"].sum()), 2)
            r["lfl_ly"] = round(float(grp[grp["Type"] == "LFL"]["LY"].sum()), 2)
            r["ty_total"] = round(float(grp["TY"].sum()), 2)
            r["lfl_growth_pct"] = round((r["lfl_ty"] / r["lfl_ly"] - 1) * 100, 1) if r["lfl_ly"] > 0 else None
            lc = lost_df.groupby("Chain") if by == ["Chain"] else None
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
    out = {
        "period": "Apr-Aug FY27 vs Apr-Aug FY26", "unit": "Rs lakh", "total_ty": round(float(d["NSV"].sum()), 2),
        "stores": {t: int((st["Type"] == t).sum()) for t in ("LFL", "NFL", "No LY store data")},
        "lost": {"stores": int(len(lost_df)), "ly_nsv": round(float(lost_df["LY"].sum()), 2)},
        "by_chain": roll(["Chain"]), "by_state": roll(["State"]), "by_zone": roll(["Zone"]), "by_pack": packs,
        "pack_by_category": [{"category": r["Category"], "pack": int(r["Net Weight"]), "nsv": round(float(r["NSV"]), 2)}
                             for _, r in cat.dropna().sort_values("NSV", ascending=False).head(30).iterrows()],
    }
    return out, st


def main():
    out, st = build()
    OUT.write_text(json.dumps(out, indent=1))
    qc = ROOT / "data" / "qc"
    qc.mkdir(exist_ok=True)
    st.reset_index().rename(columns={"sid": "Store Key"}).to_csv(qc / "store_cuts_store_type.csv", index=False)
    print("total", out["total_ty"], out["stores"], out["lost"])


if __name__ == "__main__":
    main()
