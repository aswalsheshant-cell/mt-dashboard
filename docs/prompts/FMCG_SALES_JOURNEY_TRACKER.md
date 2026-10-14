# FMCG Sales Journey: step tracker

Keep this table current. Status words: DONE (evidence exists), PARTIAL (proxy or part only), BLOCKED_EXTERNAL_EVIDENCE
(needs data we do not have), CONCEPT (no calculation). Never mark DONE without a file, dashboard block or PR link.
Last updated: 2026-10-14. Prompt: `FMCG_SALES_JOURNEY_INSIGHT_PROMPT.md`.

## A. The ladder (Days 2 to 19)

| Day | KPI | Formula as printed (checked) | Project status | Evidence / source | Blocker and owner | Next action |
|---|---|---|---|---|---|---|
| 2 | What is MT, focus areas | Concept: assortment, listing, shelf availability, planogram, promotions, visibility, stock, offtake | CONCEPT | Dashboard tabs map to these areas | – | Use as the checklist for chain reviews |
| 3 | GT vs MT | Concept | CONCEPT | – | – | – |
| 5 | Numeric Distribution | outlets with product / relevant outlets x 100 (600/1,000 = 60%) | PARTIAL (proxy) | Store x article offtake Apr-Aug'26; store master; in-house distribution view (`dashboard/tdp_inhouse.js`) | "Relevant outlets" not defined; Nielsen ND needs the TDP file (MT Channel Analyst Lead) | Define relevant outlets per chain, then compute by chain x article |
| 6 | Weighted Distribution | share of category sales value held by outlets where the product is present (ND 60% can be WD 80%) | PARTIAL (proxy) | Store-level offtake value | Nielsen WD needs the TDP file | Proxy = chain offtake value in stores where the SKU sells / chain offtake value |
| 8 | Effective Coverage | visited, ordered, SKU available (90 / 75 / 65 of 100) | BLOCKED_EXTERNAL_EVIDENCE | – | Visit, call and order data from the field-force app (Sales Ops) | Request file: store, date, visited Y/N, order Y/N, SKUs ordered |
| 9 | Productive Calls | productive calls / effective calls x 100 (22/30 = 73.3%) | BLOCKED_EXTERNAL_EVIDENCE | – | Same call data (Sales Ops) | Same request |
| 10 | Strike Rate | orders / effective calls x 100 (24/40 = 60%) | BLOCKED_EXTERNAL_EVIDENCE | – | Same call data (Sales Ops) | Same request |
| 11 | Average Order Value | total sales value / number of orders (48,000 / 24 = 2,000) | PARTIAL | Primary article files carry Inv No. and PO Number (order value per PO / invoice, not per store visit) | Store-visit orders need the call data | Compute AOV per PO by chain, label "primary PO basis" |
| 12 | Sales Mix | category sales / total sales | DONE (data exists) | Brand, category, sub-category, pack mix blocks in `dashboard/data.js` | – | Add margin-weighted mix view |
| 13 | Value vs Volume | Value = volume x average price (500,000 to 549,000 while cartons fall 10,000 to 9,000) | DONE (data exists) | Primary and offtake NSV and units; `pvm` block (volume / price / mix) | – | Flag chains with value up and volume down |
| 14 | Gross Margin | (revenue - COGS) / sales x 100 (30%) | PARTIAL (provisional) | `profitability` block (standard cost = % of MRP, not SAP COGS); article margin for some months | SAP COGS per article (Finance) | Keep label "standard-cost basis" |
| 15 | Trade Promotion ROI | (incremental gross profit - promotion cost) / promotion cost x 100 (50%) | BLOCKED_EXTERNAL_EVIDENCE | Promo files hold offer depth only | Promotion spend and baseline (Finance / Marketing); data contract #257 | Request spend by chain x article x month |
| 16 | Promotion ROI, break-even | required volume uplift = discount % / (margin % - discount %) (10% on 30% needs +50%) | PARTIAL | Offer depth by chain x article; margin from article margin | Realistic baseline and post-promo dip | Compute break-even uplift per offer; compare with L3M uplift once baseline is agreed |
| 17 | Discount Management | share of margin given away; slab vs flat | PARTIAL | TOT% / pass-on by chain; offer depth | Discount by customer x SKU file; image examples do not reconcile (5% on 20% margin and 10% on 30% margin print 17% and 39%; discount / margin gives 25% and 33%) | Use our formula, not the printed figures |
| 18 | Net Sales Value | gross - discounts - schemes and free goods - returns and damages - rebates (1,000,000 to 875,000, gross-to-net 12.5%) | PARTIAL | Gross MRP to invoice NSV (TOT, GST) in primary; returns visible; claims provisional | Rebates and claims approval (Finance) | Show gross-to-net % by chain |
| 19 | Contribution Margin | net sales - COGS - variable selling and distribution costs (A 15% vs B 26% on the same gross margin) | PARTIAL (provisional) | Chain-wise CM2 on the P&L tab | COGS, logistics, field force, provisions not loaded; claims approval and 7 alias decisions pending (Finance) | Keep "CM2 provisional" labels; rank chains by contribution, not sales |
| 20 | Sales Target Setting | announced only | NOT STARTED | – | Image not supplied | – |

## B. Steps already taken in this project that map to the ladder

| Step | Ladder link | Evidence |
|---|---|---|
| Store check: new product vs distribution increase | Day 5 / 6 (distribution gaps) | PR #322 |
| One name per chain (Carrefour, H&B, Apna Klub, Azorte incl. Centro) | Day 5 / 6 / 12 (clean chain base) | PRs #321, #326 (draft) |
| Chain-wise CM2 with distributor claims (provisional) | Day 19 | PR #314 |
| PO billing fill rate (MT) | Day 2 stock and availability | PRs #307, #320 (draft) |
| Primary vs offtake gap, FY27 | Day 13 | `primary_offtake_gap` block |
| FY25 hidden on screens | Day 13 baseline hygiene | PR #323 |

## C. Run log (add one line per run of the prompt)

| Date | Run by | Days covered | Result | Open items |
|---|---|---|---|---|
| 2026-10-14 | – | prompt and tracker created | Ladder mapped to project data | Field-force call data, promotion spend, SAP COGS, TDP file |
