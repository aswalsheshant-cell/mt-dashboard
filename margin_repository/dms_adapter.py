# -*- coding: utf-8 -*-
"""DMS-to-Repository ingestion adapter.

Maps DMS "DB Margin-Updated" columns to the canonical margin repository
schema, converting decimal margins (0.35) to percentage (35.0).
"""
import pandas as pd
from schema import REPO_COLS, HEADER_ALIASES, canon_header


DMS_COLUMN_MAP = {
    "Chain": "Chain",
    "EAN": "EAN",
    "Product Name": "Article",
    "MRP": "MRP",
    "Brand": "Brand",
    "Cat": "Category",
    "Sub_category": "Sub Category",
    "TOT margin": "Trade Margin %",
    "Additional Margin": "Additional Discount %",
    "Final Margin to be uploaded": "Final Effective Margin %",
    "Sap Code": "SKU Code",
    "Customer Name": "Distributor",
    "DC/DSD": "Supply Source",
    "Remarks": "_DMS_Remarks",
}

DECIMAL_TO_PCT_COLS = ["Trade Margin %", "Additional Discount %", "Final Effective Margin %"]


def load_dms(path, sheet="DB Margin-Updated ", deduplicate=True):
    """Read DMS file and return (mapped_df, meta_dict)."""
    raw = pd.read_excel(path, sheet_name=sheet, dtype=str)
    raw = raw.dropna(how="all")
    raw = raw[~raw.apply(lambda r: all(str(x).strip() == "" for x in r), axis=1)]

    out = pd.DataFrame(index=raw.index)
    mapped_cols = []
    unmapped_cols = []

    for src_col in raw.columns:
        target = DMS_COLUMN_MAP.get(src_col)
        if target is None:
            target = canon_header(src_col)
            if target not in REPO_COLS:
                unmapped_cols.append(src_col)
                continue
        mapped_cols.append(src_col)
        out[target] = raw[src_col]

    for c in REPO_COLS:
        if c not in out.columns:
            out[c] = ""

    for c in DECIMAL_TO_PCT_COLS:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce").apply(
                lambda v: str(round(v * 100, 4)) if pd.notna(v) else ""
            )

    _derive_tot_pct(out)

    out = out.reindex(columns=[c for c in REPO_COLS if c in out.columns] +
                      [c for c in out.columns if c not in REPO_COLS])
    out = out.reset_index(drop=True)

    if deduplicate:
        out, dedup_meta = _deduplicate_by_chain_ean(out)
        meta_extra = dedup_meta
    else:
        meta_extra = {}

    meta = {
        "source_sheet": sheet.strip(),
        "rows": len(out),
        "rows_before_dedup": len(raw) if deduplicate else len(out),
        "mapped_cols": mapped_cols,
        "unmapped_cols": unmapped_cols,
        "decimal_to_pct_converted": DECIMAL_TO_PCT_COLS,
        "missing_repo_fields": [c for c in ["Pack Size", "GST %", "Effective From"]
                                if out[c].eq("").all() or out[c].isna().all()],
    }
    meta.update(meta_extra)
    return out, meta


def _deduplicate_by_chain_ean(df):
    """Collapse distributor-level DMS rows to one article per Chain+EAN.

    The DMS file has one row per distributor per article. The margin
    repository needs one row per Chain+EAN. Strategy:
    - Group by Chain + EAN
    - Keep the row with the MAX Final Effective Margin % (most conservative
      for business review — surfaces the highest obligation)
    - Preserve distributor names and count as metadata columns
    """
    df = df.copy()
    df["_fem_num"] = pd.to_numeric(df["Final Effective Margin %"], errors="coerce")
    df["_chain_ean"] = df["Chain"].astype(str).str.strip() + "|" + df["EAN"].astype(str).str.strip()

    groups = df.groupby("_chain_ean", sort=False)
    keep_idx = groups["_fem_num"].idxmax()
    deduped = df.loc[keep_idx].copy()

    dist_count = groups["Distributor"].nunique()
    dist_names = groups["Distributor"].apply(lambda s: "; ".join(s.dropna().unique()))
    deduped["_Distributor_Count"] = deduped["_chain_ean"].map(dist_count)
    deduped["_All_Distributors"] = deduped["_chain_ean"].map(dist_names)

    margin_varies = groups["_fem_num"].nunique()
    varies_keys = set(margin_varies[margin_varies > 1].index)
    deduped["_Margin_Varies_By_Distributor"] = deduped["_chain_ean"].isin(varies_keys).map(
        {True: "YES", False: "NO"}
    )

    deduped = deduped.drop(columns=["_fem_num", "_chain_ean"]).reset_index(drop=True)

    meta = {
        "dedup_strategy": "max_effective_margin_per_chain_ean",
        "unique_chain_ean": len(keep_idx),
        "margin_varies_by_distributor": len(varies_keys),
        "total_distributors": int(df["Distributor"].nunique()),
    }
    return deduped, meta


def _derive_tot_pct(df):
    """Derive TOT % = Final Effective Margin % - Trade Margin % - Additional Discount % when blank."""
    fem = pd.to_numeric(df.get("Final Effective Margin %"), errors="coerce")
    tm = pd.to_numeric(df.get("Trade Margin %"), errors="coerce").fillna(0)
    add = pd.to_numeric(df.get("Additional Discount %"), errors="coerce").fillna(0)
    tot = pd.to_numeric(df.get("TOT %"), errors="coerce")
    derived = fem - tm - add
    mask = tot.isna() | (df["TOT %"].astype(str).str.strip() == "")
    positive = derived.clip(lower=0)
    df.loc[mask, "TOT %"] = positive[mask].round(4).apply(
        lambda v: str(v) if pd.notna(v) else ""
    )


def dms_quality_preview(path, sheet="DB Margin-Updated "):
    """Run full ingestion + validation on a DMS file and return results."""
    from validation import validate_frame, qc_report

    df, meta = load_dms(path, sheet)
    validated = validate_frame(df)
    qc = qc_report(validated)
    return validated, qc, meta


def dms_enriched_preview(path, sheet="DB Margin-Updated ", fountain_master=None):
    """Full DMS -> Fountain enrichment -> validation pipeline.
    Returns (enriched_validated_df, qc_report_df, ingest_meta, enrich_report).
    """
    from validation import validate_frame, qc_report
    from fountain_enricher import enrich

    df, ingest_meta = load_dms(path, sheet)
    enriched, enrich_report = enrich(df, fountain_master=fountain_master)
    validated = validate_frame(enriched)
    qc = qc_report(validated)
    return validated, qc, ingest_meta, enrich_report
