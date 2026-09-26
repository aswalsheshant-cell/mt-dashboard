"""Power BI CM2 must not show a margin that was never calculated (FM-33).

Found 2026-09-26 on main c8ba4aa, after #232 fixed the same thing on the HTML
dashboard (FM-32):
  * PowerQuery/39_PL_Expense_Input.pq loaded the seed file's 3 "EXAMPLE ROW"
    template rows (Rs47.65 L of placeholders) as real expense -- the HTML loader
    has filtered them since FM-01, Power BI never did;
  * DAX/13_CM2_Measures.dax computed CM2 = NSV - [Total P&L Expense] with no
    check that any expense exists in the filter context, so a BLANK expense read
    as 0 and CM2 = NSV / CM2% = 100% (headline, chain, brand, category, MoM).
  * PowerBI/QuickSetup carries copies of both, so they must stay in step.

There is no DAX / M engine in CI or this container. These tests check the
structure that produces the behaviour; the four model cases (no expense, valid
expense, unmapped-only expense, one dimension without expense) are in
tests/powerbi/cm2_availability_cases.dax for DAX Studio / Power BI Desktop.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PQ = ROOT / "PowerBI" / "PowerQuery" / "39_PL_Expense_Input.pq"
DAX = ROOT / "PowerBI" / "DAX" / "13_CM2_Measures.dax"
QS_DAX = ROOT / "PowerBI" / "QuickSetup" / "AllDAX_Consolidated.txt"
QS_PQ = ROOT / "PowerBI" / "QuickSetup" / "AllPowerQuery_Consolidated.txt"
CASES = ROOT / "tests" / "powerbi" / "cm2_availability_cases.dax"


def _code(text):
    """Drop // comments so a comment can never satisfy or fail a check."""
    return "\n".join(ln.split("//", 1)[0] for ln in text.splitlines())


def _measures(text):
    """Measure name -> body, for top-level 'Name = ...' blocks in a .dax file."""
    out, name, body = {}, None, []
    for ln in _code(text).splitlines():
        m = re.match(r"^([A-Za-z][^=\n]*?)\s*=\s*(.*)$", ln)
        if m and not ln.startswith((" ", "\t", "VAR ", "RETURN")):
            if name:
                out[name] = "\n".join(body)
            name, body = m.group(1).strip(), [m.group(2)]
        elif name:
            body.append(ln)
    if name:
        out[name] = "\n".join(body)
    return out


def _steps(pq_text):
    """M step name -> expression, for the let-block of a query."""
    body = _code(pq_text)
    body = body[body.index("let") + 3: body.rindex("\nin")]
    steps, cur = {}, None
    for ln in body.splitlines():
        m = re.match(r"^\s{4}([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$", ln)
        if m:
            cur = m.group(1)
            steps[cur] = m.group(2)
        elif cur:
            steps[cur] += "\n" + ln
    return steps


def test_power_query_drops_template_rows_before_the_final_step():
    text = PQ.read_text(encoding="utf-8")
    steps = _steps(text)
    final = _code(text).rsplit("\nin", 1)[1].strip()
    guard = [n for n, e in steps.items() if "EXAMPLE ROW" in e and "Table.SelectRows" in e and "[Remarks]" in e]
    assert guard, "no step filters Remarks containing EXAMPLE ROW"
    # walk back from the final step: the guard must be on the path that produces it
    chain, cur = [], final
    while cur in steps:
        chain.append(cur)
        refs = [n for n in steps if n != cur and re.search(rf"\b{n}\b", steps[cur])]
        cur = refs[0] if refs else None
    assert set(guard) & set(chain), f"EXAMPLE ROW filter {guard} is not on the path to '{final}': {chain}"


def _gated(body, exp_measure):
    """True if the body returns BLANK when the expense measure is blank."""
    b = re.sub(r"\s+", " ", body)
    var = re.search(rf"VAR (_\w+) = \[{re.escape(exp_measure)}\]", b)
    if not var:
        return False
    v = var.group(1)
    return bool(re.search(rf"IF \( ISBLANK \( {v} \), BLANK \(\s*\)", b))


def test_cm2_measures_return_blank_without_expense():
    m = _measures(DAX.read_text(encoding="utf-8"))
    cases = {"CM2 Value": "Total P&L Expense",
             "Chain-wise CM2": "Total P&L Expense (by Chain)",
             "Brand-wise CM2": "Total P&L Expense (by Brand)",
             "Category-wise CM2": "Total P&L Expense (by Category)"}
    bad = [name for name, exp in cases.items() if name not in m or not _gated(m[name], exp)]
    assert bad == [], f"CM2 measures without an expense-availability gate: {bad}"


def test_mom_changes_need_both_months():
    m = _measures(DAX.read_text(encoding="utf-8"))
    for name in ("MoM CM2 Change", "MoM Expense Change"):
        b = re.sub(r"\s+", " ", m[name])
        assert re.search(r"ISBLANK \( _cur \) \|\| ISBLANK \( _prev \)", b), f"{name} must be BLANK when either month is missing"


def test_percent_measures_divide_so_blank_stays_blank():
    m = _measures(DAX.read_text(encoding="utf-8"))
    for name in ("CM2 %", "Chain-wise CM2 %", "Brand-wise CM2 %", "Category-wise CM2 %"):
        assert "DIVIDE" in m[name], name


def _qs_section(path, source_file):
    t = path.read_text(encoding="utf-8")
    parts = re.split(r"\n#{20,}\n# STEP \d+/\d+\s+--\s+SOURCE FILE: (\S+)\n(?:#.*\n)*#{20,}\n", t)
    sec = {parts[i]: parts[i + 1] for i in range(1, len(parts) - 1, 2)}
    assert source_file in sec, f"{source_file} not found in {path.name}"
    return sec[source_file]


def test_quicksetup_copies_match_canonical():
    pq = PQ.read_text(encoding="utf-8").strip()
    assert _qs_section(QS_PQ, PQ.name).strip() == pq, "QuickSetup PQ 39 drifted from the canonical file"
    dax = DAX.read_text(encoding="utf-8").strip()
    assert _qs_section(QS_DAX, DAX.name).strip().startswith(dax), "QuickSetup DAX 13 drifted from the canonical file"


def test_model_case_queries_cover_all_four_cases():
    text = CASES.read_text(encoding="utf-8")
    for case in ("CASE 1", "CASE 2", "CASE 3", "CASE 4"):
        assert case in text, case
    for measure in ("CM2 Value", "Chain-wise CM2", "Total P&L Expense (Unmapped)"):
        assert f"[{measure}]" in text, measure
