"""Tests for the report-only taxonomy quality profiler."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import profile_taxonomy_quality as profiler  # noqa: E402


def _fixture_records():
    return [
        {
            "FY": "FY27", "Month": "July", "Brand": "Mamaearth", "Chain": "Dmart",
            "SubCategory": None, "Range": None, "PackSize": None,
        },
        {
            "FY": "FY27", "Month": "July", "Brand": "Mamaearth", "Chain": "Dmart",
            "SubCategory": "Shampoo", "Range": "Onion", "PackSize": "250 ml",
        },
        {
            "FY": "FY26", "Month": "March", "Brand": "Aqualogica", "Chain": "Nykaa",
            "SubCategory": "", "Range": "Hydrate", "PackSize": "80 g",
        },
    ]


def test_profile_reports_literal_null_counts_and_percentages():
    report = profiler.profile_records(_fixture_records())

    assert report["row_count"] == 3
    assert report["fields"]["SubCategory"] == {
        "null_count": 2, "null_pct": 66.67, "complete_count": 1, "complete_pct": 33.33,
    }
    assert report["fields"]["Range"]["null_count"] == 1
    assert report["fields"]["PackSize"]["null_count"] == 1


def test_profile_breaks_affected_rows_down_by_business_dimensions():
    report = profiler.profile_records(_fixture_records())

    assert report["affected_row_count"] == 2
    assert report["breakdowns"]["FY"] == {"FY26": 1, "FY27": 1}
    assert report["breakdowns"]["Month"] == {"July": 1, "March": 1}
    assert report["breakdowns"]["Brand"] == {"Aqualogica": 1, "Mamaearth": 1}
    assert report["breakdowns"]["Chain"] == {"Dmart": 1, "Nykaa": 1}


def test_cli_writes_json_report_without_failing_for_nulls(tmp_path):
    data_js = tmp_path / "data.js"
    report_path = tmp_path / "taxonomy_quality_report.json"
    data_js.write_text(
        "window.DASH = " + json.dumps({"detail_records": _fixture_records()}) + ";\n",
        encoding="utf-8",
    )

    result = profiler.main(["--data", str(data_js), "--json-out", str(report_path)])

    assert result == 0
    saved = json.loads(report_path.read_text(encoding="utf-8"))
    assert saved["status"] == "ADVISORY"
    assert saved["fields"]["SubCategory"]["null_count"] == 2
