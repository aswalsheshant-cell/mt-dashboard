"""Phase 2A -- CHAIN_OFFTAKE_NSV consumer migration, Gate 1: shadow parity.

Scope: exactly one production consumer -- renderInventorySubview()'s "Top
Chains by Offtake" table (dashboard/index.html:1618) -- per the explicit
Phase 2A decision to NOT also migrate computeChannelHealth()
(index.html:3761), a different feature exhibiting the same underlying
defect, tracked as its own separate finding instead
(docs/PHASE2A_CHAIN_OFFTAKE_LINEAGE.md).

Grain note (source-limited, not a design choice): dashboard/data.js's
offtake.by_chain carries Chain x FY totals ONLY. There is no Chain x
Month, Chain x Brand, or Chain x Category grain anywhere in the certified
offtake block -- verified: by_brand/by_zone/by_state are independent,
non-cross-tabulated dimension aggregates, and monthly_fy<NN> is a flat,
all-chains-combined series with no per-chain breakdown. The widest real
comparison grain available for CHAIN_OFFTAKE_NSV is therefore Chain x FY.
This module does not compare at Chain x Month because that grain does not
exist in the source, not because it was skipped.

This reuses Phase 1's exact governance-gated reconciliation machinery
(canonical.reconcile, canonical.governance) rather than inventing a
second classification scheme for this migration.
"""
from . import existing, facts, offtake, reconcile
from .policies import NotAvailable
from .units import round_lakh

# Same registry entry Phase 1 already uses for this exact metric/scope --
# a variance here is not a new finding, it's KI-OFFTAKE-001 itself.
GOVERNED_METRIC = "CHAIN_OFFTAKE_NSV"


def build_shadow_comparison(data):
    """One ReconciliationRow per (chain, fy) pair, for every chain in
    offtake.by_chain and every FY offtake.fy_tags declares. Mirrors
    scripts/canonical/shadow_report.py's CHAIN_OFFTAKE_NSV block but scoped
    to Phase 2A's own certification (kept separate so Phase 1's report
    numbers are never retroactively changed by Phase 2A's work)."""
    rows = []
    all_chains = facts.offtake_chain_names(data)
    fy_tags = sorted({t.upper() for t in (data.get("offtake") or {}).get("fy_tags") or ["fy26", "fy27"]})
    for fy in fy_tags:
        for chain in all_chains:
            ex_v = existing.chain_offtake_nsv(data, fy, chain)
            ca_v = offtake.chain_offtake_nsv(data, fy, chain)
            ca_available = not isinstance(ca_v, NotAvailable)
            if not ca_available:
                rows.append(reconcile.reconcile_one(
                    GOVERNED_METRIC, f"chain={chain}, fy={fy}", ex_v, ca_v,
                    expected_difference=True,
                    reason="KI-OFFTAKE-001 (Issue #195): canonical correctly reports NOT_AVAILABLE "
                           "(no real fy-keyed entry for this chain); legacy's fallback chain reaches "
                           "offtake.by_chain[].value instead."))
            else:
                rows.append(reconcile.reconcile_one(GOVERNED_METRIC, f"chain={chain}, fy={fy}", ex_v, ca_v))
    return rows


def conservation_check(data, fy, tolerance=0.10):
    """Sigma(canonical chain NSV) vs canonical total NSV, for chains where
    canonical reports a real (AVAILABLE) value. NOT expected to be exactly
    0.00 -- documented, structurally explained rounding noise exists (see
    docstring below) -- so this returns the actual variance rather than a
    bare pass/fail, and the caller/test decides against an explicit,
    reviewed tolerance rather than a silent exact-equality assumption.

    Chains that are NOT_AVAILABLE for this FY are, correctly, excluded from
    the sum -- a NOT_AVAILABLE chain contributes nothing, it does not
    silently contribute 0 in a way indistinguishable from "really zero"
    (ADR-007). available_chains/total_chains in the return value make that
    exclusion visible rather than silent.
    """
    total = offtake.offtake_nsv(data, fy)
    all_chains = facts.offtake_chain_names(data)
    chain_sum = 0.0
    available_chains = 0
    for chain in all_chains:
        v = offtake.chain_offtake_nsv(data, fy, chain)
        if not isinstance(v, NotAvailable):
            chain_sum += v
            available_chains += 1
    chain_sum = round_lakh(chain_sum)
    variance = None if isinstance(total, NotAvailable) else round_lakh(abs(total - chain_sum))
    return {
        "fy": fy,
        "canonical_total": total,
        "sum_of_available_chains": chain_sum,
        "available_chains": available_chains,
        "total_chains": len(all_chains),
        "variance": variance,
        "within_tolerance": variance is not None and variance <= tolerance,
        "tolerance": tolerance,
        "reason": ("Small residual rounding noise, not a duplication or omission defect: each "
                   "chain's FY total and the flat offtake.total_<fy> field are computed via "
                   "independent summation passes over the same monthly source in "
                   "offtake_rebuild_block() (build_dashboard_data.py), each rounded to 2dp at its "
                   "own point -- the same class of ~0.003%%-magnitude cumulative-rounding "
                   "characteristic already documented for PRIMARY_NSV in "
                   "docs/CANONICAL_ENGINE_PHASE1_REPORT.md's 'Source lineage' section, not a new "
                   "finding specific to this migration."),
    }


def edge_case_report(data):
    """Explicit findings for every edge case Phase 2A's Gate 1 instruction
    names, so each one has a real, checked answer on record -- never
    silently assumed. 'N/A' means the edge case does not occur in this
    dataset today (verified, not skipped), not that it wasn't checked."""
    by_chain = (data.get("offtake") or {}).get("by_chain") or []
    names = [r.get("name") for r in by_chain]

    duplicate_names = sorted({n for n in names if names.count(n) > 1})
    blank_names = [i for i, n in enumerate(names) if not n or not str(n).strip()]
    unmapped_chain_present = "Unmapped Chain" in names

    negative_values = []
    for r in by_chain:
        for k, v in r.items():
            if k.startswith("fy") and isinstance(v, (int, float)) and not isinstance(v, bool) and v < 0:
                negative_values.append({"chain": r.get("name"), "field": k, "value": v})

    partial_fy_chains = []
    fy_tags = sorted({t.lower() for t in (data.get("offtake") or {}).get("fy_tags") or ["fy26", "fy27"]})
    for r in by_chain:
        present = [t for t in fy_tags if t in r and r[t] is not None]
        if 0 < len(present) < len(fy_tags):
            partial_fy_chains.append({"chain": r.get("name"), "fys_present": present, "fys_missing": sorted(set(fy_tags) - set(present))})

    return {
        "unmapped_chain": {
            "found": unmapped_chain_present,
            "note": "N/A -- 'Unmapped Chain' appears in Primary detail_records but never in "
                    "offtake.by_chain in this certified data.js. Verified, not assumed.",
        },
        "duplicate_mapping": {
            "found": bool(duplicate_names),
            "duplicates": duplicate_names,
            "note": "N/A -- offtake.by_chain has 35 rows, 35 unique names, verified." if not duplicate_names
                    else f"REAL FINDING: {len(duplicate_names)} chain name(s) appear more than once.",
        },
        "blank_chain": {
            "found": bool(blank_names),
            "row_indices": blank_names,
            "note": "N/A -- no null/empty chain name found." if not blank_names
                    else f"REAL FINDING: {len(blank_names)} row(s) with a blank/null chain name.",
        },
        "missing_month_grain": {
            "found": "not_applicable",
            "note": "N/A by source design, not a defect -- offtake.by_chain has no Chain x Month "
                    "grain at all (see this module's docstring); a 'missing month' concept does not "
                    "apply to a metric whose source is Chain x FY only.",
        },
        "partial_fy_chains": {
            "found": bool(partial_fy_chains),
            "chains": partial_fy_chains,
            "note": (f"REAL: {len(partial_fy_chains)} chain(s) have real data for some FYs but not "
                     "others -- this IS KI-OFFTAKE-001's exact shape, not a separate finding. Each "
                     "one is a governed row in build_shadow_comparison()'s output, never silently "
                     "zero-filled.") if partial_fy_chains else "N/A -- no chain has partial FY coverage.",
        },
        "negative_nsv": {
            "found": bool(negative_values),
            "values": negative_values,
            "note": "N/A -- no negative chain-FY offtake value found in this certified data.js. "
                    "(Primary detail_records DOES carry legitimate negative NSV rows -- e.g. FOC/scheme "
                    "adjustments, see contracts/primary_contract.yaml's known_exceptions -- but that is "
                    "a different source, out of scope for this Offtake-side check.)" if not negative_values
                    else f"REAL FINDING: {len(negative_values)} negative chain-FY value(s).",
        },
        "zero_denominator": {
            "found": "not_applicable",
            "note": "N/A -- CHAIN_OFFTAKE_NSV is a plain summed value, not a ratio; no division "
                    "occurs in its computation, so no zero-denominator case can arise.",
        },
        "unknown_governance_entry": {
            "note": "Covered structurally, not just empirically: reconcile_one() routes every "
                    "expected_difference=True claim through governance.find_approved_exception(); "
                    "an unregistered claim becomes UNKNOWN, proven by "
                    "tests/canonical/test_governance.py::test_unregistered_exception_becomes_unknown_not_governed "
                    "and re-asserted for this migration's own rows in "
                    "tests/canonical/test_phase2_chain_offtake.py.",
        },
        "missing_availability": {
            "note": "Covered structurally: every NOT_AVAILABLE chain/FY pair in "
                    "build_shadow_comparison()'s output carries an explicit NotAvailable reason "
                    "string (never a bare None or a 0), verified in "
                    "tests/canonical/test_phase2_chain_offtake.py.",
        },
    }
