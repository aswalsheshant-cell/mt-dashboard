# Finance Approval Decision Log

**Document purpose:** Permanent record of Finance decisions on Jun'26 distributor allocation
and negative contribution-fraction treatment.

**Status:** PENDING — both decisions open as at 2026-08-06.

---

## Decision 1 — Jun'26 Distributor-to-Chain Allocation

### Context

The approved ShipTo CSV source (`Primary_ShipTo_FY25-26_to_May26.csv`) covers May'25–May'26.
For Jun'26, the pipeline falls back to May'26 contribution splits for 21 distributors.

- **Affected rows (article-level):** 10,236
- **Provisional NSV:** ₹1,376.49 L
- **Share of total Dist NSV:** 8.7%
- **Fallback coverage:** 100% (all 21 Jun'26 distributors have May'26 data)
- **Current status in model:** `Allocation Status = "Provisional"`, `Provisional Flag = TRUE`

### Options

| Option | Description | Engineering effort | Risk |
|--------|-------------|-------------------|------|
| **A** | Ratify May'26 splits as approved Jun'26 fallback | Zero — status change only | Low if chain mix stable |
| **B** | Review and approve `DistCont_Patch_Proposed.csv` (139 rows) | Finance review + Analytics promotion | Medium |
| **C** | Keep provisional; exclude from approved-only views | Zero | Governance debt until resolved |

### Decision Record

| Field | Value |
|-------|-------|
| **Decision selected** | *(Finance to complete: A / B / C)* |
| **Approver name** | *(Finance to complete)* |
| **Approver title** | *(Finance to complete)* |
| **Approval date** | *(Finance to complete)* |
| **Source file approved** | *(If Option B: file path and SHA256)* |
| **Method approved** | *(Nearest-month fallback / Proposed patch / Provisional retained)* |
| **Effective period** | Jun'26 |
| **Conditions or limitations** | *(Finance to complete)* |
| **Signed by** | *(Finance to complete)* |

### Post-Decision Engineering Actions

**If Option A:**
1. MT Analytics to note approval in this log (above fields)
2. MT Analytics to change `Approval Status` default fill in Q41 from
   `"Provisional – Jun'26 gap; awaiting Finance approval"` to
   `"Finance-Approved Fallback – Jun'26"` for the Jun'26 rows
3. Refresh PBIX — Provisional Flag remains `true` (it describes the source method);
   `Approval Status` changes to reflect Finance sign-off
4. Remove the ⚠ governance banner once confirmed

**If Option B:**
1. Finance returns reviewed/corrected `DistCont_Patch_Proposed.csv`
2. MT Analytics reviews percentages, confirms sum-to-100 per group
3. MT Analytics copies to `SeedData/Mapping/DistCont_Patch_Approved_<date>.csv`
4. MT Analytics updates Q41 P1 source path to include the new file
5. Commit, push, refresh PBIX — rows move from Provisional to Allocated

**If Option C:**
1. Log the expected resolution date in this document
2. Dashboard consumers informed via the governance banner
3. Revisit when Jun'26 DistCont data becomes available

---

## Decision 2 — Negative Contribution-Fraction Treatment

### Context

The ShipTo CSV contains 8 rows with negative `Cont%` values.
These are credit/reversal correction entries in the source system.

- **Source rows with negative Cont%:** 8
- **Affected article-level rows:** 157
- **Total negative NSV impact:** −₹0.2093 L
- **Affected distributors:** Az Enterprises (×2 reversal entries), D.L. Sales - MT,
  VENKATESHWARA AGENCIES-TG
- **Share of total Dist NSV:** 0.0013%
- **Current status:** Retained in the model; visible in `Primary Negative Frac Rows`
  and `Primary Negative Frac Flag` DAX measures on the QC page

### Options

| Option | Description | Engineering effort | Reconciliation impact |
|--------|-------------|-------------------|-----------------------|
| **Retain** | Keep reversal rows; report them separately in QC | Zero | Source ↔ model reconciles exactly |
| **Zero-floor** | Replace negative fracs/allocated values with zero | Low — one line in Q41 | −₹0.21 L disappears from chain totals; source ↔ model diverges by that amount |

### Decision Record

| Field | Value |
|-------|-------|
| **Decision selected** | *(Finance to complete: Retain / Zero-floor)* |
| **Approver name** | *(Finance to complete)* |
| **Approver title** | *(Finance to complete)* |
| **Approval date** | *(Finance to complete)* |
| **Rationale** | *(Finance to complete)* |
| **Reconciliation impact accepted** | *(Yes / No)* |
| **Signed by** | *(Finance to complete)* |

### Default (until Finance approves zero-floor)

**RETAIN.** Negative rows are visible in the QC page and labelled with
`Primary Negative Frac Flag`. They do not hide a data defect — they reflect
source reversal entries. Zero-flooring requires documented Finance authorisation
before implementation.

---

## Log History

| Date | Decision | Approver | Notes |
|------|----------|----------|-------|
| 2026-08-06 | Both decisions opened | MT Analytics | Finance Approval Pack issued |
| *(pending)* | Jun'26 Decision | *(Finance)* | — |
| *(pending)* | Negative Frac Decision | *(Finance)* | — |
