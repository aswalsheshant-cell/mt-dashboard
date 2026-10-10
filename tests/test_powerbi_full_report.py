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


CHART_TYPES = ("lineChart", "clusteredBarChart", "tableEx")


def _chart_visuals():
    base = PBI / "PBIR_Generated" / "definition" / "pages"
    out = []
    for f in base.rglob("visual.json"):
        data = json.loads(f.read_text(encoding="utf-8"))
        if data["visual"]["visualType"] in CHART_TYPES:
            out.append((f, data))
    return out


def test_generated_charts_exist_and_reference_model_objects():
    m = _model()
    cols = {t["name"]: {c["name"] for c in t.get("columns", [])} for t in m["tables"]}
    measures = {x["name"] for x in next(t for t in m["tables"] if t["name"] == "_Measures")["measures"]}
    charts = _chart_visuals()
    assert len(charts) >= 8
    for f, data in charts:
        for role in data["visual"]["query"]["queryState"].values():
            assert role["projections"], f
            for pr in role["projections"]:
                if "Column" in pr["field"]:
                    c = pr["field"]["Column"]
                    assert c["Property"] in cols[c["Expression"]["SourceRef"]["Entity"]], f
                else:
                    c = pr["field"]["Measure"]
                    assert c["Expression"]["SourceRef"]["Entity"] == "_Measures", f
                    assert c["Property"] in measures, f


def test_generated_visuals_do_not_overlap_and_stay_on_canvas():
    base = PBI / "PBIR_Generated" / "definition" / "pages"
    for page in base.glob("page_*"):
        boxes = []
        for f in (page / "visuals").glob("*/visual.json"):
            b = json.loads(f.read_text(encoding="utf-8"))["position"]
            assert b["x"] >= 0 and b["y"] >= 0, f
            assert b["x"] + b["width"] <= 1280 and b["y"] + b["height"] <= 720, f
            boxes.append((f, b))
        for i, (fa, a) in enumerate(boxes):
            for fb, b in boxes[i + 1:]:
                apart = (a["x"] + a["width"] <= b["x"] or b["x"] + b["width"] <= a["x"]
                         or a["y"] + a["height"] <= b["y"] or b["y"] + b["height"] <= a["y"])
                assert apart, (fa, fb)


def test_offtake_expected_governed_total_matches_dashboard_data():
    """Source-side offtake (ex Reliance Brand Counter) must agree with data.js within rounding."""
    exp = json.loads((PBI / "reconciliation_expected.json").read_text(encoding="utf-8"))
    src = (ROOT / "dashboard" / "data.js").read_text(encoding="utf-8")
    data = json.loads(src[src.index("{"): src.rindex("}") + 1])
    ours = float(exp["offtake"]["governed_ex_reliance_brand_counter"]["fy_lakh"]["FY27"])
    assert abs(ours - data["offtake"]["total_fy27"]) < 0.5


def test_month_label_parser_reads_serials_and_short_forms():
    import sys
    sys.path.insert(0, str(ROOT / "scripts"))
    from powerbi_full_sources import parse_period
    assert parse_period("46113.0") == "2026-04"
    assert parse_period("Jun '26") == "2026-06"
    assert parse_period("Apr'26") == "2026-04"
    assert parse_period("Aug") is None  # no year: callers fall back to the file name


def test_model_has_parameter_and_helper_functions():
    names = {e["name"] for e in _model().get("expressions", [])}
    assert {"pRootFolder", "fnCombineFolder", "fnFYLabel"} <= names


def test_only_real_calculated_columns_exist():
    got = {(t["name"], c["name"]) for t in _model()["tables"] for c in t["columns"] if c.get("type") == "calculated"}
    assert ("Chain Master", "Channel") not in got  # a filter inside a measure, not a column
    assert ("Fact Primary Article", "TOT Method") in got
    for t, c in got:
        expr = next(x for tt in _model()["tables"] if tt["name"] == t for x in tt["columns"] if x["name"] == c)["expression"]
        assert "\n\n" not in expr and not re.search(r"(?m)^[A-Z][^=\n]*=\s*$", expr), (t, c)


def test_fy_year_columns_are_text():
    for t in _model()["tables"]:
        for c in t["columns"]:
            if c["name"] == "FY Year":
                assert c["dataType"] == "string", t["name"]


def test_offtake_alias_step_leaves_only_known_unmatched_chains():
    exp = json.loads((PBI / "reconciliation_expected.json").read_text(encoding="utf-8"))
    unmatched = set(exp["offtake_chain_master_check"]["unmatched_chains_lakh"])
    assert unmatched <= {"Centro"}, unmatched


def test_model_follows_tabular_object_model_rules():
    """Structure Tabular Editor checks on deploy: calculated columns carry no sourceColumn,
    no name is used twice in a table, relationship column types agree, sort-by and
    hierarchy columns exist, every table has a partition, no directed filter cycle."""
    m = _model()
    tables = {t["name"]: t for t in m["tables"]}
    for t in m["tables"]:
        objs = [c["name"] for c in t.get("columns", [])] + [x["name"] for x in t.get("measures", [])] \
            + [h["name"] for h in t.get("hierarchies", [])]
        assert len(objs) == len(set(objs)), t["name"]
        assert t.get("partitions"), t["name"]
        cols = {c["name"] for c in t.get("columns", [])}
        for c in t.get("columns", []):
            if c.get("type") == "calculated":
                assert "sourceColumn" not in c, (t["name"], c["name"])
            assert "dataType" in c
            if "sortByColumn" in c:
                assert c["sortByColumn"] in cols, (t["name"], c["name"])
        for h in t.get("hierarchies", []):
            assert all(l["column"] in cols for l in h.get("levels", [])), (t["name"], h["name"])
    flow = collections.defaultdict(set)
    for r in m["relationships"]:
        a = {c["name"]: c for c in tables[r["fromTable"]]["columns"]}[r["fromColumn"]]
        b = {c["name"]: c for c in tables[r["toTable"]]["columns"]}[r["toColumn"]]
        assert a["dataType"] == b["dataType"], r["name"]
        flow[r["toTable"]].add(r["fromTable"])

    state = {}

    def visit(u):
        state[u] = 1
        for w in flow[u]:
            assert state.get(w) != 1, "filter cycle through %s" % w
            if w not in state:
                visit(w)
        state[u] = 2

    for u in list(flow):
        if u not in state:
            visit(u)


def test_primary_channel_filter_and_fsn_decision_are_wired():
    names = {e["name"] for e in _model()["expressions"]}
    assert "pPrimaryChannel" in names
    pq = (PBI / "PowerQuery" / "16_Fact_PrimaryArticle.pq").read_text(encoding="utf-8")
    assert "pPrimaryChannel" in pq and "Text.Upper" in pq
    master = (PBI / "SeedData" / "Masters" / "ChainMaster.csv").read_text(encoding="utf-8")
    assert "Nykaa (FSN),Nykaa,Beauty Retail,South-2,EB2B,Yes" in master
    exp = json.loads((PBI / "reconciliation_expected.json").read_text(encoding="utf-8"))
    assert "EB2B" in exp["offtake_chain_master_check"]["by_master_channel"]
