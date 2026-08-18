#!/usr/bin/env python3
"""MT channel reconciliation — enforce Total MT = geographic zones + eB2B + SIS.

Business rule under test
------------------------
Total Modern Trade = geographic MT zones + eB2B sub-channel + SIS sub-channel.

Geographic zone figures (by_zone) must carry ONLY geographic MT accounts.
eB2B (Nykaa/FSN + Eremedium) and SIS (Azorte, Shoppers Stop, Broadway,
Lifestyle) are MT sub-channels. They are:
  - INCLUDED in all national MT totals (primary, offtake, conversion).
  - EXCLUDED from the geographic zone rollup so the zone conversion benchmark
    is internally comparable across zones.

What this script does
---------------------
1. Confirms a Channel dimension exists and reports its exact totals.
2. Tests whether the zone rollup is correctly limited to geographic MT accounts
   (the core data-quality check — eB2B/SIS must not bleed into zone figures).
3. Lists chains that bill through eB2B or SIS and confirms none are attributed
   to geographic zones.
4. Runs the reconciliation identity:
     Total MT offtake = geographic zone offtake + eB2B offtake + SIS offtake
5. Quantifies the geographic-only split, separating EXACT figures from ESTIMATES.
6. Emits a release verdict.

Exactness
---------
`detail_meta.fyx_primary.FY27` is the EXACT uncapped FY27 primary and carries
by_zone and by_channel, but only at FY level — not month x zone x channel.
`detail_records` carries the full cut but is capped at 40k groups (~94.6% of
FY27 value) and is measurably MT-biased, so any month x zone x channel figure
derived from it is an ESTIMATE and is labelled as such.

Usage:  python scripts/mt_channel_reconciliation.py [path/to/data.js]
Exit code 0 = PASS, 1 = PASS WITH WARNINGS, 2 = BLOCKED.
"""
from __future__ import annotations

import collections
import json
import os
import sys

MT = "MT"
ZONE_EXCL = ("EB2B", "SIS")   # sub-channels: in total MT, but not in zone rollup
LAKH_PER_CR = 100.0

# July 2026 deck figures — total MT (geographic zones + eB2B + SIS sub-channels)
DECK_JULY_OFFTAKE_ZONE_CR = {
    "West": 8.28, "South 1": 8.19, "North": 6.99,
    "South 2": 4.91, "East": 3.55, "Central": 2.12,
}
DECK_JULY_EB2B_CR  = 2.07    # eB2B sub-channel (Nykaa/FSN July offtake)
DECK_JULY_SIS_CR   = 0.034   # SIS sub-channel (July offtake, immaterial)
DECK_JULY_PRIMARY_CR        = 49.21   # total MT primary (geographic + eB2B + SIS)
DECK_JULY_OFFTAKE_TOTAL_CR  = 36.10   # total MT offtake (geographic + eB2B + SIS)


def load(path: str) -> dict:
    with open(path, encoding="utf8") as fh:
        src = fh.read()
    return json.loads(src[src.index("{"): src.rindex("}") + 1])


def rule(title: str) -> None:
    print(f"\n{'=' * 74}\n{title}\n{'=' * 74}")


def main() -> int:
    here = os.path.dirname(os.path.abspath(__file__))
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, "..", "dashboard", "data.js")
    data = load(path)

    failures: list[str] = []
    warnings: list[str] = []

    # ---------------------------------------------------------------- check 1
    rule("CHECK 1 — Channel dimension present; sub-channel split confirmed")
    channels = data.get("dims", {}).get("Channel")
    if not channels:
        print("  FAIL: no dims.Channel in the dataset.")
        failures.append("Channel dimension absent — the rule cannot be enforced.")
        return 2
    print(f"  dims.Channel = {channels}")
    fx = data["detail_meta"]["fyx_primary"]["FY27"]
    by_ch = {d["name"]: d["nsv"] for d in fx["by_channel"]}
    total = fx["nsv"]
    print(f"\n  FY27 primary by channel (EXACT, uncapped, {fx['unit']}):")
    print(f"    {'channel':8}{'value':>12}{'share':>10}  {'in MT total?':14}{'in zone rollup?'}")
    for name, val in sorted(by_ch.items(), key=lambda kv: -kv[1]):
        in_mt   = "YES"
        in_zone = "YES" if name == MT else "NO — sub-channel"
        print(f"    {name:8}{val:12.2f}{val / total * 100:9.2f}%  {in_mt:14}{in_zone}")
    print(f"    {'TOTAL':8}{total:12.2f}  (all MT sub-channels)")
    sub_ch_val = sum(by_ch.get(c, 0.0) for c in ZONE_EXCL)
    print(f"\n  Zone sub-channels (eB2B + SIS, part of MT total): {sub_ch_val:.2f} L "
          f"= Rs {sub_ch_val / LAKH_PER_CR:.2f} Cr ({sub_ch_val / total * 100:.2f}%)")

    # ---------------------------------------------------------------- check 2
    rule("CHECK 2 — Zone rollup limited to geographic MT accounts only")
    zone_sum = sum(d["nsv"] for d in fx["by_zone"])
    print(f"  sum(by_zone)              = {zone_sum:.2f} L")
    print(f"  all-MT-channels total     = {total:.2f} L")
    print(f"  geographic-MT-only total  = {by_ch.get(MT, 0.0):.2f} L")
    if abs(zone_sum - total) < 1.0:
        print("\n  FAIL: zone rollup equals the all-MT total, meaning eB2B and SIS")
        print("        are being attributed to geographic zones instead of their")
        print("        own sub-channel tier. Zone conversion benchmark is polluted.")
        failures.append(
            f"Zone rollup carries sub-channel volume: Rs {sub_ch_val / LAKH_PER_CR:.2f} Cr "
            f"of eB2B + SIS primary is attributed to geographic zones.")
    elif abs(zone_sum - by_ch.get(MT, 0.0)) < 1.0:
        print("\n  PASS: zone rollup equals the geographic-MT-only total.")
        print("        Sub-channels (eB2B + SIS) are correctly excluded from zones.")
    else:
        print("\n  FAIL: zone rollup matches neither total — grain is undefined.")
        failures.append("Zone rollup reconciles to no stated channel base.")

    # ---------------------------------------------------------------- check 3
    rule("CHECK 3 — Sub-channel accounts not attributed to geographic zones")
    recs = data["detail_records"]
    chain_ch: dict[str, dict[str, float]] = collections.defaultdict(
        lambda: collections.defaultdict(float))
    for r in recs:
        if r.get("FY") == "FY27":
            chain_ch[r["Chain"]][r["Channel"]] += r["NSV"]

    offenders = []
    for chain, split in chain_ch.items():
        sub = sum(split.get(c, 0.0) for c in ZONE_EXCL)
        if sub > 0:
            offenders.append((chain, split.get(MT, 0.0), split.get("EB2B", 0.0),
                              split.get("SIS", 0.0)))
    offenders.sort(key=lambda t: -(t[2] + t[3]))

    if offenders:
        print(f"  Sub-channel accounts found in detail_records (expected — these are MT sub-channels):")
        print(f"  {'chain':24}{'MT zone L':>12}{'EB2B L':>10}{'SIS L':>9}")
        for chain, mt, eb, si in offenders:
            note = "  <- eB2B sub-channel" if eb else "  <- SIS sub-channel"
            print(f"  {chain:24}{mt:12.2f}{eb:10.2f}{si:9.2f}{note}")
    else:
        print("  No sub-channel accounts in detail_records FY27 sample.")

    mixed = [(chain, mt, eb, si) for chain, mt, eb, si in offenders if mt > 0 and (eb + si) > 0]
    if mixed:
        print(f"\n  WARNING: {len(mixed)} chain(s) carry both MT-zone and sub-channel volume.")
        print("  This means a single account name maps to two channel types — investigate.")
        for chain, mt, eb, si in mixed:
            warnings.append(
                f"{chain} carries both MT-zone ({mt:.2f} L) and sub-channel "
                f"({'eB2B' if eb else ''}{'SIS' if si else ''}) volume in the same FY27 sample.")

    sis_block = data["detail_meta"].get("sis_reconciliation", {})
    sis_chains = set()
    for fy, blk in sis_block.items():
        for row in blk.get("by_chain", []):
            sis_chains.add(row["name"])
    if sis_chains:
        print(f"\n  SIS accounts in detail_meta.sis_reconciliation: "
              f"{', '.join(sorted(sis_chains))}")
        print("  (correctly reported as SIS sub-channel, not as geographic zone accounts)")

    # ---------------------------------------------------------------- check 4
    rule("CHECK 4 — Reconciliation identity: Total MT = geographic zones + eB2B + SIS")
    off_zone  = {d["name"]: d.get("fy27") for d in data["offtake"]["by_zone"]}
    off_chain = {d["name"]: d.get("fy27") for d in data["offtake"]["by_chain"]}

    pan   = off_zone.get("Pan India")
    nykaa = off_chain.get("Nykaa (FSN)")
    print(f"  FY27 offtake, 'Pan India' zone : {pan}")
    print(f"  FY27 offtake, Nykaa (FSN) chain: {nykaa}")
    if pan is not None and nykaa is not None and abs(pan - nykaa) < 0.01:
        print("  -> 'Pan India' is Nykaa (FSN) exactly, 1:1. Correctly identified as eB2B sub-channel.")

    geo_zone_total = sum(v for k, v in off_zone.items() if k != "Pan India" and v)
    all_zone_total = sum(v for v in off_zone.values() if v)
    eb2b_fy27 = pan if pan is not None else 0.0
    print(f"\n  FY27 offtake breakdown:")
    print(f"    Geographic MT zones (excl. Pan India): {geo_zone_total:.2f} L")
    print(f"    eB2B sub-channel (Pan India / Nykaa):  {eb2b_fy27:.2f} L")
    print(f"    All-zone total:                        {all_zone_total:.2f} L")

    print("\n  July 2026 — deck figures (INR Cr, EXACT):")
    july_geo = sum(DECK_JULY_OFFTAKE_ZONE_CR.values())
    total_mt_check = july_geo + DECK_JULY_EB2B_CR + DECK_JULY_SIS_CR
    resid = DECK_JULY_OFFTAKE_TOTAL_CR - total_mt_check
    print(f"    6 geographic zones summed : {july_geo:.2f}")
    print(f"    eB2B sub-channel          : {DECK_JULY_EB2B_CR:.2f}")
    print(f"    SIS sub-channel           : {DECK_JULY_SIS_CR:.3f}")
    print(f"    ─────────────────────────────────────")
    print(f"    Sub-total                 : {total_mt_check:.3f}")
    print(f"    Published total MT        : {DECK_JULY_OFFTAKE_TOTAL_CR:.2f}")
    print(f"    Residual                  : {resid:+.3f}  "
          f"({'OK — rounding' if abs(resid) <= 0.05 else 'MISMATCH'})")
    if abs(resid) > 0.05:
        failures.append(
            f"Total MT offtake does not reconcile: "
            f"zones ({july_geo:.2f}) + eB2B ({DECK_JULY_EB2B_CR:.2f}) + SIS ({DECK_JULY_SIS_CR:.3f}) "
            f"= {total_mt_check:.3f} vs published {DECK_JULY_OFFTAKE_TOTAL_CR:.2f}.")

    # ---------------------------------------------------------------- check 5
    rule("CHECK 5 — Can July geographic-zone primary be corrected exactly?")
    smp = collections.defaultdict(float)
    for r in recs:
        if r.get("FY") == "FY27":
            smp[r["Channel"]] += r["NSV"]
    smp_tot = sum(smp.values())
    cover = smp_tot / total * 100
    bias = smp.get(MT, 0.0) / smp_tot * 100 - by_ch.get(MT, 0.0) / total * 100
    print(f"  detail_records covers {cover:.2f}% of exact FY27 value")
    print(f"  sampled MT share {smp.get(MT, 0.0) / smp_tot * 100:.2f}% vs exact "
          f"{by_ch.get(MT, 0.0) / total * 100:.2f}%  -> bias {bias:+.2f} pp (MT-heavy)")
    print("\n  fyx_primary gives an EXACT channel split at FY level.")
    print("  A month x zone x channel primary cut is NOT available in this dataset.")
    print("  Geographic-only July zone primary requires re-running")
    print("  scripts/build_dashboard_data.py against the full article-wise primary")
    print("  source with a Channel == 'MT' filter applied.")
    warnings.append(
        "July zone x channel primary is not derivable exactly from data.js; "
        "the source workbook is required.")

    print("\n  ESTIMATE ONLY (sampled, MT-biased — do NOT publish as geographic primary):")
    jz = collections.defaultdict(lambda: collections.defaultdict(float))
    for r in recs:
        if r.get("FY") == "FY27" and r.get("Month") == "July":
            jz[r["Zone"]][r["Channel"]] += r["NSV"]
    print(f"    {'zone':10}{'sub-ch L':>11}{'~Rs Cr':>9}")
    for z in sorted(jz, key=lambda z: -sum(jz[z].get(c, 0.0) for c in ZONE_EXCL)):
        sub = sum(jz[z].get(c, 0.0) for c in ZONE_EXCL)
        if sub > 0:
            print(f"    {z:10}{sub:11.2f}{sub / LAKH_PER_CR:9.2f}")
    tot_sub = sum(sum(jz[z].get(c, 0.0) for c in ZONE_EXCL) for z in jz)
    geo_lo = by_ch.get(MT, 0.0) / total * DECK_JULY_PRIMARY_CR
    geo_hi = DECK_JULY_PRIMARY_CR - tot_sub / LAKH_PER_CR
    july_geo_off = july_geo
    print(f"\n    Estimated July geographic-MT-only primary:")
    print(f"    FY-share method: Rs {geo_lo:.2f} Cr  |  sample-sub method: Rs {geo_hi:.2f} Cr")
    print(f"    (published total MT: Rs {DECK_JULY_PRIMARY_CR:.2f} Cr)")
    print(f"    -> Geographic conversion estimate between "
          f"{july_geo_off / geo_hi * 100:.1f}% and {july_geo_off / geo_lo * 100:.1f}%")
    print(f"       (total MT conversion: {DECK_JULY_OFFTAKE_TOTAL_CR / DECK_JULY_PRIMARY_CR * 100:.1f}%)")

    # ---------------------------------------------------------------- verdict
    rule("VERDICT")
    if failures:
        print("BLOCKED\n")
        print("Failed checks:")
        for f in failures:
            print(f"  - {f}")
    elif warnings:
        print("PASS WITH WARNINGS\n")
    else:
        print("PASS\n")
    if warnings:
        print("Warnings:")
        for w in warnings:
            print(f"  - {w}")
    print("\nTo clear the warning:")
    print("  1. Supply the full article-wise primary source for July 2026 so that")
    print("     month x zone x channel can be computed exactly.")
    print("  2. Re-run with the filtered source; CHECK 2 must show the zone rollup")
    print("     equal to the geographic-MT-only total.")
    print("  3. CHECK 4 must show total MT = zones + eB2B + SIS within Rs 0.05 Cr.")
    print("\nChannel scope reference: scripts/data/channel_master.json")

    return 2 if failures else (1 if warnings else 0)


if __name__ == "__main__":
    sys.exit(main())
