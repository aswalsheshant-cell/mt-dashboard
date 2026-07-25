# Finance Decision Package — D1 & D9

**To:** CFO / Finance Controller
**From:** Data Engineering — Honasa MT Analytics
**Date:** 2026-07-25
**Decision required by:** `[PROPOSED: 2026-08-01 — please confirm or amend]`
**Named Finance owner:** `[REQUIRED — the register names the team "Finance", not a person]`
**Reference:** PR #16 · head `b32648e` · `config/cm2_decision_register.csv`

---

## 1. Executive Summary

### Current status
The FY27 Q1 (Apr–Jun 26) Modern Trade analytics build is **technically complete and
fully validated**. All engineering quality gates pass: 120 tests, CI green, `FAIL: 0`,
no merge conflicts. Basis decisions **D10, D11 and D12 are already approved**.

### Why it is blocked
One gate remains: **`GOV-FORMULA-DRAFT` — severity BLOCKED**. All 9 components of
`config/cm2_formula.csv` carry `Status = DRAFT`. Under the platform's governance rule,
no business assumption reaches production without an approver, a date and evidence —
and an approval that engineering writes for itself is not an approval. **Engineering
cannot clear this gate.** It is a policy decision, not a defect.

### Decisions required
| ID | Question | Financial impact | Owner |
|---|---|---|---|
| **D1** | Is COGS deducted **inside** reported CM2? | **4,411.21 L** (Q1 FY27) | Finance |
| **D9** | Activate direct allocation rules ALLOC-001/002/003? | **0 L today** — forward-looking only | Finance |

### Business impact of delay
- **CM2 cannot be reported as final** for any period. Every CM2 figure carries an
  on-screen provisional banner.
- **The published CM2 is currently misleading if read without the banner.** It shows
  **99.9% of NSV** — an artefact of three EXAMPLE expense rows totalling 47.65 L, not
  a real margin. The banner (added 2026-07-25) now discloses this, but the underlying
  number stays wrong until real expense data is loaded.
- Q1 FY27 leadership reporting on contribution margin is **unavailable** for decision-making.
- Downstream decisions **D2–D8** cannot be sequenced until the CM2 definition is fixed,
  because they each depend on knowing what CM2 contains.

---

## 2. Decision D1 — Does CM2 include COGS?

### Current implementation
COGS is **computed but staged outside reported CM2**. It is calculated in
`outputs/cm2/cm2_fy27_cogs_logistics.csv` and is **not** deducted in any published
figure. The safe default in force is "staged, not applied".

### The options

| | Option (a) INCLUDE | Option (b) EXCLUDE |
|---|---|---|
| **Definition** | CM2 = NSV − COGS − trade − field force − logistics − other | CM2 = NSV − trade − field force − logistics − other; COGS disclosed **below** CM2 |
| **Reads as** | Gross-margin-inclusive contribution | Post-trade-spend contribution |

### Financial impact — Q1 FY27 (Apr–Jun 26)

Using only the components whose **basis is already approved** (D10/D11):

| Line | Option (a) INCLUDE | Option (b) EXCLUDE |
|---|---|---|
| NSV | 13,652.59 L | 13,652.59 L |
| − COGS (GMV/MRP × 14.08%) | **(4,411.21) L** | — *(shown below CM2)* |
| − Logistics (NSV × 3.27%) | (445.97) L | (445.97) L |
| **= CM2 (partial)** | **8,795.41 L** | **13,206.62 L** |
| **CM2 % of NSV** | **64.42%** | **96.73%** |

> **The two options differ by exactly 4,411.21 L — 32.31 percentage points of NSV margin.**

These exclude trade expense (818.45 L candidate) and field-force cost (711.16 L),
which are pending **D2–D7** and would reduce both columns equally.

### ⚠ Correction to the previously circulated figure
D1's impact was recorded in the register as **1,922.66 L on an NSV basis**. That
predates **D10** (approved 2026-07-24), which settled that **COGS applies to GMV/MRP**,
not NSV:

```
NSV basis (superseded)   13,652.59 × 14.08% = 1,922.66 L
GMV/MRP basis (approved) 31,336.79 × 14.08% = 4,411.21 L
Understatement                                2,488.55 L  (2.29×)
```

Corrected in commit `b32648e`. **Please decide against 4,411.21 L.**

### Recommendation
**Option (a) INCLUDE**, on three grounds:

1. **Consistency with the approved basis.** D10/D11 already established COGS as a
   distinct cost component on a GMV/MRP basis. Computing it and then excluding it from
   the headline margin leaves the approved work unused.
2. **Comparability.** A 64.42% contribution margin is commercially interpretable for
   Modern Trade; a 96.73% "margin" that excludes product cost invites misreading.
3. **Single definition.** Option (b) requires every consumer to remember that COGS sits
   below the line — a recurring misstatement risk across dashboard, Power BI and decks.

This is a recommendation on presentation coherence, **not** an accounting-policy opinion.
If Honasa's management-reporting standard defines CM2 as post-trade-spend contribution,
option (b) is correct and should be chosen.

### Risks
| Risk | If (a) INCLUDE | If (b) EXCLUDE |
|---|---|---|
| Restatement | CM2 restated downward 32.31 pp vs any prior post-trade-spend figure circulated | CM2 stays high; risk of being read as a true margin |
| Comparability | Breaks comparison with any historic post-trade-spend CM2 series | Preserves that series |
| Misinterpretation | Low — margin reads conventionally | **High** — 96.73% looks implausible as a margin |
| Rate sensitivity | COGS % drives 32 pp of margin; rate-card errors are material | Lower — COGS sits outside the headline |

### Information required from Finance
1. Option **(a)** or **(b)**.
2. Confirmation that **COGS 4,411.21 L** and **logistics 445.97 L** are correct for Q1 FY27.
3. Confirmation the supplied monthly rate card is the authoritative rate source.
4. Approver name, date, and evidence reference.

### Approval statement — D1

> *I confirm that, effective FY27, CM2 for Honasa Modern Trade is defined as*
> **☐ (a) INCLUDING approved product cost (COGS)** — *or* — **☐ (b) EXCLUDING COGS,
> with COGS disclosed below CM2**
> *and that Q1 FY27 COGS of 4,411.21 L (GMV/MRP basis, 14.08%) and logistics of
> 445.97 L (NSV basis, 3.27%) are correct.*
>
> Approved by: ________________  Role: ________________  Date: ____________
> Evidence reference: ________________________________

---

## 3. Decision D9 — Activate direct allocation rules ALLOC-001/002/003?

### Current allocation logic
**`ALLOC-000 "Retain Unallocated"` is the only APPROVED rule.** It is the priority-7
fallback: expense is held in a visible *Unallocated Brand / Unallocated Chain / Shared MT*
bucket, requires no business judgement, and cannot distort any Brand or Chain figure.

**Material disclosure:** ALLOC-001 through ALLOC-008 are **configuration only**. A
repository-wide search confirms **no code references `ALLOC-00x`**. Approving D9 today
therefore **changes no published number** — it authorises the semantics a future
allocation engine would implement.

Separately, `build_dashboard_data.cm2_block` already performs **direct-tag attribution**
for the CM2 tab — Customer Code → Chain, then Chain name; Brand/Category applied only
when the row states them; no proportional allocation invented. That is functionally
equivalent to ALLOC-001/002/003 semantics, implemented independently of the governed
rule set. **D9 would bring the governed config into line with behaviour already shipping.**

### Proposed allocation logic

| Rule | Condition | Booking | Priority |
|---|---|---|---|
| **ALLOC-001** Direct Chain and Brand | Row carries approved Chain **and** Brand | Direct to Month × Chain × Brand | 1 |
| **ALLOC-002** Retain at Chain Level | Chain known, Brand unknown | Chain + **Unallocated Brand** — does *not* spread across brands | 2 |
| **ALLOC-003** Retain at Brand Level | Brand known, Chain unknown | Brand + **Unallocated Chain** | 3 |

All three honour **only tags already present in the source**. None invents a driver,
ratio or spread. Negative values are retained (returns and reversals keep their sign).

**Explicitly out of scope of D9:** ALLOC-004/005 (field force — blocked on a Chain-Name
crosswalk and the GT/Hybrid MT share), ALLOC-006 (store-universe driver),
**ALLOC-007 (NSV-share allocation — deliberately BLOCKED; must never become an automatic
fallback)**, ALLOC-008 (distributor→chain — blocked, no crosswalk exists).

### Financial implications

**Immediate impact: 0 L.** No code consumes these rules, and the only expense data
currently loaded is 47.65 L of EXAMPLE rows, of which 100% already maps.

Illustrative classification of the current rows under the proposed logic:

| Row | Amount | Tags present | Rule | Booking |
|---|---|---|---|---|
| Dmart · Mamaearth · Face | 12.50 L | Chain + Brand | ALLOC-001 | direct |
| Reliance Retail · Mamaearth | 28.40 L | Chain + Brand | ALLOC-001 | direct |
| Apollo · BA Cost | 6.75 L | Chain only | ALLOC-002 | Chain + **Unallocated Brand** |
| | **47.65 L** | | | 40.90 L branded · 6.75 L unallocated-brand |

The real expense pools — **818.45 L** trade (distributor grain) and **711.16 L** field
force (employee grain) — are **not** reachable by ALLOC-001/002/003. They require
ALLOC-004/005/008, which remain DRAFT or BLOCKED. **D9 does not release them.**

### Reporting impact
- Brand-wise and Chain-wise CM2 gain a governed basis for direct-tagged expense.
- **Unallocated buckets stay visible and sized** — they are never hidden to make a total tie.
- No Brand or Chain figure moves today, because no code reads the rules yet.

### Risks
| Risk | Assessment |
|---|---|
| Over-attribution | **Low.** Rules honour existing tags only; no driver maths, no spreading. |
| Source tags not authoritative | **Medium.** ALLOC-001 requires confirmation that source Chain/Brand tags are correct. This is the one substantive question in D9. |
| Scope creep into ALLOC-004–008 | **Low if bounded.** The approval statement below names only 001/002/003. |
| Approving rules no code reads | **Governance risk.** Creates an approved-but-unimplemented rule set; mitigated by the disclosure above. |
| Rejecting | All expense stays in Unallocated; Brand/Chain CM2 remains uninformative. |

### Recommendation
**Approve ALLOC-001/002/003 only**, keeping 004–008 DRAFT/BLOCKED. They are the
lowest-risk rules in the set, they cannot distort a figure, and they align the governed
config with behaviour already in production. Approval should be **conditional on Finance
confirming that source Chain and Brand tags are authoritative.**

### Approval statement — D9

> *I approve activation of allocation rules **ALLOC-001 (Direct Chain and Brand)**,
> **ALLOC-002 (Retain at Chain Level)** and **ALLOC-003 (Retain at Brand Level)** as
> specified in `config/cm2_allocation_rules.csv`, and confirm that Chain and Brand tags
> present in source expense files are authoritative.*
>
> *ALLOC-004, 005, 006, 007 and 008 remain **unapproved** and are not activated by this decision.*
>
> ☐ Approved   ☐ Rejected
> Approved by: ________________  Role: ________________  Date: ____________

---

## 4. Evidence

### Current calculations — Q1 FY27

| Month | GMV/MRP (L) | NSV (L) | COGS % | Logistics % | COGS (L) | Logistics (L) |
|---|---|---|---|---|---|---|
| Apr-26 | 11,760.60 | 5,069.17 | 14.05 | 2.97 | 1,652.36 | 150.55 |
| May-26 | 10,275.28 | 4,416.06 | 13.67 | 2.83 | 1,404.63 | 124.97 |
| Jun-26 | 9,300.91 | 4,167.36 | 14.56 | 4.09 | 1,354.21 | 170.45 |
| **Total** | **31,336.79** | **13,652.59** | **14.08** | **3.27** | **4,411.21** | **445.97** |

Source: `outputs/cm2/cm2_fy27_cogs_logistics.csv`. COGS on GMV/MRP, logistics on NSV,
computed independently (D10/D11).

### Before / after comparisons

| Item | Before | After | Commit |
|---|---|---|---|
| FY27 MRP (D13) | 22,050.21 L | **31,336.79 L** | `2d87cc3` |
| D1 stated impact | 1,922.66 L (NSV basis) | **4,411.21 L** (GMV/MRP, D10) | `b32648e` |
| CM2 provisional labelling | none | banner listing both reasons | `077997a` |

The D13 correction (+9,286.58 L) applied brand exclusions to MRP and added Jun-26; it
feeds directly into the COGS base above.

### Impact on KPIs
**Dashboard — P&L tab:** Total P&L Expense · CM2 Value · MoM CM2 Movement ·
Chain-wise CM2 chart · Chain-wise CM2 detail table · Expense-by-head table · CM2 QC table

**Data model** (`dashboard/data.js` → `cm2.*`): `total_expense` · `expense_pct_of_nsv` ·
`cm2_value` · `cm2_pct` · `by_chain[]` · `by_brand[]` · `by_category[]` ·
`by_expense_head[]` · `monthly[]`

**Power BI:** `PowerBI/DAX/13_CM2_Measures.dax`

### Affected financial reports
Q1 FY27 MT contribution-margin reporting · Chain-wise and Brand-wise CM2 ·
monthly CM2 trend · the Power BI CM2 measure set. **None may be presented as final
while `GOV-FORMULA-DRAFT` is open.**

### Audit trail
Every decision carries a register row with approver, date and evidence.
`governance.py` raises `GOV-WEAKAPPROVAL` (**FAIL**) for any approval missing one of
those three — partial sign-off fails rather than passes.

| Ref | Decision | Status | Approved |
|---|---|---|---|
| D10 | COGS on GMV/MRP; logistics on NSV | **APPROVED** | 2026-07-24 |
| D11 | COGS and logistics are separate components | **APPROVED** | 2026-07-24 |
| D12 | Jun-26 GMV/MRP source authoritative | **APPROVED** | 2026-07-24 |
| D13 | FY27 MRP correction | **APPROVED** | 2026-07-24 |
| **D1** | **COGS inside CM2?** | **PENDING** | — |
| **D9** | **Activate ALLOC-001/002/003** | **PENDING** | — |

### Data provenance & seed verification — Jun-26 GMV/MRP

| Field | Value |
|---|---|
| Source file | `MT+EB2B-MTD-Primary-June'26. (1).xlsx` |
| SHA-256 | `b73bf8ffa41a96c383ca79e6e3a4e5f4df05e24bf614702ede26658012162ae3` |
| Sheet / field | `MTD-Primary-June'26.` / `MRP Value` |
| Extraction rule | `sum('MRP Value')/1e5`; excluded brands removed; channels MT+EB2B+SIS — scope identical to Apr/May |
| Rows | 23,192 total → 23,192 after exclusion |
| **Control total** | NSV **4,167.38 L** vs `data.js` **4,167.36 L** = **0.02 L** (PASS, tolerance 0.12 L) |
| Status | **AUTHORITATIVE** |
| Seed | `PowerBI/SeedData/Masters/FY27_Monthly_GMV_MRP.csv` |

The workbook is gitignored and never committed; the seed carries filename, SHA-256,
sheet, field, extraction rule and control total so the value is reproducible and
attributable. Ratio sanity: Jun 2.232 vs Apr 2.320 / May 2.327 — commercially plausible.

### Determinism
`hashlib.sha256` throughout (never Python `hash()`, which randomises per process);
explicit stable sort keys; `Decimal` for money, rounded only for display. Two
consecutive `data.js` rebuilds are byte-identical.

---

## 5. Risk Assessment

### Risks if approved
| Risk | Severity | Mitigation |
|---|---|---|
| CM2 restated ~32 pp lower under D1(a) vs any circulated post-trade-spend figure | **High** | Communicate the definition change alongside first publication |
| COGS rate-card errors become material — 32 pp of margin rides on 14.08% | **Medium** | Finance confirms the rate card as authoritative source (requested above) |
| D9 approves rules no code reads → approved-but-unimplemented set | **Medium** | Disclosed in §3; implementation must cite D9 when built |
| Source Chain/Brand tags prove unreliable under ALLOC-001 | **Medium** | Approval made conditional on Finance confirming tag authority |

### Risks if rejected
| Risk | Severity |
|---|---|
| CM2 stays provisional indefinitely; Q1 FY27 margin unreportable | **High** |
| Published 99.9% figure persists — implausible on its face and reputationally risky if seen without the banner | **High** |
| D2–D8 cannot be sequenced; the whole CM2 programme stalls | **High** |
| Approved D10/D11/D12 work delivers no reportable output | **Medium** |

### Risks of delaying
| Risk | Severity |
|---|---|
| Q1 FY27 closes without an approved contribution-margin view | **High** |
| Q2 data arrives on an unapproved definition, compounding restatement scope | **Medium** |
| PR #16 stays unmerged; 19 commits of validated work remain unreleased | **Medium** |
| Loss of decision context as time passes from the 2026-07-24 basis approvals | **Low** |

### Compliance and audit considerations
- **No approval may be self-certified.** Engineering has written no approver name or date;
  D1 and D9 both show `approved_by` empty.
- **No estimation or fabrication.** Where a source was missing (Jun-26 GMV/MRP) it was
  recovered from an authoritative workbook and reconciled to a control total within
  0.02 L. No NSV-to-GMV conversion ratio was used.
- **Excluded brands** (Pure Origin, Lumineve, Staze) are removed from every aggregation;
  records are preserved, not deleted, in `PowerBI/Excluded_Data/Excluded_Brands/`.
- **Reproducibility.** Every figure is regenerable from tracked sources plus governed seeds.
- **Structural note for audit:** the CM2 KPI deducts **mapped** expense only; unmapped
  expense is reported in QC but not subtracted. Unmapped is currently **0.00 L**, so
  there is no live understatement of cost — but once real expense data loads, any
  unmapped amount would overstate CM2. Flagged for a follow-up control.

---

## 6. Approval Checklist

Please confirm explicitly. **Partial sign-off fails the gate rather than passing it** —
approver, date and evidence are all mandatory.

| # | Item | Confirm |
|---|---|---|
| 1 | **D1 Approved** — option (a) INCLUDE COGS in CM2 | ☐ |
| 2 | **D1 Approved** — option (b) EXCLUDE COGS from CM2 | ☐ |
| 3 | **D1 Rejected** / deferred | ☐ |
| 4 | Q1 FY27 COGS **4,411.21 L** and logistics **445.97 L** confirmed correct | ☐ |
| 5 | Supplied monthly rate card confirmed as the authoritative rate source | ☐ |
| 6 | **D9 Approved** — activate ALLOC-001/002/003 only | ☐ |
| 7 | **D9 Rejected** / keep DRAFT | ☐ |
| 8 | Source Chain and Brand tags confirmed authoritative | ☐ |
| 9 | **Additional clarification required** — please specify below | ☐ |

**Approver:** ______________________  **Role:** ______________________
**Date:** ____________  **Evidence reference:** ______________________

**Clarification requested:**
```


```

### Also required, separately from D1/D9
Real monthly P&L expense rows to replace the three `EXAMPLE ROW` entries in
`PowerBI/SeedData/Masters/PL_Expense_Input.csv`. **Approving D1 and D9 alone will not
clear the provisional banner** — the example-data condition is independent.
Owner: Finance / Trade Marketing MIS.

---

## 7. What happens after Finance responds

1. Update `config/cm2_decision_register.csv` — decision, approver, date, evidence.
2. Update `config/cm2_formula.csv` — `Include_Status`, `Approved_By`, `Approval_Date`, `Status=APPROVED`.
3. Preserve provenance via the governed seed process (source filename, SHA-256, control total).
4. Recompute all derived CM2 metrics.
5. Rebuild generated outputs; verify two consecutive builds are byte-identical.
6. Reconcile against Finance-approved values.
7. Clear the provisional banner **only if reconciliation succeeds** —
   `python3 scripts/patch_cm2_provisional.py` derives it from config automatically.
8. Run the full validation suite.
9. Confirm gates: **FAIL = 0 · BLOCKED = 0 · all regression tests pass · CI green · no governance violations**.
10. Publish a merge-readiness report and request **independent code-review approval**.

**Finance confirmation resolves data accuracy only. It is not merge approval.**

---

## 8. Explicitly not done

- No approver name, date or evidence written by engineering.
- D1 and D9 remain `PENDING_APPROVAL`.
- No business rule changed without approval.
- No CM2 figure labelled final.
- The provisional banner has not been removed or waived.
- No merge recommended.
