"""
Patch dashboard/data.js to correct FY25/FY26 zone allocations for
Madhya Pradesh (North → Central) and Chhattisgarh (West → Central).

Source of truth: the exact FY25/FY26 NSV figures already stored in data.js
under the wrong zone tags. No numbers are fabricated — all are extracted
from existing data.js entries.

Changes made:
  offtake.by_state:
    • Madhya Pradesh → North  [FY25, FY26, FY27 partial] → merged into Central
    • Chhattisgarh   → West   [FY25, FY26, FY27 partial] → merged into Central
  offtake.by_zone:
    • North: −MP FY25/FY26/FY27-partial
    • West:  −CG FY25/FY26/FY27-partial
    • Central: +MP+CG FY25/FY26/FY27-partial, YoY recalculated
"""
import json, re, copy
from pathlib import Path

DATA_JS = Path("dashboard/data.js")

# ── Load ─────────────────────────────────────────────────────────────────────
raw = DATA_JS.read_text()
prefix = "window.DASH = "
json_str = raw[len(prefix):].rstrip().rstrip(";")
data = json.loads(json_str)

o = data["offtake"]

# ── 1. Extract stale North/West rows for MP and CG ───────────────────────────
by_state = o["by_state"]

mp_north = next((r for r in by_state if
                 r.get("state","").lower() == "madhya pradesh" and
                 r.get("zone","").lower() == "north"), None)
cg_west  = next((r for r in by_state if
                 r.get("state","").lower() == "chhattisgarh" and
                 r.get("zone","").lower() == "west"), None)

print("Stale rows found in data.js:")
print("  MP-North:", mp_north)
print("  CG-West :", cg_west)

# Values to migrate
mp_fy25 = mp_north.get("fy25", 0) if mp_north else 0
mp_fy26 = mp_north.get("fy26", 0) if mp_north else 0
mp_fy27_stale = mp_north.get("fy27", 0) if mp_north else 0   # pre-agg FY27 under wrong zone

cg_fy25 = cg_west.get("fy25", 0) if cg_west else 0
cg_fy26 = cg_west.get("fy26", 0) if cg_west else 0
cg_fy27_stale = cg_west.get("fy27", 0) if cg_west else 0

print(f"\nMP  FY25={mp_fy25}, FY26={mp_fy26}, FY27-stale={mp_fy27_stale}")
print(f"CG  FY25={cg_fy25}, FY26={cg_fy26}, FY27-stale={cg_fy27_stale}")

# ── 2. Fix by_state ──────────────────────────────────────────────────────────
# Find the Central MP and CG rows (already have FY27 from offtake-patch)
mp_central = next((r for r in by_state if
                   r.get("state","").lower() == "madhya pradesh" and
                   r.get("zone","").lower() == "central"), None)
cg_central = next((r for r in by_state if
                   r.get("state","").lower() == "chhattisgarh" and
                   r.get("zone","").lower() == "central"), None)

print("\nExisting Central rows:")
print("  MP-Central:", mp_central)
print("  CG-Central:", cg_central)

def _yoy(fy25, fy26):
    if fy25 and fy25 != 0:
        return round((fy26 / fy25 - 1) * 100, 2)
    return None

# Merge FY25/FY26 into the Central entries
if mp_central:
    mp_central["fy25"] = mp_fy25
    mp_central["fy26"] = mp_fy26
    mp_central["fy27"] = round(mp_central.get("fy27", 0) + mp_fy27_stale, 2)
    mp_central["yoy"] = _yoy(mp_fy25, mp_fy26)
    # reorder keys for readability
    mp_central_new = {k: mp_central[k] for k in ["state","zone","fy25","fy26","yoy","fy27"] if k in mp_central}
    by_state[by_state.index(mp_central)] = mp_central_new
    print(f"\nUpdated MP-Central: {mp_central_new}")
else:
    # Create new Central entry
    new_row = {"state": "Madhya Pradesh", "zone": "Central",
               "fy25": mp_fy25, "fy26": mp_fy26,
               "yoy": _yoy(mp_fy25, mp_fy26), "fy27": mp_fy27_stale}
    by_state.append(new_row)
    print(f"\nCreated MP-Central: {new_row}")

if cg_central:
    cg_central["fy25"] = cg_fy25
    cg_central["fy26"] = cg_fy26
    cg_central["fy27"] = round(cg_central.get("fy27", 0) + cg_fy27_stale, 2)
    cg_central["yoy"] = _yoy(cg_fy25, cg_fy26)
    cg_central_new = {k: cg_central[k] for k in ["state","zone","fy25","fy26","yoy","fy27"] if k in cg_central}
    by_state[by_state.index(cg_central)] = cg_central_new
    print(f"Updated CG-Central: {cg_central_new}")
else:
    new_row = {"state": "Chhattisgarh", "zone": "Central",
               "fy25": cg_fy25, "fy26": cg_fy26,
               "yoy": _yoy(cg_fy25, cg_fy26), "fy27": cg_fy27_stale}
    by_state.append(new_row)
    print(f"Created CG-Central: {new_row}")

# Remove stale North/West rows for MP and CG
o["by_state"] = [r for r in by_state if not (
    (r.get("state","").lower() == "madhya pradesh" and r.get("zone","").lower() == "north") or
    (r.get("state","").lower() == "chhattisgarh"   and r.get("zone","").lower() == "west")
)]
print("\nby_state: removed stale MP-North and CG-West rows")
print(f"by_state total rows: {len(o['by_state'])} (was {len(by_state)+2})")

# ── 3. Fix by_zone ────────────────────────────────────────────────────────────
by_zone = o["by_zone"]
print("\nby_zone before fix:")
for r in by_zone:
    print(" ", r)

def _get_zone(name):
    return next((r for r in by_zone if r.get("name","").strip().lower() == name.lower()), None)

zone_north   = _get_zone("North")
zone_west    = _get_zone("West")
zone_central = _get_zone("Central")

# North: subtract MP
if zone_north:
    zone_north["fy25"] = round(zone_north.get("fy25", 0) - mp_fy25, 2)
    zone_north["fy26"] = round(zone_north.get("fy26", 0) - mp_fy26, 2)
    zone_north["fy27"] = round(zone_north.get("fy27", 0) - mp_fy27_stale, 2)
    zone_north["yoy"]  = _yoy(zone_north["fy25"], zone_north["fy26"])

# West: subtract CG
if zone_west:
    zone_west["fy25"] = round(zone_west.get("fy25", 0) - cg_fy25, 2)
    zone_west["fy26"] = round(zone_west.get("fy26", 0) - cg_fy26, 2)
    zone_west["fy27"] = round(zone_west.get("fy27", 0) - cg_fy27_stale, 2)
    zone_west["yoy"]  = _yoy(zone_west["fy25"], zone_west["fy26"])

# Central: add MP + CG
if zone_central:
    zone_central["fy25"] = round(zone_central.get("fy25", 0) + mp_fy25 + cg_fy25, 2)
    zone_central["fy26"] = round(zone_central.get("fy26", 0) + mp_fy26 + cg_fy26, 2)
    zone_central["fy27"] = round(zone_central.get("fy27", 0) + mp_fy27_stale + cg_fy27_stale, 2)
    zone_central["yoy"]  = _yoy(zone_central["fy25"], zone_central["fy26"])
else:
    new_central = {
        "name": "Central",
        "fy25": round(mp_fy25 + cg_fy25, 2),
        "fy26": round(mp_fy26 + cg_fy26, 2),
        "fy27": round(mp_fy27_stale + cg_fy27_stale, 2)
    }
    new_central["yoy"] = _yoy(new_central["fy25"], new_central["fy26"])
    by_zone.append(new_central)

# Sort by_zone descending FY26
o["by_zone"] = sorted(by_zone, key=lambda r: r.get("fy26", 0) or 0, reverse=True)

print("\nby_zone after fix:")
for r in o["by_zone"]:
    print(" ", r)

# ── 4. Save ───────────────────────────────────────────────────────────────────
data["offtake"] = o
updated_json = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
DATA_JS.write_text(prefix + updated_json + ";")
print(f"\nSaved → {DATA_JS}")

# ── 5. QC Summary ─────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("QC SUMMARY — offtake.by_zone (before → after)")
print("="*60)
print(f"{'Zone':<12} {'FY25':>8} {'FY26':>8} {'FY27':>8} {'YoY%':>7}")
print("-"*60)
for r in o["by_zone"]:
    n = r.get("name","?")
    y5 = r.get("fy25","—")
    y6 = r.get("fy26","—")
    y7 = r.get("fy27","—")
    yoy = r.get("yoy","—")
    print(f"{n:<12} {str(y5):>8} {str(y6):>8} {str(y7):>8} {str(yoy):>7}")

print()
print("Central offtake FY25/FY26 now populated:")
print(f"  FY25: {mp_fy25} (MP) + {cg_fy25} (CG) = {mp_fy25+cg_fy25} Lakh")
print(f"  FY26: {mp_fy26} (MP) + {cg_fy26} (CG) = {mp_fy26+cg_fy26} Lakh")
print(f"  FY27: {zone_central.get('fy27','?')} Lakh (4 months Apr–Jul 26)")
print()
print("North adjusted: MP removed from North FY25/FY26")
print("West adjusted:  CG removed from West FY25/FY26")
