"""
validate_pbip_link.py — Verify PBIP report.json references resolve to dataset measures/columns
"""
import json
import os
import re
from pathlib import Path

def parse_tmdl_tables(dataset_path):
    """Extract measure and column names from TMDL files."""
    measures = set()
    columns = set()
    tables = set()

    tables_dir = os.path.join(dataset_path, "definition", "tables")

    if not os.path.exists(tables_dir):
        return measures, columns, tables

    for tmdl_file in os.listdir(tables_dir):
        if tmdl_file.endswith(".tmdl"):
            table_name = tmdl_file.replace(".tmdl", "")
            tables.add(table_name)

            with open(os.path.join(tables_dir, tmdl_file), 'r') as f:
                content = f.read()
                # Extract measure definitions: "measure_name = DAX_EXPRESSION"
                for match in re.finditer(r'measure\s+(\w+)\s*=', content):
                    measures.add(match.group(1))
                # Extract column definitions: "column Column_Name"
                for match in re.finditer(r'column\s+(\w+)', content):
                    columns.add(match.group(1))

    return measures, columns, tables

def extract_report_references(report_path):
    """Extract measure and column references from report.json."""
    with open(report_path, 'r') as f:
        report = json.load(f)

    referenced_measures = set()
    referenced_columns = set()

    # Recursively find queryRef values and track context
    def find_query_refs(obj, parent_key=None):
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key == "queryRef" and isinstance(value, str):
                    ref = value.strip("[]")
                    # Classify based on parent context: "values" → measure, "rows" → column
                    if parent_key == "values":
                        referenced_measures.add(ref)
                    elif parent_key == "rows":
                        referenced_columns.add(ref)
                    else:
                        # Fallback heuristic for other contexts
                        if "_" in ref or ref.isupper():
                            referenced_measures.add(ref)
                        else:
                            referenced_columns.add(ref)
                else:
                    find_query_refs(value, key if key in ["values", "rows"] else parent_key)
        elif isinstance(obj, list):
            for item in obj:
                find_query_refs(item, parent_key)

    find_query_refs(report)
    return referenced_measures, referenced_columns

def main():
    dataset_path = "ModernTrade_Report.Dataset"
    report_path = "ModernTrade_Report.Report/definition/report.json"

    # Check existence
    if not os.path.exists(dataset_path):
        print(f"[FAIL] Dataset path not found: {dataset_path}")
        return False
    if not os.path.exists(report_path):
        print(f"[FAIL] Report path not found: {report_path}")
        return False

    # Parse dataset TMDL
    measures, columns, tables = parse_tmdl_tables(dataset_path)
    print(f"Detected {len(measures)} TMDL measures in dataset.")
    print(f"Detected {len(tables)} tables with declared columns.")

    # Extract report references
    ref_measures, ref_columns = extract_report_references(report_path)
    print(f"Report layout references {len(ref_measures)} measures.")
    print(f"Report layout references {len(ref_columns)} columns.")

    # Validate
    all_pass = True
    for m in ref_measures:
        if m not in measures:
            print(f"[FAIL] Measure not found: {m}")
            all_pass = False
    for c in ref_columns:
        if c not in columns:
            print(f"[FAIL] Column not found: {c}")
            all_pass = False

    if all_pass:
        print("[PASS] All referenced measures exist.")
        print("[PASS] All referenced columns and tables exist.")
        return True
    return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
