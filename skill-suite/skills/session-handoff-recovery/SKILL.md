---
name: session-handoff-recovery
description: Use when Claude Code resumes after context compaction, a model/session switch, a cloud-container restart, a long pause, or a handoff from another agent, especially when it is unclear what was actually merged, tested, approved or still pending. Reconstructs current repository truth and creates a compact continuation brief. Excludes re-verifying a claimed fix and hands off to `change-verification`; excludes reviewing a PR's code quality and hands off to `pr-deep-review`.
---

# Role and mandate

Operate as the **state-recovery layer for Claude Code work on the MT Dashboard**.

Conversation memory is helpful context, never the authoritative project state. Git, current
PR/issue state, governed evidence files and fresh command results are the source of truth.

# Scope and boundaries

## In scope

- Context compaction recovery
- Model switching mid-project
- Cloud/container restart recovery
- Handoffs between agents or chat sessions
- Determining whether prior work is merged, still on a branch, superseded or stale
- Reconstructing pending human decisions and frozen evidence constraints
- Producing a continuation brief that a new Claude Code session can follow safely

## Required handoffs

- If a prior claim such as "fixed", "green" or "ready" must be proven again, use
  `change-verification`.
- If an open/historical PR must be judged, use `pr-deep-review`.
- If an incoming review/CI event needs an action decision, use `steward`.
- If recovered state exposes a data/mapping issue, route to `sales-data-reconciliation` or
  `mapping-approval-governor` rather than solving it here.

# Execution workflow

1. Read CLAUDE.md before taking any project action.
2. Re-establish Git state with fresh commands:
   - `git status --short --branch`
   - `git branch --show-current`
   - `git rev-parse HEAD`
   - `git rev-parse origin/main` after fetch
   - `git log --oneline -5`
3. Determine whether the previous working branch still exists, has merged, diverged from
   main, or has unpushed/uncommitted work.
4. Inspect current open PRs/issues relevant to the task. Do not assume an old PR number is
   still the implementation path; historical/frozen PRs may be evidence only.
5. Read the current governed evidence that controls the task, such as:
   - `docs/FAILURE_MODE_REGISTER.md`
   - decision/approval registers
   - current readiness/gap reports
   - latest CI/check evidence
6. Separate four categories in the recovered state:
   - **DONE_AND_MERGED** — confirmed on current main
   - **DONE_NOT_MERGED** — present only on a branch/PR
   - **BLOCKED** — input/environment/human decision explicitly prevents progress
   - **NEXT_EXECUTABLE** — safe work that can be done now without inventing a decision
7. Re-run only the minimum freshness checks needed to prevent acting on stale evidence.
8. Produce the continuation brief below and continue from `NEXT_EXECUTABLE`, unless the
   next step needs explicit approval.

## Continuation brief

Use this compact structure:

- Repository / branch / HEAD / main SHA
- Objective
- Confirmed merged work
- Open PRs/issues directly relevant to objective
- Frozen or do-not-modify evidence
- Latest validation evidence and date/commit
- Pending business/Finance/owner decisions
- Current blockers by status label
- Exact next executable action
- Explicit do-not-do list

# Guardrails

- Never continue editing a branch merely because the previous chat mentioned it. Confirm
  that it is still the correct branch against current main.
- Never treat old test results as current verification.
- Never convert an old approval into approval for a different PR, head SHA or merge.
- Never rewrite or rebase a branch documented as frozen evidence.
- Never discard local uncommitted work during recovery. Report it first.
- Never resolve an ambiguity by guessing what the previous agent intended; inspect Git and
  the governed documents.
- Keep the brief factual and compact. Its purpose is safe continuation, not a historical essay.

# Output contract

1. **Recovered state** — branch, HEAD, main and worktree
2. **What is actually complete**
3. **What remains blocked/pending**
4. **Next executable action**
5. **Handoff** — specialist skill required next, if any

Every completion statement must be tied to current repository evidence.
