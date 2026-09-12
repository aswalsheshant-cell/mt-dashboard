"""
Vidarbha → Central Zone Reclassification — Full Pipeline Remediation
=====================================================================
Audits and remediates all MT data layers so Vidarbha (Maharashtra) stores
are correctly tagged Zone=Central instead of Zone=West.

Layers touched:
  1. Vidarbha_Central_Zone_Stores.csv  — canonical 101-store reference (new)
  2. ZoneStateMaster.csv               — add Vidarbha/Central note
  3. CustomerCode_Zone_State_Mapping.csv — reclassify Vidarbha customer codes
  4. offtake_store_article_*.csv       — reclassify via site-code match
  5. Primary_Article_Monthly/*.csv     — reclassify via ship-to name / city match
  6. primary_shipto pivots             — update zone in ShipTo monthly file

Run: python scripts/remediate_vidarbha_central_zone.py
"""

import pandas as pd
import re
import os
import glob
from datetime import date

ROOT      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED_MAP  = os.path.join(ROOT, "PowerBI/SeedData/Mapping")
SEED_MST  = os.path.join(ROOT, "PowerBI/SeedData/Masters")
OFT_DIR   = os.path.join(ROOT, "PowerBI/RawDataFolders/Offtake_Monthly")
PRI_DIR   = os.path.join(ROOT, "PowerBI/RawDataFolders/Primary_Article_Monthly")
SHP_DIR   = os.path.join(ROOT, "PowerBI/RawDataFolders/Primary_ShipTo_Monthly")
NPI_SRC   = "/root/.claude/uploads/f72862e2-ac8f-514a-a251-d4833c7268e5/74ad52cf-MT_Chain_Wise__Article_Wise_NPI_for_TY__Central_mapping_for_maharastra.xlsx"

VIDARBHA_CITIES = [
    "nagpur", "amravati", "akola", "chandrapur", "wardha",
    "yavatmal", "bhandara", "gondia", "gadchiroli", "washim", "hinganghat"
]

def is_vidarbha(text):
    """Return True if text contains any Vidarbha city name."""
    if not isinstance(text, str):
        return False
    t = text.lower()
    return any(city in t for city in VIDARBHA_CITIES)

def norm_site(s):
    """Normalize site code: strip whitespace, remove trailing .0"""
    return str(s).strip().replace(".0", "") if pd.notna(s) else ""

def log(msg):
    print(f"  {msg}")

# =============================================================================
# Step 0 — Load Central Mapping (101 stores from NPI source)
# =============================================================================
print("\n[0] Loading Central Mapping (101 Vidarbha stores)")
cm = pd.read_excel(NPI_SRC, sheet_name=1, header=0)
cm["_site_norm"] = cm["Site Code"].apply(norm_site)
cm["_chain_norm"] = cm["Chain Name"].str.lower().str.strip()

# Build site-code lookup: {norm_site_code → (chain, city)}
site_to_central = {row["_site_norm"]: row for _, row in cm.iterrows() if row["_site_norm"]}

# Per-chain site code sets
CHAIN_SITES = {}
for chain in cm["Chain Name"].unique():
    sites = set(cm[cm["Chain Name"] == chain]["_site_norm"].unique())
    sites.discard("")
    CHAIN_SITES[chain] = sites

log(f"Loaded {len(cm)} stores, {len(site_to_central)} unique site codes")
for chain, sites in CHAIN_SITES.items():
    log(f"  {chain}: {len(sites)} sites")

# =============================================================================
# Step 1 — Canonical Reference File
# =============================================================================
print("\n[1] Writing Vidarbha_Central_Zone_Stores.csv")
ref_path = os.path.join(SEED_MAP, "Vidarbha_Central_Zone_Stores.csv")
ref_df = cm[["s.no", "Site Code", "Site Name", "Chain Name", "City", "State", "Zone"]].copy()
ref_df["Zone_Revised"] = "Central"
ref_df["Sub_Zone"] = "Vidarbha"
ref_df["Remap_Date"] = str(date.today())
ref_df.to_csv(ref_path, index=False)
log(f"Written → {ref_path} ({len(ref_df)} rows)")

# =============================================================================
# Step 2 — ZoneStateMaster.csv
# =============================================================================
print("\n[2] Updating ZoneStateMaster.csv")
zsm_path = os.path.join(SEED_MST, "ZoneStateMaster.csv")
zsm = pd.read_csv(zsm_path)
before = len(zsm)

# Remove any prior Vidarbha rows then re-add clean
zsm = zsm[~((zsm["State"] == "Maharashtra-Vidarbha") | (zsm["State"] == "Vidarbha"))]

# Maharashtra under West stays; add explicit Vidarbha row under Central
new_rows = [
    {"Zone": "Central", "Zone Sort Order": 6, "State": "Maharashtra-Vidarbha",
     "Region": "Vidarbha (Nagpur, Akola, Amravati, Wardha, Yavatmal, Chandrapur, Bhandara, Gadchiroli)"},
]
zsm = pd.concat([zsm, pd.DataFrame(new_rows)], ignore_index=True)
zsm.to_csv(zsm_path, index=False)
log(f"ZoneStateMaster: {before} → {len(zsm)} rows (+Vidarbha Central entry)")

# =============================================================================
# Step 3 — CustomerCode_Zone_State_Mapping.csv
# =============================================================================
print("\n[3] Updating CustomerCode_Zone_State_Mapping.csv")
czm_path = os.path.join(SEED_MAP, "CustomerCode_Zone_State_Mapping.csv")
czm = pd.read_csv(czm_path)
before_west = (czm["Zone"] == "West").sum()

# Identify Vidarbha rows: Maharashtra + any Vidarbha city in name OR City/Location
def is_vidarbha_czm(row):
    if str(row.get("State", "")).lower() not in ("maharashtra", "mumbai"):
        return False
    text = " ".join([
        str(row.get("Customer Name / Ship-to Name", "")),
        str(row.get("City / Location", "")),
        str(row.get("Business Region / Sub-region", ""))
    ])
    return is_vidarbha(text)

vidarbha_mask = czm.apply(is_vidarbha_czm, axis=1)
n_changed = vidarbha_mask.sum()

# Also match by chain: Wellness, DMart, Apollo in Nagpur/Vidarbha Customer Codes
# Cross-reference: customer codes 1101075, 1101076, 1101077 are DMart Nagpur
# Apply zone change
czm.loc[vidarbha_mask, "Zone"] = "Central"
czm.loc[vidarbha_mask, "Business Region / Sub-region"] = (
    czm.loc[vidarbha_mask, "Business Region / Sub-region"]
    .fillna("").apply(lambda x: x if "Vidarbha" in str(x) else f"{x} [Vidarbha]".strip())
)
czm.loc[vidarbha_mask, "Remarks"] = "Zone reclassified: WEST → CENTRAL (Vidarbha) per Central_Mapping Aug-26"

czm.to_csv(czm_path, index=False)
after_west  = (czm["Zone"] == "West").sum()
after_cent  = (czm["Zone"] == "Central").sum()
log(f"Reclassified {n_changed} customer codes: West {before_west} → {after_west}, Central entries now {after_cent}")

# Report what changed
changed = czm[vidarbha_mask][["Customer Code","Customer Name / Ship-to Name","State","Zone","Chain Name"]]
log(f"Changed entries ({len(changed)}):")
for _, r in changed.iterrows():
    log(f"  {r['Customer Code']} | {r['Customer Name / Ship-to Name'][:50]} | {r['Chain Name']}")

# =============================================================================
# Step 4 — Offtake Store-Article CSVs
# =============================================================================
print("\n[4] Remapping Offtake CSVs (site-code based)")

oft_files = sorted(glob.glob(os.path.join(OFT_DIR, "offtake_store_article_*.csv")))
oft_summary = []

for path in oft_files:
    fname = os.path.basename(path)
    df = pd.read_csv(path, low_memory=False)
    original_rows = len(df)

    # Normalize site codes
    df["_site_norm"] = df["Site Code"].apply(norm_site)

    # Match against central mapping (site-code exact match, post-normalization)
    sc_match  = df["_site_norm"].isin(site_to_central)

    # For Reliance (no site codes in offtake): fallback to city-name match
    rel_mask = (
        df["Chain Name"].str.lower().str.strip().str.contains("reliance", na=False) &
        ~df["Chain Name"].str.lower().str.strip().str.contains("brand counter", na=False) &
        df["State"].str.lower().str.strip().str.contains("maharashtra|mumbai", na=False) &
        df["City"].apply(is_vidarbha)
    )

    # Combined
    remap_mask = sc_match | rel_mask

    n_site   = int(sc_match.sum())
    n_rel    = int(rel_mask.sum())
    n_total  = int(remap_mask.sum())

    if n_total > 0:
        # Record before state
        before_zones = df[remap_mask]["Zone"].value_counts().to_dict()
        df.loc[remap_mask, "Zone"] = "Central"
        # Update City column to add Vidarbha tag where city is blank/generic
        df.drop(columns=["_site_norm"], inplace=True)
        df.to_csv(path, index=False)

        oft_summary.append({
            "file": fname,
            "total_rows": original_rows,
            "reclassified": n_total,
            "by_site_code": n_site,
            "by_city_reliance": n_rel,
            "before_zones": before_zones,
        })
        log(f"{fname}: {n_total} rows reclassified (site_code={n_site}, reliance_city={n_rel})")
        log(f"  before_zones: {before_zones}")
    else:
        df.drop(columns=["_site_norm"], inplace=True)
        log(f"{fname}: 0 rows changed (no Vidarbha site code matches in this month)")

# =============================================================================
# Step 5 — Primary Article Monthly CSVs
# =============================================================================
print("\n[5] Remapping Primary Article CSVs (ship-to name + state + city match)")

# Build Vidarbha ship-to identifiers:
# In primary data, Vidarbha stores appear in Ship To Name and State
# Strategy: State = Maharashtra + ship-to name contains Vidarbha city
pri_files = sorted(glob.glob(os.path.join(PRI_DIR, "primary_article_*.csv")))
pri_summary = []

for path in pri_files:
    fname = os.path.basename(path)
    df = pd.read_csv(path, low_memory=False)
    original_rows = len(df)

    # Match: State includes Maharashtra + ship-to name or store_code contains Vidarbha city
    maha_mask = df["State"].str.lower().str.strip().str.contains("maharashtra|mumbai|nagpur", na=False)

    # Ship-to name based
    shipto_vidarbha = df["Ship To Name"].apply(is_vidarbha)
    # Store code based (some primary rows have numeric store codes matching DMart 44xx or Apollo 12xxx)
    def store_is_vidarbha(row):
        try:
            sc = str(row.get("Store Code", "")).strip().replace(".0","")
            if sc in site_to_central:
                return True
        except Exception:
            pass
        return False
    store_vidarbha = df.apply(store_is_vidarbha, axis=1)

    remap_mask = maha_mask & (shipto_vidarbha | store_vidarbha)
    n_total = int(remap_mask.sum())

    if n_total > 0:
        before_zones = df[remap_mask]["Zone"].value_counts().to_dict()
        df.loc[remap_mask, "Zone"] = "Central"
        df.to_csv(path, index=False)
        pri_summary.append({
            "file": fname,
            "total_rows": original_rows,
            "reclassified": n_total,
            "by_shipto": int(shipto_vidarbha[maha_mask].sum()),
            "by_store": int(store_vidarbha[maha_mask].sum()),
            "before_zones": before_zones,
        })
        log(f"{fname}: {n_total} rows reclassified (ship-to={int(shipto_vidarbha[maha_mask].sum())}, store_code={int(store_vidarbha[maha_mask].sum())})")
    else:
        log(f"{fname}: 0 rows changed")

# =============================================================================
# Step 6 — Primary ShipTo Monthly pivot
# =============================================================================
print("\n[6] Remapping Primary_ShipTo_FY25-26_to_May26.csv")
shp_path = os.path.join(SHP_DIR, "Primary_ShipTo_FY25-26_to_May26.csv")
shp = pd.read_csv(shp_path)
before_shp = (shp["Zone"] == "West").sum()

shp_vidarbha = shp["Ship To Name"].apply(is_vidarbha) & \
               shp["State"].str.lower().str.contains("maharashtra|mumbai", na=False)
n_shp = int(shp_vidarbha.sum())
if n_shp:
    shp.loc[shp_vidarbha, "Zone"] = "Central"
    shp.to_csv(shp_path, index=False)
after_shp = (shp["Zone"] == "West").sum()
log(f"ShipTo file: {n_shp} rows reclassified, West {before_shp} → {after_shp}")

# =============================================================================
# Step 7 — Validation
# =============================================================================
print("\n[7] VALIDATION")

print("\n  7a. ZoneStateMaster:")
zsm2 = pd.read_csv(zsm_path)
print(zsm2[zsm2["Zone"]=="Central"].to_string(index=False))

print("\n  7b. CustomerCode_Zone_State_Mapping — Central count:")
czm2 = pd.read_csv(czm_path)
print(f"  Central entries: {(czm2['Zone']=='Central').sum()}")
print(f"  West (Maharashtra) remaining: {((czm2['Zone']=='West') & (czm2['State'].str.contains('Maharashtra',na=False))).sum()}")

print("\n  7c. Offtake — Zone distribution post-remap:")
for path in sorted(glob.glob(os.path.join(OFT_DIR, "offtake_store_article_*.csv"))):
    df = pd.read_csv(path, low_memory=False)
    maha = df[df["State"].str.contains("Maharashtra|Mumbai", case=False, na=False)]
    print(f"  {os.path.basename(path)}: Maharashtra rows={len(maha)}, zones={maha['Zone'].value_counts().to_dict()}")

print("\n  7d. Confirm zero Vidarbha records under West in offtake:")
vidarbha_still_west = 0
for path in sorted(glob.glob(os.path.join(OFT_DIR, "offtake_store_article_*.csv"))):
    df = pd.read_csv(path, low_memory=False)
    maha = df[df["State"].str.contains("Maharashtra|Mumbai", case=False, na=False)]
    df["_site_norm"] = df["Site Code"].apply(norm_site)
    still_west = df[df["_site_norm"].isin(site_to_central) & (df["Zone"].str.lower() == "west")]
    vidarbha_still_west += len(still_west)
    if len(still_west):
        print(f"  WARNING: {os.path.basename(path)} has {len(still_west)} Vidarbha site codes still tagged West!")
if vidarbha_still_west == 0:
    print("  PASS: Zero Vidarbha site codes remain tagged West in offtake data")

print("\n  7e. Primary — Central records introduced:")
pri_central_total = 0
for path in sorted(glob.glob(os.path.join(PRI_DIR, "primary_article_*.csv"))):
    df = pd.read_csv(path, low_memory=False)
    n = (df["Zone"] == "Central").sum()
    pri_central_total += n
    if n > 0:
        print(f"  {os.path.basename(path)}: Central={n}")
print(f"  Total Central records across all primary files: {pri_central_total}")

# =============================================================================
# Summary Report
# =============================================================================
print("\n" + "="*70)
print("REMEDIATION COMPLETE — SUMMARY")
print("="*70)
print(f"\nDate: {date.today()}")
print("\nFiles modified:")
print(f"  [MASTER]   {zsm_path}")
print(f"  [MAPPING]  {czm_path}")
print(f"  [NEW REF]  {ref_path}")
print(f"  [OFFTAKE]  {len(oft_files)} monthly CSVs")
print(f"  [PRIMARY]  {len(pri_files)} monthly CSVs")
print(f"  [SHIPTO]   {shp_path}")

print("\nOfftake reclassification:")
total_oft = sum(s["reclassified"] for s in oft_summary)
for s in oft_summary:
    print(f"  {s['file']}: {s['reclassified']} rows (site_code={s['by_site_code']}, reliance_city={s['by_city_reliance']})")
print(f"  TOTAL: {total_oft} rows across {len(oft_summary)} offtake files")

print("\nPrimary reclassification:")
total_pri = sum(s["reclassified"] for s in pri_summary)
for s in pri_summary:
    print(f"  {s['file']}: {s['reclassified']} rows")
print(f"  TOTAL: {total_pri} rows across {len(pri_summary)} primary files")

print(f"\nCustomerCode_Zone_State_Mapping: {n_changed} customer codes → Central")
print("\nLimitations:")
print("  - Reliance offtake rows (no Site Code in offtake data): matched by city name only")
print("  - Some Maharashtra Metro-CNC entries serve both Central and West — tagged Central")
print("    if store name contains Vidarbha city; split/blended routes left unchanged.")
print("  - Pre-aggregated workbooks (.xlsx/.xlsb not in repo) require manual re-export")
print("    after re-running build_dashboard_data.py with the updated raw CSVs.")
