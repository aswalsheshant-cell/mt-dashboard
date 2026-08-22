#!/usr/bin/env python3
"""
Patch Primary_ShipTo_FY25-26_to_May26.csv with July-2026 entries for
(ShipTo, "The Derma Co") combos that are missing because the brand was
not previously routed through these distributors.

Root cause: every unmapped July Dist. row is "The Derma Co" (+ two small
ShipTos with genuinely unknown chains). For all solvable cases, the chain
split is inferred from the same ShipTo's most-recent entries for other brands.

Genuinely unknown (no chain data anywhere): PLANET SERVICES-MT-DL, TROY TRADEX
→ skipped with a warning; these ₹22.4 L remain in "Unmapped Chain" until
   the business provides secondary data.

Usage: python scripts/patch_shipto_derma_co_jul26.py [--dry-run]
"""
from __future__ import annotations
import argparse, sys
from pathlib import Path
import pandas as pd

REPO = Path(__file__).resolve().parent.parent
SHIPTO_CSV = REPO / "PowerBI/RawDataFolders/Primary_ShipTo_Monthly/Primary_ShipTo_FY25-26_to_May26.csv"
JUL_CSV    = REPO / "PowerBI/RawDataFolders/Primary_Article_Monthly/primary_article_Jul_26.csv"

SKIP_SHIPTOS = {
    "planet services-mt-dl",   # chain unknown — <<FILL>> in patch proposal
    "troy tradex",             # chain unknown — <<FILL>> in patch proposal
}

def main(dry_run: bool = False):
    shipto = pd.read_csv(SHIPTO_CSV, low_memory=False)
    jul    = pd.read_csv(JUL_CSV, low_memory=False)

    # Normalise keys
    shipto.columns = [c.strip() for c in shipto.columns]
    jul.columns    = [c.strip() for c in jul.columns]

    sh_dist = shipto[
        shipto["Direct/Distributor"].astype(str).str.strip().str.lower().isin(["dist.", "dist"])
    ].copy()
    sh_dist["_st"] = sh_dist["Ship To Name"].astype(str).str.strip().str.lower()
    sh_dist["_bl"] = sh_dist["Brand"].astype(str).str.strip().str.lower()

    jul_dist = jul[
        jul["PO Type"].astype(str).str.strip().str.lower().isin(["dist.", "dist"])
    ].copy()
    jul_dist["_st"] = jul_dist["Ship To Name"].astype(str).str.strip().str.lower()
    jul_dist["_bl"] = jul_dist["brand"].astype(str).str.strip().str.lower()

    csv_keys = set(zip(sh_dist["_st"], sh_dist["_bl"]))
    missing  = {
        (st, bl) for st, bl in zip(jul_dist["_st"], jul_dist["_bl"])
        if (st, bl) not in csv_keys
    }

    new_rows: list[dict] = []
    skipped:  list[tuple] = []
    month_str = "Jul'26"
    month_start = "2026-07-01"
    fy_year = "FY_26-27"

    print(f"Missing (ShipTo, Brand) combos in July Dist: {len(missing)}\n")

    for st_lower, bl_lower in sorted(missing, key=lambda x: x[0]):
        if st_lower in SKIP_SHIPTOS:
            nsv = jul_dist[(jul_dist["_st"]==st_lower) & (jul_dist["_bl"]==bl_lower)][
                "Inv. Net value(LOC)"].sum() / 1e5
            skipped.append((st_lower, bl_lower, nsv))
            continue

        # Raw names for output (preserve capitalisation from July CSV)
        raw_st = jul_dist[jul_dist["_st"]==st_lower]["Ship To Name"].iloc[0].strip()
        raw_bl = jul_dist[jul_dist["_bl"]==bl_lower]["brand"].iloc[0].strip()

        # Most-recent chain allocation for this ShipTo across all brands in the CSV
        shipto_history = sh_dist[sh_dist["_st"]==st_lower].copy()
        if shipto_history.empty:
            skipped.append((st_lower, bl_lower,
                           jul_dist[(jul_dist["_st"]==st_lower) & (jul_dist["_bl"]==bl_lower)][
                               "Inv. Net value(LOC)"].sum() / 1e5))
            print(f"  SKIP {raw_st} | {raw_bl} — no history in CSV")
            continue

        # Group by Chain, take mean Cont% across brands/months → normalise
        chain_weights = (shipto_history
                         .groupby("Chain")["Cont%"].mean()
                         .rename("raw_cont"))
        chain_weights = chain_weights / chain_weights.sum()  # normalise to 1.0

        # Grab Zone/State from the most recent row for this ShipTo
        latest = shipto_history.sort_values("MonthStart", ascending=False).iloc[0]
        zone  = latest["Zone"]
        state = latest["State"]

        nsv_total = (jul_dist[(jul_dist["_st"]==st_lower) & (jul_dist["_bl"]==bl_lower)]
                     ["Inv. Net value(LOC)"].sum())

        print(f"  ADD {raw_st} | {raw_bl} | ₹{nsv_total/1e5:.2f} L")
        for chain, cont_frac in chain_weights.items():
            print(f"       → {chain}: {cont_frac:.4f}")
            new_rows.append({
                "Month":               month_str,
                "MonthStart":          month_start,
                "FY Year":             fy_year,
                "Ship To Name":        raw_st,
                "Direct/Distributor":  "Dist.",
                "Chain":               chain,
                "Zone":                zone,
                "State":               state,
                "Brand":               raw_bl,
                "Primary NSV":         round(nsv_total * cont_frac, 2),
                "MRP Value":           "",
                "Cont%":               round(cont_frac, 6),
            })

    print(f"\n── Summary ──────────────────────────────────────────────")
    print(f"New rows to add: {len(new_rows)}")
    print(f"Skipped (chain unknown): {len(skipped)}")
    for st, bl, nsv in skipped:
        print(f"  SKIP: {st} | {bl} | ₹{nsv:.2f} L")

    total_skipped_nsv = sum(nsv for _, _, nsv in skipped)
    print(f"  Total skipped NSV: ₹{total_skipped_nsv:.2f} L (will remain Unmapped Chain)")

    if dry_run:
        print("\n[dry-run] Stopping before write.")
        return

    if not new_rows:
        print("Nothing to write.")
        return

    new_df = pd.DataFrame(new_rows, columns=list(shipto.columns))
    extended = pd.concat([shipto, new_df], ignore_index=True)
    extended.to_csv(SHIPTO_CSV, index=False)
    print(f"\nWrote {len(new_df)} new rows to {SHIPTO_CSV.name}  "
          f"(total rows now: {len(extended)})")

if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dry-run", action="store_true",
                   help="Print what would be added without writing")
    args = p.parse_args()
    main(dry_run=args.dry_run)
