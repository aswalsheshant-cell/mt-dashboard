"""Chhattisgarh ("CG" in the primary article files) must land in Central, not West."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import build_dashboard_data as b


class CgCentralZoneTests(unittest.TestCase):
    def test_cg_label_is_central_even_when_source_says_west(self):
        for label in ("CG", "Cg", "cg ", "Chattishgarh", "Chhattisgarh"):
            self.assertEqual(b.zone_with_central_override("West", label), "Central", label)

    def test_madhya_pradesh_still_central(self):
        self.assertEqual(b.zone_with_central_override("West", "Madhya Pradesh"), "Central")

    def test_other_states_keep_the_source_zone(self):
        self.assertEqual(b.zone_with_central_override("West", "Maharashtra"), "West")
        self.assertEqual(b.zone_with_central_override("North", "Rajasthan"), "North")

    def test_source_central_tag_is_not_clobbered(self):
        self.assertEqual(b.zone_with_central_override("Central", "Maharashtra"), "Central")


if __name__ == "__main__":
    unittest.main()
