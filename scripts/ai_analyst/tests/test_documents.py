"""Phase 3 tests — document ingest & offline summarisation."""

import importlib
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ai_analyst.documents import (
    read_document,
    summarize_text,
    text_stats,
    split_sentences,
    DocumentError,
    DocumentDependencyError,
    _read_pdf,
)

PARAGRAPH = (
    "Modern trade offtake grew strongly in the quarter. "
    "Offtake growth was led by face wash and sunscreen. "
    "Distribution expanded across northern chains. "
    "The weather was pleasant on the day of the review. "
    "Offtake momentum is expected to continue next quarter."
)


class TestTextStats(unittest.TestCase):
    def test_counts(self):
        s = text_stats(PARAGRAPH)
        self.assertEqual(s["sentences"], 5)
        self.assertGreater(s["words"], 20)
        self.assertGreater(s["unique_words"], 10)

    def test_split_sentences(self):
        self.assertEqual(len(split_sentences(PARAGRAPH)), 5)


class TestSummarize(unittest.TestCase):
    def test_respects_max_and_is_deterministic(self):
        a = summarize_text(PARAGRAPH, max_sentences=2)
        b = summarize_text(PARAGRAPH, max_sentences=2)
        self.assertEqual(a, b)  # deterministic
        self.assertLessEqual(len(split_sentences(a)), 2)
        self.assertTrue(a)

    def test_prefers_salient_sentence(self):
        # "offtake" is the most frequent salient term; summary should feature it
        summary = summarize_text(PARAGRAPH, max_sentences=2).lower()
        self.assertIn("offtake", summary)

    def test_short_text_returned_whole(self):
        txt = "Only one sentence here."
        self.assertEqual(summarize_text(txt, max_sentences=5), txt)

    def test_empty(self):
        self.assertEqual(summarize_text("", max_sentences=3), "")


class TestReadDocument(unittest.TestCase):
    def test_read_text_file(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "note.txt"
            p.write_text(PARAGRAPH, encoding="utf-8")
            doc = read_document(p)
            self.assertEqual(doc.kind, "text")
            self.assertIn("offtake", doc.text.lower())

    def test_read_markdown(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "r.md"
            p.write_text("# Title\n\nSome content.", encoding="utf-8")
            self.assertEqual(read_document(p).kind, "text")

    def test_missing_file(self):
        with self.assertRaises(DocumentError):
            read_document("/nonexistent/does_not_exist.txt")

    def test_unsupported_extension(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "x.docx"
            p.write_bytes(b"stub")
            with self.assertRaises(DocumentError):
                read_document(p)


class TestPdfBackend(unittest.TestCase):
    def _has_pdf_backend(self):
        for mod in ("pdfplumber", "pypdf", "fitz"):
            try:
                importlib.import_module(mod)
                return True
            except ImportError:
                continue
        return False

    def test_pdf_without_backend_raises_clear_error(self):
        if self._has_pdf_backend():
            self.skipTest("a PDF backend is installed; dependency path not exercised")
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "doc.pdf"
            p.write_bytes(b"%PDF-1.4 stub")
            with self.assertRaises(DocumentDependencyError):
                _read_pdf(p)


if __name__ == "__main__":
    unittest.main()
