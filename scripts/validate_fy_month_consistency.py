#!/usr/bin/env python3
"""FY <-> month consistency check (THE ONE FY RULE, permanent guard).

Rule: Apr-Dec of year Y -> FY(Y+1); Jan-Mar of year Y -> FY(Y). An FY is named by
its ENDING year (FY27 = Apr'26-Mar'27; the same period is also written 26-27).

Checks (stdlib only, no pandas):
  1. Every CSV under PowerBI/ that has an FY column AND a month column: the
     FY on each row must be the FY of that row's month. Reports the label
     FORMATS seen too (FY'25-26 / FY26 / FY_24-25 / 25-26 ...) because mixed
     text formats are what break a slicer even when the year is right --
     Power Query now derives [FY Year] from the month, so formats in raw files
     are informational.
  2. data.js: every months_fyNN / month_labels list holds only months of that FY.
  3. Power Query: every fact query that carries [FY Year] derives it with
     fnFYLabel (not copied from the source).

Exit 0 = clean, 1 = a month sits in the wrong FY or a fact query copies FY.
Usage: python scripts/validate_fy_month_consistency.py [--root .]
"""
import argparse
import csv
import json
import re
import sys
from pathlib import Path

MON = {m: i for i, m in enumerate("jan feb mar apr may jun jul aug sep oct nov dec".split(), 1)}
FY_COLS = {"fy", "fy year", "fy_derived", "fiscal year"}
MONTH_COLS = {"monthstart", "month", "source_month", "monthstartcalc"}
FACT_QUERIES = ["10_Fact_PrimarySales", "11_Fact_OfftakeSales", "13_Fact_Nielsen",
                "14_Fact_TDP", "15_Fact_PrimaryShipTo", "16_Fact_PrimaryArticle"]


def fy_end_2digit(year, month):
    """FY of a calendar month, as the 2-digit ENDING year (Apr-26 -> 27, Mar-26 -> 26)."""
    return (year + 1 if month >= 4 else year) % 100


def parse_ym(v):
    v = str(v).strip()
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", v)
    if m:
        return int(m[1]), int(m[2])
    m = re.match(r"([A-Za-z]{3})[a-z]*[-' ]*(\d{2,4})$", v)
    if m and m[1].lower() in MON:
        y = int(m[2])
        return (y + 2000 if y < 100 else y), MON[m[1].lower()]
    return None


def parse_fy_end(v):
    """Ending year (2 digits) from FY'25-26 / FY26 / FY_24-25 / 25-26 / FY2627."""
    v = str(v).strip()
    m = re.search(r"(\d{2,4})\D+(\d{2,4})$", v)
    if m:
        return int(m[2]) % 100
    m = re.search(r"(\d{2})$", v)
    return int(m[1]) if m else None


def check_csvs(root):
    bad, formats, checked = [], {}, 0
    for f in sorted(Path(root, "PowerBI").rglob("*.csv")):
        try:
            with open(f, encoding="utf-8-sig", errors="replace", newline="") as fh:
                rd = csv.DictReader(fh)
                cols = rd.fieldnames or []
                fyc = next((c for c in cols if c.strip().lower() in FY_COLS), None)
                mc = next((c for c in cols if c.strip().lower() in MONTH_COLS), None)
                if not fyc or not mc:
                    continue
                for n, row in enumerate(rd, 2):
                    a, b = parse_ym(row[mc]), parse_fy_end(row[fyc])
                    if a is None or b is None:
                        continue
                    checked += 1
                    formats.setdefault(f.name, set()).add(re.sub(r"\d", "9", str(row[fyc]).strip()))
                    if fy_end_2digit(*a) != b:
                        bad.append(f"{f.relative_to(root)}:{n} month={row[mc]!r} FY={row[fyc]!r}")
        except OSError:
            continue
    return bad, formats, checked


def check_datajs(path):
    s = Path(path).read_text(encoding="utf-8")
    d = json.loads(s[s.index("{"): s.rindex("}") + 1])
    bad, seen = [], 0

    def walk(o, p=""):
        nonlocal seen
        if isinstance(o, dict):
            for k, v in o.items():
                tag = re.search(r"(fy)(\d\d)", k) if k.startswith("months_") else None
                if tag and isinstance(v, list):
                    for x in v:
                        ym = parse_ym(x) if isinstance(x, str) else None
                        if ym is None:
                            continue
                        seen += 1
                        if fy_end_2digit(*ym) != int(tag.group(2)):
                            bad.append(f"data.js {p}/{k}: {x} is not in FY{tag.group(2)}")
                else:
                    walk(v, f"{p}/{k}")
        elif isinstance(o, list):
            for v in o[:300]:
                walk(v, p)

    walk(d)
    return bad, seen


def check_powerquery(root):
    bad = []
    fn = Path(root, "PowerBI", "PowerQuery", "02_fnFYLabel.pq")
    if not fn.exists():
        return ["PowerBI/PowerQuery/02_fnFYLabel.pq is missing"]
    for name in FACT_QUERIES:
        p = Path(root, "PowerBI", "PowerQuery", name + ".pq")
        s = p.read_text(encoding="utf-8")
        if "fnFYLabel(" not in s or not re.search(r"\nin\s+FYDerived\s*\Z", s):
            bad.append(f"{p.relative_to(root)}: [FY Year] must be derived with fnFYLabel (final step FYDerived)")
    return bad


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parent.parent))
    a = ap.parse_args(argv)
    root = Path(a.root)
    c_bad, fmts, n = check_csvs(root)
    d_bad, d_n = check_datajs(root / "dashboard" / "data.js")
    q_bad = check_powerquery(root)
    allfmt = sorted({x for v in fmts.values() for x in v})
    print(f"CSV rows checked: {n} | FY label formats seen: {allfmt}")
    print(f"data.js month labels checked: {d_n}")
    bad = c_bad + d_bad + q_bad
    for b in bad[:40]:
        print("FAIL", b)
    print("FY CONSISTENCY: " + ("PASS" if not bad else f"FAIL ({len(bad)})"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
