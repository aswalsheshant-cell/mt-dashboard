# Post-V1 Backlog — FY27 Incentive Platform

Non-blocking improvements identified during the V1 completion sprint.
Nothing here may delay or gate V1 closure — see
`docs/FY27_INCENTIVE_V1_COMPLETION_SCORECARD.md` for the Definition of
Done that actually governs closure.

An item belongs here only if it is UI polish, optional automation,
performance work with no correctness impact, an additional
dashboard/report, or non-material dormant-code cleanup. A financial
correctness issue, a missing approval, an unexplained monetary
difference, or restricted-data exposure is a V1 blocker by definition
and must never be filed here instead.

## Open items

_None logged yet. Add rows as they surface during Phase C shadow
calculation, reconciliation, and QA — each with a one-line reason it is
non-blocking._

| Item | Type | Why non-blocking | Raised during |
|---|---|---|---|
| — | — | — | — |

## Governance admin item (tracked separately, not a backlog item)

Making "Incentive Decision Control Gate" (and the other product/QC
gates already running) required branch-protection status checks on
`main` needs repository Settings access this session does not have.
Recommended action for a repo admin:

1. Settings → Branches → branch protection rule for `main`
2. Add required status checks: the Incentive Decision Control Gate CI
   job, plus the existing Canonical Financial Truth / Dashboard
   Validation & QC checks already relied on informally
3. Enable "Require branches to be up to date before merging" (strict
   mode)
4. Leave all currently-passing checks in place — do not remove or
   weaken any existing protection while adding these
