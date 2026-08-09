---
name: mt-channel-decision-log
description: |
  Capture, structure, and retrieve NKAM and chain-level decisions, commitments, and
  channel intelligence for Modern Trade accounts. Use when user asks to "log this decision",
  "record what we decided for BigBasket", "NKAM decision log", "what did we agree with DMart",
  "channel intelligence brief", "what is open with Reliance", "decision history for this chain",
  "NKAM commitments tracker", "what changed with Nykaa", "chain intelligence summary",
  "open items for this account", "stakeholder brief for chain", "what schemes did we commit to",
  "NKAM action register".
  Do NOT use for scheme ROI analysis (→ mt-trade-promotion) or promo experiment design (→ mt-campaign-analytics).
---

# MT Channel Decision Log

Capture, structure, and surface every material NKAM decision — commitments made, schemes approved,
listing agreements, escalations, and open items — so institutional knowledge doesn't live only
in email threads.

---

## Decision Log Schema

Every logged decision must capture all 7 fields:

```
DECISION RECORD
──────────────────────────────────────────────────────────────────
Date:          [YYYY-MM-DD]
Chain:         [BigBasket / DMart / Reliance / Nykaa / Blinkit / …]
Decision:      [What was decided — specific, not vague]
Context:       [Why this decision was made — 1-2 sentences]
Owner:         [Name, role — who is responsible for execution]
Deadline:      [YYYY-MM-DD or "standing"]
NSV Impact:    [₹L expected — can be "not quantified" if exploratory]
Source:        [Call / Email / In-person / NKAM review meeting]
Status:        [OPEN / IN PROGRESS / DONE / BLOCKED / CANCELLED]
──────────────────────────────────────────────────────────────────
```

**Hard rules:**
- Never log a decision without an owner — "TBD" is not an owner
- Never log a financial commitment (scheme ₹L, visibility payment) without NSV Impact
- BLOCKED decisions must include what is blocking and who can unblock

---

## Decision Types — MT Specific

| Type | Examples | Escalation Level |
|---|---|---|
| **Scheme commitment** | "10% off-invoice on SKU X for Aug-Sep at BigBasket" | Finance sign-off required > ₹5L |
| **Listing agreement** | "List 3 new SKUs at DMart by 15 Sep" | NKAM + Category Manager |
| **Visibility contract** | "Secondary display at Nykaa Stores — ₹3.5L for Q2" | NKAM approval |
| **Pricing decision** | "RSP maintained at ₹299 — no match to competitor ₹279" | CMO/CFO if margin impact > 2pp |
| **Range rationalisation** | "Exit SKU Y from Reliance — < 1 unit/store/month" | NKAM + Supply Chain |
| **Escalation / Dispute** | "Reliance claims ₹12L MRN not credited — Finance investigating" | Finance Lead |
| **Policy exception** | "Brand counter exemption approved for Reliance Navi Mumbai" | MT Lead only |

---

## 90-Day Channel Intelligence Brief

Generate this brief when a team member needs to quickly get context on a specific chain:

```
## Channel Intelligence Brief — [Chain Name] — [Month] FY[XX]

### Account Snapshot
NSV (last 3 months):     ₹[X]L, ₹[Y]L, ₹[Z]L (trend: ↑/↓/→)
GM% (last month):        [X]%
Trade Spend% (last 3M):  [X]% → [Y]% → [Z]%
DOS (current):           [X] days vs target [Y] days
Numeric Distribution:    [X]% (target [Y]%)

### Commitments Made (last 90 days — not yet DONE)
[Date] | [Decision summary] | Owner: [Name] | Due: [Date] | Status

### Open Items (items awaiting chain or internal action)
[Item] | Waiting on: [chain / Finance / Supply Chain] | Since: [Date]

### Key Context Changes (last 90 days)
[e.g. "Chain re-opened listing process for Q3 in July", "New buyer appointed", "Competitor promo active"]

### Communication Patterns
Last meeting: [Date + format]
Last escalation: [Date + topic]
Average response time: [Days]

### Risk Flags
□ MRN dispute open: [₹L amount, duration]
□ Scheme addiction risk: [scheme in place > 2 consecutive months?]
□ DOS > 21 days: [Y/N — which SKUs?]
□ Brand counter filter active: [Y/N — per BUSINESS_RULES.md exact-match rule]
```

---

## Channel Opportunity Scoring

Rank chains and accounts by investment priority using a composite score:

```python
import math

def channel_opportunity_score(
    nsv_growth_yoy_pct,      # e.g. 0.25 for +25%
    distribution_gap_pp,      # e.g. 15 = 15pp below target
    roi_last_3m_avg,          # average trade spend ROI last 3 months
    dos_days,                  # current days of supply
    chain_nsv_share_pct       # chain's % of total MT NSV
):
    """
    Composite score 0–100.
    High Opportunity ≥ 60: increase investment
    Emerging 40–59: targeted investment with milestones
    Saturated < 40: maintain or reduce; fix root cause first
    """
    # Growth signal (30%): higher YoY growth = higher score
    growth_component = min(max((nsv_growth_yoy_pct + 0.5) / 1.0, 0), 1) * 30

    # Distribution gap (25%): bigger gap = more room to grow = higher score
    dist_component = min(distribution_gap_pp / 40, 1) * 25

    # ROI signal (30%): higher recent ROI = higher confidence in spend
    roi_component = min(max((roi_last_3m_avg - 0.5) / 2.0, 0), 1) * 30

    # DOS penalty (15%): high DOS = stocking problem; reduce score
    dos_penalty = min(max((dos_days - 15) / 30, 0), 1) * 15
    dos_component = 15 - dos_penalty

    raw_score = growth_component + dist_component + roi_component + dos_component

    label = (
        "High Opportunity" if raw_score >= 60 else
        "Emerging"         if raw_score >= 40 else
        "Saturated"
    )
    return round(raw_score, 1), label
```

---

## Decision Review Cadences

| Cadence | Scope | Format |
|---|---|---|
| **Weekly (Mon 9am)** | Open items only — any past due or newly blocked | 5-row table: Item / Owner / Due / Status / Action needed |
| **Monthly NKAM review** | Full 90-day brief per top-5 chains | Channel Intelligence Brief format above |
| **Quarterly (QBR)** | All decisions from quarter + outcomes + lessons learned | QBR Slide 10 + 11 (mt-deck-builder QBR template) |

---

## Decision State Machine

```
[NEW] → logged with all 7 fields
  ↓
[IN PROGRESS] → owner confirmed, execution started
  ↓              ↙ if blocked
[DONE]       [BLOCKED] → unblock owner named; weekly escalation if > 5 days blocked
                ↓
             [CANCELLED] → reason logged; NSV impact revised
```

**Escalation trigger:** Any OPEN item past its deadline by > 3 days automatically requires
a BLOCKED status update with unblock owner. Undated open items are invalid — must assign date.

---

## Weekly Open Items Digest Format

```
## NKAM Open Items — Week of [Date]

### Overdue (Past deadline — immediate action required)
| Chain | Decision | Owner | Was Due | Status | Blocker |
|---|---|---|---|---|---|
| DMart | List SKU X | [Name] | 01-Aug | BLOCKED | Chain buyer on leave until 10-Aug |

### Due This Week
| Chain | Decision | Owner | Due | Status |
|---|---|---|---|---|

### Coming Up (Next 2 weeks)
| Chain | Decision | Owner | Due | Status |

### Newly Logged This Week
| Chain | Decision | Owner | Due | NSV Impact |
|---|---|---|---|---|
```

---

## Kill Switches — Hard Stops

The following trigger an immediate HOLD on further NKAM commitments:

```
HOLD if:
  □ Chain EBITDA negative for 2+ consecutive months AND no Finance approval on file
  □ MRN dispute > ₹10L open with no resolution path
  □ Brand counter classification applied WITHOUT exact-match check (see BUSINESS_RULES.md)
  □ Scheme letter not signed before scheme period starts
  □ Listing commitment made without Category Manager co-sign for new product

Do NOT proceed — escalate to MT Lead immediately.
```

---

## Integration with Other Skills

- Use **mt-trade-promotion** when a logged decision involves scheme ROI or BTL spend
- Use **mt-campaign-analytics** to record campaign experiment outcomes
- Use **mt-intelligence-engine** for root cause analysis referenced in decision context
- Use **mt-financial-intelligence** when decisions have P&L implications > ₹5L
- Use **mt-deck-builder** Slide 9 (Actions & Owner Grid) to present open items
- Use **mt-production-readiness** before releasing chain decisions to leadership
