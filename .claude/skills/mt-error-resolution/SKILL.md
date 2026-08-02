---
name: mt-error-resolution
description: "Error resolution, data validation, and defensive automation patterns for Modern Trade (MT) data pipelines. Use this skill whenever: a report or automation produces unexpected results; reconciliation fails; data quality issues are found (duplicates, missing columns, inflated totals, unmapped records); the user asks to debug, validate, QC, or troubleshoot any MT data process; building or reviewing any automation that ingests Excel/XLSB/CSV files; or the user says 'something is wrong with the numbers'. Always use before marking any automation output as PASS or Final."
---

# MT Error Resolution & Defensive Automation

Systematic error diagnosis, data validation, and safe automation patterns for Modern Trade data pipelines. This skill ensures no incorrect report reaches leadership and no automation silently corrupts business data.

## Essential problem-solving skills

| Skill | Why it matters | Practical application |
|---|---|---|
| Problem decomposition | Prevents a large issue from being treated as one vague error | Separate ingestion, mapping, calculation, reconciliation and output problems |
| Root-cause analysis | Fixes the source of an error instead of repeatedly correcting its symptoms | Use the Five Whys and trace the first stage where the value becomes incorrect |
| Data profiling | Reveals unexpected values before calculations begin | Check row counts, nulls, duplicates, unique values, ranges and data types |
| Schema validation | Stops structurally invalid files before processing | Verify required sheets, columns, formats and business keys |
| Reconciliation | Proves that records and value totals were preserved | Compare source and output at total, month, chain, store and article levels |
| Defensive programming | Makes the process fail safely when inputs are invalid | Reject missing columns, invalid dates, divide-by-zero cases and duplicate keys |
| Unit and regression testing | Confirms both new and existing logic remain correct | Test individual calculations and compare results with a previously approved output |
| Logging and observability | Makes failures traceable and easier to diagnose | Record file, stage, rule, record key, old value, new value and error message |
| Configuration management | Prevents hidden rules and accidental hard-coding | Store thresholds, exclusions, mappings and fiscal periods in controlled tables |
| Version control | Makes changes reviewable and recoverable | Track code, rule and mapping changes with reason, owner and approval |
| Business-rule documentation | Ensures the code matches the intended business definition | Define metric formula, grain, inclusions, exclusions, owner and effective date |
| Exception management | Focuses manual effort on unresolved risks | Route exceptions by severity, owner, due date and approval status |

## Key insights that prevent common errors

1. **Define the grain before joining data.** State what one row represents in every source — for example, Month + Chain + Site Code + EAN. Never join two datasets until their grains and keys are understood.
2. **Validate keys before totals.** Matching grand totals can hide duplicate stores, swapped chains or incorrect employee mappings. Check uniqueness, coverage and conflicts first.
3. **Preserve identifiers as text.** Site Code, EAN, Article Code and Client ID must remain text so leading zeros are not lost and scientific notation is avoided.
4. **Separate facts, mappings and calculations.** Raw transactions, master mappings and calculated metrics should be stored in separate layers. This makes the source of an error visible.
5. **Use one source of truth for each mapping.** Define an owner and priority for Chain, Store, City, EAN and employee mappings. Do not silently choose between conflicting sources.
6. **Make every business rule configurable.** Variance thresholds, excluded brands, fiscal periods and mapping priorities should be controlled outside the main code.
7. **Reject unsafe input early.** A blocked process is safer than a polished but incorrect report. Missing keys, duplicated business grains or unexplained reconciliation differences should stop release.
8. **Treat null, zero and not applicable differently.** Zero is a measured value; null means missing; not applicable means the metric does not apply. They must not be combined.
9. **Make reruns idempotent.** Running the same input twice must not duplicate records or change results.
10. **Prove the fix at the lowest and highest levels.** Validate the affected record or formula, then reconcile the complete report to ensure there is no downstream impact.

## Error-resolution sequence

Use this whenever a report or automation produces an unexpected result.

### Step 1: Detect and contain

- Stop publication or master-data overwrite.
- Preserve the input files, failed output, logs and configuration version.
- Record the affected period, chains, metrics and users.
- Classify severity as Critical, High, Medium or Low.

### Step 2: Classify the error

| Error class | Typical symptom | First check |
|---|---|---|
| Source error | Missing or incorrect values already exist in the source | Compare with source owner's approved record |
| Schema error | Missing, renamed or shifted columns | Validate headers, sheets and data types |
| Grain error | Duplicate or inflated totals after merging | Compare row grain and key uniqueness on both sides |
| Mapping error | Unmapped or wrongly assigned chain, store, city, EAN or employee | Check mapping coverage, conflicts and effective dates |
| Transformation error | Values change during cleaning or conversion | Compare before-and-after values at each processing stage |
| Formula error | A metric is wrong while base data is correct | Verify formula, denominator, signs, units and rounding |
| Filter error | Valid records disappear or excluded records remain | List active filters and count records removed by each rule |
| Time-period error | Month, quarter or year totals are misplaced | Check date parsing, fiscal calendar and period boundaries |
| Output error | Data is correct but Excel or dashboard is wrong | Check formulas, pivots, refresh state, ranges and cached data |
| Environment error | Process works on one machine but not another | Compare package versions, file paths, permissions and locale |

### Step 3: Isolate the first point of failure

- Reproduce the issue with the smallest affected sample.
- Trace the record through Raw -> Standardized -> Mapped -> Calculated -> Output stages.
- At every stage compare row count, unique-key count, value total and mapping status.
- The first stage where expected and actual results differ is the likely fault location.

### Step 4: Identify the root cause

Ask:

- What changed in the input, code, configuration, mapping or business definition?
- Is the issue systematic or limited to particular records?
- Did a many-to-many join multiply records?
- Did text-to-number or date conversion change the value?
- Was an outdated mapping or formula used?
- Why did an existing validation rule not detect the issue?

The root cause is not complete until both the error and the missing control that allowed it are understood.

### Step 5: Correct safely

- Fix the rule or controlled mapping, not only the final output cell.
- Never edit raw source data silently.
- Put uncertain corrections into the Approval Queue.
- Add a validation or test that would catch the same issue in future.
- Record the old logic, new logic, reason, owner and effective date.

### Step 6: Validate the correction

Minimum proof required:

- The original failing case now passes.
- Source and processed totals reconcile.
- Row count and unique-key count are expected.
- Mapping coverage does not decline unexpectedly.
- Unaffected chains, months and metrics remain unchanged.
- A rerun produces the same result.
- The previous approved period passes regression comparison.

### Step 7: Release and monitor

- Issue a release verdict: PASS, PASS WITH WARNINGS or BLOCKED.
- Obtain the required business or Finance approval.
- Publish with version, timestamp, input list and known exceptions.
- Monitor the next run for recurrence.

## Standard decision rules

- **BLOCKED:** missing mandatory columns; duplicate primary business keys; unexplained reconciliation difference; invalid period; corrupted source; or unresolved critical mapping conflict.
- **WARNING:** non-critical unmapped records below an approved threshold; explainable rounding difference; optional field missing; or late source that does not affect the official total.
- **PASS:** all mandatory validations succeed, reconciliation is within approved tolerance and no critical exceptions remain.
- **PASS WITH WARNINGS:** mandatory controls pass, remaining exceptions are documented, impact is quantified and the authorized owner approves release.

## Defensive coding patterns for MT pipelines

### Brand Counter filtering (Reliance double-count prevention)

```python
if "Data status" in df.columns:
    _chain_c = df["Chain Name"].astype(str).str.strip().str.lower()
    _ds_c = df["Data status"].astype(str).str.strip().str.lower()
    _is_rel = _chain_c.str.contains("reliance", na=False)
    _is_bc = (_ds_c == "brand counter")  # exact match — 'non brand counter' must NOT match
    df = df[~(_is_rel & _is_bc)].copy()
```

Key: use exact `==` for "brand counter", never `str.contains()`, because "non brand counter" also contains "brand counter".

### Site Code NA handling

```python
site_cols = ["Site Code", "Site Name"]
for col in site_cols:
    if col in df.columns:
        df[col] = df[col].fillna("NA")
        df[col] = df[col].astype(str).str.strip()
        df.loc[df[col].isin(["nan", "None", "none", ""]), col] = "NA"
```

### Column presence guard

```python
if "Data status" not in df.columns:
    print("WARNING: 'Data status' column not found. Reliance BC filter skipped.")
```

### Identifier preservation

```python
text_cols = ["Site Code", "EAN", "Article Code", "Client ID"]
for col in text_cols:
    if col in df.columns:
        df[col] = df[col].astype(str).str.strip()
```

### Groupby with NA safety

```python
# dropna=False keeps NA groups visible instead of silently dropping rows
df.groupby(["Chain Name", "Site Code"], dropna=False).sum()
```

## Required validation functions

Every automation should reuse standard checks for:

- Required file, sheet and column validation
- Data-type and date-format validation
- Primary-key uniqueness
- Duplicate record detection
- Null and blank-field checks
- Allowed-value and range checks
- Mapping coverage and conflict checks
- Join-cardinality checks: one-to-one, many-to-one or invalid many-to-many
- Source-to-output row and value reconciliation
- Variance and anomaly detection
- Formula denominator and divide-by-zero protection
- Prior-period regression comparison
- Output formula, pivot, filter and refresh verification

## Master rule

When an error or reconciliation difference is found, do not patch the final report manually. Preserve the evidence, classify the error, identify the earliest processing stage where the result becomes incorrect, determine the root cause and quantify its impact. Correct the underlying rule or controlled mapping, add a test that prevents recurrence, rerun the full process and reconcile both affected and unaffected data. Keep the release BLOCKED until every critical difference is resolved or explicitly approved by the authorized business owner.
