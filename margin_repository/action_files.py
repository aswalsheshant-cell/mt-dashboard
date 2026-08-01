# -*- coding: utf-8 -*-
"""Generate the four focused action files for MDM/Finance/Commercial/Sales Ops.

Each file has exactly the columns the receiving team needs, plus an owner
header, priority ranking, and empty response columns for them to fill in.
"""
import os
import datetime as dt
import pandas as pd


def _clean_ean(v):
    s = str(v).strip()
    return s[:-2] if s.endswith(".0") else s


def new_ean_creation_file(dms_df, fountain_master, out_path=None, effective_from=None):
    """File 1 (109 records): EANs in DMS not in Fountain master.

    Columns: EAN, SAP Code, Product Name, Brand, Category, Sub Category,
             Range, Pack Size, MRP, Status, Priority
    Owner: Master Data Team
    """
    dms_df = dms_df.copy()
    dms_df["_ean"] = dms_df["EAN"].map(_clean_ean)
    fm_eans = set(fountain_master["EAN"].map(_clean_ean))
    missing = dms_df[~dms_df["_ean"].isin(fm_eans)].copy()

    missing = missing.drop_duplicates(subset=["_ean"], keep="first")

    out = pd.DataFrame({
        "EAN":              missing["_ean"].values,
        "SAP Code":         missing.get("SKU Code", "").values,
        "Product Name":     missing.get("Article", "").values,
        "Brand":            missing.get("Brand", "").values,
        "Category":         missing.get("Category", "").values,
        "Sub Category":     missing.get("Sub Category", "").values,
        "Range":            "",
        "Pack Size":        "",
        "MRP":              missing.get("MRP", "").values,
        "Status":           "ACTIVE",
        "Priority":         "",
        "MDM Response":     "",
        "Resolved On":      "",
    })
    out["Priority"] = out["Brand"].apply(
        lambda b: "P1" if str(b).lower() in ("mamaearth", "the derma co.") else "P2"
    )
    out = out.sort_values(["Priority", "Brand", "Product Name"]).reset_index(drop=True)

    if out_path:
        _write_action_file(
            out, out_path,
            owner_team="Master Data Team",
            purpose="Create master records for EANs missing from Fountain",
            record_count=len(out),
        )
    return out


def gst_upload_file(validated_df, out_path=None, effective_from=None,
                    default_gst=18, category_gst_map=None):
    """File 2 (534 records): every unique EAN needs a GST rate confirmed.

    Columns: EAN, Product Name, Category, Suggested GST %, GST %,
             Effective From, Effective To
    Owner: Finance / Tax Team
    """
    effective_from = effective_from or dt.date.today().replace(day=1).isoformat()
    category_gst_map = category_gst_map or {}

    v = validated_df.copy()
    v["_ean"] = v["EAN"].map(_clean_ean)
    uniq = v.drop_duplicates(subset=["_ean"], keep="first")

    def suggest(cat):
        c = str(cat).strip().lower()
        for k, val in category_gst_map.items():
            if k.lower() in c:
                return val
        return default_gst

    out = pd.DataFrame({
        "EAN":              uniq["_ean"].values,
        "Product Name":     uniq.get("Article", "").values,
        "Category":         uniq.get("Category", "").values,
        "Brand":            uniq.get("Brand", "").values,
        "Suggested GST %":  [suggest(c) for c in uniq.get("Category", "").values],
        "GST %":            "",
        "Effective From":   effective_from,
        "Effective To":     "",
        "Finance Response": "",
        "Resolved On":      "",
    })
    out = out.sort_values(["Category", "Brand", "Product Name"]).reset_index(drop=True)

    if out_path:
        _write_action_file(
            out, out_path,
            owner_team="Finance / Tax Team",
            purpose="Confirm GST rate per EAN (suggested = 18% for personal care)",
            record_count=len(out),
        )
    return out


def margin_conflict_file(dms_df_raw, out_path=None):
    """File 3 (15 records): Chain+EAN with different effective margins by distributor.

    Columns: Chain, Distributor, EAN, Product Name, Current Trade Margin,
             Current Additional, Current Final Margin, Recommended Margin,
             Decision, Approved By
    Owner: Commercial Finance
    """
    df = dms_df_raw.copy()
    df["_ean"] = df["EAN"].map(_clean_ean)
    df["_fem"] = pd.to_numeric(df["Final Effective Margin %"], errors="coerce")
    df["_key"] = df["Chain"].astype(str).str.strip() + "|" + df["_ean"]

    grp = df.groupby("_key")["_fem"].nunique()
    conflict_keys = set(grp[grp > 1].index)
    conflicts = df[df["_key"].isin(conflict_keys)].copy()

    out = pd.DataFrame({
        "Chain":                    conflicts["Chain"].values,
        "Distributor":              conflicts.get("Distributor", "").values,
        "EAN":                      conflicts["_ean"].values,
        "Product Name":             conflicts.get("Article", "").values,
        "Current Trade Margin %":   pd.to_numeric(conflicts["Trade Margin %"], errors="coerce").values,
        "Current Additional %":     pd.to_numeric(conflicts["Additional Discount %"], errors="coerce").values,
        "Current Final Margin %":   conflicts["_fem"].values,
        "Recommended Margin %":     "",
        "Decision":                 "",
        "Approved By":              "",
        "Approved On":              "",
    })
    out = out.sort_values(["Chain", "EAN", "Distributor"]).reset_index(drop=True)

    if out_path:
        _write_action_file(
            out, out_path,
            owner_team="Commercial Finance",
            purpose="Reconcile margin conflicts across distributors (same Chain+EAN)",
            record_count=len(out),
        )
    return out


def missing_mrp_file(validated_df, out_path=None):
    """File 4 (2 records): EANs with missing MRP.

    Columns: SAP Code, EAN, Product, Chain, MRP, Sales Ops Response
    Owner: Sales Operations
    """
    v = validated_df.copy()
    v["_ean"] = v["EAN"].map(_clean_ean)
    blank_mrp = v[v["Validation_Flags"].str.contains("BLANK_MRP", na=False)]

    out = pd.DataFrame({
        "SAP Code":            blank_mrp.get("SKU Code", "").values,
        "EAN":                 blank_mrp["_ean"].values,
        "Product":             blank_mrp.get("Article", "").values,
        "Chain":               blank_mrp.get("Chain", "").values,
        "MRP":                 "",
        "Sales Ops Response":  "",
        "Resolved On":         "",
    })
    out = out.sort_values(["Chain", "EAN"]).reset_index(drop=True)

    if out_path:
        _write_action_file(
            out, out_path,
            owner_team="Sales Operations",
            purpose="Supply missing MRP values",
            record_count=len(out),
        )
    return out


def _write_action_file(df, path, owner_team, purpose, record_count):
    """Write a two-sheet Excel: Instructions + Data."""
    inst = pd.DataFrame({
        "Field": [
            "Action File",
            "Owner Team",
            "Purpose",
            "Records",
            "Generated On",
            "How to Complete",
            "Return To",
        ],
        "Value": [
            os.path.basename(path),
            owner_team,
            purpose,
            record_count,
            dt.date.today().isoformat(),
            "Fill the empty response columns and return this file. "
            "Do not modify EAN or the reference columns.",
            "Modern Trade — Margin Repository",
        ],
    })
    with pd.ExcelWriter(path, engine="openpyxl") as w:
        inst.to_excel(w, sheet_name="Instructions", index=False)
        df.to_excel(w, sheet_name="Records", index=False)


def generate_all_action_files(dms_df_raw, dms_df_dedup, validated_df,
                              fountain_master, out_dir):
    """Generate all 4 action files. Returns a dict of file → row count."""
    os.makedirs(out_dir, exist_ok=True)
    counts = {}

    p1 = os.path.join(out_dir, "01_New_EAN_Creation.xlsx")
    df1 = new_ean_creation_file(dms_df_dedup, fountain_master, out_path=p1)
    counts[p1] = len(df1)

    p2 = os.path.join(out_dir, "02_GST_Upload.xlsx")
    df2 = gst_upload_file(validated_df, out_path=p2)
    counts[p2] = len(df2)

    p3 = os.path.join(out_dir, "03_Margin_Conflict.xlsx")
    df3 = margin_conflict_file(dms_df_raw, out_path=p3)
    counts[p3] = len(df3)

    p4 = os.path.join(out_dir, "04_Missing_MRP.xlsx")
    df4 = missing_mrp_file(validated_df, out_path=p4)
    counts[p4] = len(df4)

    return counts
