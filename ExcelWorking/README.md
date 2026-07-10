# MT Sales Summary — auto-updating quarterly working file

`MT_Sales_Summary_Automated.xlsx` is a **review-stage draft** that verifies and
automates the MT (Modern Trade only — no GT) format/chain quarterly summary.

Regenerate with:

```bash
python scripts/build_mt_sales_summary.py
```

## Workbook structure

| Sheet | Purpose |
|-------|---------|
| **Source_Data** | Wide monthly chain-level matrix (Jun-25 → Jun-26). **Paste the pending Jun-26 column here.** Blank = not received (never enter 0). |
| **Mapping** | Format → Chain → Summary Bucket reference (from the mapping screenshot). |
| **Summary** | Format & chain quarterly table Q1-24 → Q1-26, plus GO Sequential QoQ, GO QoQ, Remarks. |
| **Chart** | Grand-Total quarterly trend line, auto-linked to the Summary. |
| **QC** | Considered / excluded data, quarter mapping, pending Jun-26 list, mapping gaps, mismatch checks. |

## How the automation works

- **Q1-26 = Apr-26 + May-26 + Jun-26**, pulled from `Source_Data` by Summary Bucket via `SUMIFS`.
- A row shows **"Pending"** (not −100%) whenever any of its chains has May-26 filled but Jun-26 blank.
- Once the real Jun-26 values are pasted into `Source_Data`, every "Pending" clears and the
  Summary table + chart recompute automatically (the workbook is set to full-recalc-on-open).
- Historical quarters Q1-24 → Q4-25 carry the verified Screenshot-1 values.

## Key corrections applied

1. **−100% bug fixed** — blank Q1-26 was being treated as 0. Now blank → "Pending".
2. **SIS format row added** (was missing) — marked "Source data required" until SIS data is provided.
3. **Chart labels corrected** (old chart mislabelled the quarter order / ended at "Q4-26").
4. Quarter logic verified: Q1 = Apr-Jun … Q4 = Jan-Mar; FY labelled by start year (Apr-26 → Q1-26).

## Open items for confirmation (see QC sheet)

- Mapping for chains not in the mapping sheet: **Spar, Beauty & Nutrie, National Mart, Sumo Save, Apna Mart** (currently assumed).
- Possible duplicate: **Ratanadeep vs Ratandeep**.
- **SIS** chains + values still required.
- Pre-Jun-25 chain-level months (for Q1-24 → Q1-25) were not in the source and are carried as verified totals.
