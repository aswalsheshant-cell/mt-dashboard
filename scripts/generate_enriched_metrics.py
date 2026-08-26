#!/usr/bin/env python3
"""
Milestone 2: Generate dashboard/enriched_metrics.json
Pre-aggregates Primary NSV, Offtake, Pipeline Ratio, TGT vs ACH, and MoM/YoY
trajectories by Zone, Chain, and Category for use by the PPTX generator and
any downstream analytics scripts.
"""
import json, re
from pathlib import Path
from datetime import date

# ── Load DASH ────────────────────────────────────────────────────────────────
raw = open('dashboard/data.js').read()
raw = re.sub(r'^.*?window\.DASH\s*=\s*', '', raw, flags=re.DOTALL)
D = json.loads(raw.rstrip().rstrip(';'))

def r2(v):
    try: return round(float(v or 0), 2)
    except: return 0.0

# ── Detail records aggregation ────────────────────────────────────────────────
def agg_detail(records, group_key, fy_filter=None):
    result = {}
    for rec in records:
        fy = rec.get('FY', rec.get('fy', ''))
        if fy_filter and fy not in fy_filter:
            continue
        key = rec.get(group_key, '') or 'Unknown'
        nsv = float(rec.get('NSV', rec.get('nsv', 0)) or 0)
        qty = float(rec.get('Qty', rec.get('qty', 0)) or 0)
        if key not in result:
            result[key] = {'nsv': 0.0, 'qty': 0.0}
        result[key]['nsv'] += nsv
        result[key]['qty'] += qty
    return {k: {'nsv': r2(v['nsv']), 'qty': r2(v['qty'])} for k, v in result.items()}

REC = D.get('detail_records', [])
FY26_FILTER = {'FY26', 'fy26'}
FY27_FILTER = {'FY27', 'fy27'}

# Primary NSV by dimension
primary_fy26_zone    = agg_detail(REC, 'Zone',     FY26_FILTER)
primary_fy27_zone    = agg_detail(REC, 'Zone',     FY27_FILTER)
primary_fy26_chain   = agg_detail(REC, 'Chain',    FY26_FILTER)
primary_fy27_chain   = agg_detail(REC, 'Chain',    FY27_FILTER)
primary_fy26_brand   = agg_detail(REC, 'Brand',    FY26_FILTER)
primary_fy27_brand   = agg_detail(REC, 'Brand',    FY27_FILTER)
primary_fy26_cat     = agg_detail(REC, 'Category', FY26_FILTER)
primary_fy27_cat     = agg_detail(REC, 'Category', FY27_FILTER)

# Offtake by dimension
offtake_data = D.get('offtake', {})
offtake_fy26_total = r2(offtake_data.get('total_fy26', 0))
offtake_fy27_total = r2(offtake_data.get('total_fy27', 0))
offtake_fy26_chain = {c['name']: r2(c.get('fy26', 0) or 0)
                      for c in offtake_data.get('by_chain', []) if isinstance(c, dict)}
offtake_fy27_chain = {c['name']: r2(c.get('fy27', 0) or 0)
                      for c in offtake_data.get('by_chain', []) if isinstance(c, dict)}

# ── Monthly trends (FY27 months covered) ─────────────────────────────────────
fyx = D.get('detail_meta', {}).get('fyx_primary', {}).get('FY27', {})
months_covered = fyx.get('months_covered', [])

monthly_fy27_zone = {}
monthly_fy27_chain = {}
for rec in REC:
    fy = rec.get('FY', rec.get('fy', ''))
    if fy not in FY27_FILTER:
        continue
    month = rec.get('Month', rec.get('month', ''))
    zone  = rec.get('Zone', rec.get('zone', '')) or 'Unknown'
    chain = rec.get('Chain', rec.get('chain', '')) or 'Unknown'
    nsv   = float(rec.get('NSV', rec.get('nsv', 0)) or 0)

    if zone not in monthly_fy27_zone:
        monthly_fy27_zone[zone] = {}
    monthly_fy27_zone[zone][month] = monthly_fy27_zone[zone].get(month, 0) + nsv

    if chain not in monthly_fy27_chain:
        monthly_fy27_chain[chain] = {}
    monthly_fy27_chain[chain][month] = monthly_fy27_chain[chain].get(month, 0) + nsv

# Round
for dim in [monthly_fy27_zone, monthly_fy27_chain]:
    for k in dim:
        dim[k] = {m: r2(v) for m, v in dim[k].items()}

# ── Pipeline Ratio & TGT vs ACH ───────────────────────────────────────────────
GROWTH_TGT = 1.20  # 20% growth target over FY26 as FY27 target proxy
MONTHS_YTD = 4     # Apr–Jul'26 = 4 months

def pipeline_entry(name, p26, p27_ytd, o26, o27):
    tgt = r2(p26 * GROWTH_TGT)
    ach_pct = r2(p27_ytd / tgt * 100) if tgt else None
    run_rate = r2(p27_ytd * 12 / MONTHS_YTD)
    pip_fy26 = r2(p26 / o26) if o26 else None
    pip_fy27 = r2(p27_ytd / o27) if o27 else None
    status = ('on_track' if (ach_pct or 0) >= 80 else
              'monitor'  if (ach_pct or 0) >= 60 else 'escalate')
    pip_flag = (None if pip_fy27 is None else
                'high_risk' if pip_fy27 > 1.40 else
                'stockout'  if pip_fy27 < 0.75 else 'healthy')
    return {
        'name': name,
        'fy26_nsv': r2(p26),
        'fy27_ytd': r2(p27_ytd),
        'fy27_run_rate': run_rate,
        'fy27_tgt': tgt,
        'fy27_ach_pct': ach_pct,
        'gap_vs_tgt': r2(p27_ytd - tgt),
        'pipeline_ratio_fy26': pip_fy26,
        'pipeline_ratio_fy27': pip_fy27,
        'pipeline_flag': pip_flag,
        'status': status,
    }

# Zone-level pipeline
zone_pipeline = []
all_zones = sorted(set(list(primary_fy26_zone.keys()) + list(primary_fy27_zone.keys())))
for z in all_zones:
    p26 = primary_fy26_zone.get(z, {}).get('nsv', 0)
    p27 = primary_fy27_zone.get(z, {}).get('nsv', 0)
    o26_z = sum(c.get('fy26', 0) or 0 for c in offtake_data.get('by_zone', [])
                if isinstance(c, dict) and c.get('name') == z)
    o27_z = sum(c.get('fy27', 0) or 0 for c in offtake_data.get('by_zone', [])
                if isinstance(c, dict) and c.get('name') == z)
    entry = pipeline_entry(z, p26, p27, o26_z, o27_z)
    entry['monthly_fy27'] = monthly_fy27_zone.get(z, {})
    zone_pipeline.append(entry)

# Chain-level pipeline
chain_pipeline = []
all_chains = sorted(set(list(primary_fy26_chain.keys()) + list(primary_fy27_chain.keys())))
for ch in all_chains:
    p26 = primary_fy26_chain.get(ch, {}).get('nsv', 0)
    p27 = primary_fy27_chain.get(ch, {}).get('nsv', 0)
    o26_c = offtake_fy26_chain.get(ch, 0)
    o27_c = offtake_fy27_chain.get(ch, 0)
    entry = pipeline_entry(ch, p26, p27, o26_c, o27_c)
    entry['monthly_fy27'] = monthly_fy27_chain.get(ch, {})
    chain_pipeline.append(entry)
chain_pipeline.sort(key=lambda x: x['fy26_nsv'], reverse=True)

# Category-level
cat_pipeline = []
for cat in sorted(set(list(primary_fy26_cat.keys()) + list(primary_fy27_cat.keys()))):
    p26 = primary_fy26_cat.get(cat, {}).get('nsv', 0)
    p27 = primary_fy27_cat.get(cat, {}).get('nsv', 0)
    cat_pipeline.append(pipeline_entry(cat, p26, p27, 0, 0))
cat_pipeline.sort(key=lambda x: x['fy26_nsv'], reverse=True)

# ── YoY Summary ───────────────────────────────────────────────────────────────
p_total = D.get('primary', {})
primary_fy25_total = r2(p_total.get('nsv_fy25', 0))
primary_fy26_total = r2(p_total.get('nsv_fy26', 0))
primary_fy27_total = r2(sum(v.get('nsv', 0) for v in primary_fy27_zone.values()))

yoy_fy26 = r2((primary_fy26_total - primary_fy25_total) / primary_fy25_total * 100) if primary_fy25_total else None
yoy_fy27_ytd_vs_fy26_ytd = None  # would need FY26 Apr-Jul subset

# ── Unmapped chains ───────────────────────────────────────────────────────────
unmapped_detail = []
for ch, v in sorted(primary_fy27_chain.items(), key=lambda x: -x[1].get('nsv', 0)):
    if 'unmapped' in ch.lower() or 'unknown' in ch.lower():
        unmapped_detail.append({'chain': ch, 'fy27_ytd_nsv': v['nsv'], 'fy26_nsv': primary_fy26_chain.get(ch, {}).get('nsv', 0)})

# ── Compile ───────────────────────────────────────────────────────────────────
out = {
    'generated_at': date.today().isoformat(),
    'data_source': 'dashboard/data.js (window.DASH)',
    'fy27_period': f"{months_covered[0]} – {months_covered[-1]}" if len(months_covered) >= 2 else (months_covered[0] if months_covered else 'Apr–Jul 2026'),
    'months_covered': months_covered,
    'months_ytd': MONTHS_YTD,
    'growth_target_pct': GROWTH_TGT * 100,

    'topline': {
        'primary_fy25': primary_fy25_total,
        'primary_fy26': primary_fy26_total,
        'primary_fy27_ytd': primary_fy27_total,
        'offtake_fy26': offtake_fy26_total,
        'offtake_fy27_ytd': offtake_fy27_total,
        'yoy_fy26_pct': yoy_fy26,
        'pipeline_ratio_fy26': r2(primary_fy26_total / offtake_fy26_total) if offtake_fy26_total else None,
        'pipeline_ratio_fy27': r2(primary_fy27_total / offtake_fy27_total) if offtake_fy27_total else None,
    },

    'by_zone': zone_pipeline,
    'by_chain': chain_pipeline,
    'by_category': cat_pipeline,

    'by_brand': [
        {
            'name': b,
            'fy26_nsv': primary_fy26_brand.get(b, {}).get('nsv', 0),
            'fy27_ytd': primary_fy27_brand.get(b, {}).get('nsv', 0),
        }
        for b in sorted(set(list(primary_fy26_brand.keys()) + list(primary_fy27_brand.keys())))
    ],

    'unmapped_chains': unmapped_detail,

    'pipeline_health': {
        'high_risk_chains':  [c for c in chain_pipeline if c.get('pipeline_flag') == 'high_risk'],
        'healthy_chains':    [c for c in chain_pipeline if c.get('pipeline_flag') == 'healthy'],
        'stockout_chains':   [c for c in chain_pipeline if c.get('pipeline_flag') == 'stockout'],
        'thresholds': {'high_risk': '>1.40', 'healthy': '0.75–1.40', 'stockout': '<0.75'},
    },
}

Path('dashboard').mkdir(exist_ok=True)
out_path = 'dashboard/enriched_metrics.json'
with open(out_path, 'w') as f:
    json.dump(out, f, indent=2)

print(f"✅ enriched_metrics.json generated: {out_path}")
print(f"   Zones: {len(zone_pipeline)}  Chains: {len(chain_pipeline)}  Categories: {len(cat_pipeline)}")
print(f"   FY26 Primary NSV: ₹{primary_fy26_total:,.2f} L")
print(f"   FY27 YTD NSV:     ₹{primary_fy27_total:,.2f} L")
print(f"   Pipeline Ratio FY26: {out['topline']['pipeline_ratio_fy26']}")
print(f"   Pipeline Ratio FY27: {out['topline']['pipeline_ratio_fy27']}")
hr = out['pipeline_health']['high_risk_chains']
print(f"   High-risk chains (ratio>1.40): {len(hr)} — {[c['name'] for c in hr[:5]]}")
