"""DAX validator for the paste-in measure files under ``PowerBI/DAX/``.

Static lint — no Tabular engine required, works fully offline:

  DAX001 error  unbalanced ( ) [ ] or unterminated string
  DAX002 error  duplicate definition name across the scanned files
  DAX003 warn   reference to a table not in the model inventory
                (inventory = agent/metadata exports, else docs/DataModel.md)
  DAX004 info   raw ``/`` division — repo convention is DIVIDE()
  DAX005 info   hardcoded FY / calendar-year literal (THE ONE FY RULE:
                derive FY from month+year, don't pin "25-26"/DATE(2025,..))
  DAX006 warn   [reference] that is neither a measure defined in the scanned
                files nor one in the metadata export (only when a real
                metadata export is loaded — docs don't list measures)

The measure-block splitter is a heuristic tuned to this repo's style
(``Name = expression`` headers at paren-depth 0, VAR/RETURN bodies); the eval
tests pin its behaviour against the real files.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .metadata import ModelInventory
from .report import Finding

_HEADER_RE = re.compile(r"^\s*([A-Za-z_][^=\[\]<>!]*?)\s*=(?!=)")
_KEYWORDS = {"var", "return", "evaluate", "define", "measure", "order", "if",
             "switch", "not", "true", "false"}
_QUOTED_TABLE_RE = re.compile(r"'([^']+)'\s*(?=\[)")
_BARE_TABLE_RE = re.compile(r"(?<![\w'\]])([A-Za-z_][A-Za-z0-9_]*)\s*\[")
_BRACKET_REF_RE = re.compile(r"(?<![\w'\]])\[([^\[\]]+)\]")
_RAW_DIV_RE = re.compile(r"(?<![/*])/(?![/*=])")
_FY_LIT_RE = re.compile(r'"(?:FY[ _\'-]?\d{2}(?:-\d{2})?|\d{2}-\d{2})"'
                        r"|\bDATE\s*\(\s*20\d\d\b", re.IGNORECASE)


@dataclass
class Definition:
    name: str
    file: str
    line: int
    body: str


def strip_comments_and_strings(text: str, keep_hash_identifiers: bool = False) -> tuple[str, list]:
    """Return (cleaned, string_literals). Cleaned preserves length/newlines;
    comments and string contents become spaces. string_literals is a list of
    (line_no, literal_including_quotes). With keep_hash_identifiers=True,
    M-style ``#"quoted identifiers"`` are kept verbatim (they are names,
    not strings)."""
    out = list(text)
    literals = []
    i, n, line = 0, len(text), 1
    while i < n:
        ch = text[i]
        if ch == "\n":
            line += 1
            i += 1
            continue
        if ch == "/" and i + 1 < n and text[i + 1] == "/":
            while i < n and text[i] != "\n":
                out[i] = " "
                i += 1
            continue
        if ch == "/" and i + 1 < n and text[i + 1] == "*":
            while i < n and not (text[i] == "*" and i + 1 < n and text[i + 1] == "/"):
                if text[i] == "\n":
                    line += 1
                else:
                    out[i] = " "
                i += 1
            if i < n:
                out[i] = out[i + 1] = " "
                i += 2
            continue
        if ch == '"':
            is_hash_ident = keep_hash_identifiers and i > 0 and text[i - 1] == "#"
            start, start_line = i, line
            i += 1
            while i < n:
                if text[i] == '"':
                    if i + 1 < n and text[i + 1] == '"':   # "" escape
                        i += 2
                        continue
                    break
                if text[i] == "\n":
                    line += 1
                i += 1
            end = min(i, n - 1)
            if not is_hash_ident:
                literals.append((start_line, text[start:end + 1]))
                for j in range(start + 1, end):
                    if out[j] != "\n":
                        out[j] = " "
            i = end + 1
            continue
        i += 1
    return "".join(out), literals


def check_balance(cleaned: str, fname: str) -> list:
    findings, stack = [], []
    pairs = {")": "(", "]": "["}
    line = 1
    for ch in cleaned:
        if ch == "\n":
            line += 1
        elif ch in "([":
            stack.append((ch, line))
        elif ch in ")]":
            if not stack or stack[-1][0] != pairs[ch]:
                findings.append(Finding(fname, line, "DAX001", "error",
                                        f"unbalanced '{ch}'"))
                return findings
            stack.pop()
    for ch, ln in stack:
        findings.append(Finding(fname, ln, "DAX001", "error", f"unclosed '{ch}'"))
    return findings


def extract_definitions(cleaned: str, fname: str) -> list:
    """Split a cleaned .dax file into Name = ... definition blocks."""
    defs: list[Definition] = []
    depth = 0
    for idx, raw in enumerate(cleaned.splitlines(), start=1):
        stripped = raw.strip()
        if depth == 0 and stripped and not stripped.startswith(("'", "[", "(", ")")):
            m = _HEADER_RE.match(raw)
            if m:
                name = m.group(1).strip()
                first = name.split()[0].lower() if name.split() else ""
                if first not in _KEYWORDS and not name[0].isdigit():
                    defs.append(Definition(name, fname, idx, ""))
        depth += raw.count("(") + raw.count("[") - raw.count(")") - raw.count("]")
        depth = max(depth, 0)
        if defs:
            defs[-1].body += raw + "\n"
    return defs


def validate_file(path: Path, inventory: ModelInventory | None = None,
                  all_defs: dict | None = None,
                  extra_known: set | None = None) -> list:
    fname = str(path)
    text = Path(path).read_text(encoding="utf-8-sig")
    cleaned, literals = strip_comments_and_strings(text)
    findings = check_balance(cleaned, fname)

    defs = extract_definitions(cleaned, fname)
    if all_defs is not None:
        for d in defs:
            if d.name in all_defs:
                findings.append(Finding(fname, d.line, "DAX002", "error",
                                        f"duplicate definition '{d.name}' "
                                        f"(also in {all_defs[d.name]})"))
            else:
                all_defs[d.name] = f"{fname}:{d.line}"

    defined_here = {d.name for d in defs} | (extra_known or set())

    # DAX003 — unknown table references
    if inventory and inventory.has_tables():
        known = inventory.tables | defined_here
        sev = "warn"
        src = ("metadata export" if inventory.source == "metadata"
               else "docs/DataModel.md")
        seen = set()
        for idx, line in enumerate(cleaned.splitlines(), start=1):
            for m in _QUOTED_TABLE_RE.finditer(line):
                t = m.group(1)
                if t not in known and t not in seen:
                    seen.add(t)
                    findings.append(Finding(fname, idx, "DAX003", sev,
                                            f"table '{t}' not found in {src}"))
            for m in _BARE_TABLE_RE.finditer(line):
                t = m.group(1)
                if " " in t or t.lower() in _KEYWORDS:
                    continue
                if t not in known and t not in seen and any(
                        k.lower() == t.lower() for k in known):
                    seen.add(t)   # case mismatch only
                    findings.append(Finding(fname, idx, "DAX003", sev,
                                            f"table '{t}' case-mismatches {src}"))

    # DAX004 — raw division
    for idx, line in enumerate(cleaned.splitlines(), start=1):
        if _RAW_DIV_RE.search(line):
            findings.append(Finding(fname, idx, "DAX004", "info",
                                    "raw '/' division — repo convention is DIVIDE()"))

    # DAX005 — hardcoded FY / year literals
    for ln, lit in literals:
        if _FY_LIT_RE.match(lit):
            findings.append(Finding(fname, ln, "DAX005", "info",
                                    f"hardcoded FY literal {lit} — THE ONE FY RULE: "
                                    "derive FY from month+year where possible"))
    for idx, line in enumerate(cleaned.splitlines(), start=1):
        if re.search(r"\bDATE\s*\(\s*20\d\d\b", line):
            findings.append(Finding(fname, idx, "DAX005", "info",
                                    "hardcoded DATE(20xx, ...) literal — "
                                    "THE ONE FY RULE: prefer month+year derivation"))

    # DAX006 — unknown [measure] references (needs a real metadata export)
    if inventory and inventory.source == "metadata" and inventory.measures:
        known_cols = set().union(*inventory.columns.values()) if inventory.columns else set()
        known_refs = inventory.measures | defined_here | known_cols
        seen = set()
        for idx, line in enumerate(cleaned.splitlines(), start=1):
            for m in _BRACKET_REF_RE.finditer(line):
                ref = m.group(1).strip()
                if ref and ref not in known_refs and ref not in seen:
                    seen.add(ref)
                    findings.append(Finding(fname, idx, "DAX006", "warn",
                                            f"[{ref}] is not a known measure/column"))
    return findings


def validate_paths(paths: list, inventory: ModelInventory | None = None) -> list:
    """Two-pass: collect every definition first so cross-file [Measure]
    references (e.g. 03_Forecast using [NSV] from 01_Core) resolve."""
    findings: list[Finding] = []
    all_defs: dict[str, str] = {}
    everything: set[str] = set()
    for p in paths:
        cleaned, _ = strip_comments_and_strings(
            Path(p).read_text(encoding="utf-8-sig"))
        everything |= {d.name for d in extract_definitions(cleaned, str(p))}
    for p in paths:
        findings.extend(validate_file(Path(p), inventory, all_defs,
                                      extra_known=everything))
    return findings
