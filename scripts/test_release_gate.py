#!/usr/bin/env python3
"""
Test suite for Automated Release Gate.

Tests include:
- Baseline: current repository PASSES gate
- Deliberately injected failures to prove gate blocks them
- Finance-approved rule status checks
- Value-based tolerance validation
"""
import unittest
import pandas as pd
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
from release_gate import gate_pass, ReleaseGateReport, GateCheck


class TestReleaseGateBaseline(unittest.TestCase):
    """Tests: baseline repository should pass all mandatory gates."""

    def test_gate_with_no_data_passes(self):
        """Test 1: Gate with empty/None data should pass advisory checks."""
        passed, report = gate_pass()
        self.assertIsNotNone(report)
        self.assertEqual(len(report.checks), 10)

    def test_all_checks_present(self):
        """Test 2: All 10 checks should be in report."""
        passed, report = gate_pass()
        check_ids = [c.check_id for c in report.checks]
        expected_ids = ["G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8", "G9", "G10"]
        self.assertEqual(check_ids, expected_ids)

    def test_report_to_dict(self):
        """Test 3: Report should serialize to dict."""
        passed, report = gate_pass()
        d = report.to_dict()
        self.assertIn("gate_status", d)
        self.assertIn("checks", d)
        self.assertIsInstance(d["checks"], list)

    def test_mandatory_checks_identified(self):
        """Test 4: Mandatory checks should be marked correctly."""
        passed, report = gate_pass()
        mandatory = [c for c in report.checks if c.mandatory]
        # G1, G2, G3, G6, G10 are mandatory in base implementation
        self.assertGreater(len(mandatory), 0)

    def test_reconciliation_within_tolerance(self):
        """Test 5: Allocation reconciliation variance should be within tolerance."""
        config = {"reconciliation_variance_tolerance_pct": 0.01}
        allocation_reconciliation = {
            "Apr-26": {"original": 1000, "allocated": 1000, "variance": 0.0},
            "May-26": {"original": 2000, "allocated": 2000, "variance": 0.00001},
        }
        passed, report = gate_pass(
            allocation_reconciliation=allocation_reconciliation,
            config=config
        )
        g3 = [c for c in report.checks if c.check_id == "G3"][0]
        self.assertTrue(g3.passed)

    def test_unmapped_value_within_tolerance(self):
        """Test 6: Unmapped NSV should be within tolerance."""
        # Create DataFrame with 1% unmapped
        data = {
            'Chain': ['Apollo', 'Reliance', '_Unmapped'],
            'NSV': [980.0, 15.0, 5.0],
        }
        df = pd.DataFrame(data)
        config = {"unmapped_nsv_tolerance_pct": 2.0}
        passed, report = gate_pass(primary_df=df, config=config)
        g6 = [c for c in report.checks if c.check_id == "G6"][0]
        # 5 / 1000 = 0.5% < 2% tolerance
        self.assertTrue(g6.passed)

    def test_finance_approved_rules_pass(self):
        """Test 7: Finance-approved rules (APPROVED/PROVISIONAL) should pass."""
        config = {
            "negative_frac_treatment_status": "APPROVED",
            "jun26_allocation_status": "PROVISIONAL",
        }
        passed, report = gate_pass(config=config)
        g10 = [c for c in report.checks if c.check_id == "G10"][0]
        self.assertTrue(g10.passed)

    def test_reliance_bc_data_pass(self):
        """Test 8: Reliance BC isolation should pass when data is provided."""
        bc_data = pd.DataFrame({
            'Chain': ['Reliance BC', 'Reliance BC', 'Reliance BC'],
            'NSV': [100.0, 50.0, 25.0],
        })
        passed, report = gate_pass(reliance_bc_data=bc_data)
        g7 = [c for c in report.checks if c.check_id == "G7"][0]
        self.assertTrue(g7.passed)
        self.assertEqual(g7.actual_value, 175.0)

    def test_primary_schema_with_valid_df(self):
        """Test 9: Primary schema validation should pass with valid DataFrame."""
        df = pd.DataFrame({
            'Chain': ['Apollo', 'Dmart'],
            'NSV': [100.0, 200.0],
            'MRP': [150.0, 250.0],
            'Qty': [50, 100],
        })
        passed, report = gate_pass(primary_df=df)
        g1 = [c for c in report.checks if c.check_id == "G1"][0]
        self.assertTrue(g1.passed)


class TestReleaseGateFailures(unittest.TestCase):
    """Tests: deliberately injected failures to prove gate blocks them."""

    def test_failure_unmapped_exceeds_tolerance(self):
        """Test F1: Gate should FAIL when unmapped NSV exceeds tolerance."""
        # Create DataFrame with 5% unmapped (exceeds 2% tolerance)
        data = {
            'Chain': ['Apollo', 'Reliance', '_Unmapped'],
            'NSV': [900.0, 100.0, 50.0],  # 50/1050 = 4.76% > 2%
        }
        df = pd.DataFrame(data)
        config = {"unmapped_nsv_tolerance_pct": 2.0}
        passed, report = gate_pass(primary_df=df, config=config)
        g6 = [c for c in report.checks if c.check_id == "G6"][0]
        self.assertFalse(g6.passed)
        self.assertTrue(g6.mandatory)
        self.assertGreater(g6.actual_value, g6.threshold)

    def test_failure_reconciliation_exceeds_tolerance(self):
        """Test F2: Gate should FAIL when reconciliation variance exceeds tolerance."""
        config = {"reconciliation_variance_tolerance_pct": 0.01}
        allocation_reconciliation = {
            "Apr-26": {"original": 1000, "allocated": 1010, "variance": 1.0},  # 1% > 0.01% tolerance
        }
        passed, report = gate_pass(
            allocation_reconciliation=allocation_reconciliation,
            config=config
        )
        g3 = [c for c in report.checks if c.check_id == "G3"][0]
        self.assertFalse(g3.passed)
        self.assertTrue(g3.mandatory)

    def test_failure_negative_frac_blocked(self):
        """Test F3: Gate should FAIL when negative frac treatment is BLOCKED."""
        config = {
            "negative_frac_treatment_status": "BLOCKED",
            "jun26_allocation_status": "APPROVED",
        }
        passed, report = gate_pass(config=config)
        g10 = [c for c in report.checks if c.check_id == "G10"][0]
        self.assertFalse(g10.passed)
        self.assertTrue(g10.mandatory)

    def test_failure_jun26_blocked_still_fails_g10(self):
        """Test F4: Gate G10 should fail if jun26 is BLOCKED (though not mandatory)."""
        config = {
            "negative_frac_treatment_status": "APPROVED",
            "jun26_allocation_status": "BLOCKED",
        }
        passed, report = gate_pass(config=config)
        g10 = [c for c in report.checks if c.check_id == "G10"][0]
        self.assertFalse(g10.passed)

    def test_failure_missing_required_columns(self):
        """Test F5: Schema validation should FAIL with missing required columns."""
        # DataFrame without required columns
        df = pd.DataFrame({
            'RandomCol': [1, 2, 3],
        })
        passed, report = gate_pass(primary_df=df)
        g1 = [c for c in report.checks if c.check_id == "G1"][0]
        self.assertFalse(g1.passed)
        self.assertTrue(g1.mandatory)

    def test_mandatory_vs_advisory(self):
        """Test 10: Advisory failures should not block gate."""
        # Create DataFrame with required columns and good unmapped data
        df = pd.DataFrame({
            'Chain': ['Apollo', 'Reliance', 'Dmart'],
            'NSV': [490.0, 500.0, 10.0],  # 1% unmapped, within 2% tolerance
            'MRP': [600.0, 700.0, 50.0],
            'Qty': [100, 150, 20],
        })
        config = {
            "tot_fallback_max_pct": 20.0,
            "unmapped_nsv_tolerance_pct": 2.0,
        }
        tot_data = {
            "fallback_coverage_pct": 50.0,  # Exceeds 20% (advisory failure)
        }
        passed, report = gate_pass(primary_df=df, tot_data=tot_data, config=config)
        g8 = [c for c in report.checks if c.check_id == "G8"][0]
        self.assertFalse(g8.passed)
        self.assertFalse(g8.mandatory)  # Advisory, so gate can still pass
        # Overall gate should still pass because only advisory G8 failed
        self.assertTrue(passed)

    def test_multiple_failures_all_reported(self):
        """Test 11: Multiple failures should all be reported in gate report."""
        # Inject multiple failures
        df = pd.DataFrame({
            'Chain': ['Apollo', '_Unmapped'],
            'NSV': [500.0, 500.0],  # 50% unmapped
        })
        config = {
            "unmapped_nsv_tolerance_pct": 2.0,
            "negative_frac_treatment_status": "BLOCKED",
        }
        passed, report = gate_pass(primary_df=df, config=config)
        failures = [c for c in report.checks if not c.passed]
        # Should have at least G6 and G10 failures
        self.assertGreaterEqual(len(failures), 2)

    def test_gate_pass_false_on_mandatory_failure(self):
        """Test 12: gate_pass() should return False when mandatory check fails."""
        config = {"negative_frac_treatment_status": "BLOCKED"}
        passed, report = gate_pass(config=config)
        self.assertFalse(passed)
        # Verify it's actually from a mandatory check
        mandatory_failures = [c for c in report.checks if not c.passed and c.mandatory]
        self.assertGreater(len(mandatory_failures), 0)


class TestReleaseGateIntegration(unittest.TestCase):
    """Tests: integration with real-world data patterns."""

    def test_real_world_primary_allocation(self):
        """Test I1: Real-world primary allocation pattern."""
        # Simulate primary block output
        df = pd.DataFrame({
            'Chain': ['Apollo', 'Reliance', 'Dmart', 'Lulu'] * 5,
            'Zone': ['East', 'East', 'South', 'North'] * 5,
            'Brand': ['Mamearth'] * 20,
            'Channel': ['MT'] * 20,
            'NSV': [1000.0, 2000.0, 1500.0, 800.0] * 5,
            'MRP': [1500.0, 3000.0, 2000.0, 1200.0] * 5,
            'Qty': [500, 1000, 750, 400] * 5,
        })
        config = {
            "allocation_coverage_min_pct": 95.0,
            "unmapped_nsv_tolerance_pct": 5.0,  # Lenient to accommodate real-world data
        }
        passed, report = gate_pass(primary_df=df, config=config)
        # Verify no mandatory checks failed (all mandatory should pass with good data)
        mandatory_failures = [c for c in report.checks if c.mandatory and not c.passed]
        self.assertEqual(len(mandatory_failures), 0,
                        f"Mandatory checks failed: {[c.name for c in mandatory_failures]}")

    def test_reconciliation_with_multiple_months(self):
        """Test I2: Reconciliation across multiple months."""
        allocation_reconciliation = {
            "Apr-26": {"original": 10000, "allocated": 10000, "variance": 0.0},
            "May-26": {"original": 10500, "allocated": 10500, "variance": 0.00001},
            "Jun-26": {"original": 11000, "allocated": 11000, "variance": 0.0},
            "Jul-26": {"original": 12000, "allocated": 12000, "variance": 0.0},
        }
        config = {"reconciliation_variance_tolerance_pct": 0.01}
        passed, report = gate_pass(
            allocation_reconciliation=allocation_reconciliation,
            config=config
        )
        g3 = [c for c in report.checks if c.check_id == "G3"][0]
        self.assertTrue(g3.passed)

    def test_report_json_serialization(self):
        """Test I3: Report should be JSON-serializable."""
        df = pd.DataFrame({
            'Chain': ['Apollo'],
            'NSV': [100.0],
            'MRP': [150.0],
            'Qty': [50],
        })
        passed, report = gate_pass(primary_df=df)
        d = report.to_dict()
        # Should be JSON-able
        import json
        json_str = json.dumps(d)
        self.assertGreater(len(json_str), 0)


class TestReleaseGateReport(unittest.TestCase):
    """Tests: report generation and formatting."""

    def test_report_print_no_error(self):
        """Test R1: Report printing should not raise exception."""
        passed, report = gate_pass()
        try:
            report.print_report()
        except Exception as e:
            self.fail(f"report.print_report() raised {e}")

    def test_gate_check_to_dict(self):
        """Test R2: GateCheck.to_dict() should have required fields."""
        check = GateCheck(
            check_id="G0",
            name="Test Check",
            mandatory=True,
            passed=True,
            actual_value=50.0,
            threshold=100.0,
            source="Test",
            reason="Test reason"
        )
        d = check.to_dict()
        self.assertIn("check_id", d)
        self.assertIn("name", d)
        self.assertIn("mandatory", d)
        self.assertIn("passed", d)
        self.assertIn("actual_value", d)
        self.assertIn("threshold", d)
        self.assertIn("source", d)
        self.assertIn("reason", d)
        self.assertEqual(d["passed"], "PASS")

    def test_report_summary_counts(self):
        """Test R3: Report should accurately count passes/failures."""
        df = pd.DataFrame({
            'Chain': ['Apollo', '_Unmapped'],
            'NSV': [500.0, 500.0],
        })
        config = {"unmapped_nsv_tolerance_pct": 1.0}
        passed, report = gate_pass(primary_df=df, config=config)
        d = report.to_dict()
        self.assertEqual(d["total_checks"], 10)
        self.assertGreater(d["failed_count"], 0)
        self.assertEqual(d["failed_count"] + d["passed_count"], 10)


if __name__ == "__main__":
    unittest.main(verbosity=2)
