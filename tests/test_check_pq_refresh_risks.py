"""Refresh-risk checks must not report success after skipping unreadable sources."""

import importlib.util
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "check_pq_refresh_risks.py"
spec = importlib.util.spec_from_file_location("check_pq_refresh_risks", SCRIPT)
refresh_risks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(refresh_risks)


def test_check_values_reports_unreadable_source(tmp_path):
    missing = tmp_path / "missing.csv"
    with pytest.raises(OSError, match="Cannot check values in") as exc:
        refresh_risks.check_values([missing], {"Value": "number"})
    assert exc.value.__cause__ is not None
