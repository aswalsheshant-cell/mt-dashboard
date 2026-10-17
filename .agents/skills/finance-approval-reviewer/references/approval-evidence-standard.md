# Approval evidence standard

An item counts as approved only with all four:

1. **Decision** - Approve / Correct / Reject, in the owner's words.
2. **Approver** - a named person in Finance (or the owner the register names).
3. **Date** - the date they decided, not the date we recorded it.
4. **Reference** - mail subject, ticket, memo or sign-off ID that can be found later.

Plus the **scope** must match: same distributor / chain / month range / expense head.

## Not approval

- Silence, "no objection yet", or a blank cell.
- A system or gate name as approver (for example "Automated Finance Gate" in
  `docs/FINANCE_APPROVAL_Q1_FY27.md`). Treat it as a process record.
- An approval for another scope (a Q1 decision used for Q2, one distributor used for all).
- Our own proposal text copied into the decision column.
- A default assumption row ("Default portfolio assumption") with no reference.

## Recording

- AssumptionTable: Remarks = `Approved: <reference> <date>` (the coverage gate checks this text).
- Alias file: fill all four columns; the allocation script uses an alias only when
  `Owner_Decision == Approve` with approver, date and reference.
- If the user approves instead of Finance, record the user's name and date, and mark the
  Finance confirmation as still pending in the pack.
