#!/usr/bin/env python3
"""CI step: validate data_master.json structure and zone taxonomy."""
import json, sys

print("Validating data_master.json...")
with open("data_master.json", "r") as f:
    master = json.load(f)

for key in ["metadata", "zone_metrics_monthly"]:
    if key not in master:
        print(f"FAIL: Missing required key: {key}")
        sys.exit(1)

status = master["metadata"].get("status", "UNKNOWN")
if status != "LOCKED_MULTI_YEAR_V2":
    print(f"WARN: Master status is '{status}' (expected LOCKED_MULTI_YEAR_V2)")

authorized_zones = {"Central", "East", "North", "Pan India", "South 1", "South 2", "West"}
fy27_zones = set(master["zone_metrics_monthly"].get("fy27", {}).keys())
invalid = fy27_zones - authorized_zones
if invalid:
    print(f"FAIL: Invalid zones: {invalid}")
    sys.exit(1)

record_count = master["metadata"].get("record_count", 0)
print(f"OK  data_master.json — status={status}, zones={len(fy27_zones)}, records={record_count}")
