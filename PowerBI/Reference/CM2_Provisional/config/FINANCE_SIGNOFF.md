# Terms of Trade (TOT%) Configuration — Finance Sign-Off

**Document Type**: Finance Approval Required  
**Status**: AWAITING APPROVAL  
**Date**: 2026-08-27  
**Owner**: Finance Team  
**Scope**: Modern Trade Dashboard Phase 3 (Agent Sentiments & Executive Insights)

---

## Executive Summary

The MT Dashboard automation pipeline now requires explicit Finance approval of **Terms of Trade (TOT%)** rates — the margin pass-on percentage to retail chains. This configuration was previously hardcoded at 50.0% blended rate across all chains.

**Action Required**: Review the proposed TOT% rates (blended vs. chain-specific) and approve by updating `tot_rates.json` status to `APPROVED` with your sign-off.

---

## Current Configuration

**File**: `PowerBI/Reference/CM2_Provisional/config/tot_rates.json`  
**Status**: `DRAFT` (awaiting approval)  
**Blended Rate**: 50.0% (default if chain-specific rates not available)

### By-Chain Rates (Proposed)

| Chain | TOT% | Rationale |
|-------|------|-----------|
| **DMart** | 45.0% | High volume, high bargaining power → lower margin pass-on |
| **Reliance Retail** | 48.0% | Strong volume, premium positioning |
| **Spencer's** | 52.0% | Mid-tier volume, moderate margin |
| **Apollo** | 55.0% | Pharma focus, premium margin |
| **Nykaa SS** | 60.0% | Premium channel, higher margin support |
| **Wellness Forever** | 58.0% | Wellness positioning, elevated margin |
| **Health & Glow** | 52.0% | Standard retail, moderate margin |
| **Lulu** | 50.0% | Standard hypermarket, baseline |
| **Metro CNC** | 45.0% | Cash & Carry model, lower margin |
| **More Retail** | 48.0% | Regional player, moderate margin |
| **(All others)** | 50.0% | Blended baseline for smaller/new chains |

---

## How This Config Is Used

### Phase 3: Agent Sentiments Analysis

The TOT% rate drives **Profitability** insight generation:

```python
# Example: CM2% Analysis with TOT%
CM2 = NSV - P&L Expenses
CM2% = CM2 / NSV

Profitability Severity:
  - CRITICAL: CM2% < 20% (margin compression despite TOT% pass-on)
  - WARNING: CM2% < 25% or Expense% > 25%
  - ON_TRACK: CM2% >= 25% and Expense% <= 25%
```

The TOT% rate is **informational** in the generated insights:
- Included in profitability narrative: *"TOT%: 50.0%. Profitability on track. Maintain current strategy."*
- Helps Finance interpret CM2 trends: *"Is margin pressure driven by TOT% not covering expenses?"*

### Monthly Automation

1. **Sep 1, 00:00 UTC**: GitHub Actions runs Phase 1-3 automation
2. **Phase 3 Execution**: `generate_agent_sentiments.py` reads this config file
3. **Blended vs. Approved**:
   - If status = `DRAFT` → Warning logged, uses **blended rate (50.0%)**
   - If status = `APPROVED` → Proceeds with **full chain-specific config**
   - If status = anything else or file missing → Fallback to blended 50.0%

**No code deployment required** — just update `status` and `approved_by`/`approved_at` fields in this JSON file.

---

## Approval Workflow

### Step 1: Finance Review
Review the proposed chain-specific TOT% rates. Confirm:
- [ ] DMart 45% acceptable for high-volume/low-margin negotiation
- [ ] Tier-1 chains (Reliance, Apollo, Nykaa) 48-60% reflects premium positioning
- [ ] Tier-2/regional chains 45-52% aligns with historical negotiations
- [ ] Blended 50% is appropriate default for unmapped chains

### Step 2: Approval
Once approved, update this file:

**Requester**: [Finance Lead Name]  
**Approved By**: [Finance Lead Name]  
**Approved Date**: [YYYY-MM-DD HH:MM:SS UTC]  

Edit `tot_rates.json`:
```json
{
  "status": "APPROVED",
  "approved_by": "finance.lead@honasa.com",
  "approved_at": "2026-08-27T14:30:00Z",
  "blended_tot_pct": 50.0,
  "by_chain": { ... },
  "notes": "Finance approved chain-specific rates effective Sep 1, 2026 automation."
}
```

### Step 3: Commit & Deploy
Once approved:
```bash
git add PowerBI/Reference/CM2_Provisional/config/tot_rates.json
git commit -m "finance: Approve chain-specific TOT% rates for Phase 3 automation"
git push origin main
```

Sep 1 automation will auto-pick up the APPROVED status and use full config.

---

## Data Flow

```
User Input: tot_rates.json (DRAFT)
    ↓
Sep 1 Automation: Phase 1-3 Pipeline
    ├─ Phase 1: Build data.js (NSV, expenses, CM2)
    ├─ Phase 2: Extract CSV contracts
    ├─ Phase 3: Generate Agent Sentiments
    │   ├─ Load tot_rates.json
    │   ├─ If DRAFT: use blended 50%, log warning
    │   ├─ If APPROVED: use chain-specific rates
    │   └─ Profitability insight includes TOT% narrative
    ├─ QC Validation Gate
    └─ Commit artifacts: insights/generated_insights.json
    ↓
Dashboard: Tab 11 (Insights & Way Forward)
    ├─ Displays Profitability insight with TOT% context
    └─ User sees: "TOT%: 45.0% (DMart). Margin pressure detected."
    ↓
Power BI: PBIX Generation (Phase 2.5, Sep 10-12)
    └─ DAX measures can reference cm2_formula.csv for approval status
```

---

## Fallback & Safety

**If config is missing/invalid**:
- Default: blended_tot_pct = 50.0%
- Log: "WARN: TOT% config missing or invalid. Using fallback blended rate."
- Impact: None — profitability analysis proceeds with 50% baseline
- **No pipeline failure**

**If status ≠ APPROVED**:
- Proceeds with blended rate
- Logs: "WARN: TOT% config status is DRAFT — awaiting Finance approval."
- Dashboard still renders insights (with generic 50% rate)
- No action required until Finance approves

---

## Questions?

**Finance Contact**: aswal.sheshant@gmail.com  
**Technical Contact**: Claude Code Agent  
**Implementation**: See `scripts/generate_agent_sentiments.py` function `load_tot_config()`

---

## Sign-Off Checklist

- [ ] Reviewed chain-specific TOT% rates
- [ ] Confirmed blended 50% is appropriate default
- [ ] Approved rates reflect negotiated terms
- [ ] Ready to update `tot_rates.json` status to APPROVED

**Finance Lead**: _____________________ **Date**: _________

Once complete, reply to this document or update `tot_rates.json` directly with approval.
