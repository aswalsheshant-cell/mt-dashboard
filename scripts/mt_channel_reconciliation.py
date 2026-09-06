#!/usr/bin/env python3
"""MT channel reconciliation — enforce "Zone Sales = Modern Trade accounts only".

Business rule under test
------------------------
Zone Sales must contain ONLY MT account sales. eB2B and SIS must not be added,
allocated, mapped or rolled up into any MT Zone Sales figure, and must be
reported under their own channel headings.

What this script does
---------------------
1. Confirms a Channel dimension exists and reports its exact totals.
2. Tests whether the zone rollup carries non-MT channels (the core defect).
3. Lists every chain that bills through eB2B or SIS, and flags the ones that
   are presented as MT accounts in the leadership deck.
4. Runs the reconciliation identity  National MT = sum of MT-only zones.
5. Quantifies the adjustment, separating EXACT figures from ESTIMATES.
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
NON_MT = ("EB2B", "SIS")
LAKH_PER_CR = 100.0

# Accounts presented as MT zone accounts in the July 2026 leadership deck.
DECK_MT_CHAINS = {
    "DMart", "Reliance Retail", "Apollo", "Nykaa (FSN)", "Lulu",
    "Wellness Forever", "Health & Glow", "Metro C&C", "More Retail",
    "VMM", "V-Mart", "Spencer", "Arambagh", "Ratandeep",
    "Sasta Sundar", "Sumo Save",
}

# July 2026 zone offtake as published in the deck (INR Cr). The six geographic
# zones are already MT-only; "Pan India" is the account under question.
DECK_JULY_OFFTAKE_CR = {
    "West": 8.28, "South 1": 8.19, "North": 6.99,
    "South 2": 4.91, "East": 3.55, "Central": 2.12,
}
DECK_JULY_PANINDIA_CR = 2.07
DECK_JULY_PRIMARY_CR = 49.21
DECK_JULY_OFFTAKE_TOTAL_CR = 36.10


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
    rule("CHECK 1 — Channel dimension present and populated")
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
    print(f"    {'channel':8}{'value':>12}{'share':>10}")
    for name, val in sorted(by_ch.items(), key=lambda kv: -kv[1]):
        print(f"    {name:8}{val:12.2f}{val / total * 100:9.2f}%")
    print(f"    {'TOTAL':8}{total:12.2f}")
    non_mt_val = sum(by_ch.get(c, 0.0) for c in NON_MT)
    print(f"\n  Non-MT (eB2B + SIS) in FY27 primary: {non_mt_val:.2f} L "
          f"= Rs {non_mt_val / LAKH_PER_CR:.2f} Cr ({non_mt_val / total * 100:.2f}%)")

    # ---------------------------------------------------------------- check 2
    rule("CHECK 2 — Does the zone rollup carry non-MT channels?  (the core defect)")
    zone_sum = sum(d["nsv"] for d in fx["by_zone"])
    print(f"  sum(by_zone)    = {zone_sum:.2f} L")
    print(f"  all-channel tot = {total:.2f} L")
    print(f"  MT-only total   = {by_ch.get(MT, 0.0):.2f} L")
    if abs(zone_sum - total) < 1.0:
        print("\n  FAIL: the zone rollup equals the ALL-CHANNEL total, so eB2B and SIS")
        print("        are being allocated into geographic MT zones.")
        failures.append(
            f"Zone rollup carries eB2B + SIS: Rs {non_mt_val / LAKH_PER_CR:.2f} Cr "
            f"of non-MT primary is inside FY27 zone sales.")
    elif abs(zone_sum - by_ch.get(MT, 0.0)) < 1.0:
        print("\n  PASS: the zone rollup already equals the MT-only total.")
    else:
        print("\n  FAIL: the zone rollup matches neither total — grain is undefined.")
        failures.append("Zone rollup reconciles to no stated channel base.")

    # ---------------------------------------------------------------- check 3
    rule("CHECK 3 — Accounts mapped into MT zones that belong to eB2B or SIS")
    recs = data["detail_records"]
    chain_ch: dict[str, dict[str, float]] = collections.defaultdict(
        lambda: collections.defaultdict(float))
    for r in recs:
        if r.get("FY") == "FY27":
            chain_ch[r["Chain"]][r["Channel"]] += r["NSV"]

    offenders = []
    for chain, split in chain_ch.items():
        non = sum(split.get(c, 0.0) for c in NON_MT)
        if non > 0:
            offenders.append((chain, split.get(MT, 0.0), split.get("EB2B", 0.0),
                              split.get("SIS", 0.0), chain in DECK_MT_CHAINS))
    offenders.sort(key=lambda t: -(t[2] + t[3]))

    print(f"  {'chain':24}{'MT':>10}{'EB2B':>10}{'SIS':>9}   in MT deck?")
    for chain, mt, eb, si, in_deck in offenders:
        flag = "  <-- YES, PRESENTED AS MT" if in_deck else ""
        print(f"  {chain:24}{mt:10.2f}{eb:10.2f}{si:9.2f}{flag}")

    # SIS chains are itemised exactly in the SIS reconciliation block
    sis_block = data["detail_meta"].get("sis_reconciliation", {})
    sis_chains = set()
    for fy, blk in sis_block.items():
        for row in blk.get("by_chain", []):
            sis_chains.add(row["name"])
    if sis_chains:
        print(f"\n  SIS accounts named in detail_meta.sis_reconciliation: "
              f"{', '.join(sorted(sis_chains))}")
        print("  (none of these are named as MT accounts in the deck, but their")
        print("   value sits inside the zone rollup above)")

    misclassified = [o for o in offenders if o[4]]
    for chain, mt, eb, si, _ in misclassified:
        failures.append(
            f"{chain} is presented as an MT zone account but bills through "
            f"{'eB2B' if eb else ''}{' + ' if eb and si else ''}{'SIS' if si else ''}.")

    # ---------------------------------------------------------------- check 4
    rule("CHECK 4 — Reconciliation identity: National MT offtake = sum of MT zones")
    off_zone = {d["name"]: d.get("fy27") for d in data["offtake"]["by_zone"]}
    off_chain = {d["name"]: d.get("fy27") for d in data["offtake"]["by_chain"]}
    pan = off_zone.get("Pan India")
    nykaa = off_chain.get("Nykaa (FSN)")
    print(f"  FY27 offtake, 'Pan India' zone : {pan}")
    print(f"  FY27 offtake, Nykaa (FSN) chain: {nykaa}")
    if pan is not None and nykaa is not None and abs(pan - nykaa) < 0.01:
        print("  -> 'Pan India' is Nykaa (FSN) exactly, 1:1. It is not a geography.")
        print("     Nykaa (FSN) primary is classified EB2B, so this offtake is eB2B.")

    mt_zone_total = sum(v for k, v in off_zone.items() if k != "Pan India" and v)
    all_zone_total = sum(v for v in off_zone.values() if v)
    print(f"\n  FY27 offtake, all zones incl. Pan India : {all_zone_total:.2f} L")
    print(f"  FY27 offtake, MT zones only             : {mt_zone_total:.2f} L")
    print(f"  eB2B removed from national MT offtake   : {all_zone_total - mt_zone_total:.2f} L "
          f"= Rs {(all_zone_total - mt_zone_total) / LAKH_PER_CR:.2f} Cr")

    print("\n  July 2026 (deck figures, INR Cr) — EXACT, no estimation:")
    july_mt_off = sum(DECK_JULY_OFFTAKE_CR.values())
    print(f"    MT zone offtake, six zones summed : {july_mt_off:.2f}")
    print(f"    published national offtake        : {DECK_JULY_OFFTAKE_TOTAL_CR:.2f}")
    print(f"    Pan India / Nykaa (eB2B)          : {DECK_JULY_PANINDIA_CR:.2f}")
    resid = DECK_JULY_OFFTAKE_TOTAL_CR - DECK_JULY_PANINDIA_CR - july_mt_off
    print(f"    identity check: {DECK_JULY_OFFTAKE_TOTAL_CR:.2f} - {DECK_JULY_PANINDIA_CR:.2f} "
          f"- {july_mt_off:.2f} = {resid:+.2f}  ({'OK, rounding' if abs(resid) <= 0.02 else 'MISMATCH'})")
    if abs(resid) > 0.02:
        failures.append("National MT offtake does not equal the sum of MT zones.")

    # ---------------------------------------------------------------- check 5
    rule("CHECK 5 — Can July zone primary be corrected exactly?")
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
    print("\n  fyx_primary gives an EXACT channel split, but only at FY level.")
    print("  A month x zone x channel primary cut is NOT available in this dataset.")
    print("  Correcting July zone primary exactly therefore requires re-running")
    print("  scripts/build_dashboard_data.py against the full article-wise primary")
    print("  source with a Channel filter applied.")
    warnings.append(
        "July zone x channel primary is not derivable exactly from data.js; "
        "the source workbook is required.")

    print("\n  ESTIMATE ONLY (sampled, MT-biased — do NOT publish):")
    jz = collections.defaultdict(lambda: collections.defaultdict(float))
    for r in recs:
        if r.get("FY") == "FY27" and r.get("Month") == "July":
            jz[r["Zone"]][r["Channel"]] += r["NSV"]
    print(f"    {'zone':10}{'non-MT L':>11}{'~Rs Cr':>9}")
    for z in sorted(jz, key=lambda z: -sum(jz[z].get(c, 0.0) for c in NON_MT)):
        non = sum(jz[z].get(c, 0.0) for c in NON_MT)
        print(f"    {z:10}{non:11.2f}{non / LAKH_PER_CR:9.2f}")
    tot_non = sum(sum(jz[z].get(c, 0.0) for c in NON_MT) for z in jz)
    lo = DECK_JULY_PRIMARY_CR - non_mt_val / total * DECK_JULY_PRIMARY_CR
    hi = DECK_JULY_PRIMARY_CR - tot_non / LAKH_PER_CR
    print(f"\n    July MT-only primary lands between Rs {lo:.2f} Cr and Rs {hi:.2f} Cr")
    print(f"    (published all-channel figure: Rs {DECK_JULY_PRIMARY_CR:.2f} Cr)")
    print(f"    -> MT conversion between {july_mt_off / hi * 100:.1f}% and "
          f"{july_mt_off / lo * 100:.1f}%, vs {DECK_JULY_OFFTAKE_TOTAL_CR / DECK_JULY_PRIMARY_CR * 100:.1f}% published")

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
    print("\nTo clear the verdict:")
    print("  1. Supply the full article-wise primary source for July 2026 so that")
    print("     month x zone x channel can be cut exactly.")
    print("  2. Re-run this check; CHECK 2 must show the zone rollup equal to the")
    print("     MT-only total, and CHECK 3 must return no deck-facing offenders.")
    print("  3. Confirm the treatment of Nykaa (FSN): the account combines FSN")
    print("     (B2C marketplace) with Nykaa SS (eB2B) at article level, so a whole-")
    print("     account exclusion also removes B2C. Business owner to decide.")

    return 2 if failures else (1 if warnings else 0)


if __name__ == "__main__":
    sys.exit(main())
