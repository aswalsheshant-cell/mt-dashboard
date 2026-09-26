# Finding classification

Every finding gets one **class**, one **severity** and one **status**, each with its
evidence (file:line, command and result, or log excerpt).

## Class

| Class | Meaning | Example |
|---|---|---|
| `PRODUCT_DEFECT` | The change is wrong for users or data | Failed load shown as a healthy empty state |
| `DATA_IMPACT` | The diff reaches a figure, baseline, FY or mapping | A filter that drops negative return rows from a total |
| `HARNESS_DEFECT` | A test, CI step, hook or validator can report green over a failure, or cannot run where it claims to | `continue-on-error` on a required validator; hard-coded browser path |
| `STALE_ASSERTION` | A check tests an implementation shape the architecture no longer has | Asserting `by_chain[].fy27` when FY27 lives in article-level detail |
| `SCOPE` | Unrelated change, or a needed change left out | A rewrite riding along with a one-line fix |
| `GOVERNANCE` | Registry, approval or protected-path rule not followed | New failure pattern with no FM row |
| `NIT` | Wording, naming, style | Comment typo |

## Severity

| Severity | Meaning | Merge effect |
|---|---|---|
| `BLOCKER` | Wrong number, false green, protected data changed, security | Fix before merge |
| `FIX_BEFORE_MERGE` | Cheap and knowingly contradicts a current standard | Fix before merge |
| `FOLLOW_UP` | Real, outside this PR's scope | Record it; do not widen the PR |
| `NIT` | Optional | Carry into a later push that already touches the file |

## Status

`OPEN`, `FIXED_IN_PR` (name the commit), `FOLLOW_UP_RECORDED` (name where),
`NO_CHANGE_NEEDED` (with the reason), `BLOCKED_HUMAN_DECISION` (state both options).

A red check on the PR also gets one change-verification label: `CAUSED_BY_CHANGE`,
`PRE_EXISTING`, `BLOCKED_ENVIRONMENT`, `BLOCKED_INPUT`, `BLOCKED_HUMAN_DECISION`.
`PRE_EXISTING` needs the same failure shown on unmodified `main` (same tests, same
error text), not just the same test names.
