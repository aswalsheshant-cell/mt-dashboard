#!/usr/bin/env python3
"""Write the Power BI drop-folder files for the Nielsen cut, from the same CSVs the dashboard uses.

  PowerBI/SeedData/Nielsen/Nielsen_Monthly/nielsen_urban_mt_<label>.csv       -> Fact Nielsen Market Share
  PowerBI/SeedData/Nielsen/Nielsen_Pack_Monthly/nielsen_pack_urban_mt_<label>.csv -> Fact Nielsen Pack
  PowerBI/SeedData/Masters/Nielsen_Deck_StateExposure.csv                    -> Nielsen Deck State Exposure

Files are written under SeedData (market aggregates, tracked) and are copied into the RawDataFolders drop folders
(which the restricted-source policy keeps out of Git) to load them.

Share columns are decimals (0.128 = 12.8%), values are absolute rupees (Cr x 1e7), as in
_TEMPLATE_Nielsen_Monthly.csv. A blank source cell stays blank. Reads data/nielsen/*.csv only.

    python scripts/build_nielsen_powerbi_seed.py --label Aug26 --month "Aug 26"
"""
import argparse
import csv
import json
from pathlib import Path

from build_nielsen_payload import (CATEGORY, FACTS, _pack_facts, get, load_snapshot, shift)
from build_nielsen_dashboard import brand_label

ROOT = Path(__file__).resolve().parent.parent
CR = 1e7
CAT_NAME = {"facewash": "Facewash", "shampoo": "Shampoo"}
BRAND_FIX = {"The Derma Co": "The Derma Co."}        # spelling used in NielsenCompetitorMaster.csv
SOURCE = "Nielsen Retail Intelligence IN URB MT"
MON = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def pbi_month(label: str) -> str:
    mon, yy = label.split()
    return f"{mon}'{yy}"


def fy_label(label: str) -> str:
    """'Aug 26' -> '26-27' (Apr-Dec of year Y is FY Y-(Y+1); Jan-Mar of Y is (Y-1)-Y)."""
    mon, yy = label.split()
    y = int(yy)
    start = y if MON.index(mon) >= 3 else y - 1
    return f"{start % 100:02d}-{(start + 1) % 100:02d}"


def frac(v):
    return "" if v is None else round(v / 100, 6)


def rupees(v):
    return "" if v is None else round(v * CR, 2)


def monthly_rows(snap, kind, months):
    cat = CATEGORY[kind]
    brands = sorted({p for (f, p) in snap["data"] if f == FACTS["value"] and p != cat and p.strip().upper() != "BRAND"})
    for m in months:
        market = get(snap, "value", cat, m)
        for p in brands:
            value = get(snap, "value", p, m)
            ms, ms_vol = get(snap, "ms", p, m), get(snap, "ms_vol", p, m)
            if value is None and ms is None:
                continue                                   # brand not reported that month
            name = brand_label(p)
            vol = snap["data"].get(("Sales (Vol (KG/LT/000NO)) (000)", p), {}).get(m)
            ppml = get(snap, "ppml", p, m)
            yield [pbi_month(m), fy_label(m), CAT_NAME[kind], BRAND_FIX.get(name, name), "IN URB MT",
                   rupees(market), rupees(value), frac(ms), frac(ms_vol), SOURCE,
                   "" if vol is None else round(vol, 3), "" if ppml is None else round(ppml, 4)]


def brand_cut_rows(snap, kind, months):
    """Brand x month: share, price, distribution and productivity (the Nielsen Cuts tab), plus one '(Category)' row per month for the category price."""
    cat = CATEGORY[kind]
    brands = sorted({p for (f, p) in snap["data"] if f == FACTS["value"] and p != cat and p.strip().upper() != "BRAND"})
    r = lambda v, d: "" if v is None else round(v, d)   # noqa: E731
    for m in months:
        for p in [cat] + brands:
            value = get(snap, "value", p, m)
            if value is None:
                continue
            is_cat = p == cat
            name = "(Category)" if is_cat else brand_label(p)
            yield [pbi_month(m), fy_label(m), CAT_NAME[kind], BRAND_FIX.get(name, name), "Yes" if is_cat else "No", "IN URB MT", r(value, 4),
                   "" if is_cat else frac(get(snap, "ms", p, m)), "" if is_cat else frac(get(snap, "ms_vol", p, m)), r(get(snap, "ppml", p, m), 4),
                   r(get(snap, "wd", p, m), 3), r(get(snap, "nd", p, m), 3), r(get(snap, "stores", p, m), 0), r(get(snap, "pdo", p, m), 0),
                   r(get(snap, "sah", p, m), 3), SOURCE]


def pack_rows(folder: Path, label: str, kind: str, months):
    name = {"facewash": "FW", "shampoo": "Shampoo"}[kind]
    for m in months:
        cat = _pack_facts(folder / f"Nielsen_{name}_PacksCategory_{label}.csv", m)
        me = _pack_facts(folder / f"Nielsen_{name}_PacksMamaearth_{label}.csv", m)
        for size, v in sorted(cat.items()):
            c = v.get("value")
            if not c or c <= 0:
                continue
            mine = me.get(size) or {}
            yield [pbi_month(m), fy_label(m), CAT_NAME[kind], f"{size:g}", round(c, 4), round(mine.get("value") or 0.0, 4),
                   "" if v.get("volume") is None else round(v["volume"], 2), round(mine.get("volume") or 0.0, 2),
                   "" if v.get("wd") is None else round(v["wd"], 3), SOURCE]


def pack_brand_rows(folder: Path, label: str, kind: str, months):
    """Brand x pack size: value (Rs Cr), volume (L) and weighted distribution, all brands in the Nielsen sheet."""
    import csv as _csv
    name = {"facewash": "FW", "shampoo": "Shampoo"}[kind]
    vfact = {"facewash": "Sales Value in Cr.", "shampoo": "Sales Value (Crs.)"}[kind]
    with (folder / f"Nielsen_{name}_PackBrand_{label}.csv").open(encoding="utf-8-sig", newline="") as h:
        data = list(_csv.DictReader(h))
    for m in months:
        cell = {}
        for r in data:
            if not r["BASEPACKSIZE"] or not r.get(m, "").strip():
                continue
            slot = cell.setdefault((float(r["BASEPACKSIZE"]), brand_label(r["BRAND"])), {})
            slot[{vfact: "v", "Sales (Vol (KG/LT/000NO))": "q", "Wghtd Dist Handling": "w"}.get(r["Facts"], "x")] = float(r[m])
        for (size, brand), v in sorted(cell.items()):
            if not v.get("v"):
                continue
            yield [pbi_month(m), fy_label(m), CAT_NAME[kind], f"{size:g}", BRAND_FIX.get(brand, brand), round(v["v"], 4),
                   round(v.get("q", 0), 2), round(v["w"], 3) if "w" in v else "", SOURCE]


def write(path: Path, header, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = list(rows)
    with path.open("w", newline="", encoding="utf-8") as handle:
        w = csv.writer(handle)
        w.writerow(header)
        w.writerows(rows)
    print(f"wrote {path.relative_to(ROOT)} ({len(rows)} rows)")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--label", required=True)
    ap.add_argument("--month", required=True, help='latest month, e.g. "Aug 26"')
    ap.add_argument("--root", type=Path, default=ROOT)
    a = ap.parse_args()
    folder = a.root / "data" / "nielsen"
    fw = load_snapshot(folder / f"Nielsen_FW_Snapshot_{a.label}.csv")
    sh = load_snapshot(folder / f"Nielsen_Shampoo_Snapshot_{a.label}.csv")
    slug = a.label.lower()
    header = ["Month", "FY Year", "Nielsen Category", "Brand", "Zone", "Market Value Sales", "Our Brand Sales",
              "Value Market Share %", "Volume Market Share %", "Data Source Name", "Volume 000 L", "Price Per Ml"]
    rows = list(monthly_rows(fw, "facewash", fw["months"])) + list(monthly_rows(sh, "shampoo", sh["months"]))
    write(a.root / "PowerBI" / "SeedData" / "Nielsen" / "Nielsen_Monthly" / f"nielsen_urban_mt_{slug}.csv", header, rows)
    bc_header = ["Month", "FY Year", "Nielsen Category", "Brand", "Is Category Row", "Zone", "Value Cr", "Value Share %", "Volume Share %", "Price Per Ml",
                 "WD %", "ND %", "Stores", "Sales Per Store Rs", "SAH %", "Data Source Name"]
    bcr = list(brand_cut_rows(fw, "facewash", fw["months"])) + list(brand_cut_rows(sh, "shampoo", sh["months"]))
    write(a.root / "PowerBI" / "SeedData" / "Nielsen" / "Nielsen_Brand_Cut_Monthly" / f"nielsen_brand_cut_urban_mt_{slug}.csv", bc_header, bcr)
    months = [a.month, shift(a.month, -12)]
    prow = list(pack_rows(folder, a.label, "facewash", months)) + list(pack_rows(folder, a.label, "shampoo", months))
    write(a.root / "PowerBI" / "SeedData" / "Nielsen" / "Nielsen_Pack_Monthly" / f"nielsen_pack_urban_mt_{slug}.csv",
          ["Month", "FY Year", "Nielsen Category", "Pack Size ml", "Category Value Cr", "Our Value Cr", "Category Volume L", "Our Volume L", "Category WD %", "Data Source Name"], prow)
    pb = list(pack_brand_rows(folder, a.label, "facewash", months)) + list(pack_brand_rows(folder, a.label, "shampoo", months))
    write(a.root / "PowerBI" / "SeedData" / "Nielsen" / "Nielsen_Pack_Brand_Monthly" / f"nielsen_pack_brand_urban_mt_{slug}.csv",
          ["Month", "FY Year", "Nielsen Category", "Pack Size ml", "Brand", "Value Cr", "Volume L", "WD %", "Data Source Name"], pb)
    # account (retailer) category share: the aggregates of build_account_share.py, copied to the seed folder the queries read
    acct = a.root / "data" / "account_share"
    if (acct / "Account_Category_Monthly.csv").exists():
        import shutil
        dest = a.root / "PowerBI" / "SeedData" / "Account"
        dest.mkdir(parents=True, exist_ok=True)
        for name in ("Account_Category_Monthly.csv", "Account_Category_Geo.csv", "Account_Assortment.csv", "Account_Category_Map.csv"):
            shutil.copyfile(acct / name, dest / name)
            print(f"wrote PowerBI/SeedData/Account/{name}")
    deck_path = folder / "Deck_MT_Review_Big3_v3_1.json"
    if deck_path.exists():
        deck = json.loads(deck_path.read_text(encoding="utf-8"))
        cols = ["state", "mkt_fw", "mkt_sh", "me_fw", "me_sh", "dmart_fw", "dmart_sh", "rel_fw", "rel_sh", "apollo_fw", "apollo_sh", "lever"]
        names = ["State", "Market FW Cr", "Market SH Cr", "ME Share FW %", "ME Share SH %", "Dmart FW %", "Dmart SH %", "Reliance FW %",
                 "Reliance SH %", "Apollo FW %", "Apollo SH %", "Main Lever"]
        write(a.root / "PowerBI" / "SeedData" / "Masters" / "Nielsen_Deck_StateExposure.csv", names + ["Source", "Period"],
              [[("" if s[c] is None else s[c]) for c in cols] + ["MT_Review_Big3_v3_1.pptx (typed from deck)", deck["period"]] for s in deck["state_exposure"]])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
