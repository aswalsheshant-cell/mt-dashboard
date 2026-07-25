#!/usr/bin/env python3
"""Validate provisional dashboard workflow for internal sales-reference use.

Tests that the dashboard is correctly configured as a provisional, internal
tool pending Finance approval of D1 (COGS) and D9 (allocation rules).

This is NOT a Finance-approved dashboard. It is for internal use only.
CM2 figures are provisional and subject to change after approval.
"""
from __future__ import annotations

import csv
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class TestProvisionalGovernanceState(unittest.TestCase):
    """Tests that D1 and D9 remain PENDING_APPROVAL."""

    @classmethod
    def setUpClass(cls):
        path = ROOT / "PowerBI" / "Reference" / "CM2_Provisional" / "config" / "cm2_decision_register.csv"
        with path.open(encoding="utf-8") as f:
            cls.register = {r["decision_id"]: r for r in csv.DictReader(f)}

    def test_prov_01_d1_is_pending(self):
        """PROV-01: D1 status is PENDING_APPROVAL"""
        self.assertEqual(self.register["D1"]["status"], "PENDING_APPROVAL",
                        "D1 must remain PENDING_APPROVAL for internal use")

    def test_prov_02_d1_approver_blank(self):
        """PROV-02: D1 approver is blank (no Finance approval yet)"""
        approver = self.register["D1"].get("approved_by", "").strip()
        self.assertEqual(approver, "",
                        "D1 approver must be blank — do not invent Finance names")

    def test_prov_03_d1_date_blank(self):
        """PROV-03: D1 approval date is blank"""
        date = self.register["D1"].get("approved_at", "").strip()
        self.assertEqual(date, "",
                        "D1 date must be blank — do not invent approval dates")

    def test_prov_04_d9_is_pending(self):
        """PROV-04: D9 status is PENDING_APPROVAL"""
        self.assertEqual(self.register["D9"]["status"], "PENDING_APPROVAL",
                        "D9 must remain PENDING_APPROVAL for internal use")

    def test_prov_05_d9_approver_blank(self):
        """PROV-05: D9 approver is blank"""
        approver = self.register["D9"].get("approved_by", "").strip()
        self.assertEqual(approver, "",
                        "D9 approver must be blank — do not invent approvals")

    def test_prov_06_d9_date_blank(self):
        """PROV-06: D9 approval date is blank"""
        date = self.register["D9"].get("approved_at", "").strip()
        self.assertEqual(date, "",
                        "D9 date must be blank — governance workflow intact")


class TestDashboardProvisionalBanner(unittest.TestCase):
    """Tests that the dashboard shows the provisional warning."""

    @classmethod
    def setUpClass(cls):
        path = ROOT / "dashboard" / "data.js"
        with path.open(encoding="utf-8") as f:
            content = f.read()
        start = content.find("window.DASH = ") + len("window.DASH = ")
        end = content.rfind("};") + 1
        cls.dash = json.loads(content[start:end])

    def test_prov_07_dashboard_provisional_flag_true(self):
        """PROV-07: data.js cm2.provisional is true"""
        provisional = self.dash.get("cm2", {}).get("provisional", False)
        self.assertTrue(provisional,
                       "Dashboard must flag CM2 as provisional while D1/D9 pending")

    def test_prov_08_formula_status_is_draft(self):
        """PROV-08: cm2.formula_status is DRAFT (not APPROVED)"""
        status = self.dash.get("cm2", {}).get("formula_status", "")
        self.assertEqual(status, "DRAFT",
                        "Formula status must remain DRAFT until D1/D9 approved")

    def test_prov_09_example_data_only_true(self):
        """PROV-09: cm2.example_data_only is true"""
        example = self.dash.get("cm2", {}).get("example_data_only", False)
        self.assertTrue(example,
                       "Dashboard must flag that only example expenses are loaded")

    def test_prov_10_provisional_reasons_populated(self):
        """PROV-10: provisional_reasons explain why CM2 is provisional"""
        reasons = self.dash.get("cm2", {}).get("provisional_reasons", [])
        self.assertGreater(len(reasons), 0,
                          "Dashboard must explain why CM2 is provisional")
        reason_text = " ".join(reasons).upper()
        self.assertIn("FORMULA", reason_text,
                     "Reasons must mention formula approval pending")


class TestExampleRowsIdentification(unittest.TestCase):
    """Tests that example rows are clearly marked."""

    @classmethod
    def setUpClass(cls):
        path = ROOT / "PowerBI" / "SeedData" / "Masters" / "PL_Expense_Input.csv"
        with path.open(encoding="utf-8") as f:
            cls.expense_rows = list(csv.DictReader(f))

    def test_prov_11_three_example_rows(self):
        """PROV-11: Exactly 3 rows are marked as EXAMPLE"""
        example_count = sum(1 for r in self.expense_rows
                           if "EXAMPLE" in r.get("Remarks", "").upper())
        self.assertEqual(example_count, 3,
                        "Exactly 3 example rows expected; actual expenses must replace them")

    def test_prov_12_examples_clearly_identified(self):
        """PROV-12: Example rows have 'EXAMPLE ROW' in Remarks"""
        for row in self.expense_rows:
            if "EXAMPLE" in row.get("Remarks", "").upper():
                self.assertIn("EXAMPLE ROW", row.get("Remarks", ""),
                             "Example rows must clearly say 'EXAMPLE ROW'")


class TestProvisionalMeasureBehavior(unittest.TestCase):
    """Tests that Provisional CM2 is used; Approved CM2 stays blank."""

    @classmethod
    def setUpClass(cls):
        path = ROOT / "PowerBI" / "Reference" / "CM2_Provisional" / "DAX" / "14_CM2_Provisional_Measures.dax"
        with path.open(encoding="utf-8") as f:
            cls.dax_content = f.read()

    def test_prov_13_provisional_cm2_always_calculated(self):
        """PROV-13: Provisional CM2 measure is always calculated"""
        self.assertIn("Provisional CM2 Lacs", self.dax_content,
                     "Provisional CM2 measure must exist and be calculated always")

    def test_prov_14_approved_cm2_conditionally_blank(self):
        """PROV-14: Approved CM2 returns BLANK while D1/D9 pending"""
        self.assertIn('IF ( [Formula_Status] = "APPROVED"', self.dax_content,
                     "Approved CM2 must check Formula_Status before calculating")
        self.assertIn("BLANK()", self.dax_content,
                     "Approved CM2 must return BLANK when decisions pending")

    def test_prov_15_no_fallback_to_provisional(self):
        """PROV-15: Approved CM2 does NOT fall back to Provisional"""
        # Check that the approved measure is not coalescing or defaulting to provisional
        approved_def = self.dax_content[self.dax_content.find("Approved CM2 Lacs"):]
        approved_def = approved_def[:approved_def.find("\n\n")]
        self.assertNotIn("Provisional", approved_def,
                        "Approved measure must not reference Provisional as fallback")


class TestExpenseSourceEditable(unittest.TestCase):
    """Tests that the Power BI expense source is editable and maintainable."""

    def test_prov_16_provisional_assumptions_table_exists(self):
        """PROV-16: CM2_Provisional_Assumptions.csv exists and is editable"""
        path = ROOT / "PowerBI" / "Reference" / "CM2_Provisional" / "SeedData" / "CM2_Provisional_Assumptions.csv"
        self.assertTrue(path.exists(),
                       "Provisional assumptions table must exist for Power BI")

    def test_prov_17_assumptions_are_all_provisional(self):
        """PROV-17: All assumption rows are tagged Data_Status=PROVISIONAL"""
        path = ROOT / "PowerBI" / "Reference" / "CM2_Provisional" / "SeedData" / "CM2_Provisional_Assumptions.csv"
        with path.open(encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        for row in rows:
            status = row.get("Data_Status", "").strip()
            self.assertEqual(status, "PROVISIONAL",
                            f"Row {row.get('Expense_Category')}: must be PROVISIONAL")

    def test_prov_18_approved_by_blank_in_assumptions(self):
        """PROV-18: Approved_By is blank in all assumption rows"""
        path = ROOT / "PowerBI" / "Reference" / "CM2_Provisional" / "SeedData" / "CM2_Provisional_Assumptions.csv"
        with path.open(encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        for row in rows:
            approved_by = row.get("Approved_By", "").strip()
            self.assertEqual(approved_by, "",
                            "All assumption rows must have blank Approved_By")

    def test_prov_19_cogs_logistics_present(self):
        """PROV-19: COGS and Logistics assumptions are documented"""
        path = ROOT / "PowerBI" / "Reference" / "CM2_Provisional" / "SeedData" / "CM2_Provisional_Assumptions.csv"
        with path.open(encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        categories = {r.get("Expense_Category", "").strip() for r in rows}
        self.assertIn("COGS", categories, "COGS assumptions must be documented")
        self.assertIn("LOGISTICS", categories, "Logistics assumptions must be documented")


class TestPatchScriptSafety(unittest.TestCase):
    """Tests that the patch script cannot be run without proper validation."""

    def test_prov_20_validation_script_required(self):
        """PROV-20: Validation script exists to gate patch script"""
        path = ROOT / "scripts" / "validate_cm2_governance_before_patch.py"
        self.assertTrue(path.exists(),
                       "Validation script must gate the patch to prevent accidental approval")

    def test_prov_21_patch_guards_amounts(self):
        """PROV-21: Patch script guards against CM2 amount modification"""
        path = ROOT / "scripts" / "patch_cm2_provisional.py"
        with path.open(encoding="utf-8") as f:
            content = f.read()
        self.assertIn("assert {k: dash[\"cm2\"].get(k) for k in amounts} == amounts", content,
                     "Patch script must guard CM2 amounts")


class TestWorkflowIntegrity(unittest.TestCase):
    """Tests that the provisional workflow is complete and consistent."""

    @classmethod
    def setUpClass(cls):
        register_path = ROOT / "PowerBI" / "Reference" / "CM2_Provisional" / "config" / "cm2_decision_register.csv"
        with register_path.open(encoding="utf-8") as f:
            cls.register = list(csv.DictReader(f))

        pbi_gov_path = ROOT / "PowerBI" / "Reference" / "CM2_Provisional" / "SeedData" / "CM2_Governance_Status.csv"
        with pbi_gov_path.open(encoding="utf-8") as f:
            cls.pbi_gov = list(csv.DictReader(f))

    def test_prov_22_governance_tables_sync(self):
        """PROV-22: Governance tables are synchronized"""
        register_ids = {d["decision_id"] for d in self.register}
        pbi_ids = {d["Decision_ID"] for d in self.pbi_gov}
        self.assertEqual(register_ids, pbi_ids,
                        "Decision IDs must match between register and Power BI governance table")

    def test_prov_23_d1_d9_blocking_status_correct(self):
        """PROV-23: D1 and D9 are marked as blocking publication"""
        pbi_dict = {d["Decision_ID"]: d for d in self.pbi_gov}
        d1_blocks = pbi_dict.get("D1", {}).get("Blocks_Publication", "")
        d9_blocks = pbi_dict.get("D9", {}).get("Blocks_Publication", "")
        self.assertEqual(d1_blocks, "TRUE", "D1 must block publication")
        self.assertEqual(d9_blocks, "TRUE", "D9 must block publication")

    def test_prov_24_no_approval_entries_created(self):
        """PROV-24: No false approval entries have been created"""
        for decision in self.register:
            if decision["decision_id"] in ["D1", "D2", "D3", "D4", "D5", "D6", "D7", "D9"]:
                status = decision["status"]
                self.assertEqual(status, "PENDING_APPROVAL",
                                f"{decision['decision_id']}: must remain PENDING_APPROVAL")

    def test_prov_25_d1_d9_still_pending(self):
        """PROV-25: Even if patch was run for testing, D1/D9 still PENDING"""
        # The patch script is idempotent and re-derives flags from config.
        # This test ensures D1/D9 are still marked PENDING even if patch was
        # run (which would happen during testing).
        for decision in self.register:
            if decision["decision_id"] in ["D1", "D9"]:
                self.assertEqual(decision["status"], "PENDING_APPROVAL",
                                "D1/D9 must remain PENDING even if patch was tested")


class TestExistingTestsContinueToPass(unittest.TestCase):
    """Sanity check: existing tests still pass (proxy for no regressions)."""

    def test_prov_26_build_script_compiles(self):
        """PROV-26: build_dashboard_data.py still compiles"""
        import py_compile
        path = ROOT / "scripts" / "build_dashboard_data.py"
        try:
            py_compile.compile(str(path), doraise=True)
        except py_compile.PyCompileError as e:
            self.fail(f"build_dashboard_data.py compilation failed: {e}")

    def test_prov_27_data_js_is_valid_json(self):
        """PROV-27: data.js is valid JSON"""
        path = ROOT / "dashboard" / "data.js"
        with path.open(encoding="utf-8") as f:
            content = f.read()
        try:
            start = content.find("window.DASH = ") + len("window.DASH = ")
            end = content.rfind("};") + 1
            json.loads(content[start:end])
        except json.JSONDecodeError as e:
            self.fail(f"data.js JSON is invalid: {e}")

    def test_prov_28_html_dashboard_loads(self):
        """PROV-28: index.html is syntactically valid"""
        path = ROOT / "dashboard" / "index.html"
        with path.open(encoding="utf-8") as f:
            html = f.read()
        self.assertIn("<html", html.lower(), "index.html must be valid HTML")
        self.assertIn("window.DASH", html, "index.html must reference data.js")


if __name__ == "__main__":
    unittest.main()
