#!/usr/bin/env python3
"""Add the CM2 provisional-governance flags to an existing dashboard/data.js.

Why this exists: `build_dashboard_data.py` now emits `provisional`,
`formula_status`, `provisional_reasons` and `example_data_only` inside the cm2
block (see `_cm2_provisional_state`), but a full rebuild needs every source
workbook and those are gitignored. This performs the same computation against
the tracked config and merges only those keys into the committed data.js, the
way scripts/fix_d13_mrp.py did for D13.

It is idempotent: it recomputes the flags from config every run, so once the
formula is APPROVED and real expense rows replace the EXAMPLE rows, re-running
this clears the banner. No CM2 amount is ever touched.

    python3 scripts/patch_cm2_provisional.py --dry-run
    python3 scripts/patch_cm2_provisional.py
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_JS = ROOT / "dashboard" / "data.js"
PREFIX_RE = re.compile(r"\s*window\.DASH\s*=\s*")

sys.path.insert(0, str(ROOT / "scripts"))
from build_dashboard_data import _cm2_provisional_state, load_pl_expense_input  # noqa: E402

MANAGED_KEYS = (
    "formula_status", "provisional", "provisional_label",
    "provisional_reasons", "example_data_only",
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--data-js", default=str(DATA_JS))
    args = ap.parse_args()

    path = Path(args.data_js)
    text = path.read_text(encoding="utf-8")
    m = PREFIX_RE.match(text)
    if not m:
        print("ERROR: data.js does not start with `window.DASH =`", file=sys.stderr)
        return 2
    prefix, payload = text[: m.end()], text[m.end():].rstrip().rstrip(";")
    dash = json.loads(payload)

    if "cm2" not in dash:
        print("ERROR: no cm2 block in data.js", file=sys.stderr)
        return 2

    state = _cm2_provisional_state(load_pl_expense_input())
    before = {k: dash["cm2"].get(k) for k in MANAGED_KEYS}

    if before == state:
        print("Already up to date — no change.")
        return 0

    print("cm2 governance flags:")
    for k in MANAGED_KEYS:
        print(f"  {k}: {before.get(k)!r} -> {state[k]!r}")

    if args.dry_run:
        print("\n--dry-run: nothing written.")
        return 0

    # Amounts must be untouched — assert before and after.
    amounts = {k: dash["cm2"].get(k) for k in
               ("total_nsv", "total_expense", "cm2_value", "cm2_pct")}
    dash["cm2"].update(state)
    assert {k: dash["cm2"].get(k) for k in amounts} == amounts, "CM2 amounts changed"

    backup = path.with_suffix(path.suffix + ".cm2prov.bak")
    shutil.copy2(path, backup)
    path.write_text(prefix + json.dumps(dash, ensure_ascii=False,
                                        separators=(",", ":")) + ";\n",
                    encoding="utf-8")
    print(f"\nWrote {path}  (backup: {backup.name})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
