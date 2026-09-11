"""Core Invariant 2, enforced deterministically.

CLAUDE.md names figures that must survive every build. Until this test existed
they were instruction-only: a rebuild could silently drop a closed year and
nothing would catch it.

What is protected lives in config/baselines.json, not here, so a deliberate
change is an edit to that file with a stated reason and owner -- visible in
review -- rather than a number quietly moving inside data.js.

Three protection classes, because not everything should be frozen:
  frozen_history   a closed FY. Exact. A mismatch is a build defect.
  approved_current this FY's approved figure. Exact, keyed by FY.
  tracked_universe legitimately evolves. Must be present, positive, and equal to
                   the recorded value, so a refresh is deliberate, not drift.
"""
import json
import re
import unittest
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
from ci_validate_datajs import check_baselines, dig  # noqa: E402
BASELINE = REPO / "config" / "baselines.json"
DATA_JS = REPO / "dashboard" / "data.js"


def load_dash(text=None):
    t = text if text is not None else DATA_JS.read_text()
    return json.loads(t[re.search(r"window\.DASH\s*=\s*", t).end():].rstrip().rstrip(";"))


def checks():
    return json.loads(BASELINE.read_text())["checks"]


class BaselineFile(unittest.TestCase):
    def test_every_check_is_fully_declared(self):
        for c in checks():
            for field in ("key", "path", "expected", "unit", "class", "why", "owner"):
                self.assertIn(field, c, f"{c.get('key')} missing {field}")
            self.assertIn(c["class"], {"frozen_history", "approved_current", "tracked_universe"})

    def test_frozen_history_is_never_given_a_loose_tolerance(self):
        """A wide tolerance on a closed year would defeat the whole check."""
        for c in checks():
            if c["class"] == "frozen_history":
                self.assertLessEqual(c.get("tolerance", 0.01), 0.01, c["key"])

    def test_approved_figures_name_their_financial_year(self):
        for c in checks():
            if c["class"] == "approved_current":
                self.assertRegex(c.get("fy", ""), r"^FY\d{2}$", c["key"])


class LiveDataMatchesBaseline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.D = load_dash()

    def test_every_protected_value_is_present(self):
        for c in checks():
            self.assertIsNotNone(dig(self.D, c["path"]), f"{c['key']}: {c['path']} missing")

    def test_every_protected_value_matches(self):
        for c in checks():
            actual = dig(self.D, c["path"])
            self.assertAlmostEqual(actual, c["expected"], delta=max(c.get("tolerance", 0.01), 1e-9),
                                   msg=f"{c['key']} ({c['class']}) — {c['why']}")

    def test_universe_counts_are_positive(self):
        for c in checks():
            if c["class"] == "tracked_universe":
                self.assertGreater(dig(self.D, c["path"]), 0, c["key"])

    def test_fy27_target_and_forecast_agree(self):
        """Two independent paths carry the same approved figure; a drift is a defect."""
        self.assertAlmostEqual(dig(self.D, "targets.fy_target"),
                               dig(self.D, "forecast.fy27_forecast"), delta=0.01)


class TamperDetection(unittest.TestCase):
    """The negative test: prove the check actually fires.

    This calls the validator's own check_baselines() rather than a second copy of
    the comparison, so the test cannot pass while the code CI runs is broken.
    Mutations are applied to an in-memory copy; production data.js is never
    written to, so there is nothing to restore.
    """

    def _detect(self, mutate):
        D = load_dash()
        mutate(D)
        return check_baselines(D)

    def test_clean_data_reports_nothing(self):
        self.assertEqual(self._detect(lambda D: None), [])

    def test_dropped_closed_year_is_caught(self):
        f = self._detect(lambda D: D["offtake"].pop("total_fy26"))
        self.assertTrue(any("offtake_fy26_total" in x for x in f), f)

    def test_altered_closed_year_is_caught(self):
        f = self._detect(lambda D: D["offtake"].__setitem__("total_fy26", 31119.87 * 0.9))
        self.assertTrue(any("offtake_fy26_total" in x for x in f), f)

    def test_altered_approved_target_is_caught(self):
        f = self._detect(lambda D: D["targets"].__setitem__("fy_target", 50000.0))
        self.assertTrue(any("fy27_target" in x for x in f), f)

    def test_collapsed_store_count_is_caught(self):
        f = self._detect(lambda D: D["universe"].__setitem__("active_stores", 0))
        self.assertTrue(any("active_stores" in x for x in f), f)

    def test_a_tiny_rounding_difference_is_tolerated(self):
        """Guard against a test so strict that ordinary float noise fails the build."""
        self.assertEqual(
            self._detect(lambda D: D["offtake"].__setitem__("total_fy26", 31119.875)), [])


if __name__ == "__main__":
    unittest.main()
