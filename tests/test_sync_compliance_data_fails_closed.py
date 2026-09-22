"""Regression test for the sync_compliance_data.py mock-data landmine fix.

Before this fix, scripts/sync_compliance_data.py defaulted to writing
hardcoded MOCK PES/CFR/OTIF data straight to dashboard/compliance_metrics.json
-- the file dashboard/index.html fetches at runtime and renders as the Store
Audit Scorecard / Supply Chain & Inventory tabs. A legitimate-looking "sync"
invocation would silently overwrite whatever was in that file (real or not)
with synthetic demo values.

This test proves: (1) the default invocation never touches the live
dashboard path, (2) writing to that path without the explicit confirmation
flag fails closed (raises, does not write), (3) output is always stamped
is_synthetic=true / data_status=SYNTHETIC_DEMO so it can never be mistaken
for a certified audit downstream.
"""
import importlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
scd = importlib.import_module("sync_compliance_data")

REPO_ROOT = Path(__file__).resolve().parent.parent
PRODUCTION_FILE = REPO_ROOT / "dashboard" / "compliance_metrics.json"


def _production_file_snapshot():
    return PRODUCTION_FILE.read_bytes()


def test_default_output_path_is_not_the_live_dashboard_file():
    assert scd.DEFAULT_DEMO_PATH != scd.PRODUCTION_PATH
    assert Path(scd.DEFAULT_DEMO_PATH).name != "compliance_metrics.json"


def test_writing_production_path_without_confirmation_fails_closed(tmp_path, monkeypatch):
    before = _production_file_snapshot()
    monkeypatch.chdir(REPO_ROOT)
    with pytest.raises(SystemExit):
        scd.sync_compliance_data(str(PRODUCTION_FILE), allow_production_overwrite=False)
    assert _production_file_snapshot() == before, (
        "production compliance_metrics.json must be byte-identical after a "
        "refused write -- the guard must reject before opening the file"
    )


def test_writing_production_path_with_explicit_confirmation_is_allowed(tmp_path):
    target = tmp_path / "compliance_metrics.json"
    # Not the real production path (different directory), but same basename,
    # so this exercises the confirm=True branch without touching the repo file.
    scd.sync_compliance_data(str(target), allow_production_overwrite=True)
    assert target.exists()


def test_mock_output_is_always_stamped_synthetic(tmp_path):
    target = tmp_path / "demo.json"
    scd.sync_compliance_data(str(target))
    data = json.loads(target.read_text(encoding="utf-8"))
    for block in ("compliance", "inventory_fillrate"):
        assert data[block]["metadata"]["is_synthetic"] is True
        assert data[block]["metadata"]["data_status"] == "SYNTHETIC_DEMO"


def test_default_cli_output_does_not_require_confirmation(tmp_path, monkeypatch):
    (tmp_path / "dashboard").mkdir()
    monkeypatch.chdir(tmp_path)
    # Default --output (DEFAULT_DEMO_PATH) must work with no flags at all.
    scd.sync_compliance_data(scd.DEFAULT_DEMO_PATH)
    assert (tmp_path / scd.DEFAULT_DEMO_PATH).exists()
