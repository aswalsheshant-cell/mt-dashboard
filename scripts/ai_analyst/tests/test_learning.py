"""Phase 4 tests — persistent learning: real embeddings, retrieval, reuse."""

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ai_analyst.learning import HashingTfEmbedder, LearningStore, cosine
from ai_analyst.agent import Analyst


class TestEmbedder(unittest.TestCase):
    def setUp(self):
        self.e = HashingTfEmbedder()

    def test_deterministic(self):
        self.assertEqual(self.e.embed("total revenue by region"),
                         self.e.embed("total revenue by region"))

    def test_self_similarity_is_one(self):
        v = self.e.embed("offtake by chain")
        self.assertAlmostEqual(cosine(v, v), 1.0, places=6)

    def test_similar_beats_dissimilar(self):
        base = self.e.embed("total revenue by region")
        near = self.e.embed("revenue total per region")
        far = self.e.embed("list distinct brand names")
        self.assertGreater(cosine(base, near), cosine(base, far))

    def test_empty_vector_similarity(self):
        self.assertEqual(cosine(self.e.embed(""), self.e.embed("anything")), 0.0)


class TestStore(unittest.TestCase):
    def setUp(self):
        self.s = LearningStore(":memory:", embedder=HashingTfEmbedder())

    def tearDown(self):
        self.s.close()

    def test_record_and_retrieve(self):
        self.s.record("total revenue by region", correction='SELECT "region" FROM "t"')
        top = self.s.similar("revenue by region total", k=1)
        self.assertEqual(len(top), 1)
        self.assertGreater(top[0].score, 0.5)

    def test_best_correction_threshold(self):
        self.s.record("count of articles by category",
                      correction='SELECT "category", COUNT(*) FROM "a" GROUP BY "category"')
        # near-identical question -> reuse
        best = self.s.best_correction("count of articles by category")
        self.assertIsNotNone(best)
        # unrelated question -> no reuse
        self.assertIsNone(self.s.best_correction("distinct brand names"))

    def test_stats(self):
        self.s.record("q1", produced="SELECT 1")
        self.s.record("q2", correction="SELECT 2")
        st = self.s.stats()
        self.assertEqual(st["lessons"], 2)
        self.assertEqual(st["corrections"], 1)

    def test_persists_to_disk(self):
        with tempfile.TemporaryDirectory() as d:
            path = str(Path(d) / "learn.db")
            s1 = LearningStore(path, embedder=HashingTfEmbedder())
            s1.record("revenue by region", correction="SELECT 1")
            s1.close()
            s2 = LearningStore(path, embedder=HashingTfEmbedder())
            self.assertEqual(s2.stats()["lessons"], 1)
            self.assertIsNotNone(s2.best_correction("revenue by region"))
            s2.close()


class TestLearningEndToEnd(unittest.TestCase):
    """Teach a correction, then a near-duplicate question reuses it and runs."""

    def setUp(self):
        self.a = Analyst(provider="offline", engine="sqlite", learning=True)
        self.a.data.register_rows(
            "sales", ["region", "revenue"],
            [["North", "100"], ["North", "50"], ["South", "30"]],
        )

    def tearDown(self):
        self.a.close()

    def test_taught_sql_is_reused_and_executes(self):
        good_sql = 'SELECT "region", SUM(CAST("revenue" AS REAL)) AS total FROM "sales" GROUP BY "region"'
        self.a.learn("total revenue by region", good_sql, rating=5, domain="sales")

        res = self.a.ask("total revenue by region", domain="sales")
        self.assertTrue(res.ok, res.error)
        self.assertEqual(res.provider, "learned")      # came from the learning store
        self.assertEqual(res.sql, good_sql)            # exact reuse
        # and it actually runs on the data
        totals = {r[0]: r[1] for r in res.rows}
        self.assertEqual(totals["North"], 150.0)

    def test_unrelated_question_not_reused(self):
        self.a.learn("total revenue by region",
                     'SELECT "region" FROM "sales"', domain="sales")
        res = self.a.ask("how many rows in sales", domain="sales")
        self.assertNotEqual(res.provider, "learned")   # deterministic translation instead

    def test_learn_requires_enabled(self):
        a2 = Analyst(provider="offline", engine="sqlite", learning=False)
        with self.assertRaises(RuntimeError):
            a2.learn("q", "SELECT 1")
        a2.close()


if __name__ == "__main__":
    unittest.main()
