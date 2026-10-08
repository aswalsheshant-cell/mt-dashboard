"""TDP builder: no file means NOT_SUPPLIED (never invented numbers); a file is summed correctly and duplicates are not double counted."""
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_tdp as bt  # noqa: E402


def _row(month, chain, state, art, acv, nd=40, wd=60):
    return {"Month": month, "FY Year": "26-27", "Chain": chain, "Zone": "West", "State": state, "Brand": "TestBrand", "Category": "C", "Sub-category": "S", "Pack Size": "100",
            "Article Code": art, "Article Description": art, "ACV %": acv, "AIC": 2.0, "Numeric Distribution": nd, "Weighted Distribution": wd, "Data Source Name": "unit test fixture"}


def test_no_file_is_not_supplied(tmp_path):
    (tmp_path / "_TEMPLATE_TDP_Monthly.csv").write_text("Month\n", encoding="utf-8")
    out = bt.build(tmp_path)
    assert out["status"] == "NOT_SUPPLIED" and "TDP_<Mon>_<YY>.csv" in out["needed"]


def test_shipped_tdp_js_matches_the_folder_state():
    js = (ROOT / "dashboard" / "tdp.js").read_text(encoding="utf-8")
    assert js.startswith("window.TDP=")
    assert json.loads(js[len("window.TDP="):].rstrip().rstrip(";")) == bt.build()


def test_tdp_is_sum_of_acv_and_duplicates_dropped(tmp_path):
    rows = [_row("Jul'26", "A", "X", "a1", 50), _row("Jul'26", "A", "X", "a2", 30), _row("Jul'26", "A", "X", "a2", 30),    # repeated row
            _row("Aug'26", "A", "X", "a1", 60), _row("Aug'26", "A", "X", "a2", 40)]
    pd.DataFrame(rows).to_csv(tmp_path / "TDP_Aug_26.csv", index=False)
    out = bt.build(tmp_path)
    assert out["status"] == "LOADED" and out["latest"] == "Aug'26" and out["rows_dropped_duplicate"] == 1
    by = {r["Month"]: r["tdp"] for r in out["by_month"]}
    assert by == {"Jul'26": 80.0, "Aug'26": 100.0} and out["mom_tdp_pct"] == 25.0
    assert out["by_chain"][0]["tdp"] == 100.0


def test_html_has_the_tdp_sub_view():
    html = (ROOT / "dashboard" / "index.html").read_text(encoding="utf-8")
    assert '<script src="tdp.js"></script>' in html and "renderTdp(content)" in html and "tdp:'TDP & Distribution'" in html
