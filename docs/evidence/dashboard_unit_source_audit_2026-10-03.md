# Dashboard source unit audit — 2026-10-03

**Status:** source-unit evidence collected; Power BI import and live desktop reconciliation are still pending. B5 remains BLOCKED_PENDING_DESKTOP_EVIDENCE. This is not a release clearance.

## Reproducible run

- Branch: `codex/dashboard-unit-audit-20261003`; audited head: `2e8ea0b1d9580a7183105ca835893e2505885e22`.
- [Successful source-audit run](https://github.com/aswalsheshant-cell/mt-dashboard/actions/runs/37108289230): targeted pytest 6 passed, 25 committed CSVs read, no source write. [Private aggregate artifact](https://github.com/aswalsheshant-cell/mt-dashboard/actions/runs/37108289230/artifacts/11269300041), expires 2026-10-10 08:03 UTC. Full JSON was also printed in the job log and reviewed there because this connector cannot download the artifact ZIP.
- Auditor: `python scripts/audit_dashboard_units.py --repo-root . --out "$RUNNER_TEMP/dashboard-unit-audit.json"`. Signed decimal totals preserve returns. SHA-256 and row counts identify exact source files.

## Unit finding

| Family | Files | Source rows | Raw signed amount | Unit ruling and basis |
|---|---:|---:|---:|---|
| Offtake store × article, Apr–Aug'26 | 5 | 11,31,142 | 21,627.15 | **Lakh** for NSV. `docs/DATA_LINEAGE.md` and `scripts/build_dashboard_data.py` declare that source contract; sampled NSV/MRP ratios are about 0.00000542 raw and 0.542 after ×100,000. MRP is rupees. |
| Primary article monthly | 17 | 3,62,761 | ₹5,51,39,94,712.98 | **Rupees** for `Inv. Net value(LOC)`. `docs/DATA_LINEAGE.md` converts this field ÷100,000 for HTML lakh output; aggregate is 55,139.95 lakh, matching its documented all-months figure. Do not scale on Power BI import. |
| Primary ShipTo snapshots | 3 | 37,882 | **Do not sum these files** | Source appears rupee-sized and query 15 defaults to no conversion. The FY24–26 composite overlaps both narrower snapshots; `fnCombineFolder` currently reads all three. This is an unresolved import-duplication risk, separate from source unit. |

### Governed Offtake scope

The gross audit retains every source row. The governed column excludes only rows where `Chain Name` contains “reliance” and `Store Type` equals “brand counter,” matching the builder rule. Negative values keep their sign. No CSV was edited or row deleted.

| Source month file | Rows | Gross NSV (lakh) | Excluded RBC rows | RBC NSV (lakh) | Governed NSV (lakh) | SHA-256 |
|---|---:|---:|---:|---:|---:|---|
| offtake_store_article_Apr_26.csv | 2,21,797 | 4,024.00 | 24,259 | 435.49 | 3,588.51 | `9f98d2df1d0e5ba399960b5e5a2983784993a7a0fb12e682cbc700d1f532d5af` |
| offtake_store_article_Aug_26.csv | 2,30,057 | 4,703.50 | 24,186 | 728.38 | 3,975.13 | `aa9e683ead6d938feaa9ce9f217f091c05b5fb002ac8e6bf3af01de65e122462` |
| offtake_store_article_Jul_26.csv | 2,21,548 | 4,067.28 | 22,818 | 445.81 | 3,621.47 | `9786d5bb2587517fe66e9452923c1f2f6ab3c7e2ce62a66e249789717feb37fa` |
| offtake_store_article_Jun_26.csv | 2,29,460 | 4,304.76 | 24,058 | 464.30 | 3,840.46 | `b4ad1179e0d4afb28094ac07918b92f6ff51d1f1dee7ffff24aca8c31fedd574` |
| offtake_store_article_May_26.csv | 2,28,280 | 4,527.61 | 24,636 | 508.18 | 4,019.42 | `cdf7744e4dc31cce9f0158a5b91f88beef3d449f3de84da5255c9f424a9d253f` |

The Jul'26 governed total is **3,621.47 lakh (₹36.2147 Cr)**, consistent with the documented ₹36.21 Cr Jul benchmark at display precision. Gross Jul would be 4,067.28 lakh and includes the duplicated RBC breakout.

## Coverage and blockers

- Raw Offtake `Month` labels are mixed: Apr has `Apr'26` plus Excel serial `46113.0`; Jun has `Jun`, `Jun '26`, and `Jun'26`; Jul and Aug use bare month names. The current Power Query 11 parser assumes a quote and year. Monthly comparison must normalize from source file/date fields and mark missing periods NOT_COMPARABLE, never zero.
- The five Offtake CSVs cover only FY27 Apr–Aug'26. FY25/FY26 Offtake history lives in preaggregated HTML data, not this watch folder. A Power BI vs HTML FY25/FY26 comparison cannot be inferred from these CSVs.
- Primary and Offtake are distinct metrics. Equal numbers are required only for the same metric, period, unit, and channel scope. Live Power BI Desktop refresh and B5 governed cases are outstanding.
- PR #119 remains frozen; PR #267 remains HOLD. No merge is proposed.

## Source identity

| Family | File | Rows | SHA-256 |
|---|---|---:|---|
| Primary_Article_Monthly | primary_article_Apr_25.csv | 18,621 | `bc6765d94666d0ca3cd411f6e6548567c9affe049b6bb6e339e7f3f74ef79ca2` |
| Primary_Article_Monthly | primary_article_Apr_26.csv | 30,757 | `f63066b94456f0035e12a41027e16a78a452d90e0d5c6d21d30dd8a4a33e45a2` |
| Primary_Article_Monthly | primary_article_Aug_25.csv | 13,520 | `1858da51b2301ec7ba732170a06a1439e4fb7bd3dc9692972372b86d508048eb` |
| Primary_Article_Monthly | primary_article_Aug_26.csv | 19,070 | `959124f7ff39b82fce67595cff5559a5c1d297f5deb0aad7ef73287135f3b686` |
| Primary_Article_Monthly | primary_article_Dec_25.csv | 24,642 | `54aa7a4b5ec4638bd8ff72a5262b0a18abdd96eda80e1013967b16559f3e7932` |
| Primary_Article_Monthly | primary_article_Feb_26.csv | 14,844 | `0f0c35d417caf7e1d3f0972b2d8b8abd20fb068eb58cc8e7b81d5a3d587bb282` |
| Primary_Article_Monthly | primary_article_Jan_26.csv | 33,035 | `525afd39a37cd867beab642d442c652bcddfe78a0add594ef82d5242504327a9` |
| Primary_Article_Monthly | primary_article_Jul_25.csv | 16,643 | `008d706854ddf9ce2423d3ced2420853b2b5adea802c7531549e53b7b20f02b9` |
| Primary_Article_Monthly | primary_article_Jul_26.csv | 31,355 | `497e55d2b362313efeede535d7b1b8e5402864587672368b11a615e21720545e` |
| Primary_Article_Monthly | primary_article_Jun_25.csv | 14,634 | `82c395071f2e4a1e2607d624d5cbae854bab370d53496ffc78d0c969354a8e94` |
| Primary_Article_Monthly | primary_article_Jun_26.csv | 23,192 | `1de0ad86e2a266606bec3ec8281b5720edd44525d09a277abe18aa6d516d121d` |
| Primary_Article_Monthly | primary_article_Mar_26.csv | 17,365 | `e166173d4855de57161e20bd217469f8fbdf9cd1bb31535197ab5444f163bd1b` |
| Primary_Article_Monthly | primary_article_May_25.csv | 16,866 | `f4c21fe8e489c15acccbb1403363d8f59c7161ae013e01bf385cea35711cad8c` |
| Primary_Article_Monthly | primary_article_May_26.csv | 19,399 | `0c10f2d6b28bc8e10cdad72941e8273066635893205cd5041dc4714b2cac95c6` |
| Primary_Article_Monthly | primary_article_Nov_25.csv | 26,232 | `b1a675fb1395c14f08553bd45a2f4136be53b664210ea79dd28a468f39ad15d9` |
| Primary_Article_Monthly | primary_article_Oct_25.csv | 27,912 | `f3e739e277c19b2acb34e4d5bfd0830ab137e05c83fa1ca4b659fa7d67749331` |
| Primary_Article_Monthly | primary_article_Sep_25.csv | 14,674 | `5a2a6ab49ceb4cb8d981cd145606e222bfb91cd1ff608086fdeaa11b91ed9b3d` |
| Primary_ShipTo_Monthly | Primary_ShipTo_FY24-25.csv | 7,883 | `cec396f9eef9333dcbb9b3093afc072a69d06b60de4bdf87ad9d74112bdcef2d` |
| Primary_ShipTo_Monthly | Primary_ShipTo_FY24-26_Composite.csv | 18,941 | `6d432e0d0294c8c0fdff517aca9f35066511b8f53720986502a8572c7c9028d1` |
| Primary_ShipTo_Monthly | Primary_ShipTo_FY25-26_to_May26.csv | 11,058 | `74e3bc9c206832ca20e3619250c4479e2f6c1f2542a59253d28bd5e913f68d24` |
