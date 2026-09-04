#!/usr/bin/env python3
"""CI step: validate dashboard/data.js JSON integrity and FY27 zone presence."""
import argparse
from pathlib import Path

from json_boundary import parse_window_dash_strict


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="dashboard/data.js")
    args = parser.parse_args()

    print(f"Validating {args.data}...")
    try:
        data = parse_window_dash_strict(Path(args.data).read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        print(f"FAIL: strict JSON parse error: {exc}")
        return 1

    if "offtake" not in data:
        print("FAIL: Missing 'offtake' key in data.js")
        return 1

    fy27 = data["offtake"].get("zone_monthly_fy27", {})
    if not fy27:
        print("WARN: zone_monthly_fy27 is empty — FY27 data may not yet be loaded")
    else:
        print(f"OK  data.js — FY27 zones: {', '.join(sorted(fy27.keys()))}")

    print("OK  dashboard/data.js is valid strict JSON")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

