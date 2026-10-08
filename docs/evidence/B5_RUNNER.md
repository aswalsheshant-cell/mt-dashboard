# B5 runner — run the Desktop cases with a script, keep the evidence honest

**Status of this tool: the PowerShell half has never been run against a real
engine** (it was written where there is no Windows and no DAX engine). Your first run
is its first test. If a step looks wrong, stop and send the console output.

B5 is still `BLOCKED_PENDING_DESKTOP_EVIDENCE`. This runner does not clear it. It
only makes the Desktop session faster and the evidence file machine-checked.

## What it replaces, and what it does not

| Step in `B5_RUN_SHEET.md` | Runner |
|---|---|
| 0.5 load cross-check | runs a pre-flight query (rows loaded, `[Total Expense Amount Loaded]`, unmapped rows and amount) |
| 2–8 CM2 Cases 2–8, 10 CM2 Case 9 | runs every governed `EVALUATE` block, applies the run sheet's PASS rules |
| 9 rolling averages | same, from `rolling_average_cases.dax` |
| 1 FY parser | **manual**: Power Query M is not reachable through Analysis Services |
| screenshots | **manual**: one per step, attached by you |

## How to run

1. `git fetch` and check out the frozen `main` SHA. The working tree must be clean.
2. Build/open the model in Power BI Desktop (see `PowerBI/QuickSetup/`), then **Home ▸ Refresh** and wait.
3. FY parser: paste `tests/powerbi/pq39_fy_parser_cases.pq` as a blank query, read the `Failures` step, delete the query. Screenshot it.
4. In PowerShell, from the repo root:

   ```powershell
   powershell -ExecutionPolicy Bypass -File .\scripts\B5-DesktopRunner.ps1 `
       -RunBy "MT Channel Analyst Lead" -Refreshed `
       -FyParserFailures 0 -AttestedBy "<your name>" -ExpectSha <frozen short SHA>
   ```

   Leave out `-FyParserFailures` if you have not done step 3: row 1 then stays `NOT_RUN`.
5. Read the console summary. A row is `PASS`, `FAIL`, `NOT_EXERCISED` (Case 3 with 0 unmapped rows) or `NOT_RUN`.
6. The script writes `docs/evidence/B5_powerbi_runtime_<date>.md`. Attach the screenshots (one per step) to the B5 PR, keep the `results.json` it printed next to them, and commit the evidence file.

## What the generator refuses to do

- write evidence unless the results came from a live Analysis Services connection (port, database, server version, measure count, Desktop version and git SHA are all required);
- accept results produced by edited queries (they must equal the governed case files);
- accept a dirty working tree (unless `--allow-dirty`, which is recorded) or a SHA other than `--expect-sha`;
- overwrite an existing evidence file;
- write `PASS` for a row it did not measure.

Even when every row passes it writes `OPEN — every measured row PASS; screenshots not yet attached`.
A person changes that to `CLEARED` after attaching the screenshots. Any `FAIL` is a defect to
root-cause; never edit the expectation to fit the result.

## What it cannot prove

It cannot tell a real engine from a hand-edited `results.json`. The safeguards make faking
a deliberate act, not an accident: the queries must equal the governed files, the live
metadata (port, server version, measure count, Desktop version, SHA) must be present, both
hashes of the raw results are written into the evidence, and the screenshots (a human step)
are what make a row final. The evidence file is only as honest as the person who runs it.

## Where the logic lives

- `scripts/b5_evidence.py` — query extraction, PASS rules, evidence rendering (tested in CI by `tests/test_b5_evidence.py`, including failing fixtures).
- `scripts/B5-DesktopRunner.ps1` — finds the model's local port, runs the queries, writes `results.json`, calls the script above.
- `tests/test_b5_exit_condition.py` — still decides whether the docs may say B5 is CLEARED: an evidence file must exist and every required row must be `PASS`.
