# KA-10 — Sensitive Data Boundary

| Field | Value |
|---|---|
| Topic_ID | KA-10 |
| Purpose | What may never reach a public artifact. |
| Applicable_Agents | all agents |
| Trigger_Conditions | privacy, public dashboard, GitHub Pages, employee data, publish |
| Source_Type | Official vendor / recognised industry body |
| Access_Date | 2026-09-11 |
| Last_Reviewed | 2026-09-11 |
| Review_By | 2027-03-11 |
| Internal_Approval_Required | No — this boundary is not negotiable |
| Confidence | HIGH |

## Authoritative sources
- GitHub Docs — GitHub Pages sites are publicly available on the internet under normal publishing

## Key principles
- A GitHub Pages site is public regardless of repository visibility settings.
- Employee names, employee IDs, grades, individual targets, achievement and payout are never published.
- Presence of a restricted input may be reported as a count; contents never.
- The boundary is enforced by an automated test, not by memory.

## Recommended pattern
Restricted data lives outside the published tree. Scripts that produce it refuse to write into dashboard/. A privacy test fails the build if a restricted pattern appears in a published asset.

## Anti-patterns
- Putting employee data in dashboard/data.js because 'the repo is private'.
- Relying on a person to remember the rule.
- Publishing an aggregate that is small enough to identify one person.

## Project application
Enforced by tests/test_published_assets_privacy.py and .gitignore. DMS/Massit is incentive-scope only and is absent from the commercial payload.

## Project limitations
Aggregates must be large enough not to re-identify an individual.

## Related project files
- `tests/test_published_assets_privacy.py`
- `.gitignore`
