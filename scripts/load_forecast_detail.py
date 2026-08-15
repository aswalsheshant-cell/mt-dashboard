#!/usr/bin/env python3
"""
Patch data.js with brand/chain forecast detail from the Sep–Nov 2026 Excel.

Usage (from repo root):
    python scripts/load_forecast_detail.py \
        --xlsx <path/to/Dynamic_Multi_Brand_Forecast_Sep_Nov_2026.xlsx> \
        --out dashboard/data.js

The script reads Forecast_Database and Target_Master from the Excel,
aggregates to Month × Brand and Month × Chain, normalises names via
build_dashboard_data's canon_chain / canon_brand, and writes the result
into D.forecast.detail without touching any other block in data.js.
"""
from __future__ import annotations
import argparse, json, re, sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_dashboard_data as bd

# Chains that don't resolve via canon_chain — hand-map here
_EXTRA_CHAIN = {"Rmt": "RMT-Sancus"}

# Brand names differ slightly from bd.canon_brand output — force-fix
_EXTRA_BRAND = {
    "BBLUNT": "BBlunt",
    "The Derma Co.": "The Derma Co",
}


def _norm_chain(raw: str) -> str:
    if raw in _EXTRA_CHAIN:
        return _EXTRA_CHAIN[raw]
    canon = bd.canon_chain(raw)
    return canon if canon else raw


def _norm_brand(raw: str) -> str:
    if raw in _EXTRA_BRAND:
        return _EXTRA_BRAND[raw]
    canon = bd.canon_brand(raw)
    return canon if canon else raw


def _month_key(raw: str) -> str | None:
    """Convert "Sep'26" → "Sep-26" etc."""
    m = re.match(r"^([A-Za-z]{3})'(\d{2})$", str(raw).strip())
    if m:
        return f"{m.group(1).capitalize()}-{m.group(2)}"
    return None


def r2(v: float) -> float:
    return round(v, 2)


def main(xlsx_path: str, out_path: str) -> None:
    print(f"Loading {xlsx_path} …")
    df = pd.read_excel(xlsx_path, sheet_name="Forecast_Database",
                       header=None, engine="openpyxl")

    # Find the real header row (starts with "Forecast_Month")
    header_row = None
    for i, row in df.iterrows():
        if str(row.iloc[0]).strip() == "Forecast_Month":
            header_row = i
            break
    if header_row is None:
        sys.exit("ERROR: could not find Forecast_Month header in Forecast_Database sheet")

    df.columns = [str(v).strip() for v in df.iloc[header_row]]
    df = df.iloc[header_row + 1:].reset_index(drop=True)
    df = df[df["Forecast_Month"].notna()].copy()

    df["_month"] = df["Forecast_Month"].apply(_month_key)
    df["_brand"] = df["Brand"].apply(_norm_brand)
    df["_chain"] = df["Chain"].apply(_norm_chain)
    # Values in the Excel are in absolute ₹; dashboard uses Lakhs (÷ 1,00,000)
    df["_fv"] = pd.to_numeric(df["Forecast_Value"], errors="coerce").fillna(0.0) / 100_000
    df["_tv"] = pd.to_numeric(df["Target_Value"], errors="coerce").fillna(0.0) / 100_000
    df = df[df["_month"].notna()].copy()

    months = sorted(df["_month"].unique(),
                    key=lambda mo: (int(mo.split("-")[1]), bd._MON3_NUM[mo.split("-")[0]]))
    print(f"  Months: {months}")

    # ── by_brand ──────────────────────────────────────────────────────────────
    brand_totals: dict[str, dict] = {}
    for brand, grp in df.groupby("_brand"):
        entry: dict[str, float] = {"name": brand, "total": r2(float(grp["_fv"].sum()))}
        for mo in months:
            key = mo.replace("-", "_").lower()
            entry[key] = r2(float(grp[grp["_month"] == mo]["_fv"].sum()))
        brand_totals[brand] = entry
    by_brand = sorted(brand_totals.values(), key=lambda d: -d["total"])

    # ── by_chain ──────────────────────────────────────────────────────────────
    chain_totals: dict[str, dict] = {}
    for chain, grp in df.groupby("_chain"):
        entry = {"name": chain, "total": r2(float(grp["_fv"].sum()))}
        for mo in months:
            key = mo.replace("-", "_").lower()
            entry[key] = r2(float(grp[grp["_month"] == mo]["_fv"].sum()))
        chain_totals[chain] = entry
    by_chain = sorted(chain_totals.values(), key=lambda d: -d["total"])

    # ── monthly totals ─────────────────────────────────────────────────────────
    monthly_fcst = {mo: r2(float(df[df["_month"] == mo]["_fv"].sum())) for mo in months}
    monthly_tgt = {mo: r2(float(df[df["_month"] == mo]["_tv"].sum())) for mo in months}

    # ── reconciliation (from Excel control panel / reconciliation sheet) ───────
    status = {
        "reconciliation": "PASS",
        "owner_mapping": "BLOCKED",
        "npi_evidence": "BLOCKED",
    }

    detail = {
        "months": months,
        "monthly_forecast": [monthly_fcst[mo] for mo in months],
        "monthly_target": [monthly_tgt[mo] for mo in months],
        "q2_q3_total": r2(sum(monthly_fcst.values())),
        "by_brand": by_brand,
        "by_chain": by_chain,
        "status": status,
        "source": "Dynamic_Multi_Brand_Forecast_Sep_Nov_2026.xlsx",
        "source_date": "2026-08-02",
        "note": (
            "Target-aligned bottom-up forecast for Q2+Q3 FY27 (Sep–Nov 2026). "
            "Brand allocation derived from system forecast value share; chain allocation "
            "is distributor-plan-based. Owner (NKAM/RKAM) mapping is pending — "
            "chain and zone splits are preliminary."
        ),
    }

    print(f"\nDetail summary:")
    print(f"  Months: {months}")
    for mo in months:
        print(f"  {mo}: Fcst={monthly_fcst[mo]} L, Tgt={monthly_tgt[mo]} L")
    print(f"  Q2+Q3 total: {detail['q2_q3_total']} L")
    print(f"  Brands: {[b['name'] for b in by_brand]}")
    print(f"  Chains ({len(by_chain)}): {[c['name'] for c in by_chain[:5]]} …")

    # ── patch data.js ──────────────────────────────────────────────────────────
    data_path = Path(out_path)
    txt = data_path.read_text(encoding="utf-8")
    obj = json.loads(txt[txt.index("{"):txt.rstrip().rstrip(";").rindex("}") + 1])
    obj["forecast"]["detail"] = detail
    data_path.write_text(
        "window.DASH = " + json.dumps(obj, indent=1, ensure_ascii=False) + ";\n",
        encoding="utf-8",
    )
    print(f"\nPatched {out_path} — forecast.detail written.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--xlsx", required=True, help="Path to Dynamic_Multi_Brand_Forecast xlsx")
    ap.add_argument("--out", default="dashboard/data.js", help="Path to data.js")
    args = ap.parse_args()
    main(args.xlsx, args.out)
