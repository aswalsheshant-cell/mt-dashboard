# B5 without a Windows desktop: options found on the web (2026-10-11)

B5 stays `BLOCKED_PENDING_DESKTOP_EVIDENCE`. The owner rule (2026-09-29, 2026-10-01) asks for evidence from Power BI Desktop. Anything below is a different engine, so the owner has to accept it in writing before it can clear B5. Nothing here has been run.

| Option | What it runs | What you need | What it cannot do |
|---|---|---|---|
| **A. ExecuteQueries REST API** on a published model | CM2 Cases 2-9 and the rolling-average cases (all DAX) | Model published to a Power BI workspace, refreshed there, Build permission, an Entra app or signed-in token. Microsoft's quickstart: [execute DAX queries](https://learn.microsoft.com/en-us/power-bi/developer/execute-dax-queries-arrow/get-started). Method described by [endjin](https://endjin.com/blog/testing-power-bi-reports-using-execute-queries-rest-api) (their own approach, not a Microsoft-supported test method). | The FY parser (it is Power Query M, not DAX). The refresh in the Service needs a gateway or SharePoint/OneDrive source: our queries read a local folder. |
| **B. pql-test over XMLA** | The same DAX files | A Premium, PPU or Fabric workspace XMLA endpoint, or a local Desktop. See [pql-test](https://pypi.org/project/pql-test/). | Same FY parser gap. Needs capacity. |
| **C. Desktop Bridge CLI (preview)** | Reload and screenshots of an open Desktop | Windows, Desktop open, a recent Desktop build. Reported by [Red Gate](https://www.red-gate.com/simple-talk/featured/how-to-use-the-power-bi-desktop-bridge-to-automate-tasks-in-power-bi-desktop-and-github-copilot/) and [SQLBI pbi-tools](https://www.sqlbi.com/tools/pbi-tools/). | Not headless. Preview, no commitment on final behaviour. |

I found nothing that runs Power BI Desktop headless on a GitHub Actions runner, so CI cannot clear B5 on its own.

## What I recommend
1. Easiest for you: run the existing PowerShell runner once on any Windows laptop with Desktop (about 30 minutes, steps in `B5_RUNNER.md`). It covers everything including the FY parser.
2. If no Windows machine is available: option A for the DAX cases, plus the FY parser pasted into Power Query Online (a dataflow in the workspace). That second step I could not confirm from the sources I found, so treat it as untested.
3. Either way the evidence file `B5_powerbi_runtime_<date>.md` must say which engine produced each row.

## Decision needed from the owner
Will B5 accept ExecuteQueries results from a Service workspace instead of Desktop? If yes, I can write `scripts/b5_execute_queries.py` that posts each case block from `tests/powerbi/` and applies the same PASS rules as `scripts/B5-DesktopRunner.ps1`. I have not written it yet because it would be untested code until a workspace exists.
