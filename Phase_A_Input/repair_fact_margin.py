#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Remediation pass for fact_margin.csv.

Root causes identified:
  1. build_inputs.py treats the raw offtake 'NSV' column as "lacs per consumer
     unit" uniformly. The actual denomination varies per chain — for large modern
     trade chains the same column stores case/bundle or total site-level NSV,
     producing incorrect margin_pct → tot_pct for 91% of DERIVED rows.
  2. cm2_pct mixes two incompatible value types (₹/unit for DERIVED rows,
     %NSV for ESTIMATED rows) in one column with no type discriminator.
  3. No denomination flag exists to distinguish consumer-unit MRP from
     pack/case or aggregate MRP.

What this script does:
  - Cross-references fact_margin against primary_history (company invoice
    records — the authoritative brand NSV source) and offtake_history.
  - Classifies mrp_denomination per EAN × chain from formula_vs_primary_ratio.
  - Computes unit_nsv_validated = primary_unit_nsv (brand invoice per unit)
    where history is available and denomination is CONSUMER_UNIT_MRP.
  - For PACK_CASE_LEVEL_MRP and AGGREGATE_DENOMINATION rows: unit_nsv is
    UNAVAILABLE (cannot convert without validated pack-size conversion).
  - Separates cm2_pct into: cm2_value_per_unit, cm2_pct (rate), cm2_value_type,
    cm2_source, cm2_approval_status, cm2_approved_by, cm2_approval_date.
  - Preserves originals in audit fields.
  - Outputs repaired fact_margin.csv and unit_economics_exceptions.csv.

Does NOT:
  - Fabricate NSV or CM2 for missing-input rows.
  - Divide aggregate MRP by assumed pack size.
  - Mark any CM2 as Finance-approved.
"""
import pandas as pd
import numpy as np
from pathlib import Path
import datetime as dt

HERE = Path(__file__).resolve().parent

# ── thresholds ──────────────────────────────────────────────────────────────
# formula_nsv / primary_unit_nsv:
#   ≤ 2.5  → CONSUMER_UNIT_MRP  (formula at consumer-unit level, primary ≈ invoice)
#   ≤ 50   → PACK_CASE_LEVEL_MRP (formula represents a multi-unit pack or case)
#   > 50 or highly variable → AGGREGATE_DENOMINATION (cannot use for unit economics)
RATIO_CONSUMER_CEILING  = 2.5
RATIO_PACK_CEILING      = 50.0
MIN_PRIMARY_OBS         = 2          # minimum primary history months to trust the ratio
CV_AGGREGATE_THRESHOLD  = 1.5       # CV of per-month ratios above this → AGGREGATE

# ── load inputs ─────────────────────────────────────────────────────────────
print("Loading inputs …")
df  = pd.read_csv(HERE / "fact_margin.csv", dtype=str)
ph  = pd.read_csv(HERE / "primary_history.csv", dtype=str)
oh  = pd.read_csv(HERE / "offtake_history.csv", dtype=str)

# numeric coercions
for col in ["mrp", "margin_pct", "tot_pct", "gst_pct", "cm2_pct"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

for col in ["primary_qty", "primary_nsv"]:
    ph[col] = pd.to_numeric(ph[col], errors="coerce")

for col in ["offtake_qty", "offtake_nsv"]:
    oh[col] = pd.to_numeric(oh[col], errors="coerce")

ph = ph[ph["primary_qty"].notna() & (ph["primary_qty"] > 0)]
ph = ph[ph["primary_nsv"].notna() & (ph["primary_nsv"] > 0)]

# ── per-EAN primary unit NSV (monthly, for CV computation) ──────────────────
ph["p_unit_nsv"] = ph["primary_nsv"] / ph["primary_qty"]

ph_monthly = (
    ph.groupby(["ean", "month"])
    .agg(qty=("primary_qty", "sum"), nsv=("primary_nsv", "sum"))
    .reset_index()
)
ph_monthly["unit_nsv"] = ph_monthly["nsv"] / ph_monthly["qty"]

ph_ean = (
    ph_monthly.groupby("ean")["unit_nsv"]
    .agg(
        p_unit_nsv_median="median",
        p_unit_nsv_cv=lambda x: (x.std() / x.mean()) if x.mean() > 0 else np.nan,
        p_unit_nsv_count="count",
    )
    .reset_index()
)
print(f"  Primary EAN coverage: {len(ph_ean)} EANs")

# ── per-EAN×chain offtake unit NSV (secondary validation only) ───────────────
oh_chain_col = "chain_name" if "chain_name" in oh.columns else "chain"
oh_grp = (
    oh[oh["offtake_qty"] > 0]
    .groupby(["ean", oh_chain_col])
    .agg(sum_oqty=("offtake_qty", "sum"), sum_onsv=("offtake_nsv", "sum"))
    .reset_index()
    .rename(columns={oh_chain_col: "chain_name"})
)
oh_grp["obs_offtake_unit_nsv"] = (oh_grp["sum_onsv"] / oh_grp["sum_oqty"]).round(4)

# ── merge into fact_margin ───────────────────────────────────────────────────
df["mrp_original"]       = df["mrp"]
df["tot_pct_original"]   = df["tot_pct"]
df["cm2_pct_original"]   = df["cm2_pct"]
df["mrp_source_column"]  = "M-Value"

df = df.merge(ph_ean, on="ean", how="left")
df = df.merge(oh_grp, on=["ean", "chain_name"], how="left")

# ── formula NSV with stored inputs ──────────────────────────────────────────
df["gst_factor"] = 1.0 + df["gst_pct"].fillna(0) / 100.0
df["tot_factor"] = 1.0 + df["tot_pct"].fillna(0) / 100.0
df["formula_unit_nsv_stored_tot"] = (
    df["mrp"] / (df["gst_factor"] * df["tot_factor"])
).round(4)

# ── denomination classification ──────────────────────────────────────────────
df["formula_vs_primary_ratio"] = (
    df["formula_unit_nsv_stored_tot"] / df["p_unit_nsv_median"]
).round(3)

def classify_denomination(row):
    if row["quality_status"] == "ESTIMATED":
        return "ESTIMATED_PLACEHOLDER"
    ratio = row["formula_vs_primary_ratio"]
    n     = row["p_unit_nsv_count"]
    if pd.isna(ratio) or pd.isna(n) or n < MIN_PRIMARY_OBS:
        return "UNKNOWN_NO_PRIMARY_HISTORY"
    # High coefficient-of-variation on primary unit NSV → denominator inconsistency
    cv = row.get("p_unit_nsv_cv", 0) or 0
    if cv > CV_AGGREGATE_THRESHOLD:
        return "AGGREGATE_DENOMINATION"
    if ratio <= RATIO_CONSUMER_CEILING:
        return "CONSUMER_UNIT_MRP"
    if ratio <= RATIO_PACK_CEILING:
        return "PACK_CASE_LEVEL_MRP"
    return "AGGREGATE_DENOMINATION"

df["mrp_denomination"] = df.apply(classify_denomination, axis=1)

# ── unit NSV validated (brand invoice level from primary history) ────────────
# Only meaningful for CONSUMER_UNIT_MRP.
# For PACK/AGGREGATE: the primary_unit_nsv is per-consumer-unit from company books;
# without a validated pack-size conversion, we CANNOT derive pack-level brand NSV.
df["unit_nsv_validated"]     = np.nan
df["unit_nsv_source"]        = "UNAVAILABLE"
df["unit_nsv_validation_status"] = "NOT_VALIDATED"

cu_mask  = df["mrp_denomination"] == "CONSUMER_UNIT_MRP"
est_mask = df["mrp_denomination"] == "ESTIMATED_PLACEHOLDER"

df.loc[cu_mask, "unit_nsv_validated"]          = df.loc[cu_mask, "p_unit_nsv_median"].round(4)
df.loc[cu_mask, "unit_nsv_source"]             = "PRIMARY_INVOICE_HISTORY"
df.loc[cu_mask, "unit_nsv_validation_status"]  = "VALIDATED_VS_PRIMARY_INVOICE"

# ESTIMATED rows: use formula with stored inputs (all ESTIMATED; mrp=250 placeholder)
df.loc[est_mask, "unit_nsv_validated"] = df.loc[est_mask, "formula_unit_nsv_stored_tot"]
df.loc[est_mask, "unit_nsv_source"]    = "FORMULA_ESTIMATED_PLACEHOLDER"
df.loc[est_mask, "unit_nsv_validation_status"] = "ESTIMATED_UNVALIDATED"

# Rows with no primary history but consumer-unit classification possible:
# leave as UNAVAILABLE so we don't fabricate.

# ── effective TOT% from primary (for reference / audit) ─────────────────────
# NSV = MRP / ((1+GST/100) × (1+TOT/100))  → effective_TOT = MRP/(nsv × gst_factor) - 1
# This gives the TOTAL supply-chain margin from brand NSV to consumer MRP.
df["effective_tot_from_primary"] = np.where(
    cu_mask & df["unit_nsv_validated"].notna() & (df["unit_nsv_validated"] > 0),
    ((df["mrp"] / (df["unit_nsv_validated"] * df["gst_factor"])) - 1) * 100,
    np.nan
).round(2)

# ── formula NSV using primary-validated NSV (for CONSUMER_UNIT rows) ─────────
# Since unit_nsv_validated IS the brand NSV, formula_nsv_validated = unit_nsv_validated.
df["formula_unit_nsv_validated"] = df["unit_nsv_validated"]

# ── CM2 field separation ─────────────────────────────────────────────────────
# Rule from fact_margin analysis:
#   DERIVED rows:   cm2_pct = mrp × 0.12 (₹ per consumer unit, invariant)
#                   → value type: PER_UNIT_RUPEES
#   ESTIMATED rows: cm2_pct = 15.0 flat rate (% of NSV)
#                   → value type: PERCENT_OF_NSV

# cm2_value_per_unit: absolute ₹ per operational unit
df["cm2_value_per_unit"] = np.nan
derived_mask = df["quality_status"] == "DERIVED"
df.loc[derived_mask, "cm2_value_per_unit"] = df.loc[derived_mask, "cm2_pct"].round(4)  # already ₹/unit (= mrp × 0.12)

# cm2_pct column: now ONLY the rate (% of NSV) for ESTIMATED; blank for DERIVED
df["cm2_pct_rate"] = np.nan
df.loc[est_mask, "cm2_pct_rate"] = df.loc[est_mask, "cm2_pct"]  # = 15.0 for ESTIMATED

# cm2_value_type
df["cm2_value_type"] = "UNKNOWN"
df.loc[derived_mask, "cm2_value_type"] = "PER_UNIT_RUPEES"
df.loc[est_mask,     "cm2_value_type"] = "PERCENT_OF_NSV"

# cm2_source: traceability of how the CM2 figure was derived
df["cm2_source"] = "UNAVAILABLE"
df.loc[derived_mask, "cm2_source"] = "DERIVED_12PCT_OF_CONSUMER_MRP_PLACEHOLDER"
df.loc[est_mask,     "cm2_source"] = "ESTIMATED_15PCT_NSV_PLACEHOLDER"

# For PACK/AGGREGATE DERIVED rows, the cm2_value_per_unit is mrp × 0.12 at pack level —
# not per-consumer-unit. Flag these.
pack_agg_derived = derived_mask & ~cu_mask
df.loc[pack_agg_derived, "cm2_source"] = "DERIVED_12PCT_OF_PACK_MRP_DENOMINATION_UNKNOWN"

# All rows: no Finance approval exists
df["cm2_approval_status"] = "PROVISIONAL_NOT_FINANCE_APPROVED"
df["cm2_approved_by"]     = None
df["cm2_approval_date"]   = None

# ── unit economics sanity flags ──────────────────────────────────────────────
df["unit_econ_flag"] = "OK"

# NSV > MRP (impossible)
nsv_gt_mrp = (
    df["unit_nsv_validated"].notna() &
    (df["unit_nsv_validated"] > df["mrp_original"])
)
df.loc[nsv_gt_mrp, "unit_econ_flag"] = "NSV_EXCEEDS_MRP_ERROR"

# MRP = 0 or missing
mrp_zero = df["mrp_original"].isna() | (df["mrp_original"] <= 0)
df.loc[mrp_zero, "unit_econ_flag"] = "ZERO_OR_MISSING_MRP"

# CM2 > NSV (without approved explanation)
cm2_gt_nsv = (
    df["unit_nsv_validated"].notna() &
    df["cm2_value_per_unit"].notna() &
    (df["cm2_value_per_unit"] > df["unit_nsv_validated"]) &
    (df["cm2_approval_status"] != "FINANCE_APPROVED")
)
df.loc[cm2_gt_nsv, "unit_econ_flag"] = "CM2_EXCEEDS_NSV_UNAPPROVED"

# Aggregate denomination (cannot compute unit NSV)
df.loc[df["mrp_denomination"] == "AGGREGATE_DENOMINATION", "unit_econ_flag"] = "AGGREGATE_DENOMINATION_NO_UNIT_NSV"
df.loc[df["mrp_denomination"] == "PACK_CASE_LEVEL_MRP", "unit_econ_flag"] = "PACK_CASE_LEVEL_NO_CONSUMER_UNIT_NSV"

# VMM negative margin_pct (data engineering error from build_inputs)
vmm_neg = (df["chain_name"] == "VMM") & (df["margin_pct"] < 0)
df.loc[vmm_neg, "unit_econ_flag"] = "VMM_NEGATIVE_MARGIN_DATA_ENGINEERING_ERROR"

# Validated NSV significantly below formula NSV (>25% deviance)
nsv_deviance = (
    df["unit_nsv_validated"].notna() &
    df["formula_unit_nsv_stored_tot"].notna() &
    (df["formula_unit_nsv_stored_tot"] > 0)
)
rel_dev = (
    (df["formula_unit_nsv_stored_tot"] - df["unit_nsv_validated"]).abs() /
    df["formula_unit_nsv_stored_tot"]
)
significant_deviance = nsv_deviance & (rel_dev > 0.25)
update_mask = significant_deviance & ~df["unit_econ_flag"].isin([
    "NSV_EXCEEDS_MRP_ERROR", "ZERO_OR_MISSING_MRP",
    "CM2_EXCEEDS_NSV_UNAPPROVED", "AGGREGATE_DENOMINATION_NO_UNIT_NSV",
    "PACK_CASE_LEVEL_NO_CONSUMER_UNIT_NSV"
])
df.loc[update_mask, "unit_econ_flag"] = "NSV_MATERIAL_DEVIANCE_VS_FORMULA"

# ── assemble output columns ──────────────────────────────────────────────────
output_cols = [
    # Identity
    "month", "chain_name", "brand", "category", "article", "ean",
    # MRP — corrected
    "mrp",               # = mrp_original (no correction without pack-size validation)
    "mrp_original",
    "mrp_source_column",
    "mrp_denomination",
    "formula_vs_primary_ratio",
    # Trade terms — originals preserved; effective for reference
    "margin_pct",        # original (retailer-level derived — NOT brand TOT%)
    "tot_pct",           # original (retailer-level derived — NOT brand TOT%)
    "tot_pct_original",
    "effective_tot_from_primary",   # band-level TOT inferred from primary (reference only)
    "gst_pct",
    # NSV — validated
    "unit_nsv_validated",
    "unit_nsv_source",
    "unit_nsv_validation_status",
    "formula_unit_nsv_stored_tot",  # formula with stored tot_pct (for audit comparison)
    # Primary history reference
    "p_unit_nsv_median",
    "p_unit_nsv_count",
    # CM2 — separated fields
    "cm2_value_per_unit",   # ₹ per unit (DERIVED rows only)
    "cm2_pct_rate",          # % of NSV (ESTIMATED rows only)
    "cm2_pct_original",      # original mixed field (audit)
    "cm2_value_type",        # PER_UNIT_RUPEES | PERCENT_OF_NSV | UNKNOWN
    "cm2_source",
    "cm2_approval_status",
    "cm2_approved_by",
    "cm2_approval_date",
    # Data quality
    "quality_status",
    "unit_econ_flag",
]

out = df[[c for c in output_cols if c in df.columns]].copy()
out_path = HERE / "fact_margin.csv"
out.to_csv(out_path, index=False)
print(f"\n✓ Repaired fact_margin.csv  → {len(out):,} rows, {len(out.columns)} columns")

# ── unit economics exceptions report ────────────────────────────────────────
flag_counts = df["unit_econ_flag"].value_counts()
print("\n=== Unit economics exceptions:")
print(flag_counts.to_string())

exceptions = df[df["unit_econ_flag"] != "OK"].copy()
exc_cols = [
    "chain_name", "ean", "article", "brand", "category",
    "mrp_original", "mrp_denomination", "formula_vs_primary_ratio",
    "unit_nsv_validated", "unit_nsv_source",
    "formula_unit_nsv_stored_tot", "tot_pct_original",
    "cm2_value_per_unit", "cm2_value_type",
    "quality_status", "unit_econ_flag",
]
exc_out = exceptions[[c for c in exc_cols if c in exceptions.columns]]
exc_path = HERE / "unit_economics_exceptions.csv"
exc_out.to_csv(exc_path, index=False)
print(f"\n✓ Exceptions report → {len(exc_out):,} rows  → {exc_path.name}")

# ── coverage summary ─────────────────────────────────────────────────────────
print("\n=== Financial input coverage summary:")
total = len(out)
cu   = (out["mrp_denomination"] == "CONSUMER_UNIT_MRP").sum()
pack = (out["mrp_denomination"] == "PACK_CASE_LEVEL_MRP").sum()
agg  = (out["mrp_denomination"] == "AGGREGATE_DENOMINATION").sum()
est  = (out["mrp_denomination"] == "ESTIMATED_PLACEHOLDER").sum()
unk  = (out["mrp_denomination"] == "UNKNOWN_NO_PRIMARY_HISTORY").sum()
validated = out["unit_nsv_validated"].notna().sum()
print(f"  Total rows               : {total:>5}")
print(f"  CONSUMER_UNIT_MRP        : {cu:>5} ({100*cu/total:.1f}%)")
print(f"  PACK_CASE_LEVEL_MRP      : {pack:>5} ({100*pack/total:.1f}%)")
print(f"  AGGREGATE_DENOMINATION   : {agg:>5} ({100*agg/total:.1f}%)")
print(f"  ESTIMATED_PLACEHOLDER    : {est:>5} ({100*est/total:.1f}%)")
print(f"  UNKNOWN_NO_PRIMARY_HIST  : {unk:>5} ({100*unk/total:.1f}%)")
print(f"  Rows with validated NSV  : {validated:>5} ({100*validated/total:.1f}%)")
print(f"  cm2_approval_status=PROVISIONAL: {(out['cm2_approval_status']=='PROVISIONAL_NOT_FINANCE_APPROVED').sum():>5}")
print()
print("NEXT STEP: Finance team must:")
print("  1. Validate/correct unit_nsv_validated for PACK_CASE_LEVEL_MRP chains")
print("     (requires pack-size conversion factor per EAN × chain)")
print("  2. Provide Finance-approved CM2 per unit (approve cm2_value_per_unit or cm2_pct_rate)")
print("  3. Review and approve AGGREGATE_DENOMINATION rows — these chains have no unit NSV")
print("  4. Update cm2_approval_status, cm2_approved_by, cm2_approval_date for approved rows")
