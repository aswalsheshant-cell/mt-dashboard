#!/usr/bin/env python3
"""Insert Honasa 'PACK SIZE DEEP DIVE' (hon slide6) into w/ as new slide 7,
uniformly scaled to fit the A4 portrait size, with its chart+embedding copied,
title bar teal-ed, font unified to Calibri, and all footers renumbered /21."""
import xml.etree.ElementTree as ET, shutil, re, os
NSMAP={'a':'http://schemas.openxmlformats.org/drawingml/2006/main',
 'p':'http://schemas.openxmlformats.org/presentationml/2006/main',
 'r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
 'c':'http://schemas.openxmlformats.org/drawingml/2006/chart',
 'a16':'http://schemas.microsoft.com/office/drawing/2014/main',
 'a14':'http://schemas.microsoft.com/office/drawing/2010/main',
 'p14':'http://schemas.microsoft.com/office/powerpoint/2010/main'}
for p,u in NSMAP.items(): ET.register_namespace(p,u)
def q(t):x,l=t.split(':');return f'{{{NSMAP[x]}}}{l}'

W,H=7562850,10688638
SW,SH=6858000,12192000
S=H/SH                       # uniform fit-to-height
XOFF=round((W-SW*S)/2)
FONT='Calibri'; TEAL='2D9B7F'

NEW_SLIDE='w/ppt/slides/slide21.xml'
NEW_CHART='w/ppt/charts/chart53.xml'
NEW_XLSX='w/ppt/embeddings/Microsoft_Excel_Worksheet_pack.xlsx'

# ---- copy chart + embedding ----
shutil.copy('hon/ppt/charts/chart3.xml', NEW_CHART)
shutil.copy('hon/ppt/embeddings/Microsoft_Excel_Worksheet2.xlsx', NEW_XLSX)
os.makedirs('w/ppt/charts/_rels',exist_ok=True)
open('w/ppt/charts/_rels/chart53.xml.rels','w',encoding='utf-8').write(
 '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'
 '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
 '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/package" '
 'Target="../embeddings/Microsoft_Excel_Worksheet_pack.xlsx"/></Relationships>')

# ---- slide rels: layout (Blank=slideLayout2) + chart ----
open('w/ppt/slides/_rels/slide21.xml.rels','w',encoding='utf-8').write(
 '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'
 '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
 '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout2.xml"/>'
 '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/chart" Target="../charts/chart53.xml"/>'
 '</Relationships>')

# ---- load + transform the slide ----
tree=ET.parse('hon/ppt/slides/slide6.xml'); root=tree.getroot()
spTree=root.find('.//'+q('p:spTree'))

def scale_xfrm(xf, top=True):
    o=xf.find(q('a:off')); e=xf.find(q('a:ext'))
    if o is not None:
        o.set('x',str(round(int(o.get('x'))*S)+(XOFF if top else 0)))
        o.set('y',str(round(int(o.get('y'))*S)))
    if e is not None:
        e.set('cx',str(round(int(e.get('cx'))*S)))
        e.set('cy',str(round(int(e.get('cy'))*S)))

# scale every sz (font) attribute in the whole slide
for el in root.iter():
    if el.get('sz') is not None and el.tag in (q('a:rPr'),q('a:defRPr'),q('a:endParaRPr')):
        try: el.set('sz',str(max(100,round(int(el.get('sz'))*S))))
        except ValueError: pass

# top-level shapes
for el in list(spTree):
    tag=el.tag.split('}')[1]
    if tag in ('nvGrpSpPr','grpSpPr'): continue
    if tag=='graphicFrame':
        xf=el.find(q('p:xfrm'))
        if xf is not None: scale_xfrm(xf,top=True)
        tbl=el.find('.//'+q('a:tbl'))
        if tbl is not None:
            for gc in tbl.iter(q('a:gridCol')): gc.set('w',str(round(int(gc.get('w'))*S)))
            for tr in tbl.iter(q('a:tr')): tr.set('h',str(round(int(tr.get('h'))*S)))
    else:
        xf=el.find('.//'+q('a:xfrm'))
        if xf is not None: scale_xfrm(xf,top=True)

# font unify on the new slide (concrete typeface -> Calibri)
for tagn in ('a:latin','a:ea','a:cs'):
    for el in root.iter(q(tagn)):
        tf=el.get('typeface')
        if tf is not None and not tf.startswith('+') and tf!=FONT:
            el.set('typeface',FONT)

# recolor full-width title/header bars to teal (shape fills only, dark colours)
def is_light(h):
    try: r,g,b=int(h[0:2],16),int(h[2:4],16),int(h[4:6],16)
    except ValueError: return True
    return min(r,g,b)>=0xCC
for sp in spTree.findall(q('p:sp')):
    spPr=sp.find(q('p:spPr'))
    if spPr is None: continue
    sf=spPr.find(q('a:solidFill'))
    if sf is None: continue
    xf=sp.find('.//'+q('a:xfrm'))
    if xf is None: continue
    e=xf.find(q('a:ext'))
    if e is None: continue
    cx=int(e.get('cx')); cy=int(e.get('cy'))
    if cx<0.55*W or not(25000<=cy<=600000): continue
    s=sf.find(q('a:srgbClr'))
    if s is not None and is_light(s.get('val')): continue
    for ch in list(sf): sf.remove(ch)
    ET.SubElement(sf,q('a:srgbClr'),{'val':TEAL})

# remove original Honasa footer shapes (report caption + lone page number)
for sp in list(spTree.findall(q('p:sp'))):
    txt=''.join(t.text or '' for t in sp.iter(q('a:t'))).strip()
    if txt=='5' or txt.startswith('Market Share Performance Report'):
        spTree.remove(sp)

tree.write(NEW_SLIDE,xml_declaration=True,encoding='UTF-8')

# ---- register content types ----
ctp='w/[Content_Types].xml'; ct=open(ctp,encoding='utf-8').read()
add=('<Override PartName="/ppt/slides/slide21.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
     '<Override PartName="/ppt/charts/chart53.xml" ContentType="application/vnd.openxmlformats-officedocument.drawingml.chart+xml"/>')
ct=ct.replace('</Types>',add+'</Types>'); open(ctp,'w',encoding='utf-8').write(ct)

# ---- presentation rels: new rId for the slide ----
prp='w/ppt/_rels/presentation.xml.rels'; pr=open(prp,encoding='utf-8').read()
rids=[int(x) for x in re.findall(r'Id="rId(\d+)"',pr)]; newrid=f'rId{max(rids)+1}'
pr=pr.replace('</Relationships>',
  f'<Relationship Id="{newrid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide21.xml"/></Relationships>')
open(prp,'w',encoding='utf-8').write(pr)

# ---- sldIdLst: insert after slide6 (rId7), before slide7 (rId8) ----
pp='w/ppt/presentation.xml'; pres=open(pp,encoding='utf-8').read()
sids=[int(x) for x in re.findall(r'<p:sldId id="(\d+)"',pres)]; newsid=max(sids)+1
ins=f'<p:sldId id="{newsid}" r:id="{newrid}"/>'
pres=pres.replace('<p:sldId id="270" r:id="rId8"/>', ins+'<p:sldId id="270" r:id="rId8"/>',1)
open(pp,'w',encoding='utf-8').write(pres)

print(f'Inserted slide21 (scale={S:.4f}, xoff={XOFF}) as new position 7; rId={newrid}, sldId={newsid}')

# ---- renumber every footer PageNum to "pos / 21" by sldIdLst order ----
order=re.findall(r'<p:sldId id="\d+" r:id="(rId\d+)"/>',pres)
rid2tgt=dict(re.findall(r'Id="(rId\d+)"[^>]*Target="(slides/slide\d+\.xml)"',open(prp,encoding='utf-8').read()))
total=len(order)
fixed=0
for pos,rid in enumerate(order,1):
    tgt=rid2tgt.get(rid)
    if not tgt: continue
    f='w/ppt/'+tgt
    t2=ET.parse(f); r2=t2.getroot(); changed=False
    for sp in r2.iter(q('p:sp')):
        nv=sp.find('.//'+q('p:cNvPr'))
        if nv is not None and nv.get('name')=='PageNum':
            for tt in sp.iter(q('a:t')):
                tt.text=f'{pos} / {total}'; changed=True
    if changed:
        t2.write(f,xml_declaration=True,encoding='UTF-8'); fixed+=1
print(f'Renumbered footers on {fixed} slides; total slides = {total}')
