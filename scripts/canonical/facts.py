"""Canonical fact loading.

Phase 1's fact source is dashboard/data.js -- the certified baseline (see
docs/POST_MERGE_CERTIFICATION_PR193.md) -- not the raw XLSB/CSV source
files scripts/build_dashboard_data.py's own loaders read. Those raw
sources are gitignored and require a --src drop this repo does not commit,
so a canonical engine built against them would not be runnable by a
reviewer or in CI. data.js's detail_records (article-wise, 100% value
coverage per its own detail_meta) and offtake blocks are themselves
already the certified output of that raw-source pipeline, so treating them
as this phase's "facts" is a deliberate, documented scoping choice, not an
oversight -- see docs/CANONICAL_ENGINE_PHASE1_REPORT.md's "Known
limitations" section.

Reuses scripts/ci_validate_datajs.py's load_datajs() rather than a second
copy of the same JSON-extraction logic.
"""
import importlib
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))
_civ = importlib.import_module("ci_validate_datajs")

load_datajs = _civ.load_datajs


def primary_fact_rows(data):
    """detail_records, as-is -- already the article-wise, certified-
    coverage source for every Primary-side canonical metric. Returns the
    raw list of dicts (FY, Channel, Chain, Zone, Brand, Category, NSV, ...)
    unmodified; metric functions filter/group as needed rather than this
    function pre-aggregating (keeps the fact layer a genuine fact table,
    not a second set of pre-computed totals -- the exact anti-pattern
    docs/CANONICAL_FINANCIAL_TRUTH_DESIGN.md's target-state diagram warns
    against)."""
    return data.get("detail_records") or []


def channel_totals_for_fy(data, fy_tag):
    """detail_meta.channel_totals[fy_tag] -- {Channel: NSV_Lakh}, computed
    by detail_records_real() from the FULL, UNROUNDED row-level NSV series
    before any per-record rounding. This is a MORE PRECISE source than
    re-summing detail_records itself: every record in detail_records is
    independently rounded to 2dp at its own (finer) grain, so re-summing
    113k+ such records reintroduces cumulative rounding noise (~0.003% on
    FY26, verified while building this module) that channel_totals's
    single-point aggregate rounding does not have. Prefer this source for
    PRIMARY_NSV/CHANNEL_PRIMARY_NSV whenever it covers the requested FY;
    fall back to detail_records only for grains channel_totals doesn't
    carry (e.g. RBC's by-zone split). Returns None if the FY isn't covered
    by channel_totals at all."""
    return (data.get("detail_meta") or {}).get("channel_totals", {}).get(fy_tag)


def offtake_fy_total(data, fy_tag_lower):
    """offtake['total_<fy>'] -- the flat, FY-specific key BOTH
    offtake_block() and offtake_rebuild_block() maintain correctly (unlike
    offtake['total'], whose shape/meaning is ambiguous -- see the design
    doc's root-cause trace). Returns None if absent; callers route this
    through policies.exact_fy_or_not_available()."""
    o = data.get("offtake") or {}
    return o.get(f"total_{fy_tag_lower}")


def offtake_fy_monthly(data, fy_tag_lower):
    """offtake['monthly_<fy>'] -- used only for the reconciliation cross-
    check (sum(monthly_<fy>) == total_<fy>) already proven in
    docs/PR_193_PRODUCTION_CERTIFICATION.md Control 4, re-run here as a
    canonical-engine regression test, not a data source for any metric."""
    o = data.get("offtake") or {}
    return o.get(f"monthly_{fy_tag_lower}") or []


def offtake_chain_fy_values(data, chain_name):
    """{fy_tag_lower: value} for one chain, built ONLY from the per-chain
    <fy>-keyed fields in offtake['by_chain'] -- deliberately EXCLUDES the
    'value' and 'total' fields on each row, which the design doc's
    root-cause trace proved are an all-months-combined aggregate with no
    FY subscript (offtake_rebuild_block()'s dim_rows()), not a real
    per-FY value. This is the exact fix for KI-OFFTAKE-001: the fact
    layer itself never exposes '.value' as an FY-keyed value, so no
    metric function built on top of this fact layer can accidentally
    reach for it."""
    by_chain = (data.get("offtake") or {}).get("by_chain") or []
    row = next((r for r in by_chain if r.get("name") == chain_name), None)
    if row is None:
        return {}
    return {
        k: v for k, v in row.items()
        if k not in ("name", "raw", "value", "total", "yoy")
        and not k.startswith("secondary_")
    }


def offtake_chain_names(data):
    by_chain = (data.get("offtake") or {}).get("by_chain") or []
    return sorted({r.get("name") for r in by_chain if r.get("name")})


def reliance_bc_fy_total(data, fy_tag_lower):
    """D.reliance_brand_counters['total'] is NOT FY-keyed in the current
    schema (it's a single flat figure spanning whatever months
    load_reliance_bc_data() loaded) -- so this returns the value only when
    the block's own fy_tags contains exactly the requested FY (a single-FY
    block); otherwise NOT_AVAILABLE via the caller, since attributing a
    multi-FY flat total to one requested FY would itself violate ADR-001.
    """
    bc = data.get("reliance_brand_counters") or {}
    fy_tags = [t for t in (bc.get("fy_tags") or [])]
    if fy_tags == [fy_tag_lower]:
        return bc.get("total")
    return None
