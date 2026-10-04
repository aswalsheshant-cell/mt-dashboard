#!/usr/bin/env python3
"""Chain contribution and chain x range x pack presence from the internal offtake files.

Reads PowerBI/RawDataFolders/Offtake_Monthly/offtake_store_article_<Mon>_26.csv (this year)
and data/raw_drops/_agg/offtake_fy26.json (last year, chain level) and writes two small
aggregate CSVs under data/nielsen/. No store, employee or SO/ASE columns are read.

Basis: offtake published basis, so Reliance Brand Counter rows are left out (CLAUDE.md:
the counter partition applies to Offtake only). NSV is Rs lakh, as in the source.

    python scripts/build_nielsen_chain_view.py --months Apr May Jun Jul Aug --label Aug26
"""
import argparse
import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "PowerBI" / "RawDataFolders" / "Offtake_Monthly"
LY_JSON = ROOT / "data" / "raw_drops" / "_agg" / "offtake_fy26.json"
OUT = ROOT / "data" / "nielsen"
COLS = ["Chain Name", "State", "Brand", "Category", "Sub_category", "Range", "Net Weight", "NSV", "Sales Qty", "Store Type"]
MON = {"Apr": "Apr-25", "May": "May-25", "Jun": "Jun-25", "Jul": "Jul-25", "Aug": "Aug-25", "Sep": "Sep-25"}
FOCUS = {"Shampoo": ("Hair", "Shampoo"), "Face wash": ("Face", "Face Cleanser")}
CHAIN_FIX = {"RATANDEEP": "RATNADEEP"}
STATE_FIX = {  # spelling and case variants in the files -> one name
    "chhatisgarh": "Chhattisgarh", "delhi": "Delhi NCR", "delhi ncr": "Delhi NCR", "delhi/ ncr": "Delhi NCR", "delhi/ncr": "Delhi NCR",
    "mp": "Madhya Pradesh", "mumbai": "Maharashtra", "orissa": "Odisha", "up": "Uttar Pradesh", "up/uk": "Uttar Pradesh",
    "jammu & kasmir": "Jammu & Kashmir", "punjab/j&k/hp": "Punjab", "northeast": "Northeast",
}


def norm_state(s) -> str:
    s = re.sub(r"\s+", " ", str(s)).strip()
    return STATE_FIX.get(s.lower(), s.title() if s.isupper() else s)


def norm_chain(name: str) -> str:
    c = re.sub(r"\s+", " ", str(name)).strip().upper()
    return CHAIN_FIX.get(c, c)


def load(months):
    frames = []
    for m in months:
        d = pd.read_csv(RAW / f"offtake_store_article_{m}_26.csv", low_memory=False, usecols=lambda c: c in COLS)
        d["file"] = m
        frames.append(d)
    d = pd.concat(frames, ignore_index=True)
    d["Chain"] = d["Chain Name"].map(norm_chain)
    d["bc"] = d["Store Type"].astype(str).str.strip().eq("Brand Counter")
    d["State"] = d["State"].map(norm_state)
    d["Brand"] = d["Brand"].astype(str).str.strip()
    return d


def chain_contribution(d, months):
    ty = d[~d.bc].groupby("Chain")["NSV"].sum()
    ty_me = d[(~d.bc) & (d.Brand == "Mamaearth")].groupby("Chain")["NSV"].sum()
    ly_raw = json.loads(LY_JSON.read_text(encoding="utf-8"))["by_chain"]
    ly = {}
    for k, v in ly_raw.items():
        c = norm_chain(k)
        ly[c] = ly.get(c, 0.0) + sum((v.get(MON[m]) or 0) for m in months)
    out = pd.DataFrame({"ty": ty}).join(pd.Series(ly, name="ly"), how="outer").join(ty_me.rename("ty_me"))
    out = out.fillna({"ty": 0.0, "ly": 0.0, "ty_me": 0.0})
    tot_ty, tot_ly = out.ty.sum(), out.ly.sum()
    out["share_ty_pct"] = out.ty / tot_ty * 100
    out["share_ly_pct"] = out.ly / tot_ly * 100
    out["growth_pct"] = ((out.ty / out.ly - 1) * 100).where(out.ly > 0)
    out["contrib_pp"] = (out.ty - out.ly) / tot_ly * 100          # points of total growth
    out["share_of_growth_pct"] = (out.ty - out.ly) / (tot_ty - tot_ly) * 100
    out["mamaearth_pct_of_chain"] = (out.ty_me / out.ty * 100).where(out.ty > 0)
    out = out.sort_values("ty", ascending=False).reset_index().rename(columns={"index": "Chain"})
    return out.round(3), tot_ty, tot_ly


def range_pack_presence(d):
    """For each chain x (Shampoo, Face wash) x range x pack: NSV, states present, states missing."""
    rows = []
    for chain, g in d[~d.bc].groupby("Chain"):
        all_states = sorted(s for s in g.State.unique() if s and s not in ("nan", "Pan India"))
        if len(all_states) < 1 or g.NSV.sum() < 20:               # small chains: not useful for state fill
            continue
        for label, (cat, sub) in FOCUS.items():
            h = g[(g.Sub_category == sub) & g.Brand.isin(["Mamaearth"]) & (g.State != "Pan India")]
            if h.empty:
                continue
            h = h.assign(Range=h.Range.fillna("Unspecified").astype(str).str.strip(),
                         Pack=h["Net Weight"].map(lambda v: "" if pd.isna(v) else f"{int(v)}"))
            for (rng, pack), x in h.groupby(["Range", "Pack"]):
                if x.NSV.sum() <= 0:
                    continue
                present = sorted(x[x.NSV > 0].State.unique())
                rows.append({"Chain": chain, "Category": label, "Range": rng, "Pack": pack, "NSV_lakh": round(x.NSV.sum(), 3),
                             "States_present": len(present), "States_in_chain": len(all_states),
                             "Missing_states": "; ".join(s for s in all_states if s not in present)})
    return pd.DataFrame(rows).sort_values(["Chain", "Category", "NSV_lakh"], ascending=[True, True, False])


def chain_pack_presence(d, min_chain_nsv=100.0):
    """Every pack size Mamaearth sells in each chain (all ranges together), face wash and shampoo."""
    rows = []
    for chain, g in d[~d.bc].groupby("Chain"):
        if g.NSV.sum() < min_chain_nsv:
            continue
        all_states = sorted(s for s in g.State.unique() if s and s not in ("nan", "Pan India"))
        for label, (cat, sub) in FOCUS.items():
            h = g[(g.Sub_category == sub) & (g.Brand == "Mamaearth") & g["Net Weight"].notna()]
            for pack, x in h.groupby(h["Net Weight"].map(lambda v: f"{int(v)}")):
                if x.NSV.sum() <= 0:
                    continue
                # chains that report Pan India only (no state) get States_in_chain = 0: NSV is shown, state count is not
                rows.append({"Chain": chain, "Category": label, "Pack": pack, "NSV_lakh": round(x.NSV.sum(), 3),
                             "States_present": x[(x.NSV > 0) & (x.State != "Pan India")].State.nunique(), "States_in_chain": len(all_states)})
    return pd.DataFrame(rows).sort_values(["Category", "Chain", "NSV_lakh"], ascending=[True, True, False])


def chain_category_gap(d, min_chain_nsv=100.0):
    """Sub-categories that earn >= 2% of our all-chain NSV but are absent or under-weight in a chain."""
    x = d[~d.bc]
    sub_tot = x.groupby("Sub_category")["NSV"].sum()
    tot = sub_tot.sum()
    rows = []
    for chain, g in x.groupby("Chain"):
        ctot = g.NSV.sum()
        if ctot < min_chain_nsv:
            continue
        cs = g.groupby("Sub_category")["NSV"].sum()
        for sub, v in sub_tot.items():
            share_all = v / tot * 100
            if share_all < 2:
                continue
            share_chain = cs.get(sub, 0.0) / ctot * 100
            if share_chain < share_all * 0.6:
                rows.append({"Chain": chain, "Sub_category": sub, "Share_of_all_chain_NSV_pct": round(share_all, 2),
                             "Share_in_this_chain_pct": round(share_chain, 2), "Chain_NSV_lakh": round(ctot, 1),
                             "Status": "Absent" if cs.get(sub, 0.0) <= 0 else "Under-weight",
                             "Gap_NSV_lakh_at_all_chain_mix": round((share_all - share_chain) / 100 * ctot, 1)})
    return pd.DataFrame(rows).sort_values(["Chain", "Gap_NSV_lakh_at_all_chain_mix"], ascending=[True, False])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--months", nargs="+", default=["Apr", "May", "Jun", "Jul", "Aug"])
    ap.add_argument("--label", default="Aug26")
    a = ap.parse_args()
    d = load(a.months)
    contrib, tty, tly = chain_contribution(d, a.months)
    OUT.mkdir(parents=True, exist_ok=True)
    contrib.to_csv(OUT / f"Chain_Contribution_{a.label}.csv", index=False)
    range_pack_presence(d).to_csv(OUT / f"Chain_Range_Pack_Presence_{a.label}.csv", index=False)
    chain_category_gap(d).to_csv(OUT / f"Chain_Category_Gap_{a.label}.csv", index=False)
    chain_pack_presence(d).to_csv(OUT / f"Chain_Pack_Presence_{a.label}.csv", index=False)
    print(f"total offtake (ex Brand Counter) this year {tty:.1f} L, last year same months {tly:.1f} L")
    print(contrib.head(8).to_string())


if __name__ == "__main__":
    main()
