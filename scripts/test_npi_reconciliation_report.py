"""Smoke test for npi_reconciliation_report.py: it must run clean (exit 0,
zero qc_failures) against the real checked-in dashboard/data.js, and it
must actually catch a corrupted npd block rather than passing anything."""
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "npi_reconciliation_report.py"


def test_clean_run_against_real_data(tmp_path):
    data_js = REPO / "dashboard" / "data.js"
    if not data_js.exists():
        return
    out_dir = tmp_path / "evidence"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--data", str(data_js), "--out-dir", str(out_dir)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    summary = json.loads((out_dir / "npi_release_summary.json").read_text())
    assert summary["qc_failures"] == 0
    assert summary["artifact_stale"] is False
    assert (out_dir / "npi_release_reconciliation.csv").exists()


def test_catches_a_tampered_npd_block(tmp_path):
    """Corrupt the checked-in npd block (without touching detail_records) and
    confirm the script's stale-artifact check actually fires -- proves this
    is a real independent check, not just re-reading npd's own numbers."""
    import re
    data_js = REPO / "dashboard" / "data.js"
    if not data_js.exists():
        return
    txt = data_js.read_text(encoding="utf-8")
    m = re.search(r"window\.DASH\s*=\s*(\{.*\})\s*;?\s*$", txt, re.DOTALL)
    dash = json.loads(m.group(1))
    if not dash.get("npd") or not dash.get("detail_records"):
        return
    dash["npd"]["counts_by_fy"] = {"FAKE_FY": 999999}  # tamper
    tampered_path = tmp_path / "tampered_data.js"
    tampered_path.write_text("window.DASH = " + json.dumps(dash) + ";\n", encoding="utf-8")
    out_dir = tmp_path / "evidence_tampered"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--data", str(tampered_path), "--out-dir", str(out_dir)],
        capture_output=True, text=True,
    )
    assert result.returncode != 0
    summary = json.loads((out_dir / "npi_release_summary.json").read_text())
    assert summary["artifact_stale"] is True
    assert summary["qc_failures"] > 0
