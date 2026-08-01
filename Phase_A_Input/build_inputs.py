#!/usr/bin/env python3
"""
Build Phase_A_Input/ folder from real source data.

Sources:
  - PowerBI/RawDataFolders/Primary_Article_Monthly/*.csv  (14 months)
  - PowerBI/RawDataFolders/Offtake_Monthly/*.csv          (2 months)

Outputs all 7 CSV files the data_readiness_audit.py expects.
fact_margin is derived from offtake NSV/MRP ratio and flagged DERIVED.
"""
import pandas as pd
import numpy as np
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent.parent
OUT  = Path(__file__).resolve().parent

EXCLUDED_BRANDS = {"Pure Origin", "Lumineve", "Staze"}

PLANT_TO_WAREHOUSE = {
    "1001.0": "Gurgaon",
    "1003.0": "Bangalore",
    "1004.0": "Gurgaon",
    "1313.0": "Gurgaon",
    "1315.0": "Mumbai",
    "1317.0": "Kolkata",
}

MONTH_ABBR = {
    "Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04",
    "May": "05", "Jun": "06", "Jul": "07", "Aug": "08",
    "Sep": "09", "Oct": "10", "Nov": "11", "Dec": "12",
}

GST_BY_CATEGORY = {
    "Baby": "5.0",
    "Wellness": "12.0",
}
GST_DEFAULT = "18.0"


def parse_primary_month(val: str) -> str:
    """Convert 'Apr'25' → '2025-04'."""
    m = re.match(r"([A-Za-z]{3})['’](\d{2})", str(val).strip())
    if not m:
        return ""
    mm = MONTH_ABBR.get(m.group(1).capitalize(), "")
    yy = m.group(2)
    year = f"20{yy}"
    return f"{year}-{mm}" if mm else ""


def clean_ean(val) -> str:
    """Remove .0 suffix and leading/trailing whitespace."""
    s = str(val).strip()
    if s.endswith(".0"):
        s = s[:-2]
    return s


def parse_excel_serial(val) -> str:
    """Convert Excel date serial (e.g. 46113.0) → 'YYYY-MM'."""
    try:
        days = float(val)
        ts = pd.Timestamp("1899-12-30") + pd.to_timedelta(days, unit="D")
        return ts.strftime("%Y-%m")
    except Exception:
        return ""


# ────────────────────────────────────────────────────────────────
# 1. PRIMARY HISTORY
# ────────────────────────────────────────────────────────────────
def build_primary_history():
    src_dir = ROOT / "PowerBI" / "RawDataFolders" / "Primary_Article_Monthly"
    files = sorted(src_dir.glob("primary_article_*.csv"))
    print(f"\n[1/7] Building primary_history.csv from {len(files)} files...")

    frames = []
    for f in files:
        df = pd.read_csv(f, dtype=str)
        frames.append(df)

    raw = pd.concat(frames, ignore_index=True)
    print(f"  Raw rows: {len(raw):,}")

    # Map columns
    out = pd.DataFrame()
    out["month"]       = raw["Month"].apply(parse_primary_month)
    out["chain_name"]  = raw["Chain name"].str.strip()
    out["zone"]        = raw["Zone"].str.strip()
    out["state"]       = raw["State"].str.strip()
    out["brand"]       = raw["brand"].str.strip()
    out["category"]    = raw["category"].str.strip()
    out["article"]     = raw["Description"].str.strip()
    out["ean"]         = raw["EAN No."].apply(clean_ean)
    out["primary_qty"] = pd.to_numeric(raw["Inv Qty"], errors="coerce")
    out["primary_nsv"] = pd.to_numeric(raw["Inv. Net value(LOC)"], errors="coerce")
    out["distributor"] = raw["Ship To Name"].str.strip()
    out["warehouse"]   = raw["Plant"].map(PLANT_TO_WAREHOUSE).fillna("Unknown")

    # Drop rows with invalid months or missing keys
    out = out[out["month"].str.match(r"\d{4}-\d{2}")]
    out = out[out["ean"].str.match(r"\d{8,14}")]
    out = out.dropna(subset=["primary_qty", "primary_nsv"])

    # Exclude brands
    out = out[~out["brand"].isin(EXCLUDED_BRANDS)]

    # Aggregate to (month, chain_name, ean) grain — zone/state come from chain_master,
    # warehouse allocation from warehouse_mapping; collapse all sub-rows here.
    agg = (
        out.groupby(["month", "chain_name", "brand", "category", "article", "ean"])
        .agg(primary_qty=("primary_qty", "sum"),
             primary_nsv=("primary_nsv", "sum"))
        .reset_index()
    )
    # Restore warehouse and distributor as most common for reference
    ref = (
        out.groupby(["month", "chain_name", "ean"])
        .agg(
            warehouse=("warehouse", lambda x: x.mode()[0] if len(x) else ""),
            distributor=("distributor", lambda x: x.mode()[0] if len(x) else ""),
        )
        .reset_index()
    )
    agg = agg.merge(ref, on=["month", "chain_name", "ean"], how="left")

    # Re-attach zone/state from raw (most frequent per chain) so downstream can use them
    chain_geo = (
        out.groupby("chain_name")
        .agg(zone=("zone", lambda x: x.mode()[0] if len(x) else ""),
             state=("state", lambda x: x.mode()[0] if len(x) else ""))
        .reset_index()
    )
    agg = agg.merge(chain_geo, on="chain_name", how="left")

    path = OUT / "primary_history.csv"
    agg.to_csv(path, index=False)
    print(f"  ✓ Written {len(agg):,} rows → {path.name}")
    print(f"    Months: {sorted(agg['month'].unique())}")
    print(f"    Chains: {agg['chain_name'].nunique()} | EANs: {agg['ean'].nunique()} | Brands: {agg['brand'].unique().tolist()}")
    return agg


# ────────────────────────────────────────────────────────────────
# 2. OFFTAKE HISTORY
# ────────────────────────────────────────────────────────────────
def build_offtake_history():
    src_dir = ROOT / "PowerBI" / "RawDataFolders" / "Offtake_Monthly"
    files = sorted(src_dir.glob("offtake_store_article_*.csv"))
    print(f"\n[2/7] Building offtake_history.csv from {len(files)} files...")

    frames = []
    for f in files:
        df = pd.read_csv(f, dtype=str, low_memory=False)
        frames.append(df)

    raw = pd.concat(frames, ignore_index=True)
    print(f"  Raw rows: {len(raw):,}")

    out = pd.DataFrame()
    out["month"]      = raw["Revised Month"].apply(parse_excel_serial)
    out["chain_name"] = raw["Chain Name"].str.strip()
    out["zone"]       = raw["Zone"].str.strip()
    out["state"]      = raw["State"].str.strip()
    out["brand"]      = raw["Brand"].str.strip()
    out["category"]   = raw["Category"].str.strip()
    out["article"]    = raw["Description as per Fountain"].str.strip()
    out["ean"]        = raw["EAN"].apply(clean_ean)
    out["offtake_qty"]= pd.to_numeric(raw["Sales Qty"], errors="coerce")
    # NSV is in lacs per piece; convert to total rupees
    nsv_per_pc = pd.to_numeric(raw["NSV"], errors="coerce")
    qty         = pd.to_numeric(raw["Sales Qty"], errors="coerce")
    out["offtake_nsv"] = (nsv_per_pc * qty * 100_000).round(2)
    # store_count: count unique site codes per chain×EAN×month
    out["site_code"]  = raw["Site Code"].str.strip()

    # Filter
    out = out[out["month"].str.match(r"\d{4}-\d{2}")]
    out = out[out["ean"].str.match(r"\d{8,14}")]
    out = out.dropna(subset=["offtake_qty"])
    out = out[~out["brand"].isin(EXCLUDED_BRANDS)]

    # store_count before aggregation
    store_counts = (
        out.groupby(["month", "chain_name", "ean"])["site_code"]
        .nunique()
        .reset_index()
        .rename(columns={"site_code": "store_count"})
    )

    # Aggregate to (month, chain_name, ean) grain — zone/state from chain_master
    agg = (
        out.groupby(["month", "chain_name", "brand", "category", "article", "ean"])
        .agg(offtake_qty=("offtake_qty", "sum"),
             offtake_nsv=("offtake_nsv", "sum"))
        .reset_index()
    )
    agg = agg.merge(store_counts, on=["month", "chain_name", "ean"], how="left")

    # Re-attach zone/state from raw (most frequent per chain)
    chain_geo = (
        out.groupby("chain_name")
        .agg(zone=("zone", lambda x: x.mode()[0] if len(x) else ""),
             state=("state", lambda x: x.mode()[0] if len(x) else ""))
        .reset_index()
    )
    agg = agg.merge(chain_geo, on="chain_name", how="left")

    path = OUT / "offtake_history.csv"
    agg.to_csv(path, index=False)
    print(f"  ✓ Written {len(agg):,} rows → {path.name}")
    print(f"    Months: {sorted(agg['month'].unique())}")
    print(f"    Chains: {agg['chain_name'].nunique()} | EANs: {agg['ean'].nunique()}")
    return agg


# ────────────────────────────────────────────────────────────────
# 3. FACT MARGIN  (derived from offtake NSV/MRP; flagged DERIVED)
# ────────────────────────────────────────────────────────────────
def build_fact_margin(offtake_df: pd.DataFrame):
    print(f"\n[3/7] Building fact_margin.csv (DERIVED from offtake NSV/MRP)...")

    src_dir = ROOT / "PowerBI" / "RawDataFolders" / "Offtake_Monthly"
    files = sorted(src_dir.glob("offtake_store_article_*.csv"))
    frames = [pd.read_csv(f, dtype=str, low_memory=False) for f in files]
    raw = pd.concat(frames, ignore_index=True)

    raw["ean"]       = raw["EAN"].apply(clean_ean)
    raw["chain_name"]= raw["Chain Name"].str.strip()
    raw["brand"]     = raw["Brand"].str.strip()
    raw["category"]  = raw["Category"].str.strip()
    raw["article"]   = raw["Description as per Fountain"].str.strip()
    raw["mrp"]       = pd.to_numeric(raw["M-Value"], errors="coerce")
    raw["nsv_pc"]    = pd.to_numeric(raw["NSV"], errors="coerce") * 100_000  # rupees per unit
    raw["month"]     = raw["Revised Month"].apply(parse_excel_serial)

    raw = raw[raw["ean"].str.match(r"\d{8,14}")]
    raw = raw[~raw["brand"].isin(EXCLUDED_BRANDS)]
    raw = raw.dropna(subset=["mrp", "nsv_pc"])
    raw = raw[raw["mrp"] > 0]

    # Effective trade margin % = (MRP - NSV_per_unit) / MRP * 100
    raw["margin_pct"] = ((raw["mrp"] - raw["nsv_pc"]) / raw["mrp"] * 100).round(2)

    # Median margin per chain×EAN (stable across months)
    margin = (
        raw.groupby(["chain_name", "brand", "article", "ean"])
        .agg(
            mrp=("mrp", "median"),
            margin_pct=("margin_pct", "median"),
        )
        .reset_index()
    )
    margin["mrp"] = margin["mrp"].round(2)

    # Add GST and TOT (total of trade) — industry standards
    margin["gst_pct"] = margin["category"].map(GST_BY_CATEGORY).fillna(GST_DEFAULT) if "category" in margin.columns else GST_DEFAULT
    margin["tot_pct"] = margin["margin_pct"]       # total trade = effective margin here
    margin["cm2_pct"] = (margin["mrp"] * 0.12).round(2)  # placeholder: ~12% CM2 typical FMCG

    # Re-add category
    cat_map = raw.groupby("ean")["category"].agg(lambda x: x.mode()[0] if len(x) else "").reset_index()
    margin = margin.merge(cat_map, on="ean", how="left")
    margin["gst_pct"] = margin["category"].map(GST_BY_CATEGORY).fillna(GST_DEFAULT)

    margin["quality_status"] = "DERIVED"
    margin["month"] = "2026-04"  # representative month (most recent offtake)

    # Select final columns (include category for downstream filtering)
    margin = margin[[
        "month", "chain_name", "brand", "category", "article", "ean",
        "mrp", "margin_pct", "tot_pct", "gst_pct", "cm2_pct", "quality_status"
    ]]

    # --- Extend to all primary EANs not yet in margin ---
    # Load article_master to get brand/category for missing EANs
    article_master_path = OUT / "article_master.csv"
    if article_master_path.exists():
        am = pd.read_csv(article_master_path)
    else:
        primary_path = ROOT / "PowerBI" / "RawDataFolders" / "Primary_Article_Monthly"
        pfiles = sorted(primary_path.glob("primary_article_*.csv"))
        pframes = [pd.read_csv(f, dtype=str) for f in pfiles]
        praw = pd.concat(pframes, ignore_index=True)
        am = praw[["EAN No.", "Description", "brand", "category"]].copy()
        am.columns = ["ean", "article", "brand", "category"]
        am["ean"] = am["ean"].apply(clean_ean)
        am = am[am["ean"].str.match(r"\d{8,14}")]
        am = am[~am["brand"].isin(EXCLUDED_BRANDS)]
        am = am.drop_duplicates("ean")

    known_eans = set(margin["ean"].unique())
    missing = am[~am["ean"].isin(known_eans)].copy()

    if len(missing) > 0:
        # Industry-standard placeholder margins for EANs not in offtake
        missing["gst_pct"] = missing["category"].map(GST_BY_CATEGORY).fillna(GST_DEFAULT)
        missing["mrp"] = 250.0          # median FMCG MRP placeholder
        missing["margin_pct"] = 30.0    # typical effective trade margin
        missing["tot_pct"] = 30.0
        missing["cm2_pct"] = 15.0       # conservative CM2 estimate
        missing["quality_status"] = "ESTIMATED"
        missing["month"] = "2026-04"
        missing["chain_name"] = "ALL"   # chain-agnostic placeholder
        missing = missing[[
            "month", "chain_name", "brand", "article", "ean",
            "mrp", "margin_pct", "tot_pct", "gst_pct", "cm2_pct", "quality_status"
        ]]
        margin = pd.concat([margin, missing], ignore_index=True)

    path = OUT / "fact_margin.csv"
    margin.to_csv(path, index=False)
    print(f"  ⚠ Written {len(margin):,} rows → {path.name}")
    print(f"    WARNING: margin_pct/cm2_pct are DERIVED approximations.")
    print(f"    ACTION:  Replace with real Margin Repository export before final validation.")
    return margin


# ────────────────────────────────────────────────────────────────
# 4. ARTICLE MASTER
# ────────────────────────────────────────────────────────────────
def build_article_master(primary_df: pd.DataFrame):
    print(f"\n[4/7] Building article_master.csv...")
    master = (
        primary_df.groupby("ean")
        .agg(article=("article", lambda x: x.mode()[0]),
             brand=("brand",   lambda x: x.mode()[0]),
             category=("category", lambda x: x.mode()[0]))
        .reset_index()
    )
    path = OUT / "article_master.csv"
    master.to_csv(path, index=False)
    print(f"  ✓ Written {len(master):,} EANs → {path.name}")
    return master


# ────────────────────────────────────────────────────────────────
# 5. CHAIN MASTER
# ────────────────────────────────────────────────────────────────
def build_chain_master(primary_df: pd.DataFrame):
    print(f"\n[5/7] Building chain_master.csv...")
    # Re-read raw to get zone/state (not in aggregated primary_df)
    src_dir = ROOT / "PowerBI" / "RawDataFolders" / "Primary_Article_Monthly"
    files = sorted(src_dir.glob("primary_article_*.csv"))
    frames = [pd.read_csv(f, dtype=str) for f in files]
    raw = pd.concat(frames, ignore_index=True)
    raw["chain_name"] = raw["Chain name"].str.strip()
    raw["zone"] = raw["Zone"].str.strip()
    raw["state"] = raw["State"].str.strip()
    raw = raw[~raw["brand"].isin(EXCLUDED_BRANDS)]
    raw = raw[raw["chain_name"].isin(primary_df["chain_name"].unique())]

    master = (
        raw.groupby("chain_name")
        .agg(zone=("zone", lambda x: x.mode()[0] if len(x) else ""),
             state=("state", lambda x: x.mode()[0] if len(x) else ""))
        .reset_index()
    )
    path = OUT / "chain_master.csv"
    master.to_csv(path, index=False)
    print(f"  ✓ Written {len(master):,} chains → {path.name}")
    return master


# ────────────────────────────────────────────────────────────────
# 6. WAREHOUSE MAPPING
# ────────────────────────────────────────────────────────────────
def build_warehouse_mapping(primary_df: pd.DataFrame):
    print(f"\n[6/7] Building warehouse_mapping.csv...")

    # Recompute from raw primary source to get warehouse breakdown
    src_dir = ROOT / "PowerBI" / "RawDataFolders" / "Primary_Article_Monthly"
    files = sorted(src_dir.glob("primary_article_*.csv"))
    frames = [pd.read_csv(f, dtype=str) for f in files]
    raw = pd.concat(frames, ignore_index=True)
    raw["chain_name"] = raw["Chain name"].str.strip()
    raw["warehouse"] = raw["Plant"].map(PLANT_TO_WAREHOUSE).fillna("Unknown")
    raw["primary_qty"] = pd.to_numeric(raw["Inv Qty"], errors="coerce").fillna(0)
    raw = raw[~raw["brand"].isin(EXCLUDED_BRANDS)]
    raw = raw[raw["warehouse"] != "Unknown"]

    totals = (
        raw.groupby(["chain_name", "warehouse"])["primary_qty"]
        .sum()
        .reset_index()
    )
    chain_totals = raw.groupby("chain_name")["primary_qty"].sum().reset_index()
    chain_totals.columns = ["chain_name", "total_qty"]

    mapping = totals.merge(chain_totals, on="chain_name")
    mapping["allocation_pct"] = (mapping["primary_qty"] / mapping["total_qty"] * 100).round(2)

    # Add zone/state from chain_master
    chain_master_path = OUT / "chain_master.csv"
    if chain_master_path.exists():
        cm = pd.read_csv(chain_master_path)
        mapping = mapping.merge(cm, on="chain_name", how="left")

    mapping = mapping[mapping["allocation_pct"] > 0]
    keep_cols = ["chain_name", "warehouse", "allocation_pct"]
    if "zone" in mapping.columns:
        keep_cols = ["chain_name", "zone", "state", "warehouse", "allocation_pct"]
    mapping = mapping[keep_cols].drop(columns=["primary_qty", "total_qty"], errors="ignore")

    path = OUT / "warehouse_mapping.csv"
    mapping.to_csv(path, index=False)
    print(f"  ✓ Written {len(mapping):,} chain-warehouse rows → {path.name}")
    return mapping


# ────────────────────────────────────────────────────────────────
# 7. TARGETS (placeholder — real targets come from business)
# ────────────────────────────────────────────────────────────────
def build_targets_placeholder():
    print(f"\n[7/7] Building targets.csv (empty template — populate from business targets)...")
    df = pd.DataFrame(columns=["month", "chain_name", "brand", "target_qty", "target_nsv"])
    path = OUT / "targets.csv"
    df.to_csv(path, index=False)
    print(f"  ⚠ targets.csv is empty — business must provide actual targets")
    return df


# ────────────────────────────────────────────────────────────────
# MAIN
# ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 70)
    print("PHASE A INPUT BUILDER")
    print(f"Output dir: {OUT}")
    print("=" * 70)

    primary_df  = build_primary_history()
    offtake_df  = build_offtake_history()
    margin_df   = build_fact_margin(offtake_df)
    article_df  = build_article_master(primary_df)
    chain_df    = build_chain_master(primary_df)
    wh_df       = build_warehouse_mapping(primary_df)
    build_targets_placeholder()

    print("\n" + "=" * 70)
    print("BUILD COMPLETE")
    print("=" * 70)
    print(f"  primary_history.csv  : {len(primary_df):>7,} rows")
    print(f"  offtake_history.csv  : {len(offtake_df):>7,} rows")
    print(f"  fact_margin.csv      : {len(margin_df):>7,} rows  ⚠ DERIVED")
    print(f"  article_master.csv   : {len(article_df):>7,} EANs")
    print(f"  chain_master.csv     : {len(chain_df):>7,} chains")
    print(f"  warehouse_mapping.csv: {len(wh_df):>7,} rows")
    print()
    print("NEXT STEP:")
    print("  python forecast_engine/data_readiness_audit.py Phase_A_Input audit_output")
    print("=" * 70)
