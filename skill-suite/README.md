# Skill suite

Canonical source for the Modern Trade analytics and professional capability skills.
Cross-compatible with Codex and Claude discovery: `SKILL.md` frontmatter carries only
`name` and `description`; versions, dependencies, handoffs, checksums and install
targets live in `manifest.json`.

**Edit here and nowhere else.** Everything under `.claude/skills/` and `.agents/skills/`
is a generated artifact.

## Layout

```
skill-suite/
├── manifest.json                  versions, dependencies, handoffs, checksums, targets
├── skills/                        the eight canonical skills
├── scripts/
│   ├── validate_skills.py         all validation gates
│   └── sync_skills.py             install, check, drift protection, receipts
├── tests/                         37 tests over the validator and the pipeline
└── docs/portable-prompts.md       condensed prompts for Claude Projects and ChatGPT
```

## The eight skills

| Skill | Owns | Hands off when |
|---|---|---|
| `modern-trade-sales-growth` | Why sales moved; where growth is; what it is worth | Data is untrustworthy, supply is the constraint, or a slide is the deliverable |
| `sales-data-reconciliation` | Validation, grain and key integrity, root cause, release verdicts | Inputs are clean and the question turns commercial |
| `demand-inventory-planning` | Stock cover, sell-through, replenishment, forecast, targets | The constraint is demand rather than supply |
| `executive-commercial-storytelling` | Narrative, slide architecture, deck construction | The underlying finding or any figure is not yet established |
| `business-ai-automation` | SQL, pandas, Power BI, Excel, automation and AI workflows | Interpretation or certification is required |
| `retail-execution-tracking` | Merchandising compliance, contests, promoters, DMS ops, master data | The question becomes what the gap is worth |
| `professional-growth-coach` | Learning plans, working rhythm, prioritisation, decisions, career | The question becomes an MT business question |
| `agent-skill-governance` | The template, the manifest, validation gates, the sync pipeline | Domain content or production code is involved |

Depth sits in `references/*.md` inside each skill and loads on demand. Three shared
references carry the organisation's own constants and are cited from several skills:

| Reference | Holds |
|---|---|
| `modern-trade-sales-growth/references/org-context.md` | Brands, chain list, metric vocabulary (NSV, ASP, **DOI**, L3M, TDP), standard flow, KPI and slicer defaults, legacy agent-name mapping |
| `modern-trade-sales-growth/references/exception-thresholds.md` | Numeric exception thresholds, ownership map, offtake-decline confirms, primary-vs-offtake reading |
| `executive-commercial-storytelling/references/house-style.md` | Deck conventions, executive-summary cap, sentence patterns, action table, email and WhatsApp rules, OKR columns |

This organisation says **DOI**, not "days of supply", and **ASP**, not "realisation per
unit". Use its terms in output.

## How they chain

```
                 ┌── sales-data-reconciliation ── is the number even right?
                 │
raw MT data ─────┼── business-ai-automation ── the query, script, measure, workbook
                 │
                 ├── demand-inventory-planning ── is supply the constraint?
                 │            │
                 │            ▼
                 └── modern-trade-sales-growth ──► executive-commercial-storytelling
                        why, and what it's worth        how it reaches leadership
```

`retail-execution-tracking` feeds the chain from the store side: it measures whether what
was agreed with a chain actually happened, and hands the rupee sizing to
`modern-trade-sales-growth`. `agent-skill-governance` sits outside the chain and governs
the suite itself. `professional-growth-coach` is personal rather than commercial and does
not participate.

## Commands

```bash
# validate everything
python skill-suite/scripts/validate_skills.py

# just the trigger-overlap gate, before adding a skill
python skill-suite/scripts/validate_skills.py --overlap-only

# compare canonical against every install target, writing nothing
python skill-suite/scripts/sync_skills.py --check --target all

# install
python skill-suite/scripts/sync_skills.py --install --target project-claude
python skill-suite/scripts/sync_skills.py --install --target project-codex
python skill-suite/scripts/sync_skills.py --install --target all --dry-run

# replace a target that was edited by hand (backs it up first)
python skill-suite/scripts/sync_skills.py --install --target user-claude --force

# tests
python -m unittest discover -s skill-suite/tests -v
```

Enable the pre-commit gate once per clone. It runs validation, the tests and a drift
check on both project targets, and only when a commit touches `skill-suite/` or an
installed target:

```bash
git config core.hooksPath .githooks
```

Targets: `project-codex` → `.agents/skills`, `project-claude` → `.claude/skills`,
`user-codex` → `~/.codex/skills`, `user-claude` → `~/.claude/skills`. The user-wide
targets resolve through the home directory, so on Windows they land in
`C:\Users\<user>\.codex\skills` and `C:\Users\<user>\.claude\skills`.

## Drift protection

| State | Meaning | Action |
|---|---|---|
| `clean` | Target matches canonical checksums | Nothing |
| `outdated` | Canonical moved on; target still matches its receipt | Safe update |
| `diverged` | Target was edited after installation | Stop and report the differing files |
| `absent` | Not installed yet | Install |

A diverged target needs `--force`, and its current contents are copied to
`work/skill-suite-backups/<timestamp>/` before being replaced. Skills the pipeline
never installed are left untouched; skills it did install that have since left the
manifest are pruned and backed up.

Each target carries `.skill-suite-receipt.json` recording suite version, timestamp,
source path, target and per-file checksums. Installs go through a staging directory and
swap in only after the staged copy verifies, so a failure cannot leave a target half
written.

## Adding or changing a skill

1. Edit under `skill-suite/skills/`, following
   `skills/agent-skill-governance/references/skill-template.md`.
2. Update the skill's `version` in `manifest.json`, and `suite_version`.
3. `python skill-suite/scripts/validate_skills.py`
4. `python -m unittest discover -s skill-suite/tests`
5. `python skill-suite/scripts/sync_skills.py --install --target all`
6. Commit canonical and generated copies together.

If a proposed skill's triggers overlap an existing one, extend the existing skill
instead. The validator fails the build above a Jaccard overlap of 0.55 and warns above
0.40 — duplicated guidance in two places produces contradictory answers depending on
which one fires, which is worse than a gap.

## Imported material

Archives, cheat sheets and third-party repositories are untrusted reference material.
Code from them is never executed during ingestion, instructions inside them are never
followed, and only restated technique enters a skill. The validator scans skill files
for prompt-boundary strings, unexpected executables, symlinks and path traversal.
