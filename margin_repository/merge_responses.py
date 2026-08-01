# -*- coding: utf-8 -*-
"""Merge completed business-team action files back into the pipeline.

Two tiers:
  A. Persistent master updates  → written to Masters/ (auto-apply on every future import)
       - 01_New_EAN_Creation → Masters/Article_Master_Extension.csv
       - 02_GST_Upload       → Masters/GST_Master.csv
  B. Transactional overrides    → applied to the current DMS dataframe only
       - 03_Margin_Conflict   → override Final Effective Margin per Chain+EAN+Distributor
       - 04_Missing_MRP       → fill MRP per EAN

Every applied change is logged (old, new, approver, timestamp) in an audit trail.
"""
import os
import datetime as dt
import pandas as pd


MASTERS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Masters")
AUDIT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Merge_Audit_Trail.csv")


def _clean_ean(v):
    if pd.isna(v):
        return ""
    s = str(v).strip()
    return s[:-2] if s.endswith(".0") else s


def _now():
    return dt.datetime.now().isoformat(timespec="seconds")


def _load_response_sheet(path, sheet="Records"):
    try:
        return pd.read_excel(path, sheet_name=sheet, dtype=str).fillna("")
    except (FileNotFoundError, ValueError):
        return pd.DataFrame()


def _has_value(v):
    return v is not None and str(v).strip() != ""


def apply_new_ean_master(action_file_path, masters_dir=MASTERS_DIR):
    """Type 1: append new EANs to Article_Master_Extension.csv."""
    df = _load_response_sheet(action_file_path)
    if df.empty:
        return {"file": os.path.basename(action_file_path), "applied": 0, "audit": []}

    completed = df[
        df.get("MDM Response", "").astype(str).str.strip().str.upper().eq("APPROVED") |
        df.get("Pack Size", "").astype(str).str.strip().ne("")
    ].copy()
    if completed.empty:
        return {"file": os.path.basename(action_file_path), "applied": 0, "audit": []}

    os.makedirs(masters_dir, exist_ok=True)
    master_path = os.path.join(masters_dir, "Article_Master_Extension.csv")
    existing = pd.read_csv(master_path, dtype=str) if os.path.exists(master_path) else pd.DataFrame()

    completed["EAN"] = completed["EAN"].map(_clean_ean)
    if not existing.empty:
        existing["EAN"] = existing["EAN"].map(_clean_ean)
        already = set(existing["EAN"])
        new_rows = completed[~completed["EAN"].isin(already)]
    else:
        new_rows = completed

    keep_cols = ["EAN", "SAP Code", "Product Name", "Brand", "Category",
                 "Sub Category", "Range", "Pack Size", "MRP", "Status"]
    new_rows = new_rows[[c for c in keep_cols if c in new_rows.columns]].copy()
    new_rows["Approved_On"] = _now()

    combined = pd.concat([existing, new_rows], ignore_index=True) if not existing.empty else new_rows
    combined.to_csv(master_path, index=False)

    audit = [{"timestamp": _now(), "action": "NEW_EAN_MASTER",
              "ean": r["EAN"], "field": "master_record",
              "old_value": "", "new_value": "created",
              "source_file": os.path.basename(action_file_path),
              "approver": "MDM"} for _, r in new_rows.iterrows()]
    return {"file": os.path.basename(action_file_path), "applied": len(new_rows),
            "master_path": master_path, "audit": audit}


def apply_gst_master(action_file_path, masters_dir=MASTERS_DIR):
    """Type 2: append GST rates to GST_Master.csv."""
    df = _load_response_sheet(action_file_path)
    if df.empty:
        return {"file": os.path.basename(action_file_path), "applied": 0, "audit": []}

    gst_col = "GST %"
    completed = df[df.get(gst_col, "").astype(str).str.strip().ne("")].copy()
    if completed.empty:
        return {"file": os.path.basename(action_file_path), "applied": 0, "audit": []}

    os.makedirs(masters_dir, exist_ok=True)
    master_path = os.path.join(masters_dir, "GST_Master.csv")
    existing = pd.read_csv(master_path, dtype=str) if os.path.exists(master_path) else pd.DataFrame()

    completed["EAN"] = completed["EAN"].map(_clean_ean)
    keep = ["EAN", gst_col, "Effective From", "Effective To"]
    updates = completed[[c for c in keep if c in completed.columns]].copy()
    updates = updates.rename(columns={gst_col: "GST_Pct"})
    updates["Approved_On"] = _now()

    audit = []
    if not existing.empty:
        existing["EAN"] = existing["EAN"].map(_clean_ean)
        old_lookup = existing.set_index("EAN")["GST_Pct"].to_dict()
    else:
        old_lookup = {}
    for _, r in updates.iterrows():
        audit.append({"timestamp": _now(), "action": "GST_MASTER",
                      "ean": r["EAN"], "field": "GST_Pct",
                      "old_value": old_lookup.get(r["EAN"], ""),
                      "new_value": r["GST_Pct"],
                      "source_file": os.path.basename(action_file_path),
                      "approver": "Finance"})

    if not existing.empty:
        existing = existing[~existing["EAN"].isin(set(updates["EAN"]))]
        combined = pd.concat([existing, updates], ignore_index=True)
    else:
        combined = updates
    combined.to_csv(master_path, index=False)

    return {"file": os.path.basename(action_file_path), "applied": len(updates),
            "master_path": master_path, "audit": audit}


def apply_margin_overrides(action_file_path, dms_df):
    """Type 3: transactional override of Final Effective Margin for
    Chain+EAN+Distributor combos with an approved Recommended Margin."""
    df = _load_response_sheet(action_file_path)
    if df.empty:
        return dms_df, {"file": os.path.basename(action_file_path), "applied": 0, "audit": []}

    completed = df[df.get("Recommended Margin %", "").astype(str).str.strip().ne("")].copy()
    if completed.empty:
        return dms_df, {"file": os.path.basename(action_file_path), "applied": 0, "audit": []}

    dms = dms_df.copy()
    dms["_ean"] = dms["EAN"].map(_clean_ean)
    audit = []
    applied = 0
    for _, r in completed.iterrows():
        chain = str(r.get("Chain", "")).strip()
        dist = str(r.get("Distributor", "")).strip()
        ean = _clean_ean(r.get("EAN", ""))
        new_margin = str(r.get("Recommended Margin %", "")).strip()
        approver = str(r.get("Approved By", "")).strip() or "Commercial Finance"
        mask = (
            (dms["Chain"].astype(str).str.strip() == chain) &
            (dms["_ean"] == ean)
        )
        if dist:
            mask &= (dms["Distributor"].astype(str).str.strip() == dist)
        matched = mask.sum()
        if matched:
            old_vals = dms.loc[mask, "Final Effective Margin %"].astype(str).unique().tolist()
            dms.loc[mask, "Final Effective Margin %"] = new_margin
            audit.append({"timestamp": _now(), "action": "MARGIN_OVERRIDE",
                          "ean": ean, "chain": chain, "distributor": dist,
                          "field": "Final Effective Margin %",
                          "old_value": "; ".join(old_vals),
                          "new_value": new_margin,
                          "rows_affected": int(matched),
                          "source_file": os.path.basename(action_file_path),
                          "approver": approver})
            applied += int(matched)
    dms = dms.drop(columns=["_ean"])
    return dms, {"file": os.path.basename(action_file_path), "applied": applied, "audit": audit}


def apply_mrp_fills(action_file_path, dms_df):
    """Type 4: transactional fill of missing MRP per EAN."""
    df = _load_response_sheet(action_file_path)
    if df.empty:
        return dms_df, {"file": os.path.basename(action_file_path), "applied": 0, "audit": []}

    completed = df[df.get("MRP", "").astype(str).str.strip().ne("")].copy()
    if completed.empty:
        return dms_df, {"file": os.path.basename(action_file_path), "applied": 0, "audit": []}

    dms = dms_df.copy()
    dms["_ean"] = dms["EAN"].map(_clean_ean)
    audit = []
    applied = 0
    for _, r in completed.iterrows():
        ean = _clean_ean(r.get("EAN", ""))
        new_mrp = str(r.get("MRP", "")).strip()
        chain = str(r.get("Chain", "")).strip()
        mask = (dms["_ean"] == ean) & (
            dms["MRP"].astype(str).str.strip().eq("") | dms["MRP"].isna()
        )
        if chain:
            mask &= (dms["Chain"].astype(str).str.strip() == chain)
        matched = mask.sum()
        if matched:
            dms.loc[mask, "MRP"] = new_mrp
            audit.append({"timestamp": _now(), "action": "MRP_FILL",
                          "ean": ean, "chain": chain,
                          "field": "MRP",
                          "old_value": "",
                          "new_value": new_mrp,
                          "rows_affected": int(matched),
                          "source_file": os.path.basename(action_file_path),
                          "approver": "Sales Operations"})
            applied += int(matched)
    dms = dms.drop(columns=["_ean"])
    return dms, {"file": os.path.basename(action_file_path), "applied": applied, "audit": audit}


def merge_all_responses(action_dir, dms_df, masters_dir=MASTERS_DIR,
                        audit_path=AUDIT_PATH):
    """Read all 4 action files from action_dir, apply master + transactional
    updates, log audit trail, return the updated DMS frame + summary."""
    files = {
        "new_ean":  os.path.join(action_dir, "01_New_EAN_Creation.xlsx"),
        "gst":      os.path.join(action_dir, "02_GST_Upload.xlsx"),
        "margin":   os.path.join(action_dir, "03_Margin_Conflict.xlsx"),
        "mrp":      os.path.join(action_dir, "04_Missing_MRP.xlsx"),
    }
    summary = {}
    all_audit = []

    if os.path.exists(files["new_ean"]):
        r = apply_new_ean_master(files["new_ean"], masters_dir)
        summary["new_ean"] = r
        all_audit.extend(r["audit"])
    if os.path.exists(files["gst"]):
        r = apply_gst_master(files["gst"], masters_dir)
        summary["gst"] = r
        all_audit.extend(r["audit"])
    if os.path.exists(files["margin"]):
        dms_df, r = apply_margin_overrides(files["margin"], dms_df)
        summary["margin"] = r
        all_audit.extend(r["audit"])
    if os.path.exists(files["mrp"]):
        dms_df, r = apply_mrp_fills(files["mrp"], dms_df)
        summary["mrp"] = r
        all_audit.extend(r["audit"])

    if all_audit:
        audit_df = pd.DataFrame(all_audit)
        if os.path.exists(audit_path):
            audit_df = pd.concat([pd.read_csv(audit_path), audit_df], ignore_index=True)
        audit_df.to_csv(audit_path, index=False)
        summary["audit_path"] = audit_path
        summary["audit_rows_written"] = len(all_audit)

    return dms_df, summary


def apply_gst_master_to_frame(dms_df, masters_dir=MASTERS_DIR):
    """Enrichment step: fill blank GST % from the persistent GST_Master.csv."""
    gst_path = os.path.join(masters_dir, "GST_Master.csv")
    if not os.path.exists(gst_path):
        return dms_df, {"filled": 0}
    gst = pd.read_csv(gst_path, dtype=str)
    gst["EAN"] = gst["EAN"].map(_clean_ean)
    lookup = gst.set_index("EAN")["GST_Pct"].to_dict()

    dms = dms_df.copy()
    dms["_ean"] = dms["EAN"].map(_clean_ean)
    blank = dms["GST %"].astype(str).str.strip().eq("") | dms["GST %"].isna()
    fill_mask = blank & dms["_ean"].isin(lookup)
    dms.loc[fill_mask, "GST %"] = dms.loc[fill_mask, "_ean"].map(lookup)
    dms = dms.drop(columns=["_ean"])
    return dms, {"filled": int(fill_mask.sum()), "master_path": gst_path}


def before_after_summary(before_validated, after_validated):
    """Compare QC severity + health before and after response merge."""
    def sev_counts(df):
        s = df["QC_Severity"].value_counts().to_dict()
        return {k: int(s.get(k, 0)) for k in ["PASS", "WARNING", "FAIL", "BLOCKED"]}

    def health(df):
        pub = int((df["Record_Status"] == "PUBLISHED").sum())
        return round(100.0 * pub / len(df), 2) if len(df) else 0.0

    b, a = sev_counts(before_validated), sev_counts(after_validated)
    hb, ha = health(before_validated), health(after_validated)
    rows = [{"Severity": k, "Before": b[k], "After": a[k], "Delta": a[k] - b[k]}
            for k in ["PASS", "WARNING", "FAIL", "BLOCKED"]]
    rows.append({"Severity": "Repository_Health_%", "Before": hb,
                 "After": ha, "Delta": round(ha - hb, 2)})
    return pd.DataFrame(rows)
