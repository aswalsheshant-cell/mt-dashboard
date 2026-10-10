#!/usr/bin/env python3
"""
Generate PowerBI/model.bim from the build kit (PQ queries, DAX measures, DataModel.md).

model.bim is the Analysis Services Tabular Model JSON format. Opening it in
Tabular Editor and deploying to a Power BI Desktop instance creates the
complete semantic model in one step — no manual pasting of PQ queries or
running C# scripts.

Usage:
    python scripts/build_model_bim.py                     # default paths
    python scripts/build_model_bim.py --out model.bim     # custom output
    python scripts/build_model_bim.py --pq-root C:\\MT    # custom PQ root

The generated model.bim embeds all M expressions, DAX measures, relationships,
hierarchies, and sort orders. The only manual step left is:
  1. Open Tabular Editor → File → Open → model.bim
  2. Connect to Power BI Desktop (Model → Deploy)
  3. Apply theme + build report pages
"""

import argparse
import csv
import json
import os
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
PBI_ROOT = REPO_ROOT / "PowerBI"

# ── Column type inference ─────────────────────────────────────────────

DECIMAL_PATTERNS = re.compile(
    r"NSV|Qty|Amount|Value|Sales|Pct|Margin|Spend|MRP|Price|"
    r"Cont%|Share|Frac|Target|Expense|Volume|ACV|AIC|Cost|"
    r"Tax|TOT|CM2|Gross|Net|Revenue|Pack ML|Pack Sort|"
    r"Bucket Sort|Growth|Rate|Weight|Split|Avg|Sum|Rs|Cr|Lakh",
    re.IGNORECASE,
)
DATE_PATTERNS = re.compile(
    r"^(Date|MonthStart|MonthStartCalc|Week Start Date|"
    r"Effective_From|From|To|Updated Date|GST_Cutover_Date|Period)$",
    re.IGNORECASE,
)
INT_PATTERNS = re.compile(
    r"Sort Order|Sort$|Month No|FY Month No|Month Year Sort|"
    r"Year$|^Ordinal|^Rows|Store Count|Stores|SKUs|Articles|"
    r"Stores Selling|SKU Listings|Stores In Master|"
    r"LY Months Sold|Duration_Days|Locations|Merged Rows",
    re.IGNORECASE,
)
BOOL_PATTERNS = re.compile(
    r"^Is |^Active$|^Is_|^Has_|^Flag$|Outlier Flag|"
    r"Provisional Flag|Fallback Flag|Is Future|Is Category Row|"
    r"Finance_Approved|Relevant For Us",
    re.IGNORECASE,
)


def infer_data_type(col_name):
    if BOOL_PATTERNS.search(col_name):
        return "boolean"
    if DATE_PATTERNS.search(col_name):
        return "dateTime"
    if INT_PATTERNS.search(col_name):
        return "int64"
    if DECIMAL_PATTERNS.search(col_name):
        return "double"
    return "string"


# ── PQ file parser ────────────────────────────────────────────────────

def parse_pq_files(pq_dir):
    """Read .pq files and return a list of (query_name, m_expression) tuples."""
    queries = []
    for f in sorted(pq_dir.glob("*.pq")):
        content = f.read_text(encoding="utf-8")
        # Some files have multiple queries separated by dashes
        blocks = re.split(r"\n-{10,}\s*\n", content)
        for i, block in enumerate(blocks):
            block = block.strip()
            if not block:
                continue
            # Try to find query name from header comment
            name_match = re.search(
                r"//\s*Query(?:\s*name)?:\s*(.+)", block, re.IGNORECASE
            )
            if not name_match:
                name_match = re.search(
                    r"//\s*Table:\s*(.+)", block, re.IGNORECASE
                )
            if name_match:
                qname = name_match.group(1).strip().strip('"').strip("'")
            else:
                # Derive from filename
                stem = f.stem
                # Remove numeric prefix
                qname = re.sub(r"^\d+_", "", stem).replace("_", " ")
                if len(blocks) > 1:
                    qname += f" ({i + 1})"
            queries.append((qname, block, f.name))
    return queries


def columns_from_seed_csv(csv_path):
    """Read first row of a CSV to get column names."""
    try:
        with open(csv_path, "r", encoding="utf-8-sig") as fh:
            reader = csv.reader(fh)
            headers = next(reader)
            return [h.strip() for h in headers if h.strip()]
    except Exception:
        return []


# ── Seed CSV → table column mapping ──────────────────────────────────

SEED_TABLE_MAP = {
    "Chain Master": "Masters/ChainMaster.csv",
    "Brand Master": "Masters/BrandMaster.csv",
    "Category Master": "Masters/CategoryMaster.csv",
    "Article Master": "Masters/ArticleMaster.csv",
    "Zone State Master": "Masters/ZoneStateMaster.csv",
    "Store Master": "Masters/StoreMaster.csv",
    "Nielsen Competitor Master": "Masters/NielsenCompetitorMaster.csv",
    "Assumption Table": "Masters/AssumptionTable.csv",
}


def discover_columns(table_name, pbi_root):
    """Get columns for a table from its seed CSV."""
    seed_dir = pbi_root / "SeedData"
    rel = SEED_TABLE_MAP.get(table_name)
    if rel:
        csv_path = seed_dir / rel
        if csv_path.exists():
            return columns_from_seed_csv(csv_path)
    return None


# ── Hard-coded table column definitions (from PQ analysis) ───────────
# For tables whose columns can't be discovered from seed CSVs

KNOWN_COLUMNS = {
    "Date Table": [
        "Date", "MonthStart", "Year", "Month No", "Month Name",
        "FY Month No", "FY Year", "Quarter", "Month", "Month Year Sort",
        "Is Future",
    ],
    "Fact Primary Sales": [
        "Week Start Date", "MonthStart", "Month", "FY Year", "Quarter",
        "Chain", "Account", "Zone", "State", "City", "Store Code",
        "Store Name", "Brand", "Category", "Sub-category", "Range",
        "Pack Size", "Article Code", "Article Description", "EAN Code",
        "Primary NSV", "Primary Qty", "MRP Sales", "Data Source Name",
    ],
    "Fact Offtake Sales": [
        "MonthStart", "Month", "FY Year", "Chain", "Zone", "State",
        "City", "Store Code", "Store Name", "Store Type", "DC Name",
        "Brand", "Category", "Sub-category", "Range", "Pack Size",
        "Article Code", "Article Code Alt", "EAN Code",
        "Article Description", "Chain Article Description",
        "Offtake Qty", "Offtake NSV", "MRP Sales", "MRP Rate", "Margin",
        "SO Emp Code", "Sales Person", "PPT Category", "Data Source Name",
        "Article Key", "Match Key",
    ],
    "Fact P&L": [
        "MonthStart", "Month", "FY Year", "Chain", "Brand", "Category",
        "Offtake NSV", "Offtake Qty", "MRP Sales",
    ],
    "Fact Nielsen": [
        "MonthStart", "Month", "FY Year", "Nielsen Category", "Brand",
        "Zone", "Market Value Sales", "Our Brand Sales",
        "Value Market Share %", "Volume Market Share %",
        "Data Source Name", "Volume 000 L", "Price Per Ml",
    ],
    "Fact TDP": [
        "MonthStart", "Month", "FY Year", "Chain", "Zone", "State",
        "Brand", "Category", "Sub-category", "Pack Size", "Article Code",
        "Article Description", "ACV %", "AIC", "Numeric Distribution",
        "Weighted Distribution", "Data Source Name",
    ],
    "Fact Primary ShipTo": [
        "MonthStart", "MonthStartCalc", "Month", "FY Year",
        "Ship To Name", "Direct/Distributor", "Chain", "Zone", "State",
        "Brand", "Primary NSV", "MRP Value", "Cont%",
    ],
    "Fact Primary Article": [
        "MonthStart", "Month", "FY Year", "Channel", "Customer Code",
        "Ship To Name", "EAN Code", "net_content", "Brand",
        "PPT Category", "Category", "Sub-category", "Range",
        "Article Description", "Article MRP", "Primary Qty",
        "Primary NSV", "Primary Tax Amount", "Primary MRP", "Avg TOT",
        "MTD-Sale type", "PO Type", "Chain", "Zone", "State",
        "Article Key", "Allocation Status", "Source Type",
        "Provisional Flag",
    ],
    "Ship-To Master": [
        "Ship To Name", "Direct/Distributor", "Primary Chain", "Zone",
        "State", "Chains Served",
    ],
    "Targets": [
        "MonthStart", "Month", "FY Year", "Quarter",
        "Target NSV Cr", "Target NSV",
    ],
    "Store SO Mapping": [
        "Month", "Store Code", "Employee ID 1", "SO Name 1", "Cont% 1",
        "Employee ID 2", "SO Name 2", "Cont% 2",
        "Employee ID 3", "SO Name 3", "Cont% 3",
    ],
    "Primary Allocation Map": [
        "Month", "MonthStart", "FY Year", "Ship To Name",
        "Direct/Distributor", "Chain", "Brand", "Cont%",
    ],
    "Primary Allocation Override": [
        "Month", "Ship To Name", "Chain", "Brand",
        "Override Cont%", "Remarks",
    ],
    "Forecast Override": [
        "Month", "Chain", "Brand", "Category", "Article Code",
        "Manual Forecast NSV", "Growth Assumption %", "Remarks",
    ],
    "Sales Team Mapping": [
        "Month", "Store Code", "Employee ID", "Sales Person", "Cont%",
    ],
    "PL Expense Input": [
        "Month", "FY", "Chain", "Customer Code", "Customer Name",
        "Zone", "State", "Brand", "Category", "Sub Category",
        "Expense Head", "Expense Type", "Expense Amount (INR Lakh)",
        "Remarks", "Source", "Updated By", "Updated Date", "MonthStart",
    ],
    "CustCode Chain Map": [
        "Customer Code", "Chain",
    ],
    "GST Rate QC Table": [
        "Category", "HSN_Code", "Pre_GST_Rate_Pct",
        "Post_GST_Rate_Pct", "Effective_From", "Confidence",
        "Finance_Approved", "Impact_on_TOT_pct", "Note",
    ],
    "GST Config": [
        "GST_Cutover_Date", "Note",
    ],
    "Fact Nielsen Pack": [
        "MonthStart", "Month", "FY Year", "Nielsen Category",
        "Pack Size ml", "Category Value Cr", "Our Value Cr",
        "Category Volume L", "Our Volume L", "Category WD %",
        "Data Source Name",
    ],
    "Fact Account Category": [
        "MonthStart", "Chain", "Month", "Category",
        "Account Sales Rs L", "Honasa Sales Rs L", "Common Category",
        "Share %", "Source", "Level", "Scope", "Relevant For Us",
    ],
    "Fact Account Category Geo": [
        "MonthStart", "Chain", "Month", "Zone", "State", "City",
        "Category", "Account Sales Rs L", "Honasa Sales Rs L", "Stores",
        "Common Category", "Share %", "Source", "Relevant For Us",
    ],
    "Fact Account Assortment": [
        "MonthStart", "Month", "Category", "Articles", "Stores",
        "Chain", "Common Category", "Relevant For Us",
    ],
    "Fact Nielsen Brand Cut": [
        "MonthStart", "Month", "FY Year", "Nielsen Category", "Brand",
        "Is Category Row", "Zone", "Value Cr", "Value Share %",
        "Volume Share %", "Price Per Ml", "WD %", "ND %", "Stores",
        "Sales Per Store Rs", "SAH %", "Data Source Name",
    ],
    "Nielsen Deck State Exposure": [
        "State", "Market FW Cr", "Market SH Cr", "ME Share FW %",
        "ME Share SH %", "Dmart FW %", "Dmart SH %",
        "Reliance FW %", "Reliance SH %", "Apollo FW %", "Apollo SH %",
        "Main Lever", "Source", "Period",
    ],
    "Store City Master": [
        "Store Key", "Chain Name", "Site Code", "Store Name",
        "Zone", "State", "City Final", "City Source", "Visit City",
        "Visit Region", "Visit Status", "Nearest Listed City",
        "Store Type", "Match Key", "Source",
    ],
    "Visit City List": [
        "Region", "City", "Beats Planned (rule)", "Aliases",
    ],
    "Store Universe Overrides": [
        "Chain", "Offtake Chain", "Store Count", "Status", "Note",
        "Source", "As Of",
    ],
    "Store Key Alias": [
        "Alias Store Key", "Alias Match Key", "Alias Site Code",
        "Store Key", "Store Match Key", "Reason",
    ],
    "Dist Cont Weights": [
        "ShipTo Key", "Brand Key", "MonthStart", "Ship To Name",
        "Chain Name", "Brand", "Frac", "Raw Pct Sum", "Source File",
        "Source Type", "Approval Status", "Allocation Method",
        "Provisional Flag", "Fallback Flag", "Fallback Source Month",
        "Load Timestamp",
    ],
    "Pack Size Buckets": [
        "Pack Size Raw", "Pack ML", "Pack Bucket", "Bucket Sort",
        "Bucket Label",
    ],
    "Fact Store Type": [
        "Store Key", "Chain", "State", "Zone", "Store Type",
        "NFL Kind", "LY Months Sold", "Growth Basis",
        "NSV This Year Rs", "NSV Last Year Same Months Rs", "Period",
    ],
    "Fact Pack Size": [
        "MonthStart", "Month", "FY Year", "Category", "Pack",
        "NSV Rs", "Stores Selling", "Pack Sort",
    ],
    "Fact Sales Cuts": [
        "MonthStart", "Month", "FY Year", "Zone", "Brand",
        "Category", "Sub Category", "Store Type", "NSV Rs",
        "Stores Selling",
    ],
    "Fact Inhouse Distribution": [
        "MonthStart", "Month", "FY Year", "Level", "Name",
        "Stores Selling", "SKUs Selling", "SKU Listings",
        "Stores In Master", "NSV Rs", "Basis",
    ],
    "Secondary Sales Efficiency": [
        "FY Year", "Month", "MonthStart", "Chain", "Brand",
        "Primary NSV", "Offtake NSV", "Sell-Through Pct",
        "Sell-Through Raw", "Sell-Through Capped", "Coverage Gap Pct",
        "Inventory Signal", "Signal Sort", "Outlier Flag",
    ],
    "Fact Secondary Sales": [
        "Source_Month", "Month_Label", "MonthStart", "FY_Year",
        "FY_Derived", "Distributor", "NSV_Lakh", "NSV_Cr",
        "Is_Provisional", "Data_Source",
    ],
    "Fact Claim Master": [
        "Period", "FY_Year", "Quarter", "Chain", "Source_Chain",
        "Expense_Category", "Amount_Lakh",
    ],
    "Fact Nielsen Pack Brand": [
        "MonthStart", "Month", "FY Year", "Nielsen Category",
        "Pack Size ml", "Brand", "Value Cr", "Volume L", "WD %",
        "Data Source Name",
    ],
    "Channel Map Store": [
        "Store Code", "Channel", "Remarks",
    ],
    "Channel Map Chain": [
        "Chain", "Channel", "Remarks",
    ],
    "Customer Code Zone Master": [
        "Customer Code", "Customer Name / Ship-to Name", "State",
        "Zone", "City / Location", "Business Region / Sub-region",
        "Chain Name", "Account", "Channel", "Mapping Source",
        "Validation Status", "Remarks",
    ],
    "Dim Promo Calendar": [
        "Source_Month", "Promo_Month", "Promo_Year", "From", "To",
        "Duration_Days", "Chain Name", "Brand", "Category",
        "Sub_Category", "Range", "EAN Code", "Article Code",
        "Description", "MRP", "Offer to consumer",
        "ME_Contribution_Pct", "Chain_Contribution_Pct",
        "Total_Contribution_Pct", "Locations", "Promo_Type",
        "Promo_Key",
    ],
}


# ── DAX file parser ──────────────────────────────────────────────────

def parse_dax_measures(dax_dir):
    """Parse all .dax files and return (measures_list, calc_table_dax, calc_columns)."""
    measures = []
    calc_table_dax = None
    calc_columns = []

    skip_files = {"00_DateTable.dax"}
    calc_col_files = {"10_SIS_Reconciliation.dax", "12_TOT_Measures.dax",
                      "13_CM2_Measures.dax"}

    # Read Date Table first
    dt_path = dax_dir / "00_DateTable.dax"
    if dt_path.exists():
        content = dt_path.read_text(encoding="utf-8")
        # Extract just the DAX expression (skip comments)
        lines = content.split("\n")
        dax_lines = []
        started = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("Date Table ="):
                started = True
                dax_lines.append(line[line.index("=") + 1:])
                continue
            if started:
                if stripped.startswith("//") and not dax_lines:
                    continue
                if stripped.startswith("// ---"):
                    break
                dax_lines.append(line)
        calc_table_dax = "\n".join(dax_lines).strip()

    for f in sorted(dax_dir.glob("*.dax")):
        if f.name in skip_files:
            continue
        content = f.read_text(encoding="utf-8")
        lines = content.split("\n")

        current_name = None
        current_dax = []
        is_calc_col = False
        in_block_comment = False

        for i, line in enumerate(lines + [None]):
            if line is not None:
                trimmed = line.strip()
                if trimmed.startswith("/*"):
                    in_block_comment = True
                if in_block_comment:
                    if "*/" in trimmed:
                        in_block_comment = False
                    continue
                if trimmed.startswith("//") and current_name is None:
                    continue
            else:
                trimmed = ""

            is_new_measure = False
            new_name = None
            first_expr = None

            if line is not None and not trimmed.startswith("//"):
                # Detect calc column: 'Table'[Col] =
                calc_match = re.match(
                    r"^'([^']+)'\[([^\]]+)\]\s*=\s*(.*)", trimmed
                )
                if calc_match:
                    is_calc_col = True

                # Detect measure: Name = expr  or  [Name] = expr
                # A measure starts at column 0. Names may hold %, -, /, & and
                # digits (e.g. "MoM Growth %"). VAR and RETURN lines are body
                # lines of the measure above, never a new measure.
                m = re.match(
                    r"^(?:\[([^\]]+)\]|([A-Za-z_][^=()\[\]\n,]*(?:\([^()=\n]*\)[^=()\[\]\n,]*)*?))\s*=(?!=)\s*",
                    line,
                )
                if m and re.match(r"^(VAR|RETURN)\b", line):
                    m = None
                if m and not calc_match:
                    is_new_measure = True
                    new_name = (m.group(1) or m.group(2)).strip()
                    first_expr = line[line.index("=") + 1:]

            # Save previous measure/calc-col
            if (is_new_measure or is_calc_col or line is None) and current_name:
                dax_expr = "\n".join(current_dax).strip()
                if dax_expr:
                    measures.append({
                        "name": current_name,
                        "expression": dax_expr,
                        "source": f.name,
                    })
                current_name = None
                current_dax = []

            # Handle calc column
            if is_calc_col and calc_match:
                table_name = calc_match.group(1)
                col_name = calc_match.group(2)
                rest = calc_match.group(3)
                # Collect remaining lines until next definition
                cc_lines = [rest] if rest.strip() else []
                for j in range(i + 1, len(lines)):
                    nxt = lines[j].strip()
                    if re.match(r"^(?:'[^']+'\[|[A-Za-z_]\w*\s*=|\[)", nxt):
                        break
                    if nxt.startswith("//"):
                        break
                    cc_lines.append(lines[j])
                calc_columns.append({
                    "table": table_name,
                    "name": col_name,
                    "expression": "\n".join(cc_lines).strip(),
                    "source": f.name,
                })
                is_calc_col = False
                continue

            if is_new_measure:
                current_name = new_name
                current_dax = [first_expr]
            elif current_name is not None and line is not None:
                current_dax.append(line)

    # Calculated columns that the DAX files keep as commented blocks
    # ("// 'Table'[Col] = ..." ending at a bare "//" line or the first non-comment line).
    # Measures depend on them, so the model needs them. Text is the repo's own.
    have = {(c["table"], c["name"]) for c in calc_columns}
    for f in sorted(dax_dir.glob("*.dax")):
        lines = f.read_text(encoding="utf-8").split("\n")
        i = 0
        while i < len(lines):
            m = re.match(r"^//\s*'([^']+)'\[([^\]]+)\]\s*=\s*(?:--.*)?$", lines[i].rstrip())
            if m:
                body = []
                i += 1
                while i < len(lines) and lines[i].startswith("//") and lines[i].strip() != "//":
                    body.append(re.sub(r"^//\s?", "", lines[i]))
                    i += 1
                key = (m.group(1), m.group(2))
                if key not in have and any(b.strip() for b in body):
                    have.add(key)
                    calc_columns.append({"table": key[0], "name": key[1],
                                         "expression": "\n".join(body).strip(), "source": f.name})
            else:
                i += 1

    return measures, calc_table_dax, calc_columns


# ── PQ file → table name mapping ─────────────────────────────────────

PQ_TABLE_MAP = {
    "00_Parameters.pq": [("pRootFolder", "expression")],
    "01_fnCombineFolder.pq": [("fnCombineFolder", "expression")],
    "02_fnFYLabel.pq": [("fnFYLabel", "expression")],
    "10_Fact_PrimarySales.pq": [("Fact Primary Sales", "table")],
    "11_Fact_OfftakeSales.pq": [("Fact Offtake Sales", "table")],
    "12_Fact_PnL.pq": [("Fact P&L", "table")],
    "13_Fact_Nielsen.pq": [("Fact Nielsen", "table")],
    "14_Fact_TDP.pq": [("Fact TDP", "table")],
    "15_Fact_PrimaryShipTo.pq": [("Fact Primary ShipTo", "table")],
    "16_Fact_PrimaryArticle.pq": [("Fact Primary Article", "table")],
    "20_Dim_Masters.pq": [
        ("Chain Master", "table"),
        ("Brand Master", "table"),
        ("Category Master", "table"),
        ("Article Master", "table"),
        ("Zone State Master", "table"),
        ("Store Master", "table"),
        ("Nielsen Competitor Master", "table"),
    ],
    "21_ShipToMaster.pq": [("Ship-To Master", "table")],
    "22_CustomerCodeZoneMaster.pq": [("Customer Code Zone Master", "table")],
    "24_ChannelMap.pq": [
        ("Channel Map Store", "table"),
        ("Channel Map Chain", "table"),
    ],
    "30_AssumptionTable.pq": [("Assumption Table", "table")],
    "31_Targets.pq": [("Targets", "table")],
    "32_StoreSOMapping.pq": [("Store SO Mapping", "table")],
    "33_ForecastOverride.pq": [("Forecast Override", "table")],
    "34_PrimaryAllocationMap.pq": [("Primary Allocation Map", "table")],
    "35_PrimaryAllocationOverride.pq": [("Primary Allocation Override", "table")],
    "36_SalesTeamMapping.pq": [("Sales Team Mapping", "table")],
    "37_GST_Rate_QC_Table.pq": [("GST Rate QC Table", "table")],
    "38_GST_Config.pq": [("GST Config", "table")],
    "39_PL_Expense_Input.pq": [("PL Expense Input", "table")],
    "40_CustCode_Chain_Map.pq": [("CustCode Chain Map", "table")],
    "41_DistContWeights.pq": [("Dist Cont Weights", "table")],
    "42_PackSizeBuckets.pq": [("Pack Size Buckets", "table")],
    "43_SecondarySalesEfficiency.pq": [("Secondary Sales Efficiency", "table")],
    "44_Fact_SecondarySales.pq": [("Fact Secondary Sales", "table")],
    "45_Fact_ClaimMaster.pq": [("Fact Claim Master", "table")],
    "46_Dim_PromoCalendar.pq": [("Dim Promo Calendar", "table")],
    "47_Fact_Nielsen_Pack.pq": [("Fact Nielsen Pack", "table")],
    "48_Nielsen_Deck_StateExposure.pq": [("Nielsen Deck State Exposure", "table")],
    "49_Store_City_Master.pq": [("Store City Master", "table")],
    "50_Visit_City_List.pq": [("Visit City List", "table")],
    "51_Fact_Nielsen_Pack_Brand.pq": [("Fact Nielsen Pack Brand", "table")],
    "52_Store_Universe_Overrides.pq": [("Store Universe Overrides", "table")],
    "53_Fact_Account_Category.pq": [("Fact Account Category", "table")],
    "54_Fact_Account_Category_Geo.pq": [("Fact Account Category Geo", "table")],
    "55_Fact_Account_Assortment.pq": [("Fact Account Assortment", "table")],
    "56_Store_Key_Alias.pq": [("Store Key Alias", "table")],
    "57_Fact_Nielsen_Brand_Cut.pq": [("Fact Nielsen Brand Cut", "table")],
    "58_Fact_Store_Type.pq": [("Fact Store Type", "table")],
    "59_Fact_Pack_Size.pq": [("Fact Pack Size", "table")],
    "60_Fact_Sales_Cuts.pq": [("Fact Sales Cuts", "table")],
    "61_Fact_Inhouse_Distribution.pq": [("Fact Inhouse Distribution", "table")],
}


# ── Relationship definitions from DataModel.md ───────────────────────

RELATIONSHIPS = [
    # Date Table → Facts
    ("Date Table", "Date", "Fact Primary Sales", "Week Start Date"),
    ("Date Table", "MonthStart", "Fact Offtake Sales", "MonthStart"),
    ("Date Table", "MonthStart", "Fact P&L", "MonthStart"),
    ("Date Table", "MonthStart", "Fact Nielsen", "MonthStart"),
    ("Date Table", "MonthStart", "Fact TDP", "MonthStart"),
    ("Date Table", "MonthStart", "Targets", "MonthStart"),
    ("Date Table", "MonthStart", "Fact Primary ShipTo", "MonthStartCalc"),
    ("Date Table", "MonthStart", "Fact Primary Article", "MonthStart"),
    ("Date Table", "MonthStart", "PL Expense Input", "MonthStart"),
    ("Date Table", "MonthStart", "Fact Nielsen Pack", "MonthStart"),
    ("Date Table", "MonthStart", "Fact Account Category", "MonthStart"),
    ("Date Table", "MonthStart", "Fact Account Category Geo", "MonthStart"),
    ("Date Table", "MonthStart", "Fact Account Assortment", "MonthStart"),
    ("Date Table", "MonthStart", "Fact Nielsen Brand Cut", "MonthStart"),
    # Chain Master
    ("Chain Master", "Chain", "Fact Offtake Sales", "Chain"),
    ("Chain Master", "Chain", "Fact Primary Sales", "Chain"),
    ("Chain Master", "Chain", "Fact P&L", "Chain"),
    ("Chain Master", "Chain", "Fact TDP", "Chain"),
    ("Chain Master", "Chain", "Fact Primary ShipTo", "Chain"),
    ("Chain Master", "Chain", "Fact Primary Article", "Chain"),
    ("Chain Master", "Chain", "Fact Account Category", "Chain"),
    ("Chain Master", "Chain", "Fact Account Category Geo", "Chain"),
    ("Chain Master", "Chain", "Fact Account Assortment", "Chain"),
    # Brand Master
    ("Brand Master", "Brand", "Fact Offtake Sales", "Brand"),
    ("Brand Master", "Brand", "Fact Primary Sales", "Brand"),
    ("Brand Master", "Brand", "Fact P&L", "Brand"),
    ("Brand Master", "Brand", "Fact TDP", "Brand"),
    ("Brand Master", "Brand", "Fact Nielsen", "Brand"),
    ("Brand Master", "Brand", "Fact Primary Article", "Brand"),
    ("Brand Master", "Brand", "Fact Primary ShipTo", "Brand"),
    # Category Master
    ("Category Master", "Category", "Fact Offtake Sales", "Category"),
    ("Category Master", "Category", "Fact Primary Sales", "Category"),
    ("Category Master", "Category", "Fact P&L", "Category"),
    ("Category Master", "Category", "Fact TDP", "Category"),
    ("Category Master", "Nielsen Category", "Fact Nielsen", "Nielsen Category"),
    ("Category Master", "Category", "Fact Primary Article", "Category"),
    ("Category Master", "Nielsen Category", "Fact Nielsen Pack", "Nielsen Category"),
    # Article Master
    ("Article Master", "Article Code", "Fact Offtake Sales", "Article Code"),
    ("Article Master", "Article Code", "Fact Primary Sales", "Article Code"),
    ("Article Master", "Article Code", "Fact TDP", "Article Code"),
    # Store Master
    ("Store Master", "Store Code", "Fact Offtake Sales", "Store Code"),
    ("Store Master", "Store Code", "Fact Primary Sales", "Store Code"),
    ("Store Master", "Store Code", "Store SO Mapping", "Store Code"),
    # Zone State Master
    ("Zone State Master", "Zone", "Fact Offtake Sales", "Zone"),
    # Ship-To Master
    ("Ship-To Master", "Ship To Name", "Fact Primary ShipTo", "Ship To Name"),
    # Nielsen Competitor Master
    ("Nielsen Competitor Master", "Brand", "Fact Nielsen Brand Cut", "Brand"),
    # Store City Master / Visit City
    ("Visit City List", "City", "Store City Master", "Visit City"),
]

# ── Hierarchy definitions ─────────────────────────────────────────────

HIERARCHIES = [
    ("Zone State Master", "Geography", ["Zone", "State"]),
    ("Article Master", "Product", ["Category", "Sub-category", "Brand", "Article Code"]),
    ("Article Master", "Product (Pack)", ["Category", "Brand", "Pack Size", "Article Code"]),
    ("Date Table", "Time (FY)", ["FY Year", "Quarter", "Month Name"]),
]

# ── Sort-by-column definitions ────────────────────────────────────────

SORT_BY = [
    ("Zone State Master", "Zone", "Zone Sort Order"),
    ("Date Table", "Month Name", "Month No"),
    ("Date Table", "Month", "Month Year Sort"),
    ("Date Table", "Quarter", "FY Month No"),
    ("Brand Master", "Brand", "Brand Sort Order"),
    ("Category Master", "Category", "Category Sort Order"),
]


# ── model.bim builder ────────────────────────────────────────────────

def build_column_def(col_name):
    dtype = infer_data_type(col_name)
    col = {
        "name": col_name,
        "dataType": dtype,
        "sourceColumn": col_name,
    }
    return col


def build_table(name, columns, m_expression=None, is_calculated=False,
                calc_dax=None, calc_cols=None):
    table = {"name": name, "columns": [], "measures": []}

    seen_cols = set()
    for col_name in columns:
        if col_name in seen_cols:  # a model cannot hold two columns with one name
            continue
        seen_cols.add(col_name)
        table["columns"].append(build_column_def(col_name))

    if is_calculated and calc_dax:
        table["partitions"] = [{
            "name": name,
            "source": {
                "type": "calculated",
                "expression": calc_dax.split("\n"),
            },
        }]
    elif m_expression:
        table["partitions"] = [{
            "name": name,
            "source": {
                "type": "m",
                "expression": m_expression.split("\n"),
            },
        }]

    # Add calculated columns
    if calc_cols:
        for cc in calc_cols:
            # a calculated column replaces a same-named source column, and the
            # same calculated column listed twice is kept once
            table["columns"] = [c for c in table["columns"] if c["name"] != cc["name"]]
            table["columns"].append({
                "name": cc["name"],
                "dataType": infer_data_type(cc["name"]),
                "sourceColumn": cc["name"],
                "type": "calculated",
                "expression": cc["expression"],
                "isDataTypeInferred": True,
            })

    return table


def build_relationship(idx, dim_table, dim_col, fact_table, fact_col):
    return {
        "name": f"rel_{idx:03d}",
        "fromTable": fact_table,
        "fromColumn": fact_col,
        "toTable": dim_table,
        "toColumn": dim_col,
        "crossFilteringBehavior": "oneDirection",
    }


def build_hierarchy(name, levels):
    return {
        "name": name,
        "levels": [
            {"name": col, "ordinal": i, "column": col}
            for i, col in enumerate(levels)
        ],
    }


def main():
    parser = argparse.ArgumentParser(
        description="Generate model.bim from the MT Dashboard build kit"
    )
    parser.add_argument(
        "--out", default=str(PBI_ROOT / "model.bim"),
        help="Output path for model.bim (default: PowerBI/model.bim)",
    )
    parser.add_argument(
        "--pq-root", default=None,
        help="Override pRootFolder value embedded in M expressions",
    )
    args = parser.parse_args()

    pq_dir = PBI_ROOT / "PowerQuery"
    dax_dir = PBI_ROOT / "DAX"

    print("Parsing Power Query files...")
    pq_queries = parse_pq_files(pq_dir)
    print(f"  Found {len(pq_queries)} PQ queries")

    print("Parsing DAX measures...")
    measures, date_table_dax, calc_columns = parse_dax_measures(dax_dir)
    print(f"  Found {len(measures)} measures")
    print(f"  Found {len(calc_columns)} calculated columns")

    # Build PQ file → M expression lookup
    pq_by_file = {}
    for qname, m_expr, fname in pq_queries:
        if fname not in pq_by_file:
            pq_by_file[fname] = []
        pq_by_file[fname].append((qname, m_expr))

    # Build tables
    tables = []
    tables_by_name = {}

    # 1. Date Table (calculated)
    date_cols = KNOWN_COLUMNS["Date Table"]
    dt = build_table("Date Table", date_cols, is_calculated=True,
                     calc_dax=date_table_dax)
    dt["dataCategory"] = "Time"
    tables.append(dt)
    tables_by_name["Date Table"] = dt

    # 2. All other tables from PQ mapping
    for pq_file, table_list in PQ_TABLE_MAP.items():
        for table_name, kind in table_list:
            if kind == "expression":
                continue  # skip parameters/functions in table list
            if table_name in tables_by_name:
                continue

            # Get columns
            cols = discover_columns(table_name, PBI_ROOT)
            if cols is None:
                cols = KNOWN_COLUMNS.get(table_name)
            if cols is None:
                print(f"  WARNING: no columns for '{table_name}' — skipping")
                continue

            # Get M expression from PQ file
            m_expr = None
            pq_entries = pq_by_file.get(pq_file, [])
            if len(pq_entries) == 1:
                m_expr = pq_entries[0][1]
            elif len(pq_entries) > 1:
                # Multi-query file — try to match by name
                for qn, qe in pq_entries:
                    if qn.lower() == table_name.lower():
                        m_expr = qe
                        break
                if m_expr is None:
                    m_expr = pq_entries[0][1]

            # Get calc columns for this table
            table_calc_cols = [
                cc for cc in calc_columns if cc["table"] == table_name
            ]

            t = build_table(table_name, cols, m_expression=m_expr,
                            calc_cols=table_calc_cols or None)
            tables.append(t)
            tables_by_name[table_name] = t

    # 3. _Measures table
    measures_table = {
        "name": "_Measures",
        "columns": [{
            "name": "Placeholder",
            "dataType": "string",
            "sourceColumn": "Placeholder",
            "isHidden": True,
        }],
        "partitions": [{
            "name": "_Measures",
            "source": {
                "type": "calculated",
                "expression": ["ROW(\"Placeholder\", BLANK())"],
            },
        }],
        "measures": [],
    }

    # Add all measures to _Measures table
    for m in measures:
        measures_table["measures"].append({
            "name": m["name"],
            "expression": m["expression"].split("\n"),
            "description": f"Source: {m['source']}",
        })

    tables.append(measures_table)
    tables_by_name["_Measures"] = measures_table

    print(f"  Built {len(tables)} tables")
    print(f"  Added {len(measures_table['measures'])} measures to _Measures")

    # Build relationships
    relationships = []
    for i, (dim_t, dim_c, fact_t, fact_c) in enumerate(RELATIONSHIPS):
        if dim_t in tables_by_name and fact_t in tables_by_name:
            relationships.append(build_relationship(i, dim_t, dim_c, fact_t, fact_c))
        else:
            missing = dim_t if dim_t not in tables_by_name else fact_t
            print(f"  SKIP rel: {dim_t} → {fact_t} (missing: {missing})")

    print(f"  Built {len(relationships)} relationships")

    # Add hierarchies to tables
    for table_name, hier_name, levels in HIERARCHIES:
        if table_name in tables_by_name:
            t = tables_by_name[table_name]
            if "hierarchies" not in t:
                t["hierarchies"] = []
            t["hierarchies"].append(build_hierarchy(hier_name, levels))

    # Add sort-by-column
    for table_name, col_name, sort_col in SORT_BY:
        if table_name in tables_by_name:
            t = tables_by_name[table_name]
            for c in t.get("columns", []):
                if c["name"] == col_name:
                    c["sortByColumn"] = sort_col
                    break

    # Assemble model.bim
    model_bim = {
        "name": "MT_Dashboard",
        "compatibilityLevel": 1567,
        "model": {
            "culture": "en-US",
            "tables": tables,
            "relationships": relationships,
            "annotations": [
                {
                    "name": "GeneratedBy",
                    "value": "scripts/build_model_bim.py",
                },
                {
                    "name": "ProjectRepo",
                    "value": "aswalsheshant-cell/mt-dashboard",
                },
            ],
        },
    }

    # Write
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(model_bim, f, indent=2, ensure_ascii=False)

    size_kb = out_path.stat().st_size / 1024
    print(f"\n{'=' * 50}")
    print(f"model.bim written to: {out_path}")
    print(f"  Size: {size_kb:.0f} KB")
    print(f"  Tables: {len(tables)}")
    print(f"  Relationships: {len(relationships)}")
    print(f"  Measures: {len(measures_table['measures'])}")
    print(f"  Hierarchies: {sum(1 for t in tables for _ in t.get('hierarchies', []))}")
    print(f"{'=' * 50}")
    print("\nNext steps:")
    print("  1. Open Tabular Editor → File → Open → model.bim")
    print("  2. Connect to Power BI Desktop (Model → Deploy)")
    print("  3. Set pRootFolder parameter to your local PowerBI/ path")
    print("  4. Apply theme: View → Themes → HonasaMT_Theme.json")
    print("  5. Build 18 pages per PowerBI/docs/PageLayouts.md")


if __name__ == "__main__":
    main()
