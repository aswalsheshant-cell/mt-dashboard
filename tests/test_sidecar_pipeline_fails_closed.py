"""Regression test for pipeline_generate_sidecars.py's mock-data landmine fix.

Same failure class as tests/test_sync_compliance_data_fails_closed.py (PR
#157): pipeline_generate_sidecars.py has no real alerts/opportunities loader
on any path (alerts_df/opps_df were unconditionally synthetic), and
.github/workflows/daily-sidecar-refresh.yml -- the daily cron -- never
passes --audits/--zones/--chains. Before this fix, the ONLY thing stopping
every scheduled run from silently committing fabricated compliance/enriched
numbers as if real was an unrelated schema-shape bug in
process_generated_insights() that happened to make every one of this
workflow's 21 scheduled runs fail before reaching the commit step. Fixing
that bug in isolation, without a guard, would have made this pipeline start
succeeding -- and start committing fake data over
dashboard/compliance_metrics.json / dashboard/enriched_metrics.json, both
fetched and rendered at runtime by dashboard/index.html.

This test proves: (1) the exact daily-workflow invocation (no real source,
no confirmation flag) exits 0 and writes nothing, (2) the previously-broken
generated_insights.json schema shape now validates, (3) the opt-in mock
path, when explicitly confirmed, stamps every output is_synthetic=true /
data_status=SYNTHETIC_DEMO so it can never be mistaken for real data
downstream.
"""
import importlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
pgs = importlib.import_module("pipeline_generate_sidecars")

PRODUCTION_FILES = [
    REPO_ROOT / "dashboard" / "compliance_metrics.json",
    REPO_ROOT / "dashboard" / "enriched_metrics.json",
    REPO_ROOT / "dashboard" / "generated_insights.json",
]


def _snapshot():
    return {p: (p.read_bytes() if p.exists() else None) for p in PRODUCTION_FILES}


def test_exact_daily_workflow_invocation_exits_zero_and_writes_nothing():
    """.github/workflows/daily-sidecar-refresh.yml runs exactly:
    python3 pipeline_generate_sidecars.py --period "Q3 FY27" -- no other
    flags. This must now be a clean no-op, not a failure and not a write."""
    before = _snapshot()
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "pipeline_generate_sidecars.py"), "--period", "Q3 FY27"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Refusing to write synthetic demo data" in result.stdout
    after = _snapshot()
    assert after == before, "the daily-workflow invocation must never touch the live dashboard/*.json files"


def test_process_generated_insights_now_matches_its_own_schema():
    """The bug that made every one of this workflow's 21 scheduled runs fail:
    process_generated_insights()'s output didn't match
    schemas/generated_insights.schema.json at all."""
    import jsonschema
    _, _, _, alerts_df, opps_df, headline_data = pgs.create_synthetic_raw_data()
    payload = pgs.process_generated_insights(alerts_df, opps_df, headline_data, "Q3 FY27")
    schema = pgs.load_json_schema("generated_insights.schema.json")
    jsonschema.validate(instance=payload, schema=schema)  # raises on failure


def test_mock_path_stamps_every_output_synthetic(tmp_path, monkeypatch):
    """Exercises the actual write path (validate_and_write()) against a
    redirected DASHBOARD_DIR, so this never touches the real repo files."""
    monkeypatch.setattr(pgs, "DASHBOARD_DIR", str(tmp_path))

    audits_df, zones_df, chains_df, alerts_df, opps_df, headline_data = pgs.create_synthetic_raw_data()
    compliance_payload = pgs.process_compliance_metrics(audits_df, "Q3 FY27")
    enriched_payload = pgs.process_enriched_metrics(zones_df, chains_df)
    insights_payload = pgs.process_generated_insights(alerts_df, opps_df, headline_data, "Q3 FY27")

    synth_note = "test"
    for block in ("compliance", "inventory_fillrate"):
        compliance_payload[block]["metadata"]["is_synthetic"] = True
        compliance_payload[block]["metadata"]["data_status"] = "SYNTHETIC_DEMO"
        compliance_payload[block]["metadata"]["source"] = synth_note
    enriched_payload["metadata"] = {"is_synthetic": True, "data_status": "SYNTHETIC_DEMO", "source": synth_note}
    insights_payload["metadata"]["is_synthetic"] = True
    insights_payload["metadata"]["data_status"] = "SYNTHETIC_DEMO"
    insights_payload["metadata"]["source"] = synth_note

    pgs.validate_and_write(compliance_payload, "compliance_metrics.schema.json", "compliance_metrics.json")
    pgs.validate_and_write(enriched_payload, "enriched_metrics.schema.json", "enriched_metrics.json")
    pgs.validate_and_write(insights_payload, "generated_insights.schema.json", "generated_insights.json")

    compliance_out = json.loads((tmp_path / "compliance_metrics.json").read_text())
    for block in ("compliance", "inventory_fillrate"):
        assert compliance_out[block]["metadata"]["is_synthetic"] is True
        assert compliance_out[block]["metadata"]["data_status"] == "SYNTHETIC_DEMO"

    enriched_out = json.loads((tmp_path / "enriched_metrics.json").read_text())
    assert enriched_out["metadata"]["is_synthetic"] is True

    insights_out = json.loads((tmp_path / "generated_insights.json").read_text())
    assert insights_out["metadata"]["is_synthetic"] is True


def test_cli_help_documents_the_confirmation_flag():
    """The flag must actually exist and be discoverable -- not just
    referenced in a docstring."""
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "pipeline_generate_sidecars.py"), "--help"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0
    assert "--i-understand-this-is-mock-data" in result.stdout
