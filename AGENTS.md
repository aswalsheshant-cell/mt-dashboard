# Shared agent operating contract

This file applies to Claude Code, ChatGPT/Codex, and any other coding agent in
this repository. Read `CLAUDE.md` for the existing business and implementation
rules, `docs/PROJECT_STATE.md` for narrative state, and
`config/project_state.yml` for machine-readable blockers and held PRs. The
current human request and platform permissions take precedence over repo notes.

## Resume from Git and live GitHub

Before editing, run or obtain the equivalent of:

```text
git status --short --branch
git branch --show-current
git rev-parse HEAD
git worktree list --porcelain
git fetch origin
git log --oneline -5
```

Compare local HEAD with the remote branch and its open PR, then inspect the
current `main`, required checks, review comments, `docs/PROJECT_STATE.md`,
`config/project_state.yml`, and the relevant section of
`docs/COMPLETION_BLOCKER_PACK.md`. If authentication or a checkout is
unavailable, use read-only GitHub evidence and record the limitation. A chat
summary, old SHA, or green check from another SHA is not current evidence.

If local HEAD differs from the handoff SHA, inspect the intervening commits
and changed files before continuing. If the branch is already merged, start a
fresh branch from current `main`; do not add commits to merged history. If the
worktree is dirty, record `git status` and the diff, then checkpoint or
explicitly transfer those changes. Never reset, clean, discard, or silently
ignore another agent's edits.

## Branch and worktree ownership

- Give each focused change its own branch and, where available, its own
  worktree. One agent writes to a branch/worktree at a time; a handoff transfers
  ownership explicitly. Other agents may review it read-only.
- Start new work from current `main`. Continue an existing PR branch only when
  the handoff names its exact head and scope and its current GitHub state has
  been checked. Do not force-push, rebase, cherry-pick, or merge a held branch
  merely to combine work.
- Keep unit reconciliation, agent protocol, B5 Desktop tooling, owner mapping,
  and Finance decisions in separate focused PRs. A draft PR is the checkpoint
  for validated work that still needs evidence or review.
- PR #119 is frozen evidence for #120. PR #267 is on HOLD for Finance approval.
  PR #291 is B5 tooling, not Desktop proof. Confirm each live state before
  acting; do not rewrite or merge these branches as part of another task.

## Data and evidence boundaries

- Preserve raw rows, historical mappings, source files, approved values, and
  frozen evidence. Never change a number or drop source records to make two
  dashboards appear equal. Preserve negative returns and distinguish zero from
  missing data.
- Compare only the same metric, source rows, period, channel scope, and unit.
  Primary, Distributor Secondary, and Offtake are separate measures. Reliance
  Brand Counter deduplication applies to Offtake only; Primary stays gross.
- For a claimed correction, record source identity (path, SHA-256, row count),
  transformation, output value and unit, test command, result, and remaining
  delta. Mark missing or incompatible periods `NOT_COMPARABLE`, not zero.
- Keep person-level or client-identifying source rows, credentials, and raw
  confidential data out of PR bodies, logs, and state documents. Publish only
  the minimum aggregate evidence needed to review a claim.
- Power BI structural CI is not a live Desktop run. B5 remains
  `BLOCKED_PENDING_DESKTOP_EVIDENCE` until the governed cases, retained raw
  outputs/screenshots, and human exit decision are complete.

## PR and merge guardrails

- While `feature_freeze.active` is true, declare exactly one `Freeze
  classification:` in each PR body and meet `scripts/check_pr_scope.py`.
  A correctness fix names a changed regression test. Keep incomplete work
  draft and explain its limits.
- Run the tests relevant to the changed paths, regenerate QuickSetup when its
  source Power Query or DAX changes, and report exact commands and commit SHA.
  Read CI and reviews on that SHA; green CI is technical evidence only.
- Business mapping, Finance, and B5 exit decisions belong to their named
  human owners. Never mark a blocker clear based on code, an old screenshot,
  or an agent's interpretation of an approval.
- Merging to `main` deploys the HTML dashboard. Never merge, enable auto-merge,
  publish, or change a held PR's state without the owner's explicit instruction
  for that action. Prepare a reviewable draft and evidence first.

## Handoff record

Put this record in the active draft PR body or a committed handoff note before
transferring branch ownership. Update `docs/PROJECT_STATE.md` only for a
validated project milestone, and update `config/project_state.yml` with the
same verified blocker/held-PR facts. Do not copy transient PR status into a
second state registry.

```text
Repository and objective:
Branch and worktree path (or remote-only):
Full local HEAD / remote HEAD / main SHA, checked at:
Dirty or clean state; uncommitted paths and checkpoint:
PR / issue and freeze classification:
Allowed paths and forbidden paths:
Source evidence and data boundaries:
Tests / CI / live evidence, each with command, result, and SHA:
Open blocker, owner, and exact missing evidence:
Next authorized action:
Merge restriction: no merge without explicit owner instruction
```

On resume, verify every field against Git, GitHub, and current source files.
If a field is stale, correct the handoff before writing code. Keep historical
records as history; do not turn an unverified or provisional figure into an
approved one by editing a state document.

