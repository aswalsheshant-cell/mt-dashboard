#!/usr/bin/env python3
"""Check config/project_state.yml against GitHub itself (read-only).

tests/test_repo_state_consistency.py proves the state docs agree with
config/project_state.yml, but not that the file agrees with GitHub: on
2026-09-30 #252 was closed while the file still listed it as an open HOLD PR,
and every test stayed green. This script closes that gap.

It validates only the machine-readable current-state entries, so historical
mentions of a PR number anywhere in the docs are never checked here:
  * open_prs           -> each must be open on GitHub (frozen_sha must still match)
  * merged_prs         -> each must be merged
  * closed_superseded  -> each must be closed, not merged; successor open or merged
  * open_issues        -> each must be an open issue

Exit codes:
  0  CONSISTENT, or SKIP_EXTERNAL_CHECK (GitHub unreachable / rate-limited):
     a network problem is reported as a skip, never as a pass or as drift
  1  DRIFT: the file says something GitHub contradicts

Read-only GET requests. Uses GITHUB_TOKEN when present (Actions provides it),
otherwise unauthenticated.

Usage: python scripts/check_github_state_consistency.py [--repo owner/name]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
STATE_FILE = ROOT / "config" / "project_state.yml"
DEFAULT_REPO = "aswalsheshant-cell/mt-dashboard"


class ExternalUnavailable(Exception):
    """GitHub could not be asked. Not evidence of drift."""


def github_fetcher(repo: str, token: str | None):
    def fetch(path: str) -> dict:
        req = urllib.request.Request(
            f"https://api.github.com/repos/{repo}/{path}",
            headers={"Accept": "application/vnd.github+json",
                     **({"Authorization": f"Bearer {token}"} if token else {})})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return {"_missing": True}
            raise ExternalUnavailable(f"HTTP {e.code} for {path}") from e
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise ExternalUnavailable(f"{type(e).__name__} for {path}") from e
    return fetch


def check(state: dict, fetch) -> list[str]:
    """Return drift messages; empty means consistent. May raise ExternalUnavailable."""
    drift = []
    pr_cache = {}

    def pr(n):
        if n not in pr_cache:
            pr_cache[n] = fetch(f"pulls/{n}")
        return pr_cache[n]

    for p in state.get("open_prs", []):
        g = pr(p["number"])
        if g.get("_missing"):
            drift.append(f"#{p['number']} is listed as open but does not exist")
        elif g.get("state") != "open":
            how = "merged" if g.get("merged") else "closed"
            drift.append(f"#{p['number']} is listed as open ({p.get('status')}) but GitHub says {how}")
        elif p.get("frozen_sha") and g.get("head", {}).get("sha") != p["frozen_sha"]:
            drift.append(f"#{p['number']} frozen_sha {p['frozen_sha'][:7]} but head is "
                         f"{str(g.get('head', {}).get('sha'))[:7]}: the frozen evidence branch moved")

    for n in state.get("merged_prs", []):
        g = pr(n)
        if not g.get("merged"):
            drift.append(f"#{n} is listed as merged but GitHub says state={g.get('state')}, merged={g.get('merged')}")

    open_or_merged = {p["number"] for p in state.get("open_prs", [])} | set(state.get("merged_prs", []))
    for p in state.get("closed_superseded", []):
        g = pr(p["number"])
        if g.get("state") != "closed" or g.get("merged"):
            drift.append(f"#{p['number']} is listed as closed-superseded but GitHub says "
                         f"state={g.get('state')}, merged={g.get('merged')}")
        if p.get("superseded_by") not in open_or_merged:
            drift.append(f"#{p['number']}'s successor #{p.get('superseded_by')} is not tracked as open or merged")

    for i in state.get("open_issues", []):
        g = fetch(f"issues/{i['number']}")
        if g.get("_missing") or "pull_request" in g:
            drift.append(f"issue #{i['number']} is listed as an open issue but is not an issue")
        elif g.get("state") != "open":
            drift.append(f"issue #{i['number']} is listed as open but GitHub says {g.get('state')}")
    return drift


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", DEFAULT_REPO))
    a = ap.parse_args(argv)
    state = yaml.safe_load(STATE_FILE.read_text(encoding="utf-8"))
    try:
        drift = check(state, github_fetcher(a.repo, os.environ.get("GITHUB_TOKEN")))
    except ExternalUnavailable as e:
        print(f"SKIP_EXTERNAL_CHECK: GitHub not reachable ({e}). This is not a pass; re-run later.")
        if os.environ.get("GITHUB_ACTIONS"):
            print(f"::warning::SKIP_EXTERNAL_CHECK: project-state vs GitHub not verified ({e})")
        return 0
    if drift:
        print("DRIFT: config/project_state.yml disagrees with GitHub:")
        for d in drift:
            print(f"  - {d}")
        print("Fix config/project_state.yml (then docs/PROJECT_STATE.md and the blocker pack).")
        return 1
    print(f"CONSISTENT: {len(state.get('open_prs', []))} open, {len(state.get('merged_prs', []))} merged, "
          f"{len(state.get('closed_superseded', []))} superseded PRs and "
          f"{len(state.get('open_issues', []))} open issues match GitHub")
    return 0


if __name__ == "__main__":
    sys.exit(main())
