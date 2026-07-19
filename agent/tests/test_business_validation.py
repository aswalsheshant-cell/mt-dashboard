"""Tests for the business-validation gate (§C in AI_LEVERAGE_AND_JUDGMENT.md).

Spec Tests 2/3/4 verbatim: activity cannot equal success, a technically
clean run with a business-rule failure must still fail, and the exact
real-world Reliance store-explosion bug generalized into a reusable check.
"""
import unittest

from mtagent.validators import business_validation as bv


class TestActivityCannotEqualSuccess(unittest.TestCase):
    """Spec Test 2: 20 files processed but NSV reconciliation failed."""

    def test_nsv_mismatch_fails_even_though_activity_completed(self):
        check = bv.reconcile_metric("nsv", source_total=125_00_000, output_total=124_50_000, tolerance=0)
        self.assertFalse(check.passed)
        passed_ok, checks_passed, checks_failed = bv.evaluate([check])
        self.assertFalse(passed_ok)
        self.assertIn("nsv_reconciliation", checks_failed)

    def test_exact_match_within_tolerance_passes(self):
        check = bv.reconcile_metric("nsv", source_total=125_00_000, output_total=125_00_000, tolerance=0)
        self.assertTrue(check.passed)


class TestDistinctValueExplosion(unittest.TestCase):
    """Spec Test 3: exit code 0, but chain count 45 -> 130 (the real
    Reliance store-explosion bug, generalized)."""

    def test_chain_count_45_to_130_fails(self):
        check = bv.distinct_value_check("canonical_chain", before_count=45, after_count=130, max_growth_ratio=1.5)
        self.assertFalse(check.passed)
        self.assertIn("explosion", check.detail)

    def test_chain_count_45_to_46_passes(self):
        check = bv.distinct_value_check("canonical_chain", before_count=45, after_count=46, max_growth_ratio=1.5)
        self.assertTrue(check.passed)

    def test_no_prior_baseline_does_not_falsely_fail(self):
        check = bv.distinct_value_check("canonical_chain", before_count=0, after_count=45)
        self.assertTrue(check.passed)


class TestPeriodCompleteness(unittest.TestCase):
    """Spec Test 4: dashboard rendered successfully, but a partial June is
    shown as a closed month."""

    def test_partial_period_shown_as_closed_fails(self):
        check = bv.period_completeness_check("june26", is_partial_period=True, treated_as_closed=True)
        self.assertFalse(check.passed)
        self.assertIn("period-completeness business rule failed", check.detail)

    def test_partial_period_correctly_flagged_passes(self):
        check = bv.period_completeness_check("june26", is_partial_period=True, treated_as_closed=False)
        self.assertTrue(check.passed)

    def test_complete_period_passes(self):
        check = bv.period_completeness_check("may26", is_partial_period=False, treated_as_closed=True)
        self.assertTrue(check.passed)


class TestRowCountAndMapping(unittest.TestCase):
    def test_row_count_mismatch_fails(self):
        check = bv.reconcile_counts("offtake", source_n=23193, output_n=23100)
        self.assertFalse(check.passed)

    def test_mapping_not_in_known_canonicals_fails_but_is_named(self):
        check = bv.mapping_validation_check("chain", "Totally New Chain", {"D-Mart", "Apollo"})
        self.assertFalse(check.passed)
        self.assertIn("NOT an approved canonical value", check.detail)

    def test_mapping_in_known_canonicals_passes(self):
        check = bv.mapping_validation_check("chain", "Apollo", {"D-Mart", "Apollo"})
        self.assertTrue(check.passed)


if __name__ == "__main__":
    unittest.main()
