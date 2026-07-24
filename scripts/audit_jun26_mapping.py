#!/usr/bin/env python3
"""
June'26 Mapping Audit — Step 2 of the June 2026 data onboarding.

Run AFTER split_primary_article_xlsb.py has produced primary_article_Jun_26.csv.
Compares the Jun'26 primary CSV against all existing mapping files and prints
a clear pass/fail report with the exact rows to add for any new keys found.

Usage:
    python scripts/audit_jun26_mapping.py

Reads:
    PowerBI/RawDataFolders/Primary_Article_Monthly/primary_article_Jun_26.csv
    PowerBI/SeedData/Mapping/ChainAccount_Mapping_Inferred.csv
    PowerBI/SeedData/Mapping/CustomerCode_Zone_State_Mapping.csv
    scripts/build_dashboard_data.py  (CHAIN_ALIASES dict)

Outputs:
    Console report — pass/fail per check, with new-row templates ready to paste.
"""
from __future__ import annotations
import csv, re, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

def load_csv(path: Path) -> list[dict]:
    if not path.exists():
        print(f"  MISSING: {path.relative_to(REPO)}")
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def col(row: dict, *candidates: str) -> str:
    """Return first matching column value (case-insensitive partial match)."""
    for c in candidates:
        for k in row:
            if c.lower() in k.lower():
                return str(row[k]).strip()
    return ""


# ---------------------------------------------------------------------------
def main():
    jun_path = REPO / "PowerBI/RawDataFolders/Primary_Article_Monthly/primary_article_Jun_26.csv"
    if not jun_path.exists():
        print("❌  primary_article_Jun_26.csv not found.")
        print(f"    Expected at: {jun_path}")
        print("    Run split_primary_article_xlsb.py first.")
        sys.exit(1)

    print("=" * 70)
    print("  June'26 Mapping Audit")
    print("=" * 70)

    # -- Load Jun'26 CSV ----------------------------------------------------
    jun_rows = load_csv(jun_path)
    print(f"\n✅  Loaded primary_article_Jun_26.csv  ({len(jun_rows):,} rows)\n")

    # Column discovery
    sample = jun_rows[0] if jun_rows else {}
    chain_col  = next((c for c in sample if "chain" in c.lower()), None)
    shipto_col = next((c for c in sample if "ship" in c.lower() and "to" in c.lower()), None)
    sap_col    = next((c for c in sample if "cust" in c.lower() and "sap" in c.lower()), None)
    zone_col   = next((c for c in sample if c.strip().lower() == "zone"), None)
    state_col  = next((c for c in sample if c.strip().lower() == "state"), None)
    potype_col = next((c for c in sample if "direct" in c.lower() or "po type" in c.lower()), None)

    print(f"  Column map detected:")
    print(f"    Chain   → {chain_col!r}")
    print(f"    Ship-To → {shipto_col!r}")
    print(f"    SAP     → {sap_col!r}")
    print(f"    Zone    → {zone_col!r}")
    print(f"    State   → {state_col!r}")
    print(f"    PO Type → {potype_col!r}\n")

    # Unique keys in Jun'26
    from collections import defaultdict
    jun_chains:  dict[str, int] = defaultdict(int)
    jun_shipto:  dict[str, dict] = {}   # shipto -> {chain, zone, state, potype}
    jun_sap:     dict[str, dict] = {}   # sap_code -> {name, chain, zone, state}

    for r in jun_rows:
        ch  = r[chain_col].strip()  if chain_col  else ""
        st  = r[shipto_col].strip() if shipto_col else ""
        sap = r[sap_col].strip()    if sap_col    else ""
        zo  = r[zone_col].strip()   if zone_col   else ""
        sta = r[state_col].strip()  if state_col  else ""
        pt  = r[potype_col].strip() if potype_col else ""

        jun_chains[ch] += 1
        if st and st not in jun_shipto:
            jun_shipto[st] = {"chain": ch, "zone": zo, "state": sta, "potype": pt}
        if sap and sap not in jun_sap:
            jun_sap[sap] = {"shipto": st, "chain": ch, "zone": zo, "state": sta}

    print(f"  Jun'26 unique values:")
    print(f"    Chains:    {len(jun_chains)}")
    print(f"    Ship-Tos:  {len(jun_shipto)}")
    print(f"    SAP codes: {len(jun_sap)}")

    # -----------------------------------------------------------------------
    # CHECK 1 — New chain names vs existing mapping + CHAIN_ALIASES in build script
    # -----------------------------------------------------------------------
    print("\n" + "-" * 70)
    print("CHECK 1 — Chain names")
    print("-" * 70)

    mapped_chains: set[str] = set()
    for r in load_csv(REPO / "PowerBI/SeedData/Mapping/ChainAccount_Mapping_Inferred.csv"):
        mapped_chains.add(r.get("Chain Name", "").strip())

    # Also extract CHAIN_ALIASES from build script
    build_src = (REPO / "scripts/build_dashboard_data.py").read_text(encoding="utf-8")
    alias_m = re.search(r"CHAIN_ALIASES\s*=\s*\{([^}]+)\}", build_src, re.DOTALL)
    alias_keys: set[str] = set()
    if alias_m:
        for line in alias_m.group(1).splitlines():
            m2 = re.match(r'\s*["\']([^"\']+)["\']', line.strip())
            if m2:
                alias_keys.add(m2.group(1).strip().lower())

    # Distributor chains need ChainAccount mapping; direct chains map to themselves
    dist_chains = {ch for ch, info in jun_shipto.items()
                   if "dist" in (info.get("potype","") or "").lower()}
    new_dist = dist_chains - mapped_chains
    new_all  = set(jun_chains.keys()) - mapped_chains

    direct_new = new_all - dist_chains

    if direct_new:
        print(f"\n  ℹ️   New DIRECT chains ({len(direct_new)}) — self-mapping, no ChainAccount row needed:")
        for c in sorted(direct_new):
            print(f"        {c}  ({jun_chains[c]:,} rows)")

    if new_dist:
        print(f"\n  ⚠️   New DISTRIBUTOR chains ({len(new_dist)}) — need ChainAccount_Mapping_Inferred.csv rows:")
        for c in sorted(new_dist):
            print(f"        {c}")
        print("\n  Template rows to add to ChainAccount_Mapping_Inferred.csv:")
        print(f"  Chain Name,Ship-To Name,Bill-To / Account (inferred),Direct/Distributor,"
              f"Brand,Month Logic,Months Covered,Month Range,Avg Cont%,Min Cont%,Max Cont%,"
              f"Mapping Confidence,Remarks,Validation Status")
        for c in sorted(new_dist):
            info = next((v for k, v in jun_shipto.items() if v["chain"] == c), {})
            print(f"  {c},<Ship-To Name>,<Account>,Dist.,ALL,TBD,1,Jun'26–Jun'26,,,,Low,"
                  f"NEW in Jun'26 — validate Cont%,Pending")
    else:
        print(f"  ✅  No new distributor chains — ChainAccount mapping is complete.")

    # Check CHAIN_ALIASES coverage
    new_alias_needed = {ch for ch in jun_chains
                        if ch.lower() not in alias_keys
                        and "dist" not in (jun_shipto.get(ch,{}).get("potype","") or "").lower()}
    if new_alias_needed:
        print(f"\n  ℹ️   Chains to verify in CHAIN_ALIASES (build script):")
        for c in sorted(new_alias_needed):
            print(f"        {repr(c)}")
    else:
        print(f"  ✅  CHAIN_ALIASES covers all Jun'26 chains.")

    # -----------------------------------------------------------------------
    # CHECK 2 — New SAP codes vs CustomerCode_Zone_State_Mapping
    # -----------------------------------------------------------------------
    print("\n" + "-" * 70)
    print("CHECK 2 — Customer SAP codes")
    print("-" * 70)

    mapped_sap: set[str] = set()
    for r in load_csv(REPO / "PowerBI/SeedData/Mapping/CustomerCode_Zone_State_Mapping.csv"):
        mapped_sap.add(r.get("Customer Code", "").strip())

    new_sap = {k: v for k, v in jun_sap.items() if k and k not in mapped_sap}
    if new_sap:
        print(f"\n  ⚠️   {len(new_sap)} new SAP codes not in CustomerCode_Zone_State_Mapping.csv:")
        print(f"\n  Template rows to add:")
        print(f"  Customer Code,Customer Name / Ship-to Name,State,Zone,City / Location,"
              f"Business Region / Sub-region,Chain Name,Account,Channel,Mapping Source,"
              f"Validation Status,Remarks")
        for code, info in sorted(new_sap.items())[:20]:
            print(f"  {code},{info['shipto']},{info['state']},{info['zone']},,,"
                  f"{info['chain']},,Direct,Customer Code,Pending,NEW in Jun'26")
        if len(new_sap) > 20:
            print(f"  ... ({len(new_sap) - 20} more — see full output)")
    else:
        print(f"  ✅  All {len(jun_sap)} SAP codes already in CustomerCode_Zone_State_Mapping.csv.")

    # -----------------------------------------------------------------------
    # CHECK 3 — New Ship-To names vs ShipToMaster
    # -----------------------------------------------------------------------
    print("\n" + "-" * 70)
    print("CHECK 3 — Ship-To names")
    print("-" * 70)

    shipto_master = load_csv(REPO / "PowerBI/SeedData/Masters/ShipToMaster.csv")
    mapped_shipto = {r.get("Ship To Name","").strip() for r in shipto_master}
    new_shipto = {k: v for k, v in jun_shipto.items() if k and k not in mapped_shipto}
    if new_shipto:
        print(f"\n  ℹ️   {len(new_shipto)} Ship-To names not in ShipToMaster.csv "
              f"(informational — ShipToMaster is not yet complete).")
    else:
        print(f"  ✅  All Ship-To names in ShipToMaster.csv.")

    # -----------------------------------------------------------------------
    # SUMMARY
    # -----------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("  AUDIT SUMMARY")
    print("=" * 70)
    blockers = []
    if new_dist:
        blockers.append(f"  ❌  {len(new_dist)} new distributor chain(s) need ChainAccount rows")
    if new_sap:
        blockers.append(f"  ❌  {len(new_sap)} new SAP codes need CustomerCode_Zone_State rows")

    if blockers:
        print("\n  BLOCKERS — fix before running --detail-only:")
        for b in blockers:
            print(b)
    else:
        print("\n  ✅  No mapping blockers found.")
        print("  Ready to run:")
        print("    python scripts/build_dashboard_data.py --detail-only \\")
        print("        --src <source-workbook-dir> --out dashboard/data.js")
        print("    python scripts/build_dashboard_data.py --offtake-patch \\")
        print("        --src PowerBI/RawDataFolders/Offtake_Monthly/ --out dashboard/data.js")

    print()


if __name__ == "__main__":
    main()
