"""Q1 FY27 distributor claims allocated to months on the Finance-approved basis.

Finance (DA), 2026-10-01: A1 = additive with MT Direct DN; A2 = include in
monthly and quarterly CM2. Quarterly Rs 449.77 L stays the ACTUAL figure; the
monthly split uses each chain's Apr/May/Jun distributor-secondary share and is
ALLOCATED_PROVISIONAL. No equal /3 split; a chain with no driver is not spread.
"""
import csv
import importlib.util
import sys
from collections import defaultdict
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("claimalloc", ROOT / "scripts/build_distributor_claim_monthly_allocation.py")
alloc = importlib.util.module_from_spec(spec)
sys.modules["claimalloc"] = alloc
spec.loader.exec_module(alloc)


def rows(path):
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


@pytest.fixture(scope="module")
def out():
    return rows(alloc.OUT)


@pytest.fixture(scope="module")
def seed():
    return rows(alloc.SEED)


def test_committed_file_is_current():
    assert alloc.main(["--check"]) == 0


def test_every_line_reconciles_to_its_q1_claim(out, seed):
    got = defaultdict(float)
    for r in out:
        got[(r["Chain"], r["Expense Head"])] += float(r["Expense Amount (INR Lakh)"])
    assert len(got) == len(seed)
    for s in seed:
        assert abs(got[(s["Chain"], s["Expense Head"])] - float(s["Expense Amount (INR Lakh)"])) < 0.00015


def test_file_total_is_the_q1_total(out, seed):
    total = sum(float(r["Expense Amount (INR Lakh)"]) for r in out)
    assert abs(total - sum(float(s["Expense Amount (INR Lakh)"]) for s in seed)) < 0.0005
    assert abs(total - 449.77) < 0.01


def test_quarterly_seed_untouched(seed):
    # the ACTUAL quarterly figure is not rewritten by the allocation
    assert len(seed) == 32
    assert {s["Quarter"] for s in seed} == {"Q1"}


def test_statuses_and_months(out):
    assert {r["Status"] for r in out} <= {"ALLOCATED_PROVISIONAL", "UNALLOCATED_TIMING"}
    alloc_rows = [r for r in out if r["Status"] == "ALLOCATED_PROVISIONAL"]
    assert {r["Month"] for r in alloc_rows} == {"Apr'26", "May'26", "Jun'26"}
    assert all(r["Basis"] == alloc.BASIS and r["Approval"] == alloc.APPROVAL for r in alloc_rows)


def test_no_equal_thirds_split(out):
    # a flat /3 would give every allocated line identical shares; the driver must not
    shares = {r["Driver Share"] for r in out if r["Status"] == "ALLOCATED_PROVISIONAL"}
    assert "0.333333" not in shares and len(shares) > 3


def test_chain_without_driver_is_not_spread(out):
    spar = [r for r in out if r["Chain"] == "Spar"]
    assert spar and all(r["Status"] == "UNALLOCATED_TIMING" and r["Month"] == "Q1 (no month)" for r in spar)


def test_shares_sum_to_one_per_line(out):
    by = defaultdict(float)
    for r in out:
        if r["Status"] == "ALLOCATED_PROVISIONAL":
            by[(r["Chain"], r["Expense Head"])] += float(r["Driver Share"])
    assert all(abs(v - 1) < 1e-5 for v in by.values())


def test_unallocated_case_is_explicit():
    seed_rows = [{"FY": "FY26-27", "Quarter": "Q1", "Chain": "Nowhere", "Expense Head": "Visibility",
                  "Expense Type": "Fixed", "Expense Amount (INR Lakh)": "3.0", "Source": "t"}]
    r = alloc.allocate(seed_rows, {}, {})
    assert len(r) == 1 and r[0]["Status"] == "UNALLOCATED_TIMING" and r[0]["Expense Amount (INR Lakh)"] == "3.0000"


def test_rounding_residual_keeps_line_exact():
    seed_rows = [{"FY": "FY26-27", "Quarter": "Q1", "Chain": "DMart", "Expense Head": "X", "Expense Type": "Variable",
                  "Expense Amount (INR Lakh)": "10.0", "Source": "t"}]
    k = alloc.driver_key("DMart")
    r = alloc.allocate(seed_rows, {k: {"Apr-2026": 1.0, "May-2026": 1.0, "Jun-2026": 1.0}}, {k: {"DMART"}})
    assert abs(sum(float(x["Expense Amount (INR Lakh)"]) for x in r) - 10.0) < 1e-9


def test_proposed_aliases_are_not_governed_aliases():
    # driver-only aliases must not leak into the governed CHAIN_ALIASES table
    import build_dashboard_data as bdd
    for raw in alloc.PROPOSED_DRIVER_ALIASES:
        assert raw.lower() not in bdd._ALIAS_LOOKUP, f"{raw} is already governed; drop it from the proposal"
    assert "VISHAL" not in alloc.PROPOSED_DRIVER_ALIASES   # ambiguous: see CHAIN_ALIASES comment
