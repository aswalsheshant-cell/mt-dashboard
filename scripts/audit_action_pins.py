#!/usr/bin/env python3
"""Audit the GitHub Actions pins in .github/workflows against upstream.

For every `uses: owner/repo[/sub]@<sha>` pin this prints the release tag the SHA
belongs to, the Node runtime its action.yml declares (runs.using), whether the
commit exists upstream at all, and the latest release per major version with its
runtime -- so an upgrade can pick the lowest major that runs on the current
runner Node version (fewest breaking changes).

Read-only; needs network access to github.com (git ls-remote / shallow fetch of
public action repos). Not run in CI -- run it by hand when refreshing pins, then
update VERIFIED_PINS in tests/test_action_pins_node24.py.

Usage: python scripts/audit_action_pins.py
"""
from __future__ import annotations

import collections
import glob
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PIN = re.compile(r"uses:\s*([\w.-]+/[\w.-]+)((?:/[\w.-]+)*)@([0-9a-f]{40})")


def sh(*args, cwd=None):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=300)


def tags_of(repo):
    out = {}
    for line in sh("git", "ls-remote", "--tags", f"https://github.com/{repo}").stdout.splitlines():
        sha, ref = line.split("\t")
        tag = ref.removeprefix("refs/tags/")
        if tag.endswith("^{}"):
            out[tag[:-3]] = sha          # peeled annotated tag wins
        else:
            out.setdefault(tag, sha)
    return {t: s for t, s in out.items() if re.fullmatch(r"v\d+\.\d+\.\d+", t)}


def runtime(workdir, sha, path):
    if sh("git", "fetch", "-q", "--depth", "1", "origin", sha, cwd=workdir).returncode != 0:
        return None                      # commit does not exist upstream
    for p in (path, path.replace(".yml", ".yaml")):
        r = sh("git", "show", f"{sha}:{p}", cwd=workdir)
        if r.returncode == 0:
            m = re.search(r"using:\s*['\"]?([\w-]+)", r.stdout)
            return m.group(1) if m else "?"
    return "?"


def main() -> int:
    pins = collections.defaultdict(set)
    for f in glob.glob(str(ROOT / ".github/workflows/*.y*ml")):
        for m in PIN.finditer(Path(f).read_text(encoding="utf-8")):
            pins[(m.group(1), m.group(2).lstrip("/"))].add(m.group(3))
    bad = 0
    with tempfile.TemporaryDirectory() as tmp:
        for (repo, sub), shas in sorted(pins.items()):
            wd = Path(tmp) / repo.replace("/", "_")
            if not wd.exists():
                sh("git", "init", "-q", str(wd))
                sh("git", "remote", "add", "origin", f"https://github.com/{repo}", cwd=wd)
            path = f"{sub}/action.yml" if sub else "action.yml"
            tags = tags_of(repo)
            rev = {s: t for t, s in tags.items()}
            name = repo + (f"/{sub}" if sub else "")
            for sha in sorted(shas):
                rt = runtime(wd, sha, path)
                bad += rt is None or not str(rt).startswith("node24")
                print(f"{name:32} {sha[:7]}  {rev.get(sha, 'no tag'):9}  "
                      f"{'MISSING UPSTREAM' if rt is None else rt}")
            best = {}
            for t in tags:
                v = tuple(map(int, t[1:].split(".")))
                if v[0] not in best or v > best[v[0]][0]:
                    best[v[0]] = (v, t)
            for major in sorted(best)[-3:]:
                t = best[major][1]
                print(f"{'':32}   latest v{major}: {t} {tags[t][:7]} {runtime(wd, tags[t], path)}")
    print(f"\n{bad} pin(s) not on node24 or missing upstream")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
