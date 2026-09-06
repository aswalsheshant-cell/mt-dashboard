# Source Files — Archival & Reproducibility

**Issued:** 2026-08-08  
**Authority:** Analytics Engineering  
**Scope:** Dashboard data.js reproducibility; source data versioning  

---

## Problem Statement

The dashboard's `data.js` is generated from four source workbooks (Primary, Offtake, Universe, Promo) that are stored externally (Google Drive, per CLAUDE.md) and not committed to Git (due to large binary size). Without documented provenance and archival strategy, a full rebuild from source cannot be reproduced if source files are lost.

**This document establishes:**
1. External storage location of all source files
2. SHA256 checksums for audit trail
3. Archival cadence and retention policy
4. Rebuild procedure

---

## Source Files Inventory

### Required Source Workbooks

| Workbook | Storage Location | Format | Scope | Update Frequency | Owner |
|----------|------------------|--------|-------|------------------|-------|
| **Primary_ShipTo_FY25-26_to_May26** | Google Drive `/MT-Analytics/Sources/` | `.xlsb` (Power BI binary) | Distributor-to-Chain contribution percentages (May'25–May'26) | Monthly by Finance | Finance |
| **Offtake_Monthly_Store_FY27** | Google Drive `/MT-Analytics/Sources/Offtake/` | `.xlsb` | Store × Article × Month offtake volumes (FY27+) | Monthly by Supply Chain | Supply Chain |
| **Universe_Master_FY25-26** | Google Drive `/MT-Analytics/Sources/` | `.xlsb` | Article universe (SKUs, brands, packs, categories) | Quarterly by Product | Product |
| **Promo_Trade_Spend_Input** | Google Drive `/MT-Analytics/Sources/Promo/` | `.csv` or `.xlsx` | Promotional allocations and trade spend by brand | Monthly by Trade Marketing | Trade Marketing |

### Secondary Data Files (Seed Data)

| File | Location in Repo | Format | Purpose | Owner |
|------|------------------|--------|---------|-------|
| `GST_Rate_QC_Table.csv` | `PowerBI/SeedData/` | `.csv` | GST rate fallback for TOT% (cutover 2025-09-22) | Finance |
| `CustCode_Chain_Map.csv` | `PowerBI/SeedData/` | `.csv` | Customer code → Chain mapping for CM2 allocation | Supply Chain |
| `PL_Expense_Input.csv` | `PowerBI/SeedData/` | `.csv` | P&L expense data (CM2 denominator) | Finance |
| `DistCont_Patch_Approved_YYYYMMDD.csv` | `PowerBI/SeedData/Mapping/` | `.csv` | Finance-approved Jun'26 distributor allocation patch (if Decision 1 → Option B) | Finance |

**Note:** Seed data files are committed to Git (versioned).

---

## Build Reproducibility Procedure

### Full Rebuild from Source

To rebuild `dashboard/data.js` from scratch:

```bash
# 1. Obtain all source workbooks from Google Drive storage locations above
#    Download to a local folder (e.g., ~/MT-Sources/), keeping folder structure:
#    ~/MT-Sources/Primary_ShipTo_FY25-26_to_May26.xlsb
#    ~/MT-Sources/Offtake/Offtake_Monthly_Store_FY27.xlsb
#    ~/MT-Sources/Universe_Master_FY25-26.xlsb
#    ~/MT-Sources/Promo/Promo_Trade_Spend_Input.xlsx

# 2. Run full build
python scripts/build_dashboard_data.py \
  --src ~/MT-Sources \
  --out dashboard/data.js

# 3. Verify output
python -m py_compile scripts/build_dashboard_data.py
pytest scripts/test_pipeline.py -v
```

### Partial Refresh (Faster, Reuses Existing data.js)

If only specific data blocks need refresh (e.g., new month of Offtake):

```bash
# Refresh only Offtake block (FY27 monthly data)
python scripts/build_dashboard_data.py \
  --offtake-patch \
  --src ~/MT-Sources \
  --out dashboard/data.js

# Refresh only Primary + Insights (includes Jun'26 allocation if needed)
python scripts/build_dashboard_data.py \
  --primary-only \
  --src ~/MT-Sources \
  --out dashboard/data.js
```

---

## Source File Archival Strategy

### Monthly Archive Process (Part of Release Checklist)

**When:** Upon every successful `data.js` build release  
**Who:** Release Manager or Analytics Engineering  
**Steps:**

1. **Capture SHA256 Checksums**
   ```bash
   sha256sum ~/MT-Sources/*.xlsb ~/MT-Sources/**/*.xlsx >> \
     docs/source_checksums_$(date +%Y-%m-%d).txt
   ```

2. **Tag Git Commit**
   ```bash
   git tag -a release/data.js.FY27.M$(date +%m).$(date +%Y) \
     -m "data.js snapshot; source checksums in docs/source_checksums_*.txt"
   ```

3. **Archive Summary Entry**
   Add entry to `docs/ARCHIVE_LOG.md`:
   ```
   | 2026-08-08 | FY27-M05 | Primary+Offtake+Universe | 3.2 GB | ad7f2c1... | Production release |
   ```

### Retention Policy

- **Source files:** Keep indefinitely in Google Drive (external backup)
- **Checksums:** Keep in `docs/source_checksums_*.txt` alongside every build tag
- **Data.js snapshots:** Keep all Git tags (GitHub's cloud storage)
- **Audit trail:** Monthly summary in `docs/ARCHIVE_LOG.md` (query for rebuild without original files)

---

## Data Lineage for Audit

For compliance/audit, the following lineage is established:

```
Source Workbooks (External)
    ↓ (verified by SHA256)
scripts/build_dashboard_data.py (canonicalize + transform)
    ↓ (reconciliation gates)
Release Gate (G1-G10 validation)
    ↓ (if all gates pass)
dashboard/data.js (published)
    ↓ (GitHub Pages + Vercel)
Production Dashboard
```

**Critical:** Every `data.js` build must be accompanied by:
- Commit hash of `build_dashboard_data.py`
- SHA256 checksums of all source files used
- Release Gate report (`release_gate_report.json`)
- Build timestamp

---

## Missing Data Notifications

If a source file is missing or delayed:

| Source | Status | Impact | Workaround |
|--------|--------|--------|-----------|
| **Nielsen CSV** (Market Share) | AWAITING | FY27 Market Share data unavailable | Manual upload or use pre-agg FY25/26 only |
| **TDP CSV** (Distribution Points) | AWAITING | FY27 Distribution KPI unavailable | Supply Chain to provide; confirm SLA |
| **Jun'26 Distributor Allocation** | PENDING FINANCE DECISION | Jun'26 Primary data provisional | Finance Decision 1 will resolve (A/B/C) |

---

## Next Steps

1. **Immediate (By 2026-08-09):**
   - Finance Decision 1 & 2 approval enables final `data.js` archive
   
2. **Within 1 week:**
   - Create `docs/ARCHIVE_LOG.md` with first entry (this build)
   - Document Google Drive folder access credentials for team (separate secure channel)
   - Run test rebuild from scratch to validate procedure

3. **Ongoing:**
   - Monthly checksum capture at each release
   - Quarterly verification that archived sources can still rebuild current `data.js`

---

## Responsibility Matrix

| Task | Owner | Frequency |
|------|-------|-----------|
| Obtain source workbooks from Finance/Supply Chain | Release Manager | Monthly (at build time) |
| Verify source file integrity (SHA256) | Analytics Engineering | Every build |
| Run build.py and validate output | Analytics Engineering | Every build |
| Archive checksums and tag Git | Release Manager | Every build |
| Update ARCHIVE_LOG.md | Release Manager | Monthly |
| Test rebuild from archived sources | Analytics Engineering | Quarterly |

---

**This document is living; update as source file locations, formats, or retention policies change.**
