"""POS store counts (offtake.pos_stores) come from the offtake Site Code,
not from the 426-row SAP billing-code universe.

Guards: Reliance Brand Counter rows never counted (same dedup as offtake
NSV); a chain with no Site Code shows None (never 0); partial Site Code
coverage is disclosed; re-running recomputes a touched FY and keeps others;
load_offtake_article_files() return value is unchanged by the new sink."""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build_dashboard_data as b  # noqa: E402

COLS = ["Chain Name", "Zone", "State", "Store Type", "Site Code", "Month", "Year", "NSV"]


def _write(tmp_path, rows, name="offtake_store_article_Aug_26.csv"):
    pd.DataFrame(rows, columns=COLS).to_csv(tmp_path / name, index=False)


def _rows():
    return [
        # DMart: 3 stores in Aug, one also in Jul
        ["Dmart", "West", "Maharashtra", "Non Brand Counter", "S1", "Aug'26", 2026, 1.0],
        ["Dmart", "West", "Maharashtra", "Non Brand Counter", "S2", "Aug'26", 2026, 1.0],
        ["Dmart", "West", "Maharashtra", "Non Brand Counter", 1003.0, "Aug'26", 2026, 1.0],
        ["Dmart", "West", "Maharashtra", "Non Brand Counter", "S9", "Jul'26", 2026, 1.0],
        # Reliance non-counter: DC-level, no Site Code
        ["Reliance", "West", "Maharashtra", "Non Brand Counter", None, "Aug'26", 2026, 5.0],
        # Reliance Brand Counter: store-level but excluded (dedup rule)
        ["Reliance", "West", "Maharashtra", "Brand Counter", "RBC1", "Aug'26", 2026, 2.0],
        ["Reliance Brand Counter", "West", "Maharashtra", "Brand Counter", "RBC2", "Aug'26", 2026, 2.0],
        # More Retail: partial Site Code coverage
        ["More Retail", "South", "Karnataka", "Non Brand Counter", "M1", "Aug'26", 2026, 3.0],
        ["More Retail", "South", "Karnataka", "Non Brand Counter", None, "Aug'26", 2026, 1.0],
    ]


def test_counts_sites_not_billing_codes(tmp_path):
    _write(tmp_path, _rows())
    sink = {}
    b.load_offtake_article_files(tmp_path, site_sink=sink)
    pos = b.pos_store_block(sink)
    fy = pos["fy27"]
    assert fy["latest_month"] == "Aug-26"
    dm = fy["by_chain"]["DMart"]
    assert dm["latest"] == 3 and dm["fy_distinct"] == 4 and dm["no_site_pct"] == 0
    # "1003.0" from a float column is the same code as "1003"
    assert "1003" in sink[("DMart", "Aug-26")]["sites"]


def test_reliance_brand_counter_never_counted_and_no_site_is_none(tmp_path):
    _write(tmp_path, _rows())
    sink = {}
    b.load_offtake_article_files(tmp_path, site_sink=sink)
    pos = b.pos_store_block(sink)["fy27"]["by_chain"]
    assert "Reliance Brand Counter" not in pos
    rel = pos["Reliance Retail"]
    assert rel["latest"] is None and rel["fy_distinct"] is None  # missing, not 0
    assert rel["no_site_pct"] == 100
    assert not any("RBC" in s for e in sink.values() for s in e["sites"])


def test_partial_site_coverage_disclosed(tmp_path):
    _write(tmp_path, _rows())
    sink = {}
    b.load_offtake_article_files(tmp_path, site_sink=sink)
    mr = b.pos_store_block(sink)["fy27"]["by_chain"]["More Retail"]
    assert mr["latest"] == 1 and mr["no_site_pct"] == 25.0


def test_return_value_unchanged_by_sink(tmp_path):
    _write(tmp_path, _rows())
    plain = b.load_offtake_article_files(tmp_path)
    with_sink = b.load_offtake_article_files(tmp_path, site_sink={})
    assert plain == with_sink


def test_rerun_recomputes_touched_fy_and_keeps_others(tmp_path):
    _write(tmp_path, _rows())
    sink = {}
    b.load_offtake_article_files(tmp_path, site_sink=sink)
    existing = {"fy28": {"latest_month": "Apr-27"}, "fy27": {"stale": True}}
    pos = b.pos_store_block(sink, existing)
    assert pos["fy28"] == {"latest_month": "Apr-27"}
    assert "stale" not in pos["fy27"]
    assert pos == b.pos_store_block(sink, pos)  # idempotent


def test_data_js_pos_stores_not_the_sap_universe():
    txt = (Path(__file__).resolve().parents[1] / "dashboard" / "data.js").read_text()
    import json
    D = json.loads(txt[txt.index("{"): txt.rstrip().rstrip(";").rindex("}") + 1])
    assert D["universe"]["active_stores"] == 426  # baseline untouched
    by = D["offtake"]["pos_stores"]["fy27"]["by_chain"]
    assert by["DMart"]["latest"] > 100 and by["Apollo"]["latest"] > 1000
    assert "Reliance Brand Counter" not in by
    assert by["Reliance Retail"]["latest"] is None
