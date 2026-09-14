#!/usr/bin/env python3
"""Transform the resolved Aug'26 Primary source into the production
Primary_Article_Monthly schema, so the existing --detail-only build path
(scripts/build_dashboard_data.py) picks it up with no other code change.

Source: data/monthly/Aug26_primary_detailed.csv (53 columns, raw SAP export,
the file docs/DATA_LINEAGE.md's Aug'26 reconciliation recommends as the
correct Aug'26 Primary source over PowerBI/RawDataFolders/Primary_Aug26_FY27.csv).
Target: PowerBI/RawDataFolders/Primary_Article_Monthly/primary_article_Aug_26.csv,
matching the exact 24-column schema of every other file already in that
folder (e.g. primary_article_Jul_26.csv) -- confirmed by direct comparison,
not assumed.

Raw source stays untouched; this only ever writes the target file.

Column classification (Source Column -> Canonical Column -> Transformation -> Required):
  FY                      -> FY                        rewrite "FY'26-27" -> "FY27" (THE ONE FY RULE tag convention)   REQUIRED
  Month                   -> Month                     collapse per-row dates to the single display label "Aug'26" (matches every existing monthly file, which stores one label for the whole file, not a per-row date)   REQUIRED
  Channel                 -> Channel                   direct copy (MT/EB2B/SIS -- verified same domain as existing files)   REQUIRED
  Inv. Date               -> Inv. Date                 direct copy   REQUIRED
  Cust-SAP Code           -> Cust-SAP Code              direct copy (source also carries a duplicate "Cust-SAP Code.1" -- IGNORED, values checked identical to the primary column, not incorporated)   REQUIRED
  Ship To Name            -> Ship To Name               direct copy   REQUIRED
  EAN No.                 -> EAN No.                    direct copy   REQUIRED
  net_content             -> net_content                direct copy   OPTIONAL
  brand                   -> brand                      direct copy   REQUIRED
  PPT Category            -> PPT Category               direct copy   OPTIONAL
  category                -> category                   direct copy   REQUIRED
  sub_category            -> sub_category                direct copy   OPTIONAL
  range                   -> range                       direct copy   OPTIONAL
  Description             -> Description                 direct copy   OPTIONAL
  MRP Rate                -> MRP                          rename only, same value, same unit   REQUIRED
  Inv Qty                 -> Inv Qty                      direct copy   REQUIRED
  Inv. Net value(LOC)     -> Inv. Net value(LOC)           direct copy -- kept SIGNED (Sales positive, MRN/returns negative); the existing pipeline nets returns by summing signed values across ALL MTD-Sale types, not by pre-filtering rows, confirmed against primary_article_Jul_26.csv (31,355 rows, all 4 MTD-Sale type values present, its summed total matches the production Jul'26 NSV exactly)   REQUIRED
  Inv. Tax Amount(LOC)    -> Inv. Tax Amount(LOC)          direct copy   REQUIRED
  Total MRP sales         -> Total MRP sales               direct copy   REQUIRED
  Avg Tot                 -> Avg Tot                        direct copy   REQUIRED
  MTD-Sale type           -> MTD-Sale type                  direct copy, ALL VALUES KEPT (Sales/MRN/Cancel Invoice/Tester-FOC) -- do not filter, see Inv. Net value(LOC) note above   REQUIRED
  PO Type                 -> PO Type                        direct copy (Direct/Dist.)   REQUIRED
  Chain name              -> Chain name for Dashboard        rename only, same value, verified raw (not pre-canonicalised) in both source and every existing monthly file   REQUIRED
  Zone                    -> Zone                            direct copy   REQUIRED
  State                   -> State                           direct copy   REQUIRED

  IGNORED_WITH_REASON (present in source, dropped, not incorporated into any target column):
    Purchase Order Number, Inv No., Article Code, SO No, Division Desc.,
    Display Unit/Measure, "a", Bill Type Decsc, Distribution Channel Desc,
    Company Name, Customer Group, Customer Group Desc, Plant Description,
    Sales Document Type, Ship-To Address, Ship-To City, Ship-To Region,
    Ship-To Region Name, Plant, Order Reason Text, Customer Name,
    Customer Name.1, Store Code, "Delivery Status ", Remarks, Remarks-1,
    Cust-SAP Code.1, Format
      -- reason: none of these columns exist in the target schema (every
      other Primary_Article_Monthly/*.csv file also lacks them); dropping
      them matches the established schema, it does not lose any column the
      production pipeline reads.
    sale in lac
      -- reason: DERIVED, redundant -- equals Inv. Net value(LOC) / 1e5,
      recomputed downstream from the kept column; not carried forward
      because no existing monthly file carries it either.

  UNKNOWN_REQUIRES_REVIEW: none. Every source column was accounted for above.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE = REPO_ROOT / "data" / "monthly" / "Aug26_primary_detailed.csv"
TARGET = REPO_ROOT / "PowerBI" / "RawDataFolders" / "Primary_Article_Monthly" / "primary_article_Aug_26.csv"
REFERENCE_SCHEMA_FILE = REPO_ROOT / "PowerBI" / "RawDataFolders" / "Primary_Article_Monthly" / "primary_article_Jul_26.csv"

COLUMN_MAP = {
    "FY": "FY",
    "Month": "Month",
    "Channel": "Channel",
    "Inv. Date": "Inv. Date",
    "Cust-SAP Code": "Cust-SAP Code",
    "Ship To Name": "Ship To Name",
    "EAN No.": "EAN No.",
    "net_content": "net_content",
    "brand": "brand",
    "PPT Category": "PPT Category",
    "category": "category",
    "sub_category": "sub_category",
    "range": "range",
    "Description": "Description",
    "MRP Rate": "MRP",
    "Inv Qty": "Inv Qty",
    "Inv. Net value(LOC)": "Inv. Net value(LOC)",
    "Inv. Tax Amount(LOC)": "Inv. Tax Amount(LOC)",
    "Total MRP sales": "Total MRP sales",
    "Avg Tot": "Avg Tot",
    "MTD-Sale type": "MTD-Sale type",
    "PO Type": "PO Type",
    "Chain name": "Chain name for Dashboard",
    "Zone": "Zone",
    "State": "State",
}


def main() -> int:
    if not SOURCE.exists():
        print(f"FAIL: source not found: {SOURCE}")
        return 1
    if not REFERENCE_SCHEMA_FILE.exists():
        print(f"FAIL: reference schema file not found: {REFERENCE_SCHEMA_FILE}")
        return 1

    expected_cols = list(pd.read_csv(REFERENCE_SCHEMA_FILE, nrows=0).columns)
    src = pd.read_csv(SOURCE, low_memory=False)

    missing = [c for c in COLUMN_MAP if c not in src.columns]
    if missing:
        print(f"FAIL: source is missing expected columns: {missing}")
        return 1

    out = src[list(COLUMN_MAP.keys())].rename(columns=COLUMN_MAP)
    out["FY"] = "FY27"
    out["Month"] = "Aug'26"

    out = out[expected_cols]  # enforce exact column order match

    if list(out.columns) != expected_cols:
        print("FAIL: output schema does not match the reference file's schema/order")
        return 1

    src_total = src["Inv. Net value(LOC)"].sum()
    out_total = out["Inv. Net value(LOC)"].sum()
    if abs(src_total - out_total) > 0.01:
        print(f"FAIL: value did not survive the transform: source={src_total}, output={out_total}")
        return 1
    if len(src) != len(out):
        print(f"FAIL: row count did not survive the transform: source={len(src)}, output={len(out)}")
        return 1

    TARGET.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(TARGET, index=False)

    print(f"OK  wrote {TARGET}")
    print(f"OK  rows: {len(out)} (source: {len(src)}, match)")
    print(f"OK  Inv. Net value(LOC) total: {out_total:,.2f} (source: {src_total:,.2f}, match)")
    print(f"OK  Rs {out_total / 1e5:,.2f} Lakh = Rs {out_total / 1e7:,.2f} Cr")
    print(f"OK  FY values: {sorted(out['FY'].unique())}")
    print(f"OK  Month values: {sorted(out['Month'].unique())}")
    print(f"OK  MTD-Sale type values kept: {sorted(out['MTD-Sale type'].dropna().unique())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
