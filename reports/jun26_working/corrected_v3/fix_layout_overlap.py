import zipfile, re

SRC = 'v3/deck_v3_user.pptx'
DST = 'v3/deck_v4_fixed.pptx'

PAD = 190500  # 20px @ 96dpi in EMU
GREEN = '1F7A3D'
GREY = '404040'

def para(text, b=False, color=None, sz=1000):
    fill = f'<a:solidFill><a:srgbClr val="{color}"/></a:solidFill>' if color else ''
    bstr = ' b="1"' if b else ''
    return (f'<a:p><a:r><a:rPr lang="en-US" sz="{sz}"{bstr} dirty="0">{fill}'
            f'<a:latin typeface="Calibri" pitchFamily="34" charset="0"/></a:rPr>'
            f'<a:t>{text}</a:t></a:r></a:p>')

def bullet(text, sz=1000):
    return (f'<a:p><a:r><a:rPr lang="en-US" sz="{sz}" dirty="0">'
            f'<a:solidFill><a:srgbClr val="{GREY}"/></a:solidFill>'
            f'<a:latin typeface="Calibri" pitchFamily="34" charset="0"/></a:rPr>'
            f'<a:t>• {text}</a:t></a:r></a:p>')

def callout_box(shape_id, name, x, y, cx, cy, title, bullets, fill='FFF6E0'):
    body = para(title, b=True, sz=1200) + ''.join(bullet(b) for b in bullets)
    return f'''<p:sp><p:nvSpPr><p:cNvPr id="{shape_id}" name="{name}"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
<p:spPr><a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>
<a:prstGeom prst="roundRect"><a:avLst><a:gd name="adj" fmla="val 3226"/></a:avLst></a:prstGeom>
<a:solidFill><a:srgbClr val="{fill}"/></a:solidFill><a:ln/></p:spPr>
<p:txBody><a:bodyPr anchor="t" wrap="square"><a:normAutofit fontScale="90000" lnSpcReduction="10000"/></a:bodyPr><a:lstStyle/>{body}</p:txBody></p:sp>'''

def divider(shape_id, name, x, y, cx):
    return (f'<p:sp><p:nvSpPr><p:cNvPr id="{shape_id}" name="{name}"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
            f'<p:spPr><a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="0"/></a:xfrm>'
            f'<a:prstGeom prst="line"><a:avLst/></a:prstGeom>'
            f'<a:ln w="9525"><a:solidFill><a:srgbClr val="D9D9D9"/></a:solidFill></a:ln></p:spPr>'
            f'<p:txBody><a:bodyPr/><a:lstStyle/><a:p/></p:txBody></p:sp>')

with zipfile.ZipFile(SRC) as z:
    names = z.namelist()
    data = {n: z.read(n) for n in names}

# ---------- SLIDE 3: Strategic Brand Portfolio callout ----------
d3 = data['ppt/slides/slide3.xml'].decode('utf-8')
idx = d3.find('Strategic')
s = d3.rfind('<p:sp>', 0, idx)
e = d3.find('</p:sp>', idx) + len('</p:sp>')
old_shape = d3[s:e]

table18_bottom = 2355490  # from geometry dump
new_y = table18_bottom + PAD
new_cy = 700000  # title + 3 single-line bullets @ ~1000sz with normAutofit safety margin

new_shape = callout_box(
    20, 'Shape 21 (Strategic Brand Portfolio)',
    208385, new_y, 7140201, new_cy,
    'Strategic Brand Portfolio',
    [
        'Mamaearth stays portfolio leader: 72.1% share, +38% YoY, steady scale.',
        'The Derma Co. is fastest-scaling: 26.0% of NSV vs single digits a year ago.',
        'Aqualogica: +20% YoY, Jun cooled -16% MoM (Sun Care season); 1.5% of mix.',
    ]
)
assert old_shape in d3, 'slide3 old shape not found for replace'
d3 = d3.replace(old_shape, new_shape)
data['ppt/slides/slide3.xml'] = d3.encode('utf-8')
print('slide3 patched: new callout y=%d bottom=%d (next header at 3344609)' % (new_y, new_y+new_cy))

# ---------- SLIDE 4: split Zone Insights mega-box into two + repositioned divider ----------
d4 = data['ppt/slides/slide4.xml'].decode('utf-8')
idx = d4.find('Zone Insights')
s = d4.rfind('<p:sp>', 0, idx)
e = d4.find('</p:sp>', idx) + len('</p:sp>')
old_shape4 = d4[s:e]
assert old_shape4 in d4

table239_bottom = 5364943
zi_y = table239_bottom + PAD
zi_cy = 1450000
zi_bottom = zi_y + zi_cy

div_y = zi_bottom + PAD // 2

br_y = div_y + PAD // 2 + PAD
br_cy = 1450000
br_bottom = br_y + br_cy

zi_box = callout_box(
    65, 'Text 65 (Zone Insights)',
    329184, zi_y, 6903719, zi_cy,
    "Zone Insights | Jun’26 (post chain-NSV correction)",
    [
        "West largest zone: NSV ₹985L, 25.8% of MT offtake.",
        "Every zone grew ≥ 64% YoY in Jun’26 — corrected NSV lifts growth network-wide (+68%).",
        "South-1 led YoY growth at +82%; East and North close at +72% each.",
        "Dmart is #1 chain in 3 of 5 zones (North, South-2, West); #2 in South-1 — national engine.",
        "Apollo reclaims #1 in South-1 (₹289L), +163% YoY — Derma Co.-led pharmacy momentum.",
    ]
)
div_shape = divider(164, 'Shape 64 (mid-divider)', 320039, div_y, 6903720)
br_box = callout_box(
    165, 'Text 165 (Brand and Category Repeats)',
    329184, br_y, 6903719, br_cy,
    'Brand &amp; Category Repeats Across Zones',
    [
        "The Derma Co. held ₹990L in Jun (record ₹1,097L in May), 25.9% of portfolio, +378% YoY.",
        "Face Cleanser &amp; Sun Care are top-2 growth drivers for Derma Co. in 5 of 6 zones.",
        "FSN grew +32% YoY — improving, but still slower than the +68% network pace.",
        "Mamaearth Face Cleanser &amp; Shampoo rank #1/#2 sub-categories by value in every zone.",
        "Sun Care cooled -30% MoM (seasonal) — protect sunscreen distribution into monsoon.",
    ]
)

new_block4 = zi_box + div_shape + br_box
d4 = d4.replace(old_shape4, new_block4)

# remove the old fixed-position divider lines that used to sit inside the old mega-box range
# (Shape 64 instances at y=8411471 and y=8183192 in the original — now redundant/mispositioned)
for stale_y in ('8411471', '8183192'):
    m = re.search(rf'<p:sp>(?:(?!</p:sp>).)*?name="Shape 64"(?:(?!</p:sp>).)*?y="{stale_y}"(?:(?!</p:sp>).)*?</p:sp>', d4, re.S)
    if m:
        d4 = d4.replace(m.group(0), '')
        print('removed stale divider at y=%s' % stale_y)
    else:
        print('WARNING: stale divider at y=%s not matched by regex' % stale_y)

data['ppt/slides/slide4.xml'] = d4.encode('utf-8')
print('slide4 patched: zi_box %d-%d, divider %d, br_box %d-%d (slide height 10688638)' % (zi_y, zi_bottom, div_y, br_y, br_bottom))

with zipfile.ZipFile(DST, 'w', zipfile.ZIP_DEFLATED) as zout:
    for n in names:
        zout.writestr(n, data[n])

print('written', DST)
