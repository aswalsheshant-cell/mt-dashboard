---
name: data-validation
description: "Guidance on interpreting validation rules, handling discrepancies, and checking data_master.json."
tags: [validation, data, schema]
---
# Data Validation Instructions

## Validation Hierarchy
1. **Schema check** — required keys exist and types are correct
2. **Range check** — numeric values within business bounds
3. **Reconciliation check** — aggregates match row-level sums
4. **Baseline check** — FY25/FY26 historical values unchanged

## Core Invariants (never skip)
- MT Universe: **426 active stores** across verified MT chains
- FY27 forecast baseline: **₹441 Cr**
- `data.js` top-level keys must include: `meta`, `primary`, `offtake`, `pnl`, `dims`, `promo`
- `dims.FY` must contain at minimum `['FY25', 'FY26']`

## data_master.json Schema
```
{
  "metadata": { version, generated_at, source, description },
  "promo": {
    "n_promos": int,
    "avg_depth": float,
    "by_chain": [{ name, kam, promos, skus, brands, avg_offer_pct, received }],
    "months_available": [str],
    "monthly": { "Mon-YY": { month, total_skus, chains_in_promo, n_promos, avg_depth } }
  },
  "trade_spend": {
    "total_allocation": int,
    "currency": "INR",
    "periods": [str],
    "by_period": { "FY25": { amount, chains, status }, ... }
  }
}
```

## Validation Steps

### 1. Load and check data.js
```python
import json, re

with open('dashboard/data.js') as f:
    content = f.read()

m = re.search(r'window\.DASH\s*=\s*(\{.*\})\s*;', content, re.DOTALL)
assert m, "Cannot extract JSON from data.js"
data = json.loads(m.group(1))

required_keys = ['meta', 'primary', 'offtake', 'pnl', 'dims', 'promo', 'forecast']
missing = [k for k in required_keys if k not in data]
assert not missing, f"Missing top-level keys: {missing}"
```

### 2. FY coverage check
```python
fiscal_years = [fy.lower() for fy in data['dims'].get('FY', [])]
assert 'fy25' in fiscal_years and 'fy26' in fiscal_years, \
    f"Missing required FY coverage. Found: {fiscal_years}"
```

### 3. Primary month coverage
```python
fy25_months = data['primary'].get('monthly_fy25', {})
fy26_months = data['primary'].get('monthly_fy26', {})
assert len(fy25_months) > 0, "FY25 primary months empty"
assert len(fy26_months) > 0, "FY26 primary months empty"
```

### 4. NaN/undefined guard
```python
import math
def has_nan(obj, path="root"):
    if isinstance(obj, float) and math.isnan(obj):
        raise ValueError(f"NaN at {path}")
    if isinstance(obj, dict):
        for k, v in obj.items():
            has_nan(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            has_nan(v, f"{path}[{i}]")

has_nan(data)  # raises if any NaN found
```

## Discrepancy Handling
- **Schema mismatch**: quarantine the bad record, log it, continue with clean data
- **Range violation**: flag for review, do NOT silently drop
- **NaN/undefined in UI**: always render `–` (em-dash), never the literal string `NaN`
- **Missing FY**: warn and continue; do not fail the pipeline for future FYs

## CI Gates (must pass before merge)
- `python -m py_compile scripts/build_dashboard_data.py` → exit 0
- `dims.FY` contains FY25 and FY26
- `primary.monthly_fy25` and `primary.monthly_fy26` non-empty
- `dashboard/data.js` starts with `window.DASH`
