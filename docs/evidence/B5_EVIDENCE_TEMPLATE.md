# B5 Power BI Desktop evidence — TEMPLATE

Copy this file to `B5_powerbi_runtime_<YYYY-MM-DD>.md` in this folder and fill
in every `<…>` field. Leave nothing blank: write `NOT_RUN` if a step was not
run. Procedure and PASS rules: `B5_RUN_SHEET.md`.

| Field | Value |
|---|---|
| Date run | `<YYYY-MM-DD>` |
| Run by | `<role, e.g. MT Channel Analyst Lead>` |
| `main` commit (git SHA) | `<short SHA>` |
| Power BI Desktop version | `<Help ▸ About, e.g. 2.1xx.xxxx.x (Month YYYY)>` |
| Model file | `<.pbix file name>` |
| Refreshed before the run | `<yes / no>` |
| `[Total Expense Amount Loaded]` | `<value>` (expected ₹1,274.71 L) |
| `[Unmapped Chain Or Customer Rows]` | `<value>` |

| # | Test / case | Expected | Actual | Result | Evidence reference |
|---|---|---|---|---|---|
| 1 | FY parser (`pq39_fy_parser_cases.pq`) | `Failures` = 0 rows | `<rows>` | `<PASS/FAIL>` | `<screenshot comment link>` |
| 2 | CM2 Case 2 — month arithmetic | no `FAIL` rows; `OK` rows = Apr–Aug 2026 | `<OK n / OK blank n / FAIL n>` | `<PASS/FAIL>` | `<link>` |
| 3 | CM2 Case 3 — unmapped is QC-only | if unmapped > 0: Unmapped > 0, Mapped BLANK, CM2 BLANK | `<values>` | `<PASS/FAIL/NOT_EXERCISED>` | `<link>` |
| 4 | CM2 Case 4 — chain availability (FY27 scope) | `Violations` = 0; ChainCM2 = NSV − ChainExpense | `<Violations; spot-check values>` | `<PASS/FAIL>` | `<link>` |
| 5 | CM2 Case 5 — month leakage | `Leak` = 0 | `<value>` | `<PASS/FAIL>` | `<link>` |
| 6 | CM2 Case 6 — FY leakage | FY26 BLANK; FY27 Expense = mapped load | `<values per FY>` | `<PASS/FAIL>` | `<link>` |
| 7a | CM2 Case 7 — brand | `BrandLeak` = 0 | `<value>` | `<PASS/FAIL>` | `<link>` |
| 7b | CM2 Case 7 — category | `CategoryLeak` = 0 | `<value>` | `<PASS/FAIL>` | `<link>` |
| 8 | CM2 Case 8 — no expense, no CM2 | `Violations` = 0 | `<value>` | `<PASS/FAIL>` | `<link>` |
| 9 | L3M / L6M rolling averages (`rolling_average_cases.dax`) | CASE 1 `Mismatches` = 0; CASE 2 L3M, L6M BLANK; CASE 3 L3M = Expected | `<Mismatches; CASE 2 values; CASE 3 L3M vs Expected>` | `<PASS/FAIL>` | `<link>` |
| 10 | CM2 Case 9 — comparability | No FY filter / FY26: CM2, CM2%, Expense% BLANK; FY27: CM2 = NSV − Expense | `<3 rows>` | `<PASS/FAIL>` | `<link>` |

**B5 verdict:** `<CLEARED / OPEN — reason>`

CLEARED only if rows 1, 2, 4, 5, 6, 7a, 7b, 8, 9 and 10 are PASS and row 3 is PASS or
`NOT_EXERCISED` with the 0-row count above.
