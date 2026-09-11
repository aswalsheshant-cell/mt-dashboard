"""Published assets must never carry confidential HR, incentive or DMS data.

dashboard/ deploys to GitHub Pages, so anything in data.js or index.html is
public. This guards the boundary by PATTERN rather than by a list of real
names, so the test itself stays safe to commit and keeps working as staff
change.
"""
import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PUBLISHED = ["dashboard/data.js", "dashboard/index.html"]

# Employee IDs (HCPL####), DMS owner codes (GS########), and the tell-tale
# column headers that only ever appear in the confidential extracts.
FORBIDDEN = [
    (r"HCPL\d{3,}", "employee ID"),
    (r"\bGS1\d{7,}\b", "DMS owner code"),
    (r"Employee\s+Name", "employee-name column"),
    (r"Annual\s+Eligibility", "incentive eligibility column"),
    (r"Payout\s+Amount", "incentive payout column"),
    (r"Incentive[_ ]Grade", "incentive grade column"),
    # DMS/Massit is incentive-scope only (business instruction 2026-09-11): it
    # must not appear in, or influence, the commercial reports.
    (r"Massit", "DMS source reference"),
    (r"TotalTertiaryValue", "DMS measure"),
]


class TestPublishedAssetsPrivacy(unittest.TestCase):
    def test_no_confidential_patterns(self):
        for rel in PUBLISHED:
            p = REPO / rel
            if not p.exists():
                continue
            text = p.read_text(encoding="utf-8", errors="ignore")
            for pat, what in FORBIDDEN:
                hits = re.findall(pat, text)
                self.assertEqual(
                    hits, [],
                    f"{rel} contains {len(hits)} {what} match(es) e.g. {hits[:3]} — "
                    f"published assets are public; keep this data out of dashboard/.")

    def test_dms_block_absent_from_published_payload(self):
        """DMS is incentive-scope. Its consolidated block belongs in
        incentive_working/, never in the published dashboard payload."""
        p = REPO / "dashboard" / "data.js"
        if not p.exists():
            self.skipTest("data.js not present")
        import json
        s = p.read_text(encoding="utf-8")
        d = json.loads(s[s.index("{"):].rstrip().rstrip(";"))
        self.assertNotIn("sales_actuals", d,
                         "DMS consolidation must not be published — it is incentive-scope only.")
        cfg = d.get("config") or {}
        for k, v in cfg.items():
            if isinstance(v, dict):
                self.assertNotEqual(v.get("scope"), "INCENTIVE_ONLY",
                                    f"config section {k!r} is incentive-scope and must not be published.")

    def test_sales_actuals_is_aggregate_only(self):
        p = REPO / "dashboard" / "data.js"
        if not p.exists():
            self.skipTest("data.js not present")
        import json
        s = p.read_text(encoding="utf-8")
        d = json.loads(s[s.index("{"):].rstrip().rstrip(";"))
        sa = d.get("sales_actuals")
        if not sa:
            self.skipTest("sales_actuals not built yet")
        for row in sa.get("by_client_type") or []:
            self.assertIsInstance(row.get("clients"), int,
                                  "by_client_type must publish a COUNT of clients, never their ids")


if __name__ == "__main__":
    unittest.main()
