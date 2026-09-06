---
name: report-generator
description: "Instructions for formatting analytical summaries, metrics, and Power BI report insights."
tags: [reporting, powerbi, analytics]
---
# Report Generator Instructions

## Report Types
| Type | Output | Audience |
|------|--------|----------|
| Monthly MT Summary | Markdown / slide deck | Leadership |
| Chain Scorecard | Table with trend arrows | KAMs |
| Promo Deep-Dive | Chart data + narrative | Trade team |
| FY YoY Comparison | Side-by-side metrics | Finance |
| Power BI Insight Narrative | DAX-backed text block | Dashboard viewers |

## Metric Formatting Rules
- Currency: `₹X.XX Cr` (Crore, 2 decimal places). Never use lakhs in headlines.
- Percentages: `X.X%` with sign for change (`+2.3%`, `-1.7%`)
- Zero: render as `–` in tables, `0.0` in charts
- Large numbers: `₹441 Cr`, not `₹44,10,00,000`
- Negative variance: show in parentheses in financial tables `(₹1.4 Cr)`

## Headline Structure (EIAO Frame)
```
EVIDENCE:    [Specific measurable fact with ₹ value]
IMPLICATION: [Why this matters to the business]
ACTION:      [Specific next step with owner and date]
OWNER:       [Role + deadline]
```

Example:
```
EVIDENCE:    Reliance offtake fell ₹1.42 Cr MoM in Jul-26
IMPLICATION: One chain drove the entire MT decline; all others grew ₹0.13 Cr combined
ACTION:      Run hero-EAN OSA audit at 38 Reliance stores by Sep 15
OWNER:       NKAM Reliance · 15-Sep-26
```

## Monthly Summary Template
```markdown
## MT Performance Summary — [Month-YY]

### Headline
[One sentence with the month's key story]

### KPIs
| Metric | FY26 Actual | FY26 Target | Variance |
|--------|-------------|-------------|----------|
| Primary NSV | ₹X.XX Cr | ₹X.XX Cr | +X.X% |
| Offtake | ₹X.XX Cr | ₹X.XX Cr | +X.X% |
| Conversion | X.X% | X.X% | (X.Xpp) |

### Chain Performance (Top 3 / Bottom 3)
[Table with chain, NSV, MoM change, trend]

### Action Register
| # | Action | Owner | Due | Status |
|---|--------|-------|-----|--------|
| 1 | ... | KAM | DD-Mon | Open |
```

## Power BI Insight Generation

### DAX Pattern for Narrative Fields
```dax
MT Insight Text =
VAR _pri = [Primary NSV ₹Cr]
VAR _tgt = [FY26 Target ₹Cr]
VAR _gap = _pri - _tgt
VAR _pct = DIVIDE(_gap, _tgt, 0) * 100
RETURN
    IF(
        _gap >= 0,
        "On track: ₹" & FORMAT(_pri, "0.00") & " Cr vs target ₹" & FORMAT(_tgt, "0.00") & " Cr (+₹" & FORMAT(_gap, "0.00") & " Cr)",
        "Below target: ₹" & FORMAT(ABS(_gap), "0.00") & " Cr gap vs ₹" & FORMAT(_tgt, "0.00") & " Cr target"
    )
```

### Insight JSON Format (generated_insights.json)
```json
{
  "insights": [
    {
      "id": "monthly-summary-fy26-jul26",
      "type": "monthly_summary",
      "fy": "FY26",
      "month": "Jul-26",
      "headline": "...",
      "evidence": "...",
      "implication": "...",
      "action": "...",
      "owner": "...",
      "generated_at": "2026-09-03T16:00:00Z"
    }
  ]
}
```

## Constraints
- Never fabricate numbers. If a source field is missing, write "data pending" not an estimate.
- Always cite the source FY and month for every metric.
- Distinguish Primary (sell-in) from Offtake (sell-out) — never conflate them.
- YoY comparisons require both FY years to be present in `dims.FY`; gate the section if either is missing.
