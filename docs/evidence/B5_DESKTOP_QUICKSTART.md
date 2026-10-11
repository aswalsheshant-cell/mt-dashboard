# B5 on your Windows machine: one-page quick start

B5 stays `BLOCKED_PENDING_DESKTOP_EVIDENCE` until this run produces an evidence file and the screenshots are attached. Full detail: `B5_RUNNER.md` and `B5_RUN_SHEET.md`. You need Power BI Pro only; no Premium, PPU or Fabric.

## Before you start (10 minutes)
1. Power BI Desktop from June 2025 or later, and Python 3 on PATH.
2. `git fetch`, then check out the SHA I give you (the latest on `claude/gallant-shannon-wou27y`). Clean working tree.
3. Run `python scripts/audit_data_source_map.py --preflight PowerBI`. Fix any missing file or changed column it names before going on.
4. Build the model from `PowerBI/QuickSetup/` (or deploy `PowerBI/model.bim` with Tabular Editor), set `pRootFolder` to your local `PowerBI` folder, then **Home > Refresh** and wait. If the refresh fails, copy the exact error text and send it to me.

## The run (20 minutes)
1. FY parser: Transform data > New Source > Blank Query > Advanced Editor > paste `tests/powerbi/pq39_fy_parser_cases.pq`. The `Failures` step must return 0 rows. Screenshot it, then delete the query.
2. In PowerShell, from the repo root:
   `powershell -ExecutionPolicy Bypass -File .\scripts\B5-DesktopRunner.ps1 -RunBy "MT Channel Analyst Lead" -Refreshed -FyParserFailures 0 -AttestedBy "<your name>" -ExpectSha <short SHA>`
3. Read the console. Each row says PASS, FAIL, NOT_EXERCISED (Case 3 when there are no unmapped rows) or NOT_RUN.
4. The script writes `docs/evidence/B5_powerbi_runtime_<date>.md`. Attach one screenshot per step to the PR and keep the `results.json` it prints next to them.

## What to send back
- The whole console output, even if everything passed.
- Any FAIL or NOT_RUN row, with a screenshot.
- Expected load check before the cases: `[Total Expense Amount Loaded]` = Rs 1,274.71 L.

## If Desktop cannot be used
Fallback on Pro only: publish the model once from Desktop with the data read from SharePoint Online, then run `scripts/b5_execute_queries.py` (see `B5_ALTERNATIVES.md`). I build the SharePoint version of the queries only if you need it.
