#!/usr/bin/env python3
"""
extract_alert_payload.py

Parses compliance_metrics.json and generates Slack/Teams webhook payloads
for critical compliance gaps and operational alerts.
"""

import json
import os
import sys
from datetime import datetime

SIDECAR_PATH = os.path.join("dashboard", "compliance_metrics.json")

if not os.path.exists(SIDECAR_PATH):
    print("⚠ Sidecar not found. Generating minimal alert payload.", file=sys.stderr)
    sys.exit(0)

with open(SIDECAR_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

period = data.get("audit_period", "N/A")
overall_comp = data.get("overall_compliance_pct", 0)
audits = data.get("store_audits", [])

# Identify critical compliance breaches: Planogram <85% AND OSA <90%
critical_chains = [
    (a["chain_name"], a["zone"], a["audited_stores"], a["planogram_score_pct"], a["osa_pct"])
    for a in audits
    if a.get("planogram_score_pct", 100) < 85 and a.get("osa_pct", 100) < 90
]

# Identify watch-level (single-point failures)
watch_chains = [
    (a["chain_name"], a["zone"], a["planogram_score_pct"], a["osa_pct"])
    for a in audits
    if (a.get("planogram_score_pct", 100) < 85 or a.get("osa_pct", 100) < 90)
    and not (a.get("planogram_score_pct", 100) < 85 and a.get("osa_pct", 100) < 90)
]

has_critical = len(critical_chains) > 0
status_emoji = "🚨" if has_critical else "✅" if overall_comp >= 85 else "⚠️"
status_text = "CRITICAL ACTION REQUIRED" if has_critical else "HEALTHY" if overall_comp >= 85 else "WATCH"

# Build critical issues text
critical_lines = []
for chain, zone, stores, plano, osa in critical_chains:
    critical_lines.append(f"• *{chain} ({zone})*: Plano {plano}%, OSA {osa}% ({stores} stores)")
critical_text = "\n".join(critical_lines) if critical_lines else "None (all chains meeting benchmarks)"

# Build watch issues text
watch_lines = []
for chain, zone, plano, osa in watch_chains:
    if plano < 85:
        watch_lines.append(f"• *{chain} ({zone})*: Planogram {plano}% (threshold: 85%)")
    else:
        watch_lines.append(f"• *{chain} ({zone})*: OSA {osa}% (threshold: 90%)")
watch_text = "\n".join(watch_lines) if watch_lines else "None"

total_stores = sum(a.get("audited_stores", 0) for a in audits)

# ============================================================================
# SLACK PAYLOAD
# ============================================================================

slack_payload = {
    "text": f"{status_emoji} MT Compliance Alert: {period} ({overall_comp}% Overall)",
    "blocks": [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{status_emoji} Modern Trade Retail Execution Report"
            }
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Period:*\n{period}"},
                {"type": "mrkdwn", "text": f"*Overall Compliance:*\n{overall_comp}%"},
                {"type": "mrkdwn", "text": f"*Audited Doors:*\n{total_stores} stores"},
                {"type": "mrkdwn", "text": f"*Status:*\n{status_text}"}
            ]
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*🚨 Critical Compliance Gaps (Plano <85% AND OSA <90%):*\n{critical_text}"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*⚠️ Watch-Level Issues (Single-Point Failures):*\n{watch_text}"
            }
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "View Dashboard"},
                    "url": "https://mt-dashboard.vercel.app/",
                    "style": "primary"
                }
            ]
        }
    ]
}

# ============================================================================
# MICROSOFT TEAMS ADAPTIVE CARD PAYLOAD
# ============================================================================

teams_payload = {
    "type": "message",
    "attachments": [
        {
            "contentType": "application/vnd.microsoft.card.adaptive",
            "content": {
                "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                "type": "AdaptiveCard",
                "version": "1.4",
                "body": [
                    {
                        "type": "TextBlock",
                        "size": "Large",
                        "weight": "Bolder",
                        "text": f"{status_emoji} Modern Trade Retail Execution Report",
                        "color": "Attention" if has_critical else "Good" if overall_comp >= 85 else "Warning"
                    },
                    {
                        "type": "TextBlock",
                        "size": "Medium",
                        "text": f"Audit Period: {period} | Overall Compliance: {overall_comp}%",
                        "spacing": "Medium"
                    },
                    {
                        "type": "FactSet",
                        "facts": [
                            {"title": "Status", "value": status_text},
                            {"title": "Audited Doors", "value": f"{total_stores} stores"},
                            {"title": "Critical Gaps", "value": f"{len(critical_chains)} chains"},
                            {"title": "Watch Items", "value": f"{len(watch_chains)} chains"}
                        ],
                        "spacing": "Medium"
                    },
                    {
                        "type": "TextBlock",
                        "weight": "Bolder",
                        "text": "🚨 Critical Compliance Gaps",
                        "spacing": "Medium"
                    },
                    {
                        "type": "TextBlock",
                        "text": critical_text if critical_lines else "None — all chains meeting benchmarks",
                        "wrap": True
                    },
                    {
                        "type": "TextBlock",
                        "weight": "Bolder",
                        "text": "⚠️ Watch-Level Issues",
                        "spacing": "Medium"
                    },
                    {
                        "type": "TextBlock",
                        "text": watch_text if watch_lines else "None",
                        "wrap": True
                    }
                ],
                "actions": [
                    {
                        "type": "Action.OpenUrl",
                        "title": "View Dashboard",
                        "url": "https://mt-dashboard.vercel.app/"
                    }
                ]
            }
        }
    ]
}

# ============================================================================
# WRITE PAYLOADS
# ============================================================================

os.makedirs("/tmp", exist_ok=True)

with open("/tmp/slack_notification.json", "w", encoding="utf-8") as f:
    json.dump(slack_payload, f, indent=2)

with open("/tmp/teams_notification.json", "w", encoding="utf-8") as f:
    json.dump(teams_payload, f, indent=2)

print(f"Alert generated: status={status_text}, critical={len(critical_chains)}, watch={len(watch_chains)}")
print(f"Slack payload: /tmp/slack_notification.json")
print(f"Teams payload: /tmp/teams_notification.json")
