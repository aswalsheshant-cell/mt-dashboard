"""Tests for derive-article-master: cross-chain EAN consolidation into a
data-derived ArticleMaster (business-approved 'same article, different
chain' rule)."""
import csv
import json
import tempfile
import unittest
from pathlib import Path

from mtagent.config import Config
from mtagent.pbi_article_master import derive_article_master

HEADER = ["col0", "Unique", "Zone", "State", "City", "SO/ASE Emp Code", "SO/ASE Name",
          "Chain Name", "Store Type", "DC Code", "DC Name", "Internal Code", "Site Code",
          "Site Name", "Article", "Article_1", "EAN", "Chain Article Description",
          "Net Weight", "Description as per Fountain", "Brand", "Category", "Sub_category",
          "Range", "MRP", "Sales Qty", "MRP Sales Value", "NSV", "Per pc", "With Tax",
          "Margin", "Revised Month", "Month", "Year", "PPT Category"]


def _row(chain, ean, brand="Mamaearth", category="Face", desc="Face Wash 100ml"):
    base = {h: "" for h in HEADER}
    base.update({"Zone": "West", "State": "MH", "Chain Name": chain, "Site Code": "S1",
                 "Article": "A-" + ean[-3:], "EAN": ean, "Net Weight": "100",
                 "Description as per Fountain": desc, "Brand": brand, "Category": category,
                 "Sub_category": "Face Wash", "Range": "Rice", "MRP": "199",
                 "Sales Qty": "1", "MRP Sales Value": "199", "NSV": "1.0",
                 "Month": "May'26", "Year": "2026"})
    return [base[h] for h in HEADER]


class TestDeriveArticleMaster(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "CLAUDE.md").write_text("# fixture\n", encoding="utf-8")
        self.raw_dir = self.root / "PowerBI" / "RawDataFolders" / "Offtake_Monthly"
        self.raw_dir.mkdir(parents=True)
        self.cfg = Config(repo_root=str(self.root), index_path="agent/index/index.json",
                           pbi_build_dir="agent/pbi_build")

    def tearDown(self):
        self.tmp.cleanup()

    def _write(self, rows, name="offtake_store_article_May_26.csv"):
        with open(self.raw_dir / name, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(HEADER)
            w.writerows(rows)

    def test_blocked_without_sources(self):
        result = derive_article_master(self.cfg)
        self.assertIn("blocked_reason", result)

    def test_same_article_across_chains_consolidates_to_one_row(self):
        self._write([_row("D-Mart", "8900000000001"),
                     _row("Apollo", "8900000000001"),
                     _row("Reliance", "8900000000001")])
        result = derive_article_master(self.cfg)
        self.assertNotIn("blocked_reason", result)
        self.assertEqual(result["warning"], "")
        out = self.root / "PowerBI" / "RawDataFolders" / "Masters" / "ArticleMaster.csv"
        rows = list(csv.DictReader(open(out, newline="", encoding="utf-8")))
        self.assertEqual(len(rows), 1)  # 3 chains, 1 article
        self.assertEqual(rows[0]["EAN Code"], "8900000000001")
        self.assertEqual(rows[0]["Brand"], "Mamaearth")
        self.assertEqual(rows[0]["Pack Size"], "100")

    def test_material_conflict_reported_not_silently_resolved(self):
        self._write([_row("D-Mart", "8900000000002", brand="Mamaearth"),
                     _row("D-Mart", "8900000000002", brand="Mamaearth"),
                     _row("Apollo", "8900000000002", brand="The Derma Co.")])
        result = derive_article_master(self.cfg)
        self.assertIn("disagreement", result["warning"])
        conflicts = list(csv.DictReader(open(
            self.root / "agent" / "pbi_build" / "Article_Conflict_Report.csv",
            newline="", encoding="utf-8")))
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]["EAN Code"], "8900000000002")
        self.assertEqual(conflicts[0]["chosen (majority)"], "Mamaearth")  # 2 rows vs 1
        self.assertIn("The Derma Co.", conflicts[0]["variants"])
        self.assertIn("Apollo", conflicts[0]["variants"])  # names the disagreeing chain

    def test_derived_master_is_picked_up_by_build_dataset(self):
        from mtagent.pbi_dataset import build_dataset
        self._write([_row("D-Mart", "8900000000003")])
        (self.root / "PowerBI" / "SeedData" / "Masters").mkdir(parents=True)
        with open(self.root / "PowerBI" / "SeedData" / "Masters" / "ChainMaster.csv",
                  "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["Chain", "Account", "Chain Type", "Primary Zone", "Active"])
            w.writerow(["D-Mart", "D-Mart", "Hypermarket", "West", "Yes"])
        with open(self.root / "PowerBI" / "SeedData" / "Masters" / "ArticleMaster.csv",
                  "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["Article Code", "Article Description", "EAN Code", "Brand",
                        "Category", "Sub-category", "Range", "Pack Size"])  # empty seed

        derive_article_master(self.cfg)
        result = build_dataset(self.cfg, self.raw_dir, masters_dir=None)
        log = json.loads(result["validation_result"])
        self.assertEqual(log["unmapped_articles"], 0)   # derived master resolved it
        self.assertEqual(log["sandbox_model"]["pct_nsv_covered"], 100.0)


if __name__ == "__main__":
    unittest.main()
