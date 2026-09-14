# Recovered CM2 governance artifacts — 2026-07-24 rate card

**Recovered:** 2026-09-13, via Git history investigation (`git show 13fe0ac:<path>`).
Never deleted with malicious or careless intent — these files simply live on a
commit that was never merged into `main`:

```
Recovered_From_Commit: 13fe0acdf8f2ad3f41704f324fddf8b8f47f60a8
Commit_Message: "Add FY27 COGS + logistics CM2 calculation from supplied rate
                 card (staging only)"
Commit_Date: 2026-07-24
Author: Claude <noreply@anthropic.com> (Session 01FeZo4vCJRvRM8ACjfpqNhz)
Branch_Found_On: remotes/origin/claude/june-26-sales-data-xzbhub
Ancestor_Of_Main: NO (git merge-base --is-ancestor 13fe0ac main -> false)
Original_Paths:
  config/cm2_decision_register.csv       -> cm2_decision_register_D1-D11.csv
  config/cm2_formula.csv                 -> cm2_formula_v0.2-DRAFT.csv
  config/cm2_expense_taxonomy.csv        -> cm2_expense_taxonomy_v0.2-DRAFT.csv
  outputs/cm2/cm2_fy27_cogs_logistics.csv -> cm2_fy27_cogs_logistics_computed.csv
  scripts/cm2_cogs_logistics_fy27.py     -> cm2_cogs_logistics_fy27.py
Row_Count_Before: (unchanged -- copied verbatim, byte-for-byte via `git show`)
Value_Before/After: identical (verbatim copy, no transformation applied)
Validation_Status: VALID_RECOVERY_CANDIDATE for the GOVERNANCE STRUCTURE
                    (decision register, taxonomy, formula draft), NOT for the
                    underlying rate as a Finance-approved figure
Superseded_By: not superseded -- this is MORE rigorous than the later
               PowerBI/Reference/CM2_Provisional/config/cm2_formula.csv
               that DID reach main, and should replace it as the working
               document, pending Finance's actual review
```

## Why this matters (the actual finding)

This commit and the commit that produced the sibling `../config/cm2_formula.csv`
(the one already in this repo, dated internally "Approval_Date: 2026-08-30")
both reference the **same real event**: `"Screenshot rate card supplied
2026-07-24"` / `"Business supplied a monthly COGS % and logistics cost % rate
card for FY27 ... on 2026-07-24"`. The monthly logistics-% figures match
exactly (e.g. Jun-26 logistics = Rs170.45L in both). **The underlying rate
card itself traces to a real business communication on 2026-07-24** — it was
shared as a screenshot/image (not a machine-readable file), which is why no
spreadsheet source exists in the repo to independently verify the
transcription against, but it is not a fabricated demo number the way
`sources/Fact_Financials.csv` is (see BL-16's original finding).

**What went wrong on the branch that DID merge:** the version that reached
`main` (`PowerBI/Reference/CM2_Provisional/config/cm2_formula.csv`) took this
same real rate card and stamped it `Approved_By: MT Automation`,
`Approval_Date: 2026-08-30`, `Status: APPROVED` — a self-certification with no
real Finance sign-off behind it (see `docs/BUSINESS_LOGIC_REGISTRY.md` BL-16
for the full contradiction evidence: the approval date predates the actual
approval-request memo, etc.).

**What this recovered branch got right, that the merged version didn't:** its
`cm2_decision_register.csv` (D1–D11) leaves **every single decision correctly
marked `PENDING_APPROVAL`** — including D10 (does the rate apply to NSV or
MRP? material, ~2x difference) and D11 (is logistics cost already inside the
COGS rate, i.e. a double-count risk?) — with a recommended safe default, the
amount affected, and an evidence reference for each. This is a genuinely
better governance artifact than what's currently in the sibling folder, and
it never carries a fabricated approval stamp.

## Disposition

- **Not activated in production.** `dashboard/data.js` and
  `scripts/build_dashboard_data.py` do not read anything in this folder,
  exactly as the original commit's own message states.
- **Recommended use:** when a real Finance approval process for BL-16 CM2
  actually happens, use `cm2_decision_register_D1-D11.csv` as the decision
  document to walk through with Finance instead of writing a new one from
  scratch — it already frames the 11 open questions with the amounts and
  evidence at stake.
- **BL-16 Data Status upgraded** (see `docs/BUSINESS_LOGIC_REGISTRY.md`):
  from "rate card unverifiable" to "rate card traces to a real 2026-07-24
  business-supplied screenshot, consistent across two independent commits,
  but still not a machine-readable source file and still not Finance-approved."
  This is a meaningfully better evidence position, not a full resolution —
  Finance approval is still `PENDING_APPROVAL` on every line.
