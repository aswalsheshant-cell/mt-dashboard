#!/usr/bin/env python3
"""V3 enhancements applied on top of the CORRECTED_V2 deck (stdlib only):

  1. Font unification  -> every concrete text typeface set to Calibri
                          (theme major/minor also Calibri; theme refs +mj-lt/
                          +mn-lt left intact so they resolve to Calibri).
  2. Zone-slide margin alignment -> all full-width content blocks (tables,
                          header bars, highlight box, chain-key group) snapped
                          to a common left/right [212691, 7139214]; table
                          columns rescaled to match. Full-bleed bands skipped.
  3. Zone key insights -> one extra "Zone Insight" line added to the Key
                          Performance Highlights box on slides 7-11, incl.
                          South-1 = Karnataka/Tamil Nadu/Kerala and
                          South-2 = Andhra Pradesh & Telangana coverage.

The PACK SIZE DEEP DIVE slide insertion lives in insert_pack_size_slide.py.
Run this first (on the unzipped deck dir, default 'w/'), then the inserter.
"""
import xml.etree.ElementTree as ET, glob, re, os, sys

ROOT=sys.argv[1] if len(sys.argv)>1 else 'w'
NSMAP={'a':'http://schemas.openxmlformats.org/drawingml/2006/main',
 'p':'http://schemas.openxmlformats.org/presentationml/2006/main',
 'r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
 'c':'http://schemas.openxmlformats.org/drawingml/2006/chart',
 'a14':'http://schemas.microsoft.com/office/drawing/2010/main',
 'a16':'http://schemas.microsoft.com/office/drawing/2014/main',
 'p14':'http://schemas.microsoft.com/office/powerpoint/2010/main'}
for p,u in NSMAP.items(): ET.register_namespace(p,u)
def q(t):x,l=t.split(':');return f'{{{NSMAP[x]}}}{l}'
FONT='Calibri'; TL=212691; TR=7139214; TW=TR-TL

# ---------- 1. font unification ----------
def unify_font(path):
    tree=ET.parse(path); root=tree.getroot()
    for tag in ('a:latin','a:ea','a:cs'):
        for el in root.iter(q(tag)):
            tf=el.get('typeface')
            if tf is not None and not tf.startswith('+') and tf!=FONT:
                el.set('typeface',FONT)
    tree.write(path,xml_declaration=True,encoding='UTF-8')

# ---------- 2. zone margin alignment ----------
def align(path):
    tree=ET.parse(path); root=tree.getroot(); sp=root.find('.//'+q('p:spTree'))
    for el in list(sp):
        tag=el.tag.split('}')[1]
        if tag in ('nvGrpSpPr','grpSpPr'): continue
        xf=el.find(q('p:xfrm')) if tag=='graphicFrame' else el.find('.//'+q('a:xfrm'))
        if xf is None: continue
        o=xf.find(q('a:off')); e=xf.find(q('a:ext'))
        if o is None or e is None: continue
        L=int(o.get('x')); wd=int(e.get('cx'))
        if L<0 or not (5000000<wd<7400000): continue
        o.set('x',str(TL)); e.set('cx',str(TW))
        tbl=el.find('.//'+q('a:tbl'))
        if tbl is not None:
            cols=tbl.find(q('a:tblGrid')).findall(q('a:gridCol'))
            ws=[int(c.get('w')) for c in cols]; Ssum=sum(ws)
            if Ssum>0:
                sc=[round(w*TW/Ssum) for w in ws]; sc[-1]+=TW-sum(sc)
                for c,nw in zip(cols,sc): c.set('w',str(nw))
    tree.write(path,xml_declaration=True,encoding='UTF-8')

# ---------- 3. zone key insights ----------
INS={
 7:"Zone Insight: Mamaearth anchors the East mix; The Derma Co. is the fastest-growing brand YoY.",
 8:"Zone Insight: Mamaearth anchors the North mix; The Derma Co. is the fastest-growing brand YoY.",
 9:"Zone Insight: South-1 covers Karnataka, Tamil Nadu & Kerala; Mamaearth leads, The Derma Co. scaling fast.",
 10:"Zone Insight: South-2 covers Andhra Pradesh & Telangana; Mamaearth leads, The Derma Co. scaling fast.",
 11:"Zone Insight: Mamaearth anchors the West mix; The Derma Co. is the fastest-growing brand YoY."}
def make_para(text):
    label,rest=text.split(':',1)
    p=ET.Element(q('a:p'))
    pPr=ET.SubElement(p,q('a:pPr'),{'marL':'184150','indent':'-57150'})
    ET.SubElement(ET.SubElement(pPr,q('a:spcBef')),q('a:spcPts'),{'val':'55'})
    ET.SubElement(ET.SubElement(pPr,q('a:tabLst')),q('a:tab'),{'pos':'184150','algn':'l'})
    def run(t,b):
        r=ET.SubElement(p,q('a:r')); rPr=ET.SubElement(r,q('a:rPr'),{'sz':'1050','dirty':'0'})
        if b: rPr.set('b','1')
        ET.SubElement(rPr,q('a:latin'),{'typeface':'+mj-lt'})
        ET.SubElement(r,q('a:t')).text=t
    run(label+':',True); run(rest,False)
    return p
def add_insight(n):
    f=f'{ROOT}/ppt/slides/slide{n}.xml'; tree=ET.parse(f); root=tree.getroot()
    for s in root.iter(q('p:sp')):
        if 'Key Performance' in ''.join(t.text or '' for t in s.iter(q('a:t'))):
            xf=s.find('.//'+q('a:xfrm')); xf.find(q('a:off')).set('y','888000')
            xf.find(q('a:ext')).set('cy','1040000')
            s.find(q('p:txBody')).append(make_para(INS[n])); break
    tree.write(f,xml_declaration=True,encoding='UTF-8')

if __name__=='__main__':
    targets=(glob.glob(f'{ROOT}/ppt/slides/slide*.xml')
             +glob.glob(f'{ROOT}/ppt/slideLayouts/slideLayout*.xml')
             +glob.glob(f'{ROOT}/ppt/slideMasters/slideMaster*.xml')
             +[f'{ROOT}/ppt/theme/theme1.xml'])
    for f in targets: unify_font(f)
    for n in range(7,13): align(f'{ROOT}/ppt/slides/slide{n}.xml')
    for n in INS: add_insight(n)
    print('V3 enhancements applied to', ROOT)
