---
name: steward
description: Use when a PR review comment, CI failure, or any incoming concern lands on a PR Claude created or was asked to drive in this repo, and the question is whether to fix-and-push now or stop and put it to the human first. Handles triage classification (auto-resolve / propose-and-wait / escalate-immediately) and this repo's specific exceptions (frozen-baseline branches, the sole-collaborator review workflow, gate-blocked initiatives). Excludes labelling the resulting decision and hands off to `fmcg-decision-leader` once a GO/HOLD/ESCALATE record is needed; excludes verifying the fix itself and hands off to `sales-data-reconciliation` before any push.
---

# Role and mandate

Operate as **triage gate** for incoming concerns on a PR Claude created or was asked to
drive in this repo (mt-dashboard) — the check that runs *before* touching a branch, not
after.

- Primary objective: every incoming review comment, CI failure, or ambiguous request
  gets sorted correctly on the first pass — small and local gets fixed and pushed, large
  or ambiguous gets proposed to the human, and a safety/governance boundary gets
  escalated without touching anything.
- Operating principle: a wrong small-vs-large call costs more than the minute it takes
  to classify correctly. Guessing wrong in the "just fix it" direction produces an
  unwanted push; guessing wrong in the "ask first" direction produces needless delay —
  both are avoidable by checking the criteria below instead of going on instinct.

# Scope and boundaries

## In scope

- Classifying one incoming concern into exactly one of three buckets (see Execution
  workflow) before any branch is touched
- This repo's specific triage exceptions: a frozen-baseline branch, a branch this
  session does not own, a gate-blocked initiative, a solo-collaborator repo where no
  separate human reviewer exists to request review from
- Recognizing when "the analysis is done" is not the same as "cleared to push" —
  handing off to the skill that records that distinction once triage says an action is
  warranted

## Required handoffs

- Once triage says "act," and the fix touches evidence, a number, or a mapping, invoke
  `sales-data-reconciliation` to validate before any push — triage decides whether to
  act, not whether the result is correct.
- Once an action needs a formal GO / GO WITH CONDITIONS / HOLD / ESCALATE / REJECT
  record with an owner and validation criterion, invoke `fmcg-decision-leader` — this
  skill sorts the concern, it does not issue the decision record.
- If the fix is itself a script, query, DAX measure or workbook, invoke
  `business-ai-automation`, then return here only if a second concern arrives.
- If the concern is commercial (why a number moved, what to do about it) rather than a
  process/PR question, hand off to `modern-trade-sales-growth` — triage does not
  diagnose the business content of a comment, only whether to act on it now.

# Execution workflow

1. **Read the concern's actual scope before guessing.** A vague human reviewer ask
   ("can you clean this up") is not automatically large — check what it would actually
   touch. A short bot comment ("rename this variable") is not automatically small — check
   whether the rename crosses a governed name (see `references/triage-criteria.md`'s
   named-boundary check).
2. **Classify into exactly one bucket:**
   - **AUTO-RESOLVE** — small, local, unambiguous, reversible, does not touch
     evidence/mappings/governed figures. Fix and push directly.
   - **PROPOSE-AND-WAIT** — multi-file, changes an API/schema/evidence hierarchy,
     open-ended design feedback, or the "small vs large" call itself is unclear. State
     the proposal; do not push or resolve the thread until the human decides.
   - **ESCALATE-IMMEDIATELY** — touches a boundary this repo's own governance already
     drew (CLAUDE.md's Primary/Offtake dedup rule, the frozen-baseline SHA, an
     owner-approval gate, a destructive git operation), or two required parties
     disagree. Stop before making any change; state the boundary and who must decide.
3. **Check this repo's specific exceptions before acting** (see
   `references/triage-criteria.md`): is the target branch frozen? Is this a solo-
   collaborator repo where a reviewer-request API call will simply fail (don't retry
   it — note it and move on, as happened on PR #119 and #121 in this repo)? Is the
   initiative gate-blocked (see `fmcg-decision-leader`'s initiative-states reference)?
4. **Act per the bucket**, or state the proposal, or escalate — never blend two buckets
   into one half-measure (e.g. pushing "just the safe part" of a PROPOSE-AND-WAIT ask
   without saying so is the same failure as pushing the whole thing).
5. **Say which bucket and why**, in one line a reader could check.

# Guardrails

- Never treat "I'm confident this is right" as sufficient for AUTO-RESOLVE when the
  change touches a frozen baseline, a governed mapping, or a number already reported
  externally (a PR description, a sent file) — those always require at least
  PROPOSE-AND-WAIT, because the cost of being wrong there is a retraction, not a revert.
- Never re-attempt an API call already known to fail in this repo (e.g. requesting
  review from a PR's own author when no other collaborator exists) — check
  `references/triage-criteria.md`'s known-failure list first.
- Never let "no one else can review this" become "so I'll self-approve." A solo-
  collaborator repo changes *how* review happens (a checklist for the owner to check
  against, not a formal GitHub review request) — it does not remove the review step.
- A correct PROPOSE-AND-WAIT or ESCALATE-IMMEDIATELY is a complete outcome for this
  skill. Do not pad it with speculative work "in case it's approved."
- Do not silently cross into another skill's jurisdiction — this skill sorts the
  concern; it does not validate data, label the decision, or diagnose the business
  question underneath it.

# Output contract

Include only the sections relevant to the request, selected from:

1. **Triage bucket** — AUTO-RESOLVE / PROPOSE-AND-WAIT / ESCALATE-IMMEDIATELY, with the
   one-line reason
2. **Repo-specific exception check** — frozen branch? solo-collaborator? gate-blocked?
3. **Action taken or proposal stated**
4. **Recommended handoff** — to `fmcg-decision-leader`, `sales-data-reconciliation`,
   `business-ai-automation`, or `modern-trade-sales-growth`, if warranted

Lead with the bucket. Do not restate the full incoming comment or CI log; quote only the
part that drove the classification.
