#!/usr/bin/env python3
"""CI step: validate dashboard/data.js JSON integrity, FY27 zones, and baselines.

The baseline check makes Core Invariant 2 deterministic. CLAUDE.md names figures
that must survive every build; until now nothing enforced them, so a rebuild
could silently drop a closed year and no test would notice.

What is protected, and how, is declared in config/baselines.json -- not here --
so a deliberate change is an edit to that file with a reason and an owner,
visible in review.

The functions are importable without side effects so tests exercise this exact
code rather than a second copy of the same logic that could drift from it.
"""
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEFAULT_BASELINE = REPO / "config" / "baselines.json"


def load_datajs(path=None):
    """Parse window.DASH out of data.js."""
    text = Path(path or REPO / "dashboard" / "data.js").read_text()
    m = re.search(r"window\.DASH\s*=\s*", text)
    body = text[m.end():] if m else text
    return json.loads(body.strip().rstrip(";"))


def dig(d, path):
    """Walk a dotted path. Returns None if any step is missing."""
    cur = d
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def check_baselines(data, baseline_path=None):
    """Compare protected values against the declared baseline.

    Returns a list of human-readable failures; empty means every invariant holds.
    """
    bl = Path(baseline_path or DEFAULT_BASELINE)
    if not bl.exists():
        return [f"{bl} missing -- baseline invariants cannot be checked"]
    fails = []
    for c in json.loads(bl.read_text())["checks"]:
        actual = dig(data, c["path"])
        if actual is None:
            fails.append(f"{c['key']}: {c['path']} is missing from data.js "
                         f"(expected {c['expected']} {c['unit']})")
        elif isinstance(actual, bool) or not isinstance(actual, (int, float)):
            fails.append(f"{c['key']}: {c['path']} is {type(actual).__name__}, expected a number")
        elif c["class"] == "tracked_universe" and actual <= 0:
            fails.append(f"{c['key']}: {actual} -- must be positive")
        elif abs(actual - c["expected"]) > c.get("tolerance", 0.01):
            fails.append(
                f"{c['key']}: data.js has {actual}, baseline says {c['expected']} "
                f"{c['unit']} ({c['class']}). "
                + ("History cannot change -- investigate the build."
                   if c["class"] == "frozen_history" else
                   f"If intended, {c['owner']} approves and config/baselines.json is updated."))
    return fails


def main():
    print("Validating dashboard/data.js...")
    try:
        data = load_datajs()
    except json.JSONDecodeError as e:
        print(f"FAIL: JSON parse error: {e}")
        return 1

    if "offtake" not in data:
        print("FAIL: Missing 'offtake' key in data.js")
        return 1

    fy27 = data["offtake"].get("zone_monthly_fy27", {})
    if not fy27:
        print("WARN: zone_monthly_fy27 is empty -- FY27 data may not yet be loaded")
    else:
        print(f"OK  data.js -- FY27 zones: {', '.join(sorted(fy27.keys()))}")
    print("OK  dashboard/data.js is valid JSON")

    problems = check_baselines(data)
    if problems:
        print(f"FAIL: {len(problems)} baseline invariant(s) broken:")
        for p in problems:
            print(f"  - {p}")
        return 1
    n = len(json.loads(DEFAULT_BASELINE.read_text())["checks"])
    print(f"OK  baseline invariants hold ({n} checked)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
