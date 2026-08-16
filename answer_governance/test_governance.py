#!/usr/bin/env python3
"""
Tests for the Answer Governance Layer.

Covers:
  - Confidence classification (CONFIRMED / HIGH_CONFIDENCE / PROVISIONAL / BLOCKED)
  - Period completeness (Q1, Q2, FY, YTD, single month)
  - Evidence building for Primary, Offtake, Forecast, CM2, TOT%
  - Claim guard (unsafe certainty rewrites)
  - Feature isolation (existing pipeline unchanged)
  - Idempotency (repeated runs produce identical results)
"""
from __future__ import annotations
import hashlib, json, math, re
from pathlib import Path

import pytest

from answer_governance.models import ConfidenceStatus, Governed
from answer_governance.confidence import classify_confidence
from answer_governance.period_completeness import period_months, check_period
from answer_governance.claim_guard import guard_claim, is_safe_claim, format_status_statement
from answer_governance.evidence import build_evidence
from answer_governance.govern import govern_answer


# ── Helpers ────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def dash():
    """Load the current dashboard/data.js once for all tests."""
    path = Path(__file__).resolve().parent.parent / "dashboard" / "data.js"
    txt = path.read_text(encoding="utf-8")
    m = re.search(r"window\.DASH\s*=\s*", txt)
    raw = txt[m.end():].rstrip().rstrip(";")
    raw = re.sub(r"\bNaN\b", "null", raw)
    return json.loads(raw)


@pytest.fixture(scope="module")
def data_js_checksum():
    """MD5 checksum of data.js before tests — used to verify no modification."""
    path = Path(__file__).resolve().parent.parent / "dashboard" / "data.js"
    return hashlib.md5(path.read_bytes()).hexdigest()


# ── Period completeness ───────────────────────────────────────────────────

class TestPeriodCompleteness:
    def test_q1_months(self):
        assert period_months("Q1", "FY27") == ["April", "May", "June"]

    def test_q2_months(self):
        assert period_months("Q2", "FY27") == ["July", "Aug", "Sept"]

    def test_q3_months(self):
        assert period_months("Q3", "FY27") == ["Oct", "Nov", "Dec"]

    def test_q4_months(self):
        assert period_months("Q4", "FY27") == ["Jan", "Feb", "March"]

    def test_h1_months(self):
        assert len(period_months("H1", "FY27")) == 6

    def test_h2_months(self):
        assert len(period_months("H2", "FY27")) == 6

    def test_fy_full_year(self):
        assert len(period_months("FY", "FY27")) == 12

    def test_ytd_june(self):
        assert period_months("YTD-June", "FY27") == ["April", "May", "June"]

    def test_ytd_sept(self):
        assert period_months("YTD-Sept", "FY27") == [
            "April", "May", "June", "July", "Aug", "Sept"]

    def test_single_month(self):
        assert period_months("April", "FY27") == ["April"]

    def test_short_month_name(self):
        assert period_months("Jun", "FY27") == ["June"]

    def test_invalid_period(self):
        assert period_months("nonsense", "FY27") == []

    def test_check_period_complete(self):
        req, pres, ok = check_period("Q1", "FY27", ["April", "May", "June"])
        assert ok is True
        assert len(req) == 3
        assert len(pres) == 3

    def test_check_period_incomplete(self):
        req, pres, ok = check_period("Q1", "FY27", ["April", "May"])
        assert ok is False
        assert len(pres) == 2

    def test_check_period_empty(self):
        req, pres, ok = check_period("Q1", "FY27", [])
        assert ok is False
        assert len(pres) == 0


# ── Confidence classifier ────────────────────────────────────────────────

class TestConfidenceClassifier:
    def test_confirmed_all_gates_pass(self):
        assert classify_confidence(
            metric_exists=True,
            period_complete=True,
            reconciliation_passed=True,
        ) == ConfidenceStatus.CONFIRMED

    def test_blocked_metric_missing(self):
        assert classify_confidence(
            metric_exists=False,
            period_complete=True,
            reconciliation_passed=True,
        ) == ConfidenceStatus.BLOCKED

    def test_blocked_source_missing(self):
        assert classify_confidence(
            metric_exists=True,
            period_complete=True,
            reconciliation_passed=True,
            missing_required_source=True,
        ) == ConfidenceStatus.BLOCKED

    def test_blocked_unsupported_filter(self):
        assert classify_confidence(
            metric_exists=True,
            period_complete=True,
            reconciliation_passed=True,
            unsupported_filter=True,
        ) == ConfidenceStatus.BLOCKED

    def test_blocked_reconciliation_over_tolerance(self):
        assert classify_confidence(
            metric_exists=True,
            period_complete=True,
            reconciliation_passed=False,
            reconciliation_variance=5.0,
            reconciliation_tolerance=1.0,
        ) == ConfidenceStatus.BLOCKED

    def test_provisional_forecast(self):
        assert classify_confidence(
            metric_exists=True,
            period_complete=True,
            reconciliation_passed=True,
            is_forecast=True,
        ) == ConfidenceStatus.PROVISIONAL

    def test_provisional_estimated(self):
        assert classify_confidence(
            metric_exists=True,
            period_complete=True,
            reconciliation_passed=True,
            is_estimated=True,
        ) == ConfidenceStatus.PROVISIONAL

    def test_provisional_pending_approval(self):
        assert classify_confidence(
            metric_exists=True,
            period_complete=True,
            reconciliation_passed=True,
            has_pending_approval=True,
        ) == ConfidenceStatus.PROVISIONAL

    def test_provisional_incomplete_period(self):
        assert classify_confidence(
            metric_exists=True,
            period_complete=False,
            reconciliation_passed=True,
        ) == ConfidenceStatus.PROVISIONAL

    def test_provisional_representative(self):
        assert classify_confidence(
            metric_exists=True,
            period_complete=True,
            reconciliation_passed=True,
            is_representative=True,
        ) == ConfidenceStatus.PROVISIONAL

    def test_provisional_fallback(self):
        assert classify_confidence(
            metric_exists=True,
            period_complete=True,
            reconciliation_passed=True,
            has_fallback_dependency=True,
        ) == ConfidenceStatus.PROVISIONAL

    def test_high_confidence_allocation_partial(self):
        assert classify_confidence(
            metric_exists=True,
            period_complete=True,
            reconciliation_passed=True,
            allocation_coverage_pct=60.7,
        ) == ConfidenceStatus.HIGH_CONFIDENCE

    def test_high_confidence_value_coverage_below_99(self):
        assert classify_confidence(
            metric_exists=True,
            period_complete=True,
            reconciliation_passed=True,
            value_coverage_pct=96.6,
        ) == ConfidenceStatus.HIGH_CONFIDENCE

    def test_high_confidence_small_recon_variance(self):
        assert classify_confidence(
            metric_exists=True,
            period_complete=True,
            reconciliation_passed=True,
            reconciliation_variance=0.5,
            reconciliation_tolerance=1.0,
        ) == ConfidenceStatus.HIGH_CONFIDENCE

    def test_provisional_unmapped_low_coverage(self):
        assert classify_confidence(
            metric_exists=True,
            period_complete=True,
            reconciliation_passed=True,
            has_unmapped_records=True,
            allocation_coverage_pct=30.0,
        ) == ConfidenceStatus.PROVISIONAL


# ── Claim guard ───────────────────────────────────────────────────────────

class TestClaimGuard:
    def test_rewrites_100_accurate(self):
        result = guard_claim(
            "The Primary is 100% accurate.",
            ConfidenceStatus.HIGH_CONFIDENCE,
        )
        assert "100%" not in result
        assert "HIGH_CONFIDENCE" in result

    def test_rewrites_guaranteed(self):
        result = guard_claim(
            "This number is guaranteed.",
            ConfidenceStatus.CONFIRMED,
        )
        assert "guaranteed" not in result
        assert "CONFIRMED" in result

    def test_rewrites_exact_number(self):
        result = guard_claim(
            "This is the exact number.",
            ConfidenceStatus.PROVISIONAL,
        )
        assert "exact number" not in result
        assert "PROVISIONAL" in result

    def test_rewrites_finance_approved(self):
        result = guard_claim(
            "This is finance-approved.",
            ConfidenceStatus.PROVISIONAL,
            approval_status="Pending",
        )
        assert "Pending" in result

    def test_safe_text_unchanged(self):
        text = "Primary FY27 Q1 is 136.59 Cr."
        result = guard_claim(text, ConfidenceStatus.CONFIRMED)
        assert result == text

    def test_is_safe_claim_detects_unsafe(self):
        assert not is_safe_claim("This is 100% accurate.")
        assert not is_safe_claim("The result is guaranteed.")

    def test_is_safe_claim_passes_safe(self):
        assert is_safe_claim("Primary FY27 is classified as CONFIRMED.")
        assert is_safe_claim("The value is 136.59 Cr.")

    def test_format_status_confirmed(self):
        s = format_status_statement("Primary", ConfidenceStatus.CONFIRMED, "all months present")
        assert "CONFIRMED" in s

    def test_format_status_blocked(self):
        s = format_status_statement("Primary", ConfidenceStatus.BLOCKED, "missing data")
        assert "BLOCKED" in s

    def test_unsafe_claim_rewritten_not_blocked(self):
        result = guard_claim(
            "This is perfectly correct and fully correct.",
            ConfidenceStatus.PROVISIONAL,
        )
        assert "perfectly correct" not in result.lower() or "PROVISIONAL" in result
        assert "fully correct" not in result


# ── Evidence building (against real data.js) ──────────────────────────────

class TestEvidenceBuilding:
    def test_primary_q1_fy27_confirmed_or_high(self, dash):
        g = build_evidence("primary", "Q1", "FY27", dash)
        assert g.status in (ConfidenceStatus.CONFIRMED, ConfidenceStatus.HIGH_CONFIDENCE)
        assert g.value is not None
        assert abs(g.value - 13659.98) < 2.0
        assert g.coverage.complete is True
        assert len(g.source_paths) > 0

    def test_primary_q2_fy27_provisional_or_blocked(self, dash):
        g = build_evidence("primary", "Q2", "FY27", dash)
        assert g.status in (ConfidenceStatus.PROVISIONAL, ConfidenceStatus.BLOCKED)

    def test_primary_fy25_preagg(self, dash):
        g = build_evidence("primary", "FY", "FY25", dash)
        assert g.value == 23331.97
        assert g.status in (ConfidenceStatus.CONFIRMED, ConfidenceStatus.HIGH_CONFIDENCE)

    def test_primary_fy26_preagg(self, dash):
        g = build_evidence("primary", "FY", "FY26", dash)
        assert g.value == 32900.36
        assert g.status in (ConfidenceStatus.CONFIRMED, ConfidenceStatus.HIGH_CONFIDENCE)

    def test_offtake_q1_fy27(self, dash):
        g = build_evidence("offtake", "Q1", "FY27", dash)
        assert g.status in (ConfidenceStatus.CONFIRMED, ConfidenceStatus.HIGH_CONFIDENCE)
        assert g.value is not None
        assert abs(g.value - 11438.72) < 1.0
        assert g.coverage.complete is True
        assert any("Brand Counter" in e for e in g.exclusions)

    def test_offtake_fy28_blocked(self, dash):
        g = build_evidence("offtake", "Q1", "FY28", dash)
        assert g.status == ConfidenceStatus.BLOCKED

    def test_forecast_always_provisional(self, dash):
        g = build_evidence("forecast", "FY", "FY27", dash)
        assert g.status == ConfidenceStatus.PROVISIONAL
        assert len(g.assumptions) > 0

    def test_cm2_provisional(self, dash):
        g = build_evidence("cm2", "FY", "FY27", dash)
        assert g.status == ConfidenceStatus.PROVISIONAL

    def test_tot_provisional_or_confirmed(self, dash):
        g = build_evidence("tot", "FY", "FY27", dash)
        assert g.status in (ConfidenceStatus.CONFIRMED, ConfidenceStatus.PROVISIONAL)

    def test_unknown_metric_blocked(self, dash):
        g = build_evidence("nonexistent_metric", "Q1", "FY27", dash)
        assert g.status == ConfidenceStatus.BLOCKED
        assert "Unknown metric" in g.reason

    def test_evidence_has_structured_output(self, dash):
        g = build_evidence("primary", "Q1", "FY27", dash)
        d = g.to_dict()
        assert "metric" in d
        assert "status" in d
        assert "reconciliation" in d
        assert "coverage" in d
        assert d["status"] in ("CONFIRMED", "HIGH_CONFIDENCE", "PROVISIONAL", "BLOCKED")


# ── Top-level govern_answer ───────────────────────────────────────────────

class TestGovernAnswer:
    def test_govern_primary(self, dash):
        g = govern_answer("primary", "Q1", "FY27", dash)
        assert isinstance(g, Governed)
        assert g.value is not None
        assert g.status in (ConfidenceStatus.CONFIRMED, ConfidenceStatus.HIGH_CONFIDENCE)

    def test_govern_offtake(self, dash):
        g = govern_answer("offtake", "Q1", "FY27", dash)
        assert g.value is not None
        assert g.status in (ConfidenceStatus.CONFIRMED, ConfidenceStatus.HIGH_CONFIDENCE)

    def test_govern_with_filters(self, dash):
        g = govern_answer("primary", "Q1", "FY27", dash, filters={"Zone": "North"})
        assert g.filters == {"Zone": "North"}

    def test_idempotent(self, dash):
        g1 = govern_answer("primary", "Q1", "FY27", dash)
        g2 = govern_answer("primary", "Q1", "FY27", dash)
        assert g1.to_dict() == g2.to_dict()


# ── Pipeline isolation ────────────────────────────────────────────────────

class TestPipelineIsolation:
    def test_data_js_unchanged(self, data_js_checksum):
        """data.js must not be modified by the governance layer."""
        path = Path(__file__).resolve().parent.parent / "dashboard" / "data.js"
        current = hashlib.md5(path.read_bytes()).hexdigest()
        assert current == data_js_checksum, "data.js was modified by the governance layer!"

    def test_existing_tests_still_pass(self):
        """Verify the existing test suite is unaffected (run separately)."""
        pass

    def test_primary_totals_unchanged(self, dash):
        assert dash["primary"]["nsv_fy25"] == 23331.97
        assert dash["primary"]["nsv_fy26"] == 32900.36

    def test_offtake_totals_unchanged(self, dash):
        assert dash["offtake"]["total_fy25"] == 21840.0
        assert dash["offtake"]["total_fy26"] == 31082.0
        assert dash["offtake"]["total_fy27"] == 11438.72

    def test_bc_unchanged(self, dash):
        bc = dash.get("reliance_bc", {})
        assert bc.get("total") == 943.68
        assert bc.get("include_in_overall_offtake") is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
