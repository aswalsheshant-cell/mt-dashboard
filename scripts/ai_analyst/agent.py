"""
Orchestrator — wires Module 1 (data), Module 2 (nl2sql) and Module 3 (provider).

Usage:
    from ai_analyst import Analyst
    a = Analyst(provider="auto")             # local model if present, else offline
    a.load_dir("PowerBI/SeedData/Masters")   # real files
    print(a.schema())
    res = a.ask("how many articles by category")
    print(res.sql, res.rows)
"""

from __future__ import annotations

from typing import Dict, List, Optional

from ai_analyst.data_layer import DataLayer
from ai_analyst.llm_provider import LLMProvider, get_provider
from ai_analyst.nl2sql import NL2SQL, QueryResult
from ai_analyst.profiler import TableProfile, profile_table, profile_report, suggest_cleaning
from ai_analyst.documents import Document, read_document, summarize_text, text_stats


class Analyst:
    def __init__(self, provider="auto", engine: str = "auto", row_limit: int = 1000,
                 provider_kwargs: Optional[dict] = None):
        self.data = DataLayer(engine=engine)
        if isinstance(provider, LLMProvider):
            self.provider = provider
        else:
            self.provider = get_provider(provider, **(provider_kwargs or {}))
        self.nl2sql = NL2SQL(self.data, self.provider, row_limit=row_limit)

    # -- data --------------------------------------------------------------
    def load_csv(self, path, table: Optional[str] = None, max_rows: Optional[int] = None):
        return self.data.load_csv(path, table=table, max_rows=max_rows)

    def load_dir(self, directory, pattern: str = "*.csv", max_rows: Optional[int] = None):
        return self.data.load_dir(directory, pattern=pattern, max_rows=max_rows)

    def schema(self) -> Dict[str, List[str]]:
        return self.data.schema()

    # -- ask ---------------------------------------------------------------
    def to_sql(self, question: str) -> str:
        return self.nl2sql.to_sql(question)

    def ask(self, question: str, execute: bool = True) -> QueryResult:
        return self.nl2sql.query(question, execute=execute)

    # -- profiling / EDA (Phase 3) ----------------------------------------
    def profile(self, table: Optional[str] = None, sample: int = 5000) -> TableProfile:
        if table is None:
            tables = self.data.tables()
            if not tables:
                raise ValueError("No tables loaded to profile.")
            table = tables[0]
        return profile_table(self.data, table, sample=sample)

    def cleaning_suggestions(self, table: Optional[str] = None) -> list:
        return suggest_cleaning(self.profile(table))

    def profile_text(self, table: Optional[str] = None) -> str:
        return profile_report(self.profile(table))

    # -- documents (Phase 3) ----------------------------------------------
    def read_document(self, path) -> Document:
        return read_document(path)

    def summarize_document(self, path, max_sentences: int = 5) -> dict:
        doc = read_document(path)
        return {
            "path": doc.path,
            "kind": doc.kind,
            "n_pages": doc.n_pages,
            "stats": text_stats(doc.text),
            "summary": summarize_text(doc.text, max_sentences=max_sentences, provider=self.provider),
        }

    def close(self):
        self.data.close()
