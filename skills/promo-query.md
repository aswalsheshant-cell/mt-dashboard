---
name: promo-query
description: "Answers promo data inquiries, filters discount rules, and explains promo schemas."
tags: [promo, data, sql]
---
# Promo Query Instructions

## Data Sources
- Primary: `data/data_master.json` → `.promo` block
- Dashboard: `dashboard/data.js` → `window.DASH.promo`
- Months available: Apr-25 through current in `promo.months_available`

## Key Fields
| Field | Location | Type | Notes |
|-------|----------|------|-------|
| `n_promos` | `promo.n_promos` | int | Total promo count across all chains |
| `avg_depth` | `promo.avg_depth` | float | Average discount depth % |
| `by_chain[].name` | `promo.by_chain` | str | Chain name (e.g. "Modern Retail") |
| `by_chain[].avg_offer_pct` | `promo.by_chain` | float | Avg offer % for that chain |
| `monthly[MONTH]` | `promo.monthly` | dict | Month-level aggregates (e.g. "Apr-25") |

## Month Label Format
Labels use `Mon-YY` format: `Apr-25`, `Dec-25`, `Jan-26`. FY derivation:
- Apr–Dec of year YY → FY(YY+1) e.g. Apr-25 → FY26
- Jan–Mar of year YY → FY(YY) e.g. Mar-26 → FY26

## Query Patterns

### List chains in promo
```python
import json
data = json.load(open('data/data_master.json'))
for chain in data['promo']['by_chain']:
    print(f"{chain['name']}: {chain['promos']} promos, {chain['avg_offer_pct']}% avg depth")
```

### Monthly trend
```python
for month, stats in data['promo']['monthly'].items():
    print(f"{month}: {stats['n_promos']} promos, {stats['chains_in_promo']} chains")
```

### Filter by FY
```python
fy26_months = [m for m in data['promo']['months_available']
               if (int(m.split('-')[1]) >= 26 and m.split('-')[0] in ['Jan','Feb','Mar'])
               or (int(m.split('-')[1]) <= 25 and m.split('-')[0] not in ['Jan','Feb','Mar'])]
```

## Validation Rules
- `avg_offer_pct` must be in range 30–60%. Flag outliers outside this range.
- `n_promos` per chain must be positive. Zero = chain not in promo this period.
- `received: true` on a chain entry means data was received; `false` means pending.

## Response Format
Always report: chain name, promo count, SKU count, avg offer %, received status.
Flag any chain where `avg_offer_pct > 50` as high-depth — requires trade spend review.
