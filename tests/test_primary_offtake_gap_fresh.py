"""primary_offtake_gap must not lag behind its inputs (FM-30)."""
import json
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "dashboard" / "data.js"


def _data():
    s = DATA.read_text(encoding="utf-8")
    return json.loads(s[s.index("{"): s.rindex("}") + 1])


def test_gap_offtake_equals_offtake_block():
    d = _data()
    g, o = d["primary_offtake_gap"], d["offtake"]
    for fy in ("fy26", "fy27"):
        gap_total = sum(r["offtake"] for r in g[fy]["by_month"]["rows"] if r["offtake"] is not None)
        assert abs(gap_total - o["total_" + fy]) < 0.1, (fy, gap_total, o["total_" + fy])


def test_gap_chain_offtake_matches_by_chain():
    d = _data()
    by = {c["name"]: c for c in d["offtake"]["by_chain"]}
    for fy in ("fy26", "fy27"):
        for grp in ("matched", "offtake_only"):
            for r in g_rows(d, fy, grp):
                assert abs(r["offtake"] - by[r["name"]][fy]) < 0.02, (fy, r["name"])


def test_fy26_gap_primary_is_on_the_mt_basis():
    d = _data()
    p = sum(r["primary"] for r in d["primary_offtake_gap"]["fy26"]["by_month"]["rows"])
    mt = next(c["fy26"] for c in d["primary"]["by_channel"] if c["name"] == "MT")
    assert abs(p - mt) < 0.1, (p, mt)


def test_no_retired_chain_name_in_chain_lists():
    d = _data()
    names = {c["name"] for c in d["offtake"]["by_chain"]}
    for fy in ("fy26", "fy27"):
        for grp in ("matched", "primary_only", "offtake_only"):
            names |= {r["name"] for r in g_rows(d, fy, grp)}
    assert "Trent/Westside" not in names and "Reliance Trends" in names


def test_refresh_helper_keeps_fy27_when_fyx_primary_is_missing():
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
    import build_dashboard_data as b
    d = _data()
    d["detail_meta"] = {}
    before = json.dumps(d["primary_offtake_gap"]["fy27"], sort_keys=True)
    b.refresh_primary_offtake_gap(d)
    assert d["primary_offtake_gap"]["fy27"] is not None
    assert json.dumps(d["primary_offtake_gap"]["fy27"], sort_keys=True) == before


def test_rename_does_not_duplicate_a_row():
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
    import build_dashboard_data as b
    off = {"by_chain": [{"name": "Trent/Westside", "raw": "Trent/Westside", "fy27": 1.0},
                        {"name": "Reliance Trends", "raw": "Reliance Trends", "fy27": 2.0}]}
    b.apply_chain_renames(off)
    assert [c["name"] for c in off["by_chain"]] == ["Reliance Trends"]


def g_rows(d, fy, grp):
    return d["primary_offtake_gap"][fy]["by_chain"][grp]
