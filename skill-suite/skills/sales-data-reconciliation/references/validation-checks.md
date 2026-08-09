# Executable validation checks

Run these before any output is marked PASS. Each check states the failure it catches
and the expected result.

## SQL

```sql
-- 1. Grain uniqueness. Expected: zero rows.
select fy_month, chain_name, site_code, ean, count(*) as row_count
from stg_offtake
group by 1, 2, 3, 4
having count(*) > 1;

-- 2. Unmapped keys. Expected: zero rows.
select distinct oft.chain_code
from stg_offtake as oft
left join dim_chain as ch on oft.chain_code = ch.chain_code
where ch.chain_code is null;

-- 3. Total preservation. Expected: the two values are equal.
select
    (select sum(offtake_value_inr) from stg_offtake)      as source_total_inr,
    (select sum(offtake_value_inr) from mart_offtake_all) as mart_total_inr;

-- 4. Period completeness. Expected: the month count matches the coverage claimed.
select fy_tag, count(distinct fy_month) as month_count
from mart_offtake_chain_month
group by fy_tag;

-- 5. Sign and range sanity. Expected: zero, or every row explained.
select count(*) as negative_rows from stg_offtake where offtake_value_inr < 0;

-- 6. Join cardinality before joining. Expected: zero rows on the "one" side.
select chain_name, count(*) as dim_rows
from dim_chain
group by chain_name
having count(*) > 1;

-- 7. Regression against the approved prior period. Expected: zero rows.
select
    curr.fy_month,
    curr.chain_name,
    curr.offtake_value_inr,
    prev.offtake_value_inr as approved_value_inr
from mart_offtake_chain_month as curr
inner join approved_snapshot as prev
    on  curr.fy_month = prev.fy_month
    and curr.chain_name = prev.chain_name
where abs(curr.offtake_value_inr - prev.offtake_value_inr) > 1;
```

Note: `not in` returns no rows when the subquery contains a NULL. Use `not exists` or a
`left join ... where key is null` instead. `union` silently de-duplicates and hides a
double load — use `union all` unless de-duplication is the intent.

## pandas

```python
def profile(df, keys):
    """The six facts required before trusting a file."""
    print(f"rows={len(df):,}  cols={df.shape[1]}")
    print(df.dtypes)
    print("nulls:\n", df.isna().sum().loc[lambda s: s > 0])
    print("duplicate key rows:", df.duplicated(subset=keys).sum())
    print("blank keys:", df[keys].isna().any(axis=1).sum())
    print(df.describe(include="number").T[["min", "max", "mean"]])
```

```python
# Grain uniqueness. Expected: empty.
dupes = df[df.duplicated(subset=GRAIN, keep=False)].sort_values(GRAIN)

# Merge safety. validate= raises on unexpected cardinality;
# indicator= exposes rows that failed to map.
merged = fact.merge(
    dim,
    on="chain_name",
    how="left",
    validate="many_to_one",
    indicator=True,
)
unmapped = merged.loc[merged["_merge"] == "left_only", "chain_name"].unique()
if len(unmapped):
    raise ValueError(f"{len(unmapped)} unmapped chains: {list(unmapped)[:20]}")

# Total preservation after aggregation. Expected: passes.
assert np.isclose(agg["offtake_value_inr"].sum(), raw["offtake_value"].sum()), \
    "aggregation lost value — check for NaN keys and dropna=False"

# Coercion accounting: count what errors="coerce" silently discarded.
bad_rows = df["offtake_value"].isna().sum()
if bad_rows:
    print(f"WARNING: {bad_rows:,} rows had unparseable offtake_value")
```

Validate **before** writing any file. A written bad file gets emailed.

## Power BI

Open the Data Quality page and confirm every card is green before publishing. The
measures are in `PowerBI/DAX/06_DataQuality_Measures.dax`. A red card is never fixed by
editing the measure — trace it back to the source file.

## Order of execution

1. Schema: files, sheets, columns, dtypes present.
2. Keys: uniqueness at the declared grain; no blank keys.
3. Mapping: coverage and conflicts.
4. Values: ranges, signs, divide-by-zero exposure.
5. Reconciliation: source total equals output total, at every level reported.
6. Completeness: every expected period present.
7. Regression: prior approved period unchanged.

Stop at the first failure that invalidates everything downstream. Running checks 5–7
against a file that fails check 2 wastes time and produces misleading evidence.
