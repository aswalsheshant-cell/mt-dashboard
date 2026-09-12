---
name: honasa-data-engineering
description: |
  Principal data-engineering charter for the Honasa / Mamaearth MT Analytics platform.
  Use this skill for: repository intelligence, data lineage, metric registry, schema
  validation, data quality, cross-layer reconciliation, missing-data discovery, source
  forensics, technical debt, release readiness, production readiness score, and any
  change to the analytics model itself. Invoke BEFORE investigating a data question by
  hand -- the engines already answer most of them.
---

# Honasa MT — Data Engineering Charter

## Standing order
Do not investigate by hand what a skill can answer. If a question recurs, it belongs
in an engine, not in a transcript. Every manual forensic pass should end by leaving
behind a check that would have caught the defect automatically.

## The engines

```bash
python3 -m scripts.dataeng.cli health        # everything + readiness score (CI gate)
python3 -m scripts.dataeng.cli scan          # repository intelligence, roles, dead code
python3 -m scripts.dataeng.cli registry      # metric registry, resolved live vs data.js
python3 -m scripts.dataeng.cli lineage       # source -> transform -> output -> consumer
python3 -m scripts.dataeng.cli validate      # schema drift, FY rule, missing months, config
python3 -m scripts.dataeng.cli quality       # NaN, excluded brands, blank dims, movement
python3 -m scripts.dataeng.cli reconcile     # additivity with rounding ceilings
python3 -m scripts.dataeng.cli governance    # decision register + production gate
```

`health` exits non-zero on FAIL/BLOCKED, so it can gate a build. All reports land in
`outputs/dataeng/` and are **derived artifacts** — regenerate them, never hand-edit.

Every engine returns `Finding` objects (`scripts/dataeng/core.py`): id, skill, category,
severity, summary, evidence, amount, location, owner, decision_ref, remediation.
Severity ladder: `PASS` · `INFO` · `WARN` · `FAIL` · `BLOCKED`.

## Non-negotiable rules

**THE ONE FY RULE.** Apr–Dec of year Y → FY(Y+1); Jan–Mar of year Y → FY(Y). Always
derive from month + year via `core.fy_tag_from_ym` / `fy_tag_from_label`. Never key
off a column index or a hardcoded FY list — FY28 must appear on its own.

**Rounding is a claim that must be proven.** A component difference is rounding only
when it is ≤ the maximum theoretical rounding difference (`reconcile.max_rounding_l`:
row count × half-ulp). Everything larger is a coverage gap, missing mapping, duplicate
allocation or formula mismatch. The 22.84 L chain difference sat mislabelled as
"allocation rounding" against a 0.23 L ceiling — 99× too large.

**Blank is information.** Unmapped / blank / unallocated buckets stay visible and sized
until they reach zero. Never filter them to make a total tie.

**Negatives are real.** Returns, reversals and credits keep their sign. A chain is
retained whenever any source record exists, including net-negative ones. Dropping
net-negative rows is what made a rollup exceed its own total.

**Excluded brands** (Pure Origin, Lumineve, Staze) never enter any aggregation; records
are preserved in `PowerBI/Excluded_Data/Excluded_Brands/`.

**Bases are not interchangeable.** COGS applies to GMV/MRP; logistics applies to NSV.
MRP runs ~2.3× NSV, so a swapped base silently moves a result by that factor. Every
formula component carries an explicit `Calculation_Basis` and a blank one is a FAIL.

**Governance precedes production.** No business assumption reaches production without a
decision-register row carrying approver, date and evidence. An approval missing any of
those is not an approval. While `config/cm2_formula.csv` is `DRAFT`, every CM2 figure is
labelled **CM2 PROVISIONAL — FORMULA APPROVAL PENDING**.

## Source forensics protocol
When a value is missing, exhaust recovery before proposing estimation:

1. Tracked files → 2. git history (`git log --all --diff-filter=DR`, `git rev-list --all --objects`)
→ 3. ignored/local files → 4. referenced external locations → 5. ask for the source.

A recovered value is authoritative only when it (a) comes from a real source,
(b) uses filter logic identical to the neighbouring months, (c) reproduces a known
control total, (d) is commercially plausible, and (e) has no competing candidate.
Prove (c) numerically — the Jun-26 recovery matched a 4,167.36 L control to 0.02 L.

Estimation is a last resort, never automatic, and every estimate is labelled
**NOT FOR PRODUCTION — FINANCE APPROVAL REQUIRED**.

## Carrying values from uncommittable sources
Source workbooks are gitignored and must never be committed. When only a workbook holds
a value, record it in a governed seed with the source filename, **SHA-256**, sheet,
field, extraction rule and a **control total**, and mark it `AUTHORITATIVE`. Resolution
order is always: recomputable tracked source first, seed second. Rows not marked
`AUTHORITATIVE` are ignored, so an estimate can never silently become a base.
Pattern: `PowerBI/SeedData/Masters/FY27_Monthly_GMV_MRP.csv`.

## Safe change protocol
Before modifying anything, state: affected files · affected metrics · affected tabs ·
affected tests · risk · rollback · expected validation. Then:

1. `python3 -m scripts.dataeng.cli health` — capture the baseline
2. make the change
3. `python3 -m unittest discover -s tests`
4. `health` again and diff the findings — no new FAIL/BLOCKED
5. for a `data.js` rebuild: two consecutive builds must be **byte-identical**
6. FY25/FY26 numbers unchanged when only FY27 was intended to change

Determinism: never `hash()` (PYTHONHASHSEED randomises it per process). Use
`hashlib.sha256`. Sort with explicit keys and `kind="stable"`. Money uses `Decimal`,
rounded only for display.

## Extending the platform
Add a check to the engine it belongs to; add a test that fails without it. A new metric
goes in `registry.METRICS` with its lineage and known limitations — the registry then
validates itself against `data.js` on every run and reports drift as FAIL.

New engines follow the same contract: pure function, returns `list[Finding]`, no writes
to production paths, independently testable. `tests/test_dataeng.py` asserts that no
engine writes to `dashboard/`.

## Related skills
- `honasa-dashboard-qc-reconciliation` — release QC and PASS/WARN/FAIL/BLOCKED sweep
- `honasa-cm2-expense-classification` — CM2 taxonomy, allocation and expense governance

## Known open defects
| ID | Issue | Status |
|---|---|---|
| D1 | Is COGS inside the CM2 definition? | PENDING |
| D9 | Activate direct allocation rules | PENDING |
| D13 | `fyx_primary.FY27.mrp` understated ~9,286.58 L — no brand filter, Jun-26 absent | **RESOLVED 2026-07-24**: corrected to 31,336.79 L via `scripts/fix_d13_mrp.py`; build script fixed at line 2300 |
| CM2-CHAIN | Net-negative chains dropped from `by_chain` (`build_dashboard_data.py:1434`) | Open |
| — | `PL_Expense_Input.csv` holds 3 EXAMPLE rows; CM2 expense ratio 0.1% is not real | Open |
