-- name: chain_ranking
-- description: Chains ranked by primary NSV within one FY, with share %.
-- param: fy default=FY26
SELECT
    "Chain name"                                                     AS chain,
    round(sum("sale in lac"), 1)                                     AS nsv_lakh,
    round(100 * sum("sale in lac") / sum(sum("sale in lac")) OVER (), 1) AS share_pct
FROM v_primary_article
WHERE fy_from_label("Month") = '{{fy}}'
GROUP BY 1
ORDER BY 2 DESC
LIMIT 25;
