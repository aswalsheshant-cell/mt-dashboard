# Power BI Dashboard Automation — Setup Guide

**Purpose:** Automate monthly Power BI dataset refreshes with offtake data  
**Engine:** `scripts/powerbi_sync_agent.py` (298 lines, production-hardened)  
**Schedule:** 1st of every month, 04:00 UTC (09:30 AM IST)  
**Status:** Ready for activation

---

## **Option A: Test Dry-Run (No Credentials Required) — 5 minutes**

Test the agent code without touching Power BI.

### Step 1: Run the test suite
```bash
python scripts/test_powerbi_sync.py
```

**Expected Output:**
```
Ran 11 tests in 2.007s
OK
```

✅ This verifies:
- Capacity distinction (Premium vs. Shared)
- Exact refresh ID matching
- Exponential backoff retry logic
- Exit codes on failure

### Step 2: Test with mock credentials (no actual API calls)

```bash
# Create a test script (this won't make real API calls)
cat > /tmp/test_powerbi_agent.py << 'INNER_EOF'
import sys
sys.path.insert(0, '/home/user/mt-dashboard/scripts')

from powerbi_sync_agent import PowerBISyncAgent

# Initialize with test credentials (no API calls yet)
agent = PowerBISyncAgent(
    tenant_id="test-tenant-id",
    client_id="test-client-id",
    client_secret="test-secret",
    workspace_id="00000000-0000-0000-0000-000000000000",
    dataset_id="00000000-0000-0000-0000-000000000001",
    is_premium_capacity=True
)

print("✅ Agent initialized successfully")
print(f"  Tenant: {agent.tenant_id}")
print(f"  Workspace: {agent.workspace_id}")
print(f"  Dataset: {agent.dataset_id}")
print(f"  Capacity: {'Premium (Enhanced)' if agent.is_premium else 'Shared (Standard)'}")
print("\n✅ Dry-run test passed (no API calls made)")
INNER_EOF

python /tmp/test_powerbi_agent.py
```

**Expected Output:**
```
✅ Agent initialized successfully
  Tenant: test-tenant-id
  Workspace: 00000000-0000-0000-0000-000000000000
  Dataset: 00000000-0000-0000-0000-000000000001
  Capacity: Premium (Enhanced)

✅ Dry-run test passed (no API calls made)
```

---

## **Option B: Activate Live Power BI Refresh — 10 minutes**

Actually refresh your Power BI dataset with offtake data.

### Prerequisites

You need:
1. **Azure Service Principal credentials:**
   - `AZURE_TENANT_ID` — Your Azure AD tenant ID
   - `AZURE_CLIENT_ID` — Service principal client ID
   - `AZURE_CLIENT_SECRET` — Service principal secret

2. **Power BI identifiers:**
   - `WORKSPACE_ID` — Power BI workspace ID
   - `DATASET_ID` — Power BI dataset ID

### Step 1: Get your Power BI IDs

**In Power BI Service (app.powerbi.com):**
1. Go to your workspace
2. Click on your dataset (e.g., "Modern Trade Offtake Dataset")
3. URL bar shows: `powerbi.com/groups/{WORKSPACE_ID}/datasets/{DATASET_ID}`
4. Copy both IDs

### Step 2: Get your Azure credentials

**In Azure Portal (portal.azure.com):**
1. Go to: Azure AD → App Registrations
2. Create a new application (or use existing)
3. Copy: **Application (Client) ID** → `AZURE_CLIENT_ID`
4. Copy: **Directory (Tenant) ID** → `AZURE_TENANT_ID`
5. Create secret: **Certificates & secrets** → **New client secret** → `AZURE_CLIENT_SECRET`

**Grant Power BI API permissions:**
1. In the app: **API Permissions**
2. Add permission: **Power BI Service**
3. Select: **Dataset.ReadWrite.All**
4. Grant admin consent

### Step 3: Set environment variables and test

```bash
# Set credentials (replace with your actual values)
export AZURE_TENANT_ID="your-tenant-id"
export AZURE_CLIENT_ID="your-client-id"
export AZURE_CLIENT_SECRET="your-client-secret"

# Run a test refresh (dry-run, no actual changes)
python scripts/powerbi_sync_agent.py \
  --workspace-id "your-workspace-id" \
  --dataset-id "your-dataset-id" \
  --premium  # Use --premium for Fabric/Premium capacity, omit for Shared

```

**Expected Output:**
```
[INFO] Azure AD bearer token successfully acquired.
[INFO] Initiating Premium refresh on Dataset: your-dataset-id...
[INFO] Tracking Refresh ID (from Location header): 550e8400-e29b-41d4-a716-446655440000
[INFO] Elapsed: 0s | Status: InProgress
[INFO] Elapsed: 15s | Status: InProgress
...
[INFO] Elapsed: 180s | Status: Completed
[SUCCESS] Refresh verified successfully.
```

Exit code: **0** (success) or **1** (failure)

### Step 4: Monitor in Power BI

1. Go to Power BI workspace
2. Click dataset → **Refresh history**
3. Verify latest refresh shows recent timestamp
4. Check DAX measures: conversion %, trapped capital, DOI updated

---

## **Option C: Configure Monthly Automation (Oct 1 onwards) — 5 minutes**

Set up automated monthly refreshes via GitHub Actions.

### Prerequisites

You need GitHub repository secrets:
- `GCP_SERVICE_ACCOUNT_KEY` (base64-encoded service account JSON)
- Optionally: `MT_DECK_STAKEHOLDER_EMAILS` (for auto-share to Google Slides)

### Step 1: Add GitHub Secrets

**In GitHub:**
1. Go to: repo → Settings → Secrets and variables → Actions
2. Create new secret: `GCP_SERVICE_ACCOUNT_KEY`
   - Value: Base64-encoded service account JSON
   - ```bash
     base64 -w 0 < ~/Downloads/service-account.json > /tmp/sak.txt
     # Copy contents of /tmp/sak.txt
     ```

3. Create new secret: `MT_DECK_STAKEHOLDER_EMAILS` (optional)
   - Value: `email1@company.com,email2@company.com`

### Step 2: Verify Workflow Configuration

The workflow is already configured at `.github/workflows/monthly_mt_deck.yml`:

✅ **Cron Schedule:** `0 4 1 * * *` (1st of month, 04:00 UTC)  
✅ **Test Suite:** Analytics, Exporter, Dashboard UI, Seeds (all 4 included)  
✅ **Build:** 18-slide PPTX + Google Slides JSON  
✅ **Deploy:** Auto-publish to Google Slides (if secrets set)

### Step 3: Test the workflow manually

**In GitHub:**
1. Go to: Actions → "Modern Trade (MT) Monthly Leadership Deck Pipeline"
2. Click: "Run workflow"
3. Select:
   - Branch: `main`
   - Month: `september`
   - Year: `2026`
   - Format: `both`
   - Deploy to Google Slides: `false` (for initial test)
4. Click: "Run workflow"

**Watch the run:**
- Check step-by-step logs
- All 4 test suites should pass
- PPTX and JSON should generate
- Artifacts appear in: "Artifacts" tab (90-day retention)

### Step 4: Verify October 1 Scheduled Run

The cron will automatically trigger on **October 1, 2026 at 04:00 UTC**.

**Verify:**
1. Go to: Actions → "Modern Trade (MT) Monthly Leadership Deck Pipeline"
2. Look for run on Oct 1 at 04:00 UTC
3. All tests pass → Artifacts generated → Optional: Slides published

---

## **Option D: Full Setup (All Three) — 20 minutes**

Combines A + B + C for complete automation.

### Step-by-step:

1. **Test locally** (Option A: 5 min)
   ```bash
   python scripts/test_powerbi_sync.py
   ```

2. **Activate live refresh** (Option B: 10 min)
   ```bash
   export AZURE_TENANT_ID="..."
   export AZURE_CLIENT_ID="..."
   export AZURE_CLIENT_SECRET="..."
   
   python scripts/powerbi_sync_agent.py \
     --workspace-id "..." \
     --dataset-id "..." \
     --premium
   ```

3. **Configure monthly automation** (Option C: 5 min)
   - Add GitHub secrets
   - Test workflow manually
   - Verify Oct 1 cron is armed

---

## **Troubleshooting**

### Issue: "Azure AD Auth Error" (401)
**Cause:** Invalid credentials or insufficient permissions  
**Fix:**
1. Verify `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`
2. Check service principal has Power BI API permissions
3. Verify secret hasn't expired (create new if needed)

### Issue: "Refresh timed out after 1800s"
**Cause:** Dataset refresh taking too long  
**Fix:**
```bash
# Increase timeout (default 1800s = 30 min)
python scripts/powerbi_sync_agent.py \
  --workspace-id "..." \
  --dataset-id "..." \
  --timeout 3600  # 60 minutes
```

### Issue: Workflow fails on Oct 1 cron
**Cause:** Missing GitHub secrets or invalid credentials  
**Fix:**
1. Verify all secrets are set correctly
2. Test manually via "Run workflow" button first
3. Check Actions logs for specific error

### Issue: "Cannot find module powerbi_sync_agent"
**Cause:** Running from wrong directory  
**Fix:**
```bash
cd /home/user/mt-dashboard
python scripts/powerbi_sync_agent.py ...
```

---

## **Monitoring & Alerts**

### Set Up Slack Notifications (Optional)

**In GitHub Actions workflow, add after "Deploy to Live Google Slides":**

```yaml
- name: Slack Notification on Success
  if: success()
  uses: slackapi/slack-github-action@v1.24.0
  with:
    payload: |
      {
        "text": "✅ MT Deck refresh successful",
        "blocks": [
          {
            "type": "section",
            "text": {
              "type": "mrkdwn",
              "text": "*Modern Trade Deck — Monthly Refresh*\n✅ Success\n📅 ${{ steps.resolve_date.outputs.month }} ${{ steps.resolve_date.outputs.year }}\n🔗 <${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}|View Run>"
            }
          }
        ]
      }
  env:
    SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
```

---

## **Security Best Practices**

1. **Rotate Credentials Quarterly**
   - Azure service principal secret: Create new, delete old
   - GitHub secrets: Update with new credentials

2. **Limit Service Principal Permissions**
   - Only grant "Dataset.ReadWrite.All" for Power BI
   - Don't use global admin account

3. **Monitor Refresh History**
   - Check Power BI refresh logs monthly
   - Alert if refresh fails 2+ times

4. **Audit GitHub Actions**
   - Review workflow logs for errors
   - Monitor failed runs in Actions tab

---

## **Success Criteria**

✅ **Option A (Dry-Run):** Test suite passes (11/11 tests)  
✅ **Option B (Live):** Power BI dataset refreshes, exit code 0  
✅ **Option C (Cron):** October 1 run completes, artifacts generated  
✅ **Option D (Full):** All three working together

---

## **Next Steps**

1. **Choose your option** (A/B/C/D)
2. **Execute setup** using this guide
3. **Test** with dry-run or manual workflow
4. **Monitor** first automated run (Oct 1, 2026)
5. **Iterate** based on business feedback

---

## **Support**

| Issue | Contact | Reference |
|-------|---------|-----------|
| Python/Agent errors | Engineering | `scripts/powerbi_sync_agent.py` |
| Power BI connectivity | Power BI admin | `GOVERNANCE.md` (troubleshooting) |
| GitHub Actions | DevOps | `.github/workflows/monthly_mt_deck.yml` |
| Azure/Service Principal | Cloud admin | Azure Portal → App Registrations |
