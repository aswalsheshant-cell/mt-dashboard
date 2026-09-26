# AI prompt toolkit for the Mon-Wed practice days

The "Converting saved material into skill" loop in `SKILL.md` names Mon-Wed as "20
minutes a day, applied to real work data." This is the toolkit for those sessions —
nine ways to use an AI assistant (this one, or any other) to compress that 20 minutes,
each with a ready-to-paste prompt adapted to the six learning blocks already defined in
`SKILL.md`. These are prompting techniques, not a teaching engine of their own — for a
live, turn-by-turn explanation or quiz session, this skill still hands off to the host
environment's teaching capability (the `learn` skill) exactly as `SKILL.md`'s Required
handoffs section says; this toolkit is what to bring to that conversation.

| Technique | What it does | Ready-to-use prompt |
|---|---|---|
| Explain like I'm 5 | Forces a plain-language explanation before the jargon — the fastest way to catch a concept you're faking understanding of | "Explain [XLOOKUP / window functions / DAX time intelligence] like I'm 5, using an FMCG example, and give me 3 takeaways." |
| Examples & analogies | Anchors a new concept to something already familiar — a chain, a distributor, a P&L line | "Give 3 analogies for [SQL joins / Power Query merge]: one from Modern Trade billing, one from everyday life, one visual." |
| Motivation & purpose | Ties the technique to a real week-1 output so the practice loop doesn't stall on "why bother" | "Show why [pandas groupby] matters for closing the monthly chain report faster, and turn that into this week's 7-day plan." |
| Role-play practice | Rehearsal with feedback, not just reading — useful for the parts of a block that are judgment, not syntax | "Act as a reviewer checking my DAX measure for [YTD sales]; run a scenario, then critique my answer and suggest improvements." |
| Study plan (milestones) | Turns "learn SQL" into the dated, checkpointed plan `SKILL.md` already requires — use this to generate the week-by-week detail under a block | "Create a 2-week plan for [window functions] with daily tasks, milestones, and a Friday checkpoint quiz." |
| Quiz & feedback loop | Retrieval practice — the single highest-leverage technique for making a technique stick past Friday | "Quiz me on [Power BI time intelligence] (10 questions). After each answer, explain and give a follow-up mini-question." |
| Mind map the domain | Surfaces the prerequisites and gaps in a block before you start — worth doing on Monday, not after struggling on Wednesday | "Create a mind map for [pandas]: pillars -> subtopics -> key terms; note prerequisites I'm missing." |
| Expert roundtable | Compares trade-offs when a block has more than one right answer (e.g. Power Query vs. a Python script for the same clean-up) | "Simulate 3 experts debating [Power Query vs. pandas for this clean-up] (pragmatist, skeptic, specialist) and summarize consensus + risks." |
| Mnemonics | Cheap insurance against forgetting a short, order-dependent sequence (a DAX pattern, a QC checklist, a join-type list) | "Create 5 mnemonics for [the CM2 reconciliation checklist] and a 60-second recall drill I can repeat daily." |

## How this fits the existing loop, block by block

Pick one or two techniques per day — running all nine on one topic is decoration, not
practice, the same failure mode `SKILL.md`'s Thursday/Friday steps already guard
against (a real output, then five lines of write-up, beats a pile of notes).

| Block | Where a technique pays off most |
|---|---|
| 1. Excel | Mind map the domain (SUMIFS/XLOOKUP/Power Query prerequisites), then Examples & analogies for whichever formula is unfamiliar |
| 2. SQL | Study plan for the 2-week arc, Quiz & feedback loop daily, Expert roundtable when two query shapes could both work |
| 3. pandas | Explain like I'm 5 for the first read of unfamiliar syntax, then Role-play practice reviewing your own script |
| 4. Power BI | Mnemonics for DAX time-intelligence patterns, Expert roundtable for a modeling choice with real trade-offs |
| 5. Visualisation | Expert roundtable (pragmatist vs. specialist) on chart choice; Motivation & purpose to tie it to the QBR deck it will appear in |
| 6. Automation/QC | Mnemonics for the checklist itself; Quiz & feedback loop to rehearse catching the failure modes before they hit real data |

## Guardrail specific to this toolkit

A technique that produces a fluent-sounding explanation is not the same as the
technique working on real data — `SKILL.md`'s Thursday step (produce one real output
using it, on real work data) is still the actual test. Use this toolkit to compress the
Mon-Wed ramp-up, never to replace the Thursday output.
