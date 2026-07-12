-- name: store_coverage
-- description: Distribution footprint from offtake — distinct billed stores
--   and offtake NSV by chain and month.
-- param: fy default=%
SELECT
    fy_from_label("Month")            AS fy,
    "Month"                           AS month,
    "Chain Name"                      AS chain,
    count(DISTINCT "Site Code")       AS billed_stores,
    round(sum("NSV"), 1)              AS offtake_nsv_lakh
FROM v_offtake
WHERE fy_from_label("Month") LIKE '{{fy}}'
GROUP BY 1, 2, 3, mon3_num("Month")
ORDER BY 1, (mon3_num("Month") - 4 + 12) % 12, 5 DESC;
