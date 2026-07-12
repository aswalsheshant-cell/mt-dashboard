"""Corpus builder: everything the agent can retrieve over, all local.

Sources swept from the repo (no network):
  * Markdown docs   — CLAUDE.md, PowerBI/docs/*.md, all README.md files
  * DAX measures    — PowerBI/DAX/*.dax
  * Power Query     — PowerBI/PowerQuery/*.pq
  * Seed CSV shapes — header + 2 sample rows of each committed CSV
  * PBI metadata    — agent/metadata exports rendered as text (tables,
                      columns, measures) via metadata.py
  * PDFs            — any *.pdf under cfg.pdf_dirs (needs pypdf; skipped
                      with a notice otherwise)

Chunks are heading-aware for markdown and block-aware for DAX/PQ, sized by
cfg.chunk_chars with cfg.chunk_overlap.
"""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path

from .config import Config
from .metadata import load_inventory


@dataclass
class Chunk:
    source: str        # repo-relative path
    section: str       # heading / block hint
    text: str

    @property
    def key(self) -> str:
        return f"{self.source}#{self.section}"


# --------------------------------------------------------------------------
# splitting helpers
# --------------------------------------------------------------------------

def _window(text: str, size: int, overlap: int) -> list[str]:
    text = text.strip()
    if len(text) <= size:
        return [text] if text else []
    out, i = [], 0
    while i < len(text):
        piece = text[i:i + size]
        if i + size >= len(text):        # final window — take the tail and stop
            out.append(piece.strip())
            break
        nl = piece.rfind("\n")           # prefer a line boundary
        if nl > size // 2:
            piece = piece[:nl]
        out.append(piece.strip())
        i += len(piece) - overlap        # piece > size//2 > overlap, so step > 0
    return [p for p in out if p]


def split_markdown(text: str, source: str, size: int, overlap: int) -> list[Chunk]:
    chunks, current, heading = [], [], "intro"
    for line in text.splitlines():
        m = re.match(r"^(#{1,4})\s+(.*)", line)
        if m:
            body = "\n".join(current)
            for j, piece in enumerate(_window(body, size, overlap)):
                chunks.append(Chunk(source, f"{heading}[{j}]" if j else heading, piece))
            current, heading = [line], m.group(2).strip()
        else:
            current.append(line)
    body = "\n".join(current)
    for j, piece in enumerate(_window(body, size, overlap)):
        chunks.append(Chunk(source, f"{heading}[{j}]" if j else heading, piece))
    return chunks


def split_code(text: str, source: str, size: int, overlap: int) -> list[Chunk]:
    """DAX/PQ/py: split on blank-line-separated blocks, then window."""
    blocks = re.split(r"\n\s*\n", text)
    merged, buf = [], ""
    for b in blocks:
        if len(buf) + len(b) < size:
            buf += ("\n\n" if buf else "") + b
        else:
            if buf:
                merged.append(buf)
            buf = b
    if buf:
        merged.append(buf)
    out = []
    for i, m in enumerate(merged):
        for j, piece in enumerate(_window(m, size, overlap)):
            out.append(Chunk(source, f"block{i}" + (f".{j}" if j else ""), piece))
    return out


def csv_shape_chunk(path: Path, root: Path) -> Chunk | None:
    try:
        with open(path, newline="", encoding="utf-8-sig", errors="replace") as fh:
            rows = []
            for i, row in enumerate(csv.reader(fh)):
                rows.append(", ".join(row[:40]))
                if i >= 2:
                    break
    except OSError:
        return None
    if not rows:
        return None
    rel = str(path.relative_to(root))
    text = (f"CSV file {rel}\ncolumns: {rows[0]}\n"
            + ("sample rows:\n" + "\n".join(rows[1:]) if len(rows) > 1 else ""))
    return Chunk(rel, "shape", text)


def pdf_chunks(path: Path, root: Path, size: int, overlap: int) -> tuple[list[Chunk], str | None]:
    """Extract PDF text with pypdf if installed. Returns (chunks, notice)."""
    try:
        from pypdf import PdfReader
    except ImportError:
        try:
            from PyPDF2 import PdfReader   # older installs
        except ImportError:
            return [], f"skipped {path.name}: pypdf not installed (pip install pypdf)"
    try:
        reader = PdfReader(str(path))
        pages = [(p.extract_text() or "") for p in reader.pages]
    except Exception as e:
        return [], f"skipped {path.name}: {e}"
    rel = str(path.relative_to(root)) if path.is_relative_to(root) else str(path)
    out = []
    for pno, ptext in enumerate(pages, start=1):
        for j, piece in enumerate(_window(ptext, size, overlap)):
            out.append(Chunk(rel, f"p{pno}" + (f".{j}" if j else ""), piece))
    return out, None


# --------------------------------------------------------------------------
# corpus sweep
# --------------------------------------------------------------------------

def build_corpus(cfg: Config) -> tuple[list[Chunk], list[str]]:
    root = cfg.root()
    size, ov = cfg.chunk_chars, cfg.chunk_overlap
    chunks: list[Chunk] = []
    notices: list[str] = []

    for md in sorted(root.glob("*.md")) + sorted(root.glob("PowerBI/**/*.md")) \
            + sorted(root.glob("dashboard/README.md")):
        rel = str(md.relative_to(root))
        chunks += split_markdown(md.read_text(encoding="utf-8", errors="replace"),
                                 rel, size, ov)

    for pat, splitter in (("PowerBI/DAX/*.dax", split_code),
                          ("PowerBI/PowerQuery/*.pq", split_code),
                          ("scripts/*.py", split_code)):
        for f in sorted(root.glob(pat)):
            rel = str(f.relative_to(root))
            chunks += splitter(f.read_text(encoding="utf-8", errors="replace"),
                               rel, size, ov)

    for f in sorted(root.glob("PowerBI/SeedData/**/*.csv")) \
            + sorted(root.glob("PowerBI/templates/*.csv")) \
            + sorted(root.glob("PowerBI/RawDataFolders/*/_TEMPLATE_*.csv")):
        c = csv_shape_chunk(f, root)
        if c:
            chunks.append(c)

    inv = load_inventory(cfg.path(cfg.metadata_dir), root)
    if inv.source == "metadata":
        lines = ["Power BI model metadata export (agent/metadata):",
                 "tables: " + ", ".join(sorted(inv.tables))]
        if inv.measures:
            lines.append("measures: " + ", ".join(sorted(inv.measures)))
        for t, cols in sorted(inv.columns.items()):
            lines.append(f"columns of {t}: " + ", ".join(sorted(cols)))
        for j, piece in enumerate(_window("\n".join(lines), size, ov)):
            chunks.append(Chunk("agent/metadata", f"model[{j}]", piece))

    for d in cfg.pdf_dirs:
        pdir = cfg.path(d)
        if pdir.is_dir():
            for pdf in sorted(pdir.glob("*.pdf")):
                got, notice = pdf_chunks(pdf, root, size, ov)
                chunks += got
                if notice:
                    notices.append(notice)

    return chunks, notices
