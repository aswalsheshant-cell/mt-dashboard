# Release Gate Audit

**Frozen:** 2026-08-07  
**Branch:** `claude/primary-pipeline-allocation-fy27-l9bdf6`  
**Commit:** `91b66c3`  
**Gate implementation:** `scripts/release_gate.py`  
**Gate integration:** `scripts/build_dashboard_data.py` (safe-write pipeline) + `.github/workflows/qc.yml`  

---

## Safe-Write Semantics

The Release Gate is integrated into the `data.js` write path:

```
tempfile.mkstemp() → gate_pass() → [PASS] shutil.move() → production data.js
                                  → [FAIL] temp deleted, production untouched
```

If any mandatory gate fails, `data.js` is never replaced. Production data is always the last gate-passing build.

---

## Gate Inventory (All 10 Gates)

### G1 — Raw Data Schema Validation

| Attribute | Value |
|-----------|-------|
| **Mandatory** | Yes |
| **Threshold** | Required columns: `Chain`, `NSV`, `MRP`, `Qty` in primary DataFrame |
| **Source** | Primary/Offtake DataFrames passed to `gate_pass()` |
| **Owner** | Analytics Engineering |
| **Behavior on failure** | Blocks `data.js` publication |
| **Approval status** | LOCKED — schema is engineering contract |
| **Implementation note** | If DataFrames are `None` (no data provided), gate passes (skip behavior). This is correct for partial-refresh modes where not all data is re-loaded. |

---

### G2 — Month/FY Validation

| Attribute | Value |
|-----------|-------|
| **Mandatory** | Yes |
| **Threshold** | All month-column labels must map to a valid FY tag via `fy_tag_from_label()` |
| **Source** | `build_dashboard_data.fy_tag_from_label()` |
| **Owner** | Analytics Engineering |
| **Behavior on failure** | Blocks `data.js` publication |
| **Approval status** | LOCKED — THE ONE FY RULE (BL-01) |
| **Implementation note** | Gate imports `fy_tag_from_label` from `build_dashboard_data` at runtime — tight coupling. If the import fails, gate G2 itself fails. |

---

### G3 — Primary Reconciliation (Allocation Variance)

| Attribute | Value |
|-----------|-------|
| **Mandatory** | Yes |
| **Threshold** | Max month-level variance ≤ `reconciliation_variance_tolerance_pct` (default: **0.01%**) |
| **Source** | `allocation_reconciliation` dict from `build_dashboard_data.py` |
| **Owner** | Analytics Engineering (threshold) — Finance approval not yet obtained |
| **Behavior on failure** | Blocks `data.js` publication |
| **Approval status** | **POLICY APPROVAL REQUIRED** — 0.01% tolerance is an engineering default, not a formally Finance-approved threshold |
| **Implementation note** | If `allocation_reconciliation` is `None`, gate passes (skip). This is acceptable for `--offtake-patch` mode which doesn't recompute the allocation block. For `--primary-only` and full rebuild, reconciliation dict must be provided. |

---

### G4 — Allocation Fractions Sum = 1

| Attribute | Value |
|-----------|-------|
| **Mandatory** | No (advisory) |
| **Threshold** | Per-Chain×Month allocation fractions must sum to 1.0 |
| **Source** | Primary DataFrame allocation columns |
| **Owner** | Analytics Engineering |
| **Behavior on failure** | Warning only — does NOT block `data.js` |
| **Approval status** | **POLICY APPROVAL REQUIRED** — advisory classification should be reviewed; this is a fundamental allocation identity (per BL-02) |
| **Implementation note** | Gate G4 currently only checks that allocation columns exist and row count > 0 — it does NOT actually sum fractions per group. This is a known implementation gap: the gate structure is present but the validation is shallow. |

---

### G5 — Allocation Coverage (NSV %)

| Attribute | Value |
|-----------|-------|
| **Mandatory** | No (advisory) — despite covering a material NSV floor |
| **Threshold** | Allocated NSV ≥ `allocation_coverage_min_pct`% of total NSV (default: **95%**) |
| **Source** | Primary DataFrame NSV by chain |
| **Owner** | Analytics Engineering (threshold) — Finance approval not yet obtained |
| **Behavior on failure** | Warning only — does NOT block `data.js` |
| **Approval status** | **POLICY APPROVAL REQUIRED** — (a) 95% threshold is undocumented; (b) advisory classification is inconsistent with the business materiality of this check |
| **Implementation note** | Gate G5 implementation is shallow: it sets `coverage_pct = 100.0` when `total_nsv > 0`, which means this check effectively always passes when data is present. The actual per-chain allocation tracking is not wired into the gate input. |

---

### G6 — Unmapped Value (NSV %)

| Attribute | Value |
|-----------|-------|
| **Mandatory** | Yes |
| **Threshold** | Unmapped NSV ≤ `unmapped_nsv_tolerance_pct`% of total NSV (default: **2%**) |
| **Source** | Primary DataFrame — rows where `Chain` contains "Unmapped" |
| **Owner** | Analytics Engineering (threshold) — Finance approval not yet obtained |
| **Behavior on failure** | Blocks `data.js` publication |
| **Approval status** | **POLICY APPROVAL REQUIRED** — 2% tolerance is an engineering default, not formally Finance-approved |
| **Implementation note** | The unmapped chain detection uses a regex pattern (`Unmapped|unmapped|_`) which may not catch all unmapped patterns if the naming convention changes. |

---

### G7 — Reliance BC Double-Count Cross-Check

| Attribute | Value |
|-----------|-------|
| **Mandatory** | No (advisory) |
| **Threshold** | BC total NSV ≥ 0 (sanity check only) |
| **Source** | Reliance BC isolation DataFrame |
| **Owner** | Analytics Engineering |
| **Behavior on failure** | Warning only — does NOT block `data.js` |
| **Approval status** | ACCEPTABLE — advisory classification is correct; BC isolation is an engineering contract (BL-07) |
| **Implementation note** | Gate G7 is intentionally shallow (non-negative total). A deeper cross-check would verify BC NSV isolation from offtake totals — not currently implemented but the risk is low given the separate data loading path. |

---

### G8 — TOT% Fallback Coverage

| Attribute | Value |
|-----------|-------|
| **Mandatory** | No (advisory) |
| **Threshold** | GST-fallback tier usage ≤ `tot_fallback_max_pct`% of rows (default: **30%**) |
| **Source** | `tot_data` dict from `build_dashboard_data.py` (`tot_block()`) |
| **Owner** | Analytics Engineering (threshold) — Finance approval not yet obtained |
| **Behavior on failure** | Warning only — does NOT block `data.js` |
| **Approval status** | **POLICY APPROVAL REQUIRED** — 30% threshold source undocumented; advisory vs mandatory classification unreviewed |
| **Implementation note** | `tot_data` is only populated during `--primary-only` or full rebuild. Advisory classification is reasonable given TOT% is a derived metric with multiple valid sourcing tiers. |

---

### G9 — CM2% Expense Matching

| Attribute | Value |
|-----------|-------|
| **Mandatory** | No (advisory) |
| **Threshold** | Expense match coverage ≥ `cm2_expense_match_min_pct`% of NSV (default: **80%**) |
| **Source** | `cm2_data` dict from `build_dashboard_data.py` (`cm2_block()`) |
| **Owner** | Analytics Engineering (threshold) — Finance approval not yet obtained |
| **Behavior on failure** | Warning only — does NOT block `data.js` |
| **Approval status** | **POLICY APPROVAL REQUIRED** — 80% threshold source undocumented |
| **Implementation note** | Advisory classification is appropriate during the current phase when expense input data may be partial. Should be elevated to mandatory when `PL_Expense_Input.csv` is considered complete. |

---

### G10 — Finance-Approved Business Rules Status

| Attribute | Value |
|-----------|-------|
| **Mandatory** | Yes |
| **Threshold** | `negative_frac_treatment_status` ∈ {`APPROVED`, `PROVISIONAL`}; `jun26_allocation_status` ∈ {`APPROVED`, `PROVISIONAL`} |
| **Source** | `config` dict — mirrors `Finance_Approval_Decision_Log.md` |
| **Owner** | Finance (decisions) + Analytics Engineering (config maintenance) |
| **Behavior on failure** | Blocks `data.js` publication |
| **Approval status** | **CRITICAL GAP** — see below |
| **Implementation note** | Gate G10 passes if both statuses are `APPROVED` OR `PROVISIONAL`. Both statuses being `PROVISIONAL` will still pass the gate. |

**CRITICAL GAP in G10:**

The `_default_config()` in `release_gate.py` sets:
```python
"negative_frac_treatment_status": "APPROVED",   # ← Gate PASSES
"jun26_allocation_status": "PROVISIONAL",        # ← Gate PASSES
```

But `Finance_Approval_Decision_Log.md` (2026-08-06) shows:
- Decision 1 (Jun'26): **PENDING** — no Finance decision made
- Decision 2 (Neg Frac): **PENDING** — no Finance decision made

The default config of `"APPROVED"` for `negative_frac_treatment_status` will cause G10 to pass even though Finance has not approved the decision. This creates a false gate-pass condition.

**Required action:** Change default to `"PROVISIONAL"` until Finance Decision 2 is formally resolved. OR obtain Finance sign-off and document it in the Decision Log.

---

## Gate Classification Matrix

| Gate | Mandatory | Threshold Source | Threshold Documented | Implementation Depth |
|------|-----------|-----------------|---------------------|---------------------|
| G1 | ✓ | Engineering | N/A | Adequate |
| G2 | ✓ | THE ONE FY RULE | Locked | Adequate |
| G3 | ✓ | Engineering default | **NOT DOCUMENTED** | Adequate |
| G4 | Advisory | Engineering | N/A | **SHALLOW** — doesn't actually sum fractions |
| G5 | Advisory | Engineering default | **NOT DOCUMENTED** | **SHALLOW** — always passes when data present |
| G6 | ✓ | Engineering default | **NOT DOCUMENTED** | Adequate |
| G7 | Advisory | N/A (sanity only) | N/A | Adequate |
| G8 | Advisory | Engineering default | **NOT DOCUMENTED** | Adequate |
| G9 | Advisory | Engineering default | **NOT DOCUMENTED** | Adequate |
| G10 | ✓ | Finance decisions | **CONFIG GAP** | Adequate but misconfigured |

---

## Summary of Gate Issues

| Severity | Issue | Gate(s) |
|----------|-------|---------|
| **P0 — Config error** | Default `negative_frac_treatment_status = "APPROVED"` contradicts Finance log | G10 |
| **P1 — Policy approval** | Thresholds set by Engineering without documented Finance approval | G3, G5, G6, G8, G9 |
| **P1 — Shallow implementation** | G4 does not verify fraction sums; G5 always returns 100% coverage | G4, G5 |
| **P2 — Classification review** | G4 and G5 are advisory despite covering fundamental allocation identities | G4, G5 |

---

## Failure Injection Verification

Run `scripts/demo_release_gate_blocking.py` to verify each mandatory gate blocks correctly:

```bash
python scripts/demo_release_gate_blocking.py
```

The CI workflow (`.github/workflows/qc.yml`) runs this automatically on every push. All mandatory gates are verified to block when their conditions are violated.

---

## Recommended Remediation (Priority Order)

1. **Immediate (before production freeze):** Change `release_gate.py` `_default_config()` line 192 from `"APPROVED"` to `"PROVISIONAL"` for `negative_frac_treatment_status`. This correctly reflects the Finance Decision Log status.
2. **Before production deployment:** Obtain Finance sign-off on G3 (0.01%), G6 (2%), G8 (30%), G9 (80%) thresholds. Document in a `Gate_Threshold_Approval_Log.md`.
3. **Production hardening:** Elevate G4 to actually verify fraction sums per Chain×Month group. Elevate G5 to track actual chain-level allocation coverage (not just NSV > 0).
4. **Policy review:** Reassess whether G4 and G5 should remain advisory or become mandatory once G4/G5 implementations are deepened.
