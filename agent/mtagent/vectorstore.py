"""Local vector database — a single JSON file, no server, no network.

Two embedding backends:
  * Ollama embeddings (cfg.embed_model, e.g. nomic-embed-text) when the
    daemon is up — best quality.
  * Hashed TF-IDF (stdlib only, deterministic) as the always-available
    fallback, blended with a keyword-overlap score so retrieval stays
    useful with zero dependencies.

The index records which backend built it; queries must use the same one, so
`search` transparently falls back to keyword scoring if the index was built
with Ollama but the daemon is now down.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path

from .config import Config
from .ingest import Chunk
from .llm import Ollama, OllamaUnavailable

HASH_DIM = 512
_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9_%&'-]*")

_STOP = {"the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "is",
         "are", "be", "it", "this", "that", "with", "as", "by", "at", "from",
         "we", "was", "were", "not", "no", "if", "then", "else", "each", "let"}


def tokenize(text: str) -> list[str]:
    return [t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOP]


def _hash_slot(token: str) -> tuple[int, float]:
    h = int.from_bytes(hashlib.md5(token.encode()).digest()[:8], "big")
    return h % HASH_DIM, 1.0 if (h >> 63) & 1 else -1.0


def hash_embed(text: str, idf: dict) -> list[float]:
    vec = [0.0] * HASH_DIM
    toks = tokenize(text)
    if not toks:
        return vec
    tf: dict[str, int] = {}
    for t in toks:
        tf[t] = tf.get(t, 0) + 1
    for t, c in tf.items():
        slot, sign = _hash_slot(t)
        vec[slot] += sign * (1 + math.log(c)) * idf.get(t, 1.0)
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def compute_idf(chunks: list[Chunk]) -> dict:
    df: dict[str, int] = {}
    for c in chunks:
        for t in set(tokenize(c.text)):
            df[t] = df.get(t, 0) + 1
    n = max(len(chunks), 1)
    return {t: math.log(1 + n / d) for t, d in df.items()}


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))   # vectors stored normalized


def _normalize(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def keyword_score(query_tokens: set, text: str) -> float:
    if not query_tokens:
        return 0.0
    toks = set(tokenize(text))
    return len(query_tokens & toks) / len(query_tokens)


class VectorIndex:
    def __init__(self, embedder: str, idf: dict, entries: list[dict]):
        self.embedder = embedder      # "hash" | "ollama:<model>"
        self.idf = idf
        self.entries = entries        # {source, section, text, vec}

    # ---------------- build ----------------
    @classmethod
    def build(cls, cfg: Config, chunks: list[Chunk],
              prefer_ollama: bool = True) -> "VectorIndex":
        idf = compute_idf(chunks)
        entries = [{"source": c.source, "section": c.section, "text": c.text}
                   for c in chunks]
        embedder = "hash"
        if prefer_ollama:
            client = Ollama(cfg)
            if client.available():
                try:
                    vecs = []
                    B = 32
                    for i in range(0, len(chunks), B):
                        vecs += client.embed([c.text for c in chunks[i:i + B]])
                    for e, v in zip(entries, vecs):
                        e["vec"] = _normalize(v)
                    embedder = f"ollama:{cfg.embed_model}"
                except OllamaUnavailable:
                    pass
        if embedder == "hash":
            for e in entries:
                e["vec"] = hash_embed(e["text"], idf)
        return cls(embedder, idf, entries)

    # ---------------- persistence ----------------
    def save(self, path: Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({
            "version": 1, "embedder": self.embedder, "dim":
                len(self.entries[0]["vec"]) if self.entries else 0,
            "idf": self.idf, "entries": self.entries,
        }), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "VectorIndex":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(data["embedder"], data.get("idf", {}), data["entries"])

    # ---------------- search ----------------
    def search(self, cfg: Config, query: str, k: int | None = None) -> list[dict]:
        k = k or cfg.top_k
        qtok = set(tokenize(query))
        qvec = None
        if self.embedder.startswith("ollama:"):
            client = Ollama(cfg)
            try:
                qvec = _normalize(client.embed(
                    [query], model=self.embedder.split(":", 1)[1])[0])
            except OllamaUnavailable:
                qvec = None    # daemon gone — fall back to keyword-only
        else:
            qvec = hash_embed(query, self.idf)
        scored = []
        for e in self.entries:
            s = (cosine(qvec, e["vec"]) if qvec else 0.0) \
                + 0.3 * keyword_score(qtok, e["text"]) \
                + 0.1 * keyword_score(qtok, f"{e['source']} {e['section']}")
            scored.append((s, e))
        scored.sort(key=lambda t: -t[0])
        return [{"score": round(s, 4), "source": e["source"],
                 "section": e["section"], "text": e["text"]}
                for s, e in scored[:k]]
