"""Minimal stdlib-only .xlsx WRITER, for building test fixtures only
(sheets, values, hidden state, cell comments, error-literal cells).
Not a general xlsx library -- exists because openpyxl.Workbook() can't be
used to build test fixtures in an environment where openpyxl itself may
not be installed (see release_gate.py's stdlib scan implementation, which
this exercises).
"""
from __future__ import annotations

import zipfile
from xml.sax.saxutils import escape

_CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
{sheet_overrides}
{comment_overrides}
</Types>"""

_PKG_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""


def _col_letter(n: int) -> str:
    s = ""
    while n > 0:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


class Sheet:
    def __init__(self, name: str, hidden: bool = False):
        self.name = name
        self.hidden = hidden
        self.cells: dict = {}       # (row, col) -> value
        self.comments: dict = {}    # (row, col) -> text

    def set(self, ref: str, value):
        row, col = _parse_ref(ref)
        self.cells[(row, col)] = value

    def set_comment(self, ref: str, text: str):
        row, col = _parse_ref(ref)
        self.comments[(row, col)] = text


def _parse_ref(ref: str):
    letters = "".join(c for c in ref if c.isalpha())
    digits = "".join(c for c in ref if c.isdigit())
    col = 0
    for ch in letters:
        col = col * 26 + (ord(ch) - ord("A") + 1)
    return int(digits), col


def write_xlsx(path, sheets: list):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        sheet_overrides = "\n".join(
            f'<Override PartName="/xl/worksheets/sheet{i+1}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            for i in range(len(sheets))
        )
        comment_overrides = "\n".join(
            f'<Override PartName="/xl/comments{i+1}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.comments+xml"/>'
            for i, s in enumerate(sheets) if s.comments
        )
        z.writestr("[Content_Types].xml", _CONTENT_TYPES.format(
            sheet_overrides=sheet_overrides, comment_overrides=comment_overrides))
        z.writestr("_rels/.rels", _PKG_RELS)

        sheets_xml = "\n".join(
            f'<sheet name="{escape(s.name)}" sheetId="{i+1}" r:id="rId{i+1}"'
            + (f' state="hidden"' if s.hidden else "") + "/>"
            for i, s in enumerate(sheets)
        )
        z.writestr("xl/workbook.xml",
                    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                    '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                    f'<sheets>{sheets_xml}</sheets></workbook>')

        wb_rels = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
                    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">']
        for i in range(len(sheets)):
            wb_rels.append(
                f'<Relationship Id="rId{i+1}" '
                'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
                f'Target="worksheets/sheet{i+1}.xml"/>')
        wb_rels.append("</Relationships>")
        z.writestr("xl/_rels/workbook.xml.rels", "\n".join(wb_rels))

        for i, sheet in enumerate(sheets):
            rows = {}
            for (row, col), value in sheet.cells.items():
                rows.setdefault(row, []).append((col, value))
            row_xml = []
            for row_num in sorted(rows):
                cells_xml = []
                for col, value in sorted(rows[row_num]):
                    ref = f"{_col_letter(col)}{row_num}"
                    if isinstance(value, str) and value.startswith("#") and value.endswith(("!", "?")):
                        cells_xml.append(f'<c r="{ref}" t="e"><v>{escape(value)}</v></c>')
                    elif isinstance(value, str):
                        cells_xml.append(f'<c r="{ref}" t="inlineStr"><is><t xml:space="preserve">{escape(value)}</t></is></c>')
                    else:
                        cells_xml.append(f'<c r="{ref}"><v>{value}</v></c>')
                row_xml.append(f'<row r="{row_num}">{"".join(cells_xml)}</row>')
            sheet_xml = (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                f'<sheetData>{"".join(row_xml)}</sheetData></worksheet>'
            )
            z.writestr(f"xl/worksheets/sheet{i+1}.xml", sheet_xml)

            if sheet.comments:
                comment_entries = "\n".join(
                    f'<comment ref="{_col_letter(col)}{row}" authorId="0"><text><t>{escape(text)}</t></text></comment>'
                    for (row, col), text in sheet.comments.items()
                )
                comments_xml = (
                    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                    '<comments xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                    f'<authors><author>Test</author></authors><commentList>{comment_entries}</commentList></comments>'
                )
                z.writestr(f"xl/comments{i+1}.xml", comments_xml)
                sheet_rels = (
                    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                    f'<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments" '
                    f'Target="../comments{i+1}.xml"/></Relationships>'
                )
                z.writestr(f"xl/worksheets/_rels/sheet{i+1}.xml.rels", sheet_rels)
