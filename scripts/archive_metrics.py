#!/usr/bin/env python3
"""
Archive monthly dashboard metrics to enable YoY comparisons.
Extracts JSON payload from data.js and saves it to archive/YYYY-MM/data.json
for historical comparison in Phase 4.2 (YoY Performance Comparison).
"""

import os
import json
import re
from datetime import datetime


def archive_current_data():
    """Extract current data.js metrics and save to monthly archive."""

    # Define paths
    source_file = os.path.join("dashboard", "data.js")
    archive_base_dir = "archive"

    # Use current year-month for the folder (e.g., "2026-09")
    current_month = datetime.now().strftime("%Y-%m")
    archive_dir = os.path.join(archive_base_dir, current_month)

    if not os.path.exists(source_file):
        print(f"⚠️  Source file {source_file} not found. Skipping archive.")
        return

    # Read the data.js file
    try:
        with open(source_file, "r", encoding="utf-8") as f:
            content = f.read()
    except IOError as e:
        print(f"❌ Error reading {source_file}: {e}")
        return

    # Extract the JSON payload from window.DASH={...}; (accounting for nested braces)
    # Find opening brace after window.DASH=
    start_idx = content.find('window.DASH=')
    if start_idx == -1:
        print("❌ Error: Could not locate 'window.DASH=' in data.js")
        return

    # Find the opening brace
    brace_start = content.find('{', start_idx)
    if brace_start == -1:
        print("❌ Error: Could not locate opening brace in data.js")
        return

    # Count braces to find matching closing brace
    brace_count = 0
    for i in range(brace_start, len(content)):
        if content[i] == '{':
            brace_count += 1
        elif content[i] == '}':
            brace_count -= 1
            if brace_count == 0:
                raw_json = content[brace_start:i+1]
                break
    else:
        print("❌ Error: Could not find matching closing brace")
        return

    # Validate it's proper JSON before saving
    try:
        parsed_data = json.loads(raw_json)
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON payload extracted. {e}")
        return

    # Create archive directory if it doesn't exist
    try:
        os.makedirs(archive_dir, exist_ok=True)
    except OSError as e:
        print(f"❌ Error creating archive directory: {e}")
        return

    # Save the snapshot (minified to save space)
    archive_path = os.path.join(archive_dir, "data.json")
    try:
        with open(archive_path, "w", encoding="utf-8") as f:
            json.dump(parsed_data, f, separators=(',', ':'))

        file_size_mb = os.path.getsize(archive_path) / (1024 * 1024)
        print(f"✅ Successfully archived current metrics to {archive_path}")
        print(f"   Archived file size: {file_size_mb:.2f} MB")
        print(f"   Archive period: {current_month}")

    except IOError as e:
        print(f"❌ Error writing archive file: {e}")
        return


if __name__ == "__main__":
    archive_current_data()
