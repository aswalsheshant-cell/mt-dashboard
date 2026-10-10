# Power BI Desktop runbook

Rebuilt by `scripts/build_desktop_validation.py`. Do not edit the expected values by hand.

Expected values are what the raw files should give. They are not Desktop results. Fill the last column from DAX Studio.

## Steps (about 30 minutes)

1. Pull branch `claude/gallant-shannon-wou27y`. Before anything else, run the two read-only commands in `docs/evidence/powerbi_full_ledger.md` and compare your 20 deletions with the ledger. Do not restore or clean.
2. Install Tabular Editor 2 (free) and DAX Studio. Open Power BI Desktop with a blank report.
3. Start Desktop with a blank report and keep it open. Find its local port: in Tabular Editor use File, Open, From DB, and pick the Power BI Desktop instance (a server like `localhost:5xxxx`).
4. In Tabular Editor: File, Open, From File, `PowerBI/model.bim`. Model, Deploy, choose that Desktop instance, and tick Deploy Model Structure, Deploy Connections and Deploy Shared Expressions. `model.bim` already carries the `pRootFolder` parameter and the two helper functions; you do not paste any query. If Tabular Editor shows an error, send the exact message.
4b. In Desktop: Transform data, Manage parameters, set `pRootFolder` to your local `PowerBI` folder, for example `C:\Users\you\mt-dashboard\PowerBI`. Spaces in the path are fine. No quotes and no trailing slash. Leave `pPrimaryChannel` at `MT` (the MT basis); set it to `ALL` only to check the all-channel total. The default is `C:\MT-Dashboard`, which will not exist on your machine.
5. In Desktop: Home, Refresh. If a query fails, copy the query name and the full error text, and send it. Do not edit measures to get around it. If a query says it cannot find `#"Some Name"`, that is a query-to-query reference; send it as is.
6. Save As `.pbip` (Power BI Project) so Desktop writes the full model files.
7. In DAX Studio: connect to the model, open `PowerBI/TabularEditor/05_DAXStudio_Validation.dax`, run Q1 to Q10 one at a time.
8. Record each result below. A mismatch is a finding. Do not adjust a measure until the cause is traced to a source file or query.
9. Copy `PowerBI/PBIR_Generated/definition/pages/` into the report's `definition/pages/` (keep your two current pages first: `python scripts/generate_pbir_pages.py --existing-pages-json <your pages.json>`). Open the report and screenshot every page.
10. Run B5 separately: `docs/evidence/B5_RUN_SHEET.md`. B5 stays blocked until its own exit rule is met.
11. Publish a private draft to My workspace only after steps 5 to 9 are clean. Record the URL and say it is a manual import refresh.

## Checks

| # | Check | Expected | Desktop result | Match |
|---|---|---|---|---|
| Q1 | Row counts (tables that should have data must be above 0; empty watch folders show 0) | Primary Article, Offtake, ShipTo, Secondary, Claim Master, Promo above 0. Primary Sales, Nielsen, TDP are 0 until their files arrive. |  |  |
| Q2 | Primary Article NSV by FY and Channel (Rs lakh) | Default pPrimaryChannel = MT, so only MT rows load: FY 25-26 MT 30,684.99 and FY 26-27 (Apr-Aug) MT 21,075.63, with no EB2B or SIS rows. With pPrimaryChannel = ALL you would also see EB2B 1,965.20 and SIS 250.17 for FY 25-26 (total 32,900.36). |  |  |
| Q3 | FY 25-26 Primary NSV (Rs lakh) | 30,684.99 with the default pPrimaryChannel = MT (the MT basis). It reads 32,900.36 only if the parameter is set to ALL. |  |  |
| Q4 | Offtake Apr-Aug 2026, gross and MT split (Rs lakh) | Gross [Total Offtake NSV] 21,553.85. [Total MT NSV] 17,936.36, [Total RBC NSV] 2,582.17 and EB2B 1,035.14 (Chain Master channel, after the alias step in query 11). FSN is EB2B (owner decision 2026-10-10), so MT + EB2B = 18,971.50, the dashboard figure ex Reliance Brand Counter (18,971.68). Chains with no Chain Master row: 0.18 L (Centro 0.18). |  |  |
| Q5 | Offtake by month, gross and MT ex Reliance Brand Counter (Rs lakh) | Gross: 2026-04 4,024.00; 2026-05 4,527.61; 2026-06 4,304.76; 2026-07 4,067.28; 2026-08 4,630.21. Dashboard ex RBC (data.js; [Total MT NSV] will be lower by the unmatched chains, see Q4): 2026-04 3,588.51; 2026-05 4,019.42; 2026-06 3,840.46; 2026-07 3,621.47; 2026-08 3,901.83 |  |  |
| Q6 | Primary ShipTo NSV by FY (Rs lakh). Catches the double-load of overlapping snapshot files | FY 24-25 23,325.30, FY 25-26 32,900.36, FY 26-27 9,955.63 (Apr-Jul only; the composite file has no Jun-26 and no Aug-26 rows). If FY 25-26 is near double (about 65,800), the two subset files are being loaded again. |  |  |
| Q7 | Primary Article rows with no Chain (header-spelling bug check) | 0, or only rows that are genuinely unmapped distributor rows. A count in the tens of thousands means the Chain column is not being read. |  |  |
| Q8 | Promo contribution placeholder check | Minimum is blank or above -1,000,000,000. A value near -9.2e18 means the placeholder cleanup did not run. |  |  |
| Q9 | Date table range | Starts at or before Apr 2024 and runs past Aug 2026. |  |  |
| Q10 | MoM Growth % by month (sanity) | No blank or absurd values for months that have data. Months with no data stay blank, not zero. |  |  |

## Known gaps that are not errors

- Primary Weekly, Nielsen and TDP raw folders are empty. Their tables refresh as empty. Pages that need them show an incomplete banner.
- Offtake FY26 is not in `Offtake_Monthly` (it starts Apr-26), so the model cannot show the 31,119.88 L FY26 baseline. That figure lives in `dashboard/data.js`.
- Primary Article loads MT-channel rows only (parameter `pPrimaryChannel`, default MT). Set it to ALL to load EB2B and SIS as well; the total then reads 32,900.36 L. Primary ShipTo has no Channel column and is all channels (FY 25-26 32,900.36 L), so it will not equal Primary Article on the MT setting.
- Store Cuts files cover Apr-26 to Aug-26 only.
- FSN offtake maps to the Chain Master row `Nykaa (FSN)`, channel EB2B (owner decision 2026-10-10), so it is not in [Total MT NSV].
