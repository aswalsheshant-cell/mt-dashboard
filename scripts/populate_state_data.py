#!/usr/bin/env python3
"""
Populate D.primary.by_state and D.offtake.by_state in dashboard/data.js.

Sources used:
  - PowerBI/SeedData/Primary/Primary_FY202426_10.csv  → real primary NSV by state
  - PowerBI/SeedData/Distribution/UniverseMT.csv       → store counts for offtake allocation
  - D.offtake.by_zone (in data.js)                     → zone-level offtake NSV to distribute

Forecast is intentionally excluded (regional forecast not yet planned).
"""

import csv, json, re, sys
from collections import defaultdict
from pathlib import Path

# ---------------------------------------------------------------------------
# State name canonicalization
# ---------------------------------------------------------------------------
STATE_CANON = {
    "Lucknow-UPE":    "Uttar Pradesh",
    "Lucknow_UPE":    "Uttar Pradesh",
    "UPE":            "Uttar Pradesh",
    "UPW":            "Uttar Pradesh",
    "Northeast-Assam":"Assam",
    "Mumbai":         "Maharashtra",
    "Pune":           "Maharashtra",
    "Chattishgarh":   "Chhattisgarh",
    "Orissa":         "Odisha",
    "Jammu":          "Jammu & Kashmir",
}

# Zone name from CSV/Universe → canonical data.js name
ZONE_CANON = {
    "South-1": "South 1",
    "South-2": "South 2",
    "Central": "Central",
    "East":    "East",
    "North":   "North",
    "West":    "West",
}

FY_MAP = {
    "FY_24-25": "fy25",
    "FY_25-26": "fy26",
    "FY_26-27": "fy27",
}


def canon_state(s: str) -> str:
    return STATE_CANON.get(s.strip(), s.strip())


def canon_zone(z: str) -> str:
    return ZONE_CANON.get(z.strip(), z.strip())


# ---------------------------------------------------------------------------
# Step 1 — Build primary.by_state from Primary CSV
# ---------------------------------------------------------------------------
def build_primary_by_state(csv_path: Path) -> list[dict]:
    """Aggregate Primary NSV (Lakhs) by canonical state × FY."""
    state_fy_nsv: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    state_zone:   dict[str, str] = {}

    with open(csv_path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            fy = FY_MAP.get(row.get("FY", "").strip())
            if not fy:
                continue
            state = canon_state(row.get("State", "").strip())
            zone  = canon_zone(row.get("Zone", "").strip())
            nsv   = float(row.get("NSV", 0) or 0)
            if not state or not zone:
                continue
            state_fy_nsv[state][fy] += nsv
            state_zone[state] = zone  # last-write (same zone per state)

    out = []
    for state, fy_vals in state_fy_nsv.items():
        entry = {
            "state": state,
            "zone":  state_zone.get(state, ""),
            "fy25":  round(fy_vals.get("fy25", 0) / 1e5, 2),
            "fy26":  round(fy_vals.get("fy26", 0) / 1e5, 2),
            "fy27":  round(fy_vals.get("fy27", 0) / 1e5, 2),
        }
        # 'total' = most-recent populated FY for sort key
        entry["total"] = entry["fy27"] or entry["fy26"] or entry["fy25"]
        out.append(entry)

    out.sort(key=lambda d: -d["fy26"])
    return out


# ---------------------------------------------------------------------------
# Step 2 — Build offtake.by_state via zone proportional allocation
# ---------------------------------------------------------------------------
def build_offtake_by_state(universe_path: Path, zone_offtake: list[dict]) -> list[dict]:
    """
    Distribute zone-level offtake NSV to states proportionally by active
    store count in UniverseMT.csv (best available proxy for offtake exposure).
    """
    # Count active stores per (zone, state)
    zone_state_count: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    state_zone: dict[str, str] = {}

    with open(universe_path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("Status", "").strip().lower() != "active":
                continue
            zone  = canon_zone(row.get("Zone", "").strip())
            state = row.get("State", "").strip()
            if zone and state:
                zone_state_count[zone][state] += 1
                state_zone[state] = zone

    # Build zone → {fy25, fy26, fy27} lookup
    zone_nsv: dict[str, dict[str, float]] = {
        z["name"]: {fy: z.get(fy, 0.0) for fy in ("fy25", "fy26", "fy27")}
        for z in zone_offtake
    }

    # Determine dominant zone per state (zone with most stores)
    state_dominant_zone: dict[str, str] = {}
    state_all_zones: dict[str, dict[str, int]] = defaultdict(dict)
    for zone, states in zone_state_count.items():
        for state, count in states.items():
            state_all_zones[state][zone] = count
    for state, zone_counts in state_all_zones.items():
        state_dominant_zone[state] = max(zone_counts, key=zone_counts.get)

    # Allocate proportionally
    state_fy_nsv: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for zone, states in zone_state_count.items():
        total_stores = sum(states.values()) or 1
        for state, count in states.items():
            weight = count / total_stores
            for fy in ("fy25", "fy26", "fy27"):
                zone_val = zone_nsv.get(zone, {}).get(fy, 0.0)
                state_fy_nsv[state][fy] += zone_val * weight

    out = []
    for state, fy_vals in state_fy_nsv.items():
        out.append({
            "state": state,
            "zone":  state_dominant_zone.get(state, state_zone.get(state, "")),
            "fy25":  round(fy_vals.get("fy25", 0), 2),
            "fy26":  round(fy_vals.get("fy26", 0), 2),
            "fy27":  round(fy_vals.get("fy27", 0), 2),
            "total": round(fy_vals.get("fy27", 0) or fy_vals.get("fy26", 0), 2),
        })

    out.sort(key=lambda d: -d["fy26"])
    return out


# ---------------------------------------------------------------------------
# Step 3 — Patch data.js
# ---------------------------------------------------------------------------
def _find_block(text: str, key: str):
    """Return (start, end) of the JSON object at text.find('"key":')."""
    idx = text.find(f'"{key}":')
    if idx == -1:
        return None, None
    start = text.index("{", idx)
    depth, end = 0, start
    for i, ch in enumerate(text[start:], start):
        if ch == "{": depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    return start, end


def patch_by_state(datajs_path: Path, block_key: str, by_state: list[dict]) -> None:
    """Replace the by_state array inside the named top-level DASH block."""
    text = datajs_path.read_text(encoding="utf-8")
    start, end = _find_block(text, block_key)
    if start is None:
        print(f"  ⚠️  Block '{block_key}' not found in data.js")
        return

    obj = json.loads(text[start:end])
    obj["by_state"] = by_state
    new_json = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    text = text[:start] + new_json + text[end:]
    datajs_path.write_text(text, encoding="utf-8")
    print(f"  ✅ {block_key}.by_state → {len(by_state)} states patched")


def main():
    repo = Path("/home/user/mt-dashboard")
    pcsv = repo / "PowerBI/SeedData/Primary/Primary_FY202426_10.csv"
    univ = repo / "PowerBI/SeedData/Distribution/UniverseMT.csv"
    datajs = repo / "dashboard/data.js"

    for p in (pcsv, univ, datajs):
        if not p.exists():
            print(f"❌ Missing: {p}", file=sys.stderr)
            sys.exit(1)

    print("=" * 70)
    print("STATE DATA POPULATION — All Tabs (Forecast excluded)")
    print("=" * 70)

    # ── Primary by_state ───────────────────────────────────────────────────
    print("\n1. Building primary.by_state from Primary CSV...")
    primary_states = build_primary_by_state(pcsv)
    print(f"   {len(primary_states)} states found")
    for s in primary_states[:5]:
        print(f"   {s['state']:25} zone={s['zone']:8} fy26={s['fy26']:>8.2f}L  fy27={s['fy27']:>8.2f}L")

    # ── Offtake by_state (zone proportional) ──────────────────────────────
    print("\n2. Building offtake.by_state via zone proportional allocation...")
    text = datajs.read_text(encoding="utf-8")
    idx = text.find('"offtake":')
    s, e = _find_block(text, "offtake")
    offtake_block = json.loads(text[s:e])
    zone_offtake = offtake_block.get("by_zone", [])

    offtake_states = build_offtake_by_state(univ, zone_offtake)
    print(f"   {len(offtake_states)} states found")
    for s_ in offtake_states[:5]:
        print(f"   {s_['state']:25} zone={s_['zone']:8} fy26={s_['fy26']:>8.2f}L  fy27={s_['fy27']:>8.2f}L")

    # ── Universe by_state (store counts) ──────────────────────────────────
    print("\n3. Building universe.by_state from UniverseMT.csv...")
    universe_states = []
    zone_state_stores_all: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    state_dominant: dict[str, str] = {}
    with open(univ, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("Status", "").strip().lower() != "active":
                continue
            zone  = canon_zone(row.get("Zone", "").strip())
            state = row.get("State", "").strip()
            if zone and state:
                zone_state_stores_all[zone][state] += 1

    # Determine dominant zone per state
    state_all_zones_all: dict[str, dict[str, int]] = defaultdict(dict)
    for zone, states in zone_state_stores_all.items():
        for state, count in states.items():
            state_all_zones_all[state][zone] = count
    for state, zone_counts in state_all_zones_all.items():
        state_dominant[state] = max(zone_counts, key=zone_counts.get)

    for state, zone_counts in state_all_zones_all.items():
        total = sum(zone_counts.values())
        universe_states.append({
            "state": state,
            "zone": state_dominant[state],
            "stores": total,
        })
    universe_states.sort(key=lambda d: -d["stores"])
    print(f"   {len(universe_states)} states with active stores")
    for s in universe_states[:5]:
        print(f"   {s['state']:25} zone={s['zone']:8} stores={s['stores']}")

    # Patch universe.by_state
    text = datajs.read_text(encoding="utf-8")
    s_start, s_end = _find_block(text, "universe")
    if s_start:
        univ_obj = json.loads(text[s_start:s_end])
        univ_obj["by_state"] = universe_states
        text = text[:s_start] + json.dumps(univ_obj, ensure_ascii=False, separators=(",", ":")) + text[s_end:]
        datajs.write_text(text, encoding="utf-8")
        print(f"  ✅ universe.by_state → {len(universe_states)} states patched")

    # ── Patch data.js primary + offtake ───────────────────────────────────
    print("\n4. Patching data.js primary + offtake...")
    patch_by_state(datajs, "primary", primary_states)
    patch_by_state(datajs, "offtake", offtake_states)
    # Forecast intentionally excluded (per user instruction)
    print("   ⏭️  forecast.by_state — skipped (regional forecast not yet planned)")

    print()
    print("=" * 70)
    print("✅ STATE DATA POPULATION COMPLETE")
    print(f"   primary.by_state:  {len(primary_states)} states  (real primary NSV)")
    print(f"   offtake.by_state:  {len(offtake_states)} states  (zone proportional allocation)")
    print(f"   universe.by_state: {len(universe_states)} states  (active store counts)")
    print("=" * 70)


if __name__ == "__main__":
    main()
