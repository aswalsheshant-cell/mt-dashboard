-- name: data_quality
-- description: Data-quality sweep over the committed monthly CSVs. Every
--   result row should be 0; non-zero rows name the problem. Includes the
--   ONE-FY-RULE consistency check: the file's own FY column must agree with
--   the FY derived from the month label.
SELECT 'primary: negative NSV rows' AS check, count(*) AS bad_rows
FROM v_primary_article WHERE "sale in lac" < 0
UNION ALL
SELECT 'primary: null/blank chain', count(*)
FROM v_primary_article
WHERE "Chain name" IS NULL OR trim("Chain name") = ''
UNION ALL
SELECT 'primary: unparsable Month label', count(*)
FROM v_primary_article
WHERE fy_from_label("Month") IS NULL
UNION ALL
SELECT 'primary: FY column disagrees with ONE FY RULE', count(*)
FROM v_primary_article
WHERE right(trim("FY"), 2) <> right(fy_from_label("Month"), 2)
UNION ALL
SELECT 'offtake: negative NSV rows', count(*)
FROM v_offtake WHERE "NSV" < 0
UNION ALL
SELECT 'offtake: null/blank chain', count(*)
FROM v_offtake
WHERE "Chain Name" IS NULL OR trim("Chain Name") = ''
UNION ALL
SELECT 'offtake: unparsable Month label', count(*)
FROM v_offtake
WHERE fy_from_label("Month") IS NULL
UNION ALL
SELECT 'shipto: Cont% outside 0..1', count(*)
FROM v_primary_shipto WHERE "Cont%" < 0 OR "Cont%" > 1
ORDER BY bad_rows DESC, check;
