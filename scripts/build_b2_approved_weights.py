"""
Build ChainAllocationWeights.csv from B2-approved mapping lines.

Takes the 109 owner-approved Distributor × Brand × Chain triplets and extracts
monthly NSV detail from the ChainWisePrimarySale Dump Snapshot. For any
Distributor × Brand pair with at least one approved chain, ALL chains from the
dump are included (the dump ratios are from the same business-maintained source).
All-pending groups get no allocation (no weights entry).

Output is the governed weights file that load_chain_allocation_weights() in
build_dashboard_data.py reads as its first-priority source.

Usage:
    python scripts/build_b2_approved_weights.py

Reads:
    docs/evidence/B2/ProvisionalMapping_Register_OwnerDecisions_Apr25_Jul26.csv
    PowerBI/SeedData/Mapping/ChainWisePrimarySale_Dump_Snapshot.csv

Writes:
    PowerBI/SeedData/DIST/ChainAllocationWeights.csv
    PowerBI/SeedData/DIST/ChainAllocationWeights_provenance.json
"""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parent.parent

REGISTER = REPO / "docs" / "evidence" / "B2" / "ProvisionalMapping_Register_OwnerDecisions_Apr25_Jul26.csv"
DUMP = REPO / "PowerBI" / "SeedData" / "Mapping" / "ChainWisePrimarySale_Dump_Snapshot.csv"
OUT = REPO / "PowerBI" / "SeedData" / "DIST" / "ChainAllocationWeights.csv"

sys.path.insert(0, str(REPO / "scripts"))
from build_dashboard_data import canon_brand, canon_chain  # noqa: E402

DUMP_TO_PRIMARY_MONTH = {
    "April'25": "Apr'25", "May'25": "May'25", "June'25": "Jun'25",
    "July'25": "Jul'25", "Aug'25": "Aug'25", "Sept'25": "Sep'25",
    "Oct'25": "Oct'25", "Nov'25": "Nov'25", "Dec'25": "Dec'25",
    "Jan'26": "Jan'26", "Feb'26": "Feb'26", "March'26": "Mar'26",
    "April'26": "Apr'26", "May'26": "May'26", "Jun'26": "Jun'26",
    "Jul'26": "Jul'26",
}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    reg = pd.read_csv(REGISTER)
    approved = reg[reg["Owner_Decision"] == "Approve"].copy()
    print(f"Register: {len(reg)} lines, Rs {reg['Value_L'].sum():.2f} L")
    print(f"Approved: {len(approved)} lines, Rs {approved['Value_L'].sum():.2f} L")

    dump = pd.read_csv(DUMP)
    dump_hash = sha256(DUMP)

    # Identify Distributor × Brand pairs with at least one approved chain
    approved["_dist"] = approved["Distributor"].str.strip().str.lower()
    approved["_brand"] = approved["Brand"].map(canon_brand)
    eligible_pairs = set(zip(approved["_dist"], approved["_brand"]))
    print(f"\nEligible Dist × Brand pairs (≥1 approved chain): {len(eligible_pairs)}")

    # Also track which specific triplets are approved for provenance
    approved["_chain"] = approved["Chain"].map(canon_chain)
    approved_triplets = set(zip(approved["_dist"], approved["_brand"], approved["_chain"]))

    # Filter dump to scope and eligible pairs
    dump_scope = dump[dump["Month"].isin(DUMP_TO_PRIMARY_MONTH)].copy()
    dump_scope["_dist"] = dump_scope["Bill to customer"].str.strip().str.lower()
    dump_scope["_brand"] = dump_scope["Brand"].map(canon_brand)
    dump_scope["_chain"] = dump_scope["Chain Name"].map(canon_chain)
    dump_scope["_pair"] = list(zip(dump_scope["_dist"], dump_scope["_brand"]))
    matched = dump_scope[dump_scope["_pair"].isin(eligible_pairs)].copy()

    # Map months
    matched["Month_primary"] = matched["Month"].map(DUMP_TO_PRIMARY_MONTH)

    # Build output
    out = pd.DataFrame({
        "Ship To Name": matched["Bill to customer"].values,
        "Brand": matched["Brand"].values,
        "Month": matched["Month_primary"].values,
        "Chain Name": matched["Chain Name"].values,
        "NSV": matched["NSV"].values,
    })
    out = out[out["NSV"] > 0].copy()

    # Tag each row as GOVERNED or PENDING for provenance
    out["_dist_lc"] = out["Ship To Name"].str.strip().str.lower()
    out["_brand_c"] = out["Brand"].map(canon_brand)
    out["_chain_c"] = out["Chain Name"].map(canon_chain)
    out["_triplet"] = list(zip(out["_dist_lc"], out["_brand_c"], out["_chain_c"]))
    governed_mask = out["_triplet"].isin(approved_triplets)

    n_governed = governed_mask.sum()
    n_pending = (~governed_mask).sum()
    gov_nsv = out.loc[governed_mask, "NSV"].sum()
    pend_nsv = out.loc[~governed_mask, "NSV"].sum()

    print(f"\nOutput rows: {len(out)}")
    print(f"  Governed (approved triplets): {n_governed} rows, Rs {gov_nsv:.2f} L")
    print(f"  Pending (same Dist×Brand, unapproved chain): {n_pending} rows, Rs {pend_nsv:.2f} L")
    print(f"  Total: Rs {out['NSV'].sum():.2f} L")

    groups = out.groupby(["Ship To Name", "Brand", "Month"])
    print(f"\nWeight groups (Ship To × Brand × Month): {len(groups)}")

    # Save (drop internal columns)
    out_clean = out[["Ship To Name", "Brand", "Month", "Chain Name", "NSV"]].copy()
    out_clean.to_csv(OUT, index=False)
    print(f"\nWritten: {OUT}")
    print(f"  Rows: {len(out_clean)}")

    # Classify groups for the all-pending remainder
    all_pending_pairs = set()
    for (d, b), g in reg.groupby(["Distributor", "Brand"]):
        if not (g["Owner_Decision"] == "Approve").any():
            all_pending_pairs.add((d.strip().lower(), canon_brand(b)))
    all_pending_val = reg[reg.apply(
        lambda r: (r["Distributor"].strip().lower(), canon_brand(r["Brand"])) in all_pending_pairs,
        axis=1,
    )]["Value_L"].sum()

    # Provenance
    provenance = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "register": str(REGISTER.relative_to(REPO)),
        "register_sha256": sha256(REGISTER),
        "dump_snapshot": str(DUMP.relative_to(REPO)),
        "dump_snapshot_sha256": dump_hash,
        "approved_lines": int(len(approved)),
        "approved_value_L": round(float(approved["Value_L"].sum()), 2),
        "eligible_dist_brand_pairs": int(len(eligible_pairs)),
        "output_rows": int(len(out_clean)),
        "output_nsv_L": round(float(out_clean["NSV"].sum()), 2),
        "governed_rows": int(n_governed),
        "governed_nsv_L": round(float(gov_nsv), 2),
        "pending_rows_in_eligible_pairs": int(n_pending),
        "pending_nsv_in_eligible_pairs_L": round(float(pend_nsv), 2),
        "all_pending_pairs": int(len(all_pending_pairs)),
        "all_pending_value_L": round(float(all_pending_val), 2),
        "weight_groups": int(len(groups)),
        "scope": "Apr'25-Jul'26 (16 months)",
        "method": (
            "B2 owner-approved Distributor × Brand × Chain triplets (109 lines). "
            "For any Dist × Brand pair with ≥1 approved chain, ALL chains from the "
            "ChainWisePrimarySale Dump Snapshot are included (preserves correct "
            "proportions). All-pending groups (32 pairs, no approved chain) get no "
            "allocation and fall back to the raw distributor tag. "
            "load_chain_allocation_weights() normalizes NSV to fractions per "
            "(Ship To, Brand, Month) group."
        ),
    }
    prov_path = OUT.parent / "ChainAllocationWeights_provenance.json"
    with open(prov_path, "w") as f:
        json.dump(provenance, f, indent=2)
    print(f"Provenance: {prov_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
