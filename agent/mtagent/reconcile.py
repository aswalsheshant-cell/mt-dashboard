"""Reconciliation mode: dashboard (data.js) vs source CSVs vs itself.

Pure stdlib — no duckdb needed — so it runs anywhere. Three layers:

  internal   dashboard self-consistency: sum(monthly_fyNN) must equal the
             block's own FY total (tight tolerance).
  article    article-level sources vs the dashboard values that were built
             FROM those same sources (detail_meta.fyx_primary FY27+,
             offtake FY27+ patch) — tight tolerance.
  preagg     article-level source sums vs the PRE-AGGREGATED workbook
             numbers (primary.nsv_fy25/fy26). These come from DIFFERENT
             source files, so differences are EXPECTED and reported as
             INFO with the %, per the coverage-split rule in CLAUDE.md.

All values in INR Lakh, matching the sources and data.js.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import Config
from .fyrules import fy_tag_from_label, norm_month_label


def load_dash(root: Path) -> dict:
    """Parse dashboard/data.js (``window.DASH = {...};``) into a dict."""
    text = (root / "dashboard" / "data.js").read_text(encoding="utf-8")
    return json.loads(text[text.index("{"): text.rindex("}") + 1])


def _csv_fy_sums(files: list[Path], month_col: str, value_col: str
                 ) -> tuple[dict, dict, list]:
    """Sum value_col by FY tag and by (FY, month-label). Header lookup is by
    FIRST occurrence (the primary CSV has a duplicated 'Cust-SAP Code'
    column, so DictReader would clobber — use positional access)."""
    by_fy: dict[str, float] = {}
    by_month: dict[tuple, float] = {}
    problems: list[str] = []
    for f in files:
        with open(f, newline="", encoding="utf-8-sig", errors="replace") as fh:
            reader = csv.reader(fh)
            header = next(reader, [])
            try:
                mi = header.index(month_col)
                vi = header.index(value_col)
            except ValueError:
                problems.append(f"{f.name}: missing column "
                                f"'{month_col}' or '{value_col}'")
                continue
            bad = 0
            for row in reader:
                if len(row) <= max(mi, vi):
                    continue
                lab = norm_month_label(row[mi])   # 'Apr-26' from any style,
                fy = fy_tag_from_label(row[mi])   # incl. Excel date serials
                if not fy:
                    bad += 1
                    continue
                try:
                    v = float(row[vi]) if row[vi].strip() else 0.0
                except ValueError:
                    bad += 1
                    continue
                by_fy[fy] = by_fy.get(fy, 0.0) + v
                key = (fy, lab)
                by_month[key] = by_month.get(key, 0.0) + v
            if bad:
                problems.append(f"{f.name}: {bad} row(s) with unparsable "
                                "month/value skipped")
    return by_fy, by_month, problems


def _row(layer, name, dash, src, tol_pct):
    diff = None if (dash is None or src is None) else src - dash
    pct = (abs(diff) / abs(dash) * 100) if diff is not None and dash else None
    if dash is None or src is None:
        status = "N/A"
    elif layer == "preagg":
        status = "INFO"          # different source files — diff expected
    else:
        status = "OK" if pct is not None and pct <= tol_pct else "DIFF"
    return {"layer": layer, "check": name,
            "dashboard_lakh": None if dash is None else round(dash, 2),
            "source_lakh": None if src is None else round(src, 2),
            "diff_lakh": None if diff is None else round(diff, 2),
            "diff_pct": None if pct is None else round(pct, 3),
            "status": status}


def run_reconciliation(cfg: Config, tol_pct: float = 0.5) -> dict:
    """Returns {'rows': [...], 'problems': [...]}."""
    root = cfg.root()
    dash = load_dash(root)
    rows: list[dict] = []
    problems: list[str] = []

    # ---- source-side sums (article-level committed CSVs) ----
    prim_files = sorted((root / "PowerBI/RawDataFolders/Primary_Article_Monthly")
                        .glob("primary_article_*.csv"))
    prim_fy, _prim_month, p1 = _csv_fy_sums(prim_files, "Month", "sale in lac")
    off_files = sorted((root / "PowerBI/RawDataFolders/Offtake_Monthly")
                       .glob("offtake_store_article_*.csv"))
    off_fy, off_month, p2 = _csv_fy_sums(off_files, "Month", "NSV")
    problems += p1 + p2

    # ---- layer 1: dashboard internal consistency ----
    prim = dash.get("primary", {})
    for fy_low in ("fy25", "fy26"):
        total = prim.get(f"nsv_{fy_low}")
        monthly = prim.get(f"monthly_{fy_low}")
        if total is not None and monthly:
            rows.append(_row("internal", f"primary monthly_{fy_low} sums to nsv_{fy_low}",
                             total, sum(monthly), tol_pct))
    off = dash.get("offtake", {})
    for key in sorted(k for k in off if k.startswith("total_fy")):
        fy_low = key[len("total_"):]
        monthly = off.get(f"monthly_{fy_low}")
        if monthly:
            rows.append(_row("internal", f"offtake monthly_{fy_low} sums to {key}",
                             off[key], sum(monthly), tol_pct))

    # ---- layer 2: article-level dashboard blocks vs their own sources ----
    fyx = (dash.get("detail_meta") or {}).get("fyx_primary") or {}
    for tag, block in sorted(fyx.items()):
        src = prim_fy.get(tag)
        rows.append(_row("article", f"primary {tag} (detail_meta.fyx_primary) "
                         "vs Primary_Article_Monthly CSVs",
                         block.get("nsv"), src, tol_pct))
    for key in sorted(k for k in off if k.startswith("total_fy")):
        tag = "FY" + key[len("total_fy"):]
        if tag in off_fy:   # only FYs whose offtake CSVs are committed
            rows.append(_row("article", f"offtake {tag} total vs "
                             "Offtake_Monthly CSVs", off[key], off_fy[tag], tol_pct))
            months = off.get(f"months_{key[len('total_'):]}") or []
            monthly = off.get(f"monthly_{key[len('total_'):]}") or []
            for lab, val in zip(months, monthly):   # source keys already canonical
                rows.append(_row("article", f"offtake {tag} month {lab}",
                                 val, off_month.get((tag, norm_month_label(lab))),
                                 tol_pct))

    # ---- layer 3: pre-agg workbook numbers vs article-level sources ----
    for tag in sorted(prim_fy):
        low = tag.lower()
        if prim.get(f"nsv_{low}") is not None:
            rows.append(_row("preagg", f"primary {tag}: preagg workbook vs "
                             "article-level CSV sum (diff expected)",
                             prim[f"nsv_{low}"], prim_fy[tag], tol_pct))

    return {"rows": rows, "problems": problems}


def format_report(result: dict) -> str:
    out = []
    w = max((len(r["check"]) for r in result["rows"]), default=20)
    out.append(f"{'check'.ljust(w)} | {'dashboard':>12} | {'source':>12} | "
               f"{'diff':>10} | {'diff%':>7} | status")
    out.append("-" * (w + 60))
    for r in result["rows"]:
        def n(v, width):
            return ("" if v is None else f"{v:,}").rjust(width)
        out.append(f"{r['check'].ljust(w)} | {n(r['dashboard_lakh'],12)} | "
                   f"{n(r['source_lakh'],12)} | {n(r['diff_lakh'],10)} | "
                   f"{n(r['diff_pct'],7)} | {r['status']}")
    counts = {}
    for r in result["rows"]:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    out.append("")
    out.append("summary: " + ", ".join(f"{v} {k}" for k, v in sorted(counts.items())))
    for p in result["problems"]:
        out.append(f"[note] {p}")
    if counts.get("DIFF"):
        out.append("DIFF rows need root-cause: check missing month files, "
                   "duplicate loads, or a stale data.js (re-run the matching "
                   "scripts/build_dashboard_data.py partial refresh).")
    if counts.get("INFO"):
        out.append("INFO rows compare pre-aggregated workbooks vs article-level "
                   "files — a gap here is the known coverage split, not an error "
                   "(see CLAUDE.md).")
    return "\n".join(out)
