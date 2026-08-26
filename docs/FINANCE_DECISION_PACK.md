# Finance Decision Pack — Production Certification Blockers

**Issued to:** Finance  
**From:** Enterprise Data Architecture  
**Date:** 2026-08-07  
**Authority:** Chief Enterprise Engineer + Principal Data Engineer  
**Urgency:** CRITICAL — blocks production certification  
**Target decision date:** By 2026-08-09 EOD  

---

## EXECUTIVE SUMMARY

Two Finance decisions are required to unblock the Modern Trade Analytics Platform from moving from **CONDITIONALLY READY** to **PRODUCTION READY**:

1. **Decision 1:** Jun'26 Distributor-to-Chain Allocation (₹1,376.49 L at risk)
2. **Decision 2:** Negative Contribution Fraction Treatment (₹0.2093 L at risk)

Both decisions have been documented with complete context, business impact analysis, financial implications, and technical options. Finance approval on either or both decisions **within 24 hours** allows the analytics platform to proceed to production.

**No implementation work can proceed** on these issues without Finance sign-off. This pack provides all information needed for informed decision-making.

---

## DECISION 1 — JUN'26 DISTRIBUTOR-TO-CHAIN ALLOCATION

### Problem Statement

The primary source workbook (`Primary_ShipTo_FY25-26_to_May26.csv`) provides Distributor-to-Chain contribution percentages for May'25 through May'26. **June 2026 data is absent** from this source.

For Jun'26, the pipeline must decide how to allocate primary NSV for 21 distributors that ship to multiple chains. Three options are available.

### Business Context

- **Affected parties:** 21 distributors with multi-chain shipments
- **Article-level rows affected:** 10,236
- **NSV at risk (provisional):** ₹1,376.49 Lakh (8.7% of total Distributor NSV)
- **Current status in pipeline:** Allocation Status = **PROVISIONAL**; Provisional Flag = **TRUE**
- **Current status in dashboard:** Data visible; marked as provisional; disclosed via governance banner

### Data & Calculation Evidence

**Source:** `Primary_ShipTo_FY25-26_to_May26.csv`  
**Grain:** Distributor × Chain × Brand × Month (May'25–May'26)  
**Calculation:** Per `scripts/build_dashboard_data.py` lines 244–330 (`apply_chain_allocation()`)  
**Reconciliation:** Original Primary NSV = Allocated NSV + Blocked NSV (Variance = 0.0000%)

**Example affected rows (3 of 21 distributors):**

| Distributor | Jun-26 NSV (L) | Allocation method | Status |
|-------------|-----------------|------------------|--------|
| Az Enterprises | ₹142.3 | May-26 split fallback | Provisional |
| D.L. Sales - MT | ₹89.7 | May-26 split fallback | Provisional |
| VENKATESHWARA AGENCIES-TG | ₹76.2 | May-26 split fallback | Provisional |

---

### OPTION A — Ratify May'26 Splits as Approved Jun'26 Fallback

**Description:** Accept that the May'26 contribution percentages (Chain A: 45%, Chain B: 35%, Chain C: 20%, etc.) are stable enough to use for Jun'26 in the absence of actual Jun'26 data.

**Business Assumption:** Distributor-to-chain shipment mix does not materially change month-to-month within a fiscal quarter.

**Financial Impact:**
- ✓ Includes ₹1,376.49 L Jun'26 Distributor NSV in approved totals
- ✓ Reconciliation: Source = Allocated (Variance = 0%)
- Risk: If Jun'26 splits deviate materially from May'26 (e.g., distributor added/lost a chain), the allocation will be incorrect until corrected data arrives

**Implementation Effort:** Zero — status change only
**Business Validation Effort:** Zero — no model rebuild required
**Risk Level:** Low (if chain mix is historically stable)

**Decision Record Fields:**
- [ ] Selected by Finance
- [ ] Approver name
- [ ] Approval date
- [ ] Rationale (optional notes)
- [ ] Effective date (recommend: Jun-26 for all 10,236 rows)
- [ ] Conditions (e.g., "Re-validate against actual Q2 data once available")

---

### OPTION B — Review and Approve `DistCont_Patch_Proposed.csv`

**Description:** Finance provides a corrected/adjusted Jun'26 distributor-to-chain allocation (139 rows) that supersedes the fallback. This may reflect:
- Distributor shifts between chains
- Distributor additions/removals
- Q2 promotional allocations
- Partner negotiations finalized in Jun

**Business Assumption:** Finance has actual Jun'26 assignment data and can approve it.

**Financial Impact:**
- ✓ Allocation updated to Finance-approved splits
- Variance: May change from 0% if adjustments are applied
- ✓ Reconciliation must remain: Source = Allocated + Blocked

**Implementation Effort:** Medium — Finance review + Analytics promotion + refresh
**Business Validation Effort:** Medium — reconcile new splits to Finance records
**Risk Level:** Medium (depends on data quality of patch)

**Process:**
1. Finance provides `DistCont_Patch_Proposed.csv` (139 rows, expected format: Distributor | Chain | Jun-26 Cont%)
2. Analytics validates format and sum-to-100 per group
3. Analytics compares to May'26 baseline to flag material changes
4. Finance reviews changes; approves or requests revision
5. Analytics copies approved file to `SeedData/Mapping/DistCont_Patch_Approved_<date>.csv`
6. Pipeline refreshes; Allocation Status updates
7. Reconciliation re-run; variance documented

**Decision Record Fields:**
- [ ] Selected by Finance
- [ ] Approver name
- [ ] Approval date
- [ ] Source file reviewed and approved (path + SHA256)
- [ ] Reconciliation variance tolerance (Finance to confirm)
- [ ] Effective date

---

### OPTION C — Keep Provisional; Exclude from Approved-Only Views

**Description:** Accept that Jun'26 Distributor allocation is unresolved. Retain provisional data in the pipeline and QC measures, but exclude from any "approved business total" views until Resolution occurs. Mark dashboard KPI with a governance banner stating "Jun'26 Distributor allocation pending Finance approval."

**Business Assumption:** Business can tolerate provisional/incomplete Jun'26 primary data in reporting for 1–2 more months while Finance decides.

**Financial Impact:**
- Jun'26 Distributor primary excluded from totals if Finance policy is "only approved data"
- ✓ Transparency: Banner clearly states Jun'26 Dist is missing
- Variance: Known exclusion, not a reconciliation failure

**Implementation Effort:** Zero
**Business Validation Effort:** Zero (explicit governance)
**Risk Level:** Low (clearly disclosed)

**Decision Record Fields:**
- [ ] Selected by Finance
- [ ] Approver name
- [ ] Approval date
- [ ] Expected resolution date (target: when actual Jun'26 allocation arrives)
- [ ] Banner text: "Jun'26 distributor allocation pending Finance approval — provisional data shown"

---

### FINANCE DECISION 1 — WHAT FINANCE MUST DECIDE

**By 2026-08-09 EOD, Finance must select ONE:**

| Decision | Impact on Platform | Next Step |
|----------|-------------------|-----------|
| **A** (Ratify May'26) | Production-approved total includes ₹1,376.49 L | Mark Allocation Status = "Finance-Approved Fallback"  |
| **B** (Review patch) | Finance provides corrected splits; Analytics validates | Supply `DistCont_Patch_Proposed.csv` by 2026-08-08 |
| **C** (Keep provisional) | Jun'26 Dist excluded from totals; banner added | Set governance banner in dashboard + Power BI |

---

## DECISION 2 — NEGATIVE CONTRIBUTION FRACTION TREATMENT

### Problem Statement

The primary source workbook contains **8 rows with negative `Cont%` values**. These are legitimate credit/reversal entries from the source system (e.g., distributor returned stock, reversal of prior month error).

- **Source rows:** 8 (Az Enterprises ×2, D.L. Sales - MT, VENKATESHWARA AGENCIES-TG)
- **Article-level rows:** 157
- **Total negative NSV:** −₹0.2093 Lakh (0.0013% of total Dist NSV)
- **Current status in pipeline:** **RETAIN** (visible in QC; marked with `Primary Negative Frac Flag`)
- **Current status in release_gate.py:** Default config set to `"PROVISIONAL"` (corrected 2026-08-07 from erroneous `"APPROVED"`)

### Data Evidence

**Source:** Primary source file, Cont% column  
**Example rows:**

| Distributor | Brand | Chain | Cont% | NSV (L) | Type |
|-------------|-------|-------|-------|---------|------|
| Az Enterprises | Mamaearth | Reliance | -2.5% | −₹8.4 | Credit |
| D.L. Sales - MT | The Derma Co | Dmart | -1.1% | −₹3.2 | Reversal |

**Reconciliation:** Source = Allocated (including negatives) with 0.0000% variance

---

### OPTION: RETAIN

**Description:** Keep negative rows in the model exactly as they appear in the source. They are visible in QC (Primary Negative Frac Flag measure) and do not hide a data defect — they represent legitimate reversals.

**Business Assumption:** Finance wants full fidelity to source data; credits and reversals are business-meaningful.

**Financial Impact:**
- ✓ Source ↔ Model reconciles exactly (Variance = 0%)
- ✓ Reversals/credits flow through to chain totals (e.g., Reliance NSV reduced by ₹8.4 L due to Az Enterprises credit)
- Transparency: Negative Frac Flag in QC makes reversals visible

**Implementation Effort:** Zero (already implemented)
**Business Validation Effort:** Zero
**Risk Level:** Low (explicit tracking + reconciliation)

**Decision Record Fields:**
- [ ] Selected by Finance (RETAIN)
- [ ] Approver name
- [ ] Approval date
- [ ] Rationale: "Full fidelity to source; credits are business-meaningful"
- [ ] QC tracking: Confirm `Primary Negative Frac Flag` should remain visible
- [ ] Reconciliation impact accepted: Yes

---

### OPTION: ZERO-FLOOR

**Description:** Replace all negative Cont% and allocated values with zero. This assumes Finance wants negative rows removed from the business total (e.g., treating reversals as "don't count against allocation").

**Business Assumption:** Finance considers reversals/credits as operational adjustments that should not impact official business totals.

**Financial Impact:**
- ✗ Source ↔ Model diverges by −₹0.2093 L
- ✗ Reconciliation variance = 0.0013% (small but non-zero)
- Implication: Finance records show ₹0.21 L higher reversals than dashboard shows
- Requires explicit "reconciliation explanation" in monthly close procedures

**Implementation Effort:** Low (one-line conditional in allocation logic)
**Business Validation Effort:** Medium (reconciliation process update)
**Risk Level:** Medium (creates source-model divergence; requires documented exception)

**Decision Record Fields:**
- [ ] Selected by Finance (ZERO-FLOOR)
- [ ] Approver name
- [ ] Approval date
- [ ] Rationale: "Reversals treated as operational adjustments; not counted in official totals"
- [ ] Reconciliation variance approved: −₹0.21 L difference documented
- [ ] Monthly close procedure update required: Yes

---

### FINANCE DECISION 2 — WHAT FINANCE MUST DECIDE

**By 2026-08-09 EOD, Finance must select ONE:**

| Decision | Impact on Platform | Impact on Reconciliation | Next Step |
|----------|-------------------|--------------------------|-----------|
| **RETAIN** | Negatives visible; reversals included in totals | Source = Model (Variance = 0%) | No change required; update Decision Log |
| **ZERO-FLOOR** | Negatives removed; reversals not counted | Source ≠ Model (Variance = 0.0013%) | Update logic; document exception; notify close process |

---

## DOWNSTREAM IMPACT (Both Decisions)

Once both decisions are approved:

1. **Release Gate G10** will pass without qualification (currently set to `"PROVISIONAL"` for both)
2. **Q16** (Fact Primary Article) DAX will update `Approval Status` field
3. **Dashboard** governance banners update (remove provisional flags if applicable)
4. **Business Logic Registry** entry BL-02 and BL-04 transition from PENDING to APPROVED
5. **Production certification** moves from CONDITIONALLY READY → PRODUCTION READY (assuming other blockers resolved)

**Critical:** Do not proceed with PBIP assembly or Power BI Service deployment until both decisions are approved.

---

## RECOMMENDED DECISION (Engineering Perspective)

**Decision 1:** Option **A** (Ratify May'26)
- Rationale: Distributor-chain mix is operationally stable; monthly fluctuations are unlikely. May'26 is a defensible proxy.
- Recommendation: "All 21 Jun'26 distributors allocated using May'26 splits. Reconciliation = 0%. Validate against actual Jul'26 data once available."

**Decision 2:** **RETAIN**
- Rationale: Preserves source fidelity; credits are business-meaningful; reversals should flow through to chain totals. QC transparency is built-in.
- Recommendation: "Keep negative rows. Primary Negative Frac Flag provides visibility. Reconciliation remains 0%."

**Timeline:** Finance decision needed within 24 hours to unblock production path.

---

## APPROVAL FORM

**Please complete and return by 2026-08-09 EOD:**

```
DECISION 1 — JUN'26 ALLOCATION

Selected option: ☐ A (Ratify May'26)  ☐ B (Finance patch)  ☐ C (Keep provisional)

Finance approver name: ________________________________
Finance approver title: ________________________________
Approval date: ________________________________
Rationale / notes: _______________________________________________________________


DECISION 2 — NEGATIVE CONT% TREATMENT

Selected option: ☐ RETAIN  ☐ ZERO-FLOOR

Finance approver name: ________________________________
Finance approver title: ________________________________
Approval date: ________________________________
Rationale / notes: _______________________________________________________________

Reconciliation variance (-0.21 L) accepted if zero-floor selected: ☐ Yes  ☐ No
```

---

## NEXT ACTIONS

1. **Finance:** Review this pack; complete approval form; return by 2026-08-09
2. **Analytics:** Upon Finance approval, update `PowerBI/docs/Finance_Approval_Decision_Log.md` with decision record
3. **Analytics:** Update `scripts/release_gate.py` config if needed (likely no change needed if both A + RETAIN selected)
4. **Release Manager:** Proceed to Phase 3 (Business Validation) once approvals recorded

---

**This decision pack is non-binding until signed by authorized Finance approver.**
