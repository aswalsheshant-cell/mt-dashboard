"""
Reclassify Madhya Pradesh (North → Central) and Chhattisgarh (West → Central)
across all data layers in the MT pipeline.

Both states belong to the Central zone per ZoneStateMaster.csv, but were
historically tagged North (MP) and West (CG) in transactional data files.
"""
import pandas as pd
import os, re
from pathlib import Path

ROOT = Path("/home/user/mt-dashboard")

# ── Helpers ──────────────────────────────────────────────────────────────────
def reclassify(df, state_col, zone_col, rules):
    """
    rules: list of (state_match_fn, wrong_zone, correct_zone)
    Returns (df_modified, total_changed_count)
    """
    changed = 0
    for match_fn, wrong, correct in rules:
        state_mask = df[state_col].apply(match_fn)
        zone_mask  = df[zone_col].str.strip().str.lower() == wrong.lower()
        mask = state_mask & zone_mask
        n = mask.sum()
        if n:
            df.loc[mask, zone_col] = correct
            changed += n
            print(f"    {match_fn.__doc__}: {wrong} → {correct}: {n} rows")
    return df, changed

def is_mp(s):
    """Madhya Pradesh"""
    return isinstance(s, str) and "madhya" in s.lower()

def is_cg(s):
    """Chhattisgarh"""
    return isinstance(s, str) and "chhattisgarh" in s.lower()

RULES = [
    (is_mp, "North",  "Central"),
    (is_mp, "NORTH",  "Central"),
    (is_cg, "West",   "Central"),
    (is_cg, "WEST",   "Central"),
]

SUMMARY = {}

# ── 1. CustomerCode_Zone_State_Mapping ───────────────────────────────────────
print("\n[1] CustomerCode_Zone_State_Mapping.csv")
path = ROOT / "PowerBI/SeedData/Mapping/CustomerCode_Zone_State_Mapping.csv"
df = pd.read_csv(path, dtype=str)
before_mp = (df["Zone"].str.strip().str.lower() == "north") & df["State"].apply(is_mp)
before_cg = (df["Zone"].str.strip().str.lower() == "west")  & df["State"].apply(is_cg)
print(f"  Before: MP-North={before_mp.sum()}, CG-West={before_cg.sum()}")

df, n = reclassify(df, "State", "Zone", RULES)
df.to_csv(path, index=False)
SUMMARY["CustomerCode_Zone_State_Mapping"] = n
print(f"  → {n} rows reclassified")

# ── 2. ShipToMaster ──────────────────────────────────────────────────────────
print("\n[2] ShipToMaster.csv")
path = ROOT / "PowerBI/SeedData/Masters/ShipToMaster.csv"
df = pd.read_csv(path, dtype=str)
# ShipToMaster has Zone and State columns
df, n = reclassify(df, "State", "Zone", RULES)
df.to_csv(path, index=False)
SUMMARY["ShipToMaster"] = n
print(f"  → {n} rows reclassified")

# ── 3. Offtake Monthly CSVs ─────────────────────────────────────────────────
print("\n[3] Offtake Monthly CSVs")
offtake_dir = ROOT / "PowerBI/RawDataFolders/Offtake_Monthly"
total_offtake = 0
for f in sorted(offtake_dir.glob("offtake_store_article_*.csv")):
    df = pd.read_csv(f, dtype=str, low_memory=False)
    before_mp = ((df["Zone"].str.strip().str.lower().isin(["north"])) & df["State"].apply(is_mp)).sum()
    before_cg = ((df["Zone"].str.strip().str.lower().isin(["west"])) & df["State"].apply(is_cg)).sum()
    df, n = reclassify(df, "State", "Zone", RULES)
    if n:
        df.to_csv(f, index=False)
    print(f"  {f.name}: MP-North_before={before_mp}, CG-West_before={before_cg} → {n} reclassified")
    SUMMARY[f.name] = n
    total_offtake += n
SUMMARY["_TOTAL_OFFTAKE"] = total_offtake

# ── 4. Primary Article Monthly CSVs ─────────────────────────────────────────
print("\n[4] Primary Article Monthly CSVs")
primary_dir = ROOT / "PowerBI/RawDataFolders/Primary_Article_Monthly"
total_primary = 0
for f in sorted(primary_dir.glob("primary_article_*.csv")):
    df = pd.read_csv(f, dtype=str, low_memory=False)
    if "Zone" not in df.columns or "State" not in df.columns:
        print(f"  {f.name}: skipped (no Zone/State columns)")
        continue
    before_mp = ((df["Zone"].str.strip().str.lower().isin(["north"])) & df["State"].apply(is_mp)).sum()
    before_cg = ((df["Zone"].str.strip().str.lower().isin(["west"])) & df["State"].apply(is_cg)).sum()
    df, n = reclassify(df, "State", "Zone", RULES)
    if n:
        df.to_csv(f, index=False)
    print(f"  {f.name}: MP-North_before={before_mp}, CG-West_before={before_cg} → {n} reclassified")
    SUMMARY[f.name] = n
    total_primary += n
SUMMARY["_TOTAL_PRIMARY"] = total_primary

# ── 5. Primary ShipTo pivot ──────────────────────────────────────────────────
print("\n[5] Primary_ShipTo_FY25-26_to_May26.csv")
path = ROOT / "PowerBI/RawDataFolders/Primary_ShipTo_Monthly/Primary_ShipTo_FY25-26_to_May26.csv"
if path.exists():
    df = pd.read_csv(path, dtype=str, low_memory=False)
    # Find zone and state columns (may vary)
    zone_col  = next((c for c in df.columns if c.strip().lower() == "zone"), None)
    state_col = next((c for c in df.columns if "state" in c.lower()), None)
    if zone_col and state_col:
        df, n = reclassify(df, state_col, zone_col, RULES)
        if n:
            df.to_csv(path, index=False)
        print(f"  → {n} rows reclassified")
        SUMMARY["Primary_ShipTo"] = n
    else:
        print(f"  Columns available: {list(df.columns)}")
        print("  Skipped — could not identify Zone/State columns")
else:
    print("  File not found — skipped")

# ── Validation ───────────────────────────────────────────────────────────────
print("\n" + "="*70)
print("VALIDATION")
print("="*70)

print("\n  CustomerCode_Zone_State_Mapping — remaining North/West for MP/CG:")
path = ROOT / "PowerBI/SeedData/Mapping/CustomerCode_Zone_State_Mapping.csv"
df = pd.read_csv(path, dtype=str)
mp_n = ((df["Zone"].str.strip().str.lower() == "north") & df["State"].apply(is_mp)).sum()
cg_w = ((df["Zone"].str.strip().str.lower() == "west")  & df["State"].apply(is_cg)).sum()
mp_c = ((df["Zone"].str.strip().str.lower() == "central") & df["State"].apply(is_mp)).sum()
cg_c = ((df["Zone"].str.strip().str.lower() == "central") & df["State"].apply(is_cg)).sum()
print(f"  MP: North={mp_n} (should be 0), Central={mp_c}")
print(f"  CG: West={cg_w}  (should be 0), Central={cg_c}")
if mp_n == 0 and cg_w == 0:
    print("  PASS: Zero MP-North and CG-West in CustomerCode mapping")
else:
    print("  FAIL: Residual mismatches remain")

print("\n  Offtake post-remap check:")
for f in sorted((ROOT / "PowerBI/RawDataFolders/Offtake_Monthly").glob("offtake_store_article_*.csv")):
    df = pd.read_csv(f, dtype=str, low_memory=False)
    mp_n = ((df["Zone"].str.strip().str.lower().isin(["north"])) & df["State"].apply(is_mp)).sum()
    cg_w = ((df["Zone"].str.strip().str.lower().isin(["west"]))  & df["State"].apply(is_cg)).sum()
    mp_c = ((df["Zone"].str.strip().str.lower() == "central") & df["State"].apply(is_mp)).sum()
    cg_c = ((df["Zone"].str.strip().str.lower() == "central") & df["State"].apply(is_cg)).sum()
    status = "PASS" if mp_n == 0 and cg_w == 0 else "FAIL"
    print(f"  [{status}] {f.name}: MP Central={mp_c}, CG Central={cg_c}, MP-North={mp_n}, CG-West={cg_w}")

print("\n  Primary post-remap check:")
for f in sorted((ROOT / "PowerBI/RawDataFolders/Primary_Article_Monthly").glob("primary_article_*.csv")):
    df = pd.read_csv(f, dtype=str, low_memory=False)
    if "Zone" not in df.columns or "State" not in df.columns:
        continue
    mp_n = ((df["Zone"].str.strip().str.lower().isin(["north"])) & df["State"].apply(is_mp)).sum()
    cg_w = ((df["Zone"].str.strip().str.lower().isin(["west"]))  & df["State"].apply(is_cg)).sum()
    mp_c = ((df["Zone"].str.strip().str.lower() == "central") & df["State"].apply(is_mp)).sum()
    cg_c = ((df["Zone"].str.strip().str.lower() == "central") & df["State"].apply(is_cg)).sum()
    status = "PASS" if mp_n == 0 and cg_w == 0 else "FAIL"
    print(f"  [{status}] {f.name}: MP Central={mp_c}, CG Central={cg_c}, MP-North={mp_n}, CG-West={cg_w}")

print("\n" + "="*70)
print("REMEDIATION SUMMARY")
print("="*70)
print(f"\n  CustomerCode_Zone_State_Mapping : {SUMMARY.get('CustomerCode_Zone_State_Mapping', 0):>5} rows")
print(f"  ShipToMaster                    : {SUMMARY.get('ShipToMaster', 0):>5} rows")
print(f"  Offtake CSVs (3 files)          : {SUMMARY.get('_TOTAL_OFFTAKE', 0):>5} rows")
print(f"  Primary Article CSVs (16 files) : {SUMMARY.get('_TOTAL_PRIMARY', 0):>5} rows")
print(f"  Primary ShipTo pivot            : {SUMMARY.get('Primary_ShipTo', 0):>5} rows")
grand = sum(v for k, v in SUMMARY.items() if not k.startswith("_"))
print(f"  {'GRAND TOTAL':.<32}: {grand:>5} rows reclassified")
print("\n  Rules applied:")
print("    Madhya Pradesh  : North  → Central")
print("    Chhattisgarh    : West   → Central")
