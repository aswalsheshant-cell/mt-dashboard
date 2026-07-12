"""Ask pipeline: retrieve from the local index, answer with local Ollama.

Fully offline. If Ollama is down the command still works — it returns the
retrieved passages verbatim so the analyst can read the sources directly.
"""
from __future__ import annotations

from pathlib import Path

from .config import Config
from .ingest import build_corpus
from .llm import Ollama, OllamaUnavailable
from .vectorstore import VectorIndex

SYSTEM_PROMPT = """\
You are the offline analytics assistant for the Honasa/Mamaearth Modern Trade
(MT) leadership dashboard repo. Answer ONLY from the provided context
passages; if the context does not contain the answer, say so plainly.

Domain rules you must never contradict:
- Indian financial year (Apr-Mar). THE ONE FY RULE: Apr-Dec of calendar year
  Y belongs to FY(Y+1); Jan-Mar of year Y belongs to FY(Y). FY is always
  derived from month+year, never from a fixed column position.
- Monetary values in sources are INR Lakh; the dashboard shows INR Crore
  (Lakh / 100) where magnitude warrants.
- "NSV" headline = Offtake NSV unless stated otherwise.

Cite the source path of each passage you rely on, e.g. (PowerBI/docs/DataModel.md).
Be concise and concrete."""


def ensure_index(cfg: Config, rebuild: bool = False) -> tuple[VectorIndex, list[str]]:
    path = cfg.path(cfg.index_path)
    notices: list[str] = []
    if path.exists() and not rebuild:
        return VectorIndex.load(path), notices
    chunks, notices = build_corpus(cfg)
    idx = VectorIndex.build(cfg, chunks)
    idx.save(path)
    notices.append(f"indexed {len(chunks)} chunks with '{idx.embedder}' -> {path}")
    return idx, notices


def ask(cfg: Config, question: str, k: int | None = None) -> dict:
    """Returns {'answer': str|None, 'passages': [...], 'notices': [...]}."""
    idx, notices = ensure_index(cfg)
    passages = idx.search(cfg, question, k)
    context = "\n\n---\n\n".join(
        f"[{p['source']} :: {p['section']}]\n{p['text']}" for p in passages)
    user = f"Context passages:\n\n{context}\n\nQuestion: {question}"
    client = Ollama(cfg)
    answer = None
    try:
        answer = client.chat(SYSTEM_PROMPT, user)
    except OllamaUnavailable as e:
        notices.append(f"{e} — showing retrieved passages only "
                       f"(start Ollama and pull '{cfg.chat_model}' for answers)")
    return {"answer": answer, "passages": passages, "notices": notices}
