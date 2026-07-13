"""Tests for derive-npi-list: NPI = first primary appearance in the latest
FY present in the data (business-approved rule, THE ONE FY RULE compliant)."""
import csv
import json
import tempfile
import unittest
from pathlib import Path

from mtagent.config import Config
from mtagent.pbi_npi import derive_npi_list

HEADER = ["FY", "Month", "Purchase Order Number", "Inv No.", "Inv. Date", "Category",
          "Article Code", "SO No", "Ship To Name", "EAN No.", "net_content", "brand",
          "PPT Category", "category", "sub_category", "range", "Description", "MRP Rate",
          "Inv Qty", "Inv. Net value(LOC)"]


def _row(ean, month_label, desc="Face Wash 100ml", brand="Mamaearth"):
    base = {h: "" for h in HEADER}
    base.update({"Month": month_label, "EAN No.": ean, "Article Code": "10100001",
                 "brand": brand, "category": "Face", "sub_category": "Face Wash",
                 "Description": desc, "Inv Qty": "10", "Inv. Net value(LOC)": "1000"})
    return [base[h] for h in HEADER]


class TestDeriveNpiList(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "CLAUDE.md").write_text("# fixture\n", encoding="utf-8")
        self.raw_dir = self.root / "PowerBI" / "RawDataFolders" / "Primary_Article_Monthly"
        self.raw_dir.mkdir(parents=True)
        (self.root / "PowerBI" / "SeedData" / "Masters").mkdir(parents=True)
        self.cfg = Config(repo_root=str(self.root), index_path="agent/index/index.json",
                           pbi_build_dir="agent/pbi_build")

    def tearDown(self):
        self.tmp.cleanup()

    def _write(self, name, rows):
        with open(self.raw_dir / name, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(HEADER)
            w.writerows(rows)

    def test_blocked_without_sources(self):
        result = derive_npi_list(self.cfg)
        self.assertIn("blocked_reason", result)

    def test_first_appearance_in_latest_fy_is_npi_established_articles_are_not(self):
        # OLD article sells from Apr'25 (FY26); NEW article first appears May'26 (FY27)
        self._write("primary_article_Apr_25.csv", [_row("8900000000001", "Apr'25")])
        self._write("primary_article_May_26.csv", [_row("8900000000001", "May'26"),
                                                    _row("8900000000002", "May'26", desc="NEW Serum")])
        result = derive_npi_list(self.cfg)
        self.assertNotIn("blocked_reason", result)
        summary = json.loads(result["validation_result"])
        self.assertEqual(summary["npi_window_fy"], "FY27")   # derived from data, not hardcoded
        self.assertEqual(summary["npi_count"], 1)
        self.assertEqual(summary["total_articles_in_history"], 2)

        out = self.root / "PowerBI" / "SeedData" / "Masters" / "NPI_List.csv"
        rows = list(csv.DictReader(open(out, newline="", encoding="utf-8")))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["EAN"], "8900000000002")
        self.assertEqual(rows[0]["First Primary Month"], "May'26")
        self.assertEqual(rows[0]["NPI FY"], "FY27")
        # 'Article'/'Article Code' deliberately NOT used as a column name, so
        # the diff engine's priority matching lands on the shared EAN key
        self.assertNotIn("Article", rows[0])
        self.assertNotIn("Article Code", rows[0])
        self.assertIn("Primary Article Code", rows[0])

    def test_fy_window_moves_with_the_data(self):
        # history ending in FY26 -> the NPI window must be FY26, never a pinned year
        self._write("primary_article_Apr_25.csv", [_row("8900000000001", "Apr'25")])
        self._write("primary_article_Mar_26.csv", [_row("8900000000003", "Mar'26")])
        result = derive_npi_list(self.cfg)
        summary = json.loads(result["validation_result"])
        self.assertEqual(summary["npi_window_fy"], "FY26")
        rows = list(csv.DictReader(open(
            self.root / "PowerBI" / "SeedData" / "Masters" / "NPI_List.csv",
            newline="", encoding="utf-8")))
        # BOTH articles first appear within FY26 (Apr'25 and Mar'26) -> both NPIs
        # by the rule; the censoring caveat is stamped in the report
        self.assertEqual({r["EAN"] for r in rows}, {"8900000000001", "8900000000003"})
        self.assertIn("censoring", result["validation_result"])


if __name__ == "__main__":
    unittest.main()
