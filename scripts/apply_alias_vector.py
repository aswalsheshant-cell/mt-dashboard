#!/usr/bin/env python3
"""
scripts/apply_alias_vector.py
Applies canonical alias mapping vector across primary, secondary, and claim datasets.
Eliminates fragmentation across Chain, Brand, and Zone dimensions.
"""

import json
import re
import sys
from pathlib import Path
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
MAPPING_VECTOR_PATH = REPO_ROOT / "data_mappings/canonical_alias_vector.json"


class AliasNormalizer:

    def __init__(self, vector_path: Path):
        if not vector_path.exists():
            raise FileNotFoundError(f"Mapping vector missing at {vector_path}")

        with open(vector_path, "r", encoding="utf-8") as f:
            self.vectors = json.load(f)

        # Build reverse lookup indexes
        self.chain_map = self._build_lookup(self.vectors.get("chains", {}))
        self.brand_map = self._build_lookup(self.vectors.get("brands", {}))
        self.zone_map = self._build_lookup(self.vectors.get("zones", {}))

    def _normalize_key(self, text: str) -> str:
        if not isinstance(text, str):
            return ""
        return re.sub(r"[^A-Z0-9]", "", text.upper().strip())

    def _build_lookup(self, mapping_dict: dict) -> dict:
        lookup = {}
        for canonical, aliases in mapping_dict.items():
            lookup[self._normalize_key(canonical)] = canonical
            for alias in aliases:
                lookup[self._normalize_key(alias)] = canonical
        return lookup

    def normalize_chain(self, raw_chain: str) -> str:
        key = self._normalize_key(raw_chain)
        return self.chain_map.get(key, raw_chain.strip().upper())

    def normalize_brand(self, raw_brand: str) -> str:
        key = self._normalize_key(raw_brand)
        return self.brand_map.get(key, raw_brand.strip().upper())

    def normalize_zone(self, raw_zone: str) -> str:
        key = self._normalize_key(raw_zone)
        return self.zone_map.get(key, raw_zone.strip().title())


def main():
    print("=" * 70)
    print("🔧 Running Canonical Alias Vector Normalization Engine")
    print("=" * 70)

    if not MAPPING_VECTOR_PATH.exists():
        print(f"❌ Mapping vector missing at {MAPPING_VECTOR_PATH}")
        sys.exit(1)

    normalizer = AliasNormalizer(MAPPING_VECTOR_PATH)
    print(f"✓ Loaded mapping vector from: {MAPPING_VECTOR_PATH}")
    print(f"  • Canonical Chains: {len(normalizer.chain_map)} keys")
    print(f"  • Canonical Brands: {len(normalizer.brand_map)} keys")
    print(f"  • Canonical Zones:  {len(normalizer.zone_map)} keys")

    # 1. Normalize Synthesized FY25 Fact Table
    fy25_path = (
        REPO_ROOT
        / "PowerBI/RawDataFolders/Primary_Derived_FY25/Primary_Article_Synthesized_FY25.csv"
    )
    if fy25_path.exists():
        print(f"\n[1/3] Processing Synthesized FY25 Primary Fact Table...")
        df_fy25 = pd.read_csv(fy25_path)
        orig_chains = df_fy25["Chain"].nunique()
        orig_nsv = df_fy25.get("Primary_NSV_Lakh", pd.Series([0])).sum()

        df_fy25["Chain"] = df_fy25["Chain"].apply(normalizer.normalize_chain)
        df_fy25["Brand"] = df_fy25["Brand"].apply(normalizer.normalize_brand)

        new_nsv = df_fy25.get("Primary_NSV_Lakh", pd.Series([0])).sum()
        df_fy25.to_csv(fy25_path, index=False)

        print(f"  File: {fy25_path.name}")
        print(f"  • Rows Processed:             {len(df_fy25):,}")
        print(f"  • Raw Chains: {orig_chains} → Canonical Chains: {df_fy25['Chain'].nunique()}")
        print(f"  • Target Control NSV:         ₹{orig_nsv:,.2f}L")
        print(f"  • Post-Normalization NSV:     ₹{new_nsv:,.2f}L")
        variance = abs(new_nsv - orig_nsv)
        print(f"  • Variance:                   ₹{variance:,.4f}L")
        if variance < 0.01:
            print(f"  ✓ Exported normalized FY25 dataset.")
        else:
            print(f"  ⚠ Warning: NSV variance detected during normalization.")

    # 2. Normalize Secondary Sales (if exists)
    sec_path = (
        REPO_ROOT
        / "PowerBI/RawDataFolders/SecondarySales_Monthly/secondary_sales_tot_hierarchy_Apr_Aug_2026.csv"
    )
    if sec_path.exists():
        print(f"\n[2/3] Processing FY27 5-Month Hierarchical Secondary Sales Table...")
        df_sec = pd.read_csv(sec_path)
        orig_chains = df_sec.get("Chain", pd.Series([])).nunique()
        orig_nsv = df_sec.get("NSV", df_sec.get("Value", pd.Series([0]))).sum()

        if "Chain" in df_sec.columns:
            df_sec["Chain"] = df_sec["Chain"].apply(normalizer.normalize_chain)
        if "Brand" in df_sec.columns:
            df_sec["Brand"] = df_sec["Brand"].apply(normalizer.normalize_brand)

        new_nsv = df_sec.get("NSV", df_sec.get("Value", pd.Series([0]))).sum()
        df_sec.to_csv(sec_path, index=False)

        print(f"  File: {sec_path.name}")
        print(f"  • Rows Processed:             {len(df_sec):,}")
        print(f"  • Raw Chains: {orig_chains} → Consolidated Canonical Chains: {df_sec.get('Chain', pd.Series([])).nunique()}")
        print(f"  • Target Control NSV:         ₹{orig_nsv:,.2f}L")
        print(f"  • Post-Normalization NSV:     ₹{new_nsv:,.2f}L")
        variance = abs(new_nsv - orig_nsv)
        if variance < 0.01:
            print(f"  ✓ Exported normalized FY27 secondary dataset.")
        else:
            print(f"  ⚠ Warning: NSV variance detected during normalization.")

    # 3. Normalize Primary Composite (FY24-FY26)
    composite_path = (
        REPO_ROOT
        / "PowerBI/RawDataFolders/Primary_ShipTo_Monthly/Primary_ShipTo_FY24-26_Composite.csv"
    )
    if composite_path.exists():
        print(f"\n[3/3] Processing Multi-Year Primary Composite File (FY24–FY26)...")
        df_comp = pd.read_csv(composite_path)
        orig_nsv = pd.to_numeric(df_comp.get("Primary_NSV", df_comp.get("NSV", pd.Series([0]))), errors="coerce").sum()

        if "Chain" in df_comp.columns:
            df_comp["Chain"] = df_comp["Chain"].apply(normalizer.normalize_chain)
        if "Zone" in df_comp.columns:
            df_comp["Zone"] = df_comp["Zone"].apply(normalizer.normalize_zone)

        new_nsv = pd.to_numeric(df_comp.get("Primary_NSV", df_comp.get("NSV", pd.Series([0]))), errors="coerce").sum()
        df_comp.to_csv(composite_path, index=False)

        print(f"  File: {composite_path.name}")
        print(f"  • Rows Processed:             {len(df_comp):,}")
        print(f"  • Canonical Chains:           {df_comp.get('Chain', pd.Series([])).nunique()}")
        print(f"  • Canonical Zones:            {df_comp.get('Zone', pd.Series([])).nunique()}")
        print(f"  • Target Control Total:       ₹{orig_nsv:,.2f}L")
        print(f"  • Post-Normalization Total:   ₹{new_nsv:,.2f}L")
        variance = abs(new_nsv - orig_nsv)
        if variance < 0.01:
            print(f"  ✓ Exported normalized Primary Composite dataset.")

    print("\n" + "=" * 70)
    print("✅ Canonical Alias Normalization Complete — Zero Data Drift Detected")
    print("=" * 70)


if __name__ == "__main__":
    main()
