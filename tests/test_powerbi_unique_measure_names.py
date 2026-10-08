"""Every DAX measure in the Power BI build kit must have a unique name.

Found 2026-10-01 on main 6aa2e3c while preparing the Desktop install: two
different measures were both named `QC Mapping Coverage %`:
  * PowerBI/DAX/08_ForecastQC_Measures.dax  = [QC Mapped Offtake] / [FY26 Actual Offtake]
  * PowerBI/DAX/09_ArticleAllocation_Eligibility.dax
                                             = [QC Allocated Primary Total] / [QC Orig Primary (Dist-Brand)]
Power BI refuses a second measure with an existing name, so the QuickSetup
step 7 (paste every measure into _Measures) failed part-way on every install.
The 09 measure is now `QC Allocated Coverage %` (it pairs with
`QC Blocked Coverage %`; 08 keeps the name the Forecast QC page uses).

The splitter below only starts a new measure on a column-0 `Name =` (or
`[Name] =`) line once the previous expression's brackets are closed and it
does not end on an operator, so a line such as `IF ( [x] = 1, ...` inside an
expression is never read as a new measure. Every parsed body must balance.
"""
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DAX_DIR = ROOT / "PowerBI" / "DAX"
QS = ROOT / "PowerBI" / "QuickSetup" / "AllDAX_Consolidated.txt"

KEYWORDS = re.compile(
    r"^(VAR|RETURN|IF|SWITCH|CALCULATE|CALCULATETABLE|DIVIDE|SUM|SUMX|AVERAGEX|COUNTROWS|FILTER|ALL|"
    r"VALUES|MAX|MIN|COALESCE|AND|OR|NOT|DATEADD|DATESINPERIOD|ISBLANK|BLANK|FORMAT|SELECTEDVALUE|"
    r"HASONEVALUE|TOPN|RANKX|ADDCOLUMNS|SUMMARIZE|LOOKUPVALUE|MAXX|MINX|CONCATENATEX|TRUE|FALSE|"
    r"EVALUATE|DEFINE)\b", re.I)
HEADER = re.compile(r"^(?:\[(?P<bracket>[^\]]+)\]|(?P<plain>[^=\[\]'\"/][^=\[\]'\"]*?))\s*=(?!=)(?P<rest>.*)$")
OPEN_END = re.compile(r"(,|\+|-|\*|/|&&|\|\||\(|=|&|\bRETURN)\s*$")


def _strip_comment(line):
    out, in_str = [], False
    for i, c in enumerate(line):
        if c == '"':
            in_str = not in_str
        if not in_str and (line.startswith("//", i) or (line.startswith("--", i) and (i == 0 or line[i - 1] in " \t"))):
            break
        out.append(c)
    return "".join(out).rstrip()


def _depth(expr):
    d, in_str = 0, False
    for c in expr:
        if c == '"':
            in_str = not in_str
        elif not in_str:
            d += c in "([{"
            d -= c in ")]}"
    return d


def split_measures(text):
    """[(name, body)] for every top-level measure in one .dax file."""
    measures, cur = [], None
    for raw in text.splitlines():
        line = _strip_comment(raw)
        if not line.strip():
            continue
        m = HEADER.match(line) if not raw[:1].isspace() else None
        name = (m.group("bracket") or m.group("plain")).strip() if m else ""
        complete = cur is not None and _depth(cur[1]) == 0 and cur[1].strip() and not OPEN_END.search(cur[1].strip())
        if m and not KEYWORDS.match(name) and (cur is None or complete):
            cur = [name, m.group("rest")]
            measures.append(cur)
        elif cur is not None:
            cur[1] += "\n" + line
    return [(n, b) for n, b in measures]


def _kit_files():
    # 00 is the Date Table (a calculated table); 15 (promo) is NOT INCLUDED in QuickSetup.
    return [p for p in sorted(DAX_DIR.glob("*.dax")) if not p.name.startswith(("00_", "15_"))]


def test_every_measure_name_is_unique():
    where = defaultdict(list)
    for p in _kit_files():
        for name, _ in split_measures(p.read_text(encoding="utf-8")):
            where[name].append(p.name)
    dups = {n: f for n, f in where.items() if len(f) > 1}
    assert dups == {}, f"duplicate measure names: {dups}"


def test_every_parsed_measure_is_complete():
    for p in _kit_files():
        for name, body in split_measures(p.read_text(encoding="utf-8")):
            assert body.strip(), f"{p.name}: {name} has no expression"
            assert _depth(body) == 0, f"{p.name}: {name} has unbalanced brackets"


def test_quicksetup_has_no_duplicate_measure_headers():
    names = re.findall(r"^QC (?:Mapping|Allocated) Coverage % =", QS.read_text(encoding="utf-8"), re.M)
    assert sorted(names) == ["QC Allocated Coverage % =", "QC Mapping Coverage % ="]
