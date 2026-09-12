#!/usr/bin/env python3
"""Tests for the data-engineering skills.

The engines are what future agents will trust, so they need their own
regression cover -- especially the rounding-ceiling logic and the month parser
that already produced one false positive.
"""
import pathlib
import sys
import unittest
from decimal import Decimal

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.dataeng import core, governance, quality, reconcile, registry, validate  # noqa: E402
from scripts.dataeng.cli import readiness  # noqa: E402

D = Decimal


class TestFiscalYearRule(unittest.TestCase):
    def test_apr_to_dec_rolls_forward(self):
        self.assertEqual(core.fy_tag_from_ym("Apr", 2026), "fy27")
        self.assertEqual(core.fy_tag_from_ym("Dec", 2026), "fy27")

    def test_jan_to_mar_stays(self):
        self.assertEqual(core.fy_tag_from_ym("Jan", 2026), "fy26")
        self.assertEqual(core.fy_tag_from_ym("Mar", 2026), "fy26")

    def test_future_fy_appears_automatically(self):
        """FY28+ must fall out of the rule, never a hardcoded list."""
        self.assertEqual(core.fy_tag_from_ym("Apr", 2027), "fy28")
        self.assertEqual(core.fy_tag_from_label("Jun-30"), "fy31")

    def test_fy_months_span_apr_to_mar(self):
        m = core.fy_months("fy27")
        self.assertEqual(m[0], "Apr-26")
        self.assertEqual(m[-1], "Mar-27")
        self.assertEqual(len(m), 12)


class TestMonthParser(unittest.TestCase):
    """Regression: a serial-date month column must not read as a schema defect."""

    def test_text_label(self):
        self.assertEqual(core.parse_month_cell("Apr'26"), "Apr-26")
        self.assertEqual(core.parse_month_cell("Jun-26"), "Jun-26")

    def test_excel_serial(self):
        self.assertEqual(core.parse_month_cell("46113.0"), "Apr-26")
        self.assertEqual(core.parse_month_cell(46174), "Jun-26")

    def test_genuinely_unparseable(self):
        self.assertIsNone(core.parse_month_cell("Reliance_Brand_Counter"))
        self.assertIsNone(core.parse_month_cell(""))
        self.assertIsNone(core.parse_month_cell(None))

    def test_serial_column_is_not_flagged(self):
        """The exact false positive this parser was written to kill."""
        findings = validate.run()
        mixed = [f for f in findings if f.category == "mixed_schema"]
        self.assertEqual(mixed, [], f"false mixed-schema report: {[f.summary for f in mixed]}")


class TestRoundingCeiling(unittest.TestCase):
    """A difference is only rounding if it fits under the theoretical ceiling."""

    def test_ceiling_scales_with_rows(self):
        self.assertEqual(reconcile.max_rounding_l(46), D("0.230"))
        self.assertEqual(reconcile.max_rounding_l(12), D("0.060"))

    def test_small_diff_passes(self):
        rows = [{"v": "10.00"}, {"v": "10.00"}]
        f = reconcile.check_rollup("t", rows, "v", D("20.00"), "owner")
        self.assertEqual(f.severity, "PASS")

    def test_material_diff_is_not_called_rounding(self):
        rows = [{"v": "10.00"}, {"v": "10.00"}]
        f = reconcile.check_rollup("t", rows, "v", D("-2.84"), "owner")
        self.assertEqual(f.severity, "WARN")
        self.assertEqual(f.category, "coverage_gap")
        self.assertIn("NOT rounding", f.summary)

    def test_known_chain_gap_is_flagged_not_excused(self):
        """The historical 22.84L 'allocation rounding' must surface as a gap."""
        f = [x for x in reconcile.run() if x.id == "RECON-CM2-BY_CHAIN-NSV"][0]
        self.assertEqual(f.severity, "WARN")
        self.assertEqual(f.category, "coverage_gap")
        self.assertIn("NOT rounding", f.summary)


class TestGovernanceGate(unittest.TestCase):
    def test_draft_formula_blocks_production(self):
        allowed, blockers = governance.production_gate()
        self.assertFalse(allowed)
        self.assertTrue(any("FORMULA-DRAFT" in b for b in blockers))

    def test_approval_requires_evidence(self):
        rows, findings = governance.run()
        self.assertTrue(rows)
        weak = [f for f in findings if f.id.startswith("GOV-WEAKAPPROVAL")]
        self.assertEqual(weak, [], f"approval missing evidence: {[f.summary for f in weak]}")

    def test_every_decision_has_a_valid_status(self):
        _, findings = governance.run()
        self.assertEqual([f for f in findings if f.id.startswith("GOV-BADSTATUS")], [])


class TestRegistry(unittest.TestCase):
    def test_all_metrics_resolve(self):
        rows, findings = registry.build()
        unresolved = [r["Metric"] for r in rows if r["Resolved"] != "YES"]
        self.assertEqual(unresolved, [], f"registry drift: {unresolved}")

    def test_lineage_has_four_stages_per_metric(self):
        lin = registry.lineage_rows()
        per = {}
        for r in lin:
            per.setdefault(r["Metric"], set()).add(r["Stage"])
        for metric, stages in per.items():
            self.assertEqual(len(stages), 4, f"{metric} lineage incomplete")

    def test_known_mrp_defect_is_documented(self):
        rows, _ = registry.build()
        mrp = [r for r in rows if r["Dashboard_Path"].endswith("FY27.mrp")][0]
        self.assertIn("D13", mrp["Known_Limitations"])
        self.assertEqual(mrp["Calculation_Basis"], "GMV_MRP")


class TestDataQuality(unittest.TestCase):
    def test_no_excluded_brand_leak(self):
        leaks = [f for f in quality.run() if f.category == "excluded_brand"]
        self.assertEqual(leaks, [], f"excluded brand in an aggregation: {[f.summary for f in leaks]}")

    def test_no_nan_or_infinity(self):
        self.assertEqual([f for f in quality.run() if f.id == "DQ-NANINF"], [])


class TestFindingContract(unittest.TestCase):
    def test_severity_is_validated(self):
        with self.assertRaises(ValueError):
            core.Finding(id="x", skill="s", category="c", severity="MAYBE", summary="")

    def test_every_finding_has_id_and_summary(self):
        all_f = (validate.run() + quality.run() + reconcile.run()
                 + governance.run()[1] + registry.build()[1] + validate.run())
        for f in all_f:
            self.assertTrue(f.id.strip(), "finding without an id")
            self.assertTrue(f.summary.strip(), f"{f.id} has no summary")
            self.assertIn(f.severity, core.SEVERITIES)

    def test_actionable_findings_name_an_owner(self):
        all_f = validate.run() + quality.run() + reconcile.run()
        orphan = [f.id for f in all_f
                  if f.severity in ("FAIL", "BLOCKED", "WARN") and not f.owner.strip()]
        self.assertEqual(orphan, [], f"actionable findings with no owner: {orphan}")


class TestReadinessScore(unittest.TestCase):
    def test_blocked_dominates(self):
        f = [core.Finding(id="a", skill="s", category="c", severity="BLOCKED", summary="x")]
        score, verdict = readiness(f)
        self.assertIn("NOT READY", verdict)
        self.assertLess(score, 100)

    def test_clean_run_is_ready(self):
        f = [core.Finding(id="a", skill="s", category="c", severity="PASS", summary="x")]
        self.assertEqual(readiness(f), (100, "READY"))

    def test_warn_only_is_conditional(self):
        f = [core.Finding(id="a", skill="s", category="c", severity="WARN", summary="x")]
        _, verdict = readiness(f)
        self.assertIn("ACCEPTED EXCEPTIONS", verdict)


class TestRepoSafety(unittest.TestCase):
    def test_skills_do_not_write_to_production(self):
        """No engine may target a production path."""
        forbidden = ("dashboard/data.js", "dashboard/index.html")
        for mod in (core, validate, quality, reconcile, governance, registry):
            src = pathlib.Path(mod.__file__).read_text(encoding="utf-8")
            for line in src.splitlines():
                if any(p in line for p in forbidden):
                    self.assertNotRegex(
                        line, r"write_text|to_csv|open\([^)]*['\"][wa]",
                        f"{mod.__name__} appears to write a production file: {line.strip()}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
