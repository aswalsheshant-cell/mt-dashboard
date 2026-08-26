#!/usr/bin/env python3
"""
Sprint 9 Phase 1: Threshold Rule Evaluator

Evaluates compliance and fill-rate metrics against operational thresholds.
Generates active alerts (CRITICAL_OOS, AUDIT_FAILURE, SERVICE_BREACH).

USAGE:
  python scripts/alerts/evaluate_alerts.py --output dashboard/alerts_feed.json

  Reads:
    - dashboard/compliance_metrics.json
    - Output: dashboard/alerts_feed.json (active alerts for UI consumption)
"""
from __future__ import annotations
import json
from datetime import datetime
import uuid

THRESHOLDS = {
    "doc_critical": 7,           # DOC < 7 days = CRITICAL_OOS
    "pes_audit": 60.0,           # PES < 60% = AUDIT_FAILURE
    "cfr_service": 90.0,         # CFR < 90% = SERVICE_BREACH
    "otif_service": 88.0,        # OTIF < 88% = SERVICE_BREACH
}


def generate_alert_id() -> str:
    return f"ALT-{uuid.uuid4().hex[:8].upper()}"


def evaluate_doc_alerts(compliance: dict) -> list:
    """Check Days of Cover for CRITICAL_OOS (DOC < 7 days)."""
    alerts = []
    # Currently DOC evaluation will be enhanced when inventory data is integrated
    return alerts


def evaluate_pes_alerts(compliance: dict) -> list:
    """Check PES scores for AUDIT_FAILURE (PES < 60%)."""
    alerts = []
    accounts = compliance.get("accounts", [])

    for account in accounts:
        pes = account.get("account_pes_percent", 0)
        if pes < THRESHOLDS["pes_audit"]:
            alerts.append({
                "alert_id": generate_alert_id(),
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "severity": "CRITICAL" if pes < 50 else "WARNING",
                "alert_type": "AUDIT_FAILURE",
                "account_id": account.get("account_id"),
                "account_name": account.get("account_name"),
                "metric_name": "PES",
                "current_value": pes,
                "threshold": THRESHOLDS["pes_audit"],
                "gap": THRESHOLDS["pes_audit"] - pes,
                "message": f"{account.get('account_name')} PES score {pes}% below audit floor ({THRESHOLDS['pes_audit']}%)",
                "recommendation": "Schedule field visit; verify FSDU and OSA compliance in-store",
                "action_url": "#tab-stores"
            })

    return alerts


def evaluate_fillrate_alerts(fillrate: dict) -> list:
    """Check CFR/OTIF for SERVICE_BREACH."""
    alerts = []
    accounts = fillrate.get("accounts", [])

    for account in accounts:
        cfr = account.get("cfr_percent", 100)
        otif = account.get("otif_percent", 100)

        if cfr < THRESHOLDS["cfr_service"]:
            alerts.append({
                "alert_id": generate_alert_id(),
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "severity": "CRITICAL" if cfr < 85 else "WARNING",
                "alert_type": "SERVICE_BREACH",
                "account_id": account.get("account_id"),
                "account_name": account.get("account_name"),
                "metric_name": "CFR",
                "current_value": cfr,
                "threshold": THRESHOLDS["cfr_service"],
                "gap": THRESHOLDS["cfr_service"] - cfr,
                "message": f"{account.get('account_name')} CFR {cfr}% below service target ({THRESHOLDS['cfr_service']}%)",
                "recommendation": "Review SKU mix with 3PL; validate warehouse allocation",
                "action_url": "#tab-inventory"
            })

        if otif < THRESHOLDS["otif_service"]:
            alerts.append({
                "alert_id": generate_alert_id(),
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "severity": "CRITICAL" if otif < 85 else "WARNING",
                "alert_type": "SERVICE_BREACH",
                "account_id": account.get("account_id"),
                "account_name": account.get("account_name"),
                "metric_name": "OTIF",
                "current_value": otif,
                "threshold": THRESHOLDS["otif_service"],
                "gap": THRESHOLDS["otif_service"] - otif,
                "message": f"{account.get('account_name')} OTIF {otif}% below service target ({THRESHOLDS['otif_service']}%)",
                "recommendation": "Analyze demand forecasting; reduce replenishment lead time",
                "action_url": "#tab-inventory"
            })

    return alerts


def evaluate_alerts(compliance_path: str = "dashboard/compliance_metrics.json") -> list:
    """Main evaluation: load compliance data and generate all active alerts."""
    alerts = []

    try:
        with open(compliance_path, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"[!] Warning: {compliance_path} not found; no alerts generated")
        return alerts

    compliance = data.get("compliance", {})
    fillrate = data.get("inventory_fillrate", {})

    # Evaluate all alert types
    alerts.extend(evaluate_doc_alerts(compliance))
    alerts.extend(evaluate_pes_alerts(compliance))
    alerts.extend(evaluate_fillrate_alerts(fillrate))

    return alerts


def write_alerts_feed(alerts: list, output_path: str = "dashboard/alerts_feed.json") -> None:
    """Write active alerts to sidecar JSON for dashboard consumption."""
    critical = [a for a in alerts if a["severity"] == "CRITICAL"]
    warning = [a for a in alerts if a["severity"] == "WARNING"]

    feed = {
        "metadata": {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "total_alerts": len(alerts),
            "critical_count": len(critical),
            "warning_count": len(warning)
        },
        "alerts": alerts
    }

    with open(output_path, 'w') as f:
        json.dump(feed, f, indent=2)

    print(f"\n{'='*60}")
    print("Sprint 9 Phase 1: Alert Evaluation Complete")
    print(f"{'='*60}")
    print(f"✓ Total alerts: {len(alerts)}")
    print(f"✓ Critical: {len(critical)}")
    print(f"✓ Warning: {len(warning)}")
    print(f"✓ Output: {output_path}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Sprint 9: Alert Rule Evaluator")
    parser.add_argument("--compliance", default="dashboard/compliance_metrics.json")
    parser.add_argument("--output", default="dashboard/alerts_feed.json")
    args = parser.parse_args()

    alerts = evaluate_alerts(args.compliance)
    write_alerts_feed(alerts, args.output)
