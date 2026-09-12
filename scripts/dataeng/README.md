# `scripts/dataeng/` — Data Engineering Skills

Reusable engines that discover, validate, reconcile and govern the MT analytics model.
Charter and rules: `.claude/agents/honasa-data-engineering.md`.

**Nothing here writes to production.** `dashboard/data.js`, `dashboard/index.html` and
`build_dashboard_data.py` are read-only to every engine — asserted by
`tests/test_dataeng.py::TestRepoSafety`.

## Run

```bash
python3 -m scripts.dataeng.cli health                  # all engines + readiness score; exits 1 on FAIL/BLOCKED
python3 -m scripts.dataeng.cli health --json           # JSON output
python3 -m scripts.dataeng.cli health --save-baseline  # write config/dataeng_baseline.json
python3 -m scripts.dataeng.cli health --regression     # CI mode: exit 1 only on NEW critical findings
python3 -m scripts.dataeng.cli seed                    # validate governed seeds
python3 -m scripts.dataeng.cli seed-list               # list all seed rows with status
python3 -m scripts.dataeng.cli seed-resolve GMV Jun-26 # resolve one metric+month from seed
python3 -m scripts.dataeng.cli seed-verify-hash <file> # verify a source file's SHA256
python3 -m scripts.dataeng.cli reconcile               # or: scan registry lineage validate quality governance
```

## Architecture

```
core.py           Finding contract, THE ONE FY RULE, month parser, loaders, IO
   │
   ├── repo_scan.py     file roles, dependency edges, dead-code signal      (Phase 1)
   ├── registry.py      metric registry + lineage, live-resolved vs data.js (Phases 2,3,7)
   ├── validate.py      schema drift, FY rule, missing months, config       (Phase 4)
   ├── quality.py       NaN, excluded brands, blank dims, movement          (Phase 5)
   ├── reconcile.py     additivity with rounding ceilings                   (Phase 8)
   ├── governance.py    decision register + production gate                 (Phase 6)
   └── seed_manager.py  governed seed validation, listing, resolution       (Operationalisation)
                              │
                           cli.py  composes findings → reports + readiness score
                                   + baseline governance + seed commands
```

Every engine is a pure function returning `list[Finding]`. No engine prints a verdict;
the CLI rolls severity up. That is what makes them independently testable and reusable
by future agents.

### The `Finding` contract

`id · skill · category · severity · summary · evidence · amount_l · location · owner ·
decision_ref · remediation`

Severity: `PASS` · `INFO` · `WARN` · `FAIL` · `BLOCKED`. Any actionable finding must
name an owner — a test enforces it.

## Generated reports → `outputs/dataeng/`

| File | Output |
|---|---|
| `repository_inventory.csv` | Repository Knowledge Graph |
| `dependency_edges.csv` | file → script dependency edges |
| `metric_registry.csv` | Metric Registry (values resolved live) |
| `data_lineage_map.csv` | Data Lineage Map (4 stages per metric) |
| `decision_register_view.csv` | Decision Register view |
| `findings.csv` | every finding from every engine |
| `health_report.json` | Repository Health + Production Readiness Score |

**These are derived artifacts.** Regenerate them; never hand-edit. They are committed so
a reviewer can diff platform health between commits.

## Two rules worth repeating

**Rounding must be proven.** `reconcile.max_rounding_l(n)` = rows × 0.005. A difference
above that ceiling is a coverage gap, not rounding. The historical 22.84 L chain
difference sat mislabelled as "allocation rounding" against a 0.23 L ceiling.

**Parse before you accuse.** A month column legitimately carries both `Apr'26` and Excel
serial `46113.0`. The first version of `_mixed_schema_guard` read the wrong column and
reported two clean files as corrupt. `core.parse_month_cell` handles both forms and
`TestMonthParser::test_serial_column_is_not_flagged` keeps that false positive dead.

## Extending

Add a check to the engine it belongs to, plus a test that fails without it. New metrics
go in `registry.METRICS` with lineage and known limitations — the registry then validates
itself against `data.js` on every run and reports drift as FAIL.

## Baseline governance

`config/dataeng_baseline.json` records all currently-accepted non-PASS findings.
CI (`--regression`) exits 1 only when a **new** FAIL or BLOCKED appears that isn't in
the baseline — so pre-existing known issues do not block every pull request.

To update the baseline after intentionally resolving (or accepting) a finding:

```bash
python3 -m scripts.dataeng.cli health --save-baseline
git add config/dataeng_baseline.json
git commit -m "chore(dataeng): update accepted-findings baseline"
```

## Seed manager

Governed seeds carry authoritative values from uncommittable source workbooks.
Pattern: `PowerBI/SeedData/Masters/FY27_Monthly_GMV_MRP.csv`.

A seed row is only used in production when `Status = AUTHORITATIVE`. Every row
must carry a `Source_SHA256` so the workbook can be identified if it reappears.
The seed manager validates this and reports FAIL/WARN findings if the contract
is broken.

```bash
python3 -m unittest discover -s tests    # 104 tests
```
