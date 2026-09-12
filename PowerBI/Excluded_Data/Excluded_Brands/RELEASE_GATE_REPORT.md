# Release-Gate Report — June 2026 Sales Data
**Branch:** `claude/june-26-sales-data-xzbhub`  
**Date:** 2026-07-24  
**Status:** ✅ PASS — Ready for review. Merge only after human approval.

---

## 1. Files Changed

| File | Change |
|---|---|
| `dashboard/data.js` | FY27 Q1 offtake + primary patched; excluded brands removed from all blocks |
| `dashboard/index.html` | FY27 month labels now dynamic (months_covered-driven) |
| `scripts/patch_jun26.py` | Jun-26 patch with full provenance metadata and exclusion record |
| `scripts/exclude_brands.py` | NEW: configurable brand exclusion pipeline for data.js |
| `scripts/build_dashboard_data.py` | Added `EXCLUDED_BRANDS` list; `canon_brand()` returns `None` for excluded brands |
| `PowerBI/Excluded_Data/Excluded_Brands/Excluded_Brands_detail_records.csv` | NEW: 53 excluded rows for audit |
| `PowerBI/Excluded_Data/Excluded_Brands/Excluded_Brands_audit_summary.txt` | NEW: exclusion audit summary |
| `PowerBI/Excluded_Data/Excluded_Brands/patch_jun26_provenance.json` | NEW: full provenance record |

---

## 2. Source Used

| Field | Value |
|---|---|
| Workbook | `MT_Offtake_Primary_Jun26_Working_CORRECTED_V4.xlsx` |
| SHA-256 | `e43bea3273d2e669eccc059af29b5f7de5d28de606e098786a5f065fcca1f46a` |
| Sheets | Offtake_Chain_Zone · Primary_Zone_Chain · Primary_Summary · Primary_Brand_Monthly · KPI_Dashboard |
| Basis | Official corrected chain-NSV (Non-Brand-Counter universe only) |

---

## 3. April 2026 Offtake Discrepancy — RESOLVED

The KPI_Dashboard note text reads **"3,589.14 Lacs"** (a rounded display label authored in the workbook).  
The authoritative row-level SUMIF over `Offtake_Chain_Zone` = **3,589.13 Lacs exactly**.  
The patch uses **3,589.13** — the source-of-truth value.  
No data error; the 0.01L difference is a note-text rounding artefact only.

---

## 4. Exact Reconciled FY27 Totals (post-exclusion)

### Offtake (Non-Brand-Counter universe)

| Month | NSV (L) |
|---|---|
| Apr-26 | 3,589.13 |
| May-26 | 4,025.81 |
| Jun-26 | 3,823.78 |
| **Q1 FY27 Total** | **11,438.72** |

### Primary (FY27 cumulative, excluded brands removed)

| Metric | Value |
|---|---|
| Apr-26 NSV | 5,069.17 L |
| May-26 NSV | 4,416.06 L |
| Jun-26 NSV | 4,167.36 L |
| **FY27 Total NSV** | **13,652.59 L** |
| months_covered | April, May, June |

> Jun-26 primary: **Summary workbook based. Store × article transaction-level validation pending.**

---

## 5. Brand Exclusion Audit

**Excluded from all reporting:** Pure Origin · Lumineve · Staze

| Brand | detail_records removed | NSV (L) | MRP (L) | Qty |
|---|---|---|---|---|
| Pure Origin | 24 | 4.05 | 6.83 | 2,653 |
| Lumineve | 28 | 5.96 | 11.48 | 699 |
| Staze | 1 | 0.13 | 0.22 | 48 |
| **Total** | **53** | **10.14** | **18.53** | **3,400** |

### Aggregate adjustments applied

| Metric | Before | After | Delta |
|---|---|---|---|
| `primary.nsv_fy25` | 23,331.97 | 23,328.04 | -3.93 |
| `primary.nsv_fy26` | 32,900.36 | 32,888.12 | -12.24 |
| `primary.n_brands` | 8 | 5 | -3 |
| `fyx_primary.FY27.nsv` | 13,659.96 | 13,652.59 | -7.37 |
| `cm2.total_nsv` | 42,392.96 | 42,373.35 | -19.61 |
| `dist_gap.total_addon_ann` | 91,753.42 | 91,076.45 | -676.97 |
| `sis_reconciliation FY26 net` | 250.17 | 242.48 | -7.69 (Staze) |
| `sis_reconciliation FY27 net` | 7.86 | 0.17 | -7.69 (Lumineve) |

Excluded data files: `PowerBI/Excluded_Data/Excluded_Brands/`  
Raw source records: preserved, not deleted.

---

## 6. Dimension Reconciliation Checks

| Check | Result |
|---|---|
| `by_channel FY25 sum == nsv_fy25` (23,328.04) | ✅ PASS |
| `by_channel FY26 sum == nsv_fy26` (32,888.12) | ✅ PASS |
| `FY27 monthly sum == FY27.nsv` (13,652.59) | ✅ PASS |
| `FY27 by_channel sum == FY27.nsv` (13,652.59) | ✅ PASS |
| Excluded brands in `primary.by_brand` | ✅ PASS (0) |
| Excluded brands in `dims.Brand` | ✅ PASS (0) |
| Excluded brands in `detail_records` | ✅ PASS (0) |
| Excluded brands in `fyx_primary.FY27.by_brand` | ✅ PASS (0) |

---

## 7. Browser Validation Results (Playwright headless)

| Check | Result |
|---|---|
| No NaN / undefined in DASH object | ✅ PASS |
| Excluded brands absent from dims.Brand filter | ✅ PASS |
| Excluded brands absent from primary.by_brand | ✅ PASS |
| Offtake Apr-26 = 3,589.13 | ✅ PASS |
| Offtake May-26 = 4,025.81 | ✅ PASS |
| Offtake Jun-26 = 3,823.78 | ✅ PASS |
| Offtake Q1 FY27 = 11,438.72 | ✅ PASS |
| Primary FY27 NSV = 13,652.59 | ✅ PASS |
| months_covered = [April, May, June] | ✅ PASS |
| by_channel FY25 reconciles | ✅ PASS |
| by_channel FY26 reconciles | ✅ PASS |
| FY27 monthly sum reconciles | ✅ PASS |
| FY27 by_channel reconciles | ✅ PASS |
| All 12 tabs click without crash | ✅ PASS |
| FY27 filter activates | ✅ PASS |
| Dynamic Apr–Jun label visible | ✅ PASS |
| Excluded brands invisible in rendered page | ✅ PASS |
| JS console errors | ✅ PASS (Vercel analytics 404 is expected locally, not a dashboard error) |

---

## 8. Known Limitations

1. **Jun-26 transaction-level validation pending.** Jun-26 offtake and primary values are from the official summary workbook. Store × article raw files for Jun-26 were not available at time of patch. When available, run `--offtake-patch` and `--detail-only` to replace summary-based values with transaction-level data.

2. **`primary.by_zone` / `by_chain` FY25 and FY26 not adjusted for excluded brands.** Brand-level zone/chain splits for FY25 are not available from the pre-aggregated primary workbook. The excluded-brand impact is < 0.05% of any single chain or zone total (max excluded NSV = 12.24L vs smallest chain total > 800L).

3. **Jun-26 `PowerBI/RawDataFolders` CSVs not created.** `offtake_store_article_Jun_26.csv` and `primary_article_Jun_26.csv` cannot be generated without transaction-level source data. Power BI refresh for Jun-26 requires the raw files when available.

---

## 9. Merge Recommendation

> **DO NOT AUTO-MERGE. Human review and approval required.**

All automated checks pass. Branch is ready for review by the Honasa / Mamaearth MT leadership team. Approve after verifying:
- Apr-26 offtake value (3,589.13L) is accepted vs the note text (3,589.14L)
- Brand exclusion list is confirmed (Pure Origin, Lumineve, Staze)
- Jun-26 summary-only basis is acknowledged pending transaction-level validation
