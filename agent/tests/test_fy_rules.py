"""Pin THE ONE FY RULE — these examples come straight from CLAUDE.md and the
docstrings in scripts/build_dashboard_data.py. If this test fails, the agent
has drifted from the dashboard build script."""
import unittest

from mtagent import fyrules as fy


class TestFyTagFromYm(unittest.TestCase):
    def test_claude_md_examples(self):
        self.assertEqual(fy.fy_tag_from_ym(2026, 4), "FY27")   # Apr-26 -> FY27
        self.assertEqual(fy.fy_tag_from_ym(2026, 3), "FY26")   # Mar-26 -> FY26

    def test_boundaries(self):
        self.assertEqual(fy.fy_tag_from_ym(2024, 4), "FY25")
        self.assertEqual(fy.fy_tag_from_ym(2024, 12), "FY25")
        self.assertEqual(fy.fy_tag_from_ym(2025, 1), "FY25")
        self.assertEqual(fy.fy_tag_from_ym(2025, 3), "FY25")
        self.assertEqual(fy.fy_tag_from_ym(2025, 4), "FY26")

    def test_future_fys_work_automatically(self):
        self.assertEqual(fy.fy_tag_from_ym(2027, 4), "FY28")
        self.assertEqual(fy.fy_tag_from_ym(2030, 2), "FY30")


class TestLabels(unittest.TestCase):
    def test_dash_style(self):
        self.assertEqual(fy.fy_tag_from_label("Apr-24"), "FY25")
        self.assertEqual(fy.fy_tag_from_label("Mar-26"), "FY26")

    def test_apostrophe_style_used_by_source_csvs(self):
        self.assertEqual(fy.fy_tag_from_label("Apr'25"), "FY26")
        self.assertEqual(fy.fy_tag_from_label("Apr'26"), "FY27")

    def test_garbage_is_none(self):
        self.assertIsNone(fy.fy_tag_from_label("Total"))
        self.assertIsNone(fy.fy_tag_from_label(""))
        self.assertIsNone(fy.fy_tag_from_label("2026-04"))


class TestDerived(unittest.TestCase):
    def test_fy_start_year_roundtrip(self):
        self.assertEqual(fy.fy_start_year("FY27"), 2026)
        for tag in ("FY25", "FY26", "FY27", "FY31"):
            self.assertEqual(fy.fy_tag_from_ym(fy.fy_start_year(tag), 4), tag)

    def test_fy_source_key(self):
        self.assertEqual(fy.fy_source_key("FY26"), "FY_25-26")

    def test_quarters(self):
        self.assertEqual(fy.fy_quarter(4), 1)
        self.assertEqual(fy.fy_quarter(12), 3)
        self.assertEqual(fy.fy_quarter(1), 4)
        self.assertEqual(fy.fy_quarter(3), 4)

    def test_month_labels(self):
        labs = fy.month_labels(2024, 26)
        self.assertEqual(labs[0], "Apr-24")
        self.assertEqual(labs[-1], "May-26")
        self.assertEqual(len(labs), 26)


class TestSqlMacroParity(unittest.TestCase):
    """The DuckDB fy_from_ym macro must agree with the Python helper.
    Executed only when duckdb is installed; the macro text is always
    importable so at minimum the module stays syntactically alive."""

    def test_macros_agree_with_python(self):
        try:
            import duckdb
        except ImportError:
            self.skipTest("duckdb not installed")
        from mtagent.duck import FY_MACROS
        con = duckdb.connect(":memory:")
        con.execute(FY_MACROS)
        for y in range(2024, 2029):
            for m in range(1, 13):
                got = con.execute("SELECT fy_from_ym(?, ?)", [y, m]).fetchone()[0]
                self.assertEqual(got, fy.fy_tag_from_ym(y, m), f"{y}-{m}")
        for lab in ("Apr'25", "Mar-26", "Apr-26", "46113.0", "46113",
                    "Total", "", "garbage"):
            got = con.execute("SELECT fy_from_label(?)", [lab]).fetchone()[0]
            self.assertEqual(got, fy.fy_tag_from_label(lab), lab)
        got = con.execute("SELECT norm_month_label('46113.0')").fetchone()[0]
        self.assertEqual(got, fy.norm_month_label("46113.0"))


if __name__ == "__main__":
    unittest.main()
