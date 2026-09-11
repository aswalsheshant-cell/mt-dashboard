# KA-04 — Master Data Matching & Approval

| Field | Value |
|---|---|
| Topic_ID | KA-04 |
| Purpose | What a machine may correct automatically, and what only a human may approve. |
| Applicable_Agents | mapping-approval-governor, sales-data-reconciliation |
| Trigger_Conditions | employee mapping, identity, chain mapping, alias, fuzzy match, canonical |
| Source_Type | Official vendor / recognised industry body |
| Access_Date | 2026-09-11 |
| Last_Reviewed | 2026-09-11 |
| Review_By | 2027-03-11 |
| Internal_Approval_Required | Yes — any identity or ownership mapping |
| Confidence | HIGH |

## Authoritative sources
- Microsoft Learn — Power Query fuzzy matching (proposes similarity, does not establish identity)

## Key principles
- Escalate through: exact key -> approved normalisation -> canonical mapping -> candidate/fuzzy match -> human approval.
- Fuzzy similarity may PROPOSE. It may never APPROVE identity, ownership or anything that moves money.
- Raw and canonical values are both retained; the raw value is never overwritten.
- Silence from an owner is PENDING, never assent.

## Recommended pattern
Auto-safe: case, spacing, approved punctuation, approved aliases. Candidate-only: name->Employee ID, distributor->chain, ambiguous store->account. Never automatic: employee identity, incentive grade, commercial owner, target owner.

## Anti-patterns
- Approving an employee identity on a name match.
- Merging two genuinely different entities because the strings look alike.
- Dropping the raw value once a canonical one exists.

## Project application
Our WoA register implements exactly this: 28 one-line rule approvals, 3 exceptions, 36 with no candidate — all PENDING, none assigned.

## Project limitations
A first-time mapping always needs a human, however obvious it looks.

## Related project files
- `scripts/build_incentive_identity.py`
- `incentive_working/woa_employee_mapping_register.csv`
