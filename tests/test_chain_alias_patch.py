"""Chain names: one name per chain in data.js (owner-confirmed 2026-10-11).

Hypermax City Private Limited and CARREFOUR are the same new chain, Carrefour; Octopolis Technologies
Pvt Ltd is Apna Klub. The patch folds them into one chain in every block and keeps the totals.
"""
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import build_dashboard_data as bd  # noqa: E402

OLD = ("Hypermax City Private Limited", "CARREFOUR", "Octopolis Technologies Pvt Ltd")


def _datajs():
    s = (ROOT / "dashboard" / "data.js").read_text()
    return json.loads(s[s.index("{"): s.rindex("}") + 1])


def test_aliases_and_patch_table_agree():
    for old, new in bd.CHAIN_PATCH_RENAMES.items():
        assert bd.canon_chain(old) == new


def test_rename_merge_rows_adds_values_and_keeps_total():
    rows = [{"name": "Hypermax City Private Limited", "nsv": 2.68}, {"name": "CARREFOUR", "nsv": 2.48},
            {"name": "DMart", "nsv": 10.0}]
    out, merged = bd._rename_merge_rows(copy.deepcopy(rows), ("nsv",))
    assert merged == 1
    assert [r["name"] for r in out] == ["Carrefour", "DMart"]
    assert round(sum(r["nsv"] for r in out), 4) == round(sum(r["nsv"] for r in rows), 4)


def test_rename_merge_is_idempotent():
    rows = [{"name": "Carrefour", "nsv": 5.16}]
    out, merged = bd._rename_merge_rows(copy.deepcopy(rows), ("nsv",))
    assert merged == 0 and out == rows


def test_shipped_data_js_has_one_name_per_chain():
    text = json.dumps(_datajs())
    for name in OLD:
        assert name not in text, f"{name!r} still in data.js"
    d = _datajs()
    assert "Carrefour" in d["dims"]["Chain"]
    assert len(d["dims"]["Chain"]) == len(set(d["dims"]["Chain"]))


def test_chain_totals_tie_after_merge():
    d = _datajs()
    detail = round(sum(r.get("NSV") or 0 for r in d["detail_records"]), 2)
    assert round(sum(r["nsv"] for r in d["cm2"]["by_chain"]), 2) == round(sum(r["nsv"] for r in d["tot"]["by_chain"]), 2)
    assert abs(detail - round(sum(r["nsv"] for r in d["tot"]["by_chain"]), 2)) < 6  # tot covers the same detail, ±rounding/unallocated
