#!/usr/bin/env python3
"""Restricted-source firewall: no NEW confidential raw file may be tracked in Git.

Policy: config/restricted_source_policy.yml. docs/DATA_SECURITY_CLASSIFICATION.md
says raw customer/chain/store/article extracts are CONFIDENTIAL ("gitignored,
never committed") and employee identifiers are RESTRICTED. On 2026-10-01 the
public repository tracked 56 raw extract files plus one seed file with employee
IDs and names, because .gitignore re-includes PowerBI/**/*.csv.

This is a ratchet, not a clean-up:
  * a tracked file under a restricted path, or a CSV whose header carries an
    employee identifier, FAILS unless it is listed in `known_debt`;
  * a `known_debt` file whose content changed (SHA-256 differs) FAILS: debt
    cannot grow silently;
  * a `known_debt` entry for a file no longer tracked FAILS as stale, so the
    list shrinks when the owner removes a file.
Removing known debt from Git (and from history) is the owner's decision I-2;
this script never deletes, moves or rewrites anything.

    python scripts/restricted_source_firewall.py          # exit 1 on any failure
"""
import fnmatch
import hashlib
import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
POLICY = ROOT / "config" / "restricted_source_policy.yml"


def load_policy(path=POLICY):
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def tracked_files(root=ROOT):
    out = subprocess.run(["git", "ls-files", "-z"], cwd=root, capture_output=True, check=True).stdout
    return [p for p in out.decode("utf-8").split("\0") if p]


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def csv_header(path):
    try:
        with open(path, encoding="utf-8-sig", errors="replace") as f:
            return f.readline()
    except OSError:
        return ""


def classify(path, header, policy):
    """Return the restricted class of one tracked file, or None if it is allowed."""
    if any(fnmatch.fnmatch(path, p) for p in policy.get("allowed_patterns", [])):
        return None
    if path.lower().endswith(".csv") and header:
        cols = [c.strip().strip('"') for c in header.split(",")]
        for rx in policy.get("employee_column_patterns", []):
            if any(re.search(rx, c, re.I) for c in cols):
                return "EMPLOYEE_RAW"
    for rule in policy.get("restricted_path_patterns", []):
        if fnmatch.fnmatch(path, rule["pattern"]):
            return rule["class"]
    return None


def check(paths, policy, root=ROOT, header_of=None, hash_of=None):
    header_of = header_of or (lambda p: csv_header(Path(root) / p))
    hash_of = hash_of or (lambda p: sha256(Path(root) / p))
    debt = {d["path"]: d for d in policy.get("known_debt", [])}
    failures, known = [], []
    tracked = set(paths)
    for p in paths:
        cls = classify(p, header_of(p) if p.lower().endswith(".csv") else "", policy)
        if cls is None:
            continue
        if p not in debt:
            failures.append(f"NEW {cls}: {p} is tracked but restricted (move it outside Git; see config/restricted_source_policy.yml)")
        elif hash_of(p) != debt[p]["sha256"]:
            failures.append(f"CHANGED {cls}: {p} differs from its recorded known-debt SHA-256 (restricted debt may not grow)")
        else:
            known.append((cls, p))
    for p in debt:
        if p not in tracked:
            failures.append(f"STALE: known_debt lists {p}, which is no longer tracked; remove the entry")
    return failures, known


def main():
    policy = load_policy()
    failures, known = check(tracked_files(), policy)
    by_cls = {}
    for cls, _ in known:
        by_cls[cls] = by_cls.get(cls, 0) + 1
    print(f"known restricted debt (owner decision {policy.get('owner_decision')}): "
          + ", ".join(f"{k} {v}" for k, v in sorted(by_cls.items())) if known else "no known restricted debt")
    for f in failures:
        print("FAIL", f)
    print("RESULT:", "FAIL" if failures else "PASS (no new restricted file)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
