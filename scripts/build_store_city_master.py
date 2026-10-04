#!/usr/bin/env python3
"""Maintain the store master with city details: PowerBI/SeedData/Masters/Store_City_Master.csv

Inputs
  --master   the chain-wise store list workbook (.xlsb or .xlsx), sheet with: Chain Name, Site Code, Site Name, Zone, State, City, key
             (e.g. Final_Jan26_to_June26_chainwise_storelist.xlsb). The workbook itself stays outside Git.
  offtake    PowerBI/RawDataFolders/Offtake_Monthly/offtake_store_article_<Mon>_26.csv for the months given. Stores that sold in
             those months but are not in the master are appended (Source = "Offtake file, not in master"), so the master keeps up
             when a new month arrives.

City rule (City Final): the master city is used when it is a city the offtake files also use (or a listed city); where the master
holds a locality instead (for example Frankros areas), the offtake city is used. City Source says which one won.

Outputs (no employee, SO or ASE columns): Store_City_Master.csv, Visit_City_List.csv, and a short coverage summary on screen.

    python scripts/build_store_city_master.py --master <file.xlsb> --months Apr May Jun Jul Aug
"""
import argparse
import re
from pathlib import Path

import pandas as pd

import visit_cities as vc

ROOT = vc.ROOT
OUT = ROOT / "PowerBI" / "SeedData" / "Masters"
MASTER_SOURCE = "Chain-wise store list Jan-Jun 26"


def read_master(path: Path) -> pd.DataFrame:
    path = Path(path)
    if path.suffix.lower() == ".xlsb":
        from pyxlsb import open_workbook
        with open_workbook(str(path)) as wb, wb.get_sheet(wb.sheets[0]) as sh:
            rows = [[c.v for c in r] for r in sh.rows()]
    else:
        rows = pd.read_excel(path, header=None).values.tolist()
    head = next(i for i, r in enumerate(rows) if "Chain Name" in r)
    cols = rows[head]
    want = {n: cols.index(n) for n in ("Chain Name", "Site Code", "Site Name", "Zone", "State", "City")}
    want["Key"] = want["City"] + 1          # the list's own key column (chain + site code), unlabeled in the file
    out = pd.DataFrame([[r[i] if i < len(r) else None for i in want.values()] for r in rows[head + 1:]], columns=list(want))
    out = out.dropna(subset=["Chain Name"])
    out["Chain"] = out["Chain Name"].map(lambda s: re.sub(r"\s+", " ", str(s)).strip().upper())
    out["Site Code"] = out["Site Code"].map(lambda v: None if v is None or (isinstance(v, float) and pd.isna(v)) else re.sub(r"\.0$", "", str(v).strip()))
    for c in ("Site Name", "State", "City"):
        out[c] = out[c].map(vc.clean)
    out["Zone"] = out["Zone"].map(vc.norm_zone)
    out["Key"] = out["Key"].map(lambda v: None if v is None or (isinstance(v, float) and pd.isna(v)) else re.sub(r"\s+", " ", str(v)).strip())
    out["Chain Raw"] = out["Chain Name"].map(lambda s: re.sub(r"\s+", " ", str(s)).strip())
    return out.drop(columns=["Chain Name"])


def master_key(r, chain_display):   # chain_display here is the exact key prefix used by the offtake files
    code = r["Site Code"]
    if code and code.lower() not in ("not available", "na", "nan"):
        return f"{chain_display}{code}"
    return f"{chain_display}|{r['Site Name'] or r['City'] or ''}"


def build(master_path, months):
    m = read_master(master_path)
    off = vc.load_offtake(months)
    # Store Key = the list's own key (chain + site code), which is what the offtake files call Unique; chain name as spelled in the offtake
    disp = off.groupby("Chain")["Chain Name"].agg(lambda s: re.sub(r"\s+", " ", str(s.mode().iloc[0])).strip()).to_dict()
    m["Chain Display"] = [disp.get(c, raw) for c, raw in zip(m["Chain"], m["Chain Raw"])]
    m["Store Key"] = [k if k else master_key(r, r["Chain Display"]) for k, (_, r) in zip(m["Key"], m.iterrows())]
    m["Dup Rows"] = m.groupby("Store Key")["Store Key"].transform("size")
    m = m.drop_duplicates("Store Key", keep="first")

    stores = off.groupby("sid").agg(
        Chain=("Chain", "first"), Code=("Site Code", "first"), Name=("Site Name", lambda s: s.dropna().mode().iloc[0] if s.notna().any() else None),
        OCity=("City", lambda s: s.dropna().mode().iloc[0] if s.notna().any() else None),
        State=("State", lambda s: s.dropna().mode().iloc[0] if s.notna().any() else None),
        Zone=("Zone", lambda s: s.dropna().mode().iloc[0] if s.notna().any() else None),
        Type=("Store Type", "first")).reset_index().rename(columns={"sid": "Store Key"})
    known = {str(c).lower() for c in off["City"].dropna().unique()} | set(vc.LISTED) | set(vc.ALIASES) | set(vc.NEAR)

    merged = m.merge(stores[["Store Key", "OCity", "Type"]], on="Store Key", how="left")
    new = stores[~stores["Store Key"].isin(set(m["Store Key"]))].copy()
    new["Chain Display"] = new["Chain"].map(lambda c: disp.get(c, c.title()))
    new = new.rename(columns={"Name": "Site Name", "Code": "Site Code", "OCity": "OCity"})
    new["City"] = None
    new["Dup Rows"] = 1
    new["Source"] = "Offtake file, not in master"
    merged["Source"] = MASTER_SOURCE
    allr = pd.concat([merged, new[["Store Key", "Chain", "Chain Display", "Site Code", "Site Name", "Zone", "State", "City", "OCity", "Type", "Dup Rows", "Source"]]], ignore_index=True)

    def tidy(c):
        return c.title() if isinstance(c, str) and (c.isupper() or c.islower()) else c

    def final(r):
        mc, oc = tidy(r["City"]), tidy(r["OCity"])
        if isinstance(mc, str) and mc.lower() in known:
            return mc, "Master"
        if isinstance(oc, str):
            return oc, "Offtake file"
        return (mc, "Master (locality, no city in offtake)") if isinstance(mc, str) else (None, "Not available")
    fin = allr.apply(final, axis=1, result_type="expand")
    allr["City Final"], allr["City Source"] = fin[0], fin[1]
    cls = allr["City Final"].map(vc.classify)
    allr["Visit City"] = cls.map(lambda t: t[0])
    allr["Visit Status"] = cls.map(lambda t: t[1])
    allr["Nearest Listed City"] = cls.map(lambda t: t[2])
    allr["Visit Region"] = allr["Visit City"].map(vc.CITY_REGION)
    out = allr.rename(columns={"Chain Display": "Chain Name", "Site Name": "Store Name", "City": "City (store list)", "OCity": "City (offtake file)", "Type": "Store Type"})
    out["Store Type"] = out["Store Type"].map(lambda v: v.strip() if isinstance(v, str) else None)
    cols = ["Store Key", "Chain Name", "Site Code", "Store Name", "Zone", "State", "City (store list)", "City (offtake file)", "City Final", "City Source",
            "Visit City", "Visit Region", "Visit Status", "Nearest Listed City", "Store Type", "Dup Rows", "Source"]
    out = out[cols].sort_values(["Chain Name", "State", "City Final", "Store Name"], na_position="last")
    return out, m, stores


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--master", type=Path, required=True)
    ap.add_argument("--months", nargs="+", default=vc.MONTHS)
    a = ap.parse_args()
    out, m, stores = build(a.master, a.months)
    OUT.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT / "Store_City_Master.csv", index=False)
    cities = [{"Region": r, "City": c, "Beats Planned (rule)": "", "Aliases": "; ".join(k.title() for k, v in vc.ALIASES.items() if v == c),
               "Near Listed (not on list)": "; ".join(k.title() for k, v in vc.NEAR.items() if v == c)} for r, cs in vc.REGIONS.items() for c in cs]
    pd.DataFrame(cities).to_csv(OUT / "Visit_City_List.csv", index=False)
    print(f"store master rows: {len(out)}  (from master file {len(m)}, added from offtake {int((out['Source'] != MASTER_SOURCE).sum())})")
    print(out["Visit Status"].value_counts().to_string())
    print(out["City Source"].value_counts().to_string())
    print(f"duplicate keys collapsed in the master file: {int((m['Dup Rows'] > 1).sum())}")


if __name__ == "__main__":
    main()
