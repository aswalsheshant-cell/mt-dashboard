# Test skip inventory

Run: `python -m pytest tests/ -q -ra` on the integration branch (`claude/integration-validation`, which combines PRs #339-#344), 2026-10-19: 1027 passed, 1 failed (a stale data-source map count after the merge, regenerated and fixed on the branch), 29 skipped.
On `main` plus PRs #341-#343 the same suite reports 28 skipped; the 29th is the new September check from PR #339.

**Rule:** a skip is never removed to make the count zero. Each row says why it skips, what input is needed and who has to supply it. Owners are left as `TBD (human)`: the project has not named them and they are not guessed here.

## Summary

| Group | Count | Needs |
|---|---|---|
| Missing private data (restricted source): incentive workbook | 22 | `MT_Incentive_Working_FY27.xlsx`, built from DMS / Massit extracts that are not staged |
| Optional environment: PowerShell tests | 4 | `pwsh` installed where pytest runs |
| Waiting on business data: September chain rows | 1 | Sep'26 Bill-to rows in `ChainWisePrimarySale_Dump_Additions.csv` |
| Missing private data (gitignored): offtake CSVs | 1 | raw monthly offtake CSVs |
| Missing built artifact: `sales_actuals` | 1 | the `sales_actuals` block built into the data |
| **Total** | **29** | |

Unexplained skips: **0**. Obsolete tests found: **0**.

## Release-critical skips to close before sign-off
- **PowerShell tests (4)** skip in CI as well as here: the Python job (`production-acceptance-gate.yml`) reported 28 skipped, the same count as this machine, so the `pwsh`-dependent tests did not run there. The Windows job runs the script itself, but these pytest wrappers (checker passes on the repo; bad fixtures fail) have not been exercised. Install `pwsh` in the Python job or run them in the Windows job.
- **Incentive workbook (22)** never run here because the restricted DMS extracts are not staged. Run them in an authorised environment and keep the result; do not add data to the repository.
- **September chain rows (1)** closes when the Sep'26 Bill-to rows are supplied and added (PR #339).

## Skip list (29)

| # | Test file : line | Reason printed by pytest | Group | Input needed | Owner |
|---|---|---|---|---|---|
| 1 | `tests/test_chain_dump_allocation.py:213` | Sep'26 rows not yet added to ChainWisePrimarySale_Dump_Additions.csv | Waiting on business data | Sep'26 Bill-to rows in PowerBI/SeedData/Mapping/ChainWisePrimarySale_Dump_Additions.csv | TBD (human) |
| 2 | `tests/test_eval_harness_retired.py:61` | PowerShell (pwsh) not installed | Optional environment | PowerShell (pwsh) on the machine running pytest | TBD (human) |
| 3 | `tests/test_incentive_workbook.py:103` | MT_Incentive_Working_FY27.xlsx not generated | Missing private data (restricted source) | MT_Incentive_Working_FY27.xlsx, generated from DMS/Massit extracts (0 staged; incentive ingest blocked) | TBD (human) |
| 4 | `tests/test_incentive_workbook.py:126` | MT_Incentive_Working_FY27.xlsx not generated | Missing private data (restricted source) | MT_Incentive_Working_FY27.xlsx, generated from DMS/Massit extracts (0 staged; incentive ingest blocked) | TBD (human) |
| 5 | `tests/test_incentive_workbook.py:131` | MT_Incentive_Working_FY27.xlsx not generated | Missing private data (restricted source) | MT_Incentive_Working_FY27.xlsx, generated from DMS/Massit extracts (0 staged; incentive ingest blocked) | TBD (human) |
| 6 | `tests/test_incentive_workbook.py:140` | MT_Incentive_Working_FY27.xlsx not generated | Missing private data (restricted source) | MT_Incentive_Working_FY27.xlsx, generated from DMS/Massit extracts (0 staged; incentive ingest blocked) | TBD (human) |
| 7 | `tests/test_incentive_workbook.py:147` | MT_Incentive_Working_FY27.xlsx not generated | Missing private data (restricted source) | MT_Incentive_Working_FY27.xlsx, generated from DMS/Massit extracts (0 staged; incentive ingest blocked) | TBD (human) |
| 8 | `tests/test_incentive_workbook.py:154` | MT_Incentive_Working_FY27.xlsx not generated | Missing private data (restricted source) | MT_Incentive_Working_FY27.xlsx, generated from DMS/Massit extracts (0 staged; incentive ingest blocked) | TBD (human) |
| 9 | `tests/test_incentive_workbook.py:164` | MT_Incentive_Working_FY27.xlsx not generated | Missing private data (restricted source) | MT_Incentive_Working_FY27.xlsx, generated from DMS/Massit extracts (0 staged; incentive ingest blocked) | TBD (human) |
| 10 | `tests/test_incentive_workbook.py:172` | MT_Incentive_Working_FY27.xlsx not generated | Missing private data (restricted source) | MT_Incentive_Working_FY27.xlsx, generated from DMS/Massit extracts (0 staged; incentive ingest blocked) | TBD (human) |
| 11 | `tests/test_incentive_workbook.py:181` | MT_Incentive_Working_FY27.xlsx not generated | Missing private data (restricted source) | MT_Incentive_Working_FY27.xlsx, generated from DMS/Massit extracts (0 staged; incentive ingest blocked) | TBD (human) |
| 12 | `tests/test_incentive_workbook.py:187` | MT_Incentive_Working_FY27.xlsx not generated | Missing private data (restricted source) | MT_Incentive_Working_FY27.xlsx, generated from DMS/Massit extracts (0 staged; incentive ingest blocked) | TBD (human) |
| 13 | `tests/test_incentive_workbook.py:193` | MT_Incentive_Working_FY27.xlsx not generated | Missing private data (restricted source) | MT_Incentive_Working_FY27.xlsx, generated from DMS/Massit extracts (0 staged; incentive ingest blocked) | TBD (human) |
| 14 | `tests/test_incentive_workbook.py:203` | MT_Incentive_Working_FY27.xlsx not generated | Missing private data (restricted source) | MT_Incentive_Working_FY27.xlsx, generated from DMS/Massit extracts (0 staged; incentive ingest blocked) | TBD (human) |
| 15 | `tests/test_incentive_workbook.py:212` | MT_Incentive_Working_FY27.xlsx not generated | Missing private data (restricted source) | MT_Incentive_Working_FY27.xlsx, generated from DMS/Massit extracts (0 staged; incentive ingest blocked) | TBD (human) |
| 16 | `tests/test_incentive_workbook.py:221` | MT_Incentive_Working_FY27.xlsx not generated | Missing private data (restricted source) | MT_Incentive_Working_FY27.xlsx, generated from DMS/Massit extracts (0 staged; incentive ingest blocked) | TBD (human) |
| 17 | `tests/test_incentive_workbook.py:228` | MT_Incentive_Working_FY27.xlsx not generated | Missing private data (restricted source) | MT_Incentive_Working_FY27.xlsx, generated from DMS/Massit extracts (0 staged; incentive ingest blocked) | TBD (human) |
| 18 | `tests/test_incentive_workbook.py:235` | MT_Incentive_Working_FY27.xlsx not generated | Missing private data (restricted source) | MT_Incentive_Working_FY27.xlsx, generated from DMS/Massit extracts (0 staged; incentive ingest blocked) | TBD (human) |
| 19 | `tests/test_incentive_workbook.py:248` | MT_Incentive_Working_FY27.xlsx not generated | Missing private data (restricted source) | MT_Incentive_Working_FY27.xlsx, generated from DMS/Massit extracts (0 staged; incentive ingest blocked) | TBD (human) |
| 20 | `tests/test_incentive_workbook.py:256` | MT_Incentive_Working_FY27.xlsx not generated | Missing private data (restricted source) | MT_Incentive_Working_FY27.xlsx, generated from DMS/Massit extracts (0 staged; incentive ingest blocked) | TBD (human) |
| 21 | `tests/test_incentive_workbook.py:65` | MT_Incentive_Working_FY27.xlsx not generated | Missing private data (restricted source) | MT_Incentive_Working_FY27.xlsx, generated from DMS/Massit extracts (0 staged; incentive ingest blocked) | TBD (human) |
| 22 | `tests/test_incentive_workbook.py:68` | MT_Incentive_Working_FY27.xlsx not generated | Missing private data (restricted source) | MT_Incentive_Working_FY27.xlsx, generated from DMS/Massit extracts (0 staged; incentive ingest blocked) | TBD (human) |
| 23 | `tests/test_incentive_workbook.py:72` | MT_Incentive_Working_FY27.xlsx not generated | Missing private data (restricted source) | MT_Incentive_Working_FY27.xlsx, generated from DMS/Massit extracts (0 staged; incentive ingest blocked) | TBD (human) |
| 24 | `tests/test_incentive_workbook.py:77` | MT_Incentive_Working_FY27.xlsx not generated | Missing private data (restricted source) | MT_Incentive_Working_FY27.xlsx, generated from DMS/Massit extracts (0 staged; incentive ingest blocked) | TBD (human) |
| 25 | `tests/test_offtake_excel.py:16` | raw monthly offtake CSVs are gitignored and not on this machine | Missing private data (gitignored) | raw monthly offtake CSVs (gitignored) | TBD (human) |
| 26 | `tests/test_pbi_windows_ci_not_masked.py:70` | PowerShell (pwsh) not installed | Optional environment | PowerShell (pwsh) on the machine running pytest | TBD (human) |
| 27 | `tests/test_pbi_windows_ci_not_masked.py:83` | PowerShell (pwsh) not installed | Optional environment | PowerShell (pwsh) on the machine running pytest | TBD (human) |
| 28 | `tests/test_pbi_windows_ci_not_masked.py:92` | PowerShell (pwsh) not installed | Optional environment | PowerShell (pwsh) on the machine running pytest | TBD (human) |
| 29 | `tests/test_published_assets_privacy.py:62` | sales_actuals not built yet | Missing built artifact | sales_actuals block not built in the data | TBD (human) |
