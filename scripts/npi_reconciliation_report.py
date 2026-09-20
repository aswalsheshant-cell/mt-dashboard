#!/usr/bin/env python3
"""NPI release evidence pack: independently reconciles npd_block()'s output
against the real detail_records it was built from, and against itself, so
the NPI numbers are defensible when Finance/Sales/KAMs/leadership question
them -- not just "the code ran without an exception."

This is deliberately a SEPARATE, independent pass over detail_records
(reusing npd_block() only for the fields it doesn't make sense to
recompute a second way, e.g. the March carry-forward rule itself) rather
than trusting the checked-in dashboard/data.js's npd block at face value --
a stale artifact would otherwise pass every check trivially.

Usage:
    python scripts/npi_reconciliation_report.py \
        --data dashboard/data.js \
        --out-dir /tmp/npi-evidence

Writes:
    <out-dir>/npi_release_reconciliation.csv   -- one row per Chain x EAN pair
    <out-dir>/npi_release_summary.json         -- headline QC/reconciliation result

Exits non-zero if any control fails, so this can gate a release the same
way the other validation scripts in this repo do.
"""
from __future__ import annotations
import argparse
import csv
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_dashboard_data as bd


def load_dash(data_path: Path) -> dict:
    txt = data_path.read_text(encoding="utf-8")
    m = re.search(r"window\.DASH\s*=\s*(\{.*\})\s*;?\s*$", txt, re.DOTALL)
    if not m:
        raise SystemExit(f"Could not find window.DASH in {data_path}")
    return json.loads(m.group(1))


def grain_key(chain, article, ean):
    """Same grain as npd_block(): Chain x EAN, falling back to Chain x
    Article text only when a pair has no EAN. Kept here as an independent
    re-implementation (not imported from bd's closure) since this whole
    module exists to cross-check npd_block(), not re-trust it."""
    return (chain, "EAN", ean) if ean else (chain, "ART", article)


def row_key(row):
    """grain_key() for an already-built npd launch/history-incomplete row."""
    return grain_key(row["chain"], row["article"], row.get("ean"))


def independent_first_sale_scan(detail_records):
    """Recomputes first-observed-sale-month per Chain x EAN grain directly
    from detail_records, independently of npd_block()'s internals, as a
    cross-check rather than trusting the same code path twice."""
    first_seen = {}
    for r in detail_records:
        chain, article = r.get("Chain"), r.get("Article")
        fy, month = r.get("FY"), r.get("Month")
        if not (chain and article and fy and month and month in bd._FY_MONTH_ORDER):
            continue
        key = grain_key(chain, article, r.get("EAN"))
        idx = (bd.fy_start_year(fy), bd._FY_MONTH_ORDER[month])
        is_valid = (r.get("NSV") or 0.0) > 0 and (r.get("Qty") or 0.0) > 0
        if is_valid:
            if key not in first_seen or idx < first_seen[key]:
                first_seen[key] = idx
    return first_seen


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="dashboard/data.js")
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()

    data_path = Path(args.data)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    dash = load_dash(data_path)
    detail_records = dash.get("detail_records") or []
    if not detail_records:
        raise SystemExit("No detail_records in data.js -- nothing to reconcile.")

    # Recompute npd fresh from the same detail_records the checked-in
    # artifact was supposedly built from -- if this disagrees with
    # dash["npd"], the artifact is stale, which is itself a release-blocking
    # finding, not something to silently paper over.
    npd_fresh = bd.npd_block(detail_records)
    npd_checked_in = dash.get("npd")
    artifact_stale = npd_fresh != npd_checked_in

    failures = []

    # Control: unique launch key -- one record per Chain x EAN grain across
    # ALL cohorts combined (a pair must not appear twice).
    all_launch_keys = [row_key(r) for rows in npd_fresh["by_fy"].values() for r in rows]
    duplicate_keys = len(all_launch_keys) - len(set(all_launch_keys))
    if duplicate_keys:
        failures.append(f"{duplicate_keys} Chain x EAN pair(s) appear in more than one cohort")

    # Control: first-observed-sale reconciliation -- independent scan must
    # agree with every launch's recorded actual_first_sale_fy/month.
    independent_first_seen = independent_first_sale_scan(detail_records)
    mismatches = 0
    for rows in npd_fresh["by_fy"].values():
        for row in rows:
            key = row_key(row)
            expected_fy_tag_month = independent_first_seen.get(key)
            recorded = (bd.fy_start_year(row["actual_first_sale_fy"]),
                        bd._FY_MONTH_ORDER[row["actual_first_sale_month"]])
            if expected_fy_tag_month != recorded:
                mismatches += 1
    if mismatches:
        failures.append(f"{mismatches} launch(es) disagree with an independent first-sale rescan")

    # Control: March carry-forward correctly assigned -- 100% or fail.
    march_total = march_correct = 0
    non_march_total = non_march_correct = 0
    for rows in npd_fresh["by_fy"].values():
        for row in rows:
            fy_num = int(row["actual_first_sale_fy"][2:])
            if row["actual_first_sale_month"] == "March":
                march_total += 1
                if row["npi_cohort_fy"] == f"FY{fy_num + 1}":
                    march_correct += 1
            else:
                non_march_total += 1
                if row["npi_cohort_fy"] == row["actual_first_sale_fy"]:
                    non_march_correct += 1
    if march_total and march_correct != march_total:
        failures.append(f"March carry-forward: only {march_correct}/{march_total} correctly assigned")
    if non_march_total and non_march_correct != non_march_total:
        failures.append(f"Non-March cohort mapping: only {non_march_correct}/{non_march_total} correct")

    # Control: at each pair's recorded launch month, at least one VALID
    # (NSV>0 and Qty>0) row must exist -- a return/zero-sale row must never
    # be the sole evidence for a launch month. Pre-indexed once (not a
    # nested O(launches x records) scan) for performance on real data volume.
    valid_at_key_month = set()  # (grain_key, fy_year, month_order)
    for r in detail_records:
        chain, article, fy, month = r.get("Chain"), r.get("Article"), r.get("FY"), r.get("Month")
        if not (chain and article and fy and month and month in bd._FY_MONTH_ORDER):
            continue
        if (r.get("NSV") or 0.0) > 0 and (r.get("Qty") or 0.0) > 0:
            valid_at_key_month.add((grain_key(chain, article, r.get("EAN")),
                                     bd.fy_start_year(fy), bd._FY_MONTH_ORDER[month]))
    invalid_as_launch = 0
    for rows in npd_fresh["by_fy"].values():
        for row in rows:
            key = (row_key(row), bd.fy_start_year(row["actual_first_sale_fy"]),
                   bd._FY_MONTH_ORDER[row["actual_first_sale_month"]])
            if key not in valid_at_key_month:
                invalid_as_launch += 1
    if invalid_as_launch:
        failures.append(f"{invalid_as_launch} launch(es) have no valid (NSV>0 and Qty>0) row at their recorded launch month")

    # Control: cohort totals reconcile to detail (NSV/units/active/contribution/
    # avg/productivity), independently recomputed, not just re-reading npd's
    # own fields back at itself.
    for cohort_fy, m in npd_fresh["metrics_by_fy"].items():
        pair_keys = {row_key(r) for r in npd_fresh["by_fy"][cohort_fy]}
        nsv = qty = 0.0
        active = set()
        fy_total = 0.0
        for r in detail_records:
            if r.get("FY") != cohort_fy:
                continue
            fy_total += r.get("NSV") or 0.0
            key = grain_key(r.get("Chain"), r.get("Article"), r.get("EAN"))
            if key in pair_keys:
                row_nsv = r.get("NSV") or 0.0
                nsv += row_nsv
                qty += r.get("Qty") or 0.0
                if row_nsv > 0:
                    active.add(key)
        if round(nsv, 2) != m["npi_nsv"]:
            failures.append(f"{cohort_fy}: recomputed NPI NSV {round(nsv,2)} != reported {m['npi_nsv']}")
        if round(qty, 2) != m["npi_units"]:
            failures.append(f"{cohort_fy}: recomputed NPI units {round(qty,2)} != reported {m['npi_units']}")
        if len(active) != m["active_npi_count"]:
            failures.append(f"{cohort_fy}: recomputed active count {len(active)} != reported {m['active_npi_count']}")
        if fy_total and round(nsv / fy_total * 100, 2) != m["npi_contribution_pct"]:
            failures.append(f"{cohort_fy}: recomputed contribution % != reported")
        if len(pair_keys) and round(nsv / len(pair_keys), 2) != m["avg_nsv_per_launch"]:
            failures.append(f"{cohort_fy}: recomputed avg NSV/launch != reported")
        if active and round(nsv / len(active), 2) != m["npi_productivity"]:
            failures.append(f"{cohort_fy}: recomputed productivity != reported")

    if artifact_stale:
        failures.append("Checked-in dashboard/data.js's npd block does not match a fresh "
                         "recompute from its own detail_records -- artifact is stale.")

    # ---- write the Chain x EAN reconciliation CSV ----
    csv_path = out_dir / "npi_release_reconciliation.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["chain", "ean", "article", "record_type", "actual_first_sale_fy",
                    "actual_first_sale_month", "npi_cohort_fy",
                    "history_months_before_first_sale", "launch_confirmation_status"])
        for rows in npd_fresh["by_fy"].values():
            for row in rows:
                w.writerow([row["chain"], row.get("ean"), row["article"], "launch",
                            row["actual_first_sale_fy"], row["actual_first_sale_month"],
                            row["npi_cohort_fy"], row["history_months_before_first_sale"],
                            row["launch_confirmation_status"]])
        for row in npd_fresh["history_incomplete_pairs"]:
            w.writerow([row["chain"], row.get("ean"), row["article"], "boundary_unknown",
                        row["first_observed_fy"], row["first_observed_month"],
                        "", row["history_months_before_first_sale"], "boundary_unknown"])

    # ---- write the headline summary JSON ----
    total_pairs = len(all_launch_keys) + len(npd_fresh["history_incomplete_pairs"])
    confirmed = sum(m["confirmed_launch_count"] for m in npd_fresh["metrics_by_fy"].values())
    observed_only = sum(m["observed_only_launch_count"] for m in npd_fresh["metrics_by_fy"].values())
    march_carry = march_total
    summary = {
        "npi_model_version": "fy-cohort-march-carryforward-v2",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_data_path": str(data_path),
        "total_chain_ean_pairs": total_pairs,
        "confirmed_launches": confirmed,
        "observed_only_launches": observed_only,
        "boundary_unknown_pairs": len(npd_fresh["history_incomplete_pairs"]),
        "march_carry_forward_count": march_carry,
        "qc_failures": len(failures),
        "qc_failure_detail": failures,
        "artifact_stale": artifact_stale,
        "yoy_valid_by_fy": {fy: m["yoy_comparison_valid"] for fy, m in npd_fresh["metrics_by_fy"].items()},
        "history_coverage_by_fy": {fy: m["history_coverage"] for fy, m in npd_fresh["metrics_by_fy"].items()},
    }
    json_path = out_dir / "npi_release_summary.json"
    json_path.write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n", encoding="utf-8")

    print(f"Wrote {csv_path} ({total_pairs} rows)")
    print(f"Wrote {json_path}")
    print(json.dumps(summary, indent=2))

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
