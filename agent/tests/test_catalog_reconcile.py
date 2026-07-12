import tempfile
import unittest
from pathlib import Path

from mtagent import fyrules as fy
from mtagent.catalog import classify, find, load_catalog, suggest_placement
from mtagent.config import Config
from mtagent.reconcile import load_dash, run_reconciliation
from mtagent.worklog import log_run, read_log

REPO = Path(__file__).resolve().parents[2]


def _cfg(**kw) -> Config:
    return Config(repo_root=str(REPO), **kw)


class TestExcelSerialLabels(unittest.TestCase):
    """Some offtake extracts carry Excel date serials in the Month column
    ('46113.0' = 2026-04-01); the FY rules must accept them like the
    dashboard build does."""

    def test_serial_to_fy(self):
        self.assertEqual(fy.fy_tag_from_label("46113.0"), "FY27")
        self.assertEqual(fy.fy_tag_from_label("46113"), "FY27")
        self.assertEqual(fy.norm_month_label("46113.0"), "Apr-26")

    def test_serial_and_text_agree(self):
        self.assertEqual(fy.norm_month_label("Apr'26"),
                         fy.norm_month_label("46113.0"))

    def test_plain_numbers_not_mistaken(self):
        self.assertIsNone(fy.fy_tag_from_label("2026"))     # 4 digits
        self.assertIsNone(fy.fy_tag_from_label("123456"))   # 6 digits
        self.assertIsNone(fy.norm_month_label("Total"))


class TestReconcile(unittest.TestCase):
    def test_dash_parses(self):
        d = load_dash(REPO)
        self.assertIn("primary", d)
        self.assertIn("offtake", d)

    def test_dashboard_reconciles_with_sources(self):
        # The committed data.js was built FROM the committed CSVs, so the
        # internal + article layers must be clean. If this fails, either a
        # CSV changed without a data.js rebuild or vice versa — a real
        # refresh problem, exactly what /reconcile exists to catch.
        result = run_reconciliation(_cfg())
        diffs = [r for r in result["rows"] if r["status"] == "DIFF"]
        self.assertEqual(diffs, [], diffs)
        self.assertGreaterEqual(
            sum(r["status"] == "OK" for r in result["rows"]), 5)

    def test_row_shape(self):
        rows = run_reconciliation(_cfg())["rows"]
        for r in rows:
            self.assertIn(r["status"], ("OK", "DIFF", "INFO", "N/A"))
            self.assertIn("dashboard_lakh", r)
            self.assertIn("source_lakh", r)


class TestCatalog(unittest.TestCase):
    def test_classify_known_paths(self):
        self.assertEqual(classify("dashboard/data.js").category,
                         "Dashboard — generated data")
        self.assertEqual(classify("PowerBI/DAX/01_CoreMeasures.dax").category,
                         "Power BI — DAX measures")
        e = classify("PowerBI/RawDataFolders/Offtake_Monthly/"
                     "offtake_store_article_Apr_26.csv")
        self.assertEqual(e.category, "Data drops — offtake monthly")
        self.assertEqual(e.fy, "FY27")
        self.assertEqual(e.month, "Apr-26")

    def test_find_locates_masters(self):
        with tempfile.TemporaryDirectory() as d:
            cfg = _cfg(index_path=str(Path(d) / "index.json"))
            hits = find(cfg, "chain master seed csv")
            self.assertTrue(hits)
            self.assertTrue(any("ChainMaster.csv" in e.path for _, e in hits),
                            [e.path for _, e in hits])

    def test_placement_offtake(self):
        s = suggest_placement("New MT offtake dump June.xlsb")
        self.assertEqual(s["folder"], "PowerBI/RawDataFolders/Offtake_Monthly/")
        self.assertIn("--offtake-patch", s["then"])

    def test_placement_metadata_and_unknown(self):
        self.assertEqual(suggest_placement("model.bim")["folder"], "agent/metadata/")
        self.assertIsNone(suggest_placement("mystery.bin")["folder"])

    def test_catalog_covers_repo(self):
        with tempfile.TemporaryDirectory() as d:
            cfg = _cfg(index_path=str(Path(d) / "index.json"))
            entries = load_catalog(cfg)
        self.assertGreater(len(entries), 100)
        uncat = [e.path for e in entries if e.category == "uncategorised"]
        self.assertEqual(uncat, [], uncat)   # every tracked file has a home


class TestWorklog(unittest.TestCase):
    def test_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            cfg = _cfg(index_path=str(Path(d) / "index.json"))
            log_run(cfg, "reconcile", ["reconcile"], 0, ["clean"])
            log_run(cfg, "qc", ["qc", "--strict"], 1)
            entries = read_log(cfg, tail=10)
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]["command"], "reconcile")
        self.assertEqual(entries[1]["status"], 1)


class TestPersona(unittest.TestCase):
    def test_rules_present(self):
        from mtagent.persona import system_prompt
        p = system_prompt()
        for token in ("FY(Y+1)", "Lakh", "x 100000", "/ 100", "net of tax",
                      "MRP includes", "Pending is NOT zero", "Others",
                      "2025-09-22", "Cont%", "read-only",
                      "Observation, Analysis, Recommendation"):
            self.assertIn(token, p, token)

    def test_meeting_mode_appends_format(self):
        from mtagent.persona import system_prompt
        m = system_prompt("meeting")
        self.assertIn("Top 3 drivers", m)
        self.assertNotIn("Top 3 drivers", system_prompt("ask"))


if __name__ == "__main__":
    unittest.main()
