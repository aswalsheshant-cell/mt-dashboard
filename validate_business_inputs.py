#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Pre-refresh business input validator.

Runs 22 deterministic checks across events_calendar.csv, launch_plan.csv,
targets.csv, and fact_margin.csv before executing refresh_forecast.py.

Usage:
    python validate_business_inputs.py               # full mode (default)
    python validate_business_inputs.py --mode full   # same
    python validate_business_inputs.py --mode quick  # schema + approval gates only

Exit code:
    0  — all checks PASS or WARNING only (safe to run forecast)
    1  — one or more BLOCKED or FAIL checks (do not run forecast)
"""
import os
import sys
import re
import argparse
import datetime as dt
import json
import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
PHASE_A = os.path.join(PROJECT_ROOT, "Phase_A_Input")

EXCLUDED_BRANDS = {"Pure Origin", "Lumineve", "Staze"}

RESULTS = []   # list of (check_id, severity, file, description, status, detail)

def _result(check_id, severity, fname, description, passed, detail=""):
    status = "PASS" if passed else severity
    RESULTS.append({
        "check_id": check_id,
        "severity": severity,
        "file": fname,
        "description": description,
        "status": status,
        "detail": detail,
    })
    icon = "✓" if passed else ("✗" if severity in ("BLOCKED", "FAIL") else "⚠")
    print(f"  [{check_id}] {icon} {severity:<8} {fname:<28} {description}")
    if not passed and detail:
        print(f"             → {detail}")

def _load(fname):
    path = os.path.join(PHASE_A, fname)
    if not os.path.exists(path):
        return None, f"{path} not found"
    try:
        return pd.read_csv(path, dtype=str), None
    except Exception as e:
        return None, str(e)


def check_targets(mode):
    fname = "targets.csv"
    df, err = _load(fname)
    if err:
        _result("V-01", "BLOCKED", fname, "File readable", False, err)
        return

    _result("V-01", "BLOCKED", fname, "At least one data row present", len(df) > 0,
            f"0 rows — upload Aug–Oct 2026 targets" if len(df) == 0 else f"{len(df)} rows")

    if len(df) == 0:
        return

    required = ["month", "chain_name", "brand", "ean", "target_qty"]
    blanks = {c: int(df[c].isna().sum() + (df[c] == "").sum())
              for c in required if c in df.columns}
    total_blanks = sum(blanks.values())
    _result("V-02", "BLOCKED", fname, "No blanks in required columns",
            total_blanks == 0, f"{blanks}" if total_blanks > 0 else "")

    if "month" in df.columns:
        bad_month = df["month"].dropna()
        bad_month = bad_month[~bad_month.str.match(r"^\d{4}-\d{2}$")]
        _result("V-03", "FAIL", fname, "month format YYYY-MM",
                len(bad_month) == 0, f"{len(bad_month)} bad values: {bad_month.tolist()[:5]}")

    for col in ["target_qty", "target_nsv", "target_primary_qty"]:
        if col in df.columns:
            neg = pd.to_numeric(df[col], errors="coerce").lt(0).sum()
            _result("V-04", "FAIL", fname, f"No negative {col}",
                    neg == 0, f"{neg} negative values")

    key = [c for c in ["month", "chain_name", "brand", "ean"] if c in df.columns]
    dups = df.duplicated(subset=key).sum()
    _result("V-05", "BLOCKED", fname, "No duplicate month × chain × brand × ean",
            dups == 0, f"{dups} duplicates")

    if "quality_status" in df.columns:
        missing_qs = (df["quality_status"] == "MISSING").sum()
        _result("V-06", "FAIL", fname, "No MISSING quality_status",
                missing_qs == 0, f"{missing_qs} MISSING rows")


def check_events(mode):
    fname = "events_calendar.csv"
    df, err = _load(fname)
    if err:
        _result("V-07", "BLOCKED", fname, "File readable", False, err)
        return

    if "status" in df.columns:
        placeholder = (df["status"] == "PLACEHOLDER_TBC").sum()
    else:
        placeholder = len(df)
    _result("V-07", "BLOCKED", fname, "No PLACEHOLDER_TBC rows",
            placeholder == 0,
            f"{placeholder} of {len(df)} events still PLACEHOLDER_TBC — "
            "get uplift % approved before forecast run")

    if mode == "quick":
        return

    if "forecast_month" in df.columns:
        dups = df.duplicated(subset=["forecast_month", "chain_filter", "brand_filter",
                                     "event_name"]).sum()
        _result("V-08", "FAIL", fname, "No overlapping events same chain × brand × month",
                dups == 0, f"{dups} duplicate event rows")

        bad = df["forecast_month"].dropna()
        bad = bad[~bad.str.match(r"^\d{4}-\d{2}$")]
        _result("V-10", "FAIL", fname, "forecast_month format YYYY-MM",
                len(bad) == 0, f"{len(bad)} bad values: {bad.tolist()[:5]}")

    if "uplift_pct" in df.columns:
        uplift = pd.to_numeric(df["uplift_pct"], errors="coerce")
        out_of_range = ((uplift < 0) | (uplift > 100)).sum()
        _result("V-09", "FAIL", fname, "uplift_pct between 0 and 100",
                out_of_range == 0, f"{out_of_range} values outside [0,100]")


def check_launch_plan(mode):
    fname = "launch_plan.csv"
    df, err = _load(fname)
    if err:
        _result("V-11", "BLOCKED", fname, "File readable", False, err)
        return

    if len(df) == 0:
        _result("V-11", "BLOCKED", fname, "All NPI rows have approval_status = APPROVED",
                True, "No NPI rows — no uplift applied (acceptable if no NPIs planned)")
        _result("V-12", "FAIL", fname, "launch_month <= forecast window", True, "N/A — empty file")
        _result("V-13", "FAIL", fname, "No negative uplift percentages", True, "N/A — empty file")
        return

    if "status" in df.columns or "approval_status" in df.columns:
        scol = "approval_status" if "approval_status" in df.columns else "status"
        not_approved = (df[scol] != "APPROVED").sum()
        _result("V-11", "BLOCKED", fname, "All rows have approval_status = APPROVED",
                not_approved == 0,
                f"{not_approved} rows not APPROVED — will not affect forecast but verify intent")

    if mode == "quick":
        return

    if "launch_month" in df.columns:
        bad = df["launch_month"].dropna()
        bad = bad[~bad.str.match(r"^\d{4}-\d{2}$")]
        _result("V-12", "FAIL", fname, "launch_month format YYYY-MM",
                len(bad) == 0, f"{len(bad)} bad values")

    for col in [c for c in df.columns if "uplift_pct" in c]:
        neg = pd.to_numeric(df[col], errors="coerce").lt(0).sum()
        _result("V-13", "FAIL", fname, f"No negative {col}",
                neg == 0, f"{neg} negative values")


def check_margin(mode):
    fname = "fact_margin.csv"
    df, err = _load(fname)
    if err:
        _result("V-14", "BLOCKED", fname, "File readable", False, err)
        return

    estimated = (df.get("quality_status", pd.Series()) == "ESTIMATED").sum() if "quality_status" in df.columns else 0
    _result("V-14", "BLOCKED", fname, "No ESTIMATED rows (replace with real Finance data)",
            estimated == 0,
            f"{estimated} ESTIMATED rows — placeholder MRP/margins; CM2 reporting BLOCKED")

    if "approval_status" in df.columns:
        not_approved = (df["approval_status"] != "FINANCE_APPROVED").sum()
        _result("V-15", "FAIL", fname, "All rows Finance-approved",
                not_approved == 0,
                f"{not_approved} rows missing FINANCE_APPROVED status")
    else:
        _result("V-15", "FAIL", fname, "approval_status column present",
                False, "Column 'approval_status' not found — add before Finance sign-off")

    if mode == "quick":
        return

    for col in ["mrp", "margin_pct", "cm2_pct"]:
        if col in df.columns:
            neg = pd.to_numeric(df[col], errors="coerce").lt(0).sum()
            _result("V-16", "FAIL", fname, f"No negative {col}",
                    neg == 0, f"{neg} negative values")

    if "mrp" in df.columns:
        zero_mrp = (pd.to_numeric(df["mrp"], errors="coerce") <= 0).sum()
        _result("V-18", "FAIL", fname, "mrp > 0 for all rows",
                zero_mrp == 0, f"{zero_mrp} zero/negative MRP rows")

    key = [c for c in ["month", "chain_name", "ean"] if c in df.columns]
    if len(key) == 3:
        dups = df.duplicated(subset=key).sum()
        _result("V-17", "BLOCKED", fname, "No duplicate month × chain × ean",
                dups == 0, f"{dups} duplicates")


def check_cross_file(mode):
    fname = "cross-file"
    margin, _ = _load("fact_margin.csv")
    targets, _ = _load("targets.csv")
    events, _ = _load("events_calendar.csv")
    launch, _ = _load("launch_plan.csv")

    if margin is not None and "ean" in margin.columns:
        margin_eans = set(margin["ean"].dropna())

        if targets is not None and len(targets) > 0 and "ean" in targets.columns:
            unmapped = set(targets["ean"].dropna()) - margin_eans
            _result("V-19", "FAIL", fname, "All target EANs in margin master",
                    len(unmapped) == 0, f"{len(unmapped)} unmapped EANs: {list(unmapped)[:5]}")
        else:
            _result("V-19", "FAIL", fname, "All target EANs in margin master",
                    True, "N/A — targets.csv empty")

    # Excluded brand check — across all files
    for fn, d in [("targets.csv", targets), ("launch_plan.csv", launch)]:
        if d is not None and len(d) > 0 and "brand" in d.columns:
            bad_brands = d["brand"].isin(EXCLUDED_BRANDS)
            _result("V-20", "BLOCKED", fn,
                    f"No excluded brands ({', '.join(sorted(EXCLUDED_BRANDS))})",
                    bad_brands.sum() == 0,
                    f"{bad_brands.sum()} rows with excluded brand: {d.loc[bad_brands,'brand'].unique().tolist()}")


def check_existing_data(mode):
    for fname, key in [
        ("primary_history.csv",  ["month", "chain_name", "ean"]),
        ("offtake_history.csv",  ["month", "chain_name", "ean"]),
    ]:
        df, err = _load(fname)
        if err:
            continue
        dups = df.duplicated(subset=[c for c in key if c in df.columns]).sum()
        _result("V-22" if "primary" in fname else "V-21",
                "BLOCKED" if "primary" in fname else "WARNING",
                fname,
                "No duplicate month × chain × ean",
                dups == 0,
                f"{dups} duplicates" if dups > 0 else f"{len(df)} rows, 0 duplicates ✓")


def main():
    parser = argparse.ArgumentParser(description="Business input validator")
    parser.add_argument("--mode", choices=["full", "quick"], default="full")
    parser.add_argument("--out", default=None, help="Write JSON results to file")
    args = parser.parse_args()

    print("=" * 70)
    print("  BUSINESS INPUT VALIDATOR — Pre-Refresh Gate")
    print(f"  Mode: {args.mode}  |  {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    print("\n[targets.csv]")
    check_targets(args.mode)

    print("\n[events_calendar.csv]")
    check_events(args.mode)

    print("\n[launch_plan.csv]")
    check_launch_plan(args.mode)

    print("\n[fact_margin.csv]")
    check_margin(args.mode)

    if args.mode == "full":
        print("\n[cross-file checks]")
        check_cross_file(args.mode)

        print("\n[existing assembled data]")
        check_existing_data(args.mode)

    print("\n" + "=" * 70)
    blocked  = [r for r in RESULTS if r["status"] == "BLOCKED"]
    failed   = [r for r in RESULTS if r["status"] == "FAIL"]
    warnings = [r for r in RESULTS if r["status"] == "WARNING"]
    passed   = [r for r in RESULTS if r["status"] == "PASS"]

    print(f"  RESULTS:  PASS={len(passed)}  WARNING={len(warnings)}  FAIL={len(failed)}  BLOCKED={len(blocked)}")
    print("=" * 70)

    if blocked or failed:
        print("\n  FORECAST RUN BLOCKED — resolve the following before refresh_forecast.py:")
        for r in blocked + failed:
            print(f"  [{r['check_id']}] {r['status']} — {r['file']}: {r['description']}")
            if r["detail"]:
                print(f"        → {r['detail']}")
    else:
        if warnings:
            print("\n  Warnings (non-blocking — document before running forecast):")
            for r in warnings:
                print(f"  [{r['check_id']}] WARNING — {r['file']}: {r['description']}")
                if r["detail"]:
                    print(f"        → {r['detail']}")
        print("\n  ✓  All BLOCKED and FAIL checks passed — safe to run refresh_forecast.py")

    print("=" * 70)

    if args.out:
        with open(args.out, "w") as f:
            json.dump({"results": RESULTS, "summary": {
                "blocked": len(blocked), "fail": len(failed),
                "warning": len(warnings), "pass": len(passed),
                "safe_to_run": len(blocked) == 0 and len(failed) == 0,
            }}, f, indent=2)
        print(f"  Results written to {args.out}")

    sys.exit(0 if not (blocked or failed) else 1)


if __name__ == "__main__":
    main()
