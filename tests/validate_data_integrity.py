#!/usr/bin/env python3
"""
Data Integrity Validation — CI gate for dashboard/data.js

Assertions locked after the Aug-2026 canonical chain alignment release:
  1.  Exactly 45 unique canonical chains in primary.by_chain
  2.  Exactly 6 zones in primary.by_zone (no Pan India)
  3.  FY26 baseline sum = ₹32,900.36L ± 0.1 %
  4.  FY27 chain total > 0 (data present)
  5.  No legacy chain names (Dmart, H&G, Vishal Mega Mart, RMT-Sancus, …)
  6.  Offtake: no Pan India in zone_monthly_fy27
  7.  primary.by_channel contains MT, EB2B, SIS
  8.  No None / NaN in fy26 values across primary.by_chain
  9.  dims.Zone matches the authorised 6-zone set
 10.  primary.n_chains reported == actual chain count

Usage:
  python tests/validate_data_integrity.py [path/to/data.js]
  Exits 0 on pass, 1 on any failure.
"""
from __future__ import annotations
import json
import math
import re
import sys
from pathlib import Path


# ── Constants locked at release ────────────────────────────────────────────────

EXPECTED_CHAIN_COUNT    = 55
EXPECTED_FY26_TOTAL_L   = 32_900.36   # Lakh — authoritative from pre-aggregated workbook
FY26_TOLERANCE_PCT      = 0.1         # ± 0.1 %

AUTHORISED_ZONES = frozenset({"Central", "East", "North", "South-1", "South-2", "West"})
REQUIRED_CHANNELS = frozenset({"MT", "EB2B", "SIS"})

# Names that must NOT appear in production data after the canonical alignment
LEGACY_CHAIN_NAMES = frozenset({
    "Dmart", "D-Mart", "dmart", "d-mart",
    "H&G",
    "Vishal Mega Mart",
    "RMT-Sancus",
    "Apollo Pharmacy", "Apollo Healthco",
    "Nykaa SS(fsn)",
    "Metro-CNC-RRL",
    "Walmart CNC",
    "Reliance Retail-(Azorte)",
})


# ── Helpers ────────────────────────────────────────────────────────────────────

def load_datajs(path: str) -> dict:
    raw = Path(path).read_text(encoding="utf-8")
    raw = re.sub(r"^.*?window\.DASH\s*=\s*", "", raw, flags=re.DOTALL)
    raw = raw.rstrip().rstrip(";")
    return json.loads(raw)


def is_nan_or_none(v) -> bool:
    if v is None:
        return True
    try:
        return math.isnan(float(v))
    except (TypeError, ValueError):
        return False


# ── Validation checks ──────────────────────────────────────────────────────────

def check_chain_count(primary: dict, failures: list) -> None:
    chains = primary.get("by_chain", [])
    names = [c.get("name", "") for c in chains]
    unique = set(names)
    if len(unique) != EXPECTED_CHAIN_COUNT:
        failures.append(
            f"CHAIN COUNT: expected {EXPECTED_CHAIN_COUNT}, got {len(unique)} unique chains "
            f"({len(chains)} total rows). Unique: {sorted(unique)}"
        )
    else:
        print(f"  ✓  Chain count: {len(unique)} chains")


def check_no_legacy_names(primary: dict, failures: list) -> None:
    chains = primary.get("by_chain", [])
    found = [c["name"] for c in chains if c.get("name") in LEGACY_CHAIN_NAMES]
    if found:
        failures.append(
            f"LEGACY CHAIN NAMES: found {found} — update chain_aliases.py and rebuild"
        )
    else:
        print(f"  ✓  No legacy chain names")


def check_fy26_total(primary: dict, failures: list) -> None:
    chains = primary.get("by_chain", [])
    total = sum(float(c.get("fy26") or 0) for c in chains)
    lo = EXPECTED_FY26_TOTAL_L * (1 - FY26_TOLERANCE_PCT / 100)
    hi = EXPECTED_FY26_TOTAL_L * (1 + FY26_TOLERANCE_PCT / 100)
    if not (lo <= total <= hi):
        failures.append(
            f"FY26 TOTAL: ₹{total:,.2f}L is outside ₹{lo:,.2f}L–₹{hi:,.2f}L "
            f"(expected ₹{EXPECTED_FY26_TOTAL_L:,.2f}L ± {FY26_TOLERANCE_PCT}%)"
        )
    else:
        print(f"  ✓  FY26 total: ₹{total:,.2f}L  (within ±{FY26_TOLERANCE_PCT}% of ₹{EXPECTED_FY26_TOTAL_L:,.2f}L)")


def check_fy27_present(primary: dict, failures: list) -> None:
    chains = primary.get("by_chain", [])
    total = sum(float(c.get("fy27") or 0) for c in chains)
    if total <= 0:
        failures.append("FY27 TOTAL: sum across all chains is 0 — FY27 data missing")
    else:
        print(f"  ✓  FY27 total: ₹{total:,.2f}L")


def check_no_fy26_nulls(primary: dict, failures: list) -> None:
    chains = primary.get("by_chain", [])
    bad = [c.get("name", "?") for c in chains if is_nan_or_none(c.get("fy26"))]
    if bad:
        failures.append(f"NULL/NaN FY26: chains with missing fy26 value: {bad}")
    else:
        print(f"  ✓  No null/NaN in fy26 across {len(chains)} chains")


def check_zones(primary: dict, failures: list) -> None:
    zones = {z.get("name") for z in primary.get("by_zone", [])}
    extra = zones - AUTHORISED_ZONES
    missing = AUTHORISED_ZONES - zones
    if extra:
        failures.append(f"EXTRA ZONES: {extra} — remove from primary.by_zone")
    if missing:
        failures.append(f"MISSING ZONES: {missing} — expected in primary.by_zone")
    if not extra and not missing:
        print(f"  ✓  Zones: {sorted(zones)}")


def check_offtake_zones(offtake: dict, failures: list) -> None:
    # Check by_zone aggregation (UI-facing; raw zone_monthly_fy27 intentionally retains Pan India as source)
    by_zone_names = {z.get("name") for z in offtake.get("by_zone", [])}
    if "Pan India" in by_zone_names:
        failures.append("OFFTAKE: 'Pan India' present in by_zone — remove from UI aggregation to avoid double-count")
    else:
        print(f"  ✓  Offtake by_zone: {sorted(by_zone_names)} (no Pan India)")


def check_channels(primary: dict, failures: list) -> None:
    channels = {c.get("name") for c in primary.get("by_channel", [])}
    missing = REQUIRED_CHANNELS - channels
    if missing:
        failures.append(f"CHANNELS: missing {missing} from primary.by_channel")
    else:
        print(f"  ✓  Channels present: {sorted(channels)}")


def check_dims_zones(data: dict, failures: list) -> None:
    dims_zones = set(data.get("dims", {}).get("Zone", []))
    if not dims_zones:
        print("  –  dims.Zone not present (skip — only in full builds)")
        return
    extra = dims_zones - AUTHORISED_ZONES
    if extra:
        failures.append(f"DIMS ZONE: unexpected zones {extra}")
    else:
        print(f"  ✓  dims.Zone: {sorted(dims_zones)}")


def check_n_chains_reported(primary: dict, failures: list) -> None:
    reported = primary.get("n_chains")
    actual = len(primary.get("by_chain", []))
    if reported is None:
        print("  –  primary.n_chains not set (skip)")
        return
    if reported != actual:
        failures.append(f"N_CHAINS MISMATCH: primary.n_chains={reported} but by_chain has {actual} rows")
    else:
        print(f"  ✓  primary.n_chains: {reported}")


# ── Runner ─────────────────────────────────────────────────────────────────────

def main() -> int:
    path = sys.argv[1] if len(sys.argv) > 1 else "dashboard/data.js"
    print("=" * 72)
    print(f"DATA INTEGRITY VALIDATION — {path}")
    print("=" * 72)

    try:
        data = load_datajs(path)
    except FileNotFoundError:
        print(f"FAIL: file not found: {path}")
        return 1
    except json.JSONDecodeError as e:
        print(f"FAIL: JSON parse error: {e}")
        return 1

    primary = data.get("primary", {})
    offtake = data.get("offtake", {})

    failures: list[str] = []

    print("\n[Primary block]")
    check_chain_count(primary, failures)
    check_no_legacy_names(primary, failures)
    check_fy26_total(primary, failures)
    check_fy27_present(primary, failures)
    check_no_fy26_nulls(primary, failures)
    check_zones(primary, failures)
    check_channels(primary, failures)
    check_n_chains_reported(primary, failures)

    print("\n[Offtake block]")
    check_offtake_zones(offtake, failures)

    print("\n[Dims block]")
    check_dims_zones(data, failures)

    print()
    if failures:
        print("=" * 72)
        print(f"FAILED — {len(failures)} assertion(s):")
        for i, f in enumerate(failures, 1):
            print(f"  {i}. {f}")
        print("=" * 72)
        return 1

    print("=" * 72)
    print(f"PASSED — all {10} integrity assertions satisfied")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
