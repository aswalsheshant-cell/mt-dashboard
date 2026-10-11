#!/usr/bin/env python3
"""Store-wise month-on-month offtake file with two added columns.

One row per month x chain x store x article (as in the offtake files), plus:
  * Distributor-to-chain billed margin %  = 1 - (distributor NSV / distributor qty) / avg MRP per unit
        distributor qty / NSV : 05_ARTICLE_REGISTER (ex-GST rows only), same month, chain and EAN
        avg MRP per unit      : offtake MRP Sales Value / Sales Qty for the same month, chain and EAN
    It is a chain-article-month figure, so every store row of that chain/article/month shows the same value.
  * Promotional offer communicated        : Promo_Calendar file, same month, chain and EAN (first row if repeated).
Blank = not in a source file. Nothing is estimated. Reliance Brand Counter rows are left out (offtake rule).
Usage: python scripts/build_offtake_store_mom.py [--out work/Offtake_Store_MoM.csv]
"""
import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_bogo_offer_workbook as W  # noqa: E402

STORE_COLS = ["Zone", "State", "City", "Site Name"]


def build(out):
    import glob
    parts = []
    for f in sorted(glob.glob(str(W.RAW / "Offtake_Monthly" / "offtake_store_article_*_*.csv"))):
        d = pd.read_csv(f, usecols=W.OFF_COLS + STORE_COLS, low_memory=False)
        d["Month"] = W.mlabel(Path(f).stem.replace("offtake_store_article_", ""))
        parts.append(d)
    a = pd.concat(parts, ignore_index=True)
    all_rows = len(a)
    a = a[a["Store Type"].astype(str).str.strip() != "Brand Counter"].copy()
    a["Chain"] = a["Chain Name"].map(W.B.canon_chain)
    a["EANs"] = a["EAN"].map(W.ean)
    a["Brand"] = a["Brand"].map(W.B.canon_brand)

    # avg MRP per unit at month x chain x EAN
    g = a.groupby(["Month", "Chain", "EANs"])[["MRP Sales Value", "Sales Qty"]].sum()
    g["AvgMRP"] = g["MRP Sales Value"].where(g["Sales Qty"] > 0) / g["Sales Qty"].where(g["Sales Qty"] > 0)
    reg, _ = W.load_register()
    if not reg.empty:
        r = reg[reg["Include"] == "Y"].groupby(["Month", "ChainC", "EANs"])[["Qty", "NSVr"]].sum()
        r.index.names = ["Month", "Chain", "EANs"]
        g = g.join(r, how="left")
        g["BilledMargin"] = 1 - (g["NSVr"] / g["Qty"].where(g["Qty"] > 0)) / g["AvgMRP"]
    else:
        g["BilledMargin"] = pd.NA
    promo, _ = W.load_promo()
    if not promo.empty:
        p = promo.drop_duplicates(["Month", "ChainC", "EANs"]).set_index(["Month", "ChainC", "EANs"])
        p.index.names = ["Month", "Chain", "EANs"]
        p["Comm"] = p.apply(lambda x: ("%s to %s" % (x["From"], x["To"])) if (x["From"] or x["To"]) else x["Month"], axis=1)
        g = g.join(p[["Offer", "Comm"]], how="left")
    else:
        g["Offer"] = pd.NA; g["Comm"] = pd.NA
    a = a.merge(g[["BilledMargin", "Offer", "Comm"]].reset_index(), on=["Month", "Chain", "EANs"], how="left")

    o = pd.DataFrame({
        "Month": a["Month"], "Chain": a["Chain"], "Zone": a["Zone"], "State": a["State"], "City": a["City"],
        "Store": a["Site Name"], "EAN": a["EANs"], "Article": a["Article"],
        "Article description": a["Description as per Fountain"].fillna(a["Chain Article Description"]),
        "Brand": a["Brand"], "Subcategory": a["Sub_category"], "Range": a["Range"], "Pack": a["Net Weight"],
        "Offtake units": a["Sales Qty"], "Offtake value NSV (INR Lakh)": a["NSV"], "Article margin %": a["Margin"],
        "Distributor-to-chain billed margin %": a["BilledMargin"].round(6),
        "Billed margin basis": a["BilledMargin"].map(lambda v: "" if pd.isna(v) else "1-(dist NSV/dist qty)/avg MRP; register ex-GST"),
        "Promotional offer communicated": a["Offer"].fillna(""), "Communication date / month": a["Comm"].fillna(""),
    })
    o["_m"] = o["Month"].map(W.morder)
    o = o.sort_values(["_m", "Chain", "State", "Store", "Brand", "EAN"]).drop(columns="_m")
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    o.to_csv(out, index=False, encoding="utf-8-sig")

    cov = o.groupby("Month", sort=False).agg(rows=("EAN", "size"), billed=("Distributor-to-chain billed margin %", lambda s: s.notna().sum()),
                                             offer=("Promotional offer communicated", lambda s: (s != "").sum()))
    cov["value_lakh"] = o.groupby("Month", sort=False)["Offtake value NSV (INR Lakh)"].sum()
    print(cov.sort_index(key=lambda i: i.map(W.morder)).to_string())
    print("rows read %d, Brand Counter rows left out %d, rows written %d" % (all_rows, all_rows - len(a), len(o)))
    return o


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="work/Offtake_Store_MoM.csv")
    build(ap.parse_args().out)
