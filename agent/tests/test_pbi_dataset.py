import csv
import tempfile
import unittest
from pathlib import Path

from mtagent.config import Config
from mtagent.pbi_dataset import build_dataset, discover_offtake_files

REPO = Path(__file__).resolve().parents[2]

OFFTAKE_HEADER = [
    "col0", "Unique", "Zone", "State", "City", "SO/ASE Emp Code", "SO/ASE Name",
    "Chain Name", "Store Type", "DC Code", "DC Name", "Internal Code", "Site Code",
    "Site Name", "Article", "Article_1", "EAN", "Chain Article Description",
    "Net Weight", "Description as per Fountain", "Brand", "Category", "Sub_category",
    "Range", "MRP", "Sales Qty", "MRP Sales Value", "NSV", "Per pc", "With Tax",
    "Margin", "Revised Month", "Month", "Year", "PPT Category",
]


def _row(**overrides) -> list:
    base = {
        "col0": "", "Unique": "U1", "Zone": "west", "State": "Maharashtra", "City": "Mumbai",
        "SO/ASE Emp Code": "", "SO/ASE Name": "", "Chain Name": "D-Mart", "Store Type": "Hypermarket",
        "DC Code": "DC1", "DC Name": "Mumbai DC", "Internal Code": "", "Site Code": "SITE1",
        "Site Name": "Mumbai Store 1", "Article": "A1", "Article_1": "A1",
        "EAN": "8900000000001", "Chain Article Description": "Face Wash 100ml",
        "Net Weight": "100", "Description as per Fountain": "Face Wash 100ml",
        "Brand": "Mamaearth", "Category": "Face", "Sub_category": "Face Wash", "Range": "Rice",
        "MRP": "199", "Sales Qty": "10", "MRP Sales Value": "1990", "NSV": "15.0",
        "Per pc": "1.5", "With Tax": "1.65", "Margin": "0.3",
        "Revised Month": "", "Month": "May'26", "Year": "2026", "PPT Category": "Face",
    }
    base.update(overrides)
    return [base[h] for h in OFFTAKE_HEADER]


def _write_offtake(path: Path, rows: list) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(OFFTAKE_HEADER)
        for r in rows:
            w.writerow(r)


def _write_masters(masters_dir: Path) -> None:
    masters_dir.mkdir(parents=True, exist_ok=True)
    with open(masters_dir / "ChainMaster.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Chain", "Account", "Chain Type", "Primary Zone", "Active"])
        w.writerow(["D-Mart", "D-Mart", "Hypermarket", "West", "Yes"])
    with open(masters_dir / "ArticleMaster.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Article Code", "Article Description", "EAN Code", "Brand", "Category", "Sub-category", "Range", "Pack Size"])
        w.writerow(["ME-FW-1", "Mamaearth Rice Face Wash 100ml", "8900000000001", "Mamaearth", "Face", "Face Wash", "Rice", "100 g/ml"])


class TestDiscoverOfftakeFiles(unittest.TestCase):
    def test_sorts_oldest_to_newest_and_skips_non_matching(self):
        with tempfile.TemporaryDirectory() as td:
            raw_dir = Path(td)
            for name in ("offtake_store_article_Apr_26.csv", "offtake_store_article_May_26.csv",
                         "_TEMPLATE_Offtake_Monthly.csv", "_README.txt"):
                (raw_dir / name).write_text("x", encoding="utf-8")
            files = discover_offtake_files(raw_dir)
            self.assertEqual(len(files), 2)
            self.assertEqual(files[0][3], "Apr'26")
            self.assertEqual(files[1][3], "May'26")


class TestBuildDatasetSyntheticFixture(unittest.TestCase):
    """Fast, deterministic: hand-built fixtures, not the full 220k-row repo file."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.raw_dir = root / "raw"
        self.masters_dir = root / "masters"
        self.raw_dir.mkdir()
        _write_masters(self.masters_dir)
        self.cfg = Config(repo_root=str(root), index_path="agent/index/index.json")

    def tearDown(self):
        self.tmp.cleanup()

    def test_blocked_when_no_source_files(self):
        result = build_dataset(self.cfg, self.raw_dir, self.masters_dir)
        self.assertIn("blocked_reason", result)

    def test_blocked_when_required_column_missing(self):
        bad_header_path = self.raw_dir / "offtake_store_article_May_26.csv"
        with open(bad_header_path, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["Zone", "Chain Name"])  # missing almost everything required
            w.writerow(["West", "D-Mart"])
        result = build_dataset(self.cfg, self.raw_dir, self.masters_dir)
        self.assertIn("blocked_reason", result)
        self.assertIn("missing required column", result["blocked_reason"])

    def test_clean_rows_reconcile_exactly(self):
        rows = [_row(NSV="15.0"), _row(**{"Site Code": "SITE2", "NSV": "8.5"})]
        _write_offtake(self.raw_dir / "offtake_store_article_May_26.csv", rows)

        result = build_dataset(self.cfg, self.raw_dir, self.masters_dir)
        self.assertNotIn("blocked_reason", result)
        self.assertEqual(result["warning"], "")  # clean data -> no warning

        out_dir = self.cfg.root() / result["output_file"]
        with open(out_dir / "Fact_OfftakeSales.csv", newline="", encoding="utf-8") as fh:
            fact_rows = list(csv.DictReader(fh))
        self.assertEqual(len(fact_rows), 1)  # both rows share (FY, Month, Zone, Chain, EAN, ...)
        self.assertAlmostEqual(float(fact_rows[0]["NSV"]), 23.5, places=4)
        self.assertEqual(fact_rows[0]["Chain"], "D-Mart")  # mapped via ChainMaster.Account
        self.assertEqual(fact_rows[0]["Store_Count"], "2")

        with open(out_dir / "Source_Reconciliation_Report.csv", newline="", encoding="utf-8") as fh:
            recon = {r["metric"]: r for r in csv.DictReader(fh)}
        self.assertEqual(recon["NSV"]["status"], "PASS")

    def test_unmapped_chain_is_flagged_not_silently_dropped(self):
        rows = [_row(**{"Chain Name": "Totally Unknown Chain"})]
        _write_offtake(self.raw_dir / "offtake_store_article_May_26.csv", rows)
        result = build_dataset(self.cfg, self.raw_dir, self.masters_dir)
        self.assertIn("unmapped chain", result["warning"])
        out_dir = self.cfg.root() / result["output_file"]
        with open(out_dir / "Mapping_Exception_Report.csv", newline="", encoding="utf-8") as fh:
            exc = list(csv.DictReader(fh))
        self.assertTrue(any(e["exception_type"] == "unmapped_chain" and e["value"] == "Totally Unknown Chain" for e in exc))
        # still present in Fact (never silently dropped), under an UNMAPPED bucket
        with open(out_dir / "Fact_OfftakeSales.csv", newline="", encoding="utf-8") as fh:
            fact_rows = list(csv.DictReader(fh))
        self.assertTrue(any("UNMAPPED" in r["Chain"] for r in fact_rows))

    def test_blank_site_code_row_excluded_and_reported(self):
        rows = [_row(), _row(**{"Site Code": "", "NSV": "5.0"})]
        _write_offtake(self.raw_dir / "offtake_store_article_May_26.csv", rows)
        result = build_dataset(self.cfg, self.raw_dir, self.masters_dir)
        out_dir = self.cfg.root() / result["output_file"]
        with open(out_dir / "Data_Quality_Report.csv", newline="", encoding="utf-8") as fh:
            dq = {r["metric"]: r for r in csv.DictReader(fh)}
        self.assertEqual(dq["blank_key_rows_dropped"]["value"], "1")

    def test_never_writes_to_the_source_file(self):
        source_path = self.raw_dir / "offtake_store_article_May_26.csv"
        _write_offtake(source_path, [_row()])
        before = source_path.read_bytes()
        build_dataset(self.cfg, self.raw_dir, self.masters_dir)
        after = source_path.read_bytes()
        self.assertEqual(before, after)

    def test_incomplete_latest_month_excluded_falls_back_to_prior(self):
        _write_offtake(self.raw_dir / "offtake_store_article_Apr_26.csv", [_row() for _ in range(1500)])
        _write_offtake(self.raw_dir / "offtake_store_article_May_26.csv", [_row()])  # 1 row -> "incomplete"
        result = build_dataset(self.cfg, self.raw_dir, self.masters_dir)
        self.assertIn("Apr", result["output_file"])


class TestBuildDatasetOnRealRepoData(unittest.TestCase):
    """Integration: runs against the real committed offtake CSV + seed masters
    (small, gitignored source data is NOT required — these files ARE committed).
    Skips cleanly if the repo layout doesn't have them (e.g. a partial checkout).
    """

    def setUp(self):
        self.raw_dir = REPO / "PowerBI" / "RawDataFolders" / "Offtake_Monthly"
        self.masters_dir = REPO / "PowerBI" / "SeedData" / "Masters"
        if not any(self.raw_dir.glob("offtake_store_article_*.csv")):
            self.skipTest("no committed offtake_store_article_*.csv files in this checkout")

    def test_runs_end_to_end_and_reconciles_within_dropped_rows(self):
        cfg = Config(repo_root=str(REPO), index_path="agent/index/index_test_only.json",
                     pbi_build_dir="agent/pbi_build_test_only")
        try:
            result = build_dataset(cfg, self.raw_dir, self.masters_dir)
            self.assertNotIn("blocked_reason", result, result.get("blocked_reason"))
            out_dir = cfg.root() / result["output_file"]
            self.assertTrue((out_dir / "Fact_OfftakeSales.csv").exists())
            self.assertTrue((out_dir / "Mapping_Exception_Report.csv").exists())
            self.assertTrue((out_dir / "Dataset_Build_Log.json").exists())
        finally:
            import shutil
            shutil.rmtree(cfg.root() / cfg.pbi_build_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
