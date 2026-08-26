#!/usr/bin/env python3
"""CI step: validate dashboard/data.js JSON integrity, FY27 zone presence, and universe block."""
import json
import re
import sys
from pathlib import Path

from json_boundary import parse_window_dash_strict

def main() -> int:
    """Validate data.js with comprehensive schema checks."""
    data_path = Path("dashboard/data.js")
    try:
        json_str = data_path.read_text(encoding="utf-8")
    except OSError as e:
        print(f"FAIL: Cannot read {data_path}: {e}")
        return 1

    # NaN/undefined-safe parse: data.js may contain bare NaN or undefined literals
    json_str_clean = re.sub(r'(?<!["\w])NaN(?!["\w])', 'null', json_str)
    json_str_clean = re.sub(r'\bundefined\b', 'null', json_str_clean)
    # Remove trailing commas before ] or } (older serialisers sometimes emit them)
    json_str_clean = re.sub(r',\s*([}\]])', r'\1', json_str_clean)

    try:
        data = json.loads(json_str_clean)
    except json.JSONDecodeError as e:
        print(f"FAIL: JSON parse error: {e}")
        return 1

    # -- Offtake block ----
    if "offtake" not in data:
        print("FAIL: Missing 'offtake' key in data.js")
        return 1

    fy27 = data["offtake"].get("zone_monthly_fy27", {})
    if not fy27:
        print("WARN: zone_monthly_fy27 is empty — FY27 data may not yet be loaded")
    else:
        print(f"OK  offtake — FY27 zones: {', '.join(sorted(fy27.keys()))}")

    # -- Universe block ----
    if "universe" not in data:
        print("FAIL: 'universe' key missing from data.js — sync_data_js.py may not have run with UniverseMT.csv")
        return 1

    u = data["universe"]

    # 1. n_stores > 0 (accept either key: active_stores or n_stores alias)
    n_stores = u.get("active_stores") or u.get("n_stores") or u.get("total_stores") or 0
    if not isinstance(n_stores, (int, float)) or n_stores <= 0:
        print(f"FAIL: universe.active_stores is {n_stores!r} — expected a positive integer (426)")
        return 1

    # 2. n_chains > 0
    by_chain = u.get("by_chain", [])
    n_chains = u.get("n_chains") or len(by_chain)
    if not isinstance(n_chains, (int, float)) or n_chains <= 0:
        print(f"FAIL: universe.n_chains is {n_chains!r} — expected a positive integer")
        return 1

    # 3. by_chain schema: must be a list where every entry has 'name' (str) and 'stores' (int)
    if not isinstance(by_chain, list):
        print(f"FAIL: universe.by_chain is {type(by_chain).__name__}, expected list")
        return 1
    if len(by_chain) == 0:
        print("FAIL: universe.by_chain is empty — chain breakdown absent")
        return 1
    bad_entries = [
        i for i, e in enumerate(by_chain)
        if not isinstance(e, dict)
        or not isinstance(e.get("name"), str)
        or not e.get("name", "").strip()
        or not isinstance(e.get("stores"), (int, float))
        or e.get("stores", 0) <= 0
    ]
    if bad_entries:
        print(f"FAIL: universe.by_chain has {len(bad_entries)} malformed entries at indices {bad_entries[:5]}")
        print(f"      Each entry must have {{\"name\": <str>, \"stores\": <int>}}")
        return 1

    # 4. inactive_stores must be present (non-negative int)
    n_inactive = u.get("inactive_stores")
    if n_inactive is None:
        print("WARN: universe.inactive_stores missing — older sync_data_js.py may have generated this file")
    elif not isinstance(n_inactive, (int, float)) or n_inactive < 0:
        print(f"FAIL: universe.inactive_stores is {n_inactive!r} — expected a non-negative integer")
        return 1

    inactive_note = f", {int(n_inactive)} inactive" if n_inactive is not None else ""
    print(f"OK  universe block — {int(n_stores)} active stores{inactive_note}, {int(n_chains)} chains, "
          f"by_chain[{len(by_chain)}] schema valid")

    # -- Final ----
    print("OK  dashboard/data.js is valid JSON")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
