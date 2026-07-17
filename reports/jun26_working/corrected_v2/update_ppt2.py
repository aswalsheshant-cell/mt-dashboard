#!/usr/bin/env python3
"""V2: apply corrected Jun'26 numbers to the user's re-saved deck (deck_v2_base.pptx).
Slide map (resaved): 1=Summary, 2=Q1 scorecard, 3=Portfolio, 4=Zone summary, 11-16=zones."""
import zipfile, re, json, html

W = '/tmp/claude-0/-home-user-mt-dashboard/8b5ace2f-f399-5f35-b1e6-0bc4693c9034/scratchpad/work'
C = json.load(open(f'{W}/calc2.json'))
M15 = ['Apr-25','May-25','Jun-25','Jul-25','Aug-25','Sep-25','Oct-25','Nov-25','Dec-25','Jan-26','Feb-26','Mar-26','Apr-26','May-26','Jun-26']
iA, iM, iJ, iJ25, iMar = 12, 13, 14, 2, 11
OFF = dict(zip(M15, [2255,2466,2271,2199,2436,2095,2652,2820,2891,3039,2761,3234,3589.14,4025.83,3823.78]))
def esc(s): return html.escape(str(s), quote=False)
def R0(x): return f'{x:,.0f}'
def pctv(a, b): return None if not b else (a/b-1)*100
def arr(p, dec=0):
    if p is None: return '—'
    return ('▲' if p >= 0 else '▼') + f' {abs(p):.{dec}f}%'

parts = {}
zin = zipfile.ZipFile(f'{W}/deck_v2_base.pptx')
for n in zin.namelist(): parts[n] = zin.read(n)
zin.close()
log = []
def sld(n): return f'ppt/slides/slide{n}.xml'
def get(n): return parts[sld(n)].decode('utf8')
def put(n, x): parts[sld(n)] = x.encode('utf8')
def rep(x, old, new, cnt=1, tag=''):
    found = x.count(old)
    assert found >= cnt, f'MISSING [{tag}] ({found}<{cnt}): {old[:90]!r}'
    log.append(tag)
    return x.replace(old, new, cnt)
def rep_t(x, old, new, cnt=1, tag=''):
    return rep(x, f'>{esc(old)}<', f'>{esc(new)}<', cnt, tag)
def shape_block(x, name, occ=0):
    hits = [m.start() for m in re.finditer(re.escape(f'name="{name}"'), x)]
    assert len(hits) > occ, f'shape {name} occ{occ} not found'
    p = hits[occ]
    s = x.rfind('<p:sp>', 0, p); e = x.find('</p:sp>', p) + len('</p:sp>')
    return s, e
def sub_block(x, name, occ, fn):
    s, e = shape_block(x, name, occ)
    return x[:s] + fn(x[s:e]) + x[e:]
def set_runs_in_para(pxml, texts):
    runs = list(re.finditer(r'(<a:t>)(.*?)(</a:t>)', pxml, re.S))
    out, last = [], 0
    for k, m in enumerate(runs):
        out.append(pxml[last:m.start(2)])
        out.append(esc(texts[k]) if k < len(texts) else '')
        last = m.end(2)
    out.append(pxml[last:])
    return ''.join(out)
def set_runs_in_para_shape(block, pi, texts):
    paras = list(re.finditer(r'<a:p>.*?</a:p>', block, re.S))
    m = paras[pi]
    return block[:m.start()] + set_runs_in_para(m.group(0), texts) + block[m.end():]
def set_shape_paras(x, name, pm, occ=0):
    def fn(block):
        paras = list(re.finditer(r'<a:p>.*?</a:p>', block, re.S))
        out, last = [], 0
        for pi, m in enumerate(paras):
            out.append(block[last:m.start()])
            out.append(set_runs_in_para(m.group(0), pm[pi]) if pi in pm else m.group(0))
            last = m.end()
        out.append(block[last:])
        return ''.join(out)
    return sub_block(x, name, occ, fn)
def set_table(x, anchor, grid):
    p = x.find(anchor)
    assert p != -1, f'table anchor {anchor!r} not found'
    s = x.rfind('<a:tbl>', 0, p); e0 = x.find('</a:tbl>', p)
    assert s != -1 and e0 != -1 and x.find('</a:tbl>', s) >= p - 20, f'anchor {anchor!r} not inside a table'
    e = e0 + len('</a:tbl>')
    tbl = x[s:e]
    trs = list(re.finditer(r'<a:tr .*?</a:tr>', tbl, re.S))
    out, last = [], 0
    for ri_, tr in enumerate(trs):
        row = tr.group(0)
        if ri_ < len(grid) and grid[ri_] is not None:
            tcs = list(re.finditer(r'<a:tc(?: [^>]*)?>.*?</a:tc>', row, re.S))
            rout, rlast = [], 0
            for ci, tc in enumerate(tcs):
                cell = tc.group(0)
                if ci < len(grid[ri_]) and grid[ri_][ci] is not None:
                    ts = list(re.finditer(r'(<a:t>)(.*?)(</a:t>)', cell, re.S))
                    if ts:
                        cout, clast = [], 0
                        for k, m in enumerate(ts):
                            cout.append(cell[clast:m.start(2)])
                            cout.append(esc(grid[ri_][ci]) if k == 0 else '')
                            clast = m.end(2)
                        cout.append(cell[clast:])
                        cell = ''.join(cout)
                rout.append(row[rlast:tc.start()]); rout.append(cell); rlast = tc.end()
            rout.append(row[rlast:])
            row = ''.join(rout)
        out.append(tbl[last:tr.start()]); out.append(row); last = tr.end()
    out.append(tbl[last:])
    return x[:s] + ''.join(out) + x[e:]
def chart_name_for(slide, rid):
    rels = parts[f'ppt/slides/_rels/slide{slide}.xml.rels'].decode('utf8')
    m = dict(re.findall(r'Id="(rId\d+)"[^>]*Target="\.\./charts/(chart\d+)\.xml"', rels))
    return m[rid]
def slide_charts(slide):
    order = re.findall(r'<c:chart [^>]*r:id="(rId\d+)"', get(slide))
    return [chart_name_for(slide, r) for r in order]
def chart_info(cn):
    x = parts[f'ppt/charts/{cn}.xml'].decode('utf8')
    sers = re.findall(r'<c:ser>.*?</c:ser>', x, re.S)
    c0 = re.search(r'<c:cat>.*?</c:cat>', sers[0], re.S)
    ncats = len(re.findall(r'<c:pt ', c0.group(0))) if c0 else 0
    return {'nser': len(sers), 'ncats': ncats, 'doughnut': '<c:doughnutChart>' in x}
def set_chart(cn, cats, series_vals, series_names=None, fmt='General'):
    key = f'ppt/charts/{cn}.xml'
    x = parts[key].decode('utf8')
    sers = list(re.finditer(r'<c:ser>.*?</c:ser>', x, re.S))
    assert len(sers) == len(series_vals), f'{cn}: {len(sers)} != {len(series_vals)}'
    out, last = [], 0
    for si, sm in enumerate(sers):
        s = sm.group(0)
        if series_names and series_names[si] is not None:
            s = re.sub(r'(<c:tx>.*?<c:strCache>.*?<c:v>).*?(</c:v>)',
                       lambda m: m.group(1) + esc(series_names[si]) + m.group(2), s, 1, re.S)
        cc = '<c:ptCount val="%d"/>' % len(cats) + ''.join(f'<c:pt idx="{k}"><c:v>{esc(c)}</c:v></c:pt>' for k, c in enumerate(cats))
        s = re.sub(r'(<c:cat>.*?<c:(?:str|num)Cache>).*?(</c:(?:str|num)Cache>)', lambda m: m.group(1) + cc + m.group(2), s, 1, re.S)
        vv = series_vals[si]
        vc = f'<c:formatCode>{fmt}</c:formatCode>' + '<c:ptCount val="%d"/>' % len(vv) + ''.join(
            f'<c:pt idx="{k}"><c:v>{v}</c:v></c:pt>' for k, v in enumerate(vv) if v is not None)
        s = re.sub(r'(<c:val>.*?<c:numCache>).*?(</c:numCache>)', lambda m: m.group(1) + vc + m.group(2), s, 1, re.S)
        out.append(x[last:sm.start()]); out.append(s); last = sm.end()
    out.append(x[last:])
    parts[key] = ''.join(out).encode('utf8')
    log.append(f'{cn} cache')
def ri(s, i): return round(s[i])
def chip(x, shape, occ, prefix, p):
    def fn(block):
        ts = list(re.finditer(r'(<a:t>)(.*?)(</a:t>)', block, re.S))
        assert ts, f'no runs in {shape}'
        tgt, blank = ts[-1], None
        if ts[-1].group(2).strip() == '%' and len(ts) >= 2: tgt, blank = ts[-2], ts[-1]
        txt = arr(p) if len(ts) > 1 else f'{prefix}{arr(p)}'
        out = block[:tgt.start(2)] + esc(txt) + block[tgt.end(2):]
        if blank is not None:
            sh = len(esc(txt)) - (tgt.end(2) - tgt.start(2))
            out = out[:blank.start(2)+sh] + out[blank.end(2)+sh:]
        return out
    return sub_block(x, shape, occ, fn)
def try_chip(x, shape, occ, prefix, p):
    try: return chip(x, shape, occ, prefix, p)
    except AssertionError: return x
def try_val_chip(x, shape, label, val):
    def fn(block):
        ts = list(re.finditer(r'(<a:t>)(.*?)(</a:t>)', block, re.S))
        texts = [m.group(2) for m in ts]
        new = [f'{label} {val}'] if len(ts) == 1 else list(texts)
        if len(ts) > 1:
            if texts[0].strip().startswith(('May', 'Jun')): new[0] = f'{label} '
            new[-1] = str(val)
        out, last = [], 0
        for k, m in enumerate(ts):
            out.append(block[last:m.start(2)]); out.append(esc(new[k])); last = m.end(2)
        out.append(block[last:])
        return ''.join(out)
    try:
        s, e = shape_block(x, shape, 0)
    except AssertionError:
        return x
    return x[:s] + fn(x[s:e]) + x[e:]

zones, chains, brands, bs = C['zones'], C['chains'], C['brands'], C['brand_subcat']
zbs, zb, zc, QTR = C['zone_brand_subcat'], C['zone_brands'], C['zone_chains'], C['qtr']
l3m_off = (OFF['Mar-26'] + OFF['Apr-26'] + OFF['May-26']) / 3
q1_27, q1_26, q1_24 = 11438.75, 6992.23, 5503.20

# ================= SLIDE 1 =================
x = get(1)
x = rep_t(x, '₹ 36.52 Cr', '₹ 38.24 Cr', tag='s1 jun')
x = rep_t(x, '₹ 40.19 Cr', '₹ 40.26 Cr', tag='s1 may')
x = x.replace('>9<', '>5<', 1)   # MoM digit (KPI cards precede table in doc order)
x = rep_t(x, '₹ 36.14 Cr', '₹ 36.16 Cr', tag='s1 l3m')
x = x.replace('>1<', '>6<', 1)   # GO L3M digit
x = rep_t(x, '60.8%', '68.4%', tag='s1 yoy')
x = rep_t(x, '₹ 13.81 Cr', '₹ 15.53 Cr', tag='s1 yoyd')
x = rep_t(x, '36.52 Cr ', '38.24 Cr ', tag='s1 b1')
x = rep_t(x, '▲ 61% YoY', '▲ 68% YoY', tag='s1 b1y')
x = rep_t(x, '▲ 1.1%', '▲ 5.7%', tag='s1 b1l')
x = rep_t(x, ' vs L3M Avg, adding +1,381 Lacs YoY — the best-ever June despite a seasonal ▼9% MoM off the May record. ',
          ' vs L3M Avg, adding +1,553 Lacs YoY — best-ever June on corrected chain NSV, despite a seasonal ▼5% MoM off the May record. ', tag='s1 b1t')
x = rep_t(x, '₹112.60 Cr, ', '₹114.39 Cr, ', tag='s1 q1v')
x = rep_t(x, '▲ 61%', '▲ 64%', tag='s1 q1g')
x = rep_t(x, '— every zone grew ≥54%; ', '— every zone grew ≥55% (South-1 ▲84%); ', tag='s1 q1z')
x = rep_t(x, 'growth is broad-based, not a base effect', '2-yr Q1 CAGR of +44% confirms structural scale', tag='s1 q1c')
x = rep_t(x, ", Reliance and Apollo delivered 81.0% of Jun'26 offtake", ", Reliance and Apollo delivered 81.8% of Jun'26 offtake", tag='s1 b3')
x = rep_t(x, ' holds 69.9% portfolio share.', ' holds 71.8% portfolio share.', tag='s1 b4')
def chain_row(name, key):
    s = chains[key]['series']
    l3 = (s[iMar] + s[iA] + s[iM]) / 3
    return [name, R0(s[iJ25]), R0(s[10]), R0(s[iMar]), R0(s[iA]), R0(s[iM]), R0(s[iJ]),
            f'{s[iJ]/OFF["Jun-26"]*100:.0f}%', R0(l3), arr(pctv(s[iJ], s[iJ25])), arr(pctv(s[iJ], s[iM]))]
listed = ['Dmart','Reliance','Apollo','Fsn','Wellness Forever','H&G','Lulu','Metro Cnc','Sancus(Rmt)','More Retail','Walmart Cnc','Spencer','Vmm']
rows = [chain_row(*p) for p in [('Dmart','Dmart'),('Reliance','Reliance'),('Apollo','Apollo'),('Fsn','Fsn'),
        ('Wellness','Wellness Forever'),('H&G','H&G'),('Lulu','Lulu'),('Metro','Metro Cnc'),
        ('Delhi RMT','Sancus(Rmt)'),('More Retail','More Retail'),('Walmart','Walmart Cnc'),
        ('Spencer','Spencer'),('Vmm','Vmm')]]
oth = [OFF[M15[k]] - sum(chains[c]['series'][k] for c in listed) for k in range(15)]
ol3 = (oth[iMar]+oth[iA]+oth[iM])/3
rows.append(['Others Combined', R0(oth[iJ25]), R0(oth[10]), R0(oth[iMar]), R0(oth[iA]), R0(oth[iM]), R0(oth[iJ]),
             f'{oth[iJ]/OFF["Jun-26"]*100:.0f}%', R0(ol3), arr(pctv(oth[iJ], oth[iJ25])), arr(pctv(oth[iJ], oth[iM]))])
rows.append(['Total Channel', R0(OFF['Jun-25']), R0(OFF['Feb-26']), R0(OFF['Mar-26']), R0(OFF['Apr-26']), R0(OFF['May-26']),
             R0(OFF['Jun-26']), None, R0(l3m_off), arr(pctv(OFF['Jun-26'], OFF['Jun-25'])), arr(pctv(OFF['Jun-26'], OFF['May-26']))])
x = set_table(x, '>Delhi RMT<', [[None]*11, [None]*11] + rows)
put(1, x)
cs1 = slide_charts(1)
trend = next(c for c in cs1 if chart_info(c)['nser'] == 4)
bars = [c for c in cs1 if chart_info(c)['nser'] == 1]
top10c = next(c for c in bars if chart_info(c)['ncats'] == 10)
sharec = next(c for c in bars if chart_info(c)['ncats'] == 7)
set_chart(trend, ['Jan-26','Feb-26','Mar-26','Apr-26','May-26','Jun-26'],
          [[round(OFF[m]) for m in M15[9:]],
           [ri(chains['Dmart']['series'], k) for k in range(9, 15)],
           [ri(chains['Reliance']['series'], k) for k in range(9, 15)],
           [ri(chains['Apollo']['series'], k) for k in range(9, 15)]])
top10 = [('D-mart','Dmart'),('Reliance','Reliance'),('Apollo','Apollo'),('FSN','Fsn'),('Wellness Forever','Wellness Forever'),
         ('H&G','H&G'),('Lulu','Lulu'),('Metro CNC','Metro Cnc'),('Sancus (RMT)','Sancus(Rmt)'),('More Retail','More Retail')]
set_chart(top10c, [t[0] for t in top10], [[ri(chains[t[1]]['series'], iJ) for t in top10]], series_names=['Jun-26 NSV'])
top7 = [('D-mart','Dmart'),('Reliance','Reliance'),('Apollo','Apollo'),('FSN','Fsn'),('Lulu','Lulu'),('Wellness','Wellness Forever'),('H&G','H&G')]
set_chart(sharec, [t[0] for t in top7], [[round(chains[t[1]]['series'][iJ]/OFF['Jun-26']*100, 1) for t in top7]])

# ================= SLIDE 2 (Q1 scorecard) =================
x = get(2)
x = rep_t(x, '₹ 112.60 Cr', '₹ 114.39 Cr', tag='s2 q1')
x = rep_t(x, '▲ 61.0%', '▲ 63.6%', tag='s2 gr')
x = rep_t(x, '+ ₹ 42.68 Cr YoY', '+ ₹ 44.47 Cr YoY', tag='s2 d')
x = rep_t(x, "May'26 ₹ 40.19 Cr", "May'26 ₹ 40.26 Cr", tag='s2 may')
x = rep_t(x, '₹ 36.52 Cr', '₹ 38.24 Cr', tag='s2 jun')
x = rep_t(x, '▲ 61% YoY | best-ever June', '▲ 68% YoY | best-ever June', tag='s2 exit')
x = rep_t(x, "Apr–Jun'26 vs Apr–Jun'25  |  NSV ₹ Lacs  |  MT + EB2B channels",
          "Apr–Jun'26 vs Apr–Jun'25  |  NSV ₹ Lacs  |  MT + EB2B  |  post chain-NSV correction", tag='s2 sub')
x = set_shape_paras(x, 'Text 0', {0: ['Q1 FY27 SCORECARD — OFFTAKE']})  # restore scorecard title (was overwritten in resave)
G = lambda p: ('1E7A45' if p >= 0 else 'B23A3A')
zq = {'East':(701.43,1173.48),'North':(1582.58,2641.19),'South-1':(1355.74,2489.49),
      'South-2':(951.66,1576.36),'West':(1877.43,2904.85),'Pan India (FSN)':(523.40,653.37)}
zgrid = [[None]*5]
for nm,(a,b) in zq.items():
    zgrid.append([None, R0(a), R0(b), arr(pctv(b,a)), f'{b/q1_27*100:.0f}%'])   # keep user labels
zgrid.append([None, R0(q1_26), R0(q1_27), arr(pctv(q1_27,q1_26)), '100%'])
x = set_table(x, '>East<', zgrid)
bq = [(6142,8254),(634,2951),(169,196),(44,36)]   # ME, TDC, AQ, Other (user's short labels kept)
bgrid = [[None]*5] + [[None, R0(a), R0(b), arr(pctv(b,a)), f'{b/q1_27*100:.0f}%'] for a,b in bq]
x = set_table(x, '>ME<', bgrid)
cq = [(2599.61,4231.67),(1907.96,2805.75),(792.52,2172.92),(523.40,653.37),(123.80,333.17),(249.40,291.26)]
cgrid = [[None]*5] + [[None, R0(a), R0(b), arr(pctv(b,a)), f'{b/q1_27*100:.0f}%'] for a,b in cq]
x = set_table(x, '>Dmart<', cgrid)
x = set_shape_paras(x, 'Insights', {
    1: ['The Derma Co. multiplied ~4.7x YoY in Q1 (₹6.3 Cr → ₹29.5 Cr) and now holds 26% of the Q1 mix vs 9% LY — the structural growth engine.'],
    2: ['Mamaearth grew +34% on the largest base (72% of mix) — Face Cleanser +35% and Shampoo +65% YoY in Jun on corrected NSV keep the anchor compounding.'],
    3: ['Apollo (+174%) and Lulu (+171%) are the fastest-compounding chains; Apollo is now the #1 chain in South-1 — pharmacy-led premiumisation is working.'],
    4: ["Watch-outs: H&G Q1 ▼14% YoY, Walmart CNC billed nil in Jun'26, Wellness Forever (+17%) trails the network (+64%) — chain-level JBP correction needed."],
    5: ['Seasonality note: Jun ▼5% MoM is Sun Care-led (▼30% MoM), in line with category; 2-yr Q1 CAGR of +44% (₹55.0 Cr → ₹114.4 Cr) confirms structural scale-up.'],
})
put(2, x)

# ================= SLIDE 3 (Portfolio drivers) =================
x = get(3)
ME_FW, ME_SH, ME_SC = bs['Mamaearth|Face Cleanser'], bs['Mamaearth|Shampoo'], bs['Mamaearth|Sun Care']
TD_FW, TD_SC, TD_FS = bs['The Derma Co.|Face Cleanser'], bs['The Derma Co.|Sun Care'], bs['The Derma Co.|Face Serum']
x = chip(x, 'Text 6', 0, 'GOLY ', ME_FW['goly']); x = chip(x, 'Text 7', 0, 'MoM ', ME_FW['mom'])
x = chip(x, 'Text 10', 0, 'GOLY ', ME_SH['goly']); x = chip(x, 'Text 11', 0, 'MoM ', ME_SH['mom'])
x = chip(x, 'Text 14', 0, 'GOLY ', ME_SC['goly']); x = chip(x, 'Text 15', 0, 'MoM ', ME_SC['mom'])
x = chip(x, 'Text 6', 1, 'GOLY ', TD_FW['goly']); x = chip(x, 'Text 7', 1, 'MoM ', TD_FW['mom'])
ZB_B0 = {}
for k, v in C['qtr']['zone_brand'].items():
    z, b = k.split('|'); ZB_B0[(z, b)] = v
def bAMJ(b):  # exact Apr/May/Jun from shared zone×brand table
    return tuple(sum(ZB_B0.get((z, b), [0]*13)[9+m] for z in ['EAST','NORTH','Pan India','SOUTH-1','SOUTH-2','WEST']) for m in range(3))
def brow3(name, key):
    s = brands[key]['series']
    ap, my, jn = bAMJ(key)
    l3 = (s[iMar] + ap + my) / 3
    return [name, R0(s[iJ25]), R0(s[10]), R0(s[iMar]), R0(ap), R0(my), R0(jn),
            f'{jn/OFF["Jun-26"]*100:.0f}%', R0(l3), arr(pctv(jn, l3)), arr(pctv(jn, s[iJ25]))]
b3n = ['Mamaearth','The Derma Co.','Aqualogica']
em = [OFF[M15[k]] - sum(brands[b]['series'][k] for b in b3n) for k in range(12)] + \
     [OFF[M15[12+m]] - sum(bAMJ(b)[m] for b in b3n) for m in range(3)]
eml3 = (em[iMar]+em[iA]+em[iM])/3
g18 = [[None]*11, brow3('Mamaearth','Mamaearth'), brow3('The Derma Co.','The Derma Co.'), brow3('Aqualogica','Aqualogica'),
       ['Emerging Brands', R0(em[iJ25]), R0(em[10]), R0(em[iMar]), R0(em[iA]), R0(em[iM]), R0(em[iJ]),
        f'{em[iJ]/OFF["Jun-26"]*100:.0f}%', R0(eml3), arr(pctv(em[iJ], eml3)), arr(pctv(em[iJ], em[iJ25]))],
       ['Portfolio Total', R0(OFF['Jun-25']), R0(OFF['Feb-26']), R0(OFF['Mar-26']), R0(OFF['Apr-26']), R0(OFF['May-26']),
        R0(OFF['Jun-26']), '100%', R0(l3m_off), arr(pctv(OFF['Jun-26'], l3m_off)), arr(pctv(OFF['Jun-26'], OFF['Jun-25']))]]
x = set_table(x, '>Portfolio Total<', g18)
meJ, tdJ, aqJ = bAMJ('Mamaearth')[2], bAMJ('The Derma Co.')[2], bAMJ('Aqualogica')[2]
meS, tdS, aqS = brands['Mamaearth'], brands['The Derma Co.'], brands['Aqualogica']
x = rep_t(x, 'remains the portfolio Leader at 69.9% share, growing a steady +28% YoY. ',
          f"remains the portfolio Leader at {meJ/OFF['Jun-26']*100:.1f}% share, growing a steady +{pctv(meJ, meS['series'][iJ25]):.0f}% YoY. ", tag='s3 me')
x = rep_t(x, 'is the fastest scaling brand now 27.7% of NSV vs single digits a ',
          f"is the fastest scaling brand now {tdJ/OFF['Jun-26']*100:.1f}% of NSV vs single digits a ", tag='s3 td')
x = rep(x, esc('holds structural growth at ▲ 24% YoY, though Jun cooled ▼ 14% MoM with Sun Care seasonality. Contribution remains small (1.7%)'),
        esc(f"holds structural growth at {arr(aqS['goly'])} YoY, though Jun cooled {arr(aqS['mom'])} MoM with Sun Care seasonality. Contribution remains small ({aqS['cur']/OFF['Jun-26']*100:.1f}%)"), 1, 's3 aq')
put(3, x)
cs3 = slide_charts(3)
assert len(cs3) == 6, f's3 charts {len(cs3)}'
catsJ = ['Jun','Jul','Aug','Sep','Oct','Nov','Dec','Jan','Feb','Mar','Apr','May','Jun']
for cn, d in zip(cs3, [ME_FW, ME_SH, ME_SC, TD_FW, TD_SC, TD_FS]):
    set_chart(cn, catsJ, [[ri(d['series'], k) for k in range(2, 15)]])

# ================= SLIDE 4 (Zone summary) =================
x = get(4)
E, N, S1, S2, Wz, PAN = zones['EAST'], zones['NORTH'], zones['SOUTH-1'], zones['SOUTH-2'], zones['WEST'], zones['PAN INDIA']
x = set_shape_paras(x, 'Text 65', {
    0: ['Zone Insights | Jun’26 (post chain-NSV correction)'],
    1: ['West remained the largest zone', ' with NSV of ', f'₹{ri(Wz["series"],iJ):,} Lacs', ', contributing ', f'{Wz["share_jun"]:.1f}%', ' to overall MT offtake.'],
    2: ['Every zone grew ≥64% YoY in Jun’26', ' — the corrected chain NSV lifts growth across the board (network ▲68%).'],
    3: ['South-1 delivered the strongest YoY growth at ', f'{arr(S1["goly"])}, ', 'with East and North at +72% each — scale-up momentum is broad-based.'],
    4: ['Dmart', ' is the #1 chain in 3 out of 5 zones', ': North, South-2 and West — and a close #2 in South-1. This confirms ', 'Dmart', ' as a national growth engine, not limited to one zone.'],
    5: ['Apollo reclaims #1 in South-1 (₹289 Lacs) post correction, growing ▲163% YoY nationally', ' — repeatable pharmacy-channel momentum, largely driven by ', 'The Derma Co.'],
    9: ['The Derma Co. held ₹990 Lacs in Jun (record ₹1,097 in May)', ', contributing ', '25.9%', ' to the portfolio. The brand grew ', '▲378% ', 'YoY', ', still the fastest-scaling growth engine in the portfolio.'],
    10: ['Face Cleanser and Sun Care remained the top 2 growth drivers for The Derma Co. in 5 out of 6 zones', ', making them the clearest scale-up levers. ', 'FSN grew +32% YoY — improving, but still slower than the network (+68%).'],
    12: ['Sun Care cooled seasonally across zones (▼30% MoM off the summer peak)', ' — in line with category seasonality; protect sunscreen distribution gains into monsoon.'],
})
def zrow(label, d):
    s = d['series']; l3 = (s[iMar]+s[iA]+s[iM])/3
    return [label, R0(s[iJ25]), R0(s[iMar]), R0(s[iA]), R0(s[iM]), R0(s[iJ]),
            f'{d["share_jun"]:.0f}%', R0(l3), arr(pctv(s[iJ], l3)), arr(pctv(s[iJ], s[iJ25]))]
x = set_table(x, '>GOLY Jun<', [[None]*10, zrow('East', E), zrow('North', N), zrow('South-1', S1),
                                zrow('South-2', S2), zrow('West', Wz), zrow('FSN', PAN)])
put(4, x)
cs4 = slide_charts(4)
zcats = ['East','North','South-1','South-2','West','Pan India']
zJ = [ri(E['series'],iJ), ri(N['series'],iJ), ri(S1['series'],iJ), ri(S2['series'],iJ), ri(Wz['series'],iJ), ri(PAN['series'],iJ)]
for cn in cs4:
    if chart_info(cn)['doughnut']:
        set_chart(cn, zcats, [[round(z['share_jun'],1) for z in (E,N,S1,S2,Wz,PAN)]])
    else:
        set_chart(cn, zcats, [zJ], series_names=['Jun-26 NSV'])

# ================= ZONE SLIDES 11-16 =================
ZS = {11: ('EAST','East'), 12: ('NORTH','North'), 13: ('SOUTH-1','South-1'), 14: ('SOUTH-2','South-2'), 15: ('WEST','West'), 16: ('PAN INDIA','FSN')}
CHIPSETS = [('Text 6','Text 7','Text 8','Mamaearth|Face Cleanser'), ('Text 10','Text 11','Text 12','Mamaearth|Shampoo'),
            ('Text 14','Text 15','Text 16','Mamaearth|Sun Care'), ('Text 20','Text 21','Text 22','The Derma Co.|Face Cleanser'),
            ('Text 24','Text 25','Text 26','The Derma Co.|Sun Care'), ('Text 28','Text 29','Text 30','The Derma Co.|Face Serum')]
ZTBL = {11: [('Reliance','Reliance'),('Apollo','Apollo'),('VMM','Vmm'),('More Retail','More Retail'),('Frankros','Frankros'),('Spencer','Spencer')],
        12: [('Dmart','Dmart'),('Reliance','Reliance'),('Apollo','Apollo'),('Sancus(Rmt)','Sancus(Rmt)'),('Lulu','Lulu'),('Metro Cnc','Metro Cnc')],
        13: [('Apollo','Apollo'),('Dmart','Dmart'),('Reliance','Reliance'),('Lulu','Lulu'),('H&G','H&G'),('Metro Cnc','Metro Cnc')],
        14: [('Dmart','Dmart'),('Apollo','Apollo'),('Reliance','Reliance'),('H&G','H&G'),('More Retail','More Retail'),('Lulu','Lulu')],
        15: [('Dmart','Dmart'),('Reliance','Reliance'),('Wellness Forever','Wellness Forever'),('Apollo','Apollo'),('Metro Cnc','Metro Cnc'),('Trent','Trent')],
        16: [('Fsn','Fsn')]}
ZB_B = {}  # exact zone-brand AMJ from shared table B
for k, v in QTR['zone_brand'].items():
    z, b = k.split('|')
    ZB_B[(z, b)] = v  # cols: 8 qtrs(0-7 with Q4-23 at idx3), 8=Apr,9=May? layout: Q1-24,Q2-24,Q3-24,Q4-23,Q4-24,Q1-25,Q2-25,Q3-25,Q4-25,Apr,May,Jun,Q1T
DISP = {'Dmart':'Dmart','Reliance':'Reliance','Apollo':'Apollo','Vmm':'VMM','More Retail':'More Retail','Frankros':'Frankros',
        'Spencer':'Spencer','Sancus(Rmt)':'Sancus(Rmt)','Lulu':'Lulu','Metro Cnc':'Metro Cnc','H&G':'H&G',
        'Wellness Forever':'Wellness Forever','Trent':'Trent','V-Mart':'V-Mart','Arambagh':'Arambagh'}
for sn, (zk, zl) in ZS.items():
    x = get(sn)
    Z = zones[zk]; s = Z['series']
    cur, share, l3, goly, mom, gol3 = ri(s, iJ), Z['share_jun'], Z['l3m'], Z['goly'], Z['mom'], Z['go_l3m']
    q1z, q1zg = Z['q1_27'], pctv(Z['q1_27'], Z['q1_26'])
    zsub = 'Pan India' if sn == 16 else zk
    x = sub_block(x, 'Textbox 253', 0, lambda b: set_runs_in_para_shape(b, 1, [str(cur)]))
    x = sub_block(x, 'Textbox 257', 0, lambda b: set_runs_in_para_shape(b, 1, [f'{share:.1f}%']))
    x = sub_block(x, 'Textbox 261', 0, lambda b: set_runs_in_para_shape(b, 1, [R0(l3)]))
    x = sub_block(x, 'Textbox 265', 0, lambda b: set_runs_in_para_shape(b, 1, [arr(goly)]))
    peak = max(range(15), key=lambda k: s[k])
    if sn == 16:
        pm = {2: [f'Chain View: Jun-26 closed at {cur} for FSN ({share:.1f}% of channel), {arr(mom)} MoM. Q1 FY27 = {R0(q1z)} Lacs, {arr(q1zg)} vs Q1 FY26.'],
              3: [f'Growth View: Jun-26 was {arr(gol3)} vs L3M and {arr(goly)} vs Jun-25 — best month since the Apr-26 record of 229.'],
              4: ['Zone Insight: FSN improved to +32% YoY but still trails the network (+68%); assortment plus promo refresh remains the lever.']}
    else:
        pm = {2: [f'Zone View: Jun-26 closed at {cur} for {zl} ({share:.1f}% of channel), {arr(mom)} MoM off the {M15[peak]} record of {ri(s,peak)}. Q1 FY27 = {R0(q1z)} Lacs, {arr(q1zg)} vs Q1 FY26.'],
              3: [f'Growth View: Jun-26 was {arr(gol3)} vs L3M and {arr(goly)} vs Jun-25 — YoY momentum intact despite seasonal moderation.']}
    x = set_shape_paras(x, 'Textbox 268', pm)
    zd = zbs[zsub]
    for gs, ms, vs, key in CHIPSETS:
        if key not in zd: continue
        d = zd[key]
        x = try_chip(x, gs, 0, 'GOLY ', d['goly'])
        x = try_chip(x, ms, 0, 'MoM ', d['mom'])
        x = try_val_chip(x, vs, "Jun'26", ri(d['series'], iJ))
    # brand table: Apr/May/Jun from shared zone-brand table (exact); Jun-25/Mar-26 from merged monthly
    ztot_off = {'EAST':386.88,'NORTH':859.89,'SOUTH-1':827.25,'SOUTH-2':547.77,'WEST':985.31,'PAN INDIA':216.67}[zk]
    def bvals(b):
        v = ZB_B.get((zsub, b), [0]*13)
        return v[9], v[10], v[11]   # Apr, May, Jun
    def brow(name):
        hist = zb[zsub][name]['series']
        if name == 'Emerging Brands':
            aApr = zApr - sum(bvals(b)[0] for b in b3n)
            aMay = zMay - sum(bvals(b)[1] for b in b3n)
            aJun = ztot_off - sum(bvals(b)[2] for b in b3n)
            l3b = (hist[iMar] + aApr + aMay) / 3
            return [name, R0(hist[iJ25]), R0(aMay), R0(max(aJun, 0)), f'{max(aJun,0)/ztot_off*100:.0f}%', R0(max(l3b, 0)), None, None]
        ap, my, jn = bvals(name)
        l3b = (hist[iMar] + ap + my) / 3
        return [name, R0(hist[iJ25]), R0(my), R0(jn), f'{jn/ztot_off*100:.0f}%', R0(l3b),
                arr(pctv(jn, l3b)), arr(pctv(jn, hist[iJ25]))]
    zApr = {'EAST':372.02,'NORTH':844.80,'SOUTH-1':767.15,'SOUTH-2':473.54,'WEST':902.80,'PAN INDIA':228.83}[zk]
    zMay = {'EAST':414.58,'NORTH':936.50,'SOUTH-1':895.09,'SOUTH-2':555.05,'WEST':1016.74,'PAN INDIA':207.87}[zk]
    x = set_table(x, '>Emerging Brands<', [[None]*8, brow('Mamaearth'), brow('The Derma Co.'), brow('Aqualogica'), brow('Emerging Brands')])
    # chain table
    if sn == 16:
        f = chains['Fsn']; ss = f['series']; l3c = (ss[iMar]+ss[iA]+ss[iM])/3
        g193 = [[None]*8, ['Fsn', R0(ss[iJ25]), R0(ss[iM]), R0(ss[iJ]), '100%', R0(l3c), arr(pctv(ss[iJ], l3c)), arr(pctv(ss[iJ], ss[iJ25]))],
                ['Others Combined','0','0','0','0%','0',None,None]]
    else:
        zcd = zc[zk]
        g193 = [[None]*8]
        for disp, key in ZTBL[sn]:
            ss = zcd[key]['series']; l3c = (ss[iMar]+ss[iA]+ss[iM])/3
            g193.append([disp, R0(ss[iJ25]), R0(ss[iM]), R0(ss[iJ]), f'{ss[iJ]/s[iJ]*100:.0f}%', R0(l3c),
                         arr(pctv(ss[iJ], l3c)), arr(pctv(ss[iJ], ss[iJ25]))])
        o = [s[k] - sum(zcd[c]['series'][k] for _, c in ZTBL[sn] if c in zcd) for k in range(15)]
        ol3z = (o[iMar]+o[iA]+o[iM])/3
        g193.append(['Others Combined', R0(o[iJ25]), R0(o[iM]), R0(o[iJ]), f'{o[iJ]/s[iJ]*100:.0f}%', R0(ol3z),
                     arr(pctv(o[iJ], ol3z)) if ol3z else None, arr(pctv(o[iJ], o[iJ25])) if o[iJ25] else None])
    x = set_table(x, '>Others Combined<', g193)
    # highlight strip
    if sn != 16:
        zcd = zc[zk]
        lead = max(zcd, key=lambda c: zcd[c]['series'][iJ]); leadv = ri(zcd[lead]['series'], iJ)
        elig = {c: d for c, d in zcd.items() if d['series'][iJ25] >= 3 and d['series'][iJ] >= 10}
        fast = max(elig, key=lambda c: pctv(elig[c]['series'][iJ], elig[c]['series'][iJ25]) or -999)
        fg = pctv(zcd[fast]['series'][iJ], zcd[fast]['series'][iJ25])
        x = set_shape_paras(x, 'Textbox 290', {0: [
            f'Zone View: {zl} closed Jun-26 at {cur}, {arr(gol3)} vs L3M and {arr(goly)} vs Jun-25; Q1 FY27 {arr(q1zg)} YoY (corrected NSV).',
            f' Chain Highlights: {DISP.get(lead, lead)} leads; {DISP.get(fast, fast)} is the fastest YoY chain.']})
        x = set_shape_paras(x, 'Textbox 295', {0: [DISP.get(lead, lead), ' ', '-', ' ', str(leadv)]})
        try:
            x = sub_block(x, 'Textbox 296', 0, lambda b: set_runs_in_para(b, [f'{DISP.get(fast, fast)}  - ', arr(fg)]))
        except AssertionError: pass
        # zone record chip (May-26 corrected)
        rec = ri(s, 13)
        try:
            x = sub_block(x, 'Textbox 298', 0, lambda b: set_runs_in_para(b, ['May-26', ' ', '- ', str(rec), ' ']))
        except AssertionError: pass
    else:
        x = set_shape_paras(x, 'Textbox 290', {1: ['Chain Highlights:- ', ' ', 'FSN',
            f' closed Jun-26 at {cur}, {arr(gol3)} vs L3M and {arr(goly)} vs Jun-25; the Apr-26 record of 229 stands.']})
        x = set_shape_paras(x, 'Textbox 295', {0: ['Fsn', ' ', '-', ' ', str(cur)]})
        x = sub_block(x, 'Textbox 296', 0, lambda b: set_runs_in_para(b, ['Fsn  - ', arr(goly)]))
    put(sn, x)
    ccs = slide_charts(sn)
    assert len(ccs) == 6, f's{sn}: {len(ccs)} charts'
    keys = ['Mamaearth|Face Cleanser','Mamaearth|Shampoo','Mamaearth|Sun Care','The Derma Co.|Face Cleanser','The Derma Co.|Sun Care','The Derma Co.|Face Serum']
    for cn, key in zip(ccs, keys):
        d = zd.get(key)
        vals = [ri(d['series'], k) for k in range(2, 15)] if d else [0]*13
        set_chart(cn, catsJ, [vals])

out = f'{W}/deck_jun26_corrected.pptx'
zo = zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED)
for n, d in parts.items(): zo.writestr(n, d)
zo.close()
print(f'OK — {len(log)} edits; {out}')
