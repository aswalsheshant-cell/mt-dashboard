"""
Enrich template_ref.pptx:
- Replace every EVIDENCE|IMPLICATION|ACTION|OWNER placeholder with real diagnostic content
- Repack to MT_Jul26_Honasa_Enriched.pptx
"""

import os, re, shutil, zipfile, html

# --- Diagnostic content per slide (slide number → dict) -----------------------
CONTENT = {
    2: {
        "What moved": "5 validated growth levers are live; SAH / WD / PDO / OOS fields not yet field-reconciled for July",
        "Why it matters": "Decisions without field reconciliation treat stock-timing noise as demand signal and risk driving wrong actions",
        "What changes now": "Reconcile SAH, WD and OOS for August cycle; add PDO by state-chain; publish validated diagnostic by 31-Aug",
        "Who closes it": "Analytics | 31-Aug",
    },
    3: {
        "What moved": "ME Face Wash +3.1 pp YoY to 10.5% share (#4 nationally); Shampoo +1.2 pp to 3.7%; June Nielsen RMS confirms demand pull",
        "Why it matters": "Shampoo at +80.3% L3M is the fastest-growing segment — delay in expanding controlled pack pilots cedes early-mover advantage to competitors",
        "What changes now": "Run controlled Shampoo pack pilots (top 3 formats) in DMart and Apollo; protect Face Wash hero EAN availability above 95% in top-100 stores",
        "Who closes it": "Category + NKAM DMart / Apollo | Pilots by 15-Sep",
    },
    4: {
        "What moved": "North (58.5% conv, ₹4.97 Cr gap) and East (45.3% conv, ₹4.28 Cr gap) together hold 70.5% of national gap",
        "Why it matters": "West and South-1 are self-sustaining at 82-84% conversion; concentrating intervention on North and East yields the highest recovery per rupee of resource",
        "What changes now": "Weekly ZSM-owned gap closure loop: North targets Reliance + DMart EANs; East targets Reliance exclusively; report to Sales Lead every Friday from 22-Aug",
        "Who closes it": "North ZSM + East ZSM | Weekly from 22-Aug",
    },
    5: {
        "What moved": "West ₹8.28 Cr at 82.3% conversion; DMart West 94.2% is the best DMart rate nationally; Reliance West 54.5% is the only exception; Wellness Forever 134.9% is a timing signal",
        "Why it matters": "DMart West's 94.2% conversion proves EAN availability discipline works; Reliance West has 45% of billed inventory not selling through — recoverable with store-level action",
        "What changes now": "NKAM to map Reliance West EAN-store failures; restore top-10 declining articles by 30-Aug; hold Wellness Forever loading until timing discrepancy is explained",
        "Who closes it": "NKAM Reliance West + NKAM Wellness | 30-Aug",
    },
    6: {
        "What moved": "S-1 ₹8.19 Cr at 83.6% conversion; Apollo ₹2.84 Cr at 81.0% is the only exception; TDC Face Cleanser growing from ₹0.73 Cr (Feb) to ₹1.18 Cr (Jul)",
        "Why it matters": "Karnataka anchors 50.1% of zone value — losing it hurts more than gaining Tamil Nadu; Apollo's conversion dip is 3 pp below its national benchmark",
        "What changes now": "Apollo NKAM to fix top-5 declining EAN-store pairs in Karnataka; maintain TDC Face Cleanser OSA which underpins zone conversion",
        "Who closes it": "NKAM Apollo S-1 | 28-Aug",
    },
    7: {
        "What moved": "North ₹11.95 Cr primary vs ₹6.99 Cr offtake; 58.5% conversion; Reliance North 44.9% is the most critical account nationally; Apollo North 98.3% is the exception",
        "Why it matters": "North gap is a Reliance execution failure, not a demand failure — Apollo 98.3% in the same zone proves demand is present; ₹4.97 Cr gap is recoverable through EAN-level corrections",
        "What changes now": "Pull Reliance North EAN-store pair list; recover top 20 declining items by 05-Sep; use Apollo's 98.3% ordering cadence as the Reliance North playbook",
        "Who closes it": "North ZSM + NKAM Reliance North | 05-Sep",
    },
    8: {
        "What moved": "S-2 ₹6.89 Cr primary vs ₹4.91 Cr offtake; DMart S-2 at 45.1% is the lowest DMart conversion nationally; Apollo S-2 at 148.5% signals overbilling",
        "Why it matters": "DMart S-2 is the highest-value DMart recovery opportunity nationally; Apollo's >100% rate is a data risk — treating it as a success signal would justify loading into an already full pipe",
        "What changes now": "DMart NKAM to run S-2 store-level audit by 28-Aug; quarantine Apollo S-2 primary comparison until opening stock is reconciled; freeze new Apollo S-2 loading",
        "Who closes it": "NKAM DMart S-2 + Analytics | 28-Aug",
    },
    9: {
        "What moved": "East 45.3% conversion — worst nationally; ₹7.83 Cr primary vs ₹3.55 Cr offtake; Reliance East 52.9% is the core problem; NPI mix 10.2% is highest nationally",
        "Why it matters": "East is over-loaded relative to demonstrated demand; 10.2% NPI mix risks inventory buildup if sellthrough is not confirmed before the next primary cycle",
        "What changes now": "East ZSM to place non-Hero SKU loading moratorium pending August offtake data; Reliance East EAN-store failure list — weekly owner review from 22-Aug",
        "Who closes it": "East ZSM + NKAM Reliance East | Loading freeze by 22-Aug",
    },
    10: {
        "What moved": "Central ₹2.12 Cr at 78.8% conversion; DMart Central 95.3% is the best DMart rate nationally; zone data available from July only (first billing month)",
        "Why it matters": "Central is a clean new zone — protecting its high conversion from day one avoids the pipeline problems North and East are correcting at significant cost",
        "What changes now": "Document Central DMart's EAN availability and ordering cadence as the national DMart benchmark; build state-level comparable data from August",
        "Who closes it": "NKAM DMart + Analytics | Framework by 31-Aug",
    },
    11: {
        "What moved": "FSN / Nykaa ₹2.07 Cr at 99.4% flow; -4.6% MoM from June ₹2.17 Cr; EAN count 198 (from 222 in January); 7-month absolute trend is positive",
        "Why it matters": "July's decline is article-mix softness, not account deterioration; declining EAN count while value holds means portfolio productivity per EAN is improving",
        "What changes now": "Protect top-8 face-wash and sunscreen articles (₹1.41 Cr combined); do not add new EANs until July sellthrough is validated in the August read",
        "Who closes it": "NKAM FSN / Nykaa + Category | 30-Aug",
    },
    12: {
        "What moved": "Lulu +46.5%, VMM +18.2%, Sasta Sundar +127.8% are growth engines; Reliance -15.0%, Metro -20.5%, Arambagh -22.5% need urgent recovery",
        "Why it matters": "Scale and recovery chains need different resources; diverting Lulu / VMM attention to fix Reliance risks losing growth momentum in the accounts that are working",
        "What changes now": "Parallel owner loops: Reliance / Metro / Arambagh on weekly exception EAN lists; Lulu / VMM on availability protection briefs; no cross-assignment",
        "Who closes it": "Sales Lead (owner assignment per chain) | By 25-Aug",
    },
    13: {
        "What moved": "Three urgent recovery chains (Reliance -15%, Metro -20.5%, Arambagh -22.5%); three scale chains (Lulu +46.5%, VMM +18.2%, Sasta Sundar +127.8%); each has a distinct root cause",
        "Why it matters": "Mix erosion (Reliance), range dilution (Metro), expansion execution (VMM), seasonal concentration (Wellness) — one intervention does not work across all; wrong diagnosis wastes three months",
        "What changes now": "Each recovery chain gets a named owner and chain-specific KPI; scale chains get availability protection brief; 30-day convergence review for all nine chains",
        "Who closes it": "Sales Lead + Category (KPI design) | Owner assignment by 25-Aug",
    },
    14: {
        "What moved": "July ₹2.07 Cr vs June ₹2.17 Cr (-4.6%); 7-month trend Jan ₹1.64 Cr → Jul ₹2.07 Cr; Rice FW 100ml is top article at ₹0.27 Cr; 99.4% flow maintained throughout",
        "Why it matters": "The -4.6% MoM is article-level, not account-level; top 2 articles — Rice FW 100ml + 50ml combined ₹0.46 Cr — directly determine whether August recovers",
        "What changes now": "Raise OSA target for Rice FW 100ml and Ubtan FW to 100% on Nykaa; review article-level sellthrough in Nykaa SS before September reorder decision",
        "Who closes it": "NKAM FSN / Nykaa + Supply | 30-Aug",
    },
    15: {
        "What moved": "₹2.82 Cr NPI, 7.82% mix, 58/60 EANs billing; East leads NPI mix at 10.2%; zero-sellers: BBLUNT Cherry Red Hair Colour 130g + TDC Peptide Stem Cell Hair Serum",
        "Why it matters": "2 zero-sellers represent an active listing / OSA risk; left unresolved past August review they become dead NPI inventory — early action is cheaper than post-launch recovery",
        "What changes now": "Audit both zero-sellers: confirm store receipt, shelf visibility and scheme support by 28-Aug; no further NPI loading in same categories until these clear",
        "Who closes it": "Trade Marketing + Supply | 28-Aug",
    },
    16: {
        "What moved": "DMart ₹4.29 Cr gap (76.5% conv); Reliance ₹7.61 Cr gap (51.4% conv); Apollo ₹0.02 Cr gap (99.7% conv); two chains account for 90.7% of national gap",
        "Why it matters": "Apollo's 99.7% conversion in the same assortment window proves demand is real — DMart and Reliance gaps are execution deficits; closing 50% adds ~₹5.9 Cr monthly offtake",
        "What changes now": "Map Apollo's EAN selection and replenishment cadence; present as the DMart and Reliance execution playbook in the 31-Aug account review",
        "Who closes it": "Sales Lead + Category | Apollo audit by 31-Aug",
    },
    17: {
        "What moved": "ME ₹24.49 Cr at 73.4% conv; TDC ₹11.03 Cr at 72.6% conv; Aqualogica ₹0.48 Cr at 117% (timing effect); BBlunt ₹0.06 Cr at 35.2% conv",
        "Why it matters": "ME and TDC have nearly identical conversion — the same chain-zone-EAN fix applies to both brands simultaneously; BBlunt 35.2% is structural underperformance requiring a primary hold",
        "What changes now": "Hold BBlunt primary until offtake confirms store-level demand; reconcile Aqualogica opening stock before September load; apply chain-zone-EAN exception fix to TDC in parallel with ME",
        "Who closes it": "Category (BBlunt, Aqualogica) + Supply | By 31-Aug",
    },
    18: {
        "What moved": "₹13.11 Cr national gap; 73.4% conversion vs >90% target; North + East hold 70.5% of gap requiring week-by-week owner accountability",
        "Why it matters": "The 90-day plan is sequential — reconciliation (phase 1) validates white-space sizing (phase 2), which de-risks scaling (phase 3); skipping phase 1 invalidates everything after it",
        "What changes now": "Weekly scoreboard live from 22-Aug: North ZSM + East ZSM on gap metrics; KAMs on Hero-SKU OSA; Analytics on data exceptions; no exceptions to owner-date accountability",
        "Who closes it": "Sales Lead (weekly chair) | First review 22-Aug",
    },
    19: {
        "What moved": "31,355 / 197,740 primary-offtake rows reconciled; 0 missing zone rows; period July 2026; SAH / WD / PDO / OOS not yet field-reconciled",
        "Why it matters": "Data coverage is sufficient for chain × zone × brand decisions; article-level causal conclusions need SAH / WD / OOS — acting without them risks wrong root-cause assignments",
        "What changes now": "Publish reconciled SAH / WD fields by 31-Aug; every consequential commercial change requires named human approval before execution",
        "Who closes it": "Analytics | 31-Aug",
    },
}

# --------------------------------------------------------------------------

def escape(t):
    return html.escape(t, quote=False)

def replace_in_xml(xml_str, old, new):
    """Replace text content inside <a:t>...</a:t> tags, preserving XML structure."""
    # Match the exact text node — use regex to find the <a:t> containing old text
    pattern = re.compile(
        r'(<a:t[^>]*>)' + re.escape(old) + r'(</a:t>)',
        re.DOTALL
    )
    return pattern.sub(lambda m: m.group(1) + escape(new) + m.group(2), xml_str)


def process_slide(slide_num, content):
    path = f'tpl_unpacked/ppt/slides/slide{slide_num}.xml'
    with open(path, 'r', encoding='utf-8') as f:
        xml = f.read()

    orig_xml = xml
    mapping = {
        "What moved": content["What moved"],
        "Why it matters": content["Why it matters"],
        "What changes now": content["What changes now"],
        "Who closes it": content["Who closes it"],
    }
    for old, new in mapping.items():
        xml = replace_in_xml(xml, old, new)

    changed = sum(1 for k in mapping if k not in xml)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(xml)
    return changed


print("Processing slides...")
for slide_num, content in CONTENT.items():
    changed = process_slide(slide_num, content)
    print(f"  slide{slide_num}.xml — {4 - changed} of 4 placeholders replaced")  # invert logic

# Verify
print("\nVerifying placeholders replaced...")
for slide_num in CONTENT:
    path = f'tpl_unpacked/ppt/slides/slide{slide_num}.xml'
    with open(path) as f:
        xml = f.read()
    remaining = [t for t in ["What moved","Why it matters","What changes now","Who closes it"] if t in xml]
    if remaining:
        print(f"  WARNING slide{slide_num}: still has {remaining}")
    else:
        print(f"  slide{slide_num}: CLEAN")

# Repack
out = 'MT_Jul26_Honasa_Enriched.pptx'
if os.path.exists(out):
    os.remove(out)
with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk('tpl_unpacked'):
        for file in files:
            fp = os.path.join(root, file)
            arcname = os.path.relpath(fp, 'tpl_unpacked')
            zf.write(fp, arcname)

print(f"\nDone: {out}")
