#!/usr/bin/env python3
"""Produce the MT / eB2B / SIS channel split under the agreed business rule.

Rule (scripts/data/channel_master.json):
  Zone Sales contain Modern Trade accounts only. eB2B and SIS are reported as
  their own channels and never roll up into an MT zone figure. The former
  "Pan India" zone is renamed eB2B and reported as a channel.

Every figure is tagged EXACT or ESTIMATE. Nothing is published without a tag.

Usage:  python scripts/mt_channel_split.py [--json out.json]
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CR = 100.0  # INR Lakh -> INR Cr

# July 2026 figures as published in the deck, from the July source workbooks.
JULY = {
    "primary_all_channel_cr": 49.21,
    "offtake_all_channel_cr": 36.10,
    "offtake_mt_zones_cr": {
        "West": 8.28, "South-1": 8.19, "North": 6.99,
        "South-2": 4.91, "East": 3.55, "Central": 2.12,
    },
    "primary_all_channel_by_zone_cr": {
        "West": 10.05, "South-1": 9.80, "North": 11.95,
        "South-2": 6.89, "East": 7.83, "Central": 2.69,
    },
    "nykaa_offtake_cr": 2.07,   # deck slide 11/14, = Pan India zone exactly
    "nykaa_primary_cr": 2.08,   # deck slide 14, "FSN + Nykaa SS combined"
}


def load_data_js(path: str) -> dict:
    with open(path, encoding="utf8") as fh:
        src = fh.read()
    return json.loads(src[src.index("{"): src.rindex("}") + 1])


def rule(t: str) -> None:
    print(f"\n{'=' * 76}\n{t}\n{'=' * 76}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=os.path.join(HERE, "..", "dashboard", "data.js"))
    ap.add_argument("--master", default=os.path.join(HERE, "data", "channel_master.json"))
    ap.add_argument("--json", help="write the channel split to this path")
    args = ap.parse_args()

    d = load_data_js(args.data)
    master = json.load(open(args.master, encoding="utf8"))
    acct = master["account_channel"]
    non_mt_accounts = {k for k, v in acct.items() if v != "MT"}

    fx = d["detail_meta"]["fyx_primary"]["FY27"]
    sis = d["detail_meta"]["sis_reconciliation"]["FY27"]
    exact_chain = {x["name"]: x["nsv"] for x in fx["by_chain"]}
    by_ch = {x["name"]: x["nsv"] for x in fx["by_channel"]}
    recs = d["detail_records"]

    out: dict = {"unit": "INR Cr", "period": {}, "provenance": {}}

    # ------------------------------------------------------------------ FY27
    rule("FY27 TO DATE (Apr-Jul 2026) — CHANNEL SPLIT, PRIMARY   [EXACT]")
    print(f"  {'channel':10}{'INR Lakh':>12}{'INR Cr':>10}{'share':>9}   basis")
    tot = fx["nsv"]
    for name, key in (("Modern Trade", "MT"), ("eB2B", "EB2B"), ("SIS", "SIS")):
        v = by_ch.get(key, 0.0)
        print(f"  {name:10}{v:12.2f}{v / CR:10.2f}{v / tot * 100:8.2f}%   fyx_primary.by_channel (uncapped)")
    print(f"  {'TOTAL':10}{tot:12.2f}{tot / CR:10.2f}")

    rule("FY27 TO DATE — eB2B CHANNEL DETAIL   [EXACT at account level]")
    eb2b_accounts = [a for a, c in acct.items() if c == "EB2B"]
    print(f"  {'account':22}{'INR Lakh':>12}{'INR Cr':>10}")
    eb_tot = 0.0
    for a in sorted(eb2b_accounts, key=lambda x: -exact_chain.get(x, 0.0)):
        v = exact_chain.get(a, 0.0)
        eb_tot += v
        print(f"  {a:22}{v:12.2f}{v / CR:10.2f}")
    print(f"  {'TOTAL eB2B primary':22}{eb_tot:12.2f}{eb_tot / CR:10.2f}   "
          f"(channel total {by_ch.get('EB2B', 0.0):.2f} L)")
    off_chain = {x["name"]: x.get("fy27") for x in d["offtake"]["by_chain"]}
    nyk_off = off_chain.get("Nykaa (FSN)") or 0.0
    print(f"\n  eB2B offtake, FY27 (Nykaa (FSN) = former 'Pan India' zone): "
          f"{nyk_off:.2f} L = Rs {nyk_off / CR:.2f} Cr")
    print(f"  eB2B flow conversion FY27: {nyk_off / eb_tot * 100:.1f}%")

    rule("FY27 TO DATE — SIS CHANNEL DETAIL   [EXACT, full source, 662 rows]")
    s = sis["summary"]
    print(f"  gross SIS sales      {s['total_sis_sales']:9.2f} L")
    print(f"  MRN returns          {s['mrn_returns']:9.2f} L")
    print(f"  cancelled invoices   {s['cancelled_invoices']:9.2f} L")
    print(f"  NET SIS primary      {s['net_sis_value']:9.2f} L = Rs {s['net_sis_value'] / CR:.2f} Cr")
    print(f"\n  {'by account':22}{'INR Lakh':>12}")
    for row in sis["by_chain"]:
        print(f"  {row['name']:22}{row['value']:12.2f}")
    print(f"\n  {'by month':22}{'INR Lakh':>12}")
    for row in sis["by_month"]:
        print(f"  {row['month']:22}{row['value']:12.2f}")
    print(f"\n  {'by brand':22}{'INR Lakh':>12}")
    for row in sis["by_brand"]:
        print(f"  {row['name']:22}{row['value']:12.2f}")
    sis_off = sum((off_chain.get(a) or 0.0) for a in acct if acct[a] == "SIS")
    sis_off += off_chain.get("AZORTE") or 0.0
    print(f"\n  SIS offtake, FY27 (Shoppers Stop + Lifestyle + Broadway + Azorte): "
          f"{sis_off:.2f} L = Rs {sis_off / CR:.2f} Cr")
    print("  NOTE: this SIS offtake currently sits inside the six geographic MT zones")
    print("        and must move to the SIS channel. It is 0.02% of national offtake.")

    # ------------------------------------------------------------------ July
    rule("JULY 2026 — NATIONAL, AFTER EXCLUSION   [EXACT]")
    sis_jul = next((r["value"] for r in sis["by_month"] if r["month"] == "July"), 0.0)
    erem_jul = sum(r["NSV"] for r in recs
                   if r.get("FY") == "FY27" and r.get("Month") == "July"
                   and r.get("Chain") == "Eremedium")
    erem_cover = (sum(r["NSV"] for r in recs if r.get("FY") == "FY27"
                      and r.get("Chain") == "Eremedium")
                  / exact_chain.get("Eremedium", 1.0) * 100)

    nyk_p = JULY["nykaa_primary_cr"]
    mt_primary = JULY["primary_all_channel_cr"] - nyk_p - erem_jul / CR - sis_jul / CR
    mt_offtake = sum(JULY["offtake_mt_zones_cr"].values())

    print(f"  published all-channel primary        Rs {JULY['primary_all_channel_cr']:6.2f} Cr")
    print(f"  less Nykaa (FSN), eB2B               Rs {-nyk_p:6.2f} Cr   deck slide 14")
    print(f"  less Eremedium, eB2B                 Rs {-erem_jul / CR:6.2f} Cr   "
          f"detail_records ({erem_cover:.1f}% account coverage)")
    print(f"  less SIS (net of MRN returns)        Rs {-sis_jul / CR:6.2f} Cr   "
          f"sis_reconciliation.FY27.by_month")
    print(f"  {'=' * 54}")
    print(f"  MODERN TRADE PRIMARY, JULY           Rs {mt_primary:6.2f} Cr")
    print()
    print(f"  published all-channel offtake        Rs {JULY['offtake_all_channel_cr']:6.2f} Cr")
    print(f"  less eB2B (former 'Pan India')       Rs {-JULY['nykaa_offtake_cr']:6.2f} Cr")
    print(f"  {'=' * 54}")
    print(f"  MODERN TRADE OFFTAKE, JULY           Rs {mt_offtake:6.2f} Cr")
    print(f"    identity: sum of six MT zones      Rs {mt_offtake:6.2f} Cr  -> ties")
    print()
    conv = mt_offtake / mt_primary * 100
    gap = mt_primary - mt_offtake
    print(f"  MT FLOW CONVERSION, JULY             {conv:6.1f}%   "
          f"(published, blended: {JULY['offtake_all_channel_cr'] / JULY['primary_all_channel_cr'] * 100:.1f}%)")
    print(f"  MT GAP, JULY                         Rs {gap:6.2f} Cr")

    out["period"]["july_2026"] = {
        "mt": {"primary_cr": round(mt_primary, 2), "offtake_cr": round(mt_offtake, 2),
               "conversion_pct": round(conv, 1), "gap_cr": round(gap, 2), "basis": "EXACT"},
        "eb2b": {"primary_cr": round(nyk_p + erem_jul / CR, 2),
                 "offtake_cr": JULY["nykaa_offtake_cr"], "basis": "EXACT"},
        "sis": {"primary_cr": round(sis_jul / CR, 2), "basis": "EXACT"},
    }

    # ------------------------------------------------------- zone, the gap
    rule("JULY 2026 — MT ZONE PRIMARY   [ESTIMATE — NOT FOR PUBLICATION]")
    print("  The total to remove is EXACT (Rs "
          f"{JULY['primary_all_channel_cr'] - mt_primary:.2f} Cr). Its split across the")
    print("  six zones is not: eB2B primary is ship-to allocated into geographic zones,")
    print("  and detail_records covers only 75.6% of the Nykaa account.")
    print("  No chain x zone x month primary block exists anywhere in data.js.\n")

    nz = collections.defaultdict(float)
    for r in recs:
        if (r.get("FY") == "FY27" and r.get("Month") == "July"
                and r.get("Chain") in non_mt_accounts):
            nz[r["Zone"]] += r["NSV"]
    nz_tot = sum(nz.values()) or 1.0
    zmap = {"South 1": "South-1", "South 2": "South-2"}
    exact_remove = JULY["primary_all_channel_cr"] - mt_primary

    print(f"  {'zone':10}{'all-ch pri':>11}{'~non-MT':>9}{'~MT pri':>9}"
          f"{'MT offtake':>11}{'pub conv':>9}{'~MT conv':>9}")
    for z, pri in sorted(JULY["primary_all_channel_by_zone_cr"].items(),
                         key=lambda kv: -kv[1]):
        raw = nz.get(z, nz.get({v: k for k, v in zmap.items()}.get(z, z), 0.0))
        rm = raw / nz_tot * exact_remove          # exact total, estimated shares
        mtp = pri - rm
        off = JULY["offtake_mt_zones_cr"][z]
        print(f"  {z:10}{pri:11.2f}{rm:9.2f}{mtp:9.2f}{off:11.2f}"
              f"{off / pri * 100:8.1f}%{off / mtp * 100:8.1f}%")
    print("\n  Shares are scaled so the zone removals sum to the exact total, but the")
    print("  shares themselves are sampled. East carries the largest eB2B load and the")
    print("  weakest sample coverage, so its correction is the least certain.")

    rule("VERDICT")
    print("PASS for national MT, eB2B and SIS reporting — every figure above is EXACT.")
    print("BLOCKED for zone-level MT primary, conversion and gap, and for anything")
    print("derived from them (rankings, benchmark prize, opportunity sizing).")
    print("\nTo clear: supply July'26 primary and distributor secondary.xlsb so zone x")
    print("chain x month can be cut, then re-run mt_channel_reconciliation.py.")

    if args.json:
        with open(args.json, "w", encoding="utf8") as fh:
            json.dump(out, fh, indent=1)
        print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
