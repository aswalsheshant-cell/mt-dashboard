"""
ai_analyst — offline-first AI data-analyst agent (Phase 1 skeleton).

Modular design (see BLUEPRINT.md):
  data_layer   — Module 1: load CSV/tabular sources into a SQL engine
                 (DuckDB when installed, stdlib sqlite3 fallback) + expose schema.
  nl2sql       — Module 2: natural-language -> validated, read-only SQL, executed.
  llm_provider — Module 3: swappable LLM backends (offline deterministic stub,
                 local Ollama, opt-in remote) behind one interface.
  agent        — orchestrator wiring the three modules together.
  cli          — thin command-line entry point.

Nothing here sends data off-machine by default: the offline provider is fully
local, and remote providers require an explicit, per-call opt-in.
"""

from ai_analyst.data_layer import DataLayer
from ai_analyst.nl2sql import NL2SQL, SQLValidationError
from ai_analyst.llm_provider import (
    LLMProvider,
    OfflineDeterministicProvider,
    OllamaProvider,
    RemoteOptInProvider,
    get_provider,
)
from ai_analyst.profiler import (
    TableProfile,
    ColumnProfile,
    profile_table,
    profile_report,
    suggest_cleaning,
)
from ai_analyst.documents import (
    Document,
    DocumentError,
    DocumentDependencyError,
    read_document,
    summarize_text,
    text_stats,
)
from ai_analyst.learning import (
    LearningStore,
    Lesson,
    HashingTfEmbedder,
    get_embedder,
    cosine,
)
from ai_analyst.agent import Analyst

__all__ = [
    "LearningStore",
    "Lesson",
    "HashingTfEmbedder",
    "get_embedder",
    "cosine",
    "DataLayer",
    "NL2SQL",
    "SQLValidationError",
    "LLMProvider",
    "OfflineDeterministicProvider",
    "OllamaProvider",
    "RemoteOptInProvider",
    "get_provider",
    "TableProfile",
    "ColumnProfile",
    "profile_table",
    "profile_report",
    "suggest_cleaning",
    "Document",
    "DocumentError",
    "DocumentDependencyError",
    "read_document",
    "summarize_text",
    "text_stats",
    "Analyst",
]

__version__ = "0.1.0"
