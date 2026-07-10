"""Phase 6 tests — template fill on REAL offtake data + the no-invented-numbers rule."""

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ai_analyst.template_fill import TemplateFiller
from ai_analyst.templates import get_template, list_templates
from ai_analyst.provenance import SOURCE_REQUIRED
from ai_analyst.data_layer import DataLayer

REPO = Path(__file__).resolve().parents[3]
OFF = REPO / "PowerBI" / "RawDataFolders" / "Offtake_Monthly"
MAY = OFF / "offtake_store_article_May_26.csv"
APR = OFF / "offtake_store_article_Apr_26.csv"


class TestRegistry(unittest.TestCase):
    def test_aliases(self):
        self.assertEqual(get_template("MT Monthly Offtake Report").key, "mt_monthly_offtake")
        self.assertEqual(get_template("nielsen").key, "nielsen_market_share")

    def test_list(self):
        keys = {t["key"] for t in list_templates()}
        self.assertIn("mt_monthly_offtake", keys)
        self.assertIn("qbr_leadership_review", keys)

    def test_unknown_raises(self):
        with self.assertRaises(KeyError):
            get_template("no_such_template")


@unittest.skipUnless(MAY.exists() and APR.exists(), "real offtake CSVs not present")
class TestMonthlyOfftakeReal(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fr = TemplateFiller(engine="sqlite").fill(
            "mt_monthly_offtake",
            {"offtake": {"May'26": str(MAY), "Apr'26": str(APR)}},
            period="May'26", compare="Apr'26",
        )
        # independent ground truth
        dl = DataLayer(engine="sqlite")
        dl.load_csv(MAY, table="m")
        dl.load_csv(APR, table="a")
        cls.may_total = dl.run_sql('SELECT SUM(CAST(NULLIF("mrp_sales_value",\'\') AS REAL)) FROM "m"')[1][0][0]
        cls.apr_total = dl.run_sql('SELECT SUM(CAST(NULLIF("mrp_sales_value",\'\') AS REAL)) FROM "a"')[1][0][0]
        dl.close()

    def test_available(self):
        self.assertTrue(self.fr.available)

    def test_headline_matches_source_exactly(self):
        md = self.fr.report.to_markdown()
        expected_cr = f"{self.may_total / 1e7:,.2f}"
        self.assertIn(expected_cr, md)  # value comes straight from the source sum

    def test_mom_is_correct_and_qc_passes(self):
        expected_mom = (self.may_total - self.apr_total) / self.apr_total * 100.0
        self.assertGreater(expected_mom, 0)  # real data grew
        mom_check = next(c for c in self.fr.qc_checks if c.name == "MoM calculation")
        self.assertEqual(mom_check.status, "PASS")
        total_check = next(c for c in self.fr.qc_checks if c.name == "Total validation")
        self.assertEqual(total_check.status, "PASS")

    def test_contains_all_required_sections(self):
        md = self.fr.report.to_markdown()
        for needle in ["Confidential - MT Internal", "Leadership insights", "Action tracker",
                       "Audit — Considered / Not Considered", "Source provenance", "QC report"]:
            self.assertIn(needle, md)

    def test_mt_vs_gt_is_na_for_offtake(self):
        ch = next(c for c in self.fr.qc_checks if c.name == "MT vs GT filter")
        self.assertEqual(ch.status, "NA")

    def test_audit_lists_both_source_files(self):
        md = self.fr.report.to_markdown()
        self.assertIn("offtake_store_article_May_26.csv", md)
        self.assertIn("offtake_store_article_Apr_26.csv", md)


class TestMissingSourceContract(unittest.TestCase):
    """Rule 10: no source -> structure built, values marked required, nothing invented."""

    def test_nielsen_without_source(self):
        fr = TemplateFiller(engine="sqlite").fill(
            "nielsen_market_share", sources={}, period="May'26")
        self.assertFalse(fr.available)
        md = fr.report.to_markdown()
        self.assertIn(SOURCE_REQUIRED, md)
        self.assertIn("Not Considered", md)
        # QC still present, and total validation is NA (not a fake pass)
        tv = next(c for c in fr.qc_checks if c.name == "Total validation")
        self.assertEqual(tv.status, "NA")


class TestHideOthersSynthetic(unittest.TestCase):
    """Rule 5: 'Others' hidden from the visible table but kept in totals."""

    def _make_csv(self, path):
        path.write_text(
            "category,mrp_sales_value,nsv,chain_name,article,zone\n"
            "Face Care,100,80,DMart,A1,West\n"
            "Sun Care,60,50,DMart,A2,West\n"
            "Others,40,30,DMart,A3,West\n",
            encoding="utf-8")

    def test_others_hidden_but_in_total(self):
        with tempfile.TemporaryDirectory() as d:
            csv = Path(d) / "off.csv"
            self._make_csv(csv)
            fr = TemplateFiller(engine="sqlite").fill(
                "mt_monthly_offtake", {"offtake": {"May'26": str(csv)}}, period="May'26")
            md = fr.report.to_markdown()
            # 'Others' must not appear as a visible breakdown row...
            breakdown = md.split("by Category")[1].split("Leadership insights")[0]
            self.assertNotIn("| Others |", breakdown)
            # ...but the grand total (200 -> 0.00 Cr rounding) note references incl-Others total
            self.assertIn("incl Others", md)
            # contribution QC still sums to 100 (parts incl Others)
            contrib = next(c for c in fr.qc_checks if c.name == "Contribution %")
            self.assertEqual(contrib.status, "PASS")


if __name__ == "__main__":
    unittest.main()
