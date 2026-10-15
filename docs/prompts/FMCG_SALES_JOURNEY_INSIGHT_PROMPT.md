# FMCG Sales Journey: prompt to turn the 16 images into project insights

Owner: MT Channel Analyst Lead. Status: ready to use (docs only; no dashboard, Power BI or data change).

The images are one KPI ladder: MT basics, Numeric Distribution, Weighted Distribution, Effective Coverage,
Productive Calls, Strike Rate, AOV, Sales Mix, Value vs Volume, Gross Margin, Promotion ROI, Discount Management,
Net Sales Value, Contribution Margin. Day 20 (Sales Target Setting) is announced in the series but not in the images.

## 1. What the project can compute today (checked against the repo, 2026-10-14)

| Day / KPI | Can the project compute it today? | Source / gap |
|---|---|---|
| 5 Numeric Distribution | Yes, in-house proxy | Store x article offtake (Apr–Aug'26) and the store master. Not Nielsen ND; "relevant outlets" must be defined. |
| 6 Weighted Distribution | Yes, in-house proxy | Share of a chain's offtake value sitting in stores where the SKU sells (store-level offtake). Nielsen WD needs the TDP file (not supplied). |
| 8–10 Effective Coverage, Productive Calls, Strike Rate | **No** | Needs visit / call / order data from the field-force app. Not in the repo. |
| 11 AOV | Partly | Order value per PO / invoice from Primary article files (Inv No., PO Number). Not store-visit orders. |
| 12 Sales Mix | Yes | Brand, category, sub-category, pack, chain mix in Primary and Offtake. |
| 13 Value vs Volume | Yes | NSV and Qty in Primary; Offtake NSV and units. Price/mix split exists in `pvm`. |
| 14 Gross Margin | Provisional | Standard cost = % of MRP (not SAP COGS). Article margin only for some months. |
| 15–16 Promotion ROI | **Not fully** | Promo files hold offer depth only (no spend, no baseline) — data contract frozen in #257. Break-even uplift = discount ÷ (margin − discount) can be computed. |
| 17 Discount Management | Partly | TOT% / pass-on and offer depth by chain; no discount-by-customer-by-SKU leakage file. |
| 18 Net Sales Value | Yes (partly) | Gross MRP → TOT/GST → invoice NSV; returns shown in Primary; rebates/claims provisional (Q1 FY27). |
| 19 Contribution Margin | Provisional | CM2 chain-wise is on the dashboard but cost heads are incomplete (COGS, logistics, field force not loaded). |

Two cautions found in the images (the prompt tells Claude to check them, not copy them):
- Day 17's discount examples (5% on 20% margin = "17% of profit gone"; 10% on 30% = "39%") do not tie to the image's own formula (discount ÷ margin gives 25% and 33%).
- Examples are in SAR; the project is in INR Lakh (NSV) and uses its own FY rule (Apr–Mar).

## 2. The prompt (copy and paste, then attach the images)

```
ROLE
You are the Modern Trade (MT) channel analyst for Honasa / Mamaearth. Work in simple office language, main answer first, short paragraphs. Do not write like an AI. No fancy words.

GOAL
I am attaching 16 images from the "FMCG Sales Journey" series (Days 2, 3, 5, 6, 8 to 19). Turn them into (a) a KPI logic register, (b) a test of what our project can and cannot compute today, and (c) ready-to-use insights and actions that help grow MT business. Keep a step tracker of everything you do.

STEP 1 - READ THE IMAGES (no opinions yet)
For each image give one row: Day | KPI | exact formula as printed | the printed example (inputs and answer) | the "real question" the post asks | the action chain it shows.
Then re-calculate every printed example yourself. If a number does not tie to its own formula, flag it as "IMAGE DOES NOT RECONCILE" and show the correct figure. Do not copy a wrong number into our logic.

STEP 2 - TRANSLATE TO OUR PROJECT
For each KPI write our version of the formula using our terms and units: NSV, offtake, primary, distributor secondary, MoM, YoY, L3M Avg, contribution %, chain, account, zone, state, brand, category, sub-category, pack size, visibility, POSM, planogram, DMS, QBR. Amounts in INR Lakh; FY runs Apr to Mar (Apr-Dec of year Y = FY(Y+1); Jan-Mar of year Y = FY(Y)).
Keep the three measures apart and name them every time: Primary (SAP billing), Distributor Secondary, Offtake (chain POS). Never mix them in one growth rate. Reliance Brand Counter is excluded from Offtake only, never from Primary.

STEP 3 - DATA CHECK (be strict)
For each KPI say one of: COMPUTABLE NOW / COMPUTABLE AS PROXY / NOT POSSIBLE. Name the exact source file or dashboard block (for example offtake_store_article files, primary article files, dashboard/data.js blocks, ChainMaster, TDP file). If a source is missing, name the exact file or field needed and who owns it. Never invent, estimate or back-fill a number. Show "–" for unknown, never 0.
Known limits to respect: store-level offtake starts Apr'26; FY25 is distributor secondary only; promo files carry offer depth, not spend; CM2 cost heads are incomplete; no visit / call / order data from the field force exists.

STEP 4 - RUN THE LOGIC ON OUR DATA (only where Step 3 allows)
For the latest month and FY-to-date, by chain, then by brand and category, compute: numeric distribution proxy, weighted distribution proxy, sales mix, value vs volume (price vs volume vs mix), gross margin, break-even uplift for each promotion depth (= discount % / (margin % - discount %)), gross-to-net % (MRP to invoice NSV), and contribution margin where cost heads exist. Use L3M Avg as the baseline, not a single month. Show the formula next to every number.

STEP 5 - INSIGHTS, in this order for every finding
1. What happened (the number, the period, the measure).
2. Why it happened (the driver you can prove from our data; if you cannot prove it, say "cause not proven" and list what to check).
3. Business impact (INR Lakh and % of chain NSV; give the sizing method).
4. Action needed (one action, an owner by role, a due date or timeline, and the number that will show it worked).
Rank findings by INR Lakh impact. Use the post's own tests: "How many relevant outlets are still missing, and why?", "Did we hit the target, or did the right products and categories hit it?", "Sales up in value but down in volume: price or demand?", "Does the discount earn more than it costs?", "Which chain contributes, not just sells?".
Cover at least: distribution gaps (chain x article x store), mix shift to low-margin lines, value-up/volume-down chains, promotions below break-even, chains with high gross sales but low contribution.

STEP 6 - QC BEFORE YOU ANSWER
Check and report PASS / FAIL: totals tie to dashboard/data.js; Primary, Offtake and Secondary are not mixed; FY25 is not used as a baseline; no NaN or blank shown as zero; every ratio has a stated denominator; sums by chain equal the total; each insight has an owner and a timeline. List exceptions and what is still unverified.

STEP 7 - STEP TRACKER (keep updating it, show it at the end of every answer)
Table with columns: Step # | Day / KPI | What was done | Evidence (file, block, PR link) | Result (DONE / PARTIAL / BLOCKED) | Blocker and owner | Next action | Date.
Mark BLOCKED_EXTERNAL_EVIDENCE for anything that needs data we do not have. Never mark DONE without evidence.

OUTPUT FORMAT
A) Main answer in 5 lines. B) KPI logic register table. C) Data readiness table (Step 3). D) Top 10 insights in the 4-part format. E) QC result. F) Step tracker. G) What I need from you (max 5 questions, most important first).
Assumptions go in one short list at the end. If my ask is unclear, ask ONE question only.
```

## 3. How to use it
1. Paste the prompt in a new chat and attach the 16 images.
2. Ask Claude to keep the step tracker; save its tracker table into `FMCG_SALES_JOURNEY_TRACKER.md` after each run.
3. Treat anything marked BLOCKED_EXTERNAL_EVIDENCE as a data request to the named owner, not as a result.
4. Numbers in a reply must be checked with the project rules: `github-qc-before-answer` (QC VERIFIED or NOT IN REPO).
