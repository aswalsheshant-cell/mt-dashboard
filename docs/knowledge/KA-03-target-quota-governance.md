# KA-03 — Target / Quota Governance

| Field | Value |
|---|---|
| Topic_ID | KA-03 |
| Purpose | When a target file may be used as the payout basis, and when it may not. |
| Applicable_Agents | fmcg-decision-leader, sales-data-reconciliation, demand-inventory-planning |
| Trigger_Conditions | target, quota, achievement, target scope, coverage gap |
| Source_Type | Official vendor / recognised industry body |
| Access_Date | 2026-09-11 |
| Last_Reviewed | 2026-09-11 |
| Review_By | 2027-03-11 |
| Internal_Approval_Required | Yes — scope classification |
| Confidence | HIGH |

## Authoritative sources
- WorldatWork — quota setting and allocation governance

## Key principles
- A target needs a named owner and an approval before it drives pay.
- Target grain must match the job scope being measured.
- A derived or analytically allocated target must never silently become an official quota.
- A scoped file may legitimately total less than the business target — but only once the scope and exclusions are confirmed.
- Total-vs-detail reconciliation must be visible, not assumed.

## Recommended pattern
Classify every target file as one of: FULL_BUSINESS_TARGET, SCOPED_TARGET, INCOMPLETE_TARGET, DERIVED_TARGET, UNKNOWN_SCOPE. Only a confirmed FULL or SCOPED target may drive payout.

## Anti-patterns
- Scaling a partial target file up to match a business total.
- Assuming a coverage gap is either an error or an exclusion without asking.
- Using a prior-year-contribution allocation as an official quota.

## Project application
Our RKAM target file totals Rs 328.68 Cr against a Rs 441.33 Cr business target (74.5%). It is classified **UNKNOWN_SCOPE** until the business confirms. Existing zone/chain targets remain tagged DERIVED.

## Project limitations
The 74.5% gap is a business question. Do not scale, redistribute or infer it.

## Related project files
- `incentive_working/target_quality_exceptions.csv`
- `config/analytics_config.json`
