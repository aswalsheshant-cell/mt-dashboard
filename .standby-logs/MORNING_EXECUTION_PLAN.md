# Morning Release Execution Plan — August 28, 9:00 AM IST

**Status:** PRE-STAGED ✅  
**Trigger:** Finance D1 Approval  
**Execution Window:** 60 minutes  
**Owner:** Data Engineering (Automated)

---

## Timeline

| Time | Action | Duration | Status |
|------|--------|----------|--------|
| **9:00 AM** | Health check + CM2 status verification | 5 min | ⏳ Pending |
| **9:05 AM** | Execute Release Runbook (Steps 4-8) | 55 min | ⏳ Pending |
| **10:00 AM** | Production deployment complete | — | ⏳ Pending |

---

## Step-by-Step Execution (Automated)

### STEP 1: Health Check & Governance Verification
```bash
cd /home/user/mt-dashboard && bash daily_health_check.sh
```
**Confirms:**
- ✅ Branch integrity (no unexpected commits on main)
- ✅ Working tree clean
- ✅ Python syntax validated
- ✅ CM2 governance status (checks for APPROVED + production signature)
- ✅ All key assets present

**Decision Point:**
- **IF CM2 Status = APPROVED (production):** → Proceed to STEP 2
- **IF CM2 Status = PENDING/DRAFT:** → Trigger escalation protocol (15-min CFO call)

---

### STEP 2-8: Release Runbook Execution (Automated)
```bash
bash scripts/execute_release_runbook.sh
```

**What the script does:**

| Step | Action | Status |
|------|--------|--------|
| 4 | Detect & commit approval (config/cm2_formula.csv) | ⏳ |
| 5 | Validate governance gates (syntax, deps, asset integrity) | ⏳ |
| 6 | Merge PR #16 to main (resolve conflicts if any) | ⏳ |
| 7 | Push release to remote (with retries) | ⏳ |
| 8 | Deploy & verify (GitHub Pages, PBIX readiness) | ⏳ |

**Output Logs:**
- Main: `.standby-logs/release_runbook.log`
- Health: `.standby-logs/health_check.log`

---

## Success Criteria

- ✅ Production approval detected in config/cm2_formula.csv
- ✅ No merge conflicts during PR #16 merge
- ✅ main branch updated with all standby changes
- ✅ All changes pushed to remote
- ✅ Dashboard deployment verified

---

## Escalation Criteria

If **9:00 AM IST checkpoint shows CM2 Status = PENDING/DRAFT**:

1. **T+48h deadline exceeded** → Escalation triggered automatically
2. **Owner:** Data Engineering Lead
3. **Action:** 15-minute alignment call with Finance Controller / CFO
4. **Template:** `.escalation-package/T24H_FINANCE_ESCALATION.md`
5. **Outcome:** Collect final decision + update config/cm2_formula.csv

---

## Pre-Staged Artifacts

All of the following are ready and committed:

- ✅ `scripts/execute_release_runbook.sh` — Full 60-min automation
- ✅ `.escalation-package/T24H_FINANCE_ESCALATION.md` — Finance decision context
- ✅ `daily_health_check.sh` — 5-layer governance verification
- ✅ `PASSIVE_STANDBY_MODE.md` — Complete standby procedures
- ✅ `config/cm2_formula.csv` — Governance gate (Finance to update)

---

## Manual Handoff Points

Only IF automation encounters an issue:

1. **Merge conflicts** → Manual conflict resolution required
2. **Finance approval not received by 9:00 AM** → Escalation call dispatch
3. **Asset integrity check fails** → Review missing asset log + adjust script

---

## Post-Execution Steps

Once Release Runbook completes successfully:

1. **GitHub Pages** — Dashboard auto-deploys (2-3 min delay)
2. **Power BI Service** — Manual publish of Modern_Trade_Dashboard.pbix
3. **Stakeholder notification** — Send go-live confirmation + live dashboard URL
4. **Success log** → Append release completion details to `.standby-logs/health_check.log`

---

**Next Action:** Tomorrow, August 28, 9:00 AM IST  
**Automation Status:** All scripts pre-staged and tested ✅  
**Confidence Level:** Production-ready 🟢
