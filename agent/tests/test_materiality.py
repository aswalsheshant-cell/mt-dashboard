"""Tests for the materiality filter (§E in AI_LEVERAGE_AND_JUDGMENT.md).

Spec Test 7: "Generate leadership insights for June" should prioritize the
top growth driver, largest decline, and material exceptions -- not a long
list of every small movement.
"""
import unittest

from mtagent.validators import materiality as mat


class TestIsMaterial(unittest.TestCase):
    def test_pct_change_above_threshold_is_material(self):
        self.assertTrue(mat.is_material(pct_change=0.15))

    def test_pct_change_below_threshold_is_not_material(self):
        self.assertFalse(mat.is_material(pct_change=0.03))

    def test_abs_impact_above_threshold_is_material(self):
        self.assertTrue(mat.is_material(abs_impact=15_00_000))

    def test_abs_impact_below_threshold_is_not_material(self):
        self.assertFalse(mat.is_material(abs_impact=50_000))

    def test_nothing_provided_is_not_material(self):
        self.assertFalse(mat.is_material())


class TestRankMovements(unittest.TestCase):
    """Spec Test 7 scenario: a June leadership summary should surface the
    top growth driver and largest decline, not every SKU/account movement."""

    def _june_movements(self):
        return [
            {"name": "D-Mart NSV growth", "pct_change": 0.34, "abs_impact": 45_00_000},
            {"name": "Reliance decline", "pct_change": -0.22, "abs_impact": -28_00_000},
            {"name": "Apollo minor uptick", "pct_change": 0.02, "abs_impact": 40_000},
            {"name": "Vishal Mega Mart flat", "pct_change": 0.01, "abs_impact": 5_000},
            {"name": "More Retail small dip", "pct_change": -0.015, "abs_impact": -8_000},
            {"name": "Spencer's mapping exception", "pct_change": None, "abs_impact": 12_00_000},
        ]

    def test_only_material_movements_are_returned(self):
        ranked = mat.rank_movements(self._june_movements())
        names = {m["name"] for m in ranked}
        self.assertIn("D-Mart NSV growth", names)
        self.assertIn("Reliance decline", names)
        self.assertIn("Spencer's mapping exception", names)
        self.assertNotIn("Apollo minor uptick", names)
        self.assertNotIn("Vishal Mega Mart flat", names)
        self.assertNotIn("More Retail small dip", names)

    def test_sorted_by_largest_absolute_impact_first(self):
        ranked = mat.rank_movements(self._june_movements())
        impacts = [abs(m["abs_impact"]) for m in ranked]
        self.assertEqual(impacts, sorted(impacts, reverse=True))

    def test_capped_at_top_n(self):
        movements = [{"name": f"driver_{i}", "pct_change": 0.5, "abs_impact": 100_00_000 - i}
                     for i in range(25)]
        ranked = mat.rank_movements(movements, top_n=10)
        self.assertEqual(len(ranked), 10)

    def test_does_not_produce_a_long_list_of_every_small_movement(self):
        # 90% of these movements are immaterial noise -- the ranked output
        # must not just echo the input back.
        movements = self._june_movements()
        ranked = mat.rank_movements(movements)
        self.assertLess(len(ranked), len(movements))


if __name__ == "__main__":
    unittest.main()
