#!/usr/bin/env python3
"""Risk Rule Aggregator -- Phase A/B/C.

Reads config/risk_rule_registry.yml and, for every rule marked
`evaluation: IMPLEMENTED`, produces risk instances by READING an existing
governed check/status -- never by recomputing a business number.

Still no persistent history, no release-gate wiring, no Likelihood x
Impact scoring (none exists anywhere in this repo yet -- see
docs/RISK_MANAGEMENT_PHASE_A.md). It prints/writes a deterministic snapshot
of CURRENT risk instances, keyed so the same underlying condition always
produces the same Risk_Key across runs (RR-<rule>::<entity>) -- the
append-only history mechanism that would let a Risk_Key be tracked over
time is still not built here.

Phase C added --patch-into-datajs: writes this same snapshot into
dashboard/data.js as DASH.risk_snapshot, additive-only (see
patch_into_datajs()'s docstring), so the "Risk & Control" sub-view under
the Operational Alerts tab has something to read.

Usage:
  python scripts/risk_rule_aggregate.py                       # print summary
  python scripts/risk_rule_aggregate.py --out path/to/file.json
  python scripts/risk_rule_aggregate.py --data-js <path> --registry <path>
  python scripts/risk_rule_aggregate.py --patch-into-datajs    # publish to the dashboard
"""
from __future__ import annotations
import argparse
import json
import os
import re
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import ci_validate_datajs as cvd  # noqa: E402
import store_history_readiness as shr  # noqa: E402

DEFAULT_REGISTRY = REPO / "config" / "risk_rule_registry.yml"
DEFAULT_DATA_JS = REPO / "dashboard" / "data.js"
DEFAULT_SOURCE_REGISTRY = REPO / "config" / "data_source_registry.yml"


def load_registry(path=None):
    p = Path(path or DEFAULT_REGISTRY)
    return yaml.safe_load(p.read_text())


def _instance(rule_id, entity, severity, detail, owner):
    return {
        "risk_key": f"{rule_id}::{entity}",
        "rule_id": rule_id,
        "entity": entity,
        "severity": severity,
        "detail": detail,
        "owner": owner,
    }


def eval_baseline_drift(rule, data_js_path):
    """RR-BASELINE-DRIFT: reuses ci_validate_datajs.check_baselines() as-is."""
    try:
        data = cvd.load_datajs(data_js_path)
    except FileNotFoundError:
        return [], "data.js not found -- nothing to check"
    failures = cvd.check_baselines(data)
    instances = [
        _instance(rule["rule_id"], f"baseline#{i}", "MANDATORY", msg, rule["owner"])
        for i, msg in enumerate(failures)
    ]
    return instances, f"{len(failures)} baseline failure(s) of the checked set"


def eval_source_degraded(rule, source_registry_path):
    """RR-SOURCE-DEGRADED: reuses config/data_source_registry.yml's own
    validation_status field -- never re-derives whether a source is valid."""
    p = Path(source_registry_path or DEFAULT_SOURCE_REGISTRY)
    reg = yaml.safe_load(p.read_text())
    ok_statuses = {"VALIDATED", "AVAILABLE"}
    instances = []
    for name, entry in (reg.get("datasets") or {}).items():
        status = entry.get("validation_status")
        if status not in ok_statuses:
            instances.append(_instance(
                rule["rule_id"], name, status,
                entry.get("business_name", name),
                entry.get("business_owner", "unassigned")))
    return instances, f"{len(instances)} of {len(reg.get('datasets') or {})} registered dataset(s) not VALIDATED/AVAILABLE"


def eval_readiness_gate(rule, data_js_path):
    """RR-READINESS-GATE: reads DASH.readiness.gates as already computed by
    readiness_gate() at build time -- never recomputed here."""
    try:
        data = cvd.load_datajs(data_js_path)
    except FileNotFoundError:
        return [], "data.js not found -- nothing to check"
    gates = cvd.dig(data, "readiness.gates") or {}
    ok_statuses = {"PASS", "N/A"}
    instances = []
    for name, gate in gates.items():
        status = gate.get("status")
        if status not in ok_statuses:
            instances.append(_instance(
                rule["rule_id"], name, status,
                gate.get("measured") or gate.get("label", name),
                rule["owner"]))
    return instances, f"{len(instances)} of {len(gates)} readiness gate(s) not PASS/N-A"


def eval_ssg_source_blocked(rule):
    """RR-SSG-SOURCE-BLOCKED: reuses store_history_readiness.phase2c_gate_status()
    as-is -- never re-derives SSG source readiness."""
    status = shr.phase2c_gate_status()
    instances = []
    if status.get("publication_blocked"):
        instances.append(_instance(
            rule["rule_id"], "ssg_fy26_offtake_source", status.get("reason", "BLOCKED"),
            f"SSG_PROJECT_STATE=WAITING_FOR_SOURCE; {status}", rule["owner"]))
    return instances, f"publication_blocked={status.get('publication_blocked')}"


def eval_forecast_method_fallback(rule, data_js_path):
    """RR-FORECAST-METHOD-FALLBACK: reads DASH.forecast.method's own sentence
    -- never re-derives which forecast method ran.

    Positive-matches the ONE known fallback signature (forecast_block()'s own
    "Seasonally-indexed run-rate" text) rather than the authoritative path's
    wording: the checked-in dashboard/data.js was found, during this rule's
    own build, to carry an authoritative-looking method string that matches
    NEITHER function's current exact template (data.js can be a build or two
    behind this script) -- so requiring an exact match to the authoritative
    phrase produced a false positive. Matching the fallback's own distinctive,
    currently-confirmed phrase is the robust direction: anything that isn't
    positively the known fallback is treated as not-a-risk, never the reverse."""
    try:
        data = cvd.load_datajs(data_js_path)
    except FileNotFoundError:
        return [], "data.js not found -- nothing to check"
    method = cvd.dig(data, "forecast.method") or ""
    is_seasonal_fallback = "Seasonally-indexed run-rate" in method
    instances = []
    if is_seasonal_fallback:
        instances.append(_instance(
            rule["rule_id"], "current_forecast", "SEASONAL_ESTIMATE", method, rule["owner"]))
    return instances, ("SEASONAL_ESTIMATE (fallback)" if is_seasonal_fallback
                        else ("AUTHORITATIVE or unrecognized method text" if method else "forecast.method not present"))


def eval_forecast_growth_clamped(rule, data_js_path):
    """RR-FORECAST-GROWTH-CLAMPED: reads DASH.forecast.growth_assumption_pct
    -- never recomputes the growth rate or its clamp."""
    try:
        data = cvd.load_datajs(data_js_path)
    except FileNotFoundError:
        return [], "data.js not found -- nothing to check"
    method = cvd.dig(data, "forecast.method") or ""
    growth = cvd.dig(data, "forecast.growth_assumption_pct")
    is_seasonal_path = "Seasonally-indexed run-rate" in method
    instances = []
    if is_seasonal_path and growth is not None and growth >= 60.0:
        instances.append(_instance(
            rule["rule_id"], "current_forecast", "CLAMP_HIT",
            f"growth_assumption_pct={growth} on the seasonal-projection path (clamp ceiling 60.0)",
            rule["owner"]))
    return instances, (f"growth_assumption_pct={growth}, seasonal_path={is_seasonal_path}"
                        if growth is not None else "forecast.growth_assumption_pct not present")


def eval_allocation_fallback(rule, data_js_path):
    """RR-ALLOCATION-FALLBACK: reads DASH.chain_allocation_qc as published by
    apply_chain_allocation_enhanced() -- never re-runs or re-derives the
    allocation. Absent is reported as NOT_AVAILABLE, never assumed clean."""
    try:
        data = cvd.load_datajs(data_js_path)
    except FileNotFoundError:
        return [], "data.js not found -- nothing to check"
    qc = cvd.dig(data, "chain_allocation_qc")
    if not qc:
        return [], "NOT_AVAILABLE -- chain_allocation_qc not present in this build (no --primary-only rebuild with an allocation file has run)"
    instances = []
    if qc.get("reconciliation_passed") is False:
        instances.append(_instance(
            rule["rule_id"], "chain_allocation", "RECONCILIATION_FAILED",
            f"variance {qc.get('variance_lakh')} Lakh ({qc.get('variance_pct')}%)", rule["owner"]))
    total = qc.get("total_dist_rows_processed") or 0
    tier3 = qc.get("tier3_rows") or 0
    tier3_pct = round(tier3 / total * 100, 2) if total else None
    note = (f"reconciliation_passed={qc.get('reconciliation_passed')}, "
            f"tier3(unmapped)={tier3}/{total} rows ({tier3_pct}% -- informational, no approved tolerance registered)")
    return instances, note


def eval_mapping_completeness_degraded(rule, data_js_path):
    """RR-MAPPING-COMPLETENESS-DEGRADED: reads DASH.mapping_health.by_fy.*.rag
    as already computed by mapping_health_block() -- never reapplies the RAG
    band itself."""
    try:
        data = cvd.load_datajs(data_js_path)
    except FileNotFoundError:
        return [], "data.js not found -- nothing to check"
    mh = cvd.dig(data, "mapping_health")
    if not mh:
        return [], "NOT_AVAILABLE -- mapping_health not present in this build"
    instances = []
    for fy, entry in (mh.get("by_fy") or {}).items():
        if entry.get("rag") != "green":
            instances.append(_instance(
                rule["rule_id"], fy, entry.get("rag"),
                f"completeness {entry.get('completeness_pct')}%, unmapped NSV Rs {entry.get('unmapped_nsv')} L "
                f"(exception_count={mh.get('exception_count')}, exception_nsv=Rs {mh.get('exception_nsv')} L)",
                rule["owner"]))
    return instances, f"{len(instances)} of {len(mh.get('by_fy') or {})} FY(s) not green"


EVALUATORS = {
    "RR-BASELINE-DRIFT": lambda rule, ctx: eval_baseline_drift(rule, ctx["data_js"]),
    "RR-SOURCE-DEGRADED": lambda rule, ctx: eval_source_degraded(rule, ctx["source_registry"]),
    "RR-READINESS-GATE": lambda rule, ctx: eval_readiness_gate(rule, ctx["data_js"]),
    "RR-SSG-SOURCE-BLOCKED": lambda rule, ctx: eval_ssg_source_blocked(rule),
    "RR-FORECAST-METHOD-FALLBACK": lambda rule, ctx: eval_forecast_method_fallback(rule, ctx["data_js"]),
    "RR-FORECAST-GROWTH-CLAMPED": lambda rule, ctx: eval_forecast_growth_clamped(rule, ctx["data_js"]),
    "RR-ALLOCATION-FALLBACK": lambda rule, ctx: eval_allocation_fallback(rule, ctx["data_js"]),
    "RR-MAPPING-COMPLETENESS-DEGRADED": lambda rule, ctx: eval_mapping_completeness_degraded(rule, ctx["data_js"]),
}


def aggregate(registry_path=None, data_js_path=None, source_registry_path=None):
    registry = load_registry(registry_path)
    ctx = {
        "data_js": data_js_path or DEFAULT_DATA_JS,
        "source_registry": source_registry_path or DEFAULT_SOURCE_REGISTRY,
    }
    rules_report = []
    all_instances = []
    for rule in registry["rules"]:
        rule_id = rule["rule_id"]
        # Pass-through metadata only (never computed) -- lets a consumer (e.g.
        # the dashboard tab) render a self-contained table without needing the
        # registry YAML at runtime.
        meta = {"rule_name": rule.get("rule_name"), "risk_family": rule.get("risk_family")}
        if rule.get("evaluation") != "IMPLEMENTED":
            rules_report.append({
                "rule_id": rule_id, "evaluated": False,
                "reason": rule.get("evaluation", "UNKNOWN"),
                "instances": [], **meta,
            })
            continue
        evaluator = EVALUATORS.get(rule_id)
        if evaluator is None:
            rules_report.append({
                "rule_id": rule_id, "evaluated": False,
                "reason": "NO_EVALUATOR_REGISTERED", "instances": [], **meta,
            })
            continue
        instances, note = evaluator(rule, ctx)
        all_instances.extend(instances)
        rules_report.append({
            "rule_id": rule_id, "evaluated": True, "note": note,
            "instances": instances, **meta,
        })

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "registry_version": registry.get("schema_version"),
        "rule_count": len(registry["rules"]),
        "evaluated_rule_count": sum(1 for r in rules_report if r["evaluated"]),
        "open_risk_instance_count": len(all_instances),
        "rules": rules_report,
    }


def patch_into_datajs(data_js_path=None, registry_path=None, source_registry_path=None):
    """Publish the risk snapshot into dashboard/data.js as DASH.risk_snapshot,
    for Phase C's dashboard sub-view to read client-side.

    dashboard/data.js is otherwise never written by this module -- every
    evaluator above only reads it. This is the one place that writes, and it
    is additive only: the existing dict is loaded, exactly one new top-level
    key is added, and the whole thing is re-serialized with the SAME
    json.dumps(indent=1) convention build_dashboard_data.py itself uses.
    Verified (2026-09-22) that a load->dump round-trip of the real data.js is
    byte-for-byte identical to the original for every untouched key -- so the
    only diff this produces is the new key's addition, never a reformat of
    anything else. Writes atomically (temp file + move), the same pattern
    build_dashboard_data.py's own _safe_write_data_js() uses.
    """
    path = Path(data_js_path or DEFAULT_DATA_JS)
    text = path.read_text(encoding="utf-8")
    m = re.search(r"window\.DASH\s*=\s*", text)
    if not m:
        raise SystemExit(f"{path}: does not look like a data.js (no 'window.DASH =' found)")
    obj = json.loads(text[m.end():].strip().rstrip(";"))

    report = aggregate(registry_path, path, source_registry_path)
    obj["risk_snapshot"] = report

    payload = "window.DASH = " + json.dumps(obj, indent=1, ensure_ascii=False) + ";\n"
    fd, tmp = tempfile.mkstemp(suffix=".js", dir=path.parent)
    try:
        os.close(fd)
        Path(tmp).write_text(payload, encoding="utf-8")
        shutil.move(tmp, path)
    except Exception:
        Path(tmp).unlink(missing_ok=True)
        raise
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", default=None)
    ap.add_argument("--data-js", default=None)
    ap.add_argument("--source-registry", default=None)
    ap.add_argument("--out", default=None, help="write the full JSON snapshot here (default: print summary only)")
    ap.add_argument("--patch-into-datajs", action="store_true",
                     help="also write the snapshot into dashboard/data.js as DASH.risk_snapshot "
                          "(additive only -- see patch_into_datajs()'s docstring for the safety proof)")
    args = ap.parse_args()

    if args.patch_into_datajs:
        report = patch_into_datajs(args.data_js, args.registry, args.source_registry)
        print(f"Patched risk_snapshot into {args.data_js or DEFAULT_DATA_JS}")
    else:
        report = aggregate(args.registry, args.data_js, args.source_registry)

    if args.out:
        outp = Path(args.out)
        outp.parent.mkdir(parents=True, exist_ok=True)
        outp.write_text(json.dumps(report, indent=2))
        print(f"Wrote {outp}")

    print(f"Risk Rule Aggregator -- Phase A  ({report['evaluated_rule_count']}/{report['rule_count']} rules evaluated)")
    print(f"Open risk instances: {report['open_risk_instance_count']}")
    for r in report["rules"]:
        if not r["evaluated"]:
            print(f"  SKIP  {r['rule_id']:<28} ({r['reason']})")
        else:
            print(f"  {'OK  ' if not r['instances'] else 'OPEN'}  {r['rule_id']:<28} {r['note']}")
            for inst in r["instances"]:
                print(f"        - {inst['risk_key']}: {inst['severity']} -- {inst['detail']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
