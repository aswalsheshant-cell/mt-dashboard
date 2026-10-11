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

## Decision (owner, 2026-10-11): option A accepted
B5 may be measured on a published, refreshed copy of the model through ExecuteQueries instead of Desktop. The evidence file must say so, and it does: `scripts/b5_evidence.py` writes "measured on Power BI Service" in the title, the header and the provenance. Everything else in `B5_RUN_SHEET.md` is unchanged.

Tool: `scripts/b5_execute_queries.py` (usage in its header). It posts the governed blocks from `tests/powerbi/*_cases.dax` one by one, refuses unless the last Service refresh is Completed and the published model was built from the repo SHA, then `b5_evidence.py` applies the same PASS rules as the Desktop route. 10 unit tests with a fake HTTP layer pass. It has never run against a real workspace.

### What you still have to arrange (I cannot do these from here)
1. **Publish the model** from the frozen SHA. Either Desktop once (Publish, no cases or screenshots needed) or Tabular Editor to an XMLA endpoint. XMLA writes need Premium, PPU or Fabric capacity: a Pro-only workspace will not accept them.
2. **Refresh it in the Service.** Our queries read a local folder through `pRootFolder`, so the Service needs an on-premises data gateway on a machine that holds the folder, or the files moved to SharePoint/OneDrive with the queries pointed there. If you have SharePoint, tell me and I will prepare that variant.
3. **Get a token** and run the script (see the header). Then do the FY parser step and the screenshots by hand.

## Earlier note: decision that was needed
Will B5 accept ExecuteQueries results from a Service workspace instead of Desktop? If yes, I can write `scripts/b5_execute_queries.py` that posts each case block from `tests/powerbi/` and applies the same PASS rules as `scripts/B5-DesktopRunner.ps1`. I have not written it yet because it would be untested code until a workspace exists.

## If you only have Power BI Pro (research, 2026-10-11)

What was confirmed by an official or vendor page:
- XMLA needs a Fabric F, Embedded, Premium or PPU capacity; Pro is not enough ([Tabular Editor docs](https://docs.tabulareditor.com/en/tutorials/powerbi-xmla.html), [Microsoft](https://learn.microsoft.com/en-us/fabric/enterprise/powerbi/service-premium-connect-tools)). So `model.bim` cannot be deployed to a Pro workspace from Linux or CI.
- The Arrow variant of ExecuteQueries needs a capacity ([Microsoft](https://learn.microsoft.com/en-my/power-bi/developer/execute-dax-queries-arrow/best-practices)). The classic endpoint has limits of 120 queries a minute and 100,000 rows or 1,000,000 values a query ([reference](https://learn.microsoft.com/en-us/rest/api/power-bi/datasets/execute-queries-in-group)).
- Fabric free trial: 60 days, F4 or F64 ([Microsoft](https://learn.microsoft.com/fabric/get-started/fabric-trial)). Fabric F2 pay-as-you-go is about US$0.36 an hour (third-party price pages).
- PBIX to PBIP conversion is Desktop-only; PBIP deployment is done with `fabric-cicd` ([Microsoft](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-deploy-fabric-cicd)).

Reported only in community posts, not confirmed:
- Classic ExecuteQueries works on a Pro-only shared workspace.
- A SharePoint Online folder read through the SharePoint folder connector refreshes on a schedule without a gateway. A synced local folder does not.
- A Fabric trial capacity exposes XMLA read/write.

Nothing found: a free DAX engine (OpenBI is a partial DAX-like tool, daxparser only parses, pymsasdax and pql-test need a running engine), or anyone running Power BI Desktop headless in CI. I did not search GitHub directly (access is limited to this repo); these came from web results.

Ranking: 1) Desktop runner (no extra setup), 2) Pro route: one Desktop publish, data from SharePoint, then `b5_execute_queries.py`, 3) Fabric trial, 4) F2 for one day. Your answers: Desktop is available, and SharePoint/OneDrive for Business is the fallback.
