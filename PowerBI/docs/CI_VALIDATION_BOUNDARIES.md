# Power BI CI Validation Boundaries

**Purpose:** state plainly what `scripts/ci/test_powerbi_model.ps1` and
`PowerBI/CI/bpa_rules.json` actually check today, and what they do not, so a
green CI run is never read as more than it is.

**Governance gap this documents:** `POWERBI_SEMANTIC_VALIDATION_NOT_EXECUTED`
— see `docs/PRODUCTION_GAP_MATRIX.md` (Addendum, 2026-09-17) for the full
gap record, impact, and closure conditions. This file is the technical
detail that gap references; that file is the governance record of it.

> **A green CI run must not be interpreted as complete Power BI
> semantic-model or business validation.**

---

## What the current CI genuinely validates

The workflow `.github/workflows/pbi-windows-ci.yml` (job "Run Headless
Tabular Editor & DAX Validation") runs `scripts/ci/test_powerbi_model.ps1`,
which performs exactly these checks, confirmed by reading the script:

| Step | What it actually does | Evidence |
|---|---|---|
| 1. Watch Folder validation | For each configured raw CSV that exists on disk, checks row count ≥ a minimum and that required column headers are present | `test_powerbi_model.ps1` Step 1 (`$watchFiles` loop) |
| 2. DAX file sanity | Counts `(` vs `)` per `.dax` file and fails on mismatch — a bracket-balance check, not a parse | `test_powerbi_model.ps1` Step 2 (`$daxFiles` loop) |
| 2. Power Query file sanity | Checks each `.pq` file's raw text contains the literal substrings `let` and `in` | `test_powerbi_model.ps1` Step 2 (`$pqFiles` loop) |
| 3–4. Tabular Editor / BPA | Logs whether `PowerBI/Model/model.bim` and `PowerBI/CI/bpa_rules.json` exist, and whether a Tabular Editor CLI is installed on the runner — **does not load a model or execute a rule** when they are absent | `test_powerbi_model.ps1` Steps 3–4 (own `Write-Host` output says so directly, e.g. "(BPA execution requires Tabular Editor + active .pbix model)") |

Separately, the repo tracks Python-side data governance (schema, baseline
invariants, dashboard sweep) through `scripts/ci_validate_datajs.py` and
`tests/dashboard_sweep.js` — those are real, executed checks, but they
validate the **HTML dashboard's `data.js`**, not the Power BI semantic
model. Do not conflate the two CI surfaces.

## What the current CI does not validate

None of the following happen today, for one structural reason: **no
`.pbip`/`.bim`/`.pbix` file is committed to this repo** (by design — see
`CLAUDE.md`, "PowerBI/ — a paste-in Power BI build kit... No `.pbix` is
committed"). Every item below requires a loaded semantic model, which
does not exist in version control:

- The semantic model has never been loaded or compiled by CI
- `PowerBI/CI/bpa_rules.json`'s six rules (`DAX_NO_UNFORMATTED_DIVIDE`,
  `FORMAT_STRING_MISSING`, `RELATIONSHIPS_BOTH_DIRECTIONS`,
  `MEASURE_DESCRIPTION_MISSING`, `COLUMN_NAMING_CONVENTION`,
  `HIERARCHY_VALIDATION`) have never been executed against a real model
- DAX measures have never been semantically evaluated (only bracket-counted)
- Relationships and model architecture (cardinality, cross-filter direction,
  star-schema shape) have never been checked
- A Power BI refresh has never been run or verified to succeed
- No KPI in the model has been reconciled against an approved Finance number
- No report has been certified for production use

## The eight validation layers, and where this repo stands on each

| Layer | What it means | Current status |
|---|---|---|
| Repository validation | Files exist, are tracked, follow naming conventions | DONE — files present, referenced in `data_source_registry.yml`/registries |
| Static DAX/PQ validation | Text-level sanity (brackets balance, `let`/`in` present) | DONE — this is what CI performs today |
| Semantic-model validation | Model loads and compiles in Tabular Editor / Power BI | NOT DONE — no `.bim`/`.pbip` committed |
| BPA validation | `bpa_rules.json` rules executed against the loaded model | NOT DONE — same blocker |
| Refresh validation | A real data refresh completes without error | NOT DONE — no model to refresh |
| KPI reconciliation | Model KPI values matched against Finance-approved control totals | NOT DONE — see `docs/PRODUCTION_GAP_MATRIX.md` GAP-10 |
| Business approval | Finance/Leadership sign-off that numbers are correct | NOT DONE — `INTERNAL_BUSINESS_CONFIRMATION_REQUIRED` |
| Production certification | All of the above complete, with retained evidence | NOT DONE |

## Why this isn't a bug

`test_powerbi_model.ps1` is not silently pretending — every step that can't
execute prints exactly why (`"(BPA execution requires Tabular Editor +
active .pbix model)"`, `"(Actual model compilation requires .bim file
present)"`). The gap is that this honest-but-limited scope was only visible
in a CI log, not written down anywhere a reviewer would find it before
trusting a green check. This file closes that gap in writing; no CI
behavior was changed to produce it.

## Related documents

- `docs/PRODUCTION_GAP_MATRIX.md` — governance record of this gap (Addendum,
  2026-09-17) and its closure conditions
- `docs/PBIP_PRODUCTION_READINESS.md`, `PowerBI/docs/Desktop_Assembly_Checklist.md`
  — the existing plan for actually assembling and validating a `.pbip` model
- `PowerBI/docs/AutomationScorecard.md` — automation coverage score, a
  related but distinct measure (breadth of authored PQ/DAX vs. depth of
  validation, which is what this file addresses)
