#!/usr/bin/env python3
"""Insert a Q1 FY27 scorecard slide after slide 1 of deck_jun26.pptx."""
import zipfile, re, json, html

WORK = '/tmp/claude-0/-home-user-mt-dashboard/8b5ace2f-f399-5f35-b1e6-0bc4693c9034/scratchpad/work'
CALC = json.load(open(f'{WORK}/calc.json'))
esc = lambda s: html.escape(str(s), quote=False)
def q1(d): return d['q1_27'], d['q1_26'], (d['q1_27']/d['q1_26']-1)*100 if d['q1_26'] else None
def arr(p): return '—' if p is None else ('▲' if p >= 0 else '▼') + f' {abs(p):.0f}%'
R0 = lambda x: f'{x:,.0f}'

Q27, Q26 = 11260, 6992  # official grand totals
zones = CALC['zones']; brands = CALC['brands']; chains = CALC['chains']

EMU_IN = 914400
SLDW, SLDH = 12192000, 6858000

sid = 9000
def nid():
    global sid; sid += 1; return sid

def txbox(name, x, y, w, h, paras, anchor='t'):
    body = ''
    B = ' b="1"'; I = ' i="1"'
    for p in paras:
        runs = ''.join(
            f'<a:r><a:rPr lang="en-IN" sz="{r.get("sz",1200)}"{B if r.get("b") else ""}{I if r.get("i") else ""}>'
            f'<a:solidFill><a:srgbClr val="{r.get("color","1A1A2E")}"/></a:solidFill>'
            f'<a:latin typeface="Calibri"/></a:rPr><a:t>{esc(r["t"])}</a:t></a:r>' for r in p['runs'])
        sp_b = f'<a:spcBef><a:spcPts val="{p.get("spcBef",400)}"/></a:spcBef>'
        bu = '<a:buFont typeface="Arial"/><a:buChar char="•"/>' if p.get('bullet') else '<a:buNone/>'
        body += f'<a:p><a:pPr marL="{171450 if p.get("bullet") else 0}" indent="{-171450 if p.get("bullet") else 0}">{sp_b}{bu}</a:pPr>{runs}</a:p>'
    return (f'<p:sp><p:nvSpPr><p:cNvPr id="{nid()}" name="{name}"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>'
            f'<p:spPr><a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{w}" cy="{h}"/></a:xfrm>'
            f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/></p:spPr>'
            f'<p:txBody><a:bodyPr wrap="square" anchor="{anchor}"><a:normAutofit/></a:bodyPr><a:lstStyle/>{body}</p:txBody></p:sp>')

def rect(name, x, y, w, h, fill):
    return (f'<p:sp><p:nvSpPr><p:cNvPr id="{nid()}" name="{name}"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
            f'<p:spPr><a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{w}" cy="{h}"/></a:xfrm>'
            f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:solidFill><a:srgbClr val="{fill}"/></a:solidFill>'
            f'<a:ln><a:noFill/></a:ln></p:spPr><p:txBody><a:bodyPr/><a:lstStyle/><a:p/></p:txBody></p:sp>')

def table(name, x, y, w, colw, rows, rowh=274638):
    """rows: list of list of (text, opts). Row 0 = header."""
    gcols = ''.join(f'<a:gridCol w="{c}"/>' for c in colw)
    trs = ''
    for ri, row in enumerate(rows):
        tcs = ''
        for ci, cell in enumerate(row):
            t, opts = cell if isinstance(cell, tuple) else (cell, {})
            hdr = ri == 0
            color = 'FFFFFF' if hdr else opts.get('color', '1A1A2E')
            b = ' b="1"' if hdr or opts.get('b') else ''
            fill = '1F4E5F' if hdr else ('F2F6F7' if ri % 2 == 0 else 'FFFFFF')
            if opts.get('fill'): fill = opts['fill']
            algn = 'l' if ci == 0 else 'r'
            tcs += (f'<a:tc><a:txBody><a:bodyPr/><a:lstStyle/><a:p><a:pPr algn="{algn}"/>'
                    f'<a:r><a:rPr lang="en-IN" sz="1050"{b}><a:solidFill><a:srgbClr val="{color}"/></a:solidFill>'
                    f'<a:latin typeface="Calibri"/></a:rPr><a:t>{esc(t)}</a:t></a:r></a:p></a:txBody>'
                    f'<a:tcPr marL="54000" marR="54000" marT="18000" marB="18000" anchor="ctr">'
                    f'<a:solidFill><a:srgbClr val="{fill}"/></a:solidFill></a:tcPr></a:tc>')
        trs += f'<a:tr h="{rowh}">{tcs}</a:tr>'
    return (f'<p:graphicFrame><p:nvGraphicFramePr><p:cNvPr id="{nid()}" name="{name}"/><p:cNvGraphicFramePr>'
            f'<a:graphicFrameLocks noGrp="1"/></p:cNvGraphicFramePr><p:nvPr/></p:nvGraphicFramePr>'
            f'<p:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{sum(colw)}" cy="{rowh*len(rows)}"/></p:xfrm>'
            f'<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/table">'
            f'<a:tbl><a:tblPr firstRow="1" bandRow="1"/><a:tblGrid>{gcols}</a:tblGrid>{trs}</a:tbl>'
            f'</a:graphicData></a:graphic></p:graphicFrame>')

shapes = []
# header band
shapes.append(rect('HdrBand', 0, 0, SLDW, 754380, '1F4E5F'))
shapes.append(txbox('Title', 274638, 68580, 9000000, 400000,
    [{'runs': [{'t': 'Q1 FY27 SCORECARD — OFFTAKE', 'sz': 2000, 'b': True, 'color': 'FFFFFF'}], 'spcBef': 0}]))
shapes.append(txbox('SubTitle', 274638, 434340, 11000000, 300000,
    [{'runs': [{'t': "Apr–Jun'26 vs Apr–Jun'25  |  NSV ₹ Lacs  |  MT + EB2B channels", 'sz': 1100, 'color': 'D9E7EA'}], 'spcBef': 0}]))

# KPI strip
kpis = [
    ('Q1 FY27 NSV', '₹ 112.60 Cr', 'vs ₹ 69.92 Cr LY'),
    ('Q1 Growth', '▲ 61.0%', '+ ₹ 42.68 Cr YoY'),
    ('Best Month', "May'26 ₹ 40.19 Cr", 'all-time high'),
    ('Exit Month', "Jun'26 ₹ 36.52 Cr", '▲ 61% YoY | best-ever June'),
]
kx = 274638
for lbl, big, sub in kpis:
    shapes.append(rect(f'KpiCard {lbl}', kx, 937260, 2743200, 868680, 'F2F6F7'))
    shapes.append(txbox(f'Kpi {lbl}', kx + 91440, 982980, 2560320, 800000, [
        {'runs': [{'t': lbl, 'sz': 1000, 'b': True, 'color': '5B7C87'}], 'spcBef': 0},
        {'runs': [{'t': big, 'sz': 1600, 'b': True, 'color': '1F4E5F'}], 'spcBef': 200},
        {'runs': [{'t': sub, 'sz': 950, 'color': '5B7C87'}], 'spcBef': 100},
    ]))
    kx += 2971800

# zone table
zorder = [('East','EAST'), ('North','NORTH'), ('South-1','SOUTH-1'), ('South-2','SOUTH-2'), ('West','WEST'), ('Pan India (FSN)','PAN INDIA')]
zrows = [['Zone', 'Q1 FY26', 'Q1 FY27', 'Growth', 'Mix %']]
for disp, k in zorder:
    a, b, g = q1(zones[k])
    zrows.append([disp, R0(b), R0(a), (arr(g), {'color': '1E7A45' if g >= 0 else 'B23A3A', 'b': True}), f'{a/Q27*100:.0f}%'])
zrows.append([('TOTAL', {'b': True}), (R0(Q26), {'b': True}), (R0(Q27), {'b': True}), (arr((Q27/Q26-1)*100), {'b': True, 'color': '1E7A45'}), ('100%', {'b': True})])
shapes.append(txbox('ZoneHdr', 274638, 1988820, 4000000, 274638, [{'runs': [{'t': 'ZONE VIEW', 'sz': 1150, 'b': True, 'color': '1F4E5F'}], 'spcBef': 0}]))
shapes.append(table('Q1ZoneTbl', 274638, 2286000, 0, [1500000, 850000, 850000, 850000, 700000], zrows))

# brand table
brows = [['Brand', 'Q1 FY26', 'Q1 FY27', 'Growth', 'Mix %']]
for bname in ['Mamaearth', 'The Derma Co.', 'Aqualogica', 'Emerging Brands']:
    a, b, g = q1(brands[bname])
    brows.append([bname, R0(b), R0(a), (arr(g), {'color': '1E7A45' if (g or 0) >= 0 else 'B23A3A', 'b': True}), f'{a/Q27*100:.0f}%'])
shapes.append(txbox('BrandHdr', 5303520, 1988820, 4000000, 274638, [{'runs': [{'t': 'BRAND VIEW', 'sz': 1150, 'b': True, 'color': '1F4E5F'}], 'spcBef': 0}]))
shapes.append(table('Q1BrandTbl', 5303520, 2286000, 0, [1600000, 850000, 850000, 850000, 700000], brows))

# chain table
crows = [['Chain', 'Q1 FY26', 'Q1 FY27', 'Growth', 'Mix %']]
for cname, k in [('Dmart','Dmart'), ('Reliance','Reliance'), ('Apollo','Apollo'), ('FSN','Fsn'), ('Lulu','Lulu'), ('Wellness Forever','Wellness Forever')]:
    a, b, g = q1(chains[k])
    crows.append([cname, R0(b), R0(a), (arr(g), {'color': '1E7A45' if g >= 0 else 'B23A3A', 'b': True}), f'{a/Q27*100:.0f}%'])
shapes.append(txbox('ChainHdr', 5303520, 4360000, 4000000, 274638, [{'runs': [{'t': 'TOP CHAINS', 'sz': 1150, 'b': True, 'color': '1F4E5F'}], 'spcBef': 0}]))
shapes.append(table('Q1ChainTbl', 5303520, 4657725, 0, [1600000, 850000, 850000, 850000, 700000], crows))

# insights panel
tdq = q1(brands['The Derma Co.']); meq = q1(brands['Mamaearth'])
ins = [
    {'runs': [{'t': 'WHAT LEADERSHIP SHOULD TAKE AWAY', 'sz': 1150, 'b': True, 'color': '1F4E5F'}], 'spcBef': 0},
    {'bullet': True, 'runs': [{'t': f"The Derma Co. multiplied ~4.7x YoY in Q1 (₹{tdq[1]/100:,.1f} Cr → ₹{tdq[0]/100:,.1f} Cr) and now holds {tdq[0]/Q27*100:.0f}% of the Q1 mix vs {tdq[1]/Q26*100:.0f}% LY — the structural growth engine.", 'sz': 1050}]},
    {'bullet': True, 'runs': [{'t': f"Mamaearth grew +{meq[2]:.0f}% on the largest base ({meq[0]/Q27*100:.0f}% of mix) — the volume anchor is intact, led by Face Cleanser and Shampoo.", 'sz': 1050}]},
    {'bullet': True, 'runs': [{'t': 'Apollo (+159%) and Lulu (+171%) are the fastest-compounding chains — pharmacy & premium formats deserve incremental assortment and visibility investment.', 'sz': 1050}]},
    {'bullet': True, 'runs': [{'t': "Watch-outs: H&G Q1 ▼14% YoY, Walmart CNC billed nil in Jun'26, Wellness Forever (+17%) trails the network (+61%) — chain-level JBP correction needed.", 'sz': 1050, 'color': '8A2E2E'}]},
    {'bullet': True, 'runs': [{'t': "Seasonality note: Jun ▼9% MoM is Sun Care-led (▼30% MoM) and in line with category; exit-month YoY of +61% keeps the FY27 run-rate on track.", 'sz': 1050}]},
]
shapes.append(txbox('Insights', 274638, 4560000, 4800600, 2000000, ins))

NSMAP = ('xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
         'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
         'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"')
slide_xml = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<p:sld {NSMAP}><p:cSld><p:spTree>'
             '<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
             '<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/>'
             '<a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>'
             + ''.join(shapes) +
             '</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sld>')

# ---- repackage ----
src = f'{WORK}/deck_jun26.pptx'
zin = zipfile.ZipFile(src)
parts = {n: zin.read(n) for n in zin.namelist()}
zin.close()

NEW = 'ppt/slides/slide24.xml'
parts[NEW] = slide_xml.encode('utf8')
parts['ppt/slides/_rels/slide24.xml.rels'] = (
    b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    b'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    b'<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>'
    b'</Relationships>')

ct = parts['[Content_Types].xml'].decode('utf8')
assert 'slide24.xml' not in ct
ct = ct.replace('</Types>',
    '<Override PartName="/ppt/slides/slide24.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/></Types>')
parts['[Content_Types].xml'] = ct.encode('utf8')

prels = parts['ppt/_rels/presentation.xml.rels'].decode('utf8')
rids = [int(m) for m in re.findall(r'Id="rId(\d+)"', prels)]
newr = max(rids) + 1
prels = prels.replace('</Relationships>',
    f'<Relationship Id="rId{newr}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide24.xml"/></Relationships>')
parts['ppt/_rels/presentation.xml.rels'] = prels.encode('utf8')

pres = parts['ppt/presentation.xml'].decode('utf8')
sldids = [int(m) for m in re.findall(r'<p:sldId id="(\d+)"', pres)]
newid = max(sldids) + 1
first = re.search(r'<p:sldId id="\d+" r:id="rId\d+"/>', pres)
pres = pres[:first.end()] + f'<p:sldId id="{newid}" r:id="rId{newr}"/>' + pres[first.end():]
parts['ppt/presentation.xml'] = pres.encode('utf8')

out = f'{WORK}/deck_jun26_final.pptx'
zo = zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED)
for n, d in parts.items(): zo.writestr(n, d)
zo.close()
print('Q1 slide inserted ->', out)
