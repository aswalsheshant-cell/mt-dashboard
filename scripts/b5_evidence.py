#!/usr/bin/env python3
"""B5 evidence generator: turns REAL Power BI Desktop engine output into the B5 evidence file.

B5 (docs/COMPLETION_BLOCKER_PACK.md) is cleared only by a Desktop run of the CM2
cases and the rolling-average cases on the real model. CI has no DAX engine, so
nothing here can prove the model works. This module does three narrow jobs:

  1. extract the governed EVALUATE blocks from
       tests/powerbi/cm2_availability_cases.dax and rolling_average_cases.dax
     (single source of truth: the Windows runner asks THIS script for the queries);
  2. apply the PASS rules of docs/evidence/B5_RUN_SHEET.md to the result tables;
  3. fill docs/evidence/B5_EVIDENCE_TEMPLATE.md, but only from a live run.

Safeguards (each is pinned by tests/test_b5_evidence.py):
  * evidence is written only if results.json carries meta.source ==
    'live_analysis_services' with a port, database, server version, measure count,
    git SHA and Desktop version; anything else raises EvidenceRefused;
  * the queries recorded in results.json must equal the queries in the repo, so a
    run of edited queries cannot be presented as the governed run;
  * a dirty working tree, or a SHA different from --expect-sha, is refused;
  * fixture/test output is labelled TEST_FIXTURE and can never be written into
    docs/evidence or named B5_powerbi_runtime_*;
  * a row with no measured result is NOT_RUN, never PASS; an unmeasurable step
    (FY parser = Power Query M, unreachable through Analysis Services) is accepted
    only as an explicit, attested manual entry;
  * the generator never declares B5 CLEARED: the screenshots (one per step, per the
    run sheet) are a human step, so a fully passing run still reads
    'OPEN - screenshots not yet attached'.

Usage (normally called by scripts/B5-DesktopRunner.ps1):
    python scripts/b5_evidence.py --emit-queries queries.json
    python scripts/b5_evidence.py --results results.json [--run-by ROLE] [--refreshed]
                                  [--fy-parser-failures N --attested-by NAME]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_DIR = ROOT / "docs" / "evidence"
TEMPLATE = EVIDENCE_DIR / "B5_EVIDENCE_TEMPLATE.md"
CM2_CASES = ROOT / "tests" / "powerbi" / "cm2_availability_cases.dax"
ROLLING_CASES = ROOT / "tests" / "powerbi" / "rolling_average_cases.dax"

LIVE_SOURCE = "live_analysis_services"
FY26, FY27 = "2025-26", "2026-27"          # 'Date Table'[FY Year] labels (DAX/00_DateTable.dax)
TOL = 0.01                                  # run sheet: to Rs 0.01 L
# months with loaded expense (run sheet step 0.4; pinned to the CSV by a test)
EXPECTED_EXPENSE_MONTHS = ("2026-04", "2026-05", "2026-06", "2026-07", "2026-08")
RUN_CM2_CASES = (2, 3, 4, 5, 6, 7, 8, 9)    # Case 1 ("no expense rows") is superseded since #229
ROW_IDS = ("1", "2", "3", "4", "5", "6", "7a", "7b", "8", "9", "10")
REQUIRED_PASS = ("1", "2", "4", "5", "6", "7a", "7b", "8", "9", "10")

# Feeds step 0.5 of the run sheet and the Case 3 / Case 6 cross-checks.
PREFLIGHT_DAX = """EVALUATE
ROW (
    "RowsLoaded",     COUNTROWS ( 'PL Expense Input' ),
    "ExpenseLoaded",  [Total Expense Amount Loaded],
    "UnmappedRows",   [Unmapped Chain Or Customer Rows],
    "UnmappedAmount", [Total P&L Expense (Unmapped)],
    "MappedAmount",   [Total P&L Expense (Mapped)]
)"""


class EvidenceRefused(Exception):
    """Raised instead of writing B5 evidence that was not measured on a live engine."""


@dataclass
class RowResult:
    id: str
    status: str            # PASS | FAIL | NOT_EXERCISED | NOT_RUN
    actual: str


# ---------------------------------------------------------------------------------------
# 1. query extraction
# ---------------------------------------------------------------------------------------
_CASE_HDR = re.compile(r"^// CASE (\d+)\b")


def parse_case_file(text: str) -> dict[int, list[str]]:
    """{case number: [EVALUATE block, ...]}. A block starts at a line beginning with
    EVALUATE and ends at the next column-0 comment, EVALUATE, or end of file."""
    cases: dict[int, list[str]] = {}
    case, block = None, None

    def close():
        nonlocal block
        if block is not None and case is not None:
            body = "\n".join(block).rstrip()
            if body:
                cases.setdefault(case, []).append(body)
        block = None

    for line in text.replace("\r\n", "\n").split("\n"):
        m = _CASE_HDR.match(line)
        if m:
            close()
            case = int(m.group(1))
        elif line.startswith("EVALUATE") and case is not None:
            close()
            block = [line]
        elif line.startswith("//"):
            close()
        elif block is not None:
            block.append(line)
    close()
    return cases


def collect_queries(root: Path = ROOT) -> dict[str, str]:
    q = {"preflight:1": PREFLIGHT_DAX}
    cm2 = parse_case_file((root / "tests/powerbi/cm2_availability_cases.dax").read_text(encoding="utf-8"))
    for n in RUN_CM2_CASES:
        for i, b in enumerate(cm2.get(n, []), 1):
            q[f"cm2:{n}:{i}"] = b
    rolling = parse_case_file((root / "tests/powerbi/rolling_average_cases.dax").read_text(encoding="utf-8"))
    for n in sorted(rolling):
        for i, b in enumerate(rolling[n], 1):
            q[f"rolling:{n}:{i}"] = b
    return q


# ---------------------------------------------------------------------------------------
# 2. PASS rules (docs/evidence/B5_RUN_SHEET.md)
# ---------------------------------------------------------------------------------------
def _norm_col(c) -> str:
    m = re.search(r"\[([^\]]+)\]\s*$", str(c))
    return m.group(1) if m else str(c).strip()


def table_rows(tbl) -> list[dict]:
    """Result table -> list of {normalised column: value}. None if the table is missing."""
    if tbl is None:
        return None
    cols = [_norm_col(c) for c in tbl.get("columns", [])]
    out = []
    for r in tbl.get("rows", []):
        out.append(dict(zip(cols, r)) if not isinstance(r, dict) else {_norm_col(k): v for k, v in r.items()})
    return out


def _num(v):
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _blank(v) -> bool:
    return v is None or v == ""


def _zero_or_blank(v) -> bool:
    """COUNTROWS over an empty table can come back BLANK: both mean 'none found'."""
    if _blank(v):
        return True
    n = _num(v)
    return n is not None and abs(n) < 1e-9


def _close(a, b, tol=TOL) -> bool:
    return a is not None and b is not None and abs(a - b) <= tol


def _month(v) -> str:
    return str(v)[:7]


def _fmt(v) -> str:
    n = _num(v)
    if v is None:
        return "BLANK"
    return f"{n:,.2f}" if n is not None else str(v)


def _cnt(v) -> str:
    """A count (rows, violations, months): BLANK or a whole number, never '0.00'."""
    n = _num(v)
    return "BLANK" if v is None else (str(int(round(n))) if n is not None else str(v))


def _first(rows):
    return rows[0] if rows else None


def _preflight(cases):
    r = _first(table_rows(cases.get("preflight:1")) or [])
    return r


def _row_case2(cases, pre):
    rows = table_rows(cases.get("cm2:2:1"))
    if rows is None:
        return RowResult("2", "NOT_RUN", "no result for CM2 Case 2")
    if not rows:
        return RowResult("2", "FAIL", "Case 2 returned no rows (nothing measured)")
    fails = [r for r in rows if str(r.get("Check", "")).startswith("FAIL")]
    ok = [r for r in rows if r.get("Check") == "OK"]
    okb = [r for r in rows if r.get("Check") == "OK blank"]
    ok_months = {_month(r.get("MonthStart")) for r in ok}
    actual = f"OK {len(ok)} / OK blank {len(okb)} / FAIL {len(fails)}"
    good = not fails and ok_months == set(EXPECTED_EXPENSE_MONTHS)
    if not good and not fails:
        actual += f"; OK months {sorted(ok_months)} != {sorted(EXPECTED_EXPENSE_MONTHS)}"
    return RowResult("2", "PASS" if good else "FAIL", actual)


def _row_case3(cases, pre):
    if pre is None:
        return RowResult("3", "NOT_RUN", "no preflight result (unmapped-row count unknown)")
    unmapped_rows = _num(pre.get("UnmappedRows")) or 0
    if unmapped_rows == 0:
        return RowResult("3", "NOT_EXERCISED", "NOT_EXERCISED (0 unmapped rows)")
    r = _first(table_rows(cases.get("cm2:3:1")) or [])
    if r is None:
        return RowResult("3", "NOT_RUN", "no result for CM2 Case 3")
    good = (_num(r.get("Unmapped")) or 0) > 0 and _blank(r.get("Mapped")) and _blank(r.get("CM2"))
    return RowResult("3", "PASS" if good else "FAIL",
                     f"Unmapped {_fmt(r.get('Unmapped'))}; Mapped {_fmt(r.get('Mapped'))}; CM2 {_fmt(r.get('CM2'))}"
                     f"; unmapped rows {int(unmapped_rows)}")


def _row_case4(cases, pre):
    rows, viol = table_rows(cases.get("cm2:4:1")), table_rows(cases.get("cm2:4:2"))
    if rows is None or not viol:
        return RowResult("4", "NOT_RUN", "no result for CM2 Case 4")
    v = viol[0].get("Violations")
    bad, with_exp = [], 0
    for r in rows:
        exp, cm2, nsv = _num(r.get("ChainExpense")), _num(r.get("ChainCM2")), _num(r.get("NSV"))
        if exp is None:
            if cm2 is not None:
                bad.append(f"{r.get('Chain')}: CM2 shown without expense")
        else:
            with_exp += 1
            if not _close(cm2, None if nsv is None else nsv - exp):
                bad.append(f"{r.get('Chain')}: CM2 {cm2} != NSV {nsv} - expense {exp}")
    good = _zero_or_blank(v) and not bad and with_exp >= 1
    actual = f"Violations {_cnt(v)}; {with_exp} chain(s) with expense checked"
    if bad:
        actual += "; " + "; ".join(bad[:3])
    if with_exp == 0:
        actual += "; no chain with expense, nothing to spot-check"
    return RowResult("4", "PASS" if good else "FAIL", actual)


def _row_case5(cases, pre):
    det, leak = table_rows(cases.get("cm2:5:1")), table_rows(cases.get("cm2:5:2"))
    if det is None or not leak:
        return RowResult("5", "NOT_RUN", "no result for CM2 Case 5")
    lv = leak[0].get("Leak")
    mism = [r for r in det if not _close(_num(r.get("ChainExpense")) or 0.0,
                                         _num(r.get("MonthRowsExpense")) or 0.0, 1e-4)]
    good = _zero_or_blank(lv) and not mism and len(det) >= 1
    actual = f"Leak {_cnt(lv)}; {len(det)} chain x month row(s) compared"
    if mism:
        actual += f"; {len(mism)} row(s) disagree"
    if not det:
        actual += "; detail table empty, nothing measured"
    return RowResult("5", "PASS" if good else "FAIL", actual)


def _row_case6(cases, pre):
    rows = table_rows(cases.get("cm2:6:1"))
    if rows is None or pre is None:
        return RowResult("6", "NOT_RUN", "no result for CM2 Case 6 (or preflight)")
    loaded = _num(pre.get("ExpenseLoaded"))
    unmapped_rows = _num(pre.get("UnmappedRows")) or 0
    unmapped_amt = (_num(pre.get("UnmappedAmount")) or 0.0) if unmapped_rows else 0.0
    expected = None if loaded is None else loaded - unmapped_amt
    fy27 = [r for r in rows if str(r.get("FY Year")) == FY27]
    fy26 = [r for r in rows if str(r.get("FY Year")) == FY26]
    fy26_ok = all(_blank(r.get("Expense")) and _blank(r.get("CM2")) for r in fy26)   # absent row = all BLANK
    fy27_ok = len(fy27) == 1 and _close(_num(fy27[0].get("Expense")), expected)
    actual = (f"FY27 Expense {_fmt(fy27[0].get('Expense')) if fy27 else 'missing'} (expected {_fmt(expected)}); "
              f"FY26 " + ("row not returned (all BLANK)" if not fy26 else
                          f"Expense {_fmt(fy26[0].get('Expense'))}, CM2 {_fmt(fy26[0].get('CM2'))}"))
    return RowResult("6", "PASS" if (fy26_ok and fy27_ok) else "FAIL", actual)


def _row_pair(cases, rid, key, col):
    rows = table_rows(cases.get(key))
    if not rows:
        return RowResult(rid, "NOT_RUN", f"no result for {key}")
    v = rows[0].get(col)
    return RowResult(rid, "PASS" if _zero_or_blank(v) else "FAIL", f"{col} {_cnt(v)}")


def _row_case8(cases, pre):
    return _row_pair(cases, "8", "cm2:8:1", "Violations")


def _row_rolling(cases, pre):
    r1 = _first(table_rows(cases.get("rolling:1:1")) or [])
    r2 = _first(table_rows(cases.get("rolling:2:1")) or [])
    r3 = _first(table_rows(cases.get("rolling:3:1")) or [])
    if r1 is None or r2 is None or r3 is None:
        missing = [n for n, r in (("CASE 1", r1), ("CASE 2", r2), ("CASE 3", r3)) if r is None]
        return RowResult("9", "NOT_RUN", "no result for rolling " + ", ".join(missing))
    c1 = (_num(r1.get("Months")) or 0) > 0 and _zero_or_blank(r1.get("Mismatches"))
    c2 = _blank(r2.get("L3M")) and _blank(r2.get("L6M")) and not _blank(r2.get("FirstMonth"))
    c3 = _num(r3.get("L3M")) is not None and _close(_num(r3.get("L3M")), _num(r3.get("Expected")))
    actual = (f"Mismatches {_cnt(r1.get('Mismatches'))} over "
              f"{_cnt(r1.get('Months'))} months; CASE 2 L3M {_fmt(r2.get('L3M'))}, L6M {_fmt(r2.get('L6M'))}; "
              f"CASE 3 L3M {_fmt(r3.get('L3M'))} vs Expected {_fmt(r3.get('Expected'))}")
    return RowResult("9", "PASS" if (c1 and c2 and c3) else "FAIL", actual)


def _row_case9(cases, pre):
    rows = table_rows(cases.get("cm2:9:1"))
    if rows is None:
        return RowResult("10", "NOT_RUN", "no result for CM2 Case 9")
    by = {str(r.get("Scope")): r for r in rows}
    need = ("No FY filter", "FY27", "FY26")
    if any(k not in by for k in need):
        return RowResult("10", "FAIL", "missing scope row(s): " + ", ".join(k for k in need if k not in by))
    withheld = lambda r: (_num(r.get("Comparable")) == 0 and _blank(r.get("ExpensePct"))   # noqa: E731
                          and _blank(r.get("CM2")) and _blank(r.get("CM2Pct")))
    nf, a, b = by["No FY filter"], by["FY27"], by["FY26"]
    fy27_ok = (_num(a.get("Comparable")) == 1 and not _blank(a.get("ExpensePct")) and not _blank(a.get("CM2Pct"))
               and _close(_num(a.get("CM2")),
                          None if _num(a.get("NSV")) is None or _num(a.get("Expense")) is None
                          else _num(a.get("NSV")) - _num(a.get("Expense"))))
    fy26_ok = withheld(b) and _blank(b.get("Expense"))
    parts = {"No FY filter": withheld(nf), "FY27": fy27_ok, "FY26": fy26_ok}
    actual = (f"No FY: Comparable {_cnt(nf.get('Comparable'))}, CM2 {_fmt(nf.get('CM2'))}, CM2% {_fmt(nf.get('CM2Pct'))}, "
              f"Expense% {_fmt(nf.get('ExpensePct'))}; FY27: Comparable {_cnt(a.get('Comparable'))}, "
              f"CM2 {_fmt(a.get('CM2'))} (NSV-Expense {_fmt((_num(a.get('NSV')) or 0) - (_num(a.get('Expense')) or 0))}); "
              f"FY26: Comparable {_cnt(b.get('Comparable'))}, Expense {_fmt(b.get('Expense'))}, CM2 {_fmt(b.get('CM2'))}")
    if not all(parts.values()):
        actual += "; failing: " + ", ".join(k for k, v in parts.items() if not v)
    return RowResult("10", "PASS" if all(parts.values()) else "FAIL", actual)


def evaluate_all(doc: dict, manual_fy_failures: int | None = None, attested_by: str | None = None) -> dict[str, RowResult]:
    """Apply the run sheet's PASS rules to doc['cases']; returns {row id: RowResult}."""
    cases = doc.get("cases", {})
    pre = _preflight(cases)
    out: dict[str, RowResult] = {}
    for fn in (_row_case2, _row_case3, _row_case4, _row_case5, _row_case6):
        r = fn(cases, pre)
        out[r.id] = r
    out["7a"] = _row_pair(cases, "7a", "cm2:7:1", "BrandLeak")
    out["7b"] = _row_pair(cases, "7b", "cm2:7:1", "CategoryLeak")
    for fn in (_row_case8, _row_rolling, _row_case9):
        r = fn(cases, pre)
        out[r.id] = r
    if manual_fy_failures is None:
        out["1"] = RowResult("1", "NOT_RUN", "NOT_RUN (Power Query M cannot be run through Analysis Services; "
                                             "paste tests/powerbi/pq39_fy_parser_cases.pq in Desktop)")
    else:
        if not attested_by:
            raise EvidenceRefused("a manual FY-parser result needs --attested-by: who ran it in Desktop?")
        out["1"] = RowResult("1", "PASS" if manual_fy_failures == 0 else "FAIL",
                             f"manual entry (attested by {attested_by}): Failures = {manual_fy_failures} rows")
    return {k: out[k] for k in ROW_IDS}


# ---------------------------------------------------------------------------------------
# 3. safeguards + rendering
# ---------------------------------------------------------------------------------------
def _canon_hash(cases) -> str:
    return hashlib.sha256(json.dumps(cases, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _norm_q(t: str) -> str:
    return "\n".join(l.rstrip() for l in t.replace("\r\n", "\n").strip().split("\n"))


def validate_live(doc: dict, *, allow_dirty: bool = False, expect_sha: str | None = None) -> None:
    meta = doc.get("meta") or {}
    if meta.get("source") != LIVE_SOURCE:
        raise EvidenceRefused(f"meta.source is {meta.get('source')!r}, not {LIVE_SOURCE!r}: "
                              "B5 evidence can only come from a live Analysis Services run")
    for k in ("database", "server_version", "git_sha", "desktop_version", "model_file", "utc"):
        if not isinstance(meta.get(k), str) or not meta[k].strip():
            raise EvidenceRefused(f"live metadata is missing {k!r}")
    for k in ("port", "measure_count"):
        if not isinstance(meta.get(k), int) or isinstance(meta.get(k), bool) or meta[k] <= 0:
            raise EvidenceRefused(f"live metadata {k!r} must be a positive integer")
    if not re.match(r"\d{4}-\d{2}-\d{2}", meta["utc"]):
        raise EvidenceRefused("meta.utc is not an ISO timestamp")
    if meta.get("git_dirty") and not allow_dirty:
        raise EvidenceRefused("the repo working tree was dirty during the run; re-run on a clean checkout "
                              "of the frozen SHA (or pass --allow-dirty and accept it is recorded)")
    if expect_sha and not (meta["git_sha"].startswith(expect_sha) or expect_sha.startswith(meta["git_sha"])):
        raise EvidenceRefused(f"run SHA {meta['git_sha']} != expected frozen SHA {expect_sha}")
    repo_q = collect_queries()
    ran = doc.get("queries") or {}
    if set(ran) - set(repo_q):
        raise EvidenceRefused("results contain queries that are not in the governed case files: "
                              + ", ".join(sorted(set(ran) - set(repo_q))))
    for k, text in ran.items():
        if _norm_q(text) != _norm_q(repo_q[k]):
            raise EvidenceRefused(f"query {k} was modified: it differs from the governed case file")
    extra = set(doc.get("cases", {})) - set(repo_q)
    if extra:
        raise EvidenceRefused("results contain unknown result keys: " + ", ".join(sorted(extra)))


def _template_rows(template: str) -> dict[str, list[str]]:
    rows = {}
    for line in template.split("\n"):
        m = re.match(r"^\| (\d+[ab]?) \|", line)
        if m and line.count("|") == 7:
            rows[m.group(1)] = [c.strip() for c in line.strip().strip("|").split("|")]
    return rows


def _verdict(rows: dict[str, RowResult]) -> str:
    fail = [r for r in ROW_IDS if rows[r].status == "FAIL"]
    notrun = [r for r in ROW_IDS if rows[r].status == "NOT_RUN"]
    if fail:
        return f"OPEN — FAIL on row(s) {', '.join(fail)}; B5 is not CLEARED. Root-cause; never edit the expectation."
    if notrun:
        return f"OPEN — NOT_RUN: row(s) {', '.join(notrun)}; B5 is not CLEARED."
    return ("OPEN — every measured row PASS; screenshots not yet attached. A human changes this to CLEARED "
            "after attaching one screenshot per step (run sheet).")


def _build(doc: dict, rows: dict[str, RowResult], *, label: str, raw_sha256: str, run_by: str | None,
           refreshed: bool, allow_dirty: bool) -> str:
    meta = doc.get("meta") or {}
    cases = doc.get("cases", {})
    pre = _preflight(cases) or {}
    template = TEMPLATE.read_text(encoding="utf-8")
    date = str(meta.get("utc", ""))[:10] or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    trows = _template_rows(template)
    out = []
    body = template.split("\n")
    # title + intro replaced: a generated file has no unfilled <…> placeholders
    title = f"# B5 Power BI Desktop evidence — {date}" + (" — TEST_FIXTURE (NOT B5 EVIDENCE)" if label == "fixture" else "")
    header = {"Date run": date, "Run by": run_by or "NOT_ENTERED",
              "`main` commit (git SHA)": str(meta.get("git_sha", "NOT_RECORDED")),
              "Power BI Desktop version": str(meta.get("desktop_version", "NOT_RECORDED")),
              "Model file": str(meta.get("model_file", "NOT_RECORDED")),
              "Refreshed before the run": "yes (attested by the person running the script)" if refreshed else "NOT_ATTESTED",
              "`[Total Expense Amount Loaded]`": f"{_fmt(pre.get('ExpenseLoaded'))} (expected ₹1,274.71 L)",
              "`[Unmapped Chain Or Customer Rows]`": "NOT_RUN" if not pre else _cnt(pre.get("UnmappedRows"))}
    skip_intro = False
    for line in body:
        if line.startswith("# B5 Power BI Desktop evidence"):
            out.append(title)
            out.append("")
            if label == "fixture":
                out.append("**TEST_FIXTURE — synthetic result tables used to test the generator. NOT B5 EVIDENCE.**")
            else:
                out.append("Generated by `scripts/b5_evidence.py` from a live Power BI Desktop run "
                           "(`scripts/B5-DesktopRunner.ps1`). Procedure and PASS rules: `B5_RUN_SHEET.md`. "
                           "Rows the script could not measure say `NOT_RUN`; the evidence-reference column is for "
                           "the screenshot of each step, attached by the person who ran it.")
            out.append("")
            skip_intro = True
            continue
        if skip_intro:
            if line.startswith("| Field"):
                skip_intro = False
            else:
                continue
        m = re.match(r"^\| (.+?) \| (.+) \|$", line)
        if m and m.group(1) in header:
            out.append(f"| {m.group(1)} | {header[m.group(1)]} |")
            continue
        rid = re.match(r"^\| (\d+[ab]?) \|", line)
        if rid and rid.group(1) in rows and line.count("|") == 7:
            cells = trows[rid.group(1)]
            r = rows[rid.group(1)]
            out.append(f"| {cells[0]} | {cells[1]} | {cells[2]} | {r.actual} | {r.status} | `<attach screenshot>` |")
            continue
        if line.startswith("**B5 verdict:**"):
            out.append(f"**B5 verdict:** {_verdict(rows)}")
            continue
        out.append(line)
    text = "\n".join(out).rstrip("\n") + "\n"
    prov = ["", "## Measurement provenance", ""]
    if label == "fixture":
        prov.append("- mode: **TEST_FIXTURE**. Nothing here was measured on a model.")
    else:
        prov += [f"- mode: LIVE (`{LIVE_SOURCE}`), measured by `scripts/B5-DesktopRunner.ps1` + `scripts/b5_evidence.py`",
                 f"- local Analysis Services port: {meta.get('port')}; database: {meta.get('database')}; "
                 f"server version: {meta.get('server_version')}; model measures: {meta.get('measure_count')}",
                 f"- run at (UTC): {meta.get('utc')}; repo SHA at run: {meta.get('git_sha')}"
                 + ("; **working tree was DIRTY** (accepted with --allow-dirty)" if meta.get("git_dirty") else "; working tree clean"),
                 "- queries: identical to the governed `tests/powerbi/*_cases.dax` blocks (checked before writing)"]
    errs = doc.get("errors") or {}
    if errs:
        prov.append("- query errors (those rows read NOT_RUN): " + "; ".join(f"{k}: {str(v)[:160]}" for k, v in errs.items()))
    prov += [f"- raw results.json sha256: `{raw_sha256}`",
             f"- canonical results sha256: `{_canon_hash(cases)}` (the raw file stays on the runner's machine; "
             "keep it with the screenshots)",
             "- manual entries: " + ("; ".join(f"row {k}: {v.actual}" for k, v in rows.items() if "manual entry" in v.actual)
                                    or "none"),
             "- screenshots: one per step, attached by the runner; this script cannot attach them."]
    return text + "\n".join(prov) + "\n"


def render_fixture(doc: dict, **kw) -> str:
    return _build(doc, evaluate_all(doc), label="fixture", raw_sha256="n/a (fixture)", run_by=None,
                  refreshed=False, allow_dirty=False)


def write_fixture(doc: dict, path: Path) -> Path:
    """Fixture rendering for tests only: never into docs/evidence, never named like real evidence."""
    path = Path(path).resolve()
    ev = EVIDENCE_DIR.resolve()
    if path.parent == ev or ev in path.parents or path.name.startswith("B5_powerbi_runtime_"):
        raise EvidenceRefused("fixture output may not be written into docs/evidence or named B5_powerbi_runtime_*")
    path.write_text(render_fixture(doc), encoding="utf-8")
    return path


def write_evidence(doc: dict, *, raw_sha256: str, evidence_dir: Path | None = None, run_by: str | None = None,
                   refreshed: bool = False, fy_parser_failures: int | None = None, attested_by: str | None = None,
                   allow_dirty: bool = False, expect_sha: str | None = None) -> Path:
    validate_live(doc, allow_dirty=allow_dirty, expect_sha=expect_sha)
    rows = evaluate_all(doc, manual_fy_failures=fy_parser_failures, attested_by=attested_by)
    text = _build(doc, rows, label="live", raw_sha256=raw_sha256, run_by=run_by, refreshed=refreshed,
                  allow_dirty=allow_dirty)
    d = Path(evidence_dir) if evidence_dir is not None else EVIDENCE_DIR
    path = d / f"B5_powerbi_runtime_{doc['meta']['utc'][:10]}.md"
    if path.exists():
        raise EvidenceRefused(f"{path.name} already exists; evidence files are durable and are not overwritten")
    path.write_text(text, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------------------
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--emit-queries", metavar="PATH", help="write the governed EVALUATE blocks as JSON and exit")
    ap.add_argument("--results", metavar="PATH", help="results.json written by B5-DesktopRunner.ps1")
    ap.add_argument("--out-dir", metavar="DIR", help="default: docs/evidence")
    ap.add_argument("--run-by")
    ap.add_argument("--refreshed", action="store_true", help="attest that Home > Refresh was run before the cases")
    ap.add_argument("--fy-parser-failures", type=int, metavar="N", help="manual entry: rows in the FY parser 'Failures' step")
    ap.add_argument("--attested-by", metavar="NAME")
    ap.add_argument("--allow-dirty", action="store_true")
    ap.add_argument("--expect-sha", metavar="SHA", help="refuse unless the run SHA matches the frozen SHA")
    a = ap.parse_args(argv)

    if a.emit_queries:
        Path(a.emit_queries).write_text(json.dumps({"queries": collect_queries()}, indent=2), encoding="utf-8")
        print(f"wrote {len(collect_queries())} governed queries to {a.emit_queries}")
        return 0
    if not a.results:
        ap.error("--results or --emit-queries is required")
    try:
        raw = Path(a.results).read_bytes()
        doc = json.loads(raw.decode("utf-8-sig"))
    except (OSError, ValueError) as e:
        print(f"cannot read results: {e}", file=sys.stderr)
        return 4
    try:
        path = write_evidence(doc, raw_sha256=hashlib.sha256(raw).hexdigest(),
                              evidence_dir=Path(a.out_dir) if a.out_dir else None, run_by=a.run_by,
                              refreshed=a.refreshed, fy_parser_failures=a.fy_parser_failures,
                              attested_by=a.attested_by, allow_dirty=a.allow_dirty, expect_sha=a.expect_sha)
    except EvidenceRefused as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return 3
    rows = evaluate_all(doc, manual_fy_failures=a.fy_parser_failures, attested_by=a.attested_by)
    print(f"wrote {path}")
    for rid in ROW_IDS:
        print(f"  row {rid:>3}: {rows[rid].status:<14} {rows[rid].actual}")
    ok = all(rows[r].status == "PASS" for r in REQUIRED_PASS) and rows["3"].status in ("PASS", "NOT_EXERCISED")
    print("ALL REQUIRED ROWS PASS - attach screenshots, then a human sets the verdict to CLEARED." if ok
          else "NOT ALL ROWS PASS - B5 stays OPEN.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
