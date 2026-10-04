"""MT channel reconciliation must block the Production Acceptance Gate.

History: .github/workflows/production-acceptance-gate.yml ran
`scripts/mt_channel_reconciliation.py dashboard/data.js` with
`continue-on-error: true` and left it out of the final gate's failure condition,
because on 2026-09-23 it exited 2 (BLOCKED) on main: Rs 11.64 Cr of eB2B / SIS
primary sat inside MT zone sales (CB-01). Making it blocking then would have
failed every PR.

MT Leadership decided CB-01 on 2026-10-01 (Decision 1 = MT-only, Decision 2 = A,
Nykaa (FSN) under eB2B) and #276 applied it: the control now exits 0 on main.
The blocker-pack exit condition says to make the CI step blocking at that point.
These tests pin that, so non-MT sales can never again reach a zone total with the
check green.
"""
import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / ".github" / "workflows" / "production-acceptance-gate.yml"
DATA_JS = ROOT / "dashboard" / "data.js"


def _wf():
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def _gate_script():
    steps = _wf()["jobs"]["gate"]["steps"]
    return "\n".join(s.get("run", "") for s in steps)


def test_reconciliation_job_is_named_blocking():
    assert _wf()["jobs"]["reconciliation"]["name"] == "Gate: Reconciliation (blocking)"


def test_reconciliation_step_has_no_continue_on_error():
    job = _wf()["jobs"]["reconciliation"]
    steps = [s for s in job["steps"] if "mt_channel_reconciliation.py" in s.get("run", "")]
    assert steps, "the reconciliation step is missing"
    for s in steps:
        assert s.get("continue-on-error") in (None, False), \
            "continue-on-error lets a BLOCKED channel check pass"
    assert job.get("continue-on-error") in (None, False)


def test_gate_fails_when_reconciliation_fails():
    script = _gate_script()
    fail_condition = script.split("if [", 1)[1].split("then", 1)[0]
    assert 'needs.reconciliation.result }}" != "success"' in fail_condition, \
        "needs.reconciliation.result is not part of the gate's FAIL condition"
    assert "reconciliation" in _wf()["jobs"]["gate"]["needs"]


def test_reconciliation_is_listed_as_blocking_not_informational():
    script = _gate_script()
    before, _, after = script.partition("Blocking jobs:")
    blocking_block = after.split("if [", 1)[0]
    assert "needs.reconciliation.result" in blocking_block, "reconciliation is not under 'Blocking jobs'"
    assert "Informational" not in script, "an 'Informational' section still exists in the gate summary"


def test_workflow_text_no_longer_calls_it_informational():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert not re.search(r"Reconciliation \(informational\)|does not block", text, re.I)


def test_channel_control_exits_zero_on_committed_data():
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "mt_channel_reconciliation.py"), str(DATA_JS)],
                       capture_output=True, text=True)
    assert r.returncode == 0, "reconciliation is not clean on main; making it blocking would fail every PR\n" + r.stdout[-1500:]
