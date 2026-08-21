"""
Add validated FYTD Reliance primary (Apr–Jul 26 = ₹47.53 Cr) to slide 16.
Source: data.js → detail_meta.fyx_primary.FY27.by_chain → Reliance Retail = 4752.93L
"""
import os, re, html, zipfile

BASE = '/home/user/mt-dashboard'
WORK = f'{BASE}/tpl_enriched'
OUT  = f'{BASE}/MT_Jul26_Honasa_Final.pptx'

def esc(t):
    return html.escape(t, quote=False)

def rpl(xml, old, new):
    pat = re.compile(r'(<a:t[^>]*>)' + re.escape(old) + r'(</a:t>)', re.DOTALL)
    count = len(pat.findall(xml))
    result = pat.sub(lambda m: m.group(1) + esc(new) + m.group(2), xml)
    return result, count

def slide_path(n):
    return f'{WORK}/ppt/slides/slide{n}.xml'

def read(p):
    with open(p, encoding='utf-8') as f:
        return f.read()

def write(p, c):
    with open(p, 'w', encoding='utf-8') as f:
        f.write(c)

changes = []

# ─── SLIDE 16 — Add FYTD Reliance primary context to EVIDENCE ────────────────
s16 = read(slide_path(16))

# Update EVIDENCE to add FYTD primary for Reliance (Apr–Jul 26 = ₹47.53 Cr)
s16, n = rpl(s16,
    'DMart ₹4.29 Cr gap (76.5% conv); Reliance ₹7.61 Cr gap (51.4% conv); Apollo ₹0.02 Cr gap (99.7% conv); two chains account for 90.7% of national gap',
    'DMart ₹4.29 Cr gap (76.5% conv); Reliance ₹7.61 Cr gap (51.4% conv); Apollo ₹0.02 Cr gap (99.7% conv); two chains = 90.7% of gap; Reliance FYTD primary Apr–Jul 26: ₹47.53 Cr (₹15.66 Cr in Jul alone)'
)
changes.append(f'Slide 16 EVIDENCE — FYTD Reliance primary added: {n} replacements')

write(slide_path(16), s16)

print("Changes applied:")
for c in changes:
    print(f"  ✓ {c}")

# ─── Repack ──────────────────────────────────────────────────────────────────
if os.path.exists(OUT):
    os.remove(OUT)
with zipfile.ZipFile(OUT, 'w', zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(WORK):
        for file in files:
            fp = os.path.join(root, file)
            arcname = os.path.relpath(fp, WORK)
            zf.write(fp, arcname)
print(f"\nPacked: {OUT}")
