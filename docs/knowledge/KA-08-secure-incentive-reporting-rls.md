# KA-08 — Secure Incentive Reporting (RLS)

| Field | Value |
|---|---|
| Topic_ID | KA-08 |
| Purpose | Restrict who can see employee and incentive rows. |
| Applicable_Agents | mt-powerbi-dax, business-ai-automation |
| Trigger_Conditions | RLS, row level security, USERPRINCIPALNAME, restricted reporting, persona access |
| Source_Type | Official vendor / recognised industry body |
| Access_Date | 2026-09-11 |
| Last_Reviewed | 2026-09-11 |
| Review_By | 2027-03-11 |
| Internal_Approval_Required | No (technique) / Yes (who may see what) |
| Confidence | HIGH |

## Authoritative sources
- Microsoft Learn — Row-level security in the service (dynamic RLS via a user mapping table and USERPRINCIPALNAME())

## Key principles
- Dynamic RLS resolves the signed-in user through a governed security mapping table.
- Validate the UPN the deployed environment actually returns; an email alias is not necessarily the UPN.
- Test with the real intended roles, not only as the author.
- Security is part of the model, not a visual-level filter.

## Recommended pattern
User/UPN -> security mapping -> authorised employee / zone / account -> filtered fact rows. Test Leadership, Finance, NKAM, RKAM and BDE separately.

## Anti-patterns
- Assuming email == UPN.
- Testing only as the workspace admin.
- Hiding rows with a visual filter and calling it security.

## Project application
Any incentive Power BI output is designed for RLS from the start and is never published publicly.

## Project limitations
Not yet implemented — we have no deployed incentive report. This is design guidance for when one exists.

## Related project files
- `PowerBI/docs/`
