# Power Query for CM2 Governance Import

These Power Query snippets import the governance decision register and status tables. Add them as new queries in Power BI Desktop **before** creating the DAX measures in `14_CM2_Provisional_Measures.dax`.

---

## Query 1: Import CM2_Governance_Status

**Source:** `SeedData/Masters/CM2_Governance_Status.csv`

**Steps:**

1. **Home** ▸ **New Source** ▸ **Text/CSV**
2. Select `CM2_Governance_Status.csv`
3. Click **Load**
4. Rename the query to `CM2 Governance Status`
5. Right-click the query ▸ **Load** (loads to the data model as a table, not a worksheet)

**Columns to validate after load:**
- `Decision_ID` (e.g., "D1", "D9", "D10")
- `Status` (should be "APPROVED" or "PENDING_APPROVAL")
- `Blocks_Publication` (boolean: TRUE for D1, D2, D3, D4, D5, D6, D7, D9; FALSE for D8, D10, D11, D12, D13)

**Relationships:** No relationships needed. This table is queried via LOOKUPVALUE() in the DAX measures.

---

## Query 2: Import CM2_Provisional_Assumptions (Optional for Scenarios)

**Source:** `SeedData/Masters/CM2_Provisional_Assumptions.csv`

**Steps:**

1. **Home** ▸ **New Source** ▸ **Text/CSV**
2. Select `CM2_Provisional_Assumptions.csv`
3. Click **Load**
4. Rename the query to `CM2 Provisional Assumptions`
5. Right-click the query ▸ **Load**

**Columns to validate after load:**
- `Decision_ID` (which decisions this assumption row depends on)
- `Scenario` (Base / Optimistic / Conservative)
- `Data_Status` (should be "PROVISIONAL")
- `Include_Status` (PENDING_APPROVAL while decisions are pending)
- `Expense_Lacs` (monetary values in Lakh)

**Relationships:** 
- Optional: `CM2 Provisional Assumptions`[Decision_ID] → `CM2 Governance Status`[Decision_ID] (for cascading status)

**Note:** This table is OPTIONAL if you want to model scenarios separately in Power BI. If you do not need scenarios, load it as reference-only (do not apply it to visuals until D1 is approved).

---

## Query 3: Create a Calculated Table for Required Decisions (Advanced)

If you want Power BI to automatically detect missing approvals, create this calculated table:

```
CM2 Required Decisions =
FILTER (
    'CM2 Governance Status',
    'CM2 Governance Status'[Blocks_Publication] = TRUE()
)
```

Then use in a measure:

```
Missing Approvals Count = COUNTROWS (
    FILTER (
        [CM2 Required Decisions],
        [Status] <> "APPROVED"
    )
)
```

---

## Import Checklist

- [ ] `CM2 Governance Status` table loaded and visible in model
- [ ] `CM2 Provisional Assumptions` table loaded (optional)
- [ ] All Date fields recognized as dates (not text)
- [ ] Status column values verified (no typos like "approved" vs "APPROVED")
- [ ] Governance table is set to **not** summarize (Properties ▸ Summarization ▸ Do Not Summarize)

---

## After Importing: Add Calculated Columns to PL Expense Input

These are **required** for the measures to work (from `DAX/13_CM2_Measures.dax`):

In the `PL Expense Input` table, add:

### Column 1: Resolved Chain

```dax
'PL Expense Input'[Resolved Chain] =
VAR _custCode = TRIM ( 'PL Expense Input'[Customer Code] )
VAR _chainIn = TRIM ( 'PL Expense Input'[Chain] )
VAR _viaCode = IF ( _custCode <> "", LOOKUPVALUE ( 'CustCode Chain Map'[Chain], 'CustCode Chain Map'[Customer Code], _custCode ) )
VAR _viaChain = IF ( _chainIn <> "" && CONTAINS ( VALUES ( 'Fact Primary Article'[Chain] ), 'Fact Primary Article'[Chain], _chainIn ), _chainIn )
RETURN COALESCE ( _viaCode, _viaChain )
```

### Column 2: Resolved Brand

```dax
'PL Expense Input'[Resolved Brand] =
VAR _brandIn = TRIM ( 'PL Expense Input'[Brand] )
RETURN IF ( _brandIn = "", BLANK(),
    IF ( CONTAINS ( VALUES ( 'Fact Primary Article'[Brand] ), 'Fact Primary Article'[Brand], _brandIn ), _brandIn, BLANK() ) )
```

### Column 3: Resolved Category

```dax
'PL Expense Input'[Resolved Category] =
VAR _catIn = TRIM ( 'PL Expense Input'[Category] )
RETURN IF ( _catIn = "", BLANK(),
    IF ( CONTAINS ( VALUES ( 'Fact Primary Article'[Category] ), 'Fact Primary Article'[Category], _catIn ), _catIn, BLANK() ) )
```

### Column 4: Bad Brand Or Category (QC flag)

```dax
'PL Expense Input'[Bad Brand Or Category] =
VAR _brandIn = TRIM ( 'PL Expense Input'[Brand] )
VAR _catIn = TRIM ( 'PL Expense Input'[Category] )
RETURN ( _brandIn <> "" && ISBLANK ( 'PL Expense Input'[Resolved Brand] ) )
    || ( _catIn <> "" && ISBLANK ( 'PL Expense Input'[Resolved Category] ) )
```

---

## Refresh Schedule

- `CM2 Governance Status`: Import after Finance updates `config/cm2_decision_register.csv`
  - Trigger: Manual refresh (or scheduled via Power BI Service)
  - File: `config/cm2_decision_register.csv` (not the CSV created here — this one is a copy of that register)
- `CM2 Provisional Assumptions`: Refresh after new scenarios are added or rates change
  - Trigger: Manual refresh or monthly (when rates are updated)
  - File: `PowerBI/SeedData/Masters/CM2_Provisional_Assumptions.csv`
- `PL Expense Input`: Refresh when new monthly expense rows arrive
  - File: `PowerBI/SeedData/Masters/PL_Expense_Input.csv`

---

## Testing the Import

After all queries and tables are loaded:

1. Open a blank table visual on a test page
2. Drag `'CM2 Governance Status'[Decision_ID]` and `'CM2 Governance Status'[Status]` onto it
3. Verify you see rows D1–D13 with their current statuses
4. If D1, D2, D3, D4, D5, D6, D7, D9 show "APPROVED": the test must fail (because they are currently PENDING_APPROVAL in the seed file)
5. Expected: D10, D11, D12, D13 show "APPROVED"; all others show "PENDING_APPROVAL"

If the table is empty or shows errors, check:
- File path in the CSV source query
- Column name typos in Power Query
- DAX formula syntax (copy paste might have corrupted quotes)

