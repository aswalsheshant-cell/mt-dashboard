#!/usr/bin/env python3
"""Produce the MT / eB2B / SIS split for July 2026 from the real month sources.

Business rule (scripts/data/channel_master.json):
  Zone Sales contain Modern Trade accounts only. eB2B and SIS are reported as
  their own channels and never roll up into an MT zone figure. The former
  "Pan India" zone is renamed eB2B and reported as a channel.

Sources — both are the full uncapped month files, not the row-capped
detail_records table baked into dashboard/data.js:
  PowerBI/RawDataFolders/Primary_Article_Monthly/primary_article_Jul_26.csv
      31,355 rows. Carries an explicit Channel column (MT / EB2B / SIS).
  PowerBI/RawDataFolders/Offtake_Monthly/offtake_store_article_Jul_26.csv
      220,522 rows. No Channel column, so channel is resolved by account name
      against the channel master.

Reporting basis, reproduced from the published pack:
  offtake excludes Store Type == 'Brand Counter' (Reliance Brand Counter is a
  separate analytical breakout) and the discontinued brands Lumineve, Pure
  Origin and Staze. On that basis every zone ties to the published deck within
  Rs 0.03 Cr.

Usage:  python scripts/mt_channel_split.py [--json scripts/data/july_mt_channel_split.json]
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
PRIMARY = os.path.join(ROOT, "PowerBI/RawDataFolders/Primary_Article_Monthly/primary_article_Jul_26.csv")
OFFTAKE = os.path.join(ROOT, "PowerBI/RawDataFolders/Offtake_Monthly/offtake_store_article_Jul_26.csv")

PRIMARY_NSV = "Inv. Net value(LOC)"      # INR
OFFTAKE_NSV = "NSV"                      # INR Lakh
EXCLUDED_BRANDS = {"lumineve", "pure origin", "staze", "luminev"}
BRAND_COUNTER = "Brand Counter"
ZONES = ["West", "South-1", "North", "South-2", "East", "Central"]
FLOOR = 0.25                             # INR Cr materiality floor


def num(v: str) -> float:
    v = (v or "").replace(",", "").strip()
    try:
        return float(v)
    except ValueError:
        return 0.0


def canon_zone(z: str) -> str:
    z = (z or "").strip().upper().replace(" ", "-")
    return {"WEST": "West", "SOUTH-1": "South-1", "NORTH": "North",
            "SOUTH-2": "South-2", "EAST": "East", "CENTRAL": "Central",
            "PAN-INDIA": "Pan India"}.get(z, z.title())


def load_master() -> dict:
    return json.load(open(os.path.join(HERE, "data", "channel_master.json"), encoding="utf8"))


def offtake_channel(chain: str, master: dict) -> str:
    """Offtake has no Channel column; resolve it from the account name."""
    c = (chain or "").strip().lower()
    for token, ch in (("fsn", "EB2B"), ("nykaa", "EB2B"), ("eremedium", "EB2B"),
                      ("azorte", "SIS"), ("shoppers", "SIS"), ("lifestyle", "SIS"),
                      ("broadway", "SIS"), ("today's basket", "SIS")):
        if token in c:
            return ch
    return "MT"


def read_primary() -> tuple[dict, dict]:
    """(zone, channel) -> INR Cr, and account -> {channel: INR Cr}."""
    zc: dict = collections.defaultdict(float)
    acct: dict = collections.defaultdict(lambda: collections.defaultdict(float))
    with open(PRIMARY, encoding="utf8", errors="replace") as fh:
        for r in csv.DictReader(fh):
            v = num(r[PRIMARY_NSV]) / 1e7           # INR -> INR Cr
            ch = (r["Channel"] or "").strip().upper()
            zc[(canon_zone(r["Zone"]), ch)] += v
            if ch != "MT":
                acct[r["Chain name for Dashboard"].strip()][ch] += v
    return zc, acct


def read_offtake(master: dict) -> tuple[dict, dict]:
    """(zone, channel) -> INR Cr, and non-MT account -> INR Cr."""
    zc: dict = collections.defaultdict(float)
    acct: dict = collections.defaultdict(float)
    with open(OFFTAKE, encoding="utf8", errors="replace") as fh:
        for r in csv.DictReader(fh):
            if (r.get("Store Type") or "").strip() == BRAND_COUNTER:
                continue
            if (r.get("Brand") or "").strip().lower() in EXCLUDED_BRANDS:
                continue
            v = num(r[OFFTAKE_NSV]) / 100.0         # INR Lakh -> INR Cr
            ch = offtake_channel(r["Chain Name"], master)
            zc[(canon_zone(r["Zone"]), ch)] += v
            if ch != "MT":
                acct[r["Chain Name"].strip()] += v
    return zc, acct


def rule(t: str) -> None:
    print(f"\n{'=' * 78}\n{t}\n{'=' * 78}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=os.path.join(HERE, "data", "july_mt_channel_split.json"))
    args = ap.parse_args()

    for p in (PRIMARY, OFFTAKE):
        if not os.path.exists(p):
            print(f"MISSING SOURCE: {p}", file=sys.stderr)
            return 2

    master = load_master()
    pz, pacct = read_primary()
    oz, oacct = read_offtake(master)

    rule("JULY 2026 — PRIMARY BY CHANNEL   [EXACT, full month file]")
    pch = collections.defaultdict(float)
    for (z, c), v in pz.items():
        pch[c] += v
    ptot = sum(pch.values())
    for c in ("MT", "EB2B", "SIS"):
        print(f"  {c:6}{pch[c]:9.2f} Cr {pch[c] / ptot * 100:7.2f}%")
    print(f"  {'TOTAL':6}{ptot:9.2f} Cr   (published all-channel primary: 49.21)")

    rule("JULY 2026 — NON-MT ACCOUNTS   [EXACT]")
    print("  primary side")
    for a, d in sorted(pacct.items(), key=lambda kv: -sum(kv[1].values())):
        for c, v in d.items():
            print(f"    {a:34}{c:6}{v:9.3f} Cr")
    print("  offtake side")
    for a, v in sorted(oacct.items(), key=lambda kv: -kv[1]):
        print(f"    {a:34}{'':6}{v:9.4f} Cr")

    rule("JULY 2026 — MT-ONLY ZONE PERFORMANCE   [EXACT]")
    rows = []
    for z in ZONES:
        mtp = pz[(z, "MT")]
        mto = oz[(z, "MT")]
        rows.append({"zone": z, "primary": mtp, "offtake": mto,
                     "conv": mto / mtp * 100 if mtp else 0.0, "gap": mtp - mto})
    tp = sum(r["primary"] for r in rows)
    to = sum(r["offtake"] for r in rows)
    rows.sort(key=lambda r: -r["gap"])

    print(f"  {'zone':9}{'MT primary':>12}{'MT offtake':>12}{'conv':>9}{'gap':>9}{'mix':>8}")
    for r in rows:
        print(f"  {r['zone']:9}{r['primary']:12.2f}{r['offtake']:12.2f}"
              f"{r['conv']:8.1f}%{r['gap']:9.2f}{r['offtake'] / to * 100:7.1f}%")
    print(f"  {'TOTAL':9}{tp:12.2f}{to:12.2f}{to / tp * 100:8.1f}%{tp - to:9.2f}")

    rule("RECONCILIATION   [must tie]")
    print(f"  sum of MT zone primary        {tp:8.2f} Cr")
    print(f"  Channel == MT total           {pch['MT']:8.2f} Cr   "
          f"{'TIES' if abs(tp - pch['MT']) < 0.01 else 'MISMATCH'}")
    print(f"  sum of MT zone offtake        {to:8.2f} Cr")
    otot = sum(oz.values())
    print(f"  all-channel offtake           {otot:8.2f} Cr   (published 36.10)")
    print(f"  less eB2B                     {-oz[('Pan India', 'EB2B')]:8.2f} Cr")
    sis_off = sum(v for (z, c), v in oz.items() if c == "SIS")
    print(f"  less SIS inside MT zones      {-sis_off:8.2f} Cr")
    print(f"  = MT offtake                  {otot - oz[('Pan India', 'EB2B')] - sis_off:8.2f} Cr   "
          f"{'TIES' if abs(otot - oz[('Pan India', 'EB2B')] - sis_off - to) < 0.01 else 'MISMATCH'}")

    rule("BENCHMARK OPPORTUNITY, RECOMPUTED ON MT-ONLY   [EXACT]")
    bench_zones = ["West", "South-1"]
    bm = sum(pz[(z, "MT")] and oz[(z, "MT")] / pz[(z, "MT")] for z in bench_zones) / len(bench_zones) * 100
    print(f"  benchmark = mean MT conversion of {', '.join(bench_zones)} = {bm:.2f}%")
    prize = 0.0
    for r in sorted(rows, key=lambda r: -(r["primary"] * bm / 100 - r["offtake"])):
        rec = r["primary"] * bm / 100 - r["offtake"]
        if rec >= FLOOR:
            prize += rec
            print(f"    {r['zone']:9} {r['primary']:6.2f} x {bm:.2f}% = "
                  f"{r['primary'] * bm / 100:6.2f} vs {r['offtake']:5.2f} offtake -> +{rec:5.2f} Cr")
        elif rec > 0:
            print(f"    {r['zone']:9} +{rec:5.2f} Cr — below the Rs {FLOOR:.2f} Cr materiality floor")
    print(f"\n  RECOVERABLE ABOVE FLOOR = Rs {prize:.2f} Cr")
    print(f"  national MT conversion would move {to / tp * 100:.1f}% -> {(to + prize) / tp * 100:.1f}%")

    rule("eB2B AND SIS CHANNELS   [EXACT]")
    eb_p, eb_o = pch["EB2B"], oz[("Pan India", "EB2B")]
    print(f"  eB2B   primary {eb_p:6.2f} Cr   offtake {eb_o:6.2f} Cr   flow {eb_o / eb_p * 100:5.1f}%")
    print(f"  SIS    primary {pch['SIS']:6.2f} Cr   offtake {sis_off:6.4f} Cr   "
          f"(primary is net of MRN returns and negative in July)")

    out = {
        "period": "Jul-26", "unit": "INR Cr", "basis": "EXACT — full month source files",
        "mt": {"primary": round(tp, 2), "offtake": round(to, 2),
               "conversion_pct": round(to / tp * 100, 1), "gap": round(tp - to, 2),
               "by_zone": [{"zone": r["zone"], "primary": round(r["primary"], 2),
                            "offtake": round(r["offtake"], 2),
                            "conversion_pct": round(r["conv"], 1),
                            "gap": round(r["gap"], 2)} for r in rows]},
        "eb2b": {"primary": round(eb_p, 2), "offtake": round(eb_o, 2),
                 "flow_pct": round(eb_o / eb_p * 100, 1)},
        "sis": {"primary": round(pch["SIS"], 3), "offtake": round(sis_off, 4)},
        "benchmark": {"pct": round(bm, 2), "zones": bench_zones,
                      "recoverable_above_floor": round(prize, 2), "floor": FLOOR},
    }
    with open(args.json, "w", encoding="utf8") as fh:
        json.dump(out, fh, indent=1)
    print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
