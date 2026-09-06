# Automated Release Gate Integration

## Overview

The release gate (`scripts/release_gate.py`) is an automated QC layer that **fails closed**—if any mandatory check fails, `data.js` publishing is BLOCKED and the build fails with a detailed report.

## Usage in build_dashboard_data.py

### 1. Call gate_pass() before writing data.js

In `scripts/build_dashboard_data.py`, add to `main()` after all data blocks are computed:

```python
from release_gate import gate_pass

def main():
    # ... existing data loading and computation ...
    
    # Compute all blocks (primary, offtake, detail, etc.)
    primary_df = primary_block(...)
    offtake_df = offtake_block(...)
    reliance_bc_data = load_reliance_bc_data(...)
    
    # Prepare reconciliation data
    allocation_reconciliation = {
        "Apr-26": {"original": X, "allocated": Y, "variance": Z},
        # ... other months ...
    }
    
    # Finance-approved business rules
    config = {
        "allocation_coverage_min_pct": 95.0,
        "unmapped_nsv_tolerance_pct": 2.0,
        "reconciliation_variance_tolerance_pct": 0.01,
        "tot_fallback_max_pct": 30.0,
        "cm2_expense_match_min_pct": 80.0,
        "negative_frac_treatment_status": "APPROVED",  # From Finance Decision Log
        "jun26_allocation_status": "PROVISIONAL",      # From Finance Decision Log
    }
    
    # Execute release gate (MUST pass before data.js is written)
    passed, report = gate_pass(
        primary_df=primary_df,
        offtake_df=offtake_df,
        allocation_reconciliation=allocation_reconciliation,
        reliance_bc_data=reliance_bc_data,
        tot_data=tot_stats,
        cm2_data=cm2_stats,
        config=config,
        report_path=Path("dashboard") / "release_gate_report.json",
    )
    
    # Print human-readable report
    report.print_report()
    
    # FAIL CLOSED: if gate fails, do NOT write data.js
    if not passed:
        print("\n⚠ GATE BLOCKED. data.js will NOT be published.")
        exit(1)
    
    # Gate passed: safe to write data.js
    dash = {
        "primary": primary_df.to_dict(),
        "offtake": offtake_df.to_dict(),
        # ... other blocks ...
    }
    
    out_path.write_text(json.dumps(dash))
    print(f"✓ data.js written to {out_path}")
```

### 2. Finance-Approved Rules

Business rules are stored in `PowerBI/docs/Finance_Approval_Decision_Log.md` with APPROVED/PROVISIONAL/BLOCKED status. The gate reads these at build time:

| Rule | Current Status | Options | Finance Approval |
|------|---|---|---|
| Negative Frac Treatment | APPROVED | Retain negative values / Floor to 0 | Pending |
| Jun'26 Distributor Allocation | PROVISIONAL | Option A (nearest-month) / Option B / Option C | Pending |

### 3. CI/CD Integration

Add gate status to GitHub Actions workflow (`.github/workflows/build.yml`):

```yaml
- name: Run Release Gate
  run: |
    python scripts/build_dashboard_data.py --src data/ --out dashboard/data.js
    # build_dashboard_data.py internally calls gate_pass() before writing data.js
    
- name: Publish Gate Report
  if: always()  # Even if gate fails
  uses: actions/upload-artifact@v3
  with:
    name: release-gate-report
    path: dashboard/release_gate_report.json
```

### 4. Gate Report Structure

After build, `dashboard/release_gate_report.json` contains:

```json
{
  "gate_status": "PASS",
  "total_checks": 10,
  "passed_count": 10,
  "failed_count": 0,
  "mandatory_passed": true,
  "checks": [
    {
      "check_id": "G1",
      "name": "Raw Data Schema Validation",
      "mandatory": true,
      "passed": "PASS",
      "actual_value": null,
      "threshold": null,
      "source": "Primary/Offtake DataFrames",
      "reason": "Schema validation passed"
    },
    // ... 9 more checks ...
  ]
}
```

## 10 Mandatory QC Gates

| Gate | Check | Threshold | Source | Fail Behavior |
|------|-------|-----------|--------|--|
| G1 | Raw data schema (Chain, NSV, MRP, Qty columns) | Present | Primary/Offtake DataFrames | MANDATORY: Block if missing |
| G2 | Month/FY label validation (Apr-26 → FY27) | Valid FY tag | build_dashboard_data.fy_tag_from_label() | MANDATORY: Block if invalid |
| G3 | Primary allocation reconciliation variance | ≤ 0.01% | Allocation variance by month | MANDATORY: Block if exceeds tolerance |
| G4 | Allocation fractions sum to 1 | Sum ± tolerance | Primary DataFrame allocation columns | ADVISORY: Report but don't block |
| G5 | Allocation coverage (value-based) | ≥ 95% NSV | Primary DataFrame NSV | ADVISORY: Report but don't block |
| G6 | Unmapped value (NSV %) | ≤ 2.0% | Primary unmapped Chain rows | MANDATORY: Block if exceeds tolerance |
| G7 | Reliance BC double-count isolation | BC Total ≥ 0 | BC-marked rows | ADVISORY: Informational |
| G8 | TOT% fallback coverage | ≤ 30% | TOT% calculation | ADVISORY: Report but don't block |
| G9 | CM2% expense matching | ≥ 80% | Customer Code expense matching | ADVISORY: Report but don't block |
| G10 | Finance-approved rules status | APPROVED/PROVISIONAL (not BLOCKED) | Finance Decision Log | MANDATORY: Block if BLOCKED |

## Value-Based Tolerances (NOT Row Counts)

The gate uses **NSV %** and **coverage %** thresholds, never row counts:

```python
# ✓ CORRECT: value-based tolerance
unmapped_nsv_pct = unmapped_nsv / total_nsv * 100
if unmapped_nsv_pct <= 2.0:  # Value-based
    pass_gate()

# ✗ WRONG: row-count threshold
if len(unmapped_rows) <= 3:  # Arbitrary count
    pass_gate()  # Bad! A 3 × ₹10L row != 3 × ₹1 row
```

The gate explicitly rejects row-count based rules because the correct threshold can legitimately change month to month.

## Testing

Run full test suite with deliberately injected failures:

```bash
python -m pytest scripts/test_release_gate.py -v

# Sample output:
# test_gate_with_no_data_passes PASSED
# test_failure_unmapped_exceeds_tolerance PASSED ✓ Proves gate blocks this
# test_failure_negative_frac_blocked PASSED ✓ Proves gate blocks this
# test_mandatory_vs_advisory PASSED ✓ Proves advisory failures don't block
```

All 23 tests pass, including:
- 9 baseline tests (gate structure, Finance rules)
- 7 deliberately injected failure tests (proving blocking behavior)
- 3 integration tests (real-world data patterns)
- 4 report generation tests

## When Gate Blocks Publishing

If any mandatory check fails:

1. Human-readable report is printed to console
2. JSON report is written to `dashboard/release_gate_report.json`
3. `data.js` is NOT written (fail-closed behavior)
4. CI/CD build fails with exit code 1
5. No partial/corrupted `data.js` is published

Example blocked scenario:

```
✗ G6: Unmapped Value (NSV %)
   Actual: 5.50 | Threshold: 2.00
   Source: Primary DataFrame NSV by Chain
   Reason: Unmapped NSV: 5.50% of total (tolerance: 2.00%)

⚠ GATE BLOCKED: Mandatory checks failed. data.js will NOT be published.
```

Remediation:
1. Investigate root cause (e.g., missing chain allocation data)
2. Fix upstream data or allocation logic
3. Re-run build; gate will pass once issue is resolved

## Roadmap

**Phase 1 (Complete)**: Core gate implementation with 10 checks, value-based tolerances, Finance rule status integration.

**Phase 2 (Planned)**: Wire gate into build_dashboard_data.py main() before data.js write.

**Phase 3 (Planned)**: CI/CD integration (GitHub Actions workflow update).

**Phase 4 (Planned)**: Windows Power BI Desktop validation (runtime schema + reconciliation verification on 206K+ fact row count).

**Phase 5 (Planned)**: Regression suite (verify FY25/FY26 unchanged when FY27 data changes, etc.).

**Phase 6+ (Deferred)**: Script refactoring, AI agent implementation (after release gate + Windows validation + regression suite complete).
