-- name: monthly_nsv_trend
-- description: Month-by-month primary NSV (Lakh), optionally filtered.
-- param: chain default=%
-- param: brand default=%
SELECT
    fy_from_label("Month")               AS fy,
    "Month"                              AS month,
    round(sum("sale in lac"), 1)         AS primary_nsv_lakh
FROM v_primary_article
WHERE "Chain name" ILIKE '{{chain}}'
  AND brand        ILIKE '{{brand}}'
GROUP BY 1, 2,
    2000 + CAST(regexp_extract(trim("Month"), '([0-9]{2})$', 1) AS INTEGER),
    mon3_num("Month")
ORDER BY
    2000 + CAST(regexp_extract(trim("Month"), '([0-9]{2})$', 1) AS INTEGER),
    mon3_num("Month");
