import json
import tempfile
import unittest
from pathlib import Path

from mtagent.config import Config
from mtagent.pbi_dax_gap import (REQUIRED_MEASURES, _normalize_measure_name,
                                 generate_dax_library)

REPO = Path(__file__).resolve().parents[2]
DAX_DIR = REPO / "PowerBI" / "DAX"


class TestNormalization(unittest.TestCase):
    def test_matches_across_naming_conventions(self):
        self.assertEqual(_normalize_measure_name("NSV Cr"), _normalize_measure_name("NSV (Cr)"))
        self.assertEqual(_normalize_measure_name("MoM Growth %"), _normalize_measure_name("MoM Growth%"))

    def test_genuinely_different_names_do_not_match(self):
        self.assertNotEqual(_normalize_measure_name("Growth versus L3M %"), _normalize_measure_name("Growth vs L3M %"))


class TestRequiredCatalogueShape(unittest.TestCase):
    def test_every_entry_has_the_full_metadata_tuple(self):
        for name, entry in REQUIRED_MEASURES.items():
            self.assertEqual(len(entry), 6, f"{name} entry should be (category, desc, fmt, folder, deps, qc_test)")
            category, desc, fmt, folder, deps, qc_test = entry
            self.assertTrue(desc, f"{name} missing description")
            self.assertTrue(fmt, f"{name} missing format string")
            self.assertTrue(folder, f"{name} missing display folder")
            self.assertTrue(qc_test, f"{name} missing QC test")
            self.assertIsInstance(deps, list)

    def test_covers_all_five_spec_categories(self):
        categories = {c for c, *_ in REQUIRED_MEASURES.values()}
        self.assertEqual(categories, {"Core", "Time Intelligence", "Growth", "Business", "QC"})


class TestGenerateDaxLibrarySynthetic(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.dax_dir = root / "PowerBI" / "DAX"
        self.dax_dir.mkdir(parents=True)
        self.cfg = Config(repo_root=str(root), index_path="agent/index/index.json")

    def tearDown(self):
        self.tmp.cleanup()

    def test_blocked_when_dax_dir_missing(self):
        result = generate_dax_library(self.cfg, self.dax_dir.parent / "does_not_exist")
        self.assertIn("blocked_reason", result)

    def test_present_measure_is_not_in_gap_file(self):
        (self.dax_dir / "01_Core.dax").write_text("NSV Cr = DIVIDE ( [NSV], 10000000 )\n", encoding="utf-8")
        result = generate_dax_library(self.cfg, self.dax_dir)
        report = json.loads(result["validation_result"])
        self.assertNotIn("NSV Cr", report["missing_measures"])
        self.assertEqual(report["present"], 1)

    def test_missing_measures_get_a_divide_safe_generated_snippet(self):
        result = generate_dax_library(self.cfg, self.dax_dir)  # empty DAX dir -> everything missing
        report = json.loads(result["validation_result"])
        self.assertEqual(report["missing"], len(REQUIRED_MEASURES))
        out_dir = self.cfg.root() / result["output_file"]
        gap_text = (out_dir / "DAX_Gap_Library.dax").read_text(encoding="utf-8")
        self.assertIn("NSV Actual =", gap_text)
        self.assertIn("STAGED FOR REVIEW ONLY", gap_text)  # never auto-applied to the live model

    def test_full_coverage_produces_empty_gap_file_and_no_warning(self):
        snippets = "\n".join(f"{name} = 0\n" for name in REQUIRED_MEASURES)
        (self.dax_dir / "everything.dax").write_text(snippets, encoding="utf-8")
        result = generate_dax_library(self.cfg, self.dax_dir)
        self.assertEqual(result["warning"], "")
        report = json.loads(result["validation_result"])
        self.assertEqual(report["coverage_pct"], 100.0)

    def test_catalogue_csv_lists_every_required_measure_exactly_once(self):
        result = generate_dax_library(self.cfg, self.dax_dir)
        out_dir = self.cfg.root() / result["output_file"]
        import csv
        with open(out_dir / "Measure_Catalogue.csv", newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        self.assertEqual(len(rows), len(REQUIRED_MEASURES))
        self.assertEqual({r["measure"] for r in rows}, set(REQUIRED_MEASURES))


class TestGenerateDaxLibraryOnRealRepoDax(unittest.TestCase):
    def setUp(self):
        if not list(DAX_DIR.glob("*.dax")):
            self.skipTest("no PowerBI/DAX files in this checkout")

    def test_runs_without_crashing_and_finds_known_present_measures(self):
        cfg = Config(repo_root=str(REPO), index_path="agent/index/index_test_only.json",
                     pbi_build_dir="agent/pbi_build_test_only")
        try:
            result = generate_dax_library(cfg, DAX_DIR)
            self.assertNotIn("blocked_reason", result)
            report = json.loads(result["validation_result"])
            # measures confirmed present by manual inspection of 01_CoreMeasures.dax
            self.assertNotIn("NSV Cr", report["missing_measures"])
            self.assertNotIn("Contribution %", report["missing_measures"])
        finally:
            import shutil
            shutil.rmtree(cfg.root() / cfg.pbi_build_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
