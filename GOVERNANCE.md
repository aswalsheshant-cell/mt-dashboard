# MT Deck Generator — Production Governance & Operations

**Status:** Feature complete, ready for production transition
**Branch:** `claude/proactive-intelligence-engine-skill-jldjlg`
**Tests:** 32/32 passing
**Deployment Model:** Cloud-native automation (GitHub Actions → Google Slides API)

---

## Phase Transition Map: Development → Governance → Automation

| Phase | Horizon | Priority | Action Item | Success Milestone |
|-------|---------|----------|-------------|------------------|
| **0. Validation** | ✅ Immediate | P0 | PR review + merge to main | All tests pass + CI green |
| **1. Cloud Setup** | ✅ Immediate | P0 | Configure GCP credentials in GitHub Secrets | Live smoke test passes |
| **2. Data Integration** | 📋 Near-term | P1 | Replace DEFAULT_CONFIG with live DB/DMS feed | Deck consumes real metrics |
| **3. Automation** | 📋 Near-term | P1 | Enable scheduled GitHub Actions workflow | Monthly deck auto-published Day 1 |
| **4. Distribution** | 🔮 Future | P2 | Add Slack/Teams webhook for stakeholder alerts | Execs receive link automatically |

---

## Phase 0: Validation & Code Review (Immediate)

### Checklist

- [ ] **Code Quality**
  - [ ] Syntax: `python -m py_compile scripts/*.py`
  - [ ] Tests: `pytest scripts/test_*.py` (32/32 passing)
  - [ ] No hardcoded credentials or secrets in code

- [ ] **Integration Validation**
  - [ ] Dual-export works: `python build_mt_monthly_ppt.py --format both`
  - [ ] Generated files created without errors
  - [ ] PPTX opens and renders all 18 slides
  - [ ] JSON payload is valid (parseable, contains 251+ requests)

- [ ] **PR Gate**
  - [ ] Branch rebased on latest main
  - [ ] PR description includes test results
  - [ ] No merge conflicts
  - [ ] Reviewers: MT Trade Ops Lead + Engineering Lead

### PR Merge Strategy

- **Squash merge** to keep history clean
- **Retain commit message** with full Phase 1/2/3 summary
- **Tag version** (e.g., `v1.0.0-mt-deck`) for release tracking

---

## Phase 1: Cloud Credential Setup (Immediate)

### Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create project: `MT-Dashboard-Prod`
3. Enable APIs:
   - Google Slides API
   - Google Drive API
   - (Optional) Google Sheets API for future data connector

### Step 2: Service Account Setup (Recommended for CI/CD)

1. **Create service account:**
   - IAM & Admin → Service Accounts → Create Service Account
   - Name: `mt-deck-generator`
   - Role: `Editor` (for Slides + Drive)

2. **Create key:**
   - Click service account → Keys → Add Key → Create new key → JSON
   - Download and secure locally

3. **Add to GitHub Secrets:**
   - Repository Settings → Secrets and variables → Actions
   - Secret name: `GCP_SERVICE_ACCOUNT_KEY`
   - Value: Paste entire JSON file contents

### Step 3: Share Google Drive Folder (Organization)

Grant the service account write access to your MT reporting folder:

```bash
# Get service account email from JSON key
SERVICE_ACCOUNT_EMAIL=$(cat ~/Downloads/key.json | jq -r '.client_email')

# Share Drive folder (via Google Drive UI or API)
# Set "Viewer" or "Editor" permissions for $SERVICE_ACCOUNT_EMAIL
```

### Step 4: Smoke Test

```bash
# Dry-run deployment (validates credentials without creating presentation)
python scripts/deploy_to_google_slides.py \
  --json-file MT_september2026_gslides_batch.json \
  --dry-run

# Live smoke test (creates test presentation)
python scripts/deploy_to_google_slides.py \
  --json-file MT_september2026_gslides_batch.json \
  --title "MT Sep 2026 - Smoke Test"
```

**Validation:**
- ✅ Presentation created in Google Drive
- ✅ All 18 slides rendered
- ✅ Waterfall, matrix, tables visible
- ✅ Colors and fonts match theme

---

## Phase 2: Data Integration (Near-term)

### Current State
- **Source:** `DEFAULT_CONFIG` dict in `build_mt_monthly_ppt.py` (hardcoded mock data)
- **Problem:** Not connected to live metrics; requires manual updates monthly

### Target State
- **Source:** Direct query to MT data warehouse (Snowflake, BigQuery, Postgres, or monthly CSV export)
- **Automation:** Data refreshed automatically when metrics close

### Implementation Pattern

Create `mt_data_loader.py`:

```python
def load_mt_metrics(month: str, year: int, source: str = "default"):
    """
    Load metrics from various sources.
    
    Args:
        month: Month name (e.g., "september")
        year: Fiscal year (e.g., 2026)
        source: Data source ("default", "snowflake", "s3", "gsheet", "dms")
    
    Returns:
        Dict matching DEFAULT_CONFIG schema
    """
    if source == "default":
        return DEFAULT_CONFIG.copy()
    elif source == "snowflake":
        return load_from_snowflake(month, year)
    elif source == "s3":
        return load_from_s3(month, year)
    elif source == "gsheet":
        return load_from_google_sheets(month, year)
    elif source == "dms":
        return load_from_dms_export(month, year)
    else:
        raise ValueError(f"Unknown source: {source}")
```

Then update CLI:

```bash
python build_mt_monthly_ppt.py \
  --month september \
  --year 2026 \
  --data-source snowflake \
  --format both
```

### Typical Integration Points

| Data Category | Typical Source | Refresh Frequency |
|---------------|-------------------|---|
| Zone offtake / conversion | ERP / SAP → CSV export | Daily |
| Primary sales | DMS / Salesforce | Daily |
| Market share / competitors | Nielsen / Retailer feedback | Monthly |
| Scenario parameters | Manual input (Trade Team) | Per-promo |

---

## Phase 3: Scheduled Automation (Near-term)

### What's Already Configured

GitHub Actions workflow at `.github/workflows/monthly_mt_deck.yml` includes:

- **Scheduled trigger:** 1st of every month at 04:00 UTC (09:30 AM IST)
- **Test gate:** Runs all 32 unit tests before generating deck
- **Dual export:** Generates PPTX + JSON automatically
- **Live deployment:** Publishes to Google Slides if credentials present
- **Artifact storage:** Archives all outputs for 90 days

### Activation Steps

1. **Merge PR** into main (Phase 0 complete)

2. **Configure GitHub Secrets:**
   - Add `GCP_SERVICE_ACCOUNT_KEY` (from Phase 1)
   - (Optional) Add `MT_DECK_STAKEHOLDER_EMAILS` for auto-sharing

3. **Verify workflow triggers:**
   ```bash
   # List workflows
   git show origin/main:.github/workflows/monthly_mt_deck.yml
   ```

4. **Test manual dispatch** (from GitHub Actions UI):
   - Repository → Actions → "Modern Trade Monthly Deck Pipeline"
   - Click "Run workflow"
   - Select month/year/format
   - Execute

5. **Validate first automated run** (wait for 1st of next month at 04:00 UTC)
   - Check GitHub Actions logs
   - Verify artifacts uploaded
   - Verify presentation in Google Drive

### Workflow Behavior

| Trigger | Behavior |
|---------|----------|
| **Schedule (1st of month)** | Auto-generates previous month's deck; publishes to Slides |
| **Manual dispatch** | Generates specified month/year; respects format/deployment options |
| **Pull request** | (Currently none; can add test validation if needed) |

---

## Phase 4: Distribution & Alerts (Future)

### Slack Integration (Example)

Post deck link to leadership channel automatically:

```bash
# After deployment, extract presentation URL
DECK_URL="https://docs.google.com/presentation/d/ABC...XYZ/edit"

# Post to Slack
curl -X POST https://hooks.slack.com/services/YOUR/WEBHOOK/URL \
  -d @- <<EOF
{
  "channel": "#mt-leadership",
  "text": "📊 MT Leadership Review - September 2026 ready",
  "attachments": [
    {
      "color": "good",
      "title": "View Deck",
      "title_link": "$DECK_URL",
      "text": "18 slides | Waterfall diagnostic | Risk matrix | Scenario ROI"
    }
  ]
}
EOF
```

Integrate via GitHub Actions:
- Add Slack webhook secret to GitHub
- Post message after successful deployment

### Email Notification (Example)

```bash
# Send deck link via email after deployment
echo "Hi Leadership,

Your monthly MT review deck is ready: $DECK_URL

18 slides covering:
- Executive summary & KPIs
- Zone diagnostics & risk matrix
- Scenario analysis & execution roadmap
- Action register (live accountability tracker)

Slides: $(echo "MT_september2026_gslides_batch.json" | jq '.requests | length') API operations
Generated: $(date)

Open to review and edit.

Best,
MT Data Team" | mail -s "MT Sep 2026 Leadership Deck Ready" "$MT_STAKEHOLDER_EMAILS"
```

---

## Operational Runbook

### Monthly Deck Lifecycle

```
Day 1 (Month Close):
  04:00 UTC → GitHub Actions triggers automated pipeline
  ├─ Pulls latest metrics from data source
  ├─ Generates PPTX + JSON
  ├─ Runs all 32 tests
  ├─ Publishes to Google Slides
  ├─ Posts Slack notification → #mt-leadership
  └─ Archives artifacts (90-day retention)

Day 1–2 (Leadership Review):
  Execs access live Google Slides deck
  ├─ Edit annotations (no version control needed)
  ├─ Share with board
  └─ Copy to email if offline access needed

End of Month:
  Archive PPTX locally if needed; JSON expires after 90 days
```

### Troubleshooting

| Issue | Check | Fix |
|-------|-------|-----|
| Workflow doesn't run on schedule | GitHub Actions enabled? | Enable in Settings → Actions |
| Credentials error during deploy | `GCP_SERVICE_ACCOUNT_KEY` secret exists? | Add secret with full JSON |
| Deck publishes but slides blank | Wait 30 seconds? | Refresh browser; check batchUpdate request count |
| Data out of date | Last metric refresh timestamp? | Verify data source connection; update `mt_data_loader.py` |

---

## Success Metrics & Monitoring

| Metric | Target | Check Weekly |
|--------|--------|---|
| **Workflow execution success rate** | >95% | GitHub Actions logs |
| **Deck deployment time** | <60 seconds | Workflow run duration |
| **All tests passing** | 32/32 | Workflow test step output |
| **Presentation rendered** | 100% slides visible | Manual open + inspect |
| **Stakeholder access** | All intended viewers can open | Share emails working |

---

## Rollback & Incident Response

### If Workflow Fails

1. **Check logs:** GitHub Actions → Workflow run → Review step output
2. **Isolate issue:**
   - Test locally: `python build_mt_monthly_ppt.py --format both`
   - Test deploy: `python deploy_to_google_slides.py --json-file <file> --dry-run`
3. **Fix in-branch:**
   - Commit fix to `claude/proactive-intelligence-engine-skill-jldjlg`
   - Manually trigger workflow dispatch
   - Validate
4. **Merge fix:** Create amendment PR or include in main PR

### If Deployed Deck Is Incorrect

1. **Create new presentation:** Manually run deploy script with updated data
2. **Archive broken version:** Move to "Archive" folder in Google Drive
3. **Share corrected link:** Post updated link to Slack + email
4. **RCA:** Review data source; update pipeline if needed

---

## Documentation & Onboarding

### For MT Trade Ops

- ✅ E2E_WORKFLOW.md: "Quick Start" and "Example Workflows"
- 📄 Provide link to live Google Slides deck each month
- 📧 Email template for sharing with extended team

### For Engineers

- ✅ Code comments in `build_mt_monthly_ppt.py`, `mt_analytics_engine.py`
- ✅ Test suites in `test_gslides_export.py`, `test_analytics_engine.py`
- ✅ Workflow YAML with inline documentation
- 🔧 This GOVERNANCE.md for operational procedures

### For Leadership

- 📊 Monthly deck URL (via Slack/email)
- 📝 One-pager: "What's new this month?" (included in deck)
- 🎯 Action Register (Slide 14) for accountability tracking

---

## Questions & Support

| Audience | Question | Resource |
|----------|----------|----------|
| **Trade Ops** | "How do I generate a deck?" | E2E_WORKFLOW.md → "Quick Start" |
| **Engineer** | "How does the math work?" | `mt_analytics_engine.py` + test suite |
| **Leadership** | "What's in the deck?" | Slide 2 (TOC) + Slide 14 (Action Register) |
| **DevOps** | "How do I debug the workflow?" | `.github/workflows/monthly_mt_deck.yml` + GitHub Actions logs |

---

**Last Updated:** September 5, 2026  
**Maintained By:** MT Data Team  
**Review Cadence:** Quarterly
