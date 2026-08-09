# Skill gallery — MT analytics

Skills in this folder auto-activate when a request matches their description. Nothing
needs to be invoked by name, though `/skill-name` works too.

## The eleven skills and when each fires

### Reasoning and business

| Skill | Fires on | Where it lives |
|---|---|---|
| `mt-channel-analyst` | Role context: MT reporting, DMS, merchandising, contests, master data, leadership comms | personal |
| `mt-business-logic` | **Why** a number moved; root cause; "what's happening here" | personal |
| `mt-growth-opportunity` | **Where** the growth is; sizing a gap in ₹; action plan; promo ROI | this repo |
| `qbr-insight-writer` | Wording a finding for leadership / NKAM / RKAM | personal |
| `mt-deck-builder` | Deck structure, slide order, action titles, the slide scripts | this repo |

### Building things

| Skill | Fires on | Where it lives |
|---|---|---|
| `excel-automation` | Excel formulas, trackers, master files, reconciliation | personal |
| `mt-sql-analytics` | SQL queries, window functions, CTEs, staging→mart layering | this repo |
| `mt-python-toolkit` | pandas, xlsb/CSV loading, cleaning, groupby, merge, export | this repo |
| `mt-powerbi-modeling` | DAX, Power Query M, star schema, the `PowerBI/` kit, refresh | this repo |
| `mt-error-resolution` | Something is wrong with the numbers; QC; validation; debugging | this repo |

### Personal

| Skill | Fires on | Where it lives |
|---|---|---|
| `personal-effectiveness` | Learning plans, weekly planning, prioritisation, decisions, presenting, career | this repo |

"personal" = `~/.claude/skills/`, available in every project on this machine.
"this repo" = `.claude/skills/`, versioned with the code and shared with anyone who
clones it.

## How they chain

```
                  ┌─ mt-error-resolution ── is the number even right?
                  │
raw MT data ──────┼─ mt-sql-analytics / mt-python-toolkit / excel-automation / mt-powerbi-modeling
                  │        │
                  │        ▼
                  └─ mt-business-logic ──► mt-growth-opportunity ──► qbr-insight-writer ──► mt-deck-builder
                       why it moved          what it's worth          how to say it         which slide
```

Two global skills pair with these and should be loaded alongside: `dataviz` before
writing any chart code, and `pptx` for `.pptx` file mechanics.

## No-overlap rule

Each skill declares its boundaries in a "do not overlap" table at the top. If a new
skill would repeat an existing one, **extend the existing skill instead** — duplicated
guidance across two skills produces contradictory answers, which is worse than a gap.

Before adding a skill, check it is not already covered:

```bash
grep -h '^description:' .claude/skills/*/SKILL.md ~/.claude/skills/*/SKILL.md
```

## Using the same logic outside Claude Code

`reference/portable-prompts.md` holds condensed system-prompt versions of the MT skill
set for pasting into Claude Projects or ChatGPT Custom Instructions, so the same rules
apply wherever the work happens.
