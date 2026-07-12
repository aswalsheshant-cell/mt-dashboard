-- name: shipto_chain_mix
-- description: Chain x brand primary NSV from the ship-to allocation fact
--   (already allocated Direct/Distributor -> Chain by Cont%). FY derived
--   from the MonthStart DATE via fy_from_ym.
-- param: fy default=FY26
SELECT
    "Chain"                       AS chain,
    "Brand"                       AS brand,
    round(sum("Primary NSV") / 100000.0, 1) AS primary_nsv_lakh
FROM v_primary_shipto
WHERE fy_from_ym(year("MonthStart"), month("MonthStart")) = '{{fy}}'
GROUP BY 1, 2
ORDER BY 3 DESC
LIMIT 40;
