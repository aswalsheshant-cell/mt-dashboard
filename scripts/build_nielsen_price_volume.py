#!/usr/bin/env python3
"""Price / volume split, realisation ladder and zone price index for the Nielsen dashboard.

Two parts, kept apart because they measure different things:

  nielsen  : consumer offtake in the Nielsen market (IN URB MT). Value, volume and price per ml
             for the category and for Mamaearth, face wash and shampoo, this month vs a year ago.
             value change = volume effect + price/mix effect (same rule as mt_price_volume_split.py).
  internal : Honasa MT offtake from the store x article files (Apr-Aug 26): units, ASP, NSV as % of
             MRP sales (realisation), by month, brand, chain and zone, with a zone price index
             (zone ASP / MT ASP x 100). Basis is mt_price_volume_split.py's MT basis (Brand Counter,
             discontinued brands and non-MT chains such as FSN left out), so totals differ from the
             chain-contribution table, which keeps FSN.

Reuses Agg / read_month / decompose from scripts/mt_price_volume_split.py; nothing is recomputed twice.

    python scripts/build_nielsen_price_volume.py --label Aug26 --month "Aug 26" --months Apr May Jun Jul Aug
"""
import argparse
import json
from pathlib import Path

import mt_price_volume_split as pv
from build_nielsen_payload import CATEGORY, FACTS, OWN, get, load_snapshot, pct_change, shift

ROOT = Path(__file__).resolve().parent.parent
LAKH = 100.0


def nielsen_block(snap, kind, month):
    cat = CATEGORY[kind]
    ya = shift(month, -12)
    out = []
    for label, product in (("Category", cat), ("Mamaearth", OWN)):
        v, v0 = get(snap, "value", product, month), get(snap, "value", product, ya)
        vol = snap["data"].get(("Sales (Vol (KG/LT/000NO)) (000)", product), {})
        q, q0 = vol.get(month), vol.get(ya)
        p, p0 = get(snap, "ppml", product, month), get(snap, "ppml", product, ya)
        if None in (v, v0, q, q0, p, p0):
            continue
        f = 1000 * 1000 / 1e7
        d_vol = (q - q0) * p0 * f
        d_price = (v - v0) - d_vol
        d_val = v - v0
        out.append({"name": label, "value_cr": v, "value_cr_ya": v0, "value_yoy": pct_change(v, v0),
                    "volume_000l": q, "volume_000l_ya": q0, "volume_yoy": pct_change(q, q0),
                    "ppml": p, "ppml_ya": p0, "price_yoy": pct_change(p, p0),
                    "vol_effect_cr": round(d_vol, 3), "price_effect_cr": round(d_price, 3), "value_change_cr": round(d_val, 3),
                    "reads_as": "volume-led" if abs(d_vol) >= abs(d_price) else "price / mix-led"})
    return out


def agg_row(name, a, total):
    return {"name": name, "units": round(a.units), "nsv_cr": round(a.nsv / LAKH, 3), "asp": round(a.asp, 2),
            "realisation_pct": round(a.realisation, 1), "asp_index": round(a.asp / total.asp * 100) if total.asp else None}


def internal_block(months):
    data, chains = {}, {}
    for m in months:
        c = {}
        res = pv.read_month(m, by_chain=c)
        if res:
            data[m], chains[m] = res, c
    have = [m for m in months if m in data]
    monthly = [{"month": m, **agg_row(m, data[m][1], data[m][1])} for m in have]
    steps = []
    for a, b in zip(have, have[1:]):
        vol, price, tot = pv.decompose(data[a][1], data[b][1])
        steps.append({"from": a, "to": b, "value_change_cr": round(tot, 2), "volume_cr": round(vol, 2), "price_cr": round(price, 2),
                      "reads_as": "volume-led" if abs(vol) >= abs(price) else "price / mix-led"})
    first, last = have[0], have[-1]
    vol, price, tot = pv.decompose(data[first][1], data[last][1])
    span = {"from": first, "to": last, "value_change_cr": round(tot, 2), "volume_cr": round(vol, 2), "price_cr": round(price, 2)}
    cum = pv.Agg()
    zones, brands, chain_cum = {}, {}, {}
    for m in have:
        _, mt, z, b, _, _ = data[m]
        cum.add(mt.units, mt.nsv, mt.mrp)
        for k, a in z.items():
            zones.setdefault(k, pv.Agg()).add(a.units, a.nsv, a.mrp)
        for k, a in b.items():
            brands.setdefault(k, pv.Agg()).add(a.units, a.nsv, a.mrp)
        for k, a in chains[m].items():
            chain_cum.setdefault(k, pv.Agg()).add(a.units, a.nsv, a.mrp)
    latest_mt, latest_z = data[last][1], data[last][2]
    return {
        "months": have, "basis": "Honasa MT offtake, store x article files; Brand Counter, discontinued brands and non-MT chains (FSN etc.) left out. NSV Rs Cr; realisation = NSV as % of MRP sales.",
        "monthly": monthly, "steps": steps, "span": span,
        "zones_latest": [agg_row(k, a, latest_mt) for k, a in sorted(latest_z.items(), key=lambda kv: -kv[1].nsv)],
        "zones_cumulative": [agg_row(k, a, cum) for k, a in sorted(zones.items(), key=lambda kv: -kv[1].nsv)],
        "brands": [agg_row(k, a, cum) for k, a in sorted(brands.items(), key=lambda kv: -kv[1].nsv) if k and not k.replace(".", "").isdigit()][:6],
        "chains": [agg_row(k.title() if len(k) > 4 else k, a, cum) for k, a in sorted(chain_cum.items(), key=lambda kv: -kv[1].nsv)[:12] if a.nsv > 0],
        "total": agg_row("MT", cum, cum),
    }


def build(label, month, months, root=ROOT):
    folder = Path(root) / "data" / "nielsen"
    fw = load_snapshot(folder / f"Nielsen_FW_Snapshot_{label}.csv")
    sh = load_snapshot(folder / f"Nielsen_Shampoo_Snapshot_{label}.csv")
    return {"month": month, "month_ya": shift(month, -12),
            "nielsen": {"facewash": nielsen_block(fw, "facewash", month), "shampoo": nielsen_block(sh, "shampoo", month)},
            "internal": internal_block(months)}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--label", required=True)
    ap.add_argument("--month", required=True)
    ap.add_argument("--months", nargs="+", default=["Apr", "May", "Jun", "Jul", "Aug"])
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    out = a.out or ROOT / "data" / "nielsen" / f"Price_Volume_{a.label}.json"
    out.write_text(json.dumps(build(a.label, a.month, a.months), indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print("wrote", out)


if __name__ == "__main__":
    main()
