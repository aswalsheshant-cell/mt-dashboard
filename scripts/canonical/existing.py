"""Replicates dashboard/index.html's CURRENT production JS expressions in
Python, read-only, for shadow reconciliation against canonical.* — this
module does not execute JS; it mirrors the specific expressions being
reconciled, the same technique tests/test_pr193_reconciliation.py already
uses. Each function names the exact index.html line/function it mirrors so
a reviewer can check the mirror is accurate by reading both side by side.

Deliberately reproduces existing bugs where they still exist (there are
none left after PR #193 except KI-OFFTAKE-001, reproduced here on purpose
so the reconciliation table shows exactly what the old code returns for
the affected chains).
"""
from .fiscal import normalize_fy, data_key


def channel_primary_nsv(data, fy):
    """Executive Cockpit's channel-split donut: reads primary.by_channel's
    <fy>-lowercase-keyed field directly. dashboard/index.html:928/1278,
    channels = p.by_channel."""
    key = data_key(fy)
    out = {}
    for row in (data.get("primary") or {}).get("by_channel") or []:
        name = row.get("name")
        if name and key in row:
            out[name] = row[key]
    return out


def offtake_total_kpi(data, fy):
    """buildInventoryHealth()'s Total Offtake KPI, dashboard/index.html:1555,
    post-PR-193 fix: o?.total?.[fyR] ?? o?.[`total_${fyR}`] ?? 0.
    fyR resolution (fy || latest fy_tags entry) is the caller's
    responsibility -- pass the already-resolved fy in."""
    o = data.get("offtake") or {}
    key = data_key(fy)
    total = o.get("total")
    if isinstance(total, dict) and key in total:
        return total[key]
    flat_key = f"total_{key}"
    if flat_key in o:
        return o[flat_key]
    return 0


def chain_offtake_nsv(data, fy, chain):
    """buildInventoryHealth()'s chainData map, dashboard/index.html:1618 --
    the EXACT current (buggy for KI-OFFTAKE-001-affected chains)
    expression:
      nsv = (ch_data.total && ch_data.total[fyR]) || ch_data['total_'+fyR]
            || ch_data[fyR] || ch_data.value || 0
    Reproduced here verbatim (including the .value fallback) so the
    reconciliation table shows precisely what today's dashboard displays,
    not an idealized version of it."""
    key = data_key(fy)
    by_chain = (data.get("offtake") or {}).get("by_chain") or []
    row = next((r for r in by_chain if r.get("name") == chain), None)
    if row is None:
        return 0
    total_field = row.get("total")
    if isinstance(total_field, dict) and total_field.get(key):
        return total_field[key]
    if row.get(f"total_{key}"):
        return row[f"total_{key}"]
    if row.get(key):
        return row[key]
    if row.get("value"):
        return row["value"]
    return 0


def reliance_primary_nsv(data):
    """renderChannelSubview()'s reliance branch, dashboard/index.html
    ~1519-1538, post-PR-193 fix: sums detail_records filtered to
    Chain==='Reliance Retail', with no FY filter applied in the current
    UI (the tab shows an all-FY total unless the global FY filter bar is
    set) -- so 'existing' here is genuinely the ALL-FY total, not
    FY-specific; the comparison in the shadow report must say so rather
    than silently comparing it to a canonical single-FY figure."""
    recs = data.get("detail_records") or []
    total = sum(float(r.get("NSV") or 0)
                for r in recs if r.get("Chain") == "Reliance Retail")
    return round(total, 2)
