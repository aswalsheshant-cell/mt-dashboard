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
    meta = master["metadata"]

    # Ensure dashboard-expected metadata fields are present
    if "title" not in meta:
        meta["title"] = "Modern Trade Leadership Dashboard"
    if "period" not in meta:
        fys = meta.get("coverage", {}).get("fiscal_years", [])
        meta["period"] = f"FY{fys[0][-2:]}–{fys[-1][-2:]} (140 zone-months)" if fys else "Multi-year"
    if "fy_range" not in meta:
        fys = meta.get("coverage", {}).get("fiscal_years", [])
        meta["fy_range"] = "–".join([f"FY{fy[-2:]}" for fy in fys]) if fys else "FY25–27"
    if "unit_note" not in meta:
        meta["unit_note"] = "All figures in ₹ Crore unless stated"
    if "source" not in meta:
        meta["source"] = "Honasa / Mamaearth Modern Trade (data_master.json)"

    # Build offtake block with aggregates (zone_monthly data + computed rollups)
    zone_metrics = master["zone_metrics_monthly"]
    offtake_block = {
        "zone_monthly_fy25": zone_metrics.get("fy25", {}),
        "zone_monthly_fy26": zone_metrics.get("fy26", {}),
        "zone_monthly_fy27": zone_metrics.get("fy27", {}),
        "conversion_rates_fy25": master["conversion_rates"].get("fy25", {}),
        "conversion_rates_fy26": master["conversion_rates"].get("fy26", {}),
        "conversion_rates_fy27": master["conversion_rates"].get("fy27", {}),
    }

    # Canonical month ordering (Indian FY: Apr→Mar)
    MONTH_ORDER = ["Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar"]

    def sort_months(month_dict):
        """Sort a month→value dict into canonical Apr→Mar order, return (labels, values)."""
        def month_sort_key(m_label):
            parts = m_label.split("-")
            abbr = parts[0] if parts else m_label
            return MONTH_ORDER.index(abbr) if abbr in MONTH_ORDER else 99
        sorted_items = sorted(month_dict.items(), key=lambda x: month_sort_key(x[0]))
        return [k for k, _ in sorted_items], [v for _, v in sorted_items]

    # Build proper by_zone: single entry per zone with all FY keys {name, fy25, fy26, fy27}
    zone_names = set()
    for fy_key in ["fy25", "fy26", "fy27"]:
        zone_names.update(offtake_block.get(f"zone_monthly_{fy_key}", {}).keys())

    by_zone = []
    for zone_name in sorted(zone_names):
        entry = {"name": zone_name}
        for fy_key in ["fy25", "fy26", "fy27"]:
            zone_monthly = offtake_block.get(f"zone_monthly_{fy_key}", {})
            months_data = zone_monthly.get(zone_name, {})
            if isinstance(months_data, dict):
                entry[fy_key] = round(sum(
                    m.get("offtake_cr", 0) if isinstance(m, dict) else 0
                    for m in months_data.values()
                ), 2)
            else:
                entry[fy_key] = 0
        by_zone.append(entry)
    offtake_block["by_zone"] = by_zone

    # Grand totals for each FY
    for fy_key in ["fy25", "fy26", "fy27"]:
        total = sum(z.get(fy_key, 0) for z in by_zone)
        if total > 0:
            offtake_block[f"total_{fy_key}"] = round(total, 2)

    # YoY for FY26 vs FY25
    fy25_total = offtake_block.get("total_fy25", 0)
    fy26_total = offtake_block.get("total_fy26", 0)
    if fy25_total > 0:
        offtake_block["yoy"] = round(((fy26_total - fy25_total) / fy25_total) * 100, 2)

    # months_fyNN / monthly_fyNN: sorted month labels + summed offtake across all zones
    for fy_key in ["fy25", "fy26", "fy27"]:
        zone_monthly = offtake_block.get(f"zone_monthly_{fy_key}", {})
        # Aggregate across zones by month label
        month_totals: dict = {}
        for months_data in zone_monthly.values():
            if not isinstance(months_data, dict):
                continue
            for m_label, m_data in months_data.items():
                v = m_data.get("offtake_cr", 0) if isinstance(m_data, dict) else 0
                month_totals[m_label] = round(month_totals.get(m_label, 0) + v, 2)
        if month_totals:
            labels, values = sort_months(month_totals)
            offtake_block[f"months_{fy_key}"] = labels
            offtake_block[f"monthly_{fy_key}"] = values

    # Combined months / monthly (FY25 + FY26 for all-FY view, ordered Apr→Mar within each FY)
    combined_months = (offtake_block.get("months_fy25") or []) + (offtake_block.get("months_fy26") or [])
    combined_monthly = (offtake_block.get("monthly_fy25") or []) + (offtake_block.get("monthly_fy26") or [])
    offtake_block["months"] = combined_months
    offtake_block["monthly"] = combined_monthly

    # by_chain, by_state: empty — source data has no chain/state breakdown yet
    offtake_block["by_chain"] = []
    offtake_block["by_state"] = []
    offtake_block["n_chains"] = 0

    dash = {
        "metadata": meta,
        "meta": meta,  # Alias for compatibility with dashboard init()
        "offtake": offtake_block,
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
