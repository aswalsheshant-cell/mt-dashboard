"""mtagent — local, offline analytics agent for the Honasa/Mamaearth MT repo.

Runs entirely on the analyst's machine: Ollama for the LLM, DuckDB for SQL,
a JSON-file vector index for retrieval, and pure-Python validators for the
Power BI build kit (DAX + Power Query). Every heavy dependency is optional —
the core (validators, retrieval fallback, FY rules, CLI) is stdlib-only.
"""

__version__ = "0.1.0"
