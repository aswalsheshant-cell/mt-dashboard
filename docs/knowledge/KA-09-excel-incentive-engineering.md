# KA-09 — Excel Incentive Engineering

| Field | Value |
|---|---|
| Topic_ID | KA-09 |
| Purpose | Build a workbook a finance reviewer can audit without reverse-engineering it. |
| Applicable_Agents | business-ai-automation, excel-automation |
| Trigger_Conditions | excel workbook, incentive working, formula, structured reference, XLOOKUP |
| Source_Type | Official vendor / recognised industry body |
| Access_Date | 2026-09-11 |
| Last_Reviewed | 2026-09-11 |
| Review_By | 2027-03-11 |
| Internal_Approval_Required | No |
| Confidence | HIGH |

## Authoritative sources
- Microsoft Support — Using structured references with Excel tables
- Microsoft Support — XLOOKUP function (exact match)

## Key principles
- Use Excel Tables and structured references: they expand with new rows and read as business language.
- XLOOKUP with exact match for employee, grade and rule lookups.
- Separate input, calculation and output areas.
- Every displayed number comes from a formula, never a typed-over result.
- A blocked row stays visibly blocked; it does not become 0.

## Recommended pattern
Tables named per sheet; structured references throughout; XLOOKUP exact for lookups; SUMIFS/COUNTIFS for aggregation; IFS for slab bands; one control sheet carrying period, versions and status.

## Anti-patterns
- Hardcoded ranges like A2:A500 where a Table would grow.
- Manually overwriting a formula result.
- Hidden helper logic with no label.
- Decorative formatting that obscures which cells are inputs.

## Project application
MT_Incentive_Working_FY27.xlsx follows this: structured tables, formula-driven, blocked rows left blocked.

## Project limitations
Any value that cannot be derived by formula must be an explicit, labelled input — never a typed-in answer.

## Related project files
- `incentive_working/`
