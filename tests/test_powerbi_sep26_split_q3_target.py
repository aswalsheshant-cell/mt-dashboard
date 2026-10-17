"""Static guards for the Power BI side of the Sep'26 split and the Q3 chain target.
Not Desktop-verified: they only pin the contract the M and DAX files must keep."""
import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PBI = ROOT / "PowerBI"


def test_query41_has_insert_only_approved_post_csv_patch_layer():
    m = (PBI / "PowerQuery" / "41_DistContWeights.pq").read_text(encoding="utf-8")
    assert "DistPrimaryContWeightsArticle.csv" in m
    assert '[Approval_Status] = "Approved"' in m
    assert "> ShipToLastMonth" in m                       # never touches months inside the ShipTo CSV
    assert re.search(r"PatchBNew\s*=\s*Table\.Join\([^)]*JoinKind\.LeftAnti", m, re.S)  # insert-only
    assert "CombinedBase = Table.Combine({CombinedBase0, PatchBNew})" in m


def test_patch_seed_columns_match_what_query41_reads():
    head = next(csv.reader(open(PBI / "SeedData" / "DIST" / "DistPrimaryContWeightsArticle.csv", encoding="utf-8")))
    for c in ("Ship_To_Name", "Chain_Name", "Brand", "Month", "Cont_Pct", "Approval_Status"):
        assert c in head


def test_q3_target_measures_use_divide_and_text_fallback():
    d = (PBI / "DAX" / "23_Q3_Target_Measures.dax").read_text(encoding="utf-8")
    assert "DIVIDE" in d and "not in source" in d
    assert not re.search(r"[^A-Za-z]\)\s*/\s*\[", d)      # no bare "/" division


def test_model_has_q3_table_and_measures():
    m = json.load(open(PBI / "model.bim", encoding="utf-8"))["model"]
    assert any(t["name"] == "Q3 Chain Target" for t in m["tables"])
    names = {me["name"] for t in m["tables"] for me in t.get("measures", [])}
    assert {"Q3 New Target Rs L", "Q3 Old Target Rs L", "Q3 Plan Uplift %",
            "Q3 Target Step-Up %", "Q3 Target Step-Up Text"} <= names


def test_reconciliation_expected_carries_split_and_q3_totals():
    d = json.load(open(PBI / "reconciliation_expected.json", encoding="utf-8"))
    assert d["sep26_split_patch"]["keys"] == 19
    assert d["sep26_split_patch"]["keys_not_summing_to_100"] == []
    assert abs(d["q3_chain_target"]["new_total_lakh"] - 12499.43) < 0.05
