-- name: brand_category_mix
-- description: Brand x category primary NSV mix for one FY.
-- param: fy default=FY26
SELECT
    brand,
    category,
    round(sum("sale in lac"), 1)                                     AS nsv_lakh,
    round(100 * sum("sale in lac") / sum(sum("sale in lac")) OVER (), 2) AS share_pct
FROM v_primary_article
WHERE fy_from_label("Month") = '{{fy}}'
GROUP BY 1, 2
ORDER BY 3 DESC
LIMIT 40;
