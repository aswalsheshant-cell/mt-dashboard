---
name: mt-sql-analytics
description: |
  SQL query design, analysis patterns, and window function logic for Modern Trade (MT) data.
  Use this skill when the user asks to write SQL for sales data, primary/offtake reporting,
  chain/store aggregations, ranking, running totals, period-over-period comparisons, or
  any data mart / dbt-style query for MT metrics. Also triggers on: "write a query",
  "SQL for this", "how do I calculate in SQL", "window function", "rank stores by",
  "running total", "MoM growth in SQL", "SQL for offtake", "CTE for this report",
  "show me SQL", "pivot in SQL", "days of supply query".
  Do NOT use for Python data processing, Excel formulas, or Power BI DAX — route those
  to the relevant skills.
---

# MT SQL Analytics

Write production-grade SQL for Modern Trade reporting — clean CTEs, window functions,
period comparisons, and store/chain aggregations aligned to the Honasa MT data model.

## SQL Quality Tier (apply in this order)

**S — Always enforce:**
- Explicit CTEs (no subquery nesting beyond 2 levels)
- `lowercase` SQL keywords, `snake_case` column aliases
- Every column aliased descriptively — no `col1`, no `a.x`
- Qualify all columns with table/CTE alias
- Defensive NULL handling in aggregations

**A — Use when relevant:**
- Window functions for ranking, running totals, lag/lead comparisons
- `PARTITION BY chain_name` or `PARTITION BY fy_tag` for channel-level windows
- `DENSE_RANK()` for store rankings (handles ties correctly)
- `LAG()` / `LEAD()` for MoM or YoY delta

**B — Join patterns:**
- State grain before every join: "one row = Month + Chain + Site Code + EAN"
- Prefer LEFT JOIN + NULL check over INNER JOIN to surface unmapped records
- Use `WITH` / CTE aliases instead of derived tables for readability

**C — Cleanliness:**
- `COALESCE(value, 0)` for aggregation denominators
- `NULLIF(denominator, 0)` to guard divide-by-zero
- `TRIM(UPPER(chain_name))` before joining on string keys
- `CAST(site_code AS VARCHAR)` — preserve leading zeros, avoid numeric casting

## MT Data Model Reference

```
-- Core grains:
-- Primary:    month_label + chain_name + brand_name + pack_size → nsv_lakhs
-- Offtake:    month_label + chain_name + site_code  + ean       → qty_sold, value_sold
-- P&L:        month_label + chain_name                          → gross_margin, trade_spend
-- Distribution: month_label + chain_name + ean                  → numeric_dist, weighted_dist

-- FY logic (Indian FY, Apr–Mar):
-- Apr–Dec of calendar year Y → FY(Y+1)   e.g. Apr-26 → FY27
-- Jan–Mar of calendar year Y → FY(Y)     e.g. Mar-26 → FY26
CASE
    WHEN MONTH(txn_date) >= 4 THEN CONCAT('FY', YEAR(txn_date) + 1 - 2000)
    ELSE CONCAT('FY', YEAR(txn_date) - 2000)
END AS fy_tag
```

## Canonical Patterns

### 1. Primary NSV by Chain × FY (with MoM growth)

```sql
WITH monthly_primary AS (
    SELECT
        p.fy_tag,
        p.month_label,
        p.chain_name,
        SUM(p.nsv_lakhs) AS nsv_lakhs
    FROM primary_sales p
    WHERE p.fy_tag IN ('FY25', 'FY26', 'FY27')
    GROUP BY
        p.fy_tag,
        p.month_label,
        p.chain_name
),
with_prior_month AS (
    SELECT
        m.*,
        LAG(m.nsv_lakhs) OVER (
            PARTITION BY m.fy_tag, m.chain_name
            ORDER BY m.month_label
        ) AS prior_month_nsv
    FROM monthly_primary m
)
SELECT
    w.fy_tag,
    w.month_label,
    w.chain_name,
    w.nsv_lakhs,
    w.prior_month_nsv,
    ROUND(
        (w.nsv_lakhs - w.prior_month_nsv) / NULLIF(w.prior_month_nsv, 0) * 100,
        1
    ) AS mom_growth_pct
FROM with_prior_month w
ORDER BY
    w.fy_tag,
    w.chain_name,
    w.month_label;
```

### 2. Store Ranking by Offtake (per chain, per FY)

```sql
WITH store_offtake AS (
    SELECT
        o.fy_tag,
        o.chain_name,
        o.site_code,
        o.site_name,
        SUM(o.value_sold_lakhs) AS offtake_value_lakhs,
        SUM(o.qty_sold)         AS offtake_qty
    FROM offtake o
    WHERE o.fy_tag = 'FY27'
    GROUP BY
        o.fy_tag,
        o.chain_name,
        o.site_code,
        o.site_name
),
ranked AS (
    SELECT
        s.*,
        DENSE_RANK() OVER (
            PARTITION BY s.chain_name
            ORDER BY s.offtake_value_lakhs DESC
        ) AS store_rank_in_chain
    FROM store_offtake s
)
SELECT *
FROM ranked
WHERE store_rank_in_chain <= 10
ORDER BY
    chain_name,
    store_rank_in_chain;
```

### 3. Primary vs Offtake Reconciliation (gap detection)

```sql
WITH primary_agg AS (
    SELECT
        p.fy_tag,
        p.month_label,
        p.chain_name,
        SUM(p.nsv_lakhs) AS primary_nsv
    FROM primary_sales p
    GROUP BY p.fy_tag, p.month_label, p.chain_name
),
offtake_agg AS (
    SELECT
        o.fy_tag,
        o.month_label,
        o.chain_name,
        SUM(o.value_sold_lakhs) AS offtake_value
    FROM offtake o
    GROUP BY o.fy_tag, o.month_label, o.chain_name
)
SELECT
    COALESCE(p.fy_tag, o.fy_tag)           AS fy_tag,
    COALESCE(p.month_label, o.month_label) AS month_label,
    COALESCE(p.chain_name, o.chain_name)   AS chain_name,
    COALESCE(p.primary_nsv, 0)             AS primary_nsv_lakhs,
    COALESCE(o.offtake_value, 0)           AS offtake_value_lakhs,
    COALESCE(p.primary_nsv, 0) - COALESCE(o.offtake_value, 0) AS gap_lakhs,
    ROUND(
        (COALESCE(p.primary_nsv, 0) - COALESCE(o.offtake_value, 0))
        / NULLIF(COALESCE(p.primary_nsv, 0), 0) * 100,
        1
    ) AS gap_pct
FROM primary_agg p
FULL OUTER JOIN offtake_agg o
    ON  p.fy_tag      = o.fy_tag
    AND p.month_label = o.month_label
    AND TRIM(UPPER(p.chain_name)) = TRIM(UPPER(o.chain_name))
ORDER BY
    ABS(gap_lakhs) DESC;
```

### 4. Running Total & Cumulative Share

```sql
WITH monthly_nsv AS (
    SELECT
        p.fy_tag,
        p.month_label,
        p.brand_name,
        SUM(p.nsv_lakhs) AS brand_nsv
    FROM primary_sales p
    WHERE p.fy_tag = 'FY27'
    GROUP BY p.fy_tag, p.month_label, p.brand_name
),
totals AS (
    SELECT
        m.*,
        SUM(m.brand_nsv) OVER (PARTITION BY m.fy_tag)                       AS total_fy_nsv,
        SUM(m.brand_nsv) OVER (
            PARTITION BY m.fy_tag, m.brand_name
            ORDER BY m.month_label
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS cumulative_nsv
    FROM monthly_nsv m
)
SELECT
    t.fy_tag,
    t.month_label,
    t.brand_name,
    t.brand_nsv,
    t.cumulative_nsv,
    ROUND(t.brand_nsv / NULLIF(t.total_fy_nsv, 0) * 100, 1) AS brand_share_pct
FROM totals t
ORDER BY t.month_label, t.brand_nsv DESC;
```

## Output Rules

- Always show the SQL first, then a 2–3 line plain-English explanation
- State the grain assumption at the top of every query as a comment
- Flag any join that could produce fan-out (many-to-many risk)
- If the user's data model is unclear, state the assumed schema before writing
- Never fabricate column names — ask if unsure
