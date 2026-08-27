# Passive Standby Mode — August 27–29, 2026

**Standby Phase:** Phase 1 (awaiting external gates)  
**Duration:** T+24h to T+72h (unless approval gates signal earlier execution)  
**Status:** All technical prerequisites complete; in holding pattern for Finance + Commercial sign-off

---

## 🔒 Standby Mode Principles

### 1. Freeze Branch Commits
- **No new code commits** to `claude/june-26-sales-data-xzbhub`
- **Zero-intervention principle:** Avoid introducing speculative features, DAX restructuring, or DOM asset changes
- **Preserve current build:** All 120 tests, governance gates, and Power BI automation remain frozen
- **Rationale:** Stakeholder review phase; changes would invalidate concurrent feedback loops

### 2. Time-Boxed Feedback Gates
Two parallel tracks with explicit deadlines:

#### **Track A: Finance D1 Approval (CM2 Formula)**
- **Gate:** CM2 formula signed by Finance approver
- **File:** `config/cm2_formula.csv`
- **Deadline:** Friday, August 28, 2026, 9:00 AM IST (T+48h)
- **Escalation:** If unsigned by deadline, escalate to Finance Controller / CFO for 15-min alignment call
- **Trigger:** Once signed, execute 1-hour Release Runbook immediately

#### **Track B: Commercial / Sales & Ops UX Review**
- **Window:** August 27–29, 2026
- **Feedback Channel:** `.escalation-package/MOCK_PBIX_REVIEW_GUIDE.md` (structured template)
- **Handling:** Any UI/UX adjustments → **post-release backlog** (do NOT block primary deployment)
- **Rationale:** Live data may change feedback; design changes can be applied in Phase 4

### 3. Automated Daily Health Checks
**Script:** `bash daily_health_check.sh`  
**Frequency:** Once daily at 9:00 AM IST  
**Confirms:**
- ✅ No unexpected commits on `main`
- ✅ Working tree clean
- ✅ Python syntax OK
- ✅ Governance gate status (CM2 formula)
- ✅ All key assets present (PBIX, docs, scripts)

**Output:** Logged to `.standby-logs/health_check.log`

---

## 📋 Daily Standby Checklist

### 9:00 AM IST
- [ ] Run `bash daily_health_check.sh`
- [ ] Verify no unexpected commits on `main`
- [ ] Confirm CM2 formula status (DRAFT vs APPROVED)
- [ ] Check `.escalation-package/` for incoming approvals

### Ongoing (Throughout day)
- [ ] Monitor Finance approval channel (email, Slack)
- [ ] Collect Sales/Ops feedback into MOCK_PBIX_REVIEW_GUIDE.md template
- [ ] Flag any critical issues → escalate (do NOT fix code during standby)

### T+48h Checkpoint (Friday, Aug 28, 9:00 AM IST)
- [ ] If CM2 Status = **APPROVED:** Execute Release Runbook immediately
- [ ] If CM2 Status = **DRAFT:** Escalate to Finance Controller

---

## 🚨 Escalation Protocol

### Finance D1 Approval Missing (T+48h)
**Owner:** Data Engineering Lead  
**Action:** 15-minute alignment call with Finance Controller / CFO

**Template:** `config/D1_APPROVAL_REQUEST.md` (decision context)

**Content:** "CM2 formula gate is blocking production release. All 120 tests green, governance framework live. Please decide:
- **(a) INCLUDE:** COGS inside CM2 definition (reduces reported margin)
- **(b) EXCLUDE:** COGS shown separately (CM2 unchanged)

One-line approval in `config/cm2_formula.csv` triggers 1-hour deployment. What is your decision?"

### Commercial UX Feedback Issues
**Owner:** Product / Design Lead  
**Action:** Route feedback into post-release backlog

**Do NOT:** Block deployment for design changes  
**Do:** Collect and prioritize for Phase 4 (post-launch enhancements)

---

## 🔄 Release Trigger Sequence

**Condition:** `config/cm2_formula.csv` updated with `Status = APPROVED` + valid approver name + date

**Upon Trigger:**
```
T+0 min:   Finance approver commits signed CM2_formula.csv
T+5 min:   Automated GitHub Actions workflow detects approval
T+10 min:  Release Runbook executes:
           - Final data refresh
           - Dashboard deployment to GitHub Pages
           - PBIX publication to Power BI Service
T+60 min:  All systems live; stakeholder notifications sent
```

**Release Runbook:** See `STANDBY_PROCEDURES.md` (Phase 3 Release Execution)

---

## ⛔ What NOT to Do During Standby

❌ Do NOT commit code changes (freeze active branch)  
❌ Do NOT merge PR #16 before D1 approval  
❌ Do NOT modify DAX measures or Power BI specs  
❌ Do NOT load real data prematurely  
❌ Do NOT redesign UI based on early feedback  
❌ Do NOT manually trigger deployments  

---

## ✅ What TO Do During Standby

✅ **Monitor:** Daily health checks (9:00 AM IST)  
✅ **Communicate:** Distribute escalation package to Finance/Sales/Ops  
✅ **Collect:** UX feedback via MOCK_PBIX_REVIEW_GUIDE.md template  
✅ **Escalate:** If approval missing at T+48h deadline  
✅ **Prepare:** Release team for 1-hour execution window  
✅ **Document:** Any blocking issues (escalate, do not fix)  

---

## 📞 Communication Plan

### Finance / CFO
- **Message:** `.escalation-package/T24H_FINANCE_ESCALATION.md`
- **Channel:** Email + Slack
- **Content:** Decision options, approval checklist, deadline
- **Due:** Immediate (T+24h)

### Sales & Operations
- **Message:** `.escalation-package/MOCK_PBIX_REVIEW_GUIDE.md`
- **Channel:** Email + Power BI Teams channel
- **Content:** Dashboard preview, feedback template, UX validation
- **Due:** Aug 29 EOD (review window: Aug 27–29)

### Data Engineering / Release Team
- **Message:** This document + `.standby-logs/health_check.log`
- **Channel:** Daily standup (9:00 AM IST)
- **Content:** Governance gate status, trigger readiness
- **Due:** Daily

---

## 📊 Standby Phase Timeline

| Time | Event | Owner | Status |
|------|-------|-------|--------|
| **Aug 27, T+24h** | Escalation package sent | Data Eng | ✅ Complete |
| **Aug 27, 9:00 AM** | 1st daily health check | Data Eng | ⏳ Pending |
| **Aug 27–29** | Sales/Ops UX review | Comm Lead | ⏳ In progress |
| **Aug 28, 9:00 AM, T+48h** | Escalation checkpoint | Data Eng | ⏳ Pending |
| **Aug 28, TBD** | **[TRIGGER]** Finance approves D1 | Finance | ⏳ Awaiting approval |
| **Aug 28/29, +60 min** | Release execution (if triggered) | Data Eng | 🟢 Standby |
| **Aug 29, EOD** | UX feedback intake deadline | Comm Lead | ⏳ Pending |

---

## Key Files & Locations

| File | Purpose | Owner |
|------|---------|-------|
| `.escalation-package/T24H_FINANCE_ESCALATION.md` | Finance decision context | Data Eng |
| `.escalation-package/MOCK_PBIX_REVIEW_GUIDE.md` | Sales/Ops UX feedback template | Comm Lead |
| `config/cm2_formula.csv` | **TRIGGER FILE** — approval gate | Finance |
| `daily_health_check.sh` | Automated status monitor | Data Eng |
| `.standby-logs/health_check.log` | Daily checkpoint logs | Data Eng |
| `STANDBY_PROCEDURES.md` | Phase 3 release runbook | Data Eng |

---

## Success Criteria for Standby Phase

- ✅ No unexpected code changes on `main`
- ✅ All 120 tests remain green
- ✅ Daily health checks run without errors
- ✅ Finance approval decision (D1) received by T+48h
- ✅ Sales/Ops UX feedback collected (optional for go/no-go)
- ✅ Release team prepped for 1-hour execution window
- ✅ Escalation package delivered to all stakeholders

---

**Standby Mode Owner:** Data Engineering Lead  
**Standby Phase Duration:** T+24h to Release Trigger (estimated T+48h–T+72h)  
**Next Gate:** Finance D1 Approval (config/cm2_formula.csv update)

*No commits, no changes, no scope creep. Frozen build. Ready to deploy on signal.*
