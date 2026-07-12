-- name: primary_vs_offtake
-- description: Month-level sell-in (primary, 'sale in lac') vs sell-out
--   (offtake NSV, already in Lakh) with the gap. Months align on the
--   FY+fiscal-month derived by THE ONE FY RULE; offtake coverage is only
--   the months whose store x article files are committed.
WITH p AS (
    SELECT fy_from_label("Month") AS fy, mon3_num("Month") AS m,
           any_value("Month") AS label, sum("sale in lac") AS primary_lakh
    FROM v_primary_article GROUP BY 1, 2
), o AS (
    SELECT fy_from_label("Month") AS fy, month_num_any("Month") AS m,
           sum("NSV") AS offtake_lakh
    FROM v_offtake GROUP BY 1, 2
)
SELECT
    coalesce(p.fy, o.fy)                          AS fy,
    coalesce(p.label, 'month ' || coalesce(p.m, o.m)) AS month,
    round(p.primary_lakh, 1)                      AS primary_nsv_lakh,
    round(o.offtake_lakh, 1)                      AS offtake_nsv_lakh,
    round(o.offtake_lakh - p.primary_lakh, 1)     AS offtake_minus_primary_lakh
FROM p FULL OUTER JOIN o ON p.fy = o.fy AND p.m = o.m
ORDER BY coalesce(p.fy, o.fy),
         (coalesce(p.m, o.m) - 4 + 12) % 12;
