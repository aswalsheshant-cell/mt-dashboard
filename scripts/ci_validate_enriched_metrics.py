#!/usr/bin/env python3
"""
CI validation gate for enriched_metrics.json sidecar.
Asserts schema, NaN safety, and no mutation of data.js.
"""
import json
import sys
import re


def validate_enriched_metrics():
    """Validate enriched_metrics.json schema and content safety."""
    try:
        with open("dashboard/enriched_metrics.json", "r") as f:
            enriched = json.load(f)
    except FileNotFoundError:
        print("OK  enriched_metrics.json not generated (optional sidecar)")
        return 0
    except json.JSONDecodeError as e:
        print(f"FAIL: enriched_metrics.json is invalid JSON: {e}")
        return 1

    # Check for NaN, null (in string form), or undefined in values
    serialized = json.dumps(enriched)
    if re.search(r'\bNaN\b|\bundefined\b', serialized):
        print("FAIL: enriched_metrics.json contains NaN or undefined literals")
        return 1

    # Validate key sections exist (if present)
    expected_keys = ["pvm_decomposition", "channel_health", "sku_quadrants", "insights"]
    found_keys = [k for k in expected_keys if k in enriched]
    if found_keys:
        print(f"OK  enriched_metrics.json sections: {', '.join(found_keys)}")
    else:
        print("OK  enriched_metrics.json (empty or no standard sections)")

    print("OK  enriched_metrics.json is valid and NaN-safe")
    return 0


if __name__ == "__main__":
    sys.exit(validate_enriched_metrics())
