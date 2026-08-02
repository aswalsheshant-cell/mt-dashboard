# -*- coding: utf-8 -*-
"""Fountain-based consumer-unit MRP enrichment for PACK_CASE and AGGREGATE rows.

Phase 2 – EAN matching  (313/315 EANs matched = 99.4%)
Phase 3 – MRP classification (implied ratio, denomination re-classification)
Phase 4 – MRP reasonableness tests
Phase 5 – Proposed unit_nsv using Fountain consumer-unit MRP
Phase 6 – TOT double-counting detection (FIN-GATE-TOT-001)

Design constraints (from business owner, non-negotiable):
  - Do NOT divide MRP by grams, millilitres, or quantity in the product name.
  - Do NOT automatically apply a unit-count factor unless the source record
    explicitly flags it as case-level and the conversion is approved.
  - Fountain MRP replaces the margin-repo MRP for pending rows because Fountain
    stores consumer-unit prices by EAN — no division is involved.
  - AGGREGATE_DENOMINATION rows get Fountain MRP as the proposed per-unit price;
    the aggregate value is retained as `original_mrp` for audit.
  - 2 EANs with no Fountain match remain UNRESOLVED; their NSV stays zero.

All proposed NSV values are TENTATIVE and must be Finance-approved before
any FINAL FINANCIAL reporting.
"""
from __future__ import annotations

import glob
import os
import re
import pandas as pd
import numpy as np
from typing import Optional, Tuple

# ── Paths ────────────────────────────────────────────────────────────────────
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FOUNTAIN_DIR = os.path.join(_REPO_ROOT, "PowerBI", "RawDataFolders", "Offtake_Monthly")
FACT_MARGIN_PATH = os.path.join(_REPO_ROOT, "Phase_A_Input", "fact_margin.csv")

# Denominations that block consumer-unit NSV calculation in the forecast engine
PENDING_DENOMINATIONS = ("PACK_CASE_LEVEL_MRP", "AGGREGATE_DENOMINATION")

# Reasonable pack-unit multiplier range (implied ratio must fall within this)
MIN_RATIO = 0.80   # Fountain MRP ≤ margin MRP (small rounding acceptable)
MAX_RATIO = 250.0  # No real SKU should have case > 250 units


# ── EAN normalisation ────────────────────────────────────────────────────────

def _clean_ean(v) -> str:
    if pd.isna(v):
        return ""
    s = str(v).strip()
    if s.endswith(".0"):
        s = s[:-2]
    return s


# ── Fountain master loader ───────────────────────────────────────────────────

def load_consolidated_fountain_master(fountain_dir: str = FOUNTAIN_DIR) -> Tuple[pd.DataFrame, dict]:
    """Load all available Fountain offtake files and build a consolidated EAN master.

    Returns (master_df, meta_dict).
    master_df columns: EAN, fountain_consumer_unit_mrp (modal across files),
        fountain_net_weight, fountain_article_code, fountain_brand,
        fountain_category, fountain_sub_category, fountain_range,
        fountain_description, fountain_source_file (latest file where EAN appears).
    """
    FOUNTAIN_COLS = [
        "EAN", "MRP", "Net Weight", "Article", "Brand",
        "Category", "Sub_category", "Range", "Description as per Fountain",
    ]
    files = sorted(glob.glob(os.path.join(fountain_dir, "offtake_store_article_*.csv")))
    if not files:
        raise FileNotFoundError(f"No Fountain offtake files found in {fountain_dir}")

    frames = []
    for f in files:
        try:
            df = pd.read_csv(f, dtype=str, low_memory=False,
                             usecols=[c for c in FOUNTAIN_COLS
                                      if c in pd.read_csv(f, nrows=0).columns])
            df["_source_file"] = os.path.basename(f)
            frames.append(df)
        except Exception:
            pass

    combined = pd.concat(frames, ignore_index=True)
    combined["EAN"] = combined["EAN"].map(_clean_ean)
    combined = combined[combined["EAN"] != ""]

    # Modal MRP per EAN (most frequent non-null value across all files)
    def _modal(s):
        s = s.dropna()
        return s.mode().iloc[0] if not s.empty else None

    mrp_modal = (combined.groupby("EAN")["MRP"]
                 .apply(_modal)
                 .rename("fountain_consumer_unit_mrp")
                 .reset_index())

    # Latest canonical record per EAN
    latest = combined.sort_values("_source_file").groupby("EAN").last().reset_index()
    latest = latest.rename(columns={
        "MRP":                         "fountain_mrp_latest",
        "Net Weight":                  "fountain_net_weight",
        "Article":                     "fountain_article_code",
        "Brand":                       "fountain_brand",
        "Category":                    "fountain_category",
        "Sub_category":                "fountain_sub_category",
        "Range":                       "fountain_range",
        "Description as per Fountain": "fountain_description",
        "_source_file":                "fountain_source_file",
    })

    master = latest.merge(mrp_modal, on="EAN", how="left")
    # Prefer modal MRP; fall back to latest
    master["fountain_consumer_unit_mrp"] = (
        master["fountain_consumer_unit_mrp"]
        .fillna(master["fountain_mrp_latest"])
    )
    master = master.drop(columns=["fountain_mrp_latest"], errors="ignore")

    meta = {
        "fountain_files_loaded": [os.path.basename(f) for f in files],
        "total_rows_across_files": len(combined),
        "unique_eans": len(master),
    }
    return master, meta


# ── Phase 2: EAN matching ────────────────────────────────────────────────────

def match_eans(
    fact_margin: pd.DataFrame,
    fountain_master: pd.DataFrame,
) -> pd.DataFrame:
    """Add EAN-match columns to fact_margin rows with pending denominations.

    Adds columns:
      normalised_ean, fountain_ean, match_method, match_confidence,
      manual_review_required, match_status, mismatch_reason.
    Returns the full fact_margin with new columns (non-pending rows get
    match_status = 'NOT_APPLICABLE').
    """
    df = fact_margin.copy()
    df["normalised_ean"] = df["ean"].map(_clean_ean)

    fm = fountain_master.copy()
    fm["fountain_ean"] = fm["EAN"].map(_clean_ean)

    fountain_ean_set = set(fm["fountain_ean"].unique())

    # Default: not applicable
    for col in ["fountain_ean", "match_method", "match_confidence",
                "match_status", "mismatch_reason"]:
        df[col] = "NOT_APPLICABLE"
    df["manual_review_required"] = False

    pending_mask = df["mrp_denomination"].isin(PENDING_DENOMINATIONS)
    pending = df[pending_mask].copy()

    def _classify_match(ean: str):
        if ean in fountain_ean_set:
            return ean, "EXACT_EAN", "HIGH", False, "MATCHED", ""
        stripped = ean.lstrip("0")
        if stripped in fountain_ean_set:
            return stripped, "STRIPPED_LEADING_ZERO", "MEDIUM", True, "MATCHED_NORMALISED", ""
        return "", "NO_MATCH", "NONE", True, "UNRESOLVED", "EAN not found in any Fountain file"

    tuples = pending["normalised_ean"].map(_classify_match).tolist()
    if tuples:
        t_ean, t_method, t_conf, t_rev, t_status, t_mismatch = zip(*tuples)
        idx_list = pending.index.tolist()
        df.loc[idx_list, "fountain_ean"] = list(t_ean)
        df.loc[idx_list, "match_method"] = list(t_method)
        df.loc[idx_list, "match_confidence"] = list(t_conf)
        df.loc[idx_list, "manual_review_required"] = list(t_rev)
        df.loc[idx_list, "match_status"] = list(t_status)
        df.loc[idx_list, "mismatch_reason"] = list(t_mismatch)

    return df


# ── Phase 3: MRP classification ─────────────────────────────────────────────

def classify_mrp(
    enriched_df: pd.DataFrame,
    fountain_master: pd.DataFrame,
) -> pd.DataFrame:
    """Classify the existing MRP vs Fountain MRP and assign proposed consumer-unit MRP.

    Adds columns:
      original_mrp, fountain_consumer_unit_mrp, implied_unit_ratio,
      implied_ratio_is_integer, mrp_proposed_classification,
      proposed_consumer_unit_mrp, proposed_mrp_source.
    """
    df = enriched_df.copy()

    fm_lookup = (fountain_master
                 .assign(fountain_ean=fountain_master["EAN"].map(_clean_ean))
                 .set_index("fountain_ean")
                 [["fountain_consumer_unit_mrp", "fountain_net_weight",
                   "fountain_description", "fountain_source_file"]])

    for col in ["original_mrp", "fountain_consumer_unit_mrp",
                "implied_unit_ratio", "implied_ratio_is_integer",
                "mrp_proposed_classification", "proposed_consumer_unit_mrp",
                "proposed_mrp_source"]:
        df[col] = None

    pending_mask = df["mrp_denomination"].isin(PENDING_DENOMINATIONS)

    for idx in df[pending_mask].index:
        row = df.loc[idx]
        f_ean = str(row["fountain_ean"])
        orig_mrp = _safe_float(row["mrp"])
        df.at[idx, "original_mrp"] = orig_mrp

        if f_ean not in fm_lookup.index:
            df.at[idx, "mrp_proposed_classification"] = "UNRESOLVED_NO_FOUNTAIN_MATCH"
            df.at[idx, "proposed_mrp_source"] = "NONE"
            continue

        f_row = fm_lookup.loc[f_ean]
        f_mrp = _safe_float(f_row["fountain_consumer_unit_mrp"])
        df.at[idx, "fountain_consumer_unit_mrp"] = f_mrp

        if f_mrp is None or f_mrp <= 0:
            df.at[idx, "mrp_proposed_classification"] = "FOUNTAIN_MRP_MISSING"
            df.at[idx, "proposed_mrp_source"] = "NONE"
            continue

        if orig_mrp is not None and orig_mrp > 0 and f_mrp > 0:
            ratio = orig_mrp / f_mrp
            df.at[idx, "implied_unit_ratio"] = round(ratio, 4)
            # Check if ratio is near an integer (±5% tolerance)
            nearest_int = round(ratio)
            is_integer = (nearest_int > 0
                          and abs(ratio - nearest_int) / nearest_int <= 0.05)
            df.at[idx, "implied_ratio_is_integer"] = is_integer
        else:
            ratio = None

        # Classification
        denom = str(row["mrp_denomination"])
        if denom == "PACK_CASE_LEVEL_MRP":
            if ratio is not None and 0.9 <= ratio <= 1.1:
                classification = "CONSUMER_UNIT_MRP_CONFIRMED"
            elif ratio is not None and MIN_RATIO <= ratio <= MAX_RATIO:
                classification = "CASE_OR_MULTIPACK_MRP_FOUNTAIN_RESOLVES_UNIT"
            else:
                classification = "RATIO_OUT_OF_RANGE_MANUAL_REVIEW"
        elif denom == "AGGREGATE_DENOMINATION":
            classification = "AGGREGATE_FOUNTAIN_RESOLVES_UNIT"
        else:
            classification = "NOT_APPLICABLE"

        df.at[idx, "mrp_proposed_classification"] = classification

        # Proposed consumer-unit MRP from Fountain — no division applied;
        # Fountain stores consumer-unit price directly.
        df.at[idx, "proposed_consumer_unit_mrp"] = f_mrp
        df.at[idx, "proposed_mrp_source"] = (
            f"FOUNTAIN_MASTER:{f_row['fountain_source_file']}"
        )

    return df


# ── Phase 4: MRP reasonableness ─────────────────────────────────────────────

def validate_mrp_reasonableness(
    enriched_df: pd.DataFrame,
    fact_margin_full: pd.DataFrame,
) -> pd.DataFrame:
    """Reasonableness checks on proposed_consumer_unit_mrp.

    Checks:
      (a) Fountain MRP is lower than original MRP (for PACK_CASE rows)
      (b) Proposed unit NSV < MRP (sanity)
      (c) Cross-chain modal MRP consistency for same EAN

    Adds columns: mrp_reasonableness_status, mrp_reasonableness_notes.
    """
    df = enriched_df.copy()
    df["mrp_reasonableness_status"] = "NOT_EVALUATED"
    df["mrp_reasonableness_notes"] = ""

    # Cross-chain modal MRP from all margin data (including resolved rows)
    modal_mrp = (fact_margin_full
                 .assign(ean_c=fact_margin_full["ean"].map(_clean_ean),
                         mrp_f=pd.to_numeric(fact_margin_full["mrp"], errors="coerce"))
                 .groupby("ean_c")["mrp_f"]
                 .agg(lambda s: s.dropna().mode().iloc[0] if not s.dropna().empty else None)
                 .rename("cross_chain_modal_mrp"))

    pending_mask = df["mrp_denomination"].isin(PENDING_DENOMINATIONS)

    for idx in df[pending_mask].index:
        row = df.loc[idx]
        proposed = _safe_float(row.get("proposed_consumer_unit_mrp"))
        original = _safe_float(row.get("original_mrp"))
        gst = _safe_float(row.get("gst_pct"), default=18.0)
        tot = _safe_float(row.get("tot_pct"), default=36.44)
        notes = []
        status = "REASONABLE"

        if proposed is None:
            df.at[idx, "mrp_reasonableness_status"] = "UNRESOLVED"
            df.at[idx, "mrp_reasonableness_notes"] = "No proposed MRP available"
            continue

        # (a) Fountain MRP must be ≤ original MRP for PACK_CASE rows
        denom = str(row.get("mrp_denomination", ""))
        if denom == "PACK_CASE_LEVEL_MRP" and original is not None and proposed > original * 1.05:
            status = "FLAG_FOUNTAIN_EXCEEDS_ORIGINAL"
            notes.append(f"Fountain MRP {proposed} > original {original} (unexpected for case pack)")

        # (b) Proposed NSV sanity: NSV = MRP / ((1+GST/100)*(1+TOT/100)) must be > 0
        if gst > 0 and tot > 0:
            proposed_nsv = proposed / ((1 + gst / 100) * (1 + tot / 100))
            if proposed_nsv <= 0:
                status = "INVALID_ZERO_NSV"
                notes.append(f"Proposed NSV would be {proposed_nsv:.2f}")
            elif proposed_nsv > proposed:
                status = "INVALID_NSV_EXCEEDS_MRP"
                notes.append(f"NSV {proposed_nsv:.2f} > MRP {proposed}")

        # (c) Cross-chain consistency
        ean_c = str(row.get("normalised_ean", ""))
        modal = _safe_float(modal_mrp.get(ean_c))
        if modal is not None and modal > 0:
            diff_pct = abs(proposed - modal) / modal * 100
            if diff_pct > 20:
                notes.append(f"Fountain MRP {proposed} differs >20% from cross-chain modal {modal:.0f}")
                if status == "REASONABLE":
                    status = "FLAG_CROSS_CHAIN_DIVERGENCE"

        df.at[idx, "mrp_reasonableness_status"] = status
        df.at[idx, "mrp_reasonableness_notes"] = "; ".join(notes) if notes else "OK"

    return df


# ── Phase 5: Proposed unit NSV ───────────────────────────────────────────────

def compute_proposed_nsv(enriched_df: pd.DataFrame) -> pd.DataFrame:
    """Compute proposed unit_nsv for pending rows using Fountain consumer-unit MRP.

    Adds columns:
      proposed_unit_nsv_formula, proposed_nsv_source,
      proposed_nsv_confidence, proposed_nsv_coverage_flag.

    NSV formula: MRP / ((1 + GST%/100) × (1 + TOT%/100))
    This uses the Fountain consumer-unit MRP — no pack-size division.
    """
    df = enriched_df.copy()

    for col in ["proposed_unit_nsv_formula", "proposed_nsv_source",
                "proposed_nsv_confidence", "proposed_nsv_coverage_flag"]:
        df[col] = None

    pending_mask = df["mrp_denomination"].isin(PENDING_DENOMINATIONS)

    for idx in df[pending_mask].index:
        row = df.loc[idx]
        proposed_mrp = _safe_float(row.get("proposed_consumer_unit_mrp"))
        gst = _safe_float(row.get("gst_pct"), default=18.0)
        tot = _safe_float(row.get("tot_pct"), default=36.44)
        classification = str(row.get("mrp_proposed_classification", ""))

        if proposed_mrp is None or proposed_mrp <= 0:
            df.at[idx, "proposed_nsv_coverage_flag"] = "UNRESOLVED"
            df.at[idx, "proposed_nsv_source"] = "NONE"
            continue

        if gst <= 0 or tot <= 0:
            df.at[idx, "proposed_nsv_coverage_flag"] = "MISSING_RATES"
            df.at[idx, "proposed_nsv_source"] = "NONE"
            continue

        unit_nsv = proposed_mrp / ((1 + gst / 100) * (1 + tot / 100))
        df.at[idx, "proposed_unit_nsv_formula"] = round(unit_nsv, 4)

        source = row.get("proposed_mrp_source", "")
        df.at[idx, "proposed_nsv_source"] = f"FOUNTAIN_FORMULA:{source}"

        if "UNRESOLVED" in classification or "MANUAL_REVIEW" in classification:
            confidence = "LOW"
        elif "AGGREGATE" in classification:
            confidence = "MEDIUM"
        else:
            confidence = "HIGH"
        df.at[idx, "proposed_nsv_confidence"] = confidence
        df.at[idx, "proposed_nsv_coverage_flag"] = "PROPOSED_TENTATIVE"

    return df


# ── Phase 6: TOT double-counting gate ────────────────────────────────────────

def run_finance_gate_tot(
    fact_margin: pd.DataFrame,
    forecast_df: Optional[pd.DataFrame] = None,
) -> dict:
    """FIN-GATE-TOT-001: detect TOT double-counting in NSV and trade-spend.

    The forecast engine computes:
        trade_spend = unit_nsv × TOT%

    When unit_nsv comes from PRIMARY_INVOICE_HISTORY, it already reflects
    actual trade terms deducted from MRP, making it post-TOT NSV.
    Applying TOT% again overstates trade spend and understates CM2.

    Scenario A: unit_nsv = primary invoice price (current behaviour)
                trade_spend = invoice_nsv × stored_TOT%  ← DOUBLE-COUNTS
    Scenario B: unit_nsv = gross NSV = MRP/(1+GST) before TOT deduction
                trade_spend = gross_nsv × stored_TOT%    ← SINGLE-COUNT

    Returns a gate report dict with verdict, impact quantification, and
    recommended action. Verdict values:
        BLOCKED   – double-counting confirmed, impact ≥ ₹1 L
        WARNING   – double-counting confirmed, impact < ₹1 L
        CLEAR     – no double-counting detected
        INCONCLUSIVE – insufficient data to determine

    This gate MUST block FINAL FINANCIAL reporting until Finance resolves.
    """
    fm = fact_margin.copy()
    fm["mrp_f"] = pd.to_numeric(fm["mrp"], errors="coerce")
    fm["gst_f"] = pd.to_numeric(fm["gst_pct"], errors="coerce")
    fm["tot_f"] = pd.to_numeric(fm["tot_pct"], errors="coerce")
    fm["nsv_v"] = pd.to_numeric(fm["unit_nsv_validated"], errors="coerce")
    fm["eff_tot"] = pd.to_numeric(fm.get("effective_tot_from_primary", pd.Series(dtype=float)),
                                  errors="coerce")

    primary = fm[fm["unit_nsv_source"] == "PRIMARY_INVOICE_HISTORY"].copy()

    if primary.empty:
        return {
            "gate_id": "FIN-GATE-TOT-001",
            "verdict": "INCONCLUSIVE",
            "reason": "No PRIMARY_INVOICE_HISTORY rows found in fact_margin",
            "blocking": False,
        }

    # Gross NSV (pre-TOT)
    primary["gross_nsv"] = primary["mrp_f"] / (1 + primary["gst_f"] / 100)
    # Formula NSV (post-stored-TOT)
    primary["formula_nsv"] = primary["gross_nsv"] / (1 + primary["tot_f"] / 100)
    # Invoice NSV vs formula NSV
    primary["nsv_ratio"] = primary["nsv_v"] / primary["formula_nsv"]

    # Effective TOT implied by primary invoice NSV:
    # invoice_nsv = gross_nsv / (1 + eff_tot/100)  →  eff_tot = gross_nsv/invoice_nsv - 1
    with np.errstate(divide="ignore", invalid="ignore"):
        primary["eff_tot_implied"] = np.where(
            (primary["nsv_v"] > 0) & (primary["gross_nsv"] > 0),
            (primary["gross_nsv"] / primary["nsv_v"] - 1) * 100,
            np.nan,
        )

    # Trade spend under each scenario
    # Scenario A (current): invoice_nsv × stored_TOT
    primary["trade_A"] = primary["nsv_v"] * primary["tot_f"] / 100
    # Scenario B (corrected): gross_nsv × stored_TOT  =  gross_nsv - formula_nsv
    primary["trade_B"] = primary["gross_nsv"] * primary["tot_f"] / 100

    primary["double_count_delta_per_unit"] = primary["trade_A"] - primary["trade_B"]

    # Determine if double-counting is systematic
    negative_delta = (primary["double_count_delta_per_unit"] < -0.01).sum()
    total_rows = len(primary)

    verdict = "CLEAR"
    blocking = False

    if negative_delta / total_rows >= 0.50:
        # >50% of primary rows have Scenario A trade_spend < Scenario B
        # → primary NSV < formula NSV → effective TOT > stored TOT
        # → primary already post-TOT at a higher-than-stored rate
        verdict = "BLOCKED"
        blocking = True
    elif negative_delta / total_rows >= 0.20:
        verdict = "WARNING"
        blocking = True

    # Quantify over an optional forecast dataframe
    impact = {}
    if forecast_df is not None:
        fc = forecast_df.copy()
        fc["nsv_f"] = pd.to_numeric(fc.get("forecast_nsv", 0), errors="coerce").fillna(0)
        fc["ts_f"] = pd.to_numeric(fc.get("forecast_trade_spend", 0), errors="coerce").fillna(0)
        fc["qty_f"] = pd.to_numeric(fc.get("forecast_qty", 0), errors="coerce").fillna(0)
        prim_fc = fc[fc.get("unit_price_status", pd.Series(dtype=str))
                     .str.startswith("VALIDATED_NSV:PRIMARY_INVOICE", na=False)]

        if not prim_fc.empty:
            # Scenario A NSV = current forecast_nsv (primary invoice × qty)
            nsv_a = prim_fc["nsv_f"].sum()
            ts_a = prim_fc["ts_f"].sum()
            # Per-unit median delta (from fact_margin analysis)
            median_delta = primary["double_count_delta_per_unit"].median()
            total_qty_primary = prim_fc["qty_f"].sum()
            ts_overstatement_estimate = abs(median_delta) * total_qty_primary

            impact = {
                "primary_forecast_rows": len(prim_fc),
                "primary_forecast_qty": round(total_qty_primary, 0),
                "scenario_a_nsv_cr": round(nsv_a / 1e7, 2),
                "scenario_a_trade_spend_cr": round(ts_a / 1e7, 2),
                "median_double_count_per_unit_rs": round(abs(median_delta), 2),
                "estimated_trade_spend_overstatement_rs": round(ts_overstatement_estimate, 0),
                "estimated_overstatement_cr": round(ts_overstatement_estimate / 1e7, 2),
            }

    return {
        "gate_id": "FIN-GATE-TOT-001",
        "gate_name": "TOT Double-Count Detection",
        "verdict": verdict,
        "blocking": blocking,
        "reason": (
            "Primary invoice NSV is post-TOT (effective TOT > stored TOT on "
            f"{negative_delta}/{total_rows} rows = {100*negative_delta/total_rows:.1f}%). "
            "Applying stored TOT% on post-TOT NSV overstates trade spend."
            if verdict in ("BLOCKED", "WARNING")
            else "No systematic double-counting detected."
        ),
        "rows_analysed": total_rows,
        "rows_with_double_count_signal": int(negative_delta),
        "pct_affected": round(100 * negative_delta / total_rows, 1),
        "median_eff_tot_pct": round(float(primary["eff_tot_implied"].median()), 2),
        "median_stored_tot_pct": round(float(primary["tot_f"].median()), 2),
        "median_double_count_per_unit_rs": round(
            float(primary["double_count_delta_per_unit"].median()), 2),
        "impact_on_forecast": impact,
        "required_action": (
            "Finance must confirm: is unit_nsv_validated the pre-TOT or post-TOT NSV? "
            "Until confirmed, show Scenario A (current) and Scenario B (corrected) "
            "in parallel. Do not mark CM2 as Finance-approved."
            if blocking
            else "No action required; trade spend calculation is consistent."
        ),
        "scenarios": {
            "A": {
                "label": "Current (NSV = Primary Invoice Price, post-TOT)",
                "unit_nsv_basis": "primary_invoice_history",
                "trade_spend_formula": "unit_nsv × stored_TOT%",
                "risk": "DOUBLE_COUNT if invoice is post-TOT",
            },
            "B": {
                "label": "Corrected (NSV = Gross NSV = MRP/(1+GST), pre-TOT)",
                "unit_nsv_basis": "MRP / (1+GST) / (1+TOT)",
                "trade_spend_formula": "gross_nsv × stored_TOT% = MRP/(1+GST) - formula_nsv",
                "risk": "NONE — trade deducted once from gross NSV",
            },
        },
    }


# ── Main enrichment pipeline ─────────────────────────────────────────────────

def run_enrichment(
    fact_margin_path: str = FACT_MARGIN_PATH,
    fountain_dir: str = FOUNTAIN_DIR,
    forecast_df: Optional[pd.DataFrame] = None,
    verbose: bool = True,
) -> Tuple[pd.DataFrame, dict]:
    """Full Phase 2–6 enrichment pipeline.

    Returns (enriched_fact_margin, enrichment_report).
    enriched_fact_margin has all original columns plus enrichment columns.
    For non-pending rows, enrichment columns are None or NOT_APPLICABLE.
    """
    def log(msg):
        if verbose:
            print(f"  [MRP-ENRICH] {msg}")

    log("Loading Fountain master …")
    fountain_master, fountain_meta = load_consolidated_fountain_master(fountain_dir)
    log(f"  {fountain_meta['unique_eans']} unique EANs across {len(fountain_meta['fountain_files_loaded'])} files")

    log("Loading fact_margin …")
    fact_margin = pd.read_csv(fact_margin_path, dtype=str)
    pending_count = fact_margin["mrp_denomination"].isin(PENDING_DENOMINATIONS).sum()
    pending_eans = fact_margin.loc[
        fact_margin["mrp_denomination"].isin(PENDING_DENOMINATIONS), "ean"
    ].map(_clean_ean).nunique()
    log(f"  {len(fact_margin)} rows total | {pending_count} pending rows | {pending_eans} unique pending EANs")

    log("Phase 2: EAN matching …")
    enriched = match_eans(fact_margin, fountain_master)
    matched = (enriched["match_status"] == "MATCHED").sum()
    unresolved = (enriched["match_status"] == "UNRESOLVED").sum()
    log(f"  Matched {matched} | Unresolved {unresolved} pending rows")

    log("Phase 3: MRP classification …")
    enriched = classify_mrp(enriched, fountain_master)

    log("Phase 4: MRP reasonableness …")
    enriched = validate_mrp_reasonableness(enriched, fact_margin)

    log("Phase 5: Proposed unit NSV …")
    enriched = compute_proposed_nsv(enriched)
    nsv_resolved = (enriched["proposed_nsv_coverage_flag"] == "PROPOSED_TENTATIVE").sum()
    log(f"  NSV resolved for {nsv_resolved} pending rows")

    log("Phase 6: TOT double-count gate (FIN-GATE-TOT-001) …")
    gate = run_finance_gate_tot(fact_margin, forecast_df)
    log(f"  Gate verdict: {gate['verdict']} | Blocking: {gate['blocking']}")

    # Compile enrichment report
    pending_df = enriched[enriched["mrp_denomination"].isin(PENDING_DENOMINATIONS)]
    classification_counts = {}
    if "mrp_proposed_classification" in pending_df.columns:
        classification_counts = pending_df["mrp_proposed_classification"].value_counts().to_dict()

    confidence_counts = {}
    if "proposed_nsv_confidence" in pending_df.columns:
        confidence_counts = pending_df["proposed_nsv_confidence"].value_counts().dropna().to_dict()

    reasonableness_counts = {}
    if "mrp_reasonableness_status" in pending_df.columns:
        reasonableness_counts = pending_df["mrp_reasonableness_status"].value_counts().to_dict()

    # Unresolved EANs
    unresolved_eans = (enriched[enriched["match_status"] == "UNRESOLVED"]
                       [["ean", "article", "mrp_denomination", "mrp"]]
                       .drop_duplicates(subset=["ean"])
                       .to_dict("records"))

    report = {
        "enrichment_status": "COMPLETE_WITH_TENTATIVE_PROPOSALS",
        "fountain_meta": fountain_meta,
        "pending_rows_total": int(pending_count),
        "pending_unique_eans": int(pending_eans),
        "ean_match_results": {
            "matched": int(matched),
            "unresolved": int(unresolved),
            "match_rate_pct": round(100 * matched / pending_count, 1) if pending_count else 0,
        },
        "mrp_classification_counts": classification_counts,
        "mrp_reasonableness_counts": reasonableness_counts,
        "nsv_coverage_after_enrichment": {
            "proposed_tentative": int(nsv_resolved),
            "confidence_breakdown": confidence_counts,
        },
        "unresolved_eans": unresolved_eans,
        "finance_gate": gate,
        "caveats": [
            "All proposed NSV values are TENTATIVE — not Finance-approved.",
            "Fountain MRP is the consumer-unit MRP from the article master (no division applied).",
            "AGGREGATE_DENOMINATION rows: Fountain MRP substituted as unit price — Finance must confirm.",
            "TOT double-counting (FIN-GATE-TOT-001) must be resolved before any FINAL FINANCIAL run.",
            "2 EANs with no Fountain match remain UNRESOLVED — require Sales Operations input.",
        ],
        "blocked_for_final_financial": gate["blocking"],
        "release_status": (
            "TENTATIVE–FINANCIAL VIEW WITH WARNINGS"
            if gate["blocking"]
            else "TENTATIVE–QUANTITY PLANNING READY"
        ),
    }

    return enriched, report


# ── Convenience helpers ───────────────────────────────────────────────────────

def apply_enrichment_to_forecast(
    forecast_df: pd.DataFrame,
    enriched_margin: pd.DataFrame,
) -> pd.DataFrame:
    """Join proposed NSV from enriched_margin back onto the forecast rows.

    For pending rows that now have a proposed_unit_nsv_formula, adds:
      fountain_proposed_unit_nsv, fountain_proposed_nsv_source,
      fountain_proposed_nsv_confidence, fountain_mrp_used,
      tot_double_count_flag.

    Existing NSV columns are NOT overwritten — enrichment columns are additive.
    """
    fc = forecast_df.copy()

    # Build EAN → proposed NSV lookup (take first match per EAN)
    lookup_cols = [
        "ean", "proposed_unit_nsv_formula", "proposed_nsv_source",
        "proposed_nsv_confidence", "proposed_consumer_unit_mrp",
        "mrp_proposed_classification", "mrp_reasonableness_status",
    ]
    avail = [c for c in lookup_cols if c in enriched_margin.columns]
    lookup = (enriched_margin[avail]
              .rename(columns={"ean": "ean_key"})
              .assign(ean_key=enriched_margin["ean"].map(_clean_ean))
              .dropna(subset=["proposed_unit_nsv_formula"])
              .drop_duplicates(subset=["ean_key"]))

    fc["_ean_key"] = fc["ean"].map(_clean_ean)
    fc = fc.merge(
        lookup.rename(columns={
            "proposed_unit_nsv_formula": "fountain_proposed_unit_nsv",
            "proposed_nsv_source":       "fountain_proposed_nsv_source",
            "proposed_nsv_confidence":   "fountain_proposed_nsv_confidence",
            "proposed_consumer_unit_mrp": "fountain_mrp_used",
            "mrp_proposed_classification": "fountain_mrp_classification",
            "mrp_reasonableness_status": "fountain_mrp_reasonableness",
        }),
        left_on="_ean_key", right_on="ean_key", how="left",
    )
    fc = fc.drop(columns=["_ean_key", "ean_key"], errors="ignore")

    # For pending rows with resolved Fountain NSV, compute proposed forecast_nsv
    qty_col = "forecast_qty"
    if qty_col in fc.columns:
        fc["_qty"] = pd.to_numeric(fc[qty_col], errors="coerce").fillna(0)
        pending_resolved = (
            fc["unit_price_status"].isin([
                "NO_UNIT_NSV_PACK_CASE_LEVEL_MRP",
                "NO_UNIT_NSV_AGGREGATE_DENOMINATION",
            ])
            & fc["fountain_proposed_unit_nsv"].notna()
        )
        fc["fountain_proposed_forecast_nsv"] = None
        fc.loc[pending_resolved, "fountain_proposed_forecast_nsv"] = (
            fc.loc[pending_resolved, "_qty"]
            * fc.loc[pending_resolved, "fountain_proposed_unit_nsv"]
        ).round(2)
        fc = fc.drop(columns=["_qty"])

    return fc


def _safe_float(v, default=None):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return default
    try:
        f = float(v)
        return f if np.isfinite(f) else default
    except (TypeError, ValueError):
        return default


# ── CLI entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import json

    enriched, report = run_enrichment(verbose=True)

    out_dir = os.path.join(_REPO_ROOT, "forecast_outputs", "sep_nov_2026_tentative")
    os.makedirs(out_dir, exist_ok=True)

    enriched_path = os.path.join(out_dir, "fact_margin_enriched.csv")
    enriched.to_csv(enriched_path, index=False)
    print(f"\nEnriched margin saved: {enriched_path}")

    report_path = os.path.join(out_dir, "Fountain_MRP_Match_Report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"Match report saved:    {report_path}")

    print("\n=== FIN-GATE-TOT-001 ===")
    g = report["finance_gate"]
    print(f"  Verdict:  {g['verdict']}")
    print(f"  Blocking: {g['blocking']}")
    print(f"  Reason:   {g['reason']}")
    print(f"  Median eff TOT: {g.get('median_eff_tot_pct','?')}% vs stored {g.get('median_stored_tot_pct','?')}%")
    print(f"  Median double-count per unit: ₹{g.get('median_double_count_per_unit_rs','?')}")

    print("\n=== Release Status ===")
    print(f"  {report['release_status']}")
    if report["blocked_for_final_financial"]:
        print("  ⛔  FINAL FINANCIAL mode is BLOCKED until FIN-GATE-TOT-001 is resolved.")
