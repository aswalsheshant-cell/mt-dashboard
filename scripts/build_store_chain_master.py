#!/usr/bin/env python3
"""
Extract a canonical Store x Chain Master from the raw offtake extracts, run a
QC audit over it, and emit CSV + JSON + a compact block for data.js.

    python scripts/build_store_chain_master.py --src PowerBI/RawDataFolders \
        --out dashboard/data.js

Store identity across the source vintages is NOT uniform, and that shapes
everything below:
  Apr/May-26 CSV : Zone, State, City, Chain Name, Store Type, DC Code,
                   Site Code, Site Name        -> full store grain
  Jun-26    CSV : Chain, Store (store NAME, no code, no geography)
  Jun-26    XLSX: Chain Name, Zone, State only -> no store grain at all
So a site CODE exists only in the Apr/May vintage; Jun contributes names.
Records are keyed on (Canonical_Chain, Site_Code) rather than Site_Code alone
because the codes are per-chain sequences and DO collide across chains -- see
the duplicate-code QC below, which reports collisions instead of silently
merging two different stores into one row.
"""
import argparse, csv, json, re, sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import importlib.util
_spec = importlib.util.spec_from_file_location(
    "_bdd", Path(__file__).resolve().parent / "build_dashboard_data.py")
_bdd = importlib.util.module_from_spec(_spec)
try:
    _spec.loader.exec_module(_bdd)
except SystemExit:
    pass

canon_chain = _bdd.canon_chain
canon_zone = _bdd.canon_zone
chain_grain_group = _bdd.chain_grain_group
NA = "N/A"
PAN_INDIA = "Pan India"

COLS = ["Site_Code", "Store_Name", "Canonical_Chain", "Raw_Chain_Alias", "Channel",
        "Zone", "State", "City", "Store_Type", "Mapping_Status"]

# column-name synonyms across the source vintages
_SYN = {
    "site":   ["Site Code", "Store Code", "SiteCode", "StoreCode"],
    "name":   ["Site Name", "Store Name", "SiteName", "StoreName", "Store"],
    "chain":  ["Chain Name", "Chain"],
    "zone":   ["Zone"],
    "state":  ["State"],
    "city":   ["City"],
    "stype":  ["Store Type", "StoreType"],
}

def _pick(cols, keys):
    for k in keys:
        if k in cols:
            return k
    return None

def norm_code(v):
    """Trim, drop a float tail ('2302.0' -> '2302'), uppercase."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    s = str(v).strip()
    if not s or s.lower() in ("nan", "none", "null", "-"):
        return None
    if re.fullmatch(r"\d+\.0+", s):
        s = s.split(".")[0]
    return s.upper()

def norm_txt(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    s = " ".join(str(v).split())
    return s or None

def norm_store_type(v):
    s = (norm_txt(v) or "").lower()
    if "brand counter" in s and "non" not in s:
        return "BA"
    if s:
        return "Macro"
    return None          # unknown -> caller defaults to Macro

def read_frames(src):
    """Yield (path, DataFrame) for EVERY offtake source that carries a chain
    column. Unlike the offtake aggregator this does not pick one file per month
    -- the master wants every store sighting it can get, and duplicate sightings
    collapse during aggregation."""
    seen = set()
    for d in (src, src / "Offtake_Monthly"):
        if not d.exists():
            continue
        for pat in ("*.csv", "*.xlsx", "*.xlsm", "*.xlsb"):
            for fp in sorted(d.glob(pat)):
                if fp.name.startswith(("_TEMPLATE", "~$")) or fp.name in seen:
                    continue
                if "offtake" not in fp.name.lower():
                    continue
                seen.add(fp.name)
                try:
                    if fp.suffix.lower() == ".csv":
                        df = pd.read_csv(fp, low_memory=False)
                    elif fp.suffix.lower() == ".xlsb":
                        df = pd.read_excel(fp, sheet_name=0, header=1, engine="pyxlsb")
                    else:
                        df = pd.read_excel(fp, sheet_name=0)
                except Exception as e:
                    print(f"  skip {fp.name}: unreadable ({type(e).__name__})")
                    continue
                df.columns = [" ".join(str(c).split()) for c in df.columns]
                if _pick(set(df.columns), _SYN["chain"]):
                    yield fp, df

def chain_channel_map(data_js):
    """Chain -> Channel, learned from the article-level detail already in
    data.js (the offtake extracts carry no Channel column at all). Verified
    1:1 -- every banner trades in exactly one channel in this dataset."""
    try:
        txt = Path(data_js).read_text()
        obj = json.loads(txt[txt.index("{"): txt.rstrip().rstrip(";").rindex("}") + 1])
    except Exception:
        return {}
    m = {}
    for r in obj.get("detail_records", []):
        c, ch = r.get("Chain"), r.get("Channel")
        if c and ch:
            m.setdefault(c, ch)
    return m

def name_key(s):
    """Loose store-name key for cross-vintage linkage."""
    return re.sub(r"[^a-z0-9]", "", str(s or "").lower()) or None

def build_name_to_code(frames):
    """Site Name -> Site Code, learned from the vintages that carry BOTH.

    This is the linkage that makes the master canonical. The Jun-26 export
    identifies stores by NAME only while Apr/May-26 identify them by CODE, so
    without this join the SAME physical store is cataloged twice -- once keyed
    by code and once by name. That inflated Apollo to 7,358 "missing code"
    rows against only 7,254 real codes. 92.5% of Jun's names resolve here.
    A name that maps to more than one code is left unresolved rather than
    guessed at."""
    lut = {}
    for _fp, df in frames:
        cols = set(df.columns)
        c_site, c_name = _pick(cols, _SYN["site"]), _pick(cols, _SYN["name"])
        if not c_site or not c_name:
            continue
        sub = df[[c_site, c_name]].dropna().drop_duplicates()
        for cd, nm in sub.itertuples(index=False):
            k, c = name_key(nm), norm_code(cd)
            if k and c:
                lut.setdefault(k, set()).add(c)
    return {k: next(iter(v)) for k, v in lut.items() if len(v) == 1}

def build(src, data_js):
    chan_of = chain_channel_map(data_js)
    frames = list(read_frames(src))
    n2c = build_name_to_code(frames)
    print(f"  name->code linkage: {len(n2c):,} unambiguous store names")

    stores = {}          # (canonical_chain, key) -> record
    conflicts = {}       # site_code -> set(canonical chains)
    code_owner = {}
    stats = {"files": 0, "rows": 0, "rows_with_code": 0, "code_from_name": 0}

    for fp, df in frames:
        cols = set(df.columns)
        c_chain = _pick(cols, _SYN["chain"])
        c_site = _pick(cols, _SYN["site"])
        c_name = _pick(cols, _SYN["name"])
        c_zone = _pick(cols, _SYN["zone"])
        c_state = _pick(cols, _SYN["state"])
        c_city = _pick(cols, _SYN["city"])
        c_type = _pick(cols, _SYN["stype"])
        stats["files"] += 1
        print(f"  {fp.name}: chain={c_chain} site={c_site} name={c_name} "
              f"zone={c_zone} state={c_state} city={c_city} type={c_type}")

        sub = df[[c for c in (c_chain, c_site, c_name, c_zone, c_state, c_city, c_type)
                  if c]].copy()
        sub = sub[sub[c_chain].notna()]
        # collapse to distinct store sightings before the python loop -- the raw
        # frames are ~230k article rows each and only a few thousand stores
        sub = sub.drop_duplicates()
        stats["rows"] += len(sub)

        for rec in sub.to_dict("records"):
            raw_chain = norm_txt(rec.get(c_chain)) or ""
            canon = canon_chain(raw_chain) or raw_chain
            group = chain_grain_group(canon)
            code = norm_code(rec.get(c_site)) if c_site else None
            name = norm_txt(rec.get(c_name)) if c_name else None
            # A vintage that gives only a NAME (Jun-26's "Store") still points
            # at a real store -- resolve it to that store's Site Code so both
            # sightings collapse onto ONE master row instead of two.
            if not code and name:
                resolved = n2c.get(name_key(name))
                if resolved:
                    code = resolved
                    stats["code_from_name"] += 1
            zone = canon_zone(rec.get(c_zone)) if c_zone else None
            state = norm_txt(rec.get(c_state)) if c_state else None
            city = norm_txt(rec.get(c_city)) if c_city else None
            stype = norm_store_type(rec.get(c_type)) if c_type else None

            if code:
                stats["rows_with_code"] += 1
                code_owner.setdefault(code, set()).add(canon)

            # ---- permanent grain fallbacks (CHAIN_GRAIN_CONFIG) ----
            if group == "PAN_INDIA_ONLY":
                zone = zone or PAN_INDIA
                state = state or PAN_INDIA
                code = code or NA
                name = name or NA
            elif group == "ZONE_STATE_ONLY":
                code = code or NA
                name = name or NA
            zone = zone or NA
            state = state or NA
            city = city or NA
            stype = stype or "Macro"

            # ---- mapping status ----
            if code == NA:
                status = "PASS"            # declared macro-reporting chain
            elif not code:
                status = "MISSING_SITE_CODE"   # Group C expected a code
                code = NA
                name = name or NA
            elif canon == raw_chain:
                status = "PASS"
            else:
                status = "MAPPED_ALIAS"

            # Keying: real code first. Failing that a name. Failing BOTH, key on
            # geography -- collapsing every anonymous row of a chain into one
            # record made that record inherit every state the chain trades in
            # and show up as a bogus "conflicting state" finding.
            if code and code != NA:
                key = (canon, code)
            elif name and name != NA:
                key = (canon, f"NAME::{name_key(name)}")
            else:
                key = (canon, f"GEO::{zone}|{state}|{city}")
            cur = stores.get(key)
            if cur is None:
                stores[key] = {
                    "Site_Code": code, "Store_Name": name or NA,
                    "Canonical_Chain": canon, "Raw_Chain_Alias": raw_chain,
                    "Channel": chan_of.get(canon, NA),
                    "Zone": zone, "State": state, "City": city,
                    "Store_Type": stype, "Mapping_Status": status,
                    "_aliases": {raw_chain}, "_states": {state} if state != NA else set(),
                }
            else:
                cur["_aliases"].add(raw_chain)
                if state != NA:
                    cur["_states"].add(state)
                # fill blanks from a richer sighting; BA beats Macro
                for f, v in (("Store_Name", name), ("Zone", zone), ("State", state),
                             ("City", city)):
                    if (cur[f] in (NA, None)) and v not in (NA, None):
                        cur[f] = v
                if stype == "BA":
                    cur["Store_Type"] = "BA"
                if cur["Mapping_Status"] == "PASS" and status == "MAPPED_ALIAS":
                    cur["Mapping_Status"] = "MAPPED_ALIAS"

    # ---- QC: a code owned by >1 canonical chain, or a store with >1 state ----
    for code, owners in code_owner.items():
        if len(owners) > 1:
            conflicts[code] = sorted(owners)
    multi_state = []
    for key, r in stores.items():
        if len(r["_states"]) > 1:
            multi_state.append({"chain": r["Canonical_Chain"], "site": r["Site_Code"],
                                "states": sorted(r["_states"])})
        if len(r["_aliases"]) > 1 and r["Mapping_Status"] == "PASS":
            r["Mapping_Status"] = "MAPPED_ALIAS"
        r["Raw_Chain_Alias"] = " | ".join(sorted(a for a in r["_aliases"] if a))

    rows = []
    for r in stores.values():
        r.pop("_aliases", None); r.pop("_states", None)
        rows.append({c: r.get(c, NA) for c in COLS})
    rows.sort(key=lambda r: (r["Canonical_Chain"], str(r["Site_Code"])))
    return rows, conflicts, multi_state, stats

def qc_report(rows, conflicts, multi_state, stats):
    from collections import Counter
    n = len(rows)
    real = [r for r in rows if r["Site_Code"] != NA]
    chains = sorted({r["Canonical_Chain"] for r in rows})
    by_status = Counter(r["Mapping_Status"] for r in rows)
    by_chan = Counter(r["Channel"] for r in rows)
    by_type = Counter(r["Store_Type"] for r in rows)
    by_grain = Counter(chain_grain_group(r["Canonical_Chain"]) for r in rows)
    cov = (len(real) / n * 100) if n else 0.0
    rep = {
        "total_store_records": n,
        "with_real_site_code": len(real),
        "site_code_join_coverage_pct": round(cov, 2),
        "total_canonical_chains": len(chains),
        "by_mapping_status": dict(by_status),
        "by_channel": dict(by_chan),
        "by_store_type": dict(by_type),
        "by_grain_group": dict(by_grain),
        "duplicate_site_codes_across_chains": len(conflicts),
        "duplicate_examples": [{"site": k, "chains": v}
                               for k, v in list(conflicts.items())[:10]],
        "stores_with_conflicting_state": len(multi_state),
        "state_conflict_examples": multi_state[:10],
        "source_files_read": stats["files"],
    }
    return rep

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", default="dashboard/data.js")
    ap.add_argument("--csv", default="PowerBI/SeedData/StoreChainMaster.csv")
    ap.add_argument("--json", default="PowerBI/SeedData/StoreChainMaster.json")
    a = ap.parse_args()
    src = Path(a.src)

    print("reading offtake sources:")
    rows, conflicts, multi_state, stats = build(src, a.out)
    rep = qc_report(rows, conflicts, multi_state, stats)

    Path(a.csv).parent.mkdir(parents=True, exist_ok=True)
    with open(a.csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)
    Path(a.json).write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")

    # inject into data.js (compact: columns + row arrays, ~60% smaller than
    # a list of objects with repeated keys)
    outp = Path(a.out)
    txt = outp.read_text()
    obj = json.loads(txt[txt.index("{"): txt.rstrip().rstrip(";").rindex("}") + 1])
    obj["store_chain_master"] = {
        "columns": COLS,
        "rows": [[r[c] for c in COLS] for r in rows],
        "qc": rep,
    }
    outp.write_text("window.DASH = " + json.dumps(obj, indent=1, ensure_ascii=False) + ";\n")

    print("\n================ STORE x CHAIN MASTER — QC SUMMARY ================")
    print(f"  Total store records cataloged : {rep['total_store_records']:,}")
    print(f"  With a real Site Code         : {rep['with_real_site_code']:,}")
    print(f"  Site Code join coverage       : {rep['site_code_join_coverage_pct']}%")
    print(f"  Total canonical chains        : {rep['total_canonical_chains']}")
    print(f"  Source files read             : {rep['source_files_read']}")
    print(f"  Mapping status                : {rep['by_mapping_status']}")
    print(f"  By channel                    : {rep['by_channel']}")
    print(f"  By store type                 : {rep['by_store_type']}")
    print(f"  By grain group                : {rep['by_grain_group']}")
    print(f"  Duplicate site codes (x-chain): {rep['duplicate_site_codes_across_chains']}")
    for d in rep["duplicate_examples"]:
        print(f"      {d['site']} -> {d['chains']}")
    print(f"  Stores w/ conflicting state   : {rep['stores_with_conflicting_state']}")
    for d in rep["state_conflict_examples"]:
        print(f"      {d['chain']} {d['site']} -> {d['states']}")
    print(f"\n  wrote {a.csv}")
    print(f"  wrote {a.json}")
    print(f"  injected D.store_chain_master into {a.out}")

if __name__ == "__main__":
    main()
