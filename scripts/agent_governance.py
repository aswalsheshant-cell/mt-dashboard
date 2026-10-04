#!/usr/bin/env python3
"""Decision governance for agents: evaluate a decision, log it, check the log.

The rules live in config/agent_decision_policy.yml, outside the agent, so the
agent cannot talk its way past them. Three jobs:

  evaluate(decision)  -> ALLOWED / NEEDS_APPROVAL / BLOCKED, with reasons
  record(decision)    -> append to governance/decision_log.jsonl (hash-chained)
  check_log()         -> fail if any record breaks a rule or the chain is broken

CLI:
  python scripts/agent_governance.py check [--log PATH]
  python scripts/agent_governance.py audit --base main [--head HEAD]
  python scripts/agent_governance.py evaluate decision.json
"""
import argparse
import fnmatch
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
POLICY_PATH = REPO / "config" / "agent_decision_policy.yml"
LOG_PATH = REPO / "governance" / "decision_log.jsonl"

ALLOWED, NEEDS_APPROVAL, BLOCKED = "ALLOWED", "NEEDS_APPROVAL", "BLOCKED"


def load_policy(path=None):
    return yaml.safe_load(Path(path or POLICY_PATH).read_text())


def _is_protected(path, patterns):
    path = path.lstrip("./")
    for pat in patterns:
        if fnmatch.fnmatch(path, pat) or fnmatch.fnmatch(path, pat.replace("**/", "")):
            return True
        if pat.endswith("/**") and path.startswith(pat[:-3] + "/"):
            return True
    return False


def evaluate(decision, policy=None):
    """Return {"verdict": ..., "level": ..., "reasons": [...]}. Fails closed.

    problems = the record itself is incomplete -> BLOCKED
    notes    = why a human is needed (informational)
    """
    policy = policy or load_policy()
    problems, notes = [], []

    missing = [f for f in policy["required_fields"] if not decision.get(f)]
    if missing:
        problems.append("missing required field(s): " + ", ".join(missing))

    label = decision.get("label")
    if label not in policy["labels"]:
        problems.append(f"label {label!r} is not one of {policy['labels']}")
    elif label in policy["labels_needing_evidence"] and not decision.get("evidence"):
        problems.append(f"label {label} needs at least one evidence reference")

    actor, cls = decision.get("actor"), decision.get("action_class")
    agent = policy.get("agents", {}).get(actor)
    if actor and not agent:
        problems.append(f"actor {actor!r} is not a registered agent")
    elif agent and cls not in agent["allowed"]:
        problems.append(f"{actor} is not allowed to use {cls}")

    for item in decision.get("evidence") or []:
        if not (isinstance(item, dict) and item.get("type") in policy["evidence_types"]):
            problems.append("evidence must be a verifiable {type: file|commit} entry, not free text")
            break

    spec = policy["action_classes"].get(cls)
    level = spec["level"] if spec else policy["default_level"]
    if not spec:
        notes.append(f"unknown action_class {cls!r}: treated as {level}")

    if level == "FORBIDDEN":
        return {"verdict": BLOCKED, "level": level,
                "reasons": problems + [f"{cls} is forbidden for agents"]}

    gate = (spec or {}).get("blocked_until")
    if gate and not policy.get(gate):
        return {"verdict": BLOCKED, "level": level,
                "reasons": problems + [f"{cls} is blocked until {gate} is true in the policy"]}

    hit = [p for p in decision.get("paths", []) if _is_protected(p, policy["protected_paths"])]
    if hit:
        level = "HUMAN_APPROVAL"
        notes.append("protected path(s) touched: " + ", ".join(hit))

    if level == "AUTO_LOG" and not decision.get("evidence"):
        problems.append("AUTO_LOG actions need an evidence reference")

    if problems:
        return {"verdict": BLOCKED, "level": level, "reasons": problems + notes}
    appr = decision.get("approver")
    if level == "HUMAN_APPROVAL":
        if appr and appr == actor:
            return {"verdict": BLOCKED, "level": level, "reasons": ["an agent cannot approve its own action"]}
        if not appr or appr not in (policy.get("approvers") or []):
            why = "approver is not on the approved list" if appr else "named approver required"
            return {"verdict": NEEDS_APPROVAL, "level": level, "reasons": notes + [why]}
    return {"verdict": ALLOWED, "level": level, "reasons": notes}


def verify_evidence(decision, repo=None):
    """Check evidence against the repo itself (I/O). Returns a list of problems."""
    repo = Path(repo or REPO)
    out = []
    for item in decision.get("evidence") or []:
        if not isinstance(item, dict):
            continue
        if item.get("type") == "file":
            f = repo / item.get("path", "")
            if not f.is_file():
                out.append(f"evidence file not found: {item.get('path')}")
            elif hashlib.sha256(f.read_bytes()).hexdigest() != item.get("sha256"):
                out.append(f"evidence file changed since it was recorded: {item.get('path')}")
        elif item.get("type") == "commit":
            ok = subprocess.run(["git", "-C", str(repo), "cat-file", "-e", f"{item.get('sha')}^{{commit}}"],
                                capture_output=True).returncode == 0
            if not ok:
                out.append(f"evidence commit not found: {item.get('sha')}")
    return out


def _hash(record):
    body = {k: v for k, v in record.items() if k != "hash"}
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()


def record(decision, log_path=None, policy=None, repo=None):
    """Append a decision to the log. Refuses anything not ALLOWED."""
    result = evaluate(decision, policy)
    if result["verdict"] != ALLOWED:
        raise PermissionError(f"{result['verdict']}: " + "; ".join(result["reasons"]))
    bad = verify_evidence(decision, repo)
    if bad:
        raise PermissionError("BLOCKED: " + "; ".join(bad))
    path = Path(log_path or LOG_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    prev = "GENESIS"
    if path.exists():
        lines = [l for l in path.read_text().splitlines() if l.strip()]
        if lines:
            prev = json.loads(lines[-1])["hash"]
    rec = dict(decision, prev_hash=prev)
    rec["hash"] = _hash(rec)
    with path.open("a") as f:
        f.write(json.dumps(rec, sort_keys=True) + "\n")
    return rec


def check_log(log_path=None, policy=None, repo=None):
    """Return a list of problems. Empty list = log is clean (or not started yet)."""
    path = Path(log_path or LOG_PATH)
    if not path.exists():
        return []
    problems, prev = [], "GENESIS"
    for n, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except ValueError:
            problems.append(f"line {n}: not valid JSON")
            continue
        if rec.get("prev_hash") != prev:
            problems.append(f"line {n}: chain broken (prev_hash does not match)")
        if rec.get("hash") != _hash(rec):
            problems.append(f"line {n}: record was edited after it was written")
        res = evaluate(rec, policy)
        if res["verdict"] != ALLOWED:
            problems.append(f"line {n} ({rec.get('id')}): {res['verdict']} - " + "; ".join(res["reasons"]))
        for bad in verify_evidence(rec, repo):
            problems.append(f"line {n} ({rec.get('id')}): {bad}")
        prev = rec.get("hash")
    return problems


def _git(repo, *args):
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip() or "git failed")
    return r.stdout.split()


def audit_range(base, head="HEAD", log_path=None, policy=None, repo=None):
    """Reconcile real changes against the decision log.

    Every commit in base..head that touches a protected path must be covered by a
    logged, approved decision: the record lists that commit as evidence and lists
    each protected file the commit touched. A commit with no such record is an
    ungoverned operation -- it happened, but no decision governed it.
    Returns a list of problems (empty = every protected change is governed).
    """
    policy = policy or load_policy()
    repo = repo or REPO
    path = Path(log_path or LOG_PATH)
    records = []
    if path.exists():
        records = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    problems = []
    for sha in _git(repo, "rev-list", f"{base}..{head}"):
        files = _git(repo, "diff-tree", "--no-commit-id", "--name-only", "-r", "-m", "--root", sha)
        touched = [f for f in files if _is_protected(f, policy["protected_paths"])]
        if not touched:
            continue
        covered = False
        for rec in records:
            shas = [e.get("sha", "") for e in rec.get("evidence", []) if isinstance(e, dict) and e.get("type") == "commit"]
            if any(sha.startswith(x) or x.startswith(sha) for x in shas if x) \
                    and set(touched) <= set(rec.get("paths", [])) \
                    and evaluate(rec, policy)["verdict"] == ALLOWED:
                covered = True
                break
        if not covered:
            problems.append(f"commit {sha[:10]} changed protected file(s) {', '.join(touched)} "
                            f"with no approved decision record")
    return problems


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("--log", default=None)
    a = sub.add_parser("audit", help="every protected-path commit in base..head must have an approved decision")
    a.add_argument("--base", required=True)
    a.add_argument("--head", default="HEAD")
    a.add_argument("--log", default=None)
    e = sub.add_parser("evaluate")
    e.add_argument("decision_json")
    args = ap.parse_args(argv)

    if args.cmd == "check":
        problems = check_log(args.log)
        for p in problems:
            print("FAIL", p)
        print("PASS: decision log clean" if not problems else f"{len(problems)} problem(s)")
        return 1 if problems else 0
    if args.cmd == "audit":
        problems = audit_range(args.base, args.head, args.log)
        for p in problems:
            print("UNGOVERNED", p)
        print("PASS: all protected changes are governed" if not problems else f"{len(problems)} ungoverned change(s)")
        return 1 if problems else 0
    result = evaluate(json.loads(Path(args.decision_json).read_text()))
    print(json.dumps(result, indent=2))
    return 0 if result["verdict"] == ALLOWED else 1


if __name__ == "__main__":
    sys.exit(main())
