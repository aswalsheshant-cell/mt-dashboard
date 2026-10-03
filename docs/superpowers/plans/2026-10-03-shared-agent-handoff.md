# Shared Agent Handoff Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Give Claude Code and ChatGPT/Codex one durable, agent-neutral handoff contract without duplicating project state or weakening governance.

**Architecture:** Root AGENTS.md contains stable operating rules. Existing docs/PROJECT_STATE.md remains the narrative handoff, and config/project_state.yml remains the machine-readable blocker and held-PR state. Live GitHub and Git are checked before either file is updated or acted on.

**Tech Stack:** Markdown, YAML, Git, GitHub PR and CI.

**Spec:** docs/superpowers/specs/2026-10-03-dashboard-unit-handoff-design.md

## Global Constraints

- One writing agent per branch/worktree at a time; separate focused branches and draft PRs.
- Never merge without explicit owner instruction, even when CI is green.
- Business mapping, Finance, and B5 evidence decisions are made by their named human owners.
- Do not duplicate current status in a new root PROJECT_STATE.md. A root pointer may be added only if required for discovery.
- Do not alter frozen PR #119, HOLD PR #267, B5 PR #291, source files, or financial values.
- Keep the feature-freeze classification and privacy boundary.

## Review Focus

- A resumed agent must detect that its remembered SHA differs from the current branch.
- A dirty worktree must be checkpointed or explicitly transferred, never silently ignored.
- The state file must distinguish a held PR from a short-lived draft PR.
- A green CI run must not be interpreted as mapping approval, B5 clearance, or merge permission.
- A branch already merged to main must not receive new commits.

---

### Task 1: Agent-neutral operating contract

**Files:**
- Create: AGENTS.md
- Review for conflicts, edit minimally if required: CLAUDE.md

**Interfaces:**
- Every agent reads AGENTS.md, CLAUDE.md where applicable, docs/PROJECT_STATE.md, config/project_state.yml, relevant blocker pack, and the live PR/issue before an edit.
- A handoff record has repository, branch/worktree, full HEAD SHA, dirty/clean state, checkpoint, PR/issue, allowed and forbidden files, blocker, tests/evidence with SHA, next authorized action, and merge restriction.

- [ ] Draft AGENTS.md with the single-writer rule, resume commands, branch/worktree separation, handoff fields, governance and privacy rules, and explicit no-merge boundary.
- [ ] Cross-check each rule against CLAUDE.md, docs/PROJECT_STATE.md, docs/COMPLETION_BLOCKER_PACK.md, and config/project_state.yml. Remove duplication and resolve contradictory wording.
- [ ] Review the file for secrets, stale fixed SHAs, and any instruction that could turn a provisional number into an approved one.
- [ ] Commit AGENTS.md on a dedicated documentation branch, not on the unit-fix or B5 branches.

### Task 2: State continuity and checks

**Files:**
- Modify only for verified current facts: docs/PROJECT_STATE.md and config/project_state.yml
- Optional pointer only: PROJECT_STATE.md
- Existing test: tests/test_repo_state_consistency.py

**Interfaces:**
- docs/PROJECT_STATE.md carries narrative milestones and next approved task.
- config/project_state.yml carries blocker and held-PR states; short-lived drafts are verified live rather than copied into a stale static list.

- [ ] Fetch current main and inspect the live open PRs/issues, especially #119, #267, #291, and the unfinished Claude FY branch.
- [ ] Update only facts that are verifiably stale; preserve historical entries as history and cite current source links in the commit/PR description.
- [ ] Add a root PROJECT_STATE.md pointer only if required for agent discovery; it must contain no copied status values.
- [ ] Run python -m pytest tests/test_repo_state_consistency.py -q and record PASS or fix a genuine contradiction.
- [ ] Commit the verified state change separately from AGENTS.md so reviewers can assess factual edits independently.

### Task 3: Draft review and merge guardrails

**Files:** No additional project code.

**Interfaces:** A draft PR contains freeze classification, exact changed-file scope, consistency-test result, handoff example, and a no-merge statement.

- [ ] Open a dedicated draft PR for the protocol. Confirm its diff excludes source data, dashboard/data.js, Power BI model files, and other PR branches.
- [ ] Confirm both agents can follow the resume and handoff steps from the written rules without relying on a chat transcript.
- [ ] Leave the PR draft while the feature freeze or owner review requires it. Do not merge without explicit owner instruction.
