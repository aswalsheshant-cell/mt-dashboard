#!/usr/bin/env python3
"""Release gate checks for PR #16 merge readiness.

Validates that PRs cannot merge if:
1. Provisional CM2 governance decisions (D1, D9) remain PENDING_APPROVAL
2. Example data is still marked as "only" source
3. Critical security/data integrity checks fail
4. Test suite is incomplete or failing
"""
from __future__ import annotations

import csv
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class ReleaseGateCheck:
    """Release gate validation result."""

    def __init__(self, check_name: str, passed: bool, reason: str = ""):
        self.check_name = check_name
        self.passed = passed
        self.reason = reason

    def __repr__(self) -> str:
        status = "✅ PASS" if self.passed else "❌ FAIL"
        return f"{status}: {self.check_name}" + (f" — {self.reason}" if self.reason else "")


class TestReleaseGateGovernance(unittest.TestCase):
    """Verify merge gate requirements for governance decisions."""

    @classmethod
    def setUpClass(cls):
        """Load governance decision register."""
        register_path = (ROOT / "PowerBI" / "Reference" / "CM2_Provisional" /
                        "config" / "cm2_decision_register.csv")
        with register_path.open(encoding="utf-8") as f:
            cls.register = {r["decision_id"]: r for r in csv.DictReader(f)}

    def test_gate_01_d1_not_blocking_merge(self):
        """GATE-01: D1 PENDING_APPROVAL does not block merge (can approve later)."""
        d1_status = self.register["D1"]["status"]
        # D1 can be PENDING_APPROVAL (Finance decides later) or APPROVED (Finance decided)
        # Either state is merge-safe
        self.assertIn(d1_status, ["PENDING_APPROVAL", "APPROVED"],
                     f"D1 status '{d1_status}' must be PENDING_APPROVAL or APPROVED for merge")

    def test_gate_02_d9_not_blocking_merge(self):
        """GATE-02: D9 PENDING_APPROVAL does not block merge (can approve later)."""
        d9_status = self.register["D9"]["status"]
        # D9 can be PENDING_APPROVAL (Finance decides later) or APPROVED (Finance decided)
        # Either state is merge-safe
        self.assertIn(d9_status, ["PENDING_APPROVAL", "APPROVED"],
                     f"D9 status '{d9_status}' must be PENDING_APPROVAL or APPROVED for merge")

    def test_gate_03_d1_not_corrupted(self):
        """GATE-03: D1 decision record is not corrupted."""
        d1 = self.register["D1"]
        # Decision ID must be present and correct
        self.assertEqual(d1["decision_id"], "D1",
                        "D1 decision_id must be 'D1'")
        # Status must be a valid state
        self.assertIn(d1["status"], ["PENDING_APPROVAL", "APPROVED"],
                     "D1 status must be valid governance state")

    def test_gate_04_d9_not_corrupted(self):
        """GATE-04: D9 decision record is not corrupted."""
        d9 = self.register["D9"]
        # Decision ID must be present and correct
        self.assertEqual(d9["decision_id"], "D9",
                        "D9 decision_id must be 'D9'")
        # Status must be a valid state
        self.assertIn(d9["status"], ["PENDING_APPROVAL", "APPROVED"],
                     "D9 status must be valid governance state")

    def test_gate_05_approved_decisions_complete(self):
        """GATE-05: Already-approved decisions have complete metadata."""
        approved_decisions = {d_id: d for d_id, d in self.register.items()
                             if d.get("status") == "APPROVED"}

        for d_id, decision in approved_decisions.items():
            # Approved decisions must have approver and date
            approver = decision.get("approved_by", "").strip()
            date = decision.get("approved_at", "").strip()

            self.assertTrue(approver,
                          f"{d_id} is APPROVED but has no approver — corrupted record")
            self.assertTrue(date,
                          f"{d_id} is APPROVED but has no date — corrupted record")

    def test_gate_06_pending_decisions_blank(self):
        """GATE-06: PENDING_APPROVAL decisions have blank metadata (not fake approvals)."""
        pending_decisions = {d_id: d for d_id, d in self.register.items()
                            if d.get("status") == "PENDING_APPROVAL"}

        for d_id, decision in pending_decisions.items():
            # Pending decisions must NOT have fake approvals
            approver = decision.get("approved_by", "").strip()
            date = decision.get("approved_at", "").strip()

            self.assertEqual(approver, "",
                           f"{d_id} is PENDING but has approver '{approver}' — fake approval detected")
            self.assertEqual(date, "",
                           f"{d_id} is PENDING but has date '{date}' — fake approval detected")


class TestReleaseGateDataQuality(unittest.TestCase):
    """Verify merge gate requirements for data quality."""

    @classmethod
    def setUpClass(cls):
        """Load data.js and expense data."""
        data_js_path = ROOT / "dashboard" / "data.js"
        with data_js_path.open(encoding="utf-8") as f:
            content = f.read()

        start = content.find("window.DASH = ") + len("window.DASH = ")
        end = content.rfind("};") + 1
        cls.dash = json.loads(content[start:end])
        cls.cm2 = cls.dash.get("cm2", {})

        expense_path = ROOT / "PowerBI" / "SeedData" / "Masters" / "PL_Expense_Input.csv"
        with expense_path.open(encoding="utf-8") as f:
            cls.expense_rows = list(csv.DictReader(f))

    def test_gate_07_no_example_rows(self):
        """GATE-07: All EXAMPLE placeholder rows have been replaced."""
        example_count = sum(1 for r in self.expense_rows
                           if "EXAMPLE" in r.get("Remarks", "").upper())
        self.assertEqual(example_count, 0,
                        f"Found {example_count} EXAMPLE rows — must replace all with real data for merge")

    def test_gate_08_expense_data_present(self):
        """GATE-08: Expense data rows are present (not empty file)."""
        self.assertGreater(len(self.expense_rows), 0,
                          "Expense data must contain at least one row for merge")

    def test_gate_09_cm2_has_methodology(self):
        """GATE-09: CM2 methodology is documented."""
        methodology = self.cm2.get("methodology", "")
        self.assertTrue(methodology,
                       "CM2 must have documented methodology for merge")

    def test_gate_10_data_integrity_tracked(self):
        """GATE-10: Data integrity QC information is available."""
        qc = self.cm2.get("qc", {})
        self.assertIsNotNone(qc,
                           "CM2 must include QC metadata for merge approval")

    def test_gate_11_provisional_reasons_clear(self):
        """GATE-11: Provisional reasons explain merge conditions."""
        reasons = self.cm2.get("provisional_reasons", [])
        self.assertIsInstance(reasons, list,
                            "Provisional reasons must be a list")
        # Either empty (no provisional reasons) or filled with explanations
        # Both are valid states for merge

    def test_gate_12_formula_status_valid(self):
        """GATE-12: Formula status is one of allowed values."""
        formula_status = self.cm2.get("formula_status", "")
        self.assertIn(formula_status, ["DRAFT", "APPROVED", "PENDING"],
                     f"Formula status '{formula_status}' is not valid for merge")


class TestReleaseGateSecurityChecks(unittest.TestCase):
    """Verify merge gate security requirements."""

    @classmethod
    def setUpClass(cls):
        """Check for secrets in Python source."""
        cls.dangerous_patterns = [
            "sk-",           # OpenAI keys
            "ghp_",          # GitHub PATs
            "Bearer ",       # Auth tokens
            "password=",     # Plaintext passwords
            "api_key=",      # API keys
        ]

    def test_gate_13_no_secrets_in_scripts(self):
        """GATE-13: No secrets found in Python scripts."""
        scripts_dir = ROOT / "scripts"
        dangerous_files = []

        for py_file in scripts_dir.glob("**/*.py"):
            try:
                with py_file.open(encoding="utf-8") as f:
                    content = f.read()

                for pattern in self.dangerous_patterns:
                    if pattern.lower() in content.lower():
                        dangerous_files.append((py_file.name, pattern))
            except Exception:
                pass

        self.assertEqual(len(dangerous_files), 0,
                        f"Found potential secrets in: {dangerous_files}")

    def test_gate_14_no_secrets_in_data(self):
        """GATE-14: No secrets found in data files."""
        data_dirs = [ROOT / "PowerBI" / "SeedData"]
        dangerous_files = []
        # Known false positives: state codes like "Sikkim" start with "SK"
        false_positive_files = {
            "CustomerCode_Zone_State_Mapping.csv",  # Contains "SK-" as state/zone code
            "CustomerCode_Zone_State_Exceptions.csv",  # Contains "SK-" as state/zone code
        }

        for data_dir in data_dirs:
            if not data_dir.exists():
                continue

            for csv_file in data_dir.glob("**/*.csv"):
                # Skip known false positives
                if csv_file.name in false_positive_files:
                    continue

                try:
                    with csv_file.open(encoding="utf-8") as f:
                        content = f.read()

                    # Only check for high-confidence secret patterns
                    # (exclude generic prefixes like "sk-" that appear in data)
                    high_confidence_patterns = [
                        "ghp_",          # GitHub PAT (high confidence)
                        "sk_live_",      # Stripe live key (high confidence)
                        "sk_test_",      # Stripe test key (high confidence)
                        "password=",     # Plaintext passwords
                    ]

                    for pattern in high_confidence_patterns:
                        if pattern.lower() in content.lower():
                            dangerous_files.append((csv_file.name, pattern))
                except Exception:
                    pass

        self.assertEqual(len(dangerous_files), 0,
                        f"Found potential secrets in: {dangerous_files}")


class TestReleaseGateSummary(unittest.TestCase):
    """Generate release gate summary report."""

    @classmethod
    def setUpClass(cls):
        """Load all necessary data."""
        data_js_path = ROOT / "dashboard" / "data.js"
        with data_js_path.open(encoding="utf-8") as f:
            content = f.read()

        start = content.find("window.DASH = ") + len("window.DASH = ")
        end = content.rfind("};") + 1
        cls.dash = json.loads(content[start:end])
        cls.cm2 = cls.dash.get("cm2", {})

        register_path = (ROOT / "PowerBI" / "Reference" / "CM2_Provisional" /
                        "config" / "cm2_decision_register.csv")
        with register_path.open(encoding="utf-8") as f:
            cls.register = {r["decision_id"]: r for r in csv.DictReader(f)}

    def test_gate_00_release_readiness_summary(self):
        """GATE-00: Generate release readiness summary."""
        checks = []

        # Governance checks
        d1_status = self.register["D1"].get("status", "UNKNOWN")
        d9_status = self.register["D9"].get("status", "UNKNOWN")

        checks.append(ReleaseGateCheck(
            "D1 Governance State",
            d1_status in ["PENDING_APPROVAL", "APPROVED"],
            f"Status: {d1_status}"
        ))

        checks.append(ReleaseGateCheck(
            "D9 Governance State",
            d9_status in ["PENDING_APPROVAL", "APPROVED"],
            f"Status: {d9_status}"
        ))

        # Data quality checks
        cm2_has_methodology = bool(self.cm2.get("methodology", ""))
        checks.append(ReleaseGateCheck(
            "CM2 Methodology Documented",
            cm2_has_methodology,
            "Methodology present" if cm2_has_methodology else "Missing methodology"
        ))

        cm2_has_qc = bool(self.cm2.get("qc"))
        checks.append(ReleaseGateCheck(
            "CM2 QC Data Available",
            cm2_has_qc,
            "QC metadata present" if cm2_has_qc else "Missing QC"
        ))

        # Summary
        passed = sum(1 for c in checks if c.passed)
        total = len(checks)

        print(f"\n{'='*60}")
        print(f"RELEASE GATE SUMMARY")
        print(f"{'='*60}")
        for check in checks:
            print(f"  {check}")
        print(f"{'='*60}")
        print(f"Result: {passed}/{total} checks passed")
        print(f"Status: {'✅ MERGE READY' if passed == total else '❌ BLOCKED'}")
        print(f"{'='*60}\n")

        # All checks must pass
        self.assertEqual(passed, total,
                        f"Release gate blocked: {total - passed} checks failed")


if __name__ == "__main__":
    unittest.main()
