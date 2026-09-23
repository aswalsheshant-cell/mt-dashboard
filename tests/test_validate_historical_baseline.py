"""Regression coverage for scripts/validate_historical_baseline.py.

Proves the Historical Baseline Integrity check now reads live canonical
fields (primary.fy_tags / offtake.fy_tags / offtake.secondary_total_fy25 /
offtake.secondary_months_fy25) instead of the deprecated top-level
`metadata.coverage.fiscal_years` key that PR #180 (FM-05) removes -- and that
the deprecated key's presence or absence never changes the verdict either way
(CASE 7 / CASE 8 below).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from validate_historical_baseline import check_historical_baseline  # noqa: E402


def _valid_payload():
    """A minimal payload with real, valid canonical FY25/FY26 coverage."""
    return {
        "primary": {"fy_tags": ["fy26"]},
        "offtake": {
            "fy_tags": ["fy26", "fy27"],
            "secondary_total_fy25": 23332.36,
            "secondary_months_fy25": [
                "Apr-24", "May-24", "Jun-24", "Jul-24", "Aug-24", "Sep-24",
                "Oct-24", "Nov-24", "Dec-24", "Jan-25", "Feb-25", "Mar-25",
            ],
        },
    }


def test_case1_canonical_fy25_and_fy26_present_passes():
    ok, messages = check_historical_baseline(_valid_payload())
    assert ok is True
    assert any("Historical baseline integrity verified" in m for m in messages)


def test_case2_fy25_missing_fails():
    data = _valid_payload()
    del data["offtake"]["secondary_total_fy25"]
    del data["offtake"]["secondary_months_fy25"]
    ok, messages = check_historical_baseline(data)
    assert ok is False
    assert any("secondary_total_fy25" in m for m in messages)
    assert any("secondary_months_fy25" in m for m in messages)


def test_case3_fy26_missing_fails():
    data = _valid_payload()
    data["primary"]["fy_tags"] = ["fy27"]
    data["offtake"]["fy_tags"] = ["fy27"]
    ok, messages = check_historical_baseline(data)
    assert ok is False
    assert any("fy26" in m and "primary.fy_tags" in m for m in messages)
    assert any("fy26" in m and "offtake.fy_tags" in m for m in messages)


def test_case4_canonical_coverage_field_missing_fails():
    data = {"primary": {}, "offtake": {}}
    ok, messages = check_historical_baseline(data)
    assert ok is False
    assert any("primary.fy_tags" in m for m in messages)
    assert any("offtake.fy_tags" in m for m in messages)
    assert any("secondary_total_fy25" in m for m in messages)
    assert any("secondary_months_fy25" in m for m in messages)


def test_case4b_block_itself_missing_fails():
    ok, messages = check_historical_baseline({})
    assert ok is False
    assert any("'primary' block missing" in m for m in messages)
    assert any("'offtake' block missing" in m for m in messages)


def test_case5_canonical_field_null_fails():
    data = _valid_payload()
    data["primary"]["fy_tags"] = None
    data["offtake"]["secondary_total_fy25"] = None
    ok, messages = check_historical_baseline(data)
    assert ok is False
    assert any("primary.fy_tags" in m and ("null" in m or "missing" in m) for m in messages)
    assert any("secondary_total_fy25" in m for m in messages)


def test_case6_canonical_field_malformed_type_fails():
    data = _valid_payload()
    data["offtake"]["fy_tags"] = "fy26"  # string, not a list
    data["offtake"]["secondary_total_fy25"] = "N/A"  # not numeric
    data["offtake"]["secondary_months_fy25"] = "12"  # string, not a list
    ok, messages = check_historical_baseline(data)
    assert ok is False
    assert any("offtake.fy_tags" in m for m in messages)
    assert any("secondary_total_fy25" in m for m in messages)
    assert any("secondary_months_fy25" in m for m in messages)


def test_case6b_empty_secondary_months_list_fails():
    data = _valid_payload()
    data["offtake"]["secondary_months_fy25"] = []
    ok, messages = check_historical_baseline(data)
    assert ok is False
    assert any("secondary_months_fy25" in m for m in messages)


def test_case7_deprecated_metadata_absent_canonical_valid_passes():
    data = _valid_payload()
    assert "metadata" not in data
    ok, messages = check_historical_baseline(data)
    assert ok is True


def test_case8_deprecated_metadata_present_but_canonical_invalid_still_fails():
    """The old metadata block must never mask invalid canonical coverage."""
    data = {"primary": {}, "offtake": {}}
    data["metadata"] = {
        "coverage": {
            "fiscal_years": ["fy25", "fy26", "fy27"],
            "fy25_months": ["Apr-25", "May-25", "Jun-25", "Jul-25"],
            "fy26_months": ["Aug-25", "Sep-25", "Oct-25", "Nov-25",
                             "Dec-25", "Jan-26", "Feb-26", "Mar-26"],
        }
    }
    ok, messages = check_historical_baseline(data)
    assert ok is False


def test_metadata_never_read_at_all():
    """Sanity: the function must not reference 'metadata' anywhere in its
    source, so a future edit can't silently reintroduce the dependency."""
    import inspect
    import validate_historical_baseline as mod
    src = inspect.getsource(mod.check_historical_baseline)
    assert "metadata" not in src


def test_top_level_not_dict_fails():
    ok, messages = check_historical_baseline(["not", "a", "dict"])
    assert ok is False
