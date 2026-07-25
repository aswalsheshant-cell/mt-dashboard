# CM2 Provisional Reference — Internal Sales Dashboard Development

This folder contains all reference materials, development assets, and governance documentation for the **provisional CM2 calculation** used in the internal sales-reference dashboard. These assets support scenario analysis and financial modeling during the period when D1 (COGS inclusion decision) and D9 (allocation rule activation decision) are pending Finance approval.

## Purpose

The internal sales-reference dashboard uses **Provisional CM2** to enable:
- Real-time sales performance tracking at brand/chain/category level
- Scenario analysis (Base, Optimistic, Conservative)
- Finance scenario planning without presenting tentative expenses as approved
- Editable expense source data for future replacement with validated actuals

**This is NOT a Finance-approved dashboard.** CM2 is marked explicitly as `PROVISIONAL` and subject to change after Finance approval of blocking decisions.

## Governance Status

- **D1 (COGS Inclusion):** `PENDING_APPROVAL` — amount 4,411.21L on GMV/MRP basis (14.08% rate, D10 approved)
- **D9 (Allocation Rules):** `PENDING_APPROVAL` — activation of ALLOC-001, ALLOC-002, ALLOC-003 only
- **All other decisions (D2–D8, D10–D13):** See `config/cm2_decision_register.csv`

Until Finance approves D1 and D9:
- Provisional CM2 is calculated and displayed
- Approved CM2 returns BLANK
- Example expense rows remain marked in `PL_Expense_Input.csv`
- Assumptions are editable via `SeedData/CM2_Provisional_Assumptions.csv`

## Folder Structure

```
PowerBI/Reference/CM2_Provisional/
├── README.md (this file)
├── config/
│   ├── cm2_decision_register.csv      Decision status and governance metadata
│   ├── cm2_formula.csv                Formula components and D-references
│   ├── cm2_allocation_rules.csv       Allocation rule catalog (D9 decision)
│   └── cm2_expense_taxonomy.csv       Expense category and subcategory taxonomy
├── SeedData/
│   ├── CM2_Governance_Status.csv      Governance status snapshot for Power BI
│   └── CM2_Provisional_Assumptions.csv Editable expense assumptions (17 rows)
├── DAX/
│   └── 14_CM2_Provisional_Measures.dax DAX measures (Provisional CM2, Approved CM2, display logic)
├── QuickSetup/
│   └── PQ_CM2_Governance_Import.md    Power Query setup guide (step-by-step import)
└── docs/
    ├── PageBlueprint_CM2_Analysis_Provisional.md  Tab specification (10 sections, KPIs, charts)
    └── Finance_Validation/            (placeholder for future Finance evidence)
```

## Key Files

### Configuration (`config/`)

- **`cm2_decision_register.csv`** — Master governance table listing all 13 decisions (D1–D13), their status, approver, date, amount affected, and approved option. Used by:
  - `scripts/build_dashboard_data.py` to derive provisional state flags
  - `scripts/validate_cm2_governance_before_patch.py` to gate the patch script
  - Tests: `test_provisional_dashboard_workflow.py` (PROV-01–06, PROV-22–25)

- **`cm2_formula.csv`** — Formula definition showing which D-references are DRAFT (pending) vs APPROVED. Example:
  ```
  formula_id,description,status,decision_reference
  F1,Provisional CM2 = NSV - Provisional Expense,DRAFT,D1/D9
  F2,Approved CM2 = NSV - Approved Expense,APPROVED,D10–D13 only (no D1/D9)
  ```
  Used by `scripts/build_dashboard_data.py` to set `formula_status` in `data.js`.

- **`cm2_allocation_rules.csv`** — Catalog of allocation rules. D9 decision gates whether ALLOC-001 through ALLOC-003 (direct allocation) are activated. Current state: DRAFT. Example:
  ```
  allocation_id,description,allocation_type,active_status,decision_reference
  ALLOC-001,Direct Brand → CM2,direct,draft_pending_D9,D9
  ALLOC-002,Direct Chain → CM2,direct,draft_pending_D9,D9
  ...
  ```

- **`cm2_expense_taxonomy.csv`** — Expense category and subcategory master (COGS, LOGISTICS, TRADE_EXPENSE, FIELD_FORCE_COST, etc.). Used for expense classification and reconciliation.

### Seed Data for Power BI (`SeedData/`)

- **`CM2_Governance_Status.csv`** — Governance snapshot for Power BI queries. Contains:
  - `Decision_ID`, `Decision_Name`, `Status` (APPROVED / PENDING_APPROVAL)
  - `Approved_By`, `Approved_At` (empty for pending)
  - `Blocks_Publication` (TRUE for D1–D7, D9; FALSE otherwise)
  
  Used by Power BI DAX measures to:
  - Conditionally calculate Approved CM2 (returns BLANK if D1/D9 pending)
  - Display governance status in the CM2 Analysis tab

- **`CM2_Provisional_Assumptions.csv`** — **Editable** expense assumptions (17 rows):
  - COGS monthly breakdown + Q1 total (4,411.21L base)
  - Logistics monthly breakdown + Q1 total (360.37L base)
  - Trade Expense 47.65L (EXAMPLE, to be replaced)
  - Field Force Cost 737.16L
  - Optimistic and Conservative scenarios
  
  All rows tagged `Data_Status=PROVISIONAL`, `Include_Status=PENDING_APPROVAL`, `Approved_By=blank`.
  
  **This file is intended to be replaced with real expense data.** To update:
  1. Open in Excel or CSV editor
  2. Replace EXAMPLE rows (marked with "EXAMPLE ROW" in Remarks)
  3. Add real monthly actuals for Q1 FY27
  4. Keep `Data_Status=PROVISIONAL` until Finance approves
  5. Refresh Power BI

### DAX Measures (`DAX/`)

- **`14_CM2_Provisional_Measures.dax`** — 18 measures organized into three groups:
  
  1. **Base (always calculated):**
     - `Provisional CM2 Lacs = [Base Contribution] - [Provisional Expense]`
     - Displayed regardless of governance state
  
  2. **Conditional (returns BLANK if pending):**
     - `Approved CM2 Lacs = IF([Formula_Status]="APPROVED", ..., BLANK())`
     - Only displays when D1/D9 approved
  
  3. **Governance helpers:**
     - `Formula_Status` — derives from CM2_Governance_Status table
     - `All_Decisions_Approved` — TRUE only if D1–D9 all APPROVED
     - `CM2 Display Status` — text label ("PROVISIONAL" / "APPROVED")
     - `Show CM2 Warning` — TRUE while provisional
     - `CM2 Warning Message` — reason text

  **Key constraint:** Approved CM2 does NOT fall back to Provisional (no COALESCE). Until Finance approves D1/D9, Approved CM2 is blank.

### Power Query Setup (`QuickSetup/`)

- **`PQ_CM2_Governance_Import.md`** — Step-by-step guide to import seed tables into Power BI:
  1. Load `CM2_Governance_Status.csv` as table
  2. Optionally load `CM2_Provisional_Assumptions.csv`
  3. Add calculated columns to PL Expense Input
  4. Create relationships
  5. Refresh schedule

### Documentation (`docs/`)

- **`PageBlueprint_CM2_Analysis_Provisional.md`** — Detailed specification for the "CM2 Analysis — Provisional" Power BI tab (10 sections):
  1. Warning banner (red/amber, full-width, conditional)
  2. KPI card row (NSV, Base Contribution, Provisional Expense, Provisional CM2, etc.)
  3. Decision status table (D1–D9, filtered)
  4. Monthly waterfall chart
  5. Expense breakdown pie/donut
  6. Scenario comparison (Base/Optimistic/Conservative)
  7. Reconciliation control table
  8. Approved vs Provisional side-by-side
  9. Filters and slicers
  10. QC status footer

- **`Finance_Validation/`** — Placeholder folder for future Finance approval evidence (approver email, date, decision memo, etc.)

## Integration with Dashboard

### Dashboard Runtime Files (DO NOT MOVE)

The following files remain in their original locations and reference the config files:

- **`scripts/build_dashboard_data.py`** — Reads `cm2_decision_register.csv`, `cm2_formula.csv`, and generates `data.js` with provisional state flags:
  ```python
  def _cm2_provisional_state(expense_rows, formula_path=None):
      # Reads PowerBI/Reference/CM2_Provisional/config/cm2_formula.csv
      # Returns: formula_status, provisional, example_data_only, provisional_reasons
  ```
  Updated to reference new paths in reference folder.

- **`dashboard/data.js`** — Generated output containing CM2 block with:
  ```json
  "cm2": {
    "provisional": true,
    "formula_status": "DRAFT",
    "example_data_only": true,
    "provisional_reasons": [
      "CM2 formula (D1 COGS, D9 allocation rules) pending Finance approval",
      "Expense assumptions contain example data; replace with actuals"
    ],
    ...
  }
  ```

- **`dashboard/index.html`** — Renders provisional banner conditionally:
  ```javascript
  ${cm2Prov?`<div class="cm2-provisional">...</div>`:''}
  ```

### Validation & Patch Scripts (Runtime)

- **`scripts/validate_cm2_governance_before_patch.py`** — Pre-patch validation gate. Reads `PowerBI/Reference/CM2_Provisional/config/cm2_decision_register.csv` to enforce:
  - Status = APPROVED (not PENDING_APPROVAL)
  - Named approver (not "Finance" or blank)
  - Approval date YYYY-MM-DD format
  - Approved option populated

- **`scripts/patch_cm2_provisional.py`** — Idempotent patch script. Clears provisional flags only after validation passes.

### Tests (Updated)

- **`tests/test_provisional_dashboard_workflow.py`** — 28 tests validating provisional workflow (PROV-01–28)
- **`tests/test_powerbi_cm2_provisional.py`** — 29 tests for Power BI CM2 provisional setup (PBI-GOV, PBI-ASSUM, etc.)
- Both read from `PowerBI/Reference/CM2_Provisional/config/` and `PowerBI/Reference/CM2_Provisional/SeedData/`

## Finance Approval Workflow

When Finance is ready to approve D1 and/or D9:

1. **Decision maker** provides:
   - Named approver (e.g., "Sheetal Nair")
   - Approval date (YYYY-MM-DD format)
   - Approved option (D1: "(a) INCLUDE" or "(b) EXCLUDE"; D9: "APPROVE" or "keep DRAFT")
   - Evidence (email, decision memo, etc.)

2. **Data engineer** updates:
   ```bash
   # Edit config/cm2_decision_register.csv (now at PowerBI/Reference/CM2_Provisional/config/)
   # Set D1: status=APPROVED, approved_by=<name>, approved_at=<date>, approved_option=<choice>
   # Set D9: status=APPROVED, approved_by=<name>, approved_at=<date>, approved_option=<choice>
   ```

3. **Validation**:
   ```bash
   python3 scripts/validate_cm2_governance_before_patch.py D1 D9
   # Must return: ✅ ALL VALIDATIONS PASSED
   ```

4. **Patch & Deploy**:
   ```bash
   python3 scripts/patch_cm2_provisional.py --dry-run  # Preview changes
   python3 scripts/patch_cm2_provisional.py             # Apply
   python3 scripts/build_dashboard_data.py --primary-only --src <dir> --out dashboard/data.js
   ```

5. **Dashboard result**:
   - `cm2.provisional` → `false`
   - `formula_status` → `APPROVED`
   - Provisional banner hides
   - Approved CM2 Lacs displays (no longer blank)

## Example Rows & Data Quality

Three example rows in `PL_Expense_Input.csv` must be replaced before Finance approval:

1. **Visibility Spend 12.50L (Dmart)** — marked "EXAMPLE ROW"
2. **Scheme / Trade Spend 28.40L (Reliance Retail)** — marked "EXAMPLE ROW"
3. **BA Cost 6.75L (Apollo)** — marked "EXAMPLE ROW"

Total example contribution: 47.65L (noted in CM2_Provisional_Assumptions.csv).

When replacing:
- Preserve the row structure (Financial_Year, Chain, Brand, Expense_Category, etc.)
- Keep Data_Status=PROVISIONAL until Finance approves
- Remove "EXAMPLE ROW" from Remarks
- Add real source reference (e.g., MTIndirect_Claim_April_26_to_June_26.xlsb)
- Power BI refresh incorporates changes automatically

## CI/Testing

All tests run against files in `PowerBI/Reference/CM2_Provisional/`:
```bash
python -m unittest discover -s tests -v
```

Test files automatically updated to reference new paths:
- `tests/test_provisional_dashboard_workflow.py` (28 PROV-* tests)
- `tests/test_powerbi_cm2_provisional.py` (29 PBI-* tests)
- `tests/test_operationalisation.py` (governance checks)
- `.github/workflows/dataeng.yml` (CI runs all tests)

## Notes

- **Provisional state is derived** from config, never hardcoded. If `cm2_formula.csv` status changes, `data.js` re-derives provisional flags on next build.
- **Amounts are guarded** — patch script asserts CM2 amounts never change during flag operations.
- **No fallback logic** — Approved CM2 does not default to Provisional. Until Finance approves, Approved CM2 is blank.
- **Editable by design** — Expense assumptions are CSV; teams can edit, add rows, and re-run Power BI refresh without code changes.
- **GitHub-tracked** — Only config CSVs and Markdown docs are committed; `.pbix` files are not (built locally in Power BI Desktop).

---

**Last Updated:** 2026-07-25  
**Status:** Provisional — Ready for Internal Sales-Reference Dashboard Review  
**Limitation:** CM2 remains provisional. Finance approval and validated expenses required before finalized CM2.
