"""
Generate Dist_primary_cont_based_on_secondary_MOM.xlsx from:
  1. Approved Patch CSV  (DistCont_Patch_Approved_*.csv)
  2. Primary CSVs        (Dist chain ten column → chains served per distributor)
  3. Offtake CSVs        (chain × brand × month NSV → % split weights)

Rows from the approved patch take precedence; for everything else the
offtake-derived % from each chain the distributor is known to serve.

Output:
  PowerBI/RawDataFolders/Dist_primary_cont_based_on_secondary_MOM.xlsx
  Sheet: "Dist Primary Conv to Chain Art"  (header=1, i.e. row-0 is metadata)
"""

import sys, re, math
import pandas as pd
from pathlib import Path
from collections import defaultdict

REPO = Path(__file__).resolve().parent.parent
SRC  = REPO / "PowerBI" / "RawDataFolders"
OUT  = SRC  / "Dist_primary_cont_based_on_secondary_MOM.xlsx"

# ── Chain name canonicalizer ──────────────────────────────────────────────────
CHAIN_ALIASES = [
    ("Apollo",           ["apollo", "apollo healthco"]),
    ("Reliance Retail",  ["reliance retail", "reliance", "rrl"]),
    ("Dmart",            ["dmart", "d-mart", "d mart"]),
    ("H&G",              ["h&g", "hng"]),
    ("Lulu",             ["lulu"]),
    ("More Retail",      ["more retail", "more retails", "more"]),
    ("RMT-Sancus",       ["sancus(rmt)", "rmt-sancus", "rmt-delhi",
                          "sancus networks private limited-rmt"]),
    ("VMM",              ["vmm"]),
    ("Spencer",          ["spencer"]),
    ("Guardian",         ["guardian", "guardian healthcare",
                          "guardian healthcare services pvt ltd(dl)"]),
    ("V-Mart",           ["v-mart", "vmart", "v mart"]),
    ("Ratnadeep",        ["ratnadeep"]),
    ("Wellness Forever", ["wellness forever"]),
    ("Walmart",          ["walmart cnc", "walmart"]),
    ("Metro C&C",        ["metro cnc", "metro c&c"]),
    ("Arambagh",         ["arambagh"]),
    ("B&N",              ["b&n", "beauty & nutrie"]),
    ("Sasta Sundar",     ["sasta sundar", "ssl"]),
    ("Frankross",        ["frankros", "frankross", "frank ross"]),
    ("Nykaa (FSN)",      ["fsn", "nykaa"]),
    ("Trent",            ["trent"]),
    ("Sohum Shoppe",     ["sohum shoppe", "sohum"]),
    ("Pothys",           ["pothys"]),
    ("National Mart",    ["national mart"]),
    ("Sumo Save",        ["sumo save", "sumosave"]),
]
_ALIAS_LOOKUP = {}
for _c, _al in CHAIN_ALIASES:
    for _a in _al:
        _ALIAS_LOOKUP[_a.lower()] = _c

KNOWN_CHAINS = set(_c for _c, _ in CHAIN_ALIASES)

def canon_chain(name):
    if name is None or (isinstance(name, float) and math.isnan(name)):
        return None
    k = str(name).replace("\xa0", " ").strip()
    return _ALIAS_LOOKUP.get(k.lower())   # return None if not a known chain

def canon_brand(name):
    if not name or (isinstance(name, float) and math.isnan(name)):
        return None
    s = str(name).strip()
    m = {"bblunt": "BBlunt", "b blunt": "BBlunt", "the derma co.": "The Derma Co.",
         "the derma co": "The Derma Co.", "tdc": "The Derma Co.",
         "mamaearth": "Mamaearth", "mama earth": "Mamaearth",
         "aqualogica": "Aqualogica", "dr. sheth's": "Dr. Sheth's",
         "dr sheth's": "Dr. Sheth's", "dr. sheths": "Dr. Sheth's"}.get(s.lower())
    return m or s

def parse_month_key(v):
    """Return YYYY-MM string from datetime, date string, or 'Apr'26' text."""
    if v is None:
        return None
    if hasattr(v, "year"):
        return f"{v.year:04d}-{v.month:02d}"
    s = str(v).strip()
    if not s or s in ("nan", "NaT"):
        return None
    # date string like 2025-10-01
    m = re.match(r"(\d{4})-(\d{2})", s)
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    # Apr'26 or Apr26 style (handles right-quote ')
    m = re.match(r"([A-Za-z]{3,})['’`]?(\d{2,4})", s)
    if m:
        mon = m.group(1)[:3].title()
        mn = {"Jan":1,"Feb":2,"Mar":3,"Apr":4,"May":5,"Jun":6,
              "Jul":7,"Aug":8,"Sep":9,"Oct":10,"Nov":11,"Dec":12}.get(mon)
        if mn:
            yy = int(m.group(2)[-2:])
            return f"{2000+yy:04d}-{mn:02d}"
    return None

# ── 1. Approved Patch CSV ─────────────────────────────────────────────────────
patch_rows = []
mapping_dir = REPO / "PowerBI" / "SeedData" / "Mapping"
for csv_path in sorted(mapping_dir.glob("DistCont_Patch_Approved_*.csv")):
    pf = pd.read_csv(csv_path)
    pf.columns = [str(c).strip() for c in pf.columns]
    for _, row in pf.iterrows():
        st    = str(row.get("Ship To Name",               "")).strip()
        chain = str(row.get("Chain Name",                 "")).strip()
        brand = str(row.get("Brand",                      "")).strip()
        pct   = row.get("Secondary contribution %")
        mo    = row.get("Revised month")
        if not st or not chain or not brand or mo is None:
            continue
        try:
            pct_f = float(pct)
        except (TypeError, ValueError):
            continue
        pm = parse_month_key(mo)
        if pm is None:
            continue
        patch_rows.append({
            "Ship To Name":              st,
            "Brand":                     brand,
            "Revised month":             pm,
            "Chain Name":                chain,
            "Secondary contribution %":  pct_f,
        })

print(f"Patch rows loaded:  {len(patch_rows)}")

# keys already covered by patch → skip when deriving from offtake
patch_keys = {(r["Ship To Name"].lower(), r["Brand"].lower(), r["Revised month"])
              for r in patch_rows}

# ── 2. Distributor → Chains from primary CSVs ─────────────────────────────────
# dist_chain_map[ship_to_lower] = set of canonical chain names
dist_chain_map   : dict[str, set] = {}
ship_to_raw_map  : dict[str, str] = {}   # ship_lo → prettiest raw name seen
primary_keys_nsv : dict = defaultdict(float)  # (ship_lo, brand, pm) → NSV sum

primary_dir = SRC / "Primary_Article_Monthly"
for csv_path in sorted(primary_dir.glob("primary_article_*.csv")):
    df = pd.read_csv(csv_path, low_memory=False)
    df.columns = [str(c).strip() for c in df.columns]
    if "PO Type" not in df.columns:
        continue
    dist_mask = df["PO Type"].astype(str).str.strip().str.lower().isin(["dist.", "dist"])
    dist_df   = df[dist_mask].copy()
    if dist_df.empty:
        continue

    brand_col = next((c for c in ["brand", "Brand"] if c in dist_df.columns), None)
    nsv_col   = next((c for c in ["Inv. Net value(LOC)", "NSV", "sale in lac"]
                      if c in dist_df.columns), None)
    month_col = next((c for c in ["Month"] if c in dist_df.columns), None)
    chain10_col = "Dist chain ten" if "Dist chain ten" in dist_df.columns else None

    for _, row in dist_df.iterrows():
        st_raw = str(row.get("Ship To Name", "")).strip()
        if not st_raw or st_raw == "nan":
            continue
        st_lo = st_raw.lower()
        ship_to_raw_map.setdefault(st_lo, st_raw)

        # parse chains from slash-separated "Dist chain ten"
        if chain10_col:
            chain10 = str(row.get(chain10_col, "")).strip()
            if chain10 and chain10.lower() not in (st_lo, "nan", ""):
                for part in re.split(r"[/]", chain10):
                    part = part.strip()
                    cc = canon_chain(part)
                    if cc:   # only recognised retail chains
                        dist_chain_map.setdefault(st_lo, set()).add(cc)

        # accumulate primary NSV for keying
        brand = canon_brand(row.get(brand_col)) if brand_col else None
        pm    = parse_month_key(row.get(month_col)) if month_col else None
        nsv   = float(row.get(nsv_col, 0) or 0) if nsv_col else 0
        if brand and pm:
            primary_keys_nsv[(st_lo, brand, pm)] += nsv

print(f"Distributor-chain map entries: {len(dist_chain_map)}")
for k, v in sorted(dist_chain_map.items()):
    print(f"  {k!r:55s} → {sorted(v)}")

# ── 3. Offtake NSV by (canon_chain, canon_brand, YYYY-MM) ────────────────────
offtake_nsv: dict = defaultdict(float)
offtake_dir = SRC / "Offtake_Monthly"

for csv_path in sorted(offtake_dir.glob("offtake_store_article_*.csv")):
    df = pd.read_csv(csv_path, low_memory=False)
    df.columns = [str(c).strip() for c in df.columns]

    # handle two formats:
    #   old: Chain Name, Brand, NSV, Month   (Apr_26 / May_26)
    #   new: Chain, Brand, NSV, MonthKey     (Jun_26+)
    chain_col = next((c for c in ["Chain Name", "Chain"] if c in df.columns), None)
    brand_col = "Brand" if "Brand" in df.columns else None
    nsv_col   = "NSV"   if "NSV"   in df.columns else ("MRP In Lac" if "MRP In Lac" in df.columns else None)
    # prefer the column that produces parseable YYYY-MM month keys:
    # old format: "Month" = "Apr'26" (parseable); new format: "Month" = "Jun" (not parseable, use "MonthKey")
    month_col = None
    for _mc in ["Month", "MonthKey"]:
        if _mc not in df.columns:
            continue
        _sample = str(df[_mc].dropna().iloc[0]).strip() if len(df[_mc].dropna()) > 0 else ""
        if parse_month_key(_sample) is not None:
            month_col = _mc
            break

    if not all([chain_col, brand_col, nsv_col, month_col]):
        print(f"  Skipping {csv_path.name}: missing cols "
              f"(chain={chain_col}, brand={brand_col}, nsv={nsv_col}, month={month_col})")
        continue

    df["_cc"]  = df[chain_col].map(canon_chain)
    df["_br"]  = df[brand_col].map(canon_brand)
    df["_pm"]  = df[month_col].astype(str).map(parse_month_key)
    df["_nsv"] = pd.to_numeric(df[nsv_col], errors="coerce").fillna(0)

    ok = df["_cc"].notna() & df["_br"].notna() & df["_pm"].notna()
    for _, row in df[ok].iterrows():
        offtake_nsv[(row["_cc"], row["_br"], row["_pm"])] += row["_nsv"]

print(f"\nOfftake NSV entries: {len(offtake_nsv)}")
print(f"Offtake months: {sorted(set(pm for (_, _, pm) in offtake_nsv))}")

# ── 4. Derive allocation rows for uncovered (dist, brand, month) ──────────────
def pm_dist(a, b):
    """Months-apart distance between two YYYY-MM strings."""
    y1, m1 = int(a[:4]), int(a[5:7])
    y2, m2 = int(b[:4]), int(b[5:7])
    return abs((y1*12+m1) - (y2*12+m2))

derived_rows  = []
skipped_patch = 0

for (ship_lo, brand, pm), _nsv in sorted(primary_keys_nsv.items()):
    if (ship_lo, brand.lower(), pm) in patch_keys:
        skipped_patch += 1
        continue

    chains = dist_chain_map.get(ship_lo, set())
    if not chains:
        continue

    # lookup offtake NSV for (chain, brand, month) — exact first, then nearest
    def chain_nsv_for_month(target_pm):
        d = {}
        for c in chains:
            nsv = offtake_nsv.get((c, brand, target_pm), 0)
            if nsv > 0:
                d[c] = nsv
        return d

    chain_nsv = chain_nsv_for_month(pm)

    if not chain_nsv:
        # nearest month within 3 months that has offtake for ANY of these chains
        avail_months = sorted(
            set(m for (cc, br, m) in offtake_nsv if br == brand and cc in chains))
        if avail_months:
            near = min(avail_months, key=lambda m: pm_dist(m, pm))
            if pm_dist(near, pm) <= 3:
                chain_nsv = chain_nsv_for_month(near)

    if not chain_nsv:
        # fallback: equal weight across all known chains
        chain_nsv = {c: 1.0 for c in chains}

    total = sum(chain_nsv.values())
    if total <= 0:
        continue

    ship_raw = ship_to_raw_map.get(ship_lo, ship_lo)
    for chain_name, nsv in chain_nsv.items():
        pct = round((nsv / total) * 100, 4)
        derived_rows.append({
            "Ship To Name":             ship_raw,
            "Brand":                    brand,
            "Revised month":            pm,
            "Chain Name":               chain_name,
            "Secondary contribution %": pct,
        })

print(f"\nDerived rows:             {len(derived_rows)}")
print(f"Skipped (covered by patch): {skipped_patch}")

# ── 5. Write xlsx ──────────────────────────────────────────────────────────────
all_rows = patch_rows + derived_rows
if not all_rows:
    print("ERROR: no rows — aborting")
    sys.exit(1)

out_df = pd.DataFrame(all_rows)
out_df = out_df[["Ship To Name","Brand","Revised month","Chain Name",
                  "Secondary contribution %"]]
out_df["Revised month"] = pd.to_datetime(out_df["Revised month"] + "-01")
out_df = out_df.sort_values(
    ["Ship To Name","Brand","Revised month","Chain Name"]).reset_index(drop=True)

print(f"\nTotal rows: {len(out_df)}")
print("\nSample (first 30):")
print(out_df.head(30).to_string())

# The build script reads with header=1 (0-based), so the xlsx needs:
#   row 0: blank / metadata row
#   row 1: column names   ← pandas header row
#   row 2+: data rows
from openpyxl import Workbook

wb = Workbook()
ws = wb.active
ws.title = "Dist Primary Conv to Chain Art"

# row 0 — metadata / blank
ws.append(["Generated by gen_dist_cont_weights.py"])

# row 1 — column headers
COLS = ["Ship To Name", "Brand", "Revised month", "Chain Name", "Secondary contribution %"]
ws.append(COLS)

# row 2+ — data
for _, row in out_df.iterrows():
    ws.append([row["Ship To Name"], row["Brand"], row["Revised month"],
               row["Chain Name"], float(row["Secondary contribution %"])])

wb.save(OUT)
print(f"\nWrote: {OUT}  ({len(out_df)} data rows, header at row 1)")
