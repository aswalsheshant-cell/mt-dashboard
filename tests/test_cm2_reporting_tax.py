"""Synthetic signed source-tax contract; no workbook source data."""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from cm2_reporting import build_tax_basis, tax_summary


def primary(values, asserted=True):
    frame = pd.DataFrame(values, columns=["_M", "_NSV", "_TaxLOC", "_MRP"])
    for column, value in {"_FY": "FY27", "_Chain": "Test", "_Brand": "Test",
                          "_category": "Hair", "_EAN No.": "123", "_Chan": "MT"}.items():
        frame[column] = value
    if asserted:
        frame.attrs["invoice_nsv_tax_exclusive"] = True
    return frame


def test_signed_source_and_month_weighted_rates():
    source = primary([(4, 100, 5, 170), (4, 200, 36, 390),
                      (5, 80, 14.4, 130), (5, -20, -3.6, -40)])
    rows = build_tax_basis(source)
    pd.testing.assert_frame_equal(rows[source.columns], source)
    assert rows.gst_qc_status.tolist() == ["VALID_5_PERCENT", "VALID_18_PERCENT",
                                          "VALID_18_PERCENT", "VALID_18_PERCENT"]
    summary = tax_summary(rows)
    assert (summary["nsv"], summary["tax"], summary["mrp"]) == pytest.approx((360, 51.8, 650))
    assert summary["effective_gst_pct"] == pytest.approx(100 * 51.8 / 360)
    assert summary["gst_qc_status"] == "MIXED_RATE"
    assert tax_summary(rows[rows._M == 4])["effective_gst_pct"] == pytest.approx(100 * 41 / 300)
    assert tax_summary(rows[rows._M == 5])["effective_gst_pct"] == pytest.approx(18)


def test_missing_zero_and_small_rounded_amount_are_distinct():
    rows = build_tax_basis(primary([(4, 1, None, 2), (4, 2, 0, 3),
                                    (4, .10 / 1e5, .02 / 1e5, .20 / 1e5)]))
    assert rows.gst_qc_status.tolist() == ["MISSING_TAX", "ZERO_TAX", "REVIEW_RATE_OR_BASE"]
    summary = tax_summary(rows)
    assert summary["effective_gst_pct"] is None
    assert summary["reviewed_amount"] == pytest.approx(.10 / 1e5)
    assert summary["missing_tax_nsv"] == 1
    assert summary["status_counts"] == {"MISSING_TAX": 1, "ZERO_TAX": 1, "REVIEW_RATE_OR_BASE": 1}


def test_explicit_tax_exclusive_assertion_is_required():
    rows = build_tax_basis(primary([(4, 100, 18, 200)], asserted=False))
    assert tax_summary(rows)["effective_gst_pct"] is None
    rows.attrs["invoice_nsv_tax_exclusive"] = True
    assert tax_summary(rows)["effective_gst_pct"] == 18


def test_tolerance_and_incompatible_sign_base_or_mrp():
    rows = build_tax_basis(primary([(4, 100, 18.04, 200), (4, 100, 18.2, 200),
                                    (4, 0, 1, 2), (4, -100, 18, -200),
                                    (4, 100, 18, None)]))
    assert rows.gst_qc_status.tolist() == ["VALID_18_PERCENT"] + ["REVIEW_RATE_OR_BASE"] * 4


def test_zero_tax_and_empty_or_zero_net_populations():
    assert tax_summary(build_tax_basis(primary([(4, 10, 0, 20)])))["effective_gst_pct"] == 0
    assert tax_summary(build_tax_basis(primary([])))["effective_gst_pct"] is None
    assert tax_summary(build_tax_basis(primary([(4, 10, 1.8, 20), (4, -10, -1.8, -20)])))["effective_gst_pct"] is None
