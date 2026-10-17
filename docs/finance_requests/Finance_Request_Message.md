# Finance request: AssumptionTable rows, Jun to Sep'26

Attach: `docs/finance_requests/Finance_Assumption_Request_Jun_Sep26.csv` (one row per month, ALL chains / ALL brands / ALL categories; every figure left blank on purpose).

## What to fill, per month
| Column | Meaning | Format |
|---|---|---|
| Gross Margin % | Portfolio gross margin for the month | Fraction, e.g. 0.52 for 52% |
| Trade Spend % | Trade spend as % of NSV | Fraction, e.g. 0.08 |
| Visibility Spend | Rupees for the month | Number |
| Scheme Spend | Rupees for the month | Number |
| Other Spend | Rupees for the month | Number (0 if none) |
| Contribution Margin % | CM for the month | Fraction |
| Remarks | Your approval reference | `Approved: <ticket / mail subject> <date>` |

Please type the approval reference yourself. We do not pre-fill it, and the dashboard check only passes when a real reference is there.

## Also needed
1. **Apr'26 and May'26:** the current rows say "Default portfolio assumption". Please confirm them with a reference, or send corrected figures.
2. **May'26 chain rows** (Reliance Retail, Wellness Forever and others in the table): confirm with a reference, or tell us to remove them.
3. **COGS basis:** the provisional COGS total is 4,411.21 L but its months add to 3,411.21 L. Please confirm which GMV / MRP basis is right.

## Message options

**1. Short formal**
Please share the approved P&L assumptions (gross margin %, trade spend %, visibility, scheme, other spend, contribution margin %) for Jun to Sep'26 in the attached sheet, with your approval reference in Remarks. Please also confirm or correct Apr and May'26, the May chain-level rows, and the COGS basis (4,411.21 L vs 3,411.21 L). Until we have these, the dashboard shows margin as pending Finance for those months. Could we have them by <date>?

**2. Slightly firm**
We cannot show margin for Jun to Sep'26 until Finance gives approved assumptions; the dashboard check is blocking. Please fill the attached sheet and add your approval reference in Remarks by <date>. Apr and May'26, the May chain rows and the COGS basis also need your confirmation. We will not estimate or carry forward any figure.

**3. Simple**
Hi, can you fill the attached sheet with the margin and spend assumptions for Jun, Jul, Aug and Sep'26? Please add your approval reference in the Remarks column. Also please confirm Apr and May, and which COGS total is right (4,411.21 L or 3,411.21 L). Thanks.

## What happens when it comes back (our side)
1. Check four proofs: figures, named approver, date, reference; percentages as fractions; GM% above CM%.
2. Add the rows to `PowerBI/SeedData/Masters/AssumptionTable.csv` (add, never overwrite).
3. Run `python scripts/check_assumption_coverage.py` (should read OK), update the pinned gap tests, rebuild P&L, re-run the dashboard sweep.
Owner: Finance (or the repo owner, who may approve per the 2026-10-08 record but must still state the figures). Timeline: set the date in the message.
