import zipfile, re, json

SLIDE_W, SLIDE_H = 7562850, 10688638
PAD = 190500  # 20px @ 96dpi

BLUE = '4472C4'   # Primary (billing-in)
ORANGE = 'ED7D31' # Offtake (sell-out)
GREEN = '1F7A3D'
RED = 'C00000'
GREY = '404040'
HEADER_BLUE = '1F4E79'
LIGHT = 'F2F2F2'
CALLOUT_FILL = 'FFF6E0'

_ids = [1000]
def nid():
    _ids[0] += 1
    return _ids[0]

def esc(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

def rect(x, y, cx, cy, fill=None, line=None, name='Rect'):
    fillxml = f'<a:solidFill><a:srgbClr val="{fill}"/></a:solidFill>' if fill else '<a:noFill/>'
    linexml = f'<a:ln w="6350"><a:solidFill><a:srgbClr val="{line}"/></a:solidFill></a:ln>' if line else '<a:ln><a:noFill/></a:ln>'
    return (f'<p:sp><p:nvSpPr><p:cNvPr id="{nid()}" name="{name}"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
            f'<p:spPr><a:xfrm><a:off x="{int(x)}" y="{int(y)}"/><a:ext cx="{max(1,int(cx))}" cy="{max(1,int(cy))}"/></a:xfrm>'
            f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>{fillxml}{linexml}</p:spPr>'
            f'<p:txBody><a:bodyPr/><a:lstStyle/><a:p/></p:txBody></p:sp>')

def rrect(x, y, cx, cy, fill=None, line=None, name='RRect'):
    fillxml = f'<a:solidFill><a:srgbClr val="{fill}"/></a:solidFill>' if fill else '<a:noFill/>'
    linexml = f'<a:ln w="6350"><a:solidFill><a:srgbClr val="{line}"/></a:solidFill></a:ln>' if line else '<a:ln><a:noFill/></a:ln>'
    return (f'<p:sp><p:nvSpPr><p:cNvPr id="{nid()}" name="{name}"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
            f'<p:spPr><a:xfrm><a:off x="{int(x)}" y="{int(y)}"/><a:ext cx="{max(1,int(cx))}" cy="{max(1,int(cy))}"/></a:xfrm>'
            f'<a:prstGeom prst="roundRect"><a:avLst><a:gd name="adj" fmla="val 5000"/></a:avLst></a:prstGeom>{fillxml}{linexml}</p:spPr>'
            f'<p:txBody><a:bodyPr/><a:lstStyle/><a:p/></p:txBody></p:sp>')

def text(x, y, cx, cy, runs, align='l', anchor='t', name='Text', wrap=True, autofit=False):
    """runs: list of (text, sz, bold, color)"""
    paras = {}
    body = ''
    for t, sz, b, color in runs:
        bstr = ' b="1"' if b else ''
        colorxml = f'<a:solidFill><a:srgbClr val="{color}"/></a:solidFill>' if color else ''
        body += (f'<a:p><a:pPr algn="{align}"/><a:r><a:rPr lang="en-US" sz="{sz}"{bstr} dirty="0">{colorxml}'
                 f'<a:latin typeface="Calibri" pitchFamily="34" charset="0"/></a:rPr>'
                 f'<a:t>{esc(t)}</a:t></a:r></a:p>')
    wrapv = 'square' if wrap else 'none'
    af = '<a:normAutofit fontScale="90000"/>' if autofit else ''
    return (f'<p:sp><p:nvSpPr><p:cNvPr id="{nid()}" name="{name}"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
            f'<p:spPr><a:xfrm><a:off x="{int(x)}" y="{int(y)}"/><a:ext cx="{int(cx)}" cy="{int(cy)}"/></a:xfrm>'
            f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/></p:spPr>'
            f'<p:txBody><a:bodyPr anchor="{anchor}" wrap="{wrapv}">{af}</a:bodyPr><a:lstStyle/>{body}</p:txBody></p:sp>')

def header_frame(title, subtitle, brand_line):
    assert len(title) <= 65, f'title too long ({len(title)}): {title}'
    shapes = []
    shapes.append(rect(0, 0, SLIDE_W, 502920, fill=HEADER_BLUE, name='HeaderBg'))
    shapes.append(text(228600, 60000, SLIDE_W - 457200, 180000,
                        [(brand_line, 900, False, 'BDD7EE')], name='BrandAnchor'))
    shapes.append(text(228600, 200000, SLIDE_W - 457200, 210000,
                        [(title, 1600, True, 'FFFFFF')], name='Title'))
    shapes.append(text(228600, 380000, SLIDE_W - 457200, 140000,
                        [(subtitle, 1000, False, 'D9E2F3')], name='Subtitle'))
    return ''.join(shapes)

def kpi_column(x, y, cx, cy, tiles):
    """tiles: list of (label, value_str, delta_str_or_None, color)"""
    n = len(tiles)
    gap = PAD
    tile_h = (cy - gap * (n - 1)) / n
    shapes = []
    ty = y
    for label, value, delta, color in tiles:
        shapes.append(rrect(x, ty, cx, tile_h, fill=LIGHT, line='D9D9D9', name='KpiTile'))
        shapes.append(rect(x, ty, 55000, tile_h, fill=color, name='KpiAccent'))
        pad_in = 120000
        shapes.append(text(x + pad_in, ty + 90000, cx - 2 * pad_in, tile_h * 0.35,
                            [(label, 1000, True, GREY)], name='KpiLabel'))
        shapes.append(text(x + pad_in, ty + tile_h * 0.40, cx - 2 * pad_in, tile_h * 0.45,
                            [(value, 1800, True, color)], name='KpiValue'))
        if delta:
            shapes.append(text(x + pad_in, ty + tile_h * 0.78, cx - 2 * pad_in, tile_h * 0.20,
                                [(delta, 1000, False, GREY)], name='KpiDelta'))
        ty += tile_h + gap
    return ''.join(shapes)

def paired_bar_rows(x, y, cx, cy, items, max_val, unit='L'):
    """items: list of (label, primary_val, offtake_val, sellout_pct_str, flag_color)"""
    n = len(items)
    row_gap = 40000
    row_h = (cy - row_gap * (n - 1)) / n
    shapes = []
    label_w = int(cx * 0.30)
    bar_x = x + label_w + 40000
    bar_area_w = cx - label_w - 40000 - 620000  # reserve right space for sellout% chip
    bar_h = row_h * 0.32
    ry = y
    for label, pv, ov, so_str, flag in items:
        shapes.append(text(x, ry, label_w, row_h, [(label, 1000, True, GREY)], anchor='ctr', name='RowLabel'))
        pw = max(4000, bar_area_w * (pv / max_val)) if max_val else 4000
        ow = max(4000, bar_area_w * (ov / max_val)) if max_val else 4000
        shapes.append(rect(bar_x, ry + row_h * 0.06, pw, bar_h, fill=BLUE, name='PrimaryBar'))
        shapes.append(text(bar_x + pw + 30000, ry + row_h * 0.02, 620000, bar_h + 40000,
                            [(f'{pv:,.0f}{unit}', 800, False, BLUE)], anchor='ctr', name='PrimaryVal'))
        shapes.append(rect(bar_x, ry + row_h * 0.52, ow, bar_h, fill=ORANGE, name='OfftakeBar'))
        shapes.append(text(bar_x + ow + 30000, ry + row_h * 0.48, 620000, bar_h + 40000,
                            [(f'{ov:,.0f}{unit}', 800, False, ORANGE)], anchor='ctr', name='OfftakeVal'))
        shapes.append(rrect(x + cx - 560000, ry + row_h * 0.15, 560000, row_h * 0.7, fill=flag, name='SOChip'))
        shapes.append(text(x + cx - 560000, ry + row_h * 0.15, 560000, row_h * 0.7,
                            [(so_str, 1000, True, 'FFFFFF')], align='ctr', anchor='ctr', name='SOChipTxt'))
        ry += row_h + row_gap
    # legend
    return ''.join(shapes)

def legend(x, y):
    return (rect(x, y, 140000, 100000, fill=BLUE, name='LegPrimary') +
            text(x + 170000, y - 30000, 900000, 160000, [('Primary (billed-in)', 900, False, GREY)], name='LegPrimaryTxt') +
            rect(x + 1300000, y, 140000, 100000, fill=ORANGE, name='LegOfftake') +
            text(x + 1470000, y - 30000, 900000, 160000, [('Offtake (sold-out)', 900, False, GREY)], name='LegOfftakeTxt'))

def scr_box(x, y, cx, cy, situation, complication, resolution):
    for lbl, s in [('Situation', situation), ('Complication', complication), ('Resolution', resolution)]:
        assert len(s) <= 110, f'{lbl} too long ({len(s)}): {s}'
    body = (f'<p:sp><p:nvSpPr><p:cNvPr id="{nid()}" name="SCRBox"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
            f'<p:spPr><a:xfrm><a:off x="{int(x)}" y="{int(y)}"/><a:ext cx="{int(cx)}" cy="{int(cy)}"/></a:xfrm>'
            f'<a:prstGeom prst="roundRect"><a:avLst><a:gd name="adj" fmla="val 3226"/></a:avLst></a:prstGeom>'
            f'<a:solidFill><a:srgbClr val="{CALLOUT_FILL}"/></a:solidFill><a:ln/></p:spPr>'
            f'<p:txBody><a:bodyPr anchor="t" wrap="square"><a:normAutofit fontScale="88000" lnSpcReduction="10000"/></a:bodyPr><a:lstStyle/>')
    def p(label, txt_, color):
        return (f'<a:p><a:r><a:rPr lang="en-US" sz="1100" b="1" dirty="0"><a:solidFill><a:srgbClr val="{color}"/></a:solidFill>'
                f'<a:latin typeface="Calibri" pitchFamily="34" charset="0"/></a:rPr><a:t>{esc(label)}</a:t></a:r></a:p>'
                f'<a:p><a:r><a:rPr lang="en-US" sz="1000" dirty="0"><a:solidFill><a:srgbClr val="{GREY}"/></a:solidFill>'
                f'<a:latin typeface="Calibri" pitchFamily="34" charset="0"/></a:rPr><a:t>{esc(txt_)}</a:t></a:r></a:p>'
                f'<a:p><a:endParaRPr sz="400"/></a:p>')
    body += p('SITUATION', situation, HEADER_BLUE)
    body += p('COMPLICATION', complication, RED)
    body += p('RESOLUTION', resolution, GREEN)
    body += '</p:txBody></p:sp>'
    return body

def three_split_slide(title, subtitle, brand_line, kpi_tiles, bar_items, max_val, scr_texts, footnote=None, unit='L'):
    header = header_frame(title, subtitle, brand_line)

    body_y = 502920 + PAD
    body_h = SLIDE_H - body_y - 300000  # leave room for footnote/pagenum

    margin = 228600
    gap = 150000
    usable = SLIDE_W - 2 * margin - 2 * gap
    left_w = int(usable * 0.25)
    center_w = int(usable * 0.50)
    right_w = usable - left_w - center_w

    left_x = margin
    center_x = left_x + left_w + gap
    right_x = center_x + center_w + gap

    col1 = kpi_column(left_x, body_y, left_w, body_h, kpi_tiles)

    center_title = text(center_x, body_y, center_w, 200000,
                         [('Primary vs. Offtake — Sell-Out Tracking', 1100, True, GREY)], name='CenterTitle')
    leg = legend(center_x, body_y + 220000)
    bars = paired_bar_rows(center_x, body_y + 420000, center_w, body_h - 420000, bar_items, max_val, unit=unit)
    col2 = center_title + leg + bars

    col3 = scr_box(right_x, body_y, right_w, body_h, *scr_texts)

    foot = ''
    if footnote:
        foot = text(margin, SLIDE_H - 280000, SLIDE_W - 2 * margin, 200000,
                     [(footnote, 800, False, '808080')], name='Footnote')

    return header + col1 + col2 + col3 + foot

def slide_xml(content):
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
<p:cSld><p:spTree>
<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>
{content}
</p:spTree></p:cSld><p:clrMapOvr><a:overrideClrMapping bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/></p:clrMapOvr>
</p:sld>'''

# ============ LOAD REAL DATA ============
d = json.load(open('calc3_sellout.json'))

def flag_color(so):
    if so is None:
        return '808080'
    if so >= 100:
        return RED       # offtake > primary -> OOS / under-stock risk
    if so >= 88:
        return GREEN      # healthy
    return '#'.replace('#','E2A500')  # amber -> moderate over-stock (placeholder fix below)
def flagc(so):
    if so is None: return '808080'
    if so >= 100: return RED
    if so >= 88: return GREEN
    return 'E2A500'

# ---------- SLIDE 1: EXECUTIVE ----------
e = d['exec']
so_q1 = e['matched_offtake_q1'] / e['matched_primary_q1'] * 100
so_jun_num = None
gap_q1 = e['matched_primary_q1'] - e['matched_offtake_q1']
exec_kpis = [
    ('Total Primary (Q1 FY27)', f"Rs {e['matched_primary_q1']:,.0f}L", '26-chain matched universe', BLUE),
    ('Total Offtake (Q1 FY27)', f"Rs {e['matched_offtake_q1']:,.0f}L", 'Same 26-chain universe', ORANGE),
    ('Sell-Out %', f"{so_q1:.1f}%", f"Gap: Rs {gap_q1:,.0f}L billed-not-sold", flagc(so_q1)),
]
exec_bar_items = [
    ('Q1 FY27\n(Apr-Jun26)', e['matched_primary_q1'], e['matched_offtake_q1'], f"{so_q1:.0f}%", flagc(so_q1)),
    ("Jun'26", e['matched_primary_jun'], e['matched_offtake_jun'], f"{e['matched_offtake_jun']/e['matched_primary_jun']*100:.0f}%", flagc(e['matched_offtake_jun']/e['matched_primary_jun']*100)),
]
exec_max = max(e['matched_primary_q1'], e['matched_offtake_q1'])
exec_scr = (
    f"Q1 FY27: Primary Rs{e['matched_primary_q1']:,.0f}L vs Offtake Rs{e['matched_offtake_q1']:,.0f}L - Sell-Out {so_q1:.1f}%.",
    f"Rs{gap_q1:,.0f}L billed but not yet sold-through - trade inventory is building faster than consumer offtake.",
    "Slow Q2 primary billing pace vs Q1 to let channel inventory normalize; prioritize sell-out schemes.",
)
slide1_content = three_split_slide(
    "Primary vs. Offtake Sell-Out — Executive View",
    "Q1 FY26-27 (Apr-Jun'26) consolidated | 26-chain matched universe (Primary & Offtake both report)",
    "Portfolio | All Categories | Executive Summary",
    exec_kpis, exec_bar_items, exec_max, exec_scr,
    footnote="Sell-Out % = Offtake / Primary Billing x 100. Matched universe = chains present in both Primary and Offtake reporting (see Chain_Mapping sheet).",
)

# ---------- SLIDE 2: CHAIN / KAM ----------
c = d['chain']
focus_chains = ['Dmart', 'Reliance', 'Apollo', 'Metro Cnc', 'Lulu', 'H&G']
MATERIALITY = 20.0  # Rs Lacs Q1 primary floor
chain_items = []
for name in focus_chains:
    r = c[name]
    if r['primary_q1'] < MATERIALITY:
        continue
    so = r['sellout_q1']
    chain_items.append((name, r['primary_q1'], r['offtake_q1'], f"{so:.0f}%" if so is not None else 'n/a', flagc(so)))
chain_max = max(max(i[1], i[2]) for i in chain_items)

dmart = c['Dmart']; metro = c['Metro Cnc']; reliance = c['Reliance']
chain_kpis = [
    ('Weakest Sell-Out (Q1)', f"Dmart {dmart['sellout_q1']:.0f}%", f"Primary Rs{dmart['primary_q1']:,.0f}L vs Offtake Rs{dmart['offtake_q1']:,.0f}L", RED),
    ('OOS Risk Flag (Q1)', f"Metro Cnc {metro['sellout_q1']:.0f}%", 'Offtake exceeds Primary - stock depleting', RED),
    ('Healthiest Large KAM', f"Reliance {reliance['sellout_q1']:.0f}%", f"Primary Rs{reliance['primary_q1']:,.0f}L vs Offtake Rs{reliance['offtake_q1']:,.0f}L", GREEN),
]
chain_scr = (
    f"Dmart Q1: Primary Rs{dmart['primary_q1']:,.0f}L, Offtake Rs{dmart['offtake_q1']:,.0f}L - Sell-Out {dmart['sellout_q1']:.0f}%, weakest large KAM.",
    "Dmart and Lulu show Primary well ahead of Offtake - stock sitting in DC/store, near-expiry claim risk builds.",
    "Freeze incremental Dmart/Lulu primary orders this cycle; secure urgent PO for Metro Cnc (OOS risk).",
)
slide2_content = three_split_slide(
    "Primary vs. Offtake Sell-Out — Chain / KAM View",
    "Q1 FY26-27 (Apr-Jun'26) | Key accounts: Dmart, Reliance, Apollo + top format chains",
    "Portfolio | All Categories | Chain-Level Deep Dive",
    chain_kpis, chain_items, chain_max, chain_scr,
    footnote="Chains matched via Chain_Mapping sheet (confirmed name pairs only). Chains with Q1 Primary <Rs20L excluded as immaterial.",
)

# ---------- SLIDE 3: ZONE ----------
z = d['zone']
zone_items = []
for name, r in z.items():
    so = r['sellout_q1']
    zone_items.append((name, r['primary_q1'], r['offtake_q1'], f"{so:.0f}%", flagc(so)))
zone_max = max(max(i[1], i[2]) for i in zone_items)

worst_zone = min(z.items(), key=lambda kv: kv[1]['sellout_q1'])
best_zone = max(z.items(), key=lambda kv: kv[1]['sellout_q1'])
zone_kpis = [
    ('Weakest Zone Sell-Out', f"{worst_zone[0]} {worst_zone[1]['sellout_q1']:.0f}%", f"Primary Rs{worst_zone[1]['primary_q1']:,.0f}L vs Offtake Rs{worst_zone[1]['offtake_q1']:,.0f}L", RED),
    ('Strongest Zone Sell-Out', f"{best_zone[0]} {best_zone[1]['sellout_q1']:.0f}%", f"Primary Rs{best_zone[1]['primary_q1']:,.0f}L vs Offtake Rs{best_zone[1]['offtake_q1']:,.0f}L", GREEN),
    ('All Zones', 'Primary > Offtake', 'Every zone is over-stocked vs sell-out, none in OOS risk', 'E2A500'),
]
zone_scr = (
    f"All 5 zones show Primary > Offtake in Q1; {worst_zone[0]} weakest at {worst_zone[1]['sellout_q1']:.0f}%, {best_zone[0]} best at {best_zone[1]['sellout_q1']:.0f}%.",
    f"{worst_zone[0]} carries the largest billed-not-sold gap - a broad-based over-stock, not a single-zone issue.",
    f"RSM to phase {worst_zone[0]} primary orders over 4-6 weeks; redirect push to sell-out activation, not billing.",
)
slide3_content = three_split_slide(
    "Primary vs. Offtake Sell-Out — Zone View",
    "Q1 FY26-27 (Apr-Jun'26) | 5 common zones (East, North, South-1, South-2, West)",
    "Portfolio | All Categories | Zone-Level Deep Dive",
    zone_kpis, zone_items, zone_max, zone_scr,
    footnote="Pan India/FSN zone excluded - no matching zone dimension in Primary reporting for this channel.",
)

print('validation OK - all title/SCR length checks passed')

# ============ INSERT INTO DECK ============
SRC = 'v3/deck_v4_fixed.pptx'
DST = 'v3/deck_v5_sellout.pptx'

with zipfile.ZipFile(SRC) as z:
    names = z.namelist()
    data = {n: z.read(n) for n in names}

ct = data['[Content_Types].xml'].decode('utf-8')
rels = data['ppt/_rels/presentation.xml.rels'].decode('utf-8')
pres = data['ppt/presentation.xml'].decode('utf-8')

override25 = re.search(r'<Override PartName="/ppt/slides/slide25\.xml".*?/>', ct).group(0)
existing_rids = [int(m) for m in re.findall(r'Id="rId(\d+)"', rels)]
existing_sldids = [int(m) for m in re.findall(r'<p:sldId id="(\d+)"', pres)]
next_rid = max(existing_rids) + 1
next_sldid = max(existing_sldids) + 1

slide25_rels = data['ppt/slides/_rels/slide25.xml.rels'].decode('utf-8')

for i, content in enumerate([slide1_content, slide2_content, slide3_content], start=26):
    part = f'ppt/slides/slide{i}.xml'
    data[part] = slide_xml(content).encode('utf-8')
    data[f'ppt/slides/_rels/slide{i}.xml.rels'] = slide25_rels.encode('utf-8')
    ct = ct.replace('</Types>', override25.replace('slide25.xml', f'slide{i}.xml') + '</Types>')
    rels = rels.replace('</Relationships>',
        f'<Relationship Id="rId{next_rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide{i}.xml"/></Relationships>')
    pres = pres.replace('</p:sldIdLst>', f'<p:sldId id="{next_sldid}" r:id="rId{next_rid}"/></p:sldIdLst>')
    next_rid += 1
    next_sldid += 1

data['[Content_Types].xml'] = ct.encode('utf-8')
data['ppt/_rels/presentation.xml.rels'] = rels.encode('utf-8')
data['ppt/presentation.xml'] = pres.encode('utf-8')

with zipfile.ZipFile(DST, 'w', zipfile.ZIP_DEFLATED) as zout:
    for n in names:
        zout.writestr(n, data[n])
    for i in (26, 27, 28):
        zout.writestr(f'ppt/slides/slide{i}.xml', data[f'ppt/slides/slide{i}.xml'])
        zout.writestr(f'ppt/slides/_rels/slide{i}.xml.rels', data[f'ppt/slides/_rels/slide{i}.xml.rels'])

print('written', DST)
