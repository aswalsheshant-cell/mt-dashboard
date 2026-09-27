# Calculation contract

## Achievement and time

Represent achievement as percentage points in a clearly named field: 105 means 105%, not 1.05. Convert ratio-form inputs once using their documented units. Slab fields in the inspected workbook use percentage points. Use decimal arithmetic for boundaries and currency; display rounding must not decide a slab.

For an additive sales metric after its own identity/scope/basis/data checks:

- Achievement_Pct = 100 × sum(matched actual) / sum(matched target), when target is positive.
- Gap_To_Target = target − actual (negative indicates overachievement).
- Remaining_To_Target = max(target − actual, 0), clearly distinct from signed gap.
- Same-scope summary achievement = 100 × sum(actual) / sum(target), not mean(employee percentages).

A missing or zero/negative target requires the approved special-case policy. Without one, achievement is unavailable; a measured actual of zero with a valid positive target is 0%. Incomplete source months are partial, not zero-filled complete periods.

FY labels name the ending year: Q1 Apr–Jun, Q2 Jul–Sep, Q3 Oct–Dec, Q4 Jan–Mar. Monthly payout cannot be converted to quarterly payout by averaging achievement. Annual achievement is computed from the approved annual actual/target population; annual top-up is not assumed to equal four quarterly top-ups. Keep quarterly awards and annual awards separately keyed.

For mid-period tracking, compare actual-to-date with an approved target-to-date only if one exists. Otherwise show progress against the full-period target with that label. Do not invent a daily target distribution. A forecast is separate, assumption-labeled, and never a payable achievement.

## Slab selection

Use key (scheme version, effective period, incentive grade, component, frequency) and evaluate its approved predicate. A unique match is required unless an explicit overlap/precedence policy chooses one. No match means zero only when the scheme explicitly says below-threshold performance earns zero; otherwise report RULE_BLOCKED.

The observed flattened file uses numeric approximations such as 105.0001 above a preceding 105 boundary and 999 for an open-ended label. The raw value 105.00005 exposes a gap. Do not silently round it up or stretch 999 into infinity: validate intended comparison operators and precision against approved source wording, record the normalized predicate and retain raw values. Overlapping "below" attrition tiers require approved precedence; do not add them or let row order decide.

Use the approved Payout Amount directly when it is the final award for that tier. Amount % may be descriptive of a multiplier already embedded in Payout Amount. Multiply a base by a rate only when the policy establishes a distinct base and rate calculation. Do not normalize an amount solely because it differs from the apparent multiplier; flag the source conflict.

## Payout sequence, when all gates are satisfied

1. Confirm employee and component eligibility and that the full calculation period is valid.
2. Calculate approved component measures using eligible, reconciled populations.
3. Match each component's approved slab and record predicate, input precision and source row.
4. Combine distinct component awards only as the scheme permits; apply conditional kickers/exclusions.
5. Apply caps, proration, rounding and signed adjustments in the exact approved order. The order is a policy field, not a universal formula. Missing cap is not 'unlimited'; missing proration is not 1.
6. Reconcile the shadow amount to its components and approved adjustments. Mark CALCULATED_NOT_APPROVED.
7. Compare against the Finance-approved file using employee, period and rule version. Payment requires its own reference. Refresh must not create another payment or overwrite approval history.

Readiness is layered. A valid performance percentage may be visible while payout is blocked by a cap decision, but not while its measurement basis or target is unknown. The current repository workbook suppresses some achievement fields until its broader readiness passes; preserve that behavior unless a separate tracking-view change is authorized and tested. Never bypass the global decision gate by calculating only the convenient approved rows.

## Synthetic arithmetic examples — not company policy

- Two monthly targets 100 and 300, actuals 100 and 240: combined achievement is 85%, not the mean of 100% and 80% (90%).
- Positive target 100 with measured actual 0: achievement 0%. Missing actual: unavailable.
- Synthetic tier's final amount 1,200 and descriptive multiplier 120%: award is 1,200, not 1,440.
- A synthetic approved order 'cap 1,000, then multiply by 0.5' applied to gross 1,200 gives 500. Reversing the order gives 600. Neither is the default business policy.
