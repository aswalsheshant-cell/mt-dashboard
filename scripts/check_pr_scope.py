#!/usr/bin/env python3
"""Feature-freeze PR-scope gate: every PR must say why it is allowed in.

Found 2026-10-01: PR #272 (donut totals, share labels, FYTD measures) passed
every CI check while being outside the feature freeze. Green CI was close to
being read as approved scope; it was deferred by hand. This gate makes the
scope a checked fact instead of a judgement made at merge time.

While config/project_state.yml has feature_freeze.active: true, the PR body
must carry exactly one line

    Freeze classification: <CLASS>

(bold markers around it are fine) where CLASS is one of:

  BLOCKER_FIX      the body names a blocker from project_state.yml (B1-B6)
                   or an open issue listed there (e.g. #120)
  CORRECTNESS_FIX  the body names a regression test file (tests/... or
                   scripts/test_*.py) that is changed or added in this PR
  HOUSEKEEPING     the diff touches no dashboard/, PowerBI/DAX/,
                   PowerBI/PowerQuery/ or scripts/build_dashboard_data.py
  DEFERRED         fails on purpose: a deferred PR must not merge

A title starting with "[DEFERRED" also fails. With the freeze off, every PR
passes (the declaration is then optional).

Exit codes: 0 pass, 1 fail. Reads only local files; no network.

Usage (CI passes these from the pull_request event):
    python scripts/check_pr_scope.py --title "<title>" --body-file body.txt \
        --changed-files-file changed.txt
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
STATE_FILE = ROOT / "config" / "project_state.yml"

CLASSES = ("BLOCKER_FIX", "CORRECTNESS_FIX", "HOUSEKEEPING", "DEFERRED")
DECLARATION = re.compile(r"Freeze classification:\s*\**\s*`?([A-Z_]+)`?", re.I)
# Paths a HOUSEKEEPING PR may not touch: product behaviour and its data.
PROTECTED = ("dashboard/", "PowerBI/DAX/", "PowerBI/PowerQuery/", "scripts/build_dashboard_data.py")
TEST_PATH = re.compile(r"(?<![\w/.-])((?:tests/[\w./-]+)|(?:scripts/test_[\w.-]+\.py))")


def check(title: str, body: str, changed: list[str], state: dict) -> tuple[bool, str]:
    """Return (passed, message). Pure function: no I/O."""
    freeze = state.get("feature_freeze") or {}
    if not freeze.get("active"):
        return True, "PASS: feature freeze is off; no scope declaration required"

    if title.strip().upper().startswith("[DEFERRED"):
        return False, "FAIL: the title marks this PR [DEFERRED]; it must not merge during the freeze"

    found = {m.group(1).upper() for m in DECLARATION.finditer(body or "")}
    if not found:
        return False, ("FAIL: no 'Freeze classification: <CLASS>' line in the PR body. "
                       f"Use one of {', '.join(CLASSES)}.")
    unknown = found - set(CLASSES)
    if unknown:
        return False, f"FAIL: unknown classification {sorted(unknown)}; use one of {', '.join(CLASSES)}"
    if len(found) > 1:
        return False, f"FAIL: more than one classification declared {sorted(found)}; declare exactly one"
    cls = found.pop()

    if cls == "DEFERRED":
        return False, "FAIL: DEFERRED declared; this PR is parked until the freeze lifts"

    if cls == "BLOCKER_FIX":
        blockers = set(state.get("blockers") or {})
        issues = {int(i["number"]) for i in state.get("open_issues") or []}
        named_b = set(re.findall(r"\b(B[1-9])\b", body)) & blockers
        named_i = {int(n) for n in re.findall(r"#(\d+)", body)} & issues
        if not (named_b or named_i):
            return False, (f"FAIL: BLOCKER_FIX must name a blocker {sorted(blockers)} or an open issue "
                           f"{sorted('#%d' % i for i in issues)} from config/project_state.yml")
        return True, f"PASS: BLOCKER_FIX for {', '.join(sorted(named_b) + sorted('#%d' % i for i in named_i))}"

    if cls == "CORRECTNESS_FIX":
        named = set(TEST_PATH.findall(body))
        in_diff = sorted(named & set(changed))
        if not in_diff:
            return False, ("FAIL: CORRECTNESS_FIX must name a regression test file that this PR adds or "
                           f"changes (named: {sorted(named) or 'none'})")
        return True, f"PASS: CORRECTNESS_FIX with regression test {', '.join(in_diff)}"

    # HOUSEKEEPING
    touched = sorted(f for f in changed if f.startswith(PROTECTED))
    if touched:
        return False, ("FAIL: HOUSEKEEPING may not change product code or data; this PR touches "
                       + ", ".join(touched))
    return True, "PASS: HOUSEKEEPING (no dashboard, DAX, Power Query or data-build change)"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--title", required=True)
    ap.add_argument("--body-file", required=True, type=Path)
    ap.add_argument("--changed-files-file", required=True, type=Path)
    a = ap.parse_args(argv)
    state = yaml.safe_load(STATE_FILE.read_text(encoding="utf-8")) or {}
    body = a.body_file.read_text(encoding="utf-8") if a.body_file.exists() else ""
    changed = [ln.strip() for ln in a.changed_files_file.read_text(encoding="utf-8").splitlines() if ln.strip()]
    ok, msg = check(a.title, body, changed, state)
    print(msg)
    if not ok and os.environ.get("GITHUB_ACTIONS"):
        print(f"::error::{msg}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
