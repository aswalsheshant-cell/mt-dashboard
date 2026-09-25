"""Regression test for apply_primary_channel_correction().

Root cause (found 2026-09-23, dashboard root-cause audit): the pre-aggregated
primary seed (PowerBI/SeedData/Primary/Primary_FY202426_10.csv) tags every
FY26 row Channel="MT", so primary.by_channel rendered as 100% MT with
EB2B/SIS hard-zeroed -- even though the article-wise primary source
(Primary_Article_Monthly/*.csv) carries a real, business-confirmed channel
split for the SAME FY26 total. This test proves the correction function:
overwrites pre-agg FY values from the article-wise channel_totals when the
FY totals agree, adds any channel name detail_meta has seen, and refuses to
override when the two sources' totals disagree materially.
"""
import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
bd = importlib.import_module("build_dashboard_data")


def test_corrects_fy26_values_when_totals_agree():
    primary = {"by_channel": [{"name": "MT", "fy26": 32900.36},
                               {"name": "EB2B", "fy26": 0},
                               {"name": "SIS", "fy26": 0}]}
    detail_meta = {"channel_totals": {
        "FY26": {"MT": 30684.99, "EB2B": 1965.20, "SIS": 250.17},
    }}
    bd.apply_primary_channel_correction(primary, detail_meta)
    by_name = {c["name"]: c for c in primary["by_channel"]}
    assert by_name["MT"]["fy26"] == 30684.99
    assert by_name["EB2B"]["fy26"] == 1965.2
    assert by_name["SIS"]["fy26"] == 250.17


def test_does_not_override_when_totals_disagree():
    primary = {"by_channel": [{"name": "MT", "fy26": 32900.36},
                               {"name": "EB2B", "fy26": 0},
                               {"name": "SIS", "fy26": 0}]}
    # channel_totals FY26 total is materially different from the pre-agg total
    # (e.g. a stale/partial File 2 extract) -- must leave by_channel untouched.
    detail_meta = {"channel_totals": {
        "FY26": {"MT": 10000.0, "EB2B": 500.0, "SIS": 100.0},
    }}
    bd.apply_primary_channel_correction(primary, detail_meta)
    by_name = {c["name"]: c for c in primary["by_channel"]}
    assert by_name["MT"]["fy26"] == 32900.36
    assert by_name["EB2B"]["fy26"] == 0
    assert by_name["SIS"]["fy26"] == 0


def test_adds_missing_channel_names_from_fyx_primary():
    primary = {"by_channel": [{"name": "MT", "fy26": 32900.36}]}
    detail_meta = {"channel_totals": {}, "fyx_primary": {
        "FY27": {"by_channel": [{"name": "MT", "nsv": 100}, {"name": "EB2B", "nsv": 20},
                                 {"name": "SIS", "nsv": 5}]},
    }}
    bd.apply_primary_channel_correction(primary, detail_meta)
    names = {c["name"] for c in primary["by_channel"]}
    assert names == {"MT", "EB2B", "SIS"}


def test_never_touches_fy27_via_channel_totals():
    # FY27 is NOT in PREAGG_FY_TAGS -- it lives in fyx_primary, not by_channel's
    # pre-agg values, so a channel_totals["FY27"] entry must be ignored here.
    primary = {"by_channel": [{"name": "MT", "fy26": 32900.36}]}
    detail_meta = {"channel_totals": {"FY27": {"MT": 999.0}}}
    bd.apply_primary_channel_correction(primary, detail_meta)
    by_name = {c["name"]: c for c in primary["by_channel"]}
    assert "fy27" not in by_name["MT"]


def test_noop_when_no_channel_totals_or_fyx_primary():
    primary = {"by_channel": [{"name": "MT", "fy26": 32900.36}]}
    bd.apply_primary_channel_correction(primary, {})
    assert primary["by_channel"] == [{"name": "MT", "fy26": 32900.36}]
