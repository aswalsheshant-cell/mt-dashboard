"""Regression coverage for scripts/build_incentive_identity.py's placeholder
detection -- narrow, isolated from the full workbook build (which needs
RESTRICTED source files this test suite doesn't have access to).
"""
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

from build_incentive_identity import PLACEHOLDERS  # noqa: E402


class PlaceholderDetection(unittest.TestCase):
    def test_matches_bare_placeholder_tokens(self):
        for v in ("VACANT", "TBD", "N/A", "NA", "open", "blank", "---"):
            self.assertTrue(PLACEHOLDERS.match(v), f"{v!r} should match")

    def test_matches_placeholder_with_underscore_suffix(self):
        """Vacant_S1 (a real WoA source value) was silently classified
        INSUFFICIENT_EVIDENCE instead of SOURCE_DATA_FIX_REQUIRED because the
        old pattern's \\b assertion never fires between 'vacant' and '_' --
        both are \\w characters, so there's no boundary there.
        """
        for v in ("Vacant_S1", "VACANT_North", "tbd_pending"):
            self.assertTrue(PLACEHOLDERS.match(v), f"{v!r} should match")

    def test_does_not_match_real_names(self):
        """The fix must not start catching real names that merely start with
        a placeholder-like prefix (Narala, Nagaraju) -- the whole reason this
        is a word-boundary-shaped pattern rather than a bare prefix check.
        """
        for v in ("Narala Shalini", "Nagaraju Thadi", "Anand Haveri",
                   "Naeem Mohammad"):
            self.assertFalse(PLACEHOLDERS.match(v), f"{v!r} should NOT match")


if __name__ == "__main__":
    unittest.main()
