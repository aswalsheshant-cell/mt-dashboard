"""One FY rule, one source: month -> FY everywhere (permanent guard).

* The Power Query formula (fnFYLabel) must agree with the pipeline's
  fy_tag_from_ym for every month of every year -- so Power BI, data.js and the
  HTML dashboard can never disagree about which FY a month belongs to.
* The validator passes on the real repo, and FAILS on a month filed under the
  wrong FY or a fact query that copies FY text from the source.
"""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
import build_dashboard_data as b  # noqa: E402
import validate_fy_month_consistency as v  # noqa: E402


def m_label(year, month):
    """Python mirror of PowerQuery/02_fnFYLabel.pq (same arithmetic)."""
    start = year if month >= 4 else year - 1
    return f"{start % 100:02d}-{(start + 1) % 100:02d}"


class FormulaAgreesWithPipeline(unittest.TestCase):
    def test_label_matches_fy_tag_for_every_month_2020_2045(self):
        for y in range(2020, 2046):
            for m in range(1, 13):
                tag = b.fy_tag_from_ym(y, m)               # e.g. 'FY27'
                end = int(tag[2:])
                self.assertEqual(m_label(y, m), f"{(end - 1) % 100:02d}-{end:02d}", (y, m))
                self.assertEqual(v.fy_end_2digit(y, m), end, (y, m))

    def test_known_boundaries(self):
        self.assertEqual(m_label(2026, 3), "25-26")
        self.assertEqual(m_label(2026, 4), "26-27")
        self.assertEqual(m_label(2027, 4), "27-28")   # FY28 works with no code change


class ValidatorOnRepo(unittest.TestCase):
    def test_repo_is_clean(self):
        self.assertEqual(0, v.main(["--root", str(REPO)]))

    def test_power_query_facts_derive_fy(self):
        self.assertEqual([], v.check_powerquery(REPO))


class ValidatorCatchesDefects(unittest.TestCase):
    def _tmp_repo(self):
        d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d, True)
        (d / "PowerBI" / "PowerQuery").mkdir(parents=True)
        (d / "dashboard").mkdir()
        return d

    def test_wrong_fy_row_is_caught(self):
        d = self._tmp_repo()
        (d / "PowerBI" / "x.csv").write_text(
            "Month,FY Year\nApr-26,FY27\nMar-26,FY27\n", encoding="utf-8")   # Mar-26 is FY26
        bad, _, n = v.check_csvs(d)
        self.assertEqual(2, n)
        self.assertEqual(1, len(bad))
        self.assertIn("Mar-26", bad[0])

    def test_mixed_label_formats_with_right_year_pass(self):
        d = self._tmp_repo()
        (d / "PowerBI" / "x.csv").write_text(
            "Month,FY\nApr-26,FY27\nMay-26,FY'26-27\nJun-26,FY_26-27\nJul-26,26-27\n", encoding="utf-8")
        bad, fm, _ = v.check_csvs(d)
        self.assertEqual([], bad)
        self.assertEqual(4, len(next(iter(fm.values()))))

    def test_datajs_month_in_wrong_fy_is_caught(self):
        d = self._tmp_repo()
        (d / "dashboard" / "data.js").write_text(
            'window.DASH={"offtake":{"months_fy27":["Apr-26","Mar-26"]}};', encoding="utf-8")
        bad, n = v.check_datajs(d / "dashboard" / "data.js")
        self.assertEqual(2, n)
        self.assertEqual(1, len(bad))

    def test_fact_query_that_copies_source_fy_is_caught(self):
        d = self._tmp_repo()
        pq = d / "PowerBI" / "PowerQuery"
        (pq / "02_fnFYLabel.pq").write_text("let f = 1 in f", encoding="utf-8")
        for q in v.FACT_QUERIES:
            (pq / (q + ".pq")).write_text("let\n  S = 1\nin\n  S\n", encoding="utf-8")
        self.assertEqual(len(v.FACT_QUERIES), len(v.check_powerquery(d)))


if __name__ == "__main__":
    unittest.main()
