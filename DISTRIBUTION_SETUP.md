# Distribution & Automated Alerting Setup

Enable automatic notifications to Slack or Teams when Modern Trade snapshots are generated or when data validation fails.

---

## Slack Integration (Recommended)

### Step 1: Create a Slack Webhook

1. Go to your Slack workspace
2. Navigate to **Settings & Administration** → **Apps & Integrations** → **Manage** (or search "Incoming Webhooks")
3. Click **Create New Webhook** and select the channel (e.g., `#mt-operations` or `#data-alerts`)
4. Copy the webhook URL (looks like `https://hooks.slack.com/services/T...`)
5. Keep this URL safe — it's a secret key

### Step 2: Add Webhook to GitHub Secrets

1. Open [repository settings](https://github.com/aswalsheshant-cell/mt-dashboard/settings/secrets/actions)
2. Click **New repository secret**
3. Name: `SLACK_WEBHOOK_URL`
4. Value: Paste your Slack webhook URL
5. Click **Add secret**

### Step 3: Verify Integration

1. Modify and push the Excel template:
   ```bash
   git add MT_Primary_vs_Offtake_Analysis_Template.xlsx
   git commit -m "test: trigger MT PPT generation workflow"
   git push origin main
   ```

2. Check [GitHub Actions tab](https://github.com/aswalsheshant-cell/mt-dashboard/actions) for workflow execution
3. Once workflow succeeds, you should see a Slack message in your configured channel with:
   - ✅ Success status and artifact links
   - Direct links to PPTX, PDF, and PNG formats

### What Slack Notifications Include

**On Success:**
- ✅ Generation status
- 📥 Direct download links for PPTX (editable), PDF (print-ready), PNG (mobile)
- 🔗 Link to latest commit on GitHub

**On Failure:**
- ❌ Failure alert
- 📋 Error details (if validation failed, which cell/zone)
- 🔧 Link to workflow logs for diagnosis

---

## Teams Integration

For Microsoft Teams, use an **Incoming Webhook** connector:

1. In Teams, click **⋯** next to your channel → **Connectors**
2. Search for **Incoming Webhook** and configure
3. Give it a name (e.g., "MT Dashboard Bot")
4. Copy the webhook URL
5. Add to GitHub as `TEAMS_WEBHOOK_URL` (create a copy of the workflow step and replace `SLACK_WEBHOOK_URL` with `TEAMS_WEBHOOK_URL`)

Teams webhook format is JSON-compatible with the Slack format shown above.

---

## Advanced: Custom Notifications

You can customize the Slack message by editing `.github/workflows/generate_ppt.yml`:

### Show Extracted Metrics in Slack

Modify the success notification to include actual NSV and Gap values:

```bash
# Extract metrics from generated PNG or PPTX (advanced)
# Then embed them in the Slack message with emoji indicators
```

### Alert on High Gaps or Red Zones

Add a post-generation check:

```bash
# If gap > 5% (RED status):
# Post a red alert card highlighting the zone
```

---

## Email Distribution (Alternative)

If your organization prefers email:

1. Use GitHub Actions' built-in **Email** notification via status checks
2. Or integrate with a service like [Zapier](https://zapier.com) or [IFTTT](https://ifttt.com) to forward GitHub notifications as email

---

## Validation Failure Alerts

When data validation fails (e.g., missing primary NSV, corrupt Excel), the workflow:

1. ✋ Stops before generating PPT
2. 🔴 Posts a **failure alert** to Slack with the exact error message
3. 📝 Names the problematic cell (e.g., "Cell B7 contains invalid data: '[Enter Value]'")
4. 🔗 Links to the workflow logs for immediate troubleshooting

**MIS operator workflow:**
- Receive Slack alert: "Cell B7 is empty or invalid"
- Open Excel template
- Fix the cell (fill with actual number)
- Push updated file: `git push`
- Workflow re-triggers automatically
- Receive success notification with new PDF/PNG/PPTX

---

## Monitoring & Observability

### Weekly Health Check

Monitor these metrics to ensure the automation is working:

1. **Workflow execution count** — should match number of Excel pushes
2. **Success rate** — should be 95%+ after initial setup
3. **Slack message frequency** — every weekday if data is pushed daily
4. **CI/CD execution time** — typically 30-45 seconds end-to-end

### GitHub Actions Logs

Check workflow logs at:
```
https://github.com/aswalsheshant-cell/mt-dashboard/actions/workflows/generate_ppt.yml
```

Each run shows:
- ✅/❌ Test execution (31 tests)
- ✅/❌ Coverage report generation
- ✅/❌ PPT/PDF/PNG generation
- ✅/❌ Artifact commit and push

### Troubleshooting

**Workflow didn't trigger on Excel push:**
- Verify Excel file path matches `.github/workflows/generate_ppt.yml` trigger paths
- Check that file is in repository root (not in a subdirectory)

**Slack message not received:**
- Verify `SLACK_WEBHOOK_URL` secret is set (check Settings → Secrets)
- Confirm webhook channel still exists in Slack
- Check GitHub Actions logs for curl error messages

**Tests are failing in workflow but pass locally:**
- May be dependency issue in GitHub Actions environment
- Run `pytest test_generate_ppt.py -v` locally to replicate
- Check that all 31 tests pass locally before pushing

---

## Next Steps

1. ✅ Set up Slack webhook (or Teams alternative)
2. ✅ Add webhook URL to GitHub secrets
3. ✅ Test by pushing Excel file
4. ✅ Verify success notification arrives in Slack
5. ✅ Configure team to receive alerts daily or on-demand

---

**Last Updated:** 2026-09-04  
**Version:** 1.0  
**Maintained By:** Engineering & Operations Teams
