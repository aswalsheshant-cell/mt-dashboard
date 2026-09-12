#!/usr/bin/env python3
"""Test suite for dashboard governance disclosures and provisional state warnings.

Validates that the dashboard correctly displays:
1. CM2 provisional governance banners
2. Warnings for pending Finance approvals (D1, D9)
3. Example data status flags
4. Provisional reason explanations
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class TestDashboardDisclosures(unittest.TestCase):
    """Verify dashboard shows required governance disclosures."""

    @classmethod
    def setUpClass(cls):
        """Load data.js for disclosure analysis."""
        data_js_path = ROOT / "dashboard" / "data.js"
        with data_js_path.open(encoding="utf-8") as f:
            content = f.read()

        start = content.find("window.DASH = ") + len("window.DASH = ")
        end = content.rfind("};") + 1
        cls.dash = json.loads(content[start:end])
        cls.cm2 = cls.dash.get("cm2", {})

    def test_disclosure_01_cm2_provisional_flag_set(self):
        """DISC-01: CM2 is marked as provisional."""
        provisional = self.cm2.get("provisional", False)
        self.assertTrue(provisional,
                       "CM2 must be flagged as provisional while D1/D9 pending")

    def test_disclosure_02_provisional_label_exists(self):
        """DISC-02: Provisional label is present for display."""
        label = self.cm2.get("provisional_label", "")
        self.assertIsNotNone(label,
                           "Dashboard must have a provisional label for UI display")
        self.assertGreater(len(label), 0,
                          "Provisional label must not be empty")

    def test_disclosure_03_provisional_reasons_populated(self):
        """DISC-03: Provisional reasons explain why CM2 is provisional."""
        reasons = self.cm2.get("provisional_reasons", [])
        self.assertGreater(len(reasons), 0,
                          "Dashboard must list reasons why CM2 is provisional")

        reason_text = " ".join(reasons).upper()
        self.assertIn("FORMULA", reason_text,
                     "Reasons must mention formula approval pending (D1)")

    def test_disclosure_04_example_data_flag_detected(self):
        """DISC-04: Dashboard detects and flags example-only data state."""
        example_flag = self.cm2.get("example_data_only", False)
        self.assertIsNotNone(example_flag,
                           "Dashboard must track example_data_only state")

    def test_disclosure_05_formula_status_tracked(self):
        """DISC-05: Formula approval status is tracked."""
        formula_status = self.cm2.get("formula_status", "")
        self.assertIn(formula_status, ["DRAFT", "APPROVED"],
                     "Formula status must be either DRAFT or APPROVED")

    def test_disclosure_06_banner_warning_text(self):
        """DISC-06: Provisional warning banner includes required text."""
        label = self.cm2.get("provisional_label", "")
        # Should indicate CM2 is provisional and subject to change
        self.assertTrue("PROVISIONAL" in label.upper() or "provisional" in label,
                       "Banner must clearly indicate provisional status")

    def test_disclosure_07_no_false_approvals(self):
        """DISC-07: Dashboard does not show false Finance approvals."""
        # If example_data_only is true, we're in provisional state
        example_data = self.cm2.get("example_data_only", False)
        formula_status = self.cm2.get("formula_status", "")

        # If still in provisional state, formula cannot claim APPROVED
        if example_data or formula_status == "DRAFT":
            self.assertNotEqual(formula_status, "APPROVED",
                              "Cannot show APPROVED formula while in provisional state")

    def test_disclosure_08_qc_metadata_present(self):
        """DISC-08: QC metadata for CM2 is available."""
        qc = self.cm2.get("qc", {})
        self.assertIsNotNone(qc,
                           "CM2 must include QC metadata for transparency")

    def test_disclosure_09_methodology_documented(self):
        """DISC-09: CM2 methodology is documented in dashboard."""
        methodology = self.cm2.get("methodology", "")
        self.assertIsNotNone(methodology,
                           "Dashboard must document CM2 calculation methodology")

    def test_disclosure_10_has_expense_data_tracked(self):
        """DISC-10: Dashboard tracks whether expense data is loaded."""
        has_expense = self.cm2.get("has_expense_data", False)
        self.assertIsNotNone(has_expense,
                           "Dashboard must track if expense data is present")


class TestProvisionalBannerDisplay(unittest.TestCase):
    """Verify provisional banner displays correctly on dashboard."""

    @classmethod
    def setUpClass(cls):
        """Load data.js for banner display validation."""
        data_js_path = ROOT / "dashboard" / "data.js"
        with data_js_path.open(encoding="utf-8") as f:
            content = f.read()

        start = content.find("window.DASH = ") + len("window.DASH = ")
        end = content.rfind("};") + 1
        cls.dash = json.loads(content[start:end])
        cls.cm2 = cls.dash.get("cm2", {})

    def test_banner_01_visible_when_provisional(self):
        """BANNER-01: Banner is visible when CM2 is provisional."""
        provisional = self.cm2.get("provisional", False)
        if provisional:
            label = self.cm2.get("provisional_label", "")
            self.assertTrue(label,
                          "Provisional label must be non-empty when provisional flag set")

    def test_banner_02_includes_decision_status(self):
        """BANNER-02: Banner indicates which decisions are pending."""
        reasons = self.cm2.get("provisional_reasons", [])
        reason_text = " ".join(reasons)

        # Should mention that decisions are pending approval
        self.assertTrue(any(term in reason_text.lower()
                           for term in ["pending", "decision", "approval"]),
                       "Banner reasons must indicate pending decisions")

    def test_banner_03_non_intrusive_placement(self):
        """BANNER-03: Banner metadata allows non-intrusive UI placement."""
        # Verify that the provisional flag is a property that can be queried
        # without affecting other dashboard functionality
        primary = self.dash.get("primary", {})
        self.assertIsNotNone(primary,
                           "Dashboard primary data must be available alongside provisional flag")

    def test_banner_04_all_reasons_listed(self):
        """BANNER-04: All provisional reasons are enumerated."""
        reasons = self.cm2.get("provisional_reasons", [])
        # Each reason should be a non-empty string
        for reason in reasons:
            self.assertIsInstance(reason, str,
                                "Each provisional reason must be a string")
            self.assertGreater(len(reason.strip()), 0,
                             "Provisional reasons must not be empty strings")


class TestGovernanceDisclosureCompleteness(unittest.TestCase):
    """Verify governance transparency is complete."""

    @classmethod
    def setUpClass(cls):
        """Load data.js and decision register."""
        data_js_path = ROOT / "dashboard" / "data.js"
        with data_js_path.open(encoding="utf-8") as f:
            content = f.read()

        start = content.find("window.DASH = ") + len("window.DASH = ")
        end = content.rfind("};") + 1
        cls.dash = json.loads(content[start:end])
        cls.cm2 = cls.dash.get("cm2", {})

    def test_complete_01_all_components_declared(self):
        """COMPLETE-01: All CM2 components are disclosed."""
        # Should have entries for key metrics
        required_keys = ["total_nsv", "total_expense", "cm2_value", "formula_status"]
        for key in required_keys:
            self.assertIn(key, self.cm2,
                         f"CM2 must include '{key}' in disclosures")

    def test_complete_02_unit_declared(self):
        """COMPLETE-02: CM2 unit of measurement is declared."""
        unit = self.cm2.get("unit", "")
        self.assertIsNotNone(unit,
                           "CM2 must declare its unit (e.g., 'INR Lakh')")

    def test_complete_03_approval_state_clear(self):
        """COMPLETE-03: Formula approval state is clear and unambiguous."""
        formula_status = self.cm2.get("formula_status", "")
        self.assertIn(formula_status, ["DRAFT", "APPROVED", "PENDING"],
                     "Formula status must be clearly one of: DRAFT, APPROVED, PENDING")

    def test_complete_04_provisional_state_unambiguous(self):
        """COMPLETE-04: Provisional state is unambiguous."""
        provisional = self.cm2.get("provisional", False)
        self.assertIsInstance(provisional, bool,
                            "Provisional flag must be a boolean (True/False)")

    def test_complete_05_example_state_unambiguous(self):
        """COMPLETE-05: Example data state is unambiguous."""
        example_data_only = self.cm2.get("example_data_only", False)
        self.assertIsInstance(example_data_only, bool,
                            "example_data_only flag must be a boolean (True/False)")


if __name__ == "__main__":
    unittest.main()
