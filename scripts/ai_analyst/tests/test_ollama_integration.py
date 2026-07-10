"""Live LLM integration test.

Automatically SKIPPED when no Ollama server is reachable, so it is a no-op in
CI / air-gapped envs. On a machine running `ollama serve`, it exercises the
real end-to-end path: local model -> SQL -> validate -> execute on a table.

Run on your machine:
    ollama pull mistral && ollama serve
    python scripts/ai_analyst/run_tests.py
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ai_analyst.agent import Analyst
from ai_analyst.llm_provider import OllamaProvider

_OLLAMA_UP = OllamaProvider().is_available()


@unittest.skipUnless(_OLLAMA_UP, "no local Ollama server reachable at localhost:11434")
class TestOllamaLive(unittest.TestCase):
    def setUp(self):
        self.a = Analyst(provider="ollama", engine="sqlite")
        self.a.data.register_rows(
            "sales",
            ["region", "product", "units", "revenue"],
            [["North", "A", "10", "100"], ["North", "B", "5", "50"], ["South", "A", "3", "30"]],
        )

    def tearDown(self):
        self.a.close()

    def test_live_count(self):
        res = self.a.ask("how many rows are in sales")
        self.assertTrue(res.ok, f"live model produced unusable SQL: {res.sql} / {res.error}")
        # model-authored SQL should still be a read-only SELECT that runs
        self.assertTrue(res.sql.lower().startswith("select"))

    def test_live_group_by(self):
        res = self.a.ask("total revenue by region")
        self.assertTrue(res.ok, f"error: {res.error} / sql: {res.sql}")
        self.assertGreaterEqual(len(res.rows), 1)


if __name__ == "__main__":
    unittest.main()
