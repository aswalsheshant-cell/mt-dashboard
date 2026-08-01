# -*- coding: utf-8 -*-
"""Fountain-master enrichment for DMS-ingested margin records.

The Fountain article master arrives embedded in the monthly offtake feed
(PowerBI/RawDataFolders/Offtake_Monthly/offtake_store_article_*.csv) and
provides Pack Size, canonical Brand/Category/Sub-category/Range/PPT
Category, and Article Code keyed by EAN.

This module fills the master-data gaps in DMS-ingested records:
  - Pack Size          (from Fountain Net Weight)
  - Article Code       (SKU Code / Fountain Article)
  - Brand / Category / Sub Category / Range  (canonical spelling)
  - PPT Category       (marketing rollup)

Pack Size fallback: for EANs not in Fountain, try to parse a numeric
pack size from the DMS Product Name (150ml, 50g, "pack of 2*75gm", etc.).

GST %: NOT populated here. Fountain has an empty With-Tax column, so
GST enrichment still requires a separate master (SAP tax classification).
"""
import os
import re
import glob
import pandas as pd


FOUNTAIN_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "PowerBI", "RawDataFolders", "Offtake_Monthly",
)

FOUNTAIN_COLS = [
    "EAN", "Article", "Chain Article Description", "Net Weight",
    "Description as per Fountain", "Brand", "Category", "Sub_category",
    "Range", "MRP", "PPT Category",
]

PACK_SIZE_PATTERNS = [
    (re.compile(r"pack\s*of\s*(\d+)\s*[x*]\s*(\d+)\s*(ml|gm|g)\b", re.I),
     lambda m: f"{int(m.group(1)) * int(m.group(2))} {m.group(3).lower().replace('gm','g')}"),
    (re.compile(r"(\d+)\s*[x*]\s*(\d+)\s*(ml|gm|g)\b", re.I),
     lambda m: f"{int(m.group(1)) * int(m.group(2))} {m.group(3).lower().replace('gm','g')}"),
    (re.compile(r"(\d+(?:\.\d+)?)\s*(ml|mL|ML|gm|g|GM|G|kg|KG|L|l)\b"),
     lambda m: f"{m.group(1)} {m.group(2).lower().replace('gm','g').replace('kg','kg')}"),
    (re.compile(r"(\d+)\s*(sheet|patches|patch|piece|pcs)\b", re.I),
     lambda m: f"{m.group(1)} {m.group(2).lower()}"),
]


def _clean_ean(v):
    if pd.isna(v):
        return ""
    s = str(v).strip()
    if s.endswith(".0"):
        s = s[:-2]
    return s


def load_fountain_master(fountain_dir=FOUNTAIN_DIR, pattern="offtake_store_article_*.csv"):
    """Load the latest Fountain-sourced article master from the offtake feed."""
    files = sorted(glob.glob(os.path.join(fountain_dir, pattern)))
    if not files:
        raise FileNotFoundError(
            f"No Fountain offtake files found in {fountain_dir}"
        )
    latest = files[-1]
    df = pd.read_csv(latest, usecols=FOUNTAIN_COLS, dtype=str, low_memory=False)
    df = df.dropna(subset=["EAN"])
    df["EAN"] = df["EAN"].map(_clean_ean)
    df = df[df["EAN"] != ""]
    master = df.drop_duplicates(subset=["EAN"]).reset_index(drop=True)
    meta = {
        "source_file": os.path.basename(latest),
        "unique_eans": len(master),
        "columns": FOUNTAIN_COLS,
    }
    return master, meta


def parse_pack_size_from_name(name):
    """Best-effort pack-size parse from a product name.
    Returns a canonical string like '150 ml', '50 g', '2 sheet', or '' if not found.
    """
    if not name or pd.isna(name):
        return ""
    s = str(name)
    for pat, fmt in PACK_SIZE_PATTERNS:
        m = pat.search(s)
        if m:
            return fmt(m)
    return ""


def enrich(dms_df, fountain_master=None):
    """Enrich a DMS-normalized dataframe with Fountain master fields.

    Returns (enriched_df, enrichment_report_dict).
    """
    if fountain_master is None:
        fountain_master, _ = load_fountain_master()

    df = dms_df.copy()
    df["_ean"] = df["EAN"].map(_clean_ean)

    fm = fountain_master.rename(columns={
        "EAN": "_ean",
        "Net Weight": "_fm_pack_size",
        "Article": "_fm_article_code",
        "Brand": "_fm_brand",
        "Category": "_fm_category",
        "Sub_category": "_fm_sub_category",
        "Range": "_fm_range",
        "PPT Category": "_fm_ppt_category",
        "Description as per Fountain": "_fm_description",
    })[["_ean", "_fm_pack_size", "_fm_article_code", "_fm_brand",
        "_fm_category", "_fm_sub_category", "_fm_range",
        "_fm_ppt_category", "_fm_description"]]

    merged = df.merge(fm, on="_ean", how="left")
    matched = merged["_fm_article_code"].notna()

    def fill(col_target, col_source, is_blank_fn=None):
        if is_blank_fn is None:
            is_blank_fn = lambda v: (v is None) or (str(v).strip() == "") or (pd.isna(v))
        blank_mask = merged[col_target].map(is_blank_fn)
        fill_mask = blank_mask & merged[col_source].notna()
        merged.loc[fill_mask, col_target] = merged.loc[fill_mask, col_source]
        return int(fill_mask.sum())

    filled_pack = fill("Pack Size", "_fm_pack_size")
    filled_sku = fill("SKU Code", "_fm_article_code")
    filled_brand = fill("Brand", "_fm_brand")
    filled_cat = fill("Category", "_fm_category")
    filled_sub = fill("Sub Category", "_fm_sub_category")
    filled_range = fill("Range", "_fm_range")

    if "PPT Category" not in merged.columns:
        merged["PPT Category"] = ""
    ppt_mask = merged["_fm_ppt_category"].notna()
    merged.loc[ppt_mask, "PPT Category"] = merged.loc[ppt_mask, "_fm_ppt_category"]
    filled_ppt = int(ppt_mask.sum())

    still_blank_pack = merged["Pack Size"].map(
        lambda v: (v is None) or (str(v).strip() == "") or pd.isna(v)
    )
    fallback_source = merged["Article"].where(merged["Article"].notna(), "")
    parsed = fallback_source.map(parse_pack_size_from_name)
    parse_mask = still_blank_pack & (parsed != "")
    merged.loc[parse_mask, "Pack Size"] = parsed[parse_mask]
    parsed_from_name = int(parse_mask.sum())

    final_missing_pack = merged["Pack Size"].map(
        lambda v: (v is None) or (str(v).strip() == "") or pd.isna(v)
    ).sum()

    merged = merged.drop(columns=[c for c in merged.columns if c.startswith("_fm_")])
    merged = merged.drop(columns=["_ean"])

    report = {
        "total_dms_rows": len(df),
        "fountain_matched_rows": int(matched.sum()),
        "fountain_matched_pct": round(100.0 * matched.sum() / len(df), 1) if len(df) else 0,
        "filled_from_fountain": {
            "Pack Size": filled_pack,
            "SKU Code": filled_sku,
            "Brand": filled_brand,
            "Category": filled_cat,
            "Sub Category": filled_sub,
            "Range": filled_range,
            "PPT Category": filled_ppt,
        },
        "pack_size_parsed_from_name": parsed_from_name,
        "final_missing_pack_size": int(final_missing_pack),
        "gst_still_missing": True,
        "unmatched_eans": sorted(set(df.loc[~matched, "_ean"])) if (~matched).any() else [],
    }
    return merged.reset_index(drop=True), report
