import csv

def load(fn, nkey, nmonths):
    rows = []
    with open(fn) as f:
        r = list(csv.reader(f, delimiter='\t'))
    hdr = r[0]
    for row in r[1:]:
        if not any(row):
            continue
        key = tuple(row[:nkey])
        vals = []
        for j in range(nmonths):
            x = row[nkey + j].strip() if nkey + j < len(row) else ''
            vals.append(float(x) if x not in ('', None) else 0.0)
        rows.append((key, vals, hdr[nkey:nkey+nmonths]))
    return hdr, rows

# Primary: Channel, Zone, Chain, Apr-25..Jun-26 (15 months)
phdr, prows = load('data/primary_zone_chain.tsv', 3, 15)
# Offtake corrected monthly: Channel, Chain, Zone, Apr-25..Jun-26 (15 months)
ohdr, orows = load('data2/offtake_chain_zone_monthly_corrected.tsv', 3, 15)

M15 = ['Apr-25','May-25','Jun-25','Jul-25','Aug-25','Sep-25','Oct-25','Nov-25','Dec-25','Jan-26','Feb-26','Mar-26','Apr-26','May-26','Jun-26']
def q1fy27(vals):
    i = M15.index('Apr-26')
    return sum(vals[i:i+3])
def jun26(vals):
    return vals[M15.index('Jun-26')]

# ---- CONFIRMED chain-name mapping: primary variant(s) -> offtake canonical ----
CONFIRMED = {
    'Dmart': ['D-Mart'],
    'Reliance': ['Reliance Retail', 'Reliance Retail-(Azorte)'],
    'Apollo': ['Apollo Healthco'],
    'Metro Cnc': ['Metro-CNC-RRL'],
    'Walmart Cnc': ['Walmart CNC'],
    'Vmm': ['VMM'],
    'Wh-Smith': ['WH-Smith'],
    'Ratandeep': ['Ratnadeep'],
    'Sancus(Rmt)': ['RMT-Sancus'],
    'Sasta Sundar': ['Sasta Sunder'],
    'Sohum': ['Sohum Shoppe'],
    'Frankros': ['Frankross'],
    'Fsn': ['Nykaa SS(fsn)'],
    'Apna Mart': ['Apna Mart'],
    'Arambagh': ['Arambagh'],
    'Guardian': ['Guardian'],
    'H&G': ['H&G'],
    'Lulu': ['Lulu'],
    'More Retail': ['More Retail'],
    'National Mart': ['National Mart'],
    'Spencer': ['Spencer'],
    'Sumo Save': ['Sumo Save'],
    'Trent': ['Trent'],
    'V-Mart': ['V-Mart'],
    'Vijetha': ['Vijetha'],
    'Wellness Forever': ['Wellness Forever'],
}
PROBABLE = { 'BEAUTY & NUTRIE': ['B&N'] }

primary_chain_names = set(k[2] for k, v, h in prows)
offtake_chain_names = set(k[1] for k, v, h in orows)

mapped_primary_variants = set()
for variants in list(CONFIRMED.values()) + list(PROBABLE.values()):
    mapped_primary_variants.update(variants)
unmapped_primary = sorted(primary_chain_names - mapped_primary_variants)
unmapped_offtake = sorted(offtake_chain_names - set(CONFIRMED.keys()) - set(PROBABLE.keys()))
print('UNMAPPED PRIMARY CHAINS:', unmapped_primary)
print('UNMAPPED OFFTAKE CHAINS:', unmapped_offtake)
print()

def primary_sum_for(variants, month_fn):
    return sum(month_fn(v) for k, v, h in prows if k[2] in variants)

def offtake_sum_for(canon, month_fn):
    return sum(month_fn(v) for k, v, h in orows if k[1] == canon)

print('=== CHAIN / KAM LEVEL (Confirmed mapping only) — Jun-26 & Q1 FY27 (Rs Lacs) ===')
chain_results = {}
for canon, variants in CONFIRMED.items():
    p_jun = primary_sum_for(variants, jun26)
    o_jun = offtake_sum_for(canon, jun26)
    p_q1 = primary_sum_for(variants, q1fy27)
    o_q1 = offtake_sum_for(canon, q1fy27)
    so_jun = (o_jun/p_jun*100) if p_jun else None
    so_q1 = (o_q1/p_q1*100) if p_q1 else None
    chain_results[canon] = dict(primary_jun=p_jun, offtake_jun=o_jun, sellout_jun=so_jun,
                                 primary_q1=p_q1, offtake_q1=o_q1, sellout_q1=so_q1)
    print(f'{canon:15s} Jun Primary={p_jun:8.1f} Jun Offtake={o_jun:8.1f} SellOut%={so_jun if so_jun is None else round(so_jun,1)!s:>7}  '
          f'Q1 Primary={p_q1:8.1f} Q1 Offtake={o_q1:8.1f} SellOut%={so_q1 if so_q1 is None else round(so_q1,1)!s:>7}')

print()
print('=== EXECUTIVE LEVEL (matched-universe apples-to-apples) ===')
all_variants = set()
for v in CONFIRMED.values(): all_variants.update(v)
matched_primary_jun = sum(jun26(v) for k, v, h in prows if k[2] in all_variants)
matched_offtake_jun = sum(jun26(v) for k, v, h in orows if k[1] in CONFIRMED)
matched_primary_q1 = sum(q1fy27(v) for k, v, h in prows if k[2] in all_variants)
matched_offtake_q1 = sum(q1fy27(v) for k, v, h in orows if k[1] in CONFIRMED)
print(f'Matched-universe ({len(CONFIRMED)} chains) Jun-26: Primary={matched_primary_jun:.1f} Offtake={matched_offtake_jun:.1f} SellOut%={matched_offtake_jun/matched_primary_jun*100:.1f}')
print(f'Matched-universe ({len(CONFIRMED)} chains) Q1 FY27: Primary={matched_primary_q1:.1f} Offtake={matched_offtake_q1:.1f} SellOut%={matched_offtake_q1/matched_primary_q1*100:.1f}')

all_primary_jun = sum(jun26(v) for k, v, h in prows)
all_offtake_jun = sum(jun26(v) for k, v, h in orows)
all_primary_q1 = sum(q1fy27(v) for k, v, h in prows)
all_offtake_q1 = sum(q1fy27(v) for k, v, h in orows)
print(f'Full-universe (all chains, reference only) Jun-26: Primary={all_primary_jun:.1f} Offtake={all_offtake_jun:.1f}')
print(f'Full-universe (all chains, reference only) Q1 FY27: Primary={all_primary_q1:.1f} Offtake={all_offtake_q1:.1f}')
print(f'# distinct primary chains={len(primary_chain_names)}, # distinct offtake chains={len(offtake_chain_names)}')

print()
print('=== ZONE LEVEL (5 common zones; Pan India/FSN excluded — no primary zone equivalent) ===')
ZONES_PRIMARY = ['East','North','South-1','South-2','West']
ZONES_OFFTAKE = ['EAST','NORTH','SOUTH-1','SOUTH-2','WEST']
zone_results = {}
for zp, zo in zip(ZONES_PRIMARY, ZONES_OFFTAKE):
    p_jun = sum(jun26(v) for k, v, h in prows if k[1] == zp)
    o_jun = sum(jun26(v) for k, v, h in orows if k[2] == zo)
    p_q1 = sum(q1fy27(v) for k, v, h in prows if k[1] == zp)
    o_q1 = sum(q1fy27(v) for k, v, h in orows if k[2] == zo)
    so_jun = o_jun/p_jun*100 if p_jun else None
    so_q1 = o_q1/p_q1*100 if p_q1 else None
    zone_results[zp] = dict(primary_jun=p_jun, offtake_jun=o_jun, sellout_jun=so_jun, primary_q1=p_q1, offtake_q1=o_q1, sellout_q1=so_q1)
    print(f'{zp:10s} Jun Primary={p_jun:8.1f} Jun Offtake={o_jun:8.1f} SellOut%={so_jun:6.1f}  Q1 Primary={p_q1:8.1f} Q1 Offtake={o_q1:8.1f} SellOut%={so_q1:6.1f}')

import json
out = {
    'chain': chain_results,
    'zone': zone_results,
    'exec': {
        'matched_primary_jun': matched_primary_jun, 'matched_offtake_jun': matched_offtake_jun,
        'matched_primary_q1': matched_primary_q1, 'matched_offtake_q1': matched_offtake_q1,
        'all_primary_jun': all_primary_jun, 'all_offtake_jun': all_offtake_jun,
        'all_primary_q1': all_primary_q1, 'all_offtake_q1': all_offtake_q1,
        'n_primary_chains': len(primary_chain_names), 'n_offtake_chains': len(offtake_chain_names),
    },
    'unmapped_primary': unmapped_primary,
    'unmapped_offtake': unmapped_offtake,
}
with open('calc3_sellout.json','w') as f:
    json.dump(out, f, indent=2)
print('\nwritten calc3_sellout.json')
