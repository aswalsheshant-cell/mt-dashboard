"""Source coverage QC for the Power BI full report (read-only).

For every table in PowerBI/model.bim it finds the files the Power Query reads
(pRootFolder & "\\RawDataFolders\\..." or "\\SeedData\\..."), checks they exist,
counts rows, works out which months each file covers (FY from month + year,
Apr-Mar) and compares that with the required periods.

Missing data is reported as MISSING / INCOMPLETE. It is never turned into zero.
No source rows are copied into the output, only counts and period labels.

Usage:
  python scripts/powerbi_full_sources.py                       # default periods
  python scripts/powerbi_full_sources.py --periods 2026-04:2026-08
  python scripts/powerbi_full_sources.py --check               # exit 1 if any required source is not READY
"""

import argparse
import csv
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PBI = ROOT / "PowerBI"
MODEL = PBI / "model.bim"
OUT = PBI / "full_report_sources.json"

# Default window: FY26 + FY27 year to date. Override with --periods.
DEFAULT_PERIODS = ["2025-04:2026-08"]

MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}

# Grain / unit as stated in the Power Query headers and docs/evidence audits.
# Tables not listed here are masters or config (grain = one row per key).
FACT_NOTES = {
    "Fact Primary Sales": ("week/month x chain x brand", "rupees", "PQ 10; weekly drop folder"),
    "Fact Offtake Sales": ("month x store x article", "lakh in source, x100000 in PQ", "PQ 11; docs/evidence/dashboard_unit_source_audit_2026-10-03.md"),
    "Fact Primary ShipTo": ("month x ship-to x chain x brand", "lakh in source, converted in PQ", "PQ 15; duplicate-snapshot risk (composite + narrower files)"),
    "Fact Primary Article": ("month x ship-to x article", "rupees", "PQ 16; docs/evidence/dashboard_unit_source_audit_2026-10-03.md"),
    "Fact Secondary Sales": ("month x distributor/chain/brand", "lakh", "PQ 44"),
    "Fact Claim Master": ("quarter x chain/brand/distributor", "lakh", "PQ 45"),
    "Fact Nielsen": ("month x brand x zone", "rupees", "PQ 13"),
    "Fact TDP": ("month x brand x chain", "count", "PQ 14"),
    "Fact P&L": ("month x chain", "rupees", "PQ 12"),
}

# Pages (PageLayouts.md numbering) that depend on each fact table.
TABLE_PAGES = {
    "Fact Primary Sales": ["1", "2", "3", "4", "6", "7", "8"],
    "Fact Offtake Sales": ["1", "2", "3", "6", "7", "8"],
    "Fact Primary ShipTo": ["2B", "3"],
    "Fact Primary Article": ["2B", "7"],
    "Fact Secondary Sales": ["2", "3"],
    "Fact Claim Master": ["4"],
    "Fact Nielsen": ["9"],
    "Fact Nielsen Pack": ["9"],
    "Fact Nielsen Pack Brand": ["9"],
    "Fact Nielsen Brand Cut": ["9"],
    "Fact TDP": ["10"],
    "Fact P&L": ["4"],
    "Fact Account Category": ["9"],
    "Fact Account Category Geo": ["9"],
    "Fact Account Assortment": ["9"],
    "Fact Store Type": ["8"],
    "Fact Pack Size": ["8"],
    "Fact Sales Cuts": ["8"],
    "Fact Inhouse Distribution": ["10"],
    "Dim Promo Calendar": ["6"],
}

PATH_RE = re.compile(r'pRootFolder\s*&\s*"\\((?:RawDataFolders|SeedData)\\[^"]*)"')
# A literal path that skips pRootFolder will not resolve on another machine.
HARDCODED_RE = re.compile(r'"(?:PowerBI[\\/])?((?:RawDataFolders|SeedData)[\\/][^"]*)"')
DERIVED_RE = re.compile(r'#"(Fact [^"]+)"')
SKIP_NAMES = ("_readme", "_template")
PERIOD_COLS = ("Month", "MonthStart", "Source_Month", "Year-Month", "Period")


def fy_tag(year, month):
    """THE ONE FY RULE: Apr-Dec of Y -> FY(Y+1); Jan-Mar of Y -> FY(Y)."""
    return "FY%02d" % ((year + 1 if month >= 4 else year) % 100)


def expand_range(spec):
    a, b = spec.split(":")
    (y1, m1), (y2, m2) = [tuple(int(x) for x in p.split("-")) for p in (a, b)]
    out = []
    y, m = y1, m1
    while (y, m) <= (y2, m2):
        out.append("%04d-%02d" % (y, m))
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def parse_period(text):
    """Return 'YYYY-MM' from labels like Aug'26, Aug-2026, 2026-08, 2026-08-01, or None."""
    t = str(text).strip()
    m = re.match(r"^(\d{4})-(\d{2})", t)
    if m:
        return "%s-%s" % (m.group(1), m.group(2))
    m = re.match(r"^([A-Za-z]{3})[A-Za-z]*[\s'\-_]*(\d{2}|\d{4})$", t)
    if m and m.group(1).lower() in MONTHS:
        y = int(m.group(2))
        y = y + 2000 if y < 100 else y
        return "%04d-%02d" % (y, MONTHS[m.group(1).lower()])
    return None


def periods_from_name(name):
    m = re.search(r"_([A-Za-z]{3})_(\d{2})(?!\d)", name)
    if m and m.group(1).lower() in MONTHS:
        return ["%04d-%02d" % (2000 + int(m.group(2)), MONTHS[m.group(1).lower()])]
    m = re.search(r"_([A-Za-z]{3})_([A-Za-z]{3})_FY(\d{2})", name)  # e.g. Jul_Aug_FY27
    if m and m.group(1).lower() in MONTHS and m.group(2).lower() in MONTHS:
        fy = 2000 + int(m.group(3))
        a, b = MONTHS[m.group(1).lower()], MONTHS[m.group(2).lower()]
        return ["%04d-%02d" % (fy - 1 if mm >= 4 else fy, mm) for mm in range(a, b + 1)]
    return []


def count_rows_and_header(path):
    rows = -1
    header = []
    with open(path, "rb") as fh:
        first = fh.readline().decode("utf-8-sig", "replace").rstrip("\r\n")
        header = next(csv.reader([first])) if first else []
        rows = 0
        for block in iter(lambda: fh.read(1 << 20), b""):
            rows += block.count(b"\n")
    return max(rows, 0), header


def file_periods(path, header):
    """Months covered by a file: from the name, else from its date column (small files only)."""
    found = set(periods_from_name(path.name))
    col = next((c for c in PERIOD_COLS if c in header), None)
    if col and path.stat().st_size <= 40 << 20:
        with open(path, newline="", encoding="utf-8-sig", errors="replace") as fh:
            for rec in csv.DictReader(fh):
                p = parse_period(rec.get(col, ""))
                if p:
                    found.add(p)
    return sorted(found)


def inspect_file(path):
    rows, header = count_rows_and_header(path)
    periods = file_periods(path, header)
    return {
        "file": path.relative_to(ROOT).as_posix(),
        "size_mb": round(path.stat().st_size / 1048576, 2),
        "rows": rows,
        "columns": len(header),
        "periods": periods,
        "fy_tags": sorted({fy_tag(int(p[:4]), int(p[5:])) for p in periods}),
    }


def resolve(ref):
    """Turn a PQ path (RawDataFolders\\X or SeedData\\X\\Y.csv) into the data files behind it."""
    p = PBI / ref.replace("\\", "/")
    if p.is_dir():
        files = sorted(f for f in p.rglob("*.csv") if not f.name.lower().startswith(SKIP_NAMES))
        templates = sorted(f for f in p.iterdir() if f.is_file() and f.name.lower().startswith("_template"))
        return {"kind": "folder", "exists": True, "files": files, "template_only": not files and bool(templates)}
    if p.is_file():
        return {"kind": "file", "exists": True, "files": [p], "template_only": False}
    return {"kind": "missing", "exists": False, "files": [], "template_only": False}


def table_refs(table):
    """Return (pRootFolder-based refs, hard-coded refs, upstream tables this query is built from)."""
    refs, hard, derived = set(), set(), set()
    for part in table.get("partitions", []):
        expr = part.get("source", {}).get("expression", "")
        text = "\n".join(expr) if isinstance(expr, list) else expr
        code = "\n".join(l for l in text.splitlines() if not l.lstrip().startswith("//"))
        refs.update(PATH_RE.findall(code))
        for h in HARDCODED_RE.findall(code):
            hard.add(h.replace("/", "\\"))
        derived.update(DERIVED_RE.findall(code))
    hard -= {r for r in refs}
    derived.discard(table["name"])
    return sorted(refs), sorted(hard), sorted(derived)


def assess(model, required):
    req = set(required)
    results = []
    for table in model["model"]["tables"]:
        name = table["name"]
        if name == "_Measures":
            continue
        refs, hard, derived = table_refs(table)
        warnings = []
        if hard:
            warnings.append("Hard-coded path(s) without pRootFolder: %s. Will not resolve outside the repo root." % ", ".join(hard))
            refs = sorted(set(refs) | set(hard))
        entry = {
            "table": name,
            "is_fact": name.startswith("Fact "),
            "pq_refs": refs,
            "grain": FACT_NOTES.get(name, ("master/config", "n/a", ""))[0],
            "unit": FACT_NOTES.get(name, ("", "n/a", ""))[1],
            "notes": FACT_NOTES.get(name, ("", "", ""))[2],
            "dependent_pages": TABLE_PAGES.get(name, []),
            "derived_from": derived,
            "warnings": warnings,
            "files": [],
        }
        if not refs:
            entry["status"] = "DERIVED" if derived else "NO_FILE_SOURCE"  # derived = built from other model tables
            results.append(entry)
            continue
        covered, any_missing, template_only = set(), False, False
        for ref in refs:
            r = resolve(ref)
            any_missing |= not r["exists"]
            template_only |= r["template_only"]
            for f in r["files"]:
                info = inspect_file(f)
                entry["files"].append(info)
                covered.update(info["periods"])
        has_rows = any(f["rows"] > 0 for f in entry["files"])
        timed = entry["is_fact"] and any(f["periods"] for f in entry["files"])
        entry["periods_covered"] = sorted(covered)
        if any_missing and not has_rows:
            entry["status"] = "MISSING"
        elif not has_rows:
            entry["status"] = "TEMPLATE_ONLY" if template_only else "EMPTY"
        elif timed and req:
            missing = sorted(req - covered)
            entry["periods_missing_vs_required"] = missing
            entry["status"] = "READY" if not missing else "INCOMPLETE_PERIODS"
        else:
            entry["status"] = "READY"
        results.append(entry)
    return results


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--periods", action="append", help="YYYY-MM:YYYY-MM range, repeatable")
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--check", action="store_true", help="exit 1 if a fact table is not READY")
    args = ap.parse_args()

    ranges = args.periods or DEFAULT_PERIODS
    required = sorted({p for r in ranges for p in expand_range(r)})
    model = json.loads(MODEL.read_text(encoding="utf-8"))
    tables = assess(model, required)

    summary = {}
    for t in tables:
        summary[t["status"]] = summary.get(t["status"], 0) + 1
    doc = {
        "generated": date.today().isoformat(),
        "basis": "Source-side file inspection only. Not a Desktop refresh result.",
        "required_periods": required,
        "required_period_ranges": ranges,
        "required_fy_tags": sorted({fy_tag(int(p[:4]), int(p[5:])) for p in required}),
        "status_summary": summary,
        "tables": tables,
    }
    Path(args.out).write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")

    print("Required periods: %s .. %s (%d months)" % (required[0], required[-1], len(required)))
    print("Status summary:", summary)
    bad = [t for t in tables if t["is_fact"] and t["status"] != "READY"]
    for t in bad:
        miss = t.get("periods_missing_vs_required", [])
        print("  %-28s %-18s missing=%s" % (t["table"], t["status"], (miss[0] + ".." + miss[-1]) if miss else "-"))
    print("Wrote", Path(args.out).relative_to(ROOT) if Path(args.out).is_relative_to(ROOT) else args.out)
    if args.check and bad:
        sys.exit(1)


if __name__ == "__main__":
    main()
