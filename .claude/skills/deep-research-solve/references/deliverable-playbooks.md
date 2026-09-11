# Deliverable-specific playbooks

Read only the section matching what is actually being produced.

## When the deliverable is a prompt

- Research the target model, tool or platform first, and use its current official
  prompting guidance where available.
- Account for the tools and constraints it actually has.
- Eliminate redundant instructions. Remove vague motivational language.
- Make requirements observable and testable.
- Specify tool-use behaviour where useful.
- Define success criteria explicitly.
- Include safeguards against the failure modes the research surfaced.
- Structure complex instructions clearly.
- Avoid unnecessary chain-of-thought requirements; ask for conclusions and evidence
  rather than private reasoning.

Make the result directly reusable, not a one-off.

## When the deliverable is a Claude Code skill

Research current Claude Code skill documentation before finalising if current
behaviour or syntax matters. Use the current `SKILL.md` format.

Design around:

- a narrow, clear purpose
- a description that says **when to use it**, not merely what it can do — the
  description is the entire routing mechanism
- concise standing instructions
- appropriate `$ARGUMENTS` handling
- appropriate invocation control (`disable-model-invocation: true` when the user
  should decide when an expensive workflow runs)
- the tools the workflow actually requires
- supporting files only where they genuinely reduce context or improve
  maintainability

Keep `SKILL.md` focused. Move extensive references, templates or examples into
supporting files rather than bloating the primary file. Do not put a multi-step
workflow into `CLAUDE.md` when a task-specific skill is the better abstraction.

### Before adding a skill to a repository that already has some

- Check for an existing skill whose triggers substantially overlap. Extend that one
  instead of adding a competitor — duplicated guidance in two places produces
  contradictory answers, which is worse than a gap.
- Check whether the repository has a canonical skill source that syncs into
  install targets. If it does, edit the canonical source, never an installed copy.
- Check that whatever sync or install pipeline exists will not delete or overwrite
  a hand-written skill placed alongside generated ones.

## When the deliverable is an article, guide or documentation

Separate verified facts, analysis, recommendations and examples — do not blur them.

Use primary sources for important technical claims where possible. Do not repeat a
claim merely because many pages repeat it; repetition across content farms is not
corroboration.

Structure the document around solving the reader's actual problem rather than
around the shape of the topic. Include limitations and caveats where they
materially affect implementation. Prefer useful depth over filler.
