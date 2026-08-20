"""
Patch data.js: inject validated Reliance Retail monthly_fy26 into primary.by_chain.
Source: PowerBI/RawDataFolders/Primary_ShipTo_Monthly/Primary_ShipTo_FY25-26_to_May26.csv
Validated: FY26 total = 8348.90 Lac (₹83.49 Cr) — matches primary.by_chain.fy26.

Run from repo root:
    python scripts/patch_reliance_monthly_primary.py
"""
import csv, json, re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHIPTO_CSV = ROOT / "PowerBI/RawDataFolders/Primary_ShipTo_Monthly/Primary_ShipTo_FY25-26_to_May26.csv"
DATA_JS = ROOT / "dashboard/data.js"

MONTH_ORDER_FY26 = ["Apr'25","May'25","Jun'25","Jul'25","Aug'25","Sep'25",
                    "Oct'25","Nov'25","Dec'25","Jan'26","Feb'26","Mar'26"]
MONTH_LABELS = ["April","May","June","July","Aug","Sept","Oct","Nov","Dec","Jan","Feb","March"]

# ── 1. Extract Reliance monthly primary from ShipTo CSV ──────────────────────
monthly = defaultdict(float)
with open(SHIPTO_CSV, encoding="utf-8", errors="replace") as f:
    reader = csv.DictReader(f)
    for row in reader:
        chain = row.get("Chain", "").strip()
        if "reliance" in chain.lower():
            month = row.get("Month", "").strip()
            nsv = float(row.get("Primary NSV", 0) or 0)
            monthly[month] += nsv

fy26_vals = [round(monthly[m] / 100000, 2) for m in MONTH_ORDER_FY26]
fy26_total = round(sum(fy26_vals), 2)

print("Reliance monthly_fy26 (Lac):", fy26_vals)
print(f"Sum: {fy26_total} Lac = ₹{fy26_total/100:.2f} Cr")
assert abs(fy26_total - 8348.90) < 1.0, f"Unexpected FY26 total: {fy26_total}"
print("✓ FY26 total validates against data.js (8348.90 Lac)")

# ── 2. Patch data.js ─────────────────────────────────────────────────────────
text = DATA_JS.read_text(encoding="utf-8")

monthly_json = json.dumps(fy26_vals)

# Find the Reliance Retail entry in primary.by_chain and add monthly_fy26
# Pattern: "Reliance Retail",\n    "fy25": ...,\n    "fy26": ...,\n    "yoy": ...
old = '"Reliance Retail",\n    "fy25": 6443.46,\n    "fy26": 8348.9,\n    "yoy": 29.57\n   }'
new = ('"Reliance Retail",\n'
       '    "fy25": 6443.46,\n'
       '    "fy26": 8348.9,\n'
       '    "yoy": 29.57,\n'
       f'    "monthly_fy26": {monthly_json}\n'
       '   }')

if old not in text:
    # Already patched or different formatting — check
    if '"monthly_fy26"' in text and '"Reliance Retail"' in text:
        print("data.js already contains monthly_fy26 for Reliance Retail — no change needed.")
    else:
        print("ERROR: Expected pattern not found. Check data.js formatting.")
        idx = text.find('"Reliance Retail"')
        print("Context:", repr(text[idx:idx+200]))
    exit(1)

patched = text.replace(old, new, 1)
assert patched != text, "Replacement had no effect"
DATA_JS.write_text(patched, encoding="utf-8")
print("✓ data.js patched with Reliance monthly_fy26")
print(f"  Values: {fy26_vals}")
