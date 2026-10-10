"""Static checks on the Power BI model build and the full-report page contract.

These prove the generated files are consistent with each other. They do not prove
the model refreshes or that any number is right in Power BI Desktop.
"""

import collections
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PBI = ROOT / "PowerBI"


def _model():
    return json.loads((PBI / "model.bim").read_text(encoding="utf-8"))["model"]


def test_no_var_lines_became_measures():
    names = [m["name"] for t in _model()["tables"] for m in t.get("measures", [])]
    assert not [n for n in names if re.match(r"(VAR|RETURN)\b", n)]
    for core in ("MoM Growth %", "Latest Month NSV", "L3M Average Sales", "YoY Growth %"):
        assert core in names


def test_measure_names_are_unique():
    names = [m["name"] for t in _model()["tables"] for m in t.get("measures", [])]
    assert len(names) == len(set(names))


def test_no_duplicate_column_names_in_any_table():
    for t in _model()["tables"]:
        counts = collections.Counter(c["name"] for c in t.get("columns", []))
        assert not {k: v for k, v in counts.items() if v > 1}, t["name"]


def test_relationship_columns_exist():
    m = _model()
    cols = {t["name"]: {c["name"] for c in t.get("columns", [])} for t in m["tables"]}
    for r in m["relationships"]:
        assert r["fromColumn"] in cols[r["fromTable"]], r["name"]
        assert r["toColumn"] in cols[r["toTable"]], r["name"]


def test_shipto_query_skips_subset_snapshots():
    pq = (PBI / "PowerQuery" / "15_Fact_PrimaryShipTo.pq").read_text(encoding="utf-8")
    assert "Primary_ShipTo_FY24-25.csv" in pq and "Primary_ShipTo_FY25-26_to_May26.csv" in pq


def test_page_contract_covers_every_tab_and_subview():
    doc = json.loads((PBI / "full_report_pages.json").read_text(encoding="utf-8"))
    assert doc["html_tab_count"] == 11
    assert not [t["tab"] for t in doc["tabs"] if not t["pages"]]
    assert not [s["subview"] for s in doc["subviews"] if not s["pages"]]


def test_contract_measures_exist_in_model():
    names = {m["name"] for t in _model()["tables"] for m in t.get("measures", [])}
    doc = json.loads((PBI / "full_report_pages.json").read_text(encoding="utf-8"))
    for p in doc["pages"]:
        assert set(p["measures"]) <= names, p["page_id"]


def test_no_page_claims_ready_while_its_sources_are_incomplete():
    doc = json.loads((PBI / "full_report_pages.json").read_text(encoding="utf-8"))
    for p in doc["pages"]:
        if p["blocking_tables"] or p["partial_tables"] or p["measures_with_missing_tables"]:
            assert p["status"] != "READY", p["page_id"]


def test_generated_pbir_json_parses_and_cards_use_model_measures():
    names = {m["name"] for t in _model()["tables"] for m in t.get("measures", [])}
    base = PBI / "PBIR_Generated" / "definition" / "pages"
    files = list(base.rglob("*.json"))
    assert files
    for f in files:
        data = json.loads(f.read_text(encoding="utf-8"))
        if f.name == "visual.json" and data["visual"]["visualType"] == "card":
            prop = data["visual"]["query"]["queryState"]["Values"]["projections"][0]["field"]["Measure"]["Property"]
            assert prop in names, f


def test_every_column_used_by_a_measure_exists():
    m = _model()
    cols = {t["name"]: {c["name"] for c in t.get("columns", [])} for t in m["tables"]}
    measure_names = {x["name"] for t in m["tables"] for x in t.get("measures", [])}
    missing = []
    for t in m["tables"]:
        for x in t.get("measures", []):
            e = x["expression"]
            e = "\n".join(e) if isinstance(e, list) else e
            for tb, c in re.findall(r"'([^']+)'\[([^\]]+)\]", re.sub(r"//.*", "", e)):
                if tb in cols and c not in cols[tb] and c not in measure_names:
                    missing.append((x["name"], tb, c))
    assert not missing, missing[:5]


def test_store_cuts_queries_read_seeddata_not_rawdatafolders():
    for n in ("58_Fact_Store_Type", "59_Fact_Pack_Size", "60_Fact_Sales_Cuts", "61_Fact_Inhouse_Distribution"):
        pq = (PBI / "PowerQuery" / (n + ".pq")).read_text(encoding="utf-8")
        assert "\\SeedData\\Store_Cuts\\" in pq and "\\RawDataFolders\\Store_Cuts\\" not in pq, n


def test_power_query_static_refresh_check_is_clean():
    import subprocess
    import sys
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "check_pq_refresh_risks.py")], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout
