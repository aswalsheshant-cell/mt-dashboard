"""Tests for data_quality_reconciliation_block() -- Phase 3 of the Analytical
Integrity work (PR #155). Synthetic data only; no repo files are read except
the real, tracked PowerBI/SeedData/Masters/CategoryMaster.csv (read-only) and
config/data_source_registry.yml (read-only, text substring check).

Covers: complete data, a missing required value, a duplicate business key
(true duplicate, and the false-positive a too-coarse key would produce),
an invalid value (EAN format, including the known float-artifact suffix),
an inconsistent mapping, a missing reporting period (timeliness lag),
reconciliation pass/gap reuse of existing governed fields, a threshold not
configured, and an empty dataset.
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import build_dashboard_data as bdd  # noqa: E402


def _row(month="April", fy="FY27", channel="MT", zone="West", state="Maharashtra",
         chain="DMart", brand="Mamaearth", category="Face", subcategory="Face Wash",
         rng="Vitamin C", packsize="100.0", article="Test Article", ean="8901030123456.0"):
    return {"Month": month, "FY": fy, "Channel": channel, "Zone": zone, "State": state,
            "Chain": chain, "Brand": brand, "Category": category, "SubCategory": subcategory,
            "Range": rng, "PackSize": packsize, "Article": article, "EAN": ean,
            "NSV": 10.0, "MRP": 20.0, "Qty": 5}


def test_complete_data_no_issues():
    data = {"detail_records": [_row(), _row(month="May", state="Gujarat")],
            "detail_meta": {"value_coverage_pct": 100.0}}
    dq, recon, issues = bdd.data_quality_reconciliation_block(data)
    assert dq["dimensions"]["completeness"]["fields"]["Month"]["missing"] == 0
    assert not [i for i in issues if i["dimension"] == "completeness"]


def test_missing_required_value_flagged():
    data = {"detail_records": [_row(), _row(category=None)],
            "detail_meta": {"value_coverage_pct": 100.0}}
    dq, recon, issues = bdd.data_quality_reconciliation_block(data)
    assert dq["dimensions"]["completeness"]["fields"]["Category"]["missing"] == 1
    hit = [i for i in issues if i["issue_id"] == "completeness_category"]
    assert len(hit) == 1 and hit[0]["count"] == 1


def test_true_duplicate_business_key_detected():
    r = _row()
    data = {"detail_records": [r, dict(r)], "detail_meta": {}}
    dq, recon, issues = bdd.data_quality_reconciliation_block(data)
    assert dq["dimensions"]["uniqueness"]["duplicate_rows"] == 1
    assert any(i["issue_id"] == "uniqueness_duplicate_rows" for i in issues)


def test_different_state_is_not_a_false_positive_duplicate():
    """Regression: an earlier version of this check used a coarser business
    key (no State/SubCategory/Range/PackSize) and flagged legitimate
    per-state rows as duplicates. The key must be the full dimension grain."""
    a = _row(state="Maharashtra")
    b = _row(state="Gujarat")
    data = {"detail_records": [a, b], "detail_meta": {}}
    dq, recon, issues = bdd.data_quality_reconciliation_block(data)
    assert dq["dimensions"]["uniqueness"]["duplicate_rows"] == 0
    assert not [i for i in issues if i["issue_id"] == "uniqueness_duplicate_rows"]


def test_invalid_ean_format_flagged():
    data = {"detail_records": [_row(ean="not-an-ean")], "detail_meta": {}}
    dq, recon, issues = bdd.data_quality_reconciliation_block(data)
    assert dq["dimensions"]["validity"]["invalid_ean_format"] == 1
    assert any(i["issue_id"] == "validity_ean_format" for i in issues)


def test_valid_ean_with_float_artifact_suffix_not_flagged():
    """detail_records serializes EAN as a float-string ("8901030123456.0") --
    a pandas artifact already normalised elsewhere in this repo for
    Cust-SAP Code. A structurally valid EAN carrying that suffix must not be
    misreported as invalid."""
    data = {"detail_records": [_row(ean="8901030123456.0")], "detail_meta": {}}
    dq, recon, issues = bdd.data_quality_reconciliation_block(data)
    assert dq["dimensions"]["validity"]["invalid_ean_format"] == 0


def test_inconsistent_ean_taxonomy_flagged():
    """Same EAN, different Category across rows -- a physical SKU's taxonomy
    should not change month to month (the same principle already established
    by detail_records_real()'s own EAN backfill logic)."""
    a = _row(ean="8901030123456.0", category="Face")
    b = _row(ean="8901030123456.0", category="Hair", month="May")
    data = {"detail_records": [a, b], "detail_meta": {}}
    dq, recon, issues = bdd.data_quality_reconciliation_block(data)
    assert dq["dimensions"]["consistency"]["inconsistent_eans"] == 1
    assert any(i["issue_id"] == "consistency_ean_taxonomy" for i in issues)


def test_missing_reporting_period_lag_detected():
    data = {"detail_records": [_row()],
            "detail_meta": {"fyx_primary": {"FY27": {"months_canon": ["2026-04", "2026-05"]}}},
            "offtake": {"months_fy27": ["2026-04"]}}
    dq, recon, issues = bdd.data_quality_reconciliation_block(data)
    t = dq["dimensions"]["timeliness"]
    assert t["primary_latest_month"] == "2026-05"
    assert t["offtake_latest_month"] == "2026-04"
    assert t["in_sync"] is False
    assert any(i["issue_id"] == "timeliness_primary_offtake_lag" for i in issues)


def test_reconciliation_reuses_existing_sis_field_without_recomputing():
    data = {"detail_records": [],
            "detail_meta": {"sis_reconciliation": {"FY26": {"summary": {"net_sis_value": 250.17}}},
                            "sis_gap_status": "RESOLVED (2026-07-03) -- business confirmed..."}}
    dq, recon, issues = bdd.data_quality_reconciliation_block(data)
    sis_check = next(c for c in recon["checks"] if c["check_id"] == "SIS_RECONCILIATION")
    assert sis_check["current_value"] == 250.17
    assert sis_check["status"] == "RESOLVED"


def test_reconciliation_gap_status_when_unresolved():
    data = {"detail_records": [],
            "detail_meta": {"sis_reconciliation": {"FY26": {"summary": {"net_sis_value": 1.0}}},
                            "sis_gap_status": "still under investigation"}}
    dq, recon, issues = bdd.data_quality_reconciliation_block(data)
    sis_check = next(c for c in recon["checks"] if c["check_id"] == "SIS_RECONCILIATION")
    assert sis_check["status"] == "UNRESOLVED"


def test_mapping_completeness_reuses_existing_rag_threshold():
    data = {"detail_records": [],
            "mapping_health": {"by_fy": {"FY27": {"completeness_pct": 99.9, "rag": "green"}}}}
    dq, recon, issues = bdd.data_quality_reconciliation_block(data)
    mh_check = next(c for c in recon["checks"] if c["check_id"] == "MAPPING_COMPLETENESS_COVERAGE")
    assert mh_check["status"] == "green"
    assert mh_check["green_threshold"] == 95.0 and mh_check["amber_threshold"] == 85.0


def test_target_source_lineage_gap_detected():
    """The FY2627 target file is real but, as of Phase 2, not registered in
    config/data_source_registry.yml -- this must surface as a traceable
    reconciliation finding, never silently ignored or silently fixed here."""
    data = {"detail_records": [],
            "targets": {"source": "PowerBI/SeedData/Targets/FY2627_Targets.csv"}}
    dq, recon, issues = bdd.data_quality_reconciliation_block(data)
    t_check = next(c for c in recon["checks"] if c["check_id"] == "TARGET_SOURCE_LINEAGE")
    assert t_check["status"] == "NOT_REGISTERED"
    assert any(i["issue_id"] == "reconciliation_target_source_unregistered" for i in issues)


def test_no_threshold_reports_not_configured_never_invented():
    data = {"detail_records": [_row()], "detail_meta": {}}
    dq, recon, issues = bdd.data_quality_reconciliation_block(data)
    for dim in dq["dimensions"].values():
        assert dim["threshold"] == "NOT_CONFIGURED"
        assert dim["threshold_source"] == "NOT_CONFIGURED"
        assert dim["status"] == "INFORMATIONAL"


def test_empty_dataset_does_not_raise():
    dq, recon, issues = bdd.data_quality_reconciliation_block({})
    assert dq["dimensions"]["completeness"]["records_checked"] == 0
    assert recon["checks"] == []
    assert issues == []
