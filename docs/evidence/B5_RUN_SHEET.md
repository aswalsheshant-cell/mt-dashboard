# B5 — Power BI Desktop run sheet (current model)

**What this is.** The B5 exit condition from `docs/COMPLETION_BLOCKER_PACK.md`,
turned into steps you can follow on the Windows machine. Owner decision
2026-09-29: B5 is judged on the **current** model, meaning the FY parser plus
CM2 Cases 2–8; owner decision 2026-10-01 added the L3M/L6M rolling-average
check (step 9, #273) to the same session. The old CM2 Case 1 ("no expense rows") needed the model as it
was before #229. #229 loaded real expense rows, so Case 1 no longer applies.

**Status until this sheet is run:** `BLOCKED_PENDING_DESKTOP_EVIDENCE`.
CI has no DAX or Power Query engine, so nothing here can be marked PASS from Linux.

**Where results go:** copy `B5_EVIDENCE_TEMPLATE.md` to
`B5_powerbi_runtime_<YYYY-MM-DD>.md` in this folder and fill in every row.
Attach one screenshot per step as a comment on the B5 PR. A result reported
only in chat does not count.

---

## 0. Before you start

1. Pull the latest `main` and note the commit: `git rev-parse --short HEAD`.
   This commit goes into the evidence file.
2. Open the Power BI Desktop model and note **Help ▸ About** (version and
   month) and the `.pbix` file name.
3. **Home ▸ Refresh** so the model reads today's
   `PowerBI/SeedData/Masters/PL_Expense_Input.csv`.
4. Cross-check the load. The CSV has 64 real rows, ₹1,274.71 L in total, all
   `FY26-27`, Apr–Aug 2026:

   | Month | Rows | ₹ Lakh |
   |---|---|---|
   | Apr'26 | 14 | 260.19 |
   | May'26 | 16 | 336.56 |
   | Jun'26 | 15 | 376.89 |
   | Jul'26 | 12 | 197.49 |
   | Aug'26 | 7 | 103.58 |

   The 3 `EXAMPLE ROW` template rows are dropped by query 39 and must not appear.
5. Note these two QC measures. Case 3 depends on the first one.
   - `[Unmapped Chain Or Customer Rows]`
   - `[Total Expense Amount Loaded]` (expected ₹1,274.71 L)

DAX cases run in **DAX Studio** connected to the open model, or in Desktop's
**DAX query view**. Run each `EVALUATE` block **on its own**. The case blocks
are in `tests/powerbi/cm2_availability_cases.dax`.

---

## 1. FY parser

| | |
|---|---|
| File | `tests/powerbi/pq39_fy_parser_cases.pq` (reads `tests/powerbi/fy_parser_cases.csv`, 26 cases) |
| How | Transform data ▸ New Source ▸ Blank Query ▸ Advanced Editor ▸ paste the file ▸ Done. If `pRootFolder` is not the repo's `PowerBI` folder, set `CasesFile` to the full path of `fy_parser_cases.csv`. Delete the query afterwards: it is a test, not part of the model. |
| Expected | The `Failures` step returns **0 rows** |
| Record | Row count of `Failures`. If it is not 0, copy every row. |
| PASS rule | PASS only if `Failures` has exactly 0 rows. Anything else is FAIL. |

## 2. CM2 Case 2 — month-level arithmetic

| | |
|---|---|
| Block | `// CASE 2` (`SUMMARIZECOLUMNS` by `'Date Table'[MonthStart]`) |
| Expected (from the file) | In months **with** expense: `CM2 = NSV − Expense` exactly, `Check` = `"OK"`. In months **without** expense: `Expense` and `CM2` are BLANK, `Check` = `"OK blank"` (never `CM2 = NSV`). |
| Record | Number of rows where `Check` = `"OK"`, `"OK blank"` and `"FAIL…"`. List every FAIL row. |
| PASS rule | PASS if **no** row starts with `FAIL` and the `"OK"` rows are exactly the months with loaded expense (Apr–Aug 2026). |

## 3. CM2 Case 3 — unmapped expense is QC-only

| | |
|---|---|
| Block | `// CASE 3` |
| Expected (from the file) | `Unmapped > 0`, `Mapped` = BLANK, `CM2` = BLANK. Unmapped rows are reported in QC and never deducted. |
| Precondition | The file writes this case for data **with** unmapped rows. Check `[Unmapped Chain Or Customer Rows]` from step 0.5 first. |
| Record | The three values, plus the unmapped-row count. |
| PASS rule | **If unmapped rows > 0:** PASS only if `Unmapped > 0` and `Mapped` and `CM2` are both BLANK. **If unmapped rows = 0:** record `NOT_EXERCISED (0 unmapped rows)` with the count as evidence. This is neither PASS nor FAIL, and it does not block B5. Do not create an unmapped row to force the case. |

## 4. CM2 Case 4 — chain availability

| | |
|---|---|
| Block | `// CASE 4`: two `EVALUATE`s (the chain table, then `Violations`). Both are scoped to FY27 (`'Date Table'[FY Year] = "2026-27"`) since the CM2 comparability fix: with no FY filter every CM2 is BLANK by design (Case 9). |
| Expected (from the file) | Chains **with** expense: `ChainCM2 = NSV − ChainExpense`. Chains **without** expense: `ChainExpense` and `ChainCM2` both BLANK. The `Violations` query returns **0**. |
| Record | The `Violations` value. From the chain table, spot-check one chain with expense (write NSV, expense, CM2) and one chain without (write that both are BLANK). |
| PASS rule | PASS only if `Violations = 0` and the spot-checked chain with expense satisfies `ChainCM2 = NSV − ChainExpense`. |

## 5. CM2 Case 5 — month filter leakage

| | |
|---|---|
| Block | `// CASE 5`: the detail table, then the `Leak` query |
| Expected (from the file) | For every Chain × Month, `ChainExpense = MonthRowsExpense`. `Leak` = **0**. |
| Record | The `Leak` value (and any non-matching rows from the detail table if Leak ≠ 0). |
| PASS rule | PASS only if **`Leak = 0`**. |

## 6. CM2 Case 6 — FY filter leakage

| | |
|---|---|
| Block | `// CASE 6` |
| Expected (from the file) | The FY27 (`2026-27`) row carries FY27 expense only. The FY26 (`2025-26`) row has BLANK `Expense` and BLANK `CM2`, because every loaded row is FY27. |
| Cross-check | The FY27 `Expense` should equal the **mapped** part of the ₹1,274.71 L load: ₹1,274.71 L if step 0.5 shows 0 unmapped rows, otherwise ₹1,274.71 L minus the Case 3 `Unmapped` amount. |
| Record | `Expense`, `TopChainExp` and `CM2` for each FY row shown. |
| PASS rule | PASS only if FY26 `Expense` and `CM2` are BLANK **and** FY27 `Expense` equals the cross-check value (to ₹0.01 L). |

## 7. CM2 Case 7 — brand and category month filter

| | |
|---|---|
| Block | `// CASE 7` |
| Expected (from the file) | **`BrandLeak = 0`** and **`CategoryLeak = 0`** |
| Record | Both values |
| PASS rule | PASS only if both are 0 |

## 8. CM2 Case 8 — no expense in the period gives no CM2

| | |
|---|---|
| Block | `// CASE 8` |
| Expected (from the file) | For a month with NSV but no expense, `ChainExpense` and `ChainCM2` are BLANK for every chain (never the chain's NSV). **`Violations = 0`.** |
| Record | The `Violations` value |
| PASS rule | PASS only if **`Violations = 0`** |

## 9. Rolling averages — L3M / L6M (added 2026-10-01, owner decision, #273)

#273 changed `L3M Average Sales` and `L6M Average Sales` to average over the
months that have data (a missing month is not ₹0; an empty window is BLANK).
CI checks the formula only; this step checks the behaviour on the real model.

| | |
|---|---|
| File | `tests/powerbi/rolling_average_cases.dax` |
| Block | `// CASE 1` (Mismatches), `// CASE 2` (first month), `// CASE 3` (third month). `// CASE 4` lists genuine 0-NSV months, for the record only. |
| Expected (from the file) | CASE 1: **`Mismatches = 0`** (BLANK also means 0). CASE 2: `L3M` and `L6M` both BLANK. CASE 3: `L3M = Expected`. |
| Record | CASE 1 `Months` and `Mismatches`; CASE 2 `FirstMonth`, `L3M`, `L6M`; CASE 3 `Month`, `L3M`, `Expected`; CASE 4 row count. |
| PASS rule | PASS only if CASE 1 `Mismatches = 0` (or BLANK), CASE 2 both BLANK, and CASE 3 `L3M = Expected` (to 0.01). |

## 10. CM2 Case 9 — comparability (added 2026-10-02, CM2 comparability fix)

CM2 is withheld when the expense does not cover the same financial years as the
NSV (`[CM2 Comparable]`). CI checks the measure structure only; this step checks
the behaviour on the real model.

| | |
|---|---|
| Block | `// CASE 9` (one `EVALUATE` returning three rows: No FY filter, FY27, FY26) |
| Expected (from the file) | **No FY filter:** `Comparable = 0`; `ExpensePct`, `CM2`, `CM2Pct` all BLANK (`NSV` and `Expense` still show). **FY27:** `Comparable = 1`, `CM2 = NSV − Expense` exactly, `ExpensePct` and `CM2Pct` real numbers. **FY26:** `Comparable = 0`, `Expense` and `CM2` BLANK (never `CM2 = NSV`). |
| Record | The three rows (all columns) |
| PASS rule | PASS only if all three rows match the expected values above. Any CM2 number on the "No FY filter" or "FY26" row is a FAIL. |

---

## When B5 closes

B5 is CLEARED only when all of these hold:
- the evidence file is filled in for the FY parser, Cases 2, 4, 5, 6, 7, 8 and 9, and the rolling-average step (9), every one PASS;
- Case 3 is PASS, or `NOT_EXERCISED` with the 0-row count recorded;
- the screenshots are attached to the B5 PR.

Any FAIL keeps B5 open. It becomes a defect to root-cause; never re-word the
expectation to fit the result.
