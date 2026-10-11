"""Copy data files that exist only on an unmerged branch into a local folder, outside Git's reach.

Some data files were committed on branches that were never merged (see docs/evidence/DATA_SOURCE_MAP.md
and the ledger). This copies chosen ones out with `git show`, so nothing is checked out or switched.

* Files go under PowerBI/RawDataFolders/... or PowerBI/SeedData/... on the same relative path.
  New CSVs under PowerBI/RawDataFolders are ignored by Git (see .gitignore), so a restored raw file
  cannot be committed by accident. A restored SeedData file would show up as a new file in `git status`:
  only keep it there after the owner has approved it.
* It never overwrites an existing file. It writes a small manifest (restored_files.csv) with SHA-256.
* A raw extract being restored here does not make any query read it. Queries read what is listed in
  docs/evidence/DATA_SOURCE_MAP.md.

Usage:
  git fetch origin
  python scripts/restore_branch_files.py --list
  python scripts/restore_branch_files.py claude/offline-agent-pbi-workflow-08cz7j PowerBI/RawDataFolders/Offtake_Monthly_SIS/SIS_offtake_store_article_Apr_25.csv
  python scripts/restore_branch_files.py claude/po-billing-fill-rate 'PowerBI/SeedData/Forecast/*' --dest D:\\mt-dashboard
"""

import argparse
import csv
import fnmatch
import hashlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCOPE = ("PowerBI/RawDataFolders", "PowerBI/SeedData", "data", "dashboard")


def git(*args, cwd=ROOT):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True)


def ref_for(branch, cwd=ROOT):
    for ref in (branch, "origin/" + branch):
        if git("rev-parse", "--verify", "--quiet", ref, cwd=cwd).returncode == 0:
            return ref
    return None


def list_branch_files(ref, cwd=ROOT):
    out = git("ls-tree", "-r", "-z", "--name-only", ref, "--", *SCOPE, cwd=cwd).stdout.decode("utf-8")
    return [p for p in out.split("\0") if p]


def restore(branch, patterns, dest, cwd=ROOT):
    ref = ref_for(branch, cwd)
    if ref is None:
        raise SystemExit("Branch '%s' not found. Run: git fetch origin" % branch)
    head = set(list_branch_files("HEAD", cwd))
    wanted = [p for p in list_branch_files(ref, cwd) if any(fnmatch.fnmatch(p, pat) for pat in patterns)]
    if not wanted:
        raise SystemExit("No file on %s matches %s" % (ref, patterns))
    rows = []
    for rel in wanted:
        target = Path(dest) / rel
        if target.exists():
            rows.append((rel, "SKIPPED (already exists)", ""))
            continue
        blob = git("show", "%s:%s" % (ref, rel), cwd=cwd)
        if blob.returncode != 0:
            rows.append((rel, "FAILED", ""))
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(blob.stdout)
        note = "restored" + ("" if rel not in head else " (same path also on HEAD)")
        rows.append((rel, note, hashlib.sha256(blob.stdout).hexdigest()))
    manifest = Path(dest) / "restored_files.csv"
    new = not manifest.exists()
    with open(manifest, "a", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        if new:
            w.writerow(["path", "result", "sha256", "branch"])
        for r in rows:
            w.writerow([*r, ref])
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("branch", nargs="?")
    ap.add_argument("patterns", nargs="*", help="paths or glob patterns, as printed by --list")
    ap.add_argument("--dest", default=str(ROOT), help="repo root to restore into (default: this repo)")
    ap.add_argument("--list", action="store_true", help="list data files that exist only on unmerged branches")
    args = ap.parse_args()
    if args.list:
        head = set(list_branch_files("HEAD"))
        for b in git("branch", "-r").stdout.decode().split():
            if "HEAD" in b or b.endswith(("origin/main", "origin/gh-pages", "->")):
                continue
            only = [p for p in list_branch_files(b) if p not in head and p.endswith((".csv", ".json", ".js", ".xlsx", ".xlsb", ".zip"))
                    and "PBIR_Generated" not in p and "node_modules" not in p]
            if only:
                print("%s  (%d files)" % (b.replace("origin/", ""), len(only)))
                for p in only[:50]:
                    print("    " + p)
        return 0
    if not args.branch or not args.patterns:
        ap.error("give a branch and at least one path or pattern (or use --list)")
    for rel, result, sha in restore(args.branch, args.patterns, args.dest):
        print("%-60s %s %s" % (rel, result, sha[:12]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
