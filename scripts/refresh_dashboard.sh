#!/usr/bin/env bash
# One-command dashboard data refresh — triggered when raw monthly files land in data/raw_drops/
# Usage: ./scripts/refresh_dashboard.sh
#
# Ingest model: PARTIAL PATCH CHAIN (not a full rebuild).
#   A full rebuild needs every source workbook in --src (Primary, Offtake, P&L,
#   Universe, Promo). The monthly drop is only Primary + Offtake, so a full
#   rebuild would run without the others. The partial modes below mutate only
#   their own blocks and leave P&L / Universe / Promo / detail_records intact.

set -e

echo ""
echo "=========================================="
echo "MT Dashboard v1.1.2 — Data Refresh"
echo "=========================================="
echo ""

# Step 0: Validate raw drops folder exists
if [ ! -d "data/raw_drops" ]; then
    echo "❌ Error: data/raw_drops/ not found."
    echo "   Place your monthly source files here first:"
    echo "   - Primary_FY202426_*.xlsx"
    echo "   - Offtake pivot .xlsx/.xlsb"
    echo "   - Universe/mapping files (if updating)"
    exit 1
fi

echo "✓ Ingestion folder found: data/raw_drops/"
ls -lh data/raw_drops/ | tail -n +2 | awk '{print "  ", $9, "(" $5 ")"}'

# ---------------------------------------------------------------------------
# Helpers — all read data.js line-by-line. The file is ~42 MB; never load it
# whole (that is what was OOM-killing agent containers).
# ---------------------------------------------------------------------------
count_detail_records() {
    local START END
    START=$(grep -n '^ "detail_records": \[' dashboard/data.js | cut -d: -f1)
    [ -z "$START" ] && { echo 0; return; }
    END=$(awk -v s="$START" 'NR>s && /^ "[A-Za-z_]+":/ {print NR; exit}' dashboard/data.js)
    [ -z "$END" ] && END=$(wc -l < dashboard/data.js)
    awk -v s="$START" -v e="$END" 'NR>s && NR<e && /^  \{$/ {c++} END {print c+0}' dashboard/data.js
}

primary_totals() {
    # Both nsv_fyNN keys live only in the primary block, so a plain grep is a
    # safe snapshot and costs nothing.
    grep -o '"nsv_fy[0-9]*": [0-9.]*' dashboard/data.js 2>/dev/null | tr '\n' ' '
}

# Snapshot pre-refresh state so we can prove the partial passes preserved it
# (detail_records) and that they actually ingested something (primary totals).
if [ -f "dashboard/data.js" ]; then
    DETAIL_BEFORE=$(count_detail_records)
    PRIMARY_BEFORE=$(primary_totals)
else
    DETAIL_BEFORE=0
    PRIMARY_BEFORE=""
fi
echo "  detail_records before refresh: $DETAIL_BEFORE"
echo "  primary totals before refresh: ${PRIMARY_BEFORE:-none}"

# Did the operator actually stage a Primary file? Used below to tell a genuine
# no-op ("nothing dropped") apart from a silent one ("dropped but ignored").
PRIMARY_DROPPED=$(ls data/raw_drops/Primary_FY202426_*.xlsx \
                     data/raw_drops/Primary_FY202426_*.xlsb \
                     data/raw_drops/Primary_FY202426_*.csv 2>/dev/null | wc -l)
echo "  Primary files staged in drop folder: $PRIMARY_DROPPED"

echo ""
echo "========== Step 1/3: Regenerate data.js (partial patch chain) =========="

# Pass 1 — Primary block (also refreshes pnl/insights + DIST allocation).
#   --detail-max-rows is a defensive guard only: it is read by --detail-only and
#   by the full build, NOT by --primary-only. detail_records survive this pass
#   because --primary-only does not rebuild them at all. Keep the flag so that
#   if this line is ever switched to a full rebuild, it does not silently
#   truncate back to the 40,000 default.
echo "  [1/2] --primary-only (detail headroom 500k) ..."
python scripts/build_dashboard_data.py \
    --src data/raw_drops --out dashboard/data.js \
    --primary-only --detail-max-rows 500000

# Pass 2 — Offtake block. Idempotent: recomputes each touched FY, never
# double-counts, and leaves P&L / Universe / Promo untouched.
echo "  [2/2] --offtake-patch ..."
python scripts/build_dashboard_data.py \
    --src data/raw_drops --out dashboard/data.js \
    --offtake-patch

echo "✓ data.js regenerated"
wc -c dashboard/data.js | awk '{printf "  Size: %.2f MB\n", $1/1024/1024}'

echo ""
echo "========== Step 2/3: QA Sentinel & Validation =========="

DETAIL_AFTER=$(count_detail_records)
PRIMARY_AFTER=$(primary_totals)
export DETAIL_BEFORE DETAIL_AFTER PRIMARY_BEFORE PRIMARY_AFTER PRIMARY_DROPPED

# Streaming validation — extracts only the small blocks it needs.
python3 << 'PYTHON_VALIDATE'
import json, os, sys

PATH  = "dashboard/data.js"
CHUNK = 1 << 18                  # 256 KB window
FY26_BASELINE = 32900.36         # FY26 is a closed year: must never move
DETAIL_FLOOR  = 40000            # anything at/below this means a truncated build

failures, warnings = [], []

def extract(key):
    """Brace-matched extraction of one top-level block. Constant memory."""
    marker = f'"{key}":'.encode()
    started, depth, out, carry = False, 0, bytearray(), b""
    with open(PATH, "rb") as f:
        while True:
            buf = f.read(CHUNK)
            if not buf:
                return None
            hay = carry + buf
            if not started:
                i = hay.find(marker)
                if i == -1:
                    carry = hay[-64:]
                    continue
                j = hay.find(b"{", i)
                if j == -1:
                    carry = hay[-64:]
                    continue
                hay, started = hay[j:], True
            for b in hay:
                out.append(b)
                if b == 0x7B: depth += 1
                elif b == 0x7D:
                    depth -= 1
                    if depth == 0:
                        return json.loads(out.decode())
            carry = b""

# --- 1. Required top-level blocks (correct nesting: by_chain lives under primary)
present = set()
with open(PATH, "r") as f:
    for line in f:
        if line.startswith(' "') and '":' in line:
            present.add(line.strip().split('"')[1])
for blk in ("primary", "offtake", "pnl", "detail_meta", "detail_records", "forecast", "universe"):
    if blk not in present:
        failures.append(f"missing top-level block: {blk}")
print(f"✓ Top-level blocks present ({len(present)} keys)")

# --- 2. Primary block: null guards + baseline
p = extract("primary")
if not p:
    failures.append("could not read primary block")
else:
    tags    = p.get("fy_tags", [])
    chains  = [c for c in p.get("by_chain", []) if c.get("name") != "Unmapped Chain"]
    channels = p.get("by_channel", [])

    if not chains:
        failures.append("primary.by_chain is empty")
    if not channels:
        failures.append("primary.by_channel is empty")

    # This is the exact guard dashboard/index.html:1170-1171 applies. A single
    # null here blanks the Primary Sales tab with "No data available".
    for t in tags:
        bad_ch = [c["name"] for c in chains   if c.get(t) is None]
        bad_cn = [c["name"] for c in channels if c.get(t) is None]
        if bad_ch:
            failures.append(f"{t}: null in by_chain -> {bad_ch[:5]}")
        if bad_cn:
            failures.append(f"{t}: null in by_channel -> {bad_cn[:5]}")
    if not any("null in by_" in f for f in failures):
        print(f"✓ Null guards pass ({len(chains)} chains, {len(channels)} channels, FY {tags})")

    # FY26 is closed (Apr-25..Mar-26). New drops are FY27+, so it must not move.
    nsv26 = p.get("nsv_fy26")
    if nsv26 is None:
        failures.append("primary.nsv_fy26 missing")
    elif abs(nsv26 - FY26_BASELINE) > 0.01:
        failures.append(
            f"FY26 baseline drifted: Rs {nsv26}L vs Rs {FY26_BASELINE}L "
            "(if this restatement is intentional, update FY26_BASELINE in this script)")
    else:
        print(f"✓ FY26 baseline preserved: Rs {nsv26}L")

# --- 3. Offtake sanity. A Primary workbook left in data/raw_drops/ satisfies the
#        offtake loader's column test, so it used to be merged into offtake at
#        ~5 orders of magnitude too large, with exit 0. The loader now rejects
#        those files; this is the second line of defence. Offtake is INR Lakh and
#        tracks Primary within an order of magnitude, so anything far outside
#        that band means the wrong file was ingested.
o = extract("offtake")
f = extract("forecast")
if not o:
    failures.append("could not read offtake block")
else:
    # Derive the per-FY totals from the total_fyNN keys themselves. Do NOT key
    # off offtake["fy_tags"]: that key is only written by --offtake-patch, so a
    # block built by the full builder has none and the loop would silently
    # validate nothing while still printing a tick.
    totals = {k: v for k, v in o.items()
              if k.startswith("total_fy") and isinstance(v, (int, float))}
    if not totals:
        failures.append("offtake has no total_fyNN keys — cannot validate magnitude")
    for k, v in sorted(totals.items()):
        if not (100 <= v <= 500000):        # plausible annual MT sell-out, Lakh
            failures.append(
                f"offtake.{k} = {v:,.0f} Lakh is outside the plausible "
                "100..500,000 band — likely a Primary/rupee-denominated file "
                "ingested as offtake")
    nc = o.get("n_chains") or 0
    if nc > 60:
        failures.append(f"offtake.n_chains = {nc} exceeds the MT universe — foreign file merged")
    if not any("offtake" in f for f in failures):
        print(f"✓ Offtake sane ({nc} chains, "
              + ", ".join(f"{k}={v}" for k, v in sorted(totals.items())) + ")")

# --- 4. detail_records: floor + preservation across the refresh
before = int(os.environ.get("DETAIL_BEFORE", 0))
after  = int(os.environ.get("DETAIL_AFTER", 0))
if after <= DETAIL_FLOOR:
    failures.append(f"detail_records={after} at/below floor {DETAIL_FLOOR} — truncated build")
elif before and after < before:
    failures.append(f"detail_records shrank: {before} -> {after}")
else:
    print(f"✓ detail_records: {after} (was {before}, floor {DETAIL_FLOOR})")

# --- 4b. CROSS-BLOCK FY INTEGRITY.
#     Each block stores its own FY totals, so they can drift apart when only
#     some blocks are refreshed. Three real defects shipped this way:
#       forecast.fy26_actual Rs 227.03 Cr  (an 8-month Aug-25..Mar-26 window
#         labelled as full-year FY26)
#       offtake.total_fy26   Rs 311.28 Cr  (matching neither the 12-month
#         Rs 329.00 Cr nor the 8-month Rs 227.03 Cr sum -- orphaned)
#       offtake.monthly      identical to primary.monthly_fy26 to within Rs 1 L
#         per month, i.e. the sell-out series was primary data, making every
#         "Primary vs Offtake" comparison a comparison with itself
#     These check the block against ITSELF, so they hold for any FY.
MON={"Jan":1,"Feb":2,"Mar":3,"Apr":4,"May":5,"Jun":6,
     "Jul":7,"Aug":8,"Sep":9,"Oct":10,"Nov":11,"Dec":12}
def fy_of(label):
    try:
        mo,yy=str(label).split("-"); y=2000+int(yy); m=MON[mo[:3].title()]
    except Exception:
        return None
    return "fy%02d" % (((y+1) if m>=4 else y) % 100)

if o and p:
    months=o.get("months") or []; monthly=o.get("monthly") or []

    # (a) months_fyNN must agree with the FY rule applied to offtake.months
    for t in {fy_of(m) for m in months if fy_of(m)}:
        expect=[m for m in months if fy_of(m)==t]
        stored=o.get("months_"+t)
        if stored is not None and list(stored)!=expect:
            missing=[m for m in expect if m not in stored]
            failures.append(
                f"offtake.months_{t} disagrees with the FY rule: stored {len(stored)} "
                f"month(s), rule gives {len(expect)}" + (f", dropping {missing}" if missing else ""))

    # (b) total_fyNN must equal the sum of that FY's months in the series
    for t in {fy_of(m) for m in months if fy_of(m)}:
        tot=o.get("total_"+t)
        if tot is None: continue
        s=sum(v or 0 for m,v in zip(months,monthly) if fy_of(m)==t)
        if s and abs(tot-s) > max(1.0, 0.005*s):
            failures.append(
                f"offtake.total_{t} = {tot:,.0f} L but its own months sum to {s:,.0f} L "
                "— the stored total is stale relative to the series")

    # (c) forecast baseline must equal the FY it claims
    if f:
        bt=(f.get("base_fy_tag") or "").lower()
        ba=f.get("fy26_actual")
        if bt and ba is not None:
            s=sum(v or 0 for m,v in zip(months,monthly) if fy_of(m)==bt)
            n=len([m for m in months if fy_of(m)==bt])
            if s and abs(ba-s) > max(1.0, 0.005*s):
                failures.append(
                    f"forecast baseline ({bt}) = {ba:,.0f} L but {bt} in the offtake series "
                    f"is {s:,.0f} L over {n} month(s) — baseline covers a different window")

    # (d) offtake must not be a copy of primary
    for pk in [k for k in p if k.startswith("monthly_fy")]:
        pm=p.get(pk) or []
        if len(pm)==len(monthly) and monthly:
            close=sum(1 for a,b in zip(pm,monthly) if abs((a or 0)-(b or 0))<=1.0)
            if close==len(monthly):
                failures.append(
                    f"offtake.monthly is identical to primary.{pk} within Rs 1 L on every "
                    "month — the sell-out series is carrying primary data, so any "
                    "primary-vs-offtake comparison is self-referential")
    if not any("offtake." in x or "forecast baseline" in x for x in failures):
        print("✓ Cross-block FY integrity (windows, totals, baseline, no primary/offtake copy)")

# --- 5. Silent no-op guard. load_primary_v2 used to read the git-tracked seed
#        CSV unconditionally, so a file staged in data/raw_drops/ was never read
#        and Primary "refreshed" to identical numbers at exit 0. That is now
#        fixed at the loader, and this is the tripwire: if Primary files were
#        staged but not one FY total moved, the drop did not reach the build.
before = (os.environ.get("PRIMARY_BEFORE") or "").strip()
after  = (os.environ.get("PRIMARY_AFTER")  or "").strip()
staged = int(os.environ.get("PRIMARY_DROPPED", 0) or 0)
if staged and before and before == after:
    failures.append(
        f"{staged} Primary file(s) staged in data/raw_drops/ but no FY total "
        f"changed ({after}) — the drop was not ingested. Check the "
        "'primary source:' line in the Pass 1 output above. "
        "(Re-running with the same Primary file also trips this, by design.)")
elif staged:
    print(f"✓ Primary drop ingested ({staged} file(s) staged; {before or 'none'} -> {after})")
else:
    print(f"✓ No Primary staged; totals unchanged ({after})")

# --- 6. Literal null-safety scan, streamed
counts = {b"NaN": 0, b"undefined": 0, b"Infinity": 0}
with open(PATH, "rb") as f:
    carry = b""
    while True:
        buf = f.read(CHUNK)
        if not buf:
            break
        hay = carry + buf
        for k in counts:
            counts[k] += hay.count(k)
        carry = hay[-16:]
for k, v in counts.items():
    if v:
        failures.append(f"{v} literal '{k.decode()}' occurrence(s) in data.js")
if not any(counts.values()):
    print("✓ No NaN / undefined / Infinity literals")

# --- verdict
print()
if failures:
    print("❌ QA SENTINEL FAILED")
    for f in failures:
        print(f"   - {f}")
    sys.exit(1)
for w in warnings:
    print(f"⚠ {w}")
print("✅ QA SENTINEL PASSED")
PYTHON_VALIDATE

echo ""
echo "========== Step 3/3: Commit & Push to Production =========="

git add dashboard/data.js
git status --short

echo ""
read -p "Review changes above. Ready to push to main? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    git commit -m "data: monthly refresh via partial patch chain

$(date +%Y-%m-%d\ %H:%M:%S) ingestion from data/raw_drops/
- Pass 1: --primary-only (primary/pnl/insights + DIST allocation)
- Pass 2: --offtake-patch (idempotent per-FY offtake merge)
- detail_records ${DETAIL_BEFORE} -> ${DETAIL_AFTER}
- QA Sentinel: null guards, FY26 baseline, detail floor all passed"

    git push origin main
    if [ $? -eq 0 ]; then
        echo ""
        echo "=========================================="
        echo "✅ DEPLOYMENT COMPLETE"
        echo "=========================================="
        echo ""
        echo "Live Dashboard: https://aswalsheshant-cell.github.io/mt-dashboard/"
        echo ""
        echo "Hard-refresh your browser (Ctrl+Shift+R) to see latest data."
        echo ""
    else
        echo "❌ Push failed. Check network or permissions."
        exit 1
    fi
else
    echo "Aborted. Changes staged but not pushed."
    git reset
    exit 0
fi
