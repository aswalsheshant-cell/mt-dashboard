#!/usr/bin/env python3
"""Build a standalone NIELSEN SHAMPOO brand-share slide (URB MS Val, Bottles)
and insert it right after the existing Nielsen pair (new display position 7).
Stdlib only; operates on the w/ tree."""
import xml.etree.ElementTree as ET, re, os
from xml.sax.saxutils import escape
NS={'a':'http://schemas.openxmlformats.org/drawingml/2006/main',
 'p':'http://schemas.openxmlformats.org/presentationml/2006/main',
 'r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
for k,u in NS.items(): ET.register_namespace(k,u)
def q(t):x,l=t.split(':');return f'{{{NS[x]}}}{l}'
W,H=7562850,10688638
TL=212691; TW=6926523
TEAL='2D9B7F'; DARK='1F2933'; WARM='FAF7F2'; WHITE='FFFFFF'
GREEN='1E8E3E'; RED='C0392B'; LTEAL='E3F2EC'
FONT='Calibri'

def run(txt,sz,b=False,color=DARK):
    bold=' b="1"' if b else ''
    return (f'<a:r><a:rPr lang="en-US" sz="{sz}"{bold}><a:solidFill>'
            f'<a:srgbClr val="{color}"/></a:solidFill><a:latin typeface="{FONT}"/>'
            f'</a:rPr><a:t>{escape(txt)}</a:t></a:r>')

def textbox(sid,x,y,w,h,runs,align='l',anchor='t',fill=None,wrap='square'):
    f=(f'<a:solidFill><a:srgbClr val="{fill}"/></a:solidFill>' if fill else '<a:noFill/>')
    return (f'<p:sp><p:nvSpPr><p:cNvPr id="{sid}" name="tb{sid}"/><p:cNvSpPr txBox="1"/>'
            f'<p:nvPr/></p:nvSpPr><p:spPr><a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{w}" cy="{h}"/></a:xfrm>'
            f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>{f}</p:spPr>'
            f'<p:txBody><a:bodyPr wrap="{wrap}" anchor="{anchor}" lIns="55000" rIns="55000" tIns="30000" bIns="30000"/>'
            f'<a:p><a:pPr algn="{align}"/>{"".join(runs)}</a:p></p:txBody></p:sp>')

def card(sid,x,y,w,h,label,value,sub_runs):
    return (f'<p:sp><p:nvSpPr><p:cNvPr id="{sid}" name="card{sid}"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
            f'<p:spPr><a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{w}" cy="{h}"/></a:xfrm>'
            f'<a:prstGeom prst="roundRect"><a:avLst><a:gd name="adj" fmla="val 6000"/></a:avLst></a:prstGeom>'
            f'<a:solidFill><a:srgbClr val="{WHITE}"/></a:solidFill>'
            f'<a:ln w="12700"><a:solidFill><a:srgbClr val="{TEAL}"/></a:solidFill></a:ln></p:spPr>'
            f'<p:txBody><a:bodyPr wrap="square" anchor="ctr" lIns="60000" rIns="60000" tIns="20000" bIns="20000"/>'
            f'<a:p><a:pPr algn="ctr"/>{run(label,1000,False,DARK)}</a:p>'
            f'<a:p><a:pPr algn="ctr"/>{run(value,2000,True,TEAL)}</a:p>'
            f'<a:p><a:pPr algn="ctr"/>{"".join(sub_runs)}</a:p></p:txBody></p:sp>')

# ---- table ----
def tcell(text,sz,b,color,fill,align='ctr'):
    bb=' b="1"' if b else ''
    return (f'<a:tc><a:txBody><a:bodyPr/><a:p><a:pPr algn="{align}"/>'
            f'<a:r><a:rPr lang="en-US" sz="{sz}"{bb}>'
            f'<a:solidFill><a:srgbClr val="{color}"/></a:solidFill><a:latin typeface="{FONT}"/></a:rPr>'
            f'<a:t>{escape(text)}</a:t></a:r></a:p></a:txBody>'
            f'<a:tcPr marL="46000" marR="46000" marT="12000" marB="12000" anchor="ctr">'
            f'<a:solidFill><a:srgbClr val="{fill}"/></a:solidFill></a:tcPr></a:tc>')

def brand_table(sid,x,y,w):
    cols=[0.34,0.15,0.15,0.15,0.21]
    cw=[round(w*c) for c in cols]; cw[-1]+=w-sum(cw)
    header=['Brand',"May'25","Apr'26","May'26",'YoY bps']
    # brand, may25, apr26, may26, yoy_bps
    data=[
     ('Himalaya','21.8','22.5','22.3',50),
     ('Garnier','14.1','13.7','13.3',-75),
     ("Pond's",'13.2','13.0','13.1',-13),
     ('Clean & Clear','10.4','9.2','9.3',-112),
     ('Mamaearth','5.3','6.5','6.7',139),
     ('Joy','3.8','3.9','4.3',47),
     ('Glow & Lovely','3.0','2.5','2.4',-66),
     ('Patanjali','2.7','2.4','2.2',-43),
    ]
    rowh=470000
    rows=['<a:tr h="%d">'%rowh + ''.join(tcell(h,1050,True,WHITE,TEAL,'l' if i==0 else 'ctr') for i,h in enumerate(header)) + '</a:tr>']
    for b,a,p,m,yoy in data:
        hl = b=='Mamaearth'
        fill = LTEAL if hl else WHITE
        nm = '▲ +%d'%yoy if yoy>=0 else '▼ %d'%yoy
        ycol = GREEN if yoy>=0 else RED
        cells=[tcell(b,1050,hl,DARK,fill,'l'),
               tcell(a,1050,False,DARK,fill),tcell(p,1050,False,DARK,fill),
               tcell(m,1050,hl,DARK,fill),
               tcell(nm,1050,True,ycol,fill)]
        rows.append('<a:tr h="%d">'%rowh+''.join(cells)+'</a:tr>')
    grid=''.join(f'<a:gridCol w="{c}"/>' for c in cw)
    tbl=(f'<a:tbl><a:tblPr firstRow="1" bandRow="1"/><a:tblGrid>{grid}</a:tblGrid>{"".join(rows)}</a:tbl>')
    th=rowh*(len(data)+1)
    return (f'<p:graphicFrame><p:nvGraphicFramePr><p:cNvPr id="{sid}" name="ShampooBrandTable"/>'
            f'<p:cNvGraphicFramePr/><p:nvPr/></p:nvGraphicFramePr>'
            f'<p:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{w}" cy="{th}"/></p:xfrm>'
            f'<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/table">'
            f'{tbl}</a:graphicData></a:graphic></p:graphicFrame>'), th

def arrow(v,unit='bps'):
    return ('▲ +'+v) , GREEN

shapes=[]; sid=10
# title bar
shapes.append(f'<p:sp><p:nvSpPr><p:cNvPr id="{sid}" name="TitleBar"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
  f'<p:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{W}" cy="620000"/></a:xfrm>'
  f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:solidFill><a:srgbClr val="{TEAL}"/></a:solidFill>'
  f'</p:spPr><p:txBody><a:bodyPr anchor="ctr" lIns="{TL}" rIns="0" tIns="0" bIns="0"/>'
  f'<a:p>{run("NIELSEN MARKET SHARE READOUT: FACEWASH",1900,True,WHITE)}</a:p></p:txBody></p:sp>'); sid+=1
shapes.append(textbox(sid,TL,660000,TW,300000,[run("Category-level external validation (Nielsen MS Val, Urban — Facewash)  |  standalone facewash read, not linked to other slides",1100,False,DARK)])); sid+=1
# KPI cards
cy0=1040000; ch=640000; gap=100000; cw=round((TW-2*gap)/3)
def updown(pct,bps=False):
    pos=not pct.startswith('-')
    sym='▲ +' if pos else '▼ '
    return run(sym+pct.lstrip('+'),1050,True,GREEN if pos else RED)
shapes.append(card(sid,TL,cy0,cw,ch,"Mamaearth MS Val","6.65%",
   [run("MoM ",950,False,DARK),updown('18 bps'),run("  YoY ",950,False,DARK),updown('139 bps')])); sid+=1
shapes.append(card(sid,TL+cw+gap,cy0,cw,ch,"Mamaearth Sales","₹ 17.54 Cr",
   [run("MoM ",950,False,DARK),updown('3.7%'),run("  YoY ",950,False,DARK),updown('34.1%')])); sid+=1
shapes.append(card(sid,TL+2*(cw+gap),cy0,cw,ch,"Category (Facewash)","₹ 263.6 Cr",
   [run("MoM ",950,False,DARK),updown('0.9%'),run("  YoY ",950,False,DARK),updown('6.1%')])); sid+=1
# table section label
ty_lbl=1800000
shapes.append(textbox(sid,TL,ty_lbl,TW,300000,[run("BRAND SHARE — NIELSEN MS VAL % (URBAN, FACEWASH)",1150,True,TEAL)])); sid+=1
# table
tbl_xml,th=brand_table(sid,TL,ty_lbl+330000,TW); shapes.append(tbl_xml); sid+=1
tbl_bottom=ty_lbl+330000+th
# insight box
ib_y=tbl_bottom+220000
ins_runs=[run("Why it matters:  ",1100,True,TEAL),
 run("Mamaearth facewash MS Val reached 6.65% in May’26 (",1050,False,DARK),
 run("▲ +139 bps YoY",1050,True,GREEN),
 run(", ",1050,False,DARK),run("▲ +18 bps MoM",1050,True,GREEN),
 run(") with sales of ₹17.54 Cr (",1050,False,DARK),run("▲ +34% YoY",1050,True,GREEN),
 run(") — the strongest YoY gainer in facewash. Market leader ",1050,False,DARK),
 run("Himalaya (▲ +50 bps)",1050,True,GREEN),run(" holds top spot, while ",1050,False,DARK),
 run("Clean & Clear (▼ -112 bps)",1050,True,RED),
 run(" and Garnier (▼ -75 bps) are ceding share.",1050,False,DARK)]
action=[run("Action:  ",1100,True,TEAL),
 run("Sustain MT-chain visibility and distribution depth to convert facewash momentum into durable category share gains.",1050,False,DARK)]
src=[run("Source: Nielsen MS Val, Urban, Facewash — May’25 / Apr’26 / May’26.",900,False,'595959')]
ib=(f'<p:sp><p:nvSpPr><p:cNvPr id="{sid}" name="Insight"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>'
    f'<p:spPr><a:xfrm><a:off x="{TL}" y="{ib_y}"/><a:ext cx="{TW}" cy="1500000"/></a:xfrm>'
    f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:solidFill><a:srgbClr val="{LTEAL}"/></a:solidFill>'
    f'<a:ln w="9525"><a:solidFill><a:srgbClr val="{TEAL}"/></a:solidFill></a:ln></p:spPr>'
    f'<p:txBody><a:bodyPr wrap="square" anchor="t" lIns="90000" rIns="90000" tIns="60000" bIns="60000"/>'
    f'<a:p>{"".join(ins_runs)}</a:p><a:p><a:pPr><a:spcBef><a:spcPts val="600"/></a:spcBef></a:pPr>{"".join(action)}</a:p>'
    f'<a:p><a:pPr><a:spcBef><a:spcPts val="600"/></a:spcBef></a:pPr>{"".join(src)}</a:p></p:txBody></p:sp>'); sid+=1
# footer (position filled later by renumber)
fx=W-1280160; fy=H-228600-45720
shapes.append(f'<p:sp><p:nvSpPr><p:cNvPr id="990" name="PageNum"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>'
  f'<p:spPr><a:xfrm><a:off x="{fx}" y="{fy}"/><a:ext cx="1005840" cy="228600"/></a:xfrm>'
  f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/></p:spPr><p:txBody>'
  f'<a:bodyPr wrap="none" lIns="0" rIns="0" tIns="0" bIns="0"/><a:p><a:pPr algn="r"/>'
  f'{run("7 / 23",900,False,DARK)}</a:p></p:txBody></p:sp>')

slide=('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'
 '<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
 'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
 'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
 f'<p:cSld><p:bg><p:bgPr><a:solidFill><a:srgbClr val="{WARM}"/></a:solidFill><a:effectLst/></p:bgPr></p:bg>'
 '<p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
 '<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>'
 +''.join(shapes)+'</p:spTree></p:cSld></p:sld>')

open('w/ppt/slides/slide23.xml','w',encoding='utf-8').write(slide)
open('w/ppt/slides/_rels/slide23.xml.rels','w',encoding='utf-8').write(
 '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'
 '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
 '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout2.xml"/>'
 '</Relationships>')

# content types
ctp='w/[Content_Types].xml'; ct=open(ctp,encoding='utf-8').read()
ct=ct.replace('</Types>','<Override PartName="/ppt/slides/slide23.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/></Types>')
open(ctp,'w',encoding='utf-8').write(ct)
# presentation rels
prp='w/ppt/_rels/presentation.xml.rels'; pr=open(prp,encoding='utf-8').read()
nrid='rId%d'%(max(int(x) for x in re.findall(r'Id="rId(\d+)"',pr))+1)
pr=pr.replace('</Relationships>',f'<Relationship Id="{nrid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide23.xml"/></Relationships>')
open(prp,'w',encoding='utf-8').write(pr)
# sldIdLst: insert after slide6 (rId7), before PACK SIZE (rId27)
pp='w/ppt/presentation.xml'; pres=open(pp,encoding='utf-8').read()
nsid=max(int(x) for x in re.findall(r'<p:sldId id="(\d+)"',pres))+1
pres=pres.replace('<p:sldId id="288" r:id="rId28"/>', f'<p:sldId id="{nsid}" r:id="{nrid}"/><p:sldId id="288" r:id="rId28"/>',1)
open(pp,'w',encoding='utf-8').write(pres)
print(f'Inserted Facewash Nielsen slide as slide23.xml (rId={nrid}, sldId={nsid})')

# renumber footers /total by order
order=re.findall(r'<p:sldId id="\d+" r:id="(rId\d+)"/>',pres)
rid2t=dict(re.findall(r'Id="(rId\d+)"[^>]*Target="(slides/slide\d+\.xml)"',open(prp,encoding='utf-8').read()))
total=len(order); fixed=0
for pos,rid in enumerate(order,1):
    t=rid2t.get(rid)
    if not t: continue
    f='w/ppt/'+t; tr=ET.parse(f); ro=tr.getroot(); ch=False
    for sp in ro.iter(q('p:sp')):
        nv=sp.find('.//'+q('p:cNvPr'))
        if nv is not None and nv.get('name')=='PageNum':
            for tt in sp.iter(q('a:t')): tt.text=f'{pos} / {total}'; ch=True
    if ch: tr.write(f,xml_declaration=True,encoding='UTF-8'); fixed+=1
print(f'total slides={total}, footers renumbered on {fixed}')
