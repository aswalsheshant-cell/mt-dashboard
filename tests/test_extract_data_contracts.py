"""
Regression test for extract_data_contracts.py's extract_offtake_csv().

Context: offtake['zone_monthly_fyNN'][zone] in the real dashboard/data.js is a
plain list of per-month values (positionally aligned with
offtake['months_fyNN']), never a {month: value} dict. The old code called
.items() on it directly and crashed with:
    AttributeError: 'list' object has no attribute 'items'
before ever reaching its own dict-vs-scalar per-item branch two lines below.
"""
import sys
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from extract_data_contracts import extract_offtake_csv  # noqa: E402


def _list_shaped_offtake():
    """Matches the real dashboard/data.js shape: zone_monthly_fy26 values are
    plain lists, not dicts."""
    return {
        "offtake": {
            "months_fy26": ["Apr-25", "May-25"],
            "zone_monthly_fy26": {
                "North": [427.05, 118.2],
                "West": [607.79, 200.1],
            },
        }
    }


def _dict_shaped_offtake():
    """The shape the original code assumed -- kept supported, not just the
    new list shape, per 'preserve existing supported structures'."""
    return {
        "offtake": {
            "zone_monthly_fy26": {
                "North": {"Apr-25": {"offtake_cr": 42.0, "primary_cr": 40.0}},
            },
        }
    }


def test_list_shaped_zone_monthly_no_longer_crashes(tmp_path):
    """This is the exact structure that raised
    AttributeError: 'list' object has no attribute 'items' before the fix."""
    extract_offtake_csv(_list_shaped_offtake(), tmp_path)
    out = tmp_path / "offtake.csv"
    assert out.exists()
    df = pd.read_csv(out)
    assert set(df["Zone"]) >= {"North", "West"}


def test_list_shaped_values_map_to_correct_month_labels(tmp_path):
    extract_offtake_csv(_list_shaped_offtake(), tmp_path)
    df = pd.read_csv(tmp_path / "offtake.csv")
    row = df[(df["Zone"] == "North") & (df["Month"] == "Apr-25")].iloc[0]
    assert row["Offtake_NSV_Lakh"] == pytest.approx(427.05)
    row2 = df[(df["Zone"] == "West") & (df["Month"] == "May-25")].iloc[0]
    assert row2["Offtake_NSV_Lakh"] == pytest.approx(200.1)


def test_dict_shaped_zone_monthly_still_supported(tmp_path):
    """The original dict-per-month format (never observed in current data,
    but the code explicitly anticipated it) must keep working."""
    extract_offtake_csv(_dict_shaped_offtake(), tmp_path)
    df = pd.read_csv(tmp_path / "offtake.csv")
    row = df[(df["Zone"] == "North") & (df["Month"] == "Apr-25")].iloc[0]
    assert row["Offtake_NSV_Lakh"] == pytest.approx(42.0)
    assert row["Primary_NSV_Lakh"] == pytest.approx(40.0)


def test_missing_month_labels_key_does_not_crash(tmp_path):
    """If months_fyNN were ever absent, zip() with an empty list should just
    produce zero rows for that FY rather than raising -- no record silently
    mislabeled."""
    data = {"offtake": {"zone_monthly_fy26": {"North": [1.0, 2.0]}}}
    extract_offtake_csv(data, tmp_path)
    out = tmp_path / "offtake.csv"
    if out.exists():
        df = pd.read_csv(out)
        assert "North" not in set(df.get("Zone", []))
