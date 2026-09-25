"""Canonical Primary-side metrics: PRIMARY_NSV, CHANNEL_PRIMARY_NSV,
RBC_PRIMARY_NSV. Source: detail_records (article-wise, per
docs/CANONICAL_FINANCIAL_TRUTH_DESIGN.md's PRIMARY_NSV contract -- the
article-wise source is the confirmed authority, not the pre-agg seed).
"""
from . import facts, units
from .fiscal import normalize_fy
from .policies import NotAvailable, exact_fy_or_not_available


def _sum_nsv(rows):
    return units.round_lakh(sum(float(r.get("NSV") or 0) for r in rows))


def _by_fy(rows, key_fn):
    """rows -> {fy_tag: sum(NSV)} grouped by whatever key_fn(row) returns
    for the FY, deduplicating on the real FY field (never inferred from
    month/position -- rows already carry a real 'FY' field, per THE ONE FY
    RULE, so this just groups on it)."""
    out = {}
    for r in rows:
        fy = normalize_fy(r.get("FY"))
        if fy is None:
            continue
        out[fy] = out.get(fy, 0.0) + float(r.get("NSV") or 0)
    return {k: units.round_lakh(v) for k, v in out.items()}


def primary_nsv(data, fy):
    """PRIMARY_NSV(fy) = SUM(detail_meta.channel_totals[fy].values()) when
    that FY is covered (the full-precision, already-certified source);
    else SUM(detail_records.NSV) WHERE FY = fy as a fallback (a small,
    structurally-explained cumulative-rounding variance vs the preferred
    source -- see facts.channel_totals_for_fy's docstring)."""
    fy = normalize_fy(fy)
    ct = facts.channel_totals_for_fy(data, fy)
    if ct is not None:
        return units.round_lakh(sum(ct.values()))
    rows = facts.primary_fact_rows(data)
    by_fy = _by_fy(rows, lambda r: r.get("FY"))
    return exact_fy_or_not_available("PRIMARY_NSV", fy, by_fy)


def channel_primary_nsv(data, fy, channel):
    """CHANNEL_PRIMARY_NSV(fy, channel): prefers
    detail_meta.channel_totals[fy][channel] (full precision, certified in
    PR #193's Control 1); falls back to summing detail_records when
    channel_totals doesn't cover the requested FY."""
    fy = normalize_fy(fy)
    ct = facts.channel_totals_for_fy(data, fy)
    if ct is not None:
        if channel not in ct:
            return NotAvailable(f"CHANNEL_PRIMARY_NSV[{channel}]: not in channel_totals[{fy}]")
        return units.round_lakh(ct[channel])
    rows = [r for r in facts.primary_fact_rows(data) if r.get("Channel") == channel]
    if not rows:
        return NotAvailable(f"CHANNEL_PRIMARY_NSV: no rows for channel {channel!r}")
    by_fy = _by_fy(rows, lambda r: r.get("FY"))
    return exact_fy_or_not_available(f"CHANNEL_PRIMARY_NSV[{channel}]", fy, by_fy)


def channel_primary_nsv_all_channels(data, fy):
    """{channel: CHANNEL_PRIMARY_NSV(fy, channel)} for every channel present
    in channel_totals (preferred) or detail_records (fallback) -- used by
    the shadow reconciliation against primary.by_channel's fy26 entries
    (PR #193's Control 1)."""
    fy = normalize_fy(fy)
    ct = facts.channel_totals_for_fy(data, fy)
    if ct is not None:
        return {c: units.round_lakh(v) for c, v in ct.items()}
    rows = facts.primary_fact_rows(data)
    channels = sorted({r.get("Channel") for r in rows if r.get("Channel")})
    return {c: channel_primary_nsv(data, fy, c) for c in channels}


def rbc_primary_nsv(data, fy):
    """RBC_PRIMARY_NSV(fy) = SUM(detail_records.NSV)
    WHERE FY = fy AND Chain = 'Reliance Retail'
    (ADR-003: Primary side of the Reliance Brand Counter three-part view)."""
    fy = normalize_fy(fy)
    rows = [r for r in facts.primary_fact_rows(data) if r.get("Chain") == "Reliance Retail"]
    if not rows:
        return NotAvailable("RBC_PRIMARY_NSV: no Reliance Retail rows in detail_records")
    by_fy = _by_fy(rows, lambda r: r.get("FY"))
    return exact_fy_or_not_available("RBC_PRIMARY_NSV", fy, by_fy)


def rbc_primary_nsv_by_zone(data, fy):
    """{zone: NSV} for Reliance Retail, fy-filtered -- used by the shadow
    reconciliation against the existing Reliance-by-Zone table (PR #193's
    Reliance Control)."""
    fy = normalize_fy(fy)
    rows = [r for r in facts.primary_fact_rows(data)
            if r.get("Chain") == "Reliance Retail" and normalize_fy(r.get("FY")) == fy]
    out = {}
    for r in rows:
        z = r.get("Zone") or "Unknown"
        out[z] = out.get(z, 0.0) + float(r.get("NSV") or 0)
    return {k: units.round_lakh(v) for k, v in out.items()}
