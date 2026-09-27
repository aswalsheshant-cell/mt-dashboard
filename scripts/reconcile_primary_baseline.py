#!/usr/bin/env python3
"""Reconcile the Primary NSV figures quoted in this repo's docs against the
monthly source files in PowerBI/RawDataFolders/Primary_Article_Monthly/.

Each documented figure is a total over a stated MONTH WINDOW, not "the grand
total" -- the watch folder grows every month, so a grand total is only ever
true on the day it was written. This script recomputes the same NSV that
build_dashboard_data.py's load_primary_v2() uses (Inv. Net value(LOC) / 1e5,
no filter or dedup at this stage), per month file, and checks every figure in
DOCUMENTED_FIGURES against its own window. FY comes from THE ONE FY RULE
(bdd.fy_tag_from_ym on the file's month; the source's own FY column, which
mixes "FY'26-27" and "FY27" spellings, is normalised with bdd._fylabel and
must agree with the file's month).

Exit code 0 only when every documented figure matches its window (±0.01 L)
and every file's FY labels agree with its month -- fails closed otherwise.

Usage: python3 scripts/reconcile_primary_baseline.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import build_dashboard_data as bdd  # noqa: E402  (FY helpers: THE ONE FY RULE)

PRIMARY_DIR = ROOT / "PowerBI" / "RawDataFolders" / "Primary_Article_Monthly"
TOLERANCE_L = 0.01

# (label, where it is quoted, first month, last month, value in INR Lakh)
DOCUMENTED_FIGURES = [
    ("FY26 Primary NSV", "CLAUDE.md three-measures table; config/baselines.json",
     (2025, 4), (2026, 3), 32900.36),
    ("Primary NSV Apr'25-Jun'26 (15 months)", "PowerBI/docs/Desktop_Assembly_Checklist.md Phase J",
     (2025, 4), (2026, 6), 46560.34),
    ("Primary NSV Apr'25-Jul'26 (16 months, frozen backfill baseline)", "PR #119 / issue #120",
     (2025, 4), (2026, 7), 51481.65),
]

_MON = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}


def month_totals(primary_dir: Path = PRIMARY_DIR) -> list[dict]:
    """One row per primary_article_<Mon>_<YY>.csv: month, NSV (Lakh), FY checks."""
    out = []
    for f in sorted(primary_dir.glob("primary_article_*.csv")):
        m = re.fullmatch(r"primary_article_([A-Za-z]{3})_(\d{2})\.csv", f.name)
        if not m or m.group(1).title() not in _MON:
            raise SystemExit(f"Unrecognised file name (expected primary_article_Mon_YY.csv): {f.name}")
        ym = (2000 + int(m.group(2)), _MON[m.group(1).title()])
        df = pd.read_csv(f, usecols=["Inv. Net value(LOC)", "FY"], low_memory=False)
        nsv = pd.to_numeric(df["Inv. Net value(LOC)"], errors="coerce").fillna(0.0).sum() / 1e5
        fy = bdd.fy_tag_from_ym(*ym)
        labels = sorted({t for t in df["FY"].dropna().map(bdd._fylabel)} - {None})
        out.append({"file": f.name, "ym": ym, "fy": fy, "nsv": nsv,
                    "source_fy_labels": labels, "labels_agree": labels == [fy]})
    if not out:
        raise SystemExit(f"No primary_article_*.csv files found under {primary_dir}")
    return sorted(out, key=lambda r: r["ym"])


def window_total(rows: list[dict], start: tuple, end: tuple) -> tuple[float, list[tuple]]:
    """Sum NSV over [start, end]; also return any month in that window with no file."""
    have = {r["ym"]: r["nsv"] for r in rows}
    missing, total, (y, mo) = [], 0.0, start
    while (y, mo) <= end:
        if (y, mo) in have:
            total += have[(y, mo)]
        else:
            missing.append((y, mo))
        y, mo = (y + 1, 1) if mo == 12 else (y, mo + 1)
    return total, missing


def reconcile(rows: list[dict]) -> list[dict]:
    results = []
    for label, where, start, end, value in DOCUMENTED_FIGURES:
        got, missing = window_total(rows, start, end)
        ok = not missing and abs(got - value) <= TOLERANCE_L
        results.append({"label": label, "where": where, "window": (start, end), "documented": value,
                        "recomputed": round(got, 2), "missing_months": missing, "ok": ok})
    return results


def main() -> int:
    rows = month_totals()
    fmt = lambda ym: f"{list(_MON)[ym[1] - 1]}'{ym[0] % 100:02d}"
    print(f"{len(rows)} month file(s), {fmt(rows[0]['ym'])} to {fmt(rows[-1]['ym'])}\n")
    by_fy: dict[str, float] = {}
    for r in rows:
        by_fy[r["fy"]] = by_fy.get(r["fy"], 0.0) + r["nsv"]
        flag = "" if r["labels_agree"] else f"   <-- source FY column says {r['source_fy_labels']}"
        print(f"  {fmt(r['ym'])}  {r['fy']}  Rs{r['nsv']:>10,.2f} L{flag}")
    print("\nBy FY (THE ONE FY RULE): " + ", ".join(f"{k} Rs{v:,.2f} L" for k, v in sorted(by_fy.items())))
    print(f"All months on file: Rs{sum(r['nsv'] for r in rows):,.2f} L "
          f"(changes every month -- not a baseline)\n")

    bad = [r for r in rows if not r["labels_agree"]]
    results = reconcile(rows)
    for x in results:
        s, e = x["window"]
        state = "MATCH" if x["ok"] else ("MISSING MONTHS" if x["missing_months"] else "MISMATCH")
        print(f"{state:<14} {x['label']}: documented Rs{x['documented']:,.2f} L, "
              f"{fmt(s)}-{fmt(e)} recomputed Rs{x['recomputed']:,.2f} L  [{x['where']}]")
        if x["missing_months"]:
            print(f"               missing: {', '.join(fmt(m) for m in x['missing_months'])}")
    if bad:
        print(f"\n{len(bad)} file(s) whose FY column disagrees with the file's month.")
    return 0 if (not bad and all(x["ok"] for x in results)) else 1


if __name__ == "__main__":
    sys.exit(main())
