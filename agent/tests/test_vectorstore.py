import json
import tempfile
import unittest
from pathlib import Path

from mtagent.config import Config
from mtagent.ingest import Chunk, _window, build_corpus, split_markdown
from mtagent.vectorstore import VectorIndex, compute_idf, hash_embed, tokenize

REPO = Path(__file__).resolve().parents[2]


def _cfg() -> Config:
    return Config(repo_root=str(REPO))


class TestWindow(unittest.TestCase):
    def test_short_text_single_window(self):
        self.assertEqual(_window("hello", 100, 10), ["hello"])

    def test_no_tail_crawl(self):
        # regression: the final short remainder must not loop 1 char at a time
        text = ("line of code\n" * 400)   # ~5KB
        w = _window(text, 1400, 200)
        self.assertLess(len(w), 10)

    def test_windows_cover_text(self):
        text = "\n".join(f"row {i}" for i in range(500))
        w = _window(text, 1000, 100)
        self.assertIn("row 0", w[0])
        self.assertIn("row 499", w[-1])


class TestSplitters(unittest.TestCase):
    def test_markdown_heading_sections(self):
        md = "# Title\nintro text\n## Section A\naaa\n## Section B\nbbb\n"
        chunks = split_markdown(md, "x.md", 1000, 100)
        sections = [c.section for c in chunks]
        self.assertIn("Title", sections)
        self.assertIn("Section A", sections)


class TestHashEmbedder(unittest.TestCase):
    def test_deterministic_and_normalized(self):
        idf = {"offtake": 2.0, "nsv": 1.5}
        a = hash_embed("offtake NSV by chain", idf)
        b = hash_embed("offtake NSV by chain", idf)
        self.assertEqual(a, b)
        self.assertAlmostEqual(sum(v * v for v in a), 1.0, places=6)

    def test_similar_texts_score_higher(self):
        chunks = [Chunk("a", "s", "offtake NSV sell-out by chain and zone"),
                  Chunk("b", "s", "promo calendar trade spend events"),
                  Chunk("c", "s", "chain offtake monthly NSV trend")]
        idf = compute_idf(chunks)
        q = hash_embed("chain offtake NSV", idf)
        scores = {c.source: sum(x * y for x, y in
                                zip(q, hash_embed(c.text, idf)))
                  for c in chunks}
        self.assertGreater(scores["a"], scores["b"])
        self.assertGreater(scores["c"], scores["b"])

    def test_tokenize_drops_stopwords(self):
        self.assertNotIn("the", tokenize("the offtake of the chain"))
        self.assertIn("offtake", tokenize("the offtake of the chain"))


class TestIndexRoundtrip(unittest.TestCase):
    def test_build_save_load_search(self):
        cfg = _cfg()
        chunks = [Chunk("doc1.md", "fy", "FY is derived from month plus year, Apr to Mar"),
                  Chunk("doc2.md", "promo", "promo events and trade spend calendar"),
                  Chunk("doc3.md", "dist", "store universe distribution footprint")]
        idx = VectorIndex.build(cfg, chunks, prefer_ollama=False)
        self.assertEqual(idx.embedder, "hash")
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "index.json"
            idx.save(p)
            idx2 = VectorIndex.load(p)
        hits = idx2.search(cfg, "how is FY derived from month and year", k=1)
        self.assertEqual(hits[0]["source"], "doc1.md")


class TestCorpus(unittest.TestCase):
    def test_repo_corpus_reasonable(self):
        chunks, _ = build_corpus(_cfg())
        self.assertGreater(len(chunks), 100)
        self.assertLess(len(chunks), 3000)   # regression: no chunk explosion
        sources = {c.source for c in chunks}
        self.assertIn("CLAUDE.md", sources)
        self.assertTrue(any(s.startswith("PowerBI/DAX/") for s in sources))
        self.assertTrue(any(s.startswith("PowerBI/PowerQuery/") for s in sources))
        self.assertTrue(any(s.endswith(".csv") for s in sources))


class TestGoldenRetrieval(unittest.TestCase):
    """The same golden set the `eval` command uses, as a unit test, so plain
    `unittest` runs enforce the retrieval bar with the stdlib embedder."""

    def test_hit_at_3_bar(self):
        cfg = _cfg()
        chunks, _ = build_corpus(cfg)
        idx = VectorIndex.build(cfg, chunks, prefer_ollama=False)
        cases = [json.loads(l) for l in
                 (REPO / "agent" / "evals" / "golden_qa.jsonl")
                 .read_text().splitlines() if l.strip()]
        hits = 0
        misses = []
        for case in cases:
            got = idx.search(cfg, case["q"], 3)
            ok = any(exp in p["source"] for exp in case["expect_any"] for p in got)
            hits += ok
            if not ok:
                misses.append((case["q"], [p["source"] for p in got]))
        self.assertGreaterEqual(hits / len(cases), 0.70, misses)


if __name__ == "__main__":
    unittest.main()
