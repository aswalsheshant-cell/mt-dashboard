# Blocked Measures — Complete Reference (v3)

**Branch:** claude/safe-powerbi-dashboard-rulings  
**Generated:** 2026-07-11  
**Version:** 3 (NSV unit confirmed; cost sources now primary blockers)  
**Status:** Reference documentation (v3: NSV UNBLOCKED, cost sources block P&L)

---

## Summary

**6 measures are now intentionally blocked** (down from 9; NSV now ACTIVE, v2→v3 changes).

**Do NOT create these measures in Power BI Desktop.**  
**Do NOT use these measures in any report visual.**

### Business Rulings Applied (All Versions)

✓ **NSV Unit Validation** (v3 NEW) — Confirmed as Lakhs. ALL NSV measures now ACTIVE.
✓ **More Retail Records** (v2) — Business reviewed and approved. Kept as valid source records. NO dedup applied.
✓ **Reliance Brand Counter** (v2) — Approved as BA Availability flag. Coverage view implemented on Page 5.
✓ **State-wise Reporting** (v2) — Approved no state rollups. Zone-level used instead.

---

## 1. NSV (Net Sales Value) — NOW ACTIVE (v3)

**Status:** ✓ ACTIVE (v3: confirmed unit = Lakhs)  
**Previous Status:** BLOCKED (v2: unit unvalidated)  
**Confirmation Date:** 2026-07-11  
**Unit:** Lakhs (source) → ₹ Crore (display format)

### Resolution

Finance confirmed:
- NSV grand sum = 271,801 Lakhs across 4.21M rows
- Conversion: NSV Cr = Source NSV Lacs ÷ 100
- MRP-to-NSV ratio validated: ₹1,443.45 Cr (MRP) ÷ [NSV Cr]

### Measures NOW IMPLEMENTED ✓

- ✓ [Source NSV Lacs] — NSV in Lakhs (source unit)
- ✓ [NSV Actual Value] — NSV in rupees (Lacs × 100,000)
- ✓ [NSV Cr] — NSV in Crore format (Lacs ÷ 100)
- ✓ [NSV Contribution %] — NSV contribution % (now active)
- ✓ [NSV MoM Abs Change Cr] — NSV month-over-month change
- ✓ [NSV MoM % Change] — NSV % growth (now active)
- ✓ [MRP to NSV Ratio] — Relationship indicator
- ✓ [BA Available NSV Cr] — NSV for Brand Counter rows
- ✓ [BA Availability Mix % NSV] — BA NSV as % of total

### Implementation

```dax
[Source NSV Lacs] =
SUMX(Fact_Offtake_Safe, Fact_Offtake_Safe[Source_NSV_Lacs])

[NSV Cr] =
DIVIDE([Source NSV Lacs], 100)

[NSV MoM Abs Change Cr] =
[NSV Cr] - [Previous Month NSV Cr]
```

---

## 2. Primary vs Offtake Gap / Gap %

**Status:** BLOCKED  
**Blocker:** Separate exercise (Primary NSV validation pending)  
**Timeline:** Pending  
**Note:** NSV unit is now confirmed; Primary NSV validation is independent exercise

### Measures (Not Implemented)

- [Primary vs Offtake Gap] — |Primary NSV - Offtake NSV|
- [Gap %] — Gap as % of Primary

### Reason

Offtake NSV is now validated (confirmed as Lakhs). Primary NSV validation remains a separate exercise requiring Primary source anchor.

---

## 3. Rank by Sales (NSV-Driven)

**Status:** AVAILABLE (NSV now active)  
**Blocker:** None (NSV unit confirmed)  
**Implementation:** Available via NSV-based charts

### Measures (Now Available)

- [Rank by NSV Sales] — Rank chains/zones by NSV (via Power BI visuals)
- [Top N by NSV] — Top N performers by NSV (charts, not DAX rank)

### Implementation Approach

Ranking is now valid (NSV basis confirmed). Implement as Power BI chart sorting:
- Sort all NSV charts by [NSV Cr] (descending)
- Use Power BI rank/top-N visual filters

---

## 4. CM2 (Contribution Margin 2) / Margin % / Profitability

**Status:** BLOCKED  
**Blocker:** Cost sources (business input pending)  
**Timeline:** Pending (cost structure, allocation rules)  
**Note:** NSV unit is no longer a blocker (v3); cost sources are primary blocker

---

## 5. P&L / Profitability Measures

**Status:** BLOCKED (v3: NSV no longer a blocker)  
**Blocker:** Cost sources (business input pending)  
**Timeline:** Pending  
**Note:** NSV unit confirmed (v3); cost sources are now primary blocker

### Measures (Not Implemented)

- [Gross Profit] — Offtake NSV × margin % − COGS
- [Contribution Margin 1] — Offtake NSV − variable costs
- [Contribution Margin 2 (CM2)] — NSV − direct selling costs − allocation
- [EBITDA] — Margin − fixed overhead
- [Net Profit] — EBITDA − taxes/interest

### Reason

P&L measures have three blockers (v3: NSV unit NO LONGER ONE):
1. ✓ **NSV unit validation** (COMPLETE: confirmed Lakhs)
2. **Margin % assumptions** (not yet provided by business) — NEW PRIMARY BLOCKER
3. **Cost allocation rules** (not yet documented) — NEW PRIMARY BLOCKER

### Future Dependency

Once finance provides:
- Gross margin % by category/chain
- COGS/DC/logistics costs
- Overhead allocation method
- Cost center mapping

Then P&L measures can be implemented.

---

## 6. CM2 (Contribution Margin 2), Gross Margin %

**Status:** BLOCKED (v3: NSV no longer a blocker)  
**Blocker:** Cost sources (business input pending)  
**Timeline:** Pending  
**Note:** NSV unit confirmed (v3); cost sources are now primary blocker

### Measures (Not Implemented)

- [CM2] — Contribution Margin 2 (NSV − direct costs)
- [Gross Margin %] — Margin as % of NSV

### Reason

Both require:
- ✓ NSV unit to be correct (CONFIRMED: Lakhs)
- **Cost sources and margin assumptions** (business input pending) — NEW BLOCKER

### Interim Approach

No interim MRP-based margin is appropriate (margins are net-revenue concepts, not gross-revenue).

---

## 7. BA (Beauty Advisor) Profitability, Cost to Serve, Productivity

**Status:** BLOCKED (v3: NSV no longer a blocker)  
**Blocker:** Cost sources + BA Headcount (business input pending)  
**Timeline:** Pending  
**Note:** NSV unit confirmed (v3); BA Availability coverage implemented on Page 5

### Measures (Not Implemented)

- [BA Cost to Serve] — BA compensation / offtake
- [BA Productivity] — Offtake per BA / per store
- [BA Profitability] — Offtake NSV × margin − BA cost

### Reason

BA analysis requires (v3: NSV is no longer blocker):
1. ✓ **Brand Counter classification** (COMPLETE: BA Availability flag)
2. ✓ **NSV validation** (COMPLETE: confirmed Lakhs)
3. **BA Headcount** — How many BAs per chain/store? (NEW PRIMARY BLOCKER)
4. **BA Cost Structure** — Salary + benefits + allocation? (NEW PRIMARY BLOCKER)
5. **Margin assumptions** — Required for profitability (NEW PRIMARY BLOCKER)

### Current Implementation

BA Availability coverage is ACTIVE (Page 5):
- [BA Available Row Count] — Count of Brand Counter rows
- [BA Available MRP Sales Value Cr] — MRP for BA-available rows
- [BA Available NSV Cr] — NSV for BA-available rows (v3: NSV now active)
- [BA Availability Mix %] — BA rows as % of total (MRP basis)
- **Profitability metrics** remain blocked pending cost structure

### Future Dependency

Once:
- ✓ Business confirms "Brand Counter" = BA channel (DONE)
- ✓ NSV unit is validated (DONE: Lakhs)
- BA Headcount dimension is provided (PENDING)
- BA cost structure is documented (PENDING)
- Margin assumptions provided (PENDING)

Then BA profitability measures can be implemented.

---

## 8. State-Level Rollups & Slicers

**Status:** ✓ APPROVED (v3: business decision applied)  
**Previous Status:** BLOCKED (v2: State mapping pending)  
**Decision Date:** 2026-07-11  
**Approval:** Zone-level reporting used instead; NO state-level rollups created

### Measures (Not Implemented)

- [State-wise MRP Total] — MRP aggregated by state
- [State Contribution %] — MRP contribution % by state
- [Rank by State] — States ranked by MRP

### Visual Components (Not Created)

- State slicer
- State-wise breakdown charts
- State-level map visual
- State-level drill-through

### Reason

State column contains:
- Real states (Maharashtra, Karnataka, Tamil Nadu, etc.)
- Cities (Mumbai 118.8k rows, Bangalore 15k, Kolkata 17.4k, etc.)
- Composites (Delhi/NCR, UP/UK, Punjab/J&K/HP)
- Variants (uppercase/lowercase, abbreviations)

**Total: 247 distinct "state" values for ~30 real states.**

Publishing state-level rollups without mapping would:
- Mix state and city level data
- Inflate city totals (Mumbai appears as city + state)
- Confuse business users
- Break chain-of-custody for analytics

### Interim Approach

Zone-level reporting IS implemented:
- [MRP by Zone] (P6 canonicalized, 37 zones)
- Zone slicer available
- Zone-level charts on all pages

### Future Implementation (Post-Decision)

Once business approves City-State Master SEED mapping:
- Add Dim_State_Canonical dimension
- Implement state-wise measures
- Enable state slicer
- Replace zone-only views with state views where appropriate

---

## 9. Chain-Level Reporting for Variants (Until Canonicalization)

**Status:** BLOCKED (Partial)  
**Blocker:** Chain name variants not yet canonicalized; decision pending  
**Timeline:** 1 week

### Chains with Variants

| Variant Pair | Rows (Est.) | MRP Total | Status |
|---|---|---|---|
| Vmm / VMM | 54.8k | TBD | Both in raw data; not merged |
| Fsn / FSN | 6.3k | TBD | Both in raw data; not merged |
| Walmart Cnc / Walmart CNC | 10.3k | TBD | Both in raw data; not merged |
| Ratanadeep / Ratanadeep | 4.5k | TBD | Both in raw data; not merged |
| H&B / H_B | 5.7k | TBD | Character encoding variant; both present |
| H&G / H_G | ~237k | TBD | Character encoding variant; both present |

### Measures (Partially Blocked)

- [Chain-level MRP for Variants] — Total for Vmm/VMM combined (currently fragmented)
- [Variant Consolidation %] — Share of total MRP for merged variant

### Reason

Variants are currently reported separately (Vmm ≠ VMM in filters/charts), which:
- Fragments chain-level totals
- Confuses business users
- Requires manual consolidation in Excel

### Current Approach (Interim)

- **Report** all chain variants separately (as they appear in source)
- **Flag** variant pairs in QC & Reconciliation page
- **Do NOT merge** chain names permanently yet
- **Preserve** raw data exactly as-is

### Future Implementation (Post-Decision)

Once business approves Chain Master DRAFT canonicalization:
- Add Dim_Chain_Canonical dimension (with canonical name mapping)
- Replace all chain filters with canonical names
- Implement cross-filter to show variants under each canonical
- Update chain-level measures to aggregate across variants automatically
- Add "chain variant breakdown" drill-through (shows original variant rows)

---

## Summary Table (Updated v3: NSV Confirmed)

| # | Measure / Feature | Blocker | Timeline | Priority | Status |
|---|---|---|---|---|---|
| ✓ 1 | NSV (base unit) | ✓ COMPLETE (Lakhs confirmed) | 2026-07-11 | P0 — Now ACTIVE | ✓ ACTIVE |
| ✓ 2 | NSV Cr/MoM/Contribution/BA | ✓ COMPLETE (NSV now active) | 2026-07-11 | P0 — Now ACTIVE | ✓ ACTIVE |
| ✓ 3 | Rank by NSV (charts) | ✓ COMPLETE (NSV now active) | 2026-07-11 | P2 | ✓ AVAILABLE (via visuals) |
| — | Primary vs Offtake Gap | Separate Primary NSV validation | Pending | P2 | BLOCKED (independent) |
| 5 | P&L / Profitability | **Cost sources (new blocker)** | Pending | P1 | BLOCKED |
| 6 | CM2 / Gross Margin % | **Cost sources (new blocker)** | Pending | P2 | BLOCKED |
| 7 | BA Profitability | **BA Headcount + cost structure** | Pending | P1 | BLOCKED (coverage active) |
| ✓ 8 | State-level rollups | ✓ APPROVED (zone-only) | 2026-07-11 | P2 | ✓ NOT CREATED (intentional) |
| ✓ B.C. | Brand Counter = BA Availability | ✓ APPROVED | 2026-07-11 | P1 | ✓ APPROVED (Page 5 active) |
| ✓ M.R. | More Retail records | ✓ APPROVED (no dedup) | 2026-07-11 | P1 | ✓ APPROVED (all rows kept) |
| 9 | Chain variant consolidation | Chain canonicalization | Pending | P2 | BLOCKED |

**P0 = Unblocks other items (depends on this)  
P1 = Important for leadership reporting  
P2 = Nice-to-have; can defer  
✓ ACTIVE = Now IMPLEMENTED (v3)  
✓ APPROVED = Business ruling applied; not blocking anymore  
BLOCKED = Awaiting business input**

---

## Implementation Order (Recommended v3)

**Approved & Complete (All 4 Rulings Done):**
1. ✓ **NSV Unit Validation** (v3) — Confirmed Lakhs; all NSV measures now ACTIVE
2. ✓ **More Retail Records** — Business approved; kept as valid; no dedup
3. ✓ **Brand Counter = BA Availability** — Approved; Page 5 coverage view created
4. ✓ **State-wise Reporting** — Approved no state rollups; zone-level used

**Now Blocking Further Progress:**
1. **Cost Source Confirmation** — Finance to provide:
   - COGS by category/chain
   - Margin % assumptions
   - Cost allocation rules
   - (Blocks: P&L, CM2, Margin %, BA Profitability)
2. **BA Headcount & Cost Structure** — HR/Finance to provide:
   - BA count by chain/store
   - BA cost structure (salary + benefits)
   - Cost allocation method
   - (Blocks: BA Profitability; BA Coverage already active)
3. **Chain Master Canonicalization** — Business to approve:
   - Canonical chain names (Vmm vs VMM, etc.)
   - Variant mapping logic
   - (Blocks: chain-level consolidation; raw variants still available)

---

**Do NOT implement these measures until explicitly unblocked by business decision.**

