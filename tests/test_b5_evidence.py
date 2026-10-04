"""B5 evidence generator (scripts/b5_evidence.py) and its Windows runner.

B5 means: the CM2 cases and rolling averages were run on the REAL Power BI model
and every required row passed. CI has no DAX engine, so this file does not prove
the model works. It proves the generator that turns real engine output into the
evidence file (a) applies the run sheet's PASS rules exactly, (b) FAILS on a bad
result, (c) never writes PASS for something it did not measure, and (d) can never
be made to produce a B5 evidence file from fixtures or a non-live run.

Fixtures below are synthetic result tables for the generator only. They are never
written into docs/evidence.
"""
import copy
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import b5_evidence as b5  # noqa: E402

EVID = ROOT / "docs" / "evidence"

FY27, FY26 = "2026-27", "2025-26"
MONTHS = ["2026-04-01", "2026-05-01", "2026-06-01", "2026-07-01", "2026-08-01"]


def T(columns, rows):
    return {"columns": columns, "rows": rows}


def good_results():
    """A passing set of engine outputs (synthetic), keyed like the runner keys them."""
    c = {}
    c["preflight:1"] = T(["RowsLoaded", "ExpenseLoaded", "UnmappedRows", "UnmappedAmount", "MappedAmount"],
                         [[64, 1274.71, 2, 10.0, 1264.71]])
    c["cm2:2:1"] = T(["MonthStart", "NSV", "Expense", "CM2", "Check"],
                     [["2026-03-01", 900.0, None, None, "OK blank"]]
                     + [[m, 1000.0, 100.0, 900.0, "OK"] for m in MONTHS])
    c["cm2:3:1"] = T(["Unmapped", "Mapped", "CM2"], [[10.0, None, None]])
    c["cm2:4:1"] = T(["Chain", "NSV", "ChainExpense", "ChainCM2", "ChainCM2Pct"],
                     [["Reliance Retail", 500.0, 50.0, 450.0, 90.0], ["Lulu", 80.0, None, None, None]])
    c["cm2:4:2"] = T(["Violations"], [[0]])
    c["cm2:5:1"] = T(["Chain", "MonthStart", "ChainExpense", "MonthRowsExpense"],
                     [["Reliance Retail", "2026-04-01", 50.0, 50.0]])
    c["cm2:5:2"] = T(["Leak"], [[0]])
    c["cm2:6:1"] = T(["FY Year", "Expense", "TopChainExp", "CM2"], [[FY27, 1264.71, 400.0, 20000.0]])
    c["cm2:7:1"] = T(["BrandLeak", "CategoryLeak"], [[0, 0]])
    c["cm2:8:1"] = T(["Violations"], [[0]])
    c["cm2:9:1"] = T(["Scope", "Comparable", "NSV", "Expense", "ExpensePct", "CM2", "CM2Pct"], [
        ["No FY filter", 0, 55140.26, 1274.71, None, None, None],
        ["FY27", 1, 22239.91, 1274.71, 5.7, 20965.2, 94.3],
        ["FY26", 0, 32900.37, None, None, None, None]])
    c["rolling:1:1"] = T(["Months", "Mismatches"], [[17, 0]])
    c["rolling:2:1"] = T(["FirstMonth", "L3M", "L6M"], [["2025-04-01", None, None]])
    c["rolling:3:1"] = T(["Month", "L3M", "Expected"], [["2025-06-01", 2500.0, 2500.0]])
    c["rolling:4:1"] = T(["MonthStart", "NSV"], [])
    return c


def live_meta(**over):
    m = {"source": b5.LIVE_SOURCE, "port": 51234, "database": "ModernTrade_Model",
         "server_version": "16.0.1", "measure_count": 322, "git_sha": "84864ce", "git_dirty": False,
         "desktop_version": "2.140.1234.0", "model_file": "ModernTrade_Model.pbix",
         "utc": "2026-10-02T06:00:00Z"}
    m.update(over)
    return m


def results_doc(cases=None, meta=None):
    return {"meta": meta if meta is not None else live_meta(),
            "queries": b5.collect_queries(),
            "cases": cases if cases is not None else good_results()}


def statuses(doc, **kw):
    return {rid: r.status for rid, r in b5.evaluate_all(doc, **kw).items()}


REQUIRED = ["2", "4", "5", "6", "7a", "7b", "8", "9", "10"]


# ---- query extraction ------------------------------------------------------------------

def test_queries_cover_every_governed_block():
    q = b5.collect_queries()
    expected = {"preflight:1", "cm2:2:1", "cm2:3:1", "cm2:4:1", "cm2:4:2", "cm2:5:1", "cm2:5:2",
                "cm2:6:1", "cm2:7:1", "cm2:8:1", "cm2:9:1",
                "rolling:1:1", "rolling:2:1", "rolling:3:1", "rolling:4:1"}
    assert expected <= set(q), sorted(expected - set(q))
    for k, text in q.items():
        assert text.lstrip().startswith("EVALUATE"), k
        assert text.count("(") == text.count(")"), f"{k}: unbalanced brackets"


def test_expected_expense_months_match_the_live_expense_csv():
    import pandas as pd
    d = pd.read_csv(ROOT / "PowerBI/SeedData/Masters/PL_Expense_Input.csv", dtype=str)
    d = d[~d["Remarks"].fillna("").str.upper().str.contains("EXAMPLE ROW")]
    got = sorted({pd.to_datetime("1 " + m + " 2026", format="%d %B %Y").strftime("%Y-%m") for m in d["Month"]})
    assert got == sorted(b5.EXPECTED_EXPENSE_MONTHS)


# ---- PASS rules ------------------------------------------------------------------------

def test_passing_fixture_gives_all_required_rows_pass():
    st = statuses(results_doc())
    assert all(st[r] == "PASS" for r in REQUIRED), st
    assert st["3"] == "PASS"            # fixture has unmapped rows and the case holds
    assert st["9"] == "PASS"            # rolling averages
    assert st["1"] == "NOT_RUN"         # FY parser is manual: nothing measured, nothing passed


def test_case3_not_exercised_when_no_unmapped_rows():
    c = good_results()
    c["preflight:1"] = T(["RowsLoaded", "ExpenseLoaded", "UnmappedRows", "UnmappedAmount", "MappedAmount"],
                         [[64, 1274.71, 0, 0.0, 1274.71]])
    c["cm2:3:1"] = T(["Unmapped", "Mapped", "CM2"], [[None, None, None]])
    c["cm2:6:1"] = T(["FY Year", "Expense", "TopChainExp", "CM2"], [[FY27, 1274.71, 400.0, 20000.0]])
    st = statuses(results_doc(c))
    assert st["3"] == "NOT_EXERCISED" and st["6"] == "PASS"


def _mut(fn):
    c = copy.deepcopy(good_results())
    fn(c)
    return results_doc(c)


FAILING = {
    "case9_cm2_number_on_no_fy_row": ("10", lambda c: c["cm2:9:1"]["rows"][0].__setitem__(5, 538.66)),
    "case9_expense_pct_on_no_fy_row": ("10", lambda c: c["cm2:9:1"]["rows"][0].__setitem__(4, 2.3)),
    "case9_fy27_not_comparable": ("10", lambda c: c["cm2:9:1"]["rows"][1].__setitem__(1, 0)),
    "case9_fy27_arithmetic_wrong": ("10", lambda c: c["cm2:9:1"]["rows"][1].__setitem__(5, 22239.91)),
    "case9_fy26_cm2_equals_nsv": ("10", lambda c: c["cm2:9:1"]["rows"][2].__setitem__(5, 32900.37)),
    "case9_row_missing": ("10", lambda c: c["cm2:9:1"]["rows"].pop(0)),
    "case5_leak_above_zero": ("5", lambda c: c["cm2:5:2"].__setitem__("rows", [[3]])),
    "case5_detail_rows_disagree": ("5", lambda c: c["cm2:5:1"]["rows"][0].__setitem__(3, 80.0)),
    "case5_nothing_measured": ("5", lambda c: c["cm2:5:1"].__setitem__("rows", [])),
    "rolling_mismatches_above_zero": ("9", lambda c: c["rolling:1:1"].__setitem__("rows", [[17, 2]])),
    "rolling_first_month_not_blank": ("9", lambda c: c["rolling:2:1"]["rows"][0].__setitem__(1, 0.0)),
    "rolling_third_month_wrong": ("9", lambda c: c["rolling:3:1"]["rows"][0].__setitem__(1, 1800.0)),
    "case2_fail_row": ("2", lambda c: c["cm2:2:1"]["rows"].append(["2026-09-01", 1.0, None, 1.0, "FAIL shows CM2 without expense"])),
    "case2_missing_expense_month": ("2", lambda c: c["cm2:2:1"]["rows"].pop()),
    "case3_cm2_not_blank": ("3", lambda c: c["cm2:3:1"].__setitem__("rows", [[10.0, None, 500.0]])),
    "case4_violations": ("4", lambda c: c["cm2:4:2"].__setitem__("rows", [[2]])),
    "case4_arithmetic": ("4", lambda c: c["cm2:4:1"]["rows"][0].__setitem__(3, 500.0)),
    "case4_cm2_equals_nsv_without_expense": ("4", lambda c: c["cm2:4:1"]["rows"][1].__setitem__(3, 80.0)),
    "case6_fy26_expense_leaks": ("6", lambda c: c["cm2:6:1"]["rows"].append([FY26, 500.0, None, None])),
    "case6_fy27_wrong_total": ("6", lambda c: c["cm2:6:1"]["rows"][0].__setitem__(1, 1274.71)),
    "case7_brand_leak": ("7a", lambda c: c["cm2:7:1"].__setitem__("rows", [[4, 0]])),
    "case7_category_leak": ("7b", lambda c: c["cm2:7:1"].__setitem__("rows", [[0, 1]])),
    "case8_violations": ("8", lambda c: c["cm2:8:1"].__setitem__("rows", [[7]])),
}


@pytest.mark.parametrize("name", sorted(FAILING))
def test_bad_results_fail_the_expected_row(name):
    rid, fn = FAILING[name]
    st = statuses(_mut(fn))
    assert st[rid] == "FAIL", (name, st)
    others = {r: s for r, s in st.items() if r not in (rid, "1") and r in REQUIRED + ["3"]}
    # a single defect must not be hidden, and must not wrongly fail unrelated rows
    assert rid not in [r for r, s in others.items()], others


def test_missing_result_is_not_run_never_pass():
    c = good_results()
    del c["cm2:8:1"]
    del c["rolling:1:1"]
    st = statuses(results_doc(c))
    assert st["8"] == "NOT_RUN" and st["9"] in ("NOT_RUN", "FAIL")


def test_blank_counts_as_zero_for_count_checks_but_not_for_row_presence():
    c = good_results()
    c["cm2:5:2"]["rows"] = [[None]]            # COUNTROWS over an empty table can be BLANK
    c["cm2:8:1"]["rows"] = [[None]]
    st = statuses(results_doc(c))
    assert st["5"] == "PASS" and st["8"] == "PASS"
    c["cm2:8:1"]["rows"] = []                  # no row at all = nothing measured
    assert statuses(results_doc(c))["8"] == "NOT_RUN"


def test_fy_parser_is_manual_only():
    doc = results_doc()
    assert statuses(doc)["1"] == "NOT_RUN"
    ev = b5.evaluate_all(doc, manual_fy_failures=0, attested_by="MT Channel Analyst Lead")
    assert ev["1"].status == "PASS" and "manual entry" in ev["1"].actual
    assert b5.evaluate_all(doc, manual_fy_failures=2, attested_by="x")["1"].status == "FAIL"
    with pytest.raises(b5.EvidenceRefused):
        b5.evaluate_all(doc, manual_fy_failures=0)      # a number with nobody attesting it


# ---- safeguards: no evidence without a live engine --------------------------------------

def _evidence_files():
    return sorted(p.name for p in EVID.glob("B5_powerbi_runtime_*"))


@pytest.mark.parametrize("meta", [
    live_meta(source="test_fixture"),
    live_meta(source="chat"),
    {k: v for k, v in live_meta().items() if k != "port"},
    live_meta(database=""),
    live_meta(server_version=""),
    live_meta(measure_count=0),
])
def test_non_live_runs_cannot_write_evidence(meta, tmp_path):
    before = _evidence_files()
    with pytest.raises(b5.EvidenceRefused):
        b5.write_evidence(results_doc(meta=meta), raw_sha256="0" * 64, evidence_dir=tmp_path)
    assert list(tmp_path.iterdir()) == []
    with pytest.raises(b5.EvidenceRefused):
        b5.write_evidence(results_doc(meta=meta), raw_sha256="0" * 64)     # default dir = docs/evidence
    assert _evidence_files() == before, "a non-live run created a B5 evidence file"


def test_modified_queries_are_refused(tmp_path):
    doc = results_doc()
    original = doc["queries"]["cm2:5:2"]
    doc["queries"]["cm2:5:2"] = original.replace("<> 0", "<> 99")
    assert doc["queries"]["cm2:5:2"] != original, "test premise: the query really was edited"
    with pytest.raises(b5.EvidenceRefused):
        b5.write_evidence(doc, raw_sha256="0" * 64, evidence_dir=tmp_path)


def test_dirty_tree_is_refused_unless_allowed(tmp_path):
    doc = results_doc(meta=live_meta(git_dirty=True))
    with pytest.raises(b5.EvidenceRefused):
        b5.write_evidence(doc, raw_sha256="0" * 64, evidence_dir=tmp_path)
    p = b5.write_evidence(doc, raw_sha256="0" * 64, evidence_dir=tmp_path, allow_dirty=True)
    assert "working tree was DIRTY" in p.read_text(encoding="utf-8")


def test_expected_sha_mismatch_is_refused(tmp_path):
    with pytest.raises(b5.EvidenceRefused):
        b5.write_evidence(results_doc(), raw_sha256="0" * 64, evidence_dir=tmp_path, expect_sha="deadbee")


def test_fixture_output_is_labelled_and_cannot_go_to_docs_evidence(tmp_path):
    text = b5.render_fixture(results_doc(meta=live_meta(source="test_fixture")))
    assert "TEST_FIXTURE" in text and "NOT B5 EVIDENCE" in text
    p = tmp_path / "fixture.md"
    b5.write_fixture(results_doc(meta=live_meta(source="test_fixture")), p)
    assert "TEST_FIXTURE" in p.read_text(encoding="utf-8")
    before = _evidence_files()
    for bad in (EVID / "B5_TEST_FIXTURE_x.md", EVID / "B5_powerbi_runtime_2099-01-01.md"):
        with pytest.raises(b5.EvidenceRefused):
            b5.write_fixture(results_doc(meta=live_meta(source="test_fixture")), bad)
    assert _evidence_files() == before and not (EVID / "B5_TEST_FIXTURE_x.md").exists()


# ---- the evidence file itself ----------------------------------------------------------

def test_live_evidence_is_complete_and_satisfies_the_exit_condition_test(tmp_path):
    doc = results_doc()
    p = b5.write_evidence(doc, raw_sha256="ab" * 32, evidence_dir=tmp_path, run_by="MT Channel Analyst Lead",
                          refreshed=True, fy_parser_failures=0, attested_by="MT Channel Analyst Lead")
    t = p.read_text(encoding="utf-8")
    assert re.fullmatch(r"B5_powerbi_runtime_\d{4}-\d{2}-\d{2}\.md", p.name)
    assert "<" not in re.sub(r"`<attach screenshot>`", "", t.split("## Measurement provenance")[0]).replace("<=", ""), \
        "an unfilled <placeholder> was left in the evidence table"
    for fact in ("84864ce", "2.140.1234.0", "ModernTrade_Model.pbix", "51234", "322", "ab" * 32):
        assert fact in t, fact
    # same rule tests/test_b5_exit_condition.py applies to an evidence file
    for row in ("1", "2", "4", "5", "6", "7a", "7b", "8", "9", "10"):
        line = re.search(rf"^\| {row} \|.*$", t, re.M)
        assert line and "| PASS |" in line.group(0), row
    line3 = re.search(r"^\| 3 \|.*$", t, re.M)
    assert "| PASS |" in line3.group(0) or "NOT_EXERCISED" in line3.group(0)
    # screenshots are the human's: the generator never declares B5 cleared by itself
    assert "OPEN" in t and "screenshots" in t.split("**B5 verdict:**")[1].split("\n")[0].lower()
    assert "manual entry" in t


def test_failed_row_keeps_b5_open_and_names_it(tmp_path):
    rid, fn = FAILING["case9_cm2_number_on_no_fy_row"]
    p = b5.write_evidence(_mut(fn), raw_sha256="0" * 64, evidence_dir=tmp_path,
                          fy_parser_failures=0, attested_by="x")
    verdict = p.read_text(encoding="utf-8").split("**B5 verdict:**")[1].split("\n")[0]
    assert "OPEN" in verdict and "10" in verdict and "CLEARED" not in verdict.replace("not CLEARED", "")
    assert re.search(r"^\| 10 \|.*\| FAIL \|", p.read_text(encoding="utf-8"), re.M)


def test_runner_script_is_present_and_wired_to_the_python_side():
    ps = (ROOT / "scripts" / "B5-DesktopRunner.ps1").read_text(encoding="utf-8")
    for needle in ("msmdsrv.port.txt", "Microsoft.AnalysisServices.AdomdClient", "--emit-queries",
                   "b5_evidence.py", "live_analysis_services", "UNTESTED", "TMSCHEMA_MEASURES", "git_dirty"):
        assert needle in ps, f"B5-DesktopRunner.ps1 is missing {needle!r}"
    assert ps.count("{") == ps.count("}") and ps.count("(") == ps.count(")")
    assert "Invoke-Expression" not in ps and "iex " not in ps
    assert "docs/evidence" not in ps.replace("\\", "/") or "does not write" in ps.lower(), \
        "the PowerShell side must not write evidence itself"


def test_run_sheet_points_at_the_runner():
    sheet = (EVID / "B5_RUN_SHEET.md").read_text(encoding="utf-8")
    assert "B5_RUNNER.md" in sheet
    assert (EVID / "B5_RUNNER.md").exists()


def test_cli_refuses_a_fixture_results_file(tmp_path, capsys):
    p = tmp_path / "results.json"
    p.write_text(json.dumps(results_doc(meta=live_meta(source="test_fixture"))), encoding="utf-8")
    before = _evidence_files()
    assert b5.main(["--results", str(p)]) == 3
    assert _evidence_files() == before
