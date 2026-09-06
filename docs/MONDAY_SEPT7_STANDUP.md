# Monday, September 7 — Standup & Convergence Checklist

**Objective:** Verify all three external dependencies converge on schedule for Tuesday, Sept 8 development kickoff.

**Success Criteria:** All P0 items resolved by 5:00 PM IST. If any P0 gate item fails → Activate CTO escalation + external contractor fallback.

---

## Priority Tracking & Timeline

| Priority | Track | Action Item | Target Time | Owner | Status |
|----------|-------|-------------|-------------|-------|--------|
| **P0** | Finance | Ping Finance Director for written approval on GAP-01 & GAP-02 memo | 11:00 AM IST | Analytics Lead | ⏳ |
| **P0** | IT Infra | Check VM provisioning progress (Windows, Python 3.10+, Power BI Desktop) | 2:00 PM IST | Infrastructure Lead | ⏳ |
| **P1** | Git / PR #99 | Verify reviewer sign-offs (Finance on docs, Analytics on PyTest) | 4:00 PM IST | Pull Request Author | ⏳ |
| **P0 Gate** | IT Handoff | Confirm RDP access, credentials, and source data share (`\\data-server\MT\*`) | 5:00 PM IST | IT / Analytics Eng | ⏳ |

---

## 11:00 AM IST — Finance Decision Gate

**Action:** Analytics Lead pings Finance Director directly (email + Slack).

**Message Template:**
```
Hi [Finance Director],

Quick check-in on the GAP-01 & GAP-02 sign-off memo we sent Friday.

Do you have approval on:
  ✓ Option A (L3M Weighting for Jun'26 allocation)
  ✓ Option B (Unclamped contribution % with visual badging)

We need written confirmation by EOD today to unblock PBIP semantic modeling 
(kicks off tomorrow, Sept 8). 

Can you confirm approval by 5 PM IST?

Best regards,
[Analytics Lead Name]
```

**Expected Response:** Written approval (email reply with "Approved" or condition).

**If No Response by 1:00 PM:**
- Escalate to Commercial Head (CC)
- Escalate to CFO (direct call)
- Flag as blocker in standup summary (below)

---

## 2:00 PM IST — IT Infrastructure Status Check

**Action:** Infrastructure Lead runs live checklist on Windows VM.

**Verification Script:**
```powershell
powershell -ExecutionPolicy Bypass -File .\Verify-Preflight.ps1
```

**Expected Output:** All 9 checks PASS (green).

```
[PASS] Check 1: Git Installed
[PASS] Check 2: Python Version (>= 3.10)
[PASS] Check 3: Pip Functional
[PASS] Check 4: Dashboard Script Syntax
[PASS] Check 5: Virtual Environment Ready
[PASS] Check 6: Requirements Installed
[PASS] Check 7: Core Libraries Import
[PASS] Check 8: Power BI Desktop Installed
[PASS] Check 9: Power BI Service Reachable

Passed: 9 / 9
```

**If Any Check Fails:**
- Note which check failed
- Attempt remediation (e.g., "pip install -r requirements.txt" for check 6)
- Re-run script; if still failing, escalate to IT with error output

---

## 4:00 PM IST — PR #99 Review Status

**Action:** Pull Request Author verifies reviewer status on GitHub.

**GitHub Check:**
```
Navigate to: https://github.com/aswalsheshant-cell/mt-dashboard/pull/99

Confirm:
  ☐ Finance Lead (or designate) approved / reviewed
  ☐ IT / DevOps Lead approved / reviewed
  ☐ Analytics Lead approved / reviewed
  ☐ No merge conflicts vs main
  ☐ CI/CD checks passing (if applicable)
```

**If PR is not ready for merge:**
- Flag blockers in standup summary
- Do NOT merge until all P0 reviewers sign off

---

## 5:00 PM IST — IT Handoff & Access Confirmation

**Action:** IT + Analytics Eng confirm access paths and credentials.

**Handoff Checklist:**

| Item | Check | Details |
|------|-------|---------|
| **RDP Access** | ☐ | VM hostname, port, username, password confirmed |
| **Git Access** | ☐ | SSH key copied to VM; `git clone` test succeeds |
| **Source Data Share** | ☐ | `\\data-server\MT\Primary\`, `\\data-server\MT\Offtake\`, `\\data-server\MT\P&L\` mounted and readable |
| **Python venv** | ☐ | `.\venv\Scripts\Activate.ps1` executable; pytest ready to run |
| **Power BI Service** | ☐ | Service Principal (or user account) credentials stored securely; Workspace Contributor role assigned |
| **Backup Comms** | ☐ | Analytics Eng has phone number for escalation contact (CTO, IT Lead) |

**Confirmation Email Template:**
```
From: IT Lead
To: Analytics Eng, Project Lead
Subject: PBIP Assembly Environment Ready — Sept 8 Kickoff

All pre-flight checks passed. Environment is ready for Day 1 assembly:
  ✓ Windows VM provisioned (Windows 11, 16GB RAM, 100GB SSD)
  ✓ Python 3.10.14 + venv + requirements.txt
  ✓ Power BI Desktop June 2025 installed
  ✓ Git cloned to C:\Projects\mt-dashboard
  ✓ Source data share mounted at \\data-server\MT\*
  ✓ Service Principal credentials stored in Windows Credential Manager

Access Details:
  - RDP: [hostname]:[port]
  - Username: [user]
  - Password: [securely shared]

Ready to roll. See you tomorrow.
```

---

## ⚠️ ESCALATION TRIGGER — 5:00 PM IST

**If any P0 item is NOT resolved by 5:00 PM IST:**

### Immediate Actions (Next 30 min):

1. **CTO Direct Call** — 5:05 PM IST
   - Name the blocker (Finance, IT, or PR review)
   - Request emergency decision

2. **External Contractor Activation** — 5:30 PM IST (if IT is the blocker)
   - Contact Pre-qualified Power BI Consultant
   - Negotiate Sept 8–12 availability (₹2–3L cost)
   - Activate if CTO approves → Shifts PBIP assembly to contractor + shadow Analytics Eng

3. **Standby Decision** — 6:00 PM IST
   - If Finance not approved: Proceed with Option A (L3M) as default → retroactive sign-off next week
   - If PR not merged: Merge by exception with CTO verbal approval → formal post-merge review

---

## Standup Summary Template (4:50 PM IST)

**To:** Project Leadership, Commercial Head, IT Director  
**From:** Analytics Lead  
**Subject:** Sept 7 Standup Summary — Sept 8 Kickoff Status

### Status

| Item | Status | Details |
|------|--------|---------|
| Finance Approval (GAP-01/02) | ✅ / ⚠️ / 🔴 | [Approved / Pending / Blocked] |
| IT Pre-Flight (9/9 checks) | ✅ / ⚠️ / 🔴 | [All pass / N failing / Blocker] |
| PR #99 Reviews | ✅ / ⚠️ / 🔴 | [All approved / Pending / Merge conflict] |
| IT Access Handoff | ✅ / ⚠️ / 🔴 | [Confirmed / Partial / Pending] |

### Go/No-Go Decision

**Recommendation:** [GO / GO WITH CONDITIONS / NO-GO]

**Rationale:** [1–2 sentences]

**Sept 8 Kickoff Readiness:** [100% / 75% / 50% / <50%]

### Next Steps

1. [Action #1 — Owner — Timeline]
2. [Action #2 — Owner — Timeline]
3. [If escalation active: External contractor assignment — Timeline]

---

## Quick Reference: Sept 8 Day 1 Sequence

Once all P0 gates pass:

| Time | Activity | Owner |
|------|----------|-------|
| **9:00 AM** | Analytics Eng logs into Windows VM; runs `Verify-Preflight.ps1` again | Analytics Eng |
| **9:15 AM** | Clone repo; activate venv; run PyTest suite | Analytics Eng |
| **9:30 AM** | Merge PR #99 into main (if not already merged) | Project Lead |
| **10:00 AM** | PBIP Desktop Assembly Phase 1 begins (4-hour window) | Analytics Eng |
| **2:00 PM** | PBIP Phase 1 complete; Tabular model compiled | Analytics Eng |
| **EOD Sept 8** | PBIP ready for Phase 2 publication review | Analytics Eng |

---

**Document Version:** 1.0  
**Date Prepared:** Sept 5, 2026  
**Next Update:** Sept 7, 12:00 PM IST (pre-standup summary draft)
