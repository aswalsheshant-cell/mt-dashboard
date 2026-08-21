#!/usr/bin/env python3
"""Split Modern Trade offtake growth into volume and price.

Why this exists
---------------
`PowerBI/DAX/04_Nielsen_Measures.dax` already carries `Market Share Volume %`, and
`skill-suite/.../references/market-share.md` already states the rule: value share and
volume share moving apart is a pricing or mix story, not a demand story. Neither has
ever been used, because `RawDataFolders/Nielsen_Monthly/` holds only a template.

The internal offtake source, however, carries `Sales Qty` next to `NSV` and
`MRP Sales Value`. That supports the same diagnosis on data we actually hold:

    value  =  units  x  ASP
    d(value) = ASP_base x d(units)        <- volume effect
             + units_now x d(ASP)         <- price / mix effect

Reporting basis matches the rest of the pack: `Store Type == 'Brand Counter'` excluded
(Reliance Brand Counter is a separate analytical breakout) and the discontinued brands
Lumineve / Pure Origin / Staze excluded. NSV in the source is INR Lakh.

June offtake is absent from RawDataFolders, so the series covers Apr, May and Jul only.
That gap is reported, never interpolated.

Usage:  python scripts/mt_price_volume_split.py [--json scripts/data/mt_price_volume.json]
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
OFFTAKE_DIR = os.path.join(ROOT, "PowerBI/RawDataFolders/Offtake_Monthly")

MONTHS = ["Apr", "May", "Jun", "Jul"]
BRAND_COUNTER = "Brand Counter"
EXCLUDED_BRANDS = {"lumineve", "pure origin", "staze", "luminev"}
NON_MT_TOKENS = ("fsn", "nykaa", "eremedium", "azorte", "shoppers",
                 "lifestyle", "broadway", "today's basket")
LAKH_PER_CR = 100.0


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


def is_mt(chain: str) -> bool:
    c = (chain or "").strip().lower()
    return not any(tok in c for tok in NON_MT_TOKENS)


class Agg:
    """units, NSV (INR Lakh), MRP sales (INR)."""

    __slots__ = ("units", "nsv", "mrp")

    def __init__(self):
        self.units = self.nsv = self.mrp = 0.0

    def add(self, u, n, m):
        self.units += u
        self.nsv += n
        self.mrp += m

    @property
    def asp(self):                       # INR per unit
        return self.nsv * 1e5 / self.units if self.units else 0.0

    @property
    def realisation(self):               # NSV as a share of MRP sales
        return self.nsv * 1e5 / self.mrp * 100 if self.mrp else 0.0


def read_month(month: str):
    """Returns (total, mt_total, by_zone, by_brand, rows, bad_qty) or None."""
    path = os.path.join(OFFTAKE_DIR, f"offtake_store_article_{month}_26.csv")
    if not os.path.exists(path):
        return None
    total, mt = Agg(), Agg()
    by_zone = collections.defaultdict(Agg)
    by_brand = collections.defaultdict(Agg)
    rows = bad_qty = 0
    with open(path, encoding="utf8", errors="replace") as fh:
        for r in csv.DictReader(fh):
            if (r.get("Store Type") or "").strip() == BRAND_COUNTER:
                continue
            if (r.get("Brand") or "").strip().lower() in EXCLUDED_BRANDS:
                continue
            u = num(r["Sales Qty"])
            n = num(r["NSV"])
            m = num(r["MRP Sales Value"])
            rows += 1
            if u <= 0:
                bad_qty += 1
                continue                 # cannot price a zero-unit row
            total.add(u, n, m)
            if is_mt(r["Chain Name"]):
                mt.add(u, n, m)
                by_zone[canon_zone(r["Zone"])].add(u, n, m)
                by_brand[(r.get("Brand") or "").strip()].add(u, n, m)
    return total, mt, by_zone, by_brand, rows, bad_qty


def rule(t: str) -> None:
    print(f"\n{'=' * 78}\n{t}\n{'=' * 78}")


def decompose(base: Agg, now: Agg):
    """d(value) = volume effect + price effect, in INR Cr."""
    d_units = now.units - base.units
    d_asp = now.asp - base.asp
    vol = base.asp * d_units / 1e7
    price = now.units * d_asp / 1e7
    return vol, price, (now.nsv - base.nsv) / LAKH_PER_CR


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=os.path.join(HERE, "data", "mt_price_volume.json"))
    args = ap.parse_args()

    data = {m: read_month(m) for m in MONTHS}
    have = [m for m in MONTHS if data[m]]
    missing = [m for m in MONTHS if not data[m]]
    if not have:
        print(f"No offtake month files found in {OFFTAKE_DIR}", file=sys.stderr)
        return 2

    rule("DATA QUALITY — units field")
    for m in have:
        _, _, _, _, rows, bad = data[m]
        print(f"  {m}: {rows:,} rows, {bad} with Sales Qty <= 0 ({bad / rows * 100:.2f}%)")
    if missing:
        print(f"\n  MISSING month files: {', '.join(missing)} — reported as gaps, never interpolated.")

    rule("MODERN TRADE — UNITS, VALUE AND PRICE   [EXACT]")
    print(f"  {'month':7}{'units':>12}{'NSV Cr':>10}{'MRP Cr':>10}{'ASP Rs':>10}{'realisation':>13}")
    for m in have:
        _, mt, _, _, _, _ = data[m]
        print(f"  {m:7}{mt.units:12,.0f}{mt.nsv / LAKH_PER_CR:10.2f}"
              f"{mt.mrp / 1e7:10.2f}{mt.asp:10.2f}{mt.realisation:12.1f}%")

    rule("GROWTH SPLIT — HOW MUCH WAS VOLUME, HOW MUCH WAS PRICE   [EXACT]")
    print("  value change = (base ASP x unit change) + (current units x ASP change)\n")
    print(f"  {'period':13}{'d value Cr':>12}{'volume Cr':>12}{'price Cr':>11}{'read':>26}")
    for a, b in zip(have, have[1:]):
        _, mtA, _, _, _, _ = data[a]
        _, mtB, _, _, _, _ = data[b]
        vol, price, tot = decompose(mtA, mtB)
        lead = "volume-led" if abs(vol) >= abs(price) else "price / mix-led"
        sign = "growth" if tot >= 0 else "decline"
        gap = "" if b == MONTHS[MONTHS.index(a) + 1] else "  (non-adjacent — June missing)"
        print(f"  {a}->{b:8}{tot:12.2f}{vol:12.2f}{price:11.2f}{lead + ' ' + sign:>26}{gap}")

    rule("JULY MT BY ZONE — PRICE AND MIX   [EXACT]")
    _, mt_jul, zones_jul, brands_jul, _, _ = data["Jul"]
    print(f"  {'zone':10}{'units':>12}{'NSV Cr':>10}{'ASP Rs':>10}{'vs national':>13}{'realisation':>13}")
    for z, a in sorted(zones_jul.items(), key=lambda kv: -kv[1].nsv):
        idx = a.asp / mt_jul.asp * 100
        print(f"  {z:10}{a.units:12,.0f}{a.nsv / LAKH_PER_CR:10.2f}{a.asp:10.2f}"
              f"{idx:12.0f}{a.realisation:12.1f}%")
    print(f"  {'MT TOTAL':10}{mt_jul.units:12,.0f}{mt_jul.nsv / LAKH_PER_CR:10.2f}"
          f"{mt_jul.asp:10.2f}{100:12.0f}{mt_jul.realisation:12.1f}%")

    rule("JULY MT BY BRAND — PRICE POSITION   [EXACT]")
    print(f"  {'brand':18}{'units':>12}{'NSV Cr':>10}{'ASP Rs':>10}{'realisation':>13}")
    for bn, a in sorted(brands_jul.items(), key=lambda kv: -kv[1].nsv)[:6]:
        print(f"  {bn:18}{a.units:12,.0f}{a.nsv / LAKH_PER_CR:10.2f}{a.asp:10.2f}{a.realisation:12.1f}%")

    rule("RECONCILIATION   [must tie]")
    total_jul, mt_j, zones_j, _, _, _ = data["Jul"]
    zsum = sum(a.nsv for a in zones_j.values()) / LAKH_PER_CR
    checks = [
        ("July all-channel offtake", total_jul.nsv / LAKH_PER_CR, 36.06),
        ("July MT offtake", mt_j.nsv / LAKH_PER_CR, 33.96),
        ("sum of MT zones", zsum, mt_j.nsv / LAKH_PER_CR),
    ]
    ok = True
    for label, got, want in checks:
        tie = abs(got - want) <= 0.02
        ok &= tie
        print(f"  {label:28}{got:9.2f} Cr  vs {want:7.2f}  {'TIES' if tie else 'MISMATCH'}")
    rebuilt = mt_j.units * mt_j.asp / 1e7
    tie = abs(rebuilt - mt_j.nsv / LAKH_PER_CR) <= 0.02
    ok &= tie
    print(f"  {'units x ASP rebuilds NSV':28}{rebuilt:9.2f} Cr  vs {mt_j.nsv / LAKH_PER_CR:7.2f}  "
          f"{'TIES' if tie else 'MISMATCH'}")

    out = {
        "unit": "INR Cr unless stated", "basis": "EXACT — full month source files",
        "note": "Brand Counter stores and discontinued brands excluded; "
                "June offtake file absent from RawDataFolders",
        "months_present": have, "months_missing": missing,
        "mt_monthly": [{"month": m,
                        "units": round(data[m][1].units),
                        "nsv_cr": round(data[m][1].nsv / LAKH_PER_CR, 2),
                        "asp_inr": round(data[m][1].asp, 2),
                        "realisation_pct": round(data[m][1].realisation, 1)} for m in have],
        "jul_by_zone": [{"zone": z, "units": round(a.units),
                         "nsv_cr": round(a.nsv / LAKH_PER_CR, 2),
                         "asp_inr": round(a.asp, 2),
                         "asp_index": round(a.asp / mt_jul.asp * 100),
                         "realisation_pct": round(a.realisation, 1)}
                        for z, a in sorted(zones_jul.items(), key=lambda kv: -kv[1].nsv)],
    }
    os.makedirs(os.path.dirname(args.json), exist_ok=True)
    with open(args.json, "w", encoding="utf8") as fh:
        json.dump(out, fh, indent=1)
    print(f"\nwrote {args.json}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
