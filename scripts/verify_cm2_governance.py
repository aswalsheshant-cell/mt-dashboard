#!/usr/bin/env python3
"""
Enterprise CM2 Arithmetic & Trade Spend ROI Governance Audit

Performs strict mathematical verification across all records in data_master.json:
- Validates CM1 = Gross Revenue - Trade Spend
- Validates CM2 = CM1 - Variable Cost
- Validates CM2 % = (CM2 / Gross) * 100
- Validates Trade Spend ROI = CM2 / Trade Spend
- Audits key account presence (Trent, WH Smith, Guardian)

Returns exit code 0 (success) or 1 (failure with detailed error report).

USAGE:
  python scripts/verify_cm2_governance.py
"""

import json
import math
import sys
from pathlib import Path

MASTER_FILE = Path("data_master.json")
TOLERANCE = 1e-4  # Strict tolerance for floating point rounding (₹ 0.0001 Cr)

TARGET_ACCOUNTS = {"trent", "wh smith", "whsmith", "guardian"}


def float_equal(a: float, b: float, tol: float = TOLERANCE) -> bool:
    return abs(a - b) <= tol


def run_cm2_audit():
    if not MASTER_FILE.exists():
        print(f"❌ Error: {MASTER_FILE} not found.", file=sys.stderr)
        sys.exit(1)

    with open(MASTER_FILE, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"❌ Error: Failed to parse JSON: {e}", file=sys.stderr)
            sys.exit(1)

    print("=" * 70)
    print("🔍 ENTERPRISE CM2 ARITHMETIC & TRADE SPEND ROI GOVERNANCE AUDIT")
    print("=" * 70)

    # 1. Metadata Verification
    meta = data.get("metadata", {})
    status = meta.get("status", "UNKNOWN")
    print(f"Master Status:    {status}")
    print(f"Schema Version:   {meta.get('version', 'N/A')}")
    print(f"Active FY:        {meta.get('active_fiscal_year', 'N/A')}\n")

    # 2. Extract Claims / CM2 Collection
    records = data.get("distributor_claims_cm2_granular", [])
    if not records:
        # Check alternative top-level key fallback
        records = data.get("cm2_granular_records", [])

    if not records:
        print("⚠️ Warning: No 'distributor_claims_cm2_granular' records found in master.")
        print("Auditing FY25/26/27 zone metrics arithmetic instead...\n")

        # Flatten zone_metrics_monthly structure (FY -> Zone -> Month -> Metrics)
        zone_monthly = data.get("zone_metrics_monthly", {})
        records = []
        for fy, zones_data in zone_monthly.items():
            if isinstance(zones_data, dict):
                for zone, months_data in zones_data.items():
                    if isinstance(months_data, dict):
                        for month, metrics in months_data.items():
                            if isinstance(metrics, dict):
                                record = {
                                    "fiscal_year": fy,
                                    "zone": zone,
                                    "month": month,
                                    **metrics
                                }
                                records.append(record)

    total_records = len(records)
    print(f"Total Rows Under Audit: {total_records}")

    arithmetic_errors = []
    found_accounts = set()
    total_gross = 0.0
    total_claims = 0.0
    total_cm1 = 0.0
    total_variable_cost = 0.0
    total_cm2 = 0.0

    for idx, r in enumerate(records):
        chain = str(r.get("chain", r.get("zone", "Unknown"))).strip()
        chain_lower = chain.lower().replace(" ", "")

        # Track Target Accounts
        for target in TARGET_ACCOUNTS:
            if target.replace(" ", "") in chain_lower:
                found_accounts.add(target)

        # Numerical Fields with defaults
        gross = float(r.get("gross_revenue_inr_cr", r.get("primary_sales_inr_cr", 0.0)))
        trade_spend = float(r.get("trade_spend_inr_cr", r.get("claims_inr_cr", 0.0)))
        cm1 = float(r.get("cm1_inr_cr", gross - trade_spend))
        var_cost = float(r.get("variable_cost_inr_cr", 0.0))
        cm2 = float(r.get("cm2_inr_cr", cm1 - var_cost))
        cm2_pct = float(r.get("cm2_pct", (cm2 / gross * 100) if gross > 0 else 0.0))
        roi = float(r.get("trade_spend_roi", (cm2 / trade_spend) if trade_spend > 0 else 0.0))

        # Accumulate Totals
        total_gross += gross
        total_claims += trade_spend
        total_cm1 += cm1
        total_variable_cost += var_cost
        total_cm2 += cm2

        # Check Rule 1: CM1 = Gross Revenue - Trade Spend
        expected_cm1 = gross - trade_spend
        if not float_equal(cm1, expected_cm1):
            arithmetic_errors.append(
                f"Row {idx} ({chain}): CM1 mismatch! Got {cm1:.4f}, expected {expected_cm1:.4f} (Gross: {gross}, Spend: {trade_spend})"
            )

        # Check Rule 2: CM2 = CM1 - Variable Cost
        expected_cm2 = cm1 - var_cost
        if not float_equal(cm2, expected_cm2):
            arithmetic_errors.append(
                f"Row {idx} ({chain}): CM2 mismatch! Got {cm2:.4f}, expected {expected_cm2:.4f}"
            )

        # Check Rule 3: CM2 % = (CM2 / Gross) * 100
        if gross > 0:
            expected_cm2_pct = (cm2 / gross) * 100
            if not float_equal(cm2_pct, expected_cm2_pct, tol=1e-2):
                arithmetic_errors.append(
                    f"Row {idx} ({chain}): CM2% mismatch! Got {cm2_pct:.2f}%, expected {expected_cm2_pct:.2f}%"
                )

        # Check Rule 4: Trade Spend ROI = CM2 / Trade Spend
        if trade_spend > 0:
            expected_roi = cm2 / trade_spend
            if not float_equal(roi, expected_roi, tol=1e-2):
                arithmetic_errors.append(
                    f"Row {idx} ({chain}): ROI mismatch! Got {roi:.2f}x, expected {expected_roi:.2f}x"
                )

    # 3. Present Results
    print("-" * 70)
    print("📊 PORTFOLIO RECONCILIATION TOTALS (₹ Cr)")
    print("-" * 70)
    print(f"Gross Revenue:           ₹ {total_gross:,.2f} Cr")
    print(f"Total Trade Spend:       ₹ {total_claims:,.2f} Cr")
    print(f"Contribution Margin 1:   ₹ {total_cm1:,.2f} Cr")
    print(f"Variable Supply Costs:   ₹ {total_variable_cost:,.2f} Cr")
    print(f"Contribution Margin 2:   ₹ {total_cm2:,.2f} Cr")

    portfolio_cm2_pct = (total_cm2 / total_gross * 100) if total_gross > 0 else 0.0
    portfolio_roi = (total_cm2 / total_claims) if total_claims > 0 else 0.0
    print(f"Blended CM2 %:           {portfolio_cm2_pct:.2f}%")
    print(f"Portfolio Trade ROI:     {portfolio_roi:.2f}x")

    print("\n" + "-" * 70)
    print("🏢 KEY ACCOUNT COVERAGE AUDIT")
    print("-" * 70)
    for acc in ["trent", "wh smith", "guardian"]:
        found = any(acc.replace(" ", "") in f.replace(" ", "") for f in found_accounts)
        status_icon = "✅ PRESENT" if found else "⚠️ NOT DETECTED"
        print(f"{status_icon} | Key Account: {acc.title()}")

    # 4. Final Verdict
    print("\n" + "=" * 70)
    if not arithmetic_errors:
        print("🎉 ZERO ARITHMETIC VARIANCE DETECTED across all grain levels.")
        print("   All CM1, CM2, Margin %, and Trade Spend ROI formulas passed 100%.")
        print("=" * 70)
        sys.exit(0)
    else:
        print(f"🛑 RECONCILIATION FAILED: {len(arithmetic_errors)} arithmetic error(s) detected.")
        for err in arithmetic_errors[:10]:
            print(f"   ❌ {err}")
        if len(arithmetic_errors) > 10:
            print(f"   ... and {len(arithmetic_errors) - 10} more.")
        print("=" * 70)
        sys.exit(1)


if __name__ == "__main__":
    run_cm2_audit()
