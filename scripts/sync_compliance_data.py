#!/usr/bin/env python3
"""
SYNTHETIC DEMO Store Compliance & Inventory Fill-Rate Generator.

This produces MOCK data only -- hardcoded door/account audit numbers, not a
real audit. No script in this repo computes real PES/CFR/OTIF; there is no
registered source for one (config/data_source_registry.yml has no entry;
forecast_stock_inventory there is validation_status: MISSING for the same
reason). Output is stamped is_synthetic=true / data_status=SYNTHETIC_DEMO.

Formula (of the mock inputs only): PES = (0.40 x Price_Compliance +
0.30 x FSDU_Compliance + 0.30 x OSA_Compliance) x 100

USAGE:
  python scripts/sync_compliance_data.py [--output <path>]

  Default output: dashboard/compliance_metrics.mock_demo.json (a demo file,
  never the live dashboard path). Writing to the live path
  (dashboard/compliance_metrics.json) requires
  --i-understand-this-is-mock-data, since that file is fetched at runtime
  by dashboard/index.html and rendered on the Store Audit Scorecard /
  Supply Chain & Inventory tabs.
"""
from __future__ import annotations
import json
import argparse
from pathlib import Path
from datetime import datetime, timedelta
import sys
import os

# Add scripts directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))


def pes_score(price_pct: float, fsdu_pct: float, osa_pct: float) -> float:
    """
    Calculate Promo Execution Score (PES) as weighted average of audit dimensions.
    All inputs are 0-100 percentages.
    """
    score = (0.40 * price_pct + 0.30 * fsdu_pct + 0.30 * osa_pct)
    return round(score, 1)


def generate_mock_compliance_data() -> dict:
    """
    Generate mock compliance audit data for 12 doors across 5 accounts.
    Real scenario: PES varies by account, ranging 70–90%.
    """
    accounts_config = [
        {"id": "acc_dmart", "name": "DMart", "doors": 3},
        {"id": "acc_reliance", "name": "Reliance Retail", "doors": 3},
        {"id": "acc_apollo", "name": "Apollo Pharmacy", "doors": 2},
        {"id": "acc_wellness", "name": "Wellness Forever", "doors": 2},
        {"id": "acc_more", "name": "More Retail", "doors": 2},
    ]

    # Door-level audit results (mock)
    door_audits = [
        # DMart
        {"account": "acc_dmart", "door": "DM-001", "price": 95, "fsdu": 90, "osa": 88},
        {"account": "acc_dmart", "door": "DM-002", "price": 92, "fsdu": 85, "osa": 80},
        {"account": "acc_dmart", "door": "DM-003", "price": 88, "fsdu": 80, "osa": 75},
        # Reliance Retail
        {"account": "acc_reliance", "door": "RR-001", "price": 90, "fsdu": 88, "osa": 85},
        {"account": "acc_reliance", "door": "RR-002", "price": 85, "fsdu": 82, "osa": 80},
        {"account": "acc_reliance", "door": "RR-003", "price": 80, "fsdu": 78, "osa": 72},
        # Apollo Pharmacy
        {"account": "acc_apollo", "door": "AP-001", "price": 92, "fsdu": 88, "osa": 86},
        {"account": "acc_apollo", "door": "AP-002", "price": 88, "fsdu": 82, "osa": 78},
        # Wellness Forever
        {"account": "acc_wellness", "door": "WF-001", "price": 85, "fsdu": 80, "osa": 75},
        {"account": "acc_wellness", "door": "WF-002", "price": 80, "fsdu": 75, "osa": 70},
        # More Retail
        {"account": "acc_more", "door": "MR-001", "price": 90, "fsdu": 85, "osa": 82},
        {"account": "acc_more", "door": "MR-002", "price": 88, "fsdu": 80, "osa": 78},
    ]

    # Build door-level data
    doors_data = []
    for audit in door_audits:
        pes = pes_score(audit["price"], audit["fsdu"], audit["osa"])
        doors_data.append({
            "door_id": audit["door"],
            "door_name": f"{audit['door']} Audit",
            "account_id": audit["account"],
            "audit_date": "2026-08-20",
            "price_flag": audit["price"] >= 80,
            "fsdu_flag": audit["fsdu"] >= 75,
            "osa_flag": audit["osa"] >= 75,
            "pes_percent": pes,
            "notes": f"Price: {audit['price']}%, FSDU: {audit['fsdu']}%, OSA: {audit['osa']}%"
        })

    # Aggregate to account level
    accounts_data = []
    for acc_cfg in accounts_config:
        acc_doors = [d for d in doors_data if d["account_id"] == acc_cfg["id"]]
        if not acc_doors:
            continue

        avg_pes = round(sum(d["pes_percent"] for d in acc_doors) / len(acc_doors), 1)
        avg_price = round(sum(json.loads(d["notes"].split(": ")[1].split("%")[0]) for d in acc_doors) / len(acc_doors), 1)
        avg_fsdu = round(sum(json.loads(d["notes"].split(", FSDU: ")[1].split("%")[0]) for d in acc_doors) / len(acc_doors), 1)
        avg_osa = round(sum(json.loads(d["notes"].split(", OSA: ")[1].split("%")[0]) for d in acc_doors) / len(acc_doors), 1)

        accounts_data.append({
            "account_id": acc_cfg["id"],
            "account_name": acc_cfg["name"],
            "doors_audited": len(acc_doors),
            "account_pes_percent": avg_pes,
            "weighted_doors": len(acc_doors),
            "price_compliance": avg_price,
            "fsdu_compliance": avg_fsdu,
            "osa_compliance": avg_osa
        })

    # Macro-level PES
    macro_pes = round(sum(a["account_pes_percent"] for a in accounts_data) / len(accounts_data), 1)

    return {
        "compliance": {
            "metadata": {
                "audit_date": "2026-08-20",
                "total_doors_audited": len(doors_data),
                "macro_pes_percent": macro_pes,
                "coverage": "FY25-FY26"
            },
            "accounts": accounts_data,
            "doors": doors_data
        }
    }


def generate_mock_fillrate_data() -> dict:
    """
    Generate mock supply chain fill-rate metrics (CFR, OTIF, lost revenue).
    """
    return {
        "inventory_fillrate": {
            "metadata": {
                "period": "FY26",
                "macro_cfr_percent": 94.2,
                "macro_otif_percent": 91.8,
                "total_lost_revenue_lakh": 124.5
            },
            "accounts": [
                {
                    "account_id": "acc_dmart",
                    "account_name": "DMart",
                    "cfr_percent": 96.5,
                    "otif_percent": 94.2,
                    "lost_revenue_lakh": 28.3
                },
                {
                    "account_id": "acc_reliance",
                    "account_name": "Reliance Retail",
                    "cfr_percent": 93.8,
                    "otif_percent": 90.5,
                    "lost_revenue_lakh": 35.7
                },
                {
                    "account_id": "acc_apollo",
                    "account_name": "Apollo Pharmacy",
                    "cfr_percent": 94.1,
                    "otif_percent": 92.3,
                    "lost_revenue_lakh": 22.4
                },
                {
                    "account_id": "acc_wellness",
                    "account_name": "Wellness Forever",
                    "cfr_percent": 91.5,
                    "otif_percent": 88.9,
                    "lost_revenue_lakh": 21.8
                },
                {
                    "account_id": "acc_more",
                    "account_name": "More Retail",
                    "cfr_percent": 95.0,
                    "otif_percent": 93.1,
                    "lost_revenue_lakh": 16.3
                }
            ]
        }
    }




PRODUCTION_PATH = "dashboard/compliance_metrics.json"
DEFAULT_DEMO_PATH = "dashboard/compliance_metrics.mock_demo.json"


def generate_mock_output() -> dict:
    """
    Combine the two mock generators and stamp the result as synthetic.

    No script in this repo generates real store-audit PES/CFR/OTIF data --
    config/data_source_registry.yml has no entry for one, and
    forecast_stock_inventory is registered validation_status: MISSING for
    the same reason. This function's output must never be mistaken for a
    real audit, so every call stamps it explicitly.
    """
    compliance_data = generate_mock_compliance_data()
    fillrate_data = generate_mock_fillrate_data()
    output_data = {**compliance_data, **fillrate_data}
    for block in ("compliance", "inventory_fillrate"):
        output_data[block]["metadata"]["is_synthetic"] = True
        output_data[block]["metadata"]["data_status"] = "SYNTHETIC_DEMO"
        output_data[block]["metadata"]["source"] = (
            "scripts/sync_compliance_data.py generate_mock_*() -- hardcoded demo "
            "values, not a real store audit. See config/data_source_registry.yml."
        )
    return output_data


def sync_compliance_data(output_path: str, allow_production_overwrite: bool = False) -> None:
    """
    Write synthetic demo compliance/fill-rate data to output_path.

    Refuses to touch PRODUCTION_PATH unless allow_production_overwrite is
    explicitly set -- that file is fetched at runtime by
    dashboard/index.html and rendered as the Store Audit Scorecard / Supply
    Chain & Inventory tabs, so an accidental overwrite here would silently
    replace whatever is there today (real or not) with demo values.
    """
    if os.path.abspath(output_path) == os.path.abspath(PRODUCTION_PATH) and not allow_production_overwrite:
        print(f"[!] Refusing to write synthetic demo data to {output_path} (the live dashboard path).")
        print(f"    This generator produces MOCK data only (see generate_mock_compliance_data()'s")
        print(f"    own docstring). Pass --output <path> for a demo file, or --i-understand-this-is-mock-data")
        print(f"    to overwrite the production path anyway (not recommended).")
        raise SystemExit(1)

    print("[*] Generating SYNTHETIC DEMO compliance audit data (not a real audit)...")
    output_data = generate_mock_output()

    print(f"[*] Writing synthetic demo compliance metrics to {output_path}...")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2)

    compliance = output_data["compliance"]
    fillrate = output_data["inventory_fillrate"]

    print("\n" + "="*60)
    print("Compliance/Fill-Rate DEMO Sync Complete (SYNTHETIC_DEMO)")
    print("="*60)
    print(f"✓ Total doors audited (mock): {compliance['metadata']['total_doors_audited']}")
    print(f"✓ Macro PES score (mock): {compliance['metadata']['macro_pes_percent']}%")
    print(f"✓ Accounts (mock): {len(compliance['accounts'])}")
    print(f"✓ Macro CFR (mock): {fillrate['metadata']['macro_cfr_percent']}%")
    print(f"✓ Macro OTIF (mock): {fillrate['metadata']['macro_otif_percent']}%")
    print(f"✓ Total Lost Revenue (mock): ₹{fillrate['metadata']['total_lost_revenue_lakh']} Lakh")
    print(f"\n✓ Output file: {output_path}")
    print("  is_synthetic=true / data_status=SYNTHETIC_DEMO stamped on both blocks.")
    print("  This is demo data only -- it must never be presented as a real audit.")
    print("="*60 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate SYNTHETIC DEMO compliance & fill-rate data (mock only, not a real audit)."
    )
    parser.add_argument("--output", default=DEFAULT_DEMO_PATH,
                         help=f"Output path for the demo JSON (default: {DEFAULT_DEMO_PATH})")
    parser.add_argument("--i-understand-this-is-mock-data", dest="confirm_mock",
                         action="store_true",
                         help="Required to write to the live dashboard path "
                              f"({PRODUCTION_PATH}); has no effect for any other --output path.")
    args = parser.parse_args()

    sync_compliance_data(args.output, allow_production_overwrite=args.confirm_mock)
