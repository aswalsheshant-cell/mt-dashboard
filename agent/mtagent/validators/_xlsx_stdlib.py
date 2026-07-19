"""Minimal stdlib-only .xlsx reader (zipfile + ElementTree) for the
release-gate scans in release_gate.py.

Built because this project cannot assume network access to install
openpyxl (see AGENT_OPERATING_PRINCIPLES.md, lesson 4: "build a minimal
stdlib fallback rather than blocking entirely"). Not a general xlsx
library -- only reads what redaction_scan()/formula_error_scan() need:
sheet visibility state, cell values (including error literals), and
which cells carry a comment.
"""
from __future__ import annotations

import posixpath
import zipfile
from dataclasses import dataclass
from xml.etree import ElementTree as ET

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
RNS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"

ERROR_LITERALS = frozenset({"#REF!", "#N/A", "#VALUE!", "#DIV/0!", "#NAME?", "#NULL!", "#NUM!"})


@dataclass
class SheetInfo:
    name: str
    state: str   # "visible" | "hidden" | "veryHidden"
    path: str    # zip member path, e.g. "xl/worksheets/sheet1.xml"


class StdlibWorkbook:
    """Context-manager wrapper -- use `with open_workbook(path) as wb:`."""

    def __init__(self, path):
        self._z = zipfile.ZipFile(path)
        wb_root = ET.fromstring(self._z.read("xl/workbook.xml"))
        rels_root = ET.fromstring(self._z.read("xl/_rels/workbook.xml.rels"))
        rel_targets = {rel.get("Id"): rel.get("Target") for rel in rels_root}

        self.sheets: list[SheetInfo] = []
        sheets_el = wb_root.find(f"{NS}sheets")
        for sheet_el in sheets_el:
            name = sheet_el.get("name")
            state = sheet_el.get("state", "visible")
            rid = sheet_el.get(f"{RNS}id")
            target = rel_targets[rid]
            path = "xl/" + target if not target.startswith("/xl/") else target.lstrip("/")
            self.sheets.append(SheetInfo(name, state, path))

        self.shared_strings: list[str] = []
        if "xl/sharedStrings.xml" in self._z.namelist():
            ss_root = ET.fromstring(self._z.read("xl/sharedStrings.xml"))
            for si in ss_root:
                text = "".join(t.text or "" for t in si.iter(f"{NS}t"))
                self.shared_strings.append(text)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self._z.close()

    def comment_cells(self, sheet: SheetInfo) -> set:
        """Cell refs (e.g. 'A1') that carry a comment on this sheet, by
        resolving the sheet's own _rels to a linked comments part."""
        dirname, base = posixpath.split(sheet.path)
        rels_path = posixpath.join(dirname, "_rels", base + ".rels")
        if rels_path not in self._z.namelist():
            return set()
        rels_root = ET.fromstring(self._z.read(rels_path))
        comments_target = None
        for rel in rels_root:
            if rel.get("Type", "").endswith("/comments"):
                comments_target = posixpath.normpath(posixpath.join(dirname, rel.get("Target")))
                break
        if not comments_target or comments_target not in self._z.namelist():
            return set()
        comments_root = ET.fromstring(self._z.read(comments_target))
        return {c.get("ref") for c in comments_root.iter(f"{NS}comment") if c.get("ref")}

    def iter_cells(self, sheet: SheetInfo):
        """Yields (cell_ref, value_or_None, is_error_literal) for every
        populated cell -- string cells resolved via sharedStrings/inlineStr,
        error cells (t="e") yield their literal (e.g. "#REF!")."""
        with self._z.open(sheet.path) as fh:
            for event, elem in ET.iterparse(fh, events=("end",)):
                if elem.tag == f"{NS}c":
                    ref = elem.get("r")
                    t = elem.get("t")
                    v_elem = elem.find(f"{NS}v")
                    is_elem = elem.find(f"{NS}is")
                    if t == "s" and v_elem is not None:
                        val = self.shared_strings[int(v_elem.text)]
                    elif t == "inlineStr" and is_elem is not None:
                        val = "".join(t2.text or "" for t2 in is_elem.iter(f"{NS}t"))
                    elif v_elem is not None:
                        val = v_elem.text
                    else:
                        val = None
                    yield ref, val, (t == "e")
                    elem.clear()


def open_workbook(path) -> StdlibWorkbook:
    return StdlibWorkbook(path)
