#!/usr/bin/env python3
"""Restate the FY26 Primary block of dashboard/data.js on the MT basis (CB-01 Decision 3, approved by the repo owner 2026-10-08).

What it does
  FY26 Primary was published all-channel (Rs 32,900.36 L = MT 30,684.99 + EB2B 1,965.20 + SIS 250.17). MT views must carry MT only, as FY27 already does.
  This patches ONLY the `primary` block of an existing data.js (nothing else is touched) from the tracked article-level files
  PowerBI/RawDataFolders/Primary_Article_Monthly/primary_article_<Mon>_25|26.csv (FY'25-26 rows, `Channel` column):

    nsv_fy26      -> MT total (30,684.99 L), tied to detail_meta.channel_totals.FY26.MT
    monthly_fy26  -> workbook month minus that month's non-MT (article-level months tie to the workbook month for month)
    by_zone       -> workbook zone minus non-MT in that zone (article-level zone of the non-MT rows)
    by_brand      -> workbook brand minus non-MT of that brand
    by_chain      -> the 8 chains that are 100% non-MT leave the MT list (Nykaa (FSN), Shoppers Stop, Azorte, Eremedium, Lifestyle,
                     Ascent Wellness, Broadway, Today's Basket); every other chain is unchanged
    by_channel    -> unchanged (it is the all-channel reference: MT + EB2B + SIS = 32,900.36)

  The original all-channel numbers are kept in `primary.fy26_all_channel`; the removed non-MT is kept in `primary.non_mt_fy26`.
  Idempotent: it always restates from `fy26_all_channel`, so running it twice gives the same file.

What it does not do
  `mrp_fy26` is NOT restated (the workbook MRP basis does not tie to the article-level MRP, so no exact MT split exists); it is labelled all-channel.
  Zones: MT by zone is taken from the article-level rows using the confirmed customer-code zone mapping (Chhattisgarh and Vidarbha -> Central, the
  Gujarat-tagged UP customer -> North), not the older `Zone` tag in the files. The unrestated all-channel workbook zones stay in `fy26_all_channel`.
  The CM2 block is not changed (B3 owns it).

    python scripts/restate_fy26_mt.py [--data dashboard/data.js] [--check]
  --check: print what would change and exit 1 if data.js is not already restated.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_JS = ROOT / "dashboard" / "data.js"
ARTICLE_DIR = ROOT / "PowerBI" / "RawDataFolders" / "Primary_Article_Monthly"
ZONE_MAP = ROOT / "PowerBI" / "SeedData" / "Mapping" / "CustomerCode_Zone_State_Mapping.csv"
FY_TAG = "FY'25-26"
TOL = 0.05                                  # Rs lakh
MONTHS = ["Apr'25", "May'25", "Jun'25", "Jul'25", "Aug'25", "Sep'25", "Oct'25", "Nov'25", "Dec'25", "Jan'26", "Feb'26", "Mar'26"]
ZONE_NAME = {"South-1": "South 1", "South-2": "South 2"}
BRAND_NAME = {"Aqualogica": "Aqualogica", "BBLUNT": "BBlunt", "Dr. Sheth's": "Dr. Sheth's", "Mamaearth": "Mamaearth", "Pure Origin": "Pure Origin",
              "Staze": "Staze", "The Derma Co.": "The Derma Co", "Lumineve": "Lumineve"}
# article-level `Chain name` (stripped) -> the label the pre-aggregated workbook uses, for the chains that are entirely non-MT
CHAIN_NAME = {"Nykaa E-Retail Limited": "Nykaa (FSN)", "Shoppers Stop": "Shoppers Stop", "Azorte": "Azorte", "Eremedium Private Limited": "Eremedium",
              "Lifestyle": "Lifestyle", "Lifestyle Babyshop": "Lifestyle", "Ascent Wellness": "Ascent Wellness", "Broadway": "Broadway",
              "Today's Basket": "Today's Basket"}


def load_data(path: Path):
    text = path.read_text(encoding="utf-8")
    i = text.index("{")
    return text[:i], json.loads(text[i:text.rindex("}") + 1])


def write_data(path: Path, prefix: str, data) -> None:
    path.write_text(prefix + json.dumps(data, indent=1, ensure_ascii=False) + ";\n", encoding="utf-8")


def mapped_zone(d: pd.DataFrame, mapping: Path = ZONE_MAP) -> pd.Series:
    """Zone per customer code from the confirmed CustomerCode_Zone_State_Mapping (Chhattisgarh and Vidarbha -> Central, UP -> North).
    The article files carry an older Zone tag (CG and Vidarbha in West, one UP customer in West); the mapping wins, the file tag is the fallback."""
    m = pd.read_csv(mapping, dtype=str).drop_duplicates("Customer Code").set_index("Customer Code")["Zone"]
    code = pd.to_numeric(d["Cust-SAP Code"], errors="coerce").astype("Int64").astype(str)
    return code.map(m).fillna(d["Zone"]).map(lambda z: ZONE_NAME.get(z, z))


def article_level(folder: Path = ARTICLE_DIR) -> pd.DataFrame:
    """FY'25-26 rows of the tracked article-level primary files, with a normalised MT / non-MT flag."""
    frames = []
    names = [f"primary_article_{m.split(chr(39))[0]}_{m.split(chr(39))[1]}.csv" for m in MONTHS]      # Apr_25 ... Mar_26
    for f in sorted(str(folder / n) for n in names if (folder / n).exists()):
        d = pd.read_csv(f, low_memory=False, usecols=["FY", "Month", "Zone", "Cust-SAP Code", "Chain name", "brand", "sale in lac", "Channel"])
        frames.append(d[d["FY"] == FY_TAG])
    d = pd.concat(frames, ignore_index=True)
    d["Zone"] = mapped_zone(d)
    d["is_mt"] = d["Channel"].astype(str).str.strip().str.upper().eq("MT")
    d["Chain name"] = d["Chain name"].astype(str).str.strip()
    return d


def r2(v) -> float:
    return round(float(v), 2) + 0.0          # + 0.0 turns -0.0 into 0.0


def restate(data: dict, art: pd.DataFrame) -> dict:
    """Restate data['primary'] in place from its all-channel snapshot. Returns a small report. Raises ValueError when a tie-out fails."""
    p = data["primary"]
    snap = p.get("fy26_all_channel")
    if snap is None:                                   # first run: keep the published all-channel numbers
        snap = {"nsv_fy26": p["nsv_fy26"], "monthly_fy26": copy.deepcopy(p["monthly_fy26"]), "by_zone": copy.deepcopy(p["by_zone"]),
                "by_brand": copy.deepcopy(p["by_brand"]), "by_chain": copy.deepcopy(p["by_chain"]), "mrp_fy26": p.get("mrp_fy26")}
    nm = art[~art["is_mt"]]
    mt_total = r2(art[art["is_mt"]]["sale in lac"].sum())
    all_total = r2(art["sale in lac"].sum())
    cert = data["detail_meta"]["channel_totals"]["FY26"]["MT"]
    if abs(mt_total - cert) > TOL:
        raise ValueError(f"article-level MT FY26 {mt_total} does not tie to detail_meta.channel_totals.FY26.MT {cert}")
    if abs(all_total - snap["nsv_fy26"]) > TOL:
        raise ValueError(f"article-level all-channel FY26 {all_total} does not tie to the published all-channel {snap['nsv_fy26']}")

    # months: article-level month must tie to the workbook month (so subtracting non-MT is exact)
    nm_month = nm.groupby("Month")["sale in lac"].sum()
    all_month = art.groupby("Month")["sale in lac"].sum()
    monthly = []
    for lab, v, mon in zip(p["month_labels"], snap["monthly_fy26"], MONTHS):
        if abs(all_month.get(mon, 0) - v) > TOL:
            raise ValueError(f"month {mon}: article-level {all_month.get(mon, 0):.2f} vs workbook {v}")
        monthly.append(r2(v - nm_month.get(mon, 0)))

    nm_zone = nm.assign(z=nm["Zone"].map(lambda z: ZONE_NAME.get(z, z))).groupby("z")["sale in lac"].sum()
    mt_zone = art[art["is_mt"]].assign(z=art["Zone"].map(lambda z: ZONE_NAME.get(z, z))).groupby("z")["sale in lac"].sum()
    zones = [{**z, "fy26": r2(mt_zone.get(z["name"], 0))} for z in snap["by_zone"]]      # MT by mapped zone (CG, Vidarbha -> Central)
    nm_brand = nm.assign(b=nm["brand"].map(lambda b: BRAND_NAME.get(b, b))).groupby("b")["sale in lac"].sum()
    brands = [({**b, "fy26": r2((b["fy26"] or 0) - nm_brand.get(b["name"], 0))} if b["fy26"] is not None else dict(b)) for b in snap["by_brand"]]

    nm_chain = nm.assign(c=nm["Chain name"].map(lambda c: CHAIN_NAME.get(c, c))).groupby("c")["sale in lac"].sum()
    chains, removed = [], []
    for c in snap["by_chain"]:
        v = c["fy26"]
        n = nm_chain.get(c["name"], 0)
        if v is not None and n and abs(v - n) <= TOL:       # entirely non-MT: leaves the MT list
            removed.append({"name": c["name"], "fy26": v})
        elif n and abs(n) > TOL:
            raise ValueError(f"chain {c['name']} is partly non-MT ({n} of {v}); not handled")
        else:
            chains.append(dict(c))

    mt_from_zones = r2(sum(z["fy26"] for z in zones))
    mt_from_months = r2(sum(monthly))
    mt_from_brands = r2(sum(b["fy26"] or 0 for b in brands))
    mt_from_chains = r2(sum(c["fy26"] or 0 for c in chains))
    for name, v in (("zones", mt_from_zones), ("months", mt_from_months), ("brands", mt_from_brands), ("chains", mt_from_chains)):
        if abs(v - mt_total) > 0.1:
            raise ValueError(f"restated {name} sum {v} does not tie to MT total {mt_total}")

    non_mt = {"total": r2(nm["sale in lac"].sum()),
              "by_zone": [{"name": k, "fy26": r2(v)} for k, v in nm_zone.sort_values(ascending=False).items()],
              "by_brand": [{"name": k, "fy26": r2(v)} for k, v in nm_brand.sort_values(ascending=False).items()],
              "by_chain": removed, "by_channel": [{"name": k, "fy26": r2(v)} for k, v in
                                                   art[~art["is_mt"]].assign(ch=art["Channel"].astype(str).str.strip().str.upper()).groupby("ch")["sale in lac"].sum().items()],
              "monthly_fy26": [r2(nm_month.get(m, 0)) for m in MONTHS]}
    p["fy26_all_channel"] = snap
    p["non_mt_fy26"] = non_mt
    p["nsv_fy26"] = mt_total
    p["monthly_fy26"] = monthly
    p["by_zone"], p["by_brand"], p["by_chain"] = zones, brands, chains
    p["n_chains"] = len(chains)
    p["mrp_fy26_basis"] = "all-channel, NOT restated: the workbook MRP does not tie to the article-level MRP, so no exact MT split exists"
    p["restatement"] = {"basis": "MT only", "decision": "CB-01 Decision 3 (B): restate FY26 on the MT basis", "approved": "repo owner (aswalsheshant-cell), 2026-10-08",
                        "all_channel_nsv_fy26": snap["nsv_fy26"], "mt_nsv_fy26": mt_total, "non_mt_nsv_fy26": non_mt["total"],
                        "source": "PowerBI/RawDataFolders/Primary_Article_Monthly (FY'25-26 rows), tied to detail_meta.channel_totals.FY26",
                        "zone_basis": "MT by zone from article-level rows via CustomerCode_Zone_State_Mapping (CG + Vidarbha in Central); fy26_all_channel keeps the workbook zones"}
    return {"mt_total": mt_total, "all_channel": snap["nsv_fy26"], "non_mt": non_mt["total"], "chains_removed": [c["name"] for c in removed]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", default=str(DATA_JS))
    ap.add_argument("--check", action="store_true", help="exit 1 when data.js is not already restated; write nothing")
    a = ap.parse_args(argv)
    path = Path(a.data)
    prefix, data = load_data(path)
    before = json.dumps(data["primary"], sort_keys=True)
    rep = restate(data, article_level())
    changed = json.dumps(data["primary"], sort_keys=True) != before
    print(f"FY26 primary: all-channel {rep['all_channel']:,.2f} L -> MT {rep['mt_total']:,.2f} L (non-MT {rep['non_mt']:,.2f} L); chains leaving MT: {', '.join(rep['chains_removed'])}")
    if a.check:
        return 1 if changed else 0
    if changed:
        write_data(path, prefix, data)
        print("wrote", path)
    else:
        print("already restated: nothing to write")
    return 0


if __name__ == "__main__":
    sys.exit(main())
