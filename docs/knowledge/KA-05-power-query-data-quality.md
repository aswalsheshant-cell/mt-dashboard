# KA-05 — Power Query Data Quality

| Field | Value |
|---|---|
| Topic_ID | KA-05 |
| Purpose | Ingestion patterns that keep a refresh correct and auditable. |
| Applicable_Agents | business-ai-automation, mt-python-pipeline |
| Trigger_Conditions | power query, ingestion, refresh, ETL, data profiling, transformation |
| Source_Type | Official vendor / recognised industry body |
| Access_Date | 2026-09-11 |
| Last_Reviewed | 2026-09-11 |
| Review_By | 2027-03-11 |
| Internal_Approval_Required | No |
| Confidence | HIGH |

## Authoritative sources
- Microsoft Learn — Power Query best practices (profiling, typing, modular queries, parameters, reusable functions)

## Key principles
- Profile columns before transforming them — quality, distribution, and value profile.
- Set correct data types early and explicitly; never rely on inference.
- Filter early, keep expensive steps late.
- Use modular staging queries and query groups; name every step meaningfully.
- Put file paths and switches in parameters, not inline.
- Prefer reusable functions over copied transformation chains.

## Recommended pattern
raw -> staging -> validated/master -> semantic. Each layer is a separate, named, individually inspectable query.

## Anti-patterns
- Hardcoding a file path inside a step.
- Unnamed steps (Changed Type1, Changed Type2) that nobody can audit.
- Repeating the same transformation in several queries instead of a shared function.

## Project application
Applies to incentive and target ingestion. Our Python ingestion follows the same layering: read -> canonicalise -> validate -> aggregate -> publish.

## Project limitations
Query folding cannot be assumed for file sources; verify before relying on it.

## Related project files
- `PowerBI/PowerQuery/`
- `scripts/ingest_massit_sales.py`
