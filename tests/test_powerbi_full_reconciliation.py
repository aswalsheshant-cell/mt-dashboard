"""Task 3: measure truth and source-to-dashboard reconciliation for the full report.

Static checks on the TMDL measures plus fixture tests for the reconciler. Nothing
here runs DAX; Desktop evidence is a separate step (plan Task 7).
"""
import csv
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

MEASURES = ROOT / "ModernTrade_Report.Dataset/definition/tables/_Measures.tmdl"
OFFTAKE_HEADER = ["Chain Name", "Store Type", "Site Code", "Article", "NSV", "Month", "Year"]
PRIMARY_HEADER = ["Month", "Inv. Net value(LOC)"]


def _import():
    import reconcile_powerbi_full
    return reconcile_powerbi_full


def _write_csv(path, header, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


def _offtake_rows(extra=()):
    # 60 + 40 lakh governed MT rows, 20 lakh Reliance Brand Counter (offtake only).
    return [
        ["Apollo", "Store", "S1", "A1", 60, "Aug", 2026],
        ["Wellness Forever", "Store", "S2", "A1", 40, "Aug", 2026],
        ["Reliance Retail", "Brand Counter", "S3", "A1", 20, "Aug", 2026],
        *extra,
    ]


def _dash(**overrides):
    dash = {
        "offtake": {
            "months_fy27": ["Aug-26"], "monthly_fy27": [100.0],
            "months_fy26": ["Aug-25"], "monthly_fy26": [80.0],
        },
        "detail_meta": {"fyx_primary": {"FY27": {
            "months_canon": ["Aug-26"], "monthly_canon": [50.0], "unit": "INR Lakh"}}},
        "npd": {"metrics_by_fy": {
            "FY27": {"npi_nsv": 760.15, "yoy_npi_nsv_growth_pct": -71.17,
                     "yoy_comparison_valid": False, "observed_only_launch_count": 140,
                     "yoy_caveat": "FY26 launches are observed-only"},
        }},
        "reliance_brand_counters": {"months": [], "monthly": [], "note": "not available"},
    }
    dash.update(overrides)
    return dash


@pytest.fixture
def repo(tmp_path):
    _write_csv(tmp_path / "PowerBI/RawDataFolders/Offtake_Monthly/offtake_store_article_Aug_26.csv",
               OFFTAKE_HEADER, _offtake_rows())
    # Primary source is in rupees: 5,000,000 rupees = 50 lakh.
    _write_csv(tmp_path / "PowerBI/RawDataFolders/Primary_Article_Monthly/primary_article_Aug_26.csv",
               PRIMARY_HEADER, [["Aug'26", 3000000], ["Aug'26", 2000000]])
    (tmp_path / "dashboard").mkdir()
    (tmp_path / "dashboard/data.js").write_text("window.DASH = " + json.dumps(_dash()) + ";", encoding="utf-8")
    return tmp_path


def _row(rows, metric_prefix):
    matches = [r for r in rows if r["metric"].startswith(metric_prefix)]
    assert len(matches) == 1, [r["metric"] for r in rows]
    return matches[0]


# ---------------------------------------------------------------- reconciler

def test_identical_period_nsv_matches_dashboard_in_the_same_unit(repo):
    rows = _import().reconcile_context(repo, "2026-08", {})
    offtake = _row(rows, "MT offtake NSV")
    assert offtake["unit"] == "INR_lakh"
    assert offtake["source_amount"] == pytest.approx(100.0)       # Reliance Brand Counter excluded
    assert offtake["expected_report_amount"] == pytest.approx(100.0)
    assert offtake["variance"] == pytest.approx(0.0)
    assert offtake["status"] == "MATCH"
    assert offtake["model_inr"] == pytest.approx(10_000_000)
    primary = _row(rows, "Primary NSV")
    assert primary["source_amount"] == pytest.approx(50.0)        # rupees converted once
    assert primary["status"] == "MATCH"


def test_reliance_brand_counter_is_isolated_for_offtake_only(repo):
    rows = _import().reconcile_context(repo, "2026-08", {})
    rbc = _row(rows, "Reliance Brand Counter offtake")
    assert rbc["source_amount"] == pytest.approx(20.0)
    # The dashboard audit block is empty: no comparison is invented.
    assert rbc["expected_report_amount"] is None
    assert rbc["status"] == "NO_DASHBOARD_BASELINE"
    # Primary is gross: nothing is excluded from it.
    assert "Brand Counter" not in _row(rows, "Primary NSV")["metric"].replace("(gross, no Reliance Brand Counter exclusion)", "")


def test_missing_source_month_is_blank_never_zero(repo):
    rows = _import().reconcile_context(repo, "2026-09", {})
    for row in rows:
        assert row["source_amount"] is None, row
        assert row["variance"] is None, row
    assert _row(rows, "MT offtake NSV")["status"] == "SOURCE_UNAVAILABLE"


def test_two_source_files_for_one_month_are_not_summed(repo):
    _write_csv(repo / "PowerBI/RawDataFolders/Offtake_Monthly/offtake_store_article_Aug_26_copy.csv",
               OFFTAKE_HEADER, _offtake_rows())
    offtake = _row(_import().reconcile_context(repo, "2026-08", {}), "MT offtake NSV")
    assert offtake["status"] == "DUPLICATE_SOURCE"
    assert offtake["source_amount"] is None and offtake["variance"] is None


def test_duplicate_keys_inside_a_file_are_counted_and_rows_kept(repo):
    _write_csv(repo / "PowerBI/RawDataFolders/Offtake_Monthly/offtake_store_article_Aug_26.csv",
               OFFTAKE_HEADER, _offtake_rows(extra=[["Apollo", "Store", "S1", "A1", 0.0, "Aug", 2026]]))
    offtake = _row(_import().reconcile_context(repo, "2026-08", {}), "MT offtake NSV")
    assert offtake["duplicate_key_rows"] == 1
    assert offtake["source_amount"] == pytest.approx(100.0)       # source rows are never dropped


def test_unsupported_filter_never_implies_a_filtered_result(repo):
    rows = _import().reconcile_context(repo, "2026-08", {"Chain": ["Apollo"]})
    assert rows
    for row in rows:
        assert row["status"] == "UNSUPPORTED_FILTER", row
        assert row["source_amount"] is None and row["expected_report_amount"] is None
        assert "Chain" in row["note"]


def test_partial_fiscal_year_yoy_is_suppressed(repo):
    # FY27 has 1 covered month; the dashboard's FY26 has 12.
    dash = _dash()
    dash["offtake"]["months_fy26"] = [f"M{i}-25" for i in range(12)]
    dash["offtake"]["monthly_fy26"] = [1.0] * 12
    (repo / "dashboard/data.js").write_text("window.DASH = " + json.dumps(dash) + ";", encoding="utf-8")
    yoy = _row(_import().reconcile_context(repo, "FY27", {}), "MT offtake NSV YoY")
    assert yoy["status"] == "SUPPRESSED_PARTIAL_PERIOD"
    assert yoy["expected_report_amount"] is None
    assert "1" in yoy["note"] and "12" in yoy["note"]


def test_like_for_like_months_allow_the_yoy(repo):
    yoy = _row(_import().reconcile_context(repo, "FY27", {}), "MT offtake NSV YoY")
    assert yoy["status"] == "COMPARABLE"
    assert yoy["unit"] == "pct"
    assert yoy["expected_report_amount"] == pytest.approx((100.0 - 80.0) / 80.0 * 100)


def test_observed_only_npi_is_labelled_provisional(repo):
    npi = _row(_import().reconcile_context(repo, "FY27", {}), "NPI NSV YoY")
    assert npi["status"] == "PROVISIONAL_OBSERVED_ONLY"
    assert "not confirmed" in npi["note"].lower()
    assert npi["source_amount"] is None                            # no NPI fact exists in the model
    assert npi["expected_report_amount"] == pytest.approx(-71.17)


def test_confirmed_npi_comparison_is_the_only_unlabelled_case(repo):
    dash = _dash()
    dash["npd"]["metrics_by_fy"]["FY27"].update(yoy_comparison_valid=True, observed_only_launch_count=0)
    (repo / "dashboard/data.js").write_text("window.DASH = " + json.dumps(dash) + ";", encoding="utf-8")
    npi = _row(_import().reconcile_context(repo, "FY27", {}), "NPI NSV YoY")
    assert npi["status"] == "COMPARABLE"


def test_a_month_period_has_no_npi_row(repo):
    assert not [r for r in _import().reconcile_context(repo, "2026-08", {}) if r["metric"].startswith("NPI")]


def test_bad_period_is_rejected(repo):
    with pytest.raises(ValueError):
        _import().reconcile_context(repo, "August 2026", {})


# ------------------------------------------------------------------ measures

def _measure_blocks():
    text = MEASURES.read_text(encoding="utf-8")
    parts = re.split(r"(?m)^\tmeasure ", text)[1:]
    blocks = {}
    for part in parts:
        head, _, body = part.partition("\n")
        name = head.split("=")[0].strip().strip("'")
        blocks[name] = head + "\n" + body
    return blocks


FULL_MEASURES = [
    "Primary NSV INR", "Offtake NSV INR (All)", "Reliance Brand Counter Offtake NSV INR",
    "MT Offtake NSV INR", "MT Offtake NSV INR LY Same Months", "MT Offtake YoY Comparable",
    "MT Offtake YoY Pct", "MT Offtake YoY Label", "Primary NSV INR LY Same Months",
    "Primary YoY Comparable", "Primary YoY Pct", "Primary YoY Label",
    "Primary to MT Offtake Gap INR", "Primary to MT Offtake Gap Label",
    "Offtake Duplicate Key Rows", "Offtake Key Status", "Offtake Reporting Stores",
    "Nielsen Value Share Pct", "Forecast Source Status", "Alerts Source Status",
    "NPI Source Status", "NPI YoY Label",
]


def test_every_full_report_measure_exists_once():
    text = MEASURES.read_text(encoding="utf-8")
    blocks = _measure_blocks()
    for name in FULL_MEASURES:
        assert name in blocks, f"missing measure {name}"
        assert len(re.findall(rf"(?m)^\tmeasure '?{re.escape(name)}'? *=", text)) == 1, name


def test_existing_cm2_and_coverage_measures_are_retained():
    blocks = _measure_blocks()
    for name in ("CM2 NSV", "CM2 Modeled", "CM2 Status", "CM2 Matched NSV",
                 "Fact_OfftakeSales Covered Months", "Fact_PrimaryArticle Covered Months",
                 "Offtake Source Status"):
        assert name in blocks, name


def test_no_measure_turns_missing_data_into_zero():
    blocks = _measure_blocks()
    for name in FULL_MEASURES:
        body = blocks[name]
        assert "COALESCE" not in body.upper(), name
        assert not re.search(r"ISBLANK\([^)]*\)\s*,\s*0\b", body), name
        assert not re.search(r"\+\s*0\b", body), name


def test_amount_measures_are_blank_without_source_rows():
    blocks = _measure_blocks()
    for name in ("Primary NSV INR", "Offtake NSV INR (All)", "MT Offtake NSV INR",
                 "Reliance Brand Counter Offtake NSV INR"):
        assert "BLANK()" in blocks[name], name


def test_primary_is_gross_and_offtake_isolates_reliance_brand_counter_only():
    blocks = _measure_blocks()
    assert "Reliance" not in blocks["Primary NSV INR"]
    assert "Fact_PrimaryArticle" in blocks["Primary NSV INR"]
    assert 'Fact_OfftakeSales[Chain] <> "Reliance Brand Counter"' in blocks["MT Offtake NSV INR"]
    assert 'Fact_OfftakeSales[Chain] = "Reliance Brand Counter"' in blocks["Reliance Brand Counter Offtake NSV INR"]
    assert "Reliance Brand Counter" not in blocks["Offtake NSV INR (All)"]


def test_yoy_and_gap_need_equal_covered_months():
    blocks = _measure_blocks()
    for name, covered in (("MT Offtake YoY Comparable", "Fact_OfftakeSales Covered Months"),
                          ("Primary YoY Comparable", "Fact_PrimaryArticle Covered Months")):
        assert covered in blocks[name], name
        assert "DATEADD" in blocks[name], name
    assert "MT Offtake YoY Comparable" in blocks["MT Offtake YoY Pct"]
    assert "Primary YoY Comparable" in blocks["Primary YoY Pct"]
    gap = blocks["Primary to MT Offtake Gap INR"]
    assert "Fact_PrimaryArticle Covered Months" in gap and "Fact_OfftakeSales Covered Months" in gap


def test_ratio_measures_use_divide():
    blocks = _measure_blocks()
    for name in ("MT Offtake YoY Pct", "Primary YoY Pct", "Nielsen Value Share Pct"):
        assert "DIVIDE(" in blocks[name].upper().replace("DIVIDE (", "DIVIDE("), name


def test_missing_sources_say_unavailable_and_npi_says_provisional():
    blocks = _measure_blocks()
    for name in ("Forecast Source Status", "Alerts Source Status", "NPI Source Status"):
        assert "Unavailable" in blocks[name], name
    label = blocks["NPI YoY Label"]
    assert "Provisional" in label and "not confirmed" in label.lower()


def test_new_measures_keep_the_tmdl_indentation_that_desktop_accepts():
    # Desktop read formatString as part of the DAX when properties were over-indented.
    for name in FULL_MEASURES:
        block = _measure_blocks()[name]
        lines = block.splitlines()[1:]
        for line in lines:
            if re.match(r"\s*(displayFolder|formatString|description):", line):
                assert re.match(r"^\t\t[a-zA-Z]", line), f"{name}: property indentation {line!r}"
