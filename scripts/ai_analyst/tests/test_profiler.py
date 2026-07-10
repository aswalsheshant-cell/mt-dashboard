"""Phase 3 tests — EDA profiling on real seed data."""

import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ai_analyst.data_layer import DataLayer
from ai_analyst.profiler import profile_table, suggest_cleaning, profile_report

REPO = Path(__file__).resolve().parents[3]
ARTICLE_CSV = REPO / "PowerBI" / "SeedData" / "Masters" / "ArticleMaster.csv"


class TestProfileRealCSV(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dl = DataLayer(engine="sqlite")
        cls.dl.load_csv(ARTICLE_CSV, table="articles")
        cls.prof = profile_table(cls.dl, "articles")

    @classmethod
    def tearDownClass(cls):
        cls.dl.close()

    def test_rows_and_columns(self):
        self.assertEqual(self.prof.rows_total, self.dl.table("articles").nrows)
        self.assertEqual(len(self.prof.columns), len(self.dl.table("articles").columns))

    def _col(self, name):
        return next(c for c in self.prof.columns if c.name == name)

    def test_brand_is_categorical_with_known_distinct(self):
        brand = self._col("brand")
        self.assertEqual(brand.kind, "categorical")
        # seed file contains exactly three brands
        self.assertEqual(brand.distinct, 3)
        # top_values counts must sum to non-null count
        self.assertEqual(sum(n for _, n in brand.top_values), brand.non_null)

    def test_ean_code_detected_numeric(self):
        ean = self._col("ean_code")
        self.assertEqual(ean.kind, "numeric")
        self.assertIsNotNone(ean.minimum)
        self.assertGreater(ean.maximum, 0)

    def test_article_code_categorical(self):
        # values like ME-FW-RICE-150 are not numeric
        self.assertEqual(self._col("article_code").kind, "categorical")

    def test_no_negative_nulls(self):
        for c in self.prof.columns:
            self.assertGreaterEqual(c.nulls, 0)
            self.assertGreaterEqual(c.non_null, 0)

    def test_report_renders(self):
        text = profile_report(self.prof)
        self.assertIn("articles", text)
        self.assertIn("brand", text)

    def test_suggestions_are_wellformed(self):
        for s in suggest_cleaning(self.prof):
            self.assertIn(s["priority"], ("high", "medium", "low"))
            self.assertIn("issue", s)
            self.assertIn("suggestion", s)


class TestProfileSynthetic(unittest.TestCase):
    """Deterministic checks on controlled data (nulls, duplicates, constants)."""

    def setUp(self):
        self.dl = DataLayer(engine="sqlite")
        self.dl.register_rows(
            "t",
            ["id", "amount", "flag", "note"],
            [
                ["1", "10", "X", "a"],
                ["2", "20", "X", None],   # null note
                ["2", "20", "X", None],   # exact duplicate of the row above
                ["3", "", "X", "c"],      # null amount
            ],
        )

    def tearDown(self):
        self.dl.close()

    def test_duplicate_detection(self):
        prof = profile_table(self.dl, "t")
        self.assertEqual(prof.duplicates, 1)

    def test_constant_column_flagged(self):
        prof = profile_table(self.dl, "t")
        flag = next(c for c in prof.columns if c.name == "flag")
        self.assertEqual(flag.distinct, 1)
        sug = suggest_cleaning(prof)
        self.assertTrue(any(s["column"] == "flag" and "constant" in s["issue"] for s in sug))

    def test_null_counts(self):
        prof = profile_table(self.dl, "t")
        note = next(c for c in prof.columns if c.name == "note")
        self.assertEqual(note.nulls, 2)
        amount = next(c for c in prof.columns if c.name == "amount")
        self.assertEqual(amount.nulls, 1)


if __name__ == "__main__":
    unittest.main()
