# Classify NPI: Chain × EAN × Month × FY

**Purpose:** Permanent enforcement of complete-history NPI classification with global article identity, chain-wise performance tracking, and reconciliation proof before dashboard placement.

**Scope:** NPI classification is **non-optional**. Every article launch determination must be based on complete available Primary + Offtake history, never current-file-only. Global NPI launch (first sale across all chains) is separate from chain-level performance (new-to-chain).

---

## Core Rules (Immutable)

### Rule 1: Complete History Scanning
- Query ALL available Primary history (from earliest loaded month through latest)
- Query ALL available Offtake history (same period)
- Do NOT rely on current file alone
- Do NOT assume missing earlier months = no earlier sales
- Do NOT truncate analysis to latest FY

**Failure Scenario:** Article appears in June 2026 Offtake. If Primary history before June is missing or incomplete, classify as "Ambiguous" (not NPI). Do not assume first appearance = launch.

### Rule 2: Global EAN Classification (Article Launch)
- Classification is **per-EAN**, not per-chain
- One article = one launch date across ALL chains combined
- Categories:
  - **Confirmed NPI**: First verified commercial sale on/after Mar-26, continuous history from first sale through current reporting month
  - **Provisional NPI**: First verified commercial sale on/after Mar-26, with gaps or incomplete history (missing month(s) between first and last known sale)
  - **Existing Portfolio**: First verified commercial sale before Mar-26
  - **Ambiguous Identity**: Cannot determine launch due to missing data, name conflicts, or identity collapse
  - **Excluded/Non-commercial**: FOC, Tester, cancelled, excluded brand, invalid quantity/NSV

**Eligibility for Launch Date:** A sale must be:
- Non-zero quantity AND non-zero NSV (both strictly > 0 for Primary; quantity+NSV > 0 after lakh conversion for Offtake)
- Non-cancelled, non-MRN, non-credit note
- Not flagged FOC or Tester
- Brand not in excluded list
- Date strictly within invoice/transaction date (not future-dated, not outside month)

**Launch = the calendar month of the earliest eligible sale (MonthKey = YYYY-MM, e.g., "2026-04" → "Apr-26")**

### Rule 3: Canonical Article Identity

Priority for establishing identity:

1. **EAN (primary key)**
   - Coerced to integer from float (handle NaN as null)
   - 8, 10, 12, 13-digit valid; reject if ambiguous or malformed
   - One EAN = one article across history

2. **Article Code (fallback if EAN missing)**
   - Must be unique within brand (e.g., "MAM001" + brand)
   - If same article code appears across different brands with different descriptions, flag as Ambiguous Identity

3. **Brand + Description + Pack (fallback)**
   - Last resort: exact match on (Brand, Description, MRP or unit pack)
   - Do NOT use this if EAN or Article Code is available
   - Very likely to cause false identity collapse — tag as Ambiguous

**Identity Conflict:** If an EAN is reused for a different article (same EAN, different brand/description in different time periods), flag entire EAN as Ambiguous and document the conflict.

### Rule 4: Canonical Chain Identity (Retail Outlets Only)

- Chains in Offtake must match approved Chain Master (specific retailer banners)
- Do NOT accept distributor names as chains (e.g., "D-Mart Distribution" is not the same as "D-Mart")
- Do NOT mix "D-Mart Direct" and "D-Mart" into one chain
- One approved chain name = one output row per EAN per month

**Exceptions:** If a chain name in Offtake does not match master:
- Attempt fuzzy match (≥80% string similarity)
- If no match, flag as "Chain Mapping Exception" and assign to "Unmatched" bucket for reconciliation
- Do NOT silently remap without documentation

### Rule 5: Fiscal-Period Contract

- **NPI Threshold:** Mar-26 (last day of FY26) / Apr-26 (first day of FY27)
  - If first sale = Mar-26 or earlier → Existing Portfolio (FY26 or earlier)
  - If first sale = Apr-26 or later → Potential NPI (FY27+)
  - MonthKey "2026-03" → FY26; MonthKey "2026-04" → FY27

- **Reporting Period:** Apr-26 through Jun-26 (Q1 FY27) = **three-month comparable window**
  - Offtake: Apr-26, May-26, Jun-26 (29 days + 31 days + 30 days)
  - Primary: Apr-26, May-26, Jun-26

- **Coverage Alignment:**
  - Do NOT report "Jun-26 only" as the definition of Q1 FY27
  - Do NOT truncate reporting to months where Offtake exists
  - Primary and Offtake have different record grain — **reconcile at NSV level, not row count**

### Rule 6: Data-Coverage Alignment

Determine actual coverage:

```
Primary: min_month = [earliest month in Primary history] 
         max_month = [latest month in Primary history]
Offtake: min_month = [earliest month in Offtake history]
         max_month = [latest month in Offtake history]

Comparable Period = MAX(Primary.min, Offtake.min) through MIN(Primary.max, Offtake.max)
```

**Example:** If Primary covers Apr-25 through Jun-26 and Offtake covers Apr-26 through Jun-26, then Comparable Period = Apr-26 through Jun-26. Articles with Primary in Apr-25 or May-25 but no Offtake until Apr-26 are **Existing Portfolio** (pre-launch in Apr-26 sense).

### Rule 7: Commercial-Sale Eligibility

Every row in Primary and Offtake must be inspected before inclusion in launch analysis:

**Exclude (mark as Excluded/Non-commercial):**
- Quantity = 0 (even if NSV > 0 — error/credit)
- NSV ≤ 0 (after lakh conversion, strictly positive required)
- Cancelled invoice (explicit flag or pattern detected)
- MRN or credit note (negative quantity, negative NSV, explicit MRN code)
- FOC or Tester (explicit flag in data, or pattern: MRP = 0)
- Excluded brand (documented list: e.g., internal test brands)
- Date outside stated month (invoice dated in different month/year)
- Quantity+NSV sum = 0 (degenerate row)

**Include (eligible):**
- Quantity > 0 AND NSV > 0 (after unit conversion)
- Non-cancelled, non-credit
- Non-excluded brand
- Dated within invoice month

**Reconciliation:** Every article-month must account for **all** rows:
```
Total rows in month = Eligible rows + Excluded rows
Total NSV = Eligible NSV + Excluded NSV (documented separately)
```

### Rule 8: Distributor Allocation (Primary Only)

- Distributor Primary rows: blank or explicit "DISTRIBUTOR" chain
- Allocation: map Distributor → Retail chains using approved weights
- Approved allocation weights by (Distributor, Brand, MonthKey) must exist
- If no allocation weight for (Distributor, Brand, Month), use nearest month in same FY
- If no weight found in any month of FY, row goes to "Allocation Exception"

**Example:**
```
Source: Distributor "ABC", Brand "Mamaearth", Jun-26, 500 Lakh NSV
Allocation weights (Jun-26): D-Mart 30%, Reliance 40%, Apollo 20%, Others 10%
Output rows:
  - D-Mart:    150 Lakh NSV
  - Reliance:  200 Lakh NSV
  - Apollo:    100 Lakh NSV
  - Others:     50 Lakh NSV
Reconciliation: 150+200+100+50 = 500 ✓
```

### Rule 9: Reconciliation Before Dashboard Placement

**Level 1 — Month-to-FY reconciliation:**
```
Sum(Apr-26 NSV) + Sum(May-26 NSV) + Sum(Jun-26 NSV) = Sum(FY27 Q1 NSV)
```

**Level 2 — Source-to-Eligible reconciliation:**
```
Sum(all eligible Offtake rows) = reconciled Offtake NSV
Sum(all eligible Primary rows, post-allocation) = reconciled Primary NSV
Variance = |reported - calculated| / calculated × 100%
Tolerance: ±0.05% (≤ 1 Lakh for typical months)
```

**Level 3 — Chain-to-Total reconciliation:**
```
Sum(D-Mart Offtake) + Sum(Reliance Offtake) + ... + Sum(All Chains) 
  = Total Offtake NSV
Variance tolerance: ±0.01%
```

**Level 4 — EAN-to-Total reconciliation:**
```
Sum(EAN-1 Offtake in Q1) + Sum(EAN-2 Offtake in Q1) + ... 
  = Total Q1 Offtake NSV
Variance tolerance: ±0.02%
```

**Level 5 — Classification reconciliation:**
```
Sum(Confirmed NPI Offtake) + Sum(Provisional NPI Offtake) + Sum(Existing Portfolio Offtake)
  = Total Eligible Offtake
Variance tolerance: ±0.01%
```

**STOP before dashboard placement if ANY variance exceeds tolerance. Document the gap and investigate root cause.**

### Rule 10: Confirmed vs. Provisional NPI

**Confirmed NPI:**
- First eligible sale ≥ Apr-26
- Continuous Offtake history from launch month through latest reporting month (Jun-26)
  - "Continuous" = present in every month (Apr, May, Jun for Q1 FY27)
  - If 3-month window: ALL 3 months must have ≥1 row with quantity > 0, NSV > 0

**Provisional NPI:**
- First eligible sale ≥ Apr-26
- Offtake history has gaps (missing one or more months) OR
- Offtake coverage ends before Jun-26 (e.g., present only in Apr-May, not Jun)

### Rule 11: Chain × EAN Reporting Grain

Output grain = **Chain × EAN × Month** (Offtake reporting)

Each row represents one chain-article-month combination with:
- Chain name (approved master)
- EAN (canonical)
- MonthKey (YYYY-MM)
- FY
- First sale (launch month)
- Classification (Confirmed NPI / Provisional NPI / Existing Portfolio / Ambiguous / Excluded)
- Quantity (sum of all eligible Offtake rows for this chain-EAN-month)
- NSV (in Lakh)
- MRP (sum of MRP value in Lakh)
- Primary Quantity (sum of Primary quantities for this EAN in month, post-allocation to chain)
- Primary NSV (sum of Primary NSV for this EAN in month, post-allocation to chain)

Do NOT pre-aggregate EAN before classification (aggregation happens after classification).

---

## Invocation

```
Invoke this skill when:
- Ingesting new monthly data (Primary or Offtake)
- Re-running NPI classification for completeness or audit
- Updating dashboard NPI metrics, charts, or filters
- Validating NPI KPI calculations

Command:
$classify-npi-chain-ean --src <directory with Primary + Offtake CSVs/XLSBs> \
  --primary-history <optional: explicit Primary CSV list> \
  --offtake-history <optional: explicit Offtake CSV list> \
  --npi-threshold "2026-03" \
  --reporting-period "Apr-26,May-26,Jun-26" \
  --out <directory for output CSVs and QC reports>
```

**Output Deliverables:**

1. `npi_article_classification.csv` — Article-level classification (EAN, Article Code, Brand, First Sale, Classification, Reasons)
2. `npi_chain_ean_monthly.csv` — Chain × EAN × Month × FY fact table (full grain, all dimensions, all metrics)
3. `npi_chain_ean_summary.csv` — Chain × EAN summarized (Confirmed/Provisional/Existing/Ambiguous counts, total NSV by classification)
4. `npi_identity_exceptions.csv` — EANs with identity conflicts or ambiguous mappings
5. `npi_chain_mapping_exceptions.csv` — Chain names that did not match master
6. `npi_distributor_allocation_exceptions.csv` — Distributor rows that could not be allocated
7. `npi_history_coverage.csv` — Primary and Offtake coverage by EAN, chain, and month (min/max dates)
8. `npi_reconciliation.csv` — Multi-level reconciliation proof (source→eligible→mapped→facts)
9. `npi_by_chain.csv` — Chain-level summary (total NSV, NPI NSV, % contribution, Confirmed/Provisional split)
10. `npi_by_brand.csv` — Brand-level summary (total NSV, NPI NSV, % contribution, article count)
11. `npi_qc_summary.json` — Machine-readable pass/fail decisions

**Dashboard Update Requirements:**

After classification completes:

- **NPI KPI:** `Confirmed NPI Offtake NSV ÷ Total Eligible Offtake NSV × 100%`
  - Numerator = sum(Confirmed NPI Offtake in comparable period)
  - Denominator = sum(All eligible Offtake in comparable period)
  - Filter-responsive: update when user changes FY, Chain, or Brand filter
  
- **Chart 1 — NPI by Chain:** Stacked bar chart (Chain, Confirmed NPI NSV, Provisional NPI NSV, Existing Portfolio NSV)

- **Chart 2 — NPI Trend:** Line chart (Month, Cumulative Confirmed NPI NSV, Cumulative Provisional NPI NSV)

- **Detail Table:** Chain × EAN × Month rows (exportable to Excel)

- **New-to-Chain Analysis:** Separate table showing (Chain, EAN, Brand, First Sale in Chain, First Sale Overall, Months Since Launch, NSV in Chain, NSV Overall, % of Global Sales)

- **Filters:** Responsive to Chain, Brand, FY, Classification. No recalculation on filter change (pre-computed facts).

---

## Validation Checklist (Before Dashboard Commit)

- [ ] All 11 output CSVs generated with zero errors
- [ ] Reconciliation Level 1-5 all pass (variance ≤ tolerance)
- [ ] No Ambiguous articles in Confirmed NPI bucket
- [ ] Chain × EAN grain verified (no duplicate chain-ean-month rows)
- [ ] Confirmed NPI has continuous history (all 3 months Apr-May-Jun present)
- [ ] Provisional NPI has gaps (at least one month missing from history)
- [ ] Existing Portfolio contains zero articles with first sale ≥ Apr-26
- [ ] NPI KPI calculated and matches reconciliation proof
- [ ] Dashboard filters update NPI metrics without page reload
- [ ] No NaN, undefined, or empty values in exported detail table
- [ ] 12-tab sweep (Data Explorer × 4 FY states) with no broken cards
- [ ] Deployed Vercel URL returns correct NPI data (check commit SHA)

---

## Permanent Enforcement

This skill is **not a one-time runbook**. It permanently governs:

1. Every PR touching NPI classification or metrics
2. Every data intake that includes new Primary or Offtake
3. Every dashboard refresh cycle
4. Every validation before commit/push

**Violation of any Core Rule = STOP and escalate to user.** Do not proceed to dashboard placement until violation is resolved.
