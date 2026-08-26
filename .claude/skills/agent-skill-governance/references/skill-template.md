# Standardised skill template

Copy this as the starting point for any new skill in the suite. Cross-compatible with
Codex and Claude discovery: frontmatter carries `name` and `description` only.

```markdown
---
name: skill-kebab-case-identifier
description: Use when [precise trigger intents]. Handles [primary jurisdiction]. Excludes [neighboring jurisdiction] and hands off to `target-skill` when [observable condition].
---

# Role and mandate

Operate as **[specialist role]**.

- Primary objective: [measurable outcome]
- Operating principle: [evidence, decision, or quality philosophy]

# Scope and boundaries

## In scope

- [Task family]
- [Task family]
- [Deliverable family]

## Required handoffs

- If [observable condition], invoke or recommend `target-skill`.
- If required evidence is unreliable, stop substantive analysis and route validation to
  `sales-data-reconciliation`.
- Resume this workflow after the upstream skill produces validated inputs.

# Execution workflow

1. Classify the user's requested outcome.
2. Inventory available evidence, definitions, constraints, and missing inputs.
3. Validate inputs to the degree required by this skill.
4. Execute the domain-specific analysis or generation steps.
5. Separate verified facts, calculations, assumptions, and recommendations.
6. Apply the skill-specific output contract.
7. Identify the next action and any justified downstream handoff.

# Guardrails

- Never invent figures, mappings, causes, sources, or completed validations.
- Label assumptions and estimates explicitly.
- Do not silently cross into another skill's jurisdiction.
- Do not present an attractive artifact as evidence that the underlying analysis is
  correct.
- Preserve traceability from conclusions to supplied data or stated assumptions.

# Output contract

Include only sections relevant to the request, selected from:

1. Decision or executive summary
2. Evidence and detailed findings
3. Calculations, artifact, code, or workflow
4. Risks, caveats, and unresolved questions
5. Recommended actions and justified handoffs

Lead with the answer. Use tables only for genuine comparisons or structured evidence.
```

## Writing the description

The description is the routing mechanism, and it is the only part most requests will
ever be matched against. Four clauses, in order:

1. **Use when** — the trigger intents, in the user's vocabulary rather than yours. Users
   say "the numbers look off", not "reconciliation variance".
2. **Handles** — the jurisdiction this skill owns.
3. **Excludes** — the neighbouring jurisdiction most likely to be confused with it.
4. **Hands off to `target-skill` when [observable condition]** — the condition must be
   observable from the request or the data, not a judgement call.

Keep it under roughly 900 characters. Longer descriptions crowd the prompt; shorter ones
under-specify the boundary and cause misrouting.

## Boundary discipline

Before adding a skill, prove it does not already exist:

```bash
python skill-suite/scripts/validate_skills.py --overlap-only
```

If two descriptions share substantial trigger vocabulary, one of three things is true:
the skills should be merged; one should narrow its triggers and declare a handoff; or a
shared reference file should be extracted and both should point at it. Adding both and
hoping the model picks correctly is not an option — it produces contradictory answers
for the same question depending on which fires.

## Reference files

Depth belongs in `references/*.md` inside the skill directory, loaded on demand. Keep
`SKILL.md` to the routing contract and the reasoning, and push executable detail,
lookup tables and long code into references. A `SKILL.md` past roughly 250 lines is
usually carrying content that belongs in a reference.

Reference links are relative to the skill directory and are checked by the validator.

## Versioning

Versions live in `manifest.json`, never in frontmatter.

- **Patch** — wording, typos, clarification with no change to behaviour or routing.
- **Minor** — new capability inside the existing jurisdiction, or a new reference file.
- **Major** — the jurisdiction changes, a handoff is added or removed, or the output
  contract changes shape.

Bump `suite_version` when any skill version changes.
