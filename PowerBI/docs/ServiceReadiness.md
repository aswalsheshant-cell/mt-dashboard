# Power BI Service — Readiness Checklist

**Status:** SERVICE READY FOR CONFIGURATION (pending PBIX Desktop assembly and local validation)

---

## Requirements to Publish

### 1. PBIX File

The `MT_Automated_Performance_Dashboard_FY27.pbix` must be:
- Fully assembled in Power BI Desktop (see `PBIX_Build_Guide.md`)
- Refreshed successfully at least once locally
- Reconciliation confirmed (variance = 0)
- Governance banners tested
- All report pages built and reviewed

### 2. Power BI License

| Requirement | Details |
|-------------|---------|
| Publisher account | Requires Power BI Pro or Premium Per User (PPU) licence |
| Viewer accounts | Pro / PPU for workspace sharing; Premium capacity for free-viewer sharing |
| Workspace tier | At least a **shared** workspace; **Premium** if >1 GB dataset or embedding required |

### 3. Data Gateway

Because data files are stored locally on the machine running the refresh, an
**On-Premises Data Gateway** (standard mode) is required.

| Field | Value |
|-------|-------|
| **Gateway machine** | *(confirm: the Windows machine holding the PowerBI/ folder)* |
| **Gateway owner** | *(confirm: named IT/Analytics contact)* |
| **Gateway name** | *(e.g. MT-Dashboard-Gateway)* |
| **Data source type** | File — Folder |
| **Data source path** | The absolute path of `PowerBI/RawDataFolders/` on the gateway machine |
| **Credentials** | Windows service account with read access to all `RawDataFolders/` subfolders |

**Alternative (no gateway):** Upload all source files to a SharePoint/OneDrive folder and
reconfigure the `pRootFolder` parameter to point to the SharePoint URL.
Power BI natively connects to SharePoint folders without a gateway.

### 4. Scheduled Refresh Configuration

| Setting | Recommended value |
|---------|------------------|
| Refresh frequency | Daily (or on-demand after each monthly file drop) |
| Refresh window | Off-peak hours, e.g. 02:00–04:00 IST |
| Max refresh retries | 3 |
| Failure notification | Email to MT Analytics owner |
| Keep history | 10 refreshes (default) |

### 5. Workspace and Access

| Role | Permission | Who |
|------|------------|-----|
| Publishing owner | Workspace Admin | *(confirm)* |
| Report editors | Workspace Member or Contributor | MT Analytics team |
| Read-only consumers | Workspace Viewer or App audience | MT Leadership, Finance |
| Row-Level Security | Implement if regional/zone-specific views required | MT Analytics |

### 6. Failure Notification Recipients

| Name | Email | Condition |
|------|-------|-----------|
| *(MT Analytics lead)* | *(email)* | Any refresh failure |
| *(Finance owner)* | *(email)* | Refresh failure on Jun'26 / Provisional rows |

---

## Publish Steps (after Desktop validation)

1. Open `MT_Automated_Performance_Dashboard_FY27.pbix` in Power BI Desktop
2. Home tab → **Publish** → select the target workspace
3. In the Service: Dataset → **Settings** → Data source credentials → configure Gateway
4. Dataset → **Settings** → Scheduled refresh → set the schedule
5. Run **Refresh now** once manually and confirm success in Refresh history
6. Workspace → **Create app** (optional) for a curated app view for leadership

---

## Row-Level Security (RLS) — If Required

If zone-specific or team-specific views are needed:

1. In Power BI Desktop: Modeling → **Manage roles** → define roles
   (e.g. `Zone_North`, `Zone_South`) with filters on `Zone State Master[Zone]`
2. Assign users to roles in the Service: Dataset → **Security**
3. Test with "View as role" in Desktop before publishing

Current model does not have RLS configured. Implement only when requested.

---

## Service Configuration Blockers

| Blocker | Status |
|---------|--------|
| PBIX not yet assembled | **Blocks publish** |
| Windows machine / gateway identity not confirmed | **Blocks scheduled refresh** |
| Power BI Pro/PPU licences not confirmed | **Blocks shared workspace** |
| Workspace name not confirmed | **Blocks publish target** |

**Until these blockers are resolved:** `SERVICE READY FOR CONFIGURATION`

**After successful Service refresh:** `SERVICE AUTOMATION COMPLETE`
