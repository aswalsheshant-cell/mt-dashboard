import unittest
from pathlib import Path

from mtagent import fyrules as fy
from mtagent.config import Config
from mtagent.diffengine import (MIN_BASE_LAKH, _drops, analyze_offtake,
                                file_month, format_drilldown_context,
                                format_exception_report,
                                gst_confidence_summary)

REPO = Path(__file__).resolve().parents[2]


def _cfg() -> Config:
    return Config(repo_root=str(REPO))


# analyze_offtake parses two ~200k-row CSVs (~5s) — do it once for the module
_REPORT = None


def report():
    global _REPORT
    if _REPORT is None:
        _REPORT = analyze_offtake(_cfg())
    return _REPORT


class TestSerialFloats(unittest.TestCase):
    def test_fractional_serials_floor(self):
        # the data contract accepts floating-point serials; both engines floor
        self.assertEqual(fy.fy_tag_from_label("46113.5"), "FY27")
        self.assertEqual(fy.norm_month_label("46113.9"), "Apr-26")

    def test_file_month(self):
        self.assertEqual(file_month(Path("offtake_store_article_Apr_26.csv")),
                         (2026, 4))
        self.assertIsNone(file_month(Path("_TEMPLATE_Offtake_Monthly.csv")))


class TestDropsGuard(unittest.TestCase):
    def test_small_bases_ignored(self):
        prior = {"A": MIN_BASE_LAKH / 2, "B": 100.0}
        cur = {"A": 0.0, "B": 50.0}
        hits = _drops(prior, cur, 10.0)
        self.assertEqual([k for k, *_ in hits], ["B"])

    def test_threshold(self):
        hits = _drops({"B": 100.0}, {"B": 95.0}, 10.0)   # -5% < threshold
        self.assertEqual(hits, [])


class TestAnalyzeRealData(unittest.TestCase):
    """Runs against the latest two committed offtake months. Currently
    May'26 / June'26 -- update these three expectations (and the reconcile
    numbers they're pinned against) whenever a newer month is added to
    Offtake_Monthly, same as the last shift from Mar/Apr to Apr/May."""

    def test_month_pair(self):
        r = report()
        self.assertIsNotNone(r)
        self.assertEqual(r["prior"].label, "May-26")
        self.assertEqual(r["cur"].label, "Jun-26")
        self.assertGreater(r["prior"].rows, 100000)

    def test_serial_month_rows_included(self):
        # May'26 has no Excel-serial Month rows (unlike Apr'26's 32,494);
        # serial-format handling itself is covered separately by
        # TestExcelSerialLabels in test_catalog_reconcile.py. This just
        # pins the prior month's real total, cross-checked against
        # mtagent reconcile's own "offtake FY27 month May-26" row (which
        # reads OK against dashboard/data.js -- both agree at 4527.61L).
        r = report()
        total = sum(r["prior"].zone_nsv.values())
        self.assertAlmostEqual(total, 4527.61, delta=1.0)

    def test_report_sections(self):
        r = report()
        txt = format_exception_report(r)
        self.assertIn("1) Volume/NSV drops", txt)
        self.assertIn("2) NPI tracking", txt)
        self.assertIn("3) Operational gaps", txt)
        self.assertIn("Proactive Exception Report — Jun-26 vs May-26", txt)

    def test_normalization_no_phantom_chains(self):
        # TRIM+UPPER keys: no chain may appear twice differing only by case
        r = report()
        chains = {c for c, _ in r["cur"].chaindc_nsv}
        self.assertEqual(len(chains), len({c.upper().strip() for c in chains}))

    def test_missing_stores_have_prior_nsv(self):
        r = report()
        for s, name, chain, stype, pnsv in r["missing_stores"]:
            self.assertGreater(pnsv, 0)

    def test_drilldown_context(self):
        txt = format_drilldown_context(_cfg(), report())
        self.assertIn("underperforming outlets", txt)
        self.assertIn("sub-category NSV delta", txt)
        self.assertIn("pack-size", txt)
        self.assertIn("GST/TOT confidence", txt)


class TestGstSummary(unittest.TestCase):
    def test_rows(self):
        rows = gst_confidence_summary(_cfg())
        self.assertGreater(len(rows), 5)
        self.assertTrue(all(r["confidence"] for r in rows))
        # today every row is Pending — the drill-down must say so
        self.assertTrue(any(r["finance_approved"].lower() == "pending"
                            for r in rows))


class TestCliWiring(unittest.TestCase):
    def test_meeting_drilldown_flag(self):
        from mtagent.cli import build_parser
        ap = build_parser()
        a = ap.parse_args(["meeting", "why", "--drilldown"])
        self.assertTrue(a.drilldown)
        a = ap.parse_args(["meeting", "why", "--verbose"])
        self.assertTrue(a.drilldown)
        a = ap.parse_args(["meeting", "why"])
        self.assertFalse(a.drilldown)

    def test_config_defaults(self):
        cfg = _cfg()
        self.assertEqual(cfg.mom_drop_threshold_pct, 10.0)
        self.assertEqual(cfg.drilldown_top_n, 5)
        self.assertIn("NPI_List.csv", cfg.npi_list)


class TestPersonaAdditions(unittest.TestCase):
    def test_data_contract_rules(self):
        from mtagent.persona import system_prompt
        p = system_prompt()
        for token in ("TRIM+UPPER", "unmapped_staging", "1899-12-30",
                      "NEVER dropped"):
            self.assertIn(token, p, token)

    def test_drilldown_mode(self):
        from mtagent.persona import system_prompt
        d = system_prompt("drilldown")
        self.assertIn("brevity limit is LIFTED", d)
        self.assertIn("Finance signed-off", d)
        self.assertNotIn("brevity limit is LIFTED", system_prompt("meeting"))


if __name__ == "__main__":
    unittest.main()
