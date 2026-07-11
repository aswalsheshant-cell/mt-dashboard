# Blocked Measures — Complete Reference

**Branch:** claude/safe-powerbi-blocks  
**Generated:** 2026-07-11  
**Status:** Reference documentation (measures NOT implemented)

---

## Summary

**11 measures are intentionally blocked** awaiting business decisions. They are documented here for completeness and to prevent accidental implementation.

**Do NOT create these measures in Power BI Desktop.**  
**Do NOT use these measures in any report visual.**

---

## 1. NSV (Net Sales Value)

**Status:** BLOCKED  
**Blocker:** NSV unit unvalidated  
**Timeline:** 1–2 weeks (awaiting finance anchor)

### Problem

- Grand NSV sum = 271,801 (dimensionless) across 4.21M rows
- MRP Sales Value = ₹1,443.45 Cr (verified rupees basis)
- NSV cannot both be in rupees (would total ~₹2,718 only)
- **Unit is ambiguous:** rupees/unit/lac/percentage?

### What's Needed

Finance must provide:
- One month with signed-off MT Offtake NSV (₹Cr)
- We solve backward for the implied unit multiplier
- Row-level NSV/MRP ratio validation

### Impact of Blocking

- All NSV-based measures blocked
- All MoM/YoY/L3M/L6M % growth (NSV basis) blocked
- All profitability measures blocked (depend on NSV)
- Contribution % (NSV-driven) blocked

### Implementation (Post-Decision)

```dax
[NSV Total] =
SUMX(Fact_Offtake_Safe, Fact_Offtake_Safe[NSV])

[NSV Cr] =
DIVIDE([NSV Total], [Unit_Multiplier])  -- where Unit_Multiplier is determined by business
```

---

## 2. NSV (Crore, Lacs, Label, Cumulative)

**Status:** BLOCKED  
**Blocker:** Dependent on NSV unit confirmation  
**Timeline:** 1–2 weeks

### Measures (Not Implemented)

- [NSV (Cr)] — NSV in Crore format
- [NSV (Lacs)] — NSV in Lakh format
- [NSV Label] — Text label for tooltips ("₹X.XX Cr NSV")
- [NSV Cumulative] — Running total of NSV

### Reason

All derivative NSV measures depend on the base [NSV] unit being correct. Until unit is confirmed, these cannot be reliably calculated.

---

## 3. MoM/YoY/L3M/L6M % Growth (NSV Basis)

**Status:** BLOCKED  
**Blocker:** NSV unit unvalidated  
**Timeline:** 1–2 weeks

### Measures (Not Implemented)

- [NSV MoM % Change] — Month-over-month NSV growth %
- [NSV YoY % Change] — Year-over-year NSV growth %
- [NSV L3M % Change] — Last 3-month NSV growth %
- [NSV L6M % Change] — Last 6-month NSV growth %

### Why Blocked

Percentage growth calculations amplify the uncertainty if the NSV unit is wrong. Example:
- If NSV is actually in ₹lac (not rupees), then % growth is meaningless
- If NSV is per-unit, then % growth doesn't translate to business meaning

### Interim Approach

MRP-based % growth measures ARE implemented:
- [MRP MoM % Change] — MRP growth % (safe, verified basis)
- [MRP YoY % Change] — MRP growth % (safe, verified basis)

---

## 4. Contribution % (NSV-Driven)

**Status:** BLOCKED  
**Blocker:** NSV unit unvalidated  
**Timeline:** 1–2 weeks

### Measures (Not Implemented)

- [Contribution % (NSV Basis)] — NSV contribution within filter context

### Reason

Contribution % requires a denominator (total NSV). If NSV unit is wrong, percentages are misleading.

### Interim Approach

MRP-based contribution IS implemented:
- [MRP Contribution %] — MRP contribution (safe, verified)
- [MRP Share of Total] — MRP share across all data

---

## 5. Rank by Sales (NSV-Driven)

**Status:** BLOCKED  
**Blocker:** NSV unit unvalidated  
**Timeline:** 1–2 weeks

### Measures (Not Implemented)

- [Rank by NSV Sales] — Rank chains/zones by NSV (highest → lowest)
- [Top N by NSV] — Top N performers by NSV

### Reason

Ranking is only valid if the NSV basis is correct. Wrong unit = wrong ranking.

### Interim Approach

MRP-based ranking IS implemented (implicitly in charts):
- Sort all bar/column charts by [MRP Sales Value] (descending)

---

## 6. Primary vs Offtake Gap / Gap %

**Status:** BLOCKED  
**Blocker:** Offtake NSV unvalidated  
**Timeline:** 1–2 weeks

### Measures (Not Implemented)

- [Primary vs Offtake Gap] — |Primary NSV - Offtake NSV|
- [Gap %] — Gap as % of Primary

### Reason

Gap calculation requires both Primary NSV and Offtake NSV to be validated. Offtake NSV is blocked; Primary NSV validation is a separate exercise.

### Future Dependency

Once Offtake NSV is validated, revisit Primary NSV validation before implementing gap measures.

---

## 7. P&L / Profitability Measures

**Status:** BLOCKED  
**Blocker:** NSV unit + margin assumptions + BA Headcount (business input)  
**Timeline:** 1–2 weeks (NSV) + 1–4 weeks (others)

### Measures (Not Implemented)

- [Gross Profit] — Offtake NSV × margin % − COGS
- [Contribution Margin 1] — Offtake NSV − variable costs
- [Contribution Margin 2 (CM2)] — NSV − direct selling costs − allocation
- [EBITDA] — Margin − fixed overhead
- [Net Profit] — EBITDA − taxes/interest

### Reason

P&L measures have three blockers:
1. **NSV unit validation** (blocking factor #1)
2. **Margin % assumptions** (not yet provided by business)
3. **Cost allocation rules** (not yet documented)

### Future Dependency

Once NSV is validated and finance provides:
- Gross margin % by category/chain
- COGS/DC/logistics costs
- Overhead allocation method

Then P&L measures can be implemented.

---

## 8. CM2, Gross Margin %

**Status:** BLOCKED  
**Blocker:** NSV unit + margin assumptions  
**Timeline:** 1–2 weeks (NSV) + 2–4 weeks (assumptions)

### Measures (Not Implemented)

- [CM2] — Contribution Margin 2 (NSV − direct costs)
- [Gross Margin %] — Margin as % of NSV

### Reason

Both require:
- NSV unit to be correct
- Margin assumptions approved by finance

### Interim Approach

No interim MRP-based margin is appropriate (margins are net-revenue concepts, not gross-revenue).

---

## 9. BA (Beauty Advisor) Cost to Serve, Productivity, Profitability

**Status:** BLOCKED  
**Blocker:** BA Headcount (business input) + Brand Counter classification + NSV unit  
**Timeline:** 1 week (classification) + 1–2 weeks (NSV) + 2–4 weeks (BA modeling)

### Measures (Not Implemented)

- [BA Cost to Serve] — BA compensation / offtake
- [BA Productivity] — Offtake per BA / per store
- [BA Profitability] — Offtake NSV × margin − BA cost

### Reason

BA analysis requires:
1. **Brand Counter classification** — Is "Brand Counter" (549,617 rows) the BA channel? (Blocker #3)
2. **BA Headcount** — How many BAs per chain/store? (Business input pending)
3. **BA Cost** — Salary + benefits + allocation? (Business input pending)
4. **NSV validation** — Profitability depends on NSV unit (Blocker #1)

### Future Dependency

Once:
- Business confirms "Brand Counter" = BA channel
- BA Headcount dimension is provided
- BA cost structure is documented
- NSV unit is validated

Then BA profitability measures can be implemented.

---

## 10. State-Level Rollups & Slicers

**Status:** BLOCKED  
**Blocker:** State column polluted (247 raw values include cities); City-State mapping pending  
**Timeline:** 1–2 weeks

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

## 11. More Retail Chain Totals & Contribution (Until Dedup Decision)

**Status:** BLOCKED  
**Blocker:** 13,661 exact-duplicate rows (₹1.36 Cr / 10.3% MRP) not yet deduplicated; decision pending  
**Timeline:** 1–3 weeks

### Measures (Not Implemented)

- [More Retail Total MRP] — Accurate More Retail total (deduped)
- [More Retail Contribution %] — Accurate More Retail % contribution
- [More Retail vs All-MT] — More Retail as % of All-MT total

### Reason

More Retail has:
- 40,848 rows
- 13,661 exact duplicates (33.44%)
- ₹1.36 Cr MRP carried by duplicates (10.3% of More Retail total)
- Duplicates present in every month (systematic, not random)

If dedup is deferred, More Retail totals are overstated by ~10% MRP.

### Current Approach (Interim)

- **Report** the duplicate count (13,661 rows, ₹1.36 Cr)
- **Do NOT remove** duplicates yet
- **Flag** More Retail totals in QC & Reconciliation page: "Pending duplicate review"
- **Preserve** all raw rows (may be legitimate if further investigation confirms)

### Three Options (For Business Decision)

| Option | Action | Timeline | Note |
|--------|--------|----------|------|
| 1 | De-dupe in Power Query via `Table.Distinct` (More Retail only) | 1–2 hours | Reversible, auditable |
| 2 | Fix at source: Request vendor to provide clean More Retail files | 1–3 weeks | Preferred if double-export confirmed |
| 3 | Leave as-is + footnote More Retail as inflated | Immediate | Not recommended; misleading |

### Future Implementation

Once business approves Option 1 or 2:
- Apply dedup in Power Query (if Option 1)
- Implement accurate More Retail measures
- Update all-chain aggregates to reflect corrected More Retail total
- Remove "pending duplicate review" flag

---

## 12. Chain-Level Reporting for Variants (Until Canonicalization)

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

## Summary Table

| # | Measure / Feature | Blocker | Timeline | Priority |
|---|---|---|---|---|
| 1 | NSV (base unit) | Finance anchor | 1–2 wk | P0 — Unblocks most |
| 2 | NSV Cr/Lacs/Label/Cumulative | NSV unit | 1–2 wk | P0 |
| 3 | MoM/YoY/L3M/L6M % (NSV basis) | NSV unit | 1–2 wk | P1 |
| 4 | Contribution % (NSV) | NSV unit | 1–2 wk | P1 |
| 5 | Rank by Sales (NSV) | NSV unit | 1–2 wk | P2 |
| 6 | Primary vs Offtake Gap | Offtake NSV | 1–2 wk | P2 |
| 7 | P&L / Profitability | NSV + margins | 1–4 wk | P1 |
| 8 | CM2 / Gross Margin % | NSV + margins | 1–4 wk | P2 |
| 9 | BA Profitability | BA Headcount + NSV | 1–2 wk + 1–4 wk | P1 |
| 10 | State-level rollups | State mapping | 1–2 wk | P2 |
| 11 | More Retail totals (accurate) | Dedup decision | 1–3 wk | P2 |
| 12 | Chain variant consolidation | Chain canonicalization | 1 wk | P2 |

**P0 = Unblocks other items (depends on this)  
P1 = Important for leadership reporting  
P2 = Nice-to-have; can defer**

---

## Implementation Order (Recommended)

1. **First:** NSV unit validation (unblocks everything that depends on NSV)
2. **Second:** More Retail dedup decision + implementation
3. **Third:** Brand Counter classification + BA profitability
4. **Fourth:** Chain Master canonicalization + state-to-city mapping
5. **Fifth:** Margin assumptions + P&L/CM2 measures
6. **Sixth:** Reliance schema confirmation

---

**Do NOT implement these measures until explicitly unblocked by business decision.**

