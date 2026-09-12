#!/usr/bin/env python3
"""
Demonstration: Release gate blocks data.js publishing when mandatory checks fail.

This script shows the gate in action with deliberately injected failures,
proving the fail-closed behavior that prevents corrupt data from reaching
the dashboard.
"""
import pandas as pd
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
from release_gate import gate_pass


def demo_scenario_1_baseline_pass():
    """Scenario 1: Baseline data PASSES all mandatory checks."""
    print("\n" + "=" * 80)
    print("SCENARIO 1: BASELINE DATA (PASSES)")
    print("=" * 80)

    df = pd.DataFrame({
        'Chain': ['Apollo', 'Reliance', 'Dmart'] * 10,
        'Zone': ['East'] * 30,
        'NSV': [1000.0, 2000.0, 500.0] * 10,
        'MRP': [1500.0, 3000.0, 750.0] * 10,
        'Qty': [100, 200, 50] * 10,
    })

    config = {
        "allocation_coverage_min_pct": 95.0,
        "unmapped_nsv_tolerance_pct": 2.0,
        "reconciliation_variance_tolerance_pct": 0.01,
        "tot_fallback_max_pct": 30.0,
        "cm2_expense_match_min_pct": 80.0,
        "negative_frac_treatment_status": "APPROVED",
        "jun26_allocation_status": "PROVISIONAL",
    }

    passed, report = gate_pass(primary_df=df, config=config)
    report.print_report()

    if passed:
        print("✓ OUTCOME: data.js CAN be published\n")
    else:
        print("✗ OUTCOME: data.js CANNOT be published\n")


def demo_scenario_2_unmapped_exceeds():
    """Scenario 2: Unmapped NSV exceeds tolerance (mandatory check fails)."""
    print("\n" + "=" * 80)
    print("SCENARIO 2: UNMAPPED NSV EXCEEDS TOLERANCE (BLOCKS)")
    print("=" * 80)

    df = pd.DataFrame({
        'Chain': ['Apollo', 'Reliance', '_Unmapped'],
        'Zone': ['East', 'East', 'East'],
        'NSV': [3000.0, 2000.0, 600.0],  # 600/5600 = 10.7% > 2% tolerance
        'MRP': [4500.0, 3000.0, 900.0],
        'Qty': [300, 200, 60],
    })

    config = {
        "allocation_coverage_min_pct": 95.0,
        "unmapped_nsv_tolerance_pct": 2.0,  # 10.7% exceeds this
        "reconciliation_variance_tolerance_pct": 0.01,
        "negative_frac_treatment_status": "APPROVED",
        "jun26_allocation_status": "PROVISIONAL",
    }

    passed, report = gate_pass(primary_df=df, config=config)
    report.print_report()

    if not passed:
        print("✓ OUTCOME: data.js BLOCKED (mandatory gate failed)\n")
    else:
        print("✗ OUTCOME: Gate should have blocked this!\n")


def demo_scenario_3_reconciliation_variance():
    """Scenario 3: Allocation reconciliation variance exceeds tolerance."""
    print("\n" + "=" * 80)
    print("SCENARIO 3: RECONCILIATION VARIANCE EXCEEDS TOLERANCE (BLOCKS)")
    print("=" * 80)

    df = pd.DataFrame({
        'Chain': ['Apollo', 'Reliance'],
        'NSV': [5000.0, 5000.0],
        'MRP': [7500.0, 7500.0],
        'Qty': [500, 500],
    })

    allocation_reconciliation = {
        "Apr-26": {"original": 10000, "allocated": 10050, "variance": 0.50},  # 0.5% > 0.01%
    }

    config = {
        "reconciliation_variance_tolerance_pct": 0.01,  # 0.5% exceeds this
        "negative_frac_treatment_status": "APPROVED",
        "jun26_allocation_status": "PROVISIONAL",
    }

    passed, report = gate_pass(
        primary_df=df,
        allocation_reconciliation=allocation_reconciliation,
        config=config,
    )
    report.print_report()

    if not passed:
        print("✓ OUTCOME: data.js BLOCKED (reconciliation variance exceeded)\n")
    else:
        print("✗ OUTCOME: Gate should have blocked this!\n")


def demo_scenario_4_finance_rules_blocked():
    """Scenario 4: Finance-approved rules are BLOCKED (mandatory check fails)."""
    print("\n" + "=" * 80)
    print("SCENARIO 4: FINANCE RULES BLOCKED (BLOCKS)")
    print("=" * 80)

    df = pd.DataFrame({
        'Chain': ['Apollo', 'Reliance'],
        'NSV': [5000.0, 5000.0],
        'MRP': [7500.0, 7500.0],
        'Qty': [500, 500],
    })

    config = {
        "allocation_coverage_min_pct": 95.0,
        "unmapped_nsv_tolerance_pct": 2.0,
        "negative_frac_treatment_status": "BLOCKED",  # ✗ BLOCKED status
        "jun26_allocation_status": "APPROVED",
    }

    passed, report = gate_pass(primary_df=df, config=config)
    report.print_report()

    if not passed:
        print("✓ OUTCOME: data.js BLOCKED (Finance rule BLOCKED status)\n")
    else:
        print("✗ OUTCOME: Gate should have blocked this!\n")


def demo_scenario_5_advisory_only():
    """Scenario 5: Advisory checks fail, but all mandatory checks pass."""
    print("\n" + "=" * 80)
    print("SCENARIO 5: ADVISORY FAILURES ONLY (PASSES)")
    print("=" * 80)

    df = pd.DataFrame({
        'Chain': ['Apollo', 'Reliance', 'Dmart'],
        'NSV': [4850.0, 5000.0, 150.0],  # 1.5% unmapped < 2% tolerance
        'MRP': [7275.0, 7500.0, 225.0],
        'Qty': [485, 500, 15],
    })

    config = {
        "allocation_coverage_min_pct": 95.0,
        "unmapped_nsv_tolerance_pct": 2.0,
        "tot_fallback_max_pct": 20.0,
        "negative_frac_treatment_status": "APPROVED",
        "jun26_allocation_status": "PROVISIONAL",
    }

    tot_data = {
        "fallback_coverage_pct": 40.0,  # Exceeds 20% (advisory failure)
    }

    passed, report = gate_pass(primary_df=df, tot_data=tot_data, config=config)
    report.print_report()

    if passed:
        print("✓ OUTCOME: data.js CAN be published (advisory failures don't block)\n")
    else:
        print("✗ OUTCOME: Gate should have passed (only advisory checks failed)!\n")


if __name__ == "__main__":
    print("\n" + "#" * 80)
    print("# RELEASE GATE DEMONSTRATION")
    print("# Showing how the gate fails closed when mandatory checks fail")
    print("#" * 80)

    demo_scenario_1_baseline_pass()
    demo_scenario_2_unmapped_exceeds()
    demo_scenario_3_reconciliation_variance()
    demo_scenario_4_finance_rules_blocked()
    demo_scenario_5_advisory_only()

    print("\n" + "#" * 80)
    print("# SUMMARY")
    print("#" * 80)
    print("""
The release gate enforces these behaviors:

1. ✓ PASS: All mandatory checks pass → data.js published
2. ✗ BLOCK: Any mandatory check fails → data.js NOT published
3. ✓ PASS: Only advisory checks fail → data.js published (warnings only)

Mandatory Checks (Block if Failed):
  - G1: Raw data schema validation
  - G2: Month/FY validation
  - G3: Primary reconciliation variance (≤ 0.01%)
  - G6: Unmapped value NSV % (value-based, not row count)
  - G10: Finance-approved rules status (APPROVED/PROVISIONAL, not BLOCKED)

Advisory Checks (Report but Don't Block):
  - G4-G5: Allocation fractions and coverage
  - G7: Reliance BC double-count
  - G8: TOT% fallback coverage
  - G9: CM2% expense matching

Value-Based Tolerances (NOT Row Counts):
  - Unmapped NSV % (e.g., 2.0%)
  - Reconciliation variance % (e.g., 0.01%)
  - Allocation coverage % (e.g., 95%)
  - Fallback tier coverage % (e.g., 30%)
  - Expense matching % (e.g., 80%)

The gate fails CLOSED: when in doubt, block publishing until Finance approves.
""")
    print("#" * 80 + "\n")
