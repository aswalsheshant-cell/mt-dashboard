"""Runs the full shadow reconciliation: existing (current production,
replicated) vs canonical, for every Phase-1 metric, and prints/returns the
report table docs/CANONICAL_ENGINE_PHASE1_REPORT.md is built from.

Usage: python scripts/canonical/shadow_report.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from canonical import existing, facts, offtake, primary, reconcile
from canonical.policies import NotAvailable


def build_report(data):
    rows = []

    # --- CHANNEL_PRIMARY_NSV: Executive Cockpit donut vs canonical, per channel, per FY ---
    # primary.by_channel (the Executive Cockpit's source) genuinely has NO
    # FY27 coverage at all -- a documented architecture fact (CLAUDE.md's
    # "Coverage split": the pre-agg workbook ends Mar'26; FY27 Primary
    # lives only in detail_meta.fyx_primary), not a bug this reconciliation
    # discovered. A channel/FY absent from primary.by_channel is NOT the
    # same as primary.by_channel reporting 0 -- must not conflate the two,
    # the exact ADR-007 mistake this whole exercise exists to prevent.
    PRIMARY_BY_CHANNEL_FY_COVERAGE = "FY26"  # only FY primary.by_channel currently carries
    for fy in ("FY26", "FY27"):
        ex = existing.channel_primary_nsv(data, fy)
        ca = primary.channel_primary_nsv_all_channels(data, fy)
        governed = fy != PRIMARY_BY_CHANNEL_FY_COVERAGE
        for ch in sorted(set(ex) | set(ca)):
            ex_v = ex[ch] if ch in ex else NotAvailable(
                f"primary.by_channel has no {fy} coverage (CLAUDE.md Coverage split)")
            ca_v = ca.get(ch)
            if ca_v is None:
                continue
            if governed and ch not in ex:
                rows.append(reconcile.reconcile_one(
                    "CHANNEL_PRIMARY_NSV", f"channel={ch}, fy={fy}", ex_v, ca_v,
                    expected_difference=True,
                    reason=f"primary.by_channel carries no {fy} data at all -- documented "
                           "architecture gap (CLAUDE.md Coverage split), not discovered by "
                           "this reconciliation. Canonical correctly computes a real value "
                           "from detail_meta.channel_totals, which does cover this FY."))
            else:
                rows.append(reconcile.reconcile_one(
                    "CHANNEL_PRIMARY_NSV", f"channel={ch}, fy={fy}", ex_v, ca_v))

    # --- PRIMARY_NSV: sum of the above, per FY ---
    for fy in ("FY26", "FY27"):
        ex_dict = existing.channel_primary_nsv(data, fy)
        ca = primary.primary_nsv(data, fy)
        if fy != PRIMARY_BY_CHANNEL_FY_COVERAGE:
            ex_v = NotAvailable(f"primary.by_channel has no {fy} coverage")
            rows.append(reconcile.reconcile_one(
                "PRIMARY_NSV", f"fy={fy}", ex_v, ca, expected_difference=True,
                reason=f"Same documented {fy} coverage gap as CHANNEL_PRIMARY_NSV above."))
        else:
            ex_v = sum(ex_dict.values())
            rows.append(reconcile.reconcile_one("PRIMARY_NSV", f"fy={fy}", ex_v, ca))

    # --- OFFTAKE_NSV: Total Offtake KPI vs canonical, per FY ---
    for fy in ("FY26", "FY27"):
        ex = existing.offtake_total_kpi(data, fy)
        ca = offtake.offtake_nsv(data, fy)
        rows.append(reconcile.reconcile_one("OFFTAKE_NSV", f"fy={fy}", ex, ca))

    # --- CHAIN_OFFTAKE_NSV: Top Chains table vs canonical, per chain, FY27
    #     (the FY the "Top Chains" table currently displays by default, and
    #     where KI-OFFTAKE-001's affected chains actually diverge) ---
    fy = "FY27"
    all_chains = facts.offtake_chain_names(data)
    for chain in all_chains:
        ex_v = existing.chain_offtake_nsv(data, fy, chain)
        ca_v = offtake.chain_offtake_nsv(data, fy, chain)
        ca_available = not hasattr(ca_v, "reason")
        if not ca_available:
            # KI-OFFTAKE-001's governed case, unconditionally: canonical
            # says NOT_AVAILABLE for this chain/FY (no real <fy>-keyed
            # entry) whenever the old code's fallback chain would have
            # reached ch_data.value -- whether that field happened to be a
            # real-looking nonzero stale figure (e.g. Vijetha) or 0 (e.g.
            # chains whose last-known .value was itself 0), the underlying
            # defect is identical: a non-answer for "no data this FY"
            # substituted for an explicit NOT_AVAILABLE. This proof case
            # is exactly what CHAIN_OFFTAKE_NSV exists to close.
            rows.append(reconcile.reconcile_one(
                "CHAIN_OFFTAKE_NSV", f"chain={chain}, fy={fy}", ex_v, ca_v,
                expected_difference=True,
                reason="KI-OFFTAKE-001 (Issue #195): canonical correctly reports "
                       "NOT_AVAILABLE (no real fy27-keyed entry for this chain); the "
                       "existing dashboard's fallback chain reaches offtake.by_chain[]."
                       "value (an all-months-combined field, not FY-specific) instead. "
                       "See docs/CANONICAL_ENGINE_PHASE1_REPORT.md."))
        else:
            rows.append(reconcile.reconcile_one(
                "CHAIN_OFFTAKE_NSV", f"chain={chain}, fy={fy}", ex_v, ca_v))

    # --- RBC_PRIMARY_NSV: existing tab (all-FY total) vs canonical (FY26+FY27 summed) ---
    ex_v = existing.reliance_primary_nsv(data)
    ca_fy26 = primary.rbc_primary_nsv(data, "FY26")
    ca_fy27 = primary.rbc_primary_nsv(data, "FY27")
    ca_v = round((ca_fy26 if not hasattr(ca_fy26, "reason") else 0)
                 + (ca_fy27 if not hasattr(ca_fy27, "reason") else 0), 2)
    rows.append(reconcile.reconcile_one(
        "RBC_PRIMARY_NSV", "all FYs combined (matches current tab's no-FY-filter default)",
        ex_v, ca_v))

    # --- RBC_OFFTAKE_NSV: no existing consumer (per the dependency map) --
    #     canonical correctly reports NOT_AVAILABLE (empty BC stub in this build) ---
    for fy in ("FY26", "FY27"):
        ca_v = offtake.rbc_offtake_nsv(data, fy)
        rows.append(reconcile.reconcile_one(
            "RBC_OFFTAKE_NSV", f"fy={fy}", None, ca_v,
            expected_difference=True,
            reason="No existing dashboard consumer (per docs/CANONICAL_METRIC_DEPENDENCY_MAP.md); "
                   "'existing' is reported as None/no comparison, not a real prior value."))

    return rows


def main():
    data = facts.load_datajs()
    rows = build_report(data)
    summary = reconcile.summarize(rows)
    print(json.dumps({"summary": summary, "rows": [r.as_dict() for r in rows]}, indent=2))
    return 0 if summary["overall"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
