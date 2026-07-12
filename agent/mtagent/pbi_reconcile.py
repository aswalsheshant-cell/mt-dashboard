"""Command: "Run source-to-model reconciliation." (workflow step 13)

Independently re-derives totals from the ORIGINAL source CSV and compares
them against the built Fact/Dim outputs from ``pbi_dataset.build_dataset``
— deliberately not reusing build_dataset's internal running totals, so a
bug in the build step's own aggregation can't silently pass its own
reconciliation check.

Tolerance is configurable (``cfg.pbi_reconciliation_tolerance_pct``). No
mismatch is ever hidden — every metric is reported, PASS or FAIL.
"""
from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

from .config import Config


def _read_fact(fact_path: Path) -> list[dict]:
    with open(fact_path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _source_totals(source_path: Path) -> dict:
    with open(source_path, newline="", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        idx = {h: i for i, h in enumerate(header)}
        row_count = 0
        nsv_total = mrp_total = qty_total = 0.0
        chains, articles, stores = set(), set(), set()
        by_chain, by_zone = defaultdict(float), defaultdict(float)

        for row in reader:
            row_count += 1
            try:
                nsv = float(row[idx["NSV"]] or 0)
                mrp = float(row[idx["MRP Sales Value"]] or 0)
                qty = float(row[idx["Sales Qty"]] or 0)
            except (ValueError, IndexError):
                continue
            nsv_total += nsv
            mrp_total += mrp
            qty_total += qty
            chain = row[idx["Chain Name"]].strip()
            zone = row[idx["Zone"]].strip().upper()
            ean = row[idx["EAN"]].strip()
            site = row[idx["Site Code"]].strip()
            if chain:
                chains.add(chain)
                by_chain[chain] += nsv
            if zone:
                by_zone[zone] += nsv
            if ean:
                articles.add(ean)
            if site:
                stores.add(site)

    return {
        "row_count": row_count, "nsv_total": nsv_total, "mrp_total": mrp_total, "qty_total": qty_total,
        "distinct_chains": len(chains), "distinct_articles": len(articles), "distinct_stores": len(stores),
        "by_chain": dict(by_chain), "by_zone": dict(by_zone),
    }


def _model_totals(fact_rows: list[dict]) -> dict:
    nsv_total = sum(float(r["NSV"]) for r in fact_rows)
    mrp_total = sum(float(r["MRP_Sales_Value"]) for r in fact_rows)
    qty_total = sum(float(r["Sales_Qty"]) for r in fact_rows)
    chains = {r["Chain"] for r in fact_rows}
    articles = {r["EAN"] for r in fact_rows}
    zones = {r["Zone"] for r in fact_rows}
    by_chain = defaultdict(float)
    by_zone = defaultdict(float)
    for r in fact_rows:
        by_chain[r["Chain"]] += float(r["NSV"])
        by_zone[r["Zone"]] += float(r["NSV"])
    stores = sum(int(r["Store_Count"]) for r in fact_rows)  # not distinct across chains, only an upper bound
    return {
        "row_count": len(fact_rows), "nsv_total": nsv_total, "mrp_total": mrp_total, "qty_total": qty_total,
        "distinct_chains": len(chains), "distinct_articles": len(articles), "distinct_zones": len(zones),
        "by_chain": dict(by_chain), "by_zone": dict(by_zone), "store_count_upper_bound": stores,
    }


def _status(source_val: float, model_val: float, tolerance_pct: float) -> tuple[str, float]:
    if source_val == 0:
        variance_pct = 0.0 if model_val == 0 else 100.0
    else:
        variance_pct = round(100 * abs(source_val - model_val) / abs(source_val), 3)
    return ("PASS" if variance_pct <= tolerance_pct else "FAIL"), variance_pct


_LIKELY_CAUSES = {
    "row_count": "aggregation grain difference (Fact is grouped, not 1:1 with source) -- compare NSV, not row count, for correctness",
    "nsv_total": "unmapped chain/article rows, blank-key rows dropped, or a build-step aggregation bug",
    "mrp_total": "unmapped chain/article rows, blank-key rows dropped, or a build-step aggregation bug",
    "qty_total": "unmapped chain/article rows, blank-key rows dropped, or a build-step aggregation bug",
    "distinct_chains": "chain name not matching ChainMaster.csv after normalization -- check Mapping_Exception_Report",
    "distinct_articles": "EAN not matching ArticleMaster.csv -- check Mapping_Exception_Report (seed master may be incomplete)",
}


def reconcile_source_to_model(cfg: Config, source_path: Path, build_dir: Path) -> dict:
    fact_path = build_dir / "Fact_OfftakeSales.csv"
    if not source_path.exists():
        return {"blocked_reason": f"source file not found: {source_path}"}
    if not fact_path.exists():
        return {"blocked_reason": f"Fact_OfftakeSales.csv not found in {build_dir} -- run build_dataset first"}

    src = _source_totals(source_path)
    fact_rows = _read_fact(fact_path)
    mdl = _model_totals(fact_rows)
    tol = cfg.pbi_reconciliation_tolerance_pct

    rows = []
    for metric, source_val, model_val in [
        ("row_count", src["row_count"], mdl["row_count"]),
        ("nsv_total", src["nsv_total"], mdl["nsv_total"]),
        ("mrp_total", src["mrp_total"], mdl["mrp_total"]),
        ("qty_total", src["qty_total"], mdl["qty_total"]),
        ("distinct_chains", src["distinct_chains"], mdl["distinct_chains"]),
        ("distinct_articles", src["distinct_articles"], mdl["distinct_articles"]),
    ]:
        status, variance_pct = _status(source_val, model_val, tol)
        # row_count is EXPECTED to differ (fact is aggregated) -- always INFO, never FAIL, and never hidden.
        if metric == "row_count":
            status = "INFO"
        rows.append({
            "metric": metric, "source_value": round(source_val, 4), "model_value": round(model_val, 4),
            "absolute_variance": round(source_val - model_val, 4), "variance_pct": variance_pct,
            "status": status, "likely_cause": _LIKELY_CAUSES.get(metric, ""),
            "recommended_action": "none -- within tolerance" if status == "PASS" else
                                   "informational only" if status == "INFO" else
                                   "investigate before marking this build step complete",
        })

    for chain in sorted(set(src["by_chain"]) | set(mdl["by_chain"])):
        source_val, model_val = src["by_chain"].get(chain, 0.0), mdl["by_chain"].get(chain, 0.0)
        status, variance_pct = _status(source_val, model_val, tol)
        rows.append({
            "metric": f"chain_total:{chain}", "source_value": round(source_val, 4), "model_value": round(model_val, 4),
            "absolute_variance": round(source_val - model_val, 4), "variance_pct": variance_pct, "status": status,
            "likely_cause": "" if status == "PASS" else "chain name mapped to a different Account/UNMAPPED bucket than expected",
            "recommended_action": "none -- within tolerance" if status == "PASS" else "check Mapping_Exception_Report for this chain",
        })

    for zone in sorted(set(src["by_zone"]) | set(mdl["by_zone"])):
        source_val, model_val = src["by_zone"].get(zone, 0.0), mdl["by_zone"].get(zone, 0.0)
        status, variance_pct = _status(source_val, model_val, tol)
        rows.append({
            "metric": f"zone_total:{zone}", "source_value": round(source_val, 4), "model_value": round(model_val, 4),
            "absolute_variance": round(source_val - model_val, 4), "variance_pct": variance_pct, "status": status,
            "likely_cause": "" if status == "PASS" else "zone casing/normalization mismatch",
            "recommended_action": "none -- within tolerance" if status == "PASS" else "check Zone normalization in build_dataset",
        })

    out_path = build_dir / "Source_To_Model_Reconciliation_Report.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["metric", "source_value", "model_value", "absolute_variance",
                                            "variance_pct", "status", "likely_cause", "recommended_action"])
        w.writeheader()
        w.writerows(rows)

    failures = [r for r in rows if r["status"] == "FAIL"]
    warning = "" if not failures else f"{len(failures)} metric(s) exceeded the {tol}% reconciliation tolerance"

    return {
        "output_file": str(out_path.relative_to(cfg.root())),
        "validation_result": f"{len(rows)} metrics compared, {len(failures)} FAIL, tolerance={tol}%",
        "warning": warning,
    }
