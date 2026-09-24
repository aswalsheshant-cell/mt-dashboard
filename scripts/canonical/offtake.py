"""Canonical Offtake-side metrics: OFFTAKE_NSV, CHAIN_OFFTAKE_NSV,
RBC_OFFTAKE_NSV.

CHAIN_OFFTAKE_NSV is this package's first proof case for KI-OFFTAKE-001
(Issue #195): it is built entirely on facts.offtake_chain_fy_values(),
which never exposes the all-months-combined '.value'/'total' fields on an
offtake.by_chain row as if they were FY-specific -- see that function's
docstring for the verified root cause.
"""
from . import facts, units
from .fiscal import normalize_fy, data_key
from .policies import NotAvailable, exact_fy_or_not_available


def offtake_nsv(data, fy):
    """OFFTAKE_NSV(fy) = offtake['total_<fy>'] -- the flat, FY-specific
    field both offtake_block() and offtake_rebuild_block() maintain
    correctly (unlike the ambiguous offtake['total']). NOT_AVAILABLE if
    that exact key is absent."""
    fy = normalize_fy(fy)
    key = data_key(fy)
    v = facts.offtake_fy_total(data, key)
    if v is None:
        return NotAvailable(f"OFFTAKE_NSV: offtake.total_{key} missing")
    return units.round_lakh(v)


def chain_offtake_nsv(data, fy, chain):
    """CHAIN_OFFTAKE_NSV(fy, chain) = SUM(canonical_offtake_fact.nsv)
    WHERE Chain = chain AND FY = fy.

    Implementation: offtake.by_chain[chain][<fy>] via
    facts.offtake_chain_fy_values(), which strips the '.value'/'total'
    fields at the fact layer -- so this function CANNOT reach the
    all-months-combined aggregate even by accident. If the chain has no
    entry for the requested FY, returns NOT_AVAILABLE. Never substitutes
    another FY's value, and never substitutes the all-period aggregate.
    This is the exact fix for KI-OFFTAKE-001: the old dashboard code's
    fallback chain (ch_data.total?.[fyR] ?? ... ?? ch_data.value ?? 0)
    could reach a stale/all-period number; this function structurally
    cannot."""
    fy = normalize_fy(fy)
    key = data_key(fy)
    values = facts.offtake_chain_fy_values(data, chain)
    if not values:
        return NotAvailable(f"CHAIN_OFFTAKE_NSV: no chain named {chain!r} in offtake.by_chain")
    return exact_fy_or_not_available(f"CHAIN_OFFTAKE_NSV[{chain}]", key, values)


def chain_offtake_nsv_all_chains(data, fy):
    """{chain: CHAIN_OFFTAKE_NSV(fy, chain)} for every chain in
    offtake.by_chain -- used by the shadow reconciliation table. Includes
    NotAvailable entries explicitly (does not filter them out) so the
    reconciliation report can show exactly which chains the old dashboard
    silently mis-handled for this FY."""
    fy = normalize_fy(fy)
    return {c: chain_offtake_nsv(data, fy, c) for c in facts.offtake_chain_names(data)}


def rbc_offtake_nsv(data, fy):
    """RBC_OFFTAKE_NSV(fy): Offtake side of the Reliance Brand Counter
    three-part view (ADR-003). Source: D.reliance_brand_counters, which in
    the certified baseline is the EMPTY STUB
    ("Reliance Brand Counter data not available in current extracts") --
    load_reliance_bc_data() found no BC extract in the --src used to build
    this data.js. This is a genuine, honestly-reported NOT_AVAILABLE, not
    a wiring gap: the code path is real and correct, the underlying source
    file is simply absent from this build. See
    docs/CANONICAL_ENGINE_PHASE1_REPORT.md."""
    fy = normalize_fy(fy)
    key = data_key(fy)
    v = facts.reliance_bc_fy_total(data, key)
    if v is None:
        bc = data.get("reliance_brand_counters") or {}
        note = bc.get("note") or "no data for this FY"
        return NotAvailable(f"RBC_OFFTAKE_NSV: {note}")
    return units.round_lakh(v)
