"""
Extend the July command centre template with national category trend slides.
- Clones slide 7 (zone deep dive) twice → slides 23 and 24
- Gives each clone its OWN chart XML files (not shared)
- Updates chart data and slide text to show national ME and TDC trends
- Modifies slide 25 (cloned from slide 21, the 90-day action plan) into chain action register
"""
import os, shutil, re, copy
from pathlib import Path
import defusedxml.minidom as dxml
from xml.dom import minidom

BASE = Path('/home/user/mt-dashboard/tpl_cmd')
CT_FILE = BASE / '[Content_Types].xml'

def parse_xml(path):
    return dxml.parse(str(path))

def write_xml(dom, path):
    txt = dom.toxml(encoding='UTF-8')
    if isinstance(txt, bytes):
        txt = txt.decode('utf-8')
    # Fix standalone declaration
    txt = txt.replace("<?xml version=\"1.0\" encoding=\"UTF-8\"?>",
                      "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>")
    with open(path, 'w', encoding='utf-8') as f:
        f.write(txt)

def next_chart_id():
    charts = sorted(BASE.glob('ppt/charts/chart*.xml'))
    nums = [int(re.search(r'chart(\d+)\.xml', c.name).group(1)) for c in charts]
    return max(nums) + 1 if nums else 1

def clone_chart(src_chart_name, new_data_series):
    """Clone a chart XML file with new data series."""
    src = BASE / 'ppt' / 'charts' / src_chart_name
    nid = next_chart_id()
    dst_name = f'chart{nid}.xml'
    dst = BASE / 'ppt' / 'charts' / dst_name

    # Read source chart XML as text, then parse
    text = src.read_text(encoding='utf-8')
    doc = dxml.parseString(text.encode('utf-8'))

    # Update chart series data
    # Find all c:ser elements
    ns = {
        'c': 'http://schemas.openxmlformats.org/drawingml/2006/chart',
        'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
    }

    root = doc.documentElement

    # Find all ser (series) elements
    ser_elements = root.getElementsByTagNameNS(
        'http://schemas.openxmlformats.org/drawingml/2006/chart', 'ser')

    for i, ser in enumerate(ser_elements):
        if i >= len(new_data_series):
            break
        series_data = new_data_series[i]

        # Update series name
        if 'name' in series_data:
            tx_elements = ser.getElementsByTagNameNS(
                'http://schemas.openxmlformats.org/drawingml/2006/chart', 'tx')
            if tx_elements:
                strRef = tx_elements[0].getElementsByTagNameNS(
                    'http://schemas.openxmlformats.org/drawingml/2006/chart', 'strRef')
                if strRef:
                    strCache = strRef[0].getElementsByTagNameNS(
                        'http://schemas.openxmlformats.org/drawingml/2006/chart', 'strCache')
                    if strCache:
                        ptElems = strCache[0].getElementsByTagNameNS(
                            'http://schemas.openxmlformats.org/drawingml/2006/chart', 'pt')
                        for pt in ptElems:
                            v = pt.getElementsByTagNameNS(
                                'http://schemas.openxmlformats.org/drawingml/2006/chart', 'v')
                            if v:
                                v[0].firstChild.nodeValue = series_data['name']

        # Update values
        if 'values' in series_data:
            vals_element = ser.getElementsByTagNameNS(
                'http://schemas.openxmlformats.org/drawingml/2006/chart', 'val')
            if vals_element:
                numRef = vals_element[0].getElementsByTagNameNS(
                    'http://schemas.openxmlformats.org/drawingml/2006/chart', 'numRef')
                if numRef:
                    numCache = numRef[0].getElementsByTagNameNS(
                        'http://schemas.openxmlformats.org/drawingml/2006/chart', 'numCache')
                    if numCache:
                        pts = numCache[0].getElementsByTagNameNS(
                            'http://schemas.openxmlformats.org/drawingml/2006/chart', 'pt')
                        for j, pt in enumerate(pts):
                            if j < len(series_data['values']):
                                v = pt.getElementsByTagNameNS(
                                    'http://schemas.openxmlformats.org/drawingml/2006/chart', 'v')
                                if v:
                                    v[0].firstChild.nodeValue = str(series_data['values'][j])

        # Update category labels if provided
        if 'labels' in series_data:
            cat_element = ser.getElementsByTagNameNS(
                'http://schemas.openxmlformats.org/drawingml/2006/chart', 'cat')
            if cat_element:
                strRef = cat_element[0].getElementsByTagNameNS(
                    'http://schemas.openxmlformats.org/drawingml/2006/chart', 'strRef')
                if strRef:
                    strCache = strRef[0].getElementsByTagNameNS(
                        'http://schemas.openxmlformats.org/drawingml/2006/chart', 'strCache')
                    if strCache:
                        pts = strCache[0].getElementsByTagNameNS(
                            'http://schemas.openxmlformats.org/drawingml/2006/chart', 'pt')
                        for j, pt in enumerate(pts):
                            if j < len(series_data['labels']):
                                v = pt.getElementsByTagNameNS(
                                    'http://schemas.openxmlformats.org/drawingml/2006/chart', 'v')
                                if v:
                                    v[0].firstChild.nodeValue = str(series_data['labels'][j])

    write_xml(doc, dst)

    # Clone chart rels if they exist
    src_rels = src.parent / '_rels' / (src_chart_name + '.rels')
    if src_rels.exists():
        dst_rels = dst.parent / '_rels' / (dst_name + '.rels')
        shutil.copy2(src_rels, dst_rels)

    # Register in Content_Types.xml
    ct_doc = dxml.parse(str(CT_FILE))
    types = ct_doc.documentElement
    # Check if already registered
    existing = [e for e in types.getElementsByTagName('Override')
                if dst_name in (e.getAttribute('PartName') or '')]
    if not existing:
        new_override = ct_doc.createElement('Override')
        new_override.setAttribute('PartName', f'/ppt/charts/{dst_name}')
        new_override.setAttribute('ContentType',
            'application/vnd.openxmlformats-officedocument.drawingml.chart+xml')
        types.appendChild(new_override)
        write_xml(ct_doc, CT_FILE)

    return dst_name, nid


def update_slide_rels(slide_num, old_chart_name, new_chart_name, rel_id):
    """Update a slide's rels to point to a new chart file."""
    rels_file = BASE / 'ppt' / 'slides' / '_rels' / f'slide{slide_num}.xml.rels'
    content = rels_file.read_text(encoding='utf-8')
    content = content.replace(
        f'Target="../charts/{old_chart_name}"',
        f'Target="../charts/{new_chart_name}"'
    )
    rels_file.write_text(content, encoding='utf-8')


def update_slide_text(slide_path, replacements):
    """Replace text in a slide XML. replacements = list of (old, new) tuples."""
    content = slide_path.read_text(encoding='utf-8')
    for old, new in replacements:
        content = content.replace(old, new)
    slide_path.write_text(content, encoding='utf-8')


# ─── National Mamaearth category trends (slide 23) ───────────────────────────
# Source: sum of all zones from the template's zone slides

ME_FACE_CLEANER_NATIONAL = [7.03, 8.17, 8.55, 9.63, 9.65, 8.53]
ME_SHAMPOO_NATIONAL      = [4.81, 5.38, 6.11, 6.68, 6.87, 6.95]
ME_SUNCARE_NATIONAL      = [1.55, 2.73, 3.10, 2.95, 1.99, 1.30]

TDC_FACE_CLEANSER_NATIONAL = [2.25, 2.75, 3.24, 4.63, 4.83, 7.13]
TDC_SUNCARE_NATIONAL       = [1.04, 1.81, 2.27, 3.18, 2.05, 1.99]
TDC_FACE_SERUM_NATIONAL    = [0.56, 0.57, 0.69, 0.66, 0.66, 0.63]

MONTHS = ['Feb 26', 'Mar 26', 'Apr 26', 'May 26', 'Jun 26', 'Jul 26']

print("Cloning charts for slide 23 (National ME categories)...")
me_chart_name, me_cid = clone_chart('chart7.xml', [
    {'name': 'Face Cleanser', 'values': ME_FACE_CLEANER_NATIONAL, 'labels': MONTHS},
    {'name': 'Shampoo',       'values': ME_SHAMPOO_NATIONAL,      'labels': MONTHS},
    {'name': 'Sun Care',      'values': ME_SUNCARE_NATIONAL,       'labels': MONTHS},
])
print(f"  Created {me_chart_name}")

print("Cloning charts for slide 23 (National TDC categories)...")
tdc_chart_name, tdc_cid = clone_chart('chart8.xml', [
    {'name': 'Face Cleanser', 'values': TDC_FACE_CLEANSER_NATIONAL, 'labels': MONTHS},
    {'name': 'Sun Care',      'values': TDC_SUNCARE_NATIONAL,        'labels': MONTHS},
    {'name': 'Face Serum',    'values': TDC_FACE_SERUM_NATIONAL,     'labels': MONTHS},
])
print(f"  Created {tdc_chart_name}")

# Update slide 23 rels to use new charts
print("Updating slide 23 rels...")
update_slide_rels(23, 'chart7.xml', me_chart_name, 'rId3')
update_slide_rels(23, 'chart8.xml', tdc_chart_name, 'rId4')

# Update slide 23 text content
slide23_path = BASE / 'ppt' / 'slides' / 'slide23.xml'
update_slide_text(slide23_path, [
    ('West: Protect and convert', 'National category trends: six months of offtake'),
    ('West', 'MT National'),
    ('07', '23'),
    ('₹9.71 Cr', '₹36.10 Cr'),
    ('₹8.27 Cr', '₹36.10 Cr'),
    ('85.2%', '72.2%'),
    ('₹1.44 Cr', '₹13.06 Cr'),
    ('24.4% mix', '100.0% of MT'),
    ('July billing', 'National MT'),
    ('PRIORITY', 'NATIONAL PICTURE'),
    ('Hold DMart execution as the national template • Reliance is the only weak cell',
     'Face Cleanser leads ME; TDC Face Wash is the breakout — +47.6% MoM, new record ₹7.13 Cr'),
])
print("Slide 23 updated.")

# ─── Slide 24: TDC Face Wash breakthrough slide (same zone format) ────────────
print("\nCloning charts for slide 24 (TDC FW breakthrough)...")
tdc2_chart_name, _ = clone_chart('chart7.xml', [
    {'name': 'Face Cleanser (TDC)', 'values': TDC_FACE_CLEANSER_NATIONAL, 'labels': MONTHS},
    {'name': 'ME Face Cleanser',    'values': ME_FACE_CLEANER_NATIONAL,   'labels': MONTHS},
    {'name': 'Shampoo (ME)',        'values': ME_SHAMPOO_NATIONAL,         'labels': MONTHS},
])
print(f"  Created {tdc2_chart_name}")

tdc3_chart_name, _ = clone_chart('chart8.xml', [
    {'name': 'TDC Sun Care',   'values': TDC_SUNCARE_NATIONAL,       'labels': MONTHS},
    {'name': 'TDC Face Serum', 'values': TDC_FACE_SERUM_NATIONAL,    'labels': MONTHS},
    {'name': 'ME Sun Care',    'values': ME_SUNCARE_NATIONAL,         'labels': MONTHS},
])
print(f"  Created {tdc3_chart_name}")

update_slide_rels(24, 'chart7.xml', tdc2_chart_name, 'rId3')
update_slide_rels(24, 'chart8.xml', tdc3_chart_name, 'rId4')

slide24_path = BASE / 'ppt' / 'slides' / 'slide24.xml'
update_slide_text(slide24_path, [
    ('West: Protect and convert', 'TDC Face Wash breakthrough — ₹7.13 Cr, +47.6% MoM'),
    ('West', 'The Derma Co.'),
    ('07', '24'),
    ('₹9.71 Cr', '₹15.19 Cr'),
    ('₹8.27 Cr', '₹11.03 Cr'),
    ('85.2%', '72.6%'),
    ('₹1.44 Cr', '₹4.16 Cr'),
    ('24.4% mix', '31% brand mix'),
    ('July billing', 'TDC primary'),
    ('PRIORITY', 'THE SIGNAL'),
    ('Hold DMart execution as the national template • Reliance is the only weak cell',
     'TDC Face Wash ₹7.13 Cr is the fastest-growing MT category — +217% since Feb. Ensure ≥21-day DOI before Aug-10'),
])
print("Slide 24 updated.")

# ─── Slide 25: Chain action register (from slide 21 clone) ───────────────────
slide25_path = BASE / 'ppt' / 'slides' / 'slide25.xml'
update_slide_text(slide25_path, [
    ('A 90-day cadence that converts ₹6.22 Cr without loading a single extra case',
     'August action register — seven commitments, Aug-31 deadline'),
    ('61–90d', '61-90d'),
])
print("Slide 25 updated.")

print("\nAll enrichment slides updated. Ready to repack.")
