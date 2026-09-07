# Distributor → Chain → Article deep dive for CM2

Working patterns for the secondary hierarchy. Every snippet below was run against
`SecondarySales_Monthly_TOT_Analysis/01_FULL_HIERARCHY_Apr_Jul_2026.csv`
(28,537 rows, ₹4,281.34 L) and reconciles to that total.

---

## 1. Load it correctly

Three things go wrong on load. This handles all three.

```python
import csv, collections

HIER = ("PowerBI/RawDataFolders/SecondarySales_Monthly_TOT_Analysis/"
        "01_FULL_HIERARCHY_Apr_Jul_2026.csv")

def load_hierarchy(path=HIER):
    """Rows with NSV in Lakh, computed from the rupee column.

    - latin-1: the file carries non-UTF8 bytes
    - sums NSV_Value (rupees); NSV_Lakh is rounded to 2dp and loses Rs 7.59 L
    - EAN carries a leading apostrophe from Excel
    """
    out = []
    with open(path, encoding="latin-1", newline="") as f:
        for r in csv.DictReader(f):
            try:
                nsv = float(r["NSV_Value"] or 0) / 1e5      # -> Rs Lakh
            except ValueError:
                continue                                     # unparsable row
            out.append({
                "month":  r["Source_Month"].strip(),
                "dist":   r["Distributor"].strip(),
                "chain":  r["Chain"].strip(),
                "brand":  r["Brand"].strip(),
                "ean":    r["EAN"].strip().lstrip("'"),
                "article": r["Article"].strip(),
                "nsv_l":  nsv,
            })
    return out

rows = load_hierarchy()
print(f"{len(rows):,} rows, Rs {sum(r['nsv_l'] for r in rows):,.2f} L")
# 28,537 rows, Rs 4,281.34 L
```

Skip the `Chain_TOT_Pct` / `Brand_TOT_Pct` columns. 93% and 95% of rows
respectively disagree with the totals in their own row. Recompute:

```python
def shares(rows, parent_keys, child_key):
    """Recomputed share of each child within its parent group. Sums to 100."""
    parent = collections.defaultdict(float)
    child  = collections.defaultdict(float)
    for r in rows:
        p = tuple(r[k] for k in parent_keys)
        parent[p] += r["nsv_l"]
        child[p + (r[child_key],)] += r["nsv_l"]
    return {k: (v / parent[k[:-1]] * 100 if parent[k[:-1]] else 0.0)
            for k, v in child.items()}

chain_share = shares(rows, ["month", "dist"], "chain")
```

Verified on Apr–Jul'26: **72 of 77** distributor-months sum to exactly 100%. The other
five sum to 0 because the distributor's whole month is ₹0.00 — the guard returns 0
rather than dividing by zero, which is correct. They are not errors, but they are worth
excluding from a share-weighted allocation:

| Distributor-month with ₹0 NSV | |
|---|---|
| R.S. TRADING CO. | 2026-04, 2026-05, 2026-06 |
| Radhika Traders | 2026-05 |
| **"Distributor"** | 2026-07 — a **header row leaked into the data**, not a real party. Filter it out. |

---

## 2. The four drill levels

```python
def rollup(rows, keys, month=None):
    agg = collections.defaultdict(float)
    for r in rows:
        if month and r["month"] != month:
            continue
        agg[tuple(r[k] for k in keys)] += r["nsv_l"]
    return dict(sorted(agg.items(), key=lambda kv: -kv[1]))

by_dist    = rollup(rows, ["dist"])                              # billing party
by_d_chain = rollup(rows, ["dist", "chain"])                     # -> customer
by_d_c_br  = rollup(rows, ["dist", "chain", "brand"])            # -> brand
by_article = rollup(rows, ["dist", "chain", "brand", "ean"])     # -> article
```

Worth asserting before attributing — a level that does not tie means the level below is
incomplete, and CM2 on it comes out understated:

```python
assert abs(sum(by_dist.values()) - sum(by_article.values())) < 0.01
```

---

## 3. CM2 at each level

```
CM2 Value = NSV - Expense
CM2 %     = CM2 Value / NSV * 100
```
Tolerances the repo QC enforces (`scripts/validate_dashboard_qc.py:158`):
value ±₹0.01 L, percent ±0.1 pp.

```python
def cm2(nsv_l, expense_l):
    """Returns (cm2_value, cm2_pct). pct is None where it is not meaningful."""
    value = nsv_l - expense_l
    if nsv_l == 0:
        return value, None          # undefined, NOT 0 and NOT 100
    if nsv_l < 0:
        return value, None          # net-credit month: percent is meaningless
    return value, value / nsv_l * 100
```

**Allocating a distributor-level claim down to article** — legitimate, but the result is
allocated rather than actual, and reads best labelled that way on the output:

```python
def allocate_expense(rows, dist_expense, month):
    """dist_expense: {distributor: Rs Lakh} for one month.
    Splits each distributor's claim to article on recomputed NSV share."""
    tot = collections.defaultdict(float)
    for r in rows:
        if r["month"] == month:
            tot[r["dist"]] += r["nsv_l"]
    out = []
    for r in rows:
        if r["month"] != month:
            continue
        d = tot[r["dist"]]
        exp = dist_expense.get(r["dist"], 0.0) * (r["nsv_l"] / d) if d else 0.0
        v, p = cm2(r["nsv_l"], exp)
        out.append({**r, "expense_l": exp, "cm2_l": v, "cm2_pct": p,
                    "expense_basis": "ALLOCATED on secondary NSV share"})
    return out
```

What keeps the number defensible:

- Name the NSV basis on every CM2 figure — secondary and primary NSV give different
  CM2 for the same expense.
- Expense stays with its own measure. A claim settled against distributor billing
  belongs on secondary NSV, not on offtake.
- Where a claim is settled at distributor level and you report at article level, the
  article CM2 is an allocation. Say so in the column header, not a footnote.

---

## 4. FY25 — what you cannot do

FY25 secondary (`data/raw_drops/Distributor_secondary_FY25_Apr24_Mar25.csv`) has
`Brand` but **no `EAN` / `Article`**. So:

| Question | FY25 | FY27 |
|---|---|---|
| CM2 by distributor | Yes | Yes |
| CM2 by chain | Yes | Yes |
| CM2 by brand | Yes | Yes |
| **CM2 by article / EAN** | **No — not in the data** | Yes |

Any FY25 article-level split is modelled. `Primary_Article_Synthesized_FY25.csv` did
exactly this with a Pareto fallback on 54,328 of 67,545 rows, so it does not stand in
for measured data.

FY25 loading gotchas:

```python
# Channel column has a TRAILING SPACE in the header
channel = r["Channel "].strip()          # 'MT' or 'EB2B'

# MT-only work needs this filter, or the number runs 7% high:
#   MT   Rs 21,723.43 L
#   EB2B Rs  1,608.93 L
#   ----------------------
#   all  Rs 23,332.36 L

# Chhattisgarh is spelled "Chattishgarh" here. Match variants, not exact equality.
CENTRAL = {"madhya pradesh", "chattishgarh", "chhattisgarh", "maharashtra-vidarbha"}
# Central = Rs 1,052.77 L (4.51%). Exact-match on the correct spelling gives
# Rs 756.15 L and raises no error.
```

---

## 5. Pre-publication checklist

- [ ] Measure named on the artifact: Primary / **Distributor Secondary** / Offtake
- [ ] NSV summed from `NSV_Value`/1e5, not `NSV_Lakh`
- [ ] Shares recomputed, not read from `*_TOT_Pct`
- [ ] Units reconciled — the file mixes rupees and lakh in one row
- [ ] Each drill level ties to its parent
- [ ] Allocated expense labelled ALLOCATED
- [ ] CM2 % suppressed where NSV ≤ 0
- [ ] Chain names via `canon_chain()`; zone re-derived from `State`
- [ ] No growth % spanning two different measures
