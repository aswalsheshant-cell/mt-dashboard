import unittest
from pathlib import Path

from mtagent.config import Config
from mtagent.sql_templates import get_template, list_templates, render

REPO = Path(__file__).resolve().parents[2]


def _cfg() -> Config:
    return Config(repo_root=str(REPO))


class TestTemplates(unittest.TestCase):
    def test_all_templates_listed(self):
        names = {t.name for t in list_templates(_cfg())}
        for expected in ("fy_summary", "monthly_nsv_trend", "chain_ranking",
                         "brand_category_mix", "primary_vs_offtake",
                         "shipto_chain_mix", "store_coverage", "data_quality"):
            self.assertIn(expected, names)

    def test_every_template_renders_with_defaults(self):
        for t in list_templates(_cfg()):
            sql = render(t)
            self.assertNotIn("{{", sql, t.name)
            self.assertTrue(sql.upper().lstrip().startswith(("SELECT", "WITH")), t.name)

    def test_param_override(self):
        t = get_template(_cfg(), "chain_ranking")
        sql = render(t, {"fy": "FY27"})
        self.assertIn("'FY27'", sql)

    def test_unsafe_param_rejected(self):
        t = get_template(_cfg(), "chain_ranking")
        with self.assertRaises(ValueError):
            render(t, {"fy": "FY26'; DROP TABLE x; --"})

    def test_unknown_param_rejected(self):
        t = get_template(_cfg(), "fy_summary")
        with self.assertRaises(ValueError):
            render(t, {"nope": "1"})

    def test_unknown_template_helpful_error(self):
        with self.assertRaises(KeyError):
            get_template(_cfg(), "does_not_exist")


class TestExecution(unittest.TestCase):
    """Executes only where duckdb is installed (analyst machines)."""

    def setUp(self):
        try:
            import duckdb  # noqa: F401
        except ImportError:
            self.skipTest("duckdb not installed")

    def test_build_and_run_everything(self):
        import tempfile
        from mtagent.duck import build_db, run_sql
        with tempfile.TemporaryDirectory() as d:
            cfg = Config(repo_root=str(REPO), db_path=str(Path(d) / "t.duckdb"))
            log = build_db(cfg)
            self.assertTrue(any("v_primary_article" in line for line in log))
            for t in list_templates(cfg):
                cols, rows = run_sql(cfg, render(t))
                self.assertTrue(cols, t.name)

    def test_fy_rule_holds_on_real_data(self):
        import tempfile
        from mtagent.duck import build_db, run_sql
        with tempfile.TemporaryDirectory() as d:
            cfg = Config(repo_root=str(REPO), db_path=str(Path(d) / "t.duckdb"))
            build_db(cfg)
            cols, rows = run_sql(cfg, """
                SELECT count(*) FROM v_primary_article
                WHERE right(trim("FY"), 2) <> right(fy_from_label("Month"), 2)
            """)
            self.assertEqual(rows[0][0], 0,
                             "source FY column disagrees with THE ONE FY RULE")


if __name__ == "__main__":
    unittest.main()
