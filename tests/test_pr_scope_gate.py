"""scripts/check_pr_scope.py: the feature-freeze PR-scope gate.

No network: every case passes a PR title, body and changed-file list straight
to check(). The cases are the real PRs of 2026-10-01 -- #272 (out of scope,
green CI) must fail; #273 (correctness fix with a regression test), #274
(B5 blocker docs) and #271 (state housekeeping) must pass.
"""
import importlib.util
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("prscope", ROOT / "scripts/check_pr_scope.py")
gate = importlib.util.module_from_spec(spec)
sys.modules["prscope"] = gate
spec.loader.exec_module(gate)

STATE = {
    "feature_freeze": {"active": True},
    "blockers": {f"B{i}": {} for i in range(1, 7)},
    "open_issues": [{"number": 120}, {"number": 194}],
}


def run(body, changed, title="t", state=STATE):
    return gate.check(title, body, changed, state)


# ---- the real PRs of 2026-10-01 ------------------------------------------

def test_pr272_enhancements_without_declaration_fail():
    ok, msg = run("Adds donut centre totals, share labels and FYTD measures.",
                  ["dashboard/index.html", "PowerBI/DAX/01_CoreMeasures.dax"])
    assert not ok and "no 'Freeze classification" in msg


def test_pr272_deferred_title_fails_even_with_a_class():
    ok, msg = run("Freeze classification: HOUSEKEEPING", ["docs/x.md"],
                  title="[DEFERRED: feature freeze] donut centre totals")
    assert not ok and "DEFERRED" in msg


def test_pr273_correctness_fix_with_its_test_passes():
    body = ("**Freeze classification: CORRECTNESS_FIX** ...\n"
            "Regression test: `tests/test_powerbi_rolling_average.py` failed 6/14 on main.")
    changed = ["PowerBI/DAX/01_CoreMeasures.dax", "tests/test_powerbi_rolling_average.py"]
    ok, msg = run(body, changed)
    assert ok and "tests/test_powerbi_rolling_average.py" in msg


def test_pr274_blocker_fix_naming_b5_passes():
    ok, msg = run("**Freeze classification: BLOCKER_FIX (B5).**", ["docs/evidence/B5_RUN_SHEET.md"])
    assert ok and "B5" in msg


def test_pr271_state_housekeeping_passes():
    ok, _ = run("Freeze classification: HOUSEKEEPING", ["config/project_state.yml"])
    assert ok


# ---- each rule fails closed -----------------------------------------------

def test_deferred_class_fails():
    ok, _ = run("Freeze classification: DEFERRED", ["dashboard/index.html"])
    assert not ok


def test_unknown_class_fails():
    ok, msg = run("Freeze classification: NICE_TO_HAVE", ["docs/x.md"])
    assert not ok and "unknown" in msg


def test_two_classes_fail():
    ok, msg = run("Freeze classification: HOUSEKEEPING\nFreeze classification: BLOCKER_FIX B5", ["docs/x.md"])
    assert not ok and "more than one" in msg


def test_blocker_fix_without_a_known_blocker_fails():
    ok, _ = run("Freeze classification: BLOCKER_FIX for the dashboard", ["docs/x.md"])
    assert not ok


def test_blocker_fix_naming_a_closed_issue_fails():
    # #252 is closed; only issues listed open in project_state.yml count
    ok, _ = run("Freeze classification: BLOCKER_FIX, see #252", ["docs/x.md"])
    assert not ok


def test_blocker_fix_naming_an_open_issue_passes():
    ok, msg = run("Freeze classification: BLOCKER_FIX for #120", ["docs/x.md"])
    assert ok and "#120" in msg


def test_correctness_fix_test_not_in_diff_fails():
    ok, msg = run("Freeze classification: CORRECTNESS_FIX, see tests/test_old.py",
                  ["PowerBI/DAX/01_CoreMeasures.dax"])
    assert not ok and "regression test" in msg


def test_correctness_fix_without_naming_a_test_fails():
    ok, _ = run("Freeze classification: CORRECTNESS_FIX", ["dashboard/index.html", "tests/test_x.py"])
    assert not ok


def test_scripts_test_file_counts_as_regression_test():
    ok, _ = run("Freeze classification: CORRECTNESS_FIX — scripts/test_json_serialization.py",
                ["scripts/test_json_serialization.py"])
    assert ok


@pytest.mark.parametrize("path", ["dashboard/index.html", "dashboard/data.js",
                                  "PowerBI/DAX/01_CoreMeasures.dax",
                                  "PowerBI/PowerQuery/39_PL_Expense_Input.pq",
                                  "scripts/build_dashboard_data.py",
                                  # financial / source data and governed definitions
                                  "PowerBI/SeedData/Masters/PL_Expense_Input.csv",
                                  "PowerBI/SeedData/Masters/AssumptionTable.csv",
                                  "PowerBI/RawDataFolders/Primary_Article_Monthly/primary_article_Apr_26.csv",
                                  "PowerBI/QuickSetup/AllDAX_Consolidated.txt",
                                  "config/baselines.json",
                                  "config/data_source_registry.yml",
                                  # the enforcement itself
                                  ".github/workflows/pr-scope-gate.yml",
                                  ".github/workflows/production-acceptance-gate.yml",
                                  "scripts/check_pr_scope.py",
                                  "tests/test_pr_scope_gate.py"])
def test_housekeeping_touching_product_code_fails(path):
    ok, msg = run("Freeze classification: HOUSEKEEPING", ["docs/x.md", path])
    assert not ok and path in msg


def test_freeze_off_passes_without_declaration():
    ok, msg = run("anything", ["dashboard/index.html"], state={"feature_freeze": {"active": False}})
    assert ok and "off" in msg


# ---- wiring -----------------------------------------------------------------

def test_live_state_file_has_the_freeze_switch():
    state = yaml.safe_load((ROOT / "config/project_state.yml").read_text(encoding="utf-8"))
    assert state["feature_freeze"]["active"] in (True, False)


def test_workflow_is_read_only_and_pinned():
    wf = (ROOT / ".github/workflows/pr-scope-gate.yml").read_text(encoding="utf-8")
    assert "contents: read" in wf and "write" not in wf.split("permissions:")[1].split("jobs:")[0]
    for line in wf.splitlines():
        if "uses:" in line:
            ref = line.split("@", 1)[1].split()[0]
            assert len(ref) == 40, f"action not pinned to a full SHA: {line.strip()}"
    # PR text reaches the script through env vars, never inline in the shell script
    script = wf.split("run: |", 1)[1]
    assert "${{" not in script, "event data interpolated into the run script"


def test_cli_exit_codes(tmp_path, monkeypatch):
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    body, changed = tmp_path / "b.txt", tmp_path / "c.txt"
    state = tmp_path / "state.yml"      # a frozen state of its own: the real config/project_state.yml may have the freeze lifted
    state.write_text(yaml.safe_dump({**STATE, "feature_freeze": {"active": True}}), encoding="utf-8")
    args = ["--title", "t", "--body-file", str(body), "--changed-files-file", str(changed), "--state-file", str(state)]
    changed.write_text("docs/x.md\n", encoding="utf-8")
    body.write_text("Freeze classification: HOUSEKEEPING", encoding="utf-8")
    assert gate.main(args) == 0
    body.write_text("no declaration", encoding="utf-8")
    assert gate.main(args) == 1


# ---- self-bypass (review of 034d7f1) ------------------------------------------

def test_pr_cannot_switch_the_freeze_off_for_itself(tmp_path, monkeypatch):
    """The PR's own project_state.yml says active: false; the base says true.
    The gate is judged on the base copy, so the PR still needs a declaration."""
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    base = tmp_path / "base_state.yml"
    base.write_text(yaml.safe_dump({**STATE, "feature_freeze": {"active": True}}), encoding="utf-8")
    pr_copy = tmp_path / "pr_state.yml"           # what the PR changed; must be ignored
    pr_copy.write_text(yaml.safe_dump({**STATE, "feature_freeze": {"active": False}}), encoding="utf-8")
    body, changed = tmp_path / "b.txt", tmp_path / "c.txt"
    body.write_text("turn the freeze off", encoding="utf-8")
    changed.write_text("config/project_state.yml\n", encoding="utf-8")
    args = ["--title", "t", "--body-file", str(body), "--changed-files-file", str(changed)]
    assert gate.main(args + ["--state-file", str(base)]) == 1
    assert gate.main(args + ["--state-file", str(pr_copy)]) == 0    # why the base copy matters


def test_pr_cannot_add_itself_a_blocker(tmp_path):
    # blockers / open issues come from the base state too
    ok, _ = run("Freeze classification: BLOCKER_FIX (B9)", ["docs/x.md"])
    assert not ok


def test_workflow_runs_base_code_only():
    wf = (ROOT / ".github/workflows/pr-scope-gate.yml").read_text(encoding="utf-8")
    trig = wf.split("on:", 1)[1].split("permissions:", 1)[0]
    assert "pull_request_target" in trig and "\n  pull_request:" not in trig
    assert "persist-credentials: false" in wf
    assert "ref:" not in wf, "the job must check out the base branch, never the PR head"
    assert "--state-file config/project_state.yml" in wf
    script = wf.split("run: |", 1)[1]
    # changed files come from the API: a `git fetch` of the PR ref needs credentials that
    # persist-credentials: false removed, and fails on a private repo (PR #284, 2026-10-01)
    assert "pulls/${PR_NUMBER}/files" in script and "git fetch" not in script
    # that endpoint needs pull-requests: read; contents: read alone returns HTTP 403 (run 36954765462)
    assert "pull-requests: read" in wf.split("permissions:")[1].split("jobs:")[0]
    assert "test -s" in script, "an empty file list must fail, not pass"
    # nothing from the PR is executed: only the base checkout's checker runs
    assert "checkout pr" not in script and "pip install -r" not in script
