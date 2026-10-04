#!/usr/bin/env python3
"""Build data/nielsen_<period>.json (the dashboard payload) from the Nielsen snapshot CSVs.

Reads the CSVs written by scripts/extract_nielsen_report.py. Everything numeric is read
from those files; a blank cell stays None and is never turned into 0. The tracker text
(actions, gates) is the team's plan and is carried over from an earlier payload unchanged,
with a measurable `check` added where a target can be tested against the data.

    python scripts/build_nielsen_payload.py --label Aug26 --month "Aug 26" --out data/nielsen_aug26.json
"""
import argparse
import csv
import json
import re
from pathlib import Path

from build_nielsen_dashboard import brand_label

MARKET = "IN URB MT"
CATEGORY = {"facewash": "FACE WASH", "shampoo": "BOTTLES"}
OWN = "MAMAEARTH"
FACTS = {"value": "Sales Value (Crs.)", "ms": "MS Val", "ms_vol": "MS Vol", "ppml": "Price per ml",
         "stores": "Number of Stores Retailing", "nd": "Relative Numeric Distribution Handling",
         "wd": "Wghtd Dist Handling", "sah": "Share Among Handlers (SAH)",
         "pdo": "Per Dealer Offtake (PDO) (Value)"}
MONTH = re.compile(r"^[A-Z][a-z]{2} \d{2}$")
MON = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def num(value):
    value = (value or "").strip()
    return float(value) if value else None


def shift(label: str, months: int) -> str:
    """'Aug 26' shifted by +/- months -> 'Aug 25'."""
    mon, yy = label.split()
    i = MON.index(mon) + 12 * (2000 + int(yy)) + months
    return f"{MON[i % 12]} {(i // 12) % 100:02d}"


def load_snapshot(path: Path) -> dict:
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        months = [h for h in header if MONTH.match(h)]
        col = {h: i for i, h in enumerate(header)}
        data = {}
        for row in reader:
            if len(row) < 3 or not row[1]:
                continue
            data[(row[1], row[2])] = {m: num(row[col[m]]) for m in months}
    return {"months": months, "data": data}


def get(snap, key, product, month):
    return snap["data"].get((FACTS[key], product), {}).get(month)


def series(snap, key, product, months):
    return [get(snap, key, product, m) for m in months]


def pct_change(now, before):
    return round((now / before - 1) * 100, 4) if now is not None and before not in (None, 0) else None


PACK_FACT = {"facewash": ("Sales Value in Cr.", "value"), "shampoo": ("Sales (Vol (KG/LT/000NO))", "volume")}
PACK_ORDER = {"facewash": ("<50ml", "50-75ml", "76-100ml", ">100ml"), "shampoo": ("<100ml", "100-180ml", "180-200ml", ">200ml")}


def bucket_of(kind: str, size: float) -> str:
    if kind == "facewash":
        return "<50ml" if size < 50 else "50-75ml" if size <= 75 else "76-100ml" if size <= 100 else ">100ml"
    return "<100ml" if size < 100 else "100-180ml" if size < 180 else "180-200ml" if size <= 200 else ">200ml"


def _bucket_sums(rows, kind, month):
    fact = PACK_FACT[kind][0]
    sums = {}
    for r in rows:
        size = num(r.get("BASEPACKSIZE"))
        if r["Facts"] != fact or size is None:
            continue
        b = bucket_of(kind, size)
        sums[b] = sums.get(b, 0.0) + (num(r.get(month)) or 0.0)
    return sums


def pack_buckets(path: Path, kind: str, month: str):
    """Category pack mix in the dashboard's buckets: share now, and change vs a year earlier.

    Facewash is by value (Cr). The Shampoo pack sheets carry volume, WD and out-of-stock but no
    value, so Shampoo is by volume; `basis` says which.
    """
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    now, before = _bucket_sums(rows, kind, month), _bucket_sums(rows, kind, shift(month, -12))
    total = sum(now.values())
    if not total:
        raise ValueError(f"{Path(path).name}: no '{PACK_FACT[kind][0]}' rows for {month}")
    buckets = [{"sz": b, "val": round(now[b] / total * 100, 1),
                "yoy": round(pct_change(now[b], before[b]), 1) if before.get(b) else None}
               for b in PACK_ORDER[kind] if b in now]
    return {"buckets": buckets, "total": round(total, 3), "month": month, "basis": PACK_FACT[kind][1]}


def own_pack_buckets(path: Path, kind: str, month: str):
    """Mamaearth's own pack mix, same buckets and basis as the category."""
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        now = _bucket_sums(list(csv.DictReader(handle)), kind, month)
    total = sum(now.values())
    return {b: round(v / total * 100, 1) for b, v in now.items()} if total else {}


def premium_share(path: Path, kind: str, month: str, min_size: float) -> float | None:
    """Share of the pack fact (value for Facewash) sold in packs of min_size or larger."""
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        rows = [r for r in csv.DictReader(handle) if r["Facts"] == PACK_FACT[kind][0] and num(r.get("BASEPACKSIZE")) is not None]
    total = sum(num(r.get(month)) or 0.0 for r in rows)
    big = sum(num(r.get(month)) or 0.0 for r in rows if num(r["BASEPACKSIZE"]) >= min_size)
    return round(big / total * 100, 1) if total else None


def brand_rows(snap, category, month, months, *, top=None):
    ya, pm = shift(month, -12), shift(month, -1)
    brands = sorted({p for (f, p) in snap["data"] if f == FACTS["value"] and p != category},
                    key=lambda p: -(get(snap, "value", p, month) or 0))
    rows = []
    for p in brands[:top] if top else brands:
        ms, ms_py, ms_pm = get(snap, "ms", p, month), get(snap, "ms", p, ya), get(snap, "ms", p, pm)
        rows.append({
            "n": brand_label(p), "nsv": get(snap, "value", p, month), "ms": ms,
            "ms_py": ms_py, "ms_pm": ms_pm,
            "pp": round(ms - ms_py, 4) if ms is not None and ms_py is not None else None,
            "yoy_bps": round((ms - ms_py) * 100) if ms is not None and ms_py is not None else None,
            "yoy": pct_change(get(snap, "value", p, month), get(snap, "value", p, ya)),
            "stores": get(snap, "stores", p, month), "wd": get(snap, "wd", p, month),
            "nd": get(snap, "nd", p, month), "nd_py": get(snap, "nd", p, ya), "wd_py": get(snap, "wd", p, ya),
            "pdo": get(snap, "pdo", p, month), "ppml": get(snap, "ppml", p, month), "ppml_py": get(snap, "ppml", p, ya),
            "ms_vol": get(snap, "ms_vol", p, month), "ms_vol_py": get(snap, "ms_vol", p, ya),
            "sah": get(snap, "sah", p, month), "sah_py": get(snap, "sah", p, ya)})
    return rows


# Tracker targets that can be tested against the report. The numbers come from the team's own
# wording; the text itself is never edited. metric names are resolved in the template.
CHECKS = {
    "Close 2,000 New WD Stores": {"metric": "fw_wd", "op": ">=", "target": 91.2, "label": "WD %"},
    "Beat Garnier on WD": {"metric": "fw_wd_vs_garnier", "op": ">", "target": 0, "label": "WD lead vs Garnier (pp)"},
    "Premium Pack Mix to 18%": {"metric": "fw_premium_mix", "op": ">=", "target": 18, "label": "100ml+ share of Mamaearth value %"},
    "Per-Door Output Review": {"metric": "fw_pdo", "op": ">=", "target": 8500, "label": "Rs per store"},
    "Q2 FY27 Gate Review": {"metric": "fw_nsv", "op": ">=", "target": 10, "label": "NSV Rs Cr"},
    "WD crosses 91%": {"metric": "fw_wd", "op": ">=", "target": 91, "label": "WD %"},
    "NSV run-rate": {"metric": "fw_nsv", "op": ">=", "target": 10, "label": "NSV Rs Cr"},
    "Premium pack mix hits 18%": {"metric": "fw_premium_mix", "op": ">=", "target": 18, "label": "100ml+ share of Mamaearth value %"},
}


def attach_checks(items: list[dict], key: str) -> list[dict]:
    out = []
    for item in items:
        item = dict(item)
        for needle, check in CHECKS.items():
            if needle in (item.get(key) or ""):
                item["check"] = dict(check)
                break
        out.append(item)
    return out


def build_payload(root: Path, label: str, month: str, tracker_from: Path) -> dict:
    root = Path(root)
    folder = root / "data" / "nielsen"
    fw = load_snapshot(folder / f"Nielsen_FW_Snapshot_{label}.csv")
    sh = load_snapshot(folder / f"Nielsen_Shampoo_Snapshot_{label}.csv")
    if month not in fw["months"] or month not in sh["months"]:
        raise ValueError(f"{month} is not in both snapshots")
    months = fw["months"]
    ya, pm = shift(month, -12), shift(month, -1)
    tracker = json.loads(Path(tracker_from).read_text(encoding="utf-8"))

    fwc, shc = CATEGORY["facewash"], CATEGORY["shampoo"]
    fw_all = brand_rows(fw, fwc, month, months)
    sh_all = brand_rows(sh, shc, month, sh["months"])
    mon, yy = month.split()
    full_month = {"Jan": "January", "Feb": "February", "Mar": "March", "Apr": "April", "May": "May", "Jun": "June", "Jul": "July",
                  "Aug": "August", "Sep": "September", "Oct": "October", "Nov": "November", "Dec": "December"}[mon]
    fw_ppml = {"now": get(fw, "ppml", fwc, month), "ya": get(fw, "ppml", fwc, ya)}
    sh_pack = pack_buckets(folder / f"Nielsen_Shampoo_PacksCategory_{label}.csv", "shampoo", month)
    fw_pack = pack_buckets(folder / f"Nielsen_FW_PacksCategory_{label}.csv", "facewash", month)

    payload = {
        "reporting_period": f"{full_month} 20{yy}",
        "market": MARKET, "unit": "Rs Crore (Sales Value (Crs.))",
        "data_status": "GOVERNED",
        "source_reference": (f"Nielsen Retail Intelligence, market {MARKET}, workbooks Nielson_FW_Report_{label}.xlsb "
                             f"(FACE WASH) and Nielson_Shampoo_Report_{label}.xlsb (BOTTLES), latest month {month}; "
                             f"extracted by scripts/extract_nielsen_report.py"),
        "validation_reference": ("36 months (Aug 23 to Jul 26) of Mamaearth Facewash value, share, weighted distribution and stores "
                                 "tie to data/nielsen/Mamaearth_FW_Monthly_Trend.csv with 0 mismatches; Mamaearth value / category "
                                 "value reproduces MS Val; category pack mix sums to the category value "
                                 "(tests/test_nielsen_payload.py)"),
        "months": months,
        "ms": series(fw, "ms", OWN, months), "nsv": series(fw, "value", OWN, months),
        "wd": series(fw, "wd", OWN, months), "stores": series(fw, "stores", OWN, months),
        "brands": [{k: b[k] for k in ("n", "nsv", "ms", "pp", "yoy", "stores", "wd", "pdo")} for b in brand_rows(fw, fwc, month, months, top=8)],
        "fw_all": fw_all,
        "fw_cat_nsv": series(fw, "value", fwc, months),
        "fw_cat": {"value": get(fw, "value", fwc, month), "value_ya": get(fw, "value", fwc, ya), "value_pm": get(fw, "value", fwc, pm),
                   "ppml": fw_ppml["now"], "ppml_ya": fw_ppml["ya"], "stores": get(fw, "stores", fwc, month)},
        "fw_packs": [{"sz": p["sz"], "val": p["val"], "yoy": p["yoy"], "clr": "#2563EB"} for p in fw_pack["buckets"]],
        "fw_packs_mamaearth": own_pack_buckets(folder / f"Nielsen_FW_PacksMamaearth_{label}.csv", "facewash", month),
        "fw_pack_total_cr": fw_pack["total"],
        "fw_premium_mix": {"min_ml": 100,
                           "mamaearth": premium_share(folder / f"Nielsen_FW_PacksMamaearth_{label}.csv", "facewash", month, 100),
                           "category": premium_share(folder / f"Nielsen_FW_PacksCategory_{label}.csv", "facewash", month, 100)},
        "sh_packs": [{"sz": p["sz"], "val": p["val"], "yoy": p["yoy"], "clr": "#059669"} for p in sh_pack["buckets"]],
        "sh_pack_file": {"period": f"{full_month} 20{yy}", "basis": sh_pack["basis"], "source": f"Nielsen_Shampoo_PacksCategory_{label}.csv",
                         "buckets": [{"sz": p["sz"], "val": p["val"], "yoy": p["yoy"]} for p in sh_pack["buckets"]], "top": []},
        "shampoo": {
            "period": f"{full_month} 20{yy}", "month": month, "month_prev_year": ya, "month_prev_month": pm,
            "period_prev_year": ya, "period_prev_month": pm,
            "basis": f"{MARKET}, BOTTLES",
            "source_note": f"Nielsen_Shampoo_Report_{label}.xlsb, same market and month as Facewash.",
            "mamaearth_sales_cr": get(sh, "value", OWN, month),
            "mamaearth_sales_mom_pct": pct_change(get(sh, "value", OWN, month), get(sh, "value", OWN, pm)),
            "mamaearth_sales_yoy_pct": pct_change(get(sh, "value", OWN, month), get(sh, "value", OWN, ya)),
            "category_cr": get(sh, "value", shc, month),
            "category_mom_pct": pct_change(get(sh, "value", shc, month), get(sh, "value", shc, pm)),
            "category_yoy_pct": pct_change(get(sh, "value", shc, month), get(sh, "value", shc, ya)),
            "category_ppml": get(sh, "ppml", shc, month), "category_ppml_ya": get(sh, "ppml", shc, ya),
            "months": sh["months"],
            "series": {"ms": series(sh, "ms", OWN, sh["months"]), "nsv": series(sh, "value", OWN, sh["months"]),
                       "wd": series(sh, "wd", OWN, sh["months"]), "stores": series(sh, "stores", OWN, sh["months"]),
                       "category": series(sh, "value", shc, sh["months"])},
            "mamaearth_packs": own_pack_buckets(folder / f"Nielsen_Shampoo_PacksMamaearth_{label}.csv", "shampoo", month),
            "brands": sh_all},
        "aug_actions": attach_checks(tracker["aug_actions"], "title"), "sep_actions": attach_checks(tracker["sep_actions"], "title"),
        "gates": attach_checks(tracker["gates"], "q"),
    }
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--label", required=True)
    parser.add_argument("--month", required=True)
    parser.add_argument("--tracker-from", type=Path, default=Path("data/nielsen_jul26.json"))
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    payload = build_payload(args.root, args.label, args.month, args.root / args.tracker_from)
    args.out.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print("wrote", args.out, f"({args.out.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
