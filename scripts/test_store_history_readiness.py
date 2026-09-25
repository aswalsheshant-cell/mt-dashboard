"""Tests for the Phase 2 Data Readiness Gate (scripts/store_history_readiness.py).

Synthetic fixtures only -- no real FY26 store x article extract exists in
this repository. These tests validate the GATE's logic so it is trustworthy
the moment a real file is supplied (docs/PHASE_2_DATA_READINESS_GATE.md),
not the (nonexistent) real data itself.
"""
import importlib
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
shr = importlib.import_module("store_history_readiness")


def _good_row(month="Apr'25", chain="DMart", code="D001", name="DMart Andheri",
              article="ART-001", units=10, nsv=100.0, state="Maharashtra", city="Mumbai"):
    return {"Month": month, "Chain": chain, "Store Code": code, "Store Name": name,
            "State": state, "City": city, "Article": article, "Units": units, "NSV": nsv}


def _frame(rows):
    return pd.DataFrame(rows)


class TestRequiredColumns:
    def test_missing_required_column_blocks(self):
        df = _frame([_good_row()]).drop(columns=["NSV"])
        report = shr.validate_store_history(df)
        assert report["verdict"] == "BLOCKED_BY_DATA_QUALITY"
        assert "NSV" in report["reason"]


class TestMonthCoverage:
    def test_full_12_months_passes(self):
        months = [f"{m}'25" if m in ("Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
                  else f"{m}'26" for m in
                  ["Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar"]]
        rows = [_good_row(month=m, code=f"D{i:03d}") for i, m in enumerate(months)]
        df = _frame(rows)
        report = shr.validate_store_history(df)
        month_check = next(c for c in report["checks"] if c["check"] == "month_coverage")
        assert month_check["status"] == "PASS"
        assert month_check["months_present_count"] == 12

    def test_partial_coverage_warns_not_blocks(self):
        df = _frame([_good_row(month="Apr'25"), _good_row(month="May'25", code="D002")])
        report = shr.validate_store_history(df)
        month_check = next(c for c in report["checks"] if c["check"] == "month_coverage")
        assert month_check["status"] == "WARN"
        assert report["verdict"] == "READY_WITH_GOVERNED_EXCEPTIONS"


class TestDuplicateGrain:
    def test_duplicate_month_chain_store_article_flagged(self):
        df = _frame([_good_row(), _good_row()])  # identical row twice
        report = shr.validate_store_history(df)
        dup_check = next(c for c in report["checks"] if c["check"] == "duplicate_grain")
        assert dup_check["status"] == "WARN"
        assert dup_check["duplicate_row_count"] == 2

    def test_no_duplicates_passes(self):
        df = _frame([_good_row(code="D001"), _good_row(code="D002")])
        report = shr.validate_store_history(df)
        dup_check = next(c for c in report["checks"] if c["check"] == "duplicate_grain")
        assert dup_check["status"] == "PASS"


class TestStoreIdentityConflicts:
    def test_same_code_different_name_flagged(self):
        df = _frame([
            _good_row(code="D001", name="DMart Andheri"),
            _good_row(code="D001", name="DMart Bandra", article="ART-002"),
        ])
        report = shr.validate_store_history(df)
        conflict_check = next(c for c in report["checks"] if c["check"] == "store_identity_conflicts")
        assert conflict_check["status"] == "WARN"
        assert conflict_check["conflicts"]


class TestMissingIdentifiers:
    def test_blank_store_code_flagged(self):
        df = _frame([_good_row(code="")])
        report = shr.validate_store_history(df)
        mi = next(c for c in report["checks"] if c["check"] == "missing_identifiers")
        assert mi["status"] == "WARN"
        assert mi["missing_counts"]["Store Code"] == 1


class TestFinancialValues:
    def test_negative_nsv_reported_not_blocked(self):
        """Negative NSV (returns/credit notes) is real, per PR #167's own
        precedent -- must be visible, not a hard failure."""
        df = _frame([_good_row(nsv=-50.0)])
        report = shr.validate_store_history(df)
        fv = next(c for c in report["checks"] if c["check"] == "financial_values")
        assert fv["negative_nsv_count"] == 1
        assert report["verdict"] != "BLOCKED_BY_DATA_QUALITY"

    def test_non_numeric_nsv_warns(self):
        df = _frame([_good_row(nsv="not_a_number")])
        report = shr.validate_store_history(df)
        fv = next(c for c in report["checks"] if c["check"] == "financial_values")
        assert fv["non_numeric_nsv_count"] == 1
        assert fv["status"] == "WARN"


class TestNanInfinity:
    def test_infinite_value_fails_hard(self):
        df = _frame([_good_row(nsv=float("inf"))])
        report = shr.validate_store_history(df)
        assert report["verdict"] == "BLOCKED_BY_DATA_QUALITY"
        ni = next(c for c in report["checks"] if c["check"] == "nan_infinity")
        assert ni["status"] == "FAIL"
        assert ni["infinity_count"] == 1


class TestMissingAsZero:
    def test_missing_and_real_zero_counted_separately(self):
        df = _frame([_good_row(nsv=None), _good_row(nsv=0.0, code="D002")])
        report = shr.validate_store_history(df)
        maz = next(c for c in report["checks"] if c["check"] == "missing_as_zero_treatment")
        assert maz["genuinely_missing_nsv_rows"] == 1
        assert maz["real_zero_nsv_rows"] == 1


class TestSourceTotalReconciliation:
    def test_no_control_total_is_not_checked_not_assumed_pass(self):
        df = _frame([_good_row()])
        report = shr.validate_store_history(df, control_total=None)
        rec = next(c for c in report["checks"] if c["check"] == "source_total_reconciliation")
        assert rec["status"] == "NOT_CHECKED"

    def test_matching_control_total_passes(self):
        df = _frame([_good_row(nsv=100.0), _good_row(nsv=100.0, code="D002")])
        report = shr.validate_store_history(df, control_total=200.0)
        rec = next(c for c in report["checks"] if c["check"] == "source_total_reconciliation")
        assert rec["status"] == "PASS"

    def test_mismatched_control_total_warns(self):
        df = _frame([_good_row(nsv=100.0)])
        report = shr.validate_store_history(df, control_total=500.0)
        rec = next(c for c in report["checks"] if c["check"] == "source_total_reconciliation")
        assert rec["status"] == "WARN"


class TestIdentityContinuity:
    def test_no_reference_frame_is_not_checked(self):
        df = _frame([_good_row()])
        report = shr.validate_store_history(df, fy27_reference_df=None)
        ic = next(c for c in report["checks"] if c["check"] == "fy26_fy27_identity_continuity")
        assert ic["status"] == "NOT_CHECKED"

    def test_high_overlap_passes(self):
        fy26 = _frame([_good_row(code="D001"), _good_row(code="D002")])
        fy27 = _frame([_good_row(code="D001", month="Apr'26"), _good_row(code="D002", month="Apr'26")])
        report = shr.validate_store_history(fy26, fy27_reference_df=fy27)
        ic = next(c for c in report["checks"] if c["check"] == "fy26_fy27_identity_continuity")
        assert ic["status"] == "PASS"
        assert ic["overlap_pct_of_fy26"] == 100.0
        assert ic["name_match_pct_on_overlap"] == 100.0

    def test_low_overlap_warns(self):
        fy26 = _frame([_good_row(code="D001"), _good_row(code="D002")])
        fy27 = _frame([_good_row(code="X999", month="Apr'26")])
        report = shr.validate_store_history(fy26, fy27_reference_df=fy27)
        ic = next(c for c in report["checks"] if c["check"] == "fy26_fy27_identity_continuity")
        assert ic["status"] == "WARN"
        assert ic["overlap_pct_of_fy26"] == 0.0


class TestOverallVerdict:
    def test_clean_file_is_ready(self):
        months = ["Apr'25", "May'25", "Jun'25", "Jul'25", "Aug'25", "Sep'25",
                  "Oct'25", "Nov'25", "Dec'25", "Jan'26", "Feb'26", "Mar'26"]
        rows = [_good_row(month=m, code=f"D{i:03d}") for i, m in enumerate(months)]
        df = _frame(rows)
        report = shr.validate_store_history(df)
        assert report["verdict"] == "READY"
        assert report["hard_fail_count"] == 0
        assert report["warning_count"] == 0


class TestCrosswalkBuilder:
    def test_exact_code_match_high_confidence_auto_confirmed(self):
        fy26 = _frame([_good_row(code="D001", state="Maharashtra", city="Mumbai")])
        fy27 = _frame([_good_row(code="D001", month="Apr'26", state="Maharashtra", city="Mumbai")])
        rows = shr.build_crosswalk_candidates(fy26, fy27)
        assert len(rows) == 1
        assert rows[0]["Match_Method"] == "EXACT_CODE_MATCH"
        assert rows[0]["Match_Confidence"] == "HIGH"
        assert rows[0]["Review_Status"] == "AUTO_CONFIRMED"

    def test_exact_code_match_conflicting_geography_is_medium_pending(self):
        fy26 = _frame([_good_row(code="D001", state="Maharashtra", city="Mumbai")])
        fy27 = _frame([_good_row(code="D001", month="Apr'26", state="Karnataka", city="Bengaluru")])
        rows = shr.build_crosswalk_candidates(fy26, fy27)
        assert rows[0]["Match_Confidence"] == "MEDIUM"
        assert rows[0]["Review_Status"] == "PENDING_REVIEW"

    def test_name_match_when_code_changed(self):
        fy26 = _frame([_good_row(code="D001", name="DMart Andheri West")])
        fy27 = _frame([_good_row(code="D999", name="dmart andheri west", month="Apr'26")])
        rows = shr.build_crosswalk_candidates(fy26, fy27)
        assert rows[0]["Match_Method"] == "NORMALIZED_NAME_MATCH"
        assert rows[0]["Match_Confidence"] == "MEDIUM"
        # Never auto-confirmed below HIGH confidence.
        assert rows[0]["Review_Status"] == "PENDING_REVIEW"

    def test_unmatched_stores_on_both_sides_never_dropped(self):
        """Both the FY26 store with no FY27 counterpart AND the FY27 store
        with no FY26 counterpart must appear -- an earlier version of the
        builder only walked the FY26 side, so a store opened in FY27 was
        silently invisible rather than flagged NEW_STORE."""
        fy26 = _frame([_good_row(code="D001", name="Ghost Store")])
        fy27 = _frame([_good_row(code="D999", name="Completely Different", month="Apr'26")])
        rows = shr.build_crosswalk_candidates(fy26, fy27)
        assert len(rows) == 2
        fy26_side = next(r for r in rows if r["FY26_Store_Code"] == "D001")
        fy27_side = next(r for r in rows if r["FY27_Store_Code"] == "D999")
        assert fy26_side["Match_Method"] == "MANUAL_REVIEW"
        assert fy26_side["Cohort_Status"] == "UNMATCHED_STORE"
        assert fy26_side["FY27_Store_Code"] is None
        assert fy27_side["Match_Method"] == "MANUAL_REVIEW"
        assert fy27_side["Cohort_Status"] == "NEW_STORE"
        assert fy27_side["FY26_Store_Code"] is None

    def test_no_fuzzy_match_is_ever_auto_confirmed(self):
        """Governance invariant from docs/STORE_IDENTITY_GOVERNANCE.md: no
        row below HIGH confidence may ever be AUTO_CONFIRMED."""
        fy26 = _frame([
            _good_row(code="D001", name="DMart Andheri West", state="Maharashtra", city="Mumbai"),
            _good_row(code="D002", name="Store With No Match", article="ART-002"),
        ])
        fy27 = _frame([
            _good_row(code="D001", name="DMart Andheri West", state="Karnataka", city="Bengaluru", month="Apr'26"),
        ])
        rows = shr.build_crosswalk_candidates(fy26, fy27)
        low_or_medium = [r for r in rows if r["Match_Confidence"] != "HIGH"]
        assert low_or_medium
        assert all(r["Review_Status"] != "AUTO_CONFIRMED" for r in low_or_medium)

    def test_comparable_store_cohort_status(self):
        fy26 = _frame([_good_row(code="D001", state="Maharashtra", city="Mumbai")])
        fy27 = _frame([_good_row(code="D001", month="Apr'26", state="Maharashtra", city="Mumbai")])
        rows = shr.build_crosswalk_candidates(fy26, fy27)
        assert rows[0]["Cohort_Status"] == "COMPARABLE_STORE"

    def test_new_store_never_calculated_as_comparable(self):
        """New stores must be excluded from SSG, per docs/PHASE_2_DATA_READINESS_GATE.md
        -- confirmed here at the cohort-classification level, not left to the
        (not-yet-built) cohort engine to remember on its own."""
        fy26 = _frame([_good_row(code="D001")])
        fy27 = _frame([_good_row(code="D001", month="Apr'26"), _good_row(code="D002", name="Brand New Store", month="Apr'26")])
        rows = shr.build_crosswalk_candidates(fy26, fy27)
        new_store = next(r for r in rows if r["FY27_Store_Code"] == "D002")
        assert new_store["Cohort_Status"] == "NEW_STORE"
        assert new_store["Cohort_Status"] != "COMPARABLE_STORE"

    def test_ambiguous_match_stays_blocked_for_review(self):
        """A name-based match (lower confidence than an exact code match)
        must land in BLOCKED_FOR_REVIEW, never auto-resolved into either
        COMPARABLE_STORE or UNMATCHED_STORE on its own."""
        fy26 = _frame([_good_row(code="D777", name="Prince Anwar Shah Road")])
        fy27 = _frame([_good_row(code="D888", name="prince anwar shah road", month="Apr'26")])
        rows = shr.build_crosswalk_candidates(fy26, fy27)
        ambiguous = next(r for r in rows if r["FY26_Store_Code"] == "D777")
        assert ambiguous["Cohort_Status"] == "BLOCKED_FOR_REVIEW"
        assert ambiguous["Match_Confidence"] != "HIGH"

    def test_chain_migration_never_matched_across_chains(self):
        """A store moving from one chain to another between years must
        never be silently matched across the chain boundary -- Chain is
        part of the cohort key by design (docs/STORE_IDENTITY_GOVERNANCE.md).
        It surfaces as an UNMATCHED_STORE on the old chain and a NEW_STORE
        on the new chain, which is honest (the crosswalk cannot know it's
        the same physical site without an explicit chain-provided mapping),
        not a data-quality bug in this validator."""
        fy26 = _frame([_good_row(chain="Chain A", code="S001", name="High Street Store")])
        fy27 = _frame([_good_row(chain="Chain B", code="S001", name="High Street Store", month="Apr'26")])
        rows = shr.build_crosswalk_candidates(fy26, fy27)
        assert len(rows) == 2
        chain_a_row = next(r for r in rows if r["Chain"] == "Chain A")
        chain_b_row = next(r for r in rows if r["Chain"] == "Chain B")
        assert chain_a_row["Cohort_Status"] == "UNMATCHED_STORE"
        assert chain_b_row["Cohort_Status"] == "NEW_STORE"


class TestCohortAndMatchMethodCounts:
    def test_cohort_counts_tally_correctly(self):
        fy26 = _frame([_good_row(code="D001"), _good_row(code="D002", name="Closing Soon", article="ART-002")])
        fy27 = _frame([_good_row(code="D001", month="Apr'26"), _good_row(code="D003", name="Brand New", month="Apr'26")])
        rows = shr.build_crosswalk_candidates(fy26, fy27)
        counts = shr.cohort_counts(rows)
        assert counts.get("COMPARABLE_STORE") == 1
        assert counts.get("UNMATCHED_STORE") == 1
        assert counts.get("NEW_STORE") == 1
        assert sum(counts.values()) == len(rows)

    def test_match_method_counts_tally_correctly(self):
        fy26 = _frame([_good_row(code="D001")])
        fy27 = _frame([_good_row(code="D001", month="Apr'26")])
        rows = shr.build_crosswalk_candidates(fy26, fy27)
        counts = shr.match_method_counts(rows)
        assert counts.get("EXACT_CODE_MATCH") == 1


class TestDuplicateStoreIdCheck:
    def test_reports_distinct_store_months_without_blocking(self):
        df = _frame([_good_row(code="D001", article="ART-001"), _good_row(code="D001", article="ART-002")])
        report = shr.validate_store_history(df)
        dsi = next(c for c in report["checks"] if c["check"] == "duplicate_store_ids")
        assert dsi["status"] == "PASS"
        assert dsi["distinct_store_months"] == 1


class TestQCArtifactHelpers:
    def test_checksum_is_deterministic(self, tmp_path):
        f = tmp_path / "sample.csv"
        f.write_text("Month,Chain\nApr'25,DMart\n")
        c1 = shr.compute_checksum(f)
        c2 = shr.compute_checksum(f)
        assert c1 == c2
        assert len(c1) == 64  # sha256 hex digest length

    def test_checksum_changes_with_content(self, tmp_path):
        f1 = tmp_path / "a.csv"
        f2 = tmp_path / "b.csv"
        f1.write_text("Month,Chain\nApr'25,DMart\n")
        f2.write_text("Month,Chain\nMay'25,DMart\n")
        assert shr.compute_checksum(f1) != shr.compute_checksum(f2)
