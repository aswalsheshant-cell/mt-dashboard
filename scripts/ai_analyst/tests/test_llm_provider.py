"""Module 3 tests — provider abstraction works with no model installed."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ai_analyst.llm_provider import (
    OfflineDeterministicProvider,
    OllamaProvider,
    RemoteOptInProvider,
    LLMProvider,
    get_provider,
    extract_sql,
    build_sql_prompt,
)

SCHEMA = {
    "articles": ["article_code", "brand", "category", "sub_category", "range", "pack_size"],
    "zones": ["zone", "state", "region"],
}


class TestExtractSQL(unittest.TestCase):
    def test_strips_fences_and_prose(self):
        raw = "Here you go:\n```sql\nSELECT * FROM articles;\n```"
        self.assertEqual(extract_sql(raw), "SELECT * FROM articles")

    def test_keeps_from_select(self):
        self.assertEqual(extract_sql("SELECT 1"), "SELECT 1")


class TestOfflineProvider(unittest.TestCase):
    def setUp(self):
        self.p = OfflineDeterministicProvider()

    def test_count(self):
        sql = self.p.translate_to_sql("how many articles", SCHEMA).lower()
        self.assertIn("count(*)", sql)
        self.assertIn("articles", sql)

    def test_group_by_resolves_real_column(self):
        sql = self.p.translate_to_sql("articles by category", SCHEMA).lower()
        self.assertIn("group by", sql)
        self.assertIn("category", sql)

    def test_distinct(self):
        sql = self.p.translate_to_sql("distinct brand", SCHEMA).lower()
        self.assertIn("distinct", sql)
        self.assertIn("brand", sql)

    def test_only_real_tables(self):
        # a question mentioning zones must target the zones table, never invent one
        sql = self.p.translate_to_sql("how many zones", SCHEMA).lower()
        self.assertIn("zones", sql)

    def test_default_preview(self):
        sql = self.p.translate_to_sql("tell me about articles", SCHEMA).lower()
        self.assertIn("select", sql)
        self.assertIn("limit", sql)


class TestPromptBuilder(unittest.TestCase):
    def test_prompt_lists_tables(self):
        prompt = build_sql_prompt("x", SCHEMA)
        self.assertIn("articles", prompt)
        self.assertIn("zones", prompt)


class _FakeTextModel(LLMProvider):
    """A stand-in text model to prove prompt-based providers work end-to-end."""
    name = "fake"

    def complete(self, prompt, system=None):
        return "```sql\nSELECT brand FROM articles\n```"


class TestPromptRoundTrip(unittest.TestCase):
    def test_text_model_translate(self):
        sql = _FakeTextModel().translate_to_sql("brands?", SCHEMA)
        self.assertEqual(sql, "SELECT brand FROM articles")


class TestOllamaAndRemote(unittest.TestCase):
    def test_ollama_instantiates_and_reports_unavailable(self):
        # No server here — is_available must return False, not raise.
        p = OllamaProvider(endpoint="http://localhost:9")
        self.assertFalse(p.is_available())

    def test_remote_gated(self):
        p = RemoteOptInProvider()
        self.assertFalse(p.is_available())
        with self.assertRaises(PermissionError):
            p.complete("hi")


class TestFactory(unittest.TestCase):
    def test_offline(self):
        self.assertIsInstance(get_provider("offline"), OfflineDeterministicProvider)

    def test_auto_falls_back_offline_when_no_ollama(self):
        # auto should not raise even with no local model; may return offline.
        p = get_provider("auto", endpoint="http://localhost:9")
        self.assertIsInstance(p, OfflineDeterministicProvider)


if __name__ == "__main__":
    unittest.main()
