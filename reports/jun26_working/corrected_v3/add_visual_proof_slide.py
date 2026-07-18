import zipfile, shutil, re

SRC = 'deck_jun26_corrected.pptx'
DST = 'deck_jun26_final_v3.pptx'
shutil.copy(SRC, DST)

W, H = 7562850, 10688638  # cx, cy from presentation.xml (portrait)

def box(x, y, cx, cy, title, sub, fill='F2F2F2', border='BFBFBF'):
    return f'''<p:sp><p:nvSpPr><p:cNvPr id="0" name="ExecBox"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
<p:spPr><a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>
<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
<a:solidFill><a:srgbClr val="{fill}"/></a:solidFill>
<a:ln w="12700"><a:solidFill><a:srgbClr val="{border}"/></a:solidFill></a:ln></p:spPr>
<p:txBody><a:bodyPr wrap="square" anchor="ctr"><a:normAutofit/></a:bodyPr><a:lstStyle/>
<a:p><a:pPr algn="ctr"/><a:r><a:rPr lang="en-US" sz="1400" b="1"><a:solidFill><a:srgbClr val="404040"/></a:solidFill></a:rPr><a:t>{title}</a:t></a:r></a:p>
<a:p><a:pPr algn="ctr"/><a:r><a:rPr lang="en-US" sz="1000"><a:solidFill><a:srgbClr val="808080"/></a:solidFill></a:rPr><a:t>{sub}</a:t></a:r></a:p>
</p:txBody></p:sp>'''

title_box = f'''<p:sp><p:nvSpPr><p:cNvPr id="0" name="Title"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
<p:spPr><a:xfrm><a:off x="228600" y="228600"/><a:ext cx="{W-457200}" cy="600000"/></a:xfrm>
<a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/></p:spPr>
<p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:r><a:rPr lang="en-US" sz="2000" b="1"><a:solidFill><a:srgbClr val="1F4E79"/></a:solidFill></a:rPr>
<a:t>Visual Proof of Execution — Q1 FY26-27 (placeholder)</a:t></a:r></a:p>
<a:p><a:r><a:rPr lang="en-US" sz="1200" i="1"><a:solidFill><a:srgbClr val="595959"/></a:solidFill></a:rPr>
<a:t>Drop best-in-class visibility photos below; label each by State + Retail Chain banner. No live image source connected this cycle.</a:t></a:r></a:p>
</p:txBody></p:sp>'''

labels = [
    ("State: ___________", "Chain: ___________"),
    ("State: ___________", "Chain: ___________"),
    ("State: ___________", "Chain: ___________"),
    ("State: ___________", "Chain: ___________"),
    ("State: ___________", "Chain: ___________"),
    ("State: ___________", "Chain: ___________"),
]

cols, rows = 2, 3
margin = 300000
gap = 150000
box_w = (W - 2*margin - (cols-1)*gap)//cols
box_h = 2700000
start_y = 1100000

shapes = [title_box]
i = 0
for r in range(rows):
    for c in range(cols):
        x = margin + c*(box_w+gap)
        y = start_y + r*(box_h+gap)
        title, sub = labels[i]
        shapes.append(box(x, y, box_w, box_h, title, sub))
        i += 1

slide_xml = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
<p:cSld><p:spTree>
<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>
{''.join(shapes)}
</p:spTree></p:cSld><p:clrMapOvr><a:overrideClrMapping bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/></p:clrMapOvr>
</p:sld>'''

with zipfile.ZipFile(SRC) as zin:
    names = zin.namelist()
    data = {n: zin.read(n) for n in names}

# new slide number
new_slide_path = 'ppt/slides/slide25.xml'
data[new_slide_path] = slide_xml.encode('utf-8')

# _rels for new slide (no rels needed, minimal - but pptx requires a rels file referencing layout)
# reuse slide24's rels slideLayout target
slide24_rels = data['ppt/slides/_rels/slide24.xml.rels'].decode('utf-8')
data['ppt/slides/_rels/slide25.xml.rels'] = slide24_rels.encode('utf-8')

# [Content_Types].xml — add override for slide25
ct = data['[Content_Types].xml'].decode('utf-8')
assert '/ppt/slides/slide24.xml' in ct
override24 = re.search(r'<Override PartName="/ppt/slides/slide24\.xml".*?/>', ct).group(0)
override25 = override24.replace('slide24.xml', 'slide25.xml')
ct = ct.replace(override24, override24 + override25)
data['[Content_Types].xml'] = ct.encode('utf-8')

# presentation.xml.rels — add new relationship id
rels = data['ppt/_rels/presentation.xml.rels'].decode('utf-8')
existing_ids = [int(m) for m in re.findall(r'Id="rId(\d+)"', rels)]
new_id = max(existing_ids) + 1
rels = rels.replace('</Relationships>',
    f'<Relationship Id="rId{new_id}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide25.xml"/></Relationships>')
data['ppt/_rels/presentation.xml.rels'] = rels.encode('utf-8')

# presentation.xml — append to sldIdLst
pres = data['ppt/presentation.xml'].decode('utf-8')
existing_sld_ids = [int(m) for m in re.findall(r'<p:sldId id="(\d+)"', pres)]
new_sld_id = max(existing_sld_ids) + 1
pres = pres.replace('</p:sldIdLst>', f'<p:sldId id="{new_sld_id}" r:id="rId{new_id}"/></p:sldIdLst>')
data['ppt/presentation.xml'] = pres.encode('utf-8')

with zipfile.ZipFile(DST, 'w', zipfile.ZIP_DEFLATED) as zout:
    for n in names:
        if n in ('[Content_Types].xml', 'ppt/_rels/presentation.xml.rels', 'ppt/presentation.xml'):
            zout.writestr(n, data[n])
        else:
            zout.writestr(n, data[n])
    zout.writestr(new_slide_path, data[new_slide_path])
    zout.writestr('ppt/slides/_rels/slide25.xml.rels', data['ppt/slides/_rels/slide25.xml.rels'])

print('done', new_id, new_sld_id)
