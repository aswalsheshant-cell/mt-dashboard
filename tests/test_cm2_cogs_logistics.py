#!/usr/bin/env python3
"""Regression tests for the FY27 provisional CM2 calculation.

Locks the approved bases (D10): COGS on GMV/MRP, logistics on NSV, computed
independently. Run: python3 -m unittest discover -s tests -v
"""
import csv
import hashlib
import json
import pathlib
import subprocess
import sys
import unittest
from decimal import Decimal

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import cm2_cogs_logistics_fy27 as cm2  # noqa: E402

D = Decimal
PRODUCTION_FILES = [
    "dashboard/data.js",
    "dashboard/index.html",
    "scripts/build_dashboard_data.py",
]


class TestApprovedBases(unittest.TestCase):
    """1-5: the bases themselves."""

    def test_01_cogs_calculated_on_gmv_mrp(self):
        _, cogs, *_ = cm2.compute_month(D("60"), D("100"), D("30"), D("3"))
        self.assertEqual(cogs, D("30"))          # 100 * 30% -- GMV base

    def test_02_logistics_calculated_on_nsv(self):
        _, _, log, *_ = cm2.compute_month(D("60"), D("100"), D("30"), D("3"))
        self.assertEqual(log, D("1.8"))          # 60 * 3% -- NSV base

    def test_03_cogs_is_never_calculated_on_nsv(self):
        _, cogs, *_ = cm2.compute_month(D("60"), D("100"), D("30"), D("3"))
        self.assertNotEqual(cogs, D("60") * D("0.30"))

    def test_04_logistics_is_never_calculated_on_gmv_mrp(self):
        _, _, log, *_ = cm2.compute_month(D("60"), D("100"), D("30"), D("3"))
        self.assertNotEqual(log, D("100") * D("0.03"))

    def test_05_different_bases_produce_different_costs(self):
        """Swapping the bases must change the answer -- proves they are not aliased."""
        _, cogs_a, log_a, *_ = cm2.compute_month(D("60"), D("100"), D("30"), D("3"))
        _, cogs_b, log_b, *_ = cm2.compute_month(D("100"), D("60"), D("30"), D("3"))
        self.assertNotEqual(cogs_a, cogs_b)
        self.assertNotEqual(log_a, log_b)

    def test_05b_finance_worked_example(self):
        """GMV 100L, NSV 60L, COGS 30%, logistics 3% -> CM2 28.2L @ 47%."""
        status, cogs, log, cost, cm2_val, cm2_pct = cm2.compute_month(
            D("60"), D("100"), D("30"), D("3"))
        self.assertEqual(status, cm2.CALCULATED)
        self.assertEqual(cogs, D("30"))
        self.assertEqual(log, D("1.8"))
        self.assertEqual(cost, D("31.8"))
        self.assertEqual(cm2_val, D("28.2"))
        self.assertEqual(cm2.q2(cm2_pct), D("47.00"))


class TestArithmetic(unittest.TestCase):
    """6-8: precision, percentages, units."""

    def test_06_exact_decimal_no_binary_float(self):
        _, cogs, log, cost, cm2_val, _ = cm2.compute_month(
            D("4416.06"), D("10275.28"), D("13.67"), D("2.83"))
        for v in (cogs, log, cost, cm2_val):
            self.assertIsInstance(v, Decimal)
        self.assertEqual(cogs + log, cost)                    # exact, no drift
        self.assertEqual(D("4416.06") - cost, cm2_val)

    def test_07_percentage_conversion(self):
        self.assertEqual(cm2.pct(D("14.05")), D("0.1405"))
        self.assertNotEqual(cm2.pct(D("14.05")), D("14.05"))

    def test_08_unit_conversion_rupees_to_lakh(self):
        self.assertEqual(D("1177546281") / cm2.RUPEES_PER_LAKH, D("11775.46281"))

    def test_08b_nsv_unit_validated_against_data_js(self):
        _, meta = cm2.load_nsv_monthly()
        self.assertEqual(meta["unit"], "INR Lakh")


class TestMissingData(unittest.TestCase):
    """9-13, 15-17: controlled statuses. Never guess a base."""

    def test_09_missing_gmv_mrp_blocks_cogs(self):
        status, cogs, log, cost, cm2_val, _ = cm2.compute_month(
            D("4167.36"), None, D("14.56"), D("4.09"))
        self.assertEqual(status, cm2.GMV_MRP_MISSING)
        self.assertIsNone(cogs)
        self.assertIsNone(cost)
        self.assertIsNone(cm2_val)
        self.assertIsNotNone(log)          # logistics still computable as memo

    def test_10_missing_nsv_blocks_cm2_and_logistics(self):
        status, _, log, _, cm2_val, _ = cm2.compute_month(
            None, D("100"), D("14"), D("4"))
        self.assertEqual(status, cm2.NSV_MISSING)
        self.assertIsNone(log)
        self.assertIsNone(cm2_val)

    def test_11_missing_rates(self):
        self.assertEqual(cm2.compute_month(D("60"), D("100"), None, D("3"))[0],
                         cm2.COGS_RATE_MISSING)
        self.assertEqual(cm2.compute_month(D("60"), D("100"), D("30"), None)[0],
                         cm2.LOGISTICS_RATE_MISSING)

    def test_12_zero_sales_month(self):
        self.assertEqual(cm2.compute_month(D("0"), D("0"), D("14"), D("4"))[0],
                         cm2.NO_SALES_MONTH)

    def test_13_future_month_not_extrapolated(self):
        rows, _, _, _, _ = cm2.build_rows()
        by_month = {r["Month"]: r for r in rows}
        for m in ["Jul-26", "Aug-26", "Sep-26", "Oct-26", "Nov-26",
                  "Dec-26", "Jan-27", "Feb-27", "Mar-27"]:
            self.assertEqual(by_month[m]["Status"], cm2.NO_SALES_MONTH)
            self.assertEqual(by_month[m]["Provisional_CM2_L"], "")

    def test_15_negative_nsv_preserved(self):
        status, _, log, _, cm2_val, _ = cm2.compute_month(
            D("-50"), D("100"), D("30"), D("3"))
        self.assertEqual(status, cm2.CALCULATED)
        self.assertEqual(log, D("-1.5"))            # sign preserved, not abs()
        self.assertEqual(cm2_val, D("-50") - (D("30") + D("-1.5")))

    def test_16_negative_gmv_mrp_preserved(self):
        _, cogs, *_ = cm2.compute_month(D("60"), D("-100"), D("30"), D("3"))
        self.assertEqual(cogs, D("-30"))

    def test_17_invalid_rates_rejected(self):
        self.assertEqual(cm2.compute_month(D("60"), D("100"), D("-5"), D("3"))[0],
                         cm2.INVALID_RATE)
        self.assertEqual(cm2.compute_month(D("60"), D("100"), D("150"), D("3"))[0],
                         cm2.INVALID_RATE)


class TestSubtotal(unittest.TestCase):
    """14: Q1 percentage is weighted, never an average of monthly percentages."""

    def test_14_q1_cm2_pct_is_weighted_not_averaged(self):
        rows, totals, n_calc, _, _ = cm2.build_rows()
        sub = rows[-1]
        self.assertEqual(sub["Status"], "SUBTOTAL_CALCULATED_ONLY")
        weighted = totals["cm2"] / totals["nsv"] * D("100")
        self.assertEqual(sub["Provisional_CM2_Pct"], cm2.q2(weighted))

        monthly_pcts = [D(r["Provisional_CM2_Pct"]) for r in rows[:-1]
                        if r["Provisional_CM2_Pct"] != ""]
        naive_avg = sum(monthly_pcts) / len(monthly_pcts)
        self.assertNotEqual(cm2.q2(weighted), cm2.q2(naive_avg))

    def test_14b_subtotal_covers_calculated_months_only(self):
        rows, _, n_calc, _, _ = cm2.build_rows()
        calc = [r for r in rows[:-1] if r["Status"] == cm2.CALCULATED]
        self.assertEqual(len(calc), n_calc)
        self.assertIn(f"({n_calc} months)", rows[-1]["Month"])


class TestJun26Reconciliation(unittest.TestCase):
    """D12: Jun-26 GMV/MRP recovered from an authoritative source, not estimated."""

    TOLERANCE_L = D("0.12")          # project PASS tolerance
    DATA_JS_JUN_NSV = D("4167.36")

    def _seed_row(self):
        with open(ROOT / "PowerBI/SeedData/Masters/FY27_Monthly_GMV_MRP.csv",
                  encoding="utf-8") as fh:
            return {r["Month"]: r for r in csv.DictReader(fh)}["Jun-26"]

    def test_21_jun26_is_calculated_not_missing(self):
        rows, _, _, _, _ = cm2.build_rows()
        jun = {r["Month"]: r for r in rows}["Jun-26"]
        self.assertEqual(jun["Status"], cm2.CALCULATED)
        self.assertEqual(D(jun["GMV_MRP_Sales_L"]), D("9300.91"))
        self.assertEqual(D(jun["COGS_L"]), D("1354.21"))

    def test_22_seed_nsv_control_reconciles_to_data_js(self):
        """The recovered source must reproduce the known Jun-26 NSV."""
        control = D(self._seed_row()["NSV_Control_L"])
        self.assertLessEqual(abs(control - self.DATA_JS_JUN_NSV), self.TOLERANCE_L)

    def test_23_seed_is_hash_pinned_and_authoritative(self):
        row = self._seed_row()
        self.assertEqual(row["Status"], "AUTHORITATIVE")
        self.assertRegex(row["Source_SHA256"], r"^[0-9a-f]{64}$")
        self.assertTrue(row["Source_Sheet"].strip())

    def test_24_non_authoritative_seed_rows_are_ignored(self):
        """An estimated row must never silently become a base."""
        import tempfile
        original = cm2.GMV_SEED
        try:
            with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False,
                                             newline="", encoding="utf-8") as fh:
                w = csv.writer(fh, lineterminator="\n")
                w.writerow(["Month", "GMV_MRP_Sales_L", "NSV_Control_L", "Source_File",
                            "Source_SHA256", "Source_Sheet", "Field", "Extraction_Rule",
                            "Rows_Total", "Rows_After_Exclusion", "Recorded_By",
                            "Recorded_At", "Status", "Notes"])
                w.writerow(["Jun-26", "9999.99", "0", "guess.xlsx", "x", "s", "f",
                            "estimated", "0", "0", "test", "2026-07-24", "ESTIMATED", ""])
                cm2.GMV_SEED = pathlib.Path(fh.name)
            seed, _ = cm2.load_gmv_mrp_seed()
            self.assertEqual(seed, {})
        finally:
            cm2.GMV_SEED = original

    def test_25_no_nsv_to_gmv_ratio_used(self):
        """Jun MRP must not equal NSV scaled by any Apr/May-derived ratio."""
        jun_mrp = D("9300.91")
        apr_ratio = D("11760.60") / D("5069.17")
        may_ratio = D("10275.28") / D("4416.06")
        blended = (D("11760.60") + D("10275.28")) / (D("5069.17") + D("4416.06"))
        for ratio in (apr_ratio, may_ratio, blended):
            self.assertNotEqual(cm2.q2(self.DATA_JS_JUN_NSV * ratio), jun_mrp)

    def test_26_article_csv_wins_over_seed(self):
        """A month with a tracked CSV must resolve from the CSV, not the seed."""
        _, meta = cm2.load_gmv_mrp_monthly()
        self.assertEqual(meta["per_month"]["Apr-26"]["resolved_via"], "article_csv")
        self.assertEqual(meta["per_month"]["May-26"]["resolved_via"], "article_csv")
        self.assertEqual(meta["per_month"]["Jun-26"]["resolved_via"], "seed")

    def test_27_fy27_mrp_aggregate_defect_is_documented(self):
        """data.js FY27 mrp is wrong; D13 must track it and CM2 must not use it."""
        with open(ROOT / "PowerBI" / "Reference" / "CM2_Provisional" / "config" / "cm2_decision_register.csv", encoding="utf-8") as fh:
            reg = {r["decision_id"]: r for r in csv.DictReader(fh)}
        self.assertIn("D13", reg)
        self.assertEqual(reg["D12"]["status"], "APPROVED")
        src = (ROOT / "scripts/cm2_cogs_logistics_fy27.py").read_text(encoding="utf-8")
        self.assertNotIn('fy27["mrp"]', src)


class TestGovernance(unittest.TestCase):
    """18-19: config must carry explicit bases and record the D10 approval."""

    def test_18_formula_config_has_explicit_bases(self):
        with open(ROOT / "PowerBI" / "Reference" / "CM2_Provisional" / "config" / "cm2_formula.csv", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        self.assertTrue(rows)
        for r in rows:
            self.assertIn("Calculation_Basis", r)
            self.assertTrue(r["Calculation_Basis"].strip(),
                            f"{r['Component']} has no explicit basis -- silent NSV default risk")
        by_comp = {r["Component"]: r for r in rows}
        self.assertEqual(by_comp["Approved product cost"]["Calculation_Basis"], "GMV_MRP_SALES")
        self.assertEqual(by_comp["Approved logistics cost"]["Calculation_Basis"], "NSV")

    def test_19_d10_approval_recorded(self):
        with open(ROOT / "PowerBI" / "Reference" / "CM2_Provisional" / "config" / "cm2_decision_register.csv", encoding="utf-8") as fh:
            rows = {r["decision_id"]: r for r in csv.DictReader(fh)}
        self.assertEqual(rows["D10"]["status"], "APPROVED")
        self.assertTrue(rows["D10"]["approved_by"].strip())
        self.assertEqual(rows["D11"]["status"], "APPROVED")

    def test_19b_d1_and_d9_remain_pending(self):
        """An approved basis must not leak into an approved inclusion."""
        with open(ROOT / "PowerBI" / "Reference" / "CM2_Provisional" / "config" / "cm2_decision_register.csv", encoding="utf-8") as fh:
            rows = {r["decision_id"]: r for r in csv.DictReader(fh)}
        self.assertEqual(rows["D1"]["status"], "PENDING_APPROVAL")
        self.assertEqual(rows["D9"]["status"], "PENDING_APPROVAL")

    def test_19c_no_taxonomy_row_is_include(self):
        with open(ROOT / "PowerBI" / "Reference" / "CM2_Provisional" / "config" / "cm2_expense_taxonomy.csv", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        self.assertEqual([r for r in rows if r["CM2_Inclusion_Status"] == "INCLUDE"], [])

    def test_19d_cogs_and_logistics_are_separate_groups(self):
        with open(ROOT / "PowerBI" / "Reference" / "CM2_Provisional" / "config" / "cm2_expense_taxonomy.csv", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        groups = {r["Expense_Group"] for r in rows}
        self.assertIn("PRODUCT COST", groups)
        self.assertIn("LOGISTICS COST", groups)


class TestRepositorySafety(unittest.TestCase):
    """20: production files must be byte-identical to HEAD."""

    def test_20_production_dashboard_unchanged(self):
        for rel in PRODUCTION_FILES:
            head = subprocess.run(["git", "show", f"HEAD:{rel}"], cwd=ROOT,
                                  capture_output=True, check=True).stdout
            disk = (ROOT / rel).read_bytes()
            self.assertEqual(hashlib.sha256(head).hexdigest(),
                             hashlib.sha256(disk).hexdigest(),
                             f"{rel} differs from HEAD -- production file was modified")

    def test_20b_output_metadata_declares_provisional(self):
        meta = json.loads((ROOT / "outputs/cm2/cm2_fy27_cogs_logistics.meta.json")
                          .read_text(encoding="utf-8"))
        self.assertEqual(meta["calculation_status"], "PROVISIONAL")
        self.assertEqual(meta["cogs_basis"], "GMV_MRP_SALES")
        self.assertEqual(meta["logistics_basis"], "NSV")
        self.assertTrue(meta["cogs_and_logistics_separate"])
        self.assertEqual(meta["production_files_modified"], [])
        self.assertNotIn("Final CM2", meta["label"])

    def test_20c_repeated_runs_are_byte_identical(self):
        import tempfile
        outs = []
        for _ in range(2):
            with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
                p = f.name
            subprocess.run([sys.executable, str(ROOT / "scripts/cm2_cogs_logistics_fy27.py"),
                            "--out", p, "--meta", p + ".json"],
                           cwd=ROOT, capture_output=True, check=True)
            outs.append(pathlib.Path(p).read_bytes())
        self.assertEqual(outs[0], outs[1])


if __name__ == "__main__":
    unittest.main(verbosity=2)
