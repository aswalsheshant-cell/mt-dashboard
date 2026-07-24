# June 2026 Data Onboarding — Execution Log

**Operator:** ___________________________  
**Date executed:** ___________________________  
**Environment:** Local machine (Python 3.x + pyxlsb)  

---

## STEP 0 — Pre-flight backup

```bash
cp dashboard/data.js dashboard/data.js.bak.$(date +%Y%m%d_%H%M)
```

| | |
|---|---|
| Backup file created | `dashboard/data.js.bak.YYYYMMDD_HHMM` |
| Backup size | _____ MB |
| Original `data.js` last modified | _____________________________ |

---

## STEP 1 — Source file receipt

| Field | Value |
|---|---|
| Primary xlsb filename | _____________________________ |
| Primary xlsb file size | _____________________________ |
| Primary xlsb last modified date | _____________________________ |
| Received from | _____________________________ |
| Stored at path | `PowerBI/RawDataFolders/Primary_Article_Monthly_Source/` |
| Offtake xlsb filename | _____________________________ |
| Offtake xlsb file size | _____________________________ |
| Offtake xlsb last modified date | _____________________________ |
| Stored at path | `PowerBI/RawDataFolders/Offtake_Source/` |

---

## STEP 2 — Primary xlsb: header inspection

```bash
python scripts/split_primary_article_xlsb.py --headers-only \
    --src "PowerBI/RawDataFolders/Primary_Article_Monthly_Source/<filename>.xlsb"
```

| Field | Value |
|---|---|
| Column headers detected | _____________________________ |
| Month column name | _____________________________ |
| Month column format (date serial / text "Jun'26" / other) | _____________________________ |
| `--header-row` flag needed? (default=1) | _____________________________ |
| Any unexpected columns | _____________________________ |

---

## STEP 3 — Primary split

```bash
python scripts/split_primary_article_xlsb.py \
    --src "PowerBI/RawDataFolders/Primary_Article_Monthly_Source/<filename>.xlsb" \
    --out "PowerBI/RawDataFolders/Primary_Article_Monthly/" \
    --header-row 1
```

| Field | Value |
|---|---|
| Output file created | `primary_article_Jun_26.csv` ✅ / ❌ |
| Output row count (excl. header) | _____________________________ |
| Any other months split (list them) | _____________________________ |
| Split duration | _____________________________ |

---

## STEP 4 — Mapping audit

```bash
python scripts/audit_jun26_mapping.py
```

### Chain audit (Check 1)

| Field | Value |
|---|---|
| Unique chains in Jun'26 | _____________________________ |
| New DIRECT chains (informational) | _____________________________ |
| New DISTRIBUTOR chains needing mapping (**blocker**) | _____________________________ |
| Chains to verify in CHAIN_ALIASES | _____________________________ |
| CHAIN_ALIASES check result | PASS ✅ / FAIL ❌ |

### SAP code audit (Check 2)

| Field | Value |
|---|---|
| Unique SAP codes in Jun'26 | _____________________________ |
| New SAP codes not in CustomerCode_Zone_State_Mapping.csv (**blocker**) | _____________________________ |
| SAP check result | PASS ✅ / FAIL ❌ |

### Ship-To audit (Check 3, informational)

| Field | Value |
|---|---|
| Unique Ship-To names in Jun'26 | _____________________________ |
| New Ship-To names not in ShipToMaster.csv | _____________________________ |

### Audit overall result

| | |
|---|---|
| **BLOCKERS found** | YES — do NOT proceed / NO — proceed ✅ |

---

## STEP 5 — Mapping file updates (only if blockers found)

### ChainAccount_Mapping_Inferred.csv changes

| Chain Name | Ship-To Name | Account | Direct/Distributor | Avg Cont% | Added by |
|---|---|---|---|---|---|
| | | | | | |

### CustomerCode_Zone_State_Mapping.csv changes

| Customer Code | Ship-To Name | State | Zone | Chain | Added by |
|---|---|---|---|---|---|
| | | | | | |

| New rows added to ChainAccount_Mapping_Inferred.csv | _____ |
| New rows added to CustomerCode_Zone_State_Mapping.csv | _____ |
| Re-ran audit after mapping updates | PASS ✅ / FAIL ❌ |

---

## STEP 6 — Primary detail rebuild (`--detail-only`)

```bash
python scripts/build_dashboard_data.py --detail-only \
    --src PowerBI/RawDataFolders/Primary_Article_Monthly/ \
    --out dashboard/data.js
```

| Field | Value |
|---|---|
| `detail_records` row count written | _____________________________ |
| `detail_meta.fyx_primary.FY27.months` | _____________________________ |
| FY27 months in primary (expected: Apr-26, May-26, Jun-26) | _____________________________ |
| TOT% blended | _____________________________ |
| CM2% | _____________________________ |
| Command exit status | 0 ✅ / error ❌ |
| Any warnings or errors | _____________________________ |

---

## STEP 7 — Offtake xlsb: header inspection

```bash
python scripts/split_offtake_store_article_xlsb.py --headers-only \
    --src "PowerBI/RawDataFolders/Offtake_Source/<filename>.xlsb"
```

| Field | Value |
|---|---|
| Column headers detected | _____________________________ |
| Month column name and format | _____________________________ |
| Any unexpected columns | _____________________________ |

---

## STEP 8 — Offtake split

```bash
python scripts/split_offtake_store_article_xlsb.py \
    --src "PowerBI/RawDataFolders/Offtake_Source/<filename>.xlsb" \
    --out "PowerBI/RawDataFolders/Offtake_Monthly/"
```

| Field | Value |
|---|---|
| Output file created | `offtake_store_article_Jun_26.csv` ✅ / ❌ |
| Jun'26 output row count | _____________________________ |
| Apr'26 file row count (re-check for drift) | _____________________________ |
| May'26 file row count (re-check for drift) | _____________________________ |

---

## STEP 9 — Offtake patch (`--offtake-patch`)

**IMPORTANT: provide ALL FY27 months in `--src`, not just June, so the patch recomputes FY27 from scratch (idempotent — never double-counts).**

```bash
python scripts/build_dashboard_data.py --offtake-patch \
    --src PowerBI/RawDataFolders/Offtake_Monthly/ \
    --out dashboard/data.js
```

| Field | Value |
|---|---|
| Source months found by patch | _____________________________ |
| `fy_tags` after patch | _____________________________ |
| `total_fy27` (Lakh) | _____________________________ |
| `months_fy27` | _____________________________ |
| Apr-26 offtake total unchanged from pre-patch | _____ Lakh (was: 4024.0 Lakh) ✅ / ❌ |
| May-26 offtake total unchanged from pre-patch | _____ Lakh (was: 4527.61 Lakh) ✅ / ❌ |
| FY25 / FY26 totals unchanged | ✅ (untouched by patch) |
| Command exit status | 0 ✅ / error ❌ |

---

## STEP 10 — Business validation

Cross-check 3–5 monthly NSV totals against source workbooks (Google Drive).

| Month | Source NSV (Cr) | Dashboard NSV (Cr) | Variance | Status |
|---|---|---|---|---|
| Jun'26 Primary | | | | ✅ / ❌ |
| May'26 Primary | | | | ✅ / ❌ |
| Apr'26 Primary | | | | ✅ / ❌ |
| Jun'26 Offtake | | | | ✅ / ❌ |
| May'26 Offtake | | | | ✅ / ❌ |

**NOTE: Do NOT use estimated totals as acceptance criteria. Validate against actual source workbook values.**

Acceptable variance threshold: ±0.5% (rounding/float precision). Flag anything larger for Finance review.

---

## STEP 11 — Dashboard visual QA

Open `dashboard/index.html` in browser and sweep all 12 tabs × FY27 filter:

| Tab | FY27 visible | No NaN/undefined | Cards correct | Status |
|---|---|---|---|---|
| Data Explorer | | | | |
| Overview | | | | |
| Primary | | | | |
| Offtake | | | | |
| P&L | | | | |
| Category & Pack | | | | |
| Forecast | | | | |
| Promo & Trade Spend | | | | |
| Market Share | | | | |
| Distribution | | | | |
| Performance & Comparison | | | | |
| Insights & Way Forward | | | | |

| Overall QA result | PASS ✅ / FAIL ❌ — describe any failures: |
|---|---|
| | |

---

## STEP 12 — Git commit and push

```bash
git add dashboard/data.js \
        PowerBI/SeedData/Mapping/ChainAccount_Mapping_Inferred.csv \
        PowerBI/SeedData/Mapping/CustomerCode_Zone_State_Mapping.csv \
        PowerBI/RawDataFolders/Primary_Article_Monthly/primary_article_Jun_26.csv \
        PowerBI/RawDataFolders/Offtake_Monthly/offtake_store_article_Jun_26.csv

git commit -m "data: add Jun'26 Primary + Offtake; update FY27 dashboard

- primary_article_Jun_26.csv: <ROW_COUNT> rows
- offtake_store_article_Jun_26.csv: <ROW_COUNT> rows
- Mapping: <N> new SAP codes, <N> new chain rows added
- FY27 offtake total_fy27: <VALUE> Lakh (Apr+May+Jun)
- FY27 primary months: Apr-26, May-26, Jun-26"

git push -u origin claude/ai-agent-api-analyst-status-g5a1in
```

| Field | Value |
|---|---|
| Commit SHA | _____________________________ |
| Push status | ✅ / ❌ |
| PR created / updated | _____________________________ |

---

## Summary

| Check | Result | Notes |
|---|---|---|
| Pre-flight backup | ✅ / ❌ | |
| Source files received | ✅ / ❌ | |
| Primary split | ✅ / ❌ | |
| Mapping audit | PASS / FAIL | Blockers: |
| Mapping files updated | ✅ / N/A | |
| `--detail-only` rebuild | ✅ / ❌ | |
| Offtake split | ✅ / ❌ | |
| `--offtake-patch` rebuild | ✅ / ❌ | |
| Business validation | ✅ / ❌ | |
| Dashboard QA | ✅ / ❌ | |
| Committed and pushed | ✅ / ❌ | |

**Onboarding complete:** _____________________________ (date/time)  
**Signed off by:** _____________________________
