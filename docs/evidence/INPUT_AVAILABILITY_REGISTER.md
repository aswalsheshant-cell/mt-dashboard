# Input availability register (2026-10-11)

Sweep: every file with a data extension (csv, xlsx, xlsb, xls, json, zip, parquet) that exists in any of 285 remote branches or 288 PR heads and is not on `main` with the same content: **199 paths, 236 content variants**. Machine-readable version of the blocked items: `config/pending_inputs.yml`. Files landed from PRs: `PowerBI/Reference/PR_INPUTS_MANIFEST.csv`.

## The inputs you asked about

| Input | In a PR or branch? | Result |
|---|---|---|
| TDP monthly file | No. Nothing named TDP or ACV exists outside `main`. | Still missing. Blocks pages 1, 7, 9, 10, 11. |
| Promo calendar Apr-Aug 26 | No. Only a festival uplift placeholder (13 rows, all `PLACEHOLDER_TBC`, PR 18), landed as reference. | Still missing (D12). |
| Store audit extract | No real extract. A 1-row template exists. | Template landed; still missing. Page 23. |
| Fill rate | Yes (PR 279): PO fill rate Apr-25 to Aug-26, unfilled reasons, PO vs target, QC json. | Landed, QC passed, not wired (owner decision). Page 24 still needs stock and delivery dates. |
| B3 | Partly (PR 252/267): claim input (32 rows), allocated (92 rows), alias decisions (7, all blank); CM2 decision register (PR 16). | Landed as seeds and reference, not wired. Finance approval and alias decisions missing. |
| B4 | Partly: provisional COGS/logistics assumptions (PR 16). | Landed as reference. Approved Jun-Aug rows missing. |
| B6 | No file anywhere. | Still missing (owner decisions). |
| Offtake before Apr-26 (MT store x article) | No. Only SIS-channel files Apr-25 to Jun-26 (not MT, restricted raw) and Jun-26 summary workbooks. | Still missing. |

## What was landed and how each file checked out

| Files | QC result |
|---|---|
| PO fill rate (4 files, PR 279) | 17 months; 6,151 rows, no duplicates on the grain (with `Chain_Raw`). Quantity fill rate 82.91% and unresolved-chain PO value 21.99% match the QC json. PO vs target ties to the monthly sums. 4 resolved chain names use HTML spelling (DMart, Metro C&C, Sancus (RMT), Walmart), not Chain Master. OTIF not measurable. |
| Distributor claim (3 files, PR 252/267) | Input 449.77 L equals allocated 449.77 L (the allocated total includes 2 UNALLOCATED_TIMING rows); all 32 chain x head pairs tie to 0.00 L; driver shares sum to 1. 19 allocation rows carry driver names pending alias; 7 alias decisions blank; 5 chain names not in Chain Master (DMart, Frankross, Sastasundar, Spar, Spencer's). Possible overlap with `PL_Expense_Input.csv` (FM-14): never add the two. |
| CM2 provisional pack (PR 16) | 9 of 13 decisions `PENDING_APPROVAL` (D1-D9); D10-D13 approved. **Arithmetic problems for Finance, found by recomputing:** (a) COGS monthly rows sum to 3,411.21 L but the total row and decision D1 say 4,411.21 L. This is not a plain 1,000 L typo: the monthly rows are priced on Apr/May GMV/MRP of 7,655.33 and 6,945.53 L, while D13 gives true Apr/May GMV/MRP of 11,760.60 and 10,275.28 L (31,336.79 L with Jun), and D1 applies 14.08% to that larger basis. The rows and the total sit on different bases. (b) D10 says 3,057.00 L for Apr+May; the rows give 2,057.00 L. (c) Jun-26 COGS 1,354.21 L is 14.56% of GMV/MRP 9,300.91 L against the stated 14.08% (1,309.57 L). (d) Logistics months sum to 361.04 L against a total row of 360.37 L; D11 quotes 275.53 L for Apr+May against 190.59 L in the rows; the Jun logistics row uses NSV 5,208.78 L while D12 and the GMV/MRP control give 4,167.38 L. (e) The Optimistic and Conservative scenario rows do not follow their notes (COGS 1,078.75 and 1,198.25 L; logistics 288.30 and 432.44 L, which are 0.8 and 1.2 times the logistics total). (f) D12 text says `data.js` holds 4,167.36 L; it holds 4,167.38 L. Nothing was corrected: the file is landed as written. |
| EAN product master (PR 16) | 3,494 EANs, no duplicates; every EAN in the Apr-Aug 26 offtake files is in it. 197 EANs marked Discontinued still sell (55.95 L NSV): for MDM. |
| NPI list (offline-agent branch) | 32 EANs; none has MT primary before Apr-26. 29 of 32 are in the TDP new-article list (the rule agrees with the business list); 14 have no MT primary sale at all (EB2B/SIS or distributor-routed). EANs carry a `.0` suffix. |
| FY27 GMV/MRP control (PR 16) | Jun-26 NSV control 4,167.38 L equals the Jun-26 primary MT value in `data.js`. |
| Store audit template | One example row carries a store code (1100500, Reliance Retail): confirm it is a dummy before wide use. |
| Business trackers (PR 18) | Events 0 of 13 approved, targets MISSING, NPI schema only, 11 of 12 business decisions pending. |

## Not landed (and why)

| Class | Files | Why |
|---|---|---|
| RESTRICTED_RAW | 15 SIS offtake files, `MTD_Primary_Jun_26.csv` (ship-to and invoice level), `secondary_distributor_chain_Jun_26.csv` (has EMP ID and KAM columns), `primary_article.csv`, `StoreChainMaster.csv/json`, `StoreMaster.csv`, older versions of the monthly offtake and primary article files | Store, customer or article level raw extracts: CONFIDENTIAL in a public repo (I-2 pending). Use `scripts/restore_branch_files.py`. |
| SYNTHETIC | `Primary_Article_Synthesized_FY25.csv` (already tracked on `main` under `RawDataFolders/Primary_Derived_FY25`, never read by any query: a test pins that), `forecast_outputs/*/synthetic_margin_master.csv`, `Fact_*.csv` in `PBIX_Build_Package` | Estimated or generated data. Never loaded. |
| NEEDS_OWNER | `ArticleMaster.csv` (936 rows, two variants; `main` has 13), `ChainAliases.csv`, `Secondary_Cont_Pct_Jun26.csv` (678-line distributor x brand x chain aggregate, no store or employee columns: probably safe, owner to confirm), `ChainMarketShare_May26.csv`, `DistributorRouted_Articles.csv`, `ChainAccount_Mapping_*`, `FY2627_Targets.csv` variant | Different content from `main`; the owner has to say which is right. Aliases are already in query 11. |
| OUT_OF_SCOPE | `margin_repository/*`, `releases/*.zip`, `reports/*`, `qc/*`, `gh-pages` outputs, tsconfig and tool configs, skill files | Release packages, decks and tooling, not dashboard inputs. |
| SUPERSEDED | older copies of files that are on `main` | Same path, older content. |

## Blocked pages and what unblocks each
Pages 1, 7, 9, 10, 11: TDP monthly file. Page 22: alert rules. Page 23: real store-audit extract. Page 24: stock, delivery dates and the PR 279 decision. The 11 PARTIAL pages are missing periods (offtake before Apr-26, Store Cuts and Nielsen before Apr-26), see `PowerBI/full_report_pages.json`.

## PR #299 (closed 2026-10-11, superseded by PR #305)

Branch `claude/full-report-on-main` is kept. Not ported to `main`: TMDL dataset folder, CM2 Governed page, `cm2.views` HTML block, `reconcile_context`. Bring any of these back only as a new PR on current `main`.
