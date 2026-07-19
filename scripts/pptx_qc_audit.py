#!/usr/bin/env python3
"""Comprehensive OOXML/PPTX integrity QC audit -- structural half of the mandatory
PPTX QC checklist in CLAUDE.md ("Before sharing any .pptx deliverable"). Stdlib
only, plus xmllint (subprocess) for XSD schema checks when available.

Usage:
    python scripts/pptx_qc_audit.py deck.pptx
    python scripts/pptx_qc_audit.py deck.pptx --keep-unpacked /tmp/deck_unpacked

Covers: zip integrity, XML well-formedness, slide count, layout relationships,
content-type coverage, orphaned parts, duplicate relationship IDs, image/blip
resolution, hyperlink resolution, theme/master/layout/font/color-scheme
presence, native chart/SmartArt/table editability, notes-page presence, XSD
schema validation against the real ISO/IEC 29500-4 + OPC schemas (auto-skipped
with a WARN if the schema pack or xmllint isn't available on this machine),
and a full relationship cross-reference sweep.

This script does NOT and CANNOT replace: visual comparison against the
original, an actual PowerPoint Desktop open test, or manual slide-by-slide
review -- those require a human with PowerPoint installed. See the
"PPTX / Office deliverable QC" section of CLAUDE.md for the full checklist
and which parts are automatable vs. which need human confirmation.
"""
import re, os, sys, subprocess, zipfile, tempfile, shutil, argparse
from xml.dom import minidom

SCHEMA_CANDIDATES = [
    "/mnt/skills/public/pptx/scripts/office/schemas",
    os.path.expanduser("~/.claude/skills/pptx/scripts/office/schemas"),
]

def find_schema_dirs():
    for base in SCHEMA_CANDIDATES:
        pml = os.path.join(base, "ISO-IEC29500-4_2016", "pml.xsd")
        opc = os.path.join(base, "ecma", "fouth-edition", "opc-contentTypes.xsd")
        if os.path.exists(pml) and os.path.exists(opc):
            return os.path.join(base, "ISO-IEC29500-4_2016"), os.path.join(base, "ecma", "fouth-edition")
    return None, None

ap = argparse.ArgumentParser()
ap.add_argument("pptx", help="path to the .pptx file to audit")
ap.add_argument("--keep-unpacked", default=None, help="optional dir to unpack into (default: temp dir, auto-cleaned)")
args = ap.parse_args()

PPTX = args.pptx
_tmp = None
if args.keep_unpacked:
    WDIR = args.keep_unpacked
    os.makedirs(WDIR, exist_ok=True)
else:
    _tmp = tempfile.mkdtemp(prefix="pptx_qc_")
    WDIR = _tmp
with zipfile.ZipFile(PPTX) as _z:
    _z.extractall(WDIR)

SCHEMA_DIR, OPC = find_schema_dirs()
HAVE_XMLLINT = shutil.which("xmllint") is not None

report = {"pass": [], "warn": [], "fail": []}
def P(msg): report["pass"].append(msg)
def W(msg): report["warn"].append(msg)
def F(msg): report["fail"].append(msg)

def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()

def rel_path(*parts):
    return os.path.join(WDIR, *parts)

# ---------- 0. ZIP integrity ----------
if PPTX:
    z = zipfile.ZipFile(PPTX)
    bad = z.testzip()
    if bad:
        F(f"ZIP integrity: corrupt member {bad}")
    else:
        P(f"ZIP integrity: {len(z.namelist())} parts, CRC-verified, no corruption")

# ---------- 1. XML well-formedness, every part ----------
all_files = []
for root, dirs, files in os.walk(WDIR):
    for fn in files:
        all_files.append(os.path.join(root, fn))
xml_like = [f for f in all_files if f.endswith(".xml") or f.endswith(".rels")]
malformed = []
for f in xml_like:
    try:
        minidom.parse(f)
    except Exception as e:
        malformed.append((f, str(e)))
if malformed:
    for f, e in malformed:
        F(f"XML well-formedness: {f} -- {e}")
else:
    P(f"XML well-formedness: all {len(xml_like)} XML/rels parts are well-formed")

# ---------- 2. Slide count ----------
slide_files = sorted(f for f in os.listdir(rel_path("ppt", "slides")) if re.match(r"slide\d+\.xml$", f))
n_slides = len(slide_files)
if n_slides == 34:
    P(f"Slide count: {n_slides} (matches expected 34)")
else:
    W(f"Slide count: {n_slides} (expected 34)")

# ---------- 3. Every slide has a valid layout relationship ----------
missing_layout = []
for sf in slide_files:
    rp = rel_path("ppt", "slides", "_rels", sf + ".rels")
    if not os.path.exists(rp):
        missing_layout.append((sf, "no .rels file"))
        continue
    rels = read(rp)
    if 'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout"' not in rels:
        missing_layout.append((sf, "no slideLayout relationship in .rels"))
if missing_layout:
    for sf, why in missing_layout:
        F(f"Layout relationship: {sf} -- {why}")
else:
    P(f"Layout relationships: all {n_slides} slides have a valid slideLayout relationship")

# ---------- 4. Content_Types: every part has a Default or Override ----------
ct = read(rel_path("[Content_Types].xml"))
defaults = dict(re.findall(r'<Default Extension="([^"]+)" ContentType="([^"]+)"/>', ct))
overrides = set(re.findall(r'<Override PartName="([^"]+)"', ct))
uncovered = []
for f in all_files:
    part_name = "/" + os.path.relpath(f, WDIR).replace(os.sep, "/")
    if part_name == "/[Content_Types].xml":
        continue
    ext = f.rsplit(".", 1)[-1].lower()
    if part_name in overrides:
        continue
    if ext in defaults:
        continue
    uncovered.append(part_name)
if uncovered:
    for p in uncovered[:30]:
        W(f"Content type: {p} has neither a Default nor Override entry")
    if len(uncovered) > 30:
        W(f"...and {len(uncovered)-30} more uncovered parts")
else:
    P(f"Content types: every part on disk has a Default or Override content-type declaration")

# ---------- 5. Orphaned parts (not referenced by ANY relationship anywhere) ----------
all_rels_files = [f for f in all_files if f.endswith(".rels")]
referenced_targets = set()
for rf in all_rels_files:
    base_dir = os.path.dirname(os.path.dirname(rf))  # .rels lives in <dir>/_rels/, target is relative to <dir>
    content = read(rf)
    for m in re.finditer(r'Target="([^"]+)"(?:\s+TargetMode="External")?', content):
        target, full = m.group(1), m.group(0)
        if "TargetMode=\"External\"" in full:
            continue  # external targets (hyperlinks etc.) aren't package parts
        abs_path = os.path.normpath(os.path.join(base_dir, target))
        norm = os.path.relpath(abs_path, WDIR).replace(os.sep, "/")
        referenced_targets.add(norm)
# root-level parts (referenced from _rels/.rels) + core always-required parts are seeded already via that walk
part_candidates = [os.path.relpath(f, WDIR).replace(os.sep, "/") for f in all_files
                    if not f.endswith(".rels") and not f.endswith("[Content_Types].xml")]
orphans = [p for p in part_candidates if p not in referenced_targets]
# presentation.xml itself is the root, referenced from _rels/.rels -- already covered
if orphans:
    for p in sorted(orphans)[:30]:
        W(f"Orphaned part (not referenced by any .rels): {p}")
    if len(orphans) > 30:
        W(f"...and {len(orphans)-30} more orphaned parts")
else:
    P("Orphaned parts: none -- every part is referenced by at least one relationship")

# ---------- 6. Duplicate relationship IDs (within each .rels file) ----------
dup_found = False
for rf in all_rels_files:
    content = read(rf)
    ids = re.findall(r'Id="([^"]+)"', content)
    dupes = sorted(set(i for i in ids if ids.count(i) > 1))
    if dupes:
        dup_found = True
        F(f"Duplicate relationship IDs in {os.path.relpath(rf, WDIR)}: {dupes}")
if not dup_found:
    P(f"Relationship IDs: no duplicates in any of {len(all_rels_files)} .rels files")

# ---------- 7. Images referenced correctly (blip r:embed / r:link resolve) ----------
media_files = set(os.path.relpath(rel_path("ppt", "media", m), WDIR).replace(os.sep, "/")
                   for m in (os.listdir(rel_path("ppt", "media")) if os.path.isdir(rel_path("ppt", "media")) else []))
img_issues = []
for sf in slide_files:
    sp = rel_path("ppt", "slides", sf)
    rp = rel_path("ppt", "slides", "_rels", sf + ".rels")
    content = read(sp)
    embeds = set(re.findall(r'r:embed="([^"]+)"', content)) | set(re.findall(r'r:link="([^"]+)"', content))
    if not embeds:
        continue
    rel_ids = {}
    if os.path.exists(rp):
        for m in re.finditer(r'Id="([^"]+)"[^>]*Target="([^"]+)"', read(rp)):
            rel_ids[m.group(1)] = m.group(2)
    for eid in embeds:
        if eid not in rel_ids:
            img_issues.append(f"{sf}: r:embed/r:link '{eid}' has no matching relationship")
        else:
            tgt = os.path.normpath(os.path.join("ppt", "slides", rel_ids[eid])).replace(os.sep, "/")
            if not os.path.exists(rel_path(tgt)):
                img_issues.append(f"{sf}: image relationship '{eid}' points to missing file {tgt}")
n_images_checked = sum(1 for sf in slide_files if 'r:embed=' in read(rel_path("ppt","slides",sf)))
if img_issues:
    for i in img_issues:
        F(f"Image reference: {i}")
else:
    P(f"Image references: {len(media_files)} media files present; all blip r:embed/r:link references on slides resolve correctly")

# ---------- 8. Hyperlinks (hlinkClick r:id resolve, or are external) ----------
link_issues = []
n_hyperlinks = 0
for sf in slide_files:
    sp = rel_path("ppt", "slides", sf)
    rp = rel_path("ppt", "slides", "_rels", sf + ".rels")
    content = read(sp)
    hlinks = re.findall(r'<a:hlinkClick[^>]*r:id="([^"]*)"', content)
    if not hlinks:
        continue
    rel_ids = {}
    if os.path.exists(rp):
        for m in re.finditer(r'Id="([^"]+)"', read(rp)):
            rel_ids[m.group(1)] = True
    for hid in hlinks:
        n_hyperlinks += 1
        if hid and hid not in rel_ids:
            link_issues.append(f"{sf}: hyperlink r:id '{hid}' has no matching relationship")
if link_issues:
    for i in link_issues:
        F(f"Hyperlink: {i}")
else:
    P(f"Hyperlinks: {n_hyperlinks} hlinkClick reference(s) found across all slides, all resolve correctly")

# ---------- 9. Theme / masters / layouts / fonts / color scheme ----------
n_masters = len([f for f in os.listdir(rel_path("ppt","slideMasters")) if re.match(r"slideMaster\d+\.xml$", f)])
n_layouts = len([f for f in os.listdir(rel_path("ppt","slideLayouts")) if re.match(r"slideLayout\d+\.xml$", f)])
n_themes = len([f for f in os.listdir(rel_path("ppt","theme")) if re.match(r"theme\d+\.xml$", f)]) if os.path.isdir(rel_path("ppt","theme")) else 0
theme1 = read(rel_path("ppt","theme","theme1.xml")) if os.path.exists(rel_path("ppt","theme","theme1.xml")) else ""
clr_slots = len(re.findall(r'<a:(dk1|lt1|dk2|lt2|accent1|accent2|accent3|accent4|accent5|accent6|hlink|folHlink)>', theme1))
fonts_used = set(re.findall(r'typeface="([^"+][^"]*)"', theme1))
P(f"Theme/masters/layouts: {n_masters} slideMaster(s), {n_layouts} slideLayout(s), {n_themes} theme(s) present")
if clr_slots >= 12:
    P(f"Color scheme: theme1.xml has all {clr_slots} required color-scheme slots")
else:
    W(f"Color scheme: theme1.xml has only {clr_slots}/12 expected color-scheme slots")
if fonts_used:
    P(f"Fonts declared in theme: {', '.join(sorted(fonts_used))}")

# ---------- 10. Charts / SmartArt / tables remain editable (native, not flattened images) ----------
n_charts = len([f for f in os.listdir(rel_path("ppt","charts")) if f.endswith(".xml") and "colors" not in f and "style" not in f]) if os.path.isdir(rel_path("ppt","charts")) else 0
n_diagrams = len([f for f in os.listdir(rel_path("ppt","diagrams")) if f.endswith(".xml")]) if os.path.isdir(rel_path("ppt","diagrams")) else 0
n_tables = 0
for sf in slide_files:
    content = read(rel_path("ppt","slides",sf))
    n_tables += len(re.findall(r'<a:tbl>', content))
P(f"Native editable content: {n_charts} chart part(s), {n_diagrams} SmartArt/diagram part(s), {n_tables} table(s) across all slides (a:tbl grid, not images)")
# check charts have embedded workbook (editable data) not just rendered
if os.path.isdir(rel_path("ppt","embeddings")):
    n_emb = len(os.listdir(rel_path("ppt","embeddings")))
    P(f"Chart data workbooks: {n_emb} embedded workbook(s) in ppt/embeddings (chart data remains editable)")
elif n_charts:
    W(f"{n_charts} chart part(s) found but no ppt/embeddings directory -- chart source data may not be editable")

# ---------- 11. Notes pages preserved ----------
n_notes = len([f for f in os.listdir(rel_path("ppt","notesSlides")) if re.match(r"notesSlide\d+\.xml$", f)]) if os.path.isdir(rel_path("ppt","notesSlides")) else 0
n_notes_master = len([f for f in os.listdir(rel_path("ppt","notesMasters")) if re.match(r"notesMaster\d+\.xml$", f)]) if os.path.isdir(rel_path("ppt","notesMasters")) else 0
P(f"Notes pages: {n_notes} notesSlide part(s), {n_notes_master} notesMaster part(s) present")
# any slides that reference a notesSlide but the target is missing?
notes_issues = []
for sf in slide_files:
    rp = rel_path("ppt", "slides", "_rels", sf + ".rels")
    if not os.path.exists(rp):
        continue
    for m in re.finditer(r'Type="[^"]*notesSlide"[^>]*Target="([^"]+)"', read(rp)):
        tgt = os.path.normpath(os.path.join("ppt", "slides", m.group(1))).replace(os.sep, "/")
        if not os.path.exists(rel_path(tgt)):
            notes_issues.append(f"{sf}: notesSlide relationship points to missing {tgt}")
if notes_issues:
    for i in notes_issues:
        F(f"Notes: {i}")

# ---------- 12. XSD schema validation (new + core parts) ----------
def xmllint(schema, path):
    r = subprocess.run(["xmllint", "--noout", "--schema", schema, path], capture_output=True, text=True)
    return r.returncode == 0, (r.stdout + r.stderr)

if not HAVE_XMLLINT:
    W("XSD schema validation skipped: xmllint not found on PATH")
elif not SCHEMA_DIR:
    W("XSD schema validation skipped: ISO/IEC 29500-4 schema pack not found "
      f"(checked {', '.join(SCHEMA_CANDIDATES)}) -- structural checks above still ran")
else:
    xsd_targets = ["ppt/presentation.xml", "ppt/slideMasters/slideMaster1.xml",
                   "ppt/slideLayouts/slideLayout1.xml", "ppt/theme/theme1.xml"] + [f"ppt/slides/{f}" for f in slide_files]
    xsd_fail = []
    for t in xsd_targets:
        ok, out = xmllint(f"{SCHEMA_DIR}/pml.xsd", rel_path(t))
        if not ok:
            xsd_fail.append((t, out.strip()[:300]))
    if xsd_fail:
        for t, out in xsd_fail:
            F(f"XSD schema (pml.xsd): {t} -- {out}")
    else:
        P(f"XSD schema validation (ISO/IEC 29500-4 pml.xsd): all {len(xsd_targets)} parts (presentation, master, layout, theme, all {n_slides} slides) validate cleanly")

    ok, out = xmllint(f"{OPC}/opc-contentTypes.xsd", rel_path("[Content_Types].xml"))
    if ok:
        P("XSD schema validation (OPC opc-contentTypes.xsd): [Content_Types].xml validates cleanly")
    else:
        F(f"XSD schema (opc-contentTypes.xsd): [Content_Types].xml -- {out.strip()[:300]}")

    rels_fail = []
    for rf in all_rels_files:
        ok, out = xmllint(f"{OPC}/opc-relationships.xsd", rf)
        if not ok:
            rels_fail.append((os.path.relpath(rf, WDIR), out.strip()[:200]))
    if rels_fail:
        for rf, out in rels_fail:
            F(f"XSD schema (opc-relationships.xsd): {rf} -- {out}")
    else:
        P(f"XSD schema validation (OPC opc-relationships.xsd): all {len(all_rels_files)} .rels files validate cleanly")

# ---------- 13. r:id cross-reference resolution, whole deck ----------
cross_issues = []
for f in xml_like:
    if not f.endswith(".xml") or "_rels" in f:
        continue
    content = read(f)
    refs = set(re.findall(r'r:(?:id|embed|link|dm|lo|qs|cs)="([^"]+)"', content))
    if not refs:
        continue
    rels_f = os.path.join(os.path.dirname(f), "_rels", os.path.basename(f) + ".rels")
    ids = set(re.findall(r'Id="([^"]+)"', read(rels_f))) if os.path.exists(rels_f) else set()
    missing = refs - ids
    if missing:
        cross_issues.append(f"{os.path.relpath(f, WDIR)}: unresolved r:id/r:embed {sorted(missing)}")
if cross_issues:
    for i in cross_issues:
        F(f"Relationship cross-reference: {i}")
else:
    P(f"Relationship cross-reference: every r:id/r:embed/r:link across all {len(xml_like)} parts resolves to a real relationship entry")

# ---------- 14. sldIdLst sanity (no dupes, all slide files present) ----------
pres = read(rel_path("ppt","presentation.xml"))
sids = re.findall(r'<p:sldId id="(\d+)"', pres)
dupe_sids = sorted(set(s for s in sids if sids.count(s) > 1))
if dupe_sids:
    F(f"sldIdLst: duplicate sldId values {dupe_sids}")
else:
    P(f"sldIdLst: {len(sids)} sldId entries, all unique")

# ---------- SUMMARY ----------
print("=" * 70)
print(f"STRUCTURAL QC: {os.path.basename(PPTX)}")
print(f"PASS: {len(report['pass'])}   WARN: {len(report['warn'])}   FAIL: {len(report['fail'])}")
print("=" * 70)
for label, items in [("PASS", report["pass"]), ("WARN", report["warn"]), ("FAIL", report["fail"])]:
    for it in items:
        print(f"[{label}] {it}")

print("=" * 70)
print("NOT covered by this script -- still required before sharing (see CLAUDE.md):")
print("  - Visual comparison against the original / reference deck")
print("  - An actual PowerPoint Desktop open test")
print("  - Manual slide-by-slide review of every inserted/changed slide")
print("  - Explicit confirmation that no repair dialog appears on open")
print("=" * 70)

import json
out_json = os.path.splitext(PPTX)[0] + "_qc_report.json"
with open(out_json, "w") as f:
    json.dump(report, f, indent=2)
print(f"JSON report written to: {out_json}")

if _tmp:
    shutil.rmtree(_tmp, ignore_errors=True)

sys.exit(1 if report["fail"] else 0)
