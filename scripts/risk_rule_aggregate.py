#!/usr/bin/env python3
"""Risk Rule Aggregator -- Phase A (Foundation).

Reads config/risk_rule_registry.yml and, for every rule marked
`evaluation: IMPLEMENTED`, produces risk instances by READING an existing
governed check/status -- never by recomputing a business number.

This is Phase A only: no persistent history, no new dashboard tab, no
release-gate wiring, no Likelihood x Impact scoring (none exists anywhere
in this repo yet -- see docs/RISK_MANAGEMENT_PHASE_A.md). It prints/writes
a deterministic snapshot of CURRENT risk instances, keyed so the same
underlying condition always produces the same Risk_Key across runs
(RR-<rule>::<entity>) -- the append-only history mechanism that would let
a Risk_Key be tracked over time is explicitly Phase B, not built here.

Usage:
  python scripts/risk_rule_aggregate.py                       # print summary
  python scripts/risk_rule_aggregate.py --out path/to/file.json
  python scripts/risk_rule_aggregate.py --data-js <path> --registry <path>
"""
from __future__ import annotations
import argparse
import json
import sys
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


EVALUATORS = {
    "RR-BASELINE-DRIFT": lambda rule, ctx: eval_baseline_drift(rule, ctx["data_js"]),
    "RR-SOURCE-DEGRADED": lambda rule, ctx: eval_source_degraded(rule, ctx["source_registry"]),
    "RR-READINESS-GATE": lambda rule, ctx: eval_readiness_gate(rule, ctx["data_js"]),
    "RR-SSG-SOURCE-BLOCKED": lambda rule, ctx: eval_ssg_source_blocked(rule),
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
        if rule.get("evaluation") != "IMPLEMENTED":
            rules_report.append({
                "rule_id": rule_id, "evaluated": False,
                "reason": rule.get("evaluation", "UNKNOWN"),
                "instances": [],
            })
            continue
        evaluator = EVALUATORS.get(rule_id)
        if evaluator is None:
            rules_report.append({
                "rule_id": rule_id, "evaluated": False,
                "reason": "NO_EVALUATOR_REGISTERED", "instances": [],
            })
            continue
        instances, note = evaluator(rule, ctx)
        all_instances.extend(instances)
        rules_report.append({
            "rule_id": rule_id, "evaluated": True, "note": note,
            "instances": instances,
        })

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "registry_version": registry.get("schema_version"),
        "rule_count": len(registry["rules"]),
        "evaluated_rule_count": sum(1 for r in rules_report if r["evaluated"]),
        "open_risk_instance_count": len(all_instances),
        "rules": rules_report,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", default=None)
    ap.add_argument("--data-js", default=None)
    ap.add_argument("--source-registry", default=None)
    ap.add_argument("--out", default=None, help="write the full JSON snapshot here (default: print summary only)")
    args = ap.parse_args()

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
