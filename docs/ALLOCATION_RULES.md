# FY27 Allocation & Target Logic

## 1. Hierarchy Allocation Pathway

Target and cost allocations must flow top-down sequentially:

```
Distributor Level
    ↓
Chain Level  (e.g. BigBasket, DMart, Reliance, Nykaa)
    ↓
Brand Level  (e.g. Mamaearth, The Derma Co, Aqualogica)
    ↓
Article / SKU Level  (EAN / Article Code)
```

No level may be skipped. Brand-level targets must always reconcile to Chain-level targets.
Chain-level targets must always reconcile to Distributor-level targets. Any unallocated residual
is a data quality error — it must be investigated and assigned, not ignored.

---

## 2. Allocation Formulas & Weights

### SKU-Level Target Allocation

When allocating chain/brand targets down to Article level, use a trailing weighted average:

```
SKU Weight = 0.6 × (3-Month Historical Share) + 0.4 × (6-Month Historical Share)
```

Where:
- **3-Month Historical Share** = SKU's NSV / Total Brand NSV, trailing 3 months
- **6-Month Historical Share** = SKU's NSV / Total Brand NSV, trailing 6 months
- Weights sum to 1.0 across all active SKUs within the brand × chain combination

```python
# Python implementation
def sku_allocation_weight(nsv_3m: float, brand_nsv_3m: float,
                           nsv_6m: float, brand_nsv_6m: float) -> float:
    share_3m = nsv_3m / brand_nsv_3m if brand_nsv_3m > 0 else 0
    share_6m = nsv_6m / brand_nsv_6m if brand_nsv_6m > 0 else 0
    return 0.6 * share_3m + 0.4 * share_6m

# Allocate brand target to SKUs
def allocate_brand_target(brand_target_l: float,
                           sku_weights: dict) -> dict:
    total_weight = sum(sku_weights.values())
    if total_weight == 0:
        raise ValueError("All SKU weights are zero — cannot allocate")
    return {
        sku: brand_target_l * (w / total_weight)
        for sku, w in sku_weights.items()
    }
```

### New Product Introduction (NPI) — SKUs with < 3 Months History

For SKUs without 3 months of historical sales:

1. Use category-level brand distribution weights across active target stores
2. Category weights = all brand NSV in the category at the same chain, trailing 6 months
3. Apply NPI weight = category-level weight × expected velocity (from launch plan)
4. Flag NPI allocations in the target file as `allocation_basis = "NPI"` (not "Historical")
5. Review NPI allocations at 90-day mark — recompute using actual sales once history exists

---

## 3. Primary vs. Offtake Reconciliation

Both Primary and Offtake allocations must run through the same monthly continuity engine:

```
Primary NSV (₹L) allocated to Chain × Brand × SKU
    must reconcile to
Offtake Value (₹L) allocated to Chain × Brand × SKU
    within DOS tolerance: (Primary − Offtake) ÷ Daily Offtake Rate ≤ 21 days
```

**Reconciliation check (monthly gate):**
```python
def primary_offtake_reconciliation(primary_nsv_l, offtake_val_l, days_in_month=30):
    if offtake_val_l <= 0:
        return None  # cannot compute DOS — flag for manual review
    daily_offtake = offtake_val_l / days_in_month
    gap_nsv = primary_nsv_l - offtake_val_l
    implied_dos = gap_nsv / daily_offtake
    status = "OK" if implied_dos <= 21 else ("WARNING" if implied_dos <= 30 else "FAIL")
    return {"gap_nsv_l": round(gap_nsv, 2),
            "implied_dos_days": round(implied_dos, 1),
            "status": status}
```

**If reconciliation fails:** block allocation release — escalate to MT Lead + Finance.

---

## 4. FY Boundary Rules

- FY27 covers Apr-26 through Mar-27 (Indian financial year)
- Targets set at beginning of FY; revised quarterly (Q1 lock = Jun, Q2 = Sep, Q3 = Dec)
- FY derivation: Apr–Dec of calendar year Y → FY(Y+1); Jan–Mar of Y → FY(Y)
- **Never hardcode FY26/FY27 offsets** — derive from month label (see CLAUDE.md: THE ONE FY RULE)

---

## 5. Unallocated Target Residual — Zero Tolerance

```
∑ Allocated SKU Targets − Total Chain Target = 0  (±0.001% tolerance)
```

Any residual > 0.001% must be:
1. Investigated within 48 hours
2. Assigned to the correct SKU / chain
3. Re-run through reconciliation gate before release

Residuals are never silently absorbed into an "Other" bucket.

---

## 6. CLAUDE.md Reference

This file is part of the Engineering Constitution:

```
docs/ENGINEERING_STANDARDS.md  → architecture and engineering laws
docs/BUSINESS_RULES.md         → primary/offtake/P&L business rules
docs/QC_FRAMEWORK.md           → 10 QC gates (includes allocation gate)
docs/ALLOCATION_RULES.md       → THIS FILE — allocation hierarchy and formulas
docs/KPI_DICTIONARY.md         → KPI definitions and DAX patterns
```

The allocation logic in `scripts/build_dashboard_data.py` must implement the rules in this file.
Any deviation requires Finance + MT Lead sign-off before code is merged.
