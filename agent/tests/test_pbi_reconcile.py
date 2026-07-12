import csv
import tempfile
import unittest
from pathlib import Path

from mtagent.config import Config
from mtagent.pbi_reconcile import reconcile_source_to_model

SOURCE_HEADER = ["Zone", "State", "Chain Name", "DC Code", "Site Code", "EAN",
                  "MRP Sales Value", "NSV", "Sales Qty"]


def _write_source(path: Path, rows: list) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(SOURCE_HEADER)
        for r in rows:
            w.writerow(r)


def _write_fact(path: Path, rows: list) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["FY", "Month", "Zone", "Chain", "EAN", "Brand", "Category",
                    "Sub_Category", "NSV", "MRP_Sales_Value", "Sales_Qty", "Store_Count"])
        for r in rows:
            w.writerow(r)


class TestReconcileSourceToModel(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.cfg = Config(repo_root=str(self.root), index_path="agent/index/index.json")
        self.build_dir = self.root / "build"
        self.build_dir.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def test_blocked_when_source_missing(self):
        _write_fact(self.build_dir / "Fact_OfftakeSales.csv", [])
        result = reconcile_source_to_model(self.cfg, self.root / "no_such.csv", self.build_dir)
        self.assertIn("blocked_reason", result)

    def test_blocked_when_fact_table_missing(self):
        source_path = self.root / "source.csv"
        _write_source(source_path, [["WEST", "MH", "D-Mart", "DC1", "S1", "E1", "199", "15", "10"]])
        result = reconcile_source_to_model(self.cfg, source_path, self.build_dir)
        self.assertIn("blocked_reason", result)

    def test_matching_totals_pass(self):
        source_path = self.root / "source.csv"
        _write_source(source_path, [
            ["WEST", "MH", "D-Mart", "DC1", "S1", "E1", "199", "15.0", "10"],
            ["WEST", "MH", "D-Mart", "DC1", "S2", "E1", "199", "8.5", "5"],
        ])
        _write_fact(self.build_dir / "Fact_OfftakeSales.csv", [
            ["FY27", "May'26", "WEST", "D-Mart", "E1", "Mamaearth", "Face", "Face Wash", "23.5", "398.0", "15", "2"],
        ])
        result = reconcile_source_to_model(self.cfg, source_path, self.build_dir)
        self.assertNotIn("blocked_reason", result)
        self.assertEqual(result["warning"], "")

        out_path = self.cfg.root() / result["output_file"]
        with open(out_path, newline="", encoding="utf-8") as fh:
            rows = {r["metric"]: r for r in csv.DictReader(fh)}
        self.assertEqual(rows["nsv_total"]["status"], "PASS")
        self.assertEqual(rows["row_count"]["status"], "INFO")  # never FAILs -- aggregation grain differs by design

    def test_mismatch_is_reported_not_hidden(self):
        source_path = self.root / "source.csv"
        _write_source(source_path, [["WEST", "MH", "D-Mart", "DC1", "S1", "E1", "199", "100.0", "10"]])
        _write_fact(self.build_dir / "Fact_OfftakeSales.csv", [
            ["FY27", "May'26", "WEST", "D-Mart", "E1", "Mamaearth", "Face", "Face Wash", "40.0", "199", "10", "1"],
        ])
        result = reconcile_source_to_model(self.cfg, source_path, self.build_dir)
        self.assertIn("exceeded", result["warning"])
        out_path = self.cfg.root() / result["output_file"]
        with open(out_path, newline="", encoding="utf-8") as fh:
            rows = {r["metric"]: r for r in csv.DictReader(fh)}
        self.assertEqual(rows["nsv_total"]["status"], "FAIL")
        self.assertNotEqual(rows["nsv_total"]["likely_cause"], "")

    def test_tolerance_is_configurable(self):
        source_path = self.root / "source.csv"
        _write_source(source_path, [["WEST", "MH", "D-Mart", "DC1", "S1", "E1", "199", "100.0", "10"]])
        _write_fact(self.build_dir / "Fact_OfftakeSales.csv", [
            ["FY27", "May'26", "WEST", "D-Mart", "E1", "Mamaearth", "Face", "Face Wash", "99.6", "199", "10", "1"],
        ])
        tight_cfg = Config(repo_root=str(self.root), index_path="agent/index/index.json",
                            pbi_reconciliation_tolerance_pct=0.1)
        loose_cfg = Config(repo_root=str(self.root), index_path="agent/index/index.json",
                            pbi_reconciliation_tolerance_pct=1.0)
        tight_result = reconcile_source_to_model(tight_cfg, source_path, self.build_dir)
        loose_result = reconcile_source_to_model(loose_cfg, source_path, self.build_dir)
        self.assertIn("exceeded", tight_result["warning"])
        self.assertEqual(loose_result["warning"], "")

    def test_chain_and_zone_level_breakdown_included(self):
        source_path = self.root / "source.csv"
        _write_source(source_path, [
            ["WEST", "MH", "D-Mart", "DC1", "S1", "E1", "199", "15.0", "10"],
            ["EAST", "WB", "Spencer", "DC2", "S3", "E2", "99", "5.0", "2"],
        ])
        _write_fact(self.build_dir / "Fact_OfftakeSales.csv", [
            ["FY27", "May'26", "WEST", "D-Mart", "E1", "Mamaearth", "Face", "Face Wash", "15.0", "199", "10", "1"],
            ["FY27", "May'26", "EAST", "Spencer", "E2", "Mamaearth", "Face", "Face Wash", "5.0", "99", "2", "1"],
        ])
        result = reconcile_source_to_model(self.cfg, source_path, self.build_dir)
        out_path = self.cfg.root() / result["output_file"]
        with open(out_path, newline="", encoding="utf-8") as fh:
            metrics = {r["metric"] for r in csv.DictReader(fh)}
        self.assertIn("chain_total:D-Mart", metrics)
        self.assertIn("zone_total:EAST", metrics)


if __name__ == "__main__":
    unittest.main()
