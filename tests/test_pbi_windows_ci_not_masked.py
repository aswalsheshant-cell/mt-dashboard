"""Regression tests: the Power BI Windows CI must not report green over a failure.

Found 2026-09-26 on main 8ba13f8 (old PR #131 rebuilt on current main):
  * pbi-windows-ci.yml had `continue-on-error: true` on both validation steps,
    so the job stayed green while scripts/ci/test_powerbi_model.ps1 exited 1
    (run 36217266380: "00_Parameters.pq: Malformed M-code structure") and
    tests/validate_data_integrity.py exited 1 (3 assertions).
  * the harness step ran two python scripts back to back with no
    $LASTEXITCODE check, so the first script's failure was lost whenever the
    second one passed (a pwsh step's result is its LAST native exit code).
  * the M-checker demanded the text "let" and "in" in every .pq file, but
    00_Parameters.pq is a Power Query parameter (a value tagged
    `meta [IsParameterQuery=true, ...]`), which is valid M with no let/in.

The pwsh tests need PowerShell (present on GitHub's Windows and Ubuntu
runners); set PWSH=/path/to/pwsh to run them elsewhere.
"""
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / ".github" / "workflows" / "pbi-windows-ci.yml"
CHECKER = ROOT / "scripts" / "ci" / "test_powerbi_model.ps1"
PWSH = os.environ.get("PWSH") or shutil.which("pwsh")
needs_pwsh = pytest.mark.skipif(not PWSH, reason="PowerShell (pwsh) not installed")


def _steps():
    wf = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    return [s for job in wf["jobs"].values() for s in job["steps"]]


def test_no_step_hides_its_failure():
    masked = [s.get("name") for s in _steps() if s.get("continue-on-error")]
    assert masked == [], f"steps with continue-on-error: {masked}"


def test_every_python_call_in_a_pwsh_step_checks_its_exit_code():
    unchecked = []
    for s in _steps():
        if s.get("shell") != "pwsh" or "run" not in s:
            continue
        lines = s["run"].splitlines()
        for i, line in enumerate(lines):
            if re.match(r"\s*python\s", line):
                after = "\n".join(lines[i + 1:i + 3])
                if "$LASTEXITCODE" not in after:
                    unchecked.append(f"{s['name']}: {line.strip()}")
    assert unchecked == [], f"exit code not checked: {unchecked}"


def test_data_integrity_validator_passes_on_committed_data_js():
    r = subprocess.run([sys.executable, "tests/validate_data_integrity.py"],
                       cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stdout[-2500:] + r.stderr[-500:]


def _run_checker(repo_root):
    return subprocess.run([PWSH, "-NoProfile", "-File", str(CHECKER), "-RepoRoot", str(repo_root)],
                          capture_output=True, text=True, encoding="utf-8")


@needs_pwsh
def test_powerbi_checker_passes_on_repo():
    r = _run_checker(ROOT)
    assert r.returncode == 0, r.stdout[-2500:] + r.stderr[-500:]


def _fixture(tmp_path, name, text):
    pq = tmp_path / "PowerBI" / "PowerQuery"
    pq.mkdir(parents=True)
    (pq / name).write_text(text, encoding="utf-8")
    return tmp_path


@needs_pwsh
def test_powerbi_checker_accepts_a_parameter_query(tmp_path):
    root = _fixture(tmp_path, "00_Parameters.pq",
                    '// parameter\n"C:\\MT-Dashboard" meta [IsParameterQuery=true, Type="Text", '
                    'IsParameterQueryRequired=true]\n')
    r = _run_checker(root)
    assert r.returncode == 0, r.stdout[-1500:]


@needs_pwsh
def test_powerbi_checker_still_rejects_a_query_with_no_let_in(tmp_path):
    root = _fixture(tmp_path, "10_Broken.pq", 'Source = Csv.Document(File.Contents(pRootFolder))\n')
    r = _run_checker(root)
    assert r.returncode == 1, r.stdout[-1500:]
    assert "10_Broken.pq" in r.stdout


@pytest.fixture(scope="module")
def dash():
    raw = (ROOT / "dashboard" / "data.js").read_text(encoding="utf-8")
    return raw[raw.index("{"):].rstrip().rstrip(";")


def _mutate_and_validate(tmp_path, dash, mutate):
    import json
    d = json.loads(dash)
    mutate(d)
    out = tmp_path / "data.js"
    out.write_text("window.DASH = " + json.dumps(d) + ";\n", encoding="utf-8")
    return subprocess.run([sys.executable, "tests/validate_data_integrity.py", str(out)],
                          cwd=ROOT, capture_output=True, text=True, encoding="utf-8")


def _double_count_pan_india(d):
    zones = d["offtake"]["by_zone"]
    zones.append(dict(zones[0], name="Pan India Total",
                      fy26=sum(z.get("fy26") or 0 for z in zones)))


@pytest.mark.parametrize("mutate, expect", [
    (_double_count_pan_india, "OFFTAKE FY26"),
    (lambda d: d["detail_meta"]["fyx_primary"].pop("FY27"), "FY27 TOTAL"),
    (lambda d: d["primary"]["by_chain"][0].update(fy26=float("nan")), "NaN FY26"),
])
def test_data_integrity_validator_still_catches_real_defects(tmp_path, dash, mutate, expect):
    r = _mutate_and_validate(tmp_path, dash, mutate)
    assert r.returncode == 1 and expect in r.stdout, r.stdout[-1500:]
