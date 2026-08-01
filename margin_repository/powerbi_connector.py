# -*- coding: utf-8 -*-
"""Power BI Connector — clean table export for Power Query refresh.

Generates a clean, flat CSV/Excel that Power BI can refresh directly.
No repository internals exposed — only business-relevant fields with
stable column names that don't break Power Query mappings.
"""
import os
import pandas as pd
from repository import MarginRepository


# Stable column contract for Power BI (never rename without migration)
PBI_COLUMNS = [
    "Chain", "Brand", "Category", "Sub_Category", "Range", "Article",
    "EAN", "SKU_Code", "Pack_Size", "MRP",
    "Trade_Margin_Pct", "TOT_Pct", "Backend_Pct", "Frontend_Pct",
    "Visibility_Pct", "Listing_Support_Pct", "Rental_Support_Pct",
    "Display_Pct", "Scheme_Pct", "Special_Commercial_Pct",
    "Additional_Discount_Pct", "Distributor_Margin_Pct",
    "Consumer_Offer_Pct", "Cash_Discount_Pct",
    "Final_Effective_Margin_Pct", "GST_Pct",
    "Effective_From", "Effective_To", "Version",
    "Status", "Launch_Status", "Risk_Tier", "QC_Severity",
    "Record_Status", "Approval_Status", "Last_Updated",
]

# Map from repository columns to Power BI columns
_COL_MAP = {
    "Chain": "Chain", "Brand": "Brand", "Category": "Category",
    "Sub Category": "Sub_Category", "Range": "Range", "Article": "Article",
    "EAN": "EAN", "SKU Code": "SKU_Code", "Pack Size": "Pack_Size", "MRP": "MRP",
    "Trade Margin %": "Trade_Margin_Pct", "TOT %": "TOT_Pct",
    "Backend %": "Backend_Pct", "Frontend %": "Frontend_Pct",
    "Visibility %": "Visibility_Pct", "Listing Support %": "Listing_Support_Pct",
    "Rental Support %": "Rental_Support_Pct", "Display %": "Display_Pct",
    "Scheme %": "Scheme_Pct", "Special Commercial %": "Special_Commercial_Pct",
    "Additional Discount %": "Additional_Discount_Pct",
    "Distributor Margin %": "Distributor_Margin_Pct",
    "Consumer Offer %": "Consumer_Offer_Pct", "Cash Discount %": "Cash_Discount_Pct",
    "Final Effective Margin %": "Final_Effective_Margin_Pct", "GST %": "GST_Pct",
    "Effective From": "Effective_From", "Effective To": "Effective_To",
    "Version Number": "Version", "Status": "Status", "Launch Status": "Launch_Status",
    "QC_Severity": "QC_Severity", "Record_Status": "Record_Status",
    "Approval Status": "Approval_Status", "Last Updated": "Last_Updated",
}


def export_current_approved(repo, output_path, fmt="csv"):
    """Export the current approved (forecast-ready) margin table.

    This is the primary Power BI data source — one row per Chain×Article
    with the latest approved margin.
    """
    cur = repo.current(include_held=False)
    df = _transform(cur)
    return _write(df, output_path, fmt, "Current_Approved_Margin")


def export_full_history(repo, output_path, fmt="csv"):
    """Export full version history for Power BI trend analysis."""
    hist = repo.history.copy()
    hist_cols = list(_COL_MAP.keys()) + ["Article_Key", "Change_Type",
                                          "Import_Batch_Id", "Import_Timestamp"]
    hist_pbi = {
        **_COL_MAP,
        "Article_Key": "Article_Key",
        "Change_Type": "Change_Type",
        "Import_Batch_Id": "Import_Batch",
        "Import_Timestamp": "Import_Timestamp",
    }
    df = _transform(hist, col_map=hist_pbi)
    return _write(df, output_path, fmt, "Version_History")


def export_margin_summary(repo, output_path, fmt="csv"):
    """Export chain-wise margin summary for Power BI dashboard tiles."""
    cur = repo.current(include_held=False)
    if cur.empty:
        df = pd.DataFrame(columns=["Chain", "Articles", "Avg_Trade_Margin_Pct",
                                    "Avg_Final_Margin_Pct", "Min_Margin_Pct",
                                    "Max_Margin_Pct"])
    else:
        _n = lambda c: pd.to_numeric(cur.get(c), errors="coerce")
        g = cur.groupby("Chain").agg(
            Articles=("Chain", "size"),
            Avg_Trade_Margin_Pct=("Trade Margin %", lambda x: _n(x).mean()),
            Avg_Final_Margin_Pct=("Final Effective Margin %", lambda x: _n(x).mean()),
            Min_Margin_Pct=("Final Effective Margin %", lambda x: _n(x).min()),
            Max_Margin_Pct=("Final Effective Margin %", lambda x: _n(x).max()),
        ).reset_index()
        for c in ["Avg_Trade_Margin_Pct", "Avg_Final_Margin_Pct",
                   "Min_Margin_Pct", "Max_Margin_Pct"]:
            g[c] = g[c].round(2)
        df = g.sort_values("Avg_Final_Margin_Pct", ascending=False)

    return _write(df, output_path, fmt, "Chain_Margin_Summary")


def export_qc_status(repo, output_path, fmt="csv"):
    """Export QC status for Power BI health monitoring."""
    cur = repo.current(include_held=True)
    if cur.empty:
        df = pd.DataFrame(columns=["Chain", "PASS", "WARNING", "FAIL", "BLOCKED",
                                    "Published", "Held", "Health_Pct"])
    else:
        rows = []
        for chain, group in cur.groupby("Chain"):
            sev = group["QC_Severity"].value_counts().to_dict()
            pub = int((group["Record_Status"] == "PUBLISHED").sum())
            total = len(group)
            rows.append({
                "Chain": chain,
                "PASS": sev.get("PASS", 0),
                "WARNING": sev.get("WARNING", 0),
                "FAIL": sev.get("FAIL", 0),
                "BLOCKED": sev.get("BLOCKED", 0),
                "Published": pub,
                "Held": total - pub,
                "Health_Pct": round(100.0 * pub / total, 1) if total else 0,
            })
        df = pd.DataFrame(rows).sort_values("Health_Pct", ascending=False)

    return _write(df, output_path, fmt, "QC_Status")


def refresh_all(repo_root, output_dir, fmt="csv"):
    """Refresh all Power BI connector tables at once."""
    os.makedirs(output_dir, exist_ok=True)
    repo = MarginRepository(repo_root)
    ext = "xlsx" if fmt == "xlsx" else "csv"
    paths = {}
    paths["current"] = export_current_approved(
        repo, os.path.join(output_dir, "PBI_Current_Margin.%s" % ext), fmt)
    paths["history"] = export_full_history(
        repo, os.path.join(output_dir, "PBI_Version_History.%s" % ext), fmt)
    paths["summary"] = export_margin_summary(
        repo, os.path.join(output_dir, "PBI_Chain_Summary.%s" % ext), fmt)
    paths["qc"] = export_qc_status(
        repo, os.path.join(output_dir, "PBI_QC_Status.%s" % ext), fmt)
    return paths


def _transform(df, col_map=None):
    """Rename repository columns to stable Power BI names."""
    col_map = col_map or _COL_MAP
    if df.empty:
        return pd.DataFrame(columns=list(col_map.values()))
    rename = {k: v for k, v in col_map.items() if k in df.columns}
    out = df.rename(columns=rename)
    return out[[c for c in col_map.values() if c in out.columns]]


def _write(df, path, fmt, sheet_name="Data"):
    if fmt == "xlsx":
        df.to_excel(path, index=False, sheet_name=sheet_name)
    else:
        df.to_csv(path, index=False)
    return path


def generate_power_query_m(csv_folder_path):
    """Generate Power Query M code for connecting to the CSV exports."""
    return '''// Power Query M — Margin Repository Connector
// Point Source to the folder containing PBI_*.csv files

let
    CurrentMargin = Csv.Document(
        File.Contents("%(path)s/PBI_Current_Margin.csv"),
        [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]
    ),
    Promoted = Table.PromoteHeaders(CurrentMargin, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Promoted, {
        {"MRP", type number},
        {"Trade_Margin_Pct", type number},
        {"Final_Effective_Margin_Pct", type number},
        {"GST_Pct", type number},
        {"Version", Int64.Type}
    })
in
    Typed

// Repeat for PBI_Version_History.csv, PBI_Chain_Summary.csv, PBI_QC_Status.csv
// Refresh: Data → Refresh All (or schedule in Power BI Service)
''' % {"path": csv_folder_path}
