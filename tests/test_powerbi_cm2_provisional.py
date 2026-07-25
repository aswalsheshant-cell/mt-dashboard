#!/usr/bin/env python3
"""Power BI CM2 provisional-expense QC tests (unittest format).

Validates that the Power BI seed tables and DAX measures are configured
correctly for the controlled provisional-expense solution. These tests run
BEFORE the .pbix file is built in Power BI Desktop.

Test coverage:
- Data table structure and completeness
- Governance status consistency
- Provisional assumption validity
- Reconciliation logic
- Finance workflow safety
"""
from __future__ import annotations

import csv
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class TestCM2GovernanceStatus(unittest.TestCase):
    """Tests for CM2_Governance_Status.csv"""

    @classmethod
    def setUpClass(cls):
        path = ROOT / "PowerBI" / "SeedData" / "Masters" / "CM2_Governance_Status.csv"
        with path.open(encoding="utf-8") as f:
            cls.governance_rows = list(csv.DictReader(f))

    def test_pbi_gov_01_table_exists(self):
        """PBI-GOV-01: CM2_Governance_Status.csv exists"""
        path = ROOT / "PowerBI" / "SeedData" / "Masters" / "CM2_Governance_Status.csv"
        self.assertTrue(path.exists(), "CM2_Governance_Status.csv not found")

    def test_pbi_gov_02_required_columns(self):
        """PBI-GOV-02: All required columns present"""
        required_columns = {
            "Decision_ID", "Decision_Name", "Status",
            "Approved_By", "Approved_At", "Blocks_Publication"
        }
        actual_columns = set(self.governance_rows[0].keys()) if self.governance_rows else set()
        self.assertTrue(required_columns.issubset(actual_columns),
                       f"Missing columns: {required_columns - actual_columns}")

    def test_pbi_gov_03_decision_ids_match_register(self):
        """PBI-GOV-03: Decision IDs match config/cm2_decision_register.csv"""
        path = ROOT / "config" / "cm2_decision_register.csv"
        with path.open(encoding="utf-8") as f:
            register_rows = list(csv.DictReader(f))

        register_ids = {d["decision_id"] for d in register_rows}
        gov_ids = {d["Decision_ID"] for d in self.governance_rows}

        self.assertEqual(gov_ids, register_ids,
                        f"Mismatch: register has {register_ids}, governance has {gov_ids}")

    def test_pbi_gov_04_status_values_valid(self):
        """PBI-GOV-04: Status values are APPROVED or PENDING_APPROVAL only"""
        valid_statuses = {"APPROVED", "PENDING_APPROVAL"}
        for row in self.governance_rows:
            status = row.get("Status", "").strip()
            self.assertIn(status, valid_statuses,
                         f"Decision {row['Decision_ID']}: invalid status '{status}'")

    def test_pbi_gov_05_d1_d9_are_pending(self):
        """PBI-GOV-05: D1 and D9 are PENDING_APPROVAL (blocking decisions)"""
        gov_dict = {d["Decision_ID"]: d for d in self.governance_rows}

        d1_status = gov_dict.get("D1", {}).get("Status", "").strip()
        d9_status = gov_dict.get("D9", {}).get("Status", "").strip()

        self.assertEqual(d1_status, "PENDING_APPROVAL",
                        f"D1 status is {d1_status}, not PENDING_APPROVAL")
        self.assertEqual(d9_status, "PENDING_APPROVAL",
                        f"D9 status is {d9_status}, not PENDING_APPROVAL")

    def test_pbi_gov_06_d10_d11_d12_d13_approved(self):
        """PBI-GOV-06: D10, D11, D12, D13 are APPROVED (established baseline)"""
        gov_dict = {d["Decision_ID"]: d for d in self.governance_rows}

        for decision_id in ["D10", "D11", "D12", "D13"]:
            status = gov_dict.get(decision_id, {}).get("Status", "").strip()
            self.assertEqual(status, "APPROVED",
                            f"{decision_id} status is {status}, not APPROVED")

    def test_pbi_gov_07_blocks_publication_logic(self):
        """PBI-GOV-07: Blocks_Publication is TRUE for D1–D7,D9; FALSE for D8,D10–D13"""
        gov_dict = {d["Decision_ID"]: d for d in self.governance_rows}

        blocking_decisions = {"D1", "D2", "D3", "D4", "D5", "D6", "D7", "D9"}
        non_blocking_decisions = {"D8", "D10", "D11", "D12", "D13"}

        for decision_id in blocking_decisions:
            blocks = gov_dict.get(decision_id, {}).get("Blocks_Publication", "")
            self.assertEqual(blocks, "TRUE",
                            f"{decision_id}: Blocks_Publication should be TRUE, got {blocks}")

        for decision_id in non_blocking_decisions:
            blocks = gov_dict.get(decision_id, {}).get("Blocks_Publication", "")
            self.assertEqual(blocks, "FALSE",
                            f"{decision_id}: Blocks_Publication should be FALSE, got {blocks}")


class TestCM2ProvisionalAssumptions(unittest.TestCase):
    """Tests for CM2_Provisional_Assumptions.csv"""

    @classmethod
    def setUpClass(cls):
        path = ROOT / "PowerBI" / "SeedData" / "Masters" / "CM2_Provisional_Assumptions.csv"
        with path.open(encoding="utf-8") as f:
            cls.assumption_rows = list(csv.DictReader(f))

    def test_pbi_assum_01_table_exists(self):
        """PBI-ASSUM-01: CM2_Provisional_Assumptions.csv exists"""
        path = ROOT / "PowerBI" / "SeedData" / "Masters" / "CM2_Provisional_Assumptions.csv"
        self.assertTrue(path.exists(), "CM2_Provisional_Assumptions.csv not found")

    def test_pbi_assum_02_required_columns(self):
        """PBI-ASSUM-02: All required columns present"""
        required_columns = {
            "Financial_Year", "Scenario", "Data_Status",
            "Decision_ID", "Include_Status", "Expense_Lacs"
        }
        actual_columns = set(self.assumption_rows[0].keys()) if self.assumption_rows else set()
        self.assertTrue(required_columns.issubset(actual_columns),
                       f"Missing columns: {required_columns - actual_columns}")

    def test_pbi_assum_03_data_status_provisional(self):
        """PBI-ASSUM-03: All rows are tagged Data_Status=PROVISIONAL"""
        for row in self.assumption_rows:
            status = row.get("Data_Status", "").strip()
            self.assertEqual(status, "PROVISIONAL",
                            f"Row with {row.get('Expense_Category')}: Data_Status is {status}, not PROVISIONAL")

    def test_pbi_assum_04_include_status_pending(self):
        """PBI-ASSUM-04: Include_Status is PENDING_APPROVAL (not APPROVED)"""
        for row in self.assumption_rows:
            include_status = row.get("Include_Status", "").strip()
            self.assertEqual(include_status, "PENDING_APPROVAL",
                            f"Row {row.get('Expense_Category')}: Include_Status is {include_status}, expected PENDING_APPROVAL")

    def test_pbi_assum_05_scenario_values_valid(self):
        """PBI-ASSUM-05: Scenario values are Base, Optimistic, or Conservative"""
        valid_scenarios = {"Base", "Optimistic", "Conservative"}
        for row in self.assumption_rows:
            scenario = row.get("Scenario", "").strip()
            self.assertIn(scenario, valid_scenarios,
                         f"Row with {row.get('Expense_Category')}: Scenario is {scenario}, not in {valid_scenarios}")

    def test_pbi_assum_06_cogs_amounts(self):
        """PBI-ASSUM-06: COGS amounts reconcile to Q1 FY27 total 4411.21L (base)"""
        cogs_rows = [r for r in self.assumption_rows
                     if r.get("Expense_Category", "").strip() == "COGS"
                     and r.get("Scenario", "").strip() == "Base"
                     and r.get("Financial_Year", "").strip() == "FY27"]

        # Filter to total row (no month specified)
        total_rows = [r for r in cogs_rows if not r.get("Month", "").strip()]
        self.assertEqual(len(total_rows), 1, f"Expected 1 COGS total row, got {len(total_rows)}")

        total_amount = float(total_rows[0].get("Expense_Lacs", "0"))
        self.assertAlmostEqual(total_amount, 4411.21, places=2,
                              msg=f"COGS total is {total_amount}, expected 4411.21L")

    def test_pbi_assum_07_logistics_amounts(self):
        """PBI-ASSUM-07: Logistics amounts reconcile to Q1 FY27 total 360.37L (base)"""
        logistics_rows = [r for r in self.assumption_rows
                          if r.get("Expense_Category", "").strip() == "LOGISTICS"
                          and r.get("Scenario", "").strip() == "Base"
                          and r.get("Financial_Year", "").strip() == "FY27"]

        total_rows = [r for r in logistics_rows if not r.get("Month", "").strip()]
        self.assertEqual(len(total_rows), 1, f"Expected 1 Logistics total row, got {len(total_rows)}")

        total_amount = float(total_rows[0].get("Expense_Lacs", "0"))
        self.assertAlmostEqual(total_amount, 360.37, places=2,
                              msg=f"Logistics total is {total_amount}, expected 360.37L")

    def test_pbi_assum_08_no_approved_by_until_finance(self):
        """PBI-ASSUM-08: Approved_By is blank (waiting for Finance)"""
        for row in self.assumption_rows:
            approved_by = row.get("Approved_By", "").strip()
            self.assertEqual(approved_by, "",
                            f"Approved_By should be blank, got '{approved_by}'")

    def test_pbi_assum_09_expense_amounts_positive(self):
        """PBI-ASSUM-09: Expense_Lacs values are positive (no zero placeholders)"""
        for row in self.assumption_rows:
            amount_str = row.get("Expense_Lacs", "0").strip()
            if amount_str:
                amount = float(amount_str)
                self.assertGreater(amount, 0,
                                  msg=f"Row {row.get('Expense_Category')}: Expense_Lacs is {amount}, must be > 0")


class TestPowerBIFilesPresent(unittest.TestCase):
    """Tests for all required Power BI assets"""

    def test_pbi_files_01_dax_provisional_measures(self):
        """PBI-FILES-01: DAX/14_CM2_Provisional_Measures.dax exists"""
        path = ROOT / "PowerBI" / "DAX" / "14_CM2_Provisional_Measures.dax"
        self.assertTrue(path.exists(), "14_CM2_Provisional_Measures.dax not found")

    def test_pbi_files_02_pq_import_guide(self):
        """PBI-FILES-02: Power Query import guide exists"""
        path = ROOT / "PowerBI" / "QuickSetup" / "PQ_CM2_Governance_Import.md"
        self.assertTrue(path.exists(), "PQ_CM2_Governance_Import.md not found")

    def test_pbi_files_03_page_blueprint(self):
        """PBI-FILES-03: Page blueprint for CM2 Analysis exists"""
        path = ROOT / "PowerBI" / "docs" / "PageBlueprint_CM2_Analysis_Provisional.md"
        self.assertTrue(path.exists(), "PageBlueprint_CM2_Analysis_Provisional.md not found")

    def test_pbi_files_04_governance_validation_script(self):
        """PBI-FILES-04: Governance validation script exists"""
        path = ROOT / "scripts" / "validate_cm2_governance_before_patch.py"
        self.assertTrue(path.exists(), "validate_cm2_governance_before_patch.py not found")


class TestReconciliation(unittest.TestCase):
    """Tests for expense reconciliation logic"""

    @classmethod
    def setUpClass(cls):
        pl_path = ROOT / "PowerBI" / "SeedData" / "Masters" / "PL_Expense_Input.csv"
        with pl_path.open(encoding="utf-8") as f:
            cls.pl_expense_rows = list(csv.DictReader(f))

        assum_path = ROOT / "PowerBI" / "SeedData" / "Masters" / "CM2_Provisional_Assumptions.csv"
        with assum_path.open(encoding="utf-8") as f:
            cls.assumption_rows = list(csv.DictReader(f))

    def test_pbi_recon_01_no_zero_values(self):
        """PBI-RECON-01: No zero-values used as missing-data placeholders"""
        for row in self.assumption_rows:
            try:
                amount_str = row.get("Expense_Lacs", "0").strip()
                if amount_str:
                    amount = float(amount_str)
                    self.assertNotEqual(amount, 0,
                                       msg=f"Row {row.get('Expense_Category')} / {row.get('Scenario')}: "
                                           "Expense_Lacs is 0 — use blank instead for missing data")
            except ValueError:
                pass  # Blank is ok, numeric errors are ok

    def test_pbi_recon_02_example_data_marked(self):
        """PBI-RECON-02: EXAMPLE rows are clearly marked"""
        for row in self.pl_expense_rows:
            remarks = row.get("Remarks", "").upper()
            if "EXAMPLE" in remarks:
                # These are the placeholder rows; they should be noted in Remarks
                self.assertIn("EXAMPLE ROW", remarks,
                             f"Row marked as example but Remarks don't clearly say 'EXAMPLE ROW'")

    def test_pbi_recon_03_no_negative_amounts_in_base(self):
        """PBI-RECON-03: Base scenario amounts are all positive (no negative expenses)"""
        base_rows = [r for r in self.assumption_rows
                     if r.get("Scenario", "").strip() == "Base"]

        for row in base_rows:
            try:
                amount_str = row.get("Expense_Lacs", "0").strip()
                if amount_str:
                    amount = float(amount_str)
                    self.assertGreaterEqual(amount, 0,
                                           msg=f"Base scenario row {row.get('Expense_Category')}: negative amount {amount}")
            except ValueError:
                pass  # Skip non-numeric


class TestPatchScriptSafety(unittest.TestCase):
    """Tests for patch_cm2_provisional.py safety"""

    def test_pbi_patch_01_validation_script_exists(self):
        """PBI-PATCH-01: Validation script exists to gate the patch"""
        path = ROOT / "scripts" / "validate_cm2_governance_before_patch.py"
        self.assertTrue(path.exists(), "validate_cm2_governance_before_patch.py not found")

    def test_pbi_patch_02_patch_script_exists(self):
        """PBI-PATCH-02: Patch script exists"""
        path = ROOT / "scripts" / "patch_cm2_provisional.py"
        self.assertTrue(path.exists(), "patch_cm2_provisional.py not found")

    def test_pbi_patch_03_patch_guards_amounts(self):
        """PBI-PATCH-03: Patch script never modifies CM2 amounts"""
        # Read the patch script and verify it contains the guard assertion
        path = ROOT / "scripts" / "patch_cm2_provisional.py"
        content = path.read_text(encoding="utf-8")
        self.assertIn('assert {k: dash["cm2"].get(k) for k in amounts} == amounts', content,
                     "Patch script missing amount-preservation guard")


class TestDAXMeasureStructure(unittest.TestCase):
    """Tests for DAX measure definitions (syntactic validation only)"""

    def test_pbi_dax_01_provisional_measures_exist(self):
        """PBI-DAX-01: DAX file contains provisional measure definitions"""
        path = ROOT / "PowerBI" / "DAX" / "14_CM2_Provisional_Measures.dax"
        content = path.read_text(encoding="utf-8")

        required_measures = {
            "Provisional CM2 Lacs",
            "Approved CM2 Lacs",
            "CM2 Display Status",
            "CM2 Warning Message",
            "Show CM2 Warning",
        }

        for measure in required_measures:
            self.assertIn(measure, content,
                         f"DAX file missing measure: {measure}")

    def test_pbi_dax_02_lookupvalue_used_for_governance(self):
        """PBI-DAX-02: DAX uses LOOKUPVALUE to query governance table"""
        path = ROOT / "PowerBI" / "DAX" / "14_CM2_Provisional_Measures.dax"
        content = path.read_text(encoding="utf-8")

        self.assertIn("LOOKUPVALUE", content,
                     "DAX should use LOOKUPVALUE to query governance table")
        self.assertIn("'CM2 Governance Status'", content,
                     "DAX should reference 'CM2 Governance Status' table")

    def test_pbi_dax_03_approved_cm2_conditionally_blank(self):
        """PBI-DAX-03: Approved CM2 measure returns BLANK when pending"""
        path = ROOT / "PowerBI" / "DAX" / "14_CM2_Provisional_Measures.dax"
        content = path.read_text(encoding="utf-8")

        self.assertIn('IF ( [Formula_Status] = "APPROVED"', content,
                     "Approved CM2 measure should check Formula_Status")


if __name__ == "__main__":
    unittest.main()
