#!/usr/bin/env python3
"""
Nielsen Market Share Dashboard Builder
Injects a monthly JSON data payload into the self-contained HTML template.

Usage:
    python scripts/build_nielsen_dashboard.py --data data/nielsen_jul26.json
    python scripts/build_nielsen_dashboard.py --data data/nielsen_aug26.json --out dist/Nielsen_MS_Aug26.html
"""

import argparse
import csv
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

    # Shampoo block: its own sales / category must reproduce the share it reports
    sh = data.get("shampoo")
    if sh:
        me = next((b for b in sh.get("brands", []) if b.get("n") == "Mamaearth"), None)
        sales, cat = sh.get("mamaearth_sales_cr"), sh.get("category_cr")
        if me and sales and cat and abs(sales / cat * 100 - me.get("ms", 0)) > 0.2:
            warnings.append(f"Shampoo share {me.get('ms')}% does not match sales/category ({sales / cat * 100:.2f}%)")
        if sum(b.get("ms", 0) for b in sh.get("brands", [])) > 100:
            warnings.append("Shampoo brand shares sum above 100%")

    # Brand market share sum (rough check — should be < 100%)
    if "brands" in data:
        total_ms = sum(b.get("ms", 0) for b in data["brands"])
        if total_ms > 100:
            warnings.append(f"Brand MS sums to {total_ms:.1f}% — check for duplicates")

    return warnings


REQUIRED_STATUS = "GOVERNED"
REQUIRED_REFERENCES = ("source_reference", "validation_reference")


def governance_errors(data: dict) -> list[str]:
    """Blocking problems: a payload with any of these is never built or published.

    Market share is published on a public page, so it must come from a real,
    registered Nielsen extract. A sample/demo file, or one whose source and
    validation are not recorded, fails closed (2026-10-01: data/nielsen_aug26.json
    was a SAMPLE and was published as "August 2026").
    """
    errors = []
    comment = str(data.get("_comment", ""))
    if "sample" in comment.lower():
        errors.append(f"payload is marked SAMPLE (_comment: {comment!r})")
    if data.get("data_status") != REQUIRED_STATUS:
        errors.append(f"data_status is {data.get('data_status')!r}, must be {REQUIRED_STATUS!r}")
    for key in REQUIRED_REFERENCES:
        if not str(data.get(key, "")).strip():
            errors.append(f"{key} is missing (name the Nielsen report / the validation evidence)")
    return errors


def load_payload(data_path: Path) -> dict:
    if not data_path.exists():
        raise FileNotFoundError(f"Data file not found: {data_path}")
    with open(data_path, "r", encoding="utf-8") as f:
        return json.load(f)


# -- Real Nielsen files in data/nielsen/ ---------------------------------------
# Read straight from the files so the page and the files cannot drift apart.
# A blank cell stays None (unknown); it is never turned into 0.

FW_BRANDS_CSV = "FW_Jul26_Competitive_Landscape.csv"
FW_TREND_CSV = "Mamaearth_FW_Monthly_Trend.csv"
SH_PACK_CSV = "Shampoo_Jul26_PackSize_Analysis.csv"
ACRONYMS = {"VLCC"}


def _num(value):
    value = (value or "").strip()
    return float(value) if value else None


def brand_label(name: str) -> str:
    """HIMALAYA -> Himalaya, POND'S -> Pond's, CLEAN & CLEAR -> Clean & Clear."""
    if name.strip().upper() in ACRONYMS:
        return name.strip().upper()
    return name.strip().title().replace("'S", "'s")


def shampoo_pack_buckets(rows: list[dict]) -> list[dict]:
    """Group base pack sizes into <100 / 100-180 / 180-200 / >200 ml by Jul 26 value."""
    def bucket(size: float) -> str:
        return "<100ml" if size < 100 else "100-180ml" if size < 180 else "180-200ml" if size <= 200 else ">200ml"
    now, year_ago = {}, {}
    for row in rows:
        size = _num(row.get("BASEPACKSIZE"))
        if size is None:
            continue
        key = bucket(size)
        now[key] = now.get(key, 0.0) + (_num(row.get("Jul 26")) or 0.0)
        year_ago[key] = year_ago.get(key, 0.0) + (_num(row.get("Jul 25")) or 0.0)
    total = sum(now.values())
    out = []
    for key in ("<100ml", "100-180ml", "180-200ml", ">200ml"):
        if key in now:
            yoy = round((now[key] / year_ago[key] - 1) * 100, 1) if year_ago.get(key) else None
            out.append({"sz": key, "val": round(now[key] / total * 100, 1), "yoy": yoy})
    return out


def load_extras(repo_root: Path) -> dict:
    """Facewash brand shares (all brands), category NSV by month, Shampoo pack buckets."""
    folder = Path(repo_root) / "data" / "nielsen"
    extras: dict = {}

    brands_path = folder / FW_BRANDS_CSV
    if brands_path.is_file():
        with brands_path.open(encoding="utf-8-sig", newline="") as handle:
            extras["fw_all"] = [
                {"n": brand_label(r["brand"]), "ms_py": _num(r.get("ms_Jul25")), "ms": _num(r.get("ms_Jul26")),
                 "wd": _num(r.get("wd_jul26")), "stores": _num(r.get("stores_jul26")),
                 "l3m": _num(r.get("l3m")), "lmat": _num(r.get("lmat"))}
                for r in csv.DictReader(handle) if (r.get("brand") or "").strip()]

    trend_path = folder / FW_TREND_CSV
    if trend_path.is_file():
        with trend_path.open(encoding="utf-8-sig", newline="") as handle:
            extras["fw_cat_nsv"] = {r["month"].strip(): _num(r.get("category_nsv_cr"))
                                    for r in csv.DictReader(handle) if (r.get("month") or "").strip()}

    pack_path = folder / SH_PACK_CSV
    if pack_path.is_file():
        with pack_path.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        extras["sh_pack_file"] = {"period": "Jul 2026", "source": SH_PACK_CSV,
                                  "buckets": shampoo_pack_buckets(rows),
                                  "top": [{"sz": r["BASEPACKSIZE"], "share": round(_num(r.get("ms_pct_jul26")) or 0, 1)}
                                          for r in sorted(rows, key=lambda r: -(_num(r.get("Jul 26")) or 0))[:5]]}
    return extras


def to_js_payload(data: dict, extras: dict | None = None) -> str:
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
    if extras is not None:
        months = data["months"]
        cat = extras.get("fw_cat_nsv") or {}
        normalized["FW_ALL"] = extras.get("fw_all", [])
        normalized["FW_CAT_NSV"] = [cat.get(m) for m in months]
        normalized["SHAMPOO"] = data.get("shampoo")
        normalized["SH_PACK_FILE"] = extras.get("sh_pack_file")
        normalized["GOV"] = {
            "data_status": data.get("data_status", ""),
            "source_reference": data.get("source_reference", ""),
            "validation_reference": data.get("validation_reference", ""),
        }
    return json.dumps(normalized, separators=(",", ":"), ensure_ascii=False)


# ── Build ─────────────────────────────────────────────────────────────────────

def build(template_path: Path, data_path: Path, output_path: Path) -> None:
    print(f"[*] Data:     {data_path}")
    print(f"[*] Template: {template_path}")

    data = load_payload(data_path)

    blocking = governance_errors(data)
    if blocking:
        for e in blocking:
            print(f"[x] {e}", file=sys.stderr)
        raise SystemExit(f"Not built: {data_path.name} is not a governed Nielsen payload.")

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

    js_payload = to_js_payload(data, load_extras(REPO_ROOT))
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
    parser.add_argument(
        "--check-only", action="store_true",
        help="Only run the governance check (exit 2 if the payload may not be published)"
    )
    args = parser.parse_args()

    if args.check_only:
        errors = governance_errors(load_payload(args.data))
        for e in errors:
            print(f"[x] {e}", file=sys.stderr)
        print(f"[{'x' if errors else '✓'}] governance check: {args.data}")
        sys.exit(2 if errors else 0)

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
