"""
Regression tests for primary_block()'s dim_rows() fix (Phase 2B-B, item 1 --
docs/SOURCE_MISSINGNESS_LINEAGE.md's F14 finding).

Before this fix, dim_rows() did `pivot_table(...).fillna(0)` unconditionally,
so a chain/zone/brand with zero real rows for a given FY got a literal `0`
in by_chain/by_zone/by_brand -- indistinguishable from a chain that genuinely
had zero recorded sales that FY. Empirically confirmed against the certified
data.js before this fix: 'Dabur New U' and 'Medanta' both showed a literal
`fy26: 0` in D.primary.by_chain despite having no real FY26 primary rows.

The fix adds a `zero_fill` parameter: zero_fill=False (now used for
by_zone/by_brand/by_chain) writes None (JSON null) for a genuinely-missing
combination instead of fabricating 0 -- matching
scripts/canonical/policies.py::exact_fy_or_not_available()'s semantics on
the Python side, not just the JS/canonical side. zero_fill=True (default,
still used for by_channel) is UNCHANGED -- channel is a small, closed,
always-populated dimension with its own explicit, deliberate "represent
every known channel, even at 0" design (the immediately-following backfill
loop in primary_block()), which this fix does not touch.
"""
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import build_dashboard_data as bdd  # noqa: E402


def _df(rows):
    return pd.DataFrame(rows)


def test_chain_with_no_rows_in_a_fy_gets_none_not_zero():
    df = _df([
        {"FY": "FY26", "Month": "April", "NSV": 100.0, "MRP value": 150.0,
         "chain": "X", "brand": "B", "zone": "Z", "channel": "MT"},
        {"FY": "FY25", "Month": "April", "NSV": 50.0, "MRP value": 80.0,
         "chain": "Y", "brand": "B", "zone": "Z", "channel": "MT"},
    ])
    _, out = bdd.primary_block(df)
    by_chain = {r["name"]: r for r in out["by_chain"]}
    assert by_chain["X"]["fy26"] == 100.0
    assert "fy25" not in by_chain["X"] or by_chain["X"]["fy25"] is None
    assert by_chain["Y"]["fy26"] is None
    assert by_chain["Y"]["fy25"] == 50.0


def test_real_zero_row_is_still_distinguishable_from_missing():
    """A chain that has a REAL recorded row summing to exactly 0 (e.g. a
    return/credit-note fully offsetting a sale) must still show 0.0, not
    None -- ADR-007's "real zero != missing" cuts both ways."""
    df = _df([
        {"FY": "FY26", "Month": "April", "NSV": 100.0, "MRP value": 150.0,
         "chain": "X", "brand": "B", "zone": "Z", "channel": "MT"},
        {"FY": "FY26", "Month": "May", "NSV": -100.0, "MRP value": -150.0,
         "chain": "X", "brand": "B", "zone": "Z", "channel": "MT"},
    ])
    _, out = bdd.primary_block(df)
    by_chain = {r["name"]: r for r in out["by_chain"]}
    assert by_chain["X"]["fy26"] == 0.0
    assert by_chain["X"]["fy26"] is not None


def test_yoy_does_not_crash_when_latest_fy_is_none():
    """Regression guard for the exact bug the fix could introduce: `tags`
    are sorted chronologically (lo[0]=earliest='fy25', lo[1]=latest='fy26'),
    so a chain with real EARLIER-FY data but no LATER-FY data has a=real,
    b=None. Previously b was guaranteed a real 0 (fillna default), so
    `(b/a-1)*100` always worked; now b can genuinely be None, and the
    computation must not raise a TypeError."""
    df = _df([
        {"FY": "FY25", "Month": "April", "NSV": 50.0, "MRP value": 80.0,
         "chain": "OnlyFY25", "brand": "B", "zone": "Z", "channel": "MT"},
        {"FY": "FY26", "Month": "April", "NSV": 100.0, "MRP value": 150.0,
         "chain": "OtherChain", "brand": "B", "zone": "Z", "channel": "MT"},
    ])
    _, out = bdd.primary_block(df)  # must not raise
    by_chain = {r["name"]: r for r in out["by_chain"]}
    assert by_chain["OnlyFY25"]["fy25"] == 50.0
    assert by_chain["OnlyFY25"].get("fy26") is None
    assert by_chain["OnlyFY25"]["yoy"] is None


def test_by_channel_still_zero_fills_unchanged():
    """by_channel deliberately keeps zero_fill=True -- a channel present in
    the data for one FY but not another still gets a real 0, matching its
    own separate, documented "represent every known channel, even at 0"
    design (the backfill loop immediately after dim_rows() in primary_block())."""
    df = _df([
        {"FY": "FY26", "Month": "April", "NSV": 100.0, "MRP value": 150.0,
         "chain": "X", "brand": "B", "zone": "Z", "channel": "MT"},
        {"FY": "FY25", "Month": "April", "NSV": 50.0, "MRP value": 80.0,
         "chain": "X", "brand": "B", "zone": "Z", "channel": "EB2B"},
    ])
    _, out = bdd.primary_block(df)
    by_channel = {r["name"]: r for r in out["by_channel"]}
    assert by_channel["MT"]["fy26"] == 100.0
    assert by_channel["MT"]["fy25"] == 0.0  # zero-filled, not None -- unchanged behavior
    assert by_channel["EB2B"]["fy26"] == 0.0  # unchanged behavior


def test_by_zone_and_by_brand_also_use_missing_not_zero():
    df = _df([
        {"FY": "FY26", "Month": "April", "NSV": 100.0, "MRP value": 150.0,
         "chain": "X", "brand": "BrandA", "zone": "ZoneA", "channel": "MT"},
        {"FY": "FY25", "Month": "April", "NSV": 50.0, "MRP value": 80.0,
         "chain": "X", "brand": "BrandB", "zone": "ZoneB", "channel": "MT"},
    ])
    _, out = bdd.primary_block(df)
    by_zone = {r["name"]: r for r in out["by_zone"]}
    by_brand = {r["name"]: r for r in out["by_brand"]}
    assert by_zone["ZoneA"]["fy26"] == 100.0
    assert by_zone["ZoneA"].get("fy25") is None
    assert by_brand["BrandB"]["fy25"] == 50.0
    assert by_brand["BrandB"].get("fy26") is None


def test_multiple_raw_fy_label_variants_do_not_poison_the_sum_with_nan():
    """If the source spells the same canonical FY tag two different ways
    (e.g. real-world messy data), a chain with a real row under ONE variant
    and no rows under the OTHER must still get its real value -- not NaN
    from naive summation across variants, and not None."""
    df = _df([
        {"FY": "FY_25-26", "Month": "April", "NSV": 100.0, "MRP value": 150.0,
         "chain": "X", "brand": "B", "zone": "Z", "channel": "MT"},
        {"FY": "FY26", "Month": "May", "NSV": 20.0, "MRP value": 30.0,
         "chain": "Y", "brand": "B", "zone": "Z", "channel": "MT"},
    ])
    _, out = bdd.primary_block(df)
    by_chain = {r["name"]: r for r in out["by_chain"]}
    # X only has a row under the "FY_25-26" spelling; Y only under "FY26" --
    # both map to the same canonical fy26 tag. Each chain's real value must
    # survive, not be dropped to None or corrupted to NaN.
    assert by_chain["X"]["fy26"] == 100.0
    assert by_chain["Y"]["fy26"] == 20.0
