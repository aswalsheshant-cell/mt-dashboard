"""Source contract tests for the canonical engine's two inputs (Primary
detail_records, Offtake by_chain), per contracts/*.yaml.

First proves the contracts hold against the real certified dashboard/data.js
(with one pinned, documented known exception -- see primary_contract.yaml's
known_exceptions note), then proves each validator actually catches the
defect it claims to catch, via synthetic mutated data."""
import copy

from canonical import contract_validation as cv


def test_primary_contract_has_exactly_one_known_category_null_exception(data):
    """Pinned count, not a blanket 'ignore nulls' allowance -- if a SECOND,
    different row starts violating this contract, this test must fail so
    the new finding gets reviewed, not silently absorbed."""
    problems = cv.validate_primary_contract(data)
    assert len(problems) == 1, f"expected exactly the one documented FOC-line exception, got: {problems}"
    assert "Category" in problems[0]


def test_offtake_contract_is_clean(data):
    problems = cv.validate_offtake_contract(data)
    assert problems == []


def test_channel_contract_passes_against_real_data(data):
    assert cv.validate_channel_contract(data) == []


def test_chain_contract_passes_against_real_data(data):
    assert cv.validate_chain_contract(data) == []


def test_channel_contract_rejects_an_unrecognized_channel(data):
    mutated = copy.deepcopy(data)
    mutated["detail_records"] = [dict(mutated["detail_records"][0], Channel="NOT_A_REAL_CHANNEL")]
    problems = cv.validate_channel_contract(mutated)
    assert problems
    assert "NOT_A_REAL_CHANNEL" in problems[0]


def test_chain_contract_flags_null_chain_on_primary_rows():
    fake_data = {"detail_records": [{"Chain": None}], "offtake": {"by_chain": []}}
    problems = cv.validate_chain_contract(fake_data)
    assert problems
    assert "detail_records" in problems[0]


def test_chain_contract_flags_empty_chain_name_on_offtake_rows():
    fake_data = {"detail_records": [], "offtake": {"by_chain": [{"name": "  "}]}}
    problems = cv.validate_chain_contract(fake_data)
    assert problems
    assert "by_chain" in problems[0]


def test_primary_contract_flags_a_full_row_duplicate():
    row = {
        "Month": "April", "FY": "FY27", "Channel": "MT", "Zone": "West",
        "State": "Maharashtra", "Chain": "DMart", "Brand": "The Derma Co",
        "Category": "Face", "SubCategory": "Face Cleanser", "Range": "X",
        "PackSize": "100.0", "Article": "Some Article", "EAN": "123",
        "NSV": 10.0, "MRP": 20.0, "Qty": 5,
    }
    fake_data = {"detail_records": [row, dict(row)], "offtake": {"by_chain": []}}
    problems = cv.validate_primary_contract(fake_data)
    assert any("duplicate" in p for p in problems)


def test_primary_contract_flags_nan_nsv():
    row = {
        "Month": "April", "FY": "FY27", "Channel": "MT", "Zone": "West",
        "State": "Maharashtra", "Chain": "DMart", "Brand": "The Derma Co",
        "Category": "Face", "SubCategory": "Face Cleanser", "Range": "X",
        "PackSize": "100.0", "Article": "Some Article", "EAN": "123",
        "NSV": float("nan"), "MRP": 20.0, "Qty": 5,
    }
    problems = cv.validate_primary_contract({"detail_records": [row], "offtake": {"by_chain": []}})
    assert any("NaN" in p for p in problems)


def test_primary_contract_flags_bad_fy_pattern():
    row = {
        "Month": "April", "FY": "twenty-twenty-seven", "Channel": "MT", "Zone": "West",
        "State": "Maharashtra", "Chain": "DMart", "Brand": "The Derma Co",
        "Category": "Face", "SubCategory": "Face Cleanser", "Range": "X",
        "PackSize": "100.0", "Article": "Some Article", "EAN": "123",
        "NSV": 10.0, "MRP": 20.0, "Qty": 5,
    }
    problems = cv.validate_primary_contract({"detail_records": [row], "offtake": {"by_chain": []}})
    assert any("does not match pattern" in p for p in problems)


def test_offtake_contract_flags_duplicate_chain_name():
    fake_data = {
        "detail_records": [],
        "offtake": {"by_chain": [{"name": "DMart", "fy27": 10.0}, {"name": "DMart", "fy27": 20.0}]},
    }
    problems = cv.validate_offtake_contract(fake_data)
    assert any("duplicate chain name" in p for p in problems)


def test_offtake_contract_flags_negative_fy_value():
    fake_data = {"detail_records": [], "offtake": {"by_chain": [{"name": "DMart", "fy27": -5.0}]}}
    problems = cv.validate_offtake_contract(fake_data)
    assert any("negative" in p for p in problems)


def test_offtake_contract_flags_infinite_fy_value():
    fake_data = {"detail_records": [], "offtake": {"by_chain": [{"name": "DMart", "fy27": float("inf")}]}}
    problems = cv.validate_offtake_contract(fake_data)
    assert any("Infinity" in p for p in problems)


def test_offtake_contract_ignores_value_and_total_fields():
    """'value'/'total' are legitimate non-FY-keyed fields to have on the
    row -- the contract must not flag them just for existing (only for
    being misused as an FY substitute, which is facts.py's job to prevent,
    not this contract's)."""
    fake_data = {
        "detail_records": [],
        "offtake": {"by_chain": [{"name": "DMart", "fy27": 10.0, "value": 99999.0, "total": -5.0}]},
    }
    problems = cv.validate_offtake_contract(fake_data)
    assert problems == []
