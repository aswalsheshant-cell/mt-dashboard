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


def export_star_schema(repo, output_dir, fmt="csv"):
    """Export a proper Power BI star schema (dim + fact tables).

    Fact:  fact_margin (current), fact_margin_history (versioned)
    Dims:  dim_article, dim_chain, dim_brand, dim_category, dim_date
    """
    os.makedirs(output_dir, exist_ok=True)
    ext = "xlsx" if fmt == "xlsx" else "csv"
    cur = repo.current(include_held=True)
    hist = repo.history.copy() if not repo.history.empty else pd.DataFrame()

    paths = {}

    if cur.empty:
        empty = pd.DataFrame()
        for t in ("dim_article", "dim_chain", "dim_brand", "dim_category",
                  "dim_date", "fact_margin", "fact_margin_history"):
            p = os.path.join(output_dir, "%s.%s" % (t, ext))
            _write(empty, p, fmt, t)
            paths[t] = p
        return paths

    # --- dim_article: one row per EAN (dedup) ---
    art_cols = ["EAN", "Article", "SKU Code", "Brand", "Category", "Sub Category",
                "Range", "Pack Size", "MRP", "Launch Status", "Status"]
    dim_art = cur[[c for c in art_cols if c in cur.columns]].copy()
    dim_art = dim_art.drop_duplicates(subset=["EAN"], keep="first")
    dim_art = dim_art.rename(columns={
        "SKU Code": "SKU_Code", "Sub Category": "Sub_Category",
        "Pack Size": "Pack_Size", "Launch Status": "Launch_Status",
    })
    dim_art["Article_Key"] = dim_art["EAN"].astype(str)
    p = os.path.join(output_dir, "dim_article.%s" % ext)
    _write(dim_art, p, fmt, "dim_article")
    paths["dim_article"] = p

    # --- dim_chain ---
    dim_ch = pd.DataFrame({"Chain": sorted(cur["Chain"].dropna().unique())})
    dim_ch["Chain_Key"] = dim_ch["Chain"]
    p = os.path.join(output_dir, "dim_chain.%s" % ext)
    _write(dim_ch, p, fmt, "dim_chain")
    paths["dim_chain"] = p

    # --- dim_brand ---
    dim_br = pd.DataFrame({"Brand": sorted(cur["Brand"].dropna().unique())})
    dim_br["Brand_Key"] = dim_br["Brand"]
    p = os.path.join(output_dir, "dim_brand.%s" % ext)
    _write(dim_br, p, fmt, "dim_brand")
    paths["dim_brand"] = p

    # --- dim_category ---
    dim_cat = cur[[c for c in ["Category", "Sub Category"] if c in cur.columns]].copy()
    dim_cat = dim_cat.drop_duplicates()
    dim_cat = dim_cat.rename(columns={"Sub Category": "Sub_Category"})
    dim_cat["Category_Key"] = dim_cat["Category"].astype(str) + "|" + dim_cat.get("Sub_Category", "").astype(str)
    p = os.path.join(output_dir, "dim_category.%s" % ext)
    _write(dim_cat, p, fmt, "dim_category")
    paths["dim_category"] = p

    # --- dim_date: derived from Effective From ---
    dates = pd.to_datetime(cur.get("Effective From"), errors="coerce").dropna().unique()
    if len(dates):
        dmin, dmax = pd.Timestamp(min(dates)).normalize(), pd.Timestamp(max(dates)).normalize()
        rng = pd.date_range(dmin, dmax, freq="D")
        dim_dt = pd.DataFrame({"Date": rng})
        dim_dt["Date_Key"] = dim_dt["Date"].dt.strftime("%Y-%m-%d")
        dim_dt["Year"] = dim_dt["Date"].dt.year
        dim_dt["Month"] = dim_dt["Date"].dt.month
        dim_dt["Month_Name"] = dim_dt["Date"].dt.strftime("%b")
        dim_dt["Quarter"] = "Q" + dim_dt["Date"].dt.quarter.astype(str)
        dim_dt["FY"] = dim_dt.apply(
            lambda r: "FY%d" % (r["Year"] + 1) if r["Month"] >= 4 else "FY%d" % r["Year"], axis=1
        )
    else:
        dim_dt = pd.DataFrame(columns=["Date", "Date_Key", "Year", "Month",
                                        "Month_Name", "Quarter", "FY"])
    p = os.path.join(output_dir, "dim_date.%s" % ext)
    _write(dim_dt, p, fmt, "dim_date")
    paths["dim_date"] = p

    # --- fact_margin: current approved margins with FK columns ---
    fact = _transform(cur)
    fact["Article_Key"] = fact["EAN"].astype(str)
    fact["Chain_Key"] = fact["Chain"]
    fact["Brand_Key"] = fact["Brand"]
    fact["Category_Key"] = fact["Category"].astype(str) + "|" + fact.get("Sub_Category", "").astype(str)
    fact["Date_Key"] = pd.to_datetime(fact.get("Effective_From"), errors="coerce").dt.strftime("%Y-%m-%d")
    p = os.path.join(output_dir, "fact_margin.%s" % ext)
    _write(fact, p, fmt, "fact_margin")
    paths["fact_margin"] = p

    # --- fact_margin_history: all versions ---
    if not hist.empty:
        hist_pbi = {**_COL_MAP, "Article_Key": "Article_Key",
                    "Change_Type": "Change_Type",
                    "Import_Batch_Id": "Import_Batch",
                    "Import_Timestamp": "Import_Timestamp"}
        fh = _transform(hist, col_map=hist_pbi)
    else:
        fh = pd.DataFrame()
    p = os.path.join(output_dir, "fact_margin_history.%s" % ext)
    _write(fh, p, fmt, "fact_margin_history")
    paths["fact_margin_history"] = p

    dax_path = os.path.join(output_dir, "MEASURES.dax")
    with open(dax_path, "w") as f:
        f.write(dax_measures())
    paths["dax"] = dax_path

    return paths


def dax_measures():
    """Recommended DAX measures for the star schema."""
    return '''// ---------------------------------------------------------------------------
// Margin Repository — DAX Measures
// Place these in a measure table (or on fact_margin) in Power BI.
// ---------------------------------------------------------------------------

Total Articles =
COUNTROWS ( fact_margin )

Unique EANs =
DISTINCTCOUNT ( fact_margin[EAN] )

Avg Trade Margin % =
AVERAGE ( fact_margin[Trade_Margin_Pct] )

Avg Final Margin % =
AVERAGE ( fact_margin[Final_Effective_Margin_Pct] )

Min Final Margin % =
MIN ( fact_margin[Final_Effective_Margin_Pct] )

Max Final Margin % =
MAX ( fact_margin[Final_Effective_Margin_Pct] )

Repository Health % =
DIVIDE (
    CALCULATE ( COUNTROWS ( fact_margin ), fact_margin[Record_Status] = "PUBLISHED" ),
    COUNTROWS ( fact_margin ),
    0
) * 100

PASS Count =
CALCULATE ( COUNTROWS ( fact_margin ), fact_margin[QC_Severity] = "PASS" )

WARNING Count =
CALCULATE ( COUNTROWS ( fact_margin ), fact_margin[QC_Severity] = "WARNING" )

FAIL Count =
CALCULATE ( COUNTROWS ( fact_margin ), fact_margin[QC_Severity] = "FAIL" )

BLOCKED Count =
CALCULATE ( COUNTROWS ( fact_margin ), fact_margin[QC_Severity] = "BLOCKED" )

Missing GST =
CALCULATE (
    COUNTROWS ( fact_margin ),
    ISBLANK ( fact_margin[GST_Pct] ) || fact_margin[GST_Pct] = 0
)

Missing Pack Size =
CALCULATE (
    COUNTROWS ( fact_margin ),
    ISBLANK ( RELATED ( dim_article[Pack_Size] ) )
)

Missing MRP =
CALCULATE (
    COUNTROWS ( fact_margin ),
    ISBLANK ( fact_margin[MRP] )
)

Latest Version =
MAX ( fact_margin_history[Version] )

New Articles (This Import) =
CALCULATE (
    COUNTROWS ( fact_margin_history ),
    fact_margin_history[Change_Type] = "NEW",
    fact_margin_history[Import_Batch] = MAX ( fact_margin_history[Import_Batch] )
)

Margin Changes (This Import) =
CALCULATE (
    COUNTROWS ( fact_margin_history ),
    fact_margin_history[Change_Type] = "CHANGED",
    fact_margin_history[Import_Batch] = MAX ( fact_margin_history[Import_Batch] )
)

Chains Covered =
DISTINCTCOUNT ( fact_margin[Chain] )

Brands Covered =
DISTINCTCOUNT ( fact_margin[Brand] )
'''


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
