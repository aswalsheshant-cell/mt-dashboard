# Power BI PBIP Deployment Runbook

**Document Version:** 1.0  
**Last Updated:** 2026-09-05  
**Audience:** Analytics Engineers, Power BI Admins, IT Operations  
**Purpose:** Step-by-step procedure to assemble, validate, and publish PBIP to Power BI Service

---

## Executive Summary

This runbook covers:
1. **Desktop Assembly** — Assembling PBIP in Power BI Desktop (Windows only)
2. **Validation** — Data refresh, model checks, visual QA
3. **Publication** — Publishing to Power BI Service
4. **Monitoring** — Post-publication refresh schedule and alerts

**Timeline:** 2–3 days (Desktop assembly on Windows machine)

---

## Prerequisites

### System Requirements
- **OS:** Windows 10/11 (Power BI Desktop is Windows-only)
- **Power BI Desktop:** June 2025 or later
- **RAM:** 8 GB minimum
- **Disk:** 10 GB free (for PBIP + temp files)
- **Network:** Direct internet access (no proxy blocking Power BI Service)

### Access Requirements
- Power BI Service workspace admin access (workspace name: TBD — verify with IT)
- Read access to `/PowerBI/` directory with all 25 PQ queries and 14 DAX files
- Shared drive access to mount source data folders (if required by PQ queries)

### File Readiness Checklist
```
PowerBI/
├── QueryDefinitions/           [25 .pq files — locked]
├── MeasureDefinitions/         [14 .dax files — locked]
├── SeedData/                   [reference CSVs]
├── RawDataFolders/             [shared drive paths — configure per environment]
├── QuickSetup/                 [paste-in templates for quick assembly]
└── docs/
    ├── Desktop_Assembly_Checklist.md
    ├── AutomationScorecard.md
    └── QueryDataSource_Mapping.md
```

---

## Phase 1: Desktop Assembly (4 hours)

### Step 1.1: Prepare Windows Machine

```powershell
# On Windows machine with admin access

# 1. Install Power BI Desktop (if not present)
# Download from: https://www.microsoft.com/en-us/power-bi/desktop
# Latest version: June 2025+

# 2. Verify installation
# Open Power BI Desktop → File → About → Version should be >= June 2025

# 3. Optional: Enable data refresh from Power BI Desktop
# File → Options → Data Load → [check] Allow data refresh during load
```

### Step 1.2: Clone/Copy Project Files

```powershell
# Clone the project (or mount shared drive)
git clone https://github.com/aswalsheshant-cell/mt-dashboard.git
cd mt-dashboard/PowerBI

# Verify file structure
dir QueryDefinitions\      # Should contain 25 .pq files
dir MeasureDefinitions\    # Should contain 14 .dax files
dir SeedData\              # Should contain reference CSVs
```

### Step 1.3: Configure Data Sources

Before assembling, verify all data source paths are correct for your environment:

```powershell
# Read the mapping document
Get-Content docs\QueryDataSource_Mapping.md

# Expected output:
# Query Name               | Type    | Location (Path/Parameter)
# ─────────────────────────────────────────────────────
# dt_Primary              | Folder  | \\shared\raw\primary_fy24_26\
# dt_Offtake              | Folder  | \\shared\raw\offtake_monthly\
# dt_Universe             | Excel   | Z:\Universe_MT.xlsx
# dt_Promo                | Folder  | \\shared\raw\promos\
```

**Action:** Update shared drive paths if your environment differs (e.g., OneDrive, SharePoint).

### Step 1.4: Use Quick Setup Template (Recommended)

Power BI does NOT support automated PBIP generation from .pq/.dax files — you must 
assemble manually or use the **Quick Setup** template:

```powershell
# Option A: Use QuickSetup (Fastest)
# ─────────────────────────────────────
# 1. Open PowerBI\QuickSetup\PBIP_Template_MASTER.pbix
# 2. In Power Query Editor, paste each query from QueryDefinitions\ (25 steps)
# 3. In DAX measure tab, paste each measure from MeasureDefinitions\ (14 steps)
# 4. Skip to Step 1.5 (Refresh)

# Option B: Manual Assembly (Full Control)
# ──────────────────────────────────────────
# 1. New Blank Report → Save As → PBIP_Assembled_[Date].pbit (template format)
# 2. Model view → Manage Queries → Import all 25 .pq files
# 3. Measure definition → Add 14 DAX measures (copy from .dax files)
# 4. Proceed to Step 1.5
```

**Estimated time:** 1–2 hours (copy-paste 39 objects)

### Step 1.5: Data Refresh & Validation

```powershell
# Power BI Desktop → Home → Refresh (or Ctrl+R)
# Monitor for errors:

# Expected output (on console):
# ✓ Query "dt_Primary" loaded: 12,345 rows
# ✓ Query "dt_Offtake" loaded: 8,234 rows
# ✓ Query "dt_Universe" loaded: 426 rows
# ✓ Measure "Total_NSV_FY25" = ₹2,105 Cr
# ✓ Measure "Offtake_FY26" = ₹2,347 Cr
# ✓ Data refresh complete

# If errors occur:
# → Check Query Editor: Home → Edit Queries
# → Verify all data source paths (Step 1.3)
# → Test single query first (right-click → Refresh)
```

### Step 1.6: Visual QA & Model Validation

```powershell
# In Power BI Desktop:

# 1. Model view (top right)
#    - All tables visible?
#    - Relationships defined correctly? (no red X on relationships)
#    - Check table count: expect 5–7 main tables

# 2. Report view (create test page)
#    - Create a card visual: drag [Total_NSV_FY25] to Values
#    - Expected: ₹2,105 Cr (matches baseline in Finance_Approval_Decision_Log.md)
#    - Create another card: [Offtake_FY26]
#    - Expected: ₹2,347 Cr (or per Finance baseline)

# 3. Performance Analyzer (View → Performance Analyzer)
#    - Refresh all queries
#    - Check query durations:
#      * dt_Primary: <5 sec
#      * dt_Offtake: <5 sec
#      * All measures: <1 sec each
#    - If any query > 10 sec, flag for optimization

# 4. Data type validation
#    - Select each column → Data type should be Text/Number/Date (not "Any")
#    - Fixed all data types? → Proceed
```

### Step 1.7: Save & Export PBIP

```powershell
# Save the file as .pbix (Power BI interchange format, uploadable to Service)
# File → Save As → PBIP_Assembled_20260905.pbix
# Location: C:\Users\[YourName]\Documents\ (local)

# Or upload directly from Desktop:
# File → Publish → Select workspace → [Workspace name]
# Wait for upload (2–5 minutes)

# Alternative: Export to .pbit (template, for version control)
# File → Export → Save as PowerBI_PBIP_Template_20260905.pbit
# (Commit this to git repo in PowerBI/ folder)
```

---

## Phase 2: Power BI Service Publication (30 minutes)

### Step 2.1: Publish to Service

```powershell
# From Power BI Desktop:
# File → Publish → Select Workspace → Publish

# Or from Power BI Service web:
# 1. workspace.powerbi.com → [Workspace Name] → New → File Upload
# 2. Upload PBIP_Assembled_20260905.pbix
# 3. Wait for upload (2–5 minutes)

# Expected: "Dataset PBIP_Assembled_20260905 published successfully"
```

### Step 2.2: Configure Dataset Refresh Schedule

```powershell
# Power BI Service → Datasets → [Your Dataset] → Settings

# 1. Data source credentials
#    - Configure as needed (if queries reference shared drives or OneDrive)
#    - Test connection: [Test Connection]

# 2. Refresh schedule
#    - Enable scheduled refresh
#    - Frequency: Daily (default, or per business requirements)
#    - Time: 06:00 UTC (off-peak hours)
#    - Notifications: Email on refresh failure (add: analytics-ops@honasa.com)

# 3. Gateway (if using on-premises data)
#    - Configure Power BI Gateway (if required by IT)
#    - Ensure shared drive access is set up

# Save settings
```

### Step 2.3: Create Report on Published Dataset

```powershell
# Power BI Service → [Workspace] → [Dataset] → Create Report

# 1. Build test report pages:
#    - Page 1: KPI cards (Total_NSV_FY25, Offtake_FY26, etc.)
#    - Page 2: Sample chart (drill-down by chain/zone)
#    - Page 3: Data refresh log (shows last refresh time, success/fail)

# 2. Validate numbers match Desktop
#    - Total NSV FY25: ₹2,105 Cr ✓
#    - Total Offtake FY26: ₹2,347 Cr ✓

# 3. Share report with stakeholders
#    - Workspace → [Report] → Share → Users/Groups
#    - Or create app: Workspace → Create App
```

---

## Phase 3: Monitoring & Maintenance

### Step 3.1: Refresh Monitoring

```powershell
# Power BI Service → Datasets → [Your Dataset] → Refresh History

# Monitor:
# - Last Refresh: Should be recent (within 24 hours if daily schedule)
# - Status: ✓ Success or ✗ Failed
# - Duration: Should be consistent (<5 minutes typical)
# - On failure: Check error log → Diagnostic report

# Set up alert (if Power BI Premium):
# - Settings → Alerts → Add Alert on Refresh Failure
# - Notification to: analytics-ops@honasa.com
```

### Step 3.2: Query Performance Monitoring

```powershell
# Power BI Service → Capacity Metrics (Premium only, or Premium Trial)

# Monitor:
# - Query duration (P95 should be <5 seconds)
# - Refresh duration (should be consistent; spikes = data growth warning)
# - Memory usage (should be stable <1 GB)

# Action on spike:
# 1. Check if source data size increased
# 2. Review query complexity (Performance Analyzer in Desktop)
# 3. Consider query optimization or incremental refresh
```

### Step 3.3: Data Validation (Post-Refresh)

```powershell
# Weekly QC check (automated or manual):

# Test report (in Service) should show:
# ✓ Total NSV FY25 = ₹2,105 Cr (or per latest Finance baseline)
# ✓ Offtake FY26 = ₹2,347 Cr (or per latest)
# ✓ Store count (Universe) = 426 (should never change)
# ✓ Chain count = 8 (baseline check)

# If any metric deviates from baseline:
# → Check refresh status (failed refresh = stale data)
# → Verify source data hasn't changed unexpectedly
# → Review Finance Approval Decision Log (gaps GAP-01, GAP-02)
```

---

## Troubleshooting

### Error: "Cannot connect to data source"
```powershell
# 1. Verify shared drive is mounted
#    net use Z: \\shared\drive /persistent:yes

# 2. Test connection in Power Query Editor
#    Home → Manage Queries → Edit Queries → Select query → "Home → Refresh"
#    Watch for error message

# 3. If OneDrive/SharePoint:
#    - Verify your OneDrive is synced locally
#    - Check file permissions (you have read access)

# 4. If error persists:
#    - Contact IT: shared-drive-access@honasa.com
#    - Request access to \\shared\raw\primary_fy24_26\ (etc.)
```

### Error: "Refresh failed in Power BI Service"
```powershell
# 1. Check Power BI Gateway status (if using on-premises data)
#    Power BI Service → Settings → Gateway Status

# 2. Check dataset credentials
#    Datasets → [Your Dataset] → Settings → Data source credentials
#    Refresh/re-enter if expired

# 3. Check if source data folder is accessible from Service
#    (Service cloud can't directly access local/shared drives without Gateway)
#    → Configure Power BI Gateway (IT setup required)

# 4. If Gateway is not an option:
#    → Move source data to SharePoint/OneDrive (cloud accessible)
#    → Update Power Query connection paths
```

### Error: "Measure calculation returns NaN"
```powershell
# 1. Check DAX syntax in Measure Definition
#    Measure Editor → Diagnostics pane → check for errors

# 2. Common causes:
#    - Division by zero: use DIVIDE(numerator, denominator, 0) to default to 0
#    - BLANK() in aggregation: use SUMPRODUCT or CALCULATE with error handling

# 3. Test measure in Desktop first:
#    Home → Edit Queries → Data modeling → Measure pane → Create test card
#    If NaN in Desktop, fix DAX before publishing to Service
```

### Performance Issue: Refresh takes > 10 minutes
```powershell
# 1. Check query complexity
#    Performance Analyzer → Refresh → note slowest queries

# 2. Optimize in Power Query Editor:
#    - Remove unnecessary columns (Home → Remove Columns)
#    - Filter at source (not after merge)
#    - Avoid merged queries if possible

# 3. Consider incremental refresh (Advanced feature)
#    - Refresh only new/changed rows (reduces data volume)
#    - Setup in Desktop: Queries → Incremental Refresh → configure date range
```

---

## Rollback Procedure

If a published dataset causes issues:

```powershell
# 1. Remove current dataset from Service
#    Power BI Service → Datasets → [Bad Dataset] → Delete

# 2. Republish previous version from Desktop
#    File → Open → PBIP_Assembled_[PreviousDate].pbix
#    File → Publish → [Workspace]

# 3. Or recover from template (if committed to git)
#    git checkout PowerBI/PBIP_Template_[GoodVersion].pbit
#    Open in Desktop → Publish
```

---

## Sign-Off Checklist

Before considering deployment complete, verify:

- [ ] Desktop assembly completed without errors
- [ ] Data refresh successful (all queries loaded, all measures calculated)
- [ ] Baseline metrics verified (NSV FY25, Offtake FY26, etc.)
- [ ] Published to Power BI Service
- [ ] Refresh schedule configured (daily, off-peak)
- [ ] Alerts configured (on refresh failure)
- [ ] Test report created and validated
- [ ] Stakeholders have access
- [ ] First scheduled refresh completed successfully
- [ ] Documentation updated (this file, deployment log, etc.)

---

## Post-Deployment Support

**Issues after publication?**
- **Dataset won't refresh:** Check Power BI Gateway + data source credentials
- **Numbers don't match desktop:** Run full refresh (Ctrl+R in Desktop)
- **Performance slow:** Check query optimization, consider incremental refresh
- **Need to update measures:** Edit in Desktop → republish (overwrites Service dataset)

**Contact:**
- Power BI technical: bi-platform@honasa.com
- Data source issues: data-ops@honasa.com
- Access/permissions: it-helpdesk@honasa.com

---

**Document Version:** 1.0  
**Last Reviewed:** 2026-09-05  
**Next Review:** Upon next PBIP assembly or dataset change
