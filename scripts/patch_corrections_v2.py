#!/usr/bin/env python3
"""Patch v2/ tree in place: fixes #1 (header bar teal), #3 (table/heading
overlap), #4 (chart label headroom), #5 (slide-4 panel spacing), #6 (slide-15
storefront removal + replacement). Stdlib only."""
import xml.etree.ElementTree as ET
import os, re, glob, shutil, hashlib, math

ROOT=os.path.dirname(os.path.abspath(__file__))
V2=os.path.join(ROOT,'v2')
NSMAP={'a':'http://schemas.openxmlformats.org/drawingml/2006/main',
 'p':'http://schemas.openxmlformats.org/presentationml/2006/main',
 'r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
 'c':'http://schemas.openxmlformats.org/drawingml/2006/chart',
 'a14':'http://schemas.microsoft.com/office/drawing/2010/main',
 'a16':'http://schemas.microsoft.com/office/drawing/2014/main',
 'p14':'http://schemas.microsoft.com/office/powerpoint/2010/main'}
for p,u in NSMAP.items(): ET.register_namespace(p,u)
def q(t): p,l=t.split(':'); return f'{{{NSMAP[p]}}}{l}'

W,H=7562850,10688638
ML=274320; MT=228600; MB=228600
TEAL='2D9B7F'
THR_W=4159567   # 0.55*W  -> "wide" header bar
log=[]

def get_box_sp(sp):
    x=sp.find('.//'+q('a:xfrm'))
    if x is None: return None
    o=x.find(q('a:off')); e=x.find(q('a:ext'))
    if o is None or e is None: return None
    return [int(o.get('x')),int(o.get('y')),int(e.get('cx')),int(e.get('cy')),x,o,e]
def get_box_gf(gf):
    x=gf.find(q('p:xfrm'))
    if x is None: return None
    o=x.find(q('a:off')); e=x.find(q('a:ext'))
    if o is None or e is None: return None
    return [int(o.get('x')),int(o.get('y')),int(e.get('cx')),int(e.get('cy')),x,o,e]

def is_light(hexv):
    r=int(hexv[0:2],16); g=int(hexv[2:4],16); b=int(hexv[4:6],16)
    return min(r,g,b)>=0xCC

# ---------------- Fix #1: header bar teal ----------------
def fix1(root,slideno):
    n=0
    spTree=root.find('.//'+q('p:spTree'))
    for sp in spTree.findall(q('p:sp')):
        spPr=sp.find(q('p:spPr'))
        if spPr is None: continue
        sf=spPr.find(q('a:solidFill'))
        if sf is None: continue
        bx=get_box_sp(sp)
        if not bx: continue
        x,y,cx,cy=bx[0],bx[1],bx[2],bx[3]
        if not (cx>=THR_W and 30000<=cy<=600000): continue
        # determine current colour
        srgb=sf.find(q('a:srgbClr')); sch=sf.find(q('a:schemeClr'))
        cur=None
        if srgb is not None: cur=srgb.get('val')
        if cur is not None and is_light(cur): continue        # skip white/cream
        if cur is not None and cur.upper()==TEAL: continue     # already teal
        # rebuild fill as teal
        for ch in list(sf): sf.remove(ch)
        ET.SubElement(sf,q('a:srgbClr'),{'val':TEAL})
        n+=1
    if n: log.append(f"Slide {slideno}: recoloured {n} header/section bar(s) to teal {TEAL}")
    return n

# ---------------- Fix #3: table vs heading overlap ----------------
def collect(spTree):
    items=[]
    for el in spTree:
        tag=el.tag.split('}')[1]
        if tag=='sp':
            bx=get_box_sp(el)
            if bx: items.append(('sp',el,bx))
        elif tag=='graphicFrame':
            bx=get_box_gf(el)
            if bx:
                kind='tbl' if el.find('.//'+q('a:tbl')) is not None else 'chart'
                items.append((kind,el,bx))
        elif tag=='pic':
            bx=get_box_sp(el)
            if bx: items.append(('pic',el,bx))
    return items

def hoverlap(a,b):
    return a[0]<b[0]+b[2] and b[0]<a[0]+a[2]

def fix3(root,slideno):
    spTree=root.find('.//'+q('p:spTree'))
    items=collect(spTree)
    tables=[it for it in items if it[0]=='tbl']
    moved=0
    for tk,tel,tb in tables:
        tx,ty,tcx,tcy=tb[0],tb[1],tb[2],tb[3]
        # nearest element above that horizontally overlaps
        aboves=[it for it in items if it[2] is not tb and hoverlap(it[2],tb)
                and it[2][1]<ty and it[2][1]+it[2][3]<=ty+5000]
        if not aboves: continue
        a=max(aboves,key=lambda it:it[2][1]+it[2][3])
        gap=ty-(a[2][1]+a[2][3])
        if gap>=91440: continue
        need=91440-gap
        # room below
        belows=[it for it in items if it[2] is not tb and hoverlap(it[2],tb)
                and it[2][1]>=ty+tcy-5000]
        avail=(min(it[2][1] for it in belows)-(ty+tcy)) if belows else (H-MB-(ty+tcy))
        if avail>=need:
            tb[5].set('y',str(ty+need)); moved+=1
            log.append(f"Slide {slideno}: shifted table down {need} EMU (~{need/914400:.2f}in) to clear heading (gap was {gap})")
        else:
            log.append(f"Slide {slideno}: table-heading gap tight ({gap} EMU) but no room below ({avail}); left as-is")
    return moved

# ---------------- Fix #4: chart value-axis headroom ----------------
def slide_chart_parts(slideno):
    rels=open(f'{V2}/ppt/slides/_rels/slide{slideno}.xml.rels',encoding='utf-8').read()
    out=[]
    for rid,tgt in re.findall(r'Id="([^"]+)"[^>]*Target="([^"]+)"',rels):
        if 'charts/chart' in tgt:
            out.append(os.path.normpath(f'{V2}/ppt/slides/{tgt}'))
    return out

def fix4_chart(path):
    try: tree=ET.parse(path)
    except Exception: return False
    root=tree.getroot()
    # target vertical COLUMN charts that show value labels above the bars
    # (these are the trend charts whose top label can clip); skip horizontal
    # bars, pies/doughnuts, and any chart with an explicit axis max already set
    bar=root.find('.//'+q('c:barChart'))
    if bar is None: return False
    bardir=bar.find(q('c:barDir'))
    if bardir is None or bardir.get('val')!='col': return False
    dl=root.find('.//'+q('c:dLbls'))
    if dl is None: return False
    showval=root.find('.//'+q('c:showVal'))
    if showval is None or showval.get('val') in ('0','false'): return False
    valax=root.find('.//'+q('c:valAx'))
    if valax is None: return False
    scaling=valax.find(q('c:scaling'))
    if scaling is None: return False
    if scaling.find(q('c:max')) is not None: return False   # respect explicit max
    # gather numeric values
    vals=[]
    for v in root.iter(q('c:v')):
        try: vals.append(float(v.text))
        except (TypeError,ValueError): pass
    if not vals: return False
    dmax=max(vals)
    if dmax<=0: return False
    newmax=dmax*1.15
    # round to a tidy number
    mag=10**int(math.floor(math.log10(newmax)))
    newmax=math.ceil(newmax/mag*4)/4*mag
    mx=ET.Element(q('c:max'),{'val':repr(round(newmax,4))})
    # c:max must precede c:min inside scaling; orientation may exist. Insert after orientation/logBase appropriately: simplest valid is append then reorder
    # scaling children order: logBase?, orientation?, max?, min?
    order={'logBase':0,'orientation':1,'max':2,'min':3}
    scaling.append(mx)
    scaling[:]=sorted(scaling,key=lambda e:order.get(e.tag.split('}')[1],9))
    tree.write(path,xml_declaration=True,encoding='UTF-8')
    return True

def fix4(slidenos):
    changed=0; touched=set()
    for sn in slidenos:
        for cp in slide_chart_parts(sn):
            if cp in touched: continue
            touched.add(cp)
            if fix4_chart(cp): changed+=1
    if changed:
        log.append(f"Fix #4: added value-axis headroom (~15%) to {changed} vertical column chart part(s) with value labels so top labels are not clipped (axis-only edit, no frame/layout change)")
    else:
        log.append("Fix #4: no chart parts qualified for safe axis-headroom adjustment; left unchanged")
    return changed

# ---------------- Fix #5: slide-4 panel spacing ----------------
def fix5(root):
    spTree=root.find('.//'+q('p:spTree'))
    items=collect(spTree)
    # panel cards = white rectangles, sizeable
    cards=[]
    for k,el,bx in items:
        if k!='sp': continue
        spPr=el.find(q('p:spPr'));
        if spPr is None: continue
        sf=spPr.find(q('a:solidFill'))
        if sf is None: continue
        s=sf.find(q('a:srgbClr'))
        if s is None or s.get('val').upper()!='FFFFFF': continue
        if bx[2]>2000000 and bx[3]>700000: cards.append((el,bx))
    fixed=0
    # ensure each textbox/header inside a card is inset >=0.1in
    INS=91440
    for k,el,bx in items:
        if k not in ('sp','pic'): continue
        # find the card that contains this element's centre
        cxc=bx[0]+bx[2]//2; cyc=bx[1]+bx[3]//2
        host=None
        for cel,cb in cards:
            if cel is el: continue
            if cb[0]<=cxc<=cb[0]+cb[2] and cb[1]<=cyc<=cb[1]+cb[3]:
                host=cb; break
        if not host: continue
        nx,ny,ncx,ncy=bx[0],bx[1],bx[2],bx[3]
        # clamp right/bottom within card minus inset
        if nx+ncx>host[0]+host[2]-INS:
            ncx=max(200000,host[0]+host[2]-INS-nx)
        if ny+ncy>host[1]+host[3]-INS:
            ncy=max(120000,host[1]+host[3]-INS-ny)
        if (ncx,ncy)!=(bx[2],bx[3]):
            bx[6].set('cx',str(ncx)); bx[6].set('cy',str(ncy)); fixed+=1
    if fixed:
        log.append(f"Slide 4: tightened {fixed} panel element(s) to keep a 0.1in inset inside their panel card (no content overlap of borders)")
    else:
        log.append("Slide 4: panel contents already within card bounds; grid preserved")
    return fixed

# ---------------- Fix #6: slide-15 storefront replacement ----------------
def fix6():
    # remove existing 6 pics+caps, place 3 genuine WB/Derma execution images
    sx_path=f'{V2}/ppt/slides/slide15.xml'
    rels_path=f'{V2}/ppt/slides/_rels/slide15.xml.rels'
    # source replacements (verified shelf/display execution)
    repl=[('cand15/c01.jpg','Apollo Pharmacy — Skincare aisle, West Bengal'),
          ('cand15/c06.jpg','Mamaearth DermaSoft FSU — Apollo, West Bengal'),
          ('cand15/c13.jpg','Mamaearth DermaSoft counter display — West Bengal')]
    # remove old media files referenced by slide15
    rels=open(rels_path,encoding='utf-8').read()
    old_imgs=re.findall(r'Target="\.\./media/([^"]+)"',rels)
    for m in old_imgs:
        fp=f'{V2}/ppt/media/{m}'
        if os.path.exists(fp): os.remove(fp)
    removed=len(old_imgs)
    # copy new media
    new_rel_lines=['<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout2.xml"/>']
    placed=[]
    for i,(src,cap) in enumerate(repl,1):
        newname=f'execimg_wb_{i}.jpg'
        shutil.copy(os.path.join(ROOT,src),f'{V2}/ppt/media/{newname}')
        rid=f'rId{100+i}'
        new_rel_lines.append(f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="../media/{newname}"/>')
        placed.append((rid,cap))
    open(rels_path,'w',encoding='utf-8').write(
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        +''.join(new_rel_lines)+'</Relationships>')
    # rebuild slide body: title+rule kept, images stacked 3 rows centred
    from xml.sax.saxutils import escape
    title='West Bengal & Derma Range – Execution Snapshot'
    DARK='1F2933'; WARM='FAF7F2'
    sid=100; parts=[]
    tx,ty,tw,th=ML,MT,W-2*ML,int(0.55*914400)
    parts.append(f'<p:sp><p:nvSpPr><p:cNvPr id="{sid}" name="Title"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr><p:spPr><a:xfrm><a:off x="{tx}" y="{ty}"/><a:ext cx="{tw}" cy="{th}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/></p:spPr><p:txBody><a:bodyPr wrap="square" anchor="ctr"/><a:p><a:r><a:rPr lang="en-US" sz="2000" b="1"><a:solidFill><a:srgbClr val="{TEAL}"/></a:solidFill><a:latin typeface="Aptos"/></a:rPr><a:t>{escape(title)}</a:t></a:r></a:p></p:txBody></p:sp>'); sid+=1
    ry=ty+th+int(0.02*914400)
    parts.append(f'<p:sp><p:nvSpPr><p:cNvPr id="{sid}" name="Rule"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr><p:spPr><a:xfrm><a:off x="{ML}" y="{ry}"/><a:ext cx="{W-2*ML}" cy="26000"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:solidFill><a:srgbClr val="{TEAL}"/></a:solidFill></p:spPr><p:txBody><a:bodyPr/><a:p/></p:txBody></p:sp>'); sid+=1
    grid_top=ry+60000; grid_bottom=H-MB-int(0.30*914400)
    rows=3; cell_h=(grid_bottom-grid_top)//rows
    pad=70000; cap_h=200000
    iw,ih=839,850
    for i,(rid,cap) in enumerate(placed):
        cy0=grid_top+i*cell_h
        box_w=W-2*ML-2*pad; box_h=cell_h-2*pad-cap_h
        scale=min(box_w/iw,box_h/ih); pw=int(iw*scale); ph=int(ih*scale)
        px=ML+pad+(box_w-pw)//2; py=cy0+pad+(box_h-ph)//2
        parts.append(f'<p:pic><p:nvPicPr><p:cNvPr id="{sid}" name="Pic{i}"/><p:cNvPicPr><a:picLocks noChangeAspect="1"/></p:cNvPicPr><p:nvPr/></p:nvPicPr><p:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></p:blipFill><p:spPr><a:xfrm><a:off x="{px}" y="{py}"/><a:ext cx="{pw}" cy="{ph}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:ln w="9525"><a:solidFill><a:srgbClr val="{TEAL}"/></a:solidFill></a:ln></p:spPr></p:pic>'); sid+=1
        capy=cy0+cell_h-cap_h-pad//2
        parts.append(f'<p:sp><p:nvSpPr><p:cNvPr id="{sid}" name="Cap{i}"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr><p:spPr><a:xfrm><a:off x="{ML+pad}" y="{capy}"/><a:ext cx="{box_w}" cy="{cap_h}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/></p:spPr><p:txBody><a:bodyPr wrap="square" anchor="ctr" lIns="20000" rIns="20000" tIns="0" bIns="0"/><a:p><a:pPr algn="ctr"/><a:r><a:rPr lang="en-US" sz="1000"><a:solidFill><a:srgbClr val="{DARK}"/></a:solidFill><a:latin typeface="Aptos"/></a:rPr><a:t>{escape(cap)}</a:t></a:r></a:p></p:txBody></p:sp>'); sid+=1
    # footer page number
    fx=W-int(1.4*914400); fy=H-MB-int(0.05*914400)
    parts.append(f'<p:sp><p:nvSpPr><p:cNvPr id="{sid}" name="PageNum"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr><p:spPr><a:xfrm><a:off x="{fx}" y="{fy}"/><a:ext cx="{int(1.1*914400)}" cy="{int(0.25*914400)}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/></p:spPr><p:txBody><a:bodyPr wrap="none" lIns="0" rIns="0" tIns="0" bIns="0"/><a:p><a:pPr algn="r"/><a:r><a:rPr lang="en-US" sz="900"><a:solidFill><a:srgbClr val="{DARK}"/></a:solidFill><a:latin typeface="Aptos"/></a:rPr><a:t>15 / 20</a:t></a:r></a:p></p:txBody></p:sp>')
    body=''.join(parts)
    slidexml=('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'
      '<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
      'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
      'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
      f'<p:cSld><p:bg><p:bgPr><a:solidFill><a:srgbClr val="{WARM}"/></a:solidFill><a:effectLst/></p:bgPr></p:bg>'
      '<p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
      '<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>'
      f'{body}</p:spTree></p:cSld></p:sld>')
    open(sx_path,'w',encoding='utf-8').write(slidexml)
    log.append(f"Slide 15: removed {removed} Apollo storefront/exterior images (non-execution); replaced with 3 genuine WB/Derma shelf & DermaSoft FSU execution photos in a clean 3-up layout; cleaned up {removed} orphaned media files & rels")

# ================= run =================
def process_slide(n):
    p=f'{V2}/ppt/slides/slide{n}.xml'
    tree=ET.parse(p); root=tree.getroot()
    fix1(root,n)
    fix3(root,n)
    if n==4: fix5(root)
    tree.write(p,xml_declaration=True,encoding='UTF-8')

for n in range(1,15):
    process_slide(n)
fix4(list(range(1,13)))   # chart-bearing slides
fix6()

print('\n'.join(log))
print('\nDONE')
