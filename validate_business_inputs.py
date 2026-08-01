#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Pre-refresh business input validator.

Runs 22 deterministic checks across events_calendar.csv, launch_plan.csv,
targets.csv, and fact_margin.csv before executing refresh_forecast.py.

Usage:
    python validate_business_inputs.py                    # full / final mode
    python validate_business_inputs.py --mode final       # strict (same as full)
    python validate_business_inputs.py --mode full        # strict (legacy alias)
    python validate_business_inputs.py --mode quick       # schema + approval gates only
    python validate_business_inputs.py --mode tentative   # relaxed gate for planning mode

Exit code:
    0  — safe to proceed (all PASS/WARNING, or tentative OK)
    1  — BLOCKED or FAIL present (final mode), or TECHNICALLY BLOCKED (tentative)
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

# Checks downgraded from BLOCKED/FAIL → WARNING in tentative mode, with explanation
TENTATIVE_DOWNGRADE = {
    "V-01": ("WARNING",
             "No approved targets — tentative forecast uses history-based baseline"),
    "V-07": ("WARNING",
             "Events PLACEHOLDER_TBC — tentative forecast uses 0% uplift (conservative)"),
    "V-11": ("WARNING",
             "Unapproved NPIs excluded from tentative — no NPI uplift applied"),
    "V-14": ("WARNING",
             "ESTIMATED margins allowed in tentative mode — labeled as assumptions"),
    "V-15": ("WARNING",
             "Finance approval not required for tentative planning mode"),
}

# Checks that remain BLOCKED even in tentative mode (structural integrity)
TENTATIVE_STRUCTURAL_BLOCKED = {"V-02", "V-05", "V-17", "V-20", "V-22"}

RESULTS = []   # list of (check_id, severity, file, description, status, detail)


def _effective_severity(check_id: str, nominal_sev: str, mode: str) -> str:
    """Return the severity actually used, honouring tentative-mode downgrade."""
    if mode == "tentative" and check_id in TENTATIVE_DOWNGRADE:
        return TENTATIVE_DOWNGRADE[check_id][0]
    return nominal_sev


def _result(check_id, severity, fname, description, passed, detail="", mode="full"):
    eff_sev = _effective_severity(check_id, severity, mode)
    status = "PASS" if passed else eff_sev
    # Append tentative note when severity was downgraded
    if (not passed and mode == "tentative" and check_id in TENTATIVE_DOWNGRADE
            and eff_sev != severity):
        tentative_note = TENTATIVE_DOWNGRADE[check_id][1]
        detail = f"{detail}  [TENTATIVE: {tentative_note}]" if detail else f"[TENTATIVE: {tentative_note}]"
    RESULTS.append({
        "check_id": check_id,
        "severity": severity,
        "effective_severity": eff_sev,
        "file": fname,
        "description": description,
        "status": status,
        "detail": detail,
    })
    icon = "✓" if passed else ("✗" if eff_sev in ("BLOCKED", "FAIL") else "⚠")
    print(f"  [{check_id}] {icon} {eff_sev:<8} {fname:<28} {description}")
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
        _result("V-01", "BLOCKED", fname, "File readable", False, err, mode)
        return

    _result("V-01", "BLOCKED", fname, "At least one data row present", len(df) > 0,
            f"0 rows — upload Aug–Oct 2026 targets" if len(df) == 0 else f"{len(df)} rows",
            mode)

    if len(df) == 0:
        return

    required = ["month", "chain_name", "brand", "ean", "target_qty"]
    blanks = {c: int(df[c].isna().sum() + (df[c] == "").sum())
              for c in required if c in df.columns}
    total_blanks = sum(blanks.values())
    _result("V-02", "BLOCKED", fname, "No blanks in required columns",
            total_blanks == 0, f"{blanks}" if total_blanks > 0 else "", mode)

    if "month" in df.columns:
        bad_month = df["month"].dropna()
        bad_month = bad_month[~bad_month.str.match(r"^\d{4}-\d{2}$")]
        _result("V-03", "FAIL", fname, "month format YYYY-MM",
                len(bad_month) == 0,
                f"{len(bad_month)} bad values: {bad_month.tolist()[:5]}", mode)

    for col in ["target_qty", "target_nsv", "target_primary_qty"]:
        if col in df.columns:
            neg = pd.to_numeric(df[col], errors="coerce").lt(0).sum()
            _result("V-04", "FAIL", fname, f"No negative {col}",
                    neg == 0, f"{neg} negative values", mode)

    key = [c for c in ["month", "chain_name", "brand", "ean"] if c in df.columns]
    dups = df.duplicated(subset=key).sum()
    _result("V-05", "BLOCKED", fname, "No duplicate month × chain × brand × ean",
            dups == 0, f"{dups} duplicates", mode)

    if "quality_status" in df.columns:
        missing_qs = (df["quality_status"] == "MISSING").sum()
        _result("V-06", "FAIL", fname, "No MISSING quality_status",
                missing_qs == 0, f"{missing_qs} MISSING rows", mode)


def check_events(mode):
    fname = "events_calendar.csv"
    df, err = _load(fname)
    if err:
        _result("V-07", "BLOCKED", fname, "File readable", False, err, mode)
        return

    if "status" in df.columns:
        placeholder = (df["status"] == "PLACEHOLDER_TBC").sum()
    else:
        placeholder = len(df)
    _result("V-07", "BLOCKED", fname, "No PLACEHOLDER_TBC rows",
            placeholder == 0,
            f"{placeholder} of {len(df)} events still PLACEHOLDER_TBC — "
            "get uplift % approved before forecast run",
            mode)

    if mode in ("quick",):
        return

    if "forecast_month" in df.columns:
        dups = df.duplicated(subset=["forecast_month", "chain_filter", "brand_filter",
                                     "event_name"]).sum()
        _result("V-08", "FAIL", fname, "No overlapping events same chain × brand × month",
                dups == 0, f"{dups} duplicate event rows", mode)

        bad = df["forecast_month"].dropna()
        bad = bad[~bad.str.match(r"^\d{4}-\d{2}$")]
        _result("V-10", "FAIL", fname, "forecast_month format YYYY-MM",
                len(bad) == 0, f"{len(bad)} bad values: {bad.tolist()[:5]}", mode)

    if "uplift_pct" in df.columns:
        uplift = pd.to_numeric(df["uplift_pct"], errors="coerce")
        out_of_range = ((uplift < 0) | (uplift > 100)).sum()
        _result("V-09", "FAIL", fname, "uplift_pct between 0 and 100",
                out_of_range == 0, f"{out_of_range} values outside [0,100]", mode)


def check_launch_plan(mode):
    fname = "launch_plan.csv"
    df, err = _load(fname)
    if err:
        _result("V-11", "BLOCKED", fname, "File readable", False, err, mode)
        return

    if len(df) == 0:
        _result("V-11", "BLOCKED", fname, "All NPI rows have approval_status = APPROVED",
                True, "No NPI rows — no uplift applied (acceptable if no NPIs planned)", mode)
        _result("V-12", "FAIL", fname, "launch_month <= forecast window", True, "N/A — empty file", mode)
        _result("V-13", "FAIL", fname, "No negative uplift percentages", True, "N/A — empty file", mode)
        return

    if "status" in df.columns or "approval_status" in df.columns:
        scol = "approval_status" if "approval_status" in df.columns else "status"
        not_approved = (df[scol] != "APPROVED").sum()
        _result("V-11", "BLOCKED", fname, "All rows have approval_status = APPROVED",
                not_approved == 0,
                f"{not_approved} rows not APPROVED — will not affect forecast but verify intent",
                mode)

    if mode in ("quick",):
        return

    if "launch_month" in df.columns:
        bad = df["launch_month"].dropna()
        bad = bad[~bad.str.match(r"^\d{4}-\d{2}$")]
        _result("V-12", "FAIL", fname, "launch_month format YYYY-MM",
                len(bad) == 0, f"{len(bad)} bad values", mode)

    for col in [c for c in df.columns if "uplift_pct" in c]:
        neg = pd.to_numeric(df[col], errors="coerce").lt(0).sum()
        _result("V-13", "FAIL", fname, f"No negative {col}",
                neg == 0, f"{neg} negative values", mode)


def check_margin(mode):
    fname = "fact_margin.csv"
    df, err = _load(fname)
    if err:
        _result("V-14", "BLOCKED", fname, "File readable", False, err, mode)
        return

    estimated = (df.get("quality_status", pd.Series()) == "ESTIMATED").sum() if "quality_status" in df.columns else 0
    _result("V-14", "BLOCKED", fname, "No ESTIMATED rows (replace with real Finance data)",
            estimated == 0,
            f"{estimated} ESTIMATED rows — placeholder MRP/margins; CM2 reporting BLOCKED",
            mode)

    if "approval_status" in df.columns:
        not_approved = (df["approval_status"] != "FINANCE_APPROVED").sum()
        _result("V-15", "FAIL", fname, "All rows Finance-approved",
                not_approved == 0,
                f"{not_approved} rows missing FINANCE_APPROVED status",
                mode)
    else:
        _result("V-15", "FAIL", fname, "approval_status column present",
                False, "Column 'approval_status' not found — add before Finance sign-off",
                mode)

    if mode in ("quick",):
        return

    chain_col = "chain_name" if "chain_name" in df.columns else None

    for col in ["mrp", "margin_pct", "cm2_pct"]:
        if col not in df.columns:
            continue
        neg_mask = pd.to_numeric(df[col], errors="coerce").lt(0)
        neg_count = int(neg_mask.sum())

        # In tentative mode, isolate VMM negative margin_pct rows
        if mode == "tentative" and col == "margin_pct" and neg_count > 0 and chain_col:
            vmm_neg = int((neg_mask & (df[chain_col] == "VMM")).sum())
            non_vmm_neg = int((neg_mask & (df[chain_col] != "VMM")).sum())
            if non_vmm_neg == 0:
                _result("V-16", "WARNING", fname,
                        f"Negative {col} isolated to VMM chain (excluded from tentative)",
                        True,
                        f"{vmm_neg} VMM rows excluded from tentative — non-VMM rows clean",
                        mode)
            else:
                _result("V-16", "FAIL", fname,
                        f"No negative {col} (non-VMM rows)",
                        False,
                        f"{non_vmm_neg} non-VMM negative {col} rows — must resolve",
                        mode)
        else:
            _result("V-16", "FAIL", fname, f"No negative {col}",
                    neg_count == 0, f"{neg_count} negative values", mode)

    if "mrp" in df.columns:
        zero_mrp = (pd.to_numeric(df["mrp"], errors="coerce") <= 0).sum()
        _result("V-18", "FAIL", fname, "mrp > 0 for all rows",
                zero_mrp == 0, f"{zero_mrp} zero/negative MRP rows", mode)

    key = [c for c in ["month", "chain_name", "ean"] if c in df.columns]
    if len(key) == 3:
        dups = df.duplicated(subset=key).sum()
        _result("V-17", "BLOCKED", fname, "No duplicate month × chain × ean",
                dups == 0, f"{dups} duplicates", mode)


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
                    len(unmapped) == 0, f"{len(unmapped)} unmapped EANs: {list(unmapped)[:5]}", mode)
        else:
            _result("V-19", "FAIL", fname, "All target EANs in margin master",
                    True, "N/A — targets.csv empty", mode)

    for fn, d in [("targets.csv", targets), ("launch_plan.csv", launch)]:
        if d is not None and len(d) > 0 and "brand" in d.columns:
            bad_brands = d["brand"].isin(EXCLUDED_BRANDS)
            _result("V-20", "BLOCKED", fn,
                    f"No excluded brands ({', '.join(sorted(EXCLUDED_BRANDS))})",
                    bad_brands.sum() == 0,
                    f"{bad_brands.sum()} rows with excluded brand: {d.loc[bad_brands,'brand'].unique().tolist()}",
                    mode)


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
                f"{dups} duplicates" if dups > 0 else f"{len(df)} rows, 0 duplicates ✓",
                mode)


def _print_verdict(blocked, failed, warnings, passed, mode):
    """Print mode-appropriate verdict and return exit code."""
    print("\n" + "=" * 70)
    print(f"  RESULTS:  PASS={len(passed)}  WARNING={len(warnings)}  FAIL={len(failed)}  BLOCKED={len(blocked)}")
    print("=" * 70)

    if mode == "tentative":
        # In tentative mode, only structural BLOCKED issues are hard stops
        structural_blocked = [r for r in blocked
                              if r["check_id"] in TENTATIVE_STRUCTURAL_BLOCKED]
        if structural_blocked:
            print("\n  TECHNICALLY BLOCKED — structural data issues must be resolved even in tentative mode:")
            for r in structural_blocked:
                print(f"  [{r['check_id']}] {r['status']} — {r['file']}: {r['description']}")
                if r["detail"]:
                    print(f"        → {r['detail']}")
            print("\n  NOT READY FOR FINAL FORECAST (resolve structural issues above first)")
            print("=" * 70)
            return 1

        if warnings or blocked or failed:
            print("\n  Assumptions applied in TENTATIVE mode (review before finalizing):")
            for r in (blocked + failed + warnings):
                if r["status"] in ("WARNING", "PASS"):
                    print(f"  [{r['check_id']}] {r['status']} — {r['file']}: {r['description']}")
                    if r["detail"]:
                        print(f"        → {r['detail']}")

        # Check if VMM was isolated (excluded from tentative)
        vmm_excluded = any(
            "VMM" in r.get("detail", "") and "excluded" in r.get("detail", "").lower()
            for r in RESULTS
        )

        print()
        if vmm_excluded:
            print("  ✓  SAFE TO RUN WITH EXCLUSIONS — run validate + forecast:")
            print("       python validate_business_inputs.py --mode tentative")
            print("       python -m forecast_engine.cli --mode tentative ...")
        elif warnings or blocked or failed:
            print("  ✓  SAFE TO RUN TENTATIVE FORECAST WITH WARNINGS")
            print("       python validate_business_inputs.py --mode tentative")
            print("       python -m forecast_engine.cli --mode tentative ...")
        else:
            print("  ✓  SAFE TO RUN TENTATIVE FORECAST")
            print("       python -m forecast_engine.cli --mode tentative ...")

        print()
        print("  ⚠  NOT READY FOR FINAL FORECAST — resolve all BLOCKED/FAIL items:")
        remaining = [r for r in RESULTS if r["effective_severity"] in ("BLOCKED", "FAIL")
                     and r["status"] != "PASS"]
        for r in remaining[:5]:
            print(f"     [{r['check_id']}] {r['effective_severity']} — {r['file']}: {r['description']}")
        print("=" * 70)
        return 0

    else:
        # Final / full / quick mode — strict gate
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
        return 1 if (blocked or failed) else 0


def main():
    parser = argparse.ArgumentParser(description="Business input validator")
    parser.add_argument("--mode", choices=["full", "quick", "tentative", "final"],
                        default="full",
                        help=("full/final = strict gate (default); "
                              "quick = schema + approval only; "
                              "tentative = relaxed for planning (allows missing inputs)"))
    parser.add_argument("--out", default=None, help="Write JSON results to file")
    args = parser.parse_args()

    # Treat 'final' as 'full' (strict mode, different label only)
    run_mode = "full" if args.mode == "final" else args.mode
    display_mode = args.mode.upper()

    print("=" * 70)
    print(f"  BUSINESS INPUT VALIDATOR — Pre-Refresh Gate")
    print(f"  Mode: {display_mode}  |  {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if run_mode == "tentative":
        print("  TENTATIVE MODE: Structural checks enforced; approval gates relaxed.")
        print("  Outputs will be labeled IS_TENTATIVE=True. Not for final reporting.")
    print("=" * 70)

    print("\n[targets.csv]")
    check_targets(run_mode)

    print("\n[events_calendar.csv]")
    check_events(run_mode)

    print("\n[launch_plan.csv]")
    check_launch_plan(run_mode)

    print("\n[fact_margin.csv]")
    check_margin(run_mode)

    if run_mode in ("full", "tentative"):
        print("\n[cross-file checks]")
        check_cross_file(run_mode)

        print("\n[existing assembled data]")
        check_existing_data(run_mode)

    blocked  = [r for r in RESULTS if r["status"] == "BLOCKED"]
    failed   = [r for r in RESULTS if r["status"] == "FAIL"]
    warnings = [r for r in RESULTS if r["status"] == "WARNING"]
    passed   = [r for r in RESULTS if r["status"] == "PASS"]

    exit_code = _print_verdict(blocked, failed, warnings, passed, run_mode)

    if args.out:
        with open(args.out, "w") as f:
            json.dump({
                "results": RESULTS,
                "summary": {
                    "mode": args.mode,
                    "blocked": len(blocked),
                    "fail": len(failed),
                    "warning": len(warnings),
                    "pass": len(passed),
                    "safe_to_run": exit_code == 0,
                },
            }, f, indent=2)
        print(f"  Results written to {args.out}")

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
