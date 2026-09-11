# KA-11 — Target Scope & Quota Reconciliation

| Field | Value |
|---|---|
| Topic_ID | KA-11 |
| Purpose | Decompose the difference between a target file and the business target into named causes, so the business is asked a specific question rather than a general one. |
| Applicable_Agents | fmcg-decision-leader, sales-data-reconciliation, business-ai-automation |
| Trigger_Conditions | target mismatch, quota allocation, coverage gap, target scope, why does the target not tie |
| Source_Type | Recognised industry body (compensation governance) |
| Access_Date | 2026-09-11 |
| Last_Reviewed | 2026-09-11 |
| Review_By | 2027-03-11 |
| Internal_Approval_Required | Yes — the scope classification itself is a business decision |
| Confidence | HIGH |

## Authoritative sources
- WorldatWork — sales compensation governance: quota setting and allocation should be a
  governed process tied to roles and measures, and quota totals may legitimately differ
  from the operating plan because of coverage, ramping, territory design or deliberate
  over-allocation.
- WorldatWork — manager quota allocation practice: allocation methods vary by role and
  account potential, so a difference is evidence to investigate, not proof of an error.

## Key principles
- **A target file not equalling the business target is not automatically wrong.** The
  question is never "which number is right" but "is each difference intended".
- Never scale, redistribute or back-solve a target to close a gap. That converts an
  analytical guess into an official quota.
- Decompose before asking. "Why is coverage only 77%?" is a poor question; "Are these two
  regions H1-only by design?" is a decision the business can actually make.
- Test **presence** before **value**. A missing month or account is a harder fact than a
  value difference, and it survives a change of measure.
- Canonicalise before counting, and prove the total did not move. If normalisation changes
  the file total, the normalisation is wrong, not the file.
- Distinguish a **scope exclusion** (an entity deliberately outside the plan) from a
  **grain defect** (value present but not attached to the dimension being measured) from a
  **coverage gap** (value that should exist and does not).

## Recommended pattern
Walk the chain in order, stopping at the first level that explains the difference:

```
Business target
 -> metric and basis          (Primary? Offtake? gross or net?)
 -> period                    (all 12 months, for every region?)
 -> geography                 (which regions/states are present?)
 -> accounts / chains         (which live accounts have no target row?)
 -> brands
 -> eligible employee population
 -> role scope
 -> explicit exclusions
 -> target allocation total
```

Size each cause from evidence that is already in the data — the file's own peer ratios, or
a complete prior year — and label every number **indicative**. Then classify:

`FULL_BUSINESS_SCOPE` · `INTENTIONAL_INCENTIVE_SCOPE` · `INCOMPLETE_TARGET_COVERAGE` ·
`OVERALLOCATED_QUOTA` · `UNDERALLOCATED_QUOTA` · `DERIVED_TARGET` · `UNKNOWN_SCOPE`

A residual that no entity explains is itself a finding, and usually means the two numbers
are on different measurement bases.

## Anti-patterns
- Scaling the file up to the business total, or spreading the residual pro-rata.
- Reporting only the gap percentage, with no decomposition.
- Treating a region that appears in the file as fully covered — it may be part-year.
- Folding two different commercial entities together to make a coverage number look better.
- Merging a part-year gap and an absent-account gap into one estimate, which double counts.

## Project application
Applied to the FY27 RKAM target file by `scripts/target_scope_diagnostic.py`:

| Finding | Value |
|---|---|
| Target file | Rs 33,986.08 L (Rs 339.86 Cr) |
| Business target | Rs 44,132.86 L (Rs 441.33 Cr) |
| Gap | Rs 10,146.78 L — 77.0% coverage |
| Cause 1 — North and Central planned H1 only (Oct-26 to Mar-27 absent) | ~Rs 5,091.77 L, 50% of the gap |
| Cause 2 — 5 live accounts with no target row (Nykaa, Sancus, Ratnadeep, Guardian, Vijetha) | ~Rs 2,598.18 L, 26% |
| Unexplained residual | Rs 2,456.83 L, 24% |

Separately, a grain defect: Rs 5,012.20 L (14.75% of the file) carries no chain name, all of
it in North and Central. Verified **not** a duplicate of the chain-level rows — no state and
month carries both grains.

Classification stays `UNKNOWN_SCOPE` pending the business answers in
`incentive_working/target_scope_decision_pack.md`.

## Project limitations
The indicative sizings use FY26 offtake and the file's own peer H2/H1 ratio. They size a
cause; they do not set a target. Whether each exclusion is intended is a decision for MT
Leadership and Finance, not an analytical result.

## Related project files
- `scripts/target_scope_diagnostic.py`
- `incentive_working/target_scope_reconciliation.csv`
- `incentive_working/target_scope_decision_pack.md`
- `incentive_working/target_scope_diagnostic.json`
