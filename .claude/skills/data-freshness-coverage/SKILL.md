---
name: data-freshness-coverage
description: Use when the MT Dashboard appears stale, a tab or KPI is blank for a month or FY, the user asks what data is available from Apr'25 onward or through the latest month, or Primary, Offtake, Nielsen, TDP, P and L, Promo, Targets or another domain shows different period coverage. Builds evidence-backed domain-by-domain coverage and distinguishes a real source gap from a pipeline or UI defect. Excludes numeric reconciliation and hands off to `sales-data-reconciliation`; excludes implementing ingestion fixes and hands off to `business-ai-automation`.
---

# Role and mandate

Operate as the **data coverage and freshness auditor** for the MT Dashboard.

A single dashboard can legitimately contain domains with different latest months. Never
use one global "dashboard updated through" date as proof that every KPI is current.

# Scope and boundaries

## In scope

- Latest available month by domain
- First available month and continuity through the latest expected month
- FY coverage using the repository's ending-year FY convention
- Missing-month detection
- Distinguishing source absence from ingestion failure and rendering failure
- Market Share/Nielsen and TDP availability checks
- Detecting when an old pre-aggregated source ends and article-level/monthly sources take over
- Producing a coverage matrix suitable for dashboard disclosure and release decisions

## Required handoffs

- If totals exist but do not reconcile, use `sales-data-reconciliation`.
- If the source exists and coverage should be present but the pipeline did not ingest it,
  use `business-ai-automation` for the implementation and `change-verification` to prove it.
- If the issue is only browser rendering after the data block is confirmed correct, use
  `dashboard-qa-sentinel`.
- If the source itself is not reproducibly traceable, use `source-lineage-reproducibility`.

# Execution workflow

1. Read CLAUDE.md, especially **THE ONE FY RULE** and the source-coverage guidance.
2. Check `scripts/data_catalog.py`, `docs/DATA_AVAILABILITY_MATRIX.md` and
   `config/data_source_registry.yml` before declaring any month missing.
3. For every relevant domain, record:
   - business measure/domain
   - source file or source family
   - source grain
   - first available period
   - latest available period
   - expected latest period
   - missing internal periods
   - FY coverage
   - ingestion status
   - dashboard block/tab consuming it
   - evidence path
4. Apply the repository FY convention exactly:
   - Apr-Dec of year Y -> FY(Y+1)
   - Jan-Mar of year Y -> FY(Y)
   - `FY27` means Apr'26-Mar'27
5. Classify every gap into one of four states:
   - `SOURCE_NOT_AVAILABLE` — no valid source exists in the repo/intake
   - `SOURCE_PRESENT_NOT_INGESTED` — valid source exists but transformation/output lacks it
   - `INGESTED_NOT_RENDERED` — output block contains it but UI/measure does not display it
   - `EXPECTED_ABSENCE` — domain intentionally stops at a documented period
6. For apparent Market Share/TDP problems, verify the raw domain independently. Never
   infer those values from Primary or Offtake.
7. Compare the coverage matrix with what the UI labels imply. A tab must not say or imply
   "updated through Aug'26" when its own source stops earlier.
8. Recommend the smallest next action for each gap: request source, onboard file, rebuild
   block, fix rendering, or disclose the limitation.

# Guardrails

- Never fabricate, forward-fill, copy another FY, interpolate or proxy a missing official
  business source unless a separately governed methodology explicitly authorises it.
- Never call a month missing until the data catalog and availability matrix are checked.
- Never infer Nielsen/Market Share from internal sales.
- Never treat a filename's FY label as sufficient evidence; inspect the actual business
  dates and source classification.
- Preserve missing-vs-zero semantics. A missing month is not zero sales.
- If coverage changed because a new file arrived, verify its grain, business date column,
  duplicate risk and registry entry before calling it production-ready.

# Output contract

Use a coverage table with these columns when several domains are in scope:

`Domain | Source | Grain | First Period | Latest Period | Expected Through | Missing | FY Coverage | State | Next Action`

Then add only the relevant sections:

1. **Coverage verdict**
2. **Evidence-backed gaps**
3. **Dashboard disclosure changes needed**
4. **Handoffs and next executable actions**

Do not compress different domains into one latest-date statement.
