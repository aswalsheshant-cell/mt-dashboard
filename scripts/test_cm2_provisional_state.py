"""Regression test for _cm2_provisional_state() (scripts/build_dashboard_data.py).

Root cause this closes: patch_cm2_provisional.py has imported this function
since it was first committed (b61d84e), but the function was never actually
defined anywhere in build_dashboard_data.py's history -- confirmed via
`git log -S"_cm2_provisional_state"` returning no hits for that file. That
ImportError blocked collection of the entire scripts/test_json_serialization.py
suite (12 tests, none of them CM2-specific -- they test NaN/Infinity JSON
serialization safety across qc_dashboard/sync_data_js/ci_validate_datajs).

This is a data-presence/self-certification disclosure state, not a CM2
formula -- these tests never assert or change a CM2 amount, and always
confirm formula_status never claims Finance approval, since
docs/BUSINESS_LOGIC_REGISTRY.md's BL-16 found the one candidate formula
config self-certified by "MT Automation", not real Finance sign-off.
"""
import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
bd = importlib.import_module("build_dashboard_data")


def _never_claims_approval(state):
    assert state["formula_status"] != "APPROVED"
    assert "APPROVED" not in state["formula_status"]
    assert state["provisional"] is True


def test_known_configured_data():
    rows = [{"Expense Amount (INR Lakh)": "10.0", "Month": "April", "FY": "FY25-26", "Remarks": ""}]
    state = bd._cm2_provisional_state(rows)
    assert state["data_quality"] == "KNOWN_CONFIGURED_DATA"
    assert state["example_data_only"] is False
    _never_claims_approval(state)


def test_known_provisional_data():
    rows = [{"Expense Amount (INR Lakh)": "10.0", "Month": "April", "FY": "FY25-26",
             "Remarks": "PROVISIONAL -- awaiting invoice"}]
    state = bd._cm2_provisional_state(rows)
    assert state["data_quality"] == "KNOWN_PROVISIONAL_DATA"
    _never_claims_approval(state)


def test_missing_data_is_empty_data():
    # load_pl_expense_input() collapses "file missing" and "file has only
    # EXAMPLE ROW rows" into the same [] -- this function cannot recover
    # that distinction, by design (see the function's own docstring).
    state = bd._cm2_provisional_state([])
    assert state["data_quality"] == "EMPTY_DATA"
    assert state["example_data_only"] is True
    _never_claims_approval(state)


def test_empty_data():
    state = bd._cm2_provisional_state([])
    assert state["data_quality"] == "EMPTY_DATA"
    _never_claims_approval(state)


def test_invalid_data_no_parseable_amount():
    rows = [{"Expense Amount (INR Lakh)": "not-a-number", "Month": "April", "FY": "FY25-26"}]
    state = bd._cm2_provisional_state(rows)
    assert state["data_quality"] == "INVALID_DATA"
    _never_claims_approval(state)


def test_invalid_data_non_list_input_fails_closed():
    state = bd._cm2_provisional_state("not-a-list")
    assert state["data_quality"] == "INVALID_DATA"
    _never_claims_approval(state)


def test_unknown_period():
    rows = [{"Expense Amount (INR Lakh)": "10.0", "Month": "", "FY": ""}]
    state = bd._cm2_provisional_state(rows)
    assert state["data_quality"] == "UNKNOWN_PERIOD"
    _never_claims_approval(state)


def test_formula_status_never_claims_finance_approval_even_with_self_certified_path():
    # Even with real expense rows AND a formula_path pointing at the
    # self-certified config, this must never report an approved status.
    self_certified_path = (
        Path(__file__).resolve().parent.parent
        / "PowerBI" / "Reference" / "CM2_Provisional" / "config" / "cm2_formula.csv"
    )
    rows = [{"Expense Amount (INR Lakh)": "10.0", "Month": "April", "FY": "FY25-26"}]
    state = bd._cm2_provisional_state(rows, formula_path=str(self_certified_path))
    _never_claims_approval(state)


def test_returns_all_keys_patch_cm2_provisional_expects():
    state = bd._cm2_provisional_state([])
    expected_keys = {"formula_status", "provisional", "provisional_label",
                      "provisional_reasons", "example_data_only"}
    assert expected_keys.issubset(state.keys())


def test_patch_cm2_provisional_module_imports_successfully():
    # The actual reported defect: this must not raise ImportError any more.
    importlib.import_module("patch_cm2_provisional")
