#!/usr/bin/env python3
"""Compute all Jun'26 + Q1 FY27 KPIs for the MT Offtake leadership deck from transcribed TSVs."""
import csv, json, os
D = os.path.join(os.path.dirname(__file__), 'data')
M15 = ['Apr-25','May-25','Jun-25','Jul-25','Aug-25','Sep-25','Oct-25','Nov-25','Dec-25','Jan-26','Feb-26','Mar-26','Apr-26','May-26','Jun-26']

def load(fn, nkey):
    rows = []
    with open(os.path.join(D, fn)) as f:
        r = csv.reader(f, delimiter='\t'); hdr = next(r)
        for line in r:
            if not line or not line[0]: continue
            vals = [float(x) if x.strip() else 0.0 for x in line[nkey:]]
            vals += [0.0] * (len(hdr) - nkey - len(vals))
            rows.append((tuple(line[:nkey]), vals))
    return rows

OCZ = load('offtake_chain_zone.tsv', 3)          # (channel, chain, zone)
OBZ = load('offtake_brand_subcat_zone.tsv', 4)   # (channel, brand, subcat, zone)
PZC = load('primary_zone_chain.tsv', 3)          # (channel, zone, chain)

i = {m: k for k, m in enumerate(M15)}
JUN26, MAY26, APR26, JUN25, MAY25 = i['Jun-26'], i['May-26'], i['Apr-26'], i['Jun-25'], i['May-25']

def agg(rows, pred):
    out = [0.0]*15
    for k, v in rows:
        if pred(k):
            for j in range(15): out[j] += v[j]
    return out

def pct(new, old):
    return None if old == 0 else (new/old - 1) * 100

def l3m(series, idx):  # trailing 3 months BEFORE idx (deck convention: L3M avg excludes current month)
    return sum(series[idx-3:idx]) / 3

def growth_pack(series, idx=JUN26):
    cur = series[idx]
    return {
        'cur': cur, 'prev': series[idx-1], 'yoy_base': series[idx-12],
        'mom': pct(cur, series[idx-1]), 'goly': pct(cur, series[idx-12]),
        'l3m': l3m(series, idx), 'go_l3m': pct(cur, l3m(series, idx)),
    }

R = {}
# ---------- overall ----------
total = agg(OCZ, lambda k: True)
R['total'] = {'series': total, **growth_pack(total)}
q1_27 = sum(total[APR26:JUN26+1]); q1_26 = sum(total[0:3])
R['q1'] = {'fy27': q1_27, 'fy26': q1_26, 'growth': pct(q1_27, q1_26)}

# ---------- zones (MT zones + Pan India=EB2B) ----------
ZONES = ['EAST','NORTH','SOUTH-1','SOUTH-2','WEST']
R['zones'] = {}
for z in ZONES:
    s = agg(OCZ, lambda k, z=z: k[2] == z)
    R['zones'][z] = {'series': s, **growth_pack(s),
                     'share_jun': s[JUN26]/total[JUN26]*100,
                     'q1_27': sum(s[APR26:JUN26+1]), 'q1_26': sum(s[0:3])}
pan = agg(OCZ, lambda k: k[0] == 'EB2B')
R['zones']['PAN INDIA'] = {'series': pan, **growth_pack(pan),
                           'share_jun': pan[JUN26]/total[JUN26]*100,
                           'q1_27': sum(pan[APR26:JUN26+1]), 'q1_26': sum(pan[0:3])}

# ---------- chains (pan-channel) ----------
chains = sorted({k[1] for k, _ in OCZ})
R['chains'] = {}
for c in chains:
    s = agg(OCZ, lambda k, c=c: k[1] == c)
    if max(abs(x) for x in s) == 0: continue
    R['chains'][c] = {'series': s, **growth_pack(s),
                      'share_jun': s[JUN26]/total[JUN26]*100,
                      'q1_27': sum(s[APR26:JUN26+1]), 'q1_26': sum(s[0:3])}

# ---------- chains within zone ----------
R['zone_chains'] = {}
for z in ZONES:
    zc = {}
    for c in chains:
        s = agg(OCZ, lambda k, c=c, z=z: k[1] == c and k[2] == z)
        if max(abs(x) for x in s) == 0: continue
        zc[c] = {'series': s, **growth_pack(s)}
    R['zone_chains'][z] = zc

# ---------- brands (offtake, MT+EB2B) ----------
brands = sorted({k[1] for k, _ in OBZ})
R['brands'] = {}
for b in brands:
    s = agg(OBZ, lambda k, b=b: k[1] == b)
    R['brands'][b] = {'series': s, **growth_pack(s),
                      'share_jun': s[JUN26]/total[JUN26]*100,
                      'q1_27': sum(s[APR26:JUN26+1]), 'q1_26': sum(s[0:3])}
emerg = agg(OBZ, lambda k: k[1] not in ('Mamaearth','The Derma Co.','Aqualogica'))
R['brands']['Emerging Brands'] = {'series': emerg, **growth_pack(emerg),
                                  'share_jun': emerg[JUN26]/total[JUN26]*100,
                                  'q1_27': sum(emerg[APR26:JUN26+1]), 'q1_26': sum(emerg[0:3])}

# ---------- brand x subcat (overall = MT + EB2B) ----------
R['brand_subcat'] = {}
for (b, sc) in sorted({(k[1], k[2]) for k, _ in OBZ}):
    s = agg(OBZ, lambda k, b=b, sc=sc: k[1] == b and k[2] == sc)
    R['brand_subcat'][f'{b}|{sc}'] = {'series': s, **growth_pack(s)}

# ---------- brand x subcat x zone (for zone slides; Pan India = EB2B) ----------
R['zone_brand_subcat'] = {}
for z in ZONES + ['Pan India']:
    zd = {}
    for (b, sc) in sorted({(k[1], k[2]) for k, _ in OBZ if k[3] == z}):
        s = agg(OBZ, lambda k, b=b, sc=sc, z=z: k[1] == b and k[2] == sc and k[3] == z)
        zd[f'{b}|{sc}'] = {'series': s, **growth_pack(s)}
    R['zone_brand_subcat'][z] = zd

# ---------- brands within zone ----------
R['zone_brands'] = {}
for z in ZONES + ['Pan India']:
    zd = {}
    for b in ['Mamaearth', 'The Derma Co.', 'Aqualogica']:
        s = agg(OBZ, lambda k, b=b, z=z: k[1] == b and k[3] == z)
        zd[b] = {'series': s, **growth_pack(s)}
    s = agg(OBZ, lambda k, z=z: k[3] == z and k[1] not in ('Mamaearth','The Derma Co.','Aqualogica'))
    zd['Emerging Brands'] = {'series': s, **growth_pack(s)}
    zd['_zone_total'] = {'series': agg(OBZ, lambda k, z=z: k[3] == z)}
    R['zone_brand_totals' if False else 'zone_brands'][z] = zd

# ---------- primary ----------
prim_total = agg(PZC, lambda k: True)
R['primary_total'] = {'series': prim_total, **growth_pack(prim_total),
                      'q1_27': sum(prim_total[APR26:JUN26+1]), 'q1_26': sum(prim_total[0:3])}
R['primary_zones'] = {}
for z in ['East','North','South-1','South-2','West']:
    s = agg(PZC, lambda k, z=z: k[1] == z and k[0] != 'EB2B')
    R['primary_zones'][z] = {'series': s, **growth_pack(s)}

with open(os.path.join(os.path.dirname(__file__), 'calc.json'), 'w') as f:
    json.dump(R, f, indent=1)

# ---------- console summary ----------
def fp(x): return 'n/a' if x is None else f'{x:+.0f}%'
t = R['total']
print(f"OVERALL Jun'26: {t['cur']:.0f} L | MoM {fp(t['mom'])} | GOLY {fp(t['goly'])} | L3M {t['l3m']:.0f} | GO L3M {fp(t['go_l3m'])}")
print(f"Q1 FY27 {q1_27:.0f} vs Q1 FY26 {q1_26:.0f} => {fp(R['q1']['growth'])}")
print('\nZONES (Jun26 | share | MoM | GOLY | L3M | GOL3M | Q1FY27 | Q1 gr):')
for z, d in R['zones'].items():
    print(f"  {z:10s} {d['cur']:6.0f} {d['share_jun']:5.1f}% {fp(d['mom']):>6} {fp(d['goly']):>6} {d['l3m']:6.0f} {fp(d['go_l3m']):>6} {d['q1_27']:6.0f} {fp(pct(d['q1_27'],d['q1_26'])):>6}")
print('\nTOP CHAINS Jun26:')
top = sorted(R['chains'].items(), key=lambda kv: -kv[1]['cur'])[:12]
for c, d in top:
    print(f"  {c:18s} {d['cur']:6.0f} {d['share_jun']:5.1f}% MoM {fp(d['mom']):>6} GOLY {fp(d['goly']):>6} Q1 {d['q1_27']:6.0f} ({fp(pct(d['q1_27'],d['q1_26']))})")
print('\nBRANDS Jun26:')
for b in ['Mamaearth','The Derma Co.','Aqualogica','Emerging Brands']:
    d = R['brands'][b]
    print(f"  {b:16s} {d['cur']:6.0f} {d['share_jun']:5.1f}% MoM {fp(d['mom']):>6} GOLY {fp(d['goly']):>6} Q1 {d['q1_27']:6.0f} ({fp(pct(d['q1_27'],d['q1_26']))})")
print('\nKEY SUBCATS overall (Jun26 | MoM | GOLY):')
for k in ['Mamaearth|Face Cleanser','Mamaearth|Shampoo','Mamaearth|Sun Care','The Derma Co.|Face Cleanser','The Derma Co.|Sun Care','The Derma Co.|Face Serum']:
    d = R['brand_subcat'][k]
    print(f"  {k:30s} {d['cur']:6.0f} MoM {fp(d['mom']):>6} GOLY {fp(d['goly']):>6}")
print(f"\nPRIMARY Jun'26: {prim_total[JUN26]:.0f} L | MoM {fp(R['primary_total']['mom'])} | GOLY {fp(R['primary_total']['goly'])} | Q1FY27 {R['primary_total']['q1_27']:.0f} vs Q1FY26 {R['primary_total']['q1_26']:.0f} ({fp(pct(R['primary_total']['q1_27'],R['primary_total']['q1_26']))})")
