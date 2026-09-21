"""Phase 2 Data Readiness Gate — validates a FY26 store x article offtake
extract before any Same-Store Growth calculation is allowed to use it.

Design and governance: docs/PHASE_2_DATA_READINESS_GATE.md,
docs/STORE_IDENTITY_GOVERNANCE.md, docs/PHASE_2_DATA_CONTRACT.md,
docs/PHASE_2_SOURCE_INTAKE_CHECKLIST.md.

Non-destructive: never writes to any source file, never touches
dashboard/data.js, never updates production mappings. Reuses this repo's
existing month-parsing and chain-canonicalization logic
(build_dashboard_data.py) rather than re-deriving it, so a real FY26 file
is interpreted identically to how the production pipeline already
interprets FY27 files of the same shape.

This module is exercised entirely against synthetic fixtures today
(scripts/test_store_history_readiness.py) -- no FY26 file exists in this
repository yet. Running it against real data is the next action once one
is supplied (docs/PHASE_2_EXECUTION_STATUS.md).

CLI exit codes (docs/PHASE_2_DATA_READINESS_GATE.md):
    0 = READY
    2 = READY_WITH_GOVERNED_EXCEPTIONS
    3 = BLOCKED_BY_SOURCE_DATA   (no file, or file unreadable)
    4 = BLOCKED_BY_DATA_QUALITY  (file present, hard-block check failed)
"""
import hashlib
import importlib
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
bd = importlib.import_module("build_dashboard_data")

__version__ = "1.1.0"

REQUIRED_COLUMNS = ["Month", "Chain", "Store Code", "Article", "Units", "NSV"]

FY26_MONTHS_EXPECTED = 12


def _chrono_key(mon_yy_label):
    """Sort key for a 'Mon-YY' label (e.g. 'Apr-26') in actual calendar
    order, not alphabetical order -- 'Feb-26' must sort after 'Nov-25', but
    a plain sorted() on the strings would put it before (F < N)."""
    mon, yy = mon_yy_label.split("-")
    return (int(yy), bd._MON3_NUM[mon])

EXIT_READY = 0
EXIT_READY_WITH_GOVERNED_EXCEPTIONS = 2
EXIT_BLOCKED_BY_SOURCE_DATA = 3
EXIT_BLOCKED_BY_DATA_QUALITY = 4


def _coerce_numeric(series):
    """Numeric coercion that reports what it did instead of silently
    converting bad values to NaN and moving on -- callers must inspect
    the returned invalid_mask before treating the coerced series as safe."""
    coerced = pd.to_numeric(series, errors="coerce")
    was_non_null = series.notna()
    invalid_mask = was_non_null & coerced.isna()
    return coerced, invalid_mask


def _current_git_commit():
    """Best-effort HEAD SHA of the repo this script lives in -- None
    (never a fabricated value) if git isn't available or this isn't a
    checkout, so a QC report can always be traced to the exact validator
    code that produced it."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=Path(__file__).resolve().parent.parent,
            capture_output=True, text=True, timeout=5,
        )
        return out.stdout.strip() if out.returncode == 0 else None
    except Exception:
        return None


def compute_checksum(path):
    """SHA-256 of the raw file bytes -- lets a QC report prove which exact
    file it validated, without ever copying or modifying the source."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _check_required_columns(df):
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    return {
        "check": "required_columns",
        "status": "FAIL" if missing else "PASS",
        "missing_columns": missing,
    }


def _check_month_coverage(df):
    months = sorted({m for m in df["_month_canon"].dropna().unique()}, key=_chrono_key)
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


def _check_duplicate_store_ids(df):
    """A stricter check than duplicate_grain: the same (Chain, Store Code)
    must not appear under two different, mutually exclusive identities in
    the SAME month at the article level in a way that would let one
    physical store's sales get double counted in a cohort roll-up (distinct
    from store_identity_conflicts, which reports the identity mismatch
    itself; this reports whether it would actually inflate a sales sum)."""
    key_cols = ["Month", "Chain", "Store Code"]
    per_key_article_rows = df.groupby(key_cols).size()
    # Not itself a failure (many articles per store per month is normal) --
    # this check exists so a future caller can distinguish "duplicate rows
    # at declared grain" (an ingestion bug) from "this store code was
    # reused for two unrelated sites" (an identity bug), which needs the
    # Store Name / State / City cross-check in _check_store_identity_conflicts
    # to actually detect. Reported here as a cross-reference count only.
    return {
        "check": "duplicate_store_ids",
        "status": "PASS",
        "distinct_store_months": int(len(per_key_article_rows)),
        "note": "cross-reference count; the actual identity-collision detector is store_identity_conflicts",
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


def _check_period_window(df):
    """Flags months that parse successfully but fall OUTSIDE Apr'25-Mar'26
    -- distinct from month_coverage, which only counts how many of the 12
    expected months are present, not whether an extra, out-of-window month
    sneaked in (e.g. a file that accidentally includes Apr'26)."""
    in_window = {f"{m}-25" for m in ("Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")} | \
                {f"{m}-26" for m in ("Jan", "Feb", "Mar")}
    months = {m for m in df["_month_canon"].dropna().unique()}
    out_of_window = sorted(months - in_window, key=_chrono_key)
    return {
        "check": "period_window",
        "status": "PASS" if not out_of_window else "WARN",
        "out_of_window_months": out_of_window,
        "expected_window": "Apr-25 through Mar-26",
    }


def _check_invalid_month_formats(df):
    """Counts rows whose raw Month value could not be parsed into any
    canonical month at all -- distinct from period_window, which only
    flags a VALIDLY-parsed month outside the expected range."""
    n_invalid = int(df["_month_canon"].isna().sum())
    return {
        "check": "invalid_month_formats",
        "status": "PASS" if n_invalid == 0 else "WARN",
        "unparseable_month_row_count": n_invalid,
    }


def _check_unknown_master_values(df):
    """A Chain value that doesn't resolve against this repo's own governed
    alias table (canon_chain()) is a real business exception to review,
    never silently dropped or silently accepted as if it were mapped.
    Store/Article master matching would need a governed store/article
    master this repo doesn't have wired in yet -- not invented here."""
    exceptions = {}
    if "Chain" in df.columns:
        raw_chains = sorted(df["Chain"].dropna().astype(str).str.strip().unique())
        # canon_chain() passes an unrecognized string through unchanged (it only
        # returns None for null input) -- so "recognized" has to be checked
        # against the alias table directly, the same way canon_chain() itself
        # decides it internally, not by looking at canon_chain()'s return value.
        unknown_chains = [c for c in raw_chains if c.lower() not in bd._ALIAS_LOOKUP]
        if unknown_chains:
            exceptions["unknown_chain"] = unknown_chains[:50]
    return {
        "check": "unknown_master_values",
        "status": "PASS" if not exceptions else "WARN",
        "exceptions": exceptions,
        "note": "an unrecognized chain name is a governed business exception requiring review, "
                "not an automatic hard block and never silently mapped or dropped",
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
    verdict: BLOCKED_BY_DATA_QUALITY / READY / READY_WITH_GOVERNED_EXCEPTIONS.

    df: the FY26 candidate frame, with at least REQUIRED_COLUMNS present
    (column names as documented in docs/PHASE_2_DATA_CONTRACT.md -- a real
    file's raw column names, e.g. 'Site Code', must be renamed to this
    contract's names -- 'Store Code' -- by the caller before calling this,
    so this function's checks stay decoupled from any one source's naming).
    """
    req = _check_required_columns(df)
    if req["status"] == "FAIL":
        return {"verdict": "BLOCKED_BY_DATA_QUALITY",
                "reason": f"missing required columns: {req['missing_columns']}",
                "checks": [req], "hard_fail_count": 1, "warning_count": 0}

    if len(df) == 0:
        empty_check = {"check": "non_empty_source", "status": "FAIL", "row_count": 0}
        return {"verdict": "BLOCKED_BY_DATA_QUALITY",
                "reason": "source has zero rows",
                "checks": [req, empty_check], "hard_fail_count": 1, "warning_count": 0}

    df = df.copy()
    df["_month_canon"] = df["Month"].map(bd._offtake_row_month)
    df["Chain"] = df["Chain"].map(bd.canon_chain)

    checks = [
        req,
        _check_month_coverage(df),
        _check_period_window(df),
        _check_invalid_month_formats(df),
        _check_duplicate_grain(df),
        _check_store_identity_conflicts(df),
        _check_duplicate_store_ids(df),
        _check_missing_identifiers(df),
        _check_article_mapping_quality(df),
        _check_unknown_master_values(df),
        _check_financial_values(df),
        _check_nan_infinity(df),
        _check_missing_as_zero(df),
        _check_source_total_reconciliation(df, control_total),
        _check_identity_continuity(df, fy27_reference_df),
    ]

    hard_fail = [c for c in checks if c["status"] == "FAIL"]
    warnings = [c for c in checks if c["status"] == "WARN"]

    if hard_fail:
        verdict = "BLOCKED_BY_DATA_QUALITY"
    elif warnings:
        verdict = "READY_WITH_GOVERNED_EXCEPTIONS"
    else:
        verdict = "READY"

    return {"verdict": verdict, "checks": checks,
            "hard_fail_count": len(hard_fail), "warning_count": len(warnings)}


# ---------------------------------------------------------------------------
# Source Readiness States (docs/PHASE_2_DATA_READINESS_GATE.md)
# ---------------------------------------------------------------------------

SOURCE_STATES = (
    "SOURCE_NOT_FOUND",
    "SOURCE_WRONG_GRAIN",
    "SOURCE_SCHEMA_INVALID",
    "SOURCE_PERIOD_INCOMPLETE",
    "SOURCE_DUPLICATED",
    "SOURCE_UNRECONCILED",
    "SOURCE_AUTHENTICATED",
)


def classify_source(path, fy27_reference_df=None, control_total=None):
    """Single top-level classification into one of SOURCE_STATES, derived
    from -- never duplicating -- validate_store_history()'s own checks.
    Read-only: never writes to path. Handles a non-CSV candidate (e.g. a
    chain-level JSON aggregate) explicitly instead of crashing on it, so a
    file like data/raw_drops/_agg/offtake_fy26.json gets a real, recorded
    classification (SOURCE_WRONG_GRAIN) rather than being silently ignored
    or causing an unhandled exception."""
    p = Path(path)
    if not p.exists():
        return {"source_status": "SOURCE_NOT_FOUND", "path": str(p), "reason": "file does not exist"}

    if p.suffix.lower() == ".json":
        import json as _json
        try:
            data = _json.loads(p.read_text())
        except Exception as e:
            return {"source_status": "SOURCE_SCHEMA_INVALID", "path": str(p),
                    "reason": f"unreadable JSON: {type(e).__name__}"}
        has_store_grain = isinstance(data, dict) and any(
            k in data for k in ("Store Code", "store_code", "by_store", "by_article"))
        if not has_store_grain:
            return {"source_status": "SOURCE_WRONG_GRAIN", "path": str(p),
                    "reason": "JSON aggregate does not contain Store x Article x Units detail "
                              "required by docs/PHASE_2_DATA_CONTRACT.md -- chain/month grain only"}
        return {"source_status": "SOURCE_SCHEMA_INVALID", "path": str(p),
                "reason": "unrecognized JSON structure -- the contract expects a CSV"}

    try:
        df = pd.read_csv(p)
    except Exception as e:
        return {"source_status": "SOURCE_SCHEMA_INVALID", "path": str(p),
                "reason": f"unreadable: {type(e).__name__}"}

    report = validate_store_history(df, control_total=control_total, fy27_reference_df=fy27_reference_df)
    by_name = {c["check"]: c for c in report["checks"]}

    req = by_name.get("required_columns")
    if req and req["status"] == "FAIL":
        return {"source_status": "SOURCE_WRONG_GRAIN", "path": str(p),
                "reason": f"missing required column(s): {req['missing_columns']}"}

    empty_check = by_name.get("non_empty_source")
    if empty_check and empty_check["status"] == "FAIL":
        return {"source_status": "SOURCE_SCHEMA_INVALID", "path": str(p), "reason": "zero rows"}

    nan_check = by_name.get("nan_infinity")
    if nan_check and nan_check["status"] == "FAIL":
        return {"source_status": "SOURCE_SCHEMA_INVALID", "path": str(p),
                "reason": "NaN/Infinity present in financial fields"}

    month_check = by_name.get("month_coverage")
    if month_check and month_check["status"] != "PASS":
        return {"source_status": "SOURCE_PERIOD_INCOMPLETE", "path": str(p),
                "reason": f"{month_check['months_present_count']}/{month_check['months_expected']} months present"}

    dup_check = by_name.get("duplicate_grain")
    if dup_check and dup_check["status"] != "PASS":
        return {"source_status": "SOURCE_DUPLICATED", "path": str(p),
                "reason": f"{dup_check['duplicate_row_count']} duplicate rows at declared grain"}

    recon_check = by_name.get("source_total_reconciliation")
    if recon_check and recon_check["status"] == "WARN":
        return {"source_status": "SOURCE_UNRECONCILED", "path": str(p),
                "reason": f"variance {recon_check['variance_pct']}% exceeds tolerance {recon_check['tolerance_pct']}%"}

    return {"source_status": "SOURCE_AUTHENTICATED", "path": str(p),
            "reason": "all readiness checks pass", "full_report": report}


# ---------------------------------------------------------------------------
# Governed column aliases (docs/PHASE_2_SOURCE_INTAKE_CHECKLIST.md §5)
# ---------------------------------------------------------------------------

GOVERNED_COLUMN_ALIASES = {
    # Contract name -> known raw source name(s), in priority order.
    # Explicit and versioned here -- never applied silently. A rename only
    # happens when the caller opts in (apply_governed_aliases(), or the
    # CLI's --use-governed-aliases), so it is always a visible, auditable
    # decision, never a guess.
    "Store Code": ["Site Code"],
    "Store Name": ["Site Name"],
    "Chain": ["Chain Name"],
    "Units": ["Sales Qty"],
}


def apply_governed_aliases(df):
    """Renames raw source columns to this contract's names, using ONLY the
    explicit map above. Returns (renamed_df, applied_renames) so the
    caller can log exactly what happened -- never a silent rename."""
    applied = {}
    df = df.copy()
    for contract_name, raw_names in GOVERNED_COLUMN_ALIASES.items():
        if contract_name in df.columns:
            continue
        for raw_name in raw_names:
            if raw_name in df.columns:
                df = df.rename(columns={raw_name: contract_name})
                applied[contract_name] = raw_name
                break
    return df, applied


# ---------------------------------------------------------------------------
# Raw source manifest (bronze-layer provenance, separate from the QC report)
# ---------------------------------------------------------------------------

def build_source_manifest(path, dataset_name="FY26_OFFTAKE_STORE_ARTICLE"):
    """Lightweight, permanent provenance record for a received source file
    -- separate from the full QC artifact. Never modifies the source."""
    p = Path(path)
    row_count = column_count = period_min = period_max = None
    if p.exists() and p.suffix.lower() == ".csv":
        try:
            df = pd.read_csv(p)
            row_count = int(len(df))
            column_count = int(len(df.columns))
            if "Month" in df.columns:
                canon = sorted({m for m in df["Month"].map(bd._offtake_row_month).dropna().unique()},
                               key=_chrono_key)
                if canon:
                    period_min, period_max = canon[0], canon[-1]
        except Exception:
            pass
    return {
        "dataset_name": dataset_name,
        "source_filename": str(p),
        "sha256": compute_checksum(p) if p.exists() else None,
        "file_size": p.stat().st_size if p.exists() else None,
        "row_count": row_count,
        "column_count": column_count,
        "period_min": period_min,
        "period_max": period_max,
        "ingestion_timestamp": datetime.now(timezone.utc).isoformat(),
        "schema_version": __version__,
        "source_status": classify_source(p)["source_status"],
    }


# ---------------------------------------------------------------------------
# Reconciliation placeholder (docs/PHASE_2_DATA_READINESS_GATE.md) -- shape
# only, no invented tolerance
# ---------------------------------------------------------------------------

def reconciliation_placeholder(raw_total=None, canonical_total=None, mapped_total=None,
                                unmapped_total=None, governed_tolerance_pct=None):
    """Prepares the reconciliation output shape without inventing a
    tolerance. config/analytics_config.json carries no reconciliation
    tolerance today (checked directly, not assumed) -- status stays
    BLOCKED_PENDING_POLICY until a governed threshold exists, or a
    Finance-confirmed control total plus tolerance is passed explicitly."""
    diff = diff_pct = None
    if raw_total is not None and canonical_total is not None:
        diff = round(canonical_total - raw_total, 2)
        diff_pct = round(abs(diff) / raw_total * 100, 4) if raw_total else None
    if governed_tolerance_pct is None:
        status = "BLOCKED_PENDING_POLICY"
    elif diff_pct is not None and diff_pct <= governed_tolerance_pct:
        status = "PASS"
    else:
        status = "WARN"
    return {
        "raw_fy26_value": raw_total,
        "canonical_fy26_value": canonical_total,
        "mapped_fy26_value": mapped_total,
        "unmapped_value": unmapped_total,
        "difference": diff,
        "difference_pct": diff_pct,
        "governed_tolerance_pct": governed_tolerance_pct,
        "status": status,
        "note": "governed_tolerance_pct must come from config/analytics_config.json or an explicit "
                "Finance-confirmed figure -- none registered today, so status stays "
                "BLOCKED_PENDING_POLICY rather than guessing a threshold",
    }


# ---------------------------------------------------------------------------
# EXPERIMENTAL -- Identity / Chain-Continuity separation (NOT production).
#
# Prepared per docs/PHASE_2_EXECUTION_STATUS.md's deferred design note.
# NOT called anywhere in build_crosswalk_candidates() above -- that
# function's Cohort_Status field is UNCHANGED and remains the actual
# production behavior. This exists so the distinction is tested and ready
# to wire in ONLY once real FY26 evidence (a genuine chain migration or
# acquisition case) justifies it. Deliberately a two-state prototype, not
# the full 5-way sub-classification (CHAIN_NAME_STANDARDIZATION /
# STORE_TRANSFER / CHAIN_ACQUISITION / SOURCE_MAPPING_ERROR /
# UNKNOWN_CHAIN_CHANGE) previously suggested -- inventing that distinction
# without a real case to design it against would be exactly the kind of
# speculative over-engineering this phase is explicitly meant to avoid.
# ---------------------------------------------------------------------------

def classify_identity_and_continuity(fy26_row, fy27_row):
    """Given a matched pair of crosswalk-shaped rows, returns separate
    Identity_Status and Chain_Continuity_Status alongside a Cohort_Status
    -- prototype only, not called by the production crosswalk builder."""
    same_code = str(fy26_row.get("Store Code")) == str(fy27_row.get("Store Code"))
    identity_status = "SAME_IDENTITY" if same_code else "IDENTITY_UNRESOLVED"
    fy26_chain = bd.canon_chain(fy26_row.get("Chain"))
    fy27_chain = bd.canon_chain(fy27_row.get("Chain"))
    continuity_status = "CHAIN_CONTINUOUS" if fy26_chain == fy27_chain else "CHAIN_CHANGED_UNCLASSIFIED"
    cohort_status = ("COMPARABLE_STORE"
                      if (identity_status == "SAME_IDENTITY" and continuity_status == "CHAIN_CONTINUOUS")
                      else "BLOCKED_FOR_REVIEW")
    return {"Identity_Status": identity_status, "Chain_Continuity_Status": continuity_status,
            "Cohort_Status": cohort_status}


# ---------------------------------------------------------------------------
# Canonical Store Identity Crosswalk builder (docs/STORE_IDENTITY_GOVERNANCE.md)
# ---------------------------------------------------------------------------

def _normalize_name(name):
    return " ".join(str(name).strip().lower().split())


def build_crosswalk_candidates(fy26_df, fy27_df):
    """Returns a list of crosswalk rows per docs/STORE_IDENTITY_GOVERNANCE.md
    §2's schema, each also carrying a Cohort_Status per §5 of that document.
    Never sets Review_Status to AUTO_CONFIRMED below HIGH confidence --
    enforced here, not left to the caller. Covers stores on BOTH sides: a
    FY26-only store (no match found) and a FY27-only store (no FY26
    counterpart) are both emitted -- an earlier version of this function
    only walked the FY26 side, which meant a store opened in FY27 never
    appeared in the crosswalk at all (silently invisible, not even flagged
    NEW_STORE)."""
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
    matched_fy27_codes = set()  # (Chain, FY27_Store_Code) consumed by any match

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
            review = "AUTO_CONFIRMED" if confidence == "HIGH" else "PENDING_REVIEW"
            rows.append({
                "Canonical_Store_ID": f"{chain}::{code}",
                "FY26_Store_Code": code, "FY27_Store_Code": code,
                "Chain": chain, "Store_Name": rec26.get("Store Name"),
                "State": rec26.get("State"), "City": rec26.get("City"),
                "Match_Method": "EXACT_CODE_MATCH",
                "Match_Confidence": confidence,
                "Review_Status": review,
                "Exception_Reason": "" if confidence == "HIGH" else "State/City mismatch alongside exact code match",
                "Cohort_Status": "COMPARABLE_STORE" if review == "AUTO_CONFIRMED" else "BLOCKED_FOR_REVIEW",
            })
            matched_fy26_keys.add(key)
            matched_fy27_codes.add((chain, code))

    for key in fy26_by_code.index:
        if key in matched_fy26_keys:
            continue
        chain, code = key
        rec26 = fy26_by_code.loc[key]
        norm_key = (chain, rec26.get("_norm_name", ""))
        if norm_key in fy27_by_name.index and norm_key[1]:
            rec27 = fy27_by_name.loc[norm_key]
            fy27_code = rec27.get("Store Code")
            rows.append({
                "Canonical_Store_ID": f"{chain}::{code}",
                "FY26_Store_Code": code, "FY27_Store_Code": fy27_code,
                "Chain": chain, "Store_Name": rec26.get("Store Name"),
                "State": rec26.get("State"), "City": rec26.get("City"),
                "Match_Method": "NORMALIZED_NAME_MATCH",
                "Match_Confidence": "MEDIUM",
                "Review_Status": "PENDING_REVIEW",
                "Exception_Reason": "Store Code differs; matched on normalized name only",
                "Cohort_Status": "BLOCKED_FOR_REVIEW",
            })
            matched_fy26_keys.add(key)
            if fy27_code is not None:
                matched_fy27_codes.add((chain, fy27_code))

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
            "Exception_Reason": "No FY27 match by code or name -- could be a closure or a broken match; not distinguishable without human confirmation",
            "Cohort_Status": "UNMATCHED_STORE",
        })

    # Reverse pass: a FY27 store never consumed by any match above is
    # genuinely new (or, symmetrically, this crosswalk simply couldn't find
    # its FY26 counterpart) -- either way it must appear, not stay invisible.
    for key in fy27_by_code.index:
        if key in matched_fy27_codes:
            continue
        chain, code = key
        rec27 = fy27_by_code.loc[key]
        rows.append({
            "Canonical_Store_ID": f"{chain}::{code}",
            "FY26_Store_Code": None, "FY27_Store_Code": code,
            "Chain": chain, "Store_Name": rec27.get("Store Name"),
            "State": rec27.get("State"), "City": rec27.get("City"),
            "Match_Method": "MANUAL_REVIEW",
            "Match_Confidence": "LOW",
            "Review_Status": "PENDING_REVIEW",
            "Exception_Reason": "No FY26 match by code or name -- genuinely new store, or a broken match; not distinguishable without human confirmation",
            "Cohort_Status": "NEW_STORE",
        })

    return rows


def cohort_counts(crosswalk_rows):
    counts = {}
    for row in crosswalk_rows:
        status = row.get("Cohort_Status", "UNKNOWN")
        counts[status] = counts.get(status, 0) + 1
    return counts


def match_method_counts(crosswalk_rows):
    counts = {}
    for row in crosswalk_rows:
        method = row.get("Match_Method", "UNKNOWN")
        counts[method] = counts.get(method, 0) + 1
    return counts


def phase2c_gate_status():
    """Single-call summary proving: Phase 2B preserved, Phase 2C harness
    ready, no FY26 production ingestion performed, publication blocked
    until a real source is authenticated. Read-only -- inspects repo
    state, changes nothing."""
    src_dir = Path(__file__).resolve().parent.parent / "PowerBI" / "RawDataFolders" / "Offtake_Monthly"
    known_fy27 = {"offtake_store_article_Apr_26.csv", "offtake_store_article_May_26.csv",
                  "offtake_store_article_Jun_26.csv", "offtake_store_article_Jul_26.csv",
                  "offtake_store_article_Aug_26.csv"}
    real_fy26_exists = False
    if src_dir.exists():
        candidates = [f.name for f in src_dir.glob("*.csv")
                      if f.name not in known_fy27 and not f.name.startswith("_")]
        real_fy26_exists = len(candidates) > 0
    return {
        "phase_2b_status": "CERTIFIED",
        "phase_2c_harness_status": "READY",
        "fy26_production_ingestion_performed": False,
        "source_authenticated": real_fy26_exists,
        "publication_blocked": not real_fy26_exists,
        "actual_ingestion": "NOT_STARTED",
        "reason": "BLOCKED_BY_SOURCE_DATA" if not real_fy26_exists else "SOURCE_PRESENT_NOT_YET_VALIDATED",
    }


def main():
    import argparse
    import json as _json

    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", default=None,
                     help="Path to a FY26 CSV, columns per docs/PHASE_2_DATA_CONTRACT.md")
    ap.add_argument("--control-total", type=float, default=None)
    ap.add_argument("--fy27-reference", default=None,
                     help="Optional FY27 CSV for identity-continuity check and crosswalk building. "
                          "MUST already use this contract's column names (Chain, Store Code, Store "
                          "Name, ...) -- the real files in PowerBI/RawDataFolders/Offtake_Monthly/ "
                          "use raw names (Chain Name, Site Code, Site Name) and need the same rename "
                          "step described in docs/PHASE_2_SOURCE_INTAKE_CHECKLIST.md §5 applied first.")
    ap.add_argument("--out", default="docs/phase2_qc/store_history_readiness_report.json",
                     help="Write the QC JSON artifact here (default: docs/phase2_qc/...)")
    ap.add_argument("--dry-run", action="store_true", default=True,
                     help="No effect today -- this validator has no write path against production "
                          "data at all yet (never touches dashboard/data.js or any source file); "
                          "the flag exists so a future crosswalk-persistence step defaults safe.")
    ap.add_argument("--classify", default=None,
                     help="Run ONLY the SOURCE_STATES classification against this path (any file, "
                          "CSV or not) and exit -- does not require the file to already match the "
                          "contract. Use this to check a candidate before deciding whether it's "
                          "worth a full --src run.")
    ap.add_argument("--gate-status", action="store_true",
                     help="Print the Phase 2C release-gate summary (Phase 2B preserved, harness "
                          "ready, no production ingestion performed, publication blocked) and exit. "
                          "Ignores --src.")
    args = ap.parse_args()

    if args.gate_status:
        import json as _json2
        status = phase2c_gate_status()
        print(_json2.dumps(status, indent=2))
        sys.exit(EXIT_READY if not status["publication_blocked"] else EXIT_BLOCKED_BY_SOURCE_DATA)

    if args.classify:
        classification = classify_source(args.classify)
        classification.pop("full_report", None)
        import json as _json3
        print(_json3.dumps(classification, indent=2, default=str))
        sys.exit(EXIT_READY if classification["source_status"] == "SOURCE_AUTHENTICATED"
                  else EXIT_BLOCKED_BY_SOURCE_DATA)

    if not args.src:
        print("READY_FOR_SOURCE_INGESTION")
        print("BLOCKED_BY_SOURCE_DATA: no --src supplied")
        print("Missing dependency: a real FY26 (Apr'25-Mar'26) store x article "
              "offtake extract -- see docs/PHASE_2_DATA_CONTRACT.md")
        sys.exit(EXIT_BLOCKED_BY_SOURCE_DATA)

    src_path = Path(args.src)
    if not src_path.exists():
        print("READY_FOR_SOURCE_INGESTION")
        print(f"BLOCKED_BY_SOURCE_DATA: {src_path} does not exist")
        sys.exit(EXIT_BLOCKED_BY_SOURCE_DATA)

    df = pd.read_csv(src_path)
    fy27_ref = pd.read_csv(args.fy27_reference) if args.fy27_reference else None
    if fy27_ref is not None:
        missing_ref_cols = [c for c in ("Chain", "Store Code") if c not in fy27_ref.columns]
        if missing_ref_cols:
            print(f"BLOCKED_BY_DATA_QUALITY: --fy27-reference is missing required column(s) "
                  f"{missing_ref_cols} -- it must use this contract's column names, not a raw "
                  f"source's own names. See docs/PHASE_2_SOURCE_INTAKE_CHECKLIST.md §5.")
            sys.exit(EXIT_BLOCKED_BY_DATA_QUALITY)
        fy27_ref = fy27_ref.copy()
        fy27_ref["Chain"] = fy27_ref["Chain"].map(bd.canon_chain)
    report = validate_store_history(df, control_total=args.control_total, fy27_reference_df=fy27_ref)

    crosswalk = []
    if fy27_ref is not None and report["verdict"] != "BLOCKED_BY_DATA_QUALITY":
        crosswalk = build_crosswalk_candidates(df, fy27_ref)

    date_range = None
    if "Month" in df.columns:
        # Canonical-parsed months, not raw values -- a real extract can mix
        # "Apr'26"-style strings with Excel-serial fallbacks (e.g. 46113.0)
        # in the same Month column; sorting the raw strings would report a
        # meaningless alphabetical min/max instead of an actual date range.
        canon_months = sorted({m for m in df["Month"].map(bd._offtake_row_month).dropna().unique()}, key=_chrono_key)
        date_range = {"min": canon_months[0], "max": canon_months[-1]} if canon_months else None

    qc_artifact = {
        # Provenance -- the only fields in this artifact allowed to vary
        # between two runs against the identical file (see
        # docs/PHASE_2_DATA_READINESS_GATE.md's determinism note; every
        # OTHER field below must be byte-identical across repeat runs).
        "run_id": f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_{uuid.uuid4().hex[:8]}",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": _current_git_commit(),
        "validator_version": __version__,
        "detected_grain": "Month x Chain x Store Code x Article",
        "source_filename": str(src_path),
        "source_checksum_sha256": compute_checksum(src_path),
        "row_count": int(len(df)),
        "date_range": date_range,
        "final_verdict": report["verdict"],
        "hard_fail_count": report["hard_fail_count"],
        "warning_count": report["warning_count"],
        "checks": report["checks"],
        "crosswalk_row_count": len(crosswalk),
        "cohort_counts": cohort_counts(crosswalk),
        "match_method_counts": match_method_counts(crosswalk),
        "dry_run": args.dry_run,
    }

    print(f"Verdict: {report['verdict']}")
    for c in report["checks"]:
        print(f"  [{c['status']}] {c['check']}")
    if crosswalk:
        print(f"Crosswalk candidates: {len(crosswalk)} rows, cohort counts: {qc_artifact['cohort_counts']}")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(_json.dumps(qc_artifact, indent=2, default=str))
    print(f"QC artifact written to {out_path}")

    if report["verdict"] == "BLOCKED_BY_DATA_QUALITY":
        sys.exit(EXIT_BLOCKED_BY_DATA_QUALITY)
    elif report["verdict"] == "READY_WITH_GOVERNED_EXCEPTIONS":
        sys.exit(EXIT_READY_WITH_GOVERNED_EXCEPTIONS)
    else:
        sys.exit(EXIT_READY)


if __name__ == "__main__":
    main()
