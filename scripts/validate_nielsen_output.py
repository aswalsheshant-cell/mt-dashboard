#!/usr/bin/env python3
"""
Structural validation for a generated Nielsen market-share dashboard HTML file
(scripts/build_nielsen_dashboard.py's output).

Replaces a size-based heuristic ("~238KB expected") that went stale the day
Chart.js was extracted from an inline ~205KB blob to an external
<script src="chart.umd.js"> reference -- the correct output shrank to ~36KB,
which the old check misread as a broken build. Size is not a reliable proxy
for "did the template render correctly"; the checks below test the specific
things a correct render actually requires.
"""
import re
import sys

# A real build has never been anywhere near this small; catches a genuinely
# empty/truncated file without assuming a particular Chart.js embedding style.
MIN_SANE_SIZE_KB = 20
MIN_CANVAS_COUNT = 5


def validate_nielsen_html(html: str) -> list[str]:
    """Return a list of validation error strings; empty list = valid."""
    errors = []

    if re.search(r"__[A-Z][A-Z0-9_]*__", html):
        errors.append("Unresolved template placeholder remains (matches __NAME__ pattern)")

    if '"MONTHS"' not in html:
        errors.append("MONTHS key missing from injected Nielsen data payload")

    canvas_count = html.count("<canvas id=")
    if canvas_count < MIN_CANVAS_COUNT:
        errors.append(f"Expected >={MIN_CANVAS_COUNT} canvas elements, found {canvas_count}")

    size_kb = len(html) // 1024
    if size_kb < MIN_SANE_SIZE_KB:
        errors.append(f"Output suspiciously small: {size_kb}KB (expected >={MIN_SANE_SIZE_KB}KB)")

    if 'chart.umd.js"' not in html:
        errors.append('Chart.js external reference missing (expected <script src="chart.umd.js">)')

    if 'id="bridge-wrap"' not in html:
        errors.append('Required dashboard container missing (expected id="bridge-wrap")')

    if "DOMContentLoaded" not in html:
        errors.append("Required chart initialization entrypoint missing (DOMContentLoaded listener)")

    return errors


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts/validate_nielsen_output.py <path-to-generated-html>")
        return 2

    html_path = sys.argv[1]
    with open(html_path, encoding="utf-8") as f:
        html = f.read()

    errors = validate_nielsen_html(html)
    if errors:
        for e in errors:
            print(f"FAIL: {e}")
        return 1

    size_kb = len(html) // 1024
    canvas_count = html.count("<canvas id=")
    print(f"OK: {html_path} ({size_kb}KB, {canvas_count} canvases)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
