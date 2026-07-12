"""Power BI model inventory from local metadata exports.

The agent never talks to the Power BI service. Instead the analyst drops any
of these into ``agent/metadata/`` (all optional):

  * ``model.bim`` / ``*.bim``   — TMSL model JSON (Tabular Editor: File > Save As)
  * ``database.json``           — TMSL wrapper with a top-level ``model`` key
  * ``INFO.TABLES.csv`` / ``INFO.COLUMNS.csv`` / ``INFO.MEASURES.csv``
                                — DAX Studio:  EVALUATE INFO.TABLES()  etc.,
                                  exported as CSV (any filename containing
                                  table/column/measure works)

When no export exists we fall back to parsing ``PowerBI/docs/DataModel.md``
(the repo's authoritative star-schema doc), so the DAX validator's
unknown-table check still works out of the box — at warning severity, since
docs can lag the real model.
"""
from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ModelInventory:
    tables: set = field(default_factory=set)
    columns: dict = field(default_factory=dict)   # table -> set(column)
    measures: set = field(default_factory=set)
    source: str = "none"                          # 'metadata' | 'docs' | 'none'

    def has_tables(self) -> bool:
        return bool(self.tables)

    def merge(self, other: "ModelInventory") -> None:
        self.tables |= other.tables
        for t, cols in other.columns.items():
            self.columns.setdefault(t, set()).update(cols)
        self.measures |= other.measures


# --------------------------------------------------------------------------
# TMSL (.bim / database.json)
# --------------------------------------------------------------------------

def parse_bim(path: Path) -> ModelInventory:
    inv = ModelInventory(source="metadata")
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    model = data.get("model", data)
    for t in model.get("tables", []):
        name = t.get("name")
        if not name:
            continue
        inv.tables.add(name)
        inv.columns[name] = {c.get("name") for c in t.get("columns", []) if c.get("name")}
        for m in t.get("measures", []):
            if m.get("name"):
                inv.measures.add(m["name"])
    return inv


# --------------------------------------------------------------------------
# DAX Studio INFO.*() CSV exports
# --------------------------------------------------------------------------

def _name_col(fieldnames: list[str], *extra: str) -> str | None:
    cands = [*extra, "Name", "[Name]", "MEASURE_NAME", "TABLE_NAME", "COLUMN_NAME",
             "Explicit Name", "[ExplicitName]", "ExplicitName"]
    for c in cands:
        for f in fieldnames or []:
            if f.strip().strip("[]").lower() == c.strip("[]").lower():
                return f
    return None


def parse_info_csvs(directory: Path) -> ModelInventory:
    inv = ModelInventory(source="metadata")
    for f in sorted(Path(directory).glob("*.csv")):
        low = f.name.lower()
        kind = ("tables" if "table" in low else
                "measures" if "measure" in low else
                "columns" if "column" in low else None)
        if not kind:
            continue
        with open(f, newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            col = _name_col(reader.fieldnames or [])
            if not col:
                continue
            for row in reader:
                name = (row.get(col) or "").strip()
                if not name or name.startswith(("DateTableTemplate_", "LocalDateTable_")):
                    continue
                if kind == "tables":
                    inv.tables.add(name)
                elif kind == "measures":
                    inv.measures.add(name)
                else:
                    inv.columns.setdefault("*", set()).add(name)
    return inv


# --------------------------------------------------------------------------
# Fallback: PowerBI/docs/DataModel.md
# --------------------------------------------------------------------------

_MD_TABLE_ROW = re.compile(r"^\|\s*`([^`]+)`\s*\|")


def parse_datamodel_md(path: Path) -> ModelInventory:
    inv = ModelInventory(source="docs")
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError:
        return inv
    for line in text.splitlines():
        m = _MD_TABLE_ROW.match(line)
        if m:
            # first backticked cell of each markdown table row is the table name
            name = m.group(1).split("`")[0].strip()
            if name and " → " not in name:
                inv.tables.add(name)
    return inv


def load_inventory(metadata_dir: Path, repo_root: Path) -> ModelInventory:
    """Prefer real metadata exports; fall back to DataModel.md."""
    inv = ModelInventory()
    md = Path(metadata_dir)
    if md.is_dir():
        for bim in sorted(list(md.glob("*.bim")) + list(md.glob("database.json"))):
            try:
                inv.merge(parse_bim(bim))
                inv.source = "metadata"
            except (json.JSONDecodeError, OSError):
                pass
        got = parse_info_csvs(md)
        if got.has_tables() or got.measures:
            inv.merge(got)
            inv.source = "metadata"
    if not inv.has_tables():
        inv = parse_datamodel_md(repo_root / "PowerBI" / "docs" / "DataModel.md")
    return inv
