"""Write dashboard/tdp.js from the monthly TDP files in PowerBI/RawDataFolders/TDP_Monthly (TDP_<Mon>_<YY>.csv).

TDP = Total Distribution Points = the SUM of ACV % across SKUs (PowerBI/DAX/05_TDP_Measures.dax uses the same rule).
No TDP file has been supplied yet (see docs/NIELSEN_DATA_REQUEST.md), so with no file the output is status NOT_SUPPLIED and the dashboard
says exactly which file is needed. Nothing is estimated and no sample rows are written. Files starting with "_" (the template) are ignored.

    python scripts/build_tdp.py
"""
import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / "PowerBI" / "RawDataFolders" / "TDP_Monthly"
OUT = ROOT / "dashboard" / "tdp.js"
REQUIRED = ["Month", "FY Year", "Chain", "Zone", "State", "Brand", "Category", "Sub-category", "Pack Size", "Article Code", "Article Description",
            "ACV %", "AIC", "Numeric Distribution", "Weighted Distribution", "Data Source Name"]
KEY = ["Month", "Chain", "State", "Article Code"]
MON = {m: i for i, m in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}


def month_sort(label):
    m = re.match(r"([A-Za-z]{3})'(\d\d)$", str(label))
    return (int(m.group(2)), MON.get(m.group(1), 0)) if m else (0, 0)


def files(folder=FOLDER):
    return sorted(p for p in Path(folder).glob("TDP_*.csv") if not p.name.startswith("_"))


def build(folder=FOLDER):
    fs = files(folder)
    if not fs:
        return {"status": "NOT_SUPPLIED", "needed": "PowerBI/RawDataFolders/TDP_Monthly/TDP_<Mon>_<YY>.csv (template: _TEMPLATE_TDP_Monthly.csv)", "columns": REQUIRED}
    d = pd.concat([pd.read_csv(f) for f in fs], ignore_index=True)
    missing = [c for c in REQUIRED if c not in d.columns]
    if missing:
        raise SystemExit(f"TDP files are missing columns: {missing}")
    for c in ("ACV %", "AIC", "Numeric Distribution", "Weighted Distribution"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    bad = int(d[["ACV %"]].isna().any(axis=1).sum())
    d = d.dropna(subset=["ACV %"])
    dup = int(d.duplicated(KEY).sum())      # a repeated month x chain x state x article would double the TDP: kept out
    d = d.drop_duplicates(KEY)
    months = sorted(d["Month"].unique(), key=month_sort)

    def roll(by):
        g = d.groupby(by).agg(tdp=("ACV %", "sum"), acv=("ACV %", "mean"), aic=("AIC", "mean"), nd=("Numeric Distribution", "mean"), wd=("Weighted Distribution", "mean"), articles=("Article Code", "nunique")).reset_index()
        return g

    by_month = roll(["Month"]).set_index("Month").reindex(months).reset_index()
    last = months[-1]
    cur = d[d["Month"] == last]
    out = {"status": "LOADED", "months": months, "latest": last, "files": [f.name for f in fs], "rows_used": int(len(d)), "rows_dropped_bad_acv": bad, "rows_dropped_duplicate": dup,
           "by_month": json.loads(by_month.round(2).to_json(orient="records"))}
    for key, by in (("by_chain", ["Chain"]), ("by_brand", ["Brand"]), ("by_state", ["State"])):
        g = cur.groupby(by).agg(tdp=("ACV %", "sum"), acv=("ACV %", "mean"), nd=("Numeric Distribution", "mean"), wd=("Weighted Distribution", "mean"), articles=("Article Code", "nunique")).reset_index()
        g["wd_nd_ratio"] = (g["wd"] / g["nd"]).where(g["nd"] > 0)
        out[key] = json.loads(g.round(2).sort_values("tdp", ascending=False).to_json(orient="records"))
    prev = months[-2] if len(months) > 1 else None
    out["mom_tdp_pct"] = None
    if prev:
        a, b = float(d[d["Month"] == last]["ACV %"].sum()), float(d[d["Month"] == prev]["ACV %"].sum())
        out["mom_tdp_pct"] = round((a / b - 1) * 100, 1) if b > 0 else None
    return out


def main():
    out = build()
    OUT.write_text("window.TDP=" + json.dumps(out, separators=(",", ":")) + ";\n", encoding="utf-8")
    print("tdp:", out["status"], out.get("latest", ""))


if __name__ == "__main__":
    main()
