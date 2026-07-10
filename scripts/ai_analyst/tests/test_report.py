"""Phase 5 tests — offline report export (md/html/csv fully; xlsx/pptx pluggable)."""

import importlib
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ai_analyst.agent import Analyst
from ai_analyst.report import Report, ReportDependencyError

REPO = Path(__file__).resolve().parents[3]
ARTICLE_CSV = REPO / "PowerBI" / "SeedData" / "Masters" / "ArticleMaster.csv"


class TestRenderers(unittest.TestCase):
    def _report(self):
        r = Report("Test Report", subtitle="unit test")
        r.add_text("Some narrative.", title="Intro")
        r.add_kpis([("Rows", "13"), ("Brands", "3")])
        r.add_table(["category", "n"], [["Face Care", 7], ["Sun Care", 4]], title="By category")
        return r

    def test_markdown(self):
        md = self._report().to_markdown()
        self.assertIn("# Test Report", md)
        self.assertIn("| category | n |", md)
        self.assertIn("Face Care", md)

    def test_html_escapes(self):
        r = Report("X")
        r.add_table(["c"], [["<script>alert(1)</script>"]])
        h = r.to_html()
        self.assertNotIn("<script>alert(1)", h)
        self.assertIn("&lt;script&gt;", h)

    def test_csv(self):
        c = self._report().to_csv()
        self.assertIn("category,n", c)
        self.assertIn("Face Care,7", c)

    def test_csv_requires_table(self):
        with self.assertRaises(ValueError):
            Report("no tables").add_text("hi").to_csv()


class TestSaveRoundTrip(unittest.TestCase):
    def setUp(self):
        self.a = Analyst(provider="offline", engine="sqlite")
        self.a.load_csv(ARTICLE_CSV, table="articlemaster")

    def tearDown(self):
        self.a.close()

    def test_build_report_from_real_data(self):
        rep = self.a.build_report("MT Report", table="articlemaster",
                                  questions=["how many articles by category"])
        md = rep.to_markdown()
        self.assertIn("EDA profile", md)
        self.assertIn("articlemaster", md)
        # the asked question's result table is present
        self.assertIn("Face Care", md)

    def test_save_md_html_csv(self):
        rep = self.a.build_report("MT Report", table="articlemaster")
        with tempfile.TemporaryDirectory() as d:
            for ext in ("md", "html", "csv"):
                out = Path(d) / f"r.{ext}"
                rep.save(out)
                self.assertTrue(out.exists())
                self.assertGreater(out.stat().st_size, 0)
            html = (Path(d) / "r.html").read_text()
            self.assertIn("<table", html)

    def test_unsupported_ext(self):
        rep = self.a.build_report("x", table="articlemaster")
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                rep.save(Path(d) / "r.docx")


class TestOptionalBackends(unittest.TestCase):
    def _has(self, mod):
        try:
            importlib.import_module(mod)
            return True
        except ImportError:
            return False

    def test_xlsx(self):
        r = Report("x").add_table(["a"], [[1], [2]], title="T")
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "r.xlsx"
            if self._has("openpyxl"):
                r.save(out)
                self.assertTrue(out.exists())
            else:
                with self.assertRaises(ReportDependencyError):
                    r.save(out)

    def test_pptx(self):
        r = Report("x").add_table(["a"], [[1]], title="T")
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "r.pptx"
            if self._has("pptx"):
                r.save(out)
                self.assertTrue(out.exists())
            else:
                with self.assertRaises(ReportDependencyError):
                    r.save(out)


if __name__ == "__main__":
    unittest.main()
