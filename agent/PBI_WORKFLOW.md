# Power BI Workflow Controller (Module 2)

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

Steps marked *not yet implemented* exist in the state machine (so
`status`/`resume` always show the full 16-step picture) but have no
registered command yet — invoking them isn't possible until a follow-up
build adds `pbi_powerquery.py` / `pbi_blueprint.py` / `pbi_theme.py` /
`pbi_docs.py` / `pbi_package.py`, each following the same pattern as
`pbi_dataset.py`. They are **not silently claimed complete**.

Statuses: `Not Started` · `Ready` · `Running` · `Completed` ·
`Completed with Warning` · `Manual Action Required` · `Approval Required` ·
`Blocked` · `Failed` · `Skipped with Approval`.

## Commands

```bash
python -m mtagent pbi list                                   # every registered command + classification
python -m mtagent pbi build-dataset [--raw-dir D] [--masters-dir D]
python -m mtagent pbi generate-dax [--dax-dir D]
python -m mtagent pbi reconcile-model --source <csv> --build-dir <agent/pbi_build/...>
python -m mtagent pbi status [--json]
python -m mtagent pbi next-manual-step [--json]
python -m mtagent pbi resume [--json]
python -m mtagent pbi mark-complete --step-id <id> --evidence-kind <kind> --evidence <text-or-path>
```

`--evidence-kind` is one of `screenshot` / `metadata_export` / `query_output`
/ `file_output` / `user_confirmation`. `mark-complete` refuses to complete a
step when the evidence itself contains words like "error", "failed",
"broken" or "#error" — fix the underlying problem and resupply clean
evidence instead.

### `build-dataset` — steps 1–4

Reads the latest `offtake_store_article_*.csv` under
`PowerBI/RawDataFolders/Offtake_Monthly/` (real, committed data — no
fabrication), validates required columns, applies `ChainMaster.csv` /
`ArticleMaster.csv` mappings (TRIM+UPPER+alnum-only normalized key
matching, so `D-Mart` and `Dmart` match but a genuine gap like `Frankros`
vs. `Frank Ross` is correctly reported, not silently forced), and writes:

`Fact_OfftakeSales.csv`, `Dim_Date.csv`, `Dim_Chain.csv`, `Dim_Article.csv`,
`Mapping_Exception_Report.csv`, `Data_Quality_Report.csv`,
`Source_Reconciliation_Report.csv`, `Dataset_Build_Log.json` — all under
`agent/pbi_build/<FY>_<Month>/` (gitignored).

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
totals against the built `Fact_OfftakeSales.csv`. Tolerance is
configurable (`pbi_reconciliation_tolerance_pct`, default 0.5%). No
mismatch is ever hidden — every metric gets a row, `PASS`/`FAIL`/`INFO`.

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

**`Mapping_Exception_Report.csv`** — a real gap this run found: the source
uses the bare chain label `Reliance`, but `ChainMaster.csv` only has
`Reliance Retail` / `Azorte` mapping to Account `Reliance` — no exact
match, so 24,636 rows are correctly flagged rather than silently dropped
or force-matched:
```
exception_type,value,row_count,nsv_impact
unmapped_chain,Reliance,24636,508.18
unmapped_chain,H&G,6735,87.44
```

**`Source_To_Model_Reconciliation_Report.csv`** (from `reconcile-model`):
```
metric,source_value,model_value,absolute_variance,variance_pct,status,likely_cause,recommended_action
nsv_total,4527.606,3301.0707,1226.5353,27.09,FAIL,"unmapped chain/article rows, blank-key rows dropped, or a build-step aggregation bug",investigate before marking this build step complete
distinct_chains,24,16,8,33.333,FAIL,chain name not matching ChainMaster.csv after normalization -- check Mapping_Exception_Report,investigate before marking this build step complete
```

That FAIL is real and expected on this data: `ArticleMaster.csv` is a
13-row *seed* master (not the production article master), so most
article-level mapping is expected to miss until the real master is
supplied via `--masters-dir`. Chain-level mapping (45 chains in
`ChainMaster.csv`) is representative and the `Reliance` gap above is a
genuine finding worth fixing in the master, not a bug in the agent.

**`pbi status --json`** (abridged):
```json
{
  "completion_pct": 37.5,
  "current_phase": "Generate Power Query scripts.",
  "manual_steps_pending": ["Guide the user through manual Power BI Desktop actions.", "..."],
  "warnings": ["6 unmapped chain(s), 10376 blank-key row(s) dropped, NSV reconciliation variance 1226.535802"]
}
```

## Limitations

The agent can automatically clean/transform data, build datasets, audit
DAX coverage, and reconcile source-to-model. It **cannot** reliably open
Power BI Desktop, import files through the GUI, click Apply Changes, drag
fields onto a canvas, position visuals, configure bookmarks, publish, or
handle authentication/gateway prompts — those remain steps 11/12/14 and
are always reported as `Manual Action Required`, one step at a time, never
claimed done without evidence via `mark-complete`.
