"""scripts/eval_harness.py is retired as one change: script, CI step and runbook.

Found 2026-09-26 on main 17b3f81: eval_harness.py checked the retired
data_master.json pipeline and failed 4 of 6 checks on a healthy main (15-25 MB
data.js size window, FY25 Primary required, data_master.json status
LOCKED_MULTI_YEAR_V2, "NaN" = the intentional missing-not-zero blanks); its
--fix-status option wrote data_master.json (CLAUDE.md invariant 1). The Windows
Power BI CI ran it as a warning-only step (FM-28) and docs/OPERATIONAL_HANDOFF
told operators to run it. The same CI step skipped the REQUIRED validator
tests/validate_data_integrity.py silently if the file was missing.
Live checks it duplicated are in scripts/ci_validate_datajs.py.
"""
import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
WF = ROOT / ".github" / "workflows" / "pbi-windows-ci.yml"
# Historical records keep describing what ran at the time; they are not instructions.
HISTORICAL = {"docs/RELEASE_v2.3.0.md", "docs/FAILURE_MODE_REGISTER.md", "CHANGELOG.md"}


def test_script_is_gone_and_nothing_runs_it():
    assert not (ROOT / "scripts" / "eval_harness.py").exists()
    for wf in (ROOT / ".github" / "workflows").glob("*.y*ml"):
        code = [ln for ln in wf.read_text(encoding="utf-8").splitlines() if not ln.lstrip().startswith("#")]
        assert not [ln for ln in code if "eval_harness" in ln], wf.name   # a comment may explain the retirement


def test_no_runbook_tells_operators_to_run_it():
    hits = []
    for p in list(ROOT.glob("*.md")) + list((ROOT / "docs").rglob("*.md")) + list(ROOT.glob("*.sh")):
        rel = p.relative_to(ROOT).as_posix()
        if rel in HISTORICAL:
            continue
        for ln in p.read_text(encoding="utf-8", errors="replace").splitlines():
            if re.search(r"^\s*python3?\s+scripts/eval_harness\.py", ln):
                hits.append(f"{rel}: {ln.strip()}")
    assert hits == [], hits


def _validation_step():
    wf = yaml.safe_load(WF.read_text(encoding="utf-8"))
    steps = [s for j in wf["jobs"].values() for s in j["steps"]]
    return next(s for s in steps if "validate_data_integrity.py" in (s.get("run") or ""))


def test_required_validator_is_not_skippable():
    run = _validation_step()["run"]
    assert "not found (skipped)" not in run
    assert re.search(r"-not \(Test-Path \"tests/validate_data_integrity\.py\"\)\).*?exit 1", run, re.S), run


PWSH = shutil.which("pwsh") or ("/tmp/claude-0/pwsh/pwsh" if Path("/tmp/claude-0/pwsh/pwsh").exists() else None)


@pytest.mark.skipif(PWSH is None, reason="PowerShell (pwsh) not installed")
def test_step_passes_on_repo_and_fails_without_validator(tmp_path):
    run = _validation_step()["run"]
    ok = subprocess.run([PWSH, "-NoProfile", "-Command", run], cwd=ROOT, capture_output=True, text=True, timeout=300)
    assert ok.returncode == 0, ok.stdout[-2000:] + ok.stderr[-2000:]
    (tmp_path / "tests").mkdir()
    bad = subprocess.run([PWSH, "-NoProfile", "-Command", run], cwd=tmp_path, capture_output=True, text=True, timeout=60)
    assert bad.returncode != 0 and "required validator" in bad.stdout, bad.stdout
