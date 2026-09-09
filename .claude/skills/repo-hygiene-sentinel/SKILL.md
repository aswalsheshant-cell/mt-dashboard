# Repo Hygiene & Stale Branch Sentinel

Periodically scan for lingering pull requests, abandoned branches, and stale context badges to keep the repository clean and prevent context clutter.

## Purpose

Proactively detect and recommend cleanup of:
- **Stale PRs**: Open PRs older than 7 days without recent activity
- **Merged branches**: Remote branches whose changes are already in `main`
- **Context clutter**: Merged PR badges that can be dismissed
- **Orphaned local branches**: Branches that track merged remotes

## Core Functionality

### 1. Stale & Lingering PR Detection

Scan all open pull requests and report:
- PR number and title
- Days since creation
- Last activity date
- Branch name
- Recommendation: `[KEEP OPEN]`, `[CLOSE AS OBSOLETE]`, or `[MERGE]`

Criteria for stale:
- Older than 7 days AND no recent commits/comments
- Draft status AND older than 14 days
- Branch already merged to main (superseded)

### 2. Merged Branch Cleanup

Identify remote branches whose changes are fully integrated into `main`:
- List branch name and commit hash at divergence point
- Provide one-command cleanup: `git push origin --delete <branch-name>`
- Group by category: `claude/**`, `feat/**`, `feature/**`, `release/**`

### 3. Context Pill Safety Guard

Remind user when merged PR badges (#50, #99, #106, #107, etc.) are lingering in chat context:
- List by PR number and title
- Suggest dismissal via '✕' icon to free context
- Note when multiple merged PRs clutter session memory

### 4. Safety Boundaries

**Critical Rules:**
- ✗ NEVER automatically delete branches or close PRs
- ✗ NEVER run destructive git commands without approval
- ✓ Run in diagnostic/advisory mode only
- ✓ Present structured table with rationale
- ✓ Request explicit user confirmation before any action

## Output Format

### Stale PR Report
```
| PR # | Title | Days Open | Branch | Status | Recommendation |
|------|-------|-----------|--------|--------|-----------------|
| 100  | Feature X | 14 | feat/v1.x-feature | Draft | CLOSE or MERGE |
```

### Merged Branch Cleanup
```
| Branch Name | Merged At | Cleanup Command |
|-------------|-----------|-----------------|
| origin/feat/v1.1.0-nav | 9a9df8b | git push origin --delete feat/v1.1.0-nav |
```

### Context Cleanup Checklist
```
[ ] #107 Store Hierarchy Granularity (merged, can dismiss)
[ ] #99  v1.0.0 Release (merged, can dismiss)
[ ] #50  Legacy Feature (merged, can dismiss)
```

## Trigger Points

**Automatic:** Run at end of every successful merge to `main`
**Manual:** User invokes with: `check repo hygiene`

## Implementation Notes

- Access pull requests via GitHub API (list, filter by state, created_at)
- Access branches via `git branch -r --merged origin/main`
- Use structured table output for clarity
- Always include timestamp of last scan
- Provide grouped recommendations (e.g., all claude/** branches in one section)

## Related Skills

- `ci-autofix`: Auto-fix CI failures (separate concern)
- `dashboard-qa-sentinel`: Dashboard validation (separate concern)
- This skill: Repository maintenance only
