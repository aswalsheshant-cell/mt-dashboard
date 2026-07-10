"""Phase 7 tests — workbook QC on a crafted .xlsx (stdlib, no openpyxl needed)."""

import os
import sys
import tempfile
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ai_analyst.xlsx_qc import WorkbookQC, read_workbook, qc_report

MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
RELNS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def _col(i):  # 0-based -> A, B, ...
    return chr(ord("A") + i)


def _cell(ref, kind, val):
    if kind == "e":
        return f'<c r="{ref}" t="e"><v>{val}</v></c>'
    if kind == "n":
        return f'<c r="{ref}"><v>{val}</v></c>'
    return f'<c r="{ref}" t="inlineStr"><is><t>{escape(str(val))}</t></is></c>'


def _sheet_xml(rows, merges):
    body = []
    for ri, row in enumerate(rows, start=1):
        cells = []
        for ci, cell in enumerate(row):
            ref = f"{_col(ci)}{ri}"
            if isinstance(cell, tuple):
                cells.append(_cell(ref, cell[0], cell[1]))
            else:
                cells.append(_cell(ref, "s", cell))
        body.append(f'<row r="{ri}">{"".join(cells)}</row>')
    merge_xml = ""
    if merges:
        merge_xml = f'<mergeCells count="{len(merges)}">' + \
            "".join(f'<mergeCell ref="{m}"/>' for m in merges) + "</mergeCells>"
    return (f'<?xml version="1.0"?><worksheet xmlns="{MAIN}"><sheetData>'
            + "".join(body) + "</sheetData>" + merge_xml + "</worksheet>")


def make_xlsx(path, sheets):
    """sheets = [(name, hidden, rows, merges)] -> write a minimal valid .xlsx."""
    sheet_tags, rel_tags, ct_over = [], [], []
    for idx, (name, hidden, _rows, _m) in enumerate(sheets, start=1):
        st = ' state="hidden"' if hidden else ""
        sheet_tags.append(f'<sheet name="{escape(name)}" sheetId="{idx}"{st} r:id="rId{idx}"/>')
        rel_tags.append(f'<Relationship Id="rId{idx}" '
                        f'Type="{RELNS}/worksheet" Target="worksheets/sheet{idx}.xml"/>')
        ct_over.append(f'<Override PartName="/xl/worksheets/sheet{idx}.xml" '
                       f'ContentType="application/vnd.openxmlformats-officedocument.'
                       f'spreadsheetml.worksheet+xml"/>')
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("[Content_Types].xml",
                   '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/'
                   'package/2006/content-types"><Default Extension="rels" ContentType='
                   '"application/vnd.openxmlformats-package.relationships+xml"/>'
                   '<Default Extension="xml" ContentType="application/xml"/>'
                   '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.'
                   'openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
                   + "".join(ct_over) + "</Types>")
        z.writestr("_rels/.rels",
                   '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.'
                   'org/package/2006/relationships"><Relationship Id="rId1" Type="'
                   f'{RELNS}/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        z.writestr("xl/workbook.xml",
                   f'<?xml version="1.0"?><workbook xmlns="{MAIN}" xmlns:r="{RELNS}">'
                   f'<sheets>{"".join(sheet_tags)}</sheets></workbook>')
        z.writestr("xl/_rels/workbook.xml.rels",
                   '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.'
                   f'org/package/2006/relationships">{"".join(rel_tags)}</Relationships>')
        for idx, (_n, _h, rows, merges) in enumerate(sheets, start=1):
            z.writestr(f"xl/worksheets/sheet{idx}.xml", _sheet_xml(rows, merges))


def _fixture(path):
    raw_rows = [
        ["Chain", "Channel", "MonthDate", "StoreKey", "Calc"],
        ["DMart", "MT", ("n", 46113), "S1", ("n", 10)],
        ["DMart", "MT ", ("n", 46114), "S2", ("n", 20)],           # trailing-space variant
        ["DMart", "METock", "May'26", "S2", ("e", "#REF!")],        # bad label, dup key, text date, error
        ["DMart", "mt", ("n", 46116), "S3", ("n", 30)],             # case variant
        ["DMart", "GT", ("n", 46117), "S4", ("n", 40)],
    ]
    make_xlsx(path, [
        ("Raw_Data", False, raw_rows, ["A1:B1"]),   # data sheet + merged cells
        ("Scratch", True, [["tmp"]], []),           # hidden sheet
    ])


class TestReader(unittest.TestCase):
    def test_reads_sheets_and_headers(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "wb.xlsx"
            _fixture(p)
            sheets = read_workbook(str(p))
            self.assertIn("Raw_Data", sheets)
            self.assertTrue(sheets["Scratch"].hidden)
            self.assertEqual(sheets["Raw_Data"].column("Channel"),
                             ["MT", "MT ", "METock", "mt", "GT"])


class TestChecks(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.p = Path(self.d.name) / "wb.xlsx"
        _fixture(self.p)
        self.qc = WorkbookQC.open(str(self.p))

    def tearDown(self):
        self.d.cleanup()

    def _statuses(self, rows, check):
        return [r for r in rows if r.check == check]

    def test_broken_reference(self):
        rows = self.qc.check_errors()
        self.assertTrue(any(r.check == "Broken reference" and r.status == "Fail" for r in rows))

    def test_hidden_sheet(self):
        rows = self.qc.check_hidden_sheets()
        self.assertTrue(any(r.tab == "Scratch" for r in rows))

    def test_merged_in_data_sheet(self):
        rows = self.qc.check_merged_in_data()
        self.assertTrue(any(r.tab == "Raw_Data" and r.status == "Warn" for r in rows))

    def test_duplicate_keys(self):
        rows = self.qc.check_duplicate_keys("Raw_Data", ["StoreKey"])
        self.assertEqual(rows[0].status, "Fail")
        self.assertEqual(rows[0].difference, "1")   # S2 duplicated once

    def test_date_inconsistency(self):
        rows = self.qc.check_date_consistency("Raw_Data", "MonthDate")
        self.assertEqual(rows[0].status, "Warn")

    def test_filter_labels_catch_metock_and_variants(self):
        rows = self.qc.check_filter_labels("Raw_Data", "Channel",
                                           allowed=["MT", "GT", "EB2B", "SIS"])
        # 'METock' is not allowed -> Fail
        self.assertTrue(any(r.check == "Unexpected filter value" and "METock" in r.source
                            and r.status == "Fail" for r in rows))
        # MT / MT  / mt collapse to one canonical -> inconsistent-label Warn
        self.assertTrue(any(r.check == "Inconsistent filter label" for r in rows))

    def test_run_and_report(self):
        rows = self.qc.run(
            duplicate_keys={"Raw_Data": ["StoreKey"]},
            dates={"Raw_Data": "MonthDate"},
            filters={"Raw_Data": {"Channel": ["MT", "GT", "EB2B", "SIS"]}},
        )
        md = qc_report(rows).to_markdown()
        self.assertIn("QC_Check", md)
        self.assertIn("METock", md)
        self.assertIn("Confidential - MT Internal", md)
        # a clean workbook section still lists Pass/Fail statuses
        self.assertTrue(any(r.status == "Fail" for r in rows))


if __name__ == "__main__":
    unittest.main()
