"""The knowledge base must stay sourced, routed, fresh and free of project secrets.

An article that has silently gone stale, lost its sources, or acquired a real
employee ID is worse than no article -- it will be trusted.
"""
import datetime
import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
KB = REPO / "docs" / "knowledge"
REQUIRED = ["Topic_ID", "Purpose", "Applicable_Agents", "Trigger_Conditions",
            "Access_Date", "Last_Reviewed", "Review_By", "Confidence"]


def articles():
    return sorted(p for p in KB.glob("KA-*.md"))


class TestKnowledgeBase(unittest.TestCase):
    def test_articles_exist(self):
        self.assertGreaterEqual(len(articles()), 10, "expected KA-01..KA-10")

    def test_required_metadata_present(self):
        for p in articles():
            t = p.read_text(encoding="utf-8")
            for field in REQUIRED:
                self.assertIn(field, t, f"{p.name} is missing {field}")

    def test_every_article_cites_a_source(self):
        for p in articles():
            t = p.read_text(encoding="utf-8")
            body = t.split("## Authoritative sources", 1)
            self.assertEqual(len(body), 2, f"{p.name} has no sources section")
            cited = [ln for ln in body[1].split("##")[0].splitlines() if ln.strip().startswith("- ")]
            self.assertTrue(cited, f"{p.name} cites no source")

    def test_not_stale(self):
        today = datetime.date.today()
        for p in articles():
            m = re.search(r"\|\s*Review_By\s*\|\s*(\d{4}-\d{2}-\d{2})\s*\|", p.read_text(encoding="utf-8"))
            self.assertIsNotNone(m, f"{p.name} has no parsable Review_By")
            due = datetime.date.fromisoformat(m.group(1))
            self.assertGreaterEqual(
                due, today,
                f"{p.name} is past its review date ({due}) — revalidate before relying on it.")

    def test_router_covers_every_article(self):
        idx = (KB / "INDEX.md").read_text(encoding="utf-8")
        for p in articles():
            tid = p.name.split("-")[0] + "-" + p.name.split("-")[1]
            self.assertIn(tid, idx, f"{tid} is not listed in INDEX.md")

    def test_no_project_secrets(self):
        """Methodology only. A real employee ID here would leak into every agent."""
        for p in list(articles()) + [KB / "INDEX.md"]:
            t = p.read_text(encoding="utf-8")
            self.assertFalse(re.findall(r"HCPL\d{3,}", t), f"{p.name} contains an employee ID")
            self.assertFalse(re.findall(r"\bGS1\d{7,}\b", t), f"{p.name} contains a DMS owner code")

    def test_internal_beats_external_rule_is_stated(self):
        idx = (KB / "INDEX.md").read_text(encoding="utf-8")
        self.assertIn("INTERNAL_BUSINESS_CONFIRMATION_REQUIRED", idx)


if __name__ == "__main__":
    unittest.main()
