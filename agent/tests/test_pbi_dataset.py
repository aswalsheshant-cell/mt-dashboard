import csv
import json
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
        w.writerow(["Reliance Retail", "Reliance", "Hypermarket", "Pan India", "Yes"])
    with open(masters_dir / "ArticleMaster.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Article Code", "Article Description", "EAN Code", "Brand", "Category", "Sub-category", "Range", "Pack Size"])
        w.writerow(["ME-FW-1", "Mamaearth Rice Face Wash 100ml", "8900000000001", "Mamaearth", "Face", "Face Wash", "Rice", "100 g/ml"])


def _write_aliases(masters_dir: Path, rows: list[tuple[str, str]]) -> None:
    with open(masters_dir / "ChainAliases.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Alias", "Canonical Chain", "Note"])
        for alias, canonical in rows:
            w.writerow([alias, canonical, "test alias"])


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
        self.assertEqual(len(fact_rows), 1)  # both rows share (FY, Month, Zone, State, Chain, EAN, ...)
        self.assertAlmostEqual(float(fact_rows[0]["NSV"]), 23.5, places=4)
        self.assertEqual(fact_rows[0]["Chain"], "D-Mart")  # mapped via ChainMaster.Account
        self.assertEqual(fact_rows[0]["State"], "Maharashtra")  # regional anchor for the account matrix
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

    def test_blank_site_code_row_retained_and_reported(self):
        rows = [_row(), _row(**{"Site Code": "", "NSV": "5.0"})]
        _write_offtake(self.raw_dir / "offtake_store_article_May_26.csv", rows)
        result = build_dataset(self.cfg, self.raw_dir, self.masters_dir)
        out_dir = self.cfg.root() / result["output_file"]
        with open(out_dir / "Data_Quality_Report.csv", newline="", encoding="utf-8") as fh:
            dq = {r["metric"]: r for r in csv.DictReader(fh)}
        self.assertEqual(dq["blank_key_rows_retained"]["value"], "1")
        # the blank-site row's NSV stays in the Fact -- never dropped
        with open(out_dir / "Fact_OfftakeSales.csv", newline="", encoding="utf-8") as fh:
            fact_rows = list(csv.DictReader(fh))
        self.assertAlmostEqual(sum(float(r["NSV"]) for r in fact_rows), 20.0, places=4)
        # blank site must not inflate the store count
        self.assertEqual(sum(int(r["Store_Count"]) for r in fact_rows), 1)
        with open(out_dir / "Mapping_Exception_Report.csv", newline="", encoding="utf-8") as fh:
            exc = list(csv.DictReader(fh))
        self.assertTrue(any(e["exception_type"] == "blank_site_code" and e["row_count"] == "1" for e in exc))

    def test_blank_site_code_falls_back_to_internal_code(self):
        rows = [_row(), _row(**{"Site Code": "", "Internal Code": "IC-77", "NSV": "5.0"})]
        _write_offtake(self.raw_dir / "offtake_store_article_May_26.csv", rows)
        result = build_dataset(self.cfg, self.raw_dir, self.masters_dir)
        out_dir = self.cfg.root() / result["output_file"]
        with open(out_dir / "Data_Quality_Report.csv", newline="", encoding="utf-8") as fh:
            dq = {r["metric"]: r for r in csv.DictReader(fh)}
        self.assertEqual(dq["site_code_internal_fallbacks"]["value"], "1")
        self.assertEqual(dq["blank_key_rows_retained"]["value"], "0")
        with open(out_dir / "Fact_OfftakeSales.csv", newline="", encoding="utf-8") as fh:
            fact_rows = list(csv.DictReader(fh))
        # fallback site counts as a real store
        self.assertEqual(sum(int(r["Store_Count"]) for r in fact_rows), 2)

    def test_bare_corporate_chain_mapped_via_alias(self):
        _write_aliases(self.masters_dir, [("Reliance", "Reliance Retail")])
        rows = [_row(**{"Chain Name": "Reliance", "NSV": "7.0"})]
        _write_offtake(self.raw_dir / "offtake_store_article_May_26.csv", rows)
        result = build_dataset(self.cfg, self.raw_dir, self.masters_dir)
        self.assertNotIn("unmapped chain", result["warning"])
        out_dir = self.cfg.root() / result["output_file"]
        with open(out_dir / "Fact_OfftakeSales.csv", newline="", encoding="utf-8") as fh:
            fact_rows = list(csv.DictReader(fh))
        self.assertEqual(fact_rows[0]["Chain"], "Reliance")  # canonical row's Account
        with open(out_dir / "Mapping_Exception_Report.csv", newline="", encoding="utf-8") as fh:
            exc = list(csv.DictReader(fh))
        alias_rows = [e for e in exc if e["exception_type"] == "alias_mapped_chain"]
        self.assertEqual(len(alias_rows), 1)
        self.assertEqual(alias_rows[0]["value"], "Reliance")
        self.assertIn("Reliance Retail", alias_rows[0]["resolution"])

    def test_alias_pointing_at_missing_chain_is_surfaced_not_applied(self):
        _write_aliases(self.masters_dir, [("Reliance", "No Such Chain")])
        rows = [_row(**{"Chain Name": "Reliance"})]
        _write_offtake(self.raw_dir / "offtake_store_article_May_26.csv", rows)
        result = build_dataset(self.cfg, self.raw_dir, self.masters_dir)
        self.assertIn("unmapped chain", result["warning"])  # alias ignored, chain stays unmapped
        out_dir = self.cfg.root() / result["output_file"]
        with open(out_dir / "Mapping_Exception_Report.csv", newline="", encoding="utf-8") as fh:
            exc = list(csv.DictReader(fh))
        self.assertTrue(any(e["exception_type"] == "invalid_alias" for e in exc))

    def test_exact_duplicate_rows_dropped_business_key_dups_kept(self):
        dup = _row(NSV="15.0")
        rekey = _row(NSV="8.5")  # same (site, ean, month) business key, different values
        _write_offtake(self.raw_dir / "offtake_store_article_May_26.csv", [dup, dup, rekey])
        result = build_dataset(self.cfg, self.raw_dir, self.masters_dir)
        out_dir = self.cfg.root() / result["output_file"]
        with open(out_dir / "Fact_OfftakeSales.csv", newline="", encoding="utf-8") as fh:
            fact_rows = list(csv.DictReader(fh))
        # 15.0 counted once (exact dup dropped) + 8.5 re-line kept
        self.assertAlmostEqual(sum(float(r["NSV"]) for r in fact_rows), 23.5, places=4)
        with open(out_dir / "Data_Quality_Report.csv", newline="", encoding="utf-8") as fh:
            dq = {r["metric"]: r for r in csv.DictReader(fh)}
        self.assertEqual(dq["exact_duplicate_rows_dropped"]["value"], "1")
        self.assertEqual(dq["duplicate_business_keys"]["value"], "1")
        # variance vs source is fully explained by the dropped duplicate -> still PASS
        with open(out_dir / "Source_Reconciliation_Report.csv", newline="", encoding="utf-8") as fh:
            recon = {r["metric"]: r for r in csv.DictReader(fh)}
        self.assertEqual(recon["NSV"]["status"], "PASS")

    def test_pivot_and_outlier_reports_written(self):
        rows = [_row(NSV="15.0"),
                _row(**{"Site Code": "SITE2", "Category": "Hair", "EAN": "8900000000002",
                        "Brand": "BBlunt", "NSV": "4.0"})]
        _write_offtake(self.raw_dir / "offtake_store_article_May_26.csv", rows)
        result = build_dataset(self.cfg, self.raw_dir, self.masters_dir)
        out_dir = self.cfg.root() / result["output_file"]

        with open(out_dir / "Pivot_Chain_Category_NSV.csv", newline="", encoding="utf-8") as fh:
            pivot = list(csv.reader(fh))
        self.assertEqual(pivot[0][0], "Chain")
        self.assertIn("Face", pivot[0])
        self.assertIn("Hair", pivot[0])
        self.assertEqual(pivot[-1][0], "TOTAL")
        self.assertAlmostEqual(float(pivot[-1][-1]), 19.0, places=4)

        with open(out_dir / "Pivot_Zone_Brand_NSV.csv", newline="", encoding="utf-8") as fh:
            zb = list(csv.reader(fh))
        self.assertEqual(zb[0][0], "Zone")
        self.assertAlmostEqual(float(zb[-1][-1]), 19.0, places=4)

        with open(out_dir / "Outlier_Report.csv", newline="", encoding="utf-8") as fh:
            outliers = {r["check"]: r for r in csv.DictReader(fh)}
        for check in ("unmapped_chain_nsv_share", "blank_site_code_nsv_share",
                      "negative_chain_total_nsv", "negative_nsv_rows",
                      "sales_qty_without_mrp_value", "article_nsv_zscore"):
            self.assertIn(check, outliers)
            self.assertIn(outliers[check]["severity"], ("Critical", "High", "Medium", "Low", "Passed"))
        # clean fixture -> every check passes
        self.assertTrue(all(r["severity"] == "Passed" for r in outliers.values()), outliers)

    def test_sandbox_fact_restricted_to_matched_articles_core_fact_untouched(self):
        matched = _row(NSV="15.0")  # EAN 8900000000001 matches the seed ArticleMaster fixture
        unmatched = _row(**{"Site Code": "SITE2", "EAN": "9990000000009", "NSV": "6.0"})
        _write_offtake(self.raw_dir / "offtake_store_article_May_26.csv", [matched, unmatched])
        result = build_dataset(self.cfg, self.raw_dir, self.masters_dir)
        out_dir = self.cfg.root() / result["output_file"]

        # core Fact keeps BOTH rows -- never filtered or stripped
        with open(out_dir / "Fact_OfftakeSales.csv", newline="", encoding="utf-8") as fh:
            core_rows = list(csv.DictReader(fh))
        self.assertEqual(len(core_rows), 2)
        self.assertAlmostEqual(sum(float(r["NSV"]) for r in core_rows), 21.0, places=4)

        # sandbox only has the seed-matched row
        with open(out_dir / "Fact_Sandbox_SeedMatched.csv", newline="", encoding="utf-8") as fh:
            sandbox_rows = list(csv.DictReader(fh))
        self.assertEqual(len(sandbox_rows), 1)
        self.assertEqual(sandbox_rows[0]["EAN"], "8900000000001")
        self.assertAlmostEqual(float(sandbox_rows[0]["NSV"]), 15.0, places=4)

        with open(out_dir / "Data_Quality_Report.csv", newline="", encoding="utf-8") as fh:
            dq = {r["metric"]: r for r in csv.DictReader(fh)}
        self.assertIn("1/2 fact rows", dq["sandbox_model_coverage"]["value"])
        self.assertIn("quarantined NSV = 6.0", dq["sandbox_model_coverage"]["note"])

        with open(out_dir / "Dataset_Build_Log.json", encoding="utf-8") as fh:
            log = json.load(fh)
        self.assertEqual(log["sandbox_model"]["row_count"], 1)
        self.assertAlmostEqual(log["sandbox_model"]["nsv_covered"], 15.0, places=4)
        self.assertAlmostEqual(log["sandbox_model"]["nsv_quarantined"], 6.0, places=4)

        # main reconciliation is unaffected by the sandbox -- still PASS
        with open(out_dir / "Source_Reconciliation_Report.csv", newline="", encoding="utf-8") as fh:
            recon = {r["metric"]: r for r in csv.DictReader(fh)}
        self.assertEqual(recon["NSV"]["status"], "PASS")

    def test_blank_site_share_severity_escalates(self):
        rows = [_row(NSV="1.0"), _row(**{"Site Code": "", "NSV": "9.0"})]  # 90% of NSV blank-site
        _write_offtake(self.raw_dir / "offtake_store_article_May_26.csv", rows)
        result = build_dataset(self.cfg, self.raw_dir, self.masters_dir)
        out_dir = self.cfg.root() / result["output_file"]
        with open(out_dir / "Outlier_Report.csv", newline="", encoding="utf-8") as fh:
            outliers = {r["check"]: r for r in csv.DictReader(fh)}
        self.assertEqual(outliers["blank_site_code_nsv_share"]["severity"], "High")

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
