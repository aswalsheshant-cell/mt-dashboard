""".github/workflows/ci-auto-fix.yml must report what it actually did (old PR #132
rebuilt on current main).

Found 2026-09-26 on main 83ef4bb:
  * detection called `gh run list` with no GH_TOKEN, so gh failed and the step
    exited 0 as "GitHub CLI may not be available" -- always green, never detecting;
  * once gh works, `datetime.utcnow()` (naive) was compared with an aware
    timestamp -> TypeError;
  * the analysis step was gated `if: failure()` behind that always-green step, so
    it never ran, and it advised `continue-on-error: true` (the masking #225 removed);
  * a hard-coded checklist ended "Status: Auto-remediation applied to both
    workflows" and the summary printed "Workflow fixes deployed: ✓ ..." although
    the job changes nothing.
The detection script itself is executed here against a stub `gh`.
"""
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
WF = ROOT / ".github" / "workflows" / "ci-auto-fix.yml"
SKILL = ROOT / ".claude" / "skills" / "ci-autofix" / "SKILL.md"


def _steps():
    wf = yaml.safe_load(WF.read_text(encoding="utf-8"))
    return [s for job in wf["jobs"].values() for s in job["steps"]]


def _step(name_part):
    return next(s for s in _steps() if name_part in s.get("name", ""))


def test_no_claim_of_remediation_or_masking_advice():
    text = WF.read_text(encoding="utf-8")
    for claim in ("Auto-remediation applied", "fixes deployed", "Make test harnesses optional",
                  "Ensure all test files have 'continue-on-error", "Add `continue-on-error: true`"):
        assert claim not in text, f"workflow still says: {claim}"


def test_detection_has_a_token_and_later_steps_do_not_depend_on_failure():
    detect = _step("Detect")
    assert "GH_TOKEN" in (detect.get("env") or {}), "gh needs GH_TOKEN in Actions"
    assert not [s.get("name") for s in _steps() if (s.get("if") or "").strip() == "failure()"]


def _run_detect(tmp_path, gh_body):
    """Run the workflow's own detection script with a stub `gh` first on PATH."""
    bindir = tmp_path / "bin"
    bindir.mkdir()
    gh = bindir / "gh"
    gh.write_text("#!/bin/bash\n" + gh_body)
    gh.chmod(0o755)
    out = tmp_path / "github_output"
    out.write_text("")
    env = dict(os.environ, PATH=f"{bindir}:{os.environ['PATH']}", GITHUB_OUTPUT=str(out),
               GITHUB_WORKSPACE=str(tmp_path), GH_TOKEN="stub")
    r = subprocess.run([sys.executable, "-c", _step("Detect")["run"]], cwd=tmp_path, env=env,
                       capture_output=True, text=True, timeout=30)
    return r, dict(ln.split("=", 1) for ln in out.read_text().splitlines() if "=" in ln)


def test_detect_reports_recent_failures(tmp_path):
    recent = (datetime.now(timezone.utc) - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    old = (datetime.now(timezone.utc) - timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
    runs = [{"name": "Power BI Windows CI Validation", "status": "completed", "conclusion": "failure",
             "createdAt": recent, "url": "https://example.invalid/run/1"},
            {"name": "Dashboard Validation & QC", "status": "completed", "conclusion": "failure",
             "createdAt": old, "url": "https://example.invalid/run/2"},
            {"name": "Dashboard Validation & QC", "status": "completed", "conclusion": "success",
             "createdAt": recent, "url": "https://example.invalid/run/3"}]
    r, outputs = _run_detect(tmp_path, f"cat <<'EOF'\n{json.dumps(runs)}\nEOF\n")
    assert r.returncode == 0, r.stderr
    assert outputs.get("status") == "failures_found" and outputs.get("count") == "1", (outputs, r.stdout)
    assert "Power BI Windows CI Validation" in r.stdout and "run/1" in r.stdout


def test_detect_says_when_it_could_not_check(tmp_path):
    r, outputs = _run_detect(tmp_path, "echo 'gh: auth required' >&2\nexit 1\n")
    assert r.returncode == 0
    assert outputs.get("status") == "detection_failed"
    assert "::warning::" in r.stdout and "No recent failures" not in r.stdout


def test_detect_clean(tmp_path):
    r, outputs = _run_detect(tmp_path, "echo '[]'\n")
    assert r.returncode == 0 and outputs.get("status") == "no_failures"


def test_ci_autofix_skill_describes_real_workflows():
    text = SKILL.read_text(encoding="utf-8")
    assert "workflow (`.github/workflows/qc.yml`) runs these steps" not in text, \
        "the skill describes a qc.yml workflow that does not exist"
    for wf in ("production-acceptance-gate.yml", "validate.yml"):
        assert (ROOT / ".github" / "workflows" / wf).exists()
        assert wf in text
