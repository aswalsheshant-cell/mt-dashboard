# Triage criteria and calibration

## The three buckets, with a concrete test for each

| Bucket | Test | This repo's worked example |
|---|---|---|
| **AUTO-RESOLVE** | Single file or single function, reverses cleanly, touches no governed figure/mapping/frozen SHA, and a wrong guess costs one more push | A lint-bot rename, a docstring fix, adding a missing test case a reviewer names explicitly |
| **PROPOSE-AND-WAIT** | Multi-file, changes evidence-hierarchy logic, an API/schema, or the ask itself is open-ended ("clean this up") | A review comment questioning whether Level 1.5 should trust a self-referential pooled value — this is exactly the class of change that requires the full 25-test + 16-month rerun before it's accepted, so it is proposed and validated, never pushed on a hunch |
| **ESCALATE-IMMEDIATELY** | Crosses a boundary this repo's governance already drew, or two required parties disagree | Being asked to promote `PROVISIONAL_BUSINESS_MAPPED_PRIMARY` to governed status before owner sign-off — this is not this skill's or even `fmcg-decision-leader`'s call to make; it is CLAUDE.md's own boundary and stays with the business owner |

## Named-boundary check (apply before AUTO-RESOLVE)

A change that looks small in diff size can still be large in consequence. Check whether
it touches any of:

- A number or figure already reported externally (a PR description, a sent file, a
  comment) — even a one-line fix here needs the regenerate-and-diff step
  (`historical_primary_chain_backfill_report.py`'s pattern), not a hand edit
- A frozen-baseline SHA banner — touching the branch at all means updating the banner,
  which means this was never AUTO-RESOLVE to begin with
- `CHAIN_ALIASES`, `DISTRIBUTOR_NAME_ALIAS`, or any other governed lookup table — a new
  entry here is a business fact, not a code style choice
- The evidence-hierarchy order or a level's classification rule — always
  PROPOSE-AND-WAIT, full rerun required regardless of how small the diff looks

## Known API/process failures in this repo (do not re-attempt)

- **Requesting a GitHub review from a PR's own author.** This repo has exactly one
  collaborator (the repo owner) on every PR observed so far — a `reviewers` request
  naming them fails with "Review cannot be requested from pull request author." Confirmed
  on PR #119 and PR #121. Do not retry; post the review checklist as a PR comment
  instead and let the owner check it directly.
- **Treating a subscription-confirmation event as actionable.** The first event after
  `subscribe_pr_activity` is the subscription announcing itself (`kind:
  "subscription.created"`), not a real review or CI result. Check the PR's actual status
  (`get_status`, `get_reviews`) before reacting to it as if it were new information.
- **Assuming a Draft PR needs a merge-queue re-enable after `draft: false`.** Only
  relevant if auto-merge or a merge queue was active before the draft conversion —
  check, don't assume either way.

## Solo-collaborator review workflow (this repo's standing exception)

Because no second collaborator exists, "get this reviewed" cannot mean a formal GitHub
review request. It means:

1. Post a scoped checklist as a PR comment (see the `fmcg-decision-leader`-adjacent
   pattern used on PR #121) — concrete, checkable items, not a general "does this look
   right?"
2. Mark the PR ready for review if it was draft.
3. Do not attempt `reviewers: [...]` naming the author — see known failures above.
4. Treat the owner's response to that checklist, whenever it arrives, as the review
   disposition — a logic-affecting response reopens the branch (PROPOSE-AND-WAIT →
   fix → full revalidation); a documentation-only response does not.

## When triage itself is unclear

If the bucket call is genuinely ambiguous after checking the tests above, that ambiguity
*is* the answer: default to PROPOSE-AND-WAIT rather than picking a side. Never resolve
an unclear classification by picking whichever bucket requires the least work right now.
