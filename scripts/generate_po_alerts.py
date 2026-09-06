#!/usr/bin/env python3
"""
Phase 5: PO SLA Risk Alert Digest Generator

Generates operational PO tracking digest with:
  • Open orders >5 days (breach risk)
  • DC fill rate performance vs. target
  • Forecast accuracy (WMAPE) trending
  • Zone-wise supply chain SLA status
  • Actionable alerts for North & South-2 zones

Output: po_sla_alerts.json (daily operational digest for steering committee)
"""
import json
from pathlib import Path
from datetime import datetime

def generate_po_alerts():
    """Generate PO SLA risk alert digest"""
    output_path = Path("dashboard/po_sla_alerts.json")

    # Zone-wise PO tracking (simulated from operational data)
    zones_po_data = [
        {
            "zone_name": "West",
            "open_pos": 12,
            "breach_risk_count": 1,
            "dc_fill_rate": 92.1,
            "dc_fill_target": 95.0,
            "dc_name": "Bhiwandi/Thane",
            "transit_time_hours": 18,
            "status": "monitor",
            "priority": "yellow",
            "actionable_items": [
                "DMart appointment slot cycle: 36h (target: <24h)",
                "Inspect 1 open order: SKU-MSV-0847 (Serums) — delayed since 2026-08-22"
            ]
        },
        {
            "zone_name": "South-1",
            "open_pos": 8,
            "breach_risk_count": 0,
            "dc_fill_rate": 94.5,
            "dc_fill_target": 95.0,
            "dc_name": "Bangalore/Hosur",
            "transit_time_hours": 24,
            "status": "on_track",
            "priority": "green",
            "actionable_items": [
                "Maintaining 94.5% fill rate (within 0.5% of target)",
                "Apollo Pharmacy offtake continues strong at 1.18x primary ratio"
            ]
        },
        {
            "zone_name": "North",
            "open_pos": 10,
            "breach_risk_count": 1,
            "dc_fill_rate": 88.9,
            "dc_fill_target": 95.0,
            "dc_name": "Faridabad",
            "transit_time_hours": 22,
            "status": "escalate",
            "priority": "red",
            "actionable_items": [
                "6.1% gap vs. target: Faridabad DC cycle time 48h (need <36h)",
                "Escalate 1 order: SKU-MAM-0612 (Cleansers) — breach since 2026-08-20",
                "Tier-2 store prep pipeline: 8 pending orders for new DMart UP expansion"
            ]
        },
        {
            "zone_name": "South-2",
            "open_pos": 7,
            "breach_risk_count": 1,
            "dc_fill_rate": 86.3,
            "dc_fill_target": 95.0,
            "dc_name": "Hyderabad",
            "transit_time_hours": 26,
            "status": "escalate",
            "priority": "red",
            "actionable_items": [
                "8.7% gap vs. target: Hyderabad DC inefficiency (appointment slot contention)",
                "Escalate 1 order: SKU-BLNT-0234 (Haircare) — delayed since 2026-08-19",
                "Action: Hire temporary slot coordinator to reduce cycle from 60h to 36h"
            ]
        },
        {
            "zone_name": "East",
            "open_pos": 4,
            "breach_risk_count": 0,
            "dc_fill_rate": 91.2,
            "dc_fill_target": 95.0,
            "dc_name": "Kolkata Hub",
            "transit_time_hours": 32,
            "status": "on_track",
            "priority": "green",
            "actionable_items": [
                "Within 3.8% of target; festive pipeline seeding on track for Durga Puja",
                "Early August dispatches locked: 4-day transit buffer active"
            ]
        },
        {
            "zone_name": "Central",
            "open_pos": 3,
            "breach_risk_count": 0,
            "dc_fill_rate": 89.7,
            "dc_fill_target": 95.0,
            "dc_name": "Nagpur Hub",
            "transit_time_hours": 28,
            "status": "on_track",
            "priority": "green",
            "actionable_items": [
                "5.3% gap manageable; high-margin growth on track",
                "Standalone supermarket offtake strong with minimal trade spend"
            ]
        },
        {
            "zone_name": "Quick-Commerce & Institutional",
            "open_pos": 6,
            "breach_risk_count": 0,
            "dc_fill_rate": 98.0,
            "dc_fill_target": 97.0,
            "dc_name": "National Network",
            "transit_time_hours": 12,
            "status": "optimal",
            "priority": "green",
            "actionable_items": [
                "Exceeds target by 1.0%; 18x inventory turns maintained",
                "98%+ OSA sustained on 30 hero SKUs across dark stores"
            ]
        }
    ]

    # Forecast accuracy trending
    forecast_accuracy = {
        "current_month": {
            "month": "July 2026",
            "wmape": 12.4,
            "wmape_target": 15.0,
            "status": "on_track",
            "improvement_vs_baseline": "32% better than FY26 baseline (18.2%)"
        },
        "next_month_target": {
            "month": "August 2026",
            "wmape_target": 10.0,
            "priority_challenge": "Festival pre-stocking accuracy (high variance)",
            "mitigation": "Daily POS-linked replenishment (QC hub model at 98% fill)"
        },
        "rolling_90day": {
            "wmape_avg": 13.8,
            "best_week": "Aug 1–7 (WMAPE: 9.2%)",
            "worst_week": "Jul 22–28 (WMAPE: 16.1%)"
        }
    }

    # Strategic alerts
    strategic_alerts = [
        {
            "type": "operational",
            "priority": "high",
            "title": "North & South-2 DC Cycle Time Reduction",
            "description": "Both zones running 48–60h appointment cycles vs. <36h target. Escalate to DC operations to hire temp slot coordinators.",
            "deadline": "2026-08-31",
            "owner": "Zone Commercial Lead"
        },
        {
            "type": "supply_chain",
            "priority": "high",
            "title": "Pre-Diwali Inventory Buffer Build",
            "description": "Initiate 8–10 days safety stock accumulation across all DCs starting Sept 1 (EOD deadline: Sept 15).",
            "deadline": "2026-09-01",
            "owner": "Supply Chain Manager"
        },
        {
            "type": "forecast",
            "priority": "medium",
            "title": "Festival Forecast Bias Mitigation",
            "description": "Implement daily POS-linked replenishment for QC hub model to reduce WMAPE from 12.4% to <10%.",
            "deadline": "2026-08-30",
            "owner": "Demand Planning Lead"
        },
        {
            "type": "talent",
            "priority": "medium",
            "title": "BA Retention Bonus Release",
            "description": "Release ₹85L bonus pool for Q3–Q4 BA retention (high turnover risk in North zone).",
            "deadline": "2026-08-28",
            "owner": "HR / Regional MD"
        }
    ]

    # Compile digest
    digest = {
        "generated_at": datetime.now().isoformat(),
        "report_date": "2026-08-26",
        "report_title": "PO SLA Risk Alert Digest — July 2026 Operational Review",
        "executive_summary": {
            "total_open_pos": sum(z["open_pos"] for z in zones_po_data),
            "total_breach_risk": sum(z["breach_risk_count"] for z in zones_po_data),
            "zones_on_track": sum(1 for z in zones_po_data if z["status"] == "on_track"),
            "zones_requiring_action": sum(1 for z in zones_po_data if z["status"] in ["monitor", "escalate"]),
            "overall_status": "requires_action"
        },
        "zones_po_tracking": zones_po_data,
        "forecast_accuracy": forecast_accuracy,
        "strategic_alerts": strategic_alerts,
        "measurement_cadence": {
            "weekly": "Primary + Secondary Tracker (NSV, Offtake, POS)",
            "bi_weekly": "Account Scorecards (DMart, Reliance, Apollo, Spencer's)",
            "monthly": "Commercial Steering Calls (Zone Commercial leads + Regional MDs)"
        }
    }

    # Write to JSON
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(digest, indent=2))
    print(f"✅ PO SLA alerts generated: {output_path}")
    print(f"📊 Zones tracked: {len(zones_po_data)}")
    print(f"⚠️  Breach risk alerts: {digest['executive_summary']['total_breach_risk']}")
    print(f"🔴 Zones requiring action: {digest['executive_summary']['zones_requiring_action']}")

    return output_path

if __name__ == "__main__":
    generate_po_alerts()
