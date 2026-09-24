"""Canonical Financial Truth Gate -- structural checks for the canonical
engine (scripts/canonical/) that go beyond "do the unit tests pass."

This script is the CI entrypoint for the "Canonical Financial Truth Gate"
workflow (.github/workflows/canonical-financial-truth-gate.yml). It does
NOT replace tests/canonical/ -- pytest still runs separately and is one of
this gate's required jobs. This script checks things a green pytest run
does not, by itself, prove:

  - every reconciliation row is NaN/Infinity-free (not just tested for one
    input, but scanned across the actual full shadow report)
  - every APPROVED_GOVERNED row traces to a real governance.py registry
    entry (an "unapproved GOVERNED exception" is a caller inventing a
    status the registry never reviewed -- this must be structurally
    impossible, not just usually true)
  - no canonical metric function (outside existing.py, which deliberately
    replicates the OLD, buggy production JS for comparison) reintroduces
    the exact fallback pattern KI-OFFTAKE-001 exists to fix: reaching a
    non-FY-keyed '.value'/'total' aggregate field as a stand-in for "no
    data this FY"
  - no canonical file outside units.py performs its own Lakh<->Crore
    conversion (ADR-006: conversion is presentation-only, done in exactly
    one place)
  - the ADR-003 availability report has a real status (and, when
    NOT_AVAILABLE, a reason) for all three Reliance Brand Counter measures

Each check_* function returns a list of problem strings (empty = pass).
`main()` runs the requested subset (or all) and exits 1 if any problem was
found, printing every problem so a CI log shows exactly what to fix.

Usage:
  python3 scripts/canonical_gate_checks.py                  # run everything
  python3 scripts/canonical_gate_checks.py reconciliation   # run one check
  python3 scripts/canonical_gate_checks.py --list           # list check names
"""
import math
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CANONICAL_DIR = REPO_ROOT / "scripts" / "canonical"
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from canonical import availability, contract_validation, facts, governance, reconcile  # noqa: E402
from canonical.policies import NotAvailable  # noqa: E402
from canonical.shadow_report import build_report  # noqa: E402
from canonical.units import round_lakh  # noqa: E402


def _is_bad_float(v):
    if v is None or isinstance(v, NotAvailable):
        return False
    try:
        f = float(v)
    except (TypeError, ValueError):
        return False
    return math.isnan(f) or math.isinf(f)


def check_reconciliation():
    """Reconciliation FAIL / UNKNOWN must be zero -- these are exactly the
    two states the gate is not allowed to let through (an unexplained
    variance, or an unreviewed exception claim)."""
    problems = []
    data = facts.load_datajs()
    rows = build_report(data)
    summary = reconcile.summarize(rows)
    if summary["fail"] != 0:
        fails = [r for r in rows if r.result == "FAIL"]
        for r in fails:
            problems.append(
                f"FAIL: {r.metric}/{r.scope}: existing={r.existing_value} "
                f"canonical={r.canonical_value} ({r.reason})")
    if summary["unknown"] != 0:
        unknowns = [r for r in rows if r.result == "UNKNOWN"]
        for r in unknowns:
            problems.append(f"UNKNOWN: {r.metric}/{r.scope}: {r.reason}")
    if summary["clean_population_pct"] != 100.0:
        problems.append(
            f"clean_population_pct={summary['clean_population_pct']} (must be 100.0)")
    return problems


def check_numeric_safety():
    """No NaN / Infinity anywhere in the actual reconciliation output --
    not just in a unit test's synthetic input."""
    problems = []
    data = facts.load_datajs()
    rows = build_report(data)
    for r in rows:
        for field in ("existing_value", "canonical_value", "variance", "variance_pct"):
            v = getattr(r, field)
            if _is_bad_float(v):
                problems.append(f"{r.metric}/{r.scope}: {field}={v!r} is NaN/Infinity")
    # Regression guard on the one function every metric routes numeric
    # rounding through -- if this ever stops sanitizing NaN/Infinity, every
    # metric function downstream silently inherits the bug.
    if round_lakh(float("nan")) is not None:
        problems.append("units.round_lakh(nan) no longer returns None")
    if round_lakh(float("inf")) is not None:
        problems.append("units.round_lakh(inf) no longer returns None")
    return problems


def check_governance_integrity():
    """Every APPROVED_GOVERNED row must trace to a real, unique, FULLY
    APPROVED registry entry -- an 'unapproved GOVERNED exception' (a result
    of GOVERNED with no matching registry record, OR a matching record that
    was never actually signed off) must be structurally impossible. This is
    the self-approval guard: adding an ApprovedException to governance.py is
    not, by itself, enough to make it fire -- approver/approval_reference/
    approved_at must be populated and approval_status must be exactly
    "APPROVED", or the entry is inert."""
    problems = []
    registry_ids = {e.exception_id for e in governance.APPROVED_EXCEPTIONS}
    if len(registry_ids) != len(governance.APPROVED_EXCEPTIONS):
        problems.append("governance.APPROVED_EXCEPTIONS has duplicate exception_id values")

    required_fields = ["exception_id", "metric", "scope_description", "reason_not_pass",
                        "evidence", "business_impact", "financial_impact", "owner",
                        "approver", "approval_reference", "approved_at", "approval_status",
                        "temporary_or_permanent", "resolution_phase", "release_blocker",
                        "status"]
    for exc in governance.APPROVED_EXCEPTIONS:
        for field in required_fields:
            if not getattr(exc, field, None) and getattr(exc, field, None) != False:  # noqa: E712
                problems.append(f"{exc.exception_id}: missing/empty required field '{field}'")
        if exc.status != "APPROVED_GOVERNED":
            problems.append(f"{exc.exception_id}: status is {exc.status!r}, expected APPROVED_GOVERNED")
        if exc.temporary_or_permanent not in ("TEMPORARY", "PERMANENT"):
            problems.append(f"{exc.exception_id}: temporary_or_permanent={exc.temporary_or_permanent!r} invalid")
        if exc.approval_status != "APPROVED":
            problems.append(f"{exc.exception_id}: approval_status={exc.approval_status!r}, expected APPROVED")
        if not exc.is_fully_approved():
            problems.append(f"{exc.exception_id}: fails the self-approval guard (is_fully_approved() == False) "
                             "-- this entry is in the registry but cannot actually fire")

    data = facts.load_datajs()
    rows = build_report(data)
    for r in rows:
        if r.result != "APPROVED_GOVERNED":
            continue
        if r.exception is None:
            problems.append(f"{r.metric}/{r.scope}: result=APPROVED_GOVERNED but no exception attached")
            continue
        if r.exception.exception_id not in registry_ids:
            problems.append(
                f"{r.metric}/{r.scope}: attached exception_id "
                f"{r.exception.exception_id!r} not in governance.APPROVED_EXCEPTIONS")
    return problems


_FORBIDDEN_FALLBACK_PATTERN = re.compile(r"\.value\b")

# Scoped to the files that actually touch raw data.js fields to compute a
# metric -- facts.py (extraction), primary.py/offtake.py (metric functions).
# existing.py deliberately replicates the OLD production JS (including its
# '.value' fallback bug) so the shadow reconciliation has something real to
# compare against -- that is its documented job, not a regression. governance.py
# /reconcile.py/availability.py never touch a raw data.js field at all (they
# operate on already-computed values passed to them), so they are out of
# scope for this specific check -- checking them only risks flagging their
# own prose *describing* the anti-pattern (e.g. GOV-003's evidence text) as
# if it were a live occurrence of it.
_FALLBACK_CHECK_FILES = ["facts.py", "primary.py", "offtake.py"]


def _strip_docstrings_and_comments(src):
    src = re.sub(r'"""[\s\S]*?"""', "", src)
    src = re.sub(r"#.*", "", src)
    return src


def check_fallback_safety():
    """No canonical metric function outside existing.py may reach a non-FY-
    keyed '.value'/'total' aggregate field -- the exact KI-OFFTAKE-001
    anti-pattern (ch_data.total?.[fyR] ?? ... ?? ch_data.value ?? 0)."""
    problems = []
    for fname in _FALLBACK_CHECK_FILES:
        path = CANONICAL_DIR / fname
        code = _strip_docstrings_and_comments(path.read_text())
        if _FORBIDDEN_FALLBACK_PATTERN.search(code):
            problems.append(
                f"{fname}: matches forbidden fallback pattern '.value' as live code "
                "(a non-FY-keyed aggregate field must never be reached as a stand-in "
                "for 'no data this FY' -- see KI-OFFTAKE-001 / Issue #195)")
    return problems


_UNIT_CONVERSION_PATTERN = re.compile(r"/\s*100(\.0)?\b")


def check_unit_conversion_isolation():
    """Lakh<->Crore conversion (ADR-006) must happen only inside units.py.
    A '/ 100' outside units.py in a canonical metric/reconcile file is
    exactly PR #193 bug #2 (a display site dividing by 100 before crc()'s
    own conversion) reintroduced into the canonical layer."""
    problems = []
    for path in sorted(CANONICAL_DIR.glob("*.py")):
        if path.name in ("units.py", "__init__.py"):
            continue
        if path.name.startswith("test_"):
            continue
        code = _strip_docstrings_and_comments(path.read_text())
        for m in _UNIT_CONVERSION_PATTERN.finditer(code):
            # variance_pct / clean_population_pct are percentage math, not a
            # Lakh->Crore conversion -- allow only inside reconcile.py where
            # that is the documented, sole use.
            if path.name == "reconcile.py":
                continue
            problems.append(f"{path.name}: contains '/ 100'-style division outside units.py")
    return problems


def check_availability_metadata():
    """The ADR-003 availability report must give every one of the three
    Reliance Brand Counter measures a real status, and a reason whenever
    that status is NOT_AVAILABLE -- 'missing availability status' must be
    structurally impossible, not just true today by coincidence."""
    problems = []
    data = facts.load_datajs()
    report = availability.rbc_availability_report(data)
    expected_measures = {"RBC_PRIMARY_NSV", "RBC_OFFTAKE_NSV", "RBC_GAP_NSV"}
    if set(report.keys()) != expected_measures:
        problems.append(f"rbc_availability_report() keys={set(report.keys())}, expected {expected_measures}")
    for measure, entry in report.items():
        status = entry.get("status")
        if status not in ("AVAILABLE", "NOT_AVAILABLE"):
            problems.append(f"{measure}: status={status!r} is not a valid availability status")
        if status == "NOT_AVAILABLE" and not entry.get("reason"):
            problems.append(f"{measure}: status=NOT_AVAILABLE but no reason given")
    if report.get("RBC_PRIMARY_NSV", {}).get("status") != "AVAILABLE":
        problems.append("RBC_PRIMARY_NSV expected AVAILABLE against the certified data.js")
    if report.get("RBC_OFFTAKE_NSV", {}).get("status") != "NOT_AVAILABLE":
        problems.append("RBC_OFFTAKE_NSV expected NOT_AVAILABLE against the certified data.js "
                         "(D.reliance_brand_counters is an empty stub -- see the Phase 1 "
                         "implementation-discovery note in docs/CANONICAL_FINANCIAL_TRUTH_DESIGN.md)")
    return problems


def check_missing_never_becomes_zero():
    """ADR-007 regression guard: the one choke point every FY-keyed metric
    routes through must return NOT_AVAILABLE, never 0, for a genuinely
    absent FY key."""
    from canonical.policies import exact_fy_or_not_available
    problems = []
    result = exact_fy_or_not_available("GATE_CHECK", "FY99", {"FY26": 123.0})
    if not isinstance(result, NotAvailable):
        problems.append("exact_fy_or_not_available() returned a non-NotAvailable value for a missing FY key")
    result_present_null = exact_fy_or_not_available("GATE_CHECK", "FY26", {"FY26": None})
    if not isinstance(result_present_null, NotAvailable):
        problems.append("exact_fy_or_not_available() did not treat a present-but-null FY value as NOT_AVAILABLE")
    return problems


def check_source_contracts():
    """Primary and Offtake source contracts (contracts/primary_contract.yaml,
    contracts/offtake_contract.yaml) must hold against the certified
    dashboard/data.js. One documented exception is pinned and allowed --
    primary_contract.yaml's known_exceptions note (a single FOC/scheme
    adjustment row with no category taxonomy) -- anything beyond that
    exact, already-reviewed finding fails the gate."""
    problems = []
    data = facts.load_datajs()
    primary_problems = contract_validation.validate_primary_contract(data)
    if len(primary_problems) > 1 or (primary_problems and "Category" not in primary_problems[0]):
        problems.extend(f"primary_contract: {p}" for p in primary_problems)
    offtake_problems = contract_validation.validate_offtake_contract(data)
    problems.extend(f"offtake_contract: {p}" for p in offtake_problems)
    return problems


CHECKS = {
    "reconciliation": check_reconciliation,
    "numeric-safety": check_numeric_safety,
    "governance": check_governance_integrity,
    "fallback-safety": check_fallback_safety,
    "unit-isolation": check_unit_conversion_isolation,
    "availability-metadata": check_availability_metadata,
    "missing-never-zero": check_missing_never_becomes_zero,
    "source-contracts": check_source_contracts,
}


def main(argv):
    if "--list" in argv:
        print("\n".join(CHECKS))
        return 0

    names = [a for a in argv if not a.startswith("-")] or list(CHECKS)
    unknown = [n for n in names if n not in CHECKS]
    if unknown:
        print(f"Unknown check(s): {unknown}. Valid: {list(CHECKS)}", file=sys.stderr)
        return 2

    any_problems = False
    for name in names:
        problems = CHECKS[name]()
        if problems:
            any_problems = True
            print(f"FAIL [{name}] ({len(problems)} problem(s)):")
            for p in problems:
                print(f"  - {p}")
        else:
            print(f"PASS [{name}]")

    if any_problems:
        print("\nCanonical Financial Truth Gate: FAIL")
        return 1
    print("\nCanonical Financial Truth Gate: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
