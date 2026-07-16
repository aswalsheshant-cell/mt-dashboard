#!/usr/bin/env python3
"""Roll the May'26 MT Offtake leadership deck forward to Jun'26 + Q1 FY27.
Pure stdlib string/regex surgery on the OOXML parts; every edit is asserted."""
import zipfile, re, json, shutil, sys, html

WORK = '/tmp/claude-0/-home-user-mt-dashboard/8b5ace2f-f399-5f35-b1e6-0bc4693c9034/scratchpad/work'
CALC = json.load(open(f'{WORK}/calc.json'))
M15 = ['Apr-25','May-25','Jun-25','Jul-25','Aug-25','Sep-25','Oct-25','Nov-25','Dec-25','Jan-26','Feb-26','Mar-26','Apr-26','May-26','Jun-26']
iJ, iM, iA, iMar, iJ25 = 14, 13, 12, 11, 2
OFFICIAL = dict(zip(M15, [2255,2466,2271,2199,2436,2095,2652,2820,2891,3039,2761,3234,3589,4019,3652]))

def esc(s): return html.escape(str(s), quote=False)
def R0(x): return f'{x:,.0f}'
def pctv(new, old): return None if not old else (new/old-1)*100
def arr(p, dec=0):
    if p is None: return '—'
    a = '▲' if p >= 0 else '▼'
    return f'{a} {abs(p):.{dec}f}%'

parts = {}
zin = zipfile.ZipFile(f'{WORK}/deck.pptx')
for n in zin.namelist(): parts[n] = zin.read(n)
zin.close()

edits_log = []
def sld(n): return f'ppt/slides/slide{n}.xml'
def get(n): return parts[sld(n)].decode('utf8')
def put(n, x): parts[sld(n)] = x.encode('utf8')

def rep(x, old, new, cnt=1, tag=''):
    found = x.count(old)
    assert found >= cnt, f'MISSING [{tag}] ({found}<{cnt}): {old[:80]!r}'
    edits_log.append(f'{tag}: {old[:50]!r} -> {new[:50]!r}')
    return x.replace(old, new, cnt)

def rep_t(x, old, new, cnt=1, tag=''):
    """replace inside <a:t> boundaries to avoid touching attrs"""
    return rep(x, f'>{esc(old)}<', f'>{esc(new)}<', cnt, tag)

# ---------- shape/table block helpers ----------
def shape_block(x, name, occ=0):
    hits = [m.start() for m in re.finditer(re.escape(f'name="{name}"'), x)]
    assert len(hits) > occ, f'shape {name} occ{occ} not found'
    p = hits[occ]
    s = x.rfind('<p:sp>', 0, p)
    e = x.find('</p:sp>', p) + len('</p:sp>')
    assert s != -1 and e > s
    return s, e

def sub_block(x, name, occ, fn):
    s, e = shape_block(x, name, occ)
    return x[:s] + fn(x[s:e]) + x[e:]

def set_runs_in_para(pxml, new_texts):
    """Replace texts of runs in a paragraph xml. new_texts: list; if shorter than runs, extra runs blanked."""
    runs = list(re.finditer(r'(<a:t>)(.*?)(</a:t>)', pxml, re.S))
    out, last = [], 0
    for k, m in enumerate(runs):
        out.append(pxml[last:m.start(2)])
        out.append(esc(new_texts[k]) if k < len(new_texts) else '')
        last = m.end(2)
    out.append(pxml[last:])
    return ''.join(out)

def set_runs_in_para_shape(block, pi, texts):
    paras = list(re.finditer(r'<a:p>.*?</a:p>', block, re.S))
    assert pi < len(paras), f'para {pi} missing'
    m = paras[pi]
    return block[:m.start()] + set_runs_in_para(m.group(0), texts) + block[m.end():]

def set_shape_paras(x, name, para_map, occ=0):
    """para_map: {para_index: [run texts...]} within shape."""
    def fn(block):
        paras = list(re.finditer(r'<a:p>.*?</a:p>', block, re.S))
        out, last = [], 0
        for pi, m in enumerate(paras):
            out.append(block[last:m.start()])
            out.append(set_runs_in_para(m.group(0), para_map[pi]) if pi in para_map else m.group(0))
            last = m.end()
        out.append(block[last:])
        return ''.join(out)
    return sub_block(x, name, occ, fn)

def set_table(x, anchor, grid):
    """grid[row][col] = new text or None(keep). Applied to the a:tbl containing anchor."""
    p = x.find(anchor)
    assert p != -1, f'table anchor {anchor!r} not found'
    s = x.rfind('<a:tbl>', 0, p); e = x.find('</a:tbl>', p) + len('</a:tbl>')
    tbl = x[s:e]
    trs = list(re.finditer(r'<a:tr .*?</a:tr>', tbl, re.S))
    out, last = [], 0
    for ri, tr in enumerate(trs):
        row = tr.group(0)
        if ri < len(grid) and grid[ri] is not None:
            tcs = list(re.finditer(r'<a:tc(?: [^>]*)?>.*?</a:tc>', row, re.S))
            rout, rlast = [], 0
            for ci, tc in enumerate(tcs):
                cell = tc.group(0)
                if ci < len(grid[ri]) and grid[ri][ci] is not None:
                    ts = list(re.finditer(r'(<a:t>)(.*?)(</a:t>)', cell, re.S))
                    if ts:
                        cout, clast = [], 0
                        for k, m in enumerate(ts):
                            cout.append(cell[clast:m.start(2)])
                            cout.append(esc(grid[ri][ci]) if k == 0 else '')
                            clast = m.end(2)
                        cout.append(cell[clast:])
                        cell = ''.join(cout)
                    elif str(grid[ri][ci]).strip():
                        # empty cell needing content: inject a plain run before endParaRPr
                        cell = re.sub(r'(<a:p>)(<a:endParaRPr)', r'\1<a:r><a:t>' + esc(grid[ri][ci]) + r'</a:t></a:r>\2', cell, 1) \
                            if '<a:endParaRPr' in cell else cell.replace('<a:p/>', '<a:p><a:r><a:t>' + esc(grid[ri][ci]) + '</a:t></a:r></a:p>', 1)
                rout.append(row[rlast:tc.start()]); rout.append(cell); rlast = tc.end()
            rout.append(row[rlast:])
            row = ''.join(rout)
        out.append(tbl[last:tr.start()]); out.append(row); last = tr.end()
    out.append(tbl[last:])
    parts_new = x[:s] + ''.join(out) + x[e:]
    return parts_new

# ---------- chart cache helper ----------
def set_chart(chart_name, cats, series_vals, series_names=None, val_fmt='General'):
    key = f'ppt/charts/{chart_name}.xml'
    x = parts[key].decode('utf8')
    sers = list(re.finditer(r'<c:ser>.*?</c:ser>', x, re.S))
    assert len(sers) == len(series_vals), f'{chart_name}: {len(sers)} sers != {len(series_vals)}'
    out, last = [], 0
    for si, sm in enumerate(sers):
        s = sm.group(0)
        if series_names and series_names[si] is not None:
            s = re.sub(r'(<c:tx>.*?<c:strCache>.*?<c:v>).*?(</c:v>)', lambda m: m.group(1) + esc(series_names[si]) + m.group(2), s, 1, re.S)
        cat_cache = '<c:ptCount val="%d"/>' % len(cats) + ''.join(
            f'<c:pt idx="{k}"><c:v>{esc(c)}</c:v></c:pt>' for k, c in enumerate(cats))
        s = re.sub(r'(<c:cat>.*?<c:(?:str|num)Cache>).*?(</c:(?:str|num)Cache>)',
                   lambda m: m.group(1) + cat_cache + m.group(2), s, 1, re.S)
        vals = series_vals[si]
        val_cache = f'<c:formatCode>{val_fmt}</c:formatCode>' + '<c:ptCount val="%d"/>' % len(vals) + ''.join(
            f'<c:pt idx="{k}"><c:v>{v}</c:v></c:pt>' for k, v in enumerate(vals) if v is not None)
        s = re.sub(r'(<c:val>.*?<c:numCache>).*?(</c:numCache>)',
                   lambda m: m.group(1) + val_cache + m.group(2), s, 1, re.S)
        out.append(x[last:sm.start()]); out.append(s); last = sm.end()
    out.append(x[last:])
    parts[key] = ''.join(out).encode('utf8')
    edits_log.append(f'{chart_name}: cache -> {len(cats)} cats')

def ri(series, idx): return round(series[idx])

# =================================================================
# DATA PREP
# =================================================================
T = CALC['total']['series']
zones = CALC['zones']; chains = CALC['chains']; brands = CALC['brands']
bs = CALC['brand_subcat']; zbs = CALC['zone_brand_subcat']; zb = CALC['zone_brands']; zc = CALC['zone_chains']
l3m_off = (OFFICIAL['Mar-26'] + OFFICIAL['Apr-26'] + OFFICIAL['May-26']) / 3
q1_27 = OFFICIAL['Apr-26'] + OFFICIAL['May-26'] + OFFICIAL['Jun-26']
q1_26 = OFFICIAL['Apr-25'] + OFFICIAL['May-25'] + OFFICIAL['Jun-25']

# =================================================================
# SLIDE 1
# =================================================================
x = get(1)
x = rep_t(x, 'SUMMARY & KEY INSIGHTS MAY’26', "SUMMARY & KEY INSIGHTS JUNE’26 + Q1 FY27", tag='s1 title')
x = rep_t(x, "May'26 NSV", "Jun'26 NSV", tag='s1 kpi1')
x = rep_t(x, '₹ 40.19 Cr', '₹ 36.52 Cr', tag='s1 kpi1v')
x = rep_t(x, "Apr'26 NSV", "May'26 NSV", tag='s1 kpi2')
x = rep_t(x, '₹ 35.89 Cr', '₹ 40.19 Cr', tag='s1 kpi2v')
x = rep_t(x, 'MoM ▲ ', 'MoM ▼ ', tag='s1 mom')
x = x.replace('>12<', '>9<', 1)
x = rep_t(x, '₹ 31.95 Cr', '₹ 36.14 Cr', tag='s1 l3m')
x = x.replace('>26<', '>1<', 1)  # GO L3M
x = rep_t(x, '63.0%', '60.8%', tag='s1 yoy')
x = rep_t(x, '₹ 15.54 Cr', '₹ 13.81 Cr', tag='s1 yoyd')
x = rep_t(x, 'May’26 Chain Sales Contribution % & Sales', 'Jun’26 Chain Sales Contribution % & Sales', tag='s1 mix')
x = rep_t(x, 'Highest-ever', 'Best-ever', tag='s1 badge')
x = rep_t(x, ' NSV', ' June NSV', 1, tag='s1 badge2')
# insight bullets (run mapping)
x = rep_t(x, "May'26 Highest ever NSV offtake & closed at Rs. ", "Jun'26 NSV closed at Rs. ", tag='s1 b1')
x = rep_t(x, '40.19 Cr ', '36.52 Cr ', tag='s1 b1v')
x = rep_t(x, '▲ 63% YoY', '▲ 61% YoY', tag='s1 b1y')
x = rep_t(x, '▲ 25.8%', '▲ 1.1%', tag='s1 b1l')
x = rep_t(x, ' vs L3M Avg, adding +1,554 Lacs YoY. ', ' vs L3M Avg, adding +1,381 Lacs YoY — the best-ever June despite a seasonal ▼9% MoM off the May record. ', tag='s1 b1t')
x = rep_t(x, 'Growth is broad based ', 'Q1 FY27 closed at ', tag='s1 b2a')
x = rep_t(x, '2 ', '₹112.60 Cr, ', tag='s1 b2b')
x = x.replace('>Yr<', '>▲ 61%<', 1)
x = rep_t(x, ' CAGR of 46.5% ', ' vs Q1 FY26 (₹69.92 Cr) ', tag='s1 b2c')
x = rep_t(x, 'confirms this is not a low base artifact as ', '— every zone grew ≥54%; ', tag='s1 b2d')
x = rep_t(x, "May'25 itself grew +31.7% YoY", "growth is broad-based, not a base effect", tag='s1 b2e')
x = rep_t(x, ", Reliance and Apollo delivered 81.1% of May'26 offtake", ", Reliance and Apollo delivered 81.0% of Jun'26 offtake", tag='s1 b3')
x = rep_t(x, ' up from 77% 6 months ago. ', ' — concentration steady vs May; Walmart CNC billed nil in Jun (watch-out). ', tag='s1 b3b')
x = rep_t(x, ' holds 70.6% portfolio share.', ' holds 69.9% portfolio share.', tag='s1 b4')

# Table 28 grid
def chain_row(name, key):
    d = chains[key]; s = d['series']
    l3 = (s[iMar] + s[iA] + s[iM]) / 3
    return [name, R0(s[iJ25]), R0(s[10]), R0(s[iMar]), R0(s[iA]), R0(s[iM]), R0(s[iJ]),
            f'{s[iJ]/OFFICIAL["Jun-26"]*100:.0f}%', R0(l3), arr(pctv(s[iJ], s[iJ25])), arr(pctv(s[iJ], s[iM]))]
rows = [chain_row(*p) for p in [('Dmart','Dmart'),('Reliance','Reliance'),('Apollo','Apollo'),('Fsn','Fsn'),
        ('Wellness','Wellness Forever'),('H&G','H&G'),('Lulu','Lulu'),('Metro','Metro Cnc'),
        ('Delhi RMT','Sancus(Rmt)'),('More Retail','More Retail'),('Walmart','Walmart Cnc'),
        ('Spencer','Spencer'),('Vmm','Vmm')]]
listed = ['Dmart','Reliance','Apollo','Fsn','Wellness Forever','H&G','Lulu','Metro Cnc','Sancus(Rmt)','More Retail','Walmart Cnc','Spencer','Vmm']
oth = [OFFICIAL[M15[k]] - sum(chains[c]['series'][k] for c in listed) for k in range(15)]
ol3 = (oth[iMar]+oth[iA]+oth[iM])/3
rows.append(['Others Combined', R0(oth[iJ25]), R0(oth[10]), R0(oth[iMar]), R0(oth[iA]), R0(oth[iM]), R0(oth[iJ]),
             f'{oth[iJ]/OFFICIAL["Jun-26"]*100:.0f}%', R0(ol3), arr(pctv(oth[iJ], oth[iJ25])), arr(pctv(oth[iJ], oth[iM]))])
rows.append(['Total Channel', R0(OFFICIAL['Jun-25']), R0(OFFICIAL['Feb-26']), R0(OFFICIAL['Mar-26']), R0(OFFICIAL['Apr-26']),
             R0(OFFICIAL['May-26']), R0(OFFICIAL['Jun-26']), None, R0(l3m_off),
             arr(pctv(OFFICIAL['Jun-26'], OFFICIAL['Jun-25'])), arr(pctv(OFFICIAL['Jun-26'], OFFICIAL['May-26']))])
hdr = ['Chain','Jun-25','Feb-26','Mar-26','Apr-26','May-26','Jun-26',None,None,None,None]
hdr2 = [None]*9 + ['Jun', None]
grid = [hdr, hdr2] + rows
x = set_table(x, '>Delhi RMT<', grid)
# fix L3M header note
x = rep_t(x, 'Avg(FMA)', 'Avg(MAM)', tag='s1 l3mhdr')
put(1, x)

set_chart('chart1', ['Feb-26','Mar-26','Apr-26','May-26','Jun-26'] and ['Jan-26','Feb-26','Mar-26','Apr-26','May-26','Jun-26'],
          [[OFFICIAL[m] for m in M15[9:]],
           [ri(chains['Dmart']['series'], k) for k in range(9, 15)],
           [ri(chains['Reliance']['series'], k) for k in range(9, 15)],
           [ri(chains['Apollo']['series'], k) for k in range(9, 15)]])
top10 = [('D-mart','Dmart'),('Reliance','Reliance'),('Apollo','Apollo'),('FSN','Fsn'),('Wellness Forever','Wellness Forever'),
         ('H&G','H&G'),('Lulu','Lulu'),('Metro CNC','Metro Cnc'),('Sancus (RMT)','Sancus(Rmt)'),('More Retail','More Retail')]
set_chart('chart2', [t[0] for t in top10], [[ri(chains[t[1]]['series'], iJ) for t in top10]], series_names=['Jun-26 NSV'])
top7 = [('D-mart','Dmart'),('Reliance','Reliance'),('Apollo','Apollo'),('FSN','Fsn'),('Lulu','Lulu'),('Wellness','Wellness Forever'),('H&G','H&G')]
set_chart('chart3', [t[0] for t in top7], [[round(chains[t[1]]['series'][iJ]/OFFICIAL['Jun-26']*100, 1) for t in top7]])

# =================================================================
# SLIDE 2
# =================================================================
x = get(2)
def chip(x, shape, occ, prefix, p):  # GOLY/MoM chips: replace last value run
    def fn(block):
        ts = list(re.finditer(r'(<a:t>)(.*?)(</a:t>)', block, re.S))
        assert ts, f'no runs in {shape}'
        tgt, blank = ts[-1], None
        if ts[-1].group(2).strip() == '%' and len(ts) >= 2:
            tgt, blank = ts[-2], ts[-1]
        txt = arr(p) if len(ts) > 1 else f'{prefix}{arr(p)}'
        out = block[:tgt.start(2)] + esc(txt) + block[tgt.end(2):]
        if blank is not None:
            shift = len(esc(txt)) - (tgt.end(2) - tgt.start(2))
            out = out[:blank.start(2) + shift] + out[blank.end(2) + shift:]
        return out
    return sub_block(x, shape, occ, fn)

ME_FW, ME_SH, ME_SC = bs['Mamaearth|Face Cleanser'], bs['Mamaearth|Shampoo'], bs['Mamaearth|Sun Care']
TD_FW, TD_SC, TD_FS = bs['The Derma Co.|Face Cleanser'], bs['The Derma Co.|Sun Care'], bs['The Derma Co.|Face Serum']
x = chip(x, 'Text 6', 0, 'GOLY ', ME_FW['goly']); x = chip(x, 'Text 7', 0, 'MoM ', ME_FW['mom'])
x = chip(x, 'Text 10', 0, 'GOLY ', ME_SH['goly']); x = chip(x, 'Text 11', 0, 'MoM ', ME_SH['mom'])
x = chip(x, 'Text 14', 0, 'GOLY ', ME_SC['goly']); x = chip(x, 'Text 15', 0, 'MoM ', ME_SC['mom'])
x = chip(x, 'Text 6', 1, 'GOLY ', TD_FW['goly']); x = chip(x, 'Text 7', 1, 'MoM ', TD_FW['mom'])
x = rep_t(x, "VOLUME VS. VALUE DECOMPOSITION — MAY'26 VS MAY'25", "VOLUME VS. VALUE DECOMPOSITION — MAY'26 VS MAY'25  (QTY EXTRACT: MAY'26 BASIS — JUN'26 AWAITED)", tag='s2 voltitle')
x = rep_t(x, 'Hero SKU note: ', "Hero SKU note (May'26 SKU basis): ", 2, tag='s2 sku')

def brand_row(name, key):
    d = brands[key]; s = d['series']
    l3 = (s[iMar]+s[iA]+s[iM])/3
    return [name, R0(s[iJ25]), R0(s[10]), R0(s[iMar]), R0(s[iA]), R0(s[iM]), R0(s[iJ]),
            f'{s[iJ]/OFFICIAL["Jun-26"]*100:.0f}%', R0(l3), arr(pctv(s[iJ], l3)), arr(pctv(s[iJ], s[iJ25]))]
b3 = ['Mamaearth','The Derma Co.','Aqualogica']
em = [OFFICIAL[M15[k]] - sum(brands[b]['series'][k] for b in b3) for k in range(15)]
eml3 = (em[iMar]+em[iA]+em[iM])/3
g18 = [['Brand','Jun-25','Feb-26','Mar-26','Apr-26','May-26','Jun-26','Cont%','L3M Avg','GO L3M','GOLY Jun'],
       brand_row('Mamaearth','Mamaearth'), brand_row('The Derma Co.','The Derma Co.'), brand_row('Aqualogica','Aqualogica'),
       ['Emerging Brands', R0(em[iJ25]), R0(em[10]), R0(em[iMar]), R0(em[iA]), R0(em[iM]), R0(em[iJ]),
        f'{em[iJ]/OFFICIAL["Jun-26"]*100:.0f}%', R0(eml3), arr(pctv(em[iJ], eml3)), arr(pctv(em[iJ], em[iJ25]))],
       ['Portfolio Total', R0(OFFICIAL['Jun-25']), R0(OFFICIAL['Feb-26']), R0(OFFICIAL['Mar-26']), R0(OFFICIAL['Apr-26']),
        R0(OFFICIAL['May-26']), R0(OFFICIAL['Jun-26']), '100%', R0(l3m_off),
        arr(pctv(OFFICIAL['Jun-26'], l3m_off)), arr(pctv(OFFICIAL['Jun-26'], OFFICIAL['Jun-25']))]]
x = set_table(x, '>Portfolio Total<', g18)
# strategic text
meS, tdS, aqS = brands['Mamaearth'], brands['The Derma Co.'], brands['Aqualogica']
x = rep_t(x, 'remains the portfolio Leader at 70.6% share, growing a steady +30% YoY. ',
          f"remains the portfolio Leader at {meS['cur']/OFFICIAL['Jun-26']*100:.1f}% share, growing a steady +{meS['goly']:.0f}% YoY. ", tag='s2 me')
x = rep_t(x, 'is the fastest scaling brand now 27.4% of NSV vs single digits a ',
          f"is the fastest scaling brand now {tdS['cur']/OFFICIAL['Jun-26']*100:.1f}% of NSV vs single digits a ", tag='s2 td')
x = rep_t(x, 'continues to show positive structural growth, with ▲13% YoY, ▲7% MoM, and ▲25% vs L3M average. However, its current contribution remains relatively small, so it is not yet materially influencing the overall portfolio trajectory.',
          f"holds structural growth at {arr(aqS['goly'])} YoY, though Jun cooled {arr(aqS['mom'])} MoM with Sun Care seasonality. Contribution remains small ({aqS['cur']/OFFICIAL['Jun-26']*100:.1f}%), so it is not yet moving the overall portfolio trajectory.", tag='s2 aq')
put(2, x)

catsJ = ['Jun','Jul','Aug','Sep','Oct','Nov','Dec','Jan','Feb','Mar','Apr','May','Jun']
for cname, d in [('chart4', ME_FW), ('chart5', ME_SH), ('chart6', ME_SC), ('chart7', TD_FW), ('chart8', TD_SC), ('chart9', TD_FS)]:
    set_chart(cname, catsJ, [[ri(d['series'], k) for k in range(2, 15)]])

# =================================================================
# SLIDE 3
# =================================================================
x = get(3)
x = rep_t(x, 'Zone share, May’26 NSV and growth view', 'Zone share, Jun’26 NSV and growth view', tag='s3 sub')
x = rep_t(x, 'Zone May’26 NSV and Share', 'Zone Jun’26 NSV and Share', tag='s3 t')
W, E, N, S1, S2, PAN = zones['WEST'], zones['EAST'], zones['NORTH'], zones['SOUTH-1'], zones['SOUTH-2'], zones['PAN INDIA']
x = set_shape_paras(x, 'Text 65', {
    0: ['Zone Insights | Jun’26'],
    1: ['West remained the largest zone', ' with NSV of ', f'₹{ri(W["series"],iJ):,} Lacs', ', contributing ', f'{W["share_jun"]:.1f}%', ' to overall MT offtake.'],
    2: ['Every zone grew ≥54% YoY in Jun’26', ' — the growth mix stays broad-based across the national footprint.'],
    3: ['East delivered the strongest YoY growth at ', f'{arr(E["goly"])}, ', 'with North (+65%) and South-1 (+63%) close behind — scale-up momentum is holding.'],
    4: ['Dmart', ' is the #1 chain in 4 out of 5 zones', ': North, South-1, South-2 and West — overtaking Apollo in South-1 this month. This confirms ', 'Dmart', ' as a national growth engine, not limited to one zone.'],
    5: ['Apollo holds #2 in the southern zones and remains the pharmacy-channel engine', ', though Jun cooled ▼20% MoM after the May high, largely driven by ', 'The Derma Co.'],
    9: ['The Derma Co. held ₹1,010 Lacs in Jun (record ₹1,100 in May)', ', contributing ', '27.7%', ' to the portfolio. The brand grew ', '▲388% ', 'YoY', ', still the fastest-scaling growth engine in the portfolio.'],
    10: ['Face Cleanser and Sun Care remained the top 2 growth drivers for The Derma Co. in 5 out of 6 zones', ', making them the clearest scale-up levers. ', 'FSN grew +32% YoY — improving, but still slower than the network (+61%).'],
    12: ['Sun Care cooled seasonally across zones (▼30% MoM off the summer peak)', ' — in line with category seasonality; sunscreen distribution gains should be protected into monsoon.'],
})
def zrow(label, d):
    s = d['series']; l3 = (s[iMar]+s[iA]+s[iM])/3
    return [label, R0(s[iJ25]), R0(s[iMar]), R0(s[iA]), R0(s[iM]), R0(s[iJ]),
            f'{d["share_jun"]:.0f}%', R0(l3), arr(pctv(s[iJ], l3)), arr(pctv(s[iJ], s[iJ25]))]
g239 = [['Zone','Jun-25','Mar-26','Apr-26','May-26','Jun-26','Zone Share','L3M Avg','GO L3M','GOLY Jun'],
        zrow('East', E), zrow('North', N), zrow('South-1', S1), zrow('South-2', S2), zrow('West', W), zrow('FSN', PAN)]
x = set_table(x, '>GOLY May<', g239)
put(3, x)

zcats = ['East','North','South-1','South-2','West','Pan India']
set_chart('chart10', zcats, [[ri(E['series'],iJ), ri(N['series'],iJ), ri(S1['series'],iJ), ri(S2['series'],iJ), ri(W['series'],iJ), ri(PAN['series'],iJ)]], series_names=['Jun-26 NSV'])
set_chart('chart11', zcats, [[round(z['share_jun'],1) for z in (E,N,S1,S2,W,PAN)]])

# =================================================================
# ZONE SLIDES 10-15
# =================================================================
ZONE_SLIDES = {10: ('EAST', 'East'), 11: ('NORTH', 'North'), 12: ('SOUTH-1', 'South-1'), 13: ('SOUTH-2', 'South-2'), 14: ('WEST', 'West'), 15: ('PAN INDIA', 'FSN')}
CHIPSETS = [('Text 6','Text 7','Text 8','Mamaearth|Face Cleanser'), ('Text 10','Text 11','Text 12','Mamaearth|Shampoo'),
            ('Text 14','Text 15','Text 16','Mamaearth|Sun Care'), ('Text 20','Text 21','Text 22','The Derma Co.|Face Cleanser'),
            ('Text 24','Text 25','Text 26','The Derma Co.|Sun Care'), ('Text 28','Text 29','Text 30','The Derma Co.|Face Serum')]
ZONE_CHAINTBL = {
    10: [('Reliance','Reliance'),('Apollo','Apollo'),('VMM','Vmm'),('More Retail','More Retail'),('Frankros','Frankros'),('Spencer','Spencer')],
    11: [('Dmart','Dmart'),('Reliance','Reliance'),('Apollo','Apollo'),('Sancus(Rmt)','Sancus(Rmt)'),('Lulu','Lulu'),('Metro Cnc','Metro Cnc')],
    12: [('Apollo','Apollo'),('Dmart','Dmart'),('Reliance','Reliance'),('Lulu','Lulu'),('H&G','H&G'),('Metro Cnc','Metro Cnc')],
    13: [('Dmart','Dmart'),('Apollo','Apollo'),('Reliance','Reliance'),('H&G','H&G'),('More Retail','More Retail'),('Lulu','Lulu')],
    14: [('Dmart','Dmart'),('Reliance','Reliance'),('Wellness Forever','Wellness Forever'),('Apollo','Apollo'),('Metro Cnc','Metro Cnc'),('Trent','Trent')],
    15: [('Fsn','Fsn')],
}
def try_chip(x, shape, occ, prefix, val):
    try: return chip(x, shape, occ, prefix, val)
    except AssertionError: return x
def try_rep_shape_last_num(x, shape, newlabel, newval):
    """Jun'26 value chips: first run label, last run value (or single combined run)."""
    def fn(block):
        ts = list(re.finditer(r'(<a:t>)(.*?)(</a:t>)', block, re.S))
        texts = [m.group(2) for m in ts]
        if len(ts) == 1:
            new = [f'{newlabel} {newval}']
        else:
            new = list(texts)
            if texts[0].strip().startswith(('May', 'Jun')): new[0] = f'{newlabel} '
            new[-1] = str(newval)
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

for sn, (zkey, zlabel) in ZONE_SLIDES.items():
    x = get(sn)
    Z = zones[zkey]; s = Z['series']
    cur, mom, goly, gol3, l3, share = ri(s, iJ), Z['mom'], Z['goly'], Z['go_l3m'], Z['l3m'], Z['share_jun']
    q1z, q1zg = Z['q1_27'], pctv(Z['q1_27'], Z['q1_26'])
    x = rep_t(x, 'May-26 Sales', 'Jun-26 Sales', tag=f's{sn} kpi')
    x = sub_block(x, 'Textbox 253', 0, lambda b: set_runs_in_para_shape(b, 1, [str(cur)]))
    x = sub_block(x, 'Textbox 257', 0, lambda b: set_runs_in_para_shape(b, 1, [f'{share:.1f}%']))
    x = sub_block(x, 'Textbox 261', 0, lambda b: set_runs_in_para_shape(b, 1, [R0(l3)]))
    x = rep_t(x, 'GOLY May', 'GOLY Jun', tag=f's{sn} goly')
    x = sub_block(x, 'Textbox 265', 0, lambda b: set_runs_in_para_shape(b, 1, [arr(goly)]))
    # highlights box
    peak = max(range(15), key=lambda k: s[k])
    if peak == iJ:
        p2 = [f'Zone Record: Jun-26 delivered the highest month for {zlabel} at {cur}, contributing {share:.1f}% to total channel sales. Q1 FY27 = {R0(q1z)} Lacs, {arr(q1zg)} vs Q1 FY26.']
    else:
        p2 = [f'Zone View: Jun-26 closed at {cur} for {zlabel} ({share:.1f}% of channel), {arr(mom)} MoM off the {M15[peak]} record of {ri(s,peak)}. Q1 FY27 = {R0(q1z)} Lacs, {arr(q1zg)} vs Q1 FY26.']
    p3 = [f'Growth View: Jun-26 was {arr(gol3)} vs L3M and {arr(goly)} vs Jun-25 — YoY momentum intact despite seasonal moderation.']
    pm = {2: p2, 3: p3}
    if sn == 15:
        pm = {2: [f'Chain View: Jun-26 closed at {cur} for FSN ({share:.1f}% of channel), {arr(mom)} MoM. Q1 FY27 = {R0(q1z)} Lacs, {arr(q1zg)} vs Q1 FY26.'],
              3: [f'Growth View: Jun-26 was {arr(gol3)} vs L3M and {arr(goly)} vs Jun-25 — best month since the Apr-26 record of 229.'],
              4: ['Zone Insight: FSN improved to +32% YoY but still trails the network (+61%); assortment plus promo refresh remains the lever.']}
    x = set_shape_paras(x, 'Textbox 268', pm)
    # chart chips
    zd = zbs['Pan India' if sn == 15 else zkey]
    for gshape, mshape, vshape, key in CHIPSETS:
        if key not in zd: continue
        d = zd[key]
        x = try_chip(x, gshape, 0, 'GOLY ', d['goly'])
        x = try_chip(x, mshape, 0, 'MoM ', d['mom'])
        x = try_rep_shape_last_num(x, vshape, "Jun'26", ri(d['series'], iJ))
    # brand table
    zbd = zb['Pan India' if sn == 15 else zkey]
    ztot = [sum(zbd[b]['series'][k] for b in ['Mamaearth','The Derma Co.','Aqualogica','Emerging Brands']) for k in range(15)]
    def brow(name):
        d = zbd[name]; ss = d['series']; l3b = (ss[iMar]+ss[iA]+ss[iM])/3
        base = [name, R0(ss[iJ25]), R0(ss[iM]), R0(ss[iJ]), f'{(ss[iJ]/ztot[iJ]*100) if ztot[iJ] else 0:.0f}%', R0(l3b)]
        if name == 'Emerging Brands': return base + [None, None]
        return base + [arr(pctv(ss[iJ], l3b)), arr(pctv(ss[iJ], ss[iJ25]))]
    g190 = [['Brand','Jun-25','May-26','Jun-26','Cont %','L3M','GO L3M','GOLY'],
            brow('Mamaearth'), brow('The Derma Co.'), brow('Aqualogica'), brow('Emerging Brands')]
    x = set_table(x, '>Emerging Brands<', g190)
    # chain table
    zcd = zc.get(zkey, {})
    if sn == 15:
        f = CALC['chains']['Fsn']; ss = f['series']; l3c = (ss[iMar]+ss[iA]+ss[iM])/3
        g193 = [['Chain','Jun-25','May-26','Jun-26','Cont%','L3M','GO L3M','GOLY'],
                ['Fsn', R0(ss[iJ25]), R0(ss[iM]), R0(ss[iJ]), '100%', R0(l3c), arr(pctv(ss[iJ], l3c)), arr(pctv(ss[iJ], ss[iJ25]))],
                ['Others Combined','0','0','0','0%','0',None,None]]
    else:
        g193 = [['Chain','Jun-25','May-26','Jun-26','Cont%','L3M','GO L3M','GOLY']]
        listed_z = []
        for disp, key in ZONE_CHAINTBL[sn]:
            d = zcd[key]; ss = d['series']; l3c = (ss[iMar]+ss[iA]+ss[iM])/3
            listed_z.append(key)
            g193.append([disp, R0(ss[iJ25]), R0(ss[iM]), R0(ss[iJ]), f'{ss[iJ]/s[iJ]*100:.0f}%', R0(l3c),
                         arr(pctv(ss[iJ], l3c)), arr(pctv(ss[iJ], ss[iJ25]))])
        o = [s[k] - sum(zcd[c]['series'][k] for c in listed_z if c in zcd) for k in range(15)]
        ol3z = (o[iMar]+o[iA]+o[iM])/3
        g193.append(['Others Combined', R0(o[iJ25]), R0(o[iM]), R0(o[iJ]), f'{(o[iJ]/s[iJ]*100) if s[iJ] else 0:.0f}%', R0(ol3z),
                     arr(pctv(o[iJ], ol3z)) if ol3z else None, arr(pctv(o[iJ], o[iJ25])) if o[iJ25] else None])
    x = set_table(x, '>Others Combined<', g193)
    # bottom highlight strip
    if sn != 15:
        lead_key = max(zcd, key=lambda c: zcd[c]['series'][iJ]); leadv = ri(zcd[lead_key]['series'], iJ)
        eligible = {c: d for c, d in zcd.items() if d['series'][iJ25] >= 3 and d['series'][iJ] >= 3}
        fast_key = max(eligible, key=lambda c: pctv(eligible[c]['series'][iJ], eligible[c]['series'][iJ25]) or -999)
        fastg = pctv(zcd[fast_key]['series'][iJ], zcd[fast_key]['series'][iJ25])
        DISP = {'Dmart':'Dmart','Reliance':'Reliance','Apollo':'Apollo','Vmm':'VMM','More Retail':'More Retail','Frankros':'Frankros','Spencer':'Spencer','Sancus(Rmt)':'Sancus(Rmt)','Lulu':'Lulu','Metro Cnc':'Metro Cnc','H&G':'H&G','Wellness Forever':'Wellness Forever','Trent':'Trent','V-Mart':'V-Mart','Arambagh':'Arambagh','Sumo Save':'Sumo Save','National Mart':'National Mart'}
        x = set_shape_paras(x, 'Textbox 290', {0: [
            f'Zone View: {zlabel} closed Jun-26 at {cur}, {arr(gol3)} vs L3M and {arr(goly)} vs Jun-25; Q1 FY27 {arr(q1zg)} YoY.',
            f' Chain Highlights: {DISP.get(lead_key, lead_key)} leads; {DISP.get(fast_key, fast_key)} is the fastest YoY chain.']})
        x = set_shape_paras(x, 'Textbox 295', {0: [DISP.get(lead_key, lead_key), ' ', '-', ' ', str(leadv)]})
        try:
            x = sub_block(x, 'Textbox 296', 0, lambda b: set_runs_in_para(b, [f'{DISP.get(fast_key, fast_key)}  - ', arr(fastg)]))
        except AssertionError: pass
    else:
        x = set_shape_paras(x, 'Textbox 290', {1: [
            'Chain Highlights:- ', ' ', 'FSN',
            f' closed Jun-26 at {cur}, {arr(gol3)} vs L3M and {arr(goly)} vs Jun-25; the Apr-26 record of 229 stands.']})
        x = set_shape_paras(x, 'Textbox 295', {0: ['Fsn', ' ', '-', ' ', str(cur)]})
        x = sub_block(x, 'Textbox 296', 0, lambda b: set_runs_in_para(b, ['Fsn  - ', arr(goly)]))
    put(sn, x)
    # charts: map graphicFrames in doc order to rels
    rels = parts[f'ppt/slides/_rels/slide{sn}.xml.rels'].decode('utf8')
    rmap = dict(re.findall(r'Id="(rId\d+)"[^>]*Target="\.\./charts/(chart\d+)\.xml"', rels))
    order = re.findall(r'<c:chart [^>]*r:id="(rId\d+)"', get(sn))
    assert len(order) == 6, f'slide{sn}: {len(order)} charts'
    keys = ['Mamaearth|Face Cleanser','Mamaearth|Shampoo','Mamaearth|Sun Care','The Derma Co.|Face Cleanser','The Derma Co.|Sun Care','The Derma Co.|Face Serum']
    for ci, rid in enumerate(order):
        d = zd.get(keys[ci])
        vals = [ri(d['series'], k) for k in range(2, 15)] if d else [0]*13
        set_chart(rmap[rid], catsJ, [vals])

# =================================================================
# SLIDES 4-9: data-basis tag; slide 16-23 footers
# =================================================================
TAG = ('<p:sp><p:nvSpPr><p:cNvPr id="9901" name="DataBasisTag"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
       '<p:spPr><a:xfrm><a:off x="228600" y="6553200"/><a:ext cx="6858000" cy="228600"/></a:xfrm>'
       '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/></p:spPr>'
       '<p:txBody><a:bodyPr wrap="none" anchor="ctr"/><a:lstStyle/><a:p><a:r>'
       '<a:rPr lang="en-IN" sz="900" b="1" i="1"><a:solidFill><a:srgbClr val="C00000"/></a:solidFill></a:rPr>'
       '<a:t>DATA BASIS: MAY’26 — JUN’26 NIELSEN / CHAIN-GS REFRESH AWAITED</a:t></a:r></a:p></p:txBody></p:sp>')
for sn in (4, 5, 6, 7, 8, 9):
    x = get(sn)
    x = x.replace('</p:spTree>', TAG + '</p:spTree>', 1)
    put(sn, x)
x = get(17)
if "May'26" in x: x = x.replace("May'26", "Jun'26")
put(17, x)

# =================================================================
zout = zipfile.ZipFile(f'{WORK}/deck_jun26.pptx', 'w', zipfile.ZIP_DEFLATED)
for n, data in parts.items(): zout.writestr(n, data)
zout.close()
print(f'OK — {len(edits_log)} logged edits; deck_jun26.pptx written')
