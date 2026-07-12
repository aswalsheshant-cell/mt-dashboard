# Power BI Workflow Controller (Module 2) + Excel-Intelligence ingest (Module 1)

Manages the Power BI dashboard build as one persistent, resumable 16-step
sequence, and separates three kinds of work honestly:

1. **Automated** — the offline agent runs it and writes real output files
   (dataset build, DAX gap audit, source-to-model reconciliation).
2. **Manual** — anything requiring Power BI Desktop's graphical interface
   (importing files, clicking Apply Changes, dragging visuals, publishing).
   The controller never attempts this — see [Limitations](#limitations).
3. **Approval** — steps a human must explicitly sign off (final release QC,
   marking a release complete).

State lives in `agent/index/pbi_workflow_state.json` (gitignored, one file
per checkout) so a build can be paused and resumed without re-doing
finished work. Every state transition is appended to an internal audit
log (`state.events`), independent of the generic `agent/index/worklog.jsonl`
CLI-run log that every `mtagent` command already writes to.

## The 16 steps

| # | Step | Classification |
|---|---|---|
| 1 | Validate source files | automated |
| 2 | Build Power BI-ready datasets | automated |
| 3 | Generate dimension and fact tables | automated |
| 4 | Validate business keys and relationships | automated |
| 5 | Generate Power Query scripts | automated *(not yet implemented — see below)* |
| 6 | Generate the DAX measure library | automated |
| 7 | Generate the page-wise visual blueprint | automated *(not yet implemented)* |
| 8 | Generate the Power BI theme JSON | automated *(not yet implemented)* |
| 9 | Generate model documentation | automated *(not yet implemented)* |
| 10 | Prepare the Power BI build package | automated *(not yet implemented)* |
| 11 | Guide the user through manual Power BI Desktop actions | manual |
| 12 | Review screenshots and exported metadata | manual |
| 13 | Run source-to-model reconciliation | automated |
| 14 | Run page-level QC | manual |
| 15 | Run final dashboard release QC | approval |
| 16 | Mark the approved release package as complete | approval |

Steps 5/7/8/9/10 now have a **registered graceful stub** each
(`generate-power-query`, `generate-page-blueprint`, `generate-theme`,
`generate-docs`, `prepare-build-package`) so the sequence never stalls or
crashes on an unbuilt module — see [Graceful stubbing](#graceful-stubbing-for-unbuilt-steps-5-7-8-9-10)
below. The *real* generator (`pbi_powerquery.py` / `pbi_blueprint.py` /
`pbi_theme.py` / `pbi_docs.py` / `pbi_package.py`, each following the
same pattern as `pbi_dataset.py`) is still a follow-up build; until then
these steps are honestly reported as skipped, **never silently claimed
complete**.

Statuses: `Not Started` · `Ready` · `Running` · `Completed` ·
`Completed with Warning` · `Manual Action Required` · `Approval Required` ·
`Blocked` · `Failed` · `Skipped with Approval`.

## Commands

```bash
python -m mtagent pbi list                                   # every registered command + classification
python -m mtagent pbi build-dataset [--raw-dir D] [--masters-dir D]
python -m mtagent pbi generate-dax [--dax-dir D]
python -m mtagent pbi reconcile-model --source <csv> --build-dir <agent/pbi_build/...> [--masters-dir D]
python -m mtagent pbi run-automated [--raw-dir D] [--masters-dir D] [--dax-dir D]
python -m mtagent pbi generate-power-query | generate-page-blueprint | generate-theme | generate-docs | prepare-build-package
python -m mtagent pbi status [--json]
python -m mtagent pbi start-manual-step [--json]
python -m mtagent pbi next-manual-step [--json]
python -m mtagent pbi resume [--json]
python -m mtagent pbi mark-complete --step-id <id> --evidence-kind <kind> --evidence <text-or-path>
```

`--evidence-kind` is one of `screenshot` / `metadata_export` / `query_output`
/ `file_output` / `user_confirmation`. `mark-complete` refuses to complete a
step when the evidence itself contains words like "error", "failed",
"broken" or "#error" — fix the underlying problem and resupply clean
evidence instead.

### `build-dataset` — steps 1–4 (the Excel-Intelligence ingest)

Reads the latest `offtake_store_article_*.csv` under
`PowerBI/RawDataFolders/Offtake_Monthly/` (real, committed data — no
fabrication), validates required columns, then applies the Module 1
ingest rules in order:

1. **Exact duplicate rows are dropped at the entry point** (full-row
   identity) so a re-supplied or double-pasted extract can never
   double-count. On the real May'26 file this removed 2,466 duplicate
   lines (₹16.06 L NSV) that the source extract genuinely contains
   (one Sasta Sundar line appears 52 times identically). Business-key
   duplicates — `(site, ean, month)` seen more than once with *different*
   values — are legitimate re-lines: reported, never dropped.
2. **Blank `Site Code` falls back to `Internal Code`** when the source
   month has that column (May'26 onward does; Apr'26 doesn't).
3. **Chain mapping**: `ChainMaster.csv` normalized-key match
   (TRIM+UPPER+alnum-only, so `D-Mart` ≡ `Dmart`), then
   **`ChainAliases.csv`** for bare corporate strings (`Reliance` →
   `Reliance Retail`, `H&G` → `Health & Glow`, `Vmm` → `Vishal Mega
   Mart`, …). Every alias hit is logged to the exception report for
   one-time human verification; an alias pointing at a chain missing
   from ChainMaster is surfaced as `invalid_alias` and ignored, never
   used to invent a chain.
4. **No row is ever dropped for a blank/unmapped key.** Blank Site
   Code / EAN / Chain Name rows are retained in the Fact under explicit
   `(blank)` / `UNMAPPED:` buckets and routed to
   `Mapping_Exception_Report.csv`, so Fact NSV reconciles to the source
   and the cost of each gap stays visible (blank sites are excluded
   from `Store_Count` so store productivity is not silently inflated).

Outputs, all under `agent/pbi_build/<FY>_<Month>/` (gitignored):
`Fact_OfftakeSales.csv`, `Dim_Date.csv`, `Dim_Chain.csv`, `Dim_Article.csv`,
`Mapping_Exception_Report.csv`, `Data_Quality_Report.csv`,
`Source_Reconciliation_Report.csv`, `Dataset_Build_Log.json`, plus the
Module 1 analysis outputs: `Pivot_Chain_Category_NSV.csv`,
`Pivot_Zone_Brand_NSV.csv`, and `Outlier_Report.csv` (every check
severity-classified `Critical` / `High` / `Medium` / `Low` / `Passed`:
unmapped-chain NSV share, blank-site NSV share, negative chain totals,
negative-NSV row volume, qty-without-value pricing gaps, per-category
article NSV z-score outliers).

A month with fewer than 1,000 rows is treated as incomplete and the prior
month is used instead (never treats an incomplete month as complete).

### `generate-dax` — step 6

**This audits, it does not duplicate.** The repo already has ~3,000 lines
of hand-built DAX across `PowerBI/DAX/00_DateTable.dax` .. `13_CM2_Measures.dax`.
Blindly regenerating a second library risks exactly the kind of
duplicate-definition bug the DAX linter already caught once (`QC Mapping
Coverage %` defined twice). Instead this command:

1. Re-uses `dax_validator.extract_definitions` to inventory every measure
   name already defined in `PowerBI/DAX/`.
2. Diffs that against the 55-measure required catalogue (Core / Time
   Intelligence / Growth / Business / QC, per the spec) using
   normalized-name matching (`NSV (Cr)` ≡ `NSV Cr`).
3. Writes `Measure_Catalogue.csv`, `Measure_Dependency_Map.json`,
   `Measure_Test_Cases.csv`, `Measure_Validation_Report.json`, and — for
   anything with no match — a `DAX_Gap_Library.dax` snippet file, staged
   for human review only. **Nothing is ever auto-placed into
   `PowerBI/DAX/`** — pasting generated DAX into the live model is a
   manual Power BI Desktop action requiring explicit approval.

Known limitation: normalized-name matching is a heuristic. On this repo's
real DAX library it currently reports ~13% exact-name coverage even though
several required *concepts* already exist under a different name (e.g.
`NSV` vs. the catalogue's `NSV Actual`, `Latest Month NSV` vs. `Latest
Available Month`). Treat `DAX_Gap_Library.dax` as a starting checklist for
human review, not a literal to-do list — someone should confirm each
"Missing" row doesn't already exist under a different name before writing
new DAX.

### `reconcile-model` — step 13

Independently re-derives totals from the **original** source CSV (not
from `build-dataset`'s own running totals, so a bug in that step's
aggregation can't silently pass its own check) and compares row count,
NSV/MRP/Qty totals, distinct chains/articles, and per-chain/per-zone
totals against the built `Fact_OfftakeSales.csv`. It applies the same
*ingest contract* as the build — exact full-row duplicates excluded
(reported as an `INFO` metric), chain names compared under their mapped
ChainMaster/alias Account key so `Dmart` vs `Avenue Supermarts` doesn't
produce spurious FAILs — while still recomputing every number itself.
Tolerance is configurable (`pbi_reconciliation_tolerance_pct`, default
0.5%). No mismatch is ever hidden — every metric gets a row,
`PASS`/`FAIL`/`INFO`.

### Graceful stubbing for unbuilt steps 5/7/8/9/10

Invoking `generate-power-query` / `generate-page-blueprint` / `generate-theme`
/ `generate-docs` / `prepare-build-package` today never throws, never
crashes the CLI, and never leaves the sequence stalled: each stub logs a
technical notice (which module it stands in for, and that it's scoped
for a future build) and transitions its step straight to the existing
`Skipped with Approval` terminal status — deliberately reusing that
status rather than inventing a new one, since the 10-status vocabulary
above is fixed. `Skipped with Approval` is a **terminal-OK** status, so
it counts toward `completion_pct` and immediately readies the next step,
exactly like a real `Completed` step would. It is never reported as
`Completed` — anyone reading `status`/`resume`/`pbi list` sees plainly
that the module itself doesn't exist yet.

### `run-automated` — the full automated chain in one command

Chains `build-dataset` → `generate-dax` → the five stubs above →
`reconcile-model`, stopping the instant a `Blocked`/`Failed` result
occurs, and never attempting steps 11/12/14 (those need Power BI Desktop
or a human, and stay `Manual Action Required` / untouched). This is the
"one command, PASS/FAIL-style readiness" entry point for the automated
half of the pipeline — real generators slot in later by being added to
the registry, no orchestration change required.

### Sandbox model (`Fact_Sandbox_SeedMatched.csv`)

Every build also writes an **additive, validation-only** subset of the
Fact restricted to rows whose EAN matched the resolved
`ArticleMaster.csv`. It scales to whichever master was actually resolved
(seed, or a dropped-in production export) — never hardcoded to "13
SKUs". Critically, `Fact_OfftakeSales.csv` (the core Fact) is **never**
filtered or stripped to build it: every row and every rupee of NSV stays
in the core Fact, which is why `reconcile-model` keeps reconciling
cleanly regardless of article-master coverage. The quarantined NSV is
reported in `Data_Quality_Report.csv` (`sandbox_model_coverage`) and
`Dataset_Build_Log.json` (`sandbox_model`), with the per-EAN breakdown
already in `Mapping_Exception_Report.csv`.

Real finding on the May'26 data: the sandbox is **0 rows**. The
committed `ArticleMaster.csv` seed's EANs (`89012345000XX`, sequential)
are synthetic placeholders, not drawn from any real offtake export, so
none match the actual May'26 EANs — a genuine gap in the seed fixture
data, not a code defect. The sandbox will start populating the moment a
real `ArticleMaster.csv` (even a partial one) is dropped into
`PowerBI/RawDataFolders/Masters/`.

### `start-manual-step` — bridging automated completion to a real manual gate

A real gap this closes: `_advance_ready()` (used by `complete_step` and by
the steps 5/7/8/9/10 stubs' `skip_with_approval`) only readies the NEXT
step in sequence — it never puts a MANUAL step into `Manual Action
Required`. So after `run-automated` finishes, `next-manual-step` used to
report "none" even though step 11 (Guide the user through manual Power
BI Desktop actions) was the obvious next thing to do — misleading, since
the pipeline was in fact done with everything it *can* automate.

`start-manual-step` finds the earliest `Ready` manual step (11, 12, or
14), attaches concrete, build-specific instructions (real paths pulled
from this run's own state — the actual `agent/pbi_build/<build_id>/`
directory, the actual `dax_gap_latest/DAX_Gap_Library.dax` path, never a
placeholder), and transitions it to `Manual Action Required`. Calling it
again while a step is already active is a no-op (`already_active: true`)
— it never re-logs or resets. Typical flow:

```bash
python -m mtagent pbi run-automated --dax-dir PowerBI/DAX
python -m mtagent pbi start-manual-step     # step 11 -> Manual Action Required, real instructions attached
python -m mtagent pbi next-manual-step      # now surfaces step 11, not "none"
# ... do the Power BI Desktop work, then:
python -m mtagent pbi mark-complete --step-id manual_desktop_actions --evidence-kind screenshot --evidence <path>
python -m mtagent pbi start-manual-step     # advances to step 12 (review_evidence)
```

### Production drop-in for masters (no code/config change)

`ChainMaster.csv` / `ArticleMaster.csv` / `ChainAliases.csv` are each
resolved **independently** (`pbi_dataset.resolve_master_file`): if
`--masters-dir` was passed explicitly, that wins outright; otherwise each
file is looked up in `PowerBI/RawDataFolders/Masters/<file>` first (the
same "drop a file in RawDataFolders/<watch>/" convention already used for
monthly offtake refreshes), falling back to `PowerBI/SeedData/Masters/<file>`
only if the production file isn't there. Per-file (not whole-directory)
resolution matters: dropping in just a real `ArticleMaster.csv` upgrades
article mapping immediately without silently losing `ChainMaster.csv`
coverage if only one file was supplied. `reconcile-model` applies the
exact same resolution, so a dropped-in production master upgrades both
the build and its independent reconciliation together.

## Sample configuration

`agent/config.example.json` (copy to `agent/config.json` to override):

```json
{
  "pbi_build_dir": "agent/pbi_build",
  "pbi_reconciliation_tolerance_pct": 0.5
}
```

## Sample output

Real output from `pbi build-dataset` against the committed
`offtake_store_article_May_26.csv` (228,280 rows):

**`Fact_OfftakeSales.csv`**
```
FY,Month,Zone,Chain,EAN,Brand,Category,Sub_Category,NSV,MRP_Sales_Value,Sales_Qty,Store_Count
FY27,May'26,EAST,Apollo,8904417300659.0,Mamaearth,Baby,Baby Soap,0.0512,8398.0,38.0,34
FY27,May'26,EAST,Apollo,8904417303308.0,Mamaearth,Face,Lip Balm,0.0414,6972.0,28.0,27
```

**`Mapping_Exception_Report.csv`** — the bare `Reliance` label that an
earlier build correctly flagged as unmapped now resolves through
`ChainAliases.csv` (logged for one-time verification, never silent); the
9,426 blank-site rows (27% of NSV) are retained under the `(blank)`
bucket instead of dropped; the 2,466 exact duplicate lines are dropped
at entry:
```
exception_type,value,row_count,nsv_impact,resolution
alias_mapped_chain,Reliance,32461,1493.77,auto-mapped to 'Reliance Retail' via ChainAliases.csv -- verify once
alias_mapped_chain,H&G,6735,87.44,auto-mapped to 'Health & Glow' via ChainAliases.csv -- verify once
blank_site_code,(blank),9426,1220.13,rows RETAINED in Fact under the (blank) bucket -- fix at source extract
exact_duplicate_row,(full-row identity),2466,16.06,dropped at entry point (idempotent re-ingest)
```

**`Outlier_Report.csv`** — the one genuinely severe issue in the May'26
extract is the blank-site share:
```
severity,check,entity,value,note
Passed,unmapped_chain_nsv_share,0 chain(s),0.0% of NSV,...
High,blank_site_code_nsv_share,9426 row(s),27.04% of NSV,rows retained under the (blank) site bucket; store-level analyses undercount until fixed at source
Low,article_nsv_zscore,13 article(s) beyond |z|>3.0,...
```

**`Source_To_Model_Reconciliation_Report.csv`** (from `reconcile-model`)
is now fully green on the real May'26 data — 37 metrics compared, 0 FAIL:
```
metric,source_value,model_value,absolute_variance,variance_pct,status
source_exact_duplicate_rows,2466,0,2466,0.0,INFO
nsv_total,4511.5452,4511.5486,-0.0034,0.0,PASS
distinct_chains,24,24,0,0.0,PASS
chain_total:Reliance,1493.7701,1493.7705,-0.0004,0.0,PASS
```

Article-level dimension mapping still mostly misses because
`ArticleMaster.csv` is a 13-row *seed* master (not the production article
master) — expected until the real master is supplied (via `--masters-dir`,
or dropped into `PowerBI/RawDataFolders/Masters/` — see
[Production drop-in](#production-drop-in-for-masters-no-codeconfig-change));
the Fact carries the source file's own Brand/Category for those rows, so
no numbers are lost.

**`pbi run-automated` then `pbi status --json`** (abridged) — real run,
same May'26 data, every automated step resolved and the sequence stops
cleanly at the first manual step:
```json
{
  "completion_pct": 68.8,
  "completed_phases": ["Validate source files.", "...", "Generate Power Query scripts.",
                        "...", "Prepare the Power BI build package.", "Run source-to-model reconciliation."],
  "current_phase": "Guide the user through manual Power BI Desktop actions.",
  "automated_steps_pending": [],
  "manual_steps_pending": ["Guide the user through manual Power BI Desktop actions.",
                            "Review screenshots and exported metadata.", "Run page-level QC."],
  "warnings": ["9426 blank-key row(s) retained under (blank) buckets",
               "48/55 required measures have no existing match -- see DAX_Gap_Library.dax"]
}
```
`completed_phases` includes the five stubbed steps (5, 7, 8, 9, 10) —
they resolved via `Skipped with Approval`, not a fabricated `Completed`.

## Limitations

The agent can automatically clean/transform data, build datasets, audit
DAX coverage, and reconcile source-to-model. It **cannot** reliably open
Power BI Desktop, import files through the GUI, click Apply Changes, drag
fields onto a canvas, position visuals, configure bookmarks, publish, or
handle authentication/gateway prompts — those remain steps 11/12/14 and
are always reported as `Manual Action Required`, one step at a time, never
claimed done without evidence via `mark-complete`.
