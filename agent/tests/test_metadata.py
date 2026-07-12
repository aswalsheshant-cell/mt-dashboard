import json
import tempfile
import unittest
from pathlib import Path

from mtagent.metadata import (load_inventory, parse_bim, parse_datamodel_md,
                              parse_info_csvs)

REPO = Path(__file__).resolve().parents[2]

SAMPLE_BIM = {
    "name": "MTModel",
    "model": {
        "tables": [
            {"name": "Fact Offtake Sales",
             "columns": [{"name": "Offtake NSV"}, {"name": "Chain"}],
             "measures": [{"name": "Total Offtake NSV"}]},
            {"name": "Date Table", "columns": [{"name": "Date"}]},
        ]
    },
}


class TestBim(unittest.TestCase):
    def test_parse(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "model.bim"
            p.write_text(json.dumps(SAMPLE_BIM))
            inv = parse_bim(p)
        self.assertEqual(inv.tables, {"Fact Offtake Sales", "Date Table"})
        self.assertIn("Offtake NSV", inv.columns["Fact Offtake Sales"])
        self.assertIn("Total Offtake NSV", inv.measures)
        self.assertEqual(inv.source, "metadata")


class TestInfoCsvs(unittest.TestCase):
    def test_parse_dax_studio_exports(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "INFO.TABLES.csv").write_text(
                "[Name],[DataCategory]\nFact Offtake Sales,Regular\n"
                "LocalDateTable_abc,Time\n")
            (Path(d) / "INFO.MEASURES.csv").write_text(
                "[Name],[TableID]\nTotal Offtake NSV,1\n")
            inv = parse_info_csvs(Path(d))
        self.assertEqual(inv.tables, {"Fact Offtake Sales"})   # auto date tables dropped
        self.assertEqual(inv.measures, {"Total Offtake NSV"})


class TestDocsFallback(unittest.TestCase):
    def test_datamodel_md(self):
        inv = parse_datamodel_md(REPO / "PowerBI" / "docs" / "DataModel.md")
        self.assertEqual(inv.source, "docs")
        for t in ("Date Table", "Fact Offtake Sales", "Chain Master",
                  "Ship-To Master", "_Measures"):
            self.assertIn(t, inv.tables)

    def test_load_inventory_falls_back_to_docs(self):
        with tempfile.TemporaryDirectory() as empty_meta:
            inv = load_inventory(Path(empty_meta), REPO)
        self.assertEqual(inv.source, "docs")
        self.assertTrue(inv.has_tables())

    def test_metadata_preferred_over_docs(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "model.bim").write_text(json.dumps(SAMPLE_BIM))
            inv = load_inventory(Path(d), REPO)
        self.assertEqual(inv.source, "metadata")
        self.assertNotIn("Chain Master", inv.tables)   # docs NOT merged in


if __name__ == "__main__":
    unittest.main()
