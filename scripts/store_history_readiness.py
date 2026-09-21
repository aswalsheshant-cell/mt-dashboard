"""Phase 2 Data Readiness Gate — validates a FY26 store x article offtake
extract before any Same-Store Growth calculation is allowed to use it.

Design and governance: docs/PHASE_2_DATA_READINESS_GATE.md,
docs/STORE_IDENTITY_GOVERNANCE.md, docs/PHASE_2_DATA_CONTRACT.md.

Non-destructive: never writes to any source file, never touches
dashboard/data.js. Reuses this repo's existing month-parsing and
chain-canonicalization logic (build_dashboard_data.py) rather than
re-deriving it, so a real FY26 file is interpreted identically to how the
production pipeline already interprets FY27 files of the same shape.

This module is exercised entirely against synthetic fixtures today
(scripts/test_store_history_readiness.py) -- no FY26 file exists in this
repository yet. Running it against real data is the next action once one
is supplied (docs/PHASE_2_EXECUTION_STATUS.md).
"""
import importlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
bd = importlib.import_module("build_dashboard_data")

REQUIRED_COLUMNS = ["Month", "Chain", "Store Code", "Article", "Units", "NSV"]

FY26_MONTHS_EXPECTED = 12


def _coerce_numeric(series):
    """Numeric coercion that reports what it did instead of silently
    converting bad values to NaN and moving on -- callers must inspect
    the returned invalid_mask before treating the coerced series as safe."""
    coerced = pd.to_numeric(series, errors="coerce")
    was_non_null = series.notna()
    invalid_mask = was_non_null & coerced.isna()
    return coerced, invalid_mask


def _check_required_columns(df):
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    return {
        "check": "required_columns",
        "status": "FAIL" if missing else "PASS",
        "missing_columns": missing,
    }


def _check_month_coverage(df):
    months = sorted({m for m in df["_month_canon"].dropna().unique()})
    return {
        "check": "month_coverage",
        "status": "PASS" if len(months) >= FY26_MONTHS_EXPECTED else "WARN",
        "months_present": months,
        "months_present_count": len(months),
        "months_expected": FY26_MONTHS_EXPECTED,
    }


def _check_duplicate_grain(df):
    grain_cols = ["Month", "Chain", "Store Code", "Article"]
    dup_mask = df.duplicated(subset=grain_cols, keep=False)
    n_dup_rows = int(dup_mask.sum())
    n_dup_groups = int(df[dup_mask].drop_duplicates(subset=grain_cols).shape[0]) if n_dup_rows else 0
    return {
        "check": "duplicate_grain",
        "status": "PASS" if n_dup_rows == 0 else "WARN",
        "duplicate_row_count": n_dup_rows,
        "duplicate_group_count": n_dup_groups,
    }


def _check_store_identity_conflicts(df):
    """The same (Chain, Store Code) must resolve to one Store Name / State /
    City within a single month -- if not, that's an identity conflict, not
    a growth signal, and must be flagged rather than silently averaged in."""
    conflicts = []
    for col in ("Store Name", "State", "City"):
        if col not in df.columns:
            continue
        grp = df.groupby(["Month", "Chain", "Store Code"])[col].nunique(dropna=True)
        n_conflicts = int((grp > 1).sum())
        if n_conflicts:
            conflicts.append({"field": col, "conflicting_groups": n_conflicts})
    return {
        "check": "store_identity_conflicts",
        "status": "PASS" if not conflicts else "WARN",
        "conflicts": conflicts,
    }


def _check_missing_identifiers(df):
    counts = {}
    for col in ("Store Code", "Article", "Chain"):
        if col in df.columns:
            counts[col] = int(df[col].isna().sum() + (df[col].astype(str).str.strip() == "").sum())
    return {
        "check": "missing_identifiers",
        "status": "PASS" if all(v == 0 for v in counts.values()) else "WARN",
        "missing_counts": counts,
    }


def _check_article_mapping_quality(df):
    if "Article" not in df.columns:
        return {"check": "article_mapping_quality", "status": "FAIL", "reason": "no Article column"}
    total = len(df)
    blank = int((df["Article"].isna() | (df["Article"].astype(str).str.strip() == "")).sum())
    pct_populated = round((total - blank) / total * 100, 2) if total else 0.0
    return {
        "check": "article_mapping_quality",
        "status": "PASS" if pct_populated >= 99.0 else "WARN",
        "pct_populated": pct_populated,
        "blank_count": blank,
        "total_rows": total,
    }


def _check_financial_values(df):
    nsv, nsv_invalid = _coerce_numeric(df["NSV"])
    units, units_invalid = _coerce_numeric(df["Units"])
    negative_nsv = int((nsv < 0).sum())
    negative_units = int((units < 0).sum())
    return {
        "check": "financial_values",
        "status": "PASS" if (nsv_invalid.sum() == 0 and units_invalid.sum() == 0) else "WARN",
        "non_numeric_nsv_count": int(nsv_invalid.sum()),
        "non_numeric_units_count": int(units_invalid.sum()),
        "negative_nsv_count": negative_nsv,
        "negative_units_count": negative_units,
        "note": "negative values are not itself a failure -- returns/credit notes are real (see PR #167's TestNegativeValues precedent) -- reported for visibility, not blocked.",
    }


def _check_nan_infinity(df):
    nsv, _ = _coerce_numeric(df["NSV"])
    units, _ = _coerce_numeric(df["Units"])
    n_inf = int(np.isinf(nsv.to_numpy(dtype="float64", na_value=0.0)).sum()
                + np.isinf(units.to_numpy(dtype="float64", na_value=0.0)).sum())
    return {
        "check": "nan_infinity",
        "status": "PASS" if n_inf == 0 else "FAIL",
        "infinity_count": n_inf,
    }


def _check_missing_as_zero(df):
    """This check is about the VALIDATOR'S OWN counting, not the source
    file: confirms a genuinely missing NSV/Units value and a real recorded
    zero are counted separately here, never merged via fillna(0) the way
    the production chain-level loader does (see docs/PHASE_2_DATA_CONTRACT.md
    §2 for why that pattern is correct at chain grain and wrong here)."""
    nsv, _ = _coerce_numeric(df["NSV"])
    n_missing = int(nsv.isna().sum())
    n_real_zero = int((nsv == 0).sum())
    return {
        "check": "missing_as_zero_treatment",
        "status": "PASS",
        "genuinely_missing_nsv_rows": n_missing,
        "real_zero_nsv_rows": n_real_zero,
        "note": "counted separately by design -- a missing row and a real zero must never be read as the same thing downstream",
    }


def _check_source_total_reconciliation(df, control_total, tolerance_pct=1.0):
    if control_total is None:
        return {"check": "source_total_reconciliation", "status": "NOT_CHECKED",
                "reason": "no control_total supplied -- never assumed to pass"}
    nsv, _ = _coerce_numeric(df["NSV"])
    file_total = float(nsv.sum())
    variance_pct = abs(file_total - control_total) / control_total * 100 if control_total else None
    return {
        "check": "source_total_reconciliation",
        "status": "PASS" if (variance_pct is not None and variance_pct <= tolerance_pct) else "WARN",
        "file_total": round(file_total, 2),
        "control_total": control_total,
        "variance_pct": round(variance_pct, 4) if variance_pct is not None else None,
        "tolerance_pct": tolerance_pct,
    }


def _check_identity_continuity(df, fy27_reference_df):
    if fy27_reference_df is None:
        return {"check": "fy26_fy27_identity_continuity", "status": "NOT_CHECKED",
                "reason": "no FY27 reference frame supplied"}
    a_keys = set(zip(df["Chain"], df["Store Code"].astype(str)))
    b_keys = set(zip(fy27_reference_df["Chain"], fy27_reference_df["Store Code"].astype(str)))
    overlap = a_keys & b_keys
    overlap_pct = round(len(overlap) / len(a_keys) * 100, 2) if a_keys else 0.0
    name_match_pct = None
    if "Store Name" in df.columns and "Store Name" in fy27_reference_df.columns and overlap:
        a_map = df.drop_duplicates(["Chain", "Store Code"]).set_index(["Chain", "Store Code"])["Store Name"]
        b_map = fy27_reference_df.drop_duplicates(["Chain", "Store Code"]).set_index(["Chain", "Store Code"])["Store Name"]
        matches = 0
        for key in overlap:
            av = str(a_map.get(key, "")).strip().lower()
            bv = str(b_map.get(key, "")).strip().lower()
            if av and av == bv:
                matches += 1
        name_match_pct = round(matches / len(overlap) * 100, 2)
    return {
        "check": "fy26_fy27_identity_continuity",
        "status": "PASS" if overlap_pct >= 50.0 else "WARN",
        "fy26_distinct_keys": len(a_keys),
        "fy27_distinct_keys": len(b_keys),
        "overlap_count": len(overlap),
        "overlap_pct_of_fy26": overlap_pct,
        "name_match_pct_on_overlap": name_match_pct,
        "note": "PASS threshold (50%) is a sanity floor, not a target -- see docs/PHASE2_SSG_FEASIBILITY.md for the FY27-internal benchmark (87.9%) this should be compared against once real, not just checked against a low bar",
    }


def validate_store_history(df, control_total=None, fy27_reference_df=None):
    """Runs every readiness check and returns a report dict with an overall
    verdict: BLOCKED / READY / READY_WITH_GOVERNED_EXCEPTIONS.

    df: the FY26 candidate frame, with at least REQUIRED_COLUMNS present
    (column names as documented in docs/PHASE_2_DATA_CONTRACT.md -- a real
    file's raw column names, e.g. 'Site Code', must be renamed to this
    contract's names -- 'Store Code' -- by the caller before calling this,
    so this function's checks stay decoupled from any one source's naming).
    """
    req = _check_required_columns(df)
    if req["status"] == "FAIL":
        return {"verdict": "BLOCKED", "reason": f"missing required columns: {req['missing_columns']}",
                "checks": [req]}

    df = df.copy()
    df["_month_canon"] = df["Month"].map(bd._offtake_row_month)
    df["Chain"] = df["Chain"].map(bd.canon_chain)

    checks = [
        req,
        _check_month_coverage(df),
        _check_duplicate_grain(df),
        _check_store_identity_conflicts(df),
        _check_missing_identifiers(df),
        _check_article_mapping_quality(df),
        _check_financial_values(df),
        _check_nan_infinity(df),
        _check_missing_as_zero(df),
        _check_source_total_reconciliation(df, control_total),
        _check_identity_continuity(df, fy27_reference_df),
    ]

    hard_fail = [c for c in checks if c["status"] == "FAIL"]
    warnings = [c for c in checks if c["status"] == "WARN"]

    if hard_fail:
        verdict = "BLOCKED"
    elif warnings:
        verdict = "READY_WITH_GOVERNED_EXCEPTIONS"
    else:
        verdict = "READY"

    return {"verdict": verdict, "checks": checks,
            "hard_fail_count": len(hard_fail), "warning_count": len(warnings)}


# ---------------------------------------------------------------------------
# Canonical Store Identity Crosswalk builder (docs/STORE_IDENTITY_GOVERNANCE.md)
# ---------------------------------------------------------------------------

def _normalize_name(name):
    return " ".join(str(name).strip().lower().split())


def build_crosswalk_candidates(fy26_df, fy27_df):
    """Returns a list of crosswalk rows per docs/STORE_IDENTITY_GOVERNANCE.md
    §2's schema. Never sets Review_Status to AUTO_CONFIRMED below HIGH
    confidence -- enforced here, not left to the caller."""
    fy26 = fy26_df.copy()
    fy27 = fy27_df.copy()
    fy26["Chain"] = fy26["Chain"].map(bd.canon_chain)
    fy27["Chain"] = fy27["Chain"].map(bd.canon_chain)

    # _norm_name must exist BEFORE the *_by_code indexes are built, so a row
    # looked up from fy26_by_code still carries it (a prior version of this
    # function built the indexes first and always saw an empty _norm_name,
    # silently disabling the whole NORMALIZED_NAME_MATCH branch below --
    # caught by TestCrosswalkBuilder.test_name_match_when_code_changed).
    fy26["_norm_name"] = fy26.get("Store Name", pd.Series(dtype=object)).map(_normalize_name)
    fy27["_norm_name"] = fy27.get("Store Name", pd.Series(dtype=object)).map(_normalize_name)

    fy26_by_code = fy26.drop_duplicates(["Chain", "Store Code"]).set_index(["Chain", "Store Code"])
    fy27_by_code = fy27.drop_duplicates(["Chain", "Store Code"]).set_index(["Chain", "Store Code"])
    fy27_by_name = fy27.drop_duplicates(["Chain", "_norm_name"]).set_index(["Chain", "_norm_name"])

    rows = []
    matched_fy26_keys = set()

    for key in fy26_by_code.index:
        chain, code = key
        rec26 = fy26_by_code.loc[key]
        if key in fy27_by_code.index:
            rec27 = fy27_by_code.loc[key]
            same_state = ("State" not in fy26.columns or "State" not in fy27.columns
                          or str(rec26.get("State", "")).strip().lower() == str(rec27.get("State", "")).strip().lower())
            same_city = ("City" not in fy26.columns or "City" not in fy27.columns
                        or str(rec26.get("City", "")).strip().lower() == str(rec27.get("City", "")).strip().lower())
            confidence = "HIGH" if (same_state and same_city) else "MEDIUM"
            rows.append({
                "Canonical_Store_ID": f"{chain}::{code}",
                "FY26_Store_Code": code, "FY27_Store_Code": code,
                "Chain": chain, "Store_Name": rec26.get("Store Name"),
                "State": rec26.get("State"), "City": rec26.get("City"),
                "Match_Method": "EXACT_CODE_MATCH",
                "Match_Confidence": confidence,
                "Review_Status": "AUTO_CONFIRMED" if confidence == "HIGH" else "PENDING_REVIEW",
                "Exception_Reason": "" if confidence == "HIGH" else "State/City mismatch alongside exact code match",
            })
            matched_fy26_keys.add(key)

    for key in fy26_by_code.index:
        if key in matched_fy26_keys:
            continue
        chain, code = key
        rec26 = fy26_by_code.loc[key]
        norm_key = (chain, rec26.get("_norm_name", ""))
        if norm_key in fy27_by_name.index and norm_key[1]:
            rec27 = fy27_by_name.loc[norm_key]
            rows.append({
                "Canonical_Store_ID": f"{chain}::{code}",
                "FY26_Store_Code": code, "FY27_Store_Code": rec27.get("Store Code"),
                "Chain": chain, "Store_Name": rec26.get("Store Name"),
                "State": rec26.get("State"), "City": rec26.get("City"),
                "Match_Method": "NORMALIZED_NAME_MATCH",
                "Match_Confidence": "MEDIUM",
                "Review_Status": "PENDING_REVIEW",
                "Exception_Reason": "Store Code differs; matched on normalized name only",
            })
            matched_fy26_keys.add(key)

    for key in fy26_by_code.index:
        if key in matched_fy26_keys:
            continue
        chain, code = key
        rec26 = fy26_by_code.loc[key]
        rows.append({
            "Canonical_Store_ID": f"{chain}::{code}",
            "FY26_Store_Code": code, "FY27_Store_Code": None,
            "Chain": chain, "Store_Name": rec26.get("Store Name"),
            "State": rec26.get("State"), "City": rec26.get("City"),
            "Match_Method": "MANUAL_REVIEW",
            "Match_Confidence": "LOW",
            "Review_Status": "PENDING_REVIEW",
            "Exception_Reason": "No FY27 match by code or name -- CLOSED_OR_LOST_STORE candidate, needs human confirmation",
        })

    return rows


def main():
    import argparse
    import json

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--src", required=True, help="Path to a FY26 CSV, columns per docs/PHASE_2_DATA_CONTRACT.md")
    ap.add_argument("--control-total", type=float, default=None)
    ap.add_argument("--fy27-reference", default=None, help="Optional FY27 CSV for identity-continuity check")
    ap.add_argument("--out", default=None, help="Write the JSON report here")
    args = ap.parse_args()

    src_path = Path(args.src)
    if not src_path.exists():
        print(f"BLOCKED_BY_SOURCE_DATA: {src_path} does not exist")
        sys.exit(1)

    df = pd.read_csv(src_path)
    fy27_ref = pd.read_csv(args.fy27_reference) if args.fy27_reference else None
    report = validate_store_history(df, control_total=args.control_total, fy27_reference_df=fy27_ref)

    print(f"Verdict: {report['verdict']}")
    for c in report["checks"]:
        print(f"  [{c['status']}] {c['check']}")

    if args.out:
        import json as _json
        Path(args.out).write_text(_json.dumps(report, indent=2, default=str))
        print(f"Report written to {args.out}")

    sys.exit(0 if report["verdict"] != "BLOCKED" else 1)


if __name__ == "__main__":
    main()
