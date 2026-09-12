#!/usr/bin/env python3
"""
Milestone 2: Apply Unmapped Chain Mappings — 2-Tier Reconciliation
Reads the approved bridge CSV and applies chain mappings to reconcile
₹16,956L unmapped primary NSV into correct chain buckets.

Tier 1: 6 HIGH-confidence single-chain accounts (100% direct allocation)
Tier 2: 4 multi-chain / territory-inferred accounts (weighted split allocation)

Output:
  dashboard/enriched_metrics.json (updated with reconciled chain NSV)
  data/unmapped_reconciliation_report.json (audit trail)
"""
import json, re, csv, sys
from pathlib import Path
from datetime import date
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent))
from chain_aliases import normalize

def r2(v):
    try: return round(float(v or 0), 2)
    except: return 0.0

# ── Load data ─────────────────────────────────────────────────────────────────
raw = open('dashboard/data.js').read()
raw = re.sub(r'^.*?window\.DASH\s*=\s*', '', raw, flags=re.DOTALL)
D = json.loads(raw.rstrip().rstrip(';'))

# ── Load bridge CSV ───────────────────────────────────────────────────────────
bridge_rows = []
with open('data/unmapped_chains_bridge_suggested.csv') as f:
    bridge_rows = list(csv.DictReader(f))

# Build ship_to → mapping lookup
# For Tier 2 (weighted split), store as list of {chain, weight}
SHIP_TO_MAPPING = {}
for row in bridge_rows:
    ship_to = row['ship_to']
    chain   = row['suggested_chain']
    zone    = row['suggested_zone']
    state   = row['suggested_state']
    conf    = row['confidence']
    notes   = row['notes']

    if 'WEIGHTED SPLIT' in notes:
        # Extract the split definition sentence (stops at first ". " ending a sentence)
        import re as _re
        marker = 'WEIGHTED SPLIT: '
        split_section = ''
        if marker in notes:
            rest = notes[notes.index(marker) + len(marker):]
            # Split on ". " only when followed by an uppercase letter (next sentence)
            parts = _re.split(r'\.\s+(?=[A-Z])', rest)
            split_section = parts[0] if parts else ''
        splits = _re.findall(r'([A-Za-z &]+?)\s+([\d.]+)%', split_section)
        weights = []
        for chain_name, pct in splits:
            chain_name = chain_name.strip()
            # Skip placeholder buckets not mapped to a real chain
            if chain_name.lower() in ('other mt', 'other', 'others'):
                continue
            canon = normalize(chain_name)
            weights.append({'chain': canon, 'weight': float(pct) / 100})
        # Renormalize to 1.0 (exclude None mappings)
        total_w = sum(w['weight'] for w in weights)
        if total_w > 0:
            for w in weights:
                w['weight'] = round(w['weight'] / total_w, 4)
        SHIP_TO_MAPPING[ship_to] = {
            'type': 'weighted', 'splits': weights,
            'zone': zone, 'state': state, 'confidence': conf
        }
    else:
        SHIP_TO_MAPPING[ship_to] = {
            'type': 'direct', 'chain': normalize(chain),
            'zone': zone, 'state': state, 'confidence': conf
        }

# ── Scan alloc.cust_article for unmapped ship_to records ─────────────────────
ca = D.get('alloc', {}).get('cust_article', {})
ca_rows = ca.get('rows', [])

# Aggregate NSV by ship_to within unmapped records
unmapped_shipto_nsv = defaultdict(float)
for row in ca_rows:
    chain = row.get('chain', '')
    if not chain or 'unmapped' not in chain.lower():
        continue
    ship_to = row.get('ship_to', '') or '(no ship_to)'
    nsv = float(row.get('nsv', 0) or 0)
    unmapped_shipto_nsv[ship_to] += nsv

total_unmapped_alloc = sum(unmapped_shipto_nsv.values())

# ── Scan detail_records for unmapped FY26/FY27 chain NSV ─────────────────────
REC = D.get('detail_records', [])
FY26_F = {'FY26', 'fy26'}
FY27_F = {'FY27', 'fy27'}

unmapped_fy26 = defaultdict(float)
unmapped_fy27 = defaultdict(float)
for rec in REC:
    chain = rec.get('Chain', rec.get('chain', ''))
    if not chain or 'unmapped' not in chain.lower():
        continue
    fy  = rec.get('FY', rec.get('fy', ''))
    nsv = float(rec.get('NSV', rec.get('nsv', 0)) or 0)
    zone  = rec.get('Zone',  rec.get('zone', ''))  or 'Unknown'
    state = rec.get('State', rec.get('state', '')) or 'Unknown'
    key = (zone, state)
    if fy in FY26_F:
        unmapped_fy26[key] += nsv
    elif fy in FY27_F:
        unmapped_fy27[key] += nsv

total_unmapped_detail_fy26 = sum(unmapped_fy26.values())
total_unmapped_detail_fy27 = sum(unmapped_fy27.values())

# ── Apply mappings: compute reallocation deltas ───────────────────────────────
# We reallocate alloc NSV (which feeds the enriched_metrics chain breakdown)
# by proportionally distributing each mapped ship_to's NSV to its target chain(s)

# FY27-only deltas: FY26 is intentionally NOT mutated — primary.by_chain FY26
# is the authoritative complete figure from the pre-aggregated workbook.
chain_delta_fy27 = defaultdict(float)

reallocation_log = []
covered_nsv   = 0.0
covered_rows  = 0

for ship_to, mapping in SHIP_TO_MAPPING.items():
    ship_nsv = unmapped_shipto_nsv.get(ship_to, 0.0)
    if ship_nsv <= 0:
        continue
    covered_nsv  += ship_nsv
    covered_rows += 1

    if mapping['type'] == 'direct':
        target_chain = mapping['chain']
        chain_delta_fy27[target_chain] += ship_nsv
        reallocation_log.append({
            'ship_to': ship_to, 'type': 'DIRECT',
            'chain': target_chain, 'nsv_reallocated': round(ship_nsv, 2),
            'confidence': mapping['confidence']
        })
    else:  # weighted
        for split in mapping['splits']:
            allocated = ship_nsv * split['weight']
            chain_delta_fy27[split['chain']] += allocated
        reallocation_log.append({
            'ship_to': ship_to, 'type': 'WEIGHTED_SPLIT',
            'splits': mapping['splits'], 'nsv_reallocated': round(ship_nsv, 2),
            'confidence': mapping['confidence']
        })

residual_unmapped_nsv = total_unmapped_alloc - covered_nsv

# ── Load & update enriched_metrics.json ──────────────────────────────────────
em_path = Path('dashboard/enriched_metrics.json')
if not em_path.exists():
    print("enriched_metrics.json not found — run generate_enriched_metrics.py first")
    raise SystemExit(1)

em = json.loads(em_path.read_text())

# Update by_chain entries with reallocation deltas
# Key by canonical name so reconciliation merges into the correct bucket
chain_lookup = {normalize(c['name']): c for c in em.get('by_chain', [])}

for chain_name, delta_fy27 in chain_delta_fy27.items():
    if chain_name in chain_lookup:
        c = chain_lookup[chain_name]
        c['fy27_ytd']     = r2(c['fy27_ytd']     + delta_fy27)
        # fy26_nsv intentionally unchanged — authoritative from primary.by_chain
        c['fy27_run_rate']= r2(c['fy27_ytd'] * 12 / em['months_ytd'])
        tgt = r2(c['fy26_nsv'] * em['growth_target_pct'] / 100)
        c['fy27_tgt']     = tgt
        c['fy27_ach_pct'] = r2(c['fy27_ytd'] / tgt * 100) if tgt else None
        c['gap_vs_tgt']   = r2(c['fy27_ytd'] - tgt)
    else:
        # New chain not in primary.by_chain (alloc-only distributor chain)
        chain_lookup[chain_name] = {
            'name': chain_name,
            'fy26_nsv': 0.0,
            'fy27_ytd': r2(delta_fy27),
            'fy27_run_rate': r2(delta_fy27 * 12 / em['months_ytd']),
            'fy27_tgt': 0.0,
            'fy27_ach_pct': None,
            'gap_vs_tgt': 0,
            'pipeline_ratio_fy26': None,
            'pipeline_ratio_fy27': None,
            'pipeline_flag': None,
            'status': 'monitor',
            'monthly_fy27': {},
        }

# Reduce "Unmapped Chain" FY27 by the covered NSV (check all common variants)
# fy26_nsv for Unmapped Chain is intentionally unchanged.
for key in ('Unmapped Chain', 'unmapped chain', 'Unknown', 'Unmapped chain'):
    if key in chain_lookup:
        c = chain_lookup[key]
        c['fy27_ytd']  = r2(max(0, c['fy27_ytd']  - covered_nsv))
        c['fy27_run_rate'] = r2(c['fy27_ytd'] * 12 / em['months_ytd'])
        tgt = r2(c['fy26_nsv'] * em['growth_target_pct'] / 100)
        c['fy27_tgt']  = tgt
        c['fy27_ach_pct'] = r2(c['fy27_ytd'] / tgt * 100) if tgt else None
        c['gap_vs_tgt']   = r2(c['fy27_ytd'] - tgt)

# Re-sort chains by fy26_nsv descending; ensure canonical name on each entry
for c in chain_lookup.values():
    c['name'] = normalize(c['name'])
em['by_chain'] = sorted(chain_lookup.values(), key=lambda x: x['fy26_nsv'], reverse=True)

# Rebuild pipeline_health buckets
em['pipeline_health'] = {
    'high_risk_chains':  [c for c in em['by_chain'] if c.get('pipeline_flag') == 'high_risk'],
    'healthy_chains':    [c for c in em['by_chain'] if c.get('pipeline_flag') == 'healthy'],
    'stockout_chains':   [c for c in em['by_chain'] if c.get('pipeline_flag') == 'stockout'],
    'thresholds': {'high_risk': '>1.40', 'healthy': '0.75–1.40', 'stockout': '<0.75'},
}

em['unmapped_reconciliation'] = {
    'applied_at': date.today().isoformat(),
    'bridge_rows_applied': covered_rows,
    'nsv_reallocated_lakh': round(covered_nsv, 2),
    'residual_unmapped_nsv_lakh': round(residual_unmapped_nsv, 2),
    'coverage_pct': round(covered_nsv / total_unmapped_alloc * 100, 1) if total_unmapped_alloc else 0,
    'tier1_direct_rows': sum(1 for r in reallocation_log if r['type'] == 'DIRECT'),
    'tier2_weighted_rows': sum(1 for r in reallocation_log if r['type'] == 'WEIGHTED_SPLIT'),
}

# Save updated enriched_metrics.json
em_path.write_text(json.dumps(em, indent=2))

# ── Write audit report ────────────────────────────────────────────────────────
report = {
    'generated_at': date.today().isoformat(),
    'summary': {
        'total_unmapped_alloc_nsv': round(total_unmapped_alloc, 2),
        'total_unmapped_detail_fy26_nsv': round(total_unmapped_detail_fy26, 2),
        'total_unmapped_detail_fy27_nsv': round(total_unmapped_detail_fy27, 2),
        'bridge_rows_in_csv': len(SHIP_TO_MAPPING),
        'bridge_rows_matched_in_alloc': covered_rows,
        'nsv_covered': round(covered_nsv, 2),
        'nsv_residual_unmapped': round(residual_unmapped_nsv, 2),
        'coverage_pct': round(covered_nsv / total_unmapped_alloc * 100, 1) if total_unmapped_alloc else 0,
    },
    'chain_deltas_fy27': {k: round(v, 2) for k, v in sorted(chain_delta_fy27.items(), key=lambda x: -x[1])},
    'reallocation_log': reallocation_log,
}
Path('data').mkdir(exist_ok=True)
report_path = 'data/unmapped_reconciliation_report.json'
with open(report_path, 'w') as f:
    json.dump(report, f, indent=2)

print(f"✅ Unmapped chain reconciliation complete")
print(f"   Total unmapped alloc NSV:     ₹{total_unmapped_alloc:,.2f} L")
print(f"   NSV reallocated (bridge):     ₹{covered_nsv:,.2f} L  ({round(covered_nsv/total_unmapped_alloc*100,1) if total_unmapped_alloc else 0}% coverage)")
print(f"   Residual unmapped:            ₹{residual_unmapped_nsv:,.2f} L")
print(f"   Tier 1 (direct) rows:         {sum(1 for r in reallocation_log if r['type']=='DIRECT')}")
print(f"   Tier 2 (weighted) rows:       {sum(1 for r in reallocation_log if r['type']=='WEIGHTED_SPLIT')}")
print(f"\n   Chain NSV deltas (FY27, ₹L):")
for ch, delta in sorted(chain_delta_fy27.items(), key=lambda x: -x[1]):
    print(f"     + {ch}: ₹{delta:,.2f} L")
print(f"\n✅ enriched_metrics.json updated: dashboard/enriched_metrics.json")
print(f"✅ Audit report saved:            {report_path}")
