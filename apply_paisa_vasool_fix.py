"""
Apply Paisa Vasool context corrections across MT_Jul26_Honasa_Final.pptx

Key LY finding:
- Jul-25 national: Primary ₹24.73 Cr | Offtake ₹21.96 Cr | 88.8% conv
- Aug-25 national: Primary ₹21.62 Cr | Offtake ₹24.34 Cr | 112.6% conv (+10.8% MoM offtake)
- Reliance Jul-25 offtake ₹3.04 Cr → Aug-25 ₹4.45 Cr (+46.4% MoM) — Paisa Vasool pipeline draw-down

Slides to update: 4, 7, 9, 16, 18
"""
import os, re, html, zipfile, shutil

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

# ─── SLIDE 4 — Zone scorecard: add Paisa Vasool context to EVIDENCE + ACTION ──
s4 = read(slide_path(4))

s4, n = rpl(s4,
    'MT offtake Jul-26: ₹36.06 Cr (+64.2% YoY vs Jul-25 ₹21.96 Cr); L3M May–Jul ₹114.66 Cr (+65.8% YoY vs ₹69.16 Cr LY); North (58.5% conv, ₹4.97 Cr gap) and East (45.3% conv, ₹4.28 Cr gap) hold 70.5% of national gap',
    'MT offtake Jul-26: ₹36.06 Cr (+64.2% YoY vs Jul-25 ₹21.96 Cr); L3M May–Jul ₹114.66 Cr (+65.8% YoY); LY: Aug-25 offtake rose to ₹24.34 Cr (+10.8% vs Jul-25) at 112.6% conv — Reliance Paisa Vasool event drove pipeline draw-down; same event mid-Aug-26 expected; North + East hold 70.5% of Jul-26 gap'
)
changes.append(f"Slide 4 EVIDENCE — Paisa Vasool LY context: {n} replacements")

s4, n = rpl(s4,
    'Weekly ZSM-owned gap closure loop: North targets Reliance + DMart EANs; East targets Reliance exclusively; report to Sales Lead every Friday from 22-Aug',
    'Validate Reliance Aug-26 offtake in first week (Paisa Vasool effect expected +40% MoM vs Jul, per LY pattern); run weekly ZSM gap closure on DMart and non-Reliance exceptions from 22-Aug; Reliance EAN-store review after Aug read is confirmed'
)
changes.append(f"Slide 4 ACTION — Paisa Vasool sequencing: {n} replacements")

write(slide_path(4), s4)

# ─── SLIDE 7 — North deep-dive: soften "execution failure" for Reliance ───────
s7 = read(slide_path(7))

s7, n = rpl(s7,
    'North gap is a Reliance execution failure, not a demand failure — Apollo 98.3% in the same zone proves demand is present; ₹4.97 Cr gap is recoverable through EAN-level corrections',
    'North Reliance 44.9% partly reflects Paisa Vasool pipeline build (LY: Reliance offtake +46.4% MoM in Aug-25); Apollo 98.3% confirms demand is real; validate Aug-26 Reliance offtake before prescribing full EAN-level correction list'
)
changes.append(f"Slide 7 IMPLICATION — softened execution failure language: {n} replacements")

s7, n = rpl(s7,
    'Pull Reliance North EAN-store pair list; recover top 20 declining items by 05-Sep; use Apollo\'s 98.3% ordering cadence as the Reliance North playbook',
    'Check Reliance North Aug-26 offtake by 05-Aug (Paisa Vasool expected to draw down Jul pipeline); if Aug offtake recovers to >80% conv, hold EAN-store intervention; if not, pull top-20 declining EAN-store pairs and recover by 05-Sep'
)
changes.append(f"Slide 7 ACTION — Paisa Vasool conditional logic: {n} replacements")

s7, n = rpl(s7,
    'North ZSM + NKAM Reliance North | 05-Sep',
    'North ZSM + NKAM Reliance North | Check by 05-Aug; EAN fix by 05-Sep if Aug offtake disappoints'
)
changes.append(f"Slide 7 OWNER — date sequencing: {n} replacements")

write(slide_path(7), s7)

# ─── SLIDE 9 — East deep-dive: Reliance moratorium + Paisa Vasool caveat ──────
s9 = read(slide_path(9))

s9, n = rpl(s9,
    'East 45.3% conversion — worst nationally; ₹7.83 Cr primary vs ₹3.55 Cr offtake; Reliance East 52.9% is the core problem; NPI mix 10.2% is highest nationally',
    'East 45.3% conversion — worst nationally; ₹7.83 Cr primary vs ₹3.55 Cr offtake; Reliance East 52.9% is the core problem; LY: Reliance Aug-25 offtake +46.4% vs Jul-25 (Paisa Vasool) — some East pipeline may convert in Aug-26; NPI mix 10.2% highest nationally is a separate risk'
)
changes.append(f"Slide 9 EVIDENCE — Paisa Vasool LY callout for East Reliance: {n} replacements")

s9, n = rpl(s9,
    'East ZSM to place non-Hero SKU loading moratorium pending August offtake data; Reliance East EAN-store failure list — weekly owner review from 22-Aug',
    'Non-Hero SKU loading moratorium stands — validate Aug-26 Reliance East offtake by 05-Aug before declaring pipeline a failure; if Aug conversion stays below 70%, pull Reliance East EAN-store failure list and run weekly owner review from 05-Aug; Hero-SKU OSA monitoring continues regardless'
)
changes.append(f"Slide 9 ACTION — conditional Paisa Vasool gate: {n} replacements")

s9, n = rpl(s9,
    'East ZSM + NKAM Reliance East | Loading freeze by 22-Aug',
    'East ZSM + NKAM Reliance East | Offtake check 05-Aug; EAN action if Aug disappoints'
)
changes.append(f"Slide 9 OWNER — date updated: {n} replacements")

write(slide_path(9), s9)

# ─── SLIDE 16 — Chain deep-dive: Reliance gap includes Paisa Vasool pipeline ──
s16 = read(slide_path(16))

s16, n = rpl(s16,
    'Apollo\'s 99.7% conversion in the same assortment window proves demand is real — DMart and Reliance gaps are execution deficits; closing 50% adds ~₹5.9 Cr monthly offtake',
    'Apollo 99.7% confirms demand is real. Reliance ₹7.61 Cr gap includes Paisa Vasool pipeline build (LY: Reliance Aug-25 offtake +46.4% vs Jul-25); net Reliance gap after Aug draw-down may be materially smaller — validate before prescribing remedial actions. DMart gap (76.5%) is not event-related and needs intervention now'
)
changes.append(f"Slide 16 IMPLICATION — Paisa Vasool pipeline caveat for Reliance: {n} replacements")

s16, n = rpl(s16,
    'Map Apollo\'s EAN selection and replenishment cadence; present as the DMart and Reliance execution playbook in the 31-Aug account review',
    'Act on DMart gap now (EAN availability + DC-to-store fill, zone by zone); hold Reliance deep-dive until Aug offtake read (Paisa Vasool event expected to partially convert pipeline); present validated net gap in 31-Aug account review'
)
changes.append(f"Slide 16 ACTION — split DMart/Reliance timelines: {n} replacements")

write(slide_path(16), s16)

# ─── SLIDE 18 — 90-day plan: add Paisa Vasool checkpoint ──────────────────────
s18 = read(slide_path(18))

# Update EVIDENCE to note Paisa Vasool context
s18, n = rpl(s18,
    'MT offtake Jul-26: ₹36.06 Cr (+64.2% YoY); L3M May–Jul: ₹114.66 Cr (+65.8% YoY); ₹13.11 Cr national gap at 73.4% conversion (target >90%); North + East hold 70.5% of gap',
    'MT offtake Jul-26: ₹36.06 Cr (+64.2% YoY); L3M May–Jul: ₹114.66 Cr (+65.8% YoY); LY Paisa Vasool: Reliance Aug-25 offtake +46.4% vs Jul — some Jul-26 gap may convert naturally in Aug; validate first-week Aug before full remedial action; ₹13.11 Cr reported gap; North + East hold 70.5%'
)
changes.append(f"Slide 18 EVIDENCE — Paisa Vasool context added: {n} replacements")

s18, n = rpl(s18,
    'Weekly scoreboard live from 22-Aug: North ZSM + East ZSM on gap metrics; KAMs on Hero-SKU OSA; Analytics on data exceptions; no exceptions to owner-date accountability',
    'Paisa Vasool check: validate Reliance Aug-26 offtake by 05-Aug before deploying EAN-store fix list; weekly scoreboard from 22-Aug: North ZSM + East ZSM on post-Paisa-Vasool gap metrics; KAMs on Hero-SKU OSA; Analytics on data exceptions; no exceptions to owner-date accountability'
)
changes.append(f"Slide 18 ACTION — Paisa Vasool first checkpoint: {n} replacements")

write(slide_path(18), s18)

print("Changes applied:")
for c in changes:
    print(f"  ✓ {c}")

# ─── Repack ────────────────────────────────────────────────────────────────────
if os.path.exists(OUT):
    os.remove(OUT)
with zipfile.ZipFile(OUT, 'w', zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(WORK):
        for file in files:
            fp = os.path.join(root, file)
            arcname = os.path.relpath(fp, WORK)
            zf.write(fp, arcname)
print(f"\nPacked: {OUT}")
