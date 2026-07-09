"""
Module 1 — Data loading & SQL-engine setup.

Loads tabular sources (CSV today; window.DASH arrays and Parquet later) into an
in-memory SQL engine and exposes a uniform schema + query API. The engine is
pluggable:

  * DuckDB  — used automatically when the `duckdb` package is importable
              (fast analytical SQL, Parquet/Arrow support). Preferred on a
              real analyst machine.
  * sqlite3 — Python standard library fallback, always available offline and
              with zero install. Used in locked-down / air-gapped environments
              and for the test suite.

Both engines share one code path: CSVs are parsed in Python (so column
sanitisation and typing behave identically regardless of engine), values are
stored as text (mirroring DuckDB's `all_varchar` mode — robust for messy
source files), and numeric work is done with explicit CASTs in the generated
SQL. Only the DB-API `connect()` call differs between engines.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple


# --------------------------------------------------------------------------
# Engine selection
# --------------------------------------------------------------------------
def _select_engine(engine: str = "auto") -> str:
    """Return the concrete engine name: 'duckdb' or 'sqlite'."""
    engine = (engine or "auto").lower()
    if engine in ("sqlite", "sqlite3"):
        return "sqlite"
    if engine == "duckdb":
        return "duckdb"
    if engine == "auto":
        try:
            import duckdb  # noqa: F401
            return "duckdb"
        except Exception:
            return "sqlite"
    raise ValueError(f"Unknown engine: {engine!r}")


def _connect(engine: str):
    """Open an in-memory connection for the chosen engine (DB-API 2.0-ish)."""
    if engine == "duckdb":
        import duckdb
        return duckdb.connect(database=":memory:")
    import sqlite3
    con = sqlite3.connect(":memory:")
    return con


# --------------------------------------------------------------------------
# Identifier sanitisation
# --------------------------------------------------------------------------
_ident_bad = re.compile(r"[^0-9a-zA-Z]+")


def sanitize_identifier(name: str, fallback: str = "col") -> str:
    """Turn an arbitrary header/filename into a safe snake_case SQL identifier."""
    s = _ident_bad.sub("_", str(name).strip().lower()).strip("_")
    if not s:
        s = fallback
    if s[0].isdigit():
        s = f"{fallback}_{s}"
    return s


def _dedupe(names: Sequence[str]) -> List[str]:
    """Ensure column names are unique by suffixing _2, _3, ... on collisions."""
    seen: Dict[str, int] = {}
    out: List[str] = []
    for n in names:
        if n not in seen:
            seen[n] = 1
            out.append(n)
        else:
            seen[n] += 1
            out.append(f"{n}_{seen[n]}")
    return out


def _quote(ident: str) -> str:
    """Double-quote a SQL identifier (portable across sqlite & duckdb)."""
    return '"' + ident.replace('"', '""') + '"'


class Table:
    """Lightweight description of a loaded table."""

    def __init__(self, name: str, columns: List[str], original_headers: List[str], nrows: int):
        self.name = name
        self.columns = columns                    # sanitized identifiers
        self.original_headers = original_headers   # as they appeared in the source
        self.nrows = nrows

    def __repr__(self) -> str:
        return f"<Table {self.name} rows={self.nrows} cols={len(self.columns)}>"


class DataLayer:
    """Load tabular sources into a SQL engine and query them read-only."""

    def __init__(self, engine: str = "auto"):
        self.engine = _select_engine(engine)
        self.con = _connect(self.engine)
        self._tables: Dict[str, Table] = {}

    # -- loading -----------------------------------------------------------
    def load_csv(self, path, table: Optional[str] = None, max_rows: Optional[int] = None) -> Table:
        """Load a single CSV file as a table. Returns the Table descriptor."""
        path = Path(path)
        if table is None:
            table = sanitize_identifier(path.stem, fallback="tbl")
        with path.open(newline="", encoding="utf-8-sig", errors="replace") as fh:
            reader = csv.reader(fh)
            try:
                raw_header = next(reader)
            except StopIteration:
                raw_header = []
            headers = _dedupe([sanitize_identifier(h, f"col_{i}") for i, h in enumerate(raw_header)])
            rows: List[Tuple] = []
            for i, rec in enumerate(reader):
                if max_rows is not None and i >= max_rows:
                    break
                # normalise row width to header width
                rec = rec[: len(headers)] + [None] * (len(headers) - len(rec))
                rows.append(tuple(v if (v is not None and v != "") else None for v in rec))
        self._create_and_fill(table, headers, rows)
        t = Table(table, headers, list(raw_header), len(rows))
        self._tables[table] = t
        return t

    def load_dir(self, directory, pattern: str = "*.csv", max_rows: Optional[int] = None,
                 skip_templates: bool = True) -> List[Table]:
        """Load every file matching `pattern` under `directory`."""
        loaded = []
        for p in sorted(Path(directory).glob(pattern)):
            if skip_templates and (p.name.startswith("_TEMPLATE") or p.stem.lower().startswith("template")):
                continue
            loaded.append(self.load_csv(p, max_rows=max_rows))
        return loaded

    def register_rows(self, table: str, columns: Sequence[str], rows: Sequence[Sequence]) -> Table:
        """Register in-memory rows (e.g. extracted from window.DASH) as a table."""
        name = sanitize_identifier(table, fallback="tbl")
        cols = _dedupe([sanitize_identifier(c, f"col_{i}") for i, c in enumerate(columns)])
        norm = [tuple(v if v != "" else None for v in r) for r in rows]
        self._create_and_fill(name, cols, norm)
        t = Table(name, cols, list(columns), len(norm))
        self._tables[name] = t
        return t

    def _create_and_fill(self, table: str, columns: List[str], rows: Sequence[Tuple]) -> None:
        qt = _quote(table)
        coldefs = ", ".join(f"{_quote(c)} TEXT" for c in columns)
        self.con.execute(f"DROP TABLE IF EXISTS {qt}")
        self.con.execute(f"CREATE TABLE {qt} ({coldefs})")
        if rows:
            placeholders = ", ".join("?" for _ in columns)
            self.con.executemany(f"INSERT INTO {qt} VALUES ({placeholders})", rows)
        if self.engine == "sqlite":
            self.con.commit()

    # -- introspection -----------------------------------------------------
    def tables(self) -> List[str]:
        return list(self._tables.keys())

    def table(self, name: str) -> Optional[Table]:
        return self._tables.get(name)

    def schema(self) -> Dict[str, List[str]]:
        """Return {table_name: [column, ...]} for all loaded tables."""
        return {name: list(t.columns) for name, t in self._tables.items()}

    def schema_prompt(self) -> str:
        """Human/LLM-readable schema description for prompt building."""
        lines = []
        for name, t in self._tables.items():
            lines.append(f"Table {name} ({t.nrows} rows): {', '.join(t.columns)}")
        return "\n".join(lines)

    # -- querying ----------------------------------------------------------
    def run_sql(self, sql: str) -> Tuple[List[str], List[Tuple]]:
        """Execute SQL and return (column_names, rows). No safety checks here —
        callers (NL2SQL) validate first. Kept engine-agnostic via DB-API."""
        cur = self.con.execute(sql)
        cols = [d[0] for d in (cur.description or [])]
        rows = cur.fetchall()
        return cols, rows

    def close(self) -> None:
        try:
            self.con.close()
        except Exception:
            pass
