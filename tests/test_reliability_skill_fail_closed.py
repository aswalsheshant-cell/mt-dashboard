"""The github-actions-reliability skill's "Mandatory Health Checks (run before
every merge to main)" must fail closed (rebuild of old PR #130 on main 2e0f1e8).

Found 2026-09-26:
  * the YAML check collected parse errors / missing 'on:' findings, printed them
    and exited 0 -- a caller following the skill always saw success; it also
    skipped *.yaml files;
  * the empty-workflow loop and the asset loop printed "FAIL"/"MISSING" and
    exited 0 as well;
  * the asset list checked .github/labeler.yml, which does not exist and which
    no workflow uses, so a fail-closed version would fail on main for nothing;
  * the Startup Failure Runbook ran `python -m py_compile` on a workflow YAML
    file -- py_compile compiles Python, it has no meaning for YAML.
The skill's own code blocks are extracted and executed against fixture repos.
"""
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / ".claude" / "skills" / "github-actions-reliability" / "SKILL.md"
GOOD_WF = "name: ok\non:\n  push:\njobs:\n  a:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo hi\n"


def _block(heading):
    text = SKILL.read_text(encoding="utf-8")
    sec = text.split(heading, 1)[1]
    m = re.search(r"```bash\n(.*?)```", sec, re.S)
    assert m, f"no bash block under {heading}"
    return m.group(1)


def _asset_paths():
    return re.findall(r"for f in ([^;]+); do", _block("### 2. Repository Asset Checks"))[0].split()


def _repo(tmp_path, workflows, assets=True):
    d = tmp_path / "repo"
    (d / ".github" / "workflows").mkdir(parents=True)
    for name, body in workflows.items():
        (d / ".github" / "workflows" / name).write_text(body)
    if assets:
        for a in _asset_paths():
            (d / a).parent.mkdir(parents=True, exist_ok=True)
            (d / a).write_text("x")
    return d


def _run(block, cwd):
    return subprocess.run(["bash", "-c", block], cwd=cwd, capture_output=True, text=True, timeout=60)


def test_workflow_check_passes_on_good_files(tmp_path):
    r = _run(_block("### 1. Workflow Checks"), _repo(tmp_path, {"a.yml": GOOD_WF, "b.yaml": GOOD_WF}))
    assert r.returncode == 0, r.stdout + r.stderr


def test_workflow_check_fails_on_each_defect(tmp_path):
    cases = {
        "parse error": {"a.yml": GOOD_WF, "bad.yml": "on: [push\njobs: {"},
        "missing on:": {"a.yml": GOOD_WF, "noon.yml": "name: x\njobs: {}\n"},
        "empty file": {"a.yml": GOOD_WF, "empty.yml": ""},
        "bad .yaml file": {"a.yml": GOOD_WF, "bad.yaml": "on: [push\n"},
    }
    for i, (name, wfs) in enumerate(cases.items()):
        r = _run(_block("### 1. Workflow Checks"), _repo(tmp_path / str(i), wfs))
        assert r.returncode != 0, f"{name}: check exited 0\n{r.stdout}{r.stderr}"
        assert "FAIL" in r.stdout, f"{name}: no FAIL line\n{r.stdout}"


def test_asset_check_fails_closed_and_passes_on_main(tmp_path):
    ok = _run(_block("### 2. Repository Asset Checks"), _repo(tmp_path / "ok", {"a.yml": GOOD_WF}))
    assert ok.returncode == 0, ok.stdout
    d = _repo(tmp_path / "missing", {"a.yml": GOOD_WF})
    (d / _asset_paths()[0]).unlink()
    bad = _run(_block("### 2. Repository Asset Checks"), d)
    assert bad.returncode != 0 and "MISSING" in bad.stdout, bad.stdout
    # The mandatory check must pass on this repository as it is.
    real = _run(_block("### 2. Repository Asset Checks"), ROOT)
    assert real.returncode == 0, real.stdout


def test_runbook_does_not_py_compile_yaml():
    step1 = _block("### Step 1 — Inspect the workflow file")
    assert "py_compile" not in step1
