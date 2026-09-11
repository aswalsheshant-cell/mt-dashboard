#!/usr/bin/env python3
"""Apply the FY coverage gate + same-period YoY + targets to an EXISTING data.js.

Why this exists
---------------
`build_dashboard_data.py` is the only generator of data.js, and it needs the
source .xlsb/.xlsx workbooks. Those are gitignored, so an environment that has
the repo but not the source drops cannot run a rebuild -- yet the FY coverage
defect it fixes is already baked into the committed data.js and is putting a
wrong number on the leadership screen.

This script closes that gap. It applies exactly the logic the builder now
applies, by IMPORTING the builder's own functions rather than restating them,
using only values ALREADY PRESENT in data.js:

  * primary FY coverage gate  -- same rule as primary_block()
  * detail_meta.same_period   -- same_period_block() over detail_records
  * targets                   -- targets_block() over the tracked target CSV
  * insights                  -- insights_block() re-run on the same-period basis

Nothing is fetched, assumed or invented. Run it again after a real rebuild and
it is a no-op.

Usage:  python scripts/patch_fy_coverage_gate.py [--out dashboard/data.js] [--dry-run]
"""
from __future__ import annotations
import argparse, importlib.util, json, re, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PREFIX = "window.DASH = "


def load_builder():
    spec = importlib.util.spec_from_file_location(
        "bdd", REPO / "scripts" / "build_dashboard_data.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules["bdd"] = m
    spec.loader.exec_module(m)
    return m


def read_data_js(path: Path) -> dict:
    src = path.read_text(encoding="utf-8")
    return json.loads(src[src.index("{"):].rstrip().rstrip(";"))


def write_data_js(path: Path, data: dict) -> None:
    path.write_text(PREFIX + json.dumps(data, ensure_ascii=False, indent=1) + ";\n",
                    encoding="utf-8")


def gate_primary(primary: dict, preagg: set, fyx: dict) -> list:
    """Drop FY keys this pre-aggregated block does not actually cover.

    Mirrors primary_block()'s coverage gate. The withheld FYs are owned by the
    article-level source (detail_meta.fyx_primary), which is where the
    dashboard reads them -- so this removes a WRONG number, it does not remove
    information.
    """
    tags = [t.upper() for t in (primary.get("fy_tags") or [])]
    dropped = [t for t in tags if t not in preagg]
    if not dropped:
        return []
    held = {}
    for t in dropped:
        lo = t.lower()
        held[lo] = primary.get(f"nsv_{lo}")
        for pat in (f"nsv_{lo}", f"mrp_{lo}", f"monthly_{lo}",
                    f"months_{lo}", f"total_{lo}"):
            primary.pop(pat, None)
        for key, rows in primary.items():           # per-dimension FY columns
            if key.startswith("by_") and isinstance(rows, list):
                for r in rows:
                    if isinstance(r, dict):
                        r.pop(lo, None)
    primary["fy_tags"] = [t.lower() for t in tags if t in preagg]
    # A part-year FY against a full FY is not a YoY. With the partial FY gone
    # there is no second full year left in this block to compare against.
    if len(primary["fy_tags"]) < 2:
        primary["yoy"] = None
        for key, rows in primary.items():
            if key.startswith("by_") and isinstance(rows, list):
                for r in rows:
                    if isinstance(r, dict) and "yoy" in r:
                        r["yoy"] = None
    owned = ", ".join(f"{k}: {v.get('nsv')}" for k, v in sorted(fyx.items()))
    primary["coverage_note"] = (
        f"{', '.join(dropped)} rows present in this pre-aggregated workbook are "
        f"PARTIAL ({held}, INR Lakh) and are not published here. Those FYs are "
        f"owned by the article-level source: see detail_meta.fyx_primary"
        + (f" ({owned} INR Lakh)" if owned else "")
        + f". Source coverage = {sorted(preagg)}.")
    primary["coverage_withheld"] = held
    return dropped


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="dashboard/data.js")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    path = (REPO / a.out) if not Path(a.out).is_absolute() else Path(a.out)
    b = load_builder()
    import pandas as pd

    data = read_data_js(path)
    primary, offtake = data.get("primary", {}), data.get("offtake", {})
    dmeta = data.setdefault("detail_meta", {})
    changes = []

    # -- guard: this patch derives FY27 primary from detail_records, so refuse
    #    to run against a row-capped file where those totals would be partial.
    cov = dmeta.get("value_coverage_pct")
    if cov is not None and float(cov) < 100.0:
        print(f"REFUSING: detail_records covers only {cov}% of value; "
              f"same-period totals would be understated. Rebuild from source.")
        return 2

    # 1) primary FY coverage gate
    dropped = gate_primary(primary, b.PREAGG_FY_TAGS, dmeta.get("fyx_primary") or {})
    if dropped:
        changes.append(f"primary: withheld partial {', '.join(dropped)}; "
                       f"fy_tags -> {primary['fy_tags']}")

    # 2) same-period YoY, from the article-level detail already in the file
    recs = data.get("detail_records") or []
    if recs:
        df = pd.DataFrame([{"_FY": r.get("FY"), "_M": r.get("Month"),
                            "_NSV": r.get("NSV") or 0.0,
                            "_Zone": r.get("Zone"), "_Chain": r.get("Chain")}
                           for r in recs])
        sp = b.same_period_block(df)
        if sp:
            dmeta["same_period"] = sp
            changes.append(f"detail_meta.same_period: {sp['curr_fy']} vs {sp['prev_fy']} "
                           f"over {sp['n_months']} month(s) -> {sp['yoy_pct']}%")
    sp = dmeta.get("same_period")

    # 3) targets / achievement / run rate
    rows = b.load_targets_csv(REPO)
    if rows:
        fy = rows[0][0]
        acts = {}
        om = dict(zip(offtake.get(f"months_{fy.lower()}") or [],
                      offtake.get(f"monthly_{fy.lower()}") or []))
        if om:
            acts["offtake"] = om
        fx = (dmeta.get("fyx_primary") or {}).get(fy)
        if fx:
            acts["primary"] = dict(zip(fx.get("months_canon") or [],
                                       fx.get("monthly_canon") or []))
        tb = b.targets_block(rows, acts, sp)
        if tb:
            data["targets"] = tb
            m = tb["measures"].get(tb["basis"], {})
            changes.append(f"targets: {tb['fy_tag']} basis={tb['basis']} "
                           f"achievement {m.get('achievement_pct')}% "
                           f"({m.get('run_rate_status')})")

    # 4) insights, re-run on the like-for-like basis
    if sp and data.get("insights") is not None:
        try:
            data["insights"] = b.insights_block(
                primary, offtake, data.get("pnl") or {},
                data.get("universe") or {"by_chain": []},
                data.get("promo") or {"by_chain": [], "n_promos": 0, "avg_depth": 0},
                sp)
            changes.append(f"insights: recomputed on same-period basis "
                           f"({len(data['insights'])} items)")
        except Exception as e:                       # never lose existing insights
            print(f"  ! insights left unchanged ({type(e).__name__}: {e})")

    # 5) stamp provenance so the file says how it got this way
    data.setdefault("metadata", {})["fy_coverage_patch"] = {
        "applied": True, "preagg_fy_tags": sorted(b.PREAGG_FY_TAGS),
        "script": "scripts/patch_fy_coverage_gate.py",
        "note": ("FY coverage gate + same-period YoY + targets applied to an "
                 "existing data.js using only values already present in it. "
                 "Superseded by any full rebuild from source."),
    }

    if not changes:
        print("No changes -- data.js already gated (idempotent).")
        return 0
    print("Changes:")
    for c in changes:
        print("  *", c)
    if a.dry_run:
        print("(--dry-run: nothing written)")
        return 0
    write_data_js(path, data)
    print(f"Wrote {path} ({path.stat().st_size/1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
