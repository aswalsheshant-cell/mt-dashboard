"""FM-19: owner-approved overrides in PrimaryAllocationOverride.csv must
actually change `_Chain` -- but ONLY for distributor rows that would
otherwise stay "Unmapped Chain" (the owner's scope decision, 2026-09-27,
option A). Rows the cont% sheet already maps (exact or nearest month) must
never move, total NSV must not change, and a split override (<100%) must
fail loudly rather than be guessed. Synthetic data only.
"""
import importlib
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
bd = importlib.import_module("build_dashboard_data")


def _df():
    # Alpha/Mamaearth Apr is covered by the cont sheet; Gamma/BBlunt Aug is not.
    return pd.DataFrame({
        "PO Type": ["Dist.", "Dist.", "Dist."],
        "Ship To Name": ["Alpha Distributors", "Gamma Agencies", "Gamma Agencies"],
        "brand": ["Mamaearth", "BBLUNT", "Mamaearth"],
        "Month": ["Apr'26", "Aug'26", "Aug'26"],   # real source format
        "Chain name for Dashboard": [None, None, None],
        "_CustName": ["Alpha Distributors", "Gamma Agencies", "Gamma Agencies"],
        "_CustCode": ["D001", "D003", "D003"],
        "_Brand": ["Mamaearth", "BBLUNT", "Mamaearth"],
        "_Zone": ["North", "South-1", "South-1"],
        "_FY": ["FY27", "FY27", "FY27"],
        "_M": ["April", "Aug", "Aug"],
        "_NSV": [100.0, 5.0, 7.0],
        "_MRP": [140.0, 8.0, 10.0],
        "_Qty": [14, 1, 2],
        "_TaxLOC": [7.0, 0.5, 0.6],
        "_AvgTot": [10.0, 10.0, 10.0],
        "_EAN No.": ["", "", ""],
    })


def _wdf():
    w = pd.DataFrame({
        "_st": ["alpha distributors", "alpha distributors"],
        "_bl": ["mamaearth", "mamaearth"],
        "_pm": ["2026-04", "2026-04"],
        "_frac": [0.7, 0.3],
        "_AllocChainRaw": ["DMart", "Reliance Retail"],
        "_ShipToRaw": ["Alpha Distributors"] * 2,
        "_BrandRaw": ["Mamaearth"] * 2,
    })
    return w, {("alpha distributors", "mamaearth", "2026-04"): 100.0}


def _override(tmp_path, rows):
    p = tmp_path / "PrimaryAllocationOverride.csv"
    pd.DataFrame(rows, columns=["Month", "Ship To Name", "Chain", "Brand",
                                "Override Cont%", "Remarks"]).to_csv(p, index=False)
    return p


def _run(tmp_path, ov):
    w, rs = _wdf()
    return bd.allocate_dist_primary(_df(), w, rs, source_label="test",
                                    output_dir=tmp_path / "out", override_csv=ov)


def _chain_nsv(out):
    return out.groupby(["_CustName", "_Brand", "_Chain"])["_NSV"].sum().to_dict()


def test_without_override_the_uncovered_key_stays_unmapped(tmp_path):
    out, alloc = _run(tmp_path, _override(tmp_path, []))
    got = _chain_nsv(out)
    assert got[("Gamma Agencies", "BBLUNT", "Unmapped Chain")] == 5.0
    assert alloc["unmapped_nsv"] == 12.0


def test_approved_override_maps_only_the_unmapped_key(tmp_path):
    ov = _override(tmp_path, [["2026-08", "Gamma Agencies", "Apollo", "BBLUNT", 100,
                               "Approved: owner 2026-09-27"]])
    out, alloc = _run(tmp_path, ov)
    got = _chain_nsv(out)
    assert got[("Gamma Agencies", "BBLUNT", "Apollo")] == 5.0
    # the other uncovered key has no override and stays unmapped
    assert got[("Gamma Agencies", "Mamaearth", "Unmapped Chain")] == 7.0
    # the cont%-mapped key is untouched
    assert got[("Alpha Distributors", "Mamaearth", "DMart")] == pytest.approx(70.0)
    assert got[("Alpha Distributors", "Mamaearth", "Reliance Retail")] == pytest.approx(30.0)
    assert out["_NSV"].sum() == pytest.approx(112.0)
    assert alloc["unmapped_nsv"] == 7.0
    assert alloc["override_applied_rows"] == 1
    assert alloc["override_applied_nsv"] == 5.0


def test_override_never_moves_a_key_the_cont_sheet_already_maps(tmp_path):
    ov = _override(tmp_path, [["2026-04", "Alpha Distributors", "Apollo", "Mamaearth", 100,
                               "Approved: owner 2026-09-27"]])
    out, alloc = _run(tmp_path, ov)
    got = _chain_nsv(out)
    assert ("Alpha Distributors", "Mamaearth", "Apollo") not in got
    assert got[("Alpha Distributors", "Mamaearth", "DMart")] == pytest.approx(70.0)
    assert alloc["override_applied_rows"] == 0


def test_split_override_fails_loudly(tmp_path):
    ov = _override(tmp_path, [["2026-08", "Gamma Agencies", "Apollo", "BBLUNT", 60, "x"],
                              ["2026-08", "Gamma Agencies", "DMart", "BBLUNT", 40, "x"]])
    with pytest.raises(SystemExit):
        _run(tmp_path, ov)


def test_repo_override_file_rows_are_single_chain_and_documented():
    # Contract extended 2026-09-27: two evidence columns added so an owner
    # decision that disagrees with the EAN-affinity inference is recorded in
    # governed data, not only in a PR description.
    p = Path(__file__).resolve().parent.parent / "PowerBI" / "SeedData" / "Masters" / "PrimaryAllocationOverride.csv"
    ov = pd.read_csv(p)
    assert list(ov.columns) == ["Month", "Ship To Name", "Chain", "Brand", "Override Cont%", "Remarks",
                                "Evidence_Alignment", "Evidence_Reference"]
    assert (ov["Override Cont%"] == 100).all()
    assert ov["Remarks"].apply(lambda r: bool(bd.OVERRIDE_APPROVAL.search(str(r)))).all()
    assert set(ov["Evidence_Alignment"]) <= {"AGREES", "CONFLICTS", "NO_INDEPENDENT_EVIDENCE"}
    assert ov["Evidence_Reference"].notna().all()


def test_mapping_health_lists_only_still_unmapped_proposals(tmp_path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "unmapped_chains_bridge_suggested.csv").write_text(
        "cust_code,ship_to,total_nsv_lakh,suggested_chain,suggested_zone,confidence,cumulative_coverage_pct\n"
        "D1,Already Mapped Dist,2500,DMart,West,HIGH,50\n"
        "D2,Still Unmapped Dist,8,Lulu,South-1,LOW,100\n", encoding="utf-8")
    df = pd.DataFrame({"_FY": ["FY27", "FY27"], "_Chain": ["DMart", "Unmapped Chain"],
                       "_NSV": [100.0, 8.0]})
    alloc = {"missing_mapping": [{"fy": "FY27", "month": "Aug", "brand": "Mamaearth",
                                  "cust_code": "D2", "ship_to": "Still Unmapped Dist",
                                  "nsv": 8.0, "rows": 3}]}
    mh = bd.mapping_health_block(df, alloc=alloc, repo_root=tmp_path)
    assert [p["ship_to"] for p in mh["proposals"]] == ["Still Unmapped Dist"]
    assert mh["proposals_already_mapped_count"] == 1


@pytest.mark.parametrize("remark", [None, "", "looks right", "Approved:", "Approved: owner"])
def test_override_without_approval_evidence_fails_closed(tmp_path, remark):
    ov = _override(tmp_path, [["2026-08", "Gamma Agencies", "Apollo", "BBLUNT", 100, remark]])
    with pytest.raises(SystemExit):
        _run(tmp_path, ov)


def test_override_file_without_remarks_column_fails_closed(tmp_path):
    p = tmp_path / "PrimaryAllocationOverride.csv"
    pd.DataFrame([["2026-08", "Gamma Agencies", "Apollo", "BBLUNT", 100]],
                 columns=["Month", "Ship To Name", "Chain", "Brand", "Override Cont%"]).to_csv(p, index=False)
    with pytest.raises(SystemExit):
        _run(tmp_path, p)


def test_nearest_month_cont_split_beats_an_override(tmp_path):
    # Alpha/Mamaearth has cont% data for Apr only; a Jun row resolves to the
    # nearest month (Apr, 2 months away). An override for Jun must not win.
    df = _df()
    df.loc[0, "Month"] = "Jun'26"
    df.loc[0, "_M"] = "June"
    ov = _override(tmp_path, [["2026-06", "Alpha Distributors", "Apollo", "Mamaearth", 100,
                               "Approved: owner 2026-09-27"]])
    w, rs = _wdf()
    out, alloc = bd.allocate_dist_primary(df, w, rs, source_label="test",
                                          output_dir=tmp_path / "out", override_csv=ov)
    got = _chain_nsv(out)
    assert ("Alpha Distributors", "Mamaearth", "Apollo") not in got
    assert got[("Alpha Distributors", "Mamaearth", "DMart")] == pytest.approx(70.0)
    assert alloc["override_applied_rows"] == 0
