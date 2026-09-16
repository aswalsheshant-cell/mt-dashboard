-- ============================================================================
-- MT SQL Cookbook — real queries against this project's real fact table
-- ============================================================================
-- Purpose: SQL practice material grounded in this project's actual data, not
-- a tutorial dataset. Every query below is the SQL equivalent of something
-- dashboard/index.html already computes in pandas/JS this session, and every
-- result was verified against the live dashboard/data.js before being
-- written here (see "How this was verified" at the bottom) — following
-- docs/DATA_MODEL.md's fact/dimension naming.
--
-- Dialect: standard SQL window functions (RANK, SUM() OVER). Verified to run
-- as-is in SQLite; works unchanged in Postgres/SQL Server/BigQuery, which all
-- support the same window-function syntax.
--
-- Table shape (see docs/DATA_MODEL.md for the full fact/dimension writeup):
--   fact_sales(Month, FY, Channel, Zone, State, Chain, Brand, Category,
--              SubCategory, Range, PackSize, Article, EAN, NSV, MRP, Qty)
--   Grain: one row = one Article x one Chain x one Month. NSV/MRP in INR Lakh.
-- ============================================================================


-- ----------------------------------------------------------------------------
-- Query 1: Top-90%-of-buildup — which accounts make up 90% of FY27 NSV?
-- ----------------------------------------------------------------------------
-- SQL equivalent of scratchpad/mt_report/compute_top90.py from earlier this
-- session (same cumulative-contribution logic that script computed in pandas
-- with a groupby + cumsum). The window function does in one query what that
-- script did in three lines of pandas.
--
-- Verified result (FY27, live data): DMart, Reliance Retail, Apollo,
-- Nykaa (FSN), Lulu, Wellness Forever together = 90.7% of FY27 NSV — the
-- exact top-90% account set established earlier this session by the pandas
-- version, confirming the two approaches agree.

WITH chain_totals AS (
  SELECT Chain, SUM(NSV) AS nsv
  FROM fact_sales
  WHERE FY = 'FY27'
  GROUP BY Chain
),
ranked AS (
  SELECT
    Chain,
    nsv,
    SUM(nsv) OVER (ORDER BY nsv DESC ROWS UNBOUNDED PRECEDING) AS running_nsv,
    SUM(nsv) OVER ()                                            AS grand_total
  FROM chain_totals
)
SELECT
  Chain,
  ROUND(nsv / 100.0, 2)                        AS nsv_cr,
  ROUND(100.0 * running_nsv / grand_total, 1)  AS cum_pct
FROM ranked
ORDER BY nsv DESC;


-- ----------------------------------------------------------------------------
-- Query 2: Rank & running total by Chain — the window-function pattern
-- ----------------------------------------------------------------------------
-- The plain RANK() version of Query 1 — this is proposed-addition #3
-- ("Cumulative rank & running-total table") from this session's dashboard
-- improvement menu: same SQL pattern, without the 90%-cutoff framing.

SELECT
  Chain,
  ROUND(SUM(NSV) / 100.0, 2)             AS nsv_cr,
  RANK() OVER (ORDER BY SUM(NSV) DESC)   AS rank_by_nsv
FROM fact_sales
WHERE FY = 'FY27'
GROUP BY Chain
ORDER BY rank_by_nsv;


-- ----------------------------------------------------------------------------
-- Query 3: Like-for-like YoY growth — FY27 vs FY26, same months only
-- ----------------------------------------------------------------------------
-- THE ONE FY RULE (CLAUDE.md) forbids comparing a part-year FY27 against a
-- full FY26 — that isn't a YoY, it's a coverage artefact. This query only
-- ever compares the months BOTH years actually have. The month list below
-- (Apr-Aug) is not hardcoded from memory — it's the live value of
-- data.js's detail_meta.same_period.months as of 2026-09-16, and it widens
-- automatically as more FY27 months arrive; re-pull that value before
-- reusing this query once more months exist.
--
-- Verified against data.js's own published detail_meta.same_period.by_chain
-- block (which computes the same thing in Python) — results agree to within
-- floating-point summation-order noise (e.g. DMart: this query 95.19%,
-- published 95.2%; a ~0.01pp gap from 160,834 rows summing in a different
-- order between SQLite and Python, not a logic difference).

WITH curr AS (
  SELECT Chain, SUM(NSV) AS curr_nsv
  FROM fact_sales
  WHERE FY = 'FY27' AND Month IN ('April','May','June','July','Aug')
  GROUP BY Chain
),
prev AS (
  SELECT Chain, SUM(NSV) AS prev_nsv
  FROM fact_sales
  WHERE FY = 'FY26' AND Month IN ('April','May','June','July','Aug')
  GROUP BY Chain
)
SELECT
  curr.Chain,
  ROUND(curr.curr_nsv / 100.0, 2)                       AS curr_fy27_cr,
  ROUND(COALESCE(prev.prev_nsv, 0) / 100.0, 2)          AS prev_fy26_cr,
  ROUND(curr.curr_nsv - COALESCE(prev.prev_nsv, 0), 2)  AS delta_lakh,
  CASE WHEN COALESCE(prev.prev_nsv, 0) > 0
       THEN ROUND(100.0 * (curr.curr_nsv - prev.prev_nsv) / prev.prev_nsv, 2)
       ELSE NULL END                                     AS yoy_pct
FROM curr
LEFT JOIN prev ON prev.Chain = curr.Chain
ORDER BY curr.curr_nsv DESC;


-- ============================================================================
-- How this was verified (2026-09-16)
-- ============================================================================
-- 1. Loaded dashboard/data.js's detail_records (160,834 rows) into an
--    in-memory SQLite table matching the schema above.
-- 2. Ran all three queries above against it.
-- 3. Compared Query 1's result against the top-90% account set this session
--    established independently in pandas (scratchpad/mt_report/
--    compute_top90.py) — same six accounts, same 90.7%.
-- 4. Compared Query 3's result against data.js's own published
--    detail_meta.same_period.by_chain block — agreed within float noise.
-- No number in this file was written from memory or assumed to be correct.
-- ============================================================================
