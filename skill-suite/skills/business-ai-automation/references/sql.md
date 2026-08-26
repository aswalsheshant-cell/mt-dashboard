# SQL for MT analytics

Grain, fiscal-year and denominator rules are in the parent SKILL.md. This file
covers SQL-specific style, layering and query patterns.

## Ask before writing any query

1. **What is the grain of the output?** One row per what — Month × Chain × Site × EAN?
   Never write the SELECT before answering this.
2. **What is the grain of each input?** If two inputs have different grains, aggregate
   the finer one to the coarser grain *before* joining. This is the single largest
   source of inflated MT totals.
3. **Which FY period?** Indian FY, Apr–Mar. Apr–Dec of year Y → FY(Y+1); Jan–Mar of
   year Y → FY(Y). Derive it, never hardcode a column index.
4. **Value or volume?** Offtake value, offtake units, primary NSV, primary units — say
   which in the column name.

## House style (descriptive SQL)

Adapted from the Descriptive SQL Style Guide, Mazur and Holywell conventions.

- Keywords lowercase (`select`, `from`, `left join`). Identifiers `snake_case`.
- One column per line, trailing commas, comma-first is not used here.
- **Never `select *`** outside an ad-hoc peek. Name every column.
- CTEs over nested subqueries. Every CTE gets a **descriptive** name that says what
  one row is: `offtake_by_chain_month`, not `t1` / `cte2`.
- Explicit join type always (`inner join`, `left join`) — never a bare `join`.
- Qualify every column with its table alias; aliases are meaningful (`oft`, `pri`,
  `store`), never `a`, `b`, `c`.
- End every derived measure column with its unit: `_value_inr`, `_units`, `_pct`,
  `_cr` (crore), `_lac`.
- Money in ₹: keep raw values in the base unit, convert to Cr/Lac only in the final
  presentation layer.

```sql
-- one row per fy_month x chain: offtake value and units
with offtake_by_chain_month as (
    select
        oft.fy_month,
        oft.chain_name,
        sum(oft.offtake_value_inr) as offtake_value_inr,
        sum(oft.offtake_units)     as offtake_units
    from fact_offtake as oft
    where oft.fy_tag = 'FY27'
    group by
        oft.fy_month,
        oft.chain_name
)

select
    fy_month,
    chain_name,
    offtake_value_inr,
    offtake_units,
    offtake_value_inr / nullif(offtake_units, 0) as realisation_per_unit_inr
from offtake_by_chain_month
order by
    fy_month,
    offtake_value_inr desc;
```

## Layering — staging → intermediate → mart

Never let a leadership query read a raw table directly.

| Layer | Prefix | One row is | Rules |
|---|---|---|---|
| Staging | `stg_` | one raw record, cleaned | rename, cast, trim, no joins, no business logic |
| Intermediate | `int_` | one business event at a working grain | joins, mapping, de-duplication, FY derivation |
| Mart | `mart_` / `fct_` / `dim_` | one row per reporting grain | only aggregates and named business measures |

Rule: **business rules live in exactly one layer.** If chain consolidation happens in
`int_offtake_chain_mapped`, no downstream query is allowed to re-map chains.

## The eight query patterns MT actually needs

### 1. Growth — YoY and MoM on the same grain

```sql
select
    curr.fy_month,
    curr.chain_name,
    curr.offtake_value_inr,
    prev.offtake_value_inr as offtake_value_ly_inr,
    (curr.offtake_value_inr - prev.offtake_value_inr)
        / nullif(prev.offtake_value_inr, 0) as yoy_growth_pct
from mart_offtake_chain_month as curr
left join mart_offtake_chain_month as prev
    on  curr.chain_name = prev.chain_name
    and curr.month_number = prev.month_number
    and curr.fy_tag = 'FY27'
    and prev.fy_tag = 'FY26';
```

Prefer the self-join on `month_number` over `lag()` when FYs have different month
coverage — `lag()` silently compares Apr'26 with Mar'26 if a month is missing.

### 2. Contribution and cumulative contribution (Pareto / ABC)

```sql
select
    article_name,
    offtake_value_inr,
    offtake_value_inr / sum(offtake_value_inr) over () as contribution_pct,
    sum(offtake_value_inr) over (
        order by offtake_value_inr desc
        rows between unbounded preceding and current row
    ) / sum(offtake_value_inr) over () as cumulative_contribution_pct
from mart_offtake_article
order by offtake_value_inr desc;
```

Articles up to 80 % cumulative = A class, to 95 % = B, rest = C. Use this before any
"which SKUs matter" conversation.

### 3. Rank within a group

```sql
row_number() over (partition by zone_name order by offtake_value_inr desc) as rank_in_zone
```

`row_number()` for a top-N list, `dense_rank()` when ties must share a rank,
`percent_rank()` for "this store is in the bottom 10 % of its chain".

### 4. Running total / MTD-QTD-YTD

```sql
sum(offtake_value_inr) over (
    partition by fy_tag, chain_name
    order by month_number
    rows between unbounded preceding and current row
) as ytd_offtake_value_inr
```

### 5. Primary vs offtake reconciliation at a shared grain

```sql
with primary_by_chain as (
    select fy_month, chain_name, sum(primary_nsv_inr) as primary_nsv_inr
    from mart_primary_chain_month
    group by fy_month, chain_name
),

offtake_by_chain as (
    select fy_month, chain_name, sum(offtake_value_inr) as offtake_value_inr
    from mart_offtake_chain_month
    group by fy_month, chain_name
)

select
    coalesce(pri.fy_month, oft.fy_month)     as fy_month,
    coalesce(pri.chain_name, oft.chain_name) as chain_name,
    coalesce(pri.primary_nsv_inr, 0)         as primary_nsv_inr,
    coalesce(oft.offtake_value_inr, 0)       as offtake_value_inr,
    coalesce(pri.primary_nsv_inr, 0) - coalesce(oft.offtake_value_inr, 0)
        as primary_minus_offtake_inr
from primary_by_chain as pri
full outer join offtake_by_chain as oft
    on  pri.fy_month = oft.fy_month
    and pri.chain_name = oft.chain_name;
```

`full outer join`, not `left join` — a chain present in offtake but missing in primary
is exactly the finding worth reporting. Note the two are not directly comparable in
absolute rupees (primary is NSV to the retailer, offtake is consumer MRP-side sale);
compare **trend and direction**, and state that caveat in the output.

### 6. Numeric distribution — how many stores actually sold

```sql
count(distinct case when offtake_units > 0 then site_code end) as selling_stores,
count(distinct site_code)                                      as universe_stores,
count(distinct case when offtake_units > 0 then site_code end)
    * 1.0 / nullif(count(distinct site_code), 0)               as numeric_distribution_pct
```

### 7. New / lost / retained (churn) between two periods

```sql
select
    case
        when prev.site_code is null then 'new'
        when curr.site_code is null then 'lost'
        else 'retained'
    end as store_status,
    count(*) as store_count
from curr_period as curr
full outer join prev_period as prev
    on curr.site_code = prev.site_code
group by 1;
```

### 8. Gap to target

```sql
select
    chain_name,
    target_value_inr,
    actual_value_inr,
    actual_value_inr - target_value_inr                        as gap_inr,
    actual_value_inr / nullif(target_value_inr, 0)             as achievement_pct
from mart_target_vs_actual;
```

## Safety rules that prevent wrong numbers

1. **Always `nullif(x, 0)` in a denominator.** No exceptions.
2. **Never divide two already-averaged numbers.** Compute the ratio from summed
   numerator and summed denominator.
3. **`left join` can still fan out.** If the right side is not unique on the join key,
   rows multiply. Test uniqueness first (test 1 below).
4. **`not in` breaks on NULL.** Use `not exists` or `left join ... where x is null`.
5. **Filtering the right table in a `where` clause turns a `left join` into an inner
   join.** Put the condition in the `on` clause.
6. **Union vs union all** — `union` silently de-duplicates and hides double-loads. Use
   `union all` unless de-duplication is the intent.
7. `count(*)` counts rows, `count(col)` skips NULLs — pick deliberately.

## Translating between tools

| Task | SQL | pandas | Excel |
|---|---|---|---|
| Filter | `where` | `df[df.col > 100]` | `FILTER` |
| Aggregate | `group by` | `df.groupby().agg()` | PivotTable |
| Lookup | `left join` | `df.merge(how='left')` | `XLOOKUP` |
| Rank | `row_number() over` | `df.rank(method='first')` | `RANK.EQ` |
| Dedupe | `select distinct` | `drop_duplicates()` | Remove Duplicates |
| Conditional | `case when` | `np.where` | `IF` |

When the user has an Excel formula and wants it in SQL, translate through this table,
then apply the grain check — Excel formulas frequently assume a grain the table
does not have.

