"""
Phase 4 — persistent learning (retrieval-augmented).

Closes the loop the earlier JS prototype only pretended to: user corrections are
stored with a **real** vector and retrieved by **real** cosine similarity, then
fed back as few-shot examples (or reused directly for near-duplicate questions).

Embeddings are pluggable:
  * HashingTfEmbedder — stdlib bag-of-words with stable (hashlib) hashing and L2
    normalisation. Deterministic, offline, genuinely discriminative for the
    lexical "have I seen this question before?" job. Used everywhere by default.
  * SentenceTransformerEmbedder — optional semantic upgrade when the
    `sentence-transformers` package is installed on the user's machine.

Storage is SQLite (stdlib) so learning persists across sessions. Everything is
local; nothing is sent anywhere. (Encryption at rest is intentionally left to a
real crypto backend / OS-level disk encryption rather than a home-rolled cipher.)
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence

import sqlite3


# --------------------------------------------------------------------------
# Embedders
# --------------------------------------------------------------------------
def _tokenize(text: str) -> List[str]:
    return [t for t in re.findall(r"[a-z0-9]+", (text or "").lower()) if len(t) > 1]


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


class HashingTfEmbedder:
    """Deterministic bag-of-words embedding with stable hashing + L2 norm."""

    name = "hashing-tf"

    def __init__(self, dim: int = 512):
        self.dim = dim

    def _bucket(self, token: str) -> int:
        h = hashlib.md5(token.encode("utf-8")).hexdigest()
        return int(h, 16) % self.dim

    def embed(self, text: str) -> List[float]:
        vec = [0.0] * self.dim
        for tok in _tokenize(text):
            vec[self._bucket(tok)] += 1.0
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec


class SentenceTransformerEmbedder:
    """Optional semantic embedder (requires sentence-transformers)."""

    name = "sentence-transformers"

    def __init__(self, model: str = "all-MiniLM-L6-v2"):
        from sentence_transformers import SentenceTransformer  # type: ignore
        self._model = SentenceTransformer(model)

    def embed(self, text: str) -> List[float]:
        return [float(x) for x in self._model.encode(text or "")]


def get_embedder(name: str = "auto"):
    """Return an embedder. 'auto' uses sentence-transformers if importable."""
    name = (name or "auto").lower()
    if name in ("hashing", "hashing-tf", "stdlib"):
        return HashingTfEmbedder()
    if name in ("st", "sentence-transformers", "semantic"):
        return SentenceTransformerEmbedder()
    if name == "auto":
        try:
            return SentenceTransformerEmbedder()
        except Exception:
            return HashingTfEmbedder()
    raise ValueError(f"Unknown embedder: {name!r}")


# --------------------------------------------------------------------------
# Store
# --------------------------------------------------------------------------
@dataclass
class Lesson:
    id: int
    ts: float
    domain: str
    question: str
    produced: Optional[str]
    correction: Optional[str]
    rating: Optional[int]
    score: float = 0.0

    @property
    def sql(self) -> Optional[str]:
        """The authoritative SQL to reuse: the correction if present, else produced."""
        return self.correction or self.produced


class LearningStore:
    """Persistent store of question -> (produced, correction) with vectors."""

    def __init__(self, path: str = ":memory:", embedder=None):
        self.path = path
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.embedder = embedder or get_embedder("auto")
        self._init_schema()

    def _init_schema(self) -> None:
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS lessons (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                ts         REAL,
                domain     TEXT,
                question   TEXT NOT NULL,
                produced   TEXT,
                correction TEXT,
                rating     INTEGER,
                vector     TEXT NOT NULL
            )
            """
        )
        self.db.commit()

    def record(self, question: str, produced: Optional[str] = None,
               correction: Optional[str] = None, rating: Optional[int] = None,
               domain: str = "general") -> int:
        vec = json.dumps(self.embedder.embed(question))
        cur = self.db.execute(
            "INSERT INTO lessons (ts, domain, question, produced, correction, rating, vector) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (time.time(), domain, question, produced, correction, rating, vec),
        )
        self.db.commit()
        return cur.lastrowid

    def similar(self, question: str, k: int = 3, domain: Optional[str] = None,
                min_score: float = 0.0) -> List[Lesson]:
        qv = self.embedder.embed(question)
        rows = self.db.execute(
            "SELECT id, ts, domain, question, produced, correction, rating, vector FROM lessons"
            + (" WHERE domain = ?" if domain else ""),
            (domain,) if domain else (),
        ).fetchall()
        scored: List[Lesson] = []
        for r in rows:
            vec = json.loads(r[7])
            score = cosine(qv, vec)
            if score >= min_score:
                scored.append(Lesson(r[0], r[1], r[2], r[3], r[4], r[5], r[6], score))
        scored.sort(key=lambda l: l.score, reverse=True)
        return scored[:k]

    def best_correction(self, question: str, threshold: float = 0.92,
                        domain: Optional[str] = None) -> Optional[Lesson]:
        """Return a prior lesson whose question is near-identical AND that carries
        a correction, so it can be reused directly. None if nothing qualifies."""
        top = self.similar(question, k=1, domain=domain)
        if top and top[0].score >= threshold and top[0].correction:
            return top[0]
        return None

    def examples(self, question: str, k: int = 3, domain: Optional[str] = None,
                 min_score: float = 0.35) -> List[tuple]:
        """Few-shot (question, sql) pairs from the most similar past lessons."""
        out = []
        for l in self.similar(question, k=k, domain=domain, min_score=min_score):
            if l.sql:
                out.append((l.question, l.sql))
        return out

    def stats(self) -> dict:
        n = self.db.execute("SELECT COUNT(*) FROM lessons").fetchone()[0]
        corr = self.db.execute("SELECT COUNT(*) FROM lessons WHERE correction IS NOT NULL").fetchone()[0]
        domains = [r[0] for r in self.db.execute("SELECT DISTINCT domain FROM lessons").fetchall()]
        return {"lessons": n, "corrections": corr, "domains": domains,
                "embedder": self.embedder.name, "path": self.path}

    def clear(self) -> None:
        self.db.execute("DELETE FROM lessons")
        self.db.commit()

    def close(self) -> None:
        try:
            self.db.close()
        except Exception:
            pass
