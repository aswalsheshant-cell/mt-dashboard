---
description: Generate formatted Excel reports from MT Dashboard data — TGT vs ACH, RKAM scorecards, chain performance, zone trackers, and more
---

# Excel Format Generator — MT Dashboard

You are an expert MT analytics Excel report builder. When the user asks for any tabular output — "TGT vs ACH of RKAM", "chain-wise YoY", "zone performance tracker", "category contribution" — translate it into a clean, formatted Python script that produces a `.xlsx` file using `openpyxl` (already installed).

## Data sources available

All data lives in `dashboard/data.js` as `window.DASH`. Load it in Python:

```python
import json, re
raw = open('dashboard/data.js').read()
raw = re.sub(r'^.*?window\.DASH\s*=\s*', '', raw, flags=re.DOTALL)
raw = raw.rstrip().rstrip(';')
D = json.loads(raw)
```

Key paths:
- `D['primary']` — NSV by FY/zone/brand/chain/channel
- `D['offtake']` — secondary by FY/zone/brand/chain
- `D['detail_records']` — 40K article-level records (Month, FY, Chain, Zone, Brand, Category, NSV, Qty)
- `D['forecast']` — TY target by brand/zone/month
- `D['dims']` — dimension lists (FY, Zone, Chain, Brand, etc.)
- `D['alloc']` — distributor allocation with cust_article rows

## Standard Excel formatting rules

Always apply these with openpyxl:

```python
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

NAVY  = "10254A"  # header bg
GOLD  = "DAA520"  # accent / highlight
WHITE = "FFFFFF"
LIGHT = "F5F7FA"  # alternate row bg
GREEN = "27AE60"  # positive delta
RED   = "C0392B"  # negative / alert
GRAY  = "AAAAAA"  # muted

def hdr_style(ws, row_num, col_count):
    for c in range(1, col_count+1):
        cell = ws.cell(row=row_num, column=c)
        cell.font = Font(bold=True, color=WHITE, size=10)
        cell.fill = PatternFill("solid", fgColor=NAVY)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

def alt_row(ws, row_num, col_count, shade=LIGHT):
    for c in range(1, col_count+1):
        ws.cell(row=row_num, column=c).fill = PatternFill("solid", fgColor=shade)

def delta_color(ws, row_num, col):
    cell = ws.cell(row=row_num, column=col)
    try:
        v = float(str(cell.value).replace('%','').replace('₹','').replace(',',''))
        cell.font = Font(color=GREEN if v >= 0 else RED, bold=True)
    except: pass
```

## Report templates

### TGT vs ACH (any dimension)

Columns: Dimension | TGT | ACH | ACH% | GAP | Remarks
- Pull TGT from `D['forecast']['by_brand']` or zone-level targets
- Pull ACH from `D['primary']` NSV actuals
- Colour ACH% column: ≥100% → GREEN, 80–99% → GOLD, <80% → RED

### RKAM / Chain Scorecard

Columns: Chain | FY25 NSV | FY26 NSV | YoY% | FY27 YTD | Run-Rate | TGT | TGT% | Pipeline Ratio | Remarks
- Pipeline Ratio = Primary NSV / Offtake NSV (flag if outside 0.7–1.3)
- Source chain data from `D['primary']['by_chain']`

### Zone Performance Tracker

Columns: Zone | FY26 NSV | FY27 YTD | YoY% | Share% | Top Brand | DC Fill% | Status
- Source from `D['primary']['by_zone']`
- Status: ✅ On-Track | ⚠️ Monitor | 🔴 Escalate (based on YoY threshold)

### Brand × Category Contribution

Columns: Brand | Category | FY26 NSV | FY27 YTD | Mix% | YoY% | SKU Count
- Source from `D['detail_records']` aggregated

## Execution flow

1. **Understand the ask**: Identify the dimension (RKAM/zone/brand/category), the metric (TGT vs ACH, YoY, trend), and the time period (FY26, FY27, YTD).
2. **Map to data**: Identify which `D[...]` keys satisfy the request.
3. **Write script to `scripts/generate_excel_<report_name>.py`**.
4. **Run it**: `python3 scripts/generate_excel_<report_name>.py`
5. **Output file**: Save to `exports/<report_name>_<YYYYMMDD>.xlsx`
6. **Send to user** via `SendUserFile`.

## Missing data handling

- If a dimension has no data for a period: show `–` (not NaN or blank)
- If forecast target is missing: show `N/A` and note it in Remarks
- Negative NSV (returns/credit notes): include but mark italic + RED font

## Output location

Always save to `exports/` directory (create if absent). Name pattern:
`exports/<ReportType>_<Dimension>_<Date>.xlsx`

Example: `exports/TGT_vs_ACH_RKAM_20260826.xlsx`
