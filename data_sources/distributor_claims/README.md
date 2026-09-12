# Distributor Claims Data Archive

**Purpose:** Staging directory for extracted distributor credit notes, debit notes, scheme claims, and reconciliation ledgers.

## Directory Structure

```
data_sources/distributor_claims/
  ├── credit_notes/           (optional subdirectory)
  ├── debit_notes/            (optional subdirectory)
  ├── scheme_claims/          (optional subdirectory)
  └── [extracted_files].csv   (or .xlsx)
```

## Expected Schema

All claim files must contain these mandatory columns (aliases supported):

| Standard Name | Accepted Aliases |
|---|---|
| `distributor_id` | dist_id, dist_code, dtr_id, vendor_code |
| `claim_id` | claim_no, claim_ref, doc_no, invoice_no |
| `claim_date` | doc_date, date, month, period |
| `claim_amount` | amount, claim_val, settled_value, claim_amt |
| `chain` | account, customer_name, retailer, key_account |
| `brand` | brand_name, division |
| `expense_type` | claim_type, scheme_type, promo_head, head |

## Workflow

1. **Extract Files:** Download and extract the `.zip` archive from Google Drive.
2. **Place Files:** Copy extracted CSV/Excel files to this directory.
3. **Validate Schema:** Run pre-check validation:
   ```bash
   python scripts/validate_claims_precheck.py
   ```
4. **Fix Issues:** If validation fails, resolve header/data type issues.
5. **Commit & Push:**
   ```bash
   git add data_sources/distributor_claims/
   git commit -m "feat(claims): add validated historical distributor claims data"
   git push origin claude/power-bi-data-analysis-f1vggw
   ```

## Post-Ingestion

Once committed, the **Claims Reconciliation Sub-Agent** will:
- Extract and parse all claim records
- Perform three-way matching (scheme grid, invoice volumes, off-take data)
- Categorize claims: SETTLED, PROVISIONED, DISPUTED, DUPLICATE
- Allocate claims across Chain × Brand × Category × Article × Month hierarchy
- Compute CM2 and Trade Spend ROI metrics
- Integrate verified claims into `data_master.json`

---

**Status:** Awaiting files  
**Branch:** `claude/power-bi-data-analysis-f1vggw`  
**Governance:** LOCKED_MULTI_YEAR_V2
