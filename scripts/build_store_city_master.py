#!/usr/bin/env python3
"""Maintain the store master with city details: PowerBI/SeedData/Masters/Store_City_Master.csv

Inputs
  --master   the chain-wise store list workbook (.xlsb or .xlsx), sheet with: Chain Name, Site Code, Site Name, Zone, State, City
             (e.g. Final_Jan26_to_June26_chainwise_storelist.xlsb). The workbook itself stays outside Git.
  offtake    PowerBI/RawDataFolders/Offtake_Monthly/offtake_store_article_<Mon>_26.csv for the months given. Stores that sold in
             those months but are not in the master are appended (Source = "Offtake file, not in master").

One row per store. Identity (Store Key) = standard chain name | site code; chain | store name or chain | city where there is no code.
Every chain is written with ONE standard spelling (scripts/visit_cities.py CHAIN_STANDARD); an unknown spelling stops the build.
States are written with one standard spelling; a regional grouping in the source (UP/UK, Punjab/J&K/Hp) is replaced by the state its
city belongs to, and a city that sits in two states takes the state most of its stores use (State Note says so; the source value is kept).
Zone is the source zone, tidied for case only: where one state carries two zones the QC report lists it for you to confirm.

QC gate (the build stops on any ERROR, writes Store_City_Master_QC.csv with every finding):
  chain spelling known and unique | Store Key unique | one (chain, site code) per row | one state spelling per state |
  no leading/trailing/double spaces | no mixed-case duplicates of a city.

City rule (City Final): the master city when it is a city the offtake files also use (or a listed city), else the offtake city.
No employee, SO or ASE columns.

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
NEW_SOURCE = "Offtake file, not in master"


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
    out = pd.DataFrame([[r[i] if i < len(r) else None for i in want.values()] for r in rows[head + 1:]], columns=list(want))
    out = out.dropna(subset=["Chain Name"])
    out["Chain Raw"] = out["Chain Name"].map(lambda s: re.sub(r"\s+", " ", str(s)).strip())
    out["Chain"] = out["Chain Raw"].map(vc.std_chain)
    unknown = sorted(out.loc[out["Chain"].isna(), "Chain Raw"].unique())
    if unknown:
        raise ValueError(f"chain spelling(s) in the store list not in CHAIN_STANDARD: {unknown}")
    out["code"] = out["Site Code"].map(vc.norm_code)
    for c in ("Site Name", "State", "City"):
        out[c] = out[c].map(vc.clean)
    out["Zone"] = out["Zone"].map(vc.norm_zone)
    return out.drop(columns=["Chain Name", "Site Code"])


def sid_of(r):
    if r["code"]:
        return f"{r['Chain']}|{r['code']}"
    return f"{r['Chain']}|{r['Site Name'] or r['City'] or ''}"


def tidy_city(c):
    return c.title() if isinstance(c, str) and (c.isupper() or c.islower()) else c


def resolve_states(df):
    """Standard state per row; groups and two-state cities resolved from the stores of the same city."""
    std = df["State (as in source)"].map(vc.std_state)
    df["State"] = std.map(lambda t: t[0])
    df["is_group"] = std.map(lambda t: t[1])
    df["State Note"] = None
    known = df[df["State"].notna() & (df["State"] != "Pan India") & df["City Final"].notna()]
    ctab = known.groupby(known["City Final"].str.lower())["State"].agg(lambda s: s.value_counts().index[0])
    nstates = known.groupby(known["City Final"].str.lower())["State"].nunique()
    for i, r in df.iterrows():
        key = r["City Final"].lower() if isinstance(r["City Final"], str) else None
        if r["is_group"] or r["State"] is None:
            if key in ctab.index:
                df.at[i, "State"] = ctab[key]
                df.at[i, "State Note"] = f"regional grouping '{r['State (as in source)']}' replaced by the state of {r['City Final']}"
        elif key in ctab.index and nstates[key] > 1 and r["State"] != ctab[key] and r["State"] != "Pan India":
            df.at[i, "State Note"] = f"{r['City Final']} also appears under {r['State']}; set to {ctab[key]} (most stores)"
            df.at[i, "State"] = ctab[key]
    return df.drop(columns=["is_group"])


def qc(out):
    """List of (severity, check, count, examples). ERROR findings stop the build."""
    f = []

    def add(sev, check, bad):
        if len(bad):
            f.append((sev, check, len(bad), "; ".join(map(str, list(bad)[:6]))))
    add("ERROR", "Store Key is not unique", out.loc[out["Store Key"].duplicated(keep=False), "Store Key"])
    coded = out[out["Site Code"].notna()]
    add("ERROR", "same chain + site code on more than one row", coded.loc[coded.duplicated(["Chain Name", "Site Code"], keep=False), "Store Key"])
    names = out["Chain Name"].dropna().unique()
    norm = {}
    for n in names:
        norm.setdefault(vc._n(n), set()).add(n)
    add("ERROR", "more than one spelling of a chain", [sorted(v) for v in norm.values() if len(v) > 1])
    add("ERROR", "chain name not a standard chain", [n for n in names if n not in vc.CHAIN_STANDARD])
    add("ERROR", "state is not a standard state", sorted(set(out["State"].dropna()) - set(vc.STATE_STANDARD.values())))
    for col in ("Chain Name", "Store Name", "City Final", "State", "Zone"):
        s = out[col].dropna().astype(str)
        add("ERROR", f"{col}: leading, trailing or double spaces", s[(s != s.str.strip()) | s.str.contains(r"\s{2,}")])
    c = out["City Final"].dropna()
    low = c.groupby(c.str.lower()).agg(lambda s: sorted(set(s)))
    add("ERROR", "a state name sits in the city column", [c for c in out["City Final"].dropna().unique() if vc.is_state_name(c)])
    add("ERROR", "same city spelt with different capitals", [v for v in low if len(v) > 1])
    # warnings: things to confirm, not build failures
    sz = out.dropna(subset=["State", "Zone"]).groupby("State")["Zone"].agg(lambda s: sorted(set(s)))
    add("WARN", "state carried in more than one zone (confirm the zone for these)", [f"{k}: {', '.join(v)}" for k, v in sz.items() if len(v) > 1])
    dn = out[out["Store Name"].notna()]
    dd = dn[dn.duplicated(["Chain Name", "Store Name", "City Final"], keep=False)]
    add("WARN", "same chain + store name + city under different codes (possible duplicate store)", dd["Store Key"])
    add("WARN", "state changed to the city's main state", out.loc[out["State Note"].notna() & out["State Note"].str.contains("also appears", na=False), "Store Key"])
    add("WARN", "no city for the store", out.loc[out["City Final"].isna(), "Store Key"])
    return f


def build(master_path, months):
    m = read_master(master_path)
    off = vc.load_offtake(months)
    m["sid"] = m.apply(sid_of, axis=1)
    dup_master = int(m.duplicated("sid", keep=False).sum())
    m = m.drop_duplicates("sid", keep="first")

    mode = lambda s: s.dropna().mode().iloc[0] if s.notna().any() else None   # noqa: E731
    stores = off.groupby("sid").agg(Chain=("Chain", "first"), Chain_Raw=("Chain Raw", mode), Code=("code", "first"), Name=("Site Name", mode),
                                    OCity=("City", mode), OState=("State", mode), OZone=("Zone", mode), Type=("Store Type", "first"),
                                    OKey=("Offtake Key", mode)).reset_index()
    known = {str(c).lower() for c in off["City"].dropna().unique() if not vc.is_state_name(c)} | set(vc.LISTED) | set(vc.ALIASES) | set(vc.NEAR)

    merged = m.merge(stores[["sid", "OCity", "Type", "OKey"]], on="sid", how="left")
    merged["Source"] = MASTER_SOURCE
    new = stores[~stores["sid"].isin(set(m["sid"]))].rename(columns={"Name": "Site Name", "OState": "State", "OZone": "Zone", "Chain_Raw": "Chain Raw"})
    new["City"] = None
    new["code"] = new["Code"]
    new["Source"] = NEW_SOURCE
    keep = ["sid", "Chain", "Chain Raw", "code", "Site Name", "Zone", "State", "City", "OCity", "Type", "OKey", "Source"]
    allr = pd.concat([merged[keep], new[keep]], ignore_index=True)
    allr["State (as in source)"] = allr["State"]

    def final(r):
        mc, oc = tidy_city(r["City"]), tidy_city(r["OCity"])
        mc = None if vc.is_state_name(mc) else mc          # a state name in the city field is not a city
        oc = None if vc.is_state_name(oc) else oc
        if isinstance(mc, str) and mc.lower() in known:
            return mc, "Master"
        if isinstance(oc, str):
            return oc, "Offtake file"
        return (mc, "Master (locality, no city in offtake)") if isinstance(mc, str) else (None, "Not available")
    fin = allr.apply(final, axis=1, result_type="expand")
    allr["City Final"], allr["City Source"] = fin[0], fin[1]
    # one spelling per city: the most frequent capitalisation among the stores
    spell = allr["City Final"].dropna().groupby(allr["City Final"].dropna().str.lower()).agg(lambda s: s.value_counts().index[0])
    allr["City Final"] = allr["City Final"].map(lambda c: spell[c.lower()] if isinstance(c, str) else c)
    allr = resolve_states(allr)
    cls = allr["City Final"].map(vc.classify)
    allr["Visit City"] = cls.map(lambda t: t[0])
    allr["Visit Status"] = cls.map(lambda t: t[1])
    allr["Nearest Listed City"] = cls.map(lambda t: t[2])
    allr["Visit Region"] = allr["Visit City"].map(vc.CITY_REGION)
    # Match Key for Power BI: chain as spelt in the offtake file (upper case) | site code, blank where the store has no code
    allr["Match Key"] = [f"{str(raw).upper()}|{code}" if isinstance(code, str) and code else None for raw, code in zip(allr["Chain Raw"], allr["code"])]
    out = allr.rename(columns={"sid": "Store Key", "Chain": "Chain Name", "Chain Raw": "Chain (as in source)", "code": "Site Code", "Site Name": "Store Name",
                               "City": "City (store list)", "OCity": "City (offtake file)", "Type": "Store Type"})
    out["Store Type"] = out["Store Type"].map(lambda v: v.strip() if isinstance(v, str) else None)
    cols = ["Store Key", "Chain Name", "Chain (as in source)", "Site Code", "Store Name", "Zone", "State", "State (as in source)", "State Note", "City (store list)",
            "City (offtake file)", "City Final", "City Source", "Visit City", "Visit Region", "Visit Status", "Nearest Listed City", "Store Type", "Match Key", "Source"]
    out = out[cols].sort_values(["Chain Name", "State", "City Final", "Store Name"], na_position="last").reset_index(drop=True)
    findings = qc(out)
    return out, findings, {"dup_in_master_file": dup_master, "from_master": len(m), "added": int((out["Source"] == NEW_SOURCE).sum())}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--master", type=Path, required=True)
    ap.add_argument("--months", nargs="+", default=vc.MONTHS)
    a = ap.parse_args()
    out, findings, stats = build(a.master, a.months)
    OUT.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(findings, columns=["Severity", "Check", "Count", "Examples"]).to_csv(OUT / "Store_City_Master_QC.csv", index=False)
    errors = [f for f in findings if f[0] == "ERROR"]
    for sev, check, n, ex in findings:
        print(f"[{sev}] {check}: {n}  e.g. {ex[:160]}")
    if errors:
        raise SystemExit(f"Not written: {len(errors)} QC error(s) above (see Store_City_Master_QC.csv).")
    out.to_csv(OUT / "Store_City_Master.csv", index=False)
    cities = [{"Region": r, "City": c, "Beats Planned (rule)": "", "Aliases": "; ".join(k.title() for k, v in vc.ALIASES.items() if v == c),
               "Near Listed (not on list)": "; ".join(k.title() for k, v in vc.NEAR.items() if v == c)} for r, cs in vc.REGIONS.items() for c in cs]
    pd.DataFrame(cities).to_csv(OUT / "Visit_City_List.csv", index=False)
    print(f"store master rows: {len(out)}  (store list {stats['from_master']}, added from offtake {stats['added']}, duplicate rows in the store list collapsed {stats['dup_in_master_file']})")
    print(out["Visit Status"].value_counts().to_string())


if __name__ == "__main__":
    main()
