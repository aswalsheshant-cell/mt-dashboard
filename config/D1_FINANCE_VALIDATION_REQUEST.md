# Finance validation required — PR #16 · Decision D1

**To:** `[NAMED FINANCE OWNER REQUIRED — see §7]`
**From:** Data Engineering
**Raised:** 2026-07-25
**Response required by:** `[PROPOSED: 2026-08-01 — confirm or amend]`
**Blocks:** `GOV-FORMULA-DRAFT` (BLOCKED) · PR #16 stays unmerged until this is recorded

---

## 1. What is required

**D1 is a definitional decision that determines a value — please answer both parts.**

### Part A — the decision

> Is approved product cost (**COGS**) deducted **inside** reported CM2, or does CM2 stop
> at post-trade-spend contribution with COGS disclosed below it?

| Option | CM2 definition |
|---|---|
| **(a) INCLUDE** | CM2 = NSV − COGS − trade − field force − logistics − other |
| **(b) EXCLUDE** | CM2 = NSV − trade − field force − logistics − other; COGS shown below CM2 |

### Part B — confirm the underlying amounts

| Line | Value | Basis | Rate | Status |
|---|---|---|---|---|
| GMV/MRP sales | **31,336.79 L** | — | — | computed |
| NSV | **13,652.59 L** | — | — | computed |
| **COGS** | **4,411.21 L** | **GMV/MRP** (D10) | 14.08% blended | **confirm** |
| **Logistics** | **445.97 L** | **NSV** (D10/D11) | 3.27% blended | **confirm** |
| Total cost | 4,857.18 L | — | — | derived |
| Provisional CM2 | **8,795.41 L (64.42% of NSV)** | — | — | **not published** |

---

## 2. Period · entity · currency · units

| Field | Value |
|---|---|
| **Period** | Q1 FY27 — Apr-26, May-26, Jun-26 (Indian FY, Apr–Mar) |
| **Entity** | Honasa Consumer Ltd — Mamaearth, **Modern Trade channel only** |
| **Channel scope** | MT + EB2B + SIS |
| **Currency** | INR |
| **Units** | **Lakh (L)** — 1 L = ₹100,000. All figures above are in Lakh. |
| **Brand exclusions** | Pure Origin, Lumineve, Staze excluded from every figure |
| **Tax basis** | Excl-GST (NSV is already net of tax and TOT%) |

---

## 3. Current provisional values

**Two different CM2 figures exist. Neither is approved. Please note they are not the same measure.**

| # | Figure | Value | What it is | Where |
|---|---|---|---|---|
| 1 | **Published CM2** | **42,325.70 L = 99.9% of NSV** | NSV (FY26–FY27, TOT%-scope) − P&L expense rows. **The 99.9% is an artefact of example data**, not a real margin. | live dashboard, P&L tab |
| 2 | **Staged CM2** | **8,795.41 L = 64.42% of NSV** | Q1 FY27 NSV − COGS − logistics. Excludes trade/field-force/other. | `outputs/cm2/` — **not published** |

Figure 1 is 99.9% because the only expense data loaded is **47.65 L** from three rows
in `PL_Expense_Input.csv`, each marked `EXAMPLE ROW -- replace with real data`
(Visibility 12.50 + Scheme 28.40 + BA Cost 6.75). Both figures currently carry an
on-screen provisional banner.

> ⚠ **Correction recorded 2026-07-25.** D1's impact was previously logged as
> **1,922.66 L on an NSV basis**. That predates **D10** (APPROVED 2026-07-24), which
> settled that COGS applies to **GMV/MRP**. The true impact is **4,411.21 L** —
> the earlier figure understated it by **2,488.55 L (2.29×)**. Please decide against
> 4,411.21 L.

---

## 4. Source documents expected

| Input | Source | Provenance |
|---|---|---|
| COGS % / logistics % | Business rate card supplied 2026-07-24 | monthly rates, in repo |
| GMV/MRP Apr-26, May-26 | Article-level primary CSVs | tracked; brand exclusions applied |
| GMV/MRP Jun-26 | `MT+EB2B-MTD-Primary-June'26. (1).xlsx`, sheet `MTD-Primary-June'26.`, field `MRP Value` | SHA-256 `b73bf8ff…62ae3`; NSV control 4,167.38 L reconciles to 4,167.36 L within 0.02 L; seed `FY27_Monthly_GMV_MRP.csv`, status AUTHORITATIVE (D12) |
| NSV | `data.js` `detail_meta.fyx_primary.FY27.monthly` | derived from the same sources |
| **P&L expenses** | **`PL_Expense_Input.csv` — EXAMPLE ROWS ONLY** | **real monthly P&L expense file required** |
| Trade expense (D2/D3/D4) | `MTIndirect_Claim_April_26_to_June_26.xlsb` | 818.45 L candidate, pending |
| Field force (D5/D6/D7) | `MT_Spend.xlsx` | 692.94 L CTC + 18.22 L reimb, pending |

---

## 5. Dashboard cells and metrics affected

**Dashboard — P&L tab** (`dashboard/index.html`)
- KPI **Total P&L Expense** — currently 47.65 L (0.1% of NSV)
- KPI **CM2 Value** — currently 42,325.70 L (99.9% of NSV)
- KPI **MoM CM2 Movement**
- Chart **Chain-wise CM2** · Table **Chain-wise CM2 detail** (NSV / Expense / CM2 Value / CM2% per chain)
- Table **Expense by head** · **CM2 QC** table

**Data model** (`dashboard/data.js` → `cm2.*`)
`total_expense` · `expense_pct_of_nsv` · `cm2_value` · `cm2_pct` ·
`by_chain[]` · `by_brand[]` · `by_category[]` · `by_expense_head[]` · `monthly[]`

**Power BI** — `PowerBI/DAX/13_CM2_Measures.dax` (reads the same input file)

**Governance** — `config/cm2_formula.csv` (9 components, all DRAFT) · `config/cm2_decision_register.csv` D1

---

## 6. Required response — exactly one outcome

Please reply with **one** of:

| Outcome | What to supply |
|---|---|
| ✅ **CONFIRMED** | Option (a) or (b); confirmation that COGS 4,411.21 L and logistics 445.97 L are correct; approver name; date; source reference |
| ✏️ **CORRECTED** | Option (a) or (b); the **replacement value(s)**; the **source document/system** they come from; approver name; date |
| ⛔ **UNAVAILABLE** | Reason, and the **expected availability date** |

To clear the gate, five fields are needed per component in `config/cm2_formula.csv`:
`Include_Status` (INCLUDE/EXCLUDE) · `Approved_By` · `Approval_Date` · `Status=APPROVED` · evidence reference.

Partial sign-off **fails** rather than passes: `governance.py` raises
`GOV-WEAKAPPROVAL` (FAIL) for any approval missing approver, date or evidence.

**Separately required:** real rows to replace the three EXAMPLE rows in
`PL_Expense_Input.csv`. Approving D1 alone will **not** clear the provisional banner.

---

## 7. Owner and deadline — both need to be set by a human

Two fields in this request cannot be filled in by engineering:

1. **Named owner.** The register records the owner as the team `Finance`, not a person.
   A named individual is required so the request can be actioned and chased.
2. **Response deadline.** 2026-08-01 is a proposed placeholder only.

---

## 8. What happens on response

1. Update D1 and `config/cm2_formula.csv` with the supplied decision, approver, date, evidence.
2. Preserve provenance — the source document, its SHA-256 and control total recorded in the seed pattern; the workbook itself is never committed.
3. Recompute derived CM2 figures.
4. **Remove the provisional banner only after reconciliation passes** —
   `python3 scripts/patch_cm2_provisional.py` clears it automatically from config.
5. Re-run validation, requiring **FAIL: 0, BLOCKED: 0**.
6. Confirm CI green.
7. **Then request independent code-review approval.** Finance confirmation resolves data
   accuracy; it is **not** merge approval.

---

## 9. Explicitly not done

- No approver name, date or evidence has been written by engineering.
- D1 and D9 remain `PENDING_APPROVAL`.
- No CM2 figure is labelled final.
- No NSV-to-GMV conversion was used.
- The provisional banner has not been removed or waived.
