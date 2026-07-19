"""Tests for the Output Trust and Release Control layer
(agent/mtagent/validators/release_gate.py). The 7 proofs required by
AI_LEVERAGE_AND_JUDGMENT.md's release-gate extension, each against real
module behavior, not asserted claims.
"""
import tempfile
import unittest
from pathlib import Path

from mtagent.validators import release_gate as rg
from tests._xlsx_fixture_writer import Sheet, write_xlsx


def _clean_checklist() -> rg.ReleaseChecklist:
    return rg.ReleaseChecklist(
        source_validated=True, business_rules_applied=True, totals_reconciled=True,
        period_status_confirmed=True, mappings_approved=True, exceptions_disclosed=True,
        output_visually_checked=True, version_and_timestamp_added=True,
        confidentiality_level_confirmed=True,
    )


class TestUnreconciledFileCannotBeShared(unittest.TestCase):
    """Proof 1: an unreconciled file cannot be shared, even with human approval."""

    def test_totals_not_reconciled_blocks_approval_even_when_human_approves(self):
        checklist = _clean_checklist()
        checklist.totals_reconciled = False
        status, reasons = rg.evaluate_release(checklist, human_approved=True)
        self.assertEqual(status, rg.DRAFT)
        self.assertIn("totals_reconciled", reasons)


class TestPartialMonthCannotBeClosed(unittest.TestCase):
    """Proof 2: a partial month cannot be presented as a closed month."""

    def test_period_status_not_confirmed_blocks_release(self):
        checklist = _clean_checklist()
        checklist.period_status_confirmed = False
        status, reasons = rg.evaluate_release(checklist, human_approved=True)
        self.assertEqual(status, rg.DRAFT)
        self.assertIn("period_status_confirmed", reasons)

    def test_business_validation_period_completeness_feeds_the_same_conclusion(self):
        from mtagent.validators import business_validation as bv
        check = bv.period_completeness_check("june26", is_partial_period=True, treated_as_closed=True)
        self.assertFalse(check.passed)


class TestFactWithoutEvidenceIsRejected(unittest.TestCase):
    """Proof 3: a fact without evidence is rejected."""

    def test_fact_with_no_evidence_rejected(self):
        claim = rg.Claim(statement="Apollo Healthco is fully absorbed into Apollo.",
                          kind=rg.FACT, evidence=[])
        ok, reason = rg.validate_claim(claim)
        self.assertFalse(ok)
        self.assertIn("no supporting evidence", reason)

    def test_fact_with_evidence_accepted(self):
        claim = rg.Claim(statement="Apollo Healthco is fully absorbed into Apollo.",
                          kind=rg.FACT,
                          evidence=["785L secondary NSV remapped", "zero residual Apollo Healthco rows",
                                    "total NSV unchanged"],
                          confidence=rg.HIGH)
        ok, reason = rg.validate_claim(claim)
        self.assertTrue(ok)

    def test_inference_without_evidence_also_rejected(self):
        claim = rg.Claim(statement="The increase is SKU-driven.", kind=rg.INFERENCE, evidence=[])
        ok, _ = rg.validate_claim(claim)
        self.assertFalse(ok)

    def test_recommendation_does_not_require_evidence(self):
        claim = rg.Claim(statement="Prioritize replenishment for these SKUs.", kind=rg.RECOMMENDATION)
        ok, _ = rg.validate_claim(claim)
        self.assertTrue(ok)


class TestRedactionScanNeverCrashesOnAnUnreadableFile(unittest.TestCase):
    """The scan is pure stdlib (no openpyxl dependency) -- it must still
    never crash and never silently report 'clean' for a file it couldn't
    actually parse (missing file, not a real xlsx zip, etc.)."""

    def test_nonexistent_file_returns_explicit_unscanned_result(self):
        clean, issues = rg.redaction_scan("/nonexistent/whatever.xlsx")
        self.assertFalse(clean)
        self.assertTrue(issues)

    def test_not_a_zip_file_returns_explicit_unscanned_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "not_really_xlsx.xlsx"
            path.write_text("this is plain text, not a zip", encoding="utf-8")
            clean, issues = rg.redaction_scan(path)
            self.assertFalse(clean)
            self.assertTrue(issues)


class TestConfidentialHiddenSheetBlocksSharing(unittest.TestCase):
    """Proof 4: a confidential hidden sheet blocks sharing -- real xlsx scan,
    built with a pure-stdlib fixture writer (no openpyxl needed either way)."""

    def test_hidden_sheet_with_confidential_data_is_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "MT_Leadership_Deck_Data.xlsx"
            visible = Sheet("Summary")
            visible.set("A1", "NSV")
            visible.set("B1", 12500000)
            hidden = Sheet("CM2 Assumptions", hidden=True)
            hidden.set("A1", "Cost price basis")
            write_xlsx(path, [visible, hidden])

            clean, issues = rg.redaction_scan(path)
            self.assertFalse(clean)
            self.assertTrue(any("hidden sheet" in i for i in issues))
            self.assertTrue(any("CM2 Assumptions" in i for i in issues))

            checklist = _clean_checklist()
            checklist.confidentiality_level_confirmed = clean
            status, _ = rg.evaluate_release(checklist, human_approved=True)
            self.assertEqual(status, rg.DRAFT)

    def test_clean_workbook_scans_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "Clean.xlsx"
            ws = Sheet("Sheet1")
            ws.set("A1", "NSV")
            ws.set("B1", 100)
            write_xlsx(path, [ws])
            clean, issues = rg.redaction_scan(path)
            self.assertTrue(clean)
            self.assertEqual(issues, [])

    def test_suspicious_keyword_in_cell_text_is_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "Notes.xlsx"
            ws = Sheet("Sheet1")
            ws.set("A1", "internal only -- do not share externally")
            write_xlsx(path, [ws])
            clean, issues = rg.redaction_scan(path)
            self.assertFalse(clean)
            self.assertTrue(any("internal only" in i for i in issues))

    def test_cell_comment_is_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "Commented.xlsx"
            ws = Sheet("Sheet1")
            ws.set("A1", "NSV")
            ws.set_comment("A1", "double-check this before sending")
            write_xlsx(path, [ws])
            clean, issues = rg.redaction_scan(path)
            self.assertFalse(clean)
            self.assertTrue(any("cell comment" in i for i in issues))


class TestFormulaErrorScan(unittest.TestCase):
    """formula_error_scan() -- the automatable subset of visual QC."""

    def test_error_literal_cell_is_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "Broken.xlsx"
            ws = Sheet("Sheet1")
            ws.set("A1", "NSV")
            ws.set("B1", "#REF!")
            write_xlsx(path, [ws])
            clean, issues = rg.formula_error_scan(path)
            self.assertFalse(clean)
            self.assertTrue(any("#REF!" in i for i in issues))

    def test_clean_workbook_has_no_formula_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "Clean.xlsx"
            ws = Sheet("Sheet1")
            ws.set("A1", "NSV")
            ws.set("B1", 100)
            write_xlsx(path, [ws])
            clean, issues = rg.formula_error_scan(path)
            self.assertTrue(clean)
            self.assertEqual(issues, [])


class TestVisuallyBrokenButNumericallyCorrectStaysDraft(unittest.TestCase):
    """Proof 5: a visually broken but numerically correct output remains draft --
    `output_visually_checked` is a separate checklist item from reconciliation,
    so a fully reconciled file with no visual confirmation cannot be approved."""

    def test_all_numeric_checks_pass_but_visual_check_missing_stays_draft(self):
        checklist = _clean_checklist()
        checklist.output_visually_checked = False
        status, reasons = rg.evaluate_release(checklist, human_approved=True)
        self.assertEqual(status, rg.DRAFT)
        self.assertIn("output_visually_checked", reasons)


class TestNoVersionCannotBeApproved(unittest.TestCase):
    """Proof 6: a file without version and source lineage cannot be approved."""

    def test_missing_version_and_timestamp_blocks_approval(self):
        checklist = _clean_checklist()
        checklist.version_and_timestamp_added = False
        status, reasons = rg.evaluate_release(checklist, human_approved=True)
        self.assertEqual(status, rg.DRAFT)
        self.assertIn("version_and_timestamp_added", reasons)

    def test_version_filename_avoids_final_final_pattern(self):
        name = rg.build_version_filename("MT_Offtake_Jun26", rg.VALIDATED, version=1, date="20260719")
        self.assertEqual(name, "MT_Offtake_Jun26_Validated_v1_20260719.xlsx")
        self.assertNotIn("final_final", name.lower())


class TestLeadershipAndAnalystOutputsDiffer(unittest.TestCase):
    """Proof 7: leadership and analyst outputs contain different levels of detail."""

    def test_leadership_sections_are_a_strict_subset_of_analyst_detail(self):
        leadership = set(rg.select_sections(rg.AUDIENCE_LEADERSHIP))
        analyst = set(rg.select_sections(rg.AUDIENCE_ANALYST))
        self.assertNotEqual(leadership, analyst)
        self.assertNotIn("reconciliation", leadership)
        self.assertIn("reconciliation", analyst)
        self.assertIn("key_insights", leadership)
        self.assertNotIn("key_insights", analyst)

    def test_unknown_audience_rejected(self):
        with self.assertRaises(ValueError):
            rg.select_sections("intern")


class TestReleaseWorkflowEndToEnd(unittest.TestCase):
    """A checklist that passes everything only reaches APPROVED_FOR_SHARING
    with explicit human approval -- VALIDATED is not sufficient on its own."""

    def test_all_pass_no_human_approval_is_validated_not_approved(self):
        status, reasons = rg.evaluate_release(_clean_checklist(), human_approved=False)
        self.assertEqual(status, rg.VALIDATED)
        self.assertTrue(reasons)

    def test_all_pass_with_human_approval_is_approved(self):
        status, reasons = rg.evaluate_release(_clean_checklist(), human_approved=True)
        self.assertEqual(status, rg.APPROVED_FOR_SHARING)
        self.assertEqual(reasons, [])


class TestMaterialityClassification(unittest.TestCase):
    def test_mapping_exception_above_5l_is_at_least_material(self):
        level = rg.classify_materiality(mapping_exception_value=6_00_000)
        self.assertIn(level, (rg.MATERIAL, rg.CRITICAL))

    def test_small_movement_is_informational(self):
        level = rg.classify_materiality(pct_change=0.01, abs_impact=1000)
        self.assertEqual(level, rg.INFORMATIONAL)

    def test_very_large_financial_impact_is_critical(self):
        level = rg.classify_materiality(abs_impact=60_00_000)  # 6x the 10L threshold
        self.assertEqual(level, rg.CRITICAL)


if __name__ == "__main__":
    unittest.main()
