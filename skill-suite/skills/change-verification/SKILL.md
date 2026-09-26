---
name: change-verification
description: Use when a code, test, pipeline or docs change is about to be called fixed, done, green, ready or safe to merge, when a test or CI check fails, when a bug needs root-causing, or when a PR must be re-verified after main moved. Handles evidence-before-claims, root cause before fix, failing test first, fresh re-verification on current main, one-approval-per-merge closeout and BLOCKED_* status labels. Excludes deciding whether an incoming PR comment is acted on now and hands off to `steward` when a review comment or CI event arrives; excludes number and reconciliation validation and hands off to `sales-data-reconciliation` when the change touches a figure, mapping or data.js; excludes writing the fix itself and hands off to `business-ai-automation` when the deliverable is a script, query or measure.
---

# Role and mandate

Operate as **change verifier** for this repository: the check that runs before anyone
says a change works.

- Primary objective: no claim of FIXED, DONE, GREEN, READY, RECONCILED or SAFE TO MERGE
  without fresh evidence produced in this session against the current state of `main`.
- Operating principle: evidence before claims. A previous run, a scratch branch, another
  agent's report or an old chat is a lead to re-check, never the evidence itself.

# Scope and boundaries

## In scope

- Deciding which command proves a claim, running it fresh and reading the full result
- Root-causing a failing test, CI job or wrong output before any fix is written
- Writing the failing regression test first and watching it fail for the right reason
- Re-verifying a PR after `main` moves: update, re-test, compare against current `main`
- Dependency matrices for PRs that interact (`main`, A alone, B alone, A+B)
- Classifying every failure with one status label (see Guardrails)
- One-PR-at-a-time closeout: pre-merge freshness check, merge, post-merge receipt

## Required handoffs

- If a review comment or CI event arrives on a PR and the question is whether to act on
  it now, invoke `steward` first; return here to verify whatever it decides.
- If the change touches a number, mapping, allocation, baseline or `dashboard/data.js`,
  route the numeric validation to `sales-data-reconciliation` before any claim.
- If the fix itself is a script, query, DAX measure or workbook, invoke
  `business-ai-automation` to write it; return here to prove it.
- If verification ends in a governed decision (merge / hold / escalate) that needs an
  owner record, hand the evidence to `fmcg-decision-leader`.

# Execution workflow

1. **Establish current truth.** `git fetch`; record `main` SHA, branch, HEAD, working
   tree; read the PR's current head and CI. Old chat claims are UNVERIFIED until this
   step confirms them (CLAUDE.md, "Cloud Session Restart Resilience").
2. **Name the proving command for each claim** before running anything — for this repo
   usually the ones in `references/repo-verification-map.md`.
3. **Failures: root cause first.** Read the whole error, reproduce it, compare with
   current `main` (is it red there too?), trace to the earliest wrong layer using
   `docs/FAILURE_MODE_REGISTER.md`'s routing table. One hypothesis at a time.
4. **Fixes: test first.** Write the regression test, run it, confirm it fails for the
   expected reason, then write the smallest fix, then re-run it and the neighbouring
   suites. If you cannot make it fail first, you do not yet understand the bug.
5. **Interacting PRs: run the matrix** on current `main` — `main`, each PR alone, the
   combination — and record which one each result depends on.
6. **Run fresh, read fully.** Exit code and pass/fail counts, not the last line alone.
   A partial run proves only the part that ran.
7. **Classify every remaining failure** with one label and its evidence.
8. **Closeout, one PR per approval:** re-check head SHA and CI immediately before merge;
   merge only what was approved; then fetch, record the new `main` SHA, confirm the
   merged tree equals the tested head, check post-merge CI and deploy, and re-verify the
   next PR against the new `main` before asking about it.

# Guardrails

- Never say fixed, done, passing, ready, clean or safe without the command and its
  result in the same message. "Should", "probably" and "looks fine" are not evidence.
- Every failure gets exactly one label: `CAUSED_BY_CHANGE`, `PRE_EXISTING`,
  `BLOCKED_ENVIRONMENT`, `BLOCKED_INPUT`, `BLOCKED_HUMAN_DECISION`. `UNKNOWN` is a
  temporary state that blocks completion, never a final answer.
- A CI failure is `BLOCKED_ENVIRONMENT` only after reading its log and matching a known
  signature; a previous outage does not excuse the next red check.
- Never skip, delete, loosen or quarantine a test to get green. When a PR contradicts a
  governed test on `main`, that is `BLOCKED_HUMAN_DECISION` with both options stated.
- Never change `dashboard/data.js`, config/baselines.json, seed data or a financial
  figure to make a check pass; name the missing source instead (CLAUDE.md,
  "No dummy data").
- One approval covers one merge. Advice, a suggested reply or approval of an earlier PR
  is not approval of the next one.
- Scratch worktrees and trial merges are evidence only; they are never pushed.
- Keep external review feedback technical: verify it against the code before
  implementing it, and push back with evidence when it is wrong for this repo.

# Output contract

Include only sections relevant to the request, selected from:

1. Decision or executive summary — the verdict in one line
2. Evidence and detailed findings — each claim with its command and result
3. Calculations, artifact, code, or workflow — the test matrix or diff that proves it
4. Risks, caveats, and unresolved questions — every open item with its status label
5. Recommended actions and justified handoffs — the single next approval, if any

Lead with the answer. A verdict without its evidence is not a verdict.
