"""
Module 2 — Natural language -> validated, read-only SQL -> results.

Flow:
  question --(provider.translate_to_sql)--> SQL --(validate)--> (run on engine)

The validation step is the sandbox: only a single read-only SELECT/WITH
statement is allowed through. Any attempt at DDL/DML (DROP, DELETE, UPDATE,
INSERT, ALTER, CREATE, ATTACH, PRAGMA, ...) or statement stacking is rejected
before it reaches the database. This holds regardless of which provider
produced the SQL, so a hallucinating model cannot mutate data.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from ai_analyst.data_layer import DataLayer
from ai_analyst.llm_provider import LLMProvider


class SQLValidationError(Exception):
    """Raised when generated SQL is not a safe, single, read-only statement."""


# keywords that must never appear as standalone statements/tokens
_FORBIDDEN = {
    "insert", "update", "delete", "drop", "alter", "create", "replace",
    "truncate", "attach", "detach", "pragma", "vacuum", "reindex", "grant",
    "revoke", "copy", "install", "load", "export", "import",
}
_TOKEN = re.compile(r"[a-zA-Z_]+")


def validate_sql(sql: str) -> str:
    """Return a cleaned SQL string or raise SQLValidationError."""
    if sql is None:
        raise SQLValidationError("No SQL produced.")
    cleaned = sql.strip().rstrip(";").strip()
    if not cleaned:
        raise SQLValidationError("Empty SQL.")
    # reject statement stacking (a stray ';' means a second statement)
    if ";" in cleaned:
        raise SQLValidationError("Multiple statements are not allowed.")
    lowered = cleaned.lower()
    if not (lowered.startswith("select") or lowered.startswith("with")):
        raise SQLValidationError("Only read-only SELECT/WITH queries are allowed.")
    tokens = set(_TOKEN.findall(lowered))
    bad = tokens & _FORBIDDEN
    if bad:
        raise SQLValidationError(f"Disallowed keyword(s): {', '.join(sorted(bad))}")
    return cleaned


@dataclass
class QueryResult:
    question: str
    sql: str
    columns: List[str] = field(default_factory=list)
    rows: List[Tuple] = field(default_factory=list)
    provider: str = ""
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.error is None

    def to_dict(self) -> dict:
        return {
            "question": self.question,
            "sql": self.sql,
            "columns": self.columns,
            "rows": [list(r) for r in self.rows],
            "provider": self.provider,
            "error": self.error,
        }


class NL2SQL:
    """Translate questions to SQL and (optionally) execute them read-only."""

    def __init__(self, data: DataLayer, provider: LLMProvider, row_limit: int = 1000):
        self.data = data
        self.provider = provider
        self.row_limit = row_limit

    def to_sql(self, question: str) -> str:
        """Question -> validated SQL string (no execution)."""
        raw = self.provider.translate_to_sql(question, self.data.schema())
        return validate_sql(raw)

    def query(self, question: str, execute: bool = True) -> QueryResult:
        """Full pipeline: translate, validate, and (by default) run."""
        result = QueryResult(question=question, sql="", provider=self.provider.name)
        try:
            result.sql = self.to_sql(question)
        except Exception as exc:  # translation or validation failure
            result.error = f"{type(exc).__name__}: {exc}"
            return result
        if not execute:
            return result
        try:
            sql = result.sql
            # apply a defensive row cap if the query has no explicit LIMIT
            if " limit " not in sql.lower():
                sql = f"{sql} LIMIT {self.row_limit}"
            cols, rows = self.data.run_sql(sql)
            result.columns, result.rows = cols, rows
        except Exception as exc:
            result.error = f"Execution failed: {type(exc).__name__}: {exc}"
        return result
