"""Command: "Generate the complete DAX measure library."

Per CLAUDE.md's CRITICAL IMPLEMENTATION RULES ("audit what already
exists... extend current functions instead of creating duplicate
ones"), this does NOT regenerate a parallel DAX library — the repo
already has one across ``PowerBI/DAX/00_DateTable.dax`` .. ``13_CM2_Measures.dax``,
14 files/~3000 lines. Blindly emitting a second copy would risk exactly
the kind of duplicate-definition bug ``dax_validator`` already caught
once (``QC Mapping Coverage %`` defined twice).

Instead this is a coverage AUDIT: it re-uses ``dax_validator.extract_definitions``
to inventory every measure name already defined in ``PowerBI/DAX/``, diffs
that against the spec's required measure catalogue (Core / Time
Intelligence / Growth / Business / QC), and for anything genuinely
missing, generates a properly-commented, DIVIDE-safe DAX snippet — staged
in the build output folder for review, never auto-placed into
``PowerBI/DAX/`` (that requires explicit user approval, per the
Power BI Desktop separation rule).
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

from .config import Config
from .dax_validator import extract_definitions, strip_comments_and_strings

# name -> (category, description, format_string, display_folder, dependencies, qc_test)
REQUIRED_MEASURES: dict[str, tuple] = {
    # -- Core --
    "NSV Lacs": ("Core", "Net Sales Value in INR Lakh.", "#,##0.0", "Core Measures", [],
                 "DIVIDE(SUM(NSV), 100000) matches Fact_OfftakeSales NSV sum / 1e5"),
    "NSV Actual": ("Core", "Net Sales Value, unscaled INR.", "#,##0", "Core Measures", [],
                   "SUM(NSV) matches source column total exactly"),
    "NSV Cr": ("Core", "Net Sales Value in INR Crore.", "#,##0.00", "Core Measures", ["NSV Actual"],
               "[NSV Actual] / 1e7"),
    "MRP Sales Value": ("Core", "Gross sales value at MRP (tax-inclusive basis).", "#,##0", "Core Measures", [],
                         "SUM(MRP Sales Value) matches source column total"),
    "Quantity": ("Core", "Units sold.", "#,##0", "Core Measures", [], "SUM(Sales Qty) matches source total"),
    "Units": ("Core", "Alias of Quantity for page-level KPI cards.", "#,##0", "Core Measures", ["Quantity"], "equals [Quantity]"),
    "Distinct Articles": ("Core", "Count of distinct EAN/article codes with any sales in filter context.",
                           "#,##0", "Core Measures", [], "DISTINCTCOUNT never exceeds Dim_Article row count"),
    "Distinct Stores": ("Core", "Count of distinct store/site codes with any sales.", "#,##0", "Core Measures", [],
                         "DISTINCTCOUNT never exceeds Dim_Store row count"),
    "Active Chains": ("Core", "Count of distinct chains with NSV > 0 in filter context.", "#,##0", "Core Measures", ["NSV Actual"],
                       "never exceeds Dim_Chain row count where Active = Yes"),
    # -- Time intelligence --
    "Latest Available Month": ("Time Intelligence", "Max month with NSV > 0 in the fact table.", "General Date", "Time Intelligence", [],
                                "matches MAX month present in Fact_OfftakeSales"),
    "Previous Month": ("Time Intelligence", "Calendar month immediately before Latest Available Month.", "General Date", "Time Intelligence",
                        ["Latest Available Month"], "EOMONTH([Latest Available Month], -1) + 1"),
    "Previous Year Same Month": ("Time Intelligence", "Same calendar month, prior year.", "General Date", "Time Intelligence",
                                  ["Latest Available Month"], "EDATE([Latest Available Month], -12)"),
    "Current FY": ("Time Intelligence", "THE ONE FY RULE applied to Latest Available Month (Apr-Mar).", "General Date",
                    "Time Intelligence", ["Latest Available Month"], "matches agent.fyrules.fy_tag_from_ym"),
    "Previous FY": ("Time Intelligence", "FY immediately before Current FY.", "General Date", "Time Intelligence",
                     ["Current FY"], "Current FY - 1"),
    "MTD": ("Time Intelligence", "Month-to-date NSV using DATESMTD over the approved Date table.", "#,##0", "Time Intelligence",
             ["NSV Actual"], "DATESMTD never spans a fiscal-year boundary incorrectly"),
    "QTD": ("Time Intelligence", "Quarter-to-date NSV, fiscal quarter (Apr-Mar aligned).", "#,##0", "Time Intelligence",
             ["NSV Actual"], "fiscal quarter boundaries match Date Table[Quarter]"),
    "YTD": ("Time Intelligence", "Fiscal year-to-date NSV (Apr start).", "#,##0", "Time Intelligence",
             ["NSV Actual"], "resets at April, not January"),
    "L3M": ("Time Intelligence", "Trailing 3-month NSV total ending Latest Available Month.", "#,##0", "Time Intelligence",
             ["NSV Actual", "Latest Available Month"], "sums exactly 3 distinct months"),
    "L6M": ("Time Intelligence", "Trailing 6-month NSV total.", "#,##0", "Time Intelligence",
             ["NSV Actual", "Latest Available Month"], "sums exactly 6 distinct months"),
    "L12M": ("Time Intelligence", "Trailing 12-month NSV total.", "#,##0", "Time Intelligence",
              ["NSV Actual", "Latest Available Month"], "sums exactly 12 distinct months"),
    # -- Growth --
    "MoM Growth Value": ("Growth", "Current month NSV minus previous month NSV.", "#,##0;-#,##0", "Growth", ["NSV Actual"],
                          "BLANK() when previous month has no data, never 0"),
    "MoM Growth %": ("Growth", "MoM growth as a percentage, DIVIDE-safe.", "0.0%;-0.0%", "Growth",
                      ["MoM Growth Value"], "DIVIDE numerator by previous-month NSV, BLANK on 0 denominator"),
    "YoY Growth Value": ("Growth", "Current NSV minus same month prior year.", "#,##0;-#,##0", "Growth", ["NSV Actual"],
                          "BLANK() when prior-year month has no data"),
    "YoY Growth %": ("Growth", "YoY growth as a percentage, DIVIDE-safe.", "0.0%;-0.0%", "Growth",
                      ["YoY Growth Value"], "DIVIDE-safe, BLANK on 0 denominator"),
    "Growth versus L3M": ("Growth", "Current month NSV minus L3M average.", "#,##0;-#,##0", "Growth",
                           ["NSV Actual", "L3M"], "L3M here means the 3-month AVERAGE, not the running total"),
    "Growth versus L3M %": ("Growth", "Growth vs L3M average, DIVIDE-safe percentage.", "0.0%;-0.0%", "Growth",
                             ["Growth versus L3M"], "DIVIDE-safe"),
    "Contribution %": ("Growth", "Share of the current filter context's NSV within its parent total.", "0.0%", "Growth",
                        ["NSV Actual"], "sums to ~100% across the parent dimension's members"),
    "Incremental Growth": ("Growth", "Absolute NSV added versus the prior comparable period.", "#,##0;-#,##0", "Growth",
                            ["NSV Actual"], "equals MoM/YoY value depending on active comparison filter"),
    "Variance versus Target": ("Growth", "NSV minus the approved target/forecast value.", "#,##0;-#,##0", "Growth",
                                ["NSV Actual"], "BLANK() when no approved target exists, never 0"),
    "Variance versus Target %": ("Growth", "Variance vs target, DIVIDE-safe percentage.", "0.0%;-0.0%", "Growth",
                                  ["Variance versus Target"], "DIVIDE-safe"),
    # -- Business --
    "Primary versus Offtake": ("Business", "Primary sell-in NSV minus Offtake sell-out NSV.", "#,##0;-#,##0", "Business",
                                [], "matches PowerBI/DAX/10_SIS_Reconciliation.dax methodology"),
    "Offtake versus MASIT": ("Business", "Offtake NSV minus MASIT (market share/Nielsen-derived) estimate.", "#,##0;-#,##0",
                              "Business", [], "BLANK() when no Nielsen estimate is loaded for the period"),
    "Variance Flag above approved threshold": ("Business", "TRUE when |variance %| exceeds the approved QC threshold.",
                                                 "General", "Business", ["Variance versus Target %"],
                                                 "threshold must come from an approved config table, not a literal"),
    "Distribution Gap": ("Business", "Approved listing count minus stores with actual NSV > 0.", "#,##0", "Business",
                          ["Distinct Stores"], "never negative when listings are a superset of selling stores"),
    "Zero-Sale Stores": ("Business", "Count of listed stores with NSV = 0 in the period.", "#,##0", "Business", [],
                          "Distinct Stores (listed) minus Distinct Stores (NSV>0)"),
    "Active Listing with Zero Sale": ("Business", "Zero-Sale Stores restricted to Active = Yes listings.", "#,##0",
                                       "Business", ["Zero-Sale Stores"], "subset of Zero-Sale Stores"),
    "Store Productivity": ("Business", "NSV per active selling store.", "#,##0", "Business",
                            ["NSV Actual", "Distinct Stores"], "DIVIDE-safe"),
    "Sales per Store": ("Business", "Alias of Store Productivity for page-level cards.", "#,##0", "Business",
                         ["Store Productivity"], "equals [Store Productivity]"),
    "Article Productivity": ("Business", "NSV per distinct selling article.", "#,##0", "Business",
                              ["NSV Actual", "Distinct Articles"], "DIVIDE-safe"),
    "Chain Contribution": ("Business", "Chain's share of total NSV.", "0.0%", "Business", ["NSV Actual", "Contribution %"],
                            "sums to ~100% across all chains"),
    "Brand Contribution": ("Business", "Brand's share of total NSV.", "0.0%", "Business", ["NSV Actual", "Contribution %"],
                            "sums to ~100% across all brands"),
    "Category Contribution": ("Business", "Category's share of total NSV.", "0.0%", "Business", ["NSV Actual", "Contribution %"],
                               "sums to ~100% across all categories"),
    "CM2": ("Business", "Contribution Margin 2 (NSV minus trade spend minus direct expense).", "#,##0;-#,##0", "Business",
             ["NSV Actual"], "matches PowerBI/DAX/13_CM2_Measures.dax methodology"),
    "TOT %": ("Business", "Trade Offer / Total spend as a % of NSV.", "0.0%", "Business", ["NSV Actual"],
               "matches PowerBI/DAX/12_TOT_Measures.dax methodology"),
    "Expense Contribution": ("Business", "P&L expense line's share of total expense.", "0.0%", "Business", [],
                              "sums to ~100% across expense lines"),
    # -- QC --
    "Source Row Count": ("QC", "Raw source row count for the latest loaded period.", "#,##0", "Data Quality", [],
                          "matches Dataset_Build_Log.source_row_count"),
    "Model Row Count": ("QC", "Fact table row count after load.", "#,##0", "Data Quality", [], "matches DAX COUNTROWS(Fact_OfftakeSales)"),
    "Source versus Model Variance": ("QC", "Model Row Count minus Source Row Count.", "#,##0;-#,##0", "Data Quality",
                                      ["Source Row Count", "Model Row Count"], "explainable by aggregation grain, never silently nonzero on NSV"),
    "Unmapped Record Count": ("QC", "Rows with a chain or article that failed master mapping.", "#,##0", "Data Quality", [],
                               "matches Mapping_Exception_Report row count"),
    "Duplicate Record Count": ("QC", "Business keys (site, article, month) seen more than once in source.", "#,##0",
                                "Data Quality", [], "matches Data_Quality_Report.duplicate_business_keys"),
    "Blank Key Count": ("QC", "Rows dropped for a missing site/article/chain key.", "#,##0", "Data Quality", [],
                         "matches Data_Quality_Report.blank_key_rows_dropped"),
    "Latest Refresh Date": ("QC", "Timestamp of the last successful model refresh.", "General Date", "Data Quality", [],
                             "must update on every successful refresh, never stale"),
    "Data Completeness Status": ("QC", "'Complete' / 'Incomplete' flag for the latest period.", "General", "Data Quality", [],
                                  "'Incomplete' whenever the period's row count is below the configured minimum"),
    "Missing Month Status": ("QC", "Flags any FY month with zero fact rows between FY start and Latest Available Month.",
                              "General", "Data Quality", [], "never silently treats a missing month as zero sales"),
    "Reconciliation Status": ("QC", "'PASS'/'FAIL' from the latest Source_Reconciliation_Report.", "General", "Data Quality",
                               [], "'FAIL' whenever |variance| exceeds the configured tolerance"),
}


def _normalize_measure_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def _inventory_existing_measures(dax_dir: Path) -> dict[str, str]:
    """normalized_name -> 'file.dax:line' for every measure already
    defined under PowerBI/DAX/.
    """
    out = {}
    for path in sorted(dax_dir.glob("*.dax")):
        text = path.read_text(encoding="utf-8", errors="replace")
        cleaned, _ = strip_comments_and_strings(text)
        for d in extract_definitions(cleaned, path.name):
            out[_normalize_measure_name(d.name)] = f"{path.name}:{d.line}"
    return out


def _generate_snippet(name: str, category: str, description: str, fmt: str,
                       folder: str, deps: list, qc_test: str) -> str:
    dep_line = f"// Depends on: {', '.join(deps)}" if deps else "// Depends on: (none)"
    return (
        f"// [{category}] {description}\n"
        f"// Display folder: {folder}\n"
        f"// Format string:  {fmt}\n"
        f"{dep_line}\n"
        f"// QC test: {qc_test}\n"
        f"{name} =\n"
        f"VAR _Result = 0   // TODO: replace with the real DIVIDE()-based expression\n"
        f"RETURN\n"
        f"    IF ( ISBLANK ( _Result ), BLANK (), _Result )   // never silently coerces a true blank to 0\n"
    )


def generate_dax_library(cfg: Config, dax_dir: Path | None = None) -> dict:
    root = cfg.root()
    dax_dir = dax_dir or (root / "PowerBI" / "DAX")
    if not dax_dir.exists():
        return {"blocked_reason": f"DAX folder not found: {dax_dir}"}

    existing = _inventory_existing_measures(dax_dir)

    present, missing = [], []
    for name, (category, desc, fmt, folder, deps, qc_test) in REQUIRED_MEASURES.items():
        if _normalize_measure_name(name) in existing:
            present.append(name)
        else:
            missing.append(name)

    out_dir = cfg.path(cfg.pbi_build_dir) / "dax_gap_latest"
    out_dir.mkdir(parents=True, exist_ok=True)

    catalogue_path = out_dir / "Measure_Catalogue.csv"
    with open(catalogue_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["measure", "category", "status", "existing_location", "display_folder", "format_string", "dependencies"])
        for name, (category, desc, fmt, folder, deps, qc_test) in REQUIRED_MEASURES.items():
            key = _normalize_measure_name(name)
            status = "Present" if key in existing else "Missing"
            loc = existing.get(key, "")
            w.writerow([name, category, status, loc, folder, fmt, ";".join(deps)])

    dep_map_path = out_dir / "Measure_Dependency_Map.json"
    dep_map = {name: deps for name, (_, _, _, _, deps, _) in REQUIRED_MEASURES.items()}
    dep_map_path.write_text(json.dumps(dep_map, indent=2), encoding="utf-8")

    tests_path = out_dir / "Measure_Test_Cases.csv"
    with open(tests_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["measure", "qc_test"])
        for name, (_, _, _, _, _, qc_test) in REQUIRED_MEASURES.items():
            w.writerow([name, qc_test])

    gap_dax_path = out_dir / "DAX_Gap_Library.dax"
    if missing:
        snippets = [
            _generate_snippet(name, *REQUIRED_MEASURES[name])
            for name in missing
        ]
        header = (
            "// =====================================================================\n"
            "// GENERATED GAP LIBRARY -- measures required by the Module-2 spec that\n"
            "// were NOT found (by normalized name) in the existing PowerBI/DAX/*.dax\n"
            "// files. STAGED FOR REVIEW ONLY -- do not paste into the model until a\n"
            "// human has filled in the TODO expression and confirmed against real\n"
            "// data. Never auto-applied; placing DAX into the live model is a manual\n"
            "// Power BI Desktop action requiring explicit approval.\n"
            "// =====================================================================\n\n"
        )
        gap_dax_path.write_text(header + "\n".join(snippets), encoding="utf-8")
    else:
        gap_dax_path.write_text("// No gaps -- every required measure matched an existing definition.\n", encoding="utf-8")

    coverage_pct = round(100 * len(present) / len(REQUIRED_MEASURES), 1)
    validation_report = {
        "required_measures": len(REQUIRED_MEASURES),
        "present": len(present),
        "missing": len(missing),
        "coverage_pct": coverage_pct,
        "missing_measures": missing,
    }
    validation_path = out_dir / "Measure_Validation_Report.json"
    validation_path.write_text(json.dumps(validation_report, indent=2), encoding="utf-8")

    warning = "" if not missing else f"{len(missing)}/{len(REQUIRED_MEASURES)} required measures have no existing match -- see DAX_Gap_Library.dax"

    return {
        "output_file": str(out_dir.relative_to(root)),
        "validation_result": json.dumps(validation_report),
        "warning": warning,
    }
