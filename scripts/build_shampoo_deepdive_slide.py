#!/usr/bin/env python3
"""SHAMPOO DEEP DIVE slide (Nielsen URB, Bottles) in the PACK SIZE layout, but
keyed by BRAND x SALES x SHARE (g/ml pack data not available for shampoo).
Inserted right after PACK SIZE DEEP DIVE. Stdlib only; operates on w/."""
import xml.etree.ElementTree as ET, re, os
from xml.sax.saxutils import escape
NS={'a':'http://schemas.openxmlformats.org/drawingml/2006/main',
 'p':'http://schemas.openxmlformats.org/presentationml/2006/main',
 'r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
for k,u in NS.items(): ET.register_namespace(k,u)
def q(t):x,l=t.split(':');return f'{{{NS[x]}}}{l}'
W,H=7562850,10688638
TL=212691; TW=6926523
TEAL='2D9B7F'; DARK='1F2933'; WARM='FAF7F2'; WHITE='FFFFFF'; GREEN='1E8E3E'; RED='C0392B'; LTEAL='E3F2EC'; GREY='595959'
F='Calibri'
def run(t,sz,b=False,c=DARK):
    bb=' b="1"' if b else ''
    return f'<a:r><a:rPr lang="en-US" sz="{sz}"{bb}><a:solidFill><a:srgbClr val="{c}"/></a:solidFill><a:latin typeface="{F}"/></a:rPr><a:t>{escape(t)}</a:t></a:r>'
def label(sid,x,y,w,h,txt,sz=1150,c=TEAL):
    return (f'<p:sp><p:nvSpPr><p:cNvPr id="{sid}" name="lbl{sid}"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>'
            f'<p:spPr><a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{w}" cy="{h}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/></p:spPr>'
            f'<p:txBody><a:bodyPr anchor="ctr" lIns="0" tIns="0" bIns="0" rIns="0"/><a:p>{run(txt,sz,True,c)}</a:p></p:txBody></p:sp>')
def tc(text,sz,b,color,fill,align='ctr'):
    bb=' b="1"' if b else ''
    return (f'<a:tc><a:txBody><a:bodyPr/><a:p><a:pPr algn="{align}"/>'
            f'<a:r><a:rPr lang="en-US" sz="{sz}"{bb}><a:solidFill><a:srgbClr val="{color}"/></a:solidFill><a:latin typeface="{F}"/></a:rPr>'
            f'<a:t>{escape(text)}</a:t></a:r></a:p></a:txBody>'
            f'<a:tcPr marL="40000" marR="40000" marT="8000" marB="8000" anchor="ctr"><a:solidFill><a:srgbClr val="{fill}"/></a:solidFill></a:tcPr></a:tc>')
def table(sid,x,y,w,header,rows,colw,rowh=330000):
    cw=[round(w*c) for c in colw]; cw[-1]+=w-sum(cw)
    out=['<a:tr h="%d">'%rowh+''.join(tc(h,1000,True,WHITE,TEAL,'l' if i==0 else 'ctr') for i,h in enumerate(header))+'</a:tr>']
    for cells in rows:
        hl = cells[0]=='Mamaearth'
        fill=LTEAL if hl else WHITE
        tcs=[]
        for i,(val,col) in enumerate(cells_fmt(cells)):
            tcs.append(tc(val,1000,hl if i in(0,) else (col is not None),(col or DARK),fill,'l' if i==0 else 'ctr'))
        out.append('<a:tr h="%d">'%rowh+''.join(tcs)+'</a:tr>')
    grid=''.join(f'<a:gridCol w="{c}"/>' for c in cw)
    th=rowh*(len(rows)+1)
    return (f'<p:graphicFrame><p:nvGraphicFramePr><p:cNvPr id="{sid}" name="t{sid}"/><p:cNvGraphicFramePr/><p:nvPr/></p:nvGraphicFramePr>'
            f'<p:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{w}" cy="{th}"/></p:xfrm>'
            f'<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/table">'
            f'<a:tbl><a:tblPr firstRow="1" bandRow="1"/><a:tblGrid>{grid}</a:tblGrid>{"".join(out)}</a:tbl>'
            f'</a:graphicData></a:graphic></p:graphicFrame>'), th
def cells_fmt(cells):
    # cells: list of (text, colorOrNone)
    return cells

def arrow_pct(p):
    pos=p>=0; return ('▲ +' if pos else '▼ ')+f'{abs(p):.1f}%', (GREEN if pos else RED)
def arrow_bps(b):
    pos=b>=0; return ('▲ +' if pos else '▼ ')+f'{abs(int(b))}', (GREEN if pos else RED)

# data: brand, apr26Cr, may26Cr, contrib%, mom%, yoybps, salesYoY%, ms%may26
D=[
 ('Dove',37.47,36.72,13.3,-2.0,-120,-10.8,13.3),
 ('Head & Shoulders',34.24,32.39,11.7,-5.4,-89,-9.6,11.7),
 ('Clinic Plus',27.27,26.70,9.7,-2.1,-3,-3.1,9.7),
 ("L'Oreal Paris",26.80,25.59,9.3,-4.5,119,11.5,9.3),
 ('Sunsilk',22.31,20.66,7.5,-7.4,-91,-13.3,7.5),
 ('Tresemme',18.71,18.71,6.8,-0.0,66,7.7,6.8),
 ('Himalaya Baby Care',9.93,10.43,3.8,5.0,41,9.0,3.8),
 ('Mamaearth',6.68,6.94,2.5,4.0,91,52.2,2.5),
]
sid=10; shapes=[]
# title bar
shapes.append(f'<p:sp><p:nvSpPr><p:cNvPr id="{sid}" name="TitleBar"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
 f'<p:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{W}" cy="620000"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom>'
 f'<a:solidFill><a:srgbClr val="{TEAL}"/></a:solidFill></p:spPr><p:txBody><a:bodyPr anchor="ctr" lIns="{TL}" tIns="0" bIns="0" rIns="0"/>'
 f'<a:p>{run("SHAMPOO DEEP DIVE",1900,True,WHITE)}</a:p></p:txBody></p:sp>'); sid+=1
shapes.append(label(sid,TL,660000,TW,260000,"Top brands by sales & share — Nielsen MS Val, Urban (Bottles)  |  May 2026",1100,DARK)); sid+=1
# Table 1
shapes.append(label(sid,TL,980000,TW,250000,"TOP CONTRIBUTING BRANDS (BY MAY'26 SALES)")); sid+=1
hdr1=['Brand',"Apr'26 (Cr)","May'26 (Cr)",'Contribution %','MoM Growth','Status']
rows1=[]
for b,apr,may,con,mom,yoyb,syoy,ms in D:
    momtxt,momc=arrow_pct(mom)
    status = '▲ Gaining Share' if yoyb>=0 else 'Needs Promo Support'
    statc = GREEN if yoyb>=0 else DARK
    rows1.append([(b,None),(f'{apr:.1f}',None),(f'{may:.1f}',None),(f'{con:.1f}%',None),(momtxt,momc),(status,statc)])
t1,th1=table(sid,TL,1260000,TW,hdr1,rows1,[0.30,0.15,0.15,0.16,0.13,0.11]); shapes.append(t1); sid+=1
y2lbl=1260000+th1+150000
# Table 2
shapes.append(label(sid,TL,y2lbl,TW,250000,"BRAND SHARE & GROWTH (NIELSEN MS VAL %)")); sid+=1
hdr2=['Brand',"May'26 MS %",'YoY (bps)','Sales YoY %']
rows2=[]
for b,apr,may,con,mom,yoyb,syoy,ms in D:
    yb,ybc=arrow_bps(yoyb); sy,syc=arrow_pct(syoy)
    rows2.append([(b,None),(f'{ms:.1f}%',None),(yb,ybc),(sy,syc)])
t2,th2=table(sid,TL,y2lbl+280000,TW,hdr2,rows2,[0.40,0.20,0.20,0.20]); shapes.append(t2); sid+=1
iby=y2lbl+280000+th2+200000
# insight
ins=[run("Why it matters:  ",1100,True,TEAL),
 run("The shampoo category (Bottles) softened to ₹276 Cr (",1050,False,DARK),run("▼ -3.3% MoM",1050,True,RED),
 run(", ",1050),run("▼ -2.8% YoY",1050,True,RED),
 run("). Against that, ",1050,False,DARK),run("Mamaearth grew sales +52% YoY",1050,True,GREEN),
 run(" to ₹6.94 Cr and added ",1050,False,DARK),run("+91 bps share",1050,True,GREEN),
 run(" — the standout riser, with L’Oreal Paris (▲ +119 bps) and Tresemme (▲ +66 bps) also gaining; Dove (▼ -120) and Head & Shoulders (▼ -89) ceded share.",1050,False,DARK)]
act=[run("Action:  ",1100,True,TEAL),run("Keep pressing MT-chain distribution depth and shelf visibility to convert Mamaearth's momentum into a higher rung on the brand ladder.",1050,False,DARK)]
src=[run("Source: Nielsen MS Val, Urban, Bottles — Apr’26 vs May’26; YoY vs May’25.",900,False,GREY)]
shapes.append(f'<p:sp><p:nvSpPr><p:cNvPr id="{sid}" name="Insight"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>'
 f'<p:spPr><a:xfrm><a:off x="{TL}" y="{iby}"/><a:ext cx="{TW}" cy="1500000"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom>'
 f'<a:solidFill><a:srgbClr val="{LTEAL}"/></a:solidFill><a:ln w="9525"><a:solidFill><a:srgbClr val="{TEAL}"/></a:solidFill></a:ln></p:spPr>'
 f'<p:txBody><a:bodyPr wrap="square" anchor="t" lIns="90000" rIns="90000" tIns="60000" bIns="60000"/>'
 f'<a:p>{"".join(ins)}</a:p><a:p><a:pPr><a:spcBef><a:spcPts val="600"/></a:spcBef></a:pPr>{"".join(act)}</a:p>'
 f'<a:p><a:pPr><a:spcBef><a:spcPts val="600"/></a:spcBef></a:pPr>{"".join(src)}</a:p></p:txBody></p:sp>'); sid+=1
# footer
fx=W-1280160; fy=H-228600-45720
shapes.append(f'<p:sp><p:nvSpPr><p:cNvPr id="990" name="PageNum"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>'
 f'<p:spPr><a:xfrm><a:off x="{fx}" y="{fy}"/><a:ext cx="1005840" cy="228600"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/></p:spPr>'
 f'<p:txBody><a:bodyPr wrap="none" lIns="0" rIns="0" tIns="0" bIns="0"/><a:p><a:pPr algn="r"/>{run("10 / 24",900,False,DARK)}</a:p></p:txBody></p:sp>')

slide=('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'
 '<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
 'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
 'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
 f'<p:cSld><p:bg><p:bgPr><a:solidFill><a:srgbClr val="{WARM}"/></a:solidFill><a:effectLst/></p:bgPr></p:bg>'
 '<p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
 '<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>'
 +''.join(shapes)+'</p:spTree></p:cSld></p:sld>')
open('w/ppt/slides/slide24.xml','w',encoding='utf-8').write(slide)
open('w/ppt/slides/_rels/slide24.xml.rels','w',encoding='utf-8').write(
 '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'
 '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
 '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout2.xml"/>'
 '</Relationships>')
ctp='w/[Content_Types].xml'; ct=open(ctp,encoding='utf-8').read()
ct=ct.replace('</Types>','<Override PartName="/ppt/slides/slide24.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/></Types>')
open(ctp,'w',encoding='utf-8').write(ct)
prp='w/ppt/_rels/presentation.xml.rels'; pr=open(prp,encoding='utf-8').read()
nrid='rId%d'%(max(int(x) for x in re.findall(r'Id="rId(\d+)"',pr))+1)
pr=pr.replace('</Relationships>',f'<Relationship Id="{nrid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide24.xml"/></Relationships>')
open(prp,'w',encoding='utf-8').write(pr)
pp='w/ppt/presentation.xml'; pres=open(pp,encoding='utf-8').read()
nsid=max(int(x) for x in re.findall(r'<p:sldId id="(\d+)"',pres))+1
# insert after PACK SIZE DEEP DIVE (sldId 287 / rId27)
pres=pres.replace('<p:sldId id="287" r:id="rId27"/>', f'<p:sldId id="287" r:id="rId27"/><p:sldId id="{nsid}" r:id="{nrid}"/>',1)
open(pp,'w',encoding='utf-8').write(pres)
print(f'Inserted SHAMPOO DEEP DIVE as slide24.xml rId={nrid} sldId={nsid}')
# renumber footers
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
print(f'total={total} footersFixed={fixed}')
