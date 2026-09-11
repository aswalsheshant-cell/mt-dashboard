#!/usr/bin/env python3
"""Consolidate DMS (Massit) sales against chain sales, and publish AGGREGATES ONLY.

Why this is a separate script
----------------------------
The DMS extracts, the WoA hierarchy sheet and the employee master carry client
names, employee names and employee IDs. This repo publishes dashboard/ to
GitHub Pages, so none of that may reach data.js. This script reads those files
from OUTSIDE the repo and writes only non-identifying aggregates:
chain-type totals, coverage counts, and a reconciliation. No client name, no
employee name, no employee ID is ever emitted.

What it establishes
-------------------
Chain sales is authoritative; DMS is a gap-fill source, never additive. On
Jun-26, 98.8% of DMS tertiary belongs to chains that already have chain-sales
coverage -- adding the two would overstate the month by about Rs 35.6 Cr. DMS
earns its place here through store grain and employee attribution, not through
extra sales.

Usage:
  python scripts/ingest_massit_sales.py --massit <dir-or-file> [--massit <...>] \\
      [--woa <woa.csv>] [--out dashboard/data.js] [--dry-run]
"""
from __future__ import annotations
import argparse, csv, importlib.util, json, sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PREFIX = "window.DASH = "

# DMS client-type -> chain name as the offtake block spells it. Only aliases a
# human can verify by eye; anything unlisted stays UNMAPPED rather than guessed.
CLIENT_TYPE_TO_CHAIN = {
    "D-Mart": "DMart", "Reliance": "Reliance Retail", "Metro Cnc": "Metro C&C",
    "H&G": "Health & Glow", "RMT": "Sancus (RMT)", "Spencer": "Spencer",
    "V Mart": "V-Mart", "Walmart": "Walmart",
    "Lulu Common": "Lulu", "Lulu Daily": "Lulu",
    "Lulu Hyper (ME)": "Lulu", "Lulu TDC": "Lulu",
}


def load_builder():
    spec = importlib.util.spec_from_file_location("bdd", REPO / "scripts" / "build_dashboard_data.py")
    m = importlib.util.module_from_spec(spec); sys.modules["bdd"] = m
    spec.loader.exec_module(m); return m


def read_data_js(p: Path) -> dict:
    src = p.read_text(encoding="utf-8")
    return json.loads(src[src.index("{"):].rstrip().rstrip(";"))


def massit_files(paths):
    out = []
    for p in paths:
        q = Path(p)
        out.extend(sorted(q.glob("*.csv")) if q.is_dir() else [q])
    return [f for f in out if f.exists()]


def read_massit(files, cfg, b):
    """Rows for the consolidator + per-month coverage. Emits no identifiers."""
    measure = ((cfg.get("sales_actuals") or {}).get("massit_measure")) or "TotalTertiaryValue"
    rows, months = [], defaultdict(lambda: {"rows": 0, "clients": set(), "value": 0.0,
                                            "zones_raw": set(), "unmatched_zones": set()})
    for f in files:
        with open(f, newline="", encoding="utf-8-sig") as fh:
            for r in csv.DictReader(fh):
                mon = (r.get("Month") or "").strip()
                if not mon:
                    continue
                try:
                    v = float(r.get(measure) or 0)
                except (TypeError, ValueError):
                    v = 0.0
                cid = (r.get("Client_Id") or "").strip()
                ct = (r.get("Client Type") or "").strip()
                zc, ok = b.canon_zone_name(r.get("Zone"), cfg)
                m = months[mon]
                m["rows"] += 1; m["value"] += v
                if cid:
                    m["clients"].add(cid)
                if zc:
                    m["zones_raw"].add(zc)
                    if not ok:
                        m["unmatched_zones"].add(str(r.get("Zone")).strip())
                rows.append({"month": mon, "client_id": cid, "client_type": ct,
                             "chain": CLIENT_TYPE_TO_CHAIN.get(ct), "zone": zc, "value": v})
    return rows, months


def read_woa_client_ids(path: Path):
    """Client Ids only -- names in this sheet are deliberately not read."""
    if not path or not path.exists():
        return set()
    raw = list(csv.reader(open(path, encoding="utf-8-sig")))
    hdr = next((i for i, r in enumerate(raw[:12]) if "Client Id" in [c.strip() for c in r]), None)
    if hdr is None:
        return set()
    idx = {c.strip(): i for i, c in enumerate(raw[hdr]) if c.strip()}
    ci, sn = idx.get("Client Id"), idx.get("S.No")
    out = set()
    for r in raw[hdr + 1:]:
        if sn is None or len(r) <= max(ci, sn) or not r[sn].strip().isdigit():
            continue
        if r[ci].strip():
            out.add(r[ci].strip())
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--massit", action="append", required=True)
    ap.add_argument("--woa")
    ap.add_argument("--out", default="dashboard/data.js")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    b = load_builder()
    cfg = b.load_analytics_config(REPO)
    outp = REPO / a.out if not Path(a.out).is_absolute() else Path(a.out)
    data = read_data_js(outp)

    files = massit_files(a.massit)
    if not files:
        print("No DMS files found."); return 2
    print(f"DMS files: {', '.join(f.name for f in files)}")

    rows, months = read_massit(files, cfg, b)
    woa = read_woa_client_ids(Path(a.woa)) if a.woa else set()

    # Chain sales for the FY the DMS months fall in.
    off = data.get("offtake") or {}
    tags = {b.fy_tag_from_label(m) for m in months} - {None}
    fy = sorted(tags, key=b.fy_start_year)[-1] if tags else None
    chain_rows = {r["name"]: r.get(fy.lower()) for r in (off.get("by_chain") or [])
                  if fy and (r.get(fy.lower()) or 0) > 0}
    if not chain_rows:
        print(f"No chain sales for {fy}; cannot establish coverage."); return 2
    # chain sales is INR Lakh in data.js; DMS is rupees. Compare in rupees.
    chain_rupees = {k: (v or 0) * 100000 for k, v in chain_rows.items()}

    blk = b.sales_actuals_block(chain_rupees, rows, cfg)
    per_month = {}
    for mon, m in sorted(months.items()):
        mr = [r for r in rows if r["month"] == mon]
        mb = b.sales_actuals_block(chain_rupees, mr, cfg)
        per_month[mon] = {
            "dms_rows": m["rows"], "dms_clients": len(m["clients"]),
            "dms_value": b.r2(m["value"]),
            "duplicate_excluded": mb["massit_duplicate_excluded"],
            "gap_fill": mb["massit_gap_fill"], "unmapped": mb["massit_unmapped"],
            "clients_in_hierarchy": len(m["clients"] & woa) if woa else None,
            "hierarchy_coverage_pct": (b.r2(len(m["clients"] & woa) / len(woa) * 100)
                                       if woa and m["clients"] else None),
            "unmatched_zone_spellings": sorted(m["unmatched_zones"])[:10],
        }
    blk["by_month"] = per_month
    blk["months_present"] = sorted(months)
    blk["fy_tag"] = fy
    blk["hierarchy_stores"] = len(woa) or None
    # Period honesty: chain sales here is the whole FY window the offtake block
    # publishes, while DMS covers only the months supplied. Saying so stops the
    # consolidated figure being read as a like-for-like total.
    chain_months = off.get(f"months_{fy.lower()}") or []
    dms_months = sorted(months)
    blk["chain_sales_period"] = chain_months
    blk["dms_period"] = dms_months
    missing = [m for m in chain_months if m not in dms_months]
    blk["period_aligned"] = not missing
    if missing:
        blk["period_warning"] = (
            f"Chain sales covers {', '.join(chain_months)}; DMS covers only "
            f"{', '.join(dms_months)}. Missing DMS months: {', '.join(missing)}. "
            f"consolidated_actual is therefore NOT a like-for-like total -- it is "
            f"chain sales for the full window plus DMS gap-fill for the months "
            f"supplied. Supply the missing DMS months before using it as one number.")
    blk["privacy"] = ("Aggregates only. No client name, employee name or employee ID is "
                      "emitted here. Source extracts stay outside the repo.")

    data["sales_actuals"] = blk
    data["readiness"] = b.readiness_gate(data, cfg)

    print(f"\n  months            : {', '.join(blk['months_present'])}")
    print(f"  chain sales       : Rs {blk['chain_sales']/1e7:,.2f} Cr ({blk['chains_with_chain_sales']} chains)")
    print(f"  DMS gap-fill      : Rs {blk['massit_gap_fill']/1e7:,.2f} Cr")
    print(f"  DMS duplicate     : Rs {blk['massit_duplicate_excluded']/1e7:,.2f} Cr  (EXCLUDED)")
    print(f"  DMS unmapped      : Rs {blk['massit_unmapped']/1e7:,.2f} Cr  (exception)")
    print(f"  consolidated      : Rs {blk['consolidated_actual']/1e7:,.2f} Cr")
    print(f"  double count avoided: Rs {blk['double_count_avoided']/1e7:,.2f} Cr")
    print(f"  reconciliation    : {blk['reconciliation']['status']}")
    if blk.get("period_warning"):
        print(f"  ! PERIOD MISMATCH : chain {', '.join(blk['chain_sales_period'])} vs "
              f"DMS {', '.join(blk['dms_period'])}")

    if a.dry_run:
        print("\n(--dry-run: nothing written)"); return 0
    outp.write_text(PREFIX + json.dumps(data, ensure_ascii=False, indent=1) + ";\n", encoding="utf-8")
    print(f"\nWrote {outp} ({outp.stat().st_size/1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
