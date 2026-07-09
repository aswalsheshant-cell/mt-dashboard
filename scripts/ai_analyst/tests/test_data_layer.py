"""Module 1 tests — loading real seed CSVs and querying them."""

import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ai_analyst.data_layer import DataLayer, sanitize_identifier

REPO = Path(__file__).resolve().parents[3]
MASTERS = REPO / "PowerBI" / "SeedData" / "Masters"
ARTICLE_CSV = MASTERS / "ArticleMaster.csv"


class TestSanitize(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(sanitize_identifier("Article Code"), "article_code")
        self.assertEqual(sanitize_identifier("Sub-category"), "sub_category")
        self.assertEqual(sanitize_identifier("Inv. Net value(LOC)"), "inv_net_value_loc")

    def test_empty_and_numeric(self):
        self.assertEqual(sanitize_identifier("", fallback="col_0"), "col_0")
        self.assertTrue(sanitize_identifier("0xf").startswith("col"))


class TestDataLayerRealCSV(unittest.TestCase):
    def setUp(self):
        self.dl = DataLayer(engine="sqlite")  # stdlib engine, always available
        self.tbl = self.dl.load_csv(ARTICLE_CSV, table="articles")

    def tearDown(self):
        self.dl.close()

    def test_loads_real_file(self):
        self.assertTrue(ARTICLE_CSV.exists(), "real seed CSV must exist")
        self.assertGreater(self.tbl.nrows, 0)
        self.assertIn("article_code", self.tbl.columns)
        self.assertIn("category", self.tbl.columns)

    def test_schema_shape(self):
        sch = self.dl.schema()
        self.assertIn("articles", sch)
        self.assertEqual(len(sch["articles"]), len(self.tbl.columns))

    def test_count_matches(self):
        cols, rows = self.dl.run_sql('SELECT COUNT(*) FROM "articles"')
        self.assertEqual(rows[0][0], self.tbl.nrows)

    def test_group_by_real_column(self):
        cols, rows = self.dl.run_sql(
            'SELECT "category", COUNT(*) AS n FROM "articles" GROUP BY "category" ORDER BY n DESC'
        )
        self.assertGreater(len(rows), 0)
        # every category bucket should have at least one row
        self.assertTrue(all(r[1] >= 1 for r in rows))

    def test_duplicate_headers_are_deduped(self):
        # primary_article files have a duplicated "Cust-SAP Code" header
        pa = REPO / "PowerBI" / "RawDataFolders" / "Primary_Article_Monthly" / "primary_article_Apr_25.csv"
        if pa.exists():
            t = self.dl.load_csv(pa, table="pa", max_rows=50)
            self.assertEqual(len(t.columns), len(set(t.columns)), "columns must be unique after dedupe")


if __name__ == "__main__":
    unittest.main()
