-- name: fy_summary
-- description: Primary sell-in NSV by financial year. FY is DERIVED from the
--   month label via THE ONE FY RULE (fy_from_label macro), never read from a
--   fixed column, so FY27/FY28 appear automatically as their months arrive.
SELECT
    fy_from_label("Month")                       AS fy,
    round(sum("sale in lac"), 1)                 AS primary_nsv_lakh,
    round(sum("sale in lac") / 100.0, 2)         AS primary_nsv_cr,
    count(*)                                     AS source_rows
FROM v_primary_article
GROUP BY 1
ORDER BY 1;
