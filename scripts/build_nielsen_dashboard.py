#!/usr/bin/env python3
"""
Nielsen Market Share Dashboard Builder
Injects a monthly JSON data payload into the self-contained HTML template.

Usage:
    python scripts/build_nielsen_dashboard.py --data data/nielsen_jul26.json
    python scripts/build_nielsen_dashboard.py --data data/nielsen_aug26.json --out dist/Nielsen_MS_Aug26.html
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

PLACEHOLDER = "/* __NIELSEN_DATA_PAYLOAD__ */"
REPO_ROOT = Path(__file__).parent.parent
DEFAULT_TEMPLATE = REPO_ROOT / "templates" / "dashboard_template.html"


# ── Validation ────────────────────────────────────────────────────────────────

def validate_payload(data: dict) -> list[str]:
    """Returns a list of warning strings; empty = clean."""
    warnings = []

    # Required top-level keys
    for key in ("months", "ms", "nsv", "wd", "stores", "brands", "fw_packs", "sh_packs"):
        if key not in data:
            warnings.append(f"Missing required key: '{key}'")

    # Series length consistency
    series_keys = ("months", "ms", "nsv", "wd", "stores")
    lengths = {k: len(data[k]) for k in series_keys if k in data}
    if len(set(lengths.values())) > 1:
        warnings.append(f"Time-series length mismatch: {lengths}")

    # Pack mix sums (~100%)
    for pack_key in ("fw_packs", "sh_packs"):
        if pack_key in data:
            total = sum(p.get("val", 0) for p in data[pack_key])
            if not (98.0 <= total <= 102.0):
                warnings.append(f"{pack_key} share sum = {total:.1f}% (expected ~100%)")

    # Brand market share sum (rough check — should be < 100%)
    if "brands" in data:
        total_ms = sum(b.get("ms", 0) for b in data["brands"])
        if total_ms > 100:
            warnings.append(f"Brand MS sums to {total_ms:.1f}% — check for duplicates")

    return warnings


def load_payload(data_path: Path) -> dict:
    if not data_path.exists():
        raise FileNotFoundError(f"Data file not found: {data_path}")
    with open(data_path, "r", encoding="utf-8") as f:
        return json.load(f)


def to_js_payload(data: dict) -> str:
    """Serialize to compact JSON safe for inline JS injection."""
    # The JS array format uses single-char keys (n, nsv, ms, pp, yoy, stores, wd, pdo)
    # that the dashboard template expects — map from long-form JSON keys if present
    def remap_brand(b: dict) -> dict:
        return {
            "n":      b.get("n") or b.get("name", ""),
            "nsv":    b.get("nsv", 0),
            "ms":     b.get("ms", 0),
            "pp":     b.get("pp", 0),
            "yoy":    b.get("yoy", 0),
            "stores": b.get("stores", 0),
            "wd":     b.get("wd", 0),
            "pdo":    b.get("pdo", 0),
        }

    def remap_pack(p: dict) -> dict:
        return {
            "sz":  p.get("sz") or p.get("size", ""),
            "val": p.get("val", 0),
            "yoy": p.get("yoy", 0),
            "clr": p.get("clr") or p.get("color", "#2563EB"),
        }

    def remap_action(a: dict) -> dict:
        return {
            "title":  a.get("title", ""),
            "owner":  a.get("owner", ""),
            "budget": a.get("budget", "—"),
            "due":    a.get("due", ""),
            "desc":   a.get("desc", ""),
        }

    def remap_gate(g: dict) -> dict:
        return {
            "date":   g.get("date", ""),
            "q":      g.get("q", ""),
            "impact": g.get("impact", ""),
        }

    normalized = {
        "MONTHS":      data["months"],
        "MS_":         data["ms"],
        "NSV_":        data["nsv"],
        "WD_":         data["wd"],
        "STORES_":     data["stores"],
        "BRANDS":      [remap_brand(b) for b in data["brands"]],
        "FW_PACKS":    [remap_pack(p) for p in data["fw_packs"]],
        "SH_PACKS":    [remap_pack(p) for p in data["sh_packs"]],
        "AUG_ACTIONS": [remap_action(a) for a in data.get("aug_actions", [])],
        "SEP_ACTIONS": [remap_action(a) for a in data.get("sep_actions", [])],
        "GATES":       [remap_gate(g) for g in data.get("gates", [])],
        "_meta": {
            "generated_at":    datetime.now().isoformat(),
            "reporting_period": data.get("reporting_period", ""),
        },
    }
    return json.dumps(normalized, separators=(",", ":"), ensure_ascii=False)


# ── Build ─────────────────────────────────────────────────────────────────────

def build(template_path: Path, data_path: Path, output_path: Path) -> None:
    print(f"[*] Data:     {data_path}")
    print(f"[*] Template: {template_path}")

    data = load_payload(data_path)

    warnings = validate_payload(data)
    for w in warnings:
        print(f"[!] {w}")
    if any("Missing required key" in w for w in warnings):
        raise ValueError("Payload missing required keys — aborting.")

    with open(template_path, "r", encoding="utf-8") as f:
        template = f.read()

    if PLACEHOLDER not in template:
        raise ValueError(
            f"Injection placeholder `{PLACEHOLDER}` not found in template.\n"
            f"Re-generate the template from Nielsen_MS_Dashboard_Jul26.html."
        )

    js_payload = to_js_payload(data)
    output = template.replace(
        f"{PLACEHOLDER} {{}}",
        js_payload,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(output)

    size_kb = output_path.stat().st_size / 1024
    print(f"[✓] Built: {output_path} ({size_kb:.0f} KB)")
    if warnings:
        print(f"    {len(warnings)} warning(s) above — review before distributing")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compile monthly Nielsen Market Share Dashboard"
    )
    parser.add_argument(
        "--data", "-d", required=True, type=Path,
        help="Monthly data JSON (e.g. data/nielsen_aug26.json)"
    )
    parser.add_argument(
        "--template", "-t", default=DEFAULT_TEMPLATE, type=Path,
        help="HTML template with injection placeholder"
    )
    parser.add_argument(
        "--out", "-o", type=Path,
        help="Output path (default: dist/Nielsen_MS_Dashboard_<period>.html)"
    )
    args = parser.parse_args()

    if not args.out:
        period = args.data.stem.replace("nielsen_", "").upper()
        args.out = REPO_ROOT / "dist" / f"Nielsen_MS_Dashboard_{period}.html"

    try:
        build(args.template, args.data, args.out)
    except Exception as e:
        print(f"[!] Build failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
