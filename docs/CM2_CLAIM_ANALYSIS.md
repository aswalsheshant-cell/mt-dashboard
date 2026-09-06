# CM2 & Distributor ROI — Claim Data Integration

## Overview

The Distributor × Chain Claim Master provides detailed claim expense data for:
- **CM2 Calculation**: Cost of Marketing 2 (chain-level deductions from primary NSV)
- **Distributor ROI**: Return on Investment analysis by distributor
- **Chain-level Analysis**: Expense breakdown and profitability impact

---

## Data Structure

### Claim Categories

All claims are organized into 7 expense categories:

1. **Chain Promo (On Invoice)** — Promotion passed through invoice price
   - Booking: Approved net claim
   - Owner: Sales Finance

2. **Extra Margin / Rate Difference** — Difference between approved chain margin and invoice margin
   - Booking: Approved difference
   - Owner: Commercial Finance

3. **Visibility** — Display, gondola, promoter or visibility support
   - Booking: Approved service expense
   - Owner: Trade Marketing

4. **Off Invoice / Debit Note Promo** — Promo recovered by chain through debit note
   - Booking: Validated debit-note value
   - Owner: Claims Team

5. **Freight / Transportation** — Approved logistics support
   - Booking: Approved freight
   - Owner: Supply Chain Finance

6. **Other Claims** — Listing, sampling, incentive, returns/damage/expiry
   - Booking: Category-owner approval required
   - Owner: Finance Controller

7. **Incentive** — Distributor/chain incentive schemes
   - Booking: Approved incentive
   - Owner: Commercial Finance

---

## Data Files

### Input
- `Distributor_Chain_Claim_Master_AprJun_2026.xlsx` — Master workbook with 8 sheets:
  - **Read Me**: Guidelines for maintaining claims
  - **Executive Summary**: KPI overview (56.5M total extracted, 45.2M included)
  - **Claim Master**: 201 detailed records (Month × Distributor × Chain × Category)
  - **Chain Summary**: 25 chains with claim breakdown
  - **Distributor Summary**: 20 distributors with monthly trends
  - **Exceptions**: 51+ items requiring review/approval
  - **Checks**: Source extraction & reconciliation validation
  - **Source Index**: 971+ evidence files indexed

### Output
- `dashboard/claim_data.json` — Processed claim data for dashboard integration:

```json
{
  "metadata": {
    "source": "Distributor_Chain_Claim_Master_AprJun_2026.xlsx",
    "months": ["Apr-2026", "May-2026", "Jun-2026"],
    "period": "Q1 FY27",
    "generated_at": "2026-08-30T..."
  },
  "claims": {
    "by_chain": {
      "D-Mart": {
        "total_claim_lakh": 24188.34,
        "by_category": {
          "Extra Margin / Rate Difference": 12080.81,
          "Freight / Transportation": 13.36
        }
      },
      "...": {}
    },
    "by_distributor": {
      "A Z Enterprises": {
        "total_claim_lakh": 8883.09,
        "apr_lakh": 3763.88,
        "may_lakh": 3128.20,
        "jun_lakh": 1991.02,
        "avg_monthly": 2961.03
      },
      "...": {}
    },
    "quality_summary": {
      "total_records": 201,
      "exceptions_count": 51
    }
  }
}
```

---

## CM2 Calculation

### Formula

```
CM2 = Primary NSV × (CM2% + Claim Expenses)
```

Where:
- **Primary NSV** = Net Sales Value from primary tab
- **CM2%** = Base CM2 percentage (approved by Finance)
- **Claim Expenses** = Distributor × Chain claims from this master

### Chain-Level Example: D-Mart

| Metric | Value | Notes |
|--------|-------|-------|
| Primary NSV (FY27 Q1) | ₹X,XXX Cr | From Primary tab |
| Claim Expenses | ₹241.88 Cr | Total from all categories |
| - Extra Margin/Rate Diff | ₹120.81 Cr | Largest component |
| - Freight | ₹0.13 Cr | Minor logistics cost |
| **CM2 Impact** | +₹241.88 Cr | Deduction from base CM2% |

### Process

1. **Extract chain claims** from `by_chain` JSON
2. **Filter by approved claims only** (Review Status = "Included")
3. **Add to base CM2% calculation** in dashboard or Power BI
4. **Result**: Final CM2% after all deductions = accurate product margin

---

## Distributor ROI Analysis

### Metrics

For each distributor, calculate:

```
Distributor ROI = (Primary Volume × Margin) - (Claim Expenses + Support Costs)
                  ─────────────────────────────────────────────────────────
                           Total Distributor Sales Volume
```

### Dashboard Integration

| Distributor | Q1 Total | Avg Monthly | Apr-26 | May-26 | Jun-26 | Trend | ROI% |
|-------------|----------|-------------|--------|--------|--------|-------|------|
| A Z Enterprises | 8,883.09 | 2,961.03 | 3,763.88 | 3,128.20 | 1,991.02 | ↓ Declining | TBD |
| Balaji Associates | 286.80 | 95.60 | 84.80 | 79.19 | 122.81 | ↑ Growing | TBD |
| Chhabra Traders | 2,576.73 | 858.91 | 1,406.13 | 1,170.61 | — | ↓ Declining | TBD |
| D.L. Sales | 3,221.27 | 1,073.76 | 1,323.32 | 1,019.82 | 878.13 | ↓ Declining | TBD |

### Key Insights

- **High Claim Distributors**: A Z Enterprises (8.9M), D.L. Sales (3.2M), Chhabra (2.6M)
- **Claim Reduction Opportunity**: Review exceptions for 51 items requiring approval
- **Freight Efficiency**: Low transportation costs (0.4% of total claims)
- **Off-Invoice Promo**: 1.7M — largest deduction risk area

---

## Maintenance & Refresh

### Monthly Process

1. **Collect claim workbooks** from all distributors (Apr/May/Jun format)
2. **Run extraction** on new files in appropriate date-stamped folder
3. **Update Claim Master** sheet with new rows (preserve QC Flags and Source References)
4. **Copy formulas** down in Actual Expense, Business Key, QC Flag columns
5. **Extend summary formulas** to include new months
6. **Run validation** (Checks sheet) — ensure all files extract to PASS
7. **Review Exceptions** — get owner decisions before final release
8. **Change release verdict** to PASS only after exceptions cleared
9. **Export to JSON** via `process_claim_master.py`
10. **Regenerate dashboard** data.js with updated claims

### Script Usage

```bash
# Process new claims file
python scripts/process_claim_master.py \
  --claim-excel PowerBI/RawDataFolders/Claims/Distributor_Chain_Claim_Master.xlsx \
  --output dashboard/claim_data.json

# Integrate into data build
python scripts/build_dashboard_data.py \
  --src PowerBI/RawDataFolders \
  --out dashboard/data.js
```

---

## Quality Assurance

### Checks Performed

| Check | Status | Result |
|-------|--------|--------|
| Total Extracted Actual | PASS | 56.5M across all distributors |
| Included & Mapped | PASS | 45.2M (80% confidence) |
| Chain Mapping Required | WARN | 9.4M (17% requires review) |
| Duplicate Business Keys | PASS | 0 duplicates |
| Release Verdict | PASS WITH WARNINGS | 51 exceptions queued |

### Exception Handling

**51 exceptions identified** — Requires Finance/Commercial approval:

| Issue | Count | Action |
|-------|-------|--------|
| Legacy claim workbooks not parsed (.xls/.xlsb) | 12 | Manual review required |
| Unmapped chain names | 8 | Standardization needed |
| Missing source evidence | 5 | Document before approval |
| Out-of-period claims | 3 | Reclassify to correct month |
| Negative claim values | 8 | Verify rate adjustments |
| **Total** | **51** | **Blocks release = FAIL** |

---

## Integration Points

### Dashboard Integration

Once claim data is validated and approved:

1. **CM2 Tab**: Show chain-wise claim breakdown
   - Drill by Distributor → Chain → Expense Category
   - Month-over-month trend
   - Compare to forecast

2. **Distribution Tab**: Chain profitability after claims
   - Primary NSV vs. Claim Expenses
   - ROI% by chain
   - Margin impact

3. **Distributor View** (New Tab):
   - Distributor-wise claims by month
   - Approval status & exception queue
   - ROI ranking

### Power BI Integration

- **Fact Claim**: New table (201 rows, 17 columns)
- **Relationships**: Chain → Fact Claim, Distributor → Fact Claim
- **Measures**: Sum(Actual Expense), Avg Claim by Category, Exception Count
- **Visuals**: Waterfall (NSV → CM2 → Profit), Trend by month, Scatter (ROI vs. Volume)

---

## Contacts & Owners

| Function | Owner | Decision Rights |
|----------|-------|-----------------|
| Data Extraction | Claims Team | Claim Master maintenance |
| Validation & QA | Finance QA | Exceptions approval |
| CM2 Methodology | Finance Controller | Formula & rates |
| Commercial Rules | Commercial Finance | Rate difference, incentive |
| Supply Chain | Supply Chain Finance | Freight approval |
| Trade Marketing | Trade Marketing | Visibility spend |

---

## References

- **Source**: Distributor_Chain_Claim_Master_AprJun_2026.xlsx (8 sheets, 973 evidence files indexed)
- **Maintenance Guide**: See "Read Me" sheet in workbook
- **Script**: `scripts/process_claim_master.py` (handles extraction, validation, JSON export)
- **Dashboard Data File**: `dashboard/claim_data.json` (output for UI rendering)
