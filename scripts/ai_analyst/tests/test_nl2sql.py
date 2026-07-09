"""Module 2 tests — end-to-end NL->SQL->results on real data, plus the sandbox."""

import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ai_analyst.agent import Analyst
from ai_analyst.nl2sql import validate_sql, SQLValidationError

REPO = Path(__file__).resolve().parents[3]
ARTICLE_CSV = REPO / "PowerBI" / "SeedData" / "Masters" / "ArticleMaster.csv"


class TestValidator(unittest.TestCase):
    def test_allows_select(self):
        self.assertEqual(validate_sql("SELECT 1;"), "SELECT 1")

    def test_allows_cte(self):
        self.assertTrue(validate_sql("WITH t AS (SELECT 1) SELECT * FROM t"))

    def test_rejects_ddl(self):
        for bad in ["DROP TABLE x", "DELETE FROM x", "UPDATE x SET a=1",
                    "INSERT INTO x VALUES (1)", "PRAGMA table_info(x)", "ATTACH 'y'"]:
            with self.assertRaises(SQLValidationError):
                validate_sql(bad)

    def test_rejects_statement_stacking(self):
        with self.assertRaises(SQLValidationError):
            validate_sql("SELECT 1; DROP TABLE x")

    def test_rejects_empty(self):
        with self.assertRaises(SQLValidationError):
            validate_sql("   ")


class TestEndToEndOffline(unittest.TestCase):
    """Uses the offline deterministic provider + sqlite engine: no model, no network."""

    @classmethod
    def setUpClass(cls):
        cls.a = Analyst(provider="offline", engine="sqlite")
        cls.a.load_csv(ARTICLE_CSV, table="articles")
        # ground truth straight from the engine
        _, rows = cls.a.data.run_sql('SELECT COUNT(*) FROM "articles"')
        cls.total = rows[0][0]

    @classmethod
    def tearDownClass(cls):
        cls.a.close()

    def test_count_question_matches_ground_truth(self):
        res = self.a.ask("how many articles")
        self.assertTrue(res.ok, res.error)
        self.assertEqual(res.rows[0][0], self.total)

    def test_group_by_category_runs(self):
        res = self.a.ask("articles by category")
        self.assertTrue(res.ok, res.error)
        self.assertIn("category", [c.lower() for c in res.columns])
        # counts across groups should sum to the total rows
        self.assertEqual(sum(r[1] for r in res.rows), self.total)

    def test_distinct_brand(self):
        res = self.a.ask("distinct brand")
        self.assertTrue(res.ok, res.error)
        self.assertGreaterEqual(len(res.rows), 1)

    def test_to_sql_is_read_only(self):
        sql = self.a.to_sql("how many articles by category")
        self.assertTrue(sql.lower().startswith("select"))

    def test_row_cap_applied(self):
        # default preview has no LIMIT in the question; engine cap must bound it
        res = self.a.ask("show me the articles")
        self.assertTrue(res.ok, res.error)
        self.assertLessEqual(len(res.rows), 1000)


if __name__ == "__main__":
    unittest.main()
