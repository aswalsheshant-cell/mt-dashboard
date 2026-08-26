#!/usr/bin/env python3
"""
Patch data.js with monthly promo-calendar detail from a Promo_<Mon><YY>.xlsx.

Usage (from repo root):
    python scripts/load_promo_detail.py \
        --xlsx <path/to/Promo_Aug__2026.xlsx> \
        --out dashboard/data.js

Reads the 'Promo ' and 'Chain Update ' sheets, normalises chain / brand names,
parses the heterogeneous consumer-offer column (decimal fraction, "25% off",
"B1G1" etc.), builds per-chain / per-brand / per-category aggregates plus a
KAM accountability table, and patches the result into D.promo.detail without
touching any other block in data.js.
"""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_dashboard_data as bd

# ── name-normalisation overrides ──────────────────────────────────────────────
# Covers typos and variants found in both the Promo sheet and Chain Update sheet.
_EXTRA_CHAIN: dict[str, str] = {
    "Wellnes": "Wellness Forever",
    "Wellness Forever": "Wellness Forever",
    "Frankross": "Frankros",
    "Frankros": "Frankros",
    "V Mart": "V-Mart",
    "V-Mart": "V-Mart",
    "WH -Smith": "WH Smith",
    "Arambagh": "ARAMBAGH",
    "ARAMBAGH": "ARAMBAGH",
    "Metro": "Metro CNC",
    "Metro CNC": "Metro CNC",
    "Reliance(GE Offers)": "Reliance Retail",
    "Reliance Retail Limi": "Reliance Retail",
    "Sancus(RMT)": "RMT-Sancus",
    "SIS ": "SIS",
    "VMM": "Vishal Mega Mart",
}

_EXTRA_BRAND: dict[str, str] = {
    "BBLUNT": "BBlunt",
    "The Derma Co.": "The Derma Co",
}

_PCT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*%")
_BxGy_RE = re.compile(r"B(\d+)G(\d+)", re.IGNORECASE)


# ── helpers ───────────────────────────────────────────────────────────────────

def _norm_chain(raw: str) -> str:
    raw = raw.strip()
    if raw in _EXTRA_CHAIN:
        return _EXTRA_CHAIN[raw]
    canon = bd.canon_chain(raw)
    return canon if canon else raw


def _norm_brand(raw) -> str:
    if not raw or not isinstance(raw, str):
        return "Unknown"
    raw = raw.strip()
    if raw in _EXTRA_BRAND:
        return _EXTRA_BRAND[raw]
    canon = bd.canon_brand(raw)
    return canon if canon else raw


def _parse_offer_pct(v) -> float | None:
    """Parse heterogeneous 'Offer to consumer' → % depth (0–100), or None."""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        # decimal fraction (e.g. 0.2 = 20 %)
        f = float(v)
        if 0 < f < 1:
            return round(f * 100, 1)
        return None
    s = str(v).strip()
    m = _PCT_RE.search(s)
    if m:
        return float(m.group(1))
    m2 = _BxGy_RE.search(s)
    if m2:
        buy, get = int(m2.group(1)), int(m2.group(2))
        return round(get / (buy + get) * 100, 1)
    return None


def _infer_month(path: str) -> str:
    """Try to extract 'Mon-YY' from the filename, fallback to 'Unknown'."""
    name = Path(path).stem.replace("__", "_")
    m = re.search(r"([A-Za-z]{3})[\W_](\d{2,4})", name)
    if m:
        mon = m.group(1).capitalize()
        yr = m.group(2)[-2:]
        return f"{mon}-{yr}"
    return "Unknown"


def r1(v: float) -> float:
    return round(v, 1)


# ── main ──────────────────────────────────────────────────────────────────────

def main(xlsx_path: str, out_path: str) -> None:
    print(f"Loading {xlsx_path} …")

    # ── Promo sheet ───────────────────────────────────────────────────────────
    df = pd.read_excel(xlsx_path, sheet_name="Promo ", header=0, engine="openpyxl")
    df = df.dropna(subset=["Chain Name"])
    df["_chain"] = df["Chain Name"].apply(lambda x: _norm_chain(str(x)))
    df["_brand"] = df["Brand"].apply(_norm_brand)
    df["_category"] = df["Category"].fillna("Unknown").astype(str).str.strip()
    df["_offer_pct"] = df["Offer to consumer"].apply(_parse_offer_pct)

    # ── Chain Update sheet (KAM accountability) ───────────────────────────────
    kam_map: dict[str, dict] = {}
    try:
        ck = pd.read_excel(xlsx_path, sheet_name="Chain Update ", header=0,
                           engine="openpyxl")
        ck = ck.dropna(subset=["Chain Name"])
        for _, row in ck.iterrows():
            canon = _norm_chain(str(row["Chain Name"]))
            kam = str(row.get("KAM", "")).strip()
            status = str(row.get("Remarks", "")).strip()
            received = "received" in status.lower()
            kam_map[canon] = {"kam": kam, "status": status, "received": received}
    except Exception as exc:
        print(f"  Warning: could not read Chain Update sheet: {exc}")

    # ── by_chain ──────────────────────────────────────────────────────────────
    by_chain: list[dict] = []
    for chain, grp in df.groupby("_chain"):
        offers = grp["_offer_pct"].dropna()
        entry: dict = {
            "name": chain,
            "skus": len(grp),
            "brands": int(grp["_brand"].nunique()),
            "categories": int(grp["_category"].nunique()),
            "avg_offer_pct": r1(float(offers.mean())) if len(offers) > 0 else None,
            "offer_parseable_pct": int(round(len(offers) / len(grp) * 100)),
        }
        if chain in kam_map:
            entry["kam"] = kam_map[chain]["kam"]
            entry["received"] = kam_map[chain]["received"]
        by_chain.append(entry)
    by_chain.sort(key=lambda d: -d["skus"])

    # ── by_brand ──────────────────────────────────────────────────────────────
    by_brand: list[dict] = []
    for brand, grp in df.groupby("_brand"):
        offers = grp["_offer_pct"].dropna()
        by_brand.append({
            "name": brand,
            "skus": len(grp),
            "chains": int(grp["_chain"].nunique()),
            "avg_offer_pct": r1(float(offers.mean())) if len(offers) > 0 else None,
        })
    by_brand.sort(key=lambda d: -d["skus"])

    # ── by_category ───────────────────────────────────────────────────────────
    by_category: list[dict] = [
        {"name": cat, "skus": len(grp)}
        for cat, grp in df.groupby("_category")
    ]
    by_category.sort(key=lambda d: -d["skus"])

    # ── KAM accountability rollup ─────────────────────────────────────────────
    received_chains = [c for c, v in kam_map.items() if v["received"]]
    pending_chains = [c for c, v in kam_map.items() if not v["received"]]

    detail = {
        "month": _infer_month(xlsx_path),
        "source": Path(xlsx_path).name,
        "total_skus": len(df),
        "chains_in_promo": int(df["_chain"].nunique()),
        "brands_in_promo": int(df["_brand"].nunique()),
        "chains_received": len(received_chains),
        "chains_pending": len(pending_chains),
        "by_chain": by_chain,
        "by_brand": by_brand,
        "by_category": by_category,
        "kam_status": {
            "received": received_chains,
            "pending": pending_chains,
        },
    }

    print(f"\nPromo detail summary ({detail['month']}):")
    print(f"  SKUs: {detail['total_skus']}")
    print(f"  Chains in promo: {detail['chains_in_promo']}")
    print(f"  KAM responses — received: {detail['chains_received']}, "
          f"pending: {detail['chains_pending']}")
    print(f"  Brands: {detail['brands_in_promo']}")
    for c in by_chain:
        offer_str = f"{c['avg_offer_pct']}%" if c["avg_offer_pct"] else "–"
        print(f"    {c['name']!s:25s}: {c['skus']:4d} SKUs | offer {offer_str}")

    # ── patch data.js ─────────────────────────────────────────────────────────
    data_path = Path(out_path)
    txt = data_path.read_text(encoding="utf-8")
    obj = json.loads(txt[txt.index("{"):txt.rstrip().rstrip(";").rindex("}") + 1])
    obj["promo"]["detail"] = detail
    data_path.write_text(
        "window.DASH = " + json.dumps(obj, indent=1, ensure_ascii=False) + ";\n",
        encoding="utf-8",
    )
    print(f"\nPatched {out_path} — promo.detail written.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--xlsx", required=True,
                    help="Path to Promo_Aug__2026.xlsx (or any Promo_<Month>_<YY>.xlsx)")
    ap.add_argument("--out", default="dashboard/data.js", help="Path to data.js")
    args = ap.parse_args()
    main(args.xlsx, args.out)
