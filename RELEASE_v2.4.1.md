# v2.4.1: FY25 Reconciled Baseline & Article Master v2

**Release Date**: 2026-08-31  
**Git Commit**: `b86ee84`  
**Tag**: `v2.4.1-fy25-reconciled`

---

## Release Summary

This patch release locks the reconciled FY25 baseline dataset and the official `v2` Chain-Article-EAN mapping master, correcting a data quality issue that inflated the FY25 control total by ₹53.30 Lakhs.

---

## Key Fixes & Deliverables

### 1. FY25 Control Total Correction
- **Issue**: Synthesis script was filtering `Target_NSV_Lakh > 0`, incorrectly dropping ₹53.30L in legitimate negative billing adjustments (credit notes, returns)
- **Fix**: Changed filter to `Target_NSV_Lakh != 0` to preserve all adjustments
- **Result**: Control total now locked at **₹23,325.30 Lakhs** (exact match against composite billing registers)
- Total synthesized rows: **67,545 line items** (includes 1,228 negative adjustment rows = 1.8%)

### 2. Standardized 13-Digit EAN Master (v2)
- Stripped leading single quotes (`'`) and formatting artifacts across secondary proxy data (Q1 Apr–Jun 2026)
- Full Apr–Aug 2026 secondary window now used (Q1: 15,251 records + Q2: 22,019 records = 37,270 total)
- Unique article master: **379 distinct 13-digit numeric EANs**
- Validated account-article pairs: **8,277 tuples** across 38 retail chains
- Referential integrity: **100%**

### 3. Governance & Model Automation
- **Pytest Test Suite**: 7/7 governance tests passing (`tests/test_article_uniqueness.py`)
- **Power BI Automation**: Tabular Editor deployment scripts for 10 unified primary + YoY DAX measures
- **Pre-Flight Validation**: `scripts/validate_monthly_drop.py` for upcoming monthly drops
- **September 2026 Pipeline**: `scripts/automate_pbi_refresh.py` ready for ingestion

---

## Attached Release Assets
- `data_mappings/Chain_Article_EAN_Mapping_CORRECTED_v2.csv` — Official account-to-EAN mapping master (8,277 tuples)
- `PowerBI/RawDataFolders/Primary_Derived_FY25/Primary_Article_Synthesized_FY25.csv` — Reconciled primary derived fact dataset (67,545 rows)

---

## Tag This Release Locally

```bash
# Create and push tag (run from your local clone)
git tag -a v2.4.1-fy25-reconciled b86ee84 \
  -m "Patch release: FY25 reconciled to Rs23325.30L with EAN normalization and credit note handling"
git push origin v2.4.1-fy25-reconciled
```

## Create GitHub Release

```bash
gh release create v2.4.1-fy25-reconciled \
  "data_mappings/Chain_Article_EAN_Mapping_CORRECTED_v2.csv#Chain-Article-EAN Mapping (Official Master v2)" \
  "PowerBI/RawDataFolders/Primary_Derived_FY25/Primary_Article_Synthesized_FY25.csv#Synthesized Primary FY25 Dataset" \
  --title "v2.4.1: FY25 Reconciled Baseline & Article Master v2" \
  --notes-file RELEASE_v2.4.1.md
```

---

## Star-Schema Relationship Matrix (Power BI)

| Primary Key (Dimension) | Foreign Key (Fact) | Cardinality | Cross-Filter | Active |
|---|---|---|---|---|
| `Dim_Date[Date_Key]` | `Fact_Primary_Derived_FY25[Month_Label]` | 1→* | Single | ✅ |
| `Dim_Date[Date_Key]` | `Fact_Primary_Article_Monthly[Month_Label]` | 1→* | Single | ✅ |
| `Dim_Date[Date_Key]` | `Fact_SecondarySales[Month_Label]` | 1→* | Single | ✅ |
| `Dim_Date[Date_Key]` | `Fact_TOT_Claims[Month_Label]` | 1→* | Single | ✅ |
| `Dim_Chain[Canonical_Chain]` | `Fact_Primary_Derived_FY25[Chain]` | 1→* | Single | ✅ |
| `Dim_Chain[Canonical_Chain]` | `Fact_SecondarySales[Chain]` | 1→* | Single | ✅ |
| `Dim_Article[EAN]` | `Fact_Primary_Derived_FY25[Article_Code]` | 1→* | Single | ✅ |
| `Dim_Article[EAN]` | `Fact_Primary_Article_Monthly[Article_Code]` | 1→* | Single | ✅ |
| `Dim_Article[EAN]` | `Fact_SecondarySales[EAN]` | 1→* | Single | ✅ |
| `Dim_Brand[Brand_Name]` | `Dim_Article[Brand_Name]` | 1→* | Single | ✅ |
| `Dim_Store[Store_Code]` | `Fact_SecondarySales[Store_Code]` | 1→* | Single | ✅ |

**Guardrails**: Single-direction filtering only; all dimension keys as text strings (prevents EAN float truncation); Import/Dual mode for VertiPaq compression.
