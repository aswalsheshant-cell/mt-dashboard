#!/usr/bin/env python3
"""Power BI CM2 provisional-expense QC tests.

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
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent.parent


class TestCM2GovernanceStatus:
    """Tests for CM2_Governance_Status.csv"""

    @pytest.fixture
    def governance_rows(self):
        path = ROOT / "PowerBI" / "SeedData" / "Masters" / "CM2_Governance_Status.csv"
        with path.open(encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def test_pbi_gov_01_table_exists(self):
        """PBI-GOV-01: CM2_Governance_Status.csv exists"""
        path = ROOT / "PowerBI" / "SeedData" / "Masters" / "CM2_Governance_Status.csv"
        assert path.exists(), "CM2_Governance_Status.csv not found"

    def test_pbi_gov_02_required_columns(self, governance_rows):
        """PBI-GOV-02: All required columns present"""
        required_columns = {
            "Decision_ID", "Decision_Name", "Status",
            "Approved_By", "Approved_At", "Blocks_Publication"
        }
        actual_columns = set(governance_rows[0].keys()) if governance_rows else set()
        assert required_columns.issubset(actual_columns), \
            f"Missing columns: {required_columns - actual_columns}"

    def test_pbi_gov_03_decision_ids_match_register(self, governance_rows):
        """PBI-GOV-03: Decision IDs match config/cm2_decision_register.csv"""
        path = ROOT / "config" / "cm2_decision_register.csv"
        with path.open(encoding="utf-8") as f:
            register_rows = list(csv.DictReader(f))

        register_ids = {d["decision_id"] for d in register_rows}
        gov_ids = {d["Decision_ID"] for d in governance_rows}

        assert gov_ids == register_ids, \
            f"Mismatch: register has {register_ids}, governance has {gov_ids}"

    def test_pbi_gov_04_status_values_valid(self, governance_rows):
        """PBI-GOV-04: Status values are APPROVED or PENDING_APPROVAL only"""
        valid_statuses = {"APPROVED", "PENDING_APPROVAL"}
        for row in governance_rows:
            status = row.get("Status", "").strip()
            assert status in valid_statuses, \
                f"Decision {row['Decision_ID']}: invalid status '{status}'"

    def test_pbi_gov_05_d1_d9_are_pending(self, governance_rows):
        """PBI-GOV-05: D1 and D9 are PENDING_APPROVAL (blocking decisions)"""
        gov_dict = {d["Decision_ID"]: d for d in governance_rows}

        d1_status = gov_dict.get("D1", {}).get("Status", "").strip()
        d9_status = gov_dict.get("D9", {}).get("Status", "").strip()

        assert d1_status == "PENDING_APPROVAL", \
            f"D1 status is {d1_status}, not PENDING_APPROVAL"
        assert d9_status == "PENDING_APPROVAL", \
            f"D9 status is {d9_status}, not PENDING_APPROVAL"

    def test_pbi_gov_06_d10_d11_d12_d13_approved(self, governance_rows):
        """PBI-GOV-06: D10, D11, D12, D13 are APPROVED (established baseline)"""
        gov_dict = {d["Decision_ID"]: d for d in governance_rows}

        for decision_id in ["D10", "D11", "D12", "D13"]:
            status = gov_dict.get(decision_id, {}).get("Status", "").strip()
            assert status == "APPROVED", \
                f"{decision_id} status is {status}, not APPROVED"

    def test_pbi_gov_07_blocks_publication_logic(self, governance_rows):
        """PBI-GOV-07: Blocks_Publication is TRUE for D1–D7,D9; FALSE for D8,D10–D13"""
        gov_dict = {d["Decision_ID"]: d for d in governance_rows}

        # D1–D7 and D9 block publication (formula decisions + allocation activation)
        # D8 does NOT block (distributor crosswalk is separate from formula approval)
        # D10–D13 are already approved (don't block)
        blocking_decisions = {"D1", "D2", "D3", "D4", "D5", "D6", "D7", "D9"}
        non_blocking_decisions = {"D8", "D10", "D11", "D12", "D13"}

        for decision_id in blocking_decisions:
            blocks = gov_dict.get(decision_id, {}).get("Blocks_Publication", "")
            assert blocks == "TRUE", \
                f"{decision_id}: Blocks_Publication should be TRUE, got {blocks}"

        for decision_id in non_blocking_decisions:
            blocks = gov_dict.get(decision_id, {}).get("Blocks_Publication", "")
            assert blocks == "FALSE", \
                f"{decision_id}: Blocks_Publication should be FALSE, got {blocks}"


class TestCM2ProvisionalAssumptions:
    """Tests for CM2_Provisional_Assumptions.csv"""

    @pytest.fixture
    def assumption_rows(self):
        path = ROOT / "PowerBI" / "SeedData" / "Masters" / "CM2_Provisional_Assumptions.csv"
        with path.open(encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def test_pbi_assum_01_table_exists(self):
        """PBI-ASSUM-01: CM2_Provisional_Assumptions.csv exists"""
        path = ROOT / "PowerBI" / "SeedData" / "Masters" / "CM2_Provisional_Assumptions.csv"
        assert path.exists(), "CM2_Provisional_Assumptions.csv not found"

    def test_pbi_assum_02_required_columns(self, assumption_rows):
        """PBI-ASSUM-02: All required columns present"""
        required_columns = {
            "Financial_Year", "Scenario", "Data_Status",
            "Decision_ID", "Include_Status", "Expense_Lacs"
        }
        actual_columns = set(assumption_rows[0].keys()) if assumption_rows else set()
        assert required_columns.issubset(actual_columns), \
            f"Missing columns: {required_columns - actual_columns}"

    def test_pbi_assum_03_data_status_provisional(self, assumption_rows):
        """PBI-ASSUM-03: All rows are tagged Data_Status=PROVISIONAL"""
        for row in assumption_rows:
            status = row.get("Data_Status", "").strip()
            assert status == "PROVISIONAL", \
                f"Row with {row.get('Expense_Category')}: Data_Status is {status}, not PROVISIONAL"

    def test_pbi_assum_04_include_status_pending(self, assumption_rows):
        """PBI-ASSUM-04: Include_Status is PENDING_APPROVAL (not APPROVED)"""
        for row in assumption_rows:
            include_status = row.get("Include_Status", "").strip()
            assert include_status == "PENDING_APPROVAL", \
                f"Row {row.get('Expense_Category')}: Include_Status is {include_status}, expected PENDING_APPROVAL"

    def test_pbi_assum_05_scenario_values_valid(self, assumption_rows):
        """PBI-ASSUM-05: Scenario values are Base, Optimistic, or Conservative"""
        valid_scenarios = {"Base", "Optimistic", "Conservative"}
        for row in assumption_rows:
            scenario = row.get("Scenario", "").strip()
            assert scenario in valid_scenarios, \
                f"Row with {row.get('Expense_Category')}: Scenario is {scenario}, not in {valid_scenarios}"

    def test_pbi_assum_06_cogs_amounts(self, assumption_rows):
        """PBI-ASSUM-06: COGS amounts reconcile to Q1 FY27 total 4411.21L (base)"""
        cogs_rows = [r for r in assumption_rows
                     if r.get("Expense_Category", "").strip() == "COGS"
                     and r.get("Scenario", "").strip() == "Base"
                     and r.get("Financial_Year", "").strip() == "FY27"]

        # Filter to total row (no month specified)
        total_rows = [r for r in cogs_rows if not r.get("Month", "").strip()]
        assert len(total_rows) == 1, f"Expected 1 COGS total row, got {len(total_rows)}"

        total_amount = float(total_rows[0].get("Expense_Lacs", "0"))
        assert abs(total_amount - 4411.21) < 0.01, \
            f"COGS total is {total_amount}, expected 4411.21L"

    def test_pbi_assum_07_logistics_amounts(self, assumption_rows):
        """PBI-ASSUM-07: Logistics amounts reconcile to Q1 FY27 total 360.37L (base)"""
        logistics_rows = [r for r in assumption_rows
                          if r.get("Expense_Category", "").strip() == "LOGISTICS"
                          and r.get("Scenario", "").strip() == "Base"
                          and r.get("Financial_Year", "").strip() == "FY27"]

        total_rows = [r for r in logistics_rows if not r.get("Month", "").strip()]
        assert len(total_rows) == 1, f"Expected 1 Logistics total row, got {len(total_rows)}"

        total_amount = float(total_rows[0].get("Expense_Lacs", "0"))
        assert abs(total_amount - 360.37) < 0.01, \
            f"Logistics total is {total_amount}, expected 360.37L"

    def test_pbi_assum_08_no_approved_by_until_finance(self, assumption_rows):
        """PBI-ASSUM-08: Approved_By is blank (waiting for Finance)"""
        for row in assumption_rows:
            approved_by = row.get("Approved_By", "").strip()
            assert approved_by == "", \
                f"Approved_By should be blank, got '{approved_by}'"

    def test_pbi_assum_09_expense_amounts_positive(self, assumption_rows):
        """PBI-ASSUM-09: Expense_Lacs values are positive (no zero placeholders)"""
        for row in assumption_rows:
            try:
                amount = float(row.get("Expense_Lacs", "0"))
                assert amount > 0, \
                    f"Row {row.get('Expense_Category')}: Expense_Lacs is {amount}, must be > 0"
            except ValueError:
                pytest.fail(f"Row {row.get('Expense_Category')}: Expense_Lacs is not numeric")


class TestPowerBIFilesPresent:
    """Tests for all required Power BI assets"""

    def test_pbi_files_01_dax_provisional_measures(self):
        """PBI-FILES-01: DAX/14_CM2_Provisional_Measures.dax exists"""
        path = ROOT / "PowerBI" / "DAX" / "14_CM2_Provisional_Measures.dax"
        assert path.exists(), "14_CM2_Provisional_Measures.dax not found"

    def test_pbi_files_02_pq_import_guide(self):
        """PBI-FILES-02: Power Query import guide exists"""
        path = ROOT / "PowerBI" / "QuickSetup" / "PQ_CM2_Governance_Import.md"
        assert path.exists(), "PQ_CM2_Governance_Import.md not found"

    def test_pbi_files_03_page_blueprint(self):
        """PBI-FILES-03: Page blueprint for CM2 Analysis exists"""
        path = ROOT / "PowerBI" / "docs" / "PageBlueprint_CM2_Analysis_Provisional.md"
        assert path.exists(), "PageBlueprint_CM2_Analysis_Provisional.md not found"

    def test_pbi_files_04_governance_validation_script(self):
        """PBI-FILES-04: Governance validation script exists"""
        path = ROOT / "scripts" / "validate_cm2_governance_before_patch.py"
        assert path.exists(), "validate_cm2_governance_before_patch.py not found"


class TestReconciliation:
    """Tests for expense reconciliation logic"""

    @pytest.fixture
    def pl_expense_rows(self):
        path = ROOT / "PowerBI" / "SeedData" / "Masters" / "PL_Expense_Input.csv"
        with path.open(encoding="utf-8") as f:
            return list(csv.DictReader(f))

    @pytest.fixture
    def assumption_rows(self):
        path = ROOT / "PowerBI" / "SeedData" / "Masters" / "CM2_Provisional_Assumptions.csv"
        with path.open(encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def test_pbi_recon_01_no_zero_values(self, assumption_rows):
        """PBI-RECON-01: No zero-values used as missing-data placeholders"""
        for row in assumption_rows:
            try:
                amount = float(row.get("Expense_Lacs", "0"))
                if amount == 0:
                    pytest.fail(
                        f"Row {row.get('Expense_Category')} / {row.get('Scenario')}: "
                        f"Expense_Lacs is 0 — use blank instead for missing data"
                    )
            except ValueError:
                pass  # Blank is ok, numeric errors are ok

    def test_pbi_recon_02_example_data_marked(self, pl_expense_rows):
        """PBI-RECON-02: EXAMPLE rows are clearly marked"""
        for row in pl_expense_rows:
            remarks = row.get("Remarks", "").upper()
            if "EXAMPLE" in remarks:
                # These are the placeholder rows; they should be noted in Remarks
                assert "EXAMPLE ROW" in remarks, \
                    f"Row marked as example but Remarks don't clearly say 'EXAMPLE ROW'"

    def test_pbi_recon_03_no_negative_amounts_in_base(self, assumption_rows):
        """PBI-RECON-03: Base scenario amounts are all positive (no negative expenses)"""
        base_rows = [r for r in assumption_rows
                     if r.get("Scenario", "").strip() == "Base"]

        for row in base_rows:
            try:
                amount = float(row.get("Expense_Lacs", "0"))
                assert amount >= 0, \
                    f"Base scenario row {row.get('Expense_Category')}: negative amount {amount}"
            except ValueError:
                pass  # Skip non-numeric


class TestPatchScriptSafety:
    """Tests for patch_cm2_provisional.py safety"""

    def test_pbi_patch_01_validation_script_exists(self):
        """PBI-PATCH-01: Validation script exists to gate the patch"""
        path = ROOT / "scripts" / "validate_cm2_governance_before_patch.py"
        assert path.exists(), "validate_cm2_governance_before_patch.py not found"

    def test_pbi_patch_02_patch_script_exists(self):
        """PBI-PATCH-02: Patch script exists"""
        path = ROOT / "scripts" / "patch_cm2_provisional.py"
        assert path.exists(), "patch_cm2_provisional.py not found"

    def test_pbi_patch_03_patch_guards_amounts(self):
        """PBI-PATCH-03: Patch script never modifies CM2 amounts"""
        # Read the patch script and verify it contains the guard assertion
        path = ROOT / "scripts" / "patch_cm2_provisional.py"
        content = path.read_text(encoding="utf-8")
        assert "assert {k: dash[\"cm2\"].get(k) for k in amounts} == amounts" in content, \
            "Patch script missing amount-preservation guard"


class TestDAXMeasureStructure:
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
            assert measure in content, \
                f"DAX file missing measure: {measure}"

    def test_pbi_dax_02_lookupvalue_used_for_governance(self):
        """PBI-DAX-02: DAX uses LOOKUPVALUE to query governance table"""
        path = ROOT / "PowerBI" / "DAX" / "14_CM2_Provisional_Measures.dax"
        content = path.read_text(encoding="utf-8")

        assert "LOOKUPVALUE" in content, \
            "DAX should use LOOKUPVALUE to query governance table"
        assert "'CM2 Governance Status'" in content, \
            "DAX should reference 'CM2 Governance Status' table"

    def test_pbi_dax_03_approved_cm2_conditionally_blank(self):
        """PBI-DAX-03: Approved CM2 measure returns BLANK when pending"""
        path = ROOT / "PowerBI" / "DAX" / "14_CM2_Provisional_Measures.dax"
        content = path.read_text(encoding="utf-8")

        assert "IF ( [Formula_Status] = \"APPROVED\"" in content, \
            "Approved CM2 measure should check Formula_Status"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
