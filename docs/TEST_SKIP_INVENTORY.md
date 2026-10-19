# Test skip inventory

Two runs of `pytest tests/ -q -ra` on the combined branch (`claude/integration-validation`, PRs #339-#344 merged), 2026-10-19:
- **This machine:** 1028 passed, 29 skipped.
- **CI, Python job (PR #345, ubuntu runner):** 1028 passed, 29 skipped. The 29 are not the same 29: 4 PowerShell tests skip here but run in CI; 4 tests skip in CI (node/playwright x3, LibreOffice x1) but run here.
- Distinct skipped tests across both: **33**. Unexplained: **0**. Obsolete: **0**.

**Rule:** a skip is never removed to make the count zero. Each row says why it skips, what input is needed and who has to supply it. Owners are left as `TBD (human)`: none are named in the project and none are guessed here.

## Summary

| Group | Rows | Needs |
|---|---|---|
| Missing private data (restricted source): incentive workbook | 22 | `MT_Incentive_Working_FY27.xlsx`, built from DMS / Massit extracts that are not staged. Skips in both places |
| Waiting on business data: September chain rows | 1 | Sep'26 Bill-to rows in `ChainWisePrimarySale_Dump_Additions.csv` (both) |
| Missing private data (gitignored): offtake CSVs | 1 | raw monthly offtake CSVs (both) |
| Missing built artifact: `sales_actuals` | 1 | the `sales_actuals` block built into the data (both) |
| Optional environment, local only: PowerShell tests | 4 | `pwsh` on this machine. They run and pass in CI |
| Optional environment, CI only: node / playwright tests | 3 | node + playwright in the Python job. They pass locally |
| Optional environment, CI only: LibreOffice test | 1 | LibreOffice in the Python job. It passes locally |
| **Total distinct** | **33** | |

## Release-critical skips to close before sign-off
- **Incentive workbook (22)** never runs in either place because the restricted DMS extracts are not staged. Run these tests in an authorised environment and keep the result. Do not add the data to the repository.
- **September chain rows (1)** closes when the Sep'26 Bill-to rows are supplied and added (PR #339).
- **node/playwright (3) and LibreOffice (1) in CI**: install them in the Python job, or confirm the Browser Regression gate covers the same checks. Not yet confirmed.
- **PowerShell (4) locally**: install `pwsh` to run them here; CI already runs them.

## Skip list (33)

| # | Test file : line | Reason printed by pytest | Group | Input needed | Skips in | Owner |
|---|---|---|---|---|---|---|
| 1 | `tests/test_chain_dump_allocation.py:213` | Sep'26 rows not yet added to ChainWisePrimarySale_Dump_Additions.csv | Waiting on business data | Sep'26 Bill-to rows in PowerBI/SeedData/Mapping/ChainWisePrimarySale_Dump_Additions.csv | local and CI | TBD (human) |
| 2 | `tests/test_eval_harness_retired.py:61` | PowerShell (pwsh) not installed | Optional environment (local) | PowerShell (pwsh) on the machine running pytest; installed on the CI runner, where these 4 tests run | local only (CI ran it) | TBD (human) |
| 3 | `tests/test_incentive_workbook.py:103` | MT_Incentive_Working_FY27.xlsx not generated | Missing private data (restricted source) | MT_Incentive_Working_FY27.xlsx, built from DMS / Massit extracts (0 staged; incentive ingest blocked) | local and CI | TBD (human) |
| 4 | `tests/test_incentive_workbook.py:126` | MT_Incentive_Working_FY27.xlsx not generated | Missing private data (restricted source) | MT_Incentive_Working_FY27.xlsx, built from DMS / Massit extracts (0 staged; incentive ingest blocked) | local and CI | TBD (human) |
| 5 | `tests/test_incentive_workbook.py:131` | MT_Incentive_Working_FY27.xlsx not generated | Missing private data (restricted source) | MT_Incentive_Working_FY27.xlsx, built from DMS / Massit extracts (0 staged; incentive ingest blocked) | local and CI | TBD (human) |
| 6 | `tests/test_incentive_workbook.py:140` | MT_Incentive_Working_FY27.xlsx not generated | Missing private data (restricted source) | MT_Incentive_Working_FY27.xlsx, built from DMS / Massit extracts (0 staged; incentive ingest blocked) | local and CI | TBD (human) |
| 7 | `tests/test_incentive_workbook.py:147` | MT_Incentive_Working_FY27.xlsx not generated | Missing private data (restricted source) | MT_Incentive_Working_FY27.xlsx, built from DMS / Massit extracts (0 staged; incentive ingest blocked) | local and CI | TBD (human) |
| 8 | `tests/test_incentive_workbook.py:154` | MT_Incentive_Working_FY27.xlsx not generated | Missing private data (restricted source) | MT_Incentive_Working_FY27.xlsx, built from DMS / Massit extracts (0 staged; incentive ingest blocked) | local and CI | TBD (human) |
| 9 | `tests/test_incentive_workbook.py:164` | MT_Incentive_Working_FY27.xlsx not generated | Missing private data (restricted source) | MT_Incentive_Working_FY27.xlsx, built from DMS / Massit extracts (0 staged; incentive ingest blocked) | local and CI | TBD (human) |
| 10 | `tests/test_incentive_workbook.py:172` | MT_Incentive_Working_FY27.xlsx not generated | Missing private data (restricted source) | MT_Incentive_Working_FY27.xlsx, built from DMS / Massit extracts (0 staged; incentive ingest blocked) | local and CI | TBD (human) |
| 11 | `tests/test_incentive_workbook.py:181` | MT_Incentive_Working_FY27.xlsx not generated | Missing private data (restricted source) | MT_Incentive_Working_FY27.xlsx, built from DMS / Massit extracts (0 staged; incentive ingest blocked) | local and CI | TBD (human) |
| 12 | `tests/test_incentive_workbook.py:187` | MT_Incentive_Working_FY27.xlsx not generated | Missing private data (restricted source) | MT_Incentive_Working_FY27.xlsx, built from DMS / Massit extracts (0 staged; incentive ingest blocked) | local and CI | TBD (human) |
| 13 | `tests/test_incentive_workbook.py:193` | MT_Incentive_Working_FY27.xlsx not generated | Missing private data (restricted source) | MT_Incentive_Working_FY27.xlsx, built from DMS / Massit extracts (0 staged; incentive ingest blocked) | local and CI | TBD (human) |
| 14 | `tests/test_incentive_workbook.py:203` | MT_Incentive_Working_FY27.xlsx not generated | Missing private data (restricted source) | MT_Incentive_Working_FY27.xlsx, built from DMS / Massit extracts (0 staged; incentive ingest blocked) | local and CI | TBD (human) |
| 15 | `tests/test_incentive_workbook.py:212` | MT_Incentive_Working_FY27.xlsx not generated | Missing private data (restricted source) | MT_Incentive_Working_FY27.xlsx, built from DMS / Massit extracts (0 staged; incentive ingest blocked) | local and CI | TBD (human) |
| 16 | `tests/test_incentive_workbook.py:221` | MT_Incentive_Working_FY27.xlsx not generated | Missing private data (restricted source) | MT_Incentive_Working_FY27.xlsx, built from DMS / Massit extracts (0 staged; incentive ingest blocked) | local and CI | TBD (human) |
| 17 | `tests/test_incentive_workbook.py:228` | MT_Incentive_Working_FY27.xlsx not generated | Missing private data (restricted source) | MT_Incentive_Working_FY27.xlsx, built from DMS / Massit extracts (0 staged; incentive ingest blocked) | local and CI | TBD (human) |
| 18 | `tests/test_incentive_workbook.py:235` | MT_Incentive_Working_FY27.xlsx not generated | Missing private data (restricted source) | MT_Incentive_Working_FY27.xlsx, built from DMS / Massit extracts (0 staged; incentive ingest blocked) | local and CI | TBD (human) |
| 19 | `tests/test_incentive_workbook.py:248` | MT_Incentive_Working_FY27.xlsx not generated | Missing private data (restricted source) | MT_Incentive_Working_FY27.xlsx, built from DMS / Massit extracts (0 staged; incentive ingest blocked) | local and CI | TBD (human) |
| 20 | `tests/test_incentive_workbook.py:256` | MT_Incentive_Working_FY27.xlsx not generated | Missing private data (restricted source) | MT_Incentive_Working_FY27.xlsx, built from DMS / Massit extracts (0 staged; incentive ingest blocked) | local and CI | TBD (human) |
| 21 | `tests/test_incentive_workbook.py:65` | MT_Incentive_Working_FY27.xlsx not generated | Missing private data (restricted source) | MT_Incentive_Working_FY27.xlsx, built from DMS / Massit extracts (0 staged; incentive ingest blocked) | local and CI | TBD (human) |
| 22 | `tests/test_incentive_workbook.py:68` | MT_Incentive_Working_FY27.xlsx not generated | Missing private data (restricted source) | MT_Incentive_Working_FY27.xlsx, built from DMS / Massit extracts (0 staged; incentive ingest blocked) | local and CI | TBD (human) |
| 23 | `tests/test_incentive_workbook.py:72` | MT_Incentive_Working_FY27.xlsx not generated | Missing private data (restricted source) | MT_Incentive_Working_FY27.xlsx, built from DMS / Massit extracts (0 staged; incentive ingest blocked) | local and CI | TBD (human) |
| 24 | `tests/test_incentive_workbook.py:77` | MT_Incentive_Working_FY27.xlsx not generated | Missing private data (restricted source) | MT_Incentive_Working_FY27.xlsx, built from DMS / Massit extracts (0 staged; incentive ingest blocked) | local and CI | TBD (human) |
| 25 | `tests/test_offtake_excel.py:16` | raw monthly offtake CSVs are gitignored and not on this machine | Missing private data (gitignored) | raw monthly offtake CSVs (gitignored) | local and CI | TBD (human) |
| 26 | `tests/test_pbi_windows_ci_not_masked.py:70` | PowerShell (pwsh) not installed | Optional environment (local) | PowerShell (pwsh) on the machine running pytest; installed on the CI runner, where these 4 tests run | local only (CI ran it) | TBD (human) |
| 27 | `tests/test_pbi_windows_ci_not_masked.py:83` | PowerShell (pwsh) not installed | Optional environment (local) | PowerShell (pwsh) on the machine running pytest; installed on the CI runner, where these 4 tests run | local only (CI ran it) | TBD (human) |
| 28 | `tests/test_pbi_windows_ci_not_masked.py:92` | PowerShell (pwsh) not installed | Optional environment (local) | PowerShell (pwsh) on the machine running pytest; installed on the CI runner, where these 4 tests run | local only (CI ran it) | TBD (human) |
| 29 | `tests/test_published_assets_privacy.py:62` | sales_actuals not built yet | Missing built artifact | the sales_actuals block built into the data | local and CI | TBD (human) |
| 30 | `tests/test_nielsen_market_share_both.py:152` | node or its playwright package not installed | Optional environment (CI) | node + the playwright package on the CI runner (the dashboard sweep itself runs in the Browser Regression gate) | CI only (ran and passed locally) | TBD (human) |
| 31 | `tests/test_nielsen_payload.py:72` | node or its playwright package not installed | Optional environment (CI) | node + the playwright package on the CI runner (the dashboard sweep itself runs in the Browser Regression gate) | CI only (ran and passed locally) | TBD (human) |
| 32 | `tests/test_offtake_excel.py:71` | LibreOffice not installed | Optional environment (CI) | LibreOffice on the CI runner | CI only (ran and passed locally) | TBD (human) |
| 33 | `tests/test_store_universe.py:61` | node or its playwright package not installed | Optional environment (CI) | node + the playwright package on the CI runner (the dashboard sweep itself runs in the Browser Regression gate) | CI only (ran and passed locally) | TBD (human) |
