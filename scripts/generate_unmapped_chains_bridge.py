#!/usr/bin/env python3
"""
Milestone 2: Unmapped Chains Bridge Table
Scans all records with Chain='Unmapped Chain' or similar, extracts top contributors
by Ship-To / Customer name and NSV, and generates a suggested mapping CSV for
user review and sign-off.

Output: data/unmapped_chains_bridge_suggested.csv
"""
import json, re, csv
from pathlib import Path
from collections import defaultdict
from datetime import date

# ── Load data ─────────────────────────────────────────────────────────────────
raw = open('dashboard/data.js').read()
raw = re.sub(r'^.*?window\.DASH\s*=\s*', '', raw, flags=re.DOTALL)
D = json.loads(raw.rstrip().rstrip(';'))

# ── Load allocation table (cust_article rows — has Ship-To names) ─────────────
al = D.get('alloc', {})
ca = al.get('cust_article', {})
ca_rows = ca.get('rows', [])

KNOWN_CHAINS = {
    c['name'] for c in D.get('dims', {}).get('Chain', [])
    if isinstance(c, dict) and c.get('name') and 'unmapped' not in c.get('name', '').lower()
}
# Also load from primary.by_chain
for c in D.get('primary', {}).get('by_chain', []):
    if isinstance(c, dict) and c.get('name'):
        KNOWN_CHAINS.add(c['name'])

# ── Scan detail records for unmapped ─────────────────────────────────────────
print("Scanning detail records for unmapped chain entries...")
unmapped_by_shipto = defaultdict(lambda: {'nsv': 0.0, 'qty': 0, 'months': set(), 'fys': set()})
unmapped_total_nsv = 0.0
total_unmapped_records = 0

for rec in D.get('detail_records', []):
    chain = rec.get('Chain', rec.get('chain', ''))
    if not chain or 'unmapped' not in chain.lower():
        continue
    total_unmapped_records += 1
    nsv = float(rec.get('NSV', rec.get('nsv', 0)) or 0)
    unmapped_total_nsv += nsv
    # Use Article/EAN as best available identifier in detail records
    article = rec.get('Article', rec.get('article', '')) or '(unknown)'
    brand   = rec.get('Brand', rec.get('brand', '')) or ''
    zone    = rec.get('Zone', rec.get('zone', '')) or ''
    state   = rec.get('State', rec.get('state', '')) or ''
    month   = rec.get('Month', rec.get('month', ''))
    fy      = rec.get('FY', rec.get('fy', ''))
    key = f"{zone}|{state}"
    unmapped_by_shipto[key]['nsv'] += nsv
    unmapped_by_shipto[key]['qty'] += 1
    unmapped_by_shipto[key]['months'].add(month)
    unmapped_by_shipto[key]['fys'].add(fy)
    unmapped_by_shipto[key]['brand'] = brand
    unmapped_by_shipto[key]['zone'] = zone
    unmapped_by_shipto[key]['state'] = state

# ── Scan alloc cust_article rows for Ship-To names ────────────────────────────
shipto_agg = defaultdict(lambda: {'nsv': 0.0, 'rows': 0, 'months': set(), 'brand': set()})
for row in ca_rows:
    chain = row.get('chain', '')
    if not chain or 'unmapped' not in chain.lower():
        continue
    ship_to = row.get('ship_to', '') or '(no ship_to)'
    cust    = row.get('cust_code', '') or ''
    nsv     = float(row.get('nsv', 0) or 0)
    brand   = row.get('brand', '') or ''
    month   = row.get('month', '') or ''
    key = f"{cust}|{ship_to}"
    shipto_agg[key]['nsv'] += nsv
    shipto_agg[key]['rows'] += 1
    shipto_agg[key]['months'].add(month)
    shipto_agg[key]['brand'].add(brand)
    shipto_agg[key]['cust_code'] = cust
    shipto_agg[key]['ship_to'] = ship_to

# Sort by NSV descending
sorted_shipto = sorted(shipto_agg.items(), key=lambda x: -x[1]['nsv'])

# Build coverage: top entries covering 80% of unmapped alloc NSV
total_alloc_unmapped = sum(v['nsv'] for v in shipto_agg.values())
cumulative = 0.0
top80_rows = []
for key, v in sorted_shipto:
    cumulative += v['nsv']
    cov_pct = round(cumulative / total_alloc_unmapped * 100, 1) if total_alloc_unmapped else 0
    top80_rows.append({
        'cust_code': v['cust_code'],
        'ship_to': v['ship_to'],
        'total_nsv_lakh': round(v['nsv'], 2),
        'rows_count': v['rows'],
        'months': ', '.join(sorted(v['months'])),
        'brands': ', '.join(sorted(v['brand'])),
        'cumulative_coverage_pct': cov_pct,
        'suggested_chain': '',  # for user fill-in
        'suggested_zone': '',
        'suggested_state': '',
        'confidence': 'LOW — please map manually',
        'notes': '',
    })
    if cov_pct >= 80:
        break

# ── Fuzzy suggestion: match ship_to against known chain names ─────────────────
def fuzzy_suggest(ship_to_name: str) -> str:
    name_lower = ship_to_name.lower()
    CHAIN_KEYWORDS = {
        'dmart':       'DMart', 'd-mart': 'DMart',
        'reliance':    'Reliance Smart',
        'apollo':      'Apollo Pharmacy',
        'wellness':    'Wellness Forever',
        'spencers':    "Spencer's",
        "spencer's":   "Spencer's",
        'big bazaar':  'Big Bazaar',
        'star bazaar': 'Star Bazaar',
        'more':        'More Retail',
        'spar':        'Spar',
        'lulu':        'Lulu Hypermarket',
        'jiomart':     'JioMart',
        'blinkit':     'Blinkit',
        'zepto':       'Zepto',
        'swiggy':      'Swiggy Instamart',
    }
    for keyword, chain_name in CHAIN_KEYWORDS.items():
        if keyword in name_lower:
            return chain_name
    return ''

for row in top80_rows:
    suggestion = fuzzy_suggest(row['ship_to'])
    if suggestion:
        row['suggested_chain'] = suggestion
        row['confidence'] = 'MEDIUM — fuzzy match, verify before use'

# ── Write CSV ─────────────────────────────────────────────────────────────────
Path('data').mkdir(exist_ok=True)
out_path = f"data/unmapped_chains_bridge_suggested.csv"
FIELDS = ['cust_code', 'ship_to', 'total_nsv_lakh', 'rows_count', 'months',
          'brands', 'cumulative_coverage_pct', 'suggested_chain',
          'suggested_zone', 'suggested_state', 'confidence', 'notes']

with open(out_path, 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=FIELDS)
    writer.writeheader()
    writer.writerows(top80_rows)

print(f"\n✅ Unmapped chains bridge table saved: {out_path}")
print(f"   Total unmapped detail records:   {total_unmapped_records:,}")
print(f"   Total unmapped NSV (detail):     ₹{unmapped_total_nsv:,.2f} L")
print(f"   Alloc table unmapped NSV:         ₹{total_alloc_unmapped:,.2f} L")
print(f"   Bridge rows (covering ≥80% NSV): {len(top80_rows)}")
fuzzy_hits = sum(1 for r in top80_rows if 'MEDIUM' in r['confidence'])
print(f"   Fuzzy-matched suggestions:       {fuzzy_hits}")
print(f"\n⚠️  File requires your review and sign-off before use.")
print(f"   Fill in 'suggested_chain', 'suggested_zone', 'suggested_state' columns.")
print(f"   Then run the distributor allocation build script to apply the mapping.")
