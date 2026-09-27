# Acceptance scenarios

Run these on synthetic data when extending the tracker/calculator. This list is a test specification, not a claim that production calculation was tested.

| Case | Required result |
|---|---|
| Same positive target, one measured-zero actual and one missing actual | First achievement 0%; second unavailable, not 0% |
| Zero or negative target | No invented achievement or payout; policy exception identified |
| Targets 100/300, actuals 100/240 | Period achievement 85%, not 90% |
| Identical store sales credited in RKAM and SO role views | Each role reconciles; cross-role sum is not company sales |
| Unique name candidate without approved Employee_ID | Identity unresolved; no credited incentive |
| BA_Ops group but unknown Incentive_Grade | No automatic Sr National BA Ops rate |
| BDO/BDE focus top-up requested for Q2 while C2 is not APPROVED | `RULE_BLOCKED_C2`; blank award, not zero |
| BDO/BDE focus top-up for Q1 while C2 is not APPROVED | Q1 is inside both readings of C2; still blocked until every other gate (identity, grade, target, basis, cap, proration) passes |
| D1A PRIMARY and D1B OFFTAKE | Basis conflict; no scheme achievement or payout |
| All global decisions closed but cap/proration absent | No shadow amount; show missing row policy |
| 105, 105.00005, 105.0001 around observed tier boundary | Expose gap/precision issue; no display-rounding shortcut |
| Overlapping attrition thresholds | No stacking; require approved precedence |
| Any-one-focus-pack rule and three qualifying packs | No automatic three-pack sum or unapproved best-pack selection |
| Rule final payout 1200 with Amount % 120 | Do not pay 1440 by applying multiplier twice |
| Rule changes midway through a quarter | Preserve versions/effective intervals; no retroactive or invented proration |
| Missing month in an L3M window | Partial/blocked per policy; no divide-by-available-months default |
| Annual and quarterly components share an employee | Separate award keys; no duplicate annual top-up across quarters |
| Same inputs rerun | Stable calculation rows; no duplicate awards or payment records |
| Valid tracking but Finance payout approval absent | Tracking may show; payout remains calculated-not-approved/blocked as applicable |
| Candidate evidence known only from a chat | Request durable source reference; do not mark approved/paid |

Test each accepted slab at, immediately below and immediately above every boundary using the approved precision; test missing grades, joins, exclusions and returns. Reconcile the full population, not just matched rows. Keep source-to-rule-to-result evidence. Changes affecting Excel or Power BI additionally need their actual calculation-engine checks.

## RKAM EB2B/SIS scope cases

1. Exclude both channels from RKAM target and actual for overall and emerging, but retain them for NKAM.
2. An already excluded target is not reduced again.
3. Unknown channel mapping or missing target split stays unresolved.
4. Emerging subset plus channel filter excludes EB2B/SIS even for an emerging brand.
5. Excluded-channel returns remain in the excluded signed total.
6. Historical unfiltered RKAM percentages are not presented as corrected results.
7. Analyst is not automatically given the RKAM exclusion.
8. Summing BDO/BDE + RKAM + NKAM + Analyst into a company total fails (`ROLE_VIEW_NON_ADDITIVITY`).
