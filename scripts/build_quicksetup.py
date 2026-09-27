#!/usr/bin/env python3
"""Generate PowerBI/QuickSetup/AllPowerQuery_Consolidated.txt and
AllDAX_Consolidated.txt from the canonical PowerBI/PowerQuery/*.pq and
PowerBI/DAX/*.dax files (old PR #135, rebuilt as a generator).

The consolidated files used to be copied by hand and drifted: 7 source files
were missing, four DAX sections were older than their sources, and one section
carried an appended stale copy of another file. Now they are generated, and
`--check` (run in the required gate by tests/test_quicksetup_generated.py)
fails when a consolidated file differs from what the sources produce.

Per-step instructions (RENAME QUERY TO / TARGET / NOTE lines), the preambles
and deliberate exclusions live in PowerBI/QuickSetup/quicksetup_steps.json.
Every source file must be listed there under "steps" or "excluded" -- a new
.pq/.dax file fails the build until someone writes its setup instruction or
records why it is left out.

Usage:
    python scripts/build_quicksetup.py           # regenerate both files
    python scripts/build_quicksetup.py --check   # exit 1 if either is out of date
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "PowerBI" / "QuickSetup" / "quicksetup_steps.json"
RULE = "#" * 78


def build(kind: str, cfg: dict) -> str:
    c = cfg[kind]
    sources = sorted(p.name for p in (ROOT / c["source_dir"]).glob(c["glob"]))
    unknown = [s for s in sources if s not in c["steps"] and s not in c["excluded"]]
    if unknown:
        raise SystemExit(f"{kind}: no setup instruction or exclusion recorded for {unknown} "
                         f"-- add them to {CONFIG.relative_to(ROOT)}")
    gone = [s for s in list(c["steps"]) + list(c["excluded"]) if s not in sources]
    if gone:
        raise SystemExit(f"{kind}: {CONFIG.relative_to(ROOT)} lists files that no longer exist: {gone}")
    steps = [s for s in sources if s in c["steps"]]
    out = c["preamble"].replace("{n_files}", str(len(steps)))
    if c["excluded"]:
        out += "*** NOT INCLUDED -- these source files are deliberately left out of this setup:\n"
        for name, why in sorted(c["excluded"].items()):
            out += f"    - {name}: {why}\n"
        out += "\n"
    body = []
    for i, name in enumerate(steps, 1):
        head = f"{RULE}\n# STEP {i:02d}/{len(steps):02d}  --  SOURCE FILE: {name}\n"
        head += "".join(line + "\n" for line in c["steps"][name])
        text = (ROOT / c["source_dir"] / name).read_text(encoding="utf-8").strip("\n")
        body.append(head + RULE + "\n" + text + "\n")
    return out + "\n" + "\n\n\n".join(body)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="exit 1 if a consolidated file is out of date")
    args = ap.parse_args(argv)
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    stale = []
    for kind in ("pq", "dax"):
        want = build(kind, cfg)
        path = ROOT / cfg[kind]["out"]
        have = path.read_text(encoding="utf-8") if path.exists() else None
        if args.check:
            if have != want:
                stale.append(str(path.relative_to(ROOT)))
        elif have != want:
            path.write_text(want, encoding="utf-8")
            print(f"wrote {path.relative_to(ROOT)}")
    if stale:
        print("Out of date (run: python scripts/build_quicksetup.py): " + ", ".join(stale))
        return 1
    if args.check:
        print("QuickSetup consolidated files match their sources.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
