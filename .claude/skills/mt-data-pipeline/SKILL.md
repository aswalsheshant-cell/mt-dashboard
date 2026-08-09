---
name: mt-data-pipeline
description: |
  Multi-source data conformance, deduplication, and mart-layer architecture patterns for Modern
  Trade analytics pipelines. Use when user asks to "build a data pipeline", "conform sales sources",
  "dedup distributor data", "merge primary and offtake", "build INT layer", "staging to mart",
  "data freshness check", "orphan record check", "missing dim join", "conformed sales view",
  "how to union multiple sources", "distribution status classification", "coverage conformed",
  "mart controls", "data quality check SQL", "schema mapping", "grain declaration",
  "multi-source sales", "pipeline architecture", "dbt-style SQL".
  Do NOT use for single KPI queries (→ mt-sql-analytics) or Python scripts (→ mt-python-pipeline).
---

# MT Data Pipeline Architecture

Build rigorous multi-source data pipelines using a three-layer architecture that separates
raw ingestion from business logic and reporting — so each layer can be validated independently.

---

## Three-Layer Architecture (Mandatory)

```
Layer 1 — STAGING (stg.*)
  Raw source data landed with minimal transformation.
  Rules: rename columns to snake_case, cast types, add ingestion metadata (load_id, ingested_at).
  Never: apply business logic, join to dims, or filter records.

Layer 2 — INTERMEDIATE (int.*)
  Business logic lives here: dedup, conform, classify, enrich.
  Rules: one CTE per logical step; declare grain as comment before every view.
  Never: depend on mart.* (one-way dependency only: stg → int → mart).

Layer 3 — MART (mart.*)
  Reporting-ready facts and dimensions; consumed by Power BI / dashboard.
  Rules: denormalized for BI; include controls views alongside fact views.
  Never: contain business logic that hasn't been validated in int.*.
```

**Grain rule (mandatory comment on every INT/MART view):**
```sql
-- Grain: 1 row per sale_date + store_code + sku + channel + sales_source
```
State the grain before the first CTE. If you can't state it, the model isn't ready.

---

## Sales Conformance Pattern

Use when unifying multiple sales sources (distributor invoices + POS/offtake):

```sql
-- int.int_sales_conformed
-- Grain: 1 row per sale_date + store_code + sku + channel + sales_source
create or replace view int.int_sales_conformed as
with distributor as (
    select
        d.sale_date,
        d.store_code,
        d.sku,
        d.channel,
        'distributor'::text as sales_source,
        d.product_name,
        d.qty::numeric       as qty,
        d.gross_sales::numeric as gross_sales,
        d.net_sales::numeric as net_sales,
        d.cogs::numeric      as cogs,
        -- dedup lineage (always carry forward)
        coalesce(d.dup_group_size, 1)::int as n_source_rows,
        d.load_id,
        d.ingested_at
    from int.int_sales_distributor_dedup d
    where d.sale_date is not null
      and d.store_code is not null
      and d.sku is not null
),

offtake as (
    select
        p.txn_date::date as sale_date,
        p.store_code,
        p.sku,
        'retail'::text as channel,
        'pos'::text    as sales_source,
        null::text     as product_name,
        sum(coalesce(p.qty, 0))::numeric        as qty,
        sum(coalesce(p.gross_amount, 0))::numeric as gross_sales,
        sum(coalesce(p.net_amount, 0))::numeric  as net_sales,
        null::numeric  as cogs,
        count(*)::int  as n_source_rows,
        max(p.load_id) as load_id,
        max(p.ingested_at) as ingested_at
    from int.int_pos_dedup p
    where p.txn_date is not null
      and p.store_code is not null
      and p.sku is not null
    group by 1,2,3,4,5,6
),

sales_union as (
    select * from distributor
    union all
    select * from offtake
),

store_ctx as (
    select
        d.store_code,
        d.chain_name,
        d.zone,
        d.format_type,
        s.account_status,
        (lower(s.account_status) = 'active') as is_active_account
    from int.int_store_latest d
    left join int.int_account_status_current s using (store_code)
)

select
    u.sale_date,
    u.store_code,
    u.sku,
    u.channel,
    u.sales_source,
    u.product_name,

    sc.chain_name,
    sc.zone,
    sc.format_type,
    sc.account_status,
    sc.is_active_account,

    -- QA flags (always include — makes debugging instant)
    (sc.store_code is null) as is_missing_store_dim,
    (u.product_name is null) as is_missing_product_label,

    u.qty,
    u.gross_sales,
    u.net_sales,
    u.cogs,

    u.n_source_rows,
    u.load_id,
    u.ingested_at
from sales_union u
left join store_ctx sc using (store_code);
```

**MT mapping for Honasa:**
- `distributor` → Primary invoiced billing (FY27 detail_meta.fyx_primary)
- `offtake` / `pos` → Store offtake from offtake patch (`--offtake-patch`)
- `chain_name` → maps to `chain_name` in BUSINESS_RULES.md Reliance exact-match rule
- `is_active_account` → use to exclude delisted stores from distribution denominator

---

## Deduplication Pattern

Use `ROW_NUMBER()` with explicit priority ordering to pick the canonical row:

```sql
-- int.int_sales_distributor_dedup
-- Grain: 1 row per sale_date + store_code + sku + channel (after dedup)
create or replace view int.int_sales_distributor_dedup as
with ranked as (
    select
        s.*,
        row_number() over (
            partition by
                s.sale_date,
                s.store_code_norm,
                s.sku_norm,
                s.channel
            order by
                (s.store_code_norm is not null) desc,  -- prefer rows with good keys
                (s.sku_norm is not null) desc,
                (s.sale_date is not null) desc,
                s.ingested_at desc nulls last,          -- prefer latest ingest
                s.drop_date desc nulls last,
                s.load_id desc nulls last
        ) as rn,
        count(*) over (
            partition by s.sale_date, s.store_code_norm, s.sku_norm, s.channel
        ) as dup_group_size
    from stg.stg_distributor_sales s
    where s.txn_id is not null
)
select * from ranked where rn = 1;
```

**Priority ordering rules for MT:**
1. Rows with non-null business keys preferred (store_code, sku)
2. Most recent `ingested_at` wins ties (not `created_at` — source timestamps can be wrong)
3. Keep `dup_group_size` for audit — if > 1, document why duplicates exist

---

## Distribution / Coverage Classification

Standardize raw status strings into 4 stable buckets:

```sql
-- int.int_coverage_conformed
-- Grain: 1 row per as_of_date + store_code + sku
case
    when distribution_status in ('carried','listed','active','in_distribution','available')
        then 'carried'
    when distribution_status in ('pending','pending_launch','onboarding')
        then 'pending'
    when distribution_status in ('not_carried','not_listed','inactive')
        then 'not_carried'
    when distribution_status in ('discontinued','retired')
        then 'discontinued'
    when distribution_status is null then null
    else distribution_status  -- preserve unknown values, don't silently bucket
end as coverage_status,

-- Boolean helpers (aggregate these instead of string comparisons)
(distribution_status in ('carried','listed','active','in_distribution','available')) as is_carried,
(distribution_status in ('pending','pending_launch','onboarding')) as is_pending,
(distribution_status in ('not_carried','not_listed','inactive')) as is_not_carried,
(distribution_status in ('discontinued','retired')) as is_discontinued
```

**MT usage:**
- `is_carried` = numerator for Numeric Distribution %
- `is_active_account` from store_ctx = denominator for Numeric Distribution %
- Numeric Distribution % = `SUM(is_carried) / COUNT(DISTINCT active stores)` per chain per month

---

## Data Freshness Control

Deploy this view alongside every mart model to monitor pipeline health:

```sql
-- mart.controls_freshness
-- Pass ≤ 2 days lag | Warning ≤ 7 days | Fail > 7 days or NULL
create or replace view mart.controls_freshness as
with models as (
    select model_schema, model_name, date_column from (values
        ('mart', 'fact_sales_distributor_daily',  'sale_date'),
        ('mart', 'fact_offtake_daily',            'offtake_date'),
        ('mart', 'fact_inventory_snapshot_daily', 'snapshot_date'),
        ('mart', 'fact_actuals_monthly',          'month_start')
    ) as v(model_schema, model_name, date_column)
),
checks as (
    select
        current_date as run_date,
        (model_schema || '.' || model_name) as model_name,
        date_column,
        -- NOTE: In production, use a helper function or dynamic SQL to handle
        -- column name variation across models (see controls_freshness.sql pattern)
        null::date as latest_date  -- replace with: max(date_column) per model
    from models
),
scored as (
    select *,
        (current_date - latest_date) as days_lag
    from checks
)
select
    run_date, model_name, latest_date, days_lag,
    case
        when latest_date is null then 'Fail'
        when days_lag <= 2 then 'Pass'
        when days_lag <= 7 then 'Warning'
        else 'Fail'
    end as status
from scored
order by model_name;
```

**MT-specific freshness targets:**
| Model | Expected Cadence | Max Acceptable Lag |
|---|---|---|
| fact_sales_distributor_daily | Daily | 2 days |
| fact_offtake_daily | Weekly/monthly | 7 days |
| fact_actuals_monthly | Monthly | First 5 business days |
| fact_inventory_snapshot_daily | Daily | 3 days |

---

## Missing Dimension Join Control

Detect orphan records (fact rows that fail to join to any dimension):

```sql
-- mart.controls_missing_dim_joins
-- PASS = 0 missing | WARN_low = < 0.1% missing | FAIL = ≥ 0.1% missing
create or replace view mart.controls_missing_dim_joins as
with sales_store as (
    select
        current_date as run_date,
        'fact_sales_distributor_daily' as model_name,
        f.sale_date as grain_date,
        'dim_store' as dim_name,
        count(*) as fact_rows,
        sum(case when ds.store_code is null then 1 else 0 end) as missing_dim_rows
    from mart.fact_sales_distributor_daily f
    left join mart.dim_store ds using (store_code)
    where f.sale_date >= current_date - 90
    group by 1,2,3,4
)
select
    run_date, model_name, grain_date, dim_name, fact_rows, missing_dim_rows,
    (missing_dim_rows::numeric / nullif(fact_rows, 0)) as missing_pct,
    case
        when fact_rows = 0 then 'WARN_no_rows'
        when missing_dim_rows = 0 then 'PASS'
        when (missing_dim_rows::numeric / fact_rows) <= 0.001 then 'WARN_low'
        else 'FAIL'
    end as status
from sales_store
order by grain_date desc;
```

---

## Schema Mapping Workflow

Before editing any SQL in a new data source integration:

```
Step 1 — Fill in schema_map.md for this source:
  □ Actual table name for each assumed table (fact_sales, fact_inventory, dim_store, dim_product)
  □ Actual column name for each assumed column
  □ Mark each mapping: ✅ confirmed / ⚠️ different meaning / ❌ missing

Step 2 — Check query-to-column dependency map:
  Which SQL files break if a field is missing?
  e.g. if `cogs_amount` is missing → fact_sales, promo_performance, price_volume_mix all break

Step 3 — Fill in business rules checklist:
  □ Returns: included in fact_sales as negative rows or separate table?
  □ Distributor → Chain → Store mapping: is it in dim_store or a separate hierarchy table?
  □ Brand Counter stores: how are they flagged? (BUSINESS_RULES.md exact-match rule applies)

Step 4 — Validate with row counts before writing any report SQL:
  SELECT 'fact_sales', COUNT(*), MIN(sale_date), MAX(sale_date) FROM fact_sales
  UNION ALL
  SELECT 'dim_store', COUNT(*), NULL, NULL FROM dim_store;
```

**MT-specific schema mapping:**

| CPG Generic Table | MT Equivalent | Grain |
|---|---|---|
| `fact_sales` | `primary_fact` (NSV by chain+brand+month) | month_label + chain_name + brand_name |
| `fact_inventory` | `offtake_fact` (DOS proxy via offtake delta) | month_label + chain_name + sku |
| `dim_store` | `chain_dim` (chain metadata, zone, format) | chain_name |
| `dim_product` | `product_dim` (brand, pack, article EAN) | sku_code / EAN |
| `dim_date` | FY-aware calendar (Apr–Mar, see FY RULE in CLAUDE.md) | calendar_date |

---

## Pipeline Build Checklist

Before shipping any new INT or MART layer:

```
□ Grain declared as comment on the view
□ All CTEs named descriptively (not cte1, cte2)
□ Dedup applied before any enrichment join
□ Missing dim flags included (is_missing_store_dim, is_missing_product_label)
□ n_source_rows / dup_group_size carried for audit trail
□ Controls freshness view covers this model
□ Controls missing dim joins view covers this model
□ Row counts checked: before vs after dedup, before vs after join
□ FY derivation from month+year — never hardcoded FY25/FY26 (CLAUDE.md FY RULE)
□ Reliance Brand Counter filter uses exact match, NOT str.contains() (BUSINESS_RULES.md)
```

---

## Integration with Other Skills

- Use **mt-sql-analytics** for KPI query patterns (window functions, ranking, period comparisons)
- Use **mt-python-pipeline** for Python-side data loading and transformation scripts
- Use **mt-data-governance** for reconciliation gates and data quality rules
- Use **mt-production-readiness** for pre-release QC on new pipeline layers
- Use **mt-error-resolution** when controls views report Fail or WARN status
