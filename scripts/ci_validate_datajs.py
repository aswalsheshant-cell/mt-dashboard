#!/usr/bin/env python3
"""CI step: validate dashboard/data.js JSON integrity and FY27 zone presence."""
import json, sys

print("Validating dashboard/data.js...")
with open("dashboard/data.js", "r") as f:
    content = f.read()

# Strip JS wrapper: window.DASH = {...};
json_str = content.strip()
if json_str.startswith("window.DASH"):
    json_str = json_str.split("=", 1)[1].strip()
    if json_str.endswith(";"):
        json_str = json_str[:-1]

try:
    data = json.loads(json_str)
except json.JSONDecodeError as e:
    print(f"FAIL: JSON parse error: {e}")
    sys.exit(1)

if "offtake" not in data:
    print("FAIL: Missing 'offtake' key in data.js")
    sys.exit(1)

fy27 = data["offtake"].get("zone_monthly_fy27", {})
if not fy27:
    print("WARN: zone_monthly_fy27 is empty — FY27 data may not yet be loaded")
else:
    print(f"OK  data.js — FY27 zones: {', '.join(sorted(fy27.keys()))}")

print("OK  dashboard/data.js is valid JSON")
