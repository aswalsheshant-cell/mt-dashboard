---
name: deep-research-solve
description: Perform rigorous web and codebase research before solving a complex problem. Use when the user asks for deep research, root-cause investigation, comparison of approaches, debugging, architecture decisions, creation of prompts or skills, technical articles, implementation plans, or solutions that should be grounded in current evidence.
argument-hint: "[research question, problem, or task]"
disable-model-invocation: true
---

# Deep Research, Problem Solving, and Final Deliverable

## Task

$ARGUMENTS

## Mission

Research and solve the task thoroughly before producing the final deliverable.
Do not treat the first plausible answer as the final answer.

Investigate the problem, gather evidence, identify failure modes and constraints,
compare viable approaches, resolve important uncertainties, and then produce the
strongest practical solution supported by the available evidence.

Use available tools proactively when they materially improve correctness. For
current, changing, niche, technical, unfamiliar, or externally verifiable
information, research the web rather than relying only on prior model knowledge.
When the task concerns an existing codebase, investigate the relevant files and
actual implementation before making claims about how the system works.

## 1. Establish the real objective

Before solving the task, determine: what the user ultimately wants to achieve;
what the requested final deliverable is; what would count as success; relevant
constraints; dependencies; technical and environmental limitations; compatibility
requirements; security implications where applicable; performance implications
where applicable; edge cases; known unknowns; assumptions that need verification.

Distinguish between (1) the stated request, (2) the underlying problem, and
(3) the desired outcome. Do not optimise merely for producing an answer. Optimise
for achieving the desired outcome.

If reasonable assumptions allow progress, make and document those assumptions
instead of stopping unnecessarily. Ask the user a question only when missing
information makes meaningful progress impossible, or could cause a materially
wrong, destructive, or irreversible outcome.

## 2. Investigate existing context first

When working inside a repository or project:

- inspect relevant files before making claims about them
- search the codebase for related implementations, configuration, interfaces,
  tests, documentation, dependencies, and historical patterns
- inspect existing project instructions and conventions
- identify the actual runtime, framework and library versions when relevant
- inspect error messages and logs when available
- check tests related to the affected behaviour
- understand how the affected component interacts with its neighbours

Never invent APIs, files, functions, configuration options, library behaviour, or
project conventions that have not been verified. Prefer evidence from the actual
repository over assumptions about how a typical repository might work.

## 3. Conduct deep web research when appropriate

Use web research for information that is current, potentially outdated,
specialised, disputed, unfamiliar, version-dependent, documentation-dependent,
standards-dependent, product-dependent, security-sensitive, implementation-specific,
or explicitly requested.

Research beyond the first search result. Use multiple targeted searches when
useful. Search not only for the apparent solution but also for official
documentation, specifications and standards, release notes, changelogs, migration
guides, known issues, bug reports, GitHub issues and discussions, technical
articles, implementation examples, benchmarks, security advisories, compatibility
reports, limitations, failure reports, alternative approaches, and lessons learned
by others solving the same problem.

**Search specifically for evidence that could prove the current hypothesis wrong.**

## 4. Apply a source hierarchy

Prefer sources roughly in this order: official specifications or standards;
official documentation; official source repositories; official release notes and
changelogs; maintainers' documented statements; peer-reviewed or authoritative
technical research; high-quality technical publications; reputable engineering
articles; well-supported issue trackers and technical discussions; community
discussions and anecdotal reports.

Community sources reveal real-world problems that official documentation omits,
but an anecdote is not an authoritative fact without corroboration. Do not base
important conclusions on low-quality SEO content, copied articles, AI-generated
content farms, or unsourced claims.

## 5. Verify important claims

For conclusions that materially affect the solution: verify against primary
sources when available; cross-check across multiple independent sources where
reasonable; verify version numbers, dates, APIs, syntax, commands, limits,
compatibility claims and configuration details; distinguish current behaviour from
historical behaviour, documented guarantees from observed behaviour, and fact from
inference.

Never fabricate a citation or imply a source was checked when it was not. If
evidence conflicts, investigate the disagreement instead of silently choosing the
convenient answer. State uncertainty when the evidence genuinely remains uncertain.

## 6. Research the problem, not only the solution

Explicitly investigate common failure modes, implementation traps, edge cases,
incompatible combinations, deprecated approaches, security concerns, performance
concerns, maintainability concerns, scaling limits, hidden prerequisites, migration
issues, platform-specific behaviour, version-specific behaviour, operational
failure scenarios, and the reasons apparently correct approaches fail in practice.

Useful search shapes, adapted intelligently rather than repeated mechanically:

```
[technology] known issues            [approach] limitations
[error] root cause                   [library/version] breaking changes
[solution] production issues         [technology] security considerations
[technology] performance problems    [approach A] vs [approach B]
[feature] official documentation     [technology] migration guide
[error message] GitHub issue
```

## 7. Maintain competing hypotheses

For ambiguous or complex problems, do not lock onto the first explanation. Develop
plausible competing hypotheses. For each, consider supporting evidence,
contradicting evidence, missing evidence, how it could be tested, confidence level,
and the consequences if it is wrong.

Eliminate weak hypotheses as evidence accumulates. Prefer the explanation that
accounts for all observed evidence with the fewest unsupported assumptions.

## 8. Root-cause analysis

When investigating a bug, failure or unexpected behaviour, separate symptoms,
proximate cause, contributing factors, root cause, environmental conditions and
trigger conditions.

Do not merely suppress the visible symptom if the underlying cause can reasonably
be identified and fixed. Determine **why** the problem occurs before deciding
**how** to fix it.

## 9. Compare candidate solutions

Do not automatically choose the first workable approach. Identify realistic
alternatives when they exist and evaluate them against the criteria that matter
for this task: correctness, evidence strength, compatibility, simplicity,
implementation effort, reliability, maintainability, security, performance,
scalability, reversibility, operational burden, cost, user experience, long-term
viability.

Prefer the simplest solution that fully satisfies the verified requirements. Avoid
unnecessary architecture, abstractions, dependencies, features, defensive layers,
or speculative future-proofing.

## 10. Prefer current and supported approaches

Before recommending an API, library, framework feature, CLI command, architecture,
model, integration or configuration: confirm it currently exists; confirm it is
supported; check whether it has been deprecated or superseded; check version
requirements; prefer currently recommended patterns over legacy workarounds.

When sources from different dates conflict, prioritise current authoritative
documentation while explaining materially important historical differences.

## 11. Use subagents selectively

Use subagents when they improve quality or efficiency — independent research
questions, parallel investigation of competing approaches, separate documentation
research, codebase exploration, security analysis, testing alternative hypotheses.

Do not create subagents for trivial tasks that are faster handled directly. When
parallel research is useful, divide the work into genuinely independent questions
rather than having several agents run the same broad search. Synthesise their
findings yourself instead of accepting their conclusions unexamined.

## 12. Keep research grounded

During investigation, maintain concise working notes: important facts, relevant
source links, hypotheses, unresolved questions, rejected approaches and why they
were rejected, compatibility constraints, important version information, and
evidence affecting the final recommendation.

For long or multi-stage tasks, persist useful progress in a temporary research or
progress file if that protects against context loss. Do not clutter the user's
project with unnecessary permanent files; remove temporary files that are no
longer useful when the task is complete.

## 13. Decide when research is sufficient

Do not research indefinitely. Research is sufficiently complete when the real
problem is understood; the major claims needed for the decision are supported;
significant alternative explanations have been considered; major failure modes are
understood; realistic competing solutions have been evaluated; remaining
uncertainty is unlikely to materially change the recommendation; and additional
searching is producing diminishing returns.

The objective is sufficient high-quality evidence, not a maximum source count.

## 14. Build the solution from the evidence

Only once the investigation is sufficiently mature, construct the final solution.
It must incorporate what the research established: verified requirements,
compatibility constraints, failure-mode protections, edge-case handling, current
best practices, version-specific requirements, implementation lessons, and security
and performance considerations where applicable.

Do not produce a generic solution when the evidence supports a more specific one.

## 15. When the user requests code or project changes

1. investigate before editing
2. identify the smallest correct change
3. implement the actual solution rather than describing it
4. preserve unrelated existing behaviour
5. follow the repository's conventions
6. avoid unrelated refactoring
7. never hard-code behaviour merely to satisfy a test
8. never weaken existing validation or safety checks to make tests pass
9. update affected tests when appropriate
10. run the most relevant tests, linting, type checking, build or validation steps
11. inspect failures and correct the implementation where feasible
12. verify the resulting behaviour rather than assuming that a successful run means
    a correct one

Treat tests as evidence about correctness, not as the definition of correctness.

## 16. Deliverable-specific playbooks

When the requested deliverable is a **prompt**, a **Claude Code skill**, or an
**article, guide or documentation**, read
`references/deliverable-playbooks.md` before writing it.

## 17. Validate before finalising

Confirm that the original task has actually been answered; the underlying
objective is addressed; important claims are evidence-backed; material assumptions
are identified; current information was checked where necessary; no known critical
requirement was ignored; no significant contradiction remains unresolved; major
failure modes are handled; commands and syntax are plausible and version-appropriate;
proposed code integrates with the existing project; relevant validation ran where
possible; the solution is not unnecessarily complicated; citations correspond to
sources actually consulted; and the deliverable can be used directly.

If validation reveals a material problem, correct it before presenting the result.

## 18. Final response format

Adapt the presentation to the task rather than forcing every answer into one
template. For a substantial research-and-solution task, normally provide:

**Conclusion** — the recommended solution, stated clearly.
**What the research established** — only the findings that materially influenced
the solution.
**Recommended solution** — the complete actionable answer.
**Implementation** — where applicable, provide or make the required change.
**Important caveats** — only those that materially affect successful use.
**Verification** — what was verified, tested or cross-checked.
**Sources** — links or citations for important external claims.

Do not bury the answer beneath a narration of the research process. The user needs
the solved problem and a trustworthy deliverable, not a transcript of reasoning.

## Core operating principles

Accuracy over speed. Evidence over assumption. Primary sources over summaries.
Root cause over symptom suppression. Current documentation over stale knowledge.
Actual repository evidence over guesses about the codebase. Practical solutions
over theoretical completeness. Minimal sufficient complexity over overengineering.
Verification over confidence. A complete useful result over an unfinished research
dump.
