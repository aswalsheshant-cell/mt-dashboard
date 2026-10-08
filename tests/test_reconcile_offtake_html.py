import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from reconcile_offtake_html import reconcile


def _file(month, value):
    return {
        "source_family": "Offtake_Monthly",
        "path": f"PowerBI/RawDataFolders/Offtake_Monthly/offtake_store_article_{month}.csv",
        "governed_raw_sum": str(value),
    }


def test_same_month_same_metric_uses_lakh_and_reporting_tolerance():
    report = {"files": [_file("Apr_26", "3588.5067737815"), _file("Jul_26", "3621.4662053933")]}
    html = {"offtake": {"months_fy27": ["Apr-26", "Jul-26"], "monthly_fy27": [3588.51, 3621.47]}}
    result = reconcile(report, html)
    assert [x["status"] for x in result["months"]] == ["MATCH", "MATCH"]
    assert result["all_match"] is True
    assert result["months"][0]["difference_lakh"] == "-0.0032262185"


def test_missing_html_month_is_not_comparable_and_never_zero():
    result = reconcile({"files": [_file("Aug_26", "3975.12")]}, {"offtake": {"months_fy27": [], "monthly_fy27": []}})
    assert result["months"][0]["status"] == "NOT_COMPARABLE"
    assert result["months"][0]["html_lakh"] is None
    assert result["all_match"] is False


def test_difference_and_duplicate_source_fail_closed():
    html = {"offtake": {"months_fy27": ["Jul-26"], "monthly_fy27": [4000]}}
    assert reconcile({"files": [_file("Jul_26", "3621.46")]}, html)["months"][0]["status"] == "MISMATCH"
    assert reconcile({"files": [_file("Jul_26", "1"), _file("Jul_26", "2")]}, html)["months"][0]["status"] == "DUPLICATE_SOURCE"

