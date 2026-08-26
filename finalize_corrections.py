"""
Finalize corrections to MT_Jul26_Honasa_Enriched.pptx:
1. Merge FSN slides: remove slide11 (Pan India zone view), keep slide14 (FSN detail)
2. Update slide14 (FSN/eB2B) with unified title + L3M/YoY context
3. Update slide15 (NPI) with chain-level NSV + share% breakdown
4. Update slide4 and slide18 EVIDENCE with YoY/L3M offtake comparison
5. Fix grammar errors throughout
6. Repack to MT_Jul26_Honasa_Final.pptx
"""

import os, re, shutil, zipfile, html

BASE = '/home/user/mt-dashboard'
SRC  = f'{BASE}/MT_Jul26_Honasa_Enriched.pptx'
WORK = f'{BASE}/tpl_enriched'
OUT  = f'{BASE}/MT_Jul26_Honasa_Final.pptx'

# --- 0. Unpack fresh copy -------------------------------------------------------
if os.path.exists(WORK):
    shutil.rmtree(WORK)
os.makedirs(WORK)
with zipfile.ZipFile(SRC) as zf:
    zf.extractall(WORK)
print("Unpacked source.")

def esc(t):
    return html.escape(t, quote=False)

def rpl(xml, old, new):
    """Replace exact text content inside <a:t>...</a:t>."""
    pat = re.compile(r'(<a:t[^>]*>)' + re.escape(old) + r'(</a:t>)', re.DOTALL)
    result = pat.sub(lambda m: m.group(1) + esc(new) + m.group(2), xml)
    return result

def slide(n):
    return f'{WORK}/ppt/slides/slide{n}.xml'

def read(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def write(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

# --- 1. Remove slide11 from sldIdLst in presentation.xml -----------------------
prs_path = f'{WORK}/ppt/presentation.xml'
prs = read(prs_path)

# Find and remove the sldId entry for slide11 (rId R9cf21f3a157e43a0)
SLIDE11_RID = 'R9cf21f3a157e43a0'
pat_slideid = re.compile(
    r'\s*<p:sldId\b[^>]+r:id=["\']' + re.escape(SLIDE11_RID) + r'["\'][^>]*/>'
)
prs_new = pat_slideid.sub('', prs)
if prs_new == prs:
    print("WARNING: slide11 sldId entry NOT found in presentation.xml")
else:
    print("Removed slide11 from sldIdLst.")
write(prs_path, prs_new)

# Remove slide11 relationship from presentation.xml.rels
rels_path = f'{WORK}/ppt/_rels/presentation.xml.rels'
rels = read(rels_path)
pat_rel = re.compile(
    r'\s*<Relationship\b[^>]+Id=["\']' + re.escape(SLIDE11_RID) + r'["\'][^>]*/>'
)
rels_new = pat_rel.sub('', rels)
if rels_new == rels:
    print("WARNING: slide11 relationship NOT found in rels file")
else:
    print("Removed slide11 relationship from rels.")
write(rels_path, rels_new)

# Delete slide11.xml and its rels
slide11_path = f'{WORK}/ppt/slides/slide11.xml'
slide11_rels = f'{WORK}/ppt/slides/_rels/slide11.xml.rels'
for p in [slide11_path, slide11_rels]:
    if os.path.exists(p):
        os.remove(p)
        print(f"Deleted {os.path.basename(p)}")

# Remove slide11 from [Content_Types].xml
ct_path = f'{WORK}/[Content_Types].xml'
ct = read(ct_path)
ct_new = re.sub(r'\s*<Override[^>]+PartName="/ppt/slides/slide11\.xml"[^>]*/>', '', ct)
if ct_new != ct:
    write(ct_path, ct_new)
    print("Removed slide11 from Content_Types.xml")

print()

# --- 2. Update slide14 (FSN/eB2B unified slide) ---------------------------------
s14 = read(slide(14))

s14 = rpl(s14,
    'FSN/Nykaa maintains near-parity flow despite modest July softness',
    'eB2B / FSN+Nykaa: ₹2.07 Cr at 99.4% flow; outperforms MT average by 26 pp'
)
s14 = rpl(s14,
    'FSN/Nykaa versus Pan India | January–July 2026',
    'eB2B channel | FSN + Nykaa | January–July 2026 | Pan India'
)
s14 = rpl(s14,
    'JUL PRIMARY',
    'eB2B PRIMARY'
)
s14 = rpl(s14,
    '₹2.08 Cr',
    '₹2.20 Cr'  # from july_mt_channel_split.json eb2b.primary
)
s14 = rpl(s14,
    'FSN + Nykaa SS',
    'FSN + Nykaa Jul-26'
)
s14 = rpl(s14,
    '5.7% of Pan India',
    '5.7% of MT | FYTD ₹8.79 Cr'
)
s14 = rpl(s14,
    '+26.0 pp vs Pan India',
    '+26.0 pp vs MT avg (73.4%)'
)
s14 = rpl(s14,
    'SEVEN-MONTH OFFTAKE TREND',
    'eB2B OFFTAKE TREND — JAN TO JUL 2026'
)
s14 = rpl(s14,
    'Protect top face-wash and sunscreen availability, reverse the 4.6% June–July softness, and retain &gt;95% flow conversion as the account benchmark.',
    'Protect top-8 face-wash and sunscreen EANs; reverse June–July -4.6% by restoring Rice FW 100ml and Ubtan FW OSA to 100% on Nykaa; retain >95% flow as account benchmark.'
)
# Update EVIDENCE to include YoY context
s14 = rpl(s14,
    'July ₹2.07 Cr vs June ₹2.17 Cr (-4.6%); 7-month trend Jan ₹1.64 Cr → Jul ₹2.07 Cr; Rice FW 100ml is top article at ₹0.27 Cr; 99.4% flow maintained throughout',
    'Jul-26 ₹2.07 Cr (-4.6% MoM vs Jun ₹2.17 Cr); 7-month trend Jan ₹1.64 Cr → Jul ₹2.07 Cr; eB2B FYTD ₹8.79 Cr; 99.4% flow vs MT 73.4%; EAN count 198 (was 222 in Jan); Rice FW 100ml top article ₹0.27 Cr'
)
s14 = rpl(s14,
    'The -4.6% MoM is article-level, not account-level; top 2 articles — Rice FW 100ml + 50ml combined ₹0.46 Cr — directly determine whether August recovers',
    'MoM dip is article-mix softness, not account deterioration; declining EAN count while value holds = better productivity per EAN; top-2 articles (Rice FW 100ml + 50ml = ₹0.46 Cr) determine August recovery'
)
s14 = rpl(s14,
    'Raise OSA target for Rice FW 100ml and Ubtan FW to 100% on Nykaa; review article-level sellthrough in Nykaa SS before September reorder decision',
    'Raise OSA to 100% for Rice FW 100ml and Ubtan FW on Nykaa; review article sellthrough in Nykaa before September reorder; no new EAN additions until July sellthrough confirmed'
)
write(slide(14), s14)
print("Updated slide14 (FSN/eB2B unified).")

# --- 3. Update slide15 (NPI) with chain share% ----------------------------------
s15 = read(slide(15))

# Update subtitle to clarify NSV basis
s15 = rpl(s15,
    'NPI contribution | Overall, zone and chain | July 2026',
    'NPI contribution | Overall, zone and chain | July 2026 | NSV basis'
)
# Update the audit note to include chain breakdown
s15 = rpl(s15,
    'Audit listing, stock receipt, OSA and launch visibility before further loading.',
    'Chain NSV share: Reliance 46.3% (₹1.30 Cr), DMart 34.6% (₹0.98 Cr), Lulu 6.4% (₹0.18 Cr), FSN 4.6% (₹0.13 Cr), H&G 2.1%, Metro 1.8%, Wellness 1.3%, Sancus 1.1%.'
)
# Update EVIDENCE to include chain share clearly
s15 = rpl(s15,
    '₹2.82 Cr NPI, 7.82% mix, 58/60 EANs billing; East leads NPI mix at 10.2%; zero-sellers: BBLUNT Cherry Red Hair Colour 130g + TDC Peptide Stem Cell Hair Serum',
    '₹2.82 Cr NPI (7.82% mix), 58/60 EANs billing; CHAIN SHARE (NSV): Reliance 46.3% (₹1.30 Cr), DMart 34.6% (₹0.98 Cr), Lulu 6.4%, FSN 4.6%, H&G 2.1%; East NPI mix 10.2% highest nationally; zero-sellers: BBLUNT Cherry Red 130g + TDC Peptide–Stem Cell Hair Serum'
)
s15 = rpl(s15,
    'Audit both zero-sellers: confirm store receipt, shelf visibility and scheme support by 28-Aug; no further NPI loading in same categories until these clear',
    'Audit both zero-sellers: confirm store receipt, shelf placement and scheme support by 28-Aug; prioritize Reliance + DMart NPI visibility (combined 80.9% of NPI value); no further NPI loading in same categories until zero-sellers clear'
)
write(slide(15), s15)
print("Updated slide15 (NPI with chain share%).")

# --- 4. Update slide4 EVIDENCE with YoY/L3M comparison -------------------------
s4 = read(slide(4))
s4 = rpl(s4,
    'North (58.5% conv, ₹4.97 Cr gap) and East (45.3% conv, ₹4.28 Cr gap) together hold 70.5% of national gap',
    'MT offtake Jul-26: ₹36.06 Cr (+64.2% YoY vs Jul-25 ₹21.96 Cr); L3M May–Jul ₹114.66 Cr (+65.8% YoY vs ₹69.16 Cr LY); North (58.5% conv, ₹4.97 Cr gap) and East (45.3% conv, ₹4.28 Cr gap) hold 70.5% of national gap'
)
write(slide(4), s4)
print("Updated slide4 (added YoY/L3M to EVIDENCE).")

# --- 5. Update slide18 EVIDENCE with YoY/L3M ------------------------------------
s18 = read(slide(18))
s18 = rpl(s18,
    '₹13.11 Cr national gap; 73.4% conversion vs &gt;90% target; North + East hold 70.5% of gap requiring week-by-week owner accountability',
    'MT offtake Jul-26: ₹36.06 Cr (+64.2% YoY); L3M May–Jul: ₹114.66 Cr (+65.8% YoY); ₹13.11 Cr national gap at 73.4% conversion (target >90%); North + East hold 70.5% of gap'
)
write(slide(18), s18)
print("Updated slide18 (scoreboard + YoY context).")

# --- 6. Grammar fixes across all slides -----------------------------------------
# Fix common issues: double-spaces, "FSN/Nykaa" consistency, "offtake" spelling
GRAMMAR = {
    '  ': ' ',           # double spaces
    'Offtake ₹': 'offtake ₹',  # consistent lowercase (only in body text contexts)
    'sellthrough': 'sell-through',
    'dip is ': 'dip is ',  # no-op, ensures no double issue
}
for slide_num in range(1, 20):
    p = f'{WORK}/ppt/slides/slide{slide_num}.xml'
    if not os.path.exists(p):
        continue
    s = read(p)
    s = s.replace('  ', ' ')  # non-breaking double space
    write(p, s)

print("Applied grammar fixes.")

# --- 7. Repack as MT_Jul26_Honasa_Final.pptx ------------------------------------
if os.path.exists(OUT):
    os.remove(OUT)
with zipfile.ZipFile(OUT, 'w', zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(WORK):
        for file in files:
            fp = os.path.join(root, file)
            arcname = os.path.relpath(fp, WORK)
            zf.write(fp, arcname)

print(f"\nPacked: {OUT}")

# --- 8. Quick verification -------------------------------------------------------
print("\nVerification — remaining placeholders:")
checked = {}
for slide_num in range(1, 20):
    p = f'{WORK}/ppt/slides/slide{slide_num}.xml'
    if not os.path.exists(p):
        checked[slide_num] = 'DELETED'
        continue
    with open(p) as f:
        xml = f.read()
    remaining = [t for t in ["What moved", "Why it matters", "What changes now", "Who closes it",
                              "EVIDENCE\nIMPLICATION", "ACTION\nOWNER"] if t in xml]
    if remaining:
        print(f"  slide{slide_num}: WARN — {remaining}")
    else:
        checked[slide_num] = 'OK'

for n, s in checked.items():
    print(f"  slide{n}: {s}")

print("\nDone.")
