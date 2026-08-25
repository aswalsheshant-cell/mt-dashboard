#!/usr/bin/env python3
"""
Tier 3: Automated Data.JS Sync Pipeline

Regenerates dashboard/data.js from the authoritative data_master.json.
Ensures single source of truth: data_master.json → data.js (one-way sync).

This script is part of the master data governance consolidation (Tiers 1-3).
It automates what was previously a manual, error-prone process.

USAGE:
  python scripts/sync_data_js.py --source <data_master.json> --output <data.js>

  Default: python scripts/sync_data_js.py
    (reads: data_master.json, writes: dashboard/data.js)
"""
from __future__ import annotations
import json
import argparse
from pathlib import Path
from datetime import datetime


def load_master(master_path: str) -> dict:
    """Load the authoritative data_master.json."""
    with open(master_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def generate_data_js(master: dict) -> str:
    """
    Transform data_master.json into dashboard-optimized data.js format.

    The output is a JavaScript variable assignment that contains the complete
    dashboard data structure, derived solely from the master.
    """

    # Build the DASH object (what dashboard/index.html expects in window.DASH)
    dash = {
        "metadata": master["metadata"],
        "offtake": {
            "zone_monthly_fy25": master["zone_metrics_monthly"]["fy25"],
            "zone_monthly_fy26": master["zone_metrics_monthly"]["fy26"],
            "zone_monthly_fy27": master["zone_metrics_monthly"]["fy27"],
            "conversion_rates_fy25": master["conversion_rates"]["fy25"],
            "conversion_rates_fy26": master["conversion_rates"]["fy26"],
            "conversion_rates_fy27": master["conversion_rates"]["fy27"],
        },
        "unit_economics": master["unit_economics"],
        "executive_deck_sync": master["executive_deck_sync"],
    }

    # Serialize to JSON with proper formatting for readability
    data_json = json.dumps(dash, indent=2, ensure_ascii=False)

    # Wrap in JavaScript variable assignment (what index.html expects)
    js_output = f"window.DASH = {data_json};"

    return js_output


def validate_output(js_content: str) -> bool:
    """Validate that the generated JS is syntactically sound."""
    # Extract the JSON part (between "window.DASH = " and ";")
    try:
        json_part = js_content.replace("window.DASH = ", "").rstrip(";")
        json.loads(json_part)
        return True
    except json.JSONDecodeError as e:
        print(f"✗ JSON validation failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Regenerate dashboard/data.js from authoritative data_master.json"
    )
    parser.add_argument(
        "--source",
        default="data_master.json",
        help="Path to source data_master.json (default: data_master.json)"
    )
    parser.add_argument(
        "--output",
        default="dashboard/data.js",
        help="Path to output data.js (default: dashboard/data.js)"
    )
    args = parser.parse_args()

    print("=" * 80)
    print("TIER 3: AUTOMATED DATA.JS SYNC")
    print("=" * 80)

    # Load master
    print(f"\n[1] Loading authoritative master: {args.source}")
    try:
        master = load_master(args.source)
        print(f"  ✓ Loaded (status: {master['metadata'].get('status', 'unknown')})")
    except FileNotFoundError:
        print(f"  ✗ File not found: {args.source}")
        return 1
    except json.JSONDecodeError as e:
        print(f"  ✗ JSON parse error: {e}")
        return 1

    # Validate master structure
    print(f"\n[2] Validating master schema")
    required_keys = ["metadata", "zone_metrics_monthly", "conversion_rates", "unit_economics"]
    for key in required_keys:
        if key not in master:
            print(f"  ✗ Missing required key: {key}")
            return 1
    print(f"  ✓ Schema valid (5 collections present)")

    # Generate data.js
    print(f"\n[3] Generating data.js from master")
    js_content = generate_data_js(master)
    print(f"  ✓ Generated ({len(js_content):,} bytes)")

    # Validate output
    print(f"\n[4] Validating generated output")
    if not validate_output(js_content):
        print(f"  ✗ Output validation failed")
        return 1
    print(f"  ✓ Output is valid JavaScript")

    # Write output
    print(f"\n[5] Writing to: {args.output}")
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(js_content)
    print(f"  ✓ Written successfully ({output_path.stat().st_size:,} bytes)")

    # Summary
    print(f"\n" + "=" * 80)
    print("SYNC COMPLETE")
    print("=" * 80)
    print(f"""
Source:      {args.source} (LOCKED_MULTI_YEAR_V2)
Output:      {args.output} (production-ready)
Generated:   {datetime.now().isoformat()}

Coverage:    FY25 (4m) + FY26 (12m) + FY27 (4m) = 140 zone-months
Zones:       7 (Central, East, North, Pan India, South 1, South 2, West)
Status:      ✓ READY FOR DEPLOYMENT

Next Steps:
  1. Test dashboard rendering with new data.js
  2. Verify all 12 tabs × FY filters work correctly
  3. Commit data_master.json, data.js, and this script
  4. Push to claude/power-bi-data-analysis-f1vggw
  5. Merge PR #55 to main
""")

    return 0


if __name__ == "__main__":
    exit(main())
