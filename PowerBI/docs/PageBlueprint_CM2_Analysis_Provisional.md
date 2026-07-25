# Page Blueprint: CM2 Analysis — Provisional

**Status:** Development/Testing page — not for production publication.

**Purpose:** Enable scenario testing and Finance decision preview on D1 and D9 while maintaining clear governance barriers. All data shown is tagged PROVISIONAL until approvals are recorded in `config/cm2_decision_register.csv`.

---

## Page Layout & Components

### Section 1: Warning Banner (Top, Full Width)

**Visibility Rule:** Show when `[Show CM2 Warning] = TRUE()`

**Content:**
```
🔴 CM2 PROVISIONAL — FORMULA AND ALLOCATION APPROVAL PENDING. 
TENTATIVE EXPENSE ASSUMPTIONS. NOT FOR FINAL REPORTING OR COMMERCIAL SETTLEMENT.
```

**Styling:**
- Background: Amber/Red (#FFC107 or #FF6B6B)
- Text: Black or Dark Grey, bold, 12-14pt
- Padding: 12px all sides
- Border: Solid 1px darker shade
- **Must remain visible** under all filters and drill-downs

---

### Section 2: KPI Card Row (Top Section)

Place KPI cards in a 5-column grid below the warning. Each card shows:
- Title (top)
- Value (center, large font)
- % change (bottom, smaller font, if applicable)
- Tooltip: Click to show data source decision

#### Card 1: Net Sales (Approved)
- Measure: `[Total Primary Article NSV]`
- Format: `#,##0` Lakh
- Subtitle: "Net Sales (Excl. GST, post TOT%)"
- Tooltip: "D12 APPROVED | Jun-26 from authoritative seed"

#### Card 2: Base Contribution (Approved)
- Measure: `[Total Primary Article NSV]` (same as above)
- Format: `#,##0` Lakh
- Subtitle: "Before expense deduction"

#### Card 3: Provisional Expense
- Measure: `[Provisional Expense Lacs]`
- Format: `#,##0` Lakh
- Subtitle: "All mapped expense (pending approval)"
- Tooltip: "Includes D1 (COGS), D2-D4 (Trade), D5-D7 (Field Force), all tagged PROVISIONAL"

#### Card 4: Provisional CM2
- Measure: `[Provisional CM2 Lacs]`
- Format: `#,##0` Lakh
- Subtitle: "Provisional (NSV − Provisional Expense)"
- Conditional Formatting: Cell color = Amber (#FFEB3B) if `[CM2 Display Status] = "PROVISIONAL"`, else Green (#4CAF50)

#### Card 5: Provisional CM2 %
- Measure: `[Provisional CM2 %]`
- Format: `0.00%`
- Subtitle: "As % of NSV"
- Conditional Formatting: Cell color = Amber if PROVISIONAL, else Green

#### Card 6: Approved CM2 (if available)
- Measure: `[Approved CM2 Lacs]`
- Format: `#,##0` Lakh
- Subtitle: "Awaiting Finance Approval"
- Display Logic: Show "N/A — D1/D9 Pending" if BLANK (using conditional formatting or a measure that returns "Awaiting Approval")
- Tooltip: "Will populate only after D1 and D9 are approved"

#### Card 7: Unmapped Expense
- Measure: `[Unmapped Expense Lacs]`
- Format: `#,##0` Lakh
- Subtitle: "Excluded from Chain/Brand CM2 — audit required"
- Tooltip: "Rows that could not be resolved to a valid Chain"

#### Card 8: Missing Assumptions
- Measure: `[Missing Assumption Count]`
- Format: `0`
- Subtitle: "Approval records incomplete"
- Conditional Formatting: Red text if > 0, else Green

---

### Section 3: Decision Status Table (Left Column, Below KPIs)

**Type:** Table visual

**Rows:** 
- Drag `'CM2 Governance Status'[Decision_ID]`
- Drag `'CM2 Governance Status'[Decision_Name]`
- Drag `'CM2 Governance Status'[Status]`
- Drag `'CM2 Governance Status'[Blocks_Publication]`

**Columns:**
| Field | Display | Format |
|-------|---------|--------|
| Decision_ID | Decision ID | Text |
| Decision_Name | Decision | Text |
| Status | Status | Text (Conditional: "APPROVED" = Green, "PENDING_APPROVAL" = Red) |
| Blocks_Publication | Blocks CM2? | Boolean (YES/NO) |

**Filter:** `[Blocks_Publication] = TRUE()` (show only decisions that affect CM2)

**Tooltip:**
```
Decision: [Decision_Name]
Status: [Status]
Owner: [Approved_By] (if blank, show "Awaiting assignment")
Evidence: [Evidence_Reference]
```

**Sorting:** Decision_ID ascending

---

### Section 4: Provisional Expense Waterfall (Center Column, Large)

**Type:** Stacked Column + Line Waterfall Chart

**X-Axis:** `'Date Table'[Month]` (Apr-26, May-26, Jun-26)

**Y-Axis Values:**
1. Base Contribution (Blue column)
2. Provisional Expense (Red column, stacked above)
3. Provisional CM2 (Green line, overlaid)

**Tooltips:**
```
Month: [Month]
NSV: [Total Primary Article NSV]
Expense: [Provisional Expense Lacs]
CM2: [Provisional CM2 Lacs]
CM2%: [Provisional CM2 %]
```

**Data Labels:** Show on CM2 line only

**Title:** "Monthly CM2 Waterfall (Provisional)"

---

### Section 5: Expense Breakdown by Category (Right Column)

**Type:** Pie or Donut Chart

**Legend:** `'PL Expense Input'[Expense Head]`

**Values:** `[Provisional Expense Lacs]`

**Tooltips:**
```
Expense Head: [Expense Head]
Amount: [Provisional Expense Lacs] Lakh
% of Total: (derived)
Status: [Data_Status] (from CM2_Provisional_Assumptions)
Decision: [Decision_ID]
```

**Title:** "Provisional Expense by Head (Q1 FY27)"

**Slicers:** Add expense category filter to let users drill into subcategories

---

### Section 6: Scenario Comparison (Below Waterfall)

**Type:** Clustered Column Chart or Table

**Scenario Filter:** Disconnected slicer with values:
- Base
- Optimistic
- Conservative

**X-Axis:** Scenario

**Y-Axis:** `[Scenario CM2 Lacs]` and `[Scenario CM2 %]`

**Dual-Axis:**
- Left: CM2 Lacs (Column, blue)
- Right: CM2 % (Line, orange)

**Tooltips:**
```
Scenario: [Scenario]
Expense (Base): [Scenario Expense Lacs]
CM2: [Scenario CM2 Lacs]
CM2%: [Scenario CM2 %]
Assumption Note: [Assumption_Note]
```

**Title:** "Scenario Analysis: Base vs Optimistic vs Conservative"

**Note:** This shows how different cost assumptions affect CM2, purely for planning. The base scenario is the provisional forecast; optimistic and conservative are illustrative only.

---

### Section 7: Reconciliation Table (Below KPIs, Center)

**Type:** Matrix Table

**Rows:**
- "Loaded Expense Total"
- "Mapped Expense"
- "Unmapped Expense"
- "Reconciliation Difference"

**Values:**
- Amount (Lakh)
- Count of rows (for unmapped)
- Control tolerance

**Data:**
| Item | Value | Tolerance | Status |
|------|-------|-----------|--------|
| Source Expense Total | [Source Expense Total Lacs] | — | PASS if ≥ 0 |
| Mapped Expense | [Mapped Expense Lacs] | — | PASS if ≥ 0 |
| Unmapped Expense | [Unmapped Expense Lacs] | — | WARN if > 0 |
| Reconciliation Diff | [Expense Reconciliation Difference] | ±0.01 L | PASS if |diff| < tol |

**Conditional Formatting:**
- Difference cell: Green if |diff| < 0.01, else Red

**Tooltip:**
```
This control reconciles the source expense file to the mapped/unmapped split.
Difference should be ≤ 0.01 L (rounding tolerance).
If non-zero, check for data quality issues in source file.
```

---

### Section 8: Approved vs Provisional Comparison (Optional, Right Column)

**Type:** Side-by-Side KPI Cards or Matrix

**If `[Approved CM2 Lacs]` is BLANK:**

```
CM2 APPROVED
Value: [Awaiting Finance Approval]
Decision D1: PENDING_APPROVAL
Decision D9: PENDING_APPROVAL
```

**If `[Approved CM2 Lacs]` is NOT BLANK:**

```
CM2 APPROVED              | CM2 PROVISIONAL
[Approved CM2 Lacs]       | [Provisional CM2 Lacs]
[Approved CM2 %]          | [Provisional CM2 %]
D1: APPROVED              | D1: PENDING_APPROVAL
D9: APPROVED              | D9: PENDING_APPROVAL
```

**Styling:** 
- Approved: Green background, black text
- Provisional: Amber background, black text

---

### Section 9: Filters & Slicers (Top-Right)

Add these slicers in a 2×2 grid:

1. **Financial Year** (from Date Table)
   - Default: FY27
   - Multi-select: ON

2. **Quarter** (from Date Table)
   - Default: Q1
   - Linked to Year

3. **Month** (from Date Table)
   - Default: (all)
   - Linked to Year + Quarter

4. **Chain** (from Fact Primary Article)
   - Default: (all)

5. **Brand** (from Fact Primary Article)
   - Default: Mamaearth
   - Multi-select: ON

6. **Scenario** (from CM2 Provisional Assumptions)
   - Default: Base
   - Values: Base, Optimistic, Conservative

7. **Expense Category** (from PL Expense Input or Provisioned Assumptions)
   - Default: (all)
   - Multi-select: ON

8. **Data Status** (from CM2 Provisional Assumptions)
   - Default: PROVISIONAL
   - Values: PROVISIONAL, APPROVED

**Slicer Styling:**
- Slicer cards should have border, padding, and subtle background
- Font: 10-11pt
- Clear button on each slicer

---

### Section 10: QC Status Footer

**Type:** Text box or single-value measure card

**Content:**

```
[CM2 QC Status]
Reason: [CM2 QC Reason]
Last Updated: [Last_Updated] (from governance table)
```

**Example Output:**
```
PENDING - Awaiting Finance Approval
Reason: Awaiting approval on decisions: D1, D2, D3, D4, D5, D6, D7, D9
Last Updated: 2026-07-25
```

**Styling:**
- Amber box, 10pt text
- Position: Bottom-right
- Hover: Expands to show full decision list

---

## Tab Navigation & Bookmarks

**Create 3 bookmarks** (View ▸ Bookmarks):

1. **Provisional View**
   - Show all provisional measures
   - Filter: `[CM2 Display Status] = "PROVISIONAL"`
   - Warning banner: VISIBLE
   - Approved CM2 cards: HIDDEN or grayed

2. **Approved View**
   - Show approved measures only
   - Filter: `[CM2 Display Status] = "APPROVED"`
   - Warning banner: HIDDEN
   - If approved measures are BLANK: show "Awaiting Finance Approval"
   - Provisional cards: HIDDEN

3. **Development/Scenario View**
   - Show both provisional and scenario measures
   - Scenario selector: ACTIVE
   - Reconciliation table: EXPANDED
   - Warning banner: VISIBLE

---

## Data Model Notes

**Required relationships:**
- `Date Table`[MonthStart] → `PL Expense Input`[MonthStart] (for MoM change measures)
- `Fact Primary Article`[Chain] ← `PL Expense Input`[Resolved Chain] (bridged via FILTER in measures, not a direct relationship)
- `Fact Primary Article`[Brand] ← `PL Expense Input`[Resolved Brand] (bridged via FILTER in measures)

**Calculated columns (add to PL Expense Input):**
- Resolved Chain (from DAX/13_CM2_Measures.dax)
- Resolved Brand (from DAX/13_CM2_Measures.dax)
- Resolved Category (from DAX/13_CM2_Measures.dax)
- Bad Brand Or Category (QC flag, from DAX/13_CM2_Measures.dax)

---

## Performance & Refresh

**Query Refresh Order:**
1. `Fact Primary Article` (from raw data folder)
2. `Date Table`
3. `PL Expense Input` (from `SeedData/Masters/`)
4. `CM2 Governance Status` (from governance CSV)
5. `CM2 Provisional Assumptions` (from assumptions CSV)
6. All calculations (automatic)

**Expected Refresh Time:** < 5 seconds (if data volumes are kept under 100K rows per table)

**Incremental Refresh Recommendation:**
- Set up incremental refresh on `Fact Primary Article` to load only the latest month
- `PL Expense Input` and governance tables are small; full refresh is fine

---

## Testing Checklist

### Data Quality

- [ ] All decisions in CM2 Governance Status table match config/cm2_decision_register.csv
- [ ] Reconciliation Difference = 0 ± 0.01 L
- [ ] Unmapped Expense Lacs > 0 (audit rows exist)
- [ ] Mapped Expense + Unmapped Expense = Source Total ± rounding

### Measures

- [ ] `[Provisional CM2 Lacs]` = NSV − Expense (correct calculation)
- [ ] `[Approved CM2 Lacs]` = BLANK while D1 or D9 is PENDING_APPROVAL
- [ ] `[CM2 Warning Message]` contains "PROVISIONAL" text
- [ ] `[Show CM2 Warning]` = TRUE when any Blocks_Publication decision is PENDING

### Visuals

- [ ] Warning banner visible on load
- [ ] KPI cards show non-zero values for NSV, Expense, Provisional CM2
- [ ] Decision table shows D1–D9 rows only (filtered to Blocks_Publication=TRUE)
- [ ] Waterfall chart displays all 3 months with correct values
- [ ] Expense breakdown pie shows sum of all expense heads
- [ ] Reconciliation table shows difference < 0.01 L

### Filters & Interactivity

- [ ] Month filter changes Waterfall chart
- [ ] Chain filter updates all visuals
- [ ] Scenario selector changes Scenario Comparison chart only (doesn't affect base Provisional CM2)
- [ ] Scenario Expense recalculates when scenario changes
- [ ] All slicers default correctly and respond to clicks

### Finance Workflow

- [ ] Page loads with 120 tests passing (dashboard + Power BI QC tests combined)
- [ ] After D1 is approved and patch script runs, `[Approved CM2 Lacs]` becomes non-blank
- [ ] After D1 + D9 approval, `[CM2 Display Status]` = "APPROVED"
- [ ] Warning banner disappears after all required approvals
- [ ] Approved View bookmark shows clean green "APPROVED - Ready for Publication"

---

## Known Limitations (Until Finance Approval)

- Approved CM2 will be BLANK while D1 or D9 is PENDING_APPROVAL
- ALLOC-001/002/003 (direct allocation rules) are not yet activated; D9 approval is required
- Unmapped expense rows cannot be auto-corrected; manual Chain/Brand tagging required
- Scenario measures are illustrative only and do not affect source data
- GST treatment (D2) is not yet determined; trade expense reconciliation may change

---

## Manual Steps for Power BI Developer

1. Create a new page named "CM2 Analysis — Provisional"
2. Add sections (1–10) as described above using Power BI visuals
3. Import the three Power Query queries from `PQ_CM2_Governance_Import.md`
4. Add the DAX measures from `DAX/14_CM2_Provisional_Measures.dax` to a `_Measures` table
5. Add calculated columns to `PL Expense Input` table (from `DAX/13_CM2_Measures.dax`)
6. Create the 3 bookmarks (Provisional / Approved / Development views)
7. Test against the checklist above
8. Publish to Power BI Service (or keep in Desktop for development)

**Do NOT activate this page for external viewing until D1 and D9 are approved and the patch script has been run.**

