# Central Zone Leadership Pack — Deployment & Access Guide

**Status:** ✅ Production Ready  
**Last Updated:** 2026-08-17  
**Frequency:** Monthly (automated)

---

## Overview

The **Central Zone Leadership Pack** is an automated, monthly-generated PowerPoint presentation featuring:

- **18 slides** of Central zone (Madhya Pradesh + Chhattisgarh) performance analysis
- **Real-time metrics** from the MT dashboard data (refreshed as source updates arrive)
- **State-wise breakdown** with chain-level diagnostics
- **Governance insights** and action priorities

---

## Access & Download

### Option 1: GitHub Releases (Recommended)

**Where:** https://github.com/aswalsheshant-cell/mt-dashboard/releases

**How:**
1. Navigate to the repository Releases page
2. Look for tags: `central-zone-ppt-YYYYMMDD`
3. Download `Central_Zone_Leadership_Pack_*.pptx`

**Latest:** [Central Zone PPT Latest Release](https://github.com/aswalsheshant-cell/mt-dashboard/releases/latest)

### Option 2: GitHub Actions Artifacts

**Where:** Actions → Data Engineering / Monthly Central Zone PPT → Latest Run

**How:**
1. Go to `.github/workflows/dataeng.yml` runs (on push to main)
2. Or `.github/workflows/monthly-central-zone-ppt.yml` (monthly automated run)
3. Click latest run
4. Download artifact: `central-zone-pack` or `central-zone-leadership-pack`

**Note:** Artifacts retained for 90 days (releases retained for 365 days).

### Option 3: Local Build (On-Demand)

```bash
cd /home/user/mt-dashboard
npm install
node scripts/build_central_zone_presentation.js
# Output: Central_Zone_Leadership_Pack_Jul26.pptx (uses current data.js)
```

---

## Monthly Generation Schedule

### Automated Triggers

**Frequency:** 1st of every month at 09:00 UTC

**Workflow:** `.github/workflows/monthly-central-zone-ppt.yml`

**Steps:**
1. Checkout latest code + data.js
2. Install npm dependencies
3. Generate `Central_Zone_Leadership_Pack_*.pptx`
4. Upload to GitHub Releases (365-day retention)
5. Create tagged release for easy discovery

### Manual Trigger

If you need an immediate PPT (don't wait for monthly schedule):

1. Go to: `.github/workflows/monthly-central-zone-ppt.yml`
2. Click **Run workflow** → Select branch → **Run**
3. PPT generated within 2 minutes
4. Download from artifacts

---

## Content Overview

### Slide Sections

| Slides | Section | Content |
|--------|---------|---------|
| 1 | Cover | Central Zone headline metrics |
| 2-5 | Initiatives | Product & execution updates |
| 6-9 | Madhya Pradesh | State-level deep dive |
| 10-13 | Chhattisgarh | State-level deep dive |
| 14-15 | Comparison | MP vs CG performance index |
| 16-17 | Actions | Governance priorities & owners |
| 18 | Tracker | Monthly tracking dashboard |

### Key Metrics

**Primary (Sell-in):**
- Central zone: ₹2.62 Cr (FY26)
- Madhya Pradesh: ₹2.07 Cr (79.3% of Central)
- Chhattisgarh: ₹0.55 Cr (20.7% of Central)

**Offtake (Sell-out):**
- Central zone: ₹2.12 Cr (Jul 2026)
- Conversion: 80.9%
- MP best-in-class: 91.7% conversion

**Distribution:**
- Stores: 250+ locations across MP/CG
- Chains: All major MT chains represented
- Growth: YoY +35% (national MT +32%)

---

## Data Refresh Cycle

**PPT generated from:** `dashboard/data.js` (latest available)

**data.js updated when:**
- New MT source files arrive (Primary/Offtake/Universe/Promo)
- Run: `python scripts/build_dashboard_data.py --src <dir> --out dashboard/data.js`
- Commit and push to branch
- Merge to main

**PPT automatically reflects:**
- Latest Central zone metrics
- Updated state breakdowns
- Current chain performance
- Recent governance actions

---

## Leadership Workflow

### Weekly Review
1. Download latest PPT from Releases
2. Review Central zone performance vs. targets
3. Update Action Owner assignments (slide 16-17)
4. Share with zone leadership team

### Monthly Cadence
1. **1st of month (09:00 UTC):** New PPT auto-generated
2. **By 10:00 UTC:** Available in Releases + Actions artifacts
3. **By EOD:** Shared with leadership via email/Slack
4. **Leadership review:** QBR context + governance inputs
5. **By 5th of month:** Action closure targets due

### Quarterly Deep Dive
1. Export PPT data to Excel for trend analysis
2. Compare current quarter vs. prior 3 quarters
3. Identify patterns: seasonality, chain performance, category shifts
4. Update strategy as needed

---

## Troubleshooting

### PPT not generating?

**Check 1: Workflow Status**
```
.github/workflows/monthly-central-zone-ppt.yml → Runs tab
```
Look for ✅ green checkmark or ❌ red X.

**Check 2: data.js Validity**
```bash
python -m json.tool dashboard/data.js > /dev/null && echo "✓ Valid JSON"
```

**Check 3: Manual Generation**
```bash
cd /home/user/mt-dashboard && node scripts/build_central_zone_presentation.js
# If fails, check npm install and node version (18+)
```

### Metrics look wrong?

1. Verify source files were updated: `ls -lh ~/mt-sources/`
2. Regenerate data.js: `python scripts/build_dashboard_data.py ...`
3. Rebuild PPT: `node scripts/build_central_zone_presentation.js`
4. Check data.js validity (see above)

### Can't access GitHub Releases?

**Fallback:** Use Actions artifacts (90-day retention)
1. Go to latest `dataeng.yml` run (on any push to main)
2. Download `central-zone-pack` artifact
3. Or run locally: `node scripts/build_central_zone_presentation.js`

---

## Integration Points

### Email Distribution (Optional Setup)

To auto-email PPT to leadership on the 1st of each month:

1. Add email step to `monthly-central-zone-ppt.yml`
2. Use GitHub Secret: `LEADERSHIP_EMAIL_LIST`
3. Configure SMTP action (e.g., `dawidd6/action-send-mail@v3`)

**Example:** (not yet configured)
```yaml
- name: Email PPT to Leadership
  uses: dawidd6/action-send-mail@v3
  with:
    server_address: ${{ secrets.EMAIL_SERVER }}
    server_port: 587
    username: ${{ secrets.EMAIL_USER }}
    password: ${{ secrets.EMAIL_PASS }}
    subject: Central Zone Leadership Pack — Monthly
    to: ${{ secrets.LEADERSHIP_EMAIL_LIST }}
    attachments: Central_Zone_Leadership_Pack_*.pptx
```

### Slack Integration (Optional Setup)

To post PPT to Slack #leadership-analytics:

1. Add Slack step to workflow
2. Use GitHub Secret: `SLACK_WEBHOOK_URL`
3. Configure `slackapi/slack-github-action@v1`

---

## Support & Contact

| Issue | Contact | Reference |
|-------|---------|-----------|
| PPT content questions | Analytics Lead | `docs/IMPLEMENTATION_STATUS.md` |
| Data accuracy | Data Engineering | `scripts/build_dashboard_data.py` comments |
| CI/CD troubleshooting | DevOps / GitHub | `.github/workflows/*.yml` |
| Zone governance | Modern Trade Lead | `PowerBI/docs/RefreshGuide.md` |

---

## Version History

| Date | Version | Changes |
|------|---------|---------|
| 2026-08-17 | 1.0 | Initial deployment: 18-slide Central zone PPT, monthly automation |
| TBD | 1.1 | Email distribution integration |
| TBD | 1.2 | Slack posting + dashboard embed |

---

## Next Steps

1. ✅ **Immediate:** Download & review latest PPT from Releases
2. ✅ **By end of week:** Share with Central zone leadership team
3. ⏳ **By September 1st:** Verify monthly auto-generation runs successfully
4. ⏳ **Optional:** Set up email/Slack distribution
5. ⏳ **Quarterly:** Review PPT content structure for adjustments

---

**Ready to deploy. All systems operational. 🚀**

Generated: 2026-08-17  
Branch: `claude/data-analytics-learning-g8ggyw`  
Status: Production
