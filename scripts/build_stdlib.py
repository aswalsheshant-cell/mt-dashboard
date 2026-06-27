#!/usr/bin/env python3
"""Stdlib-only builder: operates on the already-unzipped leadership deck
('lead/') and the 4 unzipped source decks ('d_*/'), appends execution
image slides, adds warm background + page-number footers, and rezips to
Final_Portrait_Leadership_Corrected.pptx. No pip packages required."""
import os, re, shutil, struct, hashlib, zipfile, glob
from xml.sax.saxutils import escape

ROOT = os.path.dirname(os.path.abspath(__file__))
LEAD = os.path.join(ROOT, "lead")
BUILD = os.path.join(ROOT, "build")
OUT = os.path.join(ROOT, "Final_Portrait_Leadership_Corrected.pptx")
SRC_DIRS = ["d_8291de", "d_9c497f", "d_251d62", "d_3968af"]

# ---- slide geometry (EMU) ----
W, H = 7562850, 10688638
IN = 914400
ML = int(0.3 * IN); MT = int(0.25 * IN); MB = int(0.25 * IN)
TEAL = "2D9B7F"; WARM = "FAF7F2"; DARK = "1F2933"; WHITE = "FFFFFF"

# --------------------------------------------------------------------------
def img_dims(path):
    with open(path, "rb") as f:
        head = f.read(2)
        f.seek(0)
        if head == b"\xff\xd8":
            f.read(2)
            while True:
                m = f.read(2)
                if len(m) < 2 or m[0] != 0xFF:
                    return (839, 850)
                if m[1] in (0xC0,0xC1,0xC2,0xC3,0xC5,0xC6,0xC7,0xC9,0xCA,0xCB,0xCD,0xCE,0xCF):
                    f.read(3); h, w = struct.unpack(">HH", f.read(4)); return (w, h)
                seg = struct.unpack(">H", f.read(2))[0]; f.read(seg-2)
        blob = open(path, "rb").read(24)
        if blob[:8] == b"\x89PNG\r\n\x1a\n":
            w, h = struct.unpack(">II", blob[16:24]); return (w, h)
    return (839, 850)

# --------------------------------------------------------------------------
def harvest():
    """Return list of dicts: {path, caption, size, hash}."""
    out, seen = [], set()
    for d in SRC_DIRS:
        sld_dir = os.path.join(ROOT, d, "ppt", "slides")
        for sx in sorted(glob.glob(os.path.join(sld_dir, "slide*.xml")),
                         key=lambda p: int(re.search(r"slide(\d+)", p).group(1))):
            xml = open(sx, encoding="utf-8").read()
            embeds = re.findall(r'r:embed="([^"]+)"', xml)
            if not embeds:
                continue
            rels_path = os.path.join(sld_dir, "_rels", os.path.basename(sx) + ".rels")
            rels = open(rels_path, encoding="utf-8").read()
            rid_map = dict(re.findall(r'Id="([^"]+)"[^>]*Target="([^"]+)"', rels))
            texts = re.findall(r"<a:t>([^<]*)</a:t>", xml)
            caption = (texts[0].strip() if texts else d).replace("&amp;", "&")
            for rid in embeds:
                tgt = rid_map.get(rid, "")
                if "media" not in tgt:
                    continue
                media = os.path.normpath(os.path.join(sld_dir, tgt))
                if not os.path.exists(media):
                    continue
                blob = open(media, "rb").read()
                h = hashlib.md5(blob).hexdigest()
                if h in seen or len(blob) < 60000:
                    continue
                seen.add(h)
                out.append({"path": media, "caption": caption,
                            "size": len(blob), "hash": h})
    return out

def pick(images, keys, n, used):
    res = []
    for im in sorted(images, key=lambda i: i["size"], reverse=True):
        if im["hash"] in used:
            continue
        low = im["caption"].lower()
        if keys and not any(k in low for k in keys):
            continue
        res.append(im)
        if len(res) >= n:
            break
    for im in res:
        used.add(im["hash"])
    return res

def fill(images, n, used):
    """Top up a selection from any remaining strong images."""
    res = []
    for im in sorted(images, key=lambda i: i["size"], reverse=True):
        if im["hash"] in used:
            continue
        res.append(im); used.add(im["hash"])
        if len(res) >= n:
            break
    return res

# --------------------------------------------------------------------------
def short(text, n=46):
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= n else text[:n-1] + "…"

def footer_sp(idx, total, sid):
    fx = W - int(1.4*IN); fy = H - MB - int(0.05*IN); fw = int(1.1*IN); fh = int(0.25*IN)
    return (f'<p:sp><p:nvSpPr><p:cNvPr id="{sid}" name="PageNum"/><p:cNvSpPr txBox="1"/>'
            f'<p:nvPr/></p:nvSpPr><p:spPr><a:xfrm><a:off x="{fx}" y="{fy}"/>'
            f'<a:ext cx="{fw}" cy="{fh}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/>'
            f'</a:prstGeom><a:noFill/></p:spPr><p:txBody><a:bodyPr wrap="none" lIns="0" '
            f'rIns="0" tIns="0" bIns="0"/><a:p><a:pPr algn="r"/><a:r><a:rPr lang="en-US" '
            f'sz="900"><a:solidFill><a:srgbClr val="{DARK}"/></a:solidFill>'
            f'<a:latin typeface="Aptos"/></a:rPr><a:t>{idx} / {total}</a:t></a:r></a:p>'
            f'</p:txBody></p:sp>')

def bg_xml():
    return (f'<p:bg><p:bgPr><a:solidFill><a:srgbClr val="{WARM}"/></a:solidFill>'
            f'<a:effectLst/></p:bgPr></p:bg>')

def build_exec_slide(title, images, rel_imgs, page_idx, total):
    """rel_imgs: list of (rId, dims) parallel to images."""
    sid = 100
    parts = []
    # title
    tx, ty, tw, th = ML, MT, W - 2*ML, int(0.55*IN)
    parts.append(
        f'<p:sp><p:nvSpPr><p:cNvPr id="{sid}" name="Title"/><p:cNvSpPr txBox="1"/>'
        f'<p:nvPr/></p:nvSpPr><p:spPr><a:xfrm><a:off x="{tx}" y="{ty}"/>'
        f'<a:ext cx="{tw}" cy="{th}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/>'
        f'</a:prstGeom><a:noFill/></p:spPr><p:txBody><a:bodyPr wrap="square" '
        f'anchor="ctr"/><a:p><a:r><a:rPr lang="en-US" sz="2000" b="1">'
        f'<a:solidFill><a:srgbClr val="{TEAL}"/></a:solidFill>'
        f'<a:latin typeface="Aptos"/></a:rPr><a:t>{escape(title)}</a:t></a:r>'
        f'</a:p></p:txBody></p:sp>')
    sid += 1
    # teal underline rule
    ry = ty + th + int(0.02*IN)
    parts.append(
        f'<p:sp><p:nvSpPr><p:cNvPr id="{sid}" name="Rule"/><p:cNvSpPr/><p:nvPr/>'
        f'</p:nvSpPr><p:spPr><a:xfrm><a:off x="{ML}" y="{ry}"/>'
        f'<a:ext cx="{W-2*ML}" cy="26000"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/>'
        f'</a:prstGeom><a:solidFill><a:srgbClr val="{TEAL}"/></a:solidFill>'
        f'</p:spPr><p:txBody><a:bodyPr/><a:p/></p:txBody></p:sp>')
    sid += 1

    n = len(images)
    cols = 2
    rows = (n + cols - 1) // cols
    grid_top = ry + 40000
    grid_bottom = H - MB - int(0.30*IN)
    grid_left, grid_right = ML, W - ML
    cell_w = (grid_right - grid_left) // cols
    cell_h = (grid_bottom - grid_top) // rows
    pad = 55000; cap_h = 200000

    for i, (im, (rid, dims)) in enumerate(zip(images, rel_imgs)):
        r, c = divmod(i, cols)
        cx = grid_left + c*cell_w
        cy = grid_top + r*cell_h
        box_w = cell_w - 2*pad
        box_h = cell_h - 2*pad - cap_h
        iw, ih = dims
        scale = min(box_w/iw, box_h/ih)
        pw, ph = int(iw*scale), int(ih*scale)
        px = cx + pad + (box_w - pw)//2
        py = cy + pad + (box_h - ph)//2
        parts.append(
            f'<p:pic><p:nvPicPr><p:cNvPr id="{sid}" name="Pic{i}"/>'
            f'<p:cNvPicPr><a:picLocks noChangeAspect="1"/></p:cNvPicPr><p:nvPr/>'
            f'</p:nvPicPr><p:blipFill><a:blip r:embed="{rid}"/><a:stretch>'
            f'<a:fillRect/></a:stretch></p:blipFill><p:spPr><a:xfrm>'
            f'<a:off x="{px}" y="{py}"/><a:ext cx="{pw}" cy="{ph}"/></a:xfrm>'
            f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>'
            f'<a:ln w="9525"><a:solidFill><a:srgbClr val="{TEAL}"/></a:solidFill>'
            f'</a:ln></p:spPr></p:pic>')
        sid += 1
        capx = cx + pad; capy = cy + cell_h - cap_h - pad//2
        parts.append(
            f'<p:sp><p:nvSpPr><p:cNvPr id="{sid}" name="Cap{i}"/>'
            f'<p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr><p:spPr><a:xfrm>'
            f'<a:off x="{capx}" y="{capy}"/><a:ext cx="{box_w}" cy="{cap_h}"/></a:xfrm>'
            f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/></p:spPr>'
            f'<p:txBody><a:bodyPr wrap="square" anchor="ctr" lIns="20000" rIns="20000" '
            f'tIns="0" bIns="0"/><a:p><a:pPr algn="ctr"/><a:r><a:rPr lang="en-US" '
            f'sz="900"><a:solidFill><a:srgbClr val="{DARK}"/></a:solidFill>'
            f'<a:latin typeface="Aptos"/></a:rPr><a:t>{escape(short(im["caption"]))}'
            f'</a:t></a:r></a:p></p:txBody></p:sp>')
        sid += 1

    parts.append(footer_sp(page_idx, total, sid))

    body = "".join(parts)
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'
        '<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
        'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
        f'<p:cSld>{bg_xml()}<p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/>'
        '<p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm>'
        '<a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/>'
        f'<a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>{body}</p:spTree></p:cSld>'
        '<p:clrMapOvr><a:overrideClrMapping '
        'bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" '
        'accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" '
        'hlink="hlink" folHlink="folHlink"/></p:clrMapOvr></p:sld>')

# --------------------------------------------------------------------------
def patch_existing(total):
    """Add warm bg + footer page number to each of the 14 original slides."""
    sld_dir = os.path.join(BUILD, "ppt", "slides")
    for i in range(1, 15):
        p = os.path.join(sld_dir, f"slide{i}.xml")
        xml = open(p, encoding="utf-8").read()
        # find max existing id to avoid collision
        ids = [int(x) for x in re.findall(r'<p:cNvPr id="(\d+)"', xml)]
        fid = (max(ids) if ids else 1) + 50
        # warm background: insert before first <p:spTree>
        if "<p:bg>" not in xml:
            xml = xml.replace("<p:spTree>", bg_xml() + "<p:spTree>", 1)
        # footer before last </p:spTree>
        idx = xml.rfind("</p:spTree>")
        xml = xml[:idx] + footer_sp(i, total, fid) + xml[idx:]
        open(p, "w", encoding="utf-8").write(xml)

# --------------------------------------------------------------------------
def main():
    if os.path.exists(BUILD):
        shutil.rmtree(BUILD)
    shutil.copytree(LEAD, BUILD)

    images = harvest()
    print(f"Harvested {len(images)} unique execution images")

    used = set()
    plan = [
        ("West Bengal & Derma Range – Execution Snapshot",
         ["derma", "baby", "w.b", "wb", "mbec", "bengal"], 6),
        ("Gujarat Region – Execution Snapshot",
         ["gujarat", "hardik", "ganesh", "rom"], 6),
        ("JC Review Markets – Execution Snapshot",
         ["jc", "chakri", "radhika", "review"], 6),
        ("TDC / SIS Delhi NCR – Execution Snapshot",
         ["tdc", "sis", "delhi", "ncr"], 6),
        ("Stock Depth & Article Range Across Outlets",
         ["sumo", "save", "display", "ppt", "reveiw", "review"], 6),
        ("SOS / SOA – Honasa Portfolio Visibility",
         ["sos", "soa", "visibility", "mbec", "display"], 4),
    ]
    selections = []
    for title, keys, n in plan:
        sel = pick(images, keys, n, used)
        if len(sel) < n:
            sel += fill(images, n - len(sel), used)
        selections.append((title, sel))
        print(f"  {title}: {len(sel)} imgs")

    total = 14 + len(selections)

    # copy chosen images into build media + assemble per-slide rels
    media_dir = os.path.join(BUILD, "ppt", "media")
    ct_path = os.path.join(BUILD, "[Content_Types].xml")
    ct = open(ct_path, encoding="utf-8").read()
    pres_rels_path = os.path.join(BUILD, "ppt", "_rels", "presentation.xml.rels")
    pres_rels = open(pres_rels_path, encoding="utf-8").read()
    pres_path = os.path.join(BUILD, "ppt", "presentation.xml")
    pres = open(pres_path, encoding="utf-8").read()

    existing_rids = [int(x[3:]) for x in re.findall(r'Id="(rId\d+)"', pres_rels)]
    next_rid = max(existing_rids) + 1
    existing_sids = [int(x) for x in re.findall(r'<p:sldId id="(\d+)"', pres)]
    next_sid = max(existing_sids) + 1

    ct_inserts = []; rels_inserts = []; sldid_inserts = []
    img_counter = 0
    for k, (title, sel) in enumerate(selections, start=15):
        # copy images, build rels
        rel_lines = ['<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/'
                     'officeDocument/2006/relationships/slideLayout" '
                     'Target="../slideLayouts/slideLayout2.xml"/>']
        rel_imgs = []
        for j, im in enumerate(sel):
            img_counter += 1
            newname = f"execimg{img_counter}.jpg"
            shutil.copy(im["path"], os.path.join(media_dir, newname))
            rid = f"rId{100+j}"
            rel_lines.append(
                f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/'
                f'officeDocument/2006/relationships/image" Target="../media/{newname}"/>')
            rel_imgs.append((rid, img_dims(im["path"])))
        slide_xml = build_exec_slide(title, sel, rel_imgs, k, total)
        open(os.path.join(BUILD, "ppt", "slides", f"slide{k}.xml"), "w",
             encoding="utf-8").write(slide_xml)
        rels_xml = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'
                    '<Relationships xmlns="http://schemas.openxmlformats.org/package/'
                    '2006/relationships">' + "".join(rel_lines) + "</Relationships>")
        open(os.path.join(BUILD, "ppt", "slides", "_rels", f"slide{k}.xml.rels"), "w",
             encoding="utf-8").write(rels_xml)

        ct_inserts.append(f'<Override PartName="/ppt/slides/slide{k}.xml" '
                          'ContentType="application/vnd.openxmlformats-officedocument.'
                          'presentationml.slide+xml"/>')
        rid = f"rId{next_rid}"
        rels_inserts.append(f'<Relationship Id="{rid}" Type="http://schemas.'
                            'openxmlformats.org/officeDocument/2006/relationships/slide" '
                            f'Target="slides/slide{k}.xml"/>')
        sldid_inserts.append(f'<p:sldId id="{next_sid}" r:id="{rid}"/>')
        next_rid += 1; next_sid += 1

    ct = ct.replace("</Types>", "".join(ct_inserts) + "</Types>")
    open(ct_path, "w", encoding="utf-8").write(ct)
    pres_rels = pres_rels.replace("</Relationships>", "".join(rels_inserts) + "</Relationships>")
    open(pres_rels_path, "w", encoding="utf-8").write(pres_rels)
    pres = pres.replace("</p:sldIdLst>", "".join(sldid_inserts) + "</p:sldIdLst>")
    open(pres_path, "w", encoding="utf-8").write(pres)

    patch_existing(total)

    # rezip
    if os.path.exists(OUT):
        os.remove(OUT)
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        # content types first is conventional
        z.write(ct_path, "[Content_Types].xml")
        for base, _, files in os.walk(BUILD):
            for fn in files:
                full = os.path.join(base, fn)
                arc = os.path.relpath(full, BUILD)
                if arc == "[Content_Types].xml":
                    continue
                z.write(full, arc)
    print("Wrote", OUT, os.path.getsize(OUT), "bytes")

if __name__ == "__main__":
    main()
