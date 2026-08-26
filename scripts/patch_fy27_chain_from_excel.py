#!/usr/bin/env python3
"""
Fix D: Patch primary.by_chain FY27 in data.js using the authoritative
Chain_Wise_Primary_Sale.xlsx (₹18,581L full 4-month FY27 picture).

Also:
  - Normalises all chain names in primary.by_chain to canonical form
  - Merges duplicate canonical entries (e.g. Dmart + DMart → DMart)
  - Updates primary.nsv_fy27 to match the Excel grand total
  - Recalculates yoy per chain

Usage:
  python3 scripts/patch_fy27_chain_from_excel.py \
      --excel /path/to/Chain_Wise_Primary_Sale.xlsx \
      --out dashboard/data.js

Default excel path: /root/.claude/uploads/55682d72.../Chain_Wise_Primary_Sale.xlsx
"""
import argparse, json, re, sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from chain_aliases import normalize

try:
    import openpyxl
except ImportError:
    sys.exit("pip install openpyxl required")

DEFAULT_EXCEL = ('/root/.claude/uploads/55682d72-6b69-5e1a-b307-5d5ff59817ad'
                 '/bc91b3cc-Chain_Wise_Primary_Sale.xlsx')
DEFAULT_OUT   = 'dashboard/data.js'

def r2(v):
    try: return round(float(v or 0), 2)
    except: return 0.0

# ── CLI ────────────────────────────────────────────────────────────────────────
ap = argparse.ArgumentParser()
ap.add_argument('--excel', default=DEFAULT_EXCEL)
ap.add_argument('--out',   default=DEFAULT_OUT)
args = ap.parse_args()

excel_path = Path(args.excel)
out_path   = Path(args.out)

if not excel_path.exists():
    sys.exit(f"Excel not found: {excel_path}")
if not out_path.exists():
    sys.exit(f"data.js not found: {out_path}")

# ── Read Excel: Dump sheet ──────────────────────────────────────────────────
wb = openpyxl.load_workbook(str(excel_path), data_only=True)
ws = wb['Dump']

xl_chain_fy = defaultdict(float)   # (canonical_chain, fy_tag) → NSV
xl_chain_fy26, xl_chain_fy27 = defaultdict(float), defaultdict(float)

FY_MAP = {'FY_24-25': 'FY25', 'FY_25-26': 'FY26', 'FY_26-27': 'FY27'}

for row in ws.iter_rows(min_row=3, values_only=True):
    if row[0] is None:
        continue
    raw_chain = (row[4] or '').strip()
    if not raw_chain:
        continue
    chain = normalize(raw_chain)
    fy_raw = FY_MAP.get(row[12], '')
    nsv    = float(row[7] or 0)
    xl_chain_fy[(chain, fy_raw)] += nsv
    if fy_raw == 'FY26':
        xl_chain_fy26[chain] += nsv
    elif fy_raw == 'FY27':
        xl_chain_fy27[chain] += nsv

xl_fy27_total = r2(sum(xl_chain_fy27.values()))
print(f"Excel chains: {len(xl_chain_fy27)}  FY27 total: ₹{xl_fy27_total:,.2f}L")

# ── Load data.js ───────────────────────────────────────────────────────────────
raw_js   = out_path.read_text(encoding='utf-8')
prefix   = re.match(r'^.*?window\.DASH\s*=\s*', raw_js, flags=re.DOTALL)
if not prefix:
    sys.exit("Could not find 'window.DASH =' in data.js")
json_start = prefix.end()
json_body  = raw_js[json_start:].rstrip().rstrip(';')
D = json.loads(json_body)

primary = D['primary']

# ── Normalize & merge existing primary.by_chain ────────────────────────────────
merged_fy26: dict[str, float] = defaultdict(float)
merged_fy27: dict[str, float] = defaultdict(float)

for entry in primary.get('by_chain', []):
    canon = normalize(entry['name'])
    merged_fy26[canon] += r2(entry.get('fy26', 0) or 0)
    merged_fy27[canon] += r2(entry.get('fy27', 0) or 0)  # old partial FY27

print(f"\nBefore patch — primary.by_chain chains: {len(merged_fy26)}")
print(f"  FY26 total: ₹{sum(merged_fy26.values()):,.2f}L")
print(f"  FY27 total (pre-agg only): ₹{sum(merged_fy27.values()):,.2f}L")

# ── Apply Excel FY27 values ───────────────────────────────────────────────────
# Start from existing FY26 chain universe (guaranteed complete + correct)
# Override/set FY27 from Excel for every chain that appears there.
# Chains only in Excel FY27 (not in FY26 pre-agg) are added as new entries.

all_canon_chains = sorted(
    set(merged_fy26.keys()) | set(xl_chain_fy27.keys())
)

new_by_chain = []
for canon in all_canon_chains:
    fy26 = r2(merged_fy26.get(canon, 0))
    fy27 = r2(xl_chain_fy27.get(canon, merged_fy27.get(canon, 0)))
    yoy  = r2((fy27 - fy26) / fy26 * 100) if fy26 else None
    new_by_chain.append({'name': canon, 'fy26': fy26, 'fy27': fy27, 'yoy': yoy})

# Sort by FY26 NSV descending
new_by_chain.sort(key=lambda x: x['fy26'], reverse=True)

# ── Update primary block ───────────────────────────────────────────────────────
primary['by_chain']  = new_by_chain
primary['nsv_fy27']  = r2(xl_fy27_total)
primary['n_chains']  = len(new_by_chain)

print(f"\nAfter patch — primary.by_chain chains: {len(new_by_chain)}")
print(f"  FY26 total: ₹{sum(c['fy26'] for c in new_by_chain):,.2f}L")
print(f"  FY27 total (Excel-authoritative): ₹{sum(c['fy27'] for c in new_by_chain):,.2f}L")

# ── Show top-chain comparison ─────────────────────────────────────────────────
print()
print(f"{'Chain':<30} {'FY26':>10} {'FY27':>10} {'YoY%':>8}")
print('-' * 62)
for c in new_by_chain[:15]:
    yoy_str = f"{c['yoy']:>8.1f}%" if c['yoy'] is not None else '       –%'
    print(f"  {c['name']:<28} {c['fy26']:>10.2f} {c['fy27']:>10.2f} {yoy_str}")

# ── Write back data.js ─────────────────────────────────────────────────────────
new_json = json.dumps(D, ensure_ascii=False, separators=(',', ':'))
new_js   = raw_js[:json_start] + new_json + ';'
out_path.write_text(new_js, encoding='utf-8')

print(f"\n✅ data.js patched: primary.by_chain FY27 updated from Excel")
print(f"   Chains: {len(new_by_chain)}")
print(f"   primary.nsv_fy27 updated: ₹{primary['nsv_fy27']:,.2f}L")
print(f"   Verify FY26 unchanged:    ₹{primary['nsv_fy26']:,.2f}L")
