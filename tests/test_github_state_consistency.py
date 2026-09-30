"""scripts/check_github_state_consistency.py with mocked GitHub responses.

No network: every case injects a fake fetcher. The live run is the
repo-state-consistency workflow.
"""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("ghstate", ROOT / "scripts/check_github_state_consistency.py")
gh = importlib.util.module_from_spec(spec)
sys.modules["ghstate"] = gh
spec.loader.exec_module(gh)

FROZEN = "a" * 40


def fake(prs=None, issues=None):
    prs, issues = prs or {}, issues or {}

    def fetch(path):
        kind, n = path.split("/")
        table = prs if kind == "pulls" else issues
        return table.get(int(n), {"_missing": True})
    return fetch


def state(**kw):
    base = {"open_prs": [], "merged_prs": [], "closed_superseded": [], "open_issues": []}
    base.update(kw)
    return base


def test_active_pr_correctly_open():
    s = state(open_prs=[{"number": 119, "status": "FROZEN_EVIDENCE", "frozen_sha": FROZEN}])
    assert gh.check(s, fake(prs={119: {"state": "open", "head": {"sha": FROZEN}}})) == []


def test_active_pr_unexpectedly_closed():
    s = state(open_prs=[{"number": 252, "status": "HOLD"}])
    drift = gh.check(s, fake(prs={252: {"state": "closed", "merged": False}}))
    assert drift and "#252" in drift[0] and "closed" in drift[0]


def test_frozen_branch_moved_is_drift():
    s = state(open_prs=[{"number": 119, "status": "FROZEN_EVIDENCE", "frozen_sha": FROZEN}])
    drift = gh.check(s, fake(prs={119: {"state": "open", "head": {"sha": "b" * 40}}}))
    assert drift and "moved" in drift[0]


def test_merged_pr_still_marked_hold():
    s = state(open_prs=[{"number": 229, "status": "HOLD"}])
    drift = gh.check(s, fake(prs={229: {"state": "closed", "merged": True}}))
    assert drift and "merged" in drift[0]


def test_listed_merged_but_not_merged():
    s = state(merged_prs=[300])
    assert gh.check(s, fake(prs={300: {"state": "open", "merged": False}}))


def test_superseded_pr_correctly_closed():
    s = state(open_prs=[{"number": 267, "status": "HOLD"}],
              closed_superseded=[{"number": 252, "superseded_by": 267}])
    prs = {267: {"state": "open", "head": {"sha": "c" * 40}}, 252: {"state": "closed", "merged": False}}
    assert gh.check(s, fake(prs=prs)) == []


def test_superseded_pr_reopened_is_drift():
    s = state(open_prs=[{"number": 267, "status": "HOLD"}],
              closed_superseded=[{"number": 252, "superseded_by": 267}])
    prs = {267: {"state": "open"}, 252: {"state": "open", "merged": False}}
    assert any("#252" in d for d in gh.check(s, fake(prs=prs)))


def test_external_issue_still_open():
    s = state(open_issues=[{"number": 194}])
    assert gh.check(s, fake(issues={194: {"state": "open"}})) == []
    assert gh.check(s, fake(issues={194: {"state": "closed"}}))


def test_historical_references_are_not_checked():
    # Only registry entries are validated: a PR mentioned nowhere in the
    # registry (e.g. #14 in a dated history section) triggers no request.
    asked = []

    def fetch(path):
        asked.append(path)
        return {"state": "open"}
    gh.check(state(open_issues=[{"number": 120}]), fetch)
    assert asked == ["issues/120"]


def test_api_unavailable_is_skip_not_pass(monkeypatch, capsys):
    def down(repo, token):
        def fetch(path):
            raise gh.ExternalUnavailable("URLError for pulls/119")
        return fetch
    monkeypatch.setattr(gh, "github_fetcher", down)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    assert gh.main([]) == 0
    out = capsys.readouterr().out
    assert "SKIP_EXTERNAL_CHECK" in out and "CONSISTENT" not in out


def test_drift_exits_nonzero(monkeypatch, capsys):
    monkeypatch.setattr(gh, "github_fetcher", lambda repo, token: fake())   # everything "missing"
    assert gh.main([]) == 1
    assert "DRIFT" in capsys.readouterr().out
