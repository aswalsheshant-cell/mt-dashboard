#!/usr/bin/env python3
"""V2: validate corrected Jun'26 dataset, merge with monthly history, emit calc2.json."""
import csv, json, os
W = os.path.dirname(os.path.abspath(__file__))
M15 = ['Apr-25','May-25','Jun-25','Jul-25','Aug-25','Sep-25','Oct-25','Nov-25','Dec-25','Jan-26','Feb-26','Mar-26','Apr-26','May-26','Jun-26']
iA, iM, iJ, iJ25, iMar = 12, 13, 14, 2, 11
QCOLS = ['Q1-24','Q2-24','Q3-24','Q4-24','Q1-25','Q2-25','Q3-25','Q4-25','Apr-26','May-26','Jun-26']

def load(path, nkey, ncols):
    rows = []
    with open(path) as f:
        r = csv.reader(f, delimiter='\t'); hdr = next(r)
        for line in r:
            if not line or not line[0]: continue
            vals = [float(x) if x.strip() else 0.0 for x in line[nkey:nkey+ncols]]
            vals += [0.0]*(ncols-len(vals))
            rows.append((tuple(k.strip() for k in line[:nkey]), vals))
    return rows

# old monthly (validated last session)
OCZ = load(f'{W}/data/offtake_chain_zone.tsv', 3, 15)          # (channel, chain, zone)
OBZ = load(f'{W}/data/offtake_brand_subcat_zone.tsv', 4, 15)   # (channel, brand, subcat, zone)
# new corrected
QCZ = load(f'{W}/data2/offtake_chain_zone_qtr.tsv', 2, 11)     # (zone, chain) x QCOLS
QZB = load(f'{W}/data2/offtake_zone_brand_qtr.tsv', 2, 13)     # (zone, brand) x [8q + amj + q1t]
AMJ = load(f'{W}/data2/offtake_zone_brand_subcat_amj26.tsv', 3, 4)  # (zone,brand,subcat) x [apr,may,jun,q1t]
PACK = load(f'{W}/data2/offtake_pack_hero.tsv', 4, 8)          # (zone,brand,subcat,pack) x [4q,amj,q1t]

OFFICIAL_OLD = dict(zip(M15,[2255,2466,2271,2199,2436,2095,2652,2820,2891,3039,2761,3234,3589,4019,3652]))
OFFICIAL = dict(OFFICIAL_OLD); OFFICIAL.update({'Apr-26':3589.14,'May-26':4025.83,'Jun-26':3823.78})
GRAND_Q = dict(zip(QCOLS,[5503.20,5218.70,5427.91,5664.43,6992.23,6730.12,8398.23,9039.98,3589.14,4025.83,3823.78]))
ZONE_Q = {  # official zone totals from shared table A
 'EAST':[425.16,523.95,554.15,560.52,701.43,727.27,877.17,941.26,372.02,414.58,386.88],
 'NORTH':[1059.72,1041.23,1079.49,1167.91,1582.58,1506.57,1918.88,2067.78,844.80,936.50,859.89],
 'Pan India':[535.83,458.09,423.14,388.04,523.40,502.21,510.40,504.91,228.83,207.87,216.67],
 'SOUTH-1':[1011.78,983.51,966.10,1135.59,1355.74,1449.31,1708.12,1918.05,767.15,895.09,827.25],
 'SOUTH-2':[854.36,822.99,802.36,804.64,951.66,911.68,1131.77,1220.84,473.54,555.05,547.77],
 'WEST':[1616.34,1388.93,1602.67,1607.72,1877.43,1633.08,2251.87,2387.13,902.80,1016.74,985.31]}

print('=== VALIDATION 1: quarterly chain-zone rows vs official zone/grand totals ===')
ok = True
for z, exp in ZONE_Q.items():
    for qi, q in enumerate(QCOLS):
        s = sum(v[qi] for (zz, c), v in QCZ if zz == z)
        if abs(s - exp[qi]) > 0.05:
            ok = False; print(f'  MISMATCH {z} {q}: sum={s:.2f} official={exp[qi]:.2f} d={s-exp[qi]:+.2f}')
for qi, q in enumerate(QCOLS):
    s = sum(v[qi] for _, v in QCZ)
    if abs(s - GRAND_Q[q]) > 0.10: ok = False; print(f'  GRAND MISMATCH {q}: {s:.2f} vs {GRAND_Q[q]:.2f}')
print('  PASS' if ok else '  ** FAILURES ABOVE **')

print('=== VALIDATION 2: history consistency (old monthly quarters vs corrected quarterly) ===')
QM = {'Q1-25':(0,3),'Q2-25':(3,6),'Q3-25':(6,9),'Q4-25':(9,12)}
worst = []
for (z, c), v in QCZ:
    # map to old (channel, chain, zone); old zone label for Pan India rows is 'Pan India'
    old = [vv for (ch, cc, zz), vv in OCZ if cc == c and zz == z]
    if not old:
        alias = {'Frankros':'Frankros'}
        old = [vv for (ch, cc, zz), vv in OCZ if cc == c and zz == z]
    o = old[0] if old else [0.0]*15
    for q, (a, b) in QM.items():
        d = v[QCOLS.index(q)] - sum(o[a:b])
        if abs(d) > 1.0: worst.append((abs(d), f'{z}/{c} {q}: qtr={v[QCOLS.index(q)]:.1f} old-mo-sum={sum(o[a:b]):.1f} d={d:+.1f}'))
worst.sort(reverse=True)
print(f'  rows with |delta|>1 Lac in FY26 history: {len(worst)} (top 8):')
for _, msg in worst[:8]: print('   ', msg)

print('=== VALIDATION 3: zone-brand vs zone-brand-subcat AMJ26 ===')
for (z, b), v in QZB:
    for mi, m in enumerate(['Apr-26','May-26','Jun-26']):
        s = sum(vv[mi] for (zz, bb, sc), vv in AMJ if zz == z and bb == b)
        d = v[9+mi] - s
        if abs(d) > 1.4: print(f'  {z}/{b} {m}: brand={v[9+mi]:.0f} subcat-sum={s:.0f} d={d:+.1f}')
# zone totals from AMJ vs official
for z in ZONE_Q:
    for mi, m in enumerate(['Apr-26','May-26','Jun-26']):
        s = sum(vv[mi] for (zz, bb, sc), vv in AMJ if zz == z)
        d = s - ZONE_Q[z][8+mi]
        if abs(d) > 6: print(f'  AMJ zone {z} {m}: {s:.0f} vs official {ZONE_Q[z][8+mi]:.1f} d={d:+.1f} (subcat rounding)')
print('  (deltas within rounding tolerance unless listed)')

print('=== VALIDATION 4: pack hero Q1T checks ===')
bad = 0
for k, v in PACK:
    if abs((v[4]+v[5]+v[6]) - v[7]) > 1.4: bad += 1; print('  ', k, v)
print(f'  pack rows failing Apr+May+Jun≈Q1T: {bad}')

# ================= MERGE: corrected monthly series =================
def merged_chain_zone():
    out = {}
    for (ch, c, z), v in OCZ:
        nv = list(v)
        m = [vv for (zz, cc), vv in QCZ if cc == c and zz == (z if ch == 'MT' else 'Pan India')]
        if m: nv[12], nv[13], nv[14] = m[0][8], m[0][9], m[0][10]
        out[(ch, c, z)] = nv
    return out
MCZ = merged_chain_zone()

def merged_subcat():
    out = {}
    used = set()
    for (ch, b, sc, z), v in OBZ:
        nv = list(v)
        m = [vv for (zz, bb, ss), vv in AMJ if zz == z and bb == b and ss == sc]
        nv[12], nv[13], nv[14] = (m[0][0], m[0][1], m[0][2]) if m else (0.0, 0.0, 0.0)
        if m: used.add((z, b, sc))
        out[(ch, b, sc, z)] = nv
    for (z, b, sc), v in AMJ:
        if (z, b, sc) not in used and (v[0] or v[1] or v[2]):
            ch = 'EB2B' if z == 'Pan India' else 'MT'
            out[(ch, b, sc, z)] = [0.0]*12 + [v[0], v[1], v[2]]
    return out
MBZ = merged_subcat()

print('=== VALIDATION 5: merged series totals ===')
for mi, m in [(12,'Apr-26'),(13,'May-26'),(14,'Jun-26')]:
    t1 = sum(v[mi] for v in MCZ.values()); t2 = sum(v[mi] for v in MBZ.values())
    print(f'  {m}: chain-view={t1:.2f} subcat-view={t2:.0f} official={OFFICIAL[m]:.2f}')

# ================= KPI computation (same shapes as calc.json) =================
def pct(a, b): return None if not b else (a/b-1)*100
def gp(s, idx=iJ):
    return {'cur': s[idx], 'prev': s[idx-1], 'yoy_base': s[idx-12],
            'mom': pct(s[idx], s[idx-1]), 'goly': pct(s[idx], s[idx-12]),
            'l3m': sum(s[idx-3:idx])/3, 'go_l3m': pct(s[idx], sum(s[idx-3:idx])/3)}
def agg(d, pred):
    o = [0.0]*15
    for k, v in d.items():
        if pred(k):
            for i in range(15): o[i] += v[i]
    return o

R = {}
T = agg(MCZ, lambda k: True)
R['total'] = {'series': T, **gp(T)}
R['q1'] = {'fy27': sum(T[12:15]), 'fy26': sum(T[0:3]), 'growth': pct(sum(T[12:15]), sum(T[0:3]))}
ZONES = ['EAST','NORTH','SOUTH-1','SOUTH-2','WEST']
R['zones'] = {}
for z in ZONES:
    s = agg(MCZ, lambda k, z=z: k[2] == z)
    R['zones'][z] = {'series': s, **gp(s), 'share_jun': s[iJ]/OFFICIAL['Jun-26']*100,
                     'q1_27': sum(s[12:15]), 'q1_26': sum(s[0:3])}
pan = agg(MCZ, lambda k: k[0] == 'EB2B')
R['zones']['PAN INDIA'] = {'series': pan, **gp(pan), 'share_jun': pan[iJ]/OFFICIAL['Jun-26']*100,
                           'q1_27': sum(pan[12:15]), 'q1_26': sum(pan[0:3])}
R['chains'] = {}
for c in sorted({k[1] for k in MCZ}):
    s = agg(MCZ, lambda k, c=c: k[1] == c)
    if max(abs(x) for x in s) == 0: continue
    R['chains'][c] = {'series': s, **gp(s), 'share_jun': s[iJ]/OFFICIAL['Jun-26']*100,
                      'q1_27': sum(s[12:15]), 'q1_26': sum(s[0:3])}
R['zone_chains'] = {}
for z in ZONES:
    zc = {}
    for c in sorted({k[1] for k in MCZ}):
        s = agg(MCZ, lambda k, c=c, z=z: k[1] == c and k[2] == z)
        if max(abs(x) for x in s) == 0: continue
        zc[c] = {'series': s, **gp(s)}
    R['zone_chains'][z] = zc
R['brands'] = {}
for b in sorted({k[1] for k in MBZ}):
    s = agg(MBZ, lambda k, b=b: k[1] == b)
    R['brands'][b] = {'series': s, **gp(s), 'share_jun': s[iJ]/OFFICIAL['Jun-26']*100,
                      'q1_27': sum(s[12:15]), 'q1_26': sum(s[0:3])}
em = agg(MBZ, lambda k: k[1] not in ('Mamaearth','The Derma Co.','Aqualogica'))
R['brands']['Emerging Brands'] = {'series': em, **gp(em), 'share_jun': em[iJ]/OFFICIAL['Jun-26']*100,
                                  'q1_27': sum(em[12:15]), 'q1_26': sum(em[0:3])}
R['brand_subcat'] = {}
for (b, sc) in sorted({(k[1], k[2]) for k in MBZ}):
    s = agg(MBZ, lambda k, b=b, sc=sc: k[1] == b and k[2] == sc)
    R['brand_subcat'][f'{b}|{sc}'] = {'series': s, **gp(s)}
R['zone_brand_subcat'] = {}
for z in ZONES + ['Pan India']:
    zd = {}
    for (b, sc) in sorted({(k[1], k[2]) for k in MBZ if k[3] == z}):
        s = agg(MBZ, lambda k, b=b, sc=sc, z=z: k[1] == b and k[2] == sc and k[3] == z)
        zd[f'{b}|{sc}'] = {'series': s, **gp(s)}
    R['zone_brand_subcat'][z] = zd
R['zone_brands'] = {}
for z in ZONES + ['Pan India']:
    zd = {}
    for b in ['Mamaearth','The Derma Co.','Aqualogica']:
        s = agg(MBZ, lambda k, b=b, z=z: k[1] == b and k[3] == z)
        zd[b] = {'series': s, **gp(s)}
    s = agg(MBZ, lambda k, z=z: k[3] == z and k[1] not in ('Mamaearth','The Derma Co.','Aqualogica'))
    zd['Emerging Brands'] = {'series': s, **gp(s)}
    R['zone_brands'][z] = zd
# quarterly extras
R['qtr'] = {'grand': GRAND_Q, 'zones': ZONE_Q,
            'chains': {c: [sum(v[qi] for (z, cc), v in QCZ if cc == c) for qi in range(11)]
                       for c in sorted({k[1] for k, _ in QCZ})},
            'zone_brand': {f'{z}|{b}': v for (z, b), v in QZB},
            'pack': {f'{z}|{b}|{sc}|{p}': v for (z, b, sc, p), v in PACK}}
# corrections impact (Jun-26 old vs new by chain & zone; brand)
old_chain = {}
for (ch, c, z), v in OCZ: old_chain[c] = [a+b for a, b in zip(old_chain.get(c, [0]*15), v)]
R['impact'] = {'total': {'old': [2255,2466,2271,2199,2436,2095,2652,2820,2891,3039,2761,3234,3589,4019,3652],
                          'new_amj': [OFFICIAL['Apr-26'], OFFICIAL['May-26'], OFFICIAL['Jun-26']]},
               'chains_jun26': {c: {'old': round(old_chain[c][14], 1), 'new': round(R['chains'][c]['series'][14], 1)}
                                for c in R['chains'] if c in old_chain and abs(old_chain[c][14]-R['chains'][c]['series'][14]) > 0.5}}
with open(f'{W}/calc2.json', 'w') as f: json.dump(R, f, indent=1)

def fp(x): return 'n/a' if x is None else f'{x:+.1f}%'
print('\n=== HEADLINES (CORRECTED) ===')
print(f"Jun'26: {OFFICIAL['Jun-26']:.2f} L | MoM {fp(pct(OFFICIAL['Jun-26'],OFFICIAL['May-26']))} | YoY {fp(pct(OFFICIAL['Jun-26'],2271))} | L3M {(3234+OFFICIAL['Apr-26']+OFFICIAL['May-26'])/3:.1f} | GOL3M {fp(pct(OFFICIAL['Jun-26'],(3234+OFFICIAL['Apr-26']+OFFICIAL['May-26'])/3))}")
print(f"Q1 FY27 {GRAND_Q['Apr-26']+GRAND_Q['May-26']+GRAND_Q['Jun-26']:.1f} vs Q1 FY26 {GRAND_Q['Q1-25']:.1f} => {fp(pct(GRAND_Q['Apr-26']+GRAND_Q['May-26']+GRAND_Q['Jun-26'],GRAND_Q['Q1-25']))} | vs Q1-24 {GRAND_Q['Q1-24']:.0f} 2yr-CAGR {((11438.75/5503.2)**0.5-1)*100:.1f}%")
print('\nZONES corrected (Jun | share | MoM | GOLY | GOL3M | Q1FY27 | Q1gr):')
for z, d in R['zones'].items():
    print(f"  {z:10s} {d['cur']:6.0f} {d['share_jun']:5.1f}% {fp(d['mom']):>7} {fp(d['goly']):>7} {fp(d['go_l3m']):>7} {d['q1_27']:6.0f} {fp(pct(d['q1_27'],d['q1_26'])):>7}")
print('\nTOP CHAINS Jun26 corrected:')
for c, d in sorted(R['chains'].items(), key=lambda kv: -kv[1]['cur'])[:10]:
    print(f"  {c:18s} {d['cur']:7.1f} {d['share_jun']:5.1f}% MoM {fp(d['mom']):>7} GOLY {fp(d['goly']):>7} Q1 {d['q1_27']:6.0f} ({fp(pct(d['q1_27'],d['q1_26']))})")
print('\nBRANDS Jun26:')
for b in ['Mamaearth','The Derma Co.','Aqualogica','Emerging Brands']:
    d = R['brands'][b]
    print(f"  {b:16s} {d['cur']:6.0f} {d['share_jun']:5.1f}% MoM {fp(d['mom']):>7} GOLY {fp(d['goly']):>7} Q1 {d['q1_27']:6.0f} ({fp(pct(d['q1_27'],d['q1_26']))})")
print('\nKEY SUBCATS (Jun | MoM | GOLY):')
for k in ['Mamaearth|Face Cleanser','Mamaearth|Shampoo','Mamaearth|Sun Care','The Derma Co.|Face Cleanser','The Derma Co.|Sun Care','The Derma Co.|Face Serum']:
    d = R['brand_subcat'][k]
    print(f"  {k:30s} {d['cur']:6.0f} MoM {fp(d['mom']):>7} GOLY {fp(d['goly']):>7}")
print('\nCORRECTIONS IMPACT Jun-26 (chains with |delta|>0.5 L):')
for c, dd in sorted(R['impact']['chains_jun26'].items(), key=lambda kv: -(abs(kv[1]['new']-kv[1]['old']))):
    print(f"  {c:18s} old {dd['old']:8.1f} -> new {dd['new']:8.1f}  ({dd['new']-dd['old']:+.1f})")
