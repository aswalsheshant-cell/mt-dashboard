#!/usr/bin/env python3
"""
Excel workbook QC scanner -- read-only, offline, standard library only.

Recovered from the closed PR #14 branch (`scripts/ai_analyst/xlsx_qc.py`) and
rebuilt for current main: standalone (no ai_analyst package), no write-back
into the workbook, safety limits on the zip/XML, and named errors.

What it finds:
  ERROR_VALUE       a cell whose value is an Excel error (#REF!, #DIV/0!, #N/A, ...)   FAIL
  REF_IN_FORMULA    a formula that contains #REF! (even if its cached value looks ok)  FAIL
  DUPLICATE_KEY     the same key appearing on more than one row (--key)                FAIL
  NOT_ALLOWED       a value outside an allowed list, e.g. a stray "METock" (--allowed) FAIL
  CASE_VARIANT      "West" vs "WEST" in one column                                      WARN
  SPACE_VARIANT     "TDC 1%" vs "TDC  1%" / trailing spaces in one column              WARN
  HIDDEN_SHEET      a hidden or very-hidden sheet                                       WARN
  MERGED_CELLS      merged ranges (they break tabular reads)                            WARN
  STRUCTURE         a sheet listed in the workbook whose part is missing                FAIL

Guarantees: the workbook is only ever opened for reading; nothing is written
next to it unless --out names a report file (never the workbook itself); no
network call is made.

Usage:
  python scripts/xlsx_qc.py BOOK.xlsx
  python scripts/xlsx_qc.py BOOK.xlsx --key "Store Master:Store Code" \\
      --key "Offtake:Store Code+Article" --allowed "Offtake:Channel=MT,GT,EB2B,SIS" \\
      --out qc_report.csv

Exit codes: 0 = no FAIL findings, 1 = FAIL findings, 2 = the file could not be
scanned (named error: FILE_NOT_FOUND, NOT_A_ZIP, UNSUPPORTED_FORMAT,
MISSING_PART, CORRUPT, UNSAFE_XML, TOO_LARGE, BAD_ARGUMENT).
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import zipfile
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from xml.etree import ElementTree as ET

ERROR_LITERALS = {"#REF!", "#DIV/0!", "#N/A", "#VALUE!", "#NAME?", "#NULL!", "#NUM!",
                  "#SPILL!", "#CALC!", "#GETTING_DATA"}
# Safety limits: a real MT workbook is far below these; a zip bomb is not.
MAX_FILE_BYTES = 300 * 1024 * 1024
MAX_PART_BYTES = 400 * 1024 * 1024
MAX_TOTAL_BYTES = 2 * 1024 * 1024 * 1024
MAX_RATIO = 200          # uncompressed / compressed, per part
MAX_EXAMPLES = 20        # cell refs listed per finding


class WorkbookQCError(Exception):
    """A file that cannot be scanned. `code` is stable and machine-readable."""

    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code


@dataclass
class Finding:
    check: str
    status: str            # FAIL / WARN
    sheet: str
    column: str
    detail: str
    cells: list = field(default_factory=list)


@dataclass
class Sheet:
    name: str
    hidden: bool = False
    merged: list = field(default_factory=list)
    headers: dict = field(default_factory=dict)          # col letters -> header text
    rows: list = field(default_factory=list)             # [(row number, {col letters: value})]
    errors: list = field(default_factory=list)           # [(cell ref, error literal)]
    ref_formulas: list = field(default_factory=list)     # [(cell ref, formula text)]
    all_rows: list = field(default_factory=list)
    header_row: int = 0


# ---------------------------------------------------------------- safe reading
def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _col(ref: str) -> str:
    return "".join(ch for ch in ref if ch.isalpha())


def _parse(z: zipfile.ZipFile, part: str):
    info = z.getinfo(part)
    if info.file_size > MAX_PART_BYTES or (
            info.compress_size and info.file_size / info.compress_size > MAX_RATIO
            and info.file_size > 10 * 1024 * 1024):
        raise WorkbookQCError("TOO_LARGE", f"{part} expands to {info.file_size:,} bytes")
    data = z.read(part)
    head = data[:4096].upper()
    if b"<!DOCTYPE" in head or b"<!ENTITY" in data.upper():
        raise WorkbookQCError("UNSAFE_XML", f"{part} declares a DTD/entity; refusing to parse")
    try:
        return ET.fromstring(data)
    except ET.ParseError as e:
        raise WorkbookQCError("CORRUPT", f"{part} is not valid XML ({e})") from None


def read_workbook(path) -> dict:
    """Return {sheet name: Sheet}. Opens the file read-only; never writes."""
    p = Path(path)
    if not p.is_file():
        raise WorkbookQCError("FILE_NOT_FOUND", str(p))
    suffix = p.suffix.lower()
    if suffix in (".xls", ".xlsb", ".csv"):
        raise WorkbookQCError("UNSUPPORTED_FORMAT",
                              f"{suffix} is not supported; save as .xlsx (or use the "
                              f"repo's split_*_xlsb.py for .xlsb)")
    if p.stat().st_size > MAX_FILE_BYTES:
        raise WorkbookQCError("TOO_LARGE", f"{p.stat().st_size:,} bytes")
    if not zipfile.is_zipfile(p):
        raise WorkbookQCError("NOT_A_ZIP", f"{p.name} is not an .xlsx (zip) file -- corrupt or wrong format")
    try:
        z = zipfile.ZipFile(p, "r")
    except (zipfile.BadZipFile, OSError) as e:
        raise WorkbookQCError("NOT_A_ZIP", str(e)) from None
    with z:
        names = set(z.namelist())
        if sum(i.file_size for i in z.infolist()) > MAX_TOTAL_BYTES:
            raise WorkbookQCError("TOO_LARGE", "total uncompressed size over limit")
        if "xl/workbook.xml" not in names:
            raise WorkbookQCError("MISSING_PART", "xl/workbook.xml not found -- not an Excel workbook")
        shared = []
        if "xl/sharedStrings.xml" in names:
            for si in _parse(z, "xl/sharedStrings.xml"):
                shared.append("".join(t.text or "" for t in si.iter() if _local(t.tag) == "t"))
        rels = {}
        if "xl/_rels/workbook.xml.rels" in names:
            for r in _parse(z, "xl/_rels/workbook.xml.rels"):
                rels[r.get("Id")] = r.get("Target", "")
        out = {}
        for el in _parse(z, "xl/workbook.xml").iter():
            if _local(el.tag) != "sheet":
                continue
            name = el.get("name", "")
            rid = next((v for k, v in el.attrib.items() if _local(k) == "id"), None)
            target = rels.get(rid, "")
            part = target.lstrip("/") if target.startswith("/") else "xl/" + target
            sh = Sheet(name=name, hidden=el.get("state", "visible") in ("hidden", "veryHidden"))
            if not target or part not in names:
                sh.headers = None            # marks STRUCTURE problem
                out[name] = sh
                continue
            _read_sheet(z, part, sh, shared)
            out[name] = sh
        return out


def _cell(c, shared):
    t = c.get("t", "")
    v = f = None
    for ch in c:
        tag = _local(ch.tag)
        if tag == "v":
            v = ch.text
        elif tag == "f":
            f = ch.text
        elif tag == "is":
            v = "".join(x.text or "" for x in ch.iter() if _local(x.tag) == "t")
    if t == "s" and v is not None:
        try:
            v = shared[int(v)]
        except (ValueError, IndexError):
            v = None
    return t, v, f


def _read_sheet(z, part, sh: Sheet, shared):
    rows = []
    for el in _parse(z, part).iter():
        tag = _local(el.tag)
        if tag == "mergeCell" and el.get("ref"):
            sh.merged.append(el.get("ref"))
        elif tag == "row":
            rnum = int(el.get("r") or len(rows) + 1)
            cells = {}
            for c in el:
                if _local(c.tag) != "c":
                    continue
                ref = c.get("r", "")
                t, v, f = _cell(c, shared)
                if t == "e" or (v in ERROR_LITERALS):
                    sh.errors.append((ref, v or "#ERROR"))
                if f and "#REF!" in f.upper():
                    sh.ref_formulas.append((ref, "=" + f))
                if v is not None and str(v) != "":
                    cells[_col(ref)] = str(v)
            if cells:
                rows.append((rnum, cells))
    rows.sort(key=lambda r: r[0])
    sh.all_rows = rows
    set_header_row(sh, None)


def set_header_row(sh: Sheet, row_number):
    """Pick the header row. Real MT workbooks often carry a merged title banner
    and a note line above the table, so 'first non-empty row' is wrong. Auto
    rule: the first row (within the first 30) whose filled-cell count is at
    least half of the widest row there, and at least 2. `row_number` (1-based
    Excel row) overrides the rule."""
    rows = sh.all_rows
    if not rows:
        return
    if row_number is not None:
        idx = next((i for i, (r, _) in enumerate(rows) if r == row_number), None)
        if idx is None:
            raise WorkbookQCError("BAD_ARGUMENT", f"--header-row {sh.name}:{row_number} -- row is empty or missing")
    else:
        top = rows[:30]
        width = max(len(c) for _, c in top)
        need = max(2, (width + 1) // 2) if width >= 2 else 1
        idx = next(i for i, (_, c) in enumerate(top) if len(c) >= need)
    sh.header_row = rows[idx][0]
    sh.headers = rows[idx][1]
    sh.rows = rows[idx + 1:]


# ---------------------------------------------------------------- checks
def _norm_space(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _find_col(sh: Sheet, header: str):
    want = _norm_space(header).lower()
    return next((c for c, h in (sh.headers or {}).items() if _norm_space(h).lower() == want), None)


def _is_number(s: str) -> bool:
    try:
        float(s)
        return True
    except ValueError:
        return False


def scan(sheets: dict, keys=(), allowed=(), variant_columns=None) -> list:
    """Run every check. keys: [(sheet, [headers])]; allowed: [(sheet, header, {values})];
    variant_columns: None = every mostly-text column; else [(sheet, header)]."""
    F = []
    for sh in sheets.values():
        if sh.headers is None:
            F.append(Finding("STRUCTURE", "FAIL", sh.name, "", "sheet part missing from the file"))
            continue
        if sh.hidden:
            F.append(Finding("HIDDEN_SHEET", "WARN", sh.name, "", "sheet is hidden"))
        if sh.merged:
            F.append(Finding("MERGED_CELLS", "WARN", sh.name, "",
                             f"{len(sh.merged)} merged range(s)", sh.merged[:MAX_EXAMPLES]))
        by_err = defaultdict(list)
        for ref, lit in sh.errors:
            by_err[lit].append(ref)
        for lit, refs in sorted(by_err.items()):
            F.append(Finding("ERROR_VALUE", "FAIL", sh.name, "", f"{len(refs)} cell(s) = {lit}",
                             refs[:MAX_EXAMPLES]))
        if sh.ref_formulas:
            F.append(Finding("REF_IN_FORMULA", "FAIL", sh.name, "",
                             f"{len(sh.ref_formulas)} formula(s) reference #REF!",
                             [f"{r} {f}" for r, f in sh.ref_formulas[:MAX_EXAMPLES]]))

    for sheet, headers in keys:
        sh = sheets.get(sheet)
        cols = [_find_col(sh, h) for h in headers] if sh and sh.headers is not None else [None]
        if sh is None or None in cols:
            raise WorkbookQCError("BAD_ARGUMENT", f"--key {sheet}:{'+'.join(headers)} -- sheet or column not found")
        seen = defaultdict(list)
        for rnum, cells in sh.rows:
            k = tuple(cells.get(c, "") for c in cols)
            if any(k):
                seen[k].append(rnum)
        dups = {k: r for k, r in seen.items() if len(r) > 1}
        if dups:
            ex = [f"{' | '.join(k)} -> rows {', '.join(map(str, r[:5]))}" for k, r in list(dups.items())[:MAX_EXAMPLES]]
            F.append(Finding("DUPLICATE_KEY", "FAIL", sheet, "+".join(headers),
                             f"{len(dups)} key(s) on more than one row", ex))

    for sheet, header, ok in allowed:
        sh = sheets.get(sheet)
        c = _find_col(sh, header) if sh and sh.headers is not None else None
        if c is None:
            raise WorkbookQCError("BAD_ARGUMENT", f"--allowed {sheet}:{header} -- sheet or column not found")
        bad = defaultdict(list)
        for rnum, cells in sh.rows:
            v = cells.get(c)
            if v is not None and v not in ok:
                bad[v].append(f"{c}{rnum}")
        for v, refs in sorted(bad.items()):
            F.append(Finding("NOT_ALLOWED", "FAIL", sheet, header,
                             f"'{v}' is not in the allowed list ({len(refs)} cell(s))", refs[:MAX_EXAMPLES]))

    targets = []
    if variant_columns is None:
        for sh in sheets.values():
            for c, h in (sh.headers or {}).items():
                vals = [cells[c] for _, cells in sh.rows if c in cells]
                if vals and sum(not _is_number(v) for v in vals) / len(vals) >= 0.8:
                    targets.append((sh, c, h))
    else:
        for sheet, header in variant_columns:
            sh = sheets.get(sheet)
            c = _find_col(sh, header) if sh and sh.headers is not None else None
            if c is None:
                raise WorkbookQCError("BAD_ARGUMENT", f"--variants {sheet}:{header} -- sheet or column not found")
            targets.append((sh, c, header))
    for sh, c, h in targets:
        groups = defaultdict(lambda: defaultdict(list))
        for rnum, cells in sh.rows:
            v = cells.get(c)
            if v is not None:
                groups[_norm_space(v).casefold()][v].append(f"{c}{rnum}")
        for spellings in groups.values():
            if len(spellings) < 2:
                continue
            forms = list(spellings)
            case_only = len({_norm_space(x) for x in forms}) > 1
            check = "CASE_VARIANT" if case_only else "SPACE_VARIANT"
            refs = [r for x in forms for r in spellings[x][:3]]
            F.append(Finding(check, "WARN", sh.name, h,
                             " / ".join(repr(x) for x in forms), refs[:MAX_EXAMPLES]))
    return F


# ---------------------------------------------------------------- CLI
_CSV_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def csv_safe(value) -> str:
    """Text for a CSV cell that Excel will show literally, never evaluate.

    Sheet names, headers and key values come from the scanned workbook, so a
    hostile file could plant '=HYPERLINK(...)' and have it run when the CSV
    report is opened. A leading ' makes Excel treat the cell as text. Applied
    to the CSV report only: the workbook, console output and JSON keep the
    raw value."""
    v = "" if value is None else str(value)
    return "'" + v if v.startswith(_CSV_FORMULA_PREFIXES) else v


def _split(spec: str, flag: str):
    if ":" not in spec:
        raise WorkbookQCError("BAD_ARGUMENT", f"{flag} '{spec}' must be SHEET:COLUMN")
    sheet, rest = spec.split(":", 1)
    return sheet.strip(), rest


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Read-only Excel workbook QC scanner.")
    ap.add_argument("workbook")
    ap.add_argument("--key", action="append", default=[], help='"Sheet:Col" or "Sheet:ColA+ColB"')
    ap.add_argument("--allowed", action="append", default=[], help='"Sheet:Col=A,B,C"')
    ap.add_argument("--variants", action="append", default=None,
                    help='"Sheet:Col" -- limit case/space checks to these columns (default: every text column)')
    ap.add_argument("--header-row", action="append", default=[],
                    help='"Sheet:N" -- Excel row number of the header (default: auto-detected)')
    ap.add_argument("--out", help="write the findings to .csv or .json (never the workbook)")
    a = ap.parse_args(argv)
    try:
        keys = [(s, [h.strip() for h in r.split("+")]) for s, r in (_split(k, "--key") for k in a.key)]
        allowed = []
        for spec in a.allowed:
            s, r = _split(spec, "--allowed")
            if "=" not in r:
                raise WorkbookQCError("BAD_ARGUMENT", f"--allowed '{spec}' must be SHEET:COLUMN=A,B,C")
            h, vals = r.split("=", 1)
            allowed.append((s, h.strip(), {v.strip() for v in vals.split(",")}))
        variants = None
        if a.variants is not None:
            variants = [(s, h.strip()) for s, h in (_split(v, "--variants") for v in a.variants)]
        if a.out and Path(a.out).resolve() == Path(a.workbook).resolve():
            raise WorkbookQCError("BAD_ARGUMENT", "--out must not be the workbook itself")
        sheets = read_workbook(a.workbook)
        for spec in a.header_row:
            s, n = _split(spec, "--header-row")
            if s not in sheets or not n.strip().isdigit():
                raise WorkbookQCError("BAD_ARGUMENT", f"--header-row '{spec}' -- unknown sheet or not a row number")
            set_header_row(sheets[s], int(n))
        findings = scan(sheets, keys, allowed, variants)
    except WorkbookQCError as e:
        print(f"ERROR {e}", file=sys.stderr)
        return 2

    fails = [f for f in findings if f.status == "FAIL"]
    for f in findings:
        where = f.sheet + (f" / {f.column}" if f.column else "")
        print(f"{f.status:4}  {f.check:15} {where}: {f.detail}")
        for c in f.cells[:5]:
            print(f"        {c}")
    print(f"\n{len(fails)} FAIL, {len(findings) - len(fails)} WARN -> {'FAIL' if fails else 'PASS'}")
    if a.out:
        rows = [{k: csv_safe(v) for k, v in (asdict(f) | {"cells": "; ".join(f.cells)}).items()}
                for f in findings]
        if a.out.lower().endswith(".json"):
            Path(a.out).write_text(json.dumps([asdict(f) for f in findings], indent=2), encoding="utf-8")
        else:
            with open(a.out, "w", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, fieldnames=["check", "status", "sheet", "column", "detail", "cells"])
                w.writeheader()
                w.writerows(rows)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
