"""Ask pipeline: retrieve from the local index, answer with local Ollama.

Fully offline. If Ollama is down the command still works — it returns the
retrieved passages verbatim so the analyst can read the sources directly.
"""
from __future__ import annotations

from pathlib import Path

from .config import Config
from .ingest import build_corpus
from .llm import Ollama, OllamaUnavailable
from .persona import system_prompt
from .vectorstore import VectorIndex


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


def ask(cfg: Config, question: str, k: int | None = None,
        mode: str = "ask", extra_context: str | None = None) -> dict:
    """Returns {'answer': str|None, 'passages': [...], 'notices': [...]}.
    mode='meeting' retrieves fewer passages and forces the terse
    leadership-meeting answer shape; mode='drilldown' lifts the brevity
    limit and expects computed tables in extra_context (see persona)."""
    idx, notices = ensure_index(cfg)
    if mode == "meeting" and k is None:
        k = min(cfg.top_k, 4)   # smaller context -> faster local answer
    passages = idx.search(cfg, question, k)
    context = "\n\n---\n\n".join(
        f"[{p['source']} :: {p['section']}]\n{p['text']}" for p in passages)
    if extra_context:
        context = extra_context + "\n\n---\n\n" + context
    user = f"Context passages:\n\n{context}\n\nQuestion: {question}"
    client = Ollama(cfg)
    answer = None
    try:
        answer = client.chat(system_prompt(mode), user)
    except OllamaUnavailable as e:
        notices.append(f"{e} — showing retrieved passages only "
                       f"(start Ollama and pull '{cfg.chat_model}' for answers)")
    return {"answer": answer, "passages": passages, "notices": notices}
